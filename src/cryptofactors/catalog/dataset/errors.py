"""Typed exceptions for dataset manifests and publication (MAN-001)."""

from __future__ import annotations

from typing import Any, Mapping


class DatasetError(Exception):
    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class InvalidManifestError(DatasetError):
    """Manifest model, parse, or canonicalization is invalid."""


class UnsafePathError(DatasetError):
    """Path escapes root, is absolute when relative required, or is a symlink."""


class MissingInputError(DatasetError):
    """Required raw object or upstream dataset is missing."""


class OutputVerificationError(DatasetError):
    """Output file missing, unexpected, unsafe, or content/row-count mismatch."""


class LineageError(DatasetError):
    """Invalid lineage edge or cycle detected."""


class CorruptDatasetError(DatasetError):
    """Preexisting dataset path or catalog row disagrees with content."""


class DatasetPublicationError(DatasetError):
    """Atomic publication failed or is unsupported."""


class DatasetDurabilityError(DatasetPublicationError):
    """Required fsync failed."""


class SupersessionError(DatasetError):
    """Invalid supersession target or cycle."""


class RecoverableDatasetCatalogError(DatasetError):
    """Dataset files published; catalog registration failed and may be retried."""

    def __init__(
        self,
        message: str,
        *,
        dataset_id: str,
        manifest_sha256: str,
        dataset_path: str,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.dataset_id = dataset_id
        self.manifest_sha256 = manifest_sha256
        self.dataset_path = dataset_path
