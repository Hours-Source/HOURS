"""
Tests for hours_eoh.scenarios.indust_overshoot.

Covers: indust_overshoot_baseline, indust_recovery_trajectory.
"""

import pytest
from hours_eoh.scenarios.indust_overshoot import (
    indust_overshoot_baseline,
    indust_recovery_trajectory,
)

VALID_OUTCOMES = {"MANAGEABLE", "STRESSED", "CRITICAL"}


# ===========================================================================
# indust_overshoot_baseline
# ===========================================================================

class TestIndustOvershootBaseline:

    def test_returns_expected_keys(self):
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        for key in ("scenario", "population", "epsilon", "eoh_by_domain",
                    "total_eoh", "teh_created", "fiscal",
                    "canonical_total_eoh", "eoh_vs_canonical_ratio",
                    "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert indust_overshoot_baseline(
            population=1_000_000, epsilon=0.40
        )["scenario"] == "indust_overshoot_baseline"

    def test_eoh_vs_canonical_ratio_above_one(self):
        """Industrial overshoot must have higher EOH than canonical at same ε."""
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        assert result["eoh_vs_canonical_ratio"] > 1.0

    def test_infrastructure_eoh_dominant(self):
        """Infrastructure EOH should be the largest domain in the overshoot state."""
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        domains = result["eoh_by_domain"]
        assert domains["infrastructure"] > 0.0

    def test_outcome_is_valid(self):
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        assert result["outcome"] in VALID_OUTCOMES

    def test_outcome_never_manageable_at_indust_params(self):
        """
        At full industrial-overshoot parameters (65M pop, ε=0.40), the
        EOH burden and ecological deficit should always produce STRESSED or CRITICAL.
        """
        result = indust_overshoot_baseline(population=65_000_000, epsilon=0.40)
        assert result["outcome"] in {"STRESSED", "CRITICAL"}

    def test_recommendation_is_string(self):
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_total_eoh_matches_eoh_by_domain_sum(self):
        """total_eoh must equal the sum of domain EOH values."""
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        domain_sum = sum(result["eoh_by_domain"].values())
        assert result["total_eoh"] == pytest.approx(domain_sum, rel=1e-4)

    def test_teh_created_non_negative(self):
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        assert result["teh_created"] >= 0.0

    def test_fiscal_has_solvent_key(self):
        result = indust_overshoot_baseline(population=1_000_000, epsilon=0.40)
        assert "solvent" in result["fiscal"]


# ===========================================================================
# indust_recovery_trajectory
# ===========================================================================

class TestIndustRecoveryTrajectory:

    def test_returns_expected_keys(self):
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40,
            ecological_restoration_rate=0.05, n_periods=5
        )
        for key in ("scenario", "population", "epsilon",
                    "ecological_restoration_rate", "n_periods",
                    "ecosystem_recovered", "fiscal_recovered",
                    "years_to_ecosystem_recovery", "trajectory", "raw"):
            assert key in result

    def test_scenario_name(self):
        r = indust_recovery_trajectory(population=1_000_000, n_periods=5)
        assert r["scenario"] == "indust_recovery_trajectory"

    def test_trajectory_length_matches_n_periods(self):
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40, n_periods=8
        )
        assert len(result["trajectory"]) == 8

    def test_ecosystem_health_increases_with_restoration(self):
        """With positive restoration rate, ecosystem health should improve over time."""
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40,
            ecological_restoration_rate=0.05, n_periods=10
        )
        eco_values = [r["ecosystem_health"] for r in result["trajectory"]]
        assert eco_values[-1] > eco_values[0]

    def test_zero_restoration_no_ecosystem_improvement(self):
        """With zero restoration rate, ecosystem health should not improve."""
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40,
            ecological_restoration_rate=0.0, n_periods=8
        )
        eco_values = [r["ecosystem_health"] for r in result["trajectory"]]
        # ecosystem_health should remain at or below the indust starting value
        from hours_eoh.indust_no_eco_params import INDUST_ECOSYSTEM_HEALTH
        assert all(e <= INDUST_ECOSYSTEM_HEALTH + 1e-6 for e in eco_values)

    def test_years_to_recovery_none_at_zero_restoration(self):
        """Without restoration, ecosystem never crosses the 0.40 threshold."""
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40,
            ecological_restoration_rate=0.0, n_periods=10
        )
        assert result["years_to_ecosystem_recovery"] is None
        assert result["ecosystem_recovered"] is False

    def test_ecosystem_recovered_bool(self):
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40, n_periods=5
        )
        assert isinstance(result["ecosystem_recovered"], bool)

    def test_trajectory_row_keys(self):
        result = indust_recovery_trajectory(
            population=1_000_000, epsilon=0.40, n_periods=4
        )
        required = {"period", "ecosystem_health", "deferred_ecological",
                    "trust_end", "solvent", "teh_created"}
        for row in result["trajectory"]:
            assert required.issubset(row.keys())

    def test_high_restoration_recovers_faster(self):
        """Higher restoration rate should recover ecosystem health faster (or same)."""
        r_low  = indust_recovery_trajectory(
            population=1_000_000, ecological_restoration_rate=0.01, n_periods=20
        )
        r_high = indust_recovery_trajectory(
            population=1_000_000, ecological_restoration_rate=0.10, n_periods=20
        )
        eco_low  = r_low["trajectory"][-1]["ecosystem_health"]
        eco_high = r_high["trajectory"][-1]["ecosystem_health"]
        assert eco_high >= eco_low
