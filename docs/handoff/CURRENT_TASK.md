# CURRENT_TASK

Ticket: ARCH-002
State: BLOCKED
Next required actor: Sr Dev — fix membership semantics (REVIEW-0217)
Next ticket authorized: NONE

## Review verdict

**CHANGES_REQUIRED** — see `docs/reviews/REVIEW-0217_ARCH-002_CHANGES_REQUIRED.md`

## Blocking (summary)

1. CMC dead-only graveyard used as universe membership → liquid panel empty / wrong
2. `key_map.get(iid, iid)` leaks raw `cmc_*` ids into paper universe
3. No real-catalog integration proof for sensible DATA-011 panel
4. Commit uncommitted `TYPE_CHECKING` circular-import fix with rework

## Required shape

tradable = (paper/bars panel) minus CMC-dead at t (name-safe), not dead-list as membership

## Governing documents

- tickets/ARCH-002.md
- docs/reviews/REVIEW-0217_ARCH-002_CHANGES_REQUIRED.md
- src/cryptofactors/universe/binding.py
- src/cryptofactors/execution/paper_loop.py
