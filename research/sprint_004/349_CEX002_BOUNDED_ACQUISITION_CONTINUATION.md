# CEX-002 bounded acquisition continuation — preproof stop

## Authorization

Review 348 authorized up to three sequential network-enabled acquisition invocations, but
only after the one-time repository/query-only preproof passed. A failed preproof prohibits
acquisition, repair, replay, verify, and rerun.

## Preproof evidence

Repository and implementation predicates passed:

```text
HEAD=e6ddba6d1bb68086399c35d9817cca947e821b7c
ORIGIN_MAIN=e6ddba6d1bb68086399c35d9817cca947e821b7c
review-348 present=yes
evidence 1cb8a72 ancestor=yes
record-347 sha256=89dff6c1db36ee04bb29cf13e5968a701b45a70f2c5249536020286991e3b6fe
acquisition source sha256=af6ef568b9f0f30827b393efc013b13560d4fd5761ec86417c0d2cf461e1248d
acquisition test sha256=40a75c4e8516f94e9d7528ec036bd7fef964219ac2203768f510364ff30d2624
acquisition CLI sha256=6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043
index/implementation clean=yes
.env/key predicates=yes
```

The query-only state inspection used
`file:data/cex002_qualify/gate2/state.sqlite?mode=ro` and immediately set
`PRAGMA query_only=ON`; it reported `query_only=1`. The repository state facts were:

```text
receipt_head=ee2740e3f15741d4af5a1fe229851679c5fe9e6d860f38a4a5d14e13cc59c864
plan_entries=737119
attempts=755764
completions=335428
sidecars=363086
terminal_gaps=202
coinalyze_charges=0
charge_transitions=0
open_coinalyze_charges=0
runs=4
seals=4
publications=4
unfinished_runs=0
```

The exact Review-348 preproof requirement was `terminal_attempts=27658`. The actual
query-only state returned:

```text
terminal_attempts=30266
terminal_message_counts:
AcquisitionError: listed byte size does not match = 7510
AcquisitionError: stream exceeded the listed byte ceiling = 22755
AcquisitionError: streamed digest does not match the required checksum = 1
```

This differs from the required 27,658 terminal identities and therefore fails the exact
preproof. The discrepancy is a new persisted state condition outside the authorized
starting state. No acquisition invocation was run in this continuation, and no separate
connectivity probe, plan, replay, verify, repair, or data mutation was performed.

## Stop

The campaign stopped before invocation 1 because Review 348's required preproof did not
pass. There is no acquisition timing, exit, receipt, or continuation evidence to report.
No second or third invocation is authorized after this stop.
