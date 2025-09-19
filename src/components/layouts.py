"""
Layout components for the Risk Dashboard.
Provides consistent page structure and navigation.
"""

import logging
from typing import List, Optional
from dash import html, dcc
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def DashboardHeader(title: str = "Risk Dashboard") -> html.Div:
    """
    Create the main dashboard header with navigation.
    
    Args:
        title: Application title
        
    Returns:
        Header component with navigation
    """
    return html.Div([
        dbc.Navbar([
            dbc.Container([
                # Brand/Logo
                dbc.NavbarBrand([
                    html.I(className="fas fa-shield-alt me-2"),
                    title
                ], href="/", className="text-white fw-bold"),
                
                # Navigation items
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Home", href="/", className="text-white")),
                    dbc.NavItem(dbc.NavLink("Collateral Vaults", href="/collateralVaults", className="text-white")),
                    dbc.NavItem(dbc.NavLink("EVaults", href="/evaults", className="text-white")),
                    dbc.NavItem(dbc.NavLink("Block Snapshot", href="/block-snapshot", className="text-white")),
                    dbc.NavItem(dbc.NavLink("Liquidations", href="/liquidations", className="text-white"))
                ], navbar=True, className="ms-auto")
            ], fluid=True)
        ], color="primary", dark=True, className="mb-4")
    ])


def PageContainer(
    children: List,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    fluid: bool = True
) -> html.Div:
    """
    Create a standard page container with optional title.
    
    Args:
        children: Page content components
        title: Optional page title
        subtitle: Optional page subtitle
        fluid: Whether to use fluid container
        
    Returns:
        Page container component
    """
    container_content = []
    
    # Add page header if title provided
    if title:
        header_content = [html.H1(title, className="mb-3")]
        if subtitle:
            header_content.append(
                html.P(subtitle, className="lead text-muted")
            )
        container_content.append(
            html.Div(header_content, className="mb-4")
        )
    
    # Add main content
    container_content.extend(children)
    
    return dbc.Container(
        container_content,
        fluid=fluid,
        className="p-4"
    )


def SectionCard(
    title: str,
    children: List,
    icon: Optional[str] = None,
    action_button: Optional[dbc.Button] = None
) -> dbc.Card:
    """
    Create a section card with title and content.
    
    Args:
        title: Section title
        children: Section content components
        icon: Optional FontAwesome icon class
        action_button: Optional action button for the header
        
    Returns:
        Section card component
    """
    # Build header content
    header_content = []
    if icon:
        header_content.append(
            html.I(className=f"{icon} me-2")
        )
    header_content.append(html.H5(title, className="mb-0"))
    
    # Create header with optional action button
    if action_button:
        header = dbc.CardHeader([
            html.Div([
                html.Div(header_content, className="d-flex align-items-center"),
                action_button
            ], className="d-flex justify-content-between align-items-center")
        ])
    else:
        header = dbc.CardHeader(
            html.Div(header_content, className="d-flex align-items-center")
        )
    
    return dbc.Card([
        header,
        dbc.CardBody(children)
    ], className="shadow-sm mb-4")


def LoadingSpinner(message: str = "Loading...") -> html.Div:
    """
    Create a loading spinner with message.
    
    Args:
        message: Loading message to display
        
    Returns:
        Loading spinner component
    """
    return html.Div([
        dbc.Spinner([
            html.Div(message, className="mt-3")
        ], size="lg", color="primary")
    ], className="text-center p-4")


def ErrorAlert(
    message: str,
    title: str = "Error",
    dismissable: bool = True
) -> dbc.Alert:
    """
    Create an error alert component.
    
    Args:
        message: Error message
        title: Alert title
        dismissable: Whether alert can be dismissed
        
    Returns:
        Error alert component
    """
    return dbc.Alert([
        html.H5(title, className="alert-heading"),
        html.P(message, className="mb-0")
    ], color="danger", dismissable=dismissable)
