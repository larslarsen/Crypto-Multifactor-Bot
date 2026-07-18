# Sprint 002 Changelog

**Sprint:** 002 (literature and research-design refresh)
**Created:** 2026-07-18
**Research cutoff:** 2026-07-18
**Status:** literature refresh only; no empirical results; no factor validated

## Added (research/sprint_002/)

- `README.md` — scope and layout; states this is a literature/research-design refresh with
  no empirical results and no validation claims.
- `00_SCOPE_AND_SEARCH_METHOD.md` — databases, search strings, date coverage, inclusion/
  exclusion, tier classification, duplicate handling, verification method, limitations.
- `01_LITERATURE_REFRESH_2025_2026.md` — thematic narrative of the 15 verified sources.
- `02_LITERATURE_LEDGER.csv` — 15 verified sources LIT-024 … LIT-038 with full metadata.
- `03_SPRINT_001_ERRATA.csv` — one real bibliographic error found (LIT-018 year 2023 → 2025).
- `04_RESEARCH_DECISIONS.csv` — 8 design decisions (RD-01 … RD-08).
- `05_FACTOR_ROADMAP_UPDATE.md` — per-family design positions.
- `06_DATA_FEASIBILITY_BACKLOG.csv` — 10 data questions (DF-01 … DF-10) gating new families.
- `07_OPEN_RESEARCH_QUESTIONS.md` — 8 open questions.
- `factor_cards/DIL-01_token_dilution.md` — new candidate card (DEFERRED/UNTESTED).
- `factor_cards/MOM-01_literature_addendum.md`, `LIQ-01_...`, `CARRY-01_...`,
  `NET-01_...` — addenda stating what Sprint 1 specified, what changed, what is unchanged,
  new diagnostics, new data requirements, and why each remains untested.
- `CHANGELOG.md` — this file.

## Evidence Registry

- `research/evidence/hypotheses.yaml`: appended `H-011` (token-dilution, DEFERRED,
  UNTESTED). All H-001 … H-010 entries preserved unchanged. File remains valid JSON.

## Sprint 001 handling

- `research/sprint_001/` and `crypto_multifactor_research_sprint_v1_1/` left frozen and
  unedited.
- Real erratum (LIT-018 year) recorded in `03_SPRINT_001_ERRATA.csv`; the original Sprint 001
  row was not altered.

## Not changed

- Active engineering ticket (GOV-001) untouched.
- No RAW-001 or other implementation ticket authorized.
- No hypothesis marked SUPPORTED; no production code modified.
- Data/Research/Execution architecture unchanged.

## Verification performed

- Every cited source verified against its primary publisher/repository page (DOIs, arXiv ID,
  SSRN ID, NBER ID) on or before 2026-07-18.
- CSV column counts consistent; YAML syntax and hypothesis-ID uniqueness validated.
- Repository-control validator (GOV-001) remains PASS.
- Committed as one focused commit and pushed to origin/main.

## Focused correction — momentum and survivorship (appended 2026-07-18)

Added `LIT-038` (Han, Kang, Ryu; SSRN 4675565; revised 26 Mar 2026) as a working paper
(Tier C). It is the primary source for momentum implementation design: time-series and
cross-sectional momentum must be evaluated separately; transaction costs and daily
mark-to-market paths matter; portfolios may be liquidated before terminal backtest returns;
statistical significance of mean returns is insufficient evidence of realizable profitability;
long and short legs require separate attribution; margin, futures mechanics, and liquidation
assumptions must be explicit. Numerical results were not copied (not independently re-verified
from the PDF); only the abstract's qualitative conclusions are recorded.

Updated `01_LITERATURE_REFRESH_2025_2026.md`, `04_RESEARCH_DECISIONS.csv` (RD-01),
`factor_cards/MOM-01_literature_addendum.md`, and `05_FACTOR_ROADMAP_UPDATE.md` to use
LIT-038 as the principal momentum-implementation evidence and to keep the crypto-carry paper
(LIT-025) associated with `CARRY-01`. Added an explicit Survivorship and delisting section
anchored on Ammann/Burdorf/Liebi/Stöckl (SSRN 4287573, confirmed current at 2026-07-18); no
newer superseding study was located, so survivorship-free universe construction remains a
Tier-0 data requirement and the absence of a newer paper is noted as non-evidence of
improvement.

Source count raised from 14 to 15 (LIT-024 … LIT-038). LIT-024 … LIT-037 were not renumbered
or rewritten. `research/evidence/hypotheses.yaml` and the active ticket GOV-001 are unchanged
by this correction.
