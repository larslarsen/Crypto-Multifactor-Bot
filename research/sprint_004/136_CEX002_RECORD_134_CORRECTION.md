# CEX-002 Record 134 Forward Correction

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/135_CEX002_TERMINAL_CANDIDATE_REVIEW.md`
Corrected record: `research/sprint_004/134_CEX002_RUFF_INTEGRATION_AND_CANDIDATE.md`

## Decision

This record is a forward correction to record 134. It does not rewrite, replace, or
delete record 134.

Review 135 accepts the integration, compact report, content-addressed manifest detail,
preserved monolith, and terminal status-2 blocked outcome, but rejects record 134 as the
authoritative execution record until these identity and arithmetic corrections are
published.

## Integration identities

Record 134 incorrectly labels stale commits as the review-133 integration identity.
The corrected integration identities are:

- `e0068e73192659ac3870aceeb03e2d2caa3402e7` is the earlier review-126 report-split
  integration.
- `d428aecf20e92528f16905efce9fb75ae9ea4e68` is the earlier review-130 test
  integration.
- `dba025c72a5d0b09d09790b51d09cfdcf32e9dfd` is the review-133 two-path Ruff
  integration.

The correct review-133 integration commit is
`dba025c72a5d0b09d09790b51d09cfdcf32e9dfd`, committed at
2026-08-21T13:48:43-07:00 before the candidate began at
2026-08-21T13:51:14-07:00.

## Focused-command correction

The original C5 transcript is unavailable in the repo-local paths searched for this
publication. This correction therefore does not invent or reconstruct output.

Record 134's focused-command sequence remains the actual five-command sequence in order,
but the recorded `HEAD` and C5 identity must be read as the correct review-133
integration commit `dba025c72a5d0b09d09790b51d09cfdcf32e9dfd`, not `d428aec`.

The five focused commands were:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

The Git timestamp proof in review 135 establishes that the candidate ran after
`dba025c72a5d0b09d09790b51d09cfdcf32e9dfd`, not after `d428aec`.

## FAPI cache correction

Record 134 copied the FAPI cache delta from the prior record-121 run. The corrected
candidate cache state is:

- before candidate: 9 files, 9,697,128 bytes;
- candidate-added file: 1 file, 1,077,579 bytes, modified at
  2026-08-21T13:58:38-07:00;
- after candidate: 10 files, 10,774,707 bytes.

## Manifest-detail correction

Record 134 reverses the accepted record phases and misstates the iterator/header
arithmetic. The corrected manifest-detail facts are:

- production writes and validates phases in this order:
  `header -> row -> collision -> rejection -> raw_validation_pending_key`;
- the descriptor's 1,466,395 total records comprise one header plus 1,466,394 data
  records;
- `iter_manifest_detail` skips the header and yields exactly 1,466,394 records.

## Unchanged accepted evidence

Every other accepted record-134 candidate, artifact, invariant, mutation, and stop claim
remains unchanged. The accepted terminal outcome remains `BLOCKED` / `accepted=false`;
Gate 1 has not passed; version-3 plan migration and download remain unauthorized; samples
remain empty; no Gate 2, normalization, catalog publication, Nautilus work, Harmonic
Trader work, payoff analysis, PAPER, LIVE, or next-ticket work is authorized.
