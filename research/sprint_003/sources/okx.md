# Source note — OKX

**Role:** BACKFILL_PRIMARY_CANDIDATE (spot) / COST_CALIBRATION (funding, L2) / REFERENCE_METADATA (instruments)
**Audit date:** 2026-07-18

## Samples acquired
- Spot trades `BTC-USDT`: 20 rows, sha 8e1a7579…; fields instId,side,sz,px,tradeId,ts.
- SWAP funding history `BTC-USDT-SWAP`: 5 rows, sha c8b15b7b…; fields formulaType, fundingRate, fundingTime, realizedRate.
- L2 book `BTC-USDT` sz=5: sha 8f63e5fdb…; asks/bids/ts/action; 5 levels each side.
- Instruments SWAP `BTC-USDT-SWAP`: sha 1ad06f4d…; ctType=linear, ctVal=0.01 BTC, state=live.
- Instruments SWAP list (limit=10): 427 rows, sha f1852c72…; pagination via instType+limit.

## Schema / semantics
- Trades: ms-epoch `ts`. Funding: ms-epoch `fundingTime`; `formulaType` present (e.g.
  "withRate") — **capture per row**, funding formula has changed over time.
- Instruments: `ctType` (linear/inverse), `ctVal`, `ctValCcy`, `state`. Linear SWAP ctVal
  = 0.01 BTC per contract; sz is in contracts.

## Timestamp precision
Millisecond epoch UTC.

## Correction / revision
Funding `formulaType` and interval have dated changes (OKX docs). Store the formula/interval
effective at each `fundingTime`; do not assume the current formula applied historically.

## Licensing
Public market/instruments endpoints usable for research; review OKX API terms for
redistribution.

## Gaps
- Exact effective dates of past funding-formula/interval changes not pulled (Open Q4).
- L2 sample is bounded calibration only, not full depth history.
