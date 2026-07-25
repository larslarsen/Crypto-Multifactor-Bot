"""ARCH-002 — UniverseBinding contract and CMC survivorship adapter.

Membership for every experiment and paper session must resolve through a
catalog-published survivorship-aware universe dataset. Static venue maps are
symbol translation only, never membership.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.execution.symbols import (
    PAPER_TO_BINANCE_MAP,
    PAPER_TO_INSTRUMENT_ID,
)
from cryptofactors.universe.cmc_survivorship import (
    CMC_SURVIVORSHIP_DATASET_ID,
    CMCSurvivorshipProvider,
)

UNIVERSE_BINDING_CODE_VERSION: str = "v1"
SURVIVORSHIP_POLICY: str = "cmc_aware_proxy_v1"

# Prior sprint_004 artifacts listed in 41_DATA_ARCHITECTURE_GAP.md as
# survivorship-invalid for research conclusions.
SURVIVORSHIP_INVALID_ARTIFACT_IDS: frozenset[str] = frozenset({
    "EXP-004",
    "EXP-005",
    "EXP-006",
    "EXP-007",
    "EXP-008",
    "PAPER-007",
    "PAPER-008",
    "PAPER-009",
    "PROMO-003",
})


class UniverseBindingError(RuntimeError):
    """Raised when a UniverseBinding cannot be resolved or is empty."""


def is_survivorship_invalid(artifact_id: str) -> bool:
    """Return True if ``artifact_id`` is a known survivorship-invalid artifact.

    Matches exact ids or ids that start with any known prefix (e.g.
    ``EXP-004 grid``).
    """
    for prefix in SURVIVORSHIP_INVALID_ARTIFACT_IDS:
        if artifact_id == prefix or artifact_id.startswith(prefix + " "):
            return True
    return False


@runtime_checkable
class UniverseBinding(Protocol):
    """Protocol for a survivorship-aware universe membership binding."""

    universe_dataset_id: str
    survivorship_policy: str
    universe_code_version: str

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        """Return the set of eligible instrument/paper keys at ``decision_time``."""
        ...

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        """Return a coverage report for the universe at ``decision_time``."""
        ...


@dataclass(frozen=True, slots=True)
class CMCSurvivorshipBinding:
    """Binding backed by a catalog-published CMC survivorship universe dataset.

    Maps CMC ``instrument_id`` values (e.g. ``cmc_7``) to paper symbols when a
    ``key_map`` is provided. Without a map, the raw instrument ids are returned.
    """

    universe_dataset_id: str
    provider: CMCSurvivorshipProvider
    key_map: Mapping[str, str] = field(default_factory=dict)
    survivorship_policy: str = SURVIVORSHIP_POLICY
    universe_code_version: str = UNIVERSE_BINDING_CODE_VERSION

    def __post_init__(self) -> None:
        if self.provider.get_table().num_rows == 0:
            raise UniverseBindingError(
                "CMCSurvivorshipBinding cannot be constructed from an empty provider",
            )

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        """Return eligible paper/instrument keys at ``decision_time``."""
        ids = self.provider.universe_at(decision_time)
        if self.key_map:
            return frozenset(self.key_map.get(iid, iid) for iid in ids)
        return frozenset(ids)

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        """Return coverage metadata for the universe at ``decision_time``."""
        univ = self.universe_at(decision_time)
        return {
            "eligible": len(univ),
            "with_bars": None,
            "missing": None,
            "universe_dataset_id": self.universe_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
        }


def _default_symbol_to_paper_map() -> dict[str, str]:
    """Build a CMC/base-symbol -> paper-symbol map from the venue map.

    ``PAPER_TO_BINANCE_MAP`` maps ``XBTUSD`` -> ``BTCUSDT``. Stripping the
    quote leaves ``BTC`` -> ``XBTUSD``.

    Only canonical paper symbols (those present in ``PAPER_TO_INSTRUMENT_ID``)
    are included, so duplicates like ``BTCUSD`` do not overwrite ``XBTUSD``.
    """
    symbol_map: dict[str, str] = {}
    for paper, venue in PAPER_TO_BINANCE_MAP.items():
        if paper not in PAPER_TO_INSTRUMENT_ID:
            continue
        if venue.upper().endswith("USDT"):
            base = venue.upper()[:-len("USDT")]
        elif venue.upper().endswith("USD"):
            base = venue.upper()[:-len("USD")]
        else:
            base = venue.upper()
        symbol_map[base] = paper
    return symbol_map


def load_cmc_survivorship_binding(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
    symbol_map: Mapping[str, str] | None = None,
) -> CMCSurvivorshipBinding:
    """Load the latest (or requested) CMC survivorship dataset and bind it.

    Fail-closed:
    - Missing catalog dataset -> ``UniverseBindingError``.
    - Empty dataset -> ``UniverseBindingError``.
    - Missing parquet file -> ``UniverseBindingError``.
    """
    catalog: SqliteDatasetCatalog | None = None
    try:
        catalog = SqliteDatasetCatalog(db_path)
        resolved_id = dataset_id or catalog.resolve_latest_by_type(CMC_SURVIVORSHIP_DATASET_ID)
        if resolved_id is None:
            raise UniverseBindingError(
                f"No published dataset of type {CMC_SURVIVORSHIP_DATASET_ID} found",
            )
        files = catalog.list_files(resolved_id)
    except (sqlite3.Error, OSError) as exc:
        raise UniverseBindingError(
            f"Catalog lookup failed for dataset type {CMC_SURVIVORSHIP_DATASET_ID}: {exc}",
        ) from exc
    finally:
        if catalog is not None:
            catalog.close()

    parquet_path: Path | None = None
    for f in files:
        rel = str(f.get("relative_path", ""))
        if rel.endswith(".parquet"):
            parquet_path = Path(rel)
            break

    if parquet_path is None:
        raise UniverseBindingError(
            f"No parquet file found in dataset {resolved_id}",
        )

    config = DatasetStoreConfig(root=Path(store_root))
    root = Path(config.root).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    abs_dir = dataset_absolute_dir(root, resolved_id)
    full_path = abs_dir / parquet_path
    if not full_path.exists():
        raise UniverseBindingError(
            f"Dataset file missing: {full_path}",
        )

    try:
        provider = CMCSurvivorshipProvider.from_parquet(full_path)
    except Exception as exc:
        raise UniverseBindingError(
            f"Failed to load universe dataset {resolved_id} from {full_path}: {exc}",
        ) from exc

    if provider.get_table().num_rows == 0:
        raise UniverseBindingError(
            f"Universe dataset {resolved_id} is empty",
        )

    symbol_map = symbol_map or _default_symbol_to_paper_map()
    try:
        key_map = {
            r["instrument_id"]: symbol_map[symbol]
            for r in provider.records()
            if (symbol := str(r.get("symbol", "")).upper()) in symbol_map
        }
    except KeyError as exc:
        raise UniverseBindingError(
            f"Universe dataset {resolved_id} is missing required field: {exc}",
        ) from exc

    return CMCSurvivorshipBinding(
        universe_dataset_id=resolved_id,
        provider=provider,
        key_map=key_map,
    )


def load_paper_universe_binding(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
) -> CMCSurvivorshipBinding:
    """Convenience loader that returns CMC survivorship mapped to paper symbols."""
    return load_cmc_survivorship_binding(
        db_path,
        store_root,
        dataset_id=dataset_id,
        symbol_map=_default_symbol_to_paper_map(),
    )
