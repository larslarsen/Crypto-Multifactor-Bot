# REVIEW-0225 — ARCH-003 Changes Required

## Verdict

**CHANGES REQUIRED**

Code review is complete. ARCH-003 requires Sr Dev Grok Build corrections before
acceptance. No production files were changed and no tests were run as part of this
review.

## Required Handoff

- **Ticket:** ARCH-003
- **Next required actor:** Sr Dev — Grok Build
- **Next ticket authorized:** NONE
- **ADR-0015:** Not accepted
- **ARCH-003:** Not complete

## Required Sr Dev Corrections

1. `seed_identity_catalog.py:22,150-188`: delete the shared 2020 proxy. Accept
   per-symbol evidence and skip missing symbols using each proxy's event time,
   availability time, and source evidence.
2. Add migration 0011 creating stable
   `ref_venue_listing(listing_id, venue_id, instrument_id, venue_symbol)` and make
   lifecycle events reference `listing_id`.
3. In `listing_universe.py:54-77`, filter lifecycle events by `known_from_us` and
   `known_to_us` before selecting an event.
4. Replace all 12 entrypoints using `load_paper_universe_binding` with a pinned
   `load_universe_binding(db_path, store_root, args.universe_dataset_id)` call.
5. In `daily_refresh.py:511-604`, delete mutable symbol-registry writes and the
   Birdeye network block; dry-run must make no network calls and refresh instruments
   from the published listing universe.
6. In `backfill_binance_klines.py:251`, persist the acquisition's last complete
   event end rather than the requested end time.
7. In `birdeye_screen_queue.py:331-343,395-422`, rename counting functions so they
   do not claim registration and preserve Solana address case.
8. In `market/bars.py:215-235`, read partition `instrument_id` when present,
   otherwise read `quality_summary["instrument_id"]`.
9. In `publish_listing_universe.py:79`, require `--code-commit` instead of using
   `CodeIdentity(commit="ARCH-003")`.

## Verification

- Production source modified: **No**
- Tests run: **No**
- Acceptance granted: **No**
