# CEX-002 Migration Source Acceptance

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Governing reviews: `research/sprint_004/145_CEX002_VERSION4_CANDIDATE_REVIEW.md` and
`research/sprint_004/150_CEX002_SPARK_MIGRATION_TEST_REVIEW.md`

## Accepted source identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee9a794d96671763a6321373d70e3ed67d5c2f0c234ba94a234fd14308a9aae5` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `3b9181366ee4a575d450d06cf70340e1a2cf2c65d5239081f4782ebc9c6e4ced` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `6f38c99e19e0b4a48cbc9189302bdbfc225595807c0e64516338df6815d8a8a5` |

The test path contains 285 unique `test_` function definitions and `git diff --check` is
clean. The reviewer ran no test, Ruff, migration, candidate, network, or data command.

## Decision

**ACCEPT AND FREEZE THE THREE EXACT SOURCE IDENTITIES; AUTHORIZE HERMES FOR INTEGRATION,
FOCUSED COMMANDS, AND ONE REVIEWED MIGRATION-ONLY EXECUTION.**

The implementation closes reviews 145-150. It implements the fixed one-shot version-2 to
version-4 transaction, ledger-first and lock-last; refuses unsupported and mixed ordinary
states before execution; preserves the accepted report; validates the full installed
lock/ledger/prior-history/source authority; constrains amendment accounting to the reviewed
plan and allowance; and makes migration-only sample-checkpoint handling read-only. The
focused source tests cover the real CLI, interruption boundaries, idempotence, substitution,
malformed bindings, accounting, report preservation, and checkpoint immutability.

## Hermes integration

Jr Dev - Hermes first establishes `HEAD == origin/main` at this review-publication commit.
It rehashes the three accepted paths above and confirms 285 unique test definitions. A
mismatch stops before staging.

Hermes stages exactly the three accepted paths, commits and pushes one integration commit,
proves `HEAD == origin/main`, and proves the index is empty. It stages no control, review,
report, fixture, ignored evidence, database sidecar, or unrelated dirty path. It makes no
source/test edit and uses no reset, restore, checkout, stash, clean, or equivalent worktree
rewrite.

## Stop-on-first-failure commands

Only after the integration commit is pushed, Hermes runs these commands in order and stops
at the first nonzero exit:

1. `.venv/bin/python -m pytest tests/acquisition/test_binance_usdm_harmonic_qualification.py -q --tb=short`
2. `.venv/bin/python -m pytest tests/test_download_atomicity.py -q --tb=short`
3. `.venv/bin/python -m ruff check src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py scripts/research/qualify_binance_usdm_harmonic_sources.py src/source_audit/download.py tests/acquisition/test_binance_usdm_harmonic_qualification.py tests/test_download_atomicity.py`
4. `python3 scripts/check_repo_control.py`
5. `git show --check --oneline --no-renames HEAD`

Hermes retains the actual pytest pass/collection evidence and exact exit/output for each
command. A failure prevents the migration invocation.

## Migration preconditions

Only after all five commands pass, Hermes proves no qualification or candidate process is
running and captures a complete before snapshot. At minimum, it must re-prove:

- the three integrated source hashes above;
- accepted report 62 at exactly 13,946,727 bytes and SHA-256
  `f26abbc577307e5dcef693ec159fa65d1373d7b03c2be0eb6b926e5b09f97406`;
- version-2 lock SHA-256
  `e04a5ce2f2513cc8a0f4e6698dcbf9d43c5a7bec0295021ca5d431ff886f0d84`;
- legacy ledger SHA-256
  `47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6`;
- amendment ledger absence;
- sample checkpoint SHA-256
  `b60fe7b6d805f9cc14a67f1256978a742556b94949c3a74b89e1cf597d02ca7f`;
- retained raw tree at 186 files / 1,015,198,547 bytes / listing digest
  `ec06dcad4f761ff8564460d4921d026d2c35dd3ce38b44237f40194ceadf96dc`;
- the accepted manifest detail and all review-145 authority identities; and
- available bytes plus hashes/sizes of every state file the invocation may touch.

Any unexplained mismatch stops before migration and is recorded. Hermes does not repair,
delete, restore, or synthesize a precondition.

## One migration-only invocation

With all preconditions exact, Hermes loads `.env` only into the process environment and
makes exactly one foreground invocation:

```bash
set -a
. ./.env
set +a
timeout --signal=TERM --kill-after=60s 50m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --progress-path data/cex002_qualify/cex002_qualification_progress.json \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-migration-only
migration_status=$?
```

Hermes captures start/end timestamps, elapsed seconds, `migration_status`, and the complete
receipt/summary transcript. Status 2 is the expected terminal status after a successful
migration because the report remains Gate-1 blocked. Status 124 is incomplete; status 0 or
any other status is anomalous and must be recorded without retry. Every status stops after
this one invocation. No ordinary resume or second migration command is authorized.

## Required after-proof

Hermes records all filesystem/cache mutations and proves at minimum:

- accepted report 62 and its manifest detail are byte-identical;
- the installed lock is version 4 with plan digest
  `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`,
  exact versions 0-2 history, and preserved version-3 candidate lineage;
- the canonical content-addressed prior-lock evidence hashes to the accepted version-2
  lock and the legacy ledger remains byte-identical;
- the amendment ledger exists, is prepared/unspent, has empty charges/reservations, uses
  the fixed 268,435,456-byte allowance, and exactly matches the installed lock binding;
- the final source receipt exactly identifies the accepted production source and its
  code/config digest equals the installed lock input;
- the sample checkpoint remains byte-identical, samples remain empty, and the retained raw
  tree has no new or changed file;
- migration reports `executed=true` and `download_authorized=false`; and
- no accepted report, sample plan document, legacy ledger, sample checkpoint, or sample
  artifact was published or mutated outside the reviewed lock/amendment transaction.

The migration does not establish Gate 1 passage and authorizes no sample acquisition.

## Record and publication

Hermes writes `research/sprint_004/152_CEX002_MIGRATION_INTEGRATION_AND_EXECUTION.md` with
the integration commit, all command results, complete before/after evidence, migration
status/receipt, mutations, deviations, and terminal state.

After the invocation or any safe stop, Hermes updates both controls to `Next required
actor: Lead Quantitative Finance Researcher/Engineer - inspect record 152`, stages exactly
the two controls and record 152, commits and pushes, proves `HEAD == origin/main`, and
stops. It never stages the accepted report, evidence data, state files, database sidecars,
or unrelated dirty paths.

## Boundaries

No source/test edit after integration, retry, ordinary resume, second migration, sample
acquisition, Gate 2, normalization, catalog publication, Nautilus work, Harmonic Trader
work, payoff analysis, PAPER, LIVE, paid source, external artifact service, reduced scope,
or unrelated dirty-path mutation is authorized.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Next ticket remains `NONE`.
