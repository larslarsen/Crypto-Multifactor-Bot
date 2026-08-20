# CEX-002 Gate 1 Plan-2 Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Gate 1 source procurement

## Outcome

**ONE-TIME PLAN-VERSION-2 MIGRATION FAILED ITS OWN ASSERTIONS. NO REAL RUN. NO SECOND
RUN. NO SEMANTIC COMPARISON. LOCK FILE LEFT AT ITS LAST VALID STATE (VERSION 1).**

Review 92's migration command was executed verbatim from repository root. It failed at
the post-`lock_plan` assertion `assert lock.plan == old_plan`. Because `lock_plan` had
already been called on the in-memory object, the subsequent asserts (plan_version 2,
plan_digest unchanged, retained/budget snapshots unchanged, history [0,1]) never ran and
`lock.flush()` never executed. The atomic lock file on disk was therefore not touched and
remains byte-identical to its pre-migration version-1 state. Per review 92, a migration
failure stops before any real run; no qualifier invocation, no second run, and no
`drop_identity_volatility` comparison were performed.

## Migration execution

Command: the exact `python - <<'PY'` block from review 92 lines 59–133, run once.

Assertions that PASSED before the failure:

- lock file SHA-256 `45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf`
- plan_version == 1; plan_digest == `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`
- history versions `[0]`; locked code_config_digest `9845375e…`
- `len(lock.plan["entries"]) == 146`, `len(lock.plan["blocked"]) == 46`,
  `len(lock.retained_snapshot) == 118`, `unique_retained_objects == 86`,
  `unique_new_objects == 0`, `new_download_bytes == 0`
- `new_code == expected_new_code` (`3323116bef5558eb2da57f67cb8edb15267cbb55f06ebe012383431a7f580148`)
  via `plan_code_config_digest(budget_bytes=268435456, max_object_bytes=67108864)`
- `new_inputs.differences(old_inputs) == ("code_config_digest",)`
- after `lock.lock_plan(...)`: `plan_version == 2`, `plan_digest == expected_plan`

Assertion that FAILED (line 53 of the command body):

```
assert lock.plan == old_plan
```

## Exact root cause (read-only diagnosis, no mutation)

`SamplePlan.from_dict(old_plan).to_dict()` does not round-trip byte-for-byte. Direct
read-only comparison of the loaded version-1 lock shows:

- Entry counts match (146 entries, 46 blocked).
- `blocked` rows round-trip identically.
- The ONLY value-level difference in every `entries` row is the `products` field:
  - stored: `"products": ["binance_usdm_trade"]` (list)
  - round-trip: `"products": ("binance_usdm_trade",)` (tuple)

Because Python dict equality treats a list and a tuple as unequal, all 146 entries differ
and `SamplePlan.to_dict()` output can never equal the stored plan dict under the accepted
production code (`e2dd17fc…`). The tuple is a non-JSON-native representation leaking from
`to_dict()`; the stored JSON had the equivalent JSON arrays (so the serialized file is
valid), but the in-memory round-trip equality assertion in review 92 cannot hold.

This is a representation round-trip defect in the accepted production module, not a
review-92 logic error and not a Hermes execution error. The migration is a one-time
authorization that failed its preconditions; it must be corrected forward (e.g., a
`to_dict`/`from_dict` round-trip fix so `products` emits a list, re-reviewed by the
reviewer) before the plan version 2 migration and the corrected two-run execution can be
authorized again.

## Lock file integrity

- `data/cex002_qualify/cex002_sample_plan_lock.json`:
  SHA-256 `45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf` (unchanged).
- plan_version on disk remains 1; plan_digest `d6eb52ff…`; locked code/config digest
  `9845375e…`; history `[0]`.
- `lock.flush()` never executed; no temp/bak/swap artifact exists in the store directory.
- The store was not deleted, renamed, replaced, reconstructed, or relocked. No real run
  was attempted.

## Publication

- `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` next-required-actor set to
  `Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority execution`.
- Published records: `research/sprint_004/93_CEX002_GATE1_PLAN2_EXECUTION.md` only.
  `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` is unchanged (no run
  occurred). No source, test, fixture, data, or unrelated dirty path is staged.
- `HEAD == origin/main` established; Hermes stops here.

## Integrity assertions

- No secret value appears in this record; `.env` was never sourced or printed.
- The migration ran exactly once, verbatim from review 92.
- No source/test/fixture path was modified, staged, committed, or pushed.
- Raw exit status capture was not reached (the failure precedes any qualifier invocation).

## Consequence

The plan-version-2 migration is blocked by a `SamplePlan.to_dict()` round-trip
representation defect (tuple `products` instead of list). The reviewer must disposition
this defect before re-authorizing the one-time migration and the corrected two-run
execution. CEX-002 and Gate 1 remain `IN_PROGRESS`; next ticket remains `NONE`.