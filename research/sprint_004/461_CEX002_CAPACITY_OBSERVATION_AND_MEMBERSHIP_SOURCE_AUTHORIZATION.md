# CEX-002 Review 461 - Capacity Observation and Membership Source Authorization

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** record the present release-capacity shortfall and authorize the smallest remaining Gate-3 source drop
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - three required products accepted
- **Next required actor:** Sr Dev - Codex Sol on GPT-5.6-sol High
- **Next ticket:** `NONE`

## Current accepted position

Three real Gate-3 products are accepted: `binance_usdm_open_interest_5m`,
`binance_usdm_bar_1h`, and `binance_usdm_trade_flow_1h`. Gate 2 is complete; no further
download or acquisition work is required. The remaining work is normalization of the other
declared products, Gate-4 reconciliation/coverage, and the Gate-5 pinned bundle and clean
NautilusTrader catalog check.

The read-only capacity observation on 2026-09-02 returned 14,583,615,488 available bytes.
The accepted v3 sizing envelope allocates 108,082,947,883 bytes for all typed normalized
partitions. The three accepted products account for 38,238,363,362 bytes of that frozen
allocation, leaving 69,844,584,521 bytes of uncompleted normalized allocation. Adding the
already-frozen 5,556,368,003-byte catalog/manifest/bundle allocation, 5,556,368,003-byte
bounded temporary allocation, and 29,690,701,415-byte operating reserve yields
110,648,021,942 bytes of remaining free-capacity requirement under the accepted envelope.
The present shortfall against that envelope is 96,064,406,454 bytes.

This review neither attributes the unrelated filesystem usage nor authorizes deletion,
cleanup, movement, process control, a lower reserve, or a storage-architecture amendment.
Large-product execution remains blocked until a separate reviewer decision proves adequate
capacity. The membership product is bounded to 5,383,893 projected bytes and can proceed
without pretending that the release-wide shortfall is closed.

## One membership source drop authorized

Sr Dev - Codex Sol on GPT-5.6-sol High is authorized to author production and test source for
exactly `binance_usdm_perpetual_membership`, confined to:

- `src/cryptofactors/ingest/binance_usdm_membership.py`;
- `scripts/research/normalize_binance_usdm_membership.py`; and
- `tests/ingest/test_binance_usdm_membership.py`.

The implementation consumes these accepted authorities read-only and pins their exact
identities:

- `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`, SHA-256
  `f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`;
- `data/cex002_qualify/cex002_official_contract_metadata.json`, SHA-256
  `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42`; and
- the accepted schema/writer/policy contracts in
  `research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`, SHA-256
  `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`.

It must publish exactly the 771 `accepted=true`,
`membership_class=confirmed_perpetual` identities from the 1,008 accepted classifications;
the other 237 classifications remain exclusion evidence and never become membership rows.
It must reproduce the accepted 698 detailed-metadata rows and 73 funding-only rows. A
funding-only row proves only `contract_type=PERPETUAL`; unavailable ticker metadata remains
null and is never inferred from a symbol. Conflicting stable facts, missing evidence,
unresolved membership, changed authority counts or hashes, duplicate symbols, or any schema
deviation fail closed.

The output must use the exact accepted 24-column typed membership schema and native-reference
identity rules. Current canonical instrument/version fields remain null with the accepted
explicit reference state; current snapshots are not backdated. Each native-symbol partition,
its authority lineage, and the final completion descriptor are content addressed under a
caller-specified hidden output root. Files are verified, flushed, and atomically renamed
without clobbering; the completion descriptor is written last. Interrupted output remains
invisible, and replay must prove and reuse byte-identical partitions. No catalog or bundle is
published by this drop.

The tests must cover the exact schema and real 771/237 and 698/73 authority splits, conflicting
evidence, funding-only null semantics, no symbol inference or canonical backdating, pinned
input identities, duplicate rejection, path/symlink/no-clobber safety, interruption
invisibility, and byte-identical replay. Test output is temporary only and cannot satisfy the
real-data gate.

Sol may run exactly this one targeted command once after authoring:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_membership.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact command/output without patching or
rerunning. Sol performs no real-data run, integration, repository-record edit, Git operation,
commit, push, network access, acquisition, cleanup, deletion, storage change, other product,
coverage product, bundle, catalog transaction, NautilusTrader check, experiment, model, or
Harmonic Trader work. It stops for reviewer source inspection.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/461_CEX002_CAPACITY_OBSERVATION_AND_MEMBERSHIP_SOURCE_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All implementation, data, runner, acceptance-command, and unrelated dirty paths remain
unstaged and untouched.
