# CEX-002 Sample Outcome Architecture Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `e3eadc479fe1a5ee343d1d017f757b6ff0455fdc`

Subject record: `research/sprint_004/162_CEX002_VERSION4_SAMPLE_EXECUTION.md`

Architecture decision: `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`

## Decision

**ACCEPT THE BOUNDED EXECUTION AS HONEST BLOCKING EVIDENCE; DO NOT ACCEPT GATE 1;
AMEND ADR-0020 AND ASSIGN THE SOURCE, FINANCIAL-SEMANTIC, AND AUTHORITY-TRANSACTION
CORRECTION TO SR DEV - CLAUDE BUILD.**

Hermes followed review 161 exactly. Commit
`e3eadc479fe1a5ee343d1d017f757b6ff0455fdc` contains exactly the two controls, changed
report 62, and record 162. The accepted report was preserved content-addressably before
overwrite, network permission preceded the sole invocation, status 2 ended the
authorization, and no retry or later gate ran.

The run acquired exactly the 84 locked new raw objects / 1,049,324 bytes. Eighty-two
objects settled. Two cost objects remain conservatively reserved because validation
failed after their checksum-proved raw bytes were retained. The full planned amount is
charged below the allowance; the lock, prior report, prior lock, legacy ledger, listing
checkpoint, and retry journal stayed exact. This operational outcome is accepted.

## Accepted evidence state

| Evidence | Accepted identity |
|---|---|
| production source | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| CLI source | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| 285-test source | `5d4b2e2c199b6826e9da6d6561381207644d33c119572995c7211d5cead1c6d4` |
| report 62 | 13,944,475 bytes / `53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51` |
| manifest detail compressed | 11,292,635 bytes / `64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` |
| version-4 lock | 425,308 bytes / `8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc` |
| amendment ledger | 25,223 bytes / `2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c` |
| legacy ledger | 777 bytes / `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` |
| checkpoint | 395,626 bytes / `d6c327faa144e819ca6fd4c7b0325b4a39b3ecb7cf1daa2bfdb747b2f22e85ee` |
| retry journal | 13,737 bytes / `a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24` |
| sample plan document | 51,124 bytes / `02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18` |
| official metadata | 98,940 bytes / `19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8` |
| retained raw tree | 270 files / 1,016,247,871 bytes / listing digest `0fe95c8a74d15a26f4d7b12caeae75377ec4a57ee9a32d9149258f607651da23` |
| preserved prior report | 13,946,727 bytes / `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406` |

The plan remains version 4 with digest
`2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
84 new objects, 12 retained objects, 10 aliases, and zero plan-budget blocks. The ledger
has 82 charges totaling 845,471 transferred bytes and two reservations totaling 203,853
planned bytes. No unresolved reservation may be deleted or refunded.

## Finding 1 - quote states are being misclassified as corruption

The first reserved object is the 317-byte official LTCBUSD `bookTicker` ZIP at SHA-256
`7e6e5d5ce93064d208fe0fad62353eac0bb0534cc84fba536aca795752d1135e`.
Its sole row has zero bid, ask, and quantities at a terminal 2023-08-25 timestamp. This is
an authentic empty-book observation, not malformed source bytes.

The second is the 203,536-byte official XRPUSDC `bookTicker` ZIP at SHA-256
`44f09bac4854535d9d9eb72e45fb390cc6d71b046a0a3173f0c9ed4e3269a5c2`.
It contains 12,978 rows: four initial bid-only rows, then 12,974 positive uncrossed
two-sided rows. Rejecting the entire file at row zero discards almost a full valid day.

ADR-0020 now distinguishes two-sided, bid-only, ask-only, and empty quote states. Sparse
states remain cost-unpriceable evidence and never enter spread arithmetic. Structural,
numeric, timestamp, quantity-consistency, and crossed-quote failures still fail closed.
Selection is unchanged and no outcome-driven replacement is allowed.

## Finding 2 - Gate 1 is conflated with release completeness

Six official sources are reported `official_qualified`, yet Gate 1 blocks them solely
because their universe/timeline coverage has gaps. ADR-0017 explicitly says a source gap
excludes the affected contract/interval from an intersection rather than failing the
qualified source. Gate 4 requires those gaps and the full universe to remain reported.

The membership row demonstrates the implementation error directly. Membership has no
archive data family, so generic family coverage declares all 771 confirmed perpetuals
uncovered: 698 `current_unarchived` and 73 `no_family_evidence`. In reality, current
`exchangeInfo` authenticates 698 and retained official funding evidence authenticates the
historical remainder; membership has zero unresolved classifications. Three genuinely
current names absent from archives remain data-family `current_unarchived` gaps, not
membership failures.

ADR-0020 now makes `blocked_products` the Gate-1 source-blocker list and requires a
separate later-release blocker list. Coverage gaps and `release_blocked` remain honest and
complete. Source integrity, missing required samples/checksums, unresolved membership,
inaccessible sources, incomplete inventory, or budget blocks still block Gate 1.

## Claude source and test authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Claude implements ADR-0020 section 4b literally:

1. classify every `bookTicker` row as two-sided, bid-only, ask-only, or empty; retain and
   count sparse states, exclude them from cost arithmetic, and reject negative,
   inconsistent-zero, non-finite, crossed, malformed, or nonmonotonic rows;
2. keep an all-empty file as a typed unavailable cost observation rather than a source
   integrity incident, and require at least one usable two-sided row across the locked
   sample for the `bookTicker` family to qualify;
3. preserve the six-object outcome-blind cost-source selection, the complete frozen cost
   manifest, all observed invalid/sparse evidence, and exact no-substitution behavior;
4. make membership coverage depend on the affirmative membership classification, never an
   empty family set; current-unarchived names remain gaps only for affected data products;
5. separate Gate-1 source blockers from later release blockers in the report and CLI while
   retaining every matrix row, coverage kind, symbol, interval, and release block;
6. make derived taker flow inherit the bar product's release-coverage state while retaining
   its kline-schema source evidence;
7. keep source integrity, access, listing, checksum, sample, membership, and budget failures
   blocking and keep derived products excluded from Gate 1;
8. add a mutually exclusive `--apply-reviewed-v4-source-correction-only` transaction that
   accepts no caller-selected identity and is pinned to the exact accepted state above;
9. require every current plan input except executed code/config identity to remain exact,
   preserve the version-4 plan/digest/history/selection and all ledger accounting, preserve
   prior lock and ledger bytes content-addressably, advance the ledger receipt first and
   matching lock binding/input last, and recover only its exact partial state; and
10. make the correction-only mode acquire no sample, reconcile no reservation, write no
    report, and mutate no checkpoint, raw object, list/FAPI/Coinalyze cache, legacy ledger,
    retry journal, sample-plan document, or unrelated path.

Focused tests must cover both exact retained quote shapes, all four quote states, mixed
valid/sparse files, an all-empty typed observation, every still-failing invariant, no
selection substitution, membership without family evaluation, source-versus-release gate
separation, derived-flow inheritance, and every one-shot transaction precondition,
crash/recovery, idempotence, forbidden mixed state, mutation boundary, and accounting
preservation. Existing tests that encode the superseded conflation must be corrected, not
deleted or weakened.

Claude runs no test, Ruff, repository-control, network/data command, migration, ordinary
qualification, Git operation, record/control/ADR edit, commit, or push. It returns exact
SHA-256 values for all three authorized paths and the unique CEX test-function count, then
stops for reviewer source inspection. Hermes remains unauthorized.

## Boundaries

No source integration, live source-authority transaction, ordinary resume, reservation
reconciliation, Gate-1 acceptance, sizing, Gate 2, bulk acquisition, normalization,
catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE,
paid source, reduced scope, or next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
