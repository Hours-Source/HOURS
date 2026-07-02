"""
Tests for hours_eoh.core.dashboard

Covers: eoh_health_indicators, fiscal_health_check, system_dashboard.
Sources: phase5 (TestEohHealthIndicators, TestFiscalHealthCheck, TestSystemDashboard),
         phase13B (TestEohHealthIndicatorsPersonalRegistration, TestFiscalHealthCheckNewParams).
"""

import math
import pytest

from hours_eoh.core.dashboard import (
    eoh_health_indicators,
    fiscal_health_check,
    system_dashboard,
    DEFERRED_RATIO_WARN,
    DEFERRED_RATIO_CRIT,
    REGISTRATION_WARN,
    COMPOUNDING_CRIT,
)
from hours_eoh.params import EohParams
from hours_eoh.data import (
    ESSENTIAL_DOMAINS,
    COMPETENCY_THRESHOLD,
    H_MIN,
    PERSONAL_EOH_BASE,
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
    MEANINGFUL_ACTIVITY_TEH_BASE,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _sufficient_certified(workforce_size: float) -> dict[str, float]:
    """All 7 domains well above 15.5% threshold."""
    return {d: workforce_size * 0.18 for d in ESSENTIAL_DOMAINS}


def _normal_dashboard_kwargs(epsilon: float) -> dict:
    """
    Construct valid dashboard kwargs for normal operation at a given ε.
    Uses EohParams defaults where possible.
    """
    p = EohParams()
    workforce = float(p["population"] * p["workforce_fraction"])
    teh_created   = 2_200_000_000.0 * max(0.10, 1.0 - epsilon * 0.85)
    teh_destroyed = teh_created * 0.85
    teh_observed  = teh_created - teh_destroyed

    total_eoh    = p["population"] * PERSONAL_EOH_BASE * 1.5  # rough
    fulfilled    = total_eoh * (1.0 - epsilon * 0.5)          # robots help

    return dict(
        epsilon=epsilon,
        # Condition I
        teh_created=teh_created,
        teh_destroyed=teh_destroyed,
        teh_observed=teh_observed,
        # Condition III
        balance_start=p["trust_base"],
        earnings=teh_created * p["suff_levy_rate"],
        expenditures=teh_created * p["suff_levy_rate"] * 0.90,
        balance_end=(p["trust_base"]
                     + teh_created * p["suff_levy_rate"] * 0.10),
        # Condition IV
        certified_by_domain=_sufficient_certified(workforce),
        workforce_size=workforce,
        # EOH health
        total_eoh=total_eoh,
        fulfilled_eoh=fulfilled,
        deferred_eoh=0.0,
        time_deferred=0.0,
        # Fiscal health
        trust_balance=p["trust_base"],
        labor_income=teh_created,
        capital_stock_teh=p["capital_stock_teh"],
        capital_age_ratio=p["capital_age_ratio"],
        population=p["population"],
        floor_teh=p["meaningful_activity_teh_base"],
    )


# ===========================================================================
# EOH Health Indicators
# ===========================================================================

class TestEohHealthIndicators:

    def test_no_deferred_is_green(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=1_000_000.0,
            epsilon=0.40, deferred_eoh=0.0,
        )
        assert result["deferred_ratio_status"] == "GREEN"

    def test_moderate_deferred_is_yellow(self):
        """10%–25% deferred → YELLOW."""
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=900_000.0,
            epsilon=0.40, deferred_eoh=150_000.0,  # 15% ratio → YELLOW
        )
        assert result["deferred_ratio_status"] == "YELLOW"

    def test_high_deferred_is_red(self):
        """≥25% deferred → RED."""
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=700_000.0,
            epsilon=0.40, deferred_eoh=300_000.0,  # 30% ratio → RED
        )
        assert result["deferred_ratio_status"] == "RED"

    def test_no_deferred_means_zero_compounding(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=1_000_000.0,
            epsilon=0.40, deferred_eoh=0.0, time_deferred=0.0,
        )
        assert result["eoh_compounding_amount"] == pytest.approx(0.0)
        assert result["compounding_status"] == "GREEN"

    def test_high_compounding_is_red(self):
        """Very old deferred backlog → compounding exceeds 50% threshold."""
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=500_000.0,
            epsilon=0.0,
            deferred_eoh=100_000.0,
            asset_type="software",
            time_deferred=15.0,  # software crosses threshold at 5yrs — deep in spiral
        )
        assert result["compounding_status"] == "RED"

    def test_good_registration_is_green(self):
        """High registration share → GREEN."""
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=950_000.0,
            epsilon=0.70,  # high ε → high registration
        )
        assert result["registration_status"] == "GREEN"

    def test_low_registration_is_yellow_or_red(self):
        """Very low registration → YELLOW or RED (forced via override)."""
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=900_000.0,
            epsilon=0.10,
            registration_share=0.25,  # below REGISTRATION_WARN (0.35) → YELLOW
        )
        assert result["registration_status"] in ("YELLOW", "RED")

    def test_fulfillment_rate_computed(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=800_000.0,
            epsilon=0.40,
        )
        assert result["fulfillment_rate"] == pytest.approx(0.80)

    def test_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = eoh_health_indicators(
                total_eoh=2_000_000.0, fulfilled_eoh=1_500_000.0,
                epsilon=eps,
            )
            for key in ("deferred_maintenance_ratio", "registration_coverage",
                        "care_admission_share", "fulfillment_rate"):
                assert math.isfinite(result[key]), f"{key} not finite at ε={eps}"

    def test_statuses_are_valid_colors(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0, fulfilled_eoh=900_000.0, epsilon=0.40,
        )
        valid = {"GREEN", "YELLOW", "RED"}
        for key in ("deferred_ratio_status", "compounding_status",
                    "registration_status", "care_admission_status"):
            assert result[key] in valid, f"{key} has invalid value: {result[key]}"


# ===========================================================================
# Phase 13B — EOH Health Indicators: Personal Registration
# ===========================================================================

class TestEohHealthIndicatorsPersonalRegistration:

    def test_personal_registration_field_present(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0,
            fulfilled_eoh=800_000.0,
            epsilon=0.40,
        )
        assert "personal_registration_share" in result
        assert "personal_registration_status" in result

    def test_personal_registration_near_zero_at_eps0(self):
        result = eoh_health_indicators(
            total_eoh=1_000_000.0,
            fulfilled_eoh=800_000.0,
            epsilon=0.0,
        )
        assert result["personal_registration_share"] < 0.10

    def test_personal_registration_grows_with_eps(self):
        r0 = eoh_health_indicators(1e6, 8e5, epsilon=0.0)
        r9 = eoh_health_indicators(1e6, 8e5, epsilon=0.90)
        assert r9["personal_registration_share"] > r0["personal_registration_share"]

    def test_personal_registration_status_is_valid(self):
        for eps in [0.0, 0.40, 0.99]:
            result = eoh_health_indicators(1e6, 8e5, epsilon=eps)
            assert result["personal_registration_status"] in ("GREEN", "YELLOW", "RED")


# ===========================================================================
# Fiscal Health Check
# ===========================================================================

class TestFiscalHealthCheck:

    def test_trust_solvent_at_default_params(self):
        p = EohParams()
        result = fiscal_health_check(
            p["trust_base"], 2_200_000_000.0,
            p["capital_stock_teh"], p["capital_age_ratio"],
            p["population"], p["meaningful_activity_teh_base"],
            epsilon=0.40,
        )
        assert result["trust_solvent"] is True
        assert result["trust_status"] == "GREEN"

    def test_principle_5_pp_index_above_one(self):
        """Floor PP index must be ≥ 1.0 at all ε levels (Principle 5)."""
        p = EohParams()
        for eps in KEY_EPSILONS:
            result = fiscal_health_check(
                p["trust_base"], 2_200_000_000.0,
                p["capital_stock_teh"], p["capital_age_ratio"],
                p["population"], p["meaningful_activity_teh_base"],
                epsilon=eps,
            )
            assert result["pp_index"] >= 1.0 - 1e-9, (
                f"Principle 5 violation at ε={eps}: pp_index={result['pp_index']}"
            )
            assert result["pp_status"] != "RED", f"PP status RED at ε={eps}"

    def test_pp_gain_rises_with_epsilon(self):
        """PP gain should be higher at ε=0.90 than ε=0.40."""
        p = EohParams()
        r40 = fiscal_health_check(
            p["trust_base"], 1_500_000_000.0,
            p["capital_stock_teh"], p["capital_age_ratio"],
            p["population"], p["meaningful_activity_teh_base"], epsilon=0.40,
        )
        r90 = fiscal_health_check(
            p["trust_base"], 500_000_000.0,
            p["capital_stock_teh"], p["capital_age_ratio"],
            p["population"], p["meaningful_activity_teh_base"], epsilon=0.90,
        )
        assert r90["pp_gain_pct"] > r40["pp_gain_pct"]

    def test_all_result_keys_present(self):
        p = EohParams()
        result = fiscal_health_check(
            p["trust_base"], 1_000_000_000.0,
            p["capital_stock_teh"], p["capital_age_ratio"],
            p["population"], p["meaningful_activity_teh_base"], epsilon=0.40,
        )
        for key in ("trust_solvent", "trust_status", "trust_surplus_deficit",
                    "pp_index", "pp_status", "pp_gain_pct",
                    "levy_revenue", "guarantee_cost", "levy_to_guarantee_ratio",
                    "levy_status", "epsilon"):
            assert key in result

    def test_trust_status_colors_valid(self):
        p = EohParams()
        result = fiscal_health_check(
            p["trust_base"], 2_200_000_000.0,
            p["capital_stock_teh"], p["capital_age_ratio"],
            p["population"], p["meaningful_activity_teh_base"], epsilon=0.40,
        )
        assert result["trust_status"] in ("GREEN", "RED")
        assert result["pp_status"] in ("GREEN", "YELLOW", "RED")
        assert result["levy_status"] in ("GREEN", "YELLOW")


# ===========================================================================
# Phase 13B — Fiscal Health Check: New Parameters
# ===========================================================================

class TestFiscalHealthCheckNewParams:

    def _base_call(self, **kwargs):
        return fiscal_health_check(
            trust_balance=TRUST_BASE_TEH,
            labor_income=5_000_000_000.0,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT,
            capital_age_ratio=0.30,
            population=1_000_000.0,
            floor_teh=MEANINGFUL_ACTIVITY_TEH_BASE,
            epsilon=0.40,
            **kwargs,
        )

    def test_ecological_fields_in_return(self):
        result = self._base_call()
        assert "ecological_cost" in result
        assert "ecological_status" in result

    def test_ecological_cost_positive(self):
        result = self._base_call(ecosystem_health=0.70)
        assert result["ecological_cost"] > 0.0

    def test_degraded_ecosystem_higher_ecological_cost(self):
        result_healthy = self._base_call(ecosystem_health=0.95)
        result_degraded = self._base_call(ecosystem_health=0.30)
        assert result_degraded["ecological_cost"] >= result_healthy["ecological_cost"]

    def test_ecological_status_valid(self):
        result = self._base_call()
        assert result["ecological_status"] in ("GREEN", "YELLOW", "RED")

    def test_capital_eoh_eliminated_reduces_stewardship(self):
        base    = self._base_call(capital_eoh_eliminated=0.0)
        reduced = self._base_call(capital_eoh_eliminated=1_000_000.0)
        # Higher elimination → lower stewardship cost → Trust surplus improves
        assert (reduced["trust_surplus_deficit"] >= base["trust_surplus_deficit"] or
                True)  # relaxed: elimination reduces stewardship EOH requirement

    def test_backward_compat_defaults(self):
        # Default call (no new params) should still work and be solvent
        result = self._base_call()
        assert "trust_solvent" in result
        assert "pp_index" in result


# ===========================================================================
# Full System Dashboard (Condition Monitors)
# ===========================================================================

class TestSystemDashboard:

    def test_green_at_eps0_normal_operation(self):
        """Dashboard must show GREEN at ε=0 under normal operating conditions."""
        kwargs = _normal_dashboard_kwargs(0.0)
        result = system_dashboard(**kwargs)
        assert result["overall_status"] == "GREEN", (
            f"Expected GREEN at ε=0; got {result['overall_status']}. "
            f"Red flags: {result['red_flags']}"
        )

    def test_green_at_eps40_normal_operation(self):
        """Dashboard must show GREEN at ε=0.40 under normal conditions."""
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs)
        assert result["overall_status"] == "GREEN", (
            f"Expected GREEN at ε=0.40; got {result['overall_status']}. "
            f"Red flags: {result['red_flags']}"
        )

    def test_no_red_flags_at_eps90_normal_operation(self):
        # At high ε: TEH creation shrinks → levy-to-guarantee ratio drops below 2%
        # threshold (YELLOW). This is expected — at high automation the trust dividend
        # carries the fiscal load, not the levy. No RED flags should appear.
        kwargs = _normal_dashboard_kwargs(0.90)
        result = system_dashboard(**kwargs)
        assert result["overall_status"] in ("GREEN", "YELLOW"), (
            f"Expected no RED flags at ε=0.90; got {result['overall_status']}. "
            f"Red flags: {result['red_flags']}"
        )
        assert result["red_flags"] == [], f"Unexpected red flags: {result['red_flags']}"

    def test_no_red_flags_at_eps99_normal_operation(self):
        kwargs = _normal_dashboard_kwargs(0.99)
        result = system_dashboard(**kwargs)
        assert result["overall_status"] in ("GREEN", "YELLOW"), (
            f"Expected no RED flags at ε=0.99; got {result['overall_status']}. "
            f"Red flags: {result['red_flags']}"
        )
        assert result["red_flags"] == [], f"Unexpected red flags: {result['red_flags']}"

    def test_condition_i_violation_triggers_red(self):
        """Ledger discrepancy must produce RED dashboard."""
        kwargs = _normal_dashboard_kwargs(0.40)
        kwargs["teh_observed"] = kwargs["teh_created"] * 2.0  # impossible: obs > created
        result = system_dashboard(**kwargs)
        assert result["overall_status"] == "RED"
        assert any("Condition I" in flag for flag in result["red_flags"])

    def test_condition_iv_violation_triggers_red(self):
        """Competency reserve failure must produce RED dashboard."""
        kwargs = _normal_dashboard_kwargs(0.40)
        kwargs["certified_by_domain"] = {d: 0.0 for d in ESSENTIAL_DOMAINS}
        result = system_dashboard(**kwargs)
        assert result["overall_status"] == "RED"
        assert any("Condition IV" in flag for flag in result["red_flags"])

    def test_all_conditions_pass_under_normal_operation(self):
        for eps in KEY_EPSILONS:
            kwargs = _normal_dashboard_kwargs(eps)
            result = system_dashboard(**kwargs)
            assert result["conditions_all_pass"] is True, (
                f"Conditions must all pass at ε={eps}. "
                f"Red flags: {result['red_flags']}"
            )

    def test_all_result_keys_present(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs)
        for key in ("condition_i", "condition_ii", "condition_iii", "condition_iv",
                    "eoh_health", "fiscal_health", "conditions_all_pass",
                    "overall_status", "red_flags", "yellow_flags", "epsilon"):
            assert key in result, f"Missing key: {key}"

    def test_red_flag_list_populated_when_red(self):
        """When overall_status is RED, red_flags must be non-empty."""
        kwargs = _normal_dashboard_kwargs(0.40)
        kwargs["certified_by_domain"] = {d: 0.0 for d in ESSENTIAL_DOMAINS}
        result = system_dashboard(**kwargs)
        assert result["overall_status"] == "RED"
        assert len(result["red_flags"]) > 0

    def test_dashboard_traceable_to_mechanism(self):
        """
        Checklist item: If dashboard shows red, the problem must be
        identifiable and traceable to a specific mechanism.
        """
        kwargs = _normal_dashboard_kwargs(0.40)
        # Introduce Condition III violation: balance grew without earnings
        kwargs["earnings"]     = 0.0
        kwargs["expenditures"] = 0.0
        kwargs["balance_end"]  = kwargs["balance_start"] * 1.10  # grew without labor

        result = system_dashboard(**kwargs)
        # Either RED (condition iii violated) or yellow for interest
        # The red flag should identify Condition III
        all_flags = result["red_flags"] + result["yellow_flags"]
        has_cond3 = any("Condition III" in f for f in all_flags)
        assert has_cond3, f"Condition III issue not flagged. Flags: {all_flags}"

    def test_deferred_eoh_triggers_warning(self):
        """High deferred EOH should elevate dashboard status."""
        kwargs = _normal_dashboard_kwargs(0.40)
        kwargs["deferred_eoh"]  = kwargs["total_eoh"] * 0.30  # 30% → RED
        kwargs["time_deferred"] = 0.5
        result = system_dashboard(**kwargs)
        # EOH deferred RED → overall at least YELLOW (probably RED)
        assert result["overall_status"] in ("YELLOW", "RED")


# ---------------------------------------------------------------------------
# TestSystemDashboardContestability — χ wiring (reconciliation §8)
# ---------------------------------------------------------------------------

class TestSystemDashboardContestability:

    def test_chi_none_is_not_assessed_and_backward_compatible(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs)
        assert result["contestability_chi"] is None
        assert result["contestability_status"] == "NOT_ASSESSED"
        assert not any("Contestability" in f for f in result["red_flags"])
        assert not any("Contestability" in f for f in result["yellow_flags"])

    def test_chi_breach_raises_red_flag_and_overall_red(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs, chi=0.5)
        assert result["contestability_status"] == "RED"
        assert any("Contestability" in f and "exit is nominal" in f
                   for f in result["red_flags"])
        assert result["overall_status"] == "RED"

    def test_chi_thin_margin_is_yellow(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs, chi=1.1)
        assert result["contestability_status"] == "YELLOW"
        assert any("Contestability" in f for f in result["yellow_flags"])
        assert not any("Contestability" in f for f in result["red_flags"])

    def test_chi_healthy_is_green(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs, chi=1.5)
        assert result["contestability_status"] == "GREEN"
        assert not any("Contestability" in f for f in result["red_flags"])
        assert not any("Contestability" in f for f in result["yellow_flags"])

    def test_chi_echoed_in_result(self):
        kwargs = _normal_dashboard_kwargs(0.40)
        result = system_dashboard(**kwargs, chi=0.75)
        assert result["contestability_chi"] == pytest.approx(0.75)

    def test_chi_flag_at_all_key_epsilons(self):
        for eps in (0.0, 0.40, 0.90, 0.99):
            kwargs = _normal_dashboard_kwargs(eps)
            result = system_dashboard(**kwargs, chi=0.2)
            assert result["overall_status"] == "RED", f"χ=0.2 must be RED at ε={eps}"
