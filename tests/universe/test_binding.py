"""Tests for the ARCH-002 UniverseBinding contract.

Membership semantics under ADR-0014 and REVIEW-0249:

    universe(t) = quality_bar_panel_with_coverage(t)  minus  cmc_dead(t)

The CMC dataset is a dead-coin graveyard used only to *exclude*. It is never the
source of membership, and no static symbol map may supply the panel.
"""

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
    CMCSurvivorshipProvider,
    PaperPanelSurvivorshipBinding,
    QualityBarPanel,
    UniverseBinding,
    UniverseBindingError,
    is_survivorship_invalid,
    load_paper_universe_binding,
    load_quality_bar_panel,
)
from cryptofactors.universe.binding import (
    DATA011_QUALITY_BAR_PANEL_DATASET_ID,
    PAPER_PANEL_SURVIVORSHIP_POLICY,
    SURVIVORSHIP_INVALID_ARTIFACT_IDS,
    UNIVERSE_BINDING_CODE_VERSION,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_DB = REPO_ROOT / "exp003.db"
STORE_ROOT = REPO_ROOT / "data" / "exp003_store"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class _StaticBinding:
    """Test-only binding that returns a fixed set of symbols."""

    symbols: tuple[str, ...]
    universe_dataset_id: str = "static_test"
    bar_panel_dataset_id: str = "static_bar_panel"
    survivorship_policy: str = "none"
    universe_code_version: str = "test"

    def universe_at(self, decision_time: datetime) -> frozenset[str]:
        return frozenset(self.symbols)

    def coverage_report(self, decision_time: datetime) -> dict[str, Any]:
        return {
            "eligible": len(self.symbols),
            "with_bars": len(self.symbols),
            "missing": [],
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
        }

    def binding_fingerprint(self, decision_time: datetime) -> dict[str, Any]:
        return {
            "universe_dataset_id": self.universe_dataset_id,
            "bar_panel_dataset_id": self.bar_panel_dataset_id,
            "survivorship_policy": self.survivorship_policy,
            "universe_code_version": self.universe_code_version,
            "decision_time": decision_time.isoformat(),
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
    name: str,
    *,
    is_active: bool,
    birth_date: str,
    death_proxy_date: str | None = None,
) -> dict[str, Any]:
    return {
        "id": cmc_id,
        "symbol": symbol,
        "name": name,
        "slug": symbol.lower(),
        "is_active": is_active,
        "birth_date": birth_date,
        "death_proxy_date": death_proxy_date,
        "status": "active" if is_active else "inactive",
        "dateAdded": birth_date,
        "dateLaunched": birth_date,
        "latestUpdateTime": death_proxy_date,
    }


def _panel(*symbols: str, first: str = "2019-01-01", last: str = "2026-07-01") -> QualityBarPanel:
    f = datetime.fromisoformat(first).replace(tzinfo=UTC)
    lst = datetime.fromisoformat(last).replace(tzinfo=UTC)
    return QualityBarPanel(
        dataset_id="ds_test_panel",
        symbols=frozenset(symbols),
        first_bar_at=dict.fromkeys(symbols, f),
        last_bar_at=dict.fromkeys(symbols, lst),
    )


def _binding(
    panel: QualityBarPanel,
    records: list[dict[str, Any]],
    base_to_name: dict[str, str] | None = None,
) -> PaperPanelSurvivorshipBinding:
    from cryptofactors.universe.binding import PAPER_BASE_TO_NAME

    return PaperPanelSurvivorshipBinding(
        universe_dataset_id="ds_test_universe",
        bar_panel_dataset_id=panel.dataset_id,
        provider=CMCSurvivorshipProvider.from_records(records),
        panel=panel,
        base_to_name=base_to_name or PAPER_BASE_TO_NAME,
    )


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


_ALIVE = [
    _coin_record(1, "BTC", "Bitcoin", is_active=True, birth_date="2013-04-28T00:00:00Z"),
    _coin_record(2, "ETH", "Ethereum", is_active=True, birth_date="2015-08-07T00:00:00Z"),
]


# --------------------------------------------------------------------------- #
# membership semantics — the inverted-semantics defect from REVIEW-0217
# --------------------------------------------------------------------------- #

class TestMembershipSemantics:
    def test_membership_is_the_panel_not_the_dead_list(self) -> None:
        """Liquid names are absent from the graveyard yet must be members.

        Under the old dead-list-as-membership semantics this returned empty.
        """
        binding = _binding(_panel("XBTUSD", "ETHUSD"), _ALIVE)
        assert binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC)) == frozenset(
            {"XBTUSD", "ETHUSD"}
        )

    def test_a_dead_name_leaves_the_panel_after_death(self) -> None:
        records = [
            _ALIVE[0],
            _coin_record(
                2, "ETH", "Ethereum", is_active=False,
                birth_date="2015-08-07T00:00:00Z",
                death_proxy_date="2020-06-01T00:00:00Z",
            ),
        ]
        binding = _binding(_panel("XBTUSD", "ETHUSD"), records)
        before = binding.universe_at(datetime(2019, 1, 1, tzinfo=UTC))
        after = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert "ETHUSD" in before, "must be a member while alive"
        assert "ETHUSD" not in after, "must leave after its death proxy date"
        assert "XBTUSD" in after

    def test_a_ticker_collision_does_not_falsely_exclude(self) -> None:
        """SOL/UNI/CRV/OP collide with dead micro-caps sharing the ticker.

        Matching on symbol alone removes real liquid names from the panel; the
        join must also agree on the coin name.
        """
        records = [
            *_ALIVE,
            _coin_record(
                999, "SOL", "Sola Token", is_active=False,
                birth_date="2014-01-01T00:00:00Z",
                death_proxy_date="2018-01-01T00:00:00Z",
            ),
        ]
        binding = _binding(_panel("XBTUSD", "SOLUSD"), records)
        assert "SOLUSD" in binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))

    def test_the_matching_name_still_excludes(self) -> None:
        """Counterpart: a dead record whose name matches must exclude."""
        records = [
            *_ALIVE,
            _coin_record(
                5426, "SOL", "Solana", is_active=False,
                birth_date="2020-04-10T00:00:00Z",
                death_proxy_date="2022-01-01T00:00:00Z",
            ),
        ]
        binding = _binding(_panel("XBTUSD", "SOLUSD"), records)
        assert "SOLUSD" not in binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))

    def test_no_raw_cmc_identity_can_leak(self) -> None:
        binding = _binding(_panel("XBTUSD", "ETHUSD"), _ALIVE)
        universe = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert not [s for s in universe if s.lower().startswith("cmc_")]


# --------------------------------------------------------------------------- #
# as-of coverage
# --------------------------------------------------------------------------- #

class TestAsOfCoverage:
    def test_a_symbol_without_bars_yet_is_not_a_member(self) -> None:
        """Listing later than t means no price history to score at t."""
        panel = QualityBarPanel(
            dataset_id="ds_test_panel",
            symbols=frozenset({"XBTUSD", "ARBUSD"}),
            first_bar_at={
                "XBTUSD": datetime(2019, 1, 1, tzinfo=UTC),
                "ARBUSD": datetime(2023, 3, 23, tzinfo=UTC),
            },
            last_bar_at=dict.fromkeys(
                ("XBTUSD", "ARBUSD"), datetime(2026, 7, 1, tzinfo=UTC)
            ),
        )
        binding = _binding(panel, _ALIVE)
        early = binding.universe_at(datetime(2020, 1, 1, tzinfo=UTC))
        late = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert "ARBUSD" not in early
        assert "ARBUSD" in late

    def test_a_decision_time_beyond_coverage_fails_closed(self) -> None:
        binding = _binding(_panel("XBTUSD", "ETHUSD"), _ALIVE)
        with pytest.raises(UniverseBindingError, match="no as-of coverage"):
            binding.universe_at(datetime(2030, 1, 1, tzinfo=UTC))

    def test_a_decision_time_before_coverage_fails_closed(self) -> None:
        binding = _binding(_panel("XBTUSD", "ETHUSD"), _ALIVE)
        with pytest.raises(UniverseBindingError, match="no as-of coverage"):
            binding.universe_at(datetime(2010, 1, 1, tzinfo=UTC))

    def test_an_all_dead_panel_fails_closed(self) -> None:
        records = [
            _coin_record(
                1, "BTC", "Bitcoin", is_active=False,
                birth_date="2013-04-28T00:00:00Z",
                death_proxy_date="2020-01-01T00:00:00Z",
            ),
        ]
        binding = _binding(_panel("XBTUSD"), records)
        with pytest.raises(UniverseBindingError, match="empty after survivorship"):
            binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))


# --------------------------------------------------------------------------- #
# fail-closed construction
# --------------------------------------------------------------------------- #

class TestFailClosedConstruction:
    def test_an_empty_panel_is_refused(self) -> None:
        with pytest.raises(UniverseBindingError, match="non-empty panel"):
            _binding(_panel(), _ALIVE)

    def test_an_empty_provider_is_refused(self) -> None:
        with pytest.raises(UniverseBindingError, match="empty provider"):
            PaperPanelSurvivorshipBinding(
                universe_dataset_id="ds",
                bar_panel_dataset_id="ds_bars",
                provider=_empty_provider(),
                panel=_panel("XBTUSD"),
                base_to_name={},
            )

    def test_a_missing_catalog_fails_closed(self) -> None:
        with pytest.raises(UniverseBindingError):
            load_paper_universe_binding(
                db_path="/nonexistent/catalog.db",
                store_root="/nonexistent/store",
            )

    def test_a_missing_bar_panel_fails_closed(self) -> None:
        with pytest.raises(UniverseBindingError):
            load_quality_bar_panel(
                db_path="/nonexistent/catalog.db",
                store_root="/nonexistent/store",
            )

    def test_there_is_no_caller_supplied_panel_override(self) -> None:
        """A `panel=` argument would reinstate static-map membership."""
        import inspect

        params = inspect.signature(load_paper_universe_binding).parameters
        assert "panel" not in params

    def test_no_static_membership_constant_remains(self) -> None:
        """PAPER_PANEL_SYMBOLS was the static-map fallback and must be gone."""
        import cryptofactors.universe as universe_pkg
        import cryptofactors.universe.binding as binding_mod

        assert not hasattr(binding_mod, "PAPER_PANEL_SYMBOLS")
        assert not hasattr(universe_pkg, "PAPER_PANEL_SYMBOLS")

    def test_the_dead_list_membership_binding_is_gone(self) -> None:
        """CMCSurvivorshipBinding treated the graveyard as the universe."""
        import cryptofactors.universe.binding as binding_mod

        assert not hasattr(binding_mod, "CMCSurvivorshipBinding")
        assert not hasattr(binding_mod, "load_cmc_survivorship_binding")


# --------------------------------------------------------------------------- #
# fingerprint
# --------------------------------------------------------------------------- #

class TestFingerprint:
    def test_the_fingerprint_binds_both_dataset_identities(self) -> None:
        """The universe id alone does not reproduce membership."""
        binding = _binding(_panel("XBTUSD", "ETHUSD"), _ALIVE)
        fp = binding.binding_fingerprint(datetime(2024, 1, 1, tzinfo=UTC))
        assert fp["universe_dataset_id"] == "ds_test_universe"
        assert fp["bar_panel_dataset_id"] == "ds_test_panel"
        assert fp["survivorship_policy"] == PAPER_PANEL_SURVIVORSHIP_POLICY
        assert fp["universe_code_version"] == UNIVERSE_BINDING_CODE_VERSION
        assert fp["decision_time"] == "2024-01-01T00:00:00+00:00"
        assert fp["eligible_count"] == 2
        assert fp["panel_count"] == 2

    def test_the_policy_version_was_bumped_for_this_semantic_change(self) -> None:
        assert UNIVERSE_BINDING_CODE_VERSION == "v3"
        assert PAPER_PANEL_SURVIVORSHIP_POLICY == "quality_bar_panel_minus_cmc_dead_v1"

    def test_the_coverage_report_names_the_missing_symbols(self) -> None:
        panel = QualityBarPanel(
            dataset_id="ds_test_panel",
            symbols=frozenset({"XBTUSD", "ARBUSD"}),
            first_bar_at={
                "XBTUSD": datetime(2019, 1, 1, tzinfo=UTC),
                "ARBUSD": datetime(2023, 3, 23, tzinfo=UTC),
            },
            last_bar_at=dict.fromkeys(
                ("XBTUSD", "ARBUSD"), datetime(2026, 7, 1, tzinfo=UTC)
            ),
        )
        report = _binding(panel, _ALIVE).coverage_report(datetime(2020, 1, 1, tzinfo=UTC))
        assert report["missing"] == ["ARBUSD"]
        assert report["with_bars"] == 1
        assert report["panel"] == 2
        assert report["bar_panel_dataset_id"] == "ds_test_panel"


# --------------------------------------------------------------------------- #
# protocol + paper loop wiring
# --------------------------------------------------------------------------- #

class TestPaperLoopWiring:
    def test_a_minimal_binding_satisfies_the_protocol(self) -> None:
        assert isinstance(_StaticBinding(symbols=("XBTUSD",)), UniverseBinding)

    def test_the_real_binding_satisfies_the_protocol(self) -> None:
        assert isinstance(_binding(_panel("XBTUSD"), _ALIVE), UniverseBinding)

    def test_an_empty_universe_fails_the_loop_closed(self, tmp_path: Path) -> None:
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

    def test_the_result_carries_both_dataset_identities(self, tmp_path: Path) -> None:
        registry = PromotionRegistry(tmp_path / "registry.db")
        _promote(registry, "mod_fp")
        loop = FactorDrivenPaperLoop(
            model_artifact_id="mod_fp",
            promotion_registry=registry,
            factor=_StaticFactor(),
        )
        res = loop.run_loop(
            universe_binding=_StaticBinding(symbols=("XBTUSD", "ETHUSD")),
            decision_times=[datetime(2026, 1, 1, tzinfo=UTC)],
            get_prices_at=lambda dt, univ: dict.fromkeys(univ, 100.0),
        )
        assert res.universe_dataset_id == "static_test"
        assert res.bar_panel_dataset_id == "static_bar_panel"
        assert res.universe_code_version == "test"
        assert res.survivorship_policy == "none"

    def test_the_loop_refuses_a_raw_symbol_list(self, tmp_path: Path) -> None:
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


# --------------------------------------------------------------------------- #
# invalidation helper (preserved from the accepted surface)
# --------------------------------------------------------------------------- #

class TestInvalidationHelper:
    def test_known_invalid_artifacts_are_flagged(self) -> None:
        assert is_survivorship_invalid("EXP-004")
        assert is_survivorship_invalid("EXP-004 grid")
        assert is_survivorship_invalid("PAPER-009")
        assert not is_survivorship_invalid("EXP-009")
        assert not is_survivorship_invalid("PAPER-010")

    def test_the_constant_covers_the_gap_doc(self) -> None:
        assert set(SURVIVORSHIP_INVALID_ARTIFACT_IDS) == {
            "EXP-004", "EXP-005", "EXP-006", "EXP-007", "EXP-008",
            "PAPER-007", "PAPER-008", "PAPER-009", "PROMO-003",
        }


# --------------------------------------------------------------------------- #
# REVIEW-0249 item 6 — proof against the real accepted catalog artifacts
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(
    not CATALOG_DB.exists() or not STORE_ROOT.exists(),
    reason="real catalog not present in this checkout",
)
class TestRealCatalogIntegration:
    """Unit tests use synthetic providers; REVIEW-0217 item 3 required real proof."""

    def test_the_real_binding_loads_from_the_accepted_artifacts(self) -> None:
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        assert binding.bar_panel_dataset_id == DATA011_QUALITY_BAR_PANEL_DATASET_ID
        assert binding.universe_dataset_id.startswith("ds_")
        assert len(binding.panel.symbols) > 0

    def test_liquid_panel_names_remain_present(self) -> None:
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        universe = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert {"XBTUSD", "ETHUSD"} <= universe

    def test_recent_membership_is_non_empty(self) -> None:
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        assert len(binding.universe_at(datetime(2026, 6, 1, tzinfo=UTC))) > 0

    def test_membership_grows_as_names_list(self) -> None:
        """Genuine as-of behaviour: fewer names existed in 2020 than in 2024."""
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        early = binding.universe_at(datetime(2020, 6, 1, tzinfo=UTC))
        late = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert len(early) < len(late)
        assert early <= late

    def test_no_raw_identity_leaks_from_the_real_path(self) -> None:
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        universe = binding.universe_at(datetime(2024, 1, 1, tzinfo=UTC))
        assert not [s for s in universe if s.lower().startswith("cmc_")]

    def test_the_real_path_fails_closed_outside_coverage(self) -> None:
        binding = load_paper_universe_binding(CATALOG_DB, STORE_ROOT)
        with pytest.raises(UniverseBindingError, match="no as-of coverage"):
            binding.universe_at(datetime(2030, 1, 1, tzinfo=UTC))

    def test_the_panel_is_bar_derived_not_translation_map_derived(self) -> None:
        """DOGEUSD is in the translation map but has no DATA-011 bars.

        Its absence proves membership comes from published bars rather than
        from PAPER_TO_INSTRUMENT_ID.
        """
        from cryptofactors.execution.symbols import PAPER_TO_INSTRUMENT_ID

        panel = load_quality_bar_panel(CATALOG_DB, STORE_ROOT)
        assert "DOGEUSD" in PAPER_TO_INSTRUMENT_ID
        assert "DOGEUSD" not in panel.symbols
        assert panel.symbols < frozenset(PAPER_TO_INSTRUMENT_ID)
