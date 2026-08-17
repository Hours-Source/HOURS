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
)
ENTITLEMENT_AUGMENTATION = entitlement_augmentation(BASKET_HEALTH_MIN_EPSILON)
FULL_BASKET = full_basket(
    BASKET_DIET_KCAL_PER_DAY,
    BASKET_WATER_LITRES_PER_DAY,
    BASKET_THERMAL_DEGREE_DAYS_PER_YEAR,
    BASKET_SHELTER_M2_PER_PERSON,
    BASKET_HEALTH_MIN_EPSILON,
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
        assert result["floor_hours"] == pytest.approx(330.9, abs=0.5)

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
        assert priced == ["nutrition_production"]

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
        assert care["hours_per_unit"] is None, "naming care must not price it"
        assert care.get("min_epsilon", 0.0) == 0.0
        assert care["share"] == pytest.approx(0.6207, abs=0.001)

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
        assert report["floor_priced"] == pytest.approx(330.9, abs=0.5)
        assert report["coverage"] == pytest.approx(0.069, abs=0.001)

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
        # 1.475 → 1.3016 with the 2026-08-10 AGE_GROUPS elderly revalue.
        assert floor_vs_constants()["age_weight"] == pytest.approx(1.3016)

    def test_floor_sits_below_every_standard(self):
        """The only ordering compatible with 30% coverage."""
        shares = floor_vs_constants()["floor_share_of"]
        assert all(0.0 < value < 1.0 for value in shares.values())

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
        assert result["floor_hours"] == pytest.approx(330.9232760, abs=1e-6)
        assert result["coverage"] == pytest.approx(2.0 / 29.0, abs=1e-9)

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
                          BASKET_HEALTH_MIN_EPSILON)
        shipped = personal_statutory_floor(FULL_BASKET)["floor_hours"]
        assert personal_statutory_floor(hot)["floor_hours"] > shipped * 1.15

    def test_the_dormant_quantities_move_nothing_yet(self):
        """Water and thermal carry hours_per_unit=None, so they are EXCLUDED,
        not costed at zero — changing them must not move the floor. They become
        load-bearing the moment either component is priced, which is why they
        are tagged in data.py rather than left where nothing watched them."""
        odd = full_basket(BASKET_DIET_KCAL_PER_DAY, 500.0, 9000.0, 40.0,
                          BASKET_HEALTH_MIN_EPSILON)
        assert personal_statutory_floor(odd)["floor_hours"] == pytest.approx(
            personal_statutory_floor(FULL_BASKET)["floor_hours"]
        )

    def test_a_basket_line_with_no_requirement_is_refused(self):
        for bad in ((0.0, 50.0, 2500.0, 12.0), (2100.0, -1.0, 2500.0, 12.0),
                    (2100.0, 50.0, 0.0, 12.0), (2100.0, 50.0, 2500.0, 0.0)):
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
            1.3016e9, rel=1e-6
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

    def test_thermal_is_the_one_place_climate_is_the_quantity(self):
        quantity_kind = [
            name for name, kind in CLIMATE_CONDITIONING.items()
            if kind == "quantity_is_climate"
        ]
        assert quantity_kind == ["thermal"]

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
        assert report["priced_and_climate_conditioned"] == ["nutrition_production"]

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
