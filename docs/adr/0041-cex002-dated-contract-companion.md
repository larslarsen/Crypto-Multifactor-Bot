# ADR 0041 — Dated contract records alongside existing market files

Status: Accepted and implemented. Reviewed companions accepted as incomplete-history components in Reviews525 and527.
Ticket: CEX-002. Governing assignment: final section of Review525.

The immutable market publication remains unchanged. A small, separately pinned JSON
companion carries reviewed contract episodes and restrictions. It binds the market
publication, exact notice facts and explicit retrospective knowledge date. It does not
claim complete specifications or historical receipt of today's recovered notices.

CMB compiles the reviewed facts using REF-001 identity helpers and typed reference
models. No database migration or second generic reference store is needed. Asset identity
is conservatively scoped to the documented venue contract episode, with asset class
DERIVATIVE_UNDERLIER; it does not claim a fungible cross-venue token master. A canonical
instrument identifies one launch/settlement episode. Thus ticker reuse and relaunches
cannot silently join a position history. Later asset-master reconciliation remains
possible without pretending current tickers establish global asset identity.

The companion's scheduled execution end is an announced settlement start or explicit
trading cessation, not observed delisting completion. REF-001 LIST and SUSPEND records
represent the reviewed schedule, with that distinction in their evidence. Restrictions
on new positions remain separate fields; they are not full trading suspensions. Launch
terms remain labelled launch-only, with historical_terms_complete=false.

Harmonic Trader consumes the pinned JSON protocol without importing CMB source or opening
its SQLite database. Raw rows and all eleven products remain available. A history-aware
query returns original fields plus episode and boundary classification. It never books
funding payments. A history-aware native bar requires a whole interval within one known,
unrestricted episode, an explicit reviewed-notices assumption, and knowledge time no
earlier than the companion's research date. Unknown, closed or boundary-crossing bars
are rejected with a reason; their original rows remain inspectable.

This is retrospective reconstruction. It does not prove continuous tradability, complete
contract terms or causal historical source availability. Existing event-time transport
remains explicitly unqualified when no history companion is supplied. A companion cannot
mark the remaining snapshot-only names verified merely because no discrepancy was found.

No full market scan, download, catalog rewrite, model or broad suite is required. Focused
fixtures cover cancellation, relaunch, ticker reuse, restrictions, boundaries, knowledge
time and preservation of funding observations. A bounded real consumer check then proves
that the compiled records actually change native-bar selection and identity.
