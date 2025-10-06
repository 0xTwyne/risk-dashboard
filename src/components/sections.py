"""
Section components for the Risk Dashboard.
Contains reusable dashboard sections with specific business logic.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from dash import html, dcc, callback, Output, Input, dash_table
import dash_bootstrap_components as dbc

from src.api import api_client
from src.api.block_snapshot_client import block_snapshot_client
from .cards import MetricCard
from .layouts import SectionCard, LoadingSpinner, ErrorAlert
from .loading import LoadingState, ErrorState
from src.utils.usd_calculations import (
    calculate_multiple_snapshots_usd_values,
    get_summary_metrics_from_snapshots,
    format_enhanced_snapshots_for_table,
    get_pricing_warnings_summary
)
from src.utils.health_factor import (
    calculate_health_factors_for_snapshots,
    get_health_factor_summary_stats,
    calculate_ltv_position_data_for_heatmap,
    prepare_sankey_data_for_credit_flow
)
from src.utils.block_snapshot import format_block_snapshot_for_table
from .charts import (
    create_health_factor_scatter_plot,
    create_multi_vault_utilization_chart,
    create_ltv_position_heatmap,
    create_credit_flow_sankey
)

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Helper to run async functions in sync callbacks.
    Uses existing event loop if available, otherwise creates new one.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to use run_coroutine_threadsafe or similar
            # For Dash callbacks, this shouldn't happen
            raise RuntimeError("Event loop is already running")
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(coro)


async def fetch_collateral_vault_data() -> Dict[str, Any]:
    """
    Fetch collateral vault snapshots and return summary metrics.
    
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info("Fetching collateral vaults snapshots...")
        
        # Fetch data using the API client
        response = await api_client.get_collateral_vaults_snapshots(limit=100)
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "unique_vaults": 0,
                "total_snapshots": 0
            }
        
        # Extract snapshots from successful response
        snapshots = response.latestSnapshots
        total_snapshots = len(snapshots)
        
        if not snapshots:
            logger.warning("No snapshots returned from API")
            return {
                "error": None,
                "unique_vaults": 0,
                "total_snapshots": 0,
                "snapshots": [],
                "enhanced_snapshots": [],
                "summary_metrics": {},
                "pricing_warnings": []
            }
        
        # Calculate USD values using EVault pricing
        enhanced_snapshots, pricing_warnings = await calculate_multiple_snapshots_usd_values(snapshots)
        
        # Count unique vault addresses
        unique_vault_addresses = set()
        for snapshot in snapshots:
            unique_vault_addresses.add(snapshot.vaultAddress)
        
        unique_vaults_count = len(unique_vault_addresses)
        
        # Calculate summary metrics from enhanced snapshots
        summary_metrics = get_summary_metrics_from_snapshots(enhanced_snapshots)
        
        logger.info(f"Successfully processed {total_snapshots} snapshots from {unique_vaults_count} unique vaults with {len(pricing_warnings)} pricing warnings")
        
        return {
            "error": None,
            "unique_vaults": unique_vaults_count,
            "total_snapshots": total_snapshots,
            "total_unique_vaults": getattr(response, 'totalUniqueVaults', None),
            "snapshots": snapshots,  # Keep original for compatibility
            "enhanced_snapshots": enhanced_snapshots,
            "summary_metrics": summary_metrics,
            "pricing_warnings": pricing_warnings
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch vault data: {e}", exc_info=True)
        return {
            "error": str(e),
            "unique_vaults": 0,
            "total_snapshots": 0,
            "snapshots": [],
            "enhanced_snapshots": [],
            "summary_metrics": {},
            "pricing_warnings": []
        }


async def fetch_collateral_vault_data_at_block(block_number: int) -> Dict[str, Any]:
    """
    Fetch collateral vault snapshots at a specific block and return summary metrics.
    
    Args:
        block_number: Block number to fetch data for
        
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info(f"Fetching collateral vaults snapshots at block {block_number:,}...")
        
        # Create block snapshot using the block snapshot client
        block_snapshot = await block_snapshot_client.create_snapshot_at_block(block_number)
        
        if not block_snapshot or not hasattr(block_snapshot, 'vault_snapshots'):
            logger.error(f"Failed to create block snapshot for block {block_number}")
            return {
                "error": "Failed to create block snapshot",
                "unique_vaults": 0,
                "total_snapshots": 0,
                "snapshots": [],
                "enhanced_snapshots": [],
                "summary_metrics": {},
                "pricing_warnings": []
            }
        
        vault_snapshots = block_snapshot.vault_snapshots
        total_snapshots = len(vault_snapshots)
        
        if not vault_snapshots:
            logger.warning(f"No snapshots found for block {block_number}")
            return {
                "error": None,
                "unique_vaults": 0,
                "total_snapshots": 0,
                "snapshots": [],
                "enhanced_snapshots": [],
                "summary_metrics": {},
                "pricing_warnings": [],
                "block_number": block_number,
                "block_timestamp": block_snapshot.timestamp,
                "is_historical": True
            }
        
        # Convert block snapshot format to match the expected format
        enhanced_snapshots = []
        snapshots = []  # For compatibility
        
        for vault_snapshot in vault_snapshots:
            enhanced_snapshot = {
                'original_snapshot': vault_snapshot['original_snapshot'],
                'calculated_usd_values': vault_snapshot['calculated_usd_values'],
                'vault_address': vault_snapshot['vault_address'],
                'credit_vault': vault_snapshot['credit_vault'],
                'debt_vault': vault_snapshot['debt_vault'],
                'has_pricing_errors': vault_snapshot['has_pricing_errors']
            }
            enhanced_snapshots.append(enhanced_snapshot)
            snapshots.append(vault_snapshot['original_snapshot'])
        
        # Calculate summary metrics from enhanced snapshots
        summary_metrics = get_summary_metrics_from_snapshots(enhanced_snapshots)
        
        # Collect pricing warnings
        pricing_warnings = []
        pricing_warnings.extend(block_snapshot.pricing_errors)
        pricing_warnings.extend(block_snapshot.fetch_errors)
        
        unique_vaults_count = len(set(vs['vault_address'] for vs in vault_snapshots))
        
        logger.info(f"Successfully processed {total_snapshots} snapshots from {unique_vaults_count} unique vaults at block {block_number} with {len(pricing_warnings)} warnings")
        
        return {
            "error": None,
            "unique_vaults": unique_vaults_count,
            "total_snapshots": total_snapshots,
            "total_unique_vaults": block_snapshot.total_vaults,
            "snapshots": snapshots,  # Keep original for compatibility
            "enhanced_snapshots": enhanced_snapshots,
            "summary_metrics": summary_metrics,
            "pricing_warnings": pricing_warnings,
            "block_number": block_number,
            "block_timestamp": block_snapshot.timestamp,
            "evault_prices_block": block_snapshot.evault_prices_block,
            "is_historical": True
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch vault data at block {block_number}: {e}", exc_info=True)
        return {
            "error": str(e),
            "unique_vaults": 0,
            "total_snapshots": 0,
            "snapshots": [],
            "enhanced_snapshots": [],
            "summary_metrics": {},
            "pricing_warnings": [],
            "block_number": block_number,
            "is_historical": True
        }


def format_snapshots_for_table(snapshots: List) -> List[Dict[str, Any]]:
    """
    Format CollateralVaultSnapshot objects for table display using new pricing mechanism.
    
    Args:
        snapshots: List of CollateralVaultSnapshot objects
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if not snapshots:
        return []
    
    # Calculate USD values using EVault pricing
    enhanced_snapshots, _ = calculate_multiple_snapshots_usd_values(snapshots)
    
    # Format enhanced snapshots for table
    return format_enhanced_snapshots_for_table(enhanced_snapshots)


def get_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the collateral vaults table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "Vault Address", "id": "Vault Address"},
        {"name": "Credit Vault", "id": "Credit Vault"},
        {"name": "Debt Vault", "id": "Debt Vault"},
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Twyne Liq LTV (%)", "id": "Twyne Liq LTV (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Can Liquidate", "id": "Can Liquidate"},
        {"name": "Externally Liquidated", "id": "Externally Liquidated"},
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Actions", "id": "Actions", "presentation": "markdown"}
    ]


def CollateralVaultsSection(section_id: str = "collateral-section") -> html.Div:
    """
    Create the collateral vaults section component.
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        Collateral vaults section component
    """
    refresh_button = dbc.Button(
        [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
        id=f"{section_id}-refresh",
        color="outline-primary",
        size="sm"
    )
    
    return SectionCard(
        title="Collateral Vaults",
        icon="fas fa-vault",
        action_button=refresh_button,
        children=[
            # Metrics container
            html.Div(id=f"{section_id}-metrics", className="mb-3"),
            
            # Status message container
            html.Div(id=f"{section_id}-status", className="mb-3"),
            
            # Credit Flow Sankey Diagram container
            html.Div(id=f"{section_id}-sankey-chart", className="mb-4"),
            
            # Health Factor Chart container
            html.Div(id=f"{section_id}-health-chart", className="mb-4"),
            
            # LTV vs Position Size Heatmap container
            html.Div(id=f"{section_id}-ltv-heatmap", className="mb-4"),
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


async def fetch_evaults_data() -> Dict[str, Any]:
    """
    Fetch EVault metrics and return summary data.
    
    Returns:
        Dict containing metrics or error information
    """
    try:
        logger.info("Fetching EVaults latest metrics...")
        
        # Fetch data using the API client
        response = await api_client.get_evaults_latest()
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "total_vaults": 0,
                "metrics": []
            }
        
        # Extract metrics from successful response
        metrics = response.latestMetrics or []
        total_vaults = len(metrics)
        
        logger.info(f"Successfully processed {total_vaults} EVault metrics")
        
        return {
            "error": None,
            "total_vaults": total_vaults,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch EVaults data: {e}", exc_info=True)
        return {
            "error": str(e),
            "total_vaults": 0,
            "metrics": []
        }


async def fetch_evaults_data_with_history(vault_type: str) -> Dict[str, Any]:
    """
    Fetch EVaults data and historical data in a single async function.
    
    Args:
        vault_type: Either "twyne" or "euler"
        
    Returns:
        Dict containing EVaults data and historical data
    """
    try:
        # Fetch EVaults data
        evaults_data = await fetch_evaults_data()
        
        if evaults_data["error"]:
            # Add empty fields for error case
            evaults_data["filtered_metrics"] = []
            evaults_data["vault_historical_data"] = []
            return evaults_data
        
        # Filter by vault type
        filtered_metrics = filter_evaults_by_type(evaults_data["metrics"], vault_type)
        
        # If we have filtered metrics, fetch historical data
        vault_historical_data = []
        if filtered_metrics:
            vault_addresses = list(set([metric.vaultAddress for metric in filtered_metrics]))
            logger.info(f"Fetching historical data for {len(vault_addresses)} {vault_type} vault(s)")
            logger.info(f"Vault addresses: {vault_addresses}")
            vault_historical_data = await fetch_evaults_historical_data(vault_addresses)
            logger.info(f"Received historical data for {len(vault_historical_data)} vault(s)")
        
        # Add filtered metrics and historical data to the response
        evaults_data["filtered_metrics"] = filtered_metrics
        evaults_data["vault_historical_data"] = vault_historical_data
        
        return evaults_data
        
    except Exception as e:
        logger.error(f"Failed to fetch EVaults data with history: {e}", exc_info=True)
        return {
            "error": str(e),
            "total_vaults": 0,
            "metrics": [],
            "filtered_metrics": [],
            "vault_historical_data": []
        }


async def fetch_evaults_historical_data(
    vault_addresses: List[str], 
    max_records_per_vault: int = 20000
) -> List[Dict[str, Any]]:
    """
    Fetch ALL historical data for multiple EVaults using pagination.
    
    Args:
        vault_addresses: List of vault addresses to fetch data for
        max_records_per_vault: Maximum records to fetch per vault (safety limit)
        
    Returns:
        List of dicts with vault_address, symbol, and metrics
    """
    vault_data = []
    total_vaults = len(vault_addresses)
    
    logger.info(f"Fetching ALL historical data for {total_vaults} vaults (max {max_records_per_vault} records per vault)")
    
    for i, vault_address in enumerate(vault_addresses, 1):
        try:
            logger.info(f"Fetching historical data for vault {i}/{total_vaults}: {vault_address}")
            logger.info(f"Vault address type: {type(vault_address)}, length: {len(vault_address)}")
            
            # Fetch all historical data using pagination
            all_metrics = []
            offset = 0
            limit = 1000  # Maximum allowed by API
            
            while len(all_metrics) < max_records_per_vault:
                logger.info(f"Fetching batch for {vault_address}: offset={offset}, limit={limit}")
                
                response = await api_client.get_evault_metrics(
                    address=vault_address,
                    limit=limit,
                    offset=offset
                )
                
                if isinstance(response, dict) and "error" in response:
                    logger.error(f"API error fetching batch for vault {vault_address}: {response['error']}")
                    logger.error(f"Full response: {response}")
                    break
                
                # Extract metrics from successful response
                batch_metrics = response.metrics or []
                total_count = getattr(response, 'totalCount', 0) or 0
                current_count = getattr(response, 'count', len(batch_metrics)) or len(batch_metrics)
                
                logger.info(f"API Response - batch_metrics: {len(batch_metrics)}, totalCount: {total_count}, count: {current_count}")
                logger.debug(f"Response object type: {type(response)}")
                logger.debug(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                
                if not batch_metrics:
                    logger.info(f"No more metrics found for vault {vault_address} at offset {offset}")
                    break
                
                all_metrics.extend(batch_metrics)
                logger.info(f"Fetched {len(batch_metrics)} metrics, total so far: {len(all_metrics)}/{total_count if total_count > 0 else 'unknown'}")
                
                # Check if we've fetched all available data
                # If totalCount is available and we've reached it, stop
                if total_count > 0 and len(all_metrics) >= total_count:
                    logger.info(f"Fetched all available data for vault {vault_address}: {len(all_metrics)}/{total_count} records")
                    break
                
                # If we got fewer metrics than requested, we've reached the end
                if len(batch_metrics) < limit:
                    logger.info(f"Reached end of data for vault {vault_address}: got {len(batch_metrics)} < {limit} requested")
                    break
                
                # Move to next batch
                offset += limit
                
                # Safety check to prevent infinite loops
                if len(all_metrics) >= max_records_per_vault:
                    logger.warning(f"Reached maximum records limit ({max_records_per_vault}) for vault {vault_address}")
                    break
            
            if not all_metrics:
                logger.warning(f"No historical metrics found for vault {vault_address}")
                continue
            
            # Get symbol from the first metric
            symbol = all_metrics[0].symbol if all_metrics else "Unknown"
            
            vault_data.append({
                "vault_address": vault_address,
                "symbol": symbol,
                "metrics": all_metrics
            })
            
            logger.info(f"Successfully fetched {len(all_metrics)} historical metrics for vault {vault_address} ({symbol})")
            
        except Exception as e:
            logger.error(f"Error fetching historical data for vault {vault_address}: {e}", exc_info=True)
            continue
    
    logger.info(f"Successfully fetched historical data for {len(vault_data)}/{total_vaults} vaults")
    return vault_data


def format_evaults_for_table(metrics: List) -> List[Dict[str, Any]]:
    """
    Format EVaultMetric objects for table display.
    
    Args:
        metrics: List of EVaultMetric objects
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if not metrics:
        return []
    
    table_data = []
    for metric in metrics:
        # Get decimals for proper scaling
        decimals = int(metric.decimals) if metric.decimals != "0" else 18
        scaling_factor = 10 ** decimals
        
        # Scale totalAssets and totalBorrows using decimals
        total_assets = float(metric.totalAssets) / scaling_factor if metric.totalAssets != "0" else 0.0
        total_borrows = float(metric.totalBorrows) / scaling_factor if metric.totalBorrows != "0" else 0.0
        
        # Calculate utilization rate
        utilization_rate = (total_borrows / total_assets * 100) if total_assets > 0 else 0.0
        
        # Format USD values - scale by 1e18 if they are very large
        total_assets_usd_raw = float(metric.totalAssetsUsd) if metric.totalAssetsUsd != "0" else 0.0
        total_assets_usd = total_assets_usd_raw / 1e18 if total_assets_usd_raw > 1e12 else total_assets_usd_raw
        
        total_borrows_usd_raw = float(metric.totalBorrowsUsd) if metric.totalBorrowsUsd != "0" else 0.0
        total_borrows_usd = total_borrows_usd_raw / 1e18 if total_borrows_usd_raw > 1e12 else total_borrows_usd_raw
        
        # Format interest rate as percentage
        interest_rate = float(metric.interestRate) / 1e18 * 100 if metric.interestRate != "0" else 0.0
        
        row = {
            "Chain ID": metric.chainId,
            "Vault Address": metric.vaultAddress[:10] + "..." if len(metric.vaultAddress) > 10 else metric.vaultAddress,
            "Full Vault Address": metric.vaultAddress,  # Store full address for navigation
            "Name": metric.name,
            "Symbol": metric.symbol,
            "Asset": metric.asset[:10] + "..." if len(metric.asset) > 10 else metric.asset,
            "Total Assets": total_assets,
            "Total Assets (USD)": total_assets_usd,
            "Total Borrows": total_borrows,
            "Total Borrows (USD)": total_borrows_usd,
            "Interest Rate (%)": interest_rate,
            "Utilization Rate (%)": utilization_rate,
            "Block Number": int(metric.blockNumber),
            "Block Timestamp": datetime.fromtimestamp(int(metric.blockTimestamp)).strftime("%Y-%m-%d %H:%M:%S"),
            "Actions": f"[More](/evaults/{metric.vaultAddress})"
        }
        table_data.append(row)
    
    return table_data


def get_evaults_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the EVaults table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "Vault Address", "id": "Vault Address"},
        {"name": "Name", "id": "Name"},
        {"name": "Symbol", "id": "Symbol"},
        {"name": "Asset", "id": "Asset"},
        {"name": "Total Assets", "id": "Total Assets", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Borrows", "id": "Total Borrows", "type": "numeric", "format": {"specifier": ",.4f"}},
        {"name": "Total Borrows (USD)", "id": "Total Borrows (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Interest Rate (%)", "id": "Interest Rate (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Utilization Rate (%)", "id": "Utilization Rate (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Actions", "id": "Actions", "presentation": "markdown"}
    ]


def EVaultsSection(section_id: str = "evaults-section") -> html.Div:
    """
    Create the EVaults section component.
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        EVaults section component
    """
    refresh_button = dbc.Button(
        [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
        id=f"{section_id}-refresh",
        color="outline-primary",
        size="sm"
    )
    
    # Vault type toggle component
    vault_type_toggle = dbc.Row([
        dbc.Col([
            html.Label("Vault Type:", className="fw-bold mb-2"),
            dbc.ButtonGroup([
                dbc.Button(
                    "Twyne",
                    id=f"{section_id}-twyne-btn",
                    color="primary",
                    outline=False,
                    size="sm"
                ),
                dbc.Button(
                    "Euler", 
                    id=f"{section_id}-euler-btn",
                    color="primary",
                    outline=True,
                    size="sm"
                )
            ])
        ], width="auto"),
        # Store for the selected vault type
        dcc.Store(id=f"{section_id}-vault-type", data="twyne")
    ], className="mb-3", justify="start")
    
    return SectionCard(
        title="EVaults",
        icon="fas fa-coins",
        action_button=refresh_button,
        children=[
            # Vault type toggle
            vault_type_toggle,
            
            # Metrics container
            html.Div(id=f"{section_id}-metrics", className="mb-3"),
            
            # Status message container
            html.Div(id=f"{section_id}-status", className="mb-3"),
            
            # Utilization chart container
            html.Div(id=f"{section_id}-utilization-chart", className="mb-3"),
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


# Callback for collateral vaults section
@callback(
    [Output("collateral-section-metrics", "children"),
     Output("collateral-section-status", "children"),
     Output("collateral-section-sankey-chart", "children"),
     Output("collateral-section-health-chart", "children"),
     Output("collateral-section-ltv-heatmap", "children"),
     Output("collateral-section-table", "children"),
     Output("collateral-section-last-updated", "children")],
    [Input("collateral-section-refresh", "n_clicks"),
     Input("url", "pathname"),
     Input("collateral-current-block", "data")],
    prevent_initial_call=False
)
def update_collateral_metrics(n_clicks, pathname, selected_block):
    """
    Update the collateral vaults metrics and table.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        pathname: Current URL path
        selected_block: Block number to fetch data for (None for latest)
        
    Returns:
        Tuple of (metrics_cards, status_message, sankey_chart, health_chart, ltv_heatmap, table_component, last_updated_text)
    """
    # Only update if we're on the collateral vaults page
    if pathname != "/collateralVaults":
        return [], "", "", "", "", "", ""
    
    if selected_block is not None:
        logger.info(f"Updating collateral vaults metrics for block {selected_block:,}...")
        data = run_async(fetch_collateral_vault_data_at_block(selected_block))
    else:
        logger.info("Updating collateral vaults metrics (latest data)...")
        data = run_async(fetch_collateral_vault_data())
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        sankey_chart = html.Div([
            html.P("Credit flow Sankey diagram unavailable due to API error", className="text-muted text-center p-4")
        ])
        health_chart = html.Div([
            html.P("Health Factor chart unavailable due to API error", className="text-muted text-center p-4")
        ])
        ltv_heatmap = html.Div([
            html.P("LTV vs Position Size heatmap unavailable due to API error", className="text-muted text-center p-4")
        ])
        table_component = ErrorState(
            error_message="Unable to load table data due to API error",
            retry_callback="collateral-section-refresh"
        )
    else:
        # Create status message with pricing warnings if any
        pricing_warning_summary = get_pricing_warnings_summary(data.get("pricing_warnings", []))
        
        # Determine if this is historical data
        is_historical = data.get("is_historical", False)
        block_number = data.get("block_number")
        block_timestamp = data.get("block_timestamp")
        
        success_alerts = []
        
        if is_historical and block_number:
            formatted_timestamp = datetime.fromtimestamp(block_timestamp).strftime("%Y-%m-%d %H:%M:%S") if block_timestamp else "Unknown"
            success_alerts.append(
                dbc.Alert(
                    f"Historical snapshot loaded for block {block_number:,} ({formatted_timestamp})", 
                    color="info",
                    dismissable=True,
                    duration=5000
                )
            )
        else:
            success_alerts.append(
                dbc.Alert(
                    "Latest data loaded successfully", 
                    color="success",
                    dismissable=True,
                    duration=3000
                )
            )
        
        if pricing_warning_summary:
            success_alerts.append(
                dbc.Alert(
                    pricing_warning_summary,
                    color="warning",
                    dismissable=True
                )
            )
        
        status_message = html.Div(success_alerts)
        
        # Use calculated summary metrics from enhanced snapshots
        summary_metrics = data.get("summary_metrics", {})
        
        # Create metrics cards using calculated values
        metrics_cards = dbc.Row([
            dbc.Col([
                MetricCard(
                    title="Total Collateral", 
                    value=f"${summary_metrics.get('total_user_collateral_usd', 0.0):,.2f}",
                    icon="fas fa-coins",
                    color="primary"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="Total Debt", 
                    value=f"${summary_metrics.get('total_max_repay_usd', 0.0):,.2f}",
                    icon="fas fa-exclamation-triangle",
                    color="warning"
                )
            ], width=12, md=6, lg=4),
            
            dbc.Col([
                MetricCard(
                    title="Total Credit Reserved", 
                    value=f"${summary_metrics.get('total_max_release_usd', 0.0):,.2f}",
                    icon="fas fa-piggy-bank",
                    color="success"
                )
            ], width=12, md=6, lg=4)
        ], className="g-3")
        
        # Create credit flow Sankey diagram
        enhanced_snapshots = data.get("enhanced_snapshots", [])
        if enhanced_snapshots:
            # Prepare Sankey data
            sankey_data = prepare_sankey_data_for_credit_flow(enhanced_snapshots)
            sankey_chart = html.Div([
                html.H5("Credit Flow Analysis", className="mb-3"),
                create_credit_flow_sankey(sankey_data, "Credit Vaults → Debt Vaults")
            ])
        else:
            sankey_chart = html.Div([
                html.H5("Credit Flow Analysis", className="mb-3"),
                html.P("No data available for credit flow analysis", className="text-muted text-center p-4")
            ])
        
        # Create health factor chart
        if enhanced_snapshots:
            # Calculate health factors for chart
            chart_data = calculate_health_factors_for_snapshots(enhanced_snapshots)
            health_chart = html.Div([
                html.H5("Health Factor Analysis", className="mb-3"),
                create_health_factor_scatter_plot(chart_data, "Debt USD vs Health Factor")
            ])
        else:
            health_chart = html.Div([
                html.H5("Health Factor Analysis", className="mb-3"),
                html.P("No data available for health factor analysis", className="text-muted text-center p-4")
            ])
        
        # Create LTV vs Position Size heatmap
        if enhanced_snapshots:
            # Calculate LTV and position size data for heatmap
            heatmap_data = calculate_ltv_position_data_for_heatmap(enhanced_snapshots)
            ltv_heatmap = html.Div([
                html.H5("User LTV vs Position Size Distribution", className="mb-3"),
                create_ltv_position_heatmap(heatmap_data, "Position Size vs User LTV Distribution")
            ])
        else:
            ltv_heatmap = html.Div([
                html.H5("User LTV vs Position Size Distribution", className="mb-3"),
                html.P("No data available for LTV vs Position Size heatmap", className="text-muted text-center p-4")
            ])
        
        # Create table component
        if data.get("enhanced_snapshots"):
            table_data = format_enhanced_snapshots_for_table(data["enhanced_snapshots"])
            table_component = html.Div([
                html.H5("Collateral Vaults Snapshots", className="mb-3"),
                dash_table.DataTable(
                    id="collateral-snapshots-table",
                    data=table_data,
                    columns=get_table_columns(),
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {'filter_query': '{Can Liquidate} = Yes'},
                            'backgroundColor': '#ffebee',
                            'color': 'black'
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display"
                )
            ])
        else:
            table_component = html.Div([
                html.H5("Collateral Vaults Snapshots", className="mb-3"),
                html.P("No snapshot data available", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    is_historical = data.get("is_historical", False)
    if is_historical:
        block_number = data.get("block_number")
        evault_prices_block = data.get("evault_prices_block")
        if evault_prices_block and evault_prices_block != block_number:
            last_updated = f"Historical snapshot at block {block_number:,} (prices from block {evault_prices_block:,}) - Updated: {datetime.now().strftime('%H:%M:%S')}"
        else:
            last_updated = f"Historical snapshot at block {block_number:,} - Updated: {datetime.now().strftime('%H:%M:%S')}"
    else:
        last_updated = f"Latest data - Updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, sankey_chart, health_chart, ltv_heatmap, table_component, last_updated


# Callback for vault type toggle
@callback(
    [Output("evaults-section-vault-type", "data"),
     Output("evaults-section-twyne-btn", "outline"),
     Output("evaults-section-euler-btn", "outline")],
    [Input("evaults-section-twyne-btn", "n_clicks"),
     Input("evaults-section-euler-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_vault_type_toggle(twyne_clicks, euler_clicks):
    """
    Update the vault type selection based on button clicks.
    
    Args:
        twyne_clicks: Number of clicks on Twyne button
        euler_clicks: Number of clicks on Euler button
        
    Returns:
        Tuple of (selected_type, twyne_outline, euler_outline)
    """
    # Determine which button was clicked
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return "twyne", False, True
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if "twyne" in button_id:
        return "twyne", False, True  # Twyne selected (not outlined), Euler not selected (outlined)
    else:
        return "euler", True, False  # Twyne not selected (outlined), Euler selected (not outlined)


def filter_evaults_by_type(metrics: List, vault_type: str) -> List:
    """
    Filter EVault metrics by vault type based on symbol prefix.
    
    Args:
        metrics: List of EVaultMetric objects
        vault_type: Either "twyne" or "euler"
        
    Returns:
        Filtered list of EVaultMetric objects
    """
    if not metrics:
        return []
    
    filtered_metrics = []
    for metric in metrics:
        symbol = metric.symbol
        
        if vault_type == "twyne":
            # Twyne vaults start with 'ee' (case-sensitive)
            if symbol.startswith("ee"):
                filtered_metrics.append(metric)
        elif vault_type == "euler":
            # Euler vaults start with 'e' but NOT 'ee' (case-sensitive)
            if symbol.startswith("e") and not symbol.startswith("ee"):
                filtered_metrics.append(metric)
    
    return filtered_metrics


# Callback for EVaults section
@callback(
    [Output("evaults-section-metrics", "children"),
     Output("evaults-section-status", "children"),
     Output("evaults-section-utilization-chart", "children"),
     Output("evaults-section-table", "children"),
     Output("evaults-section-last-updated", "children")],
    [Input("evaults-section-refresh", "n_clicks"),
     Input("evaults-section-vault-type", "data"),
     Input("url", "pathname")],
    prevent_initial_call=False
)
def update_evaults_metrics(n_clicks, vault_type, pathname):
    """
    Update the EVaults metrics and table.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        vault_type: Selected vault type ("twyne" or "euler")
        pathname: Current URL path
        
    Returns:
        Tuple of (metrics_cards, status_message, chart_component, table_component, last_updated_text)
    """
    # Only update if we're on the EVaults page
    if pathname != "/evaults":
        return [], "", "", "", ""
    
    logger.info(f"Updating EVaults metrics for {vault_type} vaults...")
    
    # Fetch the data and historical data in a single async call
    data = run_async(fetch_evaults_data_with_history(vault_type))
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        metrics_cards = []
        chart_component = html.Div([
            html.P("Utilization chart unavailable due to API error", className="text-muted text-center p-4")
        ])
        table_component = ErrorState(
            error_message="Unable to load table data due to API error",
            retry_callback="evaults-section-refresh"
        )
    else:
        status_message = dbc.Alert(
            "Data loaded successfully", 
            color="success",
            dismissable=True,
            duration=3000  # Auto-dismiss after 3 seconds
        )
        
        # Extract filtered metrics and historical data from the combined result
        filtered_metrics = data["filtered_metrics"]
        vault_historical_data = data["vault_historical_data"]
        
        logger.info(f"Filtered {len(filtered_metrics)} {vault_type} vaults from {len(data['metrics'])} total vaults")
        if filtered_metrics:
            symbols = [m.symbol for m in filtered_metrics]
            logger.info(f"Filtered vault symbols: {symbols}")
        
        # Calculate summary metrics with proper scaling using filtered data
        total_assets_usd = 0.0
        total_borrows_usd = 0.0
        
        for m in filtered_metrics:
            # Sum total assets USD
            if m.totalAssetsUsd != "0":
                assets_usd_raw = float(m.totalAssetsUsd)
                # Scale by 1e18 if value is very large
                assets_usd_scaled = assets_usd_raw / 1e18 if assets_usd_raw > 1e12 else assets_usd_raw
                total_assets_usd += assets_usd_scaled
            
            # Sum total borrows USD
            if m.totalBorrowsUsd != "0":
                borrows_usd_raw = float(m.totalBorrowsUsd)
                # Scale by 1e18 if value is very large
                borrows_usd_scaled = borrows_usd_raw / 1e18 if borrows_usd_raw > 1e12 else borrows_usd_raw
                total_borrows_usd += borrows_usd_scaled
        avg_utilization = 0.0
        if filtered_metrics:
            utilization_rates = []
            for m in filtered_metrics:
                total_assets = float(m.totalAssets) if m.totalAssets != "0" else 0.0
                total_borrows = float(m.totalBorrows) if m.totalBorrows != "0" else 0.0
                if total_assets > 0:
                    utilization_rates.append(total_borrows / total_assets * 100)
            avg_utilization = sum(utilization_rates) / len(utilization_rates) if utilization_rates else 0.0
        
        # Create metrics cards using filtered data
        filtered_vault_count = len(filtered_metrics)
        vault_type_display = vault_type.capitalize()
        
        metrics_cards = dbc.Row([
            dbc.Col([
                MetricCard(
                    title=f"{vault_type_display} Vaults", 
                    value=str(filtered_vault_count),
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
                    title="Total Borrows (USD)", 
                    value=f"${total_borrows_usd:,.2f}",
                    icon="fas fa-chart-line",
                    color="info"
                )
            ], width=12, md=6, lg=3),
            
            dbc.Col([
                MetricCard(
                    title="Avg Utilization", 
                    value=f"{avg_utilization:.2f}%",
                    icon="fas fa-percentage",
                    color="warning" if avg_utilization > 80 else "info"
                )
            ], width=12, md=6, lg=3)
        ], className="g-3")
        
        # Create table component using filtered data
        if filtered_metrics:
            table_data = format_evaults_for_table(filtered_metrics)
            table_component = html.Div([
                html.H5(f"{vault_type_display} EVaults Metrics", className="mb-3"),
                dash_table.DataTable(
                    id="evaults-metrics-table",
                    data=table_data,
                    columns=get_evaults_table_columns(),
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        },
                        {
                            'if': {
                                'filter_query': '{Utilization Rate (%)} > 80',
                                'column_id': 'Utilization Rate (%)'
                            },
                            'backgroundColor': '#ffebee',
                            'color': 'red'
                        },
                        {
                            'if': {
                                'filter_query': '{Utilization Rate (%)} > 90',
                                'column_id': 'Utilization Rate (%)'
                            },
                            'backgroundColor': '#ffcdd2',
                            'color': 'darkred',
                            'fontWeight': 'bold'
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display"
                )
            ])
        else:
            table_component = html.Div([
                html.H5(f"{vault_type_display} EVaults Metrics", className="mb-3"),
                html.P(f"No {vault_type_display} EVault metrics available", className="text-muted text-center p-4")
            ])
        
        # Create utilization chart using pre-fetched historical data
        chart_component = html.Div()
        if filtered_metrics and vault_historical_data:
            try:
                chart_component = html.Div([
                    html.H5(f"{vault_type_display} Vault Utilization Over Time (Hourly Intervals)", className="mb-3"),
                    create_multi_vault_utilization_chart(vault_historical_data)
                ])
            except Exception as e:
                logger.error(f"Error creating utilization chart: {e}", exc_info=True)
                chart_component = html.Div([
                    html.H5(f"{vault_type_display} Vault Utilization Over Time (Hourly Intervals)", className="mb-3"),
                    html.P("Error loading utilization chart", className="text-muted text-center p-4")
                ])
        elif filtered_metrics and not vault_historical_data:
            chart_component = html.Div([
                html.H5(f"{vault_type_display} Vault Utilization Over Time", className="mb-3"),
                html.P("No historical data available for utilization chart", className="text-muted text-center p-4")
            ])
        else:
            chart_component = html.Div([
                html.H5(f"{vault_type_display} Vault Utilization Over Time (Hourly Intervals)", className="mb-3"),
                html.P(f"No {vault_type_display} vaults available for chart", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return metrics_cards, status_message, chart_component, table_component, last_updated


# =======================
# Liquidations Section
# =======================


async def fetch_internal_liquidations(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Fetch internal liquidation events from API.
    
    Args:
        limit: Number of records to fetch
        offset: Offset for pagination
        
    Returns:
        Dict containing internal liquidations data or error information
    """
    try:
        logger.info(f"Fetching internal liquidations (limit={limit}, offset={offset})...")
        
        response = await api_client.get_internal_liquidations(limit=limit, offset=offset)
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "liquidations": [],
                "count": 0,
                "totalCount": 0
            }
        
        liquidations = response.internalLiquidations
        logger.info(f"Successfully fetched {len(liquidations)} internal liquidations")
        
        return {
            "error": None,
            "liquidations": liquidations,
            "count": response.count,
            "totalCount": response.totalCount
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch internal liquidations: {e}", exc_info=True)
        return {
            "error": str(e),
            "liquidations": [],
            "count": 0,
            "totalCount": 0
        }


async def fetch_external_liquidations(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Fetch external liquidation events from API.
    
    Args:
        limit: Number of records to fetch
        offset: Offset for pagination
        
    Returns:
        Dict containing external liquidations data or error information
    """
    try:
        logger.info(f"Fetching external liquidations (limit={limit}, offset={offset})...")
        
        response = await api_client.get_external_liquidations(limit=limit, offset=offset)
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "liquidations": [],
                "count": 0,
                "totalCount": 0
            }
        
        liquidations = response.externalLiquidations
        logger.info(f"Successfully fetched {len(liquidations)} external liquidations")
        
        return {
            "error": None,
            "liquidations": liquidations,
            "count": response.count,
            "totalCount": response.totalCount
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch external liquidations: {e}", exc_info=True)
        return {
            "error": str(e),
            "liquidations": [],
            "count": 0,
            "totalCount": 0
        }


def format_internal_liquidations_for_table(liquidations: List) -> List[Dict[str, Any]]:
    """
    Format internal liquidations data for DataTable display.
    
    Args:
        liquidations: List of InternalLiquidation objects
        
    Returns:
        List of dictionaries formatted for display
    """
    table_data = []
    
    for liq in liquidations:
        # Convert timestamps and block numbers
        block_timestamp = int(liq.block_timestamp)
        formatted_time = datetime.fromtimestamp(block_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format USD values (divide by 1e18)
        credit_reserved_usd = float(liq.credit_reserved_usd) / 1e18
        debt_usd = float(liq.debt_usd) / 1e18
        pre_total_collateral_usd = float(liq.pre_total_collateral_usd) / 1e18
        total_collateral_usd = float(liq.total_assets_deposited_or_reserved_usd) / 1e18
        
        # Calculate collateral change
        collateral_change = total_collateral_usd - pre_total_collateral_usd
        
        # Format LTV (divide by 1e18 and convert to percentage)
        ltv_value = float(liq.twyne_liq_ltv) / 1e18 * 100
        
        row = {
            "Block": int(liq.block_number),
            "Timestamp": formatted_time,
            "Collateral Vault": f"{liq.collateral_vault[:6]}...{liq.collateral_vault[-4:]}",
            "Collateral Vault Full": liq.collateral_vault,
            "Credit Vault": f"{liq.credit_vault[:6]}...{liq.credit_vault[-4:]}",
            "Debt Vault": f"{liq.debt_vault[:6]}...{liq.debt_vault[-4:]}",
            "Liquidator": f"{liq.liquidator_address[:6]}...{liq.liquidator_address[-4:]}",
            "Credit Reserved (USD)": f"${credit_reserved_usd:,.2f}",
            "Debt (USD)": f"${debt_usd:,.2f}",
            "Pre-Liq Collateral (USD)": f"${pre_total_collateral_usd:,.2f}",
            "Post-Liq Collateral (USD)": f"${total_collateral_usd:,.2f}",
            "Collateral Change (USD)": f"${collateral_change:,.2f}",
            "LTV (%)": f"{ltv_value:.2f}",
            "Txn Hash": f"{liq.txn_hash[:6]}...{liq.txn_hash[-4:]}"
        }
        table_data.append(row)
    
    return table_data


def format_external_liquidations_for_table(liquidations: List) -> List[Dict[str, Any]]:
    """
    Format external liquidations data for DataTable display.
    
    Args:
        liquidations: List of ExternalLiquidation objects
        
    Returns:
        List of dictionaries formatted for display
    """
    table_data = []
    
    for liq in liquidations:
        # Convert timestamps
        block_timestamp = int(liq.blockTimestamp)
        formatted_time = datetime.fromtimestamp(block_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format USD values (divide by 1e18)
        repay_assets_usd = float(liq.repayAssetsUsd) / 1e18
        yield_balance_usd = float(liq.yieldBalanceUsd) / 1e18
        pre_collateral_usd = float(liq.preCollateralAmountUsd) / 1e18
        post_collateral_usd = float(liq.collateralAmountUsd) / 1e18
        pre_debt_usd = float(liq.preDebtAmountUsd) / 1e18
        post_debt_usd = float(liq.debtAmountUsd) / 1e18
        
        # Calculate changes
        collateral_change = post_collateral_usd - pre_collateral_usd
        debt_change = post_debt_usd - pre_debt_usd
        
        # Format LTV (divide by 1e18 and convert to percentage)
        liq_ltv_value = float(liq.liqLtv) / 1e18 * 100

        ltv = (pre_debt_usd / pre_collateral_usd) * 100
        
        row = {
            "Block": int(liq.blockNumber),
            "Timestamp": formatted_time,
            "Debt Vault Address": f"{liq.vaultAddress[:6]}...{liq.vaultAddress[-4:]}",
            "Debt Vault Address Full": liq.vaultAddress,
            "Collateral Vault Address": f"{liq.collateral[:6]}...{liq.collateral[-4:]}",
            "Collateral Vault Address Full": liq.collateral,
            "Liquidator": f"{liq.liquidator[:6]}...{liq.liquidator[-4:]}",
            "Violator": f"{liq.violator[:6]}...{liq.violator[-4:]}",
            "Repay Assets (USD)": f"${repay_assets_usd:,.2f}",
            "Yield Balance (USD)": f"${yield_balance_usd:,.2f}",
            "Pre-Liq Collateral (USD)": f"${pre_collateral_usd:,.2f}",
            "Post-Liq Collateral (USD)": f"${post_collateral_usd:,.2f}",
            "Pre-Liq Debt (USD)": f"${pre_debt_usd:,.2f}",
            "Post-Liq Debt (USD)": f"${post_debt_usd:,.2f}",
            "LTV (%)": f"{ltv:.2f}",
            "LLTV (%)": f"{liq_ltv_value:.2f}",
            "Txn Hash": f"{liq.txnHash[:6]}...{liq.txnHash[-4:]}"
        }
        table_data.append(row)
    
    return table_data


def get_internal_liquidations_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for internal liquidations table.
    
    Returns:
        List of column definitions
    """
    return [
        {"name": "Block", "id": "Block"},
        {"name": "Timestamp", "id": "Timestamp"},
        {"name": "Collateral Vault", "id": "Collateral Vault"},
        {"name": "Credit Vault", "id": "Credit Vault"},
        {"name": "Debt Vault", "id": "Debt Vault"},
        {"name": "Liquidator", "id": "Liquidator"},
        {"name": "Credit Reserved (USD)", "id": "Credit Reserved (USD)"},
        {"name": "Debt (USD)", "id": "Debt (USD)"},
        {"name": "Pre-Liq Collateral (USD)", "id": "Pre-Liq Collateral (USD)"},
        {"name": "Post-Liq Collateral (USD)", "id": "Post-Liq Collateral (USD)"},
        {"name": "Collateral Change (USD)", "id": "Collateral Change (USD)"},
        {"name": "LTV (%)", "id": "LTV (%)"},
        {"name": "Txn Hash", "id": "Txn Hash"}
    ]


def get_external_liquidations_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for external liquidations table.
    
    Returns:
        List of column definitions
    """
    return [
        {"name": "Timestamp", "id": "Timestamp"},
        {"name": "Debt Vault Address", "id": "Debt Vault Address"},
        {"name": "Collateral Vault Address", "id": "Collateral Vault Address"},
        {"name": "Pre-Liq Collateral (USD)", "id": "Pre-Liq Collateral (USD)"},
        {"name": "Post-Liq Collateral (USD)", "id": "Post-Liq Collateral (USD)"},
        {"name": "Pre-Liq Debt (USD)", "id": "Pre-Liq Debt (USD)"},
        {"name": "Post-Liq Debt (USD)", "id": "Post-Liq Debt (USD)"},
        {"name": "LTV (%)", "id": "LTV (%)"},
        {"name": "LLTV (%)", "id": "LLTV (%)"},
        {"name": "Repay Assets (USD)", "id": "Repay Assets (USD)"},
        {"name": "Yield Balance (USD)", "id": "Yield Balance (USD)"},
        {"name": "Liquidator", "id": "Liquidator"},
        {"name": "Violator", "id": "Violator"},
        {"name": "Block", "id": "Block"},
        {"name": "Txn Hash", "id": "Txn Hash"}
    ]


def LiquidationsSection(section_id: str = "liquidations-section") -> html.Div:
    """
    Create the Liquidations section component with mode toggle.
    
    Args:
        section_id: Unique ID for the section
        
    Returns:
        Liquidations section component
    """
    refresh_button = dbc.Button(
        [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
        id=f"{section_id}-refresh",
        color="outline-primary",
        size="sm"
    )
    
    # Liquidation mode toggle component
    mode_toggle = dbc.Row([
        dbc.Col([
            html.Label("Liquidation Type:", className="fw-bold mb-2"),
            dbc.ButtonGroup([
                dbc.Button(
                    "Internal",
                    id=f"{section_id}-internal-btn",
                    color="primary",
                    outline=False,
                    size="sm"
                ),
                dbc.Button(
                    "External",
                    id=f"{section_id}-external-btn",
                    color="primary",
                    outline=True,
                    size="sm"
                )
            ])
        ], width="auto"),
        # Store for the selected mode
        dcc.Store(id=f"{section_id}-mode", data="internal")
    ], className="mb-3", justify="start")
    
    return SectionCard(
        title="Liquidations",
        icon="fas fa-bolt",
        action_button=refresh_button,
        children=[
            # Mode toggle
            mode_toggle,
            
            # Status message container
            html.Div(id=f"{section_id}-status", className="mb-3"),
            
            # Table container
            html.Div(id=f"{section_id}-table", className="mb-3"),
            
            # Last updated info
            html.Div([
                html.Small(id=f"{section_id}-last-updated", className="text-muted")
            ], className="text-end")
        ]
    )


# Callback for liquidation mode toggle
@callback(
    [Output("liquidations-section-mode", "data"),
     Output("liquidations-section-internal-btn", "outline"),
     Output("liquidations-section-external-btn", "outline")],
    [Input("liquidations-section-internal-btn", "n_clicks"),
     Input("liquidations-section-external-btn", "n_clicks")],
    prevent_initial_call=True
)
def update_liquidations_mode_toggle(internal_clicks, external_clicks):
    """
    Update the liquidation mode selection based on button clicks.
    
    Args:
        internal_clicks: Number of clicks on Internal button
        external_clicks: Number of clicks on External button
        
    Returns:
        Tuple of (selected_mode, internal_outline, external_outline)
    """
    from dash import callback_context
    ctx = callback_context
    if not ctx.triggered:
        return "internal", False, True
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if "internal" in button_id:
        return "internal", False, True  # Internal selected, External not selected
    else:
        return "external", True, False  # Internal not selected, External selected


# Callback for liquidations section
@callback(
    [Output("liquidations-section-status", "children"),
     Output("liquidations-section-table", "children"),
     Output("liquidations-section-last-updated", "children")],
    [Input("liquidations-section-refresh", "n_clicks"),
     Input("liquidations-section-mode", "data"),
     Input("url", "pathname")],
    prevent_initial_call=False
)
def update_liquidations_data(n_clicks, mode, pathname):
    """
    Update the liquidations table based on selected mode.
    
    Args:
        n_clicks: Number of times refresh button was clicked
        mode: Selected mode ("internal" or "external")
        pathname: Current URL path
        
    Returns:
        Tuple of (status_message, table_component, last_updated_text)
    """
    # Only update if we're on the liquidations page
    if pathname != "/liquidations":
        return "", "", ""
    
    logger.info(f"Updating liquidations data for {mode} mode...")
    
    # Fetch data based on mode
    if mode == "internal":
        data = run_async(fetch_internal_liquidations(limit=100))
        mode_display = "Internal"
    else:
        data = run_async(fetch_external_liquidations(limit=100))
        mode_display = "External"
    
    # Create status message
    if data["error"]:
        status_message = ErrorAlert(
            message=f"Failed to fetch {mode_display.lower()} liquidations: {data['error']}",
            title="API Error"
        )
        table_component = ErrorState(
            error_message=f"Unable to load {mode_display.lower()} liquidations data",
            retry_callback="liquidations-section-refresh"
        )
    else:
        status_message = dbc.Alert(
            f"Loaded {data['count']} {mode_display.lower()} liquidations (Total: {data['totalCount']})",
            color="success",
            dismissable=True,
            duration=3000
        )
        
        # Create table component
        liquidations = data.get("liquidations", [])
        
        if liquidations:
            if mode == "internal":
                table_data = format_internal_liquidations_for_table(liquidations)
                columns = get_internal_liquidations_table_columns()
            else:
                table_data = format_external_liquidations_for_table(liquidations)
                columns = get_external_liquidations_table_columns()
            
            table_component = html.Div([
                html.H5(f"{mode_display} Liquidations", className="mb-3"),
                dash_table.DataTable(
                    id=f"liquidations-{mode}-table",
                    data=table_data,
                    columns=columns,
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontFamily': 'Arial, sans-serif',
                        'fontSize': '14px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'minWidth': '100px',
                        'maxWidth': '200px'
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'textAlign': 'center'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    export_format="csv",
                    export_headers="display",
                    tooltip_data=[
                        {
                            column: {'value': str(row.get(f"{column} Full", row.get(column, ""))), 'type': 'markdown'}
                            for column in row.keys()
                        } for row in table_data
                    ],
                    tooltip_duration=None
                )
            ])
        else:
            table_component = html.Div([
                html.H5(f"{mode_display} Liquidations", className="mb-3"),
                html.P(f"No {mode_display.lower()} liquidations found", className="text-muted text-center p-4")
            ])
    
    # Last updated timestamp
    last_updated = f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return status_message, table_component, last_updated
