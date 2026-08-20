# CEX-002 Gate 1 Stable-Authority Execution Review

Date: 2026-08-20

Reviewer: Lead Quantitative Finance Researcher/Engineer

Reviewed commit: `6f7ff87146eb46b6a1dbfb6f7a8eb264a3e3347e`

Reviewed execution record:
`research/sprint_004/88_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION.md`

Reviewed report:
`research/sprint_004/62_CEX002_GATE1_SOURCE_PROCUREMENT.json`

## Decision

**REJECT GATE 1 EVIDENCE; ACCEPT HERMES'S INTEGRATION AND STOP DISCIPLINE.**

The focused CEX-002 suite, atomic-download suite, Ruff, repository control, and committed
whitespace check passed. Both bounded real runs completed against the preserved store,
reused the listing checkpoint and all 100 retained samples without a new transfer, and
published an honest blocked matrix. The execution also exposed two source defects that
must be corrected before another real run.

Gate 1 remains `IN_PROGRESS`. Gate 2, acquisition, Nautilus integration, every other
ticket, and Harmonic Trader work remain unauthorized. Next ticket remains `NONE`.

## Findings

### 1. Semantic resume identity failed on a duplicated volatile capacity value

The required two-run assertion raised `AssertionError`. `drop_identity_volatility`
correctly excludes `gate2_feasibility`, but the same `df`-derived shortfall is copied into
`incidents[18].note`, which remains in the identity payload. The two reports therefore
differ only because local free space moved by 75,083,776 bytes.

Keep the exact available and shortfall byte values in `storage.gate2_feasibility` and in
the CLI output. Make the storage incident note stable and categorical, for example that
local capacity is insufficient and exact execution-plane values are in the feasibility
record. Do not broadly exclude incidents, incident notes, or storage classification from
semantic identity.

Add a focused test that runs with two different mocked local-capacity values and proves:

- exact feasibility values differ;
- both reports retain the `insufficient` class and a stable storage incident; and
- `identity_bytes(first) == identity_bytes(second)`.

### 2. Coinalyze rejects a valid provider identity already carrying `_PERP`

The real `future-markets` response includes native `AAVEUSD_PERP` with provider symbol
`AAVEUSD_PERP.A`. `coinalyze_perp_symbol` blindly constructs
`AAVEUSD_PERP_PERP.A`, so full-market identity validation aborts before the declared
BTCUSDT/ETHUSDT qualification samples.

Canonical mapping must support both observed native forms without weakening validation:

- `BTCUSDT` maps to `BTCUSDT_PERP.A`;
- `AAVEUSD_PERP` maps to `AAVEUSD_PERP.A`.

Continue validating every applicable Binance perpetual row and rejecting provider-label
mismatches and duplicate native identities. Add focused positive coverage for an
already-suffixed native and negative coverage for its mismatched provider label.

### 3. The evidence is not a Gate 1 pass after those two corrections

The report still contains 63 archive-only candidates without affirmative official
contract-type or realized-funding evidence: 46 dated-delivery-shaped names and 17
settlement-suffixed names. Their spelling is an audit hint, not authority, and no
developer may promote or exclude them from spelling. They remain blocking unless exact
official evidence is retained and validated.

The exact inventory also reports 8,662,211,210,669 bytes of deduplicated compressed raw
source data, 8,661,196,012,122 projected new bytes, and an approximately 8.47 TB local
shortfall. That is a real Gate 2 resource blocker, not permission to reduce the universe,
drop derivatives fields, discard provenance, or run a price-only substitute.

Hermes's detached launcher did not preserve the two raw process exit statuses. The next
authorized execution must record the actual exit status of each real invocation; terminal
text or a prior run's CLI mapping is not a substitute for the required command exit code.

## Bounded Grok Correction

Sr Dev - Grok Build using Grok 4.6 High is authorized to modify only:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py`; and
- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

Implement only findings 1 and 2 and their focused test source. Preserve all accepted
membership, immutable-plan, ledger, checkpoint, source/coverage, and transfer semantics.
Do not reclassify the 63 unresolved candidates, change the ticket scope, hide storage
requirements, or edit the CLI, fixtures, data, reports, or repository records.

Grok performs no tests, network/data run, integration, Git operation, commit, push,
purchase, deletion, catalog mutation, Gate 2, Nautilus, or Harmonic Trader work. Stop for
reviewer source inspection with exact SHA-256 hashes for the two authorized paths.

## Publication Set

The reviewer may stage, commit, and push exactly:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/89_CEX002_GATE1_STABLE_AUTHORITY_EXECUTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

No source, test, fixture, data, generated report, or unrelated dirty path belongs to this
publication. The reviewer executes no tests or acceptance commands.
