"""Focused synthetic tests for safe ZIP and CSV inspection."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipInfo

import pytest

from source_audit.archives import (
    audit_csv_safe,
    audit_zip_safe,
    is_unsafe_zip_member_name,
)
from source_audit.errors import MalformedCSVError, UnsafeArchiveError


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_safe_zip_and_harmless_double_dot_name(tmp_path: Path) -> None:
    zpath = tmp_path / "ok.zip"
    _write_zip(zpath, {"prices..backup.csv": b"a,b\n1,2\n", "data/file.csv": b"x\n"})
    result = audit_zip_safe(zpath)
    assert result.member_count == 2
    assert {m.name for m in result.members} == {"prices..backup.csv", "data/file.csv"}
    assert is_unsafe_zip_member_name("prices..backup.csv") is False


@pytest.mark.parametrize(
    "name",
    [
        "../evil.txt",
        "/abs/path.txt",
        "//unc/share/file",
        "C:/windows/file.txt",
        "foo/../../etc/passwd",
        "foo/./bar",
    ],
)
def test_unsafe_member_names(name: str) -> None:
    assert is_unsafe_zip_member_name(name) is True


def test_unsafe_path_raises(tmp_path: Path) -> None:
    zpath = tmp_path / "evil.zip"
    _write_zip(zpath, {"../evil.txt": b"bad"})
    with pytest.raises(UnsafeArchiveError, match="Unsafe path"):
        audit_zip_safe(zpath)


def test_duplicate_member_names(tmp_path: Path) -> None:
    zpath = tmp_path / "dup.zip"
    # zipfile allows duplicate names if we use ZipInfo carefully via low-level write.
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("a.csv", b"1")
        zf.writestr("a.csv", b"2")
    with pytest.raises(UnsafeArchiveError, match="Duplicate"):
        audit_zip_safe(zpath)


def test_encrypted_member_rejected(tmp_path: Path) -> None:
    """stdlib zipfile clears the encrypt flag on write; patch GPBF in the file bytes."""
    import struct

    zpath = tmp_path / "enc.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("secret.csv", b"hidden")
    raw = bytearray(zpath.read_bytes())
    # Local header general-purpose bit flag at offset 6.
    struct.pack_into("<H", raw, 6, struct.unpack_from("<H", raw, 6)[0] | 0x1)
    eocd = raw.rfind(b"PK\x05\x06")
    assert eocd >= 0
    cd_offset = struct.unpack_from("<I", raw, eocd + 16)[0]
    # Central directory header flag at cd_offset + 8.
    struct.pack_into(
        "<H",
        raw,
        cd_offset + 8,
        struct.unpack_from("<H", raw, cd_offset + 8)[0] | 0x1,
    )
    zpath.write_bytes(raw)
    with pytest.raises(UnsafeArchiveError, match="Encrypted"):
        audit_zip_safe(zpath)


def test_symlink_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "link.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        info = ZipInfo("link")
        # Unix symlink mode in external_attr upper 16 bits.
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, b"/tmp/target")
    with pytest.raises(UnsafeArchiveError, match="Symlink"):
        audit_zip_safe(zpath)


def test_member_count_limit(tmp_path: Path) -> None:
    zpath = tmp_path / "many.zip"
    _write_zip(zpath, {f"f{i}.csv": b"x" for i in range(5)})
    with pytest.raises(UnsafeArchiveError, match="Member count"):
        audit_zip_safe(zpath, max_members=3)


def test_zero_byte_compressed_positive_size_rejected(tmp_path: Path) -> None:
    """Stored empty compress with positive file_size is rejected conservatively.

    Construct a ZIP member with compress_size=0 and file_size>0 via raw ZipInfo
    when possible; if the platform stores STORED with compress==file size, skip
    by crafting an impossible ratio via max_ratio instead.
    """
    zpath = tmp_path / "bombish.zip"
    payload = b"A" * 1000
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.csv", payload)
    # Ratio limit: highly compressible data may exceed a tiny max_ratio.
    with pytest.raises(UnsafeArchiveError):
        audit_zip_safe(zpath, max_ratio=1.01, max_extracted_per_member=10**9)


def test_csv_happy_path_with_multiline_and_timestamps(tmp_path: Path) -> None:
    csv_path = tmp_path / "trades.csv"
    # Quoted multiline field.
    csv_path.write_text(
        'id,ts,note\n'
        '1,1735689600000,"hello\nworld"\n'
        "2,1735689601000,ok\n",
        encoding="utf-8",
    )
    result = audit_csv_safe(
        csv_path,
        encoding="utf-8",
        max_rows=100,
        key_fields=["id"],
        order_fields=["ts"],
        timestamp_field="ts",
        timestamp_min_utc=datetime(2010, 1, 1, tzinfo=timezone.utc),
        timestamp_max_utc=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    assert result.headers == ("id", "ts", "note")
    assert result.logical_data_records == 2
    assert result.valid_records == 2
    assert result.malformed_records == 0
    assert result.truncated is False
    assert result.observed_timestamp_units == ("ms",)
    assert result.earliest_timestamp is not None
    assert result.latest_timestamp is not None
    assert result.duplicate_key_count == 0
    assert result.ordering_violation_count == 0


def test_csv_duplicate_header_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("a,a\n1,2\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="Duplicate header"):
        audit_csv_safe(p, encoding="utf-8")


def test_csv_empty_header_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("a,\n1,2\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="Empty header"):
        audit_csv_safe(p, encoding="utf-8")


def test_csv_width_mismatch_reported(tmp_path: Path) -> None:
    p = tmp_path / "w.csv"
    p.write_text("a,b\n1,2,3\n4,5\n", encoding="utf-8")
    result = audit_csv_safe(p, encoding="utf-8")
    assert result.malformed_records == 1
    assert result.valid_records == 1
    assert result.malformed_reports[0].reason == "width_mismatch"


def test_csv_duplicate_keys_and_order_violations(tmp_path: Path) -> None:
    p = tmp_path / "k.csv"
    p.write_text("id,ts\n1,3\n1,2\n", encoding="utf-8")
    result = audit_csv_safe(
        p,
        encoding="utf-8",
        key_fields=["id"],
        order_fields=["ts"],
    )
    assert result.duplicate_key_count == 1
    assert result.ordering_violation_count == 1


def test_csv_max_rows_truncation(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    lines = ["id"] + [str(i) for i in range(10)]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = audit_csv_safe(p, encoding="utf-8", max_rows=3)
    assert result.logical_data_records == 3
    assert result.truncated is True


def test_csv_missing_key_field_before_processing(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="key_fields"):
        audit_csv_safe(p, encoding="utf-8", key_fields=["missing"])


def test_csv_physical_line_limit(tmp_path: Path) -> None:
    p = tmp_path / "long.csv"
    p.write_text("h\n" + ("x" * 50) + "\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="Physical line"):
        audit_csv_safe(p, encoding="utf-8", max_physical_line=10)


def test_csv_logical_record_limit(tmp_path: Path) -> None:
    """Over-long logical records raise (fail-fast), matching multiline accumulation.

    Contract: max_logical_record is enforced during stream accumulation in
    ``_BoundedCSVTextReader``. Exceeding it raises ``MalformedCSVError`` rather
    than collecting a soft ``logical_record_too_long`` row report. This prevents
    unbounded memory growth before the row loop can run.
    """
    p = tmp_path / "lr.csv"
    # Single physical line, two fields, total logical length >> 10.
    p.write_text("a,b\n" + ("y" * 20) + "," + ("z" * 20) + "\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="Logical record exceeds"):
        audit_csv_safe(
            p,
            encoding="utf-8",
            max_physical_line=1_000_000,
            max_logical_record=10,
        )


def test_csv_requires_encoding(tmp_path: Path) -> None:
    p = tmp_path / "e.csv"
    p.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        audit_csv_safe(p, encoding="")


def test_csv_field_larger_than_default_131072_when_configured(tmp_path: Path) -> None:
    """Fields above the stdlib default 131072 are allowed when limits permit."""
    p = tmp_path / "bigfield.csv"
    big = "x" * 200_000
    p.write_text(f"h\n{big}\n", encoding="utf-8")
    result = audit_csv_safe(
        p,
        encoding="utf-8",
        max_physical_line=300_000,
        max_logical_record=300_000,
    )
    assert result.valid_records == 1
    assert result.first_samples[0][0] == big


def test_csv_error_converted_to_typed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """stdlib ``csv.Error`` is converted to typed ``MalformedCSVError``.

    CPython 3.13 does not raise on unterminated quotes or embedded NUL, and our
    stream limits fire before ``csv.field_size_limit``. Force a real ``csv.Error``
    from the reader to exercise the conversion path.
    """
    import csv as csv_mod

    p = tmp_path / "ok.csv"
    p.write_text("h\n1\n", encoding="utf-8")
    real_reader = csv_mod.reader

    def boom_reader(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        underlying = real_reader(*args, **kwargs)

        def _gen():  # type: ignore[no-untyped-def]
            yield next(underlying)  # header row
            raise csv_mod.Error("synthetic field larger than field limit")

        return _gen()

    monkeypatch.setattr(csv_mod, "reader", boom_reader)
    with pytest.raises(MalformedCSVError, match="CSV parse error"):
        audit_csv_safe(
            p,
            encoding="utf-8",
            max_physical_line=1000,
            max_logical_record=1000,
        )


def test_multiline_logical_limit_during_accumulation(tmp_path: Path) -> None:
    """Same raise contract as single-line over-long logical records."""
    p = tmp_path / "multi.csv"
    # Quoted multiline field that grows past max_logical_record while accumulating.
    chunk = "y" * 40
    p.write_text(f'h\n"{chunk}\n{chunk}\n{chunk}"\n', encoding="utf-8")
    with pytest.raises(MalformedCSVError, match="Logical record exceeds"):
        audit_csv_safe(
            p,
            encoding="utf-8",
            max_physical_line=100,
            max_logical_record=50,
        )


def test_zip_member_stream_enforces_byte_bound(tmp_path: Path) -> None:
    from source_audit.archives import read_zip_member_text
    from source_audit.errors import UnsafeArchiveError

    zpath = tmp_path / "m.zip"
    payload = b"Z" * 10_000
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.csv", payload)
    with pytest.raises(UnsafeArchiveError, match="exceeds bound"):
        read_zip_member_text(
            zpath,
            "big.csv",
            encoding="utf-8",
            max_extracted_bytes=100,
            chunk_size=32,
        )
