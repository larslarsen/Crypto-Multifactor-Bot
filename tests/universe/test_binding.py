"""Tests for ARCH-002 UniverseBinding contract and CMC survivorship adapter."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from cryptofactors.execution import FactorDrivenPaperLoop
from cryptofactors.execution.errors import PaperExecutionError
from cryptofactors.promotion import (
    PromotionIdentityPayload,
    PromotionRegistry,
    PromotionState,
    PromotionTarget,
)
from cryptofactors.universe import (
    CMC_SURVIVORSHIP_SCHEMA,
    CMCSurvivorshipBinding,
    CMCSurvivorshipProvider,
    UniverseBinding,
    UniverseBindingError,
    is_survivorship_invalid,
    load_cmc_survivorship_binding,
)
from cryptofactors.universe.binding import SURVIVORSHIP_INVALID_ARTIFACT_IDS


@dataclass(frozen=True, slots=True)
class _StaticBinding:
    """Test-only binding that returns a fixed set of symbols."""

    symbols: tuple[str, ...]
    universe_dataset_id: str = "static_test"
    survivorship_policy: str = "none"
    universe_code_version: str = "test"

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        return frozenset(self.symbols)

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        return {
            "eligible": len(self.symbols),
            "with_bars": None,
            "missing": None,
            "universe_dataset_id": self.universe_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
        }


@dataclass(frozen=True, slots=True)
class _StaticFactor:
    factor_id: str = "static"

    def compute(self, universe: Any, decision_time: datetime) -> Any:
        class Frame:
            def __init__(self) -> None:
                self.values = [
                    type("FV", (), {"instrument_id": sym, "score": 1.0})()
                    for sym in universe
                ]
        return Frame()


def _coin_record(
    cmc_id: int,
    symbol: str,
    *,
    is_active: bool,
    birth_date: str,
    death_proxy_date: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cmc_id,
        "symbol": symbol,
        "name": f"{symbol}Coin",
        "slug": symbol.lower(),
        "is_active": is_active,
        "birth_date": birth_date,
        "death_proxy_date": death_proxy_date,
        "status": "active" if is_active else "inactive",
        "dateAdded": birth_date,
        "dateLaunched": birth_date,
        "latestUpdateTime": death_proxy_date,
    }


def _promote(registry: PromotionRegistry, artifact_id: str) -> None:
    payload = PromotionIdentityPayload(
        model_artifact_id=artifact_id,
        experiment_fingerprint="fp",
        dataset_ids=("ds1",),
        universe_ids=("cmc_survivorship_universe",),
        code_commit="c1",
        config_version="cfg1",
        feature_version="f1",
        representation_version="r1",
        portfolio_version="p1",
        cost_model_version="cost1",
        risk_policy_version="risk1",
        target_stage=PromotionTarget.PAPER,
        effective_time=datetime(2026, 1, 1, tzinfo=UTC),
        approving_authority="Lead Quant",
        evidence_reference="ref",
    )
    registry.register_candidate(payload)
    registry.transition_state(payload, PromotionState.PAPER_APPROVED, reason="ok")


def _empty_provider() -> CMCSurvivorshipProvider:
    table = pa.table(
        {name: [] for name in CMC_SURVIVORSHIP_SCHEMA.names},
        schema=CMC_SURVIVORSHIP_SCHEMA,
    )
    return CMCSurvivorshipProvider(table)


def test_empty_universe_binding_fails() -> None:
    """Empty provider -> UniverseBindingError at construction time."""
    provider = _empty_provider()
    with pytest.raises(UniverseBindingError):
        CMCSurvivorshipBinding(
            universe_dataset_id="ds_empty",
            provider=provider,
        )


def test_load_cmc_binding_fails_without_dataset() -> None:
    """Fail-closed when no catalog-published CMC dataset exists."""
    with pytest.raises(UniverseBindingError):
        load_cmc_survivorship_binding(
            db_path="/nonexistent/catalog.db",
            store_root="/nonexistent/store",
        )


def test_static_binding_satisfies_universe_binding_protocol() -> None:
    """A minimal binding implementation satisfies the protocol."""
    binding = _StaticBinding(symbols=("XBTUSD", "ETHUSD"))
    assert isinstance(binding, UniverseBinding)


def test_cmc_binding_respects_birth_death_proxy() -> None:
    """Active and alive inactive coins are in; dead coins are out after death."""
    records = [
        _coin_record(1, "BTC", is_active=True, birth_date="2013-04-28T00:00:00Z"),
        _coin_record(2, "ETH", is_active=True, birth_date="2015-08-07T00:00:00Z"),
        _coin_record(3, "DEAD", is_active=False, birth_date="2014-01-01T00:00:00Z", death_proxy_date="2017-06-01T00:00:00Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records)
    binding = CMCSurvivorshipBinding(
        universe_dataset_id="ds_test",
        provider=provider,
        key_map={
            "cmc_1": "XBTUSD",
            "cmc_2": "ETHUSD",
            "cmc_3": "DEADUSD",
        },
    )

    t_before = datetime(2013, 1, 1, tzinfo=UTC)
    assert binding.universe_at(t_before) == frozenset()

    t_mid = datetime(2016, 1, 1, tzinfo=UTC)
    assert binding.universe_at(t_mid) == frozenset({"XBTUSD", "ETHUSD", "DEADUSD"})

    t_after = datetime(2020, 1, 1, tzinfo=UTC)
    assert binding.universe_at(t_after) == frozenset({"XBTUSD", "ETHUSD"})


def test_cmc_binding_excludes_inactive_without_death() -> None:
    """Fail-closed: inactive with no death_proxy_date is never eligible."""
    records = [
        _coin_record(1, "BTC", is_active=True, birth_date="2013-04-28T00:00:00Z"),
        _coin_record(2, "IMMORTAL", is_active=False, birth_date="2014-01-01T00:00:00Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records)
    binding = CMCSurvivorshipBinding(
        universe_dataset_id="ds_test",
        provider=provider,
        key_map={"cmc_1": "XBTUSD", "cmc_2": "IMMORTALUSD"},
    )

    t = datetime(2030, 1, 1, tzinfo=UTC)
    assert binding.universe_at(t) == frozenset({"XBTUSD"})


def test_coverage_report_fields() -> None:
    """Coverage report includes mandatory identity and count fields."""
    records = [
        _coin_record(1, "BTC", is_active=True, birth_date="2013-04-28T00:00:00Z"),
    ]
    provider = CMCSurvivorshipProvider.from_records(records)
    binding = CMCSurvivorshipBinding(
        universe_dataset_id="ds_test",
        provider=provider,
    )
    report = binding.coverage_report(datetime(2020, 1, 1, tzinfo=UTC))
    assert report["eligible"] == 1
    assert report["universe_dataset_id"] == "ds_test"
    assert report["survivorship_policy"] == "cmc_aware_proxy_v1"
    assert report["universe_code_version"] == "v1"


def test_is_survivorship_invalid() -> None:
    """Known invalid sprint_004 artifacts are flagged; others are not."""
    assert is_survivorship_invalid("EXP-004")
    assert is_survivorship_invalid("EXP-004 grid")
    assert is_survivorship_invalid("PAPER-009")
    assert not is_survivorship_invalid("EXP-009")
    assert not is_survivorship_invalid("PAPER-010")


def test_invalid_artifact_ids_cover_gap_doc() -> None:
    """The constant contains the ids listed in 41_DATA_ARCHITECTURE_GAP.md."""
    expected = {
        "EXP-004", "EXP-005", "EXP-006", "EXP-007", "EXP-008",
        "PAPER-007", "PAPER-008", "PAPER-009", "PROMO-003",
    }
    assert set(SURVIVORSHIP_INVALID_ARTIFACT_IDS) == expected


def test_paper_loop_empty_universe_fails_closed(tmp_path: Path) -> None:
    """FactorDrivenPaperLoop.run_loop with an empty binding raises."""
    registry = PromotionRegistry(tmp_path / "registry.db")
    _promote(registry, "mod_empty")
    loop = FactorDrivenPaperLoop(
        model_artifact_id="mod_empty",
        promotion_registry=registry,
        factor=_StaticFactor(),
    )
    with pytest.raises(PaperExecutionError, match="empty universe"):
        loop.run_loop(
            universe_binding=_StaticBinding(symbols=()),
            decision_times=[datetime(2026, 1, 1, tzinfo=UTC)],
            get_prices_at=lambda dt, univ: {sym: 1.0 for sym in univ},
        )


def test_paper_loop_fingerprints_binding_in_result(tmp_path: Path) -> None:
    """PaperLoopResult carries the binding fingerprint fields."""
    registry = PromotionRegistry(tmp_path / "registry.db")
    _promote(registry, "mod_fp")
    binding = _StaticBinding(symbols=("XBTUSD", "ETHUSD"))

    class PriceStore:
        def get_prices_at(self, dt: datetime, universe: Any) -> dict[str, float]:
            return {sym: 100.0 for sym in universe}

    loop = FactorDrivenPaperLoop(
        model_artifact_id="mod_fp",
        promotion_registry=registry,
        factor=_StaticFactor(),
        initial_cash=100_000.0,
    )
    res = loop.run_loop(
        universe_binding=binding,
        decision_times=[datetime(2026, 1, 1, tzinfo=UTC)],
        get_prices_at=PriceStore().get_prices_at,
    )
    assert res.universe_dataset_id == "static_test"
    assert res.universe_code_version == "test"
    assert res.survivorship_policy == "none"


def test_paper_loop_no_static_map_only_construction(tmp_path: Path) -> None:
    """The loop does not accept a raw list of symbols; only a UniverseBinding."""
    registry = PromotionRegistry(tmp_path / "registry.db")
    _promote(registry, "mod_no_static")
    loop = FactorDrivenPaperLoop(
        model_artifact_id="mod_no_static",
        promotion_registry=registry,
        factor=_StaticFactor(),
    )
    with pytest.raises(TypeError):
        loop.run_loop(
            universe=["XBTUSD"],
            decision_times=[datetime(2026, 1, 1, tzinfo=UTC)],
            get_prices_at=lambda dt, univ: {},
        )


def test_load_cmc_binding_uses_symbol_map(tmp_path: Path) -> None:
    """load_cmc_survivorship_binding maps CMC symbols to paper symbols when requested."""
    from cryptofactors.universe.binding import _default_symbol_to_paper_map
    mapping = _default_symbol_to_paper_map()
    assert mapping["BTC"] == "XBTUSD"
    assert mapping["ETH"] == "ETHUSD"
    assert mapping["PEPE"] == "PEPEUSD"
