# Governance Notification System

A standalone notification system that monitors parameter updates for EVaults and sends Slack notifications when new governance events are detected.

## Overview

This system:
1. Fetches all Twyne EVaults (symbols starting with "ee") from the API
2. For each Twyne vault, queries the blockchain (via Ape framework) to get associated Euler vaults
3. Monitors all governance parameter change events for these vaults
4. Sends Slack notifications when new events are detected
5. Maintains state to avoid duplicate notifications

## Architecture

```
gov-set-notis/
├── config.py              # Configuration (contracts, RPCs, channels)
├── vault_collector.py     # Vault address collection (API + Ape)
├── state_manager.py       # State file management
├── event_processor.py     # Event fetching and filtering
├── notifier.py            # Apprise notification sending
├── main.py                # Main orchestration script
├── logging_config.py      # Logging setup
└── README.md              # This file
```

## Configuration

### 1. Contract Addresses and RPC URLs

Edit `gov-set-notis/config.py` and update the `CONTRACTS` dictionary:

```python
CONTRACTS = {
    1: {  # Ethereum Mainnet
        "VAULT_MANAGER": "0xYourVaultManagerAddress",
        "RPC_URL": "https://eth.drpc.org"
    }
}
```

### 2. Notification Channels

Configure Slack notification URLs in `gov-set-notis/config.py`:

```python
NOTIFICATION_CHANNELS = {
    "slack_param_updates": "slack://tokenA/tokenB/tokenC"
}
```

For Slack URL format, see: https://github.com/caronc/apprise/wiki/Notify_slack

### 3. Environment Variables

The system uses the existing API configuration from the main dashboard. Ensure your `.env` file has:

```
API_BASE_URL=https://your-api-url
API_KEY=your-api-key
```

## Installation

1. Install dependencies:
```bash
uv sync 
```

This will install:
- `eth-ape==0.8.0` - Blockchain interaction framework
- `apprise==1.9.0` - Notification framework
- All existing dashboard dependencies

2. Configure the system (see Configuration section above)

## Usage

### Running Manually

To run the notification system once:

```bash
cd /path/to/risk-dashboard
uv run gov-set-notis/main.py
```

The script will:
1. Collect all monitored vault addresses
2. Check for new governance events
3. Send notifications for new events
4. Update the state file

### Logs

Logs are written to:
- `gov-set-notis/gov_set_notis.log` - Main application log (with rotation)
- Console output (when running manually)

### State File

The system maintains state in `data/gov-updates.json`:

```json
{
  "1": {
    "0xvaultaddress": {
      "gov-set-caps": {
        "block": 12345678,
        "txHash": "0xabc...def"
      }
    }
  }
}
```

This tracks the last processed event for each vault/event-type combination to avoid duplicate notifications.

## Monitored Event Types

The system monitors these governance event types:

1. `gov-set-caps` - Supply/borrow cap changes
2. `gov-set-config-flags` - Configuration flag changes
3. `gov-set-fee-receiver` - Fee receiver changes
4. `gov-set-governor-admin` - Governor admin changes
5. `gov-set-hook-config` - Hook configuration changes
6. `gov-set-interest-fee` - Interest fee changes
7. `gov-set-interest-rate-model` - Interest rate model changes
8. `gov-set-liquidation-cool-off-time` - Liquidation cooloff changes
9. `gov-set-ltv` - LTV parameter changes
10. `gov-set-max-liquidation-discount` - Max liquidation discount changes

## Notification Format

Notifications are sent to Slack with the following format:

```
🔔 New parameter update found

Event Type: gov-set-caps
Vault: 0x1234...5678
Chain ID: 1
Block: 12,345,678
Block Timestamp: 1234567890
Tx Hash: 0xabc...def

Details:
  newSupplyCap: 1000000
  newBorrowCap: 500000
```

## Error Handling

The system is designed to be resilient:

- **Vault Collection**: If fetching Euler vaults for one Twyne vault fails, it skips that vault and continues
- **Event Fetching**: If fetching events for one vault/event-type fails, it continues with others
- **Notifications**: If sending a notification fails, the event is still marked as processed to avoid retrying failed sends
- **State Management**: State file is backed up before updates and writes are atomic

## Troubleshooting

### No notifications being sent

1. Check if Slack URL is configured (not PLACEHOLDER)
2. Verify the Slack URL format is correct
3. Check `gov_set_notis.log` for errors
4. Run manually to see console output

### Contract calls failing

1. Ensure `VAULT_MANAGER` address is set correctly
2. Verify RPC URL is valid and accessible
3. Check that you have sufficient RPC credits
4. Verify Ape framework is installed correctly

### State file issues

1. Check that `data/` directory exists
2. Verify write permissions
3. Look for `gov-updates.json.backup` if corrupted

### Cron job not running

1. Check cron is enabled: `sudo launchctl list | grep cron` (macOS)
2. Verify crontab entry: `crontab -l`
3. Check cron logs: `grep CRON /var/log/syslog` (Linux) or system logs (macOS)
4. Ensure paths in cron command are absolute

## Development

### Testing Manually

To test without sending notifications:

1. Configure a test vault address
2. Set notification channel to PLACEHOLDER
3. Run: `python gov-set-notis/main.py`
4. Check logs for "would be sent" messages

### Adding New Chains

To add support for a new chain:

1. Add entry to `CONTRACTS` in `config.py`:
```python
CONTRACTS = {
    1: {...},  # Ethereum
    8453: {    # Base
        "VAULT_MANAGER": "0x...",
        "RPC_URL": "https://..."
    }
}
```

2. Update `DEFAULT_CHAIN_ID` if needed
3. Ape framework will automatically handle ABI fetching for the new chain

## Support

For issues or questions:
1. Check the logs: `gov-set-notis/gov_set_notis.log`
2. Review the state file: `data/gov-updates.json`
3. Run manually with verbose logging to diagnose issues

## License

Same as the main risk-dashboard project.


