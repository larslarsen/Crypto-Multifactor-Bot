# REVIEW-0104 - FEE-001 DECIMAL IDENTITY CORRECTION REQUIRED

**Ticket:** FEE-001 - Point-in-Time Fee Schedules and Conservative Assumptions
**Disposition:** BOUNDED SR SOURCE CORRECTION
**Assigned model:** Sr Dev - Grok Build 4.5, resume the same session
**Next ticket authorized:** `NONE`
**Date:** 2026-07-21

## Accepted Source Design

The migration shape, typed model, transaction boundary, bitemporal overlap predicate, contiguous
knowledge-time correction, historical as-of behavior, exact instrument/tier lookup, and no-fallback
contract are approved for Jr testing. Do not redesign them.

## Required Correction

Edit only `src/cryptofactors/reference/store.py`:

1. Make fee-rate input strict: public add, supersede, and ID-helper paths accept `Decimal` values only
   (plus `None` for unchanged supersession fields). Reject bool, int, float, string, and every other
   type with `ReferenceValidationError`. Continue rejecting non-finite and out-of-range Decimals.
2. Make `_decimal_to_store` a unique numeric canonicalization: fixed-point, no exponent, no trailing
   fractional zeros, no trailing decimal point, and exactly `"0"` for every signed/scaled zero.
   Numerically equal Decimals such as `Decimal("0.001")` and `Decimal("0.0010")` must produce the same
   stored text and deterministic ID. Numeric Decimal equality, not input quantum, is the round-trip
   requirement.
3. Make public `fee_schedule_id_for` apply the same fee-tier normalization, fee-rate validation, and
   evidence-class validation as insertion. Calling the helper directly must never produce an ID that
   insertion would reject or normalize differently.

Preserve all other source behavior and the migration unchanged. Do not edit tests, records, tickets,
handoff, README, backlog, or review files. Do not run tests or Git commands.

## Local Preflight And Stop

Verify `pwd` is `/home/lars/Crypto_Multifactor_Bot` and this exact review file exists. If either check
fails, report and stop. Otherwise make the bounded correction, report the changed source file and exact
API behavior, then stop for Reviewer inspection.
