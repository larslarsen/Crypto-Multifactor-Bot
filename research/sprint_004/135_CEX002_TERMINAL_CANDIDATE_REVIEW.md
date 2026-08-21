# CEX-002 Terminal Candidate Review

Date: 2026-08-21

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed head: `d07b1fb1c96738205d3100077b4b4a946e6f0588`

Subject record: `research/sprint_004/134_CEX002_RUFF_INTEGRATION_AND_CANDIDATE.md`

## Decision

**ACCEPT THE INTEGRATION, COMPACT REPORT, CONTENT-ADDRESSED DETAIL, PRESERVED MONOLITH,
AND TERMINAL STATUS-2 BLOCKED OUTCOME. REJECT RECORD 134 AS THE AUTHORITATIVE EXECUTION
RECORD UNTIL HERMES PUBLISHES THE EXACT FORWARD CORRECTION BELOW.**

The corrected implementation is committed at
`dba025c72a5d0b09d09790b51d09cfdcf32e9dfd`, before the candidate start. The compact
report is valid JSON at 17,349,108 bytes and SHA-256
`e51ef2735c4937cf61cc614836478ee053c89f8100d5e4193a22e665f651fcd9`. Its descriptor
binds 733,203 rows and 733,191 pending keys to the manifest detail at compressed SHA-256
`8abf72fa22c6714051c2b451bfd27e17b6c84a65b7e476be63bc21f09f265945`, 11,288,256
bytes, and uncompressed content address
`d9be584d7a1eecd43482ea1a05a0d9dd8cd681970c4ec5ff225740a28f27a5bf`, 466,717,014
bytes. The preserved 1,059,297,547-byte monolith independently rehashes to
`46d1980ecf384874e45c4c31f142c16efc5472ef63231e9456e264f3e94ef691`.

The report honestly remains `BLOCKED` / `accepted=false`: 771 perpetuals are confirmed,
63 names remain unresolved, seven source products are blocked, the version-3 plan is
`candidate_unmigrated`, migration and download are false, and `samples` is empty. No Gate
1 pass, plan migration, acquisition, or later gate is accepted.

The reviewer executed no pytest, Ruff, repository-control, network, candidate, migration,
sample, or data-mutating command. Read-only Git and artifact inspection does not replace
Hermes's recorded command evidence.

## Record defects

Record 134 contains mutually inconsistent execution identities. Sections 1-3 identify
`d428aec` as `HEAD` and C5 output, and section 2a labels `e0068e7` as the review-133
integration. Git history proves:

- `e0068e7` is the earlier review-126 report-split integration;
- `d428aec` is the earlier review-130 test integration; and
- `dba025c72a5d0b09d09790b51d09cfdcf32e9dfd` is the review-133 two-path Ruff
  integration, committed at 2026-08-21T13:48:43-07:00 before the candidate began at
  2026-08-21T13:51:14-07:00.

The record's FAPI cache delta is also copied from record 121's prior run. The nine files
that predate this candidate total 9,697,128 bytes. The candidate added the file modified at
2026-08-21T13:58:38-07:00 with 1,077,579 bytes, so the correct after state is 10 files and
10,774,707 bytes.

Finally, section 8 reverses the accepted record phases and misdescribes the iterator count.
Production writes and validates `header -> row -> collision -> rejection ->
raw_validation_pending_key`. The descriptor's 1,466,395 total records comprise one header
plus 1,466,394 data records. `iter_manifest_detail` skips the header and yields exactly
1,466,394 records.

These are evidence-record defects. They do not change source, report, data, manifest, gate,
or candidate behavior, and they do not justify rerunning a command or the candidate.

## Hermes correction authorization

Jr Dev - Hermes must establish `HEAD == origin/main` at this reviewer-publication commit
and leave every source, test, report, ignored data, checkpoint, cache, journal, database
sidecar, and unrelated dirty path untouched.

Hermes creates only
`research/sprint_004/136_CEX002_RECORD_134_CORRECTION.md`. It preserves record 134 and
records a forward correction containing:

1. the exact three integration identities and correct review-133 integration commit above;
2. the actual focused-command sequence, explicitly correcting C5/HEAD to `dba025c` from
   the original session transcript when available, without inventing output;
3. the correct FAPI before/after counts and byte totals above;
4. the correct manifest phase order and iterator/header arithmetic above; and
5. a statement that every other accepted record-134 candidate, artifact, invariant,
   mutation, and stop claim remains unchanged.

If the original C5 transcript is unavailable, Hermes says so literally and cites the Git
timestamp proof above; it does not rerun or reconstruct the five-command sequence. It runs
no test, Ruff, candidate, network, migration, sample, Gate 2, normalization, catalog, or
data-mutating command.

Hermes then updates only `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md` to add
record 136 and return the next required actor to the reviewer. It stages exactly those two
controls plus record 136, commits, pushes, proves `HEAD == origin/main`, and stops. It uses
no reset, restore, checkout, stash, clean, deletion, or worktree rewrite.

## Next architecture

After the corrected evidence record is accepted, the next CEX-002 work is a reviewer-led
official-source investigation for the 63 unresolved archive-only names. Their spelling is
only an audit hint and cannot establish perpetual or delivery membership. The investigation
must determine what retained or newly queried official Binance evidence can authoritatively
classify the 46 dated-delivery candidates and 17 settlement-artifact candidates without
reducing the historical perpetual universe.

The candidate also proves that the current 268,435,456-byte amendment allowance cannot fit
the complete declared cost-calibration sample: 46 required objects remain blocked and the
exact cost sample is 12,522,974,218 compressed bytes. That is a separate architecture and
budget decision after membership authority is resolved; it is not authority to download
books, buy data, reduce scope, or migrate the candidate plan.

## Reviewer publication

The reviewer publishes exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/135_CEX002_TERMINAL_CANDIDATE_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, report, data, checkpoint, cache, journal, database sidecar, or unrelated
dirty path belongs to this publication.

## Disposition

CEX-002 remains `IN_PROGRESS`. Gate 1 has not passed. Gate 2 and every later gate, Nautilus
work, Harmonic Trader work, payoff analysis, PAPER, LIVE, and every next ticket remain
unauthorized. Next ticket remains `NONE`.
