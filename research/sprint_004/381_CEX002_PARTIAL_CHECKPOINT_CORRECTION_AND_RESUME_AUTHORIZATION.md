# CEX-002 Partial-Checkpoint Correction and Resume Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** correct record 380's pass disposition; authorize one bounded continuation of the existing revision candidate
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewer finding

Record 380 is accepted as evidence that Hermes invoked the authorized planner exactly once, the
process exited 124 after the harness timeout, a partial candidate was durably published, and none
of the prohibited raw-acquisition or generation-transition actions occurred. Its narrative claim
that pass_1 completed is rejected and superseded by this review. Record 380's own exact checkpoint
fields say `listing_complete=false`, 484 completed prefixes, 1,308 discovered prefixes, and a
non-null cursor for pass_1. `CURRENT_TASK.md` and CEX-002 repeated the same false completion claim.

The reviewer performed bounded read-only JSON, file-identity, source, process, and Git inspection.
No real or candidate SQLite database was queried, no candidate byte was mutated, and no command
was invoked against generation 0. The existing candidate identities remain:

- checkpoint SHA-256
  `de0527f99bbf24463d8bdc774e5cf51f356aeb14d7ee5b821d0e9384dc6152b3`,
  1,261,084 bytes;
- temporary SQLite SHA-256
  `da438ce8b812e67647d02d0451e0187f185309d1f83b4646083f47b34d5a81d1`,
  163,332,096 bytes; and
- 640 retained content-addressed listing pages, with no manifest, receipt, lineage asset, or
  completed locator.

The exact durable progress is:

| Pass | Complete | Completed prefixes | Discovered prefixes | Pages | Cursor |
| --- | --- | ---: | ---: | ---: | --- |
| `pass_1` | false | 484 | 1,308 | 640 | `data/futures/um/daily/metrics/BNXUSDT/`, null token |
| `pass_2` | false | 0 | 2 | 0 | `data/futures/um/daily/bookTicker/`, null token |

Each independent pass owns both fixed family roots. Pass_1 has completed all 316 currently
discovered bookTicker prefixes and 168 of 992 currently discovered metrics prefixes; its 640
pages comprise 316 bookTicker and 324 metrics pages. Pass_2's two discovered roots are initial
checkpoint state, not evidence of a ListObjectsV2 request. It has not started network listing.

Static inspection confirms the accepted implementation reconstructs each pass from retained,
rehash-authenticated pages, rebuilds its private index from that graph, fetches only the sorted
`discovered - completed` set, and then executes the second independent pass. The partial state is
therefore an ordinary resumable interruption, not an acquisition blocker and not evidence of a
source defect.

## Runtime basis

The retained pages span `2026-09-01T01:04:43.011940+00:00` through
`2026-09-01T01:19:27.463895+00:00`: 640 pages in about 884 seconds, or about 1.38 seconds per page.
Using the completed metrics prefixes' observed pagination rate and the required second stable
pass gives an operational estimate of roughly 90 to 150 minutes remaining, including local graph
reconstruction and final publication. This is a scheduling estimate, not an acceptance fact; S3
latency, retries, or listing drift can extend or block the run. The execution session is therefore
given a four-hour wall-clock allowance and must not impose the prior short harness timeout.

## One exact continuation authorized

Hermes is authorized for exactly one invocation of:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Before invocation, Hermes must read `AGENTS.md`, `CURRENT_TASK.md`, CEX-002, ADR-0031, and records
379-381; prove `HEAD == origin/main` at this review's publication commit; prove staging is empty;
prove no revision-candidate planner is running; rehash the accepted production, CLI, and test
paths; and prove the existing checkpoint identity above. Any mismatch stops before invocation and
is recorded.

The command must run once in one long-lived execution session with a wall-clock allowance of at
least four hours. If the command tool returns a live session identifier, Hermes must poll that
same session until it terminates; it must not launch a duplicate process. Exit 0, 1, 2, 6,
another nonzero exit, or an external interruption all end the single invocation. There is no
second resume in this assignment.

The invocation may authenticate and resume only the existing fixed sibling candidate, query-only
authenticate generation 0, reuse only authenticated retained listing pages, and make only missing
official Binance S3 ListObjectsV2 requests for the two fixed family prefixes in the two independent
passes. It may publish only the planner's candidate checkpoint/pages/tmp/manifest/receipt/lineage/
locator outputs. It may not GET a raw ZIP, invoke acquisition, use Coinalyze, edit active generation
0, select a subset, delete/clean/replace the candidate, patch source/tests, start a generation
transition, or authorize a later gate.

## Mandatory record 382 and stop

After the process reaches its one terminal result, Hermes must publish exactly
`research/sprint_004/382_CEX002_REVISION_CANDIDATE_RESUME_RECORD.md`. It must preserve the original
run and checkpoint history and report:

- exact preflight HEAD/origin, staging, process, code-hash, and checkpoint-hash facts;
- exact start/end UTC, command, execution-session wall-clock allowance, exit code, stdout, and
  stderr for the single continuation;
- whether the retained checkpoint was resumed rather than replaced and exact before/after
  checkpoint/page identities and per-pass progress;
- for completion, every bounded semantic, count, byte-equation, listing stability, manifest,
  receipt, lineage, locator, capacity, code, and generation identity required by Review 379;
- for any incomplete or blocked result, the exact refusal/terminal condition and durable partial
  state; and
- explicit confirmation that the result accepts no revision and authorizes no raw acquisition or
  transition.

Hermes may inspect planner-produced files with bounded read-only stat/hash/JSON operations after
the command. It may not directly query active or candidate real SQLite outside the integrated
planner invocation.

Before repository control, Hermes must set these literal final fields:

```text
Next required actor: Lead Quantitative Finance Researcher/Engineer
**Next required actor:** Lead Quantitative Finance Researcher/Engineer
```

It must update the final summaries with the exact outcome, keep CEX-002 and Gate 2 `IN_PROGRESS`,
keep next ticket `NONE`, then run exactly:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/382_CEX002_REVISION_CANDIDATE_RESUME_RECORD.md tickets/CEX-002.md
```

Record 382 must contain the commands' exact outputs and exit codes with Hermes attribution.
Hermes stages exactly those three paths, verifies no other path is staged, commits, pushes main,
proves `HEAD == origin/main`, and stops. Candidate data and unrelated dirty work remain unstaged.
Harness output is a handoff aid only; the repository record is authoritative.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/381_CEX002_PARTIAL_CHECKPOINT_CORRECTION_AND_RESUME_AUTHORIZATION.md`; and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, candidate data, acceptance command, or
unrelated dirty path is included in this reviewer publication.
