# CEX-002 Gate 1 Resumable Execution Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT FAILURE INTERPRETATION; KEEP PRODUCTION SOURCE ACCEPTED; AUTHORIZE TEST-ONLY CORRECTION**

## Reviewed state

Committed branch before this review:
`HEAD == origin/main == 33d1a573f31dcbdce2ea4310686066a3fa478a8d`.

Hermes published only
`research/sprint_004/71_CEX002_GATE1_RESUMABLE_EXECUTION.md` at that commit. The record
reports the first review-70 command at 77 passed / 1 failed, a deterministic isolated
rerun of the same failure, no later command, no source commit, no network run, and no
mutation of the retained 691 MiB store. That is the correct execution stop behavior.

The three uncommitted reviewed paths still match review 70 exactly:

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `3e8d14887f0f9e273a3fc00c3fd1b5d640cf01ad4214049a050df8425a5480d0` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `40d944a8149e22cd917fa3097009c53307bc5c9614ef35139f4317b1843e6f8a` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `9e75242b5ef9c67e5199dac24efe1385c43abdbdb8419cc913f9ec14c40b0aa2` |

The control plane remained stale after publication: both `docs/handoff/CURRENT_TASK.md`
and `tickets/CEX-002.md` still named Hermes even though record 71 explicitly returned the
failure to the reviewer. This review corrects that routing state.

## Finding

The failed assertion in
`test_abort_after_completed_sample_resumes_missing_objects_only` does not prove a
production resume-plan defect.

`_index_with_family()` constructs one `default_payload` and assigns those identical ZIP
bytes to every synthetic object unless a family-level override is supplied. The injected
abort occurs after the checksum sidecar for the next object can already be retained. On
resume, `recover_retained_samples()` can therefore establish the complete authority chain
for that object without another raw fetch:

1. the retained sidecar hashes to its cache-local content address;
2. its filename identifies the exact remote object key;
3. its provider checksum identifies a raw digest already present in the content-addressed
   sample store; and
4. the retained raw bytes rehash to that digest.

The object key was absent from the pre-abort sample checkpoint, but its bytes were not
missing. Recovery correctly checkpoints it without fetching its raw URL. The test then
requires every key outside the pre-abort checkpoint to appear in the raw fetch log. That
assertion is stronger than the governing contract and conflicts with review 67's rule to
recover checksum-proven retained bytes and never redownload a proven retained sample.

This is a test-fixture/expectation defect. The accepted production behavior remains
consistent with request integrity, content-addressed deduplication, and the review-67
through review-70 recovery requirements. No production or CLI change is authorized.

No pytest, acceptance command, network command, or data-mutating probe was run by the
reviewer. This decision is based on record 71, exact source inspection, and the retained
review contracts.

## Test-only correction authorization

Sr Dev — Claude Build using Claude Opus 5 may edit only:

- `tests/acquisition/test_binance_usdm_harmonic_qualification.py`.

The correction must:

1. give the abort/resume test distinct valid raw archive bytes and matching provider
   sidecars per remote object so an uncompleted object is genuinely absent from the
   content-addressed store;
2. preserve assertions that completed objects are not fetched again, genuinely missing
   objects are fetched, and the resumed report's semantic identity equals an uninterrupted
   run; and
3. add or retain a focused assertion that same-digest cross-key recovery performs no
   redundant raw fetch only when exact sidecar filename, sidecar content address,
   provider checksum, and rehashed raw bytes agree.

The correction must not weaken the production authority contract or alter production
expectations to require redundant network retrieval. Claude performs no pytest, network
run, production edit, integration, repository-record edit, Git operation, commit, push,
data mutation, Gate 2 work, or model work. It stops for fresh reviewer inspection with the
exact SHA-256 of the one authorized path. Jr integration remains unauthorized.

## Reviewer publication

Under the narrow reviewer-publication exception, this review publication is confined to:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/72_CEX002_GATE1_RESUMABLE_EXECUTION_REVIEW.md`; and
- `tickets/CEX-002.md`.

No test or acceptance command is part of this publication. The reviewer stages, commits,
and pushes only those paths while preserving every source/test drop and unrelated dirty
path.

## Gate decision

CEX-002 and Gate 1 remain `IN_PROGRESS`. Gate 2, every other ticket, and model work remain
unauthorized. Next ticket remains `NONE`.
