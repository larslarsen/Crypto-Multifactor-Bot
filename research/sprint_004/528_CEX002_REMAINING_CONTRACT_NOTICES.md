# CEX-002 — Review 528: remaining contract notices

Status: ACCEPTED COMPONENT; CEX-002 IN_PROGRESS; next ticket NONE.

The reviewer continues the owner-authorized CEX-002 repair using the existing compiler
and Harmonic Trader reader. Recover official launch, postponement and closing notices
for names still absent from Review527's dated companion. Read cached notices first;
public API recovery is sequential, saves each response, waits two seconds between
requests and stops on any error. No market-data acquisition or rewrite is assigned.

Authorized publication paths: this report,
`research/sprint_004/cex002_contract_notice_facts.json`,
`research/sprint_004/cex002_contract_history_expansion_528.json`,
`docs/handoff/CURRENT_TASK.md`, `tickets/CEX-002.md`, and the new immutable
`data/.cex002_contract_history/review528-20261027.json`.
In Harmonic Trader, update only `README.md`, `docs/handoff/CURRENT_TASK.md` and
`tickets/HT-005.md` to select the checked companion. Preserve previous companions.

Acceptance requires retained prior episode records, source-backed new boundaries,
explicit correction of postponed schedules, and closure evidence for each newly
included SETTLING contract. Check new boundaries with the existing reader and actual
Nautilus delivery using at most six selected market files / 1 MiB. Existing source
checks remain accepted; no production code changes or broad suite are assigned.

An announcement forbidding all new orders also forbids non-reduce-only orders. Store
that supported restriction kind with `restriction_scope: all_new_orders`; this does
not assert that reduce-only orders remain permitted, or that resting orders cease
matching. Preserve close-only, new-position and narrower order restrictions separately
in event details. Launch terms are not lifetime contract specifications. Publication
of a notice does not prove historical receipt. Full CEX-002 acceptance is not claimed.

Pre-market perpetual launches use the existing LIT/PUMP representation: the announced
trading start is an episode launch, with `market_regime: pre_market` in launch-only
terms. This is real futures trading, not a spot launch. Wording that orders will not
be cancelled during transition is not a cancelled listing. Missing transition dates
remain missing; no standard-market date, funding formula over the full lifetime, or
position eligibility beyond the reader's explicit schedule assumption is inferred.

The final all-SETTLING comparison caught a prior-data omission: BNX's February 2023
relaunch had no recorded end, although the snapshot marked it SETTLING. The reviewer
authorizes adding only its notice-backed March 17, 2025 08:30 cutoff and 09:00 settlement
from `2f963977c7274e0583f16f2e26987b61`. Preserve its identity, launch and launch terms.
The other 193 prior episode records remain exactly unchanged. This specifically amends
the preservation requirement above; the first failed comparison and correction are
recorded in the JSON attachment. No companion was written by that failed attempt.

## Accepted result

Review528 accepts this companion expansion and its focused consumer checks as a
component. CEX-002 remains IN_PROGRESS; next ticket NONE. No source or market files changed.

The companion contains 777 episodes across 765 symbols, adding 583
symbols. 193 prior episode records are exactly unchanged. BNX's final closure and cutoff are now recorded; all prior identities and launch terms are unchanged. All 127 SETTLING symbols
in the retained snapshot now have recovered launches and notice-backed execution ends
matching the snapshot delivery times. All 73 names absent from that snapshot retain
closed episodes. This establishes recovered schedule coverage, not continuous tradability
or complete lifetime specifications. The 80 new launch/onboard differences remain
explicit in the JSON attachment; they do not automatically imply relaunches.

Companion: data/.cex002_contract_history/review528-20261027.json
SHA256: 7db1339fa6ac9bc1d8a49e96e658f8448d9312f3732f8f529372203c4e3e40f4
Size: 1,278,107 bytes. Retrospective known_from: 2026-10-27T17:39:13Z.
Facts SHA256: eb00c02acf071f2bcb2e63ae071d26546c77a18507f4b4bae6c8d1549f8e94fc.

The sequential recovery completed successfully. First batch: 494
responses / 37,435,146 bytes. Additional category recovery:
142 / 13,736,682 bytes.
Targeted confirmations: 2 / 166,013 bytes.
Every request result is recorded in the attachment. All three processes exited 0; no
background recovery remains. No failed requests or retries occurred in these batches.
The prior Review527 rate-limit incident remains recorded there.

Corrections applied: BNT and UNFI's December 2020 proposals and INJ's January 2021
proposal were postponed; NFP moved to December 27, 2023 at 13:30 UTC; the first five
USDC contracts moved to January 4, 2024, five minutes apart starting at 12:30 UTC;
XAN moved to September 29, 2025 at 10:30 UTC. Futures settlements are kept separate
from spot swaps and bot exits. RVV/YALA's one-hour order cutoff is retained, along
with staggered closing schedules and the narrower restrictions stated by other notices.
PUMPBTC's June 13 launch follows settlement of the old PUMP contract; it does not
continue the old position. ALL and BTCDOM represent indices, not separate coins.

The existing compiler exited 0. The unchanged HT reader passed immediately before/at
all 583 added launches and all 106 new execution ends.
The real check read 6 selected market files / 166,747 bytes.
NFP, BTCUSDC and INJ's postponed proposals classify before the recovered launch. A
BTCUSDC bar reached actual native and original-field callbacks. UNFI's settlement bar
and RVV's order-restricted bar were refused. A post-settlement UNFI funding observation
reached its custom callback unchanged without a payment-entitlement claim. Full file
pins, row classifications, commands and results are in the JSON attachment. Existing
source checks remain accepted; no broad suite or full-release replay ran.

6 symbols still have no compiled episode: ARBUSDT, BCHUSDT, BTCUSDT, ETHUSDT, GAIBUSDT, XRPUSDT.
All histories and lifetime terms remain explicitly incomplete. No model, scored study
or full CEX-002 acceptance is claimed. The current handoff now contains only current
state and resumption instructions; earlier chronology remains in the ticket, reviews
and Git history.

Final publication checks passed: `python3 scripts/check_repo_control.py` and scoped
`git diff --check` in both repositories exited 0. The facts and new companion SHA256
values match the pins above; the Review527 companion retains its original SHA256.
