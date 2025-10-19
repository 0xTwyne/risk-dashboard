"""
Pydantic models for API response validation and type safety.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class BaseAPIResponse(BaseModel):
    """Base response model with common fields."""
    timestamp: Optional[str] = None
    count: Optional[int] = None
    totalCount: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class CollateralVaultSnapshot(BaseModel):
    """Model for collateral vault position snapshot.

    API v1.2: All numeric values returned as JSON numbers (not strings).
    All token amounts and LTV values are pre-scaled (human-readable).
    No client-side decimal scaling needed.
    """
    # Address fields - strings
    vaultAddress: str
    underlyingCollateralVault: str
    creditVault: str
    debtVault: str
    # Token amounts - numbers (floats), scaled by token decimals (e.g., 1000.5)
    maxRelease: float
    maxRepay: float
    totalAssetsDepositedOrReserved: float
    userOwnedCollateral: float
    # LTV - number (float), scaled value (e.g., 0.75 = 75%)
    twyneLiqLtv: float
    # Boolean fields
    canLiquidate: bool
    isExternallyLiquidated: bool
    # Block/transaction info - numbers (integers)
    blockNumber: int
    blockTimestamp: int
    logIndex: int
    # USD fields - numbers (floats), human-readable (only present in snapshots endpoint, not history endpoint)
    maxReleaseUsd: Optional[float] = None
    maxRepayUsd: Optional[float] = None
    totalAssetsDepositedOrReservedUsd: Optional[float] = None
    userOwnedCollateralUsd: Optional[float] = None
    # Optional fields - only present in history endpoint, not snapshots endpoint
    chainId: Optional[int] = None  # Number, not string
    state: Optional[str] = None
    txType: Optional[str] = None
    # Price metadata fields (v1.2) - numbers (integers)
    underlyingCollateralVaultPriceBlock: Optional[int] = None
    underlyingCollateralVaultPriceTimestamp: Optional[int] = None
    creditVaultPriceBlock: Optional[int] = None
    creditVaultPriceTimestamp: Optional[int] = None
    debtVaultPriceBlock: Optional[int] = None
    debtVaultPriceTimestamp: Optional[int] = None


class CollateralVaultsSnapshotsResponse(BaseAPIResponse):
    """Response model for collateral vaults latest snapshots."""
    snapshots: List[CollateralVaultSnapshot]  # API returns 'snapshots', not 'latestSnapshots'
    totalUniqueVaults: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    blockNumber: Optional[Any] = None  # Can be int, string, or object - handle flexibly
    timestamp: Optional[Any] = None  # Can be int, string, or object
    snapshotBlock: Optional[Any] = None  # Can be int, string, or object
    priceBlock: Optional[Any] = None  # Can be int, string, or object
    aggregates: Optional[Dict[str, Any]] = None  # Summary aggregates
    vaultPrices: Optional[Dict[str, Dict[str, Any]]] = None  # Vault price lookup


class CollateralVaultHistoryResponse(BaseAPIResponse):
    """Response model for collateral vault history."""
    vaultAddress: str
    snapshots: List[CollateralVaultSnapshot]


class CollateralVault(BaseModel):
    """Model for created collateral vault.

    API v1.2: Numeric values are JSON numbers, pre-scaled.
    """
    vaultAddress: str
    creator: str
    factory: str
    blockNumber: int
    blockTimestamp: int
    txnHash: str
    asset: str
    intermediateVault: str
    targetAsset: str
    targetVault: str
    twyneLiqLtv: float
    twyneVaultManager: str
    version: str


class CollateralVaultsResponse(BaseAPIResponse):
    """Response model for collateral vaults."""
    vaults: List[CollateralVault]


class ExternalLiquidation(BaseModel):
    """Model for external liquidation event.

    API v1.2: All numeric values are JSON numbers (not strings), pre-scaled.
    """
    vaultAddress: str
    blockNumber: int
    blockTimestamp: int
    txnHash: str
    liquidator: str
    violator: str
    creditVault: str
    debtVault: str
    underlyingCollateralVault: str
    collateral: str
    repayAssets: float
    yieldBalance: float
    repayAssetsUsd: float
    yieldBalanceUsd: float
    collateralAmount: float
    debtAmount: float
    collateralAmountUsd: float
    debtAmountUsd: float
    eulerLiqLtv: float
    twyneLiqLtv: float
    twyneMaxLiqLtv: float
    twyneSafetyBuffer: float
    creditReserved: float
    creditReservedUsd: float
    preCollateralAmount: float
    preCollateralAmountUsd: float
    preDebtAmount: float
    preDebtAmountUsd: float


class ExternalLiquidationsResponse(BaseAPIResponse):
    """Response model for external liquidations."""
    externalLiquidations: List[ExternalLiquidation]


class InternalLiquidation(BaseModel):
    """Model for internal liquidation event.

    API v1.2: All numeric values are JSON numbers (not strings), pre-scaled.
    """
    chainId: int
    factoryAddress: str
    collateralVault: str
    creditVault: str
    debtVault: str
    underlyingCollateralVault: str
    liquidatorAddress: str
    blockNumber: int
    blockTimestamp: int
    txnHash: str
    creditReserved: float
    debt: float
    totalCollateral: float
    userOwnedCollateral: float
    twyneLiqLtv: float
    creditReservedUsd: float
    debtUsd: float
    totalCollateralUsd: float
    userOwnedCollateralUsd: float


class InternalLiquidationsResponse(BaseAPIResponse):
    """Response model for internal liquidations."""
    internalLiquidations: List[InternalLiquidation]
    filters: Optional[Dict[str, Any]] = None


class EVaultMetric(BaseModel):
    """Model for EVault metric - matches actual API response with snake_case.

    API v1.2: All token amounts and rates are pre-scaled (human-readable).
    All numeric values are returned as JSON numbers (not strings).
    No client-side decimal scaling needed.
    """
    model_config = ConfigDict(populate_by_name=True)

    # API returns snake_case, but we provide camelCase aliases for backward compatibility
    chain_id: int = Field(alias="chainId")
    vault_address: str = Field(alias="vaultAddress")
    # Token amounts - numbers (floats), scaled by token decimals (e.g., 10000.0)
    total_assets: float = Field(alias="totalAssets")
    total_borrows: float = Field(alias="totalBorrows")
    # USD values - numbers (floats)
    total_assets_usd: float = Field(alias="totalAssetsUsd")
    total_borrows_usd: float = Field(alias="totalBorrowsUsd")
    decimals: int  # API returns integer, not string
    asset: str
    # Interest rate - number (float), scaled (e.g., 0.05 for 5%)
    interest_rate: float = Field(alias="interestRate")
    symbol: str
    name: str
    block_number: int = Field(alias="blockNumber")
    block_timestamp: int = Field(alias="blockTimestamp")
    # Cash - number (float), scaled by token decimals
    cash: Optional[float] = None
    # Interest accumulator - number (float), scaled (e.g., 1.05)
    interest_accumulator: Optional[float] = Field(default=None, alias="interestAccumulator")


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
    """Model for Chainlink price feed answer.

    API v1.2: All numeric values are JSON numbers (not strings), pre-scaled.
    """
    current: float
    roundId: int
    updatedAt: int
    txnHash: str
    blockNumber: int
    blockTimestamp: int
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
