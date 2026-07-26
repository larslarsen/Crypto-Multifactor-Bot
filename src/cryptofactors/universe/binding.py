"""ARCH-002/ARCH-003 — point-in-time universe bindings.

Membership for every experiment and paper session resolves from catalog listing
events. Static execution maps translate already-resolved instrument IDs for
legacy paper callers only; they never determine membership.

Research/paper panel semantics (ADR-0014):
    tradable_panel(t) = declared_panel  minus  CMC-dead_at(t)

The CMC dataset is a dead-coin graveyard; it is used to *exclude* symbols from
a declared liquid panel, not to supply the panel itself.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.models import DatasetStoreConfig
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir
from cryptofactors.execution.symbols import (
    INSTRUMENT_ID_TO_PAPER,
    PAPER_TO_BINANCE_MAP,
    PAPER_TO_INSTRUMENT_ID,
)
from cryptofactors.universe.cmc_survivorship import (
    CMC_SURVIVORSHIP_DATASET_ID,
    CMCSurvivorshipProvider,
)
from cryptofactors.universe.listing_universe import (
    ListingUniverseProvider,
    load_listing_universe_provider,
)

UNIVERSE_BINDING_CODE_VERSION: str = "v2"
SURVIVORSHIP_POLICY: str = "cmc_aware_proxy_v1"
PAPER_PANEL_SURVIVORSHIP_POLICY: str = "paper_panel_minus_cmc_dead_v1"

# Known names for paper symbols to disambiguate ticker collisions.
# Key is the base asset (e.g., "SOL"), value is the expected CMC coin name.
PAPER_BASE_TO_NAME: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "ADA": "Cardano",
    "AVAX": "Avalanche",
    "DOT": "Polkadot",
    "LINK": "Chainlink",
    "LTC": "Litecoin",
    "BCH": "Bitcoin Cash",
    "DOGE": "Dogecoin",
    "UNI": "Uniswap",
    "AAVE": "Aave",
    "CRV": "Curve DAO",
    "APE": "ApeCoin",
    "NEAR": "NEAR Protocol",
    "FIL": "Filecoin",
    "ARB": "Arbitrum",
    "OP": "Optimism",
    "SUI": "Sui",
    "SEI": "Sei",
    "WLD": "Worldcoin",
    "PEPE": "Pepe",
}

PAPER_PANEL_SYMBOLS: frozenset[str] = frozenset(PAPER_TO_INSTRUMENT_ID.keys())

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
class PublishedListingUniverseBinding:
    """Membership from one immutable, catalog-published listing snapshot."""

    universe_dataset_id: str
    provider: ListingUniverseProvider
    key_map: Mapping[str, str] = field(default_factory=dict)
    survivorship_policy: str = "published_catalog_listing_lifecycle_v1"
    universe_code_version: str = UNIVERSE_BINDING_CODE_VERSION

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        instrument_ids = self.provider.universe_at(decision_time)
        result = (
            frozenset(self.key_map[item] for item in instrument_ids if item in self.key_map)
            if self.key_map
            else instrument_ids
        )
        if not result:
            raise UniverseBindingError(
                f"published listing universe is empty at {decision_time.isoformat()}"
            )
        return result

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        return {
            "eligible": len(self.universe_at(decision_time)),
            "with_bars": None,
            "missing": None,
            "universe_dataset_id": self.universe_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
        }


def load_universe_binding(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
) -> PublishedListingUniverseBinding:
    """Load the production binding from an immutable listing-universe dataset."""
    try:
        resolved_id, provider = load_listing_universe_provider(db_path, store_root, dataset_id)
    except ValueError as exc:
        raise UniverseBindingError(str(exc)) from exc
    return PublishedListingUniverseBinding(
        universe_dataset_id=resolved_id,
        provider=provider,
    )


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
        if not self.key_map:
            return frozenset(ids)
        # Only return mapped keys; unmapped ids are dropped to avoid leakage.
        return frozenset(
            self.key_map[iid]
            for iid in ids
            if iid in self.key_map
        )

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


def _base_asset(venue_symbol: str) -> str:
    """Extract base asset from a venue pair (e.g. BTCUSDT -> BTC)."""
    sym = venue_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix) and len(sym) > len(suffix):
            return sym[: -len(suffix)]
    return sym


def _paper_symbol_to_base(paper_symbol: str) -> str | None:
    """Map a paper symbol (e.g. XBTUSD) to its base asset (e.g. BTC)."""
    venue = PAPER_TO_BINANCE_MAP.get(paper_symbol)
    if venue is None:
        return None
    return _base_asset(venue)


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO datetime string into UTC, returning None on failure."""
    if not value:
        return None
    v = str(value).strip().upper().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class PaperPanelSurvivorshipBinding:
    """Paper panel binding: declared panel minus CMC-dead coins at ``t``.

    The CMC survivorship dataset is a dead-coin graveyard. This binding starts
    from a fixed liquid panel (e.g. the DATA-011 23-symbol paper map) and
    excludes any symbol whose name-matched CMC record is dead at the decision
    time. Only paper symbols are ever returned; raw CMC ids never leak.
    """

    universe_dataset_id: str
    provider: CMCSurvivorshipProvider
    panel: frozenset[str]
    base_to_name: Mapping[str, str]
    survivorship_policy: str = PAPER_PANEL_SURVIVORSHIP_POLICY
    universe_code_version: str = UNIVERSE_BINDING_CODE_VERSION
    _records_by_symbol: dict[str, tuple[dict[str, Any], ...]] = field(
        init=False, repr=False,
    )

    def __post_init__(self) -> None:
        if not self.panel:
            raise UniverseBindingError(
                "PaperPanelSurvivorshipBinding requires a non-empty panel",
            )
        if self.provider.get_table().num_rows == 0:
            raise UniverseBindingError(
                "PaperPanelSurvivorshipBinding cannot be constructed from an empty provider",
            )
        for sym in self.panel:
            if _paper_symbol_to_base(sym) is None:
                raise UniverseBindingError(
                    f"Paper symbol {sym!r} cannot be resolved to a base asset",
                )
        by_symbol: dict[str, list[dict[str, Any]]] = {}
        for record in self.provider.records():
            sym = str(record.get("symbol", "")).upper()
            if sym:
                by_symbol.setdefault(sym, []).append(record)
        object.__setattr__(
            self,
            "_records_by_symbol",
            {k: tuple(v) for k, v in by_symbol.items()},
        )

    def _is_dead_at(self, record: dict[str, Any], t: datetime) -> bool:
        """Return True if a CMC record is dead at time ``t``."""
        if record.get("is_active"):
            return False
        death_str = record.get("death_proxy_date")
        if not death_str:
            # Inactive with no death date is treated as dead for all times.
            return True
        death_dt = _parse_iso(str(death_str))
        if death_dt is None:
            # Unparseable death date: fail-closed and treat as dead.
            return True
        return t > death_dt

    def _dead_symbols(self, t: datetime) -> set[str]:
        """Return the subset of the panel that is CMC-dead at time ``t``."""
        dead: set[str] = set()
        for paper_sym in self.panel:
            base = _paper_symbol_to_base(paper_sym)
            if base is None:
                continue
            expected_name = self.base_to_name.get(base)
            if not expected_name:
                continue
            for record in self._records_by_symbol.get(base, ()):
                if not self._is_dead_at(record, t):
                    continue
                if str(record.get("name", "")).lower() != expected_name.lower():
                    continue
                dead.add(paper_sym)
                break
        return dead

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        """Return the survivorship-filtered paper panel at ``decision_time``."""
        t = decision_time if decision_time.tzinfo else decision_time.replace(tzinfo=UTC)
        dead = self._dead_symbols(t)
        result = self.panel - dead
        if not result:
            raise UniverseBindingError(
                f"Paper panel is empty after survivorship filter at {decision_time.isoformat()}; "
                f"panel={len(self.panel)}, dead={len(dead)}",
            )
        return frozenset(result)

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        """Return coverage metadata for the panel at ``decision_time``."""
        t = decision_time if decision_time.tzinfo else decision_time.replace(tzinfo=UTC)
        dead = self._dead_symbols(t)
        result = self.panel - dead
        return {
            "eligible": len(result),
            "excluded": len(dead),
            "panel": len(self.panel),
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


def _load_cmc_provider(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
) -> tuple[str, CMCSurvivorshipProvider]:
    """Load the latest (or requested) CMC survivorship dataset from the catalog.

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
        rel = str(f.get("storage_uri", ""))
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

    return resolved_id, provider


def load_cmc_survivorship_binding(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
    symbol_map: Mapping[str, str] | None = None,
) -> CMCSurvivorshipBinding:
    """Load the latest (or requested) CMC survivorship dataset and bind it."""
    resolved_id, provider = _load_cmc_provider(db_path, store_root, dataset_id)

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
    panel: frozenset[str] | None = None,
    base_to_name: Mapping[str, str] | None = None,
) -> PublishedListingUniverseBinding:
    """Load legacy paper keys from catalog-resolved Binance listing events.

    ``store_root``, ``dataset_id``, ``panel``, and ``base_to_name`` remain in
    the signature so existing callers do not break. They are intentionally not
    membership inputs: listing lifecycle in ``ref_listing_event`` is authoritative.
    ``INSTRUMENT_ID_TO_PAPER`` only adapts resolved integer IDs to the legacy
    execution namespace.
    """
    del panel, base_to_name
    try:
        resolved_id, provider = load_listing_universe_provider(db_path, store_root, dataset_id)
    except ValueError as exc:
        raise UniverseBindingError(str(exc)) from exc
    return PublishedListingUniverseBinding(
        universe_dataset_id=resolved_id,
        provider=provider,
        key_map={str(instrument_id): paper for instrument_id, paper in INSTRUMENT_ID_TO_PAPER.items()},
    )
