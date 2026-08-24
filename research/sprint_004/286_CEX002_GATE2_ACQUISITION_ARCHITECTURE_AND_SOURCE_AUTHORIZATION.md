# CEX-002 Gate 2 Acquisition Architecture and Source Authorization

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** attestation 282 accepted; Gate-2 source drop authorized
- **Authorized actor:** Sr Dev - Grok Build, Grok 4.6 High
- **Gate 2:** in progress; raw acquisition not yet accepted
- **Next ticket:** `NONE`

## Capacity evidence acceptance

Record 283 and commit `75d505b786daa25db0e7f1f2c0f08b986c5205a0` are accepted as
faithful review-281 integration and execution. The accepted capacity source, CLI, and
15-test source identities are unchanged. Focused pytest and Ruff each passed once, and
the one authorized real command exited 0 in 1.323 seconds.

Attestation 282 is accepted at SHA-256
`0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25`,
3,794 bytes, on `dev:64513`. Its self identity, receipt-258 identity, five stable
components, reserve, total, device, and post-publication measurement independently
reconcile. The stable requirement is 139,577,980,018 bytes; the current reserve is
57,891,047,015; total requirement is 197,469,027,033; post-publication availability is
289,455,230,976. State is `sufficient`, blockers are empty, and measured headroom is
91,986,203,943 bytes.

This accepts the storage precondition only. No raw object has been acquired by this
decision and Gate 2 is not accepted.

## Architecture decision

ADR-0029 is accepted. The complete Gate-2 engine uses the exact 736,347-object Binance
requirement and 570-logical-receipt Coinalyze requirement. It uses a hash-bound immutable
plan, sharded content-addressed streaming publication, a transactional SQLite progress
store, monotone completion, bounded concurrency/retries, header-only secret handling,
immutable run receipts, and a full terminal verifier. It has no price-only, tick,
full-book, scope-filter, normalization, or model path.

The reviewer verified the authority facts directly from the accepted repository:

| Fact | Accepted value |
|---|---:|
| Main selected objects | 733,203 |
| Main selected bytes | 7,833,966,625 |
| Complete cost objects | 3,144 |
| Complete cost bytes | 12,522,974,218 |
| Combined Binance objects | 736,347 |
| Combined Binance bytes | 20,356,940,843 |
| Re-proved retained credit | 73 objects / 5,225,416 bytes |
| Projected new Binance raw | 20,351,715,427 bytes |
| Coinalyze supported mappings | 569 |
| Coinalyze unsupported typed gaps | 202 |
| Coinalyze logical receipts | 570 |
| Projected new Coinalyze raw | 30,580,702 bytes |

The official Coinalyze API documentation at `https://api.coinalyze.net/v1/doc/`, checked
2026-08-23, currently declares a maximum of 20 symbols per request, 40 API calls per
minute per key, and indefinite daily-history retention. The accepted one-symbol request
shape is therefore valid and conservative. Repository authority remains the frozen
retained inventory and report, never the current website or a newly fetched inventory.

## Authorized source drop

Grok Build is authorized to implement exactly these three new paths:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Do not edit any existing qualification, sizing, capacity, `source_audit`, package export,
fixture, evidence, ticket, handoff, ADR, configuration, or unrelated path. Existing dirty
work is out of scope and must not be restored, stashed, checked out, reset, or staged.

### Production contract

Implement ADR-0029 completely in the new production module and thin CLI. The code must:

1. pin and fully revalidate report 62, manifest detail, cost manifest, receipt 258,
   attestation 282, the receipt-bound checkpoints/metadata/lock/ledger/source identities,
   accepted counts/bytes/families/sets, holdout, and current same-device capacity before
   installing or running a plan;
2. consume the main manifest only after the authenticated `iter_manifest_detail`
   contract has fully validated it, and resolve/re-prove all 3,144 cost keys from the
   retained listing checkpoint/cache with exact sizes, ETags, digest, and zero overlap;
3. derive all 569 native/provider Coinalyze mappings from the rehashed retained inventory,
   use authenticated lifecycle bounds and the fixed cutoff, preserve the 202 exact
   unsupported gaps, and never use the two anchors or current inventory as the universe;
4. create a deterministic semantic plan and compact no-replace plan receipt without
   copying the full input manifest into another authority artifact;
5. create/open only the fixed-version single-plan SQLite state described by ADR-0029,
   with no-follow locking, full durability, monotone completion, append-only attempts,
   one writer, deterministic state digest, and rejection of a different plan or corrupt
   state;
6. stream sidecars and raw responses to private same-device files, publish no-replace
   one-byte-sharded SHA-256 content paths with file/directory fsync, and record completion
   only after content is durable;
7. prove exact Binance sidecar basename/checksum, listed bytes, raw SHA-256, safe readable
   ZIP membership and CRC, while leaving economic parsing to Gate 3;
8. use a fixed bounded pooled worker/queue ceiling, deterministic retry classes/backoff,
   bounded `Retry-After`, graceful object/time/signal stops, and restart recovery without
   a completed-object refetch;
9. make Coinalyze header-only, one-symbol daily, fixed-range, rate-limited, redacted,
   exact-decimal, symbol/time/order/value validated, and hard-bounded by the accepted new
   raw allocation; preserve empty/unavailable responses as typed outcomes rather than
   zero data or silent deletion;
10. revalidate the full unchanged ADR-0028 stable requirement and dynamic current reserve
    throughout acquisition, with no progress credit or capacity override;
11. publish immutable content-addressed run receipts for bounded invocations and an
    offline full terminal manifest/receipt verifier; and
12. return explicit distinct exit states for complete, resumable partial, complete with
    typed terminal gaps, capacity blocked, authority invalid, and unsafe/corrupt state.

The CLI must provide only `plan`, `acquire`, and `verify` operations plus location and
operational stop-bound arguments. `acquire` may expose `--max-objects` and
`--max-wall-seconds`; it must not expose symbol/family/product/date filters, worker or
rate-limit overrides, economic settings, authority hashes, capacity coefficients,
secret values, force/reset/skip flags, or a false-success switch. Network is impossible
from `plan` and `verify`.

### Test-source contract

Use synthetic transports and temporary roots only. Tests must cover at least:

- every pinned authority/count/byte/set boundary and single-field tamper rejection;
- full manifest validation before the first network call, exact cost resolution/digest,
  disjoint 736,347-object reconciliation, and no forbidden family;
- exact 569/202 Coinalyze mapping/gap projection, anchor non-substitution, lifecycle and
  cutoff binding, and current-inventory non-authority;
- deterministic plan identity, incompatible-plan refusal, SQLite schema/lock/durability,
  one-writer behavior, and corrupt-state rejection;
- content sharding, no-replace collision checks, symlink/path/device refusal, fsync order,
  exact size/checksum/ZIP/CRC validation, and partial cleanup;
- crash points before/after sidecar publication, raw publication, and database commit,
  including orphan adoption and zero completed-object refetch;
- concurrency/queue ceilings, deterministic retry classification, 429 handling,
  graceful bounds/signals, and no partial promotion;
- Coinalyze rate limit, request identity, exact decimal/time/symbol validation,
  empty/unavailable typed outcomes, cumulative byte ceiling, and secret sentinel absence
  from URLs, database bytes, receipts, logs, and exceptions;
- rolling unchanged stable-capacity guard and stop-before-transfer behavior; and
- deterministic run/terminal receipts, semantic state digest, full verify reconciliation,
  zero-download replay, and honest exit states.

Tests must prove production paths, not only helper functions or mocks disconnected from
the CLI/engine. They must remain bounded and perform no real network or accepted-data
mutation.

## One targeted senior test

After the complete three-path drop is written, Grok may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On a nonzero result or timeout, stop without a repair or rerun and report the exact
command/output/status. Run no Ruff, control, qualification, sizing, capacity, plan,
acquisition, verify, network, or other command. Use no Git. Do not create or mutate the
real SQLite state, raw store, plan receipt, run receipt, or terminal receipt.

Stop once with the three SHA-256 hashes, test-function count, targeted command result,
and confirmation that only the three authorized paths changed. This authorization is for
source and test-source creation only. Hermes integration, real planning, network
acquisition, replay, evidence records, Git, commit/push, Gate-2 acceptance, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and next-ticket work
remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, ADR-0029, current task, and
ticket. Developer source/test paths, real state/data/evidence, and unrelated dirty work
are excluded.
