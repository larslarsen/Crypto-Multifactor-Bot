# CEX-002 Gate-2 End-of-Plan Review and Revision Architecture

- **Date:** 2026-08-31
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** recovery and bounded progress accepted; record correction supplied; Gate 2 blocked on versioned revision authority
- **Authorized actor:** Sr Dev - Grok Build using Grok 4.6 High
- **Gate 2:** in progress / blocked pending revision-candidate source
- **Next ticket:** `NONE`

## Record-353 disposition

Hermes published record 353 alone in pushed commit
`5b693dcae37171988cf70323207b9b6c00506559`. `HEAD == origin/main` at that commit, and
the commit adds exactly
`research/sprint_004/353_CEX002_INTERRUPTED_RECOVERY_AND_ACQUISITION_CONTINUATION.md`.
Its SHA-256 is
`9c553b87271bd22c531d56fdf7dc5a937f054d4fe52c0dfef960702b670a6e8a`.

The Review-352 preproof passed. The one authorized command ran once and returned exit 2
`partial`; no second invocation, manual recovery, plan, replay, `verify`, source/test edit, or
later-gate command ran. The run-6 recovery is accepted exactly:

```text
run_id=00fc2af29dbf1e585ecc28974bdb034bdbcf7815b464ea333d5ddc10fae9dab4
stop_reason=interrupted
predecessor=64099aa5151f12fa09745242b71ecc36ab44e65c7cc5b26f4fddaa64d056a163
attempt_delta=235359
completion_delta=92215
byte_delta=1459224114
error_count=50921
receipt=1cf814d73aed5ab2d7aadccd8e57302339a0e78df40504d40e2d0dbbf457ee62
```

It retained the original run identity and exact predecessor-owned tail before run 7 began.
Receipt/locator/intent/seal/head publication is complete, no orphan tail exists, and no recovery
source defect is present.

Run 7 is also accepted as bounded progress and an honest end-of-plan stop:

```text
run_id=902a6fdb3d405b8db18e05564399f38ffddd7032dfaa2df707ef2d9e8d30e15b
stop_reason=partial
predecessor=1cf814d73aed5ab2d7aadccd8e57302339a0e78df40504d40e2d0dbbf457ee62
attempt_delta=89140
completion_delta=19035
byte_delta=4095285686
error_count=51275
receipt=8875338d0a2b7984fb8fefd7a716a04486667cfb1d726c3758f5496f065ef7ab
```

Direct reviewer read-only hashing independently proves all 19,035 new content paths and all
18,815 new sidecar paths are unique, regular, content-address correct, exact-size, and SHA-256
matching. Their byte totals are 4,095,285,686 and 1,720,240, with zero defects. Capacity
remained sufficient. The final database has zero unfinished runs and zero open Coinalyze charge.

## Record-353 presentation correction

Record 353's final coverage table is stale and misallocates run-7 completions to metrics while
leaving already completed book-depth and monthly premium-index rows pending. Do not amend the
record. The authoritative query-only final state is:

| Provider / family | Planned | Complete | Gap | Pending | Pending listed bytes |
|---|---:|---:|---:|---:|---:|
| Binance `daily/bookDepth` | 2,235 | 2,235 | 0 | 0 | 0 |
| Binance `daily/bookTicker` | 909 | 555 | 0 | 354 | 8,661,432,243 |
| Binance `daily/indexPriceKlines` | 12,266 | 12,266 | 0 | 0 | 0 |
| Binance `daily/klines` | 13,710 | 13,710 | 0 | 0 | 0 |
| Binance `daily/markPriceKlines` | 14,096 | 14,096 | 0 | 0 | 0 |
| Binance `daily/metrics` | 573,786 | 522,865 | 0 | 50,921 | 535,441,899 |
| Binance `daily/premiumIndexKlines` | 11,439 | 11,439 | 0 | 0 | 0 |
| Binance `monthly/fundingRate` | 21,035 | 21,035 | 0 | 0 | 0 |
| Binance `monthly/indexPriceKlines` | 21,721 | 21,721 | 0 | 0 | 0 |
| Binance `monthly/klines` | 21,932 | 21,932 | 0 | 0 | 0 |
| Binance `monthly/markPriceKlines` | 22,286 | 22,286 | 0 | 0 | 0 |
| Binance `monthly/premiumIndexKlines` | 20,932 | 20,932 | 0 | 0 | 0 |
| Coinalyze inventory | 1 | 1 | 0 | 0 | n/a |
| Coinalyze liquidation | 569 | 569 | 0 | 0 | n/a |
| Coinalyze unsupported mapping | 202 | 0 | 202 | 0 | n/a |

Thus exactly 51,275 Binance identities remain pending; every other downloadable logical receipt
is complete. The 354 ZIP-expansion identities all have retained sidecars, zero completion, zero
gap, and 8,661,432,243 frozen compressed bytes. The 50,921 metrics identities retain the prior
three-message split, sidecars, zero completion, and zero gap.

Record 353 also leaves the retry outcomes unresolved in presentation. Query-only joins prove all
13 HTTP-429 rate-limit attempts ended in a valid completion within run 7. All three transport
retries ended in the already accepted pending metrics `stream exceeded the listed byte ceiling`
outcome. There is no exhausted network failure.

Coinalyze is complete: all 569 planned liquidation identities have checksum-verified HTTP-200
charges, 20,126,995 charged bytes, 479,340 points, and exact reserved/published/settled
transitions `(569, 569, 569)`. The retained inventory is complete, all 202 unsupported mappings
remain typed gaps, and open charges equal zero.

## ZIP-ceiling diagnosis

The 354 new terminal outcomes all say:

```text
AcquisitionError: ZIP uncompressed expansion exceeds the accepted ceiling
```

They are confined to selected `daily/bookTicker` cost objects. The compressed response reached
HTTP 200, exact frozen size, and current provider checksum before the source rejected its central
directory's declared expansion. No raw completion was falsely claimed.

Reviewer read-only central-directory inspection of all 555 completed book-ticker peers proves:

```text
members per ZIP: 1
listed compressed bytes: min=317 p50=5644482 p95=9515234 max=10507167
uncompressed bytes: min=156 p50=36210458 p95=62186460 max=67095645
expansion ratio: min=0.492114 p50=6.410076 p95=7.059540 max=8.145989
```

The maximum accepted expansion is only 13,219 bytes below 64 MiB. Failed compressed sizes are
8,932,817 through 200,457,493 bytes, median 17,423,830, and total 8,661,432,243. This is an
unproved fixed-work-limit defect, not evidence of malformed provider archives. Removing all bomb
protection would also be incorrect.

ADR-0031 replaces the global cap for future source with the exact bounded formula:

```text
min(4 GiB, max(64 MiB, actual_compressed_bytes * 16))
```

All member/path/type/CRC/checksum/size protections remain. This source change cannot be applied
to the current generation because its authority and sealed receipts bind the old code hash.

## Architecture and gate decision

ADR-0031 is accepted. The existing active Gate-2 generation is now closed at run-7 head and may
not be invoked again. The 50,921 metrics revisions cannot be overwritten, silently adopted, or
misclassified as source gaps. The 354 book objects cannot be dropped merely because an internal
work limit rejected them.

The next safe step is a separate listing-only revision candidate. It must snapshot the exact
pending state, re-prove the retained sidecars, refresh current official listing metadata for
only the affected family prefixes, and publish an immutable 51,275-row candidate manifest and
receipt outside the active state. It performs no raw download and no active-state mutation.

Only after reviewer acceptance of that real candidate may later source implement and execute
the ADR-0031 linked generation transition. No transition or corrected acquisition is authorized
by this review.

## Grok revision-candidate source authorization

Sr Dev - Grok Build using Grok 4.6 High is selected for this source-authority and transaction-
boundary task. Grok may author only:

- `src/cryptofactors/acquisition/binance_usdm_gate2_revision_candidate.py`;
- `scripts/research/plan_binance_usdm_gate2_revision_candidate.py`;
- `tests/acquisition/test_binance_usdm_gate2_revision_candidate.py`; and
- `tests/acquisition/fixtures/binance_usdm_gate2_revision_candidate/` for bounded fixtures only.

The production module and CLI must implement only ADR-0031's revision-candidate planner:

1. exact generation-0 repository/source/plan/head/count binding;
2. held nonblocking no-follow acquisition lock and read-only/query-only SQLite snapshot;
3. exact derivation of the 50,921 metrics and 354 book-ticker pending sets with every other
   family, Coinalyze receipt, charge, gap, and unfinished-run predicate closed;
4. retained-sidecar no-follow rehash, basename parsing, provider-checksum binding, and exact
   plan/error lineage;
5. complete paginated current official listing retrieval for only the affected prefixes, with
   request-keyed content-addressed checkpoint/resume and no raw ZIP GET;
6. exact old/current/delta sizes, listing-page lineage, family/message counts, current maximum,
   ADR-0031 ZIP-work policy values, and a non-promotional capacity projection;
7. canonical deterministic `cex002_gate2_revision_candidate_v1` compressed row manifest and
   compact receipt whose semantic identity excludes retrieval clocks; and
8. explicit exit states for complete candidate, resumable partial listing, and blocker, with a
   nonzero blocker exit and no candidate acceptance claim.

There is no caller-selected family/symbol/key/date filter, no Coinalyze secret input, and no
mode which edits the active state. The default candidate root must be separate from active
`gate2`; path traversal, symlinks, wrong device/root, stale/tampered page reuse, duplicate or
missing keys, extra pending identities, listing drift during one candidate generation, and
interruption prefixes fail closed or resume exactly as ADR-0031 specifies.

Test source must directly cover all eight requirements plus no-network state preproof,
multi-page resume, interrupted-page cleanup, deterministic uninterrupted/resumed identity,
tampered page/checkpoint/state/sidecar refusal, exact 51,275-row production-shaped count without
materializing it as one Python collection, unknown/extra pending rows, current listing size
change, checksum change, and the lower/equal/upper ratio/absolute ZIP policy equations. Fixtures
remain small and synthetic; the large-count boundedness proof is generated in temporary state.

Grok must not edit the accepted acquisition source/CLI/test, ADR, ticket, handoff, repository
records, data, or unrelated paths. Grok performs no test or command execution, network request,
real SQLite/data open, Git operation, commit, push, plan, migration, raw acquisition, replay,
`verify`, normalization, or later-gate work. Stop for reviewer static source inspection with
exact path SHA-256 values, line and test-function counts, and confirmation that no command ran.

Hermes integration and command execution remain unauthorized until source/test acceptance.
Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

During final publication inspection, the reviewer inadvertently invoked the ticket's exact
`git diff --check` acceptance command restricted to the four reviewer-owned paths below. It
exited 0. That invocation is disclosed as a reviewer-procedure deviation, is not implementation
or acceptance evidence, and was not relied upon for the decisions in this review. No test,
source, acquisition, network, or data command ran.

The reviewer may stage, commit, and push exactly:

- `docs/adr/0031-post-plan-revision-authority-and-bounded-zip-validation.md`;
- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/354_CEX002_GATE2_END_OF_PLAN_REVIEW_AND_REVISION_ARCHITECTURE.md`; and
- `tickets/CEX-002.md`.

Developer source/test/evidence paths, state/data, `.env`, and unrelated dirty work are excluded.
