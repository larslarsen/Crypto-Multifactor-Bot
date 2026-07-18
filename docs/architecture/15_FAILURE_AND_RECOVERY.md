# 15 — Failure and Recovery

## Principles

- fail closed;
- preserve source bytes and prior outputs;
- record failed attempts;
- make retries idempotent;
- publish only after validation;
- never expose partial datasets as complete.

## File publication

Write to a temporary file on the same filesystem, flush and fsync, hash, then atomically rename. Register the object only after successful publication. Orphan temporary files are safe to remove after a configured age.

## Database transactions

Catalog mutations are short and transactional. Files are published before the final catalog transaction, and unreferenced published files are discoverable by reconciliation.

## Recovery jobs

- orphan temporary-file cleanup;
- unregistered-content reconciliation;
- catalog-to-filesystem integrity scan;
- manifest dependency verification;
- stale run detection;
- quarantine review.

## No silent continuation

A failed required partition, unresolved instrument, incompatible schema, or stale serving input blocks downstream publication. Partial research panels are permitted only when explicitly declared by the dataset contract and represented by missing-reason fields.
