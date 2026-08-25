# CEX-002 Claude Noncompliance and Grok Reassignment

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED FOR MATERIAL NONCOMPLIANCE; complete correction reassigned
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Grok Build on Grok 4.6 High
Next ticket authorized: NONE

## Inspected drop

The reviewer inspected Claude Build's claimed review-291 completion once at:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `4807864d6704bea998f280ec0c7a5a6a292361c57b77ba0b05e75b77b1b15aaf`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `30e32b4c1b2dbdcf38a0a5081529fbb4de1eddda7a98eb8a399dfbe53d4e0358`

The source, CLI, and test file contain 5,703, 151, and 2,296 lines. The test source has
78 test functions. No developer command result was supplied, and the reviewer ran no
test or acceptance command.

## Decision

Reject the drop for material noncompliance with review 291. This is not another source
review and it adds no new correction requirement. Review 291 was the complete static
checklist; the drop implements only a few local fragments while leaving literal reviewed
blockers in place.

The useful fragments are retained only as reference: two provider/outcome domain checks,
cleanup calls for private receipt/terminal files, a helper that chooses a repository or
store descendant root, an existing-completion charge settlement helper, durable-attempt
count labels in the run result, and three focused tests. None closes its full governing
invariant.

## Direct noncompliance evidence

1. `HttpxStreamTransport` still has `follow_redirects=True`. `request_with_retry()` still
   records an allowed status as successful and returns before body consumption. A streamed
   read failure remains outside retry and the worker still replaces its cause with a type
   name.

2. `attempt` still has no plan foreign key, while
   `test_coordinator_is_the_only_writer_and_settles_deterministically` still requires 16
   arbitrary non-plan identities to succeed. `run_metadata` remains unused. The semantic
   digest remains a newly computed, unanchored value and still omits the reviewed time and
   run fields. No predecessor receipt, watermark, authenticated prefix, or crash-tail
   reconciliation exists.

3. `coinalyze_charge` still lacks HTTP status, outcome, points, request proof, and
   retrieval/revision facts. Recovery still parses every published body as `200`.
   `mark_charge_published()` still ignores row count, completion can still settle a
   reservation directly, release can still delete any charge status, and over-ceiling
   state is still converted to zero remaining. The new existing-completion helper does not
   implement the reviewed strict transition or exact 569-row terminal join.

4. Retained Binance status is still inferred from mutable `validation_state`, terminal
   verification still does not re-prove exact progress/inode lineage, and retained
   Coinalyze inventory still is not plan-bound and reparsed into the exact mapping set.

5. `AcquisitionState.open()` and `bind_session()` retain the reviewed descriptor/lock
   leaks. `open_root_dir()` still accepts and creates a root by pathname; code identity,
   filesystem capacity, overrides, and ancestors are not descriptor-anchored. ZIP
   backslash/drive/symlink/duplicate/expansion handling and bounded numeric lexemes remain
   unchanged.

6. The coordinator queue is still unbounded. `consume_manifest()` still creates the full
   universe tuple. Terminal manifest and reconciliation facts remain unchanged, including
   the mislabeled sidecar-inclusive `unique_content_objects` field and omitted charge,
   attempt, revision, path, and sidecar evidence.

The three new tests cover provider/outcome labels, a manually changed published charge,
and happy-path attempt counts. They do not add the direct review-291 regressions and do not
exercise the remaining production defects.

## Actor decision

Claude has now returned two incomplete corrections on the same bounded assignment: the
review-290 continuation changed diagnostics and fixtures without repairing the shared
path, and this review-291 continuation implemented only local fragments of a six-part
complete contract. Claude is deauthorized for this drop under the accepted-result
reliability rule.

Review 289's Grok deauthorization is superseded only because the alternate senior actor
has now also failed the complete contract and no implementation or Jr role may make these
architecture-sensitive decisions. Grok is reauthorized for one clean, complete
replacement pass governed directly by ADR-0029 and review 291. The current 5,703-line
structure is not an implementation constraint; do not continue the local-patch pattern.

## Complete replacement authorization

Grok Build may rewrite exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Implement every review-291 invariant and direct regression as one coherent result. Preserve
the accepted source authority, counts, bytes, capacity basis, economic scope, ADR-0029
layer boundaries, and any byte-correct reusable primitive, but do not preserve a structure
that makes the invariants impossible to reason about. No other path may change. Use no Git.

After the entire replacement is complete, Grok inherits review 291's exact targeted
pytest and at-most-three-run repair exception. It is for post-review debugging, not for
incremental test-driven substitution. Stop on a pass, the third nonzero result, an
architecture ambiguity, an out-of-scope requirement, unsafe repository state, or any real
network/data access. Run no Ruff, control, qualification, sizing, capacity, real
plan/acquire/verify, network, Git, or other command.

Stop once with final hashes, test-function count, every authorized command result, the
corrected original shared exception type/cause, and exact three-path scope confirmation.
Hermes retains integration, broader tests/acceptance commands, evidence, and developer
source Git. No real plan, data, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, PAPER/LIVE, or next ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, real state/data/evidence, and unrelated dirty work are
excluded.
