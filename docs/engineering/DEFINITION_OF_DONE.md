# Definition of Done

A ticket is done only when:

- acceptance criteria are demonstrated;
- tests cover success and relevant failure paths;
- code is formatted, linted, and type-checked;
- migrations apply to a new database and an existing prior-version database;
- commands are idempotent where required;
- logging is structured and contains stable run IDs;
- no secrets or local absolute paths are committed;
- documentation and examples match actual behavior;
- resource use is bounded for the target machine;
- no new architecture dependency is introduced without an ADR;
- the reviewer can reproduce the result from documented commands.
