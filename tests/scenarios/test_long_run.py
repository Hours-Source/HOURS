"""
Tests for hours_eoh.scenarios.long_run.

Covers: canonical_arc_trajectory, trust_depletion_stress,
        automation_transition_trajectory.
"""

import math
import pytest
from hours_eoh.scenarios.long_run import (
    canonical_arc_trajectory,
    trust_depletion_stress,
    automation_transition_trajectory,
)

VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


# ===========================================================================
# canonical_arc_trajectory
# ===========================================================================

class TestCanonicalArcTrajectory:

    def test_returns_expected_keys(self):
        result = canonical_arc_trajectory(n_periods=5)
        for key in ("scenario", "epsilon_start", "epsilon_end", "n_periods",
                    "solvent_all", "first_insolvency", "summary_table",
                    "inflection_points", "raw"):
            assert key in result

    def test_scenario_name(self):
        assert canonical_arc_trajectory(n_periods=5)["scenario"] == "canonical_arc_trajectory"

    def test_summary_table_length(self):
        result = canonical_arc_trajectory(n_periods=10)
        assert len(result["summary_table"]) == 10

    def test_summary_table_row_keys(self):
        result = canonical_arc_trajectory(n_periods=5)
        required = {"period", "epsilon", "teh_created", "trust_end",
                    "solvent", "ecosystem_health", "basket_price"}
        for row in result["summary_table"]:
            assert required.issubset(row.keys())

    def test_epsilon_advances_from_start_to_end(self):
        result = canonical_arc_trajectory(epsilon_start=0.10, epsilon_end=0.50, n_periods=8)
        epsilons = [r["epsilon"] for r in result["summary_table"]]
        assert epsilons[0] > 0.10          # advanced at least once
        assert epsilons[-1] <= 0.50 + 1e-6  # did not exceed end

    def test_all_summary_values_finite(self):
        result = canonical_arc_trajectory(n_periods=10)
        for row in result["summary_table"]:
            for key, val in row.items():
                if isinstance(val, float):
                    assert math.isfinite(val), f"Non-finite {key} at period {row['period']}"

    def test_solvent_all_is_bool(self):
        result = canonical_arc_trajectory(n_periods=5)
        assert isinstance(result["solvent_all"], bool)

    def test_first_insolvency_none_or_int(self):
        result = canonical_arc_trajectory(n_periods=5)
        assert result["first_insolvency"] is None or isinstance(result["first_insolvency"], int)

    def test_inflection_points_is_list(self):
        result = canonical_arc_trajectory(n_periods=10)
        assert isinstance(result["inflection_points"], list)

    def test_canonical_arc_solvent_across_full_range(self):
        """Canonical arc at default params must remain solvent throughout."""
        result = canonical_arc_trajectory(epsilon_start=0.0, epsilon_end=0.99, n_periods=20)
        assert result["solvent_all"] is True

    def test_basket_price_decreasing_over_arc(self):
        """Basket price must decrease as ε rises (Principle 5)."""
        result = canonical_arc_trajectory(epsilon_start=0.0, epsilon_end=0.80, n_periods=16)
        prices = [r["basket_price"] for r in result["summary_table"]]
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1] - 1e-6, (
                f"Basket price rose at period {i + 1}: {prices[i]} → {prices[i + 1]}"
            )

    def test_raw_contains_run_simulation_keys(self):
        result = canonical_arc_trajectory(n_periods=5)
        for key in ("states", "period_results", "final_state", "solvent_all", "summary"):
            assert key in result["raw"]

    def test_single_period_run(self):
        result = canonical_arc_trajectory(n_periods=1)
        assert len(result["summary_table"]) == 1

    def test_ecological_degradation_stressor_passes_through(self):
        """sim_kwargs forwarded to run_simulation — ecosystem should degrade faster."""
        r_base = canonical_arc_trajectory(n_periods=10)
        r_stress = canonical_arc_trajectory(n_periods=10, ecological_degradation_rate=0.05)
        base_eco = r_base["summary_table"][-1]["ecosystem_health"]
        stress_eco = r_stress["summary_table"][-1]["ecosystem_health"]
        assert stress_eco < base_eco


# ===========================================================================
# trust_depletion_stress
# ===========================================================================

class TestTrustDepletionStress:

    def test_returns_expected_keys(self):
        result = trust_depletion_stress(n_periods=5)
        for key in ("scenario", "epsilon", "n_periods", "stressor_profile",
                    "first_insolvency", "trust_floor", "depletion_rate_per_period",
                    "outcome", "recommendation", "raw"):
            assert key in result

    def test_scenario_name(self):
        assert trust_depletion_stress(n_periods=5)["scenario"] == "trust_depletion_stress"

    def test_null_stressors_is_stable(self):
        """Default stressor_profile (None) must produce STABLE outcome."""
        result = trust_depletion_stress(epsilon=0.40, n_periods=10)
        assert result["outcome"] == "STABLE"

    def test_outcome_is_valid(self):
        result = trust_depletion_stress(n_periods=5)
        assert result["outcome"] in VALID_OUTCOMES

    def test_ecological_stressors_no_longer_move_this_outcome(self):
        """
        RENAMED AND RESTATED 2026-09-08. This was
        `test_high_degradation_worsens_outcome`, asserting `stressed >= base` on
        a severity scale — which held by EQUALITY and could not fail.

        Both stressors are structurally inert HERE, and the reason is adopted
        policy rather than a defect. Phase 4e/4f moved every recurring
        ecological term to the Ground Use Fee, so the domain is 0.0 and
        degrading the ecosystem no longer moves a fiscal outcome. And
        `trust_depletion_stress` builds its state without `deferred_ecological`,
        so `deferred_eco_growth_rate` could not bite at ANY value — the stock it
        multiplies is always zero. See
        `test_simulation.TestTheDeferredEcologicalRate` for where that parameter
        IS live.

        Pinned as equality so it fails in BOTH directions: if a future change
        makes ecological condition reach the fiscal path again, this fires and
        someone re-reads the partition before accepting it.
        """
        base = trust_depletion_stress(epsilon=0.40, n_periods=20)
        stressed = trust_depletion_stress(
            epsilon=0.40, n_periods=20,
            stressor_profile={"ecological_degradation_rate": 0.10,
                               "deferred_eco_growth_rate": 0.30},
        )
        assert stressed["outcome"] == base["outcome"]
        assert stressed["trust_floor"] == pytest.approx(
            base["trust_floor"], rel=1e-12
        ), (
            "an ecological stressor moved the trust floor. Under Phase 4e/4f "
            "the domain is empty and this should be impossible — check whether "
            "the obligation is now being charged BOTH to the domain and to GUF."
        )

    def test_the_trust_no_longer_depletes_under_the_default_design(self):
        """RESTATED 2026-09-16: this asserted the floor stays BELOW the opening
        balance, which was true while the Trust booked the shipped guarantee.

        Under V1 — core's default since 2026-09-16 — the Trust owes only what is
        on the ledger, and at these inputs the levy more than covers it: the
        floor is 35,007,388,914 against an opening 35,000,000,000, outcome
        STABLE with no insolvency. A depletion stress that cannot deplete is
        worth stating plainly rather than leaving as an inverted assertion, and
        the shipped design is still reachable for the old behaviour.
        """
        from hours_eoh.data import TRUST_BASE_TEH
        result = trust_depletion_stress(n_periods=10)
        assert result["trust_floor"] >= TRUST_BASE_TEH
        assert result["outcome"] == "STABLE"
        assert result["first_insolvency"] is None

    def test_recommendation_is_string(self):
        result = trust_depletion_stress(n_periods=5)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 10

    def test_first_insolvency_none_when_stable(self):
        result = trust_depletion_stress(epsilon=0.40, n_periods=10)
        if result["outcome"] == "STABLE":
            assert result["first_insolvency"] is None

    def test_raw_trajectory_length(self):
        result = trust_depletion_stress(n_periods=8)
        assert len(result["raw"]["period_results"]) == 8


# ===========================================================================
# automation_transition_trajectory
# ===========================================================================

class TestAutomationTransitionTrajectory:

    def test_returns_expected_keys(self):
        result = automation_transition_trajectory(n_periods=5)
        for key in ("scenario", "epsilon_start", "epsilon_delta", "n_periods",
                    "trajectory", "convergence_period", "raw"):
            assert key in result

    def test_scenario_name(self):
        r = automation_transition_trajectory(n_periods=5)
        assert r["scenario"] == "automation_transition_trajectory"

    def test_trajectory_length_matches_n_periods(self):
        result = automation_transition_trajectory(n_periods=10)
        assert len(result["trajectory"]) == 10

    def test_trajectory_row_keys(self):
        result = automation_transition_trajectory(n_periods=5)
        required = {"period", "epsilon", "teh_in_circulation", "floor_pp_index",
                    "labor_income", "trust_surplus_deficit", "solvent", "basket_price"}
        for row in result["trajectory"]:
            assert required.issubset(row.keys())

    def test_epsilon_advances_over_trajectory(self):
        result = automation_transition_trajectory(epsilon_start=0.10, epsilon_delta=0.05,
                                                  n_periods=8)
        epsilons = [r["epsilon"] for r in result["trajectory"]]
        assert epsilons[-1] > epsilons[0]

    def test_basket_price_decreases_over_transition(self):
        """Principle 5: basket price falls as automation rises."""
        result = automation_transition_trajectory(epsilon_start=0.10, epsilon_delta=0.05,
                                                  n_periods=10)
        prices = [r["basket_price"] for r in result["trajectory"]]
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1] - 1e-6, (
                f"Basket price rose at step {i}: {prices[i]} → {prices[i + 1]}"
            )

    def test_all_trajectory_values_finite(self):
        result = automation_transition_trajectory(n_periods=8)
        for row in result["trajectory"]:
            for key, val in row.items():
                if isinstance(val, float):
                    assert math.isfinite(val), f"Non-finite {key} at period {row['period']}"

    def test_convergence_period_none_or_int(self):
        result = automation_transition_trajectory(n_periods=5)
        assert result["convergence_period"] is None or isinstance(result["convergence_period"], int)

    def test_labor_income_is_positive(self):
        result = automation_transition_trajectory(n_periods=5)
        for row in result["trajectory"]:
            assert row["labor_income"] > 0.0

    def test_floor_pp_index_is_positive(self):
        result = automation_transition_trajectory(n_periods=5)
        for row in result["trajectory"]:
            assert row["floor_pp_index"] > 0.0
