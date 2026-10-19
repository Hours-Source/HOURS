"""Finding D: the food conservation test, rebuilt in scenarios/.

A single US total against the LSMS figure gives an ambiguous result. These tests pin the
STAGE decomposition that replaced that reading. They also guard two properties: the paid
term is a lower bound whose gap is quantified, and the LSMS processing term is
unmeasured, not zero.
"""

import pytest

from hours_eoh.data import BASKET_DIET_KCAL_PER_DAY
from hours_eoh.reference.personal_basket import (
    DIET_DAYS_PER_YEAR,
    NUTRITION_CROSSCHECK_HOURS_PER_YEAR,
    NUTRITION_HOURS_PER_KCAL,
)
from hours_eoh.scenarios.food_conservation import (
    LSMS_CROP_PRODUCTION_BAND,
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
    """Annual hours per worker are derived; both sides are measured and none is chosen.
    """

    def test_lands_in_a_plausible_band(self):
        assert 1_500.0 < hours_per_worker_year() < 2_200.0

    def test_matches_the_worked_example(self):
        assert hours_per_worker_year() == pytest.approx(1874.4, abs=1.0)

    def test_derived_from_atus_and_the_registry_not_a_literal(self):
        """Changing the year must move it — a constant would not."""
        assert hours_per_worker_year(2003) != hours_per_worker_year(2025)


class TestTheRatioIsPopulationFree:
    """`hours_per_worker_year` takes no population. It once took `total_population` and
    multiplied it out and back in, so every population gave the same answer. The wiring
    gate found this, not this file
    ([record](record/personal.md#food-conservation-test-history)).
    """

    def test_it_takes_no_population_at_all(self):
        """
        The parameter is GONE, not defaulted. A cancelling parameter left in
        place is a false affordance — it advertises a reframing that does not
        happen.
        """
        import inspect
        params = set(inspect.signature(hours_per_worker_year).parameters)
        assert params == {"year"}, (
            "hours per worker does not depend on how many non-workers there "
            "are; a population parameter here can only mislead"
        )

    def test_the_value_did_not_move(self):
        """
        It must not: a parameter that cancels cannot have been affecting the
        answer. If this ever moves, the removal was not a pure cancellation and
        the derivation needs re-reading.
        """
        assert hours_per_worker_year() == pytest.approx(1874.428397952944, rel=1e-12)

    def test_it_is_built_from_the_15plus_AGGREGATE(self):
        """
        The governing equation, checked against its own inputs rather than
        against a remembered number.
        """
        from hours_eoh.reference import atus_time_use as atus
        from hours_eoh.scenarios.food_conservation import (
            REGISTRY_EMPLOYMENT_COVERAGE, load_registry)
        y = atus.latest_year()
        numerator = (atus.hours_per_person_15plus(y, ("05",))
                     * atus.population_15_plus(y))
        covered = sum(r["employment_k"] for r in load_registry()) * 1_000.0
        assert hours_per_worker_year() == pytest.approx(
            numerator / (covered / REGISTRY_EMPLOYMENT_COVERAGE)
        )

    def test_callers_that_need_per_capita_still_carry_their_own_population(self):
        """
        The frame did not vanish — it moved to where it belongs. A caller
        converting to per-capita still divides by its own total_population, and
        that parameter is LIVE.
        """
        from hours_eoh.scenarios.food_conservation import uncounted_headroom
        a = uncounted_headroom(total_population=335e6)
        b = uncounted_headroom(total_population=200e6)
        assert a["hours_per_capita"] != b["hours_per_capita"]


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
        # 215.6 / 90.4 over the round 335M; at the survey year's Census 15+ share since 2026-10-15.
        assert u["processing"] == pytest.approx(215.1, abs=0.5)
        assert u["service"] == pytest.approx(90.1, abs=0.5)


class TestConservationTest:

    def test_production_collapsed_by_two_orders(self):
        """Production labour fell from 331 to 5.1 h/person·yr. Every uncounted term
        raises the US side, and it is still about 65× below, so no plausible completion
        of the paid term reverses this.
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
        """The single totals (393 against 331 h/person·yr) are both lower bounds, so
        they cannot settle the question. The test asserts the ambiguity, which is why
        the stage decomposition exists.
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
        """About 36% of ALL national employment would have to be uncounted food system
        to close the production gap. It is not, so the production finding stands.
        """
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
        """The registry is one epoch, so no full-test time series exists, and none is
        faked.
        """
        assert unpaid_food_series()["paid_term_is_epoch_frozen"] is True

    def test_series_is_reported_per_person_15plus_not_per_capita(self):
        """The series stays per person aged 15+, the ATUS native unit; only single-year
        figures are per capita. A fixed population across 22 years once turned the
        measured −26% provisioning decline into −8%
        ([record](record/personal.md#food-conservation-test-history)).
        """
        rows = unpaid_food_series()["rows"]
        first = next(r for r in rows if r["year"] == 2003)
        assert first["preparation"] == pytest.approx(194.3, abs=0.5)
        assert first["provisioning"] == pytest.approx(146.4, abs=0.5)

    def test_2020_is_excluded(self):
        years = [row["year"] for row in unpaid_food_series()["rows"]]
        assert 2020 not in years
        assert years[0] == 2003 and years[-1] == 2025


class TestTheProductionCollapseIsRobust:
    """The module's headline claim, pinned across the whole measured band (2026-08-28).
    `LSMS_CROP_PRODUCTION_HOURS` was once an untagged, unpinned literal that matched
    neither measured route. It is now DERIVED from the kcal chain, so it cannot drift
    from the basket. The tests assert the claim at BOTH ends of the band, because a
    finding that depends on which of two equal routes was picked is not a finding
    ([record](record/personal.md#food-conservation-test-history)).
    """

    def test_the_constant_is_derived_not_restated(self):
        """It must equal the kcal chain exactly — no third number."""
        expected = (BASKET_DIET_KCAL_PER_DAY * DIET_DAYS_PER_YEAR
                    * NUTRITION_HOURS_PER_KCAL)
        assert LSMS_CROP_PRODUCTION_HOURS == pytest.approx(expected, rel=1e-12)

    def test_the_band_brackets_both_measured_routes(self):
        lo, hi = LSMS_CROP_PRODUCTION_BAND
        assert lo < hi
        assert lo == pytest.approx(NUTRITION_CROSSCHECK_HOURS_PER_YEAR, rel=1e-12)
        assert hi == pytest.approx(LSMS_CROP_PRODUCTION_HOURS, rel=1e-12)
        assert (hi - lo) / hi < 0.10, "the two routes should agree within ~8%"

    def test_production_labour_collapses_by_at_least_an_order_of_magnitude(self):
        """The claim: automation eliminated food-PRODUCTION labour. The test asserts an
        order of magnitude, not a level, because the level moves with every constant in
        the chain.
        """
        r = conservation_test()
        prod = next(s for s in r["stages"] if s["stage"] == "production")
        collapse = prod["lsms_hours"] / prod["us_total_hours"]
        assert collapse > 20.0, f"production collapse only {collapse:.1f}x"

    def test_the_collapse_holds_at_both_ends_of_the_band(self):
        """
        THE ROBUSTNESS TEST. If the 62× finding only survived at the kcal route
        it would be an artefact of route choice. At the observed-labour end it
        must still be an order of magnitude.
        """
        r = conservation_test()
        prod = next(s for s in r["stages"] if s["stage"] == "production")
        us = prod["us_total_hours"]
        for route in LSMS_CROP_PRODUCTION_BAND:
            assert route / us > 20.0, (
                f"collapse fails at route {route}: only {route / us:.1f}x"
            )

    def test_processing_and_service_did_not_collapse(self):
        """Processing and service labour did not collapse. They are large in the US, and
        processing is mostly UNPAID: it moved into households, off the ledger.
        """
        r = conservation_test()
        by = {s["stage"]: s for s in r["stages"]}
        prod, proc, serv = by["production"], by["processing"], by["service"]
        assert proc["us_total_hours"] > 10.0 * prod["us_total_hours"]
        assert serv["us_total_hours"] > 10.0 * prod["us_total_hours"]
        assert proc["us_unpaid_hours"] > 0.9 * proc["us_total_hours"], (
            "processing must be overwhelmingly unpaid — that is the relocation"
        )

    def test_the_unmeasured_processing_term_stays_none(self):
        """An unmeasured term is not a zero term. If this ever becomes 0.0 the
        stage comparison silently starts claiming a collapse it cannot show."""
        assert LSMS_PROCESSING_HOURS is None
        r = conservation_test()
        proc = next(s for s in r["stages"] if s["stage"] == "processing")
        assert proc["lsms_hours"] is None
        assert proc["ratio_us_to_lsms"] is None
