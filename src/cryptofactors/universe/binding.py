"""ARCH-002 — UniverseBinding contract and CMC survivorship adapter.

Membership for every experiment and paper session must resolve through a
catalog-published survivorship-aware universe dataset. Static venue maps are
symbol translation only, never membership.

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

import pyarrow as pa
import pyarrow.parquet as pq

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

# Bumped from v2: membership is now the catalog-published quality-bar panel minus
# CMC-dead names, and is gated on as-of bar coverage. A v2 fingerprint describes
# different semantics and must not be mistaken for this one.
UNIVERSE_BINDING_CODE_VERSION: str = "v3"
SURVIVORSHIP_POLICY: str = "cmc_aware_proxy_v1"
PAPER_PANEL_SURVIVORSHIP_POLICY: str = "quality_bar_panel_minus_cmc_dead_v1"

QUALITY_BAR_PANEL_DATASET_TYPE: str = "market_bars"

# Pinned, never resolved by recency: resolve_latest_by_type("market_bars") returns
# whichever bar dataset published most recently (currently a 953k-row unrelated
# panel), not the reviewer-accepted DATA-011 artifact. ARCH-002 membership must be
# anchored to the exact accepted panel, the same way DATA-008 pins DATA-006.
DATA011_QUALITY_BAR_PANEL_DATASET_ID: str = (
    "ds_2bf3bf423a0c751e856dad506f12b6d8b4185b01f7408c46d76a9e7eed3f1497"
)

# DATA-011 writes each 1d bar into both a daily/ and an intraday/ tree. Reading both
# double-counts every row, so membership and coverage read the daily tree only.
_BAR_TREE_PREFIX: str = "market_bars/daily/"

# market_bars timestamps are epoch microseconds.
_US_PER_SECOND: int = 1_000_000

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

# PAPER_PANEL_SYMBOLS (frozenset(PAPER_TO_INSTRUMENT_ID)) was removed deliberately.
# A module-level "the panel is these names" constant is precisely the static-map
# membership ADR-0014 forbids; the panel now comes from load_quality_bar_panel().

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
    bar_panel_dataset_id: str
    survivorship_policy: str
    universe_code_version: str

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        """Return the set of eligible instrument/paper keys at ``decision_time``."""
        ...

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        """Return a coverage report for the universe at ``decision_time``."""
        ...

    def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
        """Return the identity a run artifact must record to be reproducible."""
        ...


@dataclass(frozen=True, slots=True)
class QualityBarPanel:
    """The declared research panel, read from a catalog-published bar dataset.

    ADR-0014 permits static maps as venue/symbol *translation* only. The panel
    membership therefore comes from the instrument ids actually present in the
    accepted DATA-011 artifact; ``PAPER_TO_INSTRUMENT_ID`` is used solely to render
    those ids as paper symbols.
    """

    dataset_id: str
    symbols: frozenset[str]
    first_bar_at: Mapping[str, datetime]
    last_bar_at: Mapping[str, datetime]

    def covered_at(self, t: datetime) -> frozenset[str]:
        """Panel symbols whose bar coverage actually spans ``t``.

        A name with no bar on or before ``t`` cannot be scored at ``t``; including
        it would silently hand the factor a symbol with no price history.
        """
        return frozenset(
            sym for sym in self.symbols
            if self.first_bar_at[sym] <= t <= self.last_bar_at[sym]
        )


def _instrument_id_to_paper() -> dict[int, str]:
    """Reverse the paper translation map: numeric instrument id -> paper symbol."""
    return {iid: paper for paper, iid in PAPER_TO_INSTRUMENT_ID.items()}


def load_quality_bar_panel(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
) -> QualityBarPanel:
    """Load the declared quality-bar panel and its per-symbol coverage.

    Fail-closed on every degenerate outcome: missing catalog row, no bar files,
    an instrument id absent from the translation map, or an empty panel. Any of
    those silently shrinking the research universe is exactly the survivorship
    failure ADR-0014 exists to prevent.
    """
    resolved_id = dataset_id or DATA011_QUALITY_BAR_PANEL_DATASET_ID
    catalog: SqliteDatasetCatalog | None = None
    try:
        catalog = SqliteDatasetCatalog(db_path)
        files = catalog.list_files(resolved_id)
    except (sqlite3.Error, OSError) as exc:
        raise UniverseBindingError(
            f"Catalog lookup failed for quality bar panel {resolved_id}: {exc}",
        ) from exc
    finally:
        if catalog is not None:
            catalog.close()

    if not files:
        raise UniverseBindingError(
            f"Quality bar panel dataset {resolved_id} is not present in the catalog",
        )

    bar_files = [
        str(f.get("storage_uri", ""))
        for f in files
        if str(f.get("storage_uri", "")).startswith(_BAR_TREE_PREFIX)
    ]
    if not bar_files:
        raise UniverseBindingError(
            f"Quality bar panel {resolved_id} contains no {_BAR_TREE_PREFIX} files",
        )

    root = Path(DatasetStoreConfig(root=Path(store_root)).root).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    abs_dir = dataset_absolute_dir(root, resolved_id)

    id_to_paper = _instrument_id_to_paper()
    first: dict[str, datetime] = {}
    last: dict[str, datetime] = {}
    for relative in bar_files:
        full_path = abs_dir / relative
        if not full_path.exists():
            raise UniverseBindingError(f"Quality bar panel file missing: {full_path}")
        try:
            table = pq.read_table(full_path, columns=["instrument_id", "period_start"])
        except (OSError, pa.ArrowInvalid) as exc:
            raise UniverseBindingError(
                f"Cannot read quality bar panel file {full_path}: {exc}",
            ) from exc
        for raw_id, raw_start in zip(
            table.column("instrument_id").to_pylist(),
            table.column("period_start").to_pylist(),
            strict=True,
        ):
            paper = id_to_paper.get(int(raw_id)) if raw_id is not None else None
            if paper is None:
                raise UniverseBindingError(
                    f"Quality bar panel {resolved_id} contains instrument id "
                    f"{raw_id!r} with no paper translation; refusing to emit a "
                    "raw identity into the research universe",
                )
            # market_bars stores period_start in epoch microseconds, matching
            # CMC_SURVIVORSHIP's _US_PER_SECOND convention. Treating it as seconds
            # yields year-50001627 timestamps and silently breaks as-of coverage.
            try:
                moment = datetime.fromtimestamp(int(raw_start) / _US_PER_SECOND, UTC)
            except (OverflowError, OSError, ValueError, TypeError) as exc:
                raise UniverseBindingError(
                    f"Quality bar panel {resolved_id} has unrepresentable "
                    f"period_start {raw_start!r} for instrument {raw_id!r}",
                ) from exc
            if paper not in first or moment < first[paper]:
                first[paper] = moment
            if paper not in last or moment > last[paper]:
                last[paper] = moment

    if not first:
        raise UniverseBindingError(
            f"Quality bar panel {resolved_id} produced an empty panel",
        )

    return QualityBarPanel(
        dataset_id=resolved_id,
        symbols=frozenset(first),
        first_bar_at=dict(first),
        last_bar_at=dict(last),
    )


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
    bar_panel_dataset_id: str
    provider: CMCSurvivorshipProvider
    panel: QualityBarPanel
    base_to_name: Mapping[str, str]
    survivorship_policy: str = PAPER_PANEL_SURVIVORSHIP_POLICY
    universe_code_version: str = UNIVERSE_BINDING_CODE_VERSION
    _records_by_symbol: dict[str, tuple[dict[str, Any], ...]] = field(
        init=False, repr=False,
    )

    def __post_init__(self) -> None:
        if not self.panel.symbols:
            raise UniverseBindingError(
                "PaperPanelSurvivorshipBinding requires a non-empty panel",
            )
        if self.provider.get_table().num_rows == 0:
            raise UniverseBindingError(
                "PaperPanelSurvivorshipBinding cannot be constructed from an empty provider",
            )
        for sym in self.panel.symbols:
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
        for paper_sym in self.panel.symbols:
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

    def _resolve(self, decision_time: datetime) -> tuple[datetime, frozenset[str], set[str], frozenset[str]]:
        """Return ``(t, with_bars, dead, eligible)`` for ``decision_time``."""
        t = decision_time if decision_time.tzinfo else decision_time.replace(tzinfo=UTC)
        with_bars = self.panel.covered_at(t)
        dead = self._dead_symbols(t)
        return t, with_bars, dead, frozenset(with_bars - dead)

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        """Return the survivorship-filtered, bar-covered paper panel at ``decision_time``."""
        t, with_bars, dead, eligible = self._resolve(decision_time)
        if not with_bars:
            raise UniverseBindingError(
                f"Quality bar panel {self.bar_panel_dataset_id} has no as-of coverage at "
                f"{t.isoformat()}; panel={len(self.panel.symbols)}. Membership cannot be "
                "resolved outside the published bar window",
            )
        if not eligible:
            raise UniverseBindingError(
                f"Paper panel is empty after survivorship filter at {t.isoformat()}; "
                f"panel={len(self.panel.symbols)}, with_bars={len(with_bars)}, dead={len(dead)}",
            )
        return eligible

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        """Return coverage metadata for the panel at ``decision_time``."""
        t, with_bars, dead, eligible = self._resolve(decision_time)
        return {
            "eligible": len(eligible),
            "excluded_dead": len(dead),
            "panel": len(self.panel.symbols),
            "with_bars": len(with_bars),
            "missing": sorted(self.panel.symbols - with_bars),
            "decision_time": t.isoformat(),
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
        }

    def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
        """Return the identity a run artifact must record to be reproducible.

        Both dataset identities are required: the universe alone does not
        determine membership, because the panel and its as-of coverage come
        from the bar dataset.
        """
        t, with_bars, dead, eligible = self._resolve(decision_time)
        return {
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
            "decision_time": t.isoformat(),
            "eligible_count": len(eligible),
            "with_bars_count": len(with_bars),
            "excluded_dead_count": len(dead),
            "panel_count": len(self.panel.symbols),
        }


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

    # The catalog file column is `storage_uri`; the previous `relative_path` lookup
    # matched nothing, so this loader could never resolve a real published dataset.
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


def load_paper_universe_binding(
    db_path: Path | str,
    store_root: Path | str,
    dataset_id: str | None = None,
    base_to_name: Mapping[str, str] | None = None,
    *,
    bar_panel_dataset_id: str | None = None,
) -> PaperPanelSurvivorshipBinding:
    """Load the composite survivorship binding used by every experiment and paper run.

    Membership is the catalog-published DATA-011 quality-bar panel, restricted to
    names whose bar coverage spans the decision time, minus names that CMC records
    as dead at that time. There is deliberately no ``panel`` override and no static
    fallback: accepting a caller-supplied panel would reintroduce exactly the
    "universe of whoever we like" failure ADR-0014 closes.
    """
    resolved_id, provider = _load_cmc_provider(db_path, store_root, dataset_id)
    panel = load_quality_bar_panel(db_path, store_root, bar_panel_dataset_id)

    return PaperPanelSurvivorshipBinding(
        universe_dataset_id=resolved_id,
        bar_panel_dataset_id=panel.dataset_id,
        provider=provider,
        panel=panel,
        base_to_name=base_to_name or PAPER_BASE_TO_NAME,
    )
