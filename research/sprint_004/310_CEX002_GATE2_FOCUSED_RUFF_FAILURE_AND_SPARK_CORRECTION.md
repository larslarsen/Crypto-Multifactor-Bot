# CEX-002 Gate-2 Focused Ruff Failure and Spark Correction

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** focused Ruff failure accepted; exact mechanical cleanup authorized
- **Authorized actor:** Implementation Dev - Codex Spark
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted validation stop

Hermes passed the corrected reviews 308-309 preproof, then ran the first authorized offline
command exactly once:

```text
.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py scripts/research/acquire_binance_usdm_harmonic_release.py tests/acquisition/test_binance_usdm_harmonic_acquisition.py
```

It ran from `2026-08-27T00:05:04.452351098Z` through
`2026-08-27T00:05:04.543542611Z`, completed in 0.091 seconds, and exited 1 with exactly three
findings:

1. unused `EXIT_UNSAFE_STATE` import in the CLI at line 18;
2. unused `dataclasses.replace` import in the acquisition source at line 33; and
3. unused `content_inode` assignment in the acquisition source at line 7448.

Hermes correctly stopped. The remaining three validation commands did not run, no execution
record was created, and no source, staging, commit, push, or other mutation occurred.

## Static diagnosis

All three findings are dead-code cleanup. The CLI uses its own `dataclasses.replace` import at
line 72, so that import remains. The acquisition module does not call its imported
`dataclasses.replace`. The local `content_inode` value is never read; retained inode validation
uses the authenticated revision and a separately obtained destination stat. Removing these
three unused bindings changes no acquisition, recovery, receipt, validation, or exit semantics.

## Spark source authorization

Spark may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`

Make exactly these edits:

1. remove `EXIT_UNSAFE_STATE` from the CLI's acquisition-module import list;
2. change the acquisition source import from `dataclass, field, replace` to
   `dataclass, field`; and
3. delete only `content_inode = int(os.fstat(fd).st_ino)` from
   `validate_provider_completion`.

Preserve every other byte, including the CLI's `from dataclasses import replace`, all tests,
and all unrelated dirty work. Do not add a replacement binding or refactor surrounding code.
Run no test, Ruff, control, plan, acquisition, verify, network, data, Git, commit, push, or
repository-record operation. Stop with both SHA-256 hashes and line counts and confirm only the
two authorized paths changed.

Hermes integration and all validation commands remain unauthorized until reviewer inspection
of the exact Spark return. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
