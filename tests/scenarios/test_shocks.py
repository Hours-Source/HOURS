"""
Tests for hours_eoh.scenarios.shocks at the canonical import location.

Covers: automation_failure_shock, demographic_shock, ecological_eoh_spike.
"""

import pytest
from hours_eoh.scenarios.shocks import (
    automation_failure_shock,
    demographic_shock,
    ecological_eoh_spike,
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
