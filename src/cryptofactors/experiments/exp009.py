"""EXP-009 — Pre-registered single-hypothesis TSMOM runner (``tsmom_365_30``).

Implements the frozen design signed in ``tickets/EXP-009_PRE_REGISTRATION.md``
(REVIEW-0252). One shot only: no grid, no parameter search, no post-hoc rescue.

Holdout is **prospective** (2026-07-31 → 2027-01-22, 26 Friday decisions).
The real holdout evaluation is sealed until every one of those decisions has
bar coverage; exploratory runs on the contaminated pre-lock span are allowed
but cannot accept the hypothesis.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Final

import numpy as np

from cryptofactors.execution.live import MAX_GROSS_LEVERAGE, MAX_SINGLE_ASSET_WEIGHT
from cryptofactors.execution.paper_loop import FactorDrivenPaperLoop, PaperLoopResult
from cryptofactors.execution.risk_limits import compute_live_gate_satisfied
from cryptofactors.factors.tsmom import (
    TSMOM_365_30_FACTOR_ID,
    TimeSeriesMomentumFactor,
    make_tsmom_365_30,
)
from cryptofactors.portfolio.perpetual_simulation import LongShortRankAllocator
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)
from cryptofactors.universe.binding import (
    BINDING_EVIDENCE_KEY,
    BINDING_EVIDENCE_SERIES_KEY,
    DATA011_QUALITY_BAR_PANEL_DATASET_ID,
    PAPER_PANEL_SURVIVORSHIP_POLICY,
    UNIVERSE_BINDING_CODE_VERSION,
    UniverseBinding,
    binding_evidence,
    binding_evidence_series,
    validate_binding_evidence_series,
)

# ---------------------------------------------------------------------------
# Frozen identity (signed pre-registration — do not change)
# ---------------------------------------------------------------------------

EXPERIMENT_ID: Final[str] = "EXP-009"
FACTOR_ID: Final[str] = TSMOM_365_30_FACTOR_ID
MODEL_ARTIFACT_ID: Final[str] = "mod_tsmom_365_30_exp009"
FEATURE_VERSION: Final[str] = "feat_tsmom_365_30_exp009"
CONFIG_VERSION: Final[str] = "cfg_tsmom_365_30_exp009"
LOOKBACK_DAYS: Final[int] = 365
SKIP_DAYS: Final[int] = 30

BAR_PANEL_DATASET_ID: Final[str] = DATA011_QUALITY_BAR_PANEL_DATASET_ID
UNIVERSE_DATASET_ID: Final[str] = (
    "ds_22d2100a575a9764cceec9cc75f45867047969d1b348fd630771bfb083f5b3d8"
)

DATA_LOCK_DATE: Final[datetime] = datetime(2026, 7, 27, 0, 0, 0, tzinfo=UTC)
EXPLORATION_START: Final[datetime] = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
EXPLORATION_END: Final[datetime] = datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)

HOLDOUT_START: Final[datetime] = datetime(2026, 7, 31, 0, 0, 0, tzinfo=UTC)
HOLDOUT_END: Final[datetime] = datetime(2027, 1, 22, 0, 0, 0, tzinfo=UTC)
REQUIRED_HOLDOUT_DECISIONS: Final[int] = 26

# Cost: 5 bps fee + 5 bps slippage per side
FEE_RATE: Final[float] = 0.0005
SLIPPAGE_RATE: Final[float] = 0.0005
INITIAL_CASH: Final[float] = 100_000.0

# Risk (ALLOC-001 constants)
MAX_SINGLE_WEIGHT: Final[float] = MAX_SINGLE_ASSET_WEIGHT  # 0.15
MAX_GROSS: Final[float] = MAX_GROSS_LEVERAGE  # 1.0
RISK_ENFORCEMENT: Final[str] = "clip_and_renormalize"
REBALANCE_SCHEDULE: Final[str] = "weekly_friday_00utc"

# Source paths that determine EXP-009 artifact identity (must be clean at HEAD).
# Covers first-party modules loaded on the holdout / paper-session path — not
# only the experiment entrypoint (dirty transitive deps still change outcomes).
EXP009_SOURCE_PATHS: Final[tuple[str, ...]] = (
    "src/cryptofactors/experiments/exp009.py",
    "src/cryptofactors/factors/tsmom.py",
    "src/cryptofactors/factors/contract.py",
    "src/cryptofactors/execution/paper_loop.py",
    "src/cryptofactors/execution/paper.py",
    "src/cryptofactors/execution/risk_limits.py",
    "src/cryptofactors/execution/live.py",
    "src/cryptofactors/execution/symbols.py",
    "src/cryptofactors/portfolio/perpetual_simulation.py",
    "src/cryptofactors/portfolio/simulation.py",
    "src/cryptofactors/universe/binding.py",
    "src/cryptofactors/universe/cmc_survivorship.py",
    "src/cryptofactors/promotion/__init__.py",
    "src/cryptofactors/promotion/models.py",
    "src/cryptofactors/promotion/registry.py",
    "src/cryptofactors/promotion/state_machine.py",
    "src/cryptofactors/promotion/errors.py",
    "scripts/research/run_exp009_preregistered_tsmom.py",
)

# Stationary bootstrap (Politis & Romano 1994)
BOOTSTRAP_MEAN_BLOCK_LENGTH: Final[int] = 4
BOOTSTRAP_N_RESAMPLES: Final[int] = 10_000
BOOTSTRAP_SEED: Final[int] = 20260727  # data-lock date as default seed
# Monte Carlo p-value estimator (post-signature; bound into fingerprint).
# Long form is recorded on artifacts; compact form is the fingerprint token so
# estimator changes cannot be silent.
P_VALUE_FORMULA: Final[str] = "(exceedances + 1) / (n_resamples + 1)"
P_VALUE_FORMULA_FINGERPRINT: Final[str] = "(e+1)/(B+1)"

# Decision rule
ACCEPT_MIN_NET_RETURN: Final[float] = 0.02
ACCEPT_ALPHA: Final[float] = 0.05

ARTIFACT_RELATIVE_PATH: Final[str] = (
    "research/sprint_004/42_EXP009_PREREGISTERED_TSMOM.json"
)
PRE_REGISTRATION_PATH: Final[str] = "tickets/EXP-009_PRE_REGISTRATION.md"
EVIDENCE_REFERENCE: Final[str] = "REVIEW-0252"

# Repo root for git identity checks (not process CWD).
# exp009.py lives at src/cryptofactors/experiments/exp009.py → parents[3] = repo root.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]

# Includes every material frozen control so a promotion payload cannot silently
# drift from the signed design (datasets, binding policy, risk, calendar, costs,
# and the p-value estimator itself).
FINGERPRINT: Final[str] = hashlib.sha256(
    (
        f"EXP-009:{FACTOR_ID}:lb={LOOKBACK_DAYS}:skip={SKIP_DAYS}:"
        f"holdout={HOLDOUT_START.date()}_{HOLDOUT_END.date()}:"
        f"n={REQUIRED_HOLDOUT_DECISIONS}:{MODEL_ARTIFACT_ID}:"
        f"min_ret={ACCEPT_MIN_NET_RETURN}:alpha={ACCEPT_ALPHA}:"
        f"fee={FEE_RATE}:slip={SLIPPAGE_RATE}:"
        f"wmax={MAX_SINGLE_WEIGHT}:gmax={MAX_GROSS}:"
        f"boot_L={BOOTSTRAP_MEAN_BLOCK_LENGTH}:boot_B={BOOTSTRAP_N_RESAMPLES}:"
        f"boot_seed={BOOTSTRAP_SEED}:p_formula={P_VALUE_FORMULA_FINGERPRINT}:"
        f"bars={BAR_PANEL_DATASET_ID}:univ={UNIVERSE_DATASET_ID}:"
        f"policy={PAPER_PANEL_SURVIVORSHIP_POLICY}:"
        f"ubv={UNIVERSE_BINDING_CODE_VERSION}:"
        f"risk_enf={RISK_ENFORCEMENT}:rebal={REBALANCE_SCHEDULE}"
    ).encode()
).hexdigest()


class EXP009Error(RuntimeError):
    """Base error for the EXP-009 runner."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, object] = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


class EXP009HoldoutNotReadyError(EXP009Error):
    """Raised when a real holdout evaluation is requested before all 26 decisions exist."""


class EXP009Mode(str, Enum):
    """Runner operating modes."""

    READINESS = "readiness"
    EXPLORATORY = "exploratory"
    HOLDOUT = "holdout"
    SYNTHETIC = "synthetic"


class HypothesisVerdict(str, Enum):
    """Pre-registered decision outcomes."""

    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    SEALED = "SEALED"  # holdout not yet evaluable
    EXPLORATORY_ONLY = "EXPLORATORY_ONLY"  # run was not on the holdout


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


def _require_utc(dt: datetime, *, field: str = "datetime") -> datetime:
    if not isinstance(dt, datetime):
        raise EXP009Error(f"{field} must be a datetime", context={"type": type(dt).__name__})
    if dt.tzinfo is None:
        raise EXP009Error(f"{field} must be timezone-aware UTC", context={"value": str(dt)})
    return dt.astimezone(UTC)


def friday_decision_times(
    start: datetime,
    end: datetime,
    *,
    require_friday: bool = True,
) -> list[datetime]:
    """Weekly Friday 00:00 UTC decisions from ``start`` through ``end`` inclusive.

    When ``require_friday`` is True (default), ``start`` must itself be a Friday
    so the schedule matches the pre-registered calendar exactly.
    """
    start = _require_utc(start, field="start")
    end = _require_utc(end, field="end")
    if end < start:
        raise EXP009Error(
            "end must be >= start",
            context={"start": start.isoformat(), "end": end.isoformat()},
        )
    if require_friday and start.weekday() != 4:
        raise EXP009Error(
            "start must be a Friday (weekday=4) for the pre-registered weekly calendar",
            context={"start": start.isoformat(), "weekday": start.weekday()},
        )
    times: list[datetime] = []
    t = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
    while t <= end_day:
        times.append(t)
        t += timedelta(days=7)
    return times


def holdout_decision_times() -> list[datetime]:
    """The frozen 26 Friday decisions of the prospective holdout window."""
    times = friday_decision_times(HOLDOUT_START, HOLDOUT_END, require_friday=True)
    if len(times) != REQUIRED_HOLDOUT_DECISIONS:
        raise EXP009Error(
            "holdout calendar does not produce the pre-registered decision count",
            context={
                "expected": REQUIRED_HOLDOUT_DECISIONS,
                "got": len(times),
                "first": times[0].isoformat() if times else None,
                "last": times[-1].isoformat() if times else None,
            },
        )
    return times


def exploration_decision_times(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[datetime]:
    """Friday decisions inside the exploration span (contaminated; not for accept).

    Aligns the first decision to the first Friday on or after ``start``.
    """
    start = _require_utc(start or EXPLORATION_START, field="start")
    end = _require_utc(end or EXPLORATION_END, field="end")
    # First Friday on or after start.
    offset = (4 - start.weekday()) % 7
    first_friday = (start + timedelta(days=offset)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if first_friday < start:
        first_friday += timedelta(days=7)
    if first_friday > end:
        return []
    return friday_decision_times(first_friday, end, require_friday=True)


# ---------------------------------------------------------------------------
# Stationary bootstrap (Politis & Romano 1994)
# ---------------------------------------------------------------------------


def stationary_bootstrap_indices(
    n: int,
    mean_block_length: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw one stationary-bootstrap index path of length ``n``.

    Block lengths are geometric with mean ``mean_block_length``; new block
    starts are uniform on ``{0, ..., n-1}``. Indices wrap circularly so every
    observation is equally likely under the stationary measure.
    """
    if n <= 0:
        raise EXP009Error("n must be positive", context={"n": n})
    if mean_block_length < 1:
        raise EXP009Error(
            "mean_block_length must be >= 1",
            context={"mean_block_length": mean_block_length},
        )
    p_new = 1.0 / float(mean_block_length)
    indices = np.empty(n, dtype=np.int64)
    idx = int(rng.integers(0, n))
    for i in range(n):
        indices[i] = idx
        if rng.random() < p_new:
            idx = int(rng.integers(0, n))
        else:
            idx = (idx + 1) % n
    return indices


def stationary_bootstrap_mean_pvalue(
    weekly_returns: Sequence[float],
    *,
    n_resamples: int = BOOTSTRAP_N_RESAMPLES,
    mean_block_length: int = BOOTSTRAP_MEAN_BLOCK_LENGTH,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """One-sided stationary-bootstrap p-value for H0: mean weekly return <= 0.

    Centers the series under H0 (mean = 0), resamples with the stationary
    bootstrap, and reports the Monte Carlo corrected one-sided p-value
    ``(exceedances + 1) / (n_resamples + 1)``.
    """
    arr = np.asarray(list(weekly_returns), dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        raise EXP009Error(
            "weekly_returns must be a non-empty 1-d sequence",
            context={"size": int(arr.size), "ndim": int(arr.ndim)},
        )
    if not np.all(np.isfinite(arr)):
        raise EXP009Error("weekly_returns must be finite")

    n = int(arr.size)
    observed_mean = float(np.mean(arr))
    # Center under H0: mean = 0, then stationary-bootstrap the centered series.
    # p = share of bootstrap means >= observed mean (one-sided upper tail).
    centered = arr - observed_mean
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = stationary_bootstrap_indices(n, mean_block_length, rng)
        boot_means[i] = float(np.mean(centered[idx]))

    exceedances = int(np.sum(boot_means >= observed_mean))
    # Monte Carlo correction: (exceedances + 1) / (B + 1) — never reports p = 0
    # and is slightly conservative vs the raw frequency.
    p_value = (exceedances + 1) / float(n_resamples + 1)

    return {
        "method": "stationary_block_bootstrap",
        "null": "mean_weekly_return <= 0",
        "alternative": "mean_weekly_return > 0",
        "one_sided": True,
        "observed_mean_weekly_return": observed_mean,
        "n_periods": n,
        "n_resamples": n_resamples,
        "mean_block_length": mean_block_length,
        "seed": seed,
        "exceedances": exceedances,
        "p_value": float(p_value),
        "p_value_formula": P_VALUE_FORMULA,
    }


def apply_decision_rule(
    total_net_return: float,
    p_value: float,
    *,
    min_net_return: float = ACCEPT_MIN_NET_RETURN,
    alpha: float = ACCEPT_ALPHA,
) -> dict[str, Any]:
    """Apply the pre-registered accept/reject rule.

    Accept iff ``total_net_return >= +0.02`` AND ``p <= 0.05`` (one-sided).
    Otherwise reject. No post-hoc rescue.
    """
    meets_return = total_net_return >= min_net_return
    meets_p = p_value <= alpha
    accept = bool(meets_return and meets_p)
    return {
        "verdict": HypothesisVerdict.ACCEPT.value if accept else HypothesisVerdict.REJECT.value,
        "total_net_return": float(total_net_return),
        "p_value": float(p_value),
        "min_net_return": float(min_net_return),
        "alpha": float(alpha),
        "meets_return_threshold": meets_return,
        "meets_significance": meets_p,
        "rule": (
            f"ACCEPT if total_net_return >= {min_net_return} AND p <= {alpha} "
            "(one-sided); otherwise REJECT"
        ),
    }


# ---------------------------------------------------------------------------
# Holdout readiness gate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HoldoutReadiness:
    """Whether the prospective holdout may be opened for evaluation."""

    ready: bool
    required_decisions: int
    decision_times: tuple[datetime, ...]
    missing_decision_times: tuple[datetime, ...]
    data_lock_date: datetime
    holdout_start: datetime
    holdout_end: datetime
    latest_available_bar: datetime | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "required_decisions": self.required_decisions,
            "decision_count_calendar": len(self.decision_times),
            "decision_times": [t.isoformat() for t in self.decision_times],
            "missing_decision_times": [t.isoformat() for t in self.missing_decision_times],
            "missing_count": len(self.missing_decision_times),
            "data_lock_date": self.data_lock_date.isoformat(),
            "holdout_start": self.holdout_start.isoformat(),
            "holdout_end": self.holdout_end.isoformat(),
            "latest_available_bar": (
                self.latest_available_bar.isoformat()
                if self.latest_available_bar is not None
                else None
            ),
            "reason": self.reason,
        }


def assess_holdout_readiness(
    *,
    latest_available_bar: datetime | None = None,
    available_decision_times: Sequence[datetime] | None = None,
    now: datetime | None = None,
) -> HoldoutReadiness:
    """Gate real holdout evaluation until all 26 post-lock Fridays have data.

    A decision is considered available when either:
    - it appears in ``available_decision_times`` (strictly after the data lock and
      not after wall clock), or
    - ``latest_available_bar`` is on or after that decision time **and** is itself
      after the data lock and not after wall clock.

    Clock clamps (cannot be bypassed by the caller):
    - ``latest_available_bar > now`` raises — future bars are not evidence.
    - ``latest_available_bar <= DATA_LOCK_DATE`` contributes no holdout Fridays
      (``available`` stays empty → all 26 missing → sealed).
    - Each ``available_decision_times`` entry after wall clock raises; entries at
      or before the data lock are ignored (they never open the gate, but they
      also never permanently seal a fully-covered holdout).

    If neither source is supplied, the holdout is not ready (prospective by
    construction until new bars land after the data lock).

    ``now`` defaults to wall-clock UTC; inject only in tests.
    """
    wall = _require_utc(now, field="now") if now is not None else datetime.now(UTC)
    calendar = tuple(holdout_decision_times())
    available: set[datetime] = set()
    # Diagnostic only: does not participate in the ready boolean. Pre-lock
    # entries are skipped below; a pre-lock latest leaves available empty so
    # all 26 calendar Fridays are already missing.
    saw_pre_lock_claim = False

    if available_decision_times is not None:
        for raw in available_decision_times:
            t = _require_utc(raw).replace(hour=0, minute=0, second=0, microsecond=0)
            if t > wall:
                raise EXP009Error(
                    "available_decision_times entry is after wall clock; "
                    "refusing future-dated holdout coverage claims",
                    context={"decision_time": t.isoformat(), "now": wall.isoformat()},
                )
            if t <= DATA_LOCK_DATE:
                # Ignore pre-lock timestamps; they are not holdout coverage.
                saw_pre_lock_claim = True
                continue
            available.add(t)

    latest: datetime | None = None
    if latest_available_bar is not None:
        latest = _require_utc(latest_available_bar, field="latest_available_bar")
        if latest > wall:
            raise EXP009Error(
                "latest_available_bar is after wall clock; refusing future-dated "
                "holdout coverage claims",
                context={
                    "latest_available_bar": latest.isoformat(),
                    "now": wall.isoformat(),
                },
            )
        if latest <= DATA_LOCK_DATE:
            saw_pre_lock_claim = True
        else:
            for t in calendar:
                if latest >= t:
                    available.add(t)

    missing = tuple(t for t in calendar if t not in available)
    ready = len(missing) == 0 and len(calendar) == REQUIRED_HOLDOUT_DECISIONS

    if ready:
        reason = (
            f"All {REQUIRED_HOLDOUT_DECISIONS} holdout Friday decisions have bar coverage; "
            "holdout evaluation is authorized under the signed pre-registration."
        )
    elif latest is None and available_decision_times is None:
        reason = (
            "Holdout is prospective and sealed: no post-lock bar coverage was supplied. "
            f"Need all {REQUIRED_HOLDOUT_DECISIONS} Friday decisions from "
            f"{HOLDOUT_START.date()} through {HOLDOUT_END.date()} before evaluation."
        )
    elif saw_pre_lock_claim and not available:
        reason = (
            "Holdout sealed: coverage claims at or before the data lock "
            f"({DATA_LOCK_DATE.isoformat()}) cannot open the prospective window."
        )
    else:
        reason = (
            f"Holdout sealed: {len(missing)} of {REQUIRED_HOLDOUT_DECISIONS} Friday "
            f"decisions lack bar coverage (latest_available_bar="
            f"{latest.isoformat() if latest else None})."
        )

    return HoldoutReadiness(
        ready=ready,
        required_decisions=REQUIRED_HOLDOUT_DECISIONS,
        decision_times=calendar,
        missing_decision_times=missing,
        data_lock_date=DATA_LOCK_DATE,
        holdout_start=HOLDOUT_START,
        holdout_end=HOLDOUT_END,
        latest_available_bar=latest,
        reason=reason,
    )


def require_holdout_ready(readiness: HoldoutReadiness) -> None:
    """Raise ``EXP009HoldoutNotReadyError`` unless the holdout gate is open."""
    if not readiness.ready:
        raise EXP009HoldoutNotReadyError(
            readiness.reason,
            context={
                "missing_count": len(readiness.missing_decision_times),
                "required": readiness.required_decisions,
                "latest_available_bar": (
                    readiness.latest_available_bar.isoformat()
                    if readiness.latest_available_bar
                    else None
                ),
            },
        )


# ---------------------------------------------------------------------------
# Period returns & risk summary from a paper session
# ---------------------------------------------------------------------------


def weekly_net_returns_from_period_logs(
    period_logs: Sequence[Any],
    *,
    initial_cash: float,
) -> list[float]:
    """Extract simple weekly net returns from sequential paper period logs.

    Raises ``EXP009Error`` if any prior equity is non-positive: substituting 0.0
    would bias the bootstrap mean upward and must not be papered over.
    """
    if not period_logs:
        return []
    if float(initial_cash) <= 0:
        raise EXP009Error(
            "initial_cash must be positive to form weekly net returns",
            context={"initial_cash": initial_cash},
        )
    returns: list[float] = []
    prev_equity = float(initial_cash)
    for index, log in enumerate(period_logs):
        equity = float(getattr(log, "equity"))
        if prev_equity <= 0:
            raise EXP009Error(
                "non-positive prior equity in period logs; refusing to impute a "
                "zero weekly return that would bias the bootstrap",
                context={"index": index, "prev_equity": prev_equity, "equity": equity},
            )
        returns.append((equity - prev_equity) / prev_equity)
        prev_equity = equity
    return returns


def risk_summary_from_period_logs(period_logs: Sequence[Any]) -> dict[str, float | bool]:
    """Max single weight / gross leverage and limit compliance from period logs."""
    if not period_logs:
        return {
            "max_abs_single_weight": 0.0,
            "max_gross_leverage": 0.0,
            "max_abs_net_exposure": 0.0,
            "meets_risk_limits": True,
        }
    max_abs_weight = 0.0
    max_gross = 0.0
    max_abs_net = 0.0
    for log in period_logs:
        weights = getattr(log, "target_weights", {}) or {}
        if not weights:
            continue
        abs_weights = [abs(float(w)) for w in weights.values()]
        max_abs_weight = max(max_abs_weight, max(abs_weights, default=0.0))
        gross = sum(abs_weights)
        max_gross = max(max_gross, gross)
        net = abs(sum(float(w) for w in weights.values()))
        max_abs_net = max(max_abs_net, net)
    meets = max_abs_weight <= MAX_SINGLE_WEIGHT + 1e-9 and max_gross <= MAX_GROSS + 1e-9
    return {
        "max_abs_single_weight": round(max_abs_weight, 6),
        "max_gross_leverage": round(max_gross, 6),
        "max_abs_net_exposure": round(max_abs_net, 6),
        "meets_risk_limits": meets,
    }


# ---------------------------------------------------------------------------
# Promotion registration for the frozen model identity
# ---------------------------------------------------------------------------


def _git_cwd(repo_root: Path | None = None) -> str:
    """Resolve the repository root for git identity checks.

    Defaults to the module-anchored repo root, never process CWD, so CLI runs
    from outside the tree cannot validate an unrelated repository.
    """
    return str(repo_root) if repo_root is not None else str(_REPO_ROOT)


def get_executing_source_commit(*, repo_root: Path | None = None) -> str:
    """Return the git HEAD SHA of the executing repository (lowercase).

    Patchable in tests. Raises ``EXP009Error`` if git is unavailable so a
    declared code identity can never silently skip source binding.
    """
    cwd = _git_cwd(repo_root)
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=cwd,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise EXP009Error(
            "cannot resolve executing source commit (git rev-parse HEAD failed)",
            context={"error": str(exc), "cwd": cwd},
        ) from exc
    if not out:
        raise EXP009Error("executing source commit is empty")
    return out.lower()


def require_clean_source_tree(
    *,
    paths: Sequence[str] = EXP009_SOURCE_PATHS,
    repo_root: Path | None = None,
) -> None:
    """Refuse identity claims when artifact-determining source is dirty.

    Follows the ARCH/DATA ``verify_source_identity`` pattern: a declared SHA only
    describes the executing tree if the relevant paths are clean at HEAD.
    """
    cwd = _git_cwd(repo_root)
    try:
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--", *paths],
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=cwd,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise EXP009Error(
            "cannot verify clean source tree (git status failed)",
            context={"error": str(exc), "paths": list(paths), "cwd": cwd},
        ) from exc
    if dirty:
        raise EXP009Error(
            "refusing to bind code identity from a dirty EXP-009 source tree; "
            "commit the artifact-determining source before signing outcomes",
            context={"dirty": dirty, "paths": list(paths), "cwd": cwd},
        )


def _validate_code_commit(code_commit: str) -> str:
    """Return a normalized git SHA bound to the executing *clean* source tree.

    Rejects placeholders, non-hex junk, SHA mismatch vs ``git rev-parse HEAD``,
    and dirty trees on the EXP-009 source closure (matching ARCH/DATA identity).
    Full 40-char equality for full ids; prefix match for abbreviated 7..39 ids.
    """
    commit = code_commit.strip().lower()
    if not commit:
        raise EXP009Error("code_commit must be a non-empty repository SHA")
    if commit in {"exp-009", "exp009", "todo", "unknown", "placeholder"}:
        raise EXP009Error(
            "code_commit must be a real repository SHA, not a ticket placeholder",
            context={"code_commit": code_commit},
        )
    # Accept full (40) or abbreviated (>=7) git object ids only.
    if len(commit) < 7 or len(commit) > 40:
        raise EXP009Error(
            "code_commit must be a git SHA of length 7..40",
            context={"code_commit": code_commit, "length": len(commit)},
        )
    if any(c not in "0123456789abcdef" for c in commit):
        raise EXP009Error(
            "code_commit must be a hexadecimal git SHA",
            context={"code_commit": code_commit},
        )
    head = get_executing_source_commit()
    if len(commit) == 40:
        if commit != head:
            raise EXP009Error(
                "code_commit does not match executing source (git HEAD)",
                context={"code_commit": commit, "executing_source": head},
            )
    else:
        # Abbreviated: declared id must be a prefix of the executing HEAD.
        if not head.startswith(commit):
            raise EXP009Error(
                "code_commit does not match executing source (git HEAD prefix)",
                context={"code_commit": commit, "executing_source": head},
            )
    require_clean_source_tree()
    return commit


def require_signed_dataset_ids(
    *,
    bar_panel_dataset_id: str | None = None,
    universe_dataset_id: str | None = None,
) -> None:
    """Reject any dataset identity other than the signed DATA-011 / UNIVERSE-006 pins.

    Overrides require a re-signed pre-registration; the runner will not accept
    alternate panels or graveyard datasets.
    """
    if bar_panel_dataset_id is not None and bar_panel_dataset_id != BAR_PANEL_DATASET_ID:
        raise EXP009Error(
            "bar_panel_dataset_id is frozen to the signed DATA-011 pin; "
            "re-sign the pre-registration to change it",
            context={
                "got": bar_panel_dataset_id,
                "signed": BAR_PANEL_DATASET_ID,
            },
        )
    if universe_dataset_id is not None and universe_dataset_id != UNIVERSE_DATASET_ID:
        raise EXP009Error(
            "universe_dataset_id is frozen to the signed UNIVERSE-006 pin; "
            "re-sign the pre-registration to change it",
            context={
                "got": universe_dataset_id,
                "signed": UNIVERSE_DATASET_ID,
            },
        )


def require_holdout_calendar_timestamps(
    decision_times: Sequence[datetime],
) -> list[datetime]:
    """Raise unless ``decision_times`` is exactly the frozen 26-Friday calendar.

    Compares **UTC instants** with no hour/minute/second truncation: noon on the
    right calendar date is not the signed Friday 00:00 UTC decision.
    """
    calendar = holdout_decision_times()
    got = [_require_utc(t) for t in decision_times]
    if got != calendar:
        raise EXP009Error(
            "decision timestamps must exactly equal the frozen holdout calendar",
            context={
                "expected_count": len(calendar),
                "got_count": len(got),
                "expected_first": calendar[0].isoformat() if calendar else None,
                "got_first": got[0].isoformat() if got else None,
                "expected_last": calendar[-1].isoformat() if calendar else None,
                "got_last": got[-1].isoformat() if got else None,
            },
        )
    return got


def ensure_model_paper_approved(
    registry: PromotionRegistry,
    *,
    effective_time: datetime,
    code_commit: str,
    bar_panel_dataset_id: str = BAR_PANEL_DATASET_ID,
    universe_dataset_id: str = UNIVERSE_DATASET_ID,
    evidence_reference: str = EVIDENCE_REFERENCE,
) -> None:
    """Idempotently register ``mod_tsmom_365_30_exp009`` through PAPER_APPROVED.

    ``code_commit`` must match the executing repository HEAD. Dataset ids must
    be the signed DATA-011 / UNIVERSE-006 pins.
    """
    effective_time = _require_utc(effective_time, field="effective_time")
    require_signed_dataset_ids(
        bar_panel_dataset_id=bar_panel_dataset_id,
        universe_dataset_id=universe_dataset_id,
    )
    commit = _validate_code_commit(code_commit)
    artifact_id = MODEL_ARTIFACT_ID
    current_state = registry.get_current_state(artifact_id)

    def _payload(target: PromotionTarget) -> PromotionIdentityPayload:
        return PromotionIdentityPayload(
            model_artifact_id=artifact_id,
            experiment_fingerprint=FINGERPRINT,
            dataset_ids=(BAR_PANEL_DATASET_ID, UNIVERSE_DATASET_ID),
            universe_ids=(UNIVERSE_DATASET_ID,),
            code_commit=commit,
            config_version=CONFIG_VERSION,
            feature_version=FEATURE_VERSION,
            representation_version="rep_time_bar_1d",
            portfolio_version="paper_ls_rank_v1",
            cost_model_version="cost_v1_binance_spot_5bps_5bps",
            risk_policy_version="risk_lev1.0_w0.15_v1",
            target_stage=target,
            effective_time=effective_time,
            approving_authority="Lead Quantitative Finance Researcher/Engineer",
            evidence_reference=evidence_reference,
        )

    if current_state is None:
        registry.register_candidate(
            _payload(PromotionTarget.RESEARCH),
            reason="EXP-009 pre-registered tsmom_365_30 candidate",
        )
        current_state = PromotionState.RESEARCH_CANDIDATE

    if current_state == PromotionState.RESEARCH_CANDIDATE:
        registry.transition_state(
            _payload(PromotionTarget.RESEARCH),
            target_state=PromotionState.RESEARCH_ACCEPTED,
            reason="EXP-009 research accepted under signed pre-registration",
        )
        current_state = PromotionState.RESEARCH_ACCEPTED

    if current_state == PromotionState.RESEARCH_ACCEPTED:
        registry.transition_state(
            _payload(PromotionTarget.PAPER),
            target_state=PromotionState.PAPER_APPROVED,
            reason="EXP-009 PAPER_APPROVED for paper execution only (not LIVE)",
        )


# ---------------------------------------------------------------------------
# Artifact schema
# ---------------------------------------------------------------------------


def frozen_factor_block() -> dict[str, Any]:
    return {
        "factor_id": FACTOR_ID,
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "lookback_days": LOOKBACK_DAYS,
        "skip_days": SKIP_DAYS,
        "rebalance": REBALANCE_SCHEDULE,
        "formula": "log(P[t-30d] / P[t-365d])",
        "parameter_freeze": True,
        "economic_rationale": (
            "Canonical ~12-month time-series momentum with ~1-month skip "
            "(Moskowitz, Ooi & Pedersen 2012); adopted a priori, not from "
            "repository grids EXP-004…EXP-008."
        ),
        "fingerprint": FINGERPRINT,
        "bar_panel_dataset_id": BAR_PANEL_DATASET_ID,
        "universe_dataset_id": UNIVERSE_DATASET_ID,
        "survivorship_policy": PAPER_PANEL_SURVIVORSHIP_POLICY,
        "universe_code_version": UNIVERSE_BINDING_CODE_VERSION,
    }


def frozen_cost_risk_block() -> dict[str, Any]:
    return {
        "fee_bps_per_side": 5,
        "slippage_bps_per_side": 5,
        "fee_rate": FEE_RATE,
        "slippage_rate": SLIPPAGE_RATE,
        "max_single_weight": MAX_SINGLE_WEIGHT,
        "max_gross_leverage": MAX_GROSS,
        "enforcement": RISK_ENFORCEMENT,
    }


def frozen_statistical_protocol_block() -> dict[str, Any]:
    return {
        "alpha": ACCEPT_ALPHA,
        "one_sided": True,
        "multiple_testing_correction": None,
        "multiple_testing_note": (
            "None required — exactly one hypothesis is tested (pre-registration §6)."
        ),
        "min_net_return": ACCEPT_MIN_NET_RETURN,
        "test": "stationary_block_bootstrap",
        "mean_block_length_weeks": BOOTSTRAP_MEAN_BLOCK_LENGTH,
        "n_resamples": BOOTSTRAP_N_RESAMPLES,
        "null": "mean_weekly_return <= 0",
        "p_value_formula": P_VALUE_FORMULA,
    }


# Memoize only the expensive bootstrap by equity-path content. Cheap validation
# (calendar, cash, reported-total-is-canonical) always runs before the lookup so
# a cache hit cannot skip defense-in-depth guards.
_RECOMPUTE_BOOTSTRAP_CACHE: dict[str, dict[str, Any]] = {}


def canonical_total_net_return_from_equity_path(
    session_result: PaperLoopResult,
) -> float:
    """Total net return from initial cash and the last period equity.

    This is the canonical economic total for EXP-009 terminal verdicts — not a
    free-standing ``session_result.total_net_return`` field the loop may round
    or that a caller could mis-set independently of the equity path.
    """
    if not session_result.period_logs:
        raise EXP009Error("cannot form canonical total net return from empty period logs")
    initial = float(session_result.initial_cash)
    if initial <= 0:
        raise EXP009Error(
            "initial_cash must be positive for canonical total net return",
            context={"initial_cash": initial},
        )
    final = float(session_result.period_logs[-1].equity)
    return (final - initial) / initial


def compound_total_net_return(weekly_returns: Sequence[float]) -> float:
    """Compound weekly simple returns to a total net return."""
    growth = 1.0
    for w in weekly_returns:
        growth *= 1.0 + float(w)
    return growth - 1.0


def _session_recompute_cache_key(session_result: PaperLoopResult) -> str:
    """Content hash of the equity path inputs to the frozen bootstrap."""
    parts: list[str] = [f"cash={float(session_result.initial_cash):.12g}"]
    for log in session_result.period_logs:
        dt = _require_utc(log.decision_time)
        parts.append(f"{dt.isoformat()}|{float(log.equity):.12g}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def recompute_holdout_statistics(
    session_result: PaperLoopResult,
) -> dict[str, Any]:
    """Recompute frozen bootstrap + decision rule from the session equity path.

    Terminal scientific verdicts must never trust caller-supplied p-values or
    free-standing total_net_return fields. Totals and the decision rule are
    formed from the equity path; the bootstrap is run on the derived weekly
    series under frozen protocol parameters.

    Cheap validation always runs. Only the bootstrap payload is memoized by
    equity-path content so evaluate → terminal gate does not re-run 10k resamples.
    """
    # --- Always-run validation (never skipped by cache) ---
    require_holdout_calendar_timestamps(
        [log.decision_time for log in session_result.period_logs]
    )
    if len(session_result.period_logs) != REQUIRED_HOLDOUT_DECISIONS:
        raise EXP009Error(
            "holdout session must have exactly 26 period logs",
            context={"got": len(session_result.period_logs)},
        )
    if abs(float(session_result.initial_cash) - INITIAL_CASH) > 1e-9:
        raise EXP009Error(
            f"holdout session requires frozen initial_cash={INITIAL_CASH}",
            context={"got": session_result.initial_cash},
        )

    weekly = weekly_net_returns_from_period_logs(
        session_result.period_logs,
        initial_cash=float(session_result.initial_cash),
    )
    if len(weekly) != REQUIRED_HOLDOUT_DECISIONS:
        raise EXP009Error(
            "weekly return series length mismatch",
            context={"got": len(weekly)},
        )

    canonical_total = canonical_total_net_return_from_equity_path(session_result)
    compounded = compound_total_net_return(weekly)
    if abs(canonical_total - compounded) > 1e-9:
        raise EXP009Error(
            "canonical equity-path total disagrees with compounded weekly returns",
            context={
                "equity_path_total": canonical_total,
                "compounded_weekly_total": compounded,
            },
        )
    # Loop-reported total must match the equity path (allow tiny float noise only).
    # Must run every call: the bootstrap cache key does not include reported total.
    reported = float(session_result.total_net_return)
    if abs(reported - canonical_total) > 1e-6:
        raise EXP009Error(
            "session_result.total_net_return is not canonical for the equity path",
            context={
                "reported": reported,
                "canonical_total_net_return": canonical_total,
            },
        )

    # --- Expensive bootstrap (memoized by equity path only) ---
    cache_key = _session_recompute_cache_key(session_result)
    cached_boot = _RECOMPUTE_BOOTSTRAP_CACHE.get(cache_key)
    if cached_boot is not None:
        bootstrap = dict(cached_boot)
    else:
        bootstrap = stationary_bootstrap_mean_pvalue(
            weekly,
            n_resamples=BOOTSTRAP_N_RESAMPLES,
            mean_block_length=BOOTSTRAP_MEAN_BLOCK_LENGTH,
            seed=BOOTSTRAP_SEED,
        )
        # Ensure complete frozen protocol evidence on every bootstrap block.
        bootstrap = {
            **bootstrap,
            "seed": BOOTSTRAP_SEED,
            "n_resamples": BOOTSTRAP_N_RESAMPLES,
            "mean_block_length": BOOTSTRAP_MEAN_BLOCK_LENGTH,
            "p_value_formula": P_VALUE_FORMULA,
            "method": "stationary_block_bootstrap",
        }
        _RECOMPUTE_BOOTSTRAP_CACHE[cache_key] = dict(bootstrap)

    decision = apply_decision_rule(
        canonical_total,
        float(bootstrap["p_value"]),
    )
    return {
        "weekly_net_returns": list(weekly),
        "canonical_total_net_return": float(canonical_total),
        "bootstrap": dict(bootstrap),
        "decision_rule": dict(decision),
        "verdict": decision["verdict"],
    }


def clear_recompute_holdout_statistics_cache() -> None:
    """Drop memoized bootstrap payloads (tests / rare re-runs)."""
    _RECOMPUTE_BOOTSTRAP_CACHE.clear()


def _require_terminal_verdict_evidence(
    *,
    verdict_value: str,
    mode_value: str,
    readiness: HoldoutReadiness,
    session_result: PaperLoopResult | None,
    decision_times: Sequence[datetime] | None,
    binding_series: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any] | None,
    decision_rule: Mapping[str, Any] | None,
) -> None:
    """Fail closed for terminal ACCEPT/REJECT scientific verdicts.

    Both outcomes require the exact 26-period holdout session, a complete binding
    series, risk-compliant weights, and a bootstrap/decision rule owned by
    ``recompute_holdout_statistics`` (memoized; never caller-only stats).
    """
    if verdict_value not in {
        HypothesisVerdict.ACCEPT.value,
        HypothesisVerdict.REJECT.value,
    }:
        return
    if mode_value != EXP009Mode.HOLDOUT.value or not readiness.ready:
        raise EXP009Error(
            f"{verdict_value} requires mode=holdout and an open holdout gate",
            context={
                "mode": mode_value,
                "holdout_ready": readiness.ready,
                "verdict": verdict_value,
            },
        )
    if session_result is None or not session_result.period_logs:
        raise EXP009Error(
            f"{verdict_value} requires a complete holdout session_result with period logs",
        )
    if len(session_result.period_logs) != REQUIRED_HOLDOUT_DECISIONS:
        raise EXP009Error(
            f"{verdict_value} requires exactly 26 holdout period logs",
            context={"got": len(session_result.period_logs)},
        )
    session_times = [log.decision_time for log in session_result.period_logs]
    require_holdout_calendar_timestamps(session_times)
    if decision_times is None:
        raise EXP009Error(
            f"{verdict_value} requires decision_times equal to the holdout calendar",
        )
    require_holdout_calendar_timestamps(decision_times)
    if len(binding_series) != REQUIRED_HOLDOUT_DECISIONS:
        raise EXP009Error(
            f"{verdict_value} requires a complete universe_binding_series (26 entries)",
            context={"got": len(binding_series)},
        )
    risk = risk_summary_from_period_logs(session_result.period_logs)
    if not risk["meets_risk_limits"]:
        raise EXP009Error(
            f"{verdict_value} requires risk-compliant session weights",
            context=dict(risk),
        )
    if abs(float(session_result.initial_cash) - INITIAL_CASH) > 1e-9:
        raise EXP009Error(
            f"{verdict_value} requires frozen initial_cash={INITIAL_CASH}",
            context={"got": session_result.initial_cash},
        )
    if bootstrap is None:
        raise EXP009Error(f"{verdict_value} requires bootstrap results")
    if decision_rule is None:
        raise EXP009Error(f"{verdict_value} requires a decision_rule block")
    if decision_rule.get("verdict") != verdict_value:
        raise EXP009Error(
            f"{verdict_value} artifact verdict disagrees with decision_rule.verdict",
            context={"decision_rule_verdict": decision_rule.get("verdict")},
        )

    # Own the computation (memoized): equity-path total + frozen bootstrap.
    recomputed = recompute_holdout_statistics(session_result)
    recomputed_boot = recomputed["bootstrap"]
    recomputed_rule = recomputed["decision_rule"]
    canonical_total = float(recomputed["canonical_total_net_return"])

    if recomputed_rule["verdict"] != verdict_value:
        raise EXP009Error(
            f"{verdict_value} rejected: recomputed decision rule is "
            f"{recomputed_rule['verdict']}",
            context={
                "canonical_total_net_return": canonical_total,
                "recomputed_p_value": recomputed_boot["p_value"],
                "recomputed": recomputed_rule,
            },
        )
    if abs(float(bootstrap.get("p_value", -1e9)) - float(recomputed_boot["p_value"])) > 1e-12:
        raise EXP009Error(
            f"{verdict_value} bootstrap p_value does not match recomputed frozen bootstrap",
            context={
                "supplied_p_value": bootstrap.get("p_value"),
                "recomputed_p_value": recomputed_boot["p_value"],
            },
        )
    # Complete protocol evidence — not p alone.
    for key in ("seed", "n_resamples", "mean_block_length", "p_value_formula", "method"):
        if bootstrap.get(key) != recomputed_boot.get(key):
            raise EXP009Error(
                f"{verdict_value} bootstrap.{key} is not the frozen protocol evidence",
                context={
                    "supplied": bootstrap.get(key),
                    "canonical": recomputed_boot.get(key),
                },
            )
    if abs(float(decision_rule.get("total_net_return", -1e9)) - canonical_total) > 1e-9:
        raise EXP009Error(
            f"{verdict_value} decision_rule.total_net_return is not the canonical equity-path total",
            context={
                "decision_rule": decision_rule.get("total_net_return"),
                "canonical_total_net_return": canonical_total,
            },
        )
    if abs(
        float(decision_rule.get("p_value", -1e9)) - float(recomputed_boot["p_value"])
    ) > 1e-12:
        raise EXP009Error(
            f"{verdict_value} decision_rule.p_value does not match recomputed bootstrap",
            context={
                "decision_rule": decision_rule.get("p_value"),
                "recomputed": recomputed_boot["p_value"],
            },
        )


def build_artifact(
    *,
    mode: EXP009Mode | str,
    universe_binding: UniverseBinding | None,
    readiness: HoldoutReadiness,
    session_result: PaperLoopResult | None = None,
    decision_times: Sequence[datetime] | None = None,
    bootstrap: Mapping[str, Any] | None = None,
    decision_rule: Mapping[str, Any] | None = None,
    verdict: HypothesisVerdict | str = HypothesisVerdict.SEALED,
    control_database: str | None = None,
    dataset_store_root: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the EXP-009 run artifact with the required ARCH-002 / EXP-009 fields.

    Always includes ``universe_dataset_id``, ``bar_panel_dataset_id``,
    ``universe_binding_series`` (when a session ran), ``survivorship_policy``,
    ``universe_code_version``, and ``survivorship_invalid: false``.
    """
    mode_value = mode.value if isinstance(mode, EXP009Mode) else str(mode)
    verdict_value = verdict.value if isinstance(verdict, HypothesisVerdict) else str(verdict)

    data_mode = (
        "real_asof" if mode_value != EXP009Mode.SYNTHETIC.value else "synthetic"
    )

    universe_dataset_id = (
        universe_binding.universe_dataset_id
        if universe_binding is not None
        else UNIVERSE_DATASET_ID
    )
    bar_panel_dataset_id = (
        getattr(universe_binding, "bar_panel_dataset_id", None)
        if universe_binding is not None
        else BAR_PANEL_DATASET_ID
    ) or BAR_PANEL_DATASET_ID
    # Always enforce signed pins — even when binding is absent (synthetic/readiness).
    require_signed_dataset_ids(
        bar_panel_dataset_id=bar_panel_dataset_id,
        universe_dataset_id=universe_dataset_id,
    )
    survivorship_policy = (
        universe_binding.survivorship_policy
        if universe_binding is not None
        else PAPER_PANEL_SURVIVORSHIP_POLICY
    )
    universe_code_version = (
        universe_binding.universe_code_version
        if universe_binding is not None
        else UNIVERSE_BINDING_CODE_VERSION
    )
    if survivorship_policy != PAPER_PANEL_SURVIVORSHIP_POLICY:
        raise EXP009Error(
            "survivorship_policy is frozen by the signed pre-registration",
            context={"got": survivorship_policy, "signed": PAPER_PANEL_SURVIVORSHIP_POLICY},
        )
    if universe_code_version != UNIVERSE_BINDING_CODE_VERSION:
        raise EXP009Error(
            "universe_code_version is frozen by the signed pre-registration",
            context={"got": universe_code_version, "signed": UNIVERSE_BINDING_CODE_VERSION},
        )

    binding_series: list[dict[str, Any]] = []
    first_binding: dict[str, Any] | None = None
    session_block: dict[str, Any] | None = None

    if session_result is not None:
        if not session_result.period_logs:
            raise EXP009Error("session_result has no period logs")
        binding_series = binding_evidence_series(session_result.period_logs)
        times = [log.decision_time for log in session_result.period_logs]
        validate_binding_evidence_series(
            binding_series,
            decision_count=len(session_result.period_logs),
            decision_times=times,
        )
        first_binding = binding_series[0]
        risk = risk_summary_from_period_logs(session_result.period_logs)
        is_complete = (
            decision_times is not None
            and len(session_result.period_logs) == len(decision_times)
            and len(decision_times) > 0
        )
        # Provisional totals; terminal holdout path rewrites from equity path below.
        session_total = float(session_result.total_net_return)
        final_equity = float(session_result.final_equity)
        live_gate = compute_live_gate_satisfied(
            data_mode,
            session_total,
            bool(risk["meets_risk_limits"]),
            bool(is_complete),
        )
        session_block = {
            "start": times[0].isoformat(),
            "end": times[-1].isoformat(),
            "decision_count": len(session_result.period_logs),
            BINDING_EVIDENCE_SERIES_KEY: binding_series,
            "total_trades_executed": session_result.total_trades_executed,
            "initial_cash": session_result.initial_cash,
            "final_equity": final_equity,
            "total_net_return": session_total,
            "total_net_return_source": "session_result",
            "max_abs_single_weight": risk["max_abs_single_weight"],
            "max_gross_leverage": risk["max_gross_leverage"],
            "max_abs_net_exposure": risk["max_abs_net_exposure"],
            "meets_risk_limits": risk["meets_risk_limits"],
            "is_complete": is_complete,
            "live_gate_satisfied": live_gate,
            "live_eligible": False,
        }
    elif universe_binding is not None and decision_times:
        # Readiness path: fingerprint each calendar decision without executing.
        first = _require_utc(decision_times[0])
        first_binding = binding_evidence(universe_binding, first)
        # Coverage time series for the planned holdout calendar (not executed).
        for dt in decision_times:
            binding_series.append(binding_evidence(universe_binding, _require_utc(dt)))

    if verdict_value in {
        HypothesisVerdict.ACCEPT.value,
        HypothesisVerdict.REJECT.value,
    }:
        # Validate against caller-supplied stats first (must match owned recompute).
        _require_terminal_verdict_evidence(
            verdict_value=verdict_value,
            mode_value=mode_value,
            readiness=readiness,
            session_result=session_result,
            decision_times=decision_times,
            binding_series=binding_series,
            bootstrap=bootstrap,
            decision_rule=decision_rule,
        )
        # Publish only owned, complete statistical evidence (memoized; no second B).
        if session_result is None:
            raise EXP009Error(f"{verdict_value} requires session_result for canonical evidence")
        canonical_holdout = recompute_holdout_statistics(session_result)
        bootstrap = canonical_holdout["bootstrap"]
        decision_rule = canonical_holdout["decision_rule"]
        if session_block is not None:
            session_block["total_net_return"] = float(
                canonical_holdout["canonical_total_net_return"]
            )
            session_block["total_net_return_source"] = "equity_path_canonical"
            session_block["final_equity"] = float(session_result.period_logs[-1].equity)
            session_block["weekly_net_returns"] = list(
                canonical_holdout["weekly_net_returns"]
            )
            session_block["live_gate_satisfied"] = compute_live_gate_satisfied(
                data_mode,
                float(canonical_holdout["canonical_total_net_return"]),
                bool(session_block["meets_risk_limits"]),
                bool(session_block["is_complete"]),
            )

    artifact: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "pre_registration": PRE_REGISTRATION_PATH,
        "pre_registration_status": "SIGNED",
        "evidence_reference": EVIDENCE_REFERENCE,
        "data_mode": data_mode,
        "mode": mode_value,
        "factor": frozen_factor_block(),
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "factor_id": FACTOR_ID,
        "lookback_days": LOOKBACK_DAYS,
        "skip_days": SKIP_DAYS,
        "control_database": control_database,
        "dataset_store_root": dataset_store_root,
        "bar_panel_dataset_id": bar_panel_dataset_id,
        "universe_dataset_id": universe_dataset_id,
        "canonical_dataset_id": bar_panel_dataset_id,
        "canonical_dataset_quality_status": "PASS",
        "survivorship_policy": survivorship_policy,
        "universe_code_version": universe_code_version,
        "survivorship_invalid": False,
        BINDING_EVIDENCE_KEY: first_binding,
        BINDING_EVIDENCE_SERIES_KEY: binding_series,
        "cost_risk_policy": frozen_cost_risk_block(),
        "statistical_protocol": frozen_statistical_protocol_block(),
        "holdout": readiness.as_dict(),
        "exploration_window": {
            "start": EXPLORATION_START.isoformat(),
            "end": EXPLORATION_END.isoformat(),
            "note": (
                "Contaminated by prior grids/paper sessions; exploratory only. "
                "Must not be used to accept the hypothesis, tune parameters, or promote."
            ),
        },
        "decision_rule": dict(decision_rule) if decision_rule else None,
        "bootstrap": dict(bootstrap) if bootstrap else None,
        "verdict": verdict_value,
        "session": session_block,
        "live_eligible": False,
        "live_eligible_note": (
            "EXP-009 is paper/research only. Promotion requires a separate PROMO ticket "
            "and only if the holdout passes the pre-registered rule."
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    if extra:
        for key, value in extra.items():
            if key in artifact:
                raise EXP009Error(
                    f"extra artifact key collides with reserved field: {key}",
                )
            artifact[key] = value

    _validate_required_artifact_fields(artifact)
    return artifact


def _validate_required_artifact_fields(artifact: Mapping[str, Any]) -> None:
    """Fail closed if ARCH-002 / EXP-009 required fields are missing or invalid."""
    required = (
        "universe_dataset_id",
        "bar_panel_dataset_id",
        "survivorship_policy",
        "universe_code_version",
        "survivorship_invalid",
        BINDING_EVIDENCE_SERIES_KEY,
    )
    missing = [k for k in required if k not in artifact]
    if missing:
        raise EXP009Error(
            f"artifact missing required fields: {missing}",
        )
    if artifact["survivorship_invalid"] is not False:
        raise EXP009Error(
            "EXP-009 artifacts must set survivorship_invalid: false",
            context={"value": artifact["survivorship_invalid"]},
        )
    if not artifact["universe_dataset_id"]:
        raise EXP009Error("universe_dataset_id must be non-empty")
    if not artifact["bar_panel_dataset_id"]:
        raise EXP009Error("bar_panel_dataset_id must be non-empty")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class EXP009Runner:
    """Frozen EXP-009 paper session runner.

    Parameters
    ----------
    universe_binding:
        ARCH-002 survivorship binding (quality-bar panel minus CMC-dead).
    promotion_registry:
        Registry used to ensure the model is PAPER_APPROVED before the loop.
    as_of_store:
        Market as-of surface (paper-symbol keys) for factor scores.
    get_prices_at:
        ``(decision_time, universe) -> {symbol: price}`` for rebalances.
    code_commit:
        Must match clean git HEAD for the EXP-009 source closure.
    bootstrap_seed:
        Must equal the signed ``BOOTSTRAP_SEED``; retained only so post-construction
        mutation is detected before holdout evaluation. Other economics have no
        override surface (module constants only).
    """

    universe_binding: UniverseBinding
    promotion_registry: PromotionRegistry
    as_of_store: Any
    get_prices_at: Callable[[datetime, Sequence[str]], dict[str, float]]
    code_commit: str
    bootstrap_seed: int = BOOTSTRAP_SEED

    def __post_init__(self) -> None:
        # Cheap deterministic checks first so construction failures are actionable
        # and do not depend on working-tree dirtiness masking them.
        require_signed_dataset_ids(
            universe_dataset_id=getattr(
                self.universe_binding, "universe_dataset_id", None
            ),
        )
        bar_from_binding = getattr(self.universe_binding, "bar_panel_dataset_id", None)
        if bar_from_binding is not None:
            require_signed_dataset_ids(bar_panel_dataset_id=str(bar_from_binding))
        if self.bootstrap_seed != BOOTSTRAP_SEED:
            raise EXP009Error(
                "bootstrap_seed is frozen by the signed pre-registration",
                context={"got": self.bootstrap_seed, "signed": BOOTSTRAP_SEED},
            )
        # Git HEAD + clean-tree identity last (environment-dependent).
        _validate_code_commit(self.code_commit)

    def make_factor(self) -> TimeSeriesMomentumFactor:
        return make_tsmom_365_30(
            self.as_of_store,
            market_dataset_id=BAR_PANEL_DATASET_ID,
        )

    def run_session(
        self,
        decision_times: Sequence[datetime],
        *,
        ensure_promotion: bool = True,
    ) -> PaperLoopResult:
        """Execute the frozen factor over ``decision_times`` under risk + cost policy."""
        if not decision_times:
            raise EXP009Error("decision_times must be non-empty")
        times = [_require_utc(t) for t in decision_times]
        if ensure_promotion:
            ensure_model_paper_approved(
                self.promotion_registry,
                effective_time=times[0],
                code_commit=self.code_commit,
                bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
                universe_dataset_id=UNIVERSE_DATASET_ID,
            )
        factor = self.make_factor()
        loop = FactorDrivenPaperLoop(
            model_artifact_id=MODEL_ARTIFACT_ID,
            promotion_registry=self.promotion_registry,
            factor=factor,
            allocator=LongShortRankAllocator(target_leverage=1.0),
            initial_cash=INITIAL_CASH,
            fee_rate=FEE_RATE,
            slippage_rate=SLIPPAGE_RATE,
            max_single_weight=MAX_SINGLE_WEIGHT,
            max_gross_leverage=MAX_GROSS,
            resume_from_store=False,
        )
        return loop.run_loop(
            universe_binding=self.universe_binding,
            decision_times=times,
            get_prices_at=self.get_prices_at,
            min_observation_days=14,
        )

    def evaluate_holdout_session(
        self,
        session_result: PaperLoopResult,
        *,
        readiness: HoldoutReadiness | None = None,
    ) -> dict[str, Any]:
        """Bootstrap + decision rule for a completed holdout session.

        ``readiness`` is mandatory and must come from an external coverage probe
        (bar max period / wall clock), not from the session's own period logs.
        Self-certifying ``available_decision_times=period_logs`` is forbidden.
        Period timestamps must exactly equal the frozen 26-Friday calendar
        (UTC instants). Statistics are always recomputed under frozen protocol
        parameters (memoized by session content so the terminal artifact gate
        does not pay a second bootstrap).
        """
        if readiness is None:
            raise EXP009Error(
                "evaluate_holdout_session requires an externally assessed "
                "HoldoutReadiness; refusing to derive readiness from session logs",
            )
        require_holdout_ready(readiness)
        if self.bootstrap_seed != BOOTSTRAP_SEED:
            raise EXP009Error(
                "holdout bootstrap seed is frozen by the signed pre-registration",
                context={"seed": self.bootstrap_seed, "frozen": BOOTSTRAP_SEED},
            )
        return recompute_holdout_statistics(session_result)

    def run_holdout(
        self,
        *,
        latest_available_bar: datetime | None = None,
        available_decision_times: Sequence[datetime] | None = None,
        now: datetime | None = None,
    ) -> tuple[PaperLoopResult, dict[str, Any], HoldoutReadiness]:
        """Open the real holdout only when all 26 decisions are covered."""
        readiness = assess_holdout_readiness(
            latest_available_bar=latest_available_bar,
            available_decision_times=available_decision_times,
            now=now,
        )
        require_holdout_ready(readiness)
        times = holdout_decision_times()
        result = self.run_session(times)
        evaluation = self.evaluate_holdout_session(result, readiness=readiness)
        return result, evaluation, readiness

    def run_exploratory(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[PaperLoopResult, list[datetime]]:
        """Run on the exploration window. Results cannot accept the hypothesis."""
        times = exploration_decision_times(start=start, end=end)
        if not times:
            raise EXP009Error("exploration window produced no Friday decisions")
        # Guard: never let exploratory bleed into the holdout calendar.
        for t in times:
            if t >= HOLDOUT_START:
                raise EXP009Error(
                    "exploratory decision times must be strictly before holdout start",
                    context={"decision_time": t.isoformat()},
                )
        result = self.run_session(times)
        return result, times


@dataclass(frozen=True, slots=True)
class EXP009ReadinessReport:
    """Infrastructure readiness without evaluating holdout outcomes."""

    holdout: HoldoutReadiness
    binding_ok: bool
    universe_dataset_id: str | None
    bar_panel_dataset_id: str | None
    sample_coverage: dict[str, Any] | None
    checks: dict[str, bool] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "holdout": self.holdout.as_dict(),
            "binding_ok": self.binding_ok,
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "sample_coverage": self.sample_coverage,
            "checks": dict(self.checks),
            "notes": list(self.notes),
        }


def run_readiness_checks(
    universe_binding: UniverseBinding | None,
    *,
    latest_available_bar: datetime | None = None,
    now: datetime | None = None,
) -> EXP009ReadinessReport:
    """Check binding + holdout gate without opening the real holdout.

    ``now`` is forwarded to the holdout gate so a non-throwing probe can supply
    a wall clock (or a frozen test clock) when probing future-dated bar claims.
    """
    holdout = assess_holdout_readiness(
        latest_available_bar=latest_available_bar,
        now=now,
    )
    notes: list[str] = [holdout.reason]
    checks: dict[str, bool] = {
        "pre_registration_signed": True,
        "factor_frozen": True,
        "holdout_calendar_26_fridays": len(holdout.decision_times)
        == REQUIRED_HOLDOUT_DECISIONS,
        "holdout_ready": holdout.ready,
        "binding_loaded": universe_binding is not None,
    }

    sample_coverage: dict[str, Any] | None = None
    universe_dataset_id: str | None = None
    bar_panel_dataset_id: str | None = None
    binding_ok = False

    if universe_binding is not None:
        universe_dataset_id = universe_binding.universe_dataset_id
        bar_panel_dataset_id = getattr(universe_binding, "bar_panel_dataset_id", None)
        try:
            # Sample coverage at a few declared times (pre-reg membership table).
            sample_times = [
                datetime(2020, 6, 1, tzinfo=UTC),
                datetime(2022, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2026, 6, 1, tzinfo=UTC),
            ]
            sample_coverage = {}
            for st in sample_times:
                univ = universe_binding.universe_at(st)
                report = universe_binding.coverage_report(st)
                sample_coverage[st.date().isoformat()] = {
                    "eligible_count": len(univ),
                    "coverage_report": report,
                }
            # Fingerprint first holdout decision (may be empty universe pre-bars).
            fp = binding_evidence(universe_binding, HOLDOUT_START)
            checks["binding_fingerprint_ok"] = bool(fp.get("universe_dataset_id"))
            checks["survivorship_policy_match"] = (
                universe_binding.survivorship_policy == PAPER_PANEL_SURVIVORSHIP_POLICY
            )
            checks["code_version_match"] = (
                universe_binding.universe_code_version == UNIVERSE_BINDING_CODE_VERSION
            )
            binding_ok = True
            notes.append(
                f"Binding loaded: universe={universe_dataset_id}, "
                f"bar_panel={bar_panel_dataset_id}, policy={universe_binding.survivorship_policy}."
            )
        except Exception as exc:  # noqa: BLE001
            binding_ok = False
            checks["binding_fingerprint_ok"] = False
            notes.append(f"Binding probe failed: {exc}")
    else:
        notes.append("No universe binding supplied; load via load_paper_universe_binding.")

    checks["all_ready_for_holdout_eval"] = bool(
        binding_ok and holdout.ready and checks["holdout_calendar_26_fridays"]
    )
    return EXP009ReadinessReport(
        holdout=holdout,
        binding_ok=binding_ok,
        universe_dataset_id=universe_dataset_id,
        bar_panel_dataset_id=bar_panel_dataset_id,
        sample_coverage=sample_coverage,
        checks=checks,
        notes=tuple(notes),
    )


__all__ = [
    "ACCEPT_ALPHA",
    "ACCEPT_MIN_NET_RETURN",
    "ARTIFACT_RELATIVE_PATH",
    "BAR_PANEL_DATASET_ID",
    "BOOTSTRAP_MEAN_BLOCK_LENGTH",
    "BOOTSTRAP_N_RESAMPLES",
    "BOOTSTRAP_SEED",
    "CONFIG_VERSION",
    "DATA_LOCK_DATE",
    "EXPERIMENT_ID",
    "EXPLORATION_END",
    "EXPLORATION_START",
    "FACTOR_ID",
    "FEATURE_VERSION",
    "FEE_RATE",
    "FINGERPRINT",
    "EXP009_SOURCE_PATHS",
    "HOLDOUT_END",
    "HOLDOUT_START",
    "INITIAL_CASH",
    "LOOKBACK_DAYS",
    "MAX_GROSS",
    "MAX_SINGLE_WEIGHT",
    "MODEL_ARTIFACT_ID",
    "PRE_REGISTRATION_PATH",
    "P_VALUE_FORMULA",
    "P_VALUE_FORMULA_FINGERPRINT",
    "REBALANCE_SCHEDULE",
    "REQUIRED_HOLDOUT_DECISIONS",
    "RISK_ENFORCEMENT",
    "SKIP_DAYS",
    "SLIPPAGE_RATE",
    "UNIVERSE_DATASET_ID",
    "EXP009Error",
    "EXP009HoldoutNotReadyError",
    "EXP009Mode",
    "EXP009ReadinessReport",
    "EXP009Runner",
    "HoldoutReadiness",
    "HypothesisVerdict",
    "apply_decision_rule",
    "assess_holdout_readiness",
    "build_artifact",
    "ensure_model_paper_approved",
    "exploration_decision_times",
    "friday_decision_times",
    "frozen_cost_risk_block",
    "frozen_factor_block",
    "frozen_statistical_protocol_block",
    "get_executing_source_commit",
    "holdout_decision_times",
    "canonical_total_net_return_from_equity_path",
    "clear_recompute_holdout_statistics_cache",
    "compound_total_net_return",
    "recompute_holdout_statistics",
    "require_clean_source_tree",
    "require_holdout_calendar_timestamps",
    "require_holdout_ready",
    "require_signed_dataset_ids",
    "risk_summary_from_period_logs",
    "run_readiness_checks",
    "stationary_bootstrap_indices",
    "stationary_bootstrap_mean_pvalue",
    "weekly_net_returns_from_period_logs",
]
