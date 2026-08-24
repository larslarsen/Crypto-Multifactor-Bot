# CEX-002 v3 Ordering Integration and Execution

Date: 2026-08-24 UTC
Actor: Jr Dev — Hermes
Ticket: CEX-002
Authorization: `research/sprint_004/276_CEX002_V3_ORDERING_SOURCE_ACCEPTANCE_AND_EXECUTION.md`

## Integrated identities

- Production source SHA-256: `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b`
- Accepted test source SHA-256: `3b5acf85c5ee5aab891f9b9622e3cc7e86e0c2df2b630812f6f26e9bce20580a`
- Sizing CLI SHA-256: `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c`
- Accepted test function count: 161

## Commands and results

Focused pytest was run once, exactly as authorized, and passed with exit 0:

```text
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short -k 'not test_the_real_accepted_authority_completes_the_receipt_path'
```

Ruff was run once, exactly as authorized, and passed with exit 0 (`All checks passed!`).

The authorized sizing command was then run twice with the accepted manifest detail:

```text
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 50m .venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

First run: exit 0; `envelopes_published=153`; `envelopes_reused=0`.
Second run: exit 0; `envelopes_published=0`; `envelopes_reused=153`.

Both runs reported:

- receipt: `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`
- receipt SHA-256: `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`
- receipt size: `39727059` bytes
- storage state: `blocked`
- blocker: `available_capacity_insufficient`
- total future storage: `169268681433` bytes
- post-publication available capacity: `148382449709` bytes
- typed normalized partitions: `108082947883` bytes
- catalog/manifest bundle: `5556368003` bytes
- bounded temporary work: `5556368003` bytes
- new Binance raw: `20351715427` bytes
- new Coinalyze raw: `30580702` bytes
- operating reserve: `29690701415` bytes

The receipt binds the accepted detail manifest by compressed SHA-256
`64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113` and
uncompressed SHA-256
`d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17`.
The second run re-proved the same receipt without new envelopes or mutation of the
sorted evidence manifest. No acquisition, normalization, catalog publication, or
Gate 2 acceptance was performed.

## Handoff

The authorized integration and execution are complete. CEX-002 is returned to the
Lead Quantitative Finance Researcher/Engineer for review of this record and receipt.
Next ticket remains `NONE`.
