# CEX-002 Review 473 - Realized Funding Acceptance

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept `binance_usdm_funding_realized`
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - five of eleven required products accepted
- **Next required actor:** Lead Quantitative Finance Researcher/Engineer
- **Next ticket:** `NONE`

## Acceptance

Review 473 accepts integration commit `e8a4443852606786d3f14ab533bbf671786c4c5e`, publication
commit `1071bec89db2d1ef237e5c288304d28b8bc9c71c`, and the real
`binance_usdm_funding_realized` product. The integrated source, CLI, and test identities match
Review 471. Hermes's ordered results passed: 66/66 focused tests, Ruff, and repository control.

The one authorized local run exited 0 after approximately 6 minutes 46 seconds. Completion identity
`57628164f19d182164b6058d9e51f794430cc918706c088f430e1c01d2898522` binds 2,683,024 observed
funding events in 21,035 partitions and 21,035 lineage records, with zero collapsed, excluded,
conflicting, inferred, or rounded events. The observed interval histogram reconciles exactly to the
product total. The completion is sole and staging is empty.

The reviewer independently reproved the completion-file hash, every descriptor-referenced Parquet
hash, every descriptor-referenced lineage hash, actual file counts, and descriptor row sums. All
21,035 Parquet hashes and 21,035 lineage hashes passed. Descriptor partition rows and physical rows
both sum to 2,683,024; collapsed rows sum to zero. No acceptance command or data mutation was
performed by the reviewer.

This is the fifth accepted Gate-3 product. The data was produced from the already downloaded local
generation-0 files; no acquisition or network download occurred.

## Record corrections

Record 472's detailed pre-run capacity value is `556,026,527,744` bytes. Its abbreviated text in
the two control files transposed the final digit to `742`; this review corrects those two summaries.
Record 472 also stated that both actor fields returned to the reviewer but left their header values
at Hermes. This review corrects both headers. These are publication defects only and do not change
the accepted code, command outcome, or data.

Gate 3 and CEX-002 remain `IN_PROGRESS`. No next product, experiment, model, Harmonic Trader work,
PAPER, LIVE, or next ticket is authorized by this acceptance.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/473_CEX002_REALIZED_FUNDING_ACCEPTANCE.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All source, test, data, runner, and unrelated dirty paths remain unstaged and untouched.
