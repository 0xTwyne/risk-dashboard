"""
Collateral Vault Detail page for Risk Dashboard.
Displays historical snapshots for a specific collateral vault.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc

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


async def fetch_vault_history_data(vault_address: str) -> Dict[str, Any]:
    """
    Fetch all historical events for a specific collateral vault.
    
    Args:
        vault_address: The vault address to fetch data for
        
    Returns:
        Dict containing history data or error information
    """
    try:
        logger.info(f"Fetching all historical data for collateral vault: {vault_address}")
        
        # Fetch all data using the API client with a high limit
        response = await api_client.get_collateral_vault_history(
            address=vault_address,
            limit=10000  # High limit to get all events
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


def create_dataframe_from_snapshots(snapshots: List) -> pd.DataFrame:
    """
    Convert CollateralVaultSnapshot objects to a pandas DataFrame.
    
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
        # Convert snapshot to dictionary using all fields from CollateralVaultSnapshot
        row = {
            'chainId': snapshot.chainId,
            'vaultAddress': snapshot.vaultAddress,
            'underlyingCollateralVault': snapshot.underlyingCollateralVault,
            'creditVault': snapshot.creditVault,
            'debtVault': snapshot.debtVault,
            'maxRelease': snapshot.maxRelease,
            'maxRepay': snapshot.maxRepay,
            'totalAssetsDepositedOrReserved': snapshot.totalAssetsDepositedOrReserved,
            'userOwnedCollateral': snapshot.userOwnedCollateral,
            'twyneLiqLtv': snapshot.twyneLiqLtv,
            'canLiquidate': snapshot.canLiquidate,
            'isExternallyLiquidated': snapshot.isExternallyLiquidated,
            'maxReleaseUsd': snapshot.maxReleaseUsd,
            'maxRepayUsd': snapshot.maxRepayUsd,
            'totalAssetsDepositedOrReservedUsd': snapshot.totalAssetsDepositedOrReservedUsd,
            'userOwnedCollateralUsd': snapshot.userOwnedCollateralUsd,
            'blockNumber': snapshot.blockNumber,
            'blockTimestamp': snapshot.blockTimestamp,
            'logIndex': snapshot.logIndex,
            'state': snapshot.state,
            'txType': snapshot.txType
        }
        data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Convert numeric columns to appropriate types
    numeric_columns = [
        'maxRelease', 'maxRepay', 'totalAssetsDepositedOrReserved', 
        'userOwnedCollateral', 'twyneLiqLtv', 'maxReleaseUsd', 'maxRepayUsd',
        'totalAssetsDepositedOrReservedUsd', 'userOwnedCollateralUsd',
        'blockNumber', 'blockTimestamp', 'logIndex'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert timestamp to datetime for better display
    if 'blockTimestamp' in df.columns:
        df['blockTimestamp_datetime'] = pd.to_datetime(df['blockTimestamp'], unit='s')
    
    return df


def format_dataframe_for_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Format DataFrame for Dash DataTable display.
    
    Args:
        df: pandas DataFrame with vault snapshot data
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if df.empty:
        return []
    
    # Create a copy for formatting
    display_df = df.copy()
    
    # Format USD values (convert from wei to dollars)
    usd_columns = ['maxReleaseUsd', 'maxRepayUsd', 'totalAssetsDepositedOrReservedUsd', 'userOwnedCollateralUsd']
    for col in usd_columns:
        if col in display_df.columns:
            display_df[f'{col}_formatted'] = display_df[col] / 1e18
    
    # Format Twyne LTV as percentage
    if 'twyneLiqLtv' in display_df.columns:
        display_df['twyneLiqLtv_percentage'] = (display_df['twyneLiqLtv'] / 1e4) * 100
    
    # Format timestamp for display
    if 'blockTimestamp_datetime' in display_df.columns:
        display_df['blockTimestamp_formatted'] = display_df['blockTimestamp_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Select and rename columns for display
    table_data = []
    for _, row in display_df.iterrows():
        formatted_row = {
            'Block Number': int(row['blockNumber']),
            'Block Timestamp': row.get('blockTimestamp_formatted', ''),
            'Chain ID': row['chainId'],
            'State': row['state'],
            'TX Type': row['txType'],
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
            
            # Data table section
            SectionCard(
                title="Vault History (Post State Events)",
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
    [Output("collateral-vault-detail-status", "children"),
     Output("collateral-vault-detail-table", "children"),
     Output("collateral-vault-detail-last-updated", "children")],
    [Input("collateral-vault-detail-refresh", "n_clicks"),
     Input("collateral-vault-detail-url", "pathname")],
    [State("collateral-vault-address-store", "data")],
    prevent_initial_call=False
)
def update_collateral_vault_detail(n_clicks_refresh, pathname, vault_address):
    """
    Update the collateral vault detail table with post-state events.
    
    Args:
        n_clicks_refresh: Number of times refresh button was clicked
        pathname: Current URL path
        vault_address: Vault address from store
        
    Returns:
        Tuple of (status_message, table_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/collateralVaults/"):
        return "", "", ""
    
    logger.info(f"Loading vault history for {vault_address}")
    
    # Fetch all historical data
    data = run_async(fetch_vault_history_data(vault_address))
    
    # Check for errors
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        table_component = ErrorState(
            error_message="Unable to load history data due to API error",
            retry_callback="collateral-vault-detail-refresh"
        )
        last_updated = ""
        return status_message, table_component, last_updated
    
    # Convert to DataFrame
    df = create_dataframe_from_snapshots(data["snapshots"])
    
    if df.empty:
        status_message = dbc.Alert(
            "No historical data available for this vault", 
            color="warning"
        )
        table_component = html.Div([
            html.H5("Vault History", className="mb-3"),
            html.P("No history data available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return status_message, table_component, last_updated
    
    # Filter for only "post" state events
    post_df = df[df['state'] == 'post'].copy()
    
    if post_df.empty:
        status_message = dbc.Alert(
            f"Loaded {len(df)} total events, but no 'post' state events found", 
            color="warning"
        )
        table_component = html.Div([
            html.H5("Vault History (Post State Events)", className="mb-3"),
            html.P("No 'post' state events available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return status_message, table_component, last_updated
    
    # Sort by block number descending (most recent first)
    post_df = post_df.sort_values('blockNumber', ascending=False)
    
    # Create success status message
    status_message = dbc.Alert(
        f"Loaded {len(post_df)} 'post' state events out of {len(df)} total events", 
        color="success",
        dismissable=True,
        duration=4000
    )
    
    # Format data for table
    table_data = format_dataframe_for_table(post_df)
    
    # Create table component
    table_component = html.Div([
        html.H5("Vault History (Post State Events)", className="mb-3"),
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
    last_updated = f"Showing {len(post_df)} post-state events - Updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return status_message, table_component, last_updated