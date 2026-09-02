# CEX-002 Review 462 - Membership Real-Authority Static Rejection

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject the unintegrated membership drop and authorize one bounded correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS` - three required products accepted
- **Next required actor:** Sr Dev - Codex Sol on GPT-5.6-sol High
- **Next ticket:** `NONE`

## Capacity disposition

The owner's cleanup increased observed available capacity to 568,669,851,648 bytes. This is above
Review 461's frozen 110,648,021,942-byte remaining release requirement, so the capacity blocker is
closed without a storage-architecture amendment, reserve reduction, or repository cleanup by an
agent. The accepted CEX authorities and three completed product roots remain present. This review
does not characterize, inspect, restore, or otherwise act on the owner's deleted material.

## Source-review result

Sol's Review-461 drop has the exact authorized three-path scope and reported identities. Its one
authorized targeted command passed 23 cases. Static review nevertheless rejects the drop because
production line 280 requires the contract-metadata `symbol_snapshot` digest to equal an evidence
record's `response_sha256`, and the test at lines 280-288 freezes that false equality.

These hashes identify different accepted objects. For the first accepted real identity, `0GUSDT`,
the qualification evidence carries the complete exchange-info response SHA-256
`f5628c9d503d860f9579df289b99a84bf409c72e21e48555ad89b893e9974124`, while the accepted
contract-metadata `symbol_snapshot` is
`9add90a7aadbde25ebd6304cd58898ddb0acffdffcee347b193523283d6d3f6b`. Both parent authorities
are independently pinned and mutually bound by the accepted sizing receipt. Requiring equality
would reject the real authority before publishing the first detailed membership row.

No data was run or mutated. The CLI is byte-acceptable and needs no correction. The rest of the
drop remains unintegrated and unaccepted pending the correction below.

## Exact correction authorized

Sol High may edit exactly:

- `src/cryptofactors/ingest/binance_usdm_membership.py`; and
- `tests/ingest/test_binance_usdm_membership.py`.

Production must continue requiring a present, lowercase 64-hex contract snapshot for every
detailed identity and valid detailed evidence provenance, but it must not equate the per-contract
snapshot digest with the whole-response evidence digest. The existing test that requires equality
must instead prove that two distinct valid identities are accepted and the exact
`contract_snapshot_sha256` value is preserved in the typed row; missing or malformed contract
snapshot values must still fail closed. No other behavior or path may change.

Sol may run exactly this targeted command once after the correction:

```bash
.venv/bin/python -m pytest tests/ingest/test_binance_usdm_membership.py -q --tb=short
```

Sol stops on the first nonzero result and reports the exact output without patching or rerunning.
No CLI edit, real-data run, integration, repository record, Git, network, data mutation, cleanup,
other product, bundle, catalog, experiment, model, Harmonic Trader, or next-ticket work is
authorized. The corrected drop stops for reviewer inspection.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception, this review publishes exactly:

- `research/sprint_004/462_CEX002_MEMBERSHIP_REAL_AUTHORITY_STATIC_REJECTION.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

All developer, data, runner, acceptance-command, and unrelated dirty paths remain unstaged and
untouched.
