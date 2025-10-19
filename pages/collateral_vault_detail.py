"""
Collateral Vault Detail page for Risk Dashboard.
Displays historical snapshots for a specific collateral vault.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

from src.components import PageContainer, SectionCard, LoadingState, ErrorState, ErrorAlert
from src.api import api_client

# Configure logging
logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync callbacks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("Event loop is already running")
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# Register the page with Dash - using path_template for dynamic routing
dash.register_page(
    __name__, 
    path_template="/collateralVaults/<vault_address>", 
    title="Collateral Vault Detail - Risk Dashboard"
)


async def fetch_vault_chart_data(
    vault_address: str,
    days: int = 1
) -> Dict[str, Any]:
    """
    Fetch hourly snapshots for chart visualization.
    Uses the snapshots endpoint with timestamp parameter to get pre-priced snapshots.

    Args:
        vault_address: The vault address to fetch data for
        days: Number of days of history to fetch (default: 1)

    Returns:
        Dict containing chart snapshot data or error information
    """
    try:
        import time

        # Step 1: Get current timestamp
        current_timestamp = int(time.time())

        # Step 2: Create list of hourly timestamps going back N days
        hours = days * 24
        hour_in_seconds = 3600

        # Create timestamps for each hour going backwards
        timestamps = []
        for i in range(hours + 1):  # +1 to include the current hour
            timestamp = current_timestamp - (i * hour_in_seconds)
            timestamps.append(timestamp)

        # Reverse to have oldest first
        timestamps.reverse()

        logger.info(f"Fetching {len(timestamps)} hourly snapshots for chart for vault {vault_address} over {days} days")

        # Step 3: Fetch snapshots at each timestamp using the snapshots endpoint
        all_snapshots = []

        # Fetch snapshots in batches to avoid too many API calls
        # We'll fetch one snapshot per hour using the timestamp parameter
        for i, ts in enumerate(timestamps):
            try:
                response = await api_client.get_collateral_vaults_snapshots(
                    limit=1,  # We only need one snapshot per timestamp
                    vault_addresses=[vault_address],
                    timestamp=ts
                )

                if isinstance(response, dict) and "error" in response:
                    logger.warning(f"API error at timestamp {ts}: {response['error']}")
                    continue

                # Add snapshots from this timestamp
                if response.snapshots and len(response.snapshots) > 0:
                    # Only add if we got a snapshot
                    all_snapshots.extend(response.snapshots)

                # Log progress every 24 hours (24 snapshots)
                if (i + 1) % 24 == 0:
                    logger.info(f"Fetched {i + 1}/{len(timestamps)} chart snapshots...")

            except Exception as e:
                logger.warning(f"Error fetching snapshot at timestamp {ts}: {e}")
                continue

        logger.info(f"Successfully fetched {len(all_snapshots)} pre-priced snapshots for chart")

        return {
            "error": None,
            "snapshots": all_snapshots,
            "vault_address": vault_address,
            "days": days,
            "timestamps_requested": len(timestamps),
            "snapshots_received": len(all_snapshots)
        }

    except Exception as e:
        logger.error(f"Failed to fetch collateral vault chart data for {vault_address}: {e}")
        return {
            "error": str(e),
            "snapshots": []
        }


async def fetch_vault_history_events(
    vault_address: str,
    start_time: int = None,
    end_time: int = None,
) -> Dict[str, Any]:
    """
    Fetch actual position update events (transactions) for the table.
    Uses the history endpoint to get all actual vault events with state and txType.

    Args:
        vault_address: The vault address to fetch data for
        start_time: Start time in seconds since epoch
        end_time: End time in seconds since epoch

    Returns:
        Dict containing history events or error information
    """
    try:
        import time
        if end_time is None:
            end_time = int(time.time())
        if start_time is None:
            start_time = 0

        logger.info(f"Fetching history events for vault {vault_address} from {start_time} to {end_time}")

        # Fetch data using the history endpoint
        response = await api_client.get_collateral_vault_history(
            address=vault_address,
            limit=10000,  # High limit to get all events
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

        logger.info(f"Successfully fetched {len(snapshots)} history events for vault {vault_address}")

        return {
            "error": None,
            "snapshots": snapshots,
            "vault_address": vault_address,
        }

    except Exception as e:
        logger.error(f"Failed to fetch collateral vault history events for {vault_address}: {e}")
        return {
            "error": str(e),
            "snapshots": []
        }


def safe_convert_to_float_from_string(value) -> float:
    """
    Safely convert value to float, handling None values.
    API v1.2: Values are already JSON numbers (floats), just need to handle None.

    Args:
        value: Numeric value (float) or None

    Returns:
        Float value (0.0 if None)
    """
    if value is None:
        return 0.0

    # Values are already floats from API, but handle any type conversion just in case
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def safe_convert_to_float(value) -> float:
    """
    Safely convert value to float, handling None values.

    Args:
        value: Value that might be None, float, or numeric

    Returns:
        Float value (0.0 if None or invalid)
    """
    if value is None:
        return 0.0

    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def create_dataframe_from_snapshots(snapshots: List) -> pd.DataFrame:
    """
    Convert CollateralVaultSnapshot objects to a pandas DataFrame.
    API v1.2: All numeric values are JSON numbers (floats/ints), pre-scaled and human-readable.

    Args:
        snapshots: List of CollateralVaultSnapshot objects

    Returns:
        pandas DataFrame with all snapshot data
    """
    if not snapshots:
        return pd.DataFrame()

    # Convert snapshots to list of dictionaries
    data = []
    for snapshot in snapshots:
        # API v1.2: All numeric values are already JSON numbers (floats/ints), pre-scaled
        # Token amounts, USD values, and LTV are all human-readable numbers
        row = {
            'chainId': str(snapshot.chainId) if snapshot.chainId else 'N/A',
            'vaultAddress': str(snapshot.vaultAddress),
            'underlyingCollateralVault': str(snapshot.underlyingCollateralVault),
            'creditVault': str(snapshot.creditVault),
            'debtVault': str(snapshot.debtVault),
            # Token amounts - already floats from API
            'maxRelease': safe_convert_to_float_from_string(snapshot.maxRelease),
            'maxRepay': safe_convert_to_float_from_string(snapshot.maxRepay),
            'totalAssetsDepositedOrReserved': safe_convert_to_float_from_string(snapshot.totalAssetsDepositedOrReserved),
            'userOwnedCollateral': safe_convert_to_float_from_string(snapshot.userOwnedCollateral),
            # LTV - already float from API (e.g., 0.75 = 75%)
            'twyneLiqLtv': safe_convert_to_float_from_string(snapshot.twyneLiqLtv),
            'canLiquidate': bool(snapshot.canLiquidate),
            'isExternallyLiquidated': bool(snapshot.isExternallyLiquidated),
            # USD values - already floats from API
            'maxReleaseUsd': safe_convert_to_float(snapshot.maxReleaseUsd),
            'maxRepayUsd': safe_convert_to_float(snapshot.maxRepayUsd),
            'totalAssetsDepositedOrReservedUsd': safe_convert_to_float(snapshot.totalAssetsDepositedOrReservedUsd),
            'userOwnedCollateralUsd': safe_convert_to_float(snapshot.userOwnedCollateralUsd),
            # Block info - already integers from API
            'blockNumber': snapshot.blockNumber,
            'blockTimestamp': snapshot.blockTimestamp,
            'logIndex': snapshot.logIndex,
            # State info
            'state': str(snapshot.state) if snapshot.state else 'post',  # Default to 'post' as snapshots endpoint only returns post-state
            'txType': str(snapshot.txType) if snapshot.txType else 'N/A'
        }
        data.append(row)

    # Create DataFrame
    df = pd.DataFrame(data)

    return df


def create_usd_progression_from_priced_snapshots(
    plot_df: pd.DataFrame
) -> Tuple[Optional[go.Figure], List[str]]:
    """
    Create a line plot showing USD progression from pre-priced snapshots.
    Snapshots already contain USD values calculated by the API.

    Args:
        plot_df: Snapshot DataFrame

    Returns:
        Tuple of (plotly figure or None, error messages list)
    """
    errors = []

    try:
        # Create the plot
        fig = go.Figure()

        # Add traces for each metric
        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['maxReleaseUsd'],
            mode='lines+markers',
            name='Max Release (USD)',
            line=dict(color='#2E8B57', width=2),
            marker=dict(size=4),
            hovertemplate='<b>Max Release</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['maxRepayUsd'],
            mode='lines+markers',
            name='Max Repay (USD)',
            line=dict(color='#DC143C', width=2),
            marker=dict(size=4),
            hovertemplate='<b>Max Repay</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))

        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['userOwnedCollateralUsd'],
            mode='lines+markers',
            name='User Collateral (USD)',
            line=dict(color='#4169E1', width=2),
            marker=dict(size=4),
            hovertemplate='<b>User Collateral</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        ))

        # Update layout
        fig.update_layout(
            title={
                'text': 'Vault Position USD Value Over Time (Pre-priced by API)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            xaxis_title='Date',
            yaxis_title='USD Value',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=80, b=50),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.5)'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.5)',
                tickformat='$,.0f'
            ),
            height=500
        )

        logger.info(f"Created USD progression chart with {len(plot_df)} data points")
        return fig, errors

    except Exception as e:
        error_msg = f"Failed to create USD progression chart: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, [error_msg]


def format_dataframe_for_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Format DataFrame for Dash DataTable display.
    API v1.2: All values are already JSON numbers, scaled and human-readable.

    Args:
        df: pandas DataFrame with vault snapshot data

    Returns:
        List of dictionaries formatted for DataTable
    """
    if df.empty:
        return []

    # Create a copy for formatting
    display_df = df.copy()

    # USD values are already floats from the API, no conversion needed
    usd_columns = ['maxReleaseUsd', 'maxRepayUsd', 'totalAssetsDepositedOrReservedUsd', 'userOwnedCollateralUsd']
    for col in usd_columns:
        if col in display_df.columns:
            display_df[f'{col}_formatted'] = display_df[col]

    # Format Twyne LTV as percentage
    # API v1.2: LTV is already a scaled float (e.g., 0.75 = 75%), just multiply by 100 for percentage
    if 'twyneLiqLtv' in display_df.columns:
        display_df['twyneLiqLtv_percentage'] = display_df['twyneLiqLtv'] * 100
    
    # Format timestamp for display
    if 'blockTimestamp_datetime' in display_df.columns:
        display_df['blockTimestamp_formatted'] = display_df['blockTimestamp_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Select and rename columns for display
    table_data = []
    for _, row in display_df.iterrows():
        formatted_row = {
            'Block Number': int(row['blockNumber']),
            'Block Timestamp': row.get('blockTimestamp_formatted', ''),
            'Chain ID': row.get('chainId', 'N/A'),
            'State': row.get('state', 'N/A'),
            'TX Type': row.get('txType', 'N/A'),
            'Credit Vault': row['creditVault'],
            'Debt Vault': row['debtVault'],
            'Max Release (USD)': row.get('maxReleaseUsd_formatted', 0.0),
            'Max Repay (USD)': row.get('maxRepayUsd_formatted', 0.0),
            'Total Assets (USD)': row.get('totalAssetsDepositedOrReservedUsd_formatted', 0.0),
            'User Collateral (USD)': row.get('userOwnedCollateralUsd_formatted', 0.0),
            'Twyne Liq LTV (%)': row.get('twyneLiqLtv_percentage', 0.0),
            'Can Liquidate': 'Yes' if row['canLiquidate'] else 'No',
            'Externally Liquidated': 'Yes' if row['isExternallyLiquidated'] else 'No',
            'Log Index': int(row['logIndex'])
        }
        table_data.append(formatted_row)
    
    return table_data


def get_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the vault history table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "State", "id": "State"},
        {"name": "TX Type", "id": "TX Type"},
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
            
            # USD Progression Chart section
            SectionCard(
                title="Historical USD Value Progression",
                icon="fas fa-chart-line",
                children=[
                    # Chart status message container
                    html.Div(id="collateral-vault-chart-status", className="mb-3"),
                    
                    # Chart container
                    html.Div(id="collateral-vault-chart", className="mb-3"),
                ]
            ),
            
            # Data table section
            SectionCard(
                title="Vault History (Transaction Events)",
                icon="fas fa-history",
                action_button=dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                    id="collateral-vault-detail-refresh",
                    color="outline-primary",
                    size="sm"
                ),
                children=[
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


# Main callback for collateral vault detail page
@callback(
    [Output("collateral-vault-chart-status", "children"),
     Output("collateral-vault-chart", "children"),
     Output("collateral-vault-detail-status", "children"),
     Output("collateral-vault-detail-table", "children"),
     Output("collateral-vault-detail-last-updated", "children")],
    [Input("collateral-vault-detail-refresh", "n_clicks"),
     Input("collateral-vault-detail-url", "pathname")],
    [State("collateral-vault-address-store", "data")],
    prevent_initial_call=False
)
def update_collateral_vault_detail(n_clicks_refresh, pathname, vault_address):
    """
    Update the collateral vault detail chart and table.
    Chart uses hourly snapshots, table uses actual transaction events.

    Args:
        n_clicks_refresh: Number of times refresh button was clicked
        pathname: Current URL path
        vault_address: Vault address from store

    Returns:
        Tuple of (chart_status, chart_component, table_status, table_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/collateralVaults/"):
        return "", "", "", "", ""

    logger.info(f"Loading vault data for {vault_address}")

    # Fetch both chart data (hourly snapshots) and history events (actual transactions)
    chart_data = run_async(fetch_vault_chart_data(vault_address, days=1))
    history_data = run_async(fetch_vault_history_events(vault_address))

    # Check for errors in chart data
    chart_component = ""
    chart_status = ""

    if chart_data["error"]:
        chart_status = ErrorAlert(
            message=f"Failed to fetch chart data: {chart_data['error']}",
            title="Chart Error"
        )
        chart_component = ""

    # Check for errors in history data
    if history_data["error"]:
        error_status = ErrorAlert(
            message=f"Failed to fetch history data: {history_data['error']}",
            title="API Error"
        )
        error_table = ErrorState(
            error_message="Unable to load history data due to API error",
            retry_callback="collateral-vault-detail-refresh"
        )
        return chart_status, chart_component, error_status, error_table, ""

    # Create USD progression chart using hourly snapshots from chart_data
    if not chart_data["error"] and chart_data["snapshots"]:

        snapshots = chart_data["snapshots"]
        data = []
        for snapshot in snapshots:
            # API v1.2: All numeric values are already JSON numbers (floats/ints), pre-scaled
            # Token amounts, USD values, and LTV are all human-readable numbers
            row = {
                'chainId': str(snapshot.chainId) if snapshot.chainId else 'N/A',
                'vaultAddress': str(snapshot.vaultAddress),
                'underlyingCollateralVault': str(snapshot.underlyingCollateralVault),
                'creditVault': str(snapshot.creditVault),
                'debtVault': str(snapshot.debtVault),
                # Token amounts - already floats from API
                'maxRelease': safe_convert_to_float_from_string(snapshot.maxRelease),
                'maxRepay': safe_convert_to_float_from_string(snapshot.maxRepay),
                'totalAssetsDepositedOrReserved': safe_convert_to_float_from_string(snapshot.totalAssetsDepositedOrReserved),
                'userOwnedCollateral': safe_convert_to_float_from_string(snapshot.userOwnedCollateral),
                # LTV - already float from API (e.g., 0.75 = 75%)
                'twyneLiqLtv': safe_convert_to_float_from_string(snapshot.twyneLiqLtv),
                'canLiquidate': bool(snapshot.canLiquidate),
                'isExternallyLiquidated': bool(snapshot.isExternallyLiquidated),
                # USD values - already floats from API
                'maxReleaseUsd': safe_convert_to_float(snapshot.maxReleaseUsd),
                'maxRepayUsd': safe_convert_to_float(snapshot.maxRepayUsd),
                'totalAssetsDepositedOrReservedUsd': safe_convert_to_float(snapshot.totalAssetsDepositedOrReservedUsd),
                'userOwnedCollateralUsd': safe_convert_to_float(snapshot.userOwnedCollateralUsd),
                # Block info - already integers from API
                'blockNumber': snapshot.creditVaultPriceBlock,
                'blockTimestamp': snapshot.creditVaultPriceTimestamp,
                'logIndex': snapshot.logIndex,
                # State info
                'state': str(snapshot.state) if snapshot.state else 'post',  # Default to 'post' as snapshots endpoint only returns post-state
                'txType': str(snapshot.txType) if snapshot.txType else 'N/A'
            }
            data.append(row)

        # Create DataFrame
        df_snapshots = pd.DataFrame(data)
        df_snapshots = df_snapshots[df_snapshots['state'] == 'post'].copy()
        df_snapshots['datetime'] = pd.to_datetime(df_snapshots['blockTimestamp'], unit='s')

        # Create the USD progression chart (no EVault data needed)
        fig, chart_errors = create_usd_progression_from_priced_snapshots(df_snapshots)

        if fig is None:
            chart_status = dbc.Alert(
                f"Chart creation failed: {'; '.join(chart_errors) if chart_errors else 'Unknown error'}",
                color="warning"
            )
            chart_component = html.Div([
                html.P("Unable to create USD progression chart", className="text-muted text-center p-4")
            ])
        else:
            chart_status = dbc.Alert(
                f"USD progression chart loaded from {len(df_snapshots)} hourly snapshots ({chart_data.get('days', 1)}-day view)",
                color="success",
                dismissable=True,
                duration=4000
            )
            if chart_errors:
                chart_status = html.Div([
                    chart_status,
                    dbc.Alert(
                        f"Warnings: {'; '.join(chart_errors[:3])}{'...' if len(chart_errors) > 3 else ''}",
                        color="warning",
                        dismissable=True
                    )
                ])

            chart_component = dcc.Graph(
                figure=fig,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                }
            )
    else:
        if not chart_status:  # Only set if not already set by error
            chart_status = dbc.Alert(
                "No snapshots available for chart creation",
                color="warning"
            )
        if not chart_component:  # Only set if not already set
            chart_component = html.Div([
                html.P("No snapshot data available for chart", className="text-muted text-center p-4")
            ])

    
    # Convert history events to DataFrame for the table
    df_history = create_dataframe_from_snapshots(history_data["snapshots"])

    if df_history.empty:
        warning_status = dbc.Alert(
            "No transaction history available for this vault",
            color="warning"
        )
        empty_table = html.Div([
            html.H5("Vault History", className="mb-3"),
            html.P("No transaction history available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return chart_status, chart_component, warning_status, empty_table, last_updated

    df_history['datetime'] = pd.to_datetime(df_history['blockTimestamp'], unit='s')

    if df_history.empty:
        warning_status = dbc.Alert(
            f"Loaded {len(df_history)} total events",
            color="warning"
        )
        empty_table = html.Div([
            html.H5("Vault History (Post State Events)", className="mb-3"),
            html.P("No 'post' state events available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return chart_status, chart_component, warning_status, empty_table, last_updated

    # Sort by block number descending (most recent first) for table display
    df_history = df_history.sort_values('blockNumber', ascending=False)
    
    # Create table status message
    table_status = dbc.Alert(
        f"Loaded {len(df_history)} transaction events",
        color="success",
        dismissable=True,
        duration=4000
    )

    # Format data for table (using post_df - actual transaction events)
    table_data = format_dataframe_for_table(df_history)
    
    # Create table component
    table_component = html.Div([
        html.H5("Vault History (Transaction Events)", className="mb-3"),
        dash_table.DataTable(
            id="collateral-vault-history-table",
            data=table_data,
            columns=get_table_columns(),
            page_size=25,
            sort_action="native",
            filter_action="native",
            sort_by=[{"column_id": "Block Number", "direction": "desc"}],
            style_cell={
                'textAlign': 'left',
                'padding': '12px',
                'fontFamily': 'Arial, sans-serif',
                'fontSize': '14px',
                'whiteSpace': 'nowrap',
                'height': 'auto',
                'maxWidth': '200px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis'
            },
            style_cell_conditional=[
                {
                    'if': {'column_id': ['Credit Vault', 'Debt Vault']},
                    'maxWidth': '120px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'nowrap'
                }
            ],
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
            export_headers="display"
        )
    ])

    # Last updated timestamp
    last_updated = f"Showing {len(df_history)} transaction events - Updated: {datetime.now().strftime('%H:%M:%S')}"

    return chart_status, chart_component, table_status, table_component, last_updated