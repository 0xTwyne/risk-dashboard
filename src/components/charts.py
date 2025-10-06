"""
Reusable chart components for the Risk Dashboard.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

logger = logging.getLogger(__name__)


def aggregate_metrics_to_hourly_intervals(metrics: List) -> List:
    """
    Aggregate EVault metrics into 1-hour intervals by taking the latest metric
    within each hour window.
    
    Args:
        metrics: List of EVaultMetric objects
        
    Returns:
        List of aggregated metrics (one per hour)
    """
    if not metrics:
        return []
    
    # Sort metrics by timestamp
    sorted_metrics = sorted(metrics, key=lambda x: int(x.blockTimestamp))
    
    # Group metrics by hour
    hourly_groups = defaultdict(list)
    
    for metric in sorted_metrics:
        timestamp = datetime.fromtimestamp(int(metric.blockTimestamp))
        # Round down to the nearest hour
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        hourly_groups[hour_key].append(metric)
    
    # Take the latest metric from each hour
    aggregated_metrics = []
    for hour_key in sorted(hourly_groups.keys()):
        # Get the latest metric in this hour (highest timestamp)
        hour_metrics = hourly_groups[hour_key]
        latest_metric = max(hour_metrics, key=lambda x: int(x.blockTimestamp))
        aggregated_metrics.append(latest_metric)
    
    logger.info(f"Aggregated {len(sorted_metrics)} metrics into {len(aggregated_metrics)} hourly intervals")
    return aggregated_metrics


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


def create_credit_flow_sankey(
    sankey_data: Dict[str, Any],
    title: str = "Credit Flow: Credit Vaults → Debt Vaults"
) -> dcc.Graph:
    """
    Create a 2-tier Sankey diagram showing credit flow from credit vaults to debt vaults.
    
    Args:
        sankey_data: Dictionary with 'labels', 'source', 'target', 'value', 'colors',
                     'num_credit', 'num_debt'
        title: Chart title
        
    Returns:
        Plotly graph component with Sankey diagram
    """
    if not sankey_data.get('labels') or not sankey_data.get('source'):
        # Return empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No credit flow data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title=title,
            template="plotly_white",
            height=600
        )
        return dcc.Graph(figure=fig)
    
    # Get tier counts
    num_credit = sankey_data.get('num_credit', 0)
    num_debt = sankey_data.get('num_debt', 0)
    
    # Format labels to show shortened addresses with tier prefix
    formatted_labels = []
    customdata_labels = []
    
    for i, label in enumerate(sankey_data['labels']):
        # Determine which tier this node belongs to
        if i < num_credit:
            tier_prefix = "Credit: "
        else:
            tier_prefix = "Debt: "
        
        # Shorten Ethereum addresses
        if len(label) > 42:  # Ethereum address length
            short_label = f"{label[:6]}...{label[-4:]}"
        else:
            short_label = label
        
        formatted_labels.append(f"{tier_prefix}{short_label}")
        customdata_labels.append(f"{tier_prefix}{label}")
    
    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        valueformat="$,.2f",
        valuesuffix=" USD",
        arrangement="snap",
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=formatted_labels,
            color=sankey_data['colors'],
            customdata=customdata_labels,  # Store full addresses with tier info
            hovertemplate='%{customdata}<br />Total Flow: %{value}<extra></extra>'
        ),
        link=dict(
            source=sankey_data['source'],
            target=sankey_data['target'],
            value=sankey_data['value'],
            color='rgba(0, 0, 0, 0.2)',  # Semi-transparent links
            hovertemplate='From: %{source.customdata}<br />'+
                         'To: %{target.customdata}<br />'+
                         'Amount: $%{value:,.2f}<extra></extra>'
        )
    )])
    
    # Update layout
    fig.update_layout(
        title=title,
        font=dict(size=10),
        template="plotly_white",
        height=600,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return dcc.Graph(
        figure=fig,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
        }
    )


def create_ltv_position_heatmap(
    heatmap_data: List[Tuple[float, float, str]],
    title: str = "Position Size vs User LTV Distribution"
) -> dcc.Graph:
    """
    Create a density heatmap showing Position Size (log scale) vs LTV.
    Cell colors represent the number of observations (density).
    
    Args:
        heatmap_data: List of tuples (ltv, position_size, vault_address)
        title: Chart title
        
    Returns:
        Plotly graph component with heatmap
    """
    if not heatmap_data:
        # Return empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No data available for heatmap",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title=title,
            template="plotly_white",
            height=500
        )
        return dcc.Graph(figure=fig)
    
    # Extract LTV and Position Size values
    ltv_values = [point[0] for point in heatmap_data]
    position_sizes = [point[1] for point in heatmap_data]
    
    # Apply log transformation to position sizes for the y-axis
    log_position_sizes = [np.log10(ps) if ps > 0 else 0 for ps in position_sizes]
    
    # Create the 2D histogram heatmap
    fig = go.Figure()
    
    # Use Histogram2d for density heatmap
    fig.add_trace(go.Histogram2d(
        x=ltv_values,
        y=log_position_sizes,
        colorscale='RdBu',  
        nbinsx=10,  # Number of bins on x-axis
        nbinsy=10,  # Number of bins on y-axis
        colorbar=dict(
            title=dict(text="Count")
        ),
        hovertemplate='LTV: %{x:.2f}<br>Log10(Position Size): %{y:.2f}<br>Count: %{z}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="User LTV",
        yaxis_title="Log10(User Position Size [USD])",
        template="plotly_white",
        height=500,
        showlegend=False,
        hovermode='closest'
    )
    
    # Set reasonable axis ranges
    if ltv_values and log_position_sizes:
        # X-axis (LTV) typically ranges from 0 to 1 (or slightly above)
        max_ltv = max(ltv_values)
        fig.update_xaxes(range=[0, min(max_ltv * 1.1, 1.0)])
        
        # Y-axis (log position size)
        min_log_ps = min(log_position_sizes)
        max_log_ps = max(log_position_sizes)
        fig.update_yaxes(range=[min_log_ps - 0.5, max_log_ps + 0.5])
    
    return dcc.Graph(
        figure=fig,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
        }
    )


def create_multi_vault_utilization_chart(
    vault_data: List[Dict[str, Any]],
    title: str = ""
) -> dcc.Graph:
    """
    Create a line chart showing utilization rates over time for multiple vaults.
    Each vault gets a different color and appears in the legend.
    
    Args:
        vault_data: List of dicts with keys:
            - vault_address: str
            - symbol: str  
            - metrics: List of EVaultMetric objects
        title: Chart title
        
    Returns:
        Plotly graph component
    """
    if not vault_data:
        # Return empty chart with message
        fig = go.Figure()
        fig.add_annotation(
            text="No vault data available",
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
    
    # Create color palette for different vaults
    colors = px.colors.qualitative.Set3
    
    fig = go.Figure()
    
    # Process each vault's data
    for i, vault_info in enumerate(vault_data):
        vault_address = vault_info.get('vault_address', 'Unknown')
        symbol = vault_info.get('symbol', 'Unknown')
        metrics = vault_info.get('metrics', [])
        
        if not metrics:
            continue
            
        logger.info(f"Processing vault {symbol}: {len(metrics)} raw metrics")
        
        # Aggregate metrics to hourly intervals
        aggregated_metrics = aggregate_metrics_to_hourly_intervals(metrics)
        
        # Calculate utilization rates and prepare data
        timestamps = []
        utilization_rates = []
        
        for metric in aggregated_metrics:
            # Get decimals for proper scaling
            decimals = int(metric.decimals) if hasattr(metric, 'decimals') and metric.decimals != "0" else 18
            scaling_factor = 10 ** decimals
            
            # Scale totalAssets and totalBorrows using decimals
            total_assets = float(metric.totalAssets) / scaling_factor if metric.totalAssets != "0" else 0.0
            total_borrows = float(metric.totalBorrows) / scaling_factor if metric.totalBorrows != "0" else 0.0
            
            # Calculate utilization rate
            utilization_rate = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
            
            timestamps.append(datetime.fromtimestamp(int(metric.blockTimestamp)))
            utilization_rates.append(utilization_rate)
        
        if not timestamps:
            continue
        
        # Log the date range for this vault
        if timestamps:
            start_date = min(timestamps)
            end_date = max(timestamps)
            logger.info(f"Vault {symbol} data range: {start_date} to {end_date} ({len(timestamps)} hourly points)")
            
        # Add trace for this vault
        color = colors[i % len(colors)]
        
        # Use different modes based on data size for performance
        mode = 'lines+markers' if len(timestamps) <= 100 else 'lines'
        marker_size = 4 if len(timestamps) <= 100 else 2
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=utilization_rates,
            mode=mode,
            name=symbol,
            line=dict(color=color, width=2),
            marker=dict(size=marker_size) if 'markers' in mode else None,
            hovertemplate=f'<b>{symbol}</b><br>%{{y:.2f}}%<br>%{{x}}<extra></extra>',
            connectgaps=True  # Connect gaps in data
        ))
    
    # Update layout
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Utilization Rate (%)",
        hovermode='x unified',
        template='plotly_white',
        height=500,
        margin=dict(l=50, r=50, t=30, b=50),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        # Add range selector for better navigation of extended timelines
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=24, label="24h", step="hour", stepmode="backward"),
                    dict(count=7, label="7d", step="day", stepmode="backward"),
                    dict(count=30, label="30d", step="day", stepmode="backward"),
                    dict(step="all", label="All")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    # Ensure y-axis starts at 0
    fig.update_yaxes(rangemode="tozero")
    
    return dcc.Graph(
        figure=fig,
        config={
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
        }
    )
