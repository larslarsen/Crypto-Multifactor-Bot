# CEX-002 Record 464 — Membership Integration and Real Run Record

- **Date:** 2026-09-02
- **Jr Dev:** Hermes
- **Ticket:** CEX-002
- **Review:** 463
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` — four required products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Preproof

Hermes reproved `HEAD == origin/main == 98909b60a4880bc83f6a895fd8614b631779064a` at Review 463's publication commit. All three accepted paths reproved at exact line counts and SHA-256:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_membership.py` | 761 | `7e14254cd8275521a52ab88faf747f9c72fd0fd51cc2a7d97d4f405af723ffc4` |
| `scripts/research/normalize_binance_usdm_membership.py` | 46 | `cd762f2b673bc2beca322da6a8ae6358d51f99cfe819ebf6313f330414140bd` |
| `tests/ingest/test_binance_usdm_membership.py` | 443 | `5c597ba2e43f25193c6c64dfb1acbe733f39f49aacfbf304f870bf31455fb110` |

## Integration

Hermes ran Review 463's three ordered commands:

1. `.venv/bin/python -m pytest tests/ingest/test_binance_usdm_membership.py -q --tb=short` — 27 passed
2. `.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_membership.py scripts/research/normalize_binance_usdm_membership.py tests/ingest/test_binance_usdm_membership.py` — All checks passed
3. `python3 scripts/check_repo_control.py` — PASS

All three passed. Hermes staged exactly the three accepted paths, committed at `d2753e7e5996fbe1acc2825d3399c5f64d529573` ("CEX-002: integrate perpetual membership normalizer"), pushed, and proved `HEAD == origin/main == d2753e7e5996fbe1acc2825d3399c5f64d529573`.

## One real membership run

Preproof: output root `data/.cex002_perpetual_membership` absent and not a symlink; `df -B1 --output=avail data` = 568,390,352,896 bytes (above the 110,648,021,942 floor).

Hermes executed exactly once in the foreground and remained attached until terminal:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_membership.py \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --contract-metadata data/cex002_qualify/cex002_official_contract_metadata.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --output-root data/.cex002_perpetual_membership
```

Start: `2026-09-02T20:26:06Z`. End: `2026-09-02T20:26:11Z`. Runtime: ~5 seconds. Exit code: 0.

## Terminal evidence

- **stdout (JSON):** `{"completion_sha256":"01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3","membership_rows":771,"partitions":771,"schema_sha256":"35c7101271c80c3c6faa222b57e5ff7a48930a470aebbc2cf330dee43c39fafb"}`
- **Completion path:** `data/.cex002_perpetual_membership/.complete/01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3.json`
- **Completion SHA-256:** `01d054b34c3a92cc349f9484296031e8cbb67ae7e62eb0a8b38c6d3928d977a3`
- **Schema SHA-256:** `35c7101271c80c3c6faa222b57e5ff7a48930a470aebbc2cf330dee43c39fafb`
- **Normalizer source SHA-256:** `7e14254cd8275521a52ab88faf747f9c72fd0fd51cc2a7d97d4f405af723ffc4`
- **Membership rows:** 771
- **Detailed metadata rows:** 698
- **Funding-only rows:** 73
- **Metadata equation:** 698 + 73 = 771
- **Classifications:** 1008
- **Excluded classifications:** 237
- **Row equation:** 1008 − 237 = 771 accepted membership rows
- **Partitions:** 771
- **Lineages:** 771
- **Partition bytes:** 5,285,816
- **Lineage bytes:** 777,292
- **Staging state:** empty
- **Sole-completion state:** one completion file in `.complete/`
- **Post-run available bytes:** 568,289,509,376

## Content-address verification

Every descriptor-referenced partition and lineage path was verified beneath the hidden root. All 771 partition parquet hashes and all 771 lineage JSON hashes match their content-addressed filenames. Zero mismatches.

## Authority digests

- `contract_metadata`: `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42`
- `report`: `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`
- `sizing`: `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`

## Publication

Record 464 is published. Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. Gate 2 remains `ACCEPTED`; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`. No acquisition, network request, source/test correction, deletion, cleanup, other product, coverage product, bundle, catalog transaction, NautilusTrader check, experiment, model, Harmonic Trader, PAPER, LIVE, or next-ticket work is authorized.
