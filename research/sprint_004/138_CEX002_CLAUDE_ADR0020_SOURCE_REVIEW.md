# CEX-002 Claude ADR-0020 Source Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `a7d062ec6738b9d5d04e3476e0410b0281e05aa7`

Governing architecture: `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`

Governing authorization: `research/sprint_004/137_CEX002_MEMBERSHIP_AND_BUDGET_ARCHITECTURE.md`

## Reviewed source drop

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
  - SHA-256: `538c1d90c7dc0c879318f1e2e9b07469862b2f655d3f28f538f8e47dee0253e4`
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
  - SHA-256: `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`
  - SHA-256: `4948007825e4c32e3a6ec75e080436e71bb230852b3da49e48c18887a69746e3`
  - unique `test_` functions: 240

The drop changed exactly the three authorized Python paths. No fixture, repository record,
data, checkpoint, cache, journal, database sidecar, Git state, or unrelated dirty path was
part of Claude's source drop.

## Decision

**REJECT PRODUCTION AND TEST SOURCE; ACCEPT AND FREEZE THE CLI WIRING.**

The implementation correctly introduces the 46 delivery rows, 17 alias mappings, the
three official pair reads, version-4 candidate lineage, non-cost-first planning, and the
six-object three-era selector. The CLI correctly constructs and passes the official
delivery-price source and remains frozen at `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc`.

The production and test paths fail four governing contracts and one mechanical acceptance
condition.

## Findings

### P0 - the reviewed authority tables are not frozen

`validate_reviewed_authority_tables()` recomputes a digest from whichever tuples currently
exist and then reports that new digest. It has no independent expected digest and does not
require the frozen 46/36/10/17/16 counts. A structurally valid row substitution, deletion,
alias remap, or authority-class swap therefore becomes the new authority instead of
failing closed. The test called `test_delivery_table_drift_fails_closed` changes each row
into an independently malformed one-row table; it never proves rejection of structurally
valid drift.

The independent canonical review-137 digests are:

- delivery table: `678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01`;
- settlement-alias table: `e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8`.

Production must carry those as literal expected constants and reject any count or digest
mismatch before resolving a name or constructing a candidate. Tests must mutate a table in
ways that remain locally well formed and prove the independent digest/count boundary rejects
the change. Tests must also compare the complete literal 46-row and 17-row contents, not
only counts, endpoints, and the ten reviewed-inference names.

### P0 - cost-source samples never receive the required data validation

The selected cost objects flow through `_acquire_sample()`, whose only content check is
`infer_schema_fields()`. That helper reads only the first CSV line from the first ZIP
member. It does not parse every data row, reject a later malformed row, prove nonempty data,
prove nondecreasing time, reject non-finite numbers, or validate quote/depth economics.
The retained-object branch does even less: it trusts checkpointed schema fields after
rehashing bytes and never reparses the retained payload. `recover_retained_samples()` also
records a cost object after first-line inference alone.

ADR-0020 requires the selected `bookTicker` and `bookDepth` qualification objects to be
checksum-proved, nonempty, fully parseable, time-monotonic, and economically valid. Add one
structured CSV/ZIP validation path used for new acquisition, content-address reuse, and
recovery. It must read every row and publish/persist a validation summary.

For `bookTicker`, require fixed-width rows; finite numeric values; integral nonnegative
update IDs; positive bid/ask prices; nonnegative quantities; bid price no greater than ask
price; and positive, nondecreasing transaction and event times. For `bookDepth`, accept the
official timestamp encodings, require positive nondecreasing timestamps, finite nonzero
percentage bands, and finite nonnegative depth/notional. At least one data row is required.
Malformed later rows, NaN/infinity, crossed quotes, negative quantities/depth/notional, and
time reversal must fail both fresh and retained/recovered paths. Focused tests must exercise
those failures and a real-shaped headed payload for each family.

### P1 - the complete Gate-2 cost manifest still has no digest

`select_cost_calibration_sample()` returns object count, bytes, keys, objects, items, gaps,
selector, and families but no canonical manifest digest. The report comment says the block
contains a digest, yet `storage.cost_sample` publishes none. This does not meet review 137's
requirement to preserve the complete final cost manifest's exact objects, bytes, gaps, and
digest outside the Gate-1 allowance.

Add a versioned canonical SHA-256 over the full selected cost object identities
(`family`, `symbol`, `key`, listed byte size, and ETag where present), selector/families,
and typed gaps. Publish it in the complete Gate-2 cost block and bind it into the relevant
candidate/report identity. Prove that changing a key, size, ETag, selector, or gap changes
the digest while the six-object Gate-1 cost-source sample leaves the full digest unchanged.

### P1 - delivery-price provenance and positive-price validation are incomplete

`parse_delivery_price_response()` accepts non-finite floating prices because `NaN <= 0`
is false. `validate_delivery_price_response()` does not prove that `request_params` is
exactly the response pair, and a nonempty retained path is accepted when its filename is
not its content address. Tighten these checks and add focused NaN/infinity, request-pair
mismatch, and non-content-addressed-path tests. The production FAPI source must still retain
the exact raw response and report only redacted endpoint-plus-pair provenance.

### P2 - duplicate test imports will fail the acceptance lint

The test import list imports `MEMBERSHIP_DATED_DELIVERY` twice and
`MEMBERSHIP_SETTLEMENT_ARTIFACT` twice. Remove the duplicates and keep the import block
mechanically clean. No Ruff result from Claude is requested or accepted; Hermes will run
the governed command only after source acceptance.

## Corrective source authorization

Sr Dev - Claude Build using Claude Opus 5 may correct only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The accepted CLI path is frozen. Claude must preserve the exact review-137 tables, direct
versus reviewed authority, alias nonconsumability, future-name blocking, non-cost-first
budget priority, three-era arithmetic, complete Gate-2 cost scope, candidate version 4,
the two superseded version-3 digests, locked versions 0-2, empty candidate samples, and all
no-mutation flags.

Claude performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, repository-record edit, ADR edit, CLI edit, fixture edit, Git operation,
commit, push, migration, sample acquisition, Gate 2, Nautilus, Harmonic Trader, PAPER,
LIVE, or other-ticket work. It stops for reviewer source inspection with both exact
SHA-256 values and the unique CEX test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/138_CEX002_CLAUDE_ADR0020_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No developer source/test/CLI/fixture path, data, checkpoint, cache, journal, sidecar, or
unrelated dirty path belongs to this publication. The reviewer executes no pytest, Ruff,
repository-control, candidate, migration, sample, or data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate integration/execution,
plan migration, sample acquisition, Gate 2 and every later gate, Nautilus work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, and every next ticket remain unauthorized.
Next ticket remains `NONE`.
