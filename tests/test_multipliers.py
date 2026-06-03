"""
Tests for hours_eoh.core.multipliers

Covers: population_weighted_mean_multiplier, multiplier_band_check,
tier_multiplier, epoch_alpha_weights.
"""

import pytest

from hours_eoh.core.multipliers import (
    population_weighted_mean_multiplier,
    multiplier_band_check,
    tier_multiplier,
    epoch_alpha_weights,
    scarcity_score,
    validate_training_duration,
    detect_artificial_scarcity,
    tier_expiry_check,
    reclassification_impact,
)
from hours_eoh.data import (
    DEFAULT_SEGMENTS, M_BAND_LOW, M_BAND_HIGH,
    SCARCITY_SEVERE_THRESHOLD, TIER_ASSESSMENT_INTERVAL_YEARS,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


class TestMultiplierSystem:

    def test_default_segments_mean_equals_target(self):
        """Multiplier band holds at ε=0 with default segments."""
        mean = population_weighted_mean_multiplier(DEFAULT_SEGMENTS)
        assert mean == pytest.approx(2.10, abs=0.01), (
            f"Default segments should produce mean ≈ 2.10, got {mean:.4f}"
        )

    def test_multiplier_band_check_passes_for_in_range(self):
        """Condition II passes for mean within [1.8, 2.1]."""
        for m in [1.8, 1.9, 2.0, 2.1]:
            result = multiplier_band_check(m)
            assert result["in_band"] is True, f"Mean={m} should be in band"
            assert result["status"] == "OK"

    def test_multiplier_band_check_fails_below_band(self):
        result = multiplier_band_check(1.5)
        assert result["in_band"] is False
        assert result["status"] == "BELOW_BAND"

    def test_multiplier_band_check_fails_above_band(self):
        result = multiplier_band_check(2.5)
        assert result["in_band"] is False
        assert result["status"] == "ABOVE_BAND"

    def test_tier_multiplier_at_all_zeros_returns_one(self):
        """Zero factors → base multiplier of 1.0."""
        m = tier_multiplier(0.0, 0.0, 0.0, 0.0)
        assert m == pytest.approx(1.0)

    def test_tier_multiplier_at_all_ones_returns_m_max(self):
        """Maximum factors → m_max (clamped)."""
        m = tier_multiplier(1.0, 1.0, 1.0, 1.0)
        assert m == pytest.approx(6.0)

    def test_tier_multiplier_rejects_out_of_range_factors(self):
        with pytest.raises(ValueError):
            tier_multiplier(1.5, 0.5, 0.5, 0.5)

    def test_tier_multiplier_mission_statement_example(self):
        """
        High-tier infrastructure engineer: high on all four factors.
        Should produce a multiplier well above 2.0.
        """
        m = tier_multiplier(training=0.8, demand=0.7, scarcity=0.6, impact=0.9)
        assert m > 2.0, f"High-leverage engineer should have m > 2.0, got {m:.2f}"

    def test_epoch_alpha_weights_sum_to_one(self):
        for eps in KEY_EPSILONS:
            weights = epoch_alpha_weights(eps)
            assert sum(weights) == pytest.approx(1.0, abs=1e-6), (
                f"Alpha weights must sum to 1.0 at ε={eps}"
            )

    def test_epoch_alpha_weights_all_positive(self):
        for eps in KEY_EPSILONS:
            weights = epoch_alpha_weights(eps)
            assert all(w > 0 for w in weights), (
                f"All alpha weights must be positive at ε={eps}"
            )


class TestScarcityScore:

    EXPECTED_KEYS = {
        "scarcity", "raw_current", "rolling_mean", "supply_adjusted",
        "window_size", "supply_discount_applied", "status",
    }

    def test_result_keys_present(self):
        result = scarcity_score([(100, 200)])
        assert self.EXPECTED_KEYS == set(result.keys())

    def test_single_entry_basic(self):
        # 100 practitioners, 200 demand → raw scarcity = 0.5
        result = scarcity_score([(100, 200)])
        assert result["raw_current"] == pytest.approx(0.5)
        assert result["rolling_mean"] == pytest.approx(0.5)
        assert result["scarcity"] == pytest.approx(0.5)
        assert result["window_size"] == 1
        assert result["supply_discount_applied"] is False

    def test_rolling_window_uses_last_n(self):
        # Five entries; first two have scarcity 0.9, last three have 0.1
        # With window=3, only last three should be averaged
        history = [(10, 100), (10, 100), (90, 100), (90, 100), (90, 100)]
        result = scarcity_score(history, window=3)
        assert result["window_size"] == 3
        assert result["rolling_mean"] == pytest.approx(0.1, abs=0.01)

    def test_window_larger_than_history(self):
        # window=10 but only 2 entries — should use both without error
        history = [(50, 100), (60, 100)]
        result = scarcity_score(history, window=10)
        assert result["window_size"] == 2

    def test_supply_response_discount_reduces_scarcity(self):
        # High elasticity should reduce scarcity below rolling_mean
        history = [(50, 200)]  # raw = 0.75
        result = scarcity_score(history, supply_elasticity=0.5, supply_lag_years=3)
        assert result["supply_discount_applied"] is True
        assert result["supply_adjusted"] < result["rolling_mean"]
        assert result["scarcity"] < result["rolling_mean"]

    def test_zero_elasticity_no_discount(self):
        history = [(50, 200)]
        result = scarcity_score(history, supply_elasticity=0.0)
        assert result["supply_discount_applied"] is False
        assert result["supply_adjusted"] == pytest.approx(result["rolling_mean"])

    def test_full_employment_zero_scarcity(self):
        # Practitioners meet or exceed demand → scarcity = 0
        history = [(200, 100), (150, 100)]
        result = scarcity_score(history)
        assert result["scarcity"] == pytest.approx(0.0)
        assert result["status"] == "OK"

    def test_severe_scarcity_status(self):
        # 5 practitioners for 100 demand → raw = 0.95 > threshold
        result = scarcity_score([(5, 100)])
        assert result["scarcity"] > SCARCITY_SEVERE_THRESHOLD
        assert result["status"] == "SEVERE_SCARCITY"

    def test_normal_scarcity_status_ok(self):
        # 50 practitioners for 100 demand → raw = 0.5
        result = scarcity_score([(50, 100)])
        assert result["status"] == "OK"

    def test_scarcity_in_unit_interval(self):
        test_cases = [(0, 100), (50, 100), (100, 100), (150, 100), (5, 100)]
        for practitioners, demand in test_cases:
            result = scarcity_score([(practitioners, demand)])
            assert 0.0 <= result["scarcity"] <= 1.0, (
                f"scarcity out of [0,1] for ({practitioners}, {demand}): {result['scarcity']}"
            )

    def test_empty_history_raises(self):
        with pytest.raises(ValueError, match="history"):
            scarcity_score([])

    def test_zero_demand_raises(self):
        with pytest.raises(ValueError, match="demand_eoh"):
            scarcity_score([(10, 0)])

    def test_negative_practitioners_raises(self):
        with pytest.raises(ValueError, match="practitioner"):
            scarcity_score([(-1, 100)])


class TestAntiGamingSafeguards:

    # --- validate_training_duration ---

    def test_training_valid_within_tolerance(self):
        # mandated=5, median=4 → ratio=1.25 < tolerance=1.5 → passes
        result = validate_training_duration(5.0, 4.0)
        assert result["passes"] is True
        assert result["status"] == "OK"
        assert result["ratio"] == pytest.approx(1.25)

    def test_training_inflation_flagged(self):
        # mandated=9, median=4 → ratio=2.25 > tolerance=1.5 → flagged
        result = validate_training_duration(9.0, 4.0)
        assert result["passes"] is False
        assert result["status"] == "TRAINING_INFLATION"

    def test_training_exact_boundary_passes(self):
        # mandated=6, median=4 → ratio=1.5 exactly at tolerance → passes
        result = validate_training_duration(6.0, 4.0)
        assert result["passes"] is True
        assert result["ratio"] == pytest.approx(1.5)

    def test_training_returns_all_fields(self):
        result = validate_training_duration(5.0, 4.0, tolerance_factor=2.0)
        assert set(result.keys()) == {
            "mandated_years", "median_competency_years", "ratio",
            "tolerance_factor", "passes", "status",
        }
        assert result["tolerance_factor"] == pytest.approx(2.0)

    def test_training_zero_mandated_passes(self):
        # A role with no training requirement is valid; ratio = 0 always passes.
        result = validate_training_duration(0.0, 4.0)
        assert result["passes"] is True
        assert result["ratio"] == pytest.approx(0.0)

    def test_training_negative_mandated_raises(self):
        with pytest.raises(ValueError):
            validate_training_duration(-1.0, 4.0)

    def test_training_zero_median_raises(self):
        with pytest.raises(ValueError):
            validate_training_duration(5.0, 0.0)

    # --- detect_artificial_scarcity ---

    def test_detect_scarcity_ok(self):
        # Normal pass rate, no quality data → OK
        result = detect_artificial_scarcity(0.60)
        assert result["passes"] is True
        assert result["status"] == "OK"
        assert result["trigger"] is None

    def test_detect_scarcity_below_floor(self):
        # pass_rate=0.20 < floor=0.30 → ARTIFICIAL_SCARCITY
        result = detect_artificial_scarcity(0.20)
        assert result["passes"] is False
        assert result["status"] == "ARTIFICIAL_SCARCITY"
        assert result["trigger"] == "pass_rate_below_floor"

    def test_detect_scarcity_floor_boundary_ok(self):
        # pass_rate exactly at floor → not flagged by trigger 1
        result = detect_artificial_scarcity(0.30)
        assert result["status"] in ("OK", "ARTIFICIAL_SCARCITY_RISK")

    def test_detect_scarcity_low_quality_differential(self):
        # pass_rate=0.5 (above floor), quality_diff=0.05 < threshold=0.20 → RISK
        result = detect_artificial_scarcity(0.50, quality_differential=0.05)
        assert result["passes"] is False
        assert result["status"] == "ARTIFICIAL_SCARCITY_RISK"
        assert result["trigger"] == "low_quality_differential"

    def test_detect_scarcity_high_quality_differential(self):
        # quality_diff above threshold → OK despite moderate pass rate
        result = detect_artificial_scarcity(0.40, quality_differential=0.50)
        assert result["passes"] is True
        assert result["status"] == "OK"

    def test_detect_scarcity_trigger1_takes_precedence(self):
        # Both triggers could fire — trigger 1 (floor) wins
        result = detect_artificial_scarcity(0.10, quality_differential=0.05)
        assert result["status"] == "ARTIFICIAL_SCARCITY"
        assert result["trigger"] == "pass_rate_below_floor"

    def test_detect_scarcity_returns_all_fields(self):
        result = detect_artificial_scarcity(0.50, quality_differential=0.30)
        assert set(result.keys()) == {
            "pass_rate", "floor", "quality_differential", "quality_threshold",
            "passes", "status", "trigger",
        }

    def test_detect_scarcity_invalid_pass_rate_raises(self):
        with pytest.raises(ValueError):
            detect_artificial_scarcity(1.5)

    def test_detect_scarcity_invalid_quality_diff_raises(self):
        with pytest.raises(ValueError):
            detect_artificial_scarcity(0.5, quality_differential=-0.1)

    # --- tier_expiry_check ---

    def test_tier_expiry_current(self):
        # elapsed=3, interval=5 → CURRENT, remaining=2
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2023)
        assert result["status"] == "CURRENT"
        assert result["expired"] is False
        assert result["elapsed"] == 3
        assert result["remaining"] == 2

    def test_tier_expiry_exact_boundary(self):
        # elapsed=5 equals interval=5 → OVERDUE
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2025)
        assert result["status"] == "OVERDUE"
        assert result["expired"] is True
        assert result["remaining"] == 0

    def test_tier_expiry_overdue(self):
        # elapsed=7, interval=5 → OVERDUE, remaining=-2
        result = tier_expiry_check(assigned_epoch=2018, current_epoch=2025)
        assert result["status"] == "OVERDUE"
        assert result["remaining"] == -2

    def test_tier_expiry_just_assigned(self):
        # elapsed=0 → CURRENT, remaining=interval
        result = tier_expiry_check(assigned_epoch=2025, current_epoch=2025)
        assert result["status"] == "CURRENT"
        assert result["elapsed"] == 0
        assert result["remaining"] == TIER_ASSESSMENT_INTERVAL_YEARS

    def test_tier_expiry_custom_interval(self):
        result = tier_expiry_check(assigned_epoch=2020, current_epoch=2023, interval_years=2)
        assert result["status"] == "OVERDUE"
        assert result["elapsed"] == 3
        assert result["remaining"] == -1

    def test_tier_expiry_returns_all_fields(self):
        result = tier_expiry_check(2020, 2023)
        assert set(result.keys()) == {
            "assigned_epoch", "current_epoch", "interval_years",
            "elapsed", "remaining", "expired", "status",
        }

    def test_tier_expiry_invalid_epoch_raises(self):
        with pytest.raises(ValueError, match="current_epoch"):
            tier_expiry_check(assigned_epoch=2025, current_epoch=2020)


class TestReclassificationImpact:

    # Reference segments: DEFAULT_SEGMENTS-like distribution with M ≈ 2.10
    _SEGMENTS = [
        {"name": "base",     "fraction": 0.20, "mean_mu": 1.20},
        {"name": "standard", "fraction": 0.50, "mean_mu": 1.87},
        {"name": "advanced", "fraction": 0.25, "mean_mu": 2.80},
        {"name": "elite",    "fraction": 0.05, "mean_mu": 4.50},
    ]

    def test_no_change_delta_zero(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["m_delta"] == pytest.approx(0.0)
        assert result["m_after"] == pytest.approx(result["m_before"])

    def test_upward_reclassification_raises_m(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 3.20}],
        )
        assert result["m_after"] > result["m_before"]
        assert result["m_delta"] > 0.0

    def test_downward_reclassification_lowers_m(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "standard", "new_mean_mu": 1.50}],
        )
        assert result["m_after"] < result["m_before"]
        assert result["m_delta"] < 0.0

    def test_passes_when_m_stays_in_band(self):
        # Starting M ≈ 2.10; reduce advanced 2.80 → 2.70 → new M ≈ 2.075 (in band)
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 2.70}],
        )
        assert result["passes"] is True
        assert result["band_after"]["in_band"] is True

    def test_fails_when_m_leaves_band(self):
        # Large upward shift: elite 4.50 → 6.00 + advanced bump → M > 2.1
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "elite", "new_mean_mu": 6.00},
             {"name": "advanced", "new_mean_mu": 4.00}],
        )
        assert result["passes"] is False
        assert result["band_after"]["status"] == "ABOVE_BAND"

    def test_absorption_to_ceiling_positive_in_band(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["absorption_remaining"]["to_ceiling"] >= 0.0

    def test_absorption_to_floor_positive_in_band(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert result["absorption_remaining"]["to_floor"] >= 0.0

    def test_further_drift_budget_upward(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "advanced", "new_mean_mu": 2.90}],
        )
        # upward change → budget = to_ceiling
        assert result["absorption_remaining"]["further_drift_budget"] == pytest.approx(
            result["absorption_remaining"]["to_ceiling"]
        )

    def test_further_drift_budget_downward(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "standard", "new_mean_mu": 1.70}],
        )
        # downward change → budget = to_floor
        assert result["absorption_remaining"]["further_drift_budget"] == pytest.approx(
            result["absorption_remaining"]["to_floor"]
        )

    def test_result_keys_present(self):
        result = reclassification_impact(self._SEGMENTS, [])
        assert {"segments_before", "segments_after", "m_before", "m_after", "m_delta",
                "band_before", "band_after", "passes", "changes_applied",
                "absorption_remaining"} == set(result.keys())
        assert {"to_ceiling", "to_floor", "further_drift_budget"} == set(
            result["absorption_remaining"].keys()
        )

    def test_invalid_segment_name_raises(self):
        with pytest.raises(ValueError):
            reclassification_impact(
                self._SEGMENTS,
                [{"name": "nonexistent", "new_mean_mu": 2.0}],
            )

    def test_segments_not_mutated(self):
        import copy
        original = copy.deepcopy(self._SEGMENTS)
        reclassification_impact(self._SEGMENTS, [{"name": "advanced", "new_mean_mu": 3.50}])
        assert self._SEGMENTS == original

    def test_multiple_changes(self):
        result = reclassification_impact(
            self._SEGMENTS,
            [{"name": "base", "new_mean_mu": 1.30},
             {"name": "standard", "new_mean_mu": 2.00}],
        )
        # Both changes are applied
        after_names = {s["name"]: s["mean_mu"] for s in result["segments_after"]}
        assert after_names["base"] == pytest.approx(1.30)
        assert after_names["standard"] == pytest.approx(2.00)
