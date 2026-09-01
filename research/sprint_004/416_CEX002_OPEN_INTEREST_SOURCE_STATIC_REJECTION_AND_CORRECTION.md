# CEX-002 Review 416 — Open-Interest Source Static Rejection and Correction

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject the unintegrated Review-415 drop; authorize one bounded correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev — Codex Sol
- **Next ticket:** `NONE`

## Inspected drop

The unintegrated Review-415 drop is confined to the authorized paths and is unstaged:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 765 | `aac74216d6105c722bf00e09bdaebd8792a347974f7515b284ffe25a81b0999a` |
| `scripts/research/normalize_binance_usdm_open_interest.py` | 50 | `e626bbbbac396eb2e5e85ec1aa1e5a4e701fce23e372ea2eb71c2499c6639b24` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 329 | `b08e6b950f580009ef9be62ccb46e31f3100cc2e13701100d44657a8fa23d727` |

Sol used the one Review-415 targeted command. It exited 0 with all 24 collected cases passing:

```text
........................                                                 [100%]
```

That result is accepted as source feedback only. No source is integrated and no real product is
accepted.

## Blocking findings

### 1. The two raw authorities are not actually pinned

`load_v3_recovery_sources` accepts any gzip JSONL whose filename matches its own digest and whose
row/byte/family totals match. It never requires the accepted v3 manifest digest
`4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d`. A different selection
with the same aggregate totals can therefore become input.

`load_generation0_sources` accepts a three-table substitute SQLite file when its caller supplies
a matching count; its own test proves that behavior. It does not authenticate the accepted schema,
domain constraints, singleton authority, sealed receipt prefix, fixed run-7 seal head, or absence
of an unsealed tail. It also proves only 685,072 total Binance completions, not the accepted 522,865
generation-0 `daily/metrics` completions. Rehashing selected content files does not repair an
untrusted key-to-digest mapping.

### 2. A completed product has no durable identity

The implementation writes partition and lineage objects but no final hidden product descriptor.
The CLI prints counts and discards the ordered partition/lineage identities. If a replay produces
the same Parquet bytes from different lineage, multiple lineage objects can exist with no durable
fact selecting the correct pair. There is no single content address proving that every partition
completed, that the exact source authorities were used, or that the typed gap set belongs to the
same result.

The HBARUSDC conflict is otherwise only an in-memory dataclass and a conditional JSON member of a
month lineage manifest. It is not a durable row under the accepted typed quality-gap schema and
would disappear if the affected symbol/month had no consumable partition.

### 3. Output child paths can follow symlinks

Only the caller's root is checked before publication. Existing `.staging`, `.partitions`,
`.lineage`, symbol, or month paths are then opened or created with ordinary path operations that
can follow a symlink outside the held root. The content-addressed name does not prevent a parent
escape.

### 4. Impossible economic values are accepted

Exact decimal parsing correctly rejects non-finite and overflowing lexemes, but negative open
interest, negative open-interest value, and negative long/short ratios still pass. These are
impossible for the declared stock and ratio fields and fail the ticket's Gate-3 quality contract.

## Exact correction authorized

Sr Dev — Codex Sol on GPT-5.6-sol High may edit only the same three unintegrated paths and must
close all four findings without changing an existing repository path.

1. Pin the v3 compressed manifest to exact SHA-256
   `4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d`, its 51,275 rows,
   9,207,379,061 bytes, 50,921 metrics rows, 354 book-ticker rows, and the fixed HBAR conflict.
2. Open generation 0 read-only and reuse the acquisition module's existing authentication logic:
   register its domain functions on the read-only connection, bind an `AcquisitionState` to that
   connection without calling its mutating `open`, run schema/domain/singleton/prefix
   authentication, require application/user versions and clean integrity/foreign-key results,
   require seal-head receipt
   `8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab`, apply the existing
   terminal no-unsealed-tail watermark rule, and require exactly 685,072 Binance completions and
   522,865 generation-0 metrics completions. Existing SQLite sidecar paths must also be regular
   no-follow inputs. Detach the borrowed connection before closing so no acquisition-state close
   path owns or mutates the authority.
3. Persist every inferred missing five-minute run, including the 288-point HBARUSDC contract-day,
   as a hidden content-addressed Parquet artifact using the accepted `QUALITY_GAP_COLUMNS` schema.
   Preserve the fixed checksum-conflict detail in its lineage JSON. Do not publish the final
   cross-product coverage product.
4. After all data partitions, lineage manifests, and gap artifacts are durable, publish exactly
   one hidden content-addressed product-completion descriptor as the last operation. It pins the
   exact ordered partition/lineage set, typed-gap artifact and rows, both accepted raw-authority
   identities/counts, schema/writer identity, normalizer source identity, and product totals. An
   interruption before that final rename has no complete-product descriptor. Replay must select
   or reproduce the same descriptor bytes. The CLI must report its path and SHA-256.
5. Hold the output root and create/open every child directory and temporary/final file no-follow
   relative to held directory descriptors. No pre-existing child symlink may be followed. Verify
   every final path remains under the held root before returning it.
6. Reject negative `sum_open_interest`, `sum_open_interest_value`, and non-null ratio fields.

The corrected tests must reject a self-addressed but nonaccepted v3 manifest, the prior minimal
substitute generation-0 database, unsealed authority tails, negative economic fields, and symlinked
output children. They must prove the exact typed HBAR gap row, inferred missing-run rows, final-
descriptor-last interruption behavior, descriptor contents, and byte-identical descriptor replay.

After the correction Sol may run exactly once:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_open_interest.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact command and output without patching or
rerunning. No real data/state invocation, integration, repository record, Git, commit, push,
network, acquisition, cleanup, other product, final bundle, catalog transaction, experiment,
backtest, model, or trading-engine work is authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/416_CEX002_OPEN_INTEREST_SOURCE_STATIC_REJECTION_AND_CORRECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The unintegrated three-path source drop and every unrelated dirty path remain unstaged.
