"""DEX-003 / ADR-0015 — deterministic ``dex_pool_registry`` transform.

Builds the first ADR-0015 canonical product from a published Uniswap V2
``PairCreated`` census. Selection is pure and offline:

* Ethereum mainnet + canonical Uniswap V2 factory only.
* Keep every factory pool where **exactly one** side is accepted USDC or USDT.
* Freeze base/stable-quote orientation so token-order cannot invert returns.
* Carry birth/block identity, conservative ``source_available_at``
  (``event_time + 24h``), actual ``retrieved_at``, and raw/dataset lineage.

No network. No Swap/Sync acquisition. No factor or universe membership logic.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final, Literal

import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    DependencyKind,
    DependencyRef,
    OutputFileSpec,
    PublishPlan,
    QualityStatus,
    RowCountPolicy,
    RowCountReceipt,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size

# ---------------------------------------------------------------------------
# Public identity constants
# ---------------------------------------------------------------------------

DEX_POOL_REGISTRY_DATASET_TYPE: Final[str] = "dex_pool_registry"
DEX_POOL_REGISTRY_SCHEMA_NAME: Final[str] = "dex_pool_registry"
DEX_POOL_REGISTRY_SCHEMA_VERSION: Final[str] = "1"
DEX_POOL_REGISTRY_TRANSFORM_NAME: Final[str] = "dex_pool_registry_from_pair_created"
DEX_POOL_REGISTRY_TRANSFORM_VERSION: Final[str] = "1"
DEX_POOL_REGISTRY_RELATIVE_PATH: Final[str] = "dex/dex_pool_registry/pools.parquet"

SOURCE_PAIR_CREATED_DATASET_TYPE: Final[str] = "uniswap_v2_pair_created"
SOURCE_PAIR_CREATED_SCHEMA_NAME: Final[str] = "uniswap_v2_pair_created"
SOURCE_PAIR_CREATED_SCHEMA_VERSION: Final[str] = "1"
SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH: Final[str] = (
    "dex/uniswap_v2_pair_created/events.parquet"
)

# Pinned full factory census that authorizes this transform (CURRENT_TASK).
PINNED_PAIR_CREATED_DATASET_ID: Final[str] = (
    "ds_0eab9b797fafac840b85175f40966f54c33d2ae3b0e8cc73ea63c9c9f2e5da5c"
)

ETHEREUM_CHAIN: Final[str] = "ethereum"
UNISWAP_V2_PROTOCOL: Final[str] = "uniswap_v2"
UNISWAP_V2_FACTORY: Final[str] = "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"

# Canonical Ethereum mainnet stable-quote identities (address is identity).
USDC_ADDRESS: Final[str] = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_ADDRESS: Final[str] = "0xdac17f958d2ee523a2206206994597c13d831ec7"

QuoteSymbol = Literal["USDC", "USDT"]

ACCEPTED_STABLE_QUOTES: Final[dict[str, QuoteSymbol]] = {
    USDC_ADDRESS: "USDC",
    USDT_ADDRESS: "USDT",
}

SOURCE_AVAILABILITY_LAG: Final[timedelta] = timedelta(hours=24)

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")
_ADDRESS_RE = re.compile(r"^0x[0-9a-f]{40}$")
_HEX_BYTES32_RE = re.compile(r"^0x[0-9a-f]{64}$")

_REQUIRED_SOURCE_COLUMNS: Final[tuple[str, ...]] = (
    "chain",
    "factory",
    "pair",
    "token0",
    "token1",
    "block_number",
    "block_hash",
    "block_timestamp",
    "tx_hash",
    "tx_index",
    "log_index",
    "event_time",
    "availability_time",
    "raw_object_id",
    "block_raw_object_id",
)

DEX_POOL_REGISTRY_SCHEMA: Final[pa.Schema] = pa.schema(
    [
        ("chain", pa.string()),
        ("protocol", pa.string()),
        ("factory", pa.string()),
        ("pool_address", pa.string()),
        ("token0", pa.string()),
        ("token1", pa.string()),
        ("base_token", pa.string()),
        ("quote_token", pa.string()),
        ("quote_symbol", pa.string()),
        ("creation_block", pa.int64()),
        ("block_hash", pa.string()),
        ("block_timestamp", pa.int64()),
        ("tx_hash", pa.string()),
        ("tx_index", pa.int64()),
        ("log_index", pa.int64()),
        ("event_time", pa.string()),
        ("source_available_at", pa.string()),
        ("retrieved_at", pa.string()),
        ("raw_object_id", pa.string()),
        ("block_raw_object_id", pa.string()),
        ("pair_created_dataset_id", pa.string()),
    ]
)


# ---------------------------------------------------------------------------
# Errors / records
# ---------------------------------------------------------------------------


class DexPoolRegistryError(RuntimeError):
    """Fail-closed transform errors for the DEX pool registry."""

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


@dataclass(frozen=True, slots=True)
class DexPoolRegistryRow:
    """One canonical registry membership for a direct stable-quote pool."""

    chain: str
    protocol: str
    factory: str
    pool_address: str
    token0: str
    token1: str
    base_token: str
    quote_token: str
    quote_symbol: QuoteSymbol
    creation_block: int
    block_hash: str
    block_timestamp: int
    tx_hash: str
    tx_index: int
    log_index: int
    event_time: datetime
    source_available_at: datetime
    retrieved_at: datetime
    raw_object_id: str
    block_raw_object_id: str
    pair_created_dataset_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "protocol": self.protocol,
            "factory": self.factory,
            "pool_address": self.pool_address,
            "token0": self.token0,
            "token1": self.token1,
            "base_token": self.base_token,
            "quote_token": self.quote_token,
            "quote_symbol": self.quote_symbol,
            "creation_block": self.creation_block,
            "block_hash": self.block_hash,
            "block_timestamp": self.block_timestamp,
            "tx_hash": self.tx_hash,
            "tx_index": self.tx_index,
            "log_index": self.log_index,
            "event_time": self.event_time.isoformat(),
            "source_available_at": self.source_available_at.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "raw_object_id": self.raw_object_id,
            "block_raw_object_id": self.block_raw_object_id,
            "pair_created_dataset_id": self.pair_created_dataset_id,
        }


@dataclass(frozen=True, slots=True)
class DexPoolRegistryBuildResult:
    """Staged registry outputs plus a ready-to-publish MAN-001 plan."""

    publish_plan: PublishPlan
    rows: tuple[DexPoolRegistryRow, ...]
    output_path: Path
    source_dataset_id: str
    selected_count: int
    usdc_count: int
    usdt_count: int
    source_row_count: int


# ---------------------------------------------------------------------------
# Parsing / normalization helpers
# ---------------------------------------------------------------------------


def normalize_address(value: object, *, label: str) -> str:
    """Lowercase-normalize a 20-byte hex address; reject malformed input."""
    if not isinstance(value, str):
        raise DexPoolRegistryError(
            f"{label} must be a string address",
            context={"type": type(value).__name__},
        )
    text = value.strip().lower()
    if not _ADDRESS_RE.fullmatch(text):
        raise DexPoolRegistryError(
            f"{label} is not a 20-byte 0x-hex address",
            context={"value": value},
        )
    return text


def normalize_bytes32(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise DexPoolRegistryError(
            f"{label} must be a string",
            context={"type": type(value).__name__},
        )
    text = value.strip().lower()
    if not _HEX_BYTES32_RE.fullmatch(text):
        raise DexPoolRegistryError(
            f"{label} is not a 32-byte 0x-hex value",
            context={"value": value},
        )
    return text


def require_utc_datetime(value: datetime, *, label: str) -> datetime:
    if not isinstance(value, datetime):
        raise DexPoolRegistryError(
            f"{label} must be a datetime",
            context={"type": type(value).__name__},
        )
    if value.tzinfo is None:
        raise DexPoolRegistryError(
            f"{label} must be timezone-aware UTC",
            context={"value": str(value)},
        )
    return value.astimezone(UTC)


def parse_iso_utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DexPoolRegistryError(
            f"{label} must be a non-empty ISO-8601 string",
            context={"value": value},
        )
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DexPoolRegistryError(
            f"{label} is not a valid ISO-8601 datetime",
            context={"value": value},
        ) from exc
    return require_utc_datetime(parsed, label=label)


def source_available_at(event_time: datetime) -> datetime:
    """ADR-0015 conservative finality lag for finalized Ethereum events."""
    return require_utc_datetime(event_time, label="event_time") + SOURCE_AVAILABILITY_LAG


def orient_base_quote(
    token0: str,
    token1: str,
) -> tuple[str, str, QuoteSymbol] | None:
    """Return ``(base, quote, quote_symbol)`` for a direct stable-quote pair.

    Exactly one of ``token0`` / ``token1`` must be an accepted stable. The
    non-stable side is the frozen base. Dual-stable and non-stable pairs return
    ``None`` (not selected for the research price panel).
    """
    t0 = normalize_address(token0, label="token0")
    t1 = normalize_address(token1, label="token1")
    if t0 == t1:
        raise DexPoolRegistryError(
            "token0 and token1 must differ",
            context={"token0": t0, "token1": t1},
        )
    s0 = ACCEPTED_STABLE_QUOTES.get(t0)
    s1 = ACCEPTED_STABLE_QUOTES.get(t1)
    if s0 is not None and s1 is None:
        return t1, t0, s0
    if s1 is not None and s0 is None:
        return t0, t1, s1
    return None


def is_direct_stable_quote_pair(token0: str, token1: str) -> bool:
    """True when exactly one side is accepted USDC or USDT."""
    return orient_base_quote(token0, token1) is not None


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------


def _require_int(value: object, *, label: str, minimum: int | None = None) -> int:
    # pyarrow / numpy scalar → python int via .item() when present.
    if not isinstance(value, bool) and hasattr(value, "item") and not isinstance(value, int):
        try:
            value = value.item()  # type: ignore[union-attr]
        except Exception:
            pass
    if isinstance(value, bool) or not isinstance(value, int):
        raise DexPoolRegistryError(
            f"{label} must be an integer",
            context={"value": value, "type": type(value).__name__},
        )
    if minimum is not None and value < minimum:
        raise DexPoolRegistryError(
            f"{label} must be >= {minimum}",
            context={"value": value},
        )
    return value


def _require_raw_object_id(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.startswith("raw_"):
        raise DexPoolRegistryError(
            f"{label} must be a raw_ object id",
            context={"value": value},
        )
    digest = value[4:]
    if not _SHA256_HEX_RE.fullmatch(digest):
        raise DexPoolRegistryError(
            f"{label} must be raw_<64 lowercase hex>",
            context={"value": value},
        )
    return value


def registry_row_from_pair_created(
    source: Mapping[str, Any],
    *,
    pair_created_dataset_id: str,
) -> DexPoolRegistryRow | None:
    """Map one PairCreated row into a registry row, or ``None`` if not selected."""
    if not pair_created_dataset_id.startswith("ds_") or len(pair_created_dataset_id) != 3 + 64:
        raise DexPoolRegistryError(
            "pair_created_dataset_id must be ds_<64 hex>",
            context={"dataset_id": pair_created_dataset_id},
        )
    digest = pair_created_dataset_id[3:]
    if not _SHA256_HEX_RE.fullmatch(digest):
        raise DexPoolRegistryError(
            "pair_created_dataset_id must be ds_<64 lowercase hex>",
            context={"dataset_id": pair_created_dataset_id},
        )

    chain = str(source.get("chain", "")).strip().lower()
    if chain != ETHEREUM_CHAIN:
        raise DexPoolRegistryError(
            "PairCreated row chain must be ethereum",
            context={"chain": source.get("chain")},
        )

    factory = normalize_address(source.get("factory"), label="factory")
    if factory != UNISWAP_V2_FACTORY:
        raise DexPoolRegistryError(
            "PairCreated row factory is not the canonical Uniswap V2 factory",
            context={"factory": factory, "expected": UNISWAP_V2_FACTORY},
        )

    token0 = normalize_address(source.get("token0"), label="token0")
    token1 = normalize_address(source.get("token1"), label="token1")
    orientation = orient_base_quote(token0, token1)
    if orientation is None:
        return None
    base_token, quote_token, quote_symbol = orientation

    event_time = parse_iso_utc(source.get("event_time"), label="event_time")
    retrieved_at = parse_iso_utc(source.get("availability_time"), label="availability_time")
    available = source_available_at(event_time)

    return DexPoolRegistryRow(
        chain=ETHEREUM_CHAIN,
        protocol=UNISWAP_V2_PROTOCOL,
        factory=UNISWAP_V2_FACTORY,
        pool_address=normalize_address(source.get("pair"), label="pair"),
        token0=token0,
        token1=token1,
        base_token=base_token,
        quote_token=quote_token,
        quote_symbol=quote_symbol,
        creation_block=_require_int(source.get("block_number"), label="block_number", minimum=0),
        block_hash=normalize_bytes32(source.get("block_hash"), label="block_hash"),
        block_timestamp=_require_int(
            source.get("block_timestamp"), label="block_timestamp", minimum=0
        ),
        tx_hash=normalize_bytes32(source.get("tx_hash"), label="tx_hash"),
        tx_index=_require_int(source.get("tx_index"), label="tx_index", minimum=0),
        log_index=_require_int(source.get("log_index"), label="log_index", minimum=0),
        event_time=event_time,
        source_available_at=available,
        retrieved_at=retrieved_at,
        raw_object_id=_require_raw_object_id(
            source.get("raw_object_id"), label="raw_object_id"
        ),
        block_raw_object_id=_require_raw_object_id(
            source.get("block_raw_object_id"), label="block_raw_object_id"
        ),
        pair_created_dataset_id=pair_created_dataset_id,
    )


def select_direct_stable_quote_pools(
    pair_created_rows: Sequence[Mapping[str, Any]],
    *,
    pair_created_dataset_id: str,
) -> tuple[DexPoolRegistryRow, ...]:
    """Select and orient every direct USDC/USDT pool from a PairCreated census.

    Fail closed on duplicate pool addresses or conflicting birth identities for
    the same pool. Output order is birth order:
    ``(creation_block, tx_index, log_index, pool_address)``.
    """
    selected: list[DexPoolRegistryRow] = []
    by_pool: dict[str, DexPoolRegistryRow] = {}

    for index, raw in enumerate(pair_created_rows):
        if not isinstance(raw, Mapping):
            raise DexPoolRegistryError(
                "PairCreated row must be a mapping",
                context={"index": index, "type": type(raw).__name__},
            )
        row = registry_row_from_pair_created(
            raw, pair_created_dataset_id=pair_created_dataset_id
        )
        if row is None:
            continue
        prior = by_pool.get(row.pool_address)
        if prior is not None:
            if (
                prior.tx_hash != row.tx_hash
                or prior.log_index != row.log_index
                or prior.creation_block != row.creation_block
                or prior.token0 != row.token0
                or prior.token1 != row.token1
            ):
                raise DexPoolRegistryError(
                    "duplicate pool_address with conflicting birth identity",
                    context={
                        "pool_address": row.pool_address,
                        "first_tx": prior.tx_hash,
                        "second_tx": row.tx_hash,
                    },
                )
            # Exact duplicate of the same birth event — ignore.
            continue
        by_pool[row.pool_address] = row
        selected.append(row)

    ordered = sorted(
        selected,
        key=lambda r: (r.creation_block, r.tx_index, r.log_index, r.pool_address),
    )
    return tuple(ordered)


# ---------------------------------------------------------------------------
# Table / parquet
# ---------------------------------------------------------------------------


def registry_rows_to_table(rows: Sequence[DexPoolRegistryRow]) -> pa.Table:
    """Materialize registry rows as a schema-conformant Arrow table."""
    if not rows:
        empty: dict[str, list[Any]] = {name: [] for name in DEX_POOL_REGISTRY_SCHEMA.names}
        return pa.Table.from_pydict(empty, schema=DEX_POOL_REGISTRY_SCHEMA)
    records = [row.as_dict() for row in rows]
    return pa.Table.from_pylist(records, schema=DEX_POOL_REGISTRY_SCHEMA)


def write_registry_parquet(path: Path, rows: Sequence[DexPoolRegistryRow]) -> tuple[str, int, int]:
    """Write zstd parquet; return ``(sha256, byte_size, row_count)``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    table = registry_rows_to_table(rows)
    pq.write_table(table, path, compression="zstd")
    sha256, byte_size = stream_sha256_and_size(path)
    return sha256, byte_size, int(table.num_rows)


def load_pair_created_records(events_path: Path) -> list[dict[str, Any]]:
    """Load PairCreated event records from a published parquet file."""
    path = Path(events_path)
    if not path.is_file():
        raise DexPoolRegistryError(
            "PairCreated events parquet is missing",
            context={"path": str(path)},
        )
    table = pq.read_table(path)
    missing = [c for c in _REQUIRED_SOURCE_COLUMNS if c not in table.column_names]
    if missing:
        raise DexPoolRegistryError(
            "PairCreated events parquet is missing required columns",
            context={"missing": missing, "columns": list(table.column_names)},
        )
    # Keep only required columns to avoid surprising extras affecting selection.
    table = table.select(list(_REQUIRED_SOURCE_COLUMNS))
    return table.to_pylist()


# ---------------------------------------------------------------------------
# Source verification + publish plan
# ---------------------------------------------------------------------------


def _require_code_commit(code_commit: str) -> str:
    commit = code_commit.strip()
    if not commit or commit == "unknown":
        raise DexPoolRegistryError(
            "code_commit is required and must be a non-empty immutable code identity",
            context={"code_commit": code_commit},
        )
    return commit


def _resolve_config_sha256(
    config_sha256: str | None,
    *,
    payload: Mapping[str, Any],
) -> str:
    if config_sha256 is not None and str(config_sha256).strip() != "":
        digest = str(config_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(digest):
            raise DexPoolRegistryError(
                "config_sha256 must be a 64-character lowercase hex SHA-256 digest",
                context={"config_sha256": config_sha256},
            )
        return digest
    body = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _parquet_row_counter(path: Path) -> int:
    return int(pq.ParquetFile(str(path)).metadata.num_rows)


def verify_pair_created_source_manifest(manifest: DatasetManifest) -> None:
    """Fail closed unless the upstream census is the accepted PairCreated product."""
    if manifest.dataset_type != SOURCE_PAIR_CREATED_DATASET_TYPE:
        raise DexPoolRegistryError(
            "source dataset_type must be uniswap_v2_pair_created",
            context={
                "dataset_id": manifest.dataset_id,
                "dataset_type": manifest.dataset_type,
            },
        )
    if (
        manifest.schema.name != SOURCE_PAIR_CREATED_SCHEMA_NAME
        or manifest.schema.version != SOURCE_PAIR_CREATED_SCHEMA_VERSION
    ):
        raise DexPoolRegistryError(
            "source schema identity is not the accepted PairCreated schema",
            context={
                "schema_name": manifest.schema.name,
                "schema_version": manifest.schema.version,
            },
        )
    if manifest.quality_status is not QualityStatus.PASS:
        raise DexPoolRegistryError(
            "source PairCreated dataset quality must be PASS",
            context={
                "dataset_id": manifest.dataset_id,
                "quality_status": manifest.quality_status.value,
            },
        )
    if not manifest.dataset_id.startswith("ds_") or len(manifest.dataset_id) != 3 + 64:
        raise DexPoolRegistryError(
            "source dataset_id is malformed",
            context={"dataset_id": manifest.dataset_id},
        )
    paths = {spec.relative_path for spec in manifest.files}
    if SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH not in paths:
        raise DexPoolRegistryError(
            "source manifest is missing PairCreated events parquet",
            context={
                "expected": SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH,
                "files": sorted(paths),
            },
        )
    if manifest.statistics.row_count <= 0:
        raise DexPoolRegistryError(
            "source PairCreated census has no rows",
            context={"dataset_id": manifest.dataset_id},
        )


def build_dex_pool_registry(
    *,
    source_manifest: DatasetManifest,
    source_events_path: Path | str,
    output_dir: Path | str,
    code_commit: str,
    config_sha256: str | None = None,
    require_pinned_source: bool = False,
    created_at: datetime | None = None,
) -> DexPoolRegistryBuildResult:
    """Build staged ``dex_pool_registry`` outputs and a MAN-001 publish plan.

    Parameters
    ----------
    source_manifest:
        Verified MAN-001 manifest for a ``uniswap_v2_pair_created`` dataset.
    source_events_path:
        Local path to that dataset's ``events.parquet`` (caller supplies the
        file; this transform never opens the network or the raw object store).
    output_dir:
        Directory that receives staged ``dex/dex_pool_registry/pools.parquet``.
    require_pinned_source:
        When True, refuse any source other than
        :data:`PINNED_PAIR_CREATED_DATASET_ID` (production census path).
    """
    verify_pair_created_source_manifest(source_manifest)
    source_dataset_id = source_manifest.dataset_id
    if require_pinned_source and source_dataset_id != PINNED_PAIR_CREATED_DATASET_ID:
        raise DexPoolRegistryError(
            "source dataset_id is not the pinned full PairCreated census",
            context={
                "dataset_id": source_dataset_id,
                "expected": PINNED_PAIR_CREATED_DATASET_ID,
            },
        )

    events_path = Path(source_events_path)
    records = load_pair_created_records(events_path)
    if len(records) != source_manifest.statistics.row_count:
        raise DexPoolRegistryError(
            "PairCreated parquet row count does not match manifest statistics",
            context={
                "parquet_rows": len(records),
                "manifest_rows": source_manifest.statistics.row_count,
            },
        )

    # Re-hash the supplied events file against the manifest declaration.
    events_sha, events_bytes = stream_sha256_and_size(events_path)
    declared = next(
        spec
        for spec in source_manifest.files
        if spec.relative_path == SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH
    )
    if events_sha != declared.sha256:
        raise DexPoolRegistryError(
            "PairCreated events parquet sha256 does not match source manifest",
            context={
                "observed": events_sha,
                "declared": declared.sha256,
                "path": str(events_path),
            },
        )
    if events_bytes != declared.bytes:
        raise DexPoolRegistryError(
            "PairCreated events parquet size does not match source manifest",
            context={
                "observed": events_bytes,
                "declared": declared.bytes,
                "path": str(events_path),
            },
        )

    rows = select_direct_stable_quote_pools(
        records, pair_created_dataset_id=source_dataset_id
    )
    if not rows:
        raise DexPoolRegistryError(
            "direct stable-quote selection produced zero pools",
            context={"source_dataset_id": source_dataset_id, "source_rows": len(records)},
        )

    usdc_count = sum(1 for row in rows if row.quote_symbol == "USDC")
    usdt_count = sum(1 for row in rows if row.quote_symbol == "USDT")
    if usdc_count + usdt_count != len(rows):
        raise DexPoolRegistryError(
            "internal orientation invariant failed",
            context={"usdc": usdc_count, "usdt": usdt_count, "total": len(rows)},
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    relative_path = DEX_POOL_REGISTRY_RELATIVE_PATH
    output_path = out_dir / relative_path
    sha256, byte_size, row_count = write_registry_parquet(output_path, rows)
    if row_count != len(rows):
        raise DexPoolRegistryError(
            "written registry row count mismatch",
            context={"written": row_count, "expected": len(rows)},
        )

    code_id = _require_code_commit(code_commit)
    cfg_payload: dict[str, Any] = {
        "dataset_type": DEX_POOL_REGISTRY_DATASET_TYPE,
        "schema_name": DEX_POOL_REGISTRY_SCHEMA_NAME,
        "schema_version": DEX_POOL_REGISTRY_SCHEMA_VERSION,
        "transform_name": DEX_POOL_REGISTRY_TRANSFORM_NAME,
        "transform_version": DEX_POOL_REGISTRY_TRANSFORM_VERSION,
        "chain": ETHEREUM_CHAIN,
        "protocol": UNISWAP_V2_PROTOCOL,
        "factory": UNISWAP_V2_FACTORY,
        "accepted_stable_quotes": {
            symbol: address
            for address, symbol in sorted(
                ((addr, sym) for addr, sym in ACCEPTED_STABLE_QUOTES.items()),
                key=lambda item: item[1],
            )
        },
        "selection_rule": "exactly_one_accepted_stable_quote",
        "orientation_rule": "non_stable_base_stable_quote",
        "source_availability_lag_hours": int(SOURCE_AVAILABILITY_LAG.total_seconds() // 3600),
        "source_dataset_id": source_dataset_id,
        "source_dataset_type": SOURCE_PAIR_CREATED_DATASET_TYPE,
        "require_pinned_source": require_pinned_source,
        "pinned_pair_created_dataset_id": PINNED_PAIR_CREATED_DATASET_ID,
    }
    cfg_hash = _resolve_config_sha256(config_sha256, payload=cfg_payload)

    event_start = min(row.event_time for row in rows)
    event_end = max(row.event_time for row in rows)
    availability_start = min(row.source_available_at for row in rows)
    availability_end = max(row.source_available_at for row in rows)

    schema_fingerprint = hashlib.sha256(
        json.dumps(
            {
                "name": DEX_POOL_REGISTRY_SCHEMA_NAME,
                "version": DEX_POOL_REGISTRY_SCHEMA_VERSION,
                "fields": list(DEX_POOL_REGISTRY_SCHEMA.names),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]

    plan = PublishPlan(
        dataset_type=DEX_POOL_REGISTRY_DATASET_TYPE,
        schema=SchemaIdentity(
            name=DEX_POOL_REGISTRY_SCHEMA_NAME,
            version=DEX_POOL_REGISTRY_SCHEMA_VERSION,
            fingerprint=schema_fingerprint,
        ),
        transform=TransformSpec(
            name=DEX_POOL_REGISTRY_TRANSFORM_NAME,
            version=DEX_POOL_REGISTRY_TRANSFORM_VERSION,
        ),
        code=CodeIdentity(commit=code_id),
        config=ConfigIdentity(config_sha256=cfg_hash),
        dependencies=(
            DependencyRef(
                id=source_dataset_id,
                kind=DependencyKind.DATASET,
                role="pair_created_census",
            ),
        ),
        output_sources={relative_path: output_path},
        output_specs=(
            OutputFileSpec(
                relative_path=relative_path,
                sha256=sha256,
                rows=row_count,
                bytes=byte_size,
                partition={
                    "chain": ETHEREUM_CHAIN,
                    "protocol": UNISWAP_V2_PROTOCOL,
                    "kind": "pool_registry",
                },
                rows_verified=True,
            ),
        ),
        statistics=DatasetStatistics(row_count=row_count, byte_size=byte_size),
        coverage=CoverageWindow(
            event_start=event_start,
            event_end=event_end,
            availability_start=availability_start,
            availability_end=availability_end,
        ),
        quality_status=QualityStatus.PASS,
        quality_summary={
            "chain": ETHEREUM_CHAIN,
            "protocol": UNISWAP_V2_PROTOCOL,
            "factory": UNISWAP_V2_FACTORY,
            "source_dataset_id": source_dataset_id,
            "source_row_count": len(records),
            "selected_pool_count": row_count,
            "usdc_quote_count": usdc_count,
            "usdt_quote_count": usdt_count,
            "selection_rule": "exactly_one_accepted_stable_quote",
            "source_availability_lag_hours": int(
                SOURCE_AVAILABILITY_LAG.total_seconds() // 3600
            ),
        },
        created_at=created_at,
        row_count_policy=RowCountPolicy.REQUIRE_VERIFIER,
        row_counters={relative_path: _parquet_row_counter},
        row_receipts={
            relative_path: RowCountReceipt(
                relative_path=relative_path,
                row_count=row_count,
                verifier_name="dex_pool_registry_row_count",
            )
        },
    )

    return DexPoolRegistryBuildResult(
        publish_plan=plan,
        rows=rows,
        output_path=output_path,
        source_dataset_id=source_dataset_id,
        selected_count=row_count,
        usdc_count=usdc_count,
        usdt_count=usdt_count,
        source_row_count=len(records),
    )


__all__ = [
    "ACCEPTED_STABLE_QUOTES",
    "DEX_POOL_REGISTRY_DATASET_TYPE",
    "DEX_POOL_REGISTRY_RELATIVE_PATH",
    "DEX_POOL_REGISTRY_SCHEMA",
    "DEX_POOL_REGISTRY_SCHEMA_NAME",
    "DEX_POOL_REGISTRY_SCHEMA_VERSION",
    "DEX_POOL_REGISTRY_TRANSFORM_NAME",
    "DEX_POOL_REGISTRY_TRANSFORM_VERSION",
    "DexPoolRegistryBuildResult",
    "DexPoolRegistryError",
    "DexPoolRegistryRow",
    "ETHEREUM_CHAIN",
    "PINNED_PAIR_CREATED_DATASET_ID",
    "SOURCE_AVAILABILITY_LAG",
    "SOURCE_PAIR_CREATED_DATASET_TYPE",
    "SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH",
    "UNISWAP_V2_FACTORY",
    "UNISWAP_V2_PROTOCOL",
    "USDC_ADDRESS",
    "USDT_ADDRESS",
    "build_dex_pool_registry",
    "is_direct_stable_quote_pair",
    "load_pair_created_records",
    "normalize_address",
    "orient_base_quote",
    "parse_iso_utc",
    "registry_row_from_pair_created",
    "registry_rows_to_table",
    "select_direct_stable_quote_pools",
    "source_available_at",
    "verify_pair_created_source_manifest",
    "write_registry_parquet",
]
