# CEX-002 Corrected Sizing-Authority Source Review

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `RECORD_218_AND_CORRECTED_GATE1_ACCEPTED_SIZING_CORRECTION_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022; no new architecture decision
**Gate 1:** Accepted on corrected path-bound authority
**Gate 2:** Not accepted

## Record-218 decision

Record 218 and the corrected terminal publication are accepted. Hermes proved the exact
review-217 pre-state, ran one network-enabled ordinary qualification invocation, and
stopped. The command exited status 0 after 596 seconds. It downloaded no sample, ran no
retry or second qualification, and performed no sizing or bulk acquisition.

Commit `313387a987f8b08a3110198f17a6cf524f8181ee` contains exactly the changed report,
record 218, and the two controls; `HEAD == origin/main`. Repository control and whitespace
validation pass. The reviewer independently rehashed the live report, manifest, lock,
ledger, checkpoint, listing checkpoint, official metadata, production source, and CLI and
inspected the report's qualification, storage, retained-lineage, and authority fields.

The corrected report is 13,745,360 bytes at SHA-256
`f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09`. It reports
`gate_status=QUALIFIED`, `accepted=true`, no source blocker, no blocked product, 1,004
discovered symbols, 771 confirmed perpetual identities, and zero unresolved membership.
The seven release blockers are the expected unacquired full-release products; they do not
invalidate source qualification and do not authorize acquisition.

The corrected manifest detail is 11,292,635 gzip bytes at SHA-256
`64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113`, expanding to
466,714,158 bytes at SHA-256
`d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17`. Independent
streaming rehash reproduced both identities.

ADR-0022's corrected retained decomposition is exact:

| Quantity | Accepted value |
|---|---:|
| valid retained requirement keys | 73 |
| unique retained credit objects | 73 |
| unique retained credit bytes | 5,225,416 |
| selected-manifest consumable keys | 56 |
| complete-cost retained keys | 17 |
| rejected ambiguous recovered rows | 176 |
| unverified retained objects | 0 |

The 176 rejected checkpoint rows remain preserved lineage and are excluded from
consumability, source evidence, reuse, and credit. The selected/cost requirement remains
736,347 objects and 20,356,940,843 compressed bytes; accepted retained credit therefore
leaves 20,351,715,427 new Binance raw bytes. Gate 1 is accepted on this corrected
publication. Gate 2 remains unknown until the bounded local sizing experiment succeeds.

## Sizing defect now exposed

The frozen sizing implementation still names the pre-ADR-0022 report, manifest, lock,
ledger, qualification production, checkpoint, and metadata identities. Those pins must be
advanced to the accepted bytes above and these current live identities:

| Authority | SHA-256 |
|---|---|
| live version-4 lock | `6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e` |
| live amendment ledger | `2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf` |
| qualification production | `2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74` |
| qualification CLI | `473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f` |
| live progress checkpoint | `cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f` |
| listing checkpoint | `d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a` |
| official contract metadata | `7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42` |

Updating pins alone is insufficient. `prove_retained_acquisition_credit()` currently
examines only selected-manifest consumable rows, counts logical rows as objects, sums each
row's bytes, and never includes the 17 retained complete-cost keys. It cannot implement
ADR-0022's separate valid-key, unique-digest, and unique-byte quantities and would fail the
real sizing run even with current pins.

## Claude source authority

Sr Dev - Claude Build using Claude Opus 5 is authorized to edit exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`; and
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

The sizing CLI stays frozen at SHA-256
`78ee687c734fc94070952d290752acdbd007970fb26c616e5e6845f1de3702ad`.
Qualification production, qualification tests/CLI, transition source/tests/CLI, report 62,
data, evidence, records, and controls are frozen.

Make one complete ADR-0022 consumer correction:

1. Advance every accepted sizing-authority identity and size to the accepted record-218
   publication. Preserve all unchanged physical totals, plan counts, Coinalyze counts,
   projection policy, writer policy, capacity policy, and no-network behavior.
2. Re-prove retained acquisition credit over the union of selected-manifest and complete-
   cost requirement keys, never the sizing cohort and never arbitrary checkpoint rows.
3. Apply path-bound authority before credit. Fresh exact-key checkpoint rows remain valid.
   A persisted `recovered_from_retained_bytes` row is valid only when its basename binds
   exactly one full key in the complete frozen domain. Every report-declared rejected row
   remains excluded, and the two report locations carrying the rejected-key set must agree.
4. Rehash every credited content-addressed object and provider sidecar. A checkpoint claim,
   report count, basename, or matching byte size alone earns no credit.
5. Count valid logical requirement keys separately from unique content digests. Credit a
   digest's bytes once, and only after at least one valid full-key binding survives. Report
   the selected/cost logical-key decomposition and reject any mismatch with accepted
   56/17/73/73/5,225,416/176/0 facts before measurement or publication.
6. Keep `reconcile_physical_inputs()` pinned to 736,347 combined objects,
   20,356,940,843 combined bytes, and 20,351,715,427 projected new Binance raw bytes.
   Receipt authority and retained-credit fields must expose the corrected decomposition
   without implying Gate-2 or acquisition authorization.

Use the existing qualification path-bound helpers where they preserve one canonical rule;
do not create a weaker parallel interpretation. No caller or CLI option may choose the
candidate domain, rejected set, credit keys, counts, bytes, or deduplication behavior.

Update the synthetic fixture and tests in the same drop. At minimum prove:

- every new report/manifest/lock/ledger/source/checkpoint/metadata literal pin;
- exact accepted authority loads and every individual pin mismatch fails closed;
- selected and cost retained keys jointly produce the 56/17 decomposition;
- a persisted ambiguous recovered Kline row is excluded even when its bytes and sidecar
  rehash correctly;
- a fresh exact-key row with the same colliding basename remains valid;
- basename-unique recovered `bookTicker` remains valid;
- a valid logical duplicate digest increments key count but not object or byte credit;
- an invalid duplicate binding cannot preserve credit without another valid binding;
- rejected-key disagreement between report locations, count mismatch, missing entry,
  missing/corrupt object, missing/corrupt sidecar, wrong sidecar filename, and wrong byte
  size all block before envelope publication; and
- the full sizing flow still performs no network/credential read, mutates only its sizing
  evidence, and preserves deterministic collision-safe receipts.

Claude runs no test, Ruff, repository control, sizing, qualification, network, data
mutation, Git, commit, push, record, or control operation. Return exact SHA-256 hashes for
both edited paths, the new `def test_` function count, and a concise implementation
summary, then stop for reviewer inspection.

## Stop boundary

Hermes and sizing execution remain unauthorized. No bulk acquisition, normalization,
catalog publication, NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, paid
source, reduced scope, or next-ticket work is authorized. Gate 2 remains unaccepted and
next ticket remains `NONE`.
