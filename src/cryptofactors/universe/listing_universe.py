"""ARCH-003 immutable listing-universe dataset provider."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir

LISTING_UNIVERSE_DATASET_TYPE: Final[str] = "reference_listing_universe"
LISTING_UNIVERSE_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("listing_event_id", pa.string()),
        ("canonical_instrument_id", pa.int64()),
        ("venue", pa.string()),
        ("venue_symbol", pa.string()),
        ("event_type", pa.string()),
        ("valid_from_us", pa.int64()),
        ("valid_to_us", pa.int64()),
        ("known_from_us", pa.int64()),
        ("known_to_us", pa.int64()),
    ]
)


def _us(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return int(value.astimezone(UTC).timestamp() * 1_000_000)


class ListingUniverseProvider:
    """Lifecycle membership over one immutable, knowledge-pinned dataset."""

    def __init__(self, table: pa.Table) -> None:
        if not table.schema.equals(LISTING_UNIVERSE_SCHEMA, check_metadata=False):
            raise ValueError("listing universe schema mismatch")
        self._records = tuple(table.to_pylist())

    @classmethod
    def from_parquet(cls, path: Path) -> ListingUniverseProvider:
        return cls(pq.read_table(path))

    def get_table(self) -> pa.Table:
        return pa.Table.from_pylist(list(self._records), schema=LISTING_UNIVERSE_SCHEMA)

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        at = _us(decision_time)
        latest: dict[tuple[str, str], Mapping[str, Any]] = {}
        for row in self._records:
            if int(row["known_from_us"]) > at:
                continue
            known_to = row.get("known_to_us")
            if known_to is not None and int(known_to) <= at:
                continue
            if int(row["valid_from_us"]) > at:
                continue
            valid_to = row.get("valid_to_us")
            if valid_to is not None and int(valid_to) <= at:
                continue
            key = (str(row["venue"]), str(row["venue_symbol"]))
            prior = latest.get(key)
            if prior is None or (
                int(row["valid_from_us"]), int(row["known_from_us"]), str(row["listing_event_id"])
            ) > (
                int(prior["valid_from_us"]),
                int(prior["known_from_us"]),
                str(prior["listing_event_id"]),
            ):
                latest[key] = row
        return frozenset(
            str(row["canonical_instrument_id"])
            for row in latest.values()
            if row["event_type"] in {"LIST", "RESUME"}
        )


def build_listing_universe_table(
    events: Sequence[Mapping[str, object]], *, venue: str
) -> pa.Table:
    """Build the immutable schema from resolver lifecycle records."""
    def parse(value: object | None) -> int | None:
        if value is None:
            return None
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return _us(parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC))

    rows = [
        {
            "listing_event_id": str(event["listing_event_id"]),
            "canonical_instrument_id": int(event["canonical_instrument_id"]),
            "venue": venue.upper(),
            "venue_symbol": str(event["venue_symbol"]),
            "event_type": str(event["event_type"]),
            "valid_from_us": parse(event["valid_from"]),
            "valid_to_us": parse(event.get("valid_to")),
            "known_from_us": parse(event["known_from"]),
            "known_to_us": parse(event.get("known_to")),
        }
        for event in events
    ]
    if not rows:
        raise ValueError("listing universe cannot be empty")
    return pa.Table.from_pylist(rows, schema=LISTING_UNIVERSE_SCHEMA)


def load_listing_universe_provider(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
) -> tuple[str, ListingUniverseProvider]:
    """Load one immutable listing universe dataset from the dataset catalog."""
    catalog = SqliteDatasetCatalog(db_path)
    try:
        resolved_id = dataset_id or catalog.resolve_latest_by_type(LISTING_UNIVERSE_DATASET_TYPE)
        if resolved_id is None:
            raise ValueError("no published reference listing universe dataset")
        files = catalog.list_files(resolved_id)
    finally:
        catalog.close()
    relative = next((Path(str(item["storage_uri"])) for item in files if str(item["storage_uri"]).endswith(".parquet")), None)
    if relative is None:
        raise ValueError(f"listing universe dataset {resolved_id} has no parquet output")
    root = Path(DatasetStoreConfig(root=Path(store_root)).root)
    if not root.is_absolute():
        root = Path.cwd() / root
    path = dataset_absolute_dir(root, resolved_id) / relative
    if not path.exists():
        raise ValueError(f"listing universe dataset file is missing: {path}")
    return resolved_id, ListingUniverseProvider.from_parquet(path)
