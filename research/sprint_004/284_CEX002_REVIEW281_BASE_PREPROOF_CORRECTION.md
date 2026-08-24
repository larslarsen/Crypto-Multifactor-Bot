# CEX-002 Review-281 Base Preproof Correction

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** correct impossible self-referential base preproof only
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** not accepted; review-281 execution pending
- **Next ticket:** `NONE`

## Control defect

Review 281 required `HEAD == origin/main == ee3f9d760466662454571081e7571b5eb33b71b7`,
then the reviewer committed and pushed review 281 at
`15a03cbe7c1718c0d842186368dcd29c889899a8`. The publication necessarily advanced the
branch, so the exact-base clause could never pass. Hermes correctly stopped without
staging, testing, executing, recording, committing, or pushing.

## Corrected preproof

This record supersedes only review 281 section 1's exact-HEAD sentence. Require:

1. `HEAD == origin/main`;
2. `git merge-base --is-ancestor 15a03cbe7c1718c0d842186368dcd29c889899a8 HEAD`
   exits 0; and
3. `research/sprint_004/281_CEX002_CAPACITY_ATTESTATION_SOURCE_ACCEPTANCE_AND_EXECUTION.md`
   has SHA-256 `388f5cf3db2bf38822d729fff4cd42c7232845320da0d49b07be7e31e2f99d4a`.

Do not require `HEAD` to equal either `ee3f9d7` or `15a03cb`: this correction's own
publication advances `HEAD` again. Every accepted source/test/CLI/receipt hash, the
15-function count, output path 282, commands, stop conditions, record 283, Git scope, and
prohibition in review 281 remains exact and unchanged.

Hermes must now execute review 281 under this corrected preproof, publish the required
result, and stop for reviewer inspection. Gate 2 remains not accepted and next ticket
remains `NONE`.

The reviewer may stage, commit, and push exactly this correction, current task, and
ticket. Developer source/test paths, attestation evidence, execution record, and unrelated
dirty work are excluded.
