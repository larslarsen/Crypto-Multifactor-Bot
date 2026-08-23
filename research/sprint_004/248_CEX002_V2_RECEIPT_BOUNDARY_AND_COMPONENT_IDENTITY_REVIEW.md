# CEX-002 V2 Receipt Boundary and Component Identity Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-246 validation failure consolidated into one senior correction
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed evidence

The reviewer inspected Hermes's complete record 247 once. Hermes proved the accepted
review-246 identities, ran the authorized focused pytest command once, and stopped after
three failures. No Ruff or real v2 sizing invocation ran, and receipt 231 remains absent.
The integrated sizing source, test, and unchanged CLI are respectively:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `f0f4f89d5e571ea586f0d6746f20cb7aad2115156b73719e8d1c7ac1cec7d550` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `5029d4cf7d1a7af507cc49d0766bf87c477c60ea13c3647e8092fe8fbfc46bf9` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file contains 139 `def test_` functions. The reviewer ran no pytest, Ruff,
sizing, qualification, control, acceptance, network, or data command.

## Consolidated diagnosis

The three failures have two bounded causes.

First-run publication returns the pre-serialization Python receipt, whose nested values
include tuples. A valid rerun returns the same durable receipt decoded from JSON, whose
corresponding values are lists. The stable projection correctly canonicalizes that
representation difference and reuses the prior bytes, but the two public return values
are not equal as Python documents. The publication API must return the exact canonical
JSON document on both paths, not merely values that serialize to the same bytes.

The product-name assertion is stale for `official_fee_schedule`: ADR-0026 explicitly
defines it as component three of required product `binance_usdm_cost_calibration`.
Inspection also found the adjacent inverse inconsistency: `fee_authority_gap` and
`scenario_policy`, components four and five of that same product, currently label their
measurement/projection blocks with their component names as `required_product`. The
correction must preserve the distinction required by ADR-0025: a dictionary key may name
a measurement component, but it does not create a twelfth required product.

## One correction contract

Claude may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

Leave `scripts/research/size_binance_usdm_harmonic_release.py` byte-identical.

### A. Return the durable receipt representation

At the successful first-publication boundary, normalize the final self-sized receipt
through the repository's one canonical JSON encoding and decoding boundary before it is
published and returned. The mapping in `result["receipt"]` must equal the JSON document
decoded from the exact fixed-target bytes. Its canonical bytes, SHA-256, byte length,
self-length field, storage decision, and all receipt facts must remain unchanged.

A valid rerun must continue to return the independently revalidated prior document. Under
changed time/free-space observations, require all three facts together: the target bytes
are unchanged, the second returned receipt equals the first returned receipt, and both
returned receipts equal the decoded durable target. Do not weaken the equality to another
canonical-byte-only comparison, remove the rerun assertions, or move prior-receipt
revalidation after publication.

### B. Preserve required-product and component identity

For each of the five ADR-0026 cost components, every emitted measurement/projection block
must identify:

- `required_product` as `binance_usdm_cost_calibration`; and
- `component` as exactly one of `retained_book_ticker`, `retained_book_depth`,
  `official_fee_schedule`, `fee_authority_gap`, or `scenario_policy`.

In particular, correct the fee-gap and scenario-policy measurement identities and retain
the already-correct official-fee required-product identity. Propagate the component name
through fixed-schema projection so the fixed-schema, coverage, and cost-component receipt
views cannot confuse the component key with a required product. The standalone
membership, coverage-gap, and bundle blocks retain their own required-product identities;
do not rename, split, or add any required product.

Replace the blind `block["required_product"] == dictionary_key` assertion with explicit
contract checks: standalone required-product blocks equal their keys, while the three
fixed-schema cost-component keys all name the cost product and their own component. Prove
the five-component cost receipt has the same parent/component identities. Preserve typed
gap and quality-gap semantics unless the identity propagation mechanically requires an
unchanged explicit component label.

### C. Preserve all accepted protections

Keep the review-246 stable projection and named mismatch behavior, complete prior internal
wholeness proof, semantic envelope count, six-component capacity equation, ADR-0024
temporary maximum, exact 73-key retained-credit join, complete target schemas, and all
tamper, collision, no-follow, race, content-addressed publication, and v1-immutability
protections. Do not delete, skip, xfail, or weaken a test to obtain agreement.

## Exact Claude authorization and stop

Work from the shared integrated paths in place. Do not reset, restore, checkout, stash,
discard, or replace either file wholesale. Do not run commands, tests, Ruff, sizing,
qualification, control, Git, network, acquisition, normalization, or data/evidence work.
Do not edit any research, ticket, handoff, ADR, receipt, manifest, database, or catalog
record.

Stop once after the complete two-path source/test correction. Report SHA-256 for the two
edited paths and the unchanged CLI, plus the final `def test_` function count. Sol, Grok,
Spark, Hermes, integration, execution, acquisition, and later work remain unauthorized
pending reviewer static acceptance. Gate 2 remains not accepted and next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/248_CEX002_V2_RECEIPT_BOUNDARY_AND_COMPONENT_IDENTITY_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
