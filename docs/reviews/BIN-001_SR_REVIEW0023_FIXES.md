# BIN-001 — Sr REVIEW-0023 remediation drop

**Status:** Ready for Jr integration and test coverage  
**Production file (already in tree):** `src/cryptofactors/ingest/binance.py`  
**Transform version:** `4`  
**Schema version:** `2` (unchanged material bar layout from v3)  
**Governing review:** `docs/reviews/REVIEW-0023_BIN-001_CHANGES_REQUIRED.md`  
**Ticket:** `tickets/BIN-001.md`  
**Migration:** none  

Sr Dev — Grok Build source-only drop. No tests, Git, commits, pushes, or
acceptance runs by Sr. Jr Dev — Hermes owns everything below.

## Code changes (already in production file)

1. **MAN-001-valid `config_sha256` (REVIEW-0023 production blocker).**  
   - Never emits an empty config hash.  
   - When the caller supplies `config_sha256`, it must be a 64-char lowercase  
     hex digest (validated; raised as `ValueError` otherwise).  
   - When omitted / empty, derive a **deterministic** SHA-256 over identity-bearing  
     normalization configuration (market, interval, venue, instrument, schema  
     identity, transform identity, volume units, close-time convention, etc.).  
   - Returned plan always has `ConfigIdentity(config_sha256=<64-hex>)`.

2. **Required immutable `code_commit` (REVIEW-0023).**  
   - `code_commit` is a **required** keyword argument (no default).  
   - Empty and the placeholder `"unknown"` are rejected with `ValueError`.  
   - The normalizer does **not** invoke Git or infer repository state.  
   - Caller must supply a non-empty immutable code identity.

3. **Transform version** bumped to `"4"` for this identity fix. Accepted v3  
   bar/quality semantics (inclusive close, per-row units, cross-object gaps,  
   market-physical fields, empty fail-closed, row counters) are preserved.

## API change for callers / tests

```python
normalize_binance_kline(
    raw_objects,
    market_type=...,
    interval=...,
    venue_id=...,
    instrument_id=...,
    output_dir=...,
    code_commit="<non-empty immutable identity>",  # REQUIRED
    config_sha256=None,  # optional; derived when omitted
)
```

Existing helpers that omit `code_commit` must pass one (e.g. a fixed test commit
string or a real 40-char hex). Do not pass `"unknown"`.

## Jr work (see `tickets/BIN-001.md` and `docs/handoff/CURRENT_TASK.md`)

1. Confirm production file is transform `"4"` with required `code_commit` and  
   non-empty config hash derivation/validation.
2. Integrate in-tree **without independent production source edits**.
3. Update all `normalize_binance_kline` call sites in  
   `tests/ingest/market/test_binance_kline.py` to pass a valid `code_commit`.
4. Replace the broad `pytest.raises(Exception)` publication test with a  
   **successful** `DatasetPublisher.publish` that covers both bar and quality  
   outputs and catalog registration. Pass explicit valid code/config identity  
   where required (or rely on derived config hash + supplied code_commit).
5. Correct remaining Jr evidence defects from REVIEW-0023:
   - monthly fixtures: true calendar inclusive close; no interval-mismatch  
     masquerading as month success; fix leap-year naming  
   - assert market-specific **physical CSV values** in the correct columns  
   - assert exact `CoverageWindow` UTC instants for valid rows  
   - record actual `test_*` count and real immutable Git hash (no constructed  
     pending values)
6. Run every ticket-exact acceptance gate.
7. Update `docs/reviews/BIN-001_CHANGE_REPORT.md` to match only demonstrated  
   behavior, this Sr drop, real counts, and real commit hash.
8. Commit and push per Hermes duties.
9. **Stop for reviewer inspection.** Do not begin BAR-001.  
   `Next ticket authorized: NONE`.

## Out of scope for this drop

- Migrations, architecture docs, ADR changes  
- Canonical bar promotion (BAR-001)  
- Sr Git / commit / push / acceptance execution  
- Independent Jr edits to production source  
