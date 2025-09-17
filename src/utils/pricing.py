"""
Pricing utilities for the Risk Dashboard.
Handles token price calculations from EVault data and USD value conversions.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def calculate_evault_token_price(evault_metric: Any) -> Tuple[float, Optional[str]]:
    """
    Calculate token price from EVault metric data.
    
    Args:
        evault_metric: EVaultMetric object with totalAssets, totalAssetsUsd, and decimals
        
    Returns:
        Tuple of (price, error_message). Price is 0.0 if calculation fails.
        error_message is None if successful, otherwise contains error description.
    """
    try:
        # Extract values from metric
        total_assets_raw = evault_metric.totalAssets
        total_assets_usd_raw = evault_metric.totalAssetsUsd
        decimals = evault_metric.decimals
        vault_address = getattr(evault_metric, 'vaultAddress', 'unknown')
        
        # Validate inputs
        if total_assets_raw == "0" or not total_assets_raw:
            return 0.0, f"Total assets is zero for vault {vault_address}"
        
        if total_assets_usd_raw == "0" or not total_assets_usd_raw:
            return 0.0, f"Total assets USD is zero for vault {vault_address}"
        
        # Convert to float
        total_assets = float(total_assets_raw)
        total_assets_usd = float(total_assets_usd_raw)
        
        if total_assets <= 0:
            return 0.0, f"Invalid total assets value for vault {vault_address}"
        
        if total_assets_usd <= 0:
            return 0.0, f"Invalid total assets USD value for vault {vault_address}"
        
        price = total_assets_usd / total_assets
        
        logger.debug(f"Calculated price for vault {vault_address}: {price:.8f} USD per token")
        
        return price, None
        
    except (ValueError, InvalidOperation, ZeroDivisionError) as e:
        error_msg = f"Price calculation failed for vault {vault_address}: {str(e)}"
        logger.error(error_msg)
        return 0.0, error_msg
    except Exception as e:
        error_msg = f"Unexpected error calculating price for vault {vault_address}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return 0.0, error_msg


def create_evault_price_lookup(evault_metrics: List[Any]) -> Tuple[Dict[str, float], List[str]]:
    """
    Create a lookup dictionary of vault addresses to token prices.
    
    Args:
        evault_metrics: List of EVaultMetric objects
        
    Returns:
        Tuple of (price_lookup_dict, error_messages_list)
    """
    price_lookup = {}
    error_messages = []
    
    for metric in evault_metrics:
        vault_address = getattr(metric, 'vaultAddress', None)
        if not vault_address:
            error_messages.append("EVault metric missing vault address")
            continue
            
        price, error_msg = calculate_evault_token_price(metric)
        price_lookup[vault_address] = price
        
        if error_msg:
            error_messages.append(error_msg)
    
    logger.info(f"Created price lookup for {len(price_lookup)} vaults with {len(error_messages)} errors")
    
    return price_lookup, error_messages


def calculate_collateral_usd_values(
    snapshot: Any, 
    credit_vault_price: float, 
    debt_vault_price: float
) -> Tuple[Dict[str, float], List[str]]:
    """
    Calculate USD values for collateral vault snapshot using EVault prices.
    
    Args:
        snapshot: CollateralVaultSnapshot object
        credit_vault_price: Price per token for credit vault
        debt_vault_price: Price per token for debt vault
        
    Returns:
        Tuple of (usd_values_dict, error_messages_list)
    """
    usd_values = {}
    error_messages = []
    vault_address = getattr(snapshot, 'vaultAddress', 'unknown')
    
    try:
        # Extract raw native amounts
        max_release_raw = float(snapshot.maxRelease) if snapshot.maxRelease != "0" else 0.0
        max_repay_raw = float(snapshot.maxRepay) if snapshot.maxRepay != "0" else 0.0
        total_assets_raw = float(snapshot.totalAssetsDepositedOrReserved) if snapshot.totalAssetsDepositedOrReserved != "0" else 0.0
        user_collateral_raw = float(snapshot.userOwnedCollateral) if snapshot.userOwnedCollateral != "0" else 0.0
        
        # Note: Native amounts are already in the correct scale (wei format)
        # We need to scale them down by 1e18 to get actual token amounts
        scaling_factor = 1e18
        
        max_release_tokens = max_release_raw / scaling_factor
        max_repay_tokens = max_repay_raw / scaling_factor
        total_assets_tokens = total_assets_raw / scaling_factor
        user_collateral_tokens = user_collateral_raw / scaling_factor
        
        # Calculate USD values using prices
        usd_values['max_release_usd'] = max_release_tokens * credit_vault_price
        usd_values['max_repay_usd'] = max_repay_tokens * debt_vault_price
        usd_values['total_assets_usd'] = total_assets_tokens * credit_vault_price
        usd_values['user_collateral_usd'] = user_collateral_tokens * credit_vault_price
        
        # Add warnings for zero prices
        if credit_vault_price == 0.0:
            error_messages.append(f"Credit vault price is zero for snapshot {vault_address}")
        if debt_vault_price == 0.0:
            error_messages.append(f"Debt vault price is zero for snapshot {vault_address}")
            
        logger.debug(f"Calculated USD values for snapshot {vault_address}: "
                    f"max_release=${usd_values['max_release_usd']:.2f}, "
                    f"max_repay=${usd_values['max_repay_usd']:.2f}, "
                    f"total_assets=${usd_values['total_assets_usd']:.2f}, "
                    f"user_collateral=${usd_values['user_collateral_usd']:.2f}")
        
    except (ValueError, TypeError) as e:
        error_msg = f"Failed to calculate USD values for snapshot {vault_address}: {str(e)}"
        logger.error(error_msg)
        error_messages.append(error_msg)
        
        # Set all values to zero on error
        usd_values = {
            'max_release_usd': 0.0,
            'max_repay_usd': 0.0,
            'total_assets_usd': 0.0,
            'user_collateral_usd': 0.0
        }
    
    return usd_values, error_messages


def get_vault_price_with_warning(
    vault_address: str, 
    price_lookup: Dict[str, float], 
    vault_type: str = "vault"
) -> Tuple[float, Optional[str]]:
    """
    Get vault price from lookup with proper error handling.
    
    Args:
        vault_address: The vault address to look up
        price_lookup: Dictionary mapping vault addresses to prices
        vault_type: Type of vault (for error messages)
        
    Returns:
        Tuple of (price, warning_message). Price is 0.0 if vault not found.
    """
    if vault_address in price_lookup:
        price = price_lookup[vault_address]
        if price == 0.0:
            return price, f"Warning: {vault_type} {vault_address} has zero price"
        return price, None
    else:
        warning_msg = f"Warning: {vault_type} {vault_address} not found in EVault data"
        logger.warning(warning_msg)
        return 0.0, warning_msg
