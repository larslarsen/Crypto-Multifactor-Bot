# REVIEW-0024 - BIN-001 INTEGRATION: CHANGES_REQUIRED

**Ticket:** BIN-001 - Binance archive kline normalizer
**Integration reported at:** `d2ba2dc145bdebff59308bbc82d8bcc90c7f3379`
**Status:** CHANGES_REQUIRED (governance and gate evidence only)
**Next required actor:** Jr Dev - Hermes
**Date:** 2026-07-19

## Source review

The REVIEW-0023 v4 production drop is accepted for integration. It resolves the source
blocker without hidden repository access:

- `code_commit` is caller-supplied and required; empty and `unknown` are rejected;
- an explicit config hash is normalized and validated as 64-hex;
- an omitted config hash is deterministically derived from canonical,
  identity-bearing normalization configuration;
- the resulting `PublishPlan` uses the resolved code/config identities and publishes
  successfully in the focused catalog/store regression.

No further Sr Dev source work is currently required.

## Integration blockers

1. Jr changed `tickets/BIN-001.md` and `CURRENT_TASK.md` to `ACCEPTED` without a reviewer
   acceptance record. Reviewer acceptance is exclusive under `AGENTS.md`; owner or Jr
   completion cannot substitute for it.
2. The current focused test file contains 29 `test_*` functions, but the recorded exact
   focused gate says `25 passed`. That result cannot establish the current file passed.
3. The control-plane command is recorded as `python3 scripts/check_repo_control.py .`,
   not the ticket-exact `python3 scripts/check_repo_control.py`.
4. The change-report heading says the Sr drop was "ACCEPTED" before this reviewer
   decision and simultaneously labels the ticket `IN_PROGRESS`. Records must distinguish
   source integration readiness from final ticket acceptance.
5. Add one deterministic-config regression proving identical identity-bearing inputs
   produce the same derived hash and a changed normalization identity produces a
   different hash. The existing test proves only shape, not determinism/sensitivity.
6. Rename or remove `test_month_end_1M_closed_jan31_to_feb28`: its 2020 fixture and
   assertions correctly target February 29, so the current name is false.

## Authorized integration task - Jr Dev - Hermes

Do not modify production source. Restore and retain `IN_PROGRESS` until the reviewer
issues final acceptance. Correct the two focused test-record issues above, run every
command in `tickets/BIN-001.md` exactly as written against the current 29-plus test file,
and record the actual results. Change report language must say the Sr drop was integrated
and source-reviewed, not that Jr accepted the ticket. Record the actual immutable commit,
commit and push, then stop for final reviewer inspection.

## Disposition

BIN-001 remains `IN_PROGRESS`. Sr Dev attention is not required. Next ticket authorized:
`NONE`.
