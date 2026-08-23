# CEX-002 Retained Lineage Authority Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Sol review-237 drop rejected before integration on one residual authority defect
- **Authorized actor:** Sr Dev - Codex Sol High
- **Integration actor after source acceptance:** NONE

## Reviewed drop

The reviewer inspected Sol High's complete review-237 drop once at:

- sizing source:
  `1ddc5e2bee0615ff97c97dc6db938d8041e04036c9e7e3f983556cb4d4a1885f`;
- sizing tests:
  `d97923ed75ef127c52f421f0d37fcdfe47fe1d8d960d8bdfeeebed3a3ff173b3`;
- unchanged sizing CLI:
  `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`;
- test functions: 137.

No reviewer pytest, Ruff, sizing, qualification, control, acceptance, network, or data
command was run. Static inspection accepts the other review-237 corrections: all 771
memberships are representable at the exact 698 detailed / 73 funding-only boundary; cost
calibration is five independent components; target grids and quality-gap reservations are
causal and partition-local; archive and Coinalyze manifest schemas are separate and
complete; bundle rows cover the projected archive-plus-Coinalyze partitions; complete gap
and bundle values are traversed; and every required future-width class enters a named
capacity component and temporary high-water calculation.

Preserve those corrections and all previously accepted authority, conversion, financial
semantics, security, publication, v1 immutability, credit, reserve, and idempotence
protections.

## Blocking finding

The Gate-2 credit proof at reviewed source lines 6915-6933 correctly re-proves exactly 73
retained requirement keys: 68 selected and five cost keys. It also states that this set is
not the 96-object coefficient cohort. The lineage path nevertheless creates
`manifest_entries` from every coefficient-cohort binding at lines 6970-6994 and passes
those entries to `build_partition_lineage` at line 7014. That builder treats any supplied
entry with a sample hash as retained at lines 3037-3105.

The result substitutes 96 measurement keys for the distinct 73-key retained-credit
authority. It can publish uncredited coefficient samples as retained receipts, omit the
future receipt/hash widths those mappings still require, and make lineage state disagree
with the raw-byte credit used by the capacity equation. The new source test at reviewed
test lines 3827-3875 explicitly supplies an arbitrary coefficient-style witness and
therefore preserves rather than detects the substitution.

This violates review 237 section 3 and ADR-0023. Integration and command execution remain
unauthorized.

## One residual correction

Make retained archive lineage an exact join to the already re-proved Gate-2 credit:

1. Derive retained bindings only for the exact full keys in `credit["keys"]`. The
   96-object coefficient cohort remains measurement/decomposition evidence and supplies
   no retention authority.
2. For each of the 73 credited keys, carry the re-proved checkpoint object hash, provider
   checksum authority, real retrieval time when known, and honest availability evidence.
   Unknown retrieval or source-availability time stays null. Do not invent a timestamp,
   hash, checksum, or retained state.
3. Fail closed if a credited key has no exact retained binding, a retained binding is not
   in the credit set, or two authorities disagree. Every other selected/cost requirement
   key must remain `projected_unacquired` with nullable future receipt fields.
4. Publish the unique retained archive-key count and a deterministic digest of the exact
   retained key set, and reconcile them to `retained_credit.valid_requirement_keys` and
   `retained_credit.keys`. Future-lineage width and temporary-high-water calculations must
   consume the corrected source states.
5. Replace the arbitrary-witness test with a disjoint cohort-versus-credit test. In the
   real accepted receipt path, prove the exact retained lineage set has 73 unique keys,
   its digest equals the credit-key digest, no coefficient-only key gains retention, and
   every noncredited requirement remains projected. Preserve the complete real-authority
   rerun and all existing valid tests.

Keep the correction minimal. Do not redesign the accepted projection, cost, quality,
bundle, capacity, or publication paths and do not weaken a production invariant or add a
skip.

## Exact Sol authorization and stop

Codex Sol High may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py` only if the exact correction
   mechanically requires it; otherwise leave it byte-identical.

Work from the current shared drop in place. Do not reset, restore, checkout, discard, or
wholesale replace it. Sol does not run commands or tests, mutate evidence/data, use Git,
or write research, ticket, handoff, ADR, receipt, envelope, database, manifest, or catalog
records. Stop once with SHA-256 for all three allowed paths, explicitly marking unchanged
paths, plus the final `test_` function count.

The owner reports that Claude is available again, but Sol retains the complete current
implementation context and this is one already-bounded residual join rather than new
architecture. Sol is therefore the sole authorized actor for this correction; Claude and
Grok are deauthorized. No integration actor is authorized until reviewer static
acceptance. Gate 2 remains blocked, bulk acquisition and all later work remain
unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/238_CEX002_RETAINED_LINEAGE_AUTHORITY_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

The three developer paths and all unrelated dirty work are excluded.
