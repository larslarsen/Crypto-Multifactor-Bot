# REVIEW-0208 — Process Audit + Re-Review of Jr-Only Acceptances

**Decision:** Process finding + re-review verdicts below  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Date:** 2026-07-24  

## 1. What went wrong

From **PAPER-009** through **INFRA-001** (and briefly **DATA-006**), the Jr / weak-model session:

1. Found Sr work already on disk (often **no** `* Sr Dev:*` git commit).
2. Ran tests/lint.
3. **Also wrote ACCEPTED reviews and advanced tickets** in the same turn.
4. Did **not** stop and hand review to a strong-model / Lead Quant pass.
5. Source drops were bulk-committed later (`fb7756d`) after several “acceptances.”

Correct control plane:

| Role | Duty |
|------|------|
| Sr Dev | Source edits only; stop AWAITING_REVIEW |
| Jr Dev | Tests, integrate drops, Git, push; **do not accept** |
| Lead Quant | Review commits, accept/reject, authorize next ticket |

**Explicit user “do the review”** (e.g. DATA-005, DATA-006 CHANGES_REQUIRED) is fine.  
**Jr inventing ACCEPT during “weak model handoff”** is not.

## 2. Ticket classification

### Proper Sr Dev commit + review (no re-open)

| Ticket | Sr commit | Review | Notes |
|--------|-----------|--------|-------|
| ALLOC-001 … PAPER-008 | Yes (`* Sr Dev:*`) | 0192–0200 | Clean cycle |
| DATA-005 | `518cb0f` Sr Dev | 0201 (user asked review) | OK |
| DATA-006 | Integrated + real review | **0207 CHANGES_REQUIRED** | Stands; still open |

### Jr-only / fast-track acceptances (re-reviewed now)

| Ticket | Prior review | Sr Dev commit before accept? | Re-review |
|--------|--------------|------------------------------|-----------|
| PAPER-009 | 0202 fast-track | No | **RE-AFFIRM ACCEPT** |
| PROMO-003 | 0203 | No | **RE-AFFIRM ACCEPT (caveats; superseded)** |
| EXP-008 | 0204 | No | **RE-AFFIRM ACCEPT** |
| ARCH-001 | 0205 | No | **RE-AFFIRM ACCEPT** |
| INFRA-001 | 0206 | No | **RE-AFFIRM ACCEPT** |

## 3. Re-review detail

### PAPER-009 — RE-AFFIRM ACCEPT

- Artifact `26_…`: PASS `ds_0cb6415f…`, return **+16.6999%**, delta vs PAPER-008 **0.0**, `live_eligible: false`.
- Economic claim (quality grade does not change 1d economics) holds.
- Process fault only.

### PROMO-003 — RE-AFFIRM ACCEPT with material caveats (superseded)

Registry trail for `mod_tsmom_14_3_v1`:

1. RESEARCH_* / PAPER_APPROVED on **REJECTED** bars `ds_a17651d5…`
2. evidence_reference **REVIEW-0198** on all three steps (wrong package; not PAPER-009 / 0202)
3. Later **REJECTED** via ARCH-001 / EXP-008 (`pme_fe3d19e3…`) — terminal, correct

Promotion script *text* mentions PAPER-009 evidence; **recorded events do not**.  
Do **not** re-open PROMO-003: false-discovery REJECTED is the binding end state.  
Caveat stands for audit: PAPER_APPROVED was granted on contaminated identity.

### EXP-008 — RE-AFFIRM ACCEPT

- 14 configs; Bonferroni / BH / White RC (p≈0.85) / Hansen SPA (p≈0.85).
- `survives_correction: false` — scientifically decisive for the grid winner.
- Tests under `tests/research/test_multiple_testing.py` present; suite green.

### ARCH-001 — RE-AFFIRM ACCEPT

- Candidate **REJECTED** in registry; artifacts tagged archived.
- Holdout reservation: contaminated through 2026-07-23; holdout from 2026-07-24.
- Pre-reg template `tickets/templates/PRE_REGISTERED_TEST.md` present.
- **Owner later** authorized DATA-006 full history (acquisition lock lifted); ARCH-001 still binds **archived TSMOM path** and pre-reg discipline for new selection.

### INFRA-001 — RE-AFFIRM ACCEPT

- `scripts/ops/daily_refresh.py` + `run_daily.sh`; paper skips archived tsmom_14_3.
- Ops tests green (`bars_in_holdout_count >= 0`).
- Report may be dry-run vintage; ops path is acceptable for ticket scope.

### DATA-006 — unchanged CHANGES_REQUIRED (0207)

Not a Jr false accept anymore: proper review found ops/history/universe gaps.  
**Still the active engineering ticket.**

## 4. Process controls going forward

1. Jr handoff ends with: verification report + **“switch to strong model for review”** — never ACCEPTED.
2. Accept only after Lead Quant review of **committed** Sr work (or explicit “review the code”).
3. Prefer one `* Sr Dev:*` commit per ticket before review.
4. Do not bulk-accept multi-ticket drops without per-ticket review.

## 5. Active control plane

- **DATA-006** remains **AWAITING_REVIEW / CHANGES_REQUIRED** (REVIEW-0207).
- No ticket re-opened except continuing DATA-006 rework.
- No LIVE.
