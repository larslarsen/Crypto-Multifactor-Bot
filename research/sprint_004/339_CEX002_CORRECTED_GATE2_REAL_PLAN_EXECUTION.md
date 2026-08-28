# CEX-002 Corrected Gate-2 Real Plan Execution

- Ticket: CEX-002
- Review: 338
- Repository commit: `4ec7e1c17ead7672d45d4ba140e53e05199906ff`
- Pre-execution `df -B1 data/cex002_qualify`: `249268436992` available bytes
- Plan start: `2026-08-28T02:49:42.094862151Z`
- Plan end: `2026-08-28T02:52:33.419731586Z`
- Elapsed: `171.325s`
- Exit: `0`

The exact authorized command ran once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=60s 2h \
  .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
  plan --store-root data/cex002_qualify
```

Captured output:

```text
command=plan exit=0 stop=ok
TIMING start=2026-08-28T02:49:42.094862151Z end=2026-08-28T02:52:33.419731586Z elapsed_seconds=171.325 exit=0
```

## Receipt and reconciliation

Receipt path:
`data/cex002_qualify/gate2/plan_receipts/c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167.json`

Receipt bytes: `5007`; device: `64513`; mode: `600`; canonical: `True`; SHA-256:
`c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167`.

The complete canonical receipt was read verbatim from that path. Its key facts were:

```text
schema=cex002_gate2_plan_receipt_v2
policy=adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2
plan_identity=8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22
rejected_plan_identity_diff=True
retained_credit={"bytes":5225416,"cost_retained_keys":5,"key_set_sha256":"5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982","objects":73,"selected_retained_keys":68,"unverified_objects":0,"valid_requirement_keys":73}
counts={"binance_objects":736347,"coinalyze_logical_receipts":570,"coinalyze_supported":569,"coinalyze_unsupported":202,"cost_objects":3144,"main_selected_objects":733203,"plan_objects":737119,"retained_credit_objects":73}
bytes={"binance_listed_bytes":20356940843,"new_binance_raw_bytes":20351715427,"new_coinalyze_raw_bytes":30580702,"retained_credit_bytes":5225416}
```

Read-only SQLite reconciliation used URI
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro` followed immediately by
`PRAGMA query_only=ON`; it did not invoke the acquisition module or CLI:

```text
application_id=1127368498
user_version=7
integrity_check=ok
foreign_key_check=[]
authority_count=1
kind_counts={'binance_object': 736347, 'coinalyze_inventory': 1, 'coinalyze_liquidation': 569, 'coinalyze_unsupported_gap': 202}
retained_true_false_not_applicable={'true': 73, 'false': 736274, 'not_applicable': 772}
terminal_gap_count=202
ledger_rows=[(1, 0)]
seal_head=[(1, 'c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167', 'data/cex002_qualify/gate2/plan_receipts/c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167.json', '2431d5373de5b7ecfa7cf950c33c0577f6950693a0a644dd2895049f56303cf8', 0, 0, 0, 0, 0, 0, 0, None)]
zero_fact_counts={'attempt': 0, 'sidecar_fact': 0, 'completion': 0, 'coinalyze_charge': 0, 'charge_transition': 0, 'run_metadata': 0, 'run_publication': 0, 'run_seal': 0}
```

Post-plan `df -B1 data/cex002_qualify` availability was `248392949760` bytes. The active
tree contained only the plan receipt, `state.sqlite`, its 32,768-byte SHM file, empty WAL,
and empty acquisition lock, all on device `64513`; the regular file sizes were 5,007,
742,330,368, 32,768, 0, and 0 bytes respectively. The receipt and state file were mode
600. No raw, content, run-receipt, or terminal directory was present.

No acquisition, verification, planning rerun, or later-gate command followed. The new plan
is planning evidence only; Gate 2 remains `IN_PROGRESS`.
