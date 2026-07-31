"""Market-layer canonical datasets (BAR-001, DEX-003 registry).

Depends on catalog + reference + quality layers. No network acquisition.
"""

from __future__ import annotations

from cryptofactors.market.bars import (
    CANONICAL_BAR_SCHEMA_NAME,
    CANONICAL_BAR_SCHEMA_VERSION,
    CANONICAL_BAR_TRANSFORM_NAME,
    CANONICAL_BAR_TRANSFORM_VERSION,
    MARKET_BARS_DATASET_TYPE,
    CanonicalBarPublishResult,
    PartitionSizeMeasurement,
    VerifiedDailySource,
    VerifiedSourceBarDataset,
    publish_canonical_bars,
)
from cryptofactors.market.dex_pool_registry import (
    DEX_POOL_REGISTRY_DATASET_TYPE,
    DEX_POOL_REGISTRY_RELATIVE_PATH,
    DEX_POOL_REGISTRY_SCHEMA_NAME,
    DEX_POOL_REGISTRY_SCHEMA_VERSION,
    DEX_POOL_REGISTRY_TRANSFORM_NAME,
    DEX_POOL_REGISTRY_TRANSFORM_VERSION,
    PINNED_PAIR_CREATED_DATASET_ID,
    DexPoolRegistryBuildResult,
    DexPoolRegistryError,
    DexPoolRegistryRow,
    build_dex_pool_registry,
    is_direct_stable_quote_pair,
    orient_base_quote,
    select_direct_stable_quote_pools,
)

__all__ = [
    "CANONICAL_BAR_SCHEMA_NAME",
    "CANONICAL_BAR_SCHEMA_VERSION",
    "CANONICAL_BAR_TRANSFORM_NAME",
    "CANONICAL_BAR_TRANSFORM_VERSION",
    "DEX_POOL_REGISTRY_DATASET_TYPE",
    "DEX_POOL_REGISTRY_RELATIVE_PATH",
    "DEX_POOL_REGISTRY_SCHEMA_NAME",
    "DEX_POOL_REGISTRY_SCHEMA_VERSION",
    "DEX_POOL_REGISTRY_TRANSFORM_NAME",
    "DEX_POOL_REGISTRY_TRANSFORM_VERSION",
    "MARKET_BARS_DATASET_TYPE",
    "PINNED_PAIR_CREATED_DATASET_ID",
    "CanonicalBarPublishResult",
    "DexPoolRegistryBuildResult",
    "DexPoolRegistryError",
    "DexPoolRegistryRow",
    "PartitionSizeMeasurement",
    "VerifiedDailySource",
    "VerifiedSourceBarDataset",
    "build_dex_pool_registry",
    "is_direct_stable_quote_pair",
    "orient_base_quote",
    "publish_canonical_bars",
    "select_direct_stable_quote_pools",
]
