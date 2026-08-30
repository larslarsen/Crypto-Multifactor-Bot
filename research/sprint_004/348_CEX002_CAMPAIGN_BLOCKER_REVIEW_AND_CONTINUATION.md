# CEX-002 Campaign Blocker Review and Continuation

- **Date:** 2026-08-29
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** bounded progress and stop accepted; evidence omissions corrected; continuation authorized
- **Authorized actor:** Jr Dev - Hermes
- **Gate 2:** in progress
- **Next ticket:** `NONE`

## Handoff disposition

Hermes published record 347 alone in pushed commit
`1cb8a7251cd788b031eac8bd62fcc21a960b6553`. `HEAD == origin/main` at that commit, the
commit adds exactly
`research/sprint_004/347_CEX002_BOUNDED_ACQUISITION_CAMPAIGN.md`, and that record's SHA-256
is `89dff6c1db36ee04bb29cf13e5968a701b45a70f2c5249536020286991e3b6fe`.

The one authorized invocation exited 2 with `max_wall_seconds`, published canonical receipt
`ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864`, and added 268,437
checksum-verified Binance completions and 2,859,665,835 listed bytes. Capacity remained
sufficient, the receipt is durably linked to the prior head, and no second or third campaign
invocation ran. The execution and its correct stop are accepted as bounded Gate-2 progress,
not Gate-2 acceptance.

Record 347 does not satisfy Review 346's complete evidence-publication contract by itself. It
omits the provider/family completion and remaining totals, exact revision-set evolution,
physical content/sidecar hash reconciliation, bounded retry outcomes, and the identity and
retained state of the new checksum mismatch. It also does not disclose that one transport
retry did not end in a completion. The reviewer does not route a presentation-only amendment;
the query-only and filesystem/hash correction below is authoritative when read with record
347.

## Reviewer read-only reconciliation

The reviewer opened only
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro`, immediately set
`PRAGMA query_only=ON`, and observed `query_only=1`. Aggregate and bounded identity queries
were followed by read-only filesystem type/size/content-hash checks for only the new
completion and sidecar sequence ranges. No acquisition, network request, replay, `verify`,
test, source edit, state/data mutation, or retired-tree access occurred.

The receipt file hashes to its filename. SQLite contains exactly 737,119 plan rows, 755,764
attempts, 335,428 completions, 363,086 sidecars, 202 terminal gaps, four closed runs, four
publications, four seals, zero charges, and zero transitions. The seal head exactly matches
the record-347 receipt and predecessor with marks `attempt_hi=755764`,
`completion_hi=335428`, `sidecar_hi=363086`, `charge_hi=0`, `transition_hi=0`, `run_hi=4`,
and `seal_hi=3`.

The Review-347 run deltas physically reconcile:

```text
new completion rows=268437
new unique content paths=268437
new content bytes=2859665835
regular/path-bound/size-matched/SHA-256-matched content defects=0
new sidecar rows=293487
new unique sidecar paths=293487
new sidecar bytes=28670296
regular/path-bound/size-matched/SHA-256-matched sidecar defects=0
private partials in tmp/run-receipt/terminal roots=0
persisted api_key/authorization marker hits across plan/attempt/run/receipt/charge fields=0
```

The exact current provider/family state is:

| Provider / family | Planned | Complete | Gap | Pending | Pending listed bytes |
|---|---:|---:|---:|---:|---:|
| Binance `daily/bookDepth` | 2,235 | 1 | 0 | 2,234 | 830,372,528 |
| Binance `daily/bookTicker` | 909 | 4 | 0 | 905 | 11,687,976,893 |
| Binance `daily/indexPriceKlines` | 12,266 | 12,266 | 0 | 0 | 0 |
| Binance `daily/klines` | 13,710 | 13,710 | 0 | 0 | 0 |
| Binance `daily/markPriceKlines` | 14,096 | 14,096 | 0 | 0 | 0 |
| Binance `daily/metrics` | 573,786 | 295,299 | 0 | 278,487 | 2,957,524,984 |
| Binance `daily/premiumIndexKlines` | 11,439 | 1 | 0 | 11,438 | 8,452,139 |
| Binance `monthly/fundingRate` | 21,035 | 15 | 0 | 21,020 | 21,337,907 |
| Binance `monthly/indexPriceKlines` | 21,721 | 9 | 0 | 21,712 | 372,013,657 |
| Binance `monthly/klines` | 21,932 | 9 | 0 | 21,923 | 645,288,273 |
| Binance `monthly/markPriceKlines` | 22,286 | 9 | 0 | 22,277 | 346,735,545 |
| Binance `monthly/premiumIndexKlines` | 20,932 | 9 | 0 | 20,923 | 290,612,430 |
| Coinalyze inventory | 1 | 0 | 0 | 1 | n/a |
| Coinalyze liquidation | 569 | 0 | 0 | 569 | n/a |
| Coinalyze unsupported mapping | 202 | 0 | 202 | 0 | n/a |

Thus 400,919 Binance objects and 570 Coinalyze requests remain unresolved. The pending
Binance listed-byte total is 17,160,314,356. None is accepted as coverage by this review.

## Revision and retry findings

All 27,658 terminal HTTP-200 identities in the invocation are distinct `daily/metrics`
objects, have a retained sidecar, and have no completion or terminal gap. The prior 2,608
revision identities are an exact subset; 25,050 new identities were added. The exact current
run classification is:

```text
listed byte size does not match: 6854 identities / 67642350 frozen bytes
stream exceeded the listed byte ceiling: 20803 identities / 222884195 frozen bytes
streamed digest does not match the required checksum: 1 identity / 9810 frozen bytes
total: 27658 identities / 290536355 frozen bytes
prior-set overlap: 2608
new identities: 25050
```

The first two messages remain confined to frozen dates `2024-04-04` through `2026-06-10`.
The third message names exactly:

```text
data/futures/um/daily/metrics/HBARUSDC/HBARUSDC-metrics-2026-07-09.zip
```

Its 98-byte current sidecar is retained at content SHA-256
`4adf2c39cdcf34abe07b695676a3c2b4b154556ded64a937887dac23ff5fb01c` and names provider
checksum `060025bb8887f2c0456d3333fb3a70001f3dfa5662132b0f895a7f3d3247bd52`.
The streamed 9,810-byte response did not match that checksum; no raw completion or gap was
published. This is consistent with a provider-side revision or publication inconsistency,
but is not yet a reviewer-disposed terminal source outcome.

The two HTTP-503 retries recovered and completed their DUSKUSDT and HEMIUSDT identities. The
connection reset on the AVAXUSDT checksum sidecar recovered to a successful sidecar fetch, but
the subsequent raw object exceeded the frozen listed-byte ceiling and remained incomplete:

```text
data/futures/um/daily/metrics/AVAXUSDT/AVAXUSDT-metrics-2026-04-27.zip
```

Review 346 required every transient/rate-limit/transport retry to end in a completion before
another invocation. The AVAXUSDT sequence therefore independently failed that literal
continuation predicate. Hermes correctly stopped without another invocation, but record 347
omits this failed predicate. No exhausted transport failure remained; the identity instead
ended in the accepted size-revision class.

## Engineering decision

No production-source correction or ADR amendment is justified now. The engine failed closed,
retained the current sidecar, discarded the unverified raw response, preserved the frozen plan,
and made no false completion or gap claim. Overwriting listing facts, forcing completion, or
disposing the revision set during partial acquisition would violate ADR-0029. The unresolved
revision identities remain pending for one later source-authority disposition after unaffected
acquisition reaches the end of the plan or a materially different blocker appears.

The prior retry predicate was intentionally conservative. For the continuation below, a
recovered network retry may end either in a valid completion or in one of the three exact
accepted pending `daily/metrics` revision messages. This is a bounded reviewer decision about
continuation evidence, not a terminal-source-outcome waiver.

## Bounded continuation authorization

Hermes owns up to three sequential acquisition invocations. Each retains the 84,600-second
engine wall bound inside a 24-hour outer bound. Preserve every unrelated modified and untracked
path. Before the first invocation only, repository/query-only preproof must establish:

- `HEAD == origin/main`, this Review 348 is present, and commit `1cb8a72` is an ancestor;
- record-347, acquisition source, acquisition test, and CLI SHA-256 values equal respectively
  `89dff6c1db36ee04bb29cf13e5968a701b45a70f2c5249536020286991e3b6fe`,
  `af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d`,
  `40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624`, and
  `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`;
- no staged path or `.git/index.lock`; the three governing implementation paths are clean;
- `.env` retains the accepted ignored/regular/owner/mode/syntax/nonempty-key predicates without
  emitting the key or its length; and
- query-only state has receipt `ee2740e...c864` as its head, the exact totals above, exactly
  27,658 sidecar-only pending `daily/metrics` revision identities with the three exact message
  counts above, no unfinished run, no open charge, and sufficient capacity.

Any failed preproof stops without acquisition, repair, reset, restore, checkout, stash, data
mutation, or rerun. Do not run a separate connectivity probe, `plan`, replay, or `verify`.

For each authorized invocation, record exact UTC timing and invoke exactly once from the
repository root with explicit external-network escalation:

```bash
(
  set -a
  . ./.env || exit 5
  set +a
  test -n "${COINALYZE_API_KEY:-}" || exit 5
  export PYTHONDONTWRITEBYTECODE=1
  exec timeout --signal=TERM --kill-after=5m 24h \
    .venv/bin/python scripts/research/acquire_binance_usdm_harmonic_release.py \
    acquire --store-root data/cex002_qualify --max-wall-seconds 84600
)
```

Capture complete bounded stdout/stderr, exit, start/end, and elapsed time. Never rerun an
invocation. Another invocation is authorized only when all continuation predicates pass:

- the canonical receipt is fully published, sealed, and linked to the prior head;
- exit 2 has stop reason `max_wall_seconds`; exit 3 `complete_with_typed_gaps` ends the campaign
  successfully and prohibits another invocation;
- every terminal HTTP-200 validation failure is a `daily/metrics` identity with exactly one of
  the three messages recorded above, remains pending with a sidecar and without a completion or
  gap, and all 27,658 pre-existing revision identities remain intact;
- every retry-class attempt is followed in that invocation by either a valid completion or one
  of those exact pending metrics-revision outcomes; an exhausted network failure is a blocker;
- there is at least one new completion and, for `max_wall_seconds`, either at least 10,000 new
  completions or at least 100,000,000 new completion bytes;
- receipt/state/high-watermark and physical content/sidecar deltas reconcile, no private
  partial or terminal artifact remains, capacity is sufficient, and no Coinalyze charge is open;
  accepted Coinalyze responses/outcomes must obey the frozen identity, shape, rate, byte-budget,
  and ledger contract; and
- the secret is absent from captured output and every persisted URL/query/database/receipt/
  evidence field without printing the secret or its length.

Exit 2 with `partial` ends the campaign and prohibits another invocation. Any other exit, new
provider/family/error message, exhausted network failure, failed reconciliation, capacity or
secret failure, low progress, or the third invocation also ends the campaign without repair or
rerun. Do not delete, modify, dispose, or accept as coverage any of the revision identities.

## Evidence and Git boundary

After the campaign stops or the third invocation finishes, create exactly:

- `research/sprint_004/349_CEX002_BOUNDED_ACQUISITION_CONTINUATION.md`.

Record the preproof, every invocation and complete bounded output, exact UTC timings/exits,
receipt bodies/hashes/chain/watermarks, per-run and cumulative state/byte deltas, exact
attempt/retry/error classifications and bounded redacted samples, provider/family completed
and remaining totals, revision-set evolution, Coinalyze ledger/outcomes, physical artifact
hash reconciliation, capacity, secret-absence predicates, observed rates, stop predicate, and
proof no unauthorized later invocation ran. Label transformed summaries accurately.

Use explicit Git-write escalation. Stage only record 349, prove that exact one-path cached set,
commit with message `record CEX-002 bounded acquisition continuation`, push `main`, and stop.
No source/test/governance edit, fourth invocation, replay, `verify`, repair, revision disposal,
Gate 3, normalization, catalog, NautilusTrader, Harmonic Trader, experiment, PAPER/LIVE, or
next-ticket work is authorized. Gate 2 remains `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review,
`docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`. Developer evidence, state/data,
`.env`, and unrelated dirty work are excluded.
