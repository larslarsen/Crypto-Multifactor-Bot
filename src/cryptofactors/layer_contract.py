from __future__ import annotations

from enum import StrEnum


class Layer(StrEnum):
    CORE = "core"
    CATALOG = "catalog"
    INGEST = "ingest"
    REFERENCE = "reference"
    QUALITY = "quality"
    MARKET = "market"
    UNIVERSE = "universe"
    FACTORS = "factors"
    LABELS = "labels"
    VALIDATION = "validation"
    PORTFOLIO = "portfolio"
    EVIDENCE = "evidence"
    EXPERIMENTS = "experiments"
    SERVING = "serving"
    EXECUTION = "execution"


ALLOWED_IMPORTS: dict[Layer, frozenset[Layer]] = {
    Layer.CORE: frozenset(),
    Layer.CATALOG: frozenset({Layer.CORE}),
    Layer.INGEST: frozenset({Layer.CORE, Layer.CATALOG}),
    Layer.REFERENCE: frozenset({Layer.CORE, Layer.CATALOG}),
    Layer.QUALITY: frozenset({Layer.CORE, Layer.CATALOG, Layer.REFERENCE}),
    Layer.MARKET: frozenset({Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.QUALITY}),
    Layer.UNIVERSE: frozenset({Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET}),
    Layer.FACTORS: frozenset({Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET, Layer.UNIVERSE, Layer.LABELS, Layer.VALIDATION}),
    Layer.LABELS: frozenset({Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET, Layer.UNIVERSE}),
    Layer.VALIDATION: frozenset({Layer.CORE, Layer.LABELS}),
    Layer.PORTFOLIO: frozenset({Layer.CORE, Layer.MARKET, Layer.UNIVERSE, Layer.FACTORS, Layer.LABELS}),
    Layer.EVIDENCE: frozenset({Layer.CORE, Layer.CATALOG}),
    Layer.EXPERIMENTS: frozenset({
        Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET, Layer.UNIVERSE,
        Layer.FACTORS, Layer.LABELS, Layer.VALIDATION, Layer.PORTFOLIO, Layer.EVIDENCE,
    }),
    Layer.SERVING: frozenset({
        Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET,
        Layer.UNIVERSE, Layer.FACTORS, Layer.PORTFOLIO,
    }),
    Layer.EXECUTION: frozenset({
        Layer.CORE, Layer.CATALOG, Layer.REFERENCE, Layer.MARKET,
        Layer.PORTFOLIO, Layer.SERVING,
    }),
}

NETWORK_ALLOWED = frozenset({Layer.INGEST, Layer.EXECUTION})


def import_is_allowed(importer: Layer, imported: Layer) -> bool:
    return importer == imported or imported in ALLOWED_IMPORTS[importer]
