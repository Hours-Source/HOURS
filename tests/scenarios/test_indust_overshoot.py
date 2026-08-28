"""
Tests for hours_eoh.scenarios.indust_overshoot.

Covers: indust_overshoot_baseline, indust_recovery_trajectory.
"""

import pytest

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.eoh_generation import ecological_eoh_breakdown
from hours_eoh.data import CAPITAL_STOCK_DEFAULT, ECOLOGICAL_THRESHOLD
from hours_eoh.indust_no_eco_params import (
    INDUST_CAPITAL_AGE_RATIO,
    INDUST_CAPITAL_EOH_ELIMINATED,
    INDUST_CAPITAL_MULTIPLIER,
    INDUST_CAPITAL_PERSONAL_EOH_FULFILLED,
    INDUST_DEFERRED_ECOLOGICAL,
    INDUST_ECOSYSTEM_HEALTH,
    INDUST_NO_ECO_PIPELINE_KWARGS,
    make_indust_no_eco_params,
)
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


class TestTheArchetypeIsWhatItClaims:
    """
    THE SCENARIO'S DEFINING PROPERTIES, pinned (2026-08-28).

    `indust_no_eco_params.py` holds five shadow constants and a 2026-08-28
    mutation sweep found four of them completely unpinned — including BOTH
    zeros that encode the archetype's central premise.

    THEY ARE NOT MIGRATED TO data.py, DELIBERATELY. `data.py` is the framework's
    structural constants; these are ONE SCENARIO'S inputs — the specification of
    an archetype, in the same class as `make_urban_collective()`'s parcel mix.
    Moving them would say the framework asserts a 10× capital stock, which it
    does not. What was missing is not provenance but a check that the archetype
    still IS what its docstring says.

    An unpinned specification is the thing that silently stops being true.
    """

    def test_capital_is_the_declared_multiple_of_canonical(self):
        p = make_indust_no_eco_params(population=1_000_000)
        canonical_per_capita = CAPITAL_STOCK_DEFAULT / 1_000_000
        assert p.get("capital_stock_teh") / 1_000_000 == pytest.approx(
            canonical_per_capita * INDUST_CAPITAL_MULTIPLIER, rel=1e-9
        )
        assert INDUST_CAPITAL_MULTIPLIER > 1.0, "overshoot means MORE capital"

    def test_capital_scales_with_population(self):
        """The archetype is an intensity, not an absolute stock."""
        a = make_indust_no_eco_params(population=1_000_000).get("capital_stock_teh")
        b = make_indust_no_eco_params(population=4_000_000).get("capital_stock_teh")
        assert b == pytest.approx(4.0 * a, rel=1e-9)

    def test_the_stock_is_aged_past_mid_life(self):
        """'Deferred renewal typical of heavy industry' — the claim is that this
        stock is OLD, not merely present."""
        assert 0.5 < INDUST_CAPITAL_AGE_RATIO < 1.0

    def test_ecosystem_health_sits_BELOW_the_spike_threshold(self):
        """
        THE RELATIONAL PROPERTY, and the reason this is the most valuable pin in
        the class. The archetype is defined as being IN the threshold-failure
        regime — its docstring says "the nonlinear penalty in ecological_eoh()
        is now live". That is a claim about 0.38 relative to
        ECOLOGICAL_THRESHOLD, not about 0.38 itself.

        `ECOLOGICAL_THRESHOLD` is a `placeholder` whose own tag block says where
        0.40 falls on the health index is "a mapping, not a measurement". If it
        is ever measured downward past 0.38, this scenario silently stops being
        an overshoot scenario while every one of its tests still passes. Pinning
        the VALUE would not catch that; pinning the RELATION does.
        """
        assert INDUST_ECOSYSTEM_HEALTH < ECOLOGICAL_THRESHOLD, (
            f"the archetype must sit in the spike regime: health "
            f"{INDUST_ECOSYSTEM_HEALTH} vs threshold {ECOLOGICAL_THRESHOLD}"
        )

    def test_the_spike_is_actually_live_in_the_archetype(self):
        """The relation above, demonstrated through the ecological domain rather
        than asserted about two numbers."""
        b = ecological_eoh_breakdown(INDUST_ECOSYSTEM_HEALTH, area_hectares=1.0e6)
        assert b["spike"] > 0.0, "the nonlinear penalty must be live"

    def test_capital_provides_no_offset_in_any_domain(self):
        """
        THE ARCHETYPE'S CENTRAL PREMISE — "it consumes entropy obligations, it
        does not reduce them" — and BOTH constants encoding it were unpinned.
        They are zero, so a mutation sweep that scales by a percentage cannot
        move them at all; only an explicit test can hold them.
        """
        assert INDUST_CAPITAL_EOH_ELIMINATED == 0.0
        assert INDUST_CAPITAL_PERSONAL_EOH_FULFILLED == 0.0
        assert INDUST_NO_ECO_PIPELINE_KWARGS["capital_eoh_eliminated"] == 0.0
        assert INDUST_NO_ECO_PIPELINE_KWARGS["capital_personal_eoh_fulfilled"] == 0.0

    def test_the_no_offset_premise_reaches_the_pipeline(self):
        """
        The premise must be OBSERVABLE, not just declared: granting the same
        capital an offset must reduce total EOH, so the archetype's zero is
        doing real work.
        """
        p = make_indust_no_eco_params(population=1_000_000)
        common = dict(
            epsilon=0.40, population=1_000_000,
            capital_stock=p.get("capital_stock_teh"),
            capital_age_ratio=p.get("capital_age_ratio"),
            ecosystem_health=p.get("ecosystem_health"),
        )
        no_offset = eoh_to_teh_pipeline(**common, **INDUST_NO_ECO_PIPELINE_KWARGS)
        with_offset = eoh_to_teh_pipeline(
            **common, capital_eoh_eliminated=1.0e8,
            capital_personal_eoh_fulfilled=0.0,
        )
        assert with_offset["total_eoh"] < no_offset["total_eoh"], (
            "if an offset changes nothing, the archetype's zero is decorative"
        )

    def test_the_deferred_backlog_is_large_relative_to_the_standing_obligation(self):
        """'Four-to-five decades of neglect' is a claim about MAGNITUDE. A
        backlog smaller than one year's obligation would not be a backlog."""
        standing = ecological_eoh_breakdown(
            INDUST_ECOSYSTEM_HEALTH, area_hectares=1.0e6
        )["total"]
        assert INDUST_DEFERRED_ECOLOGICAL > 100.0 * standing
