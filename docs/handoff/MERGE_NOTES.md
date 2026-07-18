# Merge notes

## Expected additions

- ADRs 0007–0010;
- architecture documents 11–15;
- Evidence Registry schemas and migration 0002;
- layer dependency matrix and checker;
- detailed implementation tickets;
- Hermes prompts;
- small reference contracts and tests.

## Likely manual merges

- Main Typer CLI: add evidence and catalog command groups only when implemented.
- Migration numbering: rename `0002_evidence_registry.sql` if the repository already has a migration 0002, preserving content and updating references.
- Existing package domains: map the dependency matrix to actual directory names rather than creating duplicate packages.
- Existing CI: merge checks into the current workflow.

## Do not merge blindly

Do not overwrite a newer control schema or pyproject. This overlay intentionally avoids supplying replacements for those root files.
