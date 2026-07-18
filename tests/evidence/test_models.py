from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from cryptofactors.evidence.models import HypothesisVersion


def valid_hypothesis() -> HypothesisVersion:
    return HypothesisVersion(
        hypothesis_id="H-001",
        version=1,
        slug="medium-term-momentum",
        title="Medium-term momentum",
        statement="Higher medium-term returns predict higher subsequent net returns.",
        mechanism="Slow information diffusion may create persistent cross-sectional trends.",
        expected_sign="POSITIVE",
        phase="PHASE_1",
        primary_metric="net_return",
        advancement_rule="Positive net performance under preregistered costs.",
        rejection_rule="Reject if net performance is non-positive.",
        preregistered_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )


def test_hypothesis_is_frozen() -> None:
    hypothesis = valid_hypothesis()
    with pytest.raises(ValidationError):
        hypothesis.title = "Changed"  # type: ignore[misc]


def test_naive_preregistration_time_is_rejected() -> None:
    data = valid_hypothesis().model_dump()
    data["preregistered_at"] = datetime(2026, 7, 18)
    with pytest.raises(ValidationError):
        HypothesisVersion.model_validate(data)
