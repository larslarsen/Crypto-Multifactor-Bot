# CEX-002 Sizing-Correction Focused Failure

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `SOURCE_DIRECTION_ACCEPTED_FOUR_CORRECTIONS_REQUIRED`
**Architecture:** ADR-0021 as amended by ADR-0022
**Gate 1:** Accepted
**Gate 2:** Not accepted

## Reviewed drop

Claude edited exactly the two review-219 paths:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `e16c54538f7efaded0c99026b06e9734d850129b7d0aa28b4cad2ef843205392` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `fe40597b438f9429d5acd831ec60eb8abd795d868f1c04dc325d0ab1584a28ee` |

The test source contains 55 `def test_` functions. The sizing CLI remains byte-identical
at accepted SHA-256 `78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.

Static review accepts the implementation direction. All accepted authority identities are
advanced correctly. The credit domain is selected plus cost requirements, report-declared
ambiguous recovered rows are excluded, recovered rows receive an independent path-binding
check, every credited object and sidecar is rehashed, and logical keys, unique digests,
and unique bytes are separately accounted. The receipt carries the new decomposition.

## Reviewer validation

Under the owner's standing focused-validation authorization, the reviewer ran:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short
```

The suite completed in 3.1 seconds with 3 failures and 92 passes across 95 collected
cases. The reviewer then ran exact-path Ruff over sizing production, the frozen CLI, and
the sizing tests; Ruff passed. Restricted whitespace validation also passed.

The three failures form one bounded correction batch:

1. `test_a_missing_rejected_entry_blocks` correctly receives `SizingError`, but its regex
   expects the later accepted-count field rather than the earlier per-location count
   mismatch. This is a test expectation defect, not a failure to block.
2. `test_damaged_retained_evidence_blocks_before_any_publication[wrong_byte_size]` exposes
   a production omission. `verify_retained_object()` proves the retained bytes but does
   not compare the checkpoint's declared `byte_size`; the previous sizing implementation
   performed that explicit comparison. It must be restored for every credited key.
3. `test_the_receipt_publishes_the_adr0022_credit_decomposition` treats `_run()` as the
   receipt although the established helper returns the result wrapper. The test must read
   `_run(...)["receipt"]`.

One static acceptance gap belongs in the same correction: the exact report is hash-pinned,
but the consumer should explicitly prove its accepted retained-summary values before
measurement. This makes those receipt authorities visible and keeps the synthetic tests
honest instead of relying only on the whole-report digest.

## Claude correction authority

Sr Dev - Claude Build is authorized to edit only the same two sizing production/test
paths and make exactly these four corrections:

1. After `verify_retained_object()` returns a size for a credited key, require the
   checkpoint `byte_size` to be a non-boolean integer equal to that actual size. Missing,
   non-integer, Boolean, zero/negative, or unequal values fail closed before credit or
   publication. Do not count this as merely unverified and continue.
2. Make `test_a_missing_rejected_entry_blocks` assert `SizingError` without depending on
   the later-field regex, or match the actual earlier fail-closed field. Preserve the
   report mutation and blocking premise.
3. Make the receipt-decomposition test unwrap `_run(...)["receipt"]`; preserve all of its
   decomposition assertions.
4. Explicitly compare the pinned report's
   `storage.gate2_feasibility.retained_valid_requirement_keys`,
   `retained_verified_credit_objects`, `retained_verified_credit_bytes`,
   `unverified_retained_objects`, and `rejected_retained_row_count` with the accepted
   constants before retained proof or envelope publication. Add a focused parameterized
   test showing each independently altered summary field blocks. Keep the existing proof
   that the two rejected-key locations and their counts agree.

Preserve every other review-219 change and test. Do not weaken evidence verification,
alter accepted counts, change the candidate/release domain through caller input, or add a
network, credential, policy, or authorization surface.

Claude runs no pytest, Ruff, control, sizing, qualification, network, data mutation, Git,
commit, push, record, or control operation. Return both exact SHA-256 hashes and the new
test-function count, then stop. The reviewer will rerun the complete focused suite and
exact-path Ruff.

## Stop boundary

Hermes and sizing execution remain unauthorized. No bulk acquisition, normalization,
catalog publication, NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, paid
source, reduced scope, or next-ticket work is authorized. Gate 2 remains unaccepted and
next ticket remains `NONE`.
