# Crypto Multifactor Platform — Implementation Handoff v1

**Status:** architecture extension and coding handoff  
**Date:** 2026-07-18  
**Purpose:** add enforceable platform boundaries, an Evidence Registry, detailed implementation tickets, and constrained prompts for an AI coding agent.

This package is an additive overlay for the `Crypto-Multifactor-Bot` repository. It does not replace the research sprint or architecture package. It converts two agreed design decisions into implementation contracts:

1. the platform is divided into **Data**, **Research**, and **Execution** layers with explicit dependency rules;
2. hypotheses, evidence, experiments, and decisions are recorded in an append-only **Evidence Registry**.

## Package layout

- `repo_overlay/`: files intended to be copied into the repository root.
- `handoff/`: operating instructions and prompts for Hermes or another coding agent.
- `PACKAGE_MANIFEST.json`: hashes and sizes for every file.
- `PACKAGE.sha256`: hash of the manifest.

## What to do first

1. Read `APPLY_TO_REPO.md`.
2. Copy `repo_overlay/` into the repository root without deleting existing files.
3. Give Hermes `handoff/HERMES_START_HERE.md` as its governing prompt.
4. Assign only `CAT-001` first.
5. Require a reviewable commit and passing tests before assigning `RAW-001`.

## Important boundary

This package contains specifications, migrations, schemas, tests, and small reference modules. It deliberately does **not** implement exchange collectors, factor models, or trading logic. Those are downstream of the catalog and raw-object foundations.
