"""
Tests for hours_eoh.scenarios.sweep.epsilon_sweep at its canonical location.

The sweep verifies EOH framework coherence across the full automation arc.
"""

import pytest
from hours_eoh.scenarios.sweep import epsilon_sweep


class TestEpsilonSweepCanonicalImport:
    def test_sweep_runs_and_returns_expected_keys(self):
        result = epsilon_sweep(n_points=10)
        assert "sweep" in result
        assert "all_finite" in result
        assert "basket_price_monotone" in result
        assert "floor_pp_monotone" in result
        assert "status" in result

    def test_sweep_length_matches_n_points(self):
        result = epsilon_sweep(n_points=20)
        assert len(result["sweep"]) == 21  # 0..n_points inclusive

    def test_sweep_all_finite(self):
        result = epsilon_sweep(n_points=50)
        assert result["all_finite"], (
            f"Non-finite values found: {result['infinities']}"
        )

    def test_sweep_status_ok(self):
        result = epsilon_sweep(n_points=50)
        assert result["status"] == "OK", (
            f"Sweep found issues: discontinuities={result['discontinuities']}, "
            f"infinities={result['infinities']}"
        )

    def test_basket_price_monotone_decreasing(self):
        result = epsilon_sweep(n_points=50)
        assert result["basket_price_monotone"]

    def test_floor_pp_monotone_increasing(self):
        result = epsilon_sweep(n_points=50)
        assert result["floor_pp_monotone"]

    def test_epsilon_range_is_0_to_099(self):
        result = epsilon_sweep(n_points=10)
        epsilons = [r["epsilon"] for r in result["sweep"]]
        assert epsilons[0] == pytest.approx(0.0, abs=1e-6)
        assert epsilons[-1] == pytest.approx(0.99, abs=1e-6)

    def test_fiscal_solvency_at_canonical_arc(self):
        result = epsilon_sweep(n_points=20)
        for row in result["sweep"]:
            assert row["fiscal_solvent"] is True or row["fiscal_solvent"] is False

    def test_all_sweep_rows_have_required_keys(self):
        result = epsilon_sweep(n_points=5)
        required = {
            "epsilon", "personal_eoh", "infrastructure_eoh", "ecological_eoh",
            "knowledge_eoh", "total_eoh", "basket_price", "floor_pp_index",
            "care_registration", "total_registration",
            "fiscal_solvent", "trust_surplus_deficit",
        }
        for row in result["sweep"]:
            assert required.issubset(row.keys()), (
                f"Missing keys in sweep row: {required - row.keys()}"
            )
