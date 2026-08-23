# CEX-002 Coinalyze Provenance Correction

**Date:** 2026-08-22
**Reviewer:** Lead Quantitative Finance Researcher/Engineer
**Decision:** `RECORD223_ACCEPTED_FOCUSED_SOURCE_CORRECTION_AUTHORIZED`
**Architecture:** ADR-0021 as amended by ADR-0022 and ADR-0023
**Gate 1:** Accepted
**Gate 2:** Not accepted

## Record 223 review

Hermes's integration and failed execution are accepted as a faithful execution of review
222. Commit `005f4ee6154725ae7de0acc57e11a8acf702670b` contains exactly the five authorized
failed-measurement paths, is published at `origin/main`, and passes repository control and
restricted whitespace validation. The accepted sizing source and tests retain their exact
review-222 identities. Receipt 180 and the sizing-envelope tree remain absent, and the
complete 41,372-file evidence store was unchanged by the failed invocation.

The first exact invocation exited 1 before publication with:

```text
ERROR: a Coinalyze provenance record carries a credential field
```

Hermes correctly stopped without retrying, editing source, running the second invocation,
or mutating the evidence store.

## Root cause

This is a sizing-source conformance defect, not a credential leak and not invalid Gate-1
evidence. The pinned accepted report's five Coinalyze provenance records each contain:

```json
"header_names": ["api_key"]
```

That field records only the name of the request header. It contains no header value. The
same pinned block proves `key_location == "header"`, `key_present == true`, and
`query_contains_key == false`; every retained `params` map contains no credential key.
Qualification deliberately publishes sorted header names and never header values.

`resolve_coinalyze_evidence()` currently serializes the whole provenance record and rejects
the literal substring `api_key`. It therefore mistakes the required safe header-name
provenance for a stored credential. The sizing test fixture omitted `header_names` and the
other real provenance framing fields, so its success path did not exercise the accepted
record shape.

ADR-0021 already requires keys never to enter a URL, receipt, sizing artifact, or log. No
ADR change or report rewrite is needed. The implementation must distinguish an
authenticated header's name from a credential value while remaining fail-closed against
query credentials, header values, and unrecognized provenance fields.

## Authorized senior correction

Sr Dev - Claude Build on Claude Opus 5 is authorized to edit only:

1. `src/cryptofactors/acquisition/binance_usdm_harmonic_sizing.py`; and
2. `tests/acquisition/test_binance_usdm_harmonic_sizing.py`.

The correction must make `resolve_coinalyze_evidence()` prove all of the following before
reading or measuring retained Coinalyze response bodies:

- the report-level request framing is exactly header authentication: `key_location` is
  `header`, `key_present` is the boolean `true`, and `query_contains_key` is the boolean
  `false`;
- each provenance record has the accepted explicit field set: `byte_size`,
  `content_path`, `header_names`, `params`, `path`, `provenance_source`, `retrieved_at`,
  `sha256`, `status_code`, and `transport`; no unrecognized field may carry request
  headers, authorization data, a secret, or any other value;
- `header_names` is a list of strings exactly equal to `["api_key"]`; it is metadata about
  the header name and is allowed, but no header-value mapping or value field is allowed;
- `params` is a string-to-string mapping and contains no credential parameter under case,
  underscore, or hyphen spelling variants of `apiKey`; and
- failure messages and `SizingError.context` expose only safe structural facts such as the
  endpoint and offending field name, never a rejected value or serialized record.

Keep all existing endpoint-role, path-confinement, content-address, byte-size, digest, and
payload checks. Do not add credential or environment access, network behavior, caller
policy, permissive redaction, report rewriting, or a special case keyed only to the current
report hash.

The test fixture must use the complete accepted ten-field provenance shape. Remove the
dead `if False` credential branch. Add focused tests proving:

- the safe real shape with `header_names == ["api_key"]` resolves successfully;
- wrong/missing/extra header names and altered report-level framing block;
- query parameter keys `api_key`, `apiKey`, and `api-key` block even when their value is
  `<redacted>`;
- extra header-value, authorization, credential, or unknown fields block without echoing
  their values in the exception or context; and
- resolved evidence and serialized sizing outputs still contain neither a credential
  value nor request parameters/header metadata.

Preserve every other accepted sizing test and the exact sizing CLI bytes. Claude does not
run tests or Ruff, edit repository records, execute sizing, mutate data, use Git, commit,
push, or perform later work. Stop for reviewer source inspection and return both SHA-256
identities plus the unchanged CLI SHA-256.

This reviewer-authored governance publication is restricted to exactly:

1. `research/sprint_004/224_CEX002_COINALYZE_PROVENANCE_CORRECTION.md`;
2. `docs/handoff/CURRENT_TASK.md`; and
3. `tickets/CEX-002.md`.

The reviewer may stage, commit, and push only those three paths. No developer source,
test, evidence-store, database, or unrelated dirty path is part of this publication.

## Stop boundary

This authorizes one corrective source/test drop only. It does not authorize integration,
command execution, a retry, Gate-2 acceptance, acquisition, normalization, catalog work,
NautilusTrader, Harmonic Trader, payoff analysis, PAPER, LIVE, reduced scope, paid data,
or any next-ticket work. Next ticket remains `NONE`.
