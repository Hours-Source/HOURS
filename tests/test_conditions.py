"""
Tests for hours_eoh.core.conditions

Covers: condition_i_check, condition_ii_check, balance_check,
condition_iv_check, dashboard_snapshot, domain_eoh_coverage,
condition_iii_balance_growth_check.
"""

import math
import pytest

from hours_eoh.core.conditions import (
    condition_i_check,
    condition_ii_check,
    balance_check,
    condition_iv_check,
    dashboard_snapshot,
    domain_eoh_coverage,
    condition_iii_balance_growth_check,
)
from hours_eoh.core.eoh_generation import total_eoh, eoh_to_essential_domains
from hours_eoh.core.workforce import competency_reserve
from hours_eoh.data import ESSENTIAL_DOMAINS, COMPETENCY_THRESHOLD, TRUST_BASE_TEH

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# condition_i_check
# ===========================================================================

class TestConditionI:

    def test_passes_when_supply_matches(self):
        """Condition I holds when ledger is correct."""
        created   = 10_000_000.0
        destroyed =  4_000_000.0
        observed  =  6_000_000.0  # = created - destroyed exactly
        result = condition_i_check(created, destroyed, observed, tolerance=1e-6)
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_fails_on_discrepancy(self):
        created   = 10_000_000.0
        destroyed =  4_000_000.0
        observed  =  6_001_000.0  # 1000 TEH extra — a ledger violation
        result = condition_i_check(created, destroyed, observed, tolerance=1e-6)
        assert result["passes"] is False
        assert result["status"] == "LEDGER_VIOLATION"


# ===========================================================================
# balance_check (Condition III)
# ===========================================================================

class TestBalanceCheck:

    def test_passes_exact(self):
        """Zero interest holds."""
        result = balance_check(
            balance_start=1000.0,
            earnings=500.0,
            expenditures=300.0,
            balance_end=1200.0,  # = 1000 + 500 - 300
        )
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_fails_with_phantom_growth(self):
        """Phantom growth (interest) is flagged as a violation."""
        result = balance_check(
            balance_start=1000.0,
            earnings=500.0,
            expenditures=300.0,
            balance_end=1250.0,  # 50 TEH extra — interest or error
        )
        assert result["passes"] is False
        assert result["status"] == "INTEREST_VIOLATION"

    def test_levy_is_circulatory(self):
        """
        Levies move TEH but don't destroy it. Worker pays levy → expenditure.
        Trust receives levy → earning. Both accounts satisfy Condition III.
        """
        levy_amount = 100.0

        # Worker account
        worker_result = balance_check(
            balance_start=500.0,
            earnings=200.0,
            expenditures=100.0 + levy_amount,  # levy is an expenditure
            balance_end=500.0,                  # confirmed: 500 + 200 - 200 = 500
        )
        assert worker_result["passes"] is True

        # Trust account
        trust_result = balance_check(
            balance_start=10_000.0,
            earnings=levy_amount,  # levy received is an earning
            expenditures=0.0,
            balance_end=10_100.0,  # 10000 + 100 - 0 = 10100
        )
        assert trust_result["passes"] is True

    def test_zero_activity(self):
        """No earnings, no expenditures → balance unchanged."""
        result = balance_check(
            balance_start=5000.0,
            earnings=0.0,
            expenditures=0.0,
            balance_end=5000.0,
        )
        assert result["passes"] is True


# ===========================================================================
# condition_iv_check
# ===========================================================================

class TestConditionIV:

    def test_passes_at_threshold(self):
        workforce = 1_000_000.0
        competent = 155_000.0  # exactly 15.5%
        result = condition_iv_check(workforce, competent)
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_fails_below_threshold(self):
        workforce = 1_000_000.0
        competent = 100_000.0  # only 10%
        result = condition_iv_check(workforce, competent)
        assert result["passes"] is False
        assert result["status"] == "COMPETENCY_DEFICIT"

    def test_domain_gap_status(self):
        """Aggregate passes but a specific domain is deficient."""
        workforce = 1_000_000.0
        competent = 200_000.0  # 20% → aggregate passes
        domain_cov = {
            "agriculture": 1.2,  # above minimum
            "water": 0.8,        # below minimum → DOMAIN_GAP
        }
        result = condition_iv_check(workforce, competent, domain_coverage=domain_cov)
        assert result["passes"] is True
        assert result["status"] == "DOMAIN_GAP"


# ===========================================================================
# dashboard_snapshot
# ===========================================================================

class TestDashboardSnapshot:

    def _green_snapshot_kwargs(self, epsilon: float) -> dict:
        """Build a set of arguments that should produce a green dashboard."""
        teh_created_total   = 10_000_000.0
        teh_destroyed_total =  4_000_000.0
        teh_in_circulation  =  6_000_000.0   # matches created - destroyed
        return dict(
            teh_created=teh_created_total,
            teh_destroyed=teh_destroyed_total,
            teh_observed=teh_in_circulation,
            mean_multiplier=2.0,            # in band [1.8, 2.1]
            balance_start=1000.0,
            earnings=500.0,
            expenditures=300.0,
            balance_end=1200.0,             # 1000 + 500 - 300 exactly
            workforce=1_000_000.0,
            competent_workers=200_000.0,    # 20% > 15.5% threshold
            epsilon=epsilon,
        )

    def test_green_at_all_key_epsilons(self):
        """Dashboard shows green for all conditions under normal operation."""
        for eps in KEY_EPSILONS:
            result = dashboard_snapshot(**self._green_snapshot_kwargs(eps))
            assert result["all_pass"] is True, (
                f"Dashboard should be green at ε={eps}; failing conditions: "
                + ", ".join(
                    k for k in ("condition_i", "condition_ii", "condition_iii", "condition_iv")
                    if not result[k].get("passes", result[k].get("in_band", False))
                )
            )
            assert result["overall_status"] == "GREEN"

    def test_red_on_multiplier_violation(self):
        kwargs = self._green_snapshot_kwargs(0.40)
        kwargs["mean_multiplier"] = 2.8  # above band
        result = dashboard_snapshot(**kwargs)
        assert result["all_pass"] is False
        assert result["overall_status"] == "RED"
        assert result["condition_ii"]["in_band"] is False

    def test_red_on_ledger_violation(self):
        kwargs = self._green_snapshot_kwargs(0.40)
        kwargs["teh_observed"] = 7_000_000.0  # 1M extra → ledger violation
        result = dashboard_snapshot(**kwargs)
        assert result["all_pass"] is False
        assert result["condition_i"]["status"] == "LEDGER_VIOLATION"

    def test_red_on_interest_violation(self):
        kwargs = self._green_snapshot_kwargs(0.40)
        kwargs["balance_end"] = 2000.0  # should be 1200; extra 800 = phantom growth
        result = dashboard_snapshot(**kwargs)
        assert result["all_pass"] is False
        assert result["condition_iii"]["status"] == "INTEREST_VIOLATION"


# ===========================================================================
# domain_eoh_coverage
# ===========================================================================

class TestDomainEohCoverage:

    def _reserve(self, certified_per_domain=200, workforce=1000):
        certified = {d: certified_per_domain for d in [
            "healthcare", "water", "energy", "agriculture", "logistics", "manufacturing", "construction"
        ]}
        return competency_reserve(certified, workforce)

    def test_adequate_coverage_passes(self):
        reserve  = self._reserve(certified_per_domain=200, workforce=1000)
        demands  = {"healthcare": 1000.0, "water": 500.0}  # small demands → covered
        result   = domain_eoh_coverage(reserve, demands, epsilon=0.0)
        assert result["all_covered"] is True
        assert result["status"] == "OK"

    def test_zero_demand_always_covered(self):
        reserve = self._reserve(certified_per_domain=5, workforce=1000)
        result  = domain_eoh_coverage(reserve, {"healthcare": 0.0}, epsilon=0.40)
        assert result["per_domain"]["healthcare"]["meets_coverage"] is True

    def test_high_demand_flags_gap(self):
        reserve = self._reserve(certified_per_domain=1, workforce=1000)
        demands = {"healthcare": 1_000_000_000.0}  # impossible to cover with 1 worker
        result  = domain_eoh_coverage(reserve, demands, epsilon=0.40)
        assert result["all_covered"] is False
        assert "healthcare" in result["domains_at_risk"]

    def test_high_epsilon_reduces_capacity(self):
        reserve    = self._reserve(certified_per_domain=100, workforce=1000)
        demands    = {"water": 50_000.0}
        low_eps    = domain_eoh_coverage(reserve, demands, epsilon=0.10)
        high_eps   = domain_eoh_coverage(reserve, demands, epsilon=0.90)
        # At higher ε, certified workers cover less human EOH → capacity drops
        low_cap    = low_eps["per_domain"]["water"]["capacity_eoh"]
        high_cap   = high_eps["per_domain"]["water"]["capacity_eoh"]
        assert high_cap < low_cap

    def test_unknown_domain_treated_as_zero_certified(self):
        reserve = self._reserve(certified_per_domain=100, workforce=1000)
        result  = domain_eoh_coverage(reserve, {"completely_new_domain": 10.0}, epsilon=0.40)
        assert result["per_domain"]["completely_new_domain"]["certified_count"] == 0.0

    def test_result_keys(self):
        reserve = self._reserve()
        result  = domain_eoh_coverage(reserve, {"healthcare": 1000.0})
        for key in ("per_domain", "domains_at_risk", "all_covered", "status", "epsilon"):
            assert key in result

    def test_round_trip_with_eoh_to_essential_domains(self):
        """eoh_to_essential_domains() output must feed domain_eoh_coverage() correctly."""
        from hours_eoh.data import COMPETENCY_THRESHOLD
        eoh = {k: total_eoh(0.40)[k]
               for k in ("personal", "infrastructure", "ecological", "knowledge")}
        essential = eoh_to_essential_domains(eoh)
        workforce = 600_000.0
        threshold_count = workforce * COMPETENCY_THRESHOLD
        certified = {d: threshold_count for d in ESSENTIAL_DOMAINS}
        reserve = competency_reserve(certified, workforce_size=workforce)
        result = domain_eoh_coverage(reserve, essential, epsilon=0.40)
        assert "all_covered" in result
        assert "per_domain" in result

    def test_all_essential_domains_checked(self):
        eoh = {k: total_eoh(0.40)[k]
               for k in ("personal", "infrastructure", "ecological", "knowledge")}
        essential = eoh_to_essential_domains(eoh)
        from hours_eoh.data import COMPETENCY_THRESHOLD
        workforce = 600_000.0
        certified = {d: workforce * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}
        reserve = competency_reserve(certified, workforce_size=workforce)
        result = domain_eoh_coverage(reserve, essential, epsilon=0.40)
        for domain in ESSENTIAL_DOMAINS:
            assert domain in result["per_domain"]

    def test_coverage_ratios_finite(self):
        eoh = {k: total_eoh(0.40)[k]
               for k in ("personal", "infrastructure", "ecological", "knowledge")}
        essential = eoh_to_essential_domains(eoh)
        from hours_eoh.data import COMPETENCY_THRESHOLD
        workforce = 600_000.0
        certified = {d: workforce * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}
        reserve = competency_reserve(certified, workforce_size=workforce)
        result = domain_eoh_coverage(reserve, essential, epsilon=0.40)
        for domain, info in result["per_domain"].items():
            assert math.isfinite(info["coverage_ratio"])

    def test_status_field_valid(self):
        eoh = {k: total_eoh(0.40)[k]
               for k in ("personal", "infrastructure", "ecological", "knowledge")}
        essential = eoh_to_essential_domains(eoh)
        from hours_eoh.data import COMPETENCY_THRESHOLD
        workforce = 600_000.0
        certified = {d: workforce * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}
        reserve = competency_reserve(certified, workforce_size=workforce)
        result = domain_eoh_coverage(reserve, essential, epsilon=0.40)
        assert result["status"] in ("OK", "COVERAGE_GAP")


# ===========================================================================
# condition_iii_balance_growth_check
# ===========================================================================

class TestConditionIIIBalanceGrowthCheck:

    def test_exact_match_passes(self):
        result = condition_iii_balance_growth_check(
            prev_balance=1000.0,
            new_balance=1200.0,
            labor_income=500.0,
            expenditure=300.0,
        )
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_interest_violation_detected(self):
        # Balance grew by 300 but income - expenditure = 200 → 100 unaccounted
        result = condition_iii_balance_growth_check(
            prev_balance=1000.0,
            new_balance=1300.0,
            labor_income=500.0,
            expenditure=300.0,
        )
        assert result["passes"] is False
        assert result["status"] == "INTEREST_VIOLATION"

    def test_zero_income_zero_expenditure_stable_balance(self):
        result = condition_iii_balance_growth_check(
            prev_balance=5000.0,
            new_balance=5000.0,
            labor_income=0.0,
            expenditure=0.0,
        )
        assert result["passes"] is True

    def test_declining_balance_passes(self):
        # Spending more than earning → balance declines — valid
        result = condition_iii_balance_growth_check(
            prev_balance=1000.0,
            new_balance=700.0,
            labor_income=100.0,
            expenditure=400.0,
        )
        assert result["passes"] is True

    def test_tolerance_boundary(self):
        # Discrepancy within tolerance passes
        result = condition_iii_balance_growth_check(
            prev_balance=1_000_000.0,
            new_balance=1_000_000.001,  # tiny floating-point artifact
            labor_income=0.0,
            expenditure=0.0,
            tolerance=1e-6,
        )
        assert result["passes"] is True

    def test_returns_expected_end(self):
        result = condition_iii_balance_growth_check(
            prev_balance=100.0,
            new_balance=130.0,
            labor_income=50.0,
            expenditure=20.0,
        )
        assert result["expected_end"] == pytest.approx(130.0)

    def test_trust_balance_evolution(self):
        # Simulate one period of Trust: levy in, stewardship out
        prev = TRUST_BASE_TEH
        levy_in = 50_000_000.0
        stew_out = 30_000_000.0
        new = prev + levy_in - stew_out
        result = condition_iii_balance_growth_check(prev, new, levy_in, stew_out)
        assert result["passes"] is True
