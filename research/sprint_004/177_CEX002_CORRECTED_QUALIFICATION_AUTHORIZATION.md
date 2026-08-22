# CEX-002 Corrected Qualification Authorization

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/176_CEX002_AUTHORITY_TRANSACTION_EXECUTION.md`

Architecture decision: `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`

## Decision

**ACCEPT THE SOURCE-AUTHORITY TRANSACTION; CORRECT REVIEW 175'S RECEIPT-COUNT WORDING;
AUTHORIZE JR DEV - HERMES FOR ONE BOUNDED CORRECTED ORDINARY QUALIFICATION RUN.**

Hermes ran exactly one correction-only invocation without `.env`, network permission,
retry, recovery, qualification, report publication, or sample work. It exited zero. The
receipt, live JSON, preserved predecessors, exact structural comparisons, and deterministic
tree snapshots prove that only the reviewed source-identity transform occurred.

Review 175 incorrectly required that "exactly one source receipt exists" after the
transaction. The accepted migrated pre-state already contained one receipt for production
`ee9a794d...`; ADR-0020 section 4b requires the correction to append the new receipt for
production `068763e2...`. The correct postcondition is **two total receipts, exactly one
new receipt appended**. Record 176 reports that architecture-correct state. This was a
reviewer-authored evidence-count error, not an implementation or execution defect.

Commit `3948fab309150375fb573dc0add22a2d97640ad2` contains exactly record 176 and the
two controls and is on `origin/main`. The reviewer ran static JSON, hash, and Git checks
only; no test, acceptance, network, qualification, or data-mutation command was run.

## Accepted corrected authority

| Evidence | Accepted identity |
|---|---|
| production source | `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e` |
| CLI source | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| 305-test source | `4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0` |
| report 62 | 13,944,475 bytes / `53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51` |
| manifest detail | 11,292,635 bytes / `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| corrected version-4 lock | 426,276 bytes / `522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6` |
| corrected amendment ledger | 25,797 bytes / `832228fd2b4b9394e205a69441281ddbfccc92c227144c5c0c2b8181e164e488` |
| preserved prior lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| preserved prior amendment ledger | 25,223 bytes / `2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 395,626 bytes / `d6c327faa144e819ca6fd4c7b0325b4a39b3ecb7cf1daa2bfdb747b2f22e85ee` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 bytes / `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 bytes / `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 98,940 bytes / `19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8` |

The lock and ledger carry plan version 4, plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
executing code/config digest
`da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258`,
82 charges carrying 845,471 transferred bytes, two reservations carrying 203,853 planned
bytes, 1,049,324 charged bytes, and a 268,435,456-byte allowance.

## Preconditions and report preservation

Hermes proves `HEAD == origin/main` at this review's publication commit, all accepted
identities above, 305 tests, no running qualification process, matching two-receipt
lock/ledger bindings, exact accounting, and the record-176 raw/cache/evidence tree
identities. Any mismatch stops before network execution.

Before report 62 can be overwritten, Hermes preserves its exact accepted bytes at:

`data/cex002_qualify/evidence/prior_reports/sha256/53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51.json`

That destination is currently absent. Hermes uses a collision-safe temporary copy, never
a hard link, rehashes before atomic no-replace publication, and re-proves the final hash
and 13,944,475-byte size. Any collision or mismatch stops. The ignored evidence is never
staged.

Hermes snapshots report, manifest detail, corrected and preserved authority files, legacy
ledger, checkpoint, retry journal, sample plan, listing checkpoint, official metadata,
retained raw tree, list/FAPI/Coinalyze caches, and available bytes before execution.

## One corrected ordinary run

Hermes obtains network permission before launch and consumes no preliminary restricted-
sandbox attempt. It loads `.env` only into the child process environment and makes exactly
one foreground ordinary invocation, with neither correction, migration, nor candidate
mode:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
qualification_status=$?
```

Status 0 means a terminal report claims Gate 1 passed. Status 2 means a terminal report
still claims Gate 1 blocked. Status 124 is an incomplete timeout. Any other status is a
failure. Every status ends the authorization; Hermes does not retry, resume, correct,
recover, or launch a second command.

## Required after-proof

Hermes records timestamps, elapsed time, status, and the complete transcript, then proves:

- the current report is valid and compact, with exact hash/size, source blockers,
  release blockers, Gate-1 status, complete product matrix, typed gaps, and manifest-detail
  identity;
- the two formerly reserved cost objects' exact validation states and whether each
  reservation settled, without substitution or deletion;
- exact sample attempted/acquired/reused/failed counts and bytes, with no out-of-plan raw
  identity and no unapproved bulk acquisition;
- exact before/after lock, both ledgers, checkpoint, retry journal, plan, listing metadata,
  raw/cache/evidence trees, available bytes, and any network/cache mutation;
- the corrected authority binding and two source receipts remain exact; and
- the content-addressed prior report, prior lock, and prior ledger remain byte-identical.

Gate 1 is not accepted merely because the process exits zero. Reviewer inspection of the
new report and record remains mandatory. No test or acceptance command is rerun because
the exact code identities and complete C1-C5 result are already accepted.

## Publication and stop

Hermes writes `research/sprint_004/178_CEX002_CORRECTED_QUALIFICATION_EXECUTION.md` and
updates both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 178`.

For status 0 or 2 with a valid changed report, Hermes stages exactly both controls, report
62, and record 178. If the report is unchanged/invalid or execution times out/fails, it
stages exactly both controls and record 178. Data/evidence paths, source/tests, database
sidecars, and unrelated dirty paths are never staged. Hermes runs
`python3 scripts/check_repo_control.py` and `git diff --check`, commits, pushes, proves
`HEAD == origin/main`, and stops.

## Boundaries

No second invocation, source correction, migration, candidate construction, full-history
or bulk acquisition, Gate-1 acceptance by the owner or Hermes, Gate 2, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
