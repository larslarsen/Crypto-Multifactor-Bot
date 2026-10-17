"""Temporary-fixture tests for the bounded one-minute comparison sample."""

from __future__ import annotations

import calendar
import inspect
import io
import json
import stat
import zipfile
from pathlib import Path

import pytest

from cryptofactors.acquisition import binance_usdm_kline_comparison_sample as sample
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    KNOWN_ARCHIVE_SCHEMAS,
)

RETRIEVAL = "ZZ-RETRIEVAL-7f3a"


class MapTransport:
    def __init__(self, bodies: dict[str, sample.FetchResponse | bytes]):
        self.bodies = bodies
        self.calls: list[str] = []

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> sample.FetchResponse:
        self.calls.append(url)
        body = self.bodies[url]
        if isinstance(body, sample.FetchResponse):
            return body
        return sample.FetchResponse(200, url, body, len(body))


class ExplodingTransport:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, url: str, *, timeout: float, max_bytes: int) -> sample.FetchResponse:
        self.calls += 1
        raise AssertionError(url)


class _BytesReader:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._offset = 0

    def read(self, size: int) -> bytes:
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _minute(open_ms: int, **tokens: str) -> list[str]:
    values = {
        "open_time": str(open_ms),
        "open": "100",
        "high": "100",
        "low": "100",
        "close": "100",
        "volume": "1",
        "close_time": str(open_ms + 59_999),
        "quote_volume": "100",
        "count": "1",
        "taker_buy_volume": "0.4",
        "taker_buy_quote_volume": "40",
        "ignore": "7",
    }
    values.update(tokens)
    return [values[name] for name in sample.MINUTE_FIELDS]


def _csv(rows: list[list[str]], *, header: bool = False) -> bytes:
    lines = [",".join(sample.MINUTE_FIELDS)] if header else []
    lines.extend(",".join(row) for row in rows)
    return ("\n".join(lines) + "\n").encode()


def _zip(member: str, payload: bytes, *, stored: bool = False) -> bytes:
    buffer = io.BytesIO()
    mode = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(buffer, "w", compression=mode) as archive:
        archive.writestr(member, payload)
    return buffer.getvalue()


def _zipinfo(member: str, payload: bytes, info: zipfile.ZipInfo) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(info, payload)
    return buffer.getvalue()


def _policy(repo: Path, roles: tuple[sample.Role, ...], report_sha: str, **limits: int) -> sample.Policy:
    return sample.Policy(
        repo=repo,
        report_relative="qualification.json",
        report_sha256=report_sha,
        bar_root="products/bar",
        bar_completion="11" * 32,
        flow_root="products/flow",
        flow_completion="22" * 32,
        protected=("qualification.json", "products/bar", "products/flow", "generation0"),
        roles=roles,
        **limits,
    )


def _record(symbol: str, utc_date: str, regime: str, digest: str, size: int) -> dict[str, object]:
    key = sample.hourly_object_key(symbol, utc_date)
    return {
        "byte_size": size,
        "checksum_match": True,
        "family": "daily/klines",
        "key": key,
        "products": ["binance_usdm_bar_1h"],
        "provider_checksum": digest,
        "regime": regime,
        "sha256": digest,
        "symbol": symbol,
        "url": sample.official_object_url(key),
    }


def _write_report(repo: Path, records: list[dict[str, object]]) -> str:
    repo.mkdir(parents=True, exist_ok=True)
    body = sample.canonical_json({"samples": records})
    (repo / "qualification.json").write_bytes(body)
    return sample.sha256_hex(body)


def _objects(symbol: str, utc_date: str, rows: list[list[str]], *, header: bool = False) -> dict[str, bytes]:
    member = sample.minute_member_name(symbol, utc_date)
    key = sample.minute_object_key(symbol, utc_date)
    payload = _zip(member, _csv(rows, header=header))
    digest = sample.sha256_hex(payload)
    basename = key.rsplit("/", 1)[-1]
    sidecar = f"{digest}  {basename}\n".encode()
    return {
        sample.official_object_url(key): payload,
        sample.official_object_url(key + ".CHECKSUM"): sidecar,
    }


def _fetch_one(tmp_path: Path, *, rows: list[list[str]] | None = None, clock: str = RETRIEVAL):
    symbol, utc_date = "0GUSDT", "2024-06-01"
    start = sample.utc_day_start_ms(utc_date)
    minute_rows = rows if rows is not None else [_minute(start)]
    repo = tmp_path / "repo"
    digest = sample.sha256_hex(b"0GUSDT|2024-06-01")
    report_sha = _write_report(repo, [_record(symbol, utc_date, "early", digest, 128)])
    policy = _policy(repo, (sample.Role(symbol, utc_date, "early"),), report_sha)
    evidence = tmp_path / "evidence"
    transport = MapTransport(_objects(symbol, utc_date, minute_rows))
    result = sample.fetch_sample(
        policy,
        evidence,
        fetch=True,
        transport=transport,
        clock=lambda: clock,
    )
    return policy, evidence, transport, result


def test_production_policy_pins_constants_without_reading_the_report(tmp_path: Path) -> None:
    policy = sample.production_policy(tmp_path)
    assert policy.report_sha256 == sample.REPORT_SHA256
    assert policy.bar_completion == sample.BAR_COMPLETION
    assert policy.flow_completion == sample.FLOW_COMPLETION
    assert len(policy.roles) == 10
    assert sample.BAR_ROOT in policy.protected
    assert sample.FLOW_ROOT in policy.protected
    assert sample.GENERATION0_ROOT in policy.protected
    pairs = {(role.symbol, role.utc_date, role.regime) for role in policy.roles}
    assert ("1000BTTCUSDT", "2022-04-11", "recent") in pairs
    assert ("1000BTTCUSDT", "2022-04-11", "delisted") in pairs


def test_user_agent_and_calendar_and_minute_fields() -> None:
    assert sample.USER_AGENT == "cex002-kline-comparison-sample"
    assert "USER_AGENT" in inspect.getsource(sample.UrllibTransport.fetch)
    assert sample.utc_day_start_ms("1970-01-01") == 0
    assert sample.utc_year_month(0) == "1970-01"
    start = sample.utc_day_start_ms("2025-09-17")
    assert start == calendar.timegm((2025, 9, 17, 0, 0, 0)) * 1000
    assert sample.utc_year_month(start) == "2025-09"
    schemas = KNOWN_ARCHIVE_SCHEMAS["klines"]
    assert sample.MINUTE_FIELDS == schemas["headed"] == schemas["headerless"]


def test_pinned_roles_fold_the_duplicate_day_and_ignore_decoys(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    records: list[dict[str, object]] = []
    bodies: dict[str, bytes] = {}
    seen: set[tuple[str, str]] = set()
    for role in sample.PINNED_ROLES:
        digest = sample.sha256_hex(f"{role.symbol}|{role.utc_date}".encode())
        records.append(_record(role.symbol, role.utc_date, role.regime, digest, 128))
        identity = (role.symbol, role.utc_date)
        if identity in seen:
            continue
        seen.add(identity)
        start = sample.utc_day_start_ms(role.utc_date)
        bodies.update(_objects(role.symbol, role.utc_date, [_minute(start)]))
    records.append({"family": "monthly/klines", "key": "monthly-decoy", "symbol": "DECOYUSDT"})
    records.append({"family": "daily/bookTicker", "key": "book", "symbol": "BOOKUSDT"})
    report_sha = _write_report(repo, records)
    policy = _policy(repo, sample.PINNED_ROLES, report_sha)
    transport = MapTransport(bodies)
    result = sample.fetch_sample(
        policy,
        tmp_path / "evidence",
        fetch=True,
        transport=transport,
        clock=lambda: RETRIEVAL,
    )
    assert result.distinct_objects == 9
    assert result.logical_roles == 10
    assert result.fetched_objects == 9
    assert len(transport.calls) == 18
    for index in range(0, 18, 2):
        assert transport.calls[index].endswith(".CHECKSUM")
        assert not transport.calls[index + 1].endswith(".CHECKSUM")
    assert sum("2022-04-11" in url for url in transport.calls) == 2
    assert all("DECOY" not in url and "BOOKUSDT" not in url for url in transport.calls)
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["max_objects"] == 9
    assert manifest["logical_role_count"] == 10
    assert manifest["distinct_object_count"] == 9
    shared = [item for item in manifest["objects"] if item["utc_date"] == "2022-04-11"]
    assert len(shared) == 1
    assert shared[0]["roles"] == ["delisted", "recent"]
    again = MapTransport(bodies)
    reused = sample.fetch_sample(
        policy,
        tmp_path / "evidence",
        fetch=True,
        transport=again,
        clock=lambda: "T2",
    )
    assert reused.fetched_objects == 0
    assert again.calls == []
    assert reused.reused is True


def test_selection_failures_happen_before_transport(tmp_path: Path) -> None:
    role = sample.Role("0GUSDT", "2024-06-01", "early")
    digest = sample.sha256_hex(b"one")
    document = {"samples": [_record("0GUSDT", "2024-06-01", "early", digest, 10)]}
    policy = _policy(tmp_path, (role, sample.Role("0GUSDT", "2024-06-02", "middle")), "ab" * 32)
    with pytest.raises(sample.SampleError, match="sample roles do not match"):
        sample.select_samples(document, policy)
    extra_samples = list(document["samples"])
    extra_samples.append(_record("KAIAUSDT", "2024-12-04", "early", sample.sha256_hex(b"x"), 10))
    with pytest.raises(sample.SampleError, match="sample roles do not match"):
        sample.select_samples({"samples": extra_samples}, _policy(tmp_path, (role,), "ab" * 32))
    first = _record("0GUSDT", "2024-06-01", "recent", digest, 10)
    second = _record("0GUSDT", "2024-06-01", "delisted", sample.sha256_hex(b"other"), 10)
    roles = (sample.Role("0GUSDT", "2024-06-01", "recent"), sample.Role("0GUSDT", "2024-06-01", "delisted"))
    with pytest.raises(sample.SampleError, match="duplicate sample role disagrees"):
        sample.select_samples({"samples": [first, second]}, _policy(tmp_path, roles, "ab" * 32))
    wide_roles = tuple(sample.Role("AUSDT", f"2024-01-{day:02d}", "early") for day in range(1, 11))
    wide = [_record(item.symbol, item.utc_date, item.regime, sample.sha256_hex(item.utc_date.encode()), 10) for item in wide_roles]
    with pytest.raises(sample.SampleError, match="exceeds nine"):
        sample.select_samples({"samples": wide}, _policy(tmp_path, wide_roles, "ab" * 32))


def test_checksum_statement_rejections() -> None:
    filename = "0GUSDT-1m-2024-06-01.zip"
    digest = "ab" * 32
    assert sample.parse_sidecar(f"{digest}  {filename}\n".encode(), filename=filename, limit=1000) == digest
    with pytest.raises(sample.SampleError, match="checksum filename mismatch"):
        sample.parse_sidecar(f"{digest}  other.zip\n".encode(), filename=filename, limit=1000)
    with pytest.raises(sample.SampleError, match="malformed checksum statement"):
        sample.parse_sidecar(f"{digest}\n".encode(), filename=filename, limit=1000)


def test_transport_failure_is_not_retried(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    digest = sample.sha256_hex(b"role")
    report_sha = _write_report(repo, [_record("0GUSDT", "2024-06-01", "early", digest, 8)])
    policy = _policy(repo, (sample.Role("0GUSDT", "2024-06-01", "early"),), report_sha)
    transport = ExplodingTransport()
    transport.fetch = _raising_fetch(transport)  # type: ignore[method-assign]
    with pytest.raises(sample.SampleError, match="down"):
        sample.fetch_sample(policy, tmp_path / "evidence", fetch=True, transport=transport, clock=lambda: "T")
    assert transport.calls == 1


def _raising_fetch(transport: ExplodingTransport):
    def fetch(url: str, *, timeout: float, max_bytes: int) -> sample.FetchResponse:
        transport.calls += 1
        raise sample.SampleError("down")

    return fetch


def test_byte_limits_can_only_tighten_and_row_cap_is_hard() -> None:
    loose = sample.Policy(
        repo=Path("."),
        report_relative="qualification.json",
        report_sha256="ab" * 32,
        bar_root="bar",
        bar_completion="11" * 32,
        flow_root="flow",
        flow_completion="22" * 32,
        protected=(),
        roles=(),
        max_zip_bytes=sample.HARD_MAX_ZIP_BYTES + 50,
        max_sidecar_bytes=sample.HARD_MAX_SIDECAR_BYTES + 50,
        max_decompressed_bytes=sample.HARD_MAX_DECOMPRESSED_BYTES + 50,
    )
    assert sample.zip_limit(loose) == sample.HARD_MAX_ZIP_BYTES
    assert sample.sidecar_limit(loose) == sample.HARD_MAX_SIDECAR_BYTES
    assert sample.decompressed_limit(loose) == sample.HARD_MAX_DECOMPRESSED_BYTES
    member = "AUSDT-1m-2024-01-01.csv"
    start = sample.utc_day_start_ms("2024-01-01")
    one = _zip(member, _csv([_minute(start)]))
    with pytest.raises(sample.SampleError, match="row limit exceeds the hard cap"):
        sample.extract_minute_rows(
            one,
            member_name=member,
            zip_byte_limit=sample.HARD_MAX_ZIP_BYTES,
            decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
            max_rows=1441,
        )
    full = [_minute(start + index * 60_000) for index in range(1440)]
    assert len(sample.extract_minute_rows(
        _zip(member, _csv(full)),
        member_name=member,
        zip_byte_limit=sample.HARD_MAX_ZIP_BYTES,
        decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
        max_rows=1440,
    )) == 1440
    headed = sample.extract_minute_rows(
        _zip(member, _csv(full, header=True)),
        member_name=member,
        zip_byte_limit=sample.HARD_MAX_ZIP_BYTES,
        decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
        max_rows=1440,
    )
    assert len(headed) == 1440
    with pytest.raises(sample.SampleError, match="minute CSV exceeds 1440 data rows"):
        sample.extract_minute_rows(
            _zip(member, _csv([_minute(start + index * 60_000) for index in range(1441)])),
            member_name=member,
            zip_byte_limit=sample.HARD_MAX_ZIP_BYTES,
            decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
            max_rows=1440,
        )


def test_tightened_policy_limits_fail(tmp_path: Path) -> None:
    policy, _evidence, _transport, _result = _fetch_one(tmp_path)
    tight = sample.Policy(
        repo=policy.repo,
        report_relative=policy.report_relative,
        report_sha256=policy.report_sha256,
        bar_root=policy.bar_root,
        bar_completion=policy.bar_completion,
        flow_root=policy.flow_root,
        flow_completion=policy.flow_completion,
        protected=policy.protected,
        roles=policy.roles,
        max_zip_bytes=32,
    )
    rows = [_minute(sample.utc_day_start_ms("2024-06-01"))]
    with pytest.raises(sample.SampleError, match="response exceeds its streaming byte limit"):
        sample.fetch_sample(
            tight,
            tmp_path / "tight-evidence",
            fetch=True,
            transport=MapTransport(_objects("0GUSDT", "2024-06-01", rows)),
            clock=lambda: "T",
        )
    member = sample.minute_member_name("0GUSDT", "2024-06-01")
    with pytest.raises(sample.SampleError, match="ZIP exceeds the compressed byte limit"):
        sample.extract_minute_rows(
            _zip(member, _csv(rows)),
            member_name=member,
            zip_byte_limit=32,
            decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
            max_rows=1440,
        )


def test_streaming_bounds_do_not_trust_content_length() -> None:
    with pytest.raises(sample.SampleError, match="Content-Length does not match"):
        sample.read_bounded(_BytesReader(b"abcdef"), max_bytes=10, content_length=3)
    with pytest.raises(sample.SampleError, match="response exceeds its streaming byte limit"):
        sample.read_bounded(_BytesReader(b"abcdefgh"), max_bytes=4, content_length=100)


def test_unsafe_zip_members_are_rejected() -> None:
    member = "AUSDT-1m-2024-01-01.csv"
    payload = _csv([_minute(sample.utc_day_start_ms("2024-01-01"))])
    limits = dict(
        member_name=member,
        zip_byte_limit=sample.HARD_MAX_ZIP_BYTES,
        decompressed_byte_limit=sample.HARD_MAX_DECOMPRESSED_BYTES,
        max_rows=1440,
    )
    with pytest.raises(sample.SampleError, match="ZIP is truncated or malformed"):
        sample.extract_minute_rows(b"PK\x03\x04broken", **limits)
    with pytest.raises(sample.SampleError, match="ZIP member path escapes"):
        sample.extract_minute_rows(_zip("../x.csv", payload), **limits)
    with pytest.raises(sample.SampleError, match="ZIP member path escapes"):
        sample.extract_minute_rows(_zip("/tmp/x.csv", payload), **limits)
    with pytest.raises(sample.SampleError, match="ZIP member path escapes"):
        sample.extract_minute_rows(_zip("..\\x.csv", payload), **limits)
    with pytest.raises(sample.SampleError, match="ZIP member name is not the expected CSV"):
        sample.extract_minute_rows(_zip("nope.csv", payload), **limits)
    info = zipfile.ZipInfo(member)
    info.external_attr = stat.S_IFLNK << 16
    info.compress_type = zipfile.ZIP_STORED
    with pytest.raises(sample.SampleError, match="ZIP member is not a regular file"):
        sample.extract_minute_rows(_zipinfo(member, payload, info), **limits)
    plain = bytearray(_zip(member, payload, stored=True))
    local_at = plain.find(b"PK\x03\x04")
    central_at = plain.find(b"PK\x01\x02")
    assert local_at == 0 and central_at > local_at
    plain[local_at + 6] |= 0x01
    plain[central_at + 8] |= 0x01
    assert plain[local_at + 6] & 0x01 and plain[central_at + 8] & 0x01
    with zipfile.ZipFile(io.BytesIO(plain)) as archive:
        assert archive.infolist()[0].flag_bits & 0x01
    with pytest.raises(sample.SampleError, match="encrypted ZIP member is rejected"):
        sample.extract_minute_rows(bytes(plain), **limits)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, payload)
        archive.writestr("extra.csv", payload)
    with pytest.raises(sample.SampleError, match="ZIP must contain exactly one member"):
        sample.extract_minute_rows(buffer.getvalue(), **limits)
    stored = bytearray(_zip(member, payload, stored=True))
    name_len = int.from_bytes(stored[26:28], "little")
    extra_len = int.from_bytes(stored[28:30], "little")
    stored[30 + name_len + extra_len] ^= 0xFF
    with pytest.raises(sample.SampleError, match="ZIP CRC"):
        sample.extract_minute_rows(bytes(stored), **limits)


def test_redirects_and_exact_url_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(sample.SampleError, match="redirect"):
        sample._NoRedirect().redirect_request(None, None, 302, "Moved", None, "https://evil.example")
    repo = tmp_path / "repo"
    digest = sample.sha256_hex(b"role")
    report_sha = _write_report(repo, [_record("0GUSDT", "2024-06-01", "early", digest, 8)])
    policy = _policy(repo, (sample.Role("0GUSDT", "2024-06-01", "early"),), report_sha)
    key = sample.minute_object_key("0GUSDT", "2024-06-01")
    side = sample.official_object_url(key + ".CHECKSUM")
    zipped = sample.official_object_url(key)
    moved = MapTransport({
        side: sample.FetchResponse(302, side, b"", 0),
        zipped: sample.FetchResponse(200, zipped, b"zip", 3),
    })
    with pytest.raises(sample.SampleError, match="sample HTTP status is not 200"):
        sample.fetch_sample(policy, tmp_path / "evidence", fetch=True, transport=moved, clock=lambda: "T")
    left = MapTransport({
        side: sample.FetchResponse(200, side + "/elsewhere", b"side", 4),
        zipped: sample.FetchResponse(200, zipped, b"zip", 3),
    })
    with pytest.raises(sample.SampleError, match="sample response left the exact official object"):
        sample.fetch_sample(policy, tmp_path / "evidence-left", fetch=True, transport=left, clock=lambda: "T")


def test_fetch_false_does_not_call_transport(tmp_path: Path) -> None:
    policy, evidence, _transport, _result = _fetch_one(tmp_path)
    exploding = ExplodingTransport()
    reused = sample.fetch_sample(policy, evidence, fetch=False, transport=exploding, clock=lambda: "T2")
    assert reused.fetched_objects == 0
    assert exploding.calls == 0
    missing = ExplodingTransport()
    with pytest.raises(sample.SampleError, match="retained comparison sample is missing"):
        sample.fetch_sample(policy, tmp_path / "absent", fetch=False, transport=missing, clock=lambda: "T")
    assert missing.calls == 0


def test_corrupt_object_bytes_are_not_repaired(tmp_path: Path) -> None:
    policy, evidence, _transport, result = _fetch_one(tmp_path)
    loaded = sample.load_sample(policy, evidence)
    retained = loaded.objects[0]
    path = evidence / ".objects" / retained.zip_sha256[:2] / retained.zip_sha256
    planted = bytearray(path.read_bytes())
    planted[0] ^= 0xFF
    path.write_bytes(planted)
    with pytest.raises(sample.SampleError):
        sample.fetch_sample(policy, evidence, fetch=True, transport=MapTransport({}), clock=lambda: "T2")
    assert path.read_bytes() == planted
    assert result.manifest_path.read_bytes()


def test_hooks_publish_manifest_last_and_keep_the_original_retrieval_time(tmp_path: Path) -> None:
    symbol, utc_date = "0GUSDT", "2024-06-01"
    repo = tmp_path / "repo"
    digest = sample.sha256_hex(b"hook")
    report_sha = _write_report(repo, [_record(symbol, utc_date, "early", digest, 8)])
    policy = _policy(repo, (sample.Role(symbol, utc_date, "early"),), report_sha)
    bodies = _objects(symbol, utc_date, [_minute(sample.utc_day_start_ms(utc_date))])
    evidence = tmp_path / "evidence"

    def stop_object() -> None:
        raise RuntimeError("stop object")

    with pytest.raises(RuntimeError, match="stop object"):
        sample.fetch_sample(
            policy,
            evidence,
            fetch=True,
            transport=MapTransport(bodies),
            hooks=sample.Hooks(before_object_publish=stop_object),
            clock=lambda: "T1",
        )
    assert not (evidence / ".receipts").exists()
    assert not (evidence / ".complete").exists()

    def stop_manifest() -> None:
        raise RuntimeError("stop manifest")

    with pytest.raises(RuntimeError, match="stop manifest"):
        sample.fetch_sample(
            policy,
            evidence,
            fetch=True,
            transport=MapTransport(bodies),
            hooks=sample.Hooks(before_manifest_publish=stop_manifest),
            clock=lambda: "T1",
        )
    receipts = list((evidence / ".receipts").iterdir())
    assert len(receipts) == 1
    assert not (evidence / ".complete").exists()
    assert json.loads(receipts[0].read_text())["retrieval_time"] == "T1"
    result = sample.fetch_sample(policy, evidence, fetch=True, transport=MapTransport(bodies), clock=lambda: "T2")
    assert result.fetched_objects == 0
    assert json.loads(receipts[0].read_text())["retrieval_time"] == "T1"
    extra = evidence / ".complete" / "extra.json"
    extra.write_bytes(b"EXTRA")
    with pytest.raises(sample.SampleError, match="conflicting sample manifest"):
        sample.fetch_sample(policy, evidence, fetch=True, transport=MapTransport(bodies), clock=lambda: "T3")
    assert extra.read_bytes() == b"EXTRA"


def test_load_sample_authenticates_physical_receipts(tmp_path: Path) -> None:
    policy, evidence, _transport, _result = _fetch_one(tmp_path)
    loaded = sample.load_sample(policy, evidence)
    receipt_path = evidence / ".receipts" / f"{loaded.objects[0].zip_sha256}.json"
    original = receipt_path.read_bytes()

    receipt_path.unlink()
    with pytest.raises(sample.SampleError, match="retained receipt is missing"):
        sample.load_sample(policy, evidence)
    receipt_path.write_bytes(original)

    planted = original.replace(b"{", b"{ ", 1)
    receipt_path.write_bytes(planted)
    with pytest.raises(sample.SampleError, match="retained receipt is corrupt"):
        sample.load_sample(policy, evidence)
    assert receipt_path.read_bytes() == planted
    receipt_path.write_bytes(original)

    changed = json.loads(original)
    changed["retrieval_time"] = "CHANGED"
    conflicting = sample.canonical_json(changed)
    receipt_path.write_bytes(conflicting)
    with pytest.raises(sample.SampleError, match="conflicting retained receipt"):
        sample.load_sample(policy, evidence)
    assert receipt_path.read_bytes() == conflicting
    receipt_path.write_bytes(original)

    renamed = json.loads(original)
    renamed["zip_sha256"] = "ab" * 32
    filename_body = sample.canonical_json(renamed)
    receipt_path.write_bytes(filename_body)
    with pytest.raises(sample.SampleError, match="retained receipt filename disagrees"):
        sample.load_sample(policy, evidence)
    assert receipt_path.read_bytes() == filename_body
    receipt_path.write_bytes(original)

    extra = evidence / ".receipts" / (("ff" * 32) + ".json")
    extra.write_bytes(b"{}\n")
    with pytest.raises(sample.SampleError, match="conflicting retained receipt"):
        sample.load_sample(policy, evidence)
    assert extra.read_bytes() == b"{}\n"


def test_read_retained_rows_rechecks_sidecar_sha256(tmp_path: Path) -> None:
    policy, evidence, _transport, _result = _fetch_one(tmp_path)
    loaded = sample.load_sample(policy, evidence)
    retained = loaded.objects[0]
    path = evidence / ".objects" / retained.sidecar_sha256[:2] / retained.sidecar_sha256
    original = path.read_bytes()
    planted = original.replace(b"  ", b"\t", 1)
    filename = retained.comparison_key.rsplit("/", 1)[-1]
    assert sample.parse_sidecar(planted, filename=filename, limit=sample.HARD_MAX_SIDECAR_BYTES) == retained.zip_sha256
    path.write_bytes(planted)
    with pytest.raises(sample.SampleError, match="retained checksum changed"):
        sample.read_retained_rows(policy, evidence, retained)
    assert path.read_bytes() == planted
