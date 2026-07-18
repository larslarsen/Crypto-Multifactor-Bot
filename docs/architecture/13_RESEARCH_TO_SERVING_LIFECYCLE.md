# 13 — Research-to-Serving Lifecycle

## Stages

1. **Idea** — recorded as a draft hypothesis; no implementation commitment.
2. **Registered** — falsifiable version frozen before primary results are observed.
3. **Data-ready** — required point-in-time inputs pass acceptance gates.
4. **Baseline test** — transparent implementation with costed portfolio evaluation.
5. **Robustness** — alternate periods, venues, definitions, cost cells, and dependence-aware inference.
6. **Supported or closed** — append-only evidence decision.
7. **Artifact candidate** — frozen code, datasets, environment, model/policy manifest.
8. **Parity validation** — batch replay and streaming/serving outputs match within declared tolerance.
9. **Paper promotion** — explicit promotion event; fail-closed paper operation.
10. **Prospective holdout** — no retuning during the sealed evaluation window.
11. **Live consideration** — separate governance decision, not part of architecture v1.

## Promotion gates

A serving artifact must identify:

- source hypothesis IDs and versions;
- experiment fingerprint;
- immutable training datasets;
- feature/representation contract;
- preprocessing hashes;
- universe and cost policy versions;
- dependency lock and code commit;
- approved stage and promotion event.

## Retirement

Retirement is append-only. A retired artifact remains reproducible and auditable but is no longer eligible for decisions.

## Emergency behavior

Operational failure may stop decisions or retire an artifact. It may not trigger ad hoc retraining, threshold changes, or a switch to an unpromoted model.
