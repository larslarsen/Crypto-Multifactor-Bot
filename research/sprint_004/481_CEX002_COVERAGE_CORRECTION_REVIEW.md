# CEX-002 Review 481 - Coverage correction review

- **Date:** 2026-10-16
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject the current coverage correction for integration; authorize the bounded correction below
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - nine of eleven products accepted
- **Next required actor:** Sr Dev - Codex Sol
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

## Reviewer publication scope

The reviewer may publish exactly these governance paths under AGENTS.md:

- `research/sprint_004/481_CEX002_COVERAGE_CORRECTION_REVIEW.md`;
- `tickets/CEX-002.md` (current checklist/action only);
- `docs/handoff/CURRENT_TASK.md`.

Run repository-control and whitespace checks for this documentation publication only.
Preserve the unrelated dirty baseline and leave all developer files unintegrated. Review
474's fixed closeout still governs: coverage, remaining reconciliation, Gate-0 quarantine,
bundle/catalog, clean consumer readback, replay and original final acceptance evidence.
