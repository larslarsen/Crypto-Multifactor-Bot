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
