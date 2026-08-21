# CEX-002 Plan-3 Candidate Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Plan-3 candidate execution halted

Subject review: `research/sprint_004/109_CEX002_RESIDUAL_CORRECTION_SOURCE_ACCEPTANCE.md`

## Outcome

**FOCUSED COMMAND 1 FAILED (EXIT 1, 2 OF 189 TESTS). THE CANDIDATE-ONLY REAL COMMAND WAS NOT RUN. THE FAILURE IS RECORDED VERBATIM PER REVIEW 109 AND THE STOP-ON-FAILURE DIRECTION.**

Source integration `b062f1b` committed and pushed. All accepted/frozen hashes matched (src `23e25e6...`, tests `4ef66b0...`, frozen CLI `7c60f4d5...`). The focused suite then failed at command 1 with 2 failing tests, so per review 106/109 ("Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list and must not run the real candidate process after a failure. It records the failure in record 110 exactly as observed") and the owner-relayed stop-on-failure direction, the candidate-only command was not invoked and no pre/post authority, raw-tree, amendment, or report evidence was produced.

## Verified identities

Committed control-plane base at integration: `HEAD == origin/main == b062f1b` (reviewer governance publication "accept CEX-002 residual correction source", which touched only `docs/handoff/CURRENT_TASK.md`, review 109, and `tickets/CEX-002.md`; it did not modify the two source/test paths).

After the Sr Dev source drop was present in the working tree, all three review-109 accepted hashes matched before integration:

| Path | Expected (review 109) | Observed (pre-commit) |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `23e25e6f63189a7b381450f7b7fd0187a78da6ca169eff1d4acdf588b0b75daf` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4ef66b0e527e890956075d7565601821eed7fab59307a11339d4e1afffb7e692` | match |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` (frozen) | match |

Fixture directory `tests/acquisition/fixtures/binance_usdm_harmonic_qualification` was clean (`git status` shows no modification and no untracked file inside it).

## Focused Commands (review 109 order)

### 1. Focused CEX-002 suite — FAIL, exit 1
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
Collected 189, **187 passed, 2 failed, ~1.76 s**, exit 1.

Failing tests (verbatim assertion summaries):

- `test_report_identity_matches_an_uninterrupted_run`: `assert identity_bytes(clean) == identity_bytes(second)` → diff at index 28601 `b'c' != b'r'`.
- `test_abort_after_completed_sample_resumes_missing_objects_only`: `assert identity_bytes(resumed) == identity_bytes(clean)` → diff at index 31139 `b'r' != b'c'`.

### 2. Atomic-download suite — NOT RUN
Per review 109: "Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list."

### 3. Ruff — NOT RUN
Per review 109: "Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list."

### 4. Repo control — NOT RUN
Per review 109: "Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list."

### 5. Whitespace check — NOT RUN
Per review 109: "Any nonzero exit stops immediately. Hermes must not run any subsequent command in the list."

## Candidate-Only Execution — NOT RUN

Command 1 (focused suite) exited with exit 1. Per review 109 the candidate-only real command was not invoked:

```bash
set -a
. ./.env
set +a
.venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
  --store-root data/cex002_qualify \
  --progress-path data/cex002_qualify/cex002_qualification_progress.json \
  --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --candidate-plan-only
```

No before-state evidence (lock SHA, budget-ledger SHA, raw-tree digest, amendment-ledger absence, report SHA) was captured and none was re-measured, because the process never ran. No candidate status code, report, or gate state was produced.

## No mutation occurred

No plan/ledger migration, sample download, amendment-ledger creation, Gate 2, normalization, catalog publication, Nautilus execution, other-ticket work, or Harmonic Trader work occurred. Only the two accepted Python paths were committed and pushed; the verification commands are all read-only. The preserved store was not deleted, renamed, replaced, reconstructed, or relocked. No secret value appears in this record; the API key was loaded only from `.env` and never printed or placed in a command argument.

## Consequence

The accepted Plan-3 candidate source (review 109) does not pass its own focused suite: 2 of 189 tests fail. The failures are in `identity_bytes` determinism across resumed/interrupted/replayed runs (index 28601 and 31139 character digressions). The reviewer must disposition the source defect (the accepted tests and production module are internally inconsistent) before any candidate-only real execution. Gate 1 remains unpassed; next ticket remains `NONE`.