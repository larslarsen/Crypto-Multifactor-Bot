# ADR 0009 — Research decisions are append-only

- **Status:** Accepted
- **Date:** 2026-07-18

## Decision

Hypothesis verdicts, model promotions, retirements, corrections, and reopenings are represented as events. Existing events are never edited or deleted. Current state is derived from the latest valid event.

## Rationale

Mutable status fields erase the sequence of judgment and make hindsight changes hard to detect.
