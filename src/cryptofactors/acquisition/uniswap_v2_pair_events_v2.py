"""DEX-003 / ADR-0015 §9 — pure v2 block-major event acquisition foundation.

This module is **offline and pure**. It defines plan/query-domain identity,
5,000-block roots, birth-aware address cohorts, multi-address combined
Swap/Sync request construction, log-identity v2 (including transactionIndex),
dual-response reconciliation, deterministic address/block split trees with
exact parent-partition validation, per-pool/topic coverage proofs from agreed
leaves, and the persistence *records* later lease/receipt/header engines need.

It does **not**:

* contact RPCs or schedule network work;
* implement concurrency, leases, or durable writers;
* mutate or credit scalar v1 receipts;
* publish datasets or downstream products.

v1 code under ``uniswap_v2_pair_events`` remains unchanged and receives no v2
coverage credit (ADR-0015 §9.6).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, Literal

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UNISWAP_V2_FACTORY,
    UniswapV2IngestionError,
    _canonical_json,
    _hex_bytes,
    _hex_quantity,
    _require,
)
from cryptofactors.acquisition.uniswap_v2_pair_events import (
    SWAP_TOPIC,
    SYNC_TOPIC,
)

# ---------------------------------------------------------------------------
# Versioned constants (plan identity inputs)
# ---------------------------------------------------------------------------

PINNED_FINALITY_CUTOFF_BLOCK: Final[int] = 25_600_000
ROOT_BLOCK_SIZE: Final[int] = 5_000
# Generic PlanConfig default remains non-authoritative for production.
# ADR-0015 §9.10 production path requires cohort 8 (authenticated matrix selection).
DEFAULT_INITIAL_COHORT_SIZE: Final[int] = 64
PRODUCTION_INITIAL_COHORT_SIZE: Final[int] = 8
# Live provider matrix candidates (ADR-0015 §9.8). Production execution freezes the
# authenticated matrix selection (cohort 8); plan identity still includes the size.
CANDIDATE_COHORT_SIZES: Final[frozenset[int]] = frozenset({1, 8, 32, 64, 128})

# ADR-0015 §9.10 full production plan anchors (accepted registry, cohort 8).
PRODUCTION_PLAN_ID: Final[str] = (
    "plan_2b96356463410b9d0a3f4f7313a06260360853207ed1bf1e42eec9eb4d756584"
)
PRODUCTION_ROOT_COUNT: Final[int] = 1_858_348
PRODUCTION_POOL_TOPIC_BLOCKS: Final[int] = 148_506_716_734
PRODUCTION_ROOT_DOMAIN_SET_SHA256: Final[str] = (
    "081a12f780d065a7596ba073ba80819d173e8d74b3b16235672da673942ea907"
)
PRODUCTION_REGISTRY_PARQUET_SHA256: Final[str] = (
    "8e41a9fb1e1b05f126345ca0a7a9eb04792cd0e92d45406a9b5c031105d83256"
)
PRODUCTION_REGISTRY_PARQUET_BYTES: Final[int] = 1_606_417
CLAIM_ORDER_VERSION_DOMAIN_HASH_V1: Final[str] = "domain_hash_v1"
CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1: Final[str] = "chronological_v1"

# Ordered Swap then Sync — plan identity and topic-position-0 OR filter order.
ORDERED_EVENT_TOPICS: Final[tuple[str, str]] = (SWAP_TOPIC, SYNC_TOPIC)

PLAN_SCHEMA_VERSION: Final[str] = "1"
SPLIT_POLICY_VERSION: Final[str] = "1"
LOG_IDENTITY_VERSION: Final[str] = "2"
RECEIPT_SCHEMA_VERSION: Final[str] = "1"
COVERAGE_SCHEMA_VERSION: Final[str] = "1"

# Credential-free provider *organization* identities (not URLs or keys).
DEFAULT_EVENT_PROVIDER_ORGS: Final[tuple[str, str]] = ("infura", "blockpi")
DEFAULT_METADATA_PROVIDER_ORGS: Final[tuple[str, str]] = ("infura", "alchemy")

# Accepted production registry pin (CURRENT_TASK).
ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID: Final[str] = (
    "ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15"
)

# Swap: topic0 + 2 indexed addresses; data = 4 × uint256.
# Sync: topic0 only; data = 2 × uint256 (reserves fit uint112).
_SWAP_TOPIC_COUNT = 3
_SYNC_TOPIC_COUNT = 1
_SWAP_DATA_WORDS = 4
_SYNC_DATA_WORDS = 2
_UINT112_MAX = (1 << 112) - 1

QueryNodeStatus = Literal["PENDING", "IN_FLIGHT", "AGREED", "SPLIT"]
SplitReason = Literal[
    "block_range_limit",
    "oversized_result",
    "provider_disagreement",
    "conservative_cap",
    "manual",
]

_HEX_BODY = frozenset("0123456789abcdef")
_ORG_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_DS_ID_RE = re.compile(r"^ds_[a-f0-9]{64}$")
_PLAN_ID_RE = re.compile(r"^plan_[a-f0-9]{64}$")
_DOMAIN_ID_RE = re.compile(r"^qd_[a-f0-9]{64}$")
_LEAF_ID_RE = re.compile(r"^leaf_[a-f0-9]{64}$")
_HEADER_ID_RE = re.compile(r"^chdr_[a-f0-9]{64}$")
_RAW_ID_RE = re.compile(r"^raw_[a-f0-9]{64}$")
_ACQ_ID_RE = re.compile(r"^acq_[a-f0-9]{32}$|^acq_[a-f0-9]{64}$")


class PairEventV2Error(UniswapV2IngestionError):
    """Fail-closed pure-foundation errors for the v2 plan/coverage layer."""


# ---------------------------------------------------------------------------
# Canonical hashing / normalization
# ---------------------------------------------------------------------------


def _sha256_hex(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_digest(obj: Any) -> str:
    return _sha256_hex(_canonical_json(obj))


def normalize_address(value: object, *, label: str = "address") -> str:
    if not isinstance(value, str):
        raise PairEventV2Error(f"{label} must be a string")
    text = value.strip().lower()
    if not text.startswith("0x") or len(text) != 42:
        raise PairEventV2Error(f"{label} must be a 20-byte 0x address")
    body = text[2:]
    if any(c not in _HEX_BODY for c in body):
        raise PairEventV2Error(f"{label} must be a 20-byte 0x address")
    return text


def normalize_provider_org(value: object, *, label: str = "provider_org") -> str:
    if not isinstance(value, str) or not value.strip():
        raise PairEventV2Error(f"{label} must be a non-empty string")
    text = value.strip().lower()
    if not _ORG_RE.fullmatch(text):
        raise PairEventV2Error(
            f"{label} must be a credential-free organization id "
            f"(lowercase alphanumeric/underscore), got {value!r}"
        )
    return text


def _require_sha256_hex(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise PairEventV2Error(f"{label} must be 64 lowercase hex characters")
    return value


def _require_plan_id(value: object) -> str:
    if not isinstance(value, str) or not _PLAN_ID_RE.fullmatch(value):
        raise PairEventV2Error("plan_id must be plan_<64 hex>")
    return value


def _require_domain_id(value: object) -> str:
    if not isinstance(value, str) or not _DOMAIN_ID_RE.fullmatch(value):
        raise PairEventV2Error("domain_id must be qd_<64 hex>")
    return value


def _require_leaf_receipt_id(value: object) -> str:
    if not isinstance(value, str) or not _LEAF_ID_RE.fullmatch(value):
        raise PairEventV2Error("leaf_receipt_id must be leaf_<64 hex>")
    return value


def _require_raw_object_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _RAW_ID_RE.fullmatch(value):
        raise PairEventV2Error(f"{label} must be raw_<64 hex>")
    return value


def _uint256_words(data: str, *, expected_words: int, label: str) -> list[int]:
    body = data[2:] if data.startswith("0x") else data
    if len(body) != expected_words * 64:
        raise PairEventV2Error(
            f"{label} data must be exactly {expected_words} uint256 words, "
            f"got {len(body) // 64}"
        )
    if any(c not in _HEX_BODY for c in body.lower()):
        raise PairEventV2Error(f"{label} data is not valid hex")
    return [int(body[index * 64 : (index + 1) * 64], 16) for index in range(expected_words)]


# ---------------------------------------------------------------------------
# Plan configuration and identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """Inputs that uniquely identify a versioned block-major acquisition plan."""

    registry_dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID
    chain: str = ETHEREUM_CHAIN
    factory: str = UNISWAP_V2_FACTORY
    deployment_block: int = UNISWAP_V2_DEPLOYMENT_BLOCK
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK
    root_block_size: int = ROOT_BLOCK_SIZE
    topics: tuple[str, ...] = ORDERED_EVENT_TOPICS
    initial_cohort_size: int = DEFAULT_INITIAL_COHORT_SIZE
    split_policy_version: str = SPLIT_POLICY_VERSION
    event_provider_orgs: tuple[str, ...] = DEFAULT_EVENT_PROVIDER_ORGS
    metadata_provider_orgs: tuple[str, ...] = DEFAULT_METADATA_PROVIDER_ORGS
    log_identity_version: str = LOG_IDENTITY_VERSION
    receipt_schema_version: str = RECEIPT_SCHEMA_VERSION
    plan_schema_version: str = PLAN_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.registry_dataset_id, str) or not _DS_ID_RE.fullmatch(
            self.registry_dataset_id
        ):
            raise PairEventV2Error("registry_dataset_id must be ds_<64 hex>")
        if self.registry_dataset_id != ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID:
            raise PairEventV2Error(
                "registry_dataset_id must be the pinned accepted dex_pool_registry"
            )
        if self.chain != ETHEREUM_CHAIN:
            raise PairEventV2Error("v2 plan supports ethereum only")
        if normalize_address(self.factory, label="factory") != UNISWAP_V2_FACTORY.lower():
            raise PairEventV2Error("factory must be the canonical Uniswap V2 factory")
        object.__setattr__(self, "factory", UNISWAP_V2_FACTORY.lower())
        if self.deployment_block != UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventV2Error("deployment_block must match Uniswap V2 deployment")
        if self.cutoff_block != PINNED_FINALITY_CUTOFF_BLOCK:
            raise PairEventV2Error(
                "cutoff_block must be the pinned finality cutoff 25600000"
            )
        if self.root_block_size != ROOT_BLOCK_SIZE:
            raise PairEventV2Error("root_block_size must be 5000")
        if self.initial_cohort_size not in CANDIDATE_COHORT_SIZES:
            raise PairEventV2Error(
                "initial_cohort_size must be one of the versioned matrix candidates "
                f"{sorted(CANDIDATE_COHORT_SIZES)}; got {self.initial_cohort_size}"
            )
        if tuple(self.topics) != ORDERED_EVENT_TOPICS:
            raise PairEventV2Error("topics must be the ordered Swap then Sync pair")
        if self.split_policy_version != SPLIT_POLICY_VERSION:
            raise PairEventV2Error(
                f"split_policy_version must be {SPLIT_POLICY_VERSION!r}"
            )
        if self.plan_schema_version != PLAN_SCHEMA_VERSION:
            raise PairEventV2Error(f"plan_schema_version must be {PLAN_SCHEMA_VERSION!r}")
        if self.receipt_schema_version != RECEIPT_SCHEMA_VERSION:
            raise PairEventV2Error(
                f"receipt_schema_version must be {RECEIPT_SCHEMA_VERSION!r}"
            )
        if self.log_identity_version != LOG_IDENTITY_VERSION:
            raise PairEventV2Error(
                f"log_identity_version must be {LOG_IDENTITY_VERSION!r}"
            )

        event_orgs = tuple(
            normalize_provider_org(org, label="event_provider_org")
            for org in self.event_provider_orgs
        )
        meta_orgs = tuple(
            normalize_provider_org(org, label="metadata_provider_org")
            for org in self.metadata_provider_orgs
        )
        if len(event_orgs) != 2 or len(set(event_orgs)) != 2:
            raise PairEventV2Error(
                "event_provider_orgs must be two distinct organization identities"
            )
        if len(meta_orgs) != 2 or len(set(meta_orgs)) != 2:
            raise PairEventV2Error(
                "metadata_provider_orgs must be two distinct organization identities"
            )
        object.__setattr__(self, "event_provider_orgs", event_orgs)
        object.__setattr__(self, "metadata_provider_orgs", meta_orgs)

    def identity_payload(self) -> dict[str, Any]:
        """Canonical map hashed into the plan ID (ADR-0015 §9.1)."""
        return {
            "chain": self.chain,
            "cutoff_block": self.cutoff_block,
            "deployment_block": self.deployment_block,
            "event_provider_orgs": list(self.event_provider_orgs),
            "factory": self.factory,
            "initial_cohort_size": self.initial_cohort_size,
            "log_identity_version": self.log_identity_version,
            "metadata_provider_orgs": list(self.metadata_provider_orgs),
            "plan_schema_version": self.plan_schema_version,
            "receipt_schema_version": self.receipt_schema_version,
            "registry_dataset_id": self.registry_dataset_id,
            "root_block_size": self.root_block_size,
            "split_policy_version": self.split_policy_version,
            "topics": list(self.topics),
        }

    def plan_id(self) -> str:
        return "plan_" + _canonical_digest(self.identity_payload())


# ---------------------------------------------------------------------------
# Registry pool refs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryPoolBirth:
    """Minimal registry fields required for v2 planning and coverage."""

    pool_address: str
    creation_block: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "pool_address",
            normalize_address(self.pool_address, label="pool_address"),
        )
        if not isinstance(self.creation_block, int) or isinstance(self.creation_block, bool):
            raise PairEventV2Error("creation_block must be an int")
        if self.creation_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventV2Error("creation_block precedes Uniswap V2 deployment")


def sort_pool_births(
    pools: Sequence[RegistryPoolBirth],
    *,
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> tuple[RegistryPoolBirth, ...]:
    """Deterministic address order; every birth must be on or before cutoff."""
    seen: set[str] = set()
    ordered: list[RegistryPoolBirth] = []
    for pool in sorted(pools, key=lambda p: p.pool_address):
        if pool.creation_block > cutoff_block:
            raise PairEventV2Error(
                "registry pool creation_block is after plan cutoff",
            )
        if pool.pool_address in seen:
            raise PairEventV2Error("duplicate pool_address in registry slice")
        seen.add(pool.pool_address)
        ordered.append(pool)
    return tuple(ordered)


# ---------------------------------------------------------------------------
# Root windows and cohorts
# ---------------------------------------------------------------------------


def iter_root_windows(
    *,
    deployment_block: int = UNISWAP_V2_DEPLOYMENT_BLOCK,
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
    root_block_size: int = ROOT_BLOCK_SIZE,
) -> tuple[tuple[int, int], ...]:
    """Inclusive 5,000-block roots from deployment through cutoff."""
    if root_block_size != ROOT_BLOCK_SIZE:
        raise PairEventV2Error("root_block_size must be 5000")
    if deployment_block != UNISWAP_V2_DEPLOYMENT_BLOCK:
        raise PairEventV2Error("deployment_block must match Uniswap V2 deployment")
    if cutoff_block != PINNED_FINALITY_CUTOFF_BLOCK:
        raise PairEventV2Error("cutoff_block must be the pinned finality cutoff")
    windows: list[tuple[int, int]] = []
    start = deployment_block
    while start <= cutoff_block:
        end = min(start + root_block_size - 1, cutoff_block)
        windows.append((start, end))
        start = end + 1
    return tuple(windows)


def eligible_pools_for_root(
    pools: Sequence[RegistryPoolBirth],
    *,
    root_end: int,
) -> tuple[RegistryPoolBirth, ...]:
    """Pools born on or before the root end, sorted by address."""
    eligible = [p for p in pools if p.creation_block <= root_end]
    return sort_pool_births(eligible)


def partition_address_cohorts(
    addresses: Sequence[str],
    *,
    cohort_size: int = DEFAULT_INITIAL_COHORT_SIZE,
) -> tuple[tuple[str, ...], ...]:
    """Partition a sorted address list into fixed-size cohorts (last may be short)."""
    if cohort_size <= 0:
        raise PairEventV2Error("cohort_size must be positive")
    # Always normalize and re-check order — no validation bypass.
    normalized = [normalize_address(a) for a in addresses]
    if normalized != sorted(normalized):
        raise PairEventV2Error("addresses must be sorted ascending before cohorting")
    if len(set(normalized)) != len(normalized):
        raise PairEventV2Error("addresses must be unique")
    cohorts: list[tuple[str, ...]] = []
    for index in range(0, len(normalized), cohort_size):
        cohorts.append(tuple(normalized[index : index + cohort_size]))
    return tuple(cohorts)


# ---------------------------------------------------------------------------
# Query domain / node identity
# ---------------------------------------------------------------------------


def _validate_topics(topics: Sequence[str]) -> tuple[str, ...]:
    if not topics:
        raise PairEventV2Error("topics must be non-empty")
    topic_rank = {topic: index for index, topic in enumerate(ORDERED_EVENT_TOPICS)}
    for topic in topics:
        if topic not in topic_rank:
            raise PairEventV2Error(f"unsupported topic: {topic!r}")
    ranks = [topic_rank[t] for t in topics]
    if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
        raise PairEventV2Error("topics must be unique and ordered Swap then Sync")
    return tuple(topics)


@dataclass(frozen=True, slots=True)
class QueryDomain:
    """Block interval × address set × topic set — the unit of dual-provider work."""

    start_block: int
    end_block: int
    addresses: tuple[str, ...]
    topics: tuple[str, ...] = ORDERED_EVENT_TOPICS

    def __post_init__(self) -> None:
        if self.end_block < self.start_block:
            raise PairEventV2Error("end_block precedes start_block")
        if self.start_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventV2Error("start_block precedes Uniswap V2 deployment")
        if self.end_block > PINNED_FINALITY_CUTOFF_BLOCK:
            raise PairEventV2Error("end_block exceeds pinned finality cutoff")
        if not self.addresses:
            raise PairEventV2Error("addresses must be non-empty")
        normalized = tuple(normalize_address(a) for a in self.addresses)
        if normalized != tuple(sorted(normalized)):
            raise PairEventV2Error("addresses must be sorted ascending")
        if len(set(normalized)) != len(normalized):
            raise PairEventV2Error("addresses must be unique")
        object.__setattr__(self, "addresses", normalized)
        object.__setattr__(self, "topics", _validate_topics(self.topics))

    @property
    def address_count(self) -> int:
        return len(self.addresses)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "addresses": list(self.addresses),
            "end_block": self.end_block,
            "start_block": self.start_block,
            "topics": list(self.topics),
        }

    def domain_id(self, plan_id: str) -> str:
        plan = _require_plan_id(plan_id)
        payload = {"domain": self.identity_payload(), "plan_id": plan}
        return "qd_" + _canonical_digest(payload)


@dataclass(frozen=True, slots=True)
class QueryNode:
    """One scheduler node: a query domain plus lifecycle status metadata."""

    plan_id: str
    domain: QueryDomain
    status: QueryNodeStatus = "PENDING"
    parent_domain_id: str | None = None
    split_reason: SplitReason | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))
        if self.parent_domain_id is not None:
            object.__setattr__(
                self, "parent_domain_id", _require_domain_id(self.parent_domain_id)
            )

    @property
    def domain_id(self) -> str:
        return self.domain.domain_id(self.plan_id)


# ---------------------------------------------------------------------------
# Multi-address combined Swap/Sync request construction
# ---------------------------------------------------------------------------


def combined_pair_logs_request(
    *,
    addresses: Sequence[str],
    start_block: int,
    end_block: int,
    topics: Sequence[str] = ORDERED_EVENT_TOPICS,
) -> dict[str, Any]:
    """Build eth_getLogs with address array and topic-position-0 OR."""
    domain = QueryDomain(
        start_block=start_block,
        end_block=end_block,
        addresses=tuple(addresses),
        topics=tuple(topics),
    )
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getLogs",
        "params": [
            {
                "address": list(domain.addresses),
                "fromBlock": hex(domain.start_block),
                "toBlock": hex(domain.end_block),
                "topics": [list(domain.topics)],
            }
        ],
    }


def request_for_domain(domain: QueryDomain) -> dict[str, Any]:
    return combined_pair_logs_request(
        addresses=domain.addresses,
        start_block=domain.start_block,
        end_block=domain.end_block,
        topics=domain.topics,
    )


# ---------------------------------------------------------------------------
# Log identity v2 + dual reconciliation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LogIdentityV2:
    """Order-independent log identity including every published-row field.

    Corrects the v1 digest omission of ``transactionIndex`` (ADR-0015 §9.3).
    """

    address: str
    block_number: int
    block_hash: str
    tx_hash: str
    tx_index: int
    log_index: int
    topics: tuple[str, ...]
    data: str
    removed: bool

    def as_tuple(self) -> tuple[Any, ...]:
        """Complete identity — used for both equality and order-independent sort."""
        return (
            self.address,
            self.block_number,
            self.block_hash,
            self.tx_hash,
            self.tx_index,
            self.log_index,
            self.topics,
            self.data,
            self.removed,
        )

    def position_key(self) -> tuple[str, str, int]:
        """Canonical chain position: one log slot per (block_hash, tx, log_index)."""
        return (self.block_hash, self.tx_hash, self.log_index)

    def sort_key(self) -> tuple[Any, ...]:
        # Full identity tuple — ordering is independent of provider response order
        # and does not drop any published field (including data/topics/removed).
        return self.as_tuple()


def extract_log_identity_v2(log: Mapping[str, Any]) -> LogIdentityV2:
    """Strict normalization of one eth_getLogs entry into identity v2."""
    if not isinstance(log, Mapping):
        raise PairEventV2Error("log entry must be an object")
    topics_raw = log.get("topics")
    if not isinstance(topics_raw, list) or not topics_raw:
        raise PairEventV2Error("log topics must be a non-empty list")
    topics = tuple(
        _hex_bytes(topic, 32, label=f"topic[{index}]")
        for index, topic in enumerate(topics_raw)
    )
    data_raw = _require(log, "data", label="log")
    if not isinstance(data_raw, str) or not data_raw.startswith("0x"):
        raise PairEventV2Error(f"log data must be 0x-prefixed hex, got {data_raw!r}")
    data_body = data_raw[2:]
    if len(data_body) % 2 != 0 or any(
        c not in "0123456789abcdefABCDEF" for c in data_body
    ):
        raise PairEventV2Error(f"log data is not valid hex: {data_raw!r}")
    removed = _require(log, "removed", label="log")
    if not isinstance(removed, bool):
        raise PairEventV2Error("log removed flag must be a boolean")
    return LogIdentityV2(
        address=_hex_bytes(_require(log, "address", label="log"), 20, label="log address"),
        block_number=_hex_quantity(
            _require(log, "blockNumber", label="log"), label="blockNumber"
        ),
        block_hash=_hex_bytes(
            _require(log, "blockHash", label="log"), 32, label="log blockHash"
        ),
        tx_hash=_hex_bytes(
            _require(log, "transactionHash", label="log"), 32, label="transactionHash"
        ),
        tx_index=_hex_quantity(
            _require(log, "transactionIndex", label="log"), label="transactionIndex"
        ),
        log_index=_hex_quantity(_require(log, "logIndex", label="log"), label="logIndex"),
        topics=topics,
        data="0x" + data_body.lower(),
        removed=removed,
    )


def validate_event_shape(identity: LogIdentityV2) -> None:
    """Enforce exact Uniswap V2 Swap/Sync topic and data shapes."""
    topic0 = identity.topics[0] if identity.topics else None
    if topic0 == SWAP_TOPIC:
        if len(identity.topics) != _SWAP_TOPIC_COUNT:
            raise PairEventV2Error(
                f"Swap must have {_SWAP_TOPIC_COUNT} topics, got {len(identity.topics)}"
            )
        # topics[1], topics[2] are indexed addresses (left-padded 32-byte words).
        for index in (1, 2):
            word = identity.topics[index]
            if word[2:26] != "0" * 24:
                raise PairEventV2Error(
                    f"Swap topic[{index}] is not a left-padded 20-byte address"
                )
        _uint256_words(identity.data, expected_words=_SWAP_DATA_WORDS, label="Swap")
        return
    if topic0 == SYNC_TOPIC:
        if len(identity.topics) != _SYNC_TOPIC_COUNT:
            raise PairEventV2Error(
                f"Sync must have {_SYNC_TOPIC_COUNT} topic, got {len(identity.topics)}"
            )
        reserves = _uint256_words(
            identity.data, expected_words=_SYNC_DATA_WORDS, label="Sync"
        )
        if any(value > _UINT112_MAX for value in reserves):
            raise PairEventV2Error("Sync reserve exceeds uint112")
        return
    raise PairEventV2Error(f"unsupported event topic0: {topic0!r}")


def log_identity_v2_digest(identities: Sequence[LogIdentityV2]) -> str:
    """SHA-256 of the order-independent identity set (sorted by full identity)."""
    ordered = sorted(identities, key=lambda item: item.sort_key())
    payload = json.dumps([item.as_tuple() for item in ordered], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_log_against_domain(
    identity: LogIdentityV2,
    domain: QueryDomain,
) -> None:
    """Fail closed on removed, shape, range, cohort, or unsupported topic."""
    if identity.removed:
        raise PairEventV2Error("removed log cannot become authority")
    validate_event_shape(identity)
    if identity.block_number < domain.start_block or identity.block_number > domain.end_block:
        raise PairEventV2Error("log block_number outside query domain")
    if identity.address not in domain.addresses:
        raise PairEventV2Error("log address outside query cohort")
    if identity.topics[0] not in domain.topics:
        raise PairEventV2Error("log topic0 is not in the query topic set")


def normalize_and_index_logs(
    logs: Sequence[Any],
    domain: QueryDomain,
    *,
    allow_empty: bool = True,
) -> tuple[LogIdentityV2, ...]:
    """Extract, validate shape, and reject position/identity duplicates."""
    if not isinstance(logs, Sequence) or isinstance(logs, (str, bytes)):
        raise PairEventV2Error("logs result must be a list")
    if not logs and not allow_empty:
        raise PairEventV2Error("empty logs result is not allowed")
    identities: list[LogIdentityV2] = []
    seen_full: set[tuple[Any, ...]] = set()
    seen_position: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(logs):
        if not isinstance(raw, Mapping):
            raise PairEventV2Error(f"log[{index}] must be an object")
        identity = extract_log_identity_v2(raw)
        validate_log_against_domain(identity, domain)
        full_key = identity.as_tuple()
        if full_key in seen_full:
            raise PairEventV2Error("duplicate log identity within provider response")
        position = identity.position_key()
        if position in seen_position:
            raise PairEventV2Error(
                "duplicate canonical log position (block_hash, tx_hash, log_index) "
                "within provider response"
            )
        seen_full.add(full_key)
        seen_position.add(position)
        identities.append(identity)
    return tuple(sorted(identities, key=lambda item: item.sort_key()))


def reconcile_log_sets_v2(
    primary_logs: Sequence[Any],
    secondary_logs: Sequence[Any],
    domain: QueryDomain,
) -> tuple[tuple[LogIdentityV2, ...], str]:
    """Require exact identity-set agreement from two independent providers."""
    primary = normalize_and_index_logs(primary_logs, domain)
    secondary = normalize_and_index_logs(secondary_logs, domain)
    if len(primary) != len(secondary):
        raise PairEventV2Error(
            f"log count disagreement: primary={len(primary)} secondary={len(secondary)}"
        )
    primary_set = {item.as_tuple() for item in primary}
    secondary_set = {item.as_tuple() for item in secondary}
    if primary_set != secondary_set:
        raise PairEventV2Error("log identity disagreement between providers")
    # Position sets must also match (defensive: follows from full identity).
    if {item.position_key() for item in primary} != {
        item.position_key() for item in secondary
    }:
        raise PairEventV2Error("log position disagreement between providers")
    digest = log_identity_v2_digest(primary)
    if log_identity_v2_digest(secondary) != digest:
        raise PairEventV2Error("log identity digest disagreement")
    return primary, digest


# ---------------------------------------------------------------------------
# Deterministic split trees
# ---------------------------------------------------------------------------


def split_domain_by_address(domain: QueryDomain) -> tuple[QueryDomain, QueryDomain]:
    """Split the address set into two non-empty contiguous halves (sorted order)."""
    if domain.address_count < 2:
        raise PairEventV2Error(
            "address split requires at least two addresses; use block split for singletons"
        )
    mid = domain.address_count // 2
    left = QueryDomain(
        start_block=domain.start_block,
        end_block=domain.end_block,
        addresses=domain.addresses[:mid],
        topics=domain.topics,
    )
    right = QueryDomain(
        start_block=domain.start_block,
        end_block=domain.end_block,
        addresses=domain.addresses[mid:],
        topics=domain.topics,
    )
    validate_children_partition(domain, (left, right))
    return left, right


def split_domain_by_block(domain: QueryDomain) -> tuple[QueryDomain, QueryDomain]:
    """Split the block interval into two contiguous halves."""
    if domain.end_block <= domain.start_block:
        raise PairEventV2Error(
            "block split requires a multi-block interval; singleton block is terminal"
        )
    span = domain.end_block - domain.start_block + 1
    left_span = span // 2
    left_end = domain.start_block + left_span - 1
    left = QueryDomain(
        start_block=domain.start_block,
        end_block=left_end,
        addresses=domain.addresses,
        topics=domain.topics,
    )
    right = QueryDomain(
        start_block=left_end + 1,
        end_block=domain.end_block,
        addresses=domain.addresses,
        topics=domain.topics,
    )
    validate_children_partition(domain, (left, right))
    return left, right


def choose_split(
    domain: QueryDomain,
    *,
    reason: SplitReason,
) -> tuple[QueryDomain, ...]:
    """Apply the versioned split policy (ADR-0015 §9.2)."""
    if reason in ("oversized_result", "conservative_cap", "provider_disagreement"):
        if domain.address_count >= 2:
            return split_domain_by_address(domain)
        return split_domain_by_block(domain)
    if reason == "block_range_limit":
        return split_domain_by_block(domain)
    if reason == "manual":
        if domain.address_count >= 2:
            return split_domain_by_address(domain)
        return split_domain_by_block(domain)
    raise PairEventV2Error(f"unsupported split reason: {reason!r}")


def validate_children_partition(
    parent: QueryDomain,
    children: Sequence[QueryDomain],
) -> None:
    """Require children to be a disjoint exact partition of the parent domain."""
    if not children:
        raise PairEventV2Error("split produced no children")
    for child in children:
        if child.topics != parent.topics:
            raise PairEventV2Error("child topics must equal parent topics")

    address_split = all(
        child.start_block == parent.start_block and child.end_block == parent.end_block
        for child in children
    )
    block_split = all(child.addresses == parent.addresses for child in children)

    if address_split and not block_split:
        parent_addresses = list(parent.addresses)
        child_addresses: list[str] = []
        for child in children:
            child_addresses.extend(child.addresses)
        if sorted(child_addresses) != parent_addresses:
            raise PairEventV2Error(
                "child address sets do not form an exact partition of the parent"
            )
        return

    if block_split and not address_split:
        ordered = sorted(children, key=lambda c: c.start_block)
        if ordered[0].start_block != parent.start_block:
            raise PairEventV2Error("block-split children miss parent start")
        if ordered[-1].end_block != parent.end_block:
            raise PairEventV2Error("block-split children miss parent end")
        expected = parent.start_block
        for child in ordered:
            if child.start_block != expected:
                raise PairEventV2Error("block-split children have a gap or overlap")
            expected = child.end_block + 1
        if expected != parent.end_block + 1:
            raise PairEventV2Error("block-split children do not cover parent end")
        return

    if address_split and block_split:
        if len(children) == 1 and children[0].identity_payload() == parent.identity_payload():
            return
        raise PairEventV2Error("mixed address+block split is not a pure partition")

    raise PairEventV2Error(
        "children must be a pure address partition or a pure block partition of parent"
    )


def split_node(
    node: QueryNode,
    *,
    reason: SplitReason,
) -> tuple[QueryNode, ...]:
    """Produce PENDING child nodes that exactly partition the parent domain."""
    children = choose_split(node.domain, reason=reason)
    return tuple(
        QueryNode(
            plan_id=node.plan_id,
            domain=child,
            status="PENDING",
            parent_domain_id=node.domain_id,
            split_reason=reason,
        )
        for child in children
    )


# ---------------------------------------------------------------------------
# Birth-aware domain clamping and root plan construction
# ---------------------------------------------------------------------------


def birth_clamped_interval(
    *,
    creation_block: int,
    domain_start: int,
    domain_end: int,
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> tuple[int, int] | None:
    """Return the inclusive interval a pool contributes inside a domain, if any."""
    start = max(creation_block, domain_start)
    end = min(cutoff_block, domain_end)
    if end < start:
        return None
    return start, end


@dataclass(frozen=True, slots=True)
class RootFilterPlan:
    """One initial root filter (block window × address cohort) before splits."""

    plan_id: str
    root_start: int
    root_end: int
    cohort_index: int
    domain: QueryDomain

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))

    @property
    def domain_id(self) -> str:
        return self.domain.domain_id(self.plan_id)


@dataclass(frozen=True, slots=True)
class AcquisitionPlanV2:
    """Complete deterministic root filter set for a registry + plan config."""

    config: PlanConfig
    plan_id: str
    pools: tuple[RegistryPoolBirth, ...]
    root_windows: tuple[tuple[int, int], ...]
    root_filters: tuple[RootFilterPlan, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))
        if self.plan_id != self.config.plan_id():
            raise PairEventV2Error("plan_id does not match config identity")

    @property
    def root_filter_count(self) -> int:
        return len(self.root_filters)

    @property
    def root_window_count(self) -> int:
        return len(self.root_windows)


def build_acquisition_plan_v2(
    pools: Sequence[RegistryPoolBirth],
    config: PlanConfig | None = None,
) -> AcquisitionPlanV2:
    """Build the versioned block-major root plan (no network)."""
    cfg = config if config is not None else PlanConfig()
    plan_id = cfg.plan_id()
    ordered_pools = sort_pool_births(pools, cutoff_block=cfg.cutoff_block)
    if not ordered_pools:
        raise PairEventV2Error("registry slice is empty")
    windows = iter_root_windows(
        deployment_block=cfg.deployment_block,
        cutoff_block=cfg.cutoff_block,
        root_block_size=cfg.root_block_size,
    )
    filters: list[RootFilterPlan] = []
    for root_start, root_end in windows:
        addresses = tuple(
            pool.pool_address
            for pool in ordered_pools
            if pool.creation_block <= root_end
        )
        if not addresses:
            continue
        # Re-validate every address (normalize + sort/uniqueness checks).
        cohorts = partition_address_cohorts(
            addresses, cohort_size=cfg.initial_cohort_size
        )
        for cohort_index, cohort in enumerate(cohorts):
            domain = QueryDomain(
                start_block=root_start,
                end_block=root_end,
                addresses=cohort,
                topics=cfg.topics,
            )
            filters.append(
                RootFilterPlan(
                    plan_id=plan_id,
                    root_start=root_start,
                    root_end=root_end,
                    cohort_index=cohort_index,
                    domain=domain,
                )
            )
    return AcquisitionPlanV2(
        config=cfg,
        plan_id=plan_id,
        pools=ordered_pools,
        root_windows=windows,
        root_filters=tuple(filters),
    )


# ---------------------------------------------------------------------------
# Deterministic leaf / header receipt identity
# ---------------------------------------------------------------------------


def _normalize_header_dependency_ids(
    header_ids: Sequence[str],
) -> tuple[str, ...]:
    """Sorted unique chdr_ ids; authoritative leaves require non-empty evidence."""
    if not header_ids:
        raise PairEventV2Error(
            "authoritative leaf requires non-empty canonical header dependencies"
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for header_id in header_ids:
        if not isinstance(header_id, str) or not _HEADER_ID_RE.fullmatch(header_id):
            raise PairEventV2Error(
                "canonical header dependency must be chdr_<64 hex>"
            )
        if header_id not in seen:
            seen.add(header_id)
            normalized.append(header_id)
    return tuple(sorted(normalized))


def compute_leaf_receipt_id(
    *,
    plan_id: str,
    domain_id: str,
    start_block: int,
    end_block: int,
    addresses: Sequence[str],
    topics: Sequence[str],
    log_identity_sha256: str,
    primary_provider_org: str,
    secondary_provider_org: str,
    primary_logs_raw_object_id: str,
    secondary_logs_raw_object_id: str,
    primary_logs_acquisition_id: str,
    secondary_logs_acquisition_id: str,
    log_count: int,
    canonical_header_receipt_ids: Sequence[str],
) -> str:
    """Deterministic durable leaf receipt id (binds all replay-critical fields)."""
    plan = _require_plan_id(plan_id)
    domain = QueryDomain(
        start_block=int(start_block),
        end_block=int(end_block),
        addresses=tuple(addresses),
        topics=tuple(topics),
    )
    expected_domain_id = domain.domain_id(plan)
    got_domain_id = _require_domain_id(domain_id)
    if got_domain_id != expected_domain_id:
        raise PairEventV2Error(
            "domain_id does not match plan_id + canonical domain fields"
        )
    headers = _normalize_header_dependency_ids(canonical_header_receipt_ids)
    primary_org = normalize_provider_org(primary_provider_org)
    secondary_org = normalize_provider_org(secondary_provider_org)
    if primary_org == secondary_org:
        raise PairEventV2Error("leaf providers must be distinct organizations")
    if int(log_count) < 0:
        raise PairEventV2Error("log_count must be >= 0")
    payload = {
        "addresses": list(domain.addresses),
        "canonical_header_receipt_ids": list(headers),
        "domain_id": got_domain_id,
        "end_block": domain.end_block,
        "log_count": int(log_count),
        "log_identity_sha256": _require_sha256_hex(
            log_identity_sha256, label="log_identity_sha256"
        ),
        "log_identity_version": LOG_IDENTITY_VERSION,
        "plan_id": plan,
        "primary_logs_acquisition_id": str(primary_logs_acquisition_id),
        "primary_logs_raw_object_id": _require_raw_object_id(
            primary_logs_raw_object_id, label="primary_logs_raw_object_id"
        ),
        "primary_provider_org": primary_org,
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "secondary_logs_acquisition_id": str(secondary_logs_acquisition_id),
        "secondary_logs_raw_object_id": _require_raw_object_id(
            secondary_logs_raw_object_id, label="secondary_logs_raw_object_id"
        ),
        "secondary_provider_org": secondary_org,
        "start_block": domain.start_block,
        "topics": list(domain.topics),
    }
    return "leaf_" + _canonical_digest(payload)


def compute_canonical_header_receipt_id(
    *,
    plan_id: str,
    block_number: int,
    block_hash: str,
    block_timestamp: int,
    primary_provider_org: str,
    secondary_provider_org: str,
    primary_raw_object_id: str,
    secondary_raw_object_id: str,
    primary_acquisition_id: str,
    secondary_acquisition_id: str,
) -> str:
    primary_org = normalize_provider_org(primary_provider_org)
    secondary_org = normalize_provider_org(secondary_provider_org)
    if primary_org == secondary_org:
        raise PairEventV2Error("header providers must be distinct organizations")
    payload = {
        "block_hash": _hex_bytes(block_hash, 32, label="block_hash"),
        "block_number": int(block_number),
        "block_timestamp": int(block_timestamp),
        "plan_id": _require_plan_id(plan_id),
        "primary_acquisition_id": str(primary_acquisition_id),
        "primary_provider_org": primary_org,
        "primary_raw_object_id": _require_raw_object_id(
            primary_raw_object_id, label="primary_raw_object_id"
        ),
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "secondary_acquisition_id": str(secondary_acquisition_id),
        "secondary_provider_org": secondary_org,
        "secondary_raw_object_id": _require_raw_object_id(
            secondary_raw_object_id, label="secondary_raw_object_id"
        ),
    }
    return "chdr_" + _canonical_digest(payload)


# ---------------------------------------------------------------------------
# Exact per-pool/topic coverage from validated leaf + header receipts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PoolTopicCoverage:
    """Exact coverage product for one (pool, topic0) domain (ADR-0015 §9.6)."""

    plan_id: str
    pool_address: str
    topic: str
    expected_start: int
    expected_end: int
    expected_block_count: int
    covered_block_count: int
    first_covered_block: int | None
    last_covered_block: int | None
    leaf_count: int
    # Boolean gap/overlap flags (exact fail-closed). Interval lists are not retained.
    has_gap: bool
    has_overlap: bool
    # Incremental hash root over contributing receipt ids in deterministic stream order.
    supporting_receipts_root: str
    coverage_hash: str

    @property
    def is_complete(self) -> bool:
        return (
            not self.has_gap
            and not self.has_overlap
            and self.covered_block_count == self.expected_block_count
        )


def expected_pool_topic_domain(
    pool: RegistryPoolBirth,
    *,
    topic: str,
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> tuple[int, int]:
    if topic not in ORDERED_EVENT_TOPICS:
        raise PairEventV2Error(f"unsupported topic: {topic!r}")
    if cutoff_block < pool.creation_block:
        raise PairEventV2Error("cutoff precedes pool creation")
    if pool.creation_block > cutoff_block:
        raise PairEventV2Error("pool creation_block is after cutoff")
    return pool.creation_block, cutoff_block


def _chain_receipt_root(previous: str, receipt_id: str) -> str:
    """Incremental supporting-receipt root (deterministic stream order)."""
    return _canonical_digest(
        {
            "prev": previous,
            "receipt_id": _require_leaf_receipt_id(receipt_id),
            "schema_version": COVERAGE_SCHEMA_VERSION,
        }
    )


EMPTY_SUPPORTING_RECEIPTS_ROOT: Final[str] = _canonical_digest(
    {"prev": "", "receipt_id": "", "schema_version": COVERAGE_SCHEMA_VERSION, "empty": True}
)


@dataclass(slots=True)
class _TopicCoverageCursor:
    """Constant-size per-(pool, topic) streaming state.

    Intervals must be applied in non-decreasing start order (global receipt sort).
    Stores no interval list and no receipt-id set/list.
    """

    expected_start: int
    expected_end: int
    prev_end: int  # exclusive high-water: last covered block; init expected_start-1
    covered_count: int = 0
    leaf_count: int = 0
    has_gap: bool = False
    has_overlap: bool = False
    first_covered: int | None = None
    last_covered: int | None = None
    receipts_root: str = EMPTY_SUPPORTING_RECEIPTS_ROOT

    def add_sorted(self, start: int, end: int, receipt_id: str) -> None:
        """Apply one birth-clamped interval with start >= all previous starts."""
        start = max(start, self.expected_start)
        end = min(end, self.expected_end)
        if end < start:
            return
        if start > self.prev_end + 1:
            self.has_gap = True
        if start <= self.prev_end:
            self.has_overlap = True
            if end > self.prev_end:
                self.covered_count += end - self.prev_end
                self.prev_end = end
        else:
            # Adjacent or after a gap: count full [start, end].
            self.covered_count += end - start + 1
            self.prev_end = end
        if self.first_covered is None:
            self.first_covered = start
        self.last_covered = end if self.last_covered is None else max(self.last_covered, end)
        self.leaf_count += 1
        self.receipts_root = _chain_receipt_root(self.receipts_root, receipt_id)

    def finalize(self, *, plan_id: str, pool_address: str, topic: str) -> PoolTopicCoverage:
        if self.prev_end < self.expected_end:
            self.has_gap = True
        expected_count = self.expected_end - self.expected_start + 1
        coverage_hash = _canonical_digest(
            {
                "covered_block_count": self.covered_count,
                "expected_block_count": expected_count,
                "expected_end": self.expected_end,
                "expected_start": self.expected_start,
                "first_covered_block": self.first_covered,
                "has_gap": self.has_gap,
                "has_overlap": self.has_overlap,
                "last_covered_block": self.last_covered,
                "leaf_count": self.leaf_count,
                "plan_id": plan_id,
                "pool_address": pool_address,
                "schema_version": COVERAGE_SCHEMA_VERSION,
                "supporting_receipts_root": self.receipts_root,
                "topic": topic,
            }
        )
        return PoolTopicCoverage(
            plan_id=plan_id,
            pool_address=pool_address,
            topic=topic,
            expected_start=self.expected_start,
            expected_end=self.expected_end,
            expected_block_count=expected_count,
            covered_block_count=self.covered_count,
            first_covered_block=self.first_covered,
            last_covered_block=self.last_covered,
            leaf_count=self.leaf_count,
            has_gap=self.has_gap,
            has_overlap=self.has_overlap,
            supporting_receipts_root=self.receipts_root,
            coverage_hash=coverage_hash,
        )


def _receipt_map(
    validated_receipts: Mapping[str, LeafReceiptRecord] | Sequence[LeafReceiptRecord],
) -> dict[str, LeafReceiptRecord]:
    if isinstance(validated_receipts, Mapping):
        out: dict[str, LeafReceiptRecord] = {}
        for key, receipt in validated_receipts.items():
            if key != receipt.leaf_receipt_id:
                raise PairEventV2Error(
                    "validated_receipts map key must equal leaf_receipt_id"
                )
            out[receipt.leaf_receipt_id] = receipt
        return out
    out = {}
    for receipt in validated_receipts:
        if receipt.leaf_receipt_id in out:
            raise PairEventV2Error(
                f"duplicate leaf_receipt_id in validated receipts: "
                f"{receipt.leaf_receipt_id}"
            )
        out[receipt.leaf_receipt_id] = receipt
    return out


def _header_map(
    validated_headers: Mapping[str, CanonicalHeaderReceiptRecord]
    | Sequence[CanonicalHeaderReceiptRecord],
) -> dict[str, CanonicalHeaderReceiptRecord]:
    if isinstance(validated_headers, Mapping):
        out: dict[str, CanonicalHeaderReceiptRecord] = {}
        for key, header in validated_headers.items():
            if key != header.header_receipt_id:
                raise PairEventV2Error(
                    "validated_headers map key must equal header_receipt_id"
                )
            out[header.header_receipt_id] = header
        return out
    out = {}
    for header in validated_headers:
        if header.header_receipt_id in out:
            raise PairEventV2Error(
                f"duplicate header_receipt_id in validated headers: "
                f"{header.header_receipt_id}"
            )
        out[header.header_receipt_id] = header
    return out


def verify_leaf_header_dependencies(
    receipt: LeafReceiptRecord,
    *,
    validated_headers: Mapping[str, CanonicalHeaderReceiptRecord],
) -> None:
    """Require every chdr_ dependency exists and matches plan/providers/boundary."""
    if not receipt.canonical_header_receipt_ids:
        raise PairEventV2Error("leaf has empty canonical header dependencies")
    seen_boundary = False
    for header_id in receipt.canonical_header_receipt_ids:
        header = validated_headers.get(header_id)
        if header is None:
            raise PairEventV2Error(
                f"leaf references missing canonical header receipt {header_id}"
            )
        if header.plan_id != receipt.plan_id:
            raise PairEventV2Error(
                "canonical header plan_id does not match leaf plan_id"
            )
        if header.primary_provider_org != receipt.primary_provider_org:
            raise PairEventV2Error(
                "canonical header primary provider_org does not match leaf"
            )
        if header.secondary_provider_org != receipt.secondary_provider_org:
            raise PairEventV2Error(
                "canonical header secondary provider_org does not match leaf"
            )
        if header.block_number == receipt.end_block:
            seen_boundary = True
    if not seen_boundary:
        raise PairEventV2Error(
            "leaf header dependencies must include the end-block boundary header"
        )


def _sorted_receipts(
    validated_receipts: Mapping[str, LeafReceiptRecord] | Sequence[LeafReceiptRecord],
    *,
    plan_id: str,
    validated_headers: Mapping[str, CanonicalHeaderReceiptRecord]
    | Sequence[CanonicalHeaderReceiptRecord],
) -> list[LeafReceiptRecord]:
    """Deterministic receipt order + header-map authority checks."""
    plan = _require_plan_id(plan_id)
    headers = _header_map(validated_headers)
    receipts = list(_receipt_map(validated_receipts).values())
    for receipt in receipts:
        if receipt.plan_id != plan:
            raise PairEventV2Error("receipt plan_id does not match coverage plan_id")
        verify_leaf_header_dependencies(receipt, validated_headers=headers)
    # Non-decreasing start for O(1) cursor merge; tie-break by end then id.
    receipts.sort(
        key=lambda r: (r.start_block, r.end_block, r.leaf_receipt_id)
    )
    return receipts


def prove_pool_topic_coverage(
    pool: RegistryPoolBirth,
    *,
    plan_id: str,
    topic: str,
    validated_receipts: Mapping[str, LeafReceiptRecord] | Sequence[LeafReceiptRecord],
    validated_headers: Mapping[str, CanonicalHeaderReceiptRecord]
    | Sequence[CanonicalHeaderReceiptRecord],
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> PoolTopicCoverage:
    """Prove coverage from validated leaf **and** canonical header receipts."""
    plan = _require_plan_id(plan_id)
    if topic not in ORDERED_EVENT_TOPICS:
        raise PairEventV2Error(f"unsupported topic: {topic!r}")
    expected_start, expected_end = expected_pool_topic_domain(
        pool, topic=topic, cutoff_block=cutoff_block
    )
    acc = _TopicCoverageCursor(
        expected_start=expected_start,
        expected_end=expected_end,
        prev_end=expected_start - 1,
    )
    for receipt in _sorted_receipts(
        validated_receipts, plan_id=plan, validated_headers=validated_headers
    ):
        if topic not in receipt.topics:
            continue
        if pool.pool_address not in receipt.addresses:
            continue
        clamped = birth_clamped_interval(
            creation_block=pool.creation_block,
            domain_start=receipt.start_block,
            domain_end=receipt.end_block,
            cutoff_block=cutoff_block,
        )
        if clamped is None:
            continue
        acc.add_sorted(clamped[0], clamped[1], receipt.leaf_receipt_id)
    return acc.finalize(
        plan_id=plan, pool_address=pool.pool_address, topic=topic
    )


def prove_full_registry_coverage(
    pools: Sequence[RegistryPoolBirth],
    *,
    plan_id: str,
    validated_receipts: Mapping[str, LeafReceiptRecord] | Sequence[LeafReceiptRecord],
    validated_headers: Mapping[str, CanonicalHeaderReceiptRecord]
    | Sequence[CanonicalHeaderReceiptRecord],
    topics: Sequence[str] = ORDERED_EVENT_TOPICS,
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> tuple[PoolTopicCoverage, ...]:
    """Coverage for every pool × topic with O(1) state per cell.

    Receipts are processed once in deterministic start-order. No interval lists
    or receipt-id sets are retained per membership.
    """
    plan = _require_plan_id(plan_id)
    ordered = sort_pool_births(pools, cutoff_block=cutoff_block)
    topic_list = tuple(topics)
    for topic in topic_list:
        if topic not in ORDERED_EVENT_TOPICS:
            raise PairEventV2Error(f"unsupported topic: {topic!r}")

    pool_by_addr = {p.pool_address: p for p in ordered}
    # Constant-size cursor per registry pool × topic only.
    cursors: dict[tuple[str, str], _TopicCoverageCursor] = {}
    for pool in ordered:
        for topic in topic_list:
            expected_start, expected_end = expected_pool_topic_domain(
                pool, topic=topic, cutoff_block=cutoff_block
            )
            cursors[(pool.pool_address, topic)] = _TopicCoverageCursor(
                expected_start=expected_start,
                expected_end=expected_end,
                prev_end=expected_start - 1,
            )

    for receipt in _sorted_receipts(
        validated_receipts, plan_id=plan, validated_headers=validated_headers
    ):
        for address in receipt.addresses:
            pool = pool_by_addr.get(address)
            if pool is None:
                continue
            for topic in receipt.topics:
                if topic not in topic_list:
                    continue
                acc = cursors.get((address, topic))
                if acc is None:
                    continue
                clamped = birth_clamped_interval(
                    creation_block=pool.creation_block,
                    domain_start=receipt.start_block,
                    domain_end=receipt.end_block,
                    cutoff_block=cutoff_block,
                )
                if clamped is None:
                    continue
                acc.add_sorted(clamped[0], clamped[1], receipt.leaf_receipt_id)

    reports: list[PoolTopicCoverage] = []
    for pool in ordered:
        for topic in topic_list:
            reports.append(
                cursors[(pool.pool_address, topic)].finalize(
                    plan_id=plan,
                    pool_address=pool.pool_address,
                    topic=topic,
                )
            )
    return tuple(reports)


# ---------------------------------------------------------------------------
# Persistence records (schema only — later lease/receipt/header engine)
# ---------------------------------------------------------------------------


class PersistenceRecordKind(StrEnum):
    PLAN = "plan"
    QUERY_NODE = "query_node"
    QUERY_LEASE = "query_lease"
    LEAF_RECEIPT = "leaf_receipt"
    CANONICAL_HEADER_RECEIPT = "canonical_header_receipt"
    COVERAGE_PRODUCT = "coverage_product"
    PROVIDER_DISAGREEMENT = "provider_disagreement"
    TRANSPORT_FAILURE = "transport_failure"


def plan_config_from_identity_payload(payload: Mapping[str, Any]) -> PlanConfig:
    """Reconstruct a validated ``PlanConfig`` from a durable identity payload."""
    if not isinstance(payload, Mapping):
        raise PairEventV2Error("plan identity payload must be an object")
    required = (
        "registry_dataset_id",
        "chain",
        "factory",
        "deployment_block",
        "cutoff_block",
        "root_block_size",
        "topics",
        "initial_cohort_size",
        "split_policy_version",
        "event_provider_orgs",
        "metadata_provider_orgs",
        "log_identity_version",
        "receipt_schema_version",
        "plan_schema_version",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise PairEventV2Error(
            f"plan identity payload missing fields: {missing}"
        )
    topics = payload["topics"]
    event_orgs = payload["event_provider_orgs"]
    meta_orgs = payload["metadata_provider_orgs"]
    if not isinstance(topics, list) or not isinstance(event_orgs, list) or not isinstance(
        meta_orgs, list
    ):
        raise PairEventV2Error("plan identity list fields must be JSON arrays")
    return PlanConfig(
        registry_dataset_id=str(payload["registry_dataset_id"]),
        chain=str(payload["chain"]),
        factory=str(payload["factory"]),
        deployment_block=int(payload["deployment_block"]),
        cutoff_block=int(payload["cutoff_block"]),
        root_block_size=int(payload["root_block_size"]),
        topics=tuple(topics),
        initial_cohort_size=int(payload["initial_cohort_size"]),
        split_policy_version=str(payload["split_policy_version"]),
        event_provider_orgs=tuple(event_orgs),
        metadata_provider_orgs=tuple(meta_orgs),
        log_identity_version=str(payload["log_identity_version"]),
        receipt_schema_version=str(payload["receipt_schema_version"]),
        plan_schema_version=str(payload["plan_schema_version"]),
    )


@dataclass(frozen=True, slots=True)
class PlanRecord:
    """Durable plan identity row — required before any leaf/header credit.

    Reconstructs ``PlanConfig`` from ``identity_payload_json`` and requires every
    duplicated column to equal that canonical payload.
    """

    plan_id: str
    registry_dataset_id: str
    identity_payload_json: str
    event_provider_orgs_json: str
    metadata_provider_orgs_json: str
    root_block_size: int
    initial_cohort_size: int
    deployment_block: int
    cutoff_block: int
    plan_schema_version: str = PLAN_SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        plan_id = _require_plan_id(self.plan_id)
        try:
            payload = json.loads(self.identity_payload_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("identity_payload_json must be JSON") from exc
        if not isinstance(payload, dict):
            raise PairEventV2Error("identity_payload_json must be an object")
        config = plan_config_from_identity_payload(payload)
        expected_id = config.plan_id()
        if expected_id != plan_id:
            raise PairEventV2Error(
                "plan_id does not match reconstructed PlanConfig identity"
            )
        # Duplicated columns must equal the canonical payload (no divergent copies).
        if self.registry_dataset_id != config.registry_dataset_id:
            raise PairEventV2Error("registry_dataset_id column disagrees with payload")
        if int(self.root_block_size) != config.root_block_size:
            raise PairEventV2Error("root_block_size column disagrees with payload")
        if int(self.initial_cohort_size) != config.initial_cohort_size:
            raise PairEventV2Error("initial_cohort_size column disagrees with payload")
        if int(self.deployment_block) != config.deployment_block:
            raise PairEventV2Error("deployment_block column disagrees with payload")
        if int(self.cutoff_block) != config.cutoff_block:
            raise PairEventV2Error("cutoff_block column disagrees with payload")
        if self.plan_schema_version != config.plan_schema_version:
            raise PairEventV2Error("plan_schema_version column disagrees with payload")
        try:
            event_orgs = json.loads(self.event_provider_orgs_json)
            meta_orgs = json.loads(self.metadata_provider_orgs_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("provider org JSON columns must be JSON") from exc
        if not isinstance(event_orgs, list) or not isinstance(meta_orgs, list):
            raise PairEventV2Error("provider org JSON columns must be arrays")
        if tuple(event_orgs) != config.event_provider_orgs:
            raise PairEventV2Error(
                "event_provider_orgs_json disagrees with identity payload"
            )
        if tuple(meta_orgs) != config.metadata_provider_orgs:
            raise PairEventV2Error(
                "metadata_provider_orgs_json disagrees with identity payload"
            )
        # Canonical payload encoding must match stored JSON (digest already equal).
        if _canonical_json(config.identity_payload()) != _canonical_json(payload):
            raise PairEventV2Error(
                "identity_payload_json is not canonical PlanConfig encoding"
            )
        object.__setattr__(self, "plan_id", plan_id)


@dataclass(frozen=True, slots=True)
class QueryNodeRecord:
    """Database-authoritative query lifecycle row (ADR-0015 §9.4)."""

    plan_id: str
    domain_id: str
    start_block: int
    end_block: int
    addresses_json: str
    topics_json: str
    status: QueryNodeStatus
    parent_domain_id: str | None = None
    split_reason: SplitReason | None = None
    attempt: int = 0
    updated_at: str = ""

    def __post_init__(self) -> None:
        plan_id = _require_plan_id(self.plan_id)
        try:
            addresses = json.loads(self.addresses_json)
            topics = json.loads(self.topics_json)
        except json.JSONDecodeError as exc:
            raise PairEventV2Error("addresses_json/topics_json must be JSON") from exc
        if not isinstance(addresses, list) or not isinstance(topics, list):
            raise PairEventV2Error("addresses_json/topics_json must be JSON arrays")
        domain = QueryDomain(
            start_block=int(self.start_block),
            end_block=int(self.end_block),
            addresses=tuple(addresses),
            topics=tuple(topics),
        )
        expected = domain.domain_id(plan_id)
        if _require_domain_id(self.domain_id) != expected:
            raise PairEventV2Error(
                "query node domain_id does not match plan_id + domain fields"
            )
        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "domain_id", expected)
        if self.parent_domain_id is not None:
            object.__setattr__(
                self, "parent_domain_id", _require_domain_id(self.parent_domain_id)
            )


@dataclass(frozen=True, slots=True)
class QueryLeaseRecord:
    """Expiring work lease for crash-safe multi-worker scheduling."""

    plan_id: str
    domain_id: str
    worker_id: str
    lease_token: str
    leased_at: str
    expires_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))
        object.__setattr__(self, "domain_id", _require_domain_id(self.domain_id))


@dataclass(frozen=True, slots=True)
class LeafReceiptRecord:
    """Terminal AGREED dual-provider log leaf with header dependencies.

    Construction recomputes ``domain_id`` and ``leaf_receipt_id`` from every
    replay-critical field (including sorted unique header dependencies). A
    forged id or missing boundary/header evidence fails closed.
    """

    leaf_receipt_id: str
    plan_id: str
    domain_id: str
    start_block: int
    end_block: int
    addresses: tuple[str, ...]
    topics: tuple[str, ...]
    primary_provider_org: str
    secondary_provider_org: str
    primary_logs_raw_object_id: str
    secondary_logs_raw_object_id: str
    primary_logs_acquisition_id: str
    secondary_logs_acquisition_id: str
    log_count: int
    log_identity_sha256: str
    canonical_header_receipt_ids: tuple[str, ...]
    log_identity_version: str = LOG_IDENTITY_VERSION
    receipt_schema_version: str = RECEIPT_SCHEMA_VERSION
    reconciliation_status: Literal["AGREED"] = "AGREED"
    completed_at: str = ""

    def __post_init__(self) -> None:
        if self.reconciliation_status != "AGREED":
            raise PairEventV2Error("leaf receipt must be AGREED")
        if self.log_identity_version != LOG_IDENTITY_VERSION:
            raise PairEventV2Error("leaf log_identity_version mismatch")
        if self.receipt_schema_version != RECEIPT_SCHEMA_VERSION:
            raise PairEventV2Error("leaf receipt_schema_version mismatch")
        plan_id = _require_plan_id(self.plan_id)
        domain = QueryDomain(
            start_block=int(self.start_block),
            end_block=int(self.end_block),
            addresses=tuple(self.addresses),
            topics=tuple(self.topics),
        )
        expected_domain_id = domain.domain_id(plan_id)
        if _require_domain_id(self.domain_id) != expected_domain_id:
            raise PairEventV2Error(
                "leaf domain_id does not match plan_id + domain fields"
            )
        headers = _normalize_header_dependency_ids(self.canonical_header_receipt_ids)
        expected_leaf_id = compute_leaf_receipt_id(
            plan_id=plan_id,
            domain_id=expected_domain_id,
            start_block=domain.start_block,
            end_block=domain.end_block,
            addresses=domain.addresses,
            topics=domain.topics,
            log_identity_sha256=self.log_identity_sha256,
            primary_provider_org=self.primary_provider_org,
            secondary_provider_org=self.secondary_provider_org,
            primary_logs_raw_object_id=self.primary_logs_raw_object_id,
            secondary_logs_raw_object_id=self.secondary_logs_raw_object_id,
            primary_logs_acquisition_id=self.primary_logs_acquisition_id,
            secondary_logs_acquisition_id=self.secondary_logs_acquisition_id,
            log_count=self.log_count,
            canonical_header_receipt_ids=headers,
        )
        if _require_leaf_receipt_id(self.leaf_receipt_id) != expected_leaf_id:
            raise PairEventV2Error(
                "leaf_receipt_id does not match deterministic content identity"
            )
        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "domain_id", expected_domain_id)
        object.__setattr__(self, "addresses", domain.addresses)
        object.__setattr__(self, "topics", domain.topics)
        object.__setattr__(self, "canonical_header_receipt_ids", headers)
        object.__setattr__(self, "leaf_receipt_id", expected_leaf_id)
        object.__setattr__(
            self,
            "primary_provider_org",
            normalize_provider_org(self.primary_provider_org),
        )
        object.__setattr__(
            self,
            "secondary_provider_org",
            normalize_provider_org(self.secondary_provider_org),
        )
        object.__setattr__(
            self,
            "log_identity_sha256",
            _require_sha256_hex(self.log_identity_sha256, label="log_identity_sha256"),
        )

    @property
    def addresses_json(self) -> str:
        return _canonical_json(list(self.addresses))

    @property
    def topics_json(self) -> str:
        return _canonical_json(list(self.topics))

    @property
    def canonical_header_receipt_ids_json(self) -> str:
        return _canonical_json(list(self.canonical_header_receipt_ids))


@dataclass(frozen=True, slots=True)
class CanonicalHeaderReceiptRecord:
    """One dual-agreed block header shared across leaves (ADR-0015 §9.5)."""

    header_receipt_id: str
    plan_id: str
    block_number: int
    block_hash: str
    block_timestamp: int
    primary_provider_org: str
    secondary_provider_org: str
    primary_raw_object_id: str
    secondary_raw_object_id: str
    primary_acquisition_id: str
    secondary_acquisition_id: str
    receipt_schema_version: str = RECEIPT_SCHEMA_VERSION
    completed_at: str = ""

    def __post_init__(self) -> None:
        if self.receipt_schema_version != RECEIPT_SCHEMA_VERSION:
            raise PairEventV2Error("header receipt_schema_version mismatch")
        expected = compute_canonical_header_receipt_id(
            plan_id=self.plan_id,
            block_number=self.block_number,
            block_hash=self.block_hash,
            block_timestamp=self.block_timestamp,
            primary_provider_org=self.primary_provider_org,
            secondary_provider_org=self.secondary_provider_org,
            primary_raw_object_id=self.primary_raw_object_id,
            secondary_raw_object_id=self.secondary_raw_object_id,
            primary_acquisition_id=self.primary_acquisition_id,
            secondary_acquisition_id=self.secondary_acquisition_id,
        )
        if not isinstance(self.header_receipt_id, str) or not _HEADER_ID_RE.fullmatch(
            self.header_receipt_id
        ):
            raise PairEventV2Error("header_receipt_id must be chdr_<64 hex>")
        if self.header_receipt_id != expected:
            raise PairEventV2Error(
                "header_receipt_id does not match deterministic content identity"
            )
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))
        object.__setattr__(
            self,
            "primary_provider_org",
            normalize_provider_org(self.primary_provider_org),
        )
        object.__setattr__(
            self,
            "secondary_provider_org",
            normalize_provider_org(self.secondary_provider_org),
        )


@dataclass(frozen=True, slots=True)
class CoverageProductRecord:
    """Durable per-pool/topic coverage summary for publication gates."""

    plan_id: str
    pool_address: str
    topic: str
    expected_start: int
    expected_end: int
    expected_block_count: int
    covered_block_count: int
    first_covered_block: int | None
    last_covered_block: int | None
    leaf_count: int
    has_gap: bool
    has_overlap: bool
    supporting_receipts_root: str
    coverage_hash: str
    is_complete: bool
    schema_version: str = COVERAGE_SCHEMA_VERSION


def plan_record_from_config(config: PlanConfig, *, created_at: str = "") -> PlanRecord:
    return PlanRecord(
        plan_id=config.plan_id(),
        registry_dataset_id=config.registry_dataset_id,
        identity_payload_json=_canonical_json(config.identity_payload()),
        event_provider_orgs_json=_canonical_json(list(config.event_provider_orgs)),
        metadata_provider_orgs_json=_canonical_json(list(config.metadata_provider_orgs)),
        root_block_size=config.root_block_size,
        initial_cohort_size=config.initial_cohort_size,
        deployment_block=config.deployment_block,
        cutoff_block=config.cutoff_block,
        created_at=created_at,
    )


def query_node_record_from_node(node: QueryNode, *, updated_at: str = "") -> QueryNodeRecord:
    return QueryNodeRecord(
        plan_id=node.plan_id,
        domain_id=node.domain_id,
        start_block=node.domain.start_block,
        end_block=node.domain.end_block,
        addresses_json=_canonical_json(list(node.domain.addresses)),
        topics_json=_canonical_json(list(node.domain.topics)),
        status=node.status,
        parent_domain_id=node.parent_domain_id,
        split_reason=node.split_reason,
        updated_at=updated_at,
    )


def make_leaf_receipt_record(
    *,
    plan_id: str,
    domain: QueryDomain,
    log_identity_sha256: str,
    primary_provider_org: str,
    secondary_provider_org: str,
    primary_logs_raw_object_id: str,
    secondary_logs_raw_object_id: str,
    primary_logs_acquisition_id: str,
    secondary_logs_acquisition_id: str,
    log_count: int,
    canonical_header_receipt_ids: Sequence[str],
    completed_at: str = "",
) -> LeafReceiptRecord:
    """Build a fully-validated leaf receipt with recomputed identities."""
    plan = _require_plan_id(plan_id)
    domain_id = domain.domain_id(plan)
    leaf_id = compute_leaf_receipt_id(
        plan_id=plan,
        domain_id=domain_id,
        start_block=domain.start_block,
        end_block=domain.end_block,
        addresses=domain.addresses,
        topics=domain.topics,
        log_identity_sha256=log_identity_sha256,
        primary_provider_org=primary_provider_org,
        secondary_provider_org=secondary_provider_org,
        primary_logs_raw_object_id=primary_logs_raw_object_id,
        secondary_logs_raw_object_id=secondary_logs_raw_object_id,
        primary_logs_acquisition_id=primary_logs_acquisition_id,
        secondary_logs_acquisition_id=secondary_logs_acquisition_id,
        log_count=log_count,
        canonical_header_receipt_ids=canonical_header_receipt_ids,
    )
    return LeafReceiptRecord(
        leaf_receipt_id=leaf_id,
        plan_id=plan,
        domain_id=domain_id,
        start_block=domain.start_block,
        end_block=domain.end_block,
        addresses=domain.addresses,
        topics=domain.topics,
        primary_provider_org=primary_provider_org,
        secondary_provider_org=secondary_provider_org,
        primary_logs_raw_object_id=primary_logs_raw_object_id,
        secondary_logs_raw_object_id=secondary_logs_raw_object_id,
        primary_logs_acquisition_id=primary_logs_acquisition_id,
        secondary_logs_acquisition_id=secondary_logs_acquisition_id,
        log_count=log_count,
        log_identity_sha256=log_identity_sha256,
        canonical_header_receipt_ids=tuple(canonical_header_receipt_ids),
        completed_at=completed_at,
    )


def coverage_product_record(report: PoolTopicCoverage) -> CoverageProductRecord:
    return CoverageProductRecord(
        plan_id=report.plan_id,
        pool_address=report.pool_address,
        topic=report.topic,
        expected_start=report.expected_start,
        expected_end=report.expected_end,
        expected_block_count=report.expected_block_count,
        covered_block_count=report.covered_block_count,
        first_covered_block=report.first_covered_block,
        last_covered_block=report.last_covered_block,
        leaf_count=report.leaf_count,
        has_gap=report.has_gap,
        has_overlap=report.has_overlap,
        supporting_receipts_root=report.supporting_receipts_root,
        coverage_hash=report.coverage_hash,
        is_complete=report.is_complete,
    )


# ---------------------------------------------------------------------------
# ADR-0015 §9.10 production foundation (offline pure)
# ---------------------------------------------------------------------------


def production_plan_config() -> PlanConfig:
    """Authoritative production PlanConfig: cohort 8, pinned registry, dual event orgs."""
    return PlanConfig(initial_cohort_size=PRODUCTION_INITIAL_COHORT_SIZE)


def root_pool_topic_blocks(
    *,
    addresses: Sequence[str],
    root_start: int,
    root_end: int,
    births: Mapping[str, int],
    cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK,
) -> int:
    """Birth-clamped pool×topic×block count for one root domain (integer PTB)."""
    total = 0
    for address in addresses:
        creation = births[normalize_address(address)]
        for _topic in ORDERED_EVENT_TOPICS:
            clamped = birth_clamped_interval(
                creation_block=creation,
                domain_start=root_start,
                domain_end=root_end,
                cutoff_block=cutoff_block,
            )
            if clamped is not None:
                total += clamped[1] - clamped[0] + 1
    return total


def iter_production_root_filters(
    pools: Sequence[RegistryPoolBirth],
    *,
    config: PlanConfig | None = None,
    batch_size: int = 256,
):
    """Yield production root filters in construction order without materializing all.

    Caller may process one root at a time. Does not allocate the full root list.
    ``batch_size`` is reserved for future batching hints and must be positive.
    """
    if batch_size <= 0:
        raise PairEventV2Error("batch_size must be positive")
    cfg = config if config is not None else production_plan_config()
    if cfg.initial_cohort_size != PRODUCTION_INITIAL_COHORT_SIZE:
        raise PairEventV2Error(
            "production root iterator requires initial_cohort_size=8"
        )
    if cfg.plan_id() != PRODUCTION_PLAN_ID:
        raise PairEventV2Error(
            "production root iterator requires the pinned production plan identity"
        )
    ordered = sort_pool_births(pools, cutoff_block=cfg.cutoff_block)
    if not ordered:
        raise PairEventV2Error("registry slice is empty")
    plan_id = cfg.plan_id()
    for root_start, root_end in iter_root_windows(
        deployment_block=cfg.deployment_block,
        cutoff_block=cfg.cutoff_block,
        root_block_size=cfg.root_block_size,
    ):
        addresses = tuple(
            pool.pool_address for pool in ordered if pool.creation_block <= root_end
        )
        if not addresses:
            continue
        cohorts = partition_address_cohorts(
            addresses, cohort_size=cfg.initial_cohort_size
        )
        for cohort_index, cohort in enumerate(cohorts):
            domain = QueryDomain(
                start_block=root_start,
                end_block=root_end,
                addresses=cohort,
                topics=cfg.topics,
            )
            yield RootFilterPlan(
                plan_id=plan_id,
                root_start=root_start,
                root_end=root_end,
                cohort_index=cohort_index,
                domain=domain,
            )


def _external_sort_hash_domain_ids(domain_id_path: str, *, chunk_size: int = 50_000) -> str:
    """SHA-256 over lexicographically sorted domain_id lines (each + LF).

    Uses chunked on-disk sort so peak memory stays O(chunk_size), not O(root_count).
    """
    import heapq
    import os
    import tempfile

    chunk_paths: list[str] = []
    buf: list[str] = []
    try:
        with open(domain_id_path, encoding="ascii") as source:
            for line in source:
                domain_id = line.rstrip("\n")
                if not domain_id:
                    continue
                buf.append(domain_id)
                if len(buf) >= chunk_size:
                    buf.sort()
                    fd, path = tempfile.mkstemp(prefix="cmb_dom_")
                    with os.fdopen(fd, "w", encoding="ascii") as out:
                        out.write("\n".join(buf))
                        out.write("\n")
                    chunk_paths.append(path)
                    buf.clear()
        if buf:
            buf.sort()
            fd, path = tempfile.mkstemp(prefix="cmb_dom_")
            with os.fdopen(fd, "w", encoding="ascii") as out:
                out.write("\n".join(buf))
                out.write("\n")
            chunk_paths.append(path)
            buf.clear()
        hasher = hashlib.sha256()
        if not chunk_paths:
            return hasher.hexdigest()
        files = [open(path, encoding="ascii") for path in chunk_paths]
        try:
            for domain_id in heapq.merge(*(f for f in files)):
                domain_id = domain_id.rstrip("\n")
                if not domain_id:
                    continue
                hasher.update(domain_id.encode("ascii"))
                hasher.update(b"\n")
        finally:
            for f in files:
                f.close()
        return hasher.hexdigest()
    finally:
        for path in chunk_paths:
            try:
                os.unlink(path)
            except OSError:
                pass


def compute_production_root_anchors(
    pools: Sequence[RegistryPoolBirth],
    *,
    config: PlanConfig | None = None,
    domain_id_chunk_size: int = 50_000,
) -> dict[str, Any]:
    """Stream roots once; return count, PTB total, and domain-set SHA-256.

    Domain-set digest = SHA-256 over lexicographically ordered domain_id ASCII
    values each followed by a single LF (ADR-0015 §9.10). Domain IDs are spilled
    to a temp file and externally sorted so peak memory is O(chunk), not O(roots).
    """
    import os
    import tempfile

    cfg = config if config is not None else production_plan_config()
    ordered = sort_pool_births(pools, cutoff_block=cfg.cutoff_block)
    births = {p.pool_address: p.creation_block for p in ordered}
    root_count = 0
    pool_topic_blocks = 0
    fd, domain_path = tempfile.mkstemp(prefix="cmb_prod_dom_")
    try:
        with os.fdopen(fd, "w", encoding="ascii") as domain_file:
            for root in iter_production_root_filters(ordered, config=cfg):
                root_count += 1
                domain_file.write(root.domain_id)
                domain_file.write("\n")
                pool_topic_blocks += root_pool_topic_blocks(
                    addresses=root.domain.addresses,
                    root_start=root.root_start,
                    root_end=root.root_end,
                    births=births,
                    cutoff_block=cfg.cutoff_block,
                )
        digest = _external_sort_hash_domain_ids(
            domain_path, chunk_size=domain_id_chunk_size
        )
    finally:
        try:
            os.unlink(domain_path)
        except OSError:
            pass
    return {
        "plan_id": cfg.plan_id(),
        "root_count": root_count,
        "pool_topic_blocks": pool_topic_blocks,
        "root_domain_set_sha256": digest,
    }


def verify_production_root_anchors(anchors: Mapping[str, Any]) -> None:
    """Fail closed unless anchors match the pinned ADR-0015 §9.10 values."""
    if str(anchors.get("plan_id")) != PRODUCTION_PLAN_ID:
        raise PairEventV2Error("production plan_id anchor mismatch")
    if int(anchors.get("root_count", -1)) != PRODUCTION_ROOT_COUNT:
        raise PairEventV2Error("production root_count anchor mismatch")
    if int(anchors.get("pool_topic_blocks", -1)) != PRODUCTION_POOL_TOPIC_BLOCKS:
        raise PairEventV2Error("production pool_topic_blocks anchor mismatch")
    if str(anchors.get("root_domain_set_sha256")) != PRODUCTION_ROOT_DOMAIN_SET_SHA256:
        raise PairEventV2Error("production root_domain_set_sha256 anchor mismatch")


def required_blocks_from_identities(
    identities: Sequence[LogIdentityV2],
    *,
    domain: QueryDomain,
) -> tuple[tuple[int, str | None, bool], ...]:
    """Normalized required blocks for a reconciled log set.

    Returns (block_number, expected_hash|None, is_boundary). Event blocks carry
    expected hash from the log; the domain end boundary is always required and is
    boundary-only when no log occupies that block (expected hash then nullable).
    """
    by_block: dict[int, str] = {}
    for identity in identities:
        existing = by_block.get(identity.block_number)
        if existing is not None and existing != identity.block_hash:
            raise PairEventV2Error("conflicting log block hashes in identity set")
        by_block[identity.block_number] = identity.block_hash
    rows: list[tuple[int, str | None, bool]] = []
    for block_number in sorted(set(by_block) | {domain.end_block}):
        expected = by_block.get(block_number)
        is_boundary = block_number == domain.end_block and expected is None
        if block_number == domain.end_block and expected is not None:
            is_boundary = True  # end block also present as event block
        if expected is None and block_number != domain.end_block:
            raise PairEventV2Error("non-boundary required block missing expected hash")
        # Boundary-only: is_boundary True, expected None.
        # End block with events: is_boundary True, expected set.
        # Interior event blocks: is_boundary False, expected set.
        if block_number != domain.end_block:
            is_boundary = False
        rows.append((block_number, expected, is_boundary or block_number == domain.end_block))
    # Re-normalize is_boundary: True iff block_number == domain.end_block
    normalized = tuple(
        (bn, exp, bn == domain.end_block) for bn, exp, _ in rows
    )
    return normalized


def compute_log_candidate_id(
    *,
    plan_id: str,
    domain_id: str,
    attempt: int,
    log_identity_sha256: str,
    primary_logs_raw_object_id: str,
    secondary_logs_raw_object_id: str,
    primary_logs_acquisition_id: str,
    secondary_logs_acquisition_id: str,
) -> str:
    """Deterministic candidate id bound to dual log raw authority."""
    payload = {
        "attempt": int(attempt),
        "domain_id": _require_domain_id(domain_id),
        "log_identity_sha256": _require_sha256_hex(
            log_identity_sha256, label="log_identity_sha256"
        ),
        "plan_id": _require_plan_id(plan_id),
        "primary_logs_acquisition_id": primary_logs_acquisition_id,
        "primary_logs_raw_object_id": _require_raw_object_id(
            primary_logs_raw_object_id, label="primary_logs_raw_object_id"
        ),
        "secondary_logs_acquisition_id": secondary_logs_acquisition_id,
        "secondary_logs_raw_object_id": _require_raw_object_id(
            secondary_logs_raw_object_id, label="secondary_logs_raw_object_id"
        ),
    }
    return "lcand_" + _canonical_digest(payload)


@dataclass(frozen=True, slots=True)
class RootManifestRecord:
    """Durable production root-manifest authority (migration 0020)."""

    plan_id: str
    registry_dataset_id: str
    registry_parquet_sha256: str
    registry_parquet_bytes: int
    root_count: int
    root_domain_set_sha256: str
    pool_topic_blocks: int
    status: Literal["INITIALIZING", "READY"]
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _require_plan_id(self.plan_id))
        if self.registry_dataset_id != ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID:
            raise PairEventV2Error("root manifest registry_dataset_id is not accepted")
        if not _SHA256_RE.fullmatch(self.registry_parquet_sha256):
            raise PairEventV2Error("registry_parquet_sha256 must be 64 hex")
        if self.registry_parquet_bytes <= 0:
            raise PairEventV2Error("registry_parquet_bytes must be positive")
        if self.root_count <= 0:
            raise PairEventV2Error("root_count must be positive")
        if not _SHA256_RE.fullmatch(self.root_domain_set_sha256):
            raise PairEventV2Error("root_domain_set_sha256 must be 64 hex")
        if self.pool_topic_blocks <= 0:
            raise PairEventV2Error("pool_topic_blocks must be positive")
        if self.status not in ("INITIALIZING", "READY"):
            raise PairEventV2Error("root manifest status must be INITIALIZING or READY")


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


__all__ = [
    "ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID",
    "AcquisitionPlanV2",
    "CANDIDATE_COHORT_SIZES",
    "CLAIM_ORDER_VERSION_CHRONOLOGICAL_V1",
    "CLAIM_ORDER_VERSION_DOMAIN_HASH_V1",
    "COVERAGE_SCHEMA_VERSION",
    "CanonicalHeaderReceiptRecord",
    "CoverageProductRecord",
    "DEFAULT_EVENT_PROVIDER_ORGS",
    "DEFAULT_INITIAL_COHORT_SIZE",
    "DEFAULT_METADATA_PROVIDER_ORGS",
    "LOG_IDENTITY_VERSION",
    "LeafReceiptRecord",
    "LogIdentityV2",
    "ORDERED_EVENT_TOPICS",
    "PINNED_FINALITY_CUTOFF_BLOCK",
    "PLAN_SCHEMA_VERSION",
    "PRODUCTION_INITIAL_COHORT_SIZE",
    "PRODUCTION_PLAN_ID",
    "PRODUCTION_POOL_TOPIC_BLOCKS",
    "PRODUCTION_REGISTRY_PARQUET_BYTES",
    "PRODUCTION_REGISTRY_PARQUET_SHA256",
    "PRODUCTION_ROOT_COUNT",
    "PRODUCTION_ROOT_DOMAIN_SET_SHA256",
    "PersistenceRecordKind",
    "PairEventV2Error",
    "PlanConfig",
    "PlanRecord",
    "PoolTopicCoverage",
    "QueryDomain",
    "QueryLeaseRecord",
    "QueryNode",
    "QueryNodeRecord",
    "QueryNodeStatus",
    "RECEIPT_SCHEMA_VERSION",
    "ROOT_BLOCK_SIZE",
    "RegistryPoolBirth",
    "RootFilterPlan",
    "RootManifestRecord",
    "SPLIT_POLICY_VERSION",
    "SplitReason",
    "birth_clamped_interval",
    "build_acquisition_plan_v2",
    "choose_split",
    "combined_pair_logs_request",
    "compute_canonical_header_receipt_id",
    "compute_leaf_receipt_id",
    "compute_log_candidate_id",
    "compute_production_root_anchors",
    "coverage_product_record",
    "eligible_pools_for_root",
    "expected_pool_topic_domain",
    "extract_log_identity_v2",
    "iter_production_root_filters",
    "iter_root_windows",
    "log_identity_v2_digest",
    "make_leaf_receipt_record",
    "normalize_address",
    "normalize_and_index_logs",
    "normalize_provider_org",
    "partition_address_cohorts",
    "plan_config_from_identity_payload",
    "plan_record_from_config",
    "production_plan_config",
    "prove_full_registry_coverage",
    "prove_pool_topic_coverage",
    "query_node_record_from_node",
    "reconcile_log_sets_v2",
    "request_for_domain",
    "required_blocks_from_identities",
    "root_pool_topic_blocks",
    "sort_pool_births",
    "split_domain_by_address",
    "split_domain_by_block",
    "split_node",
    "validate_children_partition",
    "validate_event_shape",
    "validate_log_against_domain",
    "verify_leaf_header_dependencies",
    "verify_production_root_anchors",
    "EMPTY_SUPPORTING_RECEIPTS_ROOT",
]
