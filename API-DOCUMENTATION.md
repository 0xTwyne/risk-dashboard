# Twyne Dune Indexer API Documentation

## Overview

The Twyne Dune Indexer API provides access to indexed blockchain data for the Twyne protocol, including:
- Collateral vault operations and snapshots
- EVault (Euler Vault) metrics and liquidations
- Chainlink oracle price feeds
- Protocol-wide statistics
- Governance parameter changes

This API is built on the Sim IDX framework using Hono and Drizzle ORM, deployed on Cloudflare Workers.

## Base Information

**Base URL**: `http://localhost:8787` (local development) or deployed endpoint

**Authentication**: All endpoints require authentication via Sim IDX middleware

**Content Type**: All responses are `application/json`

**Timestamp Format**: ISO 8601 strings or Unix timestamps (seconds)

## Recent Changes

### ⚠️ v1.2 Breaking Changes (2025-10-19)

**All numeric values are now returned as proper JSON numbers (not strings):**

- **Token amounts**: Numbers instead of strings (e.g., `1000.5` instead of `"1000.5"`)
- **USD values**: Numbers instead of strings (e.g., `2500.50` instead of `"2500.50"`)
- **LTV values**: Numbers instead of strings (e.g., `0.75` instead of `"0.75"`)
- **Interest rates**: Numbers instead of strings (e.g., `0.05` instead of `"0.05"`)
- **Block numbers**: Numbers instead of strings (e.g., `20123456` instead of `"20123456"`)
- **Timestamps**: Numbers instead of strings (e.g., `1705234567` instead of `"1705234567"`)
- **Chain IDs**: Numbers instead of strings (e.g., `1` instead of `"1"`)

**All numeric values are scaled to human-readable format:**

- Token amounts automatically scaled by their respective decimals (no raw wei values)
- USD values scaled by 1e18
- LTV values scaled by 1e4
- Interest rates scaled by 1e18

**Other changes:**

- **Removed parameter**: `includeRawAmounts` no longer available
- **New price metadata fields** added to snapshots endpoint

See [Changelog](#version-information) for complete details.

### Endpoint Consolidation

The API has been refactored to consolidate redundant endpoints:

**Removed Endpoints**:
- ❌ `/api/collateralVaults/:address/latest-snapshot` - Replaced by `/api/collateralVaults/snapshots` with `vaultAddresses` parameter

**Enhanced Endpoints**:
- ✅ `/api/collateralVaults/snapshots` - Now accepts `vaultAddresses` parameter for filtering specific vaults
- ✅ `/api/evaults/latest` - Now accepts optional `blockNumber` and `timestamp` parameters for historical queries

**Migration Guide**:
```
# Old approach (removed)
GET /api/collateralVaults/0xABC.../latest-snapshot

# New approach
GET /api/collateralVaults/snapshots?vaultAddresses=0xABC...
```

```
# Old: Only latest metrics
GET /api/evaults/latest

# New: Supports historical queries
GET /api/evaults/latest?blockNumber=20123456
GET /api/evaults/latest?timestamp=1705234567
```

## Common Patterns

### Chain ID Filtering

Most endpoints accept an optional `chainIds` query parameter to filter results by blockchain:

- **Parameter**: `chainIds` (optional)
- **Format**: Comma-separated chain IDs (e.g., `1,8453`)
- **Default**: `[1, 8453]` (Ethereum Mainnet and Base)
- **Example**: `?chainIds=1` or `?chainIds=1,8453`

### Pagination

Most list endpoints support pagination:

- **Parameters**:
  - `limit` (optional): Number of results to return (max: 100, default: 100)
  - `offset` (optional): Number of results to skip (default: 0)
- **Validation**:
  - `limit` must be >= 1 and <= 100
  - `offset` must be >= 0
- **Response includes**:
  - `count`: Number of results in current response
  - `totalCount` or `totalUniqueVaults`: Total number of available results
  - `limit`: Applied limit
  - `offset`: Applied offset

### Address Validation

All Ethereum addresses:
- Accept addresses with or without `0x` prefix
- Must be exactly 40 hexadecimal characters (20 bytes)
- Returns 400 error if invalid format

### Block and Timestamp Parameters

Historical data endpoints support:
- **blockNumber**: Fetch data at or before a specific block
- **timestamp**: Fetch data at or before a specific Unix timestamp
- **Priority**: If both provided, `blockNumber` takes precedence
- **Validation**: Both must be non-negative integers

---

## API Endpoints

### Health Check

#### GET `/api/health`

Check API health and database connectivity.

**Query Parameters**:
- `chainIds` (optional): Chain IDs to check (default: `1,8453`)

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "totalVaults": 1234,
  "totalMetricsRecords": 56789,
  "chainIds": ["1", "8453"]
}
```

**Error Response** (500):
```json
{
  "status": "unhealthy",
  "error": "Error message",
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

---

## Collateral Vaults

### GET `/api/collateralVaults`

Get all created collateral vaults with pagination and filtering.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `endBlock` (optional): Return only vaults created at or before this block number

**Response**:
```json
{
  "vaults": [
    {
      "chainId": "1",
      "blockNumber": "20123456",
      "blockTimestamp": "1705234567",
      "txnHash": "0x...",
      "vaultAddress": "0x...",
      "intermediateVault": "0x...",
      "targetVault": "0x...",
      "underlyingCollateralVault": "0x...",
      "logIndex": "123"
    }
  ],
  "count": 10,
  "totalCount": 1234,
  "limit": 100,
  "offset": 0,
  "blockNumber": "20123456" // Only included if endBlock was specified
}
```

---

### GET `/api/collateralVaults/snapshots`

Get position snapshots for collateral vaults at a specific block or latest block, with USD-denominated values.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `blockNumber` (optional): Target block number (defaults to latest available block)
- `vaultAddresses` (optional): Comma-separated vault addresses to filter (e.g., `0xabc...,0xdef...`)
- `canLiquidate` (optional): Filter by liquidation eligibility (`true` or `false`)
- `isExternallyLiquidated` (optional): Filter by external liquidation status (`true` or `false`)
- `includePricedAmounts` (optional): Include USD-denominated amounts (default: `true`)

**Important Notes**:
- Only returns "post" state snapshots to avoid double-counting
- All token amounts are **automatically scaled by their respective decimals** (human-readable values, not raw wei)
- USD values calculated using closest EVault metrics at target block
- Price metadata fields show which block's price data was used for scaling
- When no `blockNumber` specified, uses latest block from `vault_metrics` table

**Response**:
```json
{
  "blockNumber": 20123456,
  "snapshotBlock": 20123450,
  "priceBlock": 20123448,
  "snapshots": [
    {
      "vaultAddress": "0x...",
      "underlyingCollateralVault": "0x...",
      "creditVault": "0x...",
      "debtVault": "0x...",
      "canLiquidate": false,
      "isExternallyLiquidated": false,
      "twyneLiqLtv": 0.75,
      "blockNumber": 20123450,
      "blockTimestamp": 1705234567,
      "logIndex": 45,
      "underlyingCollateralVaultPriceBlock": 20123448,
      "underlyingCollateralVaultPriceTimestamp": 1705234500,
      "creditVaultPriceBlock": 20123448,
      "creditVaultPriceTimestamp": 1705234500,
      "debtVaultPriceBlock": 20123448,
      "debtVaultPriceTimestamp": 1705234500,
      "userOwnedCollateral": 1000.5,
      "maxRelease": 500.25,
      "maxRepay": 300.15,
      "totalAssetsDepositedOrReserved": 1200.6,
      "userOwnedCollateralUsd": 2500.50,
      "maxReleaseUsd": 1250.25,
      "maxRepayUsd": 750.15,
      "totalAssetsDepositedOrReservedUsd": 3000.60
    }
  ],
  "vaultPrices": {
    "0x...": {
      "pricePerToken": 2.5005,
      "symbol": "eeUSDC",
      "decimals": 6,
      "blockNumber": 20123448,
      "blockTimestamp": 1705234500
    }
  },
  "aggregates": {
    "totalUserOwnedCollateralUsd": 125000.50,
    "totalMaxReleaseUsd": 62500.25,
    "totalMaxRepayUsd": 37500.15,
    "totalAssetsDepositedOrReservedUsd": 150000.60,
    "uniqueVaults": 10
  },
  "totalUniqueVaults": 1234,
  "limit": 100,
  "offset": 0,
  "filters": {
    "canLiquidate": "true",
    "isExternallyLiquidated": null,
    "vaultAddresses": "0xabc...,0xdef..."
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**Field Descriptions**:
- `blockNumber`: Requested target block
- `snapshotBlock`: Actual max block number in returned snapshots
- `priceBlock`: Max block number used for pricing data
- `blockNumber`, `blockTimestamp`, `logIndex`: Numbers representing the snapshot's block, timestamp, and log index
- `underlyingCollateralVaultPriceBlock`, `underlyingCollateralVaultPriceTimestamp`: Numbers representing when price data was captured for underlying collateral vault
- `creditVaultPriceBlock`, `creditVaultPriceTimestamp`: Numbers representing when price data was captured for credit vault
- `debtVaultPriceBlock`, `debtVaultPriceTimestamp`: Numbers representing when price data was captured for debt vault
- `userOwnedCollateral`: Number - Collateral owned by user (scaled by vault decimals, human-readable)
- `maxRelease`: Number - Maximum credit that can be released (scaled by vault decimals, human-readable)
- `maxRepay`: Number - Maximum debt that can be repaid (scaled by vault decimals, human-readable)
- `totalAssetsDepositedOrReserved`: Number - Total assets in underlying vault (scaled by vault decimals, human-readable)
- `twyneLiqLtv`: Number - Twyne liquidation LTV threshold (e.g., 0.75 = 75%)

---

### GET `/api/collateralVaults/:address/history`

Get complete position snapshot history for a specific vault address with scaled amounts.

**Path Parameters**:
- `address`: Vault address (with or without 0x prefix)

**Query Parameters**:
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)

**Important Notes**:
- All token amounts are **automatically scaled by their respective decimals** (human-readable values, not raw wei)
- USD values calculated using vault metrics price data

**Response**:
```json
{
  "vaultAddress": "0x...",
  "snapshots": [
    {
      "vaultAddress": "0x...",
      "underlyingCollateralVault": "0x...",
      "creditVault": "0x...",
      "debtVault": "0x...",
      "userOwnedCollateral": 1000.5,
      "maxRelease": 500.25,
      "maxRepay": 300.15,
      "totalAssetsDepositedOrReserved": 1200.6,
      "userOwnedCollateralUsd": 2500.50,
      "maxReleaseUsd": 1250.25,
      "maxRepayUsd": 750.15,
      "totalAssetsDepositedOrReservedUsd": 3000.60,
      "canLiquidate": false,
      "isExternallyLiquidated": false,
      "twyneLiqLtv": 0.75,
      "state": "post",
      "txType": "deposit",
      "blockNumber": 20123456,
      "blockTimestamp": 1705234567,
      "logIndex": 45
    }
  ],
  "count": 10,
  "totalCount": 456,
  "limit": 100,
  "offset": 0,
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**Error Response** (404):
```json
{
  "error": "No position snapshots found for this vault address"
}
```

---

### GET `/api/collateralVaults/external-liquidations`

Get external liquidation events for collateral vaults with pre/post state data.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)

**Important Notes**:
- All token amounts are **automatically scaled by their respective decimals** (human-readable values, not raw wei)
- USD values are human-readable (scaled by 1e18)
- LTV values are scaled (e.g., "0.75" = 75%)

**Response**:
```json
{
  "externalLiquidations": [
    {
      "vaultAddress": "0x...",
      "blockNumber": 20123456,
      "blockTimestamp": 1705234567,
      "txnHash": "0x...",
      "liquidator": "0x...",
      "violator": "0x...",
      "collateral": "0x...",
      "repayAssets": 1000.5,
      "yieldBalance": 500.25,
      "repayAssetsUsd": 2500.50,
      "yieldBalanceUsd": 1250.25,
      "collateralAmount": 1200.6,
      "debtAmount": 900.45,
      "collateralAmountUsd": 3000.60,
      "debtAmountUsd": 2250.45,
      "eulerLiqLtv": 0.80,
      "twyneLiqLtv": 0.75,
      "twyneMaxLiqLtv": 0.85,
      "twyneSafetyBuffer": 0.10,
      "preCollateralAmount": 1500.75,
      "preCollateralAmountUsd": 3750.75,
      "preDebtAmount": 1100.55,
      "preDebtAmountUsd": 2750.55,
      "preCreditReserved": 200.10,
      "preCreditReservedUsd": 500.10,
      "creditReserved": 150.08,
      "creditReservedUsd": 375.08,
      "creditVault": "0x...",
      "debtVault": "0x...",
      "underlyingCollateralVault": "0x..."
    }
  ],
  "count": 5,
  "totalCount": 123,
  "limit": 100,
  "offset": 0,
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

---

### GET `/api/collateralVaults/internal-liquidations`

Get internal liquidation events (factory-triggered liquidations).

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `startBlock` (optional): Filter by start block number
- `endBlock` (optional): Filter by end block number
- `startTimestamp` (optional): Filter by start timestamp
- `endTimestamp` (optional): Filter by end timestamp

**Response**:
```json
{
  "internalLiquidations": [
    {
      "chainId": "1",
      "blockNumber": "20123456",
      "blockTimestamp": "1705234567",
      "txnHash": "0x...",
      "vaultAddress": "0x...",
      "isLiquidated": true,
      "logIndex": "78"
    }
  ],
  "count": 3,
  "totalCount": 45,
  "limit": 100,
  "offset": 0,
  "filters": {
    "chainIds": ["1", "8453"],
    "startBlock": "20000000",
    "endBlock": "20500000",
    "startTimestamp": null,
    "endTimestamp": null
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

---

## EVaults (Euler Vaults)

**Note**: All EVault endpoint responses use `snake_case` field names (e.g., `vault_address`, `total_assets_usd`).

### GET `/api/evault/:address/metrics`

Get historical vault metrics for a specific EVault address.

**Path Parameters**:
- `address`: EVault address (with or without 0x prefix)

**Query Parameters**:
- `limit` (optional): Results per page (max: 1000, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `startBlock` (optional): Filter by start block number
- `endBlock` (optional): Filter by end block number
- `startTime` (optional): Filter by start timestamp
- `endTime` (optional): Filter by end timestamp

**Important Notes**:
- All token amounts are **automatically scaled by their respective decimals** (human-readable values, not raw wei)
- USD values are human-readable (scaled by 1e18)
- Interest rates and accumulators are scaled (divided by 1e18)

**Response**:
```json
{
  "vaultAddress": "0x87b8081a3ace680f35125f469526ac10f5418ca7",
  "metrics": [
    {
      "chain_id": 1,
      "vault_address": "0x87b8081a3ace680f35125f469526ac10f5418ca7",
      "total_assets": 10000.0,
      "total_assets_usd": 25000.50,
      "total_borrows": 5000.0,
      "total_borrows_usd": 12500.25,
      "asset": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
      "cash": 5000.0,
      "interest_accumulator": 1.05,
      "interest_rate": 0.05,
      "symbol": "eeUSDC",
      "name": "EVK Vault eeUSDC",
      "decimals": 6,
      "block_number": 20123456,
      "block_timestamp": 1705234567
    }
  ],
  "count": 10,
  "totalCount": 456,
  "limit": 100,
  "offset": 0
}
```

---

### GET `/api/evaults/latest`

Get latest vault metrics for all tracked EVaults, optionally at a specific block or timestamp.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `blockNumber` (optional): Get metrics at or before this block number
- `timestamp` (optional): Get metrics at or before this Unix timestamp

**Behavior**:
- If `blockNumber` provided: Returns latest metrics per vault <= blockNumber
- If `timestamp` provided: Returns latest metrics per vault <= timestamp
- If both provided: `blockNumber` takes precedence
- If neither provided: Returns absolute latest metrics per vault

**Important Notes**:
- All token amounts are **automatically scaled by their respective decimals** (human-readable values, not raw wei)
- USD values are human-readable (scaled by 1e18)
- Interest rates are scaled (divided by 1e18)

**Response**:
```json
{
  "latestMetrics": [
    {
      "chain_id": 1,
      "vault_address": "0x87b8081a3ace680f35125f469526ac10f5418ca7",
      "total_assets": 10000.0,
      "total_assets_usd": 25000.50,
      "total_borrows": 5000.0,
      "total_borrows_usd": 12500.25,
      "asset": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
      "interest_rate": 0.05,
      "symbol": "eeWETH",
      "name": "EVK Vault eeWETH",
      "decimals": 18,
      "block_number": 20123456,
      "block_timestamp": 1705234567
    }
  ],
  "count": 15,
  "totalUniqueVaults": 234,
  "limit": 100,
  "offset": 0,
  "blockNumber": 20123456,
  "responseTimestamp": "2025-01-15T10:30:00.000Z"
}
```

**Field Descriptions**:
- `vault_address`: String - EVault contract address
- `asset`: String - Underlying asset token address
- `chain_id`: Number - Chain ID
- `total_assets`: Number - Total assets in the vault (scaled by token decimals, human-readable)
- `total_assets_usd`: Number - USD value of total assets (human-readable, scaled by 1e18)
- `total_borrows`: Number - Total borrowed amount (scaled by token decimals, human-readable)
- `total_borrows_usd`: Number - USD value of total borrows (human-readable, scaled by 1e18)
- `cash`: Number - Available cash in vault (scaled by token decimals)
- `interest_accumulator`: Number - Interest accumulator (scaled, e.g., 1.05)
- `interest_rate`: Number - Current interest rate (scaled, annual rate, e.g., 0.05 = 5%)
- `symbol`: String - Vault symbol (e.g., "eeWETH")
- `name`: String - Vault name
- `decimals`: Number - Token decimals
- `block_number`: Number - Block number of the metric
- `block_timestamp`: Number - Unix timestamp of the block

---

## Protocol Statistics

### GET `/api/protocolStats`

Get aggregated protocol-wide statistics including total collateral, debt, and EVault metrics.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)

**Response**:
```json
{
  "totalCollateralUsd": 12500000.50,
  "totalDebtUsd": 6250000.25,
  "totalEvaultAssetsUsd": 25000000.75,
  "totalEvaultBorrowsUsd": 12500000.38,
  "uniqueVaults": 1234,
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**Field Descriptions**:
- `totalCollateralUsd`: Sum of `userOwnedCollateral` (USD) from latest collateral vault snapshots
- `totalDebtUsd`: Sum of `maxRepay` (USD) from latest collateral vault snapshots
- `totalEvaultAssetsUsd`: Sum of assets in all EVaults with symbols starting with "ee"
- `totalEvaultBorrowsUsd`: Sum of borrows in all EVaults with symbols starting with "ee"
- `uniqueVaults`: Number of unique collateral vaults

**Calculation Notes**:
- Uses latest position snapshots (filtered by `state = 'post'`)
- Prices calculated from latest EVault metrics
- All amounts scaled from wei to human-readable (divided by 1e18)

---

## Chainlink Oracles

### GET `/api/chainlink/latest-answers`

Get the 5 most recent Chainlink price feed updates.

**Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)

**Response**:
```json
{
  "latestAnswers": [
    {
      "chainId": "1",
      "blockNumber": "20123456",
      "blockTimestamp": "1705234567",
      "aggregatorAddress": "0x...",
      "current": "250050000000",
      "roundId": "12345678901234567890",
      "updatedAt": "1705234567"
    }
  ],
  "count": 5,
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**Field Descriptions**:
- `current`: Current price from oracle (8 decimals for most feeds)
- `roundId`: Chainlink round ID
- `updatedAt`: When the price was last updated (Unix timestamp)

---

## Governance

All governance endpoints follow the same pattern:

**Common Query Parameters**:
- `chainIds` (optional): Filter by chain IDs (default: `1,8453`)
- `limit` (optional): Results per page (max: 100, default: 100)
- `offset` (optional): Number to skip (default: 0)
- `vaultAddress` (optional): Filter by specific vault address

**Common Response Structure**:
```json
{
  "events": [...],
  "count": 10,
  "totalCount": 123,
  "limit": 100,
  "offset": 0,
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

### GET `/api/gov-set-caps`

Get vault cap configuration changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `supplyCap`: New supply cap value
- `borrowCap`: New borrow cap value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-config-flags`

Get vault configuration flag changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `configFlags`: New configuration flags value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-fee-receiver`

Get fee receiver address changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `feeReceiver`: New fee receiver address
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-governor-admin`

Get governor admin address changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `governorAdmin`: New governor admin address
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-hook-config`

Get hook configuration changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `hookConfig`: New hook configuration value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-interest-fee`

Get interest fee configuration changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `interestFee`: New interest fee value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-interest-rate-model`

Get interest rate model changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `interestRateModel`: New interest rate model address
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-liquidation-cool-off-time`

Get liquidation cool-off time changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `liquidationCoolOffTime`: New cool-off time value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-ltv`

Get Loan-to-Value (LTV) ratio changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `borrowLTV`: New borrow LTV value
- `liquidationLTV`: New liquidation LTV value
- `initialLiquidationLTV`: New initial liquidation LTV value
- `targetTimestamp`: Target timestamp for the change
- `rampDuration`: Duration of the ramp period
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

### GET `/api/gov-set-max-liquidation-discount`

Get maximum liquidation discount changes.

**Event Fields**:
- `vaultAddress`: Address of the vault
- `maxLiquidationDiscount`: New max liquidation discount value
- `blockNumber`, `blockTimestamp`, `txnHash`, `chainId`

---

## Error Responses

All endpoints follow consistent error response patterns:

### Validation Errors (400)

**Invalid Pagination**:
```json
{
  "error": "Invalid limit parameter. Must be between 1 and 100."
}
```

**Invalid Address**:
```json
{
  "error": "Invalid address format. Expected 40 hex characters."
}
```

**Invalid Block Number**:
```json
{
  "error": "Invalid blockNumber parameter"
}
```

**Invalid Timestamp**:
```json
{
  "error": "Invalid timestamp parameter"
}
```

### Not Found Errors (404)

```json
{
  "error": "No position snapshots found for this vault address"
}
```

### Server Errors (500)

```json
{
  "error": "Database operation failed",
  "details": "Detailed error message"
}
```

---

## Data Types and Formats

### Numeric Values

**Token Amounts** (Numbers):
- **All endpoints return scaled values** - amounts are automatically divided by their respective token decimals
- Returned as numbers (floats)
- Examples:
  - WETH (18 decimals): `1000.5` = 1000.5 WETH
  - USDC (6 decimals): `1000.5` = 1000.5 USDC
  - WBTC (8 decimals): `1.5` = 1.5 WBTC
- **No raw wei values are returned** - all amounts are human-readable

**USD Values** (Numbers):
- All endpoints return human-readable USD values (scaled by 1e18)
- Returned as numbers (floats)
- Example: `2500.50` = $2,500.50

**Interest Rates and Accumulators** (Numbers):
- Scaled by 1e18
- Returned as numbers (floats)
- Example: `0.05` = 5% annual rate

**LTV Values** (Numbers):
- Scaled by 1e4 (basis points)
- Returned as numbers (floats)
- Example: `0.75` = 0.75 or 75%

**Block Numbers and Timestamps** (Numbers):
- All block numbers and timestamps returned as numbers (integers)
- Example: `20123456` (block number), `1705234567` (Unix timestamp)

**Chain IDs** (Numbers):
- Returned as numbers (integers)
- Example: `1` (Ethereum Mainnet), `8453` (Base)

### Addresses

- All addresses returned as lowercase hex strings with `0x` prefix
- Example: `"0x1234567890123456789012345678901234567890"`

### Timestamps

- Block timestamps: Unix timestamps as strings
- Response timestamps: ISO 8601 format
- Example: `"1705234567"` or `"2025-01-15T10:30:00.000Z"`

### Transaction Hashes

- 32-byte hex strings with `0x` prefix
- Example: `"0xabcdef..."`

---

## Best Practices

### Pagination Strategy

For large datasets:
1. Start with `offset=0` and reasonable `limit` (e.g., 100)
2. Check `totalCount` or `totalUniqueVaults` in response
3. Increment `offset` by `limit` for subsequent requests
4. Stop when `offset >= totalCount`

### Historical Queries

When querying historical data:
1. Use `blockNumber` for deterministic, reproducible queries
2. Use `timestamp` for time-based analysis when exact block doesn't matter
3. Remember: `blockNumber` takes precedence if both provided

### Filtering Vaults

For collateral vault snapshots:
- Use `vaultAddresses` to query specific vaults efficiently
- Combine with `canLiquidate=true` to find liquidation opportunities
- Use `isExternallyLiquidated=false` to filter out already liquidated positions

### Chain-Specific Queries

- Always specify `chainIds` when querying single chain
- Omit `chainIds` to query all supported chains (1 and 8453)
- Check `chainId` field in response to identify data source

---

## Common Use Cases

### Find Liquidation Opportunities

```
GET /api/collateralVaults/snapshots?canLiquidate=true&isExternallyLiquidated=false
```

### Get Vault State at Specific Block

```
GET /api/collateralVaults/snapshots?blockNumber=20123456&vaultAddresses=0x...
```

### Monitor Protocol Health

```
GET /api/protocolStats
```

### Track Specific Vault Over Time

```
GET /api/collateralVaults/0x.../history?limit=100&offset=0
```

### Get Latest EVault Metrics

```
GET /api/evaults/latest?chainIds=1
```

### Get EVault Metrics at Specific Block

```
GET /api/evaults/latest?blockNumber=20123456&limit=10
```

### Get EVault Metrics at Specific Timestamp

```
GET /api/evaults/latest?timestamp=1705234567&chainIds=1
```

### Historical EVault Analysis (Single Vault)

```
GET /api/evault/0x.../metrics?startBlock=20000000&endBlock=20500000
```

### Monitor Governance Changes

```
GET /api/gov-set-ltv?vaultAddress=0x...
```

---

## Database Schema Notes

### Position Snapshots

- Each transaction creates **two** snapshots: "pre" and "post"
- **Always filter by `state = 'post'`** when aggregating to avoid double-counting
- `txType` indicates transaction type: `deposit`, `withdraw`, `borrow`, `repay`, `teleport`, `liquidate`
- `logIndex` provides ordering within a block

### EVault Metrics

- Updated per-block for tracked vaults
- Symbols starting with "ee" indicate Euler vaults
- Price per token calculated as: `totalAssetsUsd / totalAssets`

### Vault Addresses

- `vaultAddress`: The collateral vault address
- `intermediateVault`: Credit/intermediate vault (where borrowed assets go)
- `targetVault`: Debt vault (where debt is tracked)
- `underlyingCollateralVault`: EVault holding the collateral asset

---

## Rate Limits and Performance

- No explicit rate limits currently enforced
- Maximum `limit` capped at 100 for most endpoints (1000 for vault metrics)
- Use pagination for large datasets
- Consider filtering by `chainIds` for better performance
- Complex queries (snapshots with USD calculations) may take longer

---

## Support and Issues

For API issues or questions:
- Check this documentation first
- Verify query parameters match validation rules
- Ensure addresses are properly formatted
- Check block numbers are within indexed range

---

## Version Information

**Last Updated**: 2025-10-19

**API Version**: 1.2

**Changelog**:
- **v1.2** (2025-10-19):
  - **BREAKING**: All numeric values now returned as numbers (not strings):
    - Token amounts: Numbers (floats) instead of strings
    - USD values: Numbers (floats) instead of strings
    - LTV values: Numbers (floats, e.g., `0.75`) instead of strings
    - Interest rates: Numbers (floats, e.g., `0.05`) instead of strings
    - Block numbers: Numbers (integers) instead of strings
    - Timestamps: Numbers (integers) instead of strings
    - Chain IDs: Numbers (integers) instead of strings
  - **BREAKING**: All token amounts now automatically scaled by their respective decimals (human-readable values)
  - **BREAKING**: Removed `includeRawAmounts` parameter - raw wei values are no longer available
  - **BREAKING**: All USD values now human-readable (scaled by 1e18)
  - Added price metadata fields to `/api/collateralVaults/snapshots`:
    - `underlyingCollateralVaultPriceBlock` / `underlyingCollateralVaultPriceTimestamp`
    - `creditVaultPriceBlock` / `creditVaultPriceTimestamp`
    - `debtVaultPriceBlock` / `debtVaultPriceTimestamp`
  - Added `blockTimestamp` field to vault prices in responses
  - Updated `/api/collateralVaults/:address/history` to return scaled amounts and USD values
  - Updated `/api/collateralVaults/external-liquidations` to return scaled amounts
  - Updated all EVault endpoints to return scaled amounts
- **v1.1** (2025-10-18):
  - Added `vaultAddresses` parameter to `/api/collateralVaults/snapshots`
  - Added `blockNumber` and `timestamp` parameters to `/api/evaults/latest`
  - Removed `/api/collateralVaults/:address/latest-snapshot` (use snapshots endpoint with vaultAddresses instead)
  - Fixed Buffer serialization for address fields in EVault endpoints
  - All EVault endpoint responses now use snake_case field names
- **v1.0** (2025-01-15):
  - Initial API release

**Supported Chains**:
- Chain ID 1: Ethereum Mainnet
- Chain ID 8453: Base

**Framework**: Sim IDX (Dune Analytics)

**Database**: PostgreSQL via Drizzle ORM

**Runtime**: Cloudflare Workers
