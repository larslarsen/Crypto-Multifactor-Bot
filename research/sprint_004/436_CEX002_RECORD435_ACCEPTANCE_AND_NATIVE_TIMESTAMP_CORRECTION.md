# CEX-002 Review 436 — Record 435 Acceptance and Native-Timestamp Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal record; supersede two sample-derived normalizer assumptions; authorize one bounded source/test correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Record 435 acceptance

Hermes commit `119f72bcb808e7e2d603c961d7b3b3de4edf7c56` is accepted as the exact
three-path publication of record 435. The sole Review-434 runner authenticated the accepted
repository-relative authority identities, loaded the fixed Gate-2 sources, published 173 new
content-addressed partition/lineage pairs, and then exited 1 on the production source's exact-grid
assertion. The hidden root contains 181 Parquets plus 181 matching lineage files, empty staging,
and no completion descriptor. It remains preserved, hidden, unaccepted resume evidence.

The failure does not reopen Gate 2 and does not authorize acquisition or redownload. It exposes
an implementation assumption in the open-interest normalizer.

## Governing contract

ADR-0024 requires the typed product to retain every economically valid source row and every source
timestamp, with exact raw lineage. Review 415 requires the open-interest product to reuse that
accepted typed timestamp contract, preserve every valid metrics field, compute actual elapsed
seconds, refuse duplicate-conflicting input, and emit gaps rather than repaired values. The
accepted sizing implementation already converts and preserves `create_time` as supplied and marks
stock changes `contiguous` only when the actual elapsed interval is exactly 300 seconds.

The production normalizer's additional requirement that every source timestamp be an exact UTC
five-minute clock-grid point is therefore not part of the frozen architecture. Neither rounding,
snapping, imputation, nor timestamp replacement is permitted. This review restores the accepted
contract and requires no ADR amendment.

## Complete read-only source-shape proof

The reviewer scanned the timestamp field of every accepted usable metrics ZIP: all 522,865
generation-0 objects plus all 50,920 usable v3 objects, excluding only the separately accepted
HBAR checksum-conflict identity. The scan was read-only and wrote no repository or data path.

| Measured fact | Exact result |
|---|---:|
| Accepted usable metrics ZIPs | 573,785 |
| Physical data rows | 160,226,578 |
| Timestamp parse failures | 0 |
| Subsecond timestamps | 0 |
| Exact-second timestamps not on the UTC five-minute clock grid | 62,191 |
| Files containing those timestamps | 1,620 |
| Date-only midnight timestamp tokens accepted by the existing converter | 3 |
| Files with more than 288 physical rows | 263 |
| Maximum physical rows in one ZIP | 576 |
| Repeated timestamp groups | 75,255 |
| Byte-for-byte identical repeated-row groups | 75,255 |
| Conflicting repeated-row groups | 0 |
| Out-of-contract-day rows | 2,818 |
| Files containing an out-of-day row | 2,818 |
| Maximum out-of-day rows in one file | 1 |
| Out-of-day displacement from next midnight | 0 through 59 seconds |

All 263 files above 288 rows are BTCUSDT daily metrics objects from 2020-09-01 through
2021-05-21. They contain 576 rows at maximum because the provider repeated otherwise identical
physical rows. Comparing the complete raw CSV line bytes within each repeated timestamp group
found 75,255 exact repetitions and zero byte conflicts. After collapsing only those exact repeats,
every source remains at or below 288 unique timestamps, so the accepted fixed-cadence economic-row
ceiling and sizing basis do not change.

The actual successive timestamp intervals after per-file stable sorting were 159,485,878 exact
300-second intervals, 28,050 positive intervals below 300 seconds, 27,757 intervals from 301
through 599 seconds, 35,853 intervals of at least 600 seconds, and the 75,255 identical timestamp
repetitions above. These are provider-native observation times, not corrupt values.

The complete second pass proved that every out-of-day shape is exactly one row in its file and
falls at the immediately following midnight plus 0 through 59 seconds. No preceding-day row,
second spillover, displacement of 60 seconds or more, later date, timestamp parse failure,
subsecond value, or conflicting repeated row was observed.

This full-corpus result supersedes Review 427's sample-derived 288-physical-row assumption and
Review 429's sample-derived exact-midnight-only spillover assumption. It does not supersede the
filename contract-day authority, exact source retention, duplicate-conflict rejection, stock/change
semantics, or fail-closed behavior.

## Bounded correction authorized

Sr Dev — Codex Sol on GPT-5.6-sol High may edit exactly:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`; and
- `tests/ingest/test_binance_usdm_open_interest.py`.

The CLI, accepted sizing implementation, acquisition sources, repository records, hidden output,
and every unrelated path are frozen.

The correction must implement all of the following literally:

1. Preserve every accepted source `create_time` exactly as its integer millisecond timestamp.
   Continue to reject invalid or subsecond timestamps. Remove only the absolute UTC five-minute
   clock-grid assertion. Do not add a rounded, snapped, bucketed, or replacement timestamp.
2. Preserve the accepted sizing semantics: `change_interval_seconds` is the actual positive
   elapsed number of seconds; `contiguous` and stock/value changes exist only for an exact
   300-second interval not crossing a declared source gap. Every other positive interval is
   `gap_break` and has null prior/change fields.
3. Infer a missing-cadence run only when at least one complete 300-second cadence is absent between
   observed timestamps. For positive `interval_seconds`, the exact missing count is
   `max(0, interval_seconds // 300 - 1)`, at source-phase timestamps
   `previous_time + n * 300 seconds` for `n = 1..missing_count`. Merely observing a 301-through-599
   second separation does not invent a missing row. Gap runs remain deterministic and are split at
   UTC-month boundaries without requiring their absolute timestamps to be clock-grid aligned.
4. Replace the incorrect 288-physical-row parser ceiling with the complete-corpus maximum of 576
   physical rows. A 577th physical row still fails before publication. This is a parser bound, not
   permission to collapse or omit an economic observation.
5. Stable-sort every fully validated source by its exact source timestamp. Collapse a repeated
   timestamp only when it is in the same authenticated source object and every original CSV token
   is byte-for-byte identical. Retain the first physical ordinal as the product row and record each
   collapsed ordinal in deterministic affected-partition lineage with source key, source SHA-256,
   kept ordinal, collapsed ordinal, exact observed timestamp, and a fixed identical-repeat reason.
   Any differing token, cross-source repeat, or otherwise ambiguous duplicate still fails.
6. Extend the existing adjacent-next-midnight exclusion only to the completely observed source
   domain: exactly one fully validated row at the immediately following UTC midnight plus 0 through
   59 seconds, with at least one owned-day row remaining. Record the row's actual timestamp, source
   identity, hash, and ordinal. A second excluded row, preceding-day row, displacement of 60 seconds
   or more, later date, or all-excluded source still fails. No spillover is reassigned or allowed to
   compete with the next day's owned source.
7. Omit the new identical-repeat lineage field when empty so all 181 preserved unaffected
   partition/lineage pairs remain byte-identical and reusable. The final completion totals must
   reconcile product rows, adjacent-midnight exclusions, and collapsed identical physical rows.
   No valid value or source timestamp may disappear without one of those exact lineage bindings.

Focused tests must cover off-grid exact-second retention without value changes; stable delayed
timestamps with an exact 300-second interval; 301-through-599 second gap-break behavior without an
invented missing row; an off-grid-phase missing run of at least 600 seconds; UTC-month gap splitting;
the three accepted date-only-midnight format semantics; 576 identical-pair physical rows collapsing
to 288 product rows with exact dual-ordinal lineage; conflicting and cross-source duplicate
rejection; a 577-row rejection; spillovers at offsets 0 and 59; rejection at offset 60 and on a
second spillover; unchanged optional-lineage omission; and exact completion-count reconciliation.
Existing shuffled-order, HBAR conflict, midnight ownership, economic validation, publication, and
replay tests remain in force.

Sol may run exactly once after editing:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on a nonzero result without patching or rerunning and otherwise stops for reviewer source
inspection with exact hashes, line counts, command, and output. Sol performs no real-data
invocation, data mutation, integration, repository-record edit, Git operation, commit, push,
network access, acquisition, cleanup, retry, other product, bundle, catalog transaction,
NautilusTrader check, experiment, model, trading-engine work, or next ticket.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/436_CEX002_RECORD435_ACCEPTANCE_AND_NATIVE_TIMESTAMP_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer source/test paths, hidden data, runner evidence, the untracked wrapper, and every
unrelated dirty path remain unstaged and untouched.
