# CEX-002 Sizing Source Acceptance and Execution

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `ADR0023_SOURCE_ACCEPTED_INTEGRATION_AND_SIZING_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022 and ADR-0023
**Gate 1:** Accepted
**Gate 2:** Not accepted; sizing measurement authorized

## Accepted source

Claude's final ADR-0023 drop is accepted at these exact identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `7e370adddcf03c531834e503654fc41946fd75f8ee662605b92b5cd16a4d7fb9` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `10d13532c754ec1c98c2db634c5c53402cee9f67f28f8aa5b60b26a1d5f90b63` |

The sizing CLI remains frozen at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.
The test source contains 63 `def test_` functions and collects 127 cases.

The production source advances every authority pin to record 218, proves the report's
retained summary field by field, keeps manifest consumability separate, applies path-bound
recovery to the complete selected-plus-cost requirement, rehashes each credited object and
sidecar, proves declared byte size, classifies keys by actual requirement membership, and
deduplicates objects and bytes only by digest. The receipt separately exposes 56 manifest-
consumable rows, 68 selected retained keys, 5 cost retained keys, 73 valid requirement
keys, 73 unique objects, and 5,225,416 unique bytes.

## Reviewer validation

Under the owner's focused-validation authorization, the reviewer ran the complete sizing
suite after the ADR-0023 correction:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
```

All 127 cases passed in 3.4 seconds. Exact-path Ruff passed over accepted production, the
frozen CLI, and tests. Restricted two-path whitespace validation passed.

The reviewer then ran a read-only real-store authority and retained-credit probe through
the exact accepted production bytes. It used no network and wrote no byte. It re-proved:

```text
manifest_consumable_rows=56
selected_retained_keys=68
cost_retained_keys=5
valid_requirement_keys=73
unique_objects=73
unique_bytes=5225416
unverified_objects=0
rejected_recovered_rows=176
selected_objects=733203
selected_bytes=7833966625
cost_objects=3144
cost_bytes=12522974218
combined_objects=736347
combined_bytes=20356940843
projected_new_binance_raw_bytes=20351715427
```

The probe also reproduced the pinned report/manifest/lock/ledger/source/checkpoint/listing/
metadata bindings and the report's identical retained summary. This resolves the failure
that stopped record 195 before any sizing output.

## Current sizing pre-state

Before this review, both sizing outputs are absent:

- `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` does not exist; and
- `data/cex002_qualify/evidence/sizing/v1/envelopes/sha256/` does not exist.

The store has 41,372 files. The destination filesystem reports 157,372,747,776 available
bytes. These observations are not capacity acceptance; the authorized sizing calculation
must derive normalized/catalog, Coinalyze, temporary high-water, reserve, and total future
storage under ADR-0021.

## Hermes integration and execution authority

Jr Dev - Hermes is authorized for one integrated sequence. Before any write, prove:

- `HEAD == origin/main` at this review's publication commit;
- the three sizing paths match the exact identities above and only production/tests differ
  from `HEAD`;
- report, manifest, lock, amendment ledger, qualification source/CLI, progress checkpoint,
  listing checkpoint, metadata, sample plan, retry journal, and legacy ledger match record
  218 and review 219/222 identities;
- the sizing receipt and envelope tree remain absent; and
- no sizing or qualification process is running.

Any mismatch stops before execution. Snapshot hashes, sizes, file counts, and available
bytes for the accepted authority, complete store, and intended sizing outputs.

Run exactly this first local invocation from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
    --manifest-detail-path \
    data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
sizing_status=$?
```

This command is local and credential-free. Do not load `.env` or request network access.
Status 0 means the complete sizing measurement published, whether its honest state is
`sufficient` or `blocked`. Any nonzero status ends the authorization: do not retry, run a
second invocation, repair, substitute an artifact, or launch acquisition.

If and only if the first invocation exits 0, snapshot the complete store and receipt, then
run the identical command exactly once more. The second invocation must re-prove the same
receipt, reuse every sizing envelope, create no new persistent artifact, and leave the
complete store-file hash manifest identical. Any mismatch is a failure and stops.

## Required record

Publish `research/sprint_004/223_CEX002_SIZING_INTEGRATION_AND_EXECUTION.md` with:

- exact preproof and the accepted source/test diff scope;
- both commands verbatim, start/end timestamps, duration, status, and complete transcript;
- receipt path, schema, hash, size, storage-preflight state, blockers, authorization text,
  code/authority bindings, and exact 56/68/5/73/73/5,225,416 retained facts;
- all 12 family measurements, exact rational witnesses, projections, multiplicities,
  partitions, normalized bytes, and largest projected partition;
- Coinalyze evidence/mapping/lifecycle/raw/normalized projection facts;
- every capacity component, total future storage, post-publication available bytes,
  reserve, shortfall if any, and the result in decimal GB and binary GiB;
- sizing-envelope count, total bytes, individual hashes, and first/second publication or
  reuse counts;
- before/after hashes for every accepted authority and every persistent store mutation;
- proof the second successful invocation changed no persistent file; and
- exact staged paths, commit, push, repository-control result, whitespace result, and final
  `HEAD == origin/main`.

For a successful measurement, stage exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json`;
4. `research/sprint_004/223_CEX002_SIZING_INTEGRATION_AND_EXECUTION.md`;
5. `docs/handoff/CURRENT_TASK.md`; and
6. `tickets/CEX-002.md`.

For a failed measurement with no valid receipt, omit path 3 and stage the other five.
Sizing envelopes are ignored data evidence and must never be staged. No unrelated dirty,
database, DEX, BitMEX, catalog, ingest, fixture, or other data path may be staged.

Run repository control and a whitespace check restricted to the intended publication
paths, commit, push, prove `HEAD == origin/main`, and stop for reviewer inspection. Do not
rerun pytest or Ruff; the reviewer has accepted them at the exact hashes.

## Stop boundary

This authorizes only accepted source/test integration and the bounded local sizing
measurement plus one conditional idempotence invocation. It authorizes no Gate-2
acceptance by Hermes or the owner, bulk acquisition, normalization, catalog publication,
NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, paid source, reduced scope,
or next-ticket work. Gate 2 remains unaccepted and next ticket remains `NONE`.
