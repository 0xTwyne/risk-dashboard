# Twyne Dune Indexer API Documentation

This document provides comprehensive documentation for all API endpoints in the Twyne Dune Indexer application. The API is built using the Sim IDX framework and provides access to indexed blockchain data related to collateral vaults, liquidations, and vault metrics.

## Base URL

All endpoints are prefixed with `/api/`

## Authentication

All endpoints require authentication using the Sim IDX authentication middleware.

## Common Response Format

All endpoints return JSON responses with consistent error handling:

```json
{
  "data": "...",
  "count": 10,
  "totalCount": 100,
  "limit": 50,
  "offset": 0,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

Error responses:
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

## Data Types

- **Address**: Ethereum address (40 hex characters, with or without 0x prefix)
- **Uint256**: Large integer values stored as strings
- **Block Number**: Integer block number
- **Block Timestamp**: Unix timestamp in seconds
- **Transaction Hash**: 32-byte hex string

---

## Collateral Vault Endpoints

### 1. Get All Created Vaults

**GET** `/api/collateralVaults`

Retrieves all created collateral vaults with pagination.

**Query Parameters:**
- `limit` (optional): Number of results to return (1-100, default: 50)
- `offset` (optional): Number of results to skip (default: 0)

**Response:**
```json
{
  "vaults": [
    {
      "vaultAddress": "0x...",
      "creator": "0x...",
      "factory": "0x...",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200",
      "txnHash": "0x...",
      "asset": "0x...",
      "intermediateVault": "0x...",
      "targetAsset": "0x...",
      "targetVault": "0x...",
      "twyneLiqLtv": "750000000000000000",
      "twyneVaultManager": "0x...",
      "version": "1"
    }
  ],
  "count": 50,
  "totalCount": 1000,
  "limit": 50,
  "offset": 0
}
```

### 2. Get Latest Position Snapshots

**GET** `/api/collateralVaults/latest-snapshots`

Retrieves the most recent position snapshot for each vault address.

**Query Parameters:**
- `limit` (optional): Number of results to return (1-100, default: 50)
- `offset` (optional): Number of results to skip (default: 0)
- `canLiquidate` (optional): Filter by liquidation status (true/false)
- `isExternallyLiquidated` (optional): Filter by external liquidation status (true/false)

**Response:**
```json
{
  "latestSnapshots": [
    {
      "vaultAddress": "0x...",
      "creditVault": "0x...",
      "debtVault": "0x...",
      "maxRelease": "1000000000000000000",
      "maxRepay": "500000000000000000",
      "totalAssetsDepositedOrReserved": "2000000000000000000",
      "userOwnedCollateral": "1500000000000000000",
      "twyneLiqLtv": "750000000000000000",
      "canLiquidate": false,
      "isExternallyLiquidated": false,
      "maxReleaseUsd": "1000000000",
      "maxRepayUsd": "500000000",
      "totalAssetsDepositedOrReservedUsd": "2000000000",
      "userOwnedCollateralUsd": "1500000000",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200",
      "logIndex": "10"
    }
  ],
  "count": 50,
  "totalUniqueVaults": 1000,
  "limit": 50,
  "offset": 0,
  "filters": {
    "canLiquidate": null,
    "isExternallyLiquidated": null
  },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 3. Get Latest Snapshot for Specific Vault

**GET** `/api/collateralVaults/{address}/latest-snapshot`

Retrieves the most recent position snapshot for a specific vault address.

**Path Parameters:**
- `address`: Vault address (40 hex characters, with or without 0x prefix)

**Response:**
```json
{
  "vaultAddress": "0x...",
  "latestSnapshot": {
    "vaultAddress": "0x...",
    "creditVault": "0x...",
    "debtVault": "0x...",
    "maxRelease": "1000000000000000000",
    "maxRepay": "500000000000000000",
    "totalAssetsDepositedOrReserved": "2000000000000000000",
    "userOwnedCollateral": "1500000000000000000",
    "twyneLiqLtv": "750000000000000000",
    "canLiquidate": false,
    "isExternallyLiquidated": false,
    "maxReleaseUsd": "1000000000",
    "maxRepayUsd": "500000000",
    "totalAssetsDepositedOrReservedUsd": "2000000000",
    "userOwnedCollateralUsd": "1500000000",
    "blockNumber": "12345678",
    "blockTimestamp": "1640995200",
    "logIndex": "10"
  },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

**Error Responses:**
- `400`: Invalid vault address format
- `404`: No position snapshots found for this vault address

### 4. Get Vault History

**GET** `/api/collateralVaults/{address}/history`

Retrieves all position snapshots for a specific vault address with pagination.

**Path Parameters:**
- `address`: Vault address (40 hex characters, with or without 0x prefix)

**Query Parameters:**
- `limit` (optional): Number of results to return (1-100, default: 50)
- `offset` (optional): Number of results to skip (default: 0)

**Response:**
```json
{
  "vaultAddress": "0x...",
  "snapshots": [
    {
      "vaultAddress": "0x...",
      "creditVault": "0x...",
      "debtVault": "0x...",
      "maxRelease": "1000000000000000000",
      "maxRepay": "500000000000000000",
      "totalAssetsDepositedOrReserved": "2000000000000000000",
      "userOwnedCollateral": "1500000000000000000",
      "twyneLiqLtv": "750000000000000000",
      "canLiquidate": false,
      "isExternallyLiquidated": false,
      "maxReleaseUsd": "1000000000",
      "maxRepayUsd": "500000000",
      "totalAssetsDepositedOrReservedUsd": "2000000000",
      "userOwnedCollateralUsd": "1500000000",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200",
      "logIndex": "10"
    }
  ],
  "count": 50,
  "totalCount": 200,
  "limit": 50,
  "offset": 0,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## Liquidation Endpoints

### 5. Get External Liquidations

**GET** `/api/collateralVaults/external-liquidations`

Retrieves external liquidation events for collateral vaults, including pre-liquidation data.

**Query Parameters:**
- `limit` (optional): Number of results to return (1-100, default: 50)
- `offset` (optional): Number of results to skip (default: 0)

**Response:**
```json
{
  "externalLiquidations": [
    {
      "vaultAddress": "0x...",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200",
      "txnHash": "0x...",
      "liquidator": "0x...",
      "violator": "0x...",
      "collateral": "0x...",
      "repayAssets": "1000000000000000000",
      "yieldBalance": "500000000000000000",
      "repayAssetsUsd": "1000000000",
      "yieldBalanceUsd": "500000000",
      "collateralAmount": "2000000000000000000",
      "debtAmount": "1500000000000000000",
      "collateralAmountUsd": "2000000000",
      "debtAmountUsd": "1500000000",
      "liqLtv": "750000000000000000",
      "preCollateralAmount": "2200000000000000000",
      "preCollateralAmountUsd": "2200000000",
      "preDebtAmount": "1600000000000000000",
      "preDebtAmountUsd": "1600000000"
    }
  ],
  "count": 50,
  "totalCount": 100,
  "limit": 50,
  "offset": 0,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 6. Get Internal Liquidations

**GET** `/api/collateralVaults/internal-liquidations`

Retrieves internal liquidation events (factory set collateral vault liquidated events) with position snapshot data.

**Query Parameters:**
- `limit` (optional): Number of results to return (1-100, default: 50)
- `offset` (optional): Number of results to skip (default: 0)
- `startBlock` (optional): Filter by minimum block number
- `endBlock` (optional): Filter by maximum block number
- `startTimestamp` (optional): Filter by minimum block timestamp
- `endTimestamp` (optional): Filter by maximum block timestamp

**Response:**
```json
{
  "internalLiquidations": [
    {
      "factory_address": "0x...",
      "collateral_vault": "0x...",
      "credit_vault": "0x...",
      "debt_vault": "0x...",
      "liquidator_address": "0x...",
      "block_number": "12345678",
      "block_timestamp": "1640995200",
      "txn_hash": "0x...",
      "credit_reserved": "1000000000000000000",
      "debt": "1500000000000000000",
      "twyne_liq_ltv": "750000000000000000",
      "credit_reserved_usd": "1000000000",
      "debt_usd": "1500000000",
      "pre_max_release": "800000000000000000",
      "pre_max_release_usd": "800000000",
      "pre_max_repay": "600000000000000000",
      "pre_max_repay_usd": "600000000",
      "pre_user_owned_collateral": "1200000000000000000",
      "pre_user_owned_collateral_usd": "1200000000",
      "pre_total_collateral": "2000000000000000000",
      "pre_total_collateral_usd": "2000000000",
      "total_collateral": "1800000000000000000",
      "total_assets_deposited_or_reserved_usd": "1800000000"
    }
  ],
  "count": 50,
  "totalCount": 100,
  "limit": 50,
  "offset": 0,
  "filters": {
    "startBlock": null,
    "endBlock": null,
    "startTimestamp": null,
    "endTimestamp": null
  },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## EVault Metrics Endpoints

### 7. Get Vault Metrics History

**GET** `/api/evault/{address}/metrics`

Retrieves historical metrics for a specific EVault address.

**Path Parameters:**
- `address`: Vault address (40 hex characters, with or without 0x prefix)

**Query Parameters:**
- `limit` (optional): Number of results to return (1-1000, default: 100)
- `offset` (optional): Number of results to skip (default: 0)
- `startBlock` (optional): Filter by minimum block number
- `endBlock` (optional): Filter by maximum block number
- `startTime` (optional): Filter by minimum block timestamp
- `endTime` (optional): Filter by maximum block timestamp

**Response:**
```json
{
  "vaultAddress": "0x...",
  "metrics": [
    {
      "vaultAddress": "0x...",
      "totalAssets": "10000000000000000000",
      "totalAssetsUsd": "10000000000",
      "totalBorrows": "5000000000000000000",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200"
    }
  ],
  "count": 100,
  "totalCount": 500,
  "limit": 100,
  "offset": 0
}
```

### 8. Get Latest Metrics for All Vaults

**GET** `/api/evaults/latest`

Retrieves the most recent metrics for all tracked EVaults.

**Response:**
```json
{
  "latestMetrics": [
    {
      "vaultAddress": "0x...",
      "totalAssets": "10000000000000000000",
      "totalAssetsUsd": "10000000000",
      "totalBorrows": "5000000000000000000",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200"
    }
  ],
  "count": 50,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## Chainlink Data Endpoints

### 9. Get Latest Chainlink Price Updates

**GET** `/api/chainlink/latest-answers`

Retrieves the 5 most recent Chainlink price feed updates.

**Response:**
```json
{
  "latestAnswers": [
    {
      "current": "200000000000",
      "roundId": "123456789",
      "updatedAt": "1640995200",
      "txnHash": "0x...",
      "blockNumber": "12345678",
      "blockTimestamp": "1640995200",
      "aggregator": "0x..."
    }
  ],
  "count": 5,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## Health Check Endpoint

### 10. Health Check

**GET** `/api/health`

Checks the health status of the API and database connection.

**Response (Healthy):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "totalVaults": 1000,
  "totalMetricsRecords": 50000
}
```

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "error": "Database connection failed",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## Error Handling

All endpoints use consistent error handling with appropriate HTTP status codes:

- **400 Bad Request**: Invalid parameters (e.g., malformed addresses, invalid pagination parameters)
- **404 Not Found**: Resource not found (e.g., no data for specified vault address)
- **500 Internal Server Error**: Database or server errors

Common error response format:
```json
{
  "error": "Error message describing what went wrong",
  "details": "Additional technical details (optional)"
}
```

---

## Address Validation

All endpoints that accept Ethereum addresses perform the following validation:
- Accept addresses with or without '0x' prefix
- Must be exactly 40 hexadecimal characters (20 bytes)
- Must contain only valid hex characters (0-9, a-f, A-F)

Example valid addresses:
- `0x1234567890123456789012345678901234567890`
- `1234567890123456789012345678901234567890`

---

## Pagination

Most endpoints support pagination with consistent parameters:
- `limit`: Maximum number of results (varies by endpoint, typically 1-100)
- `offset`: Number of results to skip for pagination

All paginated responses include:
- `count`: Number of items in current response
- `totalCount`: Total number of items available
- `limit`: Applied limit value
- `offset`: Applied offset value

---

## Rate Limiting and Authentication

All endpoints require authentication through the Sim IDX authentication middleware. Rate limiting and specific authentication requirements should be configured according to your deployment needs.

---

## Data Freshness

All endpoints include a `timestamp` field in responses indicating when the data was retrieved. The underlying data is updated in real-time as blockchain events are indexed by the Sim IDX listeners.
