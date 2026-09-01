# CEX-002 Record-396 Acceptance and Sol V3 Reachability Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept record 396; adopt ADR-0033; authorize one bounded Sol High source/test drop
- **Authorized actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Record-396 acceptance

The reviewer accepts Hermes commit `bf200e88274d77b4d4b66467072a2ae66cda3891` as the exact
Review-395 evidence publication:

- the commit contains exactly record 396 and the two control-plane paths;
- both required publication commands are recorded with exact zero exits;
- `HEAD == origin/main == bf200e88274d77b4d4b66467072a2ae66cda3891`, staging is empty,
  and unrelated dirty work remains unstaged;
- record 394 is preserved and its false incomplete/truncated-final-page diagnosis is explicitly
  corrected;
- both v2 passes are complete at the same 1,308 prefixes with null cursors;
- the exact first normalized difference is the `BANKUSDT` page-boundary change caused by the new
  2026-08-31 ZIP and checksum outside the frozen pending set; and
- the one Review-393 continuation is distinguished from the absence of any additional
  publication-phase planner invocation.

No v2 candidate, manifest, receipt, lineage, locator, acquisition, Gate-2 result, transition, or
later ticket is accepted. The v1 and v2 blocked trees remain immutable.

## Architecture decision

ADR-0033 is adopted. Cross-pass authority for this frozen revision is the exact aggregate prefix
namespace plus exact key/size/ETag facts for every frozen pending raw object and checksum sidecar.
Physical page count and truncation sequence remain fully authenticated within each pass and
retained in exact lineage, but unrelated live leaf-object growth may not define semantic equality.

Corrected code must create a fresh v3 sibling with distinct schema and policy identities. Neither
v1 nor v2 may be resumed, relabeled, copied, or mutated. This reviewer decision is durable here
and in ADR-0033; no harness conversation supplies architecture authority.

## Sol High source/test authorization

At the owner's explicit Sol-High direction, Sr Dev - Codex Sol using GPT-5.6-sol High is the sole
authorized source actor for this bounded drop. It may edit exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`.

It must implement ADR-0033 literally as one coherent drop:

1. use only `gate2_revision_candidate_v3`; set `ADR_ID` to `0033`; use distinct v3
   candidate/checkpoint/lineage/locator schemas and the exact policy identity
   `adr0033_aggregate_prefix_reachability_and_v3_candidate_v3`; never reference either blocked
   candidate as v3 authority;
2. retain every per-pass authentication, pagination, completion, token-cycle, bound, checkpoint,
   and recovery rule;
3. replace page-ordinal/truncation-sequence cross-pass equality with one canonical per-pass
   aggregate reachability document containing exact sorted roots, discovered prefixes, completed
   prefixes, and each prefix's sorted union of child prefixes across all of its pages;
4. require the two aggregate documents to be exact and continue to block any root, prefix-set, or
   aggregate child-prefix drift;
5. keep exact pending raw/sidecar key, size, ETag, absence, count, identity, and single-part
   sidecar checks independent of page shape;
6. replace the v2 graph digest with `stable_reachability_sha256` in v3 receipt/lineage claims;
   retain exact total/per-pass page counts and all page metadata in physical evidence, but exclude
   page counts and physical pagination shape from `semantic_sha256`;
7. retain exact pass-2 request/page lineage in physical manifest rows while preserving the
   accepted transport-stripped semantic-row digest; and
8. preserve every unrelated authority, security, held-descriptor, ZIP, generation-0, pending-set,
   capacity, deterministic-publication, and no-authorization invariant.

The tests must prove at minimum:

- v1 and v2 trees remain byte-untouched while a fresh v3 tree and exact v3 identities are used;
- recovery rejects v1/v2 checkpoint, receipt, lineage, and locator identities as v3;
- one complete pass may use one terminal page while the other uses a truncated page plus a second
  terminal page after unrelated leaf objects cross a page boundary; the candidate completes with
  equal aggregate reachability and exact differing physical lineage;
- fresh candidates with equal aggregate reachability and pending facts but different unrelated
  page counts/truncation sequences have the same semantic identity while physical evidence differs;
- root, discovered/completed prefix, or aggregate child-prefix drift blocks;
- pending raw/sidecar absence, key, size, or ETag drift blocks;
- incomplete, malformed, cyclic, unauthenticated, or ceiling-breaking pagination still blocks;
  and
- uninterrupted/resumed v3 publication and completed-candidate recovery retain existing safety
  and deterministic guarantees.

Sol may run exactly one targeted command after both files are complete:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

It must stop on the first nonzero result and report the exact command and output. This targeted
exception does not authorize integration, repository records, Git, commits, pushes, real
candidate/data access, network, acquisition, cleanup, or transition. Sol must report exact final
SHA-256 hashes, line counts, test-function/case counts, and a scoped diff summary. Harness output
is a source-drop handoff only; acceptance occurs only in a later repository review.

## Prohibitions and stop

Sol may not edit the CLI, fixtures, ADR, review, ticket, current-task, or any other path. It may
not inspect or mutate real candidate/data trees, generation 0, runners, SQLite, retained sidecars,
or content; access network/provider/Coinalyze; invoke the planner or acquisition; clean data; use
Git; or authorize integration/later work. It stops after the two-path drop and optional single
targeted command for reviewer inspection.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/adr/0033-aggregate-prefix-reachability-and-v3-candidate.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/397_CEX002_RECORD396_ACCEPTANCE_AND_SOL_V3_REACHABILITY_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

No developer source/test, implementation evidence, candidate/runner/data, acceptance command, or
unrelated dirty path is included.
