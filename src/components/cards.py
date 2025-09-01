"""
Reusable card components for the Risk Dashboard.
Following atomic design principles for consistent UI elements.
"""

import logging
from typing import Optional, Any
from dash import html
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def MetricCard(
    title: str, 
    value: str, 
    icon: str = "fas fa-chart-bar",
    color: str = "primary",
    subtitle: Optional[str] = None
) -> dbc.Card:
    """
    Create a metric display card.
    
    Args:
        title: Card title/metric name
        value: Metric value to display
        icon: FontAwesome icon class
        color: Bootstrap color theme
        subtitle: Optional subtitle text
        
    Returns:
        Dash Bootstrap Card component
    """
    card_content = [
        html.I(className=f"{icon} fa-2x text-{color} mb-2"),
        html.H4(value, className="text-dark mb-1"),
        html.P(title, className="text-muted mb-0")
    ]
    
    if subtitle:
        card_content.append(
            html.Small(subtitle, className="text-muted")
        )
    
    return dbc.Card([
        dbc.CardBody([
            html.Div(card_content, className="text-center")
        ])
    ], className="shadow-sm h-100")


def ClickableCard(
    title: str,
    description: str,
    href: str,
    icon: str = "fas fa-arrow-right",
    color: str = "light"
) -> html.A:
    """
    Create a clickable navigation card.
    
    Args:
        title: Card title
        description: Card description
        href: Link destination
        icon: FontAwesome icon class
        color: Bootstrap color theme
        
    Returns:
        Clickable Dash Bootstrap Card component wrapped in a link
    """
    return html.A([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H5(title, className="card-title"),
                    html.P(description, className="card-text text-muted"),
                    html.I(className=f"{icon} text-primary")
                ])
            ])
        ], 
        className=f"shadow-sm h-100 card-hover bg-{color}",
        style={"cursor": "pointer"})
    ],
    href=href,
    style={"textDecoration": "none", "color": "inherit"})


def InfoCard(
    content: Any,
    title: Optional[str] = None,
    color: str = "light"
) -> dbc.Card:
    """
    Create a general information card.
    
    Args:
        content: Card content (can be HTML components)
        title: Optional card title
        color: Bootstrap color theme
        
    Returns:
        Dash Bootstrap Card component
    """
    card_body_content = []
    
    if title:
        card_body_content.append(
            html.H5(title, className="card-title mb-3")
        )
    
    if isinstance(content, str):
        card_body_content.append(html.P(content, className="card-text"))
    else:
        card_body_content.append(content)
    
    return dbc.Card([
        dbc.CardBody(card_body_content)
    ], className=f"shadow-sm bg-{color}")


def StatusCard(
    status: str,
    message: str,
    icon: Optional[str] = None,
    color: str = "info"
) -> dbc.Card:
    """
    Create a status display card.
    
    Args:
        status: Status text (e.g., "Connected", "Error")
        message: Status message
        icon: Optional FontAwesome icon class
        color: Bootstrap color theme (success, danger, warning, info)
        
    Returns:
        Dash Bootstrap Card component
    """
    card_content = []
    
    if icon:
        card_content.append(
            html.I(className=f"{icon} fa-lg text-{color} me-2")
        )
    
    card_content.extend([
        html.Strong(status, className=f"text-{color}"),
        html.Br(),
        html.Small(message, className="text-muted")
    ])
    
    return dbc.Card([
        dbc.CardBody([
            html.Div(card_content, className="d-flex align-items-center")
        ])
    ], className=f"shadow-sm border-{color}")
