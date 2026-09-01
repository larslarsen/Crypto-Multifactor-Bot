# CEX-002 Review 432 — Record 431 Acceptance and Absolute-Path Resume

- **Date:** 2026-09-01
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** accept the terminal record and integrated correction; authorize one absolute-path resume
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Jr Dev — Hermes
- **Next ticket:** `NONE`

## Record 431 and integration acceptance

`HEAD == origin/main == 153c7b6e8baabf8918f19d17e76f57d289249d07`. Record 431 accurately
states both failed wrapper identities, the unauthorized duplicate, both exit-127 outcomes, the
empty Python start ticks, the harness interruption, and the unchanged hidden output. The accepted
normalizer correction is integrated at commit
`a243932d266b9a0ba88266af705febe9eaf91359` with its Review-430 identities unchanged:

| Path | Lines | SHA-256 |
|---|---:|---|
| `src/cryptofactors/ingest/binance_usdm_open_interest.py` | 1,493 | `bf6c5c445a6054c56d503f415388bc0df94e3326b621826fd0c378efa896387d` |
| `tests/ingest/test_binance_usdm_open_interest.py` | 576 | `3cd77872250130330898c83fa95196ba3e5b283633ba2809b2ac33b9d90fd9ad` |
| `scripts/research/normalize_binance_usdm_open_interest.py` | 53 | `33585315bb061a97d68197792ba86d8911383534d28c734f73f946900464a675` |

No Python process executed in either failed attempt, and no source or data defect was exposed. The
normalizer and its test require no further patch or repeated test run.

## Exact launch defect

Both stderr logs prove that the failed supervisor reached line 39 with a relative
`.venv/bin/python` path while its working directory was not the repository. The current untracked
`run_continuation_runner.sh` is not repository authority, is not accepted, may reflect later
uncommitted edits, and must not be read as evidence of what either terminal runner executed. It
must not be edited, staged, committed, or invoked.

The correction is operational only: the one authorized supervisor fixes its repository root and
uses absolute paths for Python, the CLI, every authority input, and the hidden output. This is not
a source-code correction, architecture change, acquisition, or redownload.

## Prelaunch checks

Hermes first proves all of the following without editing or running tests:

1. `HEAD == origin/main` at this review's publication commit;
2. the three path identities above;
3. both Review-430 runner directories are terminal with exit 127 and empty Python start ticks;
4. no process matching the exact open-interest normalizer command is live;
5. the hidden root still contains eight Parquets plus eight matching lineages, empty staging, and
   no completion descriptor;
6. Review 430's exact capacity equation remains sufficient; and
7. `python3 scripts/check_repo_control.py` exits 0.

Any failed precheck stops before creating a runner and is reported to the reviewer. No pytest,
ruff, source edit, Git integration, cleanup, or data command is authorized.

## One absolute-path detached supervisor

After every precheck passes, Hermes creates exactly one directory using literal template
`/tmp/cex002_oi_432_XXXXXX`. Inside that directory only, it creates one mode-0700 supervisor
script implementing these fixed operations:

1. set `REPO_ROOT` to the literal `/home/lars/Crypto_Multifactor_Bot` and `cd` there before launch;
2. create `logs/`, then record source commit, start UTC, runner directory, shell PID, and shell
   start ticks in `runner_meta.json` and `logs/runner_start.log`;
3. launch exactly this Python process with all paths absolute and with
   `PYTHONPATH=/home/lars/Crypto_Multifactor_Bot/src`:

```text
/home/lars/Crypto_Multifactor_Bot/.venv/bin/python
/home/lars/Crypto_Multifactor_Bot/scripts/research/normalize_binance_usdm_open_interest.py
--generation0-state /home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2/state.sqlite
--generation0-content-root /home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2/content
--v3-manifest /home/lars/Crypto_Multifactor_Bot/data/cex002_qualify/gate2_revision_candidate_v3/manifest/4dacaba97c17ad9c4a9724f5db74dfab7ee98760cdb3df6dea46ab37c0684c2d.json.gz
--recovery-root /home/lars/Crypto_Multifactor_Bot/data/cex002_recovery
--output-root /home/lars/Crypto_Multifactor_Bot/data/.cex002_open_interest_5m
```

4. redirect that process's stdout and stderr persistently to `logs/stdout.log` and
   `logs/stderr.log`, record its PID and Linux start ticks in `python_meta.json` and the start log,
   wait for that exact PID, and write end UTC plus exit code to `runner_end.json` and the start log;
5. perform no other operation.

Hermes launches that one supervisor with `nohup setsid`, closed stdin, and stdout/stderr redirected
to a file inside the same runner directory. It confirms that the supervisor metadata and Python
metadata exist and returns the exact directory, both PID/start-tick pairs, start UTC, and log paths
immediately. It does not wait for terminal completion in the launch harness.

There is no second launch under this review for any reason. A missing metadata file, empty Python
start tick, immediate nonzero exit, launch-command problem, or harness uncertainty is terminal and
returns to the reviewer without correction or retry. A live process is never signaled. No wrapper
or runner file is created in the repository.

## Continuation and terminal record

Later Hermes continuations may inspect only the exact reported runner and hidden root. On terminal
success they perform Review 430's full reconciliation, including exact prior-byte reuse and the
May-03 exclusion/typed-gap/May-04-owned-value checks. At any terminal outcome Hermes publishes
`research/sprint_004/433_CEX002_OPEN_INTEREST_RESUME_RECORD.md`, updates CURRENT_TASK and the ticket
with both actor fields returned to the reviewer, stages exactly those three record paths, commits,
pushes, proves `HEAD == origin/main`, and stops. A live-run status report creates no record.

No source/test/CLI patch, repeated test, acquisition, network request, cleanup, deletion, duplicate
or replacement runner, other product, final bundle, catalog transaction, NautilusTrader check,
experiment, backtest, model, trading engine, or next ticket is authorized.

Under the AGENTS.md reviewer governance-publication exception this review commits and pushes
exactly:

- `research/sprint_004/432_CEX002_RECORD431_ACCEPTANCE_AND_ABSOLUTE_PATH_RESUME.md`;
- `docs/handoff/CURRENT_TASK.md`; and
- `tickets/CEX-002.md`.

The accepted source/test integration, hidden data, terminal runner evidence, untracked wrapper,
and every unrelated dirty path remain untouched.
