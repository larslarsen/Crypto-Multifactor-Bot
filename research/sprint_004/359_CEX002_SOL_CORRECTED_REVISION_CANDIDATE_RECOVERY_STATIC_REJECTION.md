# CEX-002 Sol Corrected Revision-Candidate Recovery Static Rejection

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** rejected before integration; narrow recovery correction authorized
- **Reviewed actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Authorized corrective actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Reviewed correction

The reviewer statically inspected the Review-358 correction at these exact identities:

- production: 4,639 lines, SHA-256
  `7968634d321d178599fea201b896ebeba3ed67bd5a083ff46a1a7e5094572a5f`;
- CLI, unchanged: 87 lines, SHA-256
  `9e203790432d412d489120fdef6bcb19831cf10461cecc38e7b1f23c41fb0d1a`;
- test source: 2,383 lines and 53 test functions, SHA-256
  `3cc3bbabe202c898b178f7a30dac3707a2373c6dd8876ac7639c61272a5216a5`;
- all three bounded fixtures remain unchanged at the identities pinned in Review 358.

Sol ran Review 358's one targeted command exactly once:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

The command exited zero with all 94 collected cases passing. Its complete output was:

```text
........................................................................ [ 76%]
......................                                                   [100%]
```

Sol attests that it edited only the production and test paths, used no other executable/test,
network, data, planner/CLI, acquisition, migration, acceptance, or Git command, and did not
access the archive or real generation-0 state/WAL/SHM/content/candidate data. The reviewer
executed no test, Python, planner, SQLite, network, or data command.

## Corrections accepted and preserved

Static inspection confirms that Review 358's eight findings are materially corrected. Recovery
now recomputes deterministic receipt claims from the authenticated manifest and current
authority. The final new-locator boundary rebinds all held nested directories and reauthenticates
code, SQLite leaves, private locator, and published assets after the last hook. Named publication
collisions fail closed. SQLite leaf snapshots bind the opened descriptor to named pre/post stat
identity. Checkpoint and lineage byte ceilings precede durable publication. Pending keys use an
exact family/symbol/date grammar. The SQLite snapshot is established before its hook and the
schema object set rejects views/triggers. The four malformed child-prefix tests are corrected.
All of those changes and their focused tests must remain unchanged in substance.

## Residual blocker 1 - completed recovery does not close its named-tree boundary

On a rerun with an existing locator, `_authenticate_completed_candidate()` authenticates the
checkpoint/pages, manifest, lineage, receipt, and their derived claims through already-held
nested directory descriptors. Before returning `EXIT_COMPLETE`, however, the caller rebinds only
the store, generation, content, and candidate roots. It does not rebind `tmp`, pages, manifests,
receipts, or lineage, and it does not reauthenticate the current locator and immutable asset
names at the last recovery boundary.

A same-device nested-directory swap after the held open can therefore make the returned
`manifest_path` or `receipt_path` name content different from what was authenticated. A regular
locator or content-addressed leaf can likewise be replaced after its earlier read. The returned
receipt object is valid, but the planner's `complete` claim and published paths no longer bind the
current named candidate tree. This is the completed-recovery analogue of the new-locator race
that Review 358 corrected.

Add a recovery-only final boundary immediately before the completed return. After the final
injectable hook, rebind every held root and nested directory, reauthenticate code and SQLite,
and prove that the current named locator, checkpoint/reachable pages, manifest, lineage, and
receipt are exactly the authenticated graph. Holding safe descriptors through the final check or
performing a second bounded authentication is acceptable; a substituted name must never return
`complete`. Add focused tests for nested directory, locator, immutable asset, checkpoint/page,
code, and SQLite replacement at this recovery boundary.

## Residual blocker 2 - completed manifest authentication has no stream ceilings

The manifest recovery path hashes the compressed file without a declared compressed-byte
ceiling and iterates `gzip.GzipFile` by newline without a per-line/decompressed-byte ceiling. A
forged self-consistent locator/receipt can therefore drive an arbitrarily large compressed read
or an unbounded decompressed first line before semantic rejection. Content addressing proves
identity, not bounded resource use.

Declare conservative deterministic ceilings for the compressed manifest, each canonical JSONL
row, and total decompressed bytes/rows. Enforce them both while creating/analyzing the private
manifest and while authenticating a completed manifest, before unbounded allocation. The exact
51,275-row production-shaped case must remain valid. Add focused lowered-ceiling recovery tests,
including an overlong compressed JSONL line, and prove a typed refusal rather than a raw resource
or gzip exception.

## Narrow Sol correction authorization

Sr Dev - Codex Sol using GPT-5.6-sol High remains the sole authorized senior actor. It must
correct only the two recovery blockers above while preserving the 94 passing cases and all prior
authority corrections. Writable scope remains exactly:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`, only if mechanically required
  by the corrected API;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/` for bounded fixtures only.

Sol may use read-only static inspection commands for the governing documents and authorized
source/test paths. It may not inspect or touch the real generation-0 SQLite/WAL/SHM/content/
candidate data or `~/cmb_archive/`. It performs no network/data operation, standalone planner/
CLI, acquisition, migration, integration, repository-record edit, Git operation, commit, push,
or acceptance command.

After editing, Sol may run exactly one new command against synthetic pytest-managed temporary
roots:

```text
.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_gate2_revision_candidate.py -q --tb=short
```

Sol stops on the first nonzero result. Whether zero or nonzero, it reports the exact command and
complete output, exact SHA-256 and line count for each edited path, test-function and collected-
case counts, and confirmation that no other executable/test/network/data/Git command ran. This
is source feedback only; it does not integrate or accept the drop.

Hermes remains unauthorized. No candidate execution, cleanup, generation transition, corrected
acquisition, Gate 3, model, or next-ticket work is authorized. Gate 2 remains `IN_PROGRESS` and
next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/359_CEX002_SOL_CORRECTED_REVISION_CANDIDATE_RECOVERY_STATIC_REJECTION.md`;
  and
- `tickets/CEX-002.md`.

Developer source/test/fixture paths, real state/data, implementation evidence, and every
unrelated dirty path are excluded.
