# CEX-002 Record-394 Diagnosis Correction and Evidence Stop

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept exact terminal/run facts; reject traversal diagnosis and incomplete command evidence; authorize evidence-only completion
- **Evidence actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted terminal and publication facts

The reviewer accepts commit `f85f079f1602d1b3aa20bd9402dabbf4300173b6` as a three-path
publication of record 394 and the final summaries. It accepts these exact facts:

- the single Review-393 continuation used runner `/tmp/cex002_v2_runner_c5Yg65`, shell PID/start
  ticks `516793/5000073`, planner PID/start ticks `516870/5000086`, start
  `2026-09-01T06:29:24Z`, end `2026-09-01T07:23:10Z`, and elapsed 53 minutes 46 seconds;
- the exact planner command exited 1 with stop `blocked` and stderr
  `ERROR: listing reachability or pagination authority drifted across independent passes`;
- the v2 checkpoint advanced from SHA-256
  `aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748` and 1,838
  pass-graph pages to SHA-256
  `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` and 4,187
  pass-graph pages;
- pass 1 is `listing_complete=true`, 1,308/1,308 completed/discovered prefixes, 2,093 pages,
  null cursor; pass 2 is `listing_complete=true`, 1,308/1,308 prefixes, 2,094 pages, null cursor;
- 3,755 unique retained physical page files exist; and
- no manifest, receipt, lineage, or locator was published; no planner is live; v1 and code
  identities remain unchanged; `HEAD == origin/main == f85f079f1602d1b3aa20bd9402dabbf4300173b6`;
  and staging is empty.

The eleven runner file identities in record 394 independently rehash exactly. The continuation is
consumed. No candidate, raw acquisition, Gate-2 result, transition, or later work is accepted.

## Correct diagnosis

Record 394's statement that each pass is incomplete because its final page remains truncated is
false and is rejected. Both pass states are complete with null cursors. The actual final graph
entry in each pass is the same null-token
`data/futures/um/daily/metrics/龙虾USDT/` page with `is_truncated=false` and no next token.

The first normalized graph difference is zero-based index 571 at
`data/futures/um/daily/metrics/BANKUSDT/`:

| Fact | Pass 1 | Pass 2 |
| --- | --- | --- |
| Ordinal-0 request key | `5e411e1d6028829f7b30e8283a071931cd0d87aa0c4f5034c688cca29e472bf9` | same |
| Retrieved at | `2026-09-01T05:33:13.925500+00:00` | `2026-09-01T06:50:36.399535+00:00` |
| Ordinal-0 response SHA-256 | `c23acb06b3bb7ea99ec71ae9a7ffbdb2c9055f8404efb7e7b6d341a7206a50b6` | `8c9bff1cbfaf8c402093a8552a327fbf7a3e8b7b41e81296d16430cfb0836f9d` |
| Ordinal-0 bytes | 358,315 | 358,502 |
| Ordinal-0 truncated | false | true |
| Ordinal-1 | absent | terminal, SHA-256 `404321383442456333713986485dd2a35ba926f195abea4047e6e3761ee763e9`, 1,209 bytes |

Pass 1's terminal page ended with the `BANKUSDT-metrics-2026-08-30.zip` and checksum objects.
Pass 2's additional terminal page contains exactly the newly published
`BANKUSDT-metrics-2026-08-31.zip` and checksum objects. The listing grew between independent
passes, crossed the 1,000-object page boundary, and changed a real page-count/truncation fact.
ADR-0032 therefore blocked exactly as specified. This is not an opaque-token false positive and
not an incomplete traversal.

The new objects are outside the already frozen generation-0 pending set. Requiring byte-stable
pagination shape for all unrelated live-family objects can therefore prevent an otherwise exact
pending-revision measurement from ever completing while Binance publishes new daily files. That
is an architecture question; no source correction or new run is authorized until a repository ADR
and reviewer authorization exist.

## Missing and incorrect publication evidence

Record 394 contains no repository-control or scoped-diff command, stream, or exit-code section,
although Review 393 required both. The Hermes terminal summary is ephemeral and cannot substitute
for repository evidence. Record 394's opening statement also says no planner launch or resume
occurred “during this continuation”; the accepted continuation did launch/resume the planner. The
correct claim is that no additional planner invocation occurred during terminal inspection and
publication.

The final actor fields and three-path commit are correct, but the missing command evidence and
false diagnosis require an append-only correction before architecture work.

## Evidence-only Hermes authorization

Hermes is authorized only to create
`research/sprint_004/396_CEX002_V2_DRIFT_DIAGNOSIS_AND_PUBLICATION_EVIDENCE_COMPLETION.md` and
update `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`.

Record 396 must preserve record 394 unchanged and contain:

- all accepted Review-395 runner, terminal, checkpoint, page-count, locator, v1/code, and Git
  facts without claiming a rerun;
- the exact corrected complete-pass and BANKUSDT first-difference diagnosis above;
- the distinction between the one accepted continuation and no additional publication-phase
  invocation;
- explicit disclosure that record 394 omitted both publication-command results;
- exact commands, stdout/stderr, and exit codes for the two fresh publication checks below; and
- a statement that no planner, network, SQLite, v1/v2/runner mutation, source/test edit,
  acquisition, cleanup, transition, ADR decision, or later work occurred.

Before repository control, Hermes must set both literal top-level fields to the reviewer and both
summaries must state the corrected terminal diagnosis, this evidence-only completion, and that no
retry/resume/source/architecture/acquisition/transition work is authorized. Hermes then runs only:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/396_CEX002_V2_DRIFT_DIAGNOSIS_AND_PUBLICATION_EVIDENCE_COMPLETION.md tickets/CEX-002.md
```

If both exit zero, Hermes stages exactly record 396 plus the two control-plane paths, verifies no
other staged path, commits, pushes `main`, proves `HEAD == origin/main`, and stops. Record 394,
candidate/runner bytes, source/test, and every unrelated dirty path remain unchanged and unstaged.
Harness output is a handoff only.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/395_CEX002_RECORD394_DIAGNOSIS_CORRECTION_AND_EVIDENCE_STOP.md`; and
- `tickets/CEX-002.md`.

No implementation/evidence record, candidate/runner/data, source/test, acceptance command, or
unrelated dirty path is included in this reviewer publication.
