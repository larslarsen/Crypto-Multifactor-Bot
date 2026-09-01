# CEX-002 Sol V2 Cursor Correction Source Acceptance for Hermes Integration

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** exact Review-386 source/test drop accepted for bounded Hermes integration
- **Source actor:** Sr Dev - Codex Sol using GPT-5.6-sol High
- **Integration actor:** Jr Dev - Hermes through the installed Hermes one-shot harness
- **Gate 2:** `IN_PROGRESS`
- **Next ticket:** `NONE`

## Static acceptance

The reviewer independently inspected the complete two-path diff and rehashed both files. Sol's
ADR-0032 correction is accepted for integration at exactly these identities:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `2f7ebacaba729c57896de7489646d517bd481347534340f3c452a7a394e76309`
  - lines: 5,150
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`
  - SHA-256: `090fa536c21213767c467533827c900d0c60c182ab1fd3f283316a033449337f`
  - lines: 3,140
  - test functions: 68

The production source selects only the fresh fixed `gate2_revision_candidate_v2` sibling and
uses distinct ADR-0032 v2 candidate, checkpoint, lineage, locator, and policy identities. It
does not reference, import, rename, copy, hard-link, mutate, or authenticate the blocked v1 tree
as v2.

Cross-pass graph equality is now canonical by exact prefix and zero-based page ordinal within
that prefix. It retains sorted child prefixes and the exact truncation sequence and separately
requires equal roots and exact completed/discovered prefix sets. Opaque current/next cursor,
token-derived request key, URL, page hash, headers, and retrieval time remain authenticated in
the physical checkpoint/lineage but do not define reachability equality. Pending raw and sidecar
facts compare and digest exact key, size, and ETag without page locators; absence and all material
fact drift remain blocking.

The manifest adds `semantic_rows_sha256` over the canonical row projection that removes exactly
the two request/page locator pairs and `listing_page_lineage`. The semantic receipt binds that
digest, manifest format, and row count while the ordinary receipt and locator still bind the
exact compressed/uncompressed manifest, lineage asset, and retained pages. Completed recovery
recomputes and validates both identities. All unrelated generation-0, held-descriptor, bounded
stream, ZIP, capacity, no-replace publication, and no-authorization behavior remains intact.

Focused tests prove v1/v2 isolation, all v2 identities and cross-version recovery refusal,
opaque-cursor equivalence with exact dual physical lineage, equal semantic but distinct physical
candidates, child-prefix/page-count/truncation drift refusal, pending raw/sidecar absence and
size/ETag drift refusal, semantic-row tamper refusal, deterministic resume, and completed-tree
recovery. The two accepted paths contain 74 additions/20 deletions and 495 additions/1 deletion,
respectively; no other path belongs to the Sol drop.

Sol ran Review 386's one authorized command exactly once:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
```

It exited 0 with 139 collected cases passing and this complete output:

```text
........................................................................ [ 51%]
...................................................................      [100%]
```

Sol reports no other Python/test, planner, CLI, acquisition, network, data, SQLite, Git, record,
cleanup, or transition command. The reviewer did not rerun the test command. Harness output is
only source-drop handoff evidence; this repository record is the acceptance decision.

This is source/test acceptance for integration only. It does not integrate the drop, accept a
v2 candidate, authorize a real listing run or raw acquisition, pass Gate 2, or authorize later
work.

## Hermes integration authorization

Hermes must read `AGENTS.md`, the current task, full CEX-002 ticket, ADR-0032, and Reviews 386-387.
It must prove `HEAD == origin/main` at this review's publication commit, prove staging is empty,
and rehash the two accepted developer paths. Any mismatch stops before validation. Every
unrelated modified or untracked path must remain present, unchanged, and unstaged.

Hermes may stage only the two accepted developer paths and run exactly, in order:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
.venv/bin/python -m ruff check --no-cache src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py
python3 scripts/check_repo_control.py
git diff --check -- src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py tests/acquisition/test_binance_usdm_gate2_revision_candidate.py docs/handoff/CURRENT_TASK.md research/sprint_004/388_CEX002_V2_CURSOR_CORRECTION_INTEGRATION_RECORD.md tickets/CEX-002.md
```

Hermes stops on the first nonzero result and must not patch either accepted developer path. After
pytest and ruff pass, but before repository control, Hermes must create
`research/sprint_004/388_CEX002_V2_CURSOR_CORRECTION_INTEGRATION_RECORD.md` and update both
top-level control-plane actor fields to the reviewer. Record 388 must contain the two accepted
hashes, exact preflight facts, every exact command, complete stdout/stderr and exit code, the
139-case and warning results, and the exact final staged path list. The final actor fields must
exist before repository control and may not change afterward. Record 388 must contain the exact
repository-control result before the scoped diff runs; the scoped diff must run against the final
five repository files, and none of those files may change afterward.

If and only if all four commands pass, Hermes stages exactly the two developer paths plus record
388, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`; verifies nothing else is staged;
commits; pushes `main`; proves `HEAD == origin/main`; and stops for reviewer inspection. Git is
authorized only for those mechanical integration/publication actions. Harness output remains a
handoff aid and cannot replace record 388.

No standalone planner/CLI, listing request, raw ZIP GET, real candidate or generation-0 data
access, SQLite open, acquisition, cleanup, migration, generation transition, Gate 3, model work,
or next ticket is authorized. CEX-002 and Gate 2 remain `IN_PROGRESS`; next ticket remains
`NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/387_CEX002_SOL_V2_CURSOR_CORRECTION_SOURCE_ACCEPTANCE_FOR_HERMES_INTEGRATION.md`;
  and
- `tickets/CEX-002.md`.

The accepted developer paths remain unintegrated until Hermes publishes them. Implementation
evidence, real state/data, and every unrelated dirty path remain excluded.
