# CEX-002 Claude CLI Preflight Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed base: `b8c612edc72a2a9ef12802106d4424db32b7bc3a`

Reviewed source/test hashes:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `ee142aabf0a3df589940ab982ff0087f9deacc593517fe856af9760a900c5bcd` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `ec84ca6aa5b55e4dc89a70553922c070a8a1d96e6b15197911697b6b838bfa03` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `947bd55f3ff6354f75c803ea16a81eadecc68fb5bc7ef6a25e2e5254930ec41b` |

The 17 existing fixtures are unchanged. Static counting finds 168 test functions and no
duplicate test names.

## Decision

**REJECT BEFORE JR INTEGRATION. AUTHORIZE ONE CLI-AND-TEST ORDERING CORRECTION.**

Claude fully implements the two paths review 101 authorized. Candidate production preflight
now runs before production creates a directory or touches a mutable/remote facility; it
strictly requires current version 2 and ordered non-boolean integer history `[0, 1]`, parses
both historical plans, derives the missing version-0 content identity, loads the legacy
ledger read-only, reuses those exact in-memory authority objects, and rehashes lock and
ledger after construction. Focused source tests cover invalid lineage, complete file-tree
identity, no index/current/Coinalyze call, v0 digest reuse, and the real retained transition.

The production hash above is accepted and frozen. The current test source is accepted
subject only to the focused CLI case below. The reviewer ran no tests, lint, control
command, network/data command, migration, or real qualification.

## Blocking Finding: The CLI mutates before production preflight

The actual executable creates `store_root` at line 85, constructs transport state, loads
and bootstraps the listing checkpoint at lines 90-106, and loads the retry journal at lines
107-110. It calls `run_source_qualification` only at line 131. An invalid
`--candidate-plan-only` invocation can therefore change the store or listing/cache state
before the accepted production preflight sees the invalid lock.

The new no-mutation test invokes `run_source_qualification` directly, so it correctly proves
the production boundary but not the executable boundary Hermes must use for the real
candidate report.

Review 101 explicitly froze the CLI while also requiring preflight before any directory,
cache, checkpoint, journal, or remote-capable operation. Those requirements conflict. This
is a reviewer-authored scope error; Claude's authorized correction is otherwise accepted.

## Surgical Claude Authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `scripts/research/qualify_binance_usdm_harmonic_sources.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The accepted production hash and fixture directory must remain byte-identical. Claude must:

1. import and call the accepted `candidate_preflight` when and only when
   `--candidate-plan-only` is set;
2. compute the lock and legacy-ledger paths without creating the store, then preflight with
   the exact effective sample budget before `mkdir`, environment-backed client creation,
   transport construction, listing checkpoint load/bootstrap, retry-journal load, or any
   other cache/checkpoint/remote-capable operation;
3. handle preflight `SourceQualificationError` and `ResumeIntegrityError` through the
   existing redacted `ERROR:`/exit-1 CLI contract, without printing authority content or
   secrets;
4. leave normal noncandidate initialization and the accepted production revalidation
   unchanged; and
5. add one focused CLI-level test that starts from invalid candidate authority, invokes
   `main`, and proves exit 1, identical recursive files and directories, no report, no
   listing/bootstrap/retry/transport/current-contract/Coinalyze use, and no secret output.

Claude performs no tests, network/data run, plan or ledger migration, integration,
repository-record edit, Git operation, sample download, bulk acquisition, catalog mutation,
Nautilus work, Harmonic Trader work, or publication. It stops for reviewer source
inspection with the exact two hashes and test-function count.

## Publication Set

Under the reviewer governance-publication exception, the reviewer may stage, commit, and
push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/102_CEX002_CLAUDE_CLI_PREFLIGHT_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, database sidecar, or unrelated dirty path
belongs to this publication. The reviewer executes no acceptance command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Hermes is unauthorized. Gate 1 has not passed. Gate 2, real
acquisition, normalization, catalog publication, Nautilus execution, other-ticket work,
Harmonic Trader work, payoff analysis, PAPER, and LIVE remain unauthorized. Next ticket
remains `NONE`.
