# Implementation sequence

## Foundation gate

1. `CAT-001` — catalog/migrations.
2. `RAW-001` — immutable raw objects.
3. `MAN-001` — immutable dataset manifests.
4. `LEG-001` — legacy file census.
5. `AUD-001` — schema/coverage audit.

No source normalizer starts before the foundation gate passes.

## Reference and canonical data gate

6. `REF-001` — point-in-time identities.
7. `BIN-001` — first source normalizer.
8. `BAR-001` — canonical/daily reconciliation.
9. Add the second independent venue only after the first source passes.
10. Add funding, fees, quote FX, and execution routes.

## Research substrate gate

11. Historical universe snapshots.
12. As-of access API.
13. Label/event interval separation.
14. Purged chronological split engine.
15. Costed portfolio simulation.
16. Experiment bundles and fingerprints.
17. `EVD-001` operational registry integration.

## Research

18. Null/noise factor test.
19. Transparent factor baselines in preregistered order.
20. Simple composites.
21. ML challengers only after accepted baselines.

## Serving

22. Artifact/representation parity tests.
23. Explicit paper promotion.
24. Prospective holdout.

No live trading work is authorized by this sequence.
