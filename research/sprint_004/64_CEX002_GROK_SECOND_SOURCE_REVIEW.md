# CEX-002 Grok Second Corrective Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT TWO RESIDUAL SEMANTIC DEFECTS AND ONE TEST-SOURCE DEFECT; DO NOT INTEGRATE**

## Reviewed identities

Committed control-plane base:
`HEAD == origin/main == 867d392447b9584ee0781743e424740dbdcda0e2`.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `1d99d169b6433bdea7d644c8b370a65ff32ce83635fb681ce791f304a6ea464e` | 68,794 |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `af3aca3cf461ce2cfd31dd8db5b4aa53a9c1e5332a7bc8a622f250a3bb2855f6` | 3,127 |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `5555b6630b6016ac31e7760123761104656074832c54a2ba805a340b326b12d9` | 22,734 |

All fixture hashes remain those recorded in review 63.

## Accepted corrections

This patch correctly closes three important subproblems:

- the real-shaped metrics row is now recognized as headerless data while unexpected
  headed schemas fail closed;
- requested Coinalyze markets and returned history symbols are checked, and the matched
  market's actual `oi_lq_vol_denominated_in` value is reported; and
- an explicitly listed symbol prefix with zero objects is recorded and blocks the current
  product-completeness predicate.

These corrections must be preserved.

No new pytest cache was produced after this patch. The reviewer did not execute pytest.

## Residual blocking findings

1. **Coverage still compares only symbols already listed inside each product family, not
   the full discovered universe.** `_uncovered_listed_symbols` iterates
   `family_symbol_lists`, so a universe member with no prefix in a product family is absent
   from both the coverage map and the uncovered set. A direct probe discovered
   `BTCUSDT, ETHUSDT` from the archive union, exposed only `BTCUSDT` under one-minute
   klines, and still returned `binance_usdm_bar_1m authority='official',
   official_complete=True`, with no `ETHUSDT` gap. The prior focused test covers an empty
   prefix, not an absent prefix. Review 63 required comparison against the discovered
   universe, so silent product omission remains possible.
2. **The reported Coinalyze response hash and retrieval identity are synthesized after
   parsing rather than taken from retained raw response bytes.** `HttpxCoinalyzeTransport`
   discards `DownloadResult`, and `CoinalyzeClient._fetch` hashes a canonical
   `json.dumps(payload)` reconstruction and timestamps it after return. Direct evidence for
   the future-markets fixture reported 583 bytes and SHA-256
   `58e9400beee74ad056be1066d10353a094b97a6a25fefde3f53fd16771765233`;
   the retained raw response-shaped fixture is 741 bytes with SHA-256
   `cfe4bfc7a5c85e9ec6c550859438d431353109a0a58b30ebd7aeab84d6ac37a9`.
   A hash of reconstructed JSON is not raw source provenance and cannot reconcile the
   retained response object.
3. **The new mismatch test does not match the implemented failure.** The ETH market exists
   in the future-markets fixture, so the client correctly reaches the history check and
   raises `Coinalyze history symbols do not match request`. The test expects
   `missing requested symbols`; Hermes would therefore encounter a focused test failure.

## Reviewer evidence

- In-memory compilation of all three Python paths: PASS.
- Focused Ruff check of all three Python paths: PASS.
- Scoped `git diff --check`: PASS.
- Full-universe/absent-family-prefix direct probe: FAIL as described above.
- Raw-response identity comparison: FAIL as described above.
- Coinalyze mismatch exception direct probe: source rejection is correct; test-source
  expectation is wrong.
- Pytest and network qualification: not run because source is rejected.

## Routing decision

Grok 4.6 High has now produced two rejected corrections on this source-authority task.
Continuing with the same actor is not the best expected usage per accepted result.
Sr Dev — Claude Build using Claude Opus 5 is authorized for the next bounded correction,
providing project-specific evidence for future Grok-versus-Claude routing.

Claude must patch, not rewrite, the accepted source. The correction is limited to:

1. full-discovered-universe coverage accounting for every required logical product family,
   including symbols with no family prefix, with explicit blocking/unavailability evidence;
2. a structured Coinalyze transport result whose production provenance comes from the
   retained raw `DownloadResult` bytes/hash/retrieval identity, with redacted request
   metadata and an equivalent raw-byte-capable memory fixture contract; and
3. a correct focused mismatch test expectation plus focused absent-prefix and raw-hash
   tests.

Claude may edit only the reviewed production module, CLI if the structured transport result
requires wiring, test module, and existing bounded fixture directory. It performs no test
or acceptance-command execution, network run, integration, repository-record edit, Git
operation, commit, push, purchase, catalog mutation, or publication. It stops for reviewer
source inspection with exact hashes. Jr integration remains unauthorized.
