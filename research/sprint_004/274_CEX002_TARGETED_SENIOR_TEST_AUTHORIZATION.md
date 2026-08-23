# CEX-002 Targeted Senior Test Authorization

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** authorize one targeted senior source-feedback test
- **Authorized actor:** Sr Dev - Sol High
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Governance decision

At the owner's explicit direction, `AGENTS.md` and
`docs/engineering/DEVELOPMENT_ROLES.md` now permit the reviewer-selected senior actor to
run one explicitly enumerated targeted test command for the actor's own bounded corrective
drop. The exception exists to catch deterministic source defects before a separate Hermes
integration handoff. It does not transfer integration, acceptance-suite, evidence-record,
Git, commit, push, data, publication, or reviewer authority to the senior actor.

## Sol High authorization

Review 273's exact two-line ordering correction remains unchanged. After editing only
`tests/acquisition/test_binance_usdm_harmonic_sizing.py`, Sol High is additionally
authorized to run this command exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'test_the_v3_capacity_terms_reconcile_exactly'
```

On exit 0, stop and report the command, exit status, output, corrected test SHA-256, frozen
production/CLI hashes, and 161-test count. On the first nonzero result or timeout, make no
further repair or rerun; stop and report the exact failure. Sol may run no other pytest,
Ruff, control, sizing, qualification, network, or data command and may not use Git or edit
repository records.

Hermes remains the sole integration, full focused-validation, Ruff, sizing, evidence,
record, Git, commit, and push owner after reviewer static acceptance. Receipt 258,
integration, sizing, acquisition, normalization, catalog, NautilusTrader, Harmonic Trader,
PAPER/LIVE, and later work remain unauthorized. Gate 2 remains not accepted and next
ticket remains `NONE`.

The reviewer may stage, commit, and push exactly:

- `AGENTS.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `research/sprint_004/274_CEX002_TARGETED_SENIOR_TEST_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test paths and unrelated dirty work are excluded.
