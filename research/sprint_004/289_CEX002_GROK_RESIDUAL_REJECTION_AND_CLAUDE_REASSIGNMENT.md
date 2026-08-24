# CEX-002 Grok Residual Rejection and Claude Reassignment

Date: 2026-08-24
Reviewer: Lead Quantitative Finance Researcher/Engineer
Decision: REJECTED; one complete residual correction reassigned
Ticket state: IN_PROGRESS
Next required actor: Sr Dev - Claude Build on Claude Opus 5
Next ticket authorized: NONE

## Inspected drop

The reviewer inspected the complete review-288 drop once at these identities:

- `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`:
  `440e289c4b749b58fd29d94e75c2a65a5c0acc04285ba7fc477b8cd54f840aaf`
- `scripts/research/acquire_binance_usdm_harmonic_release.py`:
  `bb6038559d45bddfb011925ad96eb9552cbe4b71bfd5051375adbdcd3de555a9`
- `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`:
  `cc59d6510aa2233b5b38b10d5327d94ced33b32c648839de680feaa9e5754133`

The test source contains 37 test functions. All three files parse. The exact three-path
scope is preserved. No reviewer pytest ran and no developer test output was supplied.

The correction fixes the fresh-plan foreign-key insertion order, prospective capacity
formula, bounded main-manifest uniqueness check, exact retained-key selection and ZIP
validation, storage-neutral retained raw/sidecar adoption, per-attempt rate limiter call,
response closure in the principal transfer paths, deterministic gzip header, terminal
no-replace call, SQL unique-content aggregation, and post-capacity complete override.
Those changes are the accepted correction base but do not make the drop safe to
integrate.

## Decision

Reject the drop as one unit. The remaining defects affect crash consistency, exact budget
authority, resume trust, fatal concurrency, terminal proof, and filesystem containment.
They can corrupt or falsely certify the production acquisition state. This is not a test
or integration-only residual.

Grok Build has now missed the same architecture-sensitive residual contract in two
successive corrections. Under the accepted-result reliability rule in
`docs/engineering/DEVELOPMENT_ROLES.md`, Grok is deauthorized for this bounded drop and
the complete correction is reassigned to Claude Build. Do not split these requirements
among actors or submit another partial patch.

## Blocking findings

### 1. Coinalyze budget, publication, and completion are not one recoverable transition

At source lines 2861-2908 the ledger charge commits before immutable content publication,
then completion commits separately. A crash, publication failure, or completion failure
after the first commit permanently consumes budget without a corresponding completion.
The private response is also loaded completely with `read_bytes()` before validation and
the published response is loaded completely again. A zero remaining budget incorrectly
selects the full allocation as `max_bytes`, allowing a network response before the ledger
rejects it. A missing ledger row is discovered only after that network and parse work.
Secret scanning has no overlap between chunks, so a secret split across two chunks can be
missed. The parser still accepts an empty top-level container without an exact returned
symbol.

Implement a crash-recoverable coordinator transition that makes private validation,
exact persisted charge, no-replace publication ownership, and immutable completion
reconcilable under faults at every boundary. Refuse scheduling before the network when
remaining budget is zero or the singleton ledger/equation is invalid. Parse and secret-
scan incrementally with chunk overlap and bounded memory. Charge each accepted 200 or 404
body exactly once; never charge retained inventory. An over-budget, secret-bearing,
malformed, wrong-symbol, or wrong-window body must remain absent from the content store,
state, receipts, and errors.

### 2. Resume trusts unauthenticated mutable state

`AcquisitionState.open()` at lines 1617-1641 authenticates only application/user versions,
integrity, and foreign keys. It does not prove the exact schema, columns, constraints,
indexes, or row domains. The existing-state branch at lines 1758-1790 compares plan rows
but not the exact 202 terminal gaps and facts, required ledger singleton/equation,
sidecar facts, attempts, or completed provider content. Deleting a terminal gap can turn
an incomplete state into false success; deleting or altering the ledger can reset or
misstate the budget. Completed rows are skipped before their immutable provider facts are
re-proved. `semantic_digest()` at lines 2028-2052 omits authority/receipt, most completion
fields, sidecar facts, gap facts, ledger, plan facts, and durable attempts.

Authenticate the exact accepted schema and every trusted table/domain before scheduling
or verification. Reconcile the exact plan, 202 gaps and facts, singleton rows, ledger
equation, sidecar facts, attempts, and all completion fields. Re-prove each completed
provider object before it is skipped. Bind all immutable semantic facts in canonical
order in the durable digest. Mutating or deleting any independently trusted field or row
must fail closed before network activity or terminal publication.

### 3. Fatal worker errors can deadlock and lose their type

At lines 3141-3164 a daemon worker re-raises `AuthorityError` or `UnsafeStateError` without
an exception channel. The dead worker cannot consume its sentinel, leaving an unfinished
queue item so `work.join()` can wait forever. The main thread later maps every fatal to
`EXIT_UNSAFE_STATE`, losing the required distinct authority result. Workers still write
SQLite state directly instead of returning bounded results to one coordinator. The
shared attempt element and error list are racy/unbounded. The bounded network-call sample
is reported with `len(sample)`, undercounting actual calls after the sample fills.

Use one coordinator for all database writes and terminal transitions, a bounded worker
result/error channel, deterministic cancellation and settlement, and exact durable
attempt/network deltas. Propagate the original fatal class and distinct exit without a
hang. Keep only bounded redacted samples separate from exact counters. Validate all stop
bounds as positive finite values.

### 4. Offline verification still proves hashes, not the accepted release

`verify_state()` at lines 3233 onward does not join every completion to its exact plan
row or require the recorded and planned sizes. It does not parse a Binance sidecar to
prove filename/provider checksum/raw-digest agreement, join exact sidecar facts, or
reparse Coinalyze content against exact request, status, symbol, window, and outcome. It
does not require the exact provider/gap counts, 73 retained keys and objects, 5,225,416
retained bytes, five retained cost keys, or the accepted new/unique byte equations.
Sidecar physical bytes are absent from unique aggregation, and the terminal rows omit
facts needed for full reconciliation.

Create one shared streaming provider validator used before resume skip and by offline
verify. Require exactly 736,347 Binance plan/completion rows, 570 Coinalyze logical
completions, 202 exact unsupported gaps, and no pending/ambiguous work. Reconcile every
accepted retained/new/ledger/unique-physical equation, including sidecars, from SQL and
bounded streaming joins. Refuse every terminal artifact until the full proof succeeds;
repeated offline verification must publish byte-identical zero-network evidence.

### 5. Capacity, retained replay, and path containment remain incomplete

Binance performs one capacity check before downloading its sidecar and raw object; it
does not recompute after the sidecar consumes space and before the raw transfer. The
prospective equation therefore is not enforced at every transfer boundary. Retained
adoption checks `is_complete` before revalidating the existing retained completion, so a
corrupt completed retained row is silently skipped.

No-follow checks remain leaf-only for several authority/content paths; intermediate
parent symlinks can escape the accepted root. `load_holdout()` still checks then reopens
by pathname. Retained hard-link publication uses pathname operations without a safely
walked parent chain, no-replace race proof, or directory durability. Receipt publication
still calls `os.write` once and is not correct under a short write. Apply descriptor-
bound regular-file, no-follow, same-device, no-replace, and file/directory-fsync rules to
all authority, state, temporary, content, sidecar, hard-link, and receipt paths.

### 6. Required regressions are still absent or superficial

The added collection test searches for three source strings rather than proving bounded
production behavior. The suite still lacks production-path faults for atomic Coinalyze
charge/publication/completion and cross-run/concurrent exact ceilings; zero/missing/
altered ledger before network; split-chunk secrets and bounded incremental parsing;
Coinalyze retry/closure; independent schema/table/domain mutations; full semantic digest;
provider-semantic resume and verify; exact terminal counts/equations; parent symlink and
publication races; short writes; and fatal worker settlement. Add these regressions and
retain the valid review-288 tests.

## Complete correction authorization

Claude Build on Claude Opus 5 is authorized to rewrite or correct exactly:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_acquisition.py`
2. `scripts/research/acquire_binance_usdm_harmonic_release.py`
3. `tests/acquisition/test_binance_usdm_harmonic_acquisition.py`

Review 288 remains the full governing implementation contract; this review records the
unmet residuals and supersedes only its actor assignment. Preserve its accepted
authority, exact counts/bytes, ADR-0029 architecture, bounded-memory requirement, and all
regressions. Preserve the working corrections listed above unless a coherent replacement
is needed. Do not edit qualification, sizing, capacity, `source_audit`, package exports,
fixtures, evidence, ticket, handoff, ADR, configuration, or unrelated paths. Do not
restore, stash, reset, stage, or disturb dirty work. Tests remain synthetic, deterministic,
zero-network, temporary-root, and no-real-sleep.

After the complete correction is written, Claude may run exactly once:

```bash
PYTHONDONTWRITEBYTECODE=1 timeout --signal=TERM --kill-after=30s 10m \
  .venv/bin/python -m pytest \
  tests/acquisition/test_binance_usdm_harmonic_acquisition.py -q --tb=short
```

On nonzero result or timeout, stop without repair or rerun and report exact output and
status. Run no Ruff, control, qualification, sizing, capacity, plan, acquisition,
verification, network, or other command. Use no Git.

Stop once with all three SHA-256 hashes, test-function count, exact targeted-command
result, and confirmation that only the three authorized paths changed. Hermes
integration, acceptance commands, real planning/network/data/state/evidence, Git,
commit/push, Gate-2 acceptance, Gate 3, normalization, catalog, NautilusTrader, Harmonic
Trader, PAPER/LIVE, and next-ticket work remain unauthorized.

## Reviewer publication scope

The reviewer may stage, commit, and push exactly this review, current task, and ticket.
Developer source/test paths, data/state/evidence, and unrelated dirty work are excluded.
