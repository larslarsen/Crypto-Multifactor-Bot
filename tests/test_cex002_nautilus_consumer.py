"""Pinned rc3 transport and strict CEX-002 component regressions.

These tests deliberately import real NautilusTrader.  A missing pinned test
environment is an error rather than a skipped consumer check.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from nautilus_trader.persistence import ParquetDataCatalog as RealCatalog

from cryptofactors.catalog.dataset.cex002_reference_release import (
    COMPONENT_KEYS,
    PROOF_KEYS,
    REQUIRED_DATASET_TYPES,
    ReleaseError,
    _verify_proof,
    _encode_logical,
    reference_proof_component,
)
from scripts.research import check_cex002_nautilus_consumer as checker


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _table_schema() -> pa.Schema:
    return pa.schema([
        pa.field("native_symbol", pa.dictionary(pa.int32(), pa.string()), nullable=False),
        pa.field("price", pa.decimal128(38, 18), nullable=True),
        pa.field("signed_fee", pa.decimal128(38, 18), nullable=True),
        pa.field("source_available_at", pa.timestamp("ns", tz="UTC"), nullable=True),
        pa.field("close_time", pa.int64(), nullable=True),
        pa.field("labels", pa.list_(pa.string()), nullable=True),
        pa.field("is_censored", pa.bool_(), nullable=True),
    ])


def _table_rows() -> list[dict[str, object]]:
    return [
        {
            "native_symbol": "BTCUSDT",
            "price": Decimal("99999999999999999999.999999999999999999"),
            "signed_fee": Decimal("-0.000000000000000001"),
            "source_available_at": None,
            "close_time": 1_700_000_000_000,
            "labels": ["realized", "unknown"],
            "is_censored": False,
        },
        {
            "native_symbol": "ETHUSDT",
            "price": Decimal("0E-18"),
            "signed_fee": None,
            "source_available_at": 1_700_000_000_000_000_123,
            "close_time": None,
            "labels": [],
            "is_censored": True,
        },
    ]


def _values(schema: pa.Schema, rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
    table = pa.Table.from_pylist(rows, schema=schema)
    columns = [
        table.column(index).cast(pa.int64()).to_pylist()
        if pa.types.is_timestamp(field.type) else table.column(index).to_pylist()
        for index, field in enumerate(schema)
    ]
    return [tuple(column[index] for column in columns) for index in range(len(rows))]


def _scratch(tmp_path: Path) -> Path:
    root = tmp_path / "scratch"
    root.mkdir()
    return root


def test_real_custom_catalog_preserves_precision_null_dictionary_list_and_ns(tmp_path: Path) -> None:
    schema = _table_schema()
    values = _values(schema, _table_rows())
    with localcontext() as context:
        context.prec = 6
        returned = checker._roundtrip_batch(
            _scratch(tmp_path), 0, schema, list(enumerate(values)), native_bars=False,
        )
    assert returned == list(enumerate(values))
    assert returned[0][1][3] is None
    assert returned[1][1][3] == 1_700_000_000_000_000_123
    assert returned[0][1][2] == Decimal("-0.000000000000000001")
    assert returned[1][1][1] == Decimal("0E-18")
    assert checker._scratch_bytes(tmp_path / "scratch") == 0
    assert not list((tmp_path / "scratch").iterdir())


def test_reference_component_matches_independent_actual_catalog_readback(tmp_path: Path) -> None:
    schema = _table_schema()
    path = tmp_path / "source.parquet"
    pq.write_table(pa.Table.from_pylist(_table_rows(), schema=schema), path)
    source_bytes = path.read_bytes()
    spec = SimpleNamespace(relative_path="tiny/source.parquet", rows=2,
                           bytes=len(source_bytes), sha256=_sha(source_bytes))
    component, sequence = checker._stream_table(
        _scratch(tmp_path), 0, path, spec, native_bars=False,
    )
    assert sequence == 1
    assert set(component) == COMPONENT_KEYS
    assert component == reference_proof_component(path, spec.relative_path, "table")
    assert component["source_value_sha256"] == component["roundtrip_value_sha256"]


def test_zero_row_gap_and_metadata_have_honest_identity(tmp_path: Path) -> None:
    schema = pa.schema([pa.field("missing_run_start_ms", pa.int64())])
    path = tmp_path / "zero.parquet"
    pq.write_table(pa.Table.from_pylist([], schema=schema), path)
    body = path.read_bytes()
    spec = SimpleNamespace(relative_path="gap/zero.parquet", rows=0,
                           bytes=len(body), sha256=_sha(body))
    table, _ = checker._stream_table(_scratch(tmp_path), 0, path, spec, False)
    assert table == reference_proof_component(path, spec.relative_path, "table")
    assert table["time_absence_reason"] == "empty_component"
    metadata = checker._metadata_component(
        SimpleNamespace(relative_path="gap/evidence.json", rows=0, bytes=2, sha256=_sha(b"{}")),
    )
    assert metadata["value_identity"] == "metadata_bytes"
    assert metadata["readback_row_count"] == 0
    assert metadata["time_absence_reason"] == "non_temporal_component"


def _bar_schema() -> pa.Schema:
    return pa.schema([
        pa.field("venue_symbol", pa.string()),
        pa.field("open_time", pa.int64()), pa.field("close_time", pa.int64()),
        *[pa.field(name, pa.decimal128(38, 18)) for name in ("open", "high", "low", "close", "volume")],
        pa.field("canonical_instrument_id", pa.string()),
        pa.field("source_available_at", pa.timestamp("ns", tz="UTC")),
    ])


def test_real_native_bar_and_lossless_custom_bar_roundtrip(tmp_path: Path) -> None:
    schema = _bar_schema()
    row = _values(schema, [{
        "venue_symbol": "BTCUSDT", "open_time": 1_700_000_000_000,
        "close_time": 1_700_003_599_999,
        "open": Decimal("100.000000000000000000"),
        "high": Decimal("101.000000000000000000"),
        "low": Decimal("99.000000000000000000"),
        "close": Decimal("100.500000000000000000"),
        "volume": Decimal("2.000000000000000000"),
        "canonical_instrument_id": None, "source_available_at": None,
    }])[0]
    second = _values(schema, [{
        "venue_symbol": "BTCUSDT", "open_time": 1_700_003_600_000,
        "close_time": 1_700_007_199_999,
        "open": Decimal("100.5"), "high": Decimal("102.25"),
        "low": Decimal("100"), "close": Decimal("101.125"),
        "volume": Decimal("0.125"), "canonical_instrument_id": None,
        "source_available_at": None,
    }])[0]
    returned = checker._roundtrip_batch(_scratch(tmp_path), 0, schema, [(0, row), (1, second)], native_bars=True)
    assert returned == [(0, row), (1, second)]
    assert returned[0][1][-2:] == (None, None)
    native = checker._native_bar(row, schema, 1_800_000_000_000_000_000)
    assert native.ts_event == 1_700_003_599_999_000_000
    assert native.ts_init == 1_800_000_000_000_000_000
    assert native.bar_type.instrument_id.symbol.value == "BTCUSDT"


@pytest.mark.parametrize("fault", ["omitted", "duplicate", "changed", "reordered", "substituted"])
def test_corrupt_actual_catalog_results_fail_and_leave_private_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    schema = pa.schema([pa.field("value", pa.int64())])
    rows = [(0, (1,)), (1, (2,))]

    class FaultCatalog:
        def __init__(self, base_path: str) -> None:
            self.real = RealCatalog(base_path)

        def write_custom_data(self, values: object) -> str:
            return self.real.write_custom_data(values)

        def query_custom_data(self, *args: object, **kwargs: object) -> list[object]:
            result = list(self.real.query_custom_data(*args, **kwargs))
            if fault == "omitted":
                return result[:1]
            if fault == "duplicate":
                return [result[0], result[0]]
            if fault == "reordered":
                return list(reversed(result))
            wrapper = result[0]
            original = wrapper.data
            payload = "[999]" if fault == "changed" else "[2]"
            replacement = checker.Cex002ReferenceRow(
                original.ordinal, payload, _sha(payload.encode()), original.ts_event, original.ts_init,
            )
            result[0] = checker.CustomData(wrapper.data_type, replacement)
            return result

    monkeypatch.setattr(checker, "ParquetDataCatalog", FaultCatalog)
    scratch = _scratch(tmp_path)
    if fault == "reordered":
        # Explicit source ordinals authorize reassembly, never positional trust.
        assert checker._roundtrip_batch(scratch, 0, schema, rows, native_bars=False) == rows
        return
    with pytest.raises(checker.ConsumerCheckError):
        checker._roundtrip_batch(scratch, 0, schema, rows, native_bars=False)
    assert checker._scratch_bytes(scratch) > 0


def test_ordinal_and_typed_value_changes_do_not_share_digest() -> None:
    schema = pa.schema([pa.field("x", pa.decimal128(38, 18))])
    left = checker._row_tokens((Decimal("-0.000000000000000001"),), schema)
    right = checker._row_tokens((Decimal("0.000000000000000001"),), schema)
    assert left != right
    assert left == _encode_logical(Decimal("-0.000000000000000001"), schema.field(0).type)
    payload = checker._row_payload((Decimal("-0.000000000000000001"),), schema)
    assert checker._decoded_payload(payload, schema) == (Decimal("-0.000000000000000001"),)


def test_batch_size_and_scratch_cap_reject_before_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    schema = pa.schema([pa.field("blob", pa.string())])
    scratch = _scratch(tmp_path)
    with pytest.raises(checker.ConsumerCheckError, match="row bound"):
        checker._roundtrip_batch(scratch, 0, schema, [(i, ("x",)) for i in range(checker.MAX_ROWS + 1)], native_bars=False)
    monkeypatch.setattr(checker, "SCRATCH_CAP_BYTES", 20)
    with pytest.raises(checker.ConsumerCheckError, match="prewrite"):
        checker._roundtrip_batch(scratch, 1, schema, [(0, ("x",))], native_bars=False)


def test_proof_stage_no_clobber_and_interruption_never_exposes_pass(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / checker.BUNDLE_ROOT_RELATIVE).mkdir(parents=True)
    stage, stream = checker._proof_stage(repo)
    payload = b'{"status":"PASS"}\n'
    digest = hashlib.sha256()
    assert checker._write_proof_chunk(stream, payload, digest, 0) == len(payload)
    stream.close()
    assert not (stage.parent / f"{digest.hexdigest()}.json").exists()
    sealed = checker._seal_proof(stage, digest.hexdigest(), len(payload))
    assert sealed.read_bytes() == payload
    second, stream = checker._proof_stage(repo)
    stream.write(payload)
    stream.close()
    with pytest.raises(checker.ConsumerCheckError, match="collision"):
        checker._seal_proof(second, digest.hexdigest(), len(payload))
    assert sealed.read_bytes() == payload
    assert second.exists()  # failure preserves partial state


def test_version_candidate_checker_and_unsafe_scratch_refuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(checker.ConsumerCheckError, match="candidate SHA"):
        checker.check_release(repo, "0" * 64, "a" * 64, tmp_path / "scratch")
    monkeypatch.setattr(checker.importlib.metadata, "version", lambda _name: "wrong")
    with pytest.raises(checker.ConsumerCheckError, match="Nautilus version"):
        checker.check_release(repo, checker.CANDIDATE_SHA256, "a" * 64, tmp_path / "scratch")
    with pytest.raises(checker.ConsumerCheckError, match="scratch root must be separate"):
        checker._fresh_scratch(repo / "inside", repo)
    link = tmp_path / "link"
    link.symlink_to(repo)
    with pytest.raises(checker.ConsumerCheckError):
        checker._fresh_scratch(link, repo)


def _mini_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, tuple[object, ...]]:
    """A private eleven-manifest seam; production counts and pins remain fixed."""
    repo = tmp_path / "repo"
    (repo / checker.BUNDLE_ROOT_RELATIVE).mkdir(parents=True)
    code = object()
    manifests = []
    for index, dataset_type in enumerate(REQUIRED_DATASET_TYPES):
        if dataset_type == "binance_usdm_bar_1h":
            schema = pa.schema([field for field in _bar_schema() if not pa.types.is_timestamp(field.type)])
            rows = [{
                "venue_symbol": "BTCUSDT", "open_time": 1_700_000_000_000,
                "close_time": 1_700_003_599_999,
                "open": Decimal("100"), "high": Decimal("101"),
                "low": Decimal("99"), "close": Decimal("100.5"),
                "volume": Decimal("2"), "canonical_instrument_id": None,
            }]
        else:
            schema = pa.schema([
                pa.field("component", pa.string()),
                pa.field("signed_fee", pa.decimal128(38, 18)),
                pa.field("source_available_at", pa.string()),
            ])
            rows = [{"component": dataset_type, "signed_fee": Decimal("-0.000000000000000001"),
                     "source_available_at": None}]
        base = repo / "data" / "fixture" / str(index)
        base.mkdir(parents=True)
        table_path = base / "table.parquet"
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), table_path)
        metadata_path = base / "lineage.json"
        metadata_path.write_bytes(b'{"source_available_at":null}\n')
        table_bytes = table_path.read_bytes()
        metadata_bytes = metadata_path.read_bytes()
        ref = "a" * 64
        table_spec = SimpleNamespace(
            relative_path=table_path.relative_to(repo).as_posix(), sha256=_sha(table_bytes),
            bytes=len(table_bytes), rows=1,
            partition={"kind": "table", "schema_ref": ref, "role": "partition",
                       "component": "" if dataset_type == "binance_usdm_bar_1h" else dataset_type},
        )
        metadata_spec = SimpleNamespace(
            relative_path=metadata_path.relative_to(repo).as_posix(), sha256=_sha(metadata_bytes),
            bytes=len(metadata_bytes), rows=0,
            partition={"kind": "metadata", "role": "lineage"},
        )
        contracts = {ref: tuple((field.name, str(field.type), field.nullable) for field in schema)}
        files = [table_spec]
        if dataset_type == "binance_usdm_bar_1h":
            dictionary = pa.dictionary(pa.int32(), pa.string())
            gap_schema = pa.schema([
                pa.field("venue", dictionary, nullable=False),
                pa.field("native_symbol", dictionary, nullable=False),
                pa.field("canonical_instrument_id", dictionary),
                pa.field("canonical_instrument_version_id", dictionary),
                pa.field("reference_identity_state", dictionary, nullable=False),
                pa.field("required_product", dictionary, nullable=False),
                pa.field("utc_month", dictionary, nullable=False),
                pa.field("missing_run_start_ms", pa.int64()),
                pa.field("missing_run_end_ms", pa.int64()),
                pa.field("expected_grid_count", pa.int64(), nullable=False),
                pa.field("gap_kind", dictionary, nullable=False),
                pa.field("reason", dictionary, nullable=False),
            ])
            gap_path = base / "quality-gap.parquet"
            pq.write_table(pa.Table.from_pylist([{
                "venue": "BINANCE_USDM", "native_symbol": "BTCUSDT",
                "canonical_instrument_id": None, "canonical_instrument_version_id": None,
                "reference_identity_state": "unmapped",
                "required_product": dataset_type, "utc_month": "2024-01",
                "missing_run_start_ms": 1_704_067_200_000,
                "missing_run_end_ms": 1_704_067_200_000,
                "expected_grid_count": 1, "gap_kind": "missing_hour_run",
                "reason": "source_missing",
            }], schema=gap_schema), gap_path)
            gap_bytes = gap_path.read_bytes()
            gap_ref = "b" * 64
            contracts[gap_ref] = tuple((field.name, str(field.type), field.nullable) for field in gap_schema)
            files.append(SimpleNamespace(
                relative_path=gap_path.relative_to(repo).as_posix(), sha256=_sha(gap_bytes),
                bytes=len(gap_bytes), rows=1,
                partition={"kind": "table", "schema_ref": gap_ref, "role": "partition",
                           "component": "quality_gap"},
            ))
        files.append(metadata_spec)
        manifests.append(SimpleNamespace(dataset_id=f"ds_{index:064x}", dataset_type=dataset_type,
                                         files=tuple(files), code=code, contracts=contracts))
    sealed = tuple(manifests)
    descriptor = {"consumable": False, "fixture": "eleven complete datasets"}
    monkeypatch.setattr(checker, "EXPECTED_FILES", 23)
    monkeypatch.setattr(checker, "EXPECTED_ROWS", 12)
    monkeypatch.setattr(checker, "seal_code_identity", lambda *_args, **_kwargs: code)
    monkeypatch.setattr(checker, "_load_prepared", lambda *_args: (descriptor, sealed))
    monkeypatch.setattr(checker, "_registry_contracts", lambda manifest: manifest.contracts)
    monkeypatch.setattr(checker, "_release_charge", lambda *_args: (0, 0, 0, {"sqlite_bytes": 0}))
    monkeypatch.setattr(checker, "_reserve", lambda *_args: None)
    return repo, sealed


def test_complete_eleven_dataset_proof_passes_strict_existing_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, manifests = _mini_release(tmp_path, monkeypatch)
    source_sha = _sha(Path(checker.__file__).read_bytes())
    proof_path, proof_sha = checker.check_release(
        repo, checker.CANDIDATE_SHA256, source_sha, tmp_path / "scratch",
    )
    body = proof_path.read_bytes()
    assert _sha(body) == proof_sha
    proof = json.loads(body)
    assert set(proof) == PROOF_KEYS
    assert proof["status"] == "PASS" and proof["scope"] == "complete_release"
    assert [entry["dataset_id"] for entry in proof["datasets"]] == [manifest.dataset_id for manifest in manifests]
    assert [len(entry["components"]) for entry in proof["datasets"]] == [2, 3] + [2] * 9
    assert sum(component["source_row_count"] for entry in proof["datasets"] for component in entry["components"]) == 12
    gap_spec = manifests[1].files[1]
    gap_component = proof["datasets"][1]["components"][1]
    assert gap_component == reference_proof_component(repo / gap_spec.relative_path,
                                                    gap_spec.relative_path, "table")
    assert gap_component["source_value_sha256"] == gap_component["roundtrip_value_sha256"]
    _verify_proof(
        repo, proof, manifests, candidate_sha256=checker.CANDIDATE_SHA256,
        checker_sha256=source_sha, nautilus_version=checker.NAUTILUS_VERSION,
    )


@pytest.mark.parametrize("fault", ["missing_component", "unknown_component", "missing_role", "unknown_role", "malformed_primary"])
def test_bar_table_routing_refuses_unaccepted_tags_and_malformed_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    repo, manifests = _mini_release(tmp_path, monkeypatch)
    bar = manifests[1]
    primary = bar.files[0]
    gap = bar.files[1]
    if fault == "missing_component":
        del gap.partition["component"]
    elif fault == "unknown_component":
        gap.partition["component"] = "unknown_gap"
    elif fault == "missing_role":
        del gap.partition["role"]
    elif fault == "unknown_role":
        gap.partition["role"] = "metadata"
    else:
        path = repo / primary.relative_path
        shortened = pq.read_table(path).drop(["volume"])
        pq.write_table(shortened, path)
        changed = path.read_bytes()
        primary.sha256, primary.bytes = _sha(changed), len(changed)
        bar.contracts[primary.partition["schema_ref"]] = tuple(
            (field.name, str(field.type), field.nullable) for field in shortened.schema
        )
    message = ("mandatory native projection" if fault == "malformed_primary"
               else "bar table role" if fault.endswith("role") else "bar table component")
    with pytest.raises(checker.ConsumerCheckError, match=message):
        checker.check_release(repo, checker.CANDIDATE_SHA256,
                              _sha(Path(checker.__file__).read_bytes()), tmp_path / "scratch")
    proofs = repo / checker.BUNDLE_ROOT_RELATIVE / ".proofs"
    assert not list(proofs.glob("*.json"))
    assert len(list(proofs.glob(".stage-*"))) == 1


@pytest.mark.parametrize("fault", ["source", "manifest", "schema", "transport", "code", "seal", "seal_after_rename"])
def test_late_failure_cannot_seal_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    repo, manifests = _mini_release(tmp_path, monkeypatch)
    source_sha = _sha(Path(checker.__file__).read_bytes())
    if fault == "source":
        original = checker._load_prepared
        calls = 0

        def late_source(*args: object) -> object:
            nonlocal calls
            calls += 1
            if calls == 2:
                path = repo / manifests[0].files[0].relative_path
                path.write_bytes(path.read_bytes() + b"changed")
            return original(*args)

        monkeypatch.setattr(checker, "_load_prepared", late_source)
    elif fault == "manifest":
        original = checker._load_prepared
        calls = 0

        def late_manifest(*args: object) -> object:
            nonlocal calls
            calls += 1
            if calls == 2:
                return {"consumable": False, "fixture": "changed"}, manifests
            return original(*args)

        monkeypatch.setattr(checker, "_load_prepared", late_manifest)
    elif fault == "schema":
        original = checker._registry_contracts
        monkeypatch.setattr(checker, "_registry_contracts", lambda manifest: {
            "a" * 64: (("wrong_column", "int64", True),)
        } if manifest is manifests[0] else original(manifest))
    elif fault == "transport":
        original = checker._roundtrip_batch

        def refused(*args: object, **kwargs: object) -> object:
            original(*args, **kwargs)
            raise checker.ConsumerCheckError("injected post-readback interruption")

        monkeypatch.setattr(checker, "_roundtrip_batch", refused)
    elif fault == "code":
        original = checker.seal_code_identity
        calls = 0

        def late_code(*args: object, **kwargs: object) -> object:
            nonlocal calls
            calls += 1
            return object() if calls == 2 else original(*args, **kwargs)

        monkeypatch.setattr(checker, "seal_code_identity", late_code)
    else:
        original = checker._seal_proof

        def failed_seal(*args: object, **kwargs: object) -> object:
            if fault == "seal_after_rename":
                original(*args, **kwargs)
            raise checker.ConsumerCheckError("injected proof seal failure")

        monkeypatch.setattr(checker, "_seal_proof", failed_seal)
    expected = {
        "source": (checker.ConsumerCheckError, "reference changed before proof seal"),
        "manifest": (checker.ConsumerCheckError, "candidate or manifest changed before proof seal"),
        "schema": (ReleaseError, "Parquet footer schema mismatch"),
        "transport": (checker.ConsumerCheckError, "injected post-readback interruption"),
        "code": (checker.ConsumerCheckError, "runtime source or code identity changed before proof seal"),
        "seal": (checker.ConsumerCheckError, "injected proof seal failure"),
        "seal_after_rename": (checker.ConsumerCheckError, "injected proof seal failure"),
    }
    error_type, message = expected[fault]
    with pytest.raises(error_type, match=message):
        checker.check_release(repo, checker.CANDIDATE_SHA256, source_sha, tmp_path / "scratch")
    proofs = repo / checker.BUNDLE_ROOT_RELATIVE / ".proofs"
    assert not list(proofs.glob("*.json"))
    stages = list(proofs.glob(".stage-*"))
    assert len(stages) == 1
    assert b'"status":"HOLD"' in stages[0].read_bytes()


def test_checker_source_pin_refuses_drift_before_scratch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(checker.ConsumerCheckError, match="checker source SHA"):
        checker.check_release(repo, checker.CANDIDATE_SHA256, "a" * 64, tmp_path / "scratch")
    assert not (tmp_path / "scratch").exists()
