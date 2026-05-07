"""
Tests for hours_eoh.scenarios.maintenance at the canonical import location.

Covers: deferred_maintenance_crisis, care_registration_delay.
"""

import pytest
from hours_eoh.scenarios.maintenance import (
    deferred_maintenance_crisis,
    care_registration_delay,
)

VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


class TestDeferredMaintenanceCrisis:
    def test_full_fulfillment_stays_stable(self):
        result = deferred_maintenance_crisis(
            epsilon=0.40, annual_eoh=100_000.0,
            fulfillment_fraction=1.0, years=20,
        )
        assert result["outcome"] == "STABLE"
        assert result["crisis_year"] is None

    def test_zero_fulfillment_reaches_crisis_over_long_horizon(self):
        # Compounding in this framework is slow — crisis requires ~100 years.
        result = deferred_maintenance_crisis(
            epsilon=0.40, annual_eoh=100_000.0,
            fulfillment_fraction=0.0, years=100,
        )
        assert result["outcome"] == "CRISIS"
        assert result["crisis_year"] is not None

    def test_trajectory_length_matches_years(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.80, 15)
        assert len(result["trajectory"]) == 15

    def test_deferred_accumulates_monotonically_at_zero_fulfillment(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.0, 10)
        deferreds = [r["cumulative_deferred"] for r in result["trajectory"]]
        assert all(deferreds[i] <= deferreds[i + 1] for i in range(len(deferreds) - 1))

    def test_outcome_is_valid(self):
        for frac in (0.0, 0.60, 1.0):
            result = deferred_maintenance_crisis(0.40, 100_000.0, frac, 20)
            assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.80, 10)
        assert result["scenario"] == "deferred_maintenance_crisis"

    def test_higher_epsilon_softens_compounding(self):
        low_eps  = deferred_maintenance_crisis(0.10, 100_000.0, 0.0, 10)
        high_eps = deferred_maintenance_crisis(0.80, 100_000.0, 0.0, 10)
        # High ε has automation-softened compounding
        assert (high_eps["final_compounding_ratio"]
                <= low_eps["final_compounding_ratio"])


class TestCareRegistrationDelay:
    def test_no_delay_is_stable(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.0)
        assert result["outcome"] == "STABLE"
        assert result["lag_fraction"] == pytest.approx(0.0, abs=1e-9)

    def test_large_delay_is_crisis(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.40)
        assert result["outcome"] == "CRISIS"

    def test_actual_share_less_than_expected(self):
        result = care_registration_delay(epsilon=0.70, delay_epsilon=0.20)
        assert result["actual_care_share"] < result["expected_care_share"]

    def test_lag_fraction_in_range(self):
        result = care_registration_delay(epsilon=0.50, delay_epsilon=0.10)
        assert 0.0 <= result["lag_fraction"] <= 1.0

    def test_teh_deficit_non_negative(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.15)
        assert result["teh_deficit_per_worker"] >= 0.0

    def test_outcome_is_valid(self):
        for delay in (0.0, 0.10, 0.30):
            result = care_registration_delay(0.60, delay)
            assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = care_registration_delay(0.50, 0.10)
        assert result["scenario"] == "care_registration_delay"
