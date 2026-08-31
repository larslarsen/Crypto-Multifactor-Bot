# CEX-002 interrupted recovery and acquisition continuation

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** `IN_PROGRESS` / blocked
- **Next ticket:** `NONE`

## Disposition

Review 352 authorized exactly one standard acquisition invocation. Its network-free binding
phase recovered and sealed unfinished run 6 under its original identity with stop reason
`interrupted`; the same invocation then created run 7 and continued the frozen plan.

Run 7 encountered a new validation message outside Review 352's three-message metrics
revision set:

```text
AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling
```

Per the explicit stop rule, Hermes stopped the invocation and did not resolve the ZIP ceiling.
The engine returned `exit=2` with `stop=partial`. No second acquisition, manual recovery,
plan, replay, `verify`, revision disposal, source/test edit, Gate 3, normalization, catalog,
or next-ticket work ran. The ZIP-ceiling disposition remains with the reviewer.

## Preproof

The repository/environment preproof passed read-only:

```text
HEAD=583a0e23e9500cb46999d1f33062c7547236242d
ORIGIN_MAIN=583a0e23e9500cb46999d1f33062c7547236242d
commit fbe98b1 ancestor=yes
Review-352 present=yes
record-351 sha256=84ccb39cc6f1c580278c9a7522a7b469ceb59f658f1f721a8d22935a40068fb0
acquisition source sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
acquisition test sha256=40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624
acquisition CLI sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
staged paths=none
.git/index.lock=absent
.env=ignored, regular, owner lars:lars, mode 600, nonempty key syntax
```

The governed implementation paths were clean. All unrelated modified and untracked paths
were preserved. The SQLite preproof used
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
`PRAGMA query_only=ON`, and observed `query_only=1`. Integrity was `ok`; the foreign-key
check returned zero defects. No connectivity probe, separate recovery call, plan, replay,
or `verify` ran.

Before the invocation, the sealed head was receipt
`64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163` with
`attempt_hi=1307879`, `completion_hi=574392`, `sidecar_hi=625313`, `charge_hi=0`,
`transition_hi=0`, `run_hi=5`, and `seal_hi=4`. Exactly one unfinished run 6 existed with
the Review-352 identity and tail facts. No active partial/terminal files were present, and
capacity was sufficient.

## Exact invocation and outcome

The one invocation was run from the repository root with the authorized command:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 24h \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify --max-wall-seconds 84600
)
```

The complete bounded output available from the command wrapper was:

```text
command=acquire exit=2 stop=partial
```

The invocation started at `2026-08-31T17:47:26.181191+00:00` and ended at
`2026-08-31T19:08:55.083420+00:00` (5,489 seconds elapsed). It was not rerun.

## Recovery receipt: run 6

Run 6 was finalized under its original identity before run 7 began:

```text
run_id=00fc2af29dbf1e585ecc28974bdb034bdbcf7815b464ea333d5ddc10fae9dab4
started_at=2026-08-31T05:35:00.545590+00:00
ended_at=2026-08-31T17:46:42.492193+00:00
stop_reason=interrupted
predecessor=64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163
attempt_delta=235359
completion_delta=92215
gap_delta=0
byte_delta=1459224114
network_calls=235359
error_count=50921
attempt_hi=1543238
completion_hi=666607
sidecar_hi=717532
charge_hi=0
transition_hi=0
run_hi=6
seal_hi=5
receipt_sha256=1cf814d73aed5ab2d7aadccd8e57302339a0e78df40504d40e2d0dbbf457ee62
```

The recovered receipt was published and sealed with no orphan tail. Its 50,921 terminal
identities remained the same three accepted metrics-revision messages; no completion or gap
was added for them.

## Run-7 receipt and blocker

Run 7 is the final receipt of this invocation:

```text
run_id=902a6fdb3d405b8db18e05564399f38ffddd7032dfaa2df707ef2d9e8d30e15b
started_at=2026-08-31T17:47:26.181191+00:00
ended_at=2026-08-31T19:08:55.083420+00:00
stop_reason=partial
predecessor=1cf814d73aed5ab2d7aadccd8e57302339a0e78df40504d40e2d0dbbf457ee62
attempt_delta=89140
completion_delta=19035
gap_delta=0
byte_delta=4095285686
network_calls=89140
error_count=51275
receipt_sha256=8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab
receipt_bytes=5525
prefix_digest=43877e91aebdf85991f52055025ad23a68265c5dd95d1aadca8e1f1f034da8b8
semantic_state_digest=7af5edf8e860d1f7186213490ed4d45561f17b174638b2048134763a49faf315
attempt_hi=1632378
completion_hi=685642
sidecar_hi=736347
charge_hi=569
transition_hi=1707
run_hi=7
seal_hi=6
```

The run-7 attempt classification was:

```text
ok / HTTP 200=37849
terminal / HTTP 200=51275
rate_limit / HTTP 429=13
transport / status NULL=3
```

Terminal messages were:

```text
listed byte size does not match=12576
stream exceeded the listed byte ceiling=38344
streamed digest does not match the required checksum=1
ZIP uncompressed expansion exceeds the accepted ceiling=354
```

The first three counts are the unchanged accepted revision set. The 354 ZIP-expansion
outcomes are new and unresolved. The 13 rate-limit and three transport attempts are recorded
in the receipt; no later invocation was made to establish another retry outcome.

Run 7 added 18,465 Binance completions and 570 Coinalyze completions. It added 18,815
Binance sidecars. The Coinalyze ledger contains 569 `checksum_verified` HTTP-200 charges
totalling 20,126,995 charged bytes, 1,707 charge transitions, and zero open charges. No new
gap was published.

## Physical and state reconciliation

Read-only path/type/size/SHA-256 checks over run-7 sequence ranges reported:

```text
completion rows=19035
unique content paths=19035
content bytes=4095285686
content defects=0
sidecar rows=18815
unique sidecar paths=18815
sidecar bytes=1720240
sidecar defects=0
```

The final durable totals are 737119 plan rows, 1632378 attempts, 685642 completions,
736347 sidecars, 202 terminal gaps, seven runs, seven publications, seven seals, 569
Coinalyze charges, 1707 charge transitions, zero open charges, and zero unfinished runs.
The final seal head is run-7 receipt `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`.

Run-7 capacity remained sufficient:

```text
pre available=198575132672 needed=179293006553
post available=189985681408 needed=177575116300
stable requirement=139577980018
operating reserve=37997136282
```

No private partial or terminal artifact was present. No key value or key length was emitted;
the protected key had zero byte occurrences in the state database/WAL/SHM, run receipts, or
this record. Persisted URLs and facts are redacted according to the source contract.

## Coverage state at stop

The unresolved plan after run 7 remains:

| Provider / family | Complete | Gap | Pending |
|---|---:|---:|---:|
| Binance `daily/bookDepth` | 1 | 0 | 2,234 |
| Binance `daily/bookTicker` | 4 | 0 | 905 |
| Binance `daily/indexPriceKlines` | 12,266 | 0 | 0 |
| Binance `daily/klines` | 13,710 | 0 | 0 |
| Binance `daily/markPriceKlines` | 14,096 | 0 | 0 |
| Binance `daily/metrics` | 541,330 | 0 | 50,921 |
| Binance `daily/premiumIndexKlines` | 11,439 | 0 | 0 |
| Binance `monthly/fundingRate` | 21,035 | 0 | 0 |
| Binance `monthly/indexPriceKlines` | 21,721 | 0 | 0 |
| Binance `monthly/klines` | 21,932 | 0 | 0 |
| Binance `monthly/markPriceKlines` | 22,286 | 0 | 0 |
| Binance `monthly/premiumIndexKlines` | 5,252 | 0 | 15,680 |
| Coinalyze inventory | 1 | 0 | 0 |
| Coinalyze liquidation | 569 | 0 | 0 |
| Coinalyze unsupported mapping | 0 | 202 | 0 |

The ZIP-expansion identities remain unresolved and are not accepted as coverage. No source,
ADR, or implementation change was made to address them.

## Stop boundary

The one authorized invocation is complete, and the new ZIP uncompressed-expansion ceiling
message blocks further campaign work. Hermes stops after this one evidence publication. The
reviewer will disposition the ceiling and, if desired, issue a future authorization. Gate 2
remains `IN_PROGRESS`; no later gate or next-ticket work is authorized.
