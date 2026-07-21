# FX-002 - JR EVIDENCE COMPLETION TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Repair the FX-002 evidence rejected by REVIEW-0083. Do not add production source, tests, schemas,
migrations, generated datasets, ADRs, or architecture changes.

The bounded audit may reject a candidate after one mandatory gate is conclusively disproved. Do not
invent values or pad failed candidates with unsupported conclusions.

## Candidate Proofs

### Kraken

- Preserve the exact old-`since` response proof that REST returned only the recent capped window.
- Record exact bounds for every retained Kraken capture, or remove a redundant capture that cannot be
  verified.
- Correct the timestamp description to bar interval time. Do not call it close, publication, or
  availability time without exact provider documentation.
- Historical depth is already a decisive REST failure. Mark unaudited gates `NOT_EVALUATED` or
  `UNKNOWN`, not passed or assumed.

### Coin Metrics

- Use the unauthenticated Community catalog behavior already established at
  `research/sprint_003/sources/coin_metrics.md`; do not repeat the false claim that the catalog itself
  requires authentication.
- Query the actual catalog for USDT and USDC USD price/reference-rate metrics and record the exact
  supported metric identifier, Community availability, and coverage, or exact evidence that no such
  Community metric exists.
- If a candidate metric exists, make one bounded date-window timeseries request using its exact
  identifier and no `limit`. Record the response or exact provider error.

### DefiLlama

- Start from the repository-known official public host and documentation, including
  `https://stablecoins.llama.fi/stablecoins?includePrices=true`.
- Capture an exact response and determine whether it proves historical USD-per-stablecoin prices.
  Current asset/price or supply history alone fails the historical-price gate.

### Binance

- Capture the exact official exchange-information request used to test for a direct fiat-USD pair,
  or cite an accepted immutable repository artifact with exact path, evidence ID, hash, and finding.
- Stablecoin/stablecoin and crypto cross-pairs remain secondary and cannot pass the direct-USD gate.

## Evidence Rules

- `/tmp/fx_002_raw` is approved as temporary external staging for this bounded audit. No provider raw
  payload may be committed under the repository.
- Every captured request must have an exact full URL/request, UTC retrieval timestamp, HTTP/provider
  status, byte size, SHA-256, exact external path, and exact returned time bounds when applicable.
- Use explicit `NOT_APPLICABLE`, `NOT_EVALUATED`, or `UNKNOWN` with a reason where a field does not
  exist. Do not use `xx`, `current`, `~`, ellipses, `(error)`, `(external)`, or `(to capture)`.
- A licensing claim requires an exact terms/documentation URL and retrieval status. Otherwise mark
  licensing `UNKNOWN`; this fails the gate.
- Make the report, register, source notes, and matrix agree exactly. The matrix must include rate
  direction and final accepted/deferred/rejected status as required by the original task.
- Recommend `NONE` unless one source actually passes every mandatory gate.

## Acceptance Commands

Run exactly after all record changes:

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Record the literal final result lines, including pass count, warning count, and duration. A paraphrase,
prediction, prior result, or “no failures attributable” is not evidence.

## Records And Stop Condition

- Mark FX-001 `ACCEPTED` in README/backlog consistently with REVIEW-0081.
- Mark this task and the prior correction task accurately.
- Set FX-002, README, backlog, report, and handoff to `AWAITING_REVIEW` only after every item above is
  complete.
- Name Reviewer as next actor and retain `Next ticket authorized: NONE`.
- Commit and push the corrected records, then stop. Do not begin implementation or another ticket.
