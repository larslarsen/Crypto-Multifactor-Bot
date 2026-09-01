"""Synthetic proof of the ADR-0031 Gate-2 revision-candidate planner.

Every test is temporary-rooted, offline, and free of the live Gate-2 store and the
acquisition engine.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import urllib.error
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition import binance_usdm_gate2_revision_candidate as planner

REPOSITORY = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "binance_usdm_gate2_revision_candidate"
)
RUN7 = "a" * 64
PREFIX7 = "c" * 64
PLAN_ID = "d" * 64
PLAN_RECEIPT = "e" * 64
SOURCE_SHA = planner.GENERATION0_SOURCE_SHA256
CLI_SHA = planner.GENERATION0_CLI_SHA256
CHECKSUM_A = "2" * 64
CHECKSUM_B = "3" * 64
CHECKSUM_C = "4" * 64
CHECKSUM_D = "5" * 64
RUN_RECEIPT_BODY = planner.canonical_json({"run_id": RUN7, "stop": "partial"})
RECEIPT7 = planner.sha256_bytes(RUN_RECEIPT_BODY)
METRICS_A = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2024-01-01.zip"
METRICS_B = "data/futures/um/daily/metrics/ETHUSDT/ETHUSDT-metrics-2024-01-01.zip"
METRICS_DONE = "data/futures/um/daily/metrics/SOLUSDT/SOLUSDT-metrics-2024-01-01.zip"
BOOK_A = "data/futures/um/daily/bookTicker/BTCUSDT/BTCUSDT-bookTicker-2024-01-01.zip"
PINS_INT_KEYS = {
    "coinalyze_logical_receipts",
    "coinalyze_supported",
    "coinalyze_unsupported",
    "combined_bytes",
    "combined_objects",
    "cost_bytes",
    "cost_objects",
    "main_selected_bytes",
    "main_selected_objects",
    "new_binance_raw_bytes",
    "new_coinalyze_raw_bytes",
    "retained_credit_bytes",
    "retained_credit_objects",
    "stable_requirement_bytes",
}


def _load_cli() -> Any:
    path = REPOSITORY / planner.CLI_RELATIVE
    spec = importlib.util.spec_from_file_location("gate2_revision_candidate_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pins_json(device: str) -> str:
    document: dict[str, Any] = {}
    for key in planner.PINS_JSON_KEYS:
        if key in PINS_INT_KEYS:
            document[key] = 0
        elif key == "destination":
            document[key] = planner.FIXED_STORE_ROOT
        elif key == "device":
            document[key] = device
        else:
            document[key] = "0" * 64
    return json.dumps(document, sort_keys=True)


def _payload(identity: str, *, family: str, symbol: str, listed_bytes: int) -> str:
    interval = planner.ECONOMIC_DATE.search(identity)
    assert interval is not None
    body = {
        "economic_interval": interval.group(1),
        "family": family,
        "key": identity,
        "listed_bytes": listed_bytes,
        "retained": False,
        "sidecar_key": f"{identity}.CHECKSUM",
        "sidecar_url": f"{planner.VISION_OBJECT_BASE}/{identity}.CHECKSUM",
        "symbol": symbol,
        "url": f"{planner.VISION_OBJECT_BASE}/{identity}",
    }
    if family == planner.FAMILY_METRICS:
        body["consumable"] = False
    elif family == planner.FAMILY_BOOK_TICKER:
        body["etag"] = "zip"
    return planner.compact_json(
        {
            "identity": identity,
            "kind": planner.KIND_BINANCE,
            "payload": body,
            "provider": planner.PROVIDER_BINANCE,
        }
    ).decode("utf-8")


def _coinalyze_payload(identity: str, kind: str) -> str:
    return planner.compact_json(
        {
            "identity": identity,
            "kind": kind,
            "payload": {"native_symbol": identity},
            "provider": planner.PROVIDER_COINALYZE,
        }
    ).decode("utf-8")


def _write_sidecar(content_root: Path, basename: str, checksum: str) -> tuple[str, str, int, bytes]:
    body = f"{checksum}  {basename}\n".encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    path = content_root / digest[:2] / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    os.chmod(path, 0o600)
    return digest, str(path), len(body), body


def _fact(identity: str, message: str) -> str:
    return planner.compact_json(
        {
            "error": message,
            "kind": "validation",
            "status": 200,
            "url": f"{planner.VISION_OBJECT_BASE}/{identity}",
        }
    ).decode("utf-8")


def _insert_binance(
    conn: sqlite3.Connection,
    content_root: Path,
    identity: str,
    *,
    family: str,
    symbol: str,
    listed_bytes: int,
    checksum: str,
    pending: bool,
    message: str | None = None,
) -> bytes:
    conn.execute(
        "INSERT INTO plan_entry(provider, identity, kind, payload_json) VALUES (?, ?, ?, ?)",
        (
            planner.PROVIDER_BINANCE,
            identity,
            planner.KIND_BINANCE,
            _payload(identity, family=family, symbol=symbol, listed_bytes=listed_bytes),
        ),
    )
    digest, path, size, body = _write_sidecar(
        content_root, identity.rsplit("/", 1)[-1], checksum
    )
    conn.execute(
        "INSERT INTO sidecar_fact(provider, identity, sidecar_sha256, sidecar_path, "
        "sidecar_bytes, provider_checksum) VALUES (?, ?, ?, ?, ?, ?)",
        (planner.PROVIDER_BINANCE, identity, digest, path, size, checksum),
    )
    if pending:
        assert message is not None
        conn.execute(
            "INSERT INTO attempt(provider, identity, started_at, ended_at, class, "
            "status_code, redacted_fact_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                planner.PROVIDER_BINANCE,
                identity,
                "2026-08-31T17:00:00+00:00",
                "2026-08-31T17:00:01+00:00",
                planner.RETRY_TERMINAL,
                200,
                _fact(identity, message),
            ),
        )
        return body
    conn.execute(
        "INSERT INTO attempt(provider, identity, started_at, ended_at, class, "
        "status_code, redacted_fact_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            planner.PROVIDER_BINANCE,
            identity,
            "2026-08-31T17:00:00+00:00",
            "2026-08-31T17:00:01+00:00",
            "ok",
            200,
            planner.compact_json(
                {
                    "error": "",
                    "kind": "ok",
                    "status": 200,
                    "url": f"{planner.VISION_OBJECT_BASE}/{identity}",
                }
            ).decode("utf-8"),
        ),
    )
    conn.execute(
        "INSERT INTO completion(provider, identity, content_sha256, content_path, "
        "sidecar_sha256, sidecar_path, listed_bytes, retrieved_at, revision_json, "
        "validation_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 'checksum_verified')",
        (
            planner.PROVIDER_BINANCE,
            identity,
            checksum,
            str(content_root / checksum[:2] / checksum),
            digest,
            path,
            listed_bytes,
            "2026-08-31T17:00:01+00:00",
        ),
    )
    return body


def _insert_coinalyze_closed(
    conn: sqlite3.Connection,
    *,
    supported: int = 1,
    unsupported: int = 1,
) -> tuple[int, int, int, int]:
    conn.execute(
        "INSERT INTO plan_entry(provider, identity, kind, payload_json) VALUES (?, ?, ?, ?)",
        (
            planner.PROVIDER_COINALYZE,
            "inventory",
            planner.KIND_COINALYZE_INVENTORY,
            _coinalyze_payload("inventory", planner.KIND_COINALYZE_INVENTORY),
        ),
    )
    supported_ids = [f"COIN{index:04d}USDT_PERP.A" for index in range(supported)]
    unsupported_ids = [f"unsupported:GAP{index:04d}" for index in range(unsupported)]
    for identity in supported_ids:
        conn.execute(
            "INSERT INTO plan_entry(provider, identity, kind, payload_json) VALUES (?, ?, ?, ?)",
            (
                planner.PROVIDER_COINALYZE,
                identity,
                planner.KIND_COINALYZE_LIQUIDATION,
                _coinalyze_payload(identity, planner.KIND_COINALYZE_LIQUIDATION),
            ),
        )
    for identity in unsupported_ids:
        conn.execute(
            "INSERT INTO plan_entry(provider, identity, kind, payload_json) VALUES (?, ?, ?, ?)",
            (
                planner.PROVIDER_COINALYZE,
                identity,
                planner.KIND_COINALYZE_UNSUPPORTED,
                _coinalyze_payload(identity, planner.KIND_COINALYZE_UNSUPPORTED),
            ),
        )
    for identity in ["inventory", *supported_ids]:
        conn.execute(
            "INSERT INTO completion(provider, identity, content_sha256, content_path, "
            "listed_bytes, retrieved_at, revision_json, validation_state) "
            "VALUES (?, ?, ?, ?, 1, ?, '{}', 'checksum_verified')",
            (planner.PROVIDER_COINALYZE, identity, "6" * 64, "/tmp/coinalyze", "2026-08-31T17:00:01+00:00"),
        )
    charged_bytes = 0
    charged_points = 0
    for index, identity in enumerate(supported_ids):
        byte_count = 10 + index
        points = 2 + index
        charged_bytes += byte_count
        charged_points += points
        conn.execute(
            "INSERT INTO coinalyze_charge(provider, identity, generation, content_sha256, "
            "charged_bytes, http_status, outcome, points, request_proof, retrieval_json, "
            "revision_json, created_at) VALUES (?, ?, 1, ?, ?, 200, ?, ?, ?, '{}', '{}', ?)",
            (
                planner.PROVIDER_COINALYZE,
                identity,
                hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                byte_count,
                planner.OUTCOME_CHECKSUM_VERIFIED,
                points,
                "7" * 64,
                "2026-08-31T17:00:00+00:00",
            ),
        )
        for offset, status in enumerate(
            (planner.CHARGE_RESERVED, planner.CHARGE_PUBLISHED, planner.CHARGE_SETTLED)
        ):
            conn.execute(
                "INSERT INTO charge_transition(provider, identity, generation, status, at) "
                "VALUES (?, ?, 1, ?, ?)",
                (
                    planner.PROVIDER_COINALYZE,
                    identity,
                    status,
                    f"2026-08-31T17:00:0{offset}+00:00",
                ),
            )
    for identity in unsupported_ids:
        conn.execute(
            "INSERT INTO terminal_gap(provider, identity, kind, fact_json) VALUES (?, ?, ?, ?)",
            (planner.PROVIDER_COINALYZE, identity, planner.GAP_UNSUPPORTED, "{}"),
        )
    conn.execute("UPDATE coinalyze_ledger SET charged=? WHERE id=1", (charged_bytes,))
    return supported, supported * 3, charged_bytes, charged_points


def _insert_run(conn: sqlite3.Connection) -> tuple[int, int, int]:
    attempts = int(conn.execute("SELECT COALESCE(MAX(id), 0) FROM attempt").fetchone()[0])
    completions = int(conn.execute("SELECT COALESCE(MAX(seq), 0) FROM completion").fetchone()[0])
    sidecars = int(conn.execute("SELECT COALESCE(MAX(seq), 0) FROM sidecar_fact").fetchone()[0])
    charges = int(conn.execute("SELECT COALESCE(MAX(seq), 0) FROM coinalyze_charge").fetchone()[0])
    transitions = int(conn.execute("SELECT COALESCE(MAX(seq), 0) FROM charge_transition").fetchone()[0])
    conn.execute(
        "INSERT INTO run_metadata(run_id, started_at, ended_at, stop_reason, attempt_hi, "
        "network_calls, start_snapshot_json, error_count, network_sample_json, "
        "pre_capacity_json, post_capacity_json, capacity_blocked, attempt_delta, "
        "completion_delta, gap_delta, byte_delta, open_coinalyze_charges, counts_json) "
        "VALUES (?, ?, ?, 'partial', ?, 0, '{}', 0, '[]', '{}', '{}', 0, 0, 0, 0, 0, 0, '{}')",
        (RUN7, "2026-08-31T17:47:26+00:00", "2026-08-31T19:08:55+00:00", attempts),
    )
    conn.execute(
        "INSERT INTO run_publication(run_id, receipt_sha256, receipt_directory, receipt_body) "
        "VALUES (?, ?, 'run_receipts', ?)",
        (RUN7, RECEIPT7, RUN_RECEIPT_BODY.decode("utf-8")),
    )
    conn.execute(
        "INSERT INTO run_seal(run_id, receipt_sha256, predecessor_sha256, prefix_digest, "
        "marks_json) VALUES (?, ?, ?, ?, '{}')",
        (RUN7, RECEIPT7, "0" * 64, PREFIX7),
    )
    conn.execute(
        "INSERT INTO seal_head(id, receipt_sha256, receipt_path, prefix_digest, attempt_hi, "
        "completion_hi, sidecar_hi, charge_hi, transition_hi, run_hi, seal_hi, "
        "predecessor_sha256) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)",
        (
            RECEIPT7,
            f"run_receipts/{RECEIPT7}.json",
            PREFIX7,
            attempts,
            completions,
            sidecars,
            charges,
            transitions,
            "0" * 64,
        ),
    )
    return attempts, completions, sidecars


def _family_coverage(conn: sqlite3.Connection) -> tuple[tuple[str, int, int, int, int], ...]:
    rows = conn.execute(
        "SELECT json_extract(p.payload_json, '$.payload.family'), COUNT(*), "
        "SUM(CASE WHEN c.identity IS NOT NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN g.identity IS NOT NULL THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN c.identity IS NULL AND g.identity IS NULL THEN 1 ELSE 0 END) "
        "FROM plan_entry p LEFT JOIN completion c ON c.provider=p.provider AND c.identity=p.identity "
        "LEFT JOIN terminal_gap g ON g.provider=p.provider AND g.identity=p.identity "
        "WHERE p.provider=? AND p.kind=? GROUP BY 1 ORDER BY 1",
        (planner.PROVIDER_BINANCE, planner.KIND_BINANCE),
    ).fetchall()
    return tuple((str(r[0]), int(r[1]), int(r[2] or 0), int(r[3] or 0), int(r[4] or 0)) for r in rows)


def _message_counts(specs: Sequence[tuple[str, int, str, str]]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for _identity, _size, _checksum, message in specs:
        counts[message] = counts.get(message, 0) + 1
    return tuple(sorted(counts.items()))


def build_store(
    tmp_path: Path,
    *,
    pending_metrics: Sequence[tuple[str, int, str, str]] | None = None,
    pending_book: Sequence[tuple[str, int, str, str]] | None = None,
    extra_pending: Sequence[tuple[str, str, int, str, str]] = (),
    application_id: int | None = None,
    include_completed: bool = True,
    wal_mode: bool = True,
) -> dict[str, Any]:
    store = tmp_path / "data" / "cex002_qualify"
    gate2 = store / "gate2"
    content = gate2 / "content"
    content.mkdir(parents=True)
    (gate2 / "tmp").mkdir()
    (gate2 / planner.LOCK_NAME).write_bytes(b"lock\n")
    os.chmod(gate2 / planner.LOCK_NAME, 0o600)
    sqlite_path = gate2 / planner.SQLITE_NAME
    conn = sqlite3.connect(sqlite_path)
    sidecar_bodies: dict[str, bytes] = {}
    try:
        if wal_mode:
            conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(planner.SCHEMA_SQL)
        conn.execute(
            f"PRAGMA application_id={int(planner.STATE_APPLICATION_ID if application_id is None else application_id)}"
        )
        conn.execute(f"PRAGMA user_version={int(planner.STATE_USER_VERSION)}")
        device = f"dev:{gate2.stat().st_dev}"
        code = {
            "acquisition_cli_sha256": CLI_SHA,
            "acquisition_source_sha256": SOURCE_SHA,
            "policy_identity": planner.GENERATION0_POLICY_IDENTITY,
        }
        conn.execute(
            "INSERT INTO authority(id, plan_identity, plan_receipt_sha256, pins_json, "
            "code_json, destination, device, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
            (
                PLAN_ID,
                PLAN_RECEIPT,
                _pins_json(device),
                json.dumps(code, sort_keys=True),
                planner.FIXED_STORE_ROOT,
                device,
                "2026-08-30T00:00:00+00:00",
            ),
        )
        conn.execute("INSERT INTO coinalyze_ledger(id, charged) VALUES (1, 0)")
        metrics = list(
            pending_metrics
            if pending_metrics is not None
            else (
                (METRICS_A, 100, CHECKSUM_A, planner.MSG_SIZE),
                (METRICS_B, 200, CHECKSUM_B, planner.MSG_CEILING),
            )
        )
        book = list(
            pending_book
            if pending_book is not None
            else ((BOOK_A, 8_932_817, CHECKSUM_C, planner.MSG_ZIP),)
        )
        for identity, size, checksum, message in metrics:
            sidecar_bodies[identity] = _insert_binance(
                conn, content, identity, family=planner.FAMILY_METRICS,
                symbol=identity.split("/")[-2], listed_bytes=size, checksum=checksum,
                pending=True, message=message,
            )
        for identity, size, checksum, message in book:
            sidecar_bodies[identity] = _insert_binance(
                conn, content, identity, family=planner.FAMILY_BOOK_TICKER,
                symbol=identity.split("/")[-2], listed_bytes=size, checksum=checksum,
                pending=True, message=message,
            )
        for identity, family, size, checksum, message in extra_pending:
            sidecar_bodies[identity] = _insert_binance(
                conn, content, identity, family=family, symbol="X", listed_bytes=size,
                checksum=checksum, pending=True, message=message,
            )
        if include_completed:
            sidecar_bodies[METRICS_DONE] = _insert_binance(
                conn, content, METRICS_DONE, family=planner.FAMILY_METRICS,
                symbol="SOLUSDT", listed_bytes=50, checksum=CHECKSUM_D, pending=False,
            )
        charge_count, transition_count, charged_bytes, charged_points = (
            _insert_coinalyze_closed(conn)
        )
        attempt_hi, completion_hi, sidecar_hi = _insert_run(conn)
        conn.commit()
        if wal_mode:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        coverage = _family_coverage(conn)
        plan_rows = int(conn.execute("SELECT COUNT(*) FROM plan_entry").fetchone()[0])
        attempts = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
        completions = int(conn.execute("SELECT COUNT(*) FROM completion").fetchone()[0])
        sidecars = int(conn.execute("SELECT COUNT(*) FROM sidecar_fact").fetchone()[0])
        gaps = int(conn.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0])
    finally:
        conn.close()
    wal = gate2 / planner.SQLITE_WAL_NAME
    shm = gate2 / planner.SQLITE_SHM_NAME
    if not wal.exists():
        wal.write_bytes(b"")
    if not shm.exists():
        shm.write_bytes(b"\x00" * 32_768)
    state_bytes = sqlite_path.read_bytes()
    wal_bytes = wal.read_bytes()
    shm_bytes = shm.read_bytes()
    pending_specs = list(metrics) + list(book)
    pins = planner.PlannerPins(
        run7_receipt_sha256=RECEIPT7,
        run7_run_id=RUN7,
        generation0_source_sha256=SOURCE_SHA,
        generation0_cli_sha256=CLI_SHA,
        expected_plan_rows=plan_rows,
        expected_attempts=attempts,
        expected_completions=completions,
        expected_sidecars=sidecars,
        expected_gaps=gaps,
        expected_runs=1,
        expected_publications=1,
        expected_seals=1,
        expected_charges=charge_count,
        expected_charge_transitions=transition_count,
        expected_pending_metrics=len(metrics),
        expected_pending_book_ticker=len(book),
        expected_attempt_hi=attempt_hi,
        expected_completion_hi=completion_hi,
        expected_sidecar_hi=sidecar_hi,
        expected_charge_hi=charge_count,
        expected_transition_hi=transition_count,
        expected_run_hi=1,
        expected_seal_hi=1,
        expected_charged_bytes=charged_bytes,
        expected_charge_points=charged_points,
        expected_reserved_transitions=charge_count,
        expected_published_transitions=charge_count,
        expected_settled_transitions=charge_count,
        expected_inventory_complete=1,
        expected_liquidation_complete=1,
        expected_state_bytes=len(state_bytes),
        expected_state_sha256=hashlib.sha256(state_bytes).hexdigest(),
        expected_wal_bytes=len(wal_bytes),
        expected_wal_sha256=hashlib.sha256(wal_bytes).hexdigest(),
        expected_shm_bytes=len(shm_bytes),
        expected_shm_sha256=hashlib.sha256(shm_bytes).hexdigest(),
        expected_pending_metrics_bytes=sum(item[1] for item in metrics),
        expected_pending_book_bytes=sum(item[1] for item in book),
        require_physical_state_pins=True,
        expected_message_counts=_message_counts(pending_specs),
        expected_family_coverage=coverage,
    )
    return {
        "book": book,
        "content": content,
        "gate2": gate2,
        "metrics": metrics,
        "paths": planner.default_paths(REPOSITORY, store),
        "pins": pins,
        "sidecar_bodies": sidecar_bodies,
        "store": store,
    }


class ScriptedTransport:
    def __init__(self, pages: Mapping[tuple[str, str | None], str], *, redirect: bool = False) -> None:
        self.pages = dict(pages)
        self.urls: list[str] = []
        self.redirect = redirect

    def fetch(self, url: str, *, max_bytes: int) -> planner.ListingResponse:
        self.urls.append(url)
        parsed = urllib.parse.urlsplit(url)
        if parsed.path.endswith(".zip"):
            raise AssertionError(f"raw ZIP GET is forbidden: {parsed.path}")
        if self.redirect:
            raise planner.BlockedCandidateError("listing redirect is forbidden")
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        prefix = query["prefix"][0]
        token = query.get("continuation-token", [None])[0]
        try:
            body = self.pages[(prefix, token)]
        except KeyError as exc:
            raise planner.BlockedCandidateError("unexpected listing request") from exc
        encoded = body.encode("utf-8") if isinstance(body, str) else body
        if len(encoded) > max_bytes:
            raise planner.BlockedCandidateError("listing page exceeded the accepted byte ceiling")
        return planner.ListingResponse(status_code=200, url=url, headers={"etag": "list"}, body=encoded)


class TransientTransport(ScriptedTransport):
    def __init__(self, pages: Mapping[tuple[str, str | None], str], *, fail_on: int) -> None:
        super().__init__(pages)
        self.fail_on = fail_on
        self.calls = 0

    def fetch(self, url: str, *, max_bytes: int) -> planner.ListingResponse:
        self.calls += 1
        if self.calls == self.fail_on:
            raise urllib.error.URLError("injected dns failure")
        return super().fetch(url, max_bytes=max_bytes)


class SecondPassDriftTransport(ScriptedTransport):
    def __init__(
        self,
        pages: Mapping[tuple[str, str | None], str],
        *,
        drift_request: tuple[str, str | None],
        drift_body: str,
    ) -> None:
        super().__init__(pages)
        self.drift_request = drift_request
        self.drift_body = drift_body
        self.request_counts: dict[tuple[str, str | None], int] = {}

    def fetch(self, url: str, *, max_bytes: int) -> planner.ListingResponse:
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        request = (
            query["prefix"][0],
            query.get("continuation-token", [None])[0],
        )
        self.request_counts[request] = self.request_counts.get(request, 0) + 1
        if request == self.drift_request and self.request_counts[request] == 2:
            self.urls.append(url)
            body = self.drift_body.encode("utf-8")
            return planner.ListingResponse(
                status_code=200,
                url=url,
                headers={"etag": "pass-two"},
                body=body,
            )
        return super().fetch(url, max_bytes=max_bytes)


class ResponseOverrideTransport(ScriptedTransport):
    def __init__(
        self,
        pages: Mapping[tuple[str, str | None], str],
        *,
        final_url_suffix: str = "",
        oversized: bool = False,
        status_code: int = 200,
        content_length_adjustment: int = 0,
    ) -> None:
        super().__init__(pages)
        self.final_url_suffix = final_url_suffix
        self.oversized = oversized
        self.status_code = status_code
        self.content_length_adjustment = content_length_adjustment

    def fetch(self, url: str, *, max_bytes: int) -> planner.ListingResponse:
        response = super().fetch(url, max_bytes=max_bytes)
        body = response.body
        if self.oversized:
            body = b"x" * (max_bytes + 1)
        return planner.ListingResponse(
            status_code=self.status_code,
            url=response.url + self.final_url_suffix,
            headers={
                "content-length": str(len(body) + self.content_length_adjustment),
                "etag": "exact",
            },
            body=body,
        )


def _parent(key: str) -> str:
    return key.rsplit("/", 1)[0] + "/"


def _nested_pages(
    metrics: Sequence[tuple[str, int, str, str]],
    book: Sequence[tuple[str, int, str, str]],
    sidecar_bodies: Mapping[str, bytes],
    *,
    current: Mapping[str, int] | None = None,
    extra: Sequence[tuple[str, int, bytes]] = (),
    metrics_pages: int = 1,
) -> dict[tuple[str, str | None], str]:
    pages: dict[tuple[str, str | None], str] = {}
    metric_groups: dict[str, list[planner.ListingObject]] = {}
    for identity, old, _checksum, _msg in metrics:
        parent = _parent(identity)
        body = sidecar_bodies[identity]
        size = int((current or {}).get(identity, old))
        metric_groups.setdefault(parent, []).extend(
            [
                planner.ListingObject(key=identity, size=size, etag="zip"),
                planner.ListingObject(
                    key=f"{identity}.CHECKSUM",
                    size=len(body),
                    etag=planner.md5_hex(body),
                ),
            ]
        )
    for identity, size, body in extra:
        parent = _parent(identity)
        metric_groups.setdefault(parent, []).extend(
            [
                planner.ListingObject(key=identity, size=size, etag="extra"),
                planner.ListingObject(
                    key=f"{identity}.CHECKSUM", size=len(body), etag=planner.md5_hex(body)
                ),
            ]
        )
    pages[(planner.FAMILY_PREFIXES[0], None)] = planner.write_s3_list_bucket(
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        prefixes=sorted(metric_groups),
    )
    for parent, objects in metric_groups.items():
        if metrics_pages == 2 and parent == _parent(metrics[0][0]) and len(objects) >= 4:
            pages[(parent, None)] = planner.write_s3_list_bucket(
                prefix=parent,
                delimiter="/",
                objects=objects[:2],
                truncated=True,
                continuation="page-2",
            )
            pages[(parent, "page-2")] = planner.write_s3_list_bucket(
                prefix=parent,
                delimiter="/",
                objects=objects[2:],
                continuation_token="page-2",
            )
        else:
            pages[(parent, None)] = planner.write_s3_list_bucket(
                prefix=parent, delimiter="/", objects=objects
            )
    book_groups: dict[str, list[planner.ListingObject]] = {}
    for identity, old, _checksum, _msg in book:
        parent = _parent(identity)
        body = sidecar_bodies[identity]
        size = int((current or {}).get(identity, old))
        book_groups.setdefault(parent, []).extend(
            [
                planner.ListingObject(key=identity, size=size, etag="zip"),
                planner.ListingObject(
                    key=f"{identity}.CHECKSUM", size=len(body), etag=planner.md5_hex(body)
                ),
            ]
        )
    pages[(planner.FAMILY_PREFIXES[1], None)] = planner.write_s3_list_bucket(
        prefix=planner.FAMILY_PREFIXES[1],
        delimiter="/",
        prefixes=sorted(book_groups),
    )
    for parent, objects in book_groups.items():
        pages[(parent, None)] = planner.write_s3_list_bucket(
            prefix=parent, delimiter="/", objects=objects
        )
    return pages


def _run(built: Mapping[str, Any], transport: Any, **hook_fields: Any) -> dict[str, Any]:
    hook_fields.setdefault("retrieval_clock", lambda: "2026-08-31T20:00:00+00:00")
    hooks = planner.PlannerHooks(
        available_bytes=lambda _fd: 200 * 1024 * 1024 * 1024,
        **hook_fields,
    )
    return planner.plan_revision_candidate(
        built["paths"], built["pins"], hooks=hooks, transport=transport
    )


def _without_physical_pins(built: Mapping[str, Any]) -> dict[str, Any]:
    changed = dict(built)
    changed["pins"] = replace(built["pins"], require_physical_state_pins=False)
    return changed


def _rewrite_checkpoint(built: Mapping[str, Any], mutate: Any) -> None:
    path = built["paths"].candidate_root / planner.CHECKPOINT_NAME
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_bytes(planner.canonical_json(document))


def _asset_bytes(result: Mapping[str, Any]) -> dict[str, bytes]:
    locator_path = Path(result["locator_path"])
    locator = json.loads(locator_path.read_text(encoding="utf-8"))
    root = locator_path.parent
    return {
        "lineage": (root / planner.LINEAGE_NAME / locator["lineage_name"]).read_bytes(),
        "locator": locator_path.read_bytes(),
        "manifest": (root / planner.MANIFEST_NAME / locator["manifest_name"]).read_bytes(),
        "receipt": (root / planner.RECEIPT_NAME / locator["receipt_name"]).read_bytes(),
    }


def _with_copied_authority_repository(
    built: Mapping[str, Any], repository: Path
) -> dict[str, Any]:
    for relative in (
        planner.SOURCE_RELATIVE,
        planner.CLI_RELATIVE,
        planner.ACQUISITION_SOURCE_RELATIVE,
        planner.ACQUISITION_CLI_RELATIVE,
    ):
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY / relative, destination)
    changed = dict(built)
    changed["paths"] = planner.default_paths(repository, built["store"])
    return changed


def _mutate_state(built: Mapping[str, Any], statement: str, parameters: Sequence[Any] = ()) -> None:
    conn = sqlite3.connect(built["gate2"] / planner.SQLITE_NAME)
    try:
        conn.execute(statement, tuple(parameters))
        conn.commit()
    finally:
        conn.close()


def test_production_pins_match_adr() -> None:
    assert planner.PRODUCTION_PINS.expected_pending_metrics == 50_921
    assert planner.PRODUCTION_PINS.expected_pending_book_ticker == 354
    assert planner.MSG_SIZE.startswith("AcquisitionError: ")
    assert planner.MSG_ZIP.startswith("AcquisitionError: ")
    assert dict(planner.PRODUCTION_MESSAGE_COUNTS)[planner.MSG_SIZE] == 12_576
    assert dict(planner.PRODUCTION_MESSAGE_COUNTS)[planner.MSG_ZIP] == 354
    assert planner.PRODUCTION_PINS.expected_state_sha256 == planner.GENERATION0_STATE_SHA256


def test_zip_policy_lower_equal_upper_ratio_absolute() -> None:
    floor = planner.ZIP_FLOOR_BYTES
    absolute = planner.ZIP_ABSOLUTE_CEILING_BYTES
    assert planner.zip_work_ceiling(1) == floor
    assert planner.zip_work_ceiling(floor // planner.ZIP_RATIO) == floor
    just_above = floor // planner.ZIP_RATIO + 1
    assert planner.zip_work_ceiling(just_above) == just_above * planner.ZIP_RATIO
    assert planner.zip_work_ceiling(absolute // planner.ZIP_RATIO) == absolute
    assert planner.zip_work_ceiling(absolute // planner.ZIP_RATIO + 1) == absolute
    with pytest.raises(planner.BlockedCandidateError):
        planner.zip_work_ceiling(-1)


def test_complete_candidate_and_immutable_sqlite_leaves(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    gate2_fd = planner.open_root_dir(built["gate2"], create=False)
    try:
        before = planner.inventory_tree(gate2_fd)
        sqlite_before = planner.snapshot_sqlite_leaves(gate2_fd)
    finally:
        os.close(gate2_fd)
    transport = ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"]))
    result = _run(built, transport)
    assert result["exit_code"] == planner.EXIT_COMPLETE
    assert result["receipt"]["authorization"]["candidate_accepted"] is False
    assert result["receipt"]["pending"]["total"] == 3
    assert (built["paths"].candidate_root / planner.LOCATOR_NAME).is_file()
    gate2_fd = planner.open_root_dir(built["gate2"], create=False)
    try:
        after = planner.inventory_tree(gate2_fd)
        sqlite_after = planner.snapshot_sqlite_leaves(gate2_fd)
    finally:
        os.close(gate2_fd)
    assert before == after
    assert sqlite_before == sqlite_after
    with gzip.open(result["manifest_path"], "rb") as handle:
        rows = [json.loads(line)["record"] for line in handle]
    book = next(row for row in rows if row["family"] == planner.FAMILY_BOOK_TICKER)
    assert book["terminal_message"] == planner.MSG_ZIP
    assert book["old_plan_facts"]["url"].startswith(planner.VISION_OBJECT_BASE)
    assert "id" in book["terminal_attempt"]


def test_lock_nonblocking_writer_refused(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    lock_fd = os.open(str(built["gate2"] / planner.LOCK_NAME), os.O_RDWR)
    try:
        import fcntl

        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = _run(
            built,
            ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
        )
        assert result["exit_code"] == planner.EXIT_UNSAFE
    finally:
        os.close(lock_fd)


def test_no_network_state_preproof(tmp_path: Path) -> None:
    built = build_store(tmp_path, application_id=1)
    transport = ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"]))
    result = _run(built, transport)
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert transport.urls == []


def test_bare_diagnostic_is_rejected(tmp_path: Path) -> None:
    built = build_store(
        tmp_path,
        pending_metrics=((METRICS_A, 100, CHECKSUM_A, "listed byte size does not match"),),
        pending_book=(),
    )
    result = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED


def test_wal_mode_query_only_does_not_mutate_active_tree(tmp_path: Path) -> None:
    built = build_store(tmp_path, wal_mode=True)
    gate2_fd = planner.open_root_dir(built["gate2"], create=False)
    try:
        before = planner.inventory_tree(gate2_fd)
    finally:
        os.close(gate2_fd)
    result = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
    )
    assert result["exit_code"] == planner.EXIT_COMPLETE
    gate2_fd = planner.open_root_dir(built["gate2"], create=False)
    try:
        after = planner.inventory_tree(gate2_fd)
    finally:
        os.close(gate2_fd)
    assert before == after


def test_unknown_extra_pending_rows_blocked(tmp_path: Path) -> None:
    extra = (
        (
            "data/futures/um/daily/klines/BTCUSDT/BTCUSDT-1h-2024-01-01.zip",
            "daily/klines",
            10,
            CHECKSUM_D,
            planner.MSG_SIZE,
        ),
    )
    built = build_store(tmp_path, extra_pending=extra)
    result = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "family" in result["message"]


def test_forged_equal_count_head_is_blocked(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    conn = sqlite3.connect(built["gate2"] / planner.SQLITE_NAME)
    try:
        conn.execute("UPDATE seal_head SET receipt_sha256=? WHERE id=1", ("0" * 64,))
        conn.commit()
    finally:
        conn.close()
    result = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED


def test_multi_page_resume_and_transient_failures(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(
        built["metrics"], built["book"], built["sidecar_bodies"], metrics_pages=2
    )
    before = TransientTransport(pages, fail_on=1)
    first = _run(built, before)
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    after_pages = TransientTransport(pages, fail_on=3)
    second = _run(built, after_pages)
    assert second["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    complete = _run(built, ScriptedTransport(pages))
    assert complete["exit_code"] == planner.EXIT_COMPLETE


def test_deterministic_uninterrupted_versus_resumed_identity(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(
        built["metrics"], built["book"], built["sidecar_bodies"], metrics_pages=2
    )
    uninterrupted = _run(built, ScriptedTransport(pages))
    uninterrupted_assets = _asset_bytes(uninterrupted)
    shutil.rmtree(built["paths"].candidate_root)
    first = _run(
        built,
        ScriptedTransport(pages),
        interrupt_after_pages=1,
    )
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    continued = _run(built, ScriptedTransport(pages))
    assert uninterrupted["semantic_sha256"] == continued["semantic_sha256"]
    assert _asset_bytes(continued) == uninterrupted_assets
    shutil.rmtree(built["paths"].candidate_root)
    reordered_pages = dict(reversed(list(pages.items())))
    reordered = _run(built, ScriptedTransport(reordered_pages))
    assert _asset_bytes(reordered) == uninterrupted_assets
    repeated = _run(built, ScriptedTransport(pages))
    assert _asset_bytes(repeated) == uninterrupted_assets


def test_publication_interrupt_leaves_no_locator(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    result = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
        interrupt_after_private_manifest=lambda: None,
    )
    assert result["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()
    resumed = _run(
        built,
        ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
    )
    assert resumed["exit_code"] == planner.EXIT_COMPLETE
    third = build_store(tmp_path / "before_locator")
    interrupted = _run(
        third,
        ScriptedTransport(_nested_pages(third["metrics"], third["book"], third["sidecar_bodies"])),
        interrupt_before_locator=lambda: None,
    )
    assert interrupted["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    assert not (third["paths"].candidate_root / planner.LOCATOR_NAME).exists()


@pytest.mark.parametrize(
    "boundary",
    [
        "interrupt_after_private_manifest",
        "interrupt_after_manifest_publish",
        "interrupt_after_lineage_publish",
        "interrupt_after_receipt_publish",
        "interrupt_before_locator",
    ],
)
def test_every_publication_boundary_recovers_byte_identically(
    tmp_path: Path, boundary: str
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    clean = _run(built, ScriptedTransport(pages))
    expected = _asset_bytes(clean)
    shutil.rmtree(built["paths"].candidate_root)
    partial = _run(
        built,
        ScriptedTransport(pages),
        **{boundary: lambda: None},
    )
    assert partial["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()
    recovered = _run(built, ScriptedTransport(pages))
    assert recovered["exit_code"] == planner.EXIT_COMPLETE
    assert _asset_bytes(recovered) == expected


def test_nonsemantic_retrieval_clocks_and_exact_lineage_metadata(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    first = _run(
        built,
        ScriptedTransport(pages),
        retrieval_clock=lambda: "2026-08-31T20:00:00+00:00",
    )
    first_assets = _asset_bytes(first)
    first_locator = json.loads(first_assets["locator"])
    first_lineage = json.loads(first_assets["lineage"])
    first_page = first_lineage["passes"]["pass_1"]["pages"][0]
    assert first_page["final_url"] == planner.listing_url(first_page["request"])
    assert first_page["status_code"] == 200
    assert first_page["byte_size"] > 0
    assert first_page["headers"] == {"etag": "list"}
    assert first_page["retrieved_at"] == "2026-08-31T20:00:00+00:00"
    shutil.rmtree(built["paths"].candidate_root)
    second = _run(
        built,
        ScriptedTransport(pages),
        retrieval_clock=lambda: "2026-08-31T20:00:01+00:00",
    )
    second_assets = _asset_bytes(second)
    second_locator = json.loads(second_assets["locator"])
    assert second["semantic_sha256"] == first["semantic_sha256"]
    assert second_locator["semantic_sha256"] == first_locator["semantic_sha256"]
    assert second_assets["manifest"] == first_assets["manifest"]
    assert second_assets["lineage"] != first_assets["lineage"]


@pytest.mark.parametrize("asset", ["manifest", "lineage", "receipt"])
@pytest.mark.parametrize("damage", ["missing", "tampered"])
def test_locator_recovery_authenticates_every_immutable_asset(
    tmp_path: Path, asset: str, damage: str
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    complete = _run(built, ScriptedTransport(pages))
    locator = json.loads(Path(complete["locator_path"]).read_text(encoding="utf-8"))
    directory, name = {
        "manifest": (planner.MANIFEST_NAME, locator["manifest_name"]),
        "lineage": (planner.LINEAGE_NAME, locator["lineage_name"]),
        "receipt": (planner.RECEIPT_NAME, locator["receipt_name"]),
    }[asset]
    path = built["paths"].candidate_root / directory / name
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"tampered")
    recovered = _run(built, ScriptedTransport(pages))
    assert recovered["exit_code"] in {planner.EXIT_BLOCKED, planner.EXIT_UNSAFE}


def test_locator_recovery_recomputes_canonical_receipt_claims(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    complete = _run(built, ScriptedTransport(pages))
    assert complete["exit_code"] == planner.EXIT_COMPLETE
    candidate = built["paths"].candidate_root
    locator_path = candidate / planner.LOCATOR_NAME
    locator = json.loads(locator_path.read_text(encoding="utf-8"))
    receipt_path = candidate / planner.RECEIPT_NAME / locator["receipt_name"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["bytes"]["metrics_delta_bytes"] += 1
    receipt["semantic_sha256"] = planner.sha256_bytes(
        planner.canonical_json(planner._semantic_receipt_payload(receipt))
    )
    forged_body = planner.canonical_json(receipt)
    forged_sha256 = planner.sha256_bytes(forged_body)
    forged_name = f"{forged_sha256}.json"
    (candidate / planner.RECEIPT_NAME / forged_name).write_bytes(forged_body)
    locator["receipt_name"] = forged_name
    locator["receipt_sha256"] = forged_sha256
    locator["semantic_sha256"] = receipt["semantic_sha256"]
    locator_path.write_bytes(planner.canonical_json(locator))
    recovered = _run(built, ScriptedTransport(pages))
    assert recovered["exit_code"] == planner.EXIT_BLOCKED
    assert "byte claims" in recovered["message"]


@pytest.mark.parametrize("kind", ["malformed", "symlink", "directory"])
def test_locator_malformed_or_unsafe_leaf_fails_closed(tmp_path: Path, kind: str) -> None:
    built = build_store(tmp_path)
    candidate = built["paths"].candidate_root
    candidate.mkdir()
    locator = candidate / planner.LOCATOR_NAME
    if kind == "malformed":
        locator.write_bytes(b"{}\n")
    elif kind == "symlink":
        target = tmp_path / "foreign-locator"
        target.write_bytes(b"{}\n")
        os.symlink(target, locator)
    else:
        locator.mkdir()
    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    expected = planner.EXIT_BLOCKED if kind == "malformed" else planner.EXIT_UNSAFE
    assert result["exit_code"] == expected


def test_publication_collisions_never_replace_a_winner(tmp_path: Path) -> None:
    manifest_store = build_store(tmp_path / "manifest")
    manifest_pages = _nested_pages(
        manifest_store["metrics"],
        manifest_store["book"],
        manifest_store["sidecar_bodies"],
    )

    def collide_manifest() -> None:
        private = (
            manifest_store["paths"].candidate_root
            / planner.TMP_NAME
            / ".partial-manifest.json.gz"
        )
        digest = hashlib.sha256(private.read_bytes()).hexdigest()
        winner = (
            manifest_store["paths"].candidate_root
            / planner.MANIFEST_NAME
            / f"{digest}.json.gz"
        )
        winner.write_bytes(b"wrong-winner")

    manifest_result = _run(
        manifest_store,
        ScriptedTransport(manifest_pages),
        interrupt_after_private_manifest=collide_manifest,
    )
    assert manifest_result["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    resume = _run(manifest_store, ScriptedTransport(manifest_pages))
    assert resume["exit_code"] == planner.EXIT_BLOCKED
    locator_store = build_store(tmp_path / "locator")
    locator_pages = _nested_pages(
        locator_store["metrics"], locator_store["book"], locator_store["sidecar_bodies"]
    )

    def collide_locator() -> None:
        (locator_store["paths"].candidate_root / planner.LOCATOR_NAME).write_bytes(b"{}\n")

    locator_result = _run(
        locator_store,
        ScriptedTransport(locator_pages),
        before_locator_commit=collide_locator,
    )
    assert locator_result["exit_code"] == planner.EXIT_BLOCKED
    assert (locator_store["paths"].candidate_root / planner.LOCATOR_NAME).read_bytes() == b"{}\n"


@pytest.mark.parametrize("leaf_kind", ["symlink", "directory"])
def test_unsafe_named_publication_winner_fails_closed(
    tmp_path: Path, leaf_kind: str
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])

    def install_unsafe_lineage_winner() -> None:
        checkpoint = json.loads(
            (built["paths"].candidate_root / planner.CHECKPOINT_NAME).read_text(
                encoding="utf-8"
            )
        )
        body = planner.canonical_json(planner._lineage_document(checkpoint))
        name = f"{planner.sha256_bytes(body)}.json"
        winner = built["paths"].candidate_root / planner.LINEAGE_NAME / name
        if leaf_kind == "symlink":
            target = tmp_path / "foreign-lineage"
            target.write_bytes(body)
            os.symlink(target, winner)
        else:
            winner.mkdir()

    partial = _run(
        built,
        ScriptedTransport(pages),
        interrupt_after_manifest_publish=install_unsafe_lineage_winner,
    )
    assert partial["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    resumed = _run(built, ScriptedTransport(pages))
    assert resumed["exit_code"] == planner.EXIT_UNSAFE
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


def test_tampered_page_and_orphan_checkpoint_refused(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"], metrics_pages=2)
    first = _run(built, ScriptedTransport(pages), interrupt_after_pages=1)
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    page_files = list((built["paths"].candidate_root / planner.PAGES_NAME).glob("*/*"))
    page_files[0].write_bytes(b"<not-the-original/>")
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED


@pytest.mark.parametrize(
    "mutation",
    [
        lambda checkpoint: checkpoint["generation"].__setitem__("state_sha256", "0" * 64),
        lambda checkpoint: checkpoint.__setitem__("pending_identity_sha256", "0" * 64),
        lambda checkpoint: checkpoint["code_identity"].__setitem__(
            "planner_source_sha256", "0" * 64
        ),
        lambda checkpoint: checkpoint["passes"]["pass_1"].__setitem__(
            "pass_id", "pass_2"
        ),
        lambda checkpoint: checkpoint["passes"]["pass_1"].__setitem__(
            "listing_complete", True
        ),
        lambda checkpoint: checkpoint["passes"]["pass_1"].__setitem__("graph", "bad"),
        lambda checkpoint: checkpoint["passes"]["pass_1"].__setitem__(
            "published_pages", True
        ),
    ],
)
def test_checkpoint_state_completion_and_types_fail_closed(
    tmp_path: Path, mutation: Any
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    first = _run(built, ScriptedTransport(pages), interrupt_after_pages=1)
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    _rewrite_checkpoint(built, mutation)
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED


def test_checkpoint_reordered_reachable_graph_is_refused(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    first = _run(built, ScriptedTransport(pages), interrupt_after_pages=2)
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL

    def reverse_graph(checkpoint: dict[str, Any]) -> None:
        checkpoint["passes"]["pass_1"]["graph"].reverse()

    _rewrite_checkpoint(built, reverse_graph)
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "reordered" in result["message"] or "unreachable" in result["message"]


def test_checkpoint_child_and_pagination_edges_are_reparsed_from_page_bytes(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    first = _run(built, ScriptedTransport(pages), interrupt_after_pages=1)
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL

    def forge_edge(checkpoint: dict[str, Any]) -> None:
        state = checkpoint["passes"]["pass_1"]
        key = state["graph"][0]
        state["pages"][key]["child_prefixes"] = []

    _rewrite_checkpoint(built, forge_edge)
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "child-prefix" in result["message"]


@pytest.mark.parametrize(
    ("constant", "label"),
    [
        ("CHECKPOINT_CEILING_BYTES", "checkpoint"),
        ("LINEAGE_CEILING_BYTES", "lineage"),
    ],
)
def test_checkpoint_and_lineage_write_ceilings_precede_locator(
    tmp_path: Path, monkeypatch: Any, constant: str, label: str
) -> None:
    built = build_store(tmp_path)
    monkeypatch.setattr(planner, constant, 1)
    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert label in result["message"]
    assert "ceiling" in result["message"]
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


def test_immutable_sqlite_uses_one_explicit_read_transaction(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    observed: dict[str, Any] = {}

    def inspect_transaction(uri: str, conn: sqlite3.Connection) -> None:
        observed["uri"] = uri
        observed["in_transaction"] = conn.in_transaction
        observed["query_only"] = int(conn.execute("PRAGMA query_only").fetchone()[0])
        try:
            conn.execute("BEGIN")
        except sqlite3.OperationalError as exc:
            observed["second_begin"] = str(exc)

    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
        after_sqlite_open=inspect_transaction,
    )
    assert result["exit_code"] == planner.EXIT_COMPLETE
    assert "mode=ro" in observed["uri"] and "immutable=1" in observed["uri"]
    assert observed["in_transaction"] is True
    assert observed["query_only"] == 1
    assert "within a transaction" in observed["second_begin"]


def test_sqlite_snapshot_read_precedes_the_injectable_hook(
    tmp_path: Path, monkeypatch: Any
) -> None:
    built = build_store(tmp_path)
    events: list[str] = []
    original_connect = sqlite3.connect

    class TracedConnection(sqlite3.Connection):
        def execute(self, sql: str, parameters: Any = ()) -> sqlite3.Cursor:
            events.append(sql)
            return super().execute(sql, parameters)

    def traced_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        kwargs["factory"] = TracedConnection
        return original_connect(*args, **kwargs)

    monkeypatch.setattr(planner.sqlite3, "connect", traced_connect)
    fd = os.open(str(built["gate2"] / planner.SQLITE_NAME), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        conn = planner._open_sqlite_immutable(
            fd,
            planner.PlannerHooks(
                after_sqlite_open=lambda _uri, _conn: events.append("after_sqlite_open")
            ),
        )
        conn.close()
    finally:
        os.close(fd)
    hook_index = events.index("after_sqlite_open")
    snapshot_index = next(
        index for index, sql in enumerate(events) if "FROM sqlite_schema" in sql
    )
    assert snapshot_index < hook_index


def test_sqlite_leaf_snapshot_binds_opened_and_named_identity(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    swapped = False

    def swap_after_open(name: str, _fd: int) -> None:
        nonlocal swapped
        if swapped or name != planner.SQLITE_NAME:
            return
        swapped = True
        state = built["gate2"] / planner.SQLITE_NAME
        displaced = built["gate2"] / "state.sqlite.displaced"
        state.rename(displaced)
        shutil.copyfile(displaced, state)

    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
        after_sqlite_leaf_open=swap_after_open,
    )
    assert result["exit_code"] == planner.EXIT_UNSAFE
    assert "identity changed" in result["message"]
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE VIEW unexpected_schema_view AS SELECT * FROM terminal_gap",
        "CREATE TRIGGER unexpected_schema_trigger AFTER INSERT ON terminal_gap "
        "BEGIN SELECT 1; END",
    ],
)
def test_unexpected_sqlite_views_and_triggers_are_rejected(
    tmp_path: Path, statement: str
) -> None:
    built = build_store(tmp_path, wal_mode=False)
    _mutate_state(built, statement)
    result = _run(
        _without_physical_pins(built),
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "schema object" in result["message"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("family", planner.FAMILY_BOOK_TICKER),
        ("symbol", "NOT-BTCUSDT"),
        ("economic_interval", "2024-01-02"),
        ("retained", True),
    ],
)
def test_pending_payload_requires_exact_canonical_facts(
    tmp_path: Path, field: str, value: Any
) -> None:
    built = build_store(tmp_path, wal_mode=False)
    payload = json.loads(
        _payload(
            METRICS_A,
            family=planner.FAMILY_METRICS,
            symbol="BTCUSDT",
            listed_bytes=100,
        )
    )
    payload["payload"][field] = value
    _mutate_state(
        built,
        "UPDATE plan_entry SET payload_json=? WHERE provider=? AND identity=?",
        (
            planner.compact_json(payload).decode("utf-8"),
            planner.PROVIDER_BINANCE,
            METRICS_A,
        ),
    )
    result = _run(
        _without_physical_pins(built),
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED


@pytest.mark.parametrize(
    ("identity", "family", "specific_field", "specific_value"),
    [
        (METRICS_A, planner.FAMILY_METRICS, "consumable", False),
        (BOOK_A, planner.FAMILY_BOOK_TICKER, "etag", "zip"),
    ],
)
def test_pending_payload_accepts_exact_production_family_shape(
    identity: str,
    family: str,
    specific_field: str,
    specific_value: Any,
) -> None:
    envelope, body = planner._payload_envelope(
        _payload(identity, family=family, symbol="BTCUSDT", listed_bytes=100)
    )
    assert set(envelope) == {"identity", "kind", "payload", "provider"}
    assert set(body) == {
        "economic_interval",
        "family",
        "key",
        "listed_bytes",
        "retained",
        "sidecar_key",
        "sidecar_url",
        "symbol",
        "url",
        specific_field,
    }
    assert body[specific_field] == specific_value
    assert type(body[specific_field]) is type(specific_value)


@pytest.mark.parametrize(
    ("identity", "family", "refusal"),
    [
        (METRICS_A, planner.FAMILY_METRICS, "missing"),
        (METRICS_A, planner.FAMILY_METRICS, "cross_family"),
        (METRICS_A, planner.FAMILY_METRICS, "additional"),
        (METRICS_A, planner.FAMILY_METRICS, "wrong_type"),
        (BOOK_A, planner.FAMILY_BOOK_TICKER, "missing"),
        (BOOK_A, planner.FAMILY_BOOK_TICKER, "cross_family"),
        (BOOK_A, planner.FAMILY_BOOK_TICKER, "additional"),
        (BOOK_A, planner.FAMILY_BOOK_TICKER, "wrong_type"),
    ],
)
def test_pending_payload_rejects_invalid_family_specific_shape(
    identity: str, family: str, refusal: str
) -> None:
    document = json.loads(
        _payload(identity, family=family, symbol="BTCUSDT", listed_bytes=100)
    )
    body = document["payload"]
    specific_field = "consumable" if family == planner.FAMILY_METRICS else "etag"
    cross_field = "etag" if family == planner.FAMILY_METRICS else "consumable"
    cross_value: Any = "zip" if cross_field == "etag" else False
    if refusal == "missing":
        del body[specific_field]
    elif refusal == "cross_family":
        del body[specific_field]
        body[cross_field] = cross_value
    elif refusal == "additional":
        body["unexpected"] = "value"
    else:
        body[specific_field] = 1 if specific_field == "consumable" else False

    with pytest.raises(planner.BlockedCandidateError):
        planner._payload_envelope(planner.compact_json(document).decode("utf-8"))


@pytest.mark.parametrize(
    ("identity", "family"),
    [
        (METRICS_A, planner.FAMILY_BOOK_TICKER),
        (
            "data/futures/um/daily/metrics/BTCUSDT/"
            "ETHUSDT-metrics-2024-01-01.zip",
            planner.FAMILY_METRICS,
        ),
        (
            "data/futures/um/daily/metrics/BTCUSDT/"
            "BTCUSDT-metrics-2024-02-30.zip",
            planner.FAMILY_METRICS,
        ),
    ],
)
def test_pending_key_grammar_binds_family_symbol_and_date(
    identity: str, family: str
) -> None:
    with pytest.raises(planner.BlockedCandidateError):
        planner._pending_key_identity(identity, family)
    assert planner._pending_key_identity(METRICS_A, planner.FAMILY_METRICS) == (
        "BTCUSDT",
        "2024-01-01",
    )


def test_pending_sidecar_path_must_name_the_held_content_leaf(tmp_path: Path) -> None:
    built = build_store(tmp_path, wal_mode=False)
    _mutate_state(
        built,
        "UPDATE sidecar_fact SET sidecar_path=? WHERE provider=? AND identity=?",
        (str(tmp_path / "lookalike-sidecar"), planner.PROVIDER_BINANCE, METRICS_A),
    )
    result = _run(
        _without_physical_pins(built),
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "canonical" in result["message"]


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE coinalyze_charge SET identity='inventory' WHERE seq=1",
        "UPDATE charge_transition SET status=CASE seq WHEN 1 THEN 'published' "
        "WHEN 2 THEN 'reserved' ELSE status END WHERE seq IN (1, 2)",
        "UPDATE terminal_gap SET kind='untyped-gap' WHERE provider='coinalyze'",
    ],
)
def test_coinalyze_requires_per_identity_charge_chain_and_typed_gap(
    tmp_path: Path, statement: str
) -> None:
    built = build_store(tmp_path, wal_mode=False)
    _mutate_state(built, statement)
    result = _run(
        _without_physical_pins(built),
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED


@pytest.mark.parametrize("leaf_kind", ["symlink", "directory"])
def test_unsafe_existing_checkpoint_leaf_is_not_absence(
    tmp_path: Path, leaf_kind: str
) -> None:
    built = build_store(tmp_path)
    candidate = built["paths"].candidate_root
    candidate.mkdir()
    leaf = candidate / planner.CHECKPOINT_NAME
    if leaf_kind == "symlink":
        target = tmp_path / "target-checkpoint"
        target.write_text("{}", encoding="utf-8")
        os.symlink(target, leaf)
    else:
        leaf.mkdir()
    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_UNSAFE


def test_same_continuation_token_is_allowed_in_distinct_prefix_chains(
    tmp_path: Path,
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    for family_prefix in planner.FAMILY_PREFIXES:
        original = pages[(family_prefix, None)]
        root = planner.parse_s3_list_bucket(
            original,
            request=planner.listing_request_identity(
                endpoint=planner.VISION_S3_ENDPOINT,
                prefix=family_prefix,
                delimiter="/",
                continuation_token=None,
            ),
        )
        pages[(family_prefix, None)] = planner.write_s3_list_bucket(
            prefix=family_prefix,
            delimiter="/",
            prefixes=root[0],
            truncated=True,
            continuation="shared-token",
        )
        pages[(family_prefix, "shared-token")] = planner.write_s3_list_bucket(
            prefix=family_prefix,
            delimiter="/",
            continuation_token="shared-token",
        )
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_COMPLETE


def test_live_page_and_prefix_ceilings_apply_before_fetch_or_mutation(
    tmp_path: Path, monkeypatch: Any
) -> None:
    page_store = build_store(tmp_path / "page")
    page_pages = _nested_pages(
        page_store["metrics"], page_store["book"], page_store["sidecar_bodies"]
    )
    monkeypatch.setattr(planner, "PAGE_COUNT_CEILING", 1)
    page_result = _run(page_store, ScriptedTransport(page_pages))
    assert page_result["exit_code"] == planner.EXIT_BLOCKED
    assert "page count" in page_result["message"]
    monkeypatch.setattr(planner, "PAGE_COUNT_CEILING", 100_000)
    prefix_store = build_store(tmp_path / "prefix")
    prefix_pages = _nested_pages(
        prefix_store["metrics"], prefix_store["book"], prefix_store["sidecar_bodies"]
    )
    monkeypatch.setattr(planner, "PREFIX_CEILING", len(planner.FAMILY_PREFIXES))
    prefix_result = _run(prefix_store, ScriptedTransport(prefix_pages))
    assert prefix_result["exit_code"] == planner.EXIT_BLOCKED
    assert "prefix count" in prefix_result["message"]
    monkeypatch.setattr(planner, "PREFIX_CEILING", 20_000)
    other = build_store(tmp_path / "orphan")
    first = _run(
        other,
        ScriptedTransport(_nested_pages(other["metrics"], other["book"], other["sidecar_bodies"], metrics_pages=2)),
        interrupt_after_pages=1,
    )
    assert first["exit_code"] == planner.EXIT_RESUMABLE_PARTIAL
    checkpoint = json.loads((other["paths"].candidate_root / planner.CHECKPOINT_NAME).read_text())
    checkpoint["passes"]["pass_1"]["pages"]["0" * 64] = {}
    (other["paths"].candidate_root / planner.CHECKPOINT_NAME).write_bytes(planner.canonical_json(checkpoint))
    result = _run(
        other,
        ScriptedTransport(_nested_pages(other["metrics"], other["book"], other["sidecar_bodies"], metrics_pages=2)),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED


def test_echo_mismatch_redirect_and_token_cycle(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    parent = _parent(METRICS_A)
    bad = planner.write_s3_list_bucket(
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        prefixes=[parent],
    )
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    pages[(parent, None)] = bad
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED
    redirect = _run(
        build_store(tmp_path / "redir"),
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"]),
            redirect=True,
        ),
    )
    assert redirect["exit_code"] == planner.EXIT_BLOCKED
    cyclic = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    cyclic[(planner.FAMILY_PREFIXES[0], None)] = planner.write_s3_list_bucket(
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        prefixes=[parent],
        truncated=True,
        continuation="loop",
    )
    cyclic[(planner.FAMILY_PREFIXES[0], "loop")] = planner.write_s3_list_bucket(
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        prefixes=[parent],
        truncated=True,
        continuation="loop",
        continuation_token="loop",
    )
    cycle_store = build_store(tmp_path / "cycle")
    cycled = _run(cycle_store, ScriptedTransport(cyclic))
    assert cycled["exit_code"] == planner.EXIT_BLOCKED


def test_current_listing_size_change_and_checksum_etag_mismatch(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    changed = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"], current={METRICS_A: 175})
        ),
    )
    assert changed["exit_code"] == planner.EXIT_COMPLETE
    assert changed["receipt"]["bytes"]["metrics_delta_bytes"] == 75
    book_change = build_store(tmp_path / "book")
    blocked_book = _run(
        book_change,
        ScriptedTransport(
            _nested_pages(
                book_change["metrics"],
                book_change["book"],
                book_change["sidecar_bodies"],
                current={BOOK_A: 9_000_000},
            )
        ),
    )
    assert blocked_book["exit_code"] == planner.EXIT_BLOCKED
    etag = build_store(tmp_path / "etag")
    pages = _nested_pages(etag["metrics"], etag["book"], etag["sidecar_bodies"])
    parent = _parent(METRICS_A)
    pages[(parent, None)] = planner.write_s3_list_bucket(
        prefix=parent,
        delimiter="/",
        objects=[
            planner.ListingObject(key=METRICS_A, size=100, etag="zip"),
            planner.ListingObject(key=f"{METRICS_A}.CHECKSUM", size=66, etag="deadbeef"),
        ],
    )
    mismatch = _run(etag, ScriptedTransport(pages))
    assert mismatch["exit_code"] == planner.EXIT_BLOCKED
    assert "ETag" in mismatch["message"] or "etag" in mismatch["message"].lower() or "mismatch" in mismatch["message"]


def test_two_independently_retrieved_passes_detect_pending_drift(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    parent = _parent(METRICS_A)
    objects: list[planner.ListingObject] = []
    for identity, old_size, _checksum, _message in built["metrics"]:
        if _parent(identity) != parent:
            continue
        body = built["sidecar_bodies"][identity]
        objects.extend(
            (
                planner.ListingObject(
                    key=identity,
                    size=old_size + (1 if identity == METRICS_A else 0),
                    etag="zip",
                ),
                planner.ListingObject(
                    key=f"{identity}.CHECKSUM",
                    size=len(body),
                    etag=planner.md5_hex(body),
                ),
            )
        )
    transport = SecondPassDriftTransport(
        pages,
        drift_request=(parent, None),
        drift_body=planner.write_s3_list_bucket(
            prefix=parent, delimiter="/", objects=objects
        ),
    )
    result = _run(built, transport)
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "independent passes" in result["message"]
    assert transport.request_counts[(parent, None)] == 2


def test_independent_passes_detect_checksum_version_drift(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    parent = _parent(METRICS_A)
    objects: list[planner.ListingObject] = []
    for identity, old_size, _checksum, _message in built["metrics"]:
        if _parent(identity) != parent:
            continue
        body = built["sidecar_bodies"][identity]
        objects.extend(
            (
                planner.ListingObject(key=identity, size=old_size, etag="zip"),
                planner.ListingObject(
                    key=f"{identity}.CHECKSUM",
                    size=len(body),
                    etag=("f" * 32 if identity == METRICS_A else planner.md5_hex(body)),
                ),
            )
        )
    result = _run(
        built,
        SecondPassDriftTransport(
            pages,
            drift_request=(parent, None),
            drift_body=planner.write_s3_list_bucket(
                prefix=parent, delimiter="/", objects=objects
            ),
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "independent passes" in result["message"]


@pytest.mark.parametrize("etag", [None, "abcd-2"])
def test_checksum_sidecar_requires_single_part_etag(
    tmp_path: Path, etag: str | None
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    parent = _parent(METRICS_A)
    body = built["sidecar_bodies"][METRICS_A]
    pages[(parent, None)] = planner.write_s3_list_bucket(
        prefix=parent,
        delimiter="/",
        objects=[
            planner.ListingObject(key=METRICS_A, size=100, etag="zip"),
            planner.ListingObject(
                key=f"{METRICS_A}.CHECKSUM", size=len(body), etag=etag
            ),
        ],
    )
    result = _run(built, ScriptedTransport(pages))
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "single-part" in result["message"] or "missing" in result["message"]


def test_exact_final_url_and_injected_response_ceiling(tmp_path: Path, monkeypatch: Any) -> None:
    built = build_store(tmp_path / "url")
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    changed_query = _run(
        built, ResponseOverrideTransport(pages, final_url_suffix="&changed=1")
    )
    assert changed_query["exit_code"] == planner.EXIT_BLOCKED
    assert "final URL" in changed_query["message"]
    status = build_store(tmp_path / "status")
    bad_status = _run(
        status,
        ResponseOverrideTransport(
            _nested_pages(status["metrics"], status["book"], status["sidecar_bodies"]),
            status_code=206,
        ),
    )
    assert bad_status["exit_code"] == planner.EXIT_BLOCKED
    assert "status" in bad_status["message"]
    length = build_store(tmp_path / "length")
    bad_length = _run(
        length,
        ResponseOverrideTransport(
            _nested_pages(length["metrics"], length["book"], length["sidecar_bodies"]),
            content_length_adjustment=1,
        ),
    )
    assert bad_length["exit_code"] == planner.EXIT_BLOCKED
    assert "Content-Length" in bad_length["message"]
    ceiling = build_store(tmp_path / "ceiling")
    monkeypatch.setattr(planner, "LIST_PAGE_CEILING_BYTES", 1024)
    oversized = _run(
        ceiling,
        ResponseOverrideTransport(
            _nested_pages(
                ceiling["metrics"], ceiling["book"], ceiling["sidecar_bodies"]
            ),
            oversized=True,
        ),
    )
    assert oversized["exit_code"] == planner.EXIT_BLOCKED
    assert "byte ceiling" in oversized["message"]


@pytest.mark.parametrize(
    "control",
    ["", "<IsTruncated>FALSE</IsTruncated>", "<IsTruncated>maybe</IsTruncated>"],
)
def test_xml_requires_one_exact_is_truncated_control(control: str) -> None:
    request = planner.listing_request_identity(
        endpoint=planner.VISION_S3_ENDPOINT,
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        continuation_token=None,
    )
    xml = (
        "<ListBucketResult>"
        f"<Prefix>{planner.FAMILY_PREFIXES[0]}</Prefix><Delimiter>/</Delimiter>"
        f"{control}</ListBucketResult>"
    )
    with pytest.raises(planner.BlockedCandidateError):
        planner.parse_s3_list_bucket(xml, request=request)


@pytest.mark.parametrize(
    "controls",
    [
        "<Delimiter>/</Delimiter>",
        f"<Prefix>{planner.FAMILY_PREFIXES[0]}</Prefix>",
        f"<Prefix>{planner.FAMILY_PREFIXES[0]}</Prefix>"
        f"<Prefix>{planner.FAMILY_PREFIXES[0]}</Prefix><Delimiter>/</Delimiter>",
    ],
)
def test_xml_requires_exact_unique_prefix_and_delimiter_controls(controls: str) -> None:
    request = planner.listing_request_identity(
        endpoint=planner.VISION_S3_ENDPOINT,
        prefix=planner.FAMILY_PREFIXES[0],
        delimiter="/",
        continuation_token=None,
    )
    xml = f"<ListBucketResult>{controls}<IsTruncated>false</IsTruncated></ListBucketResult>"
    with pytest.raises(planner.BlockedCandidateError):
        planner.parse_s3_list_bucket(xml, request=request)


def test_candidate_root_layout_refusals(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    inside = planner.PlannerPaths(
        repository=REPOSITORY,
        store_root=built["store"],
        gate2_root=built["gate2"],
        candidate_root=built["gate2"] / "inside",
        planner_source_path=REPOSITORY / planner.SOURCE_RELATIVE,
        planner_cli_path=REPOSITORY / planner.CLI_RELATIVE,
        acquisition_source_path=REPOSITORY / planner.ACQUISITION_SOURCE_RELATIVE,
        acquisition_cli_path=REPOSITORY / planner.ACQUISITION_CLI_RELATIVE,
    )
    assert planner.plan_revision_candidate(inside, built["pins"])["exit_code"] == planner.EXIT_UNSAFE
    ancestor = planner.PlannerPaths(
        repository=REPOSITORY,
        store_root=built["store"],
        gate2_root=built["gate2"],
        candidate_root=built["store"],
        planner_source_path=REPOSITORY / planner.SOURCE_RELATIVE,
        planner_cli_path=REPOSITORY / planner.CLI_RELATIVE,
        acquisition_source_path=REPOSITORY / planner.ACQUISITION_SOURCE_RELATIVE,
        acquisition_cli_path=REPOSITORY / planner.ACQUISITION_CLI_RELATIVE,
    )
    assert planner.plan_revision_candidate(ancestor, built["pins"])["exit_code"] == planner.EXIT_UNSAFE
    link = built["store"] / "linked_candidate"
    os.symlink(tmp_path / "target", link)
    (tmp_path / "target").mkdir()
    linked = planner.PlannerPaths(
        repository=REPOSITORY,
        store_root=built["store"],
        gate2_root=built["gate2"],
        candidate_root=link,
        planner_source_path=REPOSITORY / planner.SOURCE_RELATIVE,
        planner_cli_path=REPOSITORY / planner.CLI_RELATIVE,
        acquisition_source_path=REPOSITORY / planner.ACQUISITION_SOURCE_RELATIVE,
        acquisition_cli_path=REPOSITORY / planner.ACQUISITION_CLI_RELATIVE,
    )
    assert planner.plan_revision_candidate(linked, built["pins"])["exit_code"] == planner.EXIT_UNSAFE


@pytest.mark.parametrize("boundary", ["generation", "content", "candidate"])
def test_held_root_and_nested_inode_substitution_is_refused(
    tmp_path: Path, boundary: str
) -> None:
    built = build_store(tmp_path)

    def substitute(_fd: int) -> None:
        if boundary == "generation":
            source = built["gate2"]
            displaced = built["store"] / "displaced-gate2"
        elif boundary == "content":
            source = built["content"]
            displaced = built["gate2"] / "displaced-content"
        else:
            source = built["paths"].candidate_root
            displaced = built["store"] / "displaced-candidate"
        source.rename(displaced)
        source.mkdir()

    hook_name = {
        "generation": "after_generation_open",
        "content": "after_content_open",
        "candidate": "after_candidate_open",
    }[boundary]
    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
        **{hook_name: substitute},
    )
    assert result["exit_code"] == planner.EXIT_UNSAFE
    assert "held directory" in result["message"]


def test_pre_locator_same_device_candidate_substitution_is_refused(tmp_path: Path) -> None:
    built = build_store(tmp_path)

    def substitute() -> None:
        candidate = built["paths"].candidate_root
        candidate.rename(built["store"] / "displaced-at-commit")
        candidate.mkdir()

    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
        before_locator_commit=substitute,
    )
    assert result["exit_code"] == planner.EXIT_UNSAFE
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


@pytest.mark.parametrize(
    "target",
    [
        planner.TMP_NAME,
        planner.PAGES_NAME,
        planner.MANIFEST_NAME,
        planner.RECEIPT_NAME,
        planner.LINEAGE_NAME,
        "code",
        "sqlite",
    ],
)
def test_final_locator_boundary_rebinds_nested_code_and_sqlite_authority(
    tmp_path: Path, target: str
) -> None:
    built = _with_copied_authority_repository(
        build_store(tmp_path / "store"), tmp_path / "authority-repository"
    )

    def replace_boundary_authority() -> None:
        if target == "code":
            source = built["paths"].repository / planner.SOURCE_RELATIVE
            source.write_bytes(source.read_bytes() + b"\n# injected boundary mutation\n")
            return
        if target == "sqlite":
            source = built["gate2"] / planner.SQLITE_NAME
            displaced = built["gate2"] / "state.sqlite.at-locator-boundary"
            source.rename(displaced)
            shutil.copyfile(displaced, source)
            return
        source = built["paths"].candidate_root / target
        displaced = built["paths"].candidate_root / f"displaced-{target}"
        source.rename(displaced)
        source.mkdir()

    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
        before_locator_commit=replace_boundary_authority,
    )
    assert result["exit_code"] in {planner.EXIT_BLOCKED, planner.EXIT_UNSAFE}
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


@pytest.mark.parametrize(
    "target",
    [
        "nested_directory",
        "locator",
        "immutable_asset",
        "checkpoint",
        "page",
        "code",
        "sqlite",
    ],
)
def test_completed_recovery_final_boundary_rejects_every_substitution(
    tmp_path: Path, target: str
) -> None:
    built = _with_copied_authority_repository(
        build_store(tmp_path / "store"), tmp_path / "authority-repository"
    )
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    complete = _run(built, ScriptedTransport(pages))
    assert complete["exit_code"] == planner.EXIT_COMPLETE
    candidate = built["paths"].candidate_root
    locator = json.loads((candidate / planner.LOCATOR_NAME).read_text(encoding="utf-8"))
    checkpoint = json.loads(
        (candidate / planner.CHECKPOINT_NAME).read_text(encoding="utf-8")
    )

    def replace_regular(path: Path, suffix: str) -> None:
        displaced = path.with_name(f"{path.name}.{suffix}")
        path.rename(displaced)
        shutil.copyfile(displaced, path)

    def substitute() -> None:
        if target == "nested_directory":
            source = candidate / planner.MANIFEST_NAME
            source.rename(candidate / "manifest.at-recovery-boundary")
            source.mkdir()
        elif target == "locator":
            replace_regular(candidate / planner.LOCATOR_NAME, "at-recovery-boundary")
        elif target == "immutable_asset":
            replace_regular(
                candidate / planner.RECEIPT_NAME / locator["receipt_name"],
                "at-recovery-boundary",
            )
        elif target == "checkpoint":
            replace_regular(
                candidate / planner.CHECKPOINT_NAME, "at-recovery-boundary"
            )
        elif target == "page":
            request_key = checkpoint["passes"]["pass_1"]["graph"][0]
            digest = checkpoint["passes"]["pass_1"]["pages"][request_key][
                "response_sha256"
            ]
            replace_regular(
                candidate / planner.PAGES_NAME / digest[:2] / digest,
                "at-recovery-boundary",
            )
        elif target == "code":
            source = built["paths"].repository / planner.SOURCE_RELATIVE
            source.write_bytes(source.read_bytes() + b"\n# recovery-boundary mutation\n")
        else:
            replace_regular(
                built["gate2"] / planner.SQLITE_NAME, "at-recovery-boundary"
            )

    recovered = _run(
        built,
        ScriptedTransport(pages),
        before_recovery_return=substitute,
    )
    assert recovered["exit_code"] in {planner.EXIT_BLOCKED, planner.EXIT_UNSAFE}
    assert recovered["stop_reason"] != "complete"


@pytest.mark.parametrize(
    "constant",
    [
        "MANIFEST_COMPRESSED_CEILING_BYTES",
        "MANIFEST_DECOMPRESSED_CEILING_BYTES",
        "MANIFEST_ROW_COUNT_CEILING",
    ],
)
def test_completed_recovery_enforces_manifest_stream_ceilings(
    tmp_path: Path, monkeypatch: Any, constant: str
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    complete = _run(built, ScriptedTransport(pages))
    assert complete["exit_code"] == planner.EXIT_COMPLETE
    monkeypatch.setattr(planner, constant, 1)
    recovered = _run(built, ScriptedTransport(pages))
    assert recovered["exit_code"] == planner.EXIT_BLOCKED
    assert "manifest" in recovered["message"]
    assert "ceiling" in recovered["message"]


def test_completed_recovery_refuses_an_overlong_compressed_jsonl_row(
    tmp_path: Path, monkeypatch: Any
) -> None:
    built = build_store(tmp_path)
    pages = _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
    complete = _run(built, ScriptedTransport(pages))
    assert complete["exit_code"] == planner.EXIT_COMPLETE
    monkeypatch.setattr(planner, "MANIFEST_ROW_CEILING_BYTES", 1)
    recovered = _run(built, ScriptedTransport(pages))
    assert recovered["exit_code"] == planner.EXIT_BLOCKED
    assert recovered["message"] == "manifest row exceeds the per-row byte ceiling"


@pytest.mark.parametrize(
    "constant",
    [
        "MANIFEST_COMPRESSED_CEILING_BYTES",
        "MANIFEST_ROW_CEILING_BYTES",
        "MANIFEST_DECOMPRESSED_CEILING_BYTES",
        "MANIFEST_ROW_COUNT_CEILING",
    ],
)
def test_manifest_creation_enforces_every_stream_ceiling_before_locator(
    tmp_path: Path, monkeypatch: Any, constant: str
) -> None:
    built = build_store(tmp_path)
    monkeypatch.setattr(planner, constant, 1)
    result = _run(
        built,
        ScriptedTransport(
            _nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])
        ),
    )
    assert result["exit_code"] == planner.EXIT_BLOCKED
    assert "manifest" in result["message"]
    assert "ceiling" in result["message"]
    assert not (built["paths"].candidate_root / planner.LOCATOR_NAME).exists()


def test_cli_has_no_caller_filter_and_uses_fixed_layout() -> None:
    cli = _load_cli()
    parser = cli.build_parser()
    flags = {action.dest for action in parser._actions}
    assert flags.isdisjoint({"store_root", "candidate_root", "family", "symbol", "key", "date", "secret"})


def test_cli_complete_and_blocker(tmp_path: Path) -> None:
    cli = _load_cli()
    built = build_store(tmp_path)
    stdout = io.BytesIO()

    class _Out:
        def __init__(self) -> None:
            self.buffer = stdout

        def write(self, _payload: str) -> int:
            return 0

    code = cli.main(
        [],
        pins=built["pins"],
        paths=built["paths"],
        transport=ScriptedTransport(_nested_pages(built["metrics"], built["book"], built["sidecar_bodies"])),
        stdout=_Out(),
        stderr=io.StringIO(),
    )
    assert code == planner.EXIT_COMPLETE
    receipt = json.loads(stdout.getvalue().decode("utf-8"))
    assert receipt["authorization"]["candidate_accepted"] is False
    blocked = cli.main(
        [],
        pins=built["pins"],
        paths=planner.production_paths(tmp_path / "missing-repo"),
        stdout=_Out(),
        stderr=io.StringIO(),
    )
    assert blocked in {planner.EXIT_BLOCKED, planner.EXIT_UNSAFE}


def test_fixture_sidecar_parses() -> None:
    body = (FIXTURE_DIR / "sidecar_btc_metrics.CHECKSUM").read_bytes()
    digest = planner.parse_sidecar(body, basename="BTCUSDT-metrics-2024-01-01.zip")
    assert digest == "a" * 64


def test_nested_fixture_xml_echoes_child_prefix() -> None:
    xml = (FIXTURE_DIR / "listing_metrics_page.xml").read_text(encoding="utf-8")
    prefixes, objects, truncated, token = planner.parse_s3_list_bucket(
        xml,
        request=planner.listing_request_identity(
            endpoint=planner.VISION_S3_ENDPOINT,
            prefix="data/futures/um/daily/metrics/BTCUSDT/",
            delimiter="/",
            continuation_token=None,
        ),
    )
    assert prefixes == []
    assert truncated is False
    assert token is None
    assert objects[0].key.endswith("BTCUSDT-metrics-2024-01-01.zip")


def _metrics_key(index: int) -> str:
    day = (date(2000, 1, 1) + timedelta(days=index)).isoformat()
    return f"data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{day}.zip"


def _book_key(index: int) -> str:
    day = (date(2000, 1, 1) + timedelta(days=index)).isoformat()
    return f"data/futures/um/daily/bookTicker/BTCUSDT/BTCUSDT-bookTicker-{day}.zip"


def _irrel_key(index: int) -> str:
    day = (date(2000, 1, 1) + timedelta(days=index)).isoformat()
    return f"data/futures/um/daily/metrics/IRREL/IRREL-metrics-{day}.zip"


class NestedFormulaTransport:
    def __init__(self, metrics: int, book: int, extra: int, sidecar_md5: Mapping[str, tuple[int, str]]) -> None:
        self.metrics = metrics
        self.book = book
        self.extra = extra
        self.sidecar_md5 = sidecar_md5
        self.urls: list[str] = []

    def fetch(self, url: str, *, max_bytes: int) -> planner.ListingResponse:
        self.urls.append(url)
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        prefix = query["prefix"][0]
        token = query.get("continuation-token", [None])[0]
        if prefix == planner.FAMILY_PREFIXES[0]:
            body = planner.write_s3_list_bucket(
                prefix=prefix,
                delimiter="/",
                prefixes=[
                    "data/futures/um/daily/metrics/BTCUSDT/",
                    "data/futures/um/daily/metrics/IRREL/",
                ],
            )
        elif prefix == planner.FAMILY_PREFIXES[1]:
            body = planner.write_s3_list_bucket(
                prefix=prefix,
                delimiter="/",
                prefixes=["data/futures/um/daily/bookTicker/BTCUSDT/"],
            )
        elif prefix == "data/futures/um/daily/metrics/BTCUSDT/":
            body = self._page(prefix, self.metrics, _metrics_key, 100, token)
        elif prefix == "data/futures/um/daily/metrics/IRREL/":
            body = self._page(prefix, self.extra, _irrel_key, 10, token)
        elif prefix == "data/futures/um/daily/bookTicker/BTCUSDT/":
            body = self._page(prefix, self.book, _book_key, 8_932_817, token)
        else:
            raise planner.BlockedCandidateError("unexpected listing prefix")
        encoded = body.encode("utf-8")
        if len(encoded) > max_bytes:
            raise planner.BlockedCandidateError("listing page exceeded the accepted byte ceiling")
        return planner.ListingResponse(status_code=200, url=url, headers={}, body=encoded)

    def _page(self, prefix: str, total: int, key_fn: Any, size: int, token: str | None) -> str:
        start = 0 if token is None else int(token)
        end = min(start + 250, total)
        objects = []
        for index in range(start, end):
            identity = key_fn(index)
            sidecar_size, etag = self.sidecar_md5[identity]
            objects.append(planner.ListingObject(key=identity, size=size, etag="zip"))
            objects.append(
                planner.ListingObject(key=f"{identity}.CHECKSUM", size=sidecar_size, etag=etag)
            )
        truncated = end < total
        return planner.write_s3_list_bucket(
            prefix=prefix,
            delimiter="/",
            objects=objects,
            truncated=truncated,
            continuation=str(end) if truncated else None,
            continuation_token=token,
        )


def test_production_shaped_51275_nested_without_row_collection(tmp_path: Path) -> None:
    metrics_n = 50_921
    book_n = 354
    extra_n = 400
    store = tmp_path / "data" / "cex002_qualify"
    gate2 = store / "gate2"
    content = gate2 / "content"
    content.mkdir(parents=True)
    (gate2 / planner.LOCK_NAME).write_bytes(b"lock\n")
    sqlite_path = gate2 / planner.SQLITE_NAME
    conn = sqlite3.connect(sqlite_path)
    sidecar_md5: dict[str, tuple[int, str]] = {}
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(planner.SCHEMA_SQL)
        conn.execute(f"PRAGMA application_id={int(planner.STATE_APPLICATION_ID)}")
        conn.execute(f"PRAGMA user_version={int(planner.STATE_USER_VERSION)}")
        device = f"dev:{gate2.stat().st_dev}"
        conn.execute(
            "INSERT INTO authority(id, plan_identity, plan_receipt_sha256, pins_json, "
            "code_json, destination, device, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
            (
                PLAN_ID,
                PLAN_RECEIPT,
                _pins_json(device),
                json.dumps(
                    {
                        "acquisition_cli_sha256": CLI_SHA,
                        "acquisition_source_sha256": SOURCE_SHA,
                        "policy_identity": planner.GENERATION0_POLICY_IDENTITY,
                    },
                    sort_keys=True,
                ),
                planner.FIXED_STORE_ROOT,
                device,
                "2026-08-30T00:00:00+00:00",
            ),
        )
        conn.execute("INSERT INTO coinalyze_ledger(id, charged) VALUES (1, 0)")

        def _batch(family: str, count: int, key_fn: Any, message: str, listed: int, seed: int) -> None:
            start = 0
            while start < count:
                end = min(start + 1000, count)
                plan_rows = []
                sidecar_rows = []
                attempt_rows = []
                for index in range(start, end):
                    identity = key_fn(index)
                    checksum = hashlib.sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()
                    digest, path, size, body = _write_sidecar(
                        content, identity.rsplit("/", 1)[-1], checksum
                    )
                    sidecar_md5[identity] = (size, planner.md5_hex(body))
                    plan_rows.append(
                        (
                            planner.PROVIDER_BINANCE,
                            identity,
                            planner.KIND_BINANCE,
                            _payload(
                                identity,
                                family=family,
                                symbol=identity.split("/")[-2],
                                listed_bytes=listed,
                            ),
                        )
                    )
                    sidecar_rows.append(
                        (planner.PROVIDER_BINANCE, identity, digest, path, size, checksum)
                    )
                    attempt_rows.append(
                        (
                            planner.PROVIDER_BINANCE,
                            identity,
                            "2026-08-31T17:00:00+00:00",
                            "2026-08-31T17:00:01+00:00",
                            planner.RETRY_TERMINAL,
                            200,
                            _fact(identity, message),
                        )
                    )
                conn.executemany(
                    "INSERT INTO plan_entry(provider, identity, kind, payload_json) VALUES (?, ?, ?, ?)",
                    plan_rows,
                )
                conn.executemany(
                    "INSERT INTO sidecar_fact(provider, identity, sidecar_sha256, sidecar_path, "
                    "sidecar_bytes, provider_checksum) VALUES (?, ?, ?, ?, ?, ?)",
                    sidecar_rows,
                )
                conn.executemany(
                    "INSERT INTO attempt(provider, identity, started_at, ended_at, class, "
                    "status_code, redacted_fact_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    attempt_rows,
                )
                start = end

        _batch(planner.FAMILY_METRICS, metrics_n, _metrics_key, planner.MSG_SIZE, 100, 1)
        _batch(planner.FAMILY_BOOK_TICKER, book_n, _book_key, planner.MSG_ZIP, 8_932_817, 2)
        charge_count, transition_count, charged_bytes, charged_points = (
            _insert_coinalyze_closed(conn, supported=569, unsupported=202)
        )
        attempt_hi, completion_hi, sidecar_hi = _insert_run(conn)
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        coverage = _family_coverage(conn)
        plan_rows = int(conn.execute("SELECT COUNT(*) FROM plan_entry").fetchone()[0])
        attempts = int(conn.execute("SELECT COUNT(*) FROM attempt").fetchone()[0])
        completions = int(conn.execute("SELECT COUNT(*) FROM completion").fetchone()[0])
        sidecars = int(conn.execute("SELECT COUNT(*) FROM sidecar_fact").fetchone()[0])
        gaps = int(conn.execute("SELECT COUNT(*) FROM terminal_gap").fetchone()[0])
    finally:
        conn.close()
    wal = gate2 / planner.SQLITE_WAL_NAME
    shm = gate2 / planner.SQLITE_SHM_NAME
    wal_bytes = wal.read_bytes() if wal.exists() else b""
    if not wal.exists():
        wal.write_bytes(b"")
        wal_bytes = b""
    shm_bytes = shm.read_bytes() if shm.exists() else b"\x00" * 32
    if not shm.exists():
        shm.write_bytes(shm_bytes)
    state_bytes = sqlite_path.read_bytes()
    pins = planner.PlannerPins(
        run7_receipt_sha256=RECEIPT7,
        run7_run_id=RUN7,
        expected_plan_rows=plan_rows,
        expected_attempts=attempts,
        expected_completions=completions,
        expected_sidecars=sidecars,
        expected_gaps=gaps,
        expected_runs=1,
        expected_publications=1,
        expected_seals=1,
        expected_charges=charge_count,
        expected_charge_transitions=transition_count,
        expected_pending_metrics=metrics_n,
        expected_pending_book_ticker=book_n,
        expected_attempt_hi=attempt_hi,
        expected_completion_hi=completion_hi,
        expected_sidecar_hi=sidecar_hi,
        expected_charge_hi=charge_count,
        expected_transition_hi=transition_count,
        expected_run_hi=1,
        expected_seal_hi=1,
        expected_charged_bytes=charged_bytes,
        expected_charge_points=charged_points,
        expected_reserved_transitions=charge_count,
        expected_published_transitions=charge_count,
        expected_settled_transitions=charge_count,
        expected_inventory_complete=1,
        expected_liquidation_complete=569,
        expected_state_bytes=len(state_bytes),
        expected_state_sha256=hashlib.sha256(state_bytes).hexdigest(),
        expected_wal_bytes=len(wal_bytes),
        expected_wal_sha256=hashlib.sha256(wal_bytes).hexdigest(),
        expected_shm_bytes=len(shm_bytes),
        expected_shm_sha256=hashlib.sha256(shm_bytes).hexdigest(),
        expected_pending_metrics_bytes=metrics_n * 100,
        expected_pending_book_bytes=book_n * 8_932_817,
        expected_message_counts=((planner.MSG_SIZE, metrics_n), (planner.MSG_ZIP, book_n)),
        expected_family_coverage=coverage,
    )
    paths = planner.default_paths(REPOSITORY, store)
    live = {"pending": 0, "listing": 0}

    def on_pending(count: int) -> None:
        live["pending"] = max(live["pending"], count)

    def on_listing(count: int) -> None:
        live["listing"] = max(live["listing"], count)

    extra_bodies = {}
    for index in range(extra_n):
        identity = _irrel_key(index)
        digest, _path, size, body = _write_sidecar(content, identity.rsplit("/", 1)[-1], "7" * 64)
        extra_bodies[identity] = (size, planner.md5_hex(body))
        sidecar_md5[identity] = (size, planner.md5_hex(body))
        _ = digest
    result = planner.plan_revision_candidate(
        paths,
        pins,
        hooks=planner.PlannerHooks(
            on_live_row_count=on_pending,
            on_listing_live_count=on_listing,
            available_bytes=lambda _fd: 200 * 1024 * 1024 * 1024,
        ),
        transport=NestedFormulaTransport(metrics_n, book_n, extra_n, sidecar_md5),
    )
    assert result["exit_code"] == planner.EXIT_COMPLETE
    assert result["receipt"]["pending"]["total"] == 51_275
    assert result["receipt"]["generation_0"]["counts"]["coinalyze_charge"] == 569
    assert result["receipt"]["generation_0"]["counts"]["charge_transition"] == 1_707
    assert result["receipt"]["generation_0"]["counts"]["terminal_gap"] == 202
    assert live["pending"] <= planner.CURSOR_BATCH
    assert live["listing"] <= 500
    assert live["listing"] > 0


def test_query_only_write_probe(tmp_path: Path) -> None:
    built = build_store(tmp_path)
    fd = os.open(str(built["gate2"] / planner.SQLITE_NAME), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        conn = planner._open_sqlite_immutable(fd, planner.PlannerHooks())
        try:
            with pytest.raises(sqlite3.Error):
                conn.execute("INSERT INTO coinalyze_ledger(id, charged) VALUES (2, 0)")
        finally:
            conn.close()
    finally:
        os.close(fd)
