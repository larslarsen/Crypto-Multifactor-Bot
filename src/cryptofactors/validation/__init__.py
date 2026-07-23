"""Validation layer: purged chronological splits and labels (research substrate)."""

from __future__ import annotations

from cryptofactors.validation.labels import (
    AsOfLabelEngine,
    DecisionEvent,
    LabelConfig,
    LabelEngine,
    LabelError,
    LabelType,
)
from cryptofactors.validation.experiment import (
    ExperimentBundle,
    ExperimentError,
    ExperimentRegistry,
    InMemoryExperimentRegistry,
)
from cryptofactors.validation.split import (
    AsOfDataAccess,
    ChronologicalSplitter,
    EventInterval,
    OuterFold,
    PurgedChronologicalSplitter,
    SplitConfig,
    SplitError,
    SplitMode,
    SplitPartition,
)

__all__ = [
    "AsOfDataAccess",
    "AsOfLabelEngine",
    "ChronologicalSplitter",
    "DecisionEvent",
    "EventInterval",
    "ExperimentBundle",
    "ExperimentError",
    "ExperimentRegistry",
    "InMemoryExperimentRegistry",
    "LabelConfig",
    "LabelEngine",
    "LabelError",
    "LabelType",
    "OuterFold",
    "PurgedChronologicalSplitter",
    "SplitConfig",
    "SplitError",
    "SplitMode",
    "SplitPartition",
]
