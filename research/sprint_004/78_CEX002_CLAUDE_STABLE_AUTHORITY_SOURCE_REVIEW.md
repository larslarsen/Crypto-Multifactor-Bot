# CEX-002 Claude Stable Authority Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; ACCEPT THREE CLOSURES; AUTHORIZE ONE TWO-PATH
CORRECTION**

## Reviewed state

Committed base: `HEAD == origin/main == bef62f847a7f9e0f0eb447ba7d714ae085adaf0b`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `14c434c956915e4521f695ffcc64db9bc20e77da53201d26dcc0536d48c50932` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `8cd2c89093a3e08a6f6898c9590ca1f4ab801d0ccb275c60af09a4f2a8d5f15e` |

The CLI and all seven CEX-002 fixture hashes are unchanged from review 77. Only the two
authorized paths were changed. Every DEX/BitMEX path and transient sidecar in the dirty
worktree remains unrelated and excluded.

## Accepted closures

The qualifier now decodes and relies on the retained exchangeInfo bytes, checks endpoint,
digest, byte count, retrieval time, and any supplied content path, and persists/reparses
historical responses content-addressably. Listing request identities plus raw response
digests and currently rehashed sample/checksum evidence now bind the first plan. The full
Coinalyze Binance-perpetual market map validates provider/native identity and rejects
duplicate native identities.

Those closures, the prior crash-safe reservation, storage, temporal, and complete-gap
work, and their tests must be preserved.

## Blocking findings

### 1. Volatile current-response provenance makes a normal real resume impossible

The current membership evidence contains the whole response SHA and canonical
`server_time_ms`. `membership_evidence_digest` hashes both. Binance exchangeInfo supplies
a new `serverTime` on every live fetch, which necessarily changes the raw response SHA
even when every contract row and classification is unchanged. On the first real resume,
`PlanInputs.differences` therefore reports `membership_digest` changed and raises
`plan_inputs_changed` before replaying the locked plan.

The current normal-resume test reuses an identical in-memory response, so it cannot expose
this production failure. The same volatile fields also remain in semantic report identity,
recreating the record-74 two-run comparison failure even if plan replay were allowed.

Keep each raw response SHA, byte identity, and server time in provenance and validate them
on every run. Derive the immutable plan comparison from stable canonical contract
semantics: additions/removals and material identity/class/lifecycle changes must block,
while response-wide time and raw-byte churn with identical rows must not. If a closed-
status response time supplies a lifecycle bound, persist the first authenticated closed
observation as stable evidence rather than moving the bound on each fetch. Apply the same
distinction to semantic report identity.

Add a focused two-response test whose raw SHA and `serverTime` differ but whose contract
rows are identical; it must replay one plan and retain semantic identity. Preserve a
separate changed-row/universe test that fails before sample download.

### 2. Nonempty but unknown contract values still promote to confirmed membership

`parse_exchange_info_rows` now rejects empty values, but
`is_confirmed_perpetual_row` accepts every nonempty underlying type except the one known
TradFi value. A fabricated or newly introduced `underlyingType="UNKNOWN"` therefore
qualifies as crypto. Unknown status values also pass, and duplicate native symbol rows
silently overwrite one another. Pair/base/quote/margin values are recorded but not checked
for a coherent perpetual identity.

Do not infer crypto authority from "not equal to TradFi." Accept only positively supported
official crypto semantics; unknown contract, underlying, or status enums remain typed
blocking evidence. Reject duplicate native symbols and incoherent perpetual identity
relationships. Tests must cover an unknown nonempty underlying, an unknown status, a
duplicate conflicting symbol, and an incoherent pair or quote/margin identity.

### 3. Valid positive ledger edits can still restore allowance

The ledger now rejects negative and over-budget values and a different configured budget,
but zero is accepted for both charges and reservations. Reducing a persisted reservation
to zero or a settled charge from its proved size to any smaller positive integer passes
validation and restores allowance. The `charged_bytes == sum(...)` check is tautological;
no retained total or transition evidence is checked. The claim that a charge can only grow
is therefore not established.

Reservations must retain their original positive planned size. Settlement must retain a
monotonic floor and reconcile transferred bytes to rehashed checkpoint evidence. A
legitimate zero-transfer content-address reuse needs an explicit durable no-transfer
disposition, not an indistinguishable naked zero charge. Persist and validate independent
entry counts/totals or equivalent transition evidence so partial valid-JSON edits fail
closed before download.

Add tests reducing a positive reservation to zero and a positive settled charge to a
smaller positive value. Neither may restore allowance or reach acquisition.

## Bounded correction authorization

Sr Dev - Claude Build using Claude Opus 5 may modify only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

It must preserve every accepted closure and make only the three corrections above. It
performs no test execution, network/data run, integration, fixture or repository-record
edit, Git operation, commit, push, purchase, deletion, catalog mutation, Gate 2, Nautilus,
or Harmonic Trader work. It stops for fresh reviewer source inspection with the two exact
SHA-256 hashes. Hermes and every real rerun remain unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/78_CEX002_CLAUDE_STABLE_AUTHORITY_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior record, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
