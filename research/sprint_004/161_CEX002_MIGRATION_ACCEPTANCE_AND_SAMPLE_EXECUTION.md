# CEX-002 Migration Acceptance and Sample Execution Authorization

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Subject record: `research/sprint_004/160_CEX002_MIGRATION_NETWORK_RETRY.md`

## Decision

**ACCEPT THE REVIEWED VERSION-4 MIGRATION TRANSACTION; AUTHORIZE ONE BOUNDED ORDINARY
QUALIFICATION RUN FOR THE LOCKED GATE-1 SAMPLES.**

Hermes re-proved the accepted migration preconditions, obtained network permission before
launch, and ran exactly one direct network-enabled migration-only invocation. It returned
status 2 after 555 seconds, the expected terminal status because Gate 1 remains blocked.
The transaction committed ledger-first and lock-last. No sample was acquired.

Commit `043fa9782748bd7620a57f5de6690b87b901accc` publishes exactly the two controls and
record 160. `HEAD == origin/main`, repository control passes, and the reviewer directly
re-proved the accepted source and principal migrated-state hashes. Record 160's control
sections were inserted before record 152 rather than at the chronological end; this
reviewer publication corrects that governance ordering without changing their content.

## Accepted migrated state

| Evidence | Accepted identity |
|---|---|
| production source | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| CLI source | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| 285-test source | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |
| accepted report 62 | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |
| manifest detail | 11,288,256 bytes / `8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945` |
| version-4 lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| preserved version-2 lock | 381,855 bytes / `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` |
| amendment ledger | 2,565 bytes / `96c7f9700cf89d73006f6b4234d05e1d2e25a1c766804bdb5cbd479c09d3e1c7` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| sample checkpoint | 299,571 bytes / `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan | 101,930 bytes / `02752b25d9fcfb1b9e4602bde23c8847f870578218e882213b56290b94704c12` |
| listing checkpoint | 33,206,753 bytes / `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | 98,523 bytes / `8def15228d2272bc85d2466d243c55d25b953ccaa414f91bd637a1e9bf9169bb` |
| retained raw tree | 186 files / 1,015,198,547 bytes |

The installed lock has version 4 and exact plan digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`.
It preserves plan history `[0, 1, 2]` and superseded candidate `[3]`. The amendment
ledger is empty, has a 268,435,456-byte allowance, and is bound to that plan, production
source hash, and executing code/config digest
`8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e`.
The legacy ledger remains lineage-only and unchanged.

The locked plan contains 106 entries: 84 new sample objects totaling 1,049,324 planned
bytes, 12 retained objects totaling 44,642 bytes, 10 aliases, and zero budget-blocked
entries. This is bounded source qualification sampling, not bulk historical acquisition.
The lock's required `download_authorized=false` records that the migration transition
itself authorized and performed no download. Ordinary version-4 execution is a separate
reviewer gate implemented by this review; the lock field remains byte-identical.

## Mandatory preconditions and report preservation

Jr Dev - Hermes establishes `HEAD == origin/main` at this review-publication commit,
re-proves all three source hashes and every accepted identity above, confirms no
qualification process is running, and performs the existing read-only migrated-state
preflight. It must return `version_4_lock_installed`, the exact plan digest, the exact
prepared amendment ledger with empty charges and reservations, matching lock/ledger
bindings, and `download_authorized=false`. Any mismatch stops before network execution.

Before the ordinary run can overwrite report 62, Hermes preserves its exact accepted
bytes at:

`data/cex002_qualify/evidence/prior_reports/sha256/f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406.json`

If that path exists, its hash must already equal the filename. If absent, Hermes creates
the parent directory, copies report 62 to a collision-safe temporary file without using a
hard link, rehashes the temporary copy, atomically renames it without replacing a
different destination, and re-proves the final hash. This ignored data evidence is never
staged. Any collision or hash mismatch stops.

Hermes snapshots report, manifest detail, both ledgers, lock, checkpoint, retry journal,
sample plan, listing checkpoint, official metadata, raw tree, list/FAPI/Coinalyze caches,
and available bytes before execution.

## One bounded ordinary qualification run

Hermes obtains network permission before launch and consumes no preliminary restricted-
sandbox attempt. With `.env` loaded only into the process environment, Hermes makes
exactly one foreground ordinary invocation. It uses neither migration nor candidate-plan
mode:

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

Status 0 means Gate 1 passed. Status 2 is a valid terminal report with Gate 1 still
blocked. Status 124 is an incomplete timeout. Any other status is a failure. Every status
ends the authorization: Hermes does not retry, resume, or launch a second command.

## Required after-proof

Hermes records timestamps, elapsed time, exact status, and the complete terminal
transcript, then proves and reports:

- only the 84 locked new sample identities were eligible for acquisition, with no
  out-of-plan fetch or identity substitution;
- exact attempted, acquired, retained, aliased, failed, retried, and skipped counts and
  exact planned versus transferred bytes;
- checkpoint transitions and every amendment-ledger reservation and charge, with total
  charge at or below the 268,435,456-byte allowance and no unresolved reservation;
- the unchanged legacy ledger and byte-identical version-4 lock;
- the byte-identical content-addressed prior report and the current report's validity,
  compactness, exact hash/size, Gate-1 result, product matrix, typed gaps, and manifest-
  detail identity;
- exact raw-tree, list-cache, FAPI-cache, Coinalyze-cache, checkpoint, retry-journal,
  listing-checkpoint, official-metadata, and available-byte changes;
- any deviation, interruption, unclean termination, or evidence that cannot be proved.

No focused tests or acceptance commands are rerun because the exact source identities and
their complete exit-0 sequence are already accepted. No source or test edit is authorized.

## Publication and stop

Hermes writes
`research/sprint_004/162_CEX002_VERSION4_SAMPLE_EXECUTION.md` with the complete preproof,
report preservation proof, network authorization, invocation, transcript, receipt,
after-proof, mutations, and terminal disposition.

For status 0 or 2 with a valid changed report, Hermes stages exactly the two controls,
report 62, and record 162. If report 62 is unchanged, invalid, or execution ends with
status 124 or any failure, Hermes stages exactly the two controls and record 162 and does
not stage report 62. Data, state, cache, manifest detail, evidence copies, database
sidecars, and unrelated dirty paths are never staged.

Hermes updates both controls to `Next required actor: Lead Quantitative Finance
Researcher/Engineer - inspect record 162`, commits and pushes, proves
`HEAD == origin/main`, and stops.

## Boundaries

No second invocation, automatic resume, migration, candidate-plan generation, unbounded
or full-history acquisition, Gate 2, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced scope, or
unrelated dirty-path mutation is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
