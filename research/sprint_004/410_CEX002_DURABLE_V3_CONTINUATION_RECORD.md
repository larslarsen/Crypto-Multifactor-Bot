# CEX-002 Durable V3 Continuation Record 410

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** preflight exact; v3 root pre-existed as Review 409's anchored partial tree; planner launched once from resumed checkpoint; natural terminal exit 2 after transient listing failure; v3 tree partial, no locator/publication
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight proof

| Fact | Required | Observed | Match |
|------|----------|----------|-------|
| `HEAD` | `0dcaece13d4a855918d3738cdff0e5e158379c0c` | `0dcaece13d4a855918d3738cdff0e5e158379c0c` | YES |
| `origin/main` | `0dcaece13d4a855918d3738cdff0e5e158379c0c` | `0dcaece13d4a855918d3738cdff0e5e158379c0c` | YES |
| `HEAD == origin/main` | YES | YES | YES |
| Staging empty | YES | YES | YES |
| Planner process live (before launch) | NO | NO | YES |
| `scripts/research/plan_binance_usdm_gate2_revision_candidate.py` SHA-256 | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | YES |
| `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py` SHA-256 | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | YES |
| `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py` SHA-256 | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | YES |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` SHA-256 | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | YES |
| `scripts/research/acquire_binance_usdm_harmonic_release.py` SHA-256 | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` | YES |
| v1 checkpoint SHA-256 | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | YES |
| v1 private-index (listing.sqlite) SHA-256 | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | YES |
| v2 checkpoint SHA-256 | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | YES |
| v2 private-index (listing.sqlite) SHA-256 | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | YES |

All five literal path hashes match exactly. Both v1/v2 checkpoint and private-index hashes match exactly. The v3 root pre-existed before this continuation as Review 409's anchored partial tree; it was NOT absent, fresh, or created by this run.

## Pre-launch v3 state (Review 409 anchored resume state)

The v3 root `data/cex002_qualify/gate2_revision_candidate_v3` existed before launch with the exact state recorded by Review 409:

| Fact | Exact pre-launch value |
|------|------------------------|
| checkpoint SHA-256 | `54fcc69362b763bc53998adb0de944285ab3b6f799e7219d17d5f1c3c8c6dbf7` |
| checkpoint bytes | `3780433` |
| private-index SHA-256 | `3958a3df30b7eb2a71b47d5b1d2bb6d9c162302e636add78acc3bd1a9473cc28` |
| private-index bytes | `546447360` |
| candidate-lock SHA-256 / bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `0` |
| page-file count | `2001` |
| publication-file count | `0` |
| pass 1 listing complete | `false` |
| pass 1 discovered / completed | `1308` / `1257` |
| pass 1 cursor | `{"continuation_token":null,"prefix":"data/futures/um/daily/metrics/XAGUSDT/"}` |
| pass 2 listing complete / pages | `false` / `0` |
| pass 2 discovered / completed | `2` / `0` |
| pass 2 cursor | `{"continuation_token":null,"prefix":"data/futures/um/daily/bookTicker/"}` |
| generation plan identity | `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22` |
| generation state SHA-256 | `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4` |
| pending identity SHA-256 | `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61` |

The continuation authenticated and extended this pre-existing tree. It did not create a fresh v3 root.

## Runner identities

- **Runner directory:** `/home/lars/.cache/tmp/tmp.19fBZsEX5Z`
- **Runner files:**
  - `run.sh` — SHA-256 `d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820`, 2922 bytes
  - `metadata/run_identity.json` — SHA-256 `7344292d096e90117c904063f9fbbd069014699238d83768df8881761cb3b746`, 445 bytes
  - `metadata/terminal_trailer.txt` — SHA-256 `2d67a016e206e30c2878d9c64419e9267818e7dfb1c497ceeb62824930a5d21a`, 43 bytes
  - `streams/stdout.txt` — SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, 0 bytes
  - `streams/stderr.txt` — SHA-256 `b43fd2928a933e8fe5e7d61262031813999f8cd7c6d15cc633f39669a80e9f75`, 213 bytes
- **Shell PID:** 597139
- **Shell start tick:** 6647225 (field 22 of `/proc/597139/stat`)
- **Planner PID:** 597146
- **Planner start tick:** 6647228 (field 22 of `/proc/597146/stat`)
- **Start UTC:** 2026-09-01T11:03:56Z
- **End UTC:** 2026-09-01T11:52:39Z
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`

## Terminal outcome

The planner was launched exactly once. After 48 minutes 43 seconds of wall time, the planner reached natural terminal with exit status 2 due to a transient listing request failure. The runner captured the exact exit status and wrote an atomic terminal trailer. The runner was NOT killed by `process.kill` or any signal; it observed the planner's natural exit via `wait`.

- **Exit code:** 2
- **Stop reason:** transient listing request failure (`ERROR: listing request failed transiently`)
- **Wall elapsed:** 2923 seconds (48 minutes 43 seconds)
- **Wall allowance:** 14400 seconds (4 hours)
- **Terminal trailer:** `END_UTC=2026-09-01T11:52:39Z\nEXIT_STATUS=2\n`

### Complete streams

**stdout.txt** (0 bytes): empty — the planner wrote no stdout output.

**stderr.txt** (213 bytes, exact content):
```
command=plan_revision_candidate exit=2 stop=resumable_partial
ERROR: listing request failed transiently
checkpoint=/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2_revision_candidate_v3/checkpoint.json
```

## V3 evidence tree state at terminal

The v3 root `data/cex002_qualify/gate2_revision_candidate_v3` was extended from its pre-existing partial state:

- **checkpoint.json:** 7,489,213 bytes, schema `cex002_gate2_revision_candidate_checkpoint_v3`
- **candidate.lock:** 0 bytes (lock file present)
- **pages:** 3,190 page files across prefix subdirectories
- **tmp/listing.sqlite:** 1,085,112,320 bytes (private index), SHA-256 `090e55ef831b76ba768e4e3918055b10db61729d0f908bd2b303d3f7f97ef684`
- **lineage:** empty (no lineage files)
- **manifest:** empty (no manifest files)
- **receipts:** empty (no receipt files)

### Checkpoint facts

| Field | Value |
|-------|-------|
| `schema_version` | `cex002_gate2_revision_candidate_checkpoint_v3` |
| `s3_endpoint` | `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision` |
| `family_prefixes` | `["data/futures/um/daily/metrics/", "data/futures/um/daily/bookTicker/"]` |
| `generation.plan_identity` | `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22` |
| `generation.state_sha256` | `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4` |
| `pending_identity_sha256` | `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61` |

#### Pass 1

| Field | Value |
|-------|-------|
| `pass_id` | `pass_1` |
| `published_pages` | `2094` |
| `discovered_prefixes` count | `1308` |
| `completed_prefixes` count | `1308` |
| `listing_complete` | `true` |
| `cursor` | `null` |
| `roots` | `["3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d", "fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2"]` |

#### Pass 2

| Field | Value |
|-------|-------|
| `pass_id` | `pass_2` |
| `published_pages` | `1870` |
| `discovered_prefixes` count | `1308` |
| `completed_prefixes` count | `1182` |
| `listing_complete` | `false` |
| `cursor` | `{"continuation_token":null,"prefix":"data/futures/um/daily/metrics/TQQQUSDT/"}` |
| `roots` | `["3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d", "fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2"]` |

Pass 1 completed with 2,094 pages, 1,308/1,308 prefixes, `listing_complete=true`, and a null cursor. Pass 2 is partial at 1,870 pages, 1,308 discovered prefixes, 1,182 completed prefixes, `listing_complete=false`, with the actual cursor object at `data/futures/um/daily/metrics/TQQQUSDT/` and a null continuation token. The checkpoint schema has a `cursor` object but no `cursor_state` field; only `listing_complete` and the exact cursor object are reported.

### Publication state

- **Locator:** absent (no locator directory or files)
- **Receipt:** absent (receipts directory empty)
- **Manifest:** absent (manifest directory empty)
- **Lineage:** absent (lineage directory empty)

The v3 tree is a partial artifact: pass 1 is complete (2094 pages, 1308 completed prefixes, listing_complete=true, null cursor), pass 2 is incomplete (1870 pages, 1182 completed prefixes, listing_complete=false, cursor at `data/futures/um/daily/metrics/TQQQUSDT/`). No cross-pass reachability comparison was performed. No semantic identity was computed. No locator, receipt, manifest, or lineage was published.

## Exactly-once proof

- One runner directory `/home/lars/.cache/tmp/tmp.19fBZsEX5Z` was created.
- One shell process (PID 597139, start tick 6647225) launched exactly one planner child (PID 597146, start tick 6647228).
- The runner waited for that exact child via `wait "$PLANNER_PID"` and captured the natural exit status.
- The runner wrote an atomic terminal trailer via temp + mv.
- No `process.kill`, signal, or external termination was applied.
- No duplicate, replacement, rerun, or resume was launched.
- No other planner process was live before or during the invocation.
- The recorded PIDs (597139, 597146) are no longer live in `/proc`, confirming natural process exit.

## Immutable v1/v2 proof

The v1 and v2 checkpoint and private-index hashes remain exactly as required by Review 405:

- v1 checkpoint: `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`
- v1 private-index: `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`
- v2 checkpoint: `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844`
- v2 private-index: `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a`

No v1/v2 file was opened, mutated, or referenced by the v3 planner.

## Prohibited action verification

- No raw ZIP GET was issued (only ListObjectsV2 requests for listing).
- No Coinalyze request was made.
- No v1/v2 file was mutated.
- No source/test file was edited.
- No acquisition was invoked.
- No transition was attempted.
- No later gate or next ticket was started.
- No `process.kill` or signal was sent to the runner or planner.

## Runner-location defect

Review 409 required a new runner under `/tmp`. The launch instead used `/home/lars/.cache/tmp/tmp.19fBZsEX5Z`. This is a literal runner-location deviation from the authorization and is recorded as a defect. It does NOT authorize another run. The path is not normalized to `/tmp`; the actual path is recorded exactly.

## Root runner evidence preservation

Repository status confirms the untracked root file `run_continuation_runner.sh` (2922 bytes, SHA-256 `d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820`). This file is byte-identical to `/home/lars/.cache/tmp/tmp.19fBZsEX5Z/run.sh` (confirmed via `diff`). It is an unstaged runner-evidence copy. It is NOT one of the unrelated untracked paths. No new repository-root runner was created or changed during this continuation. It must remain unstaged and must not be edited, moved, deleted, or treated as one of the unrelated untracked paths.

## Dirty-path facts

The working tree contains 11 modified and 14 untracked paths unrelated to this continuation. All remain unstaged. The root runner evidence copy is separately accounted for above. No unrelated path was touched.

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. The single authorized detached continuation reached natural terminal exit 2 after a transient listing request failure. No candidate is accepted. No acquisition, transition, later gate, or next-ticket action is authorized. Every unrelated dirty path remains present and unstaged. Harness output is a handoff aid only; this record is the execution evidence and only a later reviewer record may accept or reject the candidate.
