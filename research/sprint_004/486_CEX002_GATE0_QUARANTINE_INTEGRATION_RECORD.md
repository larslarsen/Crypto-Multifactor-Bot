# CEX-002 Record 486 - Exact-five BitMEX quarantine integration outcome

- **Date:** 2026-10-17
- **Actor:** Grok Build (grok-4.6 High), owner-approved bounded execution exception
- **Source author:** Sr Dev - Codex Sol (GPT-6.1 Sol High); frozen seven-path drop
- **Source integration:** Jr Dev - Hermes; commit `49e307e0114ab7320b821a208095f678c3c183a2`
- **Ticket:** CEX-002
- **Decision:** terminal execution record for the exact-five catalog quality transition and authenticated no-op replay. This does not accept Gate 0. Reviewer acceptance is exclusive.
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - ten of eleven products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

This record completes Review 485 steps 5-8 under the owner-approved Grok execution exception in the final section of Review 485. Validation, source integration, real dry-run, and the corrected read-only inspection were preserved and were not rerun. No source or test path was edited.

## 1. Preserved prior results (not rerun)

Review 485 already accepted and closed these results. This session did not repeat them.

| Step | Actor / model | Result | Identity |
|---|---|---|---|
| Targeted pytest | Codex Sol | 137 cases, exit 0 | frozen seven-path drop |
| Integration pytest | Hermes (`meituan/longcat-2.5-preview:free`) | 225 quarantine/catalog cases, exit 0 | Review 485 |
| Focused Ruff | Hermes | All checks passed, exit 0 | seven frozen paths |
| `python3 scripts/check_repo_control.py` | Hermes | `Repo control check: PASS`, exit 0 | integration publication |
| `git diff --check` | Hermes | empty, exit 0 | integration publication |
| Source integration | Hermes | commit `49e307e0114ab7320b821a208095f678c3c183a2`; HEAD equaled origin/main after push | `CEX-002: integrate exact-five BitMEX quarantine` |
| Real dry-run | Hermes | exit 0; `disposition=inspected`, `applied=false` | `research/sprint_004/486_CEX002_GATE0_QUARANTINE_DRY_RUN.json` |
| Corrected read-only inspection | Hermes (`stepfun/step-3.7-flash:free`) | exit 0 | quoted below |

Sol targeted command and output, preserved from Review 485:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_bitmex_funding_quarantine.py tests/catalog/test_resolve_latest_by_type.py -q --tb=short
```

```text
........................................................................ [ 52%]
.................................................................        [100%]
```

Hermes integration command, preserved from Review 485:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/acquisition/test_bitmex_funding_quarantine.py tests/catalog -q --tb=short
```

225 cases passed. Focused Ruff, repository control, and whitespace passed. The seven frozen hashes after integration, still present at this session:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/acquisition/bitmex_funding_quarantine.py` | 535 | `40fdf5dc09f628ecd9bff4a95c0fa804159b51b911768def95c587e8b8810181` |
| `scripts/research/quarantine_bitmex_funding.py` | 66 | `03c53c0e98a11d60ebca1d554bb8d978e726fb4c5530e280f00cb56dde53b257` |
| `tests/acquisition/test_bitmex_funding_quarantine.py` | 712 | `23e241f506eb07fe3ec0a01a16220cbd434516b5fc26e04b904d0508686c8e81` |
| `src/cryptofactors/catalog/dataset/catalog_store.py` | 587 | `029d3cf77ad95056139f51ae1cc88207b88a716918c88de9158eb9107dc0b620` |
| `src/cryptofactors/catalog/dataset/errors.py` | 88 | `3b2f37436e44f85c81dab696fc20144f5ab020439f6f0c9ffd1b7b8836c4c517` |
| `src/cryptofactors/catalog/dataset/__init__.py` | 123 | `3de121666142e1f4acf46c9b8fe9c2fffd0a5f838918bb76c24d4550fa36979d` |
| `tests/catalog/test_resolve_latest_by_type.py` | 372 | `d4b6be0aac9b361ef6415bc6d8f316b1e6bbce46c277474ff5e6c51700bdf651` |

Hermes real dry-run command, preserved from Review 485 (not rerun):

```bash
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_DRY_RUN.json --dry-run
```

Existing dry-run JSON `generated_at=2026-10-17T03:28:47.860470+00:00`. Observed fields: `disposition=inspected`, `applied=false`, `dry_run=true`, `idempotent_replay=false`, `artifacts_unchanged=true`. All five targets `quality_status=PASS`, `publication_status=REGISTERED`, `already_quarantined=false`. `inspections_pre == inspections_post` and `pre_resolver == post_resolver`. All five IDs were eligible. File SHA-256 `43a779e312ee5989c6b9d9e230b00b9103466839aa5319578900027993463c72` (43,188 bytes).

Corrected inspection output, preserved from Review 485 / Step 3.7 Flash, exit 0:

```text
target_count 5
all_quality ['PASS', 'PASS', 'PASS', 'PASS', 'PASS']
all_publication ['REGISTERED', 'REGISTERED', 'REGISTERED', 'REGISTERED', 'REGISTERED']
ids_match True
pre_post_equal True
applied False disposition inspected artifacts_unchanged True
```

## 2. Disclosed helper and provider failures (no catalog mutation)

These events are recorded as required by Review 485. None of them executed application or replay.

1. Hermes (`meituan/longcat-2.5-preview:free`) printed the five PASS/REGISTERED/`already_quarantined=false` values, then failed the first JSON helper with exit 1: `TypeError: unhashable type: 'dict'` from `set(d["targets"])`. Session `20261016_200920_21d18a`. Reviewer diagnostic export `/tmp/cex002_review485_hermes_inspection_stop.jsonl`. This is an evidence-helper defect. The accepted source and real dry-run remain valid.
2. Resumed Step-5 (`stepfun/step-5-preview:free`) returned upstream-capacity HTTP 429 before any tool execution. No corrected inspection, application, replay, or artifact mutation occurred.
3. Step 3.7 Flash completed the corrected inspection (exit 0) and then stalled. The reviewer interrupted the session (`Operation interrupted: retrying API call after error (retry 1/3)`). No application or replay command executed. Control returned to the reviewer.

## 3. Safety checks at this session (exit 0)

Pre-publication HEAD, before this record commit:

```
$ git rev-parse HEAD
eff67dde8e28722e045f537c8e7a24c230e131af

$ git rev-parse origin/main
eff67dde8e28722e045f537c8e7a24c230e131af
```

HEAD equaled origin/main at Review 485's latest publication `CEX-002: authorize bounded Grok quarantine completion`. `git diff --cached --name-only` was empty. Integration commit `49e307e0114ab7320b821a208095f678c3c183a2` is an ancestor (`CEX-002: integrate exact-five BitMEX quarantine`).

All seven frozen source/test hashes and line counts matched `/tmp/cex002_review485_final_source.json`. All twelve unrelated dirty source/config fingerprints matched `/tmp/cex002_review485_unrelated_hashes.json`. Dry-run JSON was present. Application and replay report paths were absent. No `quarantine_bitmex_funding` process was running.

`exp003.db` is a regular SQLite file, not a symlink (mode `0o100644`). `data/exp003_store` is a regular directory, not a symlink (mode `0o40775`). No catalog was created or migrated.

Unrelated dirty/untracked paths were left untouched.

## 4. Application (Review 485 step 5, command 2)

Exact standalone command, once, foreground:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_APPLY.json
```

```text
2026-10-17T04:10:58,102746458+00:00
disposition=applied applied=True dry_run=False idempotent_replay=False; report=research/sprint_004/486_CEX002_GATE0_QUARANTINE_APPLY.json
EXIT:0
2026-10-17T04:10:59,504053352+00:00
```

Apply JSON `generated_at=2026-10-17T04:10:58.396158+00:00`. File SHA-256 `d40ec5eb3622f56565a463de0cc81d2bbc1d7d7ddd79db75943f38b216e3cfe7` (46,084 bytes).

Observed apply fields:

- `disposition=applied`, `applied=true`, `dry_run=false`, `idempotent_replay=false`, `artifacts_unchanged=true`
- `reason=all-zero funding_rate and empty funding_interval; false PASS authority`
- `targets` identical to the dry-run (five pinned IDs)
- `inspections_pre` identical to dry-run `inspections_pre` and dry-run `inspections_post`
- all five pre rows `PASS` / `REGISTERED` / `already_quarantined=false`
- all five post rows `REJECTED` / `REGISTERED` / `already_quarantined=true`
- immutable manifest `manifest_quality_status` remains `PASS` on every target
- `pre_resolver.eligible_targets` has all five IDs; `post_resolver.eligible_targets` is empty
- `post_resolver.latest.bitmex_funding` and `post_resolver.latest.bitmex_funding_full` are both null

Quarantine metadata written into every catalog `quality_summary_json` (same `quarantined_at` on all five):

- `quarantine_marker=cex002_bitmex_false_authority`
- `quarantine_ticket=CEX-002`
- `quarantine_reason=all-zero funding_rate and empty funding_interval; false PASS authority`
- `pre_quality_status=PASS`
- `catalog_authority=REJECTED`
- `preserved_manifest=true`, `preserved_parquet=true`
- `quarantined_at=2026-10-17T04:10:58.396158+00:00`

Historical catalog `created_at` values remain: `1970-01-01T00:00:00+00:00` (`ds_4f82`, `ds_f61c`), `2026-07-24T01:32:06.704813+00:00` (`ds_11b6`), `2026-07-24T01:51:15.156657+00:00` (`ds_ab70`), `2026-07-24T04:00:41.830213+00:00` (`ds_ee8e`).

## 5. Replay (Review 485 step 5, command 3)

Exact standalone command, once, foreground, after the apply JSON matched the expected disposition:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/quarantine_bitmex_funding.py --db-path exp003.db --store-root data/exp003_store --report-path research/sprint_004/486_CEX002_GATE0_QUARANTINE_REPLAY.json
```

```text
2026-10-17T04:12:16,261992724+00:00
disposition=replayed applied=False dry_run=False idempotent_replay=True; report=research/sprint_004/486_CEX002_GATE0_QUARANTINE_REPLAY.json
EXIT:0
2026-10-17T04:12:18,527714452+00:00
```

Replay JSON `generated_at=2026-10-17T04:12:16.599685+00:00`. File SHA-256 `59e812fe3dc673f94141e3e306fbe1511501ac51ed0aec6428495471032bfd7e` (48,983 bytes).

Observed replay fields:

- `disposition=replayed`, `applied=false`, `dry_run=false`, `idempotent_replay=true`, `artifacts_unchanged=true`
- same `reason` and same five `targets`
- `inspections_pre == inspections_post`
- `inspections_pre` identical to apply `inspections_post`
- all five rows remain `REJECTED` / `REGISTERED` / `already_quarantined=true`
- original quarantine metadata unchanged, including `quarantined_at=2026-10-17T04:10:58.396158+00:00`
- `pre_resolver == post_resolver ==` apply `post_resolver` (empty eligible set; both latest IDs null)
- manifests still `manifest_quality_status=PASS`

## 6. Independent reconciliation (Review 485 step 6)

Read-only inspection of the three JSON reports, the ten report artifact paths, and SQLite URI `file:exp003.db?mode=ro`. No production helper was authored or imported. No test was authored or rerun.

Cross-report equalities:

- dry-run `inspections_pre` == dry-run `inspections_post` == application `inspections_pre`
- application `inspections_post` == replay `inspections_pre` == replay `inspections_post`
- `targets` identical across dry-run, application, and replay
- ten artifact records identical across all six inspection lists (path, sha256, byte_size, device, inode, mtime_ns, ctime_ns, mode)

Economics, every inspection list, fixed target order:

| Dataset ID prefix | Type | Rows | Symbols | Null rates | Nonzero rates | Empty intervals |
|---|---|---:|---:|---:|---:|---:|
| `ds_4f82fede83f4` | `bitmex_funding` | 14,376 | 2 | 0 | 0 | 14,376 |
| `ds_f61c69342932` | `bitmex_funding` | 32,768 | 5 | 0 | 0 | 32,768 |
| `ds_11b6665e7dcd` | `bitmex_funding` | 32,768 | 5 | 0 | 0 | 32,768 |
| `ds_ab70ebd21268` | `bitmex_funding` | 38,256 | 5 | 0 | 0 | 38,256 |
| `ds_ee8e9cd9ddd4` | `bitmex_funding_full` | 189,570 | 45 | 0 | 0 | 189,570 |
| **Sum** | | **307,738** | **[2,5,5,5,45]** | **0** | **0** | **307,738** |

Both manifest identities, distinct on every target, match Review 485:

| Dataset | Canonical `manifest_sha256` | Physical `manifest_file_sha256` |
|---|---|---|
| `ds_4f82fede83f446e3ca29522e6e5f5a0ad7fb6d03d8931f1300addfe413364933` | `7d43319236fc73f87bcbbcac19c2ec5028a70e5faed252ae9397ec83d1ca39f4` | `c26ec01f0fccae79da1b130d75803070bc1efe585b0a4bfe1e73be96aa1f24cc` |
| `ds_f61c69342932c78c370b7950faf46d3e78be3695dbde8e6077acf8ccfa115deb` | `6083d41c906f6bf4278b48a0cc6cd376a0c3c3bdc334fa94f42385eec8083ebb` | `9020c0faa95199d31d71c523f0fd86451088ce83dcb13a200cd86e74df6c1d1a` |
| `ds_11b6665e7dcd37cb85c0098f60681a252801bbc4f80cb053eccc0fa0ce3679ea` | `0e340f3e18f48bd93ccb3d8b00e17fe7883c677350a95c7dec677a08c1f274e6` | `0bd3c6d4bfc52642a05764b0b2b32b932bfe9b5e46379f5d9e4f0fdbdc32bc91` |
| `ds_ab70ebd21268fe47cbde63b266c0b6f41d0e2ca529d319e3f6f0aa5a5646f512` | `e7b64fc0312f6e2dea118bb3699734e85ce590ab519390cf5d1867edea7947e1` | `d434c8219ae382bb9f35164ebe3a05c76db845e5d0777a1ac8d1d02e7bf4fd92` |
| `ds_ee8e9cd9ddd4de87a0c68ef0ff9b4a0da6c6bd7692c96b9f29f8cca13daf46c8` | `a6427c8277f951a120984a654254e91d6e704b129aedf2bda8ee080a6cb4a39e` | `389a192f0d0c64d8403801946506c8f5841c37985cd9bef2c2e9e99b5f558bda` |

Independent rehash of the ten actual files from the report paths. Every path is a regular file (not a symlink). Reported sha256, byte_size, device, inode, mtime_ns, ctime_ns, and mode match `os.lstat` and SHA-256 of the file bytes:

| Path | SHA-256 | Bytes | Device | Inode | Mode | mtime_ns | ctime_ns |
|---|---|---:|---:|---:|---:|---:|---:|
| `.../ds_4f82fede.../manifest.json` | `c26ec01f0fccae79da1b130d75803070bc1efe585b0a4bfe1e73be96aa1f24cc` | 1,250 | 64513 | 19561077 | 33152 | 1784855300526275538 | 1784855300526275538 |
| `.../ds_4f82fede.../bitmex/funding/funding.parquet` | `0213d0b070b02c3a4db02f7028a21938b48237a806731ed4ba03166833b055e2` | 205,097 | 64513 | 19561076 | 33188 | 1784855300524350443 | 1784855300524350443 |
| `.../ds_f61c6934.../manifest.json` | `9020c0faa95199d31d71c523f0fd86451088ce83dcb13a200cd86e74df6c1d1a` | 1,279 | 64513 | 19562472 | 33152 | 1784855954740403130 | 1784855954740403130 |
| `.../ds_f61c6934.../bitmex/funding/funding.parquet` | `8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f` | 295,554 | 64513 | 19562471 | 33188 | 1784855954738242214 | 1784855954738242214 |
| `.../ds_11b6665e.../manifest.json` | `0bd3c6d4bfc52642a05764b0b2b32b932bfe9b5e46379f5d9e4f0fdbdc32bc91` | 1,293 | 64513 | 19563197 | 33152 | 1784856702874766067 | 1784856702874766067 |
| `.../ds_11b6665e.../bitmex/funding/funding.parquet` | `8246d1eb5c77f242bc01178c29aa2fa4e9b2a62ea6d4f15192b82735e42a9c3f` | 295,554 | 64513 | 19563196 | 33188 | 1784856702872757731 | 1784856702872757731 |
| `.../ds_ab70ebd2.../manifest.json` | `d434c8219ae382bb9f35164ebe3a05c76db845e5d0777a1ac8d1d02e7bf4fd92` | 1,293 | 64513 | 19563243 | 33152 | 1784857875159926724 | 1784857875160350252 |
| `.../ds_ab70ebd2.../bitmex/funding/funding.parquet` | `658ef0f1b5409aaf075ce40f385195712967bb0d369dfdf6a02785525436771e` | 409,230 | 64513 | 19563242 | 33188 | 1784857875157942379 | 1784857875157942379 |
| `.../ds_ee8e9cd9.../manifest.json` | `389a192f0d0c64d8403801946506c8f5841c37985cd9bef2c2e9e99b5f558bda` | 1,772 | 64513 | 19662892 | 33152 | 1784865641837114044 | 1784865641837200228 |
| `.../ds_ee8e9cd9.../bitmex/funding_full/funding.parquet` | `2ef8257c9724ca1949344175276c11b8f7764fd37eedfa866d5a47cf012fd215` | 1,187,191 | 64513 | 19662891 | 33188 | 1784865641832090836 | 1784865641832090836 |

Full paths are the `artifacts[].path` values in the three reports under `data/exp003_store/datasets/sha256/...`.

SQLite `mode=ro` returned exactly five `dataset` rows and five `dataset_file` rows for the pinned IDs. Every catalog column equals the corresponding replay `catalog_row`. Every file-row column equals the corresponding replay `catalog_files[0]`. The only `bitmex_funding` / `bitmex_funding_full` catalog rows are these five, all `REJECTED` / `REGISTERED`. Each `quality_summary_json` contains `quarantine_ticket=CEX-002` and `quarantine_marker=cex002_bitmex_false_authority`.

## 7. Disposition and stop

Application and authenticated no-op replay completed with exit 0. Immutable manifests and Parquets were not rewritten. Default latest resolution now excludes all five targets.

Gate 0 remains open. The separate BitMEX missing-to-zero / unconditional-PASS normalizer/publisher correction remains unassigned. This record does not accept Gate 0, the harmonic bundle, remaining Gate-4 work, Gate 5, CEX-002, or any next ticket.

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. Ticket and Gate 3 remain `IN_PROGRESS`. Ten products remain accepted. Next ticket remains `NONE`.
