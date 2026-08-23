# CEX-002 Fee Authority and Final Sizing Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Fee-source absence resolved; one complete senior correction authorized
- **Authorized actor:** Sr Dev - Grok Build
- **Integration actor after source acceptance:** NONE

## Reviewed state

The unintegrated review-233 source drop remains at these identities:

- sizing source: `a1772979f6ceb979424c865deeb00ad796377170942f1f15292cb4c4a4806866`;
- sizing tests: `402429f7d12f76b0f818ace989a780a4b5fdfd6885027dc544a5e1a7e4a38e3e`;
- sizing CLI: `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`;
- test functions: 109.

It is still rejected and must not be integrated or executed. Review 233's seven findings
are the complete defect set for the next correction; this record resolves the one
architecture prerequisite and turns those findings into one bounded implementation
contract. No further piecemeal source review is authorized.

## Fee-authority finding

The accepted qualification report names `/fapi/v1/commissionRate` as a possible
incremental endpoint but retains no response. Official documentation proves that the
endpoint is signed, symbol-specific, account-specific, and current: its request has no
historical or effective-time parameter. The current fee page is not a reproducible
effective-dated history. The repository contains no other retained fee authority and the
FEE-001 table contains zero rows.

ADR-0026 therefore resolves the boundary as unavailable historical authority. It forbids
backdating and represents the absence through 771 typed fee gaps. Two global immutable
configuration rows provide five- and ten-basis-point per-side assumed fee scenarios;
both use authority class `ASSUMED_CONSERVATIVE` and policy knowledge time
`2026-08-23T03:00:00Z`. They are not historical FEE-001 observations. The complete known
gap minimum is 9,088 rows: 8,317 accepted source gaps plus 771 fee-authority gaps.

## One complete correction contract

Grok may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py`.

Preserve every accepted review-229 fact, version-1 receipt/envelope immutability, real raw
and Coinalyze evidence pin, no-network/no-credential boundary, content-addressed
publication, race/symlink protections, exact acquisition credit, reserve floor, and
idempotent receipt behavior. Implement all requirements below together.

### A. Accepted lineage is executable

Group the 106 logical plan records by physical key. Fold a repeated key only when SHA-256,
byte size, family, retrieval time, availability semantics, and source-availability time
all agree; preserve every logical role/regime label on the folded record. The accepted
authority must prove 106 logical records, 96 physical bindings, and ten folded aliases.
Any disagreement, missing binding, or second checkpoint object blocks before publication.

### B. Exact types do not depend on runtime context

Decide decimal(38,18) representability from the original lexeme's sign, integer
coefficient, and base-10 exponent using integer arithmetic. Reconstruct without ambient
Decimal precision, binary float, or rounding. Reject precision, scale, exponent, NaN,
infinity, syntax, and range failures as redacted `SizingError` values. Convert UTC text to
epoch units with integer calendar arithmetic; do not call `datetime.timestamp()`.

Tests must change the active Decimal context and prove byte-identical results for valid
38-digit boundary lexemes, prove overflow blocks, and cover pre/post-epoch timestamps.

### C. Size final products, not physical-family facsimiles

Keep contribution measurements, but separately declare and allocate the complete target
schema for all eleven products. Every product row includes the canonical instrument and
contract-version identity appropriate to the row. At minimum the final contract includes:

- membership: venue, canonical instrument, contract version, native symbol, contract
  type, margin/settlement identity, acceptance regime, and lifecycle bounds;
- hourly bars: complete OHLCV/trade-count fields and row/source identity;
- hourly trade flow: total and taker-buy base/quote volume plus materialized taker-sell
  values and signed buy-minus-sell imbalance values;
- five-minute OI: OI level/value, positioning/taker metrics, previous comparable level,
  level/value change, change interval, and an explicit null/gap-break status;
- realized funding: event time, interval hours, rate, and long/short cashflow-rate sign
  convention; indicative funding: the actual premium inputs with any unavailable direct
  indicative rate typed nullable/gapped rather than fabricated;
- hourly mark/index/basis: causally joined mark, index, premium, absolute basis, and a
  deterministic fixed-decimal relative-basis field with zero-denominator failure;
- observed daily liquidations: native/provider identity, exact long/short units,
  imbalance, source interval, and explicit censored/not-event-complete semantics;
- cost calibration: all book-ticker and book-depth fields and rows, zero historical
  official fee rows for this authority, 771 identity-scoped fee gaps, and exactly the two
  ADR-0026 scenario-policy rows with exact rates, scope, flags, the fixed
  `2026-08-23T03:00:00Z` `policy_known_at`, `ASSUMED_CONSERVATIVE` authority, and basis
  fields;
- coverage gaps: all accepted source fields needed to preserve product, family, native
  and canonical identity, kind, status, interval, blocking, and explanation semantics;
- bundle: every dataset, partition, schema, manifest, mapping, source, code, configuration,
  unit, censorship, scenario-policy, coverage, and cross-product intersection identity
  needed to reproduce the release.

Derived sample columns must be measured from real sample values, not constant/null
placeholders. Publish physical contribution schemas and final target schemas separately,
and allocate every target-only field exactly once.

### D. Lineage payload and overhead are partition local

Measure and project a distinct lineage manifest for every required
product/native-symbol/UTC-month partition. Each contains the conservative payload charge
for all raw mappings feeding that partition, that manifest's row-group/footer metadata,
and fixed Parquet framing. Cross-product references are charged in each product they feed.
Do not divide one cohort-global file by mappings.

Coinalyze partitions obey the same contract and carry a real or projected response receipt
reference plus proved provider/native mapping. Publish payload, row-group/footer, framing,
mapping count, partition count, and largest partition separately. Nothing is charged both
inside a partition manifest and again as a release-global manifest copy.

### E. Coverage starts from all accepted evidence

Parse the full accepted product matrix and reproduce exactly 8,317 product-scoped source
gap records and the separate 3,742 typed-gap product/symbol memberships. Add exactly 771
ADR-0026 fee-authority gaps for a known minimum of 9,088 coverage rows. Do not infer these
facts from the 202 Coinalyze non-mappings.

For each fixed-cadence target product/native-symbol/month with expected-row ceiling `N`,
reserve up to `ceil(N / 2)` row-level missing-run records. Keep accepted source gaps,
fee-authority gaps, typed-gap memberships, and projected quality-gap rows as separate
receipt counts. Event-driven products use proved object/source gaps and never infer absent
unobserved events.

### F. Cadence and Coinalyze arithmetic are conservative and unit-correct

Keep daily metrics at 300 seconds. Use a one-hour realized-funding calendar ceiling until
a stricter complete-history minimum interval is proved, while publishing observed-ratio,
calendar, and winning bounds. Correct the Coinalyze test and implementation contract so a
raw point charge is converted to a projected raw-response receipt once and the typed
bytes-per-point coefficient is applied once; no raw-byte factor is multiplied twice.

### G. Receipt completeness is fail-closed

The receipt must expose all exact counts and byte components above, including the 9,088
known coverage rows, two scenario rows, zero official historical fee rows, 106/96/10
lineage decomposition, per-product final schemas, local manifest accounting, target-only
bytes, Coinalyze raw/typed/manifest separation, and the fastest-cadence bounds. Its total,
temporary high water, catalog pages, blocker list, and self-size must be recomputed from
those components. Missing or inconsistent authority blocks before durable publication.

## Required source tests

Extend the existing test file in the same drop. Tests must directly prove:

1. accepted 106/96/10 alias folding and conflict rejection;
2. context-independent decimal and integer-time boundaries;
3. exact final schema fields, derived formulas, null/gap rules, and absence of float types;
4. independent local manifest overhead for two partitions and Coinalyze raw lineage;
5. exact accepted 8,317 / 3,742 / 771 / 9,088 coverage decomposition and the
   `ceil(N / 2)` quality-gap ceiling;
6. zero official fee history plus exactly two policy scenarios, with no backdated
   FEE-001 row, zero-cost fallback, rebate, discount, or maker credit;
7. 300-second metrics and one-hour funding calendar bounds;
8. unit-correct Coinalyze projection;
9. full real-authority receipt completeness, capacity boundary, and byte-identical rerun;
10. unchanged no-network, no-credential, path, symlink, race, and version-1 protections.

Tests may use compact synthetic fixtures for individual invariants but the end-to-end test
must use the already accepted local authority. Do not delete, weaken, rename away, or mark
xfail any existing protection to obtain agreement.

## Stop conditions

Grok does not run tests, Ruff, sizing, qualification, control, network, acquisition,
normalization, or data mutation commands. It performs no Git action and writes no research,
ticket, handoff, ADR, receipt, envelope, database, manifest, or catalog record. It stops
after one complete three-path source/test drop and reports SHA-256 for every allowed path,
explicitly marking an unchanged path, plus the final `test_` function count.

No integration actor is authorized until reviewer static acceptance. Gate 2 remains
blocked, bulk acquisition remains unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `docs/adr/0026-non-backdated-fee-scenarios.md`;
- `research/sprint_004/234_CEX002_FEE_AUTHORITY_AND_FINAL_SIZING_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

The dirty developer sizing drop and unrelated repository work are excluded.
