# CURRENT_TASK

Ticket: UNIVERSE-002
State: ACCEPTED
Next required actor: Sr Engineer (Weak Model) — record review and next-ticket selection
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Authorization):**
We have successfully completed the original implementation sequence (#1 through #24), culminating in the Prospective Holdout evaluation engine. 

Before we move into execution (Sequence #25: Paper Execution Runtime), we must close the remaining gap in our universe definition: the DEX side. UNIVERSE-001 gave us CEX bars, and UNIVERSE-003 gave us the historical CEX dead-coin backfill. We now need the forward-looking DEX new-listing event stream.

I have reviewed the constraints on **UNIVERSE-002** (Birdeye DEX New-Listing Event Feed). 
1. Licensing/ToS is acceptable for internal research storage.
2. We accept that this is forward-only (from ingestion start) and does NOT contain delistings/deaths (meaning it is not survivorship-free). 
3. The CU budget (30k/mo) is strict: the implementation must NEVER attempt to fetch OHLCV bars.

I am formally authorizing **UNIVERSE-002**. I have also updated the `IMPLEMENTATION_SEQUENCE.md` to append the **Execution** phase (Step #25: Paper execution runtime).

## Governing documents

- tickets/UNIVERSE-002.md (READY)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/universe/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/universe tests/universe
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/universe tests/universe
4. python3 scripts/check_repo_control.py
5. Test asserting no OHLCV/bar endpoint is ever constructed by this module.
