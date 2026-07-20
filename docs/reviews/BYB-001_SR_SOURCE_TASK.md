# BYB-001 - Sr Dev Production Source Task

**Ticket:** `tickets/BYB-001.md`
**Actor:** Sr Dev - Grok Build
**Status:** AUTHORIZED - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Implement the complete BYB-001 production module at:

```text
src/cryptofactors/ingest/bybit.py
```

Read the full ticket, accepted Sprint 003 Bybit evidence, `ingest/binance.py`, MAN-001
publisher models, ADR-0004, and layer boundaries before editing.

## Required implementation

- Public constants, result type, and `normalize_bybit_trades` API exactly as constrained by
  the ticket.
- Local registered `.csv.gz` inputs only; strict audited ten-column schema.
- Streaming bounded gzip/CSV handling.
- Decimal-only exact fractional-second conversion to UTC microseconds.
- Explicit linear/base versus inverse/contracts semantics with no invented inverse volume.
- Typed quality issues, within/cross-object trade-ID duplicate detection, raw row lineage,
  and acceptance-quality propagation.
- Deterministic per-object trade/quality Parquet outputs and complete MAN-001 `PublishPlan`.
- No network, filename identity, pandas, secrets, global mutable state, or higher-layer import.

## Constraints

- Edit production source only. Do not create or edit tests, tickets, reviews, handoffs,
  changelogs, schemas, architecture, or research files.
- Do not modify BIN-001 or BAR-001 behavior.
- Do not add backward-compatibility aliases or broaden scope into REST/funding/bars.
- Do not run acceptance gates or claim ticket completion.
- Do not use Git, commit, or push.

## Stop condition

Return the source drop for reviewer inspection and stop. Reviewer approval is required before
Jr integration begins.
