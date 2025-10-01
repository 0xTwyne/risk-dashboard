"""
Configuration for Governance Notification System.
Centralizes all configuration including contract addresses, RPCs, API settings, and notification channels.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Contract addresses and RPC URLs per chain
CONTRACTS = {
    1: {  # Ethereum Mainnet
        "VAULT_MANAGER": "0x0acd3A3c8Ab6a5F7b5A594C88DFa28999dA858aC",
        "RPC_URL": os.getenv("RPC_URL_1", "https://eth.drpc.org")
    },
    # Add more chains as needed
    # 8453: {  # Base
    #     "VAULT_MANAGER": "PLACEHOLDER_VAULT_MANAGER_ADDRESS",
    #     "RPC_URL": os.getenv("BASE_RPC_URL", "PLACEHOLDER_RPC_URL")
    # }
}

# Notification channels (Apprise URL format)
# See https://github.com/caronc/apprise for Slack URL format
NOTIFICATION_CHANNELS = {
    "slack_param_updates": os.getenv("SLACK_WEBHOOK_URL", ""),  # Format: https://hooks.slack.com/services/...
}

# Gov-set event types to monitor
GOV_SET_TYPES = [
    "gov-set-caps",
    "gov-set-config-flags",
    "gov-set-fee-receiver",
    "gov-set-governor-admin",
    "gov-set-hook-config",
    "gov-set-interest-fee",
    "gov-set-interest-rate-model",
    "gov-set-liquidation-cool-off-time",
    "gov-set-ltv",
    "gov-set-max-liquidation-discount"
]

# API settings
FETCH_LIMIT_PER_EVENT_TYPE = 10  # Fetch latest N events per vault/event-type
DEFAULT_CHAIN_ID = 1

# State file path
STATE_FILE_PATH = "data/gov-updates.json"

# Logging settings
LOG_FILE_PATH = "gov-set-notis/gov_set_notis.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 5


