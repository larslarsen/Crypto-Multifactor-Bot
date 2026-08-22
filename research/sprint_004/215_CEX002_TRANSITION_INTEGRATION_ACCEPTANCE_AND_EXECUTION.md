# CEX-002 Transition Integration Acceptance and Execution Authorization

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `INTEGRATION_ACCEPTED_TRANSITION_EXECUTION_AUTHORIZED`
**Architecture:** ADR-0022 and reviews 208-213 remain controlling
**Gate 1:** Source finding remains accepted; affected publication authority stays suspended
**Gate 2:** Not accepted

## Record-214 decision

Record 214 is accepted. Hermes committed and pushed exactly the three accepted transition
paths, record 214, and the two control files at
`6ab3cf0fb80c7ef7e8f05d9028832a09e96abece`. `HEAD == origin/main`, all three integrated
hashes equal review 213, repository control passed, and the exact six-path whitespace
check passed. Hermes correctly did not rerun pytest/Ruff or execute the transition.

## Current real pre-state

The reviewer performed read-only identity checks after integration. Every historical
artifact still matches review 208 exactly:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| report 62 | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| manifest detail gzip | 11,294,610 | `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4` |
| version-4 lock | 426,276 | `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6` |
| amendment ledger | 26,103 | `259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0` |
| legacy ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,357 | `e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f` |

The manifest path is
`data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz`.
All four new report/checkpoint/lock/ledger evidence destinations are absent. The accepted
transition source, CLI, and tests remain at review-213 hashes.

## Hermes execution authority

Jr Dev - Hermes is authorized to execute exactly this command from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py --store-root data/cex002_qualify --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

If it exits zero with `executed=true`, run the identical command exactly once more. The
second receipt must report `executed=false`, the same final lock/ledger identities, three
source receipts, and zero sample work. Stop immediately on either nonzero exit; do not
retry a failure or run the second command after a first-command failure.

Publish `research/sprint_004/216_CEX002_PATH_BOUND_TRANSITION_EXECUTION.md` with:

- the exact preproof hashes and evidence-destination absence;
- each command verbatim, exit status, duration, and full receipt/status output;
- the four preserved evidence paths and hashes;
- final lock and amendment-ledger sizes/hashes and exact target source identity;
- proof that the legacy ledger, report, manifest, checkpoint, retry journal, sample plan,
  listing checkpoint, metadata, and accepted source paths remain byte-identical;
- proof that the second successful command changed no store file; and
- the exact Git scope and final `HEAD == origin/main`.

Update only `docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, and record 216 for reviewer
inspection. Run repository control and a whitespace check over those three paths. Commit
and push only those three repository paths. The live authority/evidence files are
gitignored data outputs and must never be staged.

## Stop boundary

This authorizes only the isolated identity transition and its one idempotence recheck. It
does not authorize ordinary qualification, sizing source change or retry, acquisition,
normalization, catalog publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE,
paid-source, reduced-scope, or next-ticket work. Gate 2 remains unaccepted and next ticket
remains `NONE`.
