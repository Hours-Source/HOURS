"""
Finding D — the food conservation test, rebuilt in scenarios/.

The scratch-script version compared a single US total against the LSMS figure
and called the result ambiguous. These tests pin the STAGE decomposition that
replaced it, and guard the two properties that make it usable: the paid term is
a lower bound whose incompleteness is quantified, and the LSMS processing term is
unmeasured rather than zero.
"""

import pytest

from hours_eoh.scenarios.food_conservation import (
    LSMS_CROP_PRODUCTION_HOURS,
    LSMS_PROCESSING_HOURS,
    SOC_AGRICULTURE,
    UNCOUNTED_SECTORS,
    conservation_test,
    food_system_employment,
    hours_per_worker_year,
    uncounted_headroom,
    unpaid_food_hours,
    unpaid_food_series,
)


class TestDerivedHoursPerWorker:
    """No chosen annual-hours constant: both sides are measured."""

    def test_lands_in_a_plausible_band(self):
        assert 1_500.0 < hours_per_worker_year() < 2_200.0

    def test_matches_the_worked_example(self):
        assert hours_per_worker_year() == pytest.approx(1874.4, abs=1.0)

    def test_derived_from_atus_and_the_registry_not_a_literal(self):
        """Changing the year must move it — a constant would not."""
        assert hours_per_worker_year(2003) != hours_per_worker_year(2025)


class TestFoodSystemEmployment:

    def test_stage_headcounts(self):
        e = food_system_employment()
        assert e["production"] == pytest.approx(919_500.0, rel=1e-3)
        assert e["processing"] == pytest.approx(869_900.0, rel=1e-3)
        assert e["service"] == pytest.approx(14_173_800.0, rel=1e-3)

    def test_service_dwarfs_production(self):
        """Fifteen times as many people serve food as grow it. That ordering is
        itself the shape of the result."""
        e = food_system_employment()
        assert e["service"] / e["production"] > 10.0

    def test_forestry_is_excluded_from_agriculture(self):
        """SOC 45-4 is forest, conservation and logging — not food. Including it
        would inflate the stage where the US number is smallest."""
        assert "454" not in SOC_AGRICULTURE


class TestUnpaidFoodHours:

    def test_us_households_do_not_produce_food(self):
        """Nothing maps to production, and that IS the result — not a gap."""
        assert unpaid_food_hours(2025)["production"] == 0.0

    def test_matches_the_worked_example(self):
        u = unpaid_food_hours(2025)
        assert u["processing"] == pytest.approx(215.6, abs=0.5)
        assert u["service"] == pytest.approx(90.4, abs=0.5)


class TestConservationTest:

    def test_production_collapsed_by_two_orders(self):
        """
        THE ROBUST HALF. 320 → 5.1 h/person·yr. Every uncounted term raises the
        US side and it is still ~62× below, so no plausible completion of the
        paid term reverses this.
        """
        r = conservation_test(2025)
        production = next(s for s in r["stages"] if s["stage"] == "production")
        assert production["us_total_hours"] == pytest.approx(5.1, abs=0.5)
        assert r["production_ratio"] < 0.02

    def test_preparation_did_not_collapse(self):
        """
        THE OTHER HALF, and the one that bears on the framework's claim. US
        preparation runs ~220 h/person·yr — the same order as the whole LSMS
        production figure — against an LSMS processing term nobody has measured.
        """
        r = conservation_test(2025)
        processing = next(s for s in r["stages"] if s["stage"] == "processing")
        assert processing["us_total_hours"] > 200.0
        assert processing["lsms_hours"] is None

    def test_unpaid_dominates_the_non_production_stages(self):
        """The registered ledger did not absorb preparation — households did."""
        r = conservation_test(2025)
        for name in ("processing", "service"):
            stage = next(s for s in r["stages"] if s["stage"] == name)
            assert stage["us_unpaid_hours"] > stage["us_paid_hours"]

    def test_totals_are_comparable_and_that_is_the_trap(self):
        """
        The single-total reading: 395 vs 320, "ambiguous". Both sides are lower
        bounds, so the totals genuinely cannot settle it — which is why the
        stage decomposition exists and why this test asserts the ambiguity
        rather than papering over it.
        """
        r = conservation_test(2025)
        assert 300.0 < r["us_total"] < 500.0
        assert r["us_total_is_lower_bound"] is True

    def test_lsms_processing_is_unmeasured_not_zero(self):
        """An unmeasured term is not a zero term — the same rule the floor's
        `unreachable` handling enforces."""
        assert LSMS_PROCESSING_HOURS is None

    def test_verdict_states_both_halves(self):
        v = conservation_test(2025)["verdict"]
        assert "PRODUCTION" in v and "PREPARATION" in v

    def test_caveat_names_the_basket_confound(self):
        c = conservation_test(2025)["caveat"]
        assert "not held fixed" in c

    def test_runs_for_any_survey_year(self):
        for year in (2003, 2013, 2025):
            assert conservation_test(year)["us_total"] > 0.0


class TestUncountedHeadroom:
    """The missing sectors, priced instead of hand-waved."""

    def test_one_percent_of_employment_is_small_against_the_gap(self):
        h = uncounted_headroom(0.01)
        assert h["hours_per_capita"] == pytest.approx(9.4, abs=0.5)
        assert h["hours_per_capita"] < LSMS_CROP_PRODUCTION_HOURS / 10.0

    def test_scales_linearly(self):
        one = uncounted_headroom(0.01)["hours_per_capita"]
        ten = uncounted_headroom(0.10)["hours_per_capita"]
        assert ten == pytest.approx(10.0 * one, rel=1e-9)

    def test_closing_the_production_gap_would_take_implausible_employment(self):
        """~34% of ALL national employment would have to be uncounted food
        system. It is not, so the production finding stands."""
        per_point = uncounted_headroom(0.01)["hours_per_capita"]
        needed = LSMS_CROP_PRODUCTION_HOURS / per_point / 100.0
        assert needed > 0.30

    def test_every_uncounted_sector_is_named_with_a_reason(self):
        assert "self_employed_farmers" in UNCOUNTED_SECTORS
        for name, reason in UNCOUNTED_SECTORS.items():
            assert len(reason) > 20, f"{name} has no stated reason"

    def test_share_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="employment_share must be in"):
            uncounted_headroom(1.5)


class TestUnpaidSeries:

    def test_preparation_rose_and_provisioning_fell(self):
        s = unpaid_food_series()
        assert s["preparation_change"] > 0.30
        assert s["provisioning_change"] < -0.20

    def test_paid_term_is_flagged_frozen(self):
        """The registry is one epoch, so a full-test time series does not exist
        and is not faked."""
        assert unpaid_food_series()["paid_term_is_epoch_frozen"] is True

    def test_series_is_reported_per_person_15plus_not_per_capita(self):
        """
        THE TRAP THIS SERIES FELL INTO ONCE. A fixed total_population across 22
        years divides by a constant while the 15+ population grows 23%, which
        alone turned the measured -26% provisioning decline into -8%. The series
        stays in the ATUS native unit; only single-year figures are per capita.
        """
        rows = unpaid_food_series()["rows"]
        first = next(r for r in rows if r["year"] == 2003)
        assert first["preparation"] == pytest.approx(194.3, abs=0.5)
        assert first["provisioning"] == pytest.approx(146.4, abs=0.5)

    def test_2020_is_excluded(self):
        years = [row["year"] for row in unpaid_food_series()["rows"]]
        assert 2020 not in years
        assert years[0] == 2003 and years[-1] == 2025
