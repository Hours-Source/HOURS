"""
Tests for hours_eoh.core.eoh_generation

Covers: personal_eoh, infrastructure_eoh, ecological_eoh, knowledge_eoh,
total_eoh, ecological_eoh_breakdown, effective_capital_from_stock,
domain_labor_requirements, epsilon_delta_sensitivity, eoh_to_essential_domains.
"""

import math
import pytest

from hours_eoh.core.eoh_generation import (
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
from hours_eoh.data import ESSENTIAL_DOMAINS

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
    assert total_eoh(0.40)["ecological"] == pytest.approx(b["total"])


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
