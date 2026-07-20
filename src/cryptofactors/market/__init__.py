"""Market-layer canonical datasets (BAR-001).

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

__all__ = [
    "CANONICAL_BAR_SCHEMA_NAME",
    "CANONICAL_BAR_SCHEMA_VERSION",
    "CANONICAL_BAR_TRANSFORM_NAME",
    "CANONICAL_BAR_TRANSFORM_VERSION",
    "MARKET_BARS_DATASET_TYPE",
    "CanonicalBarPublishResult",
    "PartitionSizeMeasurement",
    "VerifiedDailySource",
    "VerifiedSourceBarDataset",
    "publish_canonical_bars",
]
