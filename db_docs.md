
# Twyne Indexer GraphQL API Documentation

## Overview

This document provides a comprehensive guide to the Twyne Indexer database schema and GraphQL API. The system indexes blockchain events from the Twyne Protocol, storing both raw events and aggregated state for various protocol components.

## Core Entity Types

The database contains three primary categories of entities:

### 1. Event Entities
Event entities record individual blockchain events with transaction metadata. Each event entity includes:
- `id`: Unique identifier (typically `chainId_blockNumber_logIndex`)
- `blockNumber`: Block where event occurred
- `blockTimestamp`: Timestamp of the block
- `srcAddress`: Contract address that emitted the event
- Event-specific parameters

### 2. Detail Entities
Detail entities store the current state of protocol components, aggregating data from multiple events:

#### EulerCollateralVaultDetails
Represents a collateral vault that users can deposit assets into and borrow against.
```
EulerCollateralVaultDetails {
  id                # Contract address
  evc               # Euler V Controller address
  asset             # Underlying asset address
  borrower          # Borrower address
  intermediateVault # Associated intermediate vault address
  name              # Vault name
  symbol            # Vault symbol
  targetVault       # Target vault address
  twyneLiqLTV       # Liquidation LTV (Loan-to-Value ratio)
  version           # Contract version
  createdAt         # Creation timestamp
  createdAtBlock    # Creation block number
  totalSupplied     # Total assets supplied to vault
  totalCredit       # Total credit taken from intermediate vault
  totalBorrowed     # Total assets borrowed from target vault
}
```

#### IntermediateVaultDetails
Represents an intermediate vault that collateral vaults borrow from.
```
IntermediateVaultDetails {
  id                     # Contract address
  evc                    # Euler V Controller address
  asset                  # Underlying asset address
  supplyCap              # Maximum allowed supply
  borrowCap              # Maximum allowed borrows
  creator                # Creator address
  dToken                 # Debt token address
  decimals               # Asset decimals
  feeReceiver            # Fee receiver address
  governorAdmin          # Admin address
  interestAccumulator    # Interest accumulator
  interestFee            # Interest fee
  interestRateModel      # Interest rate model address
  liquidationCoolOffTime # Liquidation cooldown period
  maxLiquidationDiscount # Maximum liquidation discount
  oracle                 # Price oracle address
  name                   # Vault name
  symbol                 # Vault symbol
  unitOfAccount          # Unit of account
  totalSupplied          # Total assets supplied
  totalBorrowed          # Total assets borrowed
  aggregator             # Price aggregator address
}
```

#### EVaultDetails
Represents an Euler vault (either collateral asset or target asset).
```
EVaultDetails {
  id                     # Contract address
  evc                    # Euler V Controller address
  asset                  # Underlying asset address
  supplyCap              # Maximum allowed supply
  borrowCap              # Maximum allowed borrows
  creator                # Creator address
  dToken                 # Debt token address
  decimals               # Asset decimals
  feeReceiver            # Fee receiver address
  governorAdmin          # Admin address
  interestAccumulator    # Interest accumulator
  interestFee            # Interest fee
  interestRateModel      # Interest rate model address
  liquidationCoolOffTime # Liquidation cooldown period
  maxLiquidationDiscount # Maximum liquidation discount
  oracle                 # Price oracle address
  name                   # Vault name
  symbol                 # Vault symbol
  unitOfAccount          # Unit of account
  aggregator             # Price aggregator address
}
```

### 3. Price Data
`ChainlinkAggregator_AnswerUpdated` events track asset price updates:
```
ChainlinkAggregator_AnswerUpdated {
  id            # Unique event ID
  blockNumber   # Block number
  blockTimestamp # Timestamp
  current       # Current price
  roundId       # Oracle round ID
  updatedAt     # Oracle update timestamp
  srcAddress    # Aggregator address
}
```

## Data Relationships

Key relationships in the system:
- Each `EulerCollateralVaultDetails` has an associated `intermediateVault` and `targetVault`
- Each vault (Collateral, Intermediate, EVault) has an `asset` (token address)
- Vaults can reference price data through their `aggregator` field

## State Management

The system maintains aggregated state through event handlers:

1. **Collateral Vaults**:
   - `totalSupplied` increases with Deposit/DepositUnderlying events
   - `totalSupplied` decreases with Withdraw/RedeemUnderlying events
   - `totalBorrowed` increases with Borrow events
   - `totalBorrowed` decreases with Repay events
   - `totalCredit` tracks borrowing from intermediate vaults

2. **Intermediate Vaults**:
   - `totalSupplied` tracks deposits from users
   - `totalBorrowed` tracks loans to collateral vaults

## Common Query Patterns

### 1. Current Protocol Stats

```graphql
query GetProtocolStats {
  # Get all collateral vaults
  collateralVaults: EulerCollateralVaultDetails {
    id
    name
    symbol
    totalSupplied
    totalBorrowed
    totalCredit
  }
  
  # Get all intermediate vaults
  intermediateVaults: IntermediateVaultDetails {
    id
    name
    symbol
    totalSupplied
    totalBorrowed
  }
}
```

### 2. Vault Details with Asset Information

```graphql
query GetVaultWithAsset($vaultId: ID!) {
  vault: EulerCollateralVaultDetails(where: {id: {_eq: $vaultId}}) {
    id
    name
    symbol
    totalSupplied
    totalBorrowed
    
    # Get collateral asset details
    assetDetails: EVaultDetails(where: {id: {_eq: $asset}}) {
      name
      symbol
      decimals
    }
    
    # Get target vault details
    targetDetails: EVaultDetails(where: {id: {_eq: $targetVault}}) {
      name
      symbol
      decimals
    }
  }
}
```

### 3. Recent Price Updates for an Asset

```graphql
query GetAssetPrices($aggregatorAddress: String!, $limit: Int = 100) {
  prices: ChainlinkAggregator_AnswerUpdated(
    where: {srcAddress: {_eq: $aggregatorAddress}}
    order_by: {blockNumber: desc}
    limit: $limit
  ) {
    blockNumber
    blockTimestamp
    current
  }
}
```

### 4. Historical State at Block

For time-series data, you can calculate the state at any historical block using approaches similar to the CVs_at_block.sql example:

1. Get all vault entities created up to target block
2. Calculate balance changes by summing events up to target block
3. Aggregate to determine state at that block

## Tips for Efficient Querying

1. **Use Aggregation Functions**:
   - Hasura exposes SQL aggregation functions like `sum`, `max`, `count`
   - Example: `sum(totalSupplied)` to get protocol TVL

2. **Filter at Database Level**:
   - Always push filters to the database via `where` clauses
   - Use `_and`, `_or`, `_gt`, `_lt` operators for complex conditions

3. **Limit Result Sets**:
   - Use `limit` and `offset` for pagination
   - Order data with `order_by` for consistent pagination

4. **Join Data Efficiently**:
   - GraphQL allows fetching related data in a single query
   - Use nested selections to fetch related entities

5. **Time-Series Considerations**:
   - For charts, query data at intervals using timestamp filters
   - Consider pre-computing time-series data for complex metrics

## Advanced Risk Metrics

To implement advanced risk metrics as mentioned in your requirements:

1. **Value at Risk (VaR)**:
   - Query collateral vaults with their current positions
   - Join with price data history to determine volatility
   - Calculate VaR based on position size, volatility, and confidence level

2. **Liquidation Risk**:
   - Query `twyneLiqLTV` from collateral vaults
   - Compare with current position (totalBorrowed/totalSupplied)
   - Calculate "distance to liquidation" as percentage of price movement

3. **Utilization Rates**:
   - Calculate per-vault: `totalBorrowed / totalSupplied`
   - Calculate protocol-wide: `sum(totalBorrowed) / sum(totalSupplied)`

## Conclusion

The Twyne Indexer GraphQL API provides comprehensive access to the protocol's state and event history. By understanding the entity types, relationships, and query patterns outlined in this document, you can efficiently build dashboard visualizations and risk analysis tools on top of this data.
