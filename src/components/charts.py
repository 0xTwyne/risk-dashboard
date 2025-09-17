"""
Reusable chart components for the Risk Dashboard.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

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


def create_health_factor_scatter_plot(
    chart_data: List[Tuple[float, float, float, str]],
    title: str = "Debt USD vs Health Factor"
) -> dcc.Graph:
    """
    Create a scatter plot for Debt USD (x-axis, log scale) vs Health Factor (y-axis).
    Marker size varies based on credit USD value.
    
    Args:
        chart_data: List of tuples (health_factor, debt_usd, credit_usd, vault_address)
        title: Chart title
        
    Returns:
        Plotly graph component
    """
    if not chart_data:
        # Return empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available with debt > 0",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title=title,
            template="plotly_white",
            height=400
        )
        return dcc.Graph(figure=fig)
    
    # Extract data for plotting
    health_factors = [point[0] for point in chart_data]
    debt_usd_values = [point[1] for point in chart_data]
    credit_usd_values = [point[2] for point in chart_data]
    vault_addresses = [point[3] for point in chart_data]
    
    # Calculate marker sizes based on credit USD values
    # Normalize credit values to reasonable marker sizes (6-30 pixels)
    min_credit = min(credit_usd_values) if credit_usd_values else 1
    max_credit = max(credit_usd_values) if credit_usd_values else 1
    
    if max_credit > min_credit:
        # Scale credit values to marker sizes between 6 and 30
        marker_sizes = [
            6 + (credit - min_credit) / (max_credit - min_credit) * 24
            for credit in credit_usd_values
        ]
    else:
        # All values are the same, use default size
        marker_sizes = [12] * len(credit_usd_values)
    
    # Create hover text with vault addresses (shortened)
    hover_text = [
        f"Vault: {addr[:10]}...<br>"
        f"Health Factor: {hf:.2f}<br>"
        f"Debt USD: ${debt:,.2f}<br>"
        f"Credit USD: ${credit:,.2f}"
        for hf, debt, credit, addr in chart_data
    ]
    
    # Create the scatter plot
    fig = go.Figure()
    
    # Add scatter trace
    fig.add_trace(go.Scatter(
        x=debt_usd_values,
        y=health_factors,
        mode='markers',
        marker=dict(
            size=marker_sizes,
            color='#5A54EF',  # Custom purple-blue color
            opacity=0.7,
            line=dict(width=1, color='white')
        ),
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        name="Positions"
    ))
    
    # Add critical health factor line (typically around 1.0)
    if health_factors:
        min_hf = min(health_factors)
        max_hf = max(health_factors)
        
        # Only show critical line if it's within the data range
        if min_hf <= 1.0 <= max_hf:
            fig.add_hline(
                y=1.0,
                line_dash="dash",
                line_color="red",
                annotation_text="Critical Health Factor",
                annotation_position="right"
            )
    
    # Update layout with log scale for x-axis
    fig.update_layout(
        title=title,
        xaxis_title="Debt USD (Log Scale)",
        yaxis_title="Health Factor",
        xaxis_type="log",
        template="plotly_white",
        height=500,
        showlegend=False,
        hovermode='closest'
    )
    
    # Ensure minimum x-axis value for log scale
    min_debt = min(debt_usd_values) if debt_usd_values else 1
    max_debt = max(debt_usd_values) if debt_usd_values else 100
    
    fig.update_xaxes(
        range=[np.log10(max(min_debt * 0.5, 0.01)), np.log10(max_debt * 2)]
    )
    
    return dcc.Graph(
        figure=fig,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
        }
    )
