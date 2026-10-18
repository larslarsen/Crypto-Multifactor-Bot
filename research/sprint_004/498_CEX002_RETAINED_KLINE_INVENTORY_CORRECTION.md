# CEX-002 Review 498 — Preserve accepted kline inventory scope

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Disposition: source accepted for conditional Hermes integration and one new preparation below

## Diagnosed defect and authority

Review 496's sole real prepare failed with reference_mismatch. Its separately
authorized read-only diagnostic passed authorities and membership, then identified
bar's _account_product physical-tree equality check. No referenced file was missing;
the reported extras were older content-addressed lineages.

Review 460 explicitly accepts only the exact descriptor-referenced sets and preserves
older unreferenced files outside those datasets. Record 459 records their physical
inventory. Their SHA-256 values are respectively
0f66a9ad6cb5d0e304a459f7c3498ace53aff0b82f3748d43d92a88af447ddf8 and
0e0b8ac855464d527d8230e5f0fc2373c0ce1c51f88d6ebe1ddf1efe860843d2.
The source's universal declared==disk rule contradicts that accepted scope.

| Product | Accepted partitions | Retained unreferenced Parquets | Retained unreferenced lineages |
|---|---:|---:|---:|
| bar_1h | 22,633 | 31 | 20,335 |
| trade_flow_1h | 22,633 | 47 | 20,335 |

The reviewer independently observed the corresponding physical partition/lineage
counts: 22,664/42,968 and 22,680/42,968. One current/older 0GUSDT 2025-09 lineage
pair hashes to its filenames and refers to the same accepted Parquet; the old document
uses schema_version 1, while the accepted current document adds the version-2 exclusion
accounting. Other older Parquets are also explicitly excluded by Review 460. Do not
promote any old artifact into the accepted dataset, bundle or consumer proof.

Choose the same GPT-6 Sol High source actor: it authored the accepted correction and
its integration passed 127 cases. This is a diagnosed source-authority/inventory fix
within the existing bundle adapter; GPT-6.1 remains reviewer and writes no source/tests.
Hermes may finish Record 497 publication in parallel, staging only that record.

## One-way developer prompt

Read this review, CURRENT_TASK, Review 460 and Record 459's inventory section. Do not
read archive or unrelated history. The owner directs continuation of the bundle work;
continue the existing directly supervised source-repair route. Exactly three writable
paths, starting at the accepted Record-495 bytes:

1. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
2. scripts/research/publish_binance_usdm_harmonic_bundle.py
3. tests/ingest/test_binance_usdm_harmonic_bundle.py

Correct only the diagnosed classification and its observability:

- Keep every accepted descriptor reference required and fully authenticated. Retain
  strict unexpected-file rejection for all other products and arbitrary files.
- For bar and trade-flow only, recognize Review-459's retained unreferenced inventory
  separately. Allow only canonical regular content-addressed partition Parquets and
  lineage JSONs under their exact symbol/month directory shapes; stream-verify each
  filename SHA and reject symlinks, unsafe paths, malformed names and unknown classes.
  Enforce the two production retained-kind counts above. A bounded private fixture
  seam may use smaller inventories; the public production CLI cannot bypass these pins.
- Exclude retained files from accepted manifests, table/main/gap counts, lineage mapping
  counts, bundle rows and consumer-proof components. Never delete, move, copy or repair
  them. Do not add old invalid observations to any accepted product.
- Report retained counts/bytes and a deterministic path/hash inventory digest separately
  in prepared authority metadata (or an equally bounded non-dataset audit field), so
  they are accounted for without becoming accepted files. Do not make product dataset
  identity depend on these excluded physical leftovers. Preserve existing resource caps
  and finite streaming/metadata bounds. No new architecture, schema or source authority.
- Improve the thin CLI's DatasetError reporting so the existing blocker token remains
  available and the message/context identifies the product/path. A future real failure
  must not require another preparation or private-function diagnostic merely to learn
  its error. Preserve the exit codes and all existing arguments.
- Add meaningful fixtures for both retained kinds, current versus older lineage, active
  descriptor-only economics, unchanged retained bytes on replay, missing accepted files,
  bad retained hash/path/symlink/class and production count guards. Preserve existing
  unknown-extra rejection tests. Verify CLI error context independently.

No catalog/generic source edits, accepted-data writes, new helpers, integration,
repository records, Git, installation, network or subagents. When edits are complete,
run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

No other test/lint/probe command. Stop on its first nonzero result with full output
and no edits/retry. Return the three final hashes/line counts and concise notes, then
stop for reviewer inspection. Hermes retains integration, evidence and Git ownership.
No second real prepare or external consumer run is assigned by this source review.

Reviewer publication scope is exactly this Review 498, Review 496's result note,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. No source/test integration is included.

## Source acceptance and conditional Hermes continuation

The selected GPT-6 Sol High developer completed the bounded correction and stopped.
Its single authorized targeted command above returned exit 0, 35 passing cases.
The reviewer inspected the complete production and test diffs and independently
verified these final bytes:

| Path | SHA-256 | Lines |
|---|---|---:|
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 6018280a0ed9ab16b585875e7f1c3bd3bc96233c90407b1b5bcb7f2a222c276a | 1921 |
| scripts/research/publish_binance_usdm_harmonic_bundle.py | cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9 | 102 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 08fc013675d70d31c3ef578d7c2ce810979485ecded032a916f0a29832ee02b9 | 1203 |

The catalog source and catalog test remain at Record 495's hashes, respectively
942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387 and
e4d7cf4335e87d8e7bb4ecb2f87dd106f601e845c47e369f095a784fe3c5f456.

Accept the three-path source drop for integration. The fix authenticates the finite
retained inventory separately, enforces production kind counts and filename hashes,
and leaves the descriptor closure required. Its audit affects prepared authority
metadata only, not dataset IDs, manifests, economics or consumer-proof inputs. Other
products retain strict unexpected-file rejection. The CLI preserves the blocker and
exit code while exposing the original message/context. The meaningful fixtures cover
both retained kinds, replay preservation, active closure and malformed inventory.
No reviewer test or producer execution occurred. No full-ticket acceptance is implied.

The owner directs continuation of this same bundle repair through the established
directly supervised Hermes route. After corrected Record 497 is published, authorize
the existing native Hermes session (Nous meituan/longcat-2.5-preview:free) to execute
the following ordered workflow. This final section supersedes the earlier source-only
prohibition on a second preparation, with exactly one new invocation after integration.
Preserve normal interactive approvals and unrelated changes. Do not author source,
tests or helper files; do not read archive. Stop execution at the first nonzero result,
denial, identity mismatch or resource blocker, without repair/retry. Terminal evidence
publication remains permitted after a producer failure.

1. Confirm HEAD equals origin/main, empty index, all five source/test hashes above,
   and the new bundle root is still absent (including no dangling symlink). Run once,
   in this order:

   ```bash
   .venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py scripts/research/publish_binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/python scripts/check_repo_control.py
   ```

2. If all pass, write only
   research/sprint_004/499_CEX002_KLINE_INVENTORY_INTEGRATION_RECORD.md.
   Record actual model, exact checks/results, three changed hashes, two unchanged
   catalog hashes and developer's separate 35-case result. Recheck all five hashes.
   Stage exactly the three changed paths above plus Record 499. Inspect staged names
   and git diff --cached --check. Commit as
   CEX-002: preserve excluded kline inventory during bundle preparation
   and push normally. Verify HEAD equals origin/main and empty index. Save that full
   source integration commit as SOURCE_COMMIT. Verify its committed five blobs match
   the frozen hashes. No amend/reset/force push or unrelated staging.

3. Before launching the producer, capture free bytes and BOTH complete ordered
   read-only SQLite query results from Review 496, step 2. Preserve all ID/status pairs
   and full deterministic JSON digests using
   json.dumps(rows,default=str,separators=(',',':'),ensure_ascii=False).encode().
   Require zero CEX rows and the same five REJECTED/REGISTERED quarantine rows.
   Save this full baseline before launch; truncated prefixes are insufficient.
   Reconfirm absent owned bundle root. Keep Review 496's unchanged allocations.

4. Invoke exactly once, substituting only SOURCE_COMMIT with step 2's literal full
   integration commit (never use the failed source commit 30719fd):

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit SOURCE_COMMIT
   ```

   Use native terminal background=true and notify_on_complete=true; retain the
   process identity and wait/poll that same process until terminal. No unsupported
   timeout, duplicate launch, private-function diagnostic or preparation replay.
   Accepted-product inputs are immutable; new producer writes are confined to
   data/.cex002_harmonic_bundle under its existing policy.

5. On success perform only Review 496 step 4's emitted candidate/manifest/footer/
   owned-inventory inspection. Include the new separate retained-inventory counts,
   bytes and digests; confirm they are excluded from the accepted manifests and bundle
   components. Report candidate SHA, eleven IDs/types and ten dependency edges,
   file/main/gap counts, bundle rows/bytes/SHA/schema, new metadata bytes and free
   space. Confirm consumable=false and no proof/publication or abandoned owned stages.
   On failure retain exact rich CLI output and terminal identity; do not inspect or
   repair product data. In either terminal case repeat only the same read-only catalog
   queries, require the saved full ordered-row digests/ID statuses unchanged, and
   capture remaining free space. No catalog admission, consumer run or replay.

6. Write exactly research/sprint_004/500_CEX002_CORRECTED_BUNDLE_PREPARATION_RECORD.md
   with the actual command/source commit, model, process/exit/output, correctly timed
   full catalog baselines, resources and terminal candidate facts or blocker. Publish
   that record alone with empty-index/staged-name/staged-whitespace checks, a normal
   commit/push and final HEAD==origin/main/empty-index verification. Stop for reviewer
   inspection. Record/Git failure stops publication; do not repair or retry.

Record 497 needs a record-only correction before acceptance: bar is the second
product; diagnostic exit 0 is separate from producer exit 1; command/output must be
exact or clearly labelled summaries; complete digests are post-launch/post-failure,
not a full pre-run baseline. The reviewer sent this correction to Hermes without
authoring implementation evidence. If already committed, publish a new record-only
correction commit rather than rewriting history. No producer repetition repairs that
historical evidence limitation.
