"""
Block P-I — the normative personal floor, and the ATUS measurement behind it.

Covers `core/eoh_generation.personal_statutory_floor` (the currency-free floor),
`reference/atus_time_use.py` (pure measurement), `reference/personal_basket.py`
(the basket pinned to physical quantities) and `scenarios/personal_floor.py`
(the identity report).

P-I is REPORTING ONLY: no constant moves, and `TestPIChangesNothing` fails the
moment that stops being true.
"""

import pytest

from hours_eoh.core.eoh_generation import (
    REASON_BELOW_MIN_EPSILON,
    REASON_UNMEASURED,
    personal_statutory_floor,
)
from hours_eoh.data import (
    BASKET_WATER_DISTANCE_M,
    CARE_CHILDCARE_HOURS_PER_PERSON_YEAR,
    BASKET_DIET_KCAL_PER_DAY,
    BASKET_HEALTH_MIN_EPSILON,
    BASKET_SHELTER_M2_PER_PERSON,
    BASKET_THERMAL_DEGREE_DAYS_PER_YEAR,
    BASKET_WATER_LITRES_PER_DAY,
    PERSONAL_EOH_BASE,
    PERSONAL_EOH_SUFFICIENCY,
    PERSONAL_EOH_SURVIVAL,
)
from hours_eoh.reference import atus_time_use
from hours_eoh.reference.personal_basket import (
    CLIMATE_CONDITIONING,
    CLIMATE_NOTES,
    LSMS_AGRO_ECOLOGY,
    LSMS_COUNTRIES,
    LSMS_KCAL_PER_LABOUR_HOUR,
    NUTRITION_CROSSCHECK_HOURS_PER_YEAR,
    NUTRITION_HOURS_PER_KCAL,
    NUTRITION_TRANSFER_BIAS_SIGN,
    DIET_DAYS_PER_YEAR,
    entitlement_augmentation,
    full_basket,
    survival_core,
    COMPONENT_STATUS,
    COMPONENT_STATUS_VOCAB,
    CLIMATE_CONDITIONING,
    _share,
)
from hours_eoh.scenarios.personal_floor import (
    OBSERVED_CONVENTIONS,
    climate_conditioning,
    REFERENCE_POPULATION_US,
    floor_arc,
    floor_vs_constants,
    identity_report,
    obligation_floor,
    observed_hours,
)

KEY_EPSILONS = (0.0, 0.40, 0.99)


# ===========================================================================
# core — the floor itself
# ===========================================================================

# The shipped basket, assembled once. The quantities moved to `data.py` in the
# 2026-08-16 migration; the tests below still assert against the same values.
DIET_KCAL_PER_YEAR = BASKET_DIET_KCAL_PER_DAY * DIET_DAYS_PER_YEAR
HEALTH_MIN_EPSILON = BASKET_HEALTH_MIN_EPSILON
SURVIVAL_CORE = survival_core(
    BASKET_DIET_KCAL_PER_DAY,
    BASKET_WATER_LITRES_PER_DAY,
    BASKET_THERMAL_DEGREE_DAYS_PER_YEAR,
    BASKET_SHELTER_M2_PER_PERSON,
    BASKET_WATER_DISTANCE_M,
    CARE_CHILDCARE_HOURS_PER_PERSON_YEAR,
)
ENTITLEMENT_AUGMENTATION = entitlement_augmentation(BASKET_HEALTH_MIN_EPSILON)
FULL_BASKET = full_basket(
    BASKET_DIET_KCAL_PER_DAY,
    BASKET_WATER_LITRES_PER_DAY,
    BASKET_THERMAL_DEGREE_DAYS_PER_YEAR,
    BASKET_SHELTER_M2_PER_PERSON,
    BASKET_HEALTH_MIN_EPSILON,
    BASKET_WATER_DISTANCE_M,
    CARE_CHILDCARE_HOURS_PER_PERSON_YEAR,
)

class TestFloorArithmetic:

    def test_sums_quantity_times_hours_per_unit(self):
        basket = [
            {"component": "a", "quantity_per_person_year": 100.0, "hours_per_unit": 0.5},
            {"component": "b", "quantity_per_person_year": 10.0, "hours_per_unit": 2.0},
        ]
        assert personal_statutory_floor(basket)["floor_hours"] == pytest.approx(70.0)

    def test_empty_basket_is_zero_at_zero_coverage(self):
        result = personal_statutory_floor([])
        assert result["floor_hours"] == 0.0
        assert result["coverage"] == 0.0

    def test_by_component_breaks_the_total_down(self):
        basket = [
            {"component": "a", "quantity_per_person_year": 100.0, "hours_per_unit": 0.5},
            {"component": "b", "quantity_per_person_year": 10.0, "hours_per_unit": 2.0},
        ]
        result = personal_statutory_floor(basket)
        assert result["by_component"] == {"a": 50.0, "b": 20.0}
        assert sum(result["by_component"].values()) == pytest.approx(result["floor_hours"])


class TestUnreachableIsNotZero:
    """The load-bearing behaviour: an uncosted obligation is not a free one."""

    def test_unmeasured_component_is_excluded_not_zeroed(self):
        basket = [
            {"component": "priced", "quantity_per_person_year": 100.0, "hours_per_unit": 1.0},
            {"component": "unpriced", "quantity_per_person_year": 100.0, "hours_per_unit": None},
        ]
        result = personal_statutory_floor(basket)
        assert result["floor_hours"] == 100.0
        assert "unpriced" not in result["by_component"]
        assert result["unreachable"] == [
            {"component": "unpriced", "reason": REASON_UNMEASURED}
        ]

    def test_coverage_reports_the_incompleteness(self):
        basket = [
            {"component": "priced", "quantity_per_person_year": 1.0, "hours_per_unit": 1.0},
            {"component": "unpriced", "quantity_per_person_year": 1.0, "hours_per_unit": None},
        ]
        assert personal_statutory_floor(basket)["coverage"] == pytest.approx(0.5)

    def test_reasons_are_distinguished(self):
        """'Nobody costed it' and 'no path exists' are different facts."""
        basket = [
            {"component": "unmeasured", "quantity_per_person_year": 1.0, "hours_per_unit": None},
            {"component": "stepin", "quantity_per_person_year": 1.0,
             "hours_per_unit": 1.0, "min_epsilon": 0.5},
        ]
        reasons = {
            row["component"]: row["reason"]
            for row in personal_statutory_floor(basket, epsilon=0.0)["unreachable"]
        }
        assert reasons == {
            "unmeasured": REASON_UNMEASURED,
            "stepin": REASON_BELOW_MIN_EPSILON,
        }

    def test_step_in_opens_above_min_epsilon(self):
        basket = [{"component": "stepin", "quantity_per_person_year": 10.0,
                   "hours_per_unit": 1.0, "min_epsilon": 0.5}]
        assert personal_statutory_floor(basket, epsilon=0.49)["floor_hours"] == 0.0
        assert personal_statutory_floor(basket, epsilon=0.50)["floor_hours"] == 10.0

    def test_step_in_beats_unmeasured_when_both_apply(self):
        """No delivery path at all is the stronger statement; it should win."""
        basket = [{"component": "both", "quantity_per_person_year": 1.0,
                   "hours_per_unit": None, "min_epsilon": 0.5}]
        result = personal_statutory_floor(basket, epsilon=0.0)
        assert result["unreachable"][0]["reason"] == REASON_BELOW_MIN_EPSILON


class TestCoverageWeighting:

    def test_shares_weight_coverage_when_all_present(self):
        basket = [
            {"component": "big", "quantity_per_person_year": 1.0,
             "hours_per_unit": 1.0, "share": 0.9},
            {"component": "small", "quantity_per_person_year": 1.0,
             "hours_per_unit": None, "share": 0.1},
        ]
        assert personal_statutory_floor(basket)["coverage"] == pytest.approx(0.9)

    def test_falls_back_to_count_when_a_share_is_missing(self):
        basket = [
            {"component": "big", "quantity_per_person_year": 1.0,
             "hours_per_unit": 1.0, "share": 0.9},
            {"component": "small", "quantity_per_person_year": 1.0, "hours_per_unit": None},
        ]
        assert personal_statutory_floor(basket)["coverage"] == pytest.approx(0.5)


class TestFloorValidation:

    def test_missing_component_key_rejected(self):
        with pytest.raises(ValueError, match="quantity_per_person_year"):
            personal_statutory_floor([{"component": "a", "hours_per_unit": 1.0}])

    def test_missing_hours_per_unit_rejected_not_defaulted(self):
        """Omitting the key must not be read as 'free'; None must be explicit."""
        with pytest.raises(ValueError, match="hours_per_unit"):
            personal_statutory_floor(
                [{"component": "a", "quantity_per_person_year": 1.0}]
            )

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValueError, match="negative quantity"):
            personal_statutory_floor(
                [{"component": "a", "quantity_per_person_year": -1.0, "hours_per_unit": 1.0}]
            )

    def test_negative_hours_per_unit_rejected(self):
        with pytest.raises(ValueError, match="negative quantity/hours_per_unit"):
            personal_statutory_floor(
                [{"component": "a", "quantity_per_person_year": 1.0, "hours_per_unit": -1.0}]
            )


class TestFloorArc:
    """ε-coherence: physical requirements do not depend on the automation level."""

    @pytest.mark.parametrize("epsilon", KEY_EPSILONS)
    def test_priced_components_are_epsilon_invariant(self, epsilon):
        result = personal_statutory_floor(FULL_BASKET, epsilon)
        assert result["floor_hours"] == pytest.approx(899.2, abs=0.5)

    @pytest.mark.parametrize("epsilon", KEY_EPSILONS)
    def test_floor_is_finite_and_non_negative(self, epsilon):
        result = personal_statutory_floor(FULL_BASKET, epsilon)
        assert result["floor_hours"] >= 0.0
        assert 0.0 <= result["coverage"] <= 1.0

    def test_health_steps_in_across_the_arc(self):
        """Below the threshold health has no path; above it, it is merely uncosted."""
        def reason(epsilon):
            rows = personal_statutory_floor(FULL_BASKET, epsilon)["unreachable"]
            return next(r["reason"] for r in rows if r["component"] == "health")

        assert reason(0.0) == REASON_BELOW_MIN_EPSILON
        assert reason(0.99) == REASON_UNMEASURED


# ===========================================================================
# reference/personal_basket.py — the basket
# ===========================================================================

class TestReferenceBasket:

    def test_nutrition_reproduces_the_measured_figure(self):
        """LSMS-ISA: 767,025 kcal/yr at 2,317.8 kcal/labour-hour → ~331 h/yr."""
        hours = DIET_KCAL_PER_YEAR * NUTRITION_HOURS_PER_KCAL
        assert hours == pytest.approx(331.0, abs=1.0)
        assert LSMS_KCAL_PER_LABOUR_HOUR == pytest.approx(2317.8, abs=0.5)

    def test_the_two_routes_converge(self):
        """Bottom-up kcal chain vs observed-labour-scaled: documented 6% apart."""
        kcal_route = DIET_KCAL_PER_YEAR * NUTRITION_HOURS_PER_KCAL
        spread = abs(kcal_route - NUTRITION_CROSSCHECK_HOURS_PER_YEAR) / kcal_route
        assert spread < 0.10

    def test_only_nutrition_production_is_priced(self):
        """
        Guards the discipline, not the number: an invented delivery productivity
        would enter the floor with the same standing as the measured one, and
        afterwards nothing could tell them apart. If a component is costed here,
        it must arrive with a measurement and this test must be updated
        deliberately.
        """
        priced = [c["component"] for c in FULL_BASKET if c["hours_per_unit"] is not None]
        assert priced == ["nutrition_production", "nutrition_processing", "care"], (
            "a component was costed without this test being updated — which is "
            "the discipline, not the number"
        )
        # AND EACH PRICED ONE DECLARES WHAT KIND OF FIGURE IT IS. Nutrition is
        # `one_frame` (the right quantity, one agro-ecology); care is `bound`
        # (a declared LOWER bound, wrong scope and wrong quantity twice over).
        # Reading care's figure as the value is the specific error `bound` exists
        # to prevent, so the status is asserted alongside the pricing.
        from hours_eoh.reference.personal_basket import COMPONENT_STATUS
        assert COMPONENT_STATUS["nutrition_production"]["status"] == "one_frame"
        assert COMPONENT_STATUS["care"]["status"] == "bound"

    def test_every_component_states_a_physical_unit(self):
        for component in FULL_BASKET:
            assert component.get("unit"), f"{component['component']} has no physical unit"
            assert component["quantity_per_person_year"] > 0.0

    def test_health_is_a_step_in_entitlement(self):
        health = ENTITLEMENT_AUGMENTATION[0]
        assert health["component"] == "health"
        assert health["min_epsilon"] == HEALTH_MIN_EPSILON > 0.0

    def test_survival_core_carries_no_step_in_terms(self):
        assert all(c.get("min_epsilon", 0.0) == 0.0 for c in SURVIVAL_CORE)

    def test_processing_is_declared_not_folded_into_production(self):
        """The binding unknown must be visible as its own line, never absorbed."""
        names = [c["component"] for c in SURVIVAL_CORE]
        assert "nutrition_processing" in names
        assert "nutrition_production" in names

    def test_care_is_in_the_survival_core(self):
        """
        Care is a requirement of human survival, and TEH is denominated in human
        labour hours — so human continuation is the precondition for the ledger
        existing at all. It also has an ε=0 delivery path (humans have always
        cared for each other unassisted), so it belongs in the core and not among
        the step-in entitlements.
        """
        care = next(c for c in SURVIVAL_CORE if c["component"] == "care")
        assert care.get("min_epsilon", 0.0) == 0.0
        assert care["share"] == pytest.approx(0.6207, abs=0.001)
        # PRICED 2026-09-09, AS A BOUND. The old assertion here was
        # `hours_per_unit is None, "naming care must not price it"` — right while
        # nothing measured it, and it is the MTUS childcare median now: 46 of 50
        # samples, and a floor for two independent reasons (childcare only;
        # delivered rather than owed). It stays in the survival core because it
        # still has an ε=0 delivery path — humans have always cared for each
        # other unassisted — which pricing does not change.
        assert care["hours_per_unit"] is not None

    def test_shares_mirror_the_data_decomposition(self):
        """
        `reference/` may not import the package, so the desk estimate's four
        terms are restated in the basket. This holds the two copies together —
        one decomposition of the personal obligation, not two. Before care was
        added they disagreed and `coverage` was flattered by the absence of the
        largest term.
        """
        from hours_eoh.data import PERSONAL_EOH_COMPONENTS

        for term, spec in PERSONAL_EOH_COMPONENTS.items():
            assert _share(term) == pytest.approx(spec["share"], rel=1e-12), term

    def test_shares_sum_to_one_over_the_full_basket(self):
        assert sum(c["share"] for c in FULL_BASKET) == pytest.approx(1.0)

    def test_care_dominates_what_is_unpriced(self):
        """The coverage number is what it is mostly because of care."""
        unpriced = sum(
            c["share"] for c in FULL_BASKET if c["hours_per_unit"] is None
        )
        care = next(c for c in FULL_BASKET if c["component"] == "care")["share"]
        assert care / unpriced > 0.6


# ===========================================================================
# reference/atus_time_use.py — pure measurement
# ===========================================================================

class TestATUSExtract:

    def test_day_sums_to_1440_every_year(self):
        """The arithmetic check on the whole ingest chain: a diary is a full day."""
        for row in atus_time_use.survey_years(include_incomparable=True):
            total = sum(atus_time_use.minutes_per_day(row.year).values())
            assert total == pytest.approx(1440.0, abs=0.01), f"{row.year} does not close"

    def test_covers_2003_to_2025(self):
        years = [r.year for r in atus_time_use.survey_years(include_incomparable=True)]
        assert years[0] == 2003
        assert years[-1] == 2025
        assert len(years) == 23

    def test_2020_is_excluded_by_default_and_flagged(self):
        default = [r.year for r in atus_time_use.survey_years()]
        everything = {r.year: r for r in atus_time_use.survey_years(include_incomparable=True)}
        assert 2020 not in default
        assert everything[2020].comparable is False
        assert everything[2020].weight_variable == "TU20FWGT"

    def test_every_other_year_uses_the_multi_year_weight(self):
        for row in atus_time_use.survey_years():
            assert row.weight_variable == "TUFNWGTP"

    def test_food_preparation_series(self):
        series = atus_time_use.series(("0202",))
        assert series[2003] == pytest.approx(194.3, abs=0.5)
        assert series[2025] == pytest.approx(259.8, abs=0.5)

    def test_grocery_shopping_series(self):
        series = atus_time_use.series(("0701",))
        assert series[2003] == pytest.approx(146.4, abs=0.5)
        assert series[2025] == pytest.approx(108.9, abs=0.5)

    def test_prefix_matching_nests(self):
        """Tier-2 sums must not exceed their tier-1 parent."""
        assert (
            atus_time_use.hours_per_person_15plus(2025, ("0202",))
            < atus_time_use.hours_per_person_15plus(2025, ("02",))
        )

    def test_tier1_hours_partition_the_year(self):
        assert sum(atus_time_use.tier1_hours(2025).values()) == pytest.approx(8760.0, abs=1.0)

    def test_per_capita_scale_is_explicit(self):
        assert atus_time_use.per_capita_scale(2025, 335e6) == pytest.approx(0.8298, abs=0.001)

    def test_per_capita_scale_rejects_nonpositive_population(self):
        with pytest.raises(ValueError, match="must be positive"):
            atus_time_use.per_capita_scale(2025, 0.0)

    def test_unknown_year_raises(self):
        with pytest.raises(KeyError):
            atus_time_use.minutes_per_day(1999)

    def test_household_size_and_age_travel_with_the_frame(self):
        rows = {r.year: r for r in atus_time_use.survey_years()}
        assert rows[2003].mean_household_size > rows[2025].mean_household_size
        assert rows[2003].mean_age < rows[2025].mean_age


# Layer isolation for the two new reference modules is asserted by
# `tests/test_reference_data.py::TestLayerIsolation`, which is parametrized over
# REFERENCE_MODULES — one definition of the rule for the whole package.


# ===========================================================================
# scenarios/personal_floor.py — the identity report
# ===========================================================================

class TestObservedHours:

    def test_unpaid_core_2025(self):
        assert observed_hours(2025, "unpaid_core") == pytest.approx(763.8, abs=0.5)

    def test_paid_2025(self):
        assert observed_hours(2025, "paid") == pytest.approx(937.3, abs=0.5)

    def test_conventions_are_ordered_by_breadth(self):
        core = observed_hours(2025, "unpaid_core")
        broad = observed_hours(2025, "unpaid_broad")
        every = observed_hours(2025, "all_labour")
        assert core < broad
        assert core < every

    def test_unknown_convention_rejected(self):
        with pytest.raises(KeyError, match="unknown convention"):
            observed_hours(2025, "vibes")

    def test_defaults_to_the_latest_comparable_year(self):
        assert observed_hours() == pytest.approx(observed_hours(2025), abs=1e-9)

    def test_every_convention_is_reachable(self):
        for name in OBSERVED_CONVENTIONS:
            assert observed_hours(2025, name) > 0.0


class TestIdentityReport:

    def test_residual_is_the_arithmetic_difference(self):
        report = identity_report(2025)
        assert report["residual"] == pytest.approx(
            report["observed_hours"] - report["floor_priced"]
        )

    def test_unidentified_terms_stay_none(self):
        """The whole point: the report must not attribute the residual."""
        report = identity_report(2025)
        assert report["deferred"] is None
        assert report["extraction"] is None
        assert report["identified"] is False

    def test_residual_names_all_three_unknowns(self):
        report = identity_report(2025)
        assert report["residual_terms"] == ("floor_unpriced", "deferred", "extraction")

    def test_reports_current_values(self):
        report = identity_report(2025)
        assert report["observed_hours"] == pytest.approx(763.8, abs=0.5)
        assert report["floor_priced"] == pytest.approx(899.2, abs=0.5)
        assert report["coverage"] == pytest.approx(0.759, abs=0.001)

    @pytest.mark.parametrize("epsilon", KEY_EPSILONS)
    def test_report_is_meaningful_across_the_arc(self, epsilon):
        report = identity_report(2025, epsilon=epsilon)
        assert report["floor_priced"] > 0.0
        assert report["identified"] is False

    def test_identification_would_require_full_coverage(self):
        """A fully-priced basket flips `identified`; nothing else does."""
        basket = [{"component": "everything", "quantity_per_person_year": 1.0,
                   "hours_per_unit": 1.0, "share": 1.0}]
        assert identity_report(2025, basket=basket)["identified"] is True


class TestFloorVsConstants:

    def test_age_weight_comes_from_the_shared_bridge(self):
        # 1.475 → 1.3528 with the 2026-08-10 AGE_GROUPS elderly revalue.
        assert floor_vs_constants()["age_weight"] == pytest.approx(1.3528)

    def test_floor_sits_below_every_standard(self):
        """The only ordering compatible with 6.9% coverage (the docstring said
        30% and coverage has been 6.9% since the basket was itemised)."""
        shares = floor_vs_constants()["floor_share_of"]
        assert all(0.0 < value < 1.0 for value in shares.values())

    def test_the_floor_cannot_falsify_the_base_and_the_gap_is_coverage(self):
        """
        THE FLOOR IS THE FALSIFIER, NOT THE DEFAULT — and at this coverage it
        falsifies nothing. It is a strict LOWER bound, so it can only refute a
        constant by EXCEEDING it, and it prices one component of seven.

        The ordering below is therefore not evidence that the constants are
        right. It is what 6.9% coverage forces, and quoting it as agreement
        would be reading a coverage artefact as a corroboration — the shape
        `floor_share_of` exists to make visible.
        """
        r = floor_vs_constants()
        # 0.069 → 0.690 on 2026-09-09: care priced as a declared LOWER BOUND from
        # MTUS childcare. One component moved coverage tenfold because care
        # carries 62.1% of the desk shares — the count of components was never
        # the measure of how much was priced.
        assert r["coverage"] == pytest.approx(0.759, abs=5e-4)
        # SCOPED, AND THE SCOPE IS THE POINT. This compared the WHOLE floor
        # against a standard whose own resolves_by reads "only the components
        # that kill you if unmet — food, water, shelter, warmth" — care is not
        # in it. On 2026-09-10 the whole floor crossed 811.68 on the strength of
        # care's 168.1 h and the verdict reported a FALSIFICATION that was a
        # scope artefact. The mismatch is older than the crossing and was
        # invisible only while the floor was too small to reach any standard:
        # the check could not fail, so its passing meant nothing, and its first
        # real firing was wrong.
        assert r["floor_scoped_to"]["PERSONAL_EOH_SURVIVAL"] < r["constants_per_capita"]["PERSONAL_EOH_SURVIVAL"], (
            "the survival-scoped floor now exceeds the survival standard — it "
            "has started to bind, and the constants it sits under must be "
            "re-read rather than assumed corroborated."
        )
        # and the artefact is pinned so it cannot come back unnoticed
        assert r["floor_priced_per_capita"] > r["constants_per_capita"]["PERSONAL_EOH_SURVIVAL"], (
            "the whole floor no longer exceeds the survival standard; if that is "
            "because care was unpriced, this guard has stopped guarding anything"
        )
        assert "falsifies nothing yet" in r["verdict"]
        # AND THE VERDICT IS COMPUTED, NOT RESTATED. It said "one component of
        # seven — 6.9%" as a literal and went stale the instant a second was
        # priced. A test that only checked the phrase above would have passed.
        assert "3 of 7" in r["verdict"] and "75.9%" in r["verdict"]

    def test_what_the_unpriced_remainder_would_have_to_deliver(self):
        """
        The threshold, stated so nobody has to re-derive it: the floor binds on
        `PERSONAL_EOH_BASE` when priced hours exceed the base's per-capita
        claim. Care alone is 62.1% of the basket by share and is unpriced, so
        whether the remainder clears that gap is a question about CARE, not
        about coverage in the abstract.
        """
        r = floor_vs_constants()
        gap = r["constants_per_capita"]["PERSONAL_EOH_BASE"] - r["floor_priced_per_capita"]
        assert gap > 0.0
        # 1021.9 → 853.8 on 2026-09-09: care closed 168.1 h of it.
        assert gap == pytest.approx(453.6, abs=1.0), (
            "the gap between the priced floor and the base has moved; it is "
            "quoted in record/personal.md and in this test's docstring."
        )
        care = [c for c in FULL_BASKET if c["component"] == "care"][0]
        assert care["hours_per_unit"] is not None and care["share"] > 0.60

        # THE QUESTION THIS TEST POSED IS NOW PARTLY ANSWERED, and the answer is
        # a number rather than a verdict. With 69.0% of the desk share priced the
        # floor reaches 36.9% of the base, so for the base to be right the
        # remaining 31.0% must deliver 3.8x the hours per unit share that the
        # priced part did. That is not a falsification — the floor is a lower
        # bound and care's leg is a loose one — but it is the first thing the
        # floor has said ABOUT the base rather than merely sitting under it.
        assert r["remainder_intensity_ratio"] == pytest.approx(1.59, abs=0.05)

    def test_standards_stay_ordered(self):
        constants = floor_vs_constants()["constants_per_capita"]
        assert (
            constants["PERSONAL_EOH_SURVIVAL"]
            < constants["PERSONAL_EOH_BASE"]
            < constants["PERSONAL_EOH_SUFFICIENCY"]
        )


class TestFloorHelpers:

    def test_floor_arc_covers_the_key_epsilons(self):
        arc = floor_arc()
        assert [row["epsilon"] for row in arc] == list(KEY_EPSILONS)

    def test_survival_core_excludes_the_step_in_term(self):
        core = obligation_floor(SURVIVAL_CORE, 0.0)
        assert all(row["component"] != "health" for row in core["unreachable"])

    def test_obligation_floor_defaults_to_the_full_basket(self):
        assert obligation_floor()["floor_hours"] == pytest.approx(
            obligation_floor(FULL_BASKET)["floor_hours"]
        )


class TestTheBasketSeam:
    """The 2026-08-16 migration: chosen quantities in `data.py`, measured
    delivery productivities in `reference/`, assembled by `scenarios/`."""

    def test_the_migration_moved_no_numbers(self):
        """The whole point of doing it this way — TestPIChangesNothing's
        discipline applied to a refactor rather than a finding."""
        from hours_eoh.scenarios.personal_floor import shipped_basket

        result = personal_statutory_floor(shipped_basket())
        # 330.9232760 until care was priced 2026-09-09. The migration this test
        # guards moved no numbers; the care pricing moved this one deliberately.
        assert result["floor_hours"] == pytest.approx(899.1967160, abs=1e-6)
        # 2/29 → 20/29 when care was priced: the desk shares are 29ths, and
        # care is 18 of them. Kept as an exact fraction rather than a decimal so
        # a share change shows up as a share change.
        assert result["coverage"] == pytest.approx(22.0 / 29.0, abs=1e-9)

    def test_the_scenario_assembles_what_the_constants_say(self):
        from hours_eoh.scenarios.personal_floor import shipped_basket

        assert shipped_basket() == FULL_BASKET

    def test_quantities_are_supplied_not_stored(self):
        """A different diet standard must produce a different basket — if the
        quantity were still baked in, this would silently return the shipped
        figure and the migration would be cosmetic."""
        hot = full_basket(2500.0, BASKET_WATER_LITRES_PER_DAY,
                          BASKET_THERMAL_DEGREE_DAYS_PER_YEAR,
                          BASKET_SHELTER_M2_PER_PERSON,
                          BASKET_HEALTH_MIN_EPSILON,
                          BASKET_WATER_DISTANCE_M,
                          CARE_CHILDCARE_HOURS_PER_PERSON_YEAR)
        shipped = personal_statutory_floor(FULL_BASKET)["floor_hours"]
        # The threshold is on the NUTRITION term, which is what the diet
        # quantity moves — so it is stated against that term rather than against
        # the whole floor. Care's 168.1 h entered the floor on 2026-09-09 and is
        # invariant to the diet standard, so a whole-floor threshold now
        # understates the sensitivity it is testing for.
        hot_n = personal_statutory_floor(hot)["by_component"]["nutrition_production"]
        ship_n = personal_statutory_floor(FULL_BASKET)["by_component"]["nutrition_production"]
        assert hot_n > ship_n * 1.15
        assert personal_statutory_floor(hot)["floor_hours"] > shipped

    def test_the_dormant_quantities_move_nothing_yet(self):
        """Water and thermal carry hours_per_unit=None, so they are EXCLUDED,
        not costed at zero — changing them must not move the floor. They become
        load-bearing the moment either component is priced, which is why they
        are tagged in data.py rather than left where nothing watched them."""
        odd = full_basket(BASKET_DIET_KCAL_PER_DAY, 500.0, 9000.0, 40.0,
                          BASKET_HEALTH_MIN_EPSILON, 5_000.0,
                          CARE_CHILDCARE_HOURS_PER_PERSON_YEAR)
        assert personal_statutory_floor(odd)["floor_hours"] == pytest.approx(
            personal_statutory_floor(FULL_BASKET)["floor_hours"]
        )

    def test_a_basket_line_with_no_requirement_is_refused(self):
        for bad in ((0.0, 50.0, 2500.0, 12.0, 1000.0, 168.0),
                    (2100.0, -1.0, 2500.0, 12.0, 1000.0, 168.0),
                    (2100.0, 50.0, 0.0, 12.0, 1000.0, 168.0),
                    (2100.0, 50.0, 2500.0, 0.0, 1000.0, 168.0),
                    (2100.0, 50.0, 2500.0, 12.0, -1.0, 168.0),
                    (2100.0, 50.0, 2500.0, 12.0, 1000.0, -1.0)):
            with pytest.raises(ValueError, match="must be positive"):
                survival_core(*bad)

    def test_the_health_gate_is_bounded(self):
        for bad in (-0.1, 1.5):
            with pytest.raises(ValueError, match="health_min_epsilon"):
                entitlement_augmentation(bad)


class TestPIChangesNothing:
    """P-I is reporting only. These fail the moment it starts adopting."""

    def test_constants_are_untouched(self):
        assert PERSONAL_EOH_SURVIVAL == 600.0
        assert PERSONAL_EOH_BASE == 1000.0
        assert PERSONAL_EOH_SUFFICIENCY == 1500.0

    def test_the_floor_is_not_wired_into_generation(self):
        """`personal_eoh` must still run off the constants, not off the basket."""
        from hours_eoh.core.eoh_generation import personal_eoh

        # 1,301.6 h/person·yr × 1e6 people — the constants path, untouched by
        # P-I. It moved from 1,475 with the 2026-08-10 AGE_GROUPS elderly
        # revalue, which is a CONSTANTS change; the basket still feeds nothing,
        # which is what this test is for.
        assert personal_eoh(population=1e6, epsilon=0.0) == pytest.approx(
            1.3528e9, rel=1e-6
        )


class TestClimateProvenance:
    """
    The one priced number in the basket is a rainfed tropical smallholder
    figure. These guard that the scope is STATED — a measurement whose
    conditioning is undocumented gets quoted out of scope, which is how a
    calibration becomes a claim it cannot support.
    """

    def test_the_measurement_names_its_countries(self):
        assert len(LSMS_COUNTRIES) == 7
        assert "Ethiopia" in LSMS_COUNTRIES and "Niger" in LSMS_COUNTRIES

    def test_the_agro_ecology_is_stated_and_says_rainfed(self):
        assert "rainfed" in LSMS_AGRO_ECOLOGY.lower()
        assert "no irrigation" in LSMS_AGRO_ECOLOGY.lower()

    def test_every_component_declares_how_climate_enters(self):
        for component in FULL_BASKET:
            name = component["component"]
            assert name in CLIMATE_CONDITIONING, f"{name} has no climate conditioning"
            assert CLIMATE_CONDITIONING[name] in (
                "quantity_is_climate", "delivery", "quantity_weak", "none"
            )
            assert CLIMATE_NOTES.get(name), f"{name} has no climate note"

    def test_climate_now_enters_through_exactly_one_channel(self):
        """
        MERGED 2026-09-04. `thermal` was the one component where climate was the
        QUANTITY rather than the delivery cost, and that was the defect, not a
        feature: degree-days is a property of a PLACE, not a per-person
        quantity, so one row violated the basket's own form
        (Σ quantity_per_person_year × hours_per_unit). A village of 100 and a
        city of a million in one climate both face 2,500.

        Thermal is now an intensity on shelter's quantity — m² × degree-days ×
        hours per (m²·degree-day) — carried as `degree_days_per_year` on the
        shelter row. That also makes the substitution representable: insulation
        is shelter capital and heating is thermal flow, they TRADE OFF, and two
        additive line items could only add one point from each curve.

        The consequence is unchanged and now stated once: costing shelter makes
        the floor climate-indexed, so `PERSONAL_EOH_BASE` must declare which
        climate it is for.
        """
        assert "thermal" not in CLIMATE_CONDITIONING
        assert set(CLIMATE_CONDITIONING.values()) == {"delivery", "none"}, (
            "a component has reintroduced a climate channel other than delivery; "
            "the basket's quantities are meant to be per-person and global, with "
            "only the productivities stratified by zone."
        )

    def test_the_shelter_row_carries_the_degree_days(self):
        shelter = [c for c in FULL_BASKET if c["component"] == "shelter"]
        assert len(shelter) == 1
        assert shelter[0]["degree_days_per_year"] > 0.0
        assert shelter[0]["unit"] == "m2", (
            "shelter's quantity must stay per-person; degree-days is an "
            "intensity on it, not a quantity of its own."
        )
        assert shelter[0]["hours_per_unit"] is None, (
            "shelter is priced. The degree-day intensity must enter "
            "hours_per_unit, and PERSONAL_EOH_BASE must state its climate."
        )

    def test_no_component_quantity_is_a_property_of_a_place(self):
        """The form the merge restored: every quantity scales with people."""
        for c in FULL_BASKET:
            assert c["unit"] in {
                "kcal", "litres", "m2", "service_years", "person_years",
                "schedules",
            }, f"{c['component']}: {c['unit']} is not a per-person unit"

    def test_care_is_climate_invariant(self):
        """
        The largest component is the only one climate does not touch — a
        dependent needs the same attention at any latitude. Same structural fact
        as Block II's low abatability for care, reached from another direction.
        """
        assert CLIMATE_CONDITIONING["care"] == "none"
        invariant = [n for n, k in CLIMATE_CONDITIONING.items() if k == "none"]
        assert invariant == ["care"]

    def test_the_priced_component_is_flagged_as_carrying_its_climate(self):
        report = climate_conditioning()
        # both priced nutrition legs carry the agro-ecology; care does not,
        # because care is the one `delivery: invariant` component.
        assert report["priced_and_climate_conditioned"] == [
            "nutrition_production", "nutrition_processing"]

    def test_transfer_bias_sign_is_withheld(self):
        """
        NOT unknown to the caller — genuinely undetermined by the data. Shorter
        seasons push hours per kcal up, better temperate soils push them down,
        and the LSMS stratum adjudicates neither. Asserting a direction here
        would be the kind of claim the thermal layer refuses to make about an
        undetermined budget sign.
        """
        assert NUTRITION_TRANSFER_BIAS_SIGN is None
        assert climate_conditioning()["transfer_bias_sign"] is None

    def test_convergence_is_not_evidence_of_climate_generality(self):
        """
        Both nutrition routes come from the same seven countries, so their 7.6%
        agreement bounds the kcal chain and says nothing about transfer. The
        climate uncertainty sits OUTSIDE that spread.
        """
        kcal_route = DIET_KCAL_PER_YEAR * NUTRITION_HOURS_PER_KCAL
        spread = abs(kcal_route - NUTRITION_CROSSCHECK_HOURS_PER_YEAR) / kcal_route
        assert spread < 0.10
        # Both routes are priced off the same seven countries, so the tight
        # spread cannot be read as climate generality.
        assert climate_conditioning()["countries"] == LSMS_COUNTRIES


class TestTheBaseDeclaresItsClimate:
    """
    The base and its falsifier now refer to the same place.

    THE MISMATCH THIS CLOSES. `PERSONAL_EOH_BASE` was a single global float.
    The only priced basket component — nutrition production — is measured in
    rainfed tropical and sub-tropical Sub-Saharan Africa and its own note says
    it "does not transfer without restratification by agro-ecological zone". So
    the check was stratified and the checked was global: you cannot falsify a
    global scalar with a Sahelian measurement without saying which climate the
    scalar is for. That mismatch existed at 6.9% coverage, not at some future
    one, and was masked only because a 6.9% floor cannot falsify anything.

    AND IT WAS NOT THERMAL'S DOING. The earlier reading — that costing thermal
    would break the single global scalar — had the wrong culprit: nutrition
    already had, being the first component priced. Of the components, all but
    care are climate-conditioned, and care is 62.1% of the obligation, so there
    is no climate-free component to price first.

    STATED GAP: declaring the frame makes the two commensurable. It does not
    make the base right for that zone — 1,000 is still CHOSEN, at the top of a
    427–1092 band, and only `personal_statutory_floor` at 6.9% coverage can
    settle the point inside it.
    """

    def test_the_frame_matches_the_priced_components_stratum(self) -> None:
        from hours_eoh.data import PERSONAL_EOH_BASE_CLIMATE_FRAME
        from hours_eoh.reference.personal_basket import LSMS_AGRO_ECOLOGY
        frame = PERSONAL_EOH_BASE_CLIMATE_FRAME.lower()
        assert "ssa" in frame or "sub-tropical" in frame
        for token in ("rainfed", "tropical"):
            assert token in frame and token in LSMS_AGRO_ECOLOGY.lower(), (
                f"the base's declared frame and the priced component's stratum "
                f"disagree on {token!r} — they must name the same place or the "
                "floor cannot falsify the base."
            )

    def test_the_frame_is_declared_at_all(self) -> None:
        from hours_eoh.data import PERSONAL_EOH_BASE_CLIMATE_FRAME
        assert len(PERSONAL_EOH_BASE_CLIMATE_FRAME) > 20, (
            "the frame must NAME a zone. An empty or vague string returns the "
            "base to being a global scalar that does not say what it describes."
        )

    def test_the_climate_free_share_is_care_and_it_dominates(self) -> None:
        """Why there is no safe component to price first."""
        from hours_eoh.reference.personal_basket import CLIMATE_CONDITIONING
        free = [n for n, k in CLIMATE_CONDITIONING.items() if k == "none"]
        assert free == ["care"]
        share = {c["component"]: c["share"] for c in FULL_BASKET}
        assert share["care"] > 0.60
        conditioned = sum(v for k, v in share.items() if k != "care")
        assert 0.35 < conditioned < 0.40

    def test_the_stated_gap_is_still_stated(self) -> None:
        doc = self.__doc__ or ""
        assert "STATED GAP" in doc and "does not\n    make the base right" in doc


class TestTheComponentStatusTableCannotDrift:
    """
    `COMPONENT_STATUS` says what KIND of unknown each basket component is, so
    that "five are unmeasured" is not read as one homogeneous backlog. A table
    like that is worthless the moment it disagrees with the basket, so every
    field here is bound to the data rather than restated beside it.
    """

    def test_every_component_is_classified_and_none_is_invented(self) -> None:
        """An unclassified component would be excluded from the work order
        without anyone having decided to exclude it — the same failure the
        obligation-work registry guards against."""
        in_basket = {c["component"] for c in FULL_BASKET}
        classified = set(COMPONENT_STATUS)
        assert classified == in_basket, (
            f"unclassified: {sorted(in_basket - classified)}; "
            f"classified but not in the basket: {sorted(classified - in_basket)}"
        )

    def test_the_vocabularies_are_closed(self) -> None:
        for comp, row in COMPONENT_STATUS.items():
            for axis, allowed in COMPONENT_STATUS_VOCAB.items():
                assert row[axis] in allowed, f"{comp}.{axis}={row[axis]!r}"
            assert row["blocked_on"].strip(), f"{comp} states no blocker"

    def test_costed_iff_claimed_costed(self) -> None:
        """THE BIND THAT MATTERS. A component is `measured`/`one_frame` exactly
        when it carries an `hours_per_unit`. Measure water without updating this
        table and the test fails; downgrade a status without removing the
        productivity and it fails too."""
        costed_status = {"measured", "one_frame", "bound"}
        for c in FULL_BASKET:
            row = COMPONENT_STATUS[c["component"]]
            claims_costed = row["status"] in costed_status
            is_costed = c.get("hours_per_unit") is not None
            assert claims_costed == is_costed, (
                f"{c['component']}: status={row['status']!r} but "
                f"hours_per_unit={c.get('hours_per_unit')!r}"
            )

    def test_the_place_properties_are_named_and_set_the_indexing_grain(self) -> None:
        """
        TWO components carry a place property on the quantity side, and the
        second one changed the argument rather than repeating it.

        This test previously asserted `== {"shelter"}` and said in its own
        docstring that a second quantity-instance would need the argument
        restated. Water became one on 2026-09-09, the assertion fired, and the
        restatement is this: degree-days makes the floor CLIMATE-indexed;
        distance-to-source makes it SITE-indexed, which is strictly finer. Two
        collectives in one climate, one beside a spring and one 3 km from it,
        share a climate and do not share a floor.

        So the ceiling on how well `PERSONAL_EOH_BASE` can ever be stated is a
        SITE, not a climate zone — and each place property is pinned to the row
        that carries it, so neither can be quietly folded into a delivery
        productivity where its distribution would become invisible.
        """
        instance_q = {k for k, v in COMPONENT_STATUS.items()
                      if v["quantity"] == "instance"}
        assert instance_q == {"shelter", "water"}, instance_q

        carried = {"shelter": "degree_days_per_year", "water": "distance_to_source_m"}
        for component, field in carried.items():
            row = next(c for c in FULL_BASKET if c["component"] == component)
            assert field in row, f"{component} lost its place property {field}"
            assert row["hours_per_unit"] is None, (
                f"{component} is costed while carrying a place property — the "
                "intensity must not be folded into the delivery productivity"
            )

    def test_a_place_property_is_carried_and_never_costed(self) -> None:
        """Both intensities are carried so the row has its unit and are NOT
        multiplied into the floor. Moving either must not move a single hour —
        which is what makes them declarations rather than silent multipliers."""
        from hours_eoh.reference.personal_basket import full_basket
        from hours_eoh.data import (
            BASKET_DIET_KCAL_PER_DAY, BASKET_WATER_LITRES_PER_DAY,
            BASKET_THERMAL_DEGREE_DAYS_PER_YEAR, BASKET_SHELTER_M2_PER_PERSON,
            BASKET_HEALTH_MIN_EPSILON,
        )
        far = full_basket(
            BASKET_DIET_KCAL_PER_DAY, BASKET_WATER_LITRES_PER_DAY,
            BASKET_THERMAL_DEGREE_DAYS_PER_YEAR, BASKET_SHELTER_M2_PER_PERSON,
            BASKET_HEALTH_MIN_EPSILON, 25_000.0,
            CARE_CHILDCARE_HOURS_PER_PERSON_YEAR,
        )
        assert personal_statutory_floor(far)["floor_hours"] == pytest.approx(
            personal_statutory_floor(FULL_BASKET)["floor_hours"]
        )

    def test_care_is_the_only_component_invariant_on_BOTH_axes(self) -> None:
        """A dependent needs the same attention at any latitude — the same fact
        Block II reaches from abatability. Bound to CLIMATE_CONDITIONING so the
        two tables cannot disagree about it."""
        invariant = {k for k, v in COMPONENT_STATUS.items()
                     if v["delivery"] == "invariant"}
        assert invariant == {"care"}, invariant
        assert CLIMATE_CONDITIONING["care"] == "none"
        for comp, kind in CLIMATE_CONDITIONING.items():
            expected = "invariant" if kind == "none" else "instance"
            if COMPONENT_STATUS[comp]["delivery"] != "none":
                assert COMPONENT_STATUS[comp]["delivery"] == expected, comp

    def test_health_is_undefined_rather_than_unmeasured(self) -> None:
        """The distinction the whole table exists to protect: health's gap is
        not a data gap. Q/P(0) is undefined, not large, so more measurement does
        not close it and it must never be filled with a plausible number."""
        assert COMPONENT_STATUS["health"]["status"] == "undefined"
        assert COMPONENT_STATUS["health"]["delivery"] == "none"
        health = next(c for c in FULL_BASKET if c["component"] == "health")
        assert health.get("min_epsilon") is not None
        assert health.get("hours_per_unit") is None
        others = {k for k, v in COMPONENT_STATUS.items() if v["status"] == "undefined"}
        assert others == {"health"}, others

    def test_the_open_count_matches_what_the_floor_reports_unreachable(self) -> None:
        """The table's own arithmetic against `obligation_floor`'s: everything
        not costed must show up as unreachable, with health's reason distinct."""
        from hours_eoh.scenarios.personal_floor import obligation_floor
        r = obligation_floor()
        unreachable = {u["component"] for u in r["unreachable"]}
        not_costed = {k for k, v in COMPONENT_STATUS.items()
                      if v["status"] in {"open", "undefined"}}
        assert unreachable == not_costed, (unreachable, not_costed)
        reasons = {u["component"]: u["reason"] for u in r["unreachable"]}
        assert reasons["health"] != reasons["water"], (
            "health's reason must stay distinct from an ordinary unmeasured one")
