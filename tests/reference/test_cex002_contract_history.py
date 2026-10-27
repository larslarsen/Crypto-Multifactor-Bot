"""Synthetic notice and REF-001 identity checks for the dated companion."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.reference.cex002_contract_history import compile_contract_history, main
from cryptofactors.reference.models import AssetClass, ListingEventType


KNOWN = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
PUBLICATION = "a" * 64
FACTS_SHA = "b" * 64


def _event(kind: str, when: str, **extra):
    return {"event": kind, "effective_at": when, **extra}


def _notice(identifier: str, symbol: str, events: list[dict], terms: dict | None = None):
    return {"fact_id": identifier, "source_url": f"https://example.test/{identifier}",
            "native_symbols": [symbol], "events": events,
            "terms_at_launch": terms or {}, "history_complete": False}


def _facts() -> dict:
    return {
        "missing_snapshot_symbols": ["FTTBUSD", "BTTUSDT", "ORPHANUSDT"],
        "notices": [
            _notice("ftt-launch", "FTTBUSD", [_event("launch", "2021-09-08T04:00:00Z")]),
            _notice("ftt-cancel", "FTTBUSD", [_event("automatic_settlement",
                "2022-05-19T09:00:00Z", event_status="cancelled", executable_boundary=False)]),
            _notice("ftt-real-end", "FTTBUSD", [_event("automatic_settlement",
                "2022-11-14T04:30:00Z")]),
            _notice("btt-cancel", "BTTUSDT", [_event("launch",
                "2020-09-15T07:00:00Z", event_status="cancelled", executable_boundary=False)]),
            _notice("btt-launch", "BTTUSDT", [_event("launch", "2021-04-06T07:00:00Z")]),
            _notice("btt-end", "BTTUSDT", [_event("automatic_settlement",
                "2022-01-14T02:00:00Z")]),
            _notice("orphan", "ORPHANUSDT", [_event("automatic_settlement", "2023-01-01T00:00:00Z")]),
            _notice("aia-launch-1", "AIAUSDT", [_event("launch", "2025-01-01T00:00:00Z")],
                    {"underlying": "Old AIA", "settlement_asset": "USDT"}),
            _notice("aia-end", "AIAUSDT", [_event("new_positions_stop", "2025-02-01T08:30:00Z"),
                    _event("automatic_settlement", "2025-02-01T09:00:00Z")]),
            _notice("aia-launch-2", "AIAUSDT", [_event("launch", "2025-03-01T00:00:00Z")],
                    {"underlying": "New AIA", "settlement_asset": "USDT"}),
            _notice("lit-1", "LITUSDT", [_event("launch", "2021-01-01T00:00:00Z")]),
            _notice("lit-end", "LITUSDT", [_event("automatic_settlement", "2025-01-01T00:00:00Z")]),
            _notice("lit-2", "LITUSDT", [_event("launch", "2025-12-01T00:00:00Z")]),
            _notice("pump-1", "PUMPUSDT", [_event("launch", "2025-04-01T00:00:00Z")]),
            _notice("pump-end", "PUMPUSDT", [_event("automatic_settlement", "2025-06-01T00:00:00Z")]),
            _notice("pump-2", "PUMPUSDT", [_event("launch", "2025-07-01T00:00:00Z")]),
        ],
        "snapshot_episode_reviews": {"sources": {
            "aia-1": {"source_url": "https://example.test/aia-launch-1"},
            "aia-end": {"source_url": "https://example.test/aia-end"},
            "aia-2": {"source_url": "https://example.test/aia-launch-2"},
            "aia-transition": {"source_url": "https://example.test/aia-transition"},
            "aia-postponed": {"source_url": "https://example.test/aia-postponed"},
        }, "cases": [{"native_symbol": "AIAUSDT", "episodes": [{
            "launch": _event("launch", "2025-01-01T00:00:00Z", source_code="aia-1"),
            "settlement_start": _event("automatic_settlement", "2025-02-01T09:00:00Z",
                                       source_code="aia-end"),
        }, {
            "launch": _event("launch", "2025-03-01T00:00:00Z", source_code="aia-2"),
            "settlement_start": None, "terms_at_launch": {"tick_size": "0.001"},
        }], "additional_events": [
            _event("launch", "2025-02-15T00:00:00Z", source_code="aia-postponed",
                   event_status="postponed", executable_boundary=False),
            _event("standard_perpetual_transition_start", "2025-03-02T00:00:00Z",
                   source_code="aia-transition", positions_retained=True,
                   maximum_transition_hours=3),
        ]}]},
    }


def _compile(facts: dict):
    return compile_contract_history(facts, facts_sha256=FACTS_SHA,
                                    publication_sha256=PUBLICATION, known_from=KNOWN)


def test_cancellation_relaunch_reuse_restriction_and_typed_identity() -> None:
    compiled = _compile(_facts())
    episodes = compiled.document["episodes"]
    assert len(episodes) == 8
    ftt = next(item for item in episodes if item["native_symbol"] == "FTTBUSD")
    btt = next(item for item in episodes if item["native_symbol"] == "BTTUSDT")
    assert ftt["execution_end_ms"] > ftt["launch_ms"]
    assert btt["launch_ms"] > 0 and btt["execution_end_ms"] > btt["launch_ms"]
    cancelled_ftt_ms = int(datetime(2022, 5, 19, 9, tzinfo=timezone.utc).timestamp() * 1000)
    assert ftt["launch_ms"] < cancelled_ftt_ms < ftt["execution_end_ms"]
    assert all(event["effective_ms"] != cancelled_ftt_ms for event in ftt["events"])
    assert btt["launch_ms"] == int(datetime(2021, 4, 6, 7, tzinfo=timezone.utc).timestamp() * 1000)
    aia = [item for item in episodes if item["native_symbol"] == "AIAUSDT"]
    lit = [item for item in episodes if item["native_symbol"] == "LITUSDT"]
    pump = [item for item in episodes if item["native_symbol"] == "PUMPUSDT"]
    assert aia[0]["instrument_id"] != aia[1]["instrument_id"]
    assert lit[0]["asset_id"] != lit[1]["asset_id"]
    assert pump[0]["instrument_id"] != pump[1]["instrument_id"]
    assert aia[0]["new_positions_stop_ms"] < aia[0]["execution_end_ms"]
    assert len([event for event in aia[0]["events"]
                if event["event"] == "automatic_settlement"]) == 1
    assert aia[1]["launch_terms"]["tick_size"] == "0.001"
    assert aia[1]["pre_market_events"][0]["details"]["positions_retained"] is True
    assert aia[1]["pre_market_events"][0]["details"]["maximum_transition_hours"] == 3
    assert len([event for event in aia[1]["events"] if event["event"] == "launch"]) == 1
    assert all(asset.asset_class is AssetClass.DERIVATIVE_UNDERLIER for asset in compiled.assets)
    assert len(compiled.instruments) == len(compiled.versions) == len(compiled.aliases) == 8
    assert len([event for event in compiled.listing_events
                if event.event_type is ListingEventType.SUSPEND]) == 5
    unresolved = {item["native_symbol"]: item["reasons"]
                  for item in compiled.document["unresolved_symbols"]}
    assert "event_without_recovered_launch" in unresolved["ORPHANUSDT"]
    assert "BTTUSDT" not in unresolved and "FTTBUSD" not in unresolved
    assert all(asset.created_at == KNOWN for asset in compiled.assets)
    assert all(instrument.created_at == KNOWN for instrument in compiled.instruments)
    assert compiled.document["history_complete"] is False


def test_unrelated_notice_does_not_rename_existing_episode() -> None:
    facts = _facts()
    original = _compile(facts).document["episodes"]
    facts["notices"].append(_notice("unrelated", "ZZZUSDT", [
        _event("launch", "2025-04-01T00:00:00Z")]))
    changed = _compile(facts).document["episodes"]
    assert [(item["native_symbol"], item["instrument_id"]) for item in original] == [
        (item["native_symbol"], item["instrument_id"])
        for item in changed if item["native_symbol"] != "ZZZUSDT"]


def test_conflicting_launch_and_unknown_execution_event_refuse() -> None:
    facts = _facts()
    facts["notices"].append(_notice("overlap", "AIAUSDT", [
        _event("launch", "2025-01-10T00:00:00Z")]))
    with pytest.raises(ValueError, match="overlapping launches"):
        _compile(facts)
    facts = _facts()
    facts["notices"].append(_notice("unknown", "AIAUSDT", [
        _event("trading_pause_unknown", "2025-01-10T00:00:00Z")]))
    with pytest.raises(ValueError, match="unknown execution event"):
        _compile(facts)


def test_cli_authenticates_bounded_facts_and_prints_deterministic_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "facts.json"
    body = json.dumps(_facts(), sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    args = ["--facts", str(path), "--facts-sha", sha,
            "--publication-sha", PUBLICATION, "--known-from", "2026-10-27T12:00:00Z"]
    assert main(args) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["facts_sha256"] == sha and len(document["episodes"]) == 8
    with pytest.raises(ValueError, match="SHA-256 differs"):
        main([*args[:3], "0" * 64, *args[4:]])
    alias = tmp_path / "facts-link.json"
    alias.symlink_to(path)
    with pytest.raises(ValueError, match="non-symlink"):
        main(["--facts", str(alias), *args[2:]])


def test_confirmed_active_is_evidence_only_and_preserves_exact_launch_records() -> None:
    facts = _facts()
    original = _compile(facts)
    assert original.document["schema_version"] == 1
    facts["notices"].append(_notice("btc-confirmation", "BTCUSDT", [
        _event("confirmed_active", "2019-09-09T00:00:00Z", basis="notice confirms trading")]))
    compiled = _compile(facts)
    assert compiled.document["schema_version"] == 2
    assert [item for item in compiled.document["episodes"]
            if item["native_symbol"] != "BTCUSDT"] == original.document["episodes"]
    for records, old_records in ((compiled.versions, original.versions),
                                 (compiled.aliases, original.aliases),
                                 (compiled.listing_events, original.listing_events)):
        assert all(record in records for record in old_records)
    episode = next(item for item in compiled.document["episodes"] if item["native_symbol"] == "BTCUSDT")
    confirmed_at = datetime(2019, 9, 9, tzinfo=timezone.utc)
    assert episode["launch_ms"] is None
    assert episode["coverage_start_ms"] == int(confirmed_at.timestamp() * 1000)
    assert episode["start_kind"] == "confirmed_active" and episode["launch_terms"] == {}
    assert episode["events"][0]["event"] == "confirmed_active"
    version = next(item for item in compiled.versions
                   if item.instrument_id == episode["instrument_id"])
    alias = next(item for item in compiled.aliases if item.target_id == episode["instrument_id"])
    assert version.contract_spec == {"scope": "confirmed_active_evidence_only",
                                     "historical_terms_complete": False, "launch_terms": {}}
    assert version.window.valid_from == alias.window.valid_from == confirmed_at
    assert version.window.known_from == alias.window.known_from == KNOWN
    assert not version.window.active_at(decision_time=confirmed_at,
        knowledge_time=datetime(2026, 10, 26, tzinfo=timezone.utc))
    assert "confirmed_active" in alias.evidence and "launch" not in alias.evidence
    assert not any(item.instrument_id == episode["instrument_id"] for item in compiled.listing_events)
    exact = _compile({"notices": [_notice("btc-confirmation", "BTCUSDT", [
        _event("launch", "2019-09-09T00:00:00Z")])]}).document["episodes"][0]
    assert all(episode[field] != exact[field]
               for field in ("asset_id", "instrument_id", "instrument_version_id"))


def test_confirmed_closures_restrictions_and_subsequent_launch_use_coverage_start() -> None:
    compiled = _compile({"notices": [_notice("btc-schedules", "BTCUSDT", [
        _event("confirmed_active", "2019-09-09T00:00:00Z"),
        _event("new_positions_stop", "2020-01-01T08:30:00Z"),
        _event("automatic_settlement", "2020-01-01T09:00:00Z"),
        _event("launch", "2020-01-01T09:00:00Z"),
    ])]})
    first, second = compiled.document["episodes"]
    assert first["coverage_start_ms"] < first["new_positions_stop_ms"] < first["execution_end_ms"]
    assert second["launch_ms"] == first["execution_end_ms"]
    assert compiled.versions[0].window.valid_to == compiled.versions[1].window.valid_from
    assert [event.event_type for event in compiled.listing_events] == [
        ListingEventType.SUSPEND, ListingEventType.LIST]


@pytest.mark.parametrize("first,second,second_time", [
    ("confirmed_active", "launch", "2020-01-01T00:00:00Z"),
    ("launch", "confirmed_active", "2020-01-01T00:00:00Z"),
    ("confirmed_active", "launch", "2020-01-02T00:00:00Z"),
    ("launch", "confirmed_active", "2020-01-02T00:00:00Z"),
    ("confirmed_active", "confirmed_active", "2020-01-02T00:00:00Z"),
])
def test_confirmed_overlap_requires_explicit_reconciliation(first, second, second_time) -> None:
    with pytest.raises(ValueError, match="overlapping launches"):
        _compile({"notices": [_notice("one", "BTCUSDT", [
            _event(first, "2020-01-01T00:00:00Z")]), _notice("two", "BTCUSDT", [
                _event(second, second_time)])]})


@pytest.mark.parametrize("terms", [{"tick_size": "0.01"}, ["USDT"], "USDT"])
def test_confirmed_active_rejects_launch_terms(terms) -> None:
    notice = _notice("btc", "BTCUSDT", [_event("confirmed_active", "2020-01-01T00:00:00Z")])
    notice["terms_at_launch"] = terms
    with pytest.raises(ValueError, match="cannot carry launch terms"):
        _compile({"notices": [notice]})


def test_unresolved_postponement_is_retained_without_an_episode() -> None:
    evidence = _event("launch", "2025-11-20T12:00:00Z", event_status="postponed",
                      executable_boundary=False, source_url="https://example.test/gaib-postponed")
    unresolved = {"native_symbol": "GAIBUSDT", "reasons": ["launch_postponed_indefinitely"],
                  "events": [evidence]}
    facts = {"notices": [_notice("gaib", "GAIBUSDT", [evidence])],
             "unresolved_contracts": [unresolved]}
    compiled = _compile(facts)
    assert compiled.document["schema_version"] == 2
    assert compiled.document["unresolved_symbols"] == [unresolved]
    assert compiled.document["episodes"] == []
    assert not (compiled.assets or compiled.instruments or compiled.versions
                or compiled.aliases or compiled.listing_events)
    assert _compile({"notices": [], "unresolved_contracts": []}).document["schema_version"] == 1


@pytest.mark.parametrize("unresolved", [
    None, {}, [None], [{"native_symbol": "GAIBUSDT", "reasons": [], "events": []}],
    [{"native_symbol": "GAIBUSDT", "reasons": ["pending"], "events": [None]}],
    [{"native_symbol": "GAIBUSDT", "reasons": ["pending"], "events": [{}]}],
    [{"native_symbol": "GAIBUSDT", "reasons": ["pending"], "events": []}] * 2,
])
def test_unresolved_contracts_must_be_well_formed(unresolved) -> None:
    with pytest.raises(ValueError, match="unresolved contract"):
        _compile({"notices": [], "unresolved_contracts": unresolved})
