"""
Collateral Vault Detail page for Risk Dashboard.
Displays historical snapshots and metrics for a specific collateral vault.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc

from src.components import PageContainer, SectionCard, MetricCard, LoadingState, ErrorState, ErrorAlert
from src.api import api_client

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash - using path_template for dynamic routing
dash.register_page(
    __name__, 
    path_template="/collateralVaults/<vault_address>", 
    title="Collateral Vault Detail - Risk Dashboard"
)


def fetch_vault_history_data(
    vault_address: str, 
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch historical snapshots for a specific collateral vault.
    
    Args:
        vault_address: The vault address to fetch data for
        limit: Number of historical records to fetch
        start_time: Start time filter (Unix timestamp)
        end_time: End time filter (Unix timestamp)
        
    Returns:
        Dict containing history data or error information
    """
    try:
        logger.info(f"Fetching historical data for collateral vault: {vault_address}")
        
        # Fetch data using the API client
        response = api_client.get_collateral_vault_history(
            address=vault_address,
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "snapshots": []
            }
        
        # Extract snapshots from successful response
        snapshots = response.snapshots
        
        logger.info(f"Successfully fetched {len(snapshots)} historical snapshots for vault {vault_address}")
        
        return {
            "error": None,
            "snapshots": snapshots,
            "vault_address": vault_address
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch collateral vault history for {vault_address}: {e}")
        return {
            "error": str(e),
            "snapshots": []
        }


def format_history_for_table(snapshots: List) -> List[Dict[str, Any]]:
    """
    Format CollateralVaultSnapshot objects for table display.
    
    Args:
        snapshots: List of CollateralVaultSnapshot objects
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if not snapshots:
        return []
    
    table_data = []
    for snapshot in snapshots:
        # Convert snapshot to dictionary and format values with proper scaling
        # USD values need to be scaled by 1e18
        max_release_usd = float(snapshot.maxReleaseUsd) / 1e18 if snapshot.maxReleaseUsd != "0" else 0.0
        max_repay_usd = float(snapshot.maxRepayUsd) / 1e18 if snapshot.maxRepayUsd != "0" else 0.0
        total_assets_usd = float(snapshot.totalAssetsDepositedOrReservedUsd) / 1e18 if snapshot.totalAssetsDepositedOrReservedUsd != "0" else 0.0
        user_collateral_usd = float(snapshot.userOwnedCollateralUsd) / 1e18 if snapshot.userOwnedCollateralUsd != "0" else 0.0
        
        # Twyne LTV needs to be scaled by 1e4 and displayed as percentage
        twyne_liq_ltv_decimal = float(snapshot.twyneLiqLtv) / 1e4 if snapshot.twyneLiqLtv != "0" else 0.0
        twyne_liq_ltv_percentage = twyne_liq_ltv_decimal * 100
        
        row = {
            "Block Number": int(snapshot.blockNumber),
            "Block Timestamp": datetime.fromtimestamp(int(snapshot.blockTimestamp)).strftime("%Y-%m-%d %H:%M:%S"),
            "Chain ID": snapshot.chainId,
            "Credit Vault": snapshot.creditVault[:10] + "..." if len(snapshot.creditVault) > 10 else snapshot.creditVault,
            "Debt Vault": snapshot.debtVault[:10] + "..." if len(snapshot.debtVault) > 10 else snapshot.debtVault,
            "Max Release (USD)": max_release_usd,
            "Max Repay (USD)": max_repay_usd,
            "Total Assets (USD)": total_assets_usd,
            "User Collateral (USD)": user_collateral_usd,
            "Twyne Liq LTV (%)": twyne_liq_ltv_percentage,
            "Can Liquidate": "Yes" if snapshot.canLiquidate else "No",
            "Externally Liquidated": "Yes" if snapshot.isExternallyLiquidated else "No",
            "Log Index": int(snapshot.logIndex)
        }
        table_data.append(row)
    
    return table_data


def get_history_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the collateral vault history table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "Credit Vault", "id": "Credit Vault"},
        {"name": "Debt Vault", "id": "Debt Vault"},
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Twyne Liq LTV (%)", "id": "Twyne Liq LTV (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Can Liquidate", "id": "Can Liquidate"},
        {"name": "Externally Liquidated", "id": "Externally Liquidated"},
        {"name": "Log Index", "id": "Log Index", "type": "numeric"}
    ]


def layout(vault_address: str = None):
    """
    Define the layout for the collateral vault detail page.
    
    Args:
        vault_address: The vault address from the URL
        
    Returns:
        Dash layout components
    """
    if not vault_address:
        return PageContainer(
            children=[
                ErrorAlert(
                    message="No vault address provided",
                    title="Invalid URL"
                )
            ]
        )
    
    return PageContainer(
        children=[
            # URL location component for callbacks
            dcc.Location(id="collateral-vault-detail-url", refresh=False),
            
            # Store vault address for callbacks
            dcc.Store(id="collateral-vault-address-store", data=vault_address),
            
            # Back navigation
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-arrow-left me-2"), "Back to Collateral Vaults"],
                    href="/collateralVaults",
                    color="outline-secondary",
                    size="sm",
                    className="mb-3"
                )
            ]),
            
            # Page title
            html.Div([
                html.H2([
                    html.I(className="fas fa-vault me-2"),
                    f"Collateral Vault Details"
                ], className="mb-2"),
                html.P([
                    html.Strong("Address: "),
                    html.Code(vault_address, className="bg-light p-1")
                ], className="text-muted mb-4")
            ]),
            
            # Metrics section
            SectionCard(
                title="Current Metrics",
                icon="fas fa-chart-bar",
                children=[
                    html.Div(id="collateral-vault-detail-metrics", className="mb-3")
                ]
            ),
            
            # History table section
            SectionCard(
                title="Vault History",
                icon="fas fa-history",
                action_button=dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                    id="collateral-vault-detail-refresh",
                    color="outline-primary",
                    size="sm"
                ),
                children=[
                    # Date range picker
                    html.Div([
                        html.Label("Select Date Range:", className="form-label mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("From:", size="sm"),
                                dcc.DatePickerSingle(
                                    id="collateral-start-date-picker",
                                    date=(datetime.now() - timedelta(days=30)).date(),
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"}
                                )
                            ], width=12, md=6),
                            dbc.Col([
                                dbc.Label("To:", size="sm"),
                                dcc.DatePickerSingle(
                                    id="collateral-end-date-picker",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"}
                                )
                            ], width=12, md=6)
                        ], className="g-2"),
                        html.Div([
                            dbc.ButtonGroup([
                                dbc.Button("Last 7 days", id="collateral-7d-btn", size="sm", outline=True),
                                dbc.Button("Last 30 days", id="collateral-30d-btn", size="sm", outline=True),
                                dbc.Button("Last 90 days", id="collateral-90d-btn", size="sm", outline=True),
                                dbc.Button("Apply Range", id="collateral-apply-date-range", color="primary", size="sm")
                            ], className="mt-2")
                        ])
                    ], className="mb-3"),
                    
                    # Status message container
                    html.Div(id="collateral-vault-detail-status", className="mb-3"),
                    
                    # Table container
                    html.Div(id="collateral-vault-detail-table", className="mb-3"),
                    
                    # Last updated info
                    html.Div([
                        html.Small(id="collateral-vault-detail-last-updated", className="text-muted")
                    ], className="text-end")
                ]
            )
        ]
    )


# Callback for collateral vault detail page
@callback(
    [Output("collateral-vault-detail-metrics", "children"),
     Output("collateral-vault-detail-status", "children"),
     Output("collateral-vault-detail-table", "children"),
     Output("collateral-vault-detail-last-updated", "children")],
    [Input("collateral-vault-detail-refresh", "n_clicks"),
     Input("collateral-vault-detail-url", "pathname"),
     Input("collateral-apply-date-range", "n_clicks"),
     Input("collateral-7d-btn", "n_clicks"),
     Input("collateral-30d-btn", "n_clicks"),
     Input("collateral-90d-btn", "n_clicks")],
    [State("collateral-vault-address-store", "data"),
     State("collateral-start-date-picker", "date"),
     State("collateral-end-date-picker", "date")],
    prevent_initial_call=False
)
def update_collateral_vault_detail(n_clicks_refresh, pathname, n_clicks_apply, n_clicks_7d, 
                                 n_clicks_30d, n_clicks_90d, vault_address, start_date, end_date):
    """
    Update the collateral vault detail metrics and history table.
    
    Args:
        n_clicks_refresh: Number of times refresh button was clicked
        pathname: Current URL path
        n_clicks_apply: Number of times apply date range button was clicked
        n_clicks_7d: Number of times 7 days button was clicked
        n_clicks_30d: Number of times 30 days button was clicked
        n_clicks_90d: Number of times 90 days button was clicked
        vault_address: Vault address from store
        start_date: Start date from date picker
        end_date: End date from date picker
        
    Returns:
        Tuple of (metrics_cards, status_message, table_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/collateralVaults/"):
        return [], "", "", ""
    
    logger.info(f"Updating collateral vault detail for {vault_address}...")
    
    # Determine date range based on button clicks
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "collateral-7d-btn":
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=7)).timestamp())
        elif trigger_id == "collateral-30d-btn":
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=30)).timestamp())
        elif trigger_id == "collateral-90d-btn":
            end_time = int(datetime.now().timestamp())
            start_time = int((datetime.now() - timedelta(days=90)).timestamp())
        else:
            # Convert dates to Unix timestamps if provided
            start_time = None
            end_time = None
            
            if start_date:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                start_time = int(start_datetime.timestamp())
            
            if end_date:
                # Set end time to end of the selected day
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                end_time = int(end_datetime.timestamp())
            
            # If no dates selected, default to last 30 days
            if not start_time or not end_time:
                end_time = int(datetime.now().timestamp())
                start_time = int((datetime.now() - timedelta(days=30)).timestamp())
    else:
        # Default to last 30 days on initial load
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=30)).timestamp())
    
    # Fetch the historical data with time filtering
    data = fetch_vault_history_data(
        vault_address, 
        limit=1000,  # Increase limit for historical data
        start_time=start_time,
        end_time=end_time
    )
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        table_component = ErrorState(
            error_message="Unable to load history data due to API error",
            retry_callback="collateral-vault-detail-refresh"
        )
    else:
        # Format date range for display
        start_date_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")
        end_date_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
        
        status_message = dbc.Alert(
            f"Loaded {len(data['snapshots'])} historical records from {start_date_str} to {end_date_str}", 
            color="success",
            dismissable=True,
            duration=4000
        )
        
        # Calculate current metrics from latest data point
        if data["snapshots"]:
            # Sort by block number descending to get latest
            sorted_snapshots = sorted(data["snapshots"], key=lambda x: int(x.blockNumber), reverse=True)
            latest_snapshot = sorted_snapshots[0]
            
            # Calculate metrics from latest snapshot
            max_release_usd = float(latest_snapshot.maxReleaseUsd) / 1e18 if latest_snapshot.maxReleaseUsd != "0" else 0.0
            max_repay_usd = float(latest_snapshot.maxRepayUsd) / 1e18 if latest_snapshot.maxRepayUsd != "0" else 0.0
            total_assets_usd = float(latest_snapshot.totalAssetsDepositedOrReservedUsd) / 1e18 if latest_snapshot.totalAssetsDepositedOrReservedUsd != "0" else 0.0
            user_collateral_usd = float(latest_snapshot.userOwnedCollateralUsd) / 1e18 if latest_snapshot.userOwnedCollateralUsd != "0" else 0.0
            twyne_liq_ltv_decimal = float(latest_snapshot.twyneLiqLtv) / 1e4 if latest_snapshot.twyneLiqLtv != "0" else 0.0
            twyne_liq_ltv_percentage = twyne_liq_ltv_decimal * 100
            
            metrics_cards = dbc.Row([
                dbc.Col([
                    MetricCard(
                        title="Max Release (USD)",
                        value=f"${max_release_usd:,.2f}",
                        icon="fas fa-arrow-up",
                        color="success"
                    )
                ], width=12, md=6, lg=3),
                dbc.Col([
                    MetricCard(
                        title="Max Repay (USD)",
                        value=f"${max_repay_usd:,.2f}",
                        icon="fas fa-arrow-down",
                        color="warning"
                    )
                ], width=12, md=6, lg=3),
                dbc.Col([
                    MetricCard(
                        title="Total Assets (USD)",
                        value=f"${total_assets_usd:,.2f}",
                        icon="fas fa-coins",
                        color="info"
                    )
                ], width=12, md=6, lg=3),
                dbc.Col([
                    MetricCard(
                        title="Twyne Liq LTV (%)",
                        value=f"{twyne_liq_ltv_percentage:.2f}%",
                        icon="fas fa-percentage",
                        color="primary"
                    )
                ], width=12, md=6, lg=3)
            ], className="g-3")
        else:
            metrics_cards = []
        
        # Create table component
        if data["snapshots"]:
            table_data = format_history_for_table(data["snapshots"])
            # Sort table data by block number descending
            table_data.sort(key=lambda x: x["Block Number"], reverse=True)
            
            table_component = html.Div([
                html.H5("Collateral Vault History", className="mb-3"),
                dash_table.DataTable(
                    id="collateral-vault-history-table",
                    data=table_data,
                    columns=get_history_table_columns(),
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    sort_by=[{"column_id": "Block Number", "direction": "desc"}],  # Default sort
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'maxWidth': '200px',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {'filter_query': '{Can Liquidate} = Yes'},
                            'backgroundColor': '#ffebee',
                            'color': 'black'
                        },
                        {
                            'if': {'filter_query': '{Externally Liquidated} = Yes'},
                            'backgroundColor': '#fff3e0',
                            'color': 'black'
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display",
                    tooltip_data=[
                        {
                            column: {'value': str(row[column]), 'type': 'markdown'}
                            for column in row.keys()
                        } for row in table_data
                    ],
                    tooltip_duration=None
                )
            ])
        else:
            table_component = html.Div([
                html.H5("Collateral Vault History", className="mb-3"),
                html.P("No history data available for the selected date range", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, table_component, last_updated


# Quick date range button callbacks
@callback(
    [Output("collateral-start-date-picker", "date"),
     Output("collateral-end-date-picker", "date")],
    [Input("collateral-7d-btn", "n_clicks"),
     Input("collateral-30d-btn", "n_clicks"),
     Input("collateral-90d-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_date_range(n_clicks_7d, n_clicks_30d, n_clicks_90d):
    """Update date range pickers based on quick selection buttons."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    end_date = datetime.now().date()
    
    if trigger_id == "collateral-7d-btn":
        start_date = (datetime.now() - timedelta(days=7)).date()
    elif trigger_id == "collateral-30d-btn":
        start_date = (datetime.now() - timedelta(days=30)).date()
    elif trigger_id == "collateral-90d-btn":
        start_date = (datetime.now() - timedelta(days=90)).date()
    else:
        return dash.no_update, dash.no_update
    
    return start_date, end_date
