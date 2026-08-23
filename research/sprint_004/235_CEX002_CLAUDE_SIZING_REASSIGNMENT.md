# CEX-002 Claude Sizing Reassignment

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** Reassign review 234 unchanged because Grok Build is unavailable
- **Authorized actor:** Sr Dev - Claude Build
- **Superseded actor:** Sr Dev - Grok Build

## Reason

The owner reports that Grok Build is on cooldown and cannot start the authorized drop.
Review 234 is already a complete architecture and financial-semantics contract, so no
design change or new review slice is warranted. Claude Build is the only available formal
senior source actor capable of the bounded work. This is an availability reassignment,
not acceptance of Claude's rejected review-233 bytes.

## Exact authorization

Sr Dev - Claude Build inherits review 234 in full and may edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`;
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`;
3. `scripts/research/size_binance_usdm_harmonic_release.py`.

Claude works from the current shared three-path drop in place. It must not reset, restore,
checkout, discard, or wholesale replace those files. It closes every section A-G and all
ten test requirements in review 234 as one complete correction. Review 234's preservation,
scope, source-authoring, command, test, Git, evidence, data, and stop conditions remain
unchanged.

Grok Build is no longer authorized for this drop. No second senior actor may work
concurrently. Claude stops once with SHA-256 for all three allowed paths, explicitly marks
an unchanged path, and reports the final `test_` function count. No integration actor is
authorized until reviewer static acceptance. Gate 2 remains blocked, acquisition remains
unauthorized, and next ticket remains `NONE`.

## Reviewer publication scope

Under the AGENTS.md reviewer exception, the reviewer may stage, commit, and push exactly:

- `research/sprint_004/235_CEX002_CLAUDE_SIZING_REASSIGNMENT.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`.

The three developer paths and all unrelated dirty work are excluded.
