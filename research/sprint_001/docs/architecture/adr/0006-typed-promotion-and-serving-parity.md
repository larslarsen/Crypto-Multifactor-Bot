# ADR-0006 — Typed artifact promotion and serving parity

**Status:** Accepted

## Decision

Models enter paper/live serving only through an explicit promotion record and a complete typed manifest. Research and serving share approved factor/preprocessing code. Filename discovery is prohibited.

## Rationale

The legacy information-bar/time-bar mismatch shows that artifact naming is not a representation contract.

## Consequences

- More metadata before promotion.
- Serving fails closed on incompatible inputs.
- Quarantined artifacts can remain available for forensic analysis without accidental activation.
