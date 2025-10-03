"""
Main Dash application entry point for Risk Dashboard.
"""

import logging
import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

from config import config
from src.components.layouts import DashboardHeader

# Initialize logging
config.setup_logging()
logger = logging.getLogger(__name__)

# Initialize the Dash app with Bootstrap theme
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
    ],
    suppress_callback_exceptions=True,
    title="Risk Dashboard",
    assets_folder="src/assets"
)

# Define the app layout
app.layout = html.Div([
    # Header/Navigation
    DashboardHeader(title="Twyne Risk Dashboard"),
    
    # URL location component for routing
    dcc.Location(id="url", refresh=False),
    
    # Main content area - pages will be rendered here
    dash.page_container,
    
    # Global stores for shared state
    # dcc.Store(id="api-cache-store", storage_type="session"),
    # dcc.Store(id="user-preferences", storage_type="local"),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id="refresh-interval",
        interval=60 * 1000,  # 60 seconds
        n_intervals=0
    )
])

# Import pages to register them with Dash (after app instantiation)
logger.info("Registering dashboard pages...")
import pages.home
import pages.collateral_vaults
import pages.evaults
import pages.evault_detail
import pages.liquidations
logger.info("Pages registered successfully")

# Run the app
if __name__ == "__main__":
    logger.info("Starting Risk Dashboard application...")
    app.run(debug=False, host="0.0.0.0", port=8050)
