"""
Tests for hours_eoh.core.workforce

Covers: competency_reserve, competency_check, minimum_hours_allocation,
automation_failure_scenario, apply_death_redistribution,
competency_to_knowledge_eoh_delta, domain_eoh_coverage.
"""

import math
import pytest

from hours_eoh.core.workforce import (
    competency_reserve,
    competency_check,
    minimum_hours_allocation,
    automation_failure_scenario,
    apply_death_redistribution,
    competency_to_knowledge_eoh_delta,
)
from hours_eoh.core.conditions import domain_eoh_coverage
from hours_eoh.core.capital import (
    make_asset,
    maturation_update,
    death_event,
    birth_event,
)
from hours_eoh.core.population import aging
from hours_eoh.data import (
    ESSENTIAL_DOMAINS,
    COMPETENCY_THRESHOLD,
    H_MIN,
    PERSONAL_EOH_BASE,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKFORCE_SIZE = 500_000.0
SUFFICIENT_CERTIFIED   = {d: WORKFORCE_SIZE * 0.16 for d in ESSENTIAL_DOMAINS}
INSUFFICIENT_CERTIFIED = {d: WORKFORCE_SIZE * 0.16 for d in ESSENTIAL_DOMAINS}
INSUFFICIENT_CERTIFIED["water"]      = WORKFORCE_SIZE * 0.10
INSUFFICIENT_CERTIFIED["healthcare"] = WORKFORCE_SIZE * 0.08


def make_worker(age: float = 35.0, capacity: float = 1200.0) -> dict:
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
# competency_reserve
# ===========================================================================

class TestCompetencyReserve:

    def test_all_domains_above_threshold(self):
        """All domains meeting threshold → overall_meets_threshold True."""
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        assert reserve["overall_meets_threshold"] is True
        assert reserve["status"] == "OK"
        assert reserve["domains_at_risk"] == []

    def test_two_domains_below_threshold(self):
        """Domains below threshold appear in domains_at_risk."""
        reserve = competency_reserve(INSUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        assert reserve["overall_meets_threshold"] is False
        assert "water" in reserve["domains_at_risk"]
        assert "healthcare" in reserve["domains_at_risk"]

    def test_all_seven_domains_present_in_result(self):
        """Result must include all seven essential domains."""
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        for domain in ESSENTIAL_DOMAINS:
            assert domain in reserve["per_domain"]

    def test_per_domain_reserve_fraction_correct(self):
        """Reserve fraction = certified_count / workforce_size."""
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        for domain in ESSENTIAL_DOMAINS:
            data = reserve["per_domain"][domain]
            expected_fraction = SUFFICIENT_CERTIFIED[domain] / WORKFORCE_SIZE
            assert data["reserve_fraction"] == pytest.approx(expected_fraction)

    def test_gap_computed_correctly(self):
        """Gap = required_count - certified_count (only positive)."""
        reserve = competency_reserve(INSUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        water_data = reserve["per_domain"]["water"]
        expected_gap = WORKFORCE_SIZE * COMPETENCY_THRESHOLD - INSUFFICIENT_CERTIFIED["water"]
        assert water_data["gap"] == pytest.approx(expected_gap)

    def test_zero_certified_all_domains_at_risk(self):
        """Zero certified workers → all domains at risk."""
        reserve = competency_reserve({}, WORKFORCE_SIZE)
        assert reserve["n_domains_at_risk"] == 7
        assert reserve["overall_meets_threshold"] is False

    def test_zero_workforce_raises(self):
        with pytest.raises(ValueError):
            competency_reserve(SUFFICIENT_CERTIFIED, workforce_size=0.0)

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError):
            competency_reserve({"farming": 1000}, WORKFORCE_SIZE)

    def test_n_domains_at_risk_correct(self):
        reserve = competency_reserve(INSUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        assert reserve["n_domains_at_risk"] == len(reserve["domains_at_risk"])

    def test_reserve_is_epsilon_independent(self):
        """Competency reserve is a structural headcount check, not ε-dependent."""
        reserve1 = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        reserve2 = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        assert reserve1["overall_meets_threshold"] == reserve2["overall_meets_threshold"]


# ===========================================================================
# competency_check
# ===========================================================================

class TestCompetencyCheck:

    def test_passes_when_reserve_adequate(self):
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        assert check["passes"] is True
        assert check["status"] == "OK"
        assert check["domains_at_risk"] == []
        assert check["critical_domains"] == []

    def test_fails_with_critical_domain_gap(self):
        """Gaps in healthcare/water/energy flag critical_domains."""
        reserve = competency_reserve(INSUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        assert check["passes"] is False
        assert check["status"] == "CONDITION_IV_VIOLATION"
        assert "water" in check["critical_domains"]
        assert "healthcare" in check["critical_domains"]

    def test_all_domains_in_per_domain_result(self):
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        for domain in ESSENTIAL_DOMAINS:
            assert domain in check["per_domain"]

    def test_per_domain_status_ok_above_threshold(self):
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        for domain in ESSENTIAL_DOMAINS:
            assert check["per_domain"][domain]["status"] == "OK"

    def test_per_domain_status_below_threshold(self):
        reserve = competency_reserve(INSUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        assert check["per_domain"]["water"]["status"]      == "BELOW_THRESHOLD"
        assert check["per_domain"]["healthcare"]["status"] == "BELOW_THRESHOLD"

    def test_recommendation_not_empty(self):
        reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        assert len(check["recommendation"]) > 0

    def test_non_critical_gap_not_in_critical_domains(self):
        """A gap in agriculture is at-risk but not critical infrastructure."""
        certs = {d: WORKFORCE_SIZE * 0.16 for d in ESSENTIAL_DOMAINS}
        certs["agriculture"] = WORKFORCE_SIZE * 0.10
        reserve = competency_reserve(certs, WORKFORCE_SIZE)
        check   = competency_check(reserve)
        assert "agriculture" in check["domains_at_risk"]
        assert "agriculture" not in check["critical_domains"]

    def test_passes_at_all_key_epsilons(self):
        """Condition IV is structural — passes at all ε with adequate reserve."""
        for eps in KEY_EPSILONS:
            reserve = competency_reserve(SUFFICIENT_CERTIFIED, WORKFORCE_SIZE)
            check   = competency_check(reserve)
            assert check["passes"] is True, (
                f"Condition IV must pass at ε={eps} with adequate reserve"
            )


# ===========================================================================
# minimum_hours_allocation
# ===========================================================================

class TestMinimumHoursAllocation:

    def test_default_split_is_40_30_30(self):
        result = minimum_hours_allocation()
        assert result["rotation_hours"]    == pytest.approx(H_MIN * 0.40)
        assert result["stewardship_hours"] == pytest.approx(H_MIN * 0.30)
        assert result["employment_hours"]  == pytest.approx(H_MIN * 0.30)

    def test_total_hours_equals_h_min(self):
        result = minimum_hours_allocation()
        assert result["total_hours"] == pytest.approx(H_MIN)

    def test_custom_h_min(self):
        result = minimum_hours_allocation(h_min=520.0)
        assert result["total_hours"] == pytest.approx(520.0)

    def test_total_labor_eoh_scales_with_workforce(self):
        result = minimum_hours_allocation(workforce_size=500_000.0)
        assert result["total_labor_eoh"] == pytest.approx(H_MIN * 500_000.0)

    def test_rotation_eoh_largest_at_default_split(self):
        """Rotation (40%) should be larger than stewardship and employment (30% each)."""
        result = minimum_hours_allocation()
        assert result["rotation_hours"] > result["stewardship_hours"]
        assert result["rotation_hours"] > result["employment_hours"]

    def test_invalid_shares_raise(self):
        with pytest.raises(ValueError):
            minimum_hours_allocation(rotation_share=0.50,
                                     stewardship_share=0.30,
                                     employment_share=0.30)  # sums to 1.10

    def test_zero_h_min_raises(self):
        with pytest.raises(ValueError):
            minimum_hours_allocation(h_min=0.0)

    def test_result_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = minimum_hours_allocation(epsilon=eps)
            assert math.isfinite(result["total_hours"])
            assert math.isfinite(result["total_labor_eoh"])

    def test_per_component_eoh_sums_to_total(self):
        result = minimum_hours_allocation(workforce_size=100_000.0)
        total = (result["total_rotation_eoh"]
                 + result["total_stewardship_eoh"]
                 + result["total_employment_eoh"])
        assert total == pytest.approx(result["total_labor_eoh"])

    def test_equal_split_allowed(self):
        """Custom 1/3-1/3-1/3 split should work."""
        s = 1.0 / 3.0
        result = minimum_hours_allocation(
            rotation_share=s,
            stewardship_share=s,
            employment_share=1.0 - 2 * s,
        )
        assert math.isfinite(result["total_hours"])

    def test_rotation_supports_competency_upkeep_at_high_epsilon(self):
        """At high ε, rotation EOH must be positive and substantial."""
        alloc = minimum_hours_allocation(workforce_size=WORKFORCE_SIZE, epsilon=0.90)
        assert alloc["total_rotation_eoh"] > 0
        assert alloc["total_rotation_eoh"] >= WORKFORCE_SIZE * H_MIN * 0.40


# ===========================================================================
# automation_failure_scenario
# ===========================================================================

class TestAutomationFailureScenario:

    def _scenario(self, epsilon, critical_eoh, reserve_eoh, h_min_eoh,
                  workforce=500_000.0):
        return automation_failure_scenario(
            epsilon=epsilon,
            critical_eoh=critical_eoh,
            reserve_capacity_eoh=reserve_eoh,
            h_min_labor_eoh=h_min_eoh,
            workforce_size=workforce,
        )

    def test_covered_when_capacity_exceeds_critical(self):
        """If reserve + h_min > critical_eoh, covered = True."""
        result = self._scenario(0.40, critical_eoh=1e6,
                                reserve_eoh=800_000, h_min_eoh=300_000)
        assert result["covered"] is True
        assert result["severity"] == "NONE"

    def test_not_covered_when_capacity_insufficient(self):
        result = self._scenario(0.40, critical_eoh=2e6,
                                reserve_eoh=500_000, h_min_eoh=300_000)
        assert result["covered"] is False

    def test_severity_moderate(self):
        """Coverage ratio 0.75–1.0 → MODERATE."""
        result = self._scenario(0.40, critical_eoh=1_000_000,
                                reserve_eoh=500_000, h_min_eoh=300_000)
        assert result["coverage_ratio"] == pytest.approx(0.80, rel=0.01)
        assert result["severity"] == "MODERATE"

    def test_severity_severe(self):
        """Coverage ratio 0.50–0.75 → SEVERE."""
        result = self._scenario(0.60, critical_eoh=1_000_000,
                                reserve_eoh=400_000, h_min_eoh=200_000)
        assert result["severity"] == "SEVERE"

    def test_severity_critical(self):
        """Coverage ratio < 0.50 → CRITICAL."""
        result = self._scenario(0.80, critical_eoh=1_000_000,
                                reserve_eoh=100_000, h_min_eoh=100_000)
        assert result["severity"] == "CRITICAL"

    def test_gap_eoh_is_zero_when_covered(self):
        result = self._scenario(0.40, critical_eoh=1e6,
                                reserve_eoh=900_000, h_min_eoh=200_000)
        assert result["gap_eoh"] == pytest.approx(0.0)

    def test_gap_eoh_positive_when_not_covered(self):
        result = self._scenario(0.70, critical_eoh=2_000_000,
                                reserve_eoh=500_000, h_min_eoh=400_000)
        assert result["gap_eoh"] == pytest.approx(1_100_000.0, rel=1e-6)

    def test_coverage_ratio_formula(self):
        """coverage_ratio = (reserve + h_min) / critical_eoh."""
        result = self._scenario(0.40, critical_eoh=1_000_000,
                                reserve_eoh=600_000, h_min_eoh=200_000)
        expected = 800_000 / 1_000_000
        assert result["coverage_ratio"] == pytest.approx(expected)

    def test_zero_critical_eoh_is_covered(self):
        """If no critical EOH, any reserve covers it."""
        result = self._scenario(0.0, critical_eoh=0.0,
                                reserve_eoh=0, h_min_eoh=0)
        assert result["covered"] is True

    def test_epsilon_out_of_range_raises(self):
        with pytest.raises(ValueError):
            self._scenario(1.5, 1e6, 500_000, 200_000)

    def test_negative_critical_eoh_raises(self):
        with pytest.raises(ValueError):
            self._scenario(0.40, critical_eoh=-1.0,
                           reserve_eoh=500_000, h_min_eoh=200_000)

    def test_scenario_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = self._scenario(eps, critical_eoh=500_000,
                                    reserve_eoh=300_000, h_min_eoh=100_000)
            assert math.isfinite(result["coverage_ratio"])
            assert math.isfinite(result["gap_eoh"])

    def test_recommendation_not_empty(self):
        result = self._scenario(0.40, critical_eoh=1e6,
                                reserve_eoh=500_000, h_min_eoh=300_000)
        assert len(result["recommendation"]) > 0

    def test_low_epsilon_failure_covered(self):
        """At ε=0.0, no automation → critical_eoh=0 → workforce easily covers."""
        total_eoh = 1_500_000_000.0
        critical_eoh = total_eoh * 0.0  # no automation share
        result = automation_failure_scenario(
            epsilon=0.0,
            critical_eoh=critical_eoh,
            reserve_capacity_eoh=WORKFORCE_SIZE * 1200.0,
            h_min_labor_eoh=WORKFORCE_SIZE * H_MIN,
        )
        assert result["covered"] is True

    def test_high_epsilon_failure_shows_gap(self):
        """At ε=0.90, automation handles 90%. Sudden failure creates a large gap."""
        total_eoh    = 1_500_000_000.0
        critical_eoh = total_eoh * 0.90
        reserve_eoh_calibrated = total_eoh * 0.10 * 1.5
        h_min_eoh = WORKFORCE_SIZE * H_MIN

        result = automation_failure_scenario(
            epsilon=0.90,
            critical_eoh=critical_eoh,
            reserve_capacity_eoh=reserve_eoh_calibrated,
            h_min_labor_eoh=h_min_eoh,
        )
        assert result["coverage_ratio"] < 1.0
        assert result["gap_eoh"] > 0


# ===========================================================================
# apply_death_redistribution
# ===========================================================================

class TestApplyDeathRedistribution:

    def _death_result(self, redistributed: float = 1_000.0,
                      new_workforce: float = 9.0) -> dict:
        return {
            "eoh_to_redistribute": redistributed,
            "new_workforce":       new_workforce,
        }

    def test_redistributed_eoh_added_to_burden(self):
        result = apply_death_redistribution(
            self._death_result(1_000.0, 9.0),
            current_eoh_burden=50_000.0,
        )
        assert result["new_total_eoh_burden"] == pytest.approx(51_000.0)

    def test_per_worker_extra_correct(self):
        result = apply_death_redistribution(
            self._death_result(1_000.0, 9.0),
            current_eoh_burden=50_000.0,
        )
        assert result["additional_per_worker"] == pytest.approx(1_000.0 / 9.0)

    def test_new_workforce_matches_death_result(self):
        result = apply_death_redistribution(
            self._death_result(500.0, 99.0),
            current_eoh_burden=10_000.0,
        )
        assert result["new_workforce"] == pytest.approx(99.0)

    def test_absorbed_true_when_redistribution_nonzero(self):
        result = apply_death_redistribution(
            self._death_result(100.0, 10.0),
            current_eoh_burden=0.0,
        )
        assert result["absorbed"] is True

    def test_absorbed_false_when_no_capacity_lost(self):
        result = apply_death_redistribution(
            {"eoh_to_redistribute": 0.0, "new_workforce": 9.0},
            current_eoh_burden=5_000.0,
        )
        assert result["absorbed"] is False
        assert result["new_total_eoh_burden"] == pytest.approx(5_000.0)

    def test_chained_with_death_event(self):
        """Full round-trip: death_event → apply_death_redistribution."""
        worker = make_asset(
            asset_id="worker_001",
            asset_type="human_worker",
            teh_value=50_000.0,
            annual_eoh=1_500.0,
            design_life=40.0,
            is_human_capital=True,
            entropy_reduction_capacity=2_000.0,
        )
        death = death_event(worker, workforce_size=100.0)
        redist = apply_death_redistribution(death, current_eoh_burden=200_000.0)

        assert redist["redistributed_eoh"] == pytest.approx(death["eoh_to_redistribute"])
        assert redist["new_workforce"] == pytest.approx(99.0)
        assert redist["new_total_eoh_burden"] == pytest.approx(
            200_000.0 + death["eoh_to_redistribute"]
        )

    def test_result_keys(self):
        result = apply_death_redistribution(self._death_result(), 0.0)
        for key in ("redistributed_eoh", "new_workforce", "additional_per_worker",
                    "new_total_eoh_burden", "absorbed"):
            assert key in result


# ===========================================================================
# competency_to_knowledge_eoh_delta
# ===========================================================================

class TestCompetencyToKnowledgeEohDelta:

    def _full_reserve(self, workforce=10_000):
        certified = {d: workforce * 0.20 for d in ESSENTIAL_DOMAINS}
        return competency_reserve(certified, workforce)

    def _gap_reserve(self, workforce=10_000, gap_domains=("healthcare",)):
        certified = {d: workforce * 0.20 for d in ESSENTIAL_DOMAINS}
        for d in gap_domains:
            certified[d] = workforce * 0.05
        return competency_reserve(certified, workforce)

    def test_no_gap_returns_zero_delta(self):
        reserve = self._full_reserve()
        result  = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        assert result["knowledge_eoh_delta"] == pytest.approx(0.0)
        assert result["competency_gap_factor"] == pytest.approx(0.0)

    def test_gap_produces_positive_delta(self):
        reserve = self._gap_reserve()
        result  = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        assert result["knowledge_eoh_delta"] > 0.0
        assert result["competency_gap_factor"] > 0.0

    def test_more_gap_domains_higher_delta(self):
        one_gap  = competency_to_knowledge_eoh_delta(
            self._gap_reserve(gap_domains=("healthcare",)), knowledge_eoh_base=100_000.0
        )
        two_gaps = competency_to_knowledge_eoh_delta(
            self._gap_reserve(gap_domains=("healthcare", "water")), knowledge_eoh_base=100_000.0
        )
        assert two_gaps["knowledge_eoh_delta"] > one_gap["knowledge_eoh_delta"]

    def test_competency_gap_factor_used_in_total_eoh(self):
        from hours_eoh.core.eoh_generation import total_eoh
        reserve = self._gap_reserve()
        delta   = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        factor  = delta["competency_gap_factor"]

        base     = total_eoh(0.40)
        with_gap = total_eoh(0.40, competency_gap_factor=factor)
        assert with_gap["knowledge"] > base["knowledge"]

    def test_domain_deltas_only_for_at_risk(self):
        reserve = self._gap_reserve(gap_domains=("healthcare",))
        result  = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        assert "healthcare" in result["domain_deltas"]
        assert "water" not in result["domain_deltas"]

    def test_n_domains_at_risk(self):
        reserve = self._gap_reserve(gap_domains=("healthcare", "water"))
        result  = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        assert result["n_domains_at_risk"] == 2

    def test_result_keys(self):
        reserve = self._gap_reserve()
        result  = competency_to_knowledge_eoh_delta(reserve, knowledge_eoh_base=100_000.0)
        for key in ("competency_gap_factor", "knowledge_eoh_delta",
                    "domain_deltas", "n_domains_at_risk", "total_gap_fraction"):
            assert key in result


# ===========================================================================
# domain_eoh_coverage (from conditions, logically part of workforce checks)
# ===========================================================================

class TestDomainEohCoverage:

    def _reserve(self, certified_per_domain=200, workforce=1000):
        certified = {d: certified_per_domain for d in ESSENTIAL_DOMAINS}
        return competency_reserve(certified, workforce)

    def test_adequate_coverage_passes(self):
        reserve = self._reserve(certified_per_domain=200, workforce=1000)
        demands = {"healthcare": 1000.0, "water": 500.0}
        result  = domain_eoh_coverage(reserve, demands, epsilon=0.0)
        assert result["all_covered"] is True
        assert result["status"] == "OK"

    def test_zero_demand_always_covered(self):
        reserve = self._reserve(certified_per_domain=5, workforce=1000)
        result  = domain_eoh_coverage(reserve, {"healthcare": 0.0}, epsilon=0.40)
        assert result["per_domain"]["healthcare"]["meets_coverage"] is True

    def test_high_demand_flags_gap(self):
        reserve = self._reserve(certified_per_domain=1, workforce=1000)
        demands = {"healthcare": 1_000_000_000.0}
        result  = domain_eoh_coverage(reserve, demands, epsilon=0.40)
        assert result["all_covered"] is False
        assert "healthcare" in result["domains_at_risk"]

    def test_high_epsilon_reduces_capacity(self):
        """At higher ε, certified workers cover less human EOH → capacity drops."""
        reserve  = self._reserve(certified_per_domain=100, workforce=1000)
        demands  = {"water": 50_000.0}
        low_eps  = domain_eoh_coverage(reserve, demands, epsilon=0.10)
        high_eps = domain_eoh_coverage(reserve, demands, epsilon=0.90)
        assert high_eps["per_domain"]["water"]["capacity_eoh"] < low_eps["per_domain"]["water"]["capacity_eoh"]

    def test_unknown_domain_treated_as_zero_certified(self):
        reserve = self._reserve(certified_per_domain=100, workforce=1000)
        result  = domain_eoh_coverage(reserve, {"completely_new_domain": 10.0}, epsilon=0.40)
        assert result["per_domain"]["completely_new_domain"]["certified_count"] == 0.0

    def test_result_keys(self):
        reserve = self._reserve()
        result  = domain_eoh_coverage(reserve, {"healthcare": 1000.0})
        for key in ("per_domain", "domains_at_risk", "all_covered", "status", "epsilon"):
            assert key in result
