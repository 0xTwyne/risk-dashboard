"""
Collateral Vaults page for Risk Dashboard.
Displays collateral vault metrics and snapshots.
"""

import logging
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from src.components import PageContainer, CollateralVaultsSection

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash
dash.register_page(__name__, path="/collateralVaults", title="Collateral Vaults - Risk Dashboard")


def create_block_input_section() -> dbc.Card:
    """Create the block input section for historical snapshots."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("Data Source Selection", className="mb-0")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Block Number (Optional)", html_for="collateral-block-input"),
                    dbc.InputGroup([
                        dbc.Input(
                            id="collateral-block-input",
                            type="number",
                            placeholder="Enter block number for historical snapshot",
                            min=1,
                            step=1
                        ),
                        dbc.Button(
                            "Use Latest",
                            id="collateral-use-latest-btn",
                            color="outline-secondary",
                            n_clicks=0
                        )
                    ])
                ], md=8),
                dbc.Col([
                    dbc.Label(" ", html_for="collateral-apply-block-btn"),
                    dbc.Button(
                        "Apply Block Snapshot",
                        id="collateral-apply-block-btn",
                        color="primary",
                        className="w-100"
                    )
                ], md=4)
            ], className="mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Small([
                        "Leave empty to use the latest protocol data. ",
                        "Enter a block number to view historical data at that specific block."
                    ], className="text-muted")
                ])
            ])
        ])
    ], className="mb-4")


def layout():
    """
    Define the layout for the collateral vaults page.
    
    Returns:
        Dash layout components
    """
    return PageContainer(
        title="Collateral Vaults",
        subtitle="View collateral vault positions, snapshots, and risk metrics",
        children=[
            # URL location component for callbacks
            dcc.Location(id="url", refresh=False),
            
            # Block input section
            create_block_input_section(),
            
            # Store for current block selection
            dcc.Store(id="collateral-current-block", data=None),
            
            # Collateral Vaults Section
            CollateralVaultsSection()
        ]
    )


# Callback to handle block input changes
@callback(
    Output("collateral-current-block", "data"),
    [Input("collateral-apply-block-btn", "n_clicks"),
     Input("collateral-use-latest-btn", "n_clicks")],
    [State("collateral-block-input", "value")],
    prevent_initial_call=True
)
def update_block_selection(apply_clicks, latest_clicks, block_input):
    """Update the current block selection."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return None
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "collateral-use-latest-btn":
        return None  # None means use latest data
    elif trigger_id == "collateral-apply-block-btn" and block_input:
        return int(block_input)
    
    return None


# Callback to clear block input when "Use Latest" is clicked
@callback(
    Output("collateral-block-input", "value"),
    [Input("collateral-use-latest-btn", "n_clicks")],
    prevent_initial_call=True
)
def clear_block_input(n_clicks):
    """Clear the block input when Use Latest is clicked."""
    if n_clicks:
        return None
    return dash.no_update
