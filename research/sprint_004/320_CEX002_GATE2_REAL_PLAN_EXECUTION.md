# CEX-002 Gate-2 Real Offline Plan Execution

- **Date:** 2026-08-27 UTC
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Gate 2:** in progress; acquisition has not started
- **Next ticket:** `NONE`

## Preproof and capacity

Review 319 preproof passed without mutation: synchronized `HEAD == origin/main`, review
319 and commit `4acbdbe72900cf98880b67d276bc1ac9ec7ee8a8` in ancestry, accepted source/CLI/
test/record-318 hashes, clean governed paths, empty index, absent `data/cex002_qualify/gate2`,
required authorities/receipt/attestation/report present, and 650,668 checked files on device
64513. The pre-execution command was:

```text
df -B1 data/cex002_qualify
```

It reported available `246961917952` bytes on `/dev/mapper/ubuntu--vg-ubuntu--lv`, device
64513. No network or secret was used.

## Authorized plan

The exact authorized command ran once from the repository root:

```text
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 2h .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py plan --store-root data/cex002_qualify
```

Result: exit `0`; stdout/stderr output was exactly:

```text
command=plan exit=0 stop=ok
```

The execution wrapper did not capture UTC start/end timestamps or elapsed seconds; this
record leaves those values unavailable rather than inventing them. The plan closed normally.
No `acquire`, `verify`, network access, or data download was performed.

## Read-only reconciliation

Plan receipt:

- path: `data/cex002_qualify/gate2/plan_receipts/fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3.json`
- schema: `cex002_gate2_plan_receipt_v1`
- SHA-256: `fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`
- bytes: `4663`
- plan identity: `911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578`
- storage device: `dev:64513`

Receipt counts are `736347` Binance objects, `569` supported Coinalyze rows, `202`
unsupported gaps, `570` Coinalyze logical receipts, `3144` cost objects, `733203` main
selected objects, `73` retained-credit objects, and `737119` plan objects. Family totals
and all authority/code/helper identities are preserved in the canonical receipt above.
The receipt prohibitions exclude trades/aggTrades, full historical books, price-only/tick
paths, caller filters, stable-requirement credit, and secrets in URL/query/database/receipt/
log/exception.

The read-only SQLite inspection used:

```text
sqlite3 URI: file:data/cex002_qualify/gate2/state.sqlite?mode=ro
PRAGMA query_only=ON
```

Results:

- database bytes `742342656`, SHA-256
  `d6a0a18f7bf1c5ccfc62376f0c24257bda640165a27c57aaae9fd2fded5142a4`, device `64513`;
- `application_id=1127368498`, `user_version=7`, `integrity_check=ok`, foreign-key check `[]`;
- authority rows `1`; plan rows `737119`; kinds: `binance_object=736347`,
  `coinalyze_inventory=1`, `coinalyze_liquidation=569`,
  `coinalyze_unsupported_gap=202`; terminal gaps `202`;
- Coinalyze ledger `charged=0`; seal head receipt equals the plan receipt,
  `predecessor_sha256=NULL`, and `attempt_hi=completion_hi=sidecar_hi=charge_hi=
  transition_hi=run_hi=seal_hi=0`;
- rows in `attempt`, `sidecar_fact`, `completion`, `coinalyze_charge`, `charge_transition`,
  `run_metadata`, `run_publication`, and `run_seal`: all `0`;
- inventory contains only zero-byte `acquisition.lock`, the 4,663-byte plan receipt, the
  SQLite database, and SQLite sidecar files; no content payload, run receipt/link, terminal
  manifest, or temporary partial file exists.

All inspected Gate-2 files are on device 64513. The plan receipt is immutable content-named;
the SQLite hash is evidence only. The plan transaction installed the plan, typed gaps, zero
charge ledger, and zero-watermark head without an acquisition attempt. Gate 2 remains
unaccepted and acquisition remains unauthorized.
