# CEX-002 Authority Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing review: `research/sprint_004/166_CEX002_CLAUDE_AUTHORITY_TEST_REVIEW.md`

## Accepted source identities

| Path | SHA-256 | Decision |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bed5ab4a9d18ed0cb7410d8efc58b6a6fdb88153a68c03ae409494358d48fac7` | accepted and frozen |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` | accepted and frozen |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `4a9602d7247c0b211dd21925f724ec5e22d529646b71c77cbd529ad7d59a9fef` | accepted and frozen |

The accepted test path contains 305 unique `test_` function definitions. The reviewer ran
no test, Ruff, repository-control, network/data, transaction, migration, or ordinary
qualification command.

## Decision

**ACCEPT THE COMPLETE THREE-PATH SOURCE DROP; AUTHORIZE HERMES INTEGRATION AND FOCUSED
COMMAND EXECUTION; DO NOT AUTHORIZE THE LIVE SOURCE-AUTHORITY TRANSACTION.**

Spark's review-166 correction constructs the nonempty mixed accounting fixture from a real
settled charge, makes the altered-accounting state a genuine self-consistent mutation,
uses the exact full-ledger rejection, and proves every requested rejected public apply is
byte-nonmutating. Production and CLI stayed exact, and the test count stayed 305.

The accepted production source now implements ADR-0020 section 4b's quote semantics,
membership coverage, source-versus-release blocker separation, derived-flow inheritance,
and the exact one-shot source-authority state machine. Source acceptance is complete.
Integration evidence is not. ADR-0020 keeps integration and the live transaction as
separate reviewer gates, so this authorization stops after commands and publication.

## Hermes integration authorization

Jr Dev - Hermes must first prove `HEAD == origin/main` at the commit publishing this
review, rehash all three accepted paths, confirm the 305-test count, and confirm no CEX-002
qualification process is running. Any mismatch stops before staging.

Hermes stages only the three accepted Python paths above, verifies the staged path list is
exact, commits them as one CEX-002 source integration, and pushes. It must not stage,
revert, reset, restore, delete, or otherwise mutate any unrelated dirty path, data file,
database sidecar, DEX work, BitMEX work, catalog work, configuration, or reviewer record.

After the exact integration commit is pushed and `HEAD == origin/main`, Hermes runs this
stop-on-first-failure sequence from the repository root:

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

Hermes writes `research/sprint_004/168_CEX002_AUTHORITY_SOURCE_INTEGRATION.md` with the
preproof, exact integration commit, pushed-head proof, command evidence, final source
hashes/test count, and honest disposition. It updates only both control files to:

`Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 168`

Hermes stages exactly the two controls and record 168, commits, pushes, proves
`HEAD == origin/main`, and stops. This publication occurs after either complete command
success or the first failure.

## Boundaries

No live `--apply-reviewed-v4-source-correction-only` invocation, data mutation,
source-data network operation beyond the authorized Git pushes, ordinary qualification,
reservation reconciliation, report write, Gate-1
acceptance, sizing, Gate 2, bulk acquisition, normalization, catalog publication, Nautilus
work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced scope, or
next-ticket work is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
