# CEX-002 Review 467 - Grok Funding Source Static Rejection

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer, xhigh
- **Ticket:** CEX-002
- **Decision:** reject the first realized-funding source drop and authorize one bounded Grok correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - four of eleven required products accepted
- **Next required actor:** Sr Dev - Grok Build on Grok 4.6 High
- **Next ticket:** `NONE`

## Reviewed unintegrated drop

The owner reported Grok complete. The reviewer found exactly the three Review-466 paths and no new
change outside them. `HEAD == origin/main == 0062fa0ae63a9a9b34f673eec61546e1d3e4d595`.

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_funding_realized.py` | 1,270 | `536e58698a869b5b081c2f4a6a1d600adc72d6ce5733db40ab3d59fd556d256d` |
| `scripts/research/normalize_binance_usdm_funding_realized.py` | 50 | `05e30c8712608e4895749114375a9b38ea5cf868870d913ddef5d264f77d7b2b` |
| `tests/ingest/test_binance_usdm_funding_realized.py` | 645 | `3818177dc0b07251db1988c71e3b4dcdae170e2c58ecf7d2f41af2b13acdb572` |

The owner did not relay Grok's exact targeted-test command and output. No test result is therefore
recorded or accepted by this review. Static rejection is independently decisive; the reviewer did
not execute a test or acceptance command.

## Accepted parts

The drop correctly uses the frozen 14-column schema; preserves exact event timestamp, positive
source interval, and fixed-scale rate; implements the accepted long-debit/short-credit convention;
does not invent schedule continuity; handles exact duplicate/conflict semantics; partitions by
native symbol and UTC month; binds the report and sizing identities; and follows the accepted
hidden content-addressed completion-last publication shape. The 50-line CLI matches the authorized
arguments and requires no correction.

These accepted observations do not make the source executable because two production defects
remain.

## Finding 1 - whole-corpus row retention violates bounded publication

Production line 1,045 creates `product_rows_all`. Line 1,111 appends every normalized event from
every completed partition, and line 1,140 keeps that entire collection alive solely to calculate
the final range and interval histogram. This defeats ADR-0024's partition-bounded conversion. The
accepted sizing ceiling permits 15,660,013 events, so a Python dictionary copy of every event can
consume many times the final typed-product size and fail late after most of 21,035 partitions have
already been published.

The correction must update completion statistics while each partition is resident, then release
that partition's rows. Retain only scalar extrema plus one integer count per actually observed
positive interval. No list, table, tuple, or other collection may retain all cross-partition
product rows. The final `observed_ranges` and interval histogram must remain byte-deterministic and
identical to the current logical result.

## Finding 2 - checksum-sidecar and plan-envelope authentication is incomplete

The generation-0 query at lines 424-430 selects only the nested payload, content facts, and the
provider checksum. Lines 436-452 check the nested payload and `provider_checksum == content_sha256`
but do not authenticate:

- `plan_entry.kind == binance_object`;
- the JSON envelope's top-level `provider`, `identity`, and `kind`;
- equality of completion `sidecar_sha256`/`sidecar_path` with the joined `sidecar_fact` identity;
- the sidecar fact's positive exact byte count and content-addressed path; or
- the actual no-follow sidecar bytes, digest, and checksum/filename statement.

Review 466 requires every selected object's plan identity, sidecar identity, and provider checksum
to be reproved before parsing. A sealed database row is necessary but does not replace the required
binding among its plan, completion, sidecar fact, content-addressed sidecar bytes, and raw object.

The corrected loader must select and validate all named fields. It must open each sidecar beneath
the same explicit generation-0 content root without following symlinks, prove its exact recorded
size and SHA-256, parse the bounded checksum statement, and require exactly the selected raw
content SHA-256 plus the selected ZIP basename. Missing, malformed, extra-token, mismatched,
non-content-addressed, or substituted facts fail closed. It must keep the SQLite snapshot and raw
authority read-only.

## Bounded correction authorization

Sr Dev - Grok Build on Grok 4.6 High may modify exactly:

- `src/cryptofactors/ingest/binance_usdm_funding_realized.py`; and
- `tests/ingest/test_binance_usdm_funding_realized.py`.

The CLI hash and every other path are frozen. Production must replace whole-corpus row retention
with incremental deterministic statistics and complete the sidecar/plan-envelope proof above.
Tests must add multi-partition summary-statistic coverage for the incremental accumulator and
focused acceptance/refusal cases for the top-level plan fields, completion/sidecar-fact agreement,
content-addressed sidecar path, no-follow sidecar bytes, exact size/digest, and strict checksum plus
ZIP-basename statement. Existing Review-466 behavior remains unchanged.

Under the targeted senior test exception, Grok may execute exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short
```

Grok stops on the first nonzero result and reports exact output without patching or rerunning. It
performs no real-data run, integration, Git, record/control edit, data mutation, acquisition,
network access, cleanup, other product, catalog transaction, NautilusTrader work, experiment,
model, Harmonic Trader work, PAPER, LIVE, or next-ticket work. Hermes remains unauthorized pending
reviewer acceptance of the exact corrected source/test drop.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review publishes exactly:

- `research/sprint_004/467_CEX002_GROK_FUNDING_SOURCE_STATIC_REJECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer source/test/CLI, data, runner, acceptance-command, and unrelated dirty paths remain
unstaged and untouched.
