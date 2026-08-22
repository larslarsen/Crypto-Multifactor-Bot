# CEX-002 Migration Ruff Integration and Failed Migration-Only Invocation

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/157_CEX002_MIGRATION_RUFF_SOURCE_ACCEPTANCE.md`

## 1. Import-cleanup integration

Hermes established:

`HEAD == origin/main == 8a320049a5cb10be1b49a193db5d82201e6073f4`

before staging.

Accepted path hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |

The corrected test path contained 285 unique `test_` function definitions. `git diff
--check` was clean for the accepted test path.

Hermes staged exactly:

`tests/acquisition/test_binance_usdm_harmonic_qualification.py`

and committed:

`21fb4ecfe7bf4600578838388c3e74a2a657e6a8`

Commit message:

`CEX-002: integrate migration ruff cleanup`

After push:

`HEAD == origin/main == 21fb4ecfe7bf4600578838388c3e74a2a657e6a8`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
Hermes made no source or test edit after integration.

## 2. Focused command sequence

Review 157 required a full restart of review 151's stop-on-first-failure sequence after
the import-cleanup integration commit was pushed. All five commands returned exit 0.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 0

Output:

```text
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 94%]
......................                                                   [100%]
```

The invocation did not print a collected/pass summary line under `-q --tb=short`; Hermes
does not infer missing pass or collection counts.

### C2

Command:

`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`

Exit: 0

Output:

```text
..................                                                       [100%]
```

The invocation did not print a collected/pass summary line under `-q --tb=short`; Hermes
does not infer missing pass or collection counts.

### C3

Command:

`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`

Exit: 0

Output:

```text
All checks passed!
```

### C4

Command:

`python3 scripts/check_repo_control.py`

Exit: 0

Output:

```text
Repo control check: PASS
```

### C5

Command:

`git show --check --oneline --no-renames HEAD`

Exit: 0

Output:

```text
21fb4ec CEX-002: integrate migration ruff cleanup
```

## 3. Migration preconditions

No `python3` qualification process was running before the migration-only invocation.

Before snapshot:

| Evidence | Result |
|---|---|
| production source | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| qualification CLI | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| CEX test path | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |
| report 62 | 13,946,727 bytes, `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes, `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| version-2 lock | 381,855 bytes, `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy ledger | 777 bytes, `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint/progress | 299,571 bytes, `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| sample plan | 101,930 bytes, `02752b25d9fcfb1b9e4602bde23c8847f870578218e882213b56290b94704c12` |
| retry journal | 12,977 bytes, `ff4edb0362f838765c6427c4247d9c9ceb44bea0e011210266383a56feb1c940` |
| holdout boundary | 484 bytes, `2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85` |
| listing checkpoint | 33,206,753 bytes, `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | 98,523 bytes, `8def15228d2272bc85d2466d243c55d25b953ccaa414f91bd637a1e9bf9169bb` |
| amendment ledger | absent at `data/cex002_qualify/cex002_amendment_ledger.json` |
| retained raw tree | 186 files / 1,015,198,547 bytes |
| available bytes | 170,603,364,352 |

The CLI migration preflight returned `ReviewedMigrationAuthority` with state
`not_started`, no prepared ledger, accepted report hash
`f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`, prior-lock hash
`e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`, legacy-ledger hash
`47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`, candidate plan
digest `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, and
`download_authorized=False`.

## 4. One migration-only invocation

`.env` was loaded only into the process environment. Hermes made exactly one foreground
invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-migration-only
```

Start: `2026-08-21T19:49:25-07:00`

End: `2026-08-21T19:57:40-07:00`

Elapsed seconds: 495

Exit/status: `1`

Transcript:

```text
migration_start=2026-08-21T19:49:25-07:00
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 skipped_already_bound=40771 unclaimed=0
ERROR: retryable request failed after the bounded attempt limit | context={'label': 'fapi:exchangeInfo', 'attempts': 5, 'last_error': "Transport failure for https://fapi.binance.com/fapi/v1/exchangeInfo: [Errno -3] Temporary failure in name resolution | context={'url': 'https://fapi.binance.com/fapi/v1/exchangeInfo'}"}
migration_end=2026-08-21T19:57:40-07:00
migration_elapsed_seconds=495
migration_status=1
```

Status 1 is anomalous relative to the expected successful terminal status 2. Review 151
and review 157 authorize no retry, ordinary resume, or second migration command, so Hermes
stopped after this single invocation and did not request or use network escalation for a
second run.

## 5. After-proof

After snapshot:

| Evidence | Result |
|---|---|
| report 62 | 13,946,727 bytes, `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes, `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| sample plan lock | 381,855 bytes, `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| legacy ledger | 777 bytes, `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample plan | 101,930 bytes, `02752b25d9fcfb1b9e4602bde23c8847f870578218e882213b56290b94704c12` |
| sample checkpoint/progress | 299,571 bytes, `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| retry journal | 13,737 bytes, `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| holdout boundary | 484 bytes, `2030e20aa5bd73df8fdbb7467e928508103b2e23659b85527101ec8b8546cb85` |
| listing checkpoint | 33,206,753 bytes, `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | 98,523 bytes, `8def15228d2272bc85d2466d243c55d25b953ccaa414f91bd637a1e9bf9169bb` |
| amendment ledger | absent at `data/cex002_qualify/cex002_amendment_ledger.json` |
| retained raw tree | 186 files / 1,015,198,547 bytes |
| list cache | 40,961 files |
| FAPI cache | 14 files |
| Coinalyze cache | 7 files |
| available bytes | 170,550,804,480 |

After the failed invocation, the CLI migration preflight still returned state
`not_started`, no prepared ledger, accepted candidate plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`, and
`download_authorized=False`.

The accepted report, manifest detail, installed lock, legacy ledger, sample plan, sample
checkpoint/progress, listing checkpoint, official contract metadata, and retained raw tree
remained byte-identical. The amendment ledger remained absent. The only observed
state-file mutation was the retry journal, which changed from 12,977 bytes /
`ff4edb0362f838765c6427c4247d9c9ceb44bea0e011210266383a56feb1c940` to 13,737 bytes /
`a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` while recording the
bounded failed FAPI exchange-info attempts.

No version-4 lock was installed. No amendment ledger was prepared. No sample acquisition,
ordinary resume, second migration command, Gate 2, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, or next-ticket work
occurred.

## 6. Publication

This record publishes the import-cleanup integration, successful C1-C5 restart, and the
single failed migration-only invocation. CEX-002 remains `IN_PROGRESS`; Gate 1 has not
passed; next ticket remains `NONE`.
