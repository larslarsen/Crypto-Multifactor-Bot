"""CEX-002 Gate 1 — free-source qualification for Binance USD-M harmonic data.

Closes the fifteen review-61 defects: header/headerless schema identity, rehashed
resume, a real Coinalyze history client, ListObjectsV2 pagination, explicit 1m
selection, checksum-required completeness, no quote-label authority, source-gate
treatment of derived outputs, bookDepth+bookTicker cost inventory, authenticated
current-contract comparison, and a non-zero default exit on incomplete coverage.

Closes the review-64 residuals: coverage is accounted against the full evaluated
universe including symbols with no family prefix, and Coinalyze provenance is taken
from retained raw response bytes rather than a re-serialised parse.

Closes the review-75 findings: accepted perpetual membership requires affirmative
official evidence rather than an archive-name union; the sample plan is locked once and
replayed immutably against a cumulative, ledgered download budget; Gate 2 storage
feasibility is published as an exact deduplicated physical requirement against real
local capacity; source qualification is reported separately from universe/temporal
coverage; and Coinalyze qualifies on declared stable anchors with a separate
full-universe support map.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import re
import shutil
import time
import zipfile
from collections.abc import Callable, Collection, Mapping, Sequence
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
    "binance_usdm_bar_1h",
    "binance_usdm_trade_flow_1h",
    "binance_usdm_open_interest_5m",
    "binance_usdm_funding_realized",
    "binance_usdm_funding_indicative_1h",
    "binance_usdm_mark_index_basis_1h",
    "binance_usdm_liquidation_observed_daily",
    "binance_usdm_cost_calibration",
    "binance_usdm_coverage_gap",
    "binance_usdm_harmonic_bundle",
)

DERIVED_PRODUCTS: frozenset[str] = frozenset(
    {
        "binance_usdm_trade_flow_1h",
        "binance_usdm_coverage_gap",
        "binance_usdm_harmonic_bundle",
    }
)

SOURCE_PRODUCTS: tuple[str, ...] = tuple(
    product for product in REQUIRED_PRODUCTS if product not in DERIVED_PRODUCTS
)

# Explicit 1h selection for named kline families. Other intervals are ignored.
INTERVAL_REQUIRED_FAMILIES: dict[str, str] = {
    "monthly/klines": "1h",
    "daily/klines": "1h",
    "monthly/markPriceKlines": "1h",
    "daily/markPriceKlines": "1h",
    "monthly/indexPriceKlines": "1h",
    "daily/indexPriceKlines": "1h",
    "monthly/premiumIndexKlines": "1h",
    "daily/premiumIndexKlines": "1h",
}

# Listing these families discovers historical names. It does not select their objects.
DISCOVERY_ARCHIVE_FAMILIES: tuple[str, ...] = (
    "monthly/trades",
    "daily/trades",
    "monthly/aggTrades",
    "daily/aggTrades",
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
)

# Selected acquisition families for the Harmonic-ready release. Trades, aggregate trades,
# and full book archives remain discovery-only except the bounded daily cost sample.
OFFICIAL_ARCHIVE_FAMILIES: dict[str, tuple[str, ...]] = {
    "binance_usdm_perpetual_membership": (),
    "binance_usdm_bar_1h": ("monthly/klines", "daily/klines"),
    "binance_usdm_trade_flow_1h": ("monthly/klines", "daily/klines"),
    "binance_usdm_open_interest_5m": ("monthly/metrics", "daily/metrics"),
    "binance_usdm_funding_realized": ("monthly/fundingRate", "daily/fundingRate"),
    "binance_usdm_funding_indicative_1h": (
        "monthly/premiumIndexKlines",
        "daily/premiumIndexKlines",
    ),
    "binance_usdm_mark_index_basis_1h": (
        "monthly/markPriceKlines",
        "daily/markPriceKlines",
        "monthly/indexPriceKlines",
        "daily/indexPriceKlines",
        "monthly/premiumIndexKlines",
        "daily/premiumIndexKlines",
    ),
    "binance_usdm_cost_calibration": ("daily/bookTicker", "daily/bookDepth"),
}

COST_SAMPLE_FAMILIES: tuple[str, ...] = ("daily/bookTicker", "daily/bookDepth")
KLINE_TAKER_FLOW_FIELDS: tuple[str, ...] = (
    "volume",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
)
UNSELECTED_DISCOVERY_FAMILIES: frozenset[str] = frozenset(
    {
        "monthly/trades",
        "daily/trades",
        "monthly/aggTrades",
        "daily/aggTrades",
        "monthly/bookTicker",
        "monthly/bookDepth",
    }
)

MEMBERSHIP_FAMILY_PREFIXES: tuple[str, ...] = DISCOVERY_ARCHIVE_FAMILIES

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

# Gate 1 is bounded source qualification, not acquisition. The architecture-amendment
# ceiling is a separately ledgered total for new sample bytes; there is no independent
# per-object cap. An object that cannot fit the remaining allowance is reported with its
# exact size and blocks.
GATE1_NEW_DOWNLOAD_BUDGET_BYTES: int = 268_435_456
GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES: int = 268_435_456
GATE1_MAX_NEW_OBJECT_BYTES: int = GATE1_NEW_DOWNLOAD_BUDGET_BYTES
SAMPLE_BUDGET_BLOCK: str = "sample_budget_exceeded"

# A monthly package is canonical only once its provider checksum is officially listed.
# Anything else is quarantined provenance and its interval falls back to daily objects.
# A listed sidecar path is selection evidence, not proof. Only a rehashed retained
# object with a re-proved provider sidecar is checksum-proved and consumable.
INTEGRITY_SIDECAR_LISTED: str = "sidecar_listed"
INTEGRITY_SIDECAR_ABSENT: str = "sidecar_absent"
INTEGRITY_CHECKSUM_PROVED: str = "checksum_proved_retained"
INTEGRITY_QUARANTINED: str = "quarantined"
VALIDATION_PENDING: str = "raw_validation_pending"
VALIDATION_PROVED: str = "checksum_proved_retained"
MANIFEST_MONTHLY_REJECTED: str = "monthly_integrity_rejected"
MANIFEST_DAILY_FALLBACK: str = "daily_fallback_for_rejected_month"
MANIFEST_INTEGRITY_MISSING: str = "integrity_authority_missing"
MANIFEST_OVERLAP: str = "overlapping_selected_coverage"

# Durable identities that are never migrated by a candidate-only phase.
AMENDMENT_LEDGER_FILENAME: str = "cex002_amendment_ledger.json"
AMENDMENT_LEDGER_ID: str = "cex002_architecture_amendment_v3"
HOLDOUT_BOUNDARY_FILENAME: str = "cex002_holdout_boundary.json"
HOLDOUT_REPLAY_RULE: str = (
    "the pinned boundary is the first authenticated qualification instant; every later "
    "run replays it unchanged, and no model outcome may move it"
)
CANDIDATE_PLAN_VERSION: int = 3
REQUIRED_PRIOR_PLAN_VERSION: int = 2
CHECKPOINT_VERSION: int = 1

# Transient transport/service failures are retried; integrity and authentication
# failures are terminal and must never be retried.
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504, 509})
TERMINAL_STATUS_CODES: frozenset[int] = frozenset({400, 401, 403, 404, 405, 410})

HISTORICAL_PERPETUAL_RULE: str = (
    "Archive directory names are the historical observation set, never a contract-type "
    "proof. Accepted membership requires affirmative official evidence: an authenticated "
    "current exchangeInfo row with contractType=PERPETUAL, a retained official historical "
    "contract-metadata row with that exact type, or an official realized-funding "
    "observation, which only a perpetual contract produces. Delivery contracts, "
    "TRADIFI_PERPETUAL contracts, settlement artifacts, and unresolved archive-only "
    "candidates are reported separately and excluded; unresolved candidates block "
    "membership. Current PERPETUAL names absent from archives are current_unarchived. "
    "No archive name is promoted or excluded from spelling alone."
)

# --- review-75 membership authority --------------------------------------------------

PERPETUAL_CONTRACT_TYPE: str = "PERPETUAL"
TRADIFI_CONTRACT_TYPES: frozenset[str] = frozenset({"TRADIFI_PERPETUAL"})
TRADIFI_UNDERLYING_TYPES: frozenset[str] = frozenset({"TRADIFI"})
# Official USD-M delivery enums. A row carrying one of these is affirmative evidence that
# the contract is NOT a perpetual, which resolves the candidate instead of blocking it.
DELIVERY_CONTRACT_TYPES: frozenset[str] = frozenset(
    {
        "CURRENT_MONTH",
        "NEXT_MONTH",
        "CURRENT_QUARTER",
        "NEXT_QUARTER",
        "CURRENT_QUARTER_DELIVERING",
        "NEXT_QUARTER_DELIVERING",
        "PERPETUAL_DELIVERING",
    }
)
# Only a perpetual contract realizes funding, so an official fundingRate archive object is
# affirmative perpetual evidence for the symbol that owns it.
FUNDING_EVIDENCE_FAMILIES: tuple[str, ...] = ("monthly/fundingRate", "daily/fundingRate")

MEMBERSHIP_CONFIRMED: str = "confirmed_perpetual"
MEMBERSHIP_DELIVERY: str = "delivery_non_perpetual"
MEMBERSHIP_TRADIFI: str = "tradifi_perpetual"
MEMBERSHIP_SETTLEMENT_ARTIFACT: str = "settlement_artifact_candidate"
MEMBERSHIP_DATED_DELIVERY: str = "dated_delivery_candidate"
MEMBERSHIP_UNRESOLVED: str = "unresolved_archive_candidate"
MEMBERSHIP_UNSUPPORTED_SEMANTICS: str = "unsupported_contract_semantics"
# Unresolved classes block membership; they are never silently dropped from the report.
MEMBERSHIP_BLOCKING_CLASSES: frozenset[str] = frozenset(
    {
        MEMBERSHIP_SETTLEMENT_ARTIFACT,
        MEMBERSHIP_DATED_DELIVERY,
        MEMBERSHIP_UNRESOLVED,
        MEMBERSHIP_UNSUPPORTED_SEMANTICS,
    }
)

# Name shapes are audit hints only. They never promote a name into membership and never
# exclude one from the report; an unresolved candidate blocks whatever its spelling is.
_DATED_DELIVERY_NAME_RE = re.compile(r"^[A-Z0-9]+_\d{6}$")
_SETTLEMENT_NAME_RE = re.compile(r"SETTLED")

# --- review-75 immutable planning, cumulative budget, storage feasibility -------------

PLAN_CONTRACT_VERSION: int = 3
SAMPLE_PLAN_LOCK_FILENAME: str = "cex002_sample_plan_lock.json"
BUDGET_LEDGER_FILENAME: str = "cex002_budget_ledger.json"
CONTRACT_METADATA_FILENAME: str = "cex002_official_contract_metadata.json"
CONTRACT_SNAPSHOT_DIRNAME: str = "fapi_snapshots"
LEGACY_BUDGET_UNRESOLVED: str = "legacy_budget_accounting_unresolved"
PLAN_INPUTS_CHANGED: str = "plan_inputs_changed"
GATE2_STORAGE_BLOCK: str = "gate2_storage_insufficient"
GATE2_STORAGE_INCIDENT_NOTE: str = (
    "local capacity is insufficient for the deduplicated compressed-raw requirement; "
    "exact execution-plane values are in storage.gate2_feasibility"
)

# Coinalyze qualification anchors are declared, not derived from an alphabetical edge of
# the discovered universe. Both must be confirmed Binance perpetuals first.
COINALYZE_ANCHOR_SYMBOLS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")

# --- review-75 separated source and coverage states -----------------------------------

SOURCE_STATE_OFFICIAL: str = "official_qualified"
SOURCE_STATE_TYPED_GAPS: str = "qualified_with_typed_gaps"
SOURCE_STATE_SECONDARY: str = "secondary_qualified"
SOURCE_STATE_INACCESSIBLE: str = "inaccessible"
SOURCE_STATE_INTEGRITY: str = "schema_integrity_failure"
SOURCE_STATE_MEMBERSHIP: str = "membership_unresolved"
SOURCE_STATE_SAMPLE_PENDING: str = "sample_evidence_pending"
SOURCE_STATE_DERIVED: str = "derived_excluded"
QUALIFIED_SOURCE_STATES: frozenset[str] = frozenset(
    {SOURCE_STATE_OFFICIAL, SOURCE_STATE_TYPED_GAPS, SOURCE_STATE_SECONDARY}
)

COVERAGE_COMPLETE: str = "complete"
COVERAGE_TYPED_GAPS: str = "typed_gaps"
COVERAGE_BLOCKING_GAPS: str = "blocking_gaps"
COVERAGE_UNRESOLVED_MEMBERSHIP: str = "unresolved_membership"
COVERAGE_NOT_APPLICABLE: str = "not_applicable"

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
        "progress_objects",
        "observed_at",
        "retained_contract_metadata_rows",
        "retained_contract_snapshots",
        "response_content_path",
        "response_sha256",
        "response_byte_size",
        "server_time_ms",
        "unverified_retained_sample_keys",
        # Environment and execution plane: local free space, retained credit, and the
        # plan/budget bookkeeping are not part of what was qualified.
        "gate2_feasibility",
        "plan_lock",
        "budget",
    }
)


class SourceAuthority(str, Enum):
    OFFICIAL = "official"
    SECONDARY = "secondary"
    SAMPLE_ONLY = "sample_only"
    INACCESSIBLE = "inaccessible"
    UNSUPPORTED = "unsupported"
    MEMBERSHIP_UNRESOLVED = "membership_unresolved"
    SAMPLE_PENDING = "sample_evidence_pending"


# An official source keeps official authority while it carries typed coverage gaps; only
# an integrity or access failure withdraws it.
SOURCE_STATE_AUTHORITY: dict[str, SourceAuthority] = {
    SOURCE_STATE_OFFICIAL: SourceAuthority.OFFICIAL,
    SOURCE_STATE_TYPED_GAPS: SourceAuthority.OFFICIAL,
    SOURCE_STATE_SECONDARY: SourceAuthority.SECONDARY,
    SOURCE_STATE_INACCESSIBLE: SourceAuthority.INACCESSIBLE,
    SOURCE_STATE_INTEGRITY: SourceAuthority.SAMPLE_ONLY,
    SOURCE_STATE_MEMBERSHIP: SourceAuthority.MEMBERSHIP_UNRESOLVED,
    SOURCE_STATE_SAMPLE_PENDING: SourceAuthority.SAMPLE_PENDING,
    SOURCE_STATE_DERIVED: SourceAuthority.UNSUPPORTED,
}


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


@dataclass(frozen=True, slots=True)
class ExchangeInfoResponse:
    """One authenticated exchangeInfo fetch with its retained raw bytes and identity.

    A parsed mapping alone can never be re-proved later. Retaining the raw response
    content-addressably lets every reuse rehash and reparse the exact bytes the rows came
    from instead of trusting a copied field.
    """

    endpoint: str
    payload: Mapping[str, Any]
    raw_bytes: bytes
    sha256: str
    byte_size: int
    retrieval_time: str
    content_path: str


class CurrentContractSource(Protocol):
    def fetch_exchange_info(self) -> ExchangeInfoResponse: ...


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
    """Fixture contract source that retains real raw response bytes, not a parse."""

    payload: Mapping[str, Any]
    endpoint: str = OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"]
    retrieved_at: str = "1970-01-01T00:00:00+00:00"

    def fetch_exchange_info(self) -> ExchangeInfoResponse:
        raw = json.dumps(dict(self.payload), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return ExchangeInfoResponse(
            endpoint=self.endpoint,
            payload=json.loads(raw.decode("utf-8")),
            raw_bytes=raw,
            sha256=_object_sha256(raw),
            byte_size=len(raw),
            retrieval_time=self.retrieved_at,
            content_path="",
        )


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
    # ``listed_*`` count the full archive union, including excluded and unresolved names.
    # The accepted-universe totals below are the scope the coverage state evaluates.
    accepted_universe_object_count: int = 0
    accepted_universe_listed_bytes: int | None = None
    # Derived products carry the release state they inherit from their source product.
    release_blocked_derived: bool | None = None
    # Source authenticity/schema/checksum/access is judged separately from how much of
    # the universe and timeline the source happens to cover.
    source_qualification_state: str = ""
    coverage_state: str = ""
    release_blocked: bool = True
    typed_gap_symbols: tuple[str, ...] = ()
    coverage_gap_kinds: tuple[str, ...] = ()


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
    membership: Mapping[str, Any] = field(default_factory=dict)
    accepted_universe: tuple[str, ...] = ()
    plan_lock: Mapping[str, Any] = field(default_factory=dict)
    budget: Mapping[str, Any] = field(default_factory=dict)
    candidate_plan: Mapping[str, Any] = field(default_factory=dict)
    prospective_holdout: Mapping[str, Any] = field(default_factory=dict)
    acquisition_manifest: Mapping[str, Any] = field(default_factory=dict)

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
    """Canonical Coinalyze perpetual identity for a Binance native symbol.

    Observed native forms are both unsuffixed (``BTCUSDT``) and already carrying
    ``_PERP`` (``AAVEUSD_PERP``). The provider label is that perpetual stem plus the
    exchange code; a second ``_PERP`` is never inserted.
    """
    stem = native.strip().upper()
    if not stem.endswith("_PERP"):
        stem = f"{stem}_PERP"
    return f"{stem}.{COINALYZE_EXCHANGE_CODE}"


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
    # Object keys whose ``.CHECKSUM`` sibling is officially listed. Selection needs this
    # to tell a canonical monthly package from unproved provenance.
    checksum_keys: frozenset[str] = frozenset()

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
        checksum_keys: set[str] = set()
        for symbol in symbols:
            try:
                listed_objects = _list_objects_for_symbol(index, family, prefix, symbol)
                checksum_keys.update(
                    item.key[: -len(".CHECKSUM")]
                    for item in listed_objects
                    if item.key.endswith(".CHECKSUM")
                )
                objs = [
                    obj for obj in listed_objects if not obj.key.endswith(".CHECKSUM")
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
            checksum_keys=frozenset(checksum_keys),
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
    cumulative_spent_before_bytes: int = 0
    allowance_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [
                {**asdict(entry), "products": list(entry.products)} for entry in self.entries
            ],
            "blocked": [dict(item) for item in self.blocked],
            "new_download_bytes": self.new_download_bytes,
            "retained_bytes": self.retained_bytes,
            "budget_bytes": self.budget_bytes,
            "max_object_bytes": self.max_object_bytes,
            "unique_new_objects": self.unique_new_objects,
            "unique_retained_objects": self.unique_retained_objects,
            "cumulative_spent_before_bytes": self.cumulative_spent_before_bytes,
            "allowance_bytes": self.allowance_bytes,
            "note": (
                "Gate 1 execution budget for new downloads only; it never truncates, "
                "rejects, or miscounts larger source objects. The budget is cumulative "
                "across every invocation, not per invocation"
            ),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SamplePlan:
        """Rebuild a locked plan exactly; a resume never re-selects its keys."""
        entries = payload.get("entries")
        blocked = payload.get("blocked")
        if not isinstance(entries, list) or not isinstance(blocked, list):
            raise ResumeIntegrityError(
                "locked sample plan is missing entries or blocked records"
            )
        rebuilt: list[SamplePlanEntry] = []
        for item in entries:
            if not isinstance(item, dict):
                raise ResumeIntegrityError("locked sample plan entry is not an object")
            try:
                rebuilt.append(
                    SamplePlanEntry(
                        family=str(item["family"]),
                        symbol=str(item["symbol"]),
                        regime=str(item["regime"]),
                        products=tuple(str(name) for name in item["products"]),
                        key=str(item["key"]),
                        url=str(item["url"]),
                        byte_size=int(item["byte_size"]),
                        action=str(item["action"]),
                        block_reason=str(item.get("block_reason") or ""),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ResumeIntegrityError(
                    "locked sample plan entry is malformed", context={"entry": str(item)[:200]}
                ) from exc
        return cls(
            entries=tuple(rebuilt),
            blocked=tuple(dict(item) for item in blocked),
            new_download_bytes=int(payload.get("new_download_bytes") or 0),
            retained_bytes=int(payload.get("retained_bytes") or 0),
            budget_bytes=int(payload.get("budget_bytes") or 0),
            max_object_bytes=int(payload.get("max_object_bytes") or 0),
            unique_new_objects=int(payload.get("unique_new_objects") or 0),
            unique_retained_objects=int(payload.get("unique_retained_objects") or 0),
            cumulative_spent_before_bytes=int(
                payload.get("cumulative_spent_before_bytes") or 0
            ),
            allowance_bytes=int(payload.get("allowance_bytes") or 0),
        )


def build_sample_plan(
    *,
    inventory: Mapping[str, FamilyInventory],
    family_products: Mapping[str, tuple[str, ...]],
    sample_symbols: Sequence[str],
    delisted: Sequence[str],
    retained_keys: Mapping[str, int],
    budget_bytes: int = GATE1_NEW_DOWNLOAD_BUDGET_BYTES,
    max_object_bytes: int = GATE1_MAX_NEW_OBJECT_BYTES,
    cumulative_spent_bytes: int = 0,
    required_objects: Sequence[tuple[str, str, ListingObject, tuple[str, ...]]] = (),
) -> SamplePlan:
    """Plan every sample before downloading, choosing the smallest adequate objects.

    Already retained, verified objects never consume the new-download budget. The budget
    is cumulative: bytes already spent by earlier invocations reduce this plan's
    allowance, so no new byte can be planned once the total allowance is exhausted. When
    no candidate can fit, the regime is emitted as a typed ``sample_budget_exceeded``
    block carrying the required object identity and size instead of being silently
    dropped.
    """
    allowance = max(int(budget_bytes) - int(cumulative_spent_bytes), 0)
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

    def _plan_required(obj: ListingObject, family: str, symbol: str, products: tuple[str, ...]) -> None:
        nonlocal spent, retained_total
        size = int(obj.size) if obj.size is not None else 0
        if obj.key in emitted:
            entries.append(
                SamplePlanEntry(
                    family=family,
                    symbol=symbol,
                    regime="cost_sample",
                    products=products,
                    key=obj.key,
                    url=vision_object_url(obj.key),
                    byte_size=size,
                    action="alias",
                )
            )
            return
        if obj.key in retained_keys:
            retained_seen.add(obj.key)
            retained_total += retained_keys[obj.key]
            emitted.add(obj.key)
            entries.append(
                SamplePlanEntry(
                    family=family,
                    symbol=symbol,
                    regime="cost_sample",
                    products=products,
                    key=obj.key,
                    url=vision_object_url(obj.key),
                    byte_size=size,
                    action="reuse_retained",
                )
            )
            return
        if size <= 0 or spent + size > allowance:
            blocked.append(
                {
                    "kind": SAMPLE_BUDGET_BLOCK,
                    "family": family,
                    "symbol": symbol,
                    "regime": "cost_sample",
                    "products": list(products),
                    "required_key": obj.key,
                    "required_bytes": size,
                    "max_object_bytes": None,
                    "budget_bytes": budget_bytes,
                    "cumulative_spent_before_bytes": int(cumulative_spent_bytes),
                    "allowance_bytes": allowance,
                    "budget_remaining_bytes": max(allowance - spent, 0),
                }
            )
            entries.append(
                SamplePlanEntry(
                    family=family,
                    symbol=symbol,
                    regime="cost_sample",
                    products=products,
                    key=obj.key,
                    url=vision_object_url(obj.key),
                    byte_size=size,
                    action="blocked",
                    block_reason=SAMPLE_BUDGET_BLOCK,
                )
            )
            return
        spent += size
        emitted.add(obj.key)
        entries.append(
            SamplePlanEntry(
                family=family,
                symbol=symbol,
                regime="cost_sample",
                products=products,
                key=obj.key,
                url=vision_object_url(obj.key),
                byte_size=size,
                action="download",
            )
        )

    for family, symbol, obj, products in required_objects:
        _plan_required(obj, family, symbol, products)

    for family in sorted(inventory):
        products = family_products.get(family, ())
        if not products or family in COST_SAMPLE_FAMILIES:
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
                    if size <= 0:
                        continue
                    if spent + size > allowance:
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
                            "cumulative_spent_before_bytes": int(cumulative_spent_bytes),
                            "allowance_bytes": allowance,
                            "budget_remaining_bytes": max(allowance - spent, 0),
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
        cumulative_spent_before_bytes=int(cumulative_spent_bytes),
        allowance_bytes=allowance,
    )


@dataclass(frozen=True, slots=True)
class PlanInputs:
    """Every input that may change which objects a Gate 1 plan selects."""

    inventory_digest: str
    listing_digest: str
    membership_digest: str
    code_config_digest: str
    budget_digest: str
    retained_digest: str

    def to_dict(self) -> dict[str, str]:
        return {
            "inventory_digest": self.inventory_digest,
            "listing_digest": self.listing_digest,
            "membership_digest": self.membership_digest,
            "code_config_digest": self.code_config_digest,
            "budget_digest": self.budget_digest,
            "retained_digest": self.retained_digest,
        }

    def digest(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def differences(self, other: Mapping[str, Any]) -> tuple[str, ...]:
        return tuple(
            name
            for name, value in sorted(self.to_dict().items())
            if str(other.get(name) or "") != value
        )


def _digest_of(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def inventory_digest(inventory: Mapping[str, FamilyInventory]) -> str:
    """Digest of the complete listing evidence: family, listed state, key, size, etag."""
    payload = {
        family: {
            "listed": entry.listed,
            "symbols": list(entry.symbols),
            "objects": {
                symbol: [[obj.key, obj.size, obj.etag] for obj in objects]
                for symbol, objects in sorted(entry.objects.items())
            },
        }
        for family, entry in sorted(inventory.items())
    }
    return _digest_of(payload)


# Fields that describe what a contract is, as opposed to when or from which fetch it was
# observed. Only these bind the immutable plan and the semantic report identity.
_STABLE_EVIDENCE_FIELDS: frozenset[str] = frozenset(
    {
        "kind",
        "endpoint",
        "symbol",
        "pair",
        "contract_type",
        "status",
        "underlying_type",
        "base_asset",
        "quote_asset",
        "margin_asset",
        "onboard_ms",
        "delivery_ms",
        "closed_observed_ms",
        "semantics_state",
        "families",
        "example_key",
        "semantics",
    }
)


def membership_evidence_digest(classifications: Sequence[MembershipClassification]) -> str:
    """Digest of every classification together with the evidence identity behind it."""
    payload = [
        {
            "symbol": item.symbol,
            "class": item.membership_class,
            "in_archive": item.in_archive,
            "in_current_exchange": item.in_current_exchange,
            "name_pattern_hint": item.name_pattern_hint,
            # Stable canonical semantics only. Every material identity, class, enum and
            # lifecycle change moves this digest and blocks the locked plan, while a new
            # response time or raw-response digest over identical rows does not.
            "evidence": [
                {
                    key: value
                    for key, value in sorted(record.items())
                    if key in _STABLE_EVIDENCE_FIELDS
                }
                for record in item.evidence
            ],
        }
        for item in classifications
    ]
    return _digest_of(payload)


def listing_authority_manifest(
    checkpoint: ListingCheckpointStore | None,
) -> list[dict[str, Any]]:
    """Stable manifest of every re-proved listing request and its raw response digest."""
    if checkpoint is None:
        return []
    manifest: list[dict[str, Any]] = []
    for key, entry in sorted(checkpoint.entries.items()):
        request = entry.get("request")
        manifest.append(
            {
                "request_key": key,
                "request": dict(request) if isinstance(request, Mapping) else {},
                "response_sha256": str(entry.get("response_sha256") or ""),
                "byte_size": int(entry.get("byte_size") or 0),
            }
        )
    return manifest


def listing_authority_digest(checkpoint: ListingCheckpointStore | None) -> str:
    return _digest_of(listing_authority_manifest(checkpoint))


def executed_code_identity() -> dict[str, str]:
    """Identity of the source actually executing this plan, not a hand-kept version."""
    try:
        module_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError:
        module_sha256 = ""
    return {"module": Path(__file__).name, "module_sha256": module_sha256}


def plan_code_config_digest(*, budget_bytes: int, max_object_bytes: int) -> str:
    """Digest of the executed planning code plus its configuration."""
    _ = max_object_bytes
    return _digest_of(
        {
            "plan_contract_version": PLAN_CONTRACT_VERSION,
            "code": executed_code_identity(),
            "required_products": list(REQUIRED_PRODUCTS),
            "official_archive_families": {
                product: list(families)
                for product, families in sorted(OFFICIAL_ARCHIVE_FAMILIES.items())
            },
            "interval_required_families": dict(sorted(INTERVAL_REQUIRED_FAMILIES.items())),
            "discovery_archive_families": list(DISCOVERY_ARCHIVE_FAMILIES),
            "selected_acquisition_families": {
                product: list(families)
                for product, families in sorted(OFFICIAL_ARCHIVE_FAMILIES.items())
            },
            "cadence_selector": "monthly_preferred_daily_gap_tail_v1",
            "cost_sample": "first_midpoint_last_daily_book_v1",
            "regime_selector": "smallest_adequate_per_regime_v1",
            "budget_bytes": int(budget_bytes),
            "independent_object_cap_bytes": None,
        }
    )


def retained_evidence_snapshot(
    keys: Sequence[str],
    retained_objects: Mapping[str, Mapping[str, Any]],
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    cache: dict[tuple[str, str], int | None] | None = None,
) -> dict[str, list[Any]]:
    """Re-proved raw digest, sidecar digest and verified size for each retained key.

    A checkpoint claim is not evidence: every key is rehashed and its provider sidecar is
    re-proved here, so a missing or tampered object can never be frozen into the plan as
    authoritative. Unprovable keys are recorded with an empty identity and a zero size.
    """
    snapshot: dict[str, list[Any]] = {}
    for key in sorted(set(keys)):
        entry = retained_objects.get(key)
        size = (
            None
            if entry is None
            else verify_retained_object(
                key, entry, sample_dir=sample_dir, sidecar_dir=sidecar_dir, cache=cache
            )
        )
        if entry is None or size is None:
            snapshot[key] = ["", "", 0]
            continue
        snapshot[key] = [
            str(entry.get("sha256") or ""),
            str(entry.get("provider_checksum_sha256") or ""),
            int(size),
        ]
    return snapshot


def retained_evidence_digest(snapshot: Mapping[str, Sequence[Any]]) -> str:
    return _digest_of({str(key): list(value) for key, value in sorted(snapshot.items())})


def plan_content_digest(plan: SamplePlan) -> str:
    payload = {key: value for key, value in plan.to_dict().items() if key != "note"}
    return _digest_of(payload)


_ALLOWED_PLAN_ACTIONS: frozenset[str] = frozenset(
    {"download", "alias", "reuse_retained", "blocked"}
)


def validate_sample_plan(plan: SamplePlan) -> None:
    """Refuse a plan whose actions, identities, or totals do not hold together.

    A locked plan is replayed without re-selection, so a valid-JSON edit of an action or
    a key/URL relationship would otherwise steer acquisition past the budget guard.
    """
    emitted: set[str] = set()
    downloads: dict[str, int] = {}
    retained: dict[str, int] = {}
    for entry in plan.entries:
        context = {"key": entry.key, "action": entry.action}
        if entry.action not in _ALLOWED_PLAN_ACTIONS:
            raise ResumeIntegrityError("locked plan entry has an unknown action", context=context)
        if entry.url != vision_object_url(entry.key):
            raise ResumeIntegrityError("locked plan URL does not address its key", context=context)
        family_prefix = vision_prefix(*entry.family.split("/"))
        if not entry.key.startswith(family_prefix):
            raise ResumeIntegrityError(
                "locked plan key is outside its declared family", context=context
            )
        if f"/{entry.symbol}/" not in entry.key:
            raise ResumeIntegrityError(
                "locked plan key does not belong to its declared symbol", context=context
            )
        if entry.byte_size < 0:
            raise ResumeIntegrityError("locked plan entry has a negative size", context=context)
        if entry.action == "blocked":
            if not entry.block_reason:
                raise ResumeIntegrityError(
                    "locked plan blocked entry has no reason", context=context
                )
            continue
        if entry.action == "alias":
            if entry.key not in emitted:
                raise ResumeIntegrityError(
                    "locked plan alias references an unplanned object", context=context
                )
            continue
        if entry.key in emitted:
            raise ResumeIntegrityError(
                "locked plan acquires the same object twice", context=context
            )
        emitted.add(entry.key)
        if entry.action == "download":
            downloads[entry.key] = entry.byte_size
        else:
            retained[entry.key] = entry.byte_size
    if sum(downloads.values()) != plan.new_download_bytes:
        raise ResumeIntegrityError(
            "locked plan download bytes disagree with its planned total",
            context={
                "entries": sum(downloads.values()),
                "declared": plan.new_download_bytes,
            },
        )
    if len(downloads) != plan.unique_new_objects:
        raise ResumeIntegrityError(
            "locked plan unique new object count disagrees with its entries",
            context={"entries": len(downloads), "declared": plan.unique_new_objects},
        )
    if len(retained) != plan.unique_retained_objects:
        raise ResumeIntegrityError(
            "locked plan retained object count disagrees with its entries",
            context={"entries": len(retained), "declared": plan.unique_retained_objects},
        )
    if plan.new_download_bytes > plan.allowance_bytes:
        raise ResumeIntegrityError(
            "locked plan spends more than the allowance it was locked with",
            context={
                "planned": plan.new_download_bytes,
                "allowance": plan.allowance_bytes,
            },
        )


LEGACY_PLAN_BACKUP_FILENAME: str = "cex002_sample_plan_legacy.json"


def read_pre_lock_plan(path: Path) -> dict[str, Any] | None:
    """Load a pre-lock greedy plan document so it can be preserved, never overwritten."""
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or "entries" not in document:
        return None
    return document


@dataclass
class SamplePlanLock:
    """One immutable, versioned Gate 1 plan bound to the identities that produced it.

    After the first lock a resume replays the plan and may change execution state only.
    Selected keys, blocked keys, sample identity, and the cumulative budget are fixed, the
    plan document carries its own content digest, and a superseded plan is preserved in
    ``history`` rather than overwritten. There is no in-band switch to re-select: a new
    plan version requires a fresh reviewer authorization.
    """

    path: Path
    plan_version: int = 0
    locked_at: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] = field(default_factory=dict)
    plan_digest: str = ""
    retained_snapshot: dict[str, list[Any]] = field(default_factory=dict)
    budget_snapshot: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> SamplePlanLock | None:
        document = read_checkpoint_document(path, kind="sample_plan_lock")
        if document is None:
            return None
        plan = document.get("plan")
        inputs = document.get("inputs")
        if not isinstance(plan, dict) or not isinstance(inputs, dict):
            raise ResumeIntegrityError(
                "sample plan lock is missing its plan or inputs", context={"path": str(path)}
            )
        version = document.get("plan_version")
        if not isinstance(version, int) or version < 1:
            raise ResumeIntegrityError(
                "sample plan lock has no positive plan version", context={"path": str(path)}
            )
        snapshot = document.get("retained_snapshot")
        budget_snapshot = document.get("budget_snapshot")
        history = document.get("history")
        lock = cls(
            path=path,
            plan_version=version,
            locked_at=str(document.get("locked_at") or ""),
            inputs=dict(inputs),
            plan=dict(plan),
            plan_digest=str(document.get("plan_digest") or ""),
            retained_snapshot=(
                {str(key): list(value) for key, value in snapshot.items()}
                if isinstance(snapshot, dict)
                else {}
            ),
            budget_snapshot=dict(budget_snapshot) if isinstance(budget_snapshot, dict) else {},
            history=[dict(item) for item in history] if isinstance(history, list) else [],
        )
        # The plan document is replayed verbatim, so it is re-proved before use: first
        # that nothing edited it, then that it is internally consistent.
        rebuilt = SamplePlan.from_dict(lock.plan)
        digest = plan_content_digest(rebuilt)
        if lock.plan_digest != digest:
            raise ResumeIntegrityError(
                "locked plan content does not match its recorded digest",
                context={"path": str(path), "recorded": lock.plan_digest, "actual": digest},
            )
        validate_sample_plan(rebuilt)
        return lock

    def lock_plan(
        self,
        *,
        plan: SamplePlan,
        inputs: PlanInputs,
        locked_at: str,
        retained_snapshot: Mapping[str, Sequence[Any]],
        budget_snapshot: Mapping[str, Any],
    ) -> None:
        """Install a plan version, preserving any prior plan and its inputs."""
        if self.plan:
            self.history.append(
                {
                    "plan_version": self.plan_version,
                    "locked_at": self.locked_at,
                    "inputs": dict(self.inputs),
                    "plan": dict(self.plan),
                    "plan_digest": self.plan_digest,
                }
            )
        validate_sample_plan(plan)
        self.plan_version += 1
        self.locked_at = locked_at
        self.inputs = inputs.to_dict()
        self.plan = plan.to_dict()
        self.plan_digest = plan_content_digest(plan)
        self.retained_snapshot = {str(k): list(v) for k, v in retained_snapshot.items()}
        self.budget_snapshot = dict(budget_snapshot)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "locked_at": self.locked_at,
            "inputs": dict(self.inputs),
            "plan": dict(self.plan),
            "plan_digest": self.plan_digest,
            "retained_snapshot": {k: list(v) for k, v in sorted(self.retained_snapshot.items())},
            "budget_snapshot": dict(self.budget_snapshot),
            "history": [dict(item) for item in self.history],
        }

    def flush(self) -> None:
        _atomic_write_json(self.path, _checkpoint_document("sample_plan_lock", self.to_dict()))

    def summary(self) -> dict[str, Any]:
        return {
            "legacy_plan_preserved": any(
                int(item.get("plan_version") or 0) == 0 for item in self.history
            ),
            "plan_version": self.plan_version,
            "locked_at": self.locked_at,
            "inputs": dict(self.inputs),
            "plan_digest": self.plan_digest,
            "budget_snapshot": dict(self.budget_snapshot),
            "retained_snapshot_objects": len(self.retained_snapshot),
            "immutable": True,
            "superseded_plan_versions": [
                int(item.get("plan_version") or 0) for item in self.history
            ],
            "state": "locked",
            "note": (
                "resumes replay this plan and change execution state only; a new plan "
                "version requires a fresh reviewer authorization, not an in-band switch"
            ),
        }


def file_sha256(path: Path) -> str:
    """Digest of a durable authority file, or an empty string when it is absent."""
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class AmendmentAllowance:
    """The architecture-amendment allowance, ledgered under its own identity.

    It never reconciles, rewrites, or charges the legacy ledger. The legacy record and
    its unresolved breach are carried alongside as preserved historical evidence, and
    checksum-proved retained objects stay reusable without erasing it.
    """

    ledger_id: str
    path: str
    allowance_bytes: int
    reusable_object_count: int
    reusable_bytes: int
    planned_new_bytes: int
    charged: bool
    legacy_ledger_path: str
    legacy_ledger_sha256: str
    legacy_charged_bytes: int
    legacy_spent_max_bytes: int
    legacy_state: str
    legacy_breach_state: str

    @property
    def remaining_bytes(self) -> int:
        return max(self.allowance_bytes - self.planned_new_bytes, 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "path": self.path,
            "allowance_bytes": self.allowance_bytes,
            "independent_object_cap_bytes": None,
            "reusable_retained_object_count": self.reusable_object_count,
            "reusable_retained_bytes": self.reusable_bytes,
            "planned_new_bytes": self.planned_new_bytes,
            "remaining_bytes": self.remaining_bytes,
            "charged": self.charged,
            "legacy_ledger": {
                "path": self.legacy_ledger_path,
                "sha256": self.legacy_ledger_sha256,
                "charged_bytes": self.legacy_charged_bytes,
                "spent_max_bytes": self.legacy_spent_max_bytes,
                "state": self.legacy_state,
                "breach_state": self.legacy_breach_state,
                "charged_again": False,
                "rewritten": False,
                "reconciled": False,
            },
            "rule": (
                "a separately ledgered allowance for the amended architecture; the legacy "
                "ledger record and its unresolved breach are preserved untouched"
            ),
        }


def build_amendment_allowance(
    *,
    path: Path,
    legacy_ledger: BudgetLedger,
    legacy_ledger_path: Path,
    legacy_ledger_sha256: str,
    retained_keys: Mapping[str, int],
    planned_new_bytes: int,
    allowance_bytes: int = GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
) -> AmendmentAllowance:
    return AmendmentAllowance(
        ledger_id=AMENDMENT_LEDGER_ID,
        path=str(path),
        allowance_bytes=int(allowance_bytes),
        reusable_object_count=len(retained_keys),
        reusable_bytes=sum(int(value) for value in retained_keys.values()),
        planned_new_bytes=int(planned_new_bytes),
        charged=False,
        legacy_ledger_path=str(legacy_ledger_path),
        legacy_ledger_sha256=legacy_ledger_sha256,
        legacy_charged_bytes=legacy_ledger.charged_bytes,
        legacy_spent_max_bytes=legacy_ledger.spent_max_bytes,
        legacy_state=legacy_ledger.legacy_state,
        legacy_breach_state=legacy_ledger.breach_state,
    )


def candidate_envelope_digest(
    plan: SamplePlan, *, allowance_id: str, inputs: PlanInputs | None = None
) -> str:
    """Identity of the candidate envelope: its plan, allowance, and input identities.

    This is deliberately not the plan digest. A future exact version-3 lock records
    ``plan_content_digest`` of the same plan, so that value must remain the comparable
    one; this envelope only adds allowance and input binding on top of it.
    """
    return _digest_of(
        {
            "allowance_id": allowance_id,
            "plan_content_digest": plan_content_digest(plan),
            "inputs": {} if inputs is None else inputs.to_dict(),
        }
    )


_EXPECTED_PRIOR_HISTORY_VERSIONS: tuple[int, ...] = (0, 1)


def _exact_version(value: Any, *, expected: int, context: Mapping[str, Any]) -> int:
    """A plan version is a non-boolean integer that equals exactly what is expected."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise SourceQualificationError(
            "preserved plan version is not an integer",
            context={**dict(context), "value": repr(value)},
        )
    if value != expected:
        raise SourceQualificationError(
            "preserved plan history is not the exact expected transition",
            context={**dict(context), "found": value, "expected": expected},
        )
    return value


def validate_plan_document_entries(
    document: Mapping[str, Any], *, context: Mapping[str, Any]
) -> None:
    """Structurally validate one preserved plan document's entries and identities.

    This is the version-appropriate contract for a plan that predates content digests and
    aggregate totals: every entry must still be a real object with a known action and a
    key, URL, family, and symbol that agree.
    """
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SourceQualificationError(
            "preserved plan version has no plan document", context=dict(context)
        )
    blocked = document.get("blocked", [])
    if not isinstance(blocked, list):
        raise SourceQualificationError(
            "preserved plan blocked records are malformed", context=dict(context)
        )
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise SourceQualificationError(
                "preserved plan entry is not an object", context=dict(context)
            )
        missing = [
            field
            for field in ("family", "symbol", "key", "url", "action", "byte_size")
            if field not in entry
        ]
        if missing:
            raise SourceQualificationError(
                "preserved plan entry is missing identity fields",
                context={**dict(context), "missing": missing},
            )
        key = str(entry["key"])
        detail = {**dict(context), "key": key, "action": str(entry["action"])}
        if str(entry["action"]) not in _ALLOWED_PLAN_ACTIONS:
            raise SourceQualificationError(
                "preserved plan entry has an unknown action", context=detail
            )
        if str(entry["url"]) != vision_object_url(key):
            raise SourceQualificationError(
                "preserved plan URL does not address its key", context=detail
            )
        if not key.startswith(vision_prefix(*str(entry["family"]).split("/"))):
            raise SourceQualificationError(
                "preserved plan key is outside its declared family", context=detail
            )
        if f"/{entry['symbol']}/" not in key:
            raise SourceQualificationError(
                "preserved plan key does not belong to its declared symbol", context=detail
            )
        size = entry["byte_size"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise SourceQualificationError(
                "preserved plan entry has an invalid size", context=detail
            )


def validate_prior_plan_history(lock: SamplePlanLock) -> tuple[str, ...]:
    """Require the exact preserved version-0 then version-1 history behind version 2.

    Review 98 preserves versions 0 through 2 specifically, in that order. A missing,
    string, boolean, duplicated, reversed, later, or structurally malformed record is not
    the authority a version-3 candidate may be built on. Returns the plan-content
    identities of every preserved version, deriving one for the pre-digest version-0
    document without ever writing it back.
    """
    history = list(lock.history)
    if len(history) != len(_EXPECTED_PRIOR_HISTORY_VERSIONS):
        raise SourceQualificationError(
            "durable plan history must preserve exactly versions 0 and 1",
            context={
                "path": str(lock.path),
                "history_length": len(history),
                "expected": list(_EXPECTED_PRIOR_HISTORY_VERSIONS),
            },
        )
    digests: list[str] = []
    for position, expected in enumerate(_EXPECTED_PRIOR_HISTORY_VERSIONS):
        item = history[position]
        context = {"path": str(lock.path), "position": position, "expected_version": expected}
        if not isinstance(item, Mapping):
            raise SourceQualificationError(
                "preserved plan history record is not an object", context=context
            )
        if "plan_version" not in item:
            raise SourceQualificationError(
                "preserved plan history record has no version", context=context
            )
        version = _exact_version(item["plan_version"], expected=expected, context=context)
        plan = item.get("plan")
        if not isinstance(plan, Mapping):
            raise SourceQualificationError(
                "preserved plan version has no plan document", context=context
            )
        validate_plan_document_entries(plan, context={**context, "plan_version": version})
        rebuilt = SamplePlan.from_dict(plan)
        derived = plan_content_digest(rebuilt)
        recorded = str(item.get("plan_digest") or "")
        if version == 0:
            # The pre-lock greedy plan predates content digests and aggregate totals; a
            # recorded digest is the only known permitted absence.
            if recorded and recorded != derived:
                raise SourceQualificationError(
                    "preserved plan version digest does not match its plan",
                    context={**context, "recorded": recorded},
                )
        else:
            validate_sample_plan(rebuilt)
            if recorded != derived:
                raise SourceQualificationError(
                    "preserved plan version digest does not match its plan",
                    context={**context, "recorded": recorded},
                )
        digests.append(derived)
        if recorded:
            digests.append(recorded)
    digests.append(lock.plan_digest)
    return tuple(sorted({item for item in digests if item}))


@dataclass(frozen=True, slots=True)
class CandidateAuthority:
    """Read-only prior authority proved before any candidate-phase work begins."""

    lock: SamplePlanLock
    ledger: BudgetLedger
    lock_sha256: str
    ledger_sha256: str
    prior_plan_digests: tuple[str, ...]


def candidate_preflight(
    *,
    plan_lock_path: Path,
    budget_ledger_path: Path,
    budget_bytes: int,
) -> CandidateAuthority:
    """Hash, load, and validate the exact version-2 authority before anything mutates.

    Every load here is read-only, so an invalid transition fails closed with the candidate
    store untouched: no directory, cache, checkpoint, journal, listing, holdout,
    current-contract, or Coinalyze facility has been created or used yet.
    """
    lock_sha256 = file_sha256(plan_lock_path)
    ledger_sha256 = file_sha256(budget_ledger_path)
    lock = SamplePlanLock.load(plan_lock_path)
    if lock is None or lock.plan_version != REQUIRED_PRIOR_PLAN_VERSION:
        raise SourceQualificationError(
            "candidate plan construction requires the durable version-2 plan lock",
            context={
                "path": str(plan_lock_path),
                "found_version": None if lock is None else lock.plan_version,
                "required_version": REQUIRED_PRIOR_PLAN_VERSION,
            },
        )
    prior_plan_digests = validate_prior_plan_history(lock)
    ledger = BudgetLedger.load(budget_ledger_path, budget_bytes=budget_bytes)
    if ledger is None:
        raise SourceQualificationError(
            "candidate plan construction requires the durable legacy budget ledger",
            context={"path": str(budget_ledger_path)},
        )
    return CandidateAuthority(
        lock=lock,
        ledger=ledger,
        lock_sha256=lock_sha256,
        ledger_sha256=ledger_sha256,
        prior_plan_digests=prior_plan_digests,
    )


def build_candidate_plan_v3(
    *,
    lock: SamplePlanLock,
    prior_lock_sha256: str,
    plan: SamplePlan,
    inputs: PlanInputs,
    allowance: AmendmentAllowance,
    prior_plan_digests: Sequence[str] = (),
) -> dict[str, Any]:
    """An independent version-3 candidate that migrates nothing and downloads nothing.

    The candidate is constructed from its own allowance and inputs, not by relabelling
    the executing plan. Its digest must differ from the currently locked plan and from
    every historical plan digest.
    """
    validate_sample_plan(plan)
    # The comparable identity is the plan-content digest an exact future lock would
    # record. The envelope digest additionally binds the allowance and input identity but
    # never replaces or conceals plan-content equality.
    digest = plan_content_digest(plan)
    envelope = candidate_envelope_digest(
        plan, allowance_id=allowance.ledger_id, inputs=inputs
    )
    # Every preserved version participates, including the derived version-0 identity, so
    # an identical historical plan cannot evade reuse detection behind a new allowance.
    prior_digests = (
        {lock.plan_digest}
        | {str(item.get("plan_digest") or "") for item in lock.history}
        | {str(item) for item in prior_plan_digests}
    )
    prior_digests.discard("")
    if digest in prior_digests:
        raise ResumeIntegrityError(
            "candidate plan reuses a prior plan-content digest",
            context={"plan_digest": digest, "prior_digests": sorted(prior_digests)},
        )
    return {
        "plan_version": CANDIDATE_PLAN_VERSION,
        "state": "candidate_unmigrated",
        "migration_authorized": False,
        "download_authorized": False,
        "prior_plan_version": lock.plan_version,
        "prior_plan_digest": lock.plan_digest,
        "prior_lock_sha256": prior_lock_sha256,
        "prior_plan_history_versions": sorted(
            int(item.get("plan_version") or 0) for item in lock.history
        ),
        "prior_plan_digests": sorted(prior_digests),
        "plan_digest": digest,
        "plan_digest_domain": "plan_content_digest",
        "candidate_envelope_digest": envelope,
        "digest_reuses_prior": False,
        "inputs": inputs.to_dict(),
        "plan": plan.to_dict(),
        "allowance": allowance.to_dict(),
        "assertions": {
            "no_migration": True,
            "no_download": True,
            "no_public_relock_switch": True,
            "prior_lock_bytes_unchanged": True,
            "legacy_ledger_bytes_unchanged": True,
            "legacy_ledger_charged_again": False,
        },
        "note": (
            "versions 0-2 remain durable; this candidate is not locked and authorizes no "
            "sample download until a later reviewer decision"
        ),
    }


def verify_retained_object(
    key: str,
    entry: Mapping[str, Any],
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    cache: dict[tuple[str, str], int | None] | None = None,
) -> int | None:
    """Rehash a retained sample and re-prove its provider sidecar.

    Returns the verified byte size, or ``None`` when the evidence is missing, tampered,
    or incomplete. A checkpoint row is never accepted as proof on its own. ``cache`` may
    memoise the result for one run so the same object is not rehashed several times; it
    is keyed by object and claimed digest, so a substitution is still caught next run.
    """
    if str(entry.get("status") or "") != "complete":
        return None
    digest = str(entry.get("sha256") or "")
    if cache is not None and (key, digest) in cache:
        return cache[(key, digest)]
    verified = _verify_retained_object(
        key, entry, digest=digest, sample_dir=sample_dir, sidecar_dir=sidecar_dir
    )
    if cache is not None:
        cache[(key, digest)] = verified
    return verified


def _verify_retained_object(
    key: str,
    entry: Mapping[str, Any],
    *,
    digest: str,
    sample_dir: Path,
    sidecar_dir: Path,
) -> int | None:
    provider = str(entry.get("provider_checksum") or "")
    if len(digest) != 64 or provider != digest:
        return None
    dest = content_addressed_path(sample_dir, digest)
    if not dest.is_file() or dest.name != digest:
        return None
    if compute_sha256(dest) != digest:
        return None
    try:
        verify_provider_sidecar(
            key=key,
            object_sha256=digest,
            sidecar_path=Path(str(entry.get("provider_checksum_path") or "")),
            sidecar_sha256=str(entry.get("provider_checksum_sha256") or ""),
            sidecar_dir=sidecar_dir,
        )
    except SourceQualificationError:
        return None
    return int(dest.stat().st_size)


LEDGER_TRANSFERRED: str = "transferred"
LEDGER_NO_TRANSFER: str = "no_transfer_content_address_reuse"
_LEDGER_DISPOSITIONS: frozenset[str] = frozenset({LEDGER_TRANSFERRED, LEDGER_NO_TRANSFER})


@dataclass
class BudgetLedger:
    """Write-ahead cumulative accounting of every new Gate 1 sample byte.

    A planned object is reserved at its positive planned size before any network work and
    settled afterwards with an explicit disposition: either bytes were transferred, or the
    object was adopted from an existing content address and nothing moved. A settled
    charge keeps its planned size as a monotonic floor, its transferred amount is
    reconciled against rehashed retained evidence, and the document carries independent
    counts, totals, and a state digest so a partial valid-JSON edit fails closed before
    any download.

    Retained bytes that predate this ledger cannot be attributed per invocation, and
    review 67 made some retained samples budget-free, so their cost is an honest range
    from zero to the verified retained total.
    """

    path: Path
    budget_bytes: int
    charges: dict[str, dict[str, Any]] = field(default_factory=dict)
    reservations: dict[str, dict[str, Any]] = field(default_factory=dict)
    legacy_max_bytes: int = 0
    legacy_state: str = "resolved"
    legacy_note: str = ""

    # --- validation -------------------------------------------------------------------

    def _check_amount(self, value: Any, *, label: str, key: str, positive: bool) -> int:
        context = {"path": str(self.path), "label": label, "key": key}
        if isinstance(value, bool) or not isinstance(value, int):
            raise ResumeIntegrityError(
                "budget ledger amount is not an integer", context=context
            )
        if value < 0 or (positive and value <= 0):
            raise ResumeIntegrityError(
                "budget ledger amount is not a valid size",
                context={**context, "value": value},
            )
        if value > self.budget_bytes:
            raise ResumeIntegrityError(
                "budget ledger amount exceeds the Gate 1 budget",
                context={**context, "value": value, "budget_bytes": self.budget_bytes},
            )
        return value

    def validate(self) -> None:
        """Re-prove the whole ledger; no edit may reduce durable spend."""
        context = {"path": str(self.path)}
        if self.budget_bytes <= 0:
            raise ResumeIntegrityError("budget ledger has no positive budget", context=context)
        overlap = sorted(set(self.charges) & set(self.reservations))
        if overlap:
            raise ResumeIntegrityError(
                "budget ledger charges and reservations are not disjoint",
                context={**context, "keys": overlap[:8]},
            )
        for key, record in self.reservations.items():
            if not isinstance(record, dict):
                raise ResumeIntegrityError(
                    "budget ledger reservation is not a record", context={**context, "key": key}
                )
            # A reservation always retains its original positive planned size.
            self._check_amount(
                record.get("planned_bytes"), label="reservation", key=key, positive=True
            )
        for key, record in self.charges.items():
            if not isinstance(record, dict):
                raise ResumeIntegrityError(
                    "budget ledger charge is not a record", context={**context, "key": key}
                )
            planned = self._check_amount(
                record.get("planned_bytes"), label="charge_planned", key=key, positive=True
            )
            transferred = self._check_amount(
                record.get("transferred_bytes"), label="charge_transferred", key=key,
                positive=False,
            )
            if transferred > planned:
                raise ResumeIntegrityError(
                    "budget ledger charge exceeds its planned floor",
                    context={**context, "key": key},
                )
            disposition = str(record.get("disposition") or "")
            if disposition not in _LEDGER_DISPOSITIONS:
                raise ResumeIntegrityError(
                    "budget ledger charge has no known disposition",
                    context={**context, "key": key, "disposition": disposition},
                )
            if transferred == 0 and disposition != LEDGER_NO_TRANSFER:
                # A naked zero charge is indistinguishable from an allowance-restoring
                # edit; a genuine zero-cost reuse must say so explicitly.
                raise ResumeIntegrityError(
                    "budget ledger zero charge has no no-transfer disposition",
                    context={**context, "key": key},
                )
            if transferred > 0 and disposition != LEDGER_TRANSFERRED:
                raise ResumeIntegrityError(
                    "budget ledger transferred charge is mislabelled",
                    context={**context, "key": key},
                )
            _require_hex_digest(
                record.get("sha256"),
                label="charge object digest",
                context={**context, "key": key},
            )
        if self.legacy_max_bytes < 0:
            raise ResumeIntegrityError(
                "budget ledger legacy maximum is negative", context=context
            )

    def integrity_summary(self) -> dict[str, Any]:
        """Independent counts, totals and a state digest over the whole ledger."""
        planned_total = sum(
            int(record["planned_bytes"]) for record in self.charges.values()
        ) + sum(int(record["planned_bytes"]) for record in self.reservations.values())
        transferred_total = sum(
            int(record["transferred_bytes"]) for record in self.charges.values()
        )
        state = _digest_of(
            {
                "budget_bytes": self.budget_bytes,
                "charges": {
                    key: [
                        int(record["planned_bytes"]),
                        int(record["transferred_bytes"]),
                        str(record["disposition"]),
                        str(record["sha256"]),
                    ]
                    for key, record in sorted(self.charges.items())
                },
                "reservations": {
                    key: int(record["planned_bytes"])
                    for key, record in sorted(self.reservations.items())
                },
                "legacy_max_bytes": self.legacy_max_bytes,
                "legacy_state": self.legacy_state,
            }
        )
        return {
            "charge_count": len(self.charges),
            "reservation_count": len(self.reservations),
            "planned_total_bytes": planned_total,
            "transferred_total_bytes": transferred_total,
            "charged_bytes": self.charged_bytes,
            "state_sha256": state,
        }

    # --- durable io -------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path, *, budget_bytes: int) -> BudgetLedger | None:
        document = read_checkpoint_document(path, kind="budget_ledger")
        if document is None:
            return None
        stored_budget = document.get("budget_bytes")
        if not isinstance(stored_budget, int) or isinstance(stored_budget, bool):
            raise ResumeIntegrityError(
                "budget ledger has no integer budget", context={"path": str(path)}
            )
        if stored_budget != int(budget_bytes):
            # A different allowance is a different accounting contract, never a resume.
            raise ResumeIntegrityError(
                "budget ledger was written for a different Gate 1 budget",
                context={
                    "path": str(path),
                    "stored": stored_budget,
                    "requested": int(budget_bytes),
                },
            )
        charges = document.get("charges")
        reservations = document.get("reservations")
        if not isinstance(charges, dict) or not isinstance(reservations, dict):
            raise ResumeIntegrityError(
                "budget ledger charges or reservations are malformed",
                context={"path": str(path)},
            )
        legacy_max = document.get("legacy_max_bytes", 0)
        if isinstance(legacy_max, bool) or not isinstance(legacy_max, int) or legacy_max < 0:
            raise ResumeIntegrityError(
                "budget ledger legacy maximum is invalid", context={"path": str(path)}
            )
        ledger = cls(
            path=path,
            budget_bytes=int(budget_bytes),
            charges={
                str(key): dict(value) if isinstance(value, dict) else value
                for key, value in charges.items()
            },
            reservations={
                str(key): dict(value) if isinstance(value, dict) else value
                for key, value in reservations.items()
            },
            legacy_max_bytes=legacy_max,
            legacy_state=str(document.get("legacy_state") or "resolved"),
            legacy_note=str(document.get("legacy_note") or ""),
        )
        ledger.validate()
        recorded = document.get("integrity")
        if not isinstance(recorded, dict):
            raise ResumeIntegrityError(
                "budget ledger has no integrity summary", context={"path": str(path)}
            )
        actual = ledger.integrity_summary()
        differences = sorted(
            name for name, value in actual.items() if recorded.get(name) != value
        )
        if differences:
            # A partial valid-JSON edit cannot agree with the independent totals.
            raise ResumeIntegrityError(
                "budget ledger integrity summary disagrees with its entries",
                context={"path": str(path), "fields": differences},
            )
        return ledger

    @classmethod
    def bootstrap(
        cls,
        path: Path,
        *,
        budget_bytes: int,
        retained_objects: Mapping[str, Mapping[str, Any]],
        sample_dir: Path,
        sidecar_dir: Path,
        cache: dict[tuple[str, str], int | None] | None = None,
    ) -> BudgetLedger:
        existing = cls.load(path, budget_bytes=budget_bytes)
        if existing is not None:
            return existing
        verified: dict[str, int] = {}
        for key, entry in retained_objects.items():
            size = verify_retained_object(
                key, entry, sample_dir=sample_dir, sidecar_dir=sidecar_dir, cache=cache
            )
            if size is None:
                continue
            digest = str(entry.get("sha256") or "")
            verified.setdefault(digest, size)
        upper = sum(verified.values())
        if upper <= 0:
            return cls(path=path, budget_bytes=int(budget_bytes))
        return cls(
            path=path,
            budget_bytes=int(budget_bytes),
            legacy_max_bytes=upper,
            legacy_state=LEGACY_BUDGET_UNRESOLVED,
            legacy_note=(
                "retained sample bytes predate this ledger and include review-67 "
                "budget-free samples; the chargeable amount is a range from zero to the "
                "verified retained total, never a lower bound. The prior per-invocation "
                "breach stays established by execution record 74 and is not recomputed here"
            ),
        )

    def flush(self) -> None:
        self.validate()
        _atomic_write_json(
            self.path,
            _checkpoint_document(
                "budget_ledger",
                {
                    "budget_bytes": self.budget_bytes,
                    "charges": {
                        key: dict(record) for key, record in sorted(self.charges.items())
                    },
                    "reservations": {
                        key: dict(record) for key, record in sorted(self.reservations.items())
                    },
                    "legacy_max_bytes": self.legacy_max_bytes,
                    "legacy_state": self.legacy_state,
                    "legacy_note": self.legacy_note,
                    "integrity": self.integrity_summary(),
                },
            ),
        )

    # --- accounting -------------------------------------------------------------------

    @property
    def charged_bytes(self) -> int:
        """Definitely chargeable: settled transfers plus unsettled reservations."""
        return sum(
            int(record["transferred_bytes"]) for record in self.charges.values()
        ) + sum(int(record["planned_bytes"]) for record in self.reservations.values())

    @property
    def spent_min_bytes(self) -> int:
        return self.charged_bytes

    @property
    def spent_max_bytes(self) -> int:
        return self.charged_bytes + self.legacy_max_bytes

    @property
    def remaining_bytes(self) -> int:
        """Conservative allowance: zero while the legacy range could exhaust it."""
        return max(self.budget_bytes - self.spent_max_bytes, 0)

    @property
    def exhausted(self) -> bool:
        return self.remaining_bytes <= 0

    @property
    def breach_state(self) -> str:
        if self.spent_min_bytes > self.budget_bytes:
            return "confirmed"
        if self.spent_max_bytes > self.budget_bytes:
            return "unresolved"
        return "none"

    def reserve(self, key: str, byte_size: int) -> None:
        """Charge a positive planned size durably before the acquisition that may lose it."""
        if key in self.charges or key in self.reservations:
            return
        self.reservations[key] = {"planned_bytes": max(int(byte_size), 1)}
        self.flush()

    def settle(
        self,
        key: str,
        transferred_bytes: int,
        *,
        sha256: str,
        no_transfer: bool = False,
    ) -> None:
        """Close a reservation with an explicit disposition and a proved object digest."""
        reservation = self.reservations.get(key) or self.charges.get(key)
        transferred = 0 if no_transfer else int(transferred_bytes)
        # The planned size is a monotonic floor: settlement records the proved transfer
        # and never lowers what was already durably reserved.
        planned = max(int((reservation or {}).get("planned_bytes") or 0), transferred, 1)
        self.charges[key] = {
            "planned_bytes": planned,
            "transferred_bytes": transferred,
            "disposition": LEDGER_NO_TRANSFER if no_transfer else LEDGER_TRANSFERRED,
            "sha256": str(sha256),
        }
        self.reservations.pop(key, None)
        self.flush()

    def reconcile(
        self,
        retained_objects: Mapping[str, Mapping[str, Any]],
        *,
        sample_dir: Path,
        sidecar_dir: Path,
    ) -> dict[str, int]:
        """Settle proved reservations and re-prove every settled charge.

        A reservation is only settled against rehashed retained evidence; anything
        unproved stays charged. A settled charge whose retained object disagrees with its
        recorded transition is an integrity failure, not spend.
        """
        settled = 0
        unresolved = 0
        for key in sorted(self.reservations):
            entry = retained_objects.get(key)
            size = (
                None
                if entry is None
                else verify_retained_object(
                    key, entry, sample_dir=sample_dir, sidecar_dir=sidecar_dir
                )
            )
            if size is None:
                # The bytes may have been fetched and lost; never restore the allowance.
                unresolved += 1
                continue
            self.settle(key, size, sha256=str(entry.get("sha256") or "") if entry else "")
            settled += 1
        reproved = 0
        unreconciled = 0
        for key in sorted(self.charges):
            record = self.charges[key]
            entry = retained_objects.get(key)
            size = (
                None
                if entry is None
                else verify_retained_object(
                    key, entry, sample_dir=sample_dir, sidecar_dir=sidecar_dir
                )
            )
            if size is None:
                unreconciled += 1
                continue
            digest = str(entry.get("sha256") or "") if entry else ""
            if str(record.get("sha256") or "") != digest:
                raise ResumeIntegrityError(
                    "settled charge does not identify the retained object it charged",
                    context={"key": key, "recorded": record.get("sha256"), "retained": digest},
                )
            if record.get("disposition") == LEDGER_TRANSFERRED and int(
                record.get("transferred_bytes") or 0
            ) != int(size):
                raise ResumeIntegrityError(
                    "settled charge disagrees with the rehashed retained object size",
                    context={
                        "key": key,
                        "recorded": record.get("transferred_bytes"),
                        "verified": size,
                    },
                )
            reproved += 1
        if settled:
            self.flush()
        return {
            "settled": settled,
            "unresolved": unresolved,
            "reproved": reproved,
            "unreconciled": unreconciled,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "budget_bytes": self.budget_bytes,
            "charged_bytes": self.charged_bytes,
            "settled_object_count": len(self.charges),
            "settled_bytes": sum(
                int(record["transferred_bytes"]) for record in self.charges.values()
            ),
            "no_transfer_object_count": sum(
                1
                for record in self.charges.values()
                if record.get("disposition") == LEDGER_NO_TRANSFER
            ),
            "reserved_object_count": len(self.reservations),
            "reserved_bytes": sum(
                int(record["planned_bytes"]) for record in self.reservations.values()
            ),
            "legacy_chargeable_min_bytes": 0,
            "legacy_chargeable_max_bytes": self.legacy_max_bytes,
            "legacy_state": self.legacy_state,
            "legacy_note": self.legacy_note,
            "cumulative_spent_min_bytes": self.spent_min_bytes,
            "cumulative_spent_max_bytes": self.spent_max_bytes,
            "cumulative_remaining_bytes": self.remaining_bytes,
            "exhausted": self.exhausted,
            "breach_state": self.breach_state,
            "integrity": self.integrity_summary(),
            "external_breach_record": "research/sprint_004/74_CEX002_GATE1_RESUMABLE_EXECUTION.md",
            "accounting": (
                "write-ahead: a positive planned size is reserved before acquisition and "
                "settled with an explicit transferred or no-transfer disposition, so an "
                "interruption or an edit never restores allowance"
            ),
            "scope": "cumulative across every invocation, never per invocation",
        }


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


_OBJECT_PERIOD_RE = re.compile(r"(\d{4})-(\d{2})(?:-\d{2})?\.(?:zip|csv)$")


def object_period(key: str) -> str | None:
    """Calendar month an official archive object covers, from its own filename."""
    match = _OBJECT_PERIOD_RE.search(key)
    if match is None:
        return None
    return f"{match.group(1)}-{match.group(2)}"


_OBJECT_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\.(?:zip|csv)$")


def object_calendar_date(key: str) -> str | None:
    """Whole calendar day an official daily archive object covers, if present."""
    match = _OBJECT_DATE_RE.search(key)
    if match is None:
        return None
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def object_cadence(key: str) -> str:
    if "/monthly/" in key:
        return "monthly"
    if "/daily/" in key:
        return "daily"
    return "unknown"


def kline_schema_supports_taker_flow(fields: Sequence[str]) -> bool:
    present = {str(item) for item in fields}
    return set(KLINE_TAKER_FLOW_FIELDS).issubset(present)


def _month_from_date(value: str) -> str:
    return value[:7]


def family_group_from_key(key: str) -> str:
    """Logical family group of an official archive key: ``.../<cadence>/<family>/...``."""
    parts = key.split("/")
    return parts[4] if len(parts) > 5 else ""


def object_integrity_state(
    key: str,
    *,
    checksum_keys: Collection[str],
    quarantined: Collection[str] = (),
    proved_keys: Collection[str] = (),
) -> str:
    """Integrity qualification of one listed object, from official evidence only.

    A listed ``.CHECKSUM`` sibling is evidence that provider authority exists; it is not
    evidence that the sidecar was parsed, bound to the object, or that raw bytes matched
    it. Only a re-proved retained object earns ``checksum_proved_retained``.

    Precedence is deliberate. A listed sidecar is the outcome-blind selection
    precondition, so proof may promote validation state only inside the already eligible
    selection domain: an object whose sidecar was absent from the pinned listing stays
    ``sidecar_absent`` however well its retained bytes re-prove, and a sample proof can
    therefore never displace a daily fallback or change cadence selection.
    """
    if key in quarantined:
        return INTEGRITY_QUARANTINED
    if key not in checksum_keys:
        return INTEGRITY_SIDECAR_ABSENT
    if key in proved_keys:
        return INTEGRITY_CHECKSUM_PROVED
    return INTEGRITY_SIDECAR_LISTED


def _selectable(state: str) -> bool:
    """Outcome-blind selection precondition: provider authority must at least exist."""
    return state in {INTEGRITY_SIDECAR_LISTED, INTEGRITY_CHECKSUM_PROVED}


def select_nonoverlapping_objects(
    objects: Sequence[ListingObject],
    *,
    checksum_keys: Collection[str] = (),
    quarantined: Collection[str] = (),
    proved_keys: Collection[str] = (),
) -> tuple[tuple[ListingObject, ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Integrity-qualified monthly canon with explicit daily fallback.

    Both cadences carry the same precondition: an object without listed provider
    authority is never selected, and its interval becomes typed missing-authority
    evidence instead of silently usable data. A monthly package is canonical only when it
    passes that precondition; a rejected month falls back to daily objects, and selecting
    both cadences for one month is an economic-interval collision.
    """
    monthly: dict[str, ListingObject] = {}
    daily: dict[str, ListingObject] = {}
    collisions: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    rejected_months: set[str] = set()

    def _state(key: str) -> str:
        return object_integrity_state(
            key,
            checksum_keys=checksum_keys,
            quarantined=quarantined,
            proved_keys=proved_keys,
        )

    for obj in objects:
        cadence = object_cadence(obj.key)
        if cadence == "monthly":
            month = object_period(obj.key)
            if month is None:
                continue
            state = _state(obj.key)
            if not _selectable(state):
                rejected_months.add(month)
                rejections.append(
                    {
                        "kind": MANIFEST_MONTHLY_REJECTED,
                        "interval": month,
                        "key": obj.key,
                        "integrity_state": state,
                        "consumable": False,
                    }
                )
                continue
            prior = monthly.get(month)
            if prior is not None and prior.key != obj.key:
                collisions.append(
                    {
                        "kind": "economic_interval_collision",
                        "interval": month,
                        "keys": [prior.key, obj.key],
                    }
                )
                continue
            monthly[month] = obj
        elif cadence == "daily":
            day = object_calendar_date(obj.key) or (
                f"{object_period(obj.key)}-01" if object_period(obj.key) else None
            )
            if day is None:
                continue
            state = _state(obj.key)
            if not _selectable(state):
                rejections.append(
                    {
                        "kind": MANIFEST_INTEGRITY_MISSING,
                        "interval": day,
                        "key": obj.key,
                        "integrity_state": state,
                        "consumable": False,
                        "blocking": True,
                    }
                )
                continue
            prior = daily.get(day)
            if prior is not None and prior.key != obj.key:
                collisions.append(
                    {
                        "kind": "economic_interval_collision",
                        "interval": day,
                        "keys": [prior.key, obj.key],
                    }
                )
                continue
            daily[day] = obj
    selected: list[ListingObject] = []
    covered_months = set(monthly)
    selected.extend(monthly[month] for month in sorted(monthly))
    for day in sorted(daily):
        month = _month_from_date(day)
        if month in covered_months:
            continue
        selected.append(daily[day])
        if month in rejected_months:
            rejections.append(
                {
                    "kind": MANIFEST_DAILY_FALLBACK,
                    "interval": day,
                    "key": daily[day].key,
                    "replaces_month": month,
                    "integrity_state": _state(daily[day].key),
                    "consumable": _state(daily[day].key) == INTEGRITY_CHECKSUM_PROVED,
                }
            )
    uncovered = sorted(
        month
        for month in rejected_months
        if month not in covered_months
        and not any(_month_from_date(day) == month for day in daily)
    )
    for month in uncovered:
        rejections.append(
            {
                "kind": MANIFEST_INTEGRITY_MISSING,
                "interval": month,
                "key": "",
                "replaces_month": month,
                "consumable": False,
                "blocking": True,
                "status": "no_daily_fallback_available",
            }
        )
    return tuple(selected), tuple(collisions), tuple(rejections)


def manifest_row(
    obj: ListingObject,
    *,
    family: str,
    family_group: str,
    symbol: str,
    integrity_state: str,
    sidecar_sha256: str = "",
) -> dict[str, Any]:
    """One immutable, inspectable selected-manifest row.

    Selection is outcome-blind, so a row may be planned before its raw bytes are proved.
    Such a row is explicitly ``raw_validation_pending`` and never ``consumable``.
    """
    cadence = object_cadence(obj.key)
    if cadence == "monthly":
        interval = object_period(obj.key) or ""
        interval_kind = "month"
    else:
        interval = object_calendar_date(obj.key) or object_period(obj.key) or ""
        interval_kind = "date"
    proved = integrity_state == INTEGRITY_CHECKSUM_PROVED
    return {
        "key": obj.key,
        "family": family,
        "family_group": family_group,
        "symbol": symbol,
        "cadence": cadence,
        "byte_size": int(obj.size) if obj.size is not None else None,
        "integrity_state": integrity_state,
        "validation_state": VALIDATION_PROVED if proved else VALIDATION_PENDING,
        "consumable": proved,
        "sidecar_key": (
            f"{obj.key}.CHECKSUM"
            if integrity_state in {INTEGRITY_SIDECAR_LISTED, INTEGRITY_CHECKSUM_PROVED}
            else ""
        ),
        "sidecar_sha256": sidecar_sha256,
        "economic_interval": interval,
        "economic_interval_kind": interval_kind,
    }


def _assert_no_overlapping_coverage(rows: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed when the selected manifest covers one economic interval twice."""
    months: dict[tuple[str, str], str] = {}
    intervals: set[tuple[str, str, str]] = set()
    for row in rows:
        scope = (str(row["symbol"]), str(row["family_group"]))
        interval = str(row["economic_interval"])
        identity = (scope[0], scope[1], interval)
        if identity in intervals:
            raise SourceQualificationError(
                "selected manifest covers one economic interval twice",
                context={"kind": MANIFEST_OVERLAP, **dict(row)},
            )
        intervals.add(identity)
        if row["cadence"] == "monthly":
            months[scope] = interval
    for row in rows:
        if row["cadence"] != "daily":
            continue
        scope = (str(row["symbol"]), str(row["family_group"]))
        month = _month_from_date(str(row["economic_interval"]))
        if months.get(scope) == month:
            raise SourceQualificationError(
                "selected manifest covers a month by both cadences",
                context={"kind": MANIFEST_OVERLAP, **dict(row)},
            )


def build_acquisition_manifest(
    *,
    inventory: Mapping[str, FamilyInventory],
    universe: Sequence[str],
    quarantined: Collection[str] = (),
    proved_objects: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Immutable non-overlapping selected objects for the Harmonic-ready release."""
    members = set(universe)
    proved = dict(proved_objects or {})
    proved_keys = frozenset(proved)
    selected: dict[str, ListingObject] = {}
    rows: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    by_family: dict[str, int] = {}
    families = sorted(
        {
            family
            for product, items in OFFICIAL_ARCHIVE_FAMILIES.items()
            if product != "binance_usdm_cost_calibration"
            for family in items
        }
    )
    grouped: dict[str, list[str]] = {}
    for family in families:
        grouped.setdefault(_family_group(family), []).append(family)
    for group, group_families in sorted(grouped.items()):
        by_symbol: dict[str, list[ListingObject]] = {}
        family_of: dict[str, str] = {}
        checksum_keys: set[str] = set()
        for family in group_families:
            entry = inventory.get(family)
            if entry is None or not entry.listed:
                continue
            checksum_keys.update(entry.checksum_keys)
            for symbol, objects in entry.objects.items():
                if symbol not in members:
                    continue
                by_symbol.setdefault(symbol, []).extend(objects)
                for obj in objects:
                    family_of[obj.key] = family
        for symbol in sorted(by_symbol):
            chosen, found, rejected = select_nonoverlapping_objects(
                by_symbol[symbol],
                checksum_keys=checksum_keys,
                quarantined=quarantined,
                proved_keys=proved_keys,
            )
            collisions.extend({"symbol": symbol, "family_group": group, **item} for item in found)
            rejections.extend(
                {"symbol": symbol, "family_group": group, **item} for item in rejected
            )
            for obj in chosen:
                selected[obj.key] = obj
                family = family_of.get(obj.key, group_families[0])
                state = object_integrity_state(
                    obj.key,
                    checksum_keys=checksum_keys,
                    quarantined=quarantined,
                    proved_keys=proved_keys,
                )
                rows.append(
                    manifest_row(
                        obj,
                        family=family,
                        family_group=group,
                        symbol=symbol,
                        integrity_state=state,
                        sidecar_sha256=str(
                            (proved.get(obj.key) or {}).get("provider_checksum_sha256") or ""
                        ),
                    )
                )
                by_family[family] = by_family.get(family, 0) + 1
    rows.sort(key=lambda item: (item["family_group"], item["symbol"], item["key"]))
    _assert_no_overlapping_coverage(rows)
    pending = tuple(row["key"] for row in rows if not row["consumable"])
    return {
        "object_count": len(selected),
        "compressed_raw_bytes": sum(int(obj.size or 0) for obj in selected.values()),
        "unknown_size_objects": sum(1 for obj in selected.values() if obj.size is None),
        "keys": tuple(sorted(selected)),
        "objects": selected,
        "rows": tuple(rows),
        "collisions": tuple(collisions),
        "rejections": tuple(rejections),
        "raw_validation_pending_keys": pending,
        "consumable_object_count": len(rows) - len(pending),
        "integrity_rule": (
            "a listed provider sidecar is the outcome-blind selection precondition for "
            "both cadences; only a rehashed retained object with a re-proved sidecar is "
            "checksum-proved and consumable, and missing authority stays typed evidence"
        ),
        "family_object_counts": dict(sorted(by_family.items())),
        "cadence_rule": "monthly_preferred_daily_gap_tail_v1",
    }


def select_cost_calibration_sample(
    *,
    inventory: Mapping[str, FamilyInventory],
    universe: Sequence[str],
) -> dict[str, Any]:
    """Outcome-blind first/midpoint/last whole-day bookTicker and bookDepth objects."""
    members = set(universe)
    selected: dict[str, ListingObject] = {}
    items: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for family in COST_SAMPLE_FAMILIES:
        entry = inventory.get(family)
        group = _family_group(family)
        for symbol in sorted(members):
            objects = [] if entry is None else list(entry.objects.get(symbol, ()))
            dated = []
            for obj in objects:
                day = object_calendar_date(obj.key)
                if day is None:
                    continue
                dated.append((day, obj))
            dated.sort(key=lambda item: item[0])
            if not dated:
                gaps.append(
                    {
                        "symbol": symbol,
                        "family": family,
                        "family_group": group,
                        "kind": "cost_sample_unavailable",
                        "blocking": True,
                        "status": "cost_sample_unavailable",
                    }
                )
                continue
            picks = [dated[0], dated[len(dated) // 2], dated[-1]]
            seen: set[str] = set()
            for _day, obj in picks:
                if obj.key in seen:
                    continue
                seen.add(obj.key)
                selected[obj.key] = obj
                items.append({"family": family, "symbol": symbol, "key": obj.key, "object": obj})
    return {
        "object_count": len(selected),
        "compressed_raw_bytes": sum(int(obj.size or 0) for obj in selected.values()),
        "unknown_size_objects": sum(1 for obj in selected.values() if obj.size is None),
        "keys": tuple(sorted(selected)),
        "objects": selected,
        "items": tuple(items),
        "gaps": tuple(gaps),
        "selector": "first_midpoint_last_daily_book_v1",
        "families": list(COST_SAMPLE_FAMILIES),
    }


def selected_storage_report(
    *,
    inventory: Mapping[str, FamilyInventory],
    manifest: Mapping[str, Any],
    cost_sample: Mapping[str, Any],
) -> dict[str, Any]:
    """Exact selected raw/cost bytes; later Gate 2 bounds remain explicitly unknown."""
    listing_bytes = 0
    listing_unknown = 0
    unselected_bytes = 0
    for family, entry in inventory.items():
        for objects in entry.objects.values():
            for obj in objects:
                if obj.size is None:
                    listing_unknown += 1
                    continue
                listing_bytes += int(obj.size)
                if (
                    family in UNSELECTED_DISCOVERY_FAMILIES
                    and obj.key not in cost_sample["objects"]
                ):
                    unselected_bytes += int(obj.size)
    selected_objects = {**manifest["objects"], **cost_sample["objects"]}
    sizes = [int(obj.size) for obj in selected_objects.values() if obj.size is not None]
    return {
        "selected_compressed_raw_bytes": int(manifest["compressed_raw_bytes"]),
        "cost_sample_compressed_raw_bytes": int(cost_sample["compressed_raw_bytes"]),
        "selected_plus_cost_compressed_raw_bytes": int(manifest["compressed_raw_bytes"])
        + int(cost_sample["compressed_raw_bytes"]),
        "largest_selected_compressed_object_bytes": max(sizes) if sizes else 0,
        "selected_object_count": int(manifest["object_count"]),
        "cost_sample_object_count": int(cost_sample["object_count"]),
        "discovered_listing_bytes": listing_bytes,
        "discovered_listing_unknown_size_objects": listing_unknown,
        "unselected_discovery_bytes": unselected_bytes,
        "normalized_catalog_bytes": "unknown",
        "temporary_high_water_bytes": "unknown",
        "operating_reserve_bytes": "unknown",
        "total_sufficiency": "unknown",
        "collisions": list(manifest.get("collisions") or ()),
        "note": (
            "selected raw and cost-sample bytes are exact; normalized, temporary "
            "high-water, reserve, and total sufficiency remain unknown until a later "
            "bounded measurement"
        ),
    }


def holdout_boundary_id(*, boundary_utc: str, replay_rule: str) -> str:
    return _digest_of(
        {"ticket": TICKET_ID, "boundary_utc": boundary_utc, "replay_rule": replay_rule}
    )


@dataclass(frozen=True, slots=True)
class HoldoutBoundary:
    """A durable prospective boundary pinned once and replayed unchanged.

    The boundary is the first authenticated qualification instant. It is stored with its
    own identity digest and the digest of the record it superseded, so a later run can
    prove it was replayed rather than moved, and no model outcome can influence it.
    """

    path: Path
    boundary_utc: str
    boundary_ms: int
    boundary_id: str
    prior_record_sha256: str
    pinned_at: str
    replay_rule: str = HOLDOUT_REPLAY_RULE

    @classmethod
    def load_or_pin(cls, path: Path, *, now_iso: str) -> HoldoutBoundary:
        document = read_checkpoint_document(path, kind="holdout_boundary")
        if document is None:
            boundary_utc = now_iso
            boundary_ms = _iso_to_ms(boundary_utc)
            if boundary_ms is None:
                raise SourceQualificationError(
                    "holdout boundary requires a parseable authenticated instant",
                    context={"boundary_utc": boundary_utc},
                )
            record = cls(
                path=path,
                boundary_utc=boundary_utc,
                boundary_ms=boundary_ms,
                boundary_id=holdout_boundary_id(
                    boundary_utc=boundary_utc, replay_rule=HOLDOUT_REPLAY_RULE
                ),
                prior_record_sha256="",
                pinned_at=boundary_utc,
            )
            record.flush()
            return record
        boundary_utc = str(document.get("boundary_utc") or "")
        boundary_ms = _optional_int(document.get("boundary_ms"))
        if not boundary_utc or boundary_ms is None or boundary_ms <= 0:
            raise ResumeIntegrityError(
                "retained holdout boundary has no authenticated instant",
                context={"path": str(path)},
            )
        replay_rule = str(document.get("replay_rule") or "")
        expected = holdout_boundary_id(boundary_utc=boundary_utc, replay_rule=replay_rule)
        if str(document.get("boundary_id") or "") != expected:
            raise ResumeIntegrityError(
                "retained holdout boundary identity does not match its own record",
                context={"path": str(path), "expected": expected},
            )
        if _iso_to_ms(boundary_utc) != boundary_ms:
            raise ResumeIntegrityError(
                "retained holdout boundary instant disagrees with its timestamp",
                context={"path": str(path)},
            )
        return cls(
            path=path,
            boundary_utc=boundary_utc,
            boundary_ms=boundary_ms,
            boundary_id=expected,
            prior_record_sha256=str(document.get("prior_record_sha256") or ""),
            pinned_at=str(document.get("pinned_at") or boundary_utc),
            replay_rule=replay_rule,
        )

    def flush(self) -> None:
        _atomic_write_json(
            self.path,
            _checkpoint_document(
                "holdout_boundary",
                {
                    "boundary_utc": self.boundary_utc,
                    "boundary_ms": self.boundary_ms,
                    "boundary_id": self.boundary_id,
                    "prior_record_sha256": self.prior_record_sha256,
                    "pinned_at": self.pinned_at,
                    "replay_rule": self.replay_rule,
                },
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_state": "pinned_before_model_outcomes",
            "boundary_utc": self.boundary_utc,
            "boundary_ms": self.boundary_ms,
            "boundary_id": self.boundary_id,
            "prior_record_sha256": self.prior_record_sha256,
            "pinned_at": self.pinned_at,
            "replay_rule": self.replay_rule,
            "outcome_blind": True,
            "record_path": str(self.path),
            "stream_collector_authorized": False,
            "retrieval_clock": (
                "retrieval time is the instant this qualifier fetched an object; it is "
                "never used as the observation time of the data inside it"
            ),
            "source_availability_clock": (
                "source availability is the archive's own published interval; a later "
                "retrieval never backdates availability"
            ),
            "note": (
                "CEX-002 pins a prospective holdout boundary and honest retrieval/"
                "availability clocks; it does not acquire live trade, BBO, depth, "
                "liquidation, or OI streams"
            ),
        }


def prospective_holdout_record(boundary: HoldoutBoundary | None = None) -> dict[str, Any]:
    if boundary is None:
        return {
            "boundary_state": "unpinned",
            "stream_collector_authorized": False,
            "outcome_blind": True,
            "note": "no durable holdout boundary record is available in this store",
        }
    return boundary.to_dict()


def _month_range(first: str, last: str) -> list[str]:
    start_year, start_month = (int(part) for part in first.split("-"))
    end_year, end_month = (int(part) for part in last.split("-"))
    months: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


def temporal_group_gaps(
    *,
    symbol: str,
    family_group: str,
    families: Sequence[str],
    periods: Sequence[str],
    group_first: str | None,
    group_last: str | None,
    onboard_period: str | None,
    close_period: str | None,
    currently_listed: bool,
) -> list[dict[str, Any]]:
    """Typed temporal gaps for one symbol in one logical family group.

    Expected windows come from authenticated contract lifecycle evidence and the family's
    own global launch/latest cutoff, never from the symbol's own observations. Only an
    affirmatively explained pre-listing, family-launch, or post-close interval is
    nonblocking; an unexplained head, an unknown boundary, and a missing recent tail for a
    currently listed contract all stay blocking evidence.
    """
    observed = sorted(set(periods))
    if not observed:
        return []
    gaps: list[dict[str, Any]] = []
    base = {
        "symbol": symbol,
        "family_group": family_group,
        "families": list(families),
        "observed_months": len(observed),
        "first_observed": observed[0],
        "last_observed": observed[-1],
        "family_first_observed": group_first,
        "family_last_observed": group_last,
        "onboard_period": onboard_period,
        "close_period": close_period,
    }
    seen = set(observed)
    missing = [
        month for month in _month_range(observed[0], observed[-1]) if month not in seen
    ]
    if missing:
        gaps.append(
            {
                **base,
                "status": "interior_month_gap",
                "kind": "interior_month_gap",
                "blocking": True,
                "missing_months": missing[:24],
                "missing_month_count": len(missing),
            }
        )
    if group_first is not None:
        if observed[0] > group_first:
            if onboard_period is not None and observed[0] <= onboard_period:
                gaps.append(
                    {
                        **base,
                        "status": "head_gap_pre_listing",
                        "kind": "head_gap_pre_listing",
                        "blocking": False,
                        "explained_by": "authenticated_onboard_date",
                    }
                )
            elif onboard_period is None:
                gaps.append(
                    {
                        **base,
                        "status": "head_gap_unknown_onboard",
                        "kind": "head_gap_unknown_onboard",
                        "blocking": True,
                        "explained_by": "",
                    }
                )
            else:
                gaps.append(
                    {
                        **base,
                        "status": "head_gap_unexplained",
                        "kind": "head_gap_unexplained",
                        "blocking": True,
                        "explained_by": "",
                    }
                )
        elif onboard_period is not None and onboard_period < observed[0]:
            gaps.append(
                {
                    **base,
                    "status": "head_gap_family_launch",
                    "kind": "head_gap_family_launch",
                    "blocking": False,
                    "explained_by": "source_family_launch",
                }
            )
    if group_last is not None and observed[-1] < group_last:
        if close_period is not None and observed[-1] >= close_period:
            gaps.append(
                {
                    **base,
                    "status": "tail_gap_post_close",
                    "kind": "tail_gap_post_close",
                    "blocking": False,
                    "explained_by": "authenticated_close_or_delivery",
                }
            )
        elif close_period is not None:
            gaps.append(
                {
                    **base,
                    "status": "tail_gap_unexplained",
                    "kind": "tail_gap_unexplained",
                    "blocking": True,
                    "explained_by": "",
                }
            )
        elif currently_listed:
            gaps.append(
                {
                    **base,
                    "status": "tail_gap_missing_recent",
                    "kind": "tail_gap_missing_recent",
                    "blocking": True,
                    "explained_by": "",
                }
            )
        else:
            gaps.append(
                {
                    **base,
                    "status": "tail_gap_unknown_close",
                    "kind": "tail_gap_unknown_close",
                    "blocking": True,
                    "explained_by": "",
                }
            )
    return gaps


def contract_lifecycle_windows(
    lifecycle_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, str | None]]:
    """Authenticated onboard and close months per symbol, or ``None`` when unproved."""
    windows: dict[str, dict[str, str | None]] = {}
    for symbol, row in lifecycle_rows.items():
        windows[symbol] = {
            "onboard_period": ms_to_period(_optional_int(row.get("onboard_ms"))),
            "close_period": ms_to_period(contract_close_ms(row)),
        }
    return windows


def universe_coverage_gaps(
    *,
    universe: Sequence[str],
    families: Sequence[str],
    family_symbol_lists: Mapping[str, set[str]],
    family_symbol_objects: Mapping[tuple[str, str], int],
    family_symbol_periods: Mapping[tuple[str, str], tuple[str, ...]],
    currently_listed: Sequence[str],
    lifecycle_windows: Mapping[str, Mapping[str, str | None]],
    require_every_group: bool,
) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...], tuple[str, ...]]:
    """Coverage of the accepted universe, separated into blocking and typed gaps.

    ``require_every_group`` demands every logical family group for every symbol; the
    union-membership product only demands that a symbol be evidenced somewhere. The
    return is (gaps, blocking symbols, symbols whose only gaps are explained facts).
    """
    groups: dict[str, list[str]] = {}
    for family in families:
        groups.setdefault(_family_group(family), []).append(family)
    listed_now = set(currently_listed)
    family_first: dict[str, str] = {}
    family_last: dict[str, str] = {}
    for (family, _symbol), periods in family_symbol_periods.items():
        if not periods:
            continue
        earliest, latest = min(periods), max(periods)
        if family not in family_first or earliest < family_first[family]:
            family_first[family] = earliest
        if family not in family_last or latest > family_last[family]:
            family_last[family] = latest
    group_first_seen: dict[str, str] = {}
    group_last_seen: dict[str, str] = {}
    for group, group_families in groups.items():
        firsts = [family_first[family] for family in group_families if family in family_first]
        lasts = [family_last[family] for family in group_families if family in family_last]
        if firsts:
            group_first_seen[group] = min(firsts)
        if lasts:
            group_last_seen[group] = max(lasts)
    gaps: list[dict[str, Any]] = []
    blocking: set[str] = set()
    typed: set[str] = set()
    for symbol in sorted(set(universe)):
        window = lifecycle_windows.get(symbol, {})
        symbol_gaps: list[dict[str, Any]] = []
        covered_groups = 0
        for group in sorted(groups):
            group_families = tuple(groups[group])
            objects = sum(
                family_symbol_objects.get((family, symbol), 0) for family in group_families
            )
            if objects <= 0:
                listed = any(
                    symbol in family_symbol_lists.get(family, set()) for family in group_families
                )
                if symbol in listed_now and not listed:
                    status = "current_unarchived"
                else:
                    status = "listed_prefix_empty" if listed else "absent_family_prefix"
                symbol_gaps.append(
                    {
                        "symbol": symbol,
                        "family_group": group,
                        "families": list(group_families),
                        "status": status,
                        "kind": status,
                        "blocking": True,
                        "objects": 0,
                    }
                )
                continue
            covered_groups += 1
            symbol_gaps.extend(
                temporal_group_gaps(
                    symbol=symbol,
                    family_group=group,
                    families=group_families,
                    periods=[
                        period
                        for family in group_families
                        for period in family_symbol_periods.get((family, symbol), ())
                    ],
                    group_first=group_first_seen.get(group),
                    group_last=group_last_seen.get(group),
                    onboard_period=window.get("onboard_period"),
                    close_period=window.get("close_period"),
                    currently_listed=symbol in listed_now,
                )
            )
        if not require_every_group:
            # Union membership only needs a symbol evidenced somewhere, so a single
            # group's absence is not itself a membership gap.
            absent = {"absent_family_prefix", "listed_prefix_empty", "current_unarchived"}
            symbol_gaps = [item for item in symbol_gaps if item["status"] not in absent]
            if covered_groups == 0:
                status = "current_unarchived" if symbol in listed_now else "no_family_evidence"
                symbol_gaps.append(
                    {
                        "symbol": symbol,
                        "family_group": "any",
                        "families": list(families),
                        "status": status,
                        "kind": status,
                        "blocking": True,
                        "objects": 0,
                    }
                )
        if not symbol_gaps:
            continue
        gaps.extend(symbol_gaps)
        if any(item["blocking"] for item in symbol_gaps):
            blocking.add(symbol)
        else:
            typed.add(symbol)
    return tuple(gaps), tuple(sorted(blocking)), tuple(sorted(typed))


@dataclass(frozen=True, slots=True)
class PhysicalRequirement:
    """Deduplicated physical source objects behind the accepted universe."""

    object_count: int
    byte_total: int
    unknown_size_objects: int
    keys: frozenset[str]


def physical_source_requirement(
    *,
    inventory: Mapping[str, FamilyInventory],
    family_products: Mapping[str, tuple[str, ...]],
    universe: Sequence[str],
) -> PhysicalRequirement:
    """Count each physical object once, however many logical products claim it.

    Per-product logical totals overlap heavily (one trades object serves membership and
    trades), so they can never be summed into a storage requirement.
    """
    members = set(universe)
    sizes: dict[str, int] = {}
    unknown = 0
    for family, entry in sorted(inventory.items()):
        if not family_products.get(family):
            continue
        for symbol, objects in entry.objects.items():
            if symbol not in members:
                continue
            for obj in objects:
                if obj.key in sizes:
                    continue
                if obj.size is None:
                    unknown += 1
                    sizes[obj.key] = 0
                    continue
                sizes[obj.key] = int(obj.size)
    return PhysicalRequirement(
        object_count=len(sizes),
        byte_total=sum(sizes.values()),
        unknown_size_objects=unknown,
        keys=frozenset(sizes),
    )


def available_bytes(path: Path) -> int | None:
    try:
        return int(shutil.disk_usage(path).free)
    except OSError:
        return None


def storage_feasibility(
    *,
    requirement: PhysicalRequirement,
    retained_credit_bytes: int,
    retained_credit_objects: int,
    local_available_bytes: int | None,
    unverified_credit_objects: int = 0,
    normalized_catalog_bytes: int | None = None,
    temporary_high_water_bytes: int | None = None,
    operating_reserve_bytes: int | None = None,
) -> dict[str, Any]:
    """Exact physical Gate 2 requirement against real local capacity.

    Normalized/catalog storage is an additional, unmeasured bound; it is reported as
    unknown and never treated as zero. Insufficiency blocks Gate 2 and never relabels a
    qualified source as inaccessible.
    """
    projected_new = max(requirement.byte_total - int(retained_credit_bytes), 0)
    shortfall = (
        None
        if local_available_bytes is None
        else max(projected_new - int(local_available_bytes), 0)
    )
    raw_sufficient = (
        None
        if shortfall is None
        else bool(shortfall == 0 and requirement.unknown_size_objects == 0)
    )
    unknown_components = [
        name
        for name, value in (
            ("normalized_catalog_bytes", normalized_catalog_bytes),
            ("temporary_high_water_bytes", temporary_high_water_bytes),
            ("operating_reserve_bytes", operating_reserve_bytes),
        )
        if value is None
    ]
    if raw_sufficient is False:
        gate2_state = "insufficient"
    elif raw_sufficient is None or unknown_components:
        # ADR-0017: an unknown total requirement can never pass Gate 2.
        gate2_state = "unknown"
    else:
        gate2_state = "sufficient"
    total_required = (
        None
        if unknown_components
        else projected_new
        + int(normalized_catalog_bytes or 0)
        + int(temporary_high_water_bytes or 0)
        + int(operating_reserve_bytes or 0)
    )
    return {
        "physical_object_count": requirement.object_count,
        "physical_compressed_raw_bytes": requirement.byte_total,
        "unknown_size_objects": requirement.unknown_size_objects,
        "retained_verified_credit_objects": int(retained_credit_objects),
        "retained_verified_credit_bytes": int(retained_credit_bytes),
        "unverified_retained_objects": int(unverified_credit_objects),
        "credit_rule": (
            "credit requires a rehashed content-addressed object and a re-proved provider "
            "sidecar; unverified rows are excluded, never assumed present"
        ),
        "projected_new_compressed_raw_bytes": projected_new,
        "local_available_bytes": local_available_bytes,
        "shortfall_bytes": shortfall,
        "raw_storage_sufficient": raw_sufficient,
        "normalized_catalog_bytes": {
            "state": "unknown" if normalized_catalog_bytes is None else "measured",
            "bytes": normalized_catalog_bytes,
            "treated_as_zero": False,
            "note": (
                "normalized/Nautilus catalog storage is an additional bound on top of "
                "compressed raw and must be measured before Gate 2, never assumed zero"
            ),
        },
        "unknown_total_components": unknown_components,
        "total_required_bytes": total_required,
        "gate2_storage_state": gate2_state,
        "gate2_storage_rule": (
            "Gate 2 stays unproved while normalized, temporary high-water, reserve, or "
            "total capacity is unknown; only measured raw insufficiency may be asserted "
            "early"
        ),
        "deduplication": "each physical object counted once across every logical product",
        "note": (
            "per-product logical byte totals overlap and are reported separately; they "
            "are never summed into this requirement"
        ),
    }


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


# Native identity, contract class, status, and lifecycle boundaries are all required.
# A row missing any of them cannot support classification or a temporal window, so it
# fails closed instead of silently qualifying on a partial record.
REQUIRED_EXCHANGE_ROW_FIELDS: tuple[str, ...] = (
    "symbol",
    "pair",
    "contractType",
    "status",
    "underlyingType",
    "baseAsset",
    "quoteAsset",
    "marginAsset",
    "onboardDate",
    "deliveryDate",
)
_OPTIONAL_EXCHANGE_ROW_FIELDS: tuple[str, ...] = ("contractStatus", "underlyingSubType")
# Binance stamps a year-2100 sentinel delivery date on contracts that never deliver.
PERPETUAL_DELIVERY_SENTINEL_MS: int = 4_102_444_800_000
CLOSED_CONTRACT_STATUSES: frozenset[str] = frozenset(
    {"SETTLING", "CLOSE", "CLOSED", "DELISTED", "END_OF_DAY"}
)
# Official USD-M contract status enum. An unknown value is unproved semantics, never a
# tradable crypto perpetual by default.
SUPPORTED_CONTRACT_STATUSES: frozenset[str] = frozenset(
    {
        "PENDING_TRADING",
        "TRADING",
        "PRE_DELIVERING",
        "DELIVERING",
        "DELIVERED",
        "PRE_SETTLE",
        "SETTLING",
        "CLOSE",
    }
)
# Official USD-M underlying types for crypto contracts. TradFi is reported separately and
# anything else is unproved, so crypto authority is never inferred from "not TradFi".
SUPPORTED_CRYPTO_UNDERLYING_TYPES: frozenset[str] = frozenset({"COIN", "INDEX"})

SEMANTICS_SUPPORTED: str = "supported"
SEMANTICS_UNKNOWN_UNDERLYING: str = "unsupported_underlying_type"
SEMANTICS_UNKNOWN_STATUS: str = "unsupported_contract_status"
SEMANTICS_INCOHERENT_IDENTITY: str = "incoherent_contract_identity"


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _require_identity_text(value: Any, *, field: str, symbol: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise SourceQualificationError(
            "exchangeInfo row has an empty contract identity field",
            context={"symbol": symbol, "field": field},
        )
    return text


def _require_lifecycle_ms(value: Any, *, field: str, symbol: str) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed < 0:
        raise SourceQualificationError(
            "exchangeInfo row has an invalid contract lifecycle boundary",
            context={"symbol": symbol, "field": field, "value": str(value)},
        )
    return parsed


def exchange_info_server_time_ms(payload: Mapping[str, Any]) -> int:
    """Authenticated response time, from the payload itself rather than a local field."""
    server_time = _optional_int(payload.get("serverTime"))
    if server_time is None or server_time <= 0:
        raise SourceQualificationError(
            "exchangeInfo payload has no authenticated serverTime",
            context={"server_time": str(payload.get("serverTime"))},
        )
    return server_time


def parse_exchange_info_rows(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Complete authenticated current contract rows, keyed by native symbol.

    Every field needed to prove native identity, contract type, status, underlying type,
    and lifecycle boundaries is required; nothing is reduced to a name list, and a partial
    row is rejected rather than accepted with unknown identity.
    """
    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise SourceQualificationError(
            "exchangeInfo payload is missing symbols[]",
            context={"keys": sorted(payload.keys())},
        )
    server_time = exchange_info_server_time_ms(payload)
    rows: dict[str, dict[str, Any]] = {}
    for item in symbols:
        if not isinstance(item, dict):
            raise SourceQualificationError("exchangeInfo symbol row is not an object")
        missing = [field for field in REQUIRED_EXCHANGE_ROW_FIELDS if field not in item]
        if missing:
            raise SourceQualificationError(
                "exchangeInfo row is missing required contract identity fields",
                context={"symbol": str(item.get("symbol") or ""), "missing": missing},
            )
        name = str(item["symbol"]).strip().upper()
        if not name:
            raise SourceQualificationError("exchangeInfo row has an empty symbol")
        if name in rows:
            raise SourceQualificationError(
                "exchangeInfo contains duplicate native contract symbols",
                context={"symbol": name},
            )
        row: dict[str, Any] = {
            field: item.get(field)
            for field in (*REQUIRED_EXCHANGE_ROW_FIELDS, *_OPTIONAL_EXCHANGE_ROW_FIELDS)
            if field in item
        }
        row["symbol"] = name
        # Present-but-empty identity is the same fail-open hole as a missing key.
        row["pair"] = _require_identity_text(item.get("pair"), field="pair", symbol=name)
        row["contract_type"] = _require_identity_text(
            item.get("contractType"), field="contractType", symbol=name
        ).upper()
        row["underlying_type"] = _require_identity_text(
            item.get("underlyingType"), field="underlyingType", symbol=name
        ).upper()
        row["status"] = _require_identity_text(
            item.get("status"), field="status", symbol=name
        ).upper()
        row["base_asset"] = _require_identity_text(
            item.get("baseAsset"), field="baseAsset", symbol=name
        ).upper()
        row["quote_asset"] = _require_identity_text(
            item.get("quoteAsset"), field="quoteAsset", symbol=name
        ).upper()
        row["margin_asset"] = _require_identity_text(
            item.get("marginAsset"), field="marginAsset", symbol=name
        ).upper()
        row["onboard_ms"] = _require_lifecycle_ms(
            item.get("onboardDate"), field="onboardDate", symbol=name
        )
        row["delivery_ms"] = _require_lifecycle_ms(
            item.get("deliveryDate"), field="deliveryDate", symbol=name
        )
        row["server_time_ms"] = server_time
        rows[name] = row
    if not rows:
        raise SourceQualificationError("exchangeInfo contains no contract rows")
    return rows


def canonical_contract_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Stable canonical semantics of one contract row.

    Response-wide volatility - the fetch's ``serverTime`` and raw digest - is deliberately
    excluded. Binance stamps a new ``serverTime`` on every live fetch, so hashing it would
    make an ordinary resume look like an authority change. The lifecycle boundary is the
    persisted first authenticated closed observation, not the current response time.
    """
    return {
        "symbol": str(row.get("symbol") or ""),
        "pair": str(row.get("pair") or ""),
        "contract_type": str(row.get("contract_type") or ""),
        "status": str(row.get("status") or ""),
        "underlying_type": str(row.get("underlying_type") or ""),
        "base_asset": str(row.get("base_asset") or ""),
        "quote_asset": str(row.get("quote_asset") or ""),
        "margin_asset": str(row.get("margin_asset") or ""),
        "onboard_ms": _optional_int(row.get("onboard_ms")),
        "delivery_ms": _optional_int(row.get("delivery_ms")),
        "closed_observed_ms": _optional_int(row.get("closed_observed_ms")),
        "semantics_state": contract_semantics_state(row),
    }


def contract_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    """Volatile provenance of the response a row was proved from.

    It is retained and validated on every run, but never hashed into the immutable plan
    comparison or the semantic report identity.
    """
    return {
        "server_time_ms": _optional_int(row.get("server_time_ms")),
        "response_sha256": str(row.get("response_sha256") or ""),
        "response_byte_size": _optional_int(row.get("response_byte_size")),
        "observed_at": str(row.get("observed_at") or ""),
    }


def contract_close_ms(row: Mapping[str, Any]) -> int | None:
    """Authenticated close/delivery instant, or ``None`` when the row proves none."""
    delivery = _optional_int(row.get("delivery_ms") or row.get("deliveryDate"))
    if delivery is not None and 0 < delivery < PERPETUAL_DELIVERY_SENTINEL_MS:
        return delivery
    status = str(row.get("status") or row.get("contractStatus") or "").strip().upper()
    if status in CLOSED_CONTRACT_STATUSES:
        # The boundary is the persisted first authenticated closed observation, so it
        # never moves when a later fetch reports a new response time.
        observed = _optional_int(row.get("closed_observed_ms"))
        if observed is not None and observed > 0:
            return observed
    return None


def ms_to_period(value: int | None) -> str | None:
    if value is None or value <= 0:
        return None
    moment = datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    return f"{moment.year:04d}-{moment.month:02d}"


def is_tradifi_row(row: Mapping[str, Any]) -> bool:
    contract = str(row.get("contract_type") or row.get("contractType") or "").strip().upper()
    underlying = str(row.get("underlying_type") or row.get("underlyingType") or "").strip().upper()
    return contract in TRADIFI_CONTRACT_TYPES or underlying in TRADIFI_UNDERLYING_TYPES


def contract_semantics_state(row: Mapping[str, Any]) -> str:
    """Whether a row's official enums and identity relationships are positively supported.

    Crypto authority is only ever granted on official semantics that are recognised here.
    An unknown underlying type, an unknown status, or a contract whose native identity is
    internally incoherent is typed blocking evidence rather than a default acceptance.
    """
    underlying = str(row.get("underlying_type") or row.get("underlyingType") or "").strip().upper()
    if underlying not in SUPPORTED_CRYPTO_UNDERLYING_TYPES:
        return SEMANTICS_UNKNOWN_UNDERLYING
    status = str(row.get("status") or row.get("contractStatus") or "").strip().upper()
    if status not in SUPPORTED_CONTRACT_STATUSES:
        return SEMANTICS_UNKNOWN_STATUS
    symbol = str(row.get("symbol") or "").strip().upper()
    pair = str(row.get("pair") or "").strip().upper()
    base = str(row.get("base_asset") or "").strip().upper()
    quote = str(row.get("quote_asset") or "").strip().upper()
    margin = str(row.get("margin_asset") or "").strip().upper()
    contract = str(row.get("contract_type") or row.get("contractType") or "").strip().upper()
    if pair != f"{base}{quote}":
        return SEMANTICS_INCOHERENT_IDENTITY
    if margin != quote:
        # USD-M contracts settle in their quote asset.
        return SEMANTICS_INCOHERENT_IDENTITY
    if contract == PERPETUAL_CONTRACT_TYPE and symbol != pair:
        # A perpetual's native symbol is its pair; a dated contract's is not.
        return SEMANTICS_INCOHERENT_IDENTITY
    return SEMANTICS_SUPPORTED


def is_confirmed_perpetual_row(row: Mapping[str, Any]) -> bool:
    """Exactly ``PERPETUAL`` with positively supported official crypto semantics.

    ADR-0017 scope is the crypto USD-M perpetual venue. Any other contract class, an
    unknown enum, or an incoherent identity stays reported and excluded until official
    evidence or a future ADR supports it.
    """
    contract = str(row.get("contract_type") or row.get("contractType") or "").strip().upper()
    if contract != PERPETUAL_CONTRACT_TYPE:
        return False
    if is_tradifi_row(row):
        return False
    return contract_semantics_state(row) == SEMANTICS_SUPPORTED


def parse_current_perpetuals(payload: Mapping[str, Any]) -> list[str]:
    rows = parse_exchange_info_rows(payload)
    current = sorted(name for name, row in rows.items() if is_confirmed_perpetual_row(row))
    if not current:
        raise SourceQualificationError("exchangeInfo contains no PERPETUAL contracts")
    return current


def _name_pattern_hint(symbol: str) -> str:
    if _SETTLEMENT_NAME_RE.search(symbol):
        return "settlement_suffix"
    if _DATED_DELIVERY_NAME_RE.match(symbol):
        return "dated_delivery_suffix"
    return "none"


def _class_from_row(row: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    """Membership class implied by one official contract row, evidence-first."""
    if is_confirmed_perpetual_row(row):
        return MEMBERSHIP_CONFIRMED
    if is_tradifi_row(row):
        return MEMBERSHIP_TRADIFI
    if str(record.get("contract_type") or "") in DELIVERY_CONTRACT_TYPES:
        return MEMBERSHIP_DELIVERY
    if str(record.get("semantics_state") or "") != SEMANTICS_SUPPORTED:
        # Official evidence exists but its semantics are unproved; it blocks rather than
        # being promoted or silently excluded.
        return MEMBERSHIP_UNSUPPORTED_SEMANTICS
    return MEMBERSHIP_UNRESOLVED


@dataclass(frozen=True, slots=True)
class MembershipClassification:
    """One archive or exchange name with its affirmative official evidence, if any."""

    symbol: str
    membership_class: str
    evidence: tuple[Mapping[str, Any], ...]
    name_pattern_hint: str
    in_archive: bool
    in_current_exchange: bool

    @property
    def accepted(self) -> bool:
        return self.membership_class == MEMBERSHIP_CONFIRMED

    @property
    def blocking(self) -> bool:
        return self.membership_class in MEMBERSHIP_BLOCKING_CLASSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "membership_class": self.membership_class,
            "evidence": [dict(item) for item in self.evidence],
            "name_pattern_hint": self.name_pattern_hint,
            "in_archive": self.in_archive,
            "in_current_exchange": self.in_current_exchange,
            "accepted": self.accepted,
            "blocking": self.blocking,
        }


def funding_membership_evidence(
    inventory: Mapping[str, FamilyInventory],
) -> dict[str, dict[str, Any]]:
    """Symbols with at least one official realized-funding archive object.

    Delivery contracts never realize funding, so this is affirmative perpetual evidence
    drawn from the official archive itself rather than from a directory name.
    """
    evidence: dict[str, dict[str, Any]] = {}
    for family in FUNDING_EVIDENCE_FAMILIES:
        entry = inventory.get(family)
        if entry is None or not entry.listed:
            continue
        for symbol, objects in entry.objects.items():
            if not objects:
                continue
            found = evidence.setdefault(
                symbol, {"families": [], "object_count": 0, "example_key": objects[0].key}
            )
            found["families"].append(family)
            found["object_count"] += len(objects)
    return evidence


def classify_membership(
    *,
    discovered: Sequence[str],
    current_rows: Mapping[str, Mapping[str, Any]],
    historical_rows: Mapping[str, Mapping[str, Any]],
    funding_evidence: Mapping[str, Mapping[str, Any]],
    current_response_sha256: str = "",
) -> tuple[MembershipClassification, ...]:
    """Classify every observed name from affirmative official evidence only.

    Precedence is evidence-first: an authenticated current row, then a retained official
    historical contract-metadata row, then an official realized-funding observation. A
    name with no official evidence stays unresolved and blocks membership; its spelling is
    recorded as an audit hint and never decides the class.
    """
    archive = set(discovered)
    names = sorted(archive | set(current_rows))
    out: list[MembershipClassification] = []
    for symbol in names:
        evidence: list[Mapping[str, Any]] = []
        membership_class = MEMBERSHIP_UNRESOLVED
        current = current_rows.get(symbol)
        historical = historical_rows.get(symbol)
        funding = funding_evidence.get(symbol)
        if current is not None:
            record = {
                "kind": "authenticated_current_exchange_info",
                "endpoint": OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"],
                **canonical_contract_row(current),
                **contract_provenance(
                    {"response_sha256": current_response_sha256, **current}
                ),
            }
            evidence.append(record)
            membership_class = _class_from_row(current, record)
        if membership_class == MEMBERSHIP_UNRESOLVED and historical is not None:
            record = {
                "kind": "retained_official_contract_metadata",
                "source": str(historical.get("source") or ""),
                "response_content_path": str(historical.get("response_content_path") or ""),
                **canonical_contract_row(historical),
                **contract_provenance(historical),
            }
            evidence.append(record)
            membership_class = _class_from_row(historical, record)
        if membership_class == MEMBERSHIP_UNRESOLVED and funding is not None:
            evidence.append(
                {
                    "kind": "official_realized_funding_observation",
                    "families": list(funding.get("families", ())),
                    "object_count": int(funding.get("object_count") or 0),
                    "example_key": str(funding.get("example_key") or ""),
                    "semantics": "only a perpetual contract realizes funding",
                }
            )
            membership_class = MEMBERSHIP_CONFIRMED
        hint = _name_pattern_hint(symbol)
        if membership_class == MEMBERSHIP_UNRESOLVED:
            if hint == "settlement_suffix":
                membership_class = MEMBERSHIP_SETTLEMENT_ARTIFACT
            elif hint == "dated_delivery_suffix":
                membership_class = MEMBERSHIP_DATED_DELIVERY
        out.append(
            MembershipClassification(
                symbol=symbol,
                membership_class=membership_class,
                evidence=tuple(evidence),
                name_pattern_hint=hint,
                in_archive=symbol in archive,
                in_current_exchange=symbol in current_rows,
            )
        )
    return tuple(out)


def validate_exchange_info_response(response: ExchangeInfoResponse) -> Mapping[str, Any]:
    """Prove a contract response before anything is derived from it.

    The endpoint, byte count, digest, retrieval time, and retained content path must all
    agree with the raw bytes, and the parsed payload must be exactly what those bytes
    decode to. A source can therefore never retain one universe and classify another.
    """
    endpoint = OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"]
    if response.endpoint != endpoint:
        raise SourceQualificationError(
            "contract response is not the official exchangeInfo endpoint",
            context={"endpoint": response.endpoint, "expected": endpoint},
        )
    raw = response.raw_bytes
    if not isinstance(raw, bytes) or not raw:
        raise SourceQualificationError(
            "contract response retained no raw bytes", context={"endpoint": endpoint}
        )
    if int(response.byte_size) != len(raw):
        raise ResumeIntegrityError(
            "contract response byte count disagrees with its retained bytes",
            context={"reported": response.byte_size, "actual": len(raw)},
        )
    digest = _object_sha256(raw)
    if response.sha256 != digest:
        raise ResumeIntegrityError(
            "contract response digest disagrees with its retained bytes",
            context={"reported": response.sha256, "actual": digest},
        )
    if _iso_to_ms(response.retrieval_time) is None:
        raise SourceQualificationError(
            "contract response has no parseable retrieval time",
            context={"retrieval_time": response.retrieval_time},
        )
    if response.content_path:
        blob = Path(response.content_path)
        if not blob.is_file() or blob.name != digest or compute_sha256(blob) != digest:
            raise ResumeIntegrityError(
                "contract response content path is not its retained content address",
                context={"content_path": response.content_path, "sha256": digest},
            )
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceQualificationError(
            "contract response bytes are not readable JSON", context={"sha256": digest}
        ) from exc
    if not isinstance(parsed, dict):
        raise SourceQualificationError(
            "contract response is not an object", context={"sha256": digest}
        )
    if response.payload != parsed:
        raise ResumeIntegrityError(
            "contract response payload is not what its retained bytes decode to",
            context={"sha256": digest},
        )
    # Everything downstream reads the proved bytes, not the supplied mapping.
    return parsed


def persist_exchange_info_snapshot(body: bytes, *, snapshot_dir: Path) -> tuple[Path, str]:
    """Retain an exchangeInfo response content-addressably before it is relied on."""
    digest = _object_sha256(body)
    dest = content_addressed_path(snapshot_dir, digest)
    if dest.exists():
        existing = compute_sha256(dest)
        if existing != digest:
            raise ResumeIntegrityError(
                "retained exchangeInfo path holds different content than its address",
                context={"path": str(dest), "expected": digest, "actual": existing},
            )
        return dest, digest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".partial-{digest}.part")
    tmp.write_bytes(body)
    tmp.replace(dest)
    return dest, digest


@dataclass(frozen=True, slots=True)
class StagedContractObservation:
    """Live exchangeInfo semantics that have not yet been committed to the store.

    Classification and plan-input comparison read this view. The durable metadata
    index and content-addressed snapshot set stay unchanged until the locked plan
    accepts the inputs, or until the first plan is established.
    """

    response: ExchangeInfoResponse
    enriched_rows: dict[str, dict[str, Any]]
    observed_at: str


@dataclass
class OfficialContractMetadataStore:
    """Retained official contract responses, so today's proof survives a delisting.

    The store never trusts a copied field. It records which content-addressed
    exchangeInfo response first evidenced each symbol; every reuse rehashes those exact
    bytes, reparses them, and re-proves that the row is present.
    """

    path: Path
    snapshot_dir: Path
    snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    symbol_snapshot: dict[str, str] = field(default_factory=dict)
    # First authenticated closed observation per symbol. A lifecycle bound must not move
    # every time a later fetch reports a new response time.
    closed_observations: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, *, snapshot_dir: Path) -> OfficialContractMetadataStore:
        document = read_checkpoint_document(path, kind="official_contract_metadata")
        if document is None:
            return cls(path=path, snapshot_dir=snapshot_dir)
        snapshots = document.get("snapshots")
        symbols = document.get("symbol_snapshot")
        if not isinstance(snapshots, dict) or not isinstance(symbols, dict):
            raise ResumeIntegrityError(
                "official contract metadata document is malformed",
                context={"path": str(path)},
            )
        store = cls(path=path, snapshot_dir=snapshot_dir)
        for digest, snapshot in snapshots.items():
            if not isinstance(snapshot, dict):
                raise ResumeIntegrityError(
                    "retained exchangeInfo snapshot is not an object",
                    context={"path": str(path), "sha256": str(digest)},
                )
            store.snapshots[
                _require_hex_digest(
                    digest, label="snapshot digest", context={"path": str(path)}
                )
            ] = dict(snapshot)
        for symbol, digest in symbols.items():
            store.symbol_snapshot[str(symbol)] = _require_hex_digest(
                digest, label="snapshot digest", context={"path": str(path), "symbol": symbol}
            )
        closed = document.get("closed_observations", {})
        if not isinstance(closed, dict):
            raise ResumeIntegrityError(
                "retained closed observations are malformed", context={"path": str(path)}
            )
        for symbol, record in closed.items():
            if not isinstance(record, dict):
                raise ResumeIntegrityError(
                    "retained closed observation is not an object",
                    context={"path": str(path), "symbol": str(symbol)},
                )
            observed = _optional_int(record.get("server_time_ms"))
            if observed is None or observed <= 0:
                raise ResumeIntegrityError(
                    "retained closed observation has no authenticated response time",
                    context={"path": str(path), "symbol": str(symbol)},
                )
            _require_hex_digest(
                record.get("response_sha256"),
                label="closed observation response digest",
                context={"path": str(path), "symbol": str(symbol)},
            )
            store.closed_observations[str(symbol)] = dict(record)
        return store

    def enrich(self, rows: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
        """Attach the persisted first closed observation to each row that has one."""
        enriched: dict[str, dict[str, Any]] = {}
        for symbol, row in rows.items():
            record = self.closed_observations.get(symbol)
            merged = dict(row)
            if record is not None:
                merged["closed_observed_ms"] = _optional_int(record.get("server_time_ms"))
                merged["closed_observed_status"] = str(record.get("status") or "")
            enriched[symbol] = merged
        return enriched

    def _first_closed_record(
        self, symbol: str, row: Mapping[str, Any], digest: str
    ) -> dict[str, Any] | None:
        """Candidate first closed observation, or ``None`` when one is already durable."""
        if symbol in self.closed_observations:
            return None
        status = str(row.get("status") or "").strip().upper()
        server_time = _optional_int(row.get("server_time_ms"))
        if status not in CLOSED_CONTRACT_STATUSES:
            return None
        if server_time is None or server_time <= 0:
            return None
        return {
            "server_time_ms": server_time,
            "status": status,
            "response_sha256": digest,
        }

    def stage(
        self,
        response: ExchangeInfoResponse,
        rows: Mapping[str, Mapping[str, Any]],
        *,
        observed_at: str,
    ) -> StagedContractObservation:
        """Return live semantics without writing snapshots or the metadata checkpoint.

        A rejected authority change must leave both durable artifacts byte-for-byte
        unchanged so a later original response can resume the original plan.
        """
        digest = response.sha256
        actual = _object_sha256(response.raw_bytes)
        if actual != digest:
            raise ResumeIntegrityError(
                "staged exchangeInfo digest disagrees with the retained response bytes",
                context={"reported": digest, "actual": actual},
            )
        enriched = self.enrich(rows)
        for symbol, row in rows.items():
            record = self._first_closed_record(symbol, row, digest)
            if record is None:
                continue
            merged = dict(enriched[symbol])
            merged["closed_observed_ms"] = int(record["server_time_ms"])
            merged["closed_observed_status"] = str(record["status"])
            enriched[symbol] = merged
        return StagedContractObservation(
            response=response,
            enriched_rows=enriched,
            observed_at=observed_at,
        )

    def commit(self, staged: StagedContractObservation, *, updated_at: str) -> int:
        """Persist a staged observation after the immutable plan has accepted it."""
        added = self.observe(
            staged.response, staged.enriched_rows, observed_at=staged.observed_at
        )
        self.flush(updated_at=updated_at)
        return added

    def observe(
        self,
        response: ExchangeInfoResponse,
        rows: Mapping[str, Mapping[str, Any]],
        *,
        observed_at: str,
    ) -> int:
        """Retain the raw response, then bind newly evidenced symbols to it."""
        dest, digest = persist_exchange_info_snapshot(
            response.raw_bytes, snapshot_dir=self.snapshot_dir
        )
        if digest != response.sha256:
            raise ResumeIntegrityError(
                "retained exchangeInfo digest disagrees with the reported response",
                context={"reported": response.sha256, "retained": digest},
            )
        self.snapshots.setdefault(
            digest,
            {
                "content_path": str(dest),
                "endpoint": response.endpoint,
                "byte_size": int(response.byte_size),
                "observed_at": observed_at,
                "retrieval_time": response.retrieval_time,
            },
        )
        added = 0
        for symbol, row in rows.items():
            record = self._first_closed_record(symbol, row, digest)
            if record is not None:
                self.closed_observations[symbol] = record
            if symbol in self.symbol_snapshot:
                continue
            self.symbol_snapshot[symbol] = digest
            added += 1
        return added

    def _snapshot_rows(self, digest: str) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        snapshot = self.snapshots.get(digest)
        if snapshot is None:
            raise ResumeIntegrityError(
                "retained contract metadata references an unknown snapshot",
                context={"sha256": digest},
            )
        blob = Path(str(snapshot.get("content_path") or ""))
        if not blob.is_file():
            raise ResumeIntegrityError(
                "retained exchangeInfo response is missing from the store",
                context={"sha256": digest, "path": str(blob)},
            )
        actual = compute_sha256(blob)
        if actual != digest or blob.name != digest:
            raise ResumeIntegrityError(
                "retained exchangeInfo bytes are not at their content address",
                context={"sha256": digest, "actual": actual, "path": str(blob)},
            )
        try:
            payload = json.loads(blob.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResumeIntegrityError(
                "retained exchangeInfo response is unreadable", context={"sha256": digest}
            ) from exc
        if not isinstance(payload, dict):
            raise ResumeIntegrityError(
                "retained exchangeInfo response is not an object", context={"sha256": digest}
            )
        return parse_exchange_info_rows(payload), snapshot

    def historical_rows(self) -> dict[str, dict[str, Any]]:
        """Rows re-proved from the retained response bytes they were observed in."""
        resolved: dict[str, dict[str, Any]] = {}
        cache: dict[str, dict[str, dict[str, Any]]] = {}
        for symbol, digest in sorted(self.symbol_snapshot.items()):
            if digest not in cache:
                rows, snapshot = self._snapshot_rows(digest)
                cache[digest] = rows
                self.snapshots[digest] = {**self.snapshots[digest], **snapshot}
            rows = cache[digest]
            if symbol not in rows:
                raise ResumeIntegrityError(
                    "retained contract metadata claims a symbol its response does not contain",
                    context={"symbol": symbol, "sha256": digest},
                )
            snapshot = self.snapshots[digest]
            row = dict(rows[symbol])
            row["source"] = str(snapshot.get("endpoint") or "")
            row["observed_at"] = str(snapshot.get("observed_at") or "")
            # ``server_time_ms`` already came from the reparsed response, so a mutable
            # local observation field can never move a lifecycle boundary.
            row["response_sha256"] = digest
            row["response_byte_size"] = _optional_int(snapshot.get("byte_size"))
            row["response_content_path"] = str(snapshot.get("content_path") or "")
            resolved[symbol] = row
        return self.enrich(resolved)

    def flush(self, *, updated_at: str) -> None:
        _atomic_write_json(
            self.path,
            _checkpoint_document(
                "official_contract_metadata",
                {
                    "updated_at": updated_at,
                    "snapshots": dict(sorted(self.snapshots.items())),
                    "symbol_snapshot": dict(sorted(self.symbol_snapshot.items())),
                    "closed_observations": dict(sorted(self.closed_observations.items())),
                },
            ),
        )


def _iso_to_ms(value: str) -> int | None:
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


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

    def fetch_exchange_info(self) -> ExchangeInfoResponse:
        endpoint = OFFICIAL_INCREMENTAL_ENDPOINTS["exchangeInfo"]
        result = atomic_download(
            endpoint,
            self._cache_dir,
            transport=self._transport,
            timeout=self._timeout,
            max_bytes=8_388_608,
        )
        raw = result.dest_path.read_bytes()
        digest = _object_sha256(raw)
        if digest != result.sha256:
            raise ResumeIntegrityError(
                "retained exchangeInfo bytes do not match the download digest",
                context={"path": str(result.dest_path), "expected": result.sha256},
            )
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise SourceQualificationError("exchangeInfo response is not an object")
        return ExchangeInfoResponse(
            endpoint=endpoint,
            payload=payload,
            raw_bytes=raw,
            sha256=digest,
            byte_size=len(raw),
            retrieval_time=result.retrieval_utc.astimezone(UTC).isoformat(),
            content_path=str(result.dest_path),
        )


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
        anchor_symbols: Sequence[str],
        universe_symbols: Sequence[str] = (),
        from_ts: int,
        to_ts: int,
    ) -> dict[str, Any]:
        """Qualify Coinalyze on declared stable anchors, then map the whole universe.

        Anchors are fixed, liquid, confirmed Binance perpetuals rather than whichever
        symbols happen to sort first, so a qualification result is reproducible. Anchor
        success is never full coverage: the confirmed universe support/gap map is
        reported separately.
        """
        self._require_key()
        if not anchor_symbols:
            raise SourceQualificationError(
                "Coinalyze qualification requires declared anchor symbols"
            )
        mapped = [coinalyze_perp_symbol(symbol) for symbol in anchor_symbols]
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
        # Markets are keyed by the venue's own native identity, never by a symbol this
        # client constructed; a provider label that disagrees with it is refused.
        # Every Binance perpetual market the support map may use is identity-checked,
        # not only the two anchors, and a duplicate native identity is ambiguous evidence.
        markets_by_native: dict[str, Mapping[str, Any]] = {}
        for row in markets:
            if not isinstance(row, dict):
                continue
            if str(row.get("exchange")) != COINALYZE_EXCHANGE_CODE:
                continue
            if not bool(row.get("is_perpetual")):
                continue
            native = str(row.get("symbol_on_exchange") or "").strip().upper()
            if not native:
                raise SourceQualificationError(
                    "Coinalyze Binance perpetual market has no symbol_on_exchange",
                    context={"symbol": str(row.get("symbol") or "")},
                )
            provider = str(row.get("symbol") or "")
            if provider != coinalyze_perp_symbol(native):
                raise SourceQualificationError(
                    "Coinalyze market symbol disagrees with its native identity",
                    context={
                        "native": native,
                        "provider_symbol": provider,
                        "expected": coinalyze_perp_symbol(native),
                    },
                )
            if native in markets_by_native:
                raise SourceQualificationError(
                    "Coinalyze returned duplicate Binance perpetual native identities",
                    context={"native": native, "provider_symbol": provider},
                )
            markets_by_native[native] = row
        matched_markets: list[Mapping[str, Any]] = []
        anchor_identity: list[dict[str, str]] = []
        for symbol in anchor_symbols:
            native = symbol.strip().upper()
            row = markets_by_native.get(native)
            if row is None:
                continue
            matched_markets.append(row)
            anchor_identity.append(
                {
                    "native_symbol": native,
                    "symbol_on_exchange": str(row.get("symbol_on_exchange") or ""),
                    "provider_symbol": str(row.get("symbol") or ""),
                }
            )
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
        supported: list[str] = []
        unmapped: list[str] = []
        for symbol in sorted(set(universe_symbols)):
            if symbol.strip().upper() in markets_by_native:
                supported.append(symbol)
            else:
                unmapped.append(symbol)
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
            "anchor_symbols": list(anchor_symbols),
            "anchor_identity": anchor_identity,
            "requested_symbols": list(mapped),
            "matched_markets": sorted(matched_symbols),
            "binance_perpetual_market_count": len(markets_by_native),
            "matched_anchor_market_count": len(matched_markets),
            "native_identity_source": "future-markets.symbol_on_exchange",
            "native_identity_validated_markets": len(markets_by_native),
            "universe_support": {
                "universe_size": len(set(universe_symbols)),
                "supported_symbols": supported,
                "unmapped_symbols": unmapped,
                "supported_count": len(supported),
                "unmapped_count": len(unmapped),
                "note": (
                    "anchor qualification proves the source contract, not coverage of "
                    "every confirmed perpetual"
                ),
            },
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
        # The sidecar has proved the expected digest. Rehash any content-addressed
        # destination *before* fetching: a valid dest is no-transfer reuse, and a
        # fetch is a transfer even when the payload digest matches earlier bytes.
        dest_path = content_addressed_path(sample_dir, provider_checksum)
        if dest_path.is_file():
            existing = compute_sha256(dest_path)
            if existing != provider_checksum or dest_path.name != existing:
                raise ResumeIntegrityError(
                    "existing content-addressed object does not match the provider checksum",
                    context={
                        "key": key,
                        "path": str(dest_path),
                        "expected": provider_checksum,
                        "actual": existing,
                    },
                )
            payload = dest_path.read_bytes()
            sha256 = provider_checksum
            reused = True
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


def _state_reason(
    *,
    product: str,
    source_state: str,
    coverage_state: str,
    uncovered: Sequence[str],
    uncovered_universe: Sequence[str],
    typed_kinds: Sequence[str],
    budget_blocked: bool,
    unresolved_membership: Sequence[str],
    universe_basis: str,
    limit: int = 25,
) -> str:
    """State-first reason: what the source is, then what the coverage still lacks."""
    heads = {
        SOURCE_STATE_OFFICIAL: "official Vision archive listing, checksums, and retained samples",
        SOURCE_STATE_TYPED_GAPS: (
            "official source qualified; remaining differences are typed coverage facts"
        ),
        SOURCE_STATE_INACCESSIBLE: (
            "official Vision listing is empty or a declared family is absent"
        ),
        SOURCE_STATE_INTEGRITY: (
            "source integrity is unproved: missing checksum, unknown size, or listing/sample error"
        ),
        SOURCE_STATE_MEMBERSHIP: HISTORICAL_PERPETUAL_RULE,
        SOURCE_STATE_SAMPLE_PENDING: (
            "official listing is complete and reachable; no verified sample evidence yet"
        ),
    }
    parts = [heads.get(source_state, source_state)]
    if product == "binance_usdm_cost_calibration":
        parts.append(
            "cost calibration is the frozen first/midpoint/last daily bookTicker and "
            "bookDepth sample, not a full historical book archive"
        )
    if product == "binance_usdm_trade_flow_1h":
        parts.append(
            "hourly taker flow is derived from native 1h kline total and taker-buy "
            "volume fields; trades and aggTrades are not required"
        )
    if coverage_state == COVERAGE_UNRESOLVED_MEMBERSHIP:
        parts.append(
            f"membership unresolved for {_symbol_note(list(unresolved_membership), limit)}; "
            f"coverage evaluated over {universe_basis}"
        )
    notes = _coverage_gap_notes(uncovered, uncovered_universe)
    if notes:
        parts.append(notes)
    if typed_kinds:
        parts.append("typed coverage facts: " + ",".join(sorted(set(typed_kinds))))
    if budget_blocked:
        parts.append(
            f"{SAMPLE_BUDGET_BLOCK}: bounded cumulative Gate 1 sample budget cannot cover "
            "required regime evidence; inventory is complete"
        )
    return "; ".join(part for part in parts if part)


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
    budget_ledger: BudgetLedger | None = None,
    candidate_plan_only: bool = False,
) -> QualificationReport:
    refuse_restricted_scope(
        max_symbols=max_symbols,
        current_listing_only=current_listing_only,
        symbol_allowlist=symbol_allowlist,
    )
    generated_at = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    store = Path(store_root)
    sample_dir = store / "raw" / "sha256"
    list_cache_dir = store / "list_cache"
    progress_file = progress_path or (store / "cex002_qualification_progress.json")
    plan_path = store / "cex002_sample_plan.json"
    plan_lock_path = store / SAMPLE_PLAN_LOCK_FILENAME
    budget_ledger_path = store / BUDGET_LEDGER_FILENAME
    contract_metadata_path = store / CONTRACT_METADATA_FILENAME
    contract_snapshot_dir = store / CONTRACT_SNAPSHOT_DIRNAME
    amendment_ledger_path = store / AMENDMENT_LEDGER_FILENAME
    holdout_path = store / HOLDOUT_BOUNDARY_FILENAME
    retry_journal_path = store / "cex002_retry_journal.json"

    # A candidate request proves its exact prior authority before anything else exists:
    # no directory is created and no cache, checkpoint, journal, inventory, holdout,
    # listing, current-contract, or Coinalyze facility is loaded or used until it passes.
    candidate_authority: CandidateAuthority | None = None
    if candidate_plan_only:
        candidate_authority = candidate_preflight(
            plan_lock_path=plan_lock_path,
            budget_ledger_path=budget_ledger_path,
            budget_bytes=sample_budget_bytes,
        )

    sample_dir.mkdir(parents=True, exist_ok=True)
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
    current_rows: dict[str, dict[str, Any]] = {}
    exchange_response: ExchangeInfoResponse | None = None
    staged_observation: StagedContractObservation | None = None
    metadata_store = OfficialContractMetadataStore.load(
        contract_metadata_path, snapshot_dir=contract_snapshot_dir
    )
    if current_contracts is not None:
        exchange_response = retry_runner.run(
            "fapi:exchangeInfo", current_contracts.fetch_exchange_info
        )
        # Classification reads only the proved raw bytes of the live response. The
        # durable store is not mutated until the locked plan accepts this authority.
        proved_payload = validate_exchange_info_response(exchange_response)
        current_rows = parse_exchange_info_rows(proved_payload)
        for row in current_rows.values():
            row["response_sha256"] = exchange_response.sha256
            row["response_byte_size"] = int(exchange_response.byte_size)
            row["observed_at"] = generated_at
        current = tuple(
            sorted(name for name, row in current_rows.items() if is_confirmed_perpetual_row(row))
        )
        if not current:
            raise SourceQualificationError("exchangeInfo contains no PERPETUAL contracts")
        current_authenticated = True
        staged_observation = metadata_store.stage(
            exchange_response, current_rows, observed_at=generated_at
        )
        current_rows = staged_observation.enriched_rows
    current_set = set(current)

    # 1b. Accepted membership is evidence-based; archive names never promote themselves.
    historical_rows = metadata_store.historical_rows()
    lifecycle_rows: dict[str, dict[str, Any]] = {**historical_rows, **current_rows}
    funding_evidence = funding_membership_evidence(inventory)
    classifications = classify_membership(
        discovered=discovered,
        current_rows=current_rows,
        historical_rows=historical_rows,
        funding_evidence=funding_evidence,
        current_response_sha256=(
            exchange_response.sha256 if exchange_response is not None else ""
        ),
    )
    by_class: dict[str, list[str]] = {}
    for item in classifications:
        by_class.setdefault(item.membership_class, []).append(item.symbol)
    confirmed_universe = tuple(sorted(by_class.get(MEMBERSHIP_CONFIRMED, ())))
    unresolved_symbols = tuple(
        sorted(item.symbol for item in classifications if item.blocking)
    )
    membership_resolved = bool(confirmed_universe) and not unresolved_symbols
    # Coverage is still reported when membership is unresolved, but over the archive
    # union it was observed on, explicitly labelled as an unaccepted basis.
    evaluation_universe = confirmed_universe if confirmed_universe else tuple(discovered)
    universe_basis = (
        "confirmed_perpetual_membership"
        if confirmed_universe
        else "unresolved_archive_union"
    )
    # Archive names outside the authenticated current perpetual set stay candidates; the
    # sampling set follows the evaluated universe instead.
    archive_candidates = tuple(
        sym for sym in discovered if current_set and sym not in current_set
    )
    delisted = tuple(
        sym for sym in evaluation_universe if current_set and sym not in current_set
    )
    unarchived = tuple(sym for sym in current if sym not in set(discovered))

    sample_symbols = _sample_symbol_set(evaluation_universe, delisted)
    sample_symbol_set = set(sample_symbols)
    holdout_boundary = HoldoutBoundary.load_or_pin(holdout_path, now_iso=generated_at)
    cost_sample = select_cost_calibration_sample(
        inventory=inventory, universe=evaluation_universe
    )
    sampling_family_products = {
        family: tuple(
            product
            for product in products
            if product not in DERIVED_PRODUCTS and product != "binance_usdm_cost_calibration"
        )
        for family, products in family_products.items()
    }
    sampling_family_products = {
        family: products for family, products in sampling_family_products.items() if products
    }
    required_cost_objects = tuple(
        (
            str(item["family"]),
            str(item["symbol"]),
            item["object"],
            ("binance_usdm_cost_calibration",),
        )
        for item in cost_sample["items"]
    )

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
        if not sampling_family_products.get(family):
            continue
        for symbol in entry.symbols:
            if symbol not in sample_symbol_set:
                continue
            candidate_keys.extend(obj.key for obj in entry.objects.get(symbol, ()))
    candidate_keys.extend(str(item["key"]) for item in cost_sample["items"])
    recover_retained_samples(
        sample_dir=sample_dir,
        sidecar_dir=list_cache_dir,
        checksums=checksums,
        checkpoint=checkpoint,
        keys=candidate_keys,
    )
    # Reuse is planned only from re-proved bytes: a checkpoint claim whose object or
    # sidecar cannot be re-proved right now never becomes an authoritative plan input.
    retained_keys: dict[str, int] = {}
    unverified_retained_keys: list[str] = []
    # One re-proof per object per run: the same rehash serves planning, the frozen
    # snapshot, and the Gate 2 storage credit.
    verified_cache: dict[tuple[str, str], int | None] = {}
    for key in candidate_keys:
        entry_row = checkpoint.get(key)
        if not entry_row or entry_row.get("status") != "complete":
            continue
        verified = verify_retained_object(
            key,
            entry_row,
            sample_dir=sample_dir,
            sidecar_dir=list_cache_dir,
            cache=verified_cache,
        )
        if verified is None:
            unverified_retained_keys.append(key)
            continue
        retained_keys[key] = verified

    # The selected manifest is qualified against re-proved retained evidence, so it is
    # built only once that evidence exists.
    proved_objects = {
        key: dict(checkpoint.get(key) or {}) for key in sorted(retained_keys)
    }
    acquisition_manifest = build_acquisition_manifest(
        inventory=inventory,
        universe=evaluation_universe,
        proved_objects=proved_objects,
    )
    selected_storage = selected_storage_report(
        inventory=inventory, manifest=acquisition_manifest, cost_sample=cost_sample
    )
    # Re-proved 1h kline schema evidence, usable when no sample is acquired at all.
    retained_kline_schema: dict[str, Any] = {}
    for key in sorted(retained_keys):
        if family_group_from_key(key) != "klines":
            continue
        row = checkpoint.get(key) or {}
        fields = tuple(str(item) for item in (row.get("schema_fields") or ()))
        if not fields:
            continue
        retained_kline_schema = {
            "key": key,
            "fields": fields,
            "schema_kind": str(row.get("schema_kind") or ""),
            "source": "reproved_retained_checkpoint",
        }
        break

    # 3. Lock one immutable plan before any new download. A resume replays the locked
    #    plan and may change only execution state, never selected or blocked keys.
    #    Ledger bootstrap, reconciliation, and settlement belong exclusively to the
    #    executing branch below: a candidate phase must never write the legacy ledger.

    def _plan_inputs(snapshot: Mapping[str, Sequence[Any]]) -> PlanInputs:
        return PlanInputs(
            inventory_digest=inventory_digest(inventory),
            listing_digest=listing_authority_digest(listing_checkpoint),
            membership_digest=membership_evidence_digest(classifications),
            code_config_digest=plan_code_config_digest(
                budget_bytes=sample_budget_bytes, max_object_bytes=max_sample_object_bytes
            ),
            budget_digest=_digest_of(
                {
                    "budget_bytes": int(sample_budget_bytes),
                    "independent_object_cap_bytes": None,
                }
            ),
            retained_digest=retained_evidence_digest(snapshot),
        )

    def _candidate_inputs(snapshot: Mapping[str, Sequence[Any]]) -> PlanInputs:
        return PlanInputs(
            inventory_digest=inventory_digest(inventory),
            listing_digest=listing_authority_digest(listing_checkpoint),
            membership_digest=membership_evidence_digest(classifications),
            code_config_digest=plan_code_config_digest(
                budget_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
                max_object_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
            ),
            budget_digest=_digest_of(
                {
                    "ledger_id": AMENDMENT_LEDGER_ID,
                    "budget_bytes": GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
                    "independent_object_cap_bytes": None,
                }
            ),
            retained_digest=retained_evidence_digest(snapshot),
        )

    candidate_plan_record: dict[str, Any] = {
        "state": "not_constructed",
        "plan_version": CANDIDATE_PLAN_VERSION,
        "migration_authorized": False,
        "download_authorized": False,
        "note": (
            "a version-3 candidate is constructed only in candidate-plan-only mode, from "
            "read-only prior authority; the executing plan is never relabelled as one"
        ),
    }
    amendment_allowance: AmendmentAllowance | None = None

    if candidate_plan_only:
        # The preflight already hashed, loaded, and validated this authority before any
        # store or remote facility existed; those exact objects are reused here.
        assert candidate_authority is not None
        lock = candidate_authority.lock
        legacy_ledger = candidate_authority.ledger
        prior_lock_sha256 = candidate_authority.lock_sha256
        prior_ledger_sha256 = candidate_authority.ledger_sha256
        retained_snapshot = retained_evidence_snapshot(
            sorted(retained_keys),
            checkpoint.objects,
            sample_dir=sample_dir,
            sidecar_dir=list_cache_dir,
            cache=verified_cache,
        )
        plan_inputs = _candidate_inputs(retained_snapshot)
        # An independent candidate: its own allowance, no legacy spend subtraction, and
        # no per-object cap.
        plan = build_sample_plan(
            inventory=inventory,
            family_products=sampling_family_products,
            sample_symbols=sample_symbols,
            delisted=delisted,
            retained_keys=retained_keys,
            budget_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
            max_object_bytes=GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
            cumulative_spent_bytes=0,
            required_objects=required_cost_objects,
        )
        amendment_allowance = build_amendment_allowance(
            path=amendment_ledger_path,
            legacy_ledger=legacy_ledger,
            legacy_ledger_path=budget_ledger_path,
            legacy_ledger_sha256=prior_ledger_sha256,
            retained_keys=retained_keys,
            planned_new_bytes=plan.new_download_bytes,
        )
        candidate_plan_record = build_candidate_plan_v3(
            lock=lock,
            prior_lock_sha256=prior_lock_sha256,
            plan=plan,
            inputs=plan_inputs,
            allowance=amendment_allowance,
            prior_plan_digests=candidate_authority.prior_plan_digests,
        )
        # Prove the prior authority bytes did not move while the candidate was built.
        after_lock = file_sha256(plan_lock_path)
        after_ledger = file_sha256(budget_ledger_path)
        if after_lock != prior_lock_sha256 or after_ledger != prior_ledger_sha256:
            raise ResumeIntegrityError(
                "prior plan or budget authority changed during candidate construction",
                context={
                    "lock_before": prior_lock_sha256,
                    "lock_after": after_lock,
                    "ledger_before": prior_ledger_sha256,
                    "ledger_after": after_ledger,
                },
            )
        ledger = legacy_ledger
        reconciliation = {
            "settled": 0,
            "unresolved": 0,
            "reproved": 0,
            "unreconciled": 0,
            "state": "not_reconciled_in_candidate_phase",
        }
    else:
        ledger = budget_ledger or BudgetLedger.bootstrap(
            budget_ledger_path,
            budget_bytes=sample_budget_bytes,
            retained_objects=checkpoint.objects,
            sample_dir=sample_dir,
            sidecar_dir=list_cache_dir,
            cache=verified_cache,
        )
        # A reservation left by an interrupted run is settled only against rehashed
        # retained evidence; anything unproved stays charged.
        reconciliation = ledger.reconcile(
            checkpoint.objects, sample_dir=sample_dir, sidecar_dir=list_cache_dir
        )
        lock = SamplePlanLock.load(plan_lock_path)
        if lock is None:
            lock = SamplePlanLock(path=plan_lock_path)
            # The retained and budget snapshots are frozen at lock time; later execution
            # progress against this same plan is not an input change.
            retained_snapshot = retained_evidence_snapshot(
                sorted(retained_keys),
                checkpoint.objects,
                sample_dir=sample_dir,
                sidecar_dir=list_cache_dir,
                cache=verified_cache,
            )
            plan_inputs = _plan_inputs(retained_snapshot)
            plan = build_sample_plan(
                inventory=inventory,
                family_products=sampling_family_products,
                sample_symbols=sample_symbols,
                delisted=delisted,
                retained_keys=retained_keys,
                budget_bytes=sample_budget_bytes,
                max_object_bytes=max_sample_object_bytes,
                cumulative_spent_bytes=ledger.spent_max_bytes,
                required_objects=required_cost_objects,
            )
            # A pre-lock greedy plan is evidence of what earlier runs selected and spent. It
            # is preserved in the lock history and on disk before the first lock overwrites
            # the plan document.
            legacy_plan = read_pre_lock_plan(plan_path)
            if legacy_plan is not None:
                lock.history.append(
                    {
                        "plan_version": 0,
                        "locked_at": "",
                        "inputs": {"source": "pre_lock_greedy_plan", "path": str(plan_path)},
                        "plan": legacy_plan,
                        "plan_digest": "",
                    }
                )
                backup = store / LEGACY_PLAN_BACKUP_FILENAME
                if not backup.exists():
                    _atomic_write_json(backup, legacy_plan)
            lock.lock_plan(
                plan=plan,
                inputs=plan_inputs,
                locked_at=generated_at,
                retained_snapshot=retained_snapshot,
                budget_snapshot={
                    "budget_bytes": int(sample_budget_bytes),
                    "independent_object_cap_bytes": None,
                    "cumulative_spent_max_bytes_at_lock": ledger.spent_max_bytes,
                    "allowance_bytes_at_lock": plan.allowance_bytes,
                },
            )
            lock.flush()
        else:
            plan = SamplePlan.from_dict(lock.plan)
            # Only the evidence frozen into this lock is compared, so a normal resume is
            # stable; a genuine inventory, membership, code, or evidence change fails closed
            # before any byte is downloaded.
            retained_snapshot = retained_evidence_snapshot(
                sorted(lock.retained_snapshot),
                checkpoint.objects,
                sample_dir=sample_dir,
                sidecar_dir=list_cache_dir,
                cache=verified_cache,
            )
            plan_inputs = _plan_inputs(retained_snapshot)
            changed_inputs = plan_inputs.differences(lock.inputs)
            if changed_inputs:
                raise ResumeIntegrityError(
                    "locked Gate 1 plan inputs changed; a new plan version requires a fresh "
                    "reviewer authorization",
                    context={
                        "kind": PLAN_INPUTS_CHANGED,
                        "path": str(plan_lock_path),
                        "plan_version": lock.plan_version,
                        "changed": list(changed_inputs),
                    },
                )
    if staged_observation is not None and not candidate_plan_only:
        # Commit only after the existing plan accepts, or as part of first-plan lock.
        metadata_store.commit(staged_observation, updated_at=generated_at)
    if not candidate_plan_only:
        ledger.flush()
        _atomic_write_json(plan_path, plan.to_dict())

    # 4. Acquire only planned samples. Each physical object is fetched at most once and
    #    attributed to every logical product that declares its family.
    # The executing plan is always the durable locked plan. A candidate never becomes
    # the executing plan, and a candidate phase executes nothing at all.
    execution_plan = SamplePlan.from_dict(lock.plan) if candidate_plan_only else plan
    samples: list[SampleRecord] = []
    acquired: dict[str, SampleRecord] = {}
    for planned in (() if candidate_plan_only else plan.entries):
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
        planned_new = (
            planned.action == "download"
            and planned.key not in retained_keys
            and (checkpoint.get(planned.key) or {}).get("status") != "complete"
        )
        if planned_new and (
            planned.byte_size > ledger.remaining_bytes or ledger.exhausted
        ):
            for product in planned.products:
                incidents.append(
                    {
                        "product": product,
                        "family": planned.family,
                        "symbol": planned.symbol,
                        "regime": planned.regime,
                        "kind": SAMPLE_BUDGET_BLOCK,
                        "note": (
                            "cumulative Gate 1 new-download allowance is exhausted; "
                            f"remaining={ledger.remaining_bytes} required={planned.byte_size}"
                        ),
                    }
                )
                product_incident_counts[product] = product_incident_counts.get(product, 0) + 1
            continue
        if planned_new:
            # Write-ahead: the charge is durable before any byte crosses the network.
            ledger.reserve(planned.key, planned.byte_size)
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
            # The acquisition failed after the reservation; the bytes may still have been
            # transferred, so the reservation stays charged.
            continue
        if planned_new:
            # A content-addressed reuse transfers nothing; it settles with an explicit
            # no-transfer disposition rather than an indistinguishable zero charge.
            ledger.settle(
                record.key,
                record.byte_size,
                sha256=record.sha256,
                no_transfer=record.reused_existing,
            )
        acquired[planned.key] = record
        samples.append(record)

    for item in (() if candidate_plan_only else plan.blocked):
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

    # 4b. The report-facing manifest is rebuilt from proof established in THIS
    #     invocation: retained objects re-proved at startup plus objects whose content and
    #     provider checksum were validated during execution. A checkpoint completion claim
    #     is never promoted on its own. The locked plan, its digest, the selected and
    #     blocked keys, the download set, the execution order, and both ledgers are
    #     untouched; only what the final report may honestly call proved changes.
    final_proved: dict[str, dict[str, Any]] = dict(proved_objects)
    for record in samples:
        if not record.checksum_match or record.provider_checksum != record.sha256:
            continue
        proved_row = dict(checkpoint.get(record.key) or {})
        proved_row.setdefault("sha256", record.sha256)
        proved_row.setdefault("provider_checksum", record.provider_checksum)
        final_proved[record.key] = proved_row
    if final_proved != proved_objects:
        acquisition_manifest = build_acquisition_manifest(
            inventory=inventory,
            universe=evaluation_universe,
            proved_objects=final_proved,
        )
        selected_storage = selected_storage_report(
            inventory=inventory, manifest=acquisition_manifest, cost_sample=cost_sample
        )

    # 5. Derive every logical product row from the shared inventory. Source authority
    #    and universe/temporal coverage are judged separately.
    matrix_rows: list[ProductMatrixRow] = []
    taker_flow_evidence: dict[str, Any] = {
        "product": "binance_usdm_trade_flow_1h",
        "derived_from": "binance_usdm_bar_1h",
        "required_fields": list(KLINE_TAKER_FLOW_FIELDS),
        "supported": False,
        "evidence_key": "",
        "requires_trades_or_aggtrades": False,
    }
    symbol_coverage: dict[str, dict[str, int]] = {}
    symbol_temporal: dict[str, dict[str, dict[str, Any]]] = {}
    family_symbol_periods: dict[tuple[str, str], tuple[str, ...]] = {}
    for family, entry in inventory.items():
        for symbol, objects in entry.objects.items():
            periods = tuple(
                sorted({item for item in (object_period(obj.key) for obj in objects) if item})
            )
            if periods:
                family_symbol_periods[(family, symbol)] = periods
    integrity_kinds = {"listing_error", "sample_error", "coinalyze_error"}
    universe_set = set(evaluation_universe)
    lifecycle_windows = contract_lifecycle_windows(lifecycle_rows)

    for product in REQUIRED_PRODUCTS:
        families = OFFICIAL_ARCHIVE_FAMILIES.get(product, ())
        family_symbols: set[str] = set()
        listed_objects = 0
        listed_bytes = 0
        universe_objects = 0
        universe_bytes = 0
        unknown_sizes = False
        universe_unknown_sizes = False
        product_incidents = product_incident_counts.get(product, 0)
        product_integrity = sum(
            1
            for item in incidents
            if item.get("product") == product and item.get("kind") in integrity_kinds
        )
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
                in_universe = symbol in universe_set
                if in_universe:
                    universe_objects += len(objs)
                for obj in objs:
                    if obj.size is None:
                        unknown_sizes = True
                        if in_universe:
                            universe_unknown_sizes = True
                    else:
                        listed_bytes += int(obj.size)
                        if in_universe:
                            universe_bytes += int(obj.size)

        is_membership = product == "binance_usdm_perpetual_membership"
        if is_membership:
            family_symbols = set(evaluation_universe)
            listed_objects = len(evaluation_universe)
            universe_objects = len(evaluation_universe)

        # Account the full evaluated universe, not only symbols already listed under a
        # family: a member with no prefix is a recorded zero, not an omission.
        for family in families:
            if family not in family_symbol_lists:
                continue
            for symbol in evaluation_universe:
                family_symbol_objects.setdefault((family, symbol), 0)

        uncovered = tuple(
            symbol
            for symbol in _uncovered_listed_symbols(family_symbol_lists, family_symbol_objects)
            if symbol in universe_set
        )
        universe_gaps, blocking_symbols, typed_symbols = universe_coverage_gaps(
            universe=evaluation_universe,
            families=families,
            family_symbol_lists=family_symbol_lists,
            family_symbol_objects=family_symbol_objects,
            family_symbol_periods=family_symbol_periods,
            currently_listed=current,
            lifecycle_windows=lifecycle_windows,
            require_every_group=not is_membership,
        )
        symbol_coverage[product] = {
            f"{family}/{symbol}": count
            for (family, symbol), count in sorted(family_symbol_objects.items())
        }
        # Per-symbol temporal coverage is retained for every evaluated member, so a gap is
        # always readable against the symbol's own observed first and last month.
        temporal: dict[str, dict[str, Any]] = {}
        for symbol in evaluation_universe:
            observed_periods = sorted(
                {
                    period
                    for family in families
                    for period in family_symbol_periods.get((family, symbol), ())
                }
            )
            if observed_periods:
                temporal[symbol] = {
                    "first": observed_periods[0],
                    "last": observed_periods[-1],
                    "months": len(observed_periods),
                }
        symbol_temporal[product] = temporal
        product_sample_rows = [item for item in samples if product in item.products]
        product_samples = len(product_sample_rows)
        budget_blocked = tuple(
            dict(item)
            for item in execution_plan.blocked
            if product in tuple(item.get("products", ()))
        )
        checksum_ok = bool(product_sample_rows) and all(
            item.checksum_match and item.provider_checksum for item in product_sample_rows
        )
        source_gate = product not in DERIVED_PRODUCTS
        blocking_kinds = tuple(
            sorted({str(item["kind"]) for item in universe_gaps if item.get("blocking")})
        )
        typed_kinds = tuple(
            sorted({str(item["kind"]) for item in universe_gaps if not item.get("blocking")})
        )
        gap_kinds = tuple(sorted(set(blocking_kinds) | set(typed_kinds)))
        evidence_blocked = bool(budget_blocked) or (bool(families) and product_samples == 0)

        release_blocked_override: bool | None = None
        if product == "binance_usdm_trade_flow_1h":
            # Hourly taker flow is derived from the native 1h kline schema and its
            # interval coverage. It never requires trades or aggTrades.
            bar_row = next(
                (row for row in matrix_rows if row.product == "binance_usdm_bar_1h"), None
            )
            kline_sample = next(
                (item for item in samples if _family_group(item.family) == "klines"), None
            )
            if kline_sample is not None:
                fields = tuple(kline_sample.schema_fields)
                schema_kind = kline_sample.schema_kind
                evidence_key = kline_sample.key
                evidence_source = "acquired_sample"
            else:
                # A candidate phase acquires nothing, so the only honest evidence is the
                # re-proved retained checkpoint schema. Absent that, it stays pending.
                fields = tuple(retained_kline_schema.get("fields") or ())
                schema_kind = str(retained_kline_schema.get("schema_kind") or "")
                evidence_key = str(retained_kline_schema.get("key") or "")
                evidence_source = str(retained_kline_schema.get("source") or "")
            supported = bool(fields) and kline_schema_supports_taker_flow(fields)
            missing_fields = tuple(
                name for name in KLINE_TAKER_FLOW_FIELDS if name not in set(fields)
            )
            if bar_row is None:
                source_state = SOURCE_STATE_DERIVED
                coverage_state = COVERAGE_NOT_APPLICABLE
                release_blocked_override = True
            elif not fields:
                source_state = SOURCE_STATE_SAMPLE_PENDING
                coverage_state = bar_row.coverage_state
                release_blocked_override = True
            elif not supported:
                source_state = SOURCE_STATE_INTEGRITY
                coverage_state = bar_row.coverage_state
                release_blocked_override = True
            else:
                source_state = bar_row.source_qualification_state
                coverage_state = bar_row.coverage_state
                release_blocked_override = bar_row.release_blocked
                if (
                    source_state == SOURCE_STATE_SAMPLE_PENDING
                    and evidence_source == "reproved_retained_checkpoint"
                ):
                    # The bar row is sample-pending only because this invocation acquired
                    # nothing. Re-proved retained schema already establishes the taker-flow
                    # fields, so only that artificial condition is removed here; real
                    # integrity, access, membership, and coverage states are untouched.
                    source_state = (
                        SOURCE_STATE_TYPED_GAPS
                        if coverage_state == COVERAGE_TYPED_GAPS
                        else SOURCE_STATE_OFFICIAL
                    )
                    # The inherited release block was the same artificial condition, so it
                    # is lifted only for complete or nonblocking typed-gap coverage with no
                    # sample-budget block. Blocking coverage, unresolved membership, and a
                    # real budget block all stay blocking.
                    if (
                        coverage_state in {COVERAGE_COMPLETE, COVERAGE_TYPED_GAPS}
                        and not bar_row.sample_budget_blocked
                    ):
                        release_blocked_override = False
            reason = (
                "derived from the qualified native 1h kline schema and its interval "
                "coverage; trades and aggTrades are never required"
            )
            if missing_fields:
                reason = f"{reason}; missing taker-flow fields: {','.join(missing_fields)}"
            taker_flow_evidence = {
                "product": product,
                "derived_from": "binance_usdm_bar_1h",
                "required_fields": list(KLINE_TAKER_FLOW_FIELDS),
                "observed_schema_fields": list(fields),
                "schema_kind": schema_kind,
                "evidence_key": evidence_key,
                "evidence_source": evidence_source,
                "supported": bool(supported),
                "missing_fields": list(missing_fields),
                "source_qualification_state": source_state,
                "coverage_state": coverage_state,
                "release_blocked": bool(release_blocked_override),
                "requires_trades_or_aggtrades": False,
            }
        elif product in DERIVED_PRODUCTS:
            source_state = SOURCE_STATE_DERIVED
            coverage_state = COVERAGE_NOT_APPLICABLE
            reason = "derived output; excluded from the source gate"
        elif product == "binance_usdm_liquidation_observed_daily":
            source_state = SOURCE_STATE_INACCESSIBLE
            coverage_state = COVERAGE_BLOCKING_GAPS
            reason = (
                "official Vision has no liquidation archive; Coinalyze daily history is "
                "required as an observed/censored secondary source"
            )
        else:
            if not membership_resolved:
                coverage_state = COVERAGE_UNRESOLVED_MEMBERSHIP
            elif blocking_kinds or uncovered:
                coverage_state = COVERAGE_BLOCKING_GAPS
            elif typed_kinds:
                coverage_state = COVERAGE_TYPED_GAPS
            else:
                coverage_state = COVERAGE_COMPLETE

            if is_membership and not membership_resolved:
                source_state = SOURCE_STATE_MEMBERSHIP
            elif is_membership:
                source_state = (
                    SOURCE_STATE_TYPED_GAPS
                    if coverage_state == COVERAGE_TYPED_GAPS
                    else SOURCE_STATE_OFFICIAL
                )
            elif listed_objects == 0 or not _declared_families_present(families, family_listed):
                source_state = SOURCE_STATE_INACCESSIBLE
            elif unknown_sizes or product_integrity or (product_sample_rows and not checksum_ok):
                source_state = SOURCE_STATE_INTEGRITY
            elif not product_sample_rows:
                source_state = SOURCE_STATE_SAMPLE_PENDING
            elif typed_kinds and not blocking_kinds:
                source_state = SOURCE_STATE_TYPED_GAPS
            else:
                source_state = SOURCE_STATE_OFFICIAL

            reason = _state_reason(
                product=product,
                source_state=source_state,
                coverage_state=coverage_state,
                uncovered=uncovered,
                uncovered_universe=blocking_symbols,
                typed_kinds=typed_kinds,
                budget_blocked=bool(budget_blocked),
                unresolved_membership=unresolved_symbols,
                universe_basis=universe_basis,
            )

        authority = SOURCE_STATE_AUTHORITY[source_state]
        release_blocked = bool(
            source_state not in QUALIFIED_SOURCE_STATES
            or coverage_state in {COVERAGE_BLOCKING_GAPS, COVERAGE_UNRESOLVED_MEMBERSHIP}
            or evidence_blocked
        )
        complete = source_gate and not release_blocked

        matrix_rows.append(
            ProductMatrixRow(
                product=product,
                authority=authority.value,
                official_complete=complete,
                source_gate=source_gate,
                sample_only=authority is SourceAuthority.SAMPLE_ONLY,
                reason=reason,
                official_families=families,
                discovered_symbols=len(family_symbols)
                if family_symbols
                else len(evaluation_universe),
                sample_count=product_samples,
                listed_object_count=listed_objects,
                listed_bytes=None if unknown_sizes else listed_bytes,
                incidents=product_incidents,
                release_blocked_derived=(
                    bool(release_blocked_override)
                    if release_blocked_override is not None
                    else None
                ),
                uncovered_listed_symbols=uncovered if source_gate else (),
                uncovered_universe_symbols=blocking_symbols if source_gate else (),
                universe_coverage_gaps=universe_gaps if source_gate else (),
                sample_budget_blocked=budget_blocked if source_gate else (),
                accepted_universe_object_count=universe_objects,
                accepted_universe_listed_bytes=None if universe_unknown_sizes else universe_bytes,
                source_qualification_state=source_state,
                coverage_state=coverage_state,
                release_blocked=release_blocked if source_gate else False,
                typed_gap_symbols=typed_symbols if source_gate else (),
                coverage_gap_kinds=gap_kinds if source_gate else (),
            )
        )

    # 6. Coinalyze qualifies on declared stable anchors, never on an alphabetical edge.
    anchors = tuple(COINALYZE_ANCHOR_SYMBOLS)
    confirmed_set = set(confirmed_universe)
    unconfirmed_anchors = tuple(symbol for symbol in anchors if symbol not in confirmed_set)
    coinalyze_block: dict[str, Any] = {
        "qualified": False,
        "key_present": bool(coinalyze_api_key),
        "anchor_symbols": list(anchors),
        "reason": "Coinalyze transport or COINALYZE_API_KEY absent",
    }
    if coinalyze_transport is not None and coinalyze_api_key and unconfirmed_anchors:
        reason = (
            "declared Coinalyze anchors are not confirmed Binance perpetuals: "
            + ",".join(unconfirmed_anchors)
        )
        incidents.append(
            {
                "product": "binance_usdm_liquidation_observed_daily",
                "kind": "coinalyze_anchor_unconfirmed",
                "note": reason,
            }
        )
        coinalyze_block = {
            "qualified": False,
            "key_present": True,
            "anchor_symbols": list(anchors),
            "unconfirmed_anchors": list(unconfirmed_anchors),
            "reason": reason,
        }
    elif coinalyze_transport is not None and coinalyze_api_key:
        try:
            client = CoinalyzeClient(
                coinalyze_transport, api_key=coinalyze_api_key, retry=retry_runner
            )
            coinalyze_block = client.qualify_binance_daily(
                anchor_symbols=anchors,
                universe_symbols=confirmed_universe,
                from_ts=coinalyze_from_ts,
                to_ts=coinalyze_to_ts,
            )
            coinalyze_block["qualified"] = True
        except SourceQualificationError as exc:
            incidents.append(
                {
                    "product": "binance_usdm_liquidation_observed_daily",
                    "kind": "coinalyze_error",
                    "note": str(exc),
                }
            )
            coinalyze_block = {
                "qualified": False,
                "key_present": True,
                "anchor_symbols": list(anchors),
                "reason": str(exc),
            }

    if coinalyze_block.get("qualified"):
        support = coinalyze_block.get("universe_support") or {}
        unmapped = tuple(str(item) for item in support.get("unmapped_symbols", ()))
        liquidation_coverage = (
            COVERAGE_UNRESOLVED_MEMBERSHIP
            if not membership_resolved
            else (COVERAGE_TYPED_GAPS if unmapped else COVERAGE_COMPLETE)
        )
        liquidation_reason = (
            "Coinalyze daily Binance-perpetual liquidation/OI/funding/price history "
            f"qualified on declared anchors {','.join(anchors)} as observed/censored "
            f"secondary. {BINANCE_CENSORSHIP_NOTE}"
        )
        if unmapped:
            liquidation_reason = (
                f"{liquidation_reason}; anchor qualification is not full coverage: "
                f"{len(unmapped)} confirmed perpetuals are unmapped in Coinalyze"
            )
        rebuilt: list[ProductMatrixRow] = []
        for row in matrix_rows:
            if row.product != "binance_usdm_liquidation_observed_daily":
                rebuilt.append(row)
                continue
            rebuilt.append(
                ProductMatrixRow(
                    product=row.product,
                    authority=SourceAuthority.SECONDARY.value,
                    official_complete=True,
                    source_gate=True,
                    sample_only=False,
                    reason=liquidation_reason,
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
                    uncovered_universe_symbols=unmapped,
                    universe_coverage_gaps=tuple(
                        {
                            "symbol": symbol,
                            "family_group": "coinalyze_liquidation",
                            "families": [],
                            "status": "coinalyze_symbol_unmapped",
                            "kind": "coinalyze_symbol_unmapped",
                            "blocking": False,
                            "objects": 0,
                        }
                        # Every unmapped confirmed perpetual is retained; the product gap
                        # evidence is never truncated.
                        for symbol in unmapped
                    ),
                    sample_budget_blocked=row.sample_budget_blocked,
                    source_qualification_state=SOURCE_STATE_SECONDARY,
                    coverage_state=liquidation_coverage,
                    release_blocked=liquidation_coverage == COVERAGE_UNRESOLVED_MEMBERSHIP,
                    typed_gap_symbols=unmapped,
                    coverage_gap_kinds=("coinalyze_symbol_unmapped",) if unmapped else (),
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

    # 7. Exact selected-manifest requirement. Listing/unselected bytes stay audit-only.
    selected_keys = frozenset(acquisition_manifest["keys"]) | frozenset(cost_sample["keys"])
    requirement = PhysicalRequirement(
        object_count=len(selected_keys),
        byte_total=int(selected_storage["selected_plus_cost_compressed_raw_bytes"]),
        unknown_size_objects=int(acquisition_manifest["unknown_size_objects"])
        + int(cost_sample["unknown_size_objects"]),
        keys=selected_keys,
    )
    # Credit is only granted to bytes re-proved right now: rehashed raw object plus a
    # re-proved provider sidecar. An unverifiable row reduces nothing.
    credit_digests: set[str] = set()
    credit_bytes = 0
    unverified_credit = 0
    for key, entry_row in sorted(checkpoint.objects.items()):
        if key not in requirement.keys:
            continue
        size = verify_retained_object(
            key,
            entry_row,
            sample_dir=sample_dir,
            sidecar_dir=list_cache_dir,
            cache=verified_cache,
        )
        if size is None:
            unverified_credit += 1
            continue
        digest = str(entry_row.get("sha256") or "")
        if digest in credit_digests:
            continue
        credit_digests.add(digest)
        credit_bytes += size
    feasibility = storage_feasibility(
        requirement=requirement,
        retained_credit_bytes=credit_bytes,
        retained_credit_objects=len(credit_digests),
        local_available_bytes=available_bytes(store),
        unverified_credit_objects=unverified_credit,
        # This phase measures none of these, so Gate 2 stays unproved.
        normalized_catalog_bytes=None,
        temporary_high_water_bytes=None,
        operating_reserve_bytes=None,
    )
    if feasibility["gate2_storage_state"] == "insufficient":
        incidents.append(
            {
                "product": "binance_usdm_harmonic_bundle",
                "kind": GATE2_STORAGE_BLOCK,
                "note": GATE2_STORAGE_INCIDENT_NOTE,
            }
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
    checkpoint.flush(
        updated_at=generated_at,
        discovered_symbol_count=len(discovered),
    )
    return QualificationReport(
        ticket=TICKET_ID,
        gate="gate_1_source_procurement",
        gate_status=GateStatus.QUALIFIED.value if accepted else GateStatus.BLOCKED.value,
        generated_at=generated_at,
        universe_source=(
            "official_vision_union_listing_with_evidence_based_perpetual_membership"
        ),
        historical_perpetual_rule=HISTORICAL_PERPETUAL_RULE,
        discovered_symbols=tuple(discovered),
        current_perpetual_symbols=current,
        current_contracts_authenticated=current_authenticated,
        historical_or_delisted_candidates=archive_candidates,
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
            "full_archive_union_totals": {
                "scope": "every listed archive name, including excluded and unresolved",
                "object_count_exact": {
                    row.product: row.listed_object_count for row in matrix_rows
                },
                "byte_count_exact": {row.product: row.listed_bytes for row in matrix_rows},
            },
            "confirmed_universe_totals": {
                "scope": universe_basis,
                "object_count_exact": {
                    row.product: row.accepted_universe_object_count for row in matrix_rows
                },
                "byte_count_exact": {
                    row.product: row.accepted_universe_listed_bytes for row in matrix_rows
                },
            },
            # Retained for continuity; identical to full_archive_union_totals.
            "object_count_exact": {row.product: row.listed_object_count for row in matrix_rows},
            "byte_count_exact": {row.product: row.listed_bytes for row in matrix_rows},
            "physical_family_object_counts": dict(sorted(family_object_counts.items())),
            "physical_source_requirement": {
                "universe_basis": universe_basis,
                "universe_size": len(evaluation_universe),
                "scope": "selected_nonoverlapping_manifest_plus_cost_sample",
                "object_count": requirement.object_count,
                "compressed_raw_bytes": requirement.byte_total,
                "unknown_size_objects": requirement.unknown_size_objects,
                "deduplication": (
                    "each selected physical object counted once; unselected trades, "
                    "books, and overlapping cadence packages are audit-only"
                ),
            },
            "selected_storage": selected_storage,
            "cost_sample": {
                "object_count": cost_sample["object_count"],
                "compressed_raw_bytes": cost_sample["compressed_raw_bytes"],
                "keys": list(cost_sample["keys"]),
                "gaps": list(cost_sample["gaps"]),
                "selector": cost_sample["selector"],
                "families": list(cost_sample["families"]),
            },
            "acquisition_manifest": {
                "object_count": acquisition_manifest["object_count"],
                "compressed_raw_bytes": acquisition_manifest["compressed_raw_bytes"],
                "rows": [dict(row) for row in acquisition_manifest["rows"]],
                "collisions": list(acquisition_manifest["collisions"]),
                "rejections": list(acquisition_manifest["rejections"]),
                "raw_validation_pending_keys": list(
                    acquisition_manifest["raw_validation_pending_keys"]
                ),
                "consumable_object_count": acquisition_manifest["consumable_object_count"],
                "integrity_rule": acquisition_manifest["integrity_rule"],
                "cadence_rule": acquisition_manifest["cadence_rule"],
                "family_object_counts": dict(acquisition_manifest["family_object_counts"]),
            },
            "gate2_feasibility": {
                **feasibility,
                "selected_compressed_raw_bytes": selected_storage[
                    "selected_compressed_raw_bytes"
                ],
                "cost_sample_compressed_raw_bytes": selected_storage[
                    "cost_sample_compressed_raw_bytes"
                ],
                "largest_selected_compressed_object_bytes": selected_storage[
                    "largest_selected_compressed_object_bytes"
                ],
                "normalized_catalog_bytes": "unknown",
                "temporary_high_water_bytes": "unknown",
                "operating_reserve_bytes": "unknown",
                "total_sufficiency": "unknown",
            },
            "logical_product_totals_overlap": True,
            "taker_flow": taker_flow_evidence,
            "symbol_temporal_coverage": symbol_temporal,
            "symbol_coverage": symbol_coverage,
            "universe_coverage_gaps": {
                row.product: [dict(item) for item in row.universe_coverage_gaps]
                for row in matrix_rows
                if row.universe_coverage_gaps
            },
            "note": (
                "full-family listings remain audit facts; Gate 2 storage uses the selected "
                "non-overlapping manifest plus the declared cost sample"
            ),
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
            "unverified_retained_sample_keys": len(unverified_retained_keys),
            "physical_families_inventoried": len(inventory),
        },
        sample_plan=execution_plan.to_dict(),
        retry=retry_runner.to_dict(),
        listing_checkpoint=(
            listing_checkpoint.to_dict() if listing_checkpoint is not None else {}
        ),
        coinalyze=coinalyze_block,
        accepted=accepted,
        membership={
            "rule": HISTORICAL_PERPETUAL_RULE,
            "universe_basis": universe_basis,
            "resolved": membership_resolved,
            "confirmed_count": len(confirmed_universe),
            "unresolved_count": len(unresolved_symbols),
            "class_counts": {name: len(items) for name, items in sorted(by_class.items())},
            "classes": {name: sorted(items) for name, items in sorted(by_class.items())},
            "unresolved_symbols": list(unresolved_symbols),
            "evidence_sources": [
                "authenticated_current_exchange_info",
                "retained_official_contract_metadata",
                "official_realized_funding_observation",
            ],
            "retained_contract_metadata_rows": len(metadata_store.symbol_snapshot),
            "retained_contract_snapshots": len(metadata_store.snapshots),
            "classifications": [item.to_dict() for item in classifications],
        },
        accepted_universe=confirmed_universe,
        plan_lock=lock.summary(),
        budget={
            **ledger.to_dict(),
            "reconciliation": reconciliation,
            "legacy_budget_preserved": True,
            "legacy_ledger_path": str(budget_ledger_path),
            "architecture_amendment_allowance_bytes": GATE1_ARCHITECTURE_AMENDMENT_BUDGET_BYTES,
            "independent_object_cap_bytes": None,
            "architecture_amendment": (
                None if amendment_allowance is None else amendment_allowance.to_dict()
            ),
        },
        candidate_plan=candidate_plan_record,
        prospective_holdout=prospective_holdout_record(holdout_boundary),
        acquisition_manifest={
            "object_count": acquisition_manifest["object_count"],
            "compressed_raw_bytes": acquisition_manifest["compressed_raw_bytes"],
            "rows": [dict(row) for row in acquisition_manifest["rows"]],
            "collisions": list(acquisition_manifest["collisions"]),
            "rejections": list(acquisition_manifest["rejections"]),
            "raw_validation_pending_keys": list(
                acquisition_manifest["raw_validation_pending_keys"]
            ),
            "consumable_object_count": acquisition_manifest["consumable_object_count"],
            "integrity_rule": acquisition_manifest["integrity_rule"],
            "cadence_rule": acquisition_manifest["cadence_rule"],
        },
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
