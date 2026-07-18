#!/usr/bin/env python3
"""check_repo_control.py

Lightweight governance control check for the Crypto Multifactor repo.

Checks for presence of required governance artifacts and basic structure.
Intended to be run in CI and by agents before review handoff.
"""

from pathlib import Path
import sys

REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "docs/ARCHITECTURE_RFC.md",
    "docs/handoff/CURRENT_TASK.md",
]

REQUIRED_DIRS = [
    "tickets",
    "docs/adr",
    "research",
    "scripts",
]

def check_file(p: Path) -> bool:
    if not p.exists():
        print(f"MISSING: {p}")
        return False
    if p.stat().st_size == 0:
        print(f"EMPTY: {p}")
        return False
    return True

def main():
    root = Path(__file__).resolve().parent.parent
    ok = True

    for rel in REQUIRED_FILES:
        if not check_file(root / rel):
            ok = False

    for rel in REQUIRED_DIRS:
        d = root / rel
        if not d.exists() or not d.is_dir():
            print(f"MISSING DIR: {rel}")
            ok = False

    # Check that there is at least one active-style ticket
    tickets_dir = root / "tickets"
    if tickets_dir.exists():
        ticket_files = list(tickets_dir.glob("*.md"))
        if not ticket_files:
            print("NO TICKETS FOUND")
            ok = False

    if ok:
        print("Repo control check: PASS")
        sys.exit(0)
    else:
        print("Repo control check: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
