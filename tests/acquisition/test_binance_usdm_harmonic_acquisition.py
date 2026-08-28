"""CEX-002 Gate 2 — synthetic proof of ADR-0029 as corrected by reviews 287-289
and ADR-0030 exact retained credit.

Every test is synthetic, deterministic, zero-network, temporary-rooted, and free of real
sleep. The production engine, CLI, and offline verifier are exercised on their real paths.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import threading
import zipfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlencode, urlparse

import pytest

from cryptofactors.acquisition import binance_usdm_harmonic_acquisition as gate2
from cryptofactors.acquisition.binance_usdm_harmonic_qualification import (
    persist_provider_sidecar,
    publish_manifest_detail,
)
from cryptofactors.acquisition.binance_usdm_harmonic_sizing import (
    ARCHIVE_FAMILIES,
    COST_FAMILIES,
)

REPOSITORY = Path(__file__).resolve().parents[2]
SECRET = "SECRET_TEST_KEY_DO_NOT_LEAK_9f3a"
CUTOFF = "2020-03-31T00:00:00+00:00"
ONBOARD_MS = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
FROM_UNIX = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp())
TO_UNIX = int(datetime(2020, 3, 31, tzinfo=UTC).timestamp())
HOLDOUT_ID = "c" * 64
AVAILABLE = 80 * 10**9


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha(payload)


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return gate2.canonical_json(payload)


def _zip(name: str, body: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr(name, body)
    return buffer.getvalue()


def _key(family: str, symbol: str, interval: str) -> str:
    cadence, _, hint = family.partition("/")
    return f"data/futures/um/{cadence}/{hint}/{symbol}/{symbol}-{hint}-{interval}.zip"


def _row(key: str, family: str, symbol: str, size: int, interval: str) -> dict[str, Any]:
    cadence, _, group = family.partition("/")
    return {
        "key": key,
        "family": family,
        "family_group": group,
        "symbol": symbol,
        "cadence": cadence,
        "byte_size": size,
        "integrity_state": "listed_sidecar",
        "validation_state": "raw_validation_pending",
        "consumable": False,
        "sidecar_key": f"{key}.CHECKSUM",
        "sidecar_sha256": "",
        "economic_interval": interval,
        "economic_interval_kind": "month" if cadence == "monthly" else "date",
    }


def _listing_xml(objects: list[tuple[str, int, str]]) -> bytes:
    rows = "".join(
        f"<Contents><Key>{key}</Key><Size>{size}</Size>"
        f"<ETag>&quot;{etag}&quot;</ETag></Contents>"
        for key, size, etag in objects
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<IsTruncated>false</IsTruncated>{rows}</ListBucketResult>"
    ).encode("utf-8")


class DummyObj:
    def __init__(self, size: int, etag: str) -> None:
        self.size = size
        self.etag = etag


class FakeFilesystem:
    """Injected same-device filesystem with an optional scripted availability sequence."""

    def __init__(
        self,
        device: str = "dev:test",
        available: int = AVAILABLE,
        sequence: list[int] | None = None,
    ) -> None:
        self.device = device
        self.available = available
        self.sequence = list(sequence or ())
        self.calls = 0
        self.lock = threading.Lock()

    def device_of(self, path: Path) -> str:
        return self.device

    def available_bytes(self, path: Path) -> int:
        with self.lock:
            self.calls += 1
            if self.sequence:
                return self.sequence.pop(0)
            return self.available


class FakeTransport:
    """A synthetic streaming transport that can chunk, fail, and prove closure."""

    def __init__(self) -> None:
        self.bodies: dict[str, bytes] = {}
        self.chunked: dict[str, list[bytes]] = {}
        self.status: dict[str, list[int]] = {}
        self.headers: dict[str, dict[str, str]] = {}
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.lock = threading.Lock()
        self.block = False
        self.gate = threading.Event()
        self.gate.set()
        self.reached = threading.Event()
        self.closed = False
        self.opened_responses = 0
        self.closed_responses = 0
        self.raise_once: dict[str, Exception] = {}

    def add(
        self,
        url: str,
        body: bytes,
        *,
        status: int | list[int] = 200,
        headers: Mapping[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.bodies[url] = body
        self.status[url] = [status] if isinstance(status, int) else list(status)
        self.headers[url] = dict(headers or {})
        if chunks is not None:
            self.chunked[url] = list(chunks)

    def close(self) -> None:
        self.closed = True

    def liquidation_url(self, native: str) -> str:
        params = {
            "symbols": f"{native}_PERP.A",
            "interval": "daily",
            "from": str(FROM_UNIX),
            "to": str(TO_UNIX),
            "convert_to_usd": "false",
        }
        return (
            f"{gate2.COINALYZE_BASE}{gate2.COINALYZE_LIQUIDATION_PATH}?{urlencode(params)}"
        )

    def stream_get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        timeout: float,
    ) -> gate2.StreamResponse:
        with self.lock:
            self.calls.append((url, dict(headers or {})))
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            if self.in_flight >= 4:
                self.reached.set()
        if self.block:
            self.gate.wait(timeout=2)
        try:
            if url in self.raise_once:
                raise self.raise_once.pop(url)
            statuses = self.status.get(url) or [404]
            status = statuses.pop(0) if statuses else 404
            self.status[url] = statuses or [status]
            body = self.bodies.get(url, b"")
            pieces = list(self.chunked.get(url) or [body])
            if status not in {200, 404}:
                pieces = [b""]
            header_map = dict(self.headers.get(url) or {})

            def _chunks() -> Iterator[bytes]:
                yield from pieces

            with self.lock:
                self.opened_responses += 1

            def _close() -> None:
                with self.lock:
                    self.closed_responses += 1

            return gate2.StreamResponse(status, header_map, _chunks(), _close)
        finally:
            with self.lock:
                self.in_flight -= 1


def _load_cli() -> Any:
    path = REPOSITORY / gate2.CLI_RELATIVE_PATH
    spec = importlib.util.spec_from_file_location("gate2_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _attestation(pins: gate2.AuthorityPins, filesystem: FakeFilesystem) -> bytes:
    unsigned = {
        "schema_version": "cex002_gate2_capacity_attestation_v1",
        "ticket": "CEX-002",
        "generated_at": "2026-08-23T00:00:00+00:00",
        "capacity": {
            "stable_requirement_bytes": pins.stable_requirement_bytes,
            "operating_reserve_bytes": 1,
            "total_future_storage_bytes": pins.stable_requirement_bytes + 1,
        },
        "filesystem": {
            "destination": pins.destination,
            "device": pins.device,
            "post_publication_available_bytes": filesystem.available,
        },
        "storage_preflight_state": "sufficient",
        "blockers": [],
    }
    identity = {
        "algorithm": "sha256",
        "scope": "canonical attestation excluding self_identity",
        "payload_sha256": _sha(_canonical(unsigned)),
        "canonicalization": "UTF-8 JSON, indent=2, sorted keys, trailing LF",
    }
    return _canonical({**unsigned, "self_identity": identity})


def _market(native: str) -> dict[str, Any]:
    return {
        "symbol": f"{native}_PERP.A",
        "symbol_on_exchange": native,
        "exchange": "A",
        "is_perpetual": True,
        "oi_lq_vol_denominated_in": "USD",
    }


def _seed_retained(
    *,
    sample_dir: Path,
    sidecar_dir: Path,
    key: str,
    payload: bytes,
) -> dict[str, Any]:
    digest = _sha(payload)
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / digest).write_bytes(payload)
    sidecar_body = f"{digest} {key.rsplit('/', 1)[-1]}\n".encode()
    sidecar_path, sidecar_digest = persist_provider_sidecar(
        sidecar_body, sidecar_dir=sidecar_dir
    )
    return {
        "status": "complete",
        "sha256": digest,
        "provider_checksum": digest,
        "provider_checksum_path": str(sidecar_path),
        "provider_checksum_sha256": sidecar_digest,
        "byte_size": len(payload),
        "retrieval_time": "2026-08-21T00:00:00+00:00",
    }


def _costish(key: str) -> bool:
    return "/daily/bookTicker/" in key or "/daily/bookDepth/" in key


def _sizing_receipt_document(
    keys: Sequence[str],
    *,
    objects: int,
    unique_bytes: int,
    selected_keys: int,
    cost_keys: int,
    unverified: int = 0,
    rejected_recovered_rows: int = 0,
    valid_requirement_keys: int | None = None,
    key_set_sha256: str | None = None,
    lineage_key_set_sha256: str | None = None,
    lineage_requirement_keys: int | None = None,
    coefficient_only_keys_marked_retained: int = 0,
    physical_objects: int | None = None,
    physical_bytes: int | None = None,
    source: str | None = None,
    schema_version: str = "cex002_gate2_storage_sizing_v3",
    ticket: str = "CEX-002",
) -> dict[str, Any]:
    ordered = list(keys)
    digest = (
        key_set_sha256
        if key_set_sha256 is not None
        else gate2.requirement_key_set_sha256(sorted(str(item) for item in ordered))
    )
    key_count = len(ordered) if valid_requirement_keys is None else valid_requirement_keys
    return {
        "schema_version": schema_version,
        "ticket": ticket,
        "physical_inputs": {
            "retained_credit": {
                "bytes": unique_bytes,
                "cost_retained_keys": cost_keys,
                "key_set_sha256": digest,
                "keys": ordered,
                "objects": objects,
                "rejected_recovered_rows": rejected_recovered_rows,
                "report_summary": {
                    "rejected_retained_row_count": rejected_recovered_rows,
                    "retained_valid_requirement_keys": key_count,
                    "retained_verified_credit_bytes": unique_bytes,
                    "retained_verified_credit_objects": objects,
                    "unverified_retained_objects": unverified,
                },
                "selected_retained_keys": selected_keys,
                "source": gate2.RETAINED_CREDIT_SOURCE if source is None else source,
                "unverified_objects": unverified,
                "valid_requirement_keys": key_count,
            },
            "retained_credit_bytes": (
                unique_bytes if physical_bytes is None else physical_bytes
            ),
            "retained_credit_objects": (
                objects if physical_objects is None else physical_objects
            ),
        },
        "lineage": {
            "coefficient_only_keys_marked_retained": (
                coefficient_only_keys_marked_retained
            ),
            "retained_archive_key_set_sha256": (
                digest if lineage_key_set_sha256 is None else lineage_key_set_sha256
            ),
            "retained_archive_requirement_keys": (
                key_count if lineage_requirement_keys is None else lineage_requirement_keys
            ),
        },
    }


def _write_sizing_receipt(built: dict[str, Any], document: Mapping[str, Any]) -> None:
    body = _canonical(document)
    built["paths"].receipt_258_path.write_bytes(body)
    built["pins"] = replace(
        built["pins"],
        receipt_258_sha256=_sha(body),
        receipt_258_bytes=len(body),
    )


def _rewrite_progress(
    built: dict[str, Any], mutate: Callable[[dict[str, Any]], None]
) -> None:
    path = built["paths"].progress_path
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    body = _canonical(document)
    path.write_bytes(body)
    built["pins"] = replace(built["pins"], progress_sha256=_sha(body))


def _plan_receipt(built: dict[str, Any]) -> dict[str, Any]:
    conn = _state_conn(built["paths"])
    try:
        row = conn.execute(
            "SELECT plan_receipt_sha256 FROM authority WHERE id=1"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    path = built["paths"].plan_receipt_dir / f"{row[0]}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_installed_plan(built: dict[str, Any]) -> None:
    assert not built["paths"].state_path.exists()
    plan_dir = built["paths"].plan_receipt_dir
    if plan_dir.exists():
        assert list(plan_dir.glob("*.json")) == []


def build_universe(
    tmp_path: Path,
    *,
    archive_families: tuple[str, ...] = ARCHIVE_FAMILIES,
    supported: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"),
    unsupported: tuple[str, ...] = ("GAPUSDT",),
    extra_inventory: tuple[str, ...] = ("SOLUSDT",),
    empty_liquidation: frozenset[str] = frozenset(),
    unavailable: frozenset[str] = frozenset(),
    retain_all: bool = False,
    retain_keys: set[str] | None = None,
    credit_keys: set[str] | None = None,
    archive_intervals: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    repo = tmp_path / "repo"
    store = tmp_path / "data" / "cex002_qualify"
    listing_cache = store / "list_cache"
    coinalyze_cache = store / "coinalyze_cache"
    sample_dir = store / "raw" / "sha256"
    for path in (listing_cache, coinalyze_cache, sample_dir, store / "gate2"):
        path.mkdir(parents=True)

    symbol = "BTCUSDT"
    zips: dict[str, bytes] = {}
    selected_rows: list[dict[str, Any]] = []
    if archive_intervals:
        for family in archive_families:
            for interval in archive_intervals:
                key = _key(family, symbol, interval)
                payload = _zip("data.csv", f"{family},{symbol},{interval}\n".encode())
                zips[key] = payload
                selected_rows.append(_row(key, family, symbol, len(payload), interval))
    else:
        for family in archive_families:
            chosen = "2020-01" if family.startswith("monthly/") else "2020-01-01"
            key = _key(family, symbol, chosen)
            payload = _zip("data.csv", f"{family},{symbol}\n".encode())
            zips[key] = payload
            selected_rows.append(_row(key, family, symbol, len(payload), chosen))
    selected_rows.sort(key=lambda item: item["key"])

    cost_rows: list[dict[str, Any]] = []
    cost_items: list[dict[str, Any]] = []
    listing_objects: list[tuple[str, int, str]] = []
    if archive_intervals and len(archive_intervals) >= 68:
        cost_pairs = [
            ("daily/bookTicker", "2020-01-01"),
            ("daily/bookTicker", "2020-01-02"),
            ("daily/bookTicker", "2020-01-03"),
            ("daily/bookDepth", "2020-01-01"),
            ("daily/bookDepth", "2020-01-02"),
        ]
    else:
        cost_pairs = [(family, "2020-01-01") for family in COST_FAMILIES]
    for family, day in cost_pairs:
        key = _key(family, symbol, day)
        payload = _zip("data.csv", f"{family},{symbol},{day}\n".encode())
        zips[key] = payload
        etag = f"{len(payload):032x}"
        cost_rows.append(_row(key, family, symbol, len(payload), day))
        listing_objects.append((key, len(payload), etag))
        cost_items.append(
            {
                "family": family,
                "symbol": symbol,
                "key": key,
                "object": DummyObj(len(payload), etag),
            }
        )

    manifest = {
        "rows": selected_rows,
        "collisions": (),
        "rejections": (),
        "raw_validation_pending_keys": tuple(row["key"] for row in selected_rows),
        "object_count": len(selected_rows),
        "compressed_raw_bytes": sum(int(row["byte_size"]) for row in selected_rows),
        "consumable_object_count": 0,
        "family_object_counts": {
            family: sum(1 for row in selected_rows if row["family"] == family)
            for family in sorted({str(row["family"]) for row in selected_rows})
        },
        "cadence_rule": gate2.CADENCE_RULE,
        "integrity_rule": gate2.INTEGRITY_RULE,
    }
    descriptor = publish_manifest_detail(manifest, store_root=store)

    listing_body = _listing_xml(listing_objects)
    listing_digest = _write(listing_cache / _sha(listing_body), listing_body)
    listing_path = listing_cache / listing_digest
    cost_digest = gate2.cost_manifest_digest(
        cost_items,
        selector=gate2.COST_SELECTOR,
        families=COST_FAMILIES,
        gaps=(),
    )

    inventory_rows = [_market(native) for native in supported + extra_inventory]
    inventory_rows.append(dict(_market("BTCUSD"), exchange="F"))
    inventory_body = json.dumps(inventory_rows).encode("utf-8")
    inventory_digest = _sha(inventory_body)
    inventory_path = coinalyze_cache / inventory_digest
    inventory_path.write_bytes(inventory_body)

    liquidation_bodies: dict[str, bytes] = {}
    for native in supported:
        provider = f"{native}_PERP.A"
        if native in empty_liquidation:
            body = json.dumps([{"symbol": provider, "history": []}]).encode("utf-8")
        else:
            body = json.dumps(
                [
                    {
                        "symbol": provider,
                        "history": [
                            {"t": FROM_UNIX, "l": 1.25, "s": 0.50},
                            {"t": FROM_UNIX + 86400, "l": 2.00, "s": 0.00},
                        ],
                    }
                ]
            ).encode("utf-8")
        liquidation_bodies[native] = body

    retain_set = set(zips) if retain_all else set(retain_keys or ())
    checkpoint_objects: dict[str, Any] = {}
    for key in sorted(retain_set):
        checkpoint_objects[key] = _seed_retained(
            sample_dir=sample_dir,
            sidecar_dir=listing_cache,
            key=key,
            payload=zips[key],
        )
    authorized = set(credit_keys) if credit_keys is not None else set(retain_set)
    missing_credit = authorized - retain_set
    if missing_credit:
        raise AssertionError("credit_keys must be seeded in qualification progress")
    retained_digests: set[str] = set()
    retained_bytes = 0
    for key in sorted(authorized):
        entry = checkpoint_objects[key]
        digest = str(entry["sha256"])
        if digest not in retained_digests:
            retained_digests.add(digest)
            retained_bytes += int(entry["byte_size"])
    cost_retained = sum(1 for key in authorized if _costish(key))
    selected_retained = len(authorized) - cost_retained
    receipt_document = _sizing_receipt_document(
        sorted(authorized),
        objects=len(retained_digests),
        unique_bytes=retained_bytes,
        selected_keys=selected_retained,
        cost_keys=cost_retained,
    )
    receipt_bytes = _canonical(receipt_document)

    provenance = [
        {
            "byte_size": len(inventory_body),
            "content_path": str(inventory_path),
            "header_names": ["api_key"],
            "params": {},
            "path": "/future-markets",
            "provenance_source": "raw_response_bytes",
            "retrieved_at": "2026-08-21T00:00:00+00:00",
            "sha256": inventory_digest,
            "status_code": 200,
            "transport": "network",
        }
    ]
    classifications = [
        {
            "symbol": native,
            "accepted": True,
            "membership_class": "confirmed_perpetual",
            "evidence": [
                {
                    "kind": "exchange_info",
                    "onboard_ms": ONBOARD_MS,
                    "delivery_ms": None,
                    "closed_observed_ms": None,
                }
            ],
        }
        for native in list(supported) + list(unsupported)
    ]
    report = {
        "generated_at": CUTOFF,
        "acquisition_manifest": {"detail": descriptor},
        "storage": {
            "cost_sample": {
                "keys": [row["key"] for row in cost_rows],
                "gaps": [],
                "manifest_digest": cost_digest,
            }
        },
        "coinalyze": {
            "universe_support": {
                "supported_symbols": list(supported),
                "unmapped_symbols": list(unsupported),
                "supported_count": len(supported),
                "unmapped_count": len(unsupported),
            },
            "anchor_symbols": ["BTCUSDT", "ETHUSDT"][: len(supported)],
            "provenance": provenance,
        },
        "membership": {"classifications": classifications},
    }
    report_bytes = _canonical(report)
    report_path = repo / "research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json"
    receipt_path = repo / "research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json"
    holdout_path = store / "cex002_holdout_boundary.json"
    lock_path = store / "cex002_sample_plan_lock.json"
    ledger_path = store / "cex002_amendment_ledger.json"
    progress_doc = {"status": "complete", "objects": checkpoint_objects}
    progress_path = store / "cex002_qualification_progress.json"
    listing_checkpoint_path = store / "cex002_listing_checkpoint.json"
    metadata_path = store / "cex002_official_contract_metadata.json"
    listing_checkpoint = {
        "entries": {
            "cost": {
                "response_sha256": listing_digest,
                "content_path": str(listing_path),
            }
        }
    }
    metadata = {"symbol_snapshot": {native: "digest" for native in supported}}
    holdout = {"boundary_id": HOLDOUT_ID, "boundary_utc": "2026-08-01T00:00:00+00:00"}
    _write(lock_path, _canonical({"plan_version": 4}))
    _write(ledger_path, _canonical({"binding": {}}))
    _write(progress_path, _canonical(progress_doc))
    _write(listing_checkpoint_path, _canonical(listing_checkpoint))
    _write(metadata_path, _canonical(metadata))
    _write(holdout_path, _canonical(holdout))
    _write(report_path, report_bytes)
    _write(receipt_path, receipt_bytes)

    filesystem = FakeFilesystem()
    pins = gate2.AuthorityPins(
        report_sha256=_sha(report_bytes),
        manifest_compressed_sha256=str(descriptor["compressed_sha256"]),
        manifest_uncompressed_sha256=str(descriptor["uncompressed_sha256"]),
        cost_manifest_sha256=cost_digest,
        receipt_258_sha256=_sha(receipt_bytes),
        attestation_282_sha256="",
        listing_checkpoint_sha256=_sha(_canonical(listing_checkpoint)),
        contract_metadata_sha256=_sha(_canonical(metadata)),
        lock_sha256=_sha(_canonical({"plan_version": 4})),
        amendment_ledger_sha256=_sha(_canonical({"binding": {}})),
        progress_sha256=_sha(_canonical(progress_doc)),
        qualification_source_sha256=gate2.module_sha256(
            REPOSITORY / gate2.QUALIFICATION_SOURCE_RELATIVE
        ),
        qualification_cli_sha256=gate2.module_sha256(
            REPOSITORY / gate2.QUALIFICATION_CLI_RELATIVE
        ),
        capacity_source_sha256=gate2.module_sha256(
            REPOSITORY / gate2.ATTESTATION_SOURCE_RELATIVE
        ),
        capacity_cli_sha256=gate2.module_sha256(
            REPOSITORY / gate2.ATTESTATION_CLI_RELATIVE
        ),
        holdout_boundary_id=HOLDOUT_ID,
        main_selected_objects=len(selected_rows),
        main_selected_bytes=sum(int(row["byte_size"]) for row in selected_rows),
        cost_objects=len(cost_rows),
        cost_bytes=sum(int(row["byte_size"]) for row in cost_rows),
        combined_objects=len(selected_rows) + len(cost_rows),
        combined_bytes=sum(int(row["byte_size"]) for row in selected_rows + cost_rows),
        retained_credit_objects=len(retained_digests),
        retained_credit_bytes=retained_bytes,
        coinalyze_supported=len(supported),
        coinalyze_unsupported=len(unsupported),
        coinalyze_logical_receipts=1 + len(supported),
        new_binance_raw_bytes=sum(int(row["byte_size"]) for row in selected_rows + cost_rows),
        new_coinalyze_raw_bytes=1_000_000,
        stable_requirement_bytes=1_024,
        destination="data/cex002_qualify",
        device=filesystem.device,
        report_bytes=len(report_bytes),
        manifest_compressed_bytes=int(descriptor["compressed_bytes"]),
        receipt_258_bytes=len(receipt_bytes),
        attestation_282_bytes=None,
    )
    attestation_path = repo / "research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json"
    attestation_body = _attestation(pins, filesystem)
    pins = replace(
        pins,
        attestation_282_sha256=_sha(attestation_body),
        attestation_282_bytes=len(attestation_body),
    )
    _write(attestation_path, attestation_body)

    paths = replace(
        gate2.default_paths(REPOSITORY, store),
        repository=REPOSITORY,
        report_path=report_path,
        receipt_258_path=receipt_path,
        attestation_path=attestation_path,
        lock_path=lock_path,
        amendment_ledger_path=ledger_path,
        progress_path=progress_path,
        listing_checkpoint_path=listing_checkpoint_path,
        contract_metadata_path=metadata_path,
        listing_cache_dir=listing_cache,
        coinalyze_cache_dir=coinalyze_cache,
        holdout_path=holdout_path,
        qualification_source_path=REPOSITORY / gate2.QUALIFICATION_SOURCE_RELATIVE,
        qualification_cli_path=REPOSITORY / gate2.QUALIFICATION_CLI_RELATIVE,
        attestation_source_path=REPOSITORY / gate2.ATTESTATION_SOURCE_RELATIVE,
        attestation_cli_path=REPOSITORY / gate2.ATTESTATION_CLI_RELATIVE,
        sample_dir=sample_dir,
    )

    transport = FakeTransport()
    for key, payload in zips.items():
        digest = _sha(payload)
        basename = key.rsplit("/", 1)[-1]
        transport.add(f"{gate2.VISION_OBJECT_BASE}/{key}", payload)
        transport.add(
            f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM",
            f"{digest} {basename}\n".encode(),
        )
    for native in supported:
        provider = f"{native}_PERP.A"
        params = {
            "symbols": provider,
            "interval": "daily",
            "from": str(FROM_UNIX),
            "to": str(TO_UNIX),
            "convert_to_usd": "false",
        }
        url = f"{gate2.COINALYZE_BASE}{gate2.COINALYZE_LIQUIDATION_PATH}?{urlencode(params)}"
        if native in unavailable:
            transport.add(url, b"{}", status=404)
        else:
            transport.add(url, liquidation_bodies[native])

    return {
        "paths": paths,
        "pins": pins,
        "filesystem": filesystem,
        "transport": transport,
        "store": store,
        "zips": zips,
        "selected_rows": selected_rows,
        "cost_rows": cost_rows,
        "supported": supported,
        "retain_set": retain_set,
        "credit_set": authorized,
        "retained_credit_key_set_sha256": str(
            receipt_document["physical_inputs"]["retained_credit"]["key_set_sha256"]
        ),
    }


@pytest.fixture()
def universe(tmp_path: Path) -> dict[str, Any]:
    return build_universe(tmp_path)


def _cli_args(paths: gate2.AcquisitionPaths) -> list[str]:
    return [
        "--store-root",
        str(paths.store_root),
        "--repository",
        str(REPOSITORY),
        "--report-path",
        str(paths.report_path),
        "--receipt-258-path",
        str(paths.receipt_258_path),
        "--attestation-path",
        str(paths.attestation_path),
        "--lock-path",
        str(paths.lock_path),
        "--amendment-ledger-path",
        str(paths.amendment_ledger_path),
        "--progress-path",
        str(paths.progress_path),
        "--listing-checkpoint-path",
        str(paths.listing_checkpoint_path),
        "--contract-metadata-path",
        str(paths.contract_metadata_path),
        "--listing-cache-dir",
        str(paths.listing_cache_dir),
        "--coinalyze-cache-dir",
        str(paths.coinalyze_cache_dir),
        "--holdout-path",
        str(paths.holdout_path),
    ]




def _state_conn(paths: gate2.AcquisitionPaths) -> sqlite3.Connection:
    return sqlite3.connect(paths.state_path)


def _open_state(paths: gate2.AcquisitionPaths) -> gate2.AcquisitionState:
    state = gate2.AcquisitionState(paths.state_path, paths.lockfile_path)
    state.open()
    return state


def _acquire(built: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    params: dict[str, Any] = {
        "filesystem": built["filesystem"],
        "transport": built["transport"],
        "secret": SECRET,
        "sleeper": lambda _delay: None,
    }
    params.update(kwargs)
    return gate2.run_acquire(built["paths"], built["pins"], **params)


def _begin_unfinished_run(built: dict[str, Any]) -> str:
    """Open a bound session and leave one production run unfinished."""

    _summary, state, bundle = gate2.bind_session(
        built["paths"], built["pins"], built["filesystem"], install=True
    )
    try:
        started_at = datetime.now(UTC).isoformat()
        run_id = gate2.sha256_bytes(f"{started_at}:unfinished".encode("utf-8"))
        state.begin_run(run_id, started_at, pre_capacity=bundle["capacity"])
        return run_id
    finally:
        gate2._close_session(state, bundle)


def _run_with_deadline(target: Any, *, seconds: float = 90.0) -> dict[str, Any]:
    """Run one call in a thread and prove it settles; a deadlock fails the test."""

    box: dict[str, Any] = {}

    def _runner() -> None:
        try:
            box["result"] = target()
        except BaseException as exc:  # noqa: BLE001 - the test asserts on the class
            box["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout=seconds)
    assert not thread.is_alive(), "the run did not settle and would have deadlocked"
    return box


def test_production_pins_match_adr_0029() -> None:
    pins = gate2.PRODUCTION_PINS
    assert pins.combined_objects == 736_347
    assert pins.main_selected_objects == 733_203
    assert pins.cost_objects == 3_144
    assert pins.combined_bytes == 20_356_940_843
    assert pins.retained_credit_objects == 73
    assert pins.retained_credit_bytes == 5_225_416
    assert pins.coinalyze_supported == 569
    assert pins.coinalyze_unsupported == 202
    assert pins.coinalyze_logical_receipts == 570
    assert pins.new_binance_raw_bytes == 20_351_715_427
    assert pins.new_coinalyze_raw_bytes == 30_580_702
    assert pins.combined_bytes - pins.retained_credit_bytes == pins.new_binance_raw_bytes
    assert pins.stable_requirement_bytes == 139_577_980_018
    assert "daily/trades" in gate2.FORBIDDEN_FAMILIES
    assert gate2.WORKER_CEILING == 8
    assert gate2.COINALYZE_RATE_PER_MINUTE == 40


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("report_sha256", "report 62 hash changed"),
        ("receipt_258_sha256", "receipt 258 hash changed"),
        ("attestation_282_sha256", "attestation 282 hash changed"),
        ("listing_checkpoint_sha256", "listing checkpoint hash changed"),
        ("lock_sha256", "version-4 lock hash changed"),
        ("holdout_boundary_id", "holdout boundary identity changed"),
        ("qualification_source_sha256", "qualification source identity changed"),
        ("capacity_source_sha256", "capacity source identity changed"),
    ],
)
def test_single_field_authority_tamper_is_rejected(
    universe: dict[str, Any], field: str, message: str
) -> None:
    pins = replace(universe["pins"], **{field: "a" * 64})
    with pytest.raises(gate2.AuthorityError, match=message):
        gate2.run_plan(
            universe["paths"], pins, filesystem=universe["filesystem"], transport=None
        )


def test_plan_refuses_a_network_transport(universe: dict[str, Any]) -> None:
    with pytest.raises(gate2.AuthorityError, match="network transport"):
        gate2.run_plan(
            universe["paths"],
            universe["pins"],
            filesystem=universe["filesystem"],
            transport=universe["transport"],
        )


def test_plan_validates_manifest_and_installs_sqlite(universe: dict[str, Any]) -> None:
    result = gate2.run_plan(
        universe["paths"], pins=universe["pins"], filesystem=universe["filesystem"]
    )
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    replay = gate2.build_plan(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert replay.identity == result["plan_identity"]
    second = gate2.run_plan(
        universe["paths"], pins=universe["pins"], filesystem=universe["filesystem"]
    )
    assert second["plan_identity"] == result["plan_identity"]


def test_forbidden_family_is_rejected(tmp_path: Path, universe: dict[str, Any]) -> None:
    store = tmp_path / "forbidden"
    family = "daily/trades"
    key = _key(family, "BTCUSDT", "2020-01-01")
    row = _row(key, family, "BTCUSDT", 10, "2020-01-01")
    manifest = {
        "rows": [row],
        "collisions": (),
        "rejections": (),
        "raw_validation_pending_keys": (key,),
        "object_count": 1,
        "compressed_raw_bytes": 10,
        "consumable_object_count": 0,
        "family_object_counts": {family: 1},
        "cadence_rule": gate2.CADENCE_RULE,
        "integrity_rule": gate2.INTEGRITY_RULE,
    }
    descriptor = publish_manifest_detail(manifest, store_root=store)
    pins = replace(
        universe["pins"],
        manifest_compressed_sha256=str(descriptor["compressed_sha256"]),
        manifest_uncompressed_sha256=str(descriptor["uncompressed_sha256"]),
        main_selected_objects=1,
        main_selected_bytes=10,
    )
    with pytest.raises(gate2.AuthorityError, match="forbidden family"):
        list(gate2.consume_manifest(store, descriptor, pins))


def test_coinalyze_mappings_preserve_gaps_and_reject_anchor_substitution(
    universe: dict[str, Any],
) -> None:
    plan = gate2.build_plan(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert plan.coinalyze_supported == ("BTCUSDT", "ETHUSDT")
    assert plan.coinalyze_unsupported == ("GAPUSDT",)
    assert "SOLUSDT" not in plan.coinalyze_supported
    extra = replace(universe["pins"], coinalyze_supported=99)
    with pytest.raises(gate2.AuthorityError, match="supported mapping count"):
        gate2.build_plan(universe["paths"], extra, filesystem=universe["filesystem"])


def test_current_inventory_cannot_expand_supported_set(universe: dict[str, Any]) -> None:
    plan = gate2.build_plan(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    natives = {item["native_symbol"] for item in plan.coinalyze_mappings}
    assert "SOLUSDT" not in natives


def test_fresh_plan_installs_two_hundred_two_unsupported_gaps(tmp_path: Path) -> None:
    unsupported = tuple(f"GAP{index:03d}USDT" for index in range(202))
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        supported=("BTCUSDT",),
        unsupported=unsupported,
        extra_inventory=(),
    )
    result = gate2.run_plan(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    state = _open_state(built["paths"])
    try:
        assert state.counts()["gaps"] == 202
    finally:
        state.close()
    replay = gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    assert replay["plan_identity"] == result["plan_identity"]


def test_plan_flush_fault_rolls_back(universe: dict[str, Any]) -> None:
    with pytest.raises(gate2.FaultInjected):
        gate2.run_plan(
            universe["paths"],
            universe["pins"],
            filesystem=universe["filesystem"],
            fault=gate2.NamedFault("after_plan_flush"),
        )
    path = universe["paths"].state_path
    if path.exists():
        conn = sqlite3.connect(path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM authority").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM plan_entry").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0] == 0
        finally:
            conn.close()


def test_incompatible_plan_and_row_corruption_are_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE plan_entry SET identity = identity || '-tamper' WHERE seq = 1")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="does not match"):
        _acquire(universe)


def test_code_identity_corruption_is_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE authority SET code_json = ?", ('{"policy_identity":"nope"}',))
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="code identity|not valid JSON"
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_one_writer_lock_is_exclusive(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    first = _open_state(universe["paths"])
    try:
        second = gate2.AcquisitionState(
            universe["paths"].state_path, universe["paths"].lockfile_path
        )
        with pytest.raises(gate2.UnsafeStateError, match="another writer"):
            second.open()
    finally:
        first.close()


def test_application_id_is_read_before_write(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("PRAGMA application_id=1")
    conn.close()
    state = gate2.AcquisitionState(
        universe["paths"].state_path, universe["paths"].lockfile_path
    )
    with pytest.raises(gate2.UnsafeStateError, match="application_id"):
        try:
            state.open()
        finally:
            state.close()


# --------------------------------------------------------------------------------------
# Exact state authentication: schema, domains, singletons, gaps, and semantic digest.
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("DROP INDEX idx_plan_kind", "missing an accepted object"),
        ("DROP INDEX idx_completion_content", "missing an accepted object"),
        ("CREATE INDEX idx_side ON completion(identity)", "outside the accepted schema"),
        ("CREATE TABLE shadow (x INTEGER)", "outside the accepted schema"),
    ],
)
def test_independent_schema_mutation_is_refused(
    universe: dict[str, Any], sql: str, message: str
) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute(sql)
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match=message):
        _acquire(universe)
    assert universe["transport"].calls == []


def test_redefined_state_table_is_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("ALTER TABLE attempt ADD COLUMN smuggled TEXT")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="redefined"):
        _acquire(universe)
    assert universe["transport"].calls == []


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        (
            "UPDATE completion SET validation_state = 'invented'",
            "unknown validation state",
        ),
        ("UPDATE completion SET content_sha256 = 'ZZ' || substr(content_sha256, 3)",
         "not a lowercase SHA-256"),
        ("UPDATE completion SET listed_bytes = -1", "negative or non-integer bytes"),
        ("UPDATE terminal_gap SET kind = 'other'", "terminal gap has an unknown kind"),
        ("UPDATE attempt SET class = 'weird'", "unknown classification"),
        (
            "UPDATE sidecar_fact SET provider_checksum = 'nope'",
            "not a lowercase SHA-256 pair",
        ),
        ("UPDATE charge_transition SET status = 'guessed'", "unknown status"),
    ],
)
def test_independent_domain_mutation_is_refused(
    universe: dict[str, Any], sql: str, message: str
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(sql)
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match=message):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_deleting_a_terminal_gap_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM terminal_gap")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="unsupported gap row is missing"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_altering_a_terminal_gap_fact_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(
        "UPDATE terminal_gap SET fact_json = ?",
        (gate2.compact_json({"native_symbol": "OTHER"}).decode("utf-8"),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="gap fact changed|prefix|rewritten"
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_missing_or_duplicated_singletons_fail_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM coinalyze_ledger")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="ledger row is missing"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_altered_ledger_equation_fails_closed_before_network(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    universe["transport"].calls.clear()
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE coinalyze_ledger SET charged = charged + 17")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="attributed charges"):
        _acquire(universe)
    assert universe["transport"].calls == []


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE completion SET retrieved_at = '2000-01-01T00:00:00+00:00'",
        "UPDATE completion SET revision_json = '{}' || char(10)",
        "UPDATE sidecar_fact SET sidecar_bytes = sidecar_bytes + 1",
        "UPDATE coinalyze_ledger SET charged = charged + 1",
        "UPDATE attempt SET redacted_fact_json = '{}' || char(10)",
        "UPDATE terminal_gap SET fact_json = '{}' || char(10)",
        "UPDATE authority SET plan_receipt_sha256 = '" + "a" * 64 + "'",
        "UPDATE authority SET created_at = '1999-01-01T00:00:00+00:00'",
        "UPDATE attempt SET started_at = '1999-01-01T00:00:00+00:00'",
        "UPDATE coinalyze_charge SET created_at = '1999-01-01T00:00:00+00:00'",
        "UPDATE run_metadata SET stop_reason = 'tamper'",
        "UPDATE attempt SET ended_at = started_at",
        "UPDATE run_metadata SET network_calls = network_calls + 1",
    ],
)
def test_semantic_digest_binds_every_trusted_fact(
    universe: dict[str, Any], sql: str
) -> None:
    _acquire(universe)
    state = _open_state(universe["paths"])
    try:
        before = state.semantic_digest()
    finally:
        state.close()
    conn = _state_conn(universe["paths"])
    conn.execute(sql)
    conn.commit()
    conn.close()
    state = _open_state(universe["paths"])
    try:
        assert state.semantic_digest() != before
    finally:
        state.close()


# --------------------------------------------------------------------------------------
# Publication, containment, and immutability.
# --------------------------------------------------------------------------------------


def test_content_sharding_no_replace_and_symlink_refusal(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    body = b"hello-gate2"
    digest = _sha(body)
    dest = gate2.content_path_for(universe["paths"].content_root, digest)
    assert dest.parent.name == digest[:2]
    _, path, reused = gate2.publish_bytes(
        body,
        content_root=universe["paths"].content_root,
        tmp_root=universe["paths"].tmp_root,
        device=universe["filesystem"].device,
        filesystem=universe["filesystem"],
    )
    assert path == dest and reused is False
    _, _, reused = gate2.publish_bytes(
        body,
        content_root=universe["paths"].content_root,
        tmp_root=universe["paths"].tmp_root,
        device=universe["filesystem"].device,
        filesystem=universe["filesystem"],
    )
    assert reused is True
    other_root = tmp_path / "other"
    (other_root / digest[:2]).mkdir(parents=True)
    (other_root / digest[:2] / digest).write_bytes(b"different-bytes-not-hello")
    with pytest.raises(gate2.UnsafeStateError, match="collision"):
        gate2.publish_bytes(
            body,
            content_root=other_root,
            tmp_root=other_root / "tmp",
            device=universe["filesystem"].device,
            filesystem=universe["filesystem"],
        )


def test_intermediate_parent_symlink_cannot_escape_the_root(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    content_root = universe["paths"].content_root
    content_root.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (content_root / "ab").symlink_to(outside, target_is_directory=True)
    with pytest.raises(gate2.UnsafeStateError, match="parent component is a symlink"):
        gate2.open_dir_chain(content_root, ("ab",))
    (outside / "victim").write_bytes(b"x")
    with pytest.raises(gate2.UnsafeStateError):
        gate2.open_regular_file(content_root, content_root / "ab" / "victim")


def test_leaf_symlink_is_refused_for_authority_and_content(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    real = tmp_path / "real.json"
    real.write_bytes(b"{}")
    link_root = tmp_path / "auth"
    link_root.mkdir()
    link = link_root / "linked.json"
    link.symlink_to(real)
    with pytest.raises(gate2.AuthorityError, match="missing or is a symlink"):
        gate2.read_authority_file(link, label="holdout boundary", root=link_root)


def test_publication_race_reuses_identical_bytes(universe: dict[str, Any]) -> None:
    body = b"raced-content"
    digest = _sha(body)
    dest = gate2.content_path_for(universe["paths"].content_root, digest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    published, path, reused = gate2.publish_bytes(
        body,
        content_root=universe["paths"].content_root,
        tmp_root=universe["paths"].tmp_root,
        device=universe["filesystem"].device,
        filesystem=universe["filesystem"],
    )
    assert published == digest and path == dest and reused is True
    partials = [
        item
        for item in universe["paths"].tmp_root.iterdir()
        if item.name.startswith(".partial-")
    ] if universe["paths"].tmp_root.is_dir() else []
    assert partials == []


def test_receipt_write_is_looped_and_rehashed_under_short_writes(
    universe: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    real_write = os.write
    directory = universe["paths"].run_receipt_dir

    def short_write(fd: int, data: Any) -> int:
        view = memoryview(data)
        return real_write(fd, view[:1]) if len(view) > 1 else real_write(fd, view)

    monkeypatch.setattr(gate2.os, "write", short_write)
    document = {"schema_version": "test", "payload": "x" * 512}
    published = gate2.write_named_receipt(
        document, directory, universe["filesystem"].device, universe["filesystem"]
    )
    monkeypatch.undo()
    body = gate2.canonical_json(document)
    assert published["bytes"] == len(body)
    assert Path(published["path"]).read_bytes() == body
    assert _sha(body) == published["sha256"]


def test_zip_and_sidecar_validation(tmp_path: Path) -> None:
    payload = _zip("member.csv", b"1,2,3\n")
    digest = _sha(payload)
    basename = "BTCUSDT-klines-2020-01-01.zip"
    assert gate2.parse_sidecar(f"{digest} {basename}\n".encode(), basename=basename) == digest
    path = tmp_path / "ok.zip"
    path.write_bytes(payload)
    gate2.validate_zip(path)
    unsafe = tmp_path / "unsafe.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        handle.writestr("../escape.csv", b"nope")
    unsafe.write_bytes(buffer.getvalue())
    with pytest.raises(gate2.AcquisitionError, match="unsafe"):
        gate2.validate_zip(unsafe)
    empty = tmp_path / "empty.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        handle.writestr("blank.csv", b"")
    empty.write_bytes(buffer.getvalue())
    with pytest.raises(gate2.AcquisitionError, match="empty or not a file"):
        gate2.validate_zip(empty)


# --------------------------------------------------------------------------------------
# Production acquisition, resume, and replay.
# --------------------------------------------------------------------------------------


def test_acquire_completes_with_typed_gaps_and_replays_without_network(
    universe: dict[str, Any],
) -> None:
    first = _acquire(universe)
    assert first["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert first["network_call_count"] > 0
    assert SECRET not in json.dumps(first)
    second_transport = FakeTransport()
    second = _acquire(universe, transport=second_transport)
    assert second["network_calls"] == []
    assert second["network_call_count"] == 0
    assert second["exit_code"] == first["exit_code"]
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert verified["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert Path(verified["terminal_manifest"]).name.endswith(".jsonl.gz")


def test_cli_plan_acquire_verify_production_paths(universe: dict[str, Any]) -> None:
    cli = _load_cli()
    location = _cli_args(universe["paths"])
    assert (
        cli.main(
            ["plan", *location],
            pins=universe["pins"],
            filesystem=universe["filesystem"],
            transport=universe["transport"],
        )
        == gate2.EXIT_COMPLETE
    )
    status = cli.main(
        ["acquire", *location],
        pins=universe["pins"],
        filesystem=universe["filesystem"],
        transport=universe["transport"],
        secret=SECRET,
    )
    assert status == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert (
        cli.main(
            ["verify", *location],
            pins=universe["pins"],
            filesystem=universe["filesystem"],
            transport=universe["transport"],
        )
        == status
    )


@pytest.mark.parametrize("flag", ["--workers", "--symbol", "--family", "--force", "--skip"])
def test_cli_rejects_forbidden_flags(flag: str) -> None:
    cli = _load_cli()
    with pytest.raises(SystemExit):
        cli.main(["acquire", flag, "1"])


def test_missing_cli_identity_is_fatal(universe: dict[str, Any], tmp_path: Path) -> None:
    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir()
    paths = replace(universe["paths"], repository=empty_repo)
    with pytest.raises(gate2.AuthorityError, match="acquisition CLI identity is missing"):
        gate2.run_plan(paths, universe["pins"], filesystem=universe["filesystem"])


def test_crash_before_raw_is_resumable(universe: dict[str, Any]) -> None:
    key = universe["selected_rows"][0]["key"]
    _acquire(universe, fault=gate2.NamedFault("before_raw_publication", key))
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_short_body_does_not_delete_published_content(universe: dict[str, Any]) -> None:
    key = universe["selected_rows"][0]["key"]
    payload = universe["zips"][key]
    digest = _sha(payload)
    gate2.publish_bytes(
        payload,
        content_root=universe["paths"].content_root,
        tmp_root=universe["paths"].tmp_root,
        device=universe["filesystem"].device,
        filesystem=universe["filesystem"],
    )
    dest = gate2.content_path_for(universe["paths"].content_root, digest)
    universe["transport"].add(f"{gate2.VISION_OBJECT_BASE}/{key}", payload[:8])
    _acquire(universe, max_objects=1)
    assert dest.is_file()
    assert dest.read_bytes() == payload


def test_sidecar_conflict_is_rejected(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    state = _open_state(universe["paths"])
    try:
        key = universe["selected_rows"][0]["key"]
        target = universe["paths"].content_root / "aa" / ("a" * 64)
        state.record_sidecar(
            gate2.PROVIDER_BINANCE, key, "a" * 64, target, "b" * 64, sidecar_bytes=12
        )
        with pytest.raises(gate2.UnsafeStateError, match="sidecar fact revision"):
            state.record_sidecar(
                gate2.PROVIDER_BINANCE,
                key,
                "c" * 64,
                target,
                "d" * 64,
                sidecar_bytes=12,
            )
    finally:
        state.close()


def test_retry_429_and_transport_failure(universe: dict[str, Any]) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].status[url] = [429, 200]
    universe["transport"].headers[url] = {"Retry-After": "120"}
    slept: list[float] = []
    result = _acquire(universe, sleeper=slept.append)
    assert 60 in slept
    assert result["attempts"] == result["network_call_count"]
    assert result["attempts"] > 0


def test_transport_failure_is_retried_for_binance(universe: dict[str, Any]) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].raise_once[url] = ConnectionError("synthetic")
    result = _acquire(universe)
    assert result["attempts"] > 0
    assert result["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        transport = conn.execute(
            "SELECT COUNT(*) FROM attempt WHERE class = ?", (gate2.RETRY_TRANSPORT,)
        ).fetchone()[0]
    finally:
        conn.close()
    assert transport >= 1


def test_concurrency_ceiling_without_wall_sleep(universe: dict[str, Any]) -> None:
    result = _acquire(universe)
    assert universe["transport"].max_in_flight <= gate2.WORKER_CEILING
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_graceful_object_bound_is_resumable(universe: dict[str, Any]) -> None:
    first = _acquire(universe, max_objects=2)
    assert first["exit_code"] == gate2.EXIT_RESUMABLE_PARTIAL
    second = _acquire(universe)
    assert second["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


@pytest.mark.parametrize(
    ("bounds", "message"),
    [
        ({"max_objects": 0}, "positive integer"),
        ({"max_objects": -3}, "positive integer"),
        ({"max_wall_seconds": 0.0}, "positive finite"),
        ({"max_wall_seconds": float("inf")}, "positive finite"),
        ({"max_wall_seconds": float("nan")}, "positive finite"),
    ],
)
def test_stop_bounds_must_be_positive_and_finite(
    universe: dict[str, Any], bounds: dict[str, Any], message: str
) -> None:
    with pytest.raises(gate2.AuthorityError, match=message):
        _acquire(universe, **bounds)
    assert universe["transport"].calls == []


def test_resume_reproves_completed_provider_objects(universe: dict[str, Any]) -> None:
    _acquire(universe)
    key = universe["selected_rows"][0]["key"]
    digest = _sha(universe["zips"][key])
    published = gate2.content_path_for(universe["paths"].content_root, digest)
    published.write_bytes(b"tampered-published-raw-object")
    with pytest.raises(gate2.UnsafeStateError, match="digest changed"):
        _acquire(universe)


def test_corrupt_completed_retained_row_is_not_skipped(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    conn.execute(
        "UPDATE sidecar_fact SET provider_checksum = ? WHERE identity = ?",
        ("b" * 64, key),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="provider checksum|rewritten or deleted"
    ):
        _acquire(built)


def test_retained_credit_adopts_cost_keys_without_network(tmp_path: Path) -> None:
    days = tuple(
        (datetime(2020, 1, 1) + timedelta(days=index)).strftime("%Y-%m-%d")
        for index in range(68)
    )
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        archive_intervals=days,
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
        retain_all=True,
    )
    assert built["pins"].retained_credit_objects == 73
    assert sum(1 for key in built["retain_set"] if "book" in key) == 5
    before = sum(
        item.stat().st_blocks
        for item in built["paths"].sample_dir.iterdir()
        if item.is_file()
    )
    result = _acquire(built)
    assert [url for url in result["network_calls"] if "data.binance.vision" in url] == []
    state = _open_state(built["paths"])
    try:
        retained = [
            item
            for item in state.iter_completions()
            if item["validation_state"] == gate2.OUTCOME_RETAINED
        ]
        assert len(retained) == 73
        assert len([item for item in retained if "book" in item["identity"]]) == 5
    finally:
        state.close()
    after = sum(
        item.stat().st_blocks
        for item in built["paths"].sample_dir.iterdir()
        if item.is_file()
    )
    assert after == before
    for item in retained:
        published = Path(item["content_path"])
        source = built["paths"].sample_dir / item["content_sha256"]
        assert published.stat().st_ino == source.stat().st_ino
    replay = _acquire(built)
    assert replay["network_call_count"] == 0
    plan = _plan_receipt(built)
    credit = plan["retained_credit"]
    assert credit["valid_requirement_keys"] == 73
    assert credit["objects"] == 73
    assert credit["selected_retained_keys"] == 68
    assert credit["cost_retained_keys"] == 5
    assert credit["unverified_objects"] == 0
    assert credit["bytes"] == built["pins"].retained_credit_bytes
    assert credit["key_set_sha256"] == built["retained_credit_key_set_sha256"]
    assert "keys" not in credit


def test_retained_tamper_is_fail_closed(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    sample = next(built["paths"].sample_dir.iterdir())
    sample.write_bytes(b"tampered-retained-bytes")
    with pytest.raises(gate2.AuthorityError, match="retained"):
        _acquire(built)


def test_fatal_worker_settles_and_keeps_its_distinct_class(
    universe: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COINALYZE_API_KEY", raising=False)
    box = _run_with_deadline(lambda: _acquire(universe, secret=None))
    error = box.get("error")
    assert isinstance(error, gate2.AuthorityError)
    assert gate2.map_exception(error) == gate2.EXIT_AUTHORITY_INVALID
    assert gate2.map_exception(gate2.UnsafeStateError("x")) == gate2.EXIT_UNSAFE_STATE


def test_fatal_unsafe_state_settles_without_hanging(universe: dict[str, Any]) -> None:
    _acquire(universe, max_objects=1)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE sidecar_fact SET sidecar_bytes = sidecar_bytes + 1")
    conn.commit()
    conn.close()
    box = _run_with_deadline(lambda: _acquire(universe))
    assert isinstance(box.get("error"), gate2.UnsafeStateError)


# --------------------------------------------------------------------------------------
# The Coinalyze budget, publication, and completion transition.
# --------------------------------------------------------------------------------------


def test_coinalyze_empty_unavailable_secret_and_404_bytes(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        empty_liquidation=frozenset({"BTCUSDT"}),
        unavailable=frozenset({"ETHUSDT"}),
    )
    result = _acquire(built)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert result["counts"]["coinalyze_charged"] > 0
    assert SECRET.encode() not in built["paths"].state_path.read_bytes()
    for url, headers in built["transport"].calls:
        assert SECRET not in url
        if "liquidation-history" in url:
            assert headers.get("api_key") == SECRET
    state = _open_state(built["paths"])
    try:
        outcomes = {
            item["identity"]: item["validation_state"]
            for item in state.iter_completions()
            if item["provider"] == gate2.PROVIDER_COINALYZE
        }
    finally:
        state.close()
    assert gate2.OUTCOME_EMPTY_HISTORY in outcomes.values()
    assert gate2.OUTCOME_UNAVAILABLE in outcomes.values()


def test_coinalyze_numeric_json_and_missing_symbol(universe: dict[str, Any]) -> None:
    provider = "BTCUSDT_PERP.A"
    parsed, summary = gate2.parse_liquidation_history(
        json.dumps(
            [{"symbol": provider, "history": [{"t": FROM_UNIX, "l": 1.25, "s": 0}]}]
        ).encode(),
        provider_symbol=provider,
        start=FROM_UNIX,
        end=TO_UNIX,
    )
    assert parsed == "history" and summary.points == 1
    with pytest.raises(gate2.AcquisitionError, match="omitted the provider symbol"):
        gate2.parse_liquidation_history(
            json.dumps([{"history": [{"t": FROM_UNIX, "l": "1", "s": "1"}]}]).encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )
    for body in (b"[]", b"{}"):
        with pytest.raises(gate2.AcquisitionError, match="omitted the provider symbol"):
            gate2.parse_liquidation_history(
                body, provider_symbol=provider, start=FROM_UNIX, end=TO_UNIX
            )
    with pytest.raises(gate2.AcquisitionError, match="outside the fixed bounds"):
        gate2.parse_liquidation_history(
            json.dumps(
                [{"symbol": provider, "history": [{"t": TO_UNIX + 86400, "l": 1, "s": 1}]}]
            ).encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )


def test_bounded_incremental_parsing_refuses_unbounded_tokens() -> None:
    provider = "X_PERP.A"
    oversize = "9" * (gate2.MAX_JSON_TOKEN_BYTES + 8)
    with pytest.raises(gate2.AcquisitionError, match="ceiling"):
        gate2.parse_liquidation_history(
            f'[{{"symbol":"{provider}","note":"{oversize}"}}]'.encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )
    deep = "[" * (gate2.MAX_JSON_DEPTH + 4) + "]" * (gate2.MAX_JSON_DEPTH + 4)
    with pytest.raises(gate2.AcquisitionError, match="depth"):
        gate2.parse_liquidation_history(
            f'[{{"symbol":"{provider}","extra":{deep},"history":[]}}]'.encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )


def test_streaming_parse_is_chunk_independent() -> None:
    provider = "X_PERP.A"
    body = json.dumps(
        [
            {
                "symbol": provider,
                "history": [
                    {"t": FROM_UNIX + 86400 * index, "l": index, "s": index + 1}
                    for index in range(64)
                ],
            }
        ]
    ).encode()
    whole = gate2.validate_liquidation_stream(
        iter([body]), provider_symbol=provider, start=FROM_UNIX, end=TO_UNIX
    )
    single = gate2.validate_liquidation_stream(
        iter([body[index : index + 1] for index in range(len(body))]),
        provider_symbol=provider,
        start=FROM_UNIX,
        end=TO_UNIX,
    )
    assert whole == single
    assert whole.points == 64


def test_split_chunk_secret_is_detected_and_never_published(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
    )
    url = built["transport"].liquidation_url("BTCUSDT")
    leaked = json.dumps(
        [{"symbol": "BTCUSDT_PERP.A", "note": SECRET, "history": []}]
    ).encode()
    cut = leaked.index(SECRET.encode()) + 4
    built["transport"].add(url, leaked, chunks=[leaked[:cut], leaked[cut:]])
    result = _acquire(built)
    assert any("secret leaked" in item for item in result["errors"])
    assert SECRET.encode() not in built["paths"].state_path.read_bytes()
    assert SECRET not in json.dumps(result)
    assert result["counts"]["coinalyze_charged"] == 0
    for shard in built["paths"].content_root.glob("*/*"):
        assert SECRET.encode() not in shard.read_bytes()
    assert not any(built["paths"].tmp_root.glob(".partial-*"))


def test_coinalyze_over_budget_body_is_absent_from_every_record(
    universe: dict[str, Any],
) -> None:
    tight = replace(universe["pins"], new_coinalyze_raw_bytes=4)
    result = gate2.run_acquire(
        universe["paths"],
        tight,
        filesystem=universe["filesystem"],
        transport=universe["transport"],
        secret=SECRET,
        sleeper=lambda _delay: None,
    )
    assert any(
        "exceed the accepted allocation" in item or "ceiling" in item
        for item in result["errors"]
    )
    state = _open_state(universe["paths"])
    try:
        assert state.counts()["coinalyze_charged"] == 0
        liquidation = [
            item
            for item in state.iter_completions()
            if item["provider"] == gate2.PROVIDER_COINALYZE
            and item["validation_state"] != gate2.OUTCOME_RETAINED_INVENTORY
        ]
        assert liquidation == []
        assert state.open_charge_count() == 0
    finally:
        state.close()
    assert not any(universe["paths"].tmp_root.glob(".partial-*"))


def test_zero_remaining_budget_refuses_before_any_network_call(
    universe: dict[str, Any],
) -> None:
    exhausted = replace(universe["pins"], new_coinalyze_raw_bytes=0)
    result = gate2.run_acquire(
        universe["paths"],
        exhausted,
        filesystem=universe["filesystem"],
        transport=universe["transport"],
        secret=SECRET,
        sleeper=lambda _delay: None,
    )
    assert result["stop_reason"] in {"coinalyze_budget", "partial"}
    assert [
        url for url, _headers in universe["transport"].calls if "liquidation-history" in url
    ] == []


def test_missing_ledger_row_refuses_before_any_network_call(
    universe: dict[str, Any],
) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM coinalyze_ledger")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="ledger row is missing"):
        _acquire(universe)
    assert universe["transport"].calls == []


def test_coinalyze_ceiling_is_exact_across_runs(tmp_path: Path) -> None:
    built = build_universe(tmp_path, archive_families=("daily/klines",))
    first = _acquire(built, max_objects=1)
    charged_first = first["counts"]["coinalyze_charged"]
    second = _acquire(built)
    charged_total = second["counts"]["coinalyze_charged"]
    assert charged_total >= charged_first
    state = _open_state(built["paths"])
    try:
        conn = state._db()
        settled = conn.execute(
            "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
            "WHERE (SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
            "AND t.identity = c.identity AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) = ?",
            (gate2.CHARGE_SETTLED,),
        ).fetchone()[0]
        bodies = conn.execute(
            "SELECT COALESCE(SUM(listed_bytes), 0) FROM completion WHERE provider = ? "
            "AND validation_state != ?",
            (gate2.PROVIDER_COINALYZE, gate2.OUTCOME_RETAINED_INVENTORY),
        ).fetchone()[0]
        assert int(settled) == int(charged_total) == int(bodies)
        state.authenticate_singletons()
    finally:
        state.close()
    third = _acquire(built)
    assert third["counts"]["coinalyze_charged"] == charged_total


def test_retained_inventory_is_never_charged(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    try:
        inventory = conn.execute(
            "SELECT identity FROM completion WHERE validation_state = ?",
            (gate2.OUTCOME_RETAINED_INVENTORY,),
        ).fetchall()
        assert len(inventory) == 1
        charged = conn.execute(
            "SELECT COUNT(*) FROM coinalyze_charge WHERE identity = ?",
            (inventory[0][0],),
        ).fetchone()[0]
    finally:
        conn.close()
    assert charged == 0


def test_crash_after_publication_is_finished_on_resume(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    identity = None
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        for plan in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_LIQUIDATION,)):
            identity = plan.identity
    finally:
        state.close()
    assert identity is not None
    partial = _acquire(
        built, fault=gate2.NamedFault("after_coinalyze_publication", identity)
    )
    assert partial["exit_code"] == gate2.EXIT_RESUMABLE_PARTIAL
    state = _open_state(built["paths"])
    try:
        open_charges = list(state.iter_open_charges())
        assert len(open_charges) == 1
        assert state.completion_fact(gate2.PROVIDER_COINALYZE, identity) is None
        reserved = state.counts()["coinalyze_charged"]
        assert reserved > 0
    finally:
        state.close()
    resumed = _acquire(built)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    state = _open_state(built["paths"])
    try:
        assert state.open_charge_count() == 0
        assert state.completion_fact(gate2.PROVIDER_COINALYZE, identity) is not None
        assert state.counts()["coinalyze_charged"] == reserved
        state.authenticate_singletons()
    finally:
        state.close()
    assert [
        url
        for url, _headers in built["transport"].calls
        if "liquidation-history" in url
    ].count(built["transport"].liquidation_url("BTCUSDT")) == 1


def test_crash_before_publication_refunds_the_reservation(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        identity = next(
            plan.identity
            for plan in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_LIQUIDATION,))
        )
    finally:
        state.close()
    _begin_unfinished_run(built)
    # Durable reservation owned by the unfinished run; bytes were never published.
    conn = _state_conn(built["paths"])
    conn.execute(
        "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            "d" * 64,
            4096,
            200,
            gate2.OUTCOME_CHECKSUM_VERIFIED,
            0,
            "e" * 64,
            "{}\n",
            "{}\n",
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute(
        "INSERT INTO charge_transition(provider, identity, generation, status, at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            gate2.CHARGE_RESERVED,
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute("UPDATE coinalyze_ledger SET charged = charged + 4096")
    conn.commit()
    conn.close()
    resumed = _acquire(built)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(built["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["high_watermarks"]["charge_hi"] == 1
    assert interrupted["high_watermarks"]["transition_hi"] == 1
    state = _open_state(built["paths"])
    try:
        state.authenticate_singletons()
        assert state.open_charge_count() == 0
        conn = state._db()
        settled = conn.execute(
            "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
            "WHERE (SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
            "AND t.identity = c.identity AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) != ?",
            (gate2.CHARGE_RELEASED,),
        ).fetchone()[0]
        assert int(settled) == state.counts()["coinalyze_charged"]
        released = conn.execute(
            "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
            "WHERE (SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
            "AND t.identity = c.identity AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) = ?",
            (gate2.CHARGE_RELEASED,),
        ).fetchone()[0]
        assert int(released) == 4096
        assert int(settled) == state.counts()["coinalyze_charged"]
    finally:
        state.close()


def test_orphan_charge_tail_without_open_run_is_refused(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        identity = next(
            plan.identity
            for plan in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_LIQUIDATION,))
        )
    finally:
        state.close()
    conn = _state_conn(built["paths"])
    conn.execute(
        "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            "d" * 64,
            4096,
            200,
            gate2.OUTCOME_CHECKSUM_VERIFIED,
            0,
            "e" * 64,
            "{}\n",
            "{}\n",
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute(
        "INSERT INTO charge_transition(provider, identity, generation, status, at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            gate2.CHARGE_RESERVED,
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute("UPDATE coinalyze_ledger SET charged = charged + 4096")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="unsealed fact tail"):
        _acquire(built)


def test_coinalyze_5xx_retry_limits_every_attempt_and_closes_responses(
    tmp_path: Path,
) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    url = built["transport"].liquidation_url("BTCUSDT")
    built["transport"].status[url] = [503, 429, 200]
    built["transport"].headers[url] = {"Retry-After": "5"}
    limiter = gate2.RateLimiter(
        max_calls=1000, period_s=60.0, sleeper=lambda _delay: None, clock=lambda: 0.0
    )
    slept: list[float] = []
    result = _acquire(built, sleeper=slept.append, limiter=limiter)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    attempts = [url_ for url_, _h in built["transport"].calls if "liquidation-history" in url_]
    assert len(attempts) == 3
    assert limiter.calls == 3
    assert 5.0 in slept
    assert built["transport"].closed_responses == built["transport"].opened_responses
    conn = _state_conn(built["paths"])
    try:
        classes = [
            str(row[0])
            for row in conn.execute(
                "SELECT class FROM attempt WHERE identity LIKE '%liquidation-history%' "
                "ORDER BY id"
            )
        ]
    finally:
        conn.close()
    assert classes == [gate2.RETRY_TRANSIENT, gate2.RETRY_RATE_LIMIT, gate2.RETRY_OK]


def test_rate_limiter_enforces_forty_per_minute_without_hanging() -> None:
    clock = {"now": 0.0}
    slept: list[float] = []

    def sleeper(delay: float) -> None:
        slept.append(delay)
        clock["now"] += delay

    limiter = gate2.RateLimiter(
        max_calls=2, period_s=60.0, sleeper=sleeper, clock=lambda: clock["now"]
    )
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()
    assert slept == [60.0]
    assert clock["now"] == 60.0
    assert limiter.calls == 3


# --------------------------------------------------------------------------------------
# Capacity, terminal reconciliation, and bounded production paths.
# --------------------------------------------------------------------------------------


def test_capacity_equation_includes_next_transfer(universe: dict[str, Any]) -> None:
    pins = universe["pins"]
    transfer = 100
    available = gate2.MINIMUM_OPERATING_RESERVE_BYTES + pins.stable_requirement_bytes + transfer
    equal = gate2.evaluate_capacity(
        pins=pins, available_bytes=available, next_transfer_bytes=transfer
    )
    assert equal["storage_preflight_state"] == "sufficient"
    below = gate2.evaluate_capacity(
        pins=pins, available_bytes=available - 1, next_transfer_bytes=transfer
    )
    assert below["storage_preflight_state"] == "blocked"
    above = gate2.evaluate_capacity(
        pins=pins, available_bytes=available + 1, next_transfer_bytes=transfer
    )
    assert above["storage_preflight_state"] == "sufficient"


def test_stable_requirement_is_never_reduced_by_progress(universe: dict[str, Any]) -> None:
    first = gate2.evaluate_capacity(pins=universe["pins"], available_bytes=AVAILABLE)
    after = gate2.evaluate_capacity(
        pins=universe["pins"], available_bytes=AVAILABLE, next_transfer_bytes=10
    )
    assert first["stable_requirement_bytes"] == after["stable_requirement_bytes"]


def test_capacity_guard_stops_before_transfer(universe: dict[str, Any]) -> None:
    filesystem = FakeFilesystem(device=universe["filesystem"].device, available=100)
    with pytest.raises(gate2.CapacityBlocked):
        gate2.run_plan(universe["paths"], universe["pins"], filesystem=filesystem)
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    with pytest.raises(gate2.CapacityBlocked):
        _acquire(universe, filesystem=filesystem)


def test_capacity_is_recomputed_at_the_sidecar_and_raw_boundaries(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        supported=(),
        unsupported=(),
        extra_inventory=(),
    )
    filesystem = FakeFilesystem(device=built["pins"].device)
    result = gate2.run_acquire(
        built["paths"],
        built["pins"],
        filesystem=filesystem,
        transport=built["transport"],
        secret=SECRET,
        sleeper=lambda _delay: None,
    )
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    binance_objects = built["pins"].combined_objects
    # One preflight, one post-run fact, and the prospective equation revalidated before
    # both the sidecar transfer and the raw transfer of every object.
    assert filesystem.calls == 2 + 2 * binance_objects
    guard = gate2.CapacityGuard(
        pins=built["pins"],
        paths=built["paths"],
        filesystem=FakeFilesystem(device=built["pins"].device, available=100),
    )
    with pytest.raises(gate2.CapacityBlocked, match="capacity guard failed"):
        guard.require(gate2.SIDECAR_CEILING_BYTES, boundary="binance_sidecar")
    assert guard.blocked is True


def test_a_blocked_post_capacity_fact_never_reports_complete(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    filesystem = FakeFilesystem(
        device=universe["filesystem"].device,
        available=universe["filesystem"].available,
        sequence=[AVAILABLE, 100],
    )
    result = _acquire(universe, filesystem=filesystem)
    assert result["exit_code"] == gate2.EXIT_CAPACITY_BLOCKED
    receipt = json.loads(Path(result["run_receipt"]["path"]).read_text(encoding="utf-8"))
    assert receipt["capacity_blocked"] is True
    assert receipt["post_capacity"]["storage_preflight_state"] == "blocked"


def test_verify_refuses_network_and_incomplete_state(universe: dict[str, Any]) -> None:
    _acquire(universe, max_objects=1)
    with pytest.raises(gate2.UnsafeStateError, match="pending"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )
    with pytest.raises(gate2.AuthorityError, match="network transport"):
        gate2.verify_state(
            universe["paths"],
            universe["pins"],
            filesystem=universe["filesystem"],
            transport=universe["transport"],
        )
    assert not universe["paths"].terminal_dir.exists() or not list(
        universe["paths"].terminal_dir.glob("*.jsonl.gz")
    )


def test_verify_reconciles_exact_counts_bytes_and_equations(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    verified = gate2.verify_state(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    facts = verified["reconciliation"]
    pins = built["pins"]
    assert facts["binance_plan_objects"] == pins.combined_objects
    assert facts["binance_completions"] == pins.combined_objects
    assert facts["binance_listed_bytes"] == pins.combined_bytes
    assert facts["coinalyze_logical_receipts"] == pins.coinalyze_logical_receipts
    assert facts["unsupported_gaps"] == pins.coinalyze_unsupported
    assert facts["retained_objects"] == pins.retained_credit_objects
    assert facts["retained_listed_bytes"] == pins.retained_credit_bytes
    assert (
        facts["new_listed_bytes"]
        == pins.combined_bytes - pins.retained_credit_bytes
    )
    assert facts["sidecar_objects"] == pins.combined_objects
    assert facts["coinalyze_charged_bytes"] == facts["coinalyze_response_bytes"]


def test_verify_refuses_a_changed_retained_reconciliation(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    conn.execute(
        "UPDATE completion SET validation_state = ? WHERE identity = ?",
        (gate2.OUTCOME_CHECKSUM_VERIFIED, key),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError,
        match="retained label disagrees|rewritten or deleted|retained object count",
    ):
        gate2.verify_state(
            built["paths"], built["pins"], filesystem=built["filesystem"]
        )
    if built["paths"].terminal_dir.exists():
        assert list(built["paths"].terminal_dir.glob("*.jsonl.gz")) == []


def test_a_changed_accepted_count_cannot_attach_to_an_installed_plan(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    tampered = replace(universe["pins"], retained_credit_objects=99)
    with pytest.raises(gate2.AuthorityError, match="retained credit object count"):
        gate2.verify_state(
            universe["paths"], tampered, filesystem=universe["filesystem"]
        )


def test_verify_reproves_provider_semantics_not_only_hashes(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(
        "UPDATE completion SET revision_json = ? WHERE provider = ? "
        "AND validation_state = ?",
        (gate2.compact_json({"points": 999, "status": 200}).decode("utf-8"),
         gate2.PROVIDER_COINALYZE,
         gate2.OUTCOME_CHECKSUM_VERIFIED),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="point count disagrees|rewritten or deleted"
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_verify_requires_the_sidecar_to_name_its_raw_digest(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE completion SET sidecar_sha256 = NULL WHERE provider = ?",
                 (gate2.PROVIDER_BINANCE,))
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="sidecar|rewritten or deleted"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_sidecar_physical_bytes_are_in_the_unique_aggregation(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    facts = verified["reconciliation"]
    conn = _state_conn(universe["paths"])
    try:
        content_only = conn.execute(
            "SELECT COALESCE(SUM(sz), 0) FROM (SELECT content_sha256, "
            "MIN(listed_bytes) AS sz FROM completion GROUP BY content_sha256)"
        ).fetchone()[0]
        sidecar_only = conn.execute(
            "SELECT COALESCE(SUM(sz), 0) FROM (SELECT sidecar_sha256, "
            "MIN(sidecar_bytes) AS sz FROM sidecar_fact GROUP BY sidecar_sha256)"
        ).fetchone()[0]
    finally:
        conn.close()
    assert facts["unique_physical_bytes"] == int(content_only) + int(sidecar_only)
    assert facts["sidecar_bytes"] > 0
    assert facts["unique_physical_bytes"] > int(content_only)


def test_repeated_verification_is_byte_identical_and_offline(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    universe["transport"].calls.clear()
    first = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    second = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert first["terminal_receipt"]["sha256"] == second["terminal_receipt"]["sha256"]
    assert first["terminal_manifest"] == second["terminal_manifest"]
    assert second["terminal_receipt"]["reused"] is True
    manifest = Path(first["terminal_manifest"]).read_bytes()
    assert manifest[:4] == b"\x1f\x8b\x08\x00"
    assert manifest[4:8] == b"\x00\x00\x00\x00"
    assert universe["transport"].calls == []
    assert len(list(universe["paths"].terminal_dir.glob("*.jsonl.gz"))) == 1


def test_terminal_artifacts_are_absent_until_the_whole_proof_succeeds(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE coinalyze_ledger SET charged = charged + 5")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )
    if universe["paths"].terminal_dir.exists():
        assert list(universe["paths"].terminal_dir.glob("*.jsonl.gz")) == []


def test_production_paths_keep_bounded_collections_and_exact_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gate2, "CURSOR_BATCH", 8)
    days = tuple(
        (datetime(2020, 1, 1) + timedelta(days=index)).strftime("%Y-%m-%d")
        for index in range(24)
    )
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        archive_intervals=days,
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
    )
    result = _acquire(built)
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    assert result["network_call_count"] > gate2.NETWORK_SAMPLE_CEILING
    assert len(result["network_calls"]) == gate2.NETWORK_SAMPLE_CEILING
    assert result["attempts"] == result["network_call_count"]
    receipt = json.loads(Path(result["run_receipt"]["path"]).read_text(encoding="utf-8"))
    _assert_bounded(receipt)
    verified = gate2.verify_state(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    terminal = json.loads(
        Path(verified["terminal_receipt"]["path"]).read_text(encoding="utf-8")
    )
    _assert_bounded(terminal)
    assert verified["reconciliation"]["binance_completions"] == built["pins"].combined_objects


def _assert_bounded(document: Any) -> None:
    """No receipt field may grow with the universe."""

    if isinstance(document, dict):
        for value in document.values():
            _assert_bounded(value)
    elif isinstance(document, list):
        assert len(document) <= gate2.NETWORK_SAMPLE_CEILING
        for value in document:
            _assert_bounded(value)


def test_coordinator_is_the_only_writer_and_settles_deterministically(
    universe: dict[str, Any],
) -> None:
    state = gate2.AcquisitionState(
        universe["paths"].state_path, universe["paths"].lockfile_path
    )
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    state.open()
    try:
        coordinator = gate2.Coordinator(state)
        coordinator.start()
        identities = [
            (plan.provider, plan.identity) for plan in state.iter_plan_rows()
        ]
        assert len(identities) >= 16
        results: list[int] = []
        errors: list[BaseException] = []

        def _writer(index: int) -> None:
            try:
                provider, identity = identities[index]
                coordinator.call(
                    "record_attempt",
                    provider,
                    identity,
                    gate2.RETRY_OK,
                    status_code=200,
                    fact={"index": index},
                )
                results.append(index)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_writer, args=(index,)) for index in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
            assert not thread.is_alive()
        coordinator.stop()
        assert errors == []
        assert sorted(results) == list(range(16))
        assert state.counts()["attempts"] == 16
    finally:
        state.close()


def test_a_provider_cannot_carry_another_providers_outcome(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(
        "UPDATE completion SET validation_state = ? WHERE provider = ?",
        (gate2.OUTCOME_EMPTY_HISTORY, gate2.PROVIDER_BINANCE),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError,
        match="Binance completion carries|rewritten or deleted",
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_contradictory_charge_descriptor_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(
        "UPDATE coinalyze_charge SET http_status = 404, outcome = ?",
        (gate2.OUTCOME_CHECKSUM_VERIFIED,),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="404|rewritten or deleted|contradict"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_reported_attempts_are_the_durable_attempt_facts(
    universe: dict[str, Any],
) -> None:
    before = 0
    first = _acquire(universe)
    conn = _state_conn(universe["paths"])
    try:
        durable = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
    finally:
        conn.close()
    assert first["attempts"] == durable - before
    assert first["network_call_count"] == first["attempts"]
    receipt = json.loads(Path(first["run_receipt"]["path"]).read_text(encoding="utf-8"))
    assert receipt["attempt_delta"] == durable
    second = _acquire(universe)
    assert second["attempts"] == 0
    assert second["network_call_count"] == 0


def test_record_attempt_refuses_a_non_plan_identity(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    state = _open_state(universe["paths"])
    try:
        with pytest.raises(gate2.UnsafeStateError, match="not joined to a plan row"):
            state.record_attempt(
                gate2.PROVIDER_BINANCE,
                "identity-not-in-plan",
                gate2.RETRY_OK,
                status_code=200,
                fact={"x": 1},
            )
    finally:
        state.close()


def _refuse_after_sql(universe: dict[str, Any], sql: str, *args: Any) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(sql, args)
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError,
        match=(
            "rewritten or deleted|seal|prefix|gap fact|unsealed|code identity"
            "|watermark|disagree|not valid JSON|not a UTC timestamp|domain"
        ),
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_verify_refuses_an_independent_completion_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(
        universe,
        "UPDATE completion SET retrieved_at = '1999-01-01T00:00:00+00:00' "
        "WHERE provider = ?",
        gate2.PROVIDER_BINANCE,
    )


def test_verify_refuses_an_independent_sidecar_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(
        universe,
        "UPDATE sidecar_fact SET sidecar_path = sidecar_path || '/x'",
    )


def test_verify_refuses_an_independent_attempt_deletion(universe: dict[str, Any]) -> None:
    _refuse_after_sql(universe, "DELETE FROM attempt")


def test_verify_refuses_an_independent_charge_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(
        universe,
        "UPDATE coinalyze_charge SET created_at = '1999-01-01T00:00:00+00:00'",
    )


def test_resume_refuses_an_independent_completion_deletion(
    tmp_path: Path,
) -> None:
    built = build_universe(tmp_path, archive_families=("daily/klines",))
    _acquire(built)
    conn = _state_conn(built["paths"])
    conn.execute("DELETE FROM completion WHERE provider = ?", (gate2.PROVIDER_BINANCE,))
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="rewritten or deleted|deleted|watermark"
    ):
        _acquire(built)


def test_consume_manifest_is_an_iterator_not_a_universe_tuple(
    universe: dict[str, Any],
) -> None:
    report = json.loads(universe["paths"].report_path.read_text(encoding="utf-8"))
    descriptor = dict(report["acquisition_manifest"]["detail"])
    rows = gate2.consume_manifest(
        universe["paths"].store_root, descriptor, universe["pins"]
    )
    assert not isinstance(rows, tuple)
    first = next(rows)
    assert "key" in first
    rest = list(rows)
    assert len(rest) + 1 == universe["pins"].main_selected_objects


def test_zip_backslash_drive_duplicate_symlink_and_bomb(tmp_path: Path) -> None:
    def _write(name: str, mutate: Any) -> Path:
        path = tmp_path / name
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as handle:
            mutate(handle)
        path.write_bytes(buffer.getvalue())
        return path

    backslash = _write(
        "slash.zip", lambda handle: handle.writestr("dir\\file.csv", b"abc")
    )
    with pytest.raises(gate2.AcquisitionError, match="unsafe"):
        gate2.validate_zip(backslash)

    drive = _write("drive.zip", lambda handle: handle.writestr("C:escape.csv", b"abc"))
    with pytest.raises(gate2.AcquisitionError, match="unsafe"):
        gate2.validate_zip(drive)

    def _duplicate(handle: zipfile.ZipFile) -> None:
        handle.writestr("same.csv", b"abc")
        handle.writestr("same.csv", b"def")

    duplicate = _write("dup.zip", _duplicate)
    with pytest.raises(gate2.AcquisitionError, match="duplicated"):
        gate2.validate_zip(duplicate)

    def _symlink(handle: zipfile.ZipFile) -> None:
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        handle.writestr(info, b"x")

    linked = _write("link.zip", _symlink)
    with pytest.raises(gate2.AcquisitionError, match="symlink|not a file"):
        gate2.validate_zip(linked)

    def _bomb(handle: zipfile.ZipFile) -> None:
        for index in range(gate2.ZIP_MEMBER_CEILING + 1):
            handle.writestr(f"m{index}.csv", b"x")

    bomb = _write("bomb.zip", _bomb)
    with pytest.raises(gate2.AcquisitionError, match="member count"):
        gate2.validate_zip(bomb)

    modest = _write("modest.zip", lambda handle: handle.writestr("data.csv", b"abcdef"))
    original_ceiling = gate2.ZIP_UNCOMPRESSED_CEILING
    gate2.ZIP_UNCOMPRESSED_CEILING = 2
    try:
        with pytest.raises(gate2.AcquisitionError, match="uncompressed"):
            gate2.validate_zip(modest)
    finally:
        gate2.ZIP_UNCOMPRESSED_CEILING = original_ceiling


def test_coinalyze_exponent_and_duplicate_field_are_rejected() -> None:
    provider = "BTCUSDT_PERP.A"
    accepted = json.dumps(
        [{"symbol": provider, "history": [{"t": FROM_UNIX, "l": "1e+12", "s": "0"}]}]
    ).encode()
    parsed, summary = gate2.parse_liquidation_history(
        accepted, provider_symbol=provider, start=FROM_UNIX, end=TO_UNIX
    )
    assert summary.points == 1
    with pytest.raises(gate2.AcquisitionError, match="exponent"):
        gate2.parse_liquidation_history(
            json.dumps(
                [
                    {
                        "symbol": provider,
                        "history": [{"t": FROM_UNIX, "l": "1e+13", "s": "0"}],
                    }
                ]
            ).encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )
    with pytest.raises(gate2.AcquisitionError, match="exponent"):
        gate2.parse_liquidation_history(
            json.dumps(
                [
                    {
                        "symbol": provider,
                        "history": [{"t": FROM_UNIX, "l": "1e+99", "s": "0"}],
                    }
                ]
            ).encode(),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )
    with pytest.raises(gate2.AcquisitionError, match="repeats a field"):
        gate2.parse_liquidation_history(
            b'[{"symbol":"%s","symbol":"%s","history":[]}]'
            % (provider.encode(), provider.encode()),
            provider_symbol=provider,
            start=FROM_UNIX,
            end=TO_UNIX,
        )


def test_over_ceiling_ledger_is_unsafe_not_zero(universe: dict[str, Any]) -> None:
    _acquire(universe)
    ceiling = universe["pins"].new_coinalyze_raw_bytes
    conn = _state_conn(universe["paths"])
    extra = ceiling + 1
    first = conn.execute(
        "SELECT provider, identity FROM coinalyze_charge LIMIT 1"
    ).fetchone()
    assert first is not None
    conn.execute("UPDATE coinalyze_charge SET charged_bytes = 0")
    conn.execute(
        "UPDATE coinalyze_charge SET charged_bytes = ? WHERE provider=? AND identity=?",
        (extra, first[0], first[1]),
    )
    conn.execute("UPDATE coinalyze_ledger SET charged = ?", (extra,))
    conn.commit()
    conn.close()
    state = _open_state(universe["paths"])
    try:
        with pytest.raises(gate2.UnsafeStateError, match="over the accepted allocation"):
            state.coinalyze_remaining(ceiling)
    finally:
        state.close()


def test_release_charge_refuses_published_or_settled(universe: dict[str, Any]) -> None:
    _acquire(universe)
    state = _open_state(universe["paths"])
    try:
        row = state._db().execute(
            "SELECT provider, identity FROM coinalyze_charge LIMIT 1"
        ).fetchone()
        assert row is not None
        with pytest.raises(gate2.UnsafeStateError, match="unpublished"):
            state.release_charge(str(row[0]), str(row[1]))
    finally:
        state.close()


def test_http_transport_disables_redirects_and_does_not_forward_the_secret(
    universe: dict[str, Any],
) -> None:
    transport = gate2.HttpxStreamTransport()
    try:
        assert transport._client.follow_redirects is False
    finally:
        transport.close()
    liq = universe["transport"].liquidation_url("BTCUSDT")
    universe["transport"].add(liq, b"", status=302, headers={"Location": "https://evil.example/x"})
    _acquire(universe)
    origins = [urlparse(url).netloc for url, _headers in universe["transport"].calls]
    assert "evil.example" not in origins
    for url, headers in universe["transport"].calls:
        assert SECRET not in url
        if "evil.example" in url:
            assert "api_key" not in headers


def test_verify_publishes_separate_raw_and_sidecar_equations(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    facts = verified["reconciliation"]
    assert "unique_content_objects" not in facts
    assert (
        facts["unique_raw_content_objects"] + facts["unique_sidecar_objects"]
        == facts["unique_physical_objects"]
    )
    assert (
        facts["unique_raw_content_bytes"] + facts["unique_sidecar_bytes"]
        == facts["unique_physical_bytes"]
    )
    assert facts["coinalyze_settled_liquidations"] == universe["pins"].coinalyze_supported


def test_streamed_body_is_inside_retry_and_failed_private_is_discarded(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"].stream_get

    class _Broken(gate2.StreamResponse):
        def __init__(self, inner: gate2.StreamResponse) -> None:
            super().__init__(
                inner.status_code, inner.headers, self._boom(inner), inner.close_response
            )

        def _boom(self, inner: gate2.StreamResponse) -> Any:
            def _chunks() -> Any:
                yield from inner.iter_bytes
                raise OSError("stream reset after headers")

            return _chunks()

    calls = {"n": 0}

    def _wrap(
        target: str, *, headers: Mapping[str, str] | None, timeout: float
    ) -> gate2.StreamResponse:
        response = original(target, headers=headers, timeout=timeout)
        if target == url and calls["n"] == 0:
            calls["n"] += 1
            return _Broken(response)
        return response

    universe["transport"].stream_get = _wrap  # type: ignore[method-assign]
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert calls["n"] == 1
    conn = _state_conn(universe["paths"])
    try:
        failed = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ?",
                (gate2.RETRY_TRANSPORT,),
            ).fetchone()[0]
        )
        recovered = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ? AND redacted_fact_json LIKE ?",
                (gate2.RETRY_OK, f"%{key}.CHECKSUM%"),
            ).fetchone()[0]
        )
    finally:
        conn.close()
    assert failed >= 1
    assert recovered >= 1
    tmp = universe["paths"].tmp_root
    leftovers = (
        [item for item in tmp.iterdir() if item.name.startswith(".partial-")]
        if tmp.is_dir()
        else []
    )
    assert leftovers == []


def test_non_regular_lock_is_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    lock = universe["paths"].lockfile_path
    lock.unlink()
    lock.mkdir()
    state = gate2.AcquisitionState(universe["paths"].state_path, lock)
    with pytest.raises(gate2.UnsafeStateError, match="regular|no-follow"):
        try:
            state.open()
        finally:
            try:
                state.close()
            except Exception:
                pass


def test_session_root_survives_an_ancestor_rename(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    roots = gate2.BoundRoots.open(universe["paths"])
    try:
        original = universe["paths"].store_root
        moved = tmp_path / "moved-store"
        original.rename(moved)
        directory, name = roots.open_parent(original / "gate2" / "still-here", create=True)
        leaf = None
        try:
            leaf = os.open(
                name, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=directory
            )
        finally:
            if leaf is not None:
                os.close(leaf)
            os.close(directory)
        assert (moved / "gate2" / "still-here").exists()
    finally:
        roots.close()


def test_extra_sqlite_view_is_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    conn.execute("CREATE VIEW extra_view AS SELECT 1 AS x")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="outside the accepted schema"):
        _acquire(universe)


def test_verify_refuses_an_unsealed_attempt_tail(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    row = conn.execute("SELECT provider, identity FROM plan_entry LIMIT 1").fetchone()
    conn.execute(
        "INSERT INTO attempt(provider, identity, started_at, ended_at, class, "
        "status_code, redacted_fact_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            row[0],
            row[1],
            "2026-08-24T00:00:00+00:00",
            "2026-08-24T00:00:01+00:00",
            gate2.RETRY_OK,
            200,
            "{}\n",
        ),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="unsealed tail"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_verify_refuses_independent_authority_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(
        universe,
        "UPDATE authority SET created_at = '1999-01-01T00:00:00+00:00'",
    )


def test_verify_refuses_independent_gap_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(universe, "UPDATE terminal_gap SET fact_json = '{}'")


def test_verify_refuses_independent_transition_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(
        universe,
        "UPDATE charge_transition SET at = '1999-01-01T00:00:00+00:00'",
    )


def test_verify_refuses_independent_run_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(universe, "UPDATE run_metadata SET stop_reason = 'tamper'")


def test_verify_refuses_seal_head_mutation(universe: dict[str, Any]) -> None:
    _refuse_after_sql(universe, "UPDATE seal_head SET prefix_digest = ?", "a" * 64)


# --------------------------------------------------------------------------------------
# Review 295 residual regressions: state setup, the authenticated chain, append-only
# refunds, retained source authority, and bounded production behaviour.
# --------------------------------------------------------------------------------------


def _fd_count() -> int:
    return len(os.listdir("/proc/self/fd"))


def test_fresh_state_open_authenticates_schema_and_every_domain(tmp_path: Path) -> None:
    state = gate2.AcquisitionState(
        tmp_path / "gate2" / "state.sqlite", tmp_path / "gate2" / "acquisition.lock"
    )
    state.open()
    try:
        state.authenticate_schema()
        state.authenticate_domains()
        columns = {
            str(row[1])
            for row in state._db().execute("PRAGMA table_info(run_metadata)")
        }
        assert "receipt_sha256" not in columns
        for _message, sql in gate2.DOMAIN_CHECKS:
            assert state._db().execute(sql).fetchone() is None
    finally:
        state.close()
    reopened = gate2.AcquisitionState(
        tmp_path / "gate2" / "state.sqlite", tmp_path / "gate2" / "acquisition.lock"
    )
    reopened.open()
    reopened.close()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_pre_existing_journal_symlink_is_refused(tmp_path: Path, suffix: str) -> None:
    root = tmp_path / "gate2"
    root.mkdir(parents=True)
    state_path = root / "state.sqlite"
    first = gate2.AcquisitionState(state_path, root / "acquisition.lock")
    first.open()
    first.close()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_bytes(b"")
    journal = root / f"state.sqlite{suffix}"
    if journal.exists():
        journal.unlink()
    journal.symlink_to(elsewhere)
    state = gate2.AcquisitionState(state_path, root / "acquisition.lock")
    with pytest.raises(gate2.UnsafeStateError, match="no-follow"):
        state.open()


def test_journal_fallback_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_connect = gate2.sqlite3.connect

    class _Result:
        def fetchone(self) -> tuple[str]:
            return ("delete",)

    class _Proxy:
        def __init__(self, real: Any) -> None:
            self._real = real

        def execute(self, sql: str, *args: Any) -> Any:
            if sql == "PRAGMA journal_mode=WAL":
                return _Result()
            return self._real.execute(sql, *args)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._real, name)

    def _fake(*args: Any, **kwargs: Any) -> Any:
        return _Proxy(real_connect(*args, **kwargs))

    monkeypatch.setattr(gate2.sqlite3, "connect", _fake)
    state = gate2.AcquisitionState(
        tmp_path / "gate2" / "state.sqlite", tmp_path / "gate2" / "acquisition.lock"
    )
    with pytest.raises(gate2.UnsafeStateError, match="journal_mode is not wal"):
        state.open()


def test_state_setup_failure_releases_every_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_path = tmp_path / "gate2" / "state.sqlite"
    lock_path = tmp_path / "gate2" / "acquisition.lock"
    before = _fd_count()

    def _boom(_conn: Any) -> None:
        raise RuntimeError("synthetic setup failure")

    monkeypatch.setattr(gate2, "register_domain_functions", _boom)
    failing = gate2.AcquisitionState(state_path, lock_path)
    with pytest.raises(RuntimeError, match="synthetic setup failure"):
        failing.open()
    monkeypatch.undo()
    assert _fd_count() <= before + 1
    # the writer lock was released, so a fresh session can still bind
    recovered = gate2.AcquisitionState(state_path, lock_path)
    recovered.open()
    recovered.close()
    assert _fd_count() <= before + 1


def test_nested_close_failure_is_reported_once(tmp_path: Path) -> None:
    state = gate2.AcquisitionState(
        tmp_path / "gate2" / "state.sqlite", tmp_path / "gate2" / "acquisition.lock"
    )
    state.open()
    stolen = state._wal_fd
    assert stolen is not None
    os.close(stolen)
    with pytest.raises(gate2.UnsafeStateError, match="could not be released"):
        state.close()
    assert state.conn is None
    assert state._fd is None


def test_unbound_session_operations_are_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    state = _open_state(universe["paths"])
    try:
        plan = next(state.iter_plan_rows(kinds=(gate2.KIND_BINANCE,)))
        with pytest.raises(gate2.UnsafeStateError, match="bound session capability"):
            gate2.acquire_binance_object(
                plan,
                paths=universe["paths"],
                coordinator=gate2.Coordinator(state),
                transport=universe["transport"],
                filesystem=universe["filesystem"],
                device=universe["filesystem"].device,
                pins=universe["pins"],
                capacity=gate2.CapacityGuard(
                    pins=universe["pins"],
                    paths=universe["paths"],
                    filesystem=universe["filesystem"],
                ),
                fault=gate2.FaultInjector(),
                counters=gate2.RunCounters(),
                sleeper=lambda _delay: None,
                roots=None,
            )
    finally:
        state.close()
    assert universe["transport"].calls == []


def test_a_bound_session_survives_an_ancestor_swap(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    original = universe["paths"].store_root
    moved = tmp_path / "swapped-store"
    decoy = original

    class _SwapOnce(gate2.FaultInjector):
        def __init__(self) -> None:
            self.done = False

        def check(self, point: str, identity: str = "") -> None:
            if point == "before_raw_publication" and not self.done:
                self.done = True
                original.rename(moved)
                decoy.mkdir(parents=True, exist_ok=True)

    swap = _SwapOnce()
    result = _acquire(universe, fault=swap)
    assert swap.done is True
    assert result["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    # every descendant write followed the retained descriptors, not the pathname
    assert list((moved / "gate2" / "content").glob("*/*"))
    assert not list(decoy.glob("gate2/content/*/*"))


def test_the_chain_walks_back_to_the_installed_plan_receipt(
    universe: dict[str, Any],
) -> None:
    _acquire(universe, max_objects=1)
    _acquire(universe)
    state = _open_state(universe["paths"])
    try:
        head = state.seal_head_row()
        assert head is not None
        links = list(state.iter_seal_facts())
        assert len(links) >= 2
        authority = state.authority_row()
        assert links[0]["predecessor_sha256"] == authority["plan_receipt_sha256"]
        for earlier, later in zip(links, links[1:]):
            assert later["predecessor_sha256"] == earlier["receipt_sha256"]
        state.authenticate_prefix()
    finally:
        state.close()


def test_non_canonical_receipt_bytes_are_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    state = _open_state(universe["paths"])
    try:
        head = state.seal_head_row()
        assert head is not None
        path = Path(head["receipt_path"])
    finally:
        state.close()
    document = json.loads(path.read_text(encoding="utf-8"))
    path.write_bytes(json.dumps(document).encode("utf-8"))
    with pytest.raises(gate2.UnsafeStateError, match="does not match its identity"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_a_forked_receipt_predecessor_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE run_seal SET predecessor_sha256 = ?", ("f" * 64,))
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="seal|predecessor"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_an_over_claimed_watermark_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE seal_head SET attempt_hi = attempt_hi + 500")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="watermark|prefix"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_deleting_a_seal_link_breaks_the_sealed_prefix(universe: dict[str, Any]) -> None:
    _acquire(universe, max_objects=1)
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM run_seal WHERE seq = (SELECT MIN(seq) FROM run_seal)")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="prefix|seal"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_terminal_manifest_emits_every_seal_link(universe: dict[str, Any]) -> None:
    _acquire(universe)
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    import gzip as _gzip

    body = _gzip.decompress(Path(verified["terminal_manifest"]).read_bytes())
    records = [json.loads(line) for line in body.decode("utf-8").splitlines() if line]
    links = [row for row in records if row["record_type"] == "seal_link"]
    conn = _state_conn(universe["paths"])
    try:
        expected = int(conn.execute("SELECT COUNT(*) FROM run_seal").fetchone()[0])
    finally:
        conn.close()
    assert len(links) == expected >= 1
    assert all(len(row["receipt_sha256"]) == 64 for row in links)


def test_a_released_charge_is_retried_as_a_new_generation(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        identity = next(
            plan.identity
            for plan in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_LIQUIDATION,))
        )
    finally:
        state.close()
    _begin_unfinished_run(built)
    # Durable reservation owned by the unfinished run; bytes were never published.
    conn = _state_conn(built["paths"])
    conn.execute(
        "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            "d" * 64,
            4096,
            200,
            gate2.OUTCOME_CHECKSUM_VERIFIED,
            0,
            "e" * 64,
            "{}\n",
            "{}\n",
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute(
        "INSERT INTO charge_transition(provider, identity, generation, status, at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            1,
            gate2.CHARGE_RESERVED,
            "2026-08-24T00:00:00+00:00",
        ),
    )
    conn.execute("UPDATE coinalyze_ledger SET charged = charged + 4096")
    conn.commit()
    conn.close()
    resumed = _acquire(built)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(built["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["high_watermarks"]["charge_hi"] == 1
    assert interrupted["high_watermarks"]["transition_hi"] == 1
    conn = _state_conn(built["paths"])
    try:
        generations = conn.execute(
            "SELECT generation FROM coinalyze_charge WHERE identity = ? ORDER BY generation",
            (identity,),
        ).fetchall()
        assert [int(row[0]) for row in generations] == [1, 2]
        first = conn.execute(
            "SELECT status FROM charge_transition WHERE identity = ? AND generation = 1 "
            "ORDER BY seq",
            (identity,),
        ).fetchall()
        assert [str(row[0]) for row in first] == [
            gate2.CHARGE_RESERVED,
            gate2.CHARGE_RELEASED,
        ]
        second = conn.execute(
            "SELECT status FROM charge_transition WHERE identity = ? AND generation = 2 "
            "ORDER BY seq",
            (identity,),
        ).fetchall()
        assert [str(row[0]) for row in second] == [
            gate2.CHARGE_RESERVED,
            gate2.CHARGE_PUBLISHED,
            gate2.CHARGE_SETTLED,
        ]
        charged = int(
            conn.execute("SELECT charged FROM coinalyze_ledger").fetchone()[0]
        )
        active = int(
            conn.execute(
                "SELECT COALESCE(SUM(c.charged_bytes), 0) FROM coinalyze_charge c "
                "WHERE (SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
                "AND t.identity = c.identity AND t.generation = c.generation "
                "ORDER BY t.seq DESC LIMIT 1) != ?",
                (gate2.CHARGE_RELEASED,),
            ).fetchone()[0]
        )
        assert charged == active
        assert 4096 not in {int(row[0]) for row in conn.execute(
            "SELECT charged_bytes FROM coinalyze_charge WHERE identity = ? "
            "AND generation = 2", (identity,)
        )}
    finally:
        conn.close()
    verified = gate2.verify_state(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    assert verified["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_a_settled_charge_requires_its_exact_transition_history(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute(
        "DELETE FROM charge_transition WHERE status = ? AND seq = "
        "(SELECT MAX(seq) FROM charge_transition WHERE status = ?)",
        (gate2.CHARGE_PUBLISHED, gate2.CHARGE_PUBLISHED),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="transition|prefix|rewritten"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_terminal_charge_proof_requires_its_request_and_retrieval_facts(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE coinalyze_charge SET request_proof = ?", ("a" * 64,))
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="charge descriptor|prefix|rewritten"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_retained_raw_source_removal_is_refused(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    for item in built["paths"].sample_dir.iterdir():
        item.unlink()
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError), match="retained"):
        _acquire(built)


def test_retained_raw_source_copy_breaks_inode_lineage(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    source = next(built["paths"].sample_dir.iterdir())
    payload = source.read_bytes()
    source.unlink()
    source.write_bytes(payload)  # identical bytes, a different inode
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError)):
        _acquire(built)


def test_an_extra_retained_inventory_mapping_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    state = _open_state(universe["paths"])
    try:
        plan = next(
            row
            for row in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_INVENTORY,))
        )
        payload = dict(plan.payload)
        provenance = dict(
            json.loads(universe["paths"].report_path.read_text(encoding="utf-8"))[
                "coinalyze"
            ]
        )
        inventory_path = Path(str(provenance["provenance"][0]["content_path"]))
        markets = json.loads(inventory_path.read_bytes())
        markets.append(_market("EXTRAUSDT"))
        body = json.dumps(markets).encode("utf-8")
        with pytest.raises(gate2.UnsafeStateError, match="mapping"):
            gate2._reparse_inventory_mappings(
                body, gate2.PlanObject(plan.provider, plan.identity, plan.kind, payload)
            )
    finally:
        state.close()


def test_zip_unsupported_compression_and_close_failures_are_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as handle:
        handle.writestr("data.csv", b"1,2,3\n")
    raw = bytearray(buffer.getvalue())
    # force an unsupported compression method in both headers
    for index in range(len(raw) - 1):
        if raw[index : index + 4] == b"PK\x03\x04":
            raw[index + 8 : index + 10] = (99).to_bytes(2, "little")
        if raw[index : index + 4] == b"PK\x01\x02":
            raw[index + 10 : index + 12] = (99).to_bytes(2, "little")
    unsupported = tmp_path / "unsupported.zip"
    unsupported.write_bytes(bytes(raw))
    with pytest.raises(gate2.AcquisitionError):
        gate2.validate_zip(unsupported)

    good = tmp_path / "good.zip"
    good.write_bytes(_zip("data.csv", b"1,2,3\n"))
    real_close = zipfile.ZipFile.close
    raised: list[int] = []

    def _bad_close(self: Any) -> None:
        real_close(self)
        if not raised:
            raised.append(1)
            raise OSError("synthetic archive close failure")

    monkeypatch.setattr(zipfile.ZipFile, "close", _bad_close)
    with pytest.raises(gate2.AcquisitionError):
        gate2.validate_zip(good)
    assert raised == [1]


def test_large_production_run_holds_no_universe_sized_collection(tmp_path: Path) -> None:
    days = tuple(
        (datetime(2020, 1, 1) + timedelta(days=index)).strftime("%Y-%m-%d")
        for index in range(240)
    )
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        archive_intervals=days,
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
    )
    objects = built["pins"].combined_objects
    assert objects >= 240
    gate2.BOUND_TELEMETRY.reset()
    result = _acquire(built)
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    peaks = gate2.BOUND_TELEMETRY.snapshot()
    assert peaks["max_cursor_rows"] <= gate2.CURSOR_BATCH
    assert peaks["max_queue_depth"] <= gate2.QUEUE_CEILING
    assert peaks["max_work_depth"] <= gate2.QUEUE_CEILING
    assert peaks["max_sample_len"] <= gate2.NETWORK_SAMPLE_CEILING
    assert peaks["max_token_bytes"] <= gate2.MAX_JSON_TOKEN_BYTES
    assert len(result["network_calls"]) == gate2.NETWORK_SAMPLE_CEILING
    assert result["network_call_count"] > gate2.NETWORK_SAMPLE_CEILING


def test_terminal_receipt_binds_the_authenticated_chain(universe: dict[str, Any]) -> None:
    _acquire(universe)
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    receipt = json.loads(
        Path(verified["terminal_receipt"]["path"]).read_text(encoding="utf-8")
    )
    chain = receipt["chain"]
    state = _open_state(universe["paths"])
    try:
        head = state.seal_head_row()
        authority = state.authority_row()
        assert head is not None
        assert chain["head_receipt_sha256"] == head["receipt_sha256"]
        assert chain["head_prefix_digest"] == head["prefix_digest"]
        assert chain["plan_receipt_sha256"] == authority["plan_receipt_sha256"]
        assert chain["high_watermarks"] == {
            key: int(head[key]) for key in state._zero_watermarks()
        }
        assert chain["seal_links"] == int(
            state._db().execute("SELECT COUNT(*) FROM run_seal").fetchone()[0]
        )
    finally:
        state.close()


def test_a_seal_link_with_wrong_watermarks_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe, max_objects=1)
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    row = conn.execute(
        "SELECT seq, marks_json FROM run_seal ORDER BY seq LIMIT 1"
    ).fetchone()
    marks = json.loads(str(row[1]))
    marks["attempt_hi"] = int(marks["attempt_hi"]) + 1
    conn.execute(
        "UPDATE run_seal SET marks_json = ? WHERE seq = ?",
        (gate2.compact_json(marks).decode("utf-8"), int(row[0])),
    )
    conn.commit()
    conn.close()
    with pytest.raises(
        gate2.UnsafeStateError, match="seal|prefix|watermark|predecessor"
    ):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_bound_session_refuses_an_out_of_capability_path(universe: dict[str, Any]) -> None:
    roots = gate2.BoundRoots.open(universe["paths"])
    try:
        with pytest.raises(gate2.UnsafeStateError, match="outside the bound session"):
            gate2.open_dir_chain(Path("/tmp/not-a-session-root"), (), roots=roots)
        with pytest.raises(gate2.UnsafeStateError, match="outside the bound session"):
            gate2.open_parent_dir(
                Path("/tmp/not-a-session-root"),
                Path("/tmp/not-a-session-root/leaf"),
                roots=roots,
            )
    finally:
        roots.close()


def test_operator_override_authority_swap_is_bound(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    original = universe["paths"].store_root
    moved = tmp_path / "swapped-store"
    decoy = original

    class _SwapOnce(gate2.FaultInjector):
        def __init__(self) -> None:
            self.done = False

        def check(self, point: str, identity: str = "") -> None:
            if point == "before_manifest_open" and not self.done:
                self.done = True
                original.rename(moved)
                decoy.mkdir(parents=True, exist_ok=True)

    result = gate2.run_plan(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"], fault=_SwapOnce()
    )
    assert result["exit_code"] == gate2.EXIT_COMPLETE


def test_post_bind_cleanup_failure_releases_the_writer(
    universe: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise gate2.UnsafeStateError("synthetic cleanup failure")

    monkeypatch.setattr(gate2, "_cleanup_partials", _boom)
    with pytest.raises(gate2.UnsafeStateError, match="cleanup"):
        _acquire(universe)
    monkeypatch.undo()
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_verify_cleanup_failure_releases_the_writer(
    universe: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _acquire(universe)

    def _boom(*_args: Any, **_kwargs: Any) -> None:
        raise gate2.UnsafeStateError("synthetic cleanup failure")

    monkeypatch.setattr(gate2, "_cleanup_partials", _boom)
    with pytest.raises(gate2.UnsafeStateError, match="cleanup"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )
    monkeypatch.undo()
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert verified["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_run_receipt_carries_the_immutable_run_id(universe: dict[str, Any]) -> None:
    result = _acquire(universe)
    receipt = json.loads(Path(result["run_receipt"]["path"]).read_text(encoding="utf-8"))
    assert set(receipt) == gate2.RUN_RECEIPT_KEYS
    conn = _state_conn(universe["paths"])
    try:
        run_id = str(conn.execute("SELECT run_id FROM run_metadata").fetchone()[0])
    finally:
        conn.close()
    assert receipt["run_id"] == run_id
    assert len(run_id) == 64


def test_run_receipt_wrong_run_id_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE run_metadata SET run_id = ?", ("a" * 64,))
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="run|seal|prefix|foreign"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_run_receipt_extra_field_is_refused(universe: dict[str, Any]) -> None:
    result = _acquire(universe)
    path = Path(result["run_receipt"]["path"])
    document = json.loads(path.read_text(encoding="utf-8"))
    document["extra"] = "no"
    path.write_bytes(gate2.canonical_json(document))
    conn = _state_conn(universe["paths"])
    conn.execute(
        "UPDATE run_seal SET receipt_sha256 = ? WHERE receipt_sha256 = ?",
        (gate2.sha256_bytes(gate2.canonical_json(document)), result["run_receipt"]["sha256"]),
    )
    conn.execute(
        "UPDATE seal_head SET receipt_sha256 = ?",
        (gate2.sha256_bytes(gate2.canonical_json(document)),),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="extra or missing|identity"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def _reset_head_to_plan_without_seals(paths: gate2.AcquisitionPaths) -> str:
    state = _open_state(paths)
    try:
        empty = state._prefix_digest_unlocked(state._zero_watermarks())
        plan_sha = str(state.authority_row()["plan_receipt_sha256"])
    finally:
        state.close()
    conn = _state_conn(paths)
    conn.execute("DELETE FROM run_seal")
    conn.execute(
        "UPDATE seal_head SET receipt_sha256 = ?, receipt_path = ?, prefix_digest = ?, "
        "attempt_hi = 0, completion_hi = 0, sidecar_hi = 0, charge_hi = 0, "
        "transition_hi = 0, run_hi = 0, seal_hi = 0, predecessor_sha256 = NULL",
        (plan_sha, str(paths.plan_receipt_dir / f"{plan_sha}.json"), empty),
    )
    conn.commit()
    conn.close()
    return plan_sha


def test_published_receipt_without_seal_is_recovered(universe: dict[str, Any]) -> None:
    with pytest.raises(gate2.FaultInjected, match="before_run_seal_insert"):
        _acquire(universe, fault=gate2.NamedFault("before_run_seal_insert"))
    conn = _state_conn(universe["paths"])
    try:
        intent = conn.execute(
            "SELECT run_id, receipt_sha256 FROM run_publication"
        ).fetchone()
        assert intent is not None
        run_id = str(intent[0])
        receipt_sha = str(intent[1])
        seals = int(conn.execute("SELECT COUNT(*) FROM run_seal").fetchone()[0])
    finally:
        conn.close()
    assert seals == 0
    assert (universe["paths"].run_receipt_dir / f"{receipt_sha}.json").is_file()
    assert (universe["paths"].run_receipt_dir / f"{run_id}.link").is_file()
    resumed = _acquire(universe, max_objects=1)
    assert resumed["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        linked = conn.execute(
            "SELECT receipt_sha256 FROM run_seal WHERE receipt_sha256 = ?",
            (receipt_sha,),
        ).fetchone()
        head = conn.execute(
            "SELECT receipt_sha256, predecessor_sha256 FROM seal_head WHERE id = 1"
        ).fetchone()
        assert linked is not None
        assert str(head[0]) == resumed["run_receipt"]["sha256"]
        assert str(head[1]) == receipt_sha
    finally:
        conn.close()


def test_ambiguous_unpublished_finished_runs_fail_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    run_id = str(conn.execute("SELECT run_id FROM run_metadata").fetchone()[0])
    other = "ab" * 32
    conn.execute(
        "INSERT INTO run_metadata(run_id, started_at, ended_at, stop_reason, attempt_hi, "
        "network_calls, start_snapshot_json, error_count, network_sample_json, "
        "pre_capacity_json, post_capacity_json, capacity_blocked, attempt_delta, "
        "completion_delta, gap_delta, byte_delta, open_coinalyze_charges, counts_json) "
        "SELECT ?, started_at, ended_at, stop_reason, attempt_hi, network_calls, "
        "start_snapshot_json, error_count, network_sample_json, pre_capacity_json, "
        "post_capacity_json, capacity_blocked, attempt_delta, completion_delta, "
        "gap_delta, byte_delta, open_coinalyze_charges, counts_json FROM run_metadata "
        "WHERE run_id=?",
        (other, run_id),
    )
    conn.execute(
        "INSERT INTO run_publication(run_id, receipt_sha256, receipt_directory, receipt_body) "
        "SELECT ?, receipt_sha256, receipt_directory, receipt_body FROM run_publication "
        "WHERE run_id=?",
        (other, run_id),
    )
    conn.commit()
    conn.close()
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="ambiguous"):
        _acquire(universe, max_objects=1)


def test_missing_publication_intent_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM run_publication")
    conn.commit()
    conn.close()
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="intent"):
        _acquire(universe, max_objects=1)


def test_newest_generation_without_transition_is_refused(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    identity = str(
        conn.execute(
            "SELECT identity FROM coinalyze_charge ORDER BY seq DESC LIMIT 1"
        ).fetchone()[0]
    )
    conn.execute(
        "DELETE FROM charge_transition WHERE identity = ? AND generation = ("
        "SELECT MAX(generation) FROM coinalyze_charge WHERE identity = ?)",
        (identity, identity),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="transition|charge"):
        _acquire(universe)


def test_released_then_retried_generation_is_recovered_once(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    identity = str(
        conn.execute(
            "SELECT identity FROM coinalyze_charge ORDER BY seq LIMIT 1"
        ).fetchone()[0]
    )
    newest = int(
        conn.execute(
            "SELECT MAX(generation) FROM coinalyze_charge WHERE identity = ?",
            (identity,),
        ).fetchone()[0]
    )
    conn.execute(
        "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at) SELECT provider, identity, ?, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at FROM coinalyze_charge WHERE identity = ? AND generation = ?",
        (newest + 1, identity, newest),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError):
        _acquire(built)


def test_transport_raised_acquisition_error_is_retryable(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].raise_once[url] = gate2.AcquisitionError("synthetic transport")
    result = _acquire(universe)
    assert result["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        transport = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ? AND status_code IS NULL",
                (gate2.RETRY_TRANSPORT,),
            ).fetchone()[0]
        )
        terminal_null = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ? AND status_code IS NULL",
                (gate2.RETRY_TERMINAL,),
            ).fetchone()[0]
        )
        calls = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
    finally:
        conn.close()
    assert transport >= 1
    assert terminal_null == 0
    assert calls == result["network_call_count"]


def test_exhausted_transport_retry_records_one_attempt_per_call(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"]

    class _Always:
        def stream_get(
            self, target: str, *, headers: Mapping[str, str] | None, timeout: float
        ) -> gate2.StreamResponse:
            if target == url:
                raise ConnectionError("always down")
            return original.stream_get(target, headers=headers, timeout=timeout)

        def close(self) -> None:
            return None

    universe["transport"] = _Always()  # type: ignore[assignment]
    result = _acquire(universe)
    assert result["exit_code"] in {
        gate2.EXIT_RESUMABLE_PARTIAL,
        gate2.EXIT_UNSAFE_STATE,
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
    }
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code FROM attempt WHERE redacted_fact_json LIKE ?",
            (f"%{key}.CHECKSUM%",),
        ).fetchall()
    finally:
        conn.close()
    assert rows
    assert all(str(row[0]) == gate2.RETRY_TRANSPORT for row in rows)
    assert len(rows) <= gate2.MAX_TRANSIENT_ATTEMPTS


def test_retained_source_device_mutation_is_refused(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    conn.execute(
        "UPDATE completion SET revision_json = json_set(revision_json, '$.source_device', 0) "
        "WHERE identity = ?",
        (key,),
    )
    conn.commit()
    conn.close()
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError)):
        _acquire(built)


def test_changed_sidecar_source_bytes_are_refused(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    payload = conn.execute(
        "SELECT payload_json FROM plan_entry WHERE identity = ?", (key,)
    ).fetchone()
    document = json.loads(str(payload[0]))
    document["payload"]["retained_sidecar_bytes"] = 1
    conn.execute(
        "UPDATE plan_entry SET payload_json = ? WHERE identity = ?",
        (json.dumps(document), key),
    )
    conn.commit()
    conn.close()
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError)):
        _acquire(built)


def test_terminal_manifest_emits_authority_and_ledger(universe: dict[str, Any]) -> None:
    _acquire(universe)
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    prefix, semantic = gate2.reconstruct_digests_from_terminal_path(
        Path(verified["terminal_manifest"])
    )
    receipt = json.loads(
        Path(verified["terminal_receipt"]["path"]).read_text(encoding="utf-8")
    )
    assert prefix == receipt["chain"]["head_prefix_digest"]
    assert semantic == receipt["semantic_state_digest"]
    assert prefix != semantic


def test_exact_retrieval_url_is_required(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    row = conn.execute(
        "SELECT identity, retrieval_json FROM coinalyze_charge LIMIT 1"
    ).fetchone()
    retrieval = json.loads(str(row[1]))
    retrieval["url"] = str(retrieval["url"]) + "&extra=1"
    conn.execute(
        "UPDATE coinalyze_charge SET retrieval_json = ? WHERE identity = ?",
        (gate2.compact_json(retrieval).decode("utf-8"), str(row[0])),
    )
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="URL|charge|prefix"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_configured_receipt_root_override_is_used(universe: dict[str, Any], tmp_path: Path) -> None:
    custom = tmp_path / "custom-run-receipts"
    custom.mkdir()
    paths = replace(universe["paths"], run_receipt_dir=custom)
    universe = {**universe, "paths": paths}
    result = _acquire(universe)
    assert Path(result["run_receipt"]["path"]).parent == custom
    assert list(custom.glob("*.json"))
    assert list(custom.glob("*.link"))


@pytest.mark.parametrize(
    "point",
    (
        "before_run_receipt_publication",
        "after_run_receipt_publication",
        "before_run_locator_publication",
        "after_run_locator_publication",
        "before_run_seal_insert",
        "after_run_seal_insert",
        "before_seal_head_cas",
        "after_seal_head_cas",
    ),
)
def test_publication_crash_prefix_recovers(universe: dict[str, Any], point: str) -> None:
    with pytest.raises(gate2.FaultInjected, match=point):
        _acquire(universe, fault=gate2.NamedFault(point))
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_malformed_run_locator_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    run_id = str(conn.execute("SELECT run_id FROM run_metadata").fetchone()[0])
    conn.close()
    locator = universe["paths"].run_receipt_dir / f"{run_id}.link"
    locator.write_bytes(b"{not-json")
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="malformed|JSON"):
        _acquire(universe, max_objects=1)


def test_close_failure_on_allowed_response_is_statusless_transport(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"].stream_get

    class _CloseBoom(gate2.StreamResponse):
        def close_response(self) -> None:
            raise OSError("synthetic close failure")

    calls = {"n": 0}

    def _wrap(
        target: str, *, headers: Mapping[str, str] | None, timeout: float
    ) -> gate2.StreamResponse:
        response = original(target, headers=headers, timeout=timeout)
        if target == url and calls["n"] == 0:
            calls["n"] += 1
            return _CloseBoom(
                response.status_code, response.headers, response.iter_bytes, response.close_response
            )
        return response

    universe["transport"].stream_get = _wrap  # type: ignore[method-assign]
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code FROM attempt WHERE redacted_fact_json LIKE ?",
            ("%close%",),
        ).fetchall()
    finally:
        conn.close()
    assert rows
    assert all(str(row[0]) == gate2.RETRY_TRANSPORT and row[1] is None for row in rows)


def test_valid_released_then_retried_generation_is_handled_once(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        identity = next(
            plan.identity
            for plan in state.iter_plan_rows(kinds=(gate2.KIND_COINALYZE_LIQUIDATION,))
        )
        payload = state.plan_payload(gate2.PROVIDER_COINALYZE, identity)
        assert payload is not None
        digest = "ab" * 32
        proof = gate2.sha256_bytes(
            gate2.compact_json({"identity": identity, "query": payload["query"]})
        )
        url = f"{payload['url']}?{payload['query']}"
        retrieval = gate2.compact_json(
            {"url": url, "status": 200, "retrieved_at": "2026-08-24T00:00:00+00:00"}
        ).decode("utf-8")
        revision = gate2.compact_json({"status": 200, "points": 0}).decode("utf-8")
    finally:
        state.close()
    _begin_unfinished_run(built)
    conn = _state_conn(built["paths"])
    conn.execute(
        "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
        "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
        "revision_json, created_at) VALUES (?, ?, 1, ?, 0, 200, ?, 0, ?, ?, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            digest,
            gate2.OUTCOME_EMPTY_HISTORY,
            proof,
            retrieval,
            revision,
            "2026-08-24T00:00:01+00:00",
        ),
    )
    conn.execute(
        "INSERT INTO charge_transition(provider, identity, generation, status, at) "
        "VALUES (?, ?, 1, ?, ?), (?, ?, 1, ?, ?)",
        (
            gate2.PROVIDER_COINALYZE,
            identity,
            gate2.CHARGE_RESERVED,
            "2026-08-24T00:00:01+00:00",
            gate2.PROVIDER_COINALYZE,
            identity,
            gate2.CHARGE_RELEASED,
            "2026-08-24T00:00:02+00:00",
        ),
    )
    conn.commit()
    conn.close()
    resumed = _acquire(built)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(built["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["high_watermarks"]["charge_hi"] == 1
    assert interrupted["high_watermarks"]["transition_hi"] == 2
    conn = _state_conn(built["paths"])
    try:
        generations = [
            int(row[0])
            for row in conn.execute(
                "SELECT generation FROM coinalyze_charge WHERE identity = ? ORDER BY generation",
                (identity,),
            )
        ]
        assert generations[0] == 1
        assert 2 in generations
        open_rows = conn.execute(
            "SELECT c.generation FROM coinalyze_charge c WHERE c.identity = ? AND "
            "(SELECT t.status FROM charge_transition t WHERE t.provider = c.provider "
            "AND t.identity = c.identity AND t.generation = c.generation "
            "ORDER BY t.seq DESC LIMIT 1) IN (?, ?)",
            (identity, gate2.CHARGE_RESERVED, gate2.CHARGE_PUBLISHED),
        ).fetchall()
        assert open_rows == []
    finally:
        conn.close()


def test_retained_sidecar_source_replacement_is_refused(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    sidecar_dir = built["paths"].listing_cache_dir
    for item in sidecar_dir.iterdir():
        if item.is_file():
            item.write_bytes(b"tampered sidecar\n")
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError)):
        _acquire(built)


def test_retained_plan_label_missing_is_refused(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    _acquire(built)
    conn = _state_conn(built["paths"])
    payload = conn.execute(
        "SELECT payload_json FROM plan_entry WHERE identity = ?", (key,)
    ).fetchone()
    document = json.loads(str(payload[0]))
    document["payload"]["retained"] = False
    conn.execute(
        "UPDATE plan_entry SET payload_json = ? WHERE identity = ?",
        (json.dumps(document), key),
    )
    conn.commit()
    conn.close()
    with pytest.raises((gate2.AuthorityError, gate2.UnsafeStateError)):
        _acquire(built)


def test_retained_plan_binds_source_device_and_inode(tmp_path: Path) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), retain_keys={key}
    )
    gate2.run_plan(built["paths"], built["pins"], filesystem=built["filesystem"])
    state = _open_state(built["paths"])
    try:
        payload = state.plan_payload(gate2.PROVIDER_BINANCE, key)
        assert payload is not None
        assert payload["retained"] is True
        assert int(payload["retained_source_device"]) > 0
        assert int(payload["retained_source_inode"]) > 0
        assert int(payload["retained_sidecar_bytes"]) > 0
        assert payload["retained_sidecar_revision"] == payload["retained_sidecar_digest"]
    finally:
        state.close()


def _rewrite_head_run_receipt(
    universe: dict[str, Any], mutate: Callable[[dict[str, Any]], None]
) -> dict[str, Any]:
    conn = _state_conn(universe["paths"])
    try:
        head = conn.execute(
            "SELECT receipt_sha256, receipt_path FROM seal_head WHERE id=1"
        ).fetchone()
        assert head is not None
        path = Path(str(head[1]))
        document = json.loads(path.read_text(encoding="utf-8"))
        mutate(document)
        body = gate2.canonical_json(document)
        digest = gate2.sha256_bytes(body)
        new_path = path.parent / f"{digest}.json"
        new_path.write_bytes(body)
        run_id = str(document["run_id"])
        (path.parent / f"{run_id}.link").write_bytes(
            gate2.canonical_json({"run_id": run_id, "receipt_sha256": digest})
        )
        conn.execute(
            "UPDATE run_seal SET receipt_sha256=? WHERE receipt_sha256=?",
            (digest, str(head[0])),
        )
        conn.execute(
            "UPDATE seal_head SET receipt_sha256=?, receipt_path=?",
            (digest, str(new_path)),
        )
        conn.execute(
            "UPDATE run_publication SET receipt_sha256=?, receipt_body=? WHERE run_id=?",
            (digest, body.decode("utf-8"), run_id),
        )
        conn.commit()
        return document
    finally:
        conn.close()


def _refuse_mutated_receipt(
    universe: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    _acquire(universe)
    _rewrite_head_run_receipt(universe, mutate)
    with pytest.raises(gate2.UnsafeStateError, match=match):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_missing_filesystem_receipt_is_republished_from_intent(
    universe: dict[str, Any],
) -> None:
    with pytest.raises(gate2.FaultInjected, match="before_run_receipt_publication"):
        _acquire(universe, fault=gate2.NamedFault("before_run_receipt_publication"))
    conn = _state_conn(universe["paths"])
    try:
        intent = conn.execute(
            "SELECT run_id, receipt_sha256 FROM run_publication"
        ).fetchone()
        assert intent is not None
        run_id = str(intent[0])
        receipt_sha = str(intent[1])
        seals = int(conn.execute("SELECT COUNT(*) FROM run_seal").fetchone()[0])
    finally:
        conn.close()
    assert seals == 0
    assert not (universe["paths"].run_receipt_dir / f"{receipt_sha}.json").exists()
    assert not (universe["paths"].run_receipt_dir / f"{run_id}.link").exists()
    resumed = _acquire(universe, max_objects=1)
    assert resumed["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        linked = conn.execute(
            "SELECT receipt_sha256 FROM run_seal WHERE receipt_sha256 = ?",
            (receipt_sha,),
        ).fetchone()
        head = conn.execute(
            "SELECT receipt_sha256, predecessor_sha256 FROM seal_head WHERE id = 1"
        ).fetchone()
        assert linked is not None
        assert str(head[0]) == resumed["run_receipt"]["sha256"]
        assert str(head[1]) == receipt_sha
    finally:
        conn.close()
    assert (universe["paths"].run_receipt_dir / f"{receipt_sha}.json").is_file()
    assert (universe["paths"].run_receipt_dir / f"{run_id}.link").is_file()


def test_malformed_publication_body_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE run_publication SET receipt_body = ?", ("{not-json",))
    conn.commit()
    conn.close()
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="malformed|JSON"):
        _acquire(universe, max_objects=1)


def test_conflicting_publication_identity_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE run_publication SET receipt_sha256 = ?", ("ab" * 32,))
    conn.commit()
    conn.close()
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="conflict"):
        _acquire(universe, max_objects=1)


def test_conflicting_run_locator_fails_closed(universe: dict[str, Any]) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    run_id = str(conn.execute("SELECT run_id FROM run_metadata").fetchone()[0])
    conn.close()
    locator = universe["paths"].run_receipt_dir / f"{run_id}.link"
    locator.write_bytes(
        gate2.canonical_json({"run_id": run_id, "receipt_sha256": "ab" * 32})
    )
    _reset_head_to_plan_without_seals(universe["paths"])
    with pytest.raises(gate2.UnsafeStateError, match="disagrees|conflict"):
        _acquire(universe, max_objects=1)


def test_configured_receipt_root_crash_recovers(
    universe: dict[str, Any], tmp_path: Path
) -> None:
    custom = tmp_path / "custom-run-receipts"
    custom.mkdir()
    paths = replace(universe["paths"], run_receipt_dir=custom)
    universe = {**universe, "paths": paths}
    with pytest.raises(gate2.FaultInjected, match="after_run_receipt_publication"):
        _acquire(universe, fault=gate2.NamedFault("after_run_receipt_publication"))
    assert list(custom.glob("*.json"))
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    assert Path(resumed["run_receipt"]["path"]).parent == custom


@pytest.mark.parametrize(
    ("mutate", "match"),
    (
        (lambda doc: doc.__setitem__("ticket", "OTHER"), "ticket"),
        (lambda doc: doc.__setitem__("policy_identity", "other"), "policy"),
        (lambda doc: doc.__setitem__("plan_identity", "aa" * 32), "plan identity"),
        (lambda doc: doc.__setitem__("run_id", "bb" * 32), "run"),
        (lambda doc: doc.__setitem__("started_at", "1999-01-01T00:00:00+00:00"), "started_at"),
        (lambda doc: doc.__setitem__("ended_at", "1999-01-01T00:00:00+00:00"), "ended_at"),
        (lambda doc: doc.__setitem__("stop_reason", "other-stop"), "stop_reason"),
        (lambda doc: doc.__setitem__("attempt_delta", doc["attempt_delta"] + 1), "attempt_delta"),
        (
            lambda doc: doc.__setitem__("completion_delta", doc["completion_delta"] + 1),
            "completion_delta",
        ),
        (lambda doc: doc.__setitem__("gap_delta", doc["gap_delta"] + 1), "gap_delta"),
        (lambda doc: doc.__setitem__("byte_delta", doc["byte_delta"] + 1), "byte_delta"),
        (
            lambda doc: doc.__setitem__("network_calls", doc["network_calls"] + 1),
            "network_calls",
        ),
        (lambda doc: doc.__setitem__("attempts", doc["attempts"] + 1), "attempts"),
        (lambda doc: doc.__setitem__("error_count", doc["error_count"] + 1), "error_count"),
        (
            lambda doc: doc.__setitem__(
                "network_sample",
                list(reversed(list(doc["network_sample"])))
                if len(list(doc["network_sample"])) >= 2
                else list(doc["network_sample"]) + ["mutated-sample"],
            ),
            "network_sample",
        ),
        (
            lambda doc: doc["pre_capacity"].__setitem__(
                "available_bytes", int(doc["pre_capacity"]["available_bytes"]) + 1
            ),
            "pre_capacity",
        ),
        (
            lambda doc: doc["post_capacity"].__setitem__(
                "available_bytes", int(doc["post_capacity"]["available_bytes"]) + 1
            ),
            "post_capacity",
        ),
        (
            lambda doc: doc.__setitem__("capacity_blocked", not doc["capacity_blocked"]),
            "capacity_blocked",
        ),
        (
            lambda doc: doc.__setitem__(
                "open_coinalyze_charges", int(doc["open_coinalyze_charges"]) + 1
            ),
            "open-charge|open_coinalyze",
        ),
        (lambda doc: doc.__setitem__("semantic_state_digest", "00" * 32), "semantic"),
        (lambda doc: doc.__setitem__("prefix_digest", "11" * 32), "prefix"),
        (
            lambda doc: doc["high_watermarks"].__setitem__(
                "attempt_hi", int(doc["high_watermarks"]["attempt_hi"]) + 1
            ),
            "watermark",
        ),
        (lambda doc: doc.__setitem__("predecessor_sha256", "cc" * 32), "predecessor"),
        (
            lambda doc: doc["counts"].__setitem__("planned", int(doc["counts"]["planned"]) + 1),
            "counts",
        ),
        (
            lambda doc: doc["authority"].__setitem__("holdout_boundary_id", "dd" * 32),
            "authority",
        ),
        (
            lambda doc: doc.__setitem__(
                "code_identity",
                {key: "ee" * 32 for key in dict(doc["code_identity"])},
            ),
            "code identity",
        ),
    ),
)
def test_run_receipt_field_value_is_authenticated(
    universe: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    _refuse_mutated_receipt(universe, mutate, match)


@pytest.mark.parametrize(
    ("mutate", "match"),
    (
        (lambda doc: doc.__setitem__("attempt_delta", -1), "attempt_delta is below its bound"),
        (lambda doc: doc.__setitem__("attempt_delta", True), "attempt_delta is not an exact integer"),
        (lambda doc: doc.__setitem__("completion_delta", 1.0), "completion_delta is not an exact integer"),
        (lambda doc: doc.__setitem__("gap_delta", "1"), "gap_delta is not an exact integer"),
        (lambda doc: doc.__setitem__("byte_delta", False), "byte_delta is not an exact integer"),
        (lambda doc: doc.__setitem__("network_calls", True), "network_calls is not an exact integer"),
        (lambda doc: doc.__setitem__("attempts", "0"), "attempts is not an exact integer"),
        (lambda doc: doc.__setitem__("error_count", 1.5), "error_count is not an exact integer"),
        (lambda doc: doc.__setitem__("open_coinalyze_charges", True), "open_coinalyze_charges is not an exact integer"),
        (lambda doc: doc.__setitem__("capacity_blocked", 1), "capacity_blocked is not an exact boolean"),
        (lambda doc: doc.__setitem__("network_sample", "url"), "network_sample is not an exact list"),
        (lambda doc: doc.__setitem__("network_sample", [1]), "network_sample contains a non-string sample"),
        (
            lambda doc: doc.__setitem__(
                "network_sample", ["u"] * (gate2.NETWORK_SAMPLE_CEILING + 1)
            ),
            "network_sample exceeds its sample ceiling",
        ),
        (lambda doc: doc.__setitem__("pre_capacity", []), "pre_capacity is not an exact object"),
        (lambda doc: doc.__setitem__("counts", []), "counts is not an exact object"),
        (lambda doc: doc["counts"].__setitem__("extra", 1), "counts has extra or missing fields"),
        (
            lambda doc: doc["high_watermarks"].__setitem__("attempt_hi", "1"),
            "watermark is not a non-negative integer",
        ),
        (
            lambda doc: doc["high_watermarks"].__setitem__("extra", 0),
            "unknown watermark",
        ),
        (lambda doc: doc.__setitem__("started_at", 1), "started_at is not an exact string"),
        (lambda doc: doc.__setitem__("stop_reason", False), "stop_reason is not an exact string"),
        (lambda doc: doc.__setitem__("semantic_state_digest", True), "semantic_state_digest is not an exact string"),
        (lambda doc: doc.__setitem__("prefix_digest", 1), "prefix_digest is not an exact string"),
        (lambda doc: doc.__setitem__("predecessor_sha256", 1), "predecessor_sha256 is not an exact string"),
        (lambda doc: doc.__setitem__("authority", []), "authority is not an exact object"),
        (lambda doc: doc.__setitem__("code_identity", []), "code_identity is not an exact object"),
        (lambda doc: doc.__setitem__("run_id", True), "run_id is not an exact string"),
        (lambda doc: doc.__setitem__("ticket", 1), "ticket is not an exact string"),
        (lambda doc: doc.__setitem__("schema_version", 1), "unknown schema"),
    ),
)
def test_run_receipt_field_type_is_authenticated(
    universe: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    _refuse_mutated_receipt(universe, mutate, match)


def test_transport_header_failure_records_one_statusless_transport_attempt(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].raise_once[url] = ConnectionError("synthetic header")
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code, redacted_fact_json FROM attempt "
            "WHERE redacted_fact_json LIKE ?",
            (f"%{key}.CHECKSUM%",),
        ).fetchall()
        sealed = conn.execute("SELECT 1 FROM run_seal").fetchone()
    finally:
        conn.close()
    transport = [row for row in rows if str(row[0]) == gate2.RETRY_TRANSPORT]
    assert len(transport) == 1
    assert transport[0][1] is None
    assert "synthetic header" in str(transport[0][2])
    assert sealed is not None


def test_streamed_read_failure_records_one_transport_attempt_and_cleans_private(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"].stream_get
    calls = {"n": 0}

    def _wrap(
        target: str, *, headers: Mapping[str, str] | None, timeout: float
    ) -> gate2.StreamResponse:
        if target == url and calls["n"] == 0:
            calls["n"] += 1

            def _chunks() -> Iterator[bytes]:
                yield b"abc"
                raise OSError("synthetic stream read")

            def _close() -> None:
                with universe["transport"].lock:
                    universe["transport"].closed_responses += 1

            with universe["transport"].lock:
                universe["transport"].opened_responses += 1
            return gate2.StreamResponse(200, {}, _chunks(), _close)
        return original(target, headers=headers, timeout=timeout)

    universe["transport"].stream_get = _wrap  # type: ignore[method-assign]
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code, redacted_fact_json FROM attempt "
            "WHERE redacted_fact_json LIKE ?",
            ("%synthetic stream read%",),
        ).fetchall()
        sealed = conn.execute("SELECT 1 FROM run_seal").fetchone()
    finally:
        conn.close()
    assert len(rows) == 1
    assert str(rows[0][0]) == gate2.RETRY_TRANSPORT
    assert rows[0][1] is None
    assert sealed is not None
    leftover = [
        item
        for item in universe["paths"].tmp_root.iterdir()
        if item.name.startswith(".")
    ] if universe["paths"].tmp_root.is_dir() else []
    assert leftover == []


def test_provider_validator_failure_records_one_terminal_attempt_and_cleans_private(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].add(url, b"not-a-sidecar\n")
    result = _acquire(universe)
    assert result["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code, redacted_fact_json FROM attempt "
            "WHERE identity = ?",
            (key,),
        ).fetchall()
        sealed = conn.execute("SELECT 1 FROM run_seal").fetchone()
    finally:
        conn.close()
    terminal = [row for row in rows if str(row[0]) == gate2.RETRY_TERMINAL]
    assert len(terminal) == 1
    assert terminal[0][1] == 200
    assert "validation" in str(terminal[0][2])
    assert sealed is not None
    leftover = [
        item
        for item in universe["paths"].tmp_root.iterdir()
        if item.name.startswith(".")
    ] if universe["paths"].tmp_root.is_dir() else []
    assert leftover == []


def test_injected_interruption_records_one_interrupt_attempt(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"].stream_get
    calls = {"n": 0}

    def _wrap(
        target: str, *, headers: Mapping[str, str] | None, timeout: float
    ) -> gate2.StreamResponse:
        response = original(target, headers=headers, timeout=timeout)
        if target == url and calls["n"] == 0:
            calls["n"] += 1
            inner = response.iter_bytes

            def _chunks() -> Iterator[bytes]:
                yield from inner
                raise gate2.FaultInjected("synthetic interrupt")

            return gate2.StreamResponse(
                response.status_code,
                response.headers,
                _chunks(),
                response.close_response,
            )
        return response

    universe["transport"].stream_get = _wrap  # type: ignore[method-assign]
    result = _acquire(universe)
    assert result["exit_code"] in {
        gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS,
        gate2.EXIT_RESUMABLE_PARTIAL,
    }
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code, redacted_fact_json FROM attempt "
            "WHERE redacted_fact_json LIKE ?",
            ("%interrupt%",),
        ).fetchall()
        sealed = conn.execute("SELECT 1 FROM run_seal").fetchone()
        domains = conn.execute(
            "SELECT 1 FROM run_metadata WHERE ended_at IS NOT NULL"
        ).fetchone()
    finally:
        conn.close()
    assert len(rows) == 1
    assert str(rows[0][0]) == gate2.RETRY_TRANSPORT
    assert rows[0][1] is None
    assert sealed is not None
    assert domains is not None


def test_close_failure_is_sealed_after_domain_authentication(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"].stream_get

    class _CloseBoom(gate2.StreamResponse):
        def close_response(self) -> None:
            raise OSError("synthetic close failure")

    calls = {"n": 0}

    def _wrap(
        target: str, *, headers: Mapping[str, str] | None, timeout: float
    ) -> gate2.StreamResponse:
        response = original(target, headers=headers, timeout=timeout)
        if target == url and calls["n"] == 0:
            calls["n"] += 1
            return _CloseBoom(
                response.status_code,
                response.headers,
                response.iter_bytes,
                response.close_response,
            )
        return response

    universe["transport"].stream_get = _wrap  # type: ignore[method-assign]
    result = _acquire(universe)
    assert result["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    conn = _state_conn(universe["paths"])
    try:
        rows = conn.execute(
            "SELECT class, status_code FROM attempt WHERE redacted_fact_json LIKE ?",
            ("%close%",),
        ).fetchall()
        sealed = conn.execute("SELECT 1 FROM run_seal").fetchone()
    finally:
        conn.close()
    assert len(rows) == 1
    assert str(rows[0][0]) == gate2.RETRY_TRANSPORT
    assert rows[0][1] is None
    assert sealed is not None


def _ordered_run_receipts(paths: gate2.AcquisitionPaths) -> list[dict[str, Any]]:
    conn = _state_conn(paths)
    try:
        rows = conn.execute(
            "SELECT p.receipt_body FROM run_metadata r "
            "JOIN run_publication p ON p.run_id = r.run_id "
            "WHERE r.ended_at IS NOT NULL ORDER BY r.seq"
        ).fetchall()
    finally:
        conn.close()
    return [json.loads(str(row[0])) for row in rows]


def test_process_loss_after_run_begin_finalizes_that_run(
    universe: dict[str, Any],
) -> None:
    # Synthetic zero-fact recovery only. Corrected code is never used to finalize
    # the retired real Gate-2 store under review 324 / ADR-0030.
    with pytest.raises(gate2.FaultInjected, match="after_run_begin"):
        _acquire(universe, fault=gate2.NamedFault("after_run_begin"))
    conn = _state_conn(universe["paths"])
    try:
        open_runs = conn.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL"
        ).fetchall()
        attempts_before = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
    finally:
        conn.close()
    assert len(open_runs) == 1
    assert attempts_before == 0
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    receipts = _ordered_run_receipts(universe["paths"])
    assert len(receipts) >= 2
    assert receipts[0]["stop_reason"] == "interrupted"
    assert receipts[0]["attempt_delta"] == 0
    assert receipts[0]["network_calls"] == 0
    owned = sum(int(item["attempt_delta"]) for item in receipts)
    conn = _state_conn(universe["paths"])
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
        open_after = conn.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL"
        ).fetchall()
    finally:
        conn.close()
    assert owned == total
    assert open_after == []
    verified = gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )
    assert verified["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS


def test_process_loss_after_progress_owns_the_unsealed_tail(
    universe: dict[str, Any],
) -> None:
    with pytest.raises(gate2.FaultInjected, match="before_run_finalization"):
        _acquire(universe, fault=gate2.NamedFault("before_run_finalization"))
    conn = _state_conn(universe["paths"])
    try:
        open_runs = conn.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL"
        ).fetchall()
        attempts_before = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
        completions_before = int(
            conn.execute("SELECT COUNT(*) FROM completion").fetchone()[0]
        )
    finally:
        conn.close()
    assert len(open_runs) == 1
    assert attempts_before > 0
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    receipts = _ordered_run_receipts(universe["paths"])
    assert receipts[0]["stop_reason"] == "interrupted"
    assert receipts[0]["attempt_delta"] == attempts_before
    assert receipts[0]["network_calls"] == attempts_before
    assert receipts[0]["completion_delta"] == completions_before
    owned = sum(int(item["attempt_delta"]) for item in receipts)
    conn = _state_conn(universe["paths"])
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
        open_after = conn.execute(
            "SELECT run_id FROM run_metadata WHERE ended_at IS NULL"
        ).fetchall()
    finally:
        conn.close()
    assert owned == total
    assert open_after == []
    gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )


def test_completed_head_publication_mutation_is_refused(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("UPDATE run_publication SET receipt_body = ?", ("{not-json",))
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="intent|malformed|JSON|disagree"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_completed_head_publication_deletion_is_refused(
    universe: dict[str, Any],
) -> None:
    _acquire(universe)
    conn = _state_conn(universe["paths"])
    conn.execute("DELETE FROM run_publication")
    conn.commit()
    conn.close()
    with pytest.raises(gate2.UnsafeStateError, match="intent"):
        gate2.verify_state(
            universe["paths"], universe["pins"], filesystem=universe["filesystem"]
        )


def test_capacity_stable_components_extra_key_is_refused(
    universe: dict[str, Any],
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["pre_capacity"]["stable_components"]["extra"] = 1

    _refuse_mutated_receipt(universe, mutate, "stable_components")


def test_capacity_stable_components_missing_key_is_refused(
    universe: dict[str, Any],
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["pre_capacity"]["stable_components"] = {}

    _refuse_mutated_receipt(universe, mutate, "stable_components")


def test_capacity_stable_components_value_is_authenticated(
    universe: dict[str, Any],
) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["pre_capacity"]["stable_components"]["stable_requirement_bytes"] = 0

    _refuse_mutated_receipt(universe, mutate, "accepted mapping")


def test_production_stable_component_offset_is_refused(universe: dict[str, Any]) -> None:
    gate2.run_plan(universe["paths"], universe["pins"], filesystem=universe["filesystem"])
    conn = _state_conn(universe["paths"])
    pins = json.loads(str(conn.execute("SELECT pins_json FROM authority").fetchone()[0]))
    pins["stable_requirement_bytes"] = gate2.EXPECTED_STABLE_REQUIREMENT_BYTES
    conn.execute(
        "UPDATE authority SET pins_json = ?",
        (gate2.canonical_json(pins).decode("utf-8"),),
    )
    conn.commit()
    conn.close()
    components = dict(gate2.STABLE_COMPONENTS)
    names = sorted(components)
    components[names[0]] += 1
    components[names[1]] -= 1
    assert sum(components.values()) == gate2.EXPECTED_STABLE_REQUIREMENT_BYTES
    available = AVAILABLE
    reserve = gate2.operating_reserve_bytes(available)
    total = gate2.EXPECTED_STABLE_REQUIREMENT_BYTES + reserve
    fact = {
        "stable_requirement_bytes": gate2.EXPECTED_STABLE_REQUIREMENT_BYTES,
        "operating_reserve_bytes": reserve,
        "total_future_storage_bytes": total,
        "available_bytes": available,
        "next_transfer_bytes": 0,
        "needed_bytes": total,
        "storage_preflight_state": "sufficient" if total <= available else "blocked",
        "reserve_floor_bytes": gate2.MINIMUM_OPERATING_RESERVE_BYTES,
        "stable_components": components,
    }
    state = _open_state(universe["paths"])
    try:
        with pytest.raises(gate2.UnsafeStateError, match="accepted mapping"):
            state._parse_capacity_fact(fact, label="pre_capacity")
    finally:
        state.close()


def test_capacity_total_equation_is_authenticated(universe: dict[str, Any]) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["pre_capacity"]["total_future_storage_bytes"] = 0

    _refuse_mutated_receipt(universe, mutate, "total-future equation")


def test_capacity_blocked_equation_is_authenticated(universe: dict[str, Any]) -> None:
    def mutate(document: dict[str, Any]) -> None:
        document["post_capacity"]["storage_preflight_state"] = "blocked"

    _refuse_mutated_receipt(universe, mutate, "storage_preflight_state|equation")


def test_many_run_recovery_stays_within_constant_bound(tmp_path: Path) -> None:
    built = build_universe(
        tmp_path, archive_families=("daily/klines",), supported=("BTCUSDT",)
    )
    gate2.BOUND_TELEMETRY.reset()
    _acquire(built)
    for _ in range(8):
        _acquire(built)
    assert gate2.BOUND_TELEMETRY.max_recover_rows <= 2
    assert gate2.BOUND_TELEMETRY.max_cursor_rows <= gate2.CURSOR_BATCH
    verified = gate2.verify_state(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    assert verified["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    receipts = _ordered_run_receipts(built["paths"])
    assert len(receipts) >= 2
    conn = _state_conn(built["paths"])
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
    finally:
        conn.close()
    assert sum(int(item["attempt_delta"]) for item in receipts) == total


def test_process_loss_after_transient_retry_has_zero_worker_errors(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    universe["transport"].raise_once[url] = ConnectionError("synthetic once")
    with pytest.raises(gate2.FaultInjected, match="before_run_finalization"):
        _acquire(universe, fault=gate2.NamedFault("before_run_finalization"))
    conn = _state_conn(universe["paths"])
    try:
        errors = int(
            conn.execute(
                "SELECT error_count FROM run_metadata WHERE ended_at IS NULL"
            ).fetchone()[0]
        )
        transport = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ?",
                (gate2.RETRY_TRANSPORT,),
            ).fetchone()[0]
        )
    finally:
        conn.close()
    assert errors == 0
    assert transport >= 1
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(universe["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["error_count"] == 0
    assert interrupted["network_calls"] == interrupted["attempt_delta"]
    gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )


def test_process_loss_after_exhausted_request_has_one_worker_error(
    universe: dict[str, Any],
) -> None:
    key = universe["selected_rows"][0]["key"]
    url = f"{gate2.VISION_OBJECT_BASE}/{key}.CHECKSUM"
    original = universe["transport"]

    class _Always:
        def stream_get(
            self, target: str, *, headers: Mapping[str, str] | None, timeout: float
        ) -> gate2.StreamResponse:
            if target == url:
                raise ConnectionError("always down")
            return original.stream_get(target, headers=headers, timeout=timeout)

        def close(self) -> None:
            return None

    universe["transport"] = _Always()  # type: ignore[assignment]
    with pytest.raises(gate2.FaultInjected, match="before_run_finalization"):
        _acquire(universe, fault=gate2.NamedFault("before_run_finalization"))
    conn = _state_conn(universe["paths"])
    try:
        errors = int(
            conn.execute(
                "SELECT error_count FROM run_metadata WHERE ended_at IS NULL"
            ).fetchone()[0]
        )
        transport = int(
            conn.execute(
                "SELECT COUNT(*) FROM attempt WHERE class = ? AND redacted_fact_json LIKE ?",
                (gate2.RETRY_TRANSPORT, f"%{key}.CHECKSUM%"),
            ).fetchone()[0]
        )
    finally:
        conn.close()
    assert errors == 1
    assert transport == gate2.MAX_TRANSIENT_ATTEMPTS
    universe["transport"] = original
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(universe["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["error_count"] == 1
    assert interrupted["attempt_delta"] >= gate2.MAX_TRANSIENT_ATTEMPTS
    assert interrupted["network_calls"] == interrupted["attempt_delta"]
    gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )


def test_process_loss_after_capacity_stop_keeps_blocked(
    universe: dict[str, Any],
) -> None:
    tight = FakeFilesystem(
        device=universe["filesystem"].device,
        available=AVAILABLE,
        sequence=[AVAILABLE] + [100] * 64,
    )
    with pytest.raises(gate2.FaultInjected, match="before_run_finalization"):
        _acquire(
            universe,
            filesystem=tight,
            fault=gate2.NamedFault("before_run_finalization"),
        )
    conn = _state_conn(universe["paths"])
    try:
        row = conn.execute(
            "SELECT error_count, capacity_blocked FROM run_metadata WHERE ended_at IS NULL"
        ).fetchone()
    finally:
        conn.close()
    assert int(row[0]) >= 1
    assert int(row[1]) == 1
    resumed = _acquire(universe)
    assert resumed["exit_code"] == gate2.EXIT_COMPLETE_WITH_TERMINAL_GAPS
    interrupted = _ordered_run_receipts(universe["paths"])[0]
    assert interrupted["stop_reason"] == "interrupted"
    assert interrupted["error_count"] >= 1
    assert interrupted["capacity_blocked"] is True
    gate2.verify_state(
        universe["paths"], universe["pins"], filesystem=universe["filesystem"]
    )


def _tiny_retained_universe(
    tmp_path: Path,
    *,
    intervals: tuple[str, ...] = ("2020-01-01", "2020-01-02"),
    credit_keys: set[str] | None = None,
) -> dict[str, Any]:
    return build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        archive_intervals=intervals,
        retain_all=True,
        credit_keys=credit_keys,
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
    )


def _run_plan(built: dict[str, Any]) -> dict[str, Any]:
    return gate2.run_plan(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )


def test_ninety_complete_progress_objects_credit_only_receipt_authorized_keys(
    tmp_path: Path,
) -> None:
    days = tuple(
        (datetime(2020, 1, 1) + timedelta(days=index)).strftime("%Y-%m-%d")
        for index in range(85)
    )
    credit_keys = {_key("daily/klines", "BTCUSDT", day) for day in days[:68]} | {
        _key("daily/bookTicker", "BTCUSDT", "2020-01-01"),
        _key("daily/bookTicker", "BTCUSDT", "2020-01-02"),
        _key("daily/bookTicker", "BTCUSDT", "2020-01-03"),
        _key("daily/bookDepth", "BTCUSDT", "2020-01-01"),
        _key("daily/bookDepth", "BTCUSDT", "2020-01-02"),
    }
    assert len(credit_keys) == 73
    built = build_universe(
        tmp_path,
        archive_families=("daily/klines",),
        archive_intervals=days,
        supported=("BTCUSDT",),
        unsupported=(),
        extra_inventory=(),
        retain_all=True,
        credit_keys=credit_keys,
    )
    assert len(built["retain_set"]) == 90
    assert built["credit_set"] == credit_keys
    assert built["pins"].retained_credit_objects == 73
    result = _acquire(built)
    assert result["exit_code"] == gate2.EXIT_COMPLETE
    state = _open_state(built["paths"])
    try:
        binance = [
            item
            for item in state.iter_completions()
            if item["provider"] == gate2.PROVIDER_BINANCE
        ]
        retained = [
            item
            for item in binance
            if item["validation_state"] == gate2.OUTCOME_RETAINED
        ]
        verified = [
            item
            for item in binance
            if item["validation_state"] == gate2.OUTCOME_CHECKSUM_VERIFIED
        ]
        labeled: set[str] = set()
        unretained: set[str] = set()
        for item in binance:
            payload = state.plan_payload(gate2.PROVIDER_BINANCE, item["identity"])
            assert payload is not None
            if payload.get("retained") is True:
                labeled.add(item["identity"])
            else:
                unretained.add(item["identity"])
    finally:
        state.close()
    assert len(binance) == 90
    assert {item["identity"] for item in retained} == credit_keys
    assert len(verified) == 17
    assert labeled == credit_keys
    assert len(unretained) == 17
    assert credit_keys.isdisjoint({item["identity"] for item in verified})
    vision = [
        url
        for url, _headers in built["transport"].calls
        if "data.binance.vision" in url
    ]
    assert len(vision) == 34
    plan = _plan_receipt(built)
    credit = plan["retained_credit"]
    assert credit["valid_requirement_keys"] == 73
    assert credit["objects"] == 73
    assert credit["selected_retained_keys"] == 68
    assert credit["cost_retained_keys"] == 5
    assert credit["unverified_objects"] == 0
    assert credit["key_set_sha256"] == built["retained_credit_key_set_sha256"]
    assert "keys" not in credit


def test_unsorted_retained_keys_are_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    built = _tiny_retained_universe(tmp_path)
    keys = sorted(built["credit_set"])
    document = _sizing_receipt_document(
        list(reversed(keys)),
        objects=len(keys),
        unique_bytes=built["pins"].retained_credit_bytes,
        selected_keys=sum(1 for key in keys if not _costish(key)),
        cost_keys=sum(1 for key in keys if _costish(key)),
    )
    _write_sizing_receipt(built, document)
    with pytest.raises(
        gate2.AuthorityError,
        match="retained credit keys are not strictly unique and ordered",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_duplicate_retained_keys_are_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = _sizing_receipt_document(
        [key, key],
        objects=1,
        unique_bytes=built["pins"].retained_credit_bytes,
        selected_keys=1,
        cost_keys=0,
        valid_requirement_keys=2,
    )
    _write_sizing_receipt(built, document)
    built["pins"] = replace(built["pins"], retained_credit_objects=2)
    with pytest.raises(
        gate2.AuthorityError,
        match="retained credit keys are not strictly unique and ordered",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_missing_retained_progress_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    _rewrite_progress(built, lambda document: document["objects"].pop(key))
    with pytest.raises(
        gate2.AuthorityError,
        match="not complete in qualification progress",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_extra_retained_keys_are_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key1 = _key("daily/klines", "BTCUSDT", "2020-01-01")
    key2 = _key("daily/klines", "BTCUSDT", "2020-01-02")
    built = _tiny_retained_universe(tmp_path, credit_keys={key1})
    document = _sizing_receipt_document(
        sorted([key1, key2]),
        objects=1,
        unique_bytes=built["pins"].retained_credit_bytes,
        selected_keys=1,
        cost_keys=0,
        valid_requirement_keys=1,
    )
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="retained credit key count"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_outside_plan_retained_key_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    outside = _key("daily/klines", "FAKEUSDT", "1999-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = _sizing_receipt_document(
        sorted([key, outside]),
        objects=2,
        unique_bytes=built["pins"].retained_credit_bytes,
        selected_keys=2,
        cost_keys=0,
    )
    _write_sizing_receipt(built, document)
    built["pins"] = replace(built["pins"], retained_credit_objects=2)
    with pytest.raises(
        gate2.AuthorityError,
        match="not in the selected-plus-cost plan",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_incomplete_retained_progress_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})

    def _mark_incomplete(document: dict[str, Any]) -> None:
        document["objects"][key]["status"] = "partial"

    _rewrite_progress(built, _mark_incomplete)
    with pytest.raises(
        gate2.AuthorityError,
        match="not complete in qualification progress",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_unproved_retained_bytes_are_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    progress = json.loads(built["paths"].progress_path.read_text(encoding="utf-8"))
    digest = str(progress["objects"][key]["sha256"])
    (built["paths"].sample_dir / digest).write_bytes(b"tampered-retained-bytes")
    with pytest.raises(gate2.AuthorityError, match="retained"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_wrong_retained_digest_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(
        built["paths"].receipt_258_path.read_text(encoding="utf-8")
    )
    document["physical_inputs"]["retained_credit"]["key_set_sha256"] = "a" * 64
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="key-set digest changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_wrong_retained_lineage_digest_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(
        built["paths"].receipt_258_path.read_text(encoding="utf-8")
    )
    document["lineage"]["retained_archive_key_set_sha256"] = "b" * 64
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="lineage key-set digest changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_wrong_retained_object_count_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(
        built["paths"].receipt_258_path.read_text(encoding="utf-8")
    )
    document["physical_inputs"]["retained_credit_objects"] = 99
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="retained credit object count"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_wrong_retained_byte_count_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(
        built["paths"].receipt_258_path.read_text(encoding="utf-8")
    )
    document["physical_inputs"]["retained_credit"]["bytes"] = 1
    document["physical_inputs"]["retained_credit_bytes"] = 1
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="retained credit bytes changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_wrong_selected_cost_decomposition_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    built = _tiny_retained_universe(tmp_path)
    keys = sorted(built["credit_set"])
    document = _sizing_receipt_document(
        keys,
        objects=len(keys),
        unique_bytes=built["pins"].retained_credit_bytes,
        selected_keys=0,
        cost_keys=len(keys),
    )
    _write_sizing_receipt(built, document)
    with pytest.raises(
        gate2.AuthorityError,
        match="retained credit selected key count|retained credit cost key count",
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_changing_authorized_key_set_cannot_attach_to_installed_plan(
    tmp_path: Path,
) -> None:
    key1 = _key("daily/klines", "BTCUSDT", "2020-01-01")
    key2 = _key("daily/klines", "BTCUSDT", "2020-01-02")
    built = _tiny_retained_universe(tmp_path, credit_keys={key1})
    first_pins = built["pins"]
    first_receipt = built["paths"].receipt_258_path.read_bytes()
    first_summary = gate2.build_plan(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    progress = json.loads(built["paths"].progress_path.read_text(encoding="utf-8"))
    entry = progress["objects"][key2]
    second_document = _sizing_receipt_document(
        [key2],
        objects=1,
        unique_bytes=int(entry["byte_size"]),
        selected_keys=1,
        cost_keys=0,
    )
    _write_sizing_receipt(built, second_document)
    built["pins"] = replace(
        built["pins"],
        retained_credit_objects=1,
        retained_credit_bytes=int(entry["byte_size"]),
    )
    second_summary = gate2.build_plan(
        built["paths"], built["pins"], filesystem=built["filesystem"]
    )
    assert first_summary.identity != second_summary.identity
    assert (
        first_summary.retained_credit.key_set_sha256
        != second_summary.retained_credit.key_set_sha256
    )
    built["paths"].receipt_258_path.write_bytes(first_receipt)
    built["pins"] = first_pins
    installed = _run_plan(built)
    assert installed["plan_identity"] == first_summary.identity
    _write_sizing_receipt(built, second_document)
    built["pins"] = replace(
        built["pins"],
        retained_credit_objects=1,
        retained_credit_bytes=int(entry["byte_size"]),
    )
    with pytest.raises(gate2.UnsafeStateError, match="different plan"):
        _run_plan(built)
    conn = _state_conn(built["paths"])
    try:
        identity = conn.execute(
            "SELECT plan_identity FROM authority WHERE id=1"
        ).fetchone()
    finally:
        conn.close()
    assert identity is not None
    assert str(identity[0]) == first_summary.identity


def _rewrite_installed_plan_receipt(
    built: dict[str, Any], mutate: Callable[[dict[str, Any]], None]
) -> None:
    conn = _state_conn(built["paths"])
    try:
        row = conn.execute(
            "SELECT plan_receipt_sha256 FROM authority WHERE id=1"
        ).fetchone()
        assert row is not None
        old_sha = str(row[0])
        path = built["paths"].plan_receipt_dir / f"{old_sha}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        mutate(document)
        body = gate2.canonical_json(document)
        digest = gate2.sha256_bytes(body)
        new_path = built["paths"].plan_receipt_dir / f"{digest}.json"
        new_path.write_bytes(body)
        conn.execute(
            "UPDATE authority SET plan_receipt_sha256=? WHERE id=1", (digest,)
        )
        conn.execute(
            "UPDATE seal_head SET receipt_sha256=?, receipt_path=? WHERE id=1",
            (digest, str(new_path)),
        )
        conn.commit()
    finally:
        conn.close()


def test_extra_retained_credit_field_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["physical_inputs"]["retained_credit"]["extra"] = True
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="extra or missing fields"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_missing_retained_credit_field_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    del document["physical_inputs"]["retained_credit"]["source"]
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="extra or missing fields"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_altered_report_summary_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["physical_inputs"]["retained_credit"]["report_summary"][
        "retained_verified_credit_objects"
    ] = 99
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="report summary object count"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_altered_rejected_row_fact_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["physical_inputs"]["retained_credit"]["rejected_recovered_rows"] = 1
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="rejected row count"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_nonzero_coefficient_only_lineage_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["lineage"]["coefficient_only_keys_marked_retained"] = 1
    _write_sizing_receipt(built, document)
    with pytest.raises(
        gate2.AuthorityError, match="coefficient-only keys are marked retained"
    ):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_receipt_258_schema_mismatch_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["schema_version"] = "cex002_gate2_storage_sizing_v2"
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="schema version changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_receipt_258_ticket_mismatch_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["ticket"] = "OTHER"
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="ticket changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_lineage_key_count_mismatch_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    document["lineage"]["retained_archive_requirement_keys"] = 99
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="lineage key count changed"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_nonzero_unverified_count_is_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    document = json.loads(built["paths"].receipt_258_path.read_text(encoding="utf-8"))
    credit = document["physical_inputs"]["retained_credit"]
    credit["unverified_objects"] = 1
    credit["report_summary"]["unverified_retained_objects"] = 1
    _write_sizing_receipt(built, document)
    with pytest.raises(gate2.AuthorityError, match="unverified object count"):
        _run_plan(built)
    _assert_no_installed_plan(built)


def test_aliased_retained_digests_are_rejected_before_plan_publication(
    tmp_path: Path,
) -> None:
    key1 = _key("daily/klines", "BTCUSDT", "2020-01-01")
    key2 = _key("daily/klines", "BTCUSDT", "2020-01-02")
    built = _tiny_retained_universe(tmp_path, credit_keys={key1, key2})

    def _alias(document: dict[str, Any]) -> None:
        first = document["objects"][key1]
        digest = str(first["sha256"])
        sidecar_body = f"{digest} {key2.rsplit('/', 1)[-1]}\n".encode()
        sidecar_path, sidecar_digest = persist_provider_sidecar(
            sidecar_body, sidecar_dir=built["paths"].listing_cache_dir
        )
        document["objects"][key2]["sha256"] = digest
        document["objects"][key2]["provider_checksum"] = digest
        document["objects"][key2]["byte_size"] = first["byte_size"]
        document["objects"][key2]["provider_checksum_path"] = str(sidecar_path)
        document["objects"][key2]["provider_checksum_sha256"] = sidecar_digest

    _rewrite_progress(built, _alias)
    with pytest.raises(gate2.AuthorityError, match="retained credit objects are aliased"):
        _run_plan(built)
    _assert_no_installed_plan(built)


@pytest.mark.parametrize("value", ["12", True])
def test_retained_progress_byte_size_must_be_an_exact_positive_integer(
    tmp_path: Path, value: Any
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})

    def _coerce(document: dict[str, Any]) -> None:
        document["objects"][key]["byte_size"] = value

    _rewrite_progress(built, _coerce)
    with pytest.raises(gate2.AuthorityError, match="retained progress byte size"):
        _run_plan(built)
    _assert_no_installed_plan(built)


@pytest.mark.parametrize(
    ("mutate", "match"),
    (
        (
            lambda doc: doc["retained_credit"].__setitem__("extra", True),
            "extra or missing fields",
        ),
        (
            lambda doc: doc["retained_credit"].pop("unverified_objects"),
            "extra or missing fields",
        ),
        (
            lambda doc: doc["retained_credit"].__setitem__(
                "key_set_sha256", "A" * 64
            ),
            "key-set digest is not sha256",
        ),
        (
            lambda doc: doc["retained_credit"].__setitem__("objects", 99),
            "aliased|object count",
        ),
        (
            lambda doc: doc["retained_credit"].__setitem__("bytes", 1),
            "retained credit bytes changed",
        ),
        (
            lambda doc: doc["retained_credit"].__setitem__("unverified_objects", 1),
            "unverified object count",
        ),
        (
            lambda doc: (
                doc["retained_credit"].__setitem__("selected_retained_keys", 0),
                doc["retained_credit"].__setitem__("cost_retained_keys", 0),
            ),
            "selected and cost keys do not sum",
        ),
    ),
)
def test_compact_plan_receipt_values_are_authenticated_on_replay(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
    match: str,
) -> None:
    key = _key("daily/klines", "BTCUSDT", "2020-01-01")
    built = _tiny_retained_universe(tmp_path, credit_keys={key})
    _run_plan(built)
    _rewrite_installed_plan_receipt(built, mutate)
    state = _open_state(built["paths"])
    try:
        with pytest.raises(gate2.UnsafeStateError, match=match):
            state.authenticate_prefix()
    finally:
        state.close()
