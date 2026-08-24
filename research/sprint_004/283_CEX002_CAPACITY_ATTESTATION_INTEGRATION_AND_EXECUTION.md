# CEX-002 Capacity Attestation Integration and Execution

- **Date:** 2026-08-24 UTC
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Authorization:** Review 281, repaired by review 285
- **Gate 2:** not accepted
- **Next ticket:** `NONE`

## Preproof and integration

Review 285 requires synchronized `HEAD == origin/main`, review-281 commit
`15a03cbe7c1718c0d842186368dcd29c889899a8` as an ancestor, the accepted seven hashes,
15 capacity-attestation tests, no running sizing/attestation process, and no existing
attestation 282. All checks passed. The three accepted capacity-attestation paths were
staged without rewriting them:

- `src/cryptofactors/acquisition/binance_usdm_capacity_attestation.py`
- `scripts/research/attest_binance_usdm_harmonic_capacity.py`
- `tests/acquisition/test_binance_usdm_capacity_attestation.py`

The accepted sizing source, test, CLI, and receipt 258 were rehashed and remained
byte-identical. The accepted capacity source/test/CLI hashes are respectively
`34973e6f801ef3a16e82c3333c01fb1ee81fad357810bc28fdd5eaabf18995ec`,
`09c9663613a4addf7080d5d84f0470926e4aa86915094b2c4d21d27e6ac73cf9`, and
`e5195b967d83f3f1ab336f342c512ce375e80dbc66f67cb754acc2b86244ead5`.

## Validation

The exact focused command was run once and passed with exit 0; all 15 tests passed:

```text
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m .venv/bin/python -m pytest tests/acquisition/test_binance_usdm_capacity_attestation.py -q --tb=short
```

The exact Ruff command was run once and passed with exit 0 (`All checks passed!`).

## Real attestation

The authorized command was run exactly once after validation:

```text
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m .venv/bin/python scripts/research/attest_binance_usdm_harmonic_capacity.py --store-root data/cex002_qualify --attestation-path research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json
```

- Start UTC: `2026-08-24T03:59:45.274929334Z`
- End UTC: `2026-08-24T03:59:46.598046583Z`
- Elapsed: `1.323` seconds
- Exit status: `0`
- Complete stderr:

```text
cex002_gate2_capacity_attestation_v1 written at research/sprint_004/282_CEX002_GATE2_CAPACITY_ATTESTATION.json
attestation_sha256=0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25 attestation_bytes=3794
storage_preflight_state=sufficient total_future_storage_bytes=197469027033 post_publication_available_bytes=289455230976
note: this attestation authorizes no acquisition and accepts no gate
```

Attestation 282 is a regular file, not a symlink. Its SHA-256 is
`0e12333d94b7ce2aea373c7f4bac7887a5f72c6a710cb9e697c5ffb660c22b25` and its exact
length is 3,794 bytes. Schema is `cex002_gate2_capacity_attestation_v1`; generated UTC
is `2026-08-24T03:59:46.466165+00:00`. The receipt basis is receipt 258 at
`research/sprint_004/258_CEX002_GATE2_STORAGE_SIZING_V3.json`, device `dev:64513`,
receipt SHA-256
`3995a5072a7d84baecae677ceff6e1c7af9dd076daadec04a31717ffc8f16589`, and stable
receipt identity `686fccf7cde695a07e07d3672ee5f07add6549400b1ec0ab05c47c8c51d0fab8`.

Filesystem evidence: pre-write available `289455235072` bytes; after-staging available
`289455230976` bytes; post-publication available `289455230976` bytes; attestation
durable length `3794` bytes; receipt/store/output device `dev:64513`.

Capacity reconciliation:

- New Binance raw: `20351715427`
- New Coinalyze raw: `30580702`
- Typed normalized partitions: `108082947883`
- Catalog/manifest bundle: `5556368003`
- Bounded temporary work: `5556368003`
- Stable requirement: `139577980018`
- Operating reserve: `57891047015`
- Total requirement: `197469027033`
- Post-publication available: `289455230976`

The stable components sum exactly to `139577980018`; the reserve recomputes as
`ceil(289455235072 / 5) = 57891047015`; and stable requirement plus reserve equals the
recorded total. The total is below post-publication availability, so the measured state
is `sufficient` with no blockers. The attestation's authorization object explicitly says
acquisition is unauthorized and Gate 2 is not accepted.

## Handoff

The authorized integration, validation, and one real attestation are complete. Record 283
and attestation 282 are returned to the Lead Quantitative Finance Researcher/Engineer for
review. No acquisition, normalization, catalog publication, or later-ticket work was
performed. Next ticket remains `NONE`.
