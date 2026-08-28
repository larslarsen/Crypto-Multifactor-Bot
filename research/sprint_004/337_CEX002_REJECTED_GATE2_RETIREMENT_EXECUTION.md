# CEX-002 Rejected Gate-2 Retirement Execution

- **Ticket:** CEX-002
- **Review:** 336
- **Repository commit:** `66e95a28977a3e6b334d2f34ac7c72cfc8f3c49d`
- **Tool SHA-256:** `66faa5c6c411d433ff7d4d3e36815d9677c1974c08829f361535dd3b41503ef6`
- **Module SHA-256:** `468bcbe3640e2e1a4f112f081b0a3a86081d8f6b877f96950156d79948cd154e`
- **Authority SHA-256:** `8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1`
- **Plan receipt SHA-256:** `fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3`
- **Command exit:** `0`
- **UTC start:** `2026-08-28T02:34:22.875764846Z`
- **UTC end:** `2026-08-28T02:34:30.513845937Z`
- **Elapsed:** `7.638s`

The exact authorized command was run once, without an external timeout or separate
inspection:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/research/retire_binance_usdm_harmonic_gate2.py retire --confirm fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3
```

Captured bounded stdout/stderr:

```text
{
  "after_inventory_digest": "5d03cf25826a2e90f2552a98ba9d53539a8fb8bc0aed26d195e102ca41dc83dc",
  "authority_sha256": "8c658629a8adcb4eecd46b84509221f83bb053dc916a83f546e4de8e14a4ebc1",
  "before_inventory_digest": "5d03cf25826a2e90f2552a98ba9d53539a8fb8bc0aed26d195e102ca41dc83dc",
  "destination": "/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2_retired/fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3",
  "ended_at": "2026-08-28T02:34:30.482724+00:00",
  "entry_count": 10,
  "lock_held": true,
  "parent_fsync": true,
  "plan_identity": "911ed811ba5a04008fa787ee88eb4b38a4df3718b169b5c5d914e9ac2f30f578",
  "plan_receipt_sha256": "fb80b372080c7c59a14ecc43d89b1b2438e2b952d2ca571a10f372050f6d3bd3",
  "regular_file_bytes": 742380087,
  "rename_noreplace": true,
  "schema_version": "cex002_gate2_retirement_receipt_v1",
  "source": "/home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2",
  "started_at": "2026-08-28T02:34:23.024647+00:00",
  "syncfs": true,
  "ticket": "CEX-002"
}

TIMING start=2026-08-28T02:34:22.875764846Z end=2026-08-28T02:34:30.513845937Z elapsed_seconds=7.638 exit=0
```

No second retirement, inspection, cleanup, reverse rename, or manual data operation followed.
This preserves rejected pre-network Gate-2 state and does not accept Gate 2 or authorize
corrected planning or acquisition.
