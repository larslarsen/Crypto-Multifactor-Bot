# CEX-002 Review 496 — First real bundle candidate preparation

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes, Nous meituan/longcat-2.5-preview:free
Scope: one real prepare; candidate stays non-consumable; no catalog admission

## Decision

Review 494 accepts source integration 30719fdd2a0e71ed8266d8ce50564f4dc5efaea5
and Record 495. Its 127 catalog/bundle cases, resumed scoped Ruff and repository
control passed. Do not repeat those checks or any accepted-product normalizer.
The owner now directs continuation after that acceptance. Continue the previously
approved direct Hermes execution/supervision route for the next stated preparation
step, bounded below. Reviewer engineering acceptance remains exclusive.

Use the existing native Hermes session and reliable free Nous model selected for its
accepted recent integrations. No source actor or new subagent is needed. GPT-6.1 Sol
remains reviewer and does not execute the producer or author source/test code.

The existing catalog is exp003.db. The new bundle directory was absent when the
reviewer inspected it. Observed filesystem availability was 118,644,731,904 bytes;
the producer must still enforce current capacity itself. Preserve the fixed
24,352,003 bundle-file cap, 4,985,471,619 metadata remainder and 29,690,701,415
operating reserve. Do not expand allocations, copy accepted inputs or rewrite sizing.

ADR-0037's preparation creates eleven canonical reference manifests, one new typed
bundle object and an immutable prepared descriptor. It admits no catalog rows and
requires no consumer proof yet. The ten accepted products and all pinned authority,
reconciliation, holdout, unknown-availability, fee and censored-liquidation semantics
remain unchanged. The external Nautilus checker is a later bounded source assignment.

## One-way Hermes prompt

Work only on CEX-002 in /home/lars/Crypto_Multifactor_Bot. Read the current-task header
and this review; previously read architecture/history need not be reread. Preserve
unrelated working-tree changes and never read archive. Use normal interactive approvals;
no oneshot/yolo bypasses, installations, acquisition, source/test edits or new helpers.

1. Confirm HEAD equals origin/main and the index is empty. Verify the five integrated
   source/test hashes against Record 495. Bind the producer to the accepted source
   commit 30719fdd2a0e71ed8266d8ce50564f4dc5efaea5, even though reviewer governance
   commits may have advanced HEAD. All five accepted blobs exist at that commit.
   Stop on any mismatch or unexpected existing bundle artifacts; do not repair.
2. Capture filesystem free bytes and a read-only SQLite snapshot using URI mode=ro.
   Run these two queries and retain their ordered results for the record:

   ```sql
   SELECT dataset_id, publication_uri FROM dataset
   WHERE transform_name = 'cex002_reference_publication' ORDER BY dataset_id;
   SELECT dataset_id, quality_status, publication_status, quality_summary_json
   FROM dataset WHERE quality_summary_json LIKE '%cex002_bitmex_false_authority%'
   ORDER BY dataset_id;
   ```

   Expect zero CEX reference-publication rows and the five existing REJECTED/REGISTERED
   quarantine rows. Do not open a writable catalog or rerun quarantine. Basic inline
   read-only metadata inspection is allowed; do not author a new checker/helper file.
3. Execute this exact producer command once:

   ```bash
   PYTHONPATH=src .venv/bin/python scripts/research/publish_binance_usdm_harmonic_bundle.py prepare --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 30719fdd2a0e71ed8266d8ce50564f4dc5efaea5
   ```

   Use terminal background=true and notify_on_complete=true for this bounded long
   task. Save its native process ID and wait/poll that same process for its terminal
   exit/output; waiting is not another run. Do not use an unsupported foreground
   timeout above 600 seconds or launch a duplicate command. Stop execution work on
   first nonzero, denial, identity mismatch or resource blocker, without edits/retry.
4. On success, inspect only the emitted prepared descriptor, its eleven named new
   manifests, the bundle Parquet footer and the new owned directory inventory. Report
   candidate SHA, dataset IDs, per-product file/main/gap counts from sealed metadata,
   bundle rows/bytes/SHA/schema, new metadata bytes and current free space. Confirm
   consumable=false, exactly eleven distinct required dataset types and ten bundle
   dependency edges, and no proof/publication files or abandoned owned stages. Do not
   run the later consumer checker or reread accepted history as whole tables.
   Repeat only the two read-only catalog queries from step 2; require identical ordered
   results. Preparation must not make the release visible. No preparation replay is
   assigned in this step.
5. Record the terminal outcome in exactly
   research/sprint_004/497_CEX002_REAL_BUNDLE_PREPARATION_RECORD.md. Include actual
   model, source commit/hashes, exact command, native process/exit/output, resource
   observations, catalog before/after results and candidate metadata on success.
   On producer failure, stop preparation and document the exact blocker/trace and any
   already created candidate artifacts reported by the command; do not inspect or
   repair data further. Terminal disclosure/record publication is still authorized.
   On an automatic approval rejection, report the rejected action and reason; do not
   reword/retry it to evade review. The record must not claim release/Gate acceptance.
6. Publish only Record 497: verify the index is empty, stage its exact path, inspect
   staged names and git diff --cached --check, commit as
   CEX-002: record first real bundle preparation, and push normally. No data files,
   source/tests, reviewer governance or unrelated files may be staged. Verify HEAD
   equals origin/main and the index is empty. Stop and return the full record commit,
   terminal outcome and candidate identity. A record/Git failure stops publication;
   do not amend, reset, force push, repair or retry without reviewer direction.

New data writes are confined to data/.cex002_harmonic_bundle under the existing
producer's policy. Record 497 is Hermes-owned implementation evidence. No catalog
admission, proof generation, external consumer run, source change, accepted-product
mutation, next ticket or final release acceptance is authorized by this review.

Reviewer publication scope is exactly this Review 496,
docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md. The reviewer may publish only
that governance set; Hermes owns producer execution, data and Record 497 publication.
