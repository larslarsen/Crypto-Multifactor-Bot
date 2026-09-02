# CEX-002 Review 466 - Realized Funding Architecture and Grok Source Authorization

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer, xhigh
- **Ticket:** CEX-002
- **Decision:** accept ADR-0036 and authorize one bounded Grok 4.6 High source/test drop
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - four of eleven required products accepted
- **Next required actor:** Sr Dev - Grok Build on Grok 4.6 High
- **Next ticket:** `NONE`

## Plain-language decision

The realized-funding data is already downloaded. This boundary performs no network acquisition.
It converts the 21,035 authenticated monthly funding ZIPs into one exact event table. Each Binance
row is an actual funding settlement; the converter preserves its timestamp, exact rate, and
declared interval. It does not create hourly rows, fill gaps, or alter rates.

ADR-0036 records those semantics durably. Sr Dev - Grok Build on Grok 4.6 High is selected because
the source drop combines financial sign semantics, authenticated-source authority, and immutable
publication. Hermes remains the only integration, full-test, acceptance-command, evidence, Git,
and real-data execution actor after reviewer source acceptance.

## Accepted authority boundary

The reviewer proved `HEAD == origin/main == ca1b0525d344928fb59a5e5ea6d2d97566e77019` before this
publication and inspected the accepted generation-0 SQLite authority read-only. The required source
set is exactly:

- 21,035 `monthly/fundingRate` completion rows totaling 21,351,804 compressed bytes;
- 21,020 completions in `checksum_verified` state and 15 in accepted `retained_credit` state;
- one authenticated source object per native-symbol/month partition, hence 21,035 projected
  partitions and lineage documents;
- generation-0 Binance completion count 685,072 and accepted seal head
  `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`.

Every selected completion must independently reprove its plan identity and payload, content path,
listed byte size, content SHA-256, sidecar identity, provider checksum, retrieval time, family,
symbol, and monthly period before its ZIP is parsed. State and content inputs are read-only, opened
without symlink following, and cannot be replaced by the V3 direct-recovery manifest or an
unauthenticated filesystem scan.

Pinned repository authorities are:

- qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`, SHA-256
  `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`;
- sizing receipt `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`, SHA-256
  `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`;
- accepted 14-column `binance_usdm_funding_realized` schema and accepted writer/policy identities;
  and
- the report's 959 realized-funding source-coverage rows, 675 typed-gap symbols, and nine declared
  source-gap kinds. These are bound as authority, not expanded into missing settlement events.

The accepted sizing ceiling is 15,660,013 rows, 941,985,964 product bytes, and a 72,726-byte
largest projected partition. These are capacity ceilings, not instructions to synthesize rows.

## Frozen source and economic contract

Each ZIP must be an unencrypted, safe, single root CSV with a member name matching the
authenticated key. Both forms accepted by the source are supported: the exact three-column header
or headerless rows with exactly:

```text
calc_time,funding_interval_hours,last_funding_rate
```

Arbitrary text in the first row, extra/missing columns, unsafe paths, encryption, CRC failure,
trailing archive members, unbounded decompression, or a key/member/symbol/month mismatch fails.
Parser limits are finite and exceed every accepted funding object; the abandoned raw-acquisition
ZIP expansion-ratio ceiling is not reused to reject authentic source data.

`calc_time` is an integer Unix-millisecond settlement timestamp and must belong to the UTC month in
the source key. `funding_interval_hours` is a positive source integer and is preserved exactly;
the implementation must not whitelist remembered interval values. `last_funding_rate` must be a
finite, exactly representable `decimal128(38,18)` lexeme parsed without floats, rounding, or ambient
decimal-context dependence.

ADR-0036 is normative. The output contains observed settlement events only. An 8 -> 4 -> 1 -> 8
schedule transition remains four source-declared event regimes; the implementation never expands,
resamples, annualizes, divides, forward-fills, interpolates, or emits a zero for absence. For every
row, `long_cashflow_rate == -last_funding_rate`, `short_cashflow_rate == last_funding_rate`, and the
two sum to exact zero with convention `long_pays_short_when_rate_positive`.

Native identity is `BINANCE_USDM` plus the authenticated symbol. Both canonical identity fields
remain null with `reference_identity_not_yet_created`. Rows are deterministically sorted. An exact
duplicate `(symbol, calc_time, interval, rate)` may collapse only with every contributing ordinal
retained in lineage; a repeated `(symbol, calc_time)` with a different interval or rate fails.

## Frozen publication and completion contract

The normalizer reads its explicit generation-0 state/content roots, report, and sizing paths and
writes one caller-selected hidden output root. It publishes one content-addressed Parquet and one
content-addressed lineage document per native-symbol/UTC-month partition using the exact target
schema. Lineage maps every partition-local `raw_object_ref` exactly once to full authenticated
source facts and preserves all collapsed source ordinals.

Same-filesystem staging is bounded, flushed, verified, and atomically renamed without clobbering.
A matching winner is rehashed and reused; a differing winner fails. The completion descriptor is
written last, is the sole complete-product marker, and binds all ordered artifacts and authority
identities. Interruption leaves no visible complete product. Deterministic replay must reprove and
reuse byte-identical artifacts.

Full-corpus completion requires exactly 21,035 sources, 21,351,804 source bytes, 21,035 partitions
and lineages, the accepted source-state split, zero conflicting/excluded/inferred/rounded events,
and exact reconciliation of physical rows, collapsed identical rows, and product rows. The row,
interval, event-time, and symbol ranges and interval histogram are reported from authenticated data,
not hard-coded. A product completion is not the later coverage product, bundle, or catalog commit.

## Grok 4.6 High authorization

Sr Dev - Grok Build on Grok 4.6 High may author exactly these new paths:

- `src/cryptofactors/ingest/binance_usdm_funding_realized.py`;
- `scripts/research/normalize_binance_usdm_funding_realized.py`; and
- `tests/ingest/test_binance_usdm_funding_realized.py`.

The CLI accepts explicit `--generation0-state`, `--generation0-content-root`, `--report`,
`--sizing`, and `--output-root` arguments and prints one concise deterministic JSON result. The
drop may import accepted authorities but may not modify package exports, existing source/tests,
data, records, control files, or unrelated paths.

The new test source covers pinned-authority refusal, exact source/state/count/byte checks,
headed/headerless parsing, key/member/month identity, strict integers and decimals, positive/
negative/zero signs and exact conservation, interval transitions without invented rows or rate
scaling, identical collapse and conflict refusal, native-only identity, complete lineage, exact
schema, ZIP/path/CRC/decompression safety, no-clobber publication, interruption invisibility,
completion reconciliation, and byte-identical replay.

Under the targeted senior test exception, Grok may run exactly once:

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/ingest/test_binance_usdm_funding_realized.py -q --tb=short
```

Grok stops on the first nonzero result and reports the exact command and output without patching or
rerunning. Grok performs no real-data run, integration, repository-record edit, Git operation,
commit, push, data mutation, acquisition, network access, cleanup, catalog transaction,
NautilusTrader work, experiment, model, Harmonic Trader work, PAPER, LIVE, or next-ticket work.
Hermes remains unauthorized until reviewer static acceptance of the exact drop.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review publishes exactly:

- `docs/adr/0036-realized-funding-event-semantics.md`;
- `research/sprint_004/466_CEX002_REALIZED_FUNDING_ARCHITECTURE_AND_GROK_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All implementation, test, data, runner, acceptance-command, and unrelated dirty paths remain
unstaged and untouched.
