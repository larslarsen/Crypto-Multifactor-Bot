# CEX-002 Version-4 Candidate Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `300103bd03b3979b0849448c6e4ade36420d8a66`

Subject record: `research/sprint_004/144_CEX002_FOCUSED_TEST_INTEGRATION_AND_CANDIDATE.md`

## Decision

**ACCEPT THE INTEGRATION, TERMINAL VERSION-4 CANDIDATE, COMPACT REPORT, AND PRESERVED
EVIDENCE; AUTHORIZE CLAUDE BUILD ONLY FOR THE REVIEWED MIGRATION TRANSACTION SOURCE.**

Hermes's test-integration commit `56dc47128437f4db303e78629ceeccb1ca894d44`
contains exactly the accepted one-assertion correction. Publication commit
`300103bd03b3979b0849448c6e4ade36420d8a66` contains exactly the two controls, report 62,
and record 144. Both are pushed and `HEAD == origin/main`.

The five focused commands returned exit 0. Record 144 does not retain C1's actual
collected/pass count, contrary to review 143's evidence requirement; it honestly states
that only `[100%]` and exit 0 were retained. That is a documentation defect, not authority
to invent a count and not a reason to reject the exact-hash test run. The next Hermes
integration record must retain actual collected/pass counts. This review is the
authoritative forward disposition; record 144 remains preserved.

## Accepted evidence

| Evidence | Accepted identity |
|---|---|
| production source | `2f9647d8c41dd69e3fce79889d889b54beb3c8742d8d7ef24d57803cdd2443b1` |
| qualification CLI | `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc` |
| CEX test source | `186eccc22df2eb8f49f8f004141b6be7efdae15080afefa0675cfbd26e7a3fdd` |
| compact report 62 | `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`, 13,946,727 bytes |
| prior compact report | `e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`, 17,349,108 bytes |
| preserved monolith | `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`, 1,059,297,547 bytes |
| manifest detail | compressed `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945`, 11,288,256 bytes |

The terminal candidate returned status 2 with `gate_status=BLOCKED`, `accepted=false`, and
empty samples. It resolves all 46 reviewed delivery identities and 17 settlement aliases,
leaving zero unresolved archive names. Seven source products remain blocked; the candidate
is deliberately unmigrated and its qualification samples have not executed. This is not
Gate-1 acceptance, and sample execution alone is not presumed to close every typed or
blocking coverage state.

The accepted version-4 plan has digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
106 entries, zero blocked entries, 84 new objects totaling 1,049,324 bytes, 12 retained
objects totaling 44,642 bytes, and 10 aliases. Its envelope digest is
`be63989bd4d3d40c95c7ca405eae7558ce0ef997a2289892d14ed8d773d4cbfe`.
The complete Gate-2 cost manifest remains 3,144 objects / 12,522,974,218 bytes at digest
`04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57`.

## Architecture finding

The current production path cannot migrate this candidate. The public CLI exposes only
read-only `--candidate-plan-only`; ordinary execution replays the exhausted version-2
lock and legacy ledger. `SamplePlanLock.lock_plan()` would increment version 2 to version
3, which is forbidden because version 3 is a preserved, unexecuted superseded candidate.
The ordinary input identity and accounting path also do not understand the independent
ADR-0020 amendment allowance.

Migration is therefore not an operational Hermes command yet. It requires the bounded
transaction implementation fixed by the new ADR-0020 section. No live plan or ledger
mutation and no sample download is authorized by this review.

## Claude source authorization

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude implements the exact reviewed, one-shot
`--apply-reviewed-v4-migration-only` transition and its test source. The option is fixed to
the accepted report/candidate identities above; it accepts no operator-supplied plan,
digest, version, allowance, ledger, relock, or download authority. Candidate-only mode
remains read-only, and ordinary mode does not auto-migrate.

Before any mutable remote/cache facility, the migration preflight must rehash and validate
the exact accepted report, prior version-2 lock, legacy ledger, candidate plan/envelope,
complete-cost manifest identity, status/flags, and amendment-ledger absence or exact
recoverable prepared state. After current inventory and retained evidence re-prove, the
plan-content digest must remain exactly the accepted version-4 digest. Source/config
identity may advance only through an explicit migration receipt that binds the accepted
candidate envelope to the exact executing source identity; selection content may not
change.

The transaction is ledger-first and lock-last:

1. preserve the exact version-2 lock bytes content-addressably;
2. atomically create or re-prove a prepared amendment ledger bound to the accepted
   candidate, prior lock, legacy ledger, complete-cost manifest, allowance, and executing
   source identity;
3. atomically install an explicit version-4 lock as the commit point, preserving locked
   versions 0-2 and version-3 candidate lineage without relabelling version 3; and
4. stop before every sample-acquisition path with `download_authorized=false`.

A prepared-ledger/version-2-lock interruption is non-executing and recoverable only by the
same exact migration. A version-4 lock without its exact amendment ledger, or any authority
mismatch, fails closed before sample transfer. A valid version-4 ordinary resume uses only
the amendment ledger for new write-ahead reservations and settlements, keeps the legacy
ledger byte-identical, re-proves the frozen inputs and retained evidence, and replays the
accepted keys without re-selection.

## Required test source

The test drop proves at minimum:

- exact report, plan, envelope, prior-lock, legacy-ledger, complete-cost, source, and
  allowance binding, including rejection of self-consistent substitutions;
- no generic/public relock or operator-selected migration authority;
- explicit 2-to-4 transition with immutable versions 0-2 and separately preserved
  version-3 candidate lineage;
- content-addressed preservation of the exact prior lock;
- ledger-first/lock-last ordering and injected failure/recovery at every publication
  boundary;
- idempotent rerun after a prepared-ledger interruption and refusal of every inconsistent
  lock/ledger state;
- migration-only mode performs no sample fetch, reservation, settlement, checkpoint sample
  mutation, plan re-selection, or second migration;
- legacy-ledger bytes never change and amendment accounting alone enforces the 268,435,456-
  byte allowance with write-ahead interruption safety;
- a valid version-4 ordinary resume re-proves inputs and retained objects, can attempt only
  the 84 locked new-object identities when later authorized, and cannot fall back to
  version-2 accounting; and
- candidate-only and all version-2 behavior remain unchanged before migration.

Claude may add private helpers within the three paths but no new file or interface. It
runs no command, test, Ruff, repository-control, network/data operation, migration,
integration, record/ADR edit, or Git operation. It stops for reviewer source inspection
with exact SHA-256 values for all three paths and the unique `test_` function count.

Every existing accepted financial, source-authority, membership, manifest, cost, budget,
secret, retry, concurrency, report, and candidate invariant remains frozen unless the
ADR-0020 migration transaction explicitly requires the change.

## Reviewer publication

The reviewer publishes exactly:

- `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/145_CEX002_VERSION4_CANDIDATE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source/test, report, fixture, ignored evidence, lock, ledger, checkpoint, cache,
journal, database sidecar, or unrelated dirty path belongs to this publication. The
reviewer executes no pytest, Ruff, repository-control, migration, candidate, sample, or
data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
