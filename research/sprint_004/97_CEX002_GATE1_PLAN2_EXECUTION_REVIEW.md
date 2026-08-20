# CEX-002 Gate 1 Plan-2 Execution Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed commit: `e35d7c458f509b886698325fdb5f630c6e6fe08a`

Reviewed execution record:
`research/sprint_004/96_CEX002_GATE1_PLAN2_EXECUTION.md`

Reviewed report:
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

## Decision

**ACCEPT THE EXECUTION EVIDENCE. GATE 1 DOES NOT PASS. SET CEX-002 TO `BLOCKED`.**

The qualification implementation is now reproducible under the accepted focused
contract: 149 focused CEX-002 tests and 11 atomic-download tests passed; Ruff, repository
control, and the committed whitespace check passed; the assertion-bound migration
preserved the exact plan digest and version-1 history; both real runs captured exit 2;
Coinalyze qualified; no new sample transfer occurred; and semantic resume identity
passed.

No further developer correction is authorized. The remaining blockers are source
authority and physical resources, not another retry or implementation defect.

## Accepted Gate 1 Evidence

- plan version 2, with versions 0 and 1 preserved in history;
- unchanged plan digest
  `d6eb52ff73711df669e9388d06a6abca92cb61cc86a17169b7ed62f369f132c1`;
- 20 physical archive families and 5,123,061 deduplicated accepted-universe objects;
- 100 checksum-proved retained samples reused with zero new transfer;
- 771 affirmatively confirmed crypto perpetuals;
- complete reporting of 46 dated-delivery candidates, 17 settlement-artifact candidates,
  four affirmatively excluded delivery contracts, and 170 affirmatively excluded TradFi
  perpetuals;
- official qualification for trades, one-minute bars, OI, realized and indicative
  funding, mark/index/basis, and cost-calibration families;
- real Coinalyze BTCUSDT/ETHUSDT daily-history qualification, 759 validated Binance
  perpetual market identities, and explicit support for 569 of the 771 confirmed
  universe members;
- 202 explicit `coinalyze_symbol_unmapped` coverage gaps rather than zeros or silent
  exclusions; and
- stable two-run semantic identity with actual exit statuses 2 and 2.

The Coinalyze source itself is accepted as `secondary_qualified`. Its 202 unmapped symbols
remain typed coverage limitations for the later daily intersection and coverage product;
they do not turn missing liquidation observations into zero and do not reduce the
acquisition universe.

## Blocking Finding 1: Historical Membership Authority

Sixty-three archive-only names still have no affirmative official contract-type or
realized-funding evidence: 46 have dated-delivery-shaped names and 17 contain settlement
suffixes. Review 75 correctly prohibited promotion or exclusion from spelling. That rule
remains binding.

The official USD-M `exchangeInfo` interface is documented as current exchange trading
rules and symbol information, not a historical contract master:

`https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information`

Binance's official public-data repository documents historical trades, klines,
aggregate trades, derivatives families, and current-symbol helper scripts, but identifies
no historical contract-metadata dataset:

`https://github.com/binance/binance-public-data/blob/master/README.md`

These sources do not prove that no exact official announcement or retained historical
snapshot exists elsewhere. They do prove that the two qualified source interfaces cannot
resolve the 63 names. Gate 1 cannot pass until exact official evidence is supplied,
retained, and validated for every candidate, or a future ADR changes the authority
contract. No ADR change is authorized here.

## Blocking Finding 2: Physical Storage

The accepted-universe inventory requires exactly 8,662,211,210,669 compressed raw bytes.
After verified retained credit, projected new raw bytes are 8,661,196,012,122. The second
run measured only 185,976,057,856 local bytes available, leaving an
8,475,219,954,266-byte shortfall. Normalized/catalog storage is separately unknown and
must not be treated as zero.

Gate 2 cannot begin on the current destination. Proceeding requires a writable
destination that can hold at least the projected new raw requirement plus a separately
measured normalized/catalog allowance. This is not permission to reduce the universe,
drop derivatives products, stream-and-discard required raw provenance, or substitute a
price-only study.

## Other Retained Constraints

The legacy sample budget remains honestly unresolved/exhausted. The accepted Gate 1
evidence reuses the retained checksum-proved sample set, and no further sample download is
authorized. This record does not erase or relabel the historical budget condition.

The inventory contains numerous typed head, tail, interior, family-launch, pre-listing,
post-close, current-unarchived, and absent-family gaps. They remain required inputs to the
future coverage product and usable daily intersection. Nothing in this review promotes
those gaps to complete coverage.

## Required External Input

The next required actor is the Owner only as supplier of external resources and source
artifacts, not as acceptance authority. To resume CEX-002, the Owner must provide both:

1. an identified writable destination satisfying the raw-byte requirement and allowing a
   separate normalized/catalog capacity measurement; and
2. exact official historical contract metadata, retained official snapshots, or exact
   official announcement authority capable of resolving all 63 candidates.

The reviewer will inspect any supplied authority and remains the only actor who may accept
it or authorize a source/ADR correction. Providing hardware, a mount path, URLs, hashes,
or source artifacts does not itself accept Gate 1.

## Publication Set

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/97_CEX002_GATE1_PLAN2_EXECUTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 is `BLOCKED`. Gate 2, bulk acquisition, normalization, publication, Nautilus,
every other ticket, and Harmonic Trader work remain unauthorized. Next ticket remains
`NONE`.
