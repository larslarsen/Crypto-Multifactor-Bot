# REVIEW-0100 - REF-002 SOURCE AUDIT AUTHORIZED

**Prior ticket:** FUND-002 accepted under REVIEW-0098
**Active ticket:** REF-002 - Bybit Instrument Event Source Feasibility Audit
**Status:** AUTHORIZED - EVIDENCE ONLY
**Next required actor:** Jr Dev - Hermes
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Decision

REF-002 is the smallest independent P0 continuation. Historical listing/delisting incompleteness is an
open survivorship-bias risk, while accepted Bybit evidence already exposes `launchTime`,
`deliveryTime`, `state`, and official trade-archive edges.

The prior BTCUSDU26 record is a scheduled future-delivery exemplar as of this review date, not proof
of an already completed delivery. REF-002 must select an actually settled instrument from official
results for the historical event test.

Jr Dev - Hermes is authorized only under `docs/reviews/REF-002_JR_SOURCE_AUDIT_TASK.md`. No reference
implementation or universe work is authorized.
