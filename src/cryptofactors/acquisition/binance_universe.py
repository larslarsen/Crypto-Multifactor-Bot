"""DATA-008 Binance spot universe expansion: discovery, eligibility, and priority.

This supersedes ``binance_universe_expansion``. Three concerns that were previously
entangled are now separate and separately auditable:

* **Discovery** -- which spot symbols exist and are tradable, taken from
  ``exchangeInfo`` where ``status``, ``baseAsset`` and ``quoteAsset`` are actually
  stated rather than inferred from the symbol string.
* **Eligibility** -- whether a symbol has enough observed history to be research
  usable. A newly listed asset is *deferred with a reason*, never silently admitted.
* **Priority** -- a deterministic ranking over observed volume evidence, where the
  measurement window, observation time, tie-break and raw lineage are all explicit.

Every exclusion carries a machine-readable reason drawn from a versioned taxonomy, so
a later run can be diffed against an earlier one and the difference explained.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from cryptofactors.ingest.raw_http import (
    AcquisitionLog,
    AcquisitionOutcome,
    RawHttpAcquirer,
    canonical_json,
)

BINANCE_BASE_URL = "https://api.binance.com"
EXCHANGE_INFO_SOURCE_ID = "binance_exchange_info"
TICKER_SOURCE_ID = "binance_ticker_24hr"
KLINES_SOURCE_ID = "binance_klines"

#: Bump when the taxonomy or any classification rule changes, so two reports are
#: only comparable when they were produced under the same rules. 2026-07-27.1 adds
#: RLUSD and further stablecoin bases, which earlier evidence had allowed to rank.
EXCLUSION_TAXONOMY_VERSION = "2026-07-27.1"

#: Semantics of selection and eligibility. Bumped whenever the *meaning* of a terminal
#: outcome changes, so a corrected rule set resets queue progress even when the scalar
#: configuration is unchanged. Deliberately not the Git commit: unrelated code changes
#: must not discard multi-day queue position.
SELECTION_POLICY_VERSION = "2026-07-27.2"

#: The volume evidence this ticket ranks on. The ticket requires top-N by 30-day
#: volume, so ranking sums quote volume over trailing daily bars rather than reading
#: the 24-hour ticker. Ranking measures every eligible symbol; 24-hour data is recorded
#: as a non-truncating observation under PREFILTER_WINDOW and never limits the field.
VOLUME_WINDOW = "30d"

PREFILTER_WINDOW = "24h"
RANKING_DAYS = 30

DEFAULT_QUOTE_ASSETS = ("USDT",)
DEFAULT_MIN_QUOTE_VOLUME = 1_000_000.0
DEFAULT_MIN_HISTORY_DAYS = 365


class BinanceUniverseError(RuntimeError):
    """Raised for malformed Binance responses or invalid configuration."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class ExclusionReason(str, Enum):
    """Versioned exclusion taxonomy. Every rejected symbol carries one of these."""

    NOT_SPOT = "NOT_SPOT"
    NOT_TRADING = "NOT_TRADING"
    QUOTE_ASSET_NOT_TARGETED = "QUOTE_ASSET_NOT_TARGETED"
    LEVERAGED_TOKEN = "LEVERAGED_TOKEN"
    STABLECOIN_BASE = "STABLECOIN_BASE"
    FIAT_BASE = "FIAT_BASE"
    TOKENIZED_COMMODITY_BASE = "TOKENIZED_COMMODITY_BASE"
    BELOW_VOLUME_FLOOR = "BELOW_VOLUME_FLOOR"
    NO_VOLUME_EVIDENCE = "NO_VOLUME_EVIDENCE"
    INSUFFICIENT_VOLUME_WINDOW = "INSUFFICIENT_VOLUME_WINDOW"
    ALREADY_COVERED = "ALREADY_COVERED"
    BELOW_TOP_N = "BELOW_TOP_N"


class DeferralReason(str, Enum):
    """Why an otherwise-selectable symbol is not yet research-ready."""

    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INSUFFICIENT_VOLUME_WINDOW = "INSUFFICIENT_VOLUME_WINDOW"
    #: The provider answered and the symbol genuinely has no bars.
    NO_HISTORY = "NO_HISTORY"
    #: We could not observe the symbol at all. Not a deferral: it stays pending.
    HISTORY_REQUEST_FAILED = "HISTORY_REQUEST_FAILED"


#: Non-target base assets. Membership is data, not code, so the taxonomy version
#: above is what makes two runs comparable.
STABLECOIN_BASES = frozenset({
    "USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "UST", "USTC",
    "PAX", "SUSD", "GUSD", "LUSD", "PYUSD", "EURI", "AEUR", "USD1",
    # Observed on the exchange but previously only caught by the volume floor, so a
    # volume increase could have admitted them as research assets.
    "BFUSD", "FRAX", "USDE", "USDS", "XUSD",
    # REVIEW-0211/0242: RLUSD is a stablecoin base, not a research asset.
    "RLUSD", "USDD", "USDQ", "EURQ", "USDG", "USDX", "USDF",
})
FIAT_BASES = frozenset({
    "EUR", "GBP", "AUD", "TRY", "BRL", "RUB", "UAH", "ZAR", "NGN", "IDRT",
    "JPY", "ARS", "RON", "PLN", "CZK", "MXN", "COP",
})
TOKENIZED_COMMODITY_BASES = frozenset({"PAXG", "XAUT", "XAU", "TGOLD"})

#: Binance leveraged-token suffixes, matched against the *base asset* only.
LEVERAGED_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _whole_milliseconds(value: Any) -> int | None:
    """Decode a millisecond field as a finite whole number, or None if malformed.

    int() on a non-finite or fractional value raises outside the typed failure path,
    and truncating a fractional timestamp would silently invent a different instant.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or value != int(value)):
        return None
    return int(value)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SpotSymbol:
    """One symbol as ``exchangeInfo`` states it -- nothing inferred from the string."""

    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    is_spot_trading_allowed: bool
    permissions: tuple[str, ...]
    raw_object_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "status": self.status,
            "is_spot_trading_allowed": self.is_spot_trading_allowed,
            "permissions": list(self.permissions),
            "raw_object_id": self.raw_object_id,
        }


BASE_PANEL_DATASET_ID = (
    "ds_7a0a16834098aa336155bc5cd8085066e09c20343f5933c7017e508250a6c988"
)


def load_base_panel_symbols(db_path: Any, dataset_id: str, *, store_root: Any) -> set[str]:
    """Symbols carried by the pinned accepted base panel.

    Pinned rather than resolved: ``resolve_latest_by_type("market_bars")`` returns
    whichever dataset published most recently, which is not the reviewer-authorized
    DATA-006 artifact. Fails closed -- an unavailable base or unmappable membership
    must stop the run, because an empty base would let the additive take re-add
    symbols the panel already covers.
    """
    import sqlite3
    from pathlib import Path

    import pyarrow.parquet as pq

    from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
    from cryptofactors.catalog.dataset.paths import dataset_absolute_dir

    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as exc:
        raise BinanceUniverseError("cannot open the catalog for base-panel lookup") from exc
    try:
        row = conn.execute(
            "SELECT dataset_id FROM dataset WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()
        if row is None:
            raise BinanceUniverseError(
                f"pinned base panel {dataset_id} is not registered in this catalog",
                context={"dataset_id": dataset_id},
            )
        declared = [
            (str(r[0]), str(r[1]), int(r[2]), int(r[3])) for r in conn.execute(
                "SELECT storage_uri, file_sha256, byte_size, row_count "
                "FROM dataset_file WHERE dataset_id = ?", (dataset_id,)
            )
        ]
        if not declared:
            raise BinanceUniverseError(f"pinned base panel {dataset_id} declares no files")

        root = dataset_absolute_dir(Path(store_root), dataset_id)
        instrument_ids: set[Any] = set()
        for storage_uri, sha256, byte_size, row_count in declared:
            path = root / storage_uri
            # Every declared file must be present and match the catalog. Skipping an
            # unreadable file would let partial store corruption pass as reconciled
            # membership whenever the survivors happened to expose all instruments.
            if not path.exists():
                raise BinanceUniverseError(
                    f"pinned base panel file is missing: {storage_uri}",
                    context={"dataset_id": dataset_id},
                )
            actual_sha, actual_size = stream_sha256_and_size(path)
            if actual_sha != sha256 or actual_size != byte_size:
                raise BinanceUniverseError(
                    f"pinned base panel file does not match the catalog: {storage_uri}",
                    context={"expected_sha256": sha256, "actual_sha256": actual_sha},
                )
            if path.suffix != ".parquet":
                continue
            # Row count comes from footer metadata and only the identity column is
            # materialised. Reading whole tables held every declared file's full
            # contents in memory just to collect ids -- fine for the pinned base,
            # unbounded for a larger one.
            try:
                parquet = pq.ParquetFile(path)
                if parquet.metadata.num_rows != row_count:
                    raise BinanceUniverseError(
                        f"pinned base panel file row count mismatch: {storage_uri}",
                        context={"expected": row_count, "actual": parquet.metadata.num_rows},
                    )
                if "instrument_id" not in parquet.schema_arrow.names:
                    continue
                for batch in parquet.iter_batches(columns=["instrument_id"], batch_size=65_536):
                    instrument_ids |= set(batch.column("instrument_id").to_pylist())
            except BinanceUniverseError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise BinanceUniverseError(
                    f"pinned base panel file is unreadable: {storage_uri}"
                ) from exc
        if not instrument_ids:
            raise BinanceUniverseError(
                f"pinned base panel {dataset_id} yielded no instrument identities"
            )

        placeholders = ",".join("?" * len(instrument_ids))
        rows = conn.execute(
            "SELECT b.display_name, q.display_name FROM ref_instrument i "
            "JOIN ref_asset b ON b.asset_id = i.base_asset_id "
            "JOIN ref_asset q ON q.asset_id = i.quote_asset_id "
            f"WHERE i.instrument_id IN ({placeholders})",
            tuple(str(i) for i in instrument_ids),
        ).fetchall()
    except sqlite3.Error as exc:
        raise BinanceUniverseError("base-panel reference lookup failed") from exc
    finally:
        conn.close()

    symbols = {f"{str(b).strip().upper()}{str(q).strip().upper()}" for b, q in rows}
    if len(symbols) != len(instrument_ids):
        raise BinanceUniverseError(
            f"pinned base panel {dataset_id} has {len(instrument_ids)} instruments but "
            f"{len(symbols)} are mappable to symbols",
        )
    return symbols


def parse_exchange_info(payload: Any, *, raw_object_id: str) -> list[SpotSymbol]:
    """Decode ``exchangeInfo`` into stated symbol facts."""
    if not isinstance(payload, Mapping):
        raise BinanceUniverseError("exchangeInfo response must be a JSON object")
    symbols = payload.get("symbols")
    if not isinstance(symbols, list):
        raise BinanceUniverseError("exchangeInfo.symbols must be a list")

    parsed: list[SpotSymbol] = []
    seen: set[str] = set()
    for entry in symbols:
        if not isinstance(entry, Mapping):
            raise BinanceUniverseError("exchangeInfo symbol entry must be an object")
        for key in ("symbol", "baseAsset", "quoteAsset", "status"):
            if key not in entry:
                raise BinanceUniverseError(f"exchangeInfo symbol entry is missing {key!r}")
        symbol = str(entry["symbol"]).strip().upper()
        if not symbol:
            raise BinanceUniverseError("exchangeInfo symbol must be non-empty")
        if symbol in seen:
            raise BinanceUniverseError(f"exchangeInfo repeats symbol {symbol}")
        seen.add(symbol)

        permissions_raw = entry.get("permissions")
        permissions: tuple[str, ...] = ()
        if isinstance(permissions_raw, list):
            permissions = tuple(
                str(p).strip().upper() for p in permissions_raw if isinstance(p, str)
            )
        elif isinstance(permissions_raw, str):
            permissions = (permissions_raw.strip().upper(),)

        parsed.append(SpotSymbol(
            symbol=symbol,
            base_asset=str(entry["baseAsset"]).strip().upper(),
            quote_asset=str(entry["quoteAsset"]).strip().upper(),
            status=str(entry["status"]).strip().upper(),
            is_spot_trading_allowed=bool(entry.get("isSpotTradingAllowed", True)),
            permissions=permissions,
            raw_object_id=raw_object_id,
        ))
    return sorted(parsed, key=lambda item: item.symbol)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def is_leveraged_token(
    base_asset: str,
    *,
    permissions: Sequence[str] = (),
    known_bases: Iterable[str] = (),
) -> bool:
    """Whether a base asset is a Binance leveraged token.

    Two evidence sources, never a substring scan of the whole symbol. That scan is
    what removed ordinary listings: ``SUPERUSDT`` and ``JUPUSDT`` both contain ``UP``
    and were silently dropped from the universe.

    1. ``exchangeInfo`` permissions naming LEVERAGED are authoritative.
    2. Otherwise the *base* must end in a leveraged suffix **and** the remaining stem
       must itself be a base asset the exchange lists. ``BTCUP`` splits into ``BTC``,
       which exists, so it is leveraged. ``JUP`` splits into ``J``, which does not,
       so it is an ordinary asset.
    """
    if any("LEVERAGED" in permission for permission in permissions):
        return True

    base = base_asset.strip().upper()
    stems = {str(item).strip().upper() for item in known_bases}
    for suffix in LEVERAGED_SUFFIXES:
        if not base.endswith(suffix):
            continue
        stem = base[: -len(suffix)]
        if stem and stem in stems:
            return True
    return False


def classify_base_asset(base_asset: str) -> ExclusionReason | None:
    """Taxonomy membership for a base asset, or None when it is a target asset."""
    base = base_asset.strip().upper()
    if base in STABLECOIN_BASES:
        return ExclusionReason.STABLECOIN_BASE
    if base in FIAT_BASES:
        return ExclusionReason.FIAT_BASE
    if base in TOKENIZED_COMMODITY_BASES:
        return ExclusionReason.TOKENIZED_COMMODITY_BASE
    return None


@dataclass(frozen=True, slots=True)
class Exclusion:
    symbol: str
    base_asset: str
    quote_asset: str
    reason: ExclusionReason
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "reason": self.reason.value,
            "detail": self.detail,
            "taxonomy_version": EXCLUSION_TAXONOMY_VERSION,
        }


# ---------------------------------------------------------------------------
# Volume evidence and priority
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VolumeEvidence:
    """Observed volume for one symbol, with the window and lineage that produced it."""

    symbol: str
    quote_volume: float
    trade_count: int
    window: str
    observed_at: datetime
    raw_object_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quote_volume": self.quote_volume,
            "trade_count": self.trade_count,
            "window": self.window,
            "observed_at": self.observed_at.isoformat(),
            "raw_object_id": self.raw_object_id,
        }


def parse_ticker_evidence(
    payload: Any, *, observed_at: datetime, raw_object_id: str, window: str = PREFILTER_WINDOW
) -> dict[str, VolumeEvidence]:
    """Decode /ticker/24hr into per-symbol volume evidence."""
    if not isinstance(payload, list):
        raise BinanceUniverseError("ticker/24hr response must be a list")
    evidence: dict[str, VolumeEvidence] = {}
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise BinanceUniverseError("ticker entry must be an object")
        symbol = str(entry.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        quote_volume = _finite(entry.get("quoteVolume"))
        if quote_volume is None or quote_volume < 0:
            continue
        count = _finite(entry.get("count"))
        evidence[symbol] = VolumeEvidence(
            symbol=symbol,
            quote_volume=quote_volume,
            trade_count=int(count) if count is not None else 0,
            window=window,
            observed_at=observed_at,
            raw_object_id=raw_object_id,
        )
    return evidence


class MeasurementStatus(str, Enum):
    """Why a 30-day measurement did or did not produce evidence.

    A genuinely short window is a fact about the symbol; a failed or malformed
    request is a fact about us. Collapsing both into "no evidence" let a transient
    failure silently promote a lower-ranked survivor into the canonical universe.
    """

    OK = "OK"
    INCOMPLETE_WINDOW = "INCOMPLETE_WINDOW"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class VolumeMeasurement:
    symbol: str
    status: MeasurementStatus
    evidence: VolumeEvidence | None
    reason: str

    @property
    def usable(self) -> bool:
        return self.status is MeasurementStatus.OK and self.evidence is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "status": self.status.value,
            "reason": self.reason,
            "evidence": None if self.evidence is None else self.evidence.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class RankedSymbol:
    symbol: str
    base_asset: str
    quote_asset: str
    rank: int
    evidence: VolumeEvidence

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "rank": self.rank,
            "evidence": self.evidence.as_dict(),
        }


def rank_symbols(
    candidates: Sequence[tuple[SpotSymbol, VolumeEvidence]],
) -> list[RankedSymbol]:
    """Rank by descending observed volume, breaking ties on symbol.

    The tie-break is explicit so two runs over identical evidence produce identical
    ranks; sorting on volume alone leaves equal-volume symbols in input order.
    """
    ordered = sorted(
        candidates, key=lambda pair: (-pair[1].quote_volume, pair[0].symbol)
    )
    return [
        RankedSymbol(
            symbol=spot.symbol, base_asset=spot.base_asset, quote_asset=spot.quote_asset,
            rank=index + 1, evidence=evidence,
        )
        for index, (spot, evidence) in enumerate(ordered)
    ]


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SelectionConfig:
    quote_assets: tuple[str, ...] = DEFAULT_QUOTE_ASSETS
    min_quote_volume: float = DEFAULT_MIN_QUOTE_VOLUME
    min_history_days: int = DEFAULT_MIN_HISTORY_DAYS
    top_n: int | None = 100
    base_panel_dataset_id: str = ""
    symbols_per_day: int = 20_000
    default_start: str = ""
    pinned_end: str = ""
    cursor_policy: str = "queue_position_persistent;capacity_per_processing_day"
    policy_version: str = SELECTION_POLICY_VERSION
    evidence_source: str = BINANCE_BASE_URL

    def as_dict(self) -> dict[str, Any]:
        return {
            "quote_assets": list(self.quote_assets),
            "min_quote_volume": self.min_quote_volume,
            "min_history_days": self.min_history_days,
            "top_n": self.top_n,
            "base_panel_dataset_id": self.base_panel_dataset_id,
            "symbols_per_day": self.symbols_per_day,
            "default_start": self.default_start,
            "pinned_end": self.pinned_end,
            "cursor_policy": self.cursor_policy,
            "policy_version": self.policy_version,
            "evidence_source": self.evidence_source,
            "volume_window": VOLUME_WINDOW,
            "prefilter_window": PREFILTER_WINDOW,
            "taxonomy_version": EXCLUSION_TAXONOMY_VERSION,
        }

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict()).encode()).hexdigest()

    def selection_fingerprint(self) -> str:
        """Identity of *what* is being selected, excluding how fast we may work.

        Queue progress is keyed by this: changing capacity or cursor policy must not
        discard position, but changing eligibility, thresholds, quote assets, the
        pinned range or the base binding must start a new queue.
        """
        material = {
            k: v for k, v in self.as_dict().items()
            # Capacity and cursor mechanics are not selection identity; the policy
            # version and provider source are.
            if k not in ("symbols_per_day", "cursor_policy")
        }
        return hashlib.sha256(canonical_json(material).encode()).hexdigest()


@dataclass
class SelectionResult:
    """Discovery and priority outcome, with every decision explained."""

    ranked: list[RankedSymbol] = field(default_factory=list)
    excluded: list[Exclusion] = field(default_factory=list)
    config: SelectionConfig = field(default_factory=SelectionConfig)

    @property
    def symbols(self) -> list[str]:
        return [item.symbol for item in self.ranked]

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.as_dict(),
            "selected": [item.as_dict() for item in self.ranked],
            "excluded": [item.as_dict() for item in self.excluded],
        }


def filter_non_volume_taxonomy(
    *,
    discovered: Sequence[SpotSymbol],
    config: SelectionConfig,
    already_covered: Iterable[str] = (),
) -> tuple[list[SpotSymbol], list[Exclusion]]:
    """Apply every non-volume rule, without consulting volume evidence at all.

    Separated so that measurement coverage cannot depend on the 24-hour ticker: a
    tradable target symbol missing from that feed still has to receive a 30-day
    measurement, and previously it was dropped as NO_VOLUME_EVIDENCE instead.
    """
    covered = {str(item).strip().upper() for item in already_covered}
    known_bases = {item.base_asset for item in discovered}
    survivors: list[SpotSymbol] = []
    excluded: list[Exclusion] = []

    for spot in discovered:
        def drop(reason: ExclusionReason, detail: str, spot: SpotSymbol = spot) -> None:
            excluded.append(Exclusion(
                symbol=spot.symbol, base_asset=spot.base_asset,
                quote_asset=spot.quote_asset, reason=reason, detail=detail,
            ))

        if spot.quote_asset not in config.quote_assets:
            drop(
                ExclusionReason.QUOTE_ASSET_NOT_TARGETED,
                f"quote asset {spot.quote_asset} not in {list(config.quote_assets)}",
            )
            continue
        if not spot.is_spot_trading_allowed or (
            spot.permissions and not any("SPOT" in p for p in spot.permissions)
        ):
            drop(ExclusionReason.NOT_SPOT, "symbol is not spot tradable")
            continue
        if spot.status != "TRADING":
            drop(ExclusionReason.NOT_TRADING, f"exchangeInfo status is {spot.status}")
            continue
        if is_leveraged_token(
            spot.base_asset, permissions=spot.permissions, known_bases=known_bases
        ):
            drop(ExclusionReason.LEVERAGED_TOKEN, f"{spot.base_asset} is a leveraged token")
            continue
        taxonomy = classify_base_asset(spot.base_asset)
        if taxonomy is not None:
            drop(taxonomy, f"{spot.base_asset} is classified {taxonomy.value}")
            continue
        if spot.symbol in covered:
            drop(ExclusionReason.ALREADY_COVERED, "symbol already in the covered panel")
            continue
        survivors.append(spot)

    return survivors, excluded


def select_symbols(
    *,
    discovered: Sequence[SpotSymbol],
    evidence: Mapping[str, VolumeEvidence],
    config: SelectionConfig,
    already_covered: Iterable[str] = (),
) -> SelectionResult:
    """Apply the taxonomy and the volume floor, then rank what survives."""
    covered = {str(item).strip().upper() for item in already_covered}
    known_bases = {item.base_asset for item in discovered}
    excluded: list[Exclusion] = []
    candidates: list[tuple[SpotSymbol, VolumeEvidence]] = []

    for spot in discovered:
        def drop(reason: ExclusionReason, detail: str) -> None:
            excluded.append(Exclusion(
                symbol=spot.symbol, base_asset=spot.base_asset,
                quote_asset=spot.quote_asset, reason=reason, detail=detail,
            ))

        if spot.quote_asset not in config.quote_assets:
            drop(
                ExclusionReason.QUOTE_ASSET_NOT_TARGETED,
                f"quote asset {spot.quote_asset} not in {list(config.quote_assets)}",
            )
            continue
        if not spot.is_spot_trading_allowed or (
            spot.permissions and not any("SPOT" in p for p in spot.permissions)
        ):
            drop(ExclusionReason.NOT_SPOT, "symbol is not spot tradable")
            continue
        if spot.status != "TRADING":
            drop(ExclusionReason.NOT_TRADING, f"exchangeInfo status is {spot.status}")
            continue
        if is_leveraged_token(
            spot.base_asset, permissions=spot.permissions, known_bases=known_bases
        ):
            drop(ExclusionReason.LEVERAGED_TOKEN, f"{spot.base_asset} is a leveraged token")
            continue

        taxonomy = classify_base_asset(spot.base_asset)
        if taxonomy is not None:
            drop(taxonomy, f"{spot.base_asset} is classified {taxonomy.value}")
            continue
        if spot.symbol in covered:
            drop(ExclusionReason.ALREADY_COVERED, "symbol already in the covered panel")
            continue

        observed = evidence.get(spot.symbol)
        if observed is None:
            drop(ExclusionReason.NO_VOLUME_EVIDENCE, "no ticker evidence for symbol")
            continue
        if observed.quote_volume < config.min_quote_volume:
            drop(
                ExclusionReason.BELOW_VOLUME_FLOOR,
                f"{observed.window} quote volume {observed.quote_volume:.2f} < "
                f"{config.min_quote_volume:.2f}",
            )
            continue
        candidates.append((spot, observed))

    ranked = rank_symbols(candidates)
    if config.top_n is not None:
        # Truncation is a decision, not a disappearance: everything below the cut is
        # recorded with its rank so the audit accounts for every discovered symbol.
        for cut in ranked[config.top_n:]:
            excluded.append(Exclusion(
                symbol=cut.symbol, base_asset=cut.base_asset, quote_asset=cut.quote_asset,
                reason=ExclusionReason.BELOW_TOP_N,
                detail=f"rank {cut.rank} is below top_n={config.top_n}",
            ))
        ranked = ranked[: config.top_n]
    return SelectionResult(
        ranked=ranked,
        excluded=sorted(excluded, key=lambda item: (item.reason.value, item.symbol)),
        config=config,
    )


# ---------------------------------------------------------------------------
# History eligibility
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HistoryEligibility:
    """Whether a selected symbol has enough observed history to be research usable."""

    symbol: str
    eligible: bool
    first_bar_open_time: datetime | None
    history_days: int | None
    reason: DeferralReason | None
    raw_object_id: str | None

    @property
    def observation_failed(self) -> bool:
        """True when eligibility is unknown because the request failed."""
        return self.reason is DeferralReason.HISTORY_REQUEST_FAILED

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "eligible": self.eligible,
            "first_bar_open_time": (
                None if self.first_bar_open_time is None else self.first_bar_open_time.isoformat()
            ),
            "history_days": self.history_days,
            "reason": None if self.reason is None else self.reason.value,
            "raw_object_id": self.raw_object_id,
        }


def parse_first_kline_open_time(payload: Any, *, as_of: datetime | None = None) -> datetime | None:
    """Earliest available bar open time, or None when the symbol has no history.

    Raises for any malformed successful response. Provider success does not make its
    contents trustworthy: a fractional, non-aligned, non-finite or future open time is
    corrupt evidence, and treating it as a fact produced negative history that was
    then persisted as a terminal deferral.
    """
    if not isinstance(payload, list):
        raise BinanceUniverseError("klines response must be a list")
    if not payload:
        return None
    first = payload[0]
    if not isinstance(first, Sequence) or isinstance(first, (str, bytes)) or not first:
        raise BinanceUniverseError("kline entry must be a non-empty sequence")
    open_ms = _whole_milliseconds(first[0])
    if open_ms is None:
        raise BinanceUniverseError(f"kline open time must be whole milliseconds, got {first[0]!r}")
    if open_ms < 0:
        raise BinanceUniverseError(f"kline open time must not be negative, got {open_ms}")
    if open_ms % 86_400_000:
        raise BinanceUniverseError(f"kline open time {open_ms} is not UTC-day aligned")
    # A whole, aligned, non-negative millisecond count can still be far outside the
    # representable datetime range. Conversion must fail as typed evidence, not as a
    # bare OverflowError/OSError/ValueError escaping the HISTORY_REQUEST_FAILED path.
    try:
        moment = datetime.fromtimestamp(open_ms / 1000, UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise BinanceUniverseError(
            f"kline open time {open_ms} is not a representable timestamp"
        ) from exc
    if as_of is not None and moment > as_of:
        raise BinanceUniverseError(
            f"earliest bar {moment.isoformat()} is after the pinned {as_of.isoformat()}"
        )
    return moment


def evaluate_history(
    *,
    symbol: str,
    first_open_time: datetime | None,
    as_of: datetime,
    min_history_days: int,
    raw_object_id: str | None,
) -> HistoryEligibility:
    """Classify a symbol's history. Short history is deferred, never silently admitted."""
    if first_open_time is None:
        return HistoryEligibility(
            symbol=symbol, eligible=False, first_bar_open_time=None, history_days=None,
            reason=DeferralReason.NO_HISTORY, raw_object_id=raw_object_id,
        )
    days = (as_of - first_open_time) // timedelta(days=1)
    eligible = days >= min_history_days
    return HistoryEligibility(
        symbol=symbol,
        eligible=eligible,
        first_bar_open_time=first_open_time,
        history_days=int(days),
        reason=None if eligible else DeferralReason.INSUFFICIENT_HISTORY,
        raw_object_id=raw_object_id,
    )


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

class BinanceUniverseAcquirer:
    """Fetches the three evidence sources, preserving every response before decoding."""

    def __init__(self, *, acquirer: RawHttpAcquirer, base_url: str = BINANCE_BASE_URL) -> None:
        self._acquirer = acquirer
        self._base_url = base_url.rstrip("/")

    @property
    def log(self) -> AcquisitionLog:
        return self._acquirer.log

    def fetch_exchange_info(self) -> tuple[list[SpotSymbol], AcquisitionOutcome]:
        outcome = self._acquirer.get_json(
            provider="binance", url=f"{self._base_url}/api/v3/exchangeInfo",
            source_id=EXCHANGE_INFO_SOURCE_ID, original_name="binance_exchange_info.json",
        )
        if not outcome.ok:
            raise BinanceUniverseError(
                "exchangeInfo acquisition failed",
                context={"failure": outcome.failure_kind, "detail": outcome.detail},
            )
        return parse_exchange_info(
            outcome.payload, raw_object_id=str(outcome.raw_object_id)
        ), outcome

    def fetch_volume_evidence(self) -> tuple[dict[str, VolumeEvidence], AcquisitionOutcome]:
        outcome = self._acquirer.get_json(
            provider="binance", url=f"{self._base_url}/api/v3/ticker/24hr",
            source_id=TICKER_SOURCE_ID, original_name="binance_ticker_24hr.json",
        )
        if not outcome.ok:
            raise BinanceUniverseError(
                "ticker/24hr acquisition failed",
                context={"failure": outcome.failure_kind, "detail": outcome.detail},
            )
        return parse_ticker_evidence(
            outcome.payload, observed_at=outcome.acquired_at,
            raw_object_id=str(outcome.raw_object_id),
        ), outcome

    def fetch_trailing_volume(
        self, symbol: str, *, end_time: datetime, days: int = RANKING_DAYS
    ) -> VolumeMeasurement:
        """Measured trailing N-day quote volume, or None when the window is incomplete.

        Binance exposes no 30-day volume field, so the ticket's measure is summed from
        daily bars. The window must be exactly N unique, contiguous, closed daily bars
        ending at the pinned time; anything else is not a 30-day observation and is
        reported as such rather than labelled one.
        """
        start = end_time - timedelta(days=days - 1)
        outcome = self._acquirer.get_json(
            provider="binance", url=f"{self._base_url}/api/v3/klines",
            params={
                "symbol": symbol, "interval": "1d",
                "startTime": int(start.timestamp() * 1000),
                "endTime": int(end_time.timestamp() * 1000), "limit": days,
            },
            source_id=KLINES_SOURCE_ID, original_name=f"binance_vol{days}_{symbol}.json",
        )
        if not outcome.ok:
            return VolumeMeasurement(
                symbol=symbol, status=MeasurementStatus.FAILED, evidence=None,
                reason=f"{outcome.failure_kind}: {outcome.detail}",
            )
        if not isinstance(outcome.payload, list):
            return VolumeMeasurement(
                symbol=symbol, status=MeasurementStatus.FAILED, evidence=None,
                reason="klines response is not a list",
            )

        day_ms = 86_400_000
        acquired_ms = int(outcome.acquired_at.timestamp() * 1000)
        expected = [int(start.timestamp() * 1000) + i * day_ms for i in range(days)]
        seen: dict[int, float] = {}
        trades_seen: dict[int, int] = {}

        def failed(reason: str) -> VolumeMeasurement:
            return VolumeMeasurement(
                symbol=symbol, status=MeasurementStatus.FAILED, evidence=None, reason=reason
            )

        for row in outcome.payload:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) < 9:
                return failed("malformed kline row")
            open_raw, close_raw = row[0], row[6]
            open_ms = _whole_milliseconds(open_raw)
            close_ms = _whole_milliseconds(close_raw)
            if open_ms is None or close_ms is None:
                # Non-finite or fractional timestamps previously escaped through int()
                # as an untyped exception.
                return failed("malformed kline timestamps")
            if open_ms % day_ms:
                return failed("kline open time is not day-aligned")
            if close_ms != open_ms + day_ms - 1:
                # Structurally wrong, not merely unobserved: this is failed evidence,
                # not an incomplete window, and must block rather than silently drop
                # the symbol out of the ranking.
                return failed("kline close interval is invalid")
            if close_ms >= acquired_ms:
                return VolumeMeasurement(
                    symbol=symbol, status=MeasurementStatus.INCOMPLETE_WINDOW,
                    evidence=None, reason="window contains a bar that had not closed",
                )
            value = _finite(row[7])
            if value is None or value < 0 or open_ms in seen:
                return failed("malformed or duplicated kline volume")
            trades = _whole_milliseconds(row[8])
            if trades is None or trades < 0:
                return failed("malformed kline trade count")
            seen[open_ms] = value
            trades_seen[open_ms] = trades

        # Exactly the pinned window: no holes, no partial trailing bar, no extras.
        if sorted(seen) != expected:
            return VolumeMeasurement(
                symbol=symbol, status=MeasurementStatus.INCOMPLETE_WINDOW, evidence=None,
                reason=f"no complete {days}-day closed-bar window at the pinned end",
            )
        return VolumeMeasurement(
            symbol=symbol, status=MeasurementStatus.OK, reason="complete window",
            evidence=VolumeEvidence(
                # Actual aggregated per-kline trades. Previously len(seen), which made
                # every complete window claim exactly `days` trades.
                symbol=symbol, quote_volume=sum(seen.values()),
                trade_count=sum(trades_seen.values()),
                window=f"{days}d", observed_at=outcome.acquired_at,
                raw_object_id=str(outcome.raw_object_id),
            ),
        )

    def fetch_history_eligibility(
        self, symbol: str, *, as_of: datetime, min_history_days: int
    ) -> HistoryEligibility:
        """One request per symbol for its earliest bar; a failure defers, never admits."""
        outcome = self._acquirer.get_json(
            provider="binance", url=f"{self._base_url}/api/v3/klines",
            params={"symbol": symbol, "interval": "1d", "startTime": 0, "limit": 1},
            source_id=KLINES_SOURCE_ID, original_name=f"binance_klines_{symbol}.json",
        )
        if not outcome.ok:
            # We could not observe the symbol. That is our failure, not a fact about
            # the asset, so it must stay pending rather than be recorded as deferred.
            return HistoryEligibility(
                symbol=symbol, eligible=False, first_bar_open_time=None, history_days=None,
                reason=DeferralReason.HISTORY_REQUEST_FAILED,
                raw_object_id=outcome.raw_object_id,
            )
        try:
            first_open = parse_first_kline_open_time(outcome.payload, as_of=as_of)
        except BinanceUniverseError:
            return HistoryEligibility(
                symbol=symbol, eligible=False, first_bar_open_time=None, history_days=None,
                reason=DeferralReason.HISTORY_REQUEST_FAILED,
                raw_object_id=outcome.raw_object_id,
            )
        return evaluate_history(
            symbol=symbol, first_open_time=first_open, as_of=as_of,
            min_history_days=min_history_days, raw_object_id=outcome.raw_object_id,
        )


__all__ = [
    "BINANCE_BASE_URL",
    "DEFAULT_MIN_HISTORY_DAYS",
    "DEFAULT_MIN_QUOTE_VOLUME",
    "EXCLUSION_TAXONOMY_VERSION",
    "FIAT_BASES",
    "LEVERAGED_SUFFIXES",
    "STABLECOIN_BASES",
    "TOKENIZED_COMMODITY_BASES",
    "VOLUME_WINDOW",
    "BinanceUniverseAcquirer",
    "BinanceUniverseError",
    "DeferralReason",
    "Exclusion",
    "ExclusionReason",
    "HistoryEligibility",
    "RankedSymbol",
    "SelectionConfig",
    "SelectionResult",
    "SpotSymbol",
    "MeasurementStatus",
    "VolumeEvidence",
    "VolumeMeasurement",
    "classify_base_asset",
    "BASE_PANEL_DATASET_ID",
    "load_base_panel_symbols",
    "evaluate_history",
    "filter_non_volume_taxonomy",
    "is_leveraged_token",
    "parse_exchange_info",
    "parse_first_kline_open_time",
    "parse_ticker_evidence",
    "rank_symbols",
    "select_symbols",
]
