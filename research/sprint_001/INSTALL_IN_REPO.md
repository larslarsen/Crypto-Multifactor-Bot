# Installing this architecture into the GitHub repository

The current repository has the sprint package nested under `crypto_multifactor_research_sprint_v1_1/`. The clean target is a root-level project, not an architecture package nested beside the research package.

## Recommended migration commit

1. Create a branch such as `architecture-v1`.
2. Move the existing sprint directory to `research/sprint_001/` without editing its contents.
3. Copy this package’s `docs/architecture/`, `schemas/`, `configs/`, and `sql/` to repository root.
4. Review the small `scaffold/` directory, then copy its `pyproject.toml`, `src/`, and `tests/` to root.
5. Create a root `README.md` summarizing project status and linking to the research charter and architecture.
6. Create a local data root outside the repository and copy `configs/*.example.yaml` to untracked local configs.
7. Install the environment and commit the generated `uv.lock`.
8. Run the scaffold tests.
9. Open the first implementation issues from `07_IMPLEMENTATION_ROADMAP.md`.

## Do not do in this commit

- do not copy raw observations into Git;
- do not migrate legacy model or feature code;
- do not wire any serving bot;
- do not implement factors before the data catalog/audit;
- do not rename quarantined legacy artifacts as production candidates.

## Suggested commit sequence

1. `docs: accept research-driven architecture v1`
2. `build: initialize Python package and locked environment`
3. `feat(catalog): add SQLite control catalog`
4. `feat(storage): add immutable raw object registration`
5. `feat(audit): add legacy dataset manifest exporter`

Keeping these commits separate makes the formative data infrastructure easier to review and revert.
