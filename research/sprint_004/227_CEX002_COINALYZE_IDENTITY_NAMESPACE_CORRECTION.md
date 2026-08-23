# CEX-002 Coinalyze Identity Namespace Correction

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `RECORD226_ACCEPTED_PROVIDER_NATIVE_CORRECTION_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022 and ADR-0023
**Gate 1:** Accepted
**Gate 2:** Not accepted

## Record 226 review

Hermes's record-226 integration, validation, and stop are accepted. Commit
`913bf4c10733fe31ed957b9a927b01db48700345` contains exactly the five authorized paths,
is published at `origin/main`, passes repository control and whitespace validation, and
retains the accepted source/test/CLI identities. The complete 153-case focused suite and
exact-path Ruff both passed. Hermes then ran the first exact local sizing invocation and
correctly stopped after status 1 without retry or repair.

No receipt 180 was published. Before the Coinalyze failure, the command durably published
96 content-addressed Binance sizing envelopes totaling 1,890,921 bytes. They are valid
ignored measurement evidence from the accepted source identity, are not repository
content, and must not be deleted or rewritten. A later run may reuse one only after the
existing byte and measurement-identity checks pass. The post-failure evidence store has
41,468 files and manifest SHA-256
`361095f2be95d9efab91046b910f76cc514e8e2fc1a79e1d359ead2f13ddedb6`.

## Root cause

The failure is a namespace mismatch in sizing source and its synthetic fixture, not an
unsupported retained symbol:

- report `coinalyze.universe_support.supported_symbols` contains 569 Binance-native
  identities such as `BTCUSDT`;
- Binance membership and authenticated lifecycle dictionaries use that native namespace;
- the retained liquidation response correctly contains Coinalyze provider identities
  `BTCUSDT_PERP.A` and `ETHUSDT_PERP.A`;
- the pinned `/future-markets` body explicitly binds each provider identity to its
  `symbol_on_exchange` native identity; and
- report `anchor_identity` records the same two native/provider pairs.

The sizing code compares the retained provider strings directly to the native supported
set and indexes native lifecycles with them. Its fixture hid this defect by putting
`SYM*_PERP.A` provider strings in `supported_symbols`, omitting real future-market row
fields, and keying lifecycles to the same provider strings.

Read-only inspection proves the retained inventory contains 759 unique Binance perpetual
provider/native pairs, the report declares the same 759 validated markets, and every one
of the 569 supported native USD-M identities has exactly one inventory row. The additional
190 inventory identities are not part of the supported USD-M projection and do not expand
scope.

No report, retained response, membership, lifecycle, or ADR rewrite is warranted. The
sizing consumer must preserve and explicitly translate the two namespaces through the
already-pinned mapping evidence.

## Authorized senior correction

Sr Dev - Claude Build on Claude Opus 5 is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`; and
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

The production correction must:

- parse the pinned future-market inventory into explicit one-to-one provider-to-native and
  native-to-provider mappings using `symbol`, `symbol_on_exchange`, `exchange`, and
  `is_perpetual`; reject missing fields, wrong types, duplicates, collisions, and
  conflicting bindings;
- re-prove the inventory's unique Binance-perpetual count against both report
  `binance_perpetual_market_count` and `native_identity_validated_markets`;
- re-prove that every supported native symbol has exactly one mapping, without treating
  unrelated provider, base-asset, or inventory strings as interchangeable evidence;
- re-prove each report `anchor_identity` native/provider/`symbol_on_exchange` triple, and
  its agreement with `anchor_symbols`, `requested_symbols`, `matched_markets`, the
  inventory mapping, and the retained liquidation response;
- keep supported sets, unmapped gaps, lifecycle bounds, projection groups, and partition
  keys in Binance-native identity;
- treat liquidation response `symbol` values as Coinalyze provider identity, map each
  through the proved inventory authority before supported-set and lifecycle checks, and
  reject unknown, unsupported, duplicate, or conflicting retained series;
- retain both identities explicitly in coverage evidence and receipt output, with
  unambiguous names such as `retained_provider_symbols` and `retained_native_symbols`;
  remove or precisely redefine any ambiguous `retained_symbols` field; and
- preserve exact retained byte/point credit, lifecycle/day validation, one-symbol request
  projection, all envelope measurements, and every unrelated accepted sizing invariant.

Do not derive native identity by stripping `_PERP.A`, adding/removing suffixes, parsing
quote assets, or assuming one naming shape. The retained future-market pair is the
authority. Do not count the 190 unrelated inventory identities in the 569-symbol USD-M
projection.

The synthetic fixture must mirror the real namespaces: native supported symbols and
membership/lifecycle keys, provider symbols in retained API bodies, and complete
future-market rows with explicit provider/native bindings. Add focused tests for:

- the real BTC/ETH-shaped provider-to-native success path;
- exact 759-style inventory-count agreement at fixture scale and exact 569-style supported
  subset agreement at fixture scale;
- same counts with substituted bindings, missing supported mappings, duplicate provider or
  native identities, conflicting bindings, wrong exchange, and non-perpetual rows;
- retained provider identity mapping to native lifecycle bounds;
- native strings or unknown provider strings appearing in a retained response;
- duplicate retained series and two provider identities colliding onto one native;
- disagreement among anchor identity, requested symbols, matched markets, inventory, and
  the retained response; and
- receipt output carrying separate provider/native retained identities while projected
  lifecycle/partition counts remain native and unchanged.

Preserve all existing tests, the 96 published Binance envelopes, and the exact sizing CLI.
Claude runs no test, Ruff, sizing, data, record, Git, commit, push, or later command. Stop
for reviewer source inspection with production/test hashes and the unchanged CLI hash.

This reviewer-authored governance publication is restricted to exactly:

1. `research/sprint_004/227_CEX002_COINALYZE_IDENTITY_NAMESPACE_CORRECTION.md`;
2. `docs/handoff/CURRENT_TASK.md`; and
3. `tickets/CEX-002.md`.

## Stop boundary

This authorizes one provider/native identity source/test correction only. It authorizes no
integration, command execution, sizing retry, deletion or substitution of envelopes,
Gate-2 acceptance, network, acquisition, normalization, catalog work, NautilusTrader,
Harmonic Trader, payoff analysis, PAPER, LIVE, paid data, reduced scope, or next-ticket
work. Next ticket remains `NONE`.
