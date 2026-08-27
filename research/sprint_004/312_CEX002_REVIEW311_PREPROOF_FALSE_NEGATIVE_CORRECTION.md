# CEX-002 Review-311 Preproof False-Negative Correction

- **Date:** 2026-08-26
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** silent compound-preproof stop accepted; facts independently proved
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Accepted stop and independent proof

Hermes ran a compound review-311 preproof which exited 1 without diagnostic output, then
correctly stopped before staging, committing, pushing, validation, source repair, or other
mutation.

The reviewer checked each review-311 predicate separately and proved:

- `HEAD == origin/main == 26002e5efa4c789e0b06ab4dbe446f16b47f94cc` before this correction
  publication;
- review 311 exists in that `HEAD` tree;
- acquisition source SHA-256 is
  `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`;
- CLI SHA-256 is
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- test SHA-256 is
  `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`;
- the test path is clean;
- the acquisition source and CLI are the exact set of modified Gate-2 paths; and
- no path is staged.

The filesystem returns those two modified filenames in CLI/source lexical order, while review
311 lists source/CLI. An order-sensitive shell comparison can therefore produce the observed
silent false negative even though the required set is exact. Path-set proof is order
independent. No source issue or missing prerequisite exists.

## Corrected Hermes continuation

The independent reviewer proof above satisfies review 311's preproof. Hermes must not rerun
the failed compound preproof. Begin with review 311's exact integration staging step after
confirming only synchronized `HEAD == origin/main`; do not impose a literal ordering on a Git
path list.

After staging, validate the cached path **set** by proving it has exactly two entries and each
of these occurs exactly once:

- `scripts/research/acquire_binance_usdm_harmonic_release.py`
- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`

Then continue review 311 unchanged: cached diff check, integration commit/push, and the four
offline validation commands exactly once in order under the original stop rule. If they all
pass, publish the successful execution evidence as exactly:

- `research/sprint_004/313_CEX002_GATE2_OFFLINE_VALIDATION_EXECUTION.md`

Record 313 replaces review 311's reserved record 312 because this correction occupies record
312. Use the same evidence contract and commit message specified in review 311, then run the
ticket's exact final `git diff --check` once and stop.

No source repair, additional validation command, real `plan`, `acquire`, or `verify`
operation, network access, data/state mutation, qualification, sizing, capacity command,
Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, PAPER/LIVE, or next-ticket
work is authorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this correction,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer source/test paths,
state/data/evidence, and unrelated dirty work are excluded.
