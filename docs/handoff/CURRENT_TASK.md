# CURRENT_TASK

Ticket: FUND-005
State: AWAITING_REVIEW
Next required actor: Lead Quant (Reviewer) — review BitMEX funding cashflow provider
Next ticket authorized: NONE

**Reviewer Decision (Architecture & Ticket Selection):**

I have reviewed the `FUND-004` source sweep and validation findings. 

**Decision: PRAGMATIC ACCEPTANCE**
- **BitMEX Funding:** Accepted as the primary pragmatic source. Its clear G01/G02 semantics (documented timestamp=settlement, clear formula) exceed the quality of Binance/OKX data. The 2016+ history provides deep coverage for BTC/ETH.
- **Quote FX (USDT=USD):** Accepted. The on-chain DEX validation (within 1% of peg 99.4% of days) is sufficient for Aware-level research implementation without requiring a massive tick-level DEX reconciliation engine. Inverse contracts (XBTUSD) will convert their base-currency funding payouts to quote-currency using the matching point-in-time price bar.

With these decisions locked, we can now complete Step #10 (Funding, fees, quote FX) by ingesting the data.

I am authorizing **FUND-005** (BitMEX Funding Cashflow Provider).

## Governing documents

- tickets/FUND-005.md (READY)
- tickets/FUND-004.md (ACCEPTED)
- docs/handoff/IMPLEMENTATION_SEQUENCE.md

## Acceptance (Jr)

1. .venv/bin/python -m pytest tests/ingest/ tests/market/ -q --tb=short
2. .venv/bin/python -m ruff check src/cryptofactors/ingest/bitmex_funding.py
3. .venv/bin/python -m mypy --no-error-summary src/cryptofactors/ingest/bitmex_funding.py
4. python3 scripts/check_repo_control.py
