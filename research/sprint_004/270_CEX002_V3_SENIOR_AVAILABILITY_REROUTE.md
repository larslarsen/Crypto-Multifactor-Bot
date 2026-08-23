# CEX-002 V3 Senior Availability Reroute

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** availability-only actor substitution
- **Authorized actor:** Sr Dev - Sol High
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

Claude Build is unavailable until 2026-08-24 and Grok Build is temporarily unavailable.
At the owner's explicit direction, the unchanged review-269 exact test-only correction is
rerouted to Sr Dev - Sol High. Sol acts under the same bounded senior source/test scope and
prohibitions for this drop: edit only
`tests/acquisition/test_binance_usdm_harmonic_sizing.py`; run no commands; use no Git; edit
no records; perform no integration, execution, data, network, or later work; and stop once
with the test SHA-256, both frozen production/CLI hashes, and the 161-test count.

Review 269 remains the complete correction contract. This substitution changes no
requirement, equation, accepted base, architecture, source identity, execution authority,
or gate decision. Receipt 258, Hermes, validation, sizing, acquisition, normalization,
catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized.
Gate 2 remains not accepted and next ticket remains `NONE`.

The reviewer may stage, commit, and push exactly this record,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test/CLI paths
and unrelated dirty work are excluded.
