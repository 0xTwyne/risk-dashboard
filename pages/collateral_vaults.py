"""
Collateral Vaults page for Risk Dashboard.
Displays collateral vault metrics and snapshots.
"""

import logging
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import PageContainer, CollateralVaultsSection

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash
dash.register_page(__name__, path="/collateralVaults", title="Collateral Vaults - Risk Dashboard")


def layout():
    """
    Define the layout for the collateral vaults page.
    
    Returns:
        Dash layout components
    """
    return PageContainer(
        children=[
            # URL location component for callbacks
            dcc.Location(id="url", refresh=False),
            
            # Collateral Vaults Section
            CollateralVaultsSection()
        ]
    )
