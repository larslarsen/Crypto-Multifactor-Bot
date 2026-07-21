# FX-002 - JR SOURCE AUDIT CORRECTION TASK

**Ticket:** `tickets/FX-002.md`
**Actor:** Jr Dev - Hermes
**Status:** COMPLETED
**Next ticket:** `NONE`

## Assignment

Correct FX-002 under REVIEW-0082 without implementing production code, schemas, migrations, or ADRs.

## Required Evidence Corrections

- Kraken REST: record exact requested `since`, returned minimum/maximum timestamps, row count, and
  cap behavior. Classify it incremental/current only when old `since` is ignored by the capped
  response. Do not label current rates as a historical depeg.
- Kraken bulk: test the repository-known official bulk host/path only. If inaccessible or schema/
  licensing/revision behavior remains unverified, record the exact blocker and fail historical PIT.
- Coin Metrics: inspect the actual Community metric catalog for USDT/USDC USD price/reference-rate
  metrics. If present, query with the repository-accepted date-window and pagination parameters,
  never `limit`; otherwise reject with exact catalog evidence.
- DefiLlama: capture the exact endpoint response/error and determine only what the observed payload
  proves about history, timestamps, revisions, and licensing.
- Binance: preserve secondary-only status and capture the exact repository evidence supporting the
  absence of an independent direct USD anchor.
- For every response, record exact URL/request parameters without ellipses, retrieval UTC, byte
  size, SHA-256, returned time bounds, provider/error status, and licensing citation.
- Remove provider raw payloads from repository paths and Git publication. Store them in an approved
  external staging path; keep only hashes, metadata, and minimal licensing-safe excerpts in Git.

## Decision Rule

Recommend a primary only if direct USD direction, historical depeg coverage, observation and
availability semantics, revisions/vintages, raw reproducibility, and licensing all pass. Partial,
unknown, assumed, current-only, or inaccessible is a failure. Otherwise recommend exactly `NONE`.

## Exact Acceptance Commands

1. `python3 scripts/check_repo_control.py`
2. `PYTHONPATH=src uv run pytest -q --tb=short`

Run both exactly and record their actual complete outcomes; do not use hypothetical results.

## Records And Publication

Correct the report, evidence register, decision matrix, source notes, ticket, README, backlog,
handoff, and task/review statuses. Set FX-002 to `AWAITING_REVIEW`, name Reviewer as next actor,
retain `Next ticket authorized: NONE`, commit allowed records only, and push.

## Completion Condition

The published repository contains no raw provider payloads, has reproducible exact evidence, and
makes one decision that follows every gate without assumptions.
