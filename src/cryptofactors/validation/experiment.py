"""EXP-001 — experiment bundles and deterministic fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import Protocol, runtime_checkable

from cryptofactors.validation.labels import LabelConfig
from cryptofactors.validation.split import SplitConfig


class ExperimentError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


@dataclass(frozen=True, slots=True)
class ExperimentBundle:
    label_config: LabelConfig
    split_config: SplitConfig
    factor_defs: tuple[str, ...]
    metadata: Mapping[str, str | int | float | bool]
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if self.label_config is None:
            raise ExperimentError("label_config must not be None")
        if self.split_config is None:
            raise ExperimentError("split_config must not be None")
        if not isinstance(self.label_config, LabelConfig):
            raise ExperimentError(
                "label_config must be LabelConfig",
                context={"type": type(self.label_config).__name__},
            )
        if not isinstance(self.split_config, SplitConfig):
            raise ExperimentError(
                "split_config must be SplitConfig",
                context={"type": type(self.split_config).__name__},
            )
        if not self.factor_defs:
            raise ExperimentError("factor_defs must be non-empty")
        for f in self.factor_defs:
            if not isinstance(f, str):
                raise ExperimentError(
                    "factor_defs entries must be str",
                    context={"type": type(f).__name__},
                )
            if not f:
                raise ExperimentError("factor_defs entries must be non-empty strings")
        factors = tuple(sorted(self.factor_defs))
        object.__setattr__(self, "factor_defs", factors)

        raw_meta: Mapping[object, object] = (
            self.metadata if self.metadata is not None else {}
        )
        str_keys: list[str] = []
        for key in raw_meta.keys():
            if not isinstance(key, str):
                raise ExperimentError(
                    "metadata keys must be str",
                    context={"type": type(key).__name__},
                )
            str_keys.append(key)
        canonical_meta: dict[str, str | int | float | bool] = {}
        for key in sorted(str_keys):
            v = raw_meta[key]
            if isinstance(v, bool):
                canonical_meta[key] = v
            elif isinstance(v, int) and not isinstance(v, bool):
                canonical_meta[key] = v
            elif isinstance(v, float):
                canonical_meta[key] = v
            elif isinstance(v, str):
                canonical_meta[key] = v
            else:
                raise ExperimentError(
                    "metadata values must be str|int|float|bool",
                    context={"key": key, "type": type(v).__name__},
                )
        object.__setattr__(self, "metadata", MappingProxyType(canonical_meta))
        digest = hashlib.sha256(self._canonical_bytes()).hexdigest()
        object.__setattr__(self, "fingerprint", digest)

    def _canonical_bytes(self) -> bytes:
        payload: dict[str, object] = {
            "factor_defs": list(self.factor_defs),
            "label_config": asdict(self.label_config),
            "metadata": [[k, self.metadata[k]] for k in sorted(self.metadata.keys())],
            "split_config": asdict(self.split_config),
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")


@runtime_checkable
class ExperimentRegistry(Protocol):
    def register(self, bundle: ExperimentBundle) -> str: ...

    def load(self, fingerprint: str) -> ExperimentBundle: ...

    def list_bundles(self) -> list[str]: ...

    def has(self, fingerprint: str) -> bool: ...


class InMemoryExperimentRegistry:
    def __init__(self) -> None:
        self._bundles: dict[str, ExperimentBundle] = {}

    def register(self, bundle: ExperimentBundle) -> str:
        if not isinstance(bundle, ExperimentBundle):
            raise ExperimentError(
                "bundle must be ExperimentBundle",
                context={"type": type(bundle).__name__},
            )
        expected = hashlib.sha256(bundle._canonical_bytes()).hexdigest()
        if expected != bundle.fingerprint:
            raise ExperimentError(
                "bundle fingerprint does not match recomputed fingerprint",
                context={
                    "stored": bundle.fingerprint,
                    "recomputed": expected,
                },
            )
        fp = expected
        if fp in self._bundles:
            raise ExperimentError(
                "duplicate experiment fingerprint",
                context={"fingerprint": fp},
            )
        self._bundles[fp] = bundle
        return fp

    def load(self, fingerprint: str) -> ExperimentBundle:
        key = str(fingerprint)
        if key not in self._bundles:
            raise ExperimentError(
                "experiment fingerprint not found",
                context={"fingerprint": key},
            )
        return self._bundles[key]

    def list_bundles(self) -> list[str]:
        return sorted(self._bundles.keys())

    def has(self, fingerprint: str) -> bool:
        return str(fingerprint) in self._bundles
