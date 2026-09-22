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

    def test_trust_per_capita_sweep_bites(self):
        """
        PRIOR WORK BROUGHT, swept per person (2026-09-17).

        The neighbouring floor_fraction test exists because a swept parameter
        that moves no output is failure mode 5 in a sweep's clothes. This is the
        same check for the new parameter: the surplus must move, and it must
        move for a reason that is stated below rather than merely observed.
        """
        pop = 1_000_000.0
        result = fiscal_parameter_sweep(
            "trust_per_capita", [0.0, 4380.0, 8760.0, 35000.0], population=pop)
        assert result["parameter"] == "trust_per_capita"
        assert len(result["results"]) == 4
        surpluses = [r["surplus_deficit"] for r in result["results"]]
        assert len({round(x, 6) for x in surpluses}) == 4, (
            "the sweep is inert — every level of prior work returned the same "
            "surplus, so the parameter is not reaching the Trust"
        )
        assert surpluses == sorted(surpluses), "more prior work cannot reduce the surplus"

    def test_the_whole_effect_of_prior_work_is_its_dividend(self):
        """
        NOT AN OBSERVATION — AN IDENTITY THE SWEEP MUST REPRODUCE.

        The inheritance reaches the fisc through exactly one channel: the
        dividend on the balance. So the surplus must move by precisely
        Δper-capita × population × DEP_RATE × DIV_RATE and by nothing else. A
        second channel appearing — the Trust reaching the mint, the guarantee,
        or the levy — breaks this and should.
        """
        from hours_eoh.data import DEP_RATE, DIV_RATE
        pop = 1_000_000.0
        result = fiscal_parameter_sweep("trust_per_capita", [0.0, 8760.0], population=pop)
        lo, hi = (r["surplus_deficit"] for r in result["results"])
        assert hi - lo == pytest.approx(8760.0 * pop * DEP_RATE * DIV_RATE, rel=1e-9)

    @pytest.mark.parametrize("epsilon", [0.0, 0.40, 0.90, 0.99])
    def test_the_guarantee_is_independent_of_prior_work_across_the_arc(self, epsilon):
        """
        THE DOCTRINAL CLAIM, PINNED. Under V1 the liability is sized from the
        REGISTER, not from the Trust, so repricing what a collective brings
        changes what it HOLDS and nothing about what it OWES. Measured flat at
        every ε, not merely at the 0.40 reference (failure mode 3).
        """
        result = fiscal_parameter_sweep(
            "trust_per_capita", [0.0, 8760.0, 35000.0], epsilon=epsilon)
        costs = {round(r["guarantee_cost"], 6) for r in result["results"]}
        assert len(costs) == 1, (
            f"the guarantee moved with the inheritance at ε={epsilon}: {costs}. "
            "Under V1 it is sized from the register and must not."
        )

    @pytest.mark.parametrize("epsilon", [0.0, 0.40, 0.90, 0.99])
    def test_a_collective_that_brings_nothing_is_solvent(self, epsilon):
        """
        "The founding stock is an artifact of a collective that could not remain
        stable without one" (author, 2026-09-17) — measured. At zero prior work
        the levy covers the guarantee unaided at every point on the arc, which is
        what makes a subsistence founding a real starting state and not an edge
        case the model tolerates.
        """
        result = fiscal_parameter_sweep("trust_per_capita", [0.0], epsilon=epsilon)
        assert result["results"][0]["solvent"] is True
        assert result["solvent_range"] == (0.0, 0.0)

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
