# CEX-002 V2 Drift Diagnosis and Publication Evidence Completion

- **Date:** 2026-09-01
- **Actor:** Jr Dev - Hermes
- **Ticket:** CEX-002
- **Review:** 395
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted terminal, runner, checkpoint, and Git facts

Record 394's terminal, runner, checkpoint, pass/page, no-locator, v1/code, and Git facts are accepted without change and are restated here without claiming any rerun. All runner-file identities rehash exactly as published in record 394. No candidate, raw acquisition, Gate-2 result, transition, or later work is accepted.

- Runner: `/tmp/cex002_v2_runner_c5Yg65`, shell PID/start ticks `516793/5000073`, planner PID/start ticks `516870/5000086`, start `2026-09-01T06:29:24Z`, end `2026-09-01T07:23:10Z`, elapsed 53 minutes 46 seconds
- Command: `PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py`
- Exit code: `1`, stop `blocked`, stderr `ERROR: listing reachability or pagination authority drifted across independent passes`
- v2 checkpoint advanced from SHA-256 `aaaaf68a0f0f132d086140f66f6526905f70eaf5c2cc31c35c51431e3ffc6748` / 1,838 pages to SHA-256 `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` / 4,187 pages
- Pass 1: `listing_complete=true`, 1,308/1,308 prefixes, 2,093 pages, null cursor
- Pass 2: `listing_complete=true`, 1,308/1,308 prefixes, 2,094 pages, null cursor
- 3,755 unique retained physical page files
- No manifest, receipt, lineage, or locator was published
- No planner is live; v1 and code identities remain unchanged
- `HEAD == origin/main == 4dc451a53c6e38022b3a9344067af826cdcfcc7c`; staging is empty
- No planner launch, resume, replacement, raw ZIP GET, v1 mutation, source/test edit, cleanup, acquisition, transition, or later work occurred during this publication

## Corrected complete-pass BANKUSDT page-boundary diagnosis

Record 394's claim that each pass is incomplete because its final page remains truncated is false. Both pass states are complete with null cursors. The actual final graph entry in each pass is the same null-token `data/futures/um/daily/metrics/龙虾USDT/` page with `is_truncated=false` and no next token.

The first normalized graph difference is zero-based index 571 at `data/futures/um/daily/metrics/BANKUSDT/`:

| Fact | Pass 1 | Pass 2 |
| --- | --- | --- |
| Ordinal-0 request key | `5e411e1d6028829f7b30e8283a071931cd0d87aa0c4f5034c688cca29e472bf9` | same |
| Retrieved at | `2026-09-01T05:33:13.925500+00:00` | `2026-09-01T06:50:36.399535+00:00` |
| Ordinal-0 response SHA-256 | `c23acb06b3bb7ea99ec71ae9a7ffbdb2c9055f8404efb7e7b6d341a7206a50b6` | `8c9bff1cbfaf8c402093a8552a327fbf7a3e8b7b41e81296d16430cfb0836f9d` |
| Ordinal-0 bytes | 358,315 | 358,502 |
| Ordinal-0 truncated | false | true |
| Ordinal-1 | absent | terminal, SHA-256 `404321383442456333713986485dd2a35ba926f195abea4047e6e3761ee763e9`, 1,209 bytes |

Pass 1's terminal page ended with the `BANKUSDT-metrics-2026-08-30.zip` and checksum objects. Pass 2's additional terminal page contains exactly the newly published `BANKUSDT-metrics-2026-08-31.zip` and checksum objects. The listing grew between independent passes, crossed the 1,000-object boundary, and changed a real page-count/truncation fact. ADR-0032 therefore blocked exactly as specified. This is not an opaque-token false positive and not an incomplete traversal.

## One authorized continuation; no additional publication invocation

The continuation that produced the terminal facts above consumed the single Review-393 planner invocation. During the subsequent terminal inspection and publication phase, no additional planner launch, resume, or retry occurred. Record 394's statement that no planner launch or resume occurred "during this continuation" is incorrect as written; the correct claim is that no additional planner invocation occurred during terminal inspection and publication. The one authorized continuation was launched and polled; no second runner was created.

## Record 394 omitted both required publication-command results

Record 394 contains no repository-control or scoped-diff command, stream, or exit-code section, although Review 393 required both. The Hermes terminal summary is ephemeral and cannot substitute for repository evidence. This omission is corrected below with exact fresh command output.

## Fresh publication-check evidence

Two fresh publication commands were run after the control-plane updates below.

### Command 1

```text
python3 scripts/check_repo_control.py
```

Stdout:
```
Repo control check: PASS
```

Exit code: `0`

### Command 2

```text
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/396_CEX002_V2_DRIFT_DIAGNOSIS_AND_PUBLICATION_EVIDENCE_COMPLETION.md tickets/CEX-002.md
```

Stdout:
```
(empty)
```

Exit code: `0`

## No prohibited action statement

No planner launch, network call, SQLite query, v1/v2/runner mutation, source/test edit, acquisition, cleanup, transition, ADR decision, architecture change, or later work occurred during this publication. Record 394 is preserved unchanged. The three committed paths are exactly record 396, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. No unrelated dirty path is staged.

## Final actor fields

- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
