"""
Block-time snapshot utilities for collateral vaults.
Implements functionality to get snapshots of all collateral vaults at a given block.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from dataclasses import dataclass

from src.api import api_client
from .pricing import calculate_collateral_usd_values, create_evault_price_lookup

logger = logging.getLogger(__name__)


@dataclass
class BlockSnapshot:
    """Data class for a complete block-time snapshot of all collateral vaults."""
    target_block: int
    timestamp: Optional[int]
    vault_snapshots: List[Dict[str, Any]]
    total_vaults: int
    pricing_errors: List[str]
    fetch_errors: List[str]
    evault_prices_block: Optional[int]  # Block number where prices were fetched from


def get_all_vault_addresses_up_to_block(target_block: int) -> Tuple[Set[str], List[str]]:
    """
    Get all collateral vault addresses that have been created up to a given block.
    
    Args:
        target_block: Block number to search up to
        
    Returns:
        Tuple of (set_of_vault_addresses, error_messages_list)
    """
    vault_addresses = set()
    error_messages = []
    
    try:
        logger.info(f"Discovering collateral vaults created up to block {target_block}")
        
        # Fetch all created collateral vaults
        # We'll use pagination to get all vaults
        limit = 100
        offset = 0
        total_fetched = 0
        
        while True:
            response = api_client.get_collateral_vaults(limit=limit, offset=offset)
            
            if isinstance(response, dict) and "error" in response:
                error_msg = f"Failed to fetch collateral vaults: {response['error']}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                break
            
            vaults = response.vaults
            if not vaults:
                break
            
            # Filter vaults created up to target block
            for vault in vaults:
                vault_block = int(vault.blockNumber)
                if vault_block <= target_block:
                    vault_addresses.add(vault.vaultAddress)
                    total_fetched += 1
                else:
                    # Since vaults are likely ordered by creation time,
                    # we can potentially break early here
                    logger.debug(f"Vault {vault.vaultAddress} created at block {vault_block} > target {target_block}")
            
            # Check if we got less than limit (last page)
            if len(vaults) < limit:
                break
            
            offset += limit
            
            # Safety check to prevent infinite loops
            if offset > 10000:  # Arbitrary large number
                error_msg = f"Safety limit reached while fetching vaults (offset: {offset})"
                logger.warning(error_msg)
                error_messages.append(error_msg)
                break
        
        logger.info(f"Found {len(vault_addresses)} unique vault addresses created up to block {target_block}")
        
        return vault_addresses, error_messages
        
    except Exception as e:
        error_msg = f"Unexpected error discovering vault addresses: {str(e)}"
        logger.error(error_msg, exc_info=True)
        error_messages.append(error_msg)
        return vault_addresses, error_messages


def get_evault_prices_at_block(target_block: int) -> Tuple[Dict[str, float], int, List[str]]:
    """
    Get EVault prices at or before a specific block number.
    
    Args:
        target_block: Block number to get prices for
        
    Returns:
        Tuple of (price_lookup_dict, actual_block_used, error_messages_list)
    """
    error_messages = []
    price_lookup = {}
    actual_block = None
    
    try:
        logger.info(f"Fetching EVault prices at or before block {target_block}")
        
        # First, get all EVault addresses from latest data
        # This gives us the list of vaults to query historically
        latest_response = api_client.get_evaults_latest()
        
        if isinstance(latest_response, dict) and "error" in latest_response:
            error_msg = f"Failed to get EVault addresses: {latest_response['error']}"
            logger.error(error_msg)
            error_messages.append(error_msg)
            return price_lookup, actual_block, error_messages
        
        latest_metrics = getattr(latest_response, 'latestMetrics', []) or []
        if not latest_metrics:
            error_msg = "No EVault metrics available for price calculation"
            logger.error(error_msg)
            error_messages.append(error_msg)
            return price_lookup, actual_block, error_messages
        
        # Get unique vault addresses
        vault_addresses = set()
        for metric in latest_metrics:
            vault_address = getattr(metric, 'vaultAddress', None)
            if vault_address:
                vault_addresses.add(vault_address)
        
        logger.info(f"Found {len(vault_addresses)} EVault addresses to query for historical prices")
        
        # For each vault, get historical metrics up to target block
        all_historical_metrics = []
        blocks_found = set()
        
        for vault_address in vault_addresses:
            try:
                # Query historical metrics for this vault up to target block
                response = api_client.get_evault_metrics(
                    address=vault_address,
                    limit=1,  # We only need the latest metric at or before target block
                    end_block=target_block
                )
                
                if isinstance(response, dict) and "error" in response:
                    error_msg = f"Failed to get historical metrics for vault {vault_address}: {response['error']}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)
                    continue
                
                metrics = getattr(response, 'metrics', []) or []
                if metrics:
                    # Take the most recent metric (should be closest to target block)
                    latest_metric = metrics[0]
                    metric_block = int(latest_metric.blockNumber)
                    
                    if metric_block <= target_block:
                        all_historical_metrics.append(latest_metric)
                        blocks_found.add(metric_block)
                        logger.debug(f"Found metric for vault {vault_address} at block {metric_block}")
                    else:
                        logger.debug(f"Metric for vault {vault_address} at block {metric_block} is after target {target_block}")
                else:
                    error_msg = f"No historical metrics found for vault {vault_address} up to block {target_block}"
                    logger.warning(error_msg)
                    error_messages.append(error_msg)
                    
            except Exception as e:
                error_msg = f"Error fetching metrics for vault {vault_address}: {str(e)}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                continue
        
        if not all_historical_metrics:
            error_msg = f"No historical EVault metrics found for any vault at or before block {target_block}"
            logger.error(error_msg)
            error_messages.append(error_msg)
            return price_lookup, actual_block, error_messages
        
        # Determine the actual block we're using (should be the same or very close for all vaults)
        if blocks_found:
            actual_block = max(blocks_found)  # Use the highest block number found
        
        # Create price lookup from historical metrics
        price_lookup, price_errors = create_evault_price_lookup(all_historical_metrics)
        error_messages.extend(price_errors)
        
        logger.info(f"Successfully created price lookup for {len(price_lookup)} vaults at block {actual_block}")
        
        return price_lookup, actual_block, error_messages
        
    except Exception as e:
        error_msg = f"Unexpected error fetching EVault prices at block {target_block}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        error_messages.append(error_msg)
        return price_lookup, actual_block, error_messages


def get_vault_snapshot_at_block(
    vault_address: str, 
    target_block: int
) -> Tuple[Optional[Any], List[str]]:
    """
    Get the closest snapshot for a specific vault at or before a target block.
    
    Args:
        vault_address: Address of the collateral vault
        target_block: Block number to get snapshot for
        
    Returns:
        Tuple of (snapshot_object_or_none, error_messages_list)
    """
    error_messages = []
    
    try:
        logger.debug(f"Fetching snapshot for vault {vault_address} at or before block {target_block}")
        
        # Get historical snapshots for this vault up to target block
        response = api_client.get_collateral_vault_history(
            address=vault_address,
            limit=1,  # Only need the most recent snapshot
            end_block=target_block
        )
        
        if isinstance(response, dict) and "error" in response:
            error_msg = f"Failed to get snapshot for vault {vault_address}: {response['error']}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
            return None, error_messages
        
        snapshots = getattr(response, 'snapshots', []) or []
        if not snapshots:
            error_msg = f"No snapshots found for vault {vault_address} at or before block {target_block}"
            logger.debug(error_msg)
            error_messages.append(error_msg)
            return None, error_messages
        
        # Return the most recent snapshot (should be closest to target block)
        snapshot = snapshots[0]
        snapshot_block = int(snapshot.blockNumber)
        
        if snapshot_block <= target_block:
            logger.debug(f"Found snapshot for vault {vault_address} at block {snapshot_block}")
            return snapshot, error_messages
        else:
            error_msg = f"Snapshot for vault {vault_address} at block {snapshot_block} is after target {target_block}"
            logger.warning(error_msg)
            error_messages.append(error_msg)
            return None, error_messages
        
    except Exception as e:
        error_msg = f"Error fetching snapshot for vault {vault_address}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        error_messages.append(error_msg)
        return None, error_messages


def create_block_snapshot(target_block: int) -> BlockSnapshot:
    """
    Create a comprehensive snapshot of all collateral vaults at a given block.
    
    This is the main function that orchestrates the entire process:
    1. Discover all vault addresses created up to target block
    2. Get EVault prices at or before target block  
    3. Fetch the closest snapshot for each vault
    4. Price the native amounts using historical prices
    
    Args:
        target_block: Block number to create snapshot for
        
    Returns:
        BlockSnapshot object with comprehensive data
    """
    logger.info(f"Creating comprehensive block snapshot for block {target_block}")
    
    all_errors = []
    vault_snapshots = []
    
    # Step 1: Discover all vault addresses
    vault_addresses, discovery_errors = get_all_vault_addresses_up_to_block(target_block)
    all_errors.extend(discovery_errors)
    
    if not vault_addresses:
        logger.error(f"No vault addresses found up to block {target_block}")
        return BlockSnapshot(
            target_block=target_block,
            timestamp=None,
            vault_snapshots=[],
            total_vaults=0,
            pricing_errors=[],
            fetch_errors=all_errors,
            evault_prices_block=None
        )
    
    # Step 2: Get EVault prices at target block
    evault_prices, prices_block, pricing_errors = get_evault_prices_at_block(target_block)
    all_errors.extend(pricing_errors)
    
    if not evault_prices:
        logger.error(f"No EVault prices available for block {target_block}")
        return BlockSnapshot(
            target_block=target_block,
            timestamp=None,
            vault_snapshots=[],
            total_vaults=len(vault_addresses),
            pricing_errors=pricing_errors,
            fetch_errors=all_errors,
            evault_prices_block=prices_block
        )
    
    # Step 3: Fetch snapshots for each vault and price them
    successful_snapshots = 0
    snapshot_timestamp = None
    
    for vault_address in vault_addresses:
        snapshot, snapshot_errors = get_vault_snapshot_at_block(vault_address, target_block)
        all_errors.extend(snapshot_errors)
        
        if snapshot is None:
            continue
        
        # Get prices for this snapshot's vaults
        credit_vault = getattr(snapshot, 'creditVault', '')
        debt_vault = getattr(snapshot, 'debtVault', '')
        
        credit_price = evault_prices.get(credit_vault, 0.0)
        debt_price = evault_prices.get(debt_vault, 0.0)
        
        if credit_price == 0.0:
            error_msg = f"No price available for credit vault {credit_vault}"
            all_errors.append(error_msg)
        
        if debt_price == 0.0:
            error_msg = f"No price available for debt vault {debt_vault}"
            all_errors.append(error_msg)
        
        # Calculate USD values using historical prices
        usd_values, calc_errors = calculate_collateral_usd_values(
            snapshot, credit_price, debt_price
        )
        all_errors.extend(calc_errors)
        
        # Create enhanced snapshot data
        enhanced_snapshot = {
            'vault_address': vault_address,
            'original_snapshot': snapshot,
            'calculated_usd_values': usd_values,
            'credit_vault': credit_vault,
            'debt_vault': debt_vault,
            'credit_price': credit_price,
            'debt_price': debt_price,
            'snapshot_block': int(snapshot.blockNumber),
            'has_pricing_errors': len(calc_errors) > 0
        }
        
        vault_snapshots.append(enhanced_snapshot)
        successful_snapshots += 1
        
        # Set timestamp from first valid snapshot
        if snapshot_timestamp is None:
            snapshot_timestamp = int(snapshot.blockTimestamp)
    
    logger.info(f"Successfully created block snapshot with {successful_snapshots}/{len(vault_addresses)} vaults")
    
    return BlockSnapshot(
        target_block=target_block,
        timestamp=snapshot_timestamp,
        vault_snapshots=vault_snapshots,
        total_vaults=len(vault_addresses),
        pricing_errors=pricing_errors,
        fetch_errors=all_errors,
        evault_prices_block=prices_block
    )


def format_block_snapshot_summary(block_snapshot: BlockSnapshot) -> Dict[str, Any]:
    """
    Create a summary of the block snapshot for display purposes.
    
    Args:
        block_snapshot: BlockSnapshot object
        
    Returns:
        Dictionary with summary metrics
    """
    if not block_snapshot.vault_snapshots:
        return {
            'target_block': block_snapshot.target_block,
            'timestamp': block_snapshot.timestamp,
            'total_vaults_discovered': block_snapshot.total_vaults,
            'successful_snapshots': 0,
            'total_max_release_usd': 0.0,
            'total_max_repay_usd': 0.0,
            'total_assets_usd': 0.0,
            'total_user_collateral_usd': 0.0,
            'pricing_errors_count': len(block_snapshot.pricing_errors),
            'fetch_errors_count': len(block_snapshot.fetch_errors),
            'evault_prices_block': block_snapshot.evault_prices_block
        }
    
    # Calculate totals
    total_max_release_usd = 0.0
    total_max_repay_usd = 0.0
    total_assets_usd = 0.0
    total_user_collateral_usd = 0.0
    
    for vault_snapshot in block_snapshot.vault_snapshots:
        usd_values = vault_snapshot['calculated_usd_values']
        total_max_release_usd += usd_values.get('max_release_usd', 0.0)
        total_max_repay_usd += usd_values.get('max_repay_usd', 0.0)
        total_assets_usd += usd_values.get('total_assets_usd', 0.0)
        total_user_collateral_usd += usd_values.get('user_collateral_usd', 0.0)
    
    return {
        'target_block': block_snapshot.target_block,
        'timestamp': block_snapshot.timestamp,
        'formatted_timestamp': datetime.fromtimestamp(block_snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S") if block_snapshot.timestamp else None,
        'total_vaults_discovered': block_snapshot.total_vaults,
        'successful_snapshots': len(block_snapshot.vault_snapshots),
        'total_max_release_usd': total_max_release_usd,
        'total_max_repay_usd': total_max_repay_usd,
        'total_assets_usd': total_assets_usd,
        'total_user_collateral_usd': total_user_collateral_usd,
        'pricing_errors_count': len(block_snapshot.pricing_errors),
        'fetch_errors_count': len(block_snapshot.fetch_errors),
        'evault_prices_block': block_snapshot.evault_prices_block
    }


def format_block_snapshot_for_table(block_snapshot: BlockSnapshot) -> List[Dict[str, Any]]:
    """
    Format block snapshot data for table display.
    
    Args:
        block_snapshot: BlockSnapshot object
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    table_rows = []
    
    for vault_snapshot in block_snapshot.vault_snapshots:
        snapshot = vault_snapshot['original_snapshot']
        usd_values = vault_snapshot['calculated_usd_values']
        vault_address = vault_snapshot['vault_address']
        
        # Format timestamp
        block_timestamp = datetime.fromtimestamp(
            int(snapshot.blockTimestamp)
        ).strftime("%Y-%m-%d %H:%M:%S")
        
        # Format Twyne LTV as percentage
        twyne_liq_ltv_decimal = float(snapshot.twyneLiqLtv) / 1e4 if snapshot.twyneLiqLtv != "0" else 0.0
        twyne_liq_ltv_percentage = twyne_liq_ltv_decimal * 100
        
        row = {
            "Chain ID": snapshot.chainId,
            "Vault Address": vault_address[:10] + "..." if len(vault_address) > 10 else vault_address,
            "Full Vault Address": vault_address,
            "Credit Vault": snapshot.creditVault[:10] + "..." if len(snapshot.creditVault) > 10 else snapshot.creditVault,
            "Debt Vault": snapshot.debtVault[:10] + "..." if len(snapshot.debtVault) > 10 else snapshot.debtVault,
            "Max Release (USD)": usd_values.get('max_release_usd', 0.0),
            "Max Repay (USD)": usd_values.get('max_repay_usd', 0.0),
            "Total Assets (USD)": usd_values.get('total_assets_usd', 0.0),
            "User Collateral (USD)": usd_values.get('user_collateral_usd', 0.0),
            "Twyne Liq LTV (%)": twyne_liq_ltv_percentage,
            "Can Liquidate": "Yes" if snapshot.canLiquidate else "No",
            "Externally Liquidated": "Yes" if snapshot.isExternallyLiquidated else "No",
            "Snapshot Block": int(snapshot.blockNumber),
            "Block Timestamp": block_timestamp,
            "Credit Price": vault_snapshot['credit_price'],
            "Debt Price": vault_snapshot['debt_price'],
            "Has Pricing Errors": vault_snapshot['has_pricing_errors'],
            "Actions": f"[More](/collateralVaults/{vault_address})"
        }
        
        table_rows.append(row)
    
    return table_rows
