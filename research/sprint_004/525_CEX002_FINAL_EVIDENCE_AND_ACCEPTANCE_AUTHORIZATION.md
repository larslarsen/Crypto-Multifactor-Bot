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


## Concrete historical-universe findings after HT-004

The owner reiterates that "data" means usable survivorship-aware research inputs, not
merely readable market files. The original requirement is unchanged. No source or data
mutation was performed in this inspection.

A read-only query of all 771 published membership rows establishes:
- 698 rows use the retained exchangeInfo snapshot; 73 names are absent from that snapshot
  and are retained through official realized-funding evidence, rather than dropped.
- All 73 funding-only rows lack onboard_ms, delivery_ms, closed_observed_ms, base_asset,
  quote_asset and margin_asset. Their status is explicitly funding_only_terms_unavailable.
- The snapshot rows contain 570 TRADING, 127 SETTLING and one PENDING_TRADING contract.
  These are snapshot statuses, not a historical sequence of statuses.
- All 771 canonical instrument identifiers remain null. Native symbols exist, but the
  release has not supplied the contract-version mappings required by the HT contract.

The upstream membership acceptance established retention and faithful classification;
it did not establish complete dated contract terms. Do not erase the 73 names, treat
current status as historical status, or equate a first/last observed bar with an official
listing/delisting announcement. Nor should missing exact publication timestamps alone be
used to declare every historical series unusable: per-product timing rules still require
an explicit assessment.

A concrete recoverable example is AERGOUSDT. Official Binance notices establish:
- Launch 2024-09-10 12:15 UTC, AERGO underlying, USDT settlement, launch tick0.0001:
  https://www.binance.com/en/support/announcement/detail/de870af81e8d42cd903b84a97fa5bc91
- New positions stop 2025-03-27 08:30 UTC, automatic settlement09:00 UTC:
  https://www.binance.com/en/support/announcement/detail/db7ad1c7aa6248cda735102cdcdc4b8d
- Relaunch 2025-04-16 11:00 UTC, AERGO underlying, USDT settlement, launch tick0.00001:
  https://www.binance.com/en/support/announcement/detail/82f730b7ef444a38b323ab7a2e56b757
- New non-reduce-only orders stop 2026-07-24 06:00 UTC, settlement06:30 UTC:
  https://www.binance.com/en/support/announcement/detail/f0e3fc835b9545759e4279c64b200389

These are official documented effective events, not proof that every intermediate
contract specification remained unchanged. The displayed announcement publication times
have not yet been assigned a verified timezone or treated as archived receipt timestamps.
The current undated AERGOUSDT membership row does not represent these distinct episodes.

Repair work must recover dated trading episodes and needed contract terms without
rewriting market history, then apply them when selecting research observations. The
existing reference models already express LIST/DELIST/SUSPEND/RESUME and dated instrument
versions; do not build another generic reference framework. All published products,
prior storage checks and explicit gaps remain intact. Full data readiness is not claimed.

## Dated notice recovery — current CEX-002 assignment

The owner's continued instruction authorizes recovery of the missing historical contract
facts. The previous execution withdrawal applies to the superseded full-suite workflow,
not to this substantive repair. Reviewer research now records official notice facts in
`research/sprint_004/cex002_contract_notice_facts.json`. This exact additional path is
authorized for reviewer research publication alongside the three governance paths above.
It is a source-research attachment, not an integrated reference release or implementation
evidence. It retains all 73 missing-snapshot names and marks every history incomplete.

Record launches, restrictions on new positions/orders, and scheduled automatic settlement
separately. Preserve postponements and superseded announcements; do not apply the first
announced date after a correction. Launch terms apply at launch only. A spot token swap
does not establish automatic continuation of a futures position into its successor.
No release files are rewritten and no broad test or market-data download is authorized.
The remaining work is completion/reconciliation of the dated facts and their integration
into historical instrument selection, plus the already identified product timing rules.

### Recovered authority and closure-month observations

The reviewer research publication additionally includes the exact path
`research/sprint_004/cex002_contract_boundary_observations.json`. Together with the facts
attachment and the three previously enumerated governance paths, these are the only five
paths authorized for this reviewer publication. Neither JSON is an accepted release,
developer implementation record, or acceptance result.

The facts attachment contains 73 event groups with official source links. Among the 73
missing-snapshot names, 71 have a closing notice and 14 have a launch notice. Zero histories
are complete. ANCBUSD and AUCTIONBUSD still lack recovered primary closing notices; the
59 missing launch names are enumerated in the attachment. FTTBUSD's May and November 2022
closing notices conflict with positive-volume bars after the May date; do not infer either
continuous trading or an unannounced relaunch. The 698 snapshot names are not covered by
this recovery count and still need dated-history assessment.

The read-only observations cover 73 closure boundaries for 71 names, using 145 distinct
selected market files totaling 2,473,703 bytes (reader manifest metadata is additional).
Each result identifies its fact, boundary, file path and SHA256; the final facts attachment
is also SHA256-bound. The original 72 queries were not rerun when the LEND closure query
was added. AERGO's boundary-bar detail rereads one already selected file.

Seventy-one boundaries have hourly bars whose open is at/after the announced boundary;
65 have realized-funding source timestamps strictly after it. These are scope-limited
counts, not proof of payment, execution, or whole-history completeness. Concrete examples:

- AERGO March2025: 111 hourly bars at/after settlement; only the boundary bar has positive
  volume (50 trades). The other 110 have zero trades. There are 27 later funding rows.
- FTTBUSD November2022: 403 later hourly bars, all zero trade count and zero volume.
  Its May2022 boundary instead has 303 later positive-trade bars, so the conflict matters.
- LEND October2020: 528 hourly bars at/after settlement, all zero trade count and volume;
  the one funding observation after settlement is only five milliseconds later. It may
  represent a terminal payment; a naive strict timestamp cutoff could remove it wrongly.

Reviewer decision: preserve raw rows, distinguish execution eligibility from final
settlement/cashflow treatment, and resolve repeated symbols as separate dated episodes.
Do not turn these partial research facts into automatic filters or complete reference
versions yet. Publication headers retain unknown timezone/knowledge time. The next work
is the explicitly listed missing authority and its application through existing reference
models and the delivered consumer, not another market-data conversion or broad test run.
No production/test source, accepted release, or data catalog changed during this research.


## Recovered notices and resolved snapshot episode discrepancies

This section supersedes the missing-notice counts and unresolved FTT interpretation above.
The exact reviewer publication set remains the same five paths enumerated above.

The facts attachment now contains 134 notice groups. All 73 missing-snapshot names have
recovered launch and closing notices. FTTBUSD's planned May 19, 2022 settlement was
explicitly cancelled; later positive-volume bars therefore do not require an invented
relaunch. BTTUSDT's September 2020 launch was cancelled and its April 2021 launch is a
separate notice. ADA, XRP and DOGE BUSD launch postponements are retained, including the
second DOGE postponement. ANCBUSD/AUCTIONBUSD close at the announced December 15, 2022
09:00 UTC settlement start. Earlier unknowns are resolved only to these specific extents.

Recovery used the public Binance CMS article list and detail APIs, retaining small raw
responses in /tmp/cex002_notice_recovery. Listing, delisting and latest-news indexes were
cached; no market-data acquisition was performed. API publishDate is retained as claimed
source publication time, separately from response-file save time. Neither proves an
original unmodified revision or historical receipt. Research known_from remains null.
An initial episode-read call's session identifier was not retained by the orchestration;
a second cache-reusing invocation completed and reported its terminal result. Some tail
requests may overlap; do not claim exactly-once HTTP recovery. No market query was repeated
by that invocation. Cached responses and extracted facts bind to their saved SHA256.

The read-only monthly manifest screen examined all 698 snapshot rows and identified 12
with bar partitions earlier than their snapshot onboard month. Primary notices classify
all 12, using 37 linked source records in facts.snapshot_episode_reviews:

| Symbol | Recovered distinction |
| --- | --- |
| AIAUSDT | September 2025 launch, December settlement, January 2026 relaunch after a postponed proposal |
| BNXUSDT | April 2022 launch, February 2023 settlement and relaunch; old chart named BNXUSDTSETTLED |
| CTKUSDT | November 2020 launch, April 2024 settlement, April 2025 relaunch |
| CVCUSDT | November 2020 launch, November 2022 settlement, May 2025 relaunch |
| CVXUSDT | September 2022 launch, May 2024 settlement, July 2025 relaunch |
| ICPUSDT | May 2021 launch, June 2022 settlement, September 2022 relaunch; old contract named ICPUSDT_SETTLED |
| MAVIAUSDT | February 2024 launch, December settlement, March 2025 relaunch postponed to 17:00 UTC |
| SLPUSDT | October 2023 launch, May 2024 settlement, July 2025 relaunch |
| TLMUSDT | July 2021 launch, June 2022 settlement, March 2023 relaunch |
| LITUSDT | Earlier Litentry contract settled January 2025; December 2025 contract is Lighter Protocol |
| PUMPUSDT | Earlier PumpBTC contract settled June 2025 before PUMPBTCUSDT replacement; July 2025 contract is Pump.fun |
| ETHBTC | Official April 26, 2023 launch predates snapshot May 25 onboard; explicitly BTC-settled linear contract |

BNX, ICP, TLM and ETHBTC demonstrate that snapshot onboard timestamps are not reliable
substitutes for the announced trading start. The screen does not establish complete
histories for the other 686 snapshot rows and cannot detect reuse within one month.
The two pre-market conversions (Lighter and Pump.fun) explicitly retain positions; they
are terms/regime transitions, unlike the automatic settlements that close positions.

Only the two newly recovered closure months were queried: four files /69,988 bytes,
appended to preserved earlier observations. Total unique selected market files are now
149 /2,543,691 bytes. There are 75 saved queries across all 73 names, including one now
cancelled FTT proposal. Excluding it yields 74 announced boundaries, 72 with bar opens
at/after the boundary and 66 with later funding timestamps. ANCBUSD and AUCTIONBUSD each
have 399 zero-trade bars and 49 nonzero funding-rate observations after settlement in
December 2022. Neither observation supplies an executable price or payable cashflow.
The original FTT query is retained with its corrected status, not silently erased.

### Concrete consumer application decisions

1. Keep the accepted market publication unchanged. Dated reference information accompanies
   existing files; do not copy or normalize the billion-row release again. Preserve every
   native name and all explicit gaps, including names absent from current snapshots.
2. Resolve a native symbol by historical episode before constructing a Nautilus instrument.
   LIT/PUMP underlying reuse needs different asset identities. Closure/relaunch needs
   separate contract episodes even when the underlying stays the same. A token swap or
   rename does not carry a futures position across an explicit automatic settlement.
   Do not strip SETTLED suffixes to admit previously excluded alias files: ADR-0020 still
   requires evidence of the actual non-overlapping interval and retained raw lineage.
3. Use the existing reference model's dated instrument versions, aliases and listing
   events. Snapshot fields retain their observation date; do not project a current tick
   size, settlement currency or status backward over an older episode. Launch terms are
   launch terms only. Missing historical specifications remain named gaps, not defaults.
4. Preserve cancelled/postponed proposals as evidence, but never apply them as trading
   boundaries. Apply only the corrected event. Separate new-position restrictions from
   settlement and from reductions of existing positions. Automatic settlement start is
   not a measured completion timestamp.
5. A native hourly bar that straddles launch, restriction or settlement cannot establish
   full-hour executable prices. Retain the original observation and its interval; identify
   its boundary relationship for the consumer rather than granting full-hour eligibility
   or deleting it. Zero-trade post-settlement bars must not create new trading eligibility.
6. Realized-funding source rates are observations, not a portfolio's cashflow ledger.
   Require contract episode and position eligibility before booking a payment. Preserve
   possible terminal observations such as LEND's boundary +5ms separately from recurring
   post-close rates; no blanket timestamp clip or automatic post-close payment is accepted.
7. Keep effective time, claimed publication time and actual knowledge/receipt time separate.
   REF-001 requires a non-null known_from: integration must use an evidenced research receipt
   or explicitly selected retrospective knowledge date, never silently use the effective
   date. Historical decision-time queries must not inherit today's recovered information.
   Existing explicit event-time transport remains an assumption, not source-clock proof.

These decisions bound the application of recovered facts; they do not accept a reference
release or claim the consumer enforces them already. A source assignment must enumerate
its paths and tests and preserve Hermes's CMB integration ownership. No developer was
launched in this continuation. Source/test code, accepted data and catalog remain unchanged.
The remaining work is applying these identities/restrictions, resolving required dated
specifications and per-product availability, and reviewing the actual consumer behavior.
The broad stopped suite and full storage proof are not to be rerun. CEX-002 remains
IN_PROGRESS; reviewer remains the next required actor; next ticket and authorization NONE.


## Dated contract companion — bounded source authorization

The owner's continued instruction authorizes implementation of the application decisions.
ADR-0041 defines a small reference companion without changing accepted market files.
The reviewer selects the existing GPT-6 Sol High senior (bundle_correction_sol): it authored
accepted HT-004 and the corrected CEX release work. One senior only; GPT-6.1 is not selected
as developer. Direct bounded delegation continues the owner's established permission.

Exact CMB senior-owned paths:
- src/cryptofactors/reference/cex002_contract_history.py
- tests/reference/test_cex002_contract_history.py

Exact HT senior-owned paths in /tmp/harmonic_cex002_delivery, under HT-005:
- src/harmonic_trader/data/cex002_history.py
- src/harmonic_trader/integration/cex002_data.py
- src/harmonic_trader/cex002.py
- tests/test_cex002_history.py

Author source/tests only. No tests, API probes, Git, packages, real data, database writes,
research/governance edits or publication by senior. Return frozen hashes and stop for review.
CMB integration and checks belong to Hermes. HT checks and integration belong to its reviewer.

### Frozen implementation contract

CMB module: pure compile function accepting the facts mapping, exact facts SHA256, market
publication SHA256 and explicit timezone-aware known_from. A small module CLI accepts
--facts, --facts-sha, --publication-sha and --known-from, authenticates a regular non-symlink
facts file bounded to 4MiB and prints deterministic JSON to stdout. No network, market files,
SQLite writes, implicit clock or output-file mutation. Expose the existing REF-001 typed
Asset, Instrument, InstrumentVersion, AliasRecord and ListingEvent objects in the compile
result as well as a JSON-serializable document; use existing identity helpers/fingerprint.

Document: document_type=cex002_contract_history, schema_version=1, publication_sha256,
facts_sha256, known_from, history_complete=false, episodes and unresolved_symbols. Each
sorted episode has native_symbol, asset_id, instrument_id, instrument_version_id,
launch_ms, execution_end_ms (nullable), new_positions_stop_ms (nullable), source_urls,
launch_terms, historical_terms_complete=false. Preserve restriction event kind and all
source references in evidence; include pre-market regime/transition events separately.
IDs use venue, native symbol, explicit launch timestamp and documented launch source as
identity material, never native symbol alone or global facts digest. Added unrelated facts
must not change an existing episode ID. Use DERIVATIVE_UNDERLIER for the conservative asset
identity as specified in ADR-0041. Version contract_spec labels launch_terms only; it must
not imply those terms persisted through the episode.

Expand grouped notices by their native_symbols. Read both notices and snapshot_episode_reviews
cases. Merge identical symbol/event/time facts with their evidence; do not duplicate the
same closure from both sections. Ignore cancelled/postponed events and any event with
executable_boundary=false. Unknown event types that affect execution must raise, not silently
vanish. Associate each restriction/closure with its chronologically preceding launch; reject
conflicting overlapping launches or impossible ordering rather than guessing. Sources without
a recovered launch remain unresolved, with explicit reason; do not drop them. Repeated launch
and closure pairs become separate instruments. Explicit snapshot case terms supplement the
matching launch only. Non-execution pre-market transition facts must survive in evidence and
must not split a position book. Never consume a future fact by silently assigning its effective
time to known_from. All original histories remain incomplete.

Harmonic consumer: ContractHistory loads a regular non-symlink companion bounded to 4MiB,
requires caller-supplied SHA256 and matching publication SHA, validates types/intervals/unique
IDs and rejects overlapping episodes. No CMB imports. Expose classify(symbol,start_ms,end_ms,
knowledge_time) with an explicit half-open observation interval. Knowledge earlier than the
companion date returns unknown, not a current reconstruction. Classifications distinguish
within_known_episode, before_known_launch, between_episodes, at_or_after_execution_end,
new_positions_restricted, crosses_boundary, unknown_symbol and unknown_at_knowledge_time.
These describe the recovered schedule, not certified trade availability. Return episode IDs,
evidence and incomplete-history flag; do not infer a terminal payment from a rate timestamp.

Expose annotate_row/iter_history_rows using original ReleasedRow without mutating its fields.
Bars/flow/price-state use [open_time,close_time+1); point observations use [t,t+1ms); liquidation
uses the original UTC-day interval. Metadata/gaps remain accessible with no invented market
interval. Resolve symbol from the documented row field when partition-native_symbol is null;
validate conflicts with a non-null partition symbol. Funding annotation always says payment
eligibility is not established, preserving even a boundary+5ms observation.

Add optional history and explicit knowledge_time/reference_policy parameters to native_bar
and deliver_to_nautilus. With history, require reference_policy=reviewed_notices_assumption,
a matching publication binding, and classify the FULL bar interval as within_known_episode;
otherwise raise a specific Cex002ReaderError. Use the companion canonical instrument ID as
Nautilus Symbol under BINANCE, so successive contracts cannot share a BarType. Preserve raw
venue_symbol in original-field custom events. Mixed-episode batches must not lose callbacks:
either subscribe to every distinct BarType or reject before engine creation with a clear
single-episode requirement. Never silently drop rows or book funding. Without history retain
HT-004 explicit event-time-only behavior and label it unqualified.

CLI rows/nautilus accept --history PATH --history-sha SHA --knowledge-time UTC and, for
history-aware native projection, --reference-policy reviewed_notices_assumption. Require
complete option combinations. Rows print reference classification alongside original fields;
Nautilus output identifies qualification and companion digest. Existing all-product inventory
and raw access remain unchanged. No strategy, orders or execution-model claim.

Synthetic tests must cover actual cancellations (FTT/BTT patterns), closure/relaunch and
LIT/PUMP identity separation, unrelated-fact identity stability, restriction vs settlement,
whole-bar crossing and exact boundaries, terminal funding observation preservation, knowledge
cutoff, source/payload digest and publication mismatch, malformed/overlapping episodes, and
real Nautilus canonical BarType creation/delivery. Do not use a fake Nautilus module.

### Publication and validation ownership

Reviewer governance publication is now exactly CURRENT_TASK.md, tickets/CEX-002.md, this
Review525 and docs/adr/0041-cex002-dated-contract-companion.md (paths relative to repo, with
CURRENT_TASK under docs/handoff and Review525 under research/sprint_004). Existing research
attachments are read-only for this drop. HT reviewer publishes its own HT-005 governance.

After source inspection, Hermes may be assigned these exact CMB checks once:
PYTHONPATH=src .venv/bin/python -m pytest tests/reference/test_cex002_contract_history.py tests/reference/test_ref_store.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/reference/cex002_contract_history.py tests/reference/test_cex002_contract_history.py
python scripts/check_repo_control.py

Do not run yet: reviewer must inspect the frozen drop and issue the bounded Hermes prompt.
No broad suite, full storage proof or market scan. Any failure stops for a targeted source
correction. Real companion generation is separately bounded after passing source validation;
it may read the small facts attachment only. CEX-002 remains IN_PROGRESS; next ticket NONE.
