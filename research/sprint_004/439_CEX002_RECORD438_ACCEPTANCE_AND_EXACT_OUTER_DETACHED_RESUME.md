# CEX-002 Review 439 — Record 438 Acceptance and Exact Outer-Detached Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal facts and integrated correction; correct record publication facts; authorize one literal proven-supervisor launch
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Record 438 and integration acceptance

Hermes commit `e5016ef1cf6a0a6ffd8d1fae2641eee8a00515eb` is accepted as the exact
three-path record-438 publication. The native-timestamp source/test correction is accepted as
integrated and pushed at commit `4a65179e6cd0938a86a556eb0c7f755ab3e283be`. The four ordered
integration checks passed: focused pytest 55/55, targeted Ruff, repository control, and restricted
whitespace validation. `HEAD == origin/main == e5016ef…` before this review.

The terminal runner facts are accepted. Exactly one Review-437 runner was created. Hermes observed
its shell and Python identities live after approximately 25 seconds; immediately after the harness
returned both exact PIDs were absent. Its merged output was empty, no end time or exit code was
written, and the hidden root remained exactly 181 Parquets plus 181 lineages, empty staging, and no
completion descriptor. This is a zero-mutation launch-lifecycle failure. It contains no normalizer,
source-data, capacity, authority, or acquisition diagnosis.

The record itself is published at `e5016ef…`, not at the earlier integration commit. The ticket's
record-438 block also acquired literal leading `|` characters during publication, and its top-level
actor was not returned to the reviewer as record 438 claimed. This review corrects those governance
facts and formatting while directly authorizing Hermes for the next literal launch; no
implementation or evidence byte is changed.

## Exact launch diagnosis

Review 437 required the supervisor itself to be launched by an outer `nohup setsid` boundary and
then to parent and wait for the ordinary Python child while recording its terminal status. The
actual Review-437 supervisor instead invoked `nohup setsid` only around the inner Python child, was
not durably launched under the required outer boundary, merged stdout/stderr, persisted no Python
start ticks in its JSON, and ended with a bare `wait 2>/dev/null` that could never record terminal
status. The harness lifecycle then ended with both descendants absent.

The proven Review-434 supervisor used the required opposite shape: one outer-detached supervisor,
one ordinary child, separate logs, durable shell/Python identities, a direct wait, and an end
record. It survived the launching harness and ran until its natural terminal result. No new
launcher, wrapper, downloader, normalizer patch, or architecture is needed.

## One literal supervisor authorization

Hermes performs no test, lint, source integration, source edit, data command, or repository edit.
It first proves all of the following read-only:

- `HEAD == origin/main` at this review's publication commit;
- the integrated source/test/CLI hashes remain `c0de316b…`, `aff38de6…`, and `33585315…`;
- no process matches Review 437's exact shell/Python identities or production CLI;
- the hidden root remains 181 Parquets plus 181 lineages, empty staging, no completion descriptor;
- Review 437's capacity equation remains sufficient; and
- the untracked repository wrapper remains unused and unstaged.

After every precheck passes, Hermes executes `mktemp -d /tmp/cex002_oi_439_XXXXXX` exactly once,
sets the resulting directory to mode 0700, and substitutes that one resolved literal path for both
`__RUNNER_DIR__` occurrences in the following repository-authoritative template. No other template
byte may change:

```bash
#!/usr/bin/env bash
set -u

REPO_ROOT=/home/lars/Crypto_Multifactor_Bot
cd "$REPO_ROOT"

SOURCE_COMMIT=4a65179e6cd0938a86a556eb0c7f755ab3e283be
START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RUNNER_DIR=__RUNNER_DIR__
SHELL_PID=$$
SHELL_START_TICKS=$(awk '{print $22}' /proc/$$/stat)
CWD=$(pwd -P)

mkdir -p "$RUNNER_DIR/logs"

cat > "$RUNNER_DIR/runner_meta.json" <<EOF
{
  "source_commit": "$SOURCE_COMMIT",
  "start_utc": "$START_UTC",
  "runner_dir": "$RUNNER_DIR",
  "cwd": "$CWD",
  "command": "PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src /home/lars/Crypto_Multifactor_Bot/.venv/bin/python /home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m",
  "shell_pid": "$SHELL_PID",
  "shell_start_ticks": "$SHELL_START_TICKS"
}
EOF

cat > "$RUNNER_DIR/logs/runner_start.log" <<EOF
source_commit=$SOURCE_COMMIT
start_utc=$START_UTC
runner_dir=$RUNNER_DIR
cwd=$CWD
command=PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src /home/lars/Crypto_Multifactor_Bot/.venv/bin/python /home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py --generation0-state data/cex002_qualify/gate2/state.sqlite --generation0-content-root data/cex002_qualify/gate2/content --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz --recovery-root data/cex002_recovery --output-root data/.cex002_open_interest_5m
shell_pid=$SHELL_PID
shell_start_ticks=$SHELL_START_TICKS
EOF

PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src \
  /home/lars/Crypto_Multifactor_Bot/.venv/bin/python \
  /home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py \
  --generation0-state data/cex002_qualify/gate2/state.sqlite \
  --generation0-content-root data/cex002_qualify/gate2/content \
  --v3-manifest data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz \
  --recovery-root data/cex002_recovery \
  --output-root data/.cex002_open_interest_5m \
  > "$RUNNER_DIR/logs/stdout.log" 2> "$RUNNER_DIR/logs/stderr.log" &

PYTHON_PID=$!
PYTHON_START_TICKS=$(awk '{print $22}' /proc/$PYTHON_PID/stat)

cat > "$RUNNER_DIR/python_meta.json" <<EOF
{
  "python_pid": "$PYTHON_PID",
  "python_start_ticks": "$PYTHON_START_TICKS"
}
EOF

echo "python_pid=$PYTHON_PID" >> "$RUNNER_DIR/logs/runner_start.log"
echo "python_start_ticks=$PYTHON_START_TICKS" >> "$RUNNER_DIR/logs/runner_start.log"

wait "$PYTHON_PID"
EXIT_CODE=$?
END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat > "$RUNNER_DIR/runner_end.json" <<EOF
{
  "end_utc": "$END_UTC",
  "exit_code": "$EXIT_CODE"
}
EOF

echo "end_utc=$END_UTC" >> "$RUNNER_DIR/logs/runner_start.log"
echo "exit_code=$EXIT_CODE" >> "$RUNNER_DIR/logs/runner_start.log"
```

Hermes writes that exact substituted template to the one runner's `supervisor.sh`, sets the file
mode to 0700, hashes it, and launches the supervisor with exactly this outer boundary, where
`__RUNNER_DIR__` is replaced by the same resolved literal directory:

```bash
nohup setsid __RUNNER_DIR__/supervisor.sh </dev/null >__RUNNER_DIR__/supervisor_outer.log 2>&1 &
```

Hermes records the outer PID from that launch and waits only long enough to prove that
`runner_meta.json` and `python_meta.json` contain nonempty identities matching live `/proc` start
ticks; the shell is the Python parent; both run in the supervisor's detached session; the exact
command/cwd/source commit match this review; and `runner_end.json` is absent. It then returns the
runner directory, supervisor SHA-256, both PID/start-tick pairs, start UTC, and current output
counts without waiting for terminal completion.

There is no second directory, template rewrite, launch, retry, foreground reproduction, signal,
cleanup, or replacement for any reason. Any substitution, hash, launch, process, session, metadata,
or identity uncertainty is terminal. The repository wrapper is never read, edited, staged, or
invoked. The production command downloads nothing and resumes the same hidden output root.

## Monitoring and terminal evidence

A later Hermes continuation may inspect only the exact reported Review-439 runner. It never signals
the runner. At terminal it publishes
`research/sprint_004/440_CEX002_OPEN_INTEREST_EXACT_SUPERVISOR_RESUME_RECORD.md`, updates CURRENT_TASK
and the ticket with both actor fields returned to the reviewer, stages exactly those three record
paths, commits, pushes, proves `HEAD == origin/main`, and stops.

On success record 440 performs every Review-437 reconciliation, including the exact
160,226,578 - 75,255 - 2,818 = 160,148,505 row equation, all descriptor-referenced digests and
Parquet metadata rows, lineage outcome counts, preserved prior bytes, HBAR conflict, typed gaps,
authority counts, and artifact-class byte totals. A terminal failure records complete logs and
hidden-output facts without patch, cleanup, reproduction, or retry.

No source/test/CLI patch, test, lint, acquisition, network request, redownload, cleanup, other
product, bundle, catalog transaction, NautilusTrader check, experiment, backtest, model, trading
engine, or next ticket is authorized. Gate 2 remains accepted; CEX-002 and Gate 3 remain
`IN_PROGRESS`.

## Reviewer publication scope

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/439_CEX002_RECORD438_ACCEPTANCE_AND_EXACT_OUTER_DETACHED_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The integrated source/test correction, hidden data, runner evidence, untracked wrapper, and all
unrelated dirty paths remain unstaged and untouched.
