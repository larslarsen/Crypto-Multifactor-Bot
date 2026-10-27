# CEX-002 Review 525 — Final evidence and acceptance-command authorization

- Reviewer: Lead Quantitative Finance Researcher/Engineer
- Ticket: CEX-002, IN_PROGRESS
- Next required actor: Jr Dev — Hermes
- Next ticket and authorization: NONE

## Decision and scope

Continue the fixed Review-474 closeout. Review522 accepted the 773.097-second
known-release replay/readback; it and all previously accepted acquisition, products,
coverage, consumer proof and admission remain accepted. No repeat is assigned.
No source/test author or new implementation is needed for this evidence assignment.
Hermes owns the ordered workflow below through terminal evidence publication, using
the already approved directly supervised native route. Select Nous
`stepfun/step-3.7-flash:free`, which completed the previous integration and real run;
its documentary errors were disclosed, so this assignment uses an explicit evidence
checklist and exact publication set. Preserve normal approvals. Provider rejection
is not a command failure or permission to substitute fabricated results.

## Ordered final commands

First prove HEAD equals origin/main, empty index, and record the existing dirty paths.
Run the original ticket commands exactly, in order, with actual output/status/timing:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
python3 scripts/check_repo_control.py
git diff --check
```

Use the project environment and current workspace; disclose unrelated tracked and
untracked source present. Do not hide it, exclude tests, change PYTHONPATH, install
packages, fix source, weaken assertions or change the required commands. Native
background execution with output capture is permitted. Record the process identifier
and use the same job until terminal; poll at most every 60 seconds, no duplicate launch.
A 3600-second outer deadline bounds the pytest job; timeout is not PASS. Stop subsequent
validation/economic work on the first nonzero result and publish the actual failure.
Do not rerun a successful command. Reviewer diagnoses any blocker before corrective work.

## Bounded economic evidence, only after the commands pass

Use already accepted evidence where it supplies the exact requirement. Record475 and
Review476 cover basis; Record477 independently recomputed all liquidation values and
all 18 price/OI/funding overlap comparisons; Record490/Review491 cover bounded minute
aggregation and taker flow. Cite exact sections and retained identities. Do not rescan
whole products or rerun their normalizers. The outstanding explicit examples are OI
notional/source preservation and realized long/short cashflow.

Perform read-only evidence queries, not new production/test source. Follow accepted
completion descriptors to at most three nonempty partitions for each of OI and realized
funding, selecting deterministically by symbol/month. Authenticate selected Parquet,
lineage and referenced raw files by recorded size/hash; inspect schema first rather than
guessing fields. Bound raw ZIP expansion to the selected existing member. Retain exact
commands and values/units/native symbol/time/source identity/original row ordinal.
Use decimal strings with exact Fraction/integer arithmetic, no floats or normalizer
arithmetic helpers. At most 12 displayed examples total; no new acquired data.

For OI independently parse the retained raw `sum_open_interest` and
`sum_open_interest_value` decimal tokens and show exact equality with the normalized
stock and quote-notional fields. Independently subtract adjacent contiguous observations
to verify `open_interest_value_change` and `open_interest_change`; gaps must not imply a
change. Notional is a source-reported stock, not an hourly-price-derived estimate: do not
invent an independent mark price or claim an implied-price tautology proves venue valuation.
Disclose that valuation-method limitation explicitly. This is the retained-notional
reconciliation required by Gate4 under the existing source-preserving product contract.

For realized funding independently parse source settlement rate and interval; prove
long_cashflow_rate = -last_funding_rate, short_cashflow_rate = last_funding_rate and
sum = 0 exactly. Include positive and negative observed rates when present in the bounded
selected partitions, report if a sign is absent; zero may be shown when actually observed.
Do not annualize, divide by interval, invent a position/notional, or impute settlement times.
Retain all source/output values, not just a PASS assertion. Stop on any mismatch and report.

## Consolidated report and terminal publication

Hermes writes exactly:
`research/sprint_004/526_CEX002_FINAL_RELEASE_AND_ACCEPTANCE_RECORD.md`.
On a failed command, publish a concise failure record including exact output, command,
status, elapsed time, environment/worktree state and which steps remain unperformed.
On success, include the bounded economic evidence and a consolidated release report:

- All eleven products: manifest/completion/schema pins, actual rows/files/bytes and typed
  gaps, with links to accepted product records. Read the small admitted descriptor and
  candidate for pins; no full proof JSON load or complete inventory/hash/row scan.
- Full historical universe, per-instrument/product coverage artifact, full daily
  intersection, known source-availability limits, duplicates/revisions and storage
  accounting, citing Records483/484 and accepted raw/normalization evidence.
- Five-artifact Gate0 quarantine and normalizer correction: Reviews485/487,
  Records486/488, and unchanged five-row digest from accepted Record524.
- Prospective holdout 2026-08-21T16:19:08.994166+00:00, observed/censored liquidation,
  unavailable indicative rates, measured Coinalyze OI differences/ETH absences, fee
  assumptions/gaps and accepted cost sizing discrepancy; no overstated tradability.
- Prepared candidate8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34,
  admitted publication5ea22270b71064c94c4f6dc60f3f045219742a3130cfdb1293b6cbe47a99a30d,
  accepted full consumer proof3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d,
  source/checker identities, catalog/file/row/byte reconciliation and replay evidence.
  Historical 1,165,116,869-row consumer proof and fresh 423,446-file replay proof are
  distinct; the old capacity-failed replay stays FAILED.
- A compact acceptance-item evidence map, exact original execution commands/exit codes
  by reference to accepted records, and the four new actual final-command outcomes.
  Missing evidence remains explicit, never inferred PASS. No full-ticket acceptance claim.

Publish only Record526. Require unchanged integration HEAD (apart from this record),
empty index before staging, then stage exactly that path and ASSERT the staged path set
is exactly one path. Run cached whitespace, ordinary commit and push, verify
HEAD == origin/main and empty index. Preserve all unrelated dirt. On publication denial
retain the local record and report the exact block. Stop for reviewer disposition;
no source repair, data mutation, cleanup, model/backtest/trading or next ticket.
Reviewer retains monitoring through actual completion and record publication.

## Reviewer governance publication whitelist

The reviewer may author/stage/commit/push exactly this Review525,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
This exception does not include Record526, command execution or implementation evidence.

## Observed environment failure and bounded continuation

The initial attempt failed collection with missing `nautilus_trader`, pytest exit2,
capture exit0. Native terminal message100264 records this; its ALL_STEPS_PASSED marker
is false. Ruff/control/whitespace did actually pass. Hermes violated the stop rule by
continuing these commands, added an unauthorized PYTHONPATH=src prefix, and did not
capture pytest start/end timing or use native background execution. Earlier it confused
worktree dirt with staging dirt; the corrected cached-index check passed. Record526
must disclose these facts. No test body, economic query or release rerun was performed.
The initial Record526 at86ac571 labels abbreviated traceback as exact; the full captured
output is /tmp/cex002_pytest.out. Preserve/correct it by append rather than erase history.
These procedural defects do not turn the collection failure into success.

Read-only dependency diagnosis: the test explicitly requires real NautilusTrader;
Review511/ADR0039 pin 2.0.0rc3. The accepted isolated consumer environment contains it,
but project .venv does not. Project metadata already has PyArrow25.0.0 and
Pydantic2.13.4, matching that environment, and the repository is installed editable.
Do not change tests, skip the consumer tests or override PYTHONPATH. This is environment
setup, not a new source drop or a rerun of the full release consumer proof.

Because Step repeated explicit control errors, rotate the Hermes backend to
`poolside/laguna-s-2.1:free`, previously successful for this release's integration checks,
in a concise fresh native session. Prior upstream429 is availability evidence, not a
semantic rejection. If currently unavailable, report that result before another choice;
do not repeatedly relaunch failed model requests. The native Hermes role and ownership
remain unchanged. Close the old idle session only after its record publication finishes.

Authorize Hermes to install exactly the missing pinned base package with no dependency
upgrades, then verify installed versions and package dependencies:

```bash
uv pip install --no-config --python .venv/bin/python --default-index https://pypi.org/simple --no-deps 'nautilus-trader==2.0.0rc3'
uv pip check --python .venv/bin/python
```

If installation/check fails, stop and record it. Do not rebuild .venv, modify the clean
consumer environment, change package configuration, install extras or repair other
packages. Metadata readback must report Nautilus2.0.0rc3, PyArrow25.0.0 and Pydantic2.13.4.

Then run exactly `.venv/bin/python -m pytest tests/ -q --tb=short` in the project root,
with inherited PYTHONPATH absent (normal native session setup already unsets it).
Use native terminal background=true, notify_on_complete=true, pty=false; capture to a
new /tmp log, preserve the earlier log, record actual UTC start/end and command/capture
exit codes, and an outer timeout3600s. Explicitly stop the workflow if pytest or capture
is nonzero. No `set -e` construction that loses the status, and no PASS marker after a
failure. Monitor the same job; never launch a second while it is active.

On success reuse the already passed Ruff/control/whitespace outcomes, continue the
bounded OI/funding examples and consolidated report above without another handoff.
Append all evidence and corrections to the SAME Record526; no new numbered record.
On failure publish that result and stop. Preserve the initial failure. Exact publication
set remains only Record526, with cached-index assertion, ordinary commit/push and
HEAD/origin equality. No accepted data scans, source fixes or next ticket. Reviewer
will assess the actual final result and retains monitoring responsibility.

## Execution authorization withdrawn — owner challenges delivery direction

The owner explicitly objects to further scope/time/disk expenditure without complete
usable NautilusTrader data and rejects a smaller/sample substitute. Reviewer stops the
broad suite and withdraws all remaining workflow execution. Preserve existing data and
logs; no source, test retry, installation, report expansion, cleanup or acquisition.
Native jobproc_6306587df26b was interrupted by reviewer SIGTERM to verified pytest
PID4188203 (parent4188127, exact expected argv, no children). This supervision action
executes no test or evidence calculation. Partial output at
/tmp/cex002_pytest_r_retry.aXQOHA remains incomplete and contains failures; no PASS.
Hermes automation is stopped. Pytest terminated at 2026-10-27T01:23:12.017055107Z
with PYTEST_EXIT=143; the wrapper exit0 does not change the interrupted test result.
Full-ticket acceptance is not granted. Existing
accepted consumer/replay checks are not a claim of a finished usable catalog handoff.
Reviewer retains delivery-scope reassessment; next ticket/authorization remain NONE.


## Reviewer publication of the stopped workflow and delivered reader

HT-004 is reviewed and integrated in the independent Harmonic Trader repository at
80490b6. It provides complete read-only CEX access and tested native transport without
a second full catalog. Unknown source publication times remain unresolved; explicit
event-time playback is not proof of causal historical availability. The earlier full
consumer proof, accepted source data and unfinished CEX-002 gates keep their status.

This reviewer-authored governance publication is limited to these exact CMB paths:
- docs/handoff/CURRENT_TASK.md
- tickets/CEX-002.md
- research/sprint_004/525_CEX002_FINAL_EVIDENCE_AND_ACCEPTANCE_AUTHORIZATION.md

The reviewer may stage/commit/push only those paths under AGENTS.md's governance
publication exception. This publishes no developer source or implementation evidence
in CMB, executes no CMB acceptance command and mutates no release data. No CMB next
ticket, broad suite retry, acquisition or scored experiment is authorized.
