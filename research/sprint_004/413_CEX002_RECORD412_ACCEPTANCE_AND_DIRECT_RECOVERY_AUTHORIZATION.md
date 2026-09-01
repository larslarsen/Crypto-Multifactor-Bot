# CEX-002 Review 413 — Accept Candidate and Authorize Direct Raw Recovery

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept record 412 and its v3 candidate; replace the unimplemented linked-generation recovery with ADR-0034 direct recovery
- **Gate 2:** `IN_PROGRESS`
- **Next actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Review decision

Record 412 and commit `eb730d0659bd9b13a2ef8825d9cf82d327b55e31` are accepted as the
exact terminal publication of the completed v3 listing candidate. Both passes completed at 2,094
pages and 1,308/1,308 prefixes. The accepted candidate identities are:

- candidate semantic SHA-256: `a064fec30853eba8792052e65bbb6223224e23fc7f57879ef01291f7e825ad1b`;
- stable reachability SHA-256: `b2170ece22b5aedf8a5181c4000ef38723e26d1874d02803319bf3e8be89485b`;
- stable pending-facts SHA-256: `13cfb7440836a7a97afe069a76282c59e8ea901b863281043767086a9a006114`;
- manifest SHA-256: `4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d`;
- rows: 51,275; and
- listed bytes: 9,207,379,061.

The candidate is accepted as fixed recovery authority. Gate 2 is not yet accepted.

ADR-0034 supersedes ADR-0031's unimplemented corrected-source, transition-tool, and linked-
generation prerequisites. This is a deliberate architecture correction: those mechanisms
protected internal receipt lineage but prevented retrieval of already identified, provider-
checksummed bytes. No acquisition source or test correction is authorized.

The earlier uncommitted Review-413 Sol authorization never became repository authority and is
discarded by this publication. The interrupted direct retrieval under
`data/harmonic_trader_source` is disclosed as unauthorized staging: 1,815 files occupied about
8.1 GiB when inspected, and no related process remained live. It may be reused only under the
per-file checks in ADR-0034.

## Exact reviewer publication paths

The reviewer may stage, commit, and push only these four governance/review paths:

1. `docs/adr/0034-direct-pending-raw-recovery.md`
2. `research/sprint_004/413_CEX002_RECORD412_ACCEPTANCE_AND_DIRECT_RECOVERY_AUTHORIZATION.md`
3. `docs/handoff/CURRENT_TASK.md`
4. `tickets/CEX-002.md`

No source, test, data, acceptance-suite, or unrelated dirty path belongs to the reviewer
publication.

## One-way Hermes authorization

After the exact reviewer publication is on `origin/main`, Hermes is authorized for one resumable
direct-recovery session under ADR-0034.

Hermes must:

1. require clean staging, `HEAD == origin/main`, no live acquisition/planner/download process,
   an intact v3 locator/manifest, and the exact candidate identities above;
2. preserve every unrelated modified or untracked path;
3. rename `data/harmonic_trader_source` to `data/cex002_recovery` only when the former exists and
   the latter is absent, stopping if both exist;
4. derive the fixed URL, relative-path, size, and provider-checksum inputs from the accepted
   manifest using standard `gzip` and `jq` only;
5. validate or resume existing staging files and fetch only absent/incomplete accepted rows with
   standard resumable `wget`, never exceeding eight concurrent requests;
6. quarantine rather than delete a complete mismatching file;
7. finish by checking all 51,275 exact sizes and all provider SHA-256 values, with exact total
   bytes 9,207,379,061; and
8. publish the terminal outcome as record 414, update only the ticket and current-task control
   paths, stage only those exact evidence/control paths, commit, and push.

Hermes may rerun the same idempotent recovery command after an interruption within this one
session. It must stop and publish the exact blocker if a remote object does not match the accepted
size or checksum. It may not edit source/tests, mutate generation 0, relist Binance, create a
planner/downloader/state database, normalize data, run a model, or begin a later ticket.

