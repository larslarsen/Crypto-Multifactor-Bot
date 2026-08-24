# CEX-002 Capacity Attestation Source Review

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** first ADR-0028 drop rejected on validation and transaction residuals
- **Authorized actor:** Sr Dev - Sol High continuation
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Inspected identities

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py` | `845c495ff19b423ac40dbc192ae75babdda33b22ff301e367e5e910cec64adb9` |
| `scripts/research/attest_binance_usdm_harmonic_capacity.py` | `e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5` |
| `tests/acquisition/test_binance_usdm_capacity_attestation.py` | `529c6d1d121178323d84c5ada4c6875bec98828e899b641bd72bfccab10a5c98` |

The test file has 10 functions and the three paths pass static whitespace validation.
Every existing sizing source/test/CLI and receipt identity remains byte-identical. The
reviewer ran no pytest, Ruff, control, real attestation, network, or data command.

## Accepted base

Preserve the exact receipt-258 pins, stable capacity constants and arithmetic, strict
canonical receipt decoding, no-follow path walk, fixed CLI surface, self-length loop,
blocked/sufficient semantics, no false authorization, same-directory staging, no-replace
intent, fsync intent, error redaction, and unchanged prior evidence.

## Blocking findings

1. `validate_attestation_bytes` does not validate the attestation's `basis` or
   `code_identity` at all. It accepts arbitrary stable components, receipt identity,
   destination/device, policy/source hashes, reserve rule, equations, generated time,
   authorization statement, and extra/missing fields after an attacker recomputes the
   self hash. The durable attestation therefore cannot be reauthenticated.
2. `stable_projection_sha256` is a new hash over only five capacity components and one
   equation. ADR-0028 requires the accepted full v3 stable-receipt projection identity,
   including authority, measurements, schemas, lineage, counts, partitioning, and every
   other stable receipt field. The field is materially mislabeled and does not bind that
   authority.
3. Publication measures availability after staging, then creates a second hard-link
   directory entry and returns without measuring after link and directory fsync. The
   published `post_publication_available_bytes` can therefore exceed actual final
   availability. The transaction must use an atomic no-replace operation whose final
   publication does not add a second directory entry, and must prove the final observation
   does not undercut the attested value.
4. Same-device validation compares the receipt's declared device string to the store and
   output, but never checks the actual receipt file's `st_dev`. The test named as a
   three-device proof also compares only three supplied strings and cannot catch a receipt
   file on another mounted device.
5. Tests do not rehash and reject tampered closed-shape basis/code/filesystem/capacity/
   authorization fields, do not prove the full stable receipt identity, do not exercise
   final post-publication availability, and do not exercise `run_capacity_attestation`
   end to end over a synthetic repository layout.

## Exact continuation

Continue only the same three new paths. Do not edit any existing sizing path, receipt,
evidence, ADR, record, or control file.

1. Define one closed attestation schema. Revalidation must require exact top-level and
   nested key sets; ticket/schema; a parseable UTC generated time; basis exactly equal to
   the accepted basis document; code identity exactly equal to recomputed source/CLI
   identities; filesystem destination/device and accounting; all capacity values, reserve
   rule, equations, blockers/state; exact authorization object/statement; canonical bytes,
   exact self length, and self identity. Rehashing after any mutation must not make a
   forged document valid.
2. Bind `basis` to the full accepted v3 `stable_receipt_identity`, using the accepted
   sizing module's canonical `stable_receipt_projection` boundary or a byte-equivalent
   implementation. Name the field accordingly and test it against the full receipt. Do
   not substitute a capacity-only hash.
3. Read receipt 258 through no-follow descriptors and capture its actual regular-file
   device. Require that actual device, its declared device, store device, and output-parent
   device all agree.
4. Replace hard-link-plus-unlink publication with a Linux atomic no-replace same-directory
   rename (`renameat2(..., RENAME_NOREPLACE)` or a byte-equivalent wrapper). The staged
   directory entry becomes the target rather than creating a second entry. Fsync the file
   and directory, measure availability after final publication, and require it to equal or
   exceed the conservative value frozen in the document; otherwise remove the target,
   fsync, and fail without leaving evidence. Never overwrite an existing file or symlink.
5. Extend tests to mutate every closed schema section, recompute self identity, and prove
   rejection; prove the exact full stable receipt identity and actual receipt device;
   inject post-publication capacity loss and transaction failures; prove cleanup and
   existing-target preservation; and exercise `run_capacity_attestation` end to end in a
   synthetic repository/device layout without touching real evidence.

Preserve a minimal CLI with only `--store-root` and `--attestation-path`, exit 0 for a
complete blocked or sufficient observation, redacted nonzero failures, and no network or
credentials.

After editing, Sol may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_capacity_attestation.py -q --tb=short
```

On the first failure or timeout, stop without repair/rerun and report exact output. Run no
other command and use no Git. Stop with all three hashes, test count, command/status/output,
and unchanged accepted sizing/receipt hashes.

Integration, cleanup, real attestation, acquisition, normalization, catalog,
NautilusTrader, Harmonic Trader, PAPER/LIVE, and later work remain unauthorized. Gate 2
remains not accepted and next ticket remains `NONE`.

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths and unrelated dirty work are excluded.
