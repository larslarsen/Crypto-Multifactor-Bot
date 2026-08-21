# CEX-002 Report-Split Integration, Focused-Commands Failure, and No Candidate Resume

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/126_CEX002_REPORT_SPLIT_SOURCE_ACCEPTANCE.md`
Integration base: `1d14e7adef4876aa14701a7af734a1dd644cb527` (review-126 reviewer publication commit)

## 1. Environment

- `HEAD == origin/main == e0068e73192659ac3870aceeb03e2d2caa3402e7` (after Hermes integration commit; origin is at `e0068e7` too).
- No candidate process running (ps scan: none).
- Index empty after integration commit (`git diff --cached --name-only` = 0 lines).
- Report 62 monolith on disk: SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`, 1,059,297,547 B (1.06 GB) — byte-preserved from review 121's status-2 resume; matches review 126's accepted monolith. Untracked-at-HEAD 62 at `1d14e7a` is the 26 MB stale copy (`05fa7b0a`); working-tree 62 is the monolith. The 62 monolith is NOT staged and NOT copied to `evidence/prior_reports/` yet (see §4 — preservation was not reached because the candidate was not run; see deviation note §6).
- 17 CEX fixture files present and unchanged.

## 2. Integration commit

Hermes established `HEAD == origin/main == 1d14e7a` and rehashed the accepted/frozen paths. The three source/test paths differ from HEAD (they were not yet in `1d14e7a`), so Hermes staged exactly those three and committed one forward integration:

| Path | Accepted SHA-256 (review 126) | Working-tree hash | vs HEAD |
|---|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `6ef5c10c4ee9a5f7b19eb6ff711f73fa71eab792e3b9f393c8ae98d7b9504c8d` | `6ef5c10c…` | differs → staged |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `b4e9235406be5276619b4a69017ddb87a8cffefb691c2673f2e3b875cc775d96` | `b4e92354…` | differs → staged |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `7d046ce36d0912b728de7571cf49a227eda63191cb94fc9096f34b8fe5f67537` | `7d046ce3…` | differs → staged |

Frozen dependencies (accepted unchanged by review 126) — verified identical to HEAD, not staged:

| Path | SHA-256 (accepted) | Working-tree hash | vs HEAD |
|---|---|---|---|
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` | `f231930f…` | identical (not staged) |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` | `30388dba…` | identical (not staged) |

No `git reset`/`restore`/`checkout`/`stash`/`clean`/worktree-rewrite was used (review 126 boundary). Exact three paths staged; unrelated dirty DEX/BitMEX/catalog/ingest/config/research paths were not staged. `HEAD == origin/main == e0068e7` after push; index empty.

## 3. Focused commands (stop-on-first-failure)

Run in order. Command 1 is nonzero → sequence STOPS here. Commands 2–5 were NOT run.

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
   - Exit: **1**
   - Result: **2 failed, 254 passed** (256 items collected; 209 unique test functions, 4 `@parametrize` expansions → 256 items — matches review 126's "209 uniquely named test functions").
2. (NOT run) `tests/test_download_atomicity.py`
3. (NOT run) `ruff check …`
4. (NOT run) `python3 scripts/check_repo_control.py`
5. (NOT run) `git show --check --oneline --no-renames HEAD`

A nonzero exit on command 1 stops the sequence immediately: commands after a failure are not run, and **no candidate is started**.

### Failure 1 — `test_manifest_rows_bind_identity_cadence_and_interval`

```
tests/acquisition/test_binance_usdm_harmonic_qualification.py:4477: in test_manifest_rows_bind_identity_cadence_and_interval
    assert report.storage["acquisition_manifest"]["rows"] == published
E   KeyError: 'rows'
```

Context (lines 4472–4477): the test calls `run_source_qualification(store_root=tmp_path, index=index, current_contracts=_contracts("BTCUSDT"))` and asserts the in-memory `report.storage["acquisition_manifest"]["rows"]` equals the published rows. The preceding line (`report.acquisition_manifest["rows"]` at 4475) and the equality `[row["key"] for row in published] == [row["key"] for row in rows]` (4476) PASS; only the **storage-surface** `["rows"]` key is missing.

Interpretation: under the accepted source `6ef5c10c`, the in-memory `report.storage["acquisition_manifest"]` is presented as a summary/receipt surface without a `rows` collection, whereas the accepted test `7d046ce3` (line 4477, and the in-memory-full-authority contract at 6010–6019) expects `rows` to remain present in memory on the storage surface. This is the ADR-0019 source/test inconsistency surfaced at runtime (review 126 conducted a static acceptance with "no pytest" — runtime evidence remains Hermes's responsibility).

### Failure 2 — `test_compact_receipt_never_duplicates_the_detailed_manifest`

```
tests/acquisition/test_binance_usdm_harmonic_qualification.py:6009: in test_compact_receipt_never_duplicates_the_detailed_manifest
    assert len(named) <= 1
E   AssertionError: assert 3 <= 1
E    +  where 3 = len(['data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-01.zip',
                       'data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-02.zip',
                       'data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2020-03.zip'])
```

Context (lines 6008–6009): after writing the receipt via `write_qualification_report`, the test computes the row keys whose `key` bytes appear in the rendered receipt and asserts `len(named) <= 1` (ADR-0019 permits at most one schema-lineage key in the receipt). Three monthly-kline row keys (`BTCUSDT-1h-2020-01/02/03.zip`) leaked into the receipt, violating the `≤ 1` invariant.

Both failures are deterministic, in-process, and driven by the accepted source/test fixtures (no network, no live caches, no on-disk monolith); they are independent of the candidate resume or the listing/cache state.

## 4. Candidate preconditions / resume / after proof

NOT reached. The stop-on-first-failure rule halted the sequence at command 1. No before-snapshot beyond §1 was required for a candidate that never launched; no monolith preservation copy (`evidence/prior_reports/sha256/46d1980e….json`) was made; no candidate invocation ran; no after-snapshot was captured; no manifest-receipt validation ran; no migration/sample/Gate-2/normalization/catalog/Nautilus/PAPER/LIVE/other-ticket work ran.

## 5. Report 62 disposition

- On-disk 62 = monolith `46d1980ec…` / 1,059,297,547 B (matches review 126 accepted monolith).
- Because the candidate was never run (and thus no valid terminal status-0/2 replacement was produced), review 126's §"Record and publication" prohibition on staging an "unchanged report" applies: **62 is not staged and not committed.** The 62 working-tree modification (`M` vs the 26 MB HEAD copy `05fa7b0a`) is left uncommitted.
- The monolith has not been copied to `data/cex002_qualify/evidence/prior_reports/sha256/46d1980ec….json` because preservation precedes the candidate (review 126 §"Preserve the terminal monolith") and the candidate never ran — preservation is therefore not performed here. (Had the candidate run, preservation would occur before the candidate; the absence of a candidate means preservation is deferred to a successful-candidate run.)

## 6. Deviations

- Focused command 1 produced a nonzero exit (2 failed); commands 2–5 and the candidate resume were NOT executed. This is the review-126-mandated stop, not a deviation in method.
- No repository-control/Ruff/whitespace commands were executed due to the stop; they are deferred to a successful focused run.

## 7. Explicit no-op statement

No candidate was started. No monolith preservation copy was created. No manifest-receipt validation ran. No `git reset`/`restore`/`checkout`/`stash`/`clean`/worktree-rewrite was executed. No migration, sample download, amendment-ledger creation, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, Git LFS, external artifact service, paid source, report truncation, unrelated-ticket work, or automatic second candidate invocation occurred. The only actions this session: integration commit of the three accepted source/test paths (`e0068e7`), hash re-verification of the accepted/frozen paths and fixtures, and focused-command-1 execution (failed). The 1.06 GB 62 monolith and all unrelated dirty DEX/BitMEX/catalog/ingest/config/research paths remain exactly as found, uncommitted.

## 8. Disposition / stop point

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. `candidate_status` undefined (candidate not run). The two focused-command-1 failures (`test_manifest_rows_bind_identity_cadence_and_interval` KeyError `rows`; `test_compact_receipt_never_duplicates_the_detailed_manifest` assert 3 ≤ 1) constitute the stop point for review-126's stop-on-first-failure sequence.

Hermes stops here for reviewer inspection. The reviewer must decide whether the source/test drop accepted in review 126 contains a runtime defect (in-memory storage manifest shape / receipt row-key leakage) that requires a corrected source/test re-acceptance, or whether the accepted tests require a source-side correction — and authorize the next slice. Next ticket remains `NONE`.
