# CEX-002 Focused Test Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `59f899e1d1723bdd7acdc687910f3cb914688392`

Subject record: `research/sprint_004/141_CEX002_ADR0020_INTEGRATION_AND_CANDIDATE.md`

## Decision

**ACCEPT THE INTEGRATION AND RECORD-141 STOP; REJECT ONE STALE TEST ASSERTION.**

Commit `68d437cb0db4c1bc0b4246b131ba0deb38c60699` integrates exactly the three review-140
source identities. Commit `59f899e1d1723bdd7acdc687910f3cb914688392` publishes exactly
the two controls and record 141. Both commits are pushed, `HEAD == origin/main`, the
unrelated dirty paths remain unstaged, and the accepted compact report remains unchanged at
17,349,108 bytes and SHA-256
`e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`.

Hermes obeyed stop-on-first-failure. C1 returned exit 1, so C2-C5, report preservation,
candidate execution, and all post-proof work were correctly not run.

## Finding

### P2 - the resolved-delivery test expects the threshold instead of the fixture fact

`test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves` constructs its
archive with `_authority_index()` defaults. Those defaults contain exactly three official
families: `monthly/trades`, `monthly/aggTrades`, and `monthly/klines`. Production
`_archive_presence()` correctly reports every observed family, so `family_count` is 3.
`REVIEWED_DELIVERY_MIN_FAMILIES == 2` is the minimum required for resolution, not the
expected count for a three-family fixture.

The production source is correct and remains frozen. The test assertion at line 7064 is a
stale oracle.

## Spark correction authorization

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High may edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Spark changes only this exact assertion inside
`test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves`:

```python
assert authority["archive_evidence"]["family_count"] == 2
```

to:

```python
assert authority["archive_evidence"]["family_count"] == 3
```

Every other byte and all 261 uniquely named `test_` functions remain unchanged. Spark
runs no command, test, Ruff, repository-control, network/data work, candidate, or Git
operation; edits no source, fixture, control, record, report, or unrelated path; and stops
with the exact test-file SHA-256 and unique test-function count. Hermes remains
unauthorized pending reviewer inspection of that one-line source correction.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/142_CEX002_FOCUSED_TEST_FAILURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test drop, report, fixture, ignored data, checkpoint, cache, journal, database
sidecar, or unrelated dirty path belongs to this publication. The reviewer executes no
pytest, Ruff, repository-control, candidate, migration, sample, or data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
