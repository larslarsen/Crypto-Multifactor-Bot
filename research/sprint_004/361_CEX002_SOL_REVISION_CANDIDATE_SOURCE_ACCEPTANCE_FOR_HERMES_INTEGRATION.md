# CEX-002 Sol Revision-Candidate Source Acceptance for Hermes Integration

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact source/test drop accepted for bounded Hermes integration
- **Source actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Next actor:** Jr Dev - Hermes
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted identities

The reviewer accepts exactly these unintegrated paths and identities:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - 5,084 lines
  - SHA-256 `b8c60212ababc9f620afcf71725cac00f9f2893408f3f12f5fb947670cd03e86`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
  - 87 lines
  - SHA-256 `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - 2,518 lines and 57 test functions
  - SHA-256 `706f1affb6d9fcb07b81d8deef47a3dabe3a4b12f122dc64b34f68fb32a6ffed`;
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_book_ticker_page.xml`
  - SHA-256 `dd53323a7fcab0c39c8dd8d4824446fddc95b993c44671ead27144b064d84569`;
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_metrics_page.xml`
  - SHA-256 `d96c6713a29694264d5f3232bc04e085840b19d96d7f673e246ed36f473c5947`;
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/sidecar_btc_metrics.CHECKSUM`
  - SHA-256 `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55`.

Any byte change requires a new reviewer decision. All unrelated modified and untracked paths are
excluded and must remain unstaged and unchanged.

## Acceptance basis

The final Sol correction ran exactly:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

It exited zero with all 109 collected cases passing and no warning or traceback:

```text
........................................................................ [ 66%]
.....................................                                    [100%]
```

The reviewer independently confirmed the exact identities and statically inspected the final
iterator-ownership correction. `_write_private_gzip()` closes its supplied current-authority
iterator on all exits while SQLite remains live. Completed-manifest authentication likewise owns
and closes both the bounded gzip iterator and expected current-authority iterator. It does not
suppress cursor errors.

The complete source now provides the bounded ADR-0031 measurement planner required before any
replacement acquisition: exact generation-0/state/schema/code/pending/charge proof, held
descriptor roots and SQLite snapshot, two independently retrieved request-bound listing passes,
bounded resumable checkpoints and response pages, exact sidecar ETag/checksum authority,
deterministic manifest/lineage/receipt publication, immutable no-replace locator commit,
completed-tree recovery authentication, receipt-claim recomputation, explicit manifest stream
ceilings, and race/collision refusal. The production-shaped test covers 50,921 metrics rows, 354
book-ticker rows, and the exact 569/1,707/202 Coinalyze charge/transition/gap predicates without
collecting the pending stream in memory.

This accepts source for integration only. It does not accept a real revision candidate, authorize
the planner, approve acquisition, mutate generation 0, or pass Gate 2.

## Hermes integration authorization

Hermes must first rehash all six accepted paths and stop on any mismatch. It may then stage only
those paths. It must run exactly these validation commands against the staged source:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate docs/handoff/CURRENT_TASK.md research/sprint_004/362_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and does not patch developer source/test bytes. If every
command exits zero, Hermes creates exactly
`research/sprint_004/362_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md` with the accepted hashes,
commands, complete outputs, exit codes, collected count, clean-warning status, and scoped staged
path list. It updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to keep CEX-002
`IN_PROGRESS`, name the reviewer as next actor, keep next ticket `NONE`, and explicitly state
that real planner/acquisition execution remains unauthorized.

Hermes then stages exactly the six accepted developer paths plus record 362, `CURRENT_TASK.md`,
and `tickets/CEX-002.md`; verifies the staged path list contains nothing else; commits; pushes
`main`; proves `HEAD == origin/main`; and stops for reviewer inspection. It may use only the Git
commands mechanically necessary for those exact actions. It must not stage, edit, delete, clean,
or otherwise disturb any unrelated dirty path.

No network request other than the authorized Git push is permitted. No standalone planner/CLI,
candidate listing, real SQLite/data open, acquisition, cleanup, migration, generation transition,
Gate 3, model, or next-ticket work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/361_CEX002_SOL_REVISION_CANDIDATE_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`;
  and
- `tickets/CEX-002.md`.

The accepted developer paths remain unintegrated until Hermes publishes them. Real state/data,
implementation evidence, and all unrelated dirty paths are excluded.
