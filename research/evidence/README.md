# Evidence Registry source files

The SQLite registry is the operational control record. These versioned files seed and document the initial hypotheses. Generated current-state exports must be reproducible from append-only registry events.

- `hypotheses.yaml`: current append-only hypothesis identities and registered version definitions.
- `templates/`: authoring templates.
- `status_model.md`: lifecycle and verdict semantics.

Do not edit an already registered hypothesis version to reflect later knowledge. Add a new version and a decision event.
