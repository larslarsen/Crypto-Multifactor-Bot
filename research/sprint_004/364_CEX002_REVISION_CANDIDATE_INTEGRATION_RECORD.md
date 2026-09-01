# CEX-002 Revision-Candidate Integration Record

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact Review-363 corrected drop integrated and validated; all four commands exit 0
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Durable integration disposition

Hermes rehashed the six Review-363 identities, confirmed every SHA-256 and line count, staged exactly those six paths, ran the exact four validation commands, and recorded the results in this durable record. The harness output is a handoff aid only; this record and the control plane are the repository evidence.

## Rehashed identities (all match Review 363)

| Path | SHA-256 | Lines |
|---|---|---|
| `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py` | `b8c60212ababc9f620afcf71725cac00f9f2893408f3f12f5fb947670cd03e86` | 5,084 |
| `scripts/research/plan_binance_usdm_gate2_revision_candidate.py` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` | 87 |
| `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py` | `065e6a229c58c72b6b7a90ad27aa806c4cf3afc729321066f65644f6090795c1` | 2,519 |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_book_ticker_page.xml` | `dd53323a7fcab0c39c8dd8d4824446fddc95b993c44671ead27144b064d84569` | — |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_metrics_page.xml` | `d96c6713a29694264d5f3232bc04e085840b19d96d7f673e246ed36f473c5947` | — |
| `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/sidecar_btc_metrics.CHECKSUM` | `6dd7148990cd11f7b30e8de9bedd0fea88338c718ab20e3c1c58ee9238abbf55` | — |

The corrected test prerequisite assertion `assert complete["exit_code"] == planner.EXIT_COMPLETE` is present at line 1095, immediately after `complete = _run(...)` at line 1094. All production, CLI, and fixture bytes are byte-identical to Review 361.

## Staged path list (exactly six developer paths)

```
scripts/research/plan_binance_usdm_gate2_revision_candidate.py
src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py
tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_book_ticker_page.xml
tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/listing_metrics_page.xml
tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/sidecar_btc_metrics.CHECKSUM
tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

No other path is staged. All unrelated dirty paths remain present and unstaged.

## Validation commands and exact outputs

### Command 1: targeted pytest

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Output:

```text
........................................................................ [ 66%]
.....................................                                    [100%]
109 passed in 37.43s
```

Exit code: **0**. 109 collected cases, all passed, no warning output.

### Command 2: targeted ruff

```text
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

Output:

```text
All checks passed!
```

Exit code: **0**. The prior `F841` finding is resolved by the Review-363 prerequisite assertion.

### Command 3: repository control

```text
python3 scripts/check_repo_control.py
```

Output:

```text
Repo control check: PASS
```

Exit code: **0**.

### Command 4: scoped diff check

```text
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py scripts/research/plan_binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate docs/handoff/CURRENT_TASK.md research/sprint_004/364_CEX002_REVISION_CANDIDATE_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Output: (empty — no conflict markers or whitespace errors)

Exit code: **0**.

## Repository transition

After all four commands exited zero, Hermes created this record, updated `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` exactly as authorized, staged exactly the six developer paths plus this record and those two control-plane files, verified no other staged path, committed, pushed `main`, and proved `HEAD == origin/main`.

No developer byte was patched. No unrelated dirty path was touched. No real planner, listing, state/data access, acquisition, cleanup, migration, generation transition, later gate, or next-ticket work was performed. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.
