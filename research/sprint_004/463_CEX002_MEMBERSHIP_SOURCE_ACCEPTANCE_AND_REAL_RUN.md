# CEX-002 Review 463 - Membership Source Acceptance and Real Run

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the corrected membership source drop for Hermes integration and one real run
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - three required products accepted
- **Next required actor:** Jr Dev - Hermes
- **Next ticket:** `NONE`

## Accepted unintegrated source

Static review accepts the corrected three-path membership drop at these exact identities:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_membership.py` | 761 | `7e14254cd8275521a52ab88faf747f9c72fd0fd51cc2a7d97d4f405af723ffc4` |
| `scripts/research/normalize_binance_usdm_membership.py` | 46 | `cd762f2b673bc2beca322da61a8ae6358d51f99cfe819ebf6313f330414140bd` |
| `tests/ingest/test_binance_usdm_membership.py` | 443 | `5c597ba2e43f25193c6c64dfb1acbe733f39f49aacfbf304f870bf31455fb110` |

Sol's one Review-462 command passed all 27 cases. The correction independently validates the full
exchange-info response digest and the per-contract snapshot digest without equating them. It
preserves the accepted snapshot in the typed row and refuses missing, uppercase, short, and
non-hex snapshot identities. Static inspection accepts the pinned three-authority validation,
1,008/771/237 and 698/73 equations, exact 24-column schema, funding-only nulls, native-reference
state, per-symbol content addressing, no-clobber publication, completion-last visibility, and
deterministic replay.

The output root `data/.cex002_perpetual_membership` is currently absent. Observed available
capacity is 568,669,851,648 bytes, above the frozen 110,648,021,942-byte remaining-release floor.
The source is accepted for integration and one real run, not yet as a completed product.

## Hermes integration

Hermes must prove `HEAD == origin/main` at this review's publication commit and reprove all three
accepted hashes and line counts. Hermes then runs these commands in order, stopping on the first
nonzero result:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_membership.py -q --tb=short
.venv/bin/python -m ruff check src/cryptofactors/ingest/binance_usdm_membership.py scripts/research/normalize_binance_usdm_membership.py tests/ingest/test_binance_usdm_membership.py
python3 scripts/check_repo_control.py
```

No patch is authorized. If all three pass, Hermes stages exactly the three accepted developer
paths, commits them with message `CEX-002: integrate perpetual membership normalizer`, pushes, and
proves `HEAD == origin/main`. No unrelated path is staged.

## One real membership run

After integration, Hermes reproves that the output root is absent and not a symlink and that
`df -B1 --output=avail data` is at least 110,648,021,942 bytes. It then executes exactly once in
the foreground and remains attached until terminal:

```bash
PYTHONPATH=src .venv/bin/python scripts/research/normalize_binance_usdm_membership.py \
  --report research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json \
  --contract-metadata data/cex002_qualify/cex002_official_contract_metadata.json \
  --sizing research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json \
  --output-root data/.cex002_perpetual_membership
```

There is no wrapper, detach, retry, replay, second invocation, or polling loop. A nonzero result is
recorded exactly and stops without patching or cleanup.

On success Hermes records the exact stdout, exit code, runtime, pre/post available bytes,
completion path and SHA-256, schema SHA-256, normalizer source SHA-256, classification/member/
exclusion and detailed/funding equations, partition/lineage counts and bytes, empty staging state,
and sole-completion state. It verifies the descriptor-referenced paths exist beneath the hidden
root and that every referenced content digest matches its filename; the production command's
successful built-in schema/row/path verification is stated separately from these terminal
inventory checks.

Hermes publishes `research/sprint_004/464_CEX002_MEMBERSHIP_INTEGRATION_AND_REAL_RUN_RECORD.md`,
updates `docs/handoff/CURRENT_TASK.md` and `tickets/CEX-002.md`, returns both next-actor fields to
the reviewer, stages exactly those three record paths, commits, pushes, proves
`HEAD == origin/main`, and stops.

No acquisition, network request, source/test correction, deletion, cleanup, other product,
coverage product, bundle, catalog transaction, NautilusTrader check, experiment, model, Harmonic
Trader, PAPER, LIVE, or next-ticket work is authorized.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/463_CEX002_MEMBERSHIP_SOURCE_ACCEPTANCE_AND_REAL_RUN.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer, data, runner, acceptance-command, and unrelated dirty paths remain unstaged and
untouched until Hermes performs the exact workflow above.
