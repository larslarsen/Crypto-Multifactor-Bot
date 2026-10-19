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

## Targeted feedback: manifest assertion correction

The first authorized targeted run returned exit 1: 49 passed, one failed. The fixture
successfully prepared the release and established distinct gap counts; its new assertion
then accessed is_table on an OutputFileSpec, which exposes canonical manifest fields,
not the private producer classification flag. The developer stopped without edits/retry.
The reviewer inspected the complete production/test diff and verified production SHA
1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b.

Authorize the same source actor to correct only that new fixture's canonical-manifest
assertions in the ingest test. Use the public manifest fields and metadata kind/role
to prove zero metadata rows, preserved table totals and both gap components; retain
the separate private-account is_table assertions, which use _File correctly. Production
source is frozen. Once corrected, run the same exact two-file targeted command above
once more, stop first nonzero without edits/retry, and return both hashes/output.
No other tests, source changes, integration, records, Git or real execution.

## Final source acceptance and conditional execution

The fixture-only continuation passed all 50 cases, exit 0, using the same exact
targeted command. Production bytes did not change after the first result. The reviewer
inspected all final changes and independently verified:

| Path | SHA-256 | Lines |
|---|---|---:|
| src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py | 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b | 1996 |
| tests/ingest/test_binance_usdm_harmonic_bundle.py | 867125b2c123349abe56caa1f8c5e8ec5cc8342dc1909cb4029d123af364f2e0 | 1383 |

Accept this source for integration. The category checks retain every accepted gap
table/lineage, separate quality and authority accounting, preserve the physical total,
and enforce the existing quality pin plus the explicit 202 authority pin. The comparison
is authenticated with a bounded 1 MiB read, retains the accepted pending_reviewer
history marker, and enters the manifest once as zero-row metadata. The production
entry pin remains 18; no comparison is rerun and no OI equality is claimed. The tests
exercise representative schemas and nonzero counts, production pins, canonical manifest
and bundle inclusion, wrong categories/paths/counts and invalid comparison references.
No reviewer validation or producer ran. The source actor has stopped.

The owner directs continuation through the established direct native Hermes route.
Authorize the existing meituan/longcat-2.5-preview:free session to execute the following
complete ordered workflow, with normal interactive approvals and first-failure stops.
This final section authorizes one new preparation only after the exact new integration.
Preserve accepted inputs and unrelated changes; no source/test/helper edits, acquisition,
installation, archive, repair or retry. GPT-6.1 remains reviewer.

1. Apply Review 501 final workflow step 1's five-hash/index/upstream/absent-bundle
   checks, substituting ONLY the two changed hashes above. The unchanged CLI/catalog
   source/catalog test hashes remain exactly those in Review 501. Run once in order:

   ```bash
   .venv/bin/python -m pytest -q tests/catalog tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/ruff check src/cryptofactors/ingest/binance_usdm_harmonic_bundle.py tests/ingest/test_binance_usdm_harmonic_bundle.py
   .venv/bin/python scripts/check_repo_control.py
   ```

   These three named checks may be grouped in one terminal request with set -e,
   preserving complete output and immediate first-nonzero stop. Do not repeat passed
   checks as separate invocations. No automatic formatting/source repair on lint failure.

2. On success write only
   research/sprint_004/505_CEX002_LIQUIDATION_ACCOUNTING_INTEGRATION_RECORD.md.
   Include actual model, exact results/five hashes, and distinguish the developer's
   initial 49-pass/1-fail manifest assertion from the passing 50-case continuation.
   Recheck all five hashes; stage exactly the TWO changed files above plus Record 505.
   Inspect names and git diff --cached --check. Commit as
   CEX-002: preserve liquidation gap categories and comparison provenance
   and push normally; verify HEAD==origin/main and empty index. Retain the full NEW
   source integration commit and verify its five committed blobs against frozen hashes.
   Do not invent a pre-commit hash in the record; Record 506 pins the resulting commit.

3. Execute Review 498 final workflow steps 3–5, using only that NEW full source commit
   in the exact prepare CLI. Capture full catalog ordered-row digests and all ID/status
   pairs BEFORE launch, zero CEX rows/five rejected IDs, free space and absent bundle
   root. Invoke once with native background=true/notify_on_complete=true, retain and
   monitor that same process to terminal. On success inspect only emitted descriptor,
   eleven named manifests, bundle footer and owned inventory. Include the separate
   liquidation quality/authority counts and the comparison metadata reference, alongside
   the already-required IDs/dependencies/rows/bytes/schema/retained-inventory audit.
   Confirm consumable=false and unchanged catalog full snapshots after the attempt.
   On failure preserve exact rich output, repeat only catalog/free-space observations,
   and stop without product inspection, private-function diagnostic or producer retry.
   All allocations, reserves and producer-owned new-write confinement remain unchanged.

4. Publish terminal evidence only as
   research/sprint_004/506_CEX002_LIQUIDATION_CORRECTED_BUNDLE_PREPARATION_RECORD.md,
   applying Review 498 step 6's exact record-only Git checks, normal commit/push and
   final HEAD==origin/main/empty-index verification. Include actual literal source commit,
   command/model/process/exit/output, correctly timed full catalog evidence/resources
   and candidate facts or blocker. Terminal evidence publication is allowed after a
   producer failure; earlier identity/validation/Git/approval failure stops without repair.
   Stop for reviewer inspection. No replay, proof, catalog admission, consumer run,
   next ticket or final Gate acceptance is authorized.

## Integration acceptance and live preparation

Accept Hermes integration 42ecac90f5c47411d4d098cf68e046257bab3a97 and Record 505.
The reviewer independently matched every committed source/test hash above and all
three unchanged CLI/catalog hashes, and verified the exact three-path commit. Hermes's
grouped regression/lint/control command returned exit 0: 149 cases, Ruff clean and
repository control PASS. No passing check was repeated. Normal push and empty index
were confirmed before execution.

Record 505 repeats this review's earlier imprecise wording, authenticated before a
bounded read. The actual source checks the size before the bounded read and authenticates
its bytes with SHA-256; this review corrects that phrasing. No source correction or
validation rerun follows from this editorial clarification.

The single new real prepare launched with that full source commit as native process
proc_311fa1978b3f / PID 1612662. Its pre-launch full catalog digests are the unchanged
zero-CEX-row digest 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
and five-quarantine-row digest b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103.
All five IDs are REJECTED/REGISTERED, bundle root absent, free bytes 78,953,398,272.
The first native poll reports running, uptime 68 seconds, no output. Hermes owns
continued monitoring of that same process and Record 506 publication. Do not launch
another process or repeat a completed producer/validation command.
