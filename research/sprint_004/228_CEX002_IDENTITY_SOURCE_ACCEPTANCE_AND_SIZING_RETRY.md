# CEX-002 Identity Source Acceptance and Sizing Retry

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `IDENTITY_SOURCE_ACCEPTED_INTEGRATION_VALIDATION_AND_SIZING_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022 and ADR-0023
**Gate 1:** Accepted
**Gate 2:** Not accepted; corrected sizing measurement remains pending

## Accepted source

Claude's review-227 provider/native correction is accepted at these exact identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `aafdf65733e2865f92d89d75ce4a4ba934ce240d3d816e37a9fbe0072749ca82` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `343d422ce86d217d39459b49d40308125065b6a7873459c7d27ca37a6eda12c8` |

The sizing CLI remains unchanged at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.
The corrected test file contains 85 `def test_` functions. The 14 new functions expand to
28 cases, so the expected focused collection is 181 cases.

The production source now builds one-to-one provider/native authority from the pinned
future-market inventory, proves both report inventory counts, keeps supported/lifecycle/
projection identity native, maps retained response provider identities before coverage
checks, rejects duplicate/conflicting series, re-proves all anchor surfaces, and publishes
provider and native retained identities separately. It does not derive either namespace by
editing a symbol string. The fixture now mirrors the real namespace boundary and the added
tests cover count-preserving binding damage, inventory collisions, excluded rows, unknown
and duplicate retained identities, lifecycle mapping, anchor disagreements, and receipt
identity fields.

The reviewer inspected the complete two-file diff and restricted whitespace. Claude did
not run tests, mutate evidence, or use Git. The 96 existing Binance sizing envelopes remain
unchanged: 96 files totaling 1,890,921 bytes.

## Real-authority preproof

Read-only reviewer inspection of the pinned real authority establishes the facts Hermes
must reproduce before validation or sizing:

- the future-market inventory has 759 unique Binance-perpetual provider identities and
  759 unique native identities;
- report `binance_perpetual_market_count` and
  `native_identity_validated_markets` both equal 759;
- the supported list has 569 entries and 569 unique Binance-native symbols;
- the unmapped list has 202 entries and 202 unique Binance-native symbols;
- supported and unmapped are disjoint, their union has 771 identities, and that union is
  exactly the 771 accepted membership classifications and report `universe_size`;
- all 569 supported identities have an inventory binding, while the other 190 inventory
  identities do not enter the supported projection;
- the two retained liquidation provider identities, requested symbols, matched markets,
  and anchor rows bind exactly to native `BTCUSDT` and `ETHUSDT`; and
- receipt 180 remains absent while the current complete evidence store has 41,468 files
  and manifest SHA-256
  `361095f2be95d9efab91046b910f76cc514e8e2fc1a79e1d359ead2f13ddedb6`.

Any mismatch stops before execution.

## Hermes integrated sequence

Jr Dev - Hermes is authorized for one bounded sequence. Do not pull, reset, checkout,
restore, stash, delete, or rewrite the shared workspace or existing sizing envelopes.
Verify `HEAD == origin/main` at this review's publication commit, the exact three sizing
hashes above, every record-226 authority identity, the real-authority facts above, receipt
absence, existing-envelope count/bytes, available space, and that no qualification or
sizing process is running.

Run exactly:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
focused_status=$?

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py
ruff_status=$?
```

Both commands must exit 0, the focused suite must collect exactly 181 cases, and all three
hashes must remain exact. Any failure ends authorization with no repair or sizing run.

If and only if both validations pass, run exactly:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

Do not load `.env` or request network. A nonzero status ends authorization with no retry,
repair, or substitution. If and only if the first sizing invocation exits 0, snapshot the
complete evidence store and receipt, then run the identical sizing command exactly once
more. The first success must reuse the 96 existing Binance envelopes and may publish only
the exact missing Coinalyze envelopes plus receipt 180. The second invocation must reuse
all envelopes, reproduce identical receipt bytes, create no persistent file, and leave the
complete evidence-store hash manifest identical.

## Record and publication

Publish `research/sprint_004/229_CEX002_IDENTITY_CORRECTED_SIZING_EXECUTION.md` with all
preproof facts, commands, timestamps, durations, statuses, and transcripts. On failure,
prove the resulting evidence-store state and absence of a valid receipt, update controls
to `AWAITING_REVIEW`, publish the authorized integration paths, and stop.

On success, record every review-222 sizing fact: the 56/68/5/73/73/5,225,416 retained
decomposition; all 12 family measurements, multiplicities, partitions, and rational
witnesses; the 759 inventory mappings, 569 supported native mappings, 202 typed gaps, two
retained provider/native anchors, lifecycles, raw and normalized Coinalyze projections;
every capacity component; total future bytes in decimal GB and binary GiB; available
bytes, reserve, shortfall and state; all envelope identities and publication/reuse counts;
and byte-for-byte second-run idempotence.

For success, stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`;
4. `research/sprint_004/229_CEX002_IDENTITY_CORRECTED_SIZING_EXECUTION.md`;
5. `docs/handoff/CURRENT_TASK.md`; and
6. `tickets/CEX-002.md`.

For failure without a valid receipt, omit path 3 and stage the other five. Sizing envelopes
are ignored evidence and must never be staged. Run repository control and publication-path
whitespace validation, commit, push, prove `HEAD == origin/main`, and stop. Do not stage or
alter unrelated dirty, database, DEX, BitMEX, catalog, ingest, fixture, or other data paths.

This reviewer-authored governance publication is restricted to exactly:

1. `research/sprint_004/228_CEX002_IDENTITY_SOURCE_ACCEPTANCE_AND_SIZING_RETRY.md`;
2. `docs/handoff/CURRENT_TASK.md`; and
3. `tickets/CEX-002.md`.

## Stop boundary

This authorizes only exact integration, focused validation, corrected local sizing, one
conditional idempotence run, evidence recording, and exact-path publication. It authorizes
no source repair, network, Gate-2 acceptance by Hermes, bulk acquisition, normalization,
catalog publication, NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, paid
data, reduced scope, or next-ticket work. Next ticket remains `NONE`.
