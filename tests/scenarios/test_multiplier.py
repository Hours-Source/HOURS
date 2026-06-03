"""
Tests for hours_eoh.scenarios.multiplier — M drift scenarios.

Covers: m_below_band_drift, m_above_band_drift, m_band_sweep,
and the mean_multiplier_schedule extension to run_simulation().
"""

import pytest

from hours_eoh.scenarios.multiplier import (
    m_below_band_drift,
    m_above_band_drift,
    m_band_sweep,
)
from hours_eoh.core.simulation import make_economy_state, run_simulation
from hours_eoh.data import M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET


DRIFT_RESULT_KEYS = {
    "outcome", "breach_period", "correction_period", "periods_out_of_band",
    "m_trajectory", "band_status", "fiscal_impact", "recommendation", "raw",
}
FISCAL_IMPACT_KEYS = {"teh_creation_delta", "min_trust_balance", "solvent_throughout"}


# ---------------------------------------------------------------------------
# run_simulation() — mean_multiplier_schedule extension
# ---------------------------------------------------------------------------

class TestRunSimulationSchedule:

    def test_schedule_overrides_per_period(self):
        state = make_economy_state(epsilon=0.40)
        schedule = [1.8, 2.0, 2.2, 1.9, 2.1]
        raw = run_simulation(state, n_periods=5, mean_multiplier_schedule=schedule)
        traj = raw["summary"]["mean_multiplier_trajectory"]
        assert traj == pytest.approx(schedule)

    def test_schedule_shorter_than_periods_falls_back(self):
        state = make_economy_state(epsilon=0.40)
        schedule = [1.8, 1.9]  # only 2 entries for 5 periods
        raw = run_simulation(
            state, n_periods=5, mean_multiplier_schedule=schedule, mean_multiplier=2.0
        )
        traj = raw["summary"]["mean_multiplier_trajectory"]
        assert traj[0] == pytest.approx(1.8)
        assert traj[1] == pytest.approx(1.9)
        assert traj[2] == pytest.approx(2.0)  # fallback to kwarg default

    def test_no_schedule_uses_static_m(self):
        state = make_economy_state(epsilon=0.40)
        raw = run_simulation(state, n_periods=5, mean_multiplier=1.95)
        traj = raw["summary"]["mean_multiplier_trajectory"]
        assert all(m == pytest.approx(1.95) for m in traj)

    def test_trajectory_length_matches_n_periods(self):
        state = make_economy_state(epsilon=0.40)
        raw = run_simulation(state, n_periods=7)
        assert len(raw["summary"]["mean_multiplier_trajectory"]) == 7

    def test_summary_key_present(self):
        state = make_economy_state(epsilon=0.40)
        raw = run_simulation(state, n_periods=3)
        assert "mean_multiplier_trajectory" in raw["summary"]


# ---------------------------------------------------------------------------
# m_below_band_drift
# ---------------------------------------------------------------------------

class TestMBelowBandDrift:

    def test_result_keys_present(self):
        result = m_below_band_drift(n_periods=10, m_drift_rate=-0.05)
        assert DRIFT_RESULT_KEYS == set(result.keys())
        assert FISCAL_IMPACT_KEYS == set(result["fiscal_impact"].keys())

    def test_m_trajectory_length(self):
        result = m_below_band_drift(n_periods=12)
        assert len(result["m_trajectory"]) == 12

    def test_band_status_length_matches_trajectory(self):
        result = m_below_band_drift(n_periods=10)
        assert len(result["band_status"]) == len(result["m_trajectory"])

    def test_breach_detected_at_expected_period(self):
        # m_start=2.10, drift=-0.10, M_BAND_LOW=1.8 (breach = strictly below)
        # period 0: 2.10, 1: 2.00, 2: 1.90, 3: 1.80 (at floor, not below),
        # period 4: 1.70 → first breach
        result = m_below_band_drift(
            n_periods=15, m_start=2.10, m_drift_rate=-0.10, governance_lag=5
        )
        assert result["breach_period"] == 4

    def test_correction_period_is_breach_plus_lag(self):
        result = m_below_band_drift(
            n_periods=20, m_start=2.10, m_drift_rate=-0.10, governance_lag=4
        )
        if result["breach_period"] is not None:
            assert result["correction_period"] == result["breach_period"] + 4

    def test_no_breach_if_drift_too_slow(self):
        # drift=-0.001 per period × 10 periods: starts at 2.10, ends at 2.09 — never below 1.8
        result = m_below_band_drift(
            n_periods=10, m_start=2.10, m_drift_rate=-0.001, governance_lag=5
        )
        assert result["breach_period"] is None
        assert result["periods_out_of_band"] == 0
        assert result["outcome"] == "STABLE"

    def test_m_trajectory_clamped_to_minimum(self):
        # Very aggressive drift: M should never go below 1.0
        result = m_below_band_drift(
            n_periods=10, m_start=2.10, m_drift_rate=-0.50, governance_lag=20
        )
        assert all(m >= 1.0 for m in result["m_trajectory"])

    def test_correction_snaps_m_to_target(self):
        result = m_below_band_drift(
            n_periods=20, m_start=2.10, m_drift_rate=-0.10, governance_lag=3,
            correction_magnitude=None,
        )
        corr = result["correction_period"]
        if corr is not None and corr < len(result["m_trajectory"]):
            # After correction, M should be at or near M_BAND_TARGET
            assert result["m_trajectory"][corr] == pytest.approx(M_BAND_TARGET, abs=0.01)

    def test_outcome_is_valid_string(self):
        result = m_below_band_drift(n_periods=10)
        assert result["outcome"] in {"STABLE", "DEGRADED", "CRISIS"}

    def test_recommendation_is_nonempty_string(self):
        result = m_below_band_drift(n_periods=10)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10


# ---------------------------------------------------------------------------
# m_above_band_drift
# ---------------------------------------------------------------------------

class TestMAboveBandDrift:

    def test_result_keys_present(self):
        result = m_above_band_drift(n_periods=10, m_drift_rate=0.04)
        assert DRIFT_RESULT_KEYS == set(result.keys())

    def test_breach_detected_above_ceiling(self):
        # m_start=2.10, drift=+0.04 → breach at M_BAND_HIGH=2.1 immediately
        result = m_above_band_drift(
            n_periods=15, m_start=2.10, m_drift_rate=0.04, governance_lag=5
        )
        # First period M = 2.10 (at ceiling, not above); breach at period 1: M = 2.14
        assert result["breach_period"] is not None
        assert result["band_status"][result["breach_period"]] == "ABOVE_BAND"

    def test_above_band_status_in_trajectory(self):
        result = m_above_band_drift(
            n_periods=20, m_start=2.10, m_drift_rate=0.10, governance_lag=10
        )
        assert "ABOVE_BAND" in result["band_status"]

    def test_above_band_teh_creation_exceeds_baseline(self):
        # Higher M → more TEH created → teh_creation_delta should be positive
        result = m_above_band_drift(
            n_periods=15, m_start=2.10, m_drift_rate=0.05, governance_lag=8
        )
        assert result["fiscal_impact"]["teh_creation_delta"] >= 0

    def test_outcome_is_valid_string(self):
        result = m_above_band_drift(n_periods=10)
        assert result["outcome"] in {"STABLE", "DEGRADED", "CRISIS"}


# ---------------------------------------------------------------------------
# m_band_sweep
# ---------------------------------------------------------------------------

class TestMBandSweep:

    def test_covers_all_m_values(self):
        m_vals = [1.6, 1.8, 2.0, 2.1, 2.3]
        result = m_band_sweep(m_values=m_vals, n_periods=5)
        assert result["m_values"] == m_vals
        assert len(result["outcomes"]) == len(m_vals)
        assert len(result["teh_created"]) == len(m_vals)
        assert len(result["final_trust_balance"]) == len(m_vals)
        assert len(result["solvent_all"]) == len(m_vals)
        assert len(result["band_status"]) == len(m_vals)

    def test_default_m_values_eleven_entries(self):
        result = m_band_sweep(n_periods=5)
        assert len(result["m_values"]) == 11

    def test_higher_m_produces_more_teh(self):
        result = m_band_sweep(m_values=[1.5, 2.0, 2.5], n_periods=5)
        # TEH should be monotonically increasing with M (more TEH per EOH-hour)
        assert result["teh_created"][0] < result["teh_created"][1] < result["teh_created"][2]

    def test_summary_keys_present(self):
        result = m_band_sweep(n_periods=5)
        assert "m_floor_for_solvency" in result["summary"]
        assert "m_ceiling_stable" in result["summary"]

    def test_floor_for_solvency_below_ceiling_stable(self):
        result = m_band_sweep(n_periods=5)
        floor = result["summary"]["m_floor_for_solvency"]
        ceiling = result["summary"]["m_ceiling_stable"]
        if floor is not None and ceiling is not None:
            assert floor <= ceiling

    def test_outcomes_are_valid_strings(self):
        result = m_band_sweep(m_values=[1.8, 2.0, 2.2], n_periods=5)
        for outcome in result["outcomes"]:
            assert outcome in {"STABLE", "DEGRADED", "CRISIS"}

    def test_band_status_matches_m_values(self):
        result = m_band_sweep(m_values=[1.5, 2.0, 2.5], n_periods=5)
        assert result["band_status"][0] == "BELOW_BAND"
        assert result["band_status"][1] == "OK"
        assert result["band_status"][2] == "ABOVE_BAND"
