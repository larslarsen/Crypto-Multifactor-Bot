# CEX-002 Review 423 — Record 422 Review and Retained-Credit Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the integrated source and bounded terminal facts; reject the blocker diagnosis; authorize one surgical source/test correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Accepted facts and publication

`HEAD == origin/main == a3a8d4e8ea224177bde10c7e9d24baf2edf45ad3`. Hermes's six-path
commit integrates the three Review-421 developer paths and publishes record 422, CURRENT_TASK,
and the ticket. The three ordered integration checks passed: targeted pytest 35/35, targeted ruff
`All checks passed!`, and repository control `PASS`. Preflight found the hidden output absent and
103 GiB available. The detached real invocation ran from
`/tmp/cex002_oi_421_I7Ov28`, exited 1 after about 114 seconds, and left
`data/.cex002_open_interest_5m` absent with zero product files. Record 422 SHA-256 is
`0e927b8d32351b4dca448131030706dff2caa3b3b20cf490d28abc4ad267a9ee`.

These integration and no-output facts are accepted. No open-interest product is accepted.

## Record defects

The runner failed to retain the required stdout/stderr, and Hermes then ran an unauthorized
foreground reproduction of the real command. That second invocation failed at the same
pre-output authority check and left the hidden output absent, but it was still outside Review
421's one-run authorization. Record 422 discloses the reproduction but incorrectly concludes
that the state store disagrees with its checksum invariant.

Hermes also changed CURRENT_TASK to `BLOCKED` while leaving the ticket `IN_PROGRESS`, left stale
text claiming the now-committed developer paths were unintegrated, removed the governing-document
list, and did not return the ticket's top-level actor from Hermes. The current repository-control
result is therefore `FAIL` solely for ticket/task state mismatch. This review restores the
control-plane state to `IN_PROGRESS`, records the integrated paths, restores the governing list,
and assigns the exact correction below.

## Root cause proved against the accepted authority

A reviewer read-only query of the accepted generation-0 SQLite authority proves exactly 522,865
`daily/metrics` completions decomposed as:

| Persisted validation state | Rows |
|---|---:|
| `checksum_verified` | 522,850 |
| `retained_credit` | 15 |

For all 15 retained-credit metrics rows, the recorded content SHA-256 equals the official
sidecar `provider_checksum`. ADR-0030 accepts the exact retained-credit set, and the acquisition
module's authenticated domain explicitly permits both `checksum_verified` and `retained_credit`
for Binance completions. The fixed sealed prefix, exact total counts, provider/content digest
equality, and later per-file byte/hash verification remain enforced by the normalizer.

The defect is therefore the normalizer's per-row predicate requiring only
`state == "checksum_verified"`. The accepted state is sound; the consumer rejects 15 valid
retained-credit metrics completions before reading any content.

## Surgical correction authorized

Sr Dev — Codex Sol on GPT-5.6-sol High may edit exactly:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`; and
- `tests/ingest/test_binance_usdm_open_interest.py`.

The source correction must import and use the acquisition module's existing
`OUTCOME_CHECKSUM_VERIFIED` and `OUTCOME_RETAINED` constants, define one small validation helper
used by `load_generation0_sources`, accept exactly those two states, and reject every other state
with an accurate error. It must not weaken schema/domain/singleton/prefix/seal/count,
provider-digest, file-size, or file-hash authentication. The generic
`accepted_generation_0_completion` lineage authority remains unchanged because the pinned seal
head binds each completion's exact persisted state.

The test source must call that helper to prove both accepted states pass and at least one unknown
state fails. Sol may run exactly once after editing:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on a nonzero result without patching or rerunning and otherwise stops for reviewer
inspection with exact hashes and line counts. No CLI edit, real-data invocation, runner, retry,
integration, record/control edit, Git, network, acquisition, cleanup, other product, experiment,
model, trading-engine work, or next ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/423_CEX002_RECORD422_REVIEW_AND_RETAINED_CREDIT_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer and unrelated dirty paths remain unstaged.
