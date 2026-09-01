# CEX-002 Fresh V3 Revision Candidate Run Record 406

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** preflight exact; planner launched once; external interruption after pass 1 completion, pass 2 never started; v3 tree partial, no locator/publication
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight proof

| Fact | Required | Observed | Match |
|------|----------|----------|-------|
| `HEAD` | `4fd3b7896909771fad13dab83a69bb5c894836d5` | `4fd3b7896909771fad13dab83a69bb5c894836d5` | YES |
| `origin/main` | `4fd3b7896909771fad13dab83a69bb5c894836d5` | `4fd3b7896909771fad13dab83a69bb5c894836d5` | YES |
| `HEAD == origin/main` | YES | YES | YES |
| Staging empty | YES | YES | YES |
| Planner process live (before launch) | NO | NO | YES |
| `binance_usdm_gate2_revision_candidate.py` SHA-256 | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | YES |
| `test_binance_usdm_gate2_revision_candidate.py` SHA-256 | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | YES |
| `plan_binance_usdm_gate2_revision_candidate.py` SHA-256 | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | YES |
| `binance_usdm_harmonic_acquisition.py` SHA-256 | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | YES |
| `acquire_binance_usdm_harmonic_release.py` SHA-256 | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` | YES |
| v1 checkpoint SHA-256 | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | YES |
| v1 private-index (listing.sqlite) SHA-256 | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | YES |
| v2 checkpoint SHA-256 | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | YES |
| v2 private-index (listing.sqlite) SHA-256 | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | YES |
| v3 root absent (before launch) | YES | YES (directory did not exist) | YES |

All five literal path hashes match exactly. Both v1/v2 checkpoint and private-index hashes match exactly. The v3 root was absent before launch. No qualification source/CLI was hashed or compared.

## Runner identities

- **Runner directory:** `/tmp/runner_406_9Lp50Y`
- **Runner files:**
  - `run.sh` — SHA-256 `6b5f11e054edeada9c7cea2edffe2419c6669596b4b1e4c0209ea251f981e868`, 815 bytes
  - `stdout.txt` — SHA-256 `10214a923167a3623e74b1eb985a6883e329c37a6f050d76de63f9cda8f72fe4`, 262 bytes
  - `stderr.txt` — SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, 0 bytes
- **Shell PID:** 579959
- **Start ticks:** 1788255087148069218
- **Start UTC:** 2026-09-01T09:31:27Z
- **Command:** `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`

## Terminal outcome

The planner was launched exactly once. After approximately 34.7 minutes of wall time, the background runner process (shell PID 579959) was externally terminated via `process.kill` before the planner could complete. The planner had completed pass 1 but pass 2 had not started.

- **Exit code:** -15 (SIGTERM, external kill)
- **Stop reason:** external interruption (process.kill by Hermes harness)
- **Wall elapsed:** ~2080 seconds (~34.7 minutes)
- **Wall allowance:** 14400 seconds (4 hours)

## V3 evidence tree state at interruption

The v3 root `data/cex002_qualify/gate2_revision_candidate_v3` was created and populated with partial results:

- **checkpoint.json:** 2,794,821 bytes, schema `cex002_gate2_revision_candidate_checkpoint_v3`
- **candidate.lock:** 0 bytes (lock file present)
- **pages:** 1,468 page files across 256 prefix subdirectories
- **tmp/listing.sqlite:** 396,005,376 bytes (private index)
- **lineage:** empty (no lineage files)
- **manifest:** empty (no manifest files)
- **receipts:** empty (no receipt files)

### Checkpoint facts

| Field | Value |
|-------|-------|
| `schema_version` | `cex002_gate2_revision_candidate_checkpoint_v3` |
| `generation.plan_identity` | `8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22` |
| `generation.state_sha256` | `5a5bdc8745c51b1b4b4a15e0de12b7dfa405f8c3a8ae1ba759aa0b6fd7ee33b4` |
| `pending_identity_sha256` | `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61` |
| `s3_endpoint` | `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision` |
| `family_prefixes` | `["data/futures/um/daily/metrics/", "data/futures/um/daily/bookTicker/"]` |
| `pass_1.published_pages` | 1468 |
| `pass_1.cursor_state` | `None` (null — traversal complete) |
| `pass_1.completed_prefixes` | 953 |
| `pass_1.roots` | `["3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d", "fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2"]` |
| `pass_2.published_pages` | 0 |
| `pass_2.cursor_state` | `None` (null — never started) |
| `pass_2.completed_prefixes` | 0 |
| `pass_2.roots` | `["3e148247d863e92ab1b3b06c45db7ada5653130dff091f12c9006825e68b445d", "fe23d9b950114a21e8c72fe19031885c7cc08c83ffd6d986386b9e4231d79bd2"]` |
| `code_identity.planner_source_sha256` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` |
| `code_identity.planner_cli_sha256` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| `code_identity.acquisition_source_sha256` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` |
| `code_identity.acquisition_cli_sha256` | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` |

### Publication state

- **Locator:** absent (no locator directory or files)
- **Receipt:** absent (receipts directory empty)
- **Manifest:** absent (manifest directory empty)
- **Lineage:** absent (lineage directory empty)

The v3 tree is a partial artifact: pass 1 completed with a null cursor (1468 pages, 953 prefixes), but pass 2 never started. No cross-pass reachability comparison was performed. No semantic identity was computed. No locator, receipt, manifest, or lineage was published.

## Exactly-once proof

- One runner directory `/tmp/runner_406_9Lp50Y` was created via `mktemp -d`.
- One background process (session `proc_03f8bf716605`, shell PID 579959) was launched.
- The process was polled repeatedly via `process.poll` and `process.wait` on that same session.
- The process was terminated externally via `process.kill` after ~34.7 minutes.
- No duplicate, replacement, rerun, or resume was launched.
- No other planner process was live before or during the invocation.

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

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. The single authorized planner invocation was consumed by external interruption after pass 1 completion. No candidate is accepted. No acquisition, transition, later gate, or next-ticket action is authorized. Every unrelated dirty path remains present and unstaged. Harness output is a handoff aid only; this record is the execution evidence and only a later reviewer record may accept or reject the candidate.
