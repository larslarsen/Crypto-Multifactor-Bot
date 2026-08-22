# CEX-002 Migration Integration and Focused-Command Stop

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/151_CEX002_MIGRATION_SOURCE_ACCEPTANCE.md`

## 1. Integration

Hermes established `HEAD == origin/main == c3ffb584ebc77efab8a59e59dd51ad2e177f2a68`
at the review-151 publication commit before staging.

Accepted path hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `6f38c99e19e0b4a48cbc9189302bdbfc225595807c0e64516338df6815d8a8a5` |

The test path contained 285 unique `test_` function definitions. `git diff --check` was
clean for the three accepted paths.

Hermes staged exactly the three accepted paths and committed:

`bce618f7e100e10751a5f342ba1c55ccc7c3ef7d`

Commit message:

`CEX-002: integrate reviewed v4 migration source`

After push:

`HEAD == origin/main == bce618f7e100e10751a5f342ba1c55ccc7c3ef7d`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
Hermes made no source or test edit after integration.

## 2. Focused command sequence

Review 151 required stop-on-first-failure execution. Command 1 failed, so commands 2-5,
migration preconditions, the migration-only invocation, and after-proof were not
authorized and were not run.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 1

Observed output reached `[100%]` and reported 15 failed tests. The invocation did not print
a collected/pass summary line under `-q --tb=short`; Hermes does not infer missing pass or
collection counts.

Failures:

- `test_reviewed_migration_installs_version_four_ledger_first_and_lock_last`
- `test_reviewed_migration_refuses_a_ledger_bound_to_another_authority`
- `test_migrated_resume_accounts_only_through_the_amendment_ledger`
- `test_migration_records_an_advanced_source_identity_explicitly`
- `test_completed_migration_rejects_self_consistent_lock_substitutions[binding-does not match the accepted identity]`
- `test_completed_migration_rejects_self_consistent_lock_substitutions[source_receipts-does not match the accepted identity]`
- `test_completed_migration_rejects_self_consistent_lock_substitutions[history-does not match the accepted identity]`
- `test_completed_migration_rejects_self_consistent_lock_substitutions[prior_lock_evidence-does not match the accepted identity]`
- `test_completed_migration_rejects_self_consistent_lock_substitutions[inputs-migrated Gate 1 plan inputs changed]`
- `test_amendment_accounting_rejects_unauthorized_or_over_allowance_records[out_of_plan-outside the reviewed plan]`
- `test_amendment_accounting_rejects_unauthorized_or_over_allowance_records[wrong_size-does not match its locked planned size]`
- `test_amendment_accounting_rejects_unauthorized_or_over_allowance_records[over_allowance-exceeds the reviewed allowance]`
- `test_amendment_accounting_rejects_unauthorized_or_over_allowance_records[legacy_fields-legacy range accounting]`
- `test_migration_does_not_adopt_a_recoverable_missing_checkpoint_entry`
- `test_completed_migration_rejects_two_file_source_receipt_substitution`

Primary repeated assertion mismatch:

```text
assert 'd3fe13d96146d163bb39f338b058d3e59c26fbef6c0870b574db1dae68906da4'
== '2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef'
```

Other observed failure signatures:

- ledger-boundary error message mismatch: expected `does not match the accepted identity`,
  actual `the amendment ledger is not bound to the reviewed migration`;
- amendment accounting tests reached `IndexError: list index out of range` while looking
  for a download entry.

### C2-C5

Not run because C1 exited nonzero.

## 3. Migration disposition

No migration preconditions were captured. No `.env` migration environment was loaded. No
`--apply-reviewed-v4-migration-only` invocation was run. No ordinary resume, second
migration command, sample acquisition, Gate 2, normalization, catalog publication, Nautilus
work, Harmonic Trader work, payoff analysis, PAPER, LIVE, or next-ticket work occurred.

The accepted report, manifest detail, version-2 lock, legacy ledger, amendment ledger
absence, sample checkpoint, retained raw tree, caches, ignored evidence, database sidecars,
and unrelated dirty paths were not staged or intentionally mutated by this publication.

## 4. Publication

This record publishes the integration and required stop point only. CEX-002 remains
`IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.
