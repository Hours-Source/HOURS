"""
Tests for hours_eoh.core.prices

Covers: teh_price, teh_price_trajectory, basket_price, purchasing_power,
floor_purchasing_power, floor_monotonicity_guard, purchasing_power_sweep,
domain_scarcity_multiplier, full_price_monotonicity_audit, cpi_goods_destruction.
"""

import math
import pytest

from hours_eoh.data import BASKET_GOODS_WEIGHT, BASKET_SERVICES_WEIGHT
from hours_eoh.core.prices import (
    GOODS_PRICE_FLOOR,
    SERVICES_PRICE_FLOOR,
    teh_price,
    teh_price_trajectory,
    basket_price,
    floor_price,
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


# ===========================================================================
# floor_price (Workstream C — price-as-floor reframing)
# ===========================================================================

class TestFloorPrice:

    def test_zero_premium_equals_basket_price_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            assert floor_price(eps) == pytest.approx(basket_price(eps), rel=1e-9)

    def test_premium_adds_to_floor(self):
        for eps in KEY_EPSILONS:
            fp = floor_price(eps, market_premium=50.0)
            assert fp == pytest.approx(basket_price(eps) + 50.0, rel=1e-9)

    def test_floor_component_falls_monotonically(self):
        vals = [floor_price(eps, market_premium=0.0) for eps in KEY_EPSILONS]
        for lo, hi in zip(vals, vals[1:]):
            assert hi < lo, f"floor must fall with ε: {lo} → {hi}"

    def test_negative_premium_raises(self):
        with pytest.raises(ValueError, match="market_premium"):
            floor_price(0.40, market_premium=-1.0)

    def test_large_premium_dominated_by_premium(self):
        fp = floor_price(0.40, market_premium=10_000.0)
        assert fp > 10_000.0

    def test_arc_arc_behavior(self):
        for eps in KEY_EPSILONS:
            assert floor_price(eps) > 0



class TestThePriceFloorsAreReached:
    """
    THE ASYMPTOTES THE FLOORS NAME (pinned 2026-08-27).

    `GOODS_PRICE_FLOOR` and `SERVICES_PRICE_FLOOR` are the ε→1 limits of the two
    price ratios — the whole content of "prices collapse toward a floor as
    automation rises, and services collapse less because they stay
    labour-bearing". A +7% perturbation of either moved shipped outputs and NOT
    ONE TEST FAILED: failure mode 1 on the constants that decide where the price
    arc lands.

    They are shadow constants — declared in `core/prices.py`, not `data.py` — so
    the provenance gate cannot see them either. A 2026-08-27 sweep found 34 of 63
    shadow constants unpinned against 0 of 232 in `data.py`; the two gaps
    compound, and these two were the ones demonstrably moving output.

    `basket_price` returns a scalar cost, so each ratio is isolated by putting
    all the weight on one side of the basket.

    Pinned as ASYMPTOTIC BEHAVIOUR and ORDERING, not as levels — the levels are
    calibration and will move.
    """

    BASE = 120.0

    def _goods(self, eps):
        return basket_price(eps, self.BASE, goods_weight=1.0,
                            services_weight=0.0) / self.BASE

    def _services(self, eps):
        return basket_price(eps, self.BASE, goods_weight=0.0,
                            services_weight=1.0) / self.BASE

    def test_both_ratios_start_at_unity(self):
        assert self._goods(0.0) == pytest.approx(1.0, rel=1e-9)
        assert self._services(0.0) == pytest.approx(1.0, rel=1e-9)

    def test_goods_ratio_lands_on_its_floor(self):
        """
        Asserted at ε=1.0 where the limit is EXACT. The first version used
        ε=0.99 with `abs=0.02`, which on a floor of 0.05 tolerates a 40% move —
        a fresh mutation sweep on 2026-08-28 still reported this constant
        unpinned at +7% because of it. A tolerance wide enough to absorb the
        arc's own curvature is wide enough to absorb the constant.
        """
        assert self._goods(1.0) == pytest.approx(GOODS_PRICE_FLOOR, rel=1e-12)
        assert self._goods(0.99) >= GOODS_PRICE_FLOOR - 1e-12, (
            "a ratio may never go below its floor"
        )
        assert self._goods(0.99) == pytest.approx(GOODS_PRICE_FLOOR, rel=0.25), (
            "goods is linear, so it should be near its floor by ε=0.99"
        )

    def test_services_ratio_reaches_its_floor_only_in_the_limit(self):
        """
        AND THE CONVERGENCE IS SLOW, which is the finding rather than a tolerance
        to widen. `_SERVICES_PRICE_DECLINE_EXPONENT` = 0.35 gives
        (1−ε)**0.35, so at ε=0.99 the services ratio is still **0.360 — 1.8× its
        own floor** — and only touches 0.20 as ε→1. Goods, being linear, sit on
        their floor at 0.99 already.

        I first wrote this test asserting services was AT its floor by ε=0.99,
        which is what the phrase "prices collapse" invites you to assume. It
        fails, and it should: the two ratios reach their floors at completely
        different rates, and that difference IS the labour-bearing claim. Pinning
        the wrong version would have baked in a misreading of the model.

        This also pins `_SERVICES_PRICE_DECLINE_EXPONENT`, a third unpinned
        shadow constant in this module.
        """
        assert self._services(0.99) >= SERVICES_PRICE_FLOOR - 1e-12
        assert self._services(0.99) == pytest.approx(0.360, abs=0.01), (
            "services should still be well above its floor at ε=0.99"
        )
        assert self._services(0.99) > 1.5 * SERVICES_PRICE_FLOOR
        # the limit itself, asserted where it is EXACT
        assert self._services(1.0) == pytest.approx(SERVICES_PRICE_FLOOR, rel=1e-12)
        # goods, being linear, is already there
        assert self._goods(0.99) == pytest.approx(GOODS_PRICE_FLOOR, abs=0.02)

    def test_services_stay_dearer_than_goods_across_the_arc(self):
        """
        THE CLAIM THE TWO FLOORS EXIST TO MAKE. Services are labour-bearing, so
        automation cannot collapse them as far. If this inverts, the floors have
        swapped meaning and the arc says the opposite of the theory.
        """
        for eps in (0.2, 0.4, 0.7, 0.9, 0.99):
            assert self._services(eps) > self._goods(eps), (
                f"services must not fall below goods at ε={eps}"
            )

    def test_both_ratios_fall_monotonically(self):
        arc = [0.0, 0.2, 0.4, 0.6, 0.8, 0.99]
        g = [self._goods(e) for e in arc]
        s = [self._services(e) for e in arc]
        assert g == sorted(g, reverse=True), f"goods ratio must not rise with ε: {g}"
        assert s == sorted(s, reverse=True), f"services ratio must not rise with ε: {s}"
        assert all(0.0 < x <= 1.0 for x in g + s)


class TestTheBasketWeightsPartition:
    """
    `BASKET_GOODS_WEIGHT` / `BASKET_SERVICES_WEIGHT`, migrated and pinned
    (2026-08-28). Both were shadow constants in `core/prices.py`.

    They are two INDEPENDENT constants that must sum to 1.0, so this is a real
    check rather than an identity — nothing in the code normalises them, and a
    pair summing to 0.9 would silently shrink the whole basket.
    """

    def test_the_weights_partition_the_basket(self):
        assert BASKET_GOODS_WEIGHT + BASKET_SERVICES_WEIGHT == pytest.approx(1.0, rel=1e-12)
        assert BASKET_GOODS_WEIGHT > 0.0 and BASKET_SERVICES_WEIGHT > 0.0

    def test_the_shipped_weights_are_what_basket_price_uses(self):
        """Binds the constants to the behaviour: the default basket must equal
        the weighted combination of its two halves."""
        base = 120.0
        for eps in (0.0, 0.40, 0.99):
            goods = basket_price(eps, base, goods_weight=1.0, services_weight=0.0)
            services = basket_price(eps, base, goods_weight=0.0, services_weight=1.0)
            combined = BASKET_GOODS_WEIGHT * goods + BASKET_SERVICES_WEIGHT * services
            assert basket_price(eps, base) == pytest.approx(combined, rel=1e-9)
