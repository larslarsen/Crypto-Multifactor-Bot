# CEX-002 Gate 1 Stable-Authority Execution Record

Date: 2026-08-20

Actor: Jr Dev — Hermes

Ticket: CEX-002, Gate 1 source procurement

## Outcome

**COMMANDS 1–5 PASSED. BOTH REAL RUNS COMPLETED. GATE 1 REMAINS BLOCKED WITH A
SEMANTIC-IDENTITY ASSERTION FAILURE ON A SINGLE VOLATILE DISK-CAPACITY NOTE.**

The semantic resume identity assertion did not print `PASS`: the two reports differ in
exactly one field after `drop_identity_volatility` — the human-readable
`incidents[18].note` text, which embeds a `df`-derived local free-space figure that
legitimately drifted between the two runs. Every identity-critical component (plan
digest, budget, membership, product matrix, samples, storage shortfall class, listings,
resume state) is byte-identical. The reviewer must disposition the volatile-capacity
note.

## Reviewed identities (verified before execution)

Committed control-plane base: `HEAD == origin/main == 85bc0e47ab0a6847327f0bcfcf6d842e972f162f`.

All nine reviewed-path SHA-256 values matched review 87 exactly before the run:

| Path | Expected (review 87) | Observed |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `7e60ed28d56a32b1722d9c6016ff059c188dfed71481aa5865ca367767d14150` | match |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `578f45e2be6f4428cc73560daacb31a305f72501f26f4ea2cd2c718a444fc64b` | match |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `8076ea28b2f4c69e434afe60e7132f922eb2d322649365782117709b2260131f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `9388b67710c51ce0a4219c2e23d57c804d01f4a54b08b340dff1e9bdbb414ed0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` | match |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` | match |

## Command sequence (review 87 order) — all PASSED

### 1. Focused CEX-002 suite — PASS, exit 0
`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
144 collected, 144 passed.

### 2. Atomic-download suite — PASS, exit 0
`.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
11 collected, 11 passed.

### 3. Ruff — PASS, exit 0
`.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py`
`All checks passed!`

### 4. Repo control — PASS, exit 0
`python3 scripts/check_repo_control.py`
`Repo control check: PASS`

### 5. Whitespace check — PASS, exit 0
`git show --check --oneline --no-renames HEAD`
No whitespace errors.

## Bounded real execution

Both runs used the preserved `data/cex002_qualify` store (not deleted, renamed,
replaced, reconstructed, or relocked). The API key was loaded only from `.env` into the
environment and never printed or placed in a command argument. No source, test, or
fixture path was edited.

### First run — BLOCKED (exit 2 semantics), 665 s

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_stable_first.json'
```

Report: `/tmp/cex002_gate1_stable_first.json`
SHA-256: `15a86f8e275a3321dded5fb34c500755b3cb7478f1f56b7b0d9848922b75a5a6`
Bytes: 26,181,351. Terminal state: `ERROR: incomplete product matrix is refused`,
`gate_status=BLOCKED`. This matches the exit-2 blocked-matrix path already mapped in
execution record 74; the raw exit status was not preserved by the detached launch.

### Second run — BLOCKED (exit 2 semantics), 612 s

```
/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json'
```

Report: `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`
SHA-256: `ca9bb5f1bc10d74fb0c983af790074d0b6f724a26eeef5dbff6b6eb804822e42`
Bytes: 26,181,351. Terminal state identical: BLOCKED matrix refusal.

### Semantic resume identity assertion — FAILED (AssertionError), ~1 s

```
.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_stable_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'
```

AssertionError. A full recursive diff of `drop_identity_volatility(a)` vs
`drop_identity_volatility(b)` yields exactly ONE differing path:

- `incidents[18].note`:
  - run 1: `...exceeds local capacity by 8473465920090 bytes; Gate 2 remains blocked`
  - run 2: `...exceeds local capacity by 8473541003866 bytes; Gate 2 remains blocked`

The delta of 75,083,776 bytes equals the delta in the `df`-derived
`storage.available_bytes` between the runs (187,730,092,032 → 187,655,008,256), i.e. the
local free-space figure captured in the human-readable Gate-2 shortfall note. This is a
volatile, execution-environment value embedded in an otherwise stable incident note; it
is not a plan, membership, matrix, sample, listing, ledger, or coverage identity
component.

## Exact metrics

### Membership

basis `confirmed_perpetual_membership`, confirmed=771, unresolved=63, class counts:
`confirmed_perpetual` 771, `dated_delivery_candidate` 46, `delivery_non_perpetual` 4,
`settlement_artifact_candidate` 17, `tradifi_perpetual` 170. Universe source
`official_vision_union_listing_with_evidence_based_perpetual_membership`,
discovered_symbols=1004.

### Blocking candidates

9 blocked products:
`binance_usdm_perpetual_membership`, `binance_usdm_trade`, `binance_usdm_bar_1m`,
`binance_usdm_open_interest_5m`, `binance_usdm_funding_realized`,
`binance_usdm_funding_indicative`, `binance_usdm_mark_index_basis`,
`binance_usdm_liquidation_observed`, `binance_usdm_cost_calibration`.
`accepted=False`, `gate_status=BLOCKED`.

### Plan

plan_lock version=1, state=locked, plan_digest
`d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`, superseded=[0].
Progress: `physical_families_inventoried`=20, `progress_objects`=278,
`recovered_samples`=0, `reused_samples`=100, `unverified_retained_sample_keys`=0,
`rehash_required`=true.

### Ledger

`cex002_budget_ledger.json`: version=1, charges={}, reservations={}, charge_count=0,
charged_bytes=0, reservation_count=0, transferred_total_bytes=0, planned_total_bytes=0,
integrity state_sha256 `172dd7d3ac9659754f1e6d8f9c5f7053dc096f1b6299d8518c9d5ba18ee991b6`.
Legacy: legacy_max_bytes=1,015,198,547, legacy_state=legacy_budget_accounting_unresolved,
legacy range spent [0, 1,015,198,547], remaining=0, reserved=0, breach_state=unresolved.

### Transferred / no-transfer charges

0 transfers this run (charged=0, transferred_total_bytes=0). All 100 planned samples
reused existing retained objects (`reused_existing=True` for 100/100); no new object was
fetched. Budget bytes 268,435,456; budget_remaining_bytes=0; sample_budget_blocked
allowance_bytes=0 (91 `sample_budget_exceeded` incidents).

### Physical storage

state=insufficient. required_bytes=8,662,211,210,669;
projected_new_bytes=8,661,196,012,122. Run 1: available_bytes=187,730,092,032,
shortfall_bytes=8,473,465,920,090. Run 2: available_bytes=187,655,008,256,
shortfall_bytes=8,473,541,003,866. Shortfall class (insufficient) identical both runs.

Per-product listing totals (run 1, byte-identical run 2):
bar_1m 709,650 objects / 61,196,652,414 B; cost_calibration 584,222 / 2,448,204,498,577;
funding_indicative 660,936 / 28,705,337,062; funding_realized 21,425 / 21,645,197;
mark_index_basis 2,067,175 / 99,853,687,857; open_interest_5m 595,471 / 6,291,378,762;
perpetual_membership 771 / 6,628,196,148,904; trade 1,297,467 / 6,174,436,174,147.
Confirmed-universe totals object counts: bar_1m 689,448; cost_calibration 565,558;
funding_indicative 650,389; funding_realized 21,035; mark_index_basis 2,015,312;
open_interest_5m 573,788; perpetual_membership 771; trade 1,257,920.

### Per-product source and coverage states

- `binance_usdm_perpetual_membership`: membership_unresolved / unresolved_membership / authority membership_unresolved; listed 771 objects, 6,628,196,148,904 B; 87 samples planned.
- `binance_usdm_trade`: official_qualified / unresolved_membership / official; 1,297,467 objects, 6,174,436,174,147 B; 27 samples.
- `binance_usdm_bar_1m`: official_qualified / unresolved_membership / official; 709,650 objects, 61,196,652,414 B; 14 samples.
- `binance_usdm_open_interest_5m`: official_qualified / unresolved_membership / official; 595,471 objects, 6,291,378,762 B; 7 samples.
- `binance_usdm_funding_realized`: official_qualified / unresolved_membership / official; 21,425 objects, 21,645,197 B; 7 samples.
- `binance_usdm_funding_indicative`: official_qualified / unresolved_membership / official; 660,936 objects, 28,705,337,062 B; 14 samples.
- `binance_usdm_mark_index_basis`: official_qualified / unresolved_membership / official; 2,067,175 objects, 99,853,687,857 B; 42 samples.
- `binance_usdm_liquidation_observed`: inaccessible / blocking_gaps / authority inaccessible; 0 objects, 0 B; 0 samples; typed_gap_symbols empty, coverage_gap_kinds empty.
- `binance_usdm_cost_calibration`: official_qualified / unresolved_membership / official; 584,222 objects, 2,448,204,498,577 B; 3 samples.

Derived-excluded products (`coverage_gap`, `harmonic_bundle`) are `derived_excluded`, not
source-gate members. Blocking condition: the `binance_usdm_perpetual_membership`
unresolved membership and `binance_usdm_liquidation_observed` inaccessible source keep
the matrix incomplete.

### Samples and listings

100 planned samples: 28 early, 29 middle, 29 recent, 14 delisted; per product
mark_index_basis 28, bar_1m 14, funding_indicative 14, perpetual_membership 14,
trade 13, funding_realized 7, open_interest_5m 7, cost_calibration 3. All 100 reused
retained objects. Listing checkpoint: reused=39,805, fetched=0, unclaimed=0, retries=0.
Retry: attempts=2, base_delay_s=0.5, jitter_ratio=0.25, max_attempts=5, max_delay_s=30,
retries=0, incidents=[].

### Coinalyze evidence

key_present=true, qualified=false, anchor_symbols=[BTCUSDT, ETHUSDT]. Reason:
`Coinalyze market symbol disagrees with its native identity | context={'native':
'AAVEUSD_PERP', 'provider_symbol': 'AAVEUSD_PERP.A', 'expected': 'AAVEUSD_PERP_PERP.A'}`.
This provider-identity mismatch is a reported Coinalyze error incident.

### Metadata / progress / checkpoint identities (after run 2)

- `cex002_listing_checkpoint.json`: `018dcb22a786ebcd9460984e2353f51e62d7992eff821f8e2696a398c1319488`
- `cex002_qualification_progress.json`: `fc22da588813c10c7989e32ff5188a209880d5e4b2f911054ad47a31600ca97b`
- `cex002_sample_plan.json`: `02752b25d9fcfb1b9e4602bde23c8847f870578218e882213b56290b94704c12`
- `cex002_retry_journal.json`: `ab820dddceca958779b0b4d514fa48f58aa23de1923e0fde88314aa45922d404`
- `cex002_budget_ledger.json` integrity state_sha256: `172dd7d3ac9659754f1e6d8f9c5f7053dc096f1b6299d8518c9d5ba18ee991b6`
- `cex002_official_contract_metadata.json`: present, 97,689 B, mtime 13:14.

### Retained store

`data/cex002_qualify` retained size: 4,437,664,326 bytes (≈4.13 GiB). Preserved in place.

## Publication

- `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` next-required-actor set to
  `Lead Quantitative Finance Researcher/Engineer - inspect Gate 1 stable-authority execution`.
- Published records: `research/sprint_004/88_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`
  and `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` (the new second-run
  report). No source, test, fixture, data, or unrelated dirty path is staged.
- `HEAD == origin/main` established; Hermes stops here.

## Integrity assertions

- No secret value appears in this record or the reports; the API key was never printed.
- The store was not deleted, renamed, replaced, reconstructed, or relocked.
- No source/test/fixture path was modified, staged, committed, or pushed.
- Exit codes for the two real runs are mapped from the terminal `gate_status=BLOCKED`
  refusal and the CLI's previously recorded exit-2 behavior (record 74); the detached
  launcher did not preserve raw exit statuses.

## Consequence

Gate 1 remains honestly BLOCKED with a complete evidence base. The single divergence in
the semantic-identity assertion is a volatile disk-capacity figure inside one incident
note; all identity-critical state is stable across the two runs. The reviewer must
disposition the volatile-capacity note (e.g. exclude the `df`-derived figure from the
compared note, or record it as a non-identity incidental) and the underlying Gate 1
blockers (unresolved membership, inaccessible liquidation source, sample-budget
exhaustion, storage shortfall) before any further execution.