# CEX-002 Sol V3 Stopped-Drop Rejection and Capacity-Semantic Correction Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject failed source feedback; clarify ADR-0033; authorize one bounded Sol correction
- **Authorized actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Stopped-drop review

Sol edited only the two Review-397 paths and then used the one authorized targeted command:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

The command exited 1. Sol stopped without a patch or rerun. The visible progress was:

```text
..FFFFFFFFFF...F..FFFFFFFFFFFFFFFFFFFFF...FFF...............F........... [ 48%]
..........F.........F..F......................FFFFFFFFFFFFFFFFFFF.....F. [ 97%]
.F.                                                                      [100%]
```

The harness truncated the 2,804-line failure output. It reported 147 collected cases and a common
traceback at `_semantic_receipt_payload`: `KeyError: 'capacity_projection'`. The reviewer does not
treat the harness's inferred 59-failed/88-passed split as complete exact command output. The exit,
common traceback, and stopped state are sufficient to reject the drop for integration.

The stopped identities independently rehash as:

- source: SHA-256 `27600e99edb5c41e767996a554e4736dcc5f334eac470a99e0913ac7f1ffcc3c`,
  5,148 lines; and
- test source: SHA-256 `120d6cabe103d1eced363ee228ef85c8a33f12be31a5245e8bf9b430d2950ccf`,
  3,342 lines and 70 test functions.

The scoped diff is whitespace-clean and contains 48 insertions/50 deletions in production plus
316 insertions/114 deletions in test source. Staging is empty and
`HEAD == origin/main == a37b9068c8c6565333cb7d40180299a139dc48e4`. No source or test is
accepted, integrated, staged, committed, or pushed.

## Root cause and ADR-0033 clarification

The stopped source added `capacity_projection` to `SEMANTIC_RECEIPT_KEYS`. Candidate creation
computes `semantic_sha256` from the deterministic receipt before the fresh local capacity
measurement is attached to the physical receipt envelope, so the semantic projection raises the
observed `KeyError`.

More importantly, adding that field is outside ADR-0033's intended change. Available space,
operating reserve, and remainder are volatile same-device measurements. V2 retains them in the
exact locator-bound physical receipt but excludes them from candidate semantic identity. ADR-0033
changes only live-listing page-shape semantics and preserves that boundary. The ADR is clarified
durably: deterministic pending byte facts remain semantic; `capacity_projection` remains exact
physical receipt evidence and is not a `semantic_sha256` input.

The aggregate-reachability implementation is otherwise directionally consistent with ADR-0033 on
static review: v3 has distinct identities/root; the canonical document binds exact roots,
discovered/completed prefixes, and aggregate child-prefix sets; exact pending facts remain
separate; page counts remain physical and are projected out of listing and lineage semantics; and
the new synthetic cases exercise differing complete page shapes and exact physical lineage. This
is not source acceptance because the only run failed.

## Bounded Sol correction authorization

Sol remains the sole authorized source actor. Starting from the two stopped hashes above, it may
make only these two semantic-scope corrections in the same two paths:

1. remove the `capacity_projection` entry added to `SEMANTIC_RECEIPT_KEYS` in
   `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
2. change the new page-boundary test to assert that `capacity_projection` is absent from
   `_semantic_receipt_payload(...)` in
   `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`.

No other production or test-source change is authorized. After a static audit of those exact
corrections, Sol may run exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

It must stop on the first nonzero result without editing or rerunning. On zero, it must also stop
and report the exact complete command output, exit code, final SHA-256 hashes, line counts,
test-function/case counts, and scoped diff summary. Harness output remains an unaccepted source
handoff until a later repository review.

## Prohibitions and stop

Sol may not edit any other line or path; use Git; create repository records; run another Python or
test command; inspect or mutate real candidate/data trees, generation 0, runners, SQLite, retained
sidecars, or content; access network/provider/Coinalyze; invoke the planner or acquisition; clean
data; integrate; commit; push; or authorize later work.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/adr/0033-aggregate-prefix-reachability-and-v3-candidate.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/398_CEX002_SOL_V3_STOPPED_DROP_REJECTION_AND_CAPACITY_SEMANTIC_CORRECTION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

The unintegrated source/test drop, implementation evidence, data, acceptance command, and every
unrelated dirty path are excluded.
