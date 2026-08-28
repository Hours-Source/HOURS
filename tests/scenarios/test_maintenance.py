"""
Tests for hours_eoh.scenarios.maintenance at the canonical import location.

Covers: deferred_maintenance_crisis, care_registration_delay.
"""

import pytest
from hours_eoh.scenarios.maintenance import _IRREVERSIBILITY_MULTIPLE
from hours_eoh.scenarios.maintenance import (
    deferred_maintenance_crisis,
    care_registration_delay,
)

VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


class TestDeferredMaintenanceCrisis:
    def test_full_fulfillment_stays_stable(self):
        result = deferred_maintenance_crisis(
            epsilon=0.40, annual_eoh=100_000.0,
            fulfillment_fraction=1.0, years=20,
        )
        assert result["outcome"] == "STABLE"
        assert result["crisis_year"] is None

    def test_zero_fulfillment_reaches_crisis_over_long_horizon(self):
        # Compounding in this framework is slow — crisis requires ~100 years.
        result = deferred_maintenance_crisis(
            epsilon=0.40, annual_eoh=100_000.0,
            fulfillment_fraction=0.0, years=100,
        )
        assert result["outcome"] == "CRISIS"
        assert result["crisis_year"] is not None

    def test_trajectory_length_matches_years(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.80, 15)
        assert len(result["trajectory"]) == 15

    def test_deferred_accumulates_monotonically_at_zero_fulfillment(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.0, 10)
        deferreds = [r["cumulative_deferred"] for r in result["trajectory"]]
        assert all(deferreds[i] <= deferreds[i + 1] for i in range(len(deferreds) - 1))

    def test_outcome_is_valid(self):
        for frac in (0.0, 0.60, 1.0):
            result = deferred_maintenance_crisis(0.40, 100_000.0, frac, 20)
            assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = deferred_maintenance_crisis(0.40, 100_000.0, 0.80, 10)
        assert result["scenario"] == "deferred_maintenance_crisis"

    def test_higher_epsilon_softens_compounding(self):
        low_eps  = deferred_maintenance_crisis(0.10, 100_000.0, 0.0, 10)
        high_eps = deferred_maintenance_crisis(0.80, 100_000.0, 0.0, 10)
        # High ε has automation-softened compounding
        assert (high_eps["final_compounding_ratio"]
                <= low_eps["final_compounding_ratio"])


class TestCareRegistrationDelay:
    def test_no_delay_is_stable(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.0)
        assert result["outcome"] == "STABLE"
        assert result["lag_fraction"] == pytest.approx(0.0, abs=1e-9)

    def test_large_delay_is_crisis(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.40)
        assert result["outcome"] == "CRISIS"

    def test_actual_share_less_than_expected(self):
        result = care_registration_delay(epsilon=0.70, delay_epsilon=0.20)
        assert result["actual_care_share"] < result["expected_care_share"]

    def test_lag_fraction_in_range(self):
        result = care_registration_delay(epsilon=0.50, delay_epsilon=0.10)
        assert 0.0 <= result["lag_fraction"] <= 1.0

    def test_teh_deficit_non_negative(self):
        result = care_registration_delay(epsilon=0.60, delay_epsilon=0.15)
        assert result["teh_deficit_per_worker"] >= 0.0

    def test_outcome_is_valid(self):
        for delay in (0.0, 0.10, 0.30):
            result = care_registration_delay(0.60, delay)
            assert result["outcome"] in VALID_OUTCOMES

    def test_scenario_name(self):
        result = care_registration_delay(0.50, 0.10)
        assert result["scenario"] == "care_registration_delay"



class TestTheIrreversibilityThreshold:
    """
    `_IRREVERSIBILITY_MULTIPLE`, pinned — AND TWO DEFECTS IT UNCOVERED
    (2026-08-28).

    It is a shadow constant in `scenarios/maintenance.py` that a +7% move left
    undetected. Asking WHY it was undetectable found that its output never
    reached the caller at all:

      1. `failure_boundary`, documented as "year of irreversibility", RETURNED
         `crisis_year` — a value already returned under its own key. The
         quantity the field names was computed and discarded.
      2. `outcome` came from the compounding ratio alone, so at 20 years of zero
         maintenance the function returned **outcome=STABLE** beside a
         recommendation reading "Deferred maintenance exceeds 5× annual EOH at
         year 5. Rebuilding required." The machine-readable field contradicted
         the human-readable one.

    Both are the reported-value-is-not-the-computed-value failure this repo has
    hit before (`psi` vs `psi_applied`). Neither failed a test, because nothing
    asserted either field against a neglected asset — which is exactly what an
    unpinned constant lets happen downstream of itself.
    """

    def test_the_failure_year_is_actually_returned(self):
        """FIX 1. The field must report the quantity it is named for."""
        r = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=1_000_000.0,
                                        fulfillment_fraction=0.0, years=20)
        assert r["failure_boundary"] is not None, (
            "20 years of zero maintenance must reach irreversibility"
        )
        assert r["failure_boundary"] != r["crisis_year"], (
            "failure_boundary must not be a second copy of crisis_year"
        )

    def test_irreversibility_is_not_reported_as_stable(self):
        """FIX 2. The structured verdict must not contradict the prose."""
        r = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=1_000_000.0,
                                        fulfillment_fraction=0.0, years=20)
        assert "Rebuilding required" in r["recommendation"]
        assert r["outcome"] != "STABLE", (
            f"outcome {r['outcome']!r} contradicts its own recommendation"
        )

    def test_full_maintenance_never_reaches_irreversibility(self):
        """The converse: a threshold that fires under full maintenance is not a
        threshold, it is a clock."""
        r = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=1_000_000.0,
                                        fulfillment_fraction=1.0, years=40)
        assert r["failure_boundary"] is None
        assert r["outcome"] == "STABLE"

    def test_failure_arrives_sooner_the_worse_the_neglect(self):
        years = []
        for frac in (0.0, 0.25, 0.5):
            r = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=1_000_000.0,
                                            fulfillment_fraction=frac, years=30)
            years.append(r["failure_boundary"] or 10**6)
        assert years == sorted(years), f"worse neglect must fail sooner: {years}"

    def test_failure_is_declared_at_the_declared_multiple(self):
        """Binds the constant to the behaviour rather than restating 5.0."""
        annual = 1_000_000.0
        r = deferred_maintenance_crisis(epsilon=0.40, annual_eoh=annual,
                                        fulfillment_fraction=0.0, years=30)
        fy = r["failure_boundary"]
        assert fy is not None
        row = next(t for t in r["trajectory"] if t["year"] == fy)
        assert row["total_obligation"] > annual * _IRREVERSIBILITY_MULTIPLE
        prev = [t for t in r["trajectory"] if t["year"] == fy - 1]
        if prev:
            assert prev[0]["total_obligation"] <= annual * _IRREVERSIBILITY_MULTIPLE
