# CEX-002 Membership and Qualification-Budget Architecture

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `295eefe163fe94b82e349a039f863a9ab7fe864e`

Subject record: `research/sprint_004/136_CEX002_RECORD_134_CORRECTION.md`

Architecture decision: `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`

## Record-136 decision

**ACCEPT RECORD 136 AS THE AUTHORITATIVE FORWARD CORRECTION TO RECORD 134.**

Commit `295eefe163fe94b82e349a039f863a9ab7fe864e` changed exactly the two controls and
record 136. It preserves record 134, corrects the review-133 integration to `dba025c`,
states that the original C5 transcript is unavailable rather than inventing it, corrects
the FAPI cache to 9 files / 9,697,128 bytes before and 10 files / 10,774,707 bytes after,
and corrects the manifest phase and iterator arithmetic. No source, test, report, data,
cache, checkpoint, journal, database sidecar, or unrelated path entered the commit.

## Official-source investigation

The terminal report's 63 blockers split exactly into 46 dated delivery names and 17
settlement-suffixed names. The 46 delivery names comprise two BTCBUSD, twenty-two BTCUSDT,
and twenty-two ETHUSDT identities. The settlement aliases reduce to 16 base names because
both `AERGOUSDTSETTLED` and `AERGOUSDTSETTLEDSETTLED` map to `AERGOUSDT`.

The retained official listing checkpoint proves every candidate is a real archive name,
not a parser invention. The 17 aliases own 1,328 listed non-checksum objects. Each mapped
base already has affirmative perpetual evidence: twelve from authenticated current
`exchangeInfo`, four from official realized-funding archives.

The official Binance USD-M market-data reference defines continuous `PERPETUAL`,
`CURRENT_QUARTER`, and `NEXT_QUARTER` contract types and documents `GET
/futures/data/delivery-price` as the quarterly-contract settlement-price endpoint:

- `https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data`

Read-only 2026-08-21 probes of that endpoint returned 18 BTCUSDT and 18 ETHUSDT settlement
records whose UTC dates exactly match the reviewed suffixes from 2022-03-25 through
2026-06-26. BTCBUSD returned an empty array. The endpoint omits the four 2021 dates for each
USDT pair and both BTCBUSD dates, so it is direct authority for 36 identities but cannot
serve as a closed historical registry.

The official public-data repository states that the archive contains Binance public market
data, supports USD-M futures symbols, publishes provider checksums, and may revise archive
objects with recorded updates:

- `https://github.com/binance/binance-public-data`

The safe decision is therefore an exact reviewed authority table, not a new spelling rule.
ADR-0020 freezes all 46 exact delivery identities and all 17 exact alias mappings. Any new
date- or settlement-shaped name remains blocking until reviewed.

### Frozen delivery table version `review137-v1`

The literal `reviewed_archive_delivery_inference` members are:

- BTCBUSD: `BTCBUSD_210129`, `BTCBUSD_210226`;
- BTCUSDT: `BTCUSDT_210326`, `BTCUSDT_210625`, `BTCUSDT_210924`,
  `BTCUSDT_211231`; and
- ETHUSDT: `ETHUSDT_210326`, `ETHUSDT_210625`, `ETHUSDT_210924`,
  `ETHUSDT_211231`.

The literal `official_delivery_direct` members are:

- BTCUSDT: `BTCUSDT_220325`, `BTCUSDT_220624`, `BTCUSDT_220930`,
  `BTCUSDT_221230`, `BTCUSDT_230331`, `BTCUSDT_230630`, `BTCUSDT_230929`,
  `BTCUSDT_231229`, `BTCUSDT_240329`, `BTCUSDT_240628`, `BTCUSDT_240927`,
  `BTCUSDT_241227`, `BTCUSDT_250328`, `BTCUSDT_250627`, `BTCUSDT_250926`,
  `BTCUSDT_251226`, `BTCUSDT_260327`, `BTCUSDT_260626`; and
- ETHUSDT: `ETHUSDT_220325`, `ETHUSDT_220624`, `ETHUSDT_220930`,
  `ETHUSDT_221230`, `ETHUSDT_230331`, `ETHUSDT_230630`, `ETHUSDT_230929`,
  `ETHUSDT_231229`, `ETHUSDT_240329`, `ETHUSDT_240628`, `ETHUSDT_240927`,
  `ETHUSDT_241227`, `ETHUSDT_250328`, `ETHUSDT_250627`, `ETHUSDT_250926`,
  `ETHUSDT_251226`, `ETHUSDT_260327`, `ETHUSDT_260626`.

Each literal tuple binds the symbol, pair before the underscore, UTC delivery date encoded
by `YYMMDD`, and authority class. The code must publish a canonical serialization version
and SHA-256 for this exact 46-tuple set. The ten reviewed-archive members do not become
direct members merely because their spelling matches. Their classification is the
reviewer's explicit inference from the retained official multi-family archive lifecycle
and zero realized-funding observations, not a claim that a retained type row covers them.
The implementation must re-prove that evidence from the frozen checkpoint. The 36 direct
members must match a retained official delivery-price response. Either mismatch fails
closed.

### Frozen settlement-alias table version `review137-v1`

The literal alias-to-base mappings and independent base authority are:

| Alias | Base | Base authority |
|---|---|---|
| `AERGOUSDTSETTLED` | `AERGOUSDT` | official realized funding |
| `AERGOUSDTSETTLEDSETTLED` | `AERGOUSDT` | official realized funding |
| `AIAUSDTSETTLED` | `AIAUSDT` | authenticated current `PERPETUAL` |
| `BDXNUSDTSETTLED` | `BDXNUSDT` | official realized funding |
| `BNXUSDTSETTLED` | `BNXUSDT` | authenticated current `PERPETUAL` |
| `BTCSTUSDTSETTLED` | `BTCSTUSDT` | official realized funding |
| `CTKUSDTSETTLED` | `CTKUSDT` | authenticated current `PERPETUAL` |
| `CVCUSDTSETTLED` | `CVCUSDT` | authenticated current `PERPETUAL` |
| `CVXUSDTSETTLED` | `CVXUSDT` | authenticated current `PERPETUAL` |
| `ICPUSDT_SETTLED` | `ICPUSDT` | authenticated current `PERPETUAL` |
| `LITUSDTSETTLED` | `LITUSDT` | authenticated current `PERPETUAL` |
| `MAVIAUSDTSETTLED` | `MAVIAUSDT` | authenticated current `PERPETUAL` |
| `MINAUSDTSETTLED` | `MINAUSDT` | authenticated current `PERPETUAL` |
| `PUMPUSDTSETTLED` | `PUMPUSDT` | authenticated current `PERPETUAL` |
| `SLPUSDTSETTLED` | `SLPUSDT` | authenticated current `PERPETUAL` |
| `SXPUSDTSETTLED` | `SXPUSDT` | official realized funding |
| `TLMUSDTSETTLED` | `TLMUSDT` | authenticated current `PERPETUAL` |

The code must publish a canonical serialization version and SHA-256 for this exact
17-tuple set. Authority is re-proved from the normal retained membership evidence; the
table is not itself permission to accept a base. Any missing base, changed authority, or
unlisted alias fails closed.

## Qualification-budget investigation

The candidate plan contains 3,244 qualification-plan entries: 3 aliases, 31 downloads totaling
268,435,410 bytes, 15 retained objects totaling 4,465,586 bytes, and 3,195 blocked objects
totaling 12,250,672,167 bytes. The first 20 downloads alone are `bookTicker` objects totaling
268,277,054 bytes. That ordering blocks 78 small non-cost samples totaling less than one
megabyte across bars, metrics, funding, mark/index/premium inputs.

The complete cost manifest itself is 12,522,974,218 compressed bytes. It is required and is
not reduced. The defect is placing that final Gate-2 product inside the 268,435,456-byte
Gate-1 qualification allowance. ADR-0020 separates a deterministic six-object, three-era
cost-source sample from the complete per-contract cost manifest while preserving every final
cost object and byte.

## Decision

**AMEND THE ARCHITECTURE UNDER ADR-0020 AND ASSIGN THE SOURCE-AUTHORITY AND PLAN CORRECTION
TO SR DEV - CLAUDE BUILD.**

This is source-authority, historical-identity, financial-semantic, and plan-lineage work.
It is not suitable for Spark. Claude Opus 5 is selected because the work extends the
historical authority state machine and must preserve the complete cost product while
changing only qualification planning.

## Claude source authorization

Sr Dev - Claude Build using Claude Opus 5 may edit only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- the existing `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/` directory
  only if a bounded redacted delivery-response fixture is necessary.

Claude must implement ADR-0020 literally:

1. add versioned, digest-bound exact tables for the 46 reviewed delivery symbols and 17
   reviewed settlement aliases; no regex alone may accept or exclude a future name;
2. query each distinct frozen delivery pair through the official settlement-price endpoint,
   retain raw response bytes content-addressably with redacted request/provenance, validate
   schema/types/positive prices/unique dates, and report direct matches plus missing history;
3. classify 36 exact matches as direct delivery authority and the ten exact older identities
   as reviewed archive delivery inferences only after re-proving their retained official
   multi-family lifecycle and funding absence; all 46 are non-perpetual and nonblocking
   only while that exact evidence matches, otherwise they block;
4. resolve an exact alias only when its mapped base independently has affirmative perpetual
   evidence; report alias objects/families/bytes/provenance and keep them nonconsumable until
   later economic validation rather than silently dropping or merging them;
5. leave every unknown future archive name blocking;
6. preserve the complete first/midpoint/last per-contract cost manifest, exact bytes, gaps,
   digest, and Gate-2 storage charge outside the Gate-1 qualification allowance;
7. build the Gate-1 plan in ADR-0020 priority order, including the deterministic three-era
   smallest-positive-object sample for each cost family after all non-cost samples; for
   zero-based canonical item `i` of `n`, use stratum `min(2, floor(3 * i / n))`;
8. require every selected qualification object to fit the unchanged cumulative 256 MiB
   allowance and preserve checksum, non-empty, schema, time, and economic validation;
9. emit read-only candidate version 4 with frozen v3 plan/envelope digests recorded as
   superseded candidate lineage and locked versions 0-2 unchanged; and
10. keep `migration_authorized=false`, `download_authorized=false`, samples empty, the
    amendment ledger absent, and the legacy lock/ledger/raw tree immutable.

Focused test source must cover all 63 exact identities, table-digest drift, a future
date-shaped name, a future settlement-shaped name, missing/unconfirmed alias bases,
delivery-response empty/truncated/malformed/duplicate/nonpositive cases, secret-free
provenance, qualification priority, six cost-source strata, full-cost preservation, exact
byte accounting, v3-to-v4 candidate lineage, and no-mutation candidate preflight.

Claude performs no test, Ruff, repository-control, network/data run, candidate execution,
integration, repository-record edit, ADR edit, Git operation, commit, push, plan migration,
sample acquisition, Gate 2, normalization, catalog, Nautilus, Harmonic Trader, payoff,
PAPER, LIVE, paid-source, or other-ticket work. It stops for reviewer source inspection
with exact SHA-256 values for every edited path and the unique CEX test-function count.
Hermes remains unauthorized.

## Reviewer publication

The reviewer publishes exactly:

- `docs/adr/0020-historical-contract-authority-and-qualification-budget.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/137_CEX002_MEMBERSHIP_AND_BUDGET_ARCHITECTURE.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, report, data, checkpoint, cache, journal, database sidecar, or
unrelated dirty path belongs to this publication. The reviewer executes no pytest, Ruff,
repository-control, candidate, migration, sample, or data-mutating command.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Candidate execution, plan migration,
sample acquisition, Gate 2 and every later gate, Nautilus work, Harmonic Trader work,
payoff analysis, PAPER, LIVE, and every next ticket remain unauthorized. Next ticket
remains `NONE`.
