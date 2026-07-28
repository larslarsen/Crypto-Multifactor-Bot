#!/usr/bin/env python3
"""EXP-009 — Pre-registered tsmom_365_30 runner (signed REVIEW-0252).

Modes
-----
readiness   (default)
    Load the survivorship binding, verify the frozen 26-Friday holdout calendar,
    fingerprint coverage, and write a sealed artifact. Does **not** evaluate
    holdout returns.

exploratory
    Run the frozen factor on the contaminated exploration window
    (2020-01-01 → 2026-07-01). Verdict is always EXPLORATORY_ONLY — never ACCEPT.

holdout
    Open the real prospective holdout (2026-07-31 → 2027-01-22) only when all
    26 Friday decisions have bar coverage. Applies the stationary bootstrap and
    the pre-registered accept/reject rule. Refuses otherwise.

synthetic
    Exercise bootstrap + decision rule on caller-supplied or generated weekly
    returns without touching market data or the real holdout.

Writes ``research/sprint_004/42_EXP009_PREREGISTERED_TSMOM.json`` by default.
No LIVE. No parameter search.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import pyarrow as pa
import pyarrow.parquet as pq

from cryptofactors.catalog.dataset.catalog_store import SqliteDatasetCatalog
from cryptofactors.catalog.dataset.paths import lexical_join
from cryptofactors.execution.symbols import (
    PAPER_TO_INSTRUMENT_ID,
    PaperSymbolAsOfAdapter,
)
from cryptofactors.experiments.exp009 import (
    ARTIFACT_RELATIVE_PATH,
    BAR_PANEL_DATASET_ID,
    BOOTSTRAP_MEAN_BLOCK_LENGTH,
    BOOTSTRAP_N_RESAMPLES,
    BOOTSTRAP_SEED,
    EXPERIMENT_ID,
    HOLDOUT_START,
    MODEL_ARTIFACT_ID,
    UNIVERSE_DATASET_ID,
    EXP009Error,
    EXP009HoldoutNotReadyError,
    EXP009Mode,
    EXP009Runner,
    HypothesisVerdict,
    apply_decision_rule,
    assess_holdout_readiness,
    build_artifact,
    holdout_decision_times,
    require_signed_dataset_ids,
    run_readiness_checks,
    stationary_bootstrap_mean_pvalue,
    weekly_net_returns_from_period_logs,
)
from cryptofactors.promotion import PromotionRegistry
from cryptofactors.universe.binding import load_paper_universe_binding

_US_PER_SECOND = 1_000_000


class _InMemoryMarketBarStore:
    """In-memory market-bars as-of store over the DATA-011 daily partition."""

    def __init__(
        self,
        control_database: Path,
        dataset_store_root: Path,
        dataset_id: str,
        *,
        prefer_kind: str = "daily",
    ) -> None:
        self.control_database = Path(control_database)
        self.dataset_store_root = Path(dataset_store_root)
        self.dataset_id = dataset_id
        self.prefer_kind = prefer_kind
        self._df = self._load_bars()
        self.latest_bar_time = self._compute_latest_bar_time()

    def _dataset_file_paths(self) -> list[Path]:
        cat = SqliteDatasetCatalog(self.control_database)
        try:
            files = list(cat.list_files(self.dataset_id))
            ds_row = cat.get_dataset(self.dataset_id)
        finally:
            cat.close()

        root = self.dataset_store_root.expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root

        dataset_base = root
        if ds_row is not None:
            manifest_uri = str(ds_row.get("manifest_uri") or "")
            if manifest_uri:
                dataset_dir = str(Path(manifest_uri).parent)
                dataset_base = lexical_join(root, dataset_dir)

        paths: list[Path] = []
        for f in files:
            uri = str(f.get("storage_uri") or "")
            if not uri.endswith("bars.parquet"):
                continue
            if self.prefer_kind in uri:
                paths.append(lexical_join(dataset_base, uri))
        return paths

    def _load_bars(self) -> pd.DataFrame:
        paths = self._dataset_file_paths()
        if not paths:
            raise ValueError(
                f"No {self.prefer_kind} bars.parquet files for dataset {self.dataset_id}"
            )
        tables = [pq.read_table(path) for path in paths if path.exists()]
        if not tables:
            raise ValueError(f"No readable bar files for dataset {self.dataset_id}")
        table = pa.concat_tables(tables, promote_options="default")
        df = table.to_pandas()
        required = {"instrument_id", "period_start", "availability_time", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Dataset missing columns: {missing}")
        return df

    def _compute_latest_bar_time(self) -> datetime | None:
        """Latest bar *knowable* as-of time (BAR-001: availability_time).

        Uses ``max(availability_time)``, not ``period_start``. Under BAR-001
        availability is period_start + 1d, so feeding period_start into the
        holdout gate would open coverage roughly a day before the bar is
        knowable.
        """
        if self._df.empty:
            return None
        max_us = int(self._df["availability_time"].max())
        return datetime.fromtimestamp(max_us / _US_PER_SECOND, tz=UTC)

    def latest_available(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        max_age: Any = None,
    ) -> Any:
        if dataset_id != self.dataset_id:
            raise ValueError(f"This store only supports dataset {self.dataset_id}")
        t_us = int(_require_utc(decision_time).timestamp() * _US_PER_SECOND)
        key_set = {int(k) for k in keys}
        min_availability_us: int | None = None
        if max_age is not None:
            min_availability_us = t_us - int(max_age.total_seconds() * _US_PER_SECOND)

        df = self._df
        mask = (
            df["instrument_id"].isin(key_set)
            & (df["availability_time"] <= t_us)
            & (df["period_start"] <= t_us)
        )
        if min_availability_us is not None:
            mask &= df["availability_time"] >= min_availability_us
        eligible = df.loc[mask]
        if eligible.empty:
            return self._empty_table(fields)

        eligible = eligible.sort_values(
            ["instrument_id", "period_start", "availability_time"]
        )
        latest = eligible.groupby("instrument_id").tail(1)
        return self._project(latest, fields)

    def as_of(
        self,
        dataset_id: str,
        keys: Any,
        fields: Any,
        decision_time: datetime,
        knowledge_time: Any = None,
    ) -> Any:
        return self.latest_available(dataset_id, keys, fields, decision_time)

    def _project(self, df: pd.DataFrame, fields: Any) -> pa.Table:
        cols = [c for c in list(fields) if c in df.columns]
        if not cols:
            cols = ["instrument_id"]
        return pa.Table.from_pandas(df[cols])

    def _empty_table(self, fields: Any) -> pa.Table:
        cols = list(fields) if fields else ["instrument_id"]
        return pa.Table.from_arrays(
            [pa.array([], type=pa.null()) for _ in cols],
            names=cols,
        )


def _require_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(UTC)


def _write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"EXP-009 artifact written to {path}", file=sys.stderr)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EXP-009 pre-registered tsmom_365_30 runner",
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in EXP009Mode],
        default=EXP009Mode.READINESS.value,
        help="Operating mode (default: readiness — holdout sealed)",
    )
    parser.add_argument("--db-path", type=str, default="exp003.db")
    parser.add_argument("--store-root", type=str, default="data/exp003_store")
    parser.add_argument(
        "--dataset-id",
        type=str,
        default=BAR_PANEL_DATASET_ID,
        help=(
            "Must equal the signed DATA-011 pin "
            f"({BAR_PANEL_DATASET_ID}); overrides are rejected"
        ),
    )
    parser.add_argument(
        "--universe-dataset-id",
        type=str,
        default=UNIVERSE_DATASET_ID,
        help=(
            "Must equal the signed UNIVERSE-006 pin "
            f"({UNIVERSE_DATASET_ID}); overrides are rejected"
        ),
    )
    parser.add_argument(
        "--output",
        type=str,
        default=ARTIFACT_RELATIVE_PATH,
        help="Artifact JSON path",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=None,
        help=(
            "Synthetic mode only: override stationary-bootstrap RNG seed. "
            "Forbidden on holdout/exploratory (pre-registered seed is frozen)."
        ),
    )
    parser.add_argument(
        "--synthetic-mean",
        type=float,
        default=0.002,
        help="Synthetic mode: mean weekly return (default 0.2%%)",
    )
    parser.add_argument(
        "--synthetic-vol",
        type=float,
        default=0.03,
        help="Synthetic mode: weekly return volatility",
    )
    parser.add_argument(
        "--skip-binding",
        action="store_true",
        help="Readiness only: skip loading the live binding (calendar/bootstrap only)",
    )
    parser.add_argument(
        "--code-commit",
        type=str,
        default=None,
        help="Repository SHA for promotion identity (default: git rev-parse HEAD)",
    )
    return parser.parse_args(argv)


def _git_rev_parse_head() -> str:
    """Return ``git rev-parse HEAD`` output (strip). Patchable in tests."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()


def _resolve_code_commit(explicit: str | None) -> str:
    """Return a real repository SHA; never a ticket placeholder."""
    if explicit is not None and explicit.strip():
        return explicit.strip()
    try:
        out = _git_rev_parse_head()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise SystemExit(
            "EXP-009 requires --code-commit <sha> when git rev-parse HEAD is unavailable"
        ) from exc
    if not out:
        raise SystemExit("EXP-009: empty git HEAD; pass --code-commit <sha>")
    return out


def _require_signed_cli_dataset_ids(args: argparse.Namespace) -> None:
    """CLI dataset flags must match the signed pre-registration pins."""
    try:
        require_signed_dataset_ids(
            bar_panel_dataset_id=args.dataset_id,
            universe_dataset_id=args.universe_dataset_id,
        )
    except EXP009Error as exc:
        raise SystemExit(f"EXP-009: {exc}") from exc


def _run_readiness(args: argparse.Namespace) -> int:
    _require_signed_cli_dataset_ids(args)
    binding = None
    if not args.skip_binding:
        binding = load_paper_universe_binding(
            args.db_path,
            args.store_root,
            dataset_id=UNIVERSE_DATASET_ID,
            bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
        )
        print(
            f"EXP-009: binding loaded universe={binding.universe_dataset_id} "
            f"bar_panel={binding.bar_panel_dataset_id}",
            file=sys.stderr,
        )

    latest_bar: datetime | None = None
    if not args.skip_binding:
        try:
            store = _InMemoryMarketBarStore(
                Path(args.db_path),
                Path(args.store_root),
                BAR_PANEL_DATASET_ID,
                prefer_kind="daily",
            )
            latest_bar = store.latest_bar_time
            print(
                f"EXP-009: latest bar availability_time="
                f"{latest_bar.isoformat() if latest_bar else None}",
                file=sys.stderr,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"EXP-009: bar store probe skipped: {exc}", file=sys.stderr)

    report = run_readiness_checks(binding, latest_available_bar=latest_bar)
    calendar = holdout_decision_times()

    # Fingerprint series only for holdout decision times that already have bar
    # coverage. If none do (the usual pre-holdout case), leave the series empty
    # — still a valid sealed readiness artifact. Never fall back to a pre-lock
    # exploration Friday (that would pollute universe_binding_series).
    fingerprint_times: list[datetime] = []
    if binding is not None:
        for dt in calendar:
            cov = binding.coverage_report(dt)
            if int(cov.get("with_bars", 0)) > 0:
                fingerprint_times.append(dt)

    artifact = build_artifact(
        mode=EXP009Mode.READINESS,
        universe_binding=binding,
        readiness=report.holdout,
        decision_times=fingerprint_times or None,
        verdict=HypothesisVerdict.SEALED,
        control_database=str(args.db_path),
        dataset_store_root=str(args.store_root),
        extra={
            "readiness_checks": report.as_dict(),
            "note": (
                "Readiness / sealed artifact only. Real holdout evaluation is blocked "
                "until all 26 post-lock Friday decisions have bar coverage. "
                "No accept/reject verdict is produced in this mode."
            ),
        },
    )
    _write_artifact(Path(args.output), artifact)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "mode": "readiness",
        "holdout_ready": report.holdout.ready,
        "binding_ok": report.binding_ok,
        "verdict": HypothesisVerdict.SEALED.value,
        "output": args.output,
    }, indent=2))
    return 0


def _make_runner(
    args: argparse.Namespace,
    *,
    store: _InMemoryMarketBarStore,
    binding: Any,
) -> EXP009Runner:
    _require_signed_cli_dataset_ids(args)
    price_store = PaperSymbolAsOfAdapter(store)
    registry = PromotionRegistry(Path(args.db_path))
    dataset_id = BAR_PANEL_DATASET_ID

    def get_prices(dt: datetime, univ: Any) -> dict[str, float]:
        res: dict[str, float] = {}
        for sym in univ:
            int_key = PAPER_TO_INSTRUMENT_ID[sym]
            tbl = store.latest_available(dataset_id, [int_key], ["close"], dt)
            if tbl is not None and tbl.num_rows > 0:
                res[sym] = float(tbl.column("close")[0].as_py())
        return res

    # Bootstrap seed is part of the signed fingerprint; never override here.
    # Synthetic mode applies --bootstrap-seed only in _run_synthetic.
    return EXP009Runner(
        universe_binding=binding,
        promotion_registry=registry,
        as_of_store=price_store,
        get_prices_at=get_prices,
        code_commit=_resolve_code_commit(args.code_commit),
        bootstrap_seed=BOOTSTRAP_SEED,
    )


def _reject_bootstrap_seed_override(args: argparse.Namespace, mode: EXP009Mode) -> None:
    """Holdout/exploratory must use the frozen pre-registered bootstrap seed."""
    if args.bootstrap_seed is None:
        return
    if int(args.bootstrap_seed) == int(BOOTSTRAP_SEED):
        return
    raise SystemExit(
        f"EXP-009: --bootstrap-seed is frozen at {BOOTSTRAP_SEED} for mode={mode.value}; "
        "overrides are allowed only with --mode synthetic"
    )


def _run_exploratory(args: argparse.Namespace) -> int:
    _reject_bootstrap_seed_override(args, EXP009Mode.EXPLORATORY)
    _require_signed_cli_dataset_ids(args)
    binding = load_paper_universe_binding(
        args.db_path,
        args.store_root,
        dataset_id=UNIVERSE_DATASET_ID,
        bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
    )
    store = _InMemoryMarketBarStore(
        Path(args.db_path),
        Path(args.store_root),
        BAR_PANEL_DATASET_ID,
        prefer_kind="daily",
    )
    runner = _make_runner(args, store=store, binding=binding)
    result, times = runner.run_exploratory()
    readiness = assess_holdout_readiness(latest_available_bar=store.latest_bar_time)

    # Exploratory bootstrap is informational only and never drives ACCEPT.
    # Use signed module constants — runner no longer exposes bootstrap N/block fields.
    weekly = weekly_net_returns_from_period_logs(
        result.period_logs, initial_cash=result.initial_cash
    )
    bootstrap = None
    if weekly:
        bootstrap = stationary_bootstrap_mean_pvalue(
            weekly,
            n_resamples=BOOTSTRAP_N_RESAMPLES,
            mean_block_length=BOOTSTRAP_MEAN_BLOCK_LENGTH,
            seed=BOOTSTRAP_SEED,
        )

    artifact = build_artifact(
        mode=EXP009Mode.EXPLORATORY,
        universe_binding=binding,
        readiness=readiness,
        session_result=result,
        decision_times=times,
        bootstrap=bootstrap,
        decision_rule=None,
        verdict=HypothesisVerdict.EXPLORATORY_ONLY,
        control_database=str(args.db_path),
        dataset_store_root=str(args.store_root),
        extra={
            "note": (
                "Exploratory run on the contaminated pre-lock window only. "
                "Results must not accept the hypothesis, tune parameters, or "
                "justify promotion. Holdout remains sealed."
            ),
        },
    )
    _write_artifact(Path(args.output), artifact)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "mode": "exploratory",
        "decision_count": len(result.period_logs),
        "total_net_return": result.total_net_return,
        "verdict": HypothesisVerdict.EXPLORATORY_ONLY.value,
        "output": args.output,
    }, indent=2))
    return 0


def _run_holdout(args: argparse.Namespace) -> int:
    _reject_bootstrap_seed_override(args, EXP009Mode.HOLDOUT)
    _require_signed_cli_dataset_ids(args)
    binding = load_paper_universe_binding(
        args.db_path,
        args.store_root,
        dataset_id=UNIVERSE_DATASET_ID,
        bar_panel_dataset_id=BAR_PANEL_DATASET_ID,
    )
    store = _InMemoryMarketBarStore(
        Path(args.db_path),
        Path(args.store_root),
        BAR_PANEL_DATASET_ID,
        prefer_kind="daily",
    )
    readiness = assess_holdout_readiness(latest_available_bar=store.latest_bar_time)
    if not readiness.ready:
        # Write a sealed artifact documenting the gate failure, then exit non-zero.
        artifact = build_artifact(
            mode=EXP009Mode.HOLDOUT,
            universe_binding=binding,
            readiness=readiness,
            verdict=HypothesisVerdict.SEALED,
            control_database=str(args.db_path),
            dataset_store_root=str(args.store_root),
            extra={
                "note": (
                    "Holdout evaluation refused: not all 26 post-lock Friday decisions "
                    "have bar coverage. Artifact is sealed (verdict=SEALED)."
                ),
            },
        )
        _write_artifact(Path(args.output), artifact)
        print(readiness.reason, file=sys.stderr)
        return 2

    runner = _make_runner(args, store=store, binding=binding)
    try:
        result, evaluation, readiness = runner.run_holdout(
            latest_available_bar=store.latest_bar_time,
        )
    except EXP009HoldoutNotReadyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    artifact = build_artifact(
        mode=EXP009Mode.HOLDOUT,
        universe_binding=binding,
        readiness=readiness,
        session_result=result,
        decision_times=holdout_decision_times(),
        bootstrap=evaluation["bootstrap"],
        decision_rule=evaluation["decision_rule"],
        verdict=evaluation["verdict"],
        control_database=str(args.db_path),
        dataset_store_root=str(args.store_root),
        extra={
            "weekly_net_returns": evaluation["weekly_net_returns"],
            "note": (
                "Prospective holdout evaluation under the signed EXP-009 pre-registration. "
                "ACCEPT requires total_net_return >= +0.02 AND p <= 0.05; otherwise REJECT "
                "and archive. No post-hoc rescue."
            ),
        },
    )
    _write_artifact(Path(args.output), artifact)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "mode": "holdout",
        "model_artifact_id": MODEL_ARTIFACT_ID,
        "decision_count": len(result.period_logs),
        "total_net_return": result.total_net_return,
        "p_value": evaluation["bootstrap"]["p_value"],
        "verdict": evaluation["verdict"],
        "output": args.output,
    }, indent=2))
    return 0


def _run_synthetic(args: argparse.Namespace) -> int:
    """Bootstrap + decision-rule smoke path without market data or holdout open."""
    import numpy as np

    # Synthetic plumbing only — seed override is permitted here.
    seed = int(args.bootstrap_seed) if args.bootstrap_seed is not None else int(BOOTSTRAP_SEED)
    rng = np.random.default_rng(seed)
    n = 26
    weekly = rng.normal(loc=args.synthetic_mean, scale=args.synthetic_vol, size=n)
    # Convert to simple returns already; total net return as cumulative product - 1.
    total = float(np.prod(1.0 + weekly) - 1.0)
    bootstrap = stationary_bootstrap_mean_pvalue(
        weekly.tolist(),
        seed=seed,
    )
    decision = apply_decision_rule(total, float(bootstrap["p_value"]))
    readiness = assess_holdout_readiness()  # sealed by construction

    artifact = build_artifact(
        mode=EXP009Mode.SYNTHETIC,
        universe_binding=None,
        readiness=readiness,
        bootstrap=bootstrap,
        decision_rule=decision,
        # Synthetic never authorizes a real accept of the economic hypothesis.
        verdict=HypothesisVerdict.EXPLORATORY_ONLY,
        control_database=None,
        dataset_store_root=None,
        extra={
            "synthetic": {
                "n_periods": n,
                "mean_weekly": args.synthetic_mean,
                "vol_weekly": args.synthetic_vol,
                "total_net_return": total,
                "weekly_net_returns": weekly.tolist(),
            },
            "note": (
                "Synthetic path for bootstrap/decision-rule plumbing only. "
                "Does not open the real holdout and cannot accept the hypothesis."
            ),
        },
    )
    # Synthetic artifact still declares the pinned ids from pre-registration.
    assert artifact["survivorship_invalid"] is False
    assert artifact["bar_panel_dataset_id"] == BAR_PANEL_DATASET_ID
    assert artifact["universe_dataset_id"] == UNIVERSE_DATASET_ID

    _write_artifact(Path(args.output), artifact)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "mode": "synthetic",
        "total_net_return": total,
        "p_value": bootstrap["p_value"],
        "decision_rule_verdict": decision["verdict"],
        "artifact_verdict": HypothesisVerdict.EXPLORATORY_ONLY.value,
        "holdout_ready": readiness.ready,
        "output": args.output,
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mode = EXP009Mode(args.mode)
    print(
        f"EXP-009 mode={mode.value} model={MODEL_ARTIFACT_ID} "
        f"holdout_start={HOLDOUT_START.date()}",
        file=sys.stderr,
    )
    try:
        if mode is EXP009Mode.READINESS:
            return _run_readiness(args)
        if mode is EXP009Mode.EXPLORATORY:
            return _run_exploratory(args)
        if mode is EXP009Mode.HOLDOUT:
            return _run_holdout(args)
        if mode is EXP009Mode.SYNTHETIC:
            return _run_synthetic(args)
        raise EXP009Error(f"unknown mode: {mode}")
    except EXP009HoldoutNotReadyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except EXP009Error as exc:
        print(f"EXP-009 error: {exc}", file=sys.stderr)
        return 1
    except (ValueError, OSError, RuntimeError) as exc:
        # Store/catalog failures (e.g. missing bars) must not dump a raw traceback.
        print(f"EXP-009 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
