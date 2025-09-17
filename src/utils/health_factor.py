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
