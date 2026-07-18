# 08 — Legacy Migration Plan

## 1. Principle

The old Trading-Bot repository is an evidence archive. Do not copy its module tree into the new project.

## 2. Migration boundary

Create a dedicated adapter:

```text
src/cryptofactors/ingest/legacy_local.py
```

It may:

- enumerate files;
- hash and register original bytes;
- infer candidate source/type from path and schema;
- emit unresolved metadata questions;
- call approved source-specific normalizers after explicit mapping.

It may not:

- import legacy feature/model code;
- trust filenames as instrument identity;
- rename or overwrite legacy observations;
- classify old generated outputs as raw market data;
- promote old model metrics.

## 3. File census

Classify every local file as one of:

- raw provider object;
- normalized observation;
- derived feature;
- label/return;
- prediction/model artifact;
- report/result;
- configuration;
- unknown.

Only raw/provider objects and independently verifiable normalized observations can enter the data audit. Derived outputs remain forensic evidence.

## 4. Provenance classes

- `VERIFIED_OFFICIAL`: exact official archive/API object with checksum/request evidence.
- `VERIFIED_CROSSSOURCE`: content reconciled to official source.
- `LEGACY_PROVENANCE_PARTIAL`: source likely known but request/object evidence incomplete.
- `LEGACY_UNKNOWN`: source/timestamp semantics unresolved; quarantined.

## 5. Candidate reuse

After tests, concepts or small utilities may be transplanted:

- retry/backoff behavior;
- atomic writes;
- API pagination knowledge;
- execution accounting fixtures;
- known symbol edge cases;
- known data failures.

Transplant means rewrite behind the new interfaces with tests—not copy entire modules.

## 6. Explicit archive-only items

- legacy 113-feature ontology;
- tuned indicator/regime scripts;
- old model weights and `latest_*` conventions;
- old purging implementation;
- prior p-values/accuracy as promotion evidence;
- information-bar artifacts and metrics;
- inferred Sharpe targets.

## 7. Information models

Preserve committed information models for forensic comparison. Store them outside the active model registry with status `QUARANTINED_LEGACY`.

They cannot be loaded by serving and cannot share the namespace of approved time-bar or future event-bar models.

## 8. Completion criteria

Migration is complete when:

- every legacy file is classified;
- all candidate observations have hashes and provenance class;
- source schemas/timestamps are verified or quarantined;
- canonical datasets rebuild without importing legacy research/model code;
- the new repository can run with the old repository absent.
