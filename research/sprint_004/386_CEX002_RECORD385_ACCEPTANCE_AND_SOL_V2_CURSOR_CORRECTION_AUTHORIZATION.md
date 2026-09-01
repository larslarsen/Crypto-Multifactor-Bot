# CEX-002 Record-385 Acceptance and Sol V2 Cursor Correction Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept record 385; adopt ADR-0032; authorize one bounded Sol High source/test correction
- **Authorized actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Evidence acceptance

The reviewer accepts Hermes record 385 and commit
`04801359dd0c4967a7062e21e79495e2c7310964` as the durable Review-384 evidence publication:

- the commit contains exactly record 385 and the two control-plane paths;
- repository control and scoped diff have exact zero results with Hermes attribution;
- `HEAD == origin/main`, staging is empty, and unrelated dirty work remains unstaged;
- the first Review-383 invocation's exact captured exit-1 blocker is preserved;
- the second unauthorized launch, mixed runner identities, and no-live-process proof are exact;
- the candidate checkpoint, private index, page inventory, complete passes, and absent publication
  artifacts remained unchanged; and
- all four code identities are corrected to Review-373 values.

Both final actor fields name the reviewer, but both summaries still describe the completed
evidence-only Hermes assignment as authorized future work. This stale prose does not invalidate
record 385. Review 386 supersedes it with the new Sol assignment.

ADR-0032 is adopted because the blocker is architecture-sensitive: opaque S3 cursor bytes must
remain exact lineage while being excluded from cross-pass reachability and candidate semantic
identity. The blocked v1 candidate remains immutable, and corrected code produces an independent
v2 candidate.

## Sol High source/test authorization

Sr Dev - Codex Sol using GPT-5.6-sol High is the sole authorized source actor. It may edit exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`.

It must implement ADR-0032 literally as one coherent drop:

1. change the fixed candidate root to `gate2_revision_candidate_v2`, set `ADR_ID` to `0032`, use
   distinct v2 candidate/checkpoint/lineage/locator schema identifiers and a v2 ADR-0032 policy
   identity, and leave the v1 candidate unreferenced and untouched;
2. normalize each complete pass graph by prefix and page ordinal, comparing only exact prefix,
   sorted child-prefix list, and truncation flag after separately requiring equal roots and exact
   completed/discovered prefix sets;
3. exclude current/next continuation tokens, token-derived request keys, final URLs, response
   hashes/headers, and retrieval clocks from cross-pass graph equality while retaining them in
   exact lineage;
4. compare/digest pending raw and sidecar facts by exact key, size, and ETag without request/page
   locator identity; keep every absence, size drift, ETag drift, and single-part sidecar check;
5. add and validate `semantic_rows_sha256` over ADR-0032's exact transport-stripped row projection,
   and make receipt `semantic_sha256` bind that digest plus manifest format/row count instead of
   physical manifest hashes/names/bytes;
6. retain exact pass-2 request/page lineage in physical manifest rows and exact complete lineage
   assets/locator binding; and
7. preserve every unrelated authority, security, bound, recovery, held-descriptor, ZIP policy,
   generation-0, pending-set, capacity, and no-authorization invariant.

The tests must prove at minimum:

- a v1 tree remains unchanged while a fresh v2 tree is selected;
- all four v2 schema/policy/ADR identities are exact and recovery rejects cross-version assets;
- equivalent two-pass listings with different opaque token values and token-derived request/page
  identities complete, retain both physical lineages, and yield one normalized stable graph and
  pending-facts digest;
- fresh candidates with equivalent economic/provider facts but different tokens, page response
  identities, headers, URLs, and retrieval clocks have the same semantic identity while their
  physical lineage/manifests may differ;
- child-prefix, prefix/page-count, or truncation-sequence drift blocks;
- pending raw/sidecar key absence, size drift, or ETag drift blocks; and
- uninterrupted/resumed v2 publication and completed-candidate recovery retain existing safety
  and deterministic guarantees.

Sol may run exactly one targeted command after both files are complete:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

It must stop on the first nonzero result and report the exact command/output. This exception does
not authorize integration, repository records, Git, commits, pushes, real candidate/data access,
network, acquisition, cleanup, or transition work. Sol must report exact final SHA-256 hashes,
line counts, test-function/case counts, and a scoped diff summary. Harness output is a source-drop
handoff only; no decision or acceptance occurs outside the repository review.

## Prohibitions and stop

Sol may not edit the CLI, fixtures, ADR, review, ticket, current-task, or any other path. It may
not inspect or mutate the real v1 candidate, generation 0, runner, SQLite, retained sidecars, or
content; access network/provider/Coinalyze; invoke the planner or acquisition; clean data; use Git;
or authorize any later work. It stops after the two-path drop and optional single targeted command
for reviewer inspection.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/adr/0032-opaque-listing-cursor-normalization-and-v2-candidate.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/386_CEX002_RECORD385_ACCEPTANCE_AND_SOL_V2_CURSOR_CORRECTION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, candidate/runner data, acceptance command, or
unrelated dirty path is included.
