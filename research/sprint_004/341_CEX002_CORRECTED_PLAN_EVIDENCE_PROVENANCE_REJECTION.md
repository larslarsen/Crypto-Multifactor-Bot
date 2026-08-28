# CEX-002 Corrected Plan Evidence Provenance Rejection

- **Date:** 2026-08-27
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** plan remains accepted; record-339 provenance correction rejected
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress; acquisition remains unauthorized
- **Next ticket:** `NONE`

## Stable plan acceptance

Review 340's corrected-plan semantic disposition is unchanged. The one installed plan passes
the v2 identity, scope, retained-credit, typed-gap, zero-fact, SQLite, and capacity contract.
Do not rerun, delete, repair, or replace it.

Hermes amended only record 339 in pushed commit
`3df23830c2b2e8f630c1aa12fad95d29984bde97`. The amended record SHA-256 is
`7413bbc90eb2c41b7de030229b66ba286e07cd57bf1272879676e7287f19f684`, 129 lines.
It supplies the missing semantic receipt blocks and full seven-entry inventory values, but it
does not satisfy Review 340's exact provenance contract.

## Exact rejection

Two defects remain:

1. The receipt block is labeled a verbatim rendering with whitespace preserved, but it is
   single-line minified JSON. Production `canonical_json` is sorted, two-space-indented JSON
   with a trailing newline, and the receipt is recorded as 5,007 bytes. The displayed block is
   not the exact canonical receipt body it claims to be.
2. The listed `find ... -printf` commands cannot produce the following rendered inventory:
   they do not compute SHA-256, emit the stated type/device labels, or emit the displayed field
   order. The exact Python SQLite command/script is also omitted. Therefore the record does not
   provide the exact inspection commands corresponding to its claimed outputs.

The inventory facts themselves remain consistent. This rejection is only about false verbatim
and command-provenance claims.

## Final record-only correction

Hermes must edit only:

- `research/sprint_004/339_CEX002_CORRECTED_GATE2_REAL_PLAN_EXECUTION.md`.

Make exactly these corrections:

1. Replace the minified receipt block with the actual canonical representation. The already
   published JSON value may be parsed and serialized with
   `json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"`; prove its encoded
   length is 5,007 and SHA-256 is
   `c0b973b2c794804b543225c119eeb8a9fb17798473774859fa92abacca7b9167` before labeling
   it verbatim. This requires no plan-state read if the published semantic JSON is complete.
2. Replace the misleading command list with the exact complete command or script text that
   actually produced each receipt, SQLite, capacity, and inventory output. Each published
   output must be attributable to that text. Do not claim raw `find` output was already
   labeled or hashed if a separate transformation/hash step produced it.
3. If the actual command text was not retained, run only the minimum Review-340-authorized
   read-only standard-library reconciliation needed to reproduce the same facts, and publish
   the complete command/script and its complete bounded output. Do not change correct fact
   values merely to obtain different output formatting.
4. State accurately whether read-only reinspection was used in this final correction. Preserve
   the original plan command/timing/output, all accepted facts, and the mutable-SQLite
   evidence-only label.

Do not invoke the acquisition module or any repository CLI. Do not write, create, rename,
delete, chmod, repair, checkpoint, reconcile WAL, rerun `plan`, invoke `verify`/`acquire`, or
access the retired tree.

Use explicit Git-write escalation. Stage only record 339, prove that exact cached one-path set,
run `git diff --cached --check`, commit with message
`fix CEX-002 corrected plan evidence provenance`, push `main`, and stop for review. Return the
record SHA-256, line count, correction commit, and reinspection disposition.

No source/test/governance edit, Ruff, pytest, control, planning, acquisition, network access,
later gate, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or
next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data, and
unrelated dirty work are excluded.
