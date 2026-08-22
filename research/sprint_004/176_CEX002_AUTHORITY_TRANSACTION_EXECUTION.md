# CEX-002 Authority Transaction Execution

Date: 2026-08-21
Actor: Jr Dev - Hermes
Ticket: CEX-002

## Scope

Review 175 authorized exactly one local source-authority transaction:

```bash
timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python scripts/research/qualify_binance_usdm_harmonic_sources.py \
    --store-root data/cex002_qualify \
    --report-path research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
    --apply-reviewed-v4-source-correction-only
```

No `.env` file was loaded. No network permission was requested. No retry, recovery,
ordinary qualification, report write, sample acquisition, reservation reconciliation,
Gate 1 acceptance, Gate 2, bulk acquisition, normalization, catalog publication,
Nautilus work, Harmonic Trader work, payoff analysis, PAPER, LIVE, paid source, reduced
scope, or next-ticket work was run.

## Preproof

`git rev-parse HEAD origin/main`

```text
cbfbca82571191921dd686146ea02393b18643c6
cbfbca82571191921dd686146ea02393b18643c6
```

Accepted source hashes:

```text
068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e  src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py
473185ca946dcc37d506d8891e8f955708ff80c976a586967762c1294956d28f  scripts/research/qualify_binance_usdm_harmonic_sources.py
4cf2b786e95723f933a293b8bfdfb59236cfad8490ec7afcbadecc347e543ff0  tests/acquisition/test_binance_usdm_harmonic_qualification.py
```

`rg -c '^def test_' tests/acquisition/test_binance_usdm_harmonic_qualification.py`

```text
305
```

`ps -C python3 -o pid=,args=` exited 1 with no output.

The two destination evidence paths were absent:

```text
data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json
data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json
```

Pinned artifact sizes and hashes before invocation:

```text
13944475 / 53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
425308 / 8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc  data/cex002_qualify/cex002_sample_plan_lock.json
25223 / 2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c  data/cex002_qualify/cex002_amendment_ledger.json
777 / 47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
51124 / 02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
13737 / a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
33206753 / d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
98940 / 19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8  data/cex002_qualify/cex002_official_contract_metadata.json
11292635 / 64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Pre-invocation deterministic tree identities:

```text
8577f80bc794dab4fe7b98aa8566118aa4ccac7a05c603aed2914b17ec5889f1 files=270 bytes=1016247871 path=data/cex002_qualify/raw
d97420a075224d6639e894a5c98e848dbb4abccc581f0d6cf5fa356054b470bf files=41045 bytes=5158280401 path=data/cex002_qualify/list_cache
03ea6b726d4518f541ada5b9889cff42955a0eb2ab7e804711649da297602da2 files=16 bytes=14009673 path=data/cex002_qualify/fapi_cache
8499543d5220f1cb71b43d78e73c67a87147d775f95090a485506bf6e0d30e87 files=5 bytes=5387946 path=data/cex002_qualify/fapi_snapshots
5bf18914908474688bdfeea6563e334f8742b7406ee5c2b5b781823865440eec files=7 bytes=3144369 path=data/cex002_qualify/coinalyze_cache
ff62cf6b3beb2eb877fbeff96ec99517ab18f753d307ec9b93ccb82dc22ec77b files=3 bytes=1090593382 path=data/cex002_qualify/evidence/prior_reports
a4dfa97d0cd15c67a38a55f1fde62962b67a0762a9c17ad49c4b8e656be34e67 files=2 bytes=22580891 path=data/cex002_qualify/evidence/manifests
7336105675428dd0226e11bf8d44b7c4211d98e2cd421185261c540ebaba6a16 files=1 bytes=381855 path=data/cex002_qualify/evidence/locks
```

## Transaction result

The single authorized invocation exited zero:

```text
reviewed_v4_source_correction: {"accepted_code_config_digest": "8613b4f6f42ad32c09099362fb0ea817a2f2a660bfd3b5dc322ebea0fd207e4e", "allowance_bytes": 268435456, "charge_count": 82, "charged_bytes": 1049324, "download_authorized": false, "executed": true, "executing_code_config_digest": "da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258", "legacy_ledger_sha256": "47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6", "note": "only the executing source identity advanced; the reviewed plan, accounting, history, and lineage are unchanged, and no sample was acquired", "plan_digest": "2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef", "plan_shape": {"aliases": 10, "blocked": 0, "entries": 106, "new_bytes": 1049324, "new_objects": 84, "retained_bytes": 44642, "retained_objects": 12}, "plan_version": 4, "prior_ledger_evidence_path": "data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json", "prior_lock_evidence_path": "data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json", "reservation_count": 2, "reservations_reconciled": 0, "retained_objects_reproved": 15, "samples_acquired": 0, "source_identity": {"alias_table_sha256": "e9837ee2ac0711e41981e27979532be5095d61f04fb82442919c9f301f5998f8", "code_config_digest": "da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258", "delivery_table_sha256": "678d07e0679b0e116a372a333c3c33f74f5e421dadba393cb9516e56ae8b9a01", "module_sha256": "068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e", "reviewed_authority_table_version": "review137-v1"}, "state": "source_identity_advanced", "transaction": "cex002_reviewed_v4_source_correction"}
transaction_status=0
```

## After-proof

The receipt reports:

- `transaction=cex002_reviewed_v4_source_correction`;
- `executed=true`;
- `state=source_identity_advanced`;
- plan version `4`;
- plan digest `2fb0e47a3666f0e87b35dd7fdd6ea26aa352e34acf8dfd5debf590409aecbbef`;
- 82 charges;
- 845,471 settled transfer bytes;
- two reservations;
- 203,853 planned reservation bytes;
- 1,049,324 charged bytes;
- 268,435,456-byte allowance;
- zero acquired samples;
- zero reconciled reservations;
- `download_authorized=false`.

The prior lock and amendment ledger now exist at the required content addresses and
rehash to their filenames:

```text
425308 / 8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc  data/cex002_qualify/evidence/locks/sha256/8fda3c7db11173dafa122114667622f501b62ecf05f12cdf796897d5af0942bc.json
25223 / 2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c  data/cex002_qualify/evidence/ledgers/sha256/2a4c4db6e14350d6814b6f72a3caa1357659cd064a13fd2edeb84a2896223c8c.json
```

The live lock and amendment ledger advanced to new hashes:

```text
426276 / 522271238e38a3652f9521b236981544782e02459450703f21e9ef344d476fa6  data/cex002_qualify/cex002_sample_plan_lock.json
25797 / 832228fd2b4b9394e205a69441281ddbfccc92c227144c5c0c2b8181e164e488  data/cex002_qualify/cex002_amendment_ledger.json
```

The live amendment ledger binds plan version 4, the same plan digest, 82 charges,
845,471 transferred bytes, 1,049,324 charged bytes, two reservations, 203,853 planned
reservation bytes, the 268,435,456-byte allowance, and `download_authorized=false`.

Before correction, the prior lock and prior amendment ledger each carried one source
receipt. After correction, the live lock and live amendment ledger each carry two source
receipts; the new appended receipt has code/config digest
`da33197203e0c9651dc84f42e6e2ce26867339cebe4c68286a00639046c08258` and production
module hash `068763e2359abf4fc4fe4b7e7fdea95495db5c22bf362d468fec4056775ecb7e`.

Structured diffs with the receipt fields removed show:

- the lock differs only by `inputs.code_config_digest` plus the source-correction evidence
  path metadata;
- the ledger differs only by the receipt-derived `integrity.state_sha256`.

The report, legacy ledger, sample plan, retry journal, listing checkpoint, official
metadata, and accepted manifest detail remain byte-identical:

```text
53f8f93379cb55d66b6de062f1a6a85f4c9dd318f5b41cc047bff2f5feeaaf51  research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json
47341a9ca2c60caf73485fb9bac40c6526cb35a13471e4545cd9cdcee6e227f6  data/cex002_qualify/cex002_budget_ledger.json
02f8e435b18643586ff6e778bfd85cffd0136457b5dcf8466f5a24c35e2f2d18  data/cex002_qualify/cex002_sample_plan.json
a9c77e465972a5ab59960519f5e4fab12a63c4767747eaee22e4d12d429b0a24  data/cex002_qualify/cex002_retry_journal.json
d584e22aaaa9414b06dbe13bc24dda0b01ed48e37bdf66f5b42f90865959bf9a  data/cex002_qualify/cex002_listing_checkpoint.json
19bfa0e3314a5e2204bca68fae8dcb4583d58f886792fe615aeb4f973916f2b8  data/cex002_qualify/cex002_official_contract_metadata.json
64d0f74b8e4696c98d0f96423185fd961aba6c63348d12425e3ec364b888f113  data/cex002_qualify/evidence/manifests/sha256/d6c1fac650aaf16d88750da2a40d837f543d0c5fc88c73d463753a576d5bdd17.jsonl.gz
```

Post-invocation deterministic tree identities:

```text
8577f80bc794dab4fe7b98aa8566118aa4ccac7a05c603aed2914b17ec5889f1 files=270 bytes=1016247871 path=data/cex002_qualify/raw
d97420a075224d6639e894a5c98e848dbb4abccc581f0d6cf5fa356054b470bf files=41045 bytes=5158280401 path=data/cex002_qualify/list_cache
03ea6b726d4518f541ada5b9889cff42955a0eb2ab7e804711649da297602da2 files=16 bytes=14009673 path=data/cex002_qualify/fapi_cache
8499543d5220f1cb71b43d78e73c67a87147d775f95090a485506bf6e0d30e87 files=5 bytes=5387946 path=data/cex002_qualify/fapi_snapshots
5bf18914908474688bdfeea6563e334f8742b7406ee5c2b5b781823865440eec files=7 bytes=3144369 path=data/cex002_qualify/coinalyze_cache
ff62cf6b3beb2eb877fbeff96ec99517ab18f753d307ec9b93ccb82dc22ec77b files=3 bytes=1090593382 path=data/cex002_qualify/evidence/prior_reports
a4dfa97d0cd15c67a38a55f1fde62962b67a0762a9c17ad49c4b8e656be34e67 files=2 bytes=22580891 path=data/cex002_qualify/evidence/manifests
2bbeeaeaa1cb5b0d3b6913279e1cc65e1a9711cd0e9464b69309d14846e94af2 files=2 bytes=807163 path=data/cex002_qualify/evidence/locks
e64b9308f13f8165f6c8672059896982372a2c50cfe2ea1f6ffbfe151ff6a11d files=1 bytes=25223 path=data/cex002_qualify/evidence/ledgers
```

The first seven post-invocation tree identities match the pre-snapshot exactly. The
`evidence/locks` and `evidence/ledgers` tree identities changed only because the
transaction created the two required prior-evidence content-addressed files.

## Disposition

The one authorized local source-authority transaction exited zero and advanced only the
reviewed source identity. CEX-002 remains `IN_PROGRESS`; Gate 1 has not passed; next
ticket remains `NONE`.

Next required actor: Lead Quantitative Finance Researcher/Engineer - inspect record 176.
