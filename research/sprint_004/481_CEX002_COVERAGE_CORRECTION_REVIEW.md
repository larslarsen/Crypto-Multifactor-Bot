# CEX-002 Review 481 - Coverage correction review

- **Date:** 2026-10-16
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected coverage source; authorize the complete Hermes workflow below
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - nine of eleven products accepted
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Inspected source and authority

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_coverage.py` | 1,715 | `343b1bd816456c6625ff038f9a5303c483f3f4af8a97935d9a2139d14eeabfe9` |
| `scripts/research/normalize_binance_usdm_coverage.py` | 85 | `567f8ce77b7f19d1174fd9a9c074d541ac7cab823c63957a32f739c8b1097f5f` |
| `tests/ingest/test_binance_usdm_coverage.py` | 1,161 | `4a0dbcb9009c93f2c3cc18441b31fffa26229dfc56691de774719226e65ec60a` |

The correction addresses the original OI field mismatch, native-phase preservation,
distinct-slot daily predicates, partial-day reasons, cost component counts/source dates,
held-file scans, and staged/winning-byte verification. The CLI retains its accepted
identity. These improvements do not yet constitute source acceptance.

The reviewer read the nine completion JSON files and confirmed their hashes against
Review 480. Bounded hash-authenticated lineage examples confirmed the real quality-gap
and cost metadata shapes. No market-value audit, normalizer, test suite, Ruff, catalog
operation, or accepted-product rerun was executed. No complete targeted-test result was
available in this resumed conversation; cached test names are not execution evidence.

## Consolidated residuals

1. **Relative output roots fail at completion construction.** `normalize_coverage`
   computes an absolute `output`, and `_OutputTree` returns absolute artifact paths,
   but the completion's `manifests` comprehension calls
   `artifact.path.relative_to(output_root)` using the original argument. An ordinary
   `Path("data/.cex002_coverage")` therefore raises `ValueError` after publishing the
   reports. Normalize the output identity consistently, retain containment checks, and
   prove complete producer execution and replay with both relative and absolute paths.
   The existing fixture uses an absolute temporary root exclusively.

2. **The completion hook occurs after the final dependency/inventory proof.**
   `normalize_coverage` reproves inputs and audits the output, then `publish` invokes
   `before_publish` for completion. That hook can change a previously published report
   or a consumed input. Only the completion stage and winner are verified before its
   rename. The post-publication output audit detects changed reports after completion
   has become visible; it does not reprove inputs. Close this concrete ordering gap:
   the final precommit proof must follow the last externally callable hook and precede
   completion visibility. Preserve held descriptors, no-clobber publication, exact-byte
   replay and owned-stage cleanup. Test report and dependency mutation at that boundary
   and assert failure leaves no newly published completion. This is the existing
   completion-last contract, not a new publication architecture or a guarantee against
   arbitrary unsynchronized writers after a completed transaction.

3. **The complete producer fixture leaves the critical integration paths unproved.**
   `_complete_fixture` replaces `prove_coverage_authority` with a lambda over a report
   containing only `{"fixture":"accepted-report"}`. Six timestamp products have empty
   partition sets; quality gaps are entirely empty. The sole complete-producer case
   covers success and replay. Existing interruption, mutation, foreign-file and byte
   limit cases mostly exercise helpers, not completion visibility. Extend bounded
   fixtures to exercise the real report parser with representative accepted report
   shapes, nonempty price-state descriptors relative to their shared parent, actual
   quality-gap descriptors, detailed/funding-only/rejected and rowless identities.
   Fixture-only count/hash/allocation patches are permitted in the relevant modules;
   production pins and schemas remain frozen. Add complete-producer refusal cases for
   a foreign digest-shaped file, unexpected directory/non-regular entry, staged-file
   replacement, consumed-input mutation, output mutation before completion, interrupted
   completion and safe replay, and component/metadata overrun. Preserve the explicit
   nine-day/eight-day alignment example and add a 599-second OI interval alongside the
   existing 301-second case without inventing gaps. Prove refusal and completion absence,
   not merely that a helper raises an exception.

## Complete bounded developer assignment

Select **GPT-6.1-sol, High reasoning**, in the **Sr Dev - Codex Sol** role for this
correction, replacing GPT-5.6-sol for this bounded drop. DEVELOPMENT_ROLES.md permits
available OpenAI model selection. A fresh senior review is appropriate after the prior
correction left the completion boundary and full-producer coverage incomplete. Exactly
one senior is assigned. Review 480 records the owner's standing authorization for direct
delegation and consolidated reviewer feedback for this coverage assignment.

Read CURRENT_TASK, this review, Review 480, CEX-002's current checklist and original
requirements, ADR-0024, and DEVELOPMENT_ROLES. Edit only:

- `src/cryptofactors/ingest/binance_usdm_coverage.py`;
- `tests/ingest/test_binance_usdm_coverage.py`.

The existing CLI stays byte-identical. Correct all three residuals together, preserving
every Review-480 authority, schema, financial-semantic and allocation requirement.
Do not run real data, network calls, Ruff, acceptance commands, catalog operations or
Git; do not edit repository records, accepted inputs, fixtures outside the test module,
or any other source. No new dependency or architecture is assigned. Do not manufacture
an execution result for the preceding drop.

After finishing edits, execute this one targeted command exactly once under the AGENTS.md
senior test exception:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_coverage.py -q --tb=short
```

Stop on its first nonzero result; return the complete output and exact command without
patching and retrying. On success also stop for reviewer inspection. Return the bounded
change description and SHA-256/line counts of all three coverage files. Hermes retains
integration, acceptance execution, implementation evidence and implementation Git duties.
Hermes is not yet authorized. No other product or next ticket is authorized.

## Targeted result and fixture-only correction

The senior returned the complete correction and executed its authorized pytest once,
with exit `1` and this complete reported output:

```text
.....................F.................................................. [ 97%]
..                                                                       [100%]
=================================== FAILURES ===================================
____ test_oi_irregular_intervals_are_observed_without_invented_gaps[599000] ____
tests/ingest/test_binance_usdm_coverage.py:282: in test_oi_irregular_intervals_are_observed_without_invented_gaps
    assert scan.observed_by_day["2025-09-01"] == 288
E   assert 287 == 288
=========================== short test summary info ============================
FAILED tests/ingest/test_binance_usdm_coverage.py::test_oi_irregular_intervals_are_observed_without_invented_gaps[599000]
```

The reviewer inspected the complete correction. Production's relative-root identity and
post-hook precommit proof now satisfy the identified residuals. The expanded tests use
the real coverage-authority parser and full producer for the specified refusal and replay
paths. The sole listed test failure is a fixture boundary error: phase 1,234 ms plus the
299,000 ms shift makes the last observation occur on the following UTC day. Production
correctly reports 287 observations on September 1; its timestamp semantics must not change.

Freeze production at SHA-256
`6bb3788a91612d52fd204f9efc21a21e4a067eb679f387f16974915bcc501eee` (1,730 lines)
and the unchanged CLI hash above. The returned test file is SHA-256
`427175b97039104fe06af1626e020e330d5f568f6238113a6b55b0c386379fc2` (1,512 lines).

The same sole senior may edit only
`test_oi_irregular_intervals_are_observed_without_invented_gaps` in
`tests/ingest/test_binance_usdm_coverage.py`: use a nonzero phase below 1,000 ms
(500 ms is sufficient) so both 301-second and 599-second fixtures remain within the
declared day, and document that boundary choice. Retain the 288 observed/distinct counts,
irregular-cadence refusal, exact interval assertion and separate midnight-boundary test.
No production, CLI, other test or other path change is authorized. After this sole
correction, run the exact targeted pytest command above once, returning its full output,
exit and all three hashes/line counts. Stop on nonzero without patching or retrying.
Hermes remains unauthorized pending source acceptance.

## Final coverage source acceptance

The reviewer accepts the complete corrected three-file coverage drop for integration.
The fixture-only correction uses phase 500 ms and documents the final-row boundary.
Reversing that exact change in memory reproduces the previous test SHA-256 above;
production and CLI are unchanged. The senior ran the newly authorized focused command
once, exit `0`, with full reported output:

```text
........................................................................ [ 97%]
..                                                                       [100%]
```

All 74 cases passed. Reviewer independently reproved these final source identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_coverage.py` | 1,730 | `6bb3788a91612d52fd204f9efc21a21e4a067eb679f387f16974915bcc501eee` |
| `scripts/research/normalize_binance_usdm_coverage.py` | 85 | `567f8ce77b7f19d1174fd9a9c074d541ac7cab823c63957a32f739c8b1097f5f` |
| `tests/ingest/test_binance_usdm_coverage.py` | 1,513 | `a5c85b98dedef9e84e4f28bdb3529c26f3fd7e627cd05d10aa6f06bf8ad90eb1` |

The senior assignment is finished. This accepts source, not a coverage dataset or the
full ticket. Nine data products remain accepted until the real coverage result is reviewed.

## Complete Hermes integration, execution and evidence workflow

The owner has authorized direct developer prompting, recorded in Reviews 474, 476 and
478. Launch Jr Dev - Hermes for the following bounded workflow. Select
`meituan/longcat-2.5-preview:free` through Nous Portal, without a reasoning override.
The live public recommended-models endpoint checked on this review date lists it at
`$0.00/1M`; the previously used `meituan/longcat-2.0:free` is absent. Selection builds on
the previous Longcat integration/execution result, without asserting that this new model
version is already validated. Supervise execution and preserve the failure-stop boundary.

Run from `/home/lars/Crypto_Multifactor_Bot`. Stop at the first nonzero command or failed
proof. Do not patch source/tests, retry, delete output, or substitute another invocation.
After a failure, read-only failure inventory and terminal record publication are allowed.
Ordinary success proceeds through the whole sequence without another handoff. No full
ticket acceptance suite is assigned yet. The reviewer does not execute these commands.

### 1. Preproof and integration

Prove HEAD equals origin/main and includes this final authorization; capture the full
hash. Require empty `git diff --cached --name-only` output. Preserve the unrelated dirty
working tree; working-tree cleanliness is not required. Use `sha256sum` and `wc -l` to
reprove the three final source identities. Git blob SHA-1 is not file SHA-256.

Run each separately, inspecting its exit before proceeding:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_coverage.py -q --tb=short
PYTHONPATH=src .venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_coverage.py scripts/research/normalize_binance_usdm_coverage.py tests/ingest/test_binance_usdm_coverage.py
python3 scripts/check_repo_control.py
git diff --check
```

After all pass, stage exactly the three accepted Python files, inspect the staged set,
run `git diff --cached --check`, commit as
`CEX-002: integrate coverage ledger and daily alignment`, push, and prove
`HEAD == origin/main`. Reprove all three file hashes after integration.

### 2. One real local run

Reprove report/sizing/holdout and all nine sole completion hashes pinned in Review 480.
Use their real descriptor roots, including the shared price-state parent. Confirm the
accepted PyArrow 25.0.0 writer identity. Prove `data/.cex002_coverage` is absent and not
a symlink, and that no coverage normalizer is live. Record filesystem available bytes
with `statvfs.f_bavail * f_frsize`; retain the existing conservative
110,648,021,942-byte execution floor. Reviewer observed 219,138,945,024 available bytes
before this assignment; Hermes must measure its own current value.

Launch Hermes with `TERMINAL_MAX_FOREGROUND_TIMEOUT=43200`; request `timeout=43200` for
the real terminal command and remain attached through its terminal result. Do not use
a mechanism capped at 600 seconds, detach, a runner wrapper or a polling loop. Run once:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_coverage.py \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --holdout data/cex002_qualify/cex002_holdout_boundary.json \
  --membership-root data/.cex002_perpetual_membership \
  --bar-root data/.cex002_bar_1h \
  --trade-flow-root data/.cex002_trade_flow_1h \
  --open-interest-root data/.cex002_open_interest_5m \
  --funding-realized-root data/.cex002_funding_realized \
  --price-state-root data/.cex002_price_state \
  --liquidation-root data/.cex002_liquidation_observed_daily \
  --cost-root data/.cex002_cost_calibration \
  --output-root data/.cex002_coverage
```

Capture actual UTC before/after timestamps, duration, complete output, terminal exit,
and immediate post-run available bytes. This reads accepted local inputs and writes
only the new hidden coverage tree. No acquisition, quarantine, catalog transaction,
accepted-product rerun or harmonic model work is authorized.

### 3. Reconciliation and successful replay

On success, independently authenticate the sole completion, six manifests, every
referenced gap Parquet/lineage, daily report and instrument summary. Derive paths from
the producer's actual component layout and manifests; do not invent directory names.
Reconcile contained regular-file paths, hashes, sizes, actual schemas/row counts,
the exact complete inventory and empty staging. Verify component totals, largest-file
bounds, the measured metadata ledger and unchanged 570,896,384-byte reservation with
4,985,471,619 bytes reserved for remaining release metadata. No byte is allocated twice.

Read-only reviewer metadata observations are cross-checks, not Hermes execution evidence:

- all 771 identities and 237 exclusions remain represented;
- qualification source gaps: 8,317 rows / 4,817 partitions;
- typed gap memberships: 3,742 rows / 3,742 partitions;
- input normalized quality gaps total 68,220 rows: bars 154, flow 181, OI 57,441,
  indicative 1,215, basis 4,603, liquidation 4,626; funding has none;
- cost source gaps remain 494 referenced rows, fee gaps 771 referenced rows, no historical
  fee observations and two non-backdated policies;
- source/membership bounds and accepted partition months span 2019-09 through 2026-08:
  84 months and 64,764 expected symbol/month daily reports;
- 0GUSDT September 2025 retains nine five-product observed days and eight full-cadence
  days with event presence, with only 14 basis rows on September 22.

Independently aggregate daily predicate counts and reproduce their sorted symbol/day
digests using the exact documented row encoding, reconcile summaries to accepted input
descriptor row counts and gap counts, and verify rowless/funding-only identities remain.
Retain explicit funding expected-count unknown, observed/censored liquidation semantics,
native-phase OI, qualification-versus-observation gap distinctions and unknown availability.
Read only the necessary accepted timestamp/lineage facts for bounded independent examples;
do not re-audit 939 million accepted cost book values. Temporary read-only reconciliation
helpers are Hermes-owned implementation evidence and may be authored outside the repository,
with their identity and command recorded; they are not production/test changes.

After the run and reconciliation succeed, capture the full output path/hash/size/inode/
mtime inventory. Invoke the same exact command once more with the same timeout for the
authorized successful replay. Require exit 0, `completion_reused=true`, identical
completion bytes/digest and unchanged complete artifact inventory, inodes and mtimes.
This replay is permitted only after success; it is not a failure retry.

### 4. Terminal publication and stop

Publish the terminal result, including any first failure, as
`research/sprint_004/482_CEX002_COVERAGE_INTEGRATION_AND_REAL_RUN_RECORD.md`.
Include exact executed commands/exits, integration identity, source/completion hashes,
timing/capacity, actual component/report/intersection counts, all reconciliation and
replay evidence or exact missing evidence. Distinguish observations from projections
and reviewer inspections from Hermes-executed checks. Do not claim product acceptance.

Update only current fields/action/checklist in `docs/handoff/CURRENT_TASK.md` and
`tickets/CEX-002.md`, returning both actor fields to
`Lead Quantitative Finance Researcher/Engineer`. Keep nine products accepted pending
review, Gate 3 and CEX-002 `IN_PROGRESS`, and next ticket `NONE`. Do not append another
historical ticket narrative or edit this reviewer-authored review. Run repository-control
and whitespace checks separately, stage exactly Record 482 and those two control paths,
check staged paths/whitespace, commit, push, prove HEAD equals origin/main, and stop.
No bundle, Gate-0 mutation, other product, model or next ticket is authorized.

## Reviewer publication scope

The reviewer may publish exactly these governance paths under AGENTS.md:

- `research/sprint_004/481_CEX002_COVERAGE_CORRECTION_REVIEW.md`;
- `tickets/CEX-002.md` (current checklist/action only);
- `docs/handoff/CURRENT_TASK.md`.

Run repository-control and whitespace checks for this documentation publication only.
Preserve the unrelated dirty baseline and leave all developer files unintegrated. Review
474's fixed closeout still governs: coverage, remaining reconciliation, Gate-0 quarantine,
bundle/catalog, clean consumer readback, replay and original final acceptance evidence.
