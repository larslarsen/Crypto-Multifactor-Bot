# CEX-002 Review 485 - Gate-0 quarantine source correction

- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Decision:** authorize bounded corrective source only
- **Ticket:** CEX-002, IN_PROGRESS; ten of eleven products accepted
- **Next required actor:** Sr Dev - Codex Sol (GPT-6.1 Sol High)
- **Next ticket:** NONE
- **Base:** `89e2b10c1a06d74d482dd94b32e706325fece1e6`

## Purpose and routing

The owner directs continuation after coverage acceptance. Before bundle publication, close
Gate 0's unresolved false catalog authority. The reviewer selects GPT-6.1 Sol High for
transaction and source-authentication risk, its accepted coverage checker, and the owner's
explicit developer preference. Continue the owner-approved direct developer delegation and
review feedback workflow. Only one senior is assigned. Hermes retains integration, validation,
implementation evidence, and all catalog/data execution ownership.

This drop corrects quarantine and default resolution only. Gate 0 also requires the separate
BitMEX missing-to-zero/unconditional-PASS normalizer/publisher correction; that remains pending.
No accepted Binance product is reopened. The harmonic bundle, remaining Gate-4 checks and
Gate-5 release/consumer work remain required under Review 474.

## Read-only findings

The reviewer queried `exp003.db` using SQLite URI `mode=ro`. All five exact targets from
Research 54 remain PASS / REGISTERED. The historical draft is unintegrated CEX-001 source,
not accepted implementation. Static defects include an already-quarantined early return
before byte/economic authentication, optional/unvalidated manifest handling, preflight outside
the mutation transaction, an unconditional UPDATE rather than compare-and-swap, and migrations
even in CLI dry-run mode. These violate existing CEX-002 Gate-0 requirements.

Catalog `manifest_sha256` is the repository's canonical manifest identity, not SHA-256 of the
whole serialized manifest including its embedded digest. The existing strict manifest parser
must reprove identity; separately pin and check exact physical bytes. Preserve historical
catalog registration `created_at` differences from manifest publication time (notably ds_11b6).
The manifests and Parquets must never be rewritten.

| Dataset suffix/prefix (full IDs in Research 54) | Canonical manifest identity | Physical manifest SHA-256 |
|---|---|---|
| ds_4f82 | 7d43319236fc73f87bcbbcac19c2ec5028a70e5faed252ae9397ec83d1ca39f4 | c26ec01f0fccae79da1b130d75803070bc1efe585b0a4bfe1e73be96aa1f24cc |
| ds_f61c | 6083d41c906f6bf4278b48a0cc6cd376a0c3c3bdc334fa94f42385eec8083ebb | 9020c0faa95199d31d71c523f0fd86451088ce83dcb13a200cd86e74df6c1d1a |
| ds_11b6 | 0e340f3e18f48bd93ccb3d8b00e17fe7883c677350a95c7dec677a08c1f274e6 | 0bd3c6d4bfc52642a05764b0b2b32b932bfe9b5e46379f5d9e4f0fdbdc32bc91 |
| ds_ab70 | e7b64fc0312f6e2dea118bb3699734e85ce590ab519390cf5d1867edea7947e1 | d434c8219ae382bb9f35164ebe3a05c76db845e5d0777a1ac8d1d02e7bf4fd92 |
| ds_ee8e | a6427c8277f951a120984a654254e91d6e704b129aedf2bda8ee080a6cb4a39e | 389a192f0d0c64d8403801946506c8f5841c37985cd9bef2c2e9e99b5f558bda |

This is source-review discovery, not executed quarantine or acceptance evidence. Research 54's
307,738 rows, zero nonzero/null rates and 307,738 empty intervals remain expected observations
that execution must independently authenticate.

## Exact source scope and preservation

The reviewer preserved the seven prior working files byte-for-byte under
`/tmp/cex002_review485_preserved_source/` before authorizing edits. Their identities are:

| Authorized path | Prior lines | Prior SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/bitmex_funding_quarantine.py` | 612 | `95f5529442143634261e58b53eec79b5a84f8e45990374d5f5056578b5c0e401` |
| `scripts/research/quarantine_bitmex_funding.py` | 69 | `61d0b52b74fc3b009c9223fdbec679d5f2054d042b5d4907e7d0bd75b902ed10` |
| `tests/acquisition/test_bitmex_funding_quarantine.py` | 371 | `8b6e5f552a3d6112c17b227065639dad095c6142b534af11d0b1c3aeece39b29` |
| `src/cryptofactors/catalog/dataset/catalog_store.py` | 544 | `b5f9014aed8484845b8c58cca14d33359db5250a5912144872b60098e50e2b34` |
| `src/cryptofactors/catalog/dataset/errors.py` | 84 | `0c90bc572b9b5b1a7f3103d07bc106764500aff40f62019ac1c10e60bc58693a` |
| `src/cryptofactors/catalog/dataset/__init__.py` | 121 | `1385930627cca8b3a45076f587c97eedd9e0be91b2de94570fbe87c9ec35292a` |
| `tests/catalog/test_resolve_latest_by_type.py` | 339 | `b4056ab6abde09c0d7a07c58a33f2aa3b4dc80cea5046796d5c8bd1afb9beea6` |

Sol may replace/correct only these seven source/test paths. The preserved draft is evidence
and a defect reference; acceptance is against the full existing contract, never presumed from
that draft. Keep unrelated dirty files, especially all BitMEX normalizer/backfill and DEX files,
untouched. No new fixtures outside the named test file, shared refactor, migration, dependency,
package configuration, or record edit is authorized. Existing unchanged helpers are read-only
references. Do not access the archive.

## Required behavior

1. Production always targets exactly the five pinned IDs and their types, paths, Parquet hashes,
   sizes, row counts and symbol counts in Research 54 / the preserved target table. Bind both
   manifest identities above. Authenticate strict manifest/dataset identity and complete file
   list, corresponding catalog dataset/file rows, declared schema/code/config/coverage identity,
   file hashes/size, required economic columns, zero null/nonzero rates, exact symbol count and
   empty intervals on every invocation, including already-quarantined replay. Reject missing,
   altered, extra, conflicting or unsafe artifacts. No symlink/path traversal authority.
2. Apply only the catalog quality transition PASS to REJECTED with a CEX-002 quarantine marker,
   reason and preserved prior quality evidence. Publication state remains REGISTERED; immutable
   manifests retain their historical PASS label and bytes. Do not label this SUPERSEDED or
   silently support a different target set in the production CLI. Tests may build isolated
   equivalents through a clearly bounded test API.
3. Acquire an explicit SQLite write transaction before snapshot/authentication for application;
   use compare-and-swap against the inspected complete catalog row, require exactly one affected
   row, and roll back all five on any mismatch or postcondition failure. Protect dataset_file
   identity within the same transaction. Define nested/external-transaction behavior explicitly;
   never commit a caller's unrelated pending work. A complete valid prior quarantine is a
   reauthenticated no-op with unchanged original quarantine metadata. A partial/mixed set is a
   failure, not permission to finish a prior unknown operation. Recheck files and resolver
   exclusion before commit. Failed transactions leave all catalog rows unchanged.
4. Default latest resolution excludes REJECTED/QUARANTINED and non-REGISTERED records, retains
   existing PASS-before-warning and deterministic tie-breaking, and permits rejected historical
   inspection only through explicit audit mode. Quarantine checks all five IDs are excluded,
   not just that each target is not the latest one. Preserve unaffected catalog APIs and tests.
5. CLI requires an existing catalog/store, applies no migrations, and offers inspection-only
   dry-run through a read-only SQLite connection. JSON report records exact targets, complete
   catalog/file snapshots, both manifest hashes, byte/economic inspection, pre/post resolvers,
   applied/no-op disposition and unchanged artifacts. Write reports atomically and refuse unsafe
   destinations that could replace catalog/store artifacts; report failure must not imply
   transaction success was rolled back after commit. A subsequent genuine replay can recover
   reporting after a post-commit output failure without modifying prior metadata.
6. Test source must prove valid transaction and replay, authentication on replay, changed
   manifest/catalog/file/bytes/economic counts, partial state and wrong markers, extra file rows,
   symlink/path rejection, concurrent/CAS change refusal, failure after an early update rolling
   back every target, nested transaction ownership, read-only dry-run/no migrations, resolver
   filtering, preserved bytes, and safe report publication/error semantics. Fixtures must use
   real canonical manifests and real temporary SQLite/Parquet structures, not mock away the
   identities the tests claim to check.

## Source feedback and stop boundary

Sol returns all seven final file hashes/line counts and a concise behavior/test-source report.
No tests, real command, quarantine, database/data mutation, network, Git, integration, evidence
record, cleanup, bundle, other product, experiment or next-ticket work is authorized. Stop for
reviewer static inspection. Any targeted-test exception will be separately enumerated after
inspection. Hermes is not yet authorized to integrate or execute this drop.

## Reviewer publication

The reviewer may publish exactly this review, `docs/handoff/CURRENT_TASK.md`, and
`tickets/CEX-002.md` under the existing small-governance-publication exception. Repository-control
and whitespace checks concern this governance publication only; no source integration or
acceptance command transfers to the reviewer.

## Complete static source disposition and targeted feedback

The reviewer inspected the complete seven-path source/test drop. The old replay bypass,
manifest permissiveness, missing CAS, transaction ownership, resolver eligibility, and CLI
migration defects are corrected. Every target is authenticated before and after mutation in
one owned transaction. The source preserves both original manifest hashes and actual catalog
registration times. Canonical fixture tests exercise altered evidence on replay, complete-row
and file-row conflicts, triggers, early-update rollback, competing writers, pending external
transactions, dry-run and post-commit reporting failures.

The reviewer returned one exception-boundary/test mismatch: linked-store validation escaped
the quarantine error wrapper. Sol corrected it and removed carried unused test locals. Final
inspection finds no remaining source blocker under this bounded contract. This is source
acceptance for targeted feedback, not integration, real quarantine or Gate-0 acceptance.
Twelve unrelated dirty source/config files retain the reviewer's initial fingerprints.

Sol's explicitly authorized metadata-only probe used the unchanged strict manifest parser
and SQLite mode=ro; it exited 0 and accepted all five pinned manifests with their catalog
canonical identities. It did not read real Parquets or execute the quarantine pipeline.
Sol disclosed one initial read-only `git status`, contrary to its no-Git instruction. The
reviewer records that workflow deviation; no Git mutation occurred and no further Git use
is authorized for Sol. It does not change source or data acceptance.

Frozen candidate:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/bitmex_funding_quarantine.py` | 535 | `40fdf5dc09f628ecd9bff4a95c0fa804159b51b911768def95c587e8b8810181` |
| `scripts/research/quarantine_bitmex_funding.py` | 66 | `03c53c0e98a11d60ebca1d554bb8d978e726fb4c5530e280f00cb56dde53b257` |
| `tests/acquisition/test_bitmex_funding_quarantine.py` | 712 | `23e241f506eb07fe3ec0a01a16220cbd434516b5fc26e04b904d0508686c8e81` |
| `src/cryptofactors/catalog/dataset/catalog_store.py` | 587 | `029d3cf77ad95056139f51ae1cc88207b88a716918c88de9158eb9107dc0b620` |
| `src/cryptofactors/catalog/dataset/errors.py` | 88 | `3b2f37436e44f85c81dab696fc20144f5ab020439f6f0c9ffd1b7b8836c4c517` |
| `src/cryptofactors/catalog/dataset/__init__.py` | 123 | `3de121666142e1f4acf46c9b8fe9c2fffd0a5f838918bb76c24d4550fa36979d` |
| `tests/catalog/test_resolve_latest_by_type.py` | 372 | `d4b6be0aac9b361ef6415bc6d8f316b1e6bbce46c277474ff5e6c51700bdf651` |

Under AGENTS.md's **Targeted senior test exception**, the reviewer authorizes the same
Sol actor to execute exactly this one command once against the frozen corrective drop:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_bitmex_funding_quarantine.py tests/catalog/test_resolve_latest_by_type.py -q --tb=short
```

Report the exact command, exit code and terminal output. Stop immediately on a nonzero
result; no correction/retry is implied. No Ruff, full suite, integration, real-data command,
Git, record edit or catalog mutation is assigned. On success preserve the source bytes and
return to the reviewer for the next disposition. Hermes remains unauthorized pending that
disposition. This targeted result cannot accept the real quarantine or complete Gate 0.

## Targeted result and Hermes integration/execution authorization

Sol executed the enumerated command exactly once, exit **0**:

```text
........................................................................ [ 52%]
.................................................................        [100%]
```

All **137 cases passed**. The reviewer reproved all seven frozen hashes unchanged and
accepts the source for integration. This does not accept an unexecuted real quarantine.
Gate 0 remains open, including its separate pending normalizer/publisher correction.

The reviewer selects **Jr Dev - Hermes, `meituan/longcat-2.5-preview:free`**, without a
reasoning override. The Nous recommended-model endpoint was freshly checked and still
lists this exact zero-price model. Selection rests on its completed Review-483 standalone
workflow and functioning tool route, not its prior use alone. Its path-guessing, discretionary
search and evidence mistakes remain adverse evidence. This assignment eliminates discretionary
discovery and retry authority: use the exact paths and ordered commands below, with reviewer
supervision. Laguna's repeated stop-rule failures do not justify returning to that route;
an untested free route has no stronger repository acceptance evidence for this short workflow.
The selected role is execution/integration only; GPT-6.1 Sol remains the accepted source author.

Continue the owner's existing directly supervised Hermes workflow. Do not disable approval
checks or change configuration. Use interactive CLI, not quiet one-shot mode. A denied command
is a terminal failure, not retry authority. Stop on the first nonzero/failed proof, preserve
exact output, and publish the bounded terminal record; do not patch source or rerun anything.
No home-directory search, archive access, gitleaks discovery, installation, acquisition,
accepted-Binance-product rerun, normalizer/backfill edit/run, bundle or experiment is assigned.

### Complete ordered workflow

1. Read this review's final authorization and `CURRENT_TASK.md`. Prove HEAD equals origin/main
   at this review's latest publication, index empty, and seven hashes/line counts match the
   frozen table. Preserve every other dirty/untracked path. No broad discovery is needed.
2. Execute these validation commands in order, each as a standalone command, stopping on failure:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_bitmex_funding_quarantine.py tests/catalog -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/acquisition/bitmex_funding_quarantine.py scripts/research/quarantine_bitmex_funding.py tests/acquisition/test_bitmex_funding_quarantine.py src/cryptofactors/catalog/dataset/catalog_store.py src/cryptofactors/catalog/dataset/errors.py src/cryptofactors/catalog/dataset/__init__.py tests/catalog/test_resolve_latest_by_type.py
python3 scripts/check_repo_control.py
git diff --check
```

3. If all pass, stage exactly the seven frozen source/test files; prove the index contains
   exactly those files and their accepted bytes, run `git diff --cached --check`, commit
   `CEX-002: integrate exact-five BitMEX quarantine`, push and prove HEAD equals origin/main.
   No source/test edit is authorized, including lint fixes.
4. Confirm the existing `exp003.db` and `data/exp003_store` paths are regular database/directory
   paths, not symlinks, and all three exact report destinations below are absent. Do not create
   or migrate a catalog. The SQLite transaction itself acquires the write lock and reauthenticates
   every target. These tiny existing artifacts require no bulk capacity allocation.
5. Run the following three **standalone** commands in order, once each, with a foreground
   timeout of at least 600 seconds. Await each actual exit code. Inspect the completed JSON
   after each command for the expected disposition before proceeding. The expected dry-run is
   `inspected`, applied=false, all five PASS/REGISTERED and eligible; the application is
   `applied`, applied=true, all five REJECTED/REGISTERED and ineligible; replay is `replayed`,
   applied=false, idempotent_replay=true and the same quarantine metadata. Any mismatch stops.

```bash
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_DRY_RUN.json --dry-run
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_APPLY.json
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_REPLAY.json
```

6. Reconcile the three reports with a bounded read-only evidence inspection (no production
   helper or test authoring). The exact schema is `targets` (five target dictionaries),
   `inspections_pre` / `inspections_post` (five each), `pre_resolver` / `post_resolver`
   (`latest` and `eligible_targets`), and `artifacts_unchanged`. Each inspection contains
   `catalog_row`, `catalog_files`, `manifest_sha256`, `manifest_file_sha256`, `parquet`
   and `artifacts`. Assert dry-run pre == dry-run post == application pre; application post
   == replay pre == replay post. The ten artifact records (manifest and Parquet per ID)
   must retain exact path/hash/size/device/inode/mtime/ctime/mode entries across all reports.
   Rehash the ten actual files independently from their report paths and compare with those
   artifact hashes and sizes. Re-query the five actual dataset rows and dataset_file rows
   through SQLite URI mode=ro and compare with replay snapshots. Economics must sum to
   307,738 rows, zero null/nonzero rates and 307,738 empty intervals; symbol counts are
   [2,5,5,5,45] in fixed target order. Preserve both kinds of manifest hash distinctly.
   Record actual observations and exit codes, never guessed fields or unsupported PASS.
7. Publish `research/sprint_004/486_CEX002_GATE0_QUARANTINE_INTEGRATION_RECORD.md`, the three
   generated JSON reports (only those actually produced), `CURRENT_TASK.md` and the current
   checklist summary in `tickets/CEX-002.md`. Record exact commands, exits, validation output,
   source integration identity, real dispositions, immutable-file proof and any failure.
   Return both actor fields to Lead Quantitative Finance Researcher/Engineer. Ticket and
   Gate 3 remain IN_PROGRESS, ten products accepted, next ticket NONE. Do not mark Gate 0
   complete: normalizer/publisher correction remains pending and reviewer acceptance exclusive.
   On post-commit report failure (exit 2), record the reported catalog disposition explicitly;
   do not claim rollback or retry.
8. Run repository-control and whitespace checks for publication, stage only the record,
   actually produced reports and two control files, prove staged paths, check staged whitespace,
   commit `CEX-002: record exact-five quarantine integration outcome`, push, verify HEAD equals
   origin/main, and stop for reviewer disposition. Do not stage source again or unrelated files.

The workflow authorizes the existing exact-five catalog quality transition and one authenticated
no-op replay. It never rewrites historical manifest/Parquet files or accepts Gate 0 as a whole.
