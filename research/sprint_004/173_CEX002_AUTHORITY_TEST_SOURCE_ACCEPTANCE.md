# CEX-002 Authority Test Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/172_CEX002_AUTHORITY_FOCUSED_FAILURE_REVIEW.md`

## Accepted source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0` | accepted and frozen |

The test path contains 305 unique `test_` function definitions. Its diff contains only
review 172's five assertion corrections; the unrelated candidate-initialization and
quote-classifier tests are byte-restored. The reviewer ran no test, Ruff,
repository-control, network/data, transaction, migration, or ordinary qualification
command.

## Decision

**ACCEPT THE FIVE-ASSERTION TEST CORRECTION; AUTHORIZE HERMES TEST-ONLY INTEGRATION AND A
COMPLETE C1-C5 RESTART; DO NOT AUTHORIZE THE LIVE SOURCE-AUTHORITY TRANSACTION.**

The corrected assertions now name the accepted typed quote checks and errors, compare the
two exact cost-sample views without imposing a false order, and prove the CLI's public
correction call returns before store creation without requiring an intentionally
encapsulated helper call.

## Hermes integration and restart authorization

Jr Dev - Hermes first proves `HEAD == origin/main` at the commit publishing this review,
rehashes all three accepted paths, confirms the 305-test count, and confirms no CEX-002
qualification process is running. Any mismatch stops before staging.

Hermes stages only
`tests/acquisition/test_binance_usdm_harmonic_qualification.py`, verifies it is the sole
staged path, commits the exact correction, and pushes. It does not stage, revert, reset,
restore, delete, or otherwise mutate any unrelated dirty path.

After proving the integration commit is pushed and `HEAD == origin/main`, Hermes restarts
the complete sequence from C1:

```bash
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short
.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py
python3 scripts/check_repo_control.py
git diff --check
```

Hermes records each command verbatim, exit status, elapsed time, and material output. The
first nonzero status stops every later command. No retry or source/test edit is authorized.

## Publication and stop

Hermes writes `research/sprint_004/174_CEX002_AUTHORITY_TEST_INTEGRATION.md` with the
preproof, exact integration commit and push proof, command evidence through the first
failure or C5, final hashes/test count, and honest disposition. It updates both controls
to:

`Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 174`

Hermes stages exactly the two controls and record 174, commits, pushes, proves
`HEAD == origin/main`, and stops.

## Boundaries

No live `--apply-reviewed-v4-source-correction-only` invocation, data mutation,
source-data network operation beyond authorized Git pushes, ordinary qualification,
reservation reconciliation, report write, Gate-1 acceptance, sizing, Gate 2, bulk
acquisition, normalization, catalog publication, Nautilus work, Harmonic Trader work,
payoff analysis, PAPER, LIVE, paid source, reduced scope, or next-ticket work is
authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
