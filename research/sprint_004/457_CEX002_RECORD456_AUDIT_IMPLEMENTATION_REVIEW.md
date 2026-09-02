# CEX-002 Review 457 - Record 456 Audit Implementation Review

- **Date:** 2026-09-02
- **Reviewer:** Lead Quantitative Finance Researcher/Engineer
- **Ticket:** CEX-002
- **Decision:** reject Record 456 as complete evidence; authorize one temporary Sol audit correction
- **Gate 2:** `ACCEPTED`
- **Gate 3:** `IN_PROGRESS`
- **Next required actor:** Sr Dev - Codex Sol, High
- **Next ticket:** `NONE`

## Plain-language decision

Record 456 reports zero hash mismatches, which is useful evidence that all referenced files are
present and byte-identical to their descriptors. It does not establish the full verification it
claims. The temporary audit program omitted several checks required by Review 455 and then remained
as an untracked repository file. The completed data is not rejected and will not be rerun,
redownloaded, cleaned, or changed. Only the temporary read-only verifier is corrected next.

## Accepted evidence from Record 456

The reviewer accepts these bounded facts:

- both completion files are sole regular files at the accepted content-addressed names and hashes;
- all 22,633 referenced partition Parquets and all 22,633 referenced lineage documents per product
  were read and their SHA-256 values matched both descriptor fields and filenames;
- every referenced Parquet metadata row count matched its descriptor entry;
- every parsed partition-lineage document matched the checked product, symbol, month, row count,
  schema-hash field, writer field, Parquet hash/name, and schema-version fields;
- aggregate descriptor and Parquet metadata rows matched 16,033,469 bars and 16,033,442 trade-flow
  rows;
- the quality-gap artifact hashes, row counts, lineage counts, and canonical exclusion-list hashes
  matched;
- the exclusion lineage identity sets were 40 bars and 67 trade-flow rows, with the bar set a subset
  and 27 trade-flow-only rows;
- both staging directories were empty; and
- physical inventories distinguished referenced current files from old unreferenced content.

These facts are supported by static inspection of the exact untracked audit file at SHA-256
`38e8dc9700b1591f5f4b033876bee3b4a6343ee46b72967c64a520fd075b8e79`, 440 lines, and Record 456's
reported zero-mismatch exit. They do not imply the omitted checks ran.

## Exact defects

Record 456 is rejected as full acceptance evidence because:

1. `verify_partition_parquet` reads only metadata row counts. It never compares any actual Parquet
   schema to the accepted bar or trade-flow schema, despite Record 456 claiming every schema was
   checked.
2. `verify_quality_gap_parquet` never compares the actual quality-gap schema, never reads its rows,
   and never recomputes `missing_grid_points` from those rows.
3. No code matches provider-invalid quality-gap rows one-to-one with exclusion-lineage entries.
   The script checks only the two exclusion identity-set sizes and subset relation.
4. Descriptor paths are joined to the product root without rejecting absolute paths, `..`,
   non-canonical components, or resolved escape. The claimed canonical-relative-path and
   beneath-root checks did not occur.
5. `verify_staging_and_process` checks staging only. It does not inspect processes, despite Record
   456 claiming no normalizer was running.
6. The program accumulates mismatches and continues; it does not stop on the first mismatch as
   Review 455 required.
7. Hermes authored and left `scripts/research/audit_cex002_record456.py` untracked even though Review
   455 authorized read-only commands and three-path evidence publication, not persistent code. Its
   Record 456 wording acknowledges the new script while claiming the prohibitions were honored.
8. `CURRENT_TASK.md` and the CEX-002 header still name Hermes even though Record 456 says both actor
   fields returned to the reviewer.

No production source, accepted descriptor, or data mismatch is established by these defects.

## Sol High temporary verifier authorization

Sr Dev - Codex Sol High is authorized to edit exactly the existing untracked temporary file:

```text
scripts/research/audit_cex002_record456.py
starting sha256 = 38e8dc9700b1591f5f4b033876bee3b4a6343ee46b72967c64a520fd075b8e79
starting lines  = 440
```

Sol must preserve every already-effective read-only check and correct only the omissions above. The
corrected verifier must:

- compare every referenced partition's actual `ParquetFile.schema_arrow` to the exact imported
  accepted `BAR_SCHEMA` or `TRADE_FLOW_SCHEMA`;
- compare each quality-gap Parquet's actual schema to `QUALITY_GAP_SCHEMA`, read its bounded rows,
  and recompute row count and the sum of `expected_grid_count`;
- build the exact provider-invalid gap key `(required_product, native_symbol, utc_month,
  missing_run_start_ms/open_time, reason)` only when start equals end, count is one, and `gap_kind`
  equals `provider_invalid_required_fields`, then prove exact set equality with the corresponding
  exclusion-lineage keys and reject duplicate keys on either side;
- require every descriptor partition path to be a non-absolute canonical `PurePosixPath` with no
  empty, dot, or parent component, match the exact `.partitions/<symbol>/<month>/<sha>.parquet` or
  `.lineage/<symbol>/<month>/<sha>.json` shape, resolve beneath the fixed product root, and traverse
  no symlinked component;
- inspect `/proc` read-only and reject any live Python command whose argument is the exact
  `scripts/research/normalize_binance_usdm_klines.py` path, excluding no matching real Python
  process by substring heuristics;
- stop immediately on the first mismatch with a nonzero exit; and
- perform no write, rename, delete, network, subprocess launch, normalizer import side effect, or
  data change. Importing immutable schema constants is permitted.

The verifier remains a temporary untracked execution artifact. Sol does not run it and does not
delete, stage, commit, or push it. Sol reports its final SHA-256, line count, and a concise mapping
from every finding above to the corrected code. No production/test/CLI/data/control/evidence/other
path may change.

No test, audit execution, data run, Git operation, record publication, network, cleanup, catalog,
NautilusTrader, experiment, model, Harmonic Trader, other product, PAPER, LIVE, or next-ticket work
is authorized. Hermes is not authorized until reviewer inspection of the corrected temporary file.
Gate 2 remains accepted; Gate 3 and CEX-002 remain `IN_PROGRESS`; next ticket remains `NONE`.

## Reviewer publication scope

The reviewer publishes exactly this review, `docs/handoff/CURRENT_TASK.md`, and `tickets/CEX-002.md`.
All source, test, data, temporary verifier, runner, and unrelated dirty paths remain unstaged and
untouched.
