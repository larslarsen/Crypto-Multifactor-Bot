# CEX-002 Fresh V2 Revision Candidate Run Record
- **Date:** 2026-09-01
- **Actor:** Jr Dev - Hermes
- **Ticket:** CEX-002
- **Review:** 389
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Preflight

- `HEAD == origin/main == be02578bbd883cca3093260dde4b18af397dab6a`
- Staging empty before launch
- Unrelated dirty paths preserved (11 modified, 13 untracked)
- No revision-candidate planner process live at preflight check
- Production SHA-256: `2f7ebacaba729c57896de7489646d517bd481347534340f3c452a7a394e76309` (5,150 lines)
- Test SHA-256: `090fa536c21213767c467533827c900d0c60c182ab1fd3f283316a033449337f` (3,140 lines)
- CLI SHA-256: `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` (87 lines)
- V2 root `data/cex002_qualify/gate2_revision_candidate_v2` absent before launch
- V1 checkpoint SHA-256: `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0`
- V1 private-index (tmp/listing.sqlite) SHA-256: `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`

## Runner

- Runner directory: `/tmp/cex002_v2_runner_eqj06p`
- Shell PID: `462949`
- Python planner PID: `463025`
- Start UTC: `2026-09-01T05:19:29Z`
- End UTC: `2026-09-01T06:01:19Z`
- Wall-clock elapsed: 41 minutes 50 seconds
- Wall-clock allowance: at least 4 hours (not exhausted)

## Command

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

## Terminal outcome

- Exit code: `2`
- Stop reason: `resumable_partial` (reported by planner stderr)
- stdout: empty
- stderr:
```text
command=plan_revision_candidate exit=2 stop=resumable_partial
ERROR: listing request failed transiently
checkpoint=/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2_revision_candidate_v2/checkpoint.json
```
- Runner status file: `SHELL_PID=462949 EXIT_CODE=2`

## Proof of single invocation

The planner was launched once under shell PID 462949. At preflight the process was absent (first Hermes harness had exited). During this inspection the process was found alive (PIDs 462949 and 463025) and was observed until it terminated with exit code 2. No replacement, duplicate, or second launch occurred. The runner directory contains exactly one set of capture files for one process.

## V2 partial result

The run exited 2 with `resumable_partial`. No v2 locator exists. The v2 checkpoint, pages, and temporary listing SQLite were created; lineage, manifest, and receipts directories remain empty.

- V2 checkpoint SHA-256: `aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748`
- V2 checkpoint size: 3,478,715 bytes
- V2 schema version: `cex002_gate2_revision_candidate_checkpoint_v2`
- V2 pending_identity_sha256: `6ac5daa6636092415ce0c01982f05acba4018f65aec85eec67a0db62fe882b61`
- V2 page file count: 1,838
- V2 page subdirectory count: 255
- V2 tmp/listing.sqlite size: 500,772,864 bytes
- V2 lineage: empty
- V2 manifest: empty
- V2 receipts: empty
- V2 locator: absent

### Per-pass progress

**pass_1:**
- pass_id: `pass_1`
- listing_complete: `False`
- completed_prefixes: 1,164
- discovered_prefixes: 1,308
- pages: 1,838
- published_pages: 1,838
- seen_tokens: 398
- cursor: `{'continuation_token': None, 'prefix': 'data/futures/um/daily/metrics/TAUSDT/'}`

**pass_2:**
- pass_id: `pass_2`
- listing_complete: `False`
- completed_prefixes: 0
- discovered_prefixes: 2
- pages: 0
- published_pages: 0
- seen_tokens: 0
- cursor: `{'continuation_token': None, 'prefix': 'data/futures/um/daily/bookTicker/'}`

## V1 unchanged

- V1 checkpoint SHA-256: `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` (unchanged)
- V1 private-index (tmp/listing.sqlite) SHA-256: `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc` (unchanged)
- V1 pass_1: completed=1,308, discovered=1,308, pages=2,093, published_pages=2,093, listing_complete=True (unchanged)
- V1 pass_2: completed=1,308, discovered=1,308, pages=2,093, published_pages=2,093, listing_complete=True (unchanged)
- No v1 delete, rename, copy, hard-link, import, relabel, cleanup, or repair occurred.

## Prohibited-action proof

- No raw ZIP GET was issued.
- No Coinalyze request was issued.
- No generation-0 edit occurred.
- No v1 reference or mutation occurred.
- No family/symbol/key/date subset selection occurred.
- No acquisition, cleanup, or transition occurred.
- No source/test patch was applied.

## Outcome statement

This run exited 2 with `resumable_partial` after a transient listing-request failure. It does not accept a v2 candidate, does not authorize raw acquisition, and does not authorize a generation transition. CEX-002 and Gate 2 remain `IN_PROGRESS`. The next ticket remains `NONE`. No retry, resume, repair, cleanup, or second invocation is authorized.

## Final actor fields

- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
