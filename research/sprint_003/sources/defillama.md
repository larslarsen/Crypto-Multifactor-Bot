# Source note — DefiLlama

**Role:** REFERENCE_METADATA (TVL, stablecoins) / REFERENCE_METADATA (emissions adapters)
**Audit date:** 2026-07-18

## Samples acquired
- `api.llama.fi/v2/chains`: 457 chains, sha ba4b369f…; TVL family.
- `stablecoins.llama.fi/stablecoins?includePrices=true`: 410 assets, sha a2636737…;
  stablecoin circulating supply family.
- GitHub `DefiLlama/defillama-sdk` commits: pinned commit retrieved, sha fd8a8022….
- Emissions adapter `emissions/adapters/ethereum/index.ts` at pinned commit: **HTTP 404**
  (sha d5558cd4…) — path/content moved.

## Schema / semantics
- Chains: [{name, tvl, tokenSymbols, ...}]; stablecoins: [{pegType, circulating[chain]}].
- Emissions adapters are TypeScript per protocol; upstream = protocol contracts / subgraphs;
  emit unlocked/emitted amounts. Token/chain mappings live in the adapter registry.

## Correction / revision (important)
- TVL and emissions are **recomputed server-side** on each query; history is not a fixed
  file. Adapter code can change; results may differ after an adapter update.
- **Pin the SDK commit** and record it; verify adapter registry for token/chain mappings
  and recomputation behavior before reliance.

## Timestamp precision
Date strings / unix for TVL; block-based for emissions.

## Licensing
APIs and SDK are open (MIT-style); research use permitted. Redistribution of derived
datasets should respect upstream attributions.

## Gaps
- Adapter path at pinned commit 404'd; need to resolve current adapter location and
  confirm methodology/revision cadence (Open Q6).
- Emissions adapter output is the practical bridge to unlock/emission data for `DIL-01`,
  but vintage preservation is unverified.
