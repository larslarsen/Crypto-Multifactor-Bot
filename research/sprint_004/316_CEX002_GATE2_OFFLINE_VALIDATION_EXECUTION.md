# CEX-002 Gate-2 Offline Validation Execution

- **Date:** 2026-08-27 UTC
- **Actor:** Jr Dev — Hermes
- **Ticket:** CEX-002
- **Gate 2:** in progress; no real plan or acquisition authorized
- **Next ticket:** `NONE`

## Validation history

The Review 307 targeted acquisition suite passed once: 177 tests, exit 0, 27.333 seconds,
from `2026-08-26T23:47:54.106542354Z` to `2026-08-26T23:48:21.435360032Z`.
Review 308 focused Ruff then passed once. Its shared-dirty full suite was rejected as
contaminated evidence after exit 1 with 20 failures. Review 313's detached `/tmp` suite was
rejected because device 47 differed from receipt device 64513. Review 314's same-device clean
suite then completed once with exit 1, 5 unrelated baseline failures and no errors, from
`2026-08-27T05:21:53.106341119Z` to `2026-08-27T06:07:38.778400320Z`, 2745.672 seconds.
The five failures were the missing ignored Uniswap pilot fixture DB, the BitMEX six-versus-five
symbol expectation, and three restored EXP-009 binding-evidence mismatches. No Gate-2 test
failed; ticket-wide pytest remains blocked by those unrelated committed baseline defects.

## Clean same-device checks

Review 315's failed worktree `/home/lars/.cache/tmp/cex002-clean-qbGp3y` was removed. A fresh
detached worktree `/home/lars/.cache/tmp/cex002-clean-zyfjn3` was created at current HEAD,
then removed after validation. The shared worktree was not cleaned or otherwise altered.

The synchronized repository, `/home/lars/.cache/tmp`, receipt 258, fresh worktree, and its
receipt copy all proved numeric device `64513`. The shared Gate-2 paths were clean before
validation, with no staged path. The worktree used the shared virtual environment only through
`.venv` symlink `/home/lars/Crypto_Multifactor_Bot/.venv` and exported:

```text
PYTHONPATH=/home/lars/.cache/tmp/cex002-clean-zyfjn3/src
```

Import resolution proved:

```text
/home/lars/.cache/tmp/cex002-clean-zyfjn3/src/cryptofactors/__init__.py
```

## Remaining offline commands

The exact repository-wide Ruff command ran once from the clean worktree:

```text
.venv/bin/python -m ruff check src/cryptofactors/ scripts/
```

- Start: `2026-08-27T07:09:08.891753362Z`
- End: `2026-08-27T07:09:09.003844076Z`
- Elapsed: `0.113` seconds
- Exit: `0`
- Output: `All checks passed!`

The exact control command ran once, after Ruff:

```text
python3 scripts/check_repo_control.py
```

- Start: `2026-08-27T07:09:18.757195669Z`
- End: `2026-08-27T07:09:18.825052903Z`
- Elapsed: `0.068` seconds
- Exit: `0`
- Output: `Repo control check: PASS`

Final accepted Gate-2 identities remain:

- acquisition source: `0f8bbf70db167420b5fd5e3b3d0e4d5ed441de580c886909c7bd55426a233981`
- CLI: `6f4b56ecb43dcc448eb6c8cf765e38d9fa3923432459574d913582e3d9c84043`
- test source: `6157fd1f6ba0feccb83965a0ac383985577763edcedc92b0980a4c4cbd499ad6`

The Gate-2 paths remained clean. The shared worktree's unrelated modified and untracked
paths were preserved and were not staged or modified. No source/test repair, real plan,
acquire/verify, network, data mutation, or later-ticket work occurred. Final ticket-wide
pytest acceptance is still blocked by the five unrelated baseline defects and is not converted
to a pass by this record.
