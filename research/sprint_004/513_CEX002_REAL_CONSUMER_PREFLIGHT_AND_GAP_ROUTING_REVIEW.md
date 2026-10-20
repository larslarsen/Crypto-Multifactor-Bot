# CEX-002 Review 513 — Real consumer preflight and bar-gap routing

Reviewer: Lead Quantitative Finance Researcher/Engineer
Ticket: CEX-002, IN_PROGRESS; next ticket NONE
Source actor: Sr Dev — Codex Sol, GPT-6 Sol High (sole bounded senior)
Architecture: ADR-0039 unchanged

## Accepted starting point and actual-manifest finding

Review511 accepts integration b186b3a250ee147bb8d55311090bfb232f90e3ab,
Record512, the senior's 22 targeted cases, final scoped Ruff/control/whitespace.
Preserve those results and all accepted data. Candidate remains
8b46bebac377331a08ff1755f2a2c5362f47994939b61837542dfc9628bc9c34.

Before real execution the reviewer inspected the eleven pinned JSON manifests.
The bar manifest has 22,633 main tables /16,033,469 rows with component="", and
one 154-row gap table with component="quality_gap". BOTH have role="partition".
Current native-Bar selection uses dataset type and role only, so the real gap
schema would be rejected for lacking OHLC. The original tiny full-proof fixture
contains no bar-gap table and omitted the real component field. No consumer
execution has occurred and no data correction is warranted.

Actual gap reference:
data/.cex002_bar_1h/.quality-gaps/467853875cfb1570dcb6de953f4af54af03cab4adf6c9fd7a39143a83c4cc9e4.parquet
154 rows; 5,039 bytes; SHA256 467853875cfb1570dcb6de953f4af54af03cab4adf6c9fd7a39143a83c4cc9e4.

## Exactly two writable senior paths and fixed decision

- scripts/research/check_cex002_nautilus_consumer.py
- tests/test_cex002_nautilus_consumer.py

Select the existing GPT-6 Sol High actor for this small reviewer-designed guard
and representative fixture correction, using its accepted codec/proof context.
GPT-6.1 remains stronger reviewer; no second senior or new architecture.

For TABLE components in the bar dataset, require the accepted role="partition"
and an explicit component of either "" or "quality_gap". Only component=""
gets mandatory native Bar projection; a quality_gap table gets complete custom
row transport and the same proof/digest/schema authentication. Reject unknown or
missing component tags and unknown roles; malformed primary bar schema must still
fail and cannot opt out by dropping columns. Do not infer type from field shape.

Update tiny private fixtures to include actual component tags. Add a real gap
schema/table within the eleven-dataset end-to-end test, proving its exact source
and readback digests and inclusion through the strict existing verifier, while
main bars still receive native write/readback. Add malformed primary schema and
unknown/missing tag/role refusal cases. All existing tests remain; no production
candidate overrides, codec/proof/resource/schema changes or data editing.

The corrective senior-test exception authorizes exactly ONE execution after edits:

```
PYTHONPATH=src /tmp/cex002_nautilus_review511_env/bin/python -m pytest tests/test_cex002_nautilus_consumer.py -o addopts='' -q --tb=short -ra
```

Stop at first nonzero and return exact full command/output/status without repair
or retry. If all pass, return frozen two-path hashes/line counts for source review.
No other tests, lint, probes/import commands, install, real data, records, Git,
commit, push or integration. The existing pinned isolated environment is reused.
Hermes is not yet authorized to validate/integrate or run real data. Reviewer will
separately enumerate that workflow after source acceptance. No full-release proof,
admission, economic promotion, other ticket or automatic cleanup.

## Capacity/scale observation (reviewer metadata only)

At this continuation, df reports 298,949,865,472 SSD bytes available and
30,694,170,624 /tmp bytes. Fixed operating reserve remains 29,690,701,415.
Physical release rows remain 1,165,116,869. Cost calibration alone has 939,131,092
rows, including 882,076,090 retained ticker rows. Full real runtime cannot be
claimed from fixture timings; bounded actual-component measurements are needed.
No throughput result or consumer PASS exists yet.

## Reviewer governance publication scope

Exactly this Review513, docs/handoff/CURRENT_TASK.md and tickets/CEX-002.md.
No developer source/test/evidence/data integration by the reviewer.
