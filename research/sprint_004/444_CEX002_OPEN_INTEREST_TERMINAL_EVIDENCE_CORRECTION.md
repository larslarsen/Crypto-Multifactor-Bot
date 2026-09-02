# CEX-002 Record 444 — Open Interest Terminal Evidence Correction

- **Date:** 2026-09-02
- **Actor:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Runner:** `/tmp/cex002_oi_437_XAHLxl` (shell PID 1088968, Python PID 1089049)
- **Decision:** record-only evidence correction — Review 443 reject Record 442 as written
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Timestamp and runtime correction

Record 442 mislabeled the descriptor filesystem mtime `2026-09-01 17:48:46.152177890 -0700` as `2026-09-01 17:48:46Z`. The correct UTC conversion is `2026-09-02T00:48:46.152177890Z`. Against the recorded start `2026-09-01T21:26:20Z`, the elapsed wall time is approximately 3 hours 22 minutes 26 seconds, not approximately 65 minutes.

- Exact local mtime: `2026-09-01 17:48:46.152177890 -0700`
- Exact UTC conversion: `2026-09-02T00:48:46.152177890Z`
- Recorded start UTC: `2026-09-01T21:26:20Z`
- Correct elapsed wall time: approximately 3 hours 22 minutes 26 seconds

## Precise absence of terminal status

The Review-437 supervisor produced no durable terminal-status record. The corrected evidence distinguishes descriptor publication plus absent process identities from an unavailable supervisor exit status. No exit code, end timestamp, or terminal status was written by the runner. Terminal state is inferred from:

- The completion descriptor exists at `data/.cex002_open_interest_5m/.complete/bb089fc992326c66ddb65cea03dda92e8cd9fcf7cb7f373821f04a16db9168e4.json`
- Descriptor mtime UTC: `2026-09-02T00:48:46.152177890Z`
- Both shell PID 1088968 and Python PID 1089049 are absent from `/proc`
- No normalize process remains

## Lineage aggregate proof

All 19,744 descriptor-referenced lineage documents were scanned. The exact aggregate counts for the accepted identical-repeat and spillover fields prove they equal 75,255 and 2,818 respectively:

| Field | Aggregate count | Descriptor total | Match |
| --- | --- | --- | --- |
| collapsed_identical_source_rows | 75,255 | 75,255 | ✓ |
| excluded_source_rows | 2,818 | 2,818 | ✓ |

Lineage documents containing collapsed_identical_source_rows: 9
Lineage documents containing excluded_source_rows: 227
Parse errors: 0

## Preservation proof for all 181 pre-existing artifact pairs

All 181 partition/lineage pairs published before the Review-437 start (2026-09-01T21:26:20Z) were verified:

- Pre-cutoff lineage files: 181
- Pre-cutoff parquet files: 181
- All 181 lineage content digests match their filenames ✓
- All 181 parquet content digests match their filenames ✓
- Total content digests verified: 362

Aggregate digest of all 362 sorted content digests (181 lineage + 181 parquet):
`c88a346d3118b54006217ba1dcf422ad0f836b6ab18ddf4de1d11fff8665f57b`

This aggregate proves all 181 pre-existing artifact pairs remain unchanged and descriptor-referenced, with each current content digest equaling its content-addressed filename.

## Twelve-month 0GUSDT statement correction

The prior Record 442 described twelve 0GUSDT partitions as "calendar-length-consistent" despite partial boundary months. This record corrects that statement to coverage-boundary language: the 0GUSDT month partitions exist with row counts consistent with their observed coverage boundaries, not necessarily full calendar lengths.

## Carried-forward facts

The following facts from Record 442 are carried forward without scope expansion:

- Completion descriptor SHA-256 matches its content-addressed name
- Row equation: 160,226,578 − 75,255 − 2,818 = 160,148,505 ✓
- All 19,744 parquet SHA-256 hashes match the descriptor
- All 19,744 lineage SHA-256 hashes match the descriptor
- Quality-gap lineage and parquet SHA-256 hashes match
- One typed gap: HBARUSDC 2026-07-09 provider checksum conflict
- Authority totals verified
- Schema SHA-256: `385fabea9b59aaead2d926e769808bf810c5a4121de52d577f3400d6fa179c83`
- Writer identity: `pyarrow25.0.0_parquet2.6_zstdl3_rowgroup65536_nostats_typed_v2`
- Staging: empty

## Actor fields

Both actor fields return to the Lead Quantitative Finance Researcher/Engineer.
Gate 2 remains accepted; CEX-002 and Gate 3 remain `IN_PROGRESS`. No other
product, bundle, catalog transaction, NautilusTrader check, experiment, backtest,
model, trading engine, or next ticket is authorized.
