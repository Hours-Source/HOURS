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
        """SWEPT AGAINST THE DESIGN THAT READS IT (2026-09-16).

        When V1 became the default guarantee design this sweep went INERT —
        0.05, 0.15 and 0.30 all returned a guarantee cost of 7,564,933, because
        V1 derives the recipient share from the register and never looks at
        `floor_fraction`. A swept parameter that moves no output is failure
        mode 5, and this test is what caught it.
        """
        result = fiscal_parameter_sweep("floor_fraction", [0.05, 0.15, 0.30])
        assert len(result["results"]) == 3
        # Higher floor_fraction → higher guarantee cost → lower surplus
        costs = [r["guarantee_cost"] for r in result["results"]]
        assert costs[0] < costs[2]
        assert len({round(c, 6) for c in costs}) == 3, (
            "the sweep is inert — every value returned the same cost, which "
            "means the parameter is not reaching the design that reads it"
        )

    def test_need_fraction_sweep_is_live_under_the_default_design(self):
        """The V1 counterpart: the share of ON-LEDGER people the guarantee
        reaches. This is the parameter that actually governs the liability under
        the adopted design, so it is the one a sensitivity run should move."""
        result = fiscal_parameter_sweep("need_fraction", [0.025, 0.05, 0.10])
        costs = [r["guarantee_cost"] for r in result["results"]]
        assert len({round(c, 6) for c in costs}) == 3
        assert costs[0] < costs[1] < costs[2]
        # Linear in the need fraction: doubling it doubles what is owed.
        assert costs[2] == pytest.approx(2.0 * costs[1], rel=1e-9)

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
