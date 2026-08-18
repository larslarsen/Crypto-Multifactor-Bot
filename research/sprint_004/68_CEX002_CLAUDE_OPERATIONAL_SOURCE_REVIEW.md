# CEX-002 Claude Operational-Correction Source Review

Date: 2026-08-18

Reviewer: Lead Quantitative Finance Researcher/Engineer

Decision: **REJECT SOURCE DROP; JR INTEGRATION AND REAL RERUN UNAUTHORIZED**

## Reviewed identities

Committed control-plane base:
`HEAD == origin/main == d857ee531cf0f452c8a98efe6b86052aeeb5174c`.

| Path | SHA-256 |
|---|---|
| `src/cryptofactors/acquisition/binance_usdm_harmonic_qualification.py` | `fb16c40fa8b30c008b042ec386fde55d94866218ba8801f23b60a1e3a69addc2` |
| `scripts/research/qualify_binance_usdm_harmonic_sources.py` | `1dbba6085f1903e84974f6207a779eaf4f8994e1d121b1122a285aae940a226b` |
| `tests/acquisition/test_binance_usdm_harmonic_qualification.py` | `fd1e1fd494214f91a2805d2e0be6aea48858a791d9d0d4caddd6428d3e055a8c` |

The drop is confined to the three authorized paths. Focused Ruff and in-memory compilation
pass. No pytest or network command was run by the reviewer.

## Accepted direction

The patch correctly moves toward a shared physical-family inventory, request-keyed listing
records, immediate sample progress, retained-byte recovery, bounded retry, and an
inventory-first sample plan. Those design directions must be preserved.

## Blocking findings

### 1. Request-keyed listing checkpoints permit valid-page substitution

`ListingCheckpointStore.retained_bytes()` verifies only that the referenced bytes match
the digest stored in the checkpoint. It does not prove that:

- the checkpoint dictionary key is the canonical hash of its stored request;
- the stored request equals the request currently being resumed;
- the XML response's echoed prefix/delimiter/continuation token equals that request;
- the stored next-token/truncation metadata equals the parsed response; or
- the content path is the expected content-addressed path under the listing cache.

A reviewer direct probe mapped the request key for
`data/futures/um/monthly/trades/` to a different, internally valid retained page for
`data/futures/um/daily/metrics/`. The qualifier accepted it and returned the wrong metrics
prefix without a network request or integrity error. This violates provenance,
resumability, and the explicit review-67 requirement that tampered checkpoints fail closed.

### 2. Sample/checksum checkpoint authority is not fail-closed

The completed-sample resume path rehashes the raw bytes against `sha256` but only checks
that `provider_checksum` has 64 characters. A direct probe supplied a different valid-form
provider checksum; the code returned `checksum_match=True` while the claimed provider
checksum and raw SHA-256 disagreed.

The retained-sample recovery path also consumes a parsed checksum sidecar without first
proving that the sidecar still hashes to its content-addressed filename. A modified
sidecar can therefore become provider authority during recovery. Every accepted retained
sample must prove raw SHA-256, provider checksum, rehashed sidecar bytes, and sidecar
content address agree.

### 3. Malformed durable checkpoints silently become empty stores

Both sample-progress and listing-checkpoint loaders convert malformed JSON into an empty
mapping. Reviewer probes reproduced this behavior. Corruption or tampering can therefore
erase durable resume authority and cause remote work to be repeated silently. Existing
checkpoint files with invalid JSON, version, shape, key identity, or entry identity must
raise a typed resume-integrity failure; only a genuinely absent file may initialize an
empty store.

### 4. The preflight budget is not exact by unique remote object

When a sparse regime has one object, the plan aliases that object to early, middle, and
recent but charges its byte size three times. A direct probe planned one unique 10-byte
object as 30 new-download bytes. This can create false `sample_budget_exceeded` blocks and
does not represent the actual one-fetch physical plan. Regime aliases may remain, but each
unique remote key must be charged and fetched once; retained bytes must likewise be
reported once.

### 5. Required interruption and retry durability tests are incomplete

The new sample test observes that progress grows during a successful run; it does not
abort after a completed sample and prove that the resumed run fetches only missing remote
objects with semantic identity equal to an uninterrupted run. The new retry record also
lives only in memory until a successful report is returned. If retry exhaustion aborts the
run, its incidents are lost. In addition, checksum acquisition wraps
`TransportObjectIndex.fetch_bytes()` in a second call to the same retry runner, allowing
the nominal per-request attempt bound to multiply.

Review 67 requires a single bounded attempt policy per remote request, an atomically
durable redacted retry/incident journal, and actual interrupted-run equivalence tests.

## Reviewer evidence

- Focused Ruff over the three reviewed paths: PASS.
- In-memory AST compilation over the three reviewed paths: PASS.
- Cross-request retained-page substitution direct probe: FAIL CLOSED expected; wrong page
  accepted.
- Mismatched provider-checksum checkpoint direct probe: FAIL CLOSED expected;
  `checksum_match=True` returned.
- Malformed sample/listing checkpoint direct probes: FAIL CLOSED expected; empty stores
  returned.
- Unique-object sample-budget direct probe: expected 10 bytes; reported 30 bytes.

These are source-contract failures. Pytest execution would not change the decision and is
not authorized for this rejected drop.

## Publication transition

Jr Dev — Hermes must publish only:

- `docs/handoff/CURRENT_TASK.md`;
- `research/sprint_004/68_CEX002_CLAUDE_OPERATIONAL_SOURCE_REVIEW.md`; and
- `tickets/CEX-002.md`.

Hermes runs only `python3 scripts/check_repo_control.py` and `git diff --check`, verifies
the staged path list, commits, pushes, and establishes `HEAD == origin/main`. It excludes
the rejected three-path source/test drop and every unrelated dirty path. It performs no
test, network, source edit, data deletion, or integration.

Once the committed branch contains this review and the matching governance sections,
Sr Dev — Claude Build using Claude Opus 5 is automatically authorized for the surgical
correction below. No ephemeral prompt or owner-supplied hash is required.

## Surgical correction authorization

Claude may edit only the same three reviewed paths. It must preserve the accepted design
direction and:

1. strictly validate checkpoint document version/shape and every request key, request,
   response self-identity, parsed page metadata, digest, and cache-local
   content-addressed path before listing reuse;
2. strictly validate sample checkpoint shape and require raw digest, provider checksum,
   rehashed retained sidecar, sidecar content address, object identity, and retained raw
   bytes to agree before reuse or recovery;
3. raise `ResumeIntegrityError` for any present malformed or inconsistent checkpoint;
4. account and acquire new and retained bytes once per unique remote object while retaining
   explicit regime/product aliases;
5. use exactly one bounded retry owner per remote request and atomically persist redacted
   retry incidents as they occur so interruption cannot erase them; and
6. add deterministic tests for checkpoint-document corruption, cross-request page
   substitution, provider-checksum substitution/tampering, unique-object budget accounting,
   retry-attempt bounds, and a real injected abort-after-sample followed by missing-only
   resume and semantic-identity comparison.

The correction must preserve the existing 263 listing/checksum blobs and six raw samples;
no implementation or test may delete or mutate `data/cex002_qualify`.

Claude performs no pytest, network run, integration, repository-record edit, Git operation,
commit, push, purchase, Gate 2 work, or model work. It stops for fresh reviewer source
inspection with exact hashes.

## Gate decision

Gate 1 remains `IN_PROGRESS`. The current implementation must not be run against real
sources. Gate 2 and harmonic-model development remain unauthorized. There is no partial
PASS.
