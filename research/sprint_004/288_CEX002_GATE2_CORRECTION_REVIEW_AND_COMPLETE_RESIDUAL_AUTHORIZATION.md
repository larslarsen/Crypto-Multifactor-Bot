# CEX-002 Gate 2 Correction Review and Complete Residual Authorization

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-287 correction rejected; one complete residual correction authorized
- **Authorized actor:** Sr Dev - Grok Build, Grok 4.6 High
- **Gate 2:** in progress; raw acquisition not authorized
- **Next ticket:** `NONE`

## Inspected correction

The reviewer inspected the complete review-287 correction once at these identities:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` | `fd24bdc7e2fb2138e762cd150fd8a7f3d5eb6df4c6e963f68a03a22b24e329f1` | 121,018 |
| `scripts/research/acquire_binance_usdm_harmonic_release.py` | `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9` | 5,565 |
| `tests/acquisition/test_binance_usdm_harmonic_acquisition.py` | `4ec36eec42679cafa16854b7ff9f02fa990a2732e9aaf6461b6d2eea86270640` | 45,274 |

The test source has 32 `def test_` functions. All three files parse as Python and the
three-path scope remains exact. Unrelated dirty work was not touched. The owner relayed
completion without targeted-command output. The reviewer did not run pytest.

The correction usefully adds the pinned capacity helper identities, missing-CLI failure,
full authority rebuilding on all modes, streaming plan insertion, a pooled client,
transport retry classification, persisted Coinalyze accounting, exact Decimal parsing,
explicit returned-symbol rejection, retained adoption, no published-raw deletion, typed
unsupported completion selection, compact receipt fields, canonical JSONL-shaped output,
and a terminating fake-clock test. Preserve those correct changes.

The drop is nevertheless not executable or sufficient. The first finding below proves
that a fresh plan with the required unsupported set cannot install, independently of any
test run. The rest are production safety and terminal-evidence blockers found in the same
single static pass.

## Blocking findings

### 1. Every fresh production plan fails its first unsupported gap

At source lines 1640-1673, a plan row is appended to an in-memory batch, but an
unsupported `terminal_gap` is inserted before that batch is inserted into `plan_entry`.
The foreign key is immediate. The first of the exact 202 unsupported mappings therefore
raises `FOREIGN KEY constraint failed`; no fresh plan containing the required universe
can install. Insert each referenced plan row before its gap, or defer and reconcile the
gap inserts safely within the same all-or-nothing transaction. Test the real production
ordering boundary, including a nonempty pre-gap batch, exact 202 gaps, rollback on an
injected failure, and identical replay.

### 2. The capacity guard can cross the accepted reserve and omits Coinalyze transfers

`evaluate_capacity` at source lines 1027-1040 blocks when the stable total already
exceeds availability or when the transfer alone exceeds availability. It does not block
when `stable requirement + current reserve + next transfer > current availability`.
A transfer can therefore start with insufficient post-transfer headroom. Only Binance
raw calls the per-transfer guard; Coinalyze responses do not. A post-run blocked fact also
does not prevent a false complete result.

Use the exact prospective equation for every network body, including Binance sidecars
and raw objects and every Coinalyze attempt: the unchanged stable requirement plus reserve
plus the bounded next-transfer ceiling must fit current same-device availability before
the request. Recompute at scheduling/transfer boundaries, stop all new scheduling on the
first capacity block, settle in-flight work, and never return complete when post-capacity
is blocked. Test equality, one-byte-below, and one-byte-above boundaries for both
providers and after prior progress.

### 3. Coinalyze can publish past its budget and leak unvalidated bytes into the store

The response is published by `stream_to_content` at lines 2720-2727 before the
transactional ledger check at lines 1818-1832. An over-budget response becomes an
immutable orphan, and the worker continues scheduling later responses. Repeated failures
can consume far beyond 30,580,702 bytes. The secret scan and response parse also happen
only after publication, and `Path.read_bytes()` buffers the response. A retry is not
passed through the shared rate limiter, so the 40-call ceiling applies to logical objects
rather than actual provider calls.

Stage each response privately, hash and parse it incrementally with exact JSON numeric
lexemes, scan for the secret sentinel, and atomically prove/reserve its bytes against the
persisted remaining allocation before no-replace publication and completion. An
over-budget, secret-bearing, malformed, or wrong-identity private response must be
removed before content publication. Charge 200 and retained 404 bodies exactly once,
exclude the already-retained inventory from new-byte charge, stop scheduling on a budget
block, and fail if the one required ledger row is missing or inconsistent. Apply the
shared limiter to every actual Coinalyze attempt, including 429/5xx/transport retries.
Do not buffer the complete response or retain a manifest-sized URL/error list.

Tests must cover cumulative cross-run and concurrent exact-boundary accounting, missing
and altered ledger rows, an offending body absent from the content store, charged 404,
uncharged retained inventory, every-attempt rate limiting, exact retry counts, and secret
absence from private/published/state/receipt/error bytes.

### 4. Existing completion and state facts are neither fully monotone nor re-proved

`complete()` compares only content digest, listed bytes, and validation state at lines
1801-1815. It silently accepts changes to content path, sidecar digest/path, retrieval
time, response revision, and Coinalyze charge. The schema and exact singleton/row domains
are not authenticated on open. Missing `terminal_gap` or `coinalyze_ledger` rows are not
reconciled. On resume, installed plan rows are compared, but completed content/provider
facts are skipped without revalidation. Authority and unsafe-state exceptions raised in
a worker are caught as ordinary resumable object errors at lines 2991-2998.

Make every immutable fact insert-once/idempotent-only-when-all-fields-match. Authenticate
the exact schema, application/user versions, required indexes/constraints, singleton
authority and ledger rows, exact unsupported gap rows/facts, row domains, plan counts,
ledger equation, and semantic state before scheduling or verification. Re-prove every
completed content and sidecar path plus its provider-specific validation contract before
skipping it. An authority or unsafe-state conflict stops scheduling and propagates the
distinct fatal exit; it is never reported as a resumable network failure. One coordinator
must own database writes and terminal transitions; worker results may be concurrent.

The deterministic semantic state digest must bind the plan/receipt identities, all
completion fields, sidecar facts, exact gap facts, ledger, and durable attempt facts in
canonical order. Tests must alter each field/table independently and prove fail-closed
resume and verify behavior.

### 5. Terminal verification can accept provider-invalid or incomplete state

At lines 3079-3188 the verifier rehashes raw content but does not compare its size or
payload to the exact plan row. A Binance completion may omit its sidecar; a present
sidecar is not required to live at its content address and is not reparsed to prove the
basename/checksum equals the raw digest. Coinalyze liquidation content is not reparsed
against its exact request, status, symbol, dates, or outcome. The retained inventory is
incorrectly included in `coinalyze_bytes`, while the ledger charges only new liquidation
responses, so a valid complete run necessarily fails the ledger comparison. Conversely,
deleted unsupported gaps are not detected and can turn a typed completion into plain
complete. Retained object counts/bytes, the five retained cost keys, and the exact new
Binance equation are only reported, never required.

Create one shared provider validator used by resume and offline verify. Stream-join every
completion and exact plan row. For Binance, require plan listed size, content address and
digest, mandatory exact sidecar fact/address/hash/basename/provider checksum, safe ZIP
membership, and CRC. For Coinalyze, distinguish the one accepted retained inventory from
the 569 request rows, re-prove exact status/outcome/request identity, and incrementally
reparse retained response content. Require exactly 736,347 reconciled Binance objects,
570 Coinalyze logical completions, and 202 exact unsupported gaps; no pending/in-flight/
retryable/ambiguous row; exactly 73 retained objects / 5,225,416 bytes including five cost
keys; and exact new/unique physical-byte and ledger equations. Count sidecars and unique
content with streaming SQL aggregation, not a Python hash dictionary.

Do not write any terminal artifact for an incomplete or invalid state. After complete
reconciliation, write deterministic gzip with an empty fixed header filename and
`mtime=0`, hash while streaming, and publish no-replace with file/directory fsync. The
current randomized temporary filename can enter the gzip header, and lines 3161-3163 use
`os.replace`; both violate deterministic no-replace publication. Repeated verify must
produce the identical manifest and compact receipt with zero network.

### 6. Manifest-sized collections remain in production paths

`iter_plan_objects` retains all 733,203 main keys in a set at lines 1358-1374.
`adopt_retained` loads all 736,347 Binance identities into a list at lines 2256-2275.
`verify_state` retains every unique content digest in a dictionary at lines 3079-3093.
The run also retains every attempted URL and potentially every object error in lists.
These directly miss review 287's bounded-memory requirement.

Use the small 3,144-key cost set to reject overlap while enforcing strict main-manifest
ordering/uniqueness; do not retain the main-key set. Intersect the small authenticated
retained-object map against indexed plan lookups and apply the accepted decomposition
semantics without loading plan identities. Use cursor-batched SQL aggregation for unique
content and byte facts. Replace URL/error lists and racy shared counters with bounded
thread-safe counts, digests, and a small deterministic redacted sample. Production plan,
resume, acquire, and verify paths must have a regression that fails if a
universe-proportional Python list/set/dict or receipt field is introduced.

### 7. Retained adoption is not the accepted exact, validated, storage-neutral credit

The adoption path checks unique object count and bytes but not exact 73 valid requirement
keys or the exact five cost keys. It marks a retained raw object complete without calling
the Gate-2 ZIP/member/CRC validator. It re-streams every retained object on every run,
including completed ones, and copies retained content into the Gate-2 tree rather than
reusing the same on-device content blocks. That can consume bytes which the accepted
new-raw equation explicitly credited as already retained.

Require all three accepted decomposition quantities, exact membership, 73 keys/objects,
5,225,416 bytes, and five cost keys. Validate the raw ZIP and sidecar contract before the
first completion. Adopt the already-authenticated same-device raw and sidecar bytes by a
safe no-follow, no-replace hard link or another demonstrably storage-neutral immutable
reference; do not duplicate their data blocks. A completed retained row is first fully
re-proved and then skipped without re-copying. Test invalid ZIP/CRC, wrong cost
composition, duplicate digest/key claims, replay, and unchanged physical block usage.

### 8. No-follow and immutable publication are incomplete

Authority readers check `is_symlink()` and then reopen with `read_bytes()`/`read_text()`,
leaving a check/open race. SQLite probes with `O_NOFOLLOW`, closes the descriptor, then
reopens the pathname without no-follow at lines 1543-1553. Content checks only the leaf;
an intermediate shard or parent symlink can escape the root. Receipt writes do not loop
on short `os.write`. Response paths and sidecar parents are not all proven same-device
and no-follow.

Use descriptor-relative no-follow opens and a safely walked no-symlink parent chain for
every authority, state, lock, temporary, content, sidecar, and receipt path. Open SQLite
with an actual no-follow connection mechanism and keep the checked identity bound.
Require regular files and accepted device/root placement after open. Loop and rehash
receipt writes before publication. Apply no-replace uniformly; only private unpublished
partials may be deleted. Test leaf and intermediate symlink swaps, non-regular files,
cross-device parents, short writes, and publication races.

### 9. Retry, closure, and run evidence remain incomplete

Sidecar and Coinalyze streaming are not protected by `finally` response closure, so an
oversize/read/publish exception can retain a pooled response. Actual-attempt accounting
uses a racy shared list element; the named transport-failure test never injects a
transport failure, and no test covers Coinalyze 5xx retry or pool closure. The run receipt
can say complete even with a blocked post-capacity fact and does not bind a complete
semantic state as described above.

Close every response and the pooled transport on every success, retry, parse, capacity,
bound, signal, and exception path. Derive exact attempt/network deltas from the durable
coordinator-owned attempt facts. Validate positive finite stop bounds. Add direct
production-path tests for both providers' transport failure, 429 and 5xx sequences,
bounded exhaustion, per-attempt limiter calls, closure, fatal-state propagation, graceful
settlement, and receipt reconciliation.

## Complete residual correction authorization

Grok Build is authorized to rewrite or correct exactly these same three paths as needed:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Do not edit any existing qualification, sizing, capacity, `source_audit`, package export,
fixture, evidence, ticket, handoff, ADR, configuration, or unrelated path. Do not restore,
stash, reset, stage, or disturb existing dirty work. The current structure is not a
constraint: replace it within the three authorized paths where necessary to implement
ADR-0029 coherently instead of layering another partial fix.

Implement all nine findings and all enumerated production-path regressions in one drop.
Tests use only synthetic transports, deterministic clocks/faults, and temporary roots.
They must exercise engine/CLI paths and finish without real sleep. Real network, accepted
data mutation, real plan/state/receipt creation, economic parsing, integration, evidence,
and Git remain prohibited.

## One targeted senior test

After the complete three-path correction is written, Grok may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On nonzero result or timeout, stop without repair or rerun and report exact output and
status. Run no Ruff, control, qualification, sizing, capacity, plan, acquisition,
verification, network, or other command. Use no Git.

Stop once with all three SHA-256 hashes, test-function count, exact targeted-command
result, and confirmation that only the three authorized paths changed. Hermes
integration, acceptance commands, real planning, network acquisition, replay, evidence,
Git, commit/push, Gate-2 acceptance, Gate 3, normalization, catalog, NautilusTrader,
Harmonic Trader, PAPER/LIVE, and next-ticket work remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
The three developer source/test paths, real state/data/evidence, and unrelated dirty work
are excluded.
