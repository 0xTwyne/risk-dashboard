"""
Pydantic models for API response validation and type safety.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime


class BaseAPIResponse(BaseModel):
    """Base response model with common fields."""
    timestamp: Optional[str] = None
    count: Optional[int] = None
    totalCount: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class CollateralVaultSnapshot(BaseModel):
    """Model for collateral vault position snapshot."""
    chainId: str
    vaultAddress: str
    creditVault: str
    debtVault: str
    maxRelease: str
    maxRepay: str
    totalAssetsDepositedOrReserved: str
    userOwnedCollateral: str
    twyneLiqLtv: str
    canLiquidate: bool
    isExternallyLiquidated: bool
    maxReleaseUsd: str
    maxRepayUsd: str
    totalAssetsDepositedOrReservedUsd: str
    userOwnedCollateralUsd: str
    blockNumber: str
    blockTimestamp: str
    logIndex: str


class CollateralVaultsSnapshotsResponse(BaseAPIResponse):
    """Response model for collateral vaults latest snapshots."""
    latestSnapshots: List[CollateralVaultSnapshot]
    totalUniqueVaults: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None


class CollateralVaultHistoryResponse(BaseAPIResponse):
    """Response model for collateral vault history."""
    vaultAddress: str
    snapshots: List[CollateralVaultSnapshot]


class CollateralVault(BaseModel):
    """Model for created collateral vault."""
    vaultAddress: str
    creator: str
    factory: str
    blockNumber: str
    blockTimestamp: str
    txnHash: str
    asset: str
    intermediateVault: str
    targetAsset: str
    targetVault: str
    twyneLiqLtv: str
    twyneVaultManager: str
    version: str


class CollateralVaultsResponse(BaseAPIResponse):
    """Response model for collateral vaults."""
    vaults: List[CollateralVault]


class ExternalLiquidation(BaseModel):
    """Model for external liquidation event."""
    vaultAddress: str
    blockNumber: str
    blockTimestamp: str
    txnHash: str
    liquidator: str
    violator: str
    collateral: str
    repayAssets: str
    yieldBalance: str
    repayAssetsUsd: str
    yieldBalanceUsd: str
    collateralAmount: str
    debtAmount: str
    collateralAmountUsd: str
    debtAmountUsd: str
    liqLtv: str
    preCollateralAmount: str
    preCollateralAmountUsd: str
    preDebtAmount: str
    preDebtAmountUsd: str


class ExternalLiquidationsResponse(BaseAPIResponse):
    """Response model for external liquidations."""
    externalLiquidations: List[ExternalLiquidation]


class InternalLiquidation(BaseModel):
    """Model for internal liquidation event."""
    factory_address: str
    collateral_vault: str
    credit_vault: str
    debt_vault: str
    liquidator_address: str
    block_number: str
    block_timestamp: str
    txn_hash: str
    credit_reserved: str
    debt: str
    twyne_liq_ltv: str
    credit_reserved_usd: str
    debt_usd: str
    pre_max_release: str
    pre_max_release_usd: str
    pre_max_repay: str
    pre_max_repay_usd: str
    pre_user_owned_collateral: str
    pre_user_owned_collateral_usd: str
    pre_total_collateral: str
    pre_total_collateral_usd: str
    total_collateral: str
    total_assets_deposited_or_reserved_usd: str


class InternalLiquidationsResponse(BaseAPIResponse):
    """Response model for internal liquidations."""
    internalLiquidations: List[InternalLiquidation]
    filters: Optional[Dict[str, Any]] = None


class EVaultMetric(BaseModel):
    """Model for EVault metric."""
    chainId: str
    vaultAddress: str
    totalAssets: str
    totalAssetsUsd: str
    totalBorrows: str
    totalBorrowsUsd: str
    decimals: str
    asset: str
    interestRate: str
    symbol: str
    name: str
    blockNumber: str
    blockTimestamp: str


class EVaultMetricsResponse(BaseAPIResponse):
    """Response model for EVault metrics."""
    vaultAddress: Optional[str] = None
    metrics: Optional[List[EVaultMetric]] = None
    latestMetrics: Optional[List[EVaultMetric]] = None
    # Pagination fields
    count: Optional[int] = None
    totalCount: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class ChainlinkAnswer(BaseModel):
    """Model for Chainlink price feed answer."""
    current: str
    roundId: str
    updatedAt: str
    txnHash: str
    blockNumber: str
    blockTimestamp: str
    aggregator: str


class ChainlinkAnswersResponse(BaseAPIResponse):
    """Response model for Chainlink latest answers."""
    latestAnswers: List[ChainlinkAnswer]


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    totalVaults: Optional[int] = None
    totalMetricsRecords: Optional[int] = None
    error: Optional[str] = None


class APIError(BaseModel):
    """Model for API error responses."""
    error: str
    details: Optional[str] = None
