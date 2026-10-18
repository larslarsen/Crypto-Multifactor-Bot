# CEX-002 Review 501 — Correct the physical inventory bound

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Disposition: integration accepted; terminal preparation failure accepted; bounded source correction

## Reviewed result and diagnosed cause

Accept Hermes integration 2395f03850c3941ed0e1145053f743b6c5f69c4c and Record 499:
all five committed source/test hashes match Review 498, the exact four-path commit was
pushed, 134 catalog/bundle cases passed, scoped Ruff and repository control passed.
The progress split in Record 499 is a minor reporting error: the native output is
72 plus 62 marks, not 67 plus 67; the total 134 and exit 0 are correct. No rerun is needed.
Record 500 independently pins the integration commit omitted from Record 499's literal
SOURCE_COMMIT placeholder; this review resolves that identity without another record cycle.

Accept corrected terminal Record 497 publication 9402536f8d05981da1e2c48fca0710719fdf0a0e
and Record 500 publication d9f77def49746b8ab2bc0d82583e030e9d5e0f4f as failure evidence.
The one corrected prepare, native proc_caa44bb65052 / PID 1286281, exited 1 with
metadata_bound: kline physical inventory exceeds the accepted bound, product
binance_usdm_trade_flow_1h. The full read-only catalog digests were captured before
launch and after failure and match. Zero CEX release rows remain; the bundle root was
not created. No producer repetition or accepted-data repair has occurred.

The reviewer independently inspected physical filename inventories, not product tables:

| Product | Partition files | Lineage files | Quality-gap pair + completion | Total |
|---|---:|---:|---:|---:|
| bar_1h | 22,664 | 42,968 | 3 | 65,635 |
| trade_flow_1h | 22,680 | 42,968 | 3 | 65,651 |

Record 459's component counts were correct but its summed totals were one short:
22,633 accepted partitions + 22,633 accepted lineages + 3 metadata/gap files = 45,269,
not 45,268. Adding the accepted retained counts gives the totals above. Review 498
adopted the erroneous 65,650 total, and the reviewer missed that arithmetic error.
This correction supersedes those summed totals only. Descriptor hashes, retained kind
counts, rows, schemas, authority and accepted product bytes stay unchanged.

## One-way source prompt

Continue the existing owner-approved directly supervised source-repair route using the
same GPT-6 Sol High actor, which already holds this adapter's context and delivered
the integrated correction. GPT-6.1 remains reviewer. Read CURRENT_TASK and this review.
Exactly two writable paths:

1. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
2. tests/ingest/test_binance_usdm_harmonic_bundle.py

Replace the erroneous universal kline physical count with a finite bound derived from
the authenticated accepted file closure plus that product's already pinned permitted
retained counts. Pass the accepted closure count into the private walk if useful, or
use an equally explicit per-product derivation. Do not merely add unexplained slack.
The real bar/flow totals 65,635/65,651 must fit. Preserve missing-reference rejection,
exact production retained-kind counts, path/hash/symlink checks, strict unexpected-file
rejection for every other class/product, resource limits and excluded-file semantics.
No fixture or public production switch may bypass the finite bound.

Add a meaningful boundary regression that permits the complete accepted closure plus
exact allowed older inventory and rejects one additional regular physical file with
metadata_bound. Check both product limits, including the completion and quality-gap
pair. Use a bounded synthetic walk/file-metadata fixture if needed; do not create or
read 65,000 real data files. Keep the test independent enough to catch omission of one
of the three metadata/gap files and cross-product use of the larger bound. Preserve
existing authentication and arbitrary-extra rejection tests.

No other source/CLI/catalog changes, records, Git, integration, helper files, data writes,
real producer/accounting probes, network, installation or subagents. Once source is
finished, run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

Stop on the first nonzero result without edits/retry. Return exact output/exit and
two final SHA-256 values/line counts, then stop for source review. Hermes is stopped;
no third real preparation is authorized by this source assignment.

Reviewer publication scope is exactly this Review 501, docs/handoff/CURRENT_TASK.md
and tickets/CEX-002.md. This publication excludes source/tests and implementation evidence.
