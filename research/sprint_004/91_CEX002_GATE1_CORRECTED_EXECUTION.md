# CEX-002 Gate 1 Corrected-Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Gate 1 source procurement

## Outcome

**COMMANDS 1–5 PASSED. REAL RUN 1 EXITED 1 AT THE IMMUTABLE-PLAN GATE AND STOPPED
IMMEDIATELY. NO REPORT, NO SECOND RUN, NO SEMANTIC COMPARISON.**

Review 90: "Exit 1 stops immediately." The accepted production change
(`e2dd17fc…`) changes the qualifier's `code_config_digest`, which no longer matches the
digest recorded in the preserved plan lock. The locked Gate 1 plan (version 1) therefore
refuses to run: "locked Gate 1 plan inputs changed; a new plan version requires a fresh
reviewer authorization". This is the intended fail-closed immutable-plan protection. A
new plan version can only be established under fresh reviewer authorization.

## Verified identities

Committed control-plane base: `HEAD == origin/main == c28b78fb3cc5a078ac96e26e9bb655946084b915`.

Both review-90 accepted hashes matched before execution:

| Path | Expected (review 90) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `e2dd17fc71884bc83703f1609383e6b79eec60b54da30382f5a163b85f8bcd6a` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5df4511baaf8b31938af1972430451f3012058fe2bc0da42b88a228c2fafc6f0` | match |

## Command sequence (review 90 order) — all PASSED

### 1. Focused CEX-002 suite — PASS, exit 0
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
148 collected, 148 passed (progress dots: 72 / 72 / 4).

### 2. Atomic-download suite — PASS, exit 0
`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
11 collected, 11 passed.

### 3. Ruff — PASS, exit 0
`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
`All checks passed!`

### 4. Repo control — PASS, exit 0
`python3 scripts/check_repo_control.py` → `Repo control check: PASS`

### 5. Whitespace check — PASS, exit 0
`git show --check --oneline --no-renames HEAD` → no whitespace errors.

## Bounded real execution

### First run — EXIT 1, IMMEDIATE STOP, 622 s

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_stable_corrected_first.json; echo "R1_EXIT=$?" > /tmp/cex002_r1_exit.txt'
```

Raw process exit status captured: **1** (recorded from the wrapper).

Terminal log (only two lines; the run stopped at the plan gate before listing,
membership, plan, storage, or sample work):

```
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 unclaimed=0
ERROR: locked Gate 1 plan inputs changed; a new plan version requires a fresh reviewer authorization | context={'kind': 'plan_inputs_changed', 'path': 'data/cex002_qualify/cex002_sample_plan_lock.json', 'plan_version': 1, 'changed': ['code_config_digest']}
```

No report was produced (`/tmp/cex002_gate1_stable_corrected_first.json` does not exist).
Per review 90, exit 1 stops immediately: the second run and the semantic
`drop_identity_volatility` comparison were **not** executed.

### Second run — NOT EXECUTED

Review 90: "Exit 1 stops immediately." No second report exists. `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` is unchanged from the prior accepted publication (record 88, SHA-256 `ca9bb5f1bc10d74fb0c983af790074d0b6f724a26eeef5dbff6b6eb804822e42`).

## Plan-lock identities (blocking context)

`data/cex002_qualify/cex002_sample_plan_lock.json` (SHA-256
`45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf`):

- kind: sample plan lock; version 1; plan_version 1
- plan_digest: `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`
- locked_at: `2026-08-20T19:57:15.916435+00:00`
- budget_snapshot: allowance_bytes_at_lock 0; budget_bytes 268,435,456;
  cumulative_spent_max_bytes_at_lock 1,015,198,547; max_object_bytes 67,108,864
- inputs:
  - budget_digest: `b4700c55a60a8fdcb279df60ce14509cefd67ab66e1146feabc0c74ce595adb5`
  - code_config_digest: `9845375eb2a5f0f83917fc47fd2b25a5463c2ad9979ffb06f183d27f452fe663`
  - inventory_digest: `effe02bdcab8dd287625c4c5c4416b7bb743e1635229d2ae465dd2f6d78aa9b8`
  - listing_digest: `dc0f5e87bd3e248124a488f091ff25cd15f3f95bd98ceb7575cda7e40bc6bba7`
  - membership_digest: `386b988e3db0434bda35ffff8ca0bfd53fb6c08ebe3574b6aa2bd4040516968d`
  - retained_digest: `79c6a337d2dac9ead98d2bc5452d3a760a1f080d78ca7768352d9cef3c5c19e4`
- The changed input per the failure context is exactly `code_config_digest`: the
  accepted production module hash moved from `7e60ed28…` (review 87) to `e2dd17fc…`
  (review 90), so the recomputed code-config digest no longer equals the locked value.
- Locked plan content: 100 entries (all `reuse_retained` or `alias` against the retained
  snapshot; retained_snapshot holds 100 content-addressed objects with dual provider/
  content hashes and exact byte sizes), plus 4 blocked `sample_budget_exceeded` entries.

No listing, membership, plan, ledger, storage, coverage, sample, retry, Coinalyze, or
progress work occurred; the store was not mutated beyond the failed read path. The store
was not deleted, renamed, replaced, reconstructed, or relocked.

## Publication

- `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` next-required-actor set to
  `Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority execution`.
- Published records: `research/sprint_004/91_CEX002_GATE1_CORRECTED_EXECUTION.md` only.
  `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` is unchanged (no new
  second-run report exists). No source, test, fixture, data, or unrelated dirty path is
  staged.
- `HEAD == origin/main` established; Hermes stops here.

## Integrity assertions

- No secret value appears in this record; the API key was loaded only from `.env` and
  never printed or placed in a command argument.
- The preserved store was not deleted, renamed, replaced, reconstructed, or relocked.
- No source/test/fixture path was modified, staged, committed, or pushed.
- Raw exit status 1 was captured from the invocation wrapper, not inferred.

## Consequence

Gate 1 is blocked at the immutable-plan gate: the accepted production change alters the
locked plan's `code_config_digest`, and a new plan version requires fresh reviewer
authorization. The reviewer must disposition the plan-lock code-config change (e.g.
authorize a new plan version under the accepted `e2dd17fc…` code config) before any
further real execution. No reduced universe, omitted derivatives fields, or price-only
substitute is authorized.