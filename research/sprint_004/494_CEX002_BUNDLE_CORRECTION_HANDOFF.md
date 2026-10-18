# CEX-002 Review 494 — Bounded bundle correction handoff

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Selected senior: Sr Dev — Codex Sol, GPT-6 Sol High (gpt-6-sol, high)
Launch state: prepared for owner prompt relay or explicit direct-delegation approval
Disposition: source unaccepted; no integration or real run authorized

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
