# CEX-002 Path-Bound Qualification Authorization

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `TRANSITION_ACCEPTED_ONE_ORDINARY_QUALIFICATION_AUTHORIZED`
**Architecture:** ADR-0022
**Gate 1:** Source finding remains accepted; corrected publication is pending
**Gate 2:** Not accepted

## Record-216 decision

Record 216 is accepted. Hermes executed the isolated ADR-0022 transition exactly once and
then proved its completed-state idempotence with one identical invocation. The first
receipt reported `executed=true`; the second reported `executed=false`. Both exited zero,
reported three source receipts and zero sample/network/credential work, and named the same
final authority identities.

Commit `b4edd6140ced9286ed9e19cb9bfa52d8bc791605` contains exactly record 216 and the two
control paths, is on `origin/main`, and passed repository control and the restricted
whitespace check. The full 41,369-file store manifest was identical before and after the
idempotence invocation.

The reviewer independently rehashed the final live authority and preserved evidence and
inspected their JSON bindings. The final lock is 428,097 bytes at SHA-256
`6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e`; the final
amendment ledger is 26,677 bytes at SHA-256
`2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf`. Their final
source receipt binds production SHA-256
`2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` and code/config
digest `86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb`.

This completes only the source-identity transition. ADR-0022 still requires an ordinary
qualification publication to supersede the affected report, manifest, and live checkpoint
before sizing pins may be corrected or sizing may run.

## Accepted execution pre-state

Hermes must prove these exact identities before loading `.env` or using the network:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| qualification production | - | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| qualification CLI | - | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| qualification tests | - | `e4bd0203668a4488fe56ba4efede53696d908a0a68a227d005e3420badc29dea` |
| live report 62 | 13,559,766 | `bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227` |
| live manifest detail gzip | 11,294,610 | `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4` |
| live version-4 lock | 428,097 | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| live amendment ledger | 26,677 | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| legacy ledger | 777 | `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| live sample checkpoint | 487,815 | `cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff` |
| retry journal | 13,737 | `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 51,124 | `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| listing checkpoint | 33,206,753 | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official metadata | 99,357 | `e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f` |

The manifest-detail path is
`data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz`;
its uncompressed identity is 466,713,055 bytes at SHA-256
`1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d`.
The test source contains exactly 315 `def test_` functions.

Before execution, Hermes must also prove `HEAD == origin/main` at this review's publication
commit, no qualification process is running, the lock and ledger carry the same exact
three-receipt binding, and the four transition-preserved evidence objects still rehash to
their content-addressed names:

- `data/cex002_qualify/evidence/prior_reports/sha256/bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227.json`;
- `data/cex002_qualify/evidence/checkpoints/sha256/cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff.json`;
- `data/cex002_qualify/evidence/locks/sha256/522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6.json`; and
- `data/cex002_qualify/evidence/ledgers/sha256/259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0.json`.

Any precondition mismatch stops before network or mutation. Existing exact evidence is
reused after rehashing; it is not republished or staged.

## One corrected ordinary qualification

Hermes obtains network permission before launch and consumes no preliminary restricted-
sandbox attempt. It loads `.env` only into the child process environment and runs exactly
one foreground ordinary qualification invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
qualification_status=$?
```

This invocation has no correction, migration, candidate, alternate listing checkpoint,
budget increase, or policy override. Status 0 means a terminal report claims qualified;
status 2 means a terminal report claims blocked; status 124 means timeout; any other status
is a failure. Every status ends the authorization. Do not retry, resume, run a second
qualification, or run sizing.

## Required evidence

Before the command, snapshot exact hashes, sizes, file counts, and available bytes for the
report, manifest evidence tree, lock and both ledgers, checkpoint, retry journal, plan,
listing checkpoint, official metadata, retained raw tree, list/FAPI/Coinalyze caches, and
all transition-preserved evidence. After it ends, record the exact command, timestamps,
elapsed time, status, and complete stdout/stderr transcript, then repeat the same snapshot.

For a valid terminal report, record and independently prove:

- report and manifest-detail paths, hashes, sizes, schema, compactness, Gate-1 status,
  product matrix, source blockers, release blockers, and typed gaps;
- the ADR-0022 retained decomposition: valid retained logical keys, unique physical
  digests, unique retained bytes, selected-manifest consumable keys, and complete-cost
  retained keys;
- that ambiguous basename-only Kline mappings do not authorize consumability, reuse,
  credit, or source evidence, while their prior bytes remain preserved lineage;
- exact sample planned/attempted/acquired/reused/failed counts and bytes, with no
  out-of-plan raw identity and no unapproved bulk acquisition;
- final source identity, three-receipt lock/ledger binding, accounting, reservations,
  charges, plan version/digest/history, and every live artifact identity; and
- every before/after file and byte mutation, including network-cache changes and available
  capacity, with the four transition-preserved evidence objects still byte-identical.

The architecture-correct retained expectation remains 73 valid requirement keys, 73
unique retained objects, and 5,225,416 unique retained bytes, decomposed into 56 selected-
manifest keys and 17 complete-cost keys. A different result must be reported honestly and
returns to the reviewer; Hermes does not repair it.

## Publication and stop

Publish `research/sprint_004/218_CEX002_PATH_BOUND_QUALIFICATION_EXECUTION.md` and update
the two control files for reviewer inspection. For status 0 or 2 with a valid changed
report, stage exactly the report, record 218, and the two controls. Otherwise stage exactly
record 218 and the two controls. Data/evidence, source/tests, database sidecars, and
unrelated dirty paths are never staged.

Run repository control and a whitespace check restricted to the intended publication
paths, commit, push, prove `HEAD == origin/main`, and stop. Do not run pytest, Ruff,
sizing, bulk acquisition, normalization, catalog publication, NautilusTrader, Harmonic
Trader, payoff analysis, PAPER, LIVE, a paid source, reduced scope, or next-ticket work.
Gate 2 remains unaccepted and next ticket remains `NONE`.
