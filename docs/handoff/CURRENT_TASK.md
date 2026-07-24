# CURRENT_TASK

Ticket: DATA-010
State: READY
Next required actor: Sr Dev (Strong Model) — fix DATA-010 (then DATA-009, DEX-002, DATA-008)
Next ticket authorized: NONE

**REVIEW-0211 retrospective (backwards from DATA-010):**

| Ticket | Verdict |
|--------|---------|
| DATA-010 | CHANGES_REQUIRED — U50 coverage, bad addresses, thresholds, rejects |
| DATA-009 | CHANGES_REQUIRED — active-only universe; delta-only republish; watermark overwrite |
| UNIVERSE-004 | ACCEPTED (caveats: death untested; token≠pool queue) |
| DEX-002 | CHANGES_REQUIRED — fail-open screening (`passed: true` with null liq/vol) |
| DATA-008 | CHANGES_REQUIRED — weak symbol screen; broken UP/DOWN filter; stables pollution |
| DATA-007 | **ACCEPTED (clean)** — first ticket needing no code changes |

Full write-up: `docs/reviews/REVIEW-0211_RETRO_CODE_REVIEW_DATA007_THROUGH_010.md`

**Rework order (recommended):** DATA-010 → DEX-002 (screening fail-closed; unblocks DATA-010 quality) → DATA-009 → DATA-008.

**Process:** Jr must not ACCEPTED. Always AWAITING_REVIEW for strong-model review first.

## Governing documents

- docs/reviews/REVIEW-0211_RETRO_CODE_REVIEW_DATA007_THROUGH_010.md
- tickets/DATA-010.md
- tickets/DATA-009.md
- tickets/DEX-002.md
- tickets/DATA-008.md
- tickets/UNIVERSE-004.md
- tickets/DATA-007.md
