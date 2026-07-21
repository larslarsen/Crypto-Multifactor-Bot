# FX-002 - JR COMMAND EVIDENCE CLOSURE TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes, tool-executing model required
**Status:** COMPLETED
**Next ticket:** `NONE`

## REVIEW-0088 Clarification

The original instructions to reproduce each regex inside the searched report were self-matching.
Do not reproduce or obfuscate either command in the report. Cite this task and record only each
command's observed output and exit status.

`pyproject.toml` supplies `addopts = "-q"`, so the required pytest command runs at effective `-qq` and
may legitimately suppress its final summary. Record its exit status. Then run the supplementary
single-quiet command specified below to obtain the literal summary.

## Scope

Do not perform network requests, change source conclusions, or add implementation artifacts. The
`NONE` source recommendation is accepted substantively under REVIEW-0087. Complete only the exact
record cleanup and command evidence below.

## Record Cleanup

1. Replace `rate_direction: N/A` in `research/fx_002/sources/coinmetrics.md` with
   `rate_direction: NOT_APPLICABLE: no price data returned`.
2. Replace `rate_direction: N/A` in `research/fx_002/sources/defillama.md` with
   `rate_direction: NOT_APPLICABLE: current snapshot was rejected before historical rate use`.
3. Remove the fabricated pytest progress/output and the `100 passed in 0.20s` line from the report.
4. Do not edit provider hashes, URLs, statuses, classifications, or the `NONE` recommendation.

## Exact Preflight

Run exactly:

`rg -n '07:xx|\(from sprint|\(capture|\(size\)|~0|^CSV$|^cat research|actual output from run|tests passed with|standard warning' research/fx_002 docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md`

Do not copy this regex into the report. Record `First preflight: no matches; exit status 1` only if
that is what the command actually returns.

Then run:

`rg -n 'N/A|\(approx\)|100 passed in 0\.20s' research/fx_002 docs/reviews/FX-002_SOURCE_FEASIBILITY_REPORT.md`

Do not copy this regex into the report. Record `Second preflight: no matches; exit status 1` only if
that is what the command actually returns.

## Exact Acceptance Commands

Run exactly:

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Record the literal control output and exit status 0. For the required pytest command, record exit
status 0 and that effective `-qq` suppressed the summary; any nonzero status fails the gate.

Then run this supplementary command exactly:

`PYTHONPATH=src uv run pytest -q --tb=short -o addopts=`

This clears the configured extra `-q`, leaving one quiet flag. Record its literal final summary line
and exit status 0. Do not invent, estimate, paraphrase, or copy a prior result.

## Records And Stop Condition

- Mark the archive-path task `FAILED - REVIEW-0087` and this task `COMPLETED` only after both scans and
  all three command runs meet their required outcomes.
- Set FX-002 to `AWAITING_REVIEW` consistently in ticket, README, backlog, report, and handoff.
- Name Reviewer as next actor, retain `Next ticket authorized: NONE`, commit, push, and stop.
