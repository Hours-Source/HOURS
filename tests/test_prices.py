"""
Tests for hours_eoh.core.prices

Covers: teh_price, teh_price_trajectory, basket_price, purchasing_power,
floor_purchasing_power, floor_monotonicity_guard, purchasing_power_sweep,
domain_scarcity_multiplier, full_price_monotonicity_audit, cpi_goods_destruction.
"""

import math
import pytest

from hours_eoh.core.prices import (
    teh_price,
    teh_price_trajectory,
    basket_price,
    purchasing_power,
    floor_purchasing_power,
    floor_monotonicity_guard,
    purchasing_power_sweep,
    domain_scarcity_multiplier,
    full_price_monotonicity_audit,
    cpi_goods_destruction,
)
from hours_eoh.data import BASKET_EOH_CONTENT

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# teh_price
# ===========================================================================

class TestTehPrice:

    def test_price_falls_with_epsilon(self):
        """Prices fall monotonically as automation increases."""
        base_hours = 0.5  # 0.5 hours of human labor at ε=0
        p_0  = teh_price(base_hours, epsilon=0.0)
        p_40 = teh_price(base_hours, epsilon=0.40)
        p_90 = teh_price(base_hours, epsilon=0.90)
        assert p_0 > p_40 > p_90, (
            "Price must fall monotonically as automation increases"
        )

    def test_price_at_eps0_equals_labor_times_multiplier(self):
        base_hours = 2.0
        multiplier = 2.10
        price = teh_price(base_hours, epsilon=0.0, mean_multiplier=multiplier)
        assert price == pytest.approx(base_hours * multiplier)

    def test_price_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            price = teh_price(1.0, epsilon=eps)
            assert price > 0, f"Price must be positive at ε={eps}"
            assert math.isfinite(price)

    def test_price_floor_prevents_zero(self):
        """Even at ε=0.99, goods have a non-zero price (irreducible labor)."""
        price = teh_price(1.0, epsilon=0.99)
        assert price > 0.01

    def test_mission_statement_bread_example(self):
        """
        Example: bread requires 0.1 hours at ε=0. At ε=0.80 most is automated.
        Price should be substantially lower at ε=0.80 than at ε=0.
        """
        p_0  = teh_price(0.1, epsilon=0.0,  mean_multiplier=2.0)
        p_80 = teh_price(0.1, epsilon=0.80, mean_multiplier=2.0)
        assert p_0 == pytest.approx(0.2)
        assert p_80 < p_0 * 0.5, "At 80% automation, price should be less than half base"

    def test_price_trajectory_monotonically_decreasing(self):
        traj = teh_price_trajectory(1.0)
        prices = [p["price_teh"] for p in traj]
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1] - 1e-10, (
                f"Price trajectory must be non-increasing; prices[{i}]={prices[i]:.4f}, "
                f"prices[{i+1}]={prices[i+1]:.4f}"
            )


# ===========================================================================
# basket_price
# ===========================================================================

class TestBasketPrice:

    def test_basket_price_at_eps0_equals_baseline(self):
        baseline = 1020.0
        bp = basket_price(0.0, baseline_cost_teh=baseline)
        assert bp == pytest.approx(baseline, rel=1e-4)

    def test_basket_price_falls_with_epsilon(self):
        """Basket price is monotonically decreasing with ε."""
        bp_0  = basket_price(0.0)
        bp_40 = basket_price(0.40)
        bp_90 = basket_price(0.90)
        bp_99 = basket_price(0.99)
        assert bp_0 > bp_40 > bp_90 > bp_99

    def test_basket_price_always_positive(self):
        for eps in KEY_EPSILONS:
            bp = basket_price(eps)
            assert bp > 0, f"Basket price must be positive at ε={eps}"

    def test_basket_price_rejects_bad_weights(self):
        with pytest.raises(ValueError):
            basket_price(0.40, goods_weight=0.5, services_weight=0.6)

    def test_services_price_falls_slower_than_goods(self):
        """Services resist automation more than goods — reflect in basket."""
        bp_all_goods    = basket_price(0.80, goods_weight=1.0, services_weight=0.0)
        bp_all_services = basket_price(0.80, goods_weight=0.0, services_weight=1.0)
        bp_all_goods_0    = basket_price(0.0,  goods_weight=1.0, services_weight=0.0)
        bp_all_services_0 = basket_price(0.0,  goods_weight=0.0, services_weight=1.0)

        goods_decline_pct    = 1.0 - bp_all_goods    / bp_all_goods_0
        services_decline_pct = 1.0 - bp_all_services / bp_all_services_0

        assert goods_decline_pct > services_decline_pct, (
            "Goods prices should fall faster than services prices with automation"
        )


# ===========================================================================
# purchasing_power / floor_purchasing_power
# ===========================================================================

class TestPurchasingPower:

    def test_purchasing_power_rises_with_epsilon(self):
        """Sufficiency guarantee purchasing power rises with ε (Principle 5)."""
        pp_0  = purchasing_power(1020.0, epsilon=0.0)
        pp_40 = purchasing_power(1020.0, epsilon=0.40)
        pp_90 = purchasing_power(1020.0, epsilon=0.90)
        assert pp_0["pp_index"] < pp_40["pp_index"] < pp_90["pp_index"], (
            "Purchasing power must rise with automation — Principle 5"
        )

    def test_pp_index_one_at_eps0(self):
        """At ε=0: purchasing power index = 1.0 (baseline)."""
        pp = purchasing_power(1020.0, epsilon=0.0, baseline_basket_cost=1020.0)
        assert pp["pp_index"] == pytest.approx(1.0, rel=1e-4)

    def test_pp_index_above_one_at_positive_epsilon(self):
        for eps in [0.40, 0.90, 0.99]:
            pp = purchasing_power(1020.0, epsilon=eps)
            assert pp["pp_index"] > 1.0, (
                f"PP index must be > 1.0 at ε={eps} (same nominal TEH buys more)"
            )

    def test_floor_purchasing_power_never_declines(self):
        """Principle 5: floor PP is non-decreasing across ε range."""
        prev_pp = None
        for i in range(20):
            eps = i * 0.99 / 19
            result = floor_purchasing_power(1020.0, epsilon=eps)
            if prev_pp is not None:
                assert result["pp_index"] >= prev_pp - 1e-6, (
                    f"Floor PP must not decline: eps={eps:.2f}, "
                    f"current={result['pp_index']:.4f} < prev={prev_pp:.4f}"
                )
            prev_pp = result["pp_index"]

    def test_floor_monotonicity_guard_passes(self):
        """Principle 5 verified by structural monitor."""
        result = floor_monotonicity_guard(floor_teh=1020.0)
        assert result["passes"] is True, (
            f"Floor monotonicity guard must pass. Violations: {result['violations']}"
        )
        assert result["status"] == "OK"

    def test_floor_pp_at_eps90_substantially_higher_than_eps0(self):
        """Near post-scarcity: floor should buy materially more than at ε=0."""
        pp_0  = floor_purchasing_power(1020.0, epsilon=0.0)
        pp_90 = floor_purchasing_power(1020.0, epsilon=0.90)
        assert pp_90["pp_index"] > pp_0["pp_index"] * 1.5, (
            "At ε=0.90, floor should buy at least 50% more than at ε=0"
        )

    def test_floor_pp_gain_pct_positive(self):
        for eps in [0.40, 0.90, 0.99]:
            result = floor_purchasing_power(1020.0, epsilon=eps)
            assert result["pp_gain_pct"] > 0.0

    def test_pp_sweep_all_positive(self):
        sweep = purchasing_power_sweep(1020.0)
        for point in sweep:
            assert point["pp_index"] > 0
            assert math.isfinite(point["baskets_afforded"])


# ===========================================================================
# domain_scarcity_multiplier
# ===========================================================================

class TestDomainScarcityMultiplier:

    def test_balanced_returns_one(self):
        assert domain_scarcity_multiplier(1000.0, 1000.0) == pytest.approx(1.0)

    def test_surplus_capacity_returns_one(self):
        assert domain_scarcity_multiplier(500.0, 1000.0) == pytest.approx(1.0)

    def test_two_x_overdemand_returns_max_scarcity(self):
        result = domain_scarcity_multiplier(2000.0, 1000.0, max_scarcity=2.0)
        assert result == pytest.approx(2.0)

    def test_partial_overdemand_interpolates(self):
        # demand/capacity = 1.5 → midpoint between 1.0 and max_scarcity=2.0
        result = domain_scarcity_multiplier(1500.0, 1000.0, max_scarcity=2.0)
        assert result == pytest.approx(1.5)

    def test_zero_capacity_returns_one(self):
        assert domain_scarcity_multiplier(1000.0, 0.0) == pytest.approx(1.0)

    def test_zero_demand_returns_one(self):
        assert domain_scarcity_multiplier(0.0, 1000.0) == pytest.approx(1.0)

    def test_very_high_overdemand_capped_at_max(self):
        result = domain_scarcity_multiplier(10_000.0, 1000.0, max_scarcity=3.0)
        assert result == pytest.approx(3.0)


# ===========================================================================
# teh_price with scarcity_factor
# ===========================================================================

class TestTehPriceScarcity:

    def test_no_scarcity_same_as_default(self):
        base     = teh_price(10.0, epsilon=0.40)
        explicit = teh_price(10.0, epsilon=0.40, scarcity_factor=1.0)
        assert base == pytest.approx(explicit)

    def test_scarcity_doubles_price(self):
        base   = teh_price(10.0, epsilon=0.40)
        scarce = teh_price(10.0, epsilon=0.40, scarcity_factor=2.0)
        assert scarce == pytest.approx(base * 2.0)

    def test_scarcity_from_multiplier_function(self):
        multiplier = domain_scarcity_multiplier(1500.0, 1000.0, max_scarcity=2.0)
        price      = teh_price(10.0, epsilon=0.40, scarcity_factor=multiplier)
        assert price > teh_price(10.0, epsilon=0.40)


# ===========================================================================
# full_price_monotonicity_audit (Principle 5 structural monitor)
# ===========================================================================

class TestFullPriceMonotonicityAudit:
    """All price components must satisfy Principle 5 with default parameters."""

    def test_default_params_passes(self):
        """Default price model must satisfy Principle 5 for all components."""
        result = full_price_monotonicity_audit()
        assert result["passes"] is True
        assert result["status"] == "OK"
        assert len(result["violation_summary"]) == 0

    def test_return_keys_present(self):
        result = full_price_monotonicity_audit()
        for key in ("passes", "basket_price", "goods_price", "floor_pp",
                    "status", "violation_summary"):
            assert key in result, f"Missing key: {key}"

    def test_component_keys_present(self):
        result = full_price_monotonicity_audit()
        for comp in ("basket_price", "goods_price", "floor_pp"):
            assert "passes" in result[comp]
            assert "violations" in result[comp]
            assert "range" in result[comp]

    def test_basket_price_non_increasing(self):
        """basket_price component must pass (price falls with ε)."""
        result = full_price_monotonicity_audit()
        assert result["basket_price"]["passes"] is True

    def test_goods_price_non_increasing(self):
        """goods_price component must pass."""
        result = full_price_monotonicity_audit()
        assert result["goods_price"]["passes"] is True

    def test_floor_pp_non_decreasing(self):
        """floor purchasing power must pass (pp rises with ε)."""
        result = full_price_monotonicity_audit()
        assert result["floor_pp"]["passes"] is True

    def test_basket_price_range_bounded(self):
        """basket_price range must be within (0, baseline_cost]."""
        result = full_price_monotonicity_audit(baseline_cost_teh=1000.0)
        lo, hi = result["basket_price"]["range"]
        assert lo > 0.0
        assert hi <= 1000.0 + 1e-6

    def test_floor_pp_monotone_range(self):
        """floor_pp range[0] <= range[1] (min pp <= max pp)."""
        result = full_price_monotonicity_audit()
        lo, hi = result["floor_pp"]["range"]
        assert lo <= hi


# ===========================================================================
# cpi_goods_destruction (D4)
# ===========================================================================

class TestCpiGoodsDestruction:

    def test_zero_fulfillment_produces_zero_destruction(self):
        result = cpi_goods_destruction(0.0, 0.40)
        assert result["teh_destroyed"] == 0.0
        assert result["baskets_delivered"] == 0.0

    def test_destruction_proportional_to_capital_eoh_fulfilled(self):
        low  = cpi_goods_destruction(1_000.0, 0.40)
        high = cpi_goods_destruction(2_000.0, 0.40)
        assert abs(high["teh_destroyed"] - 2.0 * low["teh_destroyed"]) < 1e-6

    def test_destruction_equals_baskets_times_price(self):
        eoh_fulfilled = 15_000.0
        eps = 0.40
        result = cpi_goods_destruction(eoh_fulfilled, eps)
        expected_baskets = eoh_fulfilled / BASKET_EOH_CONTENT
        expected_teh     = expected_baskets * basket_price(eps)
        assert abs(result["teh_destroyed"] - expected_teh) < 1e-6
        assert abs(result["baskets_delivered"] - expected_baskets) < 1e-6

    def test_destruction_falls_with_epsilon(self):
        """As ε rises, basket price falls → less TEH destroyed per unit of EOH delivered."""
        eoh_fulfilled = 100_000.0
        vals = [cpi_goods_destruction(eoh_fulfilled, e)["teh_destroyed"]
                for e in [0.0, 0.20, 0.40, 0.60, 0.80, 0.99]]
        for i in range(1, len(vals)):
            assert vals[i] <= vals[i - 1] + 1e-6, \
                f"D4 destruction should be non-increasing with ε; violated at index {i}"

    def test_destruction_near_zero_at_high_epsilon(self):
        """At ε=0.99, basket price is near floor → much less TEH destroyed than at ε≈0."""
        result_low  = cpi_goods_destruction(100_000.0, 0.01)
        result_high = cpi_goods_destruction(100_000.0, 0.99)
        assert result_high["teh_destroyed"] < 0.25 * result_low["teh_destroyed"]

    def test_mechanism_label(self):
        result = cpi_goods_destruction(1000.0, 0.40)
        assert result["mechanism"] == "D4_cpi"
