# 04 — Repository Layout

## Recommended root layout

Move the existing sprint package under `research/sprint_001/` and add the following structure at repository root.

```text
Crypto-Multifactor-Bot/
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── .env.example
├── configs/
│   ├── storage.example.yaml
│   ├── runtime.example.yaml
│   ├── sources.example.yaml
│   ├── universe/
│   ├── costs/
│   └── experiments/
├── docs/
│   ├── architecture/
│   │   ├── adr/
│   │   └── ...
│   ├── data/
│   └── operations/
├── research/
│   ├── sprint_001/
│   ├── factor_cards/
│   ├── literature/
│   ├── experiment_registry.csv
│   └── graveyard/
├── schemas/
│   ├── json/
│   └── arrow/
├── sql/
│   ├── control_schema.sql
│   ├── analytics_views.sql
│   └── quality/
├── src/cryptofactors/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── ids.py
│   ├── catalog/
│   ├── storage/
│   ├── ingest/
│   │   ├── base.py
│   │   ├── binance.py
│   │   ├── kraken.py
│   │   ├── okx.py
│   │   ├── bybit.py
│   │   └── legacy_local.py
│   ├── reference/
│   ├── quality/
│   ├── market/
│   ├── universe/
│   ├── factors/
│   │   ├── momentum.py
│   │   ├── reversal.py
│   │   ├── defensive.py
│   │   ├── liquidity.py
│   │   └── carry.py
│   ├── labels/
│   ├── validation/
│   ├── portfolio/
│   ├── experiments/
│   ├── reports/
│   └── serving/
├── tests/
│   ├── unit/
│   ├── property/
│   ├── integration/
│   ├── leakage/
│   ├── golden/
│   └── fixtures/
├── scripts/
│   ├── bootstrap_local.sh
│   └── export_public_manifest.py
└── .github/workflows/
    ├── lint-test.yml
    └── schema-contracts.yml
```

## Package rules

### No generic `utils.py`

Place functionality in its domain. Generic utility modules tend to become unreviewed dependency hubs.

### No notebooks as production inputs

Notebooks may explore only. Promoted code moves into `src/`, receives tests, and runs from a frozen experiment config.

### No mutable `latest_*`

Use immutable IDs plus a small promotion record:

```text
production_candidate -> model_artifact_id
paper_active         -> model_artifact_id
```

The alias record is versioned in the control catalog; the artifact itself is immutable.

### Config hierarchy

- shared defaults;
- source/storage/runtime configs;
- research version config;
- experiment-specific config;
- no environment-dependent hidden defaults.

Resolve all configs to one canonical JSON/YAML file saved in the run bundle.

## Command surface

Recommended CLI:

```text
cf catalog init
cf data discover <source>
cf data fetch <source>
cf data register-legacy <path>
cf data normalize <dataset>
cf data audit <dataset>
cf reference build
cf market build-bars
cf market build-funding
cf universe build --version U50-v1
cf factors build --factor MOM-01-v1
cf labels build --target RET-7D-v1
cf experiment run EXP-2026-003
cf experiment reproduce <fingerprint>
cf report render <fingerprint>
cf model promote <artifact-id> --stage paper
cf serve paper --decision-time ...
```

Commands should be idempotent. They either return the existing matching fingerprint or publish a new immutable version.

## Public versus local data

The repository contains no raw market observations. It may contain:

- manifests with local paths redacted;
- hashes, row counts, schema fingerprints, and coverage;
- synthetic fixtures;
- small legally redistributable examples;
- experiment summaries and charts;
- exact commands needed to reproduce on the owner’s local data root.
