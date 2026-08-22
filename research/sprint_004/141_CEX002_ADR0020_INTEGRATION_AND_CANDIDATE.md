# CEX-002 ADR-0020 Integration and Focused-Command Stop

Date: 2026-08-21
Author: Jr Dev - Hermes
Governing review: `research/sprint_004/140_CEX002_ADR0020_SOURCE_ACCEPTANCE.md`

## 1. Integration

Hermes established `HEAD == origin/main == 6e4d5da8965ed8d316ae7f01f8a994bd9320c446`
at the review-140 publication commit before staging.

Accepted path hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `2f9647d8c41dd69e3fce79889d889b54beb3c8742d8d7ef24d57803cdd2443b1` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `8c455659af3a4ac13184b2ba4034dbeb1308a78e0834a2eed970159d6e577cbc` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `3836413a2e667449e700b65477e10f2b30358f2099f1965d51f21bece9b4f248` |

Frozen dependency hashes re-proved before staging:

| Path | SHA-256 |
|---|---|
| `src/source_audit/download.py` | `f231930f743f4b2f415dd84a96ec3c1ec3b1c1efab5deb7536db57fce5473fa5` |
| `tests/test_download_atomicity.py` | `30388dba0568912b7bbe3f83c5454de89cd8cf5cd1288f260d30cfda0bd8d587` |

Additional pre-integration checks:

- fixture directory diff for `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/`: empty;
- accepted compact report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`:
  17,349,108 bytes, SHA-256
  `e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`;
- CEX test source unique `test_` definitions: 261.

Hermes staged exactly the three accepted Python paths and committed:

`68d437cb0db4c1bc0b4246b131ba0deb38c60699`

Commit message:

`CEX-002: integrate ADR-0020 qualification source`

After push, Hermes proved:

`HEAD == origin/main == 68d437cb0db4c1bc0b4246b131ba0deb38c60699`

The index was empty after integration. Existing unrelated dirty paths remained unstaged.
No source or test edit was made after integration.

## 2. Focused command sequence

Review 140 required stop-on-first-failure execution. Command 1 failed, so commands 2-5,
compact-report preservation, pre-candidate snapshots, candidate execution, and post-proof
were not authorized and were not run.

### C1

Command:

`.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`

Exit: 1

Failure:

`tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves`

Observed assertion:

`assert authority["archive_evidence"]["family_count"] == 2`

Actual value:

`3`

Relevant pytest output:

```text
FAILED tests/acquisition/test_binance_usdm_harmonic_qualification.py::test_frozen_delivery_identity_resolves_only_while_its_evidence_reproves
```

The command output did not print collected or passed counts under the requested `-q
--tb=short` invocation; it printed progress through 100%, one failure, and exit 1. Hermes
does not infer missing pass counts.

### C2-C5

Not run because C1 exited nonzero.

## 3. Candidate and report disposition

No compact-report preservation was performed after C1 failed. No candidate process was
started. No `.env` candidate environment was loaded. No network/data run, plan migration,
sample acquisition, Gate 2 work, normalization, catalog publication, Nautilus work,
Harmonic Trader work, payoff analysis, PAPER, LIVE, or next-ticket work occurred.

`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` was not staged or published
by this record because the failure occurred before any valid terminal status-0/2
replacement. Gate 1 has not passed.

## 4. Mutations

Committed source/test/CLI integration mutation:

- `scripts/research/qualify_binance_usdm_harmonic_sources.py`
- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`

Record/control publication mutation:

- `docs/handoff/CURRENT_TASK.md`
- `research/sprint_004/141_CEX002_ADR0020_INTEGRATION_AND_CANDIDATE.md`
- `tickets/CEX-002.md`

No report, fixture, ignored data, checkpoint, cache, journal, database sidecar, or unrelated
dirty path is part of this publication.

## 5. Stop point

Stop point: review-140 focused command 1 returned exit 1. CEX-002 remains `IN_PROGRESS`.
Gate 1 has not passed. Next ticket remains `NONE`.
