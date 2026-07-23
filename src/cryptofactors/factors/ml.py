"""ML-001 — ML challengers (experiment #21).

Implements regularized linear models (Ridge, ElasticNet) and shallow trees (XGBoost).
Predicts cross-sectional returns using baseline factors as features.
Trains on an expanding window of historical cross-sections, strictly avoiding lookahead
by requiring label realization (event_end) <= decision_time.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import math

import numpy as np
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from cryptofactors.factors.contract import Factor, FactorFrame, FactorValue
from cryptofactors.validation.labels import LabelConfig, LabelEngine


class MLFactorError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context) if context else {}

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} | context={self.context!r}"
        return self.message


def _require_utc(dt: datetime, *, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise MLFactorError(
            f"{field} must be a datetime",
            context={"type": type(dt).__name__},
        )
    if dt.tzinfo is None:
        raise MLFactorError(
            f"{field} must be timezone-aware UTC",
            context={"value": str(dt)},
        )
    return dt.astimezone(timezone.utc)


def _normalize_universe(universe: Sequence[str]) -> tuple[str, ...]:
    if universe is None:
        raise MLFactorError("universe must not be None")
    if isinstance(universe, (str, bytes, bytearray)):
        raise MLFactorError(
            "universe must be a sequence of instrument ids",
            context={"type": type(universe).__name__},
        )
    ids: list[str] = []
    for item in universe:
        if not isinstance(item, str):
            raise MLFactorError(
                "universe entries must be str",
                context={"type": type(item).__name__},
            )
        text = item.strip()
        if not text:
            raise MLFactorError("universe entries must be non-empty strings")
        ids.append(text)
    if not ids:
        raise MLFactorError("universe must be non-empty")
    return tuple(sorted(set(ids)))


class _MLFactorBase:
    """Base class for ML factors with expanding window training."""

    factor_version: str = "1"
    factor_id: str = ""

    def __init__(
        self,
        features: Sequence[Factor],
        label_engine: LabelEngine,
        label_config: LabelConfig,
        train_schedule: Sequence[datetime],
    ) -> None:
        if not features:
            raise MLFactorError("features must be non-empty")
        self._features = tuple(features)
        self._label_engine = label_engine
        self._label_config = label_config
        self._train_schedule = tuple(
            sorted(_require_utc(t, field="train_schedule") for t in train_schedule)
        )

    def _build_dataset(
        self,
        universe: tuple[str, ...],
        decision_time: datetime,
        training: bool,
    ) -> tuple[np.ndarray, np.ndarray | None, list[str]]:
        """Build feature matrix X, target vector y, and instrument list.
        
        If `training` is True, evaluates over all valid historical dates in `train_schedule`
        where the label window is fully closed on or before `decision_time`.
        If `training` is False, evaluates features exactly at `decision_time` without labels.
        """
        X_rows: list[list[float]] = []
        y_rows: list[float] = []
        instruments_out: list[str] = []

        if training:
            valid_dates = [
                t
                for t in self._train_schedule
                if t + self._label_config.min_gap + self._label_config.horizon <= decision_time
            ]
            if not valid_dates:
                return np.array([]), np.array([]), []
            dates_to_compute = valid_dates
        else:
            dates_to_compute = [decision_time]

        for t in dates_to_compute:
            # Gather features for date t
            feature_frames = [f.compute(universe, t) for f in self._features]
            
            # Map instrument_id -> list of feature values
            feat_map: dict[str, list[float]] = {iid: [] for iid in universe}
            for frame in feature_frames:
                f_dict = {v.instrument_id: v.raw_value for v in frame.values}
                for iid in universe:
                    val = f_dict.get(iid)
                    if val is None or not math.isfinite(val):
                        feat_map[iid].append(float("nan"))
                    else:
                        feat_map[iid].append(val)

            # Gather labels for date t if training
            label_map: dict[str, float] = {}
            if training:
                events = self._label_engine.compute(universe, [t], self._label_config)
                for e in events:
                    if math.isfinite(float(e.label_value)):
                        label_map[str(e.instrument_id)] = float(e.label_value)

            for iid in universe:
                feats = feat_map[iid]
                if any(math.isnan(x) for x in feats):
                    continue # Drop rows with missing features
                
                if training:
                    lbl = label_map.get(iid)
                    if lbl is None:
                        continue # Drop rows with missing labels
                    X_rows.append(feats)
                    y_rows.append(lbl)
                else:
                    X_rows.append(feats)
                    instruments_out.append(iid)

        if not X_rows:
            return np.array([]), (np.array([]) if training else None), []

        X = np.array(X_rows, dtype=np.float64)
        y = np.array(y_rows, dtype=np.float64) if training else None
        return X, y, instruments_out

    def _fit_predict(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def compute(
        self,
        universe: Sequence[str],
        as_of: datetime,
    ) -> FactorFrame:
        decision_time = _require_utc(as_of, field="as_of")
        ordered = _normalize_universe(universe)

        # 1. Build training set
        X_train, y_train, _ = self._build_dataset(ordered, decision_time, training=True)
        if X_train.shape[0] < 5:
            # Insufficient training data: fail soft by returning empty frame
            return FactorFrame(
                values=(),
                factor_id=self.factor_id,
                factor_version=self.factor_version,
                decision_time=decision_time,
            )

        # 2. Build test set (current features)
        X_test, _, test_iids = self._build_dataset(ordered, decision_time, training=False)
        if X_test.shape[0] == 0:
            return FactorFrame(
                values=(),
                factor_id=self.factor_id,
                factor_version=self.factor_version,
                decision_time=decision_time,
            )

        # 3. Fit and predict
        assert y_train is not None  # training=True guarantees labels
        try:
            preds = self._fit_predict(X_train, y_train, X_test)
        except Exception as exc:
            raise MLFactorError(
                "model fit/predict failed",
                context={"error": str(exc), "decision_time": decision_time.isoformat()},
            ) from exc

        # 4. Construct FactorFrame
        values: list[FactorValue] = []
        for iid, pred in zip(test_iids, preds, strict=True):
            values.append(
                FactorValue(
                    instrument_id=iid,
                    decision_time=decision_time,
                    raw_value=float(pred),
                    score=float(pred),
                    availability_time=decision_time,
                    factor_id=self.factor_id,
                    factor_version=self.factor_version,
                )
            )

        return FactorFrame(
            values=tuple(values),
            factor_id=self.factor_id,
            factor_version=self.factor_version,
            decision_time=decision_time,
        )


class RidgeFactor(_MLFactorBase):
    """L2-regularized linear model."""

    factor_id = "ml_ridge"

    def __init__(
        self,
        features: Sequence[Factor],
        label_engine: LabelEngine,
        label_config: LabelConfig,
        train_schedule: Sequence[datetime],
        alpha: float = 1.0,
    ) -> None:
        super().__init__(features, label_engine, label_config, train_schedule)
        self.alpha = float(alpha)
        self._scaler = StandardScaler()
        self._model = Ridge(alpha=self.alpha, random_state=42)

    def _fit_predict(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
        X_train_s = self._scaler.fit_transform(X_train)
        X_test_s = self._scaler.transform(X_test)
        self._model.fit(X_train_s, y_train)
        return self._model.predict(X_test_s)  # type: ignore[no-any-return]


class ElasticNetFactor(_MLFactorBase):
    """L1+L2 regularized linear model."""

    factor_id = "ml_elasticnet"

    def __init__(
        self,
        features: Sequence[Factor],
        label_engine: LabelEngine,
        label_config: LabelConfig,
        train_schedule: Sequence[datetime],
        alpha: float = 1.0,
        l1_ratio: float = 0.5,
    ) -> None:
        super().__init__(features, label_engine, label_config, train_schedule)
        self.alpha = float(alpha)
        self.l1_ratio = float(l1_ratio)
        self._scaler = StandardScaler()
        self._model = ElasticNet(alpha=self.alpha, l1_ratio=self.l1_ratio, random_state=42)

    def _fit_predict(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
        X_train_s = self._scaler.fit_transform(X_train)
        X_test_s = self._scaler.transform(X_test)
        self._model.fit(X_train_s, y_train)
        return self._model.predict(X_test_s)  # type: ignore[no-any-return]


class XGBoostFactor(_MLFactorBase):
    """Shallow gradient-boosted tree."""

    factor_id = "ml_xgboost"

    def __init__(
        self,
        features: Sequence[Factor],
        label_engine: LabelEngine,
        label_config: LabelConfig,
        train_schedule: Sequence[datetime],
        max_depth: int = 3,
        n_estimators: int = 100,
        learning_rate: float = 0.1,
    ) -> None:
        super().__init__(features, label_engine, label_config, train_schedule)
        self.max_depth = int(max_depth)
        self.n_estimators = int(n_estimators)
        self.learning_rate = float(learning_rate)
        # XGBoost works without scaling
        self._model = XGBRegressor(
            max_depth=self.max_depth,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=42,
            n_jobs=1,  # Keep deterministic
        )

    def _fit_predict(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
        self._model.fit(X_train, y_train)
        return self._model.predict(X_test)  # type: ignore[no-any-return]
