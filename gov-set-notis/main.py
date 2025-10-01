"""
Main Orchestration Script for Governance Notification System.

This script:
1. Collects all monitored vault addresses (Twyne + Euler)
2. Fetches new governance events for each vault
3. Sends notifications for new events
4. Updates state file
"""

import sys
import logging
import os
from pathlib import Path

# Add parent directory to path to import src modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add gov-set-notis directory to path for local imports
gov_notis_dir = str(Path(__file__).parent)
if gov_notis_dir not in sys.path:
    sys.path.insert(0, gov_notis_dir)

from logging_config import setup_logging
from vault_collector import get_all_monitored_vaults
from event_processor import process_all_vaults_events
from notifier import send_all_notifications

# Import DEFAULT_CHAIN_ID from local config (need to be careful about naming conflict)
import importlib.util
spec = importlib.util.spec_from_file_location("local_config", Path(__file__).parent / "config.py")
local_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local_config)
DEFAULT_CHAIN_ID = local_config.DEFAULT_CHAIN_ID

logger = logging.getLogger(__name__)


def main():
    """
    Main function to run the governance notification system.
    
    Flow:
    1. Get all monitored vault addresses (Twyne + Euler)
    2. Process all vaults and collect new events
    3. Send notifications for new events
    4. Update state file
    """
    try:
        logger.info("Starting Governance Notification System...")
        logger.info("")
        
        # Step 1: Collect vault addresses
        logger.info("=" * 80)
        logger.info("STEP 1: Collecting vault addresses to monitor")
        logger.info("=" * 80)
        
        vault_addresses = get_all_monitored_vaults(chain_id=DEFAULT_CHAIN_ID)
        
        if not vault_addresses:
            logger.warning("No vault addresses found to monitor. Exiting.")
            return
        
        logger.info(f"Total vaults to monitor: {len(vault_addresses)}")
        logger.info("")
        
        # Step 2: Fetch new events
        logger.info("=" * 80)
        logger.info("STEP 2: Fetching new governance events")
        logger.info("=" * 80)
        
        new_events = process_all_vaults_events(vault_addresses, DEFAULT_CHAIN_ID)
        
        total_new_events = sum(len(events) for events in new_events.values())
        logger.info(f"Found {total_new_events} new events across {len(new_events)} vault/event-type combinations")
        logger.info("")
        
        # Step 3: Send notifications
        logger.info("=" * 80)
        logger.info("STEP 3: Sending notifications")
        logger.info("=" * 80)
        
        if new_events:
            send_all_notifications(new_events, DEFAULT_CHAIN_ID)
        else:
            logger.info("No new events to notify. State file is up to date.")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("Governance Notification System completed successfully")
        logger.info("=" * 80)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error("=" * 80)
        logger.error("FATAL ERROR in Governance Notification System")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Setup logging first
    setup_logging()
    
    # Run main function
    main()

