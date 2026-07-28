# REVIEW-0254 - EXP-009 CHANGES REQUIRED

**Decision:** CHANGES_REQUIRED
**Reviewer:** Sol 5.6 High
**Date:** 2026-07-28

## Findings

1. **Critical - terminal evidence is still partly caller-owned.**
   `recompute_holdout_statistics` derives weekly returns from the period equities, but
   applies the decision rule to `session_result.total_net_return` without proving that
   value equals the return implied by `initial_cash`, the final period equity, and
   `final_equity`. `_require_terminal_verdict_evidence` then compares only the supplied
   p-value, total return, and verdict. A sparse or forged bootstrap/decision block with
   those three matching values is accepted and serialized, and a fabricated total return
   can cross the +2% gate. Derive the terminal total return from the equity path, require
   all session total/final-equity representations to match within an explicit tolerance,
   and serialize or exact-match the complete recomputed frozen bootstrap and decision
   blocks for both ACCEPT and REJECT.
2. **High - dirty-source identity still under-covers the executing closure.**
   `EXP009_SOURCE_PATHS` contains only the experiment module, factor module, and CLI.
   Dirty first-party dependencies that determine membership, execution, risk, costs, or
   artifact bytes, including `universe/binding.py` and `execution/paper_loop.py`, can
   therefore execute while the declared HEAD identity passes. Use the established
   ARCH/DATA pattern: union the core static paths with repository-local Python modules
   actually loaded from `src/` and `scripts/`, then check that resolved closure.
3. **High - exploratory mode is broken after removing runtime override fields.**
   `run_exp009_preregistered_tsmom.py` still reads
   `runner.bootstrap_n_resamples` and `runner.bootstrap_mean_block_length`, but
   `EXP009Runner` no longer defines either field. A completed exploratory session raises
   `AttributeError` before artifact construction. Use the signed constants or the frozen
   bootstrap defaults and add a regression that reaches this post-session branch.

Exact UTC holdout timestamps, signed dataset pins, frozen runner economics, Monte Carlo
correction, holdout gating, and recomputation of the bootstrap p-value are otherwise
approved. The real prospective holdout remains sealed.

## Required Pass

Grok 4.5 should implement only the three corrections above. Opus 5 performs the
engineering pre-review; Sol 5.6 High performs one final quantitative acceptance review.
No real holdout run, parameter change, promotion, or LIVE work.

No Git or tests were run by the reviewer.

## Next

- **Next required actor:** Sr Dev - Grok 4.5
- **Engineering pre-review:** Opus 5
- **Final reviewer:** Sol 5.6 High
- **Next ticket authorized:** EXP-009 only
