# CEX-002 Claude Transition Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; ACCEPT REVIEW-78 CLOSURES; ROUTE ONE TWO-PATH
CORRECTION TO GROK**

## Reviewed state

Committed base: `HEAD == origin/main == 01d587d3f6a11a27bc4437ed944bcf9d2c35316a`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `8107235f99b6ff18c69789963800545dd49a1a0b7aab889787a62ef61349c390` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c630d9b6dfafd409c9322cc0f324864c9f864e93aef2a29f3d068a515ea0808f` |

The CLI and all CEX-002 fixtures are unchanged from review 78. Only the two authorized
paths changed. Every DEX/BitMEX path and transient sidecar in the dirty worktree remains
unrelated and excluded. The reviewer performed static source inspection only and did not
execute tests, acceptance commands, or data mutation.

## Accepted closures

The correction separates volatile current-response provenance from stable contract
semantics, retains the first authenticated closed observation, and adds a two-response
identity/resume test. Unknown underlying and status enums, duplicate native symbols, and
incoherent pair/base/quote/margin relationships now fail closed. The ledger now uses
positive write-ahead reservations, explicit transferred/no-transfer dispositions,
rehashed retained-object reconciliation, and independent persisted counts, totals, and a
state digest; the requested reduced-positive and naked-zero edit cases are represented in
test source.

Those closures and every closure accepted in reviews 65 through 78 must be preserved.

## Blocking findings

### 1. Rejected live authority can durably poison every later resume

`run_source_qualification` calls `metadata_store.observe(...)` and
`metadata_store.flush(...)` before loading and comparing the immutable plan lock. A
material current-row change is therefore committed to the official metadata store before
`PlanInputs.differences` rejects it. In particular, a transient `SETTLING` response adds a
first `closed_observation`; the changed run then fails, but that observation is attached to
a later normal `TRADING` response and changes the stable membership digest again. The
previously valid store can no longer resume even after the external authority returns to
its original state.

Stage the current response and any candidate first-closed observation without changing
the durable metadata index or snapshot set. Use that staged semantic view for
classification and plan-input comparison. Commit the raw snapshot, symbol binding,
closed observation, and metadata checkpoint only after the existing plan accepts the
inputs, or as part of successful first-plan establishment. A rejected authority change
must leave the metadata checkpoint and content-addressed snapshot set byte-for-byte
unchanged and a subsequent original response must resume the original plan and semantic
identity.

Add a focused three-response test: establish the plan with `TRADING`, present a materially
changed closed-status response and assert rejection before sample acquisition, then
present the original `TRADING` semantics with fresh volatile provenance and assert the
original plan and semantic identity resume. Also assert the rejected middle response did
not alter either durable metadata artifact.

### 2. The in-memory acquisition path records a transfer as no-transfer

When `transport is None`, `_acquire_sample` calls `index.fetch_bytes(url)` before checking
whether the provider checksum's content-addressed destination already exists. It then sets
`reused_existing=True` solely because that destination exists. The caller settles the
write-ahead reservation with the zero-byte no-transfer disposition even though the raw
payload was fetched during this acquisition. Because the focused ledger tests use this
path and deliberately share payload digests, they can restore allowance without proving
the transition they claim.

Once the retained checksum sidecar proves the expected digest, check and rehash the
content-addressed destination before fetching the raw object. If it is valid, reuse it
without calling the raw fetch and record no-transfer. Otherwise fetch the raw object and
record the transferred size even if its digest happens to match content retained by an
earlier acquisition. Add focused fetch-log and ledger assertions covering both paths.

## Bounded correction authorization

At the owner's direction, the correction is routed to Sr Dev - Grok Build using Grok 4.6
High because Claude is unavailable. Grok may modify only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

It must preserve all accepted work and make only the two corrections above. Grok authors
source and test source only. It performs no test execution, network/data run, integration,
fixture or repository-record edit, Git operation, commit, push, purchase, deletion,
catalog mutation, Gate 2, Nautilus, or Harmonic Trader work. It stops for fresh reviewer
source inspection with the two exact SHA-256 hashes. Hermes and every real rerun remain
unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/79_CEX002_CLAUDE_TRANSITION_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
