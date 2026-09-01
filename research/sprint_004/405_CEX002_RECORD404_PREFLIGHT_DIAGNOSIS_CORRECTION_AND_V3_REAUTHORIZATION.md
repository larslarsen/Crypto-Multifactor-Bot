# CEX-002 Record-404 Preflight Diagnosis Correction and V3 Reauthorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept safe no-launch stop; reject path/hash diagnosis; authorize one path-explicit fresh v3 invocation
- **Executing actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Accepted no-launch facts

The reviewer accepts Hermes commit `8f33fc3eb9b616d1d849d71776f214991afffb9d` as an exact
three-path publication of record 404 plus the two control-plane paths. It accepts these bounded
facts from the Review-403 assignment:

- preflight began at `HEAD == origin/main == 0ff212d590ea23bd275d963da755f81d44809a6a` with
  empty staging and no live revision-candidate planner;
- the integrated v3 source, test source, and planner CLI hashes matched;
- the immutable v1/v2 checkpoint and private-index hashes matched;
- the fixed v3 root was absent;
- no planner invocation, runner, network request, SQLite open, v3 tree, candidate, source/test edit,
  acquisition, cleanup, transition, or later work occurred; and
- current `HEAD == origin/main == 8f33fc3eb9b616d1d849d71776f214991afffb9d`, staging is
  empty, and all 11 unrelated modified plus 13 unrelated untracked paths remain unstaged.

Because the planner process never started, Review 403's one planner invocation was not consumed.
The evidence publication ended the Hermes assignment, so a new reviewer authorization is still
required before launch.

Record 404 updated CURRENT_TASK to the reviewer but left the ticket's top-level actor as Hermes,
contrary to Review 403's final-actor requirement. Review 405 records that defect and supersedes the
fields with a new Hermes assignment; it does not treat record 404 as having completed both final
actor updates.

## Rejected mismatch diagnosis

Record 404 associates Review 403's expected acquisition source/CLI hashes with these qualification
paths:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`.

That association is false and is rejected. The Review-403 hashes were computed from the acquisition
paths named by the integrated planner's code-identity contract:

| Required code path | Required and current SHA-256 |
| --- | --- |
| `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py` | `1ac17e902ea3b8aa6967ad3cb4e89d2b2b746f147eb1f83322fba2776e107e32` |
| `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py` | `a715023e8e8c43ef908097c4bb7332cfcc4798d08929d433223f4e149599b905` |
| `scripts/research/plan_binance_usdm_gate2_revision_candidate.py` | `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a` |
| `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` | `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d` |
| `scripts/research/acquire_binance_usdm_harmonic_release.py` | `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043` |

All five exact paths rehash to their required values. The qualification source/CLI are not part of
this preflight and must not be substituted for acquisition paths. Their different hashes do not
constitute drift.

Record 404's claim that later commits advanced HEAD after Review 403 was written is also false in
this execution context: the preflight itself proves exact Review-403 publication HEAD. Historical
qualification-authority commits do not change the explicit current acquisition path/hash mapping.
Record 404 remains unchanged as the rejected diagnosis; this review is the append-only correction.

## One path-explicit fresh v3 invocation

Hermes is authorized for exactly one planner invocation. Before launch it must:

1. read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0033, and Reviews 403-405;
2. prove `HEAD == origin/main` at this review's publication commit and staging empty;
3. prove no revision-candidate planner process is live;
4. rehash the five literal full paths in the table above and compare each only to the hash in its
   own row; do not hash or compare either qualification path;
5. rehash the immutable v1 checkpoint/private index as
   `2a9ed07c2adb72e9311e64fe93b10edd818558f521f0fabef73567f0a51d86a0` /
   `fb27538b340015ebdbe3c9737e9f70d1ec66b0a826464d145fecf7484fd0ccfc`;
6. rehash the immutable v2 checkpoint/private index as
   `b1ab6ca113bffe43bb87ed3ef9391f753a36170174e7ea738f9e29c193890844` /
   `7dc66a10dba7ea5f6bcc6cd5c845a538e9f8d6d656d0ebfeca425f0f6dc4669a`; and
7. prove `data/cex002_qualify/gate2_revision_candidate_v3` is absent.

It may hash but may not open either blocked candidate's SQLite database. Any real mismatch stops
before launch and must be published; the path association above is final and not inferential.

If preflight passes, Hermes creates one fresh `mktemp -d` runner under `/tmp`, durably captures
separate stdout/stderr, start/end UTC, exit code, shell PID/start ticks, planner PID/start ticks,
exact runner script, and terminal status, then launches exactly once with at least four hours wall
allowance:

```text
PYTHONPATH=src .venv/bin/python scripts/research/plan_binance_usdm_gate2_revision_candidate.py
```

Hermes must poll only that same process/session to terminal. Tool detachment permits observation
only through the original PID/start ticks, never a replacement. Exit 0, 1, 2, 6, 124, another
nonzero, disappearance, power loss, or interruption consumes the invocation. No rerun, resume,
repair, cleanup, or duplicate is authorized.

The planner may only acquire its accepted locks; query-only authenticate generation 0; issue fixed
official Binance S3 ListObjectsV2 requests for the two affected roots in two passes; authenticate
retained sidecars/content; and create the fresh fixed v3 evidence tree. It may not reference or
mutate v1/v2; GET raw ZIPs; use Coinalyze; edit generation 0; follow redirects; select a subset;
invoke acquisition; patch source/tests; clean/replace data; transition; or start later work.

## Mandatory record 406 and stop

Every preflight or terminal outcome must be published as
`research/sprint_004/406_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md`. Record 406 must contain
all exact Review-405 preflight facts and, if launched, all Review-403 runner/terminal/candidate
evidence requirements: runner identities and file hashes/bytes, exact command/PIDs/start ticks,
times/elapsed/allowance, complete streams, exit/stop, exactly-once proof, immutable v1/v2 proof,
checkpoint/page/pass/cursor/publication state for non-completion, or complete v3 artifact,
semantic, reachability, pending, classification, byte, capacity, code/generation, and false-
authorization facts for completion. The outcome accepts no candidate and authorizes no acquisition
or transition.

After terminal, Hermes may perform only bounded stat/hash/JSON inspection of v3 and runner files;
it may not directly query any real SQLite database. Before repository control it sets both literal
top-level actor fields to the reviewer and writes exact final summaries prohibiting any retry,
resume, acquisition, transition, later gate, or next ticket. It then runs only:

```text
python3 scripts/check_repo_control.py
git diff --check -- docs/handoff/CURRENT_TASK.md research/sprint_004/406_CEX002_FRESH_V3_REVISION_CANDIDATE_RUN_RECORD.md tickets/CEX-002.md
```

If both pass, Hermes commits/pushes exactly record 406 and the two control-plane paths, proves
remote equality, and stops. Candidate/runner bytes and every unrelated dirty path remain unstaged.
Harness output is a handoff only; only a later repository review may accept the result.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/405_CEX002_RECORD404_PREFLIGHT_DIAGNOSIS_CORRECTION_AND_V3_REAUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No source/test, implementation evidence, candidate/runner/data, acceptance command, or unrelated
dirty path is included.
