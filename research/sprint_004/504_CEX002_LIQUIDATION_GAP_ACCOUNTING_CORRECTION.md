# CEX-002 Review 504 — Preserve liquidation gap categories and accepted evidence

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Senior source actor: Sr Dev — Codex Sol, GPT-6 Sol High
Disposition: Review 501 integration accepted; terminal failure accepted; two-path source correction

## Accepted integration and failure evidence

Accept integration 05acac2f513074ceb413450b9bb1d241492d6dfb and Record 502. The
reviewer verified all five committed source/test blobs against Review 501 and the
exact three-path commit. Hermes's broader catalog/bundle run passed 136 cases;
two-path Ruff and repository control passed. Record 502 reverses the two progress
line counts; this does not change the total or exit 0 and requires no rerun.

Accept terminal Record 503, publication 159bbb81eb89791b5cb45f22d376ddc5ec5a6874.
The single new prepare exited 1 with row_mismatch, quality-gap rows are not the
accepted pin, product binance_usdm_liquidation_observed_daily. The same native process
proc_df540b91aa3a / PID 1418929 was tracked to its terminal result. Catalog full-row
digests before launch and afterward match; zero CEX reference rows remain, the five
quarantined datasets remain rejected, and no bundle directory was created.

## Diagnosed cause and accepted authority

Review 476 accepts observed-liquidation completion
dc4127dccad31477cb72ec6fdf076dbdbdef34a1212d4f090d5f421b96dc267f.
The reviewer read that bounded completion and independently matched its SHA-256,
then inspected its declared gap categories and comparison reference, not product rows:

- 2,570 all_input_missing artifacts contain 4,626 daily gap runs, covering 6,716
  missing daily slots. They are the quality-gap count pinned by this adapter.
- One coinalyze_symbol_unmapped authority-gap artifact contains 202 unmapped native
  identities. The completion separately declares authority_gap_rows=202.
- The adapter currently adds both categories into quality_rows, producing 4,828 and
  failing against the correct quality pin 4,626. Do not change that pin to 4,828.
- The completion also references the accepted comparison JSON under .comparison:
  bd76dd2069e658ce11a00b7685e0008d4d5be0bec682acdf5640552a31af3391,
  28,660 bytes, 18 entries. The reviewer matched its file SHA/size. It is required
  provenance under ADR-0037, but _account_ordinary never adds it to account.files;
  merely fixing the row sum would therefore hit the next unexpected-file failure.

Review 476 and Record 477 preserve the three measured BTC OI differences and ETH
unavailability. Referencing their accepted evidence must not rerun the comparison,
claim OI equality or reclassify the pending_reviewer marker stored in immutable history.
Liquidation remains observed/censored, event_complete=false and unknown availability.

## One-way source prompt

Continue the existing owner-approved direct source-repair route using the same GPT-6
Sol High actor. It holds this adapter's context and its last two drops passed integration;
this is one diagnosed producer-format correction. GPT-6.1 remains reviewer. Read
CURRENT_TASK, this review, Review 476's final acceptance and Record 477's file/row facts.
Exactly two writable paths:

1. src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py
2. tests/ingest/test_binance_usdm_harmonic_bundle.py

Correct the liquidation-specific accounting without changing accepted inputs or economics:

- Classify its two actual declared gap kinds explicitly. Count all_input_missing rows
  as quality gaps and coinalyze_symbol_unmapped rows separately as authority gaps.
  Authenticate and retain BOTH Parquet/lineage pairs in manifests and bundle inputs.
  Preserve total physical table rows; do not omit authority gaps merely to pass the pin.
  Reconcile the separate authority count with completion.authority_gap_rows, pin 202 in
  production, and retain the existing quality pin 4,626 and main-data row equations.
  Reject unknown/malformed gap kinds or category/path mismatches rather than silently
  excluding them. Other products' existing gap behavior remains unchanged.
- Authenticate the liquidation completion's comparison reference with bounded metadata
  reads and its declared path/SHA/entry count, and include it once as metadata (zero
  table rows), not as a fabricated table/component. Require its existing document type
  and actual entries count to match; production still pins the accepted completion and
  resulting comparison identity. Reject missing, altered, unsafe or mismatched references.
  Do not copy, rewrite, rerun or reinterpret accepted comparison evidence.
- Use representative nonzero fixtures with actual gap kinds, separate counts and a
  declared comparison document. Prove daily/authority sums remain distinct in quality
  metadata, both categories remain in file/bundle closure, and comparison is authenticated
  metadata only. Cover category/count/pin mismatch, unknown kinds, and missing/changed/
  unsafe comparison. Exercise the production row-pin check using a bounded fixture seam
  so the original combined-count bug is caught. Preserve existing regressions.

No CLI/catalog/generic/source changes, repository records, Git, integration, accepted
data writes, real prepare/private-function probes, helpers, network, installs or subagents.
After completing edits run exactly once under the targeted senior exception:

```
.venv/bin/python -m pytest -q tests/catalog/test_cex002_reference_release.py tests/ingest/test_binance_usdm_harmonic_bundle.py
```

Stop at the first nonzero result without edits/retry. Return exact output/exit and two
final SHA-256 values/line counts, then stop for reviewer inspection. Hermes is stopped;
no new real prepare, comparison rerun or consumer run is authorized by this source drop.

Reviewer publication scope is exactly this Review 504, docs/handoff/CURRENT_TASK.md
and tickets/CEX-002.md. No source/test integration or implementation evidence is included.
