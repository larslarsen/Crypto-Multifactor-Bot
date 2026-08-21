# CEX-002 Plan-3 Candidate Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Plan-3 candidate source integration

Subject review: `research/sprint_004/103_CEX002_PLAN3_CANDIDATE_SOURCE_ACCEPTANCE.md`

## Outcome

**SOURCE INTEGRATION COMMITTED AND PUSHED. FOCUSED COMMAND 1 FAILED (EXIT 1, 12 OF
189 TESTS). THE CANDIDATE-ONLY REAL COMMAND WAS NOT RUN. THE FAILURE IS RECORDED
VERBATIM PER REVIEW 103 AND THE USER DIRECTION TO STOP ON FAILURE/EXIT 1.**

Review 103 accepts three source/test paths for Jr integration and one candidate-only
real execution. The three accepted hashes matched the integrated working tree exactly and
were committed as `f257a35`. The focused suite then failed at command 1 with 12 failing
tests, so per review 103 ("Any failure stops before the real candidate run and is recorded
verbatim in record 104") and the owner-relayed stop-on-failure direction, the
candidate-only command was not invoked and no pre/post authority, raw-tree, amendment, or
report evidence was produced.

## Verified identities

Committed control-plane base at integration: `HEAD == origin/main == e3a9f31` (reviewer
governance publication "accept CEX-002 plan 3 candidate source", which touched only
`docs/handoff/CURRENT_TASK.md`, review 103, and `tickets/CEX-002.md`; it did not modify
the three source/test paths).

After the Sr Dev source drop was present in the working tree, all three review-103
accepted hashes matched before integration:

| Path | Expected (review 103) | Observed (pre-commit) |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee142aabf0a3df589940ab982ff0087f9deacc593517fe856af9760a900c5bcd` | match |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `7c60f4d5bd7eacf9f0b85bac4a5d356106d035a5613e2a4e38163697906822d8` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `6b3949e6e428e85e14febaf6a6725c487975da3e8421e206ed904442f08f7f1e` | match |

Fixture directory `tests/acquisition/fixtures/binance_usdm_harmonic_qualification` was
clean (`git status` shows no modification and no untracked file inside it).

## Source integration commit

Staged exactly the three accepted Python paths (no unrelated dirty path, fixture, data
file, report, control file, or database sidecar):

- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`

Commit: `f257a35c` — "CEX-002: integrate plan-3 candidate source (review 103 accepted)"
(3 files changed, 3054 insertions, 341 deletions). Pushed; `HEAD == origin/main ==
f257a35cc6e57b84cc764d5674a2f2af186bddc8`. No restore, reset, checkout, stash, clean,
deletion, reconstruction, or relock was used.

## Focused Commands (review 103 order)

### 1. Focused CEX-002 suite — FAIL, exit 1
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
Collected 189, **177 passed, 12 failed, 1.75 s**, exit 1.

Failing tests (verbatim assertion summaries):

- `test_resume_refuses_tampered_content_addressed_bytes`: `assert first.samples` →
  `()` (samples empty).
- `test_derived_products_do_not_block_source_gate`:
  `assert authorities["binance_usdm_trade_flow_1h"] == "unsupported"` → got `'official'`.
- `test_identity_bytes_stable_across_resume`:
  `assert identity_bytes(first) == identity_bytes(second)` → diff at index 224
  `b'0' != b'6'`.
- `test_report_identity_matches_an_uninterrupted_run`:
  `assert identity_bytes(first) == identity_bytes(second)` → diff at index 224
  `b'0' != b'6'`.
- `test_abort_after_completed_sample_resumes_missing_objects_only`:
  `FileNotFoundError: .../cex002_qualification_progress.json` (resumed store path not
  created by the test's setup).
- `test_intact_sidecar_resumes_without_any_network_fetch`:
  `assert identity_bytes(first) == identity_bytes(second)` → diff at index 223
  `b'0' != b'3'`.
- `test_no_public_switch_can_reselect_the_locked_plan`:
  `assert "relock" not in source` → `'relock' is contained here: ... and no relock"` (the
  CLI `--help`/usage text now contains the substring "relock").
- `test_family_launch_gap_keeps_official_authority`:
  `assert trades.authority == "official"` → got `'inaccessible'`.
- `test_response_time_churn_replays_one_plan_and_keeps_identity`:
  `assert identity_bytes(first) == identity_bytes(second)` → diff at index 240
  `b'0' != b'3'`.
- `test_rejected_live_authority_does_not_poison_a_later_resume`:
  `assert identity_bytes(first) == identity_bytes(resumed)` → diff at index 240
  `b'0' != b'3'`.
- `test_missing_destination_raw_fetch_is_recorded_as_a_transfer`: `assert charges` →
  `{}`.
- `test_candidate_taker_flow_uses_reproved_retained_schema`:
  `assert flow.source_qualification_state != SOURCE_STATE_SAMPLE_PENDING` → got
  `'sample_evidence_pending'`.

### 2. Atomic-download suite — PASS, exit 0
`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
11 collected, 11 passed, exit 0.

### 3. Ruff — PASS, exit 0
`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
`All checks passed!`, exit 0.

### 4. Repo control — PASS, exit 0
`python3 scripts/check_repo_control.py` → `Repo control check: PASS`, exit 0.

### 5. Whitespace check — PASS, exit 0
`git show --check --oneline --no-renames HEAD` → no whitespace errors, exit 0.

## Candidate-Only Execution — NOT RUN

Command 1 failed, so per review 103 the candidate-only real command was not invoked:

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

No before-state evidence (lock SHA, budget-ledger SHA, raw-tree digest, amendment-ledger
absence, report SHA) was captured and none was re-measured, because the process never ran.
No candidate status code, report, or gate state was produced.

## No mutation occurred

No plan/ledger migration, sample download, amendment-ledger creation, Gate 2,
normalization, catalog publication, Nautilus execution, other-ticket work, or Harmonic
Trader work occurred. Only the three accepted Python paths were committed and pushed; the
verification commands are all read-only. The preserved store was not deleted, renamed,
replaced, reconstructed, or relocked. No secret value appears in this record; no `.env`
key was printed or placed in a command argument.

## Consequence

The accepted Plan-3 candidate source (review 103) does not pass its own focused suite:
12 of 189 tests fail. The failures span resume/tamper protection, derived-product
authority, `--help` text containing the substring "relock", family-launch-gap authority
regression (`inaccessible` instead of `official`), transfer-charge accounting, the new
candidate taker-flow sample-evidence state, and `identity_bytes` determinism across
resumed/interrupted/replayed runs (index 223–240 numeric digressions). The reviewer must
disposition the source defect (the accepted tests and production module are internally
inconsistent) before any candidate-only real execution. Gate 1 remains unpassed; next
ticket remains `NONE`.
