# ADR 0018 - Resumable Bounded Listing Execution

- **Status:** Accepted
- **Date:** 2026-08-20
- **Extends:** ADR-0017 execution mechanics only
- **Evidence:** `research/sprint_004/115_CEX002_PLAN3_CANDIDATE_RESUME.md` and
  `research/sprint_004/116_CEX002_LISTING_EXECUTION_ARCHITECTURE_REVIEW.md`

## Context

CEX-002 must inventory the complete official archive scope declared by ADR-0017. Two
bounded candidate runs proved correct resume behavior but advanced only 1,718 listing
pages in approximately 110 minutes. At the second stop, the checkpoint held 31,131
requests. Exact one-hour monthly klines were present for 983 symbol prefixes, exact
one-hour daily klines had reached only 378 symbol prefixes, and exact one-hour
mark-price, index-price, and premium-index object listings had not begun.

The delay is execution overhead, not a reason to reduce the universe or required fields.
The current path traverses families, symbols, and pagination serially; opens and closes a
new HTTP client for each page; and rewrites the complete roughly 25 MB checkpoint after
each newly retained response. Repeating 50-minute slices would spend many more hours on
listing mechanics and increase checkpoint write amplification as the file grows.

## Decision

The CEX-002 listing execution path will preserve the exact source, universe, cadence,
integrity, and report contracts of ADR-0017 while changing only transport and checkpoint
execution mechanics:

1. One qualification invocation reuses bounded HTTP connection resources and closes them
   deterministically on success, error, or controlled Python cancellation/unwinding.
   Abrupt process termination relies on operating-system resource reclamation and the
   crash-recovery rule below. Secrets remain header-only and redacted.
2. Independent listing requests may use bounded concurrency with explicit backpressure.
   The worker ceiling is finite and inspectable. Request retry limits remain per request;
   concurrency may not multiply a retry budget or create overlapping ownership.
3. Checkpoint publication has one deterministic writer. Completion order may not change
   semantic inventory, report identity, incident ordering, request-to-content bindings, or
   canonical checkpoint key order. Raw checkpoint hashes may differ across independent
   cold executions only where actual retrieval timestamps are retained as evidence.
4. The full checkpoint is not rewritten for every page. Newly downloaded listing bytes
   are first published immutably by content hash. Checkpoint updates are amortized and
   explicitly flushed at normal boundaries. After interruption, uncheckpointed retained
   responses are recovered from their self-identifying bytes before any repeat fetch.
5. Bootstrap skips cache blobs already bound by the loaded checkpoint instead of rehashing
   and reparsing every known blob. A response is still rehashed and its echoed request and
   pagination metadata are revalidated whenever that request is consumed. Unknown,
   malformed, mismatched, or tampered evidence continues to fail closed or remain typed
   unclaimed evidence under the existing contract.
6. Resume uses the existing checkpoint and cache in place. No deletion, relock,
   reconstruction, authority migration, raw acquisition, or reduced listing scope is part
   of this decision.
7. The programmatic qualification function remains serial by default for backward
   compatibility. The production CLI supplies the bounded worker default explicitly;
   tests and other callers opt into concurrency deliberately.

## Required proof

Deterministic tests must establish connection reuse and closure, thread-safe first use,
the concurrency ceiling, single-writer checkpoint integrity, bounded full-checkpoint
serialization count, recovery of interruption between content publication and checkpoint
flush, no refetch of recovered requests, tamper rejection, stable serial-versus-bounded
semantic identity and request-to-content mappings after normalizing real retrieval times,
stable retry evidence ordering, and unchanged candidate authority/raw/report behavior.

## Consequences

- Complete historical membership and every required derivatives field remain mandatory.
- Listing cache size is execution evidence, not release storage and not a data-scope
  substitute.
- A later real resume is authorized only after source acceptance and Hermes integration.
- Gate 1, acquisition, Gate 2, Nautilus, and Harmonic Trader work remain unauthorized.
