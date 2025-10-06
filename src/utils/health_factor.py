"""
Health Factor calculation utilities for collateral vault snapshots.
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def calculate_health_factor(enhanced_snapshot: Dict[str, Any]) -> float:
    """
    Calculate Health Factor for a collateral vault snapshot.
    
    Formula: Health Factor = (user_owned_collateral_usd * liqLTV) / debt_usd
    If debt_usd = 0, return 2 (capped)
    Health factor is capped at maximum value of 2
    
    Args:
        enhanced_snapshot: Enhanced snapshot dictionary with calculated USD values
        
    Returns:
        Health factor as float (capped at 2.0)
    """
    try:
        snapshot = enhanced_snapshot['original_snapshot']
        usd_values = enhanced_snapshot['calculated_usd_values']
        
        # Get user owned collateral in USD
        user_collateral_usd = usd_values.get('user_collateral_usd', 0.0)
        
        # Get debt USD (using max_repay_usd as debt)
        debt_usd = usd_values.get('max_repay_usd', 0.0)
        
        # Get liqLTV from snapshot (scaled by 1e4, convert to decimal)
        twyne_liq_ltv_raw = float(snapshot.twyneLiqLtv) if snapshot.twyneLiqLtv != "0" else 0.0
        liq_ltv_decimal = twyne_liq_ltv_raw / 1e4
        
        # If debt is zero, return 2 (capped high health factor)
        if debt_usd == 0.0:
            return 2.0
        
        # Calculate health factor: (collateral_usd * liqLTV) / debt_usd
        health_factor = (user_collateral_usd * liq_ltv_decimal) / debt_usd
        
        # Cap health factor at maximum value of 2
        return min(health_factor, 2.0)
        
    except (ValueError, TypeError, KeyError) as e:
        vault_address = enhanced_snapshot.get('vault_address', 'unknown')
        logger.error(f"Failed to calculate health factor for snapshot {vault_address}: {str(e)}")
        return 0.0


def calculate_health_factors_for_snapshots(
    enhanced_snapshots: List[Dict[str, Any]]
) -> List[Tuple[float, float, float, str]]:
    """
    Calculate health factors for multiple snapshots and prepare data for charting.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        
    Returns:
        List of tuples (health_factor, debt_usd, credit_usd, vault_address) for chart data
    """
    chart_data = []
    
    for enhanced_snapshot in enhanced_snapshots:
        try:
            health_factor = calculate_health_factor(enhanced_snapshot)
            debt_usd = enhanced_snapshot['calculated_usd_values'].get('max_repay_usd', 0.0)
            credit_usd = enhanced_snapshot['calculated_usd_values'].get('user_collateral_usd', 0.0)
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            
            # Only include points with positive debt for meaningful chart
            # (points with 0 debt will all have health factor = 10)
            if debt_usd > 0:
                chart_data.append((health_factor, debt_usd, credit_usd, vault_address))
                
        except Exception as e:
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            logger.error(f"Failed to process snapshot {vault_address} for chart: {str(e)}")
            continue
    
    logger.info(f"Prepared {len(chart_data)} data points for health factor chart")
    return chart_data


def get_health_factor_summary_stats(
    enhanced_snapshots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate summary statistics for health factors.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        
    Returns:
        Dictionary with health factor statistics
    """
    health_factors = []
    positions_with_debt = 0
    positions_without_debt = 0
    
    for enhanced_snapshot in enhanced_snapshots:
        try:
            health_factor = calculate_health_factor(enhanced_snapshot)
            debt_usd = enhanced_snapshot['calculated_usd_values'].get('max_repay_usd', 0.0)
            
            health_factors.append(health_factor)
            
            if debt_usd > 0:
                positions_with_debt += 1
            else:
                positions_without_debt += 1
                
        except Exception as e:
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            logger.error(f"Failed to calculate health factor for summary stats {vault_address}: {str(e)}")
            continue
    
    if not health_factors:
        return {
            'total_positions': 0,
            'positions_with_debt': 0,
            'positions_without_debt': 0,
            'avg_health_factor': 0.0,
            'min_health_factor': 0.0,
            'max_health_factor': 0.0
        }
    
    return {
        'total_positions': len(health_factors),
        'positions_with_debt': positions_with_debt,
        'positions_without_debt': positions_without_debt,
        'avg_health_factor': sum(health_factors) / len(health_factors),
        'min_health_factor': min(health_factors),
        'max_health_factor': max(health_factors)
    }


def calculate_ltv_position_data_for_heatmap(
    enhanced_snapshots: List[Dict[str, Any]]
) -> List[Tuple[float, float, str]]:
    """
    Calculate LTV and Position Size for heatmap visualization.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        
    Returns:
        List of tuples (ltv, position_size, vault_address) for heatmap data
    """
    heatmap_data = []
    
    for enhanced_snapshot in enhanced_snapshots:
        try:
            usd_values = enhanced_snapshot['calculated_usd_values']
            
            # Get collateral and debt USD values
            collateral_usd = usd_values.get('user_collateral_usd', 0.0)
            debt_usd = usd_values.get('max_repay_usd', 0.0)
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            
            # Skip positions with zero collateral (cannot calculate LTV)
            if collateral_usd == 0.0:
                continue
            
            # Calculate LTV = DebtUSD / CollateralUSD
            ltv = debt_usd / collateral_usd
            
            # Calculate Position Size = CollateralUSD - DebtUSD
            position_size = collateral_usd - debt_usd
            
            # Only include positions with positive position size
            if position_size > 0:
                heatmap_data.append((ltv, position_size, vault_address))
                
        except Exception as e:
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            logger.error(f"Failed to process snapshot {vault_address} for heatmap: {str(e)}")
            continue
    
    logger.info(f"Prepared {len(heatmap_data)} data points for LTV vs Position Size heatmap")
    return heatmap_data


def prepare_sankey_data_for_credit_flow(
    enhanced_snapshots: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Prepare Sankey diagram data showing 2-tier credit flow:
    Credit Vaults → Debt Vaults.
    
    Args:
        enhanced_snapshots: List of enhanced snapshot dictionaries
        
    Returns:
        Dictionary with 'labels', 'source', 'target', 'value', and 'colors' for Sankey diagram
    """
    from collections import defaultdict
    
    # Collect flows: Credit Vault -> Debt Vault (using max_release_usd)
    credit_to_debt = defaultdict(float)
    
    for enhanced_snapshot in enhanced_snapshots:
        try:
            credit_vault = enhanced_snapshot.get('credit_vault', 'Unknown')
            debt_vault = enhanced_snapshot.get('debt_vault', 'Unknown')
            max_release_usd = enhanced_snapshot['calculated_usd_values'].get('max_release_usd', 0.0)
            
            # Sum max_release_usd for each (credit_vault, debt_vault) pair
            if max_release_usd > 0:
                credit_to_debt[(credit_vault, debt_vault)] += max_release_usd
                
        except Exception as e:
            vault_address = enhanced_snapshot.get('vault_address', 'unknown')
            logger.error(f"Failed to process snapshot {vault_address} for Sankey: {str(e)}")
            continue
    
    if not credit_to_debt:
        logger.warning("No flows found for Sankey diagram")
        return {
            'labels': [],
            'source': [],
            'target': [],
            'value': [],
            'colors': []
        }
    
    # Extract unique credit vaults and debt vaults
    credit_vaults = sorted(list(set(key[0] for key in credit_to_debt.keys())))
    debt_vaults = sorted(list(set(key[1] for key in credit_to_debt.keys())))
    
    # Create node labels (credit vaults first, then debt vaults)
    labels = credit_vaults + debt_vaults
    
    # Create mapping from vault address to node index
    vault_to_index = {vault: i for i, vault in enumerate(labels)}
    
    # Prepare source, target, and value arrays for links
    source_indices = []
    target_indices = []
    values = []
    
    # Add flows from credit vaults to debt vaults
    for (credit_vault, debt_vault), value in credit_to_debt.items():
        source_idx = vault_to_index[credit_vault]
        target_idx = vault_to_index[debt_vault]
        source_indices.append(source_idx)
        target_indices.append(target_idx)
        values.append(value)
    
    # Create colors for 2 tiers:
    # - Credit vaults: blue (source/left)
    # - Debt vaults: orange (target/right)
    num_credit = len(credit_vaults)
    num_debt = len(debt_vaults)
    
    colors = (
        ['rgba(52, 152, 219, 0.8)'] * num_credit +   # Blue for credit vaults
        ['rgba(230, 126, 34, 0.8)'] * num_debt       # Orange for debt vaults
    )
    
    logger.info(
        f"Prepared 2-tier Sankey data: {num_credit} credit vaults, "
        f"{num_debt} debt vaults, {len(source_indices)} flows"
    )
    
    return {
        'labels': labels,
        'source': source_indices,
        'target': target_indices,
        'value': values,
        'colors': colors,
        'num_credit': num_credit,
        'num_debt': num_debt
    }
