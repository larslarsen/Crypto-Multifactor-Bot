# CEX-002 V3 Capacity Test Ordering Failure

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 272 accepted as faithful execution; one test ordering correction required
- **Authorized actor:** Sr Dev - Sol High
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Review outcome

The reviewer accepts record 272 and commit `f81ebf9` as faithful review-271 integration
and execution. Hermes proved the accepted hashes and 161-test count, staged only the test
source, ran the focused command once, and stopped immediately after its single failure.
Hermes correctly ran no Ruff, sizing invocation, idempotence invocation, network, data, or
later work and produced no receipt 258 or v3 evidence.

The sole failure is deterministic test-source statement ordering in
`test_the_v3_capacity_terms_reconcile_exactly`. The test reads
`liquidation["identity_domain"]` before the existing assignment
`liquidation = receipt["coinalyze"]["allocation"]` later in the same function. The
allocation and all assertions are already present; production did not run and no
production or architecture issue is indicated.

## Exact Sol High correction

Edit only `tests/acquisition/test_binance_usdm_harmonic_sizing.py` at integrated SHA-256
`f67851a952bc5fdacf5a951344f119e0efd721d47974af0f6f1424449299777c`:

1. Move the existing assignment
   `liquidation = receipt["coinalyze"]["allocation"]` to immediately before
   `domain = liquidation["identity_domain"]`.
2. Remove its later duplicate immediately below the comment `Coinalyze no longer
   multiplies a complete measured payload by every point.`

Change no assertion, comment, equation, fixture, or other byte. Preserve exactly 161 test
functions. Keep production SHA-256
`d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` and CLI
SHA-256 `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`
byte-identical. Run no command; use no Git; edit no records; perform no integration,
execution, data, network, or later work. Stop once and report the test hash, both frozen
hashes, and test count.

## Boundaries

Hermes reintegration, validation, Ruff, sizing, receipt 258, acquisition, normalization,
catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized
pending reviewer static acceptance. Gate 2 remains not accepted and next ticket remains
`NONE`.

The reviewer may stage, commit, and push exactly this record,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths and
unrelated dirty work are excluded.
