# CEX-002 Gate 2 First Source Review and Consolidated Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** first Gate-2 source drop rejected; one consolidated correction authorized
- **Authorized actor:** Sr Dev - Grok Build, Grok 4.6 High
- **Gate 2:** in progress; raw acquisition not authorized
- **Next ticket:** `NONE`

## Inspected drop

The reviewer inspected the complete review-286 drop once at these identities:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` | `6bb62bb0f70bc4d2c3724c43f296022c2b13bf4c5c00358a74fba25cc0103682` | 109,326 |
| `scripts/research/acquire_binance_usdm_harmonic_release.py` | `9e52f3ba7c12ed55e769d70e1b9a0313265babcd887ae25fb4ad49505807924d` | 5,340 |
| `tests/acquisition/test_binance_usdm_harmonic_acquisition.py` | `b629bdf8f7f36d21813358095e744b2634542b54b5e9fa74093c7ffdf8045b83` | 45,698 |

The test source has 29 `def test_` functions. The three files parse as Python. The exact
scope is clean: all three are new and untracked, and no existing CEX-002 path was edited.
Unrelated dirty work remains excluded.

No reviewer test command was run. Static inspection proves that
`test_rate_limiter_enforces_forty_per_minute` cannot terminate: its injected clock stays
at zero while its sleeper only appends, so the third `acquire()` repeats the same
positive wait forever. Running the authorized full file would consume the ten-minute
timeout without adding evidence.

## Accepted correction base

The drop correctly fixes the production constants, authority locations, one-symbol
Coinalyze request shape, fixed worker/queue ceilings, secret header placement and
redaction, content sharding, same-device temporary publication, sidecar parsing, raw
checksum/size checks, ZIP CRC validation, typed unsupported mappings, explicit CLI
modes, and synthetic-only test approach. Preserve these correct portions while fixing
the complete set below. This is one correction, not a sequence of partial reviews.

## Blocking findings

### 1. Accepted retained bytes would be downloaded again

At source lines 1419 and 1488, manifest `consumable` is treated as retained credit, and
all cost rows are hard-coded non-retained at line 1434. ADR-0023 made these concepts
explicitly different. The accepted authority re-proves 73 retained requirement objects
and 5,225,416 unique bytes, including five cost keys. The implementation merely repeats
those constants in receipts; it neither derives the 73 exact keys nor verifies and
adopts their retained object and sidecar bytes. The Binance acquisition path also ignores
the plan's `retained` field. Consequently the engine schedules all 736,347 official
objects and only avoids a transfer if bytes coincidentally already exist in the new
Gate-2 store.

This violates the accepted new-raw equation and the zero-completed-object-refetch rule.
Re-use the authenticated retained-object authority and
`retained_credit_decomposition` semantics to re-prove exactly 73 objects / 5,225,416
bytes, including the five cost keys. Stream-validate and no-replace adopt their raw and
sidecar content into the Gate-2 store, record them as retained completions without a
network request, and reject any missing, changed, ambiguous, duplicate-credit, or
non-requirement claim. Manifest consumability must not grant retained credit.

### 2. Resume and verify bypass the authority and code boundary

`run_acquire` calls `run_plan` only when the state path is absent (lines 2632-2635).
`verify_state` opens mutable state directly (lines 2803-2805). Neither path rebuilds and
compares the accepted semantic plan, authority identities, plan receipt, complete code
identity, or installed plan rows on an existing state. The database stores only a small
pin subset, and `code_identity()` is unused. The fallback at lines 545-549 even reports
the qualification CLI hash as the acquisition CLI hash if the latter is missing.

In addition, live ADR-0028 capacity helpers are imported and used while
`authenticate_helpers` records but does not pin the capacity source/CLI identities
(lines 944-963). This permits changed helper semantics to govern a resumed run.

Every `plan`, `acquire`, and `verify` invocation must independently hash-authenticate all
live helper/code files, fully re-prove the unchanged accepted authority, regenerate the
same semantic plan identity, and compare the installed plan receipt and every installed
plan row before mutation or success. Missing acquisition code is fatal. Pin the accepted
capacity source/CLI identities and fail closed on any mismatch. A state created by a
different plan, code boundary, authority boundary, destination/device, or schema must be
rejected, not resumed.

### 3. The plan and verifier do not scale to the accepted universe

The planner materializes the 733,203-row manifest, then a second list and tuple of all
736,347-plus plan rows (lines 1403-1492); installation also materializes the complete SQL
parameter list. `pending()`, `completions()`, and terminal verification again load full
state into Python. Terminal verification constructs one full in-memory object containing
all rows and a second full sorted content-hash list (lines 2828-2892). The result is named
`.jsonl.gz` but is one JSON document, and the supposedly compact receipt contains every
unique content hash.

ADR-0029 requires bounded sessions without loading the manifest into memory. Make plan
derivation, installation, comparison, scheduling, completion/gap iteration, semantic
digesting, and terminal canonical JSONL publication streaming and cursor-batched. The
compact plan/run/terminal receipts contain digests, exact counts, byte totals, and
decompositions, not full object lists. Hash while streaming and publish the compressed
terminal manifest no-replace with full file and directory durability.

### 4. SQLite state is not fail-closed or monotone

`AcquisitionState.open()` writes the expected `application_id` before reading it (line
1666), thereby accepting a database with the wrong application identity. The SQLite
path itself is not opened no-follow, existing plan/state tables are not semantically
reconciled, and `PRAGMA integrity_check` cannot prove those semantics. Sidecar facts use
`INSERT OR REPLACE` (line 1779), so an accepted fact can be rewritten.

Open the fixed state path and all authority/content paths no-follow with safe parent and
same-device checks. Read and reject a nonzero wrong application ID or schema before any
write. Install identity/schema only for a genuinely new empty state. Make plan rows,
sidecar facts, typed gaps, and completions insert-once/idempotent-same; conflicting facts
must roll back and fail. Attempts remain append-only. Verify foreign keys, row domains,
exact plan content, receipt identity, counts, byte equations, and deterministic semantic
state before resuming.

### 5. Coinalyze validation and its cumulative budget are not production-correct

The byte counter is reset to zero at every `acquire` invocation (line 2644), shared
unsafely between workers (lines 2506-2525), and does not charge retained 404 bodies.
Repeated resumptions or concurrent responses can therefore exceed the accepted
30,580,702-byte new-raw allocation.

The parser uses ordinary `json.loads`; JSON decimal numbers become binary floats and are
then rejected. The real API returns JSON numeric values. Exact decimal semantics require
`parse_float=Decimal` and validation of those exact Decimal values. The parser also
substitutes the requested symbol when a response row omits `symbol`, so it does not prove
the returned identity.

Persist one transactional cumulative Coinalyze raw-byte ledger in SQLite, initialize it
from all existing adopted/completed response content, include every retained response
body including typed 404/unavailable evidence, and reserve/check/commit bytes atomically
under concurrency. Reject over-budget responses before publication/completion. Parse
numeric lexemes exactly; require the response's explicit provider symbol and exact
request-bound interval/timestamp/order/nonnegative finite values. Preserve empty and
unavailable bodies as typed retained evidence without treating them as zero.

### 6. Transport and retries do not meet the bounded operational contract

`HttpxStreamTransport.stream_get` creates and closes a new `httpx.Client` for every
request (lines 400-438), so the implementation is not pooled. Transport exceptions are
not classified or retried. The Coinalyze path retries only a first 429; first-response
5xx failures bypass the retry loop. Network-call counts record logical helper returns,
not every attempted request. Coinalyze responses are read wholly into memory.

Use one closeable pooled client for an invocation with limits consistent with the fixed
worker ceiling. Stream every sidecar and response, including Coinalyze, to bounded
same-device private files. Apply one deterministic attempt loop to both providers for
timeouts/transport failures, retryable 429/5xx statuses, bounded `Retry-After`, and
terminal statuses. Persist every actual attempt and count it once. Close all responses
and the pool on every normal, error, capacity, bound, and signal path.

### 7. A short Binance body can delete shared immutable content

After publishing a Binance blob, a short listed-size mismatch calls
`raw_path.unlink()` (line 2247). If publication reused an existing hash, this deletes a
shared content-addressed object; even for new content it violates append-only
publication. Validate the streamed byte count before publication. Never delete a
published content or sidecar path. Failed private partials may be removed; published
orphans remain safely adoptable.

### 8. Receipts, typed completion, and full verification are incomplete

Run receipts bind only the acquisition module hash (lines 2758-2777), omit byte deltas
and full authority/code identities, and undercount retries. Unsupported mapping gaps are
not included when selecting `COMPLETE_WITH_TYPED_GAPS` (lines 2742-2757). The terminal
verifier only rehashes files and compares a row count; it does not prove exact plan rows,
content-root placement, sidecar semantics, ZIP validity, Coinalyze request/response
identity, retained/new decomposition, cumulative budget, attempts, or terminal outcomes.
It uses replace publication and reports logical listed bytes as physical bytes.

Make all three mode outcomes honest and deterministic. Run receipts must include exact
attempt/completion/gap and byte deltas, pre/post capacity, the complete authority/code/
plan identities, and the semantic state digest. Any of the 202 unsupported mappings or
empty/unavailable retained responses makes the completed state
`COMPLETE_WITH_TYPED_GAPS`. The offline verifier must stream-reconcile every exact plan
identity and terminal state, revalidate each provider-specific content contract, count
unique physical content bytes once, reconcile retained/new and Coinalyze budgets, and
refuse terminal success while anything is retryable, ambiguous, in flight, over budget,
or semantically inconsistent.

### 9. The rate-limit test cannot terminate

At test lines 1235-1247, the fake sleeper records 60 seconds without advancing the fake
clock. Advance deterministic time in the sleeper or otherwise make the third acquisition
observable and terminating. The complete targeted file must finish within its existing
bound; no individual test may depend on wall-clock sleeping.

## Consolidated correction authorization

Grok Build is authorized to correct exactly the same three paths:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Do not edit any existing qualification, sizing, capacity, `source_audit`, package export,
fixture, evidence, ticket, handoff, ADR, configuration, or unrelated path. Do not restore,
stash, reset, stage, or otherwise disturb existing dirty work.

Implement all nine findings as one coherent ADR-0029 correction. Preserve exact accepted
counts, bytes, sets, hashes, destination/device, stable capacity model, command modes,
exit meanings, and no-economic-filter boundary. Add production-path synthetic regression
coverage for every correction above, including:

- exact 73-object retained adoption with the five cost keys, no network, byte
  decomposition, and fail-closed retained tampering;
- authority/code/helper/receipt/plan/state reauthentication on `plan`, existing-state
  `acquire`, and `verify`, including exact plan-row and SQLite identity corruption;
- bounded streaming plan installation/comparison/scheduling/terminal JSONL generation
  without manifest-sized lists or receipts;
- insert-once state facts, conflicting replay rejection, no-follow state/content paths,
  and published-orphan adoption without published-content deletion;
- persisted atomic cross-run Coinalyze byte accounting, concurrent boundary behavior,
  charged 404 evidence, exact numeric JSON parsing, missing/wrong symbol rejection, and
  exact daily request binding;
- one pooled transport, bounded retry of transport/429/5xx failures for both providers,
  exact attempt accounting, response/pool closure, and streaming Coinalyze publication;
- complete run/terminal reconciliation, unique physical bytes, typed unsupported gaps,
  zero-download replay, and no terminal success from altered or incomplete state; and
- deterministic rate limiting with an advancing fake clock and no real sleep.

Tests must prove production paths through the engine/CLI rather than disconnected helper
behavior. They use only synthetic transports and temporary roots. Real network, accepted
data mutation, real plan/state/receipt creation, and economic parsing remain prohibited.

## One targeted senior test

After the entire corrected three-path drop is complete, Grok may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On nonzero result or timeout, stop without repair or rerun and report the exact output and
status. Run no Ruff, control, qualification, sizing, capacity, plan, acquisition,
verification, network, or other command. Use no Git.

Stop once with the three SHA-256 hashes, test-function count, targeted command result,
and confirmation that only the three authorized paths changed. This remains source and
test-source correction only. Hermes integration, acceptance commands, real planning,
network acquisition, replay, evidence, Git, commit/push, Gate-2 acceptance, Gate 3,
normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and next-ticket work
remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
The three developer source/test paths, real state/data/evidence, and unrelated dirty work
are excluded.
