# EVD-001 - SR PRODUCTION SOURCE TASK

**Ticket:** `tickets/EVD-001.md`
**Actor:** Sr Dev - Grok Build
**Status:** AUTHORIZED - SOURCE ONLY
**Next ticket:** `NONE`

## Assignment

Complete the self-contained EVD-001 production behavior using the existing migration-0002 schema,
models, canonical hashing utilities, repository conventions, and Typer CLI structure.

## Required behavior

- Preserve immutable hypothesis versions and evidence content identities; no update/delete path.
- Build deterministic, idempotent evidence snapshots from canonical linked state at an explicit
  `as_of`, with stable ordering and canonical hashes.
- Keep decisions append-only; corrections/reopens reference prior decisions rather than mutate.
- Reject `SUPPORTED` or `REPLICATED` when the cited snapshot contains only literature/legacy
  evidence or when promotion evidence has causal or point-in-time integrity `FAIL`.
- Produce byte-stable JSON and deterministic Markdown current-state exports.
- Import `research/evidence/hypotheses.yaml` safely and idempotently through validated models and
  existing repository registration paths.
- Expose the ticket-required list/show/register/export operations and necessary snapshot,
  decision, and seed operations through the existing CLI conventions.
- Reuse migration 0002 and `canonical_json_bytes` / `content_sha256`; no ad-hoc identity scheme.

## Boundaries

- Production source only under `src/cryptofactors/evidence/` and, if needed, the existing CLI
  registration file.
- Do not modify migrations, schemas, research content, tests, tickets, reviews, handoffs, or
  architecture records.
- Do not implement or expose `hypothesis_experiment_link`, compute experiment fingerprints,
  aggregate performance scores, or import higher layers.
- If an existing public model makes a required invariant impossible without schema or architecture
  change, stop and report the exact blocker rather than inventing compatibility behavior.

## Stop condition

Return the production source drop for reviewer inspection and stop. Jr integration is not
authorized until reviewer source approval.
