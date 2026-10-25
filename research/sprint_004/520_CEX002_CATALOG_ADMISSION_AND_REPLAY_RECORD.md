# CEX-002 Record 520 — Catalog admission and replay

Launch UTC: 2026-10-25T21:30:12Z
Execution HEAD: c32ad0ad06c111d015efb34d427cc6c28aa947fa

## Raw execution output

```jsonl
{"label":"before_admission","snapshot":{"dataset":{"count":0,"sha256":"e0e6c8f84d277f4145c9512c246c1de43becdf82b2ec09bf76610ea5fa095872"},"dataset_file":{"count":0,"sha256":"6b96193eb47515a9b4174e0bf2fd61a5661fca0e828712a76d386aa8d733c3b1"},"dataset_ids":[],"dataset_input_dataset":{"count":0,"sha256":"c29faccb03bc1a3e26dc665709605beb2ef56188355f1719dbe5295a324af5e2"},"dataset_input_raw_object":{"count":0,"sha256":"6a8d487a15f8d0927d64f2c03491325ce88b37d29ed7402743c05bd67f210de3"},"quarantine_sha256":"b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103"},"stage":"catalog_snapshot"}
{"command":"/tmp/cex002_nautilus_review511_env/bin/python -u scripts/research/publish_binance_usdm_harmonic_bundle.py publish --repo /home/lars/Crypto_Multifactor_Bot --catalog /home/lars/Crypto_Multifactor_Bot/exp003.db --code-commit 1f5629badfa0e8af6338fbeb019a5f7e60b6a324 --proof /home/lars/Crypto_Multifactor_Bot/data/.cex002_harmonic_bundle/.proofs/3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d.json --proof-sha 3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d --checker-sha ac83cc25af508b75fb79d85ba7a615041235f9a9835bb37cb81f9f2f7b740117 --nautilus-version 2.0.0rc3 --prepared-sha 8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34","phase":"admission","stage":"phase_started","utc":"2026-10-25T21:30:12.875635+00:00"}
{"elapsed_seconds":0.71,"exit_code":1,"phase":"admission","stage":"phase_result","stderr":"Traceback (most recent call last):\n  File \"/home/lars/Crypto_Multifactor_Bot/scripts/research/publish_binance_usdm_harmonic_bundle.py\", line 15, in <module>\n    from cryptofactors.ingest.binance_usdm_harmonic_bundle import (\n    ...<5 lines>...\n    )\n  File \"/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/__init__.py\", line 5, in <module>\n    from cryptofactors.ingest.bitmex_funding import (\n    ...<7 lines>...\n    )\n  File \"/home/lars/Crypto_Multifactor_Bot/src/cryptofactors/ingest/bitmex_funding.py\", line 23, in <module>\n    import httpx\nModuleNotFoundError: No module named 'httpx'\n","stdout":""}
{"error":"admission failed; no further phase is authorized","error_type":"RuntimeError","phase":"admission","stage":"FAILED"}
Traceback (most recent call last):
  File "<stdin>", line 98, in <module>
  File "<stdin>", line 29, in need
RuntimeError: admission failed; no further phase is authorized
```

Workflow/deadline exit status: 1
Output capture exit status: 0

## Provenance

Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Actor: Jr Dev — Hermes
Model: meituan/longcat-2.5-preview:free (Nous Portal), no reasoning override
Reviewer: Lead Quantitative Finance Researcher/Engineer
Governing: Review 519 `research/sprint_004/519_CEX002_CATALOG_ADMISSION_AND_REPLAY_AUTHORIZATION.md`

The owner's continuation authorized advancing the ticket to its existing catalog
publication/replay requirement. Review 519 authorizes Hermes to run the unchanged
production CLI once for ONE initial publish, ONE intentional identical publish replay,
then ONE explicit release-reader verify. No source/test change was needed and none was
made. The existing full consumer PASS (Record 518) is accepted and was not rerun.

Execution HEAD at launch: `c32ad0ad06c111d015efb34d427cc6c28aa947fa` (record header,
captured by the reviewed bash block itself). Launch UTC 2026-10-25T21:30:12Z.

Process identity: session_id `proc_0e5738780857`, PID `3800846`, launched via native
`terminal(background=true, notify_on_complete=true, pty=false)`. Completion notice:
**exit code 1**. Whole-workflow deadline 345600s (96 h) via `/usr/bin/timeout`.

Governing command: the exact Review 519 bash block (tracked job + 96-hour deadline +
fresh no-clobber Record 520), run once.

## Preflight (grouped, read-only, one pass, 2026-10-25T21:27:08Z)

Observed before launch: HEAD == origin/main == `c32ad0ad…`, index empty; the three
runtime sources equal to their blobs at `1f5629b`
(`cex002_reference_release.py` fed0d0ef49eb3704be577a378dfd12eb7e6876fc41fbfe9d6507e7ef5b83fe00,
`binance_usdm_harmonic_bundle.py` 1c9214d088c4279cf34e78c24d97a9bc14124491c27f5575edcca67c675cb48b,
`publish_binance_usdm_harmonic_bundle.py` cfb5b04f87226c9d1efbb39bbd04b634c40c7a20ddb868b8c6b3768d817b3fd9);
candidate physical SHA `8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34`;
proof physical SHA `3be8597604efc7353935d79fd663efd7ffa6083ede10f4807d458b9e76927c8d`
and exact size 264156517; environment executable and `/usr/bin/timeout` present; free
space 57,958,084,608 bytes; no prior checker/publisher process (native count 0, excluding
the checking shell); Record 520 and the `.publication` namespace absent and non-symlink
(`-L` explicit). Baseline read-only catalog: quarantine Q1 count 5 sha256
`b4334b2c…` (pin match), and release rows before admission count 0 / ids [].

## Terminal failure (from the raw block above)

- Workflow/deadline exit status: **1**; output capture exit status: **0**.
- Phase `admission` was the first and only phase started. Its `phase_result` recorded
  `exit_code` 1 with `elapsed_seconds` 0.71 and `stdout` empty. The `stderr` trace shows
  the production CLI failing during module import, before any publish logic ran:
  `publish_binance_usdm_harmonic_bundle.py` line 15 imports
  `cryptofactors.ingest.binance_usdm_harmonic_bundle`; importing the package
  `cryptofactors.ingest` triggers `cryptofactors/ingest/bitmex_funding.py` line 23
  `import httpx`, which raised `ModuleNotFoundError: No module named 'httpx'`.
- The orchestration then emitted `{"stage":"FAILED","phase":"admission",
  "error_type":"RuntimeError","error":"admission failed; no further phase is authorized"}`
  and stopped. **No `identical_replay` or `release_reader` phase ran.**

## Cause and scope of the failure

- The failure is an **environment-selection** condition: the isolated consumer
  environment `/tmp/cex002_nautilus_review511_env` does not provide `httpx`, which the
  production ingest package imports at module load. The CLI process exited 1 at import
  time, so no application initialization, no publish/verify logic, and no catalog or SQL
  write of any kind executed. This is the reviewer's environment-selection error, not a
  defect in the candidate, proof, production source, or data.
- No `BEGIN IMMEDIATE` transaction, no dataset/file/dependency rows, and no
  publication descriptor were written. The raw block's own before-admission catalog
  snapshot is consistent with an empty release state.

## Post-failure state (read-only)

- exp003.db release rows `transform_name='cex002_reference_publication'`: count **0**,
  ids [] (unchanged). Quarantine Q1: count 5, sha256
  `b4334b2c3f28d58a288b0130e1009dd305c5cf30b7e4af734f8036bd74d82103` (unchanged).
- `.publication` namespace absent. Candidate descriptor and proof physical pins unchanged
  (unchanged from preflight).
- HEAD == origin/main == `c32ad0ad06c111d015efb34d427cc6c28aa947fa`; index empty. No
  unrelated dirty path was touched by this workflow.

## Limitations

- No admission, identical replay or release-reader verification succeeded; no publication
  identity exists. This record is terminal failure evidence only.
- No retry, repair, rollback, cleanup, install, source/test edit, direct SQL, import
  probe or second execution was performed. No catalog admission occurred and no release
  acceptance is claimed. A complete catalog publication still would not constitute final
  CEX-002 acceptance; remaining economic examples and final acceptance suites remain
  mandatory and unassigned.
- The existing full consumer PASS (Record 518) and all prior preparation/proof/measurement
  evidence are preserved unchanged. Reviewer will separately authorize the existing
  environment (Record 510 shows the same CLI used `.venv/bin/python`) with fresh evidence
  after this publication.

## Record status

Record 520 is catalog-admission failure evidence owned by Hermes. CEX-002 remains
IN_PROGRESS; next ticket NONE; reviewer acceptance remains exclusive.
