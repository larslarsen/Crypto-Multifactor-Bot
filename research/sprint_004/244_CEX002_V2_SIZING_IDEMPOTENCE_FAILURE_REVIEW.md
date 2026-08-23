# CEX-002 V2 Sizing Idempotence Failure Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record-243 validation failure rejected; one consolidated correction authorized
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed execution

Hermes integrated and committed the exact review-242 identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `7ca6082f9c52f4d6b5a770647ecd452cea8c279faa41811ad31d7fc70f44b4c9` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `1867f9d271a1d4e04eab931209a08451a948938e5df42ad8619c1c1d062cc0a4` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 138 functions. `HEAD == origin/main` at record-243 commit
`87c52d3eac9cbaf7430ea681d92786cb6c69479d`. Focused pytest exited 1 after 7.7909
seconds with four failures. Hermes correctly stopped before Ruff and before both sizing
invocations. No receipt 231 or v2 sizing evidence was produced by a real CLI run. No
network, acquisition, normalization, catalog, model, or later work ran.

No reviewer pytest, Ruff, sizing, qualification, control, acceptance, network, or data
command was run. Static inspection reduces all four failures to two causes. Do not route
four independent repairs.

## 1. Preserve the ADR-0024 temporary-work equation

`test_end_to_end_receipt_is_complete_and_durably_identical` fails at:

```text
assert 200457493 < (10822789 + 1094722)
```

The production equation is correct and the ordering assertion is not. ADR-0024 section 5
defines bounded temporary work as the greatest of the largest accepted compressed object,
the largest projected normalized partition, and the bounded catalog/bundle transaction.
It does not require that greatest unit to be smaller than final normalized-plus-catalog
storage. The synthetic fixture legitimately retains the accepted 200,457,493-byte largest
object while projecting a much smaller normalized test universe.

Remove that ordering assumption. Retain and strengthen the actual invariants: exactly six
non-overlapping capacity components; temporary work equals the exact three-way maximum;
typed normalized storage is included once; catalog/manifest/bundle storage is included
once; temporary work is included once; and the total is their exact integer sum. Do not
change production capacity arithmetic or make the temporary bound smaller.

## 2. Correct prior-receipt idempotence without weakening collision refusal

The other three tests complete their first sizing run and then fail on the second with:

```text
a different sizing receipt already occupies its target
```

The affected tests are:

1. `test_v2_envelopes_are_content_addressed_and_reused_not_rewritten`;
2. `test_rerun_returns_the_identical_receipt_under_changed_observations`; and
3. `test_rerun_below_the_reserve_floor_also_returns_the_identical_receipt`.

This is one production defect. `run_storage_sizing` recomputes the stable authority and
measurements, but `revalidate_prior_receipt` fails to recognize the internally valid prior
receipt as the same stable measurement. The subsequent fixed-target publication correctly
refuses to overwrite it. Do not weaken `_publish_at`, canonical-byte checks, no-follow
handling, or collision refusal to hide the failed revalidation.

Implement one explicit deterministic stable-receipt comparison boundary and use it for
prior revalidation. The stable projection must compare exactly:

- schema, ticket, policy, code identity, accepted authority, physical inputs, cohort;
- typed schema, lineage, future-width, coverage, cost, fee, measurement, projection, and
  Coinalyze evidence;
- semantic counts and partitioning; and
- the five observation-independent capacity fields plus the reserve rule.

The comparison must exclude only sizing-time observations and their frozen derivatives:
`generated_at`, filesystem observations, the newly observed operating reserve and total,
blockers, state, authorization, and published-versus-reused attempt outcomes. The prior's
own excluded fields are not trusted: `_prior_receipt_is_whole` must continue proving its
canonical bytes and exact self-length, frozen reserve from its recorded pre-write space,
six-component total, post-space blocker equation, state, and non-authorization text.

Make the stable envelope count semantic and deterministic from the measured/content-
addressed evidence set, not from first-run versus rerun publication outcomes. Every item
used by stable comparison must be independent of whether its envelope already existed.

Preserve these fail-closed outcomes:

- any stable authority, source/code, schema, measurement, projection, count, partition,
  capacity-component, or evidence identity change rejects reuse;
- a malformed, noncanonical, symlinked, internally inconsistent, or tampered prior receipt
  rejects reuse and is never overwritten;
- only an exact stable match plus an internally whole prior returns `rerun=True`;
- changed time, free space, derived reserve, and envelope reuse observations return the
  original receipt bytes, hash, length, capacity decision, and frozen filesystem block;
  and
- the second run reports operational envelope reuse outside the durable receipt.

Add or refine a focused source test that exposes the stable projection directly enough to
name a mismatching field. Preserve all existing tamper, race, symlink, capacity-boundary,
self-length, v1-immutability, real-authority rerun, and content-addressed evidence tests.
Do not delete, skip, or broadly relax any test.

## Exact Claude authorization and stop

Claude Build may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`; and
3. `scripts/research/size_binance_usdm_harmonic_release.py` only if mechanically required;
   otherwise leave it byte-identical.

Work from integrated `HEAD` in place. Do not reset, restore, checkout, discard, or
wholesale replace files. Claude does not run commands or tests, mutate evidence/data, use
Git, or write research, ticket, handoff, ADR, receipt, envelope, database, manifest, or
catalog records. Stop once with SHA-256 for all three allowed paths, marking unchanged
paths, plus the final `test_` function count.

Sol, Grok, Spark, and Hermes are deauthorized. All integration and execution await one
reviewer source acceptance. Gate 2 remains not accepted; acquisition and later work remain
unauthorized; next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/244_CEX002_V2_SIZING_IDEMPOTENCE_FAILURE_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and all unrelated dirty work are excluded.
