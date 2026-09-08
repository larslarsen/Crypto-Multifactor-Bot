# CEX-002 Review 474 - Fixed Closeout and Price-State Source Authorization

- **Date:** 2026-09-08
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** freeze the existing completion checklist and authorize the next two related products
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - five of eleven required products accepted
- **Next required actor:** Sr Dev - Codex Sol on GPT-5.6-sol High
- **Next ticket:** `NONE`

## Fixed completion boundary

The owner directs completion of the existing ticket without continuing to make new versions of
it. The reviewer adopts that direction. CEX-002 retains its existing eleven products, historical
universe, accepted source and sizing authorities, amended economic contracts, and Gates 0-5.
This is an execution decision within those contracts, not a replacement ticket, acquisition plan,
schema version, or architecture amendment.

Accepted work remains accepted: open interest (Review 445), hourly bars and trade flow (Review
460), membership (Review 465), and realized funding (Review 473). These are five accepted products,
not a claim that five elevenths of the engineering effort is complete.

The remaining delivery sequence is fixed:

| Batch | Existing deliverables | Completion evidence |
|---|---|---|
| A | `binance_usdm_funding_indicative_1h`; `binance_usdm_mark_index_basis_1h` | Separate immutable products, source lineage, explicit gaps, exact economic checks |
| B | `binance_usdm_liquidation_observed_daily` | Observed/censored long and short values with units; required Coinalyze price/OI/funding overlap reconciliation |
| C | `binance_usdm_cost_calibration` | Frozen book-ticker/depth sample, fee gaps and the two already accepted ADR-0026 scenarios |
| D | `binance_usdm_coverage_gap`; `binance_usdm_harmonic_bundle`; final Gates 4-5 | Full coverage/daily intersection, bounded one-minute/hourly reconciliation, remaining independent economic checks, pinned bundle/catalog transaction, clean NautilusTrader readback, resume/replay evidence and final acceptance results |

These batches are a work order for the same ticket. Only Batch A's source paths below are
authorized now. Each subsequent batch requires reviewer disposition of the preceding result and
an exact-path assignment; it does not reopen the deliverable list. Batch D must also cite the
existing Gate-0 five-artifact quarantine acceptance/evidence and pinned holdout boundary. Missing
evidence for either remains an explicit existing requirement, never an assumed PASS. The unrelated
dirty BitMEX source paths do not prove Gate-0 completion.

The ticket is ready for final review only when every existing acceptance item is evidenced.
Hermes owns the original full pytest, Ruff, repository-control and whitespace commands, real
commands with exit codes, implementation records, and catalog/data publication. Reviewer
acceptance is exclusive. No partial release is relabeled complete.

## Controls against further churn

- Maintain the checklist in `tickets/CEX-002.md` and the current action in `CURRENT_TASK.md`.
  Update those summaries in place; do not prepend another copy of every review outcome.
  Historical evidence remains in its existing research records and Git history.
- A reviewer source pass examines the entire authorized drop and returns all discovered blocking
  defects together, each tied to an existing requirement. A correction addresses that list in the
  same bounded drop. Cosmetic preferences and optional improvements do not become release gates.
- Keep the selected senior responsible for the complete source/test correction when routing a
  mechanical fragment to another actor would add a handoff. Rotate only for the existing
  quality, availability, or usage reasons in DEVELOPMENT_ROLES.md.
- Reopen an accepted artifact only for specific evidence of an acceptance-invalidating defect.
  A typo in a summary is corrected in the record without rerunning accepted data.
- Reuse the accepted partition publication, typing, identity and authority patterns. No general
  framework rewrite, new acquisition generation, or new storage-sizing version is planned.
  A real blocker receives the smallest evidence-backed correction within the existing objective.
- At source acceptance, enumerate the complete Hermes validation/run/evidence workflow together,
  including an adequate execution duration and the exact existing path spellings. Do not add
  ceremonial handoffs between successful steps. Existing failure-stop and role boundaries remain.

## Owner model-selection clarification - 2026-09-08

The owner confirms that the reviewer may select any available OpenAI model. Record this
latitude in `docs/engineering/DEVELOPMENT_ROLES.md`; named Spark/Sol defaults do not restrict
the available choices. Selection remains based on task fit, reliability and end-to-end usage,
with existing role boundaries preserved. Batch A remains assigned to Sol High.

## Batch A authority and scope

Sol High is selected for the related hourly-source and exact-decimal work based on its accepted
hourly-kline implementation in Reviews 453/460. One source drop handles the shared premium input
and produces two separate products under ADR-0024. No other senior is concurrently authorized.

Sol may author exactly these three new paths:

- `src/cryptofactors/ingest/binance_usdm_price_state.py`;
- `scripts/research/normalize_binance_usdm_price_state.py`; and
- `tests/ingest/test_binance_usdm_price_state.py`.

Existing source/test paths, including the accepted normalizers and sizing implementation, are
read-only references. No package export edit or shared-helper refactor is authorized.

The reviewer inspected generation-0 completion/plan rows read-only on 2026-09-08. This inventory
is source-selection evidence, not a normalization run or full raw-file authentication:

| Family | Completed objects | Compressed bytes |
|---|---:|---:|
| `daily/indexPriceKlines` | 12,266 | 10,088,018 |
| `monthly/indexPriceKlines` | 21,721 | 372,102,491 |
| `daily/markPriceKlines` | 14,096 | 10,458,575 |
| `monthly/markPriceKlines` | 22,286 | 346,831,322 |
| `daily/premiumIndexKlines` | 11,439 | 8,452,758 |
| `monthly/premiumIndexKlines` | 20,932 | 290,695,727 |

All 102,740 objects totaling 1,038,628,891 bytes are already local. The indicative product uses
the 32,371 premium objects totaling 299,148,485 bytes. The accepted retained-credit counts are
one daily and nine monthly index objects, zero mark objects, and one daily and nine monthly
premium objects; all other selected completions are `checksum_verified`.

Use the accepted generation-0 state `data/cex002_qualify/gate2/state.sqlite` and its stored content
paths. Preserve repository-relative authority arguments: Reviews 432-434 already established
that changing their spelling can change receipt identity. Authenticate the terminal generation-0
chain, its 685,072 Binance completions and seal head
`8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`.

Pin the qualification report `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` at
SHA-256 `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09` and sizing receipt
`research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json` at SHA-256
`3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`. Their complete product
schemas, writer and policy identities remain authoritative. The schemas contain 22 indicative
columns and 33 mark/index/basis columns. Sizing row and partition counts are allocation bounds,
not observed row counts or a requirement to fabricate joined rows.

Before parsing each selected ZIP, authenticate its top-level plan envelope and nested payload,
provider/family/symbol/interval/period, completion, canonical contained content path, raw size/hash,
and the physical checksum sidecar's path, size, hash, ZIP basename and checksum statement. Retained
credit remains valid only with its accepted proof. Use read-only, no-follow authority access and
complete sidecar checks as in the corrected realized-funding implementation. An unauthenticated
filesystem scan or V3 recovery manifest is not a replacement for this generation-0 authority.

## Existing economic and publication contracts applied to Batch A

1. Parse the accepted headed/headerless twelve-field hourly archive format. Validate ZIP/member/
   key identity, CRC, finite decompression/row bounds, exact integer times/counts and exact
   `decimal128(38,18)` source values without float conversion, rounding or ambient decimal-context
   dependence. Preserve original ordinals and all declared fields. Preserve the accepted
   non-overlapping monthly/daily selection and source-period ownership.
2. Premium OHLC values are signed and may be zero. They are index observations, not executed
   trade prices or volumes. Preserve ancillary source fields, including authentic zeros; do not
   apply trade-flow buy/sell or price-times-volume identities to these index families. Validate
   each family's time/OHLC consistency and detect conflicting duplicate observations.
3. Indicative funding publishes the premium inputs. As already fixed in the accepted schema and
   sizing implementation, `indicative_funding_rate` is null and `indicative_rate_status` is
   `direct_indicative_rate_unavailable`. Do not relabel premium as a funding rate, estimate a
   future settlement, copy realized funding into it, or invent zero rates. The declared nullable
   field is honest unavailability; the product's observed premium data must be real and non-empty.
4. Join mark, index and premium only on identical native symbol, open time and close time. Never
   join on row position, forward-fill, bridge a gap or take a later observation. Mark/index prices
   must be positive. Compute `absolute_basis = mark_close - index_close`. For relative basis use
   the already accepted sizing equation on scale-18 integers: `(absolute_unscaled * 10**18) //
   index_unscaled`, reconstructed at scale 18. Document this derived-value floor rule, including
   negative values, rather than describing a non-terminating ratio as exact. Preserve
   `basis_join_status=causal_open_time_join`; close-derived values must not be exposed at bar open.
5. Keep native identity and the accepted explicit null canonical-reference state. Unknown source
   availability stays unknown. Bind retrieval time and availability semantics in lineage; neither
   is replaced with bar event time. Mark rows supply the joined row's primary raw reference and
   original ordinal; lineage also binds the exact index and premium source references/ordinals.
   The single shared `source_reserved` value must agree across joined mark/index rows.
6. Deterministically order observations within one symbol/month. Agreeing repeated observations
   may collapse only with every original source/ordinal retained; conflicts fail. Record missing
   hours and unjoinable intervals as typed product gaps with source lineage. Every selected source
   and every physical row must reconcile to an output, an explicitly recorded identical duplicate,
   or an explained unjoinable observation. No invalid economic row is silently discarded or
   repaired; ADR-0035's trade-kline exclusions do not automatically extend to index data.
7. Publish separate content-addressed Parquets, lineages, quality gaps and last-written completion
   descriptors under separate product subdirectories of one caller-selected hidden root. Reuse
   the accepted no-clobber, fsync, same-filesystem publication and deterministic replay contract.
   A product with no joined rows for a partition records the gap instead of publishing an empty
   successful Parquet. No product completion is a visible bundle/catalog release.
8. Retain at most one symbol/month's market rows at a time. Accumulate whole-product statistics
   incrementally; ordered artifact descriptors may be retained, the entire market-row corpus may
   not. Read each shared premium ZIP once per invocation for both products. Completion separately
   reconciles source sets/bytes/states, physical/duplicate/output/unjoinable rows, lineage, actual
   schema, hashes, gaps and observed ranges for each product. Resume reproves existing artifacts.

The CLI accepts explicit `--generation0-state`, `--generation0-content-root`, `--report`,
`--sizing` and `--output-root` paths and returns a concise JSON result for both products. This
assignment authorizes source only; no real output root is created by the developer.

The test source must cover both frozen schemas; headed/headerless and daily/monthly inputs;
signed/zero premium and unavailable indicative rates; positive mark/index and exact signed basis
arithmetic; missing/nonmatching joins with durable gaps; duplicate/conflict and full multi-source
lineage accounting; authority/plan/raw/sidecar refusal; unsafe ZIP/path rejection; bounded row
retention; interruption, concurrent no-clobber, completion-last visibility and byte-identical
replay. Include differing source ordinals across a join and negative non-terminating basis ratios.

Sol returns the complete three-path drop with SHA-256 and line counts for reviewer static
inspection. Sol performs no tests, real-data execution, integration, repository-record edit, Git,
commit, push, data mutation, acquisition, network, cleanup, other product, experiment or model
work. Hermes is not authorized until reviewer source acceptance. The owner relays the assignment.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review publishes exactly:

- `research/sprint_004/474_CEX002_FIXED_CLOSEOUT_AND_PRICE_STATE_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `tickets/CEX-002.md`; and
- `docs/engineering/DEVELOPMENT_ROLES.md` (owner model-selection clarification only).

The reviewer changes only these governance paths. This decision executes no acceptance commands,
integrates no developer source and changes no data or prior product acceptance.
