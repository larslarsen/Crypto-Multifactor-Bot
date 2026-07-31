"""DEX-003 — focused tests for the deterministic ``dex_pool_registry`` transform.

Covers direct USDC/USDT selection, frozen base/quote orientation, birth/block
identity, ADR-0015 ``source_available_at`` (+24h), ``retrieved_at`` lineage,
raw/dataset lineage, fail-closed source verification, and the pinned-census gate.

No network. No Swap/Sync. No catalog publication (Jr owns integration runs).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cryptofactors.catalog.dataset.models import (
    CodeIdentity,
    ConfigIdentity,
    CoverageWindow,
    DatasetManifest,
    DatasetStatistics,
    DependencyKind,
    OutputFileSpec,
    PublicationMetadata,
    QualityStatus,
    SchemaIdentity,
    TransformSpec,
)
from cryptofactors.catalog.dataset.outputs import stream_sha256_and_size
from cryptofactors.market.dex_pool_registry import (
    DEX_POOL_REGISTRY_DATASET_TYPE,
    DEX_POOL_REGISTRY_RELATIVE_PATH,
    DEX_POOL_REGISTRY_SCHEMA,
    DEX_POOL_REGISTRY_SCHEMA_NAME,
    DEX_POOL_REGISTRY_SCHEMA_VERSION,
    DEX_POOL_REGISTRY_TRANSFORM_NAME,
    DEX_POOL_REGISTRY_TRANSFORM_VERSION,
    PINNED_PAIR_CREATED_DATASET_ID,
    SOURCE_AVAILABILITY_LAG,
    SOURCE_PAIR_CREATED_DATASET_TYPE,
    SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH,
    SOURCE_PAIR_CREATED_SCHEMA_NAME,
    SOURCE_PAIR_CREATED_SCHEMA_VERSION,
    UNISWAP_V2_FACTORY,
    USDC_ADDRESS,
    USDT_ADDRESS,
    DexPoolRegistryError,
    build_dex_pool_registry,
    is_direct_stable_quote_pair,
    orient_base_quote,
    registry_row_from_pair_created,
    select_direct_stable_quote_pools,
    source_available_at,
    verify_pair_created_source_manifest,
)

TEST_CODE_COMMIT = "0" * 40
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
WBTC = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
DAI = "0x6b175474e89094c44da98b954eedeac495271d0f"

EVENT_TIME = datetime(2020, 5, 5, 20, 22, 25, tzinfo=UTC)
RETRIEVED_AT = datetime(2026, 7, 29, 10, 8, 43, 223374, tzinfo=UTC)

_PAIR_CREATED_SCHEMA = pa.schema(
    [
        ("chain", pa.string()),
        ("factory", pa.string()),
        ("pair", pa.string()),
        ("token0", pa.string()),
        ("token1", pa.string()),
        ("block_number", pa.int64()),
        ("block_hash", pa.string()),
        ("block_timestamp", pa.int64()),
        ("tx_hash", pa.string()),
        ("tx_index", pa.int64()),
        ("log_index", pa.int64()),
        ("event_time", pa.string()),
        ("availability_time", pa.string()),
        ("raw_object_id", pa.string()),
        ("block_raw_object_id", pa.string()),
    ]
)


def _addr(byte: int) -> str:
    return "0x" + f"{byte:02x}" * 20


def _bytes32(byte: int) -> str:
    return "0x" + f"{byte:02x}" * 32


def _raw_id(byte: int) -> str:
    return "raw_" + f"{byte:02x}" * 32


def _dataset_id(byte: int = 0xAB) -> str:
    return "ds_" + f"{byte:02x}" * 32


def _pair_created_row(
    *,
    pair: str,
    token0: str,
    token1: str,
    block_number: int = 10_008_355,
    tx_index: int = 1,
    log_index: int = 2,
    event_time: datetime = EVENT_TIME,
    availability_time: datetime = RETRIEVED_AT,
    tx_hash: str | None = None,
    chain: str = "ethereum",
    factory: str = UNISWAP_V2_FACTORY,
) -> dict[str, Any]:
    return {
        "chain": chain,
        "factory": factory,
        "pair": pair,
        "token0": token0,
        "token1": token1,
        "block_number": block_number,
        "block_hash": _bytes32(0x11),
        "block_timestamp": int(event_time.timestamp()),
        "tx_hash": tx_hash or _bytes32(0x22),
        "tx_index": tx_index,
        "log_index": log_index,
        "event_time": event_time.isoformat(),
        "availability_time": availability_time.isoformat(),
        "raw_object_id": _raw_id(0xAA),
        "block_raw_object_id": _raw_id(0xBB),
    }


def _census_fixture() -> list[dict[str, Any]]:
    """Synthetic census: USDC pool, USDT pool, dual-stable, non-stable, and noise."""
    return [
        _pair_created_row(
            pair=_addr(0xB4),
            token0=USDC_ADDRESS,
            token1=WETH,
            block_number=10_008_355,
            tx_index=1,
            log_index=2,
        ),
        _pair_created_row(
            pair=_addr(0xC1),
            token0=WBTC,
            token1=USDT_ADDRESS,
            block_number=10_100_000,
            tx_index=3,
            log_index=4,
            event_time=EVENT_TIME + timedelta(days=1),
            tx_hash=_bytes32(0x33),
        ),
        # Dual stable — must be excluded.
        _pair_created_row(
            pair=_addr(0xD1),
            token0=USDC_ADDRESS,
            token1=USDT_ADDRESS,
            block_number=10_200_000,
            tx_index=5,
            log_index=6,
            tx_hash=_bytes32(0x44),
        ),
        # Neither side stable — excluded.
        _pair_created_row(
            pair=_addr(0xE1),
            token0=WETH,
            token1=WBTC,
            block_number=10_300_000,
            tx_index=7,
            log_index=8,
            tx_hash=_bytes32(0x55),
        ),
        # USDT as token0 (orientation reverse of token order).
        _pair_created_row(
            pair=_addr(0xF1),
            token0=USDT_ADDRESS,
            token1=DAI,
            block_number=10_050_000,
            tx_index=9,
            log_index=10,
            tx_hash=_bytes32(0x66),
        ),
    ]


def _write_pair_created_parquet(path: Path, rows: list[dict[str, Any]]) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=_PAIR_CREATED_SCHEMA)
    pq.write_table(table, path, compression="zstd")
    return stream_sha256_and_size(path)


def _source_manifest(
    events_path: Path,
    *,
    dataset_id: str | None = None,
    rows: int | None = None,
    quality: QualityStatus = QualityStatus.PASS,
    dataset_type: str = SOURCE_PAIR_CREATED_DATASET_TYPE,
    schema_name: str = SOURCE_PAIR_CREATED_SCHEMA_NAME,
    schema_version: str = SOURCE_PAIR_CREATED_SCHEMA_VERSION,
    relative_path: str = SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH,
    sha256: str | None = None,
    byte_size: int | None = None,
) -> DatasetManifest:
    observed_sha, observed_bytes = stream_sha256_and_size(events_path)
    n_rows = rows if rows is not None else int(pq.ParquetFile(str(events_path)).metadata.num_rows)
    return DatasetManifest(
        dataset_id=dataset_id or _dataset_id(),
        dataset_type=dataset_type,
        schema=SchemaIdentity(name=schema_name, version=schema_version),
        transform=TransformSpec(name="uniswap_v2_pair_created_ingest", version="1"),
        code=CodeIdentity(commit=TEST_CODE_COMMIT),
        config=ConfigIdentity(config_sha256="c" * 64),
        dependencies=(),
        files=(
            OutputFileSpec(
                relative_path=relative_path,
                sha256=sha256 or observed_sha,
                rows=n_rows,
                bytes=byte_size if byte_size is not None else observed_bytes,
                rows_verified=True,
            ),
        ),
        statistics=DatasetStatistics(
            row_count=n_rows,
            byte_size=byte_size if byte_size is not None else observed_bytes,
        ),
        coverage=CoverageWindow(
            event_start=EVENT_TIME,
            event_end=EVENT_TIME + timedelta(days=30),
            availability_start=RETRIEVED_AT,
            availability_end=RETRIEVED_AT,
        ),
        quality_status=quality,
        quality_summary={"chain": "ethereum", "event": "PairCreated", "row_count": n_rows},
        publication=PublicationMetadata(created_at=datetime(2026, 7, 30, tzinfo=UTC)),
        supersedes_dataset_id=None,
        manifest_sha256="m" * 64,
    )


# ---------------------------------------------------------------------------
# Pure orientation / selection
# ---------------------------------------------------------------------------


def test_orient_usdc_as_token0_freezes_base_on_token1() -> None:
    oriented = orient_base_quote(USDC_ADDRESS, WETH)
    assert oriented is not None
    base, quote, symbol = oriented
    assert symbol == "USDC"
    assert quote == USDC_ADDRESS
    assert base == WETH


def test_orient_usdt_as_token1_freezes_base_on_token0() -> None:
    oriented = orient_base_quote(WBTC, USDT_ADDRESS)
    assert oriented is not None
    base, quote, symbol = oriented
    assert symbol == "USDT"
    assert quote == USDT_ADDRESS
    assert base == WBTC


def test_orient_rejects_dual_stable_and_non_stable() -> None:
    assert orient_base_quote(USDC_ADDRESS, USDT_ADDRESS) is None
    assert orient_base_quote(WETH, WBTC) is None
    assert not is_direct_stable_quote_pair(USDC_ADDRESS, USDT_ADDRESS)
    assert not is_direct_stable_quote_pair(WETH, WBTC)
    assert is_direct_stable_quote_pair(USDC_ADDRESS, WETH)


def test_orient_identical_tokens_fail_closed() -> None:
    with pytest.raises(DexPoolRegistryError, match="must differ"):
        orient_base_quote(USDC_ADDRESS, USDC_ADDRESS)


def test_source_available_at_is_event_time_plus_24h() -> None:
    assert SOURCE_AVAILABILITY_LAG == timedelta(hours=24)
    assert source_available_at(EVENT_TIME) == EVENT_TIME + timedelta(hours=24)


def test_select_keeps_only_direct_stable_quote_pools() -> None:
    rows = select_direct_stable_quote_pools(
        _census_fixture(), pair_created_dataset_id=_dataset_id()
    )
    assert len(rows) == 3
    symbols = {row.quote_symbol for row in rows}
    assert symbols == {"USDC", "USDT"}
    pools = {row.pool_address for row in rows}
    assert _addr(0xB4) in pools  # USDC/WETH
    assert _addr(0xC1) in pools  # WBTC/USDT
    assert _addr(0xF1) in pools  # USDT/DAI
    assert _addr(0xD1) not in pools  # dual stable
    assert _addr(0xE1) not in pools  # non-stable


def test_select_orders_by_birth_identity() -> None:
    rows = select_direct_stable_quote_pools(
        _census_fixture(), pair_created_dataset_id=_dataset_id()
    )
    keys = [(r.creation_block, r.tx_index, r.log_index, r.pool_address) for r in rows]
    assert keys == sorted(keys)


def test_registry_row_preserves_birth_block_and_raw_lineage() -> None:
    raw = _pair_created_row(pair=_addr(0xB4), token0=USDC_ADDRESS, token1=WETH)
    ds = _dataset_id()
    row = registry_row_from_pair_created(raw, pair_created_dataset_id=ds)
    assert row is not None
    assert row.chain == "ethereum"
    assert row.protocol == "uniswap_v2"
    assert row.factory == UNISWAP_V2_FACTORY
    assert row.pool_address == _addr(0xB4)
    assert row.token0 == USDC_ADDRESS
    assert row.token1 == WETH
    assert row.base_token == WETH
    assert row.quote_token == USDC_ADDRESS
    assert row.quote_symbol == "USDC"
    assert row.creation_block == 10_008_355
    assert row.block_hash == _bytes32(0x11)
    assert row.tx_hash == _bytes32(0x22)
    assert row.tx_index == 1
    assert row.log_index == 2
    assert row.event_time == EVENT_TIME
    assert row.source_available_at == EVENT_TIME + timedelta(hours=24)
    assert row.retrieved_at == RETRIEVED_AT
    assert row.raw_object_id == _raw_id(0xAA)
    assert row.block_raw_object_id == _raw_id(0xBB)
    assert row.pair_created_dataset_id == ds


def test_duplicate_pool_with_conflicting_birth_fails_closed() -> None:
    first = _pair_created_row(pair=_addr(0xB4), token0=USDC_ADDRESS, token1=WETH)
    second = dict(first, tx_hash=_bytes32(0x99))
    with pytest.raises(DexPoolRegistryError, match="conflicting birth identity"):
        select_direct_stable_quote_pools(
            [first, second], pair_created_dataset_id=_dataset_id()
        )


def test_exact_duplicate_birth_event_is_deduped() -> None:
    first = _pair_created_row(pair=_addr(0xB4), token0=USDC_ADDRESS, token1=WETH)
    rows = select_direct_stable_quote_pools(
        [first, dict(first)], pair_created_dataset_id=_dataset_id()
    )
    assert len(rows) == 1


def test_wrong_chain_or_factory_fails_closed() -> None:
    bad_chain = _pair_created_row(
        pair=_addr(0xB4), token0=USDC_ADDRESS, token1=WETH, chain="arbitrum"
    )
    with pytest.raises(DexPoolRegistryError, match="ethereum"):
        registry_row_from_pair_created(bad_chain, pair_created_dataset_id=_dataset_id())

    bad_factory = _pair_created_row(
        pair=_addr(0xB4),
        token0=USDC_ADDRESS,
        token1=WETH,
        factory="0x0000000000000000000000000000000000000001",
    )
    with pytest.raises(DexPoolRegistryError, match="canonical Uniswap V2 factory"):
        registry_row_from_pair_created(bad_factory, pair_created_dataset_id=_dataset_id())


# ---------------------------------------------------------------------------
# Source verification + build_dex_pool_registry
# ---------------------------------------------------------------------------


def test_build_registry_end_to_end(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events, dataset_id=_dataset_id(0x11))
    out = tmp_path / "out"

    result = build_dex_pool_registry(
        source_manifest=manifest,
        source_events_path=events,
        output_dir=out,
        code_commit=TEST_CODE_COMMIT,
    )

    assert result.selected_count == 3
    assert result.usdc_count == 1
    assert result.usdt_count == 2
    assert result.source_row_count == 5
    assert result.output_path == out / DEX_POOL_REGISTRY_RELATIVE_PATH
    assert result.output_path.is_file()

    table = pq.read_table(result.output_path)
    assert table.schema.equals(DEX_POOL_REGISTRY_SCHEMA)
    assert table.num_rows == 3
    assert set(table.column("quote_symbol").to_pylist()) == {"USDC", "USDT"}

    # Every row has lag and lineage invariants.
    for row in result.rows:
        assert row.source_available_at == row.event_time + timedelta(hours=24)
        assert row.pair_created_dataset_id == manifest.dataset_id
        assert row.raw_object_id.startswith("raw_")
        assert row.block_raw_object_id.startswith("raw_")
        assert row.base_token not in (USDC_ADDRESS, USDT_ADDRESS)
        assert row.quote_token in (USDC_ADDRESS, USDT_ADDRESS)

    plan = result.publish_plan
    assert plan.dataset_type == DEX_POOL_REGISTRY_DATASET_TYPE
    assert plan.schema.name == DEX_POOL_REGISTRY_SCHEMA_NAME
    assert plan.schema.version == DEX_POOL_REGISTRY_SCHEMA_VERSION
    assert plan.transform.name == DEX_POOL_REGISTRY_TRANSFORM_NAME
    assert plan.transform.version == DEX_POOL_REGISTRY_TRANSFORM_VERSION
    assert plan.quality_status is QualityStatus.PASS
    assert len(plan.dependencies) == 1
    dep = plan.dependencies[0]
    assert dep.id == manifest.dataset_id
    assert dep.kind is DependencyKind.DATASET
    assert dep.role == "pair_created_census"
    assert plan.statistics.row_count == 3
    assert plan.quality_summary["usdc_quote_count"] == 1
    assert plan.quality_summary["usdt_quote_count"] == 2
    assert plan.coverage.event_start is not None
    assert plan.coverage.availability_start is not None
    assert plan.coverage.availability_start == plan.coverage.event_start + timedelta(hours=24)


def test_build_rejects_empty_selection(tmp_path: Path) -> None:
    only_dual = [
        _pair_created_row(
            pair=_addr(0xD1),
            token0=USDC_ADDRESS,
            token1=USDT_ADDRESS,
        )
    ]
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, only_dual)
    manifest = _source_manifest(events)
    with pytest.raises(DexPoolRegistryError, match="zero pools"):
        build_dex_pool_registry(
            source_manifest=manifest,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
        )


def test_build_rejects_non_pass_source(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events, quality=QualityStatus.PASS_WITH_WARNINGS)
    with pytest.raises(DexPoolRegistryError, match="quality must be PASS"):
        build_dex_pool_registry(
            source_manifest=manifest,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
        )


def test_build_rejects_wrong_source_dataset_type(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events, dataset_type="something_else")
    with pytest.raises(DexPoolRegistryError, match="uniswap_v2_pair_created"):
        build_dex_pool_registry(
            source_manifest=manifest,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
        )


def test_build_rejects_sha256_mismatch(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events, sha256="0" * 64)
    with pytest.raises(DexPoolRegistryError, match="sha256"):
        build_dex_pool_registry(
            source_manifest=manifest,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
        )


def test_build_rejects_row_count_mismatch(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events)
    # Force statistics to lie without changing the file hash/size path used for
    # file-spec bytes (statistics.row_count is checked first).
    bad = dataclasses.replace(
        manifest,
        statistics=DatasetStatistics(row_count=999, byte_size=manifest.statistics.byte_size),
    )
    with pytest.raises(DexPoolRegistryError, match="row count"):
        build_dex_pool_registry(
            source_manifest=bad,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
        )


def test_require_pinned_source_gate(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    wrong = _source_manifest(events, dataset_id=_dataset_id(0x01))
    with pytest.raises(DexPoolRegistryError, match="pinned full PairCreated census"):
        build_dex_pool_registry(
            source_manifest=wrong,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit=TEST_CODE_COMMIT,
            require_pinned_source=True,
        )

    pinned = _source_manifest(events, dataset_id=PINNED_PAIR_CREATED_DATASET_ID)
    result = build_dex_pool_registry(
        source_manifest=pinned,
        source_events_path=events,
        output_dir=tmp_path / "out_pinned",
        code_commit=TEST_CODE_COMMIT,
        require_pinned_source=True,
    )
    assert result.source_dataset_id == PINNED_PAIR_CREATED_DATASET_ID
    assert result.selected_count == 3


def test_verify_manifest_requires_events_file_entry(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events, relative_path="wrong/path.parquet")
    with pytest.raises(DexPoolRegistryError, match="missing PairCreated events"):
        verify_pair_created_source_manifest(manifest)


def test_code_commit_required(tmp_path: Path) -> None:
    events = tmp_path / "events.parquet"
    _write_pair_created_parquet(events, _census_fixture())
    manifest = _source_manifest(events)
    with pytest.raises(DexPoolRegistryError, match="code_commit"):
        build_dex_pool_registry(
            source_manifest=manifest,
            source_events_path=events,
            output_dir=tmp_path / "out",
            code_commit="unknown",
        )


def test_address_normalization_is_case_insensitive() -> None:
    raw = _pair_created_row(
        pair="0xB4B4B4B4B4B4B4B4B4B4B4B4B4B4B4B4B4B4B4B4",
        token0="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        token1="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        factory="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    )
    row = registry_row_from_pair_created(raw, pair_created_dataset_id=_dataset_id())
    assert row is not None
    assert row.token0 == USDC_ADDRESS
    assert row.token1 == WETH
    assert row.factory == UNISWAP_V2_FACTORY
    assert row.pool_address == _addr(0xB4)


# ---------------------------------------------------------------------------
# Optional: real pinned census (skip if local store absent)
# ---------------------------------------------------------------------------


def _pinned_census_paths() -> tuple[Path, Path] | None:
    root = (
        Path("data/dex003_full/store/datasets/sha256/0e/ab")
        / PINNED_PAIR_CREATED_DATASET_ID
    )
    manifest = root / "manifest.json"
    events = root / SOURCE_PAIR_CREATED_EVENTS_RELATIVE_PATH
    if manifest.is_file() and events.is_file():
        return manifest, events
    return None


def test_pinned_census_counts_match_handoff_when_present(tmp_path: Path) -> None:
    paths = _pinned_census_paths()
    if paths is None:
        pytest.skip("pinned PairCreated census not present locally")

    from cryptofactors.catalog.dataset.parse import load_manifest_file

    manifest_path, events_path = paths
    manifest = load_manifest_file(manifest_path)
    result = build_dex_pool_registry(
        source_manifest=manifest,
        source_events_path=events_path,
        output_dir=tmp_path / "pinned_out",
        code_commit=TEST_CODE_COMMIT,
        require_pinned_source=True,
    )
    # CURRENT_TASK handoff counts.
    assert result.source_row_count == 516_111
    assert result.selected_count == 7_659
    assert result.usdc_count == 4_181
    assert result.usdt_count == 3_478
    assert result.publish_plan.quality_status is QualityStatus.PASS
    # Dual-stable Uniswap V2 USDC/USDT pair must remain excluded.
    dual = "0x3041cbd36888becc7bbcbc0045e3b1f144466f5f"
    assert all(row.pool_address != dual for row in result.rows)
