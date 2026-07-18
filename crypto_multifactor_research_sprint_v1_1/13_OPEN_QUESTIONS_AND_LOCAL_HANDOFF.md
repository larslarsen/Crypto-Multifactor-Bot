# Open Questions and Local Handoff

These questions cannot be resolved from the public repository alone.

## Data inventory

1. What are the exact local paths, sizes, hashes, and schemas of all claimed datasets?
2. Are the 469 five-minute files distinct instruments or venue duplicates?
3. Which files contain delisted assets?
4. Are native and resampled daily bars both present, and which is authoritative?
5. Do all sources use UTC and bar-close timestamps?

## Instrument history

6. Is there a historical listing/delisting master?
7. Are token migrations and redenominations recorded?
8. Can wrapped and bridged forms be mapped without double counting?
9. Is historical perpetual availability known by asset and venue?

## Volume and execution

10. Which venue's volume is trusted, and why?
11. Are quote volume and base volume units consistent?
12. Are historical fees, spreads, and funding intervals available?
13. Are order-book or trade prints available for impact calibration?
14. Is the execution simulator tested against cash/funding reconciliation fixtures?

## Market cap and on-chain

15. Is point-in-time circulating supply available?
16. Do market-cap files preserve historical provider vintages?
17. What is the first-availability lag for each on-chain series?
18. Are historical on-chain values revised by the provider?
19. Is there an asset-to-chain/protocol taxonomy?

## Legacy research census

20. How many model, feature, universe, threshold, and slicing variants were actually run?
21. Which experiment scripts/results exist locally but are ignored by Git?
22. Which date range has been repeatedly inspected by humans?
23. Were any final thresholds selected after viewing 2025–2026 performance?
24. Is there a complete list of data leaks or discovered bugs?

## Required local export

Before architecture, run a local export that produces only metadata—not proprietary raw observations if those should remain private:

- dataset manifest with hashes;
- schema registry;
- instrument master;
- coverage-by-date summary;
- experiment-file inventory;
- requirements lock;
- test report;
- current fee/funding source map.

Once those files are available, the provisional entries in this package can be upgraded from `CLAIMED_LOCAL` to verified.

## Additional information-bar handoff required

25. What exact start/end timestamps produced each committed information model split?
26. What threshold was used by asset, and which observations were used to estimate it?
27. What were the class counts and prediction counts, including flat predictions, per fold?
28. Can per-observation predictions, timestamps, labels, and gross/net returns be exported?
29. What dataset, feature, environment, and code hashes produced every artifact?
30. Were the committed metrics produced by `eval_paper2_v2.py`, `model_trainer.py`, or another path?
31. Can true venue-specific raw price and volume inputs be supplied for the BloFin replication?
32. Are information-bar boundaries reproducible after appending new data?
33. What streaming state and late-data policy would serving use?

Do not wire the committed information models into the bot until these questions are answered and the causal replication passes.
