"""
Reusable chart components for the Risk Dashboard.
"""

import logging
from typing import List, Dict, Any, Optional
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px

logger = logging.getLogger(__name__)


def create_line_chart(
    x_data: List,
    y_data: List,
    title: str,
    x_label: str = "Time",
    y_label: str = "Value"
) -> dcc.Graph:
    """
    Create a line chart.
    
    Args:
        x_data: X-axis data
        y_data: Y-axis data
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        
    Returns:
        Plotly graph component
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='lines+markers',
        name=y_label
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white"
    )
    
    return dcc.Graph(figure=fig)


def create_bar_chart(
    x_data: List,
    y_data: List,
    title: str,
    x_label: str = "Category",
    y_label: str = "Value"
) -> dcc.Graph:
    """
    Create a bar chart.
    
    Args:
        x_data: X-axis data (categories)
        y_data: Y-axis data (values)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        
    Returns:
        Plotly graph component
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=x_data,
        y=y_data,
        name=y_label
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_white"
    )
    
    return dcc.Graph(figure=fig)


def create_pie_chart(
    labels: List[str],
    values: List[float],
    title: str
) -> dcc.Graph:
    """
    Create a pie chart.
    
    Args:
        labels: Pie slice labels
        values: Pie slice values
        title: Chart title
        
    Returns:
        Plotly graph component
    """
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.3  # Donut chart style
    ))
    
    fig.update_layout(
        title=title,
        template="plotly_white"
    )
    
    return dcc.Graph(figure=fig)
