"""
EVault Detail page for Risk Dashboard.
Displays historical metrics and charts for a specific EVault.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
import dash
from dash import html, dcc, callback, Output, Input, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px

from src.components import PageContainer, SectionCard, MetricCard, LoadingState, ErrorState, ErrorAlert
from src.api import api_client

# Configure logging
logger = logging.getLogger(__name__)

# Register the page with Dash - using path_template for dynamic routing
dash.register_page(
    __name__, 
    path_template="/evaults/<vault_address>", 
    title="EVault Detail - Risk Dashboard"
)


def fetch_vault_historical_data(vault_address: str, limit: int = 100) -> Dict[str, Any]:
    """
    Fetch historical metrics for a specific EVault.
    
    Args:
        vault_address: The vault address to fetch data for
        limit: Number of historical records to fetch
        
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info(f"Fetching historical data for vault: {vault_address}")
        
        # Fetch historical data using the API client
        response = api_client.get_evault_metrics(address=vault_address, limit=limit)
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "vault_address": vault_address,
                "metrics": []
            }
        
        # Extract metrics from successful response
        metrics = response.metrics or []
        
        logger.info(f"Successfully fetched {len(metrics)} historical metrics for vault {vault_address}")
        
        return {
            "error": None,
            "vault_address": vault_address,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch vault historical data: {e}", exc_info=True)
        return {
            "error": str(e),
            "vault_address": vault_address,
            "metrics": []
        }


def create_utilization_chart(metrics: List) -> go.Figure:
    """
    Create a line chart showing utilization rate over time.
    
    Args:
        metrics: List of EVaultMetric objects
        
    Returns:
        Plotly figure object
    """
    if not metrics:
        return go.Figure().add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Sort metrics by timestamp
    sorted_metrics = sorted(metrics, key=lambda x: int(x.blockTimestamp))
    
    # Calculate utilization rates and prepare data
    timestamps = []
    utilization_rates = []
    
    for metric in sorted_metrics:
        total_assets = float(metric.totalAssets) if metric.totalAssets != "0" else 0.0
        total_borrows = float(metric.totalBorrows) if metric.totalBorrows != "0" else 0.0
        utilization_rate = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
        
        timestamps.append(datetime.fromtimestamp(int(metric.blockTimestamp)))
        utilization_rates.append(utilization_rate)
    
    # Create the line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=utilization_rates,
        mode='lines+markers',
        name='Utilization Rate',
        line=dict(color='#007bff', width=2),
        marker=dict(size=6),
        hovertemplate='<b>%{y:.2f}%</b><br>%{x}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title="Utilization Rate Over Time",
        xaxis_title="Time",
        yaxis_title="Utilization Rate (%)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


def layout(vault_address: str = None):
    """
    Define the layout for the EVault detail page.
    
    Args:
        vault_address: The vault address from the URL
        
    Returns:
        Dash layout components
    """
    if not vault_address:
        return PageContainer(
            children=[
                ErrorAlert(
                    message="No vault address provided",
                    title="Invalid URL"
                )
            ]
        )
    
    return PageContainer(
        children=[
            # URL location component for callbacks
            dcc.Location(id="vault-detail-url", refresh=False),
            
            # Store vault address for callbacks
            dcc.Store(id="vault-address-store", data=vault_address),
            
            # Back navigation
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-arrow-left me-2"), "Back to EVaults"],
                    href="/evaults",
                    color="outline-secondary",
                    size="sm",
                    className="mb-3"
                )
            ]),
            
            # Page title
            html.Div([
                html.H2([
                    html.I(className="fas fa-coins me-2"),
                    f"EVault Details"
                ], className="mb-2"),
                html.P([
                    html.Strong("Address: "),
                    html.Code(vault_address, className="bg-light p-1")
                ], className="text-muted mb-4")
            ]),
            
            # Metrics section
            SectionCard(
                title="Current Metrics",
                icon="fas fa-chart-bar",
                children=[
                    html.Div(id="vault-detail-metrics", className="mb-3")
                ]
            ),
            
            # Chart section
            SectionCard(
                title="Utilization Rate History",
                icon="fas fa-chart-line",
                action_button=dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                    id="vault-detail-refresh",
                    color="outline-primary",
                    size="sm"
                ),
                children=[
                    html.Div(id="vault-detail-status", className="mb-3"),
                    html.Div(id="vault-detail-chart", className="mb-3"),
                    html.Div([
                        html.Small(id="vault-detail-last-updated", className="text-muted")
                    ], className="text-end")
                ]
            )
        ]
    )


# Callback for vault detail page
@callback(
    [Output("vault-detail-metrics", "children"),
     Output("vault-detail-status", "children"),
     Output("vault-detail-chart", "children"),
     Output("vault-detail-last-updated", "children")],
    [Input("vault-detail-refresh", "n_clicks"),
     Input("vault-detail-url", "pathname")],
    [State("vault-address-store", "data")],
    prevent_initial_call=False
)
def update_vault_detail(n_clicks, pathname, vault_address):
    """
    Update the vault detail metrics and chart.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        pathname: Current URL path
        vault_address: Vault address from store
        
    Returns:
        Tuple of (metrics_cards, status_message, chart_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/evaults/"):
        return [], "", "", ""
    
    logger.info(f"Updating vault detail for {vault_address}...")
    
    # Fetch the historical data
    data = fetch_vault_historical_data(vault_address, limit=100)
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        chart_component = ErrorState(
            error_message="Unable to load chart data due to API error",
            retry_callback="vault-detail-refresh"
        )
    else:
        status_message = dbc.Alert(
            f"Loaded {len(data['metrics'])} historical records", 
            color="success",
            dismissable=True,
            duration=3000
        )
        
        # Calculate current metrics from latest data point
        if data["metrics"]:
            latest_metric = max(data["metrics"], key=lambda x: int(x.blockTimestamp))
            total_assets = float(latest_metric.totalAssets) if latest_metric.totalAssets != "0" else 0.0
            total_borrows = float(latest_metric.totalBorrows) if latest_metric.totalBorrows != "0" else 0.0
            current_utilization = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
            
            # Create current metrics cards
            metrics_cards = dbc.Row([
                dbc.Col([
                    MetricCard(
                        title="Total Assets", 
                        value=f"{total_assets:,.4f}",
                        icon="fas fa-coins",
                        color="primary"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Total Assets (USD)", 
                        value=f"${float(latest_metric.totalAssetsUsd):,.2f}",
                        icon="fas fa-dollar-sign",
                        color="success"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Total Borrows", 
                        value=f"{total_borrows:,.4f}",
                        icon="fas fa-chart-line",
                        color="info"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Current Utilization", 
                        value=f"{current_utilization:.2f}%",
                        icon="fas fa-percentage",
                        color="danger" if current_utilization > 90 else "warning" if current_utilization > 80 else "info"
                    )
                ], width=12, md=6, lg=3)
            ], className="g-3")
        else:
            metrics_cards = html.P("No current metrics available", className="text-muted")
        
        # Create utilization chart
        if data["metrics"]:
            fig = create_utilization_chart(data["metrics"])
            chart_component = dcc.Graph(
                figure=fig,
                id="utilization-chart",
                config={'displayModeBar': True, 'displaylogo': False}
            )
        else:
            chart_component = html.Div([
                html.P("No historical data available for chart", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, chart_component, last_updated
