# CURRENT_TASK

Ticket: UNIVERSE-006
State: AWAITING_REVIEW
Next required actor: Reviewer (Lead Quant) — review + accept
Next ticket authorized: NONE

**Jr Deliverables (Hermes):**

1. Published CMC survivorship CSV as catalog universe dataset `ds_6513138a734c59c38beb29a29d761a506d0a1e25ce554aa57551e2bbfe1dea62`
2. 1,756 rows published, all with provenance labels (`death_date_is_proxy`, `source=cmc_data_api_unofficial`)
3. `universe_at(2020-01-01)` = 115 coins alive
4. `universe_at(2026-07-01)` = 153 coins alive
5. Report: `research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json`
6. Script: `scripts/research/publish_cmc_survivorship.py`

**Evidence:**

- `pytest tests/universe/test_cmc_survivorship.py` — 7/7 PASS
- `scripts/check_repo_control.py` — PASS
- Published dataset covers 1,603 coins with death-proxy dates, 1756 with birth dates

## Governing documents

- tickets/UNIVERSE-006.md (AWAITING_REVIEW)
- data/survivorship/cmc_dead_universe_full.csv
- research/sprint_004/42_CMC_UNIVERSE_PUBLISHED.json
