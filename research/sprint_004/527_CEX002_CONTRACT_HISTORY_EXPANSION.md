# CEX-002 — Expand the dated contract companion

Reviewer: Lead Quantitative Finance Researcher/Engineer.
State: ACCEPTED COMPONENT; CEX-002 remains IN_PROGRESS. This is the existing repair, not a new ticket.

## Scope

Recover additional launch/closure schedules from official Binance notices, reconcile
postponements before compiling, and extend the existing companion protocol. Preserve
the accepted 98 episodes and their identities. Current exchangeInfo dates are comparison
evidence, not a substitute for historical notices. Launch terms remain launch-only.
No source change, market rewrite, full suite or full-release replay is needed.

The owner-authorized reviewer owns research, the existing compiler invocation, focused
consumer checks and publication. Exact repository paths for this continuation are:

- research/sprint_004/cex002_contract_notice_facts.json
- research/sprint_004/cex002_contract_history_expansion.json
- research/sprint_004/527_CEX002_CONTRACT_HISTORY_EXPANSION.md
- docs/handoff/CURRENT_TASK.md
- tickets/CEX-002.md
- docs/adr/0041-cex002-dated-contract-companion.md (component-status correction only)

The generated companion is a new small file under data/.cex002_contract_history/;
the previously accepted companion remains unchanged. Harmonic Trader's README, docs/handoff/CURRENT_TASK.md and
HT-005 ticket may record the new pin and consumer result without source changes.

## Recovery observations

The retained three announcement catalogs contain 7,198 unique article codes. A first
title screen selected 925 possible futures notices. This screen is not complete:
futures closures also occur inside general token delisting/swap announcements.
Review the relevant futures paragraphs, not spot closure dates or arbitrage-bot exits.

The public detail batch recovered 136 additional responses (1,645,124 bytes), then hit
HTTP 429. The batch was interrupted; no background recovery remains. Its progress
showed 250 processed / 114 failures before interruption. An isolated diagnostic
confirmed HTTP 429. Do not treat missing responses as absent notices or restart the
four-worker batch. Existing cached responses remain reusable. Targeted official-page
research separately resolves closure and postponement exceptions for this expansion.

Acceptance requires: each added launch has explicit notice timing; all newly included
SETTLING snapshot contracts have recovered closing schedules; corrections supersede
earlier proposals; existing episode records are unchanged; the HT reader accepts the
new companion and applies the added boundaries. Full historical terms and all-universe
coverage remain incomplete. No scored study or full CEX-002 acceptance is claimed.


## Accepted result

The new companion contains 194 episodes across 182 symbols: 96 additional symbols,
including SOLUSDT, DOTUSDT, ADAUSDT, BNBUSDT and numerous later-closed contracts.
All 98 earlier episode records compare exactly equal, including their identities,
terms, sources and boundaries. All 20 newly included SETTLING snapshot contracts have
notice-backed execution ends; their snapshot delivery timestamps independently agree.
The 37 differences between accepted new launch dates and snapshot onboard timestamps
are retained in the JSON attachment. A discrepancy does not by itself prove a relaunch.

Corrections applied before compilation:

- DOT's August 20, 2020 launch proposal was postponed to August 22, 07:00 UTC.
- CHZ's December 29, 2020 proposal was postponed; the recovered launch is January 21,
  2021, 07:00 UTC. INJ's adjacent proposal was also postponed and was not admitted.
- BLZ's August 25, 2022 closure proposal was postponed indefinitely. The recovered
  final closure is December 23, 2024, 09:00 UTC.
- OMG's December 16 and December 30, 2024 closures were postponed. Its final settlement
  is January 31, 2025, 09:00 UTC. That final notice does not supply a revised new-position
  cutoff; none is invented. Classification remains a reviewed schedule assumption,
  not proof of continuous tradability or every order restriction.
- FTM and MKR futures settlements are distinct from spot-token swaps. The AMB futures
  settlement is distinct from the arbitrage bot's earlier exit.

The exact source URLs, launch response hashes and snapshot comparisons are in
cex002_contract_notice_facts.json and cex002_contract_history_expansion.json.
The original accepted companion remains unchanged.

New companion: data/.cex002_contract_history/review527-20261027.json
SHA256: 2f72426cc568d4d7a487d75537cd18cdefc1b29914f68d7aec0dad162e4530aa
Size: 348,938 bytes. Retrospective known_from: 2026-10-27T07:21:19Z.
Facts SHA256: d5bb033c36012e4ad89bb33f62388efad09912041f11707e7562725be9573c6c.
The unchanged existing compiler exited 0. Its exact invocation is in the JSON attachment.
No production or test source changed; the previously passing source tests remain valid.

The existing HT consumer loaded the new pinned companion. Checks covered immediately
before/at every one of the 96 new launches and all 20 new closing boundaries. Six selected
market files / 197,913 bytes were read; full identities/results are in the JSON attachment:

- OMG December 2024: all 744 hourly observations remain inside the recovered episode.
- OMG January 2025: 729 inside, 15 at/after final settlement; native projection rejects
  the first closed bar with `history-aware Bar refused: at_or_after_execution_end`.
- DOT August 2020: 233 bars inside the corrected episode; the superseded August 20
  launch interval classifies before launch. No fictitious pre-launch bar was created.
- SOL September 2020: 401 bars inside; one actual bar and one original-field callback
  reached Nautilus, with original fields unchanged.
- SKL December 2020: 569 bars inside its December 8 launch, not the snapshot's August 24.
- OMG January funding: 92 points inside and one after settlement. The latter reached
  its custom callback unchanged, without establishing payment entitlement.

## Remaining work and resumption

589 of the 771 release symbols still have no compiled episode. The full pending symbol
list is stored once in the JSON attachment. Ten symbols have recovered events but no
launch. All histories and lifetime contract specifications remain explicitly incomplete.
Do not report 182 complete histories or full CEX-002 acceptance.

Reuse cached notices. Expand recovery to general delisting/token-swap notices as well
as futures-titled articles. Resume public detail retrieval only after rate limiting has
cleared, with a lower request rate, incremental durable results and immediate stop on
429; do not rerun the stopped four-worker script. Resolve BNT/UNFI/INJ postponed chains
and BTC beta/public-launch versus ETH/BCH/XRP already-launched notices without assigning
invented effective times. No market download, full scan, broad suite or model is needed.

Repository control passed. The old/new companion and facts digests were rechecked.
Scoped whitespace checks passed; unrelated CMB and HT working-tree changes are excluded.
