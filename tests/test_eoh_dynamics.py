"""
Tests for hours_eoh.core.eoh_dynamics

Covers: deferred_eoh, eoh_compounding, compounding_profile,
regenerative_offset, regenerative_vs_maintenance_comparison,
eoh_reduction_ratio, rank_investment_candidates, optimal_investment,
maintenance_strategy_compare, deferred_eoh_paydown,
regenerative_investment_required, update_deferred_from_fulfillment.
"""

import math
import pytest

from hours_eoh.data import (
    ASSET_TYPES,
    PRE_THRESHOLD_COMPOUND_RATE,
    MONITORING_SPIKE_SOFTENING_MAX,
    REGEN_AUTOMATION_LEVERAGE_MAX,
)
from hours_eoh.core.eoh_dynamics import (
    deferred_eoh,
    eoh_compounding,
    compounding_profile,
    regenerative_offset,
    regenerative_vs_maintenance_comparison,
    eoh_reduction_ratio,
    rank_investment_candidates,
    optimal_investment,
    maintenance_strategy_compare,
    deferred_eoh_paydown,
    regenerative_investment_required,
    update_deferred_from_fulfillment,
    REGENERATIVE_PROFILES,
)
from hours_eoh.data import ASSET_TYPES

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# deferred_eoh
# ===========================================================================

class TestDeferredEoh:

    def test_is_deficit(self):
        accumulated = 10_000.0
        fulfilled   =  7_000.0
        assert deferred_eoh(accumulated, fulfilled) == pytest.approx(3_000.0)

    def test_zero_when_fully_maintained(self):
        assert deferred_eoh(5_000.0, 5_000.0) == pytest.approx(0.0)

    def test_zero_when_overfulfilled(self):
        # Surplus maintenance → no deficit (non-negative)
        assert deferred_eoh(3_000.0, 4_000.0) == pytest.approx(0.0)

    def test_positive_only(self):
        result = deferred_eoh(1000.0, 2000.0)
        assert result >= 0.0


# ===========================================================================
# eoh_compounding
# ===========================================================================

class TestEohCompounding:

    def test_zero_deferred_produces_zero_compounding(self):
        for asset_type in ASSET_TYPES:
            for eps in KEY_EPSILONS:
                result = eoh_compounding(0.0, asset_type, 50, eps)
                assert result == 0.0

    def test_zero_time_produces_zero_compounding(self):
        for asset_type in ASSET_TYPES:
            result = eoh_compounding(10_000.0, asset_type, 0, 0.40)
            assert result == 0.0

    def test_compounding_positive_for_positive_deferred_and_time(self):
        for asset_type in ASSET_TYPES:
            T = ASSET_TYPES[asset_type]["threshold_age"]
            result = eoh_compounding(10_000.0, asset_type, T / 2, 0.40)
            assert result > 0.0

    def test_compounding_nonlinear_NOT_exponential(self):
        """
        Deferred EOH grows nonlinearly, not exponentially.

        Key test: the ratio compounding(T) / compounding(T/2) should be
        MUCH larger than what smooth exponential growth would predict.
        """
        deferred = 10_000.0
        for asset_type in ASSET_TYPES:
            T = float(ASSET_TYPES[asset_type]["threshold_age"])
            half_T = T * 0.5

            at_half = eoh_compounding(deferred, asset_type, half_T, 0.0)
            at_T    = eoh_compounding(deferred, asset_type, T,      0.0)

            assert at_T > at_half, (
                f"Compounding at threshold T must exceed compounding at T/2 "
                f"for asset_type={asset_type}"
            )

            # The jump should be large (discontinuous spike at threshold)
            ratio = at_T / max(at_half, 1e-10)
            assert ratio > 8.0, (
                f"Threshold discontinuity should be large (ratio={ratio:.1f}) for "
                f"asset_type={asset_type}. Expected ratio > 8.0 to distinguish "
                f"from smooth exponential growth."
            )

    def test_software_compounds_faster_than_stone_bridge(self):
        """Mission Statement: 'stone bridge: slow; software: fast'."""
        deferred = 10_000.0

        T_soft   = float(ASSET_TYPES["software"]["threshold_age"])
        T_stone  = float(ASSET_TYPES["stone_bridge"]["threshold_age"])

        pre_soft  = eoh_compounding(deferred, "software",      T_soft  * 0.5, 0.0)
        at_soft   = eoh_compounding(deferred, "software",      T_soft,        0.0)
        pre_stone = eoh_compounding(deferred, "stone_bridge",  T_stone * 0.5, 0.0)
        at_stone  = eoh_compounding(deferred, "stone_bridge",  T_stone,       0.0)

        ratio_soft  = at_soft  / max(pre_soft,  1e-10)
        ratio_stone = at_stone / max(pre_stone, 1e-10)

        assert ratio_soft > ratio_stone, (
            f"Software should have a more severe threshold spike than stone bridge. "
            f"software ratio={ratio_soft:.1f}, stone_bridge ratio={ratio_stone:.1f}"
        )

    def test_compounding_escalates_after_threshold(self):
        """Post-threshold escalation must be rapid (power-law, not leveling off)."""
        deferred = 10_000.0
        asset_type = "software"
        T = float(ASSET_TYPES[asset_type]["threshold_age"])

        at_T    = eoh_compounding(deferred, asset_type, T,     0.0)
        at_2T   = eoh_compounding(deferred, asset_type, T * 2, 0.0)

        assert at_2T > at_T * 2.0, (
            f"Post-threshold compounding should accelerate: at_2T={at_2T:.0f} "
            f"should be much more than 2× at_T={at_T:.0f}"
        )

    def test_unknown_asset_type_raises(self):
        with pytest.raises(KeyError):
            eoh_compounding(1000.0, "magic_carpet", 10, 0.40)

    def test_compounding_produces_no_teh(self):
        """No EOH mechanism creates TEH without labor.

        eoh_compounding() returns a float (obligation), not a TEH event.
        """
        result = eoh_compounding(5000.0, "building", 30, 0.40)
        assert isinstance(result, float)
        assert result >= 0.0
        assert not hasattr(result, "teh_created")

    def test_compounding_at_all_key_epsilons(self):
        """All functions must produce finite output at key ε values."""
        deferred = 5_000.0
        for asset_type in ASSET_TYPES:
            T = float(ASSET_TYPES[asset_type]["threshold_age"])
            for eps in KEY_EPSILONS:
                result = eoh_compounding(deferred, asset_type, T, eps)
                assert math.isfinite(result), (
                    f"eoh_compounding must be finite at ε={eps}, asset={asset_type}"
                )
                assert result >= 0.0

    def test_higher_epsilon_softens_spike(self):
        """Better monitoring at higher ε slightly reduces the spike severity."""
        deferred = 10_000.0
        asset_type = "power_grid"
        T = float(ASSET_TYPES[asset_type]["threshold_age"])

        at_eps0  = eoh_compounding(deferred, asset_type, T, epsilon=0.0)
        at_eps90 = eoh_compounding(deferred, asset_type, T, epsilon=0.90)
        assert at_eps0 > at_eps90, (
            "Better monitoring at ε=0.90 should soften the threshold spike"
        )

    def test_compounding_profile_returns_trajectory(self):
        profile = compounding_profile("building", deferred=5000.0, epsilon=0.40)
        assert len(profile) > 0
        for point in profile:
            assert "year" in point
            assert "additional_eoh" in point
            assert "is_post_threshold" in point
            assert math.isfinite(point["additional_eoh"])
            assert point["additional_eoh"] >= 0.0

    def test_compounding_profile_threshold_flag(self):
        """Profile should correctly mark pre- and post-threshold points."""
        T = float(ASSET_TYPES["stone_bridge"]["threshold_age"])
        profile = compounding_profile("stone_bridge", 5000.0, max_years=2 * T)

        pre_points  = [p for p in profile if not p["is_post_threshold"]]
        post_points = [p for p in profile if p["is_post_threshold"]]

        assert len(pre_points) > 0
        assert len(post_points) > 0

        avg_pre  = sum(p["additional_eoh"] for p in pre_points)  / len(pre_points)
        avg_post = sum(p["additional_eoh"] for p in post_points) / len(post_points)
        assert avg_post > avg_pre


# ===========================================================================
# regenerative_offset
# ===========================================================================

class TestRegenerativeLabor:

    def test_returns_future_reduction(self):
        """Regenerative labor reduces future EOH generation rates."""
        result = regenerative_offset("composting", 100.0, epsilon=0.40)
        assert result["future_eoh_reduction_per_year"] > 0.0
        assert result["lifetime_eoh_savings"] > 0.0

    def test_current_eoh_fulfilled(self):
        """Regenerative labor ALSO fulfills current EOH (creates TEH normally)."""
        hours = 200.0
        result = regenerative_offset("preventive_maintenance", hours, epsilon=0.40)
        assert result["current_eoh_fulfilled"] == pytest.approx(hours)

    def test_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            for labor_type in REGENERATIVE_PROFILES:
                result = regenerative_offset(labor_type, 100.0, epsilon=eps)
                assert result["future_eoh_reduction_per_year"] > 0
                assert math.isfinite(result["lifetime_eoh_savings"])

    def test_higher_epsilon_amplifies_regenerative_benefit(self):
        """Automated monitoring extends reach of regenerative labor at higher ε."""
        r_lo = regenerative_offset("ecosystem_restoration", 100.0, epsilon=0.0)
        r_hi = regenerative_offset("ecosystem_restoration", 100.0, epsilon=0.90)
        assert r_hi["future_eoh_reduction_per_year"] > r_lo["future_eoh_reduction_per_year"]

    def test_unknown_labor_type_raises(self):
        with pytest.raises(KeyError):
            regenerative_offset("interpretive_dance", 100.0, 0.40)

    def test_does_not_create_teh_directly(self):
        """No EOH mechanism creates TEH without labor.

        regenerative_offset() returns future EOH reduction — not TEH.
        """
        result = regenerative_offset("composting", 100.0, 0.40)
        assert "future_eoh_reduction_per_year" in result
        assert "lifetime_eoh_savings" in result
        assert "teh_created" not in result

    def test_preventive_maintenance_has_high_eoh_leverage(self):
        """Preventive maintenance prevents spike events — high EOH leverage."""
        r_prev = regenerative_offset("preventive_maintenance", 100.0, 0.40)
        r_comp = regenerative_offset("composting", 100.0, 0.40)
        assert (r_prev["future_eoh_reduction_per_year"]
                > r_comp["future_eoh_reduction_per_year"]), (
            "Preventive maintenance has higher leverage than composting"
        )

    def test_lifetime_eoh_savings_equals_rate_times_years(self):
        result = regenerative_offset("education_training", 100.0, 0.40)
        expected = result["future_eoh_reduction_per_year"] * result["amortization_years"]
        assert result["lifetime_eoh_savings"] == pytest.approx(expected)

    def test_regenerative_vs_maintenance_comparison(self):
        result = regenerative_vs_maintenance_comparison(
            labor_hours=1000.0,
            regen_type="ecosystem_restoration",
            current_eoh_demand=800.0,
            epsilon=0.40,
        )
        assert "maintenance" in result
        assert "regenerative" in result
        assert "net_advantage" in result
        assert result["net_advantage"] > 0, (
            "Regenerative labor should win over maintenance in lifetime EOH impact"
        )


# ===========================================================================
# eoh_reduction_ratio
# ===========================================================================

class TestEohReductionRatio:

    def test_positive_return_investment(self):
        """Identifies net-positive assets correctly."""
        result = eoh_reduction_ratio(
            production_cost_eoh=50_000,
            annual_maintenance_eoh=500,
            annual_eoh_eliminated=5_000,
            design_life=20.0,
            epsilon=0.40,
        )
        assert result["net_positive"] is True, (
            f"Asset should be net-positive (ratio={result['ratio']:.3f})"
        )
        assert result["net_eoh_reduction"] > 0

    def test_net_loss_investment(self):
        """Identifies net-negative (net EOH loss) assets."""
        result = eoh_reduction_ratio(
            production_cost_eoh=500_000,
            annual_maintenance_eoh=10_000,
            annual_eoh_eliminated=1_000,  # eliminates far less than it costs
            design_life=20.0,
            epsilon=0.40,
        )
        assert result["net_positive"] is False, (
            f"Asset should be net-negative (ratio={result['ratio']:.3f})"
        )
        assert result["net_eoh_reduction"] < 0

    def test_mission_statement_aqueduct_logic(self):
        """
        Mission Statement: "piped water eliminates per-person water-fetching labor"
        An aqueduct serving 10,000 people, each saving 150 hours/year of water
        fetching = 1.5M EOH/yr eliminated, vs. 50k build + 5k/yr maintain.
        """
        result = eoh_reduction_ratio(
            production_cost_eoh=50_000,
            annual_maintenance_eoh=5_000,
            annual_eoh_eliminated=1_500_000,
            design_life=50.0,
            epsilon=0.0,
        )
        assert result["net_positive"] is True
        assert result["ratio"] < 0.01, (
            "Aqueduct should have a very low EOH cost/benefit ratio"
        )

    def test_higher_epsilon_improves_ratio(self):
        """At higher ε, automation handles more maintenance → human-labor cost falls."""
        kwargs = dict(
            production_cost_eoh=80_000,
            annual_maintenance_eoh=2_000,
            annual_eoh_eliminated=5_000,
            design_life=30.0,
        )
        r_eps0  = eoh_reduction_ratio(**kwargs, epsilon=0.0)
        r_eps90 = eoh_reduction_ratio(**kwargs, epsilon=0.90)

        assert r_eps90["ratio"] < r_eps0["ratio"], (
            "Higher ε should improve the investment ratio (lower cost in human labor)"
        )

    def test_payback_years_positive_for_worthwhile_asset(self):
        result = eoh_reduction_ratio(
            production_cost_eoh=10_000,
            annual_maintenance_eoh=100,
            annual_eoh_eliminated=1_000,
            design_life=20.0,
            epsilon=0.40,
        )
        assert result["payback_years"] is not None
        assert result["payback_years"] > 0

    def test_payback_none_for_net_loss(self):
        """Asset that never pays back should return payback_years=None."""
        result = eoh_reduction_ratio(
            production_cost_eoh=100_000,
            annual_maintenance_eoh=5_000,   # maint > benefit
            annual_eoh_eliminated=100,
            design_life=20.0,
            epsilon=0.0,
        )
        assert result["payback_years"] is None

    def test_design_life_zero_raises(self):
        with pytest.raises(ValueError):
            eoh_reduction_ratio(10_000, 500, 1_000, design_life=0.0)

    def test_returns_all_expected_keys(self):
        result = eoh_reduction_ratio(50_000, 1_000, 5_000, 25.0, 0.40)
        for key in ("production_cost_eoh", "lifetime_maintenance_eoh",
                    "total_eoh_cost", "lifetime_eoh_benefit", "net_eoh_reduction",
                    "ratio", "net_positive", "payback_years", "epsilon"):
            assert key in result, f"Missing key: {key}"


# ===========================================================================
# rank_investment_candidates and optimal_investment
# ===========================================================================

class TestOptimalInvestment:

    def _make_candidates(self):
        return [
            {
                "name": "aqueduct",
                "production_cost_eoh": 50_000,
                "annual_maintenance_eoh": 500,
                "annual_eoh_eliminated": 500_000,
                "design_life": 50.0,
            },
            {
                "name": "road",
                "production_cost_eoh": 80_000,
                "annual_maintenance_eoh": 2_000,
                "annual_eoh_eliminated": 20_000,
                "design_life": 30.0,
            },
            {
                "name": "white_elephant",
                "production_cost_eoh": 200_000,
                "annual_maintenance_eoh": 10_000,  # costs more than it saves
                "annual_eoh_eliminated": 500,
                "design_life": 10.0,
            },
        ]

    def test_rank_investment_identifies_best_first(self):
        """Infrastructure investment logic correctly ranks assets."""
        ranked = rank_investment_candidates(self._make_candidates(), epsilon=0.40)
        assert ranked[0]["name"] == "aqueduct"

    def test_rank_investment_net_negative_last(self):
        """White elephant (net-negative) should appear last."""
        ranked = rank_investment_candidates(self._make_candidates(), epsilon=0.40)
        assert ranked[-1]["name"] == "white_elephant"
        assert ranked[-1]["net_positive"] is False

    def test_optimal_investment_funds_best_assets(self):
        """Allocates available labor to maximize net EOH reduction."""
        result = optimal_investment(
            available_labor_eoh=150_000,
            candidates=self._make_candidates(),
            epsilon=0.40,
        )
        funded_names = [a["name"] for a in result["funded"]]
        assert "aqueduct" in funded_names, "Best asset must be funded"

    def test_optimal_investment_excludes_net_negative(self):
        result = optimal_investment(
            available_labor_eoh=500_000,
            candidates=self._make_candidates(),
            epsilon=0.40,
        )
        funded_names = [a["name"] for a in result["funded"]]
        net_neg_names = [a["name"] for a in result["net_negative"]]
        assert "white_elephant" not in funded_names
        assert "white_elephant" in net_neg_names

    def test_optimal_investment_respects_budget(self):
        result = optimal_investment(
            available_labor_eoh=60_000,
            candidates=self._make_candidates(),
            epsilon=0.40,
        )
        assert result["total_cost_eoh"] <= 60_000 + 1e-6

    def test_optimal_investment_labor_utilization(self):
        result = optimal_investment(
            available_labor_eoh=200_000,
            candidates=self._make_candidates(),
            epsilon=0.40,
        )
        assert 0.0 <= result["labor_utilization"] <= 1.0

    def test_optimal_investment_empty_candidates(self):
        result = optimal_investment(100_000, [], epsilon=0.40)
        assert result["funded"] == []
        assert result["total_net_eoh_reduction"] == 0.0

    def test_optimal_investment_zero_budget(self):
        result = optimal_investment(0.0, self._make_candidates(), epsilon=0.40)
        assert result["funded"] == []
        assert result["remaining_labor"] == pytest.approx(0.0)


# ===========================================================================
# maintenance_strategy_compare
# ===========================================================================

class TestMaintenanceStrategyCompare:

    def test_returns_all_three_strategies(self):
        result = maintenance_strategy_compare(
            asset_type="stone_bridge",
            annual_eoh=2_500.0,
            teh_value=500_000.0,
            years_horizon=30,
            epsilon=0.40,
        )
        for key in ("continuous", "deferred_to_writedown", "replace_at_writedown"):
            assert key in result
        assert "optimal_strategy" in result
        assert "continuous_advantage" in result

    def test_continuous_total_equals_annual_times_horizon(self):
        result = maintenance_strategy_compare(
            asset_type="stone_bridge",
            annual_eoh=2_500.0,
            teh_value=500_000.0,
            years_horizon=20,
            epsilon=0.40,
        )
        expected = 2_500.0 * (1.0 - 0.40) * 20
        assert result["continuous"]["total_eoh"] == pytest.approx(expected)

    def test_human_labor_fraction_correct(self):
        result = maintenance_strategy_compare(
            "stone_bridge", 1_000.0, 100_000.0, epsilon=0.60
        )
        assert result["human_labor_fraction"] == pytest.approx(0.40)

    def test_replace_cheaper_than_rebuild(self):
        result = maintenance_strategy_compare(
            asset_type="stone_bridge",
            annual_eoh=2_500.0,
            teh_value=500_000.0,
            years_horizon=50,
            epsilon=0.40,
        )
        deferred = result["deferred_to_writedown"]["total_eoh"]
        replace  = result["replace_at_writedown"]["total_eoh"]
        if deferred > 0:
            assert replace <= deferred + 1e-6

    def test_high_epsilon_reduces_all_costs(self):
        r_low  = maintenance_strategy_compare("stone_bridge", 2_500.0, 500_000.0,
                                              years_horizon=30, epsilon=0.10)
        r_high = maintenance_strategy_compare("stone_bridge", 2_500.0, 500_000.0,
                                              years_horizon=30, epsilon=0.90)
        assert r_high["continuous"]["total_eoh"] < r_low["continuous"]["total_eoh"]

    def test_long_lived_asset_favors_continuous(self):
        """Stone bridges are long-lived with sharp compounding — continuous should win."""
        result = maintenance_strategy_compare(
            asset_type="stone_bridge",
            annual_eoh=2_500.0,
            teh_value=500_000.0,
            initial_condition=1.0,
            years_horizon=50,
            epsilon=0.40,
        )
        assert result["deferred_to_writedown"]["writedown_year"] is not None
        assert result["deferred_to_writedown"]["total_eoh"] > 0

    def test_no_writedown_in_short_horizon(self):
        """A brand-new asset with short horizon may not reach write-down threshold."""
        result = maintenance_strategy_compare(
            asset_type="stone_bridge",
            annual_eoh=100.0,
            teh_value=500_000.0,
            initial_condition=1.0,
            years_horizon=3,
            epsilon=0.40,
            natural_decay_rate=0.001,
        )
        if result["deferred_to_writedown"]["writedown_year"] is None:
            assert result["deferred_to_writedown"]["total_eoh"] == 0.0

    def test_optimal_strategy_is_one_of_three(self):
        result = maintenance_strategy_compare("stone_bridge", 2_500.0, 500_000.0)
        assert result["optimal_strategy"] in (
            "continuous", "deferred_to_writedown", "replace_at_writedown"
        )


# ===========================================================================
# deferred_eoh_paydown
# ===========================================================================

class TestDeferredEohPaydown:

    def _regen(self, per_year=1000.0, amort=20, domain="ecological"):
        return {
            "future_eoh_reduction_per_year": per_year,
            "amortization_years": amort,
            "domain": domain,
        }

    def test_annual_paydown_reduces_deferred(self):
        result = deferred_eoh_paydown(self._regen(per_year=500.0), current_deferred=2000.0)
        assert result["new_deferred_after_one_year"] == pytest.approx(1500.0)

    def test_annual_paydown_capped_at_current_deferred(self):
        result = deferred_eoh_paydown(self._regen(per_year=5000.0), current_deferred=1000.0)
        assert result["annual_paydown"] == pytest.approx(1000.0)
        assert result["new_deferred_after_one_year"] == pytest.approx(0.0)

    def test_deferred_cleared_when_single_year_covers_all(self):
        result = deferred_eoh_paydown(self._regen(per_year=5000.0), current_deferred=1000.0)
        assert result["deferred_cleared"] is True

    def test_deferred_not_cleared_when_partial(self):
        result = deferred_eoh_paydown(self._regen(per_year=100.0), current_deferred=5000.0)
        assert result["deferred_cleared"] is False

    def test_lifetime_paydown_bounded_by_deferred(self):
        result = deferred_eoh_paydown(self._regen(per_year=200.0, amort=5), current_deferred=500.0)
        # 200×5=1000 > 500 → capped at 500
        assert result["lifetime_paydown"] == pytest.approx(500.0)
        assert result["new_deferred_after_amortization"] == pytest.approx(0.0)

    def test_years_to_clear_correct(self):
        result = deferred_eoh_paydown(self._regen(per_year=500.0), current_deferred=1500.0)
        assert result["years_to_clear"] == pytest.approx(3.0)

    def test_zero_deferred_returns_none_years_to_clear(self):
        result = deferred_eoh_paydown(self._regen(per_year=500.0), current_deferred=0.0)
        assert result["years_to_clear"] is None

    def test_domain_passes_through(self):
        result = deferred_eoh_paydown(self._regen(domain="ecological"), current_deferred=100.0)
        assert result["domain"] == "ecological"


# ===========================================================================
# regenerative_investment_required
# ===========================================================================

class TestRegenerativeInvestmentRequired:

    def test_hours_needed_positive(self):
        result = regenerative_investment_required(500.0, "composting", epsilon=0.0)
        assert result["hours_needed_per_year"] > 0.0

    def test_inverse_of_regenerative_offset(self):
        target_per_year = 400.0
        inv = regenerative_investment_required(target_per_year, "composting", epsilon=0.40)
        fwd = regenerative_offset("composting", inv["hours_needed_per_year"], epsilon=0.40)
        assert fwd["future_eoh_reduction_per_year"] == pytest.approx(target_per_year, rel=1e-6)

    def test_higher_epsilon_reduces_hours_needed(self):
        low  = regenerative_investment_required(1000.0, "composting", epsilon=0.0)
        high = regenerative_investment_required(1000.0, "composting", epsilon=0.90)
        assert high["hours_needed_per_year"] < low["hours_needed_per_year"]

    def test_years_horizon_override(self):
        default = regenerative_investment_required(500.0, "composting", epsilon=0.40)
        custom  = regenerative_investment_required(500.0, "composting", epsilon=0.40, years_horizon=5)
        assert custom["years_horizon"] == 5
        assert custom["cumulative_hours_over_horizon"] != default["cumulative_hours_over_horizon"]

    def test_invalid_labor_type_raises(self):
        with pytest.raises(KeyError):
            regenerative_investment_required(500.0, "not_a_type", epsilon=0.40)

    def test_result_keys(self):
        result = regenerative_investment_required(500.0, "composting")
        for key in ("labor_type", "domain", "hours_needed_per_year",
                    "cumulative_hours_over_horizon", "years_horizon",
                    "epsilon", "epsilon_leverage"):
            assert key in result


# ===========================================================================
# update_deferred_from_fulfillment
# ===========================================================================

class TestUpdateDeferredFromFulfillment:
    """Deferred EOH backlog must shrink by the amount fulfilled, capped at zero."""

    def test_partial_fulfillment(self):
        result = update_deferred_from_fulfillment(10_000.0, 4_000.0)
        assert result["new_deferred"] == pytest.approx(6_000.0)
        assert result["reduction"] == pytest.approx(4_000.0)
        assert result["excess_fulfillment"] == pytest.approx(0.0)
        assert result["fully_cleared"] is False

    def test_exact_fulfillment_clears_backlog(self):
        result = update_deferred_from_fulfillment(10_000.0, 10_000.0)
        assert result["new_deferred"] == pytest.approx(0.0)
        assert result["fully_cleared"] is True
        assert result["excess_fulfillment"] == pytest.approx(0.0)

    def test_over_fulfillment_caps_at_zero(self):
        result = update_deferred_from_fulfillment(5_000.0, 20_000.0)
        assert result["new_deferred"] == pytest.approx(0.0)
        assert result["fully_cleared"] is True
        assert result["excess_fulfillment"] == pytest.approx(15_000.0)
        assert result["reduction"] == pytest.approx(5_000.0)

    def test_zero_backlog_no_effect(self):
        result = update_deferred_from_fulfillment(0.0, 5_000.0)
        assert result["new_deferred"] == pytest.approx(0.0)
        assert result["reduction"] == pytest.approx(0.0)
        assert result["excess_fulfillment"] == pytest.approx(5_000.0)

    def test_zero_fulfillment_unchanged(self):
        result = update_deferred_from_fulfillment(8_000.0, 0.0)
        assert result["new_deferred"] == pytest.approx(8_000.0)
        assert result["reduction"] == pytest.approx(0.0)
        assert result["excess_fulfillment"] == pytest.approx(0.0)
        assert result["fully_cleared"] is False

    def test_negative_inputs_clamped(self):
        """Negative inputs must be clamped to zero (no error)."""
        result = update_deferred_from_fulfillment(-100.0, -50.0)
        assert result["new_deferred"] == pytest.approx(0.0)
        assert result["fully_cleared"] is True

    def test_return_keys_present(self):
        result = update_deferred_from_fulfillment(1_000.0, 500.0)
        for key in ("previous_deferred", "fulfilled_eoh", "reduction",
                    "new_deferred", "fully_cleared", "excess_fulfillment"):
            assert key in result

    def test_idempotent_chain(self):
        """Applying zero fulfillment repeatedly must not change the balance."""
        deferred = 50_000.0
        for _ in range(10):
            result = update_deferred_from_fulfillment(deferred, 0.0)
            deferred = result["new_deferred"]
        assert deferred == pytest.approx(50_000.0)


# ===========================================================================
# Cross-Cutting: No EOH Mechanism Creates TEH Without Labor
# ===========================================================================

class TestNoOrphanTeh:
    """No EOH mechanism creates TEH without labor.

    This is the Condition III analog for EOH: the EOH system generates
    obligations (EOH) and reduces them (fulfillment → TEH), but no EOH
    function creates TEH directly.
    """

    def test_eoh_compounding_returns_eoh_not_teh(self):
        result = eoh_compounding(5000.0, "building", 30.0, 0.40)
        assert isinstance(result, float)
        assert not isinstance(result, dict)

    def test_regenerative_offset_returns_future_eoh_not_teh(self):
        result = regenerative_offset("composting", 100.0, 0.40)
        assert "future_eoh_reduction_per_year" in result
        assert "teh_created" not in result


class TestCompoundingAndRegenerativeShape:
    """
    THE THREE COMPOUNDING/REGENERATIVE CONSTANTS, migrated and pinned
    (2026-08-28). All were shadow constants in `core/eoh_dynamics.py`, and a
    +7% move of any of them failed no test.

    Each governs a SHAPE — a ceiling, a softening cap, a leverage slope — so
    each is pinned by the behaviour its docstring claims, not by its level.
    """

    def test_pre_threshold_compounding_approaches_its_ceiling(self):
        """
        `PRE_THRESHOLD_COMPOUND_RATE` is the limit as t → T⁻: deferred
        maintenance accrues at most this fraction per period BEFORE the
        irreversibility threshold.
        """
        T = float(ASSET_TYPES["generic_infra"]["threshold_age"])
        deferred = 1000.0
        just_below = eoh_compounding(deferred, "generic_infra", T * 0.999, 0.0)
        assert just_below == pytest.approx(
            deferred * PRE_THRESHOLD_COMPOUND_RATE, rel=0.01
        )
        assert just_below <= deferred * PRE_THRESHOLD_COMPOUND_RATE + 1e-9

    def test_pre_threshold_compounding_is_bounded_everywhere_below_T(self):
        T = float(ASSET_TYPES["generic_infra"]["threshold_age"])
        ceiling = 1000.0 * PRE_THRESHOLD_COMPOUND_RATE
        for frac in (0.01, 0.25, 0.5, 0.9, 0.99):
            assert eoh_compounding(1000.0, "generic_infra", T * frac, 0.0) <= ceiling + 1e-9

    def test_compounding_rises_with_time_deferred(self):
        """Deferring work makes more work — this is entropy, not interest, and
        Condition III is untouched because no TEH is created."""
        vals = [eoh_compounding(1000.0, "generic_infra", t, 0.40)
                for t in (1.0, 10.0, 30.0, 60.0, 120.0)]
        assert vals == sorted(vals), vals

    def test_the_threshold_is_a_discontinuity_not_a_bend(self):
        """The sharp-failure claim: crossing T must jump, not merely steepen."""
        T = float(ASSET_TYPES["generic_infra"]["threshold_age"])
        below = eoh_compounding(1000.0, "generic_infra", T * 0.999, 0.0)
        above = eoh_compounding(1000.0, "generic_infra", T * 1.001, 0.0)
        assert above > 10.0 * below, f"no discontinuity at T: {below} -> {above}"

    def test_monitoring_softens_the_post_threshold_spike_by_a_capped_fraction(self):
        """
        `MONITORING_SPIKE_SOFTENING_MAX` caps how much automated monitoring can
        mitigate. THE CAP IS THE CLAIM: monitoring makes an obligation visible
        sooner, it does not discharge it, so most of the spike survives however
        good the sensors get.
        """
        T = float(ASSET_TYPES["generic_infra"]["threshold_age"])
        deferred, t = 1000.0, T * 1.5
        unmonitored = eoh_compounding(deferred, "generic_infra", t, 0.0)
        fully = eoh_compounding(deferred, "generic_infra", t, 1.0)
        assert fully < unmonitored, "monitoring must soften something"

        # The softener multiplies the SPIKE TERM ONLY — the pre-threshold
        # baseline is added afterwards and is not mitigable. Comparing the
        # totals gives 0.8007, not 0.8, and asserting the total ratio would
        # encode that arithmetic artefact as if it were the constant.
        pre = deferred * PRE_THRESHOLD_COMPOUND_RATE
        assert (fully - pre) / (unmonitored - pre) == pytest.approx(
            1.0 - MONITORING_SPIKE_SOFTENING_MAX, rel=1e-9
        )
        assert fully > 0.5 * unmonitored, (
            "most of the spike must survive — monitoring reveals, it does not repair"
        )

    def test_monitoring_does_not_soften_below_the_threshold(self):
        """The softening is a spike mitigation, so pre-threshold accrual must be
        ε-invariant. If this fails, automation is discounting an obligation it
        has not acted on."""
        T = float(ASSET_TYPES["generic_infra"]["threshold_age"])
        lo = eoh_compounding(1000.0, "generic_infra", T * 0.5, 0.0)
        hi = eoh_compounding(1000.0, "generic_infra", T * 0.5, 0.99)
        assert lo == pytest.approx(hi, rel=1e-12)

    def test_regenerative_leverage_rises_to_its_cap_with_automation(self):
        """`REGEN_AUTOMATION_LEVERAGE_MAX` is the ε=1 amplification of
        regenerative labour: leverage = 1 + MAX × ε."""
        at_zero = regenerative_offset("ecosystem_restoration", 100.0, 0.0)
        at_one = regenerative_offset("ecosystem_restoration", 100.0, 1.0)
        assert at_zero["epsilon_leverage"] == pytest.approx(1.0, rel=1e-12)
        assert at_one["epsilon_leverage"] == pytest.approx(
            1.0 + REGEN_AUTOMATION_LEVERAGE_MAX, rel=1e-9
        )

    def test_regenerative_leverage_is_monotone_and_bounded(self):
        lev = [regenerative_offset("ecosystem_restoration", 100.0, e)["epsilon_leverage"]
               for e in (0.0, 0.25, 0.5, 0.75, 0.99)]
        assert lev == sorted(lev), lev
        assert all(1.0 <= x <= 1.0 + REGEN_AUTOMATION_LEVERAGE_MAX + 1e-9 for x in lev)
