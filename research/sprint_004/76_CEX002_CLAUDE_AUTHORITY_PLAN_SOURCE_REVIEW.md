# CEX-002 Claude Authority and Plan Source Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; RETAIN DIRECTION; AUTHORIZE ONE SURGICAL CLAUDE
CORRECTION**

## Reviewed state

Committed base: `HEAD == origin/main == 495d5f7baf78bdc330d712694850de5e4d7c6c3d`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `bf0ebaf8d88963c6b51821e56784f208702fb1afbb0741b668f94468dc123acb` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `c504523a9cf3d8bbe821fb5e647ac7b1052a89063121f57c60177c28d8dbf8ca` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `88d7bbbb37005a91c7e95bc61b90fd6c8bf917da9adc61202e21e81508f7811c` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/exchange_info.json` | `17815bc25ccbe3c8bf3dd624cad99274b4059c2a3a81ccf4e91a8063ffae212a` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_future_markets.json` | `47416908780ef674efdf1cb3a62cb215c4f48834ad932f9c20e080eb6649b83f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_funding_rate_history_anchors.json` | `2537212f7b423a991a4ed9aa2413df72843dc059768e53f23260eddfe5de1f3f` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_liquidation_history_anchors.json` | `d4e7834b6705e8c21329c04fa9738c29030e1da9c674b7d57e9ba4f3977e9ad0` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_ohlcv_history_anchors.json` | `8fd1ddd5eb4b498badc4b203831872b3c1b006fb892f196f6d5273932d0de6d5` |
| `tests/acquisition/fixtures/binance_usdm_harmonic_qualification/coinalyze_open_interest_history_anchors.json` | `30be3ac8ba27213a381675f24a6f83b6de85d139032662101d14e9f8d626f9df` |

Only those nine CEX-002 paths are reviewed. Every DEX/BitMEX path and transient sidecar in
the dirty worktree remains unrelated and excluded.

## Accepted direction

The drop materially improves the design. Archive names no longer promote themselves;
current `PERPETUAL`, delivery, TradFi, settlement-shaped, dated, funding-evidenced, and
unresolved names are separately reported. Source qualification and coverage state are
separate. BTCUSDT/ETHUSDT replace alphabetical Coinalyze edges, the full support map is
retained, logical and physical storage are separated, and a plan lock plus cumulative
ledger replace the per-invocation greedy allowance.

These changes should be preserved. The residual failures below still prevent Hermes
integration.

## Blocking findings

### 1. A hard interruption can lose a completed download from the cumulative ledger

`_acquire_sample` writes and flushes the completed sample checkpoint before returning.
`run_source_qualification` records the new byte count in `BudgetLedger` only after that
return. A kill between those operations leaves a retained completed object with no ledger
entry. On resume, the object is treated as reused and is never reconciled into the ledger,
so the missing charge restores allowance and permits more than the cumulative limit.

The new cumulative test completes both writes normally and does not inject an interruption
at this exact boundary. The budget is therefore not crash-safe yet.

The legacy bootstrap also calls all retained checkpoint bytes a chargeable lower bound.
That includes the six checksum-proven samples which review 67 explicitly made budget-free.
Because old and new retained bytes are not fully attributable from the checkpoint alone,
the defensible chargeable range is zero through the verified retained total, not the total
as a lower bound. The prior breach remains established by record 74; source must report
uncertainty without inventing a larger charge.

### 2. Retained historical contract metadata is not retained source authority

`FapiCurrentContractSource` retains raw exchangeInfo bytes, but its protocol returns only a
parsed mapping. The metadata store then records selected fields and a hash of reconstructed
JSON. On load it accepts any syntactically valid row with a `contract_type`; it does not
rehash retained FAPI bytes, reparse the identified response, or prove that the stored row
occurred in it. A valid-JSON edit can therefore manufacture a historical perpetual and
silently change the accepted universe.

`parse_exchange_info_rows` also requires only `symbol` and `contractType`, while review 75
requires the fields that prove native identity, status, and underlying type. Missing
`pair`, status, underlying type, base, quote, or margin identity currently fails open.

### 3. The plan is not actually bound to stable authoritative inputs

The retained-evidence digest covers only key and byte size, not the raw digest or provider
sidecar authority. The membership digest covers only symbol and class, not the official
evidence identities. The code/config digest is a manually maintained version payload, not
the executed source/config identity.

The budget digest includes current cumulative spend and the retained digest includes the
growing retained set. Consequently, a completely normal successful resume changes the
locked inputs. The implementation reports `plan_inputs_changed` but continues and may
still qualify the gate; a real inventory, membership, code, or evidence change is not
fail-closed. The public `--relock-sample-plan` switch can reselect keys without a new
reviewer authorization, contradicting the one immutable Gate 1 plan contract.

The lock also accepts arbitrary valid-JSON actions and has no plan-content identity check.
Changing `download` to another string bypasses the pre-download budget guard while still
allowing `_acquire_sample` to fetch the object.

### 4. Storage credit is labelled verified without revalidation

The physical requirement is correctly deduplicated by remote key, but retained credit is
calculated from every completed checkpoint row whose key is required. Those rows are not
all rehashed and their provider sidecars are not all re-proved; only current plan
candidates pass through `_acquire_sample`'s reuse verification. Missing or tampered raw
bytes outside that small sample set can therefore reduce projected Gate 2 bytes while
being reported as `retained_verified_credit`.

The per-product logical object and byte totals also still aggregate the full archive union,
including excluded and unresolved names, while their coverage states evaluate the
confirmed universe. The report must label full-union inventory separately and publish
accepted-universe logical totals so the two scopes cannot be confused again.

### 5. Temporal gap explanations are not evidence-based

Every head gap is nonblocking even when `explained_by_family_launch` is false. Every tail
gap for a symbol absent from today's confirmed list is nonblocking as `tail_gap_delisted`,
without an authenticated close/delivery boundary. For a single-family product, first and
last are computed from that same family, so a missing leading or recent tail cannot be
detected at all.

This can silently release data with unexplained missing history. Expected windows must be
derived from authenticated onboard/close/delivery evidence and the source-family global
launch/latest cutoff. Unknown boundaries remain typed blocking evidence. Only an
affirmatively explained pre-listing, family-launch, or post-close interval is nonblocking.

### 6. The product gap evidence truncates Coinalyze coverage

The full support block retains every unmapped symbol, but the liquidation product emits
only `unmapped[:200]` gap records. Review 75 requires every gap. The product matrix and
coverage-gap product must retain the complete set and must validate each Coinalyze market's
native `symbol_on_exchange`, not only a mechanically constructed provider symbol.

## Surgical correction authorization

Sr Dev — Claude Build using Claude Opus 5 may modify only the same nine reviewed paths.
It must preserve the accepted direction and make only these corrections:

1. Make budget accounting interruption-safe. Durably reserve a planned new object's bytes
   before its network acquisition, or implement an equivalent write-ahead transaction.
   A completed checkpoint can never exist outside the charged/reserved ledger state. On
   resume reconcile every reservation against rehashed raw/checksum evidence; unresolved
   reservations remain conservatively charged. Add a hard-abort test exactly after sample
   checkpoint flush and before ledger finalization, then prove no allowance is restored.
2. Report legacy chargeable accounting as an honest range when budget-free baseline bytes
   cannot be distinguished. Keep remaining allowance at zero while the range could exhaust
   the budget. Do not call all retained bytes a chargeable lower bound. Preserve record
   74's external breach rather than rewriting it.
3. Return a structured FAPI response carrying retained raw bytes, content path, SHA-256,
   byte count, retrieval time, endpoint, and parsed payload. Historical metadata snapshots
   must reference that content-addressed response. Rehash and reparse it on every reuse and
   prove the exact row; missing/tampered/mismatched evidence fails closed. Require all
   native identity, contract, status, underlying, base, quote, margin, onboard, and
   delivery fields needed by the classification/coverage contract.
4. Bind the immutable plan to full authoritative identities: listing/inventory evidence,
   membership classifications plus evidence digests, raw/checksum retained evidence, and
   actual executed code/config identity. Freeze the initial retained and budget snapshot;
   later execution progress is not an input change. Any genuine input mismatch blocks the
   gate before download. Remove the public relock switch; a new plan requires a future
   reviewer authorization. Validate allowed actions, totals, key/URL/family relationships,
   and a plan-content digest. Add normal-resume, genuine-mismatch, and valid-JSON tamper
   tests.
5. Rehash raw bytes and re-prove provider sidecars for every credited required key. Count
   no unverified credit. Emit separately labelled full-archive inventory totals and
   confirmed-universe logical totals, with physical remote-key totals remaining
   deduplicated across products.
6. Calculate expected temporal windows from authenticated contract lifecycle evidence and
   family-wide source cutoffs. Unexplained heads, unknown delisting tails, and missing
   recent current coverage block release while source authority remains official. Add
   tests for an unexplained head, a current single-family missing tail, a proven post-close
   tail, and an unknown historical tail.
7. Remove the Coinalyze gap truncation and require exact exchange/native identity from
   `symbol_on_exchange` for anchors and the complete support map. Retain every unmapped
   symbol as a typed product gap.

Claude performs no test execution, network/data run, integration, repository-record edit,
Git operation, commit, push, purchase, deletion, catalog mutation, Gate 2 work, Nautilus
work, or Harmonic Trader work. It stops for fresh reviewer source inspection with exact
hashes. Hermes remains unauthorized.

## Publication set

Under the narrow reviewer governance exception, the reviewer may stage, commit, and push
exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/76_CEX002_CLAUDE_AUTHORITY_PLAN_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, prior report/record, or unrelated dirty path belongs to
this publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, Hermes integration, every real rerun,
Nautilus integration, every other ticket, and Harmonic Trader work remain unauthorized.
Next ticket remains `NONE`.
