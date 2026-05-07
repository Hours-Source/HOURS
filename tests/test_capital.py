"""
Tests for hours_eoh.core.capital

Covers: make_asset, asset_condition, asset_condition_trajectory,
writedown_trigger, execute_writedown, birth_event, death_event,
maturation_update, aggregate_personal_eoh_fulfilled, aggregate_eoh_eliminated,
apply_birth_eoh, estate_dissolution.
"""

import math
import pytest

from hours_eoh.core.capital import (
    make_asset,
    asset_condition,
    asset_condition_trajectory,
    writedown_trigger,
    execute_writedown,
    birth_event,
    death_event,
    maturation_update,
    aggregate_personal_eoh_fulfilled,
    aggregate_eoh_eliminated,
    apply_birth_eoh,
    estate_dissolution,
)
from hours_eoh.core.eoh_fulfillment import teh_supply
from hours_eoh.core.conditions import condition_i_check
from hours_eoh.core.prices import basket_price
from hours_eoh.data import (
    PERSONAL_EOH_BASE,
    ESTATE_PERSONAL_RESERVE_YEARS,
    ANNUAL_DEATH_RATE,
    ESTATE_INHERITANCE_FRACTION,
    ESTATE_LEVY_FRACTION,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_worker(age: float = 35.0, capacity: float = 1200.0) -> dict:
    """Build a human capital asset for testing."""
    return make_asset(
        asset_id=f"worker_{age}",
        asset_type="generic_infra",
        teh_value=500.0,
        annual_eoh=PERSONAL_EOH_BASE * 1.0,
        design_life=80.0,
        age=age,
        condition=1.0,
        is_human_capital=True,
        entropy_reduction_capacity=capacity,
        personal_eoh_per_year=PERSONAL_EOH_BASE,
    )


# ===========================================================================
# asset_condition / asset_condition_trajectory
# ===========================================================================

class TestAssetCondition:

    def test_perfect_maintenance_degrades_only_by_natural_decay(self):
        """Full maintenance slows but cannot stop natural aging."""
        initial = 1.0
        history = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 1000.0}] * 10
        cond = asset_condition(initial, history, natural_decay_rate=0.005)
        assert 0.90 < cond < 1.0

    def test_full_neglect_degrades_rapidly(self):
        """Zero maintenance leads to rapid condition decline."""
        initial = 1.0
        history = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 0.0}] * 10
        cond = asset_condition(initial, history, natural_decay_rate=0.005)
        assert cond < 0.50, f"Full neglect should degrade condition; got {cond:.3f}"

    def test_partial_maintenance_produces_intermediate_condition(self):
        initial       = 1.0
        full_maint    = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 1000.0}] * 20
        partial_maint = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 500.0}] * 20
        zero_maint    = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 0.0}]   * 20

        cond_full    = asset_condition(initial, full_maint)
        cond_partial = asset_condition(initial, partial_maint)
        cond_zero    = asset_condition(initial, zero_maint)

        assert cond_full > cond_partial > cond_zero

    def test_empty_history_returns_initial(self):
        assert asset_condition(0.75, []) == pytest.approx(0.75)

    def test_condition_bounded_zero_to_one(self):
        """Condition must stay in [0, 1] regardless of inputs."""
        initial = 1.0
        extreme_neglect = [{"eoh_demanded": 1000.0, "eoh_fulfilled": 0.0}] * 100
        cond = asset_condition(initial, extreme_neglect)
        assert 0.0 <= cond <= 1.0

    def test_trajectory_returns_yearly_data(self):
        traj = asset_condition_trajectory(
            initial_condition=1.0,
            annual_eoh=1000.0,
            fulfillment_fraction=0.7,
            years=10,
        )
        assert len(traj) == 10
        for point in traj:
            assert "year" in point
            assert "condition" in point
            assert 0.0 <= point["condition"] <= 1.0

    def test_trajectory_full_maintenance_vs_neglect(self):
        traj_full = asset_condition_trajectory(1.0, 1000.0, 1.0, years=20)
        traj_neg  = asset_condition_trajectory(1.0, 1000.0, 0.0, years=20)
        assert traj_full[-1]["condition"] > traj_neg[-1]["condition"]


# ===========================================================================
# writedown_trigger
# ===========================================================================

class TestWritedownTrigger:

    def test_good_condition_does_not_trigger(self):
        assert writedown_trigger(0.80) is False
        assert writedown_trigger(0.21) is False

    def test_poor_condition_triggers(self):
        assert writedown_trigger(0.19) is True
        assert writedown_trigger(0.0)  is True

    def test_at_threshold_does_not_trigger(self):
        # Exactly at threshold: 0.20 >= 0.20, so NOT triggered
        assert writedown_trigger(0.20) is False

    def test_custom_threshold(self):
        assert writedown_trigger(0.30, recoverability_threshold=0.40) is True
        assert writedown_trigger(0.45, recoverability_threshold=0.40) is False


# ===========================================================================
# make_asset
# ===========================================================================

class TestMakeAsset:

    def test_annual_personal_eoh_fulfilled_defaults_to_zero(self):
        a = make_asset(
            asset_id="grid_001",
            asset_type="power_grid",
            teh_value=1_000_000.0,
            annual_eoh=5_000.0,
            design_life=40.0,
        )
        assert a["annual_personal_eoh_fulfilled"] == 0.0

    def test_annual_personal_eoh_fulfilled_stored(self):
        a = make_asset(
            asset_id="water_001",
            asset_type="water_treatment",
            teh_value=500_000.0,
            annual_eoh=2_000.0,
            design_life=30.0,
            annual_personal_eoh_fulfilled=800.0,
        )
        assert a["annual_personal_eoh_fulfilled"] == pytest.approx(800.0)


# ===========================================================================
# execute_writedown
# ===========================================================================

class TestExecuteWritedown:

    def _make_infra_asset(self):
        return make_asset(
            asset_id="bridge_001",
            asset_type="stone_bridge",
            teh_value=500_000.0,
            annual_eoh=2_500.0,
            design_life=80.0,
            annual_eoh_eliminated=50_000.0,
            age=85.0,
            condition=0.15,
        )

    def _make_human_asset(self):
        return make_asset(
            asset_id="worker_042",
            asset_type="generic_infra",
            teh_value=200_000.0,
            annual_eoh=1_500.0,
            design_life=80.0,
            age=75.0,
            condition=0.10,
            is_human_capital=True,
            entropy_reduction_capacity=2_000.0,
            personal_eoh_per_year=1_500.0,
        )

    def test_writedown_destroys_teh_equal_to_asset_value(self):
        asset = self._make_infra_asset()
        result = execute_writedown(asset)
        assert result["teh_destroyed"] == pytest.approx(asset["teh_value"])

    def test_writedown_zeros_eoh(self):
        asset = self._make_infra_asset()
        result = execute_writedown(asset)
        assert result["eoh_removed_from_ledger"] == pytest.approx(asset["annual_eoh"])

    def test_writedown_returns_asset_id(self):
        asset = self._make_infra_asset()
        result = execute_writedown(asset)
        assert result["asset_id"] == "bridge_001"

    def test_human_writedown_redistributes_capacity(self):
        asset = self._make_human_asset()
        workforce = 1000.0
        result = execute_writedown(asset, workforce_size=workforce)

        assert result["is_human_capital"] is True
        assert result["eoh_to_redistribute"] == pytest.approx(
            asset["entropy_reduction_capacity"]
        )
        remaining = workforce - 1
        expected_per_worker = asset["entropy_reduction_capacity"] / remaining
        assert result["eoh_per_remaining_worker"] == pytest.approx(expected_per_worker)

    def test_human_writedown_removes_capacity(self):
        asset = self._make_human_asset()
        result = execute_writedown(asset, workforce_size=500.0)
        assert result["human_capacity_lost"] == pytest.approx(
            asset["entropy_reduction_capacity"]
        )

    def test_infrastructure_writedown_returns_burden_to_population(self):
        asset = self._make_infra_asset()
        result = execute_writedown(asset)
        assert result["eoh_to_redistribute"] == pytest.approx(
            asset["annual_eoh_eliminated"]
        )

    def test_writedown_teh_destroyed_is_condition_i_event(self):
        """Write-down TEH destruction is a valid Condition I event."""
        asset = self._make_infra_asset()
        writedown = execute_writedown(asset)

        prior_created   = 10_000_000.0
        prior_destroyed = 4_000_000.0
        new_destroyed   = prior_destroyed + writedown["teh_destroyed"]
        new_supply      = teh_supply(prior_created, new_destroyed)

        ci = condition_i_check(prior_created, new_destroyed, new_supply, tolerance=1e-6)
        assert ci["passes"] is True, "Write-down TEH destruction should satisfy Condition I"

    def test_writedown_no_teh_created(self):
        """Write-down destroys TEH — it does NOT create TEH."""
        asset = self._make_infra_asset()
        result = execute_writedown(asset)
        assert "teh_destroyed" in result
        assert "teh_created" not in result


# ===========================================================================
# birth_event / death_event / maturation_update
# ===========================================================================

class TestHumanCapitalLifecycle:

    def test_birth_adds_eoh_demand_with_zero_capacity(self):
        """Birth → maximum EOH, zero capacity."""
        result = birth_event(population=1_000_000, eoh_ledger_total=5e9, epsilon=0.40)
        assert result["added_eoh_per_year"] > 0
        assert result["entropy_reduction_capacity"] == 0.0, (
            "Newborns have zero entropy-reduction capacity"
        )
        assert result["net_eoh_change_per_year"] > 0

    def test_birth_care_investment_positive(self):
        result = birth_event(1_000_000, 5e9, 0.40)
        assert result["care_eoh_required_total"] > 0

    def test_birth_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = birth_event(1_000_000, 5e9, epsilon=eps)
            assert result["added_eoh_per_year"] > 0
            assert math.isfinite(result["added_eoh_per_year"])

    def test_birth_event_no_teh_created(self):
        """Birth returns EOH demand — not TEH creation."""
        result = birth_event(1_000_000, 5e9, 0.40)
        assert "added_eoh_per_year" in result
        assert "teh_created" not in result

    def test_death_event_requires_human_capital(self):
        non_human = make_asset("bridge", "stone_bridge", 100_000, 500, 80)
        with pytest.raises(ValueError, match="human capital"):
            death_event(non_human, workforce_size=1000.0)

    def test_death_event_is_writedown(self):
        """Human capital write-down via death_event."""
        human = make_asset(
            "worker_001", "generic_infra", 150_000, 1200, 80,
            is_human_capital=True,
            entropy_reduction_capacity=1_800.0,
        )
        result = death_event(human, workforce_size=800.0)
        assert result["teh_destroyed"] == pytest.approx(150_000.0)
        assert result["is_human_capital"] is True
        assert result["new_workforce"] == pytest.approx(799.0)

    def test_maturation_increases_capacity(self):
        """Education/training increases entropy-reduction capacity."""
        human = make_asset(
            "person_001", "generic_infra", 0, 1000, 80,
            is_human_capital=True, entropy_reduction_capacity=0.0,
        )
        result = maturation_update(human, years_elapsed=5, education_eoh=5000)
        assert result["capacity_delta"] > 0
        assert result["new_capacity"] > 0
        assert result["return_on_investment_ratio"] > 0

    def test_maturation_roi_is_positive(self):
        """Care economy investment should produce positive ROI."""
        human = make_asset(
            "person_002", "generic_infra", 0, 1000, 80,
            is_human_capital=True, entropy_reduction_capacity=500.0,
        )
        result = maturation_update(human, years_elapsed=1, education_eoh=2000)
        assert result["return_on_investment_ratio"] > 1.0

    # ---------- integration tests from phase4 ----------

    def test_birth_event_high_personal_eoh(self):
        """Infant personal EOH is 3x working-age base."""
        result = birth_event(1_000_000, 1_500_000_000.0, epsilon=0.0)
        expected_eoh = PERSONAL_EOH_BASE * 3.0
        assert result["added_eoh_per_year"] == pytest.approx(expected_eoh, rel=0.05)

    def test_maturation_builds_capacity(self):
        """Years of education progressively builds capacity."""
        worker = make_worker(age=5.0, capacity=0.0)
        result = maturation_update(worker, years_elapsed=13.0, education_eoh=10_000.0)
        assert result["new_capacity"] > 0.0

    def test_maturation_roi_positive_phase4(self):
        worker = make_worker(age=5.0, capacity=0.0)
        result = maturation_update(worker, years_elapsed=13.0, education_eoh=5_000.0)
        assert result["return_on_investment_ratio"] > 1.0

    def test_death_event_removes_capacity(self):
        """Death write-down removes entropy-reduction capacity."""
        worker = make_worker(age=55.0, capacity=1200.0)
        result = death_event(worker, workforce_size=500_000.0, epsilon=0.40)
        assert result["human_capacity_lost"] == pytest.approx(1200.0)
        assert result["teh_destroyed"] == pytest.approx(worker["teh_value"])

    def test_death_event_redistributes_eoh(self):
        """EOH that the worker was fulfilling is redistributed, not abandoned."""
        worker = make_worker(age=55.0, capacity=1200.0)
        result = death_event(worker, workforce_size=10_000.0)
        assert result["eoh_to_redistribute"] == pytest.approx(1200.0)
        assert result["eoh_per_remaining_worker"] > 0.0

    def test_lifecycle_eoh_accounting_consistent(self):
        """Across a lifecycle: birth adds personal EOH, death removes it."""
        birth = birth_event(500_000, 750_000_000.0, epsilon=0.40)
        added_eoh = birth["added_eoh_per_year"]

        worker = make_worker(age=65.0, capacity=1000.0)
        worker["annual_eoh"] = added_eoh
        death = death_event(worker, workforce_size=500_000.0)
        removed_eoh = death["eoh_removed_from_ledger"]

        assert removed_eoh == pytest.approx(added_eoh)


# ===========================================================================
# aggregate_personal_eoh_fulfilled
# ===========================================================================

class TestAggregatePersonalEohFulfilled:

    def _water_asset(self, fulfilled: float = 800.0) -> dict:
        return make_asset(
            asset_id="water_001",
            asset_type="water_treatment",
            teh_value=500_000.0,
            annual_eoh=2_000.0,
            design_life=30.0,
            annual_personal_eoh_fulfilled=fulfilled,
        )

    def test_single_asset_per_capita(self):
        assets = [self._water_asset(800.0)]
        result = aggregate_personal_eoh_fulfilled(assets, population=1_000.0)
        assert result["total_annual_personal_eoh_fulfilled"] == pytest.approx(800.0)
        assert result["per_capita_fulfilled"] == pytest.approx(0.8)

    def test_multiple_assets_sum(self):
        assets = [
            self._water_asset(800.0),
            make_asset("hosp_001", "hospital", 2_000_000.0, 5_000.0, 40.0,
                       annual_personal_eoh_fulfilled=600.0),
        ]
        result = aggregate_personal_eoh_fulfilled(assets, population=1_000.0)
        assert result["total_annual_personal_eoh_fulfilled"] == pytest.approx(1_400.0)
        assert result["per_capita_fulfilled"] == pytest.approx(1.4)

    def test_empty_fleet_returns_zero(self):
        result = aggregate_personal_eoh_fulfilled([], population=1_000.0)
        assert result["total_annual_personal_eoh_fulfilled"] == 0.0
        assert result["per_capita_fulfilled"] == 0.0

    def test_assets_without_field_treated_as_zero(self):
        a = make_asset("bridge_001", "stone_bridge", 500_000.0, 2_000.0, 80.0)
        result = aggregate_personal_eoh_fulfilled([a], population=1_000.0)
        assert result["total_annual_personal_eoh_fulfilled"] == 0.0

    def test_result_keys(self):
        result = aggregate_personal_eoh_fulfilled([], population=100.0)
        for key in ("total_annual_personal_eoh_fulfilled", "per_capita_fulfilled",
                    "asset_count", "population"):
            assert key in result

    def test_asset_count_correct(self):
        assets = [self._water_asset(), self._water_asset()]
        result = aggregate_personal_eoh_fulfilled(assets, population=500.0)
        assert result["asset_count"] == 2


# ===========================================================================
# aggregate_eoh_eliminated
# ===========================================================================

class TestAggregateEohEliminated:

    def _asset(self, eoh_eliminated):
        a = make_asset("bridge-1", "stone_bridge", teh_value=1_000_000,
                       annual_eoh=5000, design_life=100)
        a["annual_eoh_eliminated"] = eoh_eliminated
        return a

    def test_single_asset_total(self):
        result = aggregate_eoh_eliminated([self._asset(3000.0)])
        assert result["total_eoh_eliminated"] == pytest.approx(3000.0)

    def test_multiple_assets_summed(self):
        assets = [self._asset(1000.0), self._asset(2000.0), self._asset(500.0)]
        result = aggregate_eoh_eliminated(assets)
        assert result["total_eoh_eliminated"] == pytest.approx(3500.0)

    def test_empty_fleet(self):
        result = aggregate_eoh_eliminated([])
        assert result["total_eoh_eliminated"] == pytest.approx(0.0)
        assert result["asset_count"] == 0

    def test_missing_field_treated_as_zero(self):
        asset = make_asset("bridge-1", "stone_bridge", teh_value=1_000_000,
                           annual_eoh=5000, design_life=100)
        result = aggregate_eoh_eliminated([asset])
        assert result["total_eoh_eliminated"] == pytest.approx(0.0)

    def test_asset_count_correct(self):
        assets = [self._asset(i * 100.0) for i in range(5)]
        result = aggregate_eoh_eliminated(assets)
        assert result["asset_count"] == 5


# ===========================================================================
# apply_birth_eoh
# ===========================================================================

class TestApplyBirthEoh:

    def _birth(self, pop=1000, eps=0.40):
        return birth_event(pop, eoh_ledger_total=1_000_000, epsilon=eps)

    def test_total_increases_by_added_eoh(self):
        birth = self._birth()
        result = apply_birth_eoh(birth, current_total_personal_eoh=500_000.0)
        expected = 500_000.0 + birth["added_eoh_per_year"]
        assert result["new_total_personal_eoh"] == pytest.approx(expected)

    def test_capacity_added_is_zero(self):
        result = apply_birth_eoh(self._birth(), current_total_personal_eoh=0.0)
        assert result["capacity_added"] == pytest.approx(0.0)

    def test_net_burden_equals_added_eoh(self):
        birth = self._birth()
        result = apply_birth_eoh(birth, current_total_personal_eoh=0.0)
        assert result["net_burden_increase"] == pytest.approx(result["added_eoh_per_year"])

    def test_new_population_passes_through(self):
        birth = self._birth(pop=999)
        result = apply_birth_eoh(birth, current_total_personal_eoh=0.0)
        assert result["new_population"] == pytest.approx(1000.0)

    def test_birth_always_increases_personal_eoh(self):
        birth = self._birth()
        result = apply_birth_eoh(birth, current_total_personal_eoh=100_000.0)
        assert result["new_total_personal_eoh"] > 100_000.0

    def test_result_keys(self):
        result = apply_birth_eoh(self._birth(), current_total_personal_eoh=0.0)
        for key in ("added_eoh_per_year", "new_total_personal_eoh",
                    "new_population", "capacity_added", "net_burden_increase"):
            assert key in result


# ===========================================================================
# estate_dissolution (D5)
# ===========================================================================

class TestEstateDissolution:

    def _state(self, teh_circ: float, pop: float = 1_000_000.0, eps: float = 0.40):
        return estate_dissolution(teh_circ, pop, eps)

    def test_zero_destruction_below_reserve(self):
        """Per-capita TEH below reserve → no excess → no destruction."""
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(0.40)
        teh_circ = reserve * 0.5 * 1_000_000
        result = self._state(teh_circ)
        assert result["teh_destroyed"] == 0.0
        assert result["teh_levied_to_trust"] == 0.0

    def test_positive_destruction_above_reserve(self):
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(0.40)
        teh_circ = reserve * 10.0 * 1_000_000
        result = self._state(teh_circ)
        assert result["teh_destroyed"] > 0.0
        assert result["teh_levied_to_trust"] > 0.0

    def test_fractions_sum_to_excess(self):
        """destroyed + levied + inherited = total_excess above reserve."""
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(0.40)
        per_capita = reserve * 5.0
        pop = 1_000_000.0
        result = estate_dissolution(per_capita * pop, pop, 0.40)

        deaths = pop * ANNUAL_DEATH_RATE
        total_excess = deaths * (per_capita - reserve)
        writedown_frac = 1.0 - ESTATE_INHERITANCE_FRACTION - ESTATE_LEVY_FRACTION

        assert abs(result["teh_destroyed"] - total_excess * writedown_frac) < 1.0
        assert abs(result["teh_levied_to_trust"] - total_excess * ESTATE_LEVY_FRACTION) < 1.0
        expected_inherited = (deaths * reserve) + (total_excess * ESTATE_INHERITANCE_FRACTION)
        assert abs(result["teh_inherited"] - expected_inherited) < 1.0

    def test_reserve_shrinks_with_epsilon(self):
        """As ε rises, basket price falls → reserve falls."""
        pop = 1_000_000.0
        fixed_per_capita = 50_000.0
        teh_circ = fixed_per_capita * pop

        reserves = [estate_dissolution(teh_circ, pop, e)["personal_reserve"]
                    for e in [0.10, 0.40, 0.70, 0.99]]
        for i in range(1, len(reserves)):
            assert reserves[i] <= reserves[i - 1] + 1e-6

    def test_destruction_increases_with_epsilon_for_fixed_holdings(self):
        """For fixed nominal savings, more is above the shrinking reserve at high ε."""
        pop = 1_000_000.0
        fixed_per_capita = 50_000.0
        teh_circ = fixed_per_capita * pop

        lo = estate_dissolution(teh_circ, pop, 0.40)
        hi = estate_dissolution(teh_circ, pop, 0.90)
        assert hi["teh_destroyed"] >= lo["teh_destroyed"] - 1e-6

    def test_death_rate_scales_destruction(self):
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(0.40)
        per_capita = reserve * 5.0
        pop = 1_000_000.0
        teh_circ = per_capita * pop

        r1 = estate_dissolution(teh_circ, pop, 0.40, annual_death_rate=0.01)
        r2 = estate_dissolution(teh_circ, pop, 0.40, annual_death_rate=0.02)
        assert abs(r2["teh_destroyed"] - 2.0 * r1["teh_destroyed"]) < 1.0

    def test_mechanism_label(self):
        result = self._state(0.0)
        assert result["mechanism"] == "D5_estate"

    def test_custom_fractions_respected(self):
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(0.40)
        per_capita = reserve * 4.0
        pop = 1_000_000.0
        result = estate_dissolution(
            per_capita * pop, pop, 0.40,
            inheritance_fraction=0.50,
            estate_levy_fraction=0.10,
        )
        deaths = pop * ANNUAL_DEATH_RATE
        excess = deaths * (per_capita - reserve)
        assert abs(result["teh_destroyed"] - excess * 0.40) < 1.0
        assert abs(result["teh_levied_to_trust"] - excess * 0.10) < 1.0
