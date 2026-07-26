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
#: only comparable when they were produced under the same rules.
EXCLUSION_TAXONOMY_VERSION = "2026-07-26.1"

#: The volume evidence this ticket ranks on. Named for what it actually is: the
#: 24-hour rolling window from /api/v3/ticker/24hr. It is *not* 30-day volume, and
#: describing it as such was the previous implementation's central misstatement.
VOLUME_WINDOW = "24h"

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
    ALREADY_COVERED = "ALREADY_COVERED"


class DeferralReason(str, Enum):
    """Why an otherwise-selectable symbol is not yet research-ready."""

    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    HISTORY_UNKNOWN = "HISTORY_UNKNOWN"


#: Non-target base assets. Membership is data, not code, so the taxonomy version
#: above is what makes two runs comparable.
STABLECOIN_BASES = frozenset({
    "USDT", "USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "UST", "USTC",
    "PAX", "SUSD", "GUSD", "LUSD", "PYUSD", "EURI", "AEUR", "USD1",
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
    payload: Any, *, observed_at: datetime, raw_object_id: str, window: str = VOLUME_WINDOW
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "quote_assets": list(self.quote_assets),
            "min_quote_volume": self.min_quote_volume,
            "min_history_days": self.min_history_days,
            "top_n": self.top_n,
            "volume_window": VOLUME_WINDOW,
            "taxonomy_version": EXCLUSION_TAXONOMY_VERSION,
        }

    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict()).encode()).hexdigest()


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


def parse_first_kline_open_time(payload: Any) -> datetime | None:
    """Earliest available bar open time, or None when the symbol has no history."""
    if not isinstance(payload, list):
        raise BinanceUniverseError("klines response must be a list")
    if not payload:
        return None
    first = payload[0]
    if not isinstance(first, Sequence) or isinstance(first, (str, bytes)) or not first:
        raise BinanceUniverseError("kline entry must be a non-empty sequence")
    open_time = first[0]
    if isinstance(open_time, bool) or not isinstance(open_time, (int, float)):
        raise BinanceUniverseError(f"kline open time must be numeric, got {open_time!r}")
    return datetime.fromtimestamp(int(open_time) / 1000, UTC)


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
            reason=DeferralReason.HISTORY_UNKNOWN, raw_object_id=raw_object_id,
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
            return HistoryEligibility(
                symbol=symbol, eligible=False, first_bar_open_time=None, history_days=None,
                reason=DeferralReason.HISTORY_UNKNOWN, raw_object_id=outcome.raw_object_id,
            )
        try:
            first_open = parse_first_kline_open_time(outcome.payload)
        except BinanceUniverseError:
            return HistoryEligibility(
                symbol=symbol, eligible=False, first_bar_open_time=None, history_days=None,
                reason=DeferralReason.HISTORY_UNKNOWN, raw_object_id=outcome.raw_object_id,
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
    "VolumeEvidence",
    "classify_base_asset",
    "evaluate_history",
    "is_leveraged_token",
    "parse_exchange_info",
    "parse_first_kline_open_time",
    "parse_ticker_evidence",
    "rank_symbols",
    "select_symbols",
]
