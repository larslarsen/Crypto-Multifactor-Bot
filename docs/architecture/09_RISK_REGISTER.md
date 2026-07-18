# 09 — Architecture Risk Register

| ID | Risk | Impact | Control | Current status |
|---|---|---|---|---|
| D-01 | Historical listing/delisting history is incomplete | Survivorship bias and invalid U50 | Evidence-ranked instrument master; exclude ambiguous assets; sensitivity analysis | Open/P0 |
| D-02 | Exchange timestamp unit/convention differs | Shifted bars and look-ahead | Source-versioned normalizers; raw preservation; explicit close/availability tests | Open/P0 |
| D-03 | Reported volume is unreliable | Invalid liquidity universe/capacity | Venue reliability policy; cross-source checks; separate volume components | Open/P0 |
| D-04 | Stablecoin quotes assumed equal to USD | Biased prices/volume/returns | Point-in-time stablecoin FX dataset | Open/P0 |
| D-05 | Raw legacy provenance unavailable | Non-reproducible inputs | Register/hashes; corroborate official archives; quarantine unknown | Open/P0 |
| D-06 | Historical fee/spread data unavailable | Inflated net performance | Conservative assumptions and 0.5x/1x/2x scenarios; prospective snapshots | Open/P0 |
| D-07 | Provider revises on-chain/market-cap history | Look-ahead and vintage bias | Phase 2; collect prospective vintages; no backfill treated as known earlier | Deferred |
| C-01 | Too many small Parquet files | Slow scans and metadata overhead | Monthly cross-instrument partitions; immutable compaction | Controlled |
| C-02 | Memory oversubscription | Crashes/swap and nondeterministic speed | 20 GB query limit; bounded workers; serial model folds | Controlled |
| C-03 | Local disk failure | Loss of prospective data and lineage | External incremental backup; checksum scans | Open/Operational |
| R-01 | Feature/label leakage | False alpha | Physical separation; as-of API; event-time purge/property tests | Design control |
| R-02 | Researcher degrees of freedom | Selection bias | Preregistered registry; append-only attempts; prospective holdout | Design control |
| R-03 | Complex ML dominates effort early | Overfit and delayed baseline | Baseline ladder; no ML before factor gate | Design control |
| S-01 | Wrong model/representation loaded | Invalid live decisions | Typed model manifest and promotion registry; no globs | Design control |
| S-02 | Research and serving transforms drift | Paper/live mismatch | Shared pure factor library; parity tests | Design control |
| S-03 | Stale/missing data still trades | Operational loss | Fail-closed serving and decision snapshot validation | Design control |
| O-01 | Architecture becomes a framework project | Lost research time | Modular monolith; ADR requirement for new infrastructure | Design control |
| O-02 | Free API changes/limits | Collection gaps | bulk-first; multiple official sources; source health report; overlap repair | Open/Ongoing |

## Decisions deliberately deferred

- exact historical execution venue approval;
- final partition hash buckets;
- exact universe decision timestamp;
- optimizer library;
- live broker/exchange adapter;
- market-cap provider;
- on-chain factor set;
- event-bar serving architecture.

Deferral is intentional where the local audit or empirical results must determine the answer.
