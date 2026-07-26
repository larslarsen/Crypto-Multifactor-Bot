"""Catalog-consumer normalization and publication for Binance raw objects.

Raw acquisition owns network I/O and raw object persistence. This helper is a
separate consumer path: it accepts a catalog-resolved canonical instrument ID
from its caller and never maps symbols, tickers, or paper keys itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetPublishResult, DatasetStoreConfig
from cryptofactors.catalog.dataset.publisher import DatasetPublisher
from cryptofactors.ingest.binance import normalize_binance_kline


def publish_binance_source_bars(
    raw_object: Any,
    *,
    interval: str,
    canonical_instrument_id: int,
    catalog_path: Path,
    dataset_store_root: Path,
    stage_dir: Path,
    code_commit: str,
) -> DatasetPublishResult:
    """Normalize and publish one raw Binance object for a resolved instrument.

    ``canonical_instrument_id`` must originate from
    :class:`ReferenceIdentityResolver`; this function deliberately has no venue
    symbol parameter and cannot perform an identity lookup.
    """
    stage_dir.mkdir(parents=True, exist_ok=True)
    normalized = normalize_binance_kline(
        raw_objects=[raw_object],
        market_type="spot",
        interval=interval,
        venue_id="binance",
        instrument_id=str(canonical_instrument_id),
        output_dir=stage_dir,
        code_commit=code_commit,
    )
    catalog = SqliteDatasetCatalog(catalog_path)
    try:
        return DatasetPublisher(DatasetStoreConfig(root=dataset_store_root), catalog).publish(
            normalized.publish_plan,
            register_catalog=True,
        )
    finally:
        catalog.close()
