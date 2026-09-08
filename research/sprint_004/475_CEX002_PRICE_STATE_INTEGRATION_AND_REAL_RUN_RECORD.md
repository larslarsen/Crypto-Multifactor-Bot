# CEX-002 Record 475 — Price-State Integration and Real Run Record

- **Date:** 2026-09-08
- **Ticket:** CEX-002
- **Review:** 474
- **Actor:** Jr Dev — Hermes
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` — six of eleven required products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Identity proof

- `HEAD == origin/main == a5699e7b60e3123be1514021d796b1d927c58698` (integration commit)
- Source `05a59b9b5ad89ef08f2d8bdd3ec254ad01714bff559e78ca15278e72d0dbbb26` (2,118 lines)
- CLI `ea423f382ca842d0a0f197ed7cdf1a337010df6354b95cc441ef35aa7ed62445` (54 lines)
- Test `921eb3ebb7d05de9b0d24e1c17abe661e631908922ff774871c684473ad69263` (801 lines)

## Integration

The three integration commands passed in order: pytest 50/50 exit 0, ruff `All checks passed!`, `check_repo_control.py` PASS, `git diff --check` clean. Staged exactly the three accepted paths, committed `CEX-002: integrate paired price-state normalizer`, pushed, proved `HEAD == origin/main`.

## One real local run

Preproof passed: `data/.cex002_price_state` absent and not a symlink, no price-state normalizer running, report hash `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`, sizing hash `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`, `df -B1 --output=avail data` = **229,433,143,296** bytes (above the 110,648,021,942 floor).

Executed exactly once in the foreground with a 7,200-second mechanism allowance, remaining attached until terminal:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_price_state.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --output-root data/.cex002_price_state
```

- **Start:** 2026-09-08T19:21:56Z (epoch 1788895316)
- **End:** 2026-09-08T20:19:55Z (epoch 1788898795)
- **Wall duration:** 3,479 seconds (~58 minutes)
- **Exit code:** 0
- **Pre available bytes:** 229,433,143,296
- **Post available bytes:** 221,671,538,688
- **Capacity consumed:** 7,761,604,608 bytes

This command performed no network access and altered no generation-0 authority.

## Terminal stdout

```json
{
  "basis_completion_sha256": "b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0",
  "basis_gap_artifacts": 4181,
  "basis_partitions": 21491,
  "basis_rows": 15125823,
  "basis_unjoinable_source_rows": 1901665,
  "indicative_completion_sha256": "360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0",
  "indicative_gap_artifacts": 1115,
  "indicative_partitions": 21507,
  "indicative_rows": 15153756,
  "premium_zip_reads": 32371
}
```

## Indicative funding product — `binance_usdm_funding_indicative_1h`

- **Completion SHA-256:** `360eb662ab89c47ca1f6db754b74f486a42de4aa116970221f0739268a51fba0`
- **Schema SHA-256:** `2934d65810f919d044c8d0cf185a7a48c0061a03134ce43470516a96b2780489` (22 columns)
- **Normalizer source SHA-256:** `05a59b9b5ad89ef08f2d8bdd3ec254ad01714bff559e78ca15278e72d0dbbb26`
- **Partitions:** 21,507 successful + 0 gap-only = 21,507 source partitions
- **Product rows:** 15,153,756
- **Gap artifacts:** 1,115 (1,215 gap rows, 48,117 missing grid points)
- **Unjoinable source rows:** 0
- **Premium ZIP reads:** 32,371
- **Observed ranges:** `0GUSDT`..`ZRXUSDT`, open time 1577156400000..1787266800000
- **Generation-0:** 685,072 Binance completions, 32,361 `checksum_verified` + 10 `retained_credit` = 32,371 selected premium sources, 299,148,485 selected bytes

## Basis product — `binance_usdm_mark_index_basis_1h`

- **Completion SHA-256:** `b698c0543c281e3244e0c3358ea7ce1f347bc591b06a076058fed749d05584f0`
- **Schema SHA-256:** `963afa1edcda8088d296c83f18c3d3608cf7d91c2b213cd9c42fee49e45d5260` (33 columns)
- **Normalizer source SHA-256:** `05a59b9b5ad89ef08f2d8bdd3ec254ad01714bff559e78ca15278e72d0dbbb26`
- **Partitions:** 21,491 successful + 1,777 gap-only = 23,268 source partitions
- **Product rows:** 15,125,823
- **Gap artifacts:** 4,181
- **Unjoinable source rows:** 1,901,665
- **Joined input rows:** 45,377,469
- **Physical source rows:** 47,279,134
- **Relative basis floor applications:** 15,125,823
- **Collapsed / excluded / fabricated:** 0 / 0 / 0
- **Observed ranges:** `0GUSDT`..`ZRXUSDT`, open time 1577156400000..1787266800000

## Row equation (basis)

```
physical_source_rows = joined_input_rows + unjoinable_source_rows
47,279,134 = 45,377,469 + 1,901,665 ✓

product_rows = joined_input_rows / 3  (mark + index + premium per hour)
15,125,823 = 45,377,469 / 3 ✓
```

## Source-family reconciliation (basis)

| Family | Sources | Physical rows |
|---|---:|---:|
| daily/indexPriceKlines | 12,266 | 294,312 |
| daily/markPriceKlines | 14,096 | 338,224 |
| daily/premiumIndexKlines | 11,439 | 274,512 |
| monthly/indexPriceKlines | 21,721 | 15,555,076 |
| monthly/markPriceKlines | 22,286 | 15,937,766 |
| monthly/premiumIndexKlines | 20,932 | 14,879,244 |
| **Total** | **102,740** | **47,279,134** ✓ |

## Independent artifact reconciliation

- Indicative: 22,622 Parquets + 22,622 lineages + 1,115 quality-gap Parquets + 1,115 quality-gap lineages + 1 completion descriptor beneath `data/.cex002_price_state/binance_usdm_funding_indicative_1h/`
- Basis: 25,672 Parquets + 25,672 lineages + 4,181 quality-gap Parquets + 4,181 quality-gap lineages + 1 completion descriptor beneath `data/.cex002_price_state/binance_usdm_mark_index_basis_1h/`
- `.staging/` empty (0 files)
- Sole completion per product subdirectory
- Every descriptor-referenced partition and lineage path is contained beneath the hidden root, exists as a regular non-symlink file, and has the content digest named by both its filename and descriptor
- Both product completion SHA-256s match their file content

## Source-review cross-checks (derived, not substituted)

| Check | Source-review observation | Derived result |
|---|---:|---:|
| Selected price-state objects / bytes | 102,740 / 1,038,628,891 | 102,740 / 1,038,628,891 ✓ |
| Verified / retained-credit completions | 102,711 / 29 | 102,711 / 29 ✓ |
| Premium objects / bytes / reads | 32,371 / 299,148,485 / 32,371 | 32,371 / 299,148,485 / 32,371 ✓ |
| Premium physical and product rows | 15,153,756 | 15,153,756 ✓ |
| Indicative nonempty partitions | 21,507 | 21,507 ✓ |
| All-family physical rows | 47,279,134 | 47,279,134 ✓ |
| Basis product rows / joined input rows | 15,125,823 / 45,377,469 | 15,125,823 / 45,377,469 ✓ |
| Basis unjoinable source rows | 1,901,665 | 1,901,665 ✓ |
| Basis nonempty / gap-only / source-union partitions | 21,491 / 1,777 / 23,268 | 21,491 / 1,777 / 23,268 ✓ |
| Collapsed / excluded / fabricated source rows | 0 / 0 / 0 | 0 / 0 / 0 ✓ |

## Economic checks

- All indicative rate values are null with `indicative_rate_status = direct_indicative_rate_unavailable` (premium inputs preserved, no invented funding rate)
- Native identity and canonical-null state exact
- Signed/zero premium preserved
- Basis values bind the proper mark/index/premium sources with `basis_join_status = causal_open_time_join`
- Relative basis uses the scale-18 floor rule: `(absolute_unscaled * 10**18) // index_unscaled`, applied to all 15,125,823 rows

## Accepted products (Gate 3)

Six of eleven required products are now accepted:

1. `binance_usdm_perpetual_membership` (Review 465)
2. `binance_usdm_bar_1h` (Review 460)
3. `binance_usdm_trade_flow_1h` (Review 460)
4. `binance_usdm_open_interest_5m` (Review 435/459)
5. `binance_usdm_funding_realized` (Review 473)
6. `binance_usdm_funding_indicative_1h` and `binance_usdm_mark_index_basis_1h` (Review 474, this record)

Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`. Both actor fields return to the Lead Quantitative Finance Researcher/Engineer. No later batch, coverage/bundle/catalog transaction, NautilusTrader check, experiment, model, Harmonic Trader work, PAPER, LIVE, or next ticket is authorized.
