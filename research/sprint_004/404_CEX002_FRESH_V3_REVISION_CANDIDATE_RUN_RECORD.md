# CEX-002 Fresh V3 Revision Candidate Run Record 404

- **Date:** 2026-09-01
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** preflight mismatch — planner not launched; record 404 published documenting the stop
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight proof

| Fact | Required | Observed | Match |
|------|----------|----------|-------|
| `HEAD` | `0ff212d590ea23bd275d963da755f81d44809a6a` | `0ff212d590ea23bd275d963da755f81d44809a6a` | YES |
| `origin/main` | `0ff212d590ea23bd275d963da755f81d44809a6a` | `0ff212d590ea23bd275d963da755f81d44809a6a` | YES |
| `HEAD == origin/main` | YES | YES | YES |
| Staging empty | YES | YES | YES |
| Planner process live | NO | NO | YES |
| `binance_usdm_gate2_revision_candidate.py` SHA-256 | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` | YES |
| `test_binance_usdm_gate2_revision_candidate.py` SHA-256 | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` | YES |
| `plan_binance_usdm_gate2_revision_candidate.py` SHA-256 | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | YES |
| `binance_usdm_harmonic_qualification.py` SHA-256 | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` | **NO** |
| `qualify_binance_usdm_harmonic_sources.py` SHA-256 | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | **NO** |
| v1 checkpoint SHA-256 | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` | YES |
| v1 private-index (listing.sqlite) SHA-256 | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` | YES |
| v2 checkpoint SHA-256 | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` | YES |
| v2 private-index (listing.sqlite) SHA-256 | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a` | YES |
| v3 root absent | YES | YES (directory does not exist) | YES |

## Mismatch details

Two of the five code hashes required by Review 403 do not match the working tree:

1. **`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`**
   - Expected (Review 403): `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`
   - Actual: `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74`

2. **`scripts/research/qualify_binance_usdm_harmonic_sources.py`**
   - Expected (Review 403): `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`
   - Actual: `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f`

These files were modified by later commits in the CEX-002 authority source correction chain (`1e62cd8`, `c4a3df4`, `441a477`) that advanced HEAD after Review 403 was written.

## Execution decision

Per Review 403's explicit instruction: **"Any mismatch stops before launch and is recorded without creating v3."**

The planner was NOT invoked. No mktemp runner was created. No network request was issued. No v3 evidence tree was created. No SQLite database was opened. No candidate was produced.

## Stop

CEX-002 and Gate 2 remain `IN_PROGRESS`. Next ticket remains `NONE`. No planner invocation, network run, source/test edit, acquisition, cleanup, transition, later gate, or later-ticket action occurred. Every unrelated dirty path remains present and unstaged. Harness output is a handoff aid only; this record is the execution evidence.
