# CEX-002 Coinalyze Provenance Source Acceptance

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_ACCEPTED_INTEGRATION_VALIDATION_AND_SIZING_RETRY_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022 and ADR-0023
**Gate 1:** Accepted
**Gate 2:** Not accepted; corrected sizing measurement remains pending

## Accepted correction

Claude's review-224 source/test drop is accepted for integration at these exact identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `bcaca1b1907a89df5020cdbd33c44f49471ff67d0c97d1a303c8225c2cabb592` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `0a9a3cf0978b596130323e36e495e4fa4d0bc018f21a6d44341e8b9e3bab8177` |

The sizing CLI remains unchanged at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.
The corrected test file contains 71 `def test_` functions. The eight added functions
expand to 26 focused cases, so the expected complete focused collection is 153 cases.

The production correction replaces the invalid serialized-substring rule with explicit
structure:

- exact boolean proof of header-only authentication at the accepted report block;
- the exact ten-field retained provenance schema;
- the exact safe header-name list `api_key`, without accepting a header-value field;
- string-to-string query parameters with case/underscore/hyphen-normalized credential
  parameter rejection; and
- structural-only failure contexts that do not serialize rejected values or records.

All prior endpoint-role, cache confinement, content-address, digest, byte-size, and body
checks remain. No network or credential access was added. The test fixture now has the
real accepted provenance shape and no dead credential branch. It covers altered framing,
wrong/missing/extra header names, credential query-name variants, unknown secret-bearing
fields without value echo, non-string parameters, successful evidence resolution, and
absence of request metadata from resolved evidence and the sizing receipt.

Claude edited only the two authorized paths and did not run commands or perform Git work.
The reviewer inspected the complete diff and restricted whitespace check. Per repository
roles, executable validation remains Hermes's responsibility.

## Hermes integrated sequence

Jr Dev - Hermes is authorized for one bounded sequence. Do not pull, reset, checkout,
restore, or stash in the shared dirty workspace.

Before any write, prove:

- `HEAD == origin/main` at this review's publication commit;
- only the two accepted sizing paths differ from `HEAD` among sizing source/test/CLI;
- all three hashes equal the identities above;
- receipt `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and
  `data/cex002_qualify/evidence/sizing/v1/envelopes/sha256/` remain absent;
- the complete `data/cex002_qualify` store still has 41,372 files and manifest SHA-256
  `f2522d5a3f3152880d42e4e85ead2e5ae64c6d635293ad2ef35c3437025d4ead`;
- the report, manifest, lock, amendment ledger, qualification source/CLI, progress and
  listing checkpoints, metadata, sample plan, retry journal, and legacy ledger retain the
  exact record-223 identities; and
- no qualification or sizing process is running.

Any mismatch stops before execution. Snapshot hashes, sizes, store-file manifest, and
available bytes. Then run exactly:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
focused_status=$?

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
ruff_status=$?
```

Both commands must exit 0, the focused suite must collect exactly 153 cases, and the three
paths must retain their accepted hashes. Any failure ends authorization: do not edit,
retry, execute sizing, or substitute an artifact.

If and only if both validations pass, run the exact first local sizing invocation:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

Do not load `.env` or request network. Any nonzero status ends authorization with no retry
or repair. If and only if the first invocation exits 0, snapshot the complete store and
receipt, then run the identical sizing command exactly once more. The second invocation
must reuse all sizing envelopes, reproduce the receipt bytes, create no additional
persistent artifact, and change no existing persistent file.

## Record and publication

Publish `research/sprint_004/226_CEX002_CORRECTED_SIZING_EXECUTION.md`. Record the exact
preproof, commands, timestamps, durations, statuses, and complete transcripts. On a
validation or sizing failure, record the failure, prove the evidence store and sizing
outputs were unchanged as applicable, update controls to `AWAITING_REVIEW`, publish the
authorized integration paths, and stop.

On successful sizing, record every receipt fact required by review 222, including all 12
family measurements and rational witnesses; Coinalyze mappings, lifecycle, raw and
normalized projections; the 56/68/5/73/73/5,225,416 retained decomposition; every capacity
component; exact total future bytes in decimal GB and binary GiB; available bytes, reserve,
shortfall and state; every envelope identity; and the second-run byte-for-byte idempotence
proof.

For success, stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`;
4. `research/sprint_004/226_CEX002_CORRECTED_SIZING_EXECUTION.md`;
5. `docs/handoff/CURRENT_TASK.md`; and
6. `tickets/CEX-002.md`.

For failure without a valid receipt, omit path 3 and stage the other five. Sizing envelopes
are ignored evidence and must never be staged. Run repository control and whitespace
validation restricted to the publication paths, commit, push, prove
`HEAD == origin/main`, and stop for reviewer inspection. Do not stage or alter any
unrelated dirty, database, DEX, BitMEX, catalog, ingest, fixture, or other data path.

This reviewer-authored governance publication is restricted to exactly:

1. `research/sprint_004/225_CEX002_COINALYZE_PROVENANCE_SOURCE_ACCEPTANCE.md`;
2. `docs/handoff/CURRENT_TASK.md`; and
3. `tickets/CEX-002.md`.

## Stop boundary

This authorizes only exact source/test integration, focused validation, corrected local
sizing, one conditional idempotence run, evidence recording, and exact-path publication.
It authorizes no source repair, network, bulk acquisition, Gate-2 acceptance by Hermes,
normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff analysis,
PAPER, LIVE, paid data, reduced scope, or next-ticket work. Next ticket remains `NONE`.
