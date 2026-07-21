# REVIEW-0101 - REF-002 LICENSING CORRECTION REQUIRED

**Ticket:** REF-002 - Bybit Instrument Event Source Feasibility Audit
**Disposition:** CORRECTION REQUIRED
**Assigned role:** Jr Dev - OpenCode GPT-5.4 high
**Execution mode:** resume the existing OpenCode session; do not reread the superseded review chain
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Accepted Evidence

- All 26 registered external files exist and match their recorded byte sizes and SHA-256 values.
- The register has 20 columns and the decision matrix is rectangular with one recommendation.
- BTCUSDT and BTCUSDU26 are correctly classified.
- The rejected `status=Settled` request and current `status=Closed` fallback are captured honestly.
- `python3 scripts/check_repo_control.py` passes.

## Blocking Findings

1. Gate G07 is marked PASS without captured official terms or a licensing citation that establishes
   permission for the intended internal raw-evidence retention. Public accessibility and keeping raw
   files outside Git do not independently establish permission. Because G07 is mandatory for
   `PROSPECTIVE_ONLY_AUTHORITY`, the current recommendation is not yet supported.
2. No qualifying `status=Settled` record was returned. BITUSD is a supplemental `Closed`
   `InversePerpetual` delisting exemplar, not a selected settled instrument or completed futures
   delivery exemplar. Report and matrix terminology must preserve that distinction.
3. The required commit and push did not occur. The worktree contains the authorized FUND-002 closing
   records, REF-002 authorization, and REF-002 evidence as pending changes.

## Single Correction Pass

1. Capture one official Bybit legal/terms source applicable to API or market-data use, including body
   and headers under `/tmp/ref_002_raw`, and register both with complete metadata. Quote or cite only
   the exact provision relevant to local internal research/evidence retention. If access fails or the
   provision is not explicit, record that result and classify licensing as unknown.
2. Re-evaluate G07 literally. If permission is not established, set G07 to FAIL and publish
   `NO_AUTHORITY`. Retain `PROSPECTIVE_ONLY_AUTHORITY` only if the captured official terms affirmatively
   support the intended retention.
3. State that the required settled branch stopped without a candidate. Keep BITUSD only as a
   supplemental closed/delisted perpetual observation; do not call it settled or delivered. Do not
   perform additional instrument or announcement exploration.
4. Reconcile the report, source note, evidence register row count, decision matrix, README, backlog,
   ticket, and current-task state. Record fresh literal validator and repository-control results.
5. Set REF-002 to `AWAITING_REVIEW`, return control to Reviewer, retain
   `Next ticket authorized: NONE`, stage only the authorized pending records, commit, push, and stop.

Do not edit executable source, tests, schemas, migrations, ADRs, or generated datasets. No pytest run
is required.
