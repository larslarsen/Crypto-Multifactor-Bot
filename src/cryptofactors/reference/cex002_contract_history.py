"""Compile reviewed, incomplete CEX-002 contract notices into a pinned companion.

This is a pure retrospective reference compilation. It neither asserts historical
receipt of today's recovered notices nor writes the REF-001 database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptofactors.ids import fingerprint
from cryptofactors.reference.models import (
    AliasRecord, Asset, AssetClass, BiTemporalWindow, Instrument, InstrumentType,
    InstrumentVersion, ListingEvent, ListingEventType, TargetKind, dt_to_iso,
    ensure_utc, iso_to_dt, normalize_alias,
)
from cryptofactors.reference.store import ReferenceStore

MAX_FACTS_BYTES = 4 * 1024 * 1024
_CLOSURES = frozenset({"automatic_settlement", "trading_ceases"})
_RESTRICTIONS = frozenset({"new_positions_stop", "non_reduce_only_orders_stop", "close_only"})
_TRANSITIONS = frozenset({"standard_perpetual_transition_start"})
_EVENTS = _CLOSURES | _RESTRICTIONS | _TRANSITIONS | {
    "launch", "replacement_launch", "confirmed_active",
}


@dataclass(frozen=True, slots=True)
class CompiledContractHistory:
    document: dict[str, Any]
    assets: tuple[Asset, ...]
    instruments: tuple[Instrument, ...]
    versions: tuple[InstrumentVersion, ...]
    aliases: tuple[AliasRecord, ...]
    listing_events: tuple[ListingEvent, ...]


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _hex64(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _ms(value: object) -> int:
    _require(type(value) is str, "notice event time must be a UTC timestamp")
    moment = iso_to_dt(value)
    _require(moment.utcoffset().total_seconds() == 0, "notice event time must be UTC")
    return int(moment.timestamp() * 1000)


def _dt(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, timezone.utc)


def _coverage_start(episode: Mapping[str, Any]) -> int:
    return (episode["coverage_start_ms"] if episode["launch_ms"] is None
            else episode["launch_ms"])


def _source_url(code: str | None, sources: Mapping[str, Any]) -> str | None:
    if code is None:
        return None
    source = sources.get(code)
    _require(type(source) is dict and type(source.get("source_url")) is str,
             f"snapshot source code has no URL: {code}")
    return source["source_url"]


def compile_contract_history(
    facts: Mapping[str, Any], *, facts_sha256: str, publication_sha256: str,
    known_from: datetime,
) -> CompiledContractHistory:
    """Return typed REF-001 records and a stable serialized companion document."""
    _require(_hex64(facts_sha256) and _hex64(publication_sha256), "authority SHA-256 is malformed")
    known = ensure_utc(known_from)
    _require(isinstance(facts, Mapping), "facts must be a mapping")
    notices = facts.get("notices")
    snapshot = facts.get("snapshot_episode_reviews", {})
    _require(type(notices) is list and type(snapshot) is dict
             and type(snapshot.get("cases", [])) is list and type(snapshot.get("sources", {})) is dict,
             "reviewed notice structure is malformed")
    sources = snapshot.get("sources", {})
    # One logical event can be attested in both a notice and a snapshot review.
    events: dict[tuple[str, str, int], dict[str, Any]] = {}
    launch_terms: dict[tuple[str, int], dict[str, Any]] = {}
    unresolved: dict[str, set[str]] = {}
    unresolved_events: dict[str, list[dict[str, Any]]] = {}
    unresolved_contracts = facts.get("unresolved_contracts", [])
    _require(type(unresolved_contracts) is list, "unresolved contracts must be a list")
    unresolved_seen: set[str] = set()
    for item in unresolved_contracts:
        _require(type(item) is dict, "unresolved contract is malformed")
        symbol = item.get("native_symbol")
        reasons = item.get("reasons")
        evidence = item.get("events")
        _require(type(symbol) is str and bool(symbol) and symbol not in unresolved_seen
                 and type(reasons) is list and bool(reasons)
                 and all(type(reason) is str and bool(reason) for reason in reasons)
                 and type(evidence) is list
                 and all(type(event) is dict and type(event.get("event")) is str
                         and bool(event["event"]) for event in evidence),
                 "unresolved contract evidence is malformed/duplicated")
        unresolved_seen.add(symbol)
        unresolved[symbol] = set(reasons)
        unresolved_events[symbol] = list(evidence)

    def add(symbol: str, raw: Mapping[str, Any], *, source_url: str | None,
            source_ref: str, terms: Mapping[str, Any] | None = None) -> None:
        _require(type(symbol) is str and bool(symbol), "notice native symbol is malformed")
        kind = raw.get("event")
        _require(type(kind) is str, "notice event kind is malformed")
        if raw.get("event_status") in {"cancelled", "postponed"} or raw.get("executable_boundary") is False:
            return
        _require(kind in _EVENTS, f"unknown execution event: {kind}")
        if kind == "confirmed_active":
            _require((terms is None or isinstance(terms, Mapping) and not terms)
                     and not raw.get("terms_at_launch"),
                     f"confirmed-active evidence cannot carry launch terms: {symbol}")
        when = _ms(raw.get("effective_at"))
        key = (symbol, kind, when)
        event = events.setdefault(key, {"native_symbol": symbol, "event": kind,
                                        "effective_ms": when, "source_refs": [], "source_urls": [],
                                        "launch_source_urls": [],
                                        "raw_evidence": [],
                                        "details": {key: value for key, value in raw.items()
                                                    if key not in {"event", "effective_at"}}})
        if source_ref not in event["source_refs"]:
            event["source_refs"].append(source_ref)
        item = {"source_ref": source_ref, "source_url": source_url, "raw": dict(raw)}
        if item not in event["raw_evidence"]:
            event["raw_evidence"].append(item)
        if source_url and source_url not in event["source_urls"]:
            event["source_urls"].append(source_url)
        if kind == "launch" and source_url and source_url not in event["launch_source_urls"]:
            event["launch_source_urls"].append(source_url)
        if kind == "launch" and terms:
            previous = launch_terms.setdefault((symbol, when), {})
            for field, value in terms.items():
                if field in previous and previous[field] != value:
                    raise ValueError(f"conflicting launch-only term for {symbol}: {field}")
                previous[field] = value
            for field, value in terms.items():
                if field.endswith("_source_code"):
                    extra_url = _source_url(value, sources)
                    if extra_url and extra_url not in event["source_urls"]:
                        event["source_urls"].append(extra_url)

    for notice in notices:
        _require(type(notice) is dict and type(notice.get("native_symbols")) is list
                 and type(notice.get("events")) is list, "notice is malformed")
        url = notice.get("source_url")
        _require(type(url) is str and bool(url), "notice source URL is missing")
        for symbol in notice["native_symbols"]:
            for raw in notice["events"]:
                _require(type(raw) is dict, "notice event is malformed")
                add(symbol, raw, source_url=url, source_ref=notice.get("fact_id", url),
                    terms=notice.get("terms_at_launch"))

    for case in snapshot.get("cases", []):
        _require(type(case) is dict and type(case.get("native_symbol")) is str
                 and type(case.get("episodes")) is list, "snapshot episode case is malformed")
        symbol = case["native_symbol"]
        for episode in case["episodes"]:
            _require(type(episode) is dict, "snapshot episode is malformed")
            for field in ("launch", "settlement_start"):
                raw = episode.get(field)
                if raw is None:
                    continue
                _require(type(raw) is dict, "snapshot boundary is malformed")
                code = raw.get("source_code")
                add(symbol, raw, source_url=_source_url(code, sources),
                    source_ref=f"snapshot:{code}",
                    terms=episode.get("terms_at_launch") if field == "launch" else None)
        for raw in case.get("additional_events", []):
            _require(type(raw) is dict, "snapshot additional event is malformed")
            code = raw.get("source_code")
            add(symbol, raw, source_url=_source_url(code, sources),
                source_ref=f"snapshot:{code}")

    for symbol in facts.get("missing_snapshot_symbols", []):
        _require(type(symbol) is str, "missing snapshot symbol is malformed")
        unresolved.setdefault(symbol, set()).add("snapshot_not_full_history")

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for event in events.values():
        event["source_refs"].sort()
        event["source_urls"].sort()
        event["launch_source_urls"].sort()
        event["raw_evidence"].sort(key=lambda item: (item["source_ref"],
             json.dumps(item["raw"], sort_keys=True, separators=(",", ":"))))
        by_symbol.setdefault(event["native_symbol"], []).append(event)

    venue_id = ReferenceStore.venue_id_for("BINANCE")
    assets: list[Asset] = []
    instruments: list[Instrument] = []
    versions: list[InstrumentVersion] = []
    aliases: list[AliasRecord] = []
    listings: list[ListingEvent] = []
    episodes: list[dict[str, Any]] = []
    for symbol, ordered in sorted(by_symbol.items()):
        priority = {**{kind: 0 for kind in _CLOSURES}, "launch": 1,
                    "replacement_launch": 1, "confirmed_active": 1,
                    **{kind: 2 for kind in _RESTRICTIONS},
                    **{kind: 3 for kind in _TRANSITIONS}}
        ordered.sort(key=lambda item: (item["effective_ms"], priority[item["event"]], item["event"]))
        active: dict[str, Any] | None = None
        for event in ordered:
            kind = event["event"]
            when = event["effective_ms"]
            if kind == "replacement_launch" and event["details"].get("native_symbol") != symbol:
                previous = next((item for item in reversed(episodes)
                                 if item["native_symbol"] == symbol), None)
                if previous is not None:
                    previous["related_events"].append(event)
                    previous["source_urls"] = sorted(set(previous["source_urls"])
                                                     | set(event["source_urls"]))
                else:
                    unresolved.setdefault(symbol, set()).add("replacement_without_recovered_episode")
                    unresolved_events.setdefault(symbol, []).append(event)
            elif kind in {"launch", "replacement_launch", "confirmed_active"}:
                if active is not None:
                    raise ValueError(f"overlapping launches for {symbol}")
                confirmed = kind == "confirmed_active"
                urls = event["source_urls"] if confirmed else event["launch_source_urls"]
                _require(bool(urls), f"launch lacks documented source: {symbol}")
                identity = ({"venue": "BINANCE", "native_symbol": symbol,
                             "start_kind": "confirmed_active", "coverage_start_ms": when,
                             "confirmation_source_url": urls[0]} if confirmed else
                            {"venue": "BINANCE", "native_symbol": symbol,
                             "launch_ms": when, "launch_source_url": urls[0]})
                asset_id = ReferenceStore.asset_id_for(
                    asset_class=AssetClass.DERIVATIVE_UNDERLIER,
                    identity_key=json.dumps(identity, sort_keys=True, separators=(",", ":")),
                )
                instrument_id = ReferenceStore.instrument_id_for(
                    asset_id=asset_id, venue_id=venue_id,
                    instrument_type=InstrumentType.PERPETUAL,
                    salt=json.dumps(identity, sort_keys=True, separators=(",", ":")),
                )
                active = {"native_symbol": symbol, "asset_id": asset_id,
                          "instrument_id": instrument_id, "instrument_version_id": fingerprint(
                              "iv", {"instrument_id": instrument_id, "version_seq": 1,
                                     "valid_from": dt_to_iso(_dt(when))}),
                          "launch_ms": None if confirmed else when, "execution_end_ms": None,
                          "new_positions_stop_ms": None, "source_urls": list(event["source_urls"]),
                          "launch_terms": {} if confirmed else launch_terms.get((symbol, when), {}),
                          "historical_terms_complete": False, "events": [event],
                          "pre_market_events": [], "related_events": [],
                          "history_complete": False}
                if confirmed:
                    active.update(coverage_start_ms=when, start_kind="confirmed_active")
                episodes.append(active)
                if symbol in unresolved:
                    unresolved[symbol].discard("snapshot_not_full_history")
                    if not unresolved[symbol]:
                        unresolved.pop(symbol)
            elif active is None:
                unresolved.setdefault(symbol, set()).add("event_without_recovered_launch")
                unresolved_events.setdefault(symbol, []).append(event)
            elif kind in _CLOSURES:
                _require(when > _coverage_start(active), f"closure precedes episode start for {symbol}")
                active["execution_end_ms"] = when
                active["events"].append(event)
                active["source_urls"] = sorted(set(active["source_urls"]) | set(event["source_urls"]))
                active = None
            elif kind in _RESTRICTIONS:
                _require(when > _coverage_start(active), f"restriction precedes episode start for {symbol}")
                prior = active["new_positions_stop_ms"]
                active["new_positions_stop_ms"] = when if prior is None else min(prior, when)
                active["events"].append(event)
                active["source_urls"] = sorted(set(active["source_urls"]) | set(event["source_urls"]))
            else:
                active["pre_market_events"].append(event)
                active["source_urls"] = sorted(set(active["source_urls"]) | set(event["source_urls"]))

    episodes.sort(key=lambda item: (item["native_symbol"], _coverage_start(item)))
    for episode in episodes:
        launch = _coverage_start(episode)
        confirmed = episode["launch_ms"] is None
        end = episode["execution_end_ms"]
        restriction = episode["new_positions_stop_ms"]
        _require(end is None or launch < end, "episode end precedes launch")
        _require(restriction is None or launch < restriction and (end is None or restriction <= end),
                 "new-position restriction is outside its episode")
        window = BiTemporalWindow(_dt(launch), known, _dt(end) if end is not None else None)
        asset = Asset(episode["asset_id"], AssetClass.DERIVATIVE_UNDERLIER,
                      f"{episode['native_symbol']} venue contract episode", known)
        instrument = Instrument(episode["instrument_id"], asset.asset_id, venue_id,
                                InstrumentType.PERPETUAL, known)
        spec = {"scope": "confirmed_active_evidence_only" if confirmed else "launch_terms_only",
                "historical_terms_complete": False,
                "launch_terms": episode["launch_terms"]}
        version = InstrumentVersion(episode["instrument_version_id"], instrument.instrument_id,
                                    1, spec, window, evidence={"events": episode["events"]})
        alias_identity = {"native_symbol": episode["native_symbol"],
                          "instrument_id": instrument.instrument_id}
        alias_identity.update({"start_kind": "confirmed_active", "coverage_start_ms": launch}
                              if confirmed else {"launch_ms": launch})
        alias = AliasRecord(fingerprint("als", alias_identity),
                            episode["native_symbol"], normalize_alias(episode["native_symbol"]),
                            TargetKind.INSTRUMENT, instrument.instrument_id, window,
                            venue_id=venue_id, evidence={
                                "confirmed_active" if confirmed else "launch": episode["events"][0]},
                            is_primary=True)
        assets.append(asset)
        instruments.append(instrument)
        versions.append(version)
        aliases.append(alias)
        for event in episode["events"]:
            kind = event["event"]
            if kind != "launch" and kind not in _CLOSURES:
                continue
            event_type = ListingEventType.LIST if kind == "launch" else ListingEventType.SUSPEND
            listings.append(ListingEvent(fingerprint("lst", {"instrument_id": instrument.instrument_id,
                 "venue_id": venue_id, "event_type": event_type.value,
                 "valid_from": dt_to_iso(_dt(event["effective_ms"])), "known_from": dt_to_iso(known)}),
                 instrument.instrument_id, venue_id, event_type,
                 BiTemporalWindow(_dt(event["effective_ms"]), known),
                 evidence={"schedule_kind": kind, "announced_execution_end_not_completion": kind in _CLOSURES,
                           "source_refs": event["source_refs"], "source_urls": event["source_urls"]}))
    schema = 2 if unresolved_contracts or any(item["launch_ms"] is None for item in episodes) else 1
    document = {"document_type": "cex002_contract_history", "schema_version": schema,
                "publication_sha256": publication_sha256, "facts_sha256": facts_sha256,
                "known_from": dt_to_iso(known), "history_complete": False,
                "episodes": episodes,
                "unresolved_symbols": [{"native_symbol": symbol, "reasons": sorted(reasons),
                                        "events": unresolved_events.get(symbol, [])}
                                       for symbol, reasons in sorted(unresolved.items())]}
    return CompiledContractHistory(document, tuple(assets), tuple(instruments),
                                   tuple(versions), tuple(aliases), tuple(listings))


def _read_facts(path: Path, expected_sha: str) -> dict[str, Any]:
    _require(_hex64(expected_sha), "facts SHA-256 is malformed")
    facts = path.lstat()
    _require(stat.S_ISREG(facts.st_mode) and not stat.S_ISLNK(facts.st_mode)
             and facts.st_size <= MAX_FACTS_BYTES, "facts path is not a bounded regular non-symlink file")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        first = os.fstat(descriptor)
        body = os.read(descriptor, MAX_FACTS_BYTES + 1)
        last = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    _require(len(body) <= MAX_FACTS_BYTES and (first.st_dev, first.st_ino, first.st_size,
              first.st_mtime_ns, first.st_ctime_ns) == (last.st_dev, last.st_ino,
              last.st_size, last.st_mtime_ns, last.st_ctime_ns)
             and len(body) == first.st_size and hashlib.sha256(body).hexdigest() == expected_sha,
             "facts bytes changed or SHA-256 differs")
    parsed = json.loads(body)
    _require(type(parsed) is dict, "facts root must be an object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--facts-sha", required=True)
    parser.add_argument("--publication-sha", required=True)
    parser.add_argument("--known-from", required=True, help="explicit timezone-aware research knowledge time")
    args = parser.parse_args(argv)
    compiled = compile_contract_history(_read_facts(args.facts, args.facts_sha),
        facts_sha256=args.facts_sha, publication_sha256=args.publication_sha,
        known_from=iso_to_dt(args.known_from))
    print(json.dumps(compiled.document, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
