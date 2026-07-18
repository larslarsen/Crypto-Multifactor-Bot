# Source note — DefiLlama (CORRECTION: emissions API now paid; SDK path moved)

**Role:** REFERENCE_METADATA (APIs ACCEPT) + emissions adapters CONDITIONAL (paid/relocated)
**Audit date:** 2026-07-18 (correction pass)

## APIs (reachable, retained)
- `api.llama.fi/v2/chains`: 457 chains, sha ba4b369f…; TVL family.
- `stablecoins.llama.fi/stablecoins?includePrices=true`: 410 assets, sha a2636737…;
  stablecoin circulating supply family.

## Emissions / unlock adapters — ACCESS CHANGE
- The old `DefiLlama/defillama-sdk` `emissions/adapters/...` path now returns **404** (the
  SDK tree no longer contains `emissions` paths). DefiLlama **restructured emissions into a
  paid API**: `https://api.llama.fi/emissions/<token>` now returns **HTTP 402** (Upgrade to
  paid plan) as of 2026-07-18.
- Implication: the free emissions/unlock bridge via DefiLlama is **no longer available**;
  it is now CONDITIONAL on a paid subscription. This strengthens the DIL-01 blocker.

## What we could inspect (before the change)
- SDK commit was pinnable (`fd8a8022…`); TVL/emissions are recomputed server-side; token/chain
  mappings live in adapter registries. Revision not client-visible.

## Required before promotion (CONDITIONAL)
1. Obtain a DefiLlama paid plan OR locate the current open-source emissions adapter repo
   (if any remains public) and pin its exact commit.
2. For each of ≥5 representative adapters: record repo+commit, file path, upstream sources
   (contracts/subgraphs), token/chain mapping, schedule logic, whether outputs are
   recomputed, and revision limitations.
3. Cross-check unlocked amounts against on-chain vesting contracts.

## Licensing
- APIs are open; the emissions API is now commercial. Respect upstream attributions and the
  paid-plan terms before using emissions data.
