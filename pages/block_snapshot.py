"""
Block Snapshot page for the Risk Dashboard.
Allows users to create snapshots of all collateral vaults at specific blocks.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from src.api.block_snapshot_client import block_snapshot_client
from src.utils.block_snapshot import format_block_snapshot_for_table
from src.components import PageContainer, LoadingSpinner, MetricCard

logger = logging.getLogger(__name__)

# Register the page
dash.register_page(
    __name__,
    path="/block-snapshot",
    title="Block Snapshot - Risk Dashboard",
    name="Block Snapshot - Risk Dashboard"
)


def create_block_input_section() -> dbc.Card:
    """Create the block input section."""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("Block Snapshot Configuration", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Block Number", html_for="block-number-input"),
                    dbc.Input(
                        id="block-number-input",
                        type="number",
                        placeholder="Enter block number (e.g., 19000000)",
                        value=19000000,
                        min=1,
                        step=1
                    ),
                    dbc.FormText("Enter the block number to create a snapshot for")
                ], md=6),
                dbc.Col([
                    dbc.Label("Quick Select", html_for="quick-block-select"),
                    dbc.ButtonGroup([
                        dbc.Button("Latest - 1000", id="latest-1000-btn", outline=True, color="primary", size="sm"),
                        dbc.Button("Latest - 10000", id="latest-10000-btn", outline=True, color="primary", size="sm"),
                        dbc.Button("Latest - 100000", id="latest-100000-btn", outline=True, color="primary", size="sm")
                    ], vertical=False),
                    dbc.FormText("Quick select relative to latest block")
                ], md=6)
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "Create Snapshot",
                        id="create-snapshot-btn",
                        color="success",
                        size="lg",
                        className="me-2"
                    ),
                    dbc.Button(
                        "Get Summary Only",
                        id="get-summary-btn",
                        color="info",
                        outline=True,
                        size="lg"
                    )
                ])
            ])
        ])
    ])


def create_snapshot_results_section() -> html.Div:
    """Create the results display section."""
    return html.Div([
        # Status and loading
        html.Div(id="snapshot-status"),
        
        # Summary metrics
        html.Div(id="snapshot-metrics", className="mb-4"),
        
        # Detailed table
        html.Div(id="snapshot-table"),
        
        # Last updated timestamp
        html.Div(id="snapshot-last-updated", className="text-muted mt-3")
    ])


def create_comparison_section() -> dbc.Card:
    """Create the block comparison section."""
    return dbc.Card([
        dbc.CardHeader([
            html.H4("Block Comparison", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Block 1", html_for="compare-block1-input"),
                    dbc.Input(
                        id="compare-block1-input",
                        type="number",
                        placeholder="First block",
                        min=1,
                        step=1
                    )
                ], md=4),
                dbc.Col([
                    dbc.Label("Block 2", html_for="compare-block2-input"),
                    dbc.Input(
                        id="compare-block2-input",
                        type="number",
                        placeholder="Second block",
                        min=1,
                        step=1
                    )
                ], md=4),
                dbc.Col([
                    dbc.Label(" ", html_for="compare-btn"),
                    dbc.Button(
                        "Compare Blocks",
                        id="compare-blocks-btn",
                        color="primary",
                        className="w-100"
                    )
                ], md=4)
            ])
        ])
    ])


def layout():
    """Create the main layout for the block snapshot page."""
    return PageContainer(
        title="Block Snapshot",
        subtitle="Create comprehensive snapshots of all collateral vaults at specific blocks",
        children=[
            # Block input section
            create_block_input_section(),
            
            html.Hr(),
            
            # Results section
            create_snapshot_results_section(),
            
            html.Hr(),
            
            # Comparison section
            create_comparison_section(),
            
            html.Div(id="comparison-results", className="mt-4"),
            
            # Store components
            dcc.Store(id="current-snapshot-data"),
            dcc.Store(id="comparison-data")
        ]
    )


def format_snapshot_metrics(summary: Dict[str, Any]) -> html.Div:
    """Format snapshot summary into metric cards."""
    if not summary or 'successful_snapshots' not in summary:
        return html.Div([
            dbc.Alert("No snapshot data available", color="warning")
        ])
    
    return dbc.Row([
        dbc.Col([
            MetricCard(
                title="Target Block",
                value=f"{summary['target_block']:,}",
                subtitle=f"Timestamp: {summary.get('formatted_timestamp', 'Unknown')}"
            )
        ], md=3),
        dbc.Col([
            MetricCard(
                title="Successful Snapshots",
                value=f"{summary['successful_snapshots']:,}",
                subtitle=f"Out of {summary['total_vaults_discovered']:,} discovered vaults"
            )
        ], md=3),
        dbc.Col([
            MetricCard(
                title="Total Assets",
                value=f"${summary['total_assets_usd']:,.2f}",
                subtitle="USD value at snapshot block"
            )
        ], md=3),
        dbc.Col([
            MetricCard(
                title="Total Collateral",
                value=f"${summary['total_user_collateral_usd']:,.2f}",
                subtitle="User-owned collateral value"
            )
        ], md=3)
    ], className="mb-4")


def format_snapshot_table(block_snapshot) -> html.Div:
    """Format snapshot data into a table."""
    if not block_snapshot or not block_snapshot.vault_snapshots:
        return html.Div([
            dbc.Alert("No vault snapshots available", color="info")
        ])
    
    # Format data for table
    table_data = format_block_snapshot_for_table(block_snapshot)
    
    if not table_data:
        return html.Div([
            dbc.Alert("No data to display", color="info")
        ])
    
    # Define columns for the table
    columns = [
        {"name": "Vault Address", "id": "Vault Address", "type": "text"},
        {"name": "Credit Vault", "id": "Credit Vault", "type": "text"},
        {"name": "Debt Vault", "id": "Debt Vault", "type": "text"},
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Twyne Liq LTV (%)", "id": "Twyne Liq LTV (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Can Liquidate", "id": "Can Liquidate", "type": "text"},
        {"name": "Snapshot Block", "id": "Snapshot Block", "type": "numeric"},
        {"name": "Credit Price", "id": "Credit Price", "type": "numeric", "format": {"specifier": "$,.6f"}},
        {"name": "Debt Price", "id": "Debt Price", "type": "numeric", "format": {"specifier": "$,.6f"}}
    ]
    
    return html.Div([
        html.H5(f"Vault Snapshots ({len(table_data)} vaults)", className="mb-3"),
        dash_table.DataTable(
            data=table_data,
            columns=columns,
            page_size=20,
            sort_action="native",
            filter_action="native",
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{Has Pricing Errors} = true'},
                    'backgroundColor': '#ffeeee',
                    'color': 'black',
                }
            ]
        )
    ])


# Callbacks
@callback(
    [Output("snapshot-status", "children"),
     Output("snapshot-metrics", "children"),
     Output("snapshot-table", "children"),
     Output("snapshot-last-updated", "children"),
     Output("current-snapshot-data", "data")],
    [Input("create-snapshot-btn", "n_clicks"),
     Input("get-summary-btn", "n_clicks")],
    [State("block-number-input", "value")],
    prevent_initial_call=True
)
def create_block_snapshot(create_clicks, summary_clicks, block_number):
    """Create a block snapshot based on user input."""
    if not block_number:
        return (
            dbc.Alert("Please enter a block number", color="warning"),
            html.Div(),
            html.Div(),
            html.Div(),
            None
        )
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    try:
        # Show loading
        loading_status = LoadingSpinner(f"Creating snapshot for block {block_number:,}...")
        
        if trigger_id == "get-summary-btn":
            # Get summary only
            logger.info(f"Getting snapshot summary for block {block_number}")
            summary = block_snapshot_client.get_snapshot_summary(block_number)
            
            if 'successful_snapshots' not in summary:
                return (
                    dbc.Alert(f"Failed to get snapshot summary: {summary.get('error', 'Unknown error')}", color="danger"),
                    html.Div(),
                    html.Div(),
                    html.Div(),
                    None
                )
            
            metrics = format_snapshot_metrics(summary)
            
            return (
                dbc.Alert(f"Snapshot summary created for block {block_number:,}", color="success"),
                metrics,
                html.Div([
                    dbc.Alert("Summary only - click 'Create Snapshot' for full table data", color="info")
                ]),
                html.P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="text-muted"),
                summary
            )
        
        else:
            # Create full snapshot
            logger.info(f"Creating full snapshot for block {block_number}")
            block_snapshot = block_snapshot_client.create_snapshot_at_block(block_number)
            
            if not block_snapshot or not hasattr(block_snapshot, 'vault_snapshots'):
                return (
                    dbc.Alert(f"Failed to create snapshot for block {block_number}", color="danger"),
                    html.Div(),
                    html.Div(),
                    html.Div(),
                    None
                )
            
            summary = {
                'target_block': block_snapshot.target_block,
                'timestamp': block_snapshot.timestamp,
                'formatted_timestamp': datetime.fromtimestamp(block_snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S") if block_snapshot.timestamp else None,
                'total_vaults_discovered': block_snapshot.total_vaults,
                'successful_snapshots': len(block_snapshot.vault_snapshots),
                'total_assets_usd': sum(vs['calculated_usd_values'].get('total_assets_usd', 0.0) for vs in block_snapshot.vault_snapshots),
                'total_user_collateral_usd': sum(vs['calculated_usd_values'].get('user_collateral_usd', 0.0) for vs in block_snapshot.vault_snapshots),
                'pricing_errors_count': len(block_snapshot.pricing_errors),
                'fetch_errors_count': len(block_snapshot.fetch_errors)
            }
            
            metrics = format_snapshot_metrics(summary)
            table = format_snapshot_table(block_snapshot)
            
            # Create status with warnings if any
            status_alerts = []
            if block_snapshot.pricing_errors:
                status_alerts.append(
                    dbc.Alert(f"Warning: {len(block_snapshot.pricing_errors)} pricing errors occurred", color="warning")
                )
            if block_snapshot.fetch_errors:
                status_alerts.append(
                    dbc.Alert(f"Warning: {len(block_snapshot.fetch_errors)} fetch errors occurred", color="warning")
                )
            
            status_alerts.append(
                dbc.Alert(f"Snapshot created for block {block_number:,} with {len(block_snapshot.vault_snapshots)} vaults", color="success")
            )
            
            return (
                html.Div(status_alerts),
                metrics,
                table,
                html.P(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", className="text-muted"),
                summary
            )
    
    except Exception as e:
        logger.error(f"Error creating snapshot for block {block_number}: {str(e)}", exc_info=True)
        return (
            dbc.Alert(f"Error creating snapshot: {str(e)}", color="danger"),
            html.Div(),
            html.Div(),
            html.Div(),
            None
        )


@callback(
    Output("block-number-input", "value"),
    [Input("latest-1000-btn", "n_clicks"),
     Input("latest-10000-btn", "n_clicks"),
     Input("latest-100000-btn", "n_clicks")],
    prevent_initial_call=True
)
def set_quick_block(btn1, btn2, btn3):
    """Set block number based on quick select buttons."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # For demo purposes, using approximate block numbers
    # In production, you'd fetch the latest block from the blockchain
    latest_block = 21000000  # Approximate current block
    
    if trigger_id == "latest-1000-btn":
        return latest_block - 1000
    elif trigger_id == "latest-10000-btn":
        return latest_block - 10000
    elif trigger_id == "latest-100000-btn":
        return latest_block - 100000
    
    return dash.no_update


@callback(
    Output("comparison-results", "children"),
    [Input("compare-blocks-btn", "n_clicks")],
    [State("compare-block1-input", "value"),
     State("compare-block2-input", "value")],
    prevent_initial_call=True
)
def compare_blocks(n_clicks, block1, block2):
    """Compare two blocks."""
    if not block1 or not block2:
        return dbc.Alert("Please enter both block numbers", color="warning")
    
    if block1 == block2:
        return dbc.Alert("Please enter different block numbers", color="warning")
    
    try:
        logger.info(f"Comparing blocks {block1} and {block2}")
        
        # Show loading
        loading_div = LoadingSpinner(f"Comparing blocks {block1:,} and {block2:,}...")
        
        comparison = block_snapshot_client.compare_blocks(block1, block2)
        
        if not comparison['success']:
            return dbc.Alert(f"Comparison failed: {comparison.get('error', 'Unknown error')}", color="danger")
        
        summary1 = comparison['snapshot1']
        summary2 = comparison['snapshot2']
        differences = comparison['differences']
        
        return dbc.Card([
            dbc.CardHeader([
                html.H5(f"Block Comparison: {block1:,} vs {block2:,}")
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6(f"Block {block1:,}"),
                        html.P(f"Vaults: {summary1['successful_snapshots']:,}"),
                        html.P(f"Assets: ${summary1['total_assets_usd']:,.2f}"),
                        html.P(f"Collateral: ${summary1['total_user_collateral_usd']:,.2f}")
                    ], md=4),
                    dbc.Col([
                        html.H6("Differences"),
                        html.P(f"Vault Change: {differences['vault_count_change']:+,}"),
                        html.P(f"Assets Change: ${differences['total_assets_change_usd']:+,.2f} ({differences['percentage_assets_change']:+.2f}%)"),
                        html.P(f"Collateral Change: ${differences['total_collateral_change_usd']:+,.2f} ({differences['percentage_collateral_change']:+.2f}%)")
                    ], md=4),
                    dbc.Col([
                        html.H6(f"Block {block2:,}"),
                        html.P(f"Vaults: {summary2['successful_snapshots']:,}"),
                        html.P(f"Assets: ${summary2['total_assets_usd']:,.2f}"),
                        html.P(f"Collateral: ${summary2['total_user_collateral_usd']:,.2f}")
                    ], md=4)
                ])
            ])
        ])
        
    except Exception as e:
        logger.error(f"Error comparing blocks {block1} and {block2}: {str(e)}", exc_info=True)
        return dbc.Alert(f"Error comparing blocks: {str(e)}", color="danger")
