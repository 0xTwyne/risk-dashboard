"""
Loading and error state components for the Risk Dashboard.
"""

import logging
from dash import html
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def LoadingState(message: str = "Loading data...") -> html.Div:
    """
    Create a loading state component.
    
    Args:
        message: Loading message to display
        
    Returns:
        Loading state component
    """
    return html.Div([
        dbc.Spinner([
            html.Div([
                html.P(message, className="mb-0 mt-3")
            ])
        ], size="lg", color="primary")
    ], className="text-center p-5")


def ErrorState(
    error_message: str,
    retry_callback: str = None
) -> html.Div:
    """
    Create an error state component.
    
    Args:
        error_message: Error message to display
        retry_callback: Optional retry button callback ID
        
    Returns:
        Error state component
    """
    components = [
        html.I(className="fas fa-exclamation-triangle fa-3x text-danger mb-3"),
        html.H4("Something went wrong", className="text-danger"),
        html.P(error_message, className="text-muted mb-3")
    ]
    
    if retry_callback:
        components.append(
            dbc.Button(
                "Try Again",
                id=retry_callback,
                color="primary",
                outline=True
            )
        )
    
    return html.Div(components, className="text-center p-5")


def EmptyState(
    message: str = "No data available",
    icon: str = "fas fa-inbox"
) -> html.Div:
    """
    Create an empty state component.
    
    Args:
        message: Empty state message
        icon: FontAwesome icon class
        
    Returns:
        Empty state component
    """
    return html.Div([
        html.I(className=f"{icon} fa-3x text-muted mb-3"),
        html.H5("No Data", className="text-muted"),
        html.P(message, className="text-muted")
    ], className="text-center p-5")
