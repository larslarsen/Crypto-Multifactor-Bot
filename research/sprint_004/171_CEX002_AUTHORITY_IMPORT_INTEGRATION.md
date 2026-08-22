# CEX-002 Authority Import Integration

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/170_CEX002_AUTHORITY_IMPORT_SOURCE_ACCEPTANCE.md`

## 1. Preproof

Hermes established:

`HEAD == origin/main == cc3c6957dae1413e42628b91aeca9e461b600b14`

before staging.

Accepted source hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` |

The accepted CEX test path contained 305 unique `test_` function definitions. No `python3`
qualification process was running.

## 2. Integration

Hermes staged exactly:

`src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`

and committed:

`c4a3df4e8c10590ebbc2413cd8683199a77f77a9`

Commit message:

`CEX-002: integrate authority import correction`

After push:

`HEAD == origin/main == c4a3df4e8c10590ebbc2413cd8683199a77f77a9`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
Hermes made no source or test edit after integration.

## 3. Focused command sequence

Review 170 required a complete C1-C5 restart. Command 1 exited nonzero, so commands 2-5
were not authorized and were not run.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 1

Elapsed seconds: 6

Material output reached `[100%]` and reported 5 failed tests:

- `test_cost_validation_accepts_real_shaped_headed_payloads`
- `test_cost_validation_rejects_defective_quote_rows[rows4-quantity is negative]`
- `test_cost_validation_rejects_defective_quote_rows[rows5-price is not positive]`
- `test_all_empty_cost_object_is_unavailable_evidence_not_an_incident`
- `test_cli_exposes_the_pinned_source_correction_switch`

Failure signatures:

- `test_cost_validation_accepts_real_shaped_headed_payloads` expected
  `uncrossed_quotes` in `ticker.checks`; actual checks included
  `typed_two_sided_bid_only_ask_only_or_empty_states` and
  `nonnegative_consistent_price_and_quantity_sides`.
- `rows4-quantity is negative` expected regex `quantity is negative`; actual message was
  `cost sample quote value is negative`.
- `rows5-price is not positive` expected regex `price is not positive`; actual message was
  `cost sample quote side is inconsistently zero`.
- `test_all_empty_cost_object_is_unavailable_evidence_not_an_incident` expected the
  unavailable block item keys to equal `block["keys"]`; the first key differed between
  bookTicker and bookDepth.
- `test_cli_exposes_the_pinned_source_correction_switch` expected
  `reviewed_source_correction_preflight(` in the CLI source; it was absent.

### C2-C5

Not run because C1 exited nonzero.

## 4. Final source state

Final source hashes still match review 170:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` |

The CEX test path still contains 305 unique `test_` function definitions.

## 5. Disposition

No live `--apply-reviewed-v4-source-correction-only` invocation, data mutation,
source-data network operation beyond authorized Git pushes, ordinary qualification,
reservation reconciliation, report write, Gate-1 acceptance, sizing, Gate 2, bulk
acquisition, normalization, catalog publication, Nautilus work, Harmonic Trader work,
payoff analysis, PAPER, LIVE, paid source, reduced scope, or next-ticket work occurred.

This publication records the exact one-path integration and C1 failure only. CEX-002
remains `IN_PROGRESS`; Gate 1 has not passed; next ticket remains `NONE`.
