# ADR 0026 - Non-Backdated Fee Scenarios

- **Status:** Accepted
- **Date:** 2026-08-23
- **Amends:** ADR-0017 and ADR-0025
- **Evidence:** `research/sprint_004/234_CEX002_FEE_AUTHORITY_AND_FINAL_SIZING_CORRECTION.md`

## Context

CEX-002 needs honest transaction-cost inputs before any Harmonic Trader experiment. The
accepted qualification report retained five real book-ticker/depth samples but no fee
schedule, and the FEE-001 control table contains zero rows.

The official Binance USD-M `GET /fapi/v1/commissionRate` interface is signed USER_DATA.
It requires a symbol and a current request timestamp and returns the requesting account's
current maker, taker, and RPI rates. It has no effective-time or history parameter. The
current public fee page is likewise not a retained historical series. Listing that endpoint
in qualification metadata did not capture its response or establish past effectivity.

The local FEE-001 model distinguishes `OFFICIAL_SCHEDULE` from
`ASSUMED_CONSERVATIVE`, but its bitemporal access contract also requires `known_from`,
used as availability time, to precede the simulated decision. A policy first fixed in 2026
therefore cannot be made available to a 2020 decision without falsely backdating knowledge.
An experiment assumption is configuration known at preregistration; it is not a historical
exchange observation.

## Decision

### 1. Close the source question as unavailable history

No free reproducible historical Binance USD-M fee-schedule source is qualified for the
CEX-002 interval. The official current endpoint and current public page may support
prospective observations from their actual retrieval times, but neither may be projected
backward. The Gate-1 fee boundary is closed by publishing typed unavailability, not by
inventing a source. The accepted Binance archive, membership, Coinalyze, raw-byte,
checksum, and sample evidence remains unchanged.

### 2. Amend the cost product

ADR-0017's required `binance_usdm_cost_calibration` product consists of five explicit
components:

1. every retained field and row from the frozen book-ticker samples;
2. every retained field and row from the frozen book-depth samples;
3. effective fee-schedule observations only where retained authority proves their valid
   and availability intervals;
4. an instrument/version-scoped typed gap wherever historical fee authority is absent;
5. immutable fee-scenario policy rows used as experiment configuration.

For the accepted CEX-002 authority, component 3 has zero historical rows, component 4 has
exactly one `historical_fee_schedule_unavailable` row for each of the 771 accepted
membership identities, and component 5 has the two rows below. A missing official
schedule never becomes zero cost and never blocks publication of the honest cost product.

### 3. Pin outcome-blind fee scenarios

The release carries these venue/product-scoped policy rows, not FEE-001 historical facts:

| scenario id | maker rate | taker rate | role |
|---|---:|---:|---|
| `assumed_conservative_5bps_per_side_v1` | `0.0005` | `0.0005` | primary assumption |
| `assumed_severe_10bps_per_side_v1` | `0.0010` | `0.0010` | required sensitivity |

Both apply to Binance USD-M perpetual executions, disable maker credit, rebates, VIP
discounts, referrals, and BNB discounts, and charge each executed side. The five-basis-
point policy is an upward-rounded stress relative to the official current endpoint's
four-basis-point taker example and matches the repository's already preregistered fixed-fee
convention. The ten-basis-point row is a fixed 2x fee stress. Neither row claims a past
Binance rate or a proved historical upper bound.

Both rows use authority class `ASSUMED_CONSERVATIVE` and the fixed policy knowledge time
`2026-08-23T03:00:00Z`. That time is after every historical decision in the release and
therefore cannot be mistaken for historical availability.

A later experiment must preregister its primary cost rule before inspecting outcomes. It
must label results as net of assumed fees, apply the frozen spread/depth calibration under
the already required 0.5x/1x/2x cost sensitivities, and report the ten-basis-point fee
sensitivity. A favorable sensitivity cannot replace a failed primary rule.

### 4. Keep assumptions out of historical reference truth

The two policy rows are content-addressed release configuration with a real
`policy_known_at`, source-basis references, exact decimal rates, scope, and discount/rebate
flags. They are pinned by the final bundle descriptor. They are not inserted into
`ref_fee_schedule` with backdated `known_from` values. A future official observation may
enter FEE-001 only from a proved valid/effective time and its real availability time.

### 5. Extend the sizing lower bound

The coverage/gap sizing lower bound is now 9,088 rows: the accepted report's 8,317
product-scoped source gaps plus 771 fee-authority gaps. The accepted 3,742 typed-gap
product/symbol memberships remain a separate proved count, not a replacement for either
set. The cost product also allocates both scenario-policy rows and every field in all five
components. These additions participate in catalog pages, manifests, the final bundle,
temporary high water, and total future storage.

## Authority references

- Binance USD-M User Commission Rate documentation:
  `https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#user-commission-rate`.
  It identifies a signed USER_DATA request with required `symbol` and current signing
  `timestamp`; the response example is maker `0.0002` and taker `0.0004`.
- Binance current USD-M fee page: `https://www.binance.com/en/fee/futureFee`.
- Repository source policy:
  `research/sprint_001/docs/architecture/02_DATA_SOURCE_PLAN.md`, section 6, which requires
  `ASSUMED_CONSERVATIVE` when historical fees cannot be reconstructed.
- FEE-001 model and access semantics:
  `src/cryptofactors/reference/models.py`, `src/cryptofactors/reference/store.py`, and
  `src/cryptofactors/catalog/as_of.py`.
- Existing outcome-blind five-basis-point convention:
  `tickets/EXP-009_PRE_REGISTRATION.md`.

## Consequences

- ADR-0025's fee-authority prerequisite is resolved without credentials, paid data, or
  false history.
- Gate 1 is no longer reopened. Gate 2 remains blocked pending a correct storage receipt.
- The fee absence is explicit and does not turn CEX-002 into a price-only release.
- This ADR authorizes no acquisition, normalization, catalog publication, experiment,
  NautilusTrader integration, Harmonic Trader work, PAPER, or LIVE work.
