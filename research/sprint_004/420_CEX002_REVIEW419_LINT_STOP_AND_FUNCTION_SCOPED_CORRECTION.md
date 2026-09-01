# CEX-002 Review 420 — Review 419 Lint Stop and Function-Scoped Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the safe stopped state; supersede the ambiguous correction with two function-scoped edits
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

Review 419's literal-text deletion was under-specified because the same `key` assignment occurred
in two adjacent test functions. Sol deleted the first occurrence, which was used, instead of the
second occurrence reported unused by ruff. Sol then ran the one authorized ruff command, received
F821 at line 213 and F841 at line 221, and stopped without another edit or command. No pytest,
Git, network, real data/state, runner, output, integration, acquisition, cleanup, or other-path
work occurred.

The current unintegrated identities are:

- `src/cryptofactors/ingest/binance_usdm_open_interest.py`: 1,432 lines, SHA-256
  `c2b8835445036359e870cb6a3fa77907bc9ec766a2e1da355ef837e7c22a70d8`;
- `scripts/research/normalize_binance_usdm_open_interest.py`: 53 lines, SHA-256
  `33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675`;
- `tests/ingest/test_binance_usdm_open_interest.py`: 439 lines, SHA-256
  `389dbb62c4864510b8f440a6bed21b363e7569f385a578d53281885326241c8b`.

Sr Dev — Codex Sol on GPT-5.6-sol High is authorized to make exactly these two test-source edits,
identified by function rather than duplicated text:

1. In `test_unsafe_zip_member_paths_are_rejected`, immediately before the existing `payload =`
   statement, restore:

   ```python
   key = "data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-07-01.zip"
   ```

2. In `test_symlink_and_multi_member_zips_are_rejected`, delete its unused assignment of that same
   string, currently between `from io import BytesIO` and `target = BytesIO()`.

After both edits, Sol may run this exact command once:

```bash
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_open_interest.py scripts/research/normalize_binance_usdm_open_interest.py tests/ingest/test_binance_usdm_open_interest.py
```

Sol stops on any nonzero result without patching or rerunning and otherwise stops for reviewer
inspection with exact hashes and line counts. No other edit, pytest, real data/state, runner,
integration, repository record, Git, network, acquisition, cleanup, or other product is
authorized.

Under the reviewer governance-publication exception this review commits and pushes exactly:

- `research/sprint_004/420_CEX002_REVIEW419_LINT_STOP_AND_FUNCTION_SCOPED_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer and unrelated dirty paths remain unstaged.
