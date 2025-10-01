"""
Notification System using Apprise.
Sends Slack notifications for governance parameter updates.
"""

import logging
from typing import Dict, Any, List
import apprise

# Import from local config using importlib to avoid naming conflicts
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)

NOTIFICATION_CHANNELS = local_config.NOTIFICATION_CHANNELS
from state_manager import load_state, save_state, update_processed_event

logger = logging.getLogger(__name__)


def format_event_message(
    vault_address: str,
    event_type: str,
    event_data: Dict[str, Any]
) -> str:
    """
    Format event data into a notification message.
    
    Args:
        vault_address: Vault address
        event_type: Event type (e.g., "gov-set-caps")
        event_data: Event data from API
        
    Returns:
        Formatted string for notification
    """
    try:
        # Extract common fields
        block_number = event_data.get("blockNumber", "Unknown")
        block_timestamp = event_data.get("blockTimestamp", "Unknown")
        tx_hash = event_data.get("txnHash", "Unknown")
        chain_id = event_data.get("chainId", "Unknown")
        
        # Build message header
        message_lines = [
            "🔔 New parameter update found",
            "",
            f"Event Type: {event_type}",
            f"Vault: {vault_address}",
            f"Chain ID: {chain_id}",
            f"Block: {block_number}",
            f"Block Timestamp: {block_timestamp}",
            f"Tx Hash: {tx_hash}",
            "",
            "Details:"
        ]
        
        # Add event-specific details
        details = []
        for key, value in event_data.items():
            # Skip common fields already displayed
            if key in ["blockNumber", "blockTimestamp", "txnHash", "chainId", "vaultAddress"]:
                continue
            
            # Format the detail
            details.append(f"  {key}: {value}")
        
        message_lines.extend(details)
        
        return "\n".join(message_lines)
        
    except Exception as e:
        logger.error(f"Error formatting event message: {e}", exc_info=True)
        return f"Error formatting message for {event_type} event on vault {vault_address}"


def send_notification(
    message: str,
    channel: str = "slack_param_updates"
) -> bool:
    """
    Send notification via Apprise.
    
    Args:
        message: Formatted message to send
        channel: Channel key from config (default: "slack_param_updates")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get channel URL from config
        if channel not in NOTIFICATION_CHANNELS:
            logger.error(f"Unknown notification channel: {channel}")
            return False
        
        channel_url = NOTIFICATION_CHANNELS[channel]
        
        # Check if channel is configured
        if not channel_url or channel_url.startswith("PLACEHOLDER"):
            logger.warning(f"Notification channel '{channel}' not configured, skipping notification")
            logger.info(f"Message that would be sent:\n{message}")
            return True  # Return True to not block state updates
        
        # Create Apprise instance
        apobj = apprise.Apprise()
        
        # Add notification service
        if not apobj.add(channel_url):
            logger.error(f"Failed to add notification service for channel '{channel}'")
            return False
        
        # Send notification
        logger.info(f"Sending notification to channel '{channel}'...")
        result = apobj.notify(
            body=message,
            title="Governance Parameter Update"
        )
        
        if result:
            logger.info(f"Successfully sent notification to '{channel}'")
        else:
            logger.error(f"Failed to send notification to '{channel}'")
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
        return False


def send_all_notifications(
    new_events: Dict[str, List[Dict[str, Any]]],
    chain_id: int
) -> None:
    """
    Send notifications for all new events and update state.
    
    For each event:
    1. Format message
    2. Send notification
    3. Update state (regardless of notification success to avoid re-sending)
    
    Args:
        new_events: Dict mapping "vault:event_type" -> list of events
        chain_id: Chain ID
    """
    try:
        # Load current state
        state = load_state()
        
        total_events = sum(len(events) for events in new_events.values())
        logger.info(f"Sending notifications for {total_events} events across {len(new_events)} vault/event-type combinations")
        
        notifications_sent = 0
        notifications_failed = 0
        
        # Process each vault/event-type combination
        for key, events in new_events.items():
            vault_address, event_type = key.split(":", 1)
            
            logger.info(f"Processing {len(events)} events for {vault_address}/{event_type}")
            
            # Sort events by block number (oldest first) to process in order
            sorted_events = sorted(events, key=lambda e: int(e.get("blockNumber", 0)))
            
            for event in sorted_events:
                # Format message
                message = format_event_message(vault_address, event_type, event)
                
                # Send notification
                success = send_notification(message)
                
                if success:
                    notifications_sent += 1
                else:
                    notifications_failed += 1
                    logger.warning(f"Failed to send notification for event at block {event.get('blockNumber')}")
                
                # Update state regardless of notification success
                # This prevents re-sending notifications for events we've already tried
                block_number = event.get("blockNumber")
                tx_hash = event.get("txnHash")
                
                if block_number and tx_hash:
                    # Convert block number to int if it's a string
                    if isinstance(block_number, str):
                        block_number = int(block_number)
                    
                    update_processed_event(
                        state,
                        chain_id,
                        vault_address,
                        event_type,
                        block_number,
                        tx_hash
                    )
                else:
                    logger.error(f"Event missing blockNumber or txnHash, cannot update state: {event}")
        
        # Save updated state
        save_state(state)
        
        logger.info(f"Notification summary: {notifications_sent} sent, {notifications_failed} failed")
        
    except Exception as e:
        logger.error(f"Error sending notifications: {e}", exc_info=True)
        raise


