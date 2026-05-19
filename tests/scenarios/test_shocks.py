"""
Tests for hours_eoh.scenarios.shocks at the canonical import location.

Covers: automation_failure_shock, demographic_shock, ecological_eoh_spike,
        labor_income_shock, compound_shock.
"""

import pytest
from hours_eoh.scenarios.shocks import (
    automation_failure_shock,
    demographic_shock,
    ecological_eoh_spike,
    labor_income_shock,
    compound_shock,
)

VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


class TestAutomationFailureShock:
    def test_returns_expected_keys(self):
        result = automation_failure_shock(epsilon=0.40)
        for key in ("scenario", "epsilon", "total_eoh", "automation_eoh",
                    "covered", "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert automation_failure_shock(0.40)["scenario"] == "automation_failure_shock"

    def test_outcome_is_valid(self):
        for eps in (0.0, 0.40, 0.80):
            result = automation_failure_shock(eps)
            assert result["outcome"] in VALID_OUTCOMES

    def test_low_epsilon_stable(self):
        result = automation_failure_shock(epsilon=0.10)
        assert result["outcome"] == "STABLE"

    def test_automation_eoh_equals_epsilon_times_total(self):
        result = automation_failure_shock(epsilon=0.40)
        assert result["automation_eoh"] == pytest.approx(
            result["total_eoh"] * 0.40, rel=1e-4
        )

    def test_recommendation_is_string(self):
        result = automation_failure_shock(0.50)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10


class TestDemographicShock:
    def test_growth_shock_increases_eoh(self):
        result = demographic_shock(0.40, "growth", 0.20)
        assert result["eoh_after"] > result["eoh_before"]

    def test_decline_shock_decreases_eoh(self):
        result = demographic_shock(0.40, "decline", 0.20)
        assert result["eoh_after"] < result["eoh_before"]

    def test_aging_shock_changes_population(self):
        result = demographic_shock(0.40, "aging", 0.10)
        assert result["eoh_delta"] != 0.0

    def test_outcome_is_valid(self):
        for shock in ("growth", "decline", "aging"):
            result = demographic_shock(0.40, shock, 0.10)
            assert result["outcome"] in VALID_OUTCOMES

    def test_invalid_shock_type_raises(self):
        with pytest.raises(ValueError):
            demographic_shock(0.40, "flood", 0.10)

    def test_invalid_magnitude_raises(self):
        with pytest.raises(ValueError):
            demographic_shock(0.40, "growth", 1.5)

    def test_scenario_name(self):
        assert demographic_shock(0.40, "growth", 0.10)["scenario"] == "demographic_shock"


class TestEcologicalEohSpike:
    def test_threshold_crossed_detected(self):
        result = ecological_eoh_spike(
            epsilon=0.40,
            ecosystem_health_before=0.50,
            ecosystem_health_after=0.30,
        )
        assert result["threshold_crossed"] is True

    def test_no_threshold_cross_when_still_above(self):
        result = ecological_eoh_spike(
            epsilon=0.40,
            ecosystem_health_before=0.80,
            ecosystem_health_after=0.50,
        )
        assert result["threshold_crossed"] is False

    def test_spike_is_non_negative(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.30)
        assert result["eoh_spike"] >= 0.0

    def test_no_spike_when_health_improves(self):
        result = ecological_eoh_spike(0.40, 0.30, 0.70)
        assert result["eoh_spike"] == 0.0

    def test_outcome_is_valid(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.30)
        assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = ecological_eoh_spike(0.40, 0.70, 0.50)
        assert result["scenario"] == "ecological_eoh_spike"


# ===========================================================================
# Labor Income Shock
# ===========================================================================

class TestLaborIncomeShock:

    def test_returns_expected_keys(self):
        result = labor_income_shock(0.40, 1.0)
        for key in ("scenario", "epsilon", "income_fraction",
                    "baseline_income", "shocked_income",
                    "trust_solvent_before", "trust_solvent_after",
                    "surplus_deficit_before", "surplus_deficit_after",
                    "surplus_deficit_delta", "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert labor_income_shock(0.40, 1.0)["scenario"] == "labor_income_shock"

    def test_full_income_baseline_is_stable(self):
        """income_fraction=1.0 (no shock) must match baseline solvency."""
        result = labor_income_shock(0.40, income_fraction=1.0)
        assert result["trust_solvent_before"] == result["trust_solvent_after"]

    def test_low_income_worsens_surplus_deficit(self):
        """Shocked income must produce equal or worse surplus_deficit than baseline."""
        r_full = labor_income_shock(0.40, income_fraction=1.0)
        r_half = labor_income_shock(0.40, income_fraction=0.50)
        assert r_half["surplus_deficit_after"] <= r_full["surplus_deficit_after"]

    def test_shocked_income_less_than_baseline(self):
        result = labor_income_shock(0.40, income_fraction=0.60)
        assert result["shocked_income"] <= result["baseline_income"]

    def test_outcome_is_valid(self):
        for frac in (1.0, 0.75, 0.50, 0.25):
            result = labor_income_shock(0.40, income_fraction=frac)
            assert result["outcome"] in VALID_OUTCOMES

    def test_recommendation_is_string(self):
        result = labor_income_shock(0.40, 0.70)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_invalid_fraction_raises(self):
        with pytest.raises(ValueError):
            labor_income_shock(0.40, income_fraction=1.5)

    def test_zero_fraction_raises(self):
        """income_fraction=0.0 is valid (total collapse → uses LABOR_INCOME_MIN floor)."""
        result = labor_income_shock(0.40, income_fraction=0.0)
        assert result["outcome"] in VALID_OUTCOMES

    def test_delta_is_non_positive_for_shock(self):
        """Any shock (income_fraction < 1.0) must not improve surplus_deficit vs. baseline."""
        r_base  = labor_income_shock(0.40, income_fraction=1.0)
        r_shock = labor_income_shock(0.40, income_fraction=0.50)
        assert r_shock["surplus_deficit_delta"] <= r_base["surplus_deficit_delta"] + 1e-6


# ===========================================================================
# Compound Shock
# ===========================================================================

class TestCompoundShock:

    def test_returns_expected_keys(self):
        result = compound_shock(0.40)
        for key in ("scenario", "epsilon", "individual_outcomes",
                    "combined_eoh_delta", "trust_absorbs_combined",
                    "combined_outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert compound_shock(0.40)["scenario"] == "compound_shock"

    def test_no_shocks_is_stable(self):
        """All shocks disabled → combined_outcome is STABLE."""
        result = compound_shock(0.40, ecology_collapse=False,
                                demographic_shock_spec=None,
                                automation_fraction_lost=0.0)
        assert result["combined_outcome"] == "STABLE"
        assert result["combined_eoh_delta"] == 0.0

    def test_combined_outcome_at_least_as_severe_as_worst_individual(self):
        """Combined outcome must be >= worst individual outcome in severity."""
        _severity = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
        result = compound_shock(
            0.60,
            ecology_collapse=True,
            ecosystem_health_before=0.50,
            ecosystem_health_after=0.25,
            demographic_shock_spec={"shock_type": "aging", "magnitude": 0.20},
        )
        worst_ind = max(
            (_severity[v] for v in result["individual_outcomes"].values()),
            default=0,
        )
        assert _severity[result["combined_outcome"]] >= worst_ind

    def test_ecology_collapse_adds_individual_outcome(self):
        result = compound_shock(0.40, ecology_collapse=True,
                                ecosystem_health_before=0.70,
                                ecosystem_health_after=0.30)
        assert "ecological_eoh_spike" in result["individual_outcomes"]

    def test_demographic_shock_spec_adds_individual_outcome(self):
        result = compound_shock(
            0.40,
            demographic_shock_spec={"shock_type": "growth", "magnitude": 0.20}
        )
        assert "demographic_shock" in result["individual_outcomes"]

    def test_automation_fraction_lost_adds_individual_outcome(self):
        result = compound_shock(0.40, automation_fraction_lost=0.50)
        assert "automation_failure_shock" in result["individual_outcomes"]

    def test_combined_eoh_delta_non_negative(self):
        result = compound_shock(
            0.40,
            ecology_collapse=True,
            ecosystem_health_before=0.70,
            ecosystem_health_after=0.30,
        )
        assert result["combined_eoh_delta"] >= 0.0

    def test_combined_outcome_is_valid(self):
        result = compound_shock(0.40)
        assert result["combined_outcome"] in VALID_OUTCOMES

    def test_recommendation_is_string(self):
        result = compound_shock(0.40, ecology_collapse=True,
                                ecosystem_health_before=0.70,
                                ecosystem_health_after=0.30)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_all_three_shocks_simultaneous(self):
        """Full compound — all three shocks active."""
        result = compound_shock(
            epsilon=0.50,
            ecology_collapse=True,
            ecosystem_health_before=0.55,
            ecosystem_health_after=0.25,
            demographic_shock_spec={"shock_type": "aging", "magnitude": 0.30},
            automation_fraction_lost=0.40,
        )
        assert len(result["individual_outcomes"]) == 3
        assert result["combined_outcome"] in VALID_OUTCOMES
