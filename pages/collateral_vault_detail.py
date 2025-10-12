"""
Collateral Vault Detail page for Risk Dashboard.
Displays historical snapshots for a specific collateral vault.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, callback, Output, Input, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

from src.components import PageContainer, SectionCard, LoadingState, ErrorState, ErrorAlert
from src.api import api_client
from src.utils.pricing import calculate_evault_token_price

# Configure logging
logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync callbacks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("Event loop is already running")
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# Register the page with Dash - using path_template for dynamic routing
dash.register_page(
    __name__, 
    path_template="/collateralVaults/<vault_address>", 
    title="Collateral Vault Detail - Risk Dashboard"
)


async def fetch_evault_historical_data(
    vault_addresses: List[str], 
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch historical EVault metrics for multiple vault addresses.
    
    Args:
        vault_addresses: List of vault addresses to fetch data for
        start_time: Start time filter (Unix timestamp)
        end_time: End time filter (Unix timestamp)
        
    Returns:
        Dict containing historical metrics data or error information
    """
    try:
        logger.info(f"Fetching historical EVault data for {len(vault_addresses)} vaults")
        
        all_metrics = {}
        errors = []
        
        # Fetch data for each vault
        for vault_address in vault_addresses:
            if not vault_address:
                continue
                
            logger.info(f"Fetching EVault metrics for {vault_address}")
            
            response = await api_client.get_evault_metrics(
                address=vault_address,
                limit=1000,  # High limit to get comprehensive history
                start_time=start_time,
                end_time=end_time
            )
            
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to fetch EVault data for {vault_address}: {response['error']}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
            
            metrics = getattr(response, 'metrics', []) or []
            if metrics:
                all_metrics[vault_address] = metrics
                logger.info(f"Fetched {len(metrics)} historical metrics for {vault_address}")
            else:
                error_msg = f"No historical metrics found for {vault_address}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        return {
            "error": None if not errors else "; ".join(errors),
            "metrics": all_metrics,
            "vault_count": len(all_metrics)
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch EVault historical data: {e}")
        return {
            "error": str(e),
            "metrics": {},
            "vault_count": 0
        }


async def fetch_vault_history_data(vault_address: str) -> Dict[str, Any]:
    """
    Fetch all historical events for a specific collateral vault.
    
    Args:
        vault_address: The vault address to fetch data for
        
    Returns:
        Dict containing history data or error information
    """
    try:
        logger.info(f"Fetching all historical data for collateral vault: {vault_address}")
        
        # Fetch all data using the API client with a high limit
        response = await api_client.get_collateral_vault_history(
            address=vault_address,
            limit=10000  # High limit to get all events
        )
        
        if isinstance(response, dict) and "error" in response:
            logger.error(f"API error: {response['error']}")
            return {
                "error": response["error"],
                "snapshots": []
            }
        
        # Extract snapshots from successful response
        snapshots = response.snapshots
        
        logger.info(f"Successfully fetched {len(snapshots)} historical snapshots for vault {vault_address}")
        
        return {
            "error": None,
            "snapshots": snapshots,
            "vault_address": vault_address
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch collateral vault history for {vault_address}: {e}")
        return {
            "error": str(e),
            "snapshots": []
        }


def safe_convert_bigint_to_int(value) -> int:
    """
    Safely convert BigInt, string, or numeric value to integer.
    
    Args:
        value: Value that might be BigInt, string, or number
        
    Returns:
        Integer value
    """
    if value is None:
        return 0
    
    # Handle string representations of numbers
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    
    # Handle BigInt or other numeric types
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def create_dataframe_from_snapshots(snapshots: List) -> pd.DataFrame:
    """
    Convert CollateralVaultSnapshot objects to a pandas DataFrame.
    
    Args:
        snapshots: List of CollateralVaultSnapshot objects
        
    Returns:
        pandas DataFrame with all snapshot data
    """
    if not snapshots:
        return pd.DataFrame()
    
    # Convert snapshots to list of dictionaries
    data = []
    for snapshot in snapshots:
        # Convert snapshot to dictionary using all fields from CollateralVaultSnapshot
        # Handle BigInt conversion for numeric fields
        row = {
            'chainId': str(snapshot.chainId),
            'vaultAddress': str(snapshot.vaultAddress),
            'underlyingCollateralVault': str(snapshot.underlyingCollateralVault),
            'creditVault': str(snapshot.creditVault),
            'debtVault': str(snapshot.debtVault),
            'maxRelease': safe_convert_bigint_to_int(snapshot.maxRelease),
            'maxRepay': safe_convert_bigint_to_int(snapshot.maxRepay),
            'totalAssetsDepositedOrReserved': safe_convert_bigint_to_int(snapshot.totalAssetsDepositedOrReserved),
            'userOwnedCollateral': safe_convert_bigint_to_int(snapshot.userOwnedCollateral),
            'twyneLiqLtv': safe_convert_bigint_to_int(snapshot.twyneLiqLtv),
            'canLiquidate': bool(snapshot.canLiquidate),
            'isExternallyLiquidated': bool(snapshot.isExternallyLiquidated),
            'maxReleaseUsd': safe_convert_bigint_to_int(snapshot.maxReleaseUsd),
            'maxRepayUsd': safe_convert_bigint_to_int(snapshot.maxRepayUsd),
            'totalAssetsDepositedOrReservedUsd': safe_convert_bigint_to_int(snapshot.totalAssetsDepositedOrReservedUsd),
            'userOwnedCollateralUsd': safe_convert_bigint_to_int(snapshot.userOwnedCollateralUsd),
            'blockNumber': safe_convert_bigint_to_int(snapshot.blockNumber),
            'blockTimestamp': safe_convert_bigint_to_int(snapshot.blockTimestamp),
            'logIndex': safe_convert_bigint_to_int(snapshot.logIndex),
            'state': str(snapshot.state),
            'txType': str(snapshot.txType)
        }
        data.append(row)
    
    # Create DataFrame - all numeric fields are now properly converted to integers
    df = pd.DataFrame(data)
    
    return df


def create_historical_usd_progression(
    snapshots_df: pd.DataFrame,
    evault_metrics: Dict[str, List]
) -> Tuple[Optional[go.Figure], List[str]]:
    """
    Create a line plot showing continuous USD progression of vault position over time.
    
    This creates a time-continuous chart where:
    1. Position amounts change at CollateralVault event timestamps
    2. USD values change continuously as asset prices change (from EVault data)
    3. The chart shows the evolution of the position in USD terms over time
    
    Args:
        snapshots_df: DataFrame with collateral vault snapshots (filtered for 'post' state)
        evault_metrics: Dict mapping vault addresses to their historical metrics
        
    Returns:
        Tuple of (plotly figure or None, error messages list)
    """
    errors = []
    
    try:
        if snapshots_df.empty:
            return None, ["No snapshot data available"]
        
        # Get unique vault addresses from snapshots
        credit_vault = snapshots_df['creditVault'].iloc[0] if 'creditVault' in snapshots_df.columns else None
        debt_vault = snapshots_df['debtVault'].iloc[0] if 'debtVault' in snapshots_df.columns else None
        underlying_vault = snapshots_df['underlyingCollateralVault'].iloc[0] if 'underlyingCollateralVault' in snapshots_df.columns else None
        
        if not all([credit_vault, debt_vault, underlying_vault]):
            return None, ["Missing vault address information in snapshots"]
        
        logger.info(f"Creating continuous USD progression for vaults: credit={credit_vault}, debt={debt_vault}, underlying={underlying_vault}")
        
        # Debug: Check the data types in the DataFrame
        logger.info(f"DataFrame dtypes: {snapshots_df.dtypes}")
        logger.info(f"Sample blockTimestamp values: {snapshots_df['blockTimestamp'].head().tolist()}")
        
        # Create price time series from EVault metrics
        price_time_series = {}
        all_timestamps = set()
        
        for vault_addr, metrics in evault_metrics.items():
            if not metrics:
                continue
                
            vault_prices = []
            for metric in metrics:
                price, error = calculate_evault_token_price(metric)
                if error:
                    errors.append(error)
                    continue
                
                # Safely convert BigInt timestamps and block numbers
                timestamp = safe_convert_bigint_to_int(metric.blockTimestamp)
                block_number = safe_convert_bigint_to_int(metric.blockNumber)
                
                vault_prices.append({
                    'timestamp': timestamp,
                    'price': price,
                    'blockNumber': block_number
                })
                all_timestamps.add(timestamp)
            
            if vault_prices:
                # Sort by timestamp
                vault_prices.sort(key=lambda x: x['timestamp'])
                price_time_series[vault_addr] = vault_prices
        
        if not price_time_series:
            return None, ["No valid price data available from EVault metrics"]
        
        # Create position time series from CollateralVault snapshots
        # Sort snapshots by timestamp (ascending)
        snapshots_sorted = snapshots_df.sort_values('blockTimestamp').copy()
        
        position_changes = []
        for _, snapshot in snapshots_sorted.iterrows():
            # All values should now be properly converted integers from the DataFrame
            timestamp = int(snapshot['blockTimestamp'])
            block_number = int(snapshot['blockNumber'])
            
            # Debug: Log the types and values
            logger.info(f"Processing snapshot - timestamp: {timestamp} (type: {type(timestamp)}), block: {block_number} (type: {type(block_number)})")
            
            position_changes.append({
                'timestamp': timestamp,
                'maxRelease': float(snapshot['maxRelease']) / 1e18,  # Convert to tokens
                'maxRepay': float(snapshot['maxRepay']) / 1e18,
                'userCollateral': float(snapshot['userOwnedCollateral']) / 1e18,
                'blockNumber': block_number
            })
            all_timestamps.add(timestamp)
        
        if not position_changes:
            return None, ["No position changes available"]
        
        # Determine the overall time range
        all_timestamps = sorted(list(all_timestamps))
        if not all_timestamps:
            return None, ["No timestamp data available"]
        
        latest_timestamp = max(all_timestamps)
        # Show progression up to 1 week before the latest available data
        end_timestamp = latest_timestamp
        start_timestamp = latest_timestamp - (7 * 24 * 3600)  # 1 week before
        
        logger.info(f"Creating progression from {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
        
        # Create a unified timeline using both EVault price points and position changes
        # This ensures we capture both price changes and position changes
        timeline_points = set()
        
        # Add all EVault price timestamps within our range
        for vault_prices in price_time_series.values():
            for price_point in vault_prices:
                if start_timestamp <= price_point['timestamp'] <= end_timestamp:
                    timeline_points.add(price_point['timestamp'])
        
        # Add all position change timestamps within our range
        for position in position_changes:
            if start_timestamp <= position['timestamp'] <= end_timestamp:
                timeline_points.add(position['timestamp'])
        
        if not timeline_points:
            return None, ["No data points available in the selected time range"]
        
        # Create the continuous progression data
        progression_data = []
        
        for timestamp in sorted(timeline_points):
            # Get current position amounts (latest position change before or at this timestamp)
            current_position = get_position_at_timestamp(position_changes, timestamp)
            if not current_position:
                # If no position exists yet, skip this timestamp
                continue
            
            # Get prices at this timestamp (using latest available prices before or at this timestamp)
            credit_price = get_latest_price_before_timestamp(price_time_series.get(credit_vault, []), timestamp)
            debt_price = get_latest_price_before_timestamp(price_time_series.get(debt_vault, []), timestamp)
            underlying_price = get_latest_price_before_timestamp(price_time_series.get(underlying_vault, []), timestamp)
            
            # Skip if we don't have prices for all vaults
            if credit_price == 0 or debt_price == 0 or underlying_price == 0:
                logger.debug(f"Skipping timestamp {timestamp} due to missing prices: credit={credit_price}, debt={debt_price}, underlying={underlying_price}")
                continue
            
            # Calculate USD values using current position and current prices
            max_release_usd = current_position['maxRelease'] * credit_price
            max_repay_usd = current_position['maxRepay'] * debt_price
            user_collateral_usd = current_position['userCollateral'] * underlying_price
            
            progression_data.append({
                'timestamp': timestamp,
                'datetime': datetime.fromtimestamp(timestamp),
                'maxReleaseUsd': max_release_usd,
                'maxRepayUsd': max_repay_usd,
                'userCollateralUsd': user_collateral_usd,
                'maxReleaseTokens': current_position['maxRelease'],
                'maxRepayTokens': current_position['maxRepay'],
                'userCollateralTokens': current_position['userCollateral'],
                'creditPrice': credit_price,
                'debtPrice': debt_price,
                'underlyingPrice': underlying_price
            })
        
        if not progression_data:
            # Provide detailed debugging information
            debug_info = []
            debug_info.append(f"Timeline points: {len(timeline_points)}")
            debug_info.append(f"Position changes: {len(position_changes)}")
            debug_info.append(f"Price time series vaults: {list(price_time_series.keys())}")
            
            for vault_addr, vault_prices in price_time_series.items():
                debug_info.append(f"Vault {vault_addr}: {len(vault_prices)} price points")
                if vault_prices:
                    first_price_time = datetime.fromtimestamp(vault_prices[0]['timestamp'])
                    last_price_time = datetime.fromtimestamp(vault_prices[-1]['timestamp'])
                    debug_info.append(f"  Price range: {first_price_time} to {last_price_time}")
            
            if position_changes:
                # Timestamps should now be properly converted integers
                first_timestamp = position_changes[0]['timestamp']
                last_timestamp = position_changes[-1]['timestamp']
                
                first_pos_time = datetime.fromtimestamp(first_timestamp)
                last_pos_time = datetime.fromtimestamp(last_timestamp)
                debug_info.append(f"Position range: {first_pos_time} to {last_pos_time}")
            
            debug_info.append(f"Target range: {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
            
            return None, [f"No data points could be calculated. Debug info: {'; '.join(debug_info)}"]
        
        # Create DataFrame for plotting
        plot_df = pd.DataFrame(progression_data)
        
        # Create the plot
        fig = go.Figure()
        
        # Add traces for each metric with enhanced hover information
        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['maxReleaseUsd'],
            mode='lines',
            name='Max Release (USD)',
            line=dict(color='#2E8B57', width=2),
            hovertemplate='<b>Max Release</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         'Tokens: %{customdata[0]:,.4f}<br>' +
                         'Price: $%{customdata[1]:,.6f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(plot_df['maxReleaseTokens'], plot_df['creditPrice']))
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['maxRepayUsd'],
            mode='lines',
            name='Max Repay (USD)',
            line=dict(color='#DC143C', width=2),
            hovertemplate='<b>Max Repay</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         'Tokens: %{customdata[0]:,.4f}<br>' +
                         'Price: $%{customdata[1]:,.6f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(plot_df['maxRepayTokens'], plot_df['debtPrice']))
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_df['datetime'],
            y=plot_df['userCollateralUsd'],
            mode='lines',
            name='User Collateral (USD)',
            line=dict(color='#4169E1', width=2),
            hovertemplate='<b>User Collateral</b><br>' +
                         'Date: %{x}<br>' +
                         'USD Value: $%{y:,.2f}<br>' +
                         'Tokens: %{customdata[0]:,.4f}<br>' +
                         'Price: $%{customdata[1]:,.6f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(plot_df['userCollateralTokens'], plot_df['underlyingPrice']))
        ))
        
        # Add vertical lines at position change timestamps
        try:
            position_change_times = []
            logger.info(f"Processing {len(position_changes)} position changes for vertical lines")
            
            for i, pos in enumerate(position_changes):
                timestamp = pos['timestamp']
                logger.info(f"Position change {i}: timestamp={timestamp}, type={type(timestamp)}")
                
                # Ensure it's a proper integer timestamp
                if isinstance(timestamp, (int, float)):
                    change_time = datetime.fromtimestamp(int(timestamp))
                    position_change_times.append(change_time)
                    logger.info(f"Converted to datetime: {change_time}")
                else:
                    logger.warning(f"Skipping invalid timestamp type: {type(timestamp)}")
            
            logger.info(f"Adding {len(position_change_times)} vertical lines to chart")
            
            # Only add vertical lines if we have valid timestamps
            for i, change_time in enumerate(position_change_times):
                logger.info(f"Adding vline {i}: {change_time} (type: {type(change_time)})")
                fig.add_vline(
                    x=change_time,
                    line_dash="dash",
                    line_color="rgba(128,128,128,0.5)",
                    line_width=1,
                    annotation_text="Position Change",
                    annotation_position="top"
                )
                
        except Exception as e:
            logger.error(f"Error adding position change markers: {e}", exc_info=True)
            # Continue without vertical lines
        
        # Update layout
        fig.update_layout(
            title={
                'text': 'Continuous USD Value Progression (Position × Asset Prices)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'color': '#2c3e50'}
            },
            xaxis_title='Date',
            yaxis_title='USD Value',
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=80, b=50),
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.5)'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                showline=True,
                linewidth=1,
                linecolor='rgba(128,128,128,0.5)',
                tickformat='$,.0f'
            ),
            height=500
        )
        
        logger.info(f"Created USD progression chart with {len(progression_data)} data points")
        return fig, errors
        
    except Exception as e:
        error_msg = f"Failed to create USD progression chart: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return None, [error_msg]


def get_position_at_timestamp(position_changes: List[Dict], target_timestamp: int) -> Optional[Dict]:
    """
    Get the current position amounts at a given timestamp.
    Returns the latest position change that occurred before or at the target timestamp.
    
    Args:
        position_changes: List of position change events sorted by timestamp
        target_timestamp: Target timestamp to find position for
        
    Returns:
        Position dict with maxRelease, maxRepay, userCollateral, or None if no position found
    """
    if not position_changes:
        return None
    
    # Find the latest position change that is not from the future
    current_position = None
    for position in position_changes:
        if position['timestamp'] <= target_timestamp:
            current_position = position
        else:
            break  # Since data is sorted, we can stop here
    
    return current_position


def get_price_at_timestamp(price_data: List[Dict], target_timestamp: int) -> float:
    """
    Get the price at a specific timestamp.
    For continuous progression, we want the exact price at this timestamp if available,
    otherwise the latest price before this timestamp.
    
    Args:
        price_data: List of price data points sorted by timestamp
        target_timestamp: Target timestamp to find price for
        
    Returns:
        Price value, or 0.0 if no suitable price found
    """
    if not price_data:
        return 0.0
    
    # First, check for exact timestamp match
    for price_point in price_data:
        if price_point['timestamp'] == target_timestamp:
            return price_point['price']
    
    # If no exact match, find the latest price before this timestamp
    latest_price = 0.0
    for price_point in price_data:
        if price_point['timestamp'] <= target_timestamp:
            latest_price = price_point['price']
        else:
            break  # Since data is sorted, we can stop here
    
    return latest_price


def get_latest_price_before_timestamp(price_data: List[Dict], target_timestamp: int) -> float:
    """
    Get the latest price available before or at the target timestamp.
    This handles the case where EVault data is stored at different intervals than CollateralVault snapshots.
    
    Args:
        price_data: List of price data points sorted by timestamp
        target_timestamp: Target timestamp to find price for
        
    Returns:
        Price value, or 0.0 if no suitable price found
    """
    if not price_data:
        return 0.0
    
    # Find the latest price that is not from the future
    latest_price = 0.0
    latest_timestamp = 0
    
    for price_point in price_data:
        if price_point['timestamp'] <= target_timestamp:
            if price_point['timestamp'] >= latest_timestamp:
                latest_price = price_point['price']
                latest_timestamp = price_point['timestamp']
        else:
            break  # Since data is sorted, we can stop here
    
    return latest_price


def format_dataframe_for_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Format DataFrame for Dash DataTable display.
    
    Args:
        df: pandas DataFrame with vault snapshot data
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    if df.empty:
        return []
    
    # Create a copy for formatting
    display_df = df.copy()
    
    # Format USD values (convert from wei to dollars)
    usd_columns = ['maxReleaseUsd', 'maxRepayUsd', 'totalAssetsDepositedOrReservedUsd', 'userOwnedCollateralUsd']
    for col in usd_columns:
        if col in display_df.columns:
            display_df[f'{col}_formatted'] = display_df[col] / 1e18
    
    # Format Twyne LTV as percentage
    if 'twyneLiqLtv' in display_df.columns:
        display_df['twyneLiqLtv_percentage'] = (display_df['twyneLiqLtv'] / 1e4) * 100
    
    # Format timestamp for display
    if 'blockTimestamp_datetime' in display_df.columns:
        display_df['blockTimestamp_formatted'] = display_df['blockTimestamp_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Select and rename columns for display
    table_data = []
    for _, row in display_df.iterrows():
        formatted_row = {
            'Block Number': int(row['blockNumber']),
            'Block Timestamp': row.get('blockTimestamp_formatted', ''),
            'Chain ID': row['chainId'],
            'State': row['state'],
            'TX Type': row['txType'],
            'Credit Vault': row['creditVault'],
            'Debt Vault': row['debtVault'],
            'Max Release (USD)': row.get('maxReleaseUsd_formatted', 0.0),
            'Max Repay (USD)': row.get('maxRepayUsd_formatted', 0.0),
            'Total Assets (USD)': row.get('totalAssetsDepositedOrReservedUsd_formatted', 0.0),
            'User Collateral (USD)': row.get('userOwnedCollateralUsd_formatted', 0.0),
            'Twyne Liq LTV (%)': row.get('twyneLiqLtv_percentage', 0.0),
            'Can Liquidate': 'Yes' if row['canLiquidate'] else 'No',
            'Externally Liquidated': 'Yes' if row['isExternallyLiquidated'] else 'No',
            'Log Index': int(row['logIndex'])
        }
        table_data.append(formatted_row)
    
    return table_data


def get_table_columns() -> List[Dict[str, str]]:
    """
    Get column definitions for the vault history table.
    
    Returns:
        List of column definitions for DataTable
    """
    return [
        {"name": "Block Number", "id": "Block Number", "type": "numeric"},
        {"name": "Block Timestamp", "id": "Block Timestamp"},
        {"name": "Chain ID", "id": "Chain ID"},
        {"name": "State", "id": "State"},
        {"name": "TX Type", "id": "TX Type"},
        {"name": "Credit Vault", "id": "Credit Vault"},
        {"name": "Debt Vault", "id": "Debt Vault"},
        {"name": "Max Release (USD)", "id": "Max Release (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Max Repay (USD)", "id": "Max Repay (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Total Assets (USD)", "id": "Total Assets (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "User Collateral (USD)", "id": "User Collateral (USD)", "type": "numeric", "format": {"specifier": "$,.2f"}},
        {"name": "Twyne Liq LTV (%)", "id": "Twyne Liq LTV (%)", "type": "numeric", "format": {"specifier": ".2f"}},
        {"name": "Can Liquidate", "id": "Can Liquidate"},
        {"name": "Externally Liquidated", "id": "Externally Liquidated"},
        {"name": "Log Index", "id": "Log Index", "type": "numeric"}
    ]


def layout(vault_address: str = None):
    """
    Define the layout for the collateral vault detail page.
    
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
            dcc.Location(id="collateral-vault-detail-url", refresh=False),
            
            # Store vault address for callbacks
            dcc.Store(id="collateral-vault-address-store", data=vault_address),
            
            # Back navigation
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-arrow-left me-2"), "Back to Collateral Vaults"],
                    href="/collateralVaults",
                    color="outline-secondary",
                    size="sm",
                    className="mb-3"
                )
            ]),
            
            # Page title
            html.Div([
                html.H2([
                    html.I(className="fas fa-vault me-2"),
                    f"Collateral Vault Details"
                ], className="mb-2"),
                html.P([
                    html.Strong("Address: "),
                    html.Code(vault_address, className="bg-light p-1")
                ], className="text-muted mb-4")
            ]),
            
            # USD Progression Chart section
            SectionCard(
                title="Historical USD Value Progression",
                icon="fas fa-chart-line",
                children=[
                    # Chart status message container
                    html.Div(id="collateral-vault-chart-status", className="mb-3"),
                    
                    # Chart container
                    html.Div(id="collateral-vault-chart", className="mb-3"),
                ]
            ),
            
            # Data table section
            SectionCard(
                title="Vault History (Post State Events)",
                icon="fas fa-history",
                action_button=dbc.Button(
                    [html.I(className="fas fa-sync-alt me-2"), "Refresh"],
                    id="collateral-vault-detail-refresh",
                    color="outline-primary",
                    size="sm"
                ),
                children=[
                    # Status message container
                    html.Div(id="collateral-vault-detail-status", className="mb-3"),
                    
                    # Table container
                    html.Div(id="collateral-vault-detail-table", className="mb-3"),
                    
                    # Last updated info
                    html.Div([
                        html.Small(id="collateral-vault-detail-last-updated", className="text-muted")
                    ], className="text-end")
                ]
            )
        ]
    )


# Main callback for collateral vault detail page
@callback(
    [Output("collateral-vault-chart-status", "children"),
     Output("collateral-vault-chart", "children"),
     Output("collateral-vault-detail-status", "children"),
     Output("collateral-vault-detail-table", "children"),
     Output("collateral-vault-detail-last-updated", "children")],
    [Input("collateral-vault-detail-refresh", "n_clicks"),
     Input("collateral-vault-detail-url", "pathname")],
    [State("collateral-vault-address-store", "data")],
    prevent_initial_call=False
)
def update_collateral_vault_detail(n_clicks_refresh, pathname, vault_address):
    """
    Update the collateral vault detail chart and table with post-state events.
    
    Args:
        n_clicks_refresh: Number of times refresh button was clicked
        pathname: Current URL path
        vault_address: Vault address from store
        
    Returns:
        Tuple of (chart_status, chart_component, table_status, table_component, last_updated_text)
    """
    if not vault_address or not pathname.startswith("/collateralVaults/"):
        return "", "", "", "", ""
    
    logger.info(f"Loading vault history for {vault_address}")
    
    # Fetch all historical data
    data = run_async(fetch_vault_history_data(vault_address))
    
    # Check for errors
    if data["error"]:
        error_status = ErrorAlert(
            message=f"Failed to fetch data: {data['error']}",
            title="API Error"
        )
        error_table = ErrorState(
            error_message="Unable to load history data due to API error",
            retry_callback="collateral-vault-detail-refresh"
        )
        return error_status, "", error_status, error_table, ""
    
    # Convert to DataFrame
    df = create_dataframe_from_snapshots(data["snapshots"])
    
    if df.empty:
        warning_status = dbc.Alert(
            "No historical data available for this vault", 
            color="warning"
        )
        empty_table = html.Div([
            html.H5("Vault History", className="mb-3"),
            html.P("No history data available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return warning_status, "", warning_status, empty_table, last_updated
    
    # Filter for only "post" state events
    post_df = df[df['state'] == 'post'].copy()
    
    if post_df.empty:
        warning_status = dbc.Alert(
            f"Loaded {len(df)} total events, but no 'post' state events found", 
            color="warning"
        )
        empty_table = html.Div([
            html.H5("Vault History (Post State Events)", className="mb-3"),
            html.P("No 'post' state events available", className="text-muted text-center p-4")
        ])
        last_updated = f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        return warning_status, "", warning_status, empty_table, last_updated
    
    # Sort by block number descending (most recent first)
    post_df = post_df.sort_values('blockNumber', ascending=False)
    
    # Get vault addresses for EVault data fetching
    unique_vaults = set()
    if not post_df.empty:
        credit_vault = post_df['creditVault'].iloc[0]
        debt_vault = post_df['debtVault'].iloc[0]
        underlying_vault = post_df['underlyingCollateralVault'].iloc[0]
        unique_vaults = {credit_vault, debt_vault, underlying_vault}
    
    # Determine time range for EVault data
    # Use a broader range to ensure we have sufficient price data
    if not post_df.empty:
        # Values should now be properly converted integers from the DataFrame
        latest_timestamp = int(post_df['blockTimestamp'].max())
        earliest_timestamp = int(post_df['blockTimestamp'].min())
    else:
        latest_timestamp = int(datetime.now().timestamp())
        earliest_timestamp = latest_timestamp - (7 * 24 * 3600)
    
    # Extend the range to ensure we have price data before the first position
    buffer_time = 14 * 24 * 3600  # 2 weeks buffer for price data
    evault_start_time = earliest_timestamp - buffer_time
    evault_end_time = latest_timestamp + (24 * 3600)  # 1 day after for safety
    
    # Fetch EVault historical data for the vault addresses
    chart_component = ""
    chart_status = ""
    
    if unique_vaults:
        logger.info(f"Fetching EVault data for vaults: {unique_vaults}")
        evault_data = run_async(fetch_evault_historical_data(
            list(unique_vaults),
            start_time=evault_start_time,
            end_time=evault_end_time
        ))
        
        if evault_data["error"]:
            chart_status = dbc.Alert(
                f"Chart unavailable: {evault_data['error']}", 
                color="warning"
            )
            chart_component = html.Div([
                html.P("Unable to load historical price data for chart", className="text-muted text-center p-4")
            ])
        else:
            # Create the USD progression chart
            fig, chart_errors = create_historical_usd_progression(post_df, evault_data["metrics"])
            
            if fig is None:
                chart_status = dbc.Alert(
                    f"Chart creation failed: {'; '.join(chart_errors) if chart_errors else 'Unknown error'}", 
                    color="warning"
                )
                chart_component = html.Div([
                    html.P("Unable to create USD progression chart", className="text-muted text-center p-4")
                ])
            else:
                chart_status = dbc.Alert(
                    f"Chart created with {evault_data['vault_count']} EVault price sources", 
                    color="success",
                    dismissable=True,
                    duration=4000
                )
                if chart_errors:
                    chart_status = html.Div([
                        chart_status,
                        dbc.Alert(
                            f"Warnings: {'; '.join(chart_errors[:3])}{'...' if len(chart_errors) > 3 else ''}", 
                            color="warning",
                            dismissable=True
                        )
                    ])
                
                chart_component = dcc.Graph(
                    figure=fig,
                    config={
                        'displayModeBar': True,
                        'displaylogo': False,
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                    }
                )
    else:
        chart_status = dbc.Alert(
            "No vault addresses available for chart creation", 
            color="warning"
        )
        chart_component = html.Div([
            html.P("No vault data available for chart", className="text-muted text-center p-4")
        ])
    
    # Create table status message
    table_status = dbc.Alert(
        f"Loaded {len(post_df)} 'post' state events out of {len(df)} total events", 
        color="success",
        dismissable=True,
        duration=4000
    )
    
    # Format data for table
    table_data = format_dataframe_for_table(post_df)
    
    # Create table component
    table_component = html.Div([
        html.H5("Vault History (Post State Events)", className="mb-3"),
        dash_table.DataTable(
            id="collateral-vault-history-table",
            data=table_data,
            columns=get_table_columns(),
            page_size=25,
            sort_action="native",
            filter_action="native",
            sort_by=[{"column_id": "Block Number", "direction": "desc"}],
            style_cell={
                'textAlign': 'left',
                'padding': '12px',
                'fontFamily': 'Arial, sans-serif',
                'fontSize': '14px',
                'whiteSpace': 'nowrap',
                'height': 'auto',
                'maxWidth': '200px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis'
            },
            style_cell_conditional=[
                {
                    'if': {'column_id': ['Credit Vault', 'Debt Vault']},
                    'maxWidth': '120px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'nowrap'
                }
            ],
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
                },
                {
                    'if': {'filter_query': '{Externally Liquidated} = Yes'},
                    'backgroundColor': '#fff3e0',
                    'color': 'black'
                }
            ],
            style_table={'overflowX': 'auto'},
            export_format="csv",
            export_headers="display"
        )
    ])
    
    # Last updated timestamp
    last_updated = f"Showing {len(post_df)} post-state events - Updated: {datetime.now().strftime('%H:%M:%S')}"
    
    return chart_status, chart_component, table_status, table_component, last_updated