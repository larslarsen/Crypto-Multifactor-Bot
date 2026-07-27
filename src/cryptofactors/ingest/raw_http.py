"""Shared raw HTTP acquisition with byte-exact response preservation.

Used by every acquisition path that must be replayable and auditable. The contract
is deliberately small: perform a request, preserve exactly what came back before any
decoding, and record the attempt whether or not it succeeded. Error bodies are
evidence in their own right; a transport failure that produced no body still leaves a
failed-acquisition record so a gap in coverage is always explainable.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from cryptofactors.ingest.raw.models import AcquisitionMetadata
from cryptofactors.ingest.raw.writer import RawObjectWriter


class RawAcquisitionError(RuntimeError):
    """Raised for invalid acquisition configuration."""


def canonical_json(payload: Any) -> str:
    """Stable encoding so a recorded request compares byte-for-byte."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    """One HTTP attempt, whether or not it produced usable data.

    ``payload`` is None whenever the attempt failed; ``raw_object_id`` is None only
    when the transport produced no body at all.
    """

    provider: str
    request: dict[str, Any]
    acquired_at: datetime
    ok: bool
    payload: Any = None
    status_code: int | None = None
    raw_object_id: str | None = None
    acquisition_id: str | None = None
    failure_kind: str | None = None
    detail: str | None = None
    attempt: int = 1
    backoff_seconds: float = 0.0

    @property
    def request_json(self) -> str:
        return canonical_json(self.request)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "request_json": self.request_json,
            "acquired_at": self.acquired_at.isoformat(),
            "ok": self.ok,
            "status_code": self.status_code,
            "raw_object_id": self.raw_object_id,
            "acquisition_id": self.acquisition_id,
            "failure_kind": self.failure_kind,
            "detail": self.detail,
            "attempt": self.attempt,
            "backoff_seconds": self.backoff_seconds,
            "rate_limited": self.status_code in RATE_LIMIT_STATUSES,
        }


RATE_LIMIT_STATUSES = frozenset({429})
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass
class AcquisitionLog:
    """Every attempt made during a run, successful or not."""

    outcomes: list[AcquisitionOutcome] = field(default_factory=list)

    def record(self, outcome: AcquisitionOutcome) -> AcquisitionOutcome:
        self.outcomes.append(outcome)
        return outcome

    @property
    def raw_object_ids(self) -> frozenset[str]:
        return frozenset(o.raw_object_id for o in self.outcomes if o.raw_object_id is not None)

    @property
    def failures(self) -> list[AcquisitionOutcome]:
        return [o for o in self.outcomes if not o.ok]

    @property
    def retries(self) -> list[AcquisitionOutcome]:
        return [o for o in self.outcomes if o.attempt > 1]

    @property
    def rate_limit_incidents(self) -> list[AcquisitionOutcome]:
        return [o for o in self.outcomes if o.status_code in RATE_LIMIT_STATUSES]

    def as_dicts(self) -> list[dict[str, Any]]:
        return [o.as_dict() for o in self.outcomes]


class RawHttpAcquirer:
    """Performs HTTP requests, preserving the exact response bytes before decoding."""

    def __init__(
        self,
        *,
        raw_writer: RawObjectWriter,
        client: httpx.Client,
        log: AcquisitionLog | None = None,
        max_attempts: int = 1,
        backoff_seconds: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise RawAcquisitionError("max_attempts must be at least 1")
        self._raw_writer = raw_writer
        self._client = client
        self.log = log if log is not None else AcquisitionLog()
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep

    def get_json(
        self,
        *,
        provider: str,
        url: str,
        params: Mapping[str, Any] | None = None,
        source_id: str,
        original_name: str,
    ) -> AcquisitionOutcome:
        """Acquire JSON, retrying politely on rate limits and transient errors.

        Every attempt preserves its own response bytes, so a 429 body is evidence in
        its own right rather than something discarded on the way to a retry.
        """
        outcome = self._attempt(
            provider=provider, url=url, params=params, source_id=source_id,
            original_name=original_name, attempt=1,
        )
        for attempt in range(2, self._max_attempts + 1):
            if outcome.ok:
                return outcome
            retryable = (
                outcome.failure_kind == "transport"
                or (outcome.status_code in RETRYABLE_STATUSES)
            )
            if not retryable:
                return outcome
            waited = 0.0
            if self._backoff_seconds > 0:
                # Exponential, so a rate-limited provider gets progressively more room.
                waited = self._backoff_seconds * (2 ** (attempt - 2))
                self._sleep(waited)
            outcome = self._attempt(
                provider=provider, url=url, params=params, source_id=source_id,
                original_name=original_name, attempt=attempt, backoff_seconds=waited,
            )
        return outcome

    def _attempt(
        self,
        *,
        provider: str,
        url: str,
        params: Mapping[str, Any] | None,
        source_id: str,
        original_name: str,
        attempt: int,
        backoff_seconds: float = 0.0,
    ) -> AcquisitionOutcome:
        request = {"method": "GET", "url": url, "params": dict(params or {})}
        acquired_at = datetime.now(UTC)

        try:
            response = self._client.get(url, params=dict(params or {}))
        except httpx.HTTPError as exc:
            detail = f"transport failure: {exc}"
            # No bytes to preserve, but the attempt must still be evidence.
            self._raw_writer.record_failed_acquisition(
                AcquisitionMetadata(source_id=source_id, request=request, acquired_at=acquired_at),
                detail,
            )
            return self.log.record(AcquisitionOutcome(
                provider=provider, request=request, acquired_at=acquired_at, ok=False,
                failure_kind="transport", detail=detail, attempt=attempt,
                backoff_seconds=backoff_seconds,
            ))

        body = response.content
        acquired_at = datetime.now(UTC)
        raw = self._raw_writer.write_stream(
            [body],
            AcquisitionMetadata(
                source_id=source_id,
                request=request,
                response_metadata={"status_code": response.status_code, "provider": provider},
                original_name=original_name,
                acquired_at=acquired_at,
            ),
        )
        common: dict[str, Any] = {
            "provider": provider,
            "request": request,
            "acquired_at": acquired_at,
            "status_code": response.status_code,
            "raw_object_id": raw.raw_object_id,
            "acquisition_id": raw.acquisition_id,
            "attempt": attempt,
            "backoff_seconds": backoff_seconds,
        }

        if response.is_error:
            return self.log.record(AcquisitionOutcome(
                ok=False, failure_kind="http_status",
                detail=f"HTTP {response.status_code}", **common,
            ))
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            return self.log.record(AcquisitionOutcome(
                ok=False, failure_kind="invalid_json",
                detail=f"invalid JSON body: {exc}", **common,
            ))
        return self.log.record(AcquisitionOutcome(ok=True, payload=payload, **common))


