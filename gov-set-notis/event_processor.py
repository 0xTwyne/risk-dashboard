"""
Event Processing for Governance Notifications.
Fetches gov-set events and identifies new ones that haven't been processed.
"""

import logging
from typing import Dict, List, Any, Optional, Set

from src.api import api_client
# Import from local config using importlib to avoid naming conflicts
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)

GOV_SET_TYPES = local_config.GOV_SET_TYPES
FETCH_LIMIT_PER_EVENT_TYPE = local_config.FETCH_LIMIT_PER_EVENT_TYPE
DEFAULT_CHAIN_ID = local_config.DEFAULT_CHAIN_ID
from state_manager import load_state, get_last_processed_event

logger = logging.getLogger(__name__)


def fetch_new_events_for_vault(
    vault_address: str,
    event_type: str,
    chain_id: int,
    last_processed_block: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch new events for a vault/event-type that haven't been processed.
    
    Steps:
    1. Call API to get latest N events for this vault/event-type
    2. Filter events with blockNumber > last_processed_block
    3. Return list of new events (newest first)
    
    Args:
        vault_address: Vault to query
        event_type: Gov-set event type (e.g., "gov-set-caps")
        chain_id: Chain ID
        last_processed_block: Block number of last processed event
        
    Returns:
        List of new event dicts from API
    """
    try:
        logger.debug(f"Fetching {event_type} events for vault {vault_address}")
        
        # Call API to get latest events
        response = api_client.get_gov_set_events(
            event_type=event_type,
            vault_address=vault_address,
            chain_ids=[chain_id],
            limit=FETCH_LIMIT_PER_EVENT_TYPE,
            offset=0
        )
        
        if isinstance(response, dict) and "error" in response:
            logger.warning(f"API error fetching {event_type} for {vault_address}: {response['error']}")
            return []
        
        # Extract events from response
        events = response.get("events", [])
        
        if not events:
            logger.debug(f"No {event_type} events found for vault {vault_address}")
            return []
        
        # Filter for new events (block number > last processed)
        new_events = []
        
        for event in events:
            # Extract block number - handle both string and int
            block_number = event.get("blockNumber")
            if isinstance(block_number, str):
                block_number = int(block_number)
            
            # Check if this event is new
            if last_processed_block is None or block_number > last_processed_block:
                new_events.append(event)
                logger.debug(f"  New event found at block {block_number}")
            else:
                logger.debug(f"  Skipping already processed event at block {block_number}")
        
        if new_events:
            logger.info(f"Found {len(new_events)} new {event_type} events for vault {vault_address}")
        
        return new_events
        
    except Exception as e:
        logger.error(f"Error fetching events for {vault_address}/{event_type}: {e}", exc_info=True)
        return []


def process_all_vaults_events(
    vault_addresses: Set[str],
    chain_id: int
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process all vaults and collect new events.
    
    Returns:
        Dict mapping (vault_address:event_type) -> list of new events
        Format: {
            "0xVault1:gov-set-caps": [event1, event2],
            "0xVault2:gov-set-ltv": [event1]
        }
    
    Args:
        vault_addresses: Set of vault addresses to monitor
        chain_id: Chain ID
        
    Returns:
        Dictionary of new events keyed by "vault:event_type"
    """
    new_events_map = {}
    
    try:
        logger.info(f"Processing events for {len(vault_addresses)} vaults on chain {chain_id}")
        
        # Load current state
        state = load_state()
        
        total_new_events = 0
        
        # Process each vault
        for vault_address in vault_addresses:
            logger.info(f"Processing vault {vault_address}")
            
            # Process each event type
            for event_type in GOV_SET_TYPES:
                logger.debug(f"  Checking {event_type}...")
                
                # Get last processed event from state
                last_event = get_last_processed_event(
                    state,
                    chain_id,
                    vault_address,
                    event_type
                )
                
                last_processed_block = last_event.get("block") if last_event else None
                
                if last_processed_block:
                    logger.debug(f"    Last processed block: {last_processed_block}")
                else:
                    logger.debug(f"    No previous events processed")
                
                # Fetch new events from API
                new_events = fetch_new_events_for_vault(
                    vault_address,
                    event_type,
                    chain_id,
                    last_processed_block
                )
                
                # Store new events if any
                if new_events:
                    key = f"{vault_address}:{event_type}"
                    new_events_map[key] = new_events
                    total_new_events += len(new_events)
                    logger.info(f"    Found {len(new_events)} new events for {event_type}")
        
        logger.info(f"Processing complete. Found {total_new_events} total new events across {len(new_events_map)} vault/event-type combinations")
        return new_events_map
        
    except Exception as e:
        logger.error(f"Error processing vaults events: {e}", exc_info=True)
        return new_events_map


