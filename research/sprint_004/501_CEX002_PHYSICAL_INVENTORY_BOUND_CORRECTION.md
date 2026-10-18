# CEX-002 Review 501 — Correct the physical inventory bound

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Disposition: integration accepted; terminal preparation failure accepted; bounded source correction

## Reviewed result and diagnosed cause

Accept Hermes integration 2395f03850c3941ed0e1145053f743b6c5f69c4c and Record 499:
all five committed source/test hashes match Review 498, the exact four-path commit was
pushed, 134 catalog/bundle cases passed, scoped Ruff and repository control passed.
The progress split in Record 499 is a minor reporting error: the native output is
72 plus 62 marks, not 67 plus 67; the total 134 and exit 0 are correct. No rerun is needed.
Record 500 independently pins the integration commit omitted from Record 499's literal
SOURCE_COMMIT placeholder; this review resolves that identity without another record cycle.

Accept corrected terminal Record 497 publication 9402536f8d05981da1e2c48fca0710719fdf0a0e
and Record 500 publication d9f77def49746b8ab2bc0d82583e030e9d5e0f4f as failure evidence.
The one corrected prepare, native proc_caa44bb65052 / PID 1286281, exited 1 with
metadata_bound: kline physical inventory exceeds the accepted bound, product
binance_usdm_trade_flow_1h. The full read-only catalog digests were captured before
launch and after failure and match. Zero CEX release rows remain; the bundle root was
not created. No producer repetition or accepted-data repair has occurred.

The reviewer independently inspected physical filename inventories, not product tables:

| Product | Partition files | Lineage files | Quality-gap pair + completion | Total |
|---|---:|---:|---:|---:|
| bar_1h | 22,664 | 42,968 | 3 | 65,635 |
| trade_flow_1h | 22,680 | 42,968 | 3 | 65,651 |

Record 459's component counts were correct but its summed totals were one short:
22,633 accepted partitions + 22,633 accepted lineages + 3 metadata/gap files = 45,269,
not 45,268. Adding the accepted retained counts gives the totals above. Review 498
adopted the erroneous 65,650 total, and the reviewer missed that arithmetic error.
This correction supersedes those summed totals only. Descriptor hashes, retained kind
counts, rows, schemas, authority and accepted product bytes stay unchanged.

## One-way source prompt

Continue the existing owner-approved directly supervised source-repair route using the
same GPT-6 Sol High actor, which already holds this adapter's context and delivered
the integrated correction. GPT-6.1 remains reviewer. Read CURRENT_TASK and this review.
Exactly two writable paths:

1. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
2. tests/ingest/test_binance_usdm_harmonic_bundle.py

Replace the erroneous universal kline physical count with a finite bound derived from
the authenticated accepted file closure plus that product's already pinned permitted
retained counts. Pass the accepted closure count into the private walk if useful, or
use an equally explicit per-product derivation. Do not merely add unexplained slack.
The real bar/flow totals 65,635/65,651 must fit. Preserve missing-reference rejection,
exact production retained-kind counts, path/hash/symlink checks, strict unexpected-file
rejection for every other class/product, resource limits and excluded-file semantics.
No fixture or public production switch may bypass the finite bound.

Add a meaningful boundary regression that permits the complete accepted closure plus
exact allowed older inventory and rejects one additional regular physical file with
metadata_bound. Check both product limits, including the completion and quality-gap
pair. Use a bounded synthetic walk/file-metadata fixture if needed; do not create or
read 65,000 real data files. Keep the test independent enough to catch omission of one
of the three metadata/gap files and cross-product use of the larger bound. Preserve
existing authentication and arbitrary-extra rejection tests.

No other source/CLI/catalog changes, records, Git, integration, helper files, data writes,
real producer/accounting probes, network, installation or subagents. Once source is
finished, run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

Stop on the first nonzero result without edits/retry. Return exact output/exit and
two final SHA-256 values/line counts, then stop for source review. Hermes is stopped;
no third real preparation is authorized by this source assignment.

Reviewer publication scope is exactly this Review 501, docs/handoff/CURRENT_TASK.md
and tickets/CEX-002.md. This publication excludes source/tests and implementation evidence.

## Final source acceptance and Hermes workflow

The developer removed an unnecessary proposed duplicate-reference rejection before
testing; that rule is not part of the final drop. The single authorized targeted command
returned exit 0 with 37 passing cases. The reviewer inspected the complete final source
and test diffs and independently verified:

| Path | SHA-256 | Lines |
|---|---|---:|
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1370c63017275692c4b43c8577bcee8c3475ea357bf041a446a6ccec4debd3e5 | 1925 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | e91ac496b1de969b975c0dd95b3ef0c79340d7b0ed8f0ce6310761e917baf1b4 | 1239 |

Accept these bytes for integration. The physical bound is the unique authenticated
descriptor-path count plus that product's frozen retained-kind allowance; all existing
classification, digest and symlink rules remain. The synthetic walk test permits exactly
65,635/65,651 files and rejects the next regular file for each product, without physical
data creation. There is no public bypass or unexplained slack. No reviewer test ran.
The source actor has stopped. Acceptance of the real bundle remains pending.

Continue the owner-approved direct Hermes route with the existing native session and
Nous meituan/longcat-2.5-preview:free, which completed the preceding checks and correctly
stopped/published the terminal failure. This final section explicitly authorizes one new
prepare only after the new integration below. Keep normal approvals, first-failure stops,
immutable accepted products and unrelated changes. Do not author source/tests/helpers,
install, acquire, read archive, repair or retry. GPT-6.1 remains reviewer.

1. Confirm HEAD==origin/main, empty index and the two frozen changed hashes above.
   Verify the three unchanged hashes from Review 498: CLI cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9,
   catalog source 942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387,
   catalog test e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456.
   Confirm absent bundle root including no dangling symlink. Run exactly once in order:

   ```bash
   .venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/python scripts/check_repo_control.py
   ```

2. On success write research/sprint_004/502_CEX002_PHYSICAL_BOUND_INTEGRATION_RECORD.md
   with actual model, exact validation commands/results and the five hashes. Distinguish
   the developer's 37-case run. Stage exactly the TWO changed paths above and Record 502;
   inspect names, frozen hashes and git diff --cached --check. Commit as
   CEX-002: derive physical inventory cap from accepted closure
   and push normally. Verify HEAD==origin/main and empty index; save this full new
   source integration commit and verify its five committed blobs. Do not use an old
   source commit for execution. No amend/reset/force push or unrelated staging.

3. Execute Review 498 final workflow steps 3–5 exactly, substituting only this new
   source integration commit. Those steps capture full ordered-row catalog baselines
   BEFORE launch, verify zero CEX rows/five rejected IDs and absent bundle root, launch
   the exact prepare command ONCE with background=true/notify_on_complete=true, track
   its same native process to terminal, inspect only emitted candidate metadata/footer
   on success, and repeat the same read-only catalog snapshots/free-space observation
   afterward. The prepared release remains non-consumable. Existing allocations,
   resource reserves and new-write confinement to data/.cex002_harmonic_bundle persist.
   No private-function diagnostic, second invocation, catalog admission or consumer run.

4. Publish terminal evidence only as
   research/sprint_004/503_CEX002_PHYSICAL_BOUND_BUNDLE_PREPARATION_RECORD.md,
   applying Review 498 step 6's record-only scope and Git checks. Include actual literal
   command/full source commit, model/process/exit/output, correctly timed full catalog
   digests, resources and candidate facts or exact blocker. A producer failure stops
   execution without retry; terminal evidence publication is still allowed. Any earlier
   validation, identity, Git or approval failure stops the workflow without repair/retry.
   Verify normal push, HEAD==origin/main and empty index, then stop for reviewer inspection.

No additional source, new ticket, product rerun, replay, proof generation, catalog
publication or final Gate acceptance is authorized by this continuation.
