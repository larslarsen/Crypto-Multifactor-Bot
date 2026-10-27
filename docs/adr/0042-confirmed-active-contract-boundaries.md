# ADR 0042 — Confirmed-active dates without invented launch times

Status: Accepted and implemented in CEX-002 Review529.

A recovered first-ever launch timestamp is not necessary to identify later observations
of a contract whose existence is documented. BTC's public launch follows beta trading;
ETH/BCH/XRP launch notices say trading has started without an exact start; ARB's notice
is approximate. Treating all later rows as unknown discards supported history.

Extend the existing companion, not the market files or catalog. A `confirmed_active`
fact records a conservative coverage start supported by a notice or a pinned, nonempty
exchange trading observation. It does not assert an exact launch. New episodes have
`launch_ms: null`, `coverage_start_ms`, and `start_kind: confirmed_active`. Earlier rows
are `before_confirmed_active`, never asserted to predate launch. Whole intervals at or
after this boundary can use the existing reviewed-notices playback assumption; pinned
market evidence corroborates the contract named in the notice. Evidence states its basis.
This assumes continuity after confirmation subject to recovered closures/restrictions,
as existing notice-based episodes do; it is not a proof of uninterrupted tradability.

Mixed companions use schema 2. The reader continues to accept schema 1. Existing exact
launch episodes and their identities remain byte-for-byte unchanged within schema 2.
New identity keys use the confirmation time and source with a distinct kind; no LIST
event or launch-only specifications are invented. Typed alias/version validity begins
at confirmation, with an explicit evidence-only specification. A later exact-launch
recovery requires explicit identity reconciliation, not automatic position carryover.

Unresolved-contract facts can retain the GAIB postponement and its evidence without
inventing an episode. All incomplete-history, retrospective knowledge and payment
eligibility limits remain. No inference of lifetime tick sizes, leverage, quantity limits
or historical receipt time follows from a confirmed-active boundary.
