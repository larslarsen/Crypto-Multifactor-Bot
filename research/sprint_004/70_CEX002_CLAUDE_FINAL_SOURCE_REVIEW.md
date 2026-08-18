# CEX-002 Claude Final Operational Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **ACCEPT SOURCE DROP; AUTHORIZE HERMES INTEGRATION AND BOUNDED REAL GATE 1 RUN**

## Reviewed identities

Committed control-plane base:
`HEAD == origin/main == 30d0e78d1b0941e930be65963761cfef4b8b0ef8`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `9e75242b5ef9c67e5199dac24efe1385c43abdbdb8419cc913f9ec14c40b0aa2` |

The drop is confined to the three authorized paths. The CLI is unchanged from review 69.

## Acceptance findings

The retained-sidecar chain is now complete:

1. Every checksum sidecar is persisted content-addressably before a sample checkpoint is
   written, including in-memory/test-index acquisition.
2. Each checkpoint records the sidecar's cache-local path and blob SHA-256.
3. New acquisition, retained recovery, and every completed-sample resume rehash the
   sidecar, validate its content address, require exactly one checksum/filename record,
   bind the filename to the object key, and require sidecar checksum, checkpoint digest,
   provider checksum, and retained raw bytes to agree.
4. Missing, relocated, substituted, malformed, or tampered sidecars fail closed with
   `ResumeIntegrityError` instead of redownloading or promoting checkpoint state.
5. Focused test source covers intact no-fetch resume plus missing, tampered, relocated,
   substituted-digest, foreign-filename, disagreeing-checksum, and multi-record sidecars.

All review-67 through review-69 requirements are now represented in source: shared
physical inventory, request-keyed page checkpoints, per-sample atomic progress, salvage of
retained bytes, one bounded retry owner with a durable incident journal, inventory-first
unique-object budget accounting, and injected interruption/resume equivalence.

## Reviewer evidence

- Focused Ruff over the three reviewed paths: PASS.
- In-memory AST compilation over the three reviewed paths: PASS.
- Intact retained-sidecar no-network-fetch direct probe: PASS.
- Missing retained-sidecar fail-closed direct probe: PASS.
- Prior review-68 substitution, malformed-checkpoint, checksum-substitution, and
  unique-object-budget direct probes: PASS in review 69.
- Real store shape remains approximately 691 MiB with six raw objects and no old progress
  file; no reviewer command mutated it.
- Pytest and network qualification: not run by the reviewer; these belong to Hermes.

This is source acceptance only. It is not Gate 1 data acceptance.

## Hermes integration authorization

Hermes verifies the three hashes above, preserves every unrelated dirty path, and runs in
order:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/ scripts/`
4. `python3 scripts/check_repo_control.py`
5. `git diff --check`

The monorepo full suite remains deferred to final CEX-002 release acceptance. No `-k`,
clean-worktree reconstruction, DEX/BitMEX test execution, or source edit is authorized.
If a focused command fails, Hermes records the exact failure in
`research/sprint_004/71_CEX002_GATE1_RESUMABLE_EXECUTION.md`, publishes that evidence, and
stops without a network run.

After all five commands pass, Hermes stages only the three reviewed source/test paths,
checks `git diff --cached --name-only`, commits with message
`CEX-002: integrate resumable bounded Gate 1 qualifier`, and pushes so
`HEAD == origin/main` before network execution.

## Bounded real execution authorization

Hermes then runs the real qualifier against the existing `data/cex002_qualify` store. It
must not delete, rename, or replace that store. It loads `.env` without printing it or
placing the key in a command argument.

First run:

`/bin/bash -lc 'set -a; . ./.env; set +a; .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py --store-root data/cex002_qualify --progress-path data/cex002_qualify/cex002_qualification_progress.json --report-path /tmp/cex002_gate1_resumable_first.json'`

Exit 0 is qualified, exit 2 is an honest blocked matrix, and exit 1 is execution failure.
For exit 1, Hermes stops network work but still records and publishes the durable
checkpoint/retry/store evidence in record 71; it does not claim success.

If the first run exits 0 or 2, Hermes runs the same qualifier a second time with report:

`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

It then runs:

`.venv/bin/python -c 'import json; from pathlib import Path; from cryptofactors.acquisition.binance_usdm_harmonic_qualification import drop_identity_volatility; a=json.loads(Path("/tmp/cex002_gate1_resumable_first.json").read_text()); b=json.loads(Path("research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json").read_text()); assert drop_identity_volatility(a)==drop_identity_volatility(b); print("Gate 1 semantic resume identity: PASS")'`

Hermes records commands, exits, elapsed time, report hashes, exact object/byte totals,
symbol and blocked-product counts, sample plan and new-download bytes, recovered/reused
samples, listing checkpoint claimed/reused/fetched/unclaimed counts, retry incidents,
Coinalyze provenance, progress/checkpoint identities, and retained-store size in record 71.
No secret value may appear.

Before the final evidence commit, Hermes changes the next required actor in
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to
`Lead Quantitative Finance Researcher/Engineer — inspect Gate 1 resumable execution`.
It stages only those two records, record 71, and the real report when one exists, verifies
the staged path list, commits, pushes, establishes `HEAD == origin/main`, and stops.

## Gate decision

Gate 1 remains `IN_PROGRESS` pending real evidence. Gate 2 and harmonic-model development
remain unauthorized. There is no partial PASS.
