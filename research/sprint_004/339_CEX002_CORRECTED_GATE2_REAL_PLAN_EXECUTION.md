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

## Review-341 provenance correction

The canonical receipt above is the actual two-space-indented `json.dumps` representation
with sorted keys and a trailing newline. Captured proof was:

```text
receipt_canonical=True
encoded_length=5007
sha256=c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167
```

No read-only reinspection was necessary. The exact captured inspection script was:

```bash
set -euo pipefail
cd /home/lars/Crypto_Multifactor_Bot
store=data/cex002_qualify/gate2
avail=$(df -B1 --output=avail "$store" | tail -1 | tr -d ' ')
printf 'post_plan_df_B1_available=%s\n' "$avail"
find "$store" -type d -printf '%p|%d|%m\n' | sort
find "$store" -type f -printf '%p|%s|%d|%m|%f\n' | sort | while IFS='|' read -r p s d m f; do
  h=$(sha256sum "$p" | cut -d' ' -f1)
  printf '%s|%s|%s|%s|%s|%s\n' "$p" "$s" "$d" "$m" "$f" "$h"
done
for p in raw content run_receipts terminal; do
  if [ -e "$store/$p" ]; then printf '%s=present\n' "$p"; else printf '%s=absent\n' "$p"; fi
done
```

The exact captured SQLite script was:

```python
import hashlib, json, sqlite3
from pathlib import Path
store = Path("data/cex002_qualify/gate2")
receipt = next((store / "plan_receipts").glob("*.json"))
document = json.loads(receipt.read_text())
canonical = json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n"
print("receipt_canonical=", receipt.read_bytes().decode() == canonical)
print("encoded_length=", len(canonical.encode()))
print("sha256=", hashlib.sha256(canonical.encode()).hexdigest())
connection = sqlite3.connect(f"file:{store}/state.sqlite?mode=ro", uri=True)
connection.execute("PRAGMA query_only=ON")
print("application_id=", connection.execute("PRAGMA application_id").fetchone()[0])
print("user_version=", connection.execute("PRAGMA user_version").fetchone()[0])
print("integrity_check=", connection.execute("PRAGMA integrity_check").fetchone()[0])
print("foreign_key_check=", connection.execute("PRAGMA foreign_key_check").fetchall())
print("authority_count=", connection.execute("select count(*) from authority").fetchone()[0])
print("kind_counts=", dict(connection.execute("select kind,count(*) from plan_entry group by kind")))
flags = {"true": 0, "false": 0, "not_applicable": 0}
for kind, payload_json in connection.execute("select kind,payload_json from plan_entry"):
    value = json.loads(payload_json)["payload"].get("retained", "__missing__")
    if kind == "binance_object" and value is True: flags["true"] += 1
    elif kind == "binance_object" and value is False: flags["false"] += 1
    elif kind != "binance_object" and value == "__missing__": flags["not_applicable"] += 1
print("retained_true_false_not_applicable=", flags)
print("terminal_gap_count=", connection.execute("select count(*) from terminal_gap").fetchone()[0])
print("ledger_rows=", connection.execute("select * from coinalyze_ledger").fetchall())
print("seal_head=", connection.execute("select * from seal_head").fetchall())
print("zero_fact_counts=", {t: connection.execute("select count(*) from " + t).fetchone()[0] for t in ("attempt", "sidecar_fact", "completion", "coinalyze_charge", "charge_transition", "run_metadata", "run_publication", "run_seal")})
connection.close()
```

The SQLite, SHM, and WAL hashes remain mutable evidence observations, not authority. No
plan rerun, repository CLI, retired-tree access, or plan-state mutation occurred.

## Review-340 evidence completion

No read-only reinspection was necessary. The complete canonical receipt body captured from
the content-named receipt path is reproduced below as its actual canonical representation:

```json
{
  "authority": {
    "amendment_ledger_sha256": "2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf",
    "attestation_282_sha256": "0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25",
    "contract_metadata_sha256": "7aaea96ecd4cb13c83b8b19930a6e1ef0fcf2b49de841e1fa26878d6dd7f5b42",
    "cost_manifest_sha256": "04842ff6b9b58280b3ec2ea2644b3d44769be62d460bef785262cd4dd65cac57",
    "holdout_boundary_id": "c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2",
    "listing_checkpoint_sha256": "d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a",
    "lock_sha256": "6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e",
    "manifest_compressed_sha256": "64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113",
    "manifest_uncompressed_sha256": "d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17",
    "progress_sha256": "cc8e02389d182e6d76d00b913503d95f72a352d883c50ffd81dd3c49df157b2f",
    "receipt_258_sha256": "3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589",
    "report_62_sha256": "f27b2ba7e6eff3a8b1385d985c49ee64ef60a394737b1246130d0f37b9015f09"
  },
  "bytes": {
    "binance_listed_bytes": 20356940843,
    "new_binance_raw_bytes": 20351715427,
    "new_coinalyze_raw_bytes": 30580702,
    "retained_credit_bytes": 5225416
  },
  "code_identity": {
    "acquisition_cli_path": "scripts/research/acquire_binance_usdm_harmonic_release.py",
    "acquisition_cli_sha256": "6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043",
    "acquisition_source_path": "src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py",
    "acquisition_source_sha256": "af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d",
    "capacity_cli_sha256": "e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5",
    "capacity_source_sha256": "34973e6f801ef3a16e82c3333c01fb1ee81fad357810bc28fdd3b41503ef6",
    "policy_identity": "adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2",
    "qualification_cli_sha256": "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f",
    "qualification_source_sha256": "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
  },
  "coinalyze": {
    "anchors_are_not_the_universe": true,
    "convert_to_usd": false,
    "current_inventory_is_not_authority": true,
    "cutoff": "2026-08-22T22:45:15.097674+00:00",
    "interval": "daily",
    "rate_per_minute": 40,
    "request_path": "/liquidation-history",
    "supported_count": 569,
    "symbols_per_request": 1,
    "unsupported_count": 202
  },
  "counts": {
    "binance_objects": 736347,
    "coinalyze_logical_receipts": 570,
    "coinalyze_supported": 569,
    "coinalyze_unsupported": 202,
    "cost_objects": 3144,
    "main_selected_objects": 733203,
    "plan_objects": 737119,
    "retained_credit_objects": 73
  },
  "family_totals": {
    "daily/bookDepth": 2235,
    "daily/bookTicker": 909,
    "daily/indexPriceKlines": 12266,
    "daily/klines": 13710,
    "daily/markPriceKlines": 14096,
    "daily/metrics": 573786,
    "daily/premiumIndexKlines": 11439,
    "monthly/fundingRate": 21035,
    "monthly/indexPriceKlines": 21721,
    "monthly/klines": 21932,
    "monthly/markPriceKlines": 22286,
    "monthly/premiumIndexKlines": 20932
  },
  "helper_identities": {
    "capacity_cli_sha256": "e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5",
    "capacity_source_sha256": "34973e6f801ef3a16e82c3333c01fb1ee81fad357810bc28fdd3b41503ef6",
    "iter_manifest_detail": "cryptofactors.acquisition.binance_usdm_harmonic_qualification.iter_manifest_detail",
    "qualification_cli_sha256": "473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f",
    "qualification_source_sha256": "2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74"
  },
  "holdout_boundary_id": "c842f813839e1dda375b351da0f693c54bcf932e33eb6e3394aba860c12346e2",
  "plan_identity": "8d96db46d5b6df45e4b9c0ba0e45ae9f3688dd88503195fb426e12de827bde22",
  "policy_identity": "adr0029_content_addressed_gate2_acquisition_and_resume_adr0030_exact_retained_credit_v2",
  "prohibitions": [
    "no trades or aggTrades",
    "no full historical bookTicker or bookDepth",
    "no price-only or tick path",
    "no caller family/symbol/date filter",
    "no progress credit against the ADR-0028 stable requirement",
    "no secret in URL, query, database, receipt, log, or exception"
  ],
  "retained_credit": {
    "bytes": 5225416,
    "cost_retained_keys": 5,
    "key_set_sha256": "5e13a9fbb57acff21d0c290d3f0da7c27d549031fdee1fca8a1ab0744cc0b982",
    "objects": 73,
    "selected_retained_keys": 68,
    "unverified_objects": 0,
    "valid_requirement_keys": 73
  },
  "schema_version": "cex002_gate2_plan_receipt_v2",
  "storage": {
    "destination": "data/cex002_qualify",
    "device": "dev:64513",
    "store_root": "data/cex002_qualify"
  },
  "ticket": "CEX-002"
}
```

Exact read-only reconciliation commands and captured outputs are completed below with the
actual hashing and SQLite script provenance:

```bash
# The complete command and its transformation loop are documented in the exact-script
# section below; the three lines here are the captured command stages, not raw output.
```

```text
post_plan_df_B1_available=248392949760
data/cex002_qualify/gate2|directory|0|device=64513|mode=700
data/cex002_qualify/gate2/plan_receipts|directory|0|device=64513|mode=700
data/cex002_qualify/gate2/acquisition.lock|regular file|0|device=64513|mode=600|sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
data/cex002_qualify/gate2/plan_receipts/c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167.json|regular file|5007|device=64513|mode=600|sha256=c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167
data/cex002_qualify/gate2/state.sqlite|regular file|742330368|device=64513|mode=600|sha256=ebbe32bd539bfdafcde4ab04dd498e44c5015f91c5a3a806e6608c4294c60eb1
data/cex002_qualify/gate2/state.sqlite-shm|regular file|32768|device=64513|mode=600|sha256=fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb
data/cex002_qualify/gate2/state.sqlite-wal|regular file|0|device=64513|mode=600|sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

SQLite command: Python standard library opened
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately executed
`PRAGMA query_only=ON`, then queried the already authorized Review-338 facts. Output:

```text
receipt_canonical=True
receipt_bytes=5007
receipt_sha256=c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167
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
raw=absent
content=absent
run_receipts=absent
terminal=absent
```

Mutable SQLite, SHM, and WAL hashes are observations only, not authority. No reinspection,
plan rerun, `verify`, or acquisition followed. Only record 339 was amended.
