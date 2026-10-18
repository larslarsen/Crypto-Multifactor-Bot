# CEX-002 Review 494 — Bounded bundle correction handoff

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Selected senior: Sr Dev — Codex Sol, GPT-6 Sol High (gpt-6-sol, high)
Launch state: owner-approved developer assignment complete; developer stopped
Disposition: final source accepted for Hermes validation/integration; real runs unassigned

## Decision and fixed scope

Grok's first targeted run failed collection. After its four bounded syntax repairs,
the same exact command executed all 24 cases: **14 passed, 10 failed**, exit 1. Eight
catalog failures stop at dependency-order validation and two ingest/CLI failures stop
at a coverage Parquet schema check. Grok stopped without another edit or retry.
The reviewer's stale helper-interface diagnosis was withdrawn; preserve that helper's
existing required keyword arguments. No developer files are integrated.

Rotate the next bounded repair after repeated source/semantic misses and prolonged
correction latency. Choose the available GPT-6 Sol High for these diagnosed Python,
Arrow, SQLite and fixture fixes under the already accepted ADR-0037 design. This is
an explicit task-fit/reliability choice, not reuse of a previous Sol assignment or a
nominal-price decision. GPT-6.1 Sol remains reviewer and must not author production
or test code. Grok's assignment is stopped; do not run two senior actors concurrently.

The owner may relay this one-way prompt. Direct launch/supervision requires explicit
owner approval for this bounded assignment: Review 474's direct-subagent exception
was for Batch A's three-path assignment and is not assumed to extend to this drop.
This is a relay/delegation boundary, not owner engineering acceptance authority.

The owner subsequently answered yes to the explicit request to launch and supervise
this assignment. The reviewer launched bundle_correction_sol using gpt-6-sol with
high reasoning and a fresh context. That approval covers bounded direct supervision
of this repair; it does not authorize integration or transfer reviewer acceptance.
The one targeted test slot below belongs to this developer; Grok remains stopped.

## One-way developer prompt

Work in /home/lars/Crypto_Multifactor_Bot on CEX-002 only. Read AGENTS.md,
docs/handoff/CURRENT_TASK.md, ADR-0037 and this full review. Review 493 contains the
complete prior source review and accepted sizing correction. Do not read the archive.
Read the affected existing producer/canonicalizer source as needed; avoid rereading
historical reviews. Preserve unrelated working-tree changes.

Exactly five writable source/test paths:

1. src/cryptofactors/catalog/dataset/cex002_reference_release.py
2. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
3. scripts/research/publish_binance_usdm_harmonic_bundle.py
4. tests/catalog/test_cex002_reference_release.py
5. tests/ingest/test_binance_usdm_harmonic_bundle.py

Returned starting SHA-256 values, in that order:

```
05daa51d2918924e0fc8153972a49a9851d981f1f823a5038aaa3c77e39014cf
086c99281e0318bb9a4598539804262d6e553e60c108bc2757acdf4e3a1164dc
d245e6195f5619a3d2c5594bb3a1edf4a5345b2696486a352b5af398b3681553
c6eb65f46b90a26706631445b284a772ff54785f87e8d831e20ed5c22e74c8f7
4169ba20d5ed5cda44e149212bd8da4230adb60038fa34759df873d80365234b
```

Complete this consolidated correction together:

- Respect existing manifest canonicalization. It sorts dependencies; _seal_chain must
  validate exactly the ten DATASET role/ID edges and reject duplicates/missing/foreign
  edges without requiring the builder's original tuple order. Preserve all eleven
  identities and existing generic canonicalizer behavior.
- Resolve the coverage footer schema failure against the frozen Arrow contracts.
  Normalize only proven Arrow/Parquet representation aliases, preserving field names,
  actual types and nullability. Schema identities must retain the authenticated declared
  contract's meaning; do not hash unstable physical spelling or weaken schema guards.
- Complete Review 493's actual producer-format repairs: funding and price-state row
  equations differ from klines; basis joins three legs. Coverage lineage uses hyphenated
  plural component names. Retain those real formats in fixtures. Explicit absence
  markers for genuinely global gaps are accepted; never invent a venue identity.
- Fix tuple-row external SQLite connection binding without committing/rolling back
  pending caller work. Preserve read-only consistent readback and atomic eleven-dataset
  admission, complete replay comparison and the five BitMEX exclusions.
- Replace the infeasible nine-pages-per-file SQLite estimate with measured growth or
  a justified bound for actual serialized records and existing schema. Two accepted
  products alone exceed the entire metadata remainder under the present formula.
  Preserve the fixed 4,985,471,619 metadata remainder and 29,690,701,415 operating
  reserve, including SQLite/WAL/temp growth on the actual filesystems. Preflight the
  new bundle write before placing it. Do not charge accepted data again or enlarge caps.
- Remove only this attempt's unrenamed stage after successful EEXIST reuse; preserve
  other attempts' evidence. Verify the whole owned inventory is unchanged on replay.
- Preserve precision-38 decimal values and exact nanoseconds in the logical codec.
  Avoid ambient precision-28 quantization and datetime.microsecond truncation. Add
  independent >28-coefficient-digit and one-nanosecond-difference regressions.
- Bind captured prepared/manifest snapshots to their expected physical pins, recheck
  the durable proof/publication chain before the one commit, and compare complete
  publication entries including manifest paths. Test metadata mutation during admission.
- Strengthen temporary fixtures with real funding/price-state/coverage variants and
  a representative frozen financial schema. Keep resource tests deterministic with
  simulated free space. Do not delete assertions or substitute fake producer equations.

Keep the ten accepted products, reconciliation, holdout, source-availability unknowns,
fee scenarios and censored liquidation semantics unchanged. Keep catalog independent
of ingest, and ingest within ingest/catalog/core imports. No generic source, migrations,
dependencies, records, exports or data changes. Do not implement/run the later external
Nautilus checker or claim final economic/release acceptance.

After completing the correction, run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

Stop at its first nonzero result and report the exact command/output without further
edits or retry. Temporary Git/SQLite fixture operations inside this test are permitted;
direct project Git is not. No other executable probes, syntax/AST commands, tests,
installation, network, real preparation/publication, data mutation, subagents, records,
integration, commit or push. Return the complete five hashes/line counts and concise
notes, then stop for reviewer inspection. Hermes retains validation/integration/Git.

Reviewer publication scope is exactly this Review 494, Review 493's result note,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. No developer integration is included.

## Returned correction and bounded fixture continuation

The sole GPT-6 Sol High developer completed the assigned correction and its one exact
pytest run returned exit 1: 26 passed, 2 failed (28 cases). It stopped without further
edits or retry. The reviewer independently verified all five returned hashes:

```
942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387  2139
dedf31e1996a71c055560b40558a6f1e2a86f8429da805d4cf17a02caf87355e  1848
d245e6195f5619a3d2c5594bb3a1edf4a5345b2696486a352b5af398b3681553   101
33f985a0811ab59f07c60b570ca58580503f935655a0d7c0843a216cf665b3e0  1021
35317790f6a0f04fb255f722abcb95e0307f7cff7fdb013a9a036bc8f02e92fa  1079
```

Inspection attributes both failures to fixture selection. The partial-reader fixture
deletes a constituent and the surviving bundle's dependency edge, so complete replay
comparison correctly diagnoses mixed state. Delete the terminal bundle's row/files/
outgoing edges instead, leaving every surviving constituent intact, and retain the
exact partial_release assertion. Keep the separate mixed-release scenario unchanged.
The bar-gap selector matches both the bar's global quality artifact and a coverage-owned
quality gap whose required_product is bar. Qualify it by the bar dataset ID as well;
retain both absent-symbol/month assertions and coverage's real BTCUSDT identity.

Authorize the same developer to make only those two fixture corrections in the two
test paths, with all three production/CLI paths read-only. Then run the exact same
two-file pytest command once more. Stop on its first nonzero result without edits or
retry and return full output and five hashes/line counts. No other probes, tests,
records, integration, Git or real runs are authorized. This is direct supervision
within the owner's approved Review 494 assignment. Source acceptance remains pending.

## Final source decision and integration prompt

The additional exact targeted run returned exit 0 with all 28 cases passing:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
............................                                             [100%]
```

The reviewer inspected the complete correction against the starting snapshot and
independently verified the final five hashes below. Only the two test fixtures changed
after the preceding failed run; the three production/CLI hashes stayed unchanged.
The fixture correction preserves exact partial/mixed rejection assertions and separately
asserts the global bar gap's absence marker and the coverage gap's actual BTCUSDT symbol.

```
942140dbbc85a4b7cb7f24284442edf8b8289705651895be7cdaa076ddaa8387  2139
dedf31e1996a71c055560b40558a6f1e2a86f8429da805d4cf17a02caf87355e  1848
d245e6195f5619a3d2c5594bb3a1edf4a5345b2696486a352b5af398b3681553   101
c043dcc63fce6e2c7366cdf2365c0af96b39d26a9203455be0e493132585e1a2  1021
d33da132d17026b3042aa26f8142f6ba6fe8758c2377705b96141d46a1102d1a  1088
```

Accept these source bytes for Hermes validation/integration under ADR-0037. The review
confirms exact unordered dependency edges, producer-specific equations and lineage,
declared schema identities, tuple-row binding, precision-38/ns proof tokens, attempt-owned
stage cleanup, owned-inventory preflight, packed-record SQLite reservation and complete
metadata snapshots rechecked immediately before commit. SQLite temporary work is kept
in memory; database/WAL growth is reserved on the catalog filesystem. The representative
147,081-reference regression passes. This is not a measurement of the complete real
candidate or an acceptance of its eventual capacity/proof/economics.

No reviewer tests or acceptance commands ran. Both developer test slots are consumed;
the source actor has stopped. All five files remain unintegrated. Ten accepted products,
Gate 2 acceptance, Gate 3 IN_PROGRESS, CEX-002 IN_PROGRESS and next ticket NONE persist.

The following concrete one-way Hermes prompt is authorized for owner relay. Direct
Hermes launch/supervision requires the owner's explicit approval; the current approval
covered the Review 494 source developer. No Hermes launch has occurred for this step.

> Work on CEX-002 only in /home/lars/Crypto_Multifactor_Bot. Read AGENTS.md,
> docs/handoff/CURRENT_TASK.md and this final section of Review 494. You are Jr Dev
> Hermes using the best reliable available free Nous Portal model; identify the actual
> model in your record. Own validation, integration, evidence and Git only. Do not author
> or modify source/test code, accepted data, schemas or architecture. Never read archive.
>
> Preserve all unrelated working-tree changes. Confirm the index is empty and the five
> source/test files match the final hashes above before validation. Stop on any mismatch,
> denial or nonzero result; do not retry or repair source. Do not repeat the developer's
> focused command as a separate step: the catalog regression command below includes it.
>
> Execute in order:
>
> 1. `.venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py`
> 2. `.venv/bin/ruff check src/cryptofactors/catalog/dataset/cex002_reference_release.py src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py scripts/research/publish_binance_usdm_harmonic_bundle.py tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py`
> 3. `.venv/bin/python scripts/check_repo_control.py`
>
> If all pass, create only
> research/sprint_004/495_CEX002_BUNDLE_INTEGRATION_RECORD.md with exact commands,
> exit codes/output summaries, five hashes and the actual model. Distinguish the
> developer's first 26/2 result and passing 28-case continuation from your own validation.
> Include that no real prepare/publish/consumer/data operation occurred and final release
> acceptance remains pending. This record is implementation evidence owned by Hermes.
>
> Recheck unchanged five source hashes, then stage exactly the five source/test paths
> enumerated in this review plus Record 495. Check `git diff --cached --check` and the
> staged path list. Never use git add -A, stage unrelated work, amend, reset or force push.
> Commit as `CEX-002: integrate harmonic reference release adapter`, push normally to the
> existing upstream, verify HEAD equals origin/main and the index is empty, and return
> the full commit hash, final hashes and validation results. Do not change reviewer
> acceptance or ticket status. Stop for reviewer inspection. No real preparation,
> publication, external checker or next ticket is authorized by this integration prompt.
