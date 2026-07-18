# Source note — OKX (CORRECTION: historical host unreachable)

**Role:** BACKFILL_PRIMARY (CONDITIONAL — host unreachable) + INCREMENTAL_PRIMARY (REST OK)
**Audit date:** 2026-07-18 (correction pass)

## Historical files — ACCESS GAP
- The OKX historical download host (`bulk-data-download.okx.com`) does **NOT resolve** from
  this environment (DNS failure, 2026-07-18). Historical trade/funding/L2 files are
  therefore `CONDITIONAL` pending access from a resolvable host.
- The first pass substituted live `/market/trades` and `/market/books` for historical-source
  qualification. That was wrong: those are live snapshots with no coverage dates. Retained
  only as incremental samples (SRC-004b).

## Live REST (incremental, retained, valid)
- Trades `BTC-USDT`: 20 rows, sha 8e1a7579…; fields instId,side,sz,px,tradeId,ts.
- Funding history `BTC-USDT-SWAP`: 5 rows, sha c8b15b7b…; fields formulaType,fundingRate,fundingTime,realizedRate.
- L2 book `BTC-USDT` sz=5: sha 8f63e5fdb…; asks/bids/ts/action.
- Instruments SWAP: sha f1852c72… (427 instruments); ctType=linear, ctVal=0.01 BTC, state=live.

## Expected historical-file schema (NOT verified — host unreachable)
- Gzipped CSV per day. Trades: instId,side,sz,px,tradeId,ts. Funding: instId,fundingRate,
  fundingTime,formulaType. L2: bids/asks/ts.
- `formulaType` and funding interval have dated changes (OKX docs); capture the formula in
  force at each `fundingTime` — do not project the current formula backward.
- Linear SWAP `ctVal`=0.01 BTC; size in contracts.

## Required before promotion (CONDITIONAL)
1. Acquire from a host where `bulk-data-download.okx.com` (or its current equivalent) resolves.
2. Verify historical file layout, compression, schema, timestamp/sequence fields, coverage dates.
3. Confirm contract units, funding formula/interval fields, correction/replacement behavior, terms.

## Licensing
- Public market/instruments endpoints usable for research; review OKX API terms.
