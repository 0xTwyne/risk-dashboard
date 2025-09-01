"""
Home page for Risk Dashboard.
Main landing page with navigation to different sections.
"""

import logging
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import PageContainer, ClickableCard

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash
dash.register_page(__name__, path="/", title="Home - Risk Dashboard")


def layout():
    """
    Define the layout for the home page.
    
    Returns:
        Dash layout components
    """
    return PageContainer(
        children=[
            # Navigation cards
            dbc.Row([
                dbc.Col([
                    ClickableCard(
                        title="Collateral Vaults",
                        description="View collateral vault positions, snapshots, and liquidation risks",
                        href="/collateralVaults",
                        icon="fas fa-vault",
                        color="light"
                    )
                ], width=12, md=6, lg=4)
            ], className="g-4")
        ]
    )