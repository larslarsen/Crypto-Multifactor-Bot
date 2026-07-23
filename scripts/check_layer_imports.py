#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

LAYER_NAMES = {
    "core", "catalog", "ingest", "reference", "quality", "market", "universe",
    "factors", "labels", "validation", "portfolio", "evidence", "experiments",
    "serving", "execution",
}

ALLOWED = {
    "core": set(),
    "catalog": {"core"},
    "ingest": {"core", "catalog"},
    "reference": {"core", "catalog"},
    "quality": {"core", "catalog", "reference"},
    "market": {"core", "catalog", "reference", "quality"},
    "universe": {"core", "catalog", "reference", "market"},
    "factors": {"core", "catalog", "reference", "market", "universe", "labels", "validation"},
    "labels": {"core", "catalog", "reference", "market", "universe"},
    "validation": {"core", "labels"},
    "portfolio": {"core", "market", "universe", "factors", "labels"},
    "evidence": {"core", "catalog"},
    "experiments": {"core", "catalog", "reference", "market", "universe", "factors", "labels", "validation", "portfolio", "evidence"},
    "serving": {"core", "catalog", "reference", "market", "universe", "factors", "portfolio"},
    "execution": {"core", "catalog", "reference", "market", "portfolio", "serving"},
}


def package_layer(path: Path, root: Path) -> str | None:
    relative = path.relative_to(root)
    return relative.parts[0] if relative.parts and relative.parts[0] in LAYER_NAMES else None


def imported_layer(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "cryptofactors" and parts[1] in LAYER_NAMES:
        return parts[1]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("src/cryptofactors"))
    args = parser.parse_args()
    root = args.root.resolve()
    violations: list[str] = []
    if not root.exists():
        print(f"layer root does not exist: {root}", file=sys.stderr)
        return 2
    for path in sorted(root.rglob("*.py")):
        importer = package_layer(path, root)
        if importer is None:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        modules: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend((node.lineno, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append((node.lineno, node.module))
        for line, module in modules:
            imported = imported_layer(module)
            if imported and imported != importer and imported not in ALLOWED[importer]:
                violations.append(f"{path}:{line}: {importer} may not import {imported} ({module})")
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    print("layer import check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
