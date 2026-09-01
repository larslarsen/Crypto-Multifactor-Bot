# CEX-002 Review 415 — Record 414 Acceptance, Gate-2 Acceptance, and Open-Interest Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept record 414; accept one honest Binance source outcome; accept Gate 2; authorize one concrete Gate-3 product source drop
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Record 414 acceptance

Hermes commit `01c5c769d0272372ea9a17297ba55c0fa052f5be` is accepted as the exact
three-path publication of record 414:

- `research/sprint_004/414_CEX002_DIRECT_RECOVERY_TERMINAL_BLOCKER_RECORD.md`, SHA-256
  `ee80929a7c0ab96075963a5a125acaaba3a004ddfc3723296ccce603daef8fbe`;
- `docs/handoff/CURRENT_TASK.md`, pre-review SHA-256
  `b6745e4f2ea07c8a1ee4ecb8f2422414e94dcd4058be2b884439e7315b9eea27`; and
- `tickets/CEX-002.md`, pre-review SHA-256
  `ff3fdfac5bfa8f7fa69e2b4ef602d419c3bb24f44b8244b2a4b0b9e0e3a0adf1`.

`HEAD == origin/main == 01c5c769d0272372ea9a17297ba55c0fa052f5be` before this review.
Record 414 honestly reports the terminal direct-recovery execution, its procedural
deviations, the two transient retries, and the one provider-side digest conflict. The
deviations do not alter an accepted source or test path and did not damage an accepted
raw object.

## One separately accepted honest source outcome

The exact identity
`data/futures/um/daily/metrics/HBARUSDC/HBARUSDC-metrics-2026-07-09.zip`
has the following mutually inconsistent official facts:

- the accepted Binance checksum sidecar requires SHA-256
  `060025bb8887f2c0456d3333fb3a70001f3dfa5662132b0f895a7f3d3247bd52`;
- repeated retrieval of the fixed official object returns SHA-256
  `8d6e3d3efff6e615be11e43c22df3ecda579aeeb45b3da41c88a65662b5e2cc5`;
- the returned size is the accepted 9,810 bytes; and
- the returned ETag is the accepted `d7f563900c0c2c99b7fd066e02d404c4`.

The reviewer accepts this identity as the ADR-0031 separately reviewed honest source
outcome `PROVIDER_CHECKSUM_CONFLICT_UNAVAILABLE`. The served body is evidence only and is
not accepted as consumable market data. It remains retained at the recovery and quarantine
paths, no checksum is substituted, no row is inferred or filled, and no alternate planning
or download system is authorized.

Per ADR-0017, this source gap retains HBARUSDC membership and excludes only the affected
`binance_usdm_open_interest_5m` contract-day from the product intersection. Gate 3 must emit
the conflict as a typed coverage gap and must break, rather than bridge, open-interest-change
continuity across the missing interval.

## Gate-2 decision

Gate 2 is accepted with this exact terminal reconciliation:

| Source outcome | Count |
|---|---:|
| Accepted generation-0 Binance completions | 685,072 |
| Provider-checksum-verified direct-recovery objects | 51,274 |
| Separately accepted honest Binance source outcome | 1 |
| **Planned Binance identities reconciled** | **736,347** |
| Accepted Coinalyze completions | 570 |
| Existing typed Coinalyze gaps | 202 |

The direct-recovery root contains all 51,275 paths and exactly 9,207,379,061 listed bytes.
The conflicting 9,810-byte body is not counted as authenticated usable market data; its
identity is closed by the explicit source outcome above. Generation 0 remains unchanged.
No relisting, revised manifest, replacement generation, transition tool, or additional raw
acquisition is required or authorized.

This accepts acquisition only. CEX-002 remains `IN_PROGRESS`; no required research product,
bundle, experiment, backtest, Harmonic Trader, or NautilusTrader consumer result is accepted.

## One concrete Gate-3 source drop authorized

Sr Dev — Codex Sol on GPT-5.6-sol High is authorized to author the complete production and
test source for exactly one declared research product:
`binance_usdm_open_interest_5m`. The drop is confined to these three paths:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`;
- `scripts/research/normalize_binance_usdm_open_interest.py`; and
- `tests/ingest/test_binance_usdm_open_interest.py`.

The implementation must consume the accepted generation-0 completion/content authority and
the accepted v3 direct-recovery manifest/root read-only. It must produce the complete real
five-minute open-interest table, partitioned by native symbol and UTC month, under a caller-
specified hidden output root. It must reuse the exact typed schema and decimal/timestamp
contracts already accepted in ADR-0024 and the sizing implementation; it may import those
contracts but may not modify the sizing or acquisition sources.

The product must preserve open interest as a stock; compute prior stock, stock change, value
change, elapsed seconds, and `first_observation` / `contiguous` / `gap_break` state without
crossing a missing cadence or the accepted HBARUSDC conflict; preserve every valid source
metric field and exact raw-object/row lineage; refuse non-finite, overflowing, malformed,
duplicate-conflicting, path-escaping, symlink, CRC-invalid, or unsafe ZIP input; and emit typed
gaps instead of zeroes, silent row drops, or repaired values. Source ZIP expansion is bounded
and streamed during parsing; the former raw-download expansion ceiling is not reused as a
reason to reject a checksum-authenticated ZIP.

Each completed Parquet partition and lineage manifest must be content addressed, verified,
flushed, and atomically renamed under the hidden root. Replay must prove or reuse byte-identical
partitions. No partial product or bundle becomes reader-visible, and the final CEX-002 bundle
and catalog transaction remain unauthorized.

The test source must cover real-format headed and headerless metrics, exact decimal conversion,
stock/change and gap-break semantics, duplicate/conflict rejection, unsafe/CRC-invalid ZIPs,
the accepted one-identity checksum-conflict gap, interruption invisibility, and byte-identical
replay. Synthetic fixtures are test evidence only and cannot satisfy the later real-data run.

Sol may run this one targeted command once after authoring the drop:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact output without patching or rerunning.
Sol performs no real-data run, data mutation, integration, repository-record edit, Git operation,
commit, push, network access, acquisition, other product, bundle, catalog transaction, experiment,
backtest, model, or trading-engine work. It stops for reviewer source inspection.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/415_CEX002_RECORD414_ACCEPTANCE_GATE2_AND_OPEN_INTEREST_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All unrelated modified and untracked paths remain unstaged and unchanged.
