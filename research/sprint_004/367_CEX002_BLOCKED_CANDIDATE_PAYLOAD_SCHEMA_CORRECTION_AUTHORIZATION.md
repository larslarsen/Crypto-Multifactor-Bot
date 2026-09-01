# CEX-002 Blocked Candidate Payload-Schema Correction Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 366 accepted as blocked execution evidence; bounded source/test correction authorized
- **Corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Record-366 disposition

The reviewer independently inspected Hermes commit
`d7cb01dfd5c74daec79292a399bdbb786878d4f5`, record 366, the final control-plane fields,
the empty staging area, and the preserved unrelated dirty paths. `HEAD == origin/main` at that
commit. Record 366 is accepted as faithful execution evidence for the one Review-365 invocation:
the command ran once, exited 1 with `ERROR: pending plan payload keys changed`, stopped before
listing or candidate publication, and performed no raw ZIP GET, acquisition, Coinalyze access,
active-generation edit, cleanup, replacement, or transition.

This accepts the blocked execution record only. It does not accept a candidate, pass Gate 2, or
authorize a retry.

## Repository-native diagnosis

The refusal is a planner/test contract defect, not provider drift and not a generation-0 data
mutation. The frozen acquisition writer in
`src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py` constructs two legitimate
non-retained Binance payload shapes before `plan_entry_bytes()` wraps them:

- selected-manifest rows include `consumable`; and
- bounded cost-sample rows include `etag`.

The exact pending set is already bound to 50,921 selected-manifest `daily/metrics` rows and 354
cost-sample `daily/bookTicker` rows. The integrated revision planner instead required one common
nine-field inner payload for both families. Its synthetic `_payload()` helper reproduced that
incorrect common shape, so 109 green cases did not exercise either production writer shape.

The active state remains protected by its frozen SQLite/WAL/SHM identities, schema proof, plan
identity, family coverage, and pending counts. The correction therefore changes no architecture
and needs no ADR amendment; it aligns the ADR-0031 reader with the already accepted ADR-0029
generation-0 writer while preserving exact fail-closed schema checks.

## Exact Sol correction

Sol High is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`.

The correction must:

1. preserve the exact four-field payload envelope;
2. preserve the existing nine common inner fields and all existing canonical value checks;
3. require the `daily/metrics` inner payload to have exactly the common fields plus
   `consumable`, with `consumable` an exact `bool`;
4. require the `daily/bookTicker` inner payload to have exactly the common fields plus `etag`,
   with `etag` exact text;
5. reject a missing family-specific field, a cross-family field, any additional field, or the
   wrong family-specific type;
6. make synthetic builders production-shaped for both affected families and add direct positive
   coverage for both exact shapes plus negative coverage for the four refusal classes above; and
7. preserve every other generation, listing, sidecar, checkpoint, manifest, capacity,
   publication, recovery, and authorization boundary unchanged.

No CLI or fixture change is authorized. After editing, Sol may run exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on the first nonzero result. It must report the exact command/output/exit code, changed
paths, SHA-256 identities, and line counts, then stop for reviewer static inspection. It may not
run lint, repository control, a standalone planner, network/data access, real-state access,
integration, record editing, Git, commit, push, retry/resume, cleanup, acquisition, transition,
or later work.

Hermes remains unauthorized. Harness chat is a handoff aid only; the reviewer will promote the
result into repository records before any integration or real retry. Gate 2 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/367_CEX002_BLOCKED_CANDIDATE_PAYLOAD_SCHEMA_CORRECTION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Developer paths, real state/data, implementation evidence, and every unrelated dirty path remain
excluded.
