# REVIEW-0217 — ARCH-002 CHANGES_REQUIRED

**Ticket:** ARCH-002 — UniverseBinding Contract  
**Decision:** CHANGES_REQUIRED  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Base:** `10b3ff9` + uncommitted `TYPE_CHECKING` fix in `paper_loop.py`

## Verdict

**CHANGES_REQUIRED.** API surface and fail-closed wiring are directionally right. Runtime membership semantics are inverted and unusable for research/paper.

## What works

| Item | Notes |
|------|--------|
| Protocol + adapter shape | `UniverseBinding`, `CMCSurvivorshipBinding`, loaders |
| Paper loop API | `run_loop(universe_binding=...)`; empty → `PaperExecutionError` |
| Fingerprint fields | `universe_dataset_id`, `universe_code_version`, `survivorship_policy` on result |
| Invalidation helper | `SURVIVORSHIP_INVALID_ARTIFACT_IDS` + `is_survivorship_invalid` |
| Circular import fix | `TYPE_CHECKING` import in `paper_loop.py` (uncommitted) — correct |
| Unit tests | Birth/death/immortal/empty/static-list rejection green |
| Gates (Jr) | pytest universe+execution PASS; ruff clean; control PASS |

## Blocking issues

### 1. Dead-only graveyard used as membership (critical)

UNIVERSE-006 published a **dead-coin** registry (1,756 inactive). ARCH-002 treats
`CMCSurvivorshipProvider.universe_at(t)` as the **research universe**.

Empirical check on `data/survivorship/cmc_dead_universe_full.csv`:

| decision_time | raw `universe_at` size | paper-mapped via key_map |
|---------------|------------------------|---------------------------|
| 2020-01-01 | 18 | mostly unmapped `cmc_*` |
| 2024-01-01 | 15 | mostly unmapped `cmc_*` |
| 2026-07-01 | **0** | empty → paper loop fails closed |

Liquid names (XBTUSD, ETHUSD, …) are **active** and **absent** from the graveyard.
They never enter membership. Scripts that load `load_paper_universe_binding` cannot
run a normal liquid TSMOM panel.

**Required semantics (ADR-0014):**  
tradable panel = (symbols with quality bars / declared panel) **minus** CMC-dead at `t`  
(with name-safe ticker disambiguation), **not** “whoever is in the dead list and not yet dead.”

### 2. `key_map.get(iid, iid)` leaks raw CMC ids into paper universe

```python
return frozenset(self.key_map.get(iid, iid) for iid in ids)
```

Unmapped dead coins become `cmc_1229`-style keys in the paper loop. Only 4 base tickers
hit the paper map (SOL/UNI/CRV/OP collision set). Paper binding must return **only**
mapped paper symbols (or fail closed if intersection is empty when a panel map is required).

### 3. No integration proof on published catalog dataset

Loaders resolve catalog type `cmc_survivorship_universe`, but there is no Jr evidence of
a successful `load_paper_universe_binding` against the real UNIVERSE-006 pin producing a
sensible panel for DATA-011 bar symbols. Unit tests use synthetic in-memory providers only.

### 4. Uncommitted circular-import fix

`TYPE_CHECKING` fix is correct and required; must be committed with the rework.

## Non-blocking

- `coverage_report` leaves `with_bars` / `missing` as `None` (acceptable stub; fill in later).
- `quality_cleared_bars.py` / `extend_binance_history.py` still mention static map keys
  (data tooling, not membership for exp/paper) — OK for now.
- Synthetic path in `run_paper_momts.py` still builds prices from `PAPER_TO_INSTRUMENT_ID.keys()`
  for synthetic store only — flag for cleanup, not blocking if real path uses binding.

## Required rework (Sr)

1. Redefine paper binding as **panel ∩ ~dead(t)** (or composite provider), not dead-list membership.
2. Name-safe CMC join (reuse DATA-011 `PAPER_BASE_TO_NAME` pattern or shared helper).
3. Paper `universe_at` returns only paper keys; no `cmc_*` leakage.
4. Empty intersection after panel filter → fail closed with clear error.
5. Test: at `t=2024-01-01`, binding includes XBTUSD/ETHUSD (panel) and excludes a known
   dead mapped name after death; at recent `t` panel is non-empty when bars exist.
6. Commit `TYPE_CHECKING` fix with rework.

## Next

Next ticket authorized: **NONE**. Rework ARCH-002 → AWAITING_REVIEW again.
