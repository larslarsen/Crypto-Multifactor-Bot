# CEX-002 Claude ADR-0020 Correction Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `8d1f42824e6a045893f8a71a7daf4ccf8bafe6ea`

Governing correction: `research/sprint_004/138_CEX002_CLAUDE_ADR0020_SOURCE_REVIEW.md`

## Reviewed correction drop

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
  - SHA-256: `9d69d6a3bf4a3fe81a6b81217f496b8ed500283a1b7b884fec4dd073e5d40e4d`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`
  - SHA-256: `033564eafd3862a84d8db8e9206ffd6b694e766b9f518867d8e61c4570c7dd25`
  - unique `test_` functions: 258
- frozen CLI verification:
  - SHA-256: `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc`

The correction changed only the two review-138-authorized files. The accepted CLI remains
byte-identical. No fixture, repository record, data, checkpoint, cache, journal, database
sidecar, Git state, or unrelated dirty path was part of Claude's correction.

## Decision

**REJECT FOR TWO RESIDUAL SOURCE BOUNDARIES AND TWO MECHANICAL TEST DEFECTS.**

The correction now has independent review-137 count and digest constants, complete literal
table tests, finite delivery-price and exact request/path provenance checks, a versioned
complete cost-manifest digest bound into the version-4 candidate envelope, and one shared
row/economic validator invoked by fresh acquisition, content-address reuse, and recovery.
Those accepted regions are frozen.

## Findings

### P1 - a second ZIP member remains outside the cost proof

`cost_sample_rows()` still opens only `members[0]`, and `_split_csv_line()` is an ad hoc
comma split rather than structured CSV parsing. The new validator therefore reads every
row only in the first member. A checksum-valid ZIP can carry a valid first CSV member and
a malformed second member while receiving a successful validation summary. This is the
same first-member trust boundary review 138 required the structured CSV/ZIP path to close.

The cost-validation path must use the standard CSV parser in strict mode and fail closed
unless a ZIP contains exactly one non-directory CSV member. It must parse that entire
member, preserve empty cells so fixed-width validation rejects them, and reject malformed
CSV. Add a focused test proving a valid first member plus any second member is rejected;
the existing fresh/reuse/recovery use of the shared validator must remain unchanged.

### P1 - version-4 construction can still omit the complete cost identity

`build_candidate_plan_v4()` gives `complete_cost_manifest_digest` a default empty string
and publishes the version label even when that digest is absent. A direct caller can
therefore construct a nominal ADR-0020 version-4 candidate that is not bound to the final
Gate-2 cost product. The production caller supplies the digest, but the builder itself is
the candidate authority boundary and must fail closed.

Make the argument required and reject anything other than one lowercase 64-hex SHA-256
before returning a candidate. Update the existing direct-builder test to supply a valid
digest and add focused invalid-identity coverage without changing plan-lineage semantics.

### P2 - one retained-content test now exercises the preceding path check

`test_delivery_price_response_is_proved_against_its_retained_bytes` writes bad bytes to
`delivery.json` while expecting the retained-content error. The corrected production code
first rejects that filename as non-content-addressed, so the assertion cannot match. Put
the deliberately bad bytes at the response digest filename so the test reaches the content
rehash branch. Keep the separate non-content-addressed-path test unchanged.

### P2 - the test file fails the clean-diff boundary

`git diff --check` reports `new blank line at EOF` at test line 8331. Remove only the
surplus EOF line. No reviewer test or Ruff result was run or accepted.

## Corrective source authorization

Sr Dev - Claude Build using Claude Opus 5 may correct only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude changes only the four bounded regions above. The authority tables and validation,
delivery-price production logic and new provenance tests, cost economic rules and their
fresh/reuse/recovery wiring, full-manifest digest domain and report publication, cost-source
selection, candidate lineage/no-mutation flags, CLI, fixtures, and every other path are
frozen.

Claude performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, repository-record edit, ADR edit, CLI edit, fixture edit, Git operation,
commit, push, migration, sample acquisition, Gate 2, Nautilus, Harmonic Trader, PAPER,
LIVE, or other-ticket work. It stops for reviewer source inspection with both exact
SHA-256 values and the unique CEX test-function count. Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/139_CEX002_CLAUDE_ADR0020_CORRECTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

No developer source/test/CLI/fixture path, data, checkpoint, cache, journal, sidecar, or
unrelated dirty path belongs to this publication. The reviewer executes no pytest, Ruff,
repository-control, candidate, migration, sample, or data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate integration/execution,
plan migration, sample acquisition, Gate 2 and every later gate, Nautilus work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, and every next ticket remain unauthorized.
Next ticket remains `NONE`.
