"""
USD calculation utilities for collateral vault snapshots.
Implements new pricing mechanism using EVault data instead of pre-calculated USD values.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional

from .evault_data import get_vault_prices_for_snapshot, evault_cache
from .pricing import calculate_collateral_usd_values

logger = logging.getLogger(__name__)


async def calculate_snapshot_usd_values(snapshot: Any) -> Tuple[Dict[str, float], List[str]]:
    """
    Calculate USD values for a collateral vault snapshot using EVault pricing.
    
    Args:
        snapshot: CollateralVaultSnapshot object
        
    Returns:
        Tuple of (usd_values_dict, warning_messages_list)
    """
    warning_messages = []
    vault_address = getattr(snapshot, 'vaultAddress', 'unknown')
    
    try:
        # Get vault addresses
        credit_vault = getattr(snapshot, 'creditVault', '')
        debt_vault = getattr(snapshot, 'debtVault', '')
        
        if not credit_vault or not debt_vault:
            error_msg = f"Missing vault addresses for snapshot {vault_address}"
            logger.error(error_msg)
            warning_messages.append(error_msg)
            return _get_zero_usd_values(), warning_messages
        
        # Get prices for both vaults
        credit_price, debt_price, price_errors = await get_vault_prices_for_snapshot(
            credit_vault, debt_vault
        )
        warning_messages.extend(price_errors)
        
        # Calculate USD values using the pricing utility
        usd_values, calc_errors = calculate_collateral_usd_values(
            snapshot, credit_price, debt_price
        )
        warning_messages.extend(calc_errors)
        
        return usd_values, warning_messages
        
    except Exception as e:
        error_msg = f"Failed to calculate USD values for snapshot {vault_address}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        warning_messages.append(error_msg)
        return _get_zero_usd_values(), warning_messages


async def calculate_multiple_snapshots_usd_values(
    snapshots: List[Any]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Calculate USD values for multiple collateral vault snapshots efficiently.
    
    Args:
        snapshots: List of CollateralVaultSnapshot objects
        
    Returns:
        Tuple of (enhanced_snapshots_list, warning_messages_list)
    """
    enhanced_snapshots = []
    all_warnings = []
    
    if not snapshots:
        return enhanced_snapshots, all_warnings
    
    logger.info(f"Calculating USD values for {len(snapshots)} snapshots")
    
    for snapshot in snapshots:
        # Calculate USD values for this snapshot
        usd_values, warnings = await calculate_snapshot_usd_values(snapshot)
        all_warnings.extend(warnings)
        
        # Create enhanced snapshot data
        enhanced_snapshot = {
            'original_snapshot': snapshot,
            'calculated_usd_values': usd_values,
            'vault_address': getattr(snapshot, 'vaultAddress', 'unknown'),
            'credit_vault': getattr(snapshot, 'creditVault', ''),
            'debt_vault': getattr(snapshot, 'debtVault', ''),
            'has_pricing_errors': len(warnings) > 0
        }
        
        enhanced_snapshots.append(enhanced_snapshot)
    
    logger.info(f"Completed USD calculations with {len(all_warnings)} warnings")
    
    return enhanced_snapshots, all_warnings


def get_summary_metrics_from_snapshots(
    enhanced_snapshots: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate summary metrics from enhanced snapshots with USD values.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        
    Returns:
        Dictionary with summary metrics
    """
    total_max_release_usd = 0.0
    total_max_repay_usd = 0.0
    total_assets_usd = 0.0
    total_user_collateral_usd = 0.0
    
    for enhanced_snapshot in enhanced_snapshots:
        usd_values = enhanced_snapshot['calculated_usd_values']
        
        total_max_release_usd += usd_values.get('max_release_usd', 0.0)
        total_max_repay_usd += usd_values.get('max_repay_usd', 0.0)
        total_assets_usd += usd_values.get('total_assets_usd', 0.0)
        total_user_collateral_usd += usd_values.get('user_collateral_usd', 0.0)
    
    return {
        'total_max_release_usd': total_max_release_usd,
        'total_max_repay_usd': total_max_repay_usd,
        'total_assets_usd': total_assets_usd,
        'total_user_collateral_usd': total_user_collateral_usd,
        'total_snapshots': len(enhanced_snapshots)
    }


def format_enhanced_snapshot_for_table(enhanced_snapshot: Dict[str, Any], symbol_mapping: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Format an enhanced snapshot for table display.
    
    Args:
        enhanced_snapshot: Enhanced snapshot dictionary with calculated USD values
        symbol_mapping: Dict mapping vault addresses to symbols (optional)
        
    Returns:
        Dictionary formatted for DataTable display
    """
    if symbol_mapping is None:
        symbol_mapping = {}
    
    snapshot = enhanced_snapshot['original_snapshot']
    usd_values = enhanced_snapshot['calculated_usd_values']
    
    # Get basic snapshot data
    vault_address = enhanced_snapshot['vault_address']
    credit_vault_address = snapshot.creditVault
    debt_vault_address = snapshot.debtVault
    
    # Format timestamp
    from datetime import datetime
    block_timestamp = datetime.fromtimestamp(
        int(snapshot.blockTimestamp)
    ).strftime("%Y-%m-%d %H:%M:%S")
    
    # Format Twyne LTV as percentage
    twyne_liq_ltv_decimal = float(snapshot.twyneLiqLtv) / 1e4 if snapshot.twyneLiqLtv != "0" else 0.0
    twyne_liq_ltv_percentage = twyne_liq_ltv_decimal * 100
    
    # Get symbols or use full addresses (for copying)
    credit_vault_display = symbol_mapping.get(credit_vault_address.lower(), credit_vault_address)
    debt_vault_display = symbol_mapping.get(debt_vault_address.lower(), debt_vault_address)
    
    # Create table row with calculated USD values
    row = {
        "Chain ID": snapshot.chainId,
        "Vault Address": vault_address,  # Store full address for copying
        "Credit Vault": credit_vault_display,
        "Debt Vault": debt_vault_display,
        "Max Release (USD)": usd_values.get('max_release_usd', 0.0),
        "Max Repay (USD)": usd_values.get('max_repay_usd', 0.0),
        "Total Assets (USD)": usd_values.get('total_assets_usd', 0.0),
        "User Collateral (USD)": usd_values.get('user_collateral_usd', 0.0),
        "Twyne Liq LTV (%)": twyne_liq_ltv_percentage,
        "Can Liquidate": "Yes" if snapshot.canLiquidate else "No",
        "Externally Liquidated": "Yes" if snapshot.isExternallyLiquidated else "No",
        "Block Number": int(snapshot.blockNumber),
        "Block Timestamp": block_timestamp,
        "Actions": f"[More](/collateralVaults/{vault_address})",
        "Has Pricing Errors": enhanced_snapshot['has_pricing_errors']  # For styling/warnings
    }
    
    return row


def format_enhanced_snapshots_for_table(
    enhanced_snapshots: List[Dict[str, Any]],
    symbol_mapping: Dict[str, str] = None
) -> List[Dict[str, Any]]:
    """
    Format multiple enhanced snapshots for table display.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        symbol_mapping: Dict mapping vault addresses to symbols (optional)
        
    Returns:
        List of dictionaries formatted for DataTable
    """
    return [
        format_enhanced_snapshot_for_table(enhanced_snapshot, symbol_mapping) 
        for enhanced_snapshot in enhanced_snapshots
    ]


def _get_zero_usd_values() -> Dict[str, float]:
    """
    Get dictionary with all USD values set to zero.
    
    Returns:
        Dictionary with zero USD values
    """
    return {
        'max_release_usd': 0.0,
        'max_repay_usd': 0.0,
        'total_assets_usd': 0.0,
        'user_collateral_usd': 0.0
    }


def get_pricing_warnings_summary(warning_messages: List[str]) -> Optional[str]:
    """
    Create a summary of pricing warnings for display.
    
    Args:
        warning_messages: List of warning messages
        
    Returns:
        Summary string or None if no warnings
    """
    if not warning_messages:
        return None
    
    # Count different types of warnings
    missing_vaults = [msg for msg in warning_messages if "not found in EVault data" in msg]
    zero_prices = [msg for msg in warning_messages if "zero price" in msg]
    other_errors = [msg for msg in warning_messages if msg not in missing_vaults and msg not in zero_prices]
    
    summary_parts = []
    
    if missing_vaults:
        summary_parts.append(f"{len(missing_vaults)} missing vault(s)")
    
    if zero_prices:
        summary_parts.append(f"{len(zero_prices)} vault(s) with zero price")
    
    if other_errors:
        summary_parts.append(f"{len(other_errors)} other pricing error(s)")
    
    if summary_parts:
        return f"Pricing warnings: {', '.join(summary_parts)}"
    
    return None
