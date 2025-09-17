"""
Section components for the Risk Dashboard.
Contains reusable dashboard sections with specific business logic.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from dash import html, dcc, callback, Output, Input, dash_table
import dash_bootstrap_components as dbc

from src.api import api_client
from .cards import MetricCard
from .layouts import SectionCard, LoadingSpinner, ErrorAlert
from .loading import LoadingState, ErrorState
from src.utils.usd_calculations import (
    calculate_multiple_snapshots_usd_values,
    get_summary_metrics_from_snapshots,
    format_enhanced_snapshots_for_table,
    get_pricing_warnings_summary
)
from src.utils.health_factor import (
    calculate_health_factors_for_snapshots,
    get_health_factor_summary_stats
)
from .charts import create_health_factor_scatter_plot

logger = logging.getLogger(__name__)


def fetch_collateral_vault_data() -> Dict[str, Any]:
    """
    Fetch collateral vault snapshots and return summary metrics.
    
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info("Fetching collateral vaults snapshots...")
        
        # Fetch data using the API client
        response = api_client.get_collateral_vaults_snapshots(limit=100)
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "unique_vaults": 0,
                "total_snapshots": 0
            }
        
        # Extract snapshots from successful response
        snapshots = response.latestSnapshots
        total_snapshots = len(snapshots)
        
        if not snapshots:
            logger.warning("No snapshots returned from API")
            return {
                "error": None,
                "unique_vaults": 0,
                "total_snapshots": 0,
                "snapshots": [],
                "enhanced_snapshots": [],
                "summary_metrics": {},
                "pricing_warnings": []
            }
        
        # Calculate USD values using EVault pricing
        enhanced_snapshots, pricing_warnings = calculate_multiple_snapshots_usd_values(snapshots)
        
        # Count unique vault addresses
        unique_vault_addresses = set()
        for snapshot in snapshots:
            unique_vault_addresses.add(snapshot.vaultAddress)
        
        unique_vaults_count = len(unique_vault_addresses)
        
        # Calculate summary metrics from enhanced snapshots
        summary_metrics = get_summary_metrics_from_snapshots(enhanced_snapshots)
        
        logger.info(f"Successfully processed {total_snapshots} snapshots from {unique_vaults_count} unique vaults with {len(pricing_warnings)} pricing warnings")
        
        return {
            "error": None,
            "unique_vaults": unique_vaults_count,
            "total_snapshots": total_snapshots,
            "total_unique_vaults": getattr(response, 'totalUniqueVaults', None),
            "snapshots": snapshots,  # Keep original for compatibility
            "enhanced_snapshots": enhanced_snapshots,
            "summary_metrics": summary_metrics,
            "pricing_warnings": pricing_warnings
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch vault data: {e}", exc_info=True)
        return {
            "error": str(e),
            "unique_vaults": 0,
            "total_snapshots": 0,
            "snapshots": [],
            "enhanced_snapshots": [],
            "summary_metrics": {},
            "pricing_warnings": []
        }


def format_snapshots_for_table(snapshots: List) -> List[Dict[str, Any]]:
    """
    Format CollateralVaultSnapshot objects for table display using new pricing mechanism.
    
    Args:
        snapshots: List of CollateralVaultSnapshot objects
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if not snapshots:
        return []
    
    # Calculate USD values using EVault pricing
    enhanced_snapshots, _ = calculate_multiple_snapshots_usd_values(snapshots)
    
    # Format enhanced snapshots for table
    return format_enhanced_snapshots_for_table(enhanced_snapshots)


def get_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the collateral vaults table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "Vault Address", "id": "Vault Address"},
        {"name": "Credit Vault", "id": "Credit Vault"},
        {"name": "Debt Vault", "id": "Debt Vault"},
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Twyne Liq LTV (%)", "id": "Twyne Liq LTV (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Can Liquidate", "id": "Can Liquidate"},
        {"name": "Externally Liquidated", "id": "Externally Liquidated"},
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Actions", "id": "Actions", "presentation": "markdown"}
    ]


def CollateralVaultsSection(section_id: str = "collateral-section") -> html.Div:
    """
    Create the collateral vaults section component.
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        Collateral vaults section component
    """
    refresh_button = dbc.Button(
        [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
        id=f"{section_id}-refresh",
        color="outline-primary",
        size="sm"
    )
    
    return SectionCard(
        title="Collateral Vaults",
        icon="fas fa-vault",
        action_button=refresh_button,
        children=[
            # Metrics container
            html.Div(id=f"{section_id}-metrics", className="mb-3"),
            
            # Status message container
            html.Div(id=f"{section_id}-status", className="mb-3"),
            
            # Health Factor Chart container
            html.Div(id=f"{section_id}-health-chart", className="mb-4"),
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


def fetch_evaults_data() -> Dict[str, Any]:
    """
    Fetch EVault metrics and return summary data.
    
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info("Fetching EVaults latest metrics...")
        
        # Fetch data using the API client
        response = api_client.get_evaults_latest()
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "total_vaults": 0,
                "metrics": []
            }
        
        # Extract metrics from successful response
        metrics = response.latestMetrics or []
        total_vaults = len(metrics)
        
        logger.info(f"Successfully processed {total_vaults} EVault metrics")
        
        return {
            "error": None,
            "total_vaults": total_vaults,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch EVaults data: {e}", exc_info=True)
        return {
            "error": str(e),
            "total_vaults": 0,
            "metrics": []
        }


def format_evaults_for_table(metrics: List) -> List[Dict[str, Any]]:
    """
    Format EVaultMetric objects for table display.
    
    Args:
        metrics: List of EVaultMetric objects
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if not metrics:
        return []
    
    table_data = []
    for metric in metrics:
        # Get decimals for proper scaling
        decimals = int(metric.decimals) if metric.decimals != "0" else 18
        scaling_factor = 10 ** decimals
        
        # Scale totalAssets and totalBorrows using decimals
        total_assets = float(metric.totalAssets) / scaling_factor if metric.totalAssets != "0" else 0.0
        total_borrows = float(metric.totalBorrows) / scaling_factor if metric.totalBorrows != "0" else 0.0
        
        # Calculate utilization rate
        utilization_rate = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
        
        # Format USD values - scale by 1e18 if they are very large
        total_assets_usd_raw = float(metric.totalAssetsUsd) if metric.totalAssetsUsd != "0" else 0.0
        total_assets_usd = total_assets_usd_raw / 1e18 if total_assets_usd_raw > 1e12 else total_assets_usd_raw
        
        total_borrows_usd_raw = float(metric.totalBorrowsUsd) if metric.totalBorrowsUsd != "0" else 0.0
        total_borrows_usd = total_borrows_usd_raw / 1e18 if total_borrows_usd_raw > 1e12 else total_borrows_usd_raw
        
        # Format interest rate as percentage
        interest_rate = float(metric.interestRate) / 1e18 * 100 if metric.interestRate != "0" else 0.0
        
        row = {
            "Chain ID": metric.chainId,
            "Vault Address": metric.vaultAddress[:10] + "..." if len(metric.vaultAddress) > 10 else metric.vaultAddress,
            "Full Vault Address": metric.vaultAddress,  # Store full address for navigation
            "Name": metric.name,
            "Symbol": metric.symbol,
            "Asset": metric.asset[:10] + "..." if len(metric.asset) > 10 else metric.asset,
            "Total Assets": total_assets,
            "Total Assets (USD)": total_assets_usd,
            "Total Borrows": total_borrows,
            "Total Borrows (USD)": total_borrows_usd,
            "Interest Rate (%)": interest_rate,
            "Utilization Rate (%)": utilization_rate,
            "Block Number": int(metric.blockNumber),
            "Block Timestamp": datetime.fromtimestamp(int(metric.blockTimestamp)).strftime("%Y-%m-%d %H:%M:%S"),
            "Actions": f"[More](/evaults/{metric.vaultAddress})"
        }
        table_data.append(row)
    
    return table_data


def get_evaults_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the EVaults table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "Vault Address", "id": "Vault Address"},
        {"name": "Name", "id": "Name"},
        {"name": "Symbol", "id": "Symbol"},
        {"name": "Asset", "id": "Asset"},
        {"name": "Total Assets", "id": "Total Assets", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Borrows", "id": "Total Borrows", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Total Borrows (USD)", "id": "Total Borrows (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Interest Rate (%)", "id": "Interest Rate (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Utilization Rate (%)", "id": "Utilization Rate (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Actions", "id": "Actions", "presentation": "markdown"}
    ]


def EVaultsSection(section_id: str = "evaults-section") -> html.Div:
    """
    Create the EVaults section component.
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        EVaults section component
    """
    refresh_button = dbc.Button(
        [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
        id=f"{section_id}-refresh",
        color="outline-primary",
        size="sm"
    )
    
    # Vault type toggle component
    vault_type_toggle = dbc.Row([
        dbc.Col([
            html.Label("Vault Type:", className="fw-bold mb-2"),
            dbc.ButtonGroup([
                dbc.Button(
                    "Twyne",
                    id=f"{section_id}-twyne-btn",
                    color="primary",
                    outline=False,
                    size="sm"
                ),
                dbc.Button(
                    "Euler", 
                    id=f"{section_id}-euler-btn",
                    color="primary",
                    outline=True,
                    size="sm"
                )
            ])
        ], width="auto"),
        # Store for the selected vault type
        dcc.Store(id=f"{section_id}-vault-type", data="twyne")
    ], className="mb-3", justify="start")
    
    return SectionCard(
        title="EVaults",
        icon="fas fa-coins",
        action_button=refresh_button,
        children=[
            # Vault type toggle
            vault_type_toggle,
            
            # Metrics container
            html.Div(id=f"{section_id}-metrics", className="mb-3"),
            
            # Status message container
            html.Div(id=f"{section_id}-status", className="mb-3"),
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


# Callback for collateral vaults section
@callback(
    [Output("collateral-section-metrics", "children"),
     Output("collateral-section-status", "children"),
     Output("collateral-section-health-chart", "children"),
     Output("collateral-section-table", "children"),
     Output("collateral-section-last-updated", "children")],
    [Input("collateral-section-refresh", "n_clicks"),
     Input("url", "pathname")],
    prevent_initial_call=False
)
def update_collateral_metrics(n_clicks, pathname):
    """
    Update the collateral vaults metrics and table.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        pathname: Current URL path
        
    Returns:
        Tuple of (metrics_cards, status_message, health_chart, table_component, last_updated_text)
    """
    # Only update if we're on the collateral vaults page
    if pathname != "/collateralVaults":
        return [], "", "", "", ""
    
    logger.info("Updating collateral vaults metrics...")
    
    # Fetch the data
    data = fetch_collateral_vault_data()
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        health_chart = html.Div([
            html.P("Health Factor chart unavailable due to API error", className="text-muted text-center p-4")
        ])
        table_component = ErrorState(
            error_message="Unable to load table data due to API error",
            retry_callback="collateral-section-refresh"
        )
    else:
        # Create status message with pricing warnings if any
        pricing_warning_summary = get_pricing_warnings_summary(data.get("pricing_warnings", []))
        
        if pricing_warning_summary:
            status_message = html.Div([
                dbc.Alert(
                    "Data loaded successfully", 
                    color="success",
                    dismissable=True,
                    duration=3000
                ),
                dbc.Alert(
                    pricing_warning_summary,
                    color="warning",
                    dismissable=True
                )
            ])
        else:
            status_message = dbc.Alert(
                "Data loaded successfully", 
                color="success",
                dismissable=True,
                duration=3000
            )
        
        # Use calculated summary metrics from enhanced snapshots
        summary_metrics = data.get("summary_metrics", {})
        
        # Create metrics cards using calculated values
        metrics_cards = dbc.Row([
            dbc.Col([
                MetricCard(
                    title="Total Collateral", 
                    value=f"${summary_metrics.get('total_user_collateral_usd', 0.0):,.2f}",
                    icon="fas fa-coins",
                    color="primary"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="Total Debt", 
                    value=f"${summary_metrics.get('total_max_repay_usd', 0.0):,.2f}",
                    icon="fas fa-exclamation-triangle",
                    color="warning"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="Total Credit Reserved", 
                    value=f"${summary_metrics.get('total_max_release_usd', 0.0):,.2f}",
                    icon="fas fa-piggy-bank",
                    color="success"
                )
            ], width=12, md=6, lg=4)
        ], className="g-3")
        
        # Create health factor chart
        enhanced_snapshots = data.get("enhanced_snapshots", [])
        if enhanced_snapshots:
            # Calculate health factors for chart
            chart_data = calculate_health_factors_for_snapshots(enhanced_snapshots)
            health_chart = html.Div([
                html.H5("Health Factor Analysis", className="mb-3"),
                create_health_factor_scatter_plot(chart_data, "Debt USD vs Health Factor")
            ])
        else:
            health_chart = html.Div([
                html.H5("Health Factor Analysis", className="mb-3"),
                html.P("No data available for health factor analysis", className="text-muted text-center p-4")
            ])
        
        # Create table component
        if data.get("enhanced_snapshots"):
            table_data = format_enhanced_snapshots_for_table(data["enhanced_snapshots"])
            table_component = html.Div([
                html.H5("Collateral Vaults Snapshots", className="mb-3"),
                dash_table.DataTable(
                    id="collateral-snapshots-table",
                    data=table_data,
                    columns=get_table_columns(),
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
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
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display"
                )
            ])
        else:
            table_component = html.Div([
                html.H5("Collateral Vaults Snapshots", className="mb-3"),
                html.P("No snapshot data available", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, health_chart, table_component, last_updated


# Callback for vault type toggle
@callback(
    [Output("evaults-section-vault-type", "data"),
     Output("evaults-section-twyne-btn", "outline"),
     Output("evaults-section-euler-btn", "outline")],
    [Input("evaults-section-twyne-btn", "n_clicks"),
     Input("evaults-section-euler-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_vault_type_toggle(twyne_clicks, euler_clicks):
    """
    Update the vault type selection based on button clicks.
    
    Args:
        twyne_clicks: Number of clicks on Twyne button
        euler_clicks: Number of clicks on Euler button
        
    Returns:
        Tuple of (selected_type, twyne_outline, euler_outline)
    """
    # Determine which button was clicked
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return "twyne", False, True
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if "twyne" in button_id:
        return "twyne", False, True  # Twyne selected (not outlined), Euler not selected (outlined)
    else:
        return "euler", True, False  # Twyne not selected (outlined), Euler selected (not outlined)


def filter_evaults_by_type(metrics: List, vault_type: str) -> List:
    """
    Filter EVault metrics by vault type based on symbol prefix.
    
    Args:
        metrics: List of EVaultMetric objects
        vault_type: Either "twyne" or "euler"
        
    Returns:
        Filtered list of EVaultMetric objects
    """
    if not metrics:
        return []
    
    filtered_metrics = []
    for metric in metrics:
        symbol = metric.symbol
        
        if vault_type == "twyne":
            # Twyne vaults start with 'ee' (case-sensitive)
            if symbol.startswith("ee"):
                filtered_metrics.append(metric)
        elif vault_type == "euler":
            # Euler vaults start with 'e' but NOT 'ee' (case-sensitive)
            if symbol.startswith("e") and not symbol.startswith("ee"):
                filtered_metrics.append(metric)
    
    return filtered_metrics


# Callback for EVaults section
@callback(
    [Output("evaults-section-metrics", "children"),
     Output("evaults-section-status", "children"),
     Output("evaults-section-table", "children"),
     Output("evaults-section-last-updated", "children")],
    [Input("evaults-section-refresh", "n_clicks"),
     Input("evaults-section-vault-type", "data"),
     Input("url", "pathname")],
    prevent_initial_call=False
)
def update_evaults_metrics(n_clicks, vault_type, pathname):
    """
    Update the EVaults metrics and table.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        vault_type: Selected vault type ("twyne" or "euler")
        pathname: Current URL path
        
    Returns:
        Tuple of (metrics_cards, status_message, table_component, last_updated_text)
    """
    # Only update if we're on the EVaults page
    if pathname != "/evaults":
        return [], "", "", ""
    
    logger.info("Updating EVaults metrics...")
    
    # Fetch the data
    data = fetch_evaults_data()
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        table_component = ErrorState(
            error_message="Unable to load table data due to API error",
            retry_callback="evaults-section-refresh"
        )
    else:
        status_message = dbc.Alert(
            "Data loaded successfully", 
            color="success",
            dismissable=True,
            duration=3000  # Auto-dismiss after 3 seconds
        )
        
        # Filter metrics by vault type
        filtered_metrics = filter_evaults_by_type(data["metrics"], vault_type)
        
        # Calculate summary metrics with proper scaling using filtered data
        total_assets_usd = 0.0
        total_borrows_usd = 0.0
        
        for m in filtered_metrics:
            # Sum total assets USD
            if m.totalAssetsUsd != "0":
                assets_usd_raw = float(m.totalAssetsUsd)
                # Scale by 1e18 if value is very large
                assets_usd_scaled = assets_usd_raw / 1e18 if assets_usd_raw > 1e12 else assets_usd_raw
                total_assets_usd += assets_usd_scaled
            
            # Sum total borrows USD
            if m.totalBorrowsUsd != "0":
                borrows_usd_raw = float(m.totalBorrowsUsd)
                # Scale by 1e18 if value is very large
                borrows_usd_scaled = borrows_usd_raw / 1e18 if borrows_usd_raw > 1e12 else borrows_usd_raw
                total_borrows_usd += borrows_usd_scaled
        avg_utilization = 0.0
        if filtered_metrics:
            utilization_rates = []
            for m in filtered_metrics:
                total_assets = float(m.totalAssets) if m.totalAssets != "0" else 0.0
                total_borrows = float(m.totalBorrows) if m.totalBorrows != "0" else 0.0
                if total_assets > 0:
                    utilization_rates.append(total_borrows / total_assets * 100)
            avg_utilization = sum(utilization_rates) / len(utilization_rates) if utilization_rates else 0.0
        
        # Create metrics cards using filtered data
        filtered_vault_count = len(filtered_metrics)
        vault_type_display = vault_type.capitalize()
        
        metrics_cards = dbc.Row([
            dbc.Col([
                MetricCard(
                    title=f"{vault_type_display} Vaults", 
                    value=str(filtered_vault_count),
                    icon="fas fa-coins",
                    color="primary"
                )
            ], width=12, md=6, lg=3),
            
            dbc.Col([
                MetricCard(
                    title="Total Assets (USD)", 
                    value=f"${total_assets_usd:,.2f}",
                    icon="fas fa-dollar-sign",
                    color="success"
                )
            ], width=12, md=6, lg=3),
            
            dbc.Col([
                MetricCard(
                    title="Total Borrows (USD)", 
                    value=f"${total_borrows_usd:,.2f}",
                    icon="fas fa-chart-line",
                    color="info"
                )
            ], width=12, md=6, lg=3),
            
            dbc.Col([
                MetricCard(
                    title="Avg Utilization", 
                    value=f"{avg_utilization:.2f}%",
                    icon="fas fa-percentage",
                    color="warning" if avg_utilization > 80 else "info"
                )
            ], width=12, md=6, lg=3)
        ], className="g-3")
        
        # Create table component using filtered data
        if filtered_metrics:
            table_data = format_evaults_for_table(filtered_metrics)
            table_component = html.Div([
                html.H5(f"{vault_type_display} EVaults Metrics", className="mb-3"),
                dash_table.DataTable(
                    id="evaults-metrics-table",
                    data=table_data,
                    columns=get_evaults_table_columns(),
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
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
                            'if': {
                                'filter_query': '{Utilization Rate (%)} > 80',
                                'column_id': 'Utilization Rate (%)'
                            },
                            'backgroundColor': '#ffebee',
                            'color': 'red'
                        },
                        {
                            'if': {
                                'filter_query': '{Utilization Rate (%)} > 90',
                                'column_id': 'Utilization Rate (%)'
                            },
                            'backgroundColor': '#ffcdd2',
                            'color': 'darkred',
                            'fontWeight': 'bold'
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display"
                )
            ])
        else:
            table_component = html.Div([
                html.H5(f"{vault_type_display} EVaults Metrics", className="mb-3"),
                html.P(f"No {vault_type_display} EVault metrics available", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, table_component, last_updated
