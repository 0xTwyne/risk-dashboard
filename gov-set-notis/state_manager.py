"""
State Management for Governance Notifications.
Manages the gov-updates.json state file for tracking processed events.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path

# Import from local config using importlib to avoid naming conflicts
import importlib.util

spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)

STATE_FILE_PATH = local_config.STATE_FILE_PATH

logger = logging.getLogger(__name__)


def load_state() -> Dict[str, Any]:
    """
    Load state from gov-updates.json.
    
    Returns:
        State dictionary with structure:
        {
            "chain_id": {
                "vault_address": {
                    "event_type": {
                        "block": block_number,
                        "txHash": "0x..."
                    }
                }
            }
        }
    """
    try:
        state_path = Path(STATE_FILE_PATH)
        
        if not state_path.exists():
            logger.info(f"State file not found at {STATE_FILE_PATH}, creating new empty state")
            # Create directory if it doesn't exist
            state_path.parent.mkdir(parents=True, exist_ok=True)
            # Initialize with empty state
            empty_state = {}
            save_state(empty_state)
            return empty_state
        
        with open(state_path, 'r') as f:
            state = json.load(f)
            logger.info(f"Loaded state from {STATE_FILE_PATH}")
            return state
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse state file {STATE_FILE_PATH}: {e}")
        logger.info("Returning empty state")
        return {}
    except Exception as e:
        logger.error(f"Error loading state file: {e}", exc_info=True)
        return {}


def save_state(state: Dict[str, Any]) -> None:
    """
    Save state to gov-updates.json.
    
    Args:
        state: State dictionary to save
    """
    try:
        state_path = Path(STATE_FILE_PATH)
        
        # Create directory if it doesn't exist
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if file exists
        if state_path.exists():
            backup_path = state_path.with_suffix('.json.backup')
            state_path.rename(backup_path)
            logger.debug(f"Created backup at {backup_path}")
        
        # Write state atomically
        temp_path = state_path.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Atomic rename
        temp_path.rename(state_path)
        logger.info(f"Saved state to {STATE_FILE_PATH}")
        
    except Exception as e:
        logger.error(f"Failed to save state: {e}", exc_info=True)
        raise


def get_last_processed_event(
    state: Dict,
    chain_id: int,
    vault_address: str,
    event_type: str
) -> Optional[Dict[str, Any]]:
    """
    Get the last processed event for a vault/event-type combination.
    
    Args:
        state: State dictionary
        chain_id: Chain ID
        vault_address: Vault address (case-insensitive)
        event_type: Event type (e.g., "gov-set-caps")
        
    Returns:
        Dict with 'block' and 'txHash' or None if not found
    """
    try:
        chain_id_str = str(chain_id)
        vault_address_lower = vault_address.lower()
        
        if chain_id_str not in state:
            logger.debug(f"Chain ID {chain_id} not in state")
            return None
        
        if vault_address_lower not in state[chain_id_str]:
            logger.debug(f"Vault {vault_address} not in state for chain {chain_id}")
            return None
        
        if event_type not in state[chain_id_str][vault_address_lower]:
            logger.debug(f"Event type {event_type} not in state for vault {vault_address}")
            return None
        
        event_data = state[chain_id_str][vault_address_lower][event_type]
        logger.debug(f"Found last processed event for {vault_address}/{event_type}: block {event_data.get('block')}")
        return event_data
        
    except Exception as e:
        logger.error(f"Error getting last processed event: {e}", exc_info=True)
        return None


def update_processed_event(
    state: Dict,
    chain_id: int,
    vault_address: str,
    event_type: str,
    block_number: int,
    tx_hash: str
) -> None:
    """
    Update state with newly processed event.
    
    Args:
        state: State dictionary (modified in-place)
        chain_id: Chain ID
        vault_address: Vault address
        event_type: Event type (e.g., "gov-set-caps")
        block_number: Block number of the event
        tx_hash: Transaction hash of the event
    """
    try:
        chain_id_str = str(chain_id)
        vault_address_lower = vault_address.lower()
        
        # Create nested structure if doesn't exist
        if chain_id_str not in state:
            state[chain_id_str] = {}
        
        if vault_address_lower not in state[chain_id_str]:
            state[chain_id_str][vault_address_lower] = {}
        
        # Update the specific event entry
        state[chain_id_str][vault_address_lower][event_type] = {
            "block": block_number,
            "txHash": tx_hash
        }
        
        logger.info(f"Updated state for {vault_address}/{event_type}: block {block_number}, tx {tx_hash}")
        
    except Exception as e:
        logger.error(f"Error updating processed event: {e}", exc_info=True)
        raise


