# CURRENT_TASK

Ticket: CEX-002
State: IN_PROGRESS
Final reviewer: Lead Quantitative Finance Researcher/Engineer
Next required actor: Lead Quantitative Finance Researcher/Engineer — remaining historical coverage and dated specifications
Next ticket: NONE
Next ticket authorized: NONE

## Current action

The dated companion now contains 777 episodes across 765 symbols, adding
583 symbols in Review528. 193 prior episode records remain exactly unchanged; BNX's missing final closure is corrected without changing its identity or launch terms.
All 127 SETTLING snapshot symbols and all 73 names absent from the snapshot now have
recovered launch and closing schedules. These are reviewed schedules, not complete
lifetime specifications or a claim of continuous tradability.

Current companion: data/.cex002_contract_history/review528-20261027.json
SHA256: 7db1339fa6ac9bc1d8a49e96e658f8448d9312f3732f8f529372203c4e3e40f4
Retrospective known_from: 2026-10-27T17:39:13Z. Size: 1,278,107 bytes.
The existing compiler and HT reader passed; 6 selected market files / 166,747
bytes verified actual callbacks, corrected launches, closing/order restrictions, and
unchanged funding fields without payment entitlement. No production source, market data,
broad suite or full replay changed or ran. All notice recovery jobs exited 0.

6 symbols remain without episodes: ARBUSDT, BCHUSDT, BTCUSDT, ETHUSDT, GAIBUSDT, XRPUSDT.
Evidence, exact commands, file pins and remaining work:
research/sprint_004/cex002_contract_history_expansion_528.json and
research/sprint_004/528_CEX002_REMAINING_CONTRACT_NOTICES.md.

## Continue from here

Resolve the explicitly listed remaining launch-time uncertainties and dated specifications.
Reuse cached notices under /tmp/cex002_notice_recovery and the accepted facts; do not
restart completed download batches. Launch-only terms do not establish later tick sizes,
funding intervals, quantity limits or pre-market transition timing. Historical receipt
times remain unknown; event-time playback is an explicit assumption.

The owner-authorized reviewer may finish this CEX repair directly; Hermes is optional.
Independent senior source authorship remains required if a source change is needed.
Preserve the complete eleven-product release and accepted full storage/consumer proofs.
Do not resume the stopped broad suite, repeat the full replay, rewrite market files,
start a strategy/scored study, touch unrelated DEX work or authorize another ticket.
HT-005's reader is accepted as a component; full CEX-002 acceptance is not claimed.

Governing documents:

- research/sprint_004/528_CEX002_REMAINING_CONTRACT_NOTICES.md
- research/sprint_004/527_CEX002_CONTRACT_HISTORY_EXPANSION.md
- research/sprint_004/525_CEX002_FINAL_EVIDENCE_AND_ACCEPTANCE_AUTHORIZATION.md
- docs/adr/0041-cex002-dated-contract-companion.md
- docs/adr/0040-cex002-accepted-proof-reuse.md
- research/sprint_004/474_CEX002_FIXED_CLOSEOUT_AND_PRICE_STATE_SOURCE_AUTHORIZATION.md
- tickets/CEX-002.md
