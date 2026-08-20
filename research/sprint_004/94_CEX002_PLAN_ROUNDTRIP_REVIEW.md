# CEX-002 Plan Round-Trip Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed commit: `c2b91d9baade7f56223fb266ec0ba1214fe72582`

Reviewed execution record:
`research/sprint_004/93_CEX002_GATE1_PLAN2_EXECUTION.md`

## Decision

**ACCEPT HERMES'S MIGRATION STOP; REJECT THE PLAN SERIALIZATION CONTRACT.**

Hermes executed review 92's one-time migration exactly once. Every pre-migration
identity and count assertion passed, and the in-memory lock reached version 2 with the
same plan digest. The exact-plan assertion then failed before `flush()`, so the durable
lock correctly remains byte-identical version 1 at SHA-256
`45c2207934952997398f1e8a90865094c3e1fea9dec5654db3bfba21e94720bf`.
No real run was authorized after that failure.

The failure exposes a production serialization defect. `SamplePlan.to_dict()` uses
`dataclasses.asdict` on `SamplePlanEntry`, which retains `products` as a tuple. Persisted
JSON reloads the same value as a list, so
`SamplePlan.from_dict(stored).to_dict() != stored` even though canonical JSON bytes and
the plan digest are equivalent. An immutable versioned plan must have one JSON-native,
exactly round-trippable document representation.

## Bounded Grok Correction

Sr Dev - Grok Build using Grok 4.6 High may modify only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Make `SamplePlan.to_dict()` emit `products` as a JSON-native list for every entry. Preserve
the internal immutable tuple type and every existing validation, selection, budget,
ledger, membership, storage, Coinalyze, and transfer behavior.

Add focused test source proving all of the following with at least one multi-product
entry and blocked-plan evidence:

- every serialized entry's `products` value is a list;
- `json.loads(json.dumps(plan.to_dict())) == plan.to_dict()`;
- `SamplePlan.from_dict(persisted).to_dict() == persisted`; and
- `plan_content_digest` is identical before and after the persisted round trip.

Do not weaken the review-92 exact equality assertion or change `SamplePlan.from_dict()` to
retain mutable internal lists. Do not edit the migration authorization, CLI, fixtures,
data, reports, or repository records.

Grok performs no tests, network/data run, integration, Git operation, commit, push,
purchase, deletion, plan migration, catalog mutation, Gate 2, Nautilus, or Harmonic
Trader work. Stop for reviewer source inspection with exact SHA-256 hashes for the two
authorized paths.

## Publication Set

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/94_CEX002_PLAN_ROUNDTRIP_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.

## Disposition

CEX-002 and Gate 1 remain `IN_PROGRESS`. Plan migration, another real run, Gate 2,
Nautilus, every other ticket, and Harmonic Trader work remain unauthorized. The 63
unresolved historical candidates and physical storage shortfall remain untouched. Next
ticket remains `NONE`.
