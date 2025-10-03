"""
EVault Detail page for Risk Dashboard.
Displays historical metrics and charts for a specific EVault.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
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


async def fetch_vault_historical_data(
    vault_address: str, 
    limit: int = 100,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch historical metrics for a specific EVault.
    
    Args:
        vault_address: The vault address to fetch data for
        limit: Number of historical records to fetch
        start_time: Start time filter (Unix timestamp)
        end_time: End time filter (Unix timestamp)
        
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info(f"Fetching historical data for vault: {vault_address}")
        if start_time and end_time:
            logger.info(f"Time range: {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}")
        
        # Fetch historical data using the API client
        response = await api_client.get_evault_metrics(
            address=vault_address, 
            limit=limit,
            start_time=start_time,
            end_time=end_time
        )
        
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
                    # Date range picker
                    html.Div([
                        html.Label("Select Date Range:", className="form-label mb-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("From:", size="sm"),
                                dcc.DatePickerSingle(
                                    id="start-date-picker",
                                    date=(datetime.now() - timedelta(days=30)).date(),
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"}
                                )
                            ], width=12, md=6),
                            dbc.Col([
                                dbc.Label("To:", size="sm"),
                                dcc.DatePickerSingle(
                                    id="end-date-picker",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    style={"width": "100%"}
                                )
                            ], width=12, md=6)
                        ], className="g-2"),
                        html.Div([
                            dbc.ButtonGroup([
                                dbc.Button("Last 7 Days", id="preset-7d", size="sm", color="outline-secondary"),
                                dbc.Button("Last 30 Days", id="preset-30d", size="sm", color="outline-secondary"),
                                dbc.Button("Last 90 Days", id="preset-90d", size="sm", color="outline-secondary"),
                            ], className="me-2"),
                            dbc.Button(
                                "Apply Date Range",
                                id="apply-date-range",
                                color="primary",
                                size="sm"
                            )
                        ], className="mt-2")
                    ], className="mb-3 p-3 bg-light rounded"),
                    
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
     Input("vault-detail-url", "pathname"),
     Input("apply-date-range", "n_clicks")],
    [State("vault-address-store", "data"),
     State("start-date-picker", "date"),
     State("end-date-picker", "date")],
    prevent_initial_call=False
)
def update_vault_detail(n_clicks_refresh, pathname, n_clicks_apply, vault_address, start_date, end_date):
    """
    Update the vault detail metrics and chart.
    
    Args:
        n_clicks_refresh: Number of times refresh button was clicked
        pathname: Current URL path
        n_clicks_apply: Number of times apply date range button was clicked
        vault_address: Vault address from store
        start_date: Start date from date picker
        end_date: End date from date picker
        
    Returns:
        Tuple of (metrics_cards, status_message, chart_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/evaults/"):
        return [], "", "", ""
    
    logger.info(f"Updating vault detail for {vault_address}...")
    
    # Convert dates to Unix timestamps if provided
    start_time = None
    end_time = None
    
    if start_date:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        start_time = int(start_datetime.timestamp())
    
    if end_date:
        # Set end time to end of the selected day
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        end_time = int(end_datetime.timestamp())
    
    # If no dates selected, default to last 30 days
    if not start_time or not end_time:
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=30)).timestamp())
    
    # Fetch the historical data with time filtering
    data = run_async(fetch_vault_historical_data(
        vault_address, 
        limit=1000,  # Increase limit for historical data
        start_time=start_time,
        end_time=end_time
    ))
    
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
        # Format date range for display
        start_date_str = datetime.fromtimestamp(start_time).strftime("%Y-%m-%d")
        end_date_str = datetime.fromtimestamp(end_time).strftime("%Y-%m-%d")
        
        status_message = dbc.Alert(
            f"Loaded {len(data['metrics'])} historical records from {start_date_str} to {end_date_str}", 
            color="success",
            dismissable=True,
            duration=4000
        )
        
        # Calculate current metrics from latest data point
        if data["metrics"]:
            latest_metric = max(data["metrics"], key=lambda x: int(x.blockTimestamp))
            
            # Get decimals for proper scaling
            decimals = int(latest_metric.decimals) if hasattr(latest_metric, 'decimals') and latest_metric.decimals != "0" else 18
            scaling_factor = 10 ** decimals
            
            # Scale totalAssets and totalBorrows using decimals
            total_assets = float(latest_metric.totalAssets) / scaling_factor if latest_metric.totalAssets != "0" else 0.0
            total_borrows = float(latest_metric.totalBorrows) / scaling_factor if latest_metric.totalBorrows != "0" else 0.0
            current_utilization = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
            
            # Scale USD values by 1e18 if needed
            total_assets_usd_raw = float(latest_metric.totalAssetsUsd) if latest_metric.totalAssetsUsd != "0" else 0.0
            total_assets_usd = total_assets_usd_raw / 1e18 if total_assets_usd_raw > 1e12 else total_assets_usd_raw
            
            total_borrows_usd_raw = float(latest_metric.totalBorrowsUsd) if hasattr(latest_metric, 'totalBorrowsUsd') and latest_metric.totalBorrowsUsd != "0" else 0.0
            total_borrows_usd = total_borrows_usd_raw / 1e18 if total_borrows_usd_raw > 1e12 else total_borrows_usd_raw
            
            # Format interest rate as percentage
            interest_rate = float(latest_metric.interestRate) / 1e18 * 100 if hasattr(latest_metric, 'interestRate') and latest_metric.interestRate != "0" else 0.0
            
            # Create current metrics cards
            metrics_cards = dbc.Row([
                dbc.Col([
                    MetricCard(
                        title="Total Assets", 
                        value=f"{total_assets:,.4f} {getattr(latest_metric, 'symbol', '')}",
                        icon="fas fa-coins",
                        color="primary"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Total Assets (USD)", 
                        value=f"${total_assets_usd:,.2f}",
                        icon="fas fa-dollar-sign",
                        color="success"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Total Borrows", 
                        value=f"{total_borrows:,.4f} {getattr(latest_metric, 'symbol', '')}",
                        icon="fas fa-chart-line",
                        color="info"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Total Borrows (USD)", 
                        value=f"${total_borrows_usd:,.2f}",
                        icon="fas fa-dollar-sign",
                        color="warning"
                    )
                ], width=12, md=6, lg=3),
                
                dbc.Col([
                    MetricCard(
                        title="Interest Rate", 
                        value=f"{interest_rate:.2f}%",
                        icon="fas fa-percent",
                        color="secondary"
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


# Callback for preset date buttons
@callback(
    [Output("start-date-picker", "date"),
     Output("end-date-picker", "date")],
    [Input("preset-7d", "n_clicks"),
     Input("preset-30d", "n_clicks"),
     Input("preset-90d", "n_clicks")],
    prevent_initial_call=True
)
def update_date_presets(n_clicks_7d, n_clicks_30d, n_clicks_90d):
    """
    Update date pickers based on preset button clicks.
    
    Args:
        n_clicks_7d: Clicks on 7 days preset
        n_clicks_30d: Clicks on 30 days preset
        n_clicks_90d: Clicks on 90 days preset
        
    Returns:
        Tuple of (start_date, end_date)
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    end_date = datetime.now().date()
    
    if button_id == "preset-7d":
        start_date = (datetime.now() - timedelta(days=7)).date()
    elif button_id == "preset-30d":
        start_date = (datetime.now() - timedelta(days=30)).date()
    elif button_id == "preset-90d":
        start_date = (datetime.now() - timedelta(days=90)).date()
    else:
        return dash.no_update, dash.no_update
    
    return start_date, end_date
