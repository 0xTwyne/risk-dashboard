"""
Liquidations page for Risk Dashboard.
Displays internal and external liquidation events for collateral vaults.
"""

import logging
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import PageContainer, LiquidationsSection

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash
dash.register_page(__name__, path="/liquidations", title="Liquidations - Risk Dashboard")


def layout():
    """
    Define the layout for the Liquidations page.
    
    Returns:
        Dash layout components
    """
    return PageContainer(
        children=[
            # URL location component for callbacks
            dcc.Location(id="url", refresh=False),
            
            # Liquidations Section
            LiquidationsSection()
        ]
    )

