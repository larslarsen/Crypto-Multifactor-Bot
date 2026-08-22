# CEX-002 Authority Transaction Authorization

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/174_CEX002_AUTHORITY_TEST_INTEGRATION.md`

Architecture decision: `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`

## Decision

**ACCEPT THE TEST INTEGRATION AND COMPLETE C1-C5 RESULT; AUTHORIZE JR DEV - HERMES FOR
ONE LOCAL SOURCE-AUTHORITY TRANSACTION AND ITS EVIDENCE PUBLICATION.**

Hermes integrated only the accepted test path in commit `75385595d737e4499dd44e56f293410683e5b601`
and published only record 174 plus the two controls in commit
`b1096915d7db1362857b07f6757b69e0d8e5acd3`. Both commits are on `origin/main`. The
production, CLI, and 305-test hashes match review 173. C1-C5 all exited zero, the recorded
commands and stop boundaries match review 173, and neither commit contains an unrelated
path.

The ignored live store remains in the exact fresh state pinned by ADR-0020 section 4b:

| Evidence | Accepted identity |
|---|---|
| report 62 | 13,944,475 bytes / `53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51` |
| version-4 lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| amendment ledger | 25,223 bytes / `2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 395,626 bytes / `d6c327faa144e819ca6fd4c7b0325b4a39b3ecb7cf1daa2bfdb747b2f22e85ee` |
| sample plan | 51,124 bytes / `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| listing checkpoint | 33,206,753 bytes / `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 98,940 bytes / `19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8` |
| manifest detail | 11,292,635 bytes / `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |

The two transaction evidence destinations are absent. No mixed or partial correction
state exists. The reviewer performed static inspection and hash/Git checks only; no test,
acceptance, transaction, qualification, network, or data-mutation command was run.

## Hermes preproof

Hermes must first prove `HEAD == origin/main` at this review's publication commit, the
three accepted source hashes and 305-test count, no running qualification process, every
accepted live-store identity above, and absence of:

- `data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json`;
- `data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json`.

It snapshots exact hashes/sizes or deterministic tree identities for report 62, manifest
detail, both ledgers, lock, checkpoint, retry journal, sample plan, listing checkpoint,
official metadata, retained raw tree, and list/FAPI/Coinalyze caches. Any mismatch or
existing transaction evidence stops before invocation.

## One local transaction

Hermes runs exactly one foreground invocation, without loading `.env` and without network
permission:

```bash
timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-source-correction-only
transaction_status=$?
```

Status zero is the only success. Every other status ends this authorization. Hermes does
not retry, recover, invoke a second transaction, or enter ordinary qualification.

## Required after-proof

For status zero, Hermes records the complete receipt and proves:

- `transaction=cex002_reviewed_v4_source_correction`, `executed=true`, and
  `state=source_identity_advanced`;
- plan version 4 and plan digest
  `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef` remain exact;
- exactly one source receipt exists and the lock and ledger bind the same executing
  code/config identity;
- 82 charges carrying 845,471 settled transfer bytes, two reservations carrying 203,853
  planned bytes, 1,049,324 charged bytes, the 268,435,456-byte allowance, zero acquired
  samples, zero reconciled reservations, and `download_authorized=false`;
- the prior lock and amendment ledger now exist at the two content addresses above and
  rehash to their filenames;
- the live lock and amendment ledger have new exact hashes and differ from their accepted
  predecessors only by the reviewed source-identity receipt/binding transform; and
- every other pre-snapshot artifact and tree is byte-identical.

For any nonzero or interrupted result, Hermes records the exact resulting state and
mutations without attempting recovery. It must not infer success from partial evidence.

## Publication and stop

Hermes writes `research/sprint_004/176_CEX002_AUTHORITY_TRANSACTION_EXECUTION.md`, updates
the two controls to `Next required actor: Lead Quantitative Finance Researcher/Engineer -
inspect record 176`, runs `python3 scripts/check_repo_control.py` and `git diff --check`,
then stages, commits, and pushes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/176_CEX002_AUTHORITY_TRANSACTION_EXECUTION.md`;
- `tickets/CEX-002.md`.

Data/evidence paths, report 62, source/tests, database sidecars, and unrelated dirty paths
are never staged. Hermes proves `HEAD == origin/main` and stops.

## Boundaries

No network call, report write, sample acquisition, reservation reconciliation, ordinary
qualification, Gate-1 acceptance, Gate 2, bulk acquisition, normalization, catalog
publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid
source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
