# CEX-002 V2 Stable Capacity Residual Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** review-244 drop rejected on one stable-capacity residual
- **Authorized actor:** Sr Dev - Claude Build
- **Integration actor after source acceptance:** NONE
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Reviewed drop

The reviewer inspected Claude Build's complete review-244 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `6126a24a5f7636c14cf6d3d968eabca6b6d09f346922a3b122216c9ee3957067` |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `a2dda4458ae3549f87e759d1910bb2d0c5e78cc94de19253f63c257e3505e940` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The test file has 139 functions. No reviewer pytest, Ruff, sizing, qualification, control,
acceptance, network, or data command was run.

## Accepted correction

Preserve the drop in place. Static review accepts:

- canonical stable projection of measured in-memory structures and decoded JSON;
- one named stable-mismatch boundary used by prior-receipt revalidation;
- continued canonical-byte and complete internal-wholeness proof of the prior receipt;
- a semantic distinct content-addressed envelope count independent of write/reuse outcomes;
- unchanged fixed-target collision, no-follow, race, tamper, and v1 protections;
- exact six-component capacity arithmetic and the ADR-0024 three-way temporary maximum;
  and
- removal of the invalid temporary-versus-final-storage ordering assumption.

## One residual blocker

`capacity.equation` is fixed receipt policy prose, not a sizing-time observation or a
derivative of one. The drop places it in `VOLATILE_CAPACITY_FIELDS`, while
`_prior_receipt_is_whole` validates only the numeric equation and never validates this
string. A prior receipt can therefore change `capacity.equation` to arbitrary canonical
text and still pass both the stable projection and internal-wholeness checks. That weakens
the existing tamper/collision contract.

Make the minimal correction:

1. classify `capacity.equation` as stable and compare it exactly through the same stable
   projection and named mismatch path;
2. leave only `operating_reserve_bytes` and `total_future_storage_bytes` in the volatile
   capacity set;
3. make the focused projection test prove a changed equation returns
   `capacity.equation`; and
4. preserve every other review-244 source/test change byte-for-byte except directly
   required formatting.

Do not replace the equation with recomputed prose, omit it, or move collision refusal.

## Exact Claude authorization and stop

Claude may edit only the sizing production and sizing test paths. Leave the sizing CLI
byte-identical. Work from the shared drop in place without reset, restore, checkout,
discard, or wholesale replacement. Do not run commands/tests, use Git, mutate data or
evidence, or edit repository records. Stop once with all three path SHA-256 values and the
final `test_` function count.

Sol, Grok, Spark, Hermes, integration, and execution remain unauthorized pending reviewer
source acceptance. Gate 2 remains not accepted; acquisition and later work remain
unauthorized; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `research/sprint_004/245_CEX002_V2_STABLE_CAPACITY_RESIDUAL_REVIEW.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test/CLI paths and unrelated dirty work are excluded.
