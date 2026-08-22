# CEX-002 Migration Network Failure Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/158_CEX002_MIGRATION_RUFF_INTEGRATION_AND_EXECUTION.md`

## Decision

**ACCEPT THE CLEANUP INTEGRATION AND ALL FIVE FOCUSED COMMANDS; ACCEPT THE PRE-TRANSACTION
NETWORK STOP; AUTHORIZE ONE DIRECT NETWORK-ENABLED MIGRATION-ONLY RETRY.**

Hermes integrated the exact review-157 test identity in commit
`21fb4ecfe7bf4600578838388c3e74a2a657e6a8` and pushed it. Publication commit
`7745f99d2eff7ee353f254559f71e84e721c4fc2` contains exactly the two controls and record
158. `HEAD == origin/main`, repository control passes, and all accepted source hashes
remain exact.

C1-C5 all returned exit 0. The reviewer accepts this post-integration focused evidence;
the retry does not rerun it.

The single migration-only invocation exited 1 after all five bounded `fapi:exchangeInfo`
attempts failed with restricted-environment DNS resolution errors. The failure occurred
before plan construction, prior-lock preservation, amendment-ledger preparation, or the
version-4 commit point. Hermes correctly performed no retry.

## Accepted post-failure state

The following state is accepted as the retry precondition:

| Evidence | Accepted identity |
|---|---|
| report 62 | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes / `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| version-2 lock | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 299,571 bytes / `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| amendment ledger | absent |
| retained raw tree | 186 files / 1,015,198,547 bytes |
| migration preflight | `not_started`, accepted plan digest `2fb0e47a...`, `download_authorized=false` |

The retry journal is preserved failure history. It must not be deleted, restored, or
rewritten before the next invocation. Every other review-151 precondition remains exact.

## One direct network-enabled retry

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit,
re-proves the accepted source hashes and complete table above, confirms no qualification
process is running, and re-runs the read-only migration preflight. Any mismatch stops.

Hermes then obtains network permission outside the restricted sandbox before starting the
process. It must not consume another sandboxed attempt first. With `.env` loaded only into
the process environment, it makes exactly one foreground invocation using review 151's
exact command and 50-minute timeout:

```bash
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-migration-only
```

Status 2 remains the expected terminal status after a successful migration. Every status
stops after this invocation. No further retry, ordinary resume, or second migration command
is authorized.

## After-proof and publication

Hermes performs every review-151 after-proof, records all mutations including the advanced
retry journal, and proves whether the version-4 lock/amendment transaction committed. It
writes `research/sprint_004/160_CEX002_MIGRATION_NETWORK_RETRY.md` with preconditions,
network authorization, timestamps, transcript, status, receipt, complete after-state,
mutations, deviations, and terminal state.

Hermes updates both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 160`, stages exactly the two controls and record 160,
commits and pushes, proves `HEAD == origin/main`, and stops. It never stages data, state,
cache, report, manifest detail, database sidecar, or unrelated dirty paths.

## Boundaries

No source/test edit, C1-C5 rerun, preliminary sandboxed attempt, further retry, ordinary
resume, second migration, sample acquisition, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, external
artifact service, reduced scope, or unrelated dirty-path mutation is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
