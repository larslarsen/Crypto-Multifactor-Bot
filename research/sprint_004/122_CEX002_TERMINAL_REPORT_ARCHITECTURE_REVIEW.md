# CEX-002 Terminal Report Architecture Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `96c55da64e0f4b8fc0ee8797d9bdaa8a1c6f515d`

Subject record: `research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md`

Oversized terminal report:

- path: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`;
- SHA-256: `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`;
- bytes: `1,059,297,547`;
- state: preserved working-tree modification, not committed or pushed.

## Decision

**ACCEPT THE FIVE-PATH INTEGRATION AND TERMINAL STATUS-2 EXECUTION. REJECT THE
MONOLITHIC REPORT AS A PUBLISHABLE ARTIFACT. ADOPT ADR-0019 AND ROUTE THE BOUNDED
REPORT-SPLIT CORRECTION TO CLAUDE BUILD.**

Commit `f05ee711f5db34421fae7f738aef00917bbdacf5` integrates exactly the five hashes
accepted by review 120. Commit `96c55da64e0f4b8fc0ee8797d9bdaa8a1c6f515d` publishes only
the two controls and record 121. Current `HEAD == origin/main` at the latter commit.

The real candidate completed in 1,963 seconds with status 2 after reusing 30,172 listing
requests and fetching the remaining 9,640. It used eight workers, one pooled client closed
successfully, 39 checkpoint serializations, and 22 retries. The checkpoint reached 40,771
entries; the lock, ledger, retained raw tree, and amendment-ledger absence remained exact.
This accepts ADR-0018's performance, bounded-resource, resume, and durability outcome.

The candidate remains honestly `BLOCKED`: 771 confirmed perpetuals, 63 unresolved names,
seven blocked source products, no plan migration, no sample acquisition, empty `samples`,
and `migration_authorized=false` / `download_authorized=false`. Gate 1 has not passed.

## Publication finding

The 1.06 GB size is structural. The completed manifest contains 733,203 selected rows and
7,833,966,625 compressed raw bytes. Static streaming inspection finds about 10.26 million
scalar values under top-level `acquisition_manifest` and another 10.43 million under
`storage`, because the detailed manifest is serialized twice. Git LFS would preserve the
bad representation while adding an unnecessary external storage dependency.

ADR-0019 instead keeps a compact tracked receipt and one complete deterministic,
content-addressed, stream-verifiable manifest detail artifact beneath the ignored data
root. This is lossless and preserves the full universe, fields, rows, lineage, collisions,
rejections, and pending-integrity evidence. No data scope or evidence standard is reduced.

## Record corrections and deviations

Record 121 incorrectly names `f987da5` as the review-120 publication/integration base. The
correct publication commit and integration parent is
`e99f47588208cddc1816fbbf5e0828ea3e39e801`; the integration commit is `f05ee71`.

Review 120 also incorrectly required pytest to collect 186 tests after recording 186
unique test-function definitions. Parametrization expands the accepted CEX test hash to
205 collected items, and all 205 passed. This count mismatch is a reviewer-authored
specification error, not a source/test failure. No rerun is warranted on the unchanged
integration. Record 121 abbreviates the executable as `python` rather than the required
`.venv/bin/python`; the later report must record exact commands without abbreviation.

Hermes continued after the literal count mismatch and used a Git reset to remove the
failed oversized-report commit even though review 120 prohibited both actions. Current Git
history and status prove the five-path integration, small publication, oversized report,
and unrelated dirty work remain present; no observed source or evidence loss resulted.
The deviations are rejected as workflow precedent. A failed large-artifact publication
must be handled only through an authorized forward correction, never an unapproved reset.

## Claude source authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to implement ADR-0019 in exactly:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude must:

- remove the duplicate detailed manifest from the storage block while preserving its
  complete top-level in-memory authority;
- implement deterministic, bounded-memory, atomic canonical-JSONL+gzip detail publication
  under a CLI-supplied store-relative evidence root;
- publish a compact atomic report 62 containing a complete descriptor and all
  low-cardinality evidence, below ADR-0019's fail-closed ceiling;
- implement a streaming validating reader for future Gate-2 consumption;
- preserve semantic identity through the uncompressed detail digest and summary counts;
- add the complete deterministic, tamper, traversal, count, atomic-failure, reuse,
  no-duplication, size-ceiling, and unchanged-authority test source required by ADR-0019;
  and
- preserve every accepted source, universe, cadence, membership, plan, storage, retry,
  checkpoint, secret, no-download, and exit-status contract.

The writer may use only the standard library and existing project helpers. It may not add
Git LFS, an external artifact service, a dependency, a paid service, a scope reduction, a
lossy summary, a sample, a report truncation, or a fallback that accepts missing detail.

The current 1.06 GB report and all data/checkpoint/cache/journal/progress paths are frozen.
Claude does not read, edit, move, copy, compress, delete, stage, or otherwise touch them.
It performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, record edit, ADR edit, Git operation, commit, push, plan migration, sample
acquisition, Gate 2, catalog, Nautilus, Harmonic Trader, payoff, PAPER, LIVE, or other-ticket
work. It stops for reviewer source inspection with exact hashes for the three authorized
paths and the unique CEX test-function count. Hermes and candidate execution remain
unauthorized until a later source acceptance.

## Reviewer publication

The reviewer publishes exactly:

- `docs/adr/0019-scalable-qualification-evidence-publication.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/122_CEX002_TERMINAL_REPORT_ARCHITECTURE_REVIEW.md`; and
- `tickets/CEX-002.md`.

The oversized report, source/test paths, data, checkpoints, caches, journals, database
sidecars, and unrelated dirty paths are excluded.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Report rerun, plan migration, sample
acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader
work, payoff analysis, PAPER, LIVE, and every other ticket remain unauthorized. Next
ticket remains `NONE`.
