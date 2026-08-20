# CEX-002 Gate 1 Resumable Execution Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT GATE 1 EVIDENCE; ACCEPT HERMES INTEGRATION DISCIPLINE; AUTHORIZE ONE
BOUNDED CLAUDE SOURCE/TEST CORRECTION**

## Reviewed committed state

`HEAD == origin/main == 9d6339244c51cf5b8ace4e4cb72ba6b0f7760b78`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `c32b74f543c9254c81579a0275364b943a262c35f3b72050fa9560dbc7abdb90` |
| `research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json` | `ddedc886f229bfb51b9eb516490654f50a24a72a5a11ec9b95142f56ed3cdc85` |
| `research/sprint_004/74_CEX002_GATE1_RESUMABLE_EXECUTION.md` | `ebe5ad48794cc82827e1e202a3df12cd47e54b19cbef00f316f6895f67a0b3ef` |

The worktree also contains unrelated DEX/BitMEX work and transient database sidecars. None
is part of this review or the publication set below.

## Accepted execution evidence

Hermes followed review 73's role boundary and stop conditions. The focused CEX-002 suite
reported 79 passed, the atomic-download suite 11 passed, Ruff and both control checks
passed, exactly the three accepted source/test paths were committed at `70ded45`, the
credential remained environment-only and redacted, and both real runs honestly exited 2.
The listing checkpoint was fully reused on run 2 and the 4.1 GiB store was preserved.

Those are positive integration and operational-resume results. They do not make the
source matrix or Gate 1 data evidence acceptable.

## Blocking findings

### 1. The report promotes an unproved archive union to perpetual membership

The report declares `binance_usdm_perpetual_membership` official and complete over 1,004
symbols while its own rule says archive directory names are not contract-type proof. Of
those names, only 698 are authenticated current `PERPETUAL` rows; 309 are merely
`historical_or_delisted_candidates`, including 50 dated delivery names and 17 settlement
artifact names. Archive-only candidates such as `BTCUSDT_210326`,
`AERGOUSDTSETTLEDSETTLED`, `AAPLUSDT`, and `ANTHROPICUSDT` then generate false required-
product gaps as if their perpetual status had been proved.

Binance's official contract enums distinguish `PERPETUAL` from monthly and quarterly
delivery contracts, and current `exchangeInfo` exposes `contractType`, `status`,
`underlyingType`, and native identity. Official continuous-contract documentation also
distinguishes `TRADIFI_PERPETUAL`. The implementation may inventory every archive name,
but it may not promote candidates, delivery contracts, settlement artifacts, or another
contract type into the ADR-0017 universe without affirmative official evidence.

Primary references inspected:

- `https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/common-definition`
- `https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#exchange-information`

### 2. The 256 MiB budget is per invocation, not cumulative

Review 67 authorized at most 256 MiB of new Gate 1 sample downloads in total. The planner
recomputes against the currently retained keys and initializes `spent = 0` on every
invocation. Run 1 selected 266,836,686 new bytes; run 2 then selected a complementary
30,367,993 bytes with a fresh allowance. The report's representative keys, samples,
matrix counts, incidents, and budget blocks therefore changed on resume, and the required
semantic identity assertion failed.

The additional retained bytes must remain preserved. They may be identified as legacy
over-budget evidence, but they may not silently become proof that the cumulative contract
was met.

### 3. Gate 2 is physically infeasible on the current destination as reported

The report attributes 6,628,196,148,904 bytes to the membership product and
6,174,436,174,147 bytes to trades, but does not publish a deduplicated physical object and
byte total across accepted-universe source keys. The current filesystem has only
191,467,429,888 bytes available. Even the reported trade bytes alone exceed available
space by more than 32 times.

Record 60 requires ordinary storage to be measured from the complete inventory before
bulk acquisition. Gate 2 cannot be authorized until the corrected universe has an exact
deduplicated compressed-raw requirement, retained-byte credit, projected new bytes, local
capacity snapshot, and explicit shortfall. Normalized/catalog storage must be reported as
an additional bound or explicitly unknown; it cannot be treated as zero.

### 4. Source qualification is conflated with full temporal coverage

The matrix reduces an official source to `sample_only` whenever every universe symbol
does not appear in every declared family group. Legitimate pre-listing periods, source-
family launch dates, delisted tails, and current unarchived contracts are coverage facts,
not by themselves failures of source authenticity, schema, checksum, or access.

The corrected report must separate source-family qualification from per-symbol temporal
coverage. It must retain every gap, but use distinct states such as official qualified,
qualified with typed gaps, inaccessible, schema/integrity failure, and membership
unresolved. A product may remain release-blocked by gaps without falsely describing the
official source as sample-only.

### 5. Coinalyze qualification samples an unstable alphabetical edge

The qualifier maps the first two generic sample symbols, which produced
`0GUSDT_PERP.A` and `IOSTUSDT_PERP.A`; Coinalyze returned only IOST and the exact-symbol
guard correctly failed. That proves the guard, not that the required Coinalyze source is
inaccessible. Gate 1 needs stable declared qualification anchors plus a separate full-
universe support/gap map.

## Fixed correction contract

Sr Dev — Claude Build using Claude Opus 5 is authorized to correct only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`;
- `scripts/research/qualify_binance_usdm_harmonic_sources.py`, only if the report/CLI
  contract requires it;
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/`, only for bounded
  fixtures.

The correction must implement all of the following:

1. Preserve the complete archive-name inventory, but construct accepted historical
   perpetual membership only from affirmative official evidence: an authenticated current
   `exchangeInfo` row with `contractType == PERPETUAL`, a retained official historical
   metadata row with that exact type, or an official realized-funding observation whose
   source semantics prove a perpetual contract. Emit separate, auditable classifications
   for confirmed membership, delivery/non-perpetual evidence, settlement/archive
   artifacts, `TRADIFI_PERPETUAL`, and unresolved archive-only candidates. Unresolved
   candidates block membership; names and spelling never promote or silently exclude one.
2. Retain complete current exchange rows and the fields needed to prove native identity,
   contract type, status, and underlying type. Do not change the ADR-0017 venue or scope;
   any contract class outside exact `PERPETUAL` remains separately reported and excluded
   unless a future ADR changes the scope.
3. Replace the per-run greedy plan with one immutable versioned plan bound to digests of
   the complete inventory, membership evidence, code/config, budget, and initial retained
   evidence. Once locked, resumes may change only execution state (`download` to verified
   reuse), never selected keys, blocked keys, matrix/sample identity, or cumulative budget.
   Preserve the legacy plan and all retained bytes. Reconstruct and report the prior
   budget breach where evidence permits; otherwise emit an explicit lower bound and
   `legacy_budget_accounting_unresolved`. No new byte may be planned after the cumulative
   allowance is exhausted.
4. Publish exact deduplicated physical source-key object/byte totals for the confirmed
   universe, exact verified retained credit, projected new compressed-raw bytes, local
   available bytes, and shortfall. Keep per-product logical totals separate because they
   overlap. Report normalized/catalog storage as a bound or unknown. Storage insufficiency
   keeps Gate 2 blocked without relabeling a qualified source as inaccessible.
5. Split `source_qualification_state` from `coverage_state`. Preserve per-symbol first/last
   observations, missing family/interval evidence, current-unarchived gaps, and every
   unresolved membership item. Do not demand that a source family predate its own launch
   or a contract's listing to qualify its authority.
6. Qualify Coinalyze history with declared stable BTCUSDT and ETHUSDT anchors only after
   both are authenticated confirmed Binance perpetuals and matched in Coinalyze's Binance
   perpetual market list. Require exact returned identity and non-empty liquidation, OI,
   funding, and OHLCV samples for each anchor, retaining existing raw-response provenance,
   unit, retention, attribution, and overlap rules. Separately report the full confirmed-
   universe Coinalyze supported/unmapped set; anchor success is not full coverage.
7. Add focused tests for delivery/settlement/TradFi/unresolved classification, no
   archive-name promotion, immutable multi-process plan identity, cumulative budget across
   interruptions, legacy-plan preservation and breach reporting, deduplicated physical
   storage/shortfall, qualification-versus-coverage states, stable Coinalyze anchors, and
   full-universe support gaps. Retain every previously accepted integrity, retry,
   checkpoint, redaction, and malformed-evidence test.

Claude authors source and test source only. It performs no test execution, network/data
run, integration, repository-record edit, Git operation, commit, push, purchase, deletion,
catalog mutation, Gate 2 work, or Harmonic Trader work. It stops for fresh reviewer source
inspection with exact hashes. Hermes integration and every further real run remain
unauthorized.

## Publication set

Under the narrow reviewer-authored governance exception, the reviewer may stage, commit,
and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/75_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, data, report 62, record 74, or unrelated dirty path is part of this
publication. The reviewer does not execute tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, every other ticket, Nautilus integration,
and Harmonic Trader model work remain unauthorized. Next ticket remains `NONE`.
