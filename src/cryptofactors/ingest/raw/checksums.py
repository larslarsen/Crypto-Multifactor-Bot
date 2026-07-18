"""Explicit provider checksum evaluation (distinct from content SHA-256 identity)."""

from __future__ import annotations

from cryptofactors.ingest.raw.errors import ChecksumError, HashMismatchError, RawStoreError
from cryptofactors.ingest.raw.models import (
    ChecksumAlgorithm,
    ChecksumVerification,
    ProviderChecksum,
)
from cryptofactors.ingest.raw.paths import validate_sha256_hex


def normalize_algorithm(algorithm: str) -> str:
    a = algorithm.strip().lower().replace("-", "")
    if a == "sha256":
        return ChecksumAlgorithm.SHA256.value
    return algorithm.strip().lower()


def evaluate_provider_checksum(
    provider: ProviderChecksum | None,
    *,
    content_sha256: str,
    reject_unsupported: bool = True,
    reject_malformed: bool = True,
) -> ChecksumVerification:
    """Evaluate provider checksum against computed content SHA-256.

    - No provider checksum → ABSENT (never silently treated as verified).
    - Unsupported algorithm → ChecksumError if reject_unsupported else UNSUPPORTED.
    - Malformed value → ChecksumError if reject_malformed else MALFORMED.
    - SHA-256 match → VERIFIED; mismatch → MISMATCH.
    """
    if provider is None:
        return ChecksumVerification.ABSENT

    algo = normalize_algorithm(provider.algorithm)
    if algo != ChecksumAlgorithm.SHA256.value:
        if reject_unsupported:
            raise ChecksumError(
                f"unsupported checksum algorithm: {provider.algorithm!r}",
                context={"algorithm": provider.algorithm},
            )
        return ChecksumVerification.UNSUPPORTED

    try:
        expected = validate_sha256_hex(provider.value)
    except RawStoreError as exc:
        if reject_malformed:
            raise ChecksumError(
                "malformed checksum value for sha256",
                context={"value": provider.value},
            ) from exc
        return ChecksumVerification.MALFORMED

    actual = validate_sha256_hex(content_sha256)
    if expected == actual:
        return ChecksumVerification.VERIFIED
    return ChecksumVerification.MISMATCH


def require_checksum_ok_for_verified_status(
    content_status: str,
    verification: ChecksumVerification,
) -> str:
    """Return content status, refusing VERIFIED unless verification succeeded."""
    status = content_status.upper()
    if status == "VERIFIED" and verification is not ChecksumVerification.VERIFIED:
        raise ChecksumError(
            "content status VERIFIED requires successful provider checksum verification",
            context={
                "content_status": content_status,
                "checksum_verification": verification.value,
            },
        )
    if status not in ("ACQUIRED", "VERIFIED", "QUARANTINED", "REJECTED"):
        raise ChecksumError(
            f"unsupported content status: {content_status!r}",
            context={"content_status": content_status},
        )
    return status


def raise_if_hard_fail(verification: ChecksumVerification, *, content_sha256: str) -> None:
    if verification is ChecksumVerification.MISMATCH:
        raise HashMismatchError(
            "provider checksum does not match computed content SHA-256",
            context={"content_sha256": content_sha256},
        )
