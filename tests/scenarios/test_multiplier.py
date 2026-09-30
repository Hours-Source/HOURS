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


# ---------------------------------------------------------------------------
# band_correction — the floor under a Condition II correction (2026-09-30)
# ---------------------------------------------------------------------------

class TestBandCorrectionRespectsTheFloor:
    """
    Two constitutional constraints: every tier μ ≥ M_FLOOR (an hour mints at
    least what an hour of one's own obligation costs at the floor) and the mean
    ≤ M_BAND_HIGH. The drift scenarios above move aggregate M only, so they
    cannot see which tier a correction lands on.
    """

    @staticmethod
    def _snap(name):
        from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS
        return WORKFORCE_SNAPSHOTS[name]

    def test_an_in_band_composition_is_left_alone(self):
        from hours_eoh.scenarios.multiplier import band_correction
        r = band_correction(self._snap("reference"))
        assert not r["above_band"]
        assert r["proportional"]["factor"] == 1.0
        assert r["off_the_top"]["tiers_capped"] == []
        assert r["off_the_top"]["mean_after"] == pytest.approx(r["m_before"], rel=1e-15)

    @pytest.mark.parametrize("name", ["above_band", "high_epsilon"])
    def test_off_the_top_lands_on_the_ceiling_and_keeps_the_floor(self, name):
        from hours_eoh.data import M_BAND_HIGH, M_FLOOR
        from hours_eoh.scenarios.multiplier import band_correction
        segs = self._snap(name)
        r = band_correction(segs)["off_the_top"]
        assert r["mean_after"] == pytest.approx(M_BAND_HIGH, rel=1e-12)
        assert r["floor_respected"] and r["min_tier_after"] >= M_FLOOR
        low = min(segs, key=lambda s: s["mean_mu"])
        assert low["name"] not in r["tiers_capped"], "the bottom must be untouched"

    def test_proportional_breaks_the_floor_past_its_limit(self):
        """Credential inflation (M 2.35) with a 1.10 base tier: scaling everyone
        down to the ceiling pays the base tier below an hour."""
        from hours_eoh.scenarios.multiplier import band_correction
        r = band_correction(self._snap("above_band"))
        assert r["m_before"] > r["proportional_limit"]
        assert not r["proportional"]["floor_respected"]

    def test_proportional_holds_inside_its_limit(self):
        """And the check can NOT fire: the natural high-ε drift (M 2.22) is
        inside the proportional limit for its composition."""
        from hours_eoh.scenarios.multiplier import band_correction
        r = band_correction(self._snap("high_epsilon"))
        assert r["above_band"]
        assert r["m_before"] < r["proportional_limit"]
        assert r["proportional"]["floor_respected"]

    def test_the_limit_divides_by_the_floor_it_is_given(self):
        """Mode 3: M_FLOOR is 1.0, so a limit that forgot the floor would pass
        every shipped case. A floor that is not 1 makes the division visible."""
        from hours_eoh.data import M_BAND_HIGH
        from hours_eoh.scenarios.multiplier import band_correction
        segs = self._snap("low_epsilon")
        lowest = min(s["mean_mu"] for s in segs)
        r = band_correction(segs, floor=1.1)
        assert r["proportional_limit"] == pytest.approx(M_BAND_HIGH * lowest / 1.1, rel=1e-15)

    def test_the_limit_is_the_formula(self):
        from hours_eoh.data import M_BAND_HIGH, M_FLOOR
        from hours_eoh.scenarios.multiplier import band_correction
        segs = self._snap("low_epsilon")
        lowest = min(s["mean_mu"] for s in segs)
        assert band_correction(segs)["proportional_limit"] == pytest.approx(
            M_BAND_HIGH * lowest / M_FLOOR, rel=1e-15)

    def test_on_the_measured_map_no_proportional_correction_can_keep_the_floor(self):
        """The measured registry's lowest occupation sits EXACTLY on M_FLOOR —
        a construction of the frozen geometric map (its lower bound is the
        reference epoch's minimum), not an empirical fact. The consequence is
        real either way: the proportional limit equals the ceiling, so any
        above-band drift on this map must be corrected off the top."""
        from hours_eoh.core.multipliers import registry_segments
        from hours_eoh.data import M_BAND_HIGH, M_FLOOR
        from hours_eoh.scenarios.multiplier import band_correction
        segs = registry_segments()
        assert min(s["mean_mu"] for s in segs) == M_FLOOR
        assert band_correction(segs)["proportional_limit"] == pytest.approx(M_BAND_HIGH, rel=1e-15)

    def test_a_floor_at_or_above_the_ceiling_is_refused(self):
        from hours_eoh.scenarios.multiplier import band_correction
        with pytest.raises(ValueError):
            band_correction(self._snap("reference"), band_high=1.0, floor=1.0)


class TestTheAdoptedCorrection:
    """Author decision 2026-09-30: an above-band composition is corrected OFF
    THE TOP. These pin the guarantees `corrected_segments` states."""

    @staticmethod
    def _snap(name):
        from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS
        return WORKFORCE_SNAPSHOTS[name]

    def test_the_adopted_rule_is_named(self):
        from hours_eoh.scenarios.multiplier import ADOPTED_BAND_CORRECTION, band_correction
        assert ADOPTED_BAND_CORRECTION == "off_the_top"
        assert band_correction(self._snap("reference"))["adopted"] == "off_the_top"

    @pytest.mark.parametrize("name", ["above_band", "high_epsilon"])
    def test_corrected_composition_lands_on_the_ceiling_above_the_floor(self, name):
        from hours_eoh.core.multipliers import population_weighted_mean_multiplier
        from hours_eoh.data import M_BAND_HIGH, M_FLOOR
        from hours_eoh.scenarios.multiplier import corrected_segments
        before = self._snap(name)
        after = corrected_segments(before)
        assert population_weighted_mean_multiplier(after) == pytest.approx(M_BAND_HIGH, rel=1e-12)
        assert all(a["mean_mu"] <= b["mean_mu"] for a, b in zip(after, before)), "nothing moves up"
        assert min(a["mean_mu"] for a in after) >= M_FLOOR
        low = min(range(len(before)), key=lambda i: before[i]["mean_mu"])
        assert after[low]["mean_mu"] == before[low]["mean_mu"]

    def test_in_band_is_unchanged_and_inputs_are_not_mutated(self):
        import copy
        from hours_eoh.scenarios.multiplier import corrected_segments
        before = self._snap("reference")
        snapshot = copy.deepcopy(before)
        assert corrected_segments(before) == before
        corrected_segments(self._snap("above_band"))
        assert before == snapshot

    def test_the_measured_registry_above_band_is_correctable_off_the_top(self):
        """The case proportional correction cannot handle: the measured map's
        floor occupation stays at M_FLOOR when the registry is pushed above
        band by inflating its upper half."""
        from hours_eoh.core.multipliers import (
            population_weighted_mean_multiplier, registry_segments)
        from hours_eoh.data import M_BAND_HIGH, M_FLOOR
        from hours_eoh.scenarios.multiplier import band_correction, corrected_segments
        segs = [{**s, "mean_mu": s["mean_mu"] * (1.2 if s["mean_mu"] > 2.0 else 1.0)}
                for s in registry_segments()]
        assert population_weighted_mean_multiplier(segs) > M_BAND_HIGH
        assert not band_correction(segs)["proportional"]["floor_respected"]
        after = corrected_segments(segs)
        assert population_weighted_mean_multiplier(after) == pytest.approx(M_BAND_HIGH, rel=1e-12)
        assert min(s["mean_mu"] for s in after) == M_FLOOR
