# BIN-001 — Sr REVIEW-0020 remediation drop

**Status:** Ready for Jr integration and test coverage  
**Production file (already in tree):** `src/cryptofactors/ingest/binance.py`  
**Transform version:** `3`  
**Schema version:** `2` (new identity + fingerprint; not reused from v1)  
**Governing reviews:**  
- `docs/reviews/REVIEW-0020_BIN-001_CHANGES_REQUIRED.md` (current disposition)  
- `docs/reviews/REVIEW-0019_BIN-001_CHANGES_REQUIRED.md` (defect history)  
**Ticket:** `tickets/BIN-001.md`  
**Migration:** none  

Sr Dev — Grok Build source-only drop. No tests, Git, commits, pushes, or
acceptance runs by Sr. Jr Dev — Hermes owns everything below.

## Code changes (already in production file)

1. **Cross-object duplicate/gap assessment (REVIEW-0020 #1).**  
   After per-object parse, the complete multi-object bar sequence is assessed.  
   Cross-object gaps and duplicates emit `binance_kline_gap` /  
   `binance_kline_duplicate_open_time` with `scope=cross_object` and  
   `prev_raw_object_id` / `next_raw_object_id` (or first/duplicate object ids).  
   Issues are routed into the relevant per-object quality partitions (lineage  
   retained). Within-object detection still runs with `scope=within_object`.  
   Gap arithmetic uses unit-independent UTC microseconds.

2. **Empty / header-only fail closed (REVIEW-0020 #2).**  
   Zero typed bars after processing an archive emits  
   `binance_kline_empty_observations` (ERROR) → quality REJECTED.  
   No silent PASS on empty or header-only CSVs.

3. **Per-row timestamp unit normalization (REVIEW-0020 #3).**  
   Each row is converted with **its own** detected unit (`ms`/`us`/`s`), never  
   the object's first-row unit. Mixed units still reject the object via  
   `binance_kline_mixed_timestamp_unit` while preserving per-row UTC fields.  
   Invalid/out-of-range times surface as `binance_kline_invalid_timestamp`  
   (coverage conversion failures are not swallowed).

4. **Market-physical volume fields (REVIEW-0020 #4).**  
   - **spot / usdm:** `volume`, `quote_volume`, `taker_buy_base_volume`,  
     `taker_buy_quote_volume`.  
   - **coinm:** `volume` (contracts), `base_asset_volume`, `taker_buy_volume`  
     (contracts), `taker_buy_base_asset_volume` — physical names match COIN-M  
     meaning; no contradictory `quote_volume` label.  
   Partition + quality_summary carry volume unit metadata and  
   `schema_variant` (`quote_notional` | `coin_margined`).  
   Unknown market types still raise `ValueError`.

5. **Schema identity versioned (REVIEW-0020 #5).**  
   `BINANCE_KLINE_SCHEMA_VERSION = "2"` with a stable  
   `SchemaIdentity.fingerprint` derived from material field layout + market  
   variant. Transform version bumped to `"3"`.

## Behavior Jr must encode in tests

| Case | Expectation |
|------|-------------|
| Cross-object gap | Two raw objects, adjacent opens non-contiguous → `binance_kline_gap` with `scope=cross_object` / `cross_object=True` |
| Cross-object duplicate | Same open_time in two objects → `binance_kline_duplicate_open_time` spanning objects |
| Empty CSV zip | `binance_kline_empty_observations`; quality REJECTED |
| Header-only CSV | same empty-observations failure |
| Mixed ms/us rows | each row's `open_time` UTC-us correct for **its** unit; mixed-unit ERROR present |
| Coverage bounds | valid min/max event times; invalid timestamps → `binance_kline_invalid_timestamp`, not silent omit |
| COIN-M columns | parquet has `base_asset_volume` / `taker_buy_volume` / `taker_buy_base_asset_volume` (not mislabeled quote_*) |
| Spot/USD-M columns | `quote_volume` / `taker_buy_base_volume` / `taker_buy_quote_volume` |
| Schema identity | `publish_plan.schema.version == "2"` and non-null fingerprint |
| Prior REVIEW-0019 cases | inclusive close ms/us; exclusive mismatch; within-object dup/gap; malformed first row; calendar `1M` month-end/leap; lineage; local-only; full two-output MAN-001 **publication** of returned plan (bars + quality) |

## Jr work (see `tickets/BIN-001.md` and `docs/handoff/CURRENT_TASK.md`)

1. Confirm `src/cryptofactors/ingest/binance.py` is the REVIEW-0020 drop  
   (transform `"3"`, schema version `"2"`, cross-object gap path, empty fail-closed,  
   per-row unit conversion, coinm physical fields).
2. Integrate in-tree without independent production source changes.
3. Extend `tests/ingest/market/test_binance_kline.py` for every finding above  
   and the omitted REVIEW-0019 cases listed in REVIEW-0020.
4. Run every ticket acceptance command and `python3 scripts/check_repo_control.py`.
5. Correct `docs/reviews/BIN-001_CHANGE_REPORT.md`: accurate integration commit  
   hash, behavioral claims (including cross-object gaps), real test counts,  
   this Sr drop reference.
6. Commit and push per Hermes duties.
7. **Stop for reviewer inspection.** Do not begin BAR-001.  
   `Next ticket authorized: NONE`.

## Out of scope for this drop

- Migrations, architecture docs, ADR changes  
- Canonical bar promotion (BAR-001)  
- Network access in the normalizer  
- Sr Git / commit / push / acceptance execution  
- Independent Jr edits to production source  
