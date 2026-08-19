"""CEX-002 Gate 1 — free-source qualification for Binance USD-M harmonic data.

Closes the fifteen review-61 defects: header/headerless schema identity, rehashed
resume, a real Coinalyze history client, ListObjectsV2 pagination, explicit 1m
selection, checksum-required completeness, no quote-label authority, source-gate
treatment of derived outputs, bookDepth+bookTicker cost inventory, authenticated
current-contract comparison, and a non-zero default exit on incomplete coverage.

Closes the review-64 residuals: coverage is accounted against the full discovered
universe including symbols with no family prefix, and Coinalyze provenance is taken
from retained raw response bytes rather than a re-serialised parse.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import re
import time
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode, urlparse, urlunparse
from xml.etree import ElementTree

from source_audit.download import (
    HttpTransport,
    TimeoutConfig,
    atomic_download,
    content_addressed_path,
)
from source_audit.errors import ChecksumMismatchError, DownloadError, SizeLimitError
from source_audit.hashing import compute_sha256

TICKET_ID: str = "CEX-002"
VISION_S3_ENDPOINT: str = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
VISION_OBJECT_BASE: str = "https://data.binance.vision"
VISION_PREFIX: str = "data/futures/um"
FAPI_BASE: str = "https://fapi.binance.com"
COINALYZE_BASE: str = "https://api.coinalyze.net/v1"
COINALYZE_EXCHANGE_CODE: str = "A"
COINALYZE_INTERVAL_DAILY: str = "daily"
BINANCE_CENSORSHIP_NOTE: str = (
    "Binance force-order publication after 2021-04-27 is latest-per-symbol-per-second; "
    "this product is observed/censored, never event-complete"
)
COINALYZE_DAILY_RETENTION: str = (
    "official Coinalyze policy: intraday keeps 1500-2000 points and deletes older; "
    "daily observations are not deleted"
)

OFFICIAL_INCREMENTAL_ENDPOINTS: dict[str, str] = {
    "exchangeInfo": f"{FAPI_BASE}/fapi/v1/exchangeInfo",
    "fundingRate": f"{FAPI_BASE}/fapi/v1/fundingRate",
    "openInterest": f"{FAPI_BASE}/fapi/v1/openInterest",
    "openInterestHist": f"{FAPI_BASE}/futures/data/openInterestHist",
    "forceOrders": f"{FAPI_BASE}/fapi/v1/allForceOrders",
    "premiumIndex": f"{FAPI_BASE}/fapi/v1/premiumIndex",
    "commissionRate": f"{FAPI_BASE}/fapi/v1/commissionRate",
}

COINALYZE_HISTORY_ENDPOINTS: dict[str, str] = {
    "future_markets": "/future-markets",
    "liquidation": "/liquidation-history",
    "open_interest": "/open-interest-history",
    "funding": "/funding-rate-history",
    "ohlcv": "/ohlcv-history",
}

REQUIRED_PRODUCTS: tuple[str, ...] = (
    "binance_usdm_perpetual_membership",
    "binance_usdm_trade",
    "binance_usdm_bar_1m",
    "binance_usdm_trade_flow",
    "binance_usdm_open_interest_5m",
    "binance_usdm_funding_realized",
    "binance_usdm_funding_indicative",
    "binance_usdm_mark_index_basis",
    "binance_usdm_liquidation_observed",
    "binance_usdm_cost_calibration",
    "binance_usdm_coverage_gap",
    "binance_usdm_harmonic_bundle",
)

DERIVED_PRODUCTS: frozenset[str] = frozenset(
    {
        "binance_usdm_trade_flow",
        "binance_usdm_coverage_gap",
        "binance_usdm_harmonic_bundle",
    }
)

SOURCE_PRODUCTS: tuple[str, ...] = tuple(
    product for product in REQUIRED_PRODUCTS if product not in DERIVED_PRODUCTS
)

# Explicit 1m selection for named one-minute families. Other intervals are ignored.
INTERVAL_REQUIRED_FAMILIES: dict[str, str] = {
    "monthly/klines": "1m",
    "daily/klines": "1m",
    "monthly/markPriceKlines": "1m",
    "daily/markPriceKlines": "1m",
    "monthly/indexPriceKlines": "1m",
    "daily/indexPriceKlines": "1m",
    "monthly/premiumIndexKlines": "1m",
    "daily/premiumIndexKlines": "1m",
}

OFFICIAL_ARCHIVE_FAMILIES: dict[str, tuple[str, ...]] = {
    "binance_usdm_perpetual_membership": (
        "monthly/trades",
        "daily/trades",
        "monthly/klines",
        "daily/klines",
        "monthly/metrics",
        "daily/metrics",
        "monthly/fundingRate",
        "daily/fundingRate",
        "monthly/markPriceKlines",
        "daily/markPriceKlines",
        "monthly/indexPriceKlines",
        "daily/indexPriceKlines",
        "monthly/premiumIndexKlines",
        "daily/premiumIndexKlines",
        "monthly/bookTicker",
        "daily/bookTicker",
        "monthly/bookDepth",
        "daily/bookDepth",
    ),
    "binance_usdm_trade": (
        "monthly/trades",
        "daily/trades",
        "monthly/aggTrades",
        "daily/aggTrades",
    ),
    "binance_usdm_bar_1m": ("monthly/klines", "daily/klines"),
    "binance_usdm_open_interest_5m": ("monthly/metrics", "daily/metrics"),
    "binance_usdm_funding_realized": ("monthly/fundingRate", "daily/fundingRate"),
    "binance_usdm_funding_indicative": (
        "monthly/premiumIndexKlines",
        "daily/premiumIndexKlines",
    ),
    "binance_usdm_mark_index_basis": (
        "monthly/markPriceKlines",
        "daily/markPriceKlines",
        "monthly/indexPriceKlines",
        "daily/indexPriceKlines",
        "monthly/premiumIndexKlines",
        "daily/premiumIndexKlines",
    ),
    "binance_usdm_cost_calibration": (
        "monthly/bookTicker",
        "daily/bookTicker",
        "monthly/bookDepth",
        "daily/bookDepth",
    ),
}

MEMBERSHIP_FAMILY_PREFIXES: tuple[str, ...] = tuple(
    sorted({family for families in OFFICIAL_ARCHIVE_FAMILIES.values() for family in families})
)

KNOWN_ARCHIVE_SCHEMAS: dict[str, dict[str, tuple[str, ...]]] = {
    "trades": {
        "headed": ("id", "price", "qty", "quote_qty", "time", "is_buyer_maker"),
        "headerless": ("id", "price", "qty", "quote_qty", "time", "is_buyer_maker"),
    },
    "aggTrades": {
        "headed": (
            "agg_trade_id",
            "price",
            "quantity",
            "first_trade_id",
            "last_trade_id",
            "transact_time",
            "is_buyer_maker",
        ),
        "headerless": (
            "agg_trade_id",
            "price",
            "quantity",
            "first_trade_id",
            "last_trade_id",
            "transact_time",
            "is_buyer_maker",
        ),
    },
    "klines": {
        "headed": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "headerless": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
    },
    "fundingRate": {
        "headed": ("calc_time", "funding_interval_hours", "last_funding_rate"),
        "headerless": ("calc_time", "funding_interval_hours", "last_funding_rate"),
    },
    "metrics": {
        "headed": (
            "create_time",
            "symbol",
            "sum_open_interest",
            "sum_open_interest_value",
            "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio",
            "count_long_short_ratio",
            "sum_taker_long_short_vol_ratio",
        ),
        "headerless": (
            "create_time",
            "symbol",
            "sum_open_interest",
            "sum_open_interest_value",
            "count_toptrader_long_short_ratio",
            "sum_toptrader_long_short_ratio",
            "count_long_short_ratio",
            "sum_taker_long_short_vol_ratio",
        ),
    },
    "bookTicker": {
        "headed": (
            "update_id",
            "best_bid_price",
            "best_bid_qty",
            "best_ask_price",
            "best_ask_qty",
            "transaction_time",
            "event_time",
        ),
        "headerless": (
            "update_id",
            "best_bid_price",
            "best_bid_qty",
            "best_ask_price",
            "best_ask_qty",
            "transaction_time",
            "event_time",
        ),
    },
    "bookDepth": {
        "headed": ("timestamp", "percentage", "depth", "notional"),
        "headerless": ("timestamp", "percentage", "depth", "notional"),
    },
    "markPriceKlines": {
        "headed": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "headerless": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
    },
    "indexPriceKlines": {
        "headed": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "headerless": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
    },
    "premiumIndexKlines": {
        "headed": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
        "headerless": (
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_volume",
            "taker_buy_quote_volume",
            "ignore",
        ),
    },
}

OVERLAP_RECONCILIATION: dict[str, Any] = {
    "required_before_accepting_liquidation": True,
    "fields": {
        "price": {
            "coinalyze": "ohlcv-history.history.c",
            "official": "klines.close or markPriceKlines.close",
        },
        "open_interest": {
            "coinalyze": "open-interest-history.history.c",
            "official": "metrics.sum_open_interest",
        },
        "funding": {
            "coinalyze": "funding-rate-history.history.c",
            "official": "fundingRate.last_funding_rate",
        },
    },
}

# Gate 1 is bounded source qualification, not acquisition. These are execution budgets
# for NEW downloads only; they never truncate, reject, or miscount larger source objects,
# which Gate 2 acquires in full.
GATE1_NEW_DOWNLOAD_BUDGET_BYTES: int = 268_435_456
GATE1_MAX_NEW_OBJECT_BYTES: int = 67_108_864
SAMPLE_BUDGET_BLOCK: str = "sample_budget_exceeded"
CHECKPOINT_VERSION: int = 1

# Transient transport/service failures are retried; integrity and authentication
# failures are terminal and must never be retried.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504, 509})
TERMINAL_STATUS_CODES: frozenset[int] = frozenset({400, 401, 403, 404, 405, 410})

HISTORICAL_PERPETUAL_RULE: str = (
    "Archive directory names are the historical observation set, not a contract-type "
    "proof. Authenticated current PERPETUAL membership comes only from FAPI "
    "exchangeInfo.contractType=PERPETUAL. Archive names absent from that set are "
    "historical_or_delisted_candidates. Current PERPETUAL names absent from archives "
    "are current_unarchived. No archive name is asserted PERPETUAL from spelling."
)

_SYMBOL_DIR_RE = re.compile(r"^[A-Z0-9_]+$")
_BOOL_TOKENS = frozenset({"true", "false"})
_SECRET_PARAM_KEYS = frozenset(
    {"api_key", "apikey", "key", "token", "secret", "password", "access_token"}
)
_IDENTITY_DROP_KEYS = frozenset(
    {
        "generated_at",
        "retrieval_time",
        "content_path",
        "sample_store",
        "progress_path",
        "reused_samples",
        "reused_existing",
        "retrieved_at",
        # Execution-plane volatility: how the run was executed must never change the
        # semantic identity of what was qualified.
        "sample_plan",
        "sample_plan_path",
        "retry",
        "retry_journal_path",
        "listing_checkpoint",
        "recovered_samples",
    }
)


class SourceAuthority(str, Enum):
    OFFICIAL = "official"
    SECONDARY = "secondary"
    SAMPLE_ONLY = "sample_only"
    INACCESSIBLE = "inaccessible"
    UNSUPPORTED = "unsupported"


class GateStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    BLOCKED = "BLOCKED"


class SourceQualificationError(RuntimeError):
    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class ResumeIntegrityError(SourceQualificationError):
    """Content-addressed resume bytes do not match the recorded digest."""


@dataclass(frozen=True, slots=True)
class ListingObject:
    key: str
    size: int | None = None
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaIdentity:
    kind: str
    fields: tuple[str, ...]
    family_hint: str


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded exponential backoff with jitter for transient transport failures."""

    max_attempts: int = 5
    base_delay_s: float = 0.5
    max_delay_s: float = 30.0
    jitter_ratio: float = 0.25

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_s <= 0 or self.max_delay_s <= 0:
            raise ValueError("retry delays must be positive")
        if not 0.0 <= self.jitter_ratio < 1.0:
            raise ValueError("jitter_ratio must be in [0, 1)")

    def backoff_delay(self, attempt: int) -> float:
        """Un-jittered delay before retry ``attempt`` (1-based)."""
        return min(self.base_delay_s * (2 ** (attempt - 1)), self.max_delay_s)


def failure_status_code(exc: BaseException) -> int | None:
    context = getattr(exc, "context", None)
    if isinstance(context, Mapping):
        status = context.get("status_code")
        if isinstance(status, int):
            return status
    return None


def is_retryable_failure(exc: BaseException) -> bool:
    """True only for transient transport/service failures.

    Integrity failures (checksum, size limit, schema) and authentication or
    not-found responses are terminal and fail immediately.
    """
    if isinstance(exc, (ChecksumMismatchError, SizeLimitError, ResumeIntegrityError)):
        return False
    if isinstance(exc, SourceQualificationError):
        return False
    if not isinstance(exc, DownloadError):
        return False
    status = failure_status_code(exc)
    if status is None:
        # Connect reset/timeout and other transport failures carry no HTTP status.
        return True
    if status in RETRYABLE_STATUS_CODES:
        return True
    if status in TERMINAL_STATUS_CODES:
        return False
    return 500 <= status < 600


def redact_retry_label(label: str) -> str:
    """Retry labels are journalled, so drop any query string before persisting."""
    return label.split("?", 1)[0]


@dataclass
class RetryRunner:
    """Runs a callable under a bounded retry policy and records incident counts.

    Exactly one runner owns the attempt budget for a given remote request; runners are
    never nested, so the nominal per-request bound cannot multiply. ``sleeper`` and
    ``jitter`` are injectable so tests are deterministic and never actually sleep.
    """

    policy: RetryPolicy = field(default_factory=RetryPolicy)
    sleeper: Callable[[float], None] = time.sleep
    jitter: Callable[[float], float] | None = None
    journal: RetryJournal | None = None
    attempts: int = 0
    retries: int = 0
    incidents: list[dict[str, Any]] = field(default_factory=list)

    def _jittered(self, delay: float) -> float:
        if self.jitter is not None:
            return self.jitter(delay)
        span = delay * self.policy.jitter_ratio
        return max(0.0, random.uniform(delay - span, delay + span))

    def run(self, label: str, call: Callable[[], Any]) -> Any:
        last: BaseException | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            self.attempts += 1
            try:
                return call()
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                if not is_retryable_failure(exc):
                    raise
                last = exc
                incident = {
                    "label": redact_retry_label(label),
                    "attempt": attempt,
                    "status_code": failure_status_code(exc),
                    "error": type(exc).__name__,
                    "retryable": True,
                }
                self.incidents.append(incident)
                # Persist as it happens: an aborted run must not erase retry evidence.
                if self.journal is not None:
                    self.journal.append(incident)
                if attempt >= self.policy.max_attempts:
                    break
                self.retries += 1
                self.sleeper(self._jittered(self.policy.backoff_delay(attempt)))
        raise SourceQualificationError(
            "retryable request failed after the bounded attempt limit",
            context={
                "label": label,
                "attempts": self.policy.max_attempts,
                "last_error": str(last),
            },
        ) from last

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_attempts": self.policy.max_attempts,
            "base_delay_s": self.policy.base_delay_s,
            "max_delay_s": self.policy.max_delay_s,
            "jitter_ratio": self.policy.jitter_ratio,
            "attempts": self.attempts,
            "retries": self.retries,
            "incidents": list(self.incidents),
            "journal_path": None if self.journal is None else str(self.journal.path),
        }


class ObjectIndex(Protocol):
    def list_common_prefixes(self, prefix: str) -> list[str]: ...

    def list_objects(self, prefix: str) -> list[ListingObject]: ...

    def fetch_bytes(self, url: str) -> bytes: ...


class CurrentContractSource(Protocol):
    def fetch_exchange_info(self) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class CoinalyzeResponse:
    """One Coinalyze fetch with its retained raw response bytes and identity.

    Provenance is taken from these retained bytes, never from a re-serialised
    parse of the payload.
    """

    path: str
    payload: Any
    raw_bytes: bytes
    sha256: str
    byte_size: int
    retrieved_at: str
    request_params: Mapping[str, str]
    header_names: tuple[str, ...]
    source: str
    content_path: str | None = None
    status_code: int | None = None


def redact_request_params(params: Mapping[str, str]) -> dict[str, str]:
    """Request metadata for provenance with any secret-shaped value redacted."""
    return {
        str(key): ("<redacted>" if str(key).lower() in _SECRET_PARAM_KEYS else str(value))
        for key, value in sorted(params.items())
    }


class CoinalyzeTransport(Protocol):
    def fetch(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> CoinalyzeResponse: ...


@dataclass
class MemoryObjectIndex:
    prefixes: dict[str, list[str]] = field(default_factory=dict)
    objects: dict[str, list[ListingObject]] = field(default_factory=dict)
    bodies: dict[str, bytes] = field(default_factory=dict)

    def list_common_prefixes(self, prefix: str) -> list[str]:
        return sorted(self.prefixes.get(prefix, []))

    def list_objects(self, prefix: str) -> list[ListingObject]:
        return sorted(self.objects.get(prefix, []), key=lambda item: item.key)

    def fetch_bytes(self, url: str) -> bytes:
        if url not in self.bodies:
            raise SourceQualificationError(
                "memory index has no body for url",
                context={"url": url},
            )
        return self.bodies[url]


@dataclass
class MemoryCurrentContractSource:
    payload: Mapping[str, Any]

    def fetch_exchange_info(self) -> Mapping[str, Any]:
        return dict(self.payload)


@dataclass
class MemoryCoinalyzeTransport:
    """Fixture transport holding raw response bytes, not parsed objects.

    It reports the same raw-byte provenance contract as the production transport,
    so a fixture hash is comparable with the retained response object.
    """

    raw_payloads: dict[str, bytes]
    retrieved_at: str = "1970-01-01T00:00:00+00:00"
    last_headers: dict[str, str] = field(default_factory=dict)
    last_params: dict[str, str] = field(default_factory=dict)
    last_path: str = ""

    @classmethod
    def from_files(cls, files: Mapping[str, Path]) -> MemoryCoinalyzeTransport:
        return cls(raw_payloads={path: Path(src).read_bytes() for path, src in files.items()})

    def fetch(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> CoinalyzeResponse:
        if "api_key" in params or "apikey" in {key.lower() for key in params}:
            raise SourceQualificationError(
                "Coinalyze API key must not appear in query parameters",
                context={"path": path},
            )
        self.last_path = path
        self.last_params = dict(params)
        self.last_headers = dict(headers)
        if path not in self.raw_payloads:
            raise SourceQualificationError(
                "memory Coinalyze transport has no payload",
                context={"path": path},
            )
        raw = self.raw_payloads[path]
        return CoinalyzeResponse(
            path=path,
            payload=json.loads(raw.decode("utf-8")),
            raw_bytes=raw,
            sha256=_object_sha256(raw),
            byte_size=len(raw),
            retrieved_at=self.retrieved_at,
            request_params=redact_request_params(params),
            header_names=tuple(sorted(headers)),
            source="memory_raw_bytes",
        )


@dataclass(frozen=True, slots=True)
class SampleRecord:
    product: str
    products: tuple[str, ...]
    family: str
    symbol: str
    regime: str
    url: str
    key: str
    sha256: str
    byte_size: int
    reused_existing: bool
    provider_checksum: str
    checksum_match: bool
    schema_kind: str
    schema_fields: tuple[str, ...]
    availability_semantics: str
    retrieval_time: str
    content_path: str


@dataclass(frozen=True, slots=True)
class ProductMatrixRow:
    product: str
    authority: str
    official_complete: bool
    source_gate: bool
    sample_only: bool
    reason: str
    official_families: tuple[str, ...]
    discovered_symbols: int
    sample_count: int
    listed_object_count: int
    listed_bytes: int | None
    incidents: int
    uncovered_listed_symbols: tuple[str, ...]
    uncovered_universe_symbols: tuple[str, ...]
    universe_coverage_gaps: tuple[Mapping[str, Any], ...]
    sample_budget_blocked: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class QualificationReport:
    ticket: str
    gate: str
    gate_status: str
    generated_at: str
    universe_source: str
    historical_perpetual_rule: str
    discovered_symbols: tuple[str, ...]
    current_perpetual_symbols: tuple[str, ...]
    current_contracts_authenticated: bool
    historical_or_delisted_candidates: tuple[str, ...]
    current_unarchived: tuple[str, ...]
    product_matrix: tuple[ProductMatrixRow, ...]
    samples: tuple[SampleRecord, ...]
    blocked_products: tuple[str, ...]
    storage: Mapping[str, Any]
    licensing: Mapping[str, Any]
    incidents: tuple[Mapping[str, Any], ...]
    resume: Mapping[str, Any]
    sample_plan: Mapping[str, Any]
    retry: Mapping[str, Any]
    listing_checkpoint: Mapping[str, Any]
    coinalyze: Mapping[str, Any]
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["product_matrix"] = [asdict(row) for row in self.product_matrix]
        payload["samples"] = [asdict(sample) for sample in self.samples]
        return payload


def refuse_restricted_scope(
    *,
    max_symbols: int | None,
    current_listing_only: bool,
    symbol_allowlist: Sequence[str] | None,
) -> None:
    if max_symbols is not None:
        raise SourceQualificationError(
            "fixed-N scope is refused",
            context={"max_symbols": max_symbols},
        )
    if current_listing_only:
        raise SourceQualificationError(
            "current-listing scope is refused",
            context={"current_listing_only": True},
        )
    if symbol_allowlist is not None:
        raise SourceQualificationError(
            "hand-selected symbol map is refused",
            context={"symbol_allowlist": list(symbol_allowlist)},
        )


def vision_prefix(*parts: str) -> str:
    segs = [VISION_PREFIX, *[part.strip("/") for part in parts if part]]
    return "/".join(segs) + "/"


def vision_object_url(key: str) -> str:
    return f"{VISION_OBJECT_BASE}/{key.lstrip('/')}"


def coinalyze_perp_symbol(native: str) -> str:
    return f"{native.strip().upper()}_PERP.{COINALYZE_EXCHANGE_CODE}"


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _first_child(node: ElementTree.Element, local: str) -> ElementTree.Element | None:
    for child in list(node):
        if _local_tag(child.tag) == local:
            return child
    return None


def parse_s3_list_bucket(
    xml_text: str,
) -> tuple[list[str], list[ListingObject], bool, str | None]:
    """Parse ListObjectsV2. V1 NextMarker-only pages are refused."""
    root = ElementTree.fromstring(xml_text)
    truncated = False
    next_v2: str | None = None
    next_v1: str | None = None
    for node in root.iter():
        local = _local_tag(node.tag)
        if local == "IsTruncated" and (node.text or "").strip().lower() == "true":
            truncated = True
        if local == "NextContinuationToken" and node.text:
            next_v2 = str(node.text)
        if local == "NextMarker" and node.text:
            next_v1 = str(node.text)
    if truncated and next_v2 is None:
        raise SourceQualificationError(
            "truncated S3 listing is not ListObjectsV2; NextMarker cannot continue a V2 request",
            context={"next_marker": next_v1},
        )
    prefixes: list[str] = []
    objects: list[ListingObject] = []
    for node in list(root):
        local = _local_tag(node.tag)
        if local == "CommonPrefixes":
            prefix_el = _first_child(node, "Prefix")
            if prefix_el is not None and prefix_el.text:
                prefixes.append(str(prefix_el.text))
        elif local == "Contents":
            key_el = _first_child(node, "Key")
            if key_el is None or not key_el.text or str(key_el.text).endswith("/"):
                continue
            size_el = _first_child(node, "Size")
            etag_el = _first_child(node, "ETag")
            size = int(size_el.text) if size_el is not None and size_el.text else None
            etag = etag_el.text.strip().strip('"') if etag_el is not None and etag_el.text else None
            objects.append(ListingObject(key=str(key_el.text), size=size, etag=etag))
    return prefixes, objects, truncated, next_v2


def write_s3_list_bucket(
    *,
    prefixes: Sequence[str] = (),
    objects: Sequence[ListingObject] = (),
    truncated: bool = False,
    continuation: str | None = None,
    next_marker: str | None = None,
    prefix: str | None = None,
    delimiter: str | None = None,
    continuation_token: str | None = None,
) -> str:
    """Render a ListObjectsV2 response.

    ``prefix``/``delimiter``/``continuation_token`` echo the originating request the way
    S3 does, which is what makes a retained response self-identifying.
    """
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">',
    ]
    if prefix is not None:
        parts.append(f"<Prefix>{prefix}</Prefix>")
    if delimiter is not None:
        parts.append(f"<Delimiter>{delimiter}</Delimiter>")
    if continuation_token is not None:
        parts.append(f"<ContinuationToken>{continuation_token}</ContinuationToken>")
    parts.append(f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>")
    if continuation is not None:
        parts.append(f"<NextContinuationToken>{continuation}</NextContinuationToken>")
    if next_marker is not None:
        parts.append(f"<NextMarker>{next_marker}</NextMarker>")
    for prefix in prefixes:
        parts.append(f"<CommonPrefixes><Prefix>{prefix}</Prefix></CommonPrefixes>")
    for obj in objects:
        size = "" if obj.size is None else f"<Size>{obj.size}</Size>"
        etag = "" if obj.etag is None else f"<ETag>&quot;{obj.etag}&quot;</ETag>"
        parts.append(f"<Contents><Key>{obj.key}</Key>{size}{etag}</Contents>")
    parts.append("</ListBucketResult>")
    return "".join(parts)


def parse_provider_checksum(text: str) -> str | None:
    token = text.strip().split()[0] if text.strip() else ""
    digest = token.lower()
    if len(digest) == 64 and all(char in "0123456789abcdef" for char in digest):
        return digest
    return None


def _split_csv_line(line: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in line.strip().split(",") if part.strip() != "")


def _is_numeric_or_bool_token(token: str) -> bool:
    lowered = token.strip().lower()
    if lowered in _BOOL_TOKENS:
        return True
    try:
        float(token)
    except ValueError:
        return False
    return True


def _is_known_headerless_data_row(
    fields: Sequence[str],
    *,
    headerless: Sequence[str],
    headed: Sequence[str],
) -> bool:
    """True when the first row is data for a known headerless family schema."""
    if not headerless or len(fields) != len(headerless):
        return False
    if headed and tuple(fields) == tuple(headed):
        return False
    for value, column in zip(fields, headerless, strict=True):
        if column == "symbol":
            if not _SYMBOL_DIR_RE.fullmatch(str(value).strip().upper()):
                return False
            continue
        if not _is_numeric_or_bool_token(value):
            return False
    return True


def _family_hint_from_name(name: str) -> str:
    key = name.replace("\\", "/").lower()
    markers = (
        "aggtrades",
        "markpriceklines",
        "indexpriceklines",
        "premiumindexklines",
        "fundingrate",
        "bookticker",
        "bookdepth",
        "metrics",
        "klines",
        "trades",
    )
    canonical = {
        "aggtrades": "aggTrades",
        "markpriceklines": "markPriceKlines",
        "indexpriceklines": "indexPriceKlines",
        "premiumindexklines": "premiumIndexKlines",
        "fundingrate": "fundingRate",
        "bookticker": "bookTicker",
        "bookdepth": "bookDepth",
        "metrics": "metrics",
        "klines": "klines",
        "trades": "trades",
    }
    for marker in markers:
        if marker in key:
            return canonical[marker]
    return ""


def infer_schema_fields(payload: bytes, *, name: str) -> SchemaIdentity:
    """Identify headed vs headerless rows using known family schemas.

    A numeric/boolean first CSV row is never treated as field names.
    """
    hint = _family_hint_from_name(name)
    known = KNOWN_ARCHIVE_SCHEMAS.get(hint, {})
    first_line = ""
    if name.endswith(".CHECKSUM") or name.endswith(".checksum"):
        return SchemaIdentity(kind="checksum", fields=("sha256", "filename"), family_hint=hint)
    if len(payload) >= 2 and payload[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as handle:
                members = [info for info in handle.infolist() if not info.is_dir()]
                if not members:
                    raise SourceQualificationError(
                        "ZIP sample has no file members",
                        context={"name": name},
                    )
                with handle.open(members[0]) as member:
                    first_line = member.readline().decode("utf-8", errors="replace")
        except (OSError, zipfile.BadZipFile, UnicodeError) as exc:
            raise SourceQualificationError(
                "ZIP sample is unreadable",
                context={"name": name, "error": str(exc)},
            ) from exc
    else:
        text = payload[:8192].decode("utf-8", errors="replace")
        stripped = text.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SourceQualificationError(
                    "JSON sample is unreadable",
                    context={"name": name},
                ) from exc
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return SchemaIdentity(
                    kind="json_object",
                    fields=tuple(str(key) for key in data[0].keys()),
                    family_hint=hint,
                )
            if isinstance(data, dict):
                return SchemaIdentity(
                    kind="json_object",
                    fields=tuple(str(key) for key in data.keys()),
                    family_hint=hint,
                )
        first_line = text.splitlines()[0] if text.splitlines() else ""
    fields = _split_csv_line(first_line)
    headed = known.get("headed", ())
    headerless = known.get("headerless", ())
    if headed and fields == headed:
        return SchemaIdentity(kind="headed", fields=fields, family_hint=hint)
    if _is_known_headerless_data_row(fields, headerless=headerless, headed=headed):
        return SchemaIdentity(kind="headerless", fields=headerless, family_hint=hint)
    raise SourceQualificationError(
        "sample first row is not the known family header and is not known headerless data",
        context={"name": name, "first_row": list(fields), "family_hint": hint},
    )


def symbols_from_prefixes(prefixes: Sequence[str]) -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for prefix in prefixes:
        name = prefix.rstrip("/").rsplit("/", 1)[-1].upper()
        if not _SYMBOL_DIR_RE.fullmatch(name):
            continue
        if name not in seen:
            seen.add(name)
            symbols.append(name)
    symbols.sort()
    return symbols


@dataclass(frozen=True, slots=True)
class FamilyInventory:
    """Complete listing of one physical archive family, traversed exactly once."""

    family: str
    prefix: str
    listed: bool
    symbols: tuple[str, ...]
    objects: Mapping[str, tuple[ListingObject, ...]]
    incidents: tuple[Mapping[str, Any], ...]

    def object_count(self, symbol: str) -> int:
        return len(self.objects.get(symbol, ()))


def build_family_inventory(
    index: ObjectIndex,
    *,
    families: Sequence[str] = MEMBERSHIP_FAMILY_PREFIXES,
) -> dict[str, FamilyInventory]:
    """Inventory every unique physical family once.

    Logical product rows are derived from this shared inventory, so the same physical
    prefix is never traversed again for a second product.
    """
    inventory: dict[str, FamilyInventory] = {}
    for family in families:
        prefix = vision_prefix(*family.split("/"))
        incidents: list[dict[str, Any]] = []
        try:
            prefix_list = index.list_common_prefixes(prefix)
        except SourceQualificationError as exc:
            inventory[family] = FamilyInventory(
                family=family,
                prefix=prefix,
                listed=False,
                symbols=(),
                objects={},
                incidents=(
                    {"family": family, "kind": "listing_error", "note": str(exc)},
                ),
            )
            continue
        symbols = symbols_from_prefixes(prefix_list)
        objects: dict[str, tuple[ListingObject, ...]] = {}
        for symbol in symbols:
            try:
                objs = [
                    obj
                    for obj in _list_objects_for_symbol(index, family, prefix, symbol)
                    if not obj.key.endswith(".CHECKSUM")
                ]
            except SourceQualificationError as exc:
                incidents.append(
                    {
                        "family": family,
                        "symbol": symbol,
                        "kind": "listing_error",
                        "note": str(exc),
                    }
                )
                continue
            objects[symbol] = tuple(objs)
        inventory[family] = FamilyInventory(
            family=family,
            prefix=prefix,
            listed=True,
            symbols=tuple(symbols),
            objects=objects,
            incidents=tuple(incidents),
        )
    return inventory


def inventory_symbols(inventory: Mapping[str, FamilyInventory]) -> list[str]:
    """Discovered universe as the union of every inventoried family listing."""
    union: set[str] = set()
    for entry in inventory.values():
        union.update(entry.symbols)
    if not union:
        incidents = [
            f"{entry.family}:{item.get('note')}"
            for entry in inventory.values()
            for item in entry.incidents
        ]
        raise SourceQualificationError(
            "official archive family union produced an empty historical family",
            context={"incidents": incidents},
        )
    return sorted(union)


def select_regime_candidates(
    objects: Sequence[ListingObject],
) -> dict[str, tuple[ListingObject, ...]]:
    """Regime buckets with candidates ordered smallest-first.

    Regime evidence (early/middle/recent) is preserved; within a regime the planner is
    free to choose the smallest adequate object.
    """
    usable = [
        obj
        for obj in sorted(objects, key=lambda item: item.key)
        if obj.key.endswith(".zip") or obj.key.endswith(".csv")
    ]
    if not usable:
        return {}
    count = len(usable)
    if count < 3:
        buckets = {
            "early": [usable[0]],
            "middle": [usable[count // 2]],
            "recent": [usable[-1]],
        }
    else:
        third = count // 3
        buckets = {
            "early": usable[:third],
            "middle": usable[third : 2 * third] or [usable[count // 2]],
            "recent": usable[2 * third :],
        }
    ordered: dict[str, tuple[ListingObject, ...]] = {}
    for regime, items in buckets.items():
        ordered[regime] = tuple(
            sorted(
                items,
                key=lambda obj: (
                    obj.size if obj.size is not None else 1 << 62,
                    obj.key,
                ),
            )
        )
    return ordered


@dataclass(frozen=True, slots=True)
class SamplePlanEntry:
    family: str
    symbol: str
    regime: str
    products: tuple[str, ...]
    key: str
    url: str
    byte_size: int
    action: str
    block_reason: str = ""


@dataclass(frozen=True, slots=True)
class SamplePlan:
    """Deterministic preflight plan produced before any new sample byte is fetched."""

    entries: tuple[SamplePlanEntry, ...]
    blocked: tuple[Mapping[str, Any], ...]
    new_download_bytes: int
    retained_bytes: int
    budget_bytes: int
    max_object_bytes: int
    unique_new_objects: int = 0
    unique_retained_objects: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [asdict(entry) for entry in self.entries],
            "blocked": [dict(item) for item in self.blocked],
            "new_download_bytes": self.new_download_bytes,
            "retained_bytes": self.retained_bytes,
            "budget_bytes": self.budget_bytes,
            "max_object_bytes": self.max_object_bytes,
            "unique_new_objects": self.unique_new_objects,
            "unique_retained_objects": self.unique_retained_objects,
            "note": (
                "Gate 1 execution budget for new downloads only; it never truncates, "
                "rejects, or miscounts larger source objects"
            ),
        }


def build_sample_plan(
    *,
    inventory: Mapping[str, FamilyInventory],
    family_products: Mapping[str, tuple[str, ...]],
    sample_symbols: Sequence[str],
    delisted: Sequence[str],
    retained_keys: Mapping[str, int],
    budget_bytes: int = GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    max_object_bytes: int = GATE1_MAX_NEW_OBJECT_BYTES,
) -> SamplePlan:
    """Plan every sample before downloading, choosing the smallest adequate objects.

    Already retained, verified objects never consume the new-download budget. When no
    candidate can fit, the regime is emitted as a typed ``sample_budget_exceeded`` block
    carrying the required object identity and size instead of being silently dropped.
    """
    entries: list[SamplePlanEntry] = []
    blocked: list[dict[str, Any]] = []
    delisted_set = set(delisted)
    sample_set = set(sample_symbols)
    spent = 0
    retained_total = 0
    # Budget and acquisition are accounted per unique remote object. Regime and product
    # aliases of an object already planned are free and are never fetched twice.
    emitted: set[str] = set()
    retained_seen: set[str] = set()
    for family in sorted(inventory):
        products = family_products.get(family, ())
        if not products:
            continue
        entry = inventory[family]
        for symbol in entry.symbols:
            if symbol not in sample_set:
                continue
            candidates = select_regime_candidates(entry.objects.get(symbol, ()))
            if not candidates:
                continue
            regimes = dict(candidates)
            if symbol in delisted_set:
                regimes["delisted"] = candidates.get("recent") or next(iter(candidates.values()))
            for regime in sorted(regimes):
                options = regimes[regime]
                if not options:
                    continue

                def _entry(obj: ListingObject, action: str) -> SamplePlanEntry:
                    return SamplePlanEntry(
                        family=family,
                        symbol=symbol,
                        regime=regime,
                        products=products,
                        key=obj.key,
                        url=vision_object_url(obj.key),
                        byte_size=int(obj.size) if obj.size is not None else 0,
                        action=action,
                    )

                chosen: SamplePlanEntry | None = None
                for obj in options:
                    if obj.key in emitted:
                        chosen = _entry(obj, "alias")
                        break
                for obj in options if chosen is None else ():
                    if obj.key in retained_keys:
                        if obj.key not in retained_seen:
                            retained_seen.add(obj.key)
                            retained_total += retained_keys[obj.key]
                        emitted.add(obj.key)
                        chosen = _entry(obj, "reuse_retained")
                        break
                for obj in options if chosen is None else ():
                    size = int(obj.size) if obj.size is not None else 0
                    if size <= 0 or size > max_object_bytes:
                        continue
                    if spent + size > budget_bytes:
                        continue
                    spent += size
                    emitted.add(obj.key)
                    chosen = _entry(obj, "download")
                    break
                if chosen is None:
                    smallest = options[0]
                    required = int(smallest.size) if smallest.size is not None else 0
                    blocked.append(
                        {
                            "kind": SAMPLE_BUDGET_BLOCK,
                            "family": family,
                            "symbol": symbol,
                            "regime": regime,
                            "products": list(products),
                            "required_key": smallest.key,
                            "required_bytes": required,
                            "max_object_bytes": max_object_bytes,
                            "budget_bytes": budget_bytes,
                            "budget_remaining_bytes": max(budget_bytes - spent, 0),
                        }
                    )
                    entries.append(
                        SamplePlanEntry(
                            family=family,
                            symbol=symbol,
                            regime=regime,
                            products=products,
                            key=smallest.key,
                            url=vision_object_url(smallest.key),
                            byte_size=required,
                            action="blocked",
                            block_reason=SAMPLE_BUDGET_BLOCK,
                        )
                    )
                    continue
                entries.append(chosen)
    return SamplePlan(
        entries=tuple(entries),
        blocked=tuple(blocked),
        new_download_bytes=spent,
        retained_bytes=retained_total,
        budget_bytes=budget_bytes,
        max_object_bytes=max_object_bytes,
        unique_new_objects=len(emitted) - len(retained_seen),
        unique_retained_objects=len(retained_seen),
    )


def _uncovered_listed_symbols(
    family_symbols: Mapping[str, set[str]],
    family_symbol_objects: Mapping[tuple[str, str], int],
) -> tuple[str, ...]:
    """Symbols listed under a family prefix that contributed zero objects."""
    uncovered: set[str] = set()
    for family, symbols in family_symbols.items():
        for symbol in symbols:
            if family_symbol_objects.get((family, symbol), 0) <= 0:
                uncovered.add(symbol)
    return tuple(sorted(uncovered))


def _family_group(family: str) -> str:
    """Logical family behind a cadence prefix: monthly/klines and daily/klines -> klines."""
    return family.split("/", 1)[-1]


def _universe_coverage_gaps(
    universe: Sequence[str],
    families: Sequence[str],
    family_symbol_lists: Mapping[str, set[str]],
    family_symbol_objects: Mapping[tuple[str, str], int],
    *,
    require_every_group: bool,
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    """Coverage of the full discovered universe, not only symbols already listed.

    A universe member with no prefix under a logical family is a coverage gap with
    explicit unavailability evidence, never a silent omission. ``require_every_group``
    demands every logical family for every symbol; the union-membership product only
    demands that a symbol be evidenced somewhere.
    """
    groups: dict[str, list[str]] = {}
    for family in families:
        groups.setdefault(_family_group(family), []).append(family)
    gaps: list[dict[str, Any]] = []
    uncovered: set[str] = set()
    for symbol in sorted(set(universe)):
        symbol_gaps: list[dict[str, Any]] = []
        covered_groups = 0
        for group in sorted(groups):
            group_families = tuple(groups[group])
            objects = sum(
                family_symbol_objects.get((family, symbol), 0) for family in group_families
            )
            if objects > 0:
                covered_groups += 1
                continue
            listed = any(
                symbol in family_symbol_lists.get(family, set()) for family in group_families
            )
            symbol_gaps.append(
                {
                    "symbol": symbol,
                    "family_group": group,
                    "families": list(group_families),
                    "status": "listed_prefix_empty" if listed else "absent_family_prefix",
                    "objects": 0,
                }
            )
        blocked = bool(symbol_gaps) if require_every_group else covered_groups == 0
        if blocked:
            uncovered.add(symbol)
            gaps.extend(symbol_gaps)
    return tuple(gaps), tuple(sorted(uncovered))


def _symbol_note(symbols: Sequence[str], limit: int) -> str:
    listed = ",".join(symbols[:limit])
    remainder = len(symbols) - limit
    return f"{listed} (+{remainder} more)" if remainder > 0 else listed


def _coverage_gap_notes(
    uncovered_listed: Sequence[str],
    uncovered_universe: Sequence[str],
    *,
    limit: int = 25,
) -> str:
    notes: list[str] = []
    if uncovered_listed:
        notes.append(
            "listed family prefixes have zero objects for "
            + _symbol_note(uncovered_listed, limit)
        )
    if uncovered_universe:
        notes.append(
            "discovered universe symbols lack required family coverage: "
            + _symbol_note(uncovered_universe, limit)
        )
    return "; ".join(notes)


def _declared_families_present(families: Sequence[str], family_listed: Mapping[str, int]) -> bool:
    """True when every logical family (trades, klines, ...) has at least one cadence."""
    if not families:
        return False
    groups: dict[str, list[str]] = {}
    for family in families:
        groups.setdefault(_family_group(family), []).append(family)
    return all(any(family_listed.get(item, 0) > 0 for item in group) for group in groups.values())


def _required_interval(family: str) -> str | None:
    return INTERVAL_REQUIRED_FAMILIES.get(family)


def _discover_symbol_prefixes(index: ObjectIndex, family: str, family_prefix: str, symbol: str) -> list[str]:
    symbol_prefix = f"{family_prefix}{symbol}/"
    required = _required_interval(family)
    try:
        nested = index.list_common_prefixes(symbol_prefix)
    except SourceQualificationError:
        return [] if required else [symbol_prefix]
    if required:
        wanted = f"{symbol_prefix}{required}/"
        return [prefix for prefix in nested if prefix == wanted]
    return [symbol_prefix]


def _list_objects_for_symbol(
    index: ObjectIndex,
    family: str,
    family_prefix: str,
    symbol: str,
) -> list[ListingObject]:
    out: dict[str, ListingObject] = {}
    for prefix in _discover_symbol_prefixes(index, family, family_prefix, symbol):
        for obj in index.list_objects(prefix):
            out[obj.key] = obj
    return sorted(out.values(), key=lambda item: item.key)


def discover_historical_symbols(index: ObjectIndex) -> list[str]:
    """Discovered universe via the shared single-traversal family inventory."""
    return inventory_symbols(build_family_inventory(index))


def parse_current_perpetuals(payload: Mapping[str, Any]) -> list[str]:
    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise SourceQualificationError(
            "exchangeInfo payload is missing symbols[]",
            context={"keys": sorted(payload.keys())},
        )
    current: list[str] = []
    for item in symbols:
        if not isinstance(item, dict):
            raise SourceQualificationError("exchangeInfo symbol row is not an object")
        if "contractType" not in item or "symbol" not in item:
            raise SourceQualificationError(
                "exchangeInfo row missing symbol or contractType",
                context={"row_keys": sorted(item.keys())},
            )
        if str(item["contractType"]).strip().upper() != "PERPETUAL":
            continue
        name = str(item["symbol"]).strip().upper()
        if name:
            current.append(name)
    if not current:
        raise SourceQualificationError("exchangeInfo contains no PERPETUAL contracts")
    return sorted(set(current))


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def _checkpoint_document(kind: str, body: Mapping[str, Any]) -> dict[str, Any]:
    return {"ticket": TICKET_ID, "kind": kind, "version": CHECKPOINT_VERSION, **dict(body)}


def read_checkpoint_document(path: Path, *, kind: str) -> dict[str, Any] | None:
    """Load a durable checkpoint document, or ``None`` when it is genuinely absent.

    A present but malformed, foreign, or wrong-version document is a resume-integrity
    failure. Silently degrading it to an empty store would erase durable resume authority
    and repeat remote work.
    """
    if not path.exists():
        return None
    if not path.is_file():
        raise ResumeIntegrityError(
            "checkpoint path exists but is not a file", context={"path": str(path)}
        )
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ResumeIntegrityError(
            "checkpoint document is unreadable", context={"path": str(path)}
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ResumeIntegrityError(
            "checkpoint document is not valid JSON", context={"path": str(path)}
        ) from exc
    if not isinstance(data, dict):
        raise ResumeIntegrityError(
            "checkpoint document is not an object", context={"path": str(path)}
        )
    if data.get("ticket") != TICKET_ID:
        raise ResumeIntegrityError(
            "checkpoint document belongs to another ticket",
            context={"path": str(path), "ticket": data.get("ticket")},
        )
    if data.get("kind") != kind:
        raise ResumeIntegrityError(
            "checkpoint document kind mismatch",
            context={"path": str(path), "expected": kind, "found": data.get("kind")},
        )
    if data.get("version") != CHECKPOINT_VERSION:
        raise ResumeIntegrityError(
            "unsupported checkpoint document version",
            context={"path": str(path), "version": data.get("version")},
        )
    return data


def _require_hex_digest(value: Any, *, label: str, context: Mapping[str, Any]) -> str:
    digest = str(value or "").lower().strip()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ResumeIntegrityError(
            f"{label} is not a 64-character hex digest", context=dict(context)
        )
    return digest


def listing_request_identity(
    *,
    endpoint: str,
    prefix: str,
    delimiter: str,
    continuation_token: str | None,
) -> dict[str, Any]:
    """Durable, redacted identity of one ListObjectsV2 request."""
    return {
        "endpoint": endpoint,
        "list_type": "2",
        "prefix": prefix,
        "delimiter": delimiter,
        "continuation_token": continuation_token,
    }


def listing_request_key(identity: Mapping[str, Any]) -> str:
    blob = json.dumps(dict(identity), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalized_identity(request: Mapping[str, Any]) -> dict[str, Any]:
    token = request.get("continuation_token")
    return listing_request_identity(
        endpoint=str(request.get("endpoint") or ""),
        prefix=str(request.get("prefix") or ""),
        delimiter=str(request.get("delimiter") or ""),
        continuation_token=None if token is None else str(token),
    )


@dataclass
class RetryJournal:
    """Atomically durable, redacted retry-incident journal.

    Incidents are persisted as they occur so an aborted run cannot erase the evidence
    that remote work was retried.
    """

    path: Path | None = None
    incidents: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> RetryJournal:
        document = read_checkpoint_document(path, kind="retry_journal")
        if document is None:
            return cls(path=path)
        recorded = document.get("incidents")
        if not isinstance(recorded, list):
            raise ResumeIntegrityError(
                "retry journal incidents are not a list", context={"path": str(path)}
            )
        return cls(path=path, incidents=[dict(item) for item in recorded])

    def append(self, incident: Mapping[str, Any]) -> None:
        self.incidents.append(dict(incident))
        if self.path is not None:
            _atomic_write_json(
                self.path, _checkpoint_document("retry_journal", {"incidents": self.incidents})
            )


@dataclass
class ListingCheckpointStore:
    """Request-keyed listing checkpoint binding a request identity to retained bytes.

    Reuse requires that the checkpoint key, the stored request, the response's own echoed
    prefix/delimiter/continuation token, the parsed page metadata, the digest, and the
    cache-local content-addressed path all agree. Anything else fails closed.
    """

    path: Path
    cache_dir: Path
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    unclaimed: list[dict[str, Any]] = field(default_factory=list)
    reused: int = 0
    fetched: int = 0

    @classmethod
    def load(cls, path: Path, cache_dir: Path) -> ListingCheckpointStore:
        document = read_checkpoint_document(path, kind="listing_checkpoint")
        if document is None:
            return cls(path=path, cache_dir=cache_dir)
        entries = document.get("entries")
        unclaimed = document.get("unclaimed", [])
        if not isinstance(entries, dict) or not isinstance(unclaimed, list):
            raise ResumeIntegrityError(
                "listing checkpoint document has an invalid shape",
                context={"path": str(path)},
            )
        store = cls(
            path=path,
            cache_dir=cache_dir,
            entries={},
            unclaimed=[dict(item) for item in unclaimed],
        )
        for key, entry in entries.items():
            store.entries[str(key)] = store._validated_entry(str(key), entry)
        return store

    def _validated_entry(self, key: str, entry: Any) -> dict[str, Any]:
        context = {"path": str(self.path), "request_key": key}
        if not isinstance(entry, dict):
            raise ResumeIntegrityError("listing checkpoint entry is not an object", context=context)
        request = entry.get("request")
        if not isinstance(request, dict):
            raise ResumeIntegrityError(
                "listing checkpoint entry has no request identity", context=context
            )
        identity = _normalized_identity(request)
        if dict(request) != identity:
            raise ResumeIntegrityError(
                "listing checkpoint request identity is malformed", context=context
            )
        if listing_request_key(identity) != key:
            raise ResumeIntegrityError(
                "listing checkpoint key is not the canonical hash of its request",
                context=context,
            )
        digest = _require_hex_digest(
            entry.get("response_sha256"), label="listing response digest", context=context
        )
        expected_path = content_addressed_path(self.cache_dir, digest)
        if Path(str(entry.get("content_path") or "")) != expected_path:
            raise ResumeIntegrityError(
                "listing checkpoint content path is not the cache-local content address",
                context={**context, "expected": str(expected_path)},
            )
        if not isinstance(entry.get("is_truncated"), bool):
            raise ResumeIntegrityError(
                "listing checkpoint truncation flag is not a bool", context=context
            )
        token = entry.get("next_continuation_token")
        if token is not None and not isinstance(token, str):
            raise ResumeIntegrityError(
                "listing checkpoint next token is not a string", context=context
            )
        if not isinstance(entry.get("byte_size"), int) or int(entry["byte_size"]) < 0:
            raise ResumeIntegrityError(
                "listing checkpoint byte size is invalid", context=context
            )
        validated = dict(entry)
        validated["request"] = identity
        validated["response_sha256"] = digest
        validated["content_path"] = str(expected_path)
        return validated

    def _flush(self) -> None:
        _atomic_write_json(
            self.path,
            _checkpoint_document(
                "listing_checkpoint", {"entries": self.entries, "unclaimed": self.unclaimed}
            ),
        )

    def record(self, identity: Mapping[str, Any], entry: Mapping[str, Any]) -> None:
        key = listing_request_key(_normalized_identity(identity))
        self.entries[key] = self._validated_entry(key, entry)
        self._flush()

    def retained_bytes(self, identity: Mapping[str, Any]) -> bytes | None:
        """Retained response for this exact request, or ``None`` when not checkpointed.

        Every reuse re-proves the full chain: key, stored request, retained digest,
        cache-local content address, the response's own echoed request identity, and the
        parsed truncation/next-token metadata.
        """
        wanted = _normalized_identity(identity)
        key = listing_request_key(wanted)
        entry = self.entries.get(key)
        if not entry:
            return None
        entry = self._validated_entry(key, entry)
        context = {"request_key": key, "prefix": wanted["prefix"]}
        if entry["request"] != wanted:
            raise ResumeIntegrityError(
                "listing checkpoint request does not match the resumed request",
                context=context,
            )
        raw_path = Path(entry["content_path"])
        if not raw_path.is_file():
            raise ResumeIntegrityError(
                "listing checkpoint points at a missing retained response",
                context={**context, "content_path": str(raw_path)},
            )
        actual = compute_sha256(raw_path)
        if actual != entry["response_sha256"]:
            raise ResumeIntegrityError(
                "listing checkpoint hash mismatch; refusing tampered retained response",
                context={**context, "expected": entry["response_sha256"], "actual": actual},
            )
        payload = raw_path.read_bytes()
        echoed = parse_listing_identity(payload, endpoint=wanted["endpoint"])
        if echoed != wanted:
            raise ResumeIntegrityError(
                "retained response does not echo the resumed request identity",
                context={**context, "echoed": echoed},
            )
        _prefixes, _objects, truncated, next_token = parse_s3_list_bucket(
            payload.decode("utf-8")
        )
        if truncated != entry["is_truncated"] or next_token != entry.get(
            "next_continuation_token"
        ):
            raise ResumeIntegrityError(
                "retained response pagination metadata does not match the checkpoint",
                context={
                    **context,
                    "parsed_truncated": truncated,
                    "parsed_next_token": next_token,
                },
            )
        self.reused += 1
        return payload

    def bootstrap(self, *, endpoint: str) -> dict[str, int]:
        """Claim retained content-addressed blobs whose request identity is provable.

        A ListBucketResult echoes its own prefix, delimiter and continuation token, so the
        originating request is recoverable from the bytes. Anything unprovable is retained
        as unclaimed evidence: never redownloaded over, never misattributed, never deleted.
        """
        claimed = 0
        checksum_blobs = 0
        unclaimed = 0
        if not self.cache_dir.is_dir():
            return {"claimed": 0, "checksum_blobs": 0, "unclaimed": 0}
        known_unclaimed = {str(item.get("content_path")) for item in self.unclaimed}

        def _mark_unclaimed(blob: Path, reason: str, note: str | None = None) -> int:
            if str(blob) in known_unclaimed:
                return 0
            record: dict[str, Any] = {"content_path": str(blob), "reason": reason}
            if note is not None:
                record["note"] = note
            self.unclaimed.append(record)
            known_unclaimed.add(str(blob))
            return 1

        for blob in sorted(self.cache_dir.iterdir()):
            if not blob.is_file() or len(blob.name) != 64:
                continue
            digest = compute_sha256(blob)
            if digest != blob.name:
                unclaimed += _mark_unclaimed(blob, "content_address_mismatch")
                continue
            payload = blob.read_bytes()
            identity = parse_listing_identity(payload, endpoint=endpoint)
            if identity is None:
                if parse_provider_checksum(payload.decode("utf-8", errors="replace")) is not None:
                    checksum_blobs += 1
                    continue
                unclaimed += _mark_unclaimed(blob, "unprovable_request_identity")
                continue
            key = listing_request_key(identity)
            if key in self.entries:
                continue
            try:
                _prefixes, _objects, truncated, next_token = parse_s3_list_bucket(
                    payload.decode("utf-8")
                )
            except SourceQualificationError as exc:
                unclaimed += _mark_unclaimed(blob, "unparsable_listing_page", str(exc))
                continue
            self.entries[key] = self._validated_entry(
                key,
                {
                    "request": identity,
                    "response_sha256": digest,
                    "content_path": str(content_addressed_path(self.cache_dir, digest)),
                    "byte_size": len(payload),
                    "retrieved_at": None,
                    "bootstrapped": True,
                    "is_truncated": truncated,
                    "next_continuation_token": next_token,
                },
            )
            claimed += 1
        self._flush()
        return {"claimed": claimed, "checksum_blobs": checksum_blobs, "unclaimed": unclaimed}

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "entries": len(self.entries),
            "reused_requests": self.reused,
            "fetched_requests": self.fetched,
            "unclaimed_evidence": len(self.unclaimed),
        }


def parse_listing_identity(payload: bytes, *, endpoint: str) -> dict[str, Any] | None:
    """Recover the originating ListObjectsV2 request identity from a response body."""
    try:
        root = ElementTree.fromstring(payload.decode("utf-8"))
    except (ElementTree.ParseError, UnicodeDecodeError):
        return None
    if _local_tag(root.tag) != "ListBucketResult":
        return None
    prefix_node = _first_child(root, "Prefix")
    delimiter_node = _first_child(root, "Delimiter")
    token_node = _first_child(root, "ContinuationToken")
    if prefix_node is None or delimiter_node is None:
        return None
    return listing_request_identity(
        endpoint=endpoint,
        prefix=prefix_node.text or "",
        delimiter=delimiter_node.text or "",
        continuation_token=None if token_node is None else (token_node.text or ""),
    )


@dataclass
class RetainedChecksumIndex:
    """Provider checksum sidecars already retained on disk, keyed by object basename.

    A sidecar only carries provider authority while its bytes still hash to its own
    content-addressed filename, so every lookup re-proves that before returning it.
    """

    cache_dir: Path | None = None
    by_basename: dict[str, dict[str, Any]] = field(default_factory=dict)
    ambiguous: set[str] = field(default_factory=set)

    @classmethod
    def from_cache(cls, cache_dir: Path) -> RetainedChecksumIndex:
        index = cls(cache_dir=cache_dir)
        if not cache_dir.is_dir():
            return index
        for blob in sorted(cache_dir.iterdir()):
            if not blob.is_file() or len(blob.name) != 64:
                continue
            body = blob.read_bytes()
            if body[:5] == b"<?xml":
                continue
            if compute_sha256(blob) != blob.name:
                # Not content-addressed: never provider authority.
                continue
            text_body = body.decode("utf-8", errors="replace")
            digest = parse_provider_checksum(text_body)
            if digest is None:
                continue
            tokens = text_body.strip().split()
            if len(tokens) < 2:
                continue
            basename = tokens[1].strip()
            if basename in index.by_basename:
                if index.by_basename[basename]["provider_checksum"] != digest:
                    index.ambiguous.add(basename)
                continue
            index.by_basename[basename] = {
                "provider_checksum": digest,
                "content_path": str(blob),
                "blob_sha256": blob.name,
            }
        return index

    def lookup(self, key: str) -> dict[str, Any] | None:
        basename = key.rsplit("/", 1)[-1]
        if basename in self.ambiguous:
            return None
        evidence = self.by_basename.get(basename)
        if evidence is None:
            return None
        blob = Path(str(evidence["content_path"]))
        if not blob.is_file():
            return None
        actual = compute_sha256(blob)
        if actual != str(evidence["blob_sha256"]) or actual != blob.name:
            raise ResumeIntegrityError(
                "retained provider checksum sidecar no longer matches its content address",
                context={"key": key, "content_path": str(blob), "actual": actual},
            )
        parsed = parse_provider_checksum(blob.read_bytes().decode("utf-8", errors="replace"))
        if parsed != str(evidence["provider_checksum"]):
            raise ResumeIntegrityError(
                "retained provider checksum sidecar bytes changed",
                context={"key": key, "content_path": str(blob)},
            )
        return dict(evidence)


@dataclass
class SampleCheckpointStore:
    """Per-object sample checkpoint written atomically as each object is verified."""

    path: Path
    sidecar_dir: Path | None = None
    objects: dict[str, dict[str, Any]] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    recovered: int = 0

    @classmethod
    def load(cls, path: Path, sidecar_dir: Path | None = None) -> SampleCheckpointStore:
        document = read_checkpoint_document(path, kind="sample_checkpoint")
        if document is None:
            return cls(path=path)
        objects = document.get("objects")
        if not isinstance(objects, dict):
            raise ResumeIntegrityError(
                "sample checkpoint objects are not an object", context={"path": str(path)}
            )
        store = cls(
            path=path,
            sidecar_dir=sidecar_dir,
            extra={
                key: value
                for key, value in document.items()
                if key not in {"objects", "ticket", "kind", "version"}
            },
        )
        for key, entry in objects.items():
            store.objects[str(key)] = store._validated_entry(str(key), entry)
        return store

    def _validated_entry(self, key: str, entry: Any) -> dict[str, Any]:
        context = {"path": str(self.path), "key": key}
        if not isinstance(entry, dict):
            raise ResumeIntegrityError("sample checkpoint entry is not an object", context=context)
        if entry.get("status") != "complete":
            raise ResumeIntegrityError(
                "sample checkpoint entry is not a completed object", context=context
            )
        digest = _require_hex_digest(entry.get("sha256"), label="sample digest", context=context)
        provider = _require_hex_digest(
            entry.get("provider_checksum"), label="provider checksum", context=context
        )
        if provider != digest:
            raise ResumeIntegrityError(
                "sample checkpoint provider checksum disagrees with the object digest",
                context={**context, "sha256": digest, "provider_checksum": provider},
            )
        if entry.get("checksum_match") is not True:
            raise ResumeIntegrityError(
                "sample checkpoint entry is not checksum-verified", context=context
            )
        if str(entry.get("url") or "") != vision_object_url(key):
            raise ResumeIntegrityError(
                "sample checkpoint url does not match the object key", context=context
            )
        size = entry.get("byte_size")
        if not isinstance(size, int) or size <= 0:
            raise ResumeIntegrityError("sample checkpoint byte size is invalid", context=context)
        fields = entry.get("schema_fields")
        if not isinstance(fields, list) or not fields:
            raise ResumeIntegrityError(
                "sample checkpoint schema fields are missing", context=context
            )
        if not str(entry.get("schema_kind") or ""):
            raise ResumeIntegrityError(
                "sample checkpoint schema kind is missing", context=context
            )
        sidecar_path = str(entry.get("provider_checksum_path") or "")
        sidecar_digest = _require_hex_digest(
            entry.get("provider_checksum_sha256"),
            label="sample checkpoint sidecar digest",
            context=context,
        )
        if not sidecar_path:
            raise ResumeIntegrityError(
                "sample checkpoint has no provider sidecar path", context=context
            )
        if self.sidecar_dir is not None:
            expected = content_addressed_path(self.sidecar_dir, sidecar_digest)
            if Path(sidecar_path) != expected:
                raise ResumeIntegrityError(
                    "sample checkpoint sidecar path is not its cache-local content address",
                    context={**context, "expected": str(expected)},
                )
        validated = dict(entry)
        validated["sha256"] = digest
        validated["provider_checksum"] = provider
        return validated

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self.objects.get(key)
        return None if entry is None else self._validated_entry(key, entry)

    def record(self, key: str, entry: Mapping[str, Any]) -> None:
        """Checkpoint one verified object immediately, not at end of run."""
        self.objects[key] = self._validated_entry(key, dict(entry))
        self.flush()

    def flush(self, **updates: Any) -> None:
        self.extra.update(updates)
        body = dict(self.extra)
        body["objects"] = self.objects
        _atomic_write_json(self.path, _checkpoint_document("sample_checkpoint", body))


def persist_provider_sidecar(body: bytes, *, sidecar_dir: Path) -> tuple[Path, str]:
    """Publish a provider checksum sidecar content-addressably before it is relied on.

    Every sidecar, however it was obtained, becomes a retained content-addressed object so
    a later resume can re-prove provider authority instead of trusting a checkpoint.
    """
    digest = _object_sha256(body)
    dest = content_addressed_path(sidecar_dir, digest)
    if dest.exists():
        existing = compute_sha256(dest)
        if existing != digest:
            raise ResumeIntegrityError(
                "retained sidecar path holds different content than its content address",
                context={"path": str(dest), "expected": digest, "actual": existing},
            )
        return dest, digest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".partial-{digest}.part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    return dest, digest


def verify_provider_sidecar(
    *,
    key: str,
    object_sha256: str,
    sidecar_path: Path,
    sidecar_sha256: str,
    sidecar_dir: Path,
) -> str:
    """Re-prove provider authority from the retained sidecar bytes themselves.

    A sample checkpoint alone is never provider authority: the sidecar must still exist at
    its cache-local content address, rehash to the recorded blob digest, parse to exactly
    one provider checksum and filename, name this object, and carry the object's digest.
    """
    context = {"key": key, "sidecar_path": str(sidecar_path)}
    blob_digest = _require_hex_digest(
        sidecar_sha256, label="sidecar blob digest", context=context
    )
    expected_path = content_addressed_path(sidecar_dir, blob_digest)
    if Path(sidecar_path) != expected_path:
        raise ResumeIntegrityError(
            "provider sidecar path is not its cache-local content address",
            context={**context, "expected": str(expected_path)},
        )
    if not expected_path.is_file():
        raise ResumeIntegrityError(
            "provider sidecar is missing from the retained store", context=context
        )
    actual = compute_sha256(expected_path)
    if actual != blob_digest:
        raise ResumeIntegrityError(
            "provider sidecar bytes do not match the recorded blob digest",
            context={**context, "expected": blob_digest, "actual": actual},
        )
    tokens = expected_path.read_bytes().decode("utf-8", errors="replace").strip().split()
    if len(tokens) != 2:
        raise ResumeIntegrityError(
            "provider sidecar does not hold exactly one checksum and filename",
            context={**context, "fields": len(tokens)},
        )
    provider = parse_provider_checksum(tokens[0])
    if provider is None:
        raise ResumeIntegrityError(
            "provider sidecar checksum is malformed", context=context
        )
    if tokens[1] != key.rsplit("/", 1)[-1]:
        raise ResumeIntegrityError(
            "provider sidecar names a different object",
            context={**context, "sidecar_filename": tokens[1]},
        )
    if provider != object_sha256:
        raise ResumeIntegrityError(
            "provider sidecar checksum disagrees with the retained object digest",
            context={**context, "sidecar_checksum": provider, "object": object_sha256},
        )
    return provider


def recover_retained_samples(
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    checksums: RetainedChecksumIndex,
    checkpoint: SampleCheckpointStore,
    keys: Sequence[str],
) -> int:
    """Re-adopt already downloaded, checksum-proven sample bytes without redownloading.

    A retained object is recovered only when its provider checksum sidecar still hashes to
    its own content address, the content-addressed object exists at the digest the sidecar
    claims, and the retained raw bytes rehash to that same digest.
    """
    recovered = 0
    for key in keys:
        if checkpoint.get(key) is not None:
            continue
        evidence = checksums.lookup(key)
        if evidence is None:
            continue
        digest = str(evidence["provider_checksum"])
        dest = content_addressed_path(sample_dir, digest)
        if not dest.is_file():
            continue
        actual = compute_sha256(dest)
        if actual != digest or dest.name != digest:
            raise ResumeIntegrityError(
                "retained sample bytes do not match the retained provider checksum",
                context={"key": key, "expected": digest, "actual": actual, "path": str(dest)},
            )
        sidecar_path = Path(str(evidence["content_path"]))
        verify_provider_sidecar(
            key=key,
            object_sha256=actual,
            sidecar_path=sidecar_path,
            sidecar_sha256=str(evidence["blob_sha256"]),
            sidecar_dir=sidecar_dir,
        )
        payload = dest.read_bytes()
        schema = infer_schema_fields(payload, name=key)
        checkpoint.record(
            key,
            {
                "status": "complete",
                "sha256": digest,
                "byte_size": len(payload),
                "url": vision_object_url(key),
                "provider_checksum": digest,
                "checksum_match": True,
                "schema_kind": schema.kind,
                "schema_fields": list(schema.fields),
                "retrieval_time": "",
                "recovered_from_retained_bytes": True,
                "provider_checksum_path": str(sidecar_path),
                "provider_checksum_sha256": str(evidence["blob_sha256"]),
            },
        )
        recovered += 1
    checkpoint.recovered += recovered
    return recovered


def _object_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sample_symbol_set(discovered: Sequence[str], delisted: Sequence[str]) -> list[str]:
    ordered = list(discovered)
    chosen: list[str] = []
    if ordered:
        chosen.extend((ordered[0], ordered[len(ordered) // 2], ordered[-1]))
    if delisted:
        chosen.append(delisted[0])
    unique: list[str] = []
    seen: set[str] = set()
    for symbol in chosen:
        if symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)
    return unique


def drop_identity_volatility(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: drop_identity_volatility(item)
            for key, item in value.items()
            if key not in _IDENTITY_DROP_KEYS
        }
    if isinstance(value, list):
        return [drop_identity_volatility(item) for item in value]
    if isinstance(value, tuple):
        return [drop_identity_volatility(item) for item in value]
    return value


def identity_payload(report: QualificationReport) -> dict[str, Any]:
    return drop_identity_volatility(report.to_dict())


def identity_bytes(report: QualificationReport) -> bytes:
    return (
        json.dumps(identity_payload(report), indent=2, sort_keys=True, default=str) + "\n"
    ).encode("utf-8")


def qualification_exit_code(report: QualificationReport) -> int:
    if report.accepted and report.gate_status == GateStatus.QUALIFIED.value:
        return 0
    return 2


class TransportObjectIndex:
    """Binance Vision listing/fetch using ListObjectsV2 only."""

    def __init__(
        self,
        transport: HttpTransport,
        *,
        timeout: TimeoutConfig | None = None,
        s3_endpoint: str = VISION_S3_ENDPOINT,
        list_cache_dir: Path | None = None,
        checkpoint: ListingCheckpointStore | None = None,
        retry: RetryRunner | None = None,
    ) -> None:
        self._transport = transport
        self._timeout = timeout or TimeoutConfig()
        self._s3_endpoint = s3_endpoint
        self._list_cache_dir = list_cache_dir
        self._checkpoint = checkpoint
        self._retry = retry or RetryRunner()

    def list_common_prefixes(self, prefix: str) -> list[str]:
        prefixes, _objects = self._list_pages(prefix)
        return prefixes

    def list_objects(self, prefix: str) -> list[ListingObject]:
        _prefixes, objects = self._list_pages(prefix)
        return objects

    def fetch_bytes(self, url: str) -> bytes:
        dest = self._list_cache_dir
        if dest is None:
            raise SourceQualificationError(
                "TransportObjectIndex.fetch_bytes requires list_cache_dir",
                context={"url": url},
            )
        listed = None
        result = self._retry.run(
            f"fetch_bytes:{url}",
            lambda: atomic_download(
                url,
                dest,
                transport=self._transport,
                timeout=self._timeout,
                max_bytes=max(listed or 8_388_608, 8_388_608),
            ),
        )
        return result.dest_path.read_bytes()

    def _list_pages(self, prefix: str) -> tuple[list[str], list[ListingObject]]:
        if self._list_cache_dir is None:
            raise SourceQualificationError(
                "TransportObjectIndex listing requires list_cache_dir",
                context={"prefix": prefix},
            )
        prefixes: list[str] = []
        objects: list[ListingObject] = []
        token: str | None = None
        seen: set[str] = set()
        while True:
            page_prefixes, page_objects, truncated, next_token = self._list_page(prefix, token)
            prefixes.extend(page_prefixes)
            objects.extend(page_objects)
            if not truncated:
                break
            if not next_token:
                raise SourceQualificationError(
                    "S3 listing truncated without V2 continuation token",
                    context={"prefix": prefix},
                )
            if next_token in seen:
                raise SourceQualificationError(
                    "S3 listing page cycle detected",
                    context={"prefix": prefix, "token": next_token},
                )
            seen.add(next_token)
            token = next_token
        unique_prefixes = sorted(set(prefixes))
        unique_objects = {item.key: item for item in objects}
        return unique_prefixes, sorted(unique_objects.values(), key=lambda item: item.key)

    def _list_page(
        self, prefix: str, token: str | None = None
    ) -> tuple[list[str], list[ListingObject], bool, str | None]:
        params = {"list-type": "2", "delimiter": "/", "prefix": prefix}
        if token is not None:
            params["continuation-token"] = token
        parsed = urlparse(self._s3_endpoint)
        url = urlunparse(parsed._replace(query=urlencode(params)))
        identity = listing_request_identity(
            endpoint=self._s3_endpoint,
            prefix=prefix,
            delimiter="/",
            continuation_token=token,
        )
        if self._checkpoint is not None:
            retained = self._checkpoint.retained_bytes(identity)
            if retained is not None:
                return parse_s3_list_bucket(retained.decode("utf-8"))
        result = self._retry.run(
            f"list:{prefix}",
            lambda: atomic_download(
                url,
                self._list_cache_dir,
                transport=self._transport,
                timeout=self._timeout,
                max_bytes=8_388_608,
            ),
        )
        payload = result.dest_path.read_bytes()
        parsed_page = parse_s3_list_bucket(payload.decode("utf-8"))
        echoed = parse_listing_identity(payload, endpoint=self._s3_endpoint)
        if echoed is not None and echoed != identity:
            # A self-identifying response must describe the request we actually made.
            raise ResumeIntegrityError(
                "fetched listing response does not echo the requested identity",
                context={"prefix": prefix, "echoed": echoed},
            )
        if self._checkpoint is not None:
            self._checkpoint.fetched += 1
            # The recorded path is the published one; the checkpoint contract re-proves
            # that it is the cache-local content address.
            self._checkpoint.record(
                identity,
                {
                    "request": dict(identity),
                    "response_sha256": result.sha256,
                    "content_path": str(result.dest_path),
                    "byte_size": len(payload),
                    "retrieved_at": result.retrieval_utc.astimezone(UTC).isoformat(),
                    "bootstrapped": False,
                    "is_truncated": parsed_page[2],
                    "next_continuation_token": parsed_page[3],
                },
            )
        return parsed_page


class HttpxCoinalyzeTransport:
    """Fetch Coinalyze JSON. The key may be supplied only as the api_key header."""

    def __init__(
        self,
        transport: HttpTransport,
        *,
        cache_dir: Path,
        timeout: TimeoutConfig | None = None,
    ) -> None:
        self._transport = transport
        self._cache_dir = cache_dir
        self._timeout = timeout or TimeoutConfig()

    def fetch(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> CoinalyzeResponse:
        if "api_key" in params or "apikey" in {key.lower() for key in params}:
            raise SourceQualificationError(
                "Coinalyze API key must not appear in query parameters",
                context={"path": path},
            )
        url = f"{COINALYZE_BASE}{path}"
        result = atomic_download(
            url,
            self._cache_dir,
            params=dict(params),
            headers=dict(headers),
            transport=self._transport,
            timeout=self._timeout,
            max_bytes=8_388_608,
        )
        raw = result.dest_path.read_bytes()
        if _object_sha256(raw) != result.sha256:
            raise ResumeIntegrityError(
                "retained Coinalyze response bytes do not match the download digest",
                context={"path": path, "expected": result.sha256},
            )
        return CoinalyzeResponse(
            path=path,
            payload=json.loads(raw.decode("utf-8")),
            raw_bytes=raw,
            sha256=result.sha256,
            byte_size=len(raw),
            retrieved_at=result.retrieval_utc.astimezone(UTC).isoformat(),
            request_params=redact_request_params(params),
            header_names=tuple(sorted(headers)),
            source="http_atomic_download",
            content_path=str(result.dest_path),
            status_code=result.status_code,
        )


class FapiCurrentContractSource:
    def __init__(
        self,
        transport: HttpTransport,
        *,
        cache_dir: Path,
        timeout: TimeoutConfig | None = None,
    ) -> None:
        self._transport = transport
        self._cache_dir = cache_dir
        self._timeout = timeout or TimeoutConfig()

    def fetch_exchange_info(self) -> Mapping[str, Any]:
        result = atomic_download(
            OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"],
            self._cache_dir,
            transport=self._transport,
            timeout=self._timeout,
            max_bytes=8_388_608,
        )
        payload = json.loads(result.dest_path.read_bytes().decode("utf-8"))
        if not isinstance(payload, dict):
            raise SourceQualificationError("exchangeInfo response is not an object")
        return payload


def parse_coinalyze_history(
    payload: Any,
    *,
    path: str,
    required_point_fields: Sequence[str],
) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise SourceQualificationError(
            "Coinalyze history response is empty or not a list",
            context={"path": path},
        )
    parsed: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict) or "symbol" not in row or "history" not in row:
            raise SourceQualificationError(
                "Coinalyze row missing symbol/history",
                context={"path": path},
            )
        history = row["history"]
        if not isinstance(history, list) or not history:
            raise SourceQualificationError(
                "Coinalyze history is empty",
                context={"path": path, "symbol": row.get("symbol")},
            )
        for point in history:
            if not isinstance(point, dict):
                raise SourceQualificationError("Coinalyze history point is not an object")
            missing = [name for name in required_point_fields if name not in point]
            if missing:
                raise SourceQualificationError(
                    "Coinalyze history point missing required fields",
                    context={"path": path, "missing": missing},
                )
        times = [int(point["t"]) for point in history]
        parsed.append(
            {
                "symbol": str(row["symbol"]),
                "points": len(history),
                "first_t": min(times),
                "last_t": max(times),
                "fields": list(required_point_fields),
            }
        )
    return parsed


class CoinalyzeClient:
    """Real Coinalyze history client. The key is header-only and never stored."""

    def __init__(
        self,
        transport: CoinalyzeTransport,
        *,
        api_key: str | None,
        retry: RetryRunner | None = None,
    ) -> None:
        self._transport = transport
        self._api_key = api_key
        self._retry = retry or RetryRunner()

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            return {}
        return {"api_key": self._api_key}

    def _require_key(self) -> None:
        if not self._api_key:
            raise SourceQualificationError(
                "COINALYZE_API_KEY is required for Coinalyze history qualification"
            )

    def _fetch(
        self,
        path: str,
        *,
        params: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> tuple[Any, dict[str, Any]]:
        if "api_key" in params:
            raise SourceQualificationError(
                "Coinalyze API key must not appear in query parameters",
                context={"path": path},
            )
        response = self._retry.run(
            f"coinalyze:{path}",
            lambda: self._transport.fetch(path, params=params, headers=headers),
        )
        if response.path != path:
            raise SourceQualificationError(
                "Coinalyze transport returned a different path than requested",
                context={"requested": path, "returned": response.path},
            )
        raw = response.raw_bytes
        if not isinstance(raw, bytes) or not raw:
            raise SourceQualificationError(
                "Coinalyze transport retained no raw response bytes",
                context={"path": path},
            )
        if _object_sha256(raw) != response.sha256 or len(raw) != response.byte_size:
            raise SourceQualificationError(
                "Coinalyze provenance does not match the retained raw response bytes",
                context={
                    "path": path,
                    "reported_sha256": response.sha256,
                    "reported_byte_size": response.byte_size,
                    "raw_byte_size": len(raw),
                },
            )
        return response.payload, {
            "path": path,
            "params": redact_request_params(params),
            "header_names": sorted(headers.keys()),
            "sha256": response.sha256,
            "byte_size": response.byte_size,
            "retrieved_at": response.retrieved_at,
            "provenance_source": "raw_response_bytes",
            "transport": response.source,
            "content_path": response.content_path,
            "status_code": response.status_code,
        }

    def qualify_binance_daily(
        self,
        *,
        native_symbols: Sequence[str],
        from_ts: int,
        to_ts: int,
    ) -> dict[str, Any]:
        self._require_key()
        mapped = [coinalyze_perp_symbol(symbol) for symbol in native_symbols]
        requested = set(mapped)
        params = {
            "symbols": ",".join(mapped),
            "interval": COINALYZE_INTERVAL_DAILY,
            "from": str(int(from_ts)),
            "to": str(int(to_ts)),
        }
        headers = self._headers()
        markets, markets_prov = self._fetch(
            COINALYZE_HISTORY_ENDPOINTS["future_markets"],
            params={},
            headers=headers,
        )
        if not isinstance(markets, list) or not markets:
            raise SourceQualificationError("Coinalyze future-markets response is empty")
        matched_markets = [
            row
            for row in markets
            if isinstance(row, dict)
            and str(row.get("exchange")) == COINALYZE_EXCHANGE_CODE
            and bool(row.get("is_perpetual"))
            and str(row.get("symbol")) in requested
        ]
        matched_symbols = {str(row["symbol"]) for row in matched_markets}
        missing_markets = sorted(requested - matched_symbols)
        if missing_markets:
            raise SourceQualificationError(
                "Coinalyze future-markets missing requested symbols",
                context={"requested": sorted(requested), "missing": missing_markets},
            )
        units_by_symbol = {
            str(row["symbol"]): row.get("oi_lq_vol_denominated_in") for row in matched_markets
        }
        if any(value in (None, "") for value in units_by_symbol.values()):
            raise SourceQualificationError(
                "matched Coinalyze market is missing oi_lq_vol_denominated_in",
                context={"units": units_by_symbol},
            )
        unique_units = sorted({str(value) for value in units_by_symbol.values()})
        denominated_in = unique_units[0] if len(unique_units) == 1 else units_by_symbol
        history_specs = (
            ("liquidation", COINALYZE_HISTORY_ENDPOINTS["liquidation"], ("t", "l", "s")),
            (
                "open_interest",
                COINALYZE_HISTORY_ENDPOINTS["open_interest"],
                ("t", "o", "h", "l", "c"),
            ),
            ("funding", COINALYZE_HISTORY_ENDPOINTS["funding"], ("t", "o", "h", "l", "c")),
            ("ohlcv", COINALYZE_HISTORY_ENDPOINTS["ohlcv"], ("t", "o", "h", "l", "c", "v")),
        )
        samples: dict[str, list[dict[str, Any]]] = {}
        provenance = [markets_prov]
        for name, path, fields in history_specs:
            payload, prov = self._fetch(path, params=params, headers=headers)
            parsed = parse_coinalyze_history(payload, path=path, required_point_fields=fields)
            returned = {row["symbol"] for row in parsed}
            if returned != requested:
                raise SourceQualificationError(
                    "Coinalyze history symbols do not match request",
                    context={
                        "path": path,
                        "requested": sorted(requested),
                        "returned": sorted(returned),
                    },
                )
            samples[name] = parsed
            provenance.append(prov)
        return {
            "key_present": True,
            "key_location": "header",
            "query_contains_key": False,
            "base": COINALYZE_BASE,
            "endpoints": dict(COINALYZE_HISTORY_ENDPOINTS),
            "interval": COINALYZE_INTERVAL_DAILY,
            "from": int(from_ts),
            "to": int(to_ts),
            "requested_symbols": list(mapped),
            "matched_markets": sorted(matched_symbols),
            "binance_perpetual_market_count": len(matched_markets),
            "units": {
                "liquidation_l": "long liquidated volume",
                "liquidation_s": "short liquidated volume",
                "denominated_in": denominated_in,
                "denominated_in_by_symbol": units_by_symbol,
                "timestamps": "unix_seconds",
            },
            "retention": COINALYZE_DAILY_RETENTION,
            "censorship": BINANCE_CENSORSHIP_NOTE,
            "attribution": "Coinalyze; cite https://coinalyze.net when redistributed",
            "overlap_reconciliation": OVERLAP_RECONCILIATION,
            "samples": samples,
            "provenance": provenance,
        }


def _acquire_sample(
    *,
    key: str,
    listed_size: int,
    products: tuple[str, ...],
    family: str,
    symbol: str,
    regime: str,
    sample_dir: Path,
    sidecar_dir: Path,
    index: ObjectIndex,
    transport: HttpTransport | None,
    checkpoint: SampleCheckpointStore,
    checksums: RetainedChecksumIndex | None,
    retry: RetryRunner,
) -> SampleRecord:
    url = vision_object_url(key)
    primary = products[0] if products else ""
    prior = checkpoint.get(key)
    if isinstance(prior, dict) and prior.get("status") == "complete" and prior.get("sha256"):
        expected = str(prior["sha256"])
        dest = content_addressed_path(sample_dir, expected)
        if not dest.is_file():
            raise ResumeIntegrityError(
                "resume progress points at a missing content-addressed object",
                context={"key": key, "sha256": expected},
            )
        actual = compute_sha256(dest)
        if actual != expected:
            raise ResumeIntegrityError(
                "resume hash mismatch; refusing tampered content-addressed object",
                context={"key": key, "expected": expected, "actual": actual},
            )
        if dest.name != actual:
            raise ResumeIntegrityError(
                "content-addressed path does not match recomputed digest",
                context={"path": str(dest), "sha256": actual},
            )
        checksum = str(prior.get("provider_checksum") or "")
        if checksum != actual:
            raise ResumeIntegrityError(
                "resume provider checksum disagrees with the retained object digest",
                context={"key": key, "provider_checksum": checksum, "sha256": actual},
            )
        # A checkpoint alone is never provider authority: re-prove it from the retained
        # sidecar bytes on every resume.
        verify_provider_sidecar(
            key=key,
            object_sha256=actual,
            sidecar_path=Path(str(prior.get("provider_checksum_path") or "")),
            sidecar_sha256=str(prior.get("provider_checksum_sha256") or ""),
            sidecar_dir=sidecar_dir,
        )
        schema = tuple(str(item) for item in (prior.get("schema_fields") or ()))
        return SampleRecord(
            product=primary,
            products=products,
            family=family,
            symbol=symbol,
            regime=regime,
            url=url,
            key=key,
            sha256=actual,
            byte_size=int(dest.stat().st_size),
            reused_existing=True,
            provider_checksum=checksum,
            checksum_match=True,
            schema_kind=str(prior.get("schema_kind") or ""),
            schema_fields=schema,
            availability_semantics="source_object_listing_time_unknown",
            retrieval_time=str(prior.get("retrieval_time") or ""),
            content_path=str(dest),
        )

    if listed_size <= 0:
        raise SourceQualificationError(
            "cannot sample an object with unknown or zero listing size",
            context={"key": key},
        )

    provider_checksum: str | None = None
    checksum_source = "network"
    sidecar_path: Path | None = None
    sidecar_sha256: str | None = None
    if checksums is not None:
        evidence = checksums.lookup(key)
        if evidence is not None:
            provider_checksum = str(evidence["provider_checksum"])
            sidecar_path = Path(str(evidence["content_path"]))
            sidecar_sha256 = str(evidence["blob_sha256"])
            checksum_source = "retained_evidence"
    if provider_checksum is None:
        checksum_url = vision_object_url(f"{key}.CHECKSUM")
        try:
            # index.fetch_bytes owns its own bounded retry; wrapping it again here would
            # multiply the nominal per-request attempt bound.
            checksum_body = index.fetch_bytes(checksum_url)
        except SourceQualificationError as exc:
            raise SourceQualificationError(
                "provider checksum is required",
                context={"key": key},
            ) from exc
        provider_checksum = parse_provider_checksum(
            checksum_body.decode("utf-8", errors="replace")
        )
        if provider_checksum is None:
            raise SourceQualificationError(
                "provider checksum sidecar is missing or malformed",
                context={"key": key},
            )
        # Retain the sidecar content-addressably, including for in-memory indexes, so the
        # sample checkpoint can never outlive its provider evidence.
        sidecar_path, sidecar_sha256 = persist_provider_sidecar(
            checksum_body, sidecar_dir=sidecar_dir
        )
    if provider_checksum is None or sidecar_path is None or sidecar_sha256 is None:
        raise SourceQualificationError(
            "provider checksum sidecar is missing or malformed",
            context={"key": key},
        )

    retrieval_time = datetime.now(UTC).isoformat()
    if transport is not None:
        result = retry.run(
            f"sample:{key}",
            lambda: atomic_download(
                url,
                sample_dir,
                transport=transport,
                expected_sha256=provider_checksum,
                max_bytes=listed_size + 1024,
            ),
        )
        sha256 = result.sha256
        dest_path = result.dest_path
        reused = result.reused_existing
        payload = dest_path.read_bytes()
        retrieval_time = result.retrieval_utc.astimezone(UTC).isoformat()
    else:
        payload = index.fetch_bytes(url)
        sha256 = _object_sha256(payload)
        if sha256 != provider_checksum:
            raise SourceQualificationError(
                "provider checksum mismatch",
                context={"url": url, "expected": provider_checksum, "actual": sha256},
            )
        dest_path = content_addressed_path(sample_dir, sha256)
        if dest_path.exists():
            existing = compute_sha256(dest_path)
            if existing != sha256:
                raise SourceQualificationError(
                    "existing content-addressed object does not match new digest",
                    context={"path": str(dest_path)},
                )
            reused = True
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest_path.with_name(f".partial-{sha256}.part")
            tmp.write_bytes(payload)
            tmp.replace(dest_path)
            reused = False

    if compute_sha256(dest_path) != sha256:
        raise SourceQualificationError(
            "published sample failed post-write rehash",
            context={"key": key},
        )
    schema = infer_schema_fields(payload, name=key)
    # The sidecar must prove this exact object before the checkpoint can be written.
    verify_provider_sidecar(
        key=key,
        object_sha256=sha256,
        sidecar_path=sidecar_path,
        sidecar_sha256=sidecar_sha256,
        sidecar_dir=sidecar_dir,
    )
    # Checkpoint immediately: an interruption after this point must never lose the
    # object-to-digest, checksum, schema, and provenance evidence already proven.
    checkpoint.record(
        key,
        {
            "status": "complete",
            "sha256": sha256,
            "byte_size": len(payload),
            "url": url,
            "provider_checksum": provider_checksum,
            "checksum_match": True,
            "schema_kind": schema.kind,
            "schema_fields": list(schema.fields),
            "retrieval_time": retrieval_time,
            "provider_checksum_source": checksum_source,
            "provider_checksum_path": str(sidecar_path),
            "provider_checksum_sha256": sidecar_sha256,
        },
    )
    return SampleRecord(
        product=primary,
        products=products,
        family=family,
        symbol=symbol,
        regime=regime,
        url=url,
        key=key,
        sha256=sha256,
        byte_size=len(payload),
        reused_existing=reused,
        provider_checksum=provider_checksum,
        checksum_match=True,
        schema_kind=schema.kind,
        schema_fields=schema.fields,
        availability_semantics="source_object_listing_time_unknown",
        retrieval_time=retrieval_time,
        content_path=str(dest_path),
    )


def family_product_map(
    archive_families: Mapping[str, tuple[str, ...]] = OFFICIAL_ARCHIVE_FAMILIES,
) -> dict[str, tuple[str, ...]]:
    """Physical family -> every logical product that derives rows from it."""
    mapping: dict[str, list[str]] = {}
    for product in sorted(archive_families):
        for family in archive_families[product]:
            mapping.setdefault(family, []).append(product)
    return {family: tuple(sorted(products)) for family, products in mapping.items()}


def run_source_qualification(
    *,
    store_root: Path,
    index: ObjectIndex,
    transport: HttpTransport | None = None,
    progress_path: Path | None = None,
    current_contracts: CurrentContractSource | None = None,
    coinalyze_transport: CoinalyzeTransport | None = None,
    coinalyze_api_key: str | None = None,
    max_symbols: int | None = None,
    current_listing_only: bool = False,
    symbol_allowlist: Sequence[str] | None = None,
    now: datetime | None = None,
    coinalyze_from_ts: int = 1_577_836_800,
    coinalyze_to_ts: int = 1_609_459_200,
    retry: RetryRunner | None = None,
    listing_checkpoint: ListingCheckpointStore | None = None,
    sample_budget_bytes: int = GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    max_sample_object_bytes: int = GATE1_MAX_NEW_OBJECT_BYTES,
) -> QualificationReport:
    refuse_restricted_scope(
        max_symbols=max_symbols,
        current_listing_only=current_listing_only,
        symbol_allowlist=symbol_allowlist,
    )
    generated_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    store = Path(store_root)
    sample_dir = store / "raw" / "sha256"
    sample_dir.mkdir(parents=True, exist_ok=True)
    list_cache_dir = store / "list_cache"
    progress_file = progress_path or (store / "cex002_qualification_progress.json")
    plan_path = store / "cex002_sample_plan.json"
    retry_journal_path = store / "cex002_retry_journal.json"
    retry_runner = retry or RetryRunner()
    if retry_runner.journal is None:
        retry_runner.journal = RetryJournal.load(retry_journal_path)
    checkpoint = SampleCheckpointStore.load(progress_file, sidecar_dir=list_cache_dir)
    checksums = RetainedChecksumIndex.from_cache(list_cache_dir)

    # 1. Inventory every unique physical family exactly once.
    inventory = build_family_inventory(index)
    discovered = inventory_symbols(inventory)
    family_products = family_product_map()
    family_object_counts: dict[str, int] = {
        family: sum(len(objs) for objs in entry.objects.values())
        for family, entry in inventory.items()
    }

    current_authenticated = False
    current: tuple[str, ...] = ()
    if current_contracts is not None:
        payload = retry_runner.run(
            "fapi:exchangeInfo", current_contracts.fetch_exchange_info
        )
        current = tuple(parse_current_perpetuals(payload))
        current_authenticated = True
    current_set = set(current)
    delisted = tuple(sym for sym in discovered if current_set and sym not in current_set)
    unarchived = tuple(sym for sym in current if sym not in set(discovered))

    sample_symbols = _sample_symbol_set(discovered, delisted)
    sample_symbol_set = set(sample_symbols)

    incidents: list[dict[str, Any]] = []
    product_incident_counts: dict[str, int] = {product: 0 for product in REQUIRED_PRODUCTS}
    for family in sorted(inventory):
        for item in inventory[family].incidents:
            for product in family_products.get(family, ()):
                incidents.append({"product": product, **dict(item)})
                product_incident_counts[product] = product_incident_counts.get(product, 0) + 1

    # 2. Recover already retained, checksum-proven sample bytes before planning so they
    #    never consume the new-download budget and are never fetched again.
    candidate_keys: list[str] = []
    for family, entry in sorted(inventory.items()):
        if not family_products.get(family):
            continue
        for symbol in entry.symbols:
            if symbol not in sample_symbol_set:
                continue
            candidate_keys.extend(obj.key for obj in entry.objects.get(symbol, ()))
    recover_retained_samples(
        sample_dir=sample_dir,
        sidecar_dir=list_cache_dir,
        checksums=checksums,
        checkpoint=checkpoint,
        keys=candidate_keys,
    )
    retained_keys: dict[str, int] = {}
    for key in candidate_keys:
        entry_row = checkpoint.get(key)
        if entry_row and entry_row.get("status") == "complete":
            retained_keys[key] = int(entry_row.get("byte_size") or 0)

    # 3. Produce and persist the deterministic sample plan before any new download.
    plan = build_sample_plan(
        inventory=inventory,
        family_products=family_products,
        sample_symbols=sample_symbols,
        delisted=delisted,
        retained_keys=retained_keys,
        budget_bytes=sample_budget_bytes,
        max_object_bytes=max_sample_object_bytes,
    )
    _atomic_write_json(plan_path, plan.to_dict())

    # 4. Acquire only planned samples. Each physical object is fetched at most once and
    #    attributed to every logical product that declares its family.
    samples: list[SampleRecord] = []
    acquired: dict[str, SampleRecord] = {}
    for planned in plan.entries:
        if planned.action == "blocked":
            continue
        already = acquired.get(planned.key)
        if already is not None:
            # Regime/product alias of an object already proven in this run.
            samples.append(
                replace(
                    already,
                    regime=planned.regime,
                    products=planned.products,
                    product=planned.products[0] if planned.products else already.product,
                )
            )
            continue
        try:
            record = _acquire_sample(
                key=planned.key,
                listed_size=planned.byte_size,
                products=planned.products,
                family=planned.family,
                symbol=planned.symbol,
                regime=planned.regime,
                sample_dir=sample_dir,
                sidecar_dir=list_cache_dir,
                index=index,
                transport=transport,
                checkpoint=checkpoint,
                checksums=checksums,
                retry=retry_runner,
            )
        except ResumeIntegrityError:
            raise
        except SourceQualificationError as exc:
            for product in planned.products:
                incidents.append(
                    {
                        "product": product,
                        "family": planned.family,
                        "symbol": planned.symbol,
                        "regime": planned.regime,
                        "kind": "sample_error",
                        "note": str(exc),
                    }
                )
                product_incident_counts[product] = product_incident_counts.get(product, 0) + 1
            continue
        acquired[planned.key] = record
        samples.append(record)

    for item in plan.blocked:
        for product in item.get("products", ()):
            incidents.append(
                {
                    "product": product,
                    "family": item.get("family"),
                    "symbol": item.get("symbol"),
                    "regime": item.get("regime"),
                    "kind": SAMPLE_BUDGET_BLOCK,
                    "note": (
                        f"required object {item.get('required_key')} of "
                        f"{item.get('required_bytes')} bytes exceeds the Gate 1 new-download budget"
                    ),
                }
            )

    # 5. Derive every logical product row from the shared inventory.
    matrix_rows: list[ProductMatrixRow] = []
    symbol_coverage: dict[str, dict[str, int]] = {}

    for product in REQUIRED_PRODUCTS:
        families = OFFICIAL_ARCHIVE_FAMILIES.get(product, ())
        family_symbols: set[str] = set()
        listed_objects = 0
        listed_bytes = 0
        unknown_sizes = False
        product_incidents = product_incident_counts.get(product, 0)
        family_listed: dict[str, int] = {}
        family_symbol_lists: dict[str, set[str]] = {}
        family_symbol_objects: dict[tuple[str, str], int] = {}

        for family in families:
            entry = inventory.get(family)
            if entry is None or not entry.listed:
                continue
            family_listed.setdefault(family, 0)
            family_symbols.update(entry.symbols)
            family_symbol_lists[family] = set(entry.symbols)
            for symbol in entry.symbols:
                objs = entry.objects.get(symbol)
                if objs is None:
                    family_symbol_objects[(family, symbol)] = 0
                    continue
                family_symbol_objects[(family, symbol)] = len(objs)
                listed_objects += len(objs)
                family_listed[family] = family_listed.get(family, 0) + len(objs)
                for obj in objs:
                    if obj.size is None:
                        unknown_sizes = True
                    else:
                        listed_bytes += int(obj.size)

        if product == "binance_usdm_perpetual_membership":
            family_symbols = set(discovered)
            listed_objects = len(discovered)

        # Account the full discovered universe, not only symbols already listed under a
        # family: a universe member with no prefix is a recorded zero, not an omission.
        for family in families:
            if family not in family_symbol_lists:
                continue
            for symbol in discovered:
                family_symbol_objects.setdefault((family, symbol), 0)

        uncovered = _uncovered_listed_symbols(family_symbol_lists, family_symbol_objects)
        universe_gaps, uncovered_universe = _universe_coverage_gaps(
            discovered,
            families,
            family_symbol_lists,
            family_symbol_objects,
            require_every_group=product != "binance_usdm_perpetual_membership",
        )
        symbol_coverage[product] = {
            f"{family}/{symbol}": count
            for (family, symbol), count in sorted(family_symbol_objects.items())
        }
        product_sample_rows = [item for item in samples if product in item.products]
        product_samples = len(product_sample_rows)
        budget_blocked = tuple(
            dict(item) for item in plan.blocked if product in tuple(item.get("products", ()))
        )
        checksum_ok = bool(product_sample_rows) and all(
            item.checksum_match and item.provider_checksum for item in product_sample_rows
        )
        source_gate = product not in DERIVED_PRODUCTS
        if product in DERIVED_PRODUCTS:
            authority = SourceAuthority.UNSUPPORTED
            complete = False
            reason = "derived output; excluded from the source gate"
        elif product == "binance_usdm_liquidation_observed":
            authority = SourceAuthority.INACCESSIBLE
            complete = False
            reason = (
                "official Vision has no liquidation archive; Coinalyze daily history is "
                "required as an observed/censored secondary source"
            )
        elif product == "binance_usdm_perpetual_membership":
            complete = (
                bool(discovered)
                and current_authenticated
                and product_incidents == 0
                and not uncovered_universe
            )
            authority = SourceAuthority.OFFICIAL if complete else SourceAuthority.SAMPLE_ONLY
            reason = HISTORICAL_PERPETUAL_RULE
            membership_notes = _coverage_gap_notes(uncovered, uncovered_universe)
            if not complete and membership_notes:
                reason = f"{reason} {membership_notes}"
        elif product == "binance_usdm_cost_calibration":
            ticker = family_object_counts.get("monthly/bookTicker", 0) + family_object_counts.get(
                "daily/bookTicker", 0
            )
            depth = family_object_counts.get("monthly/bookDepth", 0) + family_object_counts.get(
                "daily/bookDepth", 0
            )
            complete = (
                ticker > 0
                and depth > 0
                and checksum_ok
                and not unknown_sizes
                and product_incidents == 0
                and _declared_families_present(families, family_listed)
                and not uncovered
                and not uncovered_universe
            )
            authority = SourceAuthority.OFFICIAL if complete else SourceAuthority.SAMPLE_ONLY
            reason = (
                "cost calibration requires official bookTicker and bookDepth inventory"
            )
            cost_notes = _coverage_gap_notes(uncovered, uncovered_universe)
            if not complete and cost_notes:
                reason = f"{reason}; {cost_notes}"
            if not complete and budget_blocked:
                reason = f"{reason}; {SAMPLE_BUDGET_BLOCK}"
        else:
            complete = (
                listed_objects > 0
                and checksum_ok
                and not unknown_sizes
                and product_incidents == 0
                and _declared_families_present(families, family_listed)
                and product_samples > 0
                and not uncovered
                and not uncovered_universe
            )
            if listed_objects == 0:
                authority = SourceAuthority.INACCESSIBLE
                reason = "official Vision listing is empty for this product"
            elif not complete:
                authority = SourceAuthority.SAMPLE_ONLY
                reason = (
                    "official listing is incomplete: missing checksum, size, family, "
                    "sample evidence, or per-symbol object coverage"
                )
                gap_notes = _coverage_gap_notes(uncovered, uncovered_universe)
                if gap_notes:
                    reason = gap_notes
                if budget_blocked:
                    # Inventory is complete and the source is reachable; only the bounded
                    # Gate 1 sample budget is unmet.
                    reason = (
                        f"{SAMPLE_BUDGET_BLOCK}: bounded Gate 1 sample budget cannot "
                        f"cover required regime evidence; inventory is complete"
                    )
            else:
                authority = SourceAuthority.OFFICIAL
                reason = "official Vision archive listing, checksums, and retained samples"

        matrix_rows.append(
            ProductMatrixRow(
                product=product,
                authority=authority.value,
                official_complete=complete if source_gate else False,
                source_gate=source_gate,
                sample_only=authority is SourceAuthority.SAMPLE_ONLY,
                reason=reason,
                official_families=families,
                discovered_symbols=len(family_symbols) if family_symbols else len(discovered),
                sample_count=product_samples,
                listed_object_count=listed_objects,
                listed_bytes=None if unknown_sizes else listed_bytes,
                incidents=product_incidents,
                uncovered_listed_symbols=uncovered if source_gate else (),
                uncovered_universe_symbols=uncovered_universe if source_gate else (),
                universe_coverage_gaps=universe_gaps if source_gate else (),
                sample_budget_blocked=budget_blocked if source_gate else (),
            )
        )

    coinalyze_block: dict[str, Any] = {
        "qualified": False,
        "key_present": bool(coinalyze_api_key),
        "reason": "Coinalyze transport or COINALYZE_API_KEY absent",
    }
    if coinalyze_transport is not None and coinalyze_api_key:
        try:
            client = CoinalyzeClient(
                coinalyze_transport, api_key=coinalyze_api_key, retry=retry_runner
            )
            coinalyze_block = client.qualify_binance_daily(
                native_symbols=sample_symbols[:2] or discovered[:1],
                from_ts=coinalyze_from_ts,
                to_ts=coinalyze_to_ts,
            )
            coinalyze_block["qualified"] = True
        except SourceQualificationError as exc:
            incidents.append(
                {
                    "product": "binance_usdm_liquidation_observed",
                    "kind": "coinalyze_error",
                    "note": str(exc),
                }
            )
            coinalyze_block = {
                "qualified": False,
                "key_present": True,
                "reason": str(exc),
            }

    if coinalyze_block.get("qualified"):
        rebuilt: list[ProductMatrixRow] = []
        for row in matrix_rows:
            if row.product != "binance_usdm_liquidation_observed":
                rebuilt.append(row)
                continue
            rebuilt.append(
                ProductMatrixRow(
                    product=row.product,
                    authority=SourceAuthority.SECONDARY.value,
                    official_complete=True,
                    source_gate=True,
                    sample_only=False,
                    reason=(
                        "Coinalyze daily Binance-perpetual liquidation/OI/funding/price "
                        f"history qualified as observed/censored secondary. {BINANCE_CENSORSHIP_NOTE}"
                    ),
                    official_families=row.official_families,
                    discovered_symbols=row.discovered_symbols,
                    sample_count=row.sample_count
                    + int(
                        sum(
                            item["points"]
                            for item in coinalyze_block["samples"]["liquidation"]
                        )
                    ),
                    listed_object_count=row.listed_object_count,
                    listed_bytes=row.listed_bytes,
                    incidents=row.incidents,
                    uncovered_listed_symbols=row.uncovered_listed_symbols,
                    uncovered_universe_symbols=row.uncovered_universe_symbols,
                    universe_coverage_gaps=row.universe_coverage_gaps,
                    sample_budget_blocked=row.sample_budget_blocked,
                )
            )
        matrix_rows = rebuilt

    samples_sorted = tuple(
        sorted(
            samples,
            key=lambda sample: (
                sample.product,
                sample.family,
                sample.symbol,
                sample.regime,
                sample.key,
            ),
        )
    )
    incidents_sorted = tuple(
        sorted(
            incidents,
            key=lambda item: (
                str(item.get("product", "")),
                str(item.get("family", "")),
                str(item.get("symbol", "")),
                str(item.get("kind", "")),
            ),
        )
    )
    blocked = tuple(
        row.product for row in matrix_rows if row.source_gate and not row.official_complete
    )
    accepted = len(blocked) == 0
    checkpoint.flush(
        updated_at=generated_at,
        discovered_symbol_count=len(discovered),
    )
    return QualificationReport(
        ticket=TICKET_ID,
        gate="gate_1_source_procurement",
        gate_status=GateStatus.QUALIFIED.value if accepted else GateStatus.BLOCKED.value,
        generated_at=generated_at,
        universe_source="official_vision_union_membership_listing",
        historical_perpetual_rule=HISTORICAL_PERPETUAL_RULE,
        discovered_symbols=tuple(discovered),
        current_perpetual_symbols=current,
        current_contracts_authenticated=current_authenticated,
        historical_or_delisted_candidates=delisted,
        current_unarchived=unarchived,
        product_matrix=tuple(matrix_rows),
        samples=samples_sorted,
        blocked_products=blocked,
        storage={
            "sample_store": str(sample_dir),
            "progress_path": str(progress_file),
            "sample_plan_path": str(plan_path),
            "retry_journal_path": str(retry_journal_path),
            "discovered_symbol_count": len(discovered),
            "object_count_exact": {row.product: row.listed_object_count for row in matrix_rows},
            "byte_count_exact": {row.product: row.listed_bytes for row in matrix_rows},
            "physical_family_object_counts": dict(sorted(family_object_counts.items())),
            "symbol_coverage": symbol_coverage,
            "universe_coverage_gaps": {
                row.product: [dict(item) for item in row.universe_coverage_gaps]
                for row in matrix_rows
                if row.universe_coverage_gaps
            },
            "note": "object and byte totals are full-family listings, not sample extrapolations",
        },
        licensing={
            "official_preferred": True,
            "purchase_authorized": False,
            "paid_source_authorized": False,
            "official_incremental_endpoints": dict(OFFICIAL_INCREMENTAL_ENDPOINTS),
            "policy": "no paid data purchase is authorized under this ticket",
        },
        incidents=incidents_sorted,
        resume={
            "progress_objects": len(checkpoint.objects),
            "reused_samples": sum(1 for item in samples if item.reused_existing),
            "recovered_samples": checkpoint.recovered,
            "rehash_required": True,
            "physical_families_inventoried": len(inventory),
        },
        sample_plan=plan.to_dict(),
        retry=retry_runner.to_dict(),
        listing_checkpoint=(
            listing_checkpoint.to_dict() if listing_checkpoint is not None else {}
        ),
        coinalyze=coinalyze_block,
        accepted=accepted,
    )


def accept_qualification(report: QualificationReport) -> None:
    if report.gate_status != GateStatus.QUALIFIED.value or not report.accepted:
        raise SourceQualificationError(
            "incomplete product matrix is refused",
            context={
                "gate_status": report.gate_status,
                "blocked_products": list(report.blocked_products),
            },
        )
    if report.blocked_products:
        raise SourceQualificationError(
            "blocked source products remain; universe/product scope may not shrink",
            context={"blocked_products": list(report.blocked_products)},
        )


def write_qualification_report(report: QualificationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
