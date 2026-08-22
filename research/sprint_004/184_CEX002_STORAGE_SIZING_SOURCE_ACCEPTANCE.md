# CEX-002 Storage-Sizing Source Acceptance

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `ACCEPTED_FOR_INTEGRATION_AND_REAL_SIZING`  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; the real sizing receipt remains reviewer evidence

## Accepted drop

The reviewer accepts Claude's review-183 correction at these exact uncommitted
identities:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `795eab0312064e3d7be7dd8f826b5dc5754a8e6b5e702872ac3699dad1532390` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `e7127f9724ce046233979ec29d43035ff5358c213beee2b9cd22b0e841ee323a` |

The test path contains exactly 44 `def test_` functions. Scope is clean: only the same
three untracked sizing paths changed within this source drop. The reviewer used static
source/test inspection and read-only accepted-artifact inspection. The reviewer ran no
test, linter, control, sizing, network, acquisition, or data-mutation command.

## Review-183 closure

1. Coinalyze gross raw now contains the exact accepted 1,449,633-byte inventory receipt
   plus the conservative 569 one-symbol liquidation projection. Retained credit is one
   inventory receipt and one 40,826-byte two-symbol liquidation response. Receipt,
   covered-symbol, proved-point, and byte counts are separate, and projected new raw is
   the exact gross-minus-retained equation. The accepted report hash pins the daily query
   and cutoff; response points are parsed and checked for symbol, cadence, uniqueness, and
   authenticated lifecycle before credit.
2. Fixed-target rerun now separates stable current reproof from frozen sizing-time
   capacity observations. It compares the complete stable authority/cohort/measurement/
   projection/count identity, validates the prior receipt's canonical length and capacity
   outcome, and returns the prior document unchanged when free space changes. Focused
   changed-reserve and section-tamper cases are present.
3. The stale partition assertion now requires the greatest single logical output file.
   Output multiplicity remains in total projected bytes and partition count, not in the
   high-water partition.
4. Envelope and receipt publication now use no-follow descriptors. Temporary creation,
   linking, collision comparison, file fsync, directory fsync, and cleanup are anchored to
   the opened directory descriptor; existing targets and prior receipts are opened with
   `O_NOFOLLOW`. Focused symlink and identical/nonidentical collision cases are present.

These corrections preserve the accepted review-181/review-182 physical-input,
real-envelope, partition, capacity, and fixed-policy behavior. No additional source
correction cycle is authorized.

## Hermes integration and execution authority

Jr Dev - Hermes must work from the committed review-184 control plane and may integrate
only the three accepted paths above. All unrelated dirty DEX, BitMEX, catalog, ingest,
configuration, database-sidecar, fixture, script, and research paths must remain
byte-identical and unstaged.

Before any command, Hermes must prove:

- `HEAD == origin/main` at the reviewer publication commit;
- all three accepted SHA-256 identities and the 44-test count;
- the accepted manifest detail exists at
  `data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz`,
  with size `11,294,610` and SHA-256
  `576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4`;
- `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` and
  `data/cex002_qualify/evidence/sizing/v1/envelopes/sha256` are absent; and
- no sizing process is running.

Hermes then runs these commands in order. Any nonzero result stops all later commands and
is recorded without repair, retry, substitution, or source edit.

```bash
.venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short

.venv/bin/python -m ruff check \
  src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py \
  scripts/research/size_binance_usdm_harmonic_release.py \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py

python3 scripts/check_repo_control.py
```

Only after all three commands exit zero, Hermes runs the following local, credential-free
sizing command exactly once:

```bash
.venv/bin/python scripts/research/size_binance_usdm_harmonic_release.py \
  --manifest-detail-path \
  data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Status zero means only that measurement completed. Both `sufficient` and `blocked` are
honest outcomes and neither accepts Gate 2. After a zero first run, Hermes proves the
fixed receipt is canonical, its declared/hash/size identities match, every sizing envelope
is a regular content-addressed file, and no partial file remains. Hermes then runs the
same sizing command exactly one more time. The second transcript must say `re-proved`,
must publish zero envelopes, and must return the exact first receipt hash and size. Any
other outcome stops.

Hermes records every command, exit code, transcript, elapsed time, receipt field summary,
receipt hash/size, envelope file/count/byte identities, available capacity, pre/post tree
state, and exact Git scope in
`research/sprint_004/185_CEX002_STORAGE_SIZING_INTEGRATION_AND_EXECUTION.md`. Hermes updates
`docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to require reviewer inspection,
runs `git diff --check` restricted to the exact CEX-002 paths it will stage, stages no
unrelated path, commits, pushes, and proves `HEAD == origin/main`.

The integration commit may contain only:

- the three accepted source/test paths;
- `research/sprint_004/180_CEX002_GATE2_STORAGE_SIZING.json` if the sizing command created
  it successfully;
- `research/sprint_004/185_CEX002_STORAGE_SIZING_INTEGRATION_AND_EXECUTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The content-addressed Parquet sizing envelopes remain local evidence under the accepted
data store and are recorded by exact identity; they are not added to Git.

## Stop boundary

Hermes performs no source/test authorship, network call, credential load, qualification,
bulk acquisition, normalization, catalog publication, Gate-2 acceptance, NautilusTrader,
Harmonic Trader, payoff, PAPER, LIVE, paid-source, reduced-scope, or next-ticket work.
After record 185 is pushed, stop for reviewer inspection. Next ticket remains `NONE`.
