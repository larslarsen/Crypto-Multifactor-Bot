# CEX-002 Claude Complete Static Review and Consolidated Correction

Date: 2026-08-25
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED ON COMPLETE STATIC REVIEW; one consolidated correction retained by Claude
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5
Next ticket authorized: NONE

## Inspected correction snapshot

The reviewer inspected the stable post-review-290 working-tree snapshot at these exact
identities:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `6e1d867578f6c328f5453f39d58565dd5de9e33cbdbfde510cdc944a488caea5`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `7deabb36cdab9a8b7f1911c89609914b2fe6eed21e6142e3a234050f7f5fe96b`

The source, CLI, and test file contain 5,619, 151, and 2,232 lines respectively. The
test source contains 75 test functions. No reviewer test or acceptance command ran.

The current edits correctly close the exclusive state before the fresh-plan replay, use
one independently built retained-tamper fixture, and expose the unexpected worker
exception class in the wrapper message. They are retained as part of the correction base.
They do not identify or repair the underlying ordinary-acquisition exception, preserve
its cause, or release state resources on every failed open.

## Decision

Reject the drop as one unit. The reported 46 failures are one shared execution-path
failure, not 46 separate defects, but the shared failure is not the only blocker. Static
inspection finds independent defects in source authentication, progress monotonicity,
Coinalyze crash recovery, retained-credit proof, streamed retry accounting, filesystem
containment, and terminal evidence. Passing the current tests would not make the engine
safe to run against the accepted 736,347-object plus 570-receipt release.

Review 290 is superseded by this complete static decision. Do not run another test until
all findings below and their regressions are implemented together. This is the final
source-review checklist for this drop; the next reviewer decision will inspect the whole
corrected result once, not issue one review per failing assertion.

## Blocking findings

### 1. The worker boundary still masks the shared defect and streamed reads are outside retry

At source lines 5171-5178 the new wrapper appends only `type(exc).__name__`. It discards
the original cause and traceback, so it has made the broad failure more legible without
fixing it. The first ordinary synthetic acquisition exception still must be corrected at
its source.

At lines 4191-4271 an allowed HTTP status is durably recorded as a successful attempt
before the caller consumes the response body. A pooled `iter_bytes()`/read failure occurs
after retry has returned, is never retried, leaves a false `OK` attempt, and falls into the
generic worker fatal. Transport exceptions that are already `AcquisitionError` or
`FaultInjected` can increment the in-memory network count without any durable attempt.
The run receipt never requires its network count to equal the coordinator-owned attempt
delta and does not persist the bounded safe fatal diagnostic.

Make one transfer attempt encompass headers and complete streamed-body consumption. A
failed stream must close and discard its private file, record one exact redacted durable
failure, apply the reviewed retry class/backoff/limiter, and retry without publishing.
Every actual network call must have exactly one durable attempt fact. Preserve a bounded
secret-safe diagnostic class and causal identity for unexpected failures, then correct
the shared ordinary-path cause rather than accepting the wrapper as the fix.

### 2. Mutable state is not append-only or authenticated by its claimed digest

The `attempt` table at lines 2372-2381 has no plan foreign key. `record_attempt()` accepts
arbitrary provider/identity pairs, and the test at lines 2193-2230 explicitly expects 16
non-plan identities to succeed. `run_metadata` is defined but unused. Cross-table domains
do not require provider/kind/outcome combinations, exact JSON and time domains, or a
Coinalyze charge only for a liquidation plan row.

`semantic_digest()` at lines 3476-3559 merely hashes the state currently presented to
it. No prior immutable receipt lineage or watermark is authenticated on resume, so a
valid-form update or deletion simply produces a new digest. It also omits authority
`created_at`, attempt start/end times, charge `created_at`, and every `run_metadata` fact.
The authority row stores only two pin values and the existing-plan comparison does not
compare the stored pin document. The current digest test proves only that a value changes;
it never proves that resume or verification refuses the changed state.

Make attempts and all immutable state facts plan-owned and append-only. Bind every trusted
field and row, including timestamps and run facts, to a no-replace predecessor receipt or
equivalent crash-recoverable watermark so an authenticated prefix cannot be rewritten or
deleted. Reconcile any unsealed crash tail from provider/content facts before extending
the lineage. Either implement `run_metadata` completely or remove it from the accepted
schema. Resume and verify tests must mutate and delete valid-form facts and prove refusal,
not merely compare two newly computed hashes.

### 3. The Coinalyze charge transition cannot recover exact response semantics

`coinalyze_charge` stores only digest, byte count, state, and creation time. It does not
store the validated HTTP status, outcome, point count, request proof, or retrieval facts.
Consequently lines 4830-4855 recover every published charge by parsing it as a `200`
liquidation response. A crash after publishing an accepted `404` either becomes
unrecoverable or, if its body happens to parse, is falsely completed as `200`.

The state machine is also not strict. `mark_charge_published()` ignores zero-row updates;
`complete(..., settle_charge=True)` will settle a `RESERVED` row without requiring
`PUBLISHED`; `release_charge()` can refund and delete `PUBLISHED` or `SETTLED` rows; an
existing completion branch can leave a published charge unsettled; and
`coinalyze_remaining()` converts an already over-ceiling ledger into ordinary exhaustion
instead of unsafe state. Terminal verification compares charged bytes but does not require
exactly one settled charge joined to each of the 569 liquidation completions and no charge
for inventory or gaps. Zero-byte bodies make byte-only reconciliation insufficient.

Persist the complete validated recovery descriptor before publication. Enforce exact
`RESERVED -> PUBLISHED -> SETTLED` transitions with checked row counts and idempotent
same-fact replay; only an unpublished reservation may be released. Recover `200` and
`404` with their original immutable semantics, and require the exact 569 completion/charge
identity join plus the accepted cumulative byte ceiling before terminal success.

### 4. Resume and verify can manufacture retained credit and substitute inventory

The shared provider validator only checks the retained Coinalyze inventory's current
content address, size, and outcome. Its plan row contains no accepted provenance digest
or size, so another content-addressed body can replace the accepted inventory in mutable
state without being reparsed against the exact 569 mappings.

For Binance, `retained` is inferred solely from mutable
`completion.validation_state`. The validator does not require membership in the exact 73
progress keys, the retained source/revision facts, storage-neutral inode lineage, or the
five exact cost keys. Terminal verification counts whatever rows are relabeled retained;
a same-count/same-byte swap can receive the 5,225,416-byte credit. `verify_state()` does
not call the retained source re-proof used by acquisition.

Put immutable retained provenance in the plan/state facts and use it in the one shared
validator. On every resume and offline verification, reparse the retained inventory and
reconstruct the accepted mapping set; re-prove the exact 73 Binance keys, bytes, source
facts, hard-link/storage-neutral relationship, and five cost keys. Reject any additional
or missing retained label independently of aggregate counts.

### 5. State open, trusted roots, redirects, and archive parsing are not fail closed

`AcquisitionState.open()` at lines 2576-2650 leaks descriptors and an acquired writer
lock on lock contention and on most failures after connection setup. `bind_session()`
calls it outside its cleanup `try`. `close()` itself does not use nested cleanup if
connection close or unlock fails.

The no-follow helpers safely walk descendants only after accepting a root by pathname.
`open_root_dir()` creates parents with `mkdir(parents=True)` and opens only the root leaf;
authority/code reads in `load_authority_bundle()` and `code_identity()` omit the repository
or store root entirely. `RealFilesystem` also follows or trusts parent paths. Intermediate
ancestors can therefore redirect authority, state, capacity, or publication outside the
accepted roots despite the leaf checks.

`HttpxStreamTransport` enables unrestricted redirects at lines 430-437. A Coinalyze
redirect can forward the custom `api_key` header to an unapproved origin and can accept
bytes outside the frozen provider authority. Disable redirects or validate every hop
against the exact accepted scheme and host while never forwarding the secret cross-origin.

ZIP validation treats backslashes and drive-qualified names as ordinary POSIX member
characters, accepts duplicate and non-regular/symlink members, has no member-count or
uncompressed expansion ceiling, and lets several ZIP exception classes escape as generic
worker failures. Coinalyze numeric lexemes allow tiny exponent strings that can expand
into enormous `Decimal`/`format(..., "f")` allocations, and duplicate required JSON fields
are accepted.

Bind repository and store roots from safely walked descriptors, then use relative
descriptor operations for every authority, state/WAL/lock, capacity, temporary, content,
receipt, and retained path. Close every resource on every open failure. Add redirect/API
key, ancestor-symlink, lock/setup cleanup, ZIP backslash/drive/symlink/duplicate/bomb, body
read failure, numeric exponent, and duplicate-field regressions.

### 6. Terminal evidence and boundedness do not prove the complete accepted release

The terminal manifest at lines 5538-5561 omits content/sidecar paths, sidecar bytes and
provider checksum, retrieval and revision facts, charge facts, and attempt/run lineage.
Its compact receipt points only to the unanchored mutable-state digest. The reconciliation
field named `unique_content_objects` actually includes sidecars, while separate exact raw
content and sidecar object/byte equations are not published. A terminal publication error
after the private manifest is closed can also leave a private file in the terminal
directory.

`consume_manifest()` at lines 4977-4987 is production-source code that materializes the
entire accepted main universe into a tuple. The collection regression uses only 24 rows
and checks receipt list lengths, so it does not exercise production heap behavior. The
coordinator queue is declared unbounded even though synchronous callers currently bound
its usual occupancy.

Publish a canonical terminal manifest/receipt pair that independently exposes and
reconciles all immutable provider, retained/new, sidecar, charge, attempt, and physical
facts required by ADR-0029. Use accurately named separate raw-content, sidecar, and total
physical equations and require the exact manifest row equation before publication. Clean
private terminal files on every failure. Remove the universe-materializing compatibility
wrapper from production or replace it with an iterator, make every queue mechanically
bounded, and add a production-path bounded-memory proof that can detect a universe-sized
collection.

## Consolidated correction authorization

Claude Build may rewrite or correct exactly these same three paths:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Do not edit or disturb any other path. Do not restore, stash, reset, stage, commit, or
push. Preserve the accepted authority, exact counts/bytes, source scope, capacity basis,
ADR-0029 boundaries, valid existing regressions, and the three useful post-review-290
edits. A coherent replacement within the three paths is allowed; another layer of
special-case assertions is not.

Tests remain synthetic, deterministic, temporary-rooted, zero-network, and free of real
sleep. Add direct regressions for every finding above. In particular, a valid ordinary
synthetic universe must complete with the exact typed-gap exit before any downstream
fault test is considered meaningful.

## Bounded senior test-and-repair exception

The targeted senior test exception exists to reduce reviewer/developer ping-pong after
the reviewer has completed source inspection. It is not a substitute for this review.
After implementing the entire consolidated correction, Claude may run the exact command
below up to three total times in this continuation:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

After a nonzero result, Claude may diagnose and repair only failures within this exact
three-path contract, then rerun within the three-run ceiling. Stop immediately on a pass,
the third nonzero result, an architecture ambiguity, a required out-of-scope edit, real
network/data access, or any unsafe repository condition. Run no Ruff, control,
qualification, sizing, capacity, real plan/acquire/verify, network, Git, or other command.

Stop once with the final three SHA-256 hashes, test-function count, every targeted-command
result and status, the corrected underlying worker exception type/cause, and confirmation
that only the three authorized paths changed. Hermes retains integration, broader tests,
acceptance commands, evidence records, and developer-source Git. No real plan, network,
data, Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next
ticket is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, real state/data/evidence, and unrelated dirty work are
excluded.
