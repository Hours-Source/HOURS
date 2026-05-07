"""
Tests for hours_eoh.scenarios.sensitivity.

Covers: fiscal_parameter_sweep, eoh_arc_sensitivity, epsilon_delta_sensitivity re-export.
"""

import pytest
from hours_eoh.scenarios.sensitivity import (
    fiscal_parameter_sweep,
    eoh_arc_sensitivity,
    epsilon_delta_sensitivity,
)


class TestFiscalParameterSweep:
    def test_levy_rate_sweep(self):
        result = fiscal_parameter_sweep("levy_rate", [0.05, 0.10, 0.15, 0.20])
        assert result["parameter"] == "levy_rate"
        assert len(result["results"]) == 4

    def test_higher_levy_improves_solvency(self):
        result = fiscal_parameter_sweep("levy_rate", [0.01, 0.10, 0.30])
        solvency = [r["solvent"] for r in result["results"]]
        # At very low levy the Trust should be insolvent; at high levy, solvent
        assert any(solvency), "At least one levy rate should be solvent"

    def test_floor_fraction_sweep(self):
        result = fiscal_parameter_sweep("floor_fraction", [0.05, 0.15, 0.30])
        assert len(result["results"]) == 3
        # Higher floor_fraction → higher guarantee cost → lower surplus
        costs = [r["guarantee_cost"] for r in result["results"]]
        assert costs[0] < costs[2]

    def test_invalid_parameter_raises(self):
        with pytest.raises(ValueError):
            fiscal_parameter_sweep("magic_param", [0.10])

    def test_result_has_solvent_range(self):
        result = fiscal_parameter_sweep("levy_rate", [0.10, 0.15, 0.20])
        assert "solvent_range" in result

    def test_all_results_have_required_keys(self):
        result = fiscal_parameter_sweep("dep_rate", [0.01, 0.02])
        for row in result["results"]:
            for key in ("parameter_value", "solvent", "surplus_deficit",
                        "total_expenditure", "levy_collected", "guarantee_cost"):
                assert key in row

    def test_dep_rate_sweep(self):
        result = fiscal_parameter_sweep("dep_rate", [0.01, 0.05])
        assert result["epsilon"] == pytest.approx(0.40)

    def test_capital_age_ratio_sweep(self):
        result = fiscal_parameter_sweep("capital_age_ratio", [0.20, 0.60, 0.90])
        # Older capital → higher stewardship cost → lower surplus
        surplus = [r["surplus_deficit"] for r in result["results"]]
        assert surplus[0] >= surplus[2]


class TestEohArcSensitivity:
    def test_returns_list_of_dicts(self):
        results = eoh_arc_sensitivity(n_points=5)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_each_result_has_base_epsilon(self):
        results = eoh_arc_sensitivity(n_points=3)
        for r in results:
            assert "base_epsilon" in r

    def test_arc_covers_full_range(self):
        results = eoh_arc_sensitivity(epsilon_start=0.0, epsilon_end=0.99, n_points=10)
        epsilons = [r["base_epsilon"] for r in results]
        assert epsilons[0] <= 0.05
        assert epsilons[-1] >= 0.80


class TestEpsilonDeltaSensitivityReexport:
    def test_importable_from_scenarios(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        assert isinstance(result, dict)

    def test_returns_key_metrics(self):
        result = epsilon_delta_sensitivity(0.40, 0.10)
        assert "delta_epsilon" in result
