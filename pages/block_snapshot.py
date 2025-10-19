"""
Block Comparison page for the Risk Dashboard.
Allows users to compare collateral vault snapshots between two blocks.
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

import dash
from dash import html, callback, Input, Output, State
import dash_bootstrap_components as dbc

from src.api.block_snapshot_client import block_snapshot_client
from src.components import PageContainer, LoadingSpinner

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


# Register the page
dash.register_page(
    __name__,
    path="/block-snapshot",
    title="Block Comparison - Risk Dashboard",
    name="Block Comparison - Risk Dashboard"
)


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
                        placeholder="First block number",
                        min=1,
                        step=1
                    ),
                    dbc.FormText("Enter the first block number to compare")
                ], md=5),
                dbc.Col([
                    dbc.Label("Block 2", html_for="compare-block2-input"),
                    dbc.Input(
                        id="compare-block2-input",
                        type="number",
                        placeholder="Second block number",
                        min=1,
                        step=1
                    ),
                    dbc.FormText("Enter the second block number to compare")
                ], md=5),
                dbc.Col([
                    dbc.Label(" ", html_for="compare-btn"),
                    dbc.Button(
                        "Compare Blocks",
                        id="compare-blocks-btn",
                        color="primary",
                        size="lg",
                        className="w-100"
                    )
                ], md=2)
            ])
        ])
    ], className="mb-4")


def layout():
    """Create the main layout for the block comparison page."""
    return PageContainer(
        title="Block Comparison",
        subtitle="Compare collateral vault snapshots between two blocks",
        children=[
            # Comparison section
            create_comparison_section(),
            
            # Results section
            html.Div(id="comparison-results", className="mt-4")
        ]
    )


async def fetch_snapshots_at_block(block_number: int) -> Dict[str, Any]:
    """
    Fetch snapshot aggregates at a specific block using the API.

    Args:
        block_number: Block number to fetch snapshots for

    Returns:
        Dict with snapshot aggregates and metadata
    """
    from src.api import api_client

    try:
        response = await api_client.get_collateral_vaults_snapshots(
            limit=100,
            block_number=block_number
        )

        if isinstance(response, dict) and "error" in response:
            return {"success": False, "error": response["error"]}

        # Get aggregates from response
        aggregates = response.aggregates or {}

        # Get block timestamp from first snapshot if available
        block_timestamp = None
        if response.snapshots:
            block_timestamp = int(response.snapshots[0].blockTimestamp)

        # Convert snapshot_block to int safely
        try:
            snapshot_block_int = int(response.snapshotBlock) if response.snapshotBlock else block_number
        except (ValueError, TypeError):
            snapshot_block_int = block_number

        return {
            "success": True,
            "block_number": block_number,
            "block_timestamp": block_timestamp,
            "snapshot_block": snapshot_block_int,
            "successful_snapshots": aggregates.get("uniqueVaults", 0),
            "total_assets_usd": aggregates.get("totalAssetsDepositedOrReservedUsd", 0.0),
            "total_user_collateral_usd": aggregates.get("totalUserOwnedCollateralUsd", 0.0),
            "total_max_release_usd": aggregates.get("totalMaxReleaseUsd", 0.0),
            "total_max_repay_usd": aggregates.get("totalMaxRepayUsd", 0.0),
        }
    except Exception as e:
        logger.error(f"Failed to fetch snapshots at block {block_number}: {e}")
        return {"success": False, "error": str(e)}


@callback(
    Output("comparison-results", "children"),
    [Input("compare-blocks-btn", "n_clicks")],
    [State("compare-block1-input", "value"),
     State("compare-block2-input", "value")],
    prevent_initial_call=True
)
def compare_blocks(n_clicks, block1, block2):
    """Compare two blocks by fetching pre-priced snapshots from API."""
    if not block1 or not block2:
        return dbc.Alert("Please enter both block numbers", color="warning")

    if block1 == block2:
        return dbc.Alert("Please enter different block numbers", color="warning")

    try:
        logger.info(f"Comparing blocks {block1} and {block2} using API snapshots...")

        # Fetch snapshots for both blocks from API
        summary1 = run_async(fetch_snapshots_at_block(block1))
        summary2 = run_async(fetch_snapshots_at_block(block2))

        if not summary1.get('success'):
            return dbc.Alert(
                f"Failed to fetch data for block {block1}: {summary1.get('error', 'Unknown error')}",
                color="danger"
            )

        if not summary2.get('success'):
            return dbc.Alert(
                f"Failed to fetch data for block {block2}: {summary2.get('error', 'Unknown error')}",
                color="danger"
            )

        # Calculate differences
        differences = {
            'vault_count_change': summary2['successful_snapshots'] - summary1['successful_snapshots'],
            'total_assets_change_usd': summary2['total_assets_usd'] - summary1['total_assets_usd'],
            'total_collateral_change_usd': summary2['total_user_collateral_usd'] - summary1['total_user_collateral_usd'],
            'total_credit_change_usd': summary2['total_max_release_usd'] - summary1['total_max_release_usd'],
            'total_debt_change_usd': summary2['total_max_repay_usd'] - summary1['total_max_repay_usd'],
        }

        # Calculate percentage changes
        differences['percentage_assets_change'] = (
            (differences['total_assets_change_usd'] / summary1['total_assets_usd'] * 100)
            if summary1['total_assets_usd'] > 0 else 0.0
        )
        differences['percentage_collateral_change'] = (
            (differences['total_collateral_change_usd'] / summary1['total_user_collateral_usd'] * 100)
            if summary1['total_user_collateral_usd'] > 0 else 0.0
        )
        differences['percentage_credit_change'] = (
            (differences['total_credit_change_usd'] / summary1['total_max_release_usd'] * 100)
            if summary1['total_max_release_usd'] > 0 else 0.0
        )
        differences['percentage_debt_change'] = (
            (differences['total_debt_change_usd'] / summary1['total_max_repay_usd'] * 100)
            if summary1['total_max_repay_usd'] > 0 else 0.0
        )
        
        # Format timestamp if available
        timestamp1 = ""
        if summary1.get('block_timestamp'):
            timestamp1 = f" ({datetime.fromtimestamp(summary1['block_timestamp']).strftime('%Y-%m-%d %H:%M:%S')})"

        timestamp2 = ""
        if summary2.get('block_timestamp'):
            timestamp2 = f" ({datetime.fromtimestamp(summary2['block_timestamp']).strftime('%Y-%m-%d %H:%M:%S')})"
        
        return dbc.Card([
            dbc.CardHeader([
                html.H5(f"Block Comparison: {block1:,} vs {block2:,}", className="mb-0")
            ]),
            dbc.CardBody([
                # Summary stats in cards
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.H6(f"Block {block1:,}{timestamp1}", className="text-primary mb-3"),
                            html.Div([
                                html.P([
                                    html.Strong("Vaults: "),
                                    html.Span(f"{summary1['successful_snapshots']:,}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Total Assets: "),
                                    html.Span(f"${summary1['total_assets_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("User Collateral: "),
                                    html.Span(f"${summary1['total_user_collateral_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Credit Reserved: "),
                                    html.Span(f"${summary1['total_max_release_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Debt: "),
                                    html.Span(f"${summary1['total_max_repay_usd']:,.2f}")
                                ], className="mb-0")
                            ])
                        ], className="p-3 border rounded bg-light")
                    ], md=4),
                    
                    dbc.Col([
                        html.Div([
                            html.H6("Differences", className="text-info mb-3"),
                            html.Div([
                                html.P([
                                    html.Strong("Vault Change: "),
                                    html.Span(
                                        f"{differences['vault_count_change']:+,}",
                                        className="text-success" if differences['vault_count_change'] >= 0 else "text-danger"
                                    )
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Assets Change: "),
                                    html.Span(
                                        f"${differences['total_assets_change_usd']:+,.2f} ({differences['percentage_assets_change']:+.2f}%)",
                                        className="text-success" if differences['total_assets_change_usd'] >= 0 else "text-danger"
                                    )
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Collateral Change: "),
                                    html.Span(
                                        f"${differences['total_collateral_change_usd']:+,.2f} ({differences['percentage_collateral_change']:+.2f}%)",
                                        className="text-success" if differences['total_collateral_change_usd'] >= 0 else "text-danger"
                                    )
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Credit Change: "),
                                    html.Span(
                                        f"${differences['total_credit_change_usd']:+,.2f} ({differences['percentage_credit_change']:+.2f}%)",
                                        className="text-success" if differences['total_credit_change_usd'] >= 0 else "text-danger"
                                    )
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Debt Change: "),
                                    html.Span(
                                        f"${differences['total_debt_change_usd']:+,.2f} ({differences['percentage_debt_change']:+.2f}%)",
                                        className="text-success" if differences['total_debt_change_usd'] >= 0 else "text-danger"
                                    )
                                ], className="mb-0")
                            ])
                        ], className="p-3 border rounded bg-light")
                    ], md=4),
                    
                    dbc.Col([
                        html.Div([
                            html.H6(f"Block {block2:,}{timestamp2}", className="text-primary mb-3"),
                            html.Div([
                                html.P([
                                    html.Strong("Vaults: "),
                                    html.Span(f"{summary2['successful_snapshots']:,}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Total Assets: "),
                                    html.Span(f"${summary2['total_assets_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("User Collateral: "),
                                    html.Span(f"${summary2['total_user_collateral_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Credit Reserved: "),
                                    html.Span(f"${summary2['total_max_release_usd']:,.2f}")
                                ], className="mb-2"),
                                html.P([
                                    html.Strong("Debt: "),
                                    html.Span(f"${summary2['total_max_repay_usd']:,.2f}")
                                ], className="mb-0")
                            ])
                        ], className="p-3 border rounded bg-light")
                    ], md=4)
                ], className="g-3"),
                
                # Timestamp info
                html.Div([
                    html.Hr(className="my-4"),
                    html.P(
                        f"Comparison generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        className="text-muted text-center mb-0"
                    )
                ])
            ])
        ], className="shadow-sm")
        
    except Exception as e:
        logger.error(f"Error comparing blocks {block1} and {block2}: {str(e)}", exc_info=True)
        return dbc.Alert(f"Error comparing blocks: {str(e)}", color="danger")
