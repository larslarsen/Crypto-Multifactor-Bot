# CEX-002 — Review529: admit confirmed later history without inventing launches

Status: ACCEPTED COMPONENT. CEX-002 IN_PROGRESS; next ticket NONE.

The reviewer authorizes one senior source drop under ADR0042. Select Codex Sol 6.1 High
for a bounded compiler/reader change; the reviewer owns evidence, validation and Git under
the owner's CEX repair override. No concurrent senior developer. HT-005 is reopened only
for this cross-repository reader correction; no new ticket or strategy is authorized.

Source/test paths: CMB `src/cryptofactors/reference/cex002_contract_history.py` and
`tests/reference/test_cex002_contract_history.py`; HT
`src/harmonic_trader/data/cex002_history.py` and `tests/test_cex002_history.py`.
The senior authors these four paths only, with no tests, Git or data execution.

Reviewer publication paths: this report, ADR0042, CMB `docs/handoff/CURRENT_TASK.md`,
`tickets/CEX-002.md`, `research/sprint_004/cex002_contract_notice_facts.json`,
`research/sprint_004/cex002_confirmed_history_529.json`; HT `README.md`,
`docs/handoff/CURRENT_TASK.md`, `tickets/HT-005.md`. Generate one new immutable companion
under `data/.cex002_contract_history/`; preserve all earlier companions and market files.

Acceptance: preserve all 777 prior episode records and identities; check compiler and
reader schema compatibility, confirmed boundaries, knowledge-time rejection, whole-bar
boundary crossing, restrictions/closures and postponed GAIB. Run only CMB
`PYTHONPATH=src .venv/bin/python -m pytest tests/reference/test_cex002_contract_history.py -q --tb=short`
and HT `PYTHONPATH=src .venv/bin/python -m pytest tests/test_cex002_history.py -q --tb=short`,
plus Ruff on the four changed paths. Verify five selected symbol/month bar files and
at most 1 MiB total market data, delivering a later BTC/ETH/BCH/XRP/ARB bar to actual
Nautilus callbacks. Inspect GAIB membership/manifest declarations without a full scan.
Run repository-control and scoped whitespace checks before publication. No broad suite.

Research work: reuse cached notices; examine the five missing active names and record
GAIB's indefinitely postponed launch separately. Identify the concrete limitation of
public historical trading-rule recovery, including source statements about unannounced
changes; do not turn that limitation into an endless completion requirement.

## Accepted result

The reviewer accepts the independently authored four-file source/test change and the
compiled companion. 770 of 771 names now have usable dated coverage. The remaining name,
GAIBUSDT, is explicitly postponed, marked PENDING_TRADING in the retained snapshot, and
has no declared bar partition. No active contract remains wholly excluded solely because
its exact first-ever opening time is missing. The five confirmation boundaries are:

| Contract | Conservative coverage begins (UTC) | Evidence |
|---|---|---|
| BTCUSDT | 2019-09-13 04:00:00 | Official public-access schedule after earlier beta |
| ETHUSDT | 2019-11-29 00:29:52 | Publisher timestamp of notice confirming it had launched |
| BCHUSDT | 2019-12-19 13:09:03 | Publisher timestamp of notice confirming it had launched |
| XRPUSDT | 2020-01-06 11:42:09 | Publisher timestamp of notice confirming it had launched |
| ARBUSDT | 2023-03-23 16:00:00 | End of a pinned hourly bar containing actual trades |

These timestamps are not fabricated first-trade times. ARB's approximate announcement
identifies the contract; the stored exchange bar supplies evidence that trading occurred
before its end. Earlier raw bars remain available and labelled unknown or crossing the
confirmation boundary. Confirmation notices do not supply launch-only terms.

All 777 prior episode records, including identities, are exactly unchanged. Schema 2
adds five confirmation episodes for 782 total; schema 1 remains readable. A confirmed
record emits no false LIST event. Typed validity starts at confirmation, while knowledge
starts at the explicit present research date. Continuity remains an explicit assumption.

Companion: `data/.cex002_contract_history/review529-20261027.json`
SHA256: `6ef47558eff2b3d3b30fbd8569dd96e0f7b7863bd8b310025cf641f7e72034a9`
Size: 1,290,098 bytes. Retrospective known_from: `2026-10-27T18:20:52Z`.
Facts SHA256: `bfcd796895520c15260c26190aec0b504645608e710b61ae903be26a3f269f88`.

The compiler's 22 cases and reader's 32 cases passed (54 total), including actual synthetic
Nautilus callbacks, earlier/crossing refusal, closures/restrictions, knowledge-time gates,
pending contracts, schema compatibility and preservation of funding fields. Scoped Ruff
passed in both repositories. HT pytest could not write its optional cache but exited 0;
the first HT Ruff invocation exited 2 because its cache was read-only, then the same
command passed with normal filesystem access. No source repair or test rerun was needed.

Five real files / 75,640 bytes were checked. One bar each from BTC, ETH, BCH, XRP and ARB
reached native and original-field Nautilus callbacks with unchanged values. The remaining
unknown/boundary bars in those selections were refused: three before-confirmation XRP
bars, one crossing XRP bar, and one before-confirmation ARB bar. Their original rows are
preserved. GAIB remains unknown for native projection with its postponement retained.
The metadata probes initially requested BTC/ETH months outside the release and then used
an incorrect reader attribute; both failures occurred before market-file reads and are
recorded in the JSON evidence. Corrected public-API selection succeeded.

Exact commands, exit codes, source hashes, notice URLs/hashes, five partition pins and
classification/callback results are in `cex002_confirmed_history_529.json`. Existing full
storage, eleven-product consumer and replay proofs remain accepted. No market download,
full scan, broad test suite, strategy or order execution ran. All jobs are terminal.

## Historical trading-rule limitation and finite remaining work

The [2021 minimum-notional announcement](https://www.binance.com/en/support/announcement/detail/76719bbaeeb847bbac4daa2906fcdcc0)
sets a $1 threshold from 2021-01-25 07:00 UTC, exempts reduce-only orders, and permits
later changes without announcements. The [current contract FAQ](https://www.binance.com/en/support/faq/detail/360033161972)
also directs users to the current API for thresholds that may change without notice.
A current value cannot establish its past effective date. Therefore public-notice recovery
alone cannot certify every historical tick/quantity/notional/margin constraint. This is
a source limitation, not an instruction to keep downloading announcements indefinitely.

Retain missing specifications as explicit gaps. These callbacks establish data delivery
and dated contract selection, not realistic order acceptance, fills or funding entitlement.
Historical order simulation requires sourced snapshots or an explicit documented assumption
for each missing constraint; no such simulation is performed here.

The next same-ticket action is the outstanding bounded OI source/notional and funding-sign
examples described in Review525, then a consolidated acceptance-item evidence map using
accepted records. Reviewer may execute those small evidence queries under the owner
repair override, without the withdrawn broad-suite prerequisite. Authorize at most three
existing nonempty partitions per product, their recorded lineage/raw sources and 12 displayed
examples total; inspect schemas and preserve exact source decimals. Do not rerun normalization,
full storage/readback/replay proofs, or resume the stopped broad suite. Any remaining gate
must be named with its missing evidence; no blanket full-ticket acceptance is claimed.

Final publication checks passed: repository-control and scoped whitespace checks in both
repositories exited 0; all four frozen source hashes, the facts hash, the new companion
hash and the previous companion hash matched. Only enumerated CEX/HT paths are integrated.
