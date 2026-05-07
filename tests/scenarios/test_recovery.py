"""
Tests for hours_eoh.scenarios.recovery.

Covers: maintenance_recovery_schedule, minimum_fulfillment_for_recovery.
"""

import pytest
from hours_eoh.scenarios.recovery import (
    maintenance_recovery_schedule,
    minimum_fulfillment_for_recovery,
)


class TestMaintenanceRecoverySchedule:
    def test_zero_backlog_recovers_immediately(self):
        result = maintenance_recovery_schedule(
            epsilon=0.40,
            current_deferred=0.0,
            annual_eoh=100_000.0,
            fulfillment_fraction=1.5,
        )
        assert result["recoverable"] is True
        assert result["recovery_year"] == 1

    def test_small_backlog_recovers_quickly(self):
        # Backlog = 2× annual; with 50% surplus capacity, clears in ~4 years
        result = maintenance_recovery_schedule(
            epsilon=0.40,
            current_deferred=200_000.0,
            annual_eoh=100_000.0,
            fulfillment_fraction=1.5,  # 50,000 EOH/yr toward backlog
        )
        assert result["recoverable"] is True
        assert result["recovery_year"] is not None
        assert result["recovery_year"] <= 10

    def test_no_surplus_means_no_recovery(self):
        # fulfillment_fraction=1.0 → zero surplus → backlog never decreases
        result = maintenance_recovery_schedule(
            epsilon=0.40,
            current_deferred=500_000.0,  # 5× annual
            annual_eoh=100_000.0,
            fulfillment_fraction=1.0,
            max_years=10,
        )
        assert result["recoverable"] is False
        assert result["final_deferred"] == pytest.approx(500_000.0)

    def test_backlog_decreases_with_surplus(self):
        result = maintenance_recovery_schedule(
            epsilon=0.40,
            current_deferred=1_000_000.0,
            annual_eoh=100_000.0,
            fulfillment_fraction=2.0,  # 100% surplus → 100,000 EOH/yr paydown
            max_years=15,
        )
        if result["trajectory"]:
            first  = result["trajectory"][0]["deferred"]
            last   = result["trajectory"][-1]["deferred"]
            assert last < first

    def test_result_keys_present(self):
        result = maintenance_recovery_schedule(0.40, 100_000.0, 50_000.0)
        for key in ("recoverable", "recovery_year", "trajectory",
                    "final_deferred", "recommendation"):
            assert key in result

    def test_recommendation_is_string(self):
        result = maintenance_recovery_schedule(0.40, 100_000.0, 50_000.0)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10

    def test_trajectory_is_list(self):
        result = maintenance_recovery_schedule(0.40, 50_000.0, 100_000.0,
                                               fulfillment_fraction=2.0)
        assert isinstance(result["trajectory"], list)
        assert len(result["trajectory"]) >= 1


class TestMinimumFulfillmentForRecovery:
    def test_small_backlog_has_low_minimum(self):
        result = minimum_fulfillment_for_recovery(
            epsilon=0.40,
            current_deferred=200_000.0,  # 2× annual
            annual_eoh=100_000.0,
            max_years=20,
        )
        assert result["min_fulfillment"] is not None
        assert 1.0 < result["min_fulfillment"] <= 2.0

    def test_returns_expected_keys(self):
        result = minimum_fulfillment_for_recovery(0.40, 200_000.0, 100_000.0)
        assert "min_fulfillment" in result
        assert "recovery_year" in result
        assert "sweep" in result

    def test_sweep_is_list(self):
        result = minimum_fulfillment_for_recovery(0.40, 200_000.0, 100_000.0)
        assert isinstance(result["sweep"], list)
        assert len(result["sweep"]) >= 1
