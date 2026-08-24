# CEX-002 V3 Blocked Measurement and Capacity Attestation Architecture

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** v3 execution accepted; Gate 2 blocked; ADR-0028 implementation authorized
- **Authorized actor:** Sr Dev - Sol High
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Execution acceptance

Record 277 and commit `aba5f5d` are accepted as faithful review-276 integration and
execution. The integrated production/test/CLI hashes match review 276, focused pytest and
Ruff exited 0, the first sizing run published 153 envelopes, and the second identical run
published zero and reused all 153. Receipt 258 is byte-identical across both runs.

Accepted receipt facts:

| Fact | Value |
|---|---:|
| Receipt SHA-256 | `3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589` |
| Receipt bytes | 39,727,059 |
| Stable requirement excluding reserve | 139,577,980,018 |
| Operating reserve | 29,690,701,415 |
| Total future storage | 169,268,681,433 |
| Post-publication available | 148,382,449,709 |
| Observed shortfall | 20,886,231,724 |
| Additional free space required under the dynamic reserve | 26,107,789,655 |

All six capacity components sum exactly to the total. The receipt binds the accepted
compressed and uncompressed manifest identities, 771 accepted membership identities, 11
required products, 736,347 physical raw objects, 291,255 projected normalized files, and
153 sizing envelopes. The 153 content-addressed files total 3,658,657 bytes; every file's
content matches its SHA-256 filename. The sorted `filename<TAB>byte_size` manifest has
SHA-256 `76e3a8324513a1b1e4cb8fcce853aade78f2fac29194cce06ccaebd0c3c100fa`.

Record 277 omits the review-requested command timestamps/wall times and sorted evidence
manifest. Those publication omissions are nonblocking because the committed receipt,
content-addressed evidence, exact command/result record, and Git scope independently
reconcile. The reviewer does not require another evidence-only handoff.

Receipt 258 is accepted as authoritative blocked measurement evidence. This does not
accept Gate 2 or authorize acquisition.

## Capacity finding

Free space continued to fall after receipt publication while the owner's unrelated
download was active. At reviewer inspection it was 147,508,445,184 bytes and the
conservative additional-free requirement had grown to about 26.97 GB. The owner should
plan to recover at least 30 GB after the download finishes, then run the reviewed capacity
attestation. No file deletion or movement is authorized here.

Read-only inventory found approximately 20.26 GB in `/home/lars/.cache`, 0.77 GB in
`/home/lars/.npm`, and user-controlled files in `Downloads`, including a 39.37 GB
`System Volume Information` directory and about 10.9 GB of older media. Cache alone is
insufficient under the dynamic reserve. The reviewer will not delete or move any of these
without the owner's explicit path-level authority.

## ADR-0028 implementation contract

Implement exactly three new paths:

1. `src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py`
2. `scripts/research/attest_binance_usdm_harmonic_capacity.py`
3. `tests/acquisition/test_binance_usdm_capacity_attestation.py`

The implementation must:

1. bind and fully revalidate receipt 258's exact hash, length, canonical JSON, schema,
   policy, code identity, device/destination, stable component values, stable sum, reserve
   rule, capacity equation, and internally whole blocked state;
2. derive current reserve and total only from current pre-write availability and the
   accepted stable basis, with no operator override;
3. account for the attestation's exact durable bytes and compare against post-publication
   available bytes on the same device;
4. publish one explicit output path transactionally with no-follow reads/creation,
   same-directory staging, no replacement, file and directory fsync, cleanup after
   failure, and refusal of an existing path or symlink;
5. publish exact basis, filesystem, code, arithmetic, blocker/state, authorization, and
   self-identity facts without secrets, credentials, network, or v1/v2/v3 evidence writes;
6. return exit 0 for a complete `blocked` or `sufficient` observation and nonzero only for
   invalid authority, unsafe publication, or incomplete measurement.

The CLI accepts `--store-root` and required `--attestation-path`; it fixes receipt 258 and
source/CLI paths from the repository and exposes no economic, capacity, reserve, device,
state, or publication-policy option. The output path must be a new regular file beneath
`research/sprint_004/` and publication must refuse an existing target.

Tests must prove exact basis binding, component reconciliation, dynamic reserve boundary,
self-length/post-write accounting, same-device binding, blocked/sufficient states without
false authorization, canonical deterministic fields, existing/symlink refusal,
transaction cleanup, no prior-evidence mutation, no network/credential surface, and CLI
redaction/error behavior. Do not weaken or rewrite any existing sizing source, test, CLI,
receipt, or envelope.

Sol High may edit only the three new paths. After editing, Sol may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_capacity_attestation.py -q --tb=short
```

On the first nonzero result or timeout, stop without a repair/rerun and report the exact
failure. Run no other command and use no Git. Stop with the three hashes, unique test
count, targeted command/output/status, and confirmation that existing sizing paths and
evidence are unchanged.

Integration, capacity cleanup, attestation execution against the real destination,
acquisition, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, and
later work remain unauthorized pending reviewer source acceptance. Gate 2 remains not
accepted and next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, ADR-0028, current task, and
ticket. Developer source/test paths, receipts, evidence, and unrelated dirty work are
excluded.
