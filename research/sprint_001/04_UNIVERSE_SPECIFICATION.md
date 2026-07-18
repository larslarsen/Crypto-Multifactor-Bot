# Point-in-Time Universe Specification

## 1. Primary universe: U50

At each decision time, rank all historically listed candidate assets by lagged 30-calendar-day median consolidated daily quote volume.

An asset is eligible when all conditions are met using only information available at the decision time:

- at least 180 calendar days since first reliable listing;
- at least 27 valid daily observations in the trailing 30 days;
- trailing median consolidated daily quote volume of at least USD 1 million;
- rank within the top 50 among otherwise eligible assets;
- executable on at least one approved venue;
- unambiguous canonical asset mapping;
- no stablecoin, fiat token, wrapped duplicate, leveraged token, or synthetic inverse token;
- no active data-quality quarantine.

The USD floor prevents the top-N rule from admitting an economically unusable tail when the market contracts.

## 2. Robustness universes

- **U25:** top 25, same rules.
- **U100:** top 100, same rules, with a stricter position-capacity haircut.
- **Single-venue universe:** historically executable on the selected venue.
- **Multi-venue universe:** executable on any approved venue.
- **Survivor-biased diagnostic:** current survivors only, reported solely to quantify bias and never as a primary result.

Primary conclusions must not depend on one universe width.

## 3. Decision schedule

Primary weekly decision: fixed UTC timestamp, selected before results.  
Secondary daily decision: fixed UTC timestamp.

The same schedule is used for all factor comparisons.

## 4. Membership snapshots

Store a row per `(decision_time, asset_id)` with:

- eligibility;
- each gate value;
- rejection reason;
- volume rank;
- listing age;
- valid-observation count;
- approved execution venues;
- shortability;
- spot and perpetual flags.

Membership is never regenerated from a current file list without a version bump.

## 5. Delistings and migrations

- Retain delisted assets in historical samples.
- Use the last executable price under a conservative liquidation rule.
- Record migrations and redenominations as corporate actions.
- Do not splice MATIC/POL-style migrations without an explicit conversion record.
- Assets with an announced delisting may be excluded only after the announcement's availability time and according to a preregistered liquidation policy.

## 6. Short universe

The market-neutral short side is a strict subset of U50.

At each date, an asset additionally requires:

- active perpetual or borrow facility;
- known contract terms;
- known funding/borrow observations;
- adequate open interest or depth;
- no imminent contract termination;
- venue and jurisdiction approval for the simulated strategy.

A short signal on an ineligible asset is not redistributed after seeing returns; weights are recomputed from the eligible short set.

## 7. Liquidity is both gate and risk limit

Eligibility does not imply unlimited capacity.

Position caps use:

- trailing median daily quote volume;
- observed spread;
- depth or impact model;
- intended participation rate;
- venue concentration;
- liquidation horizon.

## 8. Venue approval

Venue approval is dated and based on:

- data reliability;
- fee transparency;
- operational history;
- wash-trading/volume reliability assessment;
- custody/default assumptions;
- settlement and funding integrity.

A venue's reported volume may be excluded from ranking while its prices remain useful for diagnostics.

## 9. Market-cap data

Size is not used to define U50 unless point-in-time circulating supply passes audit. Volume-based eligibility remains the baseline because it is closer to implementation capacity.

## 10. No fallback that changes the scientific question

If fewer than the required number of assets qualify, the portfolio uses the smaller universe. It does not silently relax thresholds or backfill current high-liquidity assets.
