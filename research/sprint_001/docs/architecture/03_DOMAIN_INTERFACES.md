# 03 — Domain Interfaces

## 1. Interface philosophy

Interfaces exist to protect research invariants, not to create abstract class hierarchies. Prefer small typed protocols and immutable records. Domain functions must not depend on global paths or hidden “latest” files.

## 2. Acquisition interface

```python
class SourceAdapter(Protocol):
    source_id: str

    def discover(self, request: DiscoveryRequest) -> list[SourceObjectRef]: ...
    def fetch(self, ref: SourceObjectRef, destination: Path) -> RawFetchResult: ...
    def parse_metadata(self, raw: RawObject) -> SourceMetadata: ...
```

Rules:

- `fetch` writes only to staging/raw.
- original bytes are preserved;
- request parameters, response headers, status, checksum, and acquisition time are recorded;
- pagination state is explicit;
- retry does not create duplicate identities.

## 3. Normalization interface

```python
class Normalizer(Protocol):
    input_schema_version: str
    output_schema_version: str

    def normalize(self, raw_object_ids: Sequence[str], config: FrozenConfig) -> BuildResult: ...
```

A normalizer is source-specific. It cannot output a canonical dataset unless all temporal/unit assumptions are declared and validated.

## 4. Dataset publication interface

```python
class DatasetPublisher(Protocol):
    def publish(
        self,
        dataset_type: str,
        schema_version: str,
        input_dataset_ids: Sequence[str],
        files: Sequence[Path],
        quality_summary: QualitySummary,
        transform: TransformIdentity,
    ) -> DatasetManifest: ...
```

Publication is atomic. The manifest is hashed after all output hashes are known.

## 5. Point-in-time reference interface

```python
class ReferenceStore(Protocol):
    def instruments_as_of(self, decision_time: datetime) -> ArrowTable: ...
    def resolve_alias(self, source: str, symbol: str, as_of: datetime) -> InstrumentResolution: ...
    def fee_schedule_as_of(self, instrument_id: int, decision_time: datetime) -> FeeSchedule: ...
```

Every resolution returns confidence and evidence lineage.

## 6. As-of observation interface

```python
class AsOfStore(Protocol):
    def latest_available(
        self,
        dataset_id: str,
        keys: Sequence[int],
        fields: Sequence[str],
        decision_time: datetime,
        max_age: timedelta | None,
    ) -> ArrowTable: ...
```

The implementation enforces `availability_time <= decision_time`. Factor code does not implement its own as-of joins.

## 7. Universe interface

```python
class UniverseBuilder(Protocol):
    universe_version: str

    def build(self, decision_time: datetime, inputs: UniverseInputs) -> UniverseSnapshot: ...
```

Output includes eligible and rejected assets, each gate value, route candidates, shortability, and lineage.

## 8. Factor interface

```python
class Factor(Protocol):
    factor_id: str
    factor_version: str
    dependencies: tuple[DataDependency, ...]

    def compute(self, context: FactorContext) -> FactorFrame: ...
```

`FactorFrame` includes:

- decision time;
- asset ID;
- raw value;
- transformed score;
- availability time;
- lookback start/end;
- source dataset IDs;
- missing reason;
- quality flags.

Factor functions are deterministic and pure with respect to declared inputs.

## 9. Label interface

```python
class Labeler(Protocol):
    target_id: str
    target_version: str

    def compute(self, decisions: UniverseSnapshot, market: MarketAccess) -> LabelFrame: ...
```

Labels include event intervals, route, gross return, fee, spread/impact, funding/borrow, net return, censoring, delisting, and ambiguity.

## 10. Split interface

```python
class ChronologicalSplitter(Protocol):
    split_version: str

    def split(self, events: EventIntervals, config: SplitConfig) -> list[OuterFold]: ...
```

The splitter removes earlier events whose `event_end` overlaps a later partition. Each fold contains exact row IDs and date ranges. Preprocessing is fitted inside fold scope.

## 11. Portfolio interface

```python
class PortfolioConstructor(Protocol):
    portfolio_version: str

    def target_weights(
        self,
        scores: FactorOrModelScores,
        universe: UniverseSnapshot,
        holdings: Holdings,
        constraints: PortfolioConstraints,
        cost_estimates: CostEstimates,
    ) -> TargetPortfolio: ...
```

Weights are a pure function of these inputs. Simulation/execution is separate.

## 12. Experiment interface

```python
class ExperimentRunner(Protocol):
    def run(self, record: FrozenExperimentRecord) -> ExperimentBundle: ...
```

Preconditions:

- experiment is registered;
- config is frozen;
- all dataset IDs resolve;
- code and environment identity are known;
- output fingerprint does not already exist unless explicitly verifying reproduction.

## 13. Model artifact interface

Every model artifact has a manifest declaring:

- model type and version;
- training experiment/fingerprint;
- universe, factor, target, and cost versions;
- representation type/version;
- feature list/order/types;
- preprocessing artifact hashes;
- train/validation/test/prospective ranges;
- dataset/code/environment hashes;
- metrics and promotion decision;
- serving compatibility version.

The loader rejects missing or mismatched metadata. It never chooses a model from a filename pattern.

## 14. Dependency direction

Allowed dependency direction:

```text
catalog/storage <- ingest/reference/quality/market
reference + market <- universe
reference + market + universe <- factors/labels
factors + labels + universe <- validation/experiments
experiments + portfolio <- promotion
promotion + approved factor library <- serving
```

Forbidden:

- `market` importing `factors`;
- `factors` importing `labels`;
- `serving` importing notebooks or exploratory experiment modules;
- collectors importing portfolio/model code;
- model loaders scanning arbitrary directories.
