# CEX-002 Blocked Sidecar-Path Serialization Correction Authorization

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record 371 accepted as blocked execution evidence; bounded source/test correction authorized
- **Corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Record-371 disposition

The reviewer independently inspected Hermes commit
`f6ba0c8a77dc64ddf3dcc0612ae911c597e9e10e`, record 371, both final actor fields, the empty
staging area, the absent candidate locator, matching remote, and preserved unrelated dirty paths.
Record 371 is accepted as faithful evidence for the one Review-370 invocation. The command ran
once, exited 1 with
`ERROR: a retained sidecar path is not the canonical content-addressed leaf`, stopped before
listing or candidate publication, and performed no raw ZIP GET, acquisition, Coinalyze access,
active-generation edit, cleanup, replacement, or transition.

This accepts the blocked execution record only. It does not accept a candidate, pass Gate 2, or
authorize a retry.

## Repository-native diagnosis

The refusal is an exact path-serialization reader/test defect, not a changed sidecar or an unsafe
generation-0 path. The accepted acquisition writer's `content_path_for()` returns
`Path(content_root) / digest[:2] / digest`. Generation 0 was installed and acquired with the
repository-recorded command argument `--store-root data/cex002_qualify`, so its durable sidecar
paths use the exact relative form:

```text
data/cex002_qualify/gate2/content/<first-two-hex>/<sha256>
```

The revision planner opens and rebinds the physical content root through held descriptors, but
then constructs its string comparison with `Path(content_root).absolute()`. Its production CLI
derives an absolute repository root, so the reader incorrectly demands an absolute serialization
for the same held leaf. The focused test writer likewise stored temporary absolute paths and
therefore masked the production serialization mismatch.

The physical proof remains sound: generation-0 SQLite/WAL/SHM identities are pinned, the content
root is held and rebound, the shard and digest components are exact, and the sidecar bytes are
opened no-follow and rehashed through that held descriptor. The correction changes no
architecture and needs no ADR amendment. It must align the string-form check with the frozen
writer while retaining the descriptor-bound physical proof.

## Exact Sol correction

Sol High is authorized to edit only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`.

The correction must:

1. derive the exact durable sidecar-path serialization from the already pinned generation
   destination plus `gate2/content/<shard>/<digest>`;
2. require byte-for-byte equality with that relative canonical string, without `resolve()`,
   `.absolute()`, normalization, alias acceptance, or pathname-based authority;
3. continue opening only `<shard>/<digest>` through the already held and rebound content-root
   descriptor, then rehashing exact bytes/size and reparsing the provider checksum;
4. make synthetic state rows carry the production-relative serialized sidecar path while their
   physical test bytes remain beneath the held temporary content descriptor;
5. add direct positive coverage for the production-relative form and negative coverage that
   rejects an absolute spelling of the physical leaf, dot/traversal or other noncanonical
   spelling, a wrong shard, and a wrong digest leaf; and
6. preserve every payload, generation, listing, sidecar-byte, checkpoint, manifest, capacity,
   publication, recovery, and authorization boundary otherwise unchanged.

No CLI or fixture change is authorized. After editing, Sol may run exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on the first nonzero result. It reports the exact command/output/exit code, changed
paths, SHA-256 identities, line counts, and collected-case accounting, then stops for reviewer
static inspection. It may not run lint, repository control, a standalone planner, network/data
access, real-state access, integration, record editing, Git, commit, push, retry/resume, cleanup,
acquisition, transition, or later work.

Hermes remains unauthorized. Harness output is a handoff aid only; the reviewer must promote the
result into repository authority before any integration or real retry. Gate 2 remains
`IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/372_CEX002_BLOCKED_SIDECAR_PATH_SERIALIZATION_CORRECTION_AUTHORIZATION.md`;
  and
- `tickets/CEX-002.md`.

Developer paths, real state/data, implementation evidence, and every unrelated dirty path remain
excluded.
