# Reviewer instructions

Review foundational tickets more strictly than model code. A defect in identity, time semantics, immutability, or lineage propagates into every later result.

For every pull request, verify:

- scope matches one ticket;
- dependencies follow the layer graph;
- migrations are forward-only and transactional;
- IDs are deterministic where specified;
- repeated commands are idempotent;
- files are written atomically;
- clocks use explicit UTC;
- paths are configurable and normalized;
- failures are recorded and fail closed;
- tests exercise corruption, retry, duplicate, partial-write, and boundary cases;
- no hidden network access occurs in research code;
- no observed research result changes a preregistered criterion in the same commit.

Reject changes that are clever but difficult to audit. Prefer explicit code and narrow interfaces.
