# CEX-002 Durable V3 Continuation Record 412

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** preflight exact; v3 root pre-existed as Review 411's anchored partial tree; planner launched once from resumed checkpoint; natural terminal exit 0 after complete listing; v3 tree complete, locator/receipt/manifest/lineage published
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight proof

| Fact | Required | Observed | Match |
|------|----------|----------|-------|
| `HEAD` | `3fa12ce770e88215a0fbe3387f6aeec2b358db97` | `3fa12ce770e88215a0fbe3387f6aeec2b358db97` | YES |
| `origin/main` | `3fa12ce770e88215a0fbe3387f6aeec2b358db97` | `3fa12ce770e88215a0fbe3387f6aeec2b358db97` | YES |
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

All five literal path hashes match exactly. Both v1/v2 checkpoint and private-index hashes match exactly. The v3 root pre-existed before this continuation as Review 411's anchored partial tree; it was NOT absent, fresh, or created by this run.

## Pre-launch v3 state (Review 411 anchored resume state)

The v3 root `data/cex002_qualify/gate2_revision_candidate_v3` existed before launch with the exact state recorded by Review 411:

| Fact | Exact pre-launch value |
|------|------------------------|
| checkpoint SHA-256 | `c82186e09d560e0f209872e0c21055e137a259f46b088f3e5f2360a473ef1451` |
| checkpoint bytes | `7489213` |
| private-index SHA-256 | `090e55ef831b76ba768e4e3918055b10db61729d0f908bd2b303d3f7f97ef684` |
| private-index bytes | `1085112320` |
| candidate-lock SHA-256 / bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` / `0` |
| page-file count | `3190` |
| publication-file count | `0` |
| pass 1 listing complete / pages | `true` / `2094` |
| pass 1 discovered / completed | `1308` / `1308` |
| pass 1 cursor | `null` |
| pass 2 listing complete / pages | `false` / `1870` |
| pass 2 discovered / completed | `1308` / `1182` |
| pass 2 cursor | `{"continuation_token":null,"prefix":"data/futures/um/daily/metrics/TQQQUSDT/"}` |
| generation plan identity | `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22` |
| generation state SHA-256 | `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4` |
| pending identity SHA-256 | `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61` |

The continuation authenticated and extended this pre-existing tree. It did not create a fresh v3 root.

## Runner identities

- **Runner directory:** `/tmp/runner_411_hVWK2w`
- **Runner files:**
  - `run.sh` — SHA-256 `d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820`, 2922 bytes
  - `metadata/run_identity.json` — SHA-256 `d1836b9a24204f12df901b002cc74a889aea8c8f474d54f8567b714695135592`, 445 bytes
  - `metadata/terminal_trailer.txt` — SHA-256 `dfeeb9d23e53c7a55c9e04f4abed2e11225151f1686d3ea44d54a82312c9cfbb`, 43 bytes
  - `streams/stdout.txt` — SHA-256 `3e157735c8a5d68349def22ae784d63ddf7293668bff6687ad1116dd13027b51`, 7431 bytes
  - `streams/stderr.txt` — SHA-256 `4fe78b6b2fcfc2a4f6b9a5791c902685a39b24c3647afa00336e83555590d3f5`, 145 bytes
- **Shell PID:** 614789
- **Shell start tick:** 7040685 (field 22 of `/proc/614789/stat`)
- **Planner PID:** 614870
- **Planner start tick:** 7040697 (field 22 of `/proc/614870/stat`)
- **Start UTC:** 2026-09-01T12:09:30Z
- **End UTC:** 2026-09-01T12:15:52Z
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`

## Terminal outcome

The planner was launched exactly once. After 6 minutes 22 seconds of wall time, the planner reached natural terminal with exit status 0 after completing both listing passes and publishing a complete v3 candidate. The runner captured the exact exit status and wrote an atomic terminal trailer. The runner was NOT killed by `process.kill` or any signal; it observed the planner's natural exit via `wait`.

- **Exit code:** 0
- **Stop reason:** complete listing and publication
- **Wall elapsed:** 382 seconds (6 minutes 22 seconds)
- **Wall allowance:** 14400 seconds (4 hours)
- **Terminal trailer:** `END_UTC=2026-09-01T12:15:52Z\nEXIT_STATUS=0\n`

### Complete streams

**stdout.txt** (7431 bytes, exact content):
```json
{
  "adr": "0033",
  "authorization": {
    "acquisition_authorized": false,
    "candidate_accepted": false,
    "gate_2_accepted": false,
    "statement": "this candidate is listing-only evidence for a later reviewer decision; it accepts no revision, authorizes no acquisition, and changes no generation-0 state"
  },
  "bytes": {
    "book_ticker_current_bytes": 8661432243,
    "book_ticker_delta_bytes": 0,
    "book_ticker_old_bytes": 8661432243,
    "current_listed_bytes": 9207379061,
    "delta_bytes": 10504919,
    "equation": "current_listed_bytes - old_planned_bytes = delta_bytes",
    "metrics_current_bytes": 545946818,
    "metrics_delta_bytes": 10504919,
    "metrics_old_bytes": 535441899,
    "old_planned_bytes": 9196874142
  },
  "capacity_projection": {
    "acquisition_authorized": false,
    "available_bytes": 137966837760,
    "candidate_accepted": false,
    "measurement_only": true,
    "needed_bytes": 36800746613,
    "operating_reserve_bytes": 27593367552,
    "pending_current_listed_bytes": 9207379061,
    "remainder_bytes": 101166091147,
    "statement": "capacity projection is measurement evidence only; it accepts no candidate, authorizes no acquisition, and changes no ticket state"
  },
  "classification": {
    "book_ticker_zip_work": 354,
    "message_counts": {
      "AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling": 354,
      "AcquisitionError: listed byte size does not match": 12576,
      "AcquisitionError: stream exceeded the listed byte ceiling": 38344,
      "AcquisitionError: streamed digest does not match the required checksum": 1
    },
    "metrics_revision": 50921,
    "provider_revision_rows": 50921,
    "zip_work_rows": 354
  },
  "code_identity": {
    "acquisition_cli_sha256": "6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043",
    "acquisition_source_sha256": "af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d",
    "planner_cli_sha256": "9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a",
    "planner_source_sha256": "1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32"
  },
  "generation_0": {
    "acquisition_cli_sha256": "6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043",
    "acquisition_source_sha256": "af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d",
    "application_id": 1127368498,
    "authority_destination": "data/cex002_qualify",
    "authority_device": "dev:64513",
    "counts": {
      "attempt": 1632378,
      "charge_transition": 1707,
      "coinalyze_charge": 569,
      "completion": 685642,
      "open_coinalyze_charges": 0,
      "plan_entry": 737119,
      "run_metadata": 7,
      "run_publication": 7,
      "run_seal": 7,
      "sidecar_fact": 736347,
      "terminal_gap": 202,
      "unfinished_runs": 0
    },
    "created_at": "2026-08-28T02:52:17.350883+00:00",
    "foreign_key_violation_count": 0,
    "integrity_check": "ok",
    "physical": {
      "shm": {
        "bytes": 32768,
        "device": 64513,
        "inode": 20587464,
        "mode": 384,
        "mtime_ns": 1788210763032969440,
        "name": "state.sqlite-shm",
        "sha256": "fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb"
      },
      "state": {
        "bytes": 2386247680,
        "device": 64513,
        "inode": 20587453,
        "mode": 384,
        "mtime_ns": 1788203408070457829,
        "name": "state.sqlite",
        "sha256": "5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4"
      },
      "wal": {
        "bytes": 0,
        "device": 64513,
        "inode": 20587461,
        "mode": 384,
        "mtime_ns": 1788204076973277583,
        "name": "state.sqlite-wal",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
      }
    },
    "pins_json_sha256": "0dfe25a37e3da8517b05ac181b301e439b9494e5ef2230eafe8c21290cd6a45d",
    "plan_identity": "8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22",
    "plan_receipt_sha256": "c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167",
    "policy_identity": "adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2",
    "run7_prefix_digest": "43877e91aebdf85991f52055025ad23a68265c5dd95d1aadca8e1f1f034da8b8",
    "run7_receipt_sha256": "8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab",
    "run7_run_id": "902a6fdb3d405b8db18e05564399f38ffddd7032dfaa2df707ef2d9e8d30e15b",
    "schema_sha256": "d01df13ad3f540bc2366e88c835facb59b3ffad9a3b12f7b312be270d2051994",
    "user_version": 7,
    "watermarks": {
      "attempt_hi": 1632378,
      "charge_hi": 569,
      "completion_hi": 685642,
      "run_hi": 7,
      "seal_hi": 6,
      "sidecar_hi": 736347,
      "transition_hi": 1707
    }
  },
  "lineage": {
    "asset_bytes": 7043697,
    "asset_name": "b87a205194d7b593c44a0563b196f60b8c8bca0c5dd075414b897c51c571034e.json",
    "asset_sha256": "b87a205194d7b593c44a0563b196f60b8c8bca0c5dd075414b897c51c571034e",
    "pass_page_counts": {
      "pass_1": 2094,
      "pass_2": 2094
    },
    "schema_version": "cex002_gate2_revision_candidate_lineage_v3",
    "stable_pending_fact_count": 51275,
    "stable_pending_facts_sha256": "13cfb7440836a7a97afe069a76282c59e8ea901b863281043767086a9a006114",
    "stable_reachability_sha256": "b2170ece22b5aedf8a5181c4000ef38723e26d1874d02803319bf3e8be89485b"
  },
  "listing": {
    "current_maximum_object_bytes": 200457493,
    "family_prefixes": [
      "data/futures/um/daily/metrics/",
      "data/futures/um/daily/bookTicker/"
    ],
    "independent_passes": [
      "pass_1",
      "pass_2"
    ],
    "page_count": 4188,
    "pass_page_counts": {
      "pass_1": 2094,
      "pass_2": 2094
    },
    "stable_pending_facts_sha256": "13cfb7440836a7a97afe069a76282c59e8ea901b863281043767086a9a006114",
    "stable_reachability_sha256": "b2170ece22b5aedf8a5181c4000ef38723e26d1874d02803319bf3e8be89485b"
  },
  "manifest": {
    "compressed_bytes": 11213976,
    "compressed_sha256": "4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d",
    "format": "gzip_jsonl",
    "name": "4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz",
    "row_count": 51275,
    "semantic_rows_sha256": "5bc6bbfca7fcdcc27b8e646af8ca28b7eac3c79a26795e6cae631a5514137f28",
    "uncompressed_sha256": "a397e6343ebc3be594d01ec012fb78cd80f4603ba213ea317c7fc0f6142222be"
  },
  "pending": {
    "book_ticker_zip_work": 354,
    "identity_sha256": "6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61",
    "messages": {
      "AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling": 354,
      "AcquisitionError: listed byte size does not match": 12576,
      "AcquisitionError: stream exceeded the listed byte ceiling": 38344,
      "AcquisitionError: streamed digest does not match the required checksum": 1
    },
    "metrics_revision": 50921,
    "total": 51275
  },
  "policy_identity": "adr0033_aggregate_prefix_reachability_and_v3_candidate_v3",
  "schema_version": "cex002_gate2_revision_candidate_v3",
  "semantic_sha256": "a064fec30853eba8792052e65bbb6223224e23fc7f57879ef01291f7e825ad1b",
  "ticket": "CEX-002",
  "zip_work_policy": {
    "absolute_ceiling_bytes": 4294967296,
    "equation": "min(4 GiB, max(64 MiB, compressed_bytes * 16))",
    "floor_bytes": 67108864,
    "ratio": 16
  }
}
```

**stderr.txt** (145 bytes, exact content):
```
command=plan_revision_candidate exit=0 stop=complete
note: this candidate is evidence only; it accepts no revision and authorizes no acquisition
```

## V3 evidence tree state at terminal

The v3 root `data/cex002_qualify/gate2_revision_candidate_v3` was extended from its pre-existing partial state to a complete published candidate:

- **checkpoint.json:** 7,904,205 bytes, schema `cex002_gate2_revision_candidate_checkpoint_v3`, SHA-256 `9ce6ee6548dd550d6b118ec64f334168ea2aa9a32bf701197103fd59168f7970`
- **candidate.lock:** 0 bytes (lock file present), SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- **pages:** 3,345 page files across prefix subdirectories
- **tmp/listing.sqlite:** 1,149,280,256 bytes (private index), SHA-256 `059965cb7537f7bd56c92b83368c6e72c29801a2fdc90c51ab7b57bf55d66313`
- **locator.json:** 1,407 bytes, SHA-256 `9c0778f7b4b9fb2acea239c4432f700da7482efccb414d04a367726828913e11`
- **receipts/3e157735c8a5d68349def22ae784d63ddf7293668bff6687ad1116dd13027b51.json:** 7,431 bytes, SHA-256 `3e157735c8a5d68349def22ae784d63ddf7293668bff6687ad1116dd13027b51`
- **manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz:** 11,213,976 bytes, SHA-256 `4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d`
- **lineage/b87a205194d7b593c44a0563b196f60b8c8bca0c5dd075414b897c51c571034e.json:** 7,043,697 bytes, SHA-256 `b87a205194d7b593c44a0563b196f60b8c8bca0c5dd075414b897c51c571034e`

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
| `published_pages` | `2094` |
| `discovered_prefixes` count | `1308` |
| `completed_prefixes` count | `1308` |
| `listing_complete` | `true` |
| `cursor` | `null` |
| `roots` | `["3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d", "fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2"]` |

Both passes completed with 2,094 pages, 1,308/1,308 prefixes, `listing_complete=true`, and null cursors. The checkpoint schema has a `cursor` object but no `cursor_state` field; only `listing_complete` and the exact cursor object are reported.

### Semantic identity

| Fact | Value |
|------|-------|
| `semantic_sha256` | `a064fec30853eba8792052e65bbb6223224e23fc7f57879ef01291f7e825ad1b` |
| `stable_reachability_sha256` | `b2170ece22b5aedf8a5181c4000ef38723e26d1874d02803319bf3e8be89485b` |
| `stable_pending_facts_sha256` | `13cfb7440836a7a97afe069a76282c59e8ea901b863281043767086a9a006114` |
| `stable_pending_fact_count` | `51275` |

### Classification

| Fact | Value |
|------|-------|
| `metrics_revision` | `50921` |
| `provider_revision_rows` | `50921` |
| `zip_work_rows` | `354` |
| `book_ticker_zip_work` | `354` |

### Byte accounting

| Fact | Value |
|------|-------|
| `current_listed_bytes` | `9207379061` |
| `old_planned_bytes` | `9196874142` |
| `delta_bytes` | `10504919` |
| `metrics_current_bytes` | `545946818` |
| `metrics_old_bytes` | `535441899` |
| `metrics_delta_bytes` | `10504919` |
| `book_ticker_current_bytes` | `8661432243` |
| `book_ticker_old_bytes` | `8661432243` |
| `book_ticker_delta_bytes` | `0` |

### Capacity projection (measurement only)

| Fact | Value |
|------|-------|
| `available_bytes` | `137966837760` |
| `needed_bytes` | `36800746613` |
| `operating_reserve_bytes` | `27593367552` |
| `remainder_bytes` | `101166091147` |
| `measurement_only` | `true` |
| `acquisition_authorized` | `false` |
| `candidate_accepted` | `false` |

### Code/generation identity

| Fact | Value |
|------|-------|
| `planner_cli_sha256` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| `planner_source_sha256` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` |
| `acquisition_cli_sha256` | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` |
| `acquisition_source_sha256` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` |
| `application_id` | `1127368498` |
| `authority_destination` | `data/cex002_qualify` |
| `authority_device` | `dev:64513` |
| `user_version` | `7` |
| `integrity_check` | `ok` |
| `foreign_key_violation_count` | `0` |

### Immutable v1/v2 proof

The v1 and v2 checkpoint and private-index hashes remain exactly as required by Review 405:

- v1 checkpoint: `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`
- v1 private-index: `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`
- v2 checkpoint: `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844`
- v2 private-index: `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a`

No v1/v2 file was opened, mutated, or referenced by the v3 planner.

## Publication state

The v3 tree is a complete published candidate: both passes are complete (2094 pages each, 1308/1308 completed prefixes, listing_complete=true, null cursors). Cross-pass reachability comparison was performed. Semantic identity was computed. Locator, receipt, manifest, and lineage were published.

- **Locator:** `locator.json` (1,407 bytes, SHA-256 `9c0778f7b4b9fb2acea239c4432f700da7482efccb414d04a367726828913e11`)
- **Receipt:** `receipts/3e157735c8a5d68349def22ae784d63ddf7293668bff6687ad1116dd13027b51.json` (7,431 bytes)
- **Manifest:** `manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz` (11,213,976 bytes, 51,275 rows)
- **Lineage:** `lineage/b87a205194d7b593c44a0563b196f60b8c8bca0c5dd075414b897c51c571034e.json` (7,043,697 bytes)

## Exactly-once proof

- One runner directory `/tmp/runner_411_hVWK2w` was created.
- One shell process (PID 614789, start tick 7040685) launched exactly one planner child (PID 614870, start tick 7040697).
- The runner waited for that exact child via `wait "$PLANNER_PID"` and captured the natural exit status.
- The runner wrote an atomic terminal trailer via temp + mv.
- No `process.kill`, signal, or external termination was applied.
- No duplicate, replacement, rerun, or resume was launched.
- No other planner process was live before or during the invocation.
- The recorded PIDs (614789, 614870) are no longer live in `/proc`, confirming natural process exit.

## Prohibited action verification

- No raw ZIP GET was issued (only ListObjectsV2 requests for listing).
- No Coinalyze request was made.
- No v1/v2 file was mutated.
- No source/test file was edited.
- No acquisition was invoked.
- No transition was attempted.
- No later gate or next ticket was started.
- No `process.kill` or signal was sent to the runner or planner.

## Transient procedural violation

During successful-launch preflight, Hermes temporarily created and deleted a repository-root `_preflight_check.py` file despite the no-repository-edit instruction. The file is absent now (confirmed via `git status` and filesystem inspection). This exact transient procedural violation is recorded here. No repository file was touched at terminal; the file was deleted during preflight.

## Dirty-path facts

The working tree contains 11 modified and 14 untracked paths unrelated to this continuation. The 14 untracked paths consist of 13 unrelated untracked paths plus one separate untracked root runner-evidence copy `run_continuation_runner.sh` (2922 bytes, SHA-256 `d5c4a6b07531b52a95414b9d2a8178de11135e5f4f0b5b09e538ce20748ee820`). All remain unstaged. No unrelated path was touched.

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. The single authorized detached continuation reached natural terminal exit 0 after completing both listing passes and publishing a complete v3 candidate. The candidate remains evidence only: `candidate_accepted=false`, `gate_2_accepted=false`, `acquisition_authorized=false`. No acquisition, transition, later gate, or next-ticket action is authorized. Every unrelated dirty path remains present and unstaged. Harness output is a handoff aid only; this record is the execution evidence and only a later reviewer record may accept or reject the candidate.
