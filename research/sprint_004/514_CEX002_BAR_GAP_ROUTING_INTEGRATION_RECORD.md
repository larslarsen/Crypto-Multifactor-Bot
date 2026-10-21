# CEX-002 Record 514 — bar-gap routing correction integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 513 final section
`research/sprint_004/513_CEX002_REAL_CONSUMER_PREFLIGHT_AND_GAP_ROUTING_REVIEW.md`
("Corrected source accepted; Hermes integration and bounded real measurement")

## Outcome

The two-path bar-gap routing correction was integrated. No real full-release consumer
execution, proof generation or catalog admission occurred. This record is integration
evidence only; it claims no release or Gate acceptance.

## Accepted correction and its decision

The eleven pinned JSON manifests contain a real `role="partition"` gap table
(`component="quality_gap"`, 154 rows, 5,039 bytes) alongside the 22,633 main bar tables
(`component=""`). The previous native-Bar selection used dataset type and role only, so the
real gap schema would have been rejected for lacking OHLC. The accepted guard requires, for
TABLE components in the bar dataset, `role="partition"` plus an explicit component of either
`""` or `quality_gap`; only `component=""` receives the mandatory native Bar projection, and
`quality_gap` uses complete custom row transport with the same proof/digest/schema
authentication. Unknown or missing component tags and unknown roles are refused, and a
malformed primary bar schema still fails (it cannot opt out by dropping columns). Type is
not inferred from field shape.

## Final source/test identities (frozen, independently reauthenticated by Hermes)

| path | SHA-256 | lines |
| --- | --- | ---: |
| scripts/research/check_cex002_nautilus_consumer.py | ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117 | 798 |
| tests/test_cex002_nautilus_consumer.py | c4e051a1b9e0f9ae9df983f4319c2f4370cbe108b2d88b2632af8768d4465ff5 | 521 |

Preceding accepted integration (preserved, not superseded by this drop):
b186b3a250ee147bb8d55311090bfb232f90e3ab / Record 512.

## Senior targeted execution (attributed, not rerun by Hermes)

The corrective source was executed exactly once under the targeted senior-test exception by
the authorized sole senior actor, Sr Dev — Codex Sol (GPT-6 Sol High):

```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
  -> exit 0: 27 passed in 2.47s
```

The senior did not rerun setup and did not run any other test, lint, probe, real-data or Git
step. Result and attribution are the senior's; Hermes did not execute or repeat them.

## Hermes ordered validation (exact command, actual result)

Pre-flight: `HEAD == origin/main == c82ba5acac61e98184a4253f3a977875b77e30d5`; index empty;
both frozen hashes and line counts authenticated above.

Grouped in one terminal request with `set -e`:

```
.venv/bin/python -m ruff check scripts/research/check_cex002_nautilus_consumer.py tests/test_cex002_nautilus_consumer.py
  -> All checks passed!
python3 scripts/check_repo_control.py
  -> Repo control check: PASS
git diff --check
  -> no output
```

All three exited 0. No check was rerun; no source, test, dependency or data file was
modified by Hermes.

## Interruption disclosure (limited, no effect on evidence)

During Hermes's preparation for section B, the reviewer issued a Ctrl-C that interrupted
Hermes before any validation or data process was running. No producer, checker, test or
setup process was active; no data, catalog or source state changed. The interruption ended
only that preparation turn. Section A resumed from the unchanged pre-flight state, with all
three checks still run once as above and both frozen hashes unchanged.

## Integration

- Staged exactly three paths: the two frozen source/test paths above plus this Record 514.
- Asserted staged-name equality; `git diff --cached --check` exit 0, no output.
- Normal commit and normal push executed; `HEAD == origin/main`; index empty.
- Committed source hashes reauthenticated after the push.
- No `git add -A`, no unrelated staging, no amend/reset/force push. Unrelated dirty paths
  in the working tree were preserved.

## Scope limits and gaps

- No real full-release consumer execution, proof generation, `.proofs` output or catalog
  admission occurred; the 27-pass fixture result is not claimed as release acceptance.
- Section B (one bounded real measurement, 24 selected whole tables / 369,588 rows, Record
  515) is NOT executed in this record; it is deferred pending delivery after this commit.
- The senior source actor is stopped; Hermes made no source or test edit.
- No source edits, dependency/lock changes, arbitrary cleanup, producer retry, admission or
  next-ticket work. The accepted producer/catalog tests are preserved, not rerun.

## Record status

Record 514 is integration evidence owned by Hermes. It claims no release or Gate acceptance.
CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
