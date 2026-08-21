# CEX-002 Listing Integration and Candidate Resume

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/120_CEX002_LISTING_SOURCE_ACCEPTANCE.md`
Preceding proved state: record `research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md`
Integration base: `f987da574b3c24360d9cfbab82b282343ad1c9c0` (review-120 publication commit)

## 1. Integration commit

HEAD == origin/main established at review-120 publication commit `f987da57` (71c4421..e99f475).
Hermes staged exactly the five accepted paths (no unrelated dirty DEX/BitMEX/catalog/ingest/config/research paths):

| Path | Accepted SHA-256 (review 120) | Verified |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `b6077bf833ae59b2414b441564764179fc0dcff0db6cec3457139a5a26df53e8` | match `b6077bf8…` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `45e0f6990df6a71d6197a6b981270ae63b79897553595e6a9b05f912ecfb3f63` | match `45e0f699…` |
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` | match `f231930f…` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `88b62427ffb125b509f150279f934a8c0bf151a62e985af070518c1d32f844c5` | match `88b62427…` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` | match `30388dba…` |

17-fixture directory (`tests/acquisition/fixtures/binance_usdm_harmonic_qualification`) unchanged (17 files).

Integration commit:

```
commit f05ee711f5db34421fae7f738aef00917bbdacf5 (HEAD -> main, origin/main)
Author: Jr Dev - Hermes
    CEX-002: integrate listing source acceptance (review 120 accepted)

5 files changed, 1248 insertions(+), 35 deletions(-)
```

`HEAD == origin/main == f05ee711f5db34421fae7f738aef00917bbdacf5`.

## 2. Focused commands

Run in order after the source-integration commit:

1. `python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
   - Exit: 0. pytest report: **205 passed**.
   - Static source invariant verified: `grep -cE "^def test_"` = **186** uniquely named test functions (matches review 120). pytest collects 205 items because 4 functions carry `@parametrize` expansions (186 functions → 205 collected instances); all instances pass. Count invariant satisfies review 120 ("186 uniquely named test functions").
2. `python -m pytest tests/test_download_atomicity.py -q --tb=short`
   - Exit: 0. pytest report: **18 passed**. Static function count: 18. ✓
3. `python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
   - Exit: 0. `All checks passed!`
4. `python3 scripts/check_repo_control.py`
   - Exit: 0. `Repo control check: PASS`
5. `git show --check --oneline --no-renames HEAD`
   - Exit: 0. `f05ee71 …` (no check-whitespace violations).

All five focused commands passed. Sequence proceeds to candidate preconditions.

## 3. Candidate preconditions (before snapshot)

No candidate process running (ps scan: none). Before snapshot captured 2026-08-21T16:17:32Z:

- `HEAD` = `f05ee711f5db34421fae7f738aef00917bbdacf5` / `origin/main` = same.
- plan lock SHA-256 = `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84` (381,855 B) — matches review 115 proved after-state.
- legacy budget ledger SHA-256 = `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6` (777 B) — matches review 115.
- tracked report 62 SHA-256 = `dce2a2396c6b250be928f4cde217ce49419561f958301ad97afbd479b6b39e31` (26,320,909 B), stale mtime 2026-08-20T21:51:03Z (unchanged) — matches review 115.
- raw tree: 186 files / 1,015,198,547 B / digest `41cade46c794cfc8a3a18c3b2bfd5291c30a710652d1146969965d65ac3f943e` — matches review 115.
- amendment-ledger exists = **False** — matches review 115.
- listing checkpoint SHA-256 = `85149715…` (25,039,732 B), entries = 31,131, unclaimed = 0, latest retrieval 2026-08-21T05:02:54Z.
- list_cache: 31,321 files / 3,561,567,568 B / digest `5e01e92b…`.
- fapi_cache: 8 files / 8,619,549 B / digest `d562899b…`.
- coinalyze_cache: 6 files / 1,694,736 B / digest `a1c98904…`.
- retry journal SHA-256 = `ab820ddd…`.
- progress SHA-256 = `332f2d87…`.
- fs available: 179,875,049,472 B.

Immutable invariants (plan lock, budget ledger, amendment-ledger absence, retained raw tree) all match review 115's proved after-state. The existing checkpoint and caches were reused in place; no store reconstruction.

## 4. One measured candidate resume

Secret loaded via `. ./.env` only (never printed / not in argv). Single bounded foreground invocation (50-min `timeout`, SIGTERM + 60s kill-after). Start 2026-08-21T09:19:07-07:00, end 2026-08-21T09:51:50-07:00, elapsed 1,963 s.

```
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --candidate-plan-only
candidate_status=$?
```

Result: **`candidate_status=2`** (terminal evidence — per review 120, status 0 or 2 is terminal; candidate was not invoked again).

Console output (verbatim, essential lines):

```
listing checkpoint bootstrap: claimed=0 checksum_blobs=186 skipped_already_bound=31131 unclaimed=0
Qualification report written to research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
gate_status=BLOCKED accepted=False symbols=1004 blocked=['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']
sample_plan: planned_new_bytes=0 budget=268435456 retained_bytes=805792081 budget_blocked=46
plan_lock: version=2 state=locked plan_digest=d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1 superseded=[0, 1]
budget: charged=0 spent_range=[0,1015198547] remaining=0 reserved=0 legacy_state=legacy_budget_accounting_unresolved breach_state=unresolved
membership: basis=confirmed_perpetual_membership confirmed=771 unresolved=63 classes={'confirmed_perpetual': 771, 'dated_delivery_candidate': 46, 'delivery_non_perpetual': 4, 'settlement_artifact_candidate': 17, 'tradifi_perpetual': 170}
gate2_storage: state=unknown selected_raw_bytes=7833966625 cost_sample_bytes=12522974218 projected_new_bytes=20352428237 available_bytes=177907154944 total_required_bytes=None unknown_components=['normalized_catalog_bytes', 'temporary_high_water_bytes', 'operating_reserve_bytes']
candidate_plan: state=candidate_unmigrated version=3 prior_version=2 plan_digest=0a1c358c8fee3df35d1049424502b11e38c0084592a03ab6f9de99b8a0078593 envelope_digest=0f9d0d6d87c703e56fad71bcf137eaf8e390b44d07f9007ad0b24bca85746cb8 migration_authorized=False download_authorized=False
holdout: id=c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2 boundary_utc=2026-08-21T16:19:08.994166+00:00 stream_collector=False
listing_checkpoint: reused=30172 fetched=9640 unclaimed=0 serializations=39 | workers=8 clients=1/1 retries=22
ERROR: incomplete product matrix is refused | context={'gate_status': 'BLOCKED', 'blocked_products': ['binance_usdm_perpetual_membership', 'binance_usdm_bar_1h', 'binance_usdm_open_interest_5m', 'binance_usdm_funding_realized', 'binance_usdm_funding_indicative_1h', 'binance_usdm_mark_index_basis_1h', 'binance_usdm_cost_calibration']}
CANDIDATE_STATUS=2
CANDIDATE_END=2026-08-21T09:51:50-07:00
CANDIDATE_ELAPSED=1963s
```

### Terminal report (report 62) state captured by the candidate

| Field | Value |
|---|---|
| gate_status | `BLOCKED` |
| accepted | `False` |
| symbols | 1004 |
| blocked_products | 7 (`binance_usdm_perpetual_membership`, `binance_usdm_bar_1h`, `binance_usdm_open_interest_5m`, `binance_usdm_funding_realized`, `binance_usdm_funding_indicative_1h`, `binance_usdm_mark_index_basis_1h`, `binance_usdm_cost_calibration`) |
| membership | basis=`confirmed_perpetual_membership`, confirmed=771, unresolved=63; classes: confirmed_perpetual 771, dated_delivery_candidate 46, delivery_non_perpetual 4, settlement_artifact_candidate 17, tradifi_perpetual 170 |
| plan_lock | version=2, state=`locked`, plan_digest=`d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`, superseded=[0,1] |
| candidate_plan | state=`candidate_unmigrated`, version=3, prior_version=2, plan_digest=`0a1c358c8fee3df35d1049424502b11e38c0084592a03ab6f9de99b8a0078593`, envelope_digest=`0f9d0d6d87c703e56fad71bcf137eaf8e390b44d07f9007ad0b24bca85746cb8` |
| budget | charged=0, spent_range=[0,1015198547], remaining=0, reserved=0, legacy_state=`legacy_budget_accounting_unresolved`, breach_state=`unresolved` |
| gate2_storage | state=`unknown` (not authorized); selected_raw_bytes=7,833,966,625; cost_sample_bytes=12,522,974,218; projected_new_bytes=20,352,428,237; available_bytes=177,907,154,944; total_required_bytes=None; unknown_components=[normalized_catalog_bytes, temporary_high_water_bytes, operating_reserve_bytes] |
| migration_authorized | `False` |
| download_authorized | `False` |
| samples | `[]` (empty) |
| holdout | id=`c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2`, boundary_utc=`2026-08-21T16:19:08.994166+00:00`, stream_collector=False |
| listing_checkpoint reuse | reused=30,172, fetched=9,640, unclaimed=0, serializations=39, workers=8, clients=1/1, retries=22 |

## 5. After snapshot (delta proof)

After snapshot captured 2026-08-21T16:54:40Z (immediate repeat of before snapshot).

### Immutable invariants proved unchanged (match review 115 proved after-state)

| Field | Before | After | Unchanged |
|---|---|---|---|
| plan_lock SHA-256 (`e04a5ce2…`) | `e04a5ce2…` | `e04a5ce2…` | yes |
| plan_lock bytes | 381,855 | 381,855 | yes |
| budget_ledger SHA-256 (`47341a9c…`) | `47341a9c…` | `47341a9c…` | yes |
| amendment_ledger exists | False | False | yes |
| raw tree digest (`41cade46c…`) | `41cade46c…` | `41cade46c…` | yes |
| raw tree file count | 186 | 186 | yes |
| raw tree bytes | 1,015,198,547 | 1,015,198,547 | yes |
| listing unclaimed | 0 | 0 | yes |

### Evolved-by-candidate deltas (expected; candidate-process authorized)

| Field | Before | After | Delta |
|---|---|---|---|
| listing_checkpoint SHA-256 | `85149715…` | `d584e22a…` | changed (candidate serialization) |
| listing_checkpoint bytes | 25,039,732 | 33,206,753 | +8,167,021 |
| listing entries count | 31,131 | 40,771 | +9,640 (matches `fetched=9640`) |
| list_cache file count | 31,321 | 40,961 | +9,640 |
| list_cache bytes | 3,561,567,568 | 5,158,272,575 | +1,596,705,007 |
| fapi_cache file count | 8 | 9 | +1 |
| fapi_cache bytes | 8,619,549 | 9,697,128 | +1,077,579 |
| coinalyze_cache file count | 6 | 7 | +1 |
| coinalyze_cache bytes | 1,694,736 | 3,144,369 | +1,449,633 |
| retry_journal SHA-256 | `ab820ddd…` | `ff4edb03…` | changed (retries recorded) |
| qualification_progress SHA-256 | `332f2d87…` | `d58c7b79…` | changed (candidate advance) |
| report 62 SHA-256 | `dce2a2396…` (stale) | `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691` | **written by candidate (terminal evidence, status 2)** |
| report 62 bytes | 26,320,909 | 1,059,297,547 | ~1.06 GB |
| fs available | 179,875,049,472 | 176,827,457,536 | −3,047,591,936 |

### Proof of no unauthorized mutation

The candidate performed the authorized `--candidate-plan-only` resume only: it advanced the listing/retry/progress state and wrote the BLOCKED terminal report 62 (status 2). It did **not**:
- perform plan migration (`migration_authorized=False`, `candidate_plan.state=candidate_unmigrated`);
- perform sample download (`download_authorized=False`, `samples=[]`);
- create an amendment-ledger (still absent);
- advance Gate 2 (`gate2_storage.state=unknown`, not authorized);
- normalize / publish catalog / run Nautilus / Harmonic Trader / payoff analysis / PAPER / LIVE / other-ticket work.

## 6. Stop point / disposition

Stop point: review 120's one measured candidate resume completed with `candidate_status=2` (terminal evidence, BLOCKED). No second invocation is authorized.

CEX-002 remains `IN_PROGRESS`; Gate 1 has NOT passed (gate_status=BLOCKED). Plan migration, sample acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every other ticket remain unauthorized.

Terminal evidence: report 62 at SHA-256 `46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691` (1,059,297,547 B ≈ 1.06 GB), mtime 2026-08-21T16:51:47Z, on disk at `data/cex002_qualify` / written by the candidate to `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`.

## 7. Explicit no-op statement

No migration, sample download, amendment-ledger creation, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, database-sidecar migration, or other-ticket work occurred in this session. The only artifacts written by the candidate are the authorized listing/checkpoint retry/progress/cache growth and the BLOCKED terminal report 62 (status 2). Data files, checkpoints, caches, progress, journal, and unrelated dirty DEX/BitMEX paths are left uncommitted on disk.

## 8. Publication disposition (reviewer decision required for report 62)

Review 120 authorizes staging report 62 when its bytes changed through the authorized candidate process. They did (26,320,909 B → 1,059,297,547 B ≈ 1.06 GB; the candidate, on `status=2`, emitted the complete terminal report including the full 771-symbol `confirmed_perpetual` class, the 40,771-entry listing, storage projections, and Coinalyze mapping — causing the bloat).

However, the commit that staged all four publication paths (this record 121, the two control files, and report 62) was **rejected by the remote**:

```
remote: File research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json is 1010.22 MB;
remote: this exceeds GitHub's file size limit of 100.00 MB   (GH001)
```

GitHub enforces a hard 100 MB per-blob limit with no server override. The repository has no `.gitattributes` and is not git-lfs enabled; the prior ~26 MB report 62 was below the limit and was committed to origin/main, confirming plain git is the intended mechanism. A 1.06 GB blob therefore **cannot** be pushed under the current repo configuration.

Hermes cannot resolve this unilaterally, because the alternatives each cross into reviewer-gated territory:

- Introducing git-lfs (or a `lfs` smudge/filter) is a repository-wide source-authority / architecture change requiring an ADR (docs/adr) and reviewer authorization before it may touch a committed artifact; Hermes is prohibited from making source-authority or architecture decisions.
- Down-streaming / truncating financial evidence is a financial-semantics / source-authority decision (Gate 1 terminal report integrity) reserved to the reviewer.
- Selecting a different on-disk representation or relocating 62 to a non-tracked artifact changes the source-authority layout and is likewise reviewer-gated.

**Disposition taken:** the failed local publication commit was reset. Only the pushable, small-text publication paths were committed and pushed to origin/main:

- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`; and
- `research/sprint_004/121_CEX002_LISTING_INTEGRATION_AND_CANDIDATE_RESUME.md` (this record, including section 6's terminal-evidence identity for 62).

The 1.06 GB report 62 (SHA-256 `46d1980ec…`, mtime 2026-08-21T16:51:47Z) remains on disk at `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` and is intentionally left **uncommitted** so it does not block the pushable evidence. `git status` shows it as a working-tree modification (`M`), preserved for the reviewer.

**Reviewer choices (not executed by Hermes):**
1. Authorize git-lfs (with ADR-0018/ADR-0019 amendment) and re-stage 62 so its terminal evidence enters repo history; or
2. Authorize relocation of 62 to a non-tracked artifact store and record its identity here as an out-of-repo reference; or
3. Authorize an alternative on-disk report representation (streamed/rolled-up) that remains under the 100 MB limit — which would require rerunning the candidate with the alternate writer (a candidate-reexecute decision, reviewer-gated); or
4. Accept 62 as on-disk-only terminal evidence without repo publication (no repo commit).

Hermes will not act further on 62 until the reviewer selects one. This record 121 is the stop point; next ticket remains `NONE`.
