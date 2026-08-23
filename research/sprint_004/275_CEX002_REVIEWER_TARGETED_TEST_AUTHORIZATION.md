# CEX-002 Reviewer Targeted Test Authorization

- **Date:** 2026-08-23
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** authorize one reviewer source-feedback test after exact Sol inspection
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Static inspection

The reviewer inspected Sol High's completed review-273 drop once at:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py` | `d4afaa6285733c10311560b9fd68b223ab31fa90b1293a71871ea262daa82f5b` (unchanged) |
| `tests/acquisition/test_binance_usdm_harmonic_sizing.py` | `3b5acf85c5ee5aab891f9b9622e3cc7e86e0c2df2b630812f6f26e9bce20580a` |
| `scripts/research/size_binance_usdm_harmonic_release.py` | `36740c926c32e4973bb31dcb570d3c69b89f9f343d52eb8aed3d33d359d7b23c` (unchanged) |

The diff moves the existing `liquidation` assignment immediately before its first use and
removes only the later duplicate. It changes no assertion, equation, fixture, or other
source, preserves 161 test functions, and passes static whitespace validation. This is the
exact review-273 correction.

## Reviewer targeted-test governance

At the owner's explicit direction, `AGENTS.md` and
`docs/engineering/DEVELOPMENT_ROLES.md` now permit the reviewer to run one explicitly
enumerated targeted test against an unintegrated developer drop solely for immediate
source-review feedback. The result neither integrates nor accepts the drop. Hermes retains
focused/full validation, Ruff, sizing, evidence, repository records, Git, commit, and push.

After this governance publication is committed and pushed, the reviewer is authorized to
run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_sizing.py -q --tb=short \
  -k 'test_the_v3_capacity_terms_reconcile_exactly'
```

On exit 0, the reviewer publishes source acceptance and routes Hermes. On the first
nonzero result or timeout, the reviewer publishes the complete failure and routes a
correction without rerunning. No reviewer Ruff, control, focused/full suite, sizing,
qualification, network, data, integration, source edit, evidence edit, or acceptance
command is authorized.

Receipt 258, integration, sizing, acquisition, normalization, catalog, NautilusTrader,
Harmonic Trader, PAPER/LIVE, and later work remain unauthorized. Gate 2 remains not
accepted and next ticket remains `NONE`.

The reviewer may stage, commit, and push exactly:

- `AGENTS.md`;
- `docs/engineering/DEVELOPMENT_ROLES.md`;
- `research/sprint_004/275_CEX002_REVIEWER_TARGETED_TEST_AUTHORIZATION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

Developer source/test paths and unrelated dirty work are excluded.
