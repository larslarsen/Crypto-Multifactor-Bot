# DF-01 — Coin Metrics Point-in-Time Supply Authority Audit Report

**Status:** AWAITING_REVIEW
**Recommendation:** NO_PRIMARY_PIT_SUPPLY_AUTHORITY
**Next ticket authorized:** `NONE`
**Next required actor:** Reviewer
**Date:** 2026-07-21
**Auditor:** Jr Dev — Hermes (Hy3:free)
**Authorized under:** REVIEW-0122

## Scope
Evidence synthesis only. Determine whether accepted Sprint-003 Coin Metrics Community
evidence authorizes historical point-in-time circulating / max / FDV supply. No network
access, production code, tests, schema, factor work, or new factual inference.

## Decision: NO_PRIMARY_PIT_SUPPLY_AUTHORITY
All eight gates block. No primary point-in-time supply authority is granted.

## Gate results (all blocking)
- **G01 FAIL_SEMANTIC** — `SplyCur` is issued supply, not circulating float.
- **G02 FAIL_PARTIAL** — BTC/SUSHI observations exist; BONK/micro-cap Community coverage absent.
- **G03 FAIL_UNKNOWN** — publication/known-time lag is unbounded.
- **G04 FAIL_UNKNOWN** — server-side revisions/backfills exist with no retained historical vintages.
- **G05 FAIL_PARTIAL** — request identities/hashes are recorded, but original raw response bodies are not repository-retained.
- **G06 FAIL_UNKNOWN** — licensing and internal raw-retention authority were not established.
- **G07 FAIL_UNKNOWN** — no contemporaneously published historical value was reproduced.
- **G08 FAIL_SEMANTIC** — future unissued/max supply is absent, so FDV and required denominator history cannot be constructed.

## Evidence provenance
- Ten repository-native artifacts used (hashes/sizes in `EVIDENCE_REGISTER.csv`): the
  sprint_002/003 inventories, decision registers, schema/semantics audit, correction/
  revision audit, research-data and research-lead decisions, evidence reconciliation,
  hash verification, and the Coin Metrics source note.
- The **original Coin Metrics Community API response bodies are NOT repository-retained**.
  Only their accepted inventory, request identities, SHA-256 hashes, and audit findings
  remain. This is recorded explicitly (G05); the bodies are not claimed as repo-native.

## Accepted role preserved
Coin Metrics Community retains its accepted status as conditional
`REFERENCE_METADATA` / `EXPLORATORY_PHASE2` only. No accepted Sprint-003 finding is
overruled. No new factual inference is introduced.

## Downstream impact
- **SIZE-01**, **DIL-01**, and supply-dependent **NET-01** work remain **blocked**.
- No prospective collector, code, schema, migration, or implementation authority is
  granted by this audit.

## Deliverables
- `docs/reviews/DF-01_COIN_METRICS_PIT_SUPPLY_AUTHORITY_REPORT.md` (this report)
- `research/df_01/EVIDENCE_REGISTER.csv` (10 rows, hashes/sizes, retained flag)
- `research/df_01/decision_matrix.csv` (8 gates, all blocking)
- `research/df_01/sources/coin_metrics.md` (synthesis source note)

## Validation
- `python3 scripts/check_repo_control.py`: PASS
- `git diff --check`: clean
- CSV shape: register 10 data rows (E01-E10), matrix 8 gate rows (G01-G08), 0 CR bytes
- Evidence path/sha256/size verified against the 10 retained repo artifacts
- All 8 gates present and blocking
- No files outside the allowed DF-01 scope (tickets/, docs/reviews/, research/df_01/,
  backlog, README, CURRENT_TASK) were modified
