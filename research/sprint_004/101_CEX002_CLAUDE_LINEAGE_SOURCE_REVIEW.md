# CEX-002 Claude Lineage Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `995ae18bab046699b930892b7cb126e4ed370bae`

Reviewed source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `06d9d9282fe965feb208503a2a364ab16cfa561ad0bca771707254feb6e23242` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `ec84ca6aa5b55e4dc89a70553922c070a8a1d96e6b15197911697b6b838bfa03` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `88d733db342682604811377b46a843c9ab232be027abbd53fa8d60bdb66797d7` |

The existing fixture directory is unchanged. Static counting finds 166 test functions, so
the accumulated suite remains present.

## Decision

**REJECT BEFORE JR INTEGRATION. AUTHORIZE ONE FINAL SURGICAL CLAUDE CORRECTION.**

Claude closes the five review-100 implementation defects: candidate mode no longer
bootstraps, reconciles, settles, or flushes the legacy ledger; a proved outstanding
reservation remains byte-identical; taker flow uses re-proved retained kline schema without
a sample fetch; the comparable digest is the future lock's `plan_content_digest`; the
envelope digest is separately named; current version must equal 2; and unproved manifest
rows are selected-but-pending and nonconsumable. The real retained lock is compatible with
the intended transition: current version 2, ordered history versions 0 and 1, 203 legacy
version-0 entries, and 146 version-1/current entries.

Two exact-transition defects remain. The reviewer ran no tests, lint, control command,
network/data command, migration, or real qualification.

## Blocking Finding 1: Invalid authority mutates before it is rejected

`run_source_qualification` does not load and validate the candidate's plan lock and legacy
ledger until the candidate branch near line 6715. Before reaching that branch it creates
the raw directory, inventories remote listings and their caches, fetches current-contract
authority, pins and flushes the durable holdout boundary near line 6558, and may recover
checkpoint evidence. A version-1, version-3, or malformed-history request can therefore
change the candidate store before the exact-authority error is raised.

Review 100 required every invalid transition to fail before candidate mutation. The new
parameterized test checks only that an exception is raised; it does not snapshot the store
or prove that no directory, holdout, cache, checkpoint, journal, listing, current-contract,
or Coinalyze operation occurred.

## Blocking Finding 2: The lineage parser is not exact or fully validated

`validate_prior_plan_history` converts `item.get("plan_version") or 0` with `int` and then
sorts the result. A missing version field is silently accepted as version 0, booleans and
numeric strings are accepted as versions, and reversed history `[1, 0]` is treated as the
expected `[0, 1]` transition. The version-0 plan is checked only for a nonempty `entries`
value; its entries are never parsed or structurally validated. The focused malformed case
empties only the version-1 plan and therefore misses this path.

`build_candidate_plan_v3` also forms `prior_digests` only from recorded digest strings.
The preserved version-0 record predates that field and contains an empty value, so it is
discarded even though its retained plan document can provide a deterministic derived
content identity. Review 100 required comparison against current and historical plan
content, with an identical historical plan unable to evade reuse detection through the
new allowance envelope.

## Final Surgical Claude Authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The CLI hash above is accepted and must remain unchanged. The fixture directory must remain
unchanged. Claude preserves every correction accepted in this review and changes only the
two findings above. The drop must:

1. perform candidate-only read-only preflight immediately after computing paths and before
   creating a directory or loading/using any mutable cache, checkpoint, journal, inventory,
   holdout, listing, current-contract, or Coinalyze facility;
2. hash, load, and validate the exact current version-2 lock and legacy ledger during that
   preflight, retain those in-memory objects for candidate construction, and rehash both
   authority files after construction;
3. require history in exact stored order `[0, 1]`, with each version field a non-boolean
   integer equal to its expected value; missing, string, boolean, duplicated, reversed, or
   later values fail closed;
4. parse both historical plan documents and structurally validate their entries and
   identities under version-appropriate contracts, allowing only the known absence of the
   pre-digest version-0 fields rather than treating any nonempty object as valid;
5. derive and report a deterministic version-0 plan-content identity from the preserved
   plan document, include it with version 1 and current version 2 in candidate reuse
   comparison, and never write that derived identity back to the lock; and
6. add focused tests proving every invalid transition leaves a recursive before/after
   snapshot of the complete store byte-identical and performs no index/current-contract or
   other remote call, plus direct missing/string/boolean/reversed/malformed-v0 and
   version-0-reuse cases.

Claude performs no tests, network/data run, plan or ledger migration, integration,
repository-record edit, Git operation, sample download, bulk acquisition, catalog mutation,
Nautilus work, Harmonic Trader work, or publication. It stops for reviewer source
inspection with exact hashes and the test-function count.

## Publication Set

Under the reviewer governance-publication exception, the reviewer may stage, commit, and
push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/101_CEX002_CLAUDE_LINEAGE_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, database sidecar, or unrelated dirty path
belongs to this publication. The reviewer executes no acceptance command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Hermes is unauthorized. Gate 1 has not passed. Gate 2, real
acquisition, normalization, catalog publication, Nautilus execution, other-ticket work,
Harmonic Trader work, payoff analysis, PAPER, and LIVE remain unauthorized. Next ticket
remains `NONE`.
