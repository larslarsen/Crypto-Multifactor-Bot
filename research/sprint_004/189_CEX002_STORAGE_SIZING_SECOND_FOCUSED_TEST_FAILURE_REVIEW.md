# CEX-002 Storage-Sizing Second Focused Test Failure Review

**Date:** 2026-08-22  
**Reviewer:** Lead Quantitative Finance Researcher/Engineer  
**Decision:** `FAILED_TEST_SOURCE`; one bounded Spark correction authorized  
**Gate 1:** Accepted  
**Gate 2:** Not accepted; no sizing invocation occurred

## Reviewed execution

Hermes correctly integrated review 187 at commit
`f0e7b32fe577909137f89041305fc84286b75662`, pushed it, and stopped on the first
nonzero command. The commit contains exactly the accepted test correction, record 188,
and the two control records. `HEAD == origin/main` at that commit.

The focused test command exited status 1 after 2 seconds with 18 failures. Hermes ran no
later lint, control, sizing, network, or data-mutation command. Receipt 180 and the sizing
envelope tree remain absent. Production and CLI remain accepted at review-184 hashes; the
integrated 44-test path remains at review-187 SHA-256
`e7b7103cb36f83642762a91101be98ae368ba41b425f8a3e00711632895da6de`.

## Findings

### 1. High - the synthetic cohort does not represent its declared 12-family contract

The fixture uses `selected_rows[:10] + cost_rows[:2]`. `selected_rows` is ordered by
family, symbol, and interval, so the first ten rows cover only early families rather than
one sample from each archive family. Production correctly rejects the fixture with nine
missing physical families. This upstream fixture error accounts for the dominant repeated
failures, including the foreign-receipt case that never reaches receipt publication.

Select exactly one non-consumable row for each family in `PHYSICAL_FAMILIES` from the
combined selected and cost rows. Choosing a non-consumable daily-kline row is material:
the later retained-credit loop must not overwrite a cohort checkpoint with a different
synthetic payload.

### 2. Medium - the whole-file text scan confuses path joining with arithmetic division

The rational-comparison test scans every source line for the text `" / "` and therefore
rejects valid `path / child` expressions such as `Path(sample_dir) / digest`. Its dynamic
beyond-float-precision assertions already exercise exact cross multiplication. Restrict
the no-float/no-ordinary-division source assertion to the arithmetic helpers
`ratio_exceeds` and `ceil_div`; do not scan unrelated filesystem code.

### 3. Medium - the symlink test rejects an equally safe refusal path

The content-address target is a symlink outside the evidence root. Production refuses it
during target confinement with `a sizing envelope escapes its evidence root`, before the
descriptor hash can report `not a regular file`. Both are fail-closed `SizingError`
outcomes and the target remains untouched. Accept either exact safe message in this test.

No production failure was proved by record 188. Review 184's production/CLI acceptance
remains in force.

## Spark correction boundary

Implementation Dev - Codex Spark using GPT-5.3-Codex-Spark High is authorized to edit
only `tests/acquisition/test_binance_usdm_harmonic_sizing.py`:

1. build `cohort_rows` as exactly one non-consumable row per `PHYSICAL_FAMILIES` family
   from `selected_rows + cost_rows`;
2. restrict the static no-float/no-ordinary-division check to `ratio_exceeds` and
   `ceil_div`, preserving the dynamic beyond-`2**53` assertions; and
3. allow the symlink refusal regex to match either `not a regular file` or
   `escapes its evidence root`.

Spark preserves every other byte and all 44 `def test_` functions. It changes no
production/CLI byte, runs no test, linter, control, Git, network, sizing, or data command,
edits no repository record, returns the corrected test SHA-256, and stops for reviewer
inspection. Hermes restart is not yet authorized.

No sizing invocation, Gate-2 acceptance, bulk acquisition, normalization, catalog
publication, NautilusTrader, Harmonic Trader, payoff, PAPER, LIVE, paid-source,
reduced-scope, or next-ticket work is authorized. Next ticket remains `NONE`.
