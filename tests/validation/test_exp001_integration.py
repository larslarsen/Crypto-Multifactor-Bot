"""EXP-001 — focused integration tests for experiment bundles & fingerprints.

Covers (per Jr contract):
- Fingerprint tampering: tamper with factor_defs / metadata after construction ->
  ExperimentError on register (recomputed fingerprint mismatch).
- Non-string factor IDs: int in factor_defs -> ExperimentError at construction.
- Non-string metadata keys: int key -> ExperimentError at construction.
- register / duplicate detection / load / list / has happy paths.

The approved drop (``cryptofactors.validation.experiment``) is not modified here. Jr added
package exports only.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

import pytest

from cryptofactors.validation import (
    ExperimentBundle,
    ExperimentError,
    InMemoryExperimentRegistry,
    LabelConfig,
    LabelType,
    SplitConfig,
    SplitMode,
)


def _label_config() -> LabelConfig:
    return LabelConfig(
        horizon=timedelta(days=1),
        label_type=LabelType.SIGN,
        market_dataset_id="bars",
        instrument_dataset_id="ref_instrument_version",
    )


def _split_config() -> SplitConfig:
    return SplitConfig(mode=SplitMode.PURGED_KFOLD, n_folds=2)


def _bundle(
    factor_defs: tuple[str, ...] = ("f1", "f2"),
    metadata: Mapping[str, str | int | float | bool] | None = None,
) -> ExperimentBundle:
    return ExperimentBundle(
        label_config=_label_config(),
        split_config=_split_config(),
        factor_defs=factor_defs,
        metadata=metadata if metadata is not None else {"name": "exp1"},
    )


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

def test_non_string_factor_id_raises() -> None:
    with pytest.raises(ExperimentError):
        _bundle(factor_defs=("f1", 42))  # type: ignore[arg-type]


def test_empty_factor_defs_raises() -> None:
    with pytest.raises(ExperimentError):
        _bundle(factor_defs=())


def test_non_string_metadata_key_raises() -> None:
    with pytest.raises(ExperimentError):
        _bundle(metadata={123: "v"})  # type: ignore[dict-item]


def test_invalid_metadata_value_raises() -> None:
    with pytest.raises(ExperimentError):
        _bundle(metadata={"k": None})  # type: ignore[dict-item]


def test_bundle_fingerprint_is_deterministic() -> None:
    a = _bundle()
    b = _bundle()
    assert a.fingerprint == b.fingerprint
    assert len(a.fingerprint) == 64  # sha256 hex


def test_bundle_factor_defs_sorted() -> None:
    b = _bundle(factor_defs=("f2", "f1"))
    assert b.factor_defs == ("f1", "f2")


# ---------------------------------------------------------------------------
# Fingerprint tampering -> register rejects
# ---------------------------------------------------------------------------

def test_tamper_factor_defs_rejected_on_register() -> None:
    reg = InMemoryExperimentRegistry()
    b = _bundle()
    stored_fp = b.fingerprint
    # Tamper factor_defs after construction (frozen -> bypass via object.__setattr__).
    object.__setattr__(b, "factor_defs", ("f1", "tampered"))
    with pytest.raises(ExperimentError, match="fingerprint does not match"):
        reg.register(b)
    # stored fingerprint unchanged; registry still empty
    assert b.fingerprint == stored_fp
    assert reg.list_bundles() == []


def test_tamper_metadata_rejected_on_register() -> None:
    reg = InMemoryExperimentRegistry()
    b = _bundle(metadata={"name": "exp1"})
    object.__setattr__(b, "metadata", {"name": "evil"})
    with pytest.raises(ExperimentError, match="fingerprint does not match"):
        reg.register(b)
    assert reg.list_bundles() == []


# ---------------------------------------------------------------------------
# Happy paths: register / duplicate / load / list / has
# ---------------------------------------------------------------------------

def test_register_returns_fingerprint() -> None:
    reg = InMemoryExperimentRegistry()
    b = _bundle()
    fp = reg.register(b)
    assert fp == b.fingerprint
    assert reg.has(fp)
    assert fp in reg.list_bundles()


def test_duplicate_register_raises() -> None:
    reg = InMemoryExperimentRegistry()
    b = _bundle()
    reg.register(b)
    with pytest.raises(ExperimentError, match="duplicate"):
        reg.register(b)


def test_load_roundtrip() -> None:
    reg = InMemoryExperimentRegistry()
    b = _bundle(metadata={"name": "exp1", "k": 3})
    fp = reg.register(b)
    loaded = reg.load(fp)
    assert loaded.fingerprint == fp
    assert loaded.factor_defs == ("f1", "f2")
    assert dict(loaded.metadata) == {"name": "exp1", "k": 3}


def test_load_missing_raises() -> None:
    reg = InMemoryExperimentRegistry()
    with pytest.raises(ExperimentError, match="not found"):
        reg.load("deadbeef")


def test_has_missing_false() -> None:
    reg = InMemoryExperimentRegistry()
    assert reg.has("nope") is False


def test_register_rejects_non_bundle() -> None:
    reg = InMemoryExperimentRegistry()
    with pytest.raises(ExperimentError, match="must be ExperimentBundle"):
        reg.register("not-a-bundle")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Two distinct bundles -> two distinct fingerprints
# ---------------------------------------------------------------------------

def test_distinct_bundles_distinct_fingerprints() -> None:
    reg = InMemoryExperimentRegistry()
    b1 = _bundle(factor_defs=("f1", "f2"))
    b2 = _bundle(factor_defs=("f1", "f3"))
    fp1 = reg.register(b1)
    fp2 = reg.register(b2)
    assert fp1 != fp2
    assert len(reg.list_bundles()) == 2
