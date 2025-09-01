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
        
        # Extract metrics from successful response
        snapshots = response.latestSnapshots
        total_snapshots = len(snapshots)
        
        # Count unique vault addresses
        unique_vault_addresses = set()
        for snapshot in snapshots:
            unique_vault_addresses.add(snapshot.vaultAddress)
        
        unique_vaults_count = len(unique_vault_addresses)
        
        logger.info(f"Successfully processed {total_snapshots} snapshots from {unique_vaults_count} unique vaults")
        
        return {
            "error": None,
            "unique_vaults": unique_vaults_count,
            "total_snapshots": total_snapshots,
            "total_unique_vaults": getattr(response, 'totalUniqueVaults', None),
            "snapshots": snapshots
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch vault data: {e}", exc_info=True)
        return {
            "error": str(e),
            "unique_vaults": 0,
            "total_snapshots": 0,
            "snapshots": []
        }


def format_snapshots_for_table(snapshots: List) -> List[Dict[str, Any]]:
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
        # Convert snapshot to dictionary and format values
        row = {
            "Chain ID": snapshot.chainId,
            "Vault Address": snapshot.vaultAddress[:10] + "..." if len(snapshot.vaultAddress) > 10 else snapshot.vaultAddress,
            "Credit Vault": snapshot.creditVault[:10] + "..." if len(snapshot.creditVault) > 10 else snapshot.creditVault,
            "Debt Vault": snapshot.debtVault[:10] + "..." if len(snapshot.debtVault) > 10 else snapshot.debtVault,
            "Max Release (USD)": f"${float(snapshot.maxReleaseUsd):,.2f}" if snapshot.maxReleaseUsd != "0" else "$0.00",
            "Max Repay (USD)": f"${float(snapshot.maxRepayUsd):,.2f}" if snapshot.maxRepayUsd != "0" else "$0.00",
            "Total Assets (USD)": f"${float(snapshot.totalAssetsDepositedOrReservedUsd):,.2f}" if snapshot.totalAssetsDepositedOrReservedUsd != "0" else "$0.00",
            "User Collateral (USD)": f"${float(snapshot.userOwnedCollateralUsd):,.2f}" if snapshot.userOwnedCollateralUsd != "0" else "$0.00",
            "Twyne LTV": f"{float(snapshot.twyneLiqLtv):.4f}" if snapshot.twyneLiqLtv != "0" else "0.0000",
            "Can Liquidate": "Yes" if snapshot.canLiquidate else "No",
            "Externally Liquidated": "Yes" if snapshot.isExternallyLiquidated else "No",
            "Block Number": snapshot.blockNumber,
            "Block Timestamp": datetime.fromtimestamp(int(snapshot.blockTimestamp)).strftime("%Y-%m-%d %H:%M:%S")
        }
        table_data.append(row)
    
    return table_data


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
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric"},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric"},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric"},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric"},
        {"name": "Twyne LTV", "id": "Twyne LTV", "type": "numeric"},
        {"name": "Can Liquidate", "id": "Can Liquidate"},
        {"name": "Externally Liquidated", "id": "Externally Liquidated"},
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"}
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
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


def EVaultsSection(section_id: str = "evaults-section") -> html.Div:
    """
    Create the EVaults section component (placeholder for now).
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        EVaults section component
    """
    return SectionCard(
        title="EVaults",
        icon="fas fa-coins",
        children=[
            html.Div([
                html.P("EVaults metrics coming soon...", className="text-muted text-center p-4"),
                html.I(className="fas fa-tools fa-2x text-muted")
            ], className="text-center")
        ]
    )


# Callback for collateral vaults section
@callback(
    [Output("collateral-section-metrics", "children"),
     Output("collateral-section-status", "children"),
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
        Tuple of (metrics_cards, status_message, table_component, last_updated_text)
    """
    # Only update if we're on the collateral vaults page
    if pathname != "/collateralVaults":
        return [], "", "", ""
    
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
        table_component = ErrorState(
            error_message="Unable to load table data due to API error",
            retry_callback="collateral-section-refresh"
        )
    else:
        status_message = dbc.Alert(
            "Data loaded successfully", 
            color="success",
            dismissable=True,
            duration=3000  # Auto-dismiss after 3 seconds
        )
        
        # Create metrics cards
        metrics_cards = dbc.Row([
            dbc.Col([
                MetricCard(
                    title="Unique Vaults", 
                    value=str(data["unique_vaults"]),
                    icon="fas fa-vault",
                    color="primary"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="Total Snapshots", 
                    value=str(data["total_snapshots"]),
                    icon="fas fa-camera",
                    color="info"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="API Status", 
                    value="Connected" if not data["error"] else "Error",
                    icon="fas fa-plug" if not data["error"] else "fas fa-exclamation-triangle",
                    color="success" if not data["error"] else "danger"
                )
            ], width=12, md=6, lg=4)
        ], className="g-3")
        
        # Create table component
        if data["snapshots"]:
            table_data = format_snapshots_for_table(data["snapshots"])
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
    
    return metrics_cards, status_message, table_component, last_updated
