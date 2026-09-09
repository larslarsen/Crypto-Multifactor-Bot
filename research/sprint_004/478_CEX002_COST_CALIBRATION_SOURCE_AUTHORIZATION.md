# CEX-002 Review 478 - Cost Calibration Source Authorization

- **Date:** 2026-09-08
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept corrected Batch C source; authorize Hermes validation, integration and one local run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - eight products accepted
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Corrected source acceptance and Hermes workflow

This section is the current authorization. The initial assignment and consolidated
correction below are history and must not be replayed. The reviewer accepts the corrected
three-path source drop at these exact identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_cost_calibration.py` | 1,551 | `2026982aa275ffb09e5dceb75453d0290cd7c0b35e248f48e45cf3f3cee3b41d` |
| `scripts/research/normalize_binance_usdm_cost_calibration.py` | 57 | `196bbd5efec2465ca17a62b728eed754c85096c71409e8a35f47ba68a1b4162d` |
| `tests/ingest/test_binance_usdm_cost_calibration.py` | 907 | `0aa2c218e7cdccaef37327dbf9c4f9229fc74744bae01d98ad50843781a5d701` |

Sol ran the one authorized targeted pytest command once: 38 cases passed, exit 0. Its
complete output was `...................................... [100%]` (spacing abbreviated
here). No Ruff, integration or real-data result is claimed from the source author.

Static review closes the three consolidated findings. Publication now renames the held
verified staged file directly, verifies its inode and bytes, preserves conflicting winners,
and cleans only the current invocation's own failed temporary files. Source ordinals are
counted independently and their retained ranges must cover each source exactly once.
The five existing sizing allocations are bound and measured output bytes are enforced.
Every described Parquet/lineage/schema/row/byte fact and the full file/directory inventory
is re-proved around completion publication. The corrected tests cover these failure paths,
deterministic ZIP fixtures, interrupted replay and direct-rename inode preservation.

This is source acceptance only. Eight products remain accepted; cost calibration awaits
the real run and reviewer product disposition. No further source edits are authorized.

### Hermes assignment

The owner has authorized direct developer prompting. Hermes alone now owns the following
complete workflow. The reviewer replaces Laguna with `meituan/longcat-2.0:free`, listed
second in the live Nous Portal free recommendations on 2026-09-08. Solar, listed first,
previously failed tool transport; Laguna now repeated procedural errors after Batch B's
reporting errors. Longcat is the bounded replacement, not a claim of demonstrated
repository reliability. Hermes's role and the accepted source remain unchanged.

The reviewer halted and closed Laguna session `20260908_213716_d483b4` before validation,
integration or a data run. At HEAD `d22f8302853a1584a83b4f72420ce8aa6abd1d3e`, it used
`git diff --quiet` to test the index, received exit 1 from the intentionally dirty working
tree, and repeated that command despite the first-nonzero rule. It then compared Git blob
SHA-1 from `git hash-object` with the accepted file SHA-256 and falsely reported a source
mismatch. Its attempted nonexistent `shell` tool did not execute. All actual commands
were read-only. Reviewer inspection confirms the empty index, unchanged HEAD/origin and
the accepted three file SHA-256 values. This is a procedural rejection, not a source
defect. Record 479 must preserve these facts alongside the eventual result.

The reviewer explicitly reauthorizes the unstarted workflow below once under the replacement
session. This disposition clears only the failed preflight; it does not authorize a second
normalizer invocation or further automatic retries. Use `git diff --cached --name-only`
for the empty-index proof (empty output required), `sha256sum` for file identities, and
`wc -l` for line counts. Do not substitute `git diff --quiet` or `git hash-object`.

Run from `/home/lars/Crypto_Multifactor_Bot`. Preserve the unrelated dirty baseline.
Stop at the first nonzero command or failed proof, record the exact failure, and do not
patch source, retry, relaunch, delete output or diagnose by running additional mutating
commands. Read-only failure inventory and the terminal record are authorized after a stop.
An ordinary successful command does not require another reviewer or owner relay.

1. Prove `HEAD == origin/main` including this published review, capture the full hash,
   confirm the index is empty, and compare the three file hashes and line counts above.
2. Execute these checks in order, stopping at the first failure:

   ```bash
   PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_cost_calibration.py -q --tb=short
   PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_cost_calibration.py scripts/research/normalize_binance_usdm_cost_calibration.py tests/ingest/test_binance_usdm_cost_calibration.py
   python3 scripts/check_repo_control.py
   git diff --check
   ```

3. Stage exactly the accepted three Python paths, inspect the staged path set, run
   `git diff --cached --check`, commit and push them, and prove `HEAD == origin/main`.
   Reprove the three source hashes after integration. Do not stage unrelated paths.
4. Before the real run, rehash the pinned qualification, sizing and compressed v3 manifest
   files named below and compare them to their accepted hashes. Prove the accepted
   membership completion exists with its fixed hash. Confirm PyArrow is exactly 25.0.0
   and the writer identity is
   `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`.
   Prove `data/.cex002_cost_calibration` is absent and not a symlink; no cost normalizer
   process is live. Record exact available bytes using `statvfs.f_bavail * f_frsize`.
   Require at least **73,204,546,497 bytes**, the unchanged cost allocation
   37,957,477,079 + temporary-work bound 5,556,368,003 + operating reserve 29,690,701,415.
5. Run exactly one foreground local conversion with a **43,200-second** execution
   allowance. Hermes must be launched with `TERMINAL_MAX_FOREGROUND_TIMEOUT=43200`, and
   its terminal call must request `timeout=43200`; do not launch through a mechanism still
   capped at 600 seconds. This allowance is a ceiling, not a runtime prediction. Stay
   attached to the existing execution until terminal. No wrapper, detach, second process,
   retry or resume is authorized here. The exact command is:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_cost_calibration.py \
     --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
     --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
     --generation0-state data/cex002_qualify/gate2/state.sqlite \
     --generation0-content-root data/cex002_qualify/gate2/content \
     --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
     --recovery-root data/cex002_recovery \
     --membership-root data/.cex002_perpetual_membership \
     --output-root data/.cex002_cost_calibration
   ```

   Preserve these relative authority spellings. Record actual start/end timestamps in
   UTC, terminal exit code and observed elapsed duration. Do not convert local time to
   UTC by changing its label. Capture the immediate post-run available bytes separately
   from the output's logical file-byte sum.
6. On success, reconcile the sole completion's own digest; every referenced Parquet and
   lineage digest, size, schema and row count; the exact component/file inventories; empty
   staging and zero foreign/symlink objects; actual versus allocated bytes; and every
   per-source ordinal-domain/range equation. Reconcile 3,144 sources / 12,522,974,218 raw
   bytes, the 2,790/354 authority split, 909/2,235 family split, 494 frozen source gaps,
   771 fee gaps, zero historical fee rows and two policy rows. Report actual book rows,
   quote-state counts and partitions; projections are not observations. Read bounded
   real book-ticker/depth examples against the original raw rows, including the retained
   empty/one-sided states, exact decimals, timestamps and signed depth bands. Do not rerun
   the normalizer for reconciliation or rewrite accepted data. On failure preserve all
   partial output and report its exact inventory with no completion claim.
7. Publish the result as
   `research/sprint_004/479_CEX002_COST_CALIBRATION_INTEGRATION_AND_REAL_RUN_RECORD.md`.
   Record observed commands/exits, hashes, integration commit, timing, capacity, actual
   component counts/bytes, row/lineage reconciliation and limitations. Use exact observed
   fields; do not invent success, estimates, independent checks or workflow chronology.
   Reviewer acceptance remains exclusive. Update only `CURRENT_TASK.md` and the existing
   checklist/current-action portion of `tickets/CEX-002.md` in place, returning both actor
   fields to `Lead Quantitative Finance Researcher/Engineer`. Keep CEX-002 `IN_PROGRESS`,
   eight accepted products pending this review, next ticket `NONE`. Run repository control
   and whitespace checks after these edits; stage exactly those three record/control
   paths, run staged whitespace checks, commit, push, prove `HEAD == origin/main`, and stop.

Hermes may author temporary read-only reconciliation helpers as implementation evidence,
with their commands and identities recorded; this does not authorize production/test edits
or reviewer-authored implementation evidence. No acquisition, other-product rerun, Batch D,
catalog transaction, NautilusTrader, model, experiment or next ticket is authorized.

## Consolidated source disposition

The reviewer inspected the complete initial three-path drop, including Sol's final static
corrections, at these frozen identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_cost_calibration.py` | 1,179 | `9d17395e6dc3eae39839a1099e497f140821cecc7922e2b55c743da59dc30aec` |
| `scripts/research/normalize_binance_usdm_cost_calibration.py` | 57 | `196bbd5efec2465ca17a62b728eed754c85096c71409e8a35f47ba68a1b4162d` |
| `tests/ingest/test_binance_usdm_cost_calibration.py` | 702 | `66c3206cc22a3450ab9c2b19deff28e06cc8e6d36a22cdfd9402ca85cebb64f8` |

The full manifest selection, five component schemas, fee semantics, exact conversions,
quote/depth states and authenticated generation-0/recovery binding are retained. No source
or data acceptance is granted yet. No tests or normalizer commands were executed by the
reviewer or Sol for this initial drop.

The following is the consolidated blocking list, tied to the already authorized contract:

1. **Completion must prove the actual output inventory.** `only_completion` inspects only
   `.complete`; the normalizer never reconciles the rest of the tree to its descriptor.
   A pre-existing unreferenced file or symlink can remain while completion succeeds. An
   exception in `before_publish` leaves a JSON staging file; the existing interrupted-run
   test resumes successfully without checking that leftover. Reprove every referenced
   Parquet and lineage hash, schema/row/byte facts and the exact tree inventory before
   exposing completion. Reject foreign, incompatible, missing or unreferenced artifacts
   and unsafe paths. Keep staging handling ownership-bounded: clean a failed invocation's
   own temporary files in its failure path, retain verified partitions for replay, and
   never silently delete arbitrary pre-existing data. Test foreign files/symlinks,
   corruption or disappearance after a partition was published, interruption cleanup,
   and successful byte-identical replay with the required final inventory.

2. **Reconcile measured rows and enforce the accepted sizing bounds.** The descriptor's
   `physical_rows` is assigned the sum of output rows, so physical-versus-retained equality
   is asserted rather than independently counted during source parsing. Count each raw
   object's complete ordinal domain once and prove its rows are retained exactly once
   across partition ownership, including the adjacent-month case. Retain those per-source
   counts/ranges in lineage and the completion reconciliation. `NORMALIZED_ALLOCATION_BYTES`
   is currently metadata only, and `_validate_sizing` checks schema/batch size but not the
   component allocation contract. Bind the existing component row, byte and largest-file
   bounds; measure actual Parquet, lineage, gap and completion bytes and refuse an exceeded
   allocation before completion. Keep the zero-row official schema and all existing source
   rows; do not shrink data to meet the bound. Test measured row reconciliation across
   multiple objects/month boundaries and a deliberately reduced fixture allocation that
   must refuse completion. No new sizing version or arbitrary tolerance is authorized.

3. **Use the existing partition-atomic staging contract.** `_write_partition` closes its
   authenticated staged file, then `_publish_parquet_file` reopens its path and copies the
   whole partition into a second temporary file before renaming. ADR-0024 specifies that
   the verified staged partition itself becomes the final file. Publish that held,
   verified file directly with no-clobber rename or verify an identical existing winner.
   Keep creation, publication and cleanup under held no-follow directory descriptors for
   every component. Preserve bounded row-group streaming, fsync and final verification;
   test stage/path replacement and conflicting existing content without clobbering it.

Sol High remains the sole source author for this first consolidated correction. Edit only
the production and test paths above; the CLI is frozen. Preserve the accepted design and
address this list in place. Under the AGENTS.md targeted senior test exception, after the
complete correction Sol may execute this command **once**:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_cost_calibration.py -q --tb=short
```

Stop on its first nonzero result and report exact output without patching or rerunning.
On success report the exact result and frozen two-path hashes, then stop for reviewer
inspection. No Ruff, full acceptance suite, real-data conversion, network, integration,
Git, records or data publication is authorized. Hermes remains unauthorized pending the
source disposition. This exception supersedes the initial no-test instruction only for
the one enumerated corrective-drop command.

Reviewer read-only input checks also confirmed the exact disjoint 2,790/354 union and
independently reconstructed the unchanged complete cost-manifest digest. ZIP central
directories for all 3,144 selected objects contain one member each; the maximum expanded
ticker member is 1,593,414,699 bytes and depth member 2,139,688 bytes, both within the
proposed 2 GiB ceiling. First-row inspection of all 909 selected ticker objects found no
transaction timestamp outside its source day. These are bounded metadata/row inspections,
not a whole-corpus CRC, economic validation, test result or real-product acceptance.

## Assignment

The owner directs continued work and direct developer prompting. The reviewer assigns
GPT-5.6-sol High as the sole senior for Batch C, based on its accepted prior product work
and the authority, exact-numeric and publication risks here. Direct sub-agent delegation
and consolidated feedback are authorized for this drop. Existing role ownership remains.

Author exactly these three new paths:

- `src/cryptofactors/ingest/binance_usdm_cost_calibration.py`;
- `scripts/research/normalize_binance_usdm_cost_calibration.py`; and
- `tests/ingest/test_binance_usdm_cost_calibration.py`.

Deliver the complete source and test source, then stop for one consolidated reviewer
inspection. Do not execute tests, Ruff, acceptance commands, real normalization, integration,
Git, network, data mutation or repository-record edits. Hermes validation and integration
will be authorized with the source disposition. No other senior is assigned concurrently.

## Fixed input boundary

This is Review 474's existing Batch C, not a new acquisition plan or schema version.
ADR-0024/0025/0026/0027 and the accepted sizing contract govern. The five qualification
samples mentioned in ADR-0026 are not a cap on the complete frozen cost manifest.
The ticket and frozen `storage.cost_sample` require all 3,144 selected whole-day objects:
909 book-ticker and 2,235 book-depth objects, totaling 12,522,974,218 compressed bytes.
All source fields and rows must be retained. Do not substitute `cost_source_sample` or the
sizing coefficient cohort for this manifest. Do not acquire full historical book archives.

Read-only inspection of the accepted generation-0 completion table found 2,790 of these
keys present; the other 354 are book-ticker keys covered by the already accepted v3 direct
recovery (Review 415). Bind the disjoint union to the exact selected key set; no new
download or reopening of Gate 2 is required.

Pinned authorities:

- qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`,
  SHA-256 `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`;
- sizing `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`,
  SHA-256 `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`;
- complete cost manifest digest
  `04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`;
- generation 0 `data/cex002_qualify/gate2/state.sqlite` and its `content/` sibling,
  seal head `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`;
- v3 gzip JSONL manifest
  `data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz`
  (compressed SHA-256 is its filename), recovery root `data/cex002_recovery`;
- accepted membership completion
  `01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3`
  (Review 465), exactly 771 native membership identities.

Reuse the existing generation-0 authentication and immutable-publication patterns without
editing accepted modules. Authenticate the report, sizing, sealed plan/completion/sidecar
chain, v3 manifest and selected raw bytes before their publication. Retained-credit states
remain valid only under the existing authenticated authority contract. V3 retrieval and
publication times not proved by retained evidence remain unknown. Preserve source key,
checksum, revision, raw ordinal, source event time and availability/retrieval distinctions.
No filesystem mtime becomes a historical availability clock.

## Product contract

Publish one hidden `binance_usdm_cost_calibration` product with the five heterogeneous
component schemas pinned in `typed_schema_contract.cost_component_schemas`:

1. `retained_book_ticker`: every selected update ID, bid/ask price and quantity,
   transaction time and event time, with raw reference/ordinal and native identity.
2. `retained_book_depth`: every selected timestamp, signed percentage band, depth and
   notional, with raw reference/ordinal and native identity.
3. `official_fee_schedule`: the schema-bearing zero-row component required by ADR-0026.
4. `fee_authority_gap`: exactly 771 instrument/version-scoped
   `historical_fee_schedule_unavailable` rows, using the accepted identity state and
   nullable canonical IDs honestly.
5. `scenario_policy`: exactly the two pinned ADR-0026 rows, 0.0005 primary and 0.0010
   sensitivity per executed side; `ASSUMED_CONSERVATIVE`, policy knowledge time
   `2026-08-23T03:00:00Z`, all credit/rebate/discount flags disabled, exact source basis.

These policy rows are immutable experiment configuration. They are not historical fee
observations, a historical upper bound, or backdated FEE-001 reference rows. Missing fees
never become zero cost. Zero rows are expected only for the explicit official-fee component.

Use frozen types, nullability, writer settings and component/native-symbol/UTC-month
partitioning. The unchanged cost allocation is 37,957,477,079 bytes, with 3,865 projected
component partitions (866 ticker, 2,226 depth, 771 fee gaps, one official-fee schema and one
scenario partition). Sizing row projections are bounds, not observed row counts. Keep
memory bounded by streamed row groups and one partition; do not materialize the entire
book corpus or all large partitions as Python rows. Use the existing 65,536-row writer cap.

Parse decimals and times exactly with integer/context-independent conversion. Preserve
headed/headerless formats, one-sided and empty quote states, and legitimate zero depth.
Do not impose positive liquidity or a two-sided-book requirement: ADR-0020 permits thin,
one-sided and empty quote states. Reject negative or inconsistent quote values, crossed
two-sided quotes, malformed fields, overflow, non-finite values and corrupt/unsafe ZIPs.
Repeated timestamps and depth bands are not a fixed-cadence missing-event grid. Retain
source observations and ordinals; do not silently deduplicate, repair or drop records.
Use transaction time for ticker partition attribution while preserving event time, and
source timestamp for depth; explicitly handle any source-day boundary observations
without silently omitting them. Report a source-contract conflict before inventing a rule.

Retain the frozen cost-sample source gaps with their native membership and family scope
in completion/lineage metadata for Batch D. Do not manufacture hourly/daily event gaps
between the selected sample days or expand coverage beyond the frozen sample.

Use content-addressed Parquet and lineage, no-clobber atomic publication, bounded staging,
schema/byte/row/hash verification, deterministic ordering and byte-identical replay. A
completion descriptor reconciles the exact source set, every component and physical row,
all schemas and code/config identities, partition/lineage digests, quote-state counts,
fee absence and policy meaning. Existing conflicting, symlinked, stale, unreferenced or
incompatible output must fail safely. No partial release is consumer-visible.

Test source must cover the real physical formats, exact numerics and clocks, quote/depth
states, full-manifest selection across generation 0 and recovery, authentication failures,
771-identity fee-gap/scenario semantics through bounded fixtures, partition streaming,
corrupt/unsafe input, no-clobber publication, interrupted replay and completion rejection.
Tests must not require production data or network and must not present fixtures as release
evidence. Report exact file hashes/line counts, design choices and any unresolved blocker.

## Review boundary and publication scope

Batch A/B remain accepted; do not rerun or alter them. Batch D, catalog transactions,
NautilusTrader, models and the next ticket remain unauthorized. Review 474's checklist is
unchanged. This source authorization is not product acceptance.

Under the reviewer governance-publication exception, the reviewer may stage, commit and
push exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
All unrelated dirty paths remain untouched. This publication executes no acceptance
commands, integrates no developer source and mutates no data.
