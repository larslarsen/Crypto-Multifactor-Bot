from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True, slots=True)
class RawObject:
    raw_object_id: str
    source_id: str
    sha256: str
    bytes: int
    storage_path: Path
    acquired_at: datetime


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    dataset_type: str
    schema_version: str
    input_ids: tuple[str, ...]
    output_hashes: tuple[str, ...]
    row_count: int
    byte_size: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SourceObjectRef:
    source_id: str
    object_key: str
    request: Mapping[str, Any]


class SourceAdapter(Protocol):
    source_id: str

    def discover(self, request: Mapping[str, Any]) -> Sequence[SourceObjectRef]: ...

    def fetch(self, ref: SourceObjectRef, destination: Path) -> RawObject: ...


class DatasetPublisher(Protocol):
    def publish(
        self,
        *,
        dataset_type: str,
        schema_version: str,
        input_ids: Sequence[str],
        files: Sequence[Path],
        metadata: Mapping[str, Any],
    ) -> DatasetManifest: ...
