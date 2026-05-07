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
)
from hours_eoh.data import DEFAULT_SEGMENTS, M_BAND_LOW, M_BAND_HIGH

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
