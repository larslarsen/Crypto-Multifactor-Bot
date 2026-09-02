# CEX-002 Review 458 - Corrected Full Audit Authorization

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected temporary verifier for one Hermes execution
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Temporary verifier acceptance

Review 458 accepts Sol's corrected temporary read-only verifier at exactly:

```text
scripts/research/audit_cex002_record456.py
sha256 = 0bfae90a2a5c76be1ef1b8389cabda1ca17793eba1d6cc520c94f18ed5464da6
lines  = 730
```

Sol edited only that existing untracked file and did not execute, delete, stage, commit, or push it.
No production/test/CLI/data/control/evidence/other path changed.

Static inspection confirms the correction preserves the prior full-file hash, metadata-row,
lineage-binding, exclusion-set, staging, and inventory checks and now also:

- compares every partition's actual PyArrow schema to the exact accepted bar or trade-flow schema;
- bounds and reads each small quality-gap artifact, compares its actual schema, and recomputes both
  row count and missing-grid total;
- rejects malformed or duplicate provider-invalid keys and proves exact one-to-one equality between
  provider-invalid gap rows and exclusion-lineage entries;
- accepts only exact canonical relative descriptor path shapes, checks every component without
  symlink traversal, and proves resolution remains beneath the fixed product root;
- reads `/proc/*/cmdline` directly and rejects a live Python process with the exact relative or
  absolute kline-normalizer script argument; and
- raises `AuditMismatch` immediately and returns nonzero on the first mismatch or unexpected read
  failure.

This accepts only a temporary audit command, not the data products or Gate 3.

## Hermes execution and correction authorization

Jr Dev - Hermes performs only this ordered workflow:

1. Prove `HEAD == origin/main`, prove the temporary verifier's exact hash and line count above, and
   prove the two accepted completion filenames from Review 455 remain the sole completion files.
   Any mismatch stops before execution.
2. Execute the verifier exactly once from the repository root, with bytecode writes disabled:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python scripts/research/audit_cex002_record456.py
```

   Capture its complete output and exit status. It must stop on the first nonzero result. There is no
   second invocation or retry.
3. After the verifier is terminal, obtain one new exact audit-time capacity observation with
   `df -B1 --output=avail data` and label it as post-audit, not as reconstructed run-time evidence.
4. Remove exactly the untracked temporary file
   `scripts/research/audit_cex002_record456.py` and prove that path is absent and unstaged. No other
   file or directory may be removed or cleaned.
5. Publish `research/sprint_004/459_CEX002_CORRECTED_FULL_KLINE_AUDIT_RECORD.md` plus matching
   `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, commit and push only those three paths,
   prove `HEAD == origin/main`, and set both actor fields to the Lead Quantitative Finance
   Researcher/Engineer.

On exit zero, Record 459 must state every verified predicate without overstating it and include the
exact completion identities, 22,633-per-product audited counts, aggregate rows, schema identities,
gap rows/missing-grid totals, exclusion set/equality totals, referenced versus unreferenced physical
inventories, staging/process results, complete command/output/exit status, verifier hash/lines,
post-audit exact capacity observation, temporary-file removal proof, and corrections to the Record
454 chronology/capacity labels and Record 456 audit-method claims.

On nonzero, Record 459 records the exact first mismatch/output and still removes only the temporary
verifier before publication. It does not diagnose by guess or repair data.

No normalizer, test, source/test/CLI edit, data change, download, network, wrapper, detach, polling
loop, retry, general cleanup, catalog, NautilusTrader, experiment, model, Harmonic Trader, other
product, PAPER, LIVE, or next-ticket work is authorized. Gate 2 remains accepted; Gate 3 and CEX-002
remain `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer publishes exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
The temporary verifier remains untracked for Hermes execution and deletion. All data, runner, and
unrelated dirty paths remain unstaged and untouched.
