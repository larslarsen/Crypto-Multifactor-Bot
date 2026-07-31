"""DEX-003 production orchestration for Uniswap V2 pair-event acquisition.

Consumes the accepted ``dex_pool_registry`` and deterministically schedules
dual-provider Swap/Sync (and token-decimal) work for every registry pool from
birth through the pinned finality cutoff. Execution delegates entirely to
``UniswapV2PairEventIngestor`` — this module does not reimplement dual-RPC
reconciliation, receipt binding, or replay.

Runtime configuration supplies RPC URLs and optional pilot bounds. Planning,
coverage inspection, and resume accounting are offline (receipt/raw store only).
Network contact occurs only when ``run()`` invokes the injected ingestor.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

import pyarrow.parquet as pq

from cryptofactors.acquisition.uniswap_v2 import (
    ETHEREUM_CHAIN,
    UNISWAP_V2_DEPLOYMENT_BLOCK,
    UniswapV2IngestionError,
)
from cryptofactors.acquisition.uniswap_v2_pair_events import (
    EventKind,
    RECEIPT_TABLE,
    TokenDecimalsRow,
    UniswapV2PairEventIngestor,
    topic_for_kind,
)
from cryptofactors.catalog.dataset.models import DatasetManifest, QualityStatus
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.catalog.dataset.parse import load_manifest_file
from cryptofactors.catalog.dataset.paths import dataset_absolute_dir

# ---------------------------------------------------------------------------
# Pinned production identity
# ---------------------------------------------------------------------------

PINNED_FINALITY_CUTOFF_BLOCK: Final[int] = 25_600_000

# Accepted corrected registry (CURRENT_TASK / catalog SUPERSEDED predecessor).
ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID: Final[str] = (
    "ds_42ce2515e226258557a06a374498547393bbc984db791c56fa19d81d7ef16d15"
)

# Registry product identity (mirrors market.dex_pool_registry; no market import —
# acquisition may not depend on market per layer matrix).
DEX_POOL_REGISTRY_DATASET_TYPE: Final[str] = "dex_pool_registry"
DEX_POOL_REGISTRY_SCHEMA_NAME: Final[str] = "dex_pool_registry"
DEX_POOL_REGISTRY_SCHEMA_VERSION: Final[str] = "1"
DEX_POOL_REGISTRY_RELATIVE_PATH: Final[str] = "dex/dex_pool_registry/pools.parquet"

DEFAULT_EVENT_CHUNK_SIZE: Final[int] = 10_000
DEFAULT_EVENT_KINDS: Final[tuple[EventKind, ...]] = ("swap", "sync")

_ADDRESS_LEN = 42
_REQUIRED_REGISTRY_COLUMNS: Final[tuple[str, ...]] = (
    "pool_address",
    "token0",
    "token1",
    "base_token",
    "quote_token",
    "quote_symbol",
    "creation_block",
    "chain",
    "protocol",
    "factory",
)


class PairEventOrchestrationError(RuntimeError):
    """Fail-closed orchestration errors (planning / resume / config)."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


# ---------------------------------------------------------------------------
# Work items / plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistryPoolRef:
    """One registry pool the orchestrator may schedule."""

    pool_address: str
    token0: str
    token1: str
    base_token: str
    quote_token: str
    quote_symbol: str
    creation_block: int


@dataclass(frozen=True, slots=True)
class EventAcquisitionJob:
    """One Swap or Sync contiguous acquisition range for a pool.

    The range is always a contiguous ``[start_block, end_block]`` that the
    ingestor will chunk. Resume is handled inside ``fetch`` via receipts.
    """

    pool_address: str
    kind: EventKind
    start_block: int
    end_block: int
    creation_block: int
    chunk_size: int

    @property
    def topic(self) -> str:
        return topic_for_kind(self.kind)

    @property
    def planned_chunk_count(self) -> int:
        return len(list(iter_chunk_ranges(self.start_block, self.end_block, self.chunk_size)))


@dataclass(frozen=True, slots=True)
class TokenDecimalsJob:
    """Dual-provider decimals() call for one token at a historical block."""

    token: str
    block_number: int


@dataclass(frozen=True, slots=True)
class AcquisitionPlan:
    """Deterministic full work plan for a registry slice."""

    registry_dataset_id: str
    finality_cutoff_block: int
    chunk_size: int
    pools: tuple[RegistryPoolRef, ...]
    event_jobs: tuple[EventAcquisitionJob, ...]
    decimals_jobs: tuple[TokenDecimalsJob, ...]
    pilot_bounds: Mapping[str, Any]

    @property
    def pool_count(self) -> int:
        return len(self.pools)

    @property
    def event_job_count(self) -> int:
        return len(self.event_jobs)

    @property
    def planned_chunk_count(self) -> int:
        return sum(job.planned_chunk_count for job in self.event_jobs)


@dataclass(frozen=True, slots=True)
class ChunkCoverage:
    pool_address: str
    kind: EventKind
    start_block: int
    end_block: int
    complete: bool


@dataclass(frozen=True, slots=True)
class JobCoverage:
    job: EventAcquisitionJob
    completed_chunks: tuple[tuple[int, int], ...]
    pending_chunks: tuple[tuple[int, int], ...]

    @property
    def is_complete(self) -> bool:
        return not self.pending_chunks

    @property
    def completed_chunk_count(self) -> int:
        return len(self.completed_chunks)

    @property
    def pending_chunk_count(self) -> int:
        return len(self.pending_chunks)


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Receipt-store coverage for a plan (offline; no network)."""

    plan: AcquisitionPlan
    jobs: tuple[JobCoverage, ...]

    @property
    def complete_job_count(self) -> int:
        return sum(1 for job in self.jobs if job.is_complete)

    @property
    def pending_job_count(self) -> int:
        return sum(1 for job in self.jobs if not job.is_complete)

    @property
    def completed_chunk_count(self) -> int:
        return sum(job.completed_chunk_count for job in self.jobs)

    @property
    def pending_chunk_count(self) -> int:
        return sum(job.pending_chunk_count for job in self.jobs)


@dataclass(frozen=True, slots=True)
class EventJobResult:
    job: EventAcquisitionJob
    status: Literal["completed", "skipped_complete", "failed"]
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class DecimalsJobResult:
    job: TokenDecimalsJob
    status: Literal["completed", "failed"]
    row: TokenDecimalsRow | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    plan: AcquisitionPlan
    coverage_before: CoverageReport
    event_results: tuple[EventJobResult, ...]
    decimals_results: tuple[DecimalsJobResult, ...]
    dry_run: bool

    @property
    def failed(self) -> bool:
        return any(r.status == "failed" for r in self.event_results) or any(
            r.status == "failed" for r in self.decimals_results
        )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PairEventOrchestratorConfig:
    """Runtime orchestration config. Provider URLs stay out of source control.

    Pilot bounds limit work at runtime without changing production chunk
    identity. ``max_chunks_per_pool`` and/or ``max_end_block`` select an exact
    *prefix* of the production chunk tiling from each pool's birth through
    ``finality_cutoff_block`` — never a shortened tail chunk — so pilot
    receipts remain reusable when the range expands to the full cutoff.
    """

    registry_store_root: Path
    receipt_db_path: Path
    raw_root: Path
    primary_rpc_url: str
    secondary_rpc_url: str
    registry_dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID
    require_accepted_registry: bool = True
    primary_provider_id: str = "rpc_primary"
    secondary_provider_id: str = "rpc_secondary"
    finality_cutoff_block: int = PINNED_FINALITY_CUTOFF_BLOCK
    chunk_size: int = DEFAULT_EVENT_CHUNK_SIZE
    event_kinds: tuple[EventKind, ...] = DEFAULT_EVENT_KINDS
    acquire_token_decimals: bool = True
    emit_rows: bool = False
    # Pilot / bounded runtime limits (None = unrestricted production).
    max_pools: int | None = None
    pool_offset: int = 0
    max_chunks_per_pool: int | None = None
    max_end_block: int | None = None
    pool_allowlist: frozenset[str] | None = None
    # Header transport knobs forwarded to the ingestor.
    header_batch_size: int = 64
    header_max_in_flight: int = 4
    header_requests_per_second: float = 20.0
    use_header_batches: bool = True

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise PairEventOrchestrationError("chunk_size must be positive")
        if self.finality_cutoff_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventOrchestrationError(
                "finality_cutoff_block precedes Uniswap V2 deployment",
                context={"finality_cutoff_block": self.finality_cutoff_block},
            )
        if self.pool_offset < 0:
            raise PairEventOrchestrationError("pool_offset must be >= 0")
        if self.max_pools is not None and self.max_pools <= 0:
            raise PairEventOrchestrationError("max_pools must be positive when set")
        if self.max_chunks_per_pool is not None and self.max_chunks_per_pool <= 0:
            raise PairEventOrchestrationError(
                "max_chunks_per_pool must be positive when set"
            )
        if self.max_end_block is not None and self.max_end_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventOrchestrationError(
                "max_end_block precedes Uniswap V2 deployment",
                context={"max_end_block": self.max_end_block},
            )
        if not self.event_kinds:
            raise PairEventOrchestrationError("event_kinds must be non-empty")
        for kind in self.event_kinds:
            if kind not in ("swap", "sync"):
                raise PairEventOrchestrationError(
                    f"unsupported event kind: {kind!r}",
                    context={"event_kinds": self.event_kinds},
                )
        # Deterministic kind order: reject duplicates.
        if len(set(self.event_kinds)) != len(self.event_kinds):
            raise PairEventOrchestrationError(
                "event_kinds must not contain duplicates",
                context={"event_kinds": self.event_kinds},
            )
        if not self.primary_rpc_url or not self.secondary_rpc_url:
            raise PairEventOrchestrationError(
                "primary_rpc_url and secondary_rpc_url are required at runtime"
            )
        if self.primary_rpc_url.rstrip("/") == self.secondary_rpc_url.rstrip("/"):
            raise PairEventOrchestrationError(
                "primary and secondary RPC URLs must be distinct"
            )
        if self.primary_provider_id == self.secondary_provider_id:
            raise PairEventOrchestrationError(
                "primary and secondary provider ids must differ"
            )

    def pilot_bounds_dict(self) -> dict[str, Any]:
        return {
            "max_pools": self.max_pools,
            "pool_offset": self.pool_offset,
            "max_chunks_per_pool": self.max_chunks_per_pool,
            "max_end_block": self.max_end_block,
            "pool_allowlist": (
                sorted(self.pool_allowlist) if self.pool_allowlist is not None else None
            ),
            "event_kinds": list(self.event_kinds),
            "chunk_size": self.chunk_size,
            "finality_cutoff_block": self.finality_cutoff_block,
            "acquire_token_decimals": self.acquire_token_decimals,
            "require_accepted_registry": self.require_accepted_registry,
            "pilot_tiling": "exact_prefix_of_production_chunks",
        }

    def production_aligned_end_block(self, creation_block: int) -> int | None:
        """End block of the exact production-chunk prefix for one pool (or None)."""
        return production_aligned_end_block(
            creation_block=creation_block,
            finality_cutoff_block=self.finality_cutoff_block,
            chunk_size=self.chunk_size,
            max_chunks=self.max_chunks_per_pool,
            max_end_block=self.max_end_block,
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def normalize_pool_address(value: object, *, label: str = "pool_address") -> str:
    if not isinstance(value, str):
        raise PairEventOrchestrationError(
            f"{label} must be a 20-byte 0x address",
            context={"value": value},
        )
    text = value.strip().lower()
    if not text.startswith("0x") or len(text) != _ADDRESS_LEN:
        raise PairEventOrchestrationError(
            f"{label} must be a 20-byte 0x address",
            context={"value": value},
        )
    # Require hex body after case fold.
    body = text[2:]
    if any(c not in "0123456789abcdef" for c in body):
        raise PairEventOrchestrationError(
            f"{label} must be a 20-byte 0x address",
            context={"value": value},
        )
    return text


def iter_chunk_ranges(
    start_block: int,
    end_block: int,
    chunk_size: int,
) -> list[tuple[int, int]]:
    """Return the exact chunk tiling ``fetch`` will walk for a range."""
    if chunk_size <= 0:
        raise PairEventOrchestrationError("chunk_size must be positive")
    if end_block < start_block:
        raise PairEventOrchestrationError(
            "end_block precedes start_block",
            context={"start_block": start_block, "end_block": end_block},
        )
    ranges: list[tuple[int, int]] = []
    for chunk_start in range(start_block, end_block + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, end_block)
        ranges.append((chunk_start, chunk_end))
    return ranges


def production_chunk_ranges(
    *,
    creation_block: int,
    finality_cutoff_block: int,
    chunk_size: int,
) -> list[tuple[int, int]]:
    """Full production tiling from pool birth through the pinned cutoff."""
    if creation_block > finality_cutoff_block:
        return []
    return iter_chunk_ranges(creation_block, finality_cutoff_block, chunk_size)


def production_aligned_end_block(
    *,
    creation_block: int,
    finality_cutoff_block: int,
    chunk_size: int,
    max_chunks: int | None = None,
    max_end_block: int | None = None,
) -> int | None:
    """Return the end of an exact prefix of production chunks, or ``None``.

    Pilots must never invent a shortened final chunk. Only complete production
    chunks (from birth through ``finality_cutoff_block``) may be selected:

    * ``max_chunks`` keeps the first N production chunks;
    * ``max_end_block`` keeps only production chunks whose end is ``<=`` that
      bound (chunks that would extend past the bound are dropped, not truncated).

    The resulting ``[creation_block, end]`` therefore uses the same chunk
    identity as the full-range production plan, so receipts remain reusable
    when the job later expands to the full cutoff.
    """
    if max_chunks is not None and max_chunks <= 0:
        raise PairEventOrchestrationError(
            "max_chunks must be positive when set",
            context={"max_chunks": max_chunks},
        )
    production = production_chunk_ranges(
        creation_block=creation_block,
        finality_cutoff_block=finality_cutoff_block,
        chunk_size=chunk_size,
    )
    if max_end_block is not None:
        production = [rng for rng in production if rng[1] <= max_end_block]
    if max_chunks is not None:
        production = production[:max_chunks]
    if not production:
        return None
    return production[-1][1]


def load_registry_pool_refs(events_or_pools_path: Path | str) -> tuple[RegistryPoolRef, ...]:
    """Load registry pools from a published ``pools.parquet`` (offline)."""
    path = Path(events_or_pools_path)
    if not path.is_file():
        raise PairEventOrchestrationError(
            "registry pools parquet is missing",
            context={"path": str(path)},
        )
    table = pq.read_table(path)
    missing = [c for c in _REQUIRED_REGISTRY_COLUMNS if c not in table.column_names]
    if missing:
        raise PairEventOrchestrationError(
            "registry parquet missing required columns",
            context={"missing": missing, "columns": list(table.column_names)},
        )
    records = table.select(list(_REQUIRED_REGISTRY_COLUMNS)).to_pylist()
    pools: list[RegistryPoolRef] = []
    seen: set[str] = set()
    for index, raw in enumerate(records):
        chain = str(raw.get("chain", "")).strip().lower()
        if chain != ETHEREUM_CHAIN:
            raise PairEventOrchestrationError(
                "registry row chain must be ethereum",
                context={"index": index, "chain": raw.get("chain")},
            )
        pool = normalize_pool_address(raw.get("pool_address"))
        if pool in seen:
            raise PairEventOrchestrationError(
                "duplicate pool_address in registry",
                context={"pool_address": pool},
            )
        seen.add(pool)
        creation_block = int(raw["creation_block"])
        if creation_block < UNISWAP_V2_DEPLOYMENT_BLOCK:
            raise PairEventOrchestrationError(
                "creation_block precedes Uniswap V2 deployment",
                context={"pool_address": pool, "creation_block": creation_block},
            )
        pools.append(
            RegistryPoolRef(
                pool_address=pool,
                token0=normalize_pool_address(raw.get("token0"), label="token0"),
                token1=normalize_pool_address(raw.get("token1"), label="token1"),
                base_token=normalize_pool_address(raw.get("base_token"), label="base_token"),
                quote_token=normalize_pool_address(raw.get("quote_token"), label="quote_token"),
                quote_symbol=str(raw["quote_symbol"]).strip().upper(),
                creation_block=creation_block,
            )
        )
    # Registry publication already sorts by birth; re-sort for safety.
    pools.sort(key=lambda p: (p.creation_block, p.pool_address))
    return tuple(pools)


def select_pools_for_run(
    pools: Sequence[RegistryPoolRef],
    *,
    pool_offset: int = 0,
    max_pools: int | None = None,
    pool_allowlist: frozenset[str] | None = None,
) -> tuple[RegistryPoolRef, ...]:
    """Apply deterministic pilot filters without reordering the census."""
    selected = list(pools)
    if pool_allowlist is not None:
        allowed = {normalize_pool_address(a) for a in pool_allowlist}
        selected = [p for p in selected if p.pool_address in allowed]
    if pool_offset:
        selected = selected[pool_offset:]
    if max_pools is not None:
        selected = selected[:max_pools]
    return tuple(selected)


def build_event_jobs(
    pools: Sequence[RegistryPoolRef],
    *,
    finality_cutoff_block: int,
    chunk_size: int,
    event_kinds: Sequence[EventKind] = DEFAULT_EVENT_KINDS,
    max_chunks_per_pool: int | None = None,
    max_end_block: int | None = None,
) -> tuple[EventAcquisitionJob, ...]:
    """Build the deterministic Swap/Sync job list for selected pools.

    Job ranges always end on a production chunk boundary (exact prefix of the
    birth→cutoff tiling). See :func:`production_aligned_end_block`.
    """
    jobs: list[EventAcquisitionJob] = []
    for pool in pools:
        end = production_aligned_end_block(
            creation_block=pool.creation_block,
            finality_cutoff_block=finality_cutoff_block,
            chunk_size=chunk_size,
            max_chunks=max_chunks_per_pool,
            max_end_block=max_end_block,
        )
        if end is None:
            # No complete production chunk fits the pilot bounds.
            continue
        # Invariant: [creation, end] chunk tiling is a prefix of production.
        production = production_chunk_ranges(
            creation_block=pool.creation_block,
            finality_cutoff_block=finality_cutoff_block,
            chunk_size=chunk_size,
        )
        planned = iter_chunk_ranges(pool.creation_block, end, chunk_size)
        if planned != production[: len(planned)]:
            raise PairEventOrchestrationError(
                "internal pilot tiling is not a prefix of production chunks",
                context={
                    "pool": pool.pool_address,
                    "planned": planned,
                    "production_prefix": production[: len(planned)],
                },
            )
        for kind in event_kinds:
            jobs.append(
                EventAcquisitionJob(
                    pool_address=pool.pool_address,
                    kind=kind,
                    start_block=pool.creation_block,
                    end_block=end,
                    creation_block=pool.creation_block,
                    chunk_size=chunk_size,
                )
            )
    return tuple(jobs)


def build_decimals_jobs(
    pools: Sequence[RegistryPoolRef],
) -> tuple[TokenDecimalsJob, ...]:
    """One decimals job per distinct token, pinned to earliest pool birth block."""
    earliest: dict[str, int] = {}
    for pool in pools:
        for token in (pool.token0, pool.token1):
            prev = earliest.get(token)
            if prev is None or pool.creation_block < prev:
                earliest[token] = pool.creation_block
    return tuple(
        TokenDecimalsJob(token=token, block_number=block)
        for token, block in sorted(earliest.items(), key=lambda item: item[0])
    )


def build_acquisition_plan(
    pools: Sequence[RegistryPoolRef],
    config: PairEventOrchestratorConfig,
) -> AcquisitionPlan:
    """Compose the full deterministic plan for a config + registry slice."""
    selected = select_pools_for_run(
        pools,
        pool_offset=config.pool_offset,
        max_pools=config.max_pools,
        pool_allowlist=config.pool_allowlist,
    )
    event_jobs = build_event_jobs(
        selected,
        finality_cutoff_block=config.finality_cutoff_block,
        chunk_size=config.chunk_size,
        event_kinds=config.event_kinds,
        max_chunks_per_pool=config.max_chunks_per_pool,
        max_end_block=config.max_end_block,
    )
    decimals_jobs = (
        build_decimals_jobs(selected) if config.acquire_token_decimals else ()
    )
    return AcquisitionPlan(
        registry_dataset_id=config.registry_dataset_id,
        finality_cutoff_block=config.finality_cutoff_block,
        chunk_size=config.chunk_size,
        pools=selected,
        event_jobs=event_jobs,
        decimals_jobs=decimals_jobs,
        pilot_bounds=config.pilot_bounds_dict(),
    )


def load_completed_chunk_ranges(
    receipt_db_path: Path | str,
    *,
    pair: str,
    kind: EventKind,
) -> frozenset[tuple[int, int]]:
    """Read completed chunk ranges for one pair/kind from the receipt store."""
    path = Path(receipt_db_path)
    if not path.is_file():
        return frozenset()
    pair_n = normalize_pool_address(pair)
    topic = topic_for_kind(kind)
    conn = sqlite3.connect(path)
    try:
        # Table may not exist yet on a fresh db — treat as empty coverage.
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (RECEIPT_TABLE,),
        ).fetchone()
        if exists is None:
            return frozenset()
        rows = conn.execute(
            f"SELECT start_block, end_block FROM {RECEIPT_TABLE} "
            "WHERE chain = ? AND pair = ? AND topic = ? "
            "ORDER BY start_block, end_block",
            (ETHEREUM_CHAIN, pair_n, topic),
        ).fetchall()
    finally:
        conn.close()
    return frozenset((int(start), int(end)) for start, end in rows)


def job_coverage(
    job: EventAcquisitionJob,
    *,
    receipt_db_path: Path | str,
) -> JobCoverage:
    """Compute completed vs pending chunks for one event job (offline)."""
    planned = iter_chunk_ranges(job.start_block, job.end_block, job.chunk_size)
    completed = load_completed_chunk_ranges(
        receipt_db_path, pair=job.pool_address, kind=job.kind
    )
    done = tuple(r for r in planned if r in completed)
    pending = tuple(r for r in planned if r not in completed)
    # Fail closed if a receipt exists outside the planned tiling for this job
    # window with overlapping but non-matching bounds (re-chunk hazard).
    for start, end in completed:
        if end < job.start_block or start > job.end_block:
            continue
        if (start, end) not in planned and start >= job.start_block and end <= job.end_block:
            raise PairEventOrchestrationError(
                "receipt chunk bounds do not match the planned tiling; "
                "refusing to resume with a different chunk_size",
                context={
                    "pair": job.pool_address,
                    "kind": job.kind,
                    "receipt": (start, end),
                    "chunk_size": job.chunk_size,
                    "job_range": (job.start_block, job.end_block),
                },
            )
    return JobCoverage(job=job, completed_chunks=done, pending_chunks=pending)


def build_coverage_report(
    plan: AcquisitionPlan,
    *,
    receipt_db_path: Path | str,
) -> CoverageReport:
    jobs = tuple(
        job_coverage(job, receipt_db_path=receipt_db_path) for job in plan.event_jobs
    )
    return CoverageReport(plan=plan, jobs=jobs)


def verify_registry_manifest(
    manifest: DatasetManifest,
    *,
    require_accepted: bool = True,
    expected_dataset_id: str = ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
) -> None:
    if manifest.dataset_type != DEX_POOL_REGISTRY_DATASET_TYPE:
        raise PairEventOrchestrationError(
            "registry dataset_type must be dex_pool_registry",
            context={"dataset_type": manifest.dataset_type},
        )
    if (
        manifest.schema.name != DEX_POOL_REGISTRY_SCHEMA_NAME
        or manifest.schema.version != DEX_POOL_REGISTRY_SCHEMA_VERSION
    ):
        raise PairEventOrchestrationError(
            "registry schema identity is not accepted",
            context={
                "schema_name": manifest.schema.name,
                "schema_version": manifest.schema.version,
            },
        )
    if manifest.quality_status is not QualityStatus.PASS:
        raise PairEventOrchestrationError(
            "registry quality must be PASS",
            context={"quality_status": manifest.quality_status.value},
        )
    if require_accepted and manifest.dataset_id != expected_dataset_id:
        raise PairEventOrchestrationError(
            "registry dataset_id is not the accepted production registry",
            context={
                "dataset_id": manifest.dataset_id,
                "expected": expected_dataset_id,
            },
        )
    paths = {spec.relative_path for spec in manifest.files}
    if DEX_POOL_REGISTRY_RELATIVE_PATH not in paths:
        raise PairEventOrchestrationError(
            "registry manifest missing pools parquet",
            context={"files": sorted(paths)},
        )


def resolve_registry_paths(
    config: PairEventOrchestratorConfig,
) -> tuple[Path, Path]:
    """Return ``(dataset_dir, pools_parquet_path)`` under the store root."""
    dataset_dir = dataset_absolute_dir(
        Path(config.registry_store_root), config.registry_dataset_id
    )
    pools_path = dataset_dir / DEX_POOL_REGISTRY_RELATIVE_PATH
    return dataset_dir, pools_path


def load_plan_from_registry_store(
    config: PairEventOrchestratorConfig,
    *,
    manifest: DatasetManifest | None = None,
) -> AcquisitionPlan:
    """Load registry pools from the content-addressed store and build a plan.

    Production planning **always** loads and verifies the dataset manifest and
    the declared pools parquet hash. There is no path that plans from a bare
    parquet file while bypassing MAN-001 identity. When ``manifest`` is omitted
    it is read from ``<dataset_dir>/manifest.json``.
    """
    dataset_dir, pools_path = resolve_registry_paths(config)
    if manifest is None:
        manifest_path = dataset_dir / "manifest.json"
        if not manifest_path.is_file():
            raise PairEventOrchestrationError(
                "registry manifest.json is required for production planning; "
                "refusing to plan from pools parquet without MAN-001 verification",
                context={"path": str(manifest_path)},
            )
        try:
            manifest = load_manifest_file(manifest_path)
        except Exception as exc:
            raise PairEventOrchestrationError(
                "failed to load registry manifest.json",
                context={"path": str(manifest_path), "error": str(exc)},
            ) from exc

    verify_registry_manifest(
        manifest,
        require_accepted=config.require_accepted_registry,
        expected_dataset_id=config.registry_dataset_id,
    )
    if manifest.dataset_id != config.registry_dataset_id:
        raise PairEventOrchestrationError(
            "manifest dataset_id does not match config.registry_dataset_id",
            context={
                "manifest": manifest.dataset_id,
                "config": config.registry_dataset_id,
            },
        )
    if not pools_path.is_file():
        raise PairEventOrchestrationError(
            "registry pools parquet missing under store",
            context={"path": str(pools_path)},
        )
    observed_sha, observed_bytes = stream_sha256_and_size(pools_path)
    declared = next(
        spec
        for spec in manifest.files
        if spec.relative_path == DEX_POOL_REGISTRY_RELATIVE_PATH
    )
    if observed_sha != declared.sha256 or observed_bytes != declared.bytes:
        raise PairEventOrchestrationError(
            "registry pools parquet does not match manifest declaration",
            context={
                "observed_sha": observed_sha,
                "declared_sha": declared.sha256,
                "observed_bytes": observed_bytes,
                "declared_bytes": declared.bytes,
            },
        )

    pools = load_registry_pool_refs(pools_path)
    return build_acquisition_plan(pools, config)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class PairEventAcquisitionOrchestrator:
    """Schedules and drives ``UniswapV2PairEventIngestor`` without duplicating it.

    Construct with runtime config. Optionally inject an already-built ingestor
    (tests / custom transport). When omitted, ``run()`` builds one from config
    URLs and the supplied ``raw_writer``.
    """

    config: PairEventOrchestratorConfig
    ingestor: UniswapV2PairEventIngestor | None = None
    raw_writer: Any | None = None
    _owns_ingestor: bool = field(default=False, init=False, repr=False)

    def build_plan(
        self,
        *,
        manifest: DatasetManifest | None = None,
        pools: Sequence[RegistryPoolRef] | None = None,
    ) -> AcquisitionPlan:
        """Build a deterministic acquisition plan.

        When ``require_accepted_registry`` is True (production default), the plan
        must be loaded from the verified accepted registry store. Caller-supplied
        ``pools`` are refused so production planning cannot bypass MAN-001
        identity and pools-hash verification. Test/custom injection is allowed
        only when ``require_accepted_registry=False``.
        """
        if pools is not None:
            if self.config.require_accepted_registry:
                raise PairEventOrchestrationError(
                    "caller-supplied pools are not allowed when "
                    "require_accepted_registry=True; load the verified accepted "
                    "registry from the store (manifest + pools hash)",
                    context={
                        "registry_dataset_id": self.config.registry_dataset_id,
                        "require_accepted_registry": True,
                    },
                )
            return build_acquisition_plan(pools, self.config)
        return load_plan_from_registry_store(self.config, manifest=manifest)

    def coverage(self, plan: AcquisitionPlan) -> CoverageReport:
        return build_coverage_report(plan, receipt_db_path=self.config.receipt_db_path)

    def _ensure_ingestor(self) -> UniswapV2PairEventIngestor:
        if self.ingestor is not None:
            return self.ingestor
        if self.raw_writer is None:
            raise PairEventOrchestrationError(
                "raw_writer is required when ingestor is not injected"
            )
        self.ingestor = UniswapV2PairEventIngestor(
            primary_rpc_url=self.config.primary_rpc_url,
            secondary_rpc_url=self.config.secondary_rpc_url,
            raw_writer=self.raw_writer,
            primary_provider_id=self.config.primary_provider_id,
            secondary_provider_id=self.config.secondary_provider_id,
            raw_root=Path(self.config.raw_root),
            finality_cutoff_block=self.config.finality_cutoff_block,
            header_batch_size=self.config.header_batch_size,
            header_max_in_flight=self.config.header_max_in_flight,
            header_requests_per_second=self.config.header_requests_per_second,
            use_header_batches=self.config.use_header_batches,
        )
        self._owns_ingestor = True
        return self.ingestor

    def close(self) -> None:
        if self._owns_ingestor and self.ingestor is not None:
            self.ingestor.close()
            self.ingestor = None
            self._owns_ingestor = False

    def run(
        self,
        *,
        plan: AcquisitionPlan | None = None,
        manifest: DatasetManifest | None = None,
        dry_run: bool = False,
        skip_complete_jobs: bool = True,
        stop_on_error: bool = True,
    ) -> OrchestrationResult:
        """Execute (or dry-run) the acquisition plan.

        Parameters
        ----------
        dry_run:
            When True, build plan + coverage only. No ingestor calls, no network.
        skip_complete_jobs:
            When True, jobs whose planned chunks are all present in the receipt
            store are not re-submitted to ``fetch`` (resume-friendly). Incomplete
            jobs are still submitted as their full ``[start, end]`` range so the
            ingestor's per-chunk resume / reorg checks remain authoritative.
        stop_on_error:
            When True, the first failed job aborts the run after recording it.

        When ``require_accepted_registry`` is True, a caller-supplied prebuilt
        ``plan`` is refused. Production execution must build the plan via the
        verified store path (accepted manifest identity + pools hash). Pass
        ``require_accepted_registry=False`` for test/custom injection only.
        """
        if plan is not None and self.config.require_accepted_registry:
            raise PairEventOrchestrationError(
                "caller-supplied prebuilt plan is not allowed when "
                "require_accepted_registry=True; build the plan via the verified "
                "accepted registry store path",
                context={
                    "registry_dataset_id": self.config.registry_dataset_id,
                    "plan_registry_dataset_id": plan.registry_dataset_id,
                    "require_accepted_registry": True,
                },
            )
        active_plan = plan if plan is not None else self.build_plan(manifest=manifest)
        coverage_before = self.coverage(active_plan)

        if dry_run:
            return OrchestrationResult(
                plan=active_plan,
                coverage_before=coverage_before,
                event_results=tuple(
                    EventJobResult(
                        job=job_cov.job,
                        status="skipped_complete" if job_cov.is_complete else "completed",
                        detail="dry_run",
                    )
                    for job_cov in coverage_before.jobs
                ),
                decimals_results=tuple(
                    DecimalsJobResult(job=job, status="completed", detail="dry_run")
                    for job in active_plan.decimals_jobs
                ),
                dry_run=True,
            )

        ingestor = self._ensure_ingestor()
        receipt_db = str(self.config.receipt_db_path)
        raw_root = Path(self.config.raw_root)

        decimals_results: list[DecimalsJobResult] = []
        for decimals_job in active_plan.decimals_jobs:
            try:
                row = ingestor.fetch_token_decimals(
                    token=decimals_job.token,
                    block_number=decimals_job.block_number,
                    receipt_db_path=receipt_db,
                    raw_root=raw_root,
                )
                decimals_results.append(
                    DecimalsJobResult(job=decimals_job, status="completed", row=row)
                )
            except (UniswapV2IngestionError, ValueError, OSError) as exc:
                decimals_results.append(
                    DecimalsJobResult(
                        job=decimals_job, status="failed", detail=str(exc)
                    )
                )
                if stop_on_error:
                    return OrchestrationResult(
                        plan=active_plan,
                        coverage_before=coverage_before,
                        event_results=(),
                        decimals_results=tuple(decimals_results),
                        dry_run=False,
                    )

        coverage_by_key = {
            (c.job.pool_address, c.job.kind, c.job.start_block, c.job.end_block): c
            for c in coverage_before.jobs
        }
        event_results: list[EventJobResult] = []
        for job in active_plan.event_jobs:
            cov = coverage_by_key.get(
                (job.pool_address, job.kind, job.start_block, job.end_block)
            )
            if skip_complete_jobs and cov is not None and cov.is_complete:
                event_results.append(
                    EventJobResult(
                        job=job,
                        status="skipped_complete",
                        detail="all planned chunks present in receipt store",
                    )
                )
                continue
            try:
                # Full-range fetch: ingestor skips/verifies completed chunks via
                # receipts and acquires only missing ones. Do not re-chunk here.
                ingestor.fetch(
                    pair=job.pool_address,
                    kind=job.kind,
                    start_block=job.start_block,
                    end_block=job.end_block,
                    chunk_size=job.chunk_size,
                    receipt_db_path=receipt_db,
                    emit_rows=self.config.emit_rows,
                    raw_root=raw_root,
                )
                event_results.append(EventJobResult(job=job, status="completed"))
            except (UniswapV2IngestionError, ValueError, OSError) as exc:
                event_results.append(
                    EventJobResult(job=job, status="failed", detail=str(exc))
                )
                if stop_on_error:
                    break

        return OrchestrationResult(
            plan=active_plan,
            coverage_before=coverage_before,
            event_results=tuple(event_results),
            decimals_results=tuple(decimals_results),
            dry_run=False,
        )


__all__ = [
    "ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID",
    "AcquisitionPlan",
    "ChunkCoverage",
    "CoverageReport",
    "DEFAULT_EVENT_CHUNK_SIZE",
    "DEFAULT_EVENT_KINDS",
    "DecimalsJobResult",
    "EventAcquisitionJob",
    "EventJobResult",
    "JobCoverage",
    "OrchestrationResult",
    "PINNED_FINALITY_CUTOFF_BLOCK",
    "PairEventAcquisitionOrchestrator",
    "PairEventOrchestrationError",
    "PairEventOrchestratorConfig",
    "RegistryPoolRef",
    "TokenDecimalsJob",
    "build_acquisition_plan",
    "build_coverage_report",
    "build_decimals_jobs",
    "build_event_jobs",
    "iter_chunk_ranges",
    "job_coverage",
    "load_completed_chunk_ranges",
    "load_plan_from_registry_store",
    "load_registry_pool_refs",
    "normalize_pool_address",
    "production_aligned_end_block",
    "production_chunk_ranges",
    "resolve_registry_paths",
    "select_pools_for_run",
    "verify_registry_manifest",
]
