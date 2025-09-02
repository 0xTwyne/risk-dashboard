"""
EVaults page for Risk Dashboard.
Displays EVault metrics including total assets, borrows, and utilization rates.
"""

import logging
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.components import PageContainer, EVaultsSection

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash
dash.register_page(__name__, path="/evaults", title="EVaults - Risk Dashboard")


def layout():
    """
    Define the layout for the EVaults page.
    
    Returns:
        Dash layout components
    """
    return PageContainer(
        children=[
            # URL location component for callbacks
            dcc.Location(id="url", refresh=False),
            
            # EVaults Section
            EVaultsSection()
        ]
    )
