"""
Tests for hours_eoh.core.eoh_generation

Covers: personal_eoh, infrastructure_eoh, ecological_eoh, knowledge_eoh,
total_eoh, ecological_eoh_breakdown, effective_capital_from_stock,
domain_labor_requirements, epsilon_delta_sensitivity, eoh_to_essential_domains.
"""

import math
import pytest

from hours_eoh.core.eoh_generation import (
    personal_base_for,
    knowledge_eoh_breakdown,
    personal_eoh,
    infrastructure_eoh,
    ecological_eoh,
    knowledge_eoh,
    total_eoh,
    effective_capital_from_stock,
    ecological_eoh_breakdown,
    domain_labor_requirements,
    epsilon_delta_sensitivity,
    eoh_to_essential_domains,
)
from hours_eoh.data import (
    ECOLOGICAL_SPIKE_INTENSITY,
    ECOLOGICAL_THRESHOLD,
    ECOLOGICAL_BASE_RATE,
    ECOLOGICAL_INTENSITY_BASE,
    LAND_HECTARES_PER_CAPITA,
    ESSENTIAL_DOMAINS,
    KNOWLEDGE_EOH_BASE,
    KNOWLEDGE_REFERENCE_POPULATION,
    SKILL_DECAY_RATE,
    SKILL_TRANSMISSION_RATE,
    US_MAINLAND_HECTARES,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]
POP = 1_000_000
CAPITAL = 2_000_000_000.0


# ===========================================================================
# personal_eoh
# ===========================================================================

class TestPersonalEoh:

    def test_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = personal_eoh(POP, epsilon=eps)
            assert result > 0, f"personal_eoh should be positive at ε={eps}"
            assert math.isfinite(result), f"personal_eoh should be finite at ε={eps}"

    def test_scales_with_population(self):
        eoh1 = personal_eoh(POP, epsilon=0.40)
        eoh2 = personal_eoh(2 * POP, epsilon=0.40)
        assert eoh2 > eoh1, "Personal EOH should scale with population"
        # Roughly proportional (not exact due to age-distribution shift)
        assert 1.8 < eoh2 / eoh1 < 2.2

    def test_weighted_by_age(self):
        # A population of all elderly should generate more EOH than all working-age
        elderly_dist = {"elderly": 1.0, "infant": 0.0, "child": 0.0, "working_age": 0.0}
        working_dist = {"elderly": 0.0, "infant": 0.0, "child": 0.0, "working_age": 1.0}
        eoh_elderly  = personal_eoh(POP, age_distribution=elderly_dist, epsilon=0.40)
        eoh_working  = personal_eoh(POP, age_distribution=working_dist, epsilon=0.40)
        assert eoh_elderly > eoh_working, (
            "Elderly population should generate more personal EOH than working-age"
        )


# ===========================================================================
# infrastructure_eoh
# ===========================================================================

class TestInfrastructureEoh:

    def test_increases_with_capital_stock(self):
        """Total EOH increases with capital stock size."""
        eoh_small = infrastructure_eoh(CAPITAL,       epsilon=0.40)
        eoh_large = infrastructure_eoh(CAPITAL * 3.0, epsilon=0.40)
        assert eoh_large > eoh_small, (
            "Infrastructure EOH must increase with capital stock size"
        )

    def test_increases_with_age(self):
        eoh_new = infrastructure_eoh(CAPITAL, capital_age_ratio=0.0, epsilon=0.40)
        eoh_old = infrastructure_eoh(CAPITAL, capital_age_ratio=1.0, epsilon=0.40)
        assert eoh_old > eoh_new, "Older capital stock should generate more EOH"

    def test_grows_with_epsilon(self):
        """Higher ε → more capital investment → more infrastructure EOH."""
        eoh_0  = infrastructure_eoh(CAPITAL, epsilon=0.0)
        eoh_90 = infrastructure_eoh(CAPITAL, epsilon=0.90)
        assert eoh_90 > eoh_0, (
            "Infrastructure EOH should grow with ε (automation enables more capital)"
        )


# ===========================================================================
# ecological_eoh
# ===========================================================================

class TestEcologicalEoh:

    def test_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = ecological_eoh(0.70, epsilon=eps)
            assert result > 0
            assert math.isfinite(result)

    def test_nonlinear_spike_below_threshold(self):
        """EOH compounding is nonlinear, not exponential."""
        # At health=0.70 (above threshold=0.40): no spike
        eoh_above = ecological_eoh(0.70, threshold=0.40)
        # At health=0.20 (below threshold): spike should be significant
        eoh_below = ecological_eoh(0.20, threshold=0.40)
        # Below-threshold EOH should be disproportionately higher
        assert eoh_below > eoh_above * 3.0, (
            "Ecological EOH should spike nonlinearly below threshold"
        )

    def test_deferred_visibility_grows_with_epsilon(self):
        """More deferred obligations visible at higher ε (better monitoring)."""
        eoh_lo_eps = ecological_eoh(0.70, epsilon=0.0,  deferred=1_000_000.0)
        eoh_hi_eps = ecological_eoh(0.70, epsilon=0.90, deferred=1_000_000.0)
        assert eoh_hi_eps > eoh_lo_eps, (
            "Deferred ecological EOH should be more visible at higher ε"
        )


# ===========================================================================
# knowledge_eoh
# ===========================================================================

class TestKnowledgeEoh:

    def test_grows_with_epsilon(self):
        """Knowledge EOH becomes dominant at high ε."""
        eoh_0  = knowledge_eoh(1.0, epsilon=0.0)
        eoh_40 = knowledge_eoh(1.0, epsilon=0.40)
        eoh_90 = knowledge_eoh(1.0, epsilon=0.90)
        assert eoh_0 < eoh_40 < eoh_90, (
            "Knowledge EOH must grow monotonically with ε"
        )

    def test_finite_at_all_epsilons(self):
        for eps in KEY_EPSILONS:
            result = knowledge_eoh(1.0, epsilon=eps)
            assert math.isfinite(result), f"knowledge_eoh must be finite at ε={eps}"
            assert result > 0


class TestKnowledgePopulationScaling:
    """
    Block K-I: knowledge EOH was population-INVARIANT — the same absolute number
    at 1M and at 300M — so the domain's share of total EOH fell as 1/population
    while every other domain scaled. These tests pin the fix AND pin that the
    fix moved no numbers at the default population.
    """

    def test_default_population_arc_is_pinned(self):
        """
        Values at the reference population, after two adoptions. K-I moved
        NOTHING here (10,000 / 112,240 / 973,251.19); K-IV adopted the measured
        base and the transmission renewal rate (uniform 1,225×); the Finding-E
        re-anchor to the ε_ref FIXED POINT then took 0.779× off that, giving a
        net 954.91× against pre-K-IV.
        """
        assert knowledge_eoh(1.0, epsilon=0.0)  == pytest.approx(1.39629894e7, rel=1e-6)
        assert knowledge_eoh(1.0, epsilon=0.40) == pytest.approx(1.56720600e8, rel=1e-6)
        assert knowledge_eoh(1.0, epsilon=0.99) == pytest.approx(1.35895000e9, rel=1e-6)

    def test_adoption_moved_every_arc_point_by_the_same_factor(self):
        """The adoption rescales; it does not reshape. Guards against a base
        change silently altering the arc's SHAPE as well as its level. The
        factor is 1,394.45× once the working life was measured (954.91×
        post-Finding-E, 1,225.27× at the K-IV anchor); that it stays UNIFORM
        across the arc is what this test is for."""
        for eps, pre in ((0.0, 10_000.0), (0.40, 112_240.0), (0.99, 973_251.19)):
            assert knowledge_eoh(1.0, epsilon=eps) / pre == pytest.approx(1396.29890, rel=1e-3)

    def test_scales_linearly_with_population(self):
        base = knowledge_eoh(1.0, epsilon=0.40)
        for factor in (0.5, 2.0, 300.0):
            scaled = knowledge_eoh(
                1.0, epsilon=0.40,
                population=KNOWLEDGE_REFERENCE_POPULATION * factor,
            )
            assert scaled == pytest.approx(base * factor)

    def test_per_capita_is_population_invariant_across_arc(self):
        """The property that was broken: h/person/yr must not depend on N."""
        for eps in KEY_EPSILONS:
            per_capita = {
                pop: total_eoh(epsilon=eps, population=pop)["knowledge"] / pop
                for pop in (1e6, 2e6, 3e8)
            }
            values = list(per_capita.values())
            assert values[0] == pytest.approx(values[1]), (
                f"knowledge h/person/yr must not vary with population at ε={eps}; "
                f"got {per_capita}"
            )
            assert values[0] == pytest.approx(values[2])

    def test_zero_population_yields_zero_obligation(self):
        assert knowledge_eoh(1.0, epsilon=0.40, population=0.0) == 0.0

    def test_negative_population_rejected(self):
        with pytest.raises(ValueError, match="population must be non-negative"):
            knowledge_eoh(1.0, epsilon=0.40, population=-1.0)

    def test_breakdown_forwards_population(self):
        """The civilisational/apparatus SPLIT is a ratio — invariant — but the
        components must scale."""
        one = knowledge_eoh_breakdown(1.0, epsilon=0.40)
        two = knowledge_eoh_breakdown(
            1.0, epsilon=0.40,
            population=KNOWLEDGE_REFERENCE_POPULATION * 2.0,
        )
        assert two["total"] == pytest.approx(one["total"] * 2.0)
        assert two["apparatus"] == pytest.approx(one["apparatus"] * 2.0)
        assert two["apparatus_fraction"] == pytest.approx(one["apparatus_fraction"])


class TestKnowledgeStockFlowSemantics:
    """
    Block K-I: `base_rate` is a STOCK, not the annual figure. Pinned because the
    O*NET closure route (Block K-II) depends on this reading — it supplies a
    training stock and a renewal rate, which is the same shape.
    """

    def test_base_rate_is_not_the_epsilon_zero_answer(self):
        """The mislabel that motivated the correction: base != K(0)."""
        k0 = knowledge_eoh(1.0, epsilon=0.0)
        assert k0 != pytest.approx(KNOWLEDGE_EOH_BASE)
        assert k0 == pytest.approx(KNOWLEDGE_EOH_BASE * SKILL_TRANSMISSION_RATE)

    def test_obligation_is_linear_in_the_renewal_rate(self):
        """Stock × rate: doubling the renewal rate doubles the annual flow."""
        single = knowledge_eoh(1.0, SKILL_TRANSMISSION_RATE, epsilon=0.40)
        double = knowledge_eoh(1.0, SKILL_TRANSMISSION_RATE * 2.0, epsilon=0.40)
        assert double == pytest.approx(single * 2.0)

    def test_default_rate_is_bound_not_literal(self):
        """Repricing hazard: the default must track the named constant, and
        must be the ADOPTED rate rather than the deprecated placeholder."""
        assert knowledge_eoh(1.0, epsilon=0.40) == pytest.approx(
            knowledge_eoh(1.0, SKILL_TRANSMISSION_RATE, epsilon=0.40)
        )
        assert knowledge_eoh(1.0, epsilon=0.40) != pytest.approx(
            knowledge_eoh(1.0, SKILL_DECAY_RATE, epsilon=0.40)
        )


# ===========================================================================
# total_eoh
# ===========================================================================

class TestTotalEoh:

    def test_returns_all_domains(self):
        result = total_eoh(epsilon=0.40)
        assert "personal" in result
        assert "infrastructure" in result
        assert "ecological" in result
        assert "knowledge" in result
        assert "total" in result
        assert result["total"] == pytest.approx(
            result["personal"] + result["infrastructure"]
            + result["ecological"] + result["knowledge"]
        )

    def test_finite_positive_at_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = total_eoh(eps)
            assert result["total"] > 0, f"total_eoh must be positive at ε={eps}"
            assert math.isfinite(result["total"]), f"total_eoh must be finite at ε={eps}"

    def test_no_gap_unchanged(self):
        baseline = total_eoh(0.40)
        with_gap = total_eoh(0.40, competency_gap_factor=0.0)
        assert with_gap["knowledge"] == pytest.approx(baseline["knowledge"])

    def test_gap_increases_knowledge_eoh(self):
        baseline = total_eoh(0.40)
        with_gap = total_eoh(0.40, competency_gap_factor=0.50)
        assert with_gap["knowledge"] > baseline["knowledge"]
        assert with_gap["knowledge"] == pytest.approx(baseline["knowledge"] * 1.50, rel=1e-9)

    def test_gap_does_not_affect_personal(self):
        baseline = total_eoh(0.40)
        with_gap = total_eoh(0.40, competency_gap_factor=1.0)
        assert with_gap["personal"] == pytest.approx(baseline["personal"])

    def test_gap_factor_in_return_dict(self):
        result = total_eoh(0.40, competency_gap_factor=0.25)
        assert result["competency_gap_factor"] == pytest.approx(0.25)


# ===========================================================================
# effective_capital_from_stock
# ===========================================================================

class TestEffectiveCapitalFromStock:

    def test_at_eps0_returns_base(self):
        assert effective_capital_from_stock(1_000_000.0, 0.0) == pytest.approx(1_000_000.0)

    def test_grows_with_epsilon(self):
        base  = effective_capital_from_stock(1_000_000.0, 0.0)
        high  = effective_capital_from_stock(1_000_000.0, 0.90)
        assert high > base

    def test_matches_infrastructure_eoh_internal_scaling(self):
        capital = 2_000_000_000.0
        eps = 0.50
        age = 0.50
        rate = 0.025
        age_factor = 1.0 + (2.0 - 1.0) * age
        expected = effective_capital_from_stock(capital, eps) * rate * age_factor
        actual   = infrastructure_eoh(capital, age, eps, rate, 2.0)
        assert actual == pytest.approx(expected)


# ===========================================================================
# ecological_eoh_breakdown
# ===========================================================================

class TestEcologicalEohBreakdown:

    def test_total_matches_ecological_eoh(self):
        for health in (0.90, 0.50, 0.30):
            breakdown = ecological_eoh_breakdown(health, epsilon=0.40, deferred=10000.0)
            total_fn  = ecological_eoh(health, epsilon=0.40, deferred=10000.0)
            assert breakdown["total"] == pytest.approx(total_fn, rel=1e-9)

    def test_spike_zero_above_threshold(self):
        breakdown = ecological_eoh_breakdown(0.80, threshold=0.40)
        assert breakdown["spike"] == pytest.approx(0.0)
        assert breakdown["in_threshold_spike"] is False

    def test_spike_nonzero_below_threshold(self):
        breakdown = ecological_eoh_breakdown(0.20, threshold=0.40)
        assert breakdown["spike"] > 0.0
        assert breakdown["in_threshold_spike"] is True

    def test_visible_deferred_increases_with_epsilon(self):
        low  = ecological_eoh_breakdown(0.70, epsilon=0.0, deferred=100_000.0)
        high = ecological_eoh_breakdown(0.70, epsilon=0.90, deferred=100_000.0)
        assert high["visible_deferred"] > low["visible_deferred"]

    def test_result_keys(self):
        result = ecological_eoh_breakdown(0.70)
        for key in ("baseline", "spike", "visible_deferred", "total",
                    "monitoring_factor", "in_threshold_spike"):
            assert key in result


# ===========================================================================
# domain_labor_requirements
# ===========================================================================

class TestDomainLaborRequirements:
    """domain_labor_requirements() must translate EOH to headcount per domain."""

    def _eoh_dict(self, eps=0.40):
        return total_eoh(eps)

    def test_return_keys_present(self):
        eoh = self._eoh_dict()
        result = domain_labor_requirements(eoh, epsilon=0.40)
        assert "epsilon" in result
        assert "human_fraction" in result
        assert "hours_per_worker" in result
        assert "domains" in result
        assert "total_workers_needed" in result

    def test_domain_keys_match_input(self):
        eoh = {"personal": 1e9, "infrastructure": 5e8, "ecological": 2e8, "knowledge": 1e8}
        result = domain_labor_requirements(eoh, epsilon=0.40)
        assert set(result["domains"].keys()) == {"personal", "infrastructure", "ecological", "knowledge"}

    def test_human_fraction_correct(self):
        result = domain_labor_requirements(self._eoh_dict(), epsilon=0.60)
        assert result["human_fraction"] == pytest.approx(0.40)

    def test_workers_scale_with_eoh(self):
        """Doubling EOH must double workers needed."""
        base = domain_labor_requirements({"personal": 1_000_000.0}, epsilon=0.40)
        double = domain_labor_requirements({"personal": 2_000_000.0}, epsilon=0.40)
        assert double["total_workers_needed"] == pytest.approx(
            base["total_workers_needed"] * 2.0, rel=1e-6
        )

    def test_workers_decrease_with_higher_epsilon(self):
        """More automation → fewer human workers needed."""
        low  = domain_labor_requirements({"personal": 1e9}, epsilon=0.20)
        high = domain_labor_requirements({"personal": 1e9}, epsilon=0.80)
        assert high["total_workers_needed"] < low["total_workers_needed"]

    def test_workers_zero_at_eps_one(self):
        """At ε=1.0 (full automation), zero human workers needed."""
        result = domain_labor_requirements({"personal": 1e9}, epsilon=1.0)
        assert result["total_workers_needed"] == pytest.approx(0.0)

    def test_total_workers_sum_of_domains(self):
        eoh = {"personal": 1e9, "infra": 5e8}
        result = domain_labor_requirements(eoh, epsilon=0.40)
        manual = sum(d["workers_needed"] for d in result["domains"].values())
        assert result["total_workers_needed"] == pytest.approx(manual)

    def test_finite_across_all_key_epsilons(self):
        eoh = self._eoh_dict()
        for eps in KEY_EPSILONS:
            result = domain_labor_requirements(eoh, epsilon=eps)
            assert math.isfinite(result["total_workers_needed"])


# ===========================================================================
# epsilon_delta_sensitivity
# ===========================================================================

class TestEpsilonDeltaSensitivity:
    """Sensitivity analysis must correctly quantify the effect of Δε."""

    def test_return_keys_present(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        assert "base_epsilon" in result
        assert "new_epsilon" in result
        assert "delta_epsilon" in result
        assert "metrics" in result

    def test_metric_keys_present(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        for name in ("total_eoh", "human_eoh", "teh_created", "registration_share",
                     "knowledge_eoh", "workers_needed"):
            assert name in result["metrics"], f"Missing metric: {name}"

    def test_per_metric_keys(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        for name, m in result["metrics"].items():
            for key in ("base", "new", "delta", "pct_change"):
                assert key in m, f"Metric '{name}' missing key '{key}'"

    def test_new_epsilon_clamped_at_099(self):
        result = epsilon_delta_sensitivity(0.95, 0.20)
        assert result["new_epsilon"] <= 0.99

    def test_new_epsilon_clamped_at_zero(self):
        result = epsilon_delta_sensitivity(0.10, -0.50)
        assert result["new_epsilon"] >= 0.0

    def test_zero_delta_all_deltas_zero(self):
        result = epsilon_delta_sensitivity(0.40, 0.0)
        for name, m in result["metrics"].items():
            assert m["delta"] == pytest.approx(0.0, abs=1.0), (
                f"Non-zero delta for {name} with Δε=0: {m['delta']}"
            )

    def test_human_eoh_decreases_with_positive_delta(self):
        """More automation → less human EOH."""
        result = epsilon_delta_sensitivity(0.40, 0.20)
        assert result["metrics"]["human_eoh"]["delta"] < 0.0

    def test_knowledge_eoh_increases_with_positive_delta(self):
        """Knowledge EOH grows with ε (more complex systems to understand)."""
        result = epsilon_delta_sensitivity(0.20, 0.50)
        assert result["metrics"]["knowledge_eoh"]["delta"] > 0.0

    def test_pct_change_consistent_with_base_and_delta(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        for name, m in result["metrics"].items():
            if m["base"] != 0.0 and m["pct_change"] is not None:
                expected = m["delta"] / m["base"] * 100.0
                assert m["pct_change"] == pytest.approx(expected, rel=1e-6)

    def test_all_metrics_finite(self):
        for eps in [0.10, 0.40, 0.80]:
            result = epsilon_delta_sensitivity(eps, 0.05)
            for name, m in result["metrics"].items():
                assert math.isfinite(m["base"])
                assert math.isfinite(m["new"])


# ===========================================================================
# eoh_to_essential_domains
# ===========================================================================

class TestEohToEssentialDomains:
    """Bridge from aggregate EOH to 7 essential workforce domains."""

    def _eoh_dict(self, eps=0.40):
        r = total_eoh(eps)
        return {k: r[k] for k in ("personal", "infrastructure", "ecological", "knowledge")}

    def test_returns_all_essential_domains(self):
        result = eoh_to_essential_domains(self._eoh_dict())
        for domain in ESSENTIAL_DOMAINS:
            assert domain in result, f"Missing essential domain: {domain}"

    def test_all_values_non_negative(self):
        result = eoh_to_essential_domains(self._eoh_dict())
        for domain, val in result.items():
            assert val >= 0.0

    def test_all_values_finite(self):
        for eps in KEY_EPSILONS:
            result = eoh_to_essential_domains(self._eoh_dict(eps))
            for val in result.values():
                assert math.isfinite(val)

    def test_total_equals_input_total(self):
        """With default weights (each column sums to 1), output sum = input sum."""
        eoh = self._eoh_dict()
        result = eoh_to_essential_domains(eoh)
        input_total  = sum(eoh.values())
        output_total = sum(result.values())
        assert output_total == pytest.approx(input_total, rel=1e-6)

    def test_custom_weights_accepted(self):
        """Custom weight matrix must be accepted and applied."""
        custom = {
            "agriculture": {"personal": 0.5, "infrastructure": 0.5},
            "construction": {"ecological": 1.0},
        }
        result = eoh_to_essential_domains(
            {"personal": 1000.0, "infrastructure": 2000.0, "ecological": 500.0, "knowledge": 100.0},
            weights=custom,
        )
        assert result["agriculture"] == pytest.approx(0.5 * 1000.0 + 0.5 * 2000.0)
        assert result["construction"] == pytest.approx(500.0)

    def test_missing_eoh_domains_treated_as_zero(self):
        """EOH domain not in input dict must be treated as 0."""
        result = eoh_to_essential_domains({"personal": 1000.0})  # others missing
        assert all(v >= 0.0 for v in result.values())

    def test_healthcare_largest_from_personal(self):
        """With only personal EOH, healthcare must receive the largest share."""
        result = eoh_to_essential_domains({"personal": 1_000_000.0,
                                           "infrastructure": 0.0, "ecological": 0.0, "knowledge": 0.0})
        assert result["healthcare"] == max(result.values())

    def test_agriculture_largest_from_ecological(self):
        """With only ecological EOH, agriculture must receive the largest share."""
        result = eoh_to_essential_domains({"personal": 0.0, "infrastructure": 0.0,
                                           "ecological": 1_000_000.0, "knowledge": 0.0})
        assert result["agriculture"] == max(result.values())


# ---------------------------------------------------------------------------
# Thermal obligation — the planetary radiative-capacity term (2026-08-05)
# ---------------------------------------------------------------------------

def test_thermal_obligation_defaults_to_zero_everywhere():
    """The wiring is opt-in: every pre-existing caller must be unaffected."""
    from hours_eoh.core.eoh_generation import ecological_eoh_breakdown, ecological_eoh, total_eoh
    b = ecological_eoh_breakdown(0.70, 0.40)
    assert b["thermal"] == 0.0
    assert b["total"] == pytest.approx(b["baseline"] + b["spike"] + b["visible_deferred"])
    assert ecological_eoh(0.70, 0.40) == pytest.approx(b["total"])
    # PHASE 4b: total_eoh resolves the ecological area FROM ITS POPULATION while
    # ecological_eoh alone has no population and keeps the declared US reference
    # frame. The two therefore differ by design on their DEFAULTS, and agree
    # exactly once the same area is supplied — which is what is asserted here,
    # rather than letting two paths disagree silently.
    assert total_eoh(0.40, ecological_area_hectares=US_MAINLAND_HECTARES)["ecological"] \
        == pytest.approx(b["total"])
    assert total_eoh(0.40)["ecological"] < b["total"] / 100.0


def test_thermal_obligation_adds_to_the_ecological_domain():
    from hours_eoh.core.eoh_generation import ecological_eoh_breakdown, total_eoh
    base = ecological_eoh_breakdown(0.70, 0.40)
    load = ecological_eoh_breakdown(0.70, 0.40, thermal_obligation=1_789_175.0)
    assert load["thermal"] == pytest.approx(1_789_175.0)
    assert load["total"] - base["total"] == pytest.approx(1_789_175.0)
    assert total_eoh(0.40, thermal_obligation=1_789_175.0)["ecological"] - \
           total_eoh(0.40)["ecological"] == pytest.approx(1_789_175.0)


def test_thermal_obligation_is_not_scaled_by_monitoring():
    """Unlike historical neglect, measured forcing is a direct observation — it is
    fully visible at every ε rather than emerging as sensing improves."""
    from hours_eoh.core.eoh_generation import ecological_eoh_breakdown
    at_zero = ecological_eoh_breakdown(0.70, 0.0, thermal_obligation=1e6)
    at_full = ecological_eoh_breakdown(0.70, 0.99, thermal_obligation=1e6)
    assert at_zero["thermal"] == at_full["thermal"] == pytest.approx(1e6)
    assert at_zero["monitoring_factor"] < at_full["monitoring_factor"]


def test_thermal_obligation_flows_through_pipeline_and_fiscal():
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.fiscal import fiscal_snapshot
    flow = 1_789_175.0
    a = eoh_to_teh_pipeline(0.40)
    b = eoh_to_teh_pipeline(0.40, thermal_obligation=flow)
    assert b["eoh_by_domain"]["ecological"] - a["eoh_by_domain"]["ecological"] == pytest.approx(flow)
    assert b["teh_created"] > a["teh_created"]          # the obligation partly funds itself
    s = fiscal_snapshot(3.5e10, b["teh_created"], 2e9, 0.3, 1e6, 0.40, thermal_obligation=flow)
    s0 = fiscal_snapshot(3.5e10, a["teh_created"], 2e9, 0.3, 1e6, 0.40)
    assert s["ecological"]["ecological_eoh_total"] - \
           s0["ecological"]["ecological_eoh_total"] == pytest.approx(flow)


def test_thermal_obligation_arc_coherent():
    from hours_eoh.core.eoh_generation import ecological_eoh
    for eps in (0.0, 0.40, 0.90, 0.99):
        v = ecological_eoh(0.70, eps, thermal_obligation=1_789_175.0)
        assert v > 0.0 and math.isfinite(v)


# ---------------------------------------------------------------------------
# Domain balance — the denominator problem (docs/parameter_provenance.md)
#
# These pin a property of the CALIBRATION SET, not of any one function: personal
# EOH dominates the total so completely that ε is ~95% a personal-domain number,
# and the ecological/knowledge domains cannot move it. They are written to FAIL
# if the domain bases are ever put on a commensurable footing — that is the
# point. If one breaks, the fix is to update the doc's table, not the assertion.
# ---------------------------------------------------------------------------

DOMAINS = ("personal", "infrastructure", "ecological", "knowledge")


# BLOCK K-IV MOVED THESE, AND THE FINDING-E RE-ANCHOR MOVED THEM BACK A LITTLE.
# Before K-IV personal ran 86–96% at every ε and the two small domains together
# were a rounding error. Putting knowledge on the measured O*NET footing cut
# personal's share at the top of the arc almost in half. Re-anchoring the base
# to the ε_ref FIXED POINT (0.779× the K-IV value) gives back ~5 points at the
# top. The defect is PARTLY closed: personal still dominates the low arc, where
# there is no apparatus for knowledge to attach to, and ecological is untouched.
# Moved by the 2026-08-10 AGE_GROUPS elderly revalue (2.5 → 1.48): w fell
# 1.475 → 1.3016, so the personal numerator fell 11.76% while the other three
# domains were untouched. Was {0.0: 0.945, 0.40: 0.859, 0.90: 0.614, 0.99: 0.562}.
# The DEFECT is unchanged — personal still dominates the low arc, and the
# revalue narrows the imbalance without addressing its cause.
_PERSONAL_SHARE_EXPECTED = {0.0: 0.936, 0.40: 0.820, 0.90: 0.517, 0.99: 0.461}


@pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
def test_domain_balance_personal_share_across_the_arc(eps):
    d = total_eoh(epsilon=eps)
    share = d["personal"] / d["total"]
    assert share == pytest.approx(_PERSONAL_SHARE_EXPECTED[eps], abs=0.01), (
        f"personal share {share:.3f} at ε={eps} — domain balance has changed; "
        "update docs/parameter_provenance.md §'Domain balance'"
    )


def test_domain_balance_personal_still_dominates_the_low_arc():
    """K-IV did NOT fix domain balance — it closed one of the two small domains.
    At ε=0 there is no apparatus, so knowledge cannot attach and personal is
    still 94%. The remaining lever is the ecological base, plus ATUS on the
    personal numerator itself."""
    d = total_eoh(epsilon=0.0)
    assert d["personal"] / d["total"] > 0.90


def test_domain_balance_knowledge_is_no_longer_a_rounding_error():
    """THE K-IV RESULT. Pre-adoption the two small domains were <0.1% of total
    EOH at ε=0.40; knowledge alone now carries ~8%, and by ε=0.99 it is the
    largest non-personal domain. This is the behaviour knowledge_eoh's own
    reference text has always asserted and never delivered."""
    mid = total_eoh(epsilon=0.40)
    assert mid["knowledge"] / mid["total"] > 0.05

    top = total_eoh(epsilon=0.99)
    assert top["knowledge"] > top["infrastructure"]
    # 0.412 at the K-IV one-shot anchor; 0.353 at the Finding-E fixed point.
    # 0.353 → 0.3785 with the 2026-08-10 elderly revalue: knowledge did not
    # grow, personal SHRANK 11.76% and knowledge's share of the smaller total
    # rose. 0.460 → 0.471 with the 2026-08-16 working-life measurement, and
    # this time by the OTHER mechanism: the renewal rate rose 6.7% so knowledge
    # itself grew. The claim being tested — knowledge stops being a rounding
    # error at the top of the arc — is unaffected by which way it happened,
    # which is why the share is pinned and the cause is recorded in prose.
    assert top["knowledge"] / top["total"] == pytest.approx(0.471, abs=0.01)


def test_domain_balance_ecological_is_still_the_open_defect():
    """Ecological was NOT touched by K-IV and remains ~0.04% of total. Named so
    the closed domain is not mistaken for a closed defect."""
    d = total_eoh(epsilon=0.40)
    assert d["ecological"] / d["total"] < 0.001


def test_domain_balance_ecological_is_sub_hour_per_person():
    """0.71 h/person·yr — the absolute-vs-relative scale defect, made visible."""
    pop = 1_000_000.0
    d = total_eoh(epsilon=0.40, population=pop)
    assert d["ecological"] / pop < 1.0
    # > 1,400 until the 2026-08-10 elderly revalue took w to 1.3016; the point
    # of the assertion is the ORDER-OF-MAGNITUDE gap against ecological's
    # sub-hour figure, which 1,301.6 makes exactly as starkly.
    assert d["personal"] / pop > 1_250.0


def test_domain_balance_epsilon_is_insensitive_to_the_small_domains():
    """A 100× ecological base barely moves the denominator ε is divided by.

    This is why measured work on the small domains cannot be quoted as moving ε.
    """
    base = total_eoh(epsilon=0.40)["total"]
    inflated = total_eoh(epsilon=0.40, ecological_base=500_000.0 * 100)["total"]
    assert (inflated - base) / base < 0.05


def test_domain_balance_thermal_obligation_enters_at_one_part_in_a_thousand():
    """The measured planetary obligation against what the model already books.

    thermal_flow at ε=0.40 (research/thermal_solvency) is ~1.79M h/yr for 1M
    people. Against personal EOH it is negligible — so the fiscal layer's "38×
    margin" verdict passes because the obligation is small, not because the
    fisc is strong.
    """
    flow = 1_789_175.0
    d = total_eoh(epsilon=0.40, thermal_obligation=flow)
    assert flow / d["total"] < 0.0015
    assert d["ecological"] / d["personal"] < 0.002


# ---------------------------------------------------------------------------
# Block I — the standards split (2026-08-06)
#
# One constant was doing three jobs. STANDARD (survival vs sufficiency) and
# DELIVERY (autarky vs collective) are orthogonal; these pin the standard axis.
# The delivery axis arrives with abatement in Block II.
# ---------------------------------------------------------------------------

class TestPersonalStandards:

    def test_three_standards_are_ordered(self):
        assert (personal_base_for("survival")
                < personal_base_for("collapsed")
                < personal_base_for("sufficiency"))

    def test_survival_is_inside_the_autarky_feasibility_bound(self):
        """S_a is HARD-bounded: a survival standard above labour supply is extinction.

        Bound is (L − R)/w = 627 per-equivalent on the repo's own constants. 600
        is set independently and CHECKED here rather than pinned to the bound —
        a constant that cannot fail its own test says nothing.
        """
        from hours_eoh.scenarios.feasibility import feasibility_check
        c = feasibility_check(adult_capacity_h_yr=2000.0, adult_share=0.5,
                              epsilon=0.0,
                              personal_base=personal_base_for("survival"))
        assert c["feasible"] is True
        assert personal_base_for("survival") < c["implied_base_ceiling"]

    def test_sufficiency_is_allowed_to_exceed_supply(self):
        """F_a exceeding autarky supply is the POINT, not a defect — that gap is
        why collectives form."""
        from hours_eoh.scenarios.feasibility import feasibility_check
        c = feasibility_check(adult_capacity_h_yr=2000.0, adult_share=0.5,
                              epsilon=0.0,
                              personal_base=personal_base_for("sufficiency"))
        assert c["feasible"] is False

    def test_unknown_standard_rejected(self):
        with pytest.raises(ValueError):
            personal_base_for("comfortable")

    def test_personal_eoh_honours_the_standard(self):
        pop = 1_000_000.0
        for s in ("survival", "collapsed", "sufficiency"):
            assert personal_eoh(pop, standard=s) == pytest.approx(
                personal_eoh(pop, base_rate=personal_base_for(s)))

    def test_standard_overrides_base_rate_and_says_so(self):
        pop = 1_000_000.0
        assert personal_eoh(pop, base_rate=99.0, standard="survival") == pytest.approx(
            personal_eoh(pop, standard="survival"))

    def test_default_is_unchanged_by_the_split(self):
        """Block I moves NO numbers — it separates concepts only."""
        pop = 1_000_000.0
        assert personal_eoh(pop) == pytest.approx(personal_eoh(pop, standard="collapsed"))
        assert total_eoh(epsilon=0.40)["total"] == pytest.approx(
            total_eoh(epsilon=0.40, personal_standard="collapsed")["total"])

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_total_eoh_standard_arc_coherent(self, eps):
        for s in ("survival", "collapsed", "sufficiency"):
            d = total_eoh(epsilon=eps, personal_standard=s)
            assert d["total"] > 0.0 and math.isfinite(d["total"])
        assert (total_eoh(epsilon=eps, personal_standard="survival")["total"]
                < total_eoh(epsilon=eps, personal_standard="sufficiency")["total"])


class TestKnowledgeSplit:

    def test_components_sum_to_total(self):
        for cpu in (1.0, 2.44, 9.821):
            r = knowledge_eoh_breakdown(4.6, complexity_per_unit=cpu)
            assert (r["civilisational"] + r["apparatus"]
                    == pytest.approx(r["total"]))

    def test_no_apparatus_at_zero_automation(self):
        """cpu(0) = 1.0, so the whole domain is civilisational at ε=0."""
        r = knowledge_eoh_breakdown(1.0, epsilon=0.0)
        assert r["apparatus"] == pytest.approx(0.0)
        assert r["apparatus_fraction"] == pytest.approx(0.0)

    def test_apparatus_share_rises_with_complexity(self):
        shares = [knowledge_eoh_breakdown(4.6, complexity_per_unit=c)["apparatus_fraction"]
                  for c in (1.0, 1.36, 2.44, 5.41, 9.821)]
        assert shares == sorted(shares)
        assert shares[-1] == pytest.approx(0.898, abs=0.005)

    def test_split_derives_from_the_existing_form_not_a_new_constant(self):
        """apparatus_fraction = 1 − 1/cpu, so no constant was introduced."""
        for cpu in (1.5, 3.0, 8.0):
            r = knowledge_eoh_breakdown(4.6, complexity_per_unit=cpu)
            assert r["apparatus_fraction"] == pytest.approx(1.0 - 1.0 / cpu)

    def test_explicit_override_is_honoured(self):
        r = knowledge_eoh_breakdown(4.6, complexity_per_unit=2.44,
                                    apparatus_fraction=0.25)
        assert r["apparatus_fraction"] == 0.25
        assert r["apparatus"] == pytest.approx(r["total"] * 0.25)

    def test_override_validated(self):
        with pytest.raises(ValueError):
            knowledge_eoh_breakdown(4.6, apparatus_fraction=1.5)

    def test_total_matches_knowledge_eoh(self):
        from hours_eoh.core.eoh_generation import knowledge_eoh
        r = knowledge_eoh_breakdown(4.6, complexity_per_unit=2.44)
        assert r["total"] == pytest.approx(knowledge_eoh(4.6, complexity_per_unit=2.44))


# ---------------------------------------------------------------------------
# Block III — the accounting basis
#
# Infrastructure and the APPARATUS share of knowledge are INTERMEDIATE: the cost
# of the service apparatus, not obligations a civilisation owes. Counting them in
# the total is the same error as adding intermediate consumption to GDP.
# ---------------------------------------------------------------------------

class TestAccountingBasis:

    def test_gross_is_the_default_and_unchanged(self):
        d = total_eoh(epsilon=0.40)
        assert d["total"] == pytest.approx(d["total_gross"])
        assert d["total_gross"] == pytest.approx(
            d["personal"] + d["infrastructure"] + d["ecological"] + d["knowledge"])

    def test_final_excludes_the_apparatus(self):
        d = total_eoh(epsilon=0.40, basis="final")
        assert d["total"] == pytest.approx(d["total_base"])
        assert d["total"] < d["total_gross"]

    def test_base_plus_overhead_reconstructs_gross(self):
        for eps in [0.0, 0.40, 0.90, 0.99]:
            d = total_eoh(epsilon=eps)
            assert d["total_base"] + d["total_overhead"] == pytest.approx(
                d["total_gross"])

    def test_overhead_is_infrastructure_plus_apparatus_knowledge(self):
        d = total_eoh(epsilon=0.40)
        assert d["total_overhead"] == pytest.approx(
            d["infrastructure"] + d["knowledge_apparatus"])

    def test_base_is_personal_ecological_and_civilisational_knowledge(self):
        d = total_eoh(epsilon=0.40)
        assert d["total_base"] == pytest.approx(
            d["personal"] + d["ecological"] + d["knowledge_civilisational"])

    def test_knowledge_split_is_a_partition(self):
        for eps in [0.0, 0.40, 0.99]:
            d = total_eoh(epsilon=eps)
            assert (d["knowledge_apparatus"] + d["knowledge_civilisational"]
                    == pytest.approx(d["knowledge"]))

    def test_final_basis_drifts_less_than_gross_but_no_longer_near_constant(self):
        """
        CONSERVATION RESULT DOWNGRADED BY BLOCK K-IV — recorded, not retuned.

        Pre-adoption the final basis drifted +0.35% across the arc against the
        gross basis's +10%, and that near-flatness was quoted as the payoff of
        the Block I–III thread: obligation is population × per-person, and the
        apparatus built to SERVE it is not additional obligation.

        It drifted +7.7% after K-IV and drifts **+6.1%** (1,485 → 1,575
        h/person·yr) after the Finding-E re-anchor. The direction still holds —
        final drifts far less than gross — but "near-constant" is no longer
        supportable, and the re-anchor does not restore it: a 22% smaller
        knowledge base shrinks the drift proportionally without touching its
        cause.

        THE CAUSE IS STRUCTURAL, NOT A CALIBRATION ARTIFACT. The final basis
        includes `knowledge_civilisational`, which is base·kbs(ε)·cpu(0)·d, and
        kbs = 1 + slope·ε shares `CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE` with
        cpu. So the component the Block I split labels *civilisational* — "the
        corpus renewed whatever the capital" — is itself ε-driven, growing 9.91×
        across the arc. The label implies an ε-invariant floor; the code has
        never computed one.

        Pre-K-IV this was invisible because knowledge was 0.005% of total EOH.
        The honest reading: **the near-conservation result was an artifact of
        the knowledge domain being negligible.** Whether the civilisational
        corpus should be ε-invariant is a theory question (author sign-off), not
        something to fix by moving a threshold here.
        """
        finals = [total_eoh(epsilon=e, basis="final")["total"]
                  for e in (0.0, 0.40, 0.99)]
        grosses = [total_eoh(epsilon=e)["total"] for e in (0.0, 0.40, 0.99)]
        final_drift = finals[-1] / finals[0] - 1.0
        gross_drift = grosses[-1] / grosses[0] - 1.0

        # +6.1% → +9.0%: the final basis excludes apparatus knowledge but keeps the
        # CIVILISATIONAL corpus, which the re-anchor grew 1.397× along with the rest.
        assert final_drift == pytest.approx(0.090, abs=0.005)
        assert gross_drift > 0.09
        assert final_drift < gross_drift / 5.0

    def test_civilisational_knowledge_is_not_epsilon_invariant(self):
        """Pins the cause of the above, so it cannot be rediscovered as a
        mystery. If the corpus is ever made ε-invariant this fails and the
        conservation result should be re-examined at the same time."""
        lo = total_eoh(epsilon=0.0)["knowledge_civilisational"]
        hi = total_eoh(epsilon=0.99)["knowledge_civilisational"]
        assert hi / lo == pytest.approx(9.91, rel=1e-2), (
            "civilisational knowledge tracks kbs = 1 + slope·ε, sharing the "
            "automation slope with the apparatus term it is contrasted against"
        )

    def test_all_values_remain_numeric(self):
        """Regression: a str in the dict broke isfinite checks downstream."""
        import math as _m
        for v in total_eoh(epsilon=0.40).values():
            assert isinstance(v, (int, float)) and _m.isfinite(v)

    def test_bad_basis_rejected(self):
        with pytest.raises(ValueError, match="basis"):
            total_eoh(epsilon=0.40, basis="net")


# ===========================================================================
# total_eoh — the ecological AREA seam (2026-08-17)
#
# ecological_eoh() was keyed to area on 2026-08-16, but neither total_eoh nor
# eoh_to_teh_pipeline plumbed it, so the fix was stranded one layer below the
# intake path docs/guides/implementation_guide.md tells institutions to use.
# These pin the seam AND the thing that makes it safe: the default must not move.
# ===========================================================================

class TestEcologicalAreaReachesTotalEoh:
    """area_hectares reaches total_eoh, and the default path is unchanged."""

    def test_area_scales_the_ecological_domain_linearly(self):
        # Area is the extensive quantity: doubling it doubles the obligation.
        for eps in KEY_EPSILONS:
            one = total_eoh(epsilon=eps, ecological_area_hectares=1.0e8)["ecological"]
            five = total_eoh(epsilon=eps, ecological_area_hectares=5.0e8)["ecological"]
            assert one > 0.0
            assert five == pytest.approx(5.0 * one, rel=1e-12)

    def test_default_resolves_the_area_FROM_THE_POPULATION(self):
        """
        PHASE 4b (2026-08-17). The default used to be ECOLOGICAL_BASE_RATE — the
        obligation for the WHOLE CONTIGUOUS US — while the default population is
        1,000,000. Nothing connected them, so the shipped default had a million
        people stewarding the entire United States and the reported ecological
        share was flattered by the ratio between the two.

        The fix is in the RESOLUTION, not the constant: ECOLOGICAL_BASE_RATE
        correctly states the US-scale obligation and ECOLOGICAL_INTENSITY_BASE is
        derived from it, so rewriting it would break an identity the repo pins
        deliberately. The default now derives its area from the population.
        """
        for eps in KEY_EPSILONS:
            for pop in (1e6, 335e6):
                got = total_eoh(epsilon=eps, population=pop,
                                ecosystem_health=0.70)["ecological"]
                expected = (pop * LAND_HECTARES_PER_CAPITA
                            * ECOLOGICAL_INTENSITY_BASE) / 0.70
                assert got == pytest.approx(expected, rel=1e-12)

    def test_the_anchor_identity_is_UNTOUCHED(self):
        """
        What the resolution change deliberately preserves. A naive fix that
        rewrote ECOLOGICAL_BASE_RATE to a 1M-consistent value would break
        `intensity x reference area = anchor` — and that identity is correct, so
        the pins would be firing against the fix rather than against a defect.
        """
        assert ECOLOGICAL_INTENSITY_BASE == pytest.approx(
            ECOLOGICAL_BASE_RATE / US_MAINLAND_HECTARES, rel=1e-15
        )

    def test_supplying_the_us_area_still_reproduces_the_us_anchor(self):
        """The constant is still reachable — it is now supplied, not assumed."""
        for eps in KEY_EPSILONS:
            got = total_eoh(epsilon=eps, ecosystem_health=0.70,
                            ecological_area_hectares=US_MAINLAND_HECTARES)["ecological"]
            assert got == pytest.approx(ECOLOGICAL_BASE_RATE / 0.70, rel=1e-9)

    def test_the_us_frame_now_DIFFERS_from_the_default(self):
        """
        The mismatch this change removes, pinned as a difference. Before Phase 4b
        the default WAS the whole-US area, so these agreed; now the default is
        1M people's share of it and the US frame is 335x larger.
        """
        for eps in KEY_EPSILONS:
            framed = total_eoh(epsilon=eps, ecological_area_hectares=US_MAINLAND_HECTARES)
            default = total_eoh(epsilon=eps)
            assert framed["ecological"] > 100.0 * default["ecological"]

    def test_base_and_area_together_is_REFUSED(self):
        """
        The silently-ignored-parameter failure this repo keeps finding. Under
        ecological_scale() precedence base_rate wins and the area vanishes; a
        caller who supplied an area would believe it was in force. Refused, not
        resolved.
        """
        with pytest.raises(ValueError, match="not both"):
            total_eoh(
                epsilon=0.40,
                ecological_base=500_000.0,
                ecological_area_hectares=US_MAINLAND_HECTARES,
            )

    def test_explicit_base_still_honoured(self):
        # The pre-2026-08-16 absolute path is unaffected.
        got = total_eoh(epsilon=0.40, ecological_base=1_000_000.0, ecosystem_health=0.70)
        assert got["ecological"] == pytest.approx(1_000_000.0 / 0.70, rel=1e-12)

    def test_zero_area_is_zero_obligation_not_a_crash(self):
        # eps-coherence: a collective stewarding no land owes no ecological EOH,
        # and the rest of the ledger still resolves.
        for eps in KEY_EPSILONS:
            d = total_eoh(epsilon=eps, ecological_area_hectares=0.0)
            assert d["ecological"] == 0.0
            assert math.isfinite(d["total"]) and d["total"] > 0.0

    def test_negative_area_rejected(self):
        with pytest.raises(ValueError, match="area_hectares"):
            total_eoh(epsilon=0.40, ecological_area_hectares=-1.0)


class TestStatutoryHoursPerUnitYear:
    """
    The derivation `infrastructure_statutory_floor` documented and nothing
    implemented, leaving INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT — a convention
    adopted from 23 CFR 650 — read by no code path at all.
    """

    def test_reproduces_the_governing_equation(self):
        from hours_eoh.core.eoh_generation import statutory_hours_per_unit_year
        for interval, crew in ((24.0, 16.0), (3.0, 4.0), (12.0, 20.0)):
            assert statutory_hours_per_unit_year(crew, interval) == pytest.approx(
                (12.0 / interval) * crew, rel=1e-12
            )

    def test_the_statutory_default_reproduces_the_worked_example(self):
        """23 CFR 650 routine (24 mo) at 16 crew-hours = the 'good' bucket's 8 h."""
        from hours_eoh.core.eoh_generation import statutory_hours_per_unit_year
        from hours_eoh.data import INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT
        assert INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT == 24.0
        assert statutory_hours_per_unit_year(16.0) == pytest.approx(8.0, rel=1e-12)

    def test_it_feeds_the_floor_and_reproduces_ITS_worked_example(self):
        """
        End-to-end: derived hours through the floor must give the 448,816 h/yr
        the floor's own docstring states, which is what shows the derivation and
        the floor were always meant to be the same chain.
        """
        from hours_eoh.core.eoh_generation import (
            infrastructure_statutory_floor,
            statutory_hours_per_unit_year as h,
        )
        census = [
            {"count": 8019,  "hours_per_unit_year": h(16.0)},           # 8 h
            {"count": 12482, "hours_per_unit_year": h(16.0, 9.6)},      # 20 h
            {"count": 2813,  "hours_per_unit_year": h(16.0, 4.0)},      # 48 h
        ]
        assert infrastructure_statutory_floor(census) == pytest.approx(448_816.0, rel=1e-9)

    def test_shorter_interval_costs_more_hours(self):
        from hours_eoh.core.eoh_generation import statutory_hours_per_unit_year as h
        assert h(16.0, 12.0) > h(16.0, 24.0)

    def test_no_currency_enters_the_chain(self):
        """
        An interval is a count of months and a visit is a count of hours, which
        is the property that made the statutory floor doctrine-invariant.
        """
        import inspect
        from hours_eoh.core.eoh_generation import statutory_hours_per_unit_year
        src = inspect.getsource(statutory_hours_per_unit_year)
        for money in ("dollar", "usd", "cost_per", "price", "wage"):
            assert money not in src.lower()

    def test_invalid_inputs_rejected(self):
        from hours_eoh.core.eoh_generation import statutory_hours_per_unit_year as h
        with pytest.raises(ValueError, match="interval_months"):
            h(16.0, 0.0)
        with pytest.raises(ValueError, match="crew_hours_per_visit"):
            h(-1.0)


def test_eta_land_mask_threshold_is_superseded_by_the_shipped_method():
    """
    The constant asserted a binary threshold "is required"; the η dataset that
    shipped states it used the continuous land FRACTION and explicitly not a
    threshold. Retired rather than wired — wiring it would reintroduce the
    all-or-nothing coastal treatment the data deliberately avoided.
    """
    from hours_eoh.research.thermal_path_c import load_eta_land
    weighting = load_eta_land()["_method"]["weighting"]
    assert "not a binary threshold" in weighting
    assert "FRACTION" in weighting


class TestEcologicalSpikeShape:
    """
    THE SUB-THRESHOLD SPIKE, migrated and pinned (2026-08-28).

    `ECOLOGICAL_SPIKE_INTENSITY` was `_ECOLOGICAL_SPIKE_INTENSITY` in
    `core/eoh_generation.py`. The 2026-08-09 provenance pass NAMED it as
    calibrated-to-target — picked to produce the escalation the arc was expected
    to show — and it then stayed a shadow constant for the whole period since,
    so the gate that reports calibrated-to-target constants could not see it. A
    +7% move failed no test.

    Division of labour with `ECOLOGICAL_THRESHOLD`: the threshold sets WHERE the
    spike begins, this sets HOW BIG it gets. Pinned as shape.
    """

    def test_no_spike_above_the_threshold(self):
        """A regime-shift term that fires in the healthy regime is not a
        regime-shift term."""
        for health in (ECOLOGICAL_THRESHOLD + 0.01, 0.6, 0.8, 1.0):
            b = ecological_eoh_breakdown(health, area_hectares=1.0e6)
            assert b["spike"] == 0.0, f"spike fired at healthy h={health}"

    def test_the_spike_engages_below_the_threshold(self):
        b = ecological_eoh_breakdown(ECOLOGICAL_THRESHOLD - 0.01,
                                     area_hectares=1.0e6)
        assert b["spike"] > 0.0

    def test_the_spike_grows_as_health_falls(self):
        spikes = [ecological_eoh_breakdown(h, area_hectares=1.0e6)["spike"]
                  for h in (0.39, 0.30, 0.20, 0.10, 0.01)]
        assert spikes == sorted(spikes), spikes

    def test_the_approach_is_quadratic_not_linear(self):
        """
        THE SHAPE CLAIM. spike ∝ ((threshold − health)/threshold)², so doubling
        the deficit quadruples the spike. A linear term would merely double it —
        a different model of regime shift, and the exponent is what
        distinguishes them.

        Measured between two deficits well clear of the health clamp (see the
        collapse test below), so the clamp cannot flatter the exponent.
        """
        thr = ECOLOGICAL_THRESHOLD
        quarter = ecological_eoh_breakdown(thr * 0.75, area_hectares=1.0e6)["spike"]
        half = ecological_eoh_breakdown(thr * 0.50, area_hectares=1.0e6)["spike"]
        assert half == pytest.approx(4.0 * quarter, rel=1e-6)

    def test_total_collapse_costs_the_declared_multiple_of_the_baseline(self):
        """
        As health → 0 the deficit fraction → 1, so the spike approaches exactly
        INTENSITY × scale. That is what the constant MEANS, and asserting it
        binds the constant to the behaviour rather than restating the number.

        THE HEALTH CLAMP IS WHY THIS IS AN APPROACH, NOT AN EQUALITY.
        `ecological_eoh` floors health at 0.001 to avoid a division by zero, so
        the deficit at h=0 is 0.9975 and the spike is 4.975×, never 5×. Pinned
        with the clamp visible — a 0.5% shortfall that looks like a rounding
        error is exactly the kind of thing that gets "fixed" by widening a
        tolerance instead of being understood.
        """
        b = ecological_eoh_breakdown(0.0, area_hectares=1.0e6)
        deficit = (ECOLOGICAL_THRESHOLD - 0.001) / ECOLOGICAL_THRESHOLD
        assert b["spike"] == pytest.approx(
            ECOLOGICAL_SPIKE_INTENSITY * deficit ** 2 * b["scale"], rel=1e-9
        )
        assert b["spike"] / b["scale"] == pytest.approx(
            ECOLOGICAL_SPIKE_INTENSITY, rel=0.01
        )

    def test_the_spike_scales_with_area_like_the_baseline(self):
        """It is an obligation on ground, so it must be extensive in area — the
        property the 2026-08-16 keying fix established for the domain."""
        one = ecological_eoh_breakdown(0.2, area_hectares=1.0e6)["spike"]
        two = ecological_eoh_breakdown(0.2, area_hectares=2.0e6)["spike"]
        assert two == pytest.approx(2.0 * one, rel=1e-9)


class TestPhase4fTheStandingTermIsGufs:
    """
    THE ECOLOGICAL LEVEL, CLOSED — and not by a census (Phase 4f, 2026-08-28).

    `ECOLOGICAL_BASE_RATE` produces `standing`, a RECURRING per-year term, and
    Phase 4d's adopted partition says everything recurring is GUF's. The
    question "what should the anchor be?" was carried for months as a
    MEASUREMENT question; it is not one.

    The argument is checkable, and `test_the_census_is_already_spent_in_guf`
    checks it: GUF's recurring target already charges the measured stewardship
    intensity of every class the census can price. Raising this anchor toward
    the census would bill the same hours twice.

    THEORY-FLAGGED. The relocation is opt-in and default-off, exactly as
    `health_response` and `thermal_obligation` were at their sign-offs.
    """

    def test_the_default_moves_nothing(self):
        """`TestPIChangesNothing` discipline: the seam is explicit, not applied."""
        for health in (0.3, 0.7, 1.0):
            a = ecological_eoh_breakdown(health, area_hectares=1.65e6)
            b = ecological_eoh_breakdown(health, area_hectares=1.65e6,
                                         standing_response="domain")
            assert a["total"] == b["total"]
            assert a["standing_relocated"] == 0.0

    def test_relocating_standing_removes_exactly_the_standing_term(self):
        kept = ecological_eoh_breakdown(0.70, area_hectares=1.65e6)
        moved = ecological_eoh_breakdown(0.70, area_hectares=1.65e6,
                                         standing_response="guf")
        assert moved["total"] == pytest.approx(
            kept["total"] - kept["standing"], rel=1e-12
        )
        assert moved["standing_relocated"] == pytest.approx(kept["standing"])

    def test_the_obligation_is_conserved_only_relocated(self):
        """Nothing is destroyed: what leaves the domain is reported."""
        for health in (0.3, 0.7, 1.0):
            kept = ecological_eoh_breakdown(health, area_hectares=1.65e6)
            moved = ecological_eoh_breakdown(health, area_hectares=1.65e6,
                                             standing_response="guf")
            assert moved["total"] + moved["standing_relocated"] == pytest.approx(
                kept["total"], rel=1e-12
            )

    def test_the_full_partition_leaves_only_stocks(self):
        """
        THE PARTITION REALISED. With both recurring terms relocated and no stock
        supplied, the ecological domain is EXACTLY zero — which is Phase 4d's
        "the domain carries exactly two terms and both are STOCKS", arrived at
        by algebra rather than assertion.
        """
        b = ecological_eoh_breakdown(0.70, area_hectares=1.65e6,
                                     health_response="guf",
                                     standing_response="guf")
        assert b["total"] == 0.0

    def test_the_stocks_still_survive_the_relocation(self):
        """The partition must EMPTY the recurring side, not the domain."""
        b = ecological_eoh_breakdown(0.70, area_hectares=1.65e6,
                                     health_response="guf",
                                     standing_response="guf",
                                     thermal_obligation=1000.0,
                                     restoration_obligation=250.0)
        assert b["total"] == pytest.approx(1250.0, rel=1e-12)

    def test_the_census_is_already_spent_in_guf(self):
        """
        THE ARGUMENT, RUN. Every class whose stewardship intensity the census
        can price already appears in GUF's recurring target, so matching this
        anchor to the census would double-count. If GUF ever stops charging
        stewardship, this test fails and the Phase 4f derivation must be redone.
        """
        from hours_eoh.scenarios.guf_magnitude import recurring_target_by_class

        charged = {r["land_use"]: r["stewardship_h_per_ha"]
                   for r in recurring_target_by_class()
                   if r["stewardship_h_per_ha"] is not None}
        assert charged, "GUF must charge stewardship somewhere, or 4f's premise fails"
        for land_use, intensity in charged.items():
            assert intensity > 0.0, f"{land_use} charged a non-positive intensity"
        # and every one of them dwarfs the anchor it would otherwise be raised to
        assert min(charged.values()) > 100.0 * ECOLOGICAL_INTENSITY_BASE

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.99])
    def test_arc_coherence_under_both_policies(self, eps):
        for policy in ("domain", "guf"):
            v = ecological_eoh(0.70, epsilon=eps, area_hectares=1.65e6,
                               standing_response=policy)
            assert v >= 0.0 and v == v

    def test_the_switch_is_reachable_from_the_documented_intake_path(self):
        """
        Parameters stranded one layer below `eoh_to_teh_pipeline` is this repo's
        recurring failure — `personal_standard` and `ecological_health_response`
        both hit that wall. This one is checked at the entry point.
        """
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

        kept = eoh_to_teh_pipeline(epsilon=0.40, population=1e6)
        moved = eoh_to_teh_pipeline(epsilon=0.40, population=1e6,
                                    ecological_standing_response="guf",
                                    ecological_health_response="guf")
        assert moved["eoh_by_domain"]["ecological"] == 0.0
        assert kept["eoh_by_domain"]["ecological"] > 0.0
