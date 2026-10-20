# CEX-002 Record 512 — Nautilus consumer checker integration

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 511 `research/sprint_004/511_CEX002_NAUTILUS_CONSUMER_SOURCE_AUTHORIZATION.md`

## Outcome

The Nautilus consumer-checker source was integrated after the reviewer's mechanical
correction. The source is a real full-release consumer checker (not run here); no real
full-release proof, catalog admission or consumer execution occurred. This record is
integration evidence only.

## Final source/test identities

| path | SHA-256 | lines |
| --- | --- | --- |
| scripts/research/check_cex002_nautilus_consumer.py | 6ac5fd0dbf4c676ccaf87fc288d68c3725a170a1de5aefe9babe497b2fb9584e | 795 |
| tests/test_cex002_nautilus_consumer.py | 37363e911a82cb2c7394cbb806f2acbe9c8b35a148f16f12c69ca8ebcd54802e | 442 |

Preceding drops (superseded, not integrated):
- First disposition: checker 438452694111131753d7f8dc34f1ca3fdf5e60377b8bc07564100a5a6f505b0b, test 184b1e4758e667a9a2f674607ca5735b3c5080fb5cb76da51257573e5787e702.
- Corrected source (accepted after the senior's decoder/late-failure fix): checker
  283d1730a2af0d734a52bf03515fec989e591d4dcdbd9cbba81ed727dccad282, test
  66bd7c1a74e5e420e636acd546e3827360c89ff36720d892057a4aa8fcefa75e.

## Test history (exact commands/status)

Run 1 — Hermes validation of the first disposition, exit 1:
```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
```
Result: 9 failed, 13 passed in 1.03s. All nine shared one root cause at
scripts/research/check_cex002_nautilus_consumer.py:452 (`query_custom_data`):
`OSError: Failed to query custom data: Record batch decode error: Error parsing 'custom_data': decode_custom_from_arrow: Failed to call decode_record_batch_py: ConsumerCheckError: custom Arrow field type changed`.
The group stopped at this nonzero; Ruff/control/whitespace were not run. Reviewer accepted
this first-failure stop.

Run 2 — senior corrective execution, exit 0 (attributed to GPT-6 Sol High under the narrow
targeted senior-test exception, NOT Hermes; not rerun by Hermes):
```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
```
Result: 22 passed in 1.08s. Preserved unchanged.

Lint check — Hermes validation of the corrected source, exit 1:
```
.venv/bin/python -m ruff check scripts/research/check_cex002_nautilus_consumer.py tests/test_cex002_nautilus_consumer.py
```
Result: "Found 2 errors." F402 (`field` shadowed by loop variable at checker:164) and F841
(`result` assigned but unused at test:395). The group stopped at this nonzero; control and
whitespace were not run. Reviewer accepted this stop.

## Mechanical correction (reviewer-reviewed, no behavior change)

Compared against the frozen pre-lint copies, the only changes are: rename `field` to
`schema_field` in the decoder loop (checker), and remove `result =` from the `refused`
helper's original call (test), retaining the call. All assertions and behavior preserved.

## Hermes validation of the final source (exact commands/results)

Pre-flight: HEAD == origin/main == `29097c533b77e751da416445c4f581ea0f0b6de4`; index empty;
final hashes and line counts authenticated above.

Grouped in one terminal request with `set -e`:
```
.venv/bin/python -m ruff check scripts/research/check_cex002_nautilus_consumer.py tests/test_cex002_nautilus_consumer.py
  -> All checks passed!

python3 scripts/check_repo_control.py
  -> Repo control check: PASS

git diff --check
  -> no output
```
Both final hashes reauthenticated after the checks: unchanged.

## Environment setup evidence (from the preceding session, preserved)

Executed once in order, all exit 0:
```
uv venv --no-project --no-config --python /home/lars/Crypto_Multifactor_Bot/.venv/bin/python /tmp/cex002_nautilus_review511_env
  -> Using CPython 3.13.14 interpreter at: .venv/bin/python
     Creating virtual environment at: /tmp/cex002_nautilus_review511_env

uv pip install --no-config --python /tmp/cex002_nautilus_review511_env/bin/python --default-index https://pypi.org/simple 'nautilus-trader==2.0.0rc3' 'pyarrow==25.0.0' 'pytest==9.1.1' 'pydantic==2.13.4'
  -> Resolved 12 packages; Installed 12 packages
     + annotated-types==0.8.0, iniconfig==2.3.1, nautilus-trader==2.0.0rc3, packaging==26.3,
       pluggy==1.7.0, pyarrow==25.0.0, pydantic==2.13.4, pydantic-core==2.46.4,
       pygments==2.21.0, pytest==9.1.1, typing-extensions==4.16.0, typing-inspection==0.4.4
     (uv emitted a benign cross-filesystem cache-copy warning; no operator fallback.)

uv pip freeze --python /tmp/cex002_nautilus_review511_env/bin/python
  -> annotated-types==0.8.0, iniconfig==2.3.1, nautilus-trader==2.0.0rc3, packaging==26.3,
     pluggy==1.7.0, pyarrow==25.0.0, pydantic==2.13.4, pydantic-core==2.46.4,
     pygments==2.21.0, pytest==9.1.1, typing-extensions==4.16.0, typing-inspection==0.4.4
```

Sanity check (one inline invocation, exit 0), limitation disclosed: it asserted Python 3.13
and printed the four distribution versions but did not itself assert all four versions; the
reviewer verified the versions from its output:
```
sys.executable /tmp/cex002_nautilus_review511_env/bin/python
python_version 3.13.14
dist nautilus-trader 2.0.0rc3
dist pyarrow 25.0.0
dist pytest 9.1.1
dist pydantic 2.13.4
imports_ok True  (CustomData, DataType, register_custom_data_class from nautilus_trader.model;
                 ParquetDataCatalog from nautilus_trader.persistence)
```

Setup and sanity were NOT rerun by Hermes for this integration; the accepted results are
preserved as above.

## Integration

- Staged exactly three paths: the two final source/test paths above plus this Record 512.
- `git diff --cached --check`: exit 0, no output.
- Staged path list and committed blob identities verified.
- Commit and normal push executed; HEAD equals origin/main and the index is empty.
- No `git add -A`, no unrelated staging, no amend/reset/force push.

## Scope limits and gaps

- No real full-release consumer execution, proof generation or catalog admission occurred;
  no fixture results are claimed as release acceptance.
- The checker/test source is not imported, run or inspected by Hermes beyond the authorized
  validation commands above; the senior is the only authorized source actor and is stopped.
- No source edits, dependency/lock changes, real-data checks or next-ticket work.
- The accepted producer/catalog tests are preserved, not rerun.

## Record status

Record 512 is integration evidence owned by Hermes. It claims no release or Gate acceptance.
CEX-002 remains IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
