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


class TestAnExactTieIsRecovered:
    """A backlog equal to one year's demand is recovered, whatever float
    rounding does to the subtraction (2026-10-15: the US frame flipped year
    2 -> 1 -> 2 across two recalibrations that moved neither ratio)."""

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_the_tie_is_year_one_at_every_scale_and_a_real_miss_is_not(self, eps):
        # The US frame's two (backlog, demand) pairs: 1.5x demand to one ulp,
        # one ulp ABOVE and one BELOW — the bare `<=` read years 2 and 1.
        for deferred, annual in ((163843062700.78687, 109228708467.19122),
                                 (166100070339.38538, 110733380226.25694)):
            tie = maintenance_recovery_schedule(eps, deferred, annual, 1.5)
            assert tie["recovery_year"] == 1, deferred
        miss = maintenance_recovery_schedule(eps, 1.5 * 1e11 * (1 + 1e-6), 1e11, 1.5)
        assert miss["recovery_year"] == 2


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
