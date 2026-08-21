# CEX-002 Test Integration and Focused-Command Stop-on-Failure (C3)

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/130_CEX002_SPARK_TEST_SOURCE_ACCEPTANCE.md`
Integration base: `fee34a1010beddcc27166282af9c7f5cde139dba` (review-130 reviewer publication commit)

## 1. Environment

- `HEAD == origin/main == d428aecf20e92528f16905efce9fb75ae9ea4e68` (after Hermes test-integration commit; origin advanced to `d428aec`).
- No candidate process running (ps scan: none).
- Monolith on disk: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`, 1,059,297,547 B — matches review 130; not yet copied to `evidence/prior_reports/` (copy is a pre-candidate step reached only after C1–C5 pass).
- 17 CEX fixtures intact.

## 2. Test-integration commit

Hermes established `HEAD == origin/main == fee34a1`, rehashed the accepted test plus the four frozen source/test paths, the 17 fixtures, and the monolith — all matched review 130 (no mismatch). Hermes staged **exactly** `tests/acquisition/test_binance_usdm_harmonic_qualification.py` (the single accepted test correction `23f1159f8d664f0c55b26498ef69ea72196bb70279055ccf6f9da06dea0d550b`) and committed one forward test-integration commit. The four frozen paths (src `6ef5c10c`, cli `b4e92354`, download `f231930f`, atomicity `30388dba`) were verified identical to HEAD and not staged. No `reset`/`restore`/`checkout`/`stash`/`clean`/worktree-rewrite was used; the monolith, ignored data, controls, records, database sidecars, and every unrelated dirty DEX/BitMEX/catalog/ingest/config/research path were left untouched and unstaged.

```
commit d428aecf20e92528f16905efce9fb75ae9ea4e68 (HEAD -> main, origin/main)
Author: Jr Dev - Hermes
    CEX-002: integrate review-130 corrected CEX test source (Spark test correction)

1 file changed, 37 insertions(+), 6 deletions(-)
```

`HEAD == origin/main == d428aec`, index empty after push.

## 3. Restart of focused commands (review 130 stop-on-first-failure sequence)

Run in order. Review 130: "Any nonzero exit stops the remaining commands and the candidate."

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
   - Exit: **0**. Result: **256 passed** (0 failed). Unique test functions: **209** (review 130 notes "209 uniquely named test functions"; pytest collected 256 items — the static 209 plus parametrized expansions; Hermes records the actual collected count, not the static definition count). ✓ (The two C1 failures from record 127 are closed.)
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
   - Exit: **0**. Result: **18 passed** (18 collected). ✓
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
   - Exit: **1**. `Found 2 errors.`
4. (NOT run) `python3 scripts/check_repo_control.py`
5. (NOT run) `git show --check --oneline --no-renames HEAD`

Stop point: **command 3 returned nonzero** → sequence halts. Commands 4 and 5 were NOT run. **No candidate invocation was started; no monolith preservation copy was made; no before/after snapshot, candidate resume, or manifest-detail validation was performed.**

## 4. Ruff errors (verbatim)

```
F402 Import `fields` from line 39 shadowed by loop variable
    --> src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py:6488:25
     |
 6486 |         samples: dict[str, list[dict[str, Any]]] = {}
 6487 |         provenance = [markets_prov]
 6488 |         for name, path, fields in history_specs:
     |                         ^^^^^^
 6489 |         payload, prov = self._fetch(path, params=params, headers=headers)
 6490 |         parsed = parse_coinalyze_history(payload, path=path, required_point_fields=fields)

F841 Local variable `rendered` is assigned to but never used
    --> tests/acquisition/test_binance_usdm_harmonic_qualification.py:6020:5
     |
6018 |     assert receipt_path.stat().st_size < REPORT_PUBLICATION_CEILING_BYTES
6019 |
6020 |     rendered = receipt_path.read_bytes()
     |     ^^^^^^^^
6021 |     rows = report.acquisition_manifest["rows"]
6022 |     assert len(rows) > 1
     |
help: Remove assignment to unused variable `rendered`

Found 2 errors.
No fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).
```

### Error locations and provenance

- **F402 — source (`6ef5c10c`):** `field, fields` is imported from `dataclasses` at module level (source line 41, reported by ruff as "from line 39"). Inside `run_source_qualification`'s Coinalyze-history sampling loop, the local `for name, path, fields in history_specs:` (`for … fields …`) shadows the imported `fields`. This lives in **frozen source** `6ef5c10c8ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d`, accepted by review 126 and integrated at e0068e7. It was never surfaced before because review 126's sequence stopped at C1 (C3 never reached); review 130 restarted the sequence to C3.
- **F841 — test (`23f1159f`):** `rendered = receipt_path.read_bytes()` at test line 6020 is dead: `grep -n "rendered" tests/acquisition/test_binance_usdm_harmonic_qualification.py` shows its only references are (a) a separate in-use `rendered` at lines 5814–5816, and (b) the orphaned assignment at 6020. The previous test version (`7d046ce3`) used `rendered` at the `assert len(named) <= 1` / `if row["key"].encode("utf-8") in rendered` block (old lines 5996/6002/6008). Spark's accepted correction (`23f1159f`) replaced that block with the new "No complete row objects should occur in the compact receipt text, but selected keys may still appear as lineage references in the compact sample_plan" logic and dropped the `rendered` uses while keeping the assignment. The reviewer's review-130 acceptance did not run ruff (review 130 line 30: "The reviewer ran no pytest, Ruff, repository-control, …"), so F841 was undiscovered.

## 5. Why Hermes did not fix these

Both errors are in paths the boundaries forbid Hermes from editing:

- Review 126 §"Hermes integration authority" (line 56–62): Hermes stages exactly the accepted source/test paths and may not edit test source beyond the accepted hash; it must not alter production source.
- Review 130 §"Boundaries" (line 119–124): "No production/test edit … is authorized after the exact test integration."
- Review 120 §"Hermes integration" (line 61–62) and the recurring "must not stage … database sidecars, control files, records" discipline.

Accordingly Hermes does not modify `6ef5c10c` (src) or `23f1159f` (test) to silence either rule. The two violations are reviewer-resolution findings against the accepted source/test drops.

## 6. Candidate / preservation / after-proof status

NOT reached (stop at C3). Specifically:
- No monolith preservation copy was written to `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ec….json`.
- No before snapshot / 40,771-entry listing precondition check was performed for launch.
- No candidate invocation ran (`--candidate-plan-only`), so no `candidate_status`, no after snapshot, no manifest-detail validation (compactness / content-address / reader / 733,203-row / aggregate / order / uniqueness / preservation).
- Report 62 on disk is unchanged by Hermes; the on-disk monolith remains `46d1980ec…` / 1,059,297,547 B (unmodified). It is **not** staged or committed (no valid terminal status-0/2 replacement was produced).

## 7. Explicit no-op statement

No candidate was started. No monolith preservation copy was created. No before/after snapshot was captured. No manifest-detail validation ran. No `git reset`/`restore`/`checkout`/`stash`/`clean`/worktree-rewrite was executed. No plan migration, sample download, amendment-ledger creation, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, Git LFS, external artifact service, report truncation, scope reduction, or unrelated-ticket work occurred. The only source/test change is the review-130 integration commit `d428aec` (one test file). The 1.06 GB 62 monolith and all unrelated dirty DEX/BitMEX/catalog/ingest/config/research paths remain exactly as found, uncommitted.

## 8. Stop point / disposition

Stop point: review-130 focused-command 3 (ruff) returned nonzero (`Found 2 errors`, exit 1) — F402 in frozen source `6ef5c10c` and F841 in accepted test `23f1159f`. Per review 130 stop-on-first-failure, C4/C5 and the corrected candidate resume are deferred.

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. `candidate_status` undefined. Next ticket remains `NONE`.

## 9. Reviewer action required (Hermes cannot resolve)

The two ruff errors are in reviewer-accepted/frozen paths that Hermes is prohibited from editing. The reviewer must choose one of:

1. **Re-authorize a corrected source/test drop** that silences both ruff errors (F402 by renaming the `fields` loop variable in src `6ef5c10c`; F841 by removing the orphaned `rendered = receipt_path.read_bytes()` at test line 6020, or restoring its legitimate single-key-in-receipt assertion), then re-accept with a new hash so Hermes may integrate the corrected drop; or
2. **Carve an explicit ruff per-path/per-rule exception** (e.g. scoped `per-file-ignores` / line-range ignore for the two accepted paths) and confirm the focused-command sequence is to be re-run under that exception; or
3. **Accept the stop-at-C3 outcome** and direct Hermes to the next gate.

Hermes will not self-edit the accepted source/test or self-suppress ruff. Stopped here for inspection.
