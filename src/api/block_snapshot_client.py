"""
API client extensions for block snapshot functionality.
Provides convenient methods to work with block snapshots.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .client import api_client
from ..utils.block_snapshot import create_block_snapshot, BlockSnapshot, format_block_snapshot_summary

logger = logging.getLogger(__name__)


class BlockSnapshotClient:
    """
    Client for block snapshot operations.
    Extends the main API client with block snapshot specific functionality.
    """
    
    def __init__(self):
        self.api_client = api_client
        logger.info("BlockSnapshotClient initialized")
    
    def create_snapshot_at_block(self, block_number: int) -> BlockSnapshot:
        """
        Create a comprehensive snapshot of all collateral vaults at a specific block.
        
        Args:
            block_number: Block number to create snapshot for
            
        Returns:
            BlockSnapshot object with comprehensive data
        """
        logger.info(f"Creating block snapshot for block {block_number}")
        
        try:
            snapshot = create_block_snapshot(block_number)
            
            # Log summary
            summary = format_block_snapshot_summary(snapshot)
            logger.info(f"Block snapshot created: {summary['successful_snapshots']}/{summary['total_vaults_discovered']} vaults, "
                       f"${summary['total_assets_usd']:,.2f} total assets")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to create block snapshot for block {block_number}: {str(e)}", exc_info=True)
            # Return empty snapshot with error information
            return BlockSnapshot(
                target_block=block_number,
                timestamp=None,
                vault_snapshots=[],
                total_vaults=0,
                pricing_errors=[],
                fetch_errors=[f"Unexpected error: {str(e)}"],
                evault_prices_block=None
            )
    
    def get_snapshot_summary(self, block_number: int) -> Dict[str, Any]:
        """
        Get a summary of the block snapshot without full vault details.
        
        Args:
            block_number: Block number to get summary for
            
        Returns:
            Dictionary with summary metrics
        """
        logger.info(f"Getting snapshot summary for block {block_number}")
        
        snapshot = self.create_snapshot_at_block(block_number)
        return format_block_snapshot_summary(snapshot)
    
    def get_vault_addresses_at_block(self, block_number: int) -> Dict[str, Any]:
        """
        Get just the vault addresses that existed at a specific block.
        
        Args:
            block_number: Block number to query
            
        Returns:
            Dictionary with vault addresses and metadata
        """
        from ..utils.block_snapshot import get_all_vault_addresses_up_to_block
        
        logger.info(f"Getting vault addresses for block {block_number}")
        
        try:
            vault_addresses, errors = get_all_vault_addresses_up_to_block(block_number)
            
            return {
                "target_block": block_number,
                "vault_addresses": list(vault_addresses),
                "total_vaults": len(vault_addresses),
                "errors": errors,
                "success": len(errors) == 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get vault addresses for block {block_number}: {str(e)}", exc_info=True)
            return {
                "target_block": block_number,
                "vault_addresses": [],
                "total_vaults": 0,
                "errors": [f"Unexpected error: {str(e)}"],
                "success": False
            }
    
    def get_evault_prices_at_block(self, block_number: int) -> Dict[str, Any]:
        """
        Get EVault prices at a specific block.
        
        Args:
            block_number: Block number to get prices for
            
        Returns:
            Dictionary with price data and metadata
        """
        from ..utils.block_snapshot import get_evault_prices_at_block
        
        logger.info(f"Getting EVault prices for block {block_number}")
        
        try:
            prices, actual_block, errors = get_evault_prices_at_block(block_number)
            
            return {
                "target_block": block_number,
                "actual_block": actual_block,
                "prices": prices,
                "total_vaults": len(prices),
                "errors": errors,
                "success": len(errors) == 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get EVault prices for block {block_number}: {str(e)}", exc_info=True)
            return {
                "target_block": block_number,
                "actual_block": None,
                "prices": {},
                "total_vaults": 0,
                "errors": [f"Unexpected error: {str(e)}"],
                "success": False
            }
    
    def compare_blocks(self, block1: int, block2: int) -> Dict[str, Any]:
        """
        Compare snapshots between two blocks.
        
        Args:
            block1: First block number
            block2: Second block number
            
        Returns:
            Dictionary with comparison data
        """
        logger.info(f"Comparing blocks {block1} and {block2}")
        
        try:
            snapshot1 = self.create_snapshot_at_block(block1)
            snapshot2 = self.create_snapshot_at_block(block2)
            
            summary1 = format_block_snapshot_summary(snapshot1)
            summary2 = format_block_snapshot_summary(snapshot2)
            
            # Calculate differences
            vault_diff = summary2['successful_snapshots'] - summary1['successful_snapshots']
            assets_diff = summary2['total_assets_usd'] - summary1['total_assets_usd']
            collateral_diff = summary2['total_user_collateral_usd'] - summary1['total_user_collateral_usd']
            credit_diff = summary2['total_max_release_usd'] - summary1['total_max_release_usd']
            debt_diff = summary2['total_max_repay_usd'] - summary1['total_max_repay_usd']
            
            return {
                "block1": block1,
                "block2": block2,
                "snapshot1": summary1,
                "snapshot2": summary2,
                "differences": {
                    "vault_count_change": vault_diff,
                    "total_assets_change_usd": assets_diff,
                    "total_collateral_change_usd": collateral_diff,
                    "total_credit_change_usd": credit_diff,
                    "total_debt_change_usd": debt_diff,
                    "percentage_assets_change": (assets_diff / summary1['total_assets_usd'] * 100) if summary1['total_assets_usd'] > 0 else 0,
                    "percentage_collateral_change": (collateral_diff / summary1['total_user_collateral_usd'] * 100) if summary1['total_user_collateral_usd'] > 0 else 0,
                    "percentage_credit_change": (credit_diff / summary1['total_max_release_usd'] * 100) if summary1['total_max_release_usd'] > 0 else 0,
                    "percentage_debt_change": (debt_diff / summary1['total_max_repay_usd'] * 100) if summary1['total_max_repay_usd'] > 0 else 0
                },
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to compare blocks {block1} and {block2}: {str(e)}", exc_info=True)
            return {
                "block1": block1,
                "block2": block2,
                "snapshot1": None,
                "snapshot2": None,
                "differences": {},
                "success": False,
                "error": str(e)
            }
    
    def get_block_range_summary(self, start_block: int, end_block: int, step: int = 1000) -> Dict[str, Any]:
        """
        Get summary data for a range of blocks.
        
        Args:
            start_block: Starting block number
            end_block: Ending block number
            step: Block step size
            
        Returns:
            Dictionary with range summary data
        """
        logger.info(f"Getting block range summary from {start_block} to {end_block} with step {step}")
        
        try:
            summaries = []
            current_block = start_block
            
            while current_block <= end_block:
                try:
                    summary = self.get_snapshot_summary(current_block)
                    summaries.append(summary)
                    logger.info(f"Processed block {current_block}")
                except Exception as e:
                    logger.error(f"Failed to process block {current_block}: {str(e)}")
                    summaries.append({
                        "target_block": current_block,
                        "error": str(e),
                        "successful_snapshots": 0,
                        "total_assets_usd": 0.0
                    })
                
                current_block += step
            
            return {
                "start_block": start_block,
                "end_block": end_block,
                "step": step,
                "summaries": summaries,
                "total_blocks_processed": len(summaries),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get block range summary: {str(e)}", exc_info=True)
            return {
                "start_block": start_block,
                "end_block": end_block,
                "step": step,
                "summaries": [],
                "total_blocks_processed": 0,
                "success": False,
                "error": str(e)
            }


# Create singleton instance
block_snapshot_client = BlockSnapshotClient()
