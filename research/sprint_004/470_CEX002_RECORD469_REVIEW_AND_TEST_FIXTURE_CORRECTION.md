# CEX-002 Review 470 - Record 469 Review and Test-Fixture Correction

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept Hermes's stop and authorize one exact Grok test-fixture correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - four of eleven required products accepted
- **Next required actor:** Sr Dev - Grok Build on Grok 4.6 High
- **Next ticket:** `NONE`

## Disposition

Review 470 accepts Record 469's execution facts. Hermes correctly stopped at the first ordered
command after 64 passing cases and one failing case. Ruff, repository control, integration, Git
publication of developer paths, and the real run did not occur. The hidden output root remains
absent; no data was downloaded or mutated. `HEAD == origin/main ==
c235633fbea1959b47fd4e30706d8462cc3ff845`.

The failure is a test-fixture defect, not a production or data defect. In
`test_missing_or_nonpositive_sidecar_bytes_fail`, the first two `_authenticate(...)` calls write
the content-addressed sidecar before production rejects the deliberately nonpositive recorded byte
count. The final case reuses the same `tmp_path`, body, digest, and path with `write=False`; that
flag prevents a new write but does not remove the sidecar already created by the first two cases.
Production therefore finds and correctly authenticates an existing file, while the test incorrectly
expects a missing-file exception.

The accepted production source, CLI, and all financial, authority, memory, and publication
semantics remain unchanged.

## Exact correction

Sr Dev - Grok Build on Grok 4.6 High may modify only
`tests/ingest/test_binance_usdm_funding_realized.py`. Immediately before the final missing-sidecar
assertion, the test must unlink the exact previously created `path` and prove it is absent. It then
calls the existing `_authenticate(..., write=False)` assertion unchanged. No production helper,
expected exception, earlier case, or other test behavior changes.

The following paths are frozen at their accepted identities:

- production: `src/cryptofactors/ingest/binance_usdm_funding_realized.py`, SHA-256
  `4e38658f89905e1f5b66b739eb8f58e2f66ce204b9c61cfbfa7cb0ed161acada`, 1,404 lines;
- CLI: `scripts/research/normalize_binance_usdm_funding_realized.py`, SHA-256
  `05e30c8712608e4895749114375a9b38ea5cf868870d913ddef5d264f77d7b2b`, 50 lines.

Under the targeted senior test exception, Grok may execute exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short
```

Grok stops on any nonzero result without patching or rerunning and reports the exact result plus the
corrected test line count and SHA-256. It performs no production/CLI edit, real-data run,
integration, Git, record/control edit, data mutation, acquisition, network access, cleanup, other
product, catalog transaction, experiment, model, Harmonic Trader work, PAPER, LIVE, or next-ticket
work. Hermes remains unauthorized pending reviewer inspection of the exact corrected test.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review publishes exactly:

- `research/sprint_004/470_CEX002_RECORD469_REVIEW_AND_TEST_FIXTURE_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer source/test/CLI, data, runner, acceptance-command, and unrelated dirty paths remain
unstaged and untouched.
