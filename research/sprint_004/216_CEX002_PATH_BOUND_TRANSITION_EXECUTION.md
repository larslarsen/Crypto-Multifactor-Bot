# CEX-002 Path-Bound Transition Execution

Date: 2026-08-22
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 215 authorized Hermes to run exactly one isolated path-bound transition command
from the repository root. Because the first command exited zero with `executed=true`,
Hermes ran the identical command exactly once more to prove idempotence. Both commands
exited zero.

No ordinary qualification, sizing source change or retry, acquisition, normalization,
catalog publication, NautilusTrader work, Harmonic Trader work, payoff analysis, PAPER,
LIVE, paid-source, reduced-scope, test, lint, network, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
4890083ab1a5b8dfa439d7625f0347e6dde945d2
4890083ab1a5b8dfa439d7625f0347e6dde945d2
```

Historical artifact identities before execution:

```text
522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6  data/cex002_qualify/cex002_sample_plan_lock.json
47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f  data/cex002_qualify/cex002_official_contract_metadata.json
259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0  data/cex002_qualify/cex002_amendment_ledger.json
cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff  data/cex002_qualify/cex002_qualification_progress.json
a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4  data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Historical artifact sizes before execution:

```text
426276 data/cex002_qualify/cex002_sample_plan_lock.json
777 data/cex002_qualify/cex002_budget_ledger.json
33206753 data/cex002_qualify/cex002_listing_checkpoint.json
99357 data/cex002_qualify/cex002_official_contract_metadata.json
26103 data/cex002_qualify/cex002_amendment_ledger.json
487815 data/cex002_qualify/cex002_qualification_progress.json
13737 data/cex002_qualify/cex002_retry_journal.json
51124 data/cex002_qualify/cex002_sample_plan.json
13559766 research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
11294610 data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

The four exact prior-evidence destinations were absent:

```text
absent data/cex002_qualify/evidence/prior_reports/sha256/bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227.json
absent data/cex002_qualify/evidence/checkpoints/sha256/cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff.json
absent data/cex002_qualify/evidence/locks/sha256/522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6.json
absent data/cex002_qualify/evidence/ledgers/sha256/259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0.json
```

Accepted transition path identities:

```text
f9a1bc89c63b22c974d020044ea8732939358efae00b42f2141bfd0eee34e5e5  src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py
ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd  scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py
60b018f05e5d96e0863c529ca6670e6563c9c3cead9539b30dbf381803ab76ff  tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py
```

## Command evidence

### C1 - isolated transition

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py --store-root data/cex002_qualify --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Result:

```text
executed=true
state=source_identity_advanced
final.lock_sha256=6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e
final.amendment_ledger_sha256=2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf
final.code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb
final.source_receipts=3
work.samples_acquired=0
work.network_requests=0
work.credentials_read=0
elapsed_seconds=1
exit_status=0
```

Status output:

```text
transition applied: code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb source_receipts=3 samples_acquired=0
note: this transition authorizes no acquisition and accepts no gate
```

### C2 - identical idempotence recheck

Before C2, Hermes wrote a temporary store-file hash manifest outside the repository:

```text
41369 /tmp/cex002_transition_before_second.sha256
2709b4958c4c5c578565e5b7244f36988d03106b00f6e6789403ee4f14041123  /tmp/cex002_transition_before_second.sha256
```

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py --store-root data/cex002_qualify --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json --manifest-detail-path data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
```

Result:

```text
executed=false
state=source_identity_advanced
final.lock_sha256=6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e
final.amendment_ledger_sha256=2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf
final.code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb
final.source_receipts=3
work.samples_acquired=0
work.network_requests=0
work.credentials_read=0
elapsed_seconds=1
exit_status=0
```

Status output:

```text
transition already complete: code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb source_receipts=3 samples_acquired=0
note: this transition authorizes no acquisition and accepts no gate
```

After C2, the store-file hash manifest was identical:

```text
41369 /tmp/cex002_transition_after_second.sha256
2709b4958c4c5c578565e5b7244f36988d03106b00f6e6789403ee4f14041123  /tmp/cex002_transition_after_second.sha256
store_manifest_cmp_status=0
```

## Post-execution proof

Preserved evidence paths:

```text
bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227  data/cex002_qualify/evidence/prior_reports/sha256/bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227.json
cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff  data/cex002_qualify/evidence/checkpoints/sha256/cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff.json
522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6  data/cex002_qualify/evidence/locks/sha256/522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6.json
259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0  data/cex002_qualify/evidence/ledgers/sha256/259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0.json
```

Preserved evidence sizes and final authority sizes:

```text
13559766 data/cex002_qualify/evidence/prior_reports/sha256/bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227.json
487815 data/cex002_qualify/evidence/checkpoints/sha256/cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff.json
426276 data/cex002_qualify/evidence/locks/sha256/522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6.json
26103 data/cex002_qualify/evidence/ledgers/sha256/259a1bfe274f402207dbd15e6e582fb4619bed62ddca5f606ea470755084b1b0.json
428097 data/cex002_qualify/cex002_sample_plan_lock.json
26677 data/cex002_qualify/cex002_amendment_ledger.json
```

Final live authority and immutable artifact identities:

```text
6cbd044adf4ace577ff8899b2825723e8c0ae99d1fe3c855f2783ce54d7b722e  data/cex002_qualify/cex002_sample_plan_lock.json
2d41fbf009d9803ca5bda05c3a11d75dafe505a1397756e5fafefeb2d1cb90bf  data/cex002_qualify/cex002_amendment_ledger.json
47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
e520f0f072730f566d027342ddc7e09f7b690ab80e76acbd40756759f13add1f  data/cex002_qualify/cex002_official_contract_metadata.json
cc35a5c2c1fd72904d0d6a899565a763c89a38bb1295275e589e4d92be67eaff  data/cex002_qualify/cex002_qualification_progress.json
a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
bf01f88976e2ac3d224e843f340de726f5c8c337ba56a50f9e3c6f75c4d6f227  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
576b3d7b03ff16fd492c5a9382e35f65e54d73ef3996c3a7fe5c6e6ba49b0fb4  data/cex002_qualify/evidence/manifests/sha256/1d21de4d68fb0dfd330dc480a0d27ddf2216c3b7d5e93b13ff70ea26230f968d.jsonl.gz
f9a1bc89c63b22c974d020044ea8732939358efae00b42f2141bfd0eee34e5e5  src/cryptofactors/acquisition/binance_usdm_harmonic_path_bound_transition.py
ada238d22560ddcaf834dff03d0da44c546856090e6133cf5afeb7be3d50aabd  scripts/research/apply_binance_usdm_harmonic_path_bound_transition.py
60b018f05e5d96e0863c529ca6670e6563c9c3cead9539b30dbf381803ab76ff  tests/acquisition/test_binance_usdm_harmonic_path_bound_transition.py
```

Target source identity:

```text
module_sha256=2f88ad6e7cfc531fefe3d9c7a9ddbc830741687e93c51450fc826062dffb2c74
code_config_digest=86ff0eb0ee5fa379855745aedb41bb8442b0a244a8c5a740665acc735fba28fb
reviewed_authority_table_version=review137-v1
delivery_table_sha256=678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01
alias_table_sha256=e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8
```

## Git scope

Repository-control and whitespace validation:

```text
Repo control check: PASS
elapsed_seconds=0
exit_status=0
```

```text
elapsed_seconds=0
exit_status=0
```

Intended staged paths for this publication are exactly:

- `research/sprint_004/216_CEX002_PATH_BOUND_TRANSITION_EXECUTION.md`
- `docs/handoff/CURRENT_TASK.md`
- `tickets/CEX-002.md`

The live authority/evidence files are gitignored data outputs and are not staged. No
unrelated dirty path, DEX path, BitMEX path, catalog/ingest path, sizing receipt, or sizing
envelope is staged by this record.

## Disposition

The isolated path-bound identity transition executed once and then proved idempotent on
the second identical command. Gate 2 remains unaccepted. Next ticket remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 216.
