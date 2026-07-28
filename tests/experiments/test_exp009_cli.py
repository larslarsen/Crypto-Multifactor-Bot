"""EXP-009 CLI script coverage (mode dispatch, sealed exit, code commit)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "research"
    / "run_exp009_preregistered_tsmom.py"
)


def _load_cli():
    spec = importlib.util.spec_from_file_location("run_exp009_cli", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


cli = _load_cli()


def test_resolve_code_commit_explicit() -> None:
    assert cli._resolve_code_commit("deadbeefcafebabe") == "deadbeefcafebabe"
    assert cli._resolve_code_commit("  abcdef0  ") == "abcdef0"


def test_resolve_code_commit_from_git() -> None:
    # Patch the script-local helper, not stdlib subprocess (xdist-safe).
    with patch.object(cli, "_git_rev_parse_head", return_value="abc1234"):
        assert cli._resolve_code_commit(None) == "abc1234"


def test_resolve_code_commit_fails_without_git() -> None:
    with patch.object(
        cli,
        "_git_rev_parse_head",
        side_effect=cli.subprocess.CalledProcessError(1, "git"),
    ):
        with pytest.raises(SystemExit, match="--code-commit"):
            cli._resolve_code_commit(None)


def test_reject_bootstrap_seed_override_blocks_holdout() -> None:
    args = SimpleNamespace(bootstrap_seed=999)
    with pytest.raises(SystemExit, match="bootstrap-seed is frozen"):
        cli._reject_bootstrap_seed_override(args, cli.EXP009Mode.HOLDOUT)


def test_reject_bootstrap_seed_override_allows_frozen_value() -> None:
    args = SimpleNamespace(bootstrap_seed=cli.BOOTSTRAP_SEED)
    cli._reject_bootstrap_seed_override(args, cli.EXP009Mode.HOLDOUT)  # no raise


def test_main_synthetic_mode_dispatch(tmp_path: Path) -> None:
    out = tmp_path / "synth.json"
    code = cli.main(
        [
            "--mode",
            "synthetic",
            "--output",
            str(out),
            "--bootstrap-seed",
            "42",
        ]
    )
    assert code == 0
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "EXP-009" in text
    assert "EXPLORATORY_ONLY" in text


def test_main_holdout_sealed_returns_exit_2(tmp_path: Path) -> None:
    """Sealed holdout path: gate not open → exit 2 (no real evaluation)."""
    out = tmp_path / "holdout_sealed.json"

    # Avoid loading real catalogs/bars: force readiness sealed and skip store work
    # by failing early at binding load with a controlled path that still hits
    # the sealed early-return after readiness assessment.
    sealed = cli.assess_holdout_readiness()  # no coverage → sealed
    assert sealed.ready is False

    mock_binding = MagicMock()
    mock_binding.universe_dataset_id = cli.UNIVERSE_DATASET_ID
    mock_binding.bar_panel_dataset_id = cli.BAR_PANEL_DATASET_ID
    mock_binding.survivorship_policy = "quality_bar_panel_minus_cmc_dead_v1"
    mock_binding.universe_code_version = "v3"

    mock_store = MagicMock()
    mock_store.latest_bar_time = None

    with (
        patch.object(cli, "load_paper_universe_binding", return_value=mock_binding),
        patch.object(cli, "_InMemoryMarketBarStore", return_value=mock_store),
        patch.object(cli, "assess_holdout_readiness", return_value=sealed),
    ):
        code = cli.main(
            [
                "--mode",
                "holdout",
                "--output",
                str(out),
            ]
        )
    assert code == 2
    assert out.is_file()
    assert "SEALED" in out.read_text(encoding="utf-8")


def test_main_catches_value_error_from_store(tmp_path: Path) -> None:
    """Store/catalog ValueError must exit 1 without escaping as an uncaught traceback."""
    out = tmp_path / "err.json"

    with patch.object(
        cli,
        "load_paper_universe_binding",
        side_effect=ValueError("No readable bar files"),
    ):
        code = cli.main(
            [
                "--mode",
                "holdout",
                "--output",
                str(out),
            ]
        )
    assert code == 1


def test_cli_rejects_dataset_id_override() -> None:
    with pytest.raises(SystemExit, match="DATA-011|frozen|signed"):
        cli._require_signed_cli_dataset_ids(
            SimpleNamespace(
                dataset_id="ds_not_signed",
                universe_dataset_id=cli.UNIVERSE_DATASET_ID,
            )
        )
    with pytest.raises(SystemExit, match="UNIVERSE-006|frozen|signed"):
        cli._require_signed_cli_dataset_ids(
            SimpleNamespace(
                dataset_id=cli.BAR_PANEL_DATASET_ID,
                universe_dataset_id="ds_not_signed",
            )
        )


def test_compute_latest_bar_time_uses_availability_not_period_start() -> None:
    """Gate input is knowable time (availability), not period_start."""
    import pandas as pd

    store = object.__new__(cli._InMemoryMarketBarStore)
    # period_start day 0; availability day 1 (BAR-001 +1d) — max availability wins.
    store._df = pd.DataFrame(
        {
            "period_start": [1_000_000, 2_000_000],  # 1s, 2s epoch us
            "availability_time": [86_400_000_000, 172_800_000_000],  # +1d, +2d us
        }
    )
    latest = cli._InMemoryMarketBarStore._compute_latest_bar_time(store)
    assert latest is not None
    # max availability_time = 172800 seconds from epoch
    assert int(latest.timestamp()) == 172_800


def test_run_readiness_empty_series_when_no_holdout_coverage(tmp_path: Path) -> None:
    """Regression: never fall back to a pre-lock exploration Friday in the series.

    When every holdout Friday has with_bars == 0, universe_binding_series must
    be empty — re-adding the old exploration-date fallback would put a
    2026-06 Friday into the readiness artifact.
    """
    import json

    out = tmp_path / "readiness.json"
    mock_binding = MagicMock()
    mock_binding.universe_dataset_id = cli.UNIVERSE_DATASET_ID
    mock_binding.bar_panel_dataset_id = cli.BAR_PANEL_DATASET_ID
    mock_binding.survivorship_policy = "quality_bar_panel_minus_cmc_dead_v1"
    mock_binding.universe_code_version = "v3"
    mock_binding.coverage_report.return_value = {
        "with_bars": 0,
        "eligible": 0,
        "excluded_dead": 0,
        "panel": 22,
        "missing": [],
        "decision_time": "2026-07-31T00:00:00+00:00",
        "universe_dataset_id": cli.UNIVERSE_DATASET_ID,
        "bar_panel_dataset_id": cli.BAR_PANEL_DATASET_ID,
        "survivorship_policy": "quality_bar_panel_minus_cmc_dead_v1",
        "universe_code_version": "v3",
    }

    mock_store = MagicMock()
    mock_store.latest_bar_time = None

    sealed = cli.assess_holdout_readiness()
    assert sealed.ready is False

    args = cli._parse_args(
        [
            "--mode",
            "readiness",
            "--output",
            str(out),
            "--db-path",
            "exp003.db",
            "--store-root",
            "data/exp003_store",
        ]
    )

    report = SimpleNamespace(
        holdout=sealed,
        binding_ok=True,
        as_dict=lambda: {"holdout": sealed.as_dict(), "binding_ok": True},
    )
    with (
        patch.object(cli, "load_paper_universe_binding", return_value=mock_binding),
        patch.object(cli, "_InMemoryMarketBarStore", return_value=mock_store),
        patch.object(cli, "run_readiness_checks", return_value=report),
    ):
        code = cli._run_readiness(args)

    assert code == 0
    assert out.is_file()
    artifact = json.loads(out.read_text(encoding="utf-8"))
    series = artifact.get("universe_binding_series")
    assert series == []
    # Must not be a one-entry pre-lock exploration Friday.
    assert len(series) == 0
    # coverage_report consulted for holdout calendar only (26 Fridays), never
    # a fallback exploration date after the empty scan.
    assert mock_binding.coverage_report.call_count == 26
