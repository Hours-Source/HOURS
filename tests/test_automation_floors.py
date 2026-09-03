"""
The automation-floor measurement, and the limits it must keep stating.

WHY THIS EXISTS. `PERSONAL_AUTOMATION_FLOORS` carries one entry, and that entry
is a charter decision rather than a measurement. This module asked whether ATUS
can supply the other three and concluded that it cannot. These tests pin the
measurement, the asymmetry that makes it readable in one direction only, and —
most importantly — that the module never starts emitting a floor value.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh import data
from hours_eoh.reference import atus_time_use as atus
from hours_eoh.reference import mtus_time_use as mtus
from hours_eoh.scenarios import automation_floors as af
from hours_eoh.scenarios.component_shares import COMPONENT_CODES


class TestItProducesNoFloorValue:
    """The whole point: a measurement that cannot pin a level must not ship one."""

    def test_report_says_so_explicitly(self) -> None:
        assert af.report()["produces_a_floor_value"] is False

    def test_no_returned_value_could_be_read_as_a_floor(self) -> None:
        """
        A floor is a fraction in [0, 1]. Nothing this module returns under a key
        naming a floor may be a bare number — if one ever appears, someone has
        started calibrating against a window this module says cannot carry it.
        """
        rep = af.report()
        for component, row in rep["components"].items():
            for key, value in row.items():
                if "floor" in key:
                    assert isinstance(value, (bool, str)), (
                        f"{component}.{key} is {value!r} — a floor-named key "
                        "carrying a number is this module calibrating a value "
                        "it has just argued the data cannot support"
                    )

    def test_the_unfloored_components_are_still_unfloored(self) -> None:
        for component in af.UNFLOORED:
            assert component not in data.PERSONAL_AUTOMATION_FLOORS
        assert set(data.PERSONAL_AUTOMATION_FLOORS) == {"care"}


class TestTheAsymmetryIsLoadBearing:
    """
    Automation and marketisation both push observed unpaid hours DOWN and cannot
    be separated here, so a rise is evidence and a fall is not. Inverting that
    would turn every marketised component into a false automation finding.
    """

    def test_a_component_that_rose_supports_a_nonzero_floor(self) -> None:
        rows = af.floor_direction()
        assert rows["nutrition"]["supports_nonzero_floor"] is True
        assert rows["nutrition"]["change"] > 0.0

    def test_a_component_that_fell_supports_nothing(self) -> None:
        shelter = af.floor_direction()["shelter"]
        assert shelter["change"] < 0.0
        assert shelter["supports_nonzero_floor"] is False
        assert "not separable" in shelter["reading"]

    def test_support_follows_the_direction_and_never_the_magnitude(self) -> None:
        for row in af.floor_direction().values():
            assert row["supports_nonzero_floor"] is (row["change"] > 0.0)


class TestTheSaturationControl:
    """Household shrinkage lowers per-person hours with no automation in it."""

    def test_the_control_is_measured_not_assumed(self) -> None:
        sat = af.saturation_evidence()
        rows = {r.year: r for r in atus.survey_years() if r.comparable}
        first, last = sat["window"]
        expected = (
            rows[last].mean_household_size - rows[first].mean_household_size
        ) / rows[first].mean_household_size
        assert sat["household_size_change"] == pytest.approx(expected, rel=1e-12)
        assert sat["household_size_change"] < 0.0

    def test_the_dishwasher_probe_rose_which_no_automation_reading_explains(self) -> None:
        probe = af.saturation_evidence()["probes"]["020203"]
        assert probe["change"] > 0.0
        assert probe["beyond_household_shrinkage"] is False

    def test_a_probe_clears_the_bar_only_by_falling_faster_than_households(self) -> None:
        sat = af.saturation_evidence()
        hh = sat["household_size_change"]
        for probe in sat["probes"].values():
            assert probe["beyond_household_shrinkage"] is (probe["change"] < hh)

    def test_the_control_does_work_that_a_bare_sign_test_would_not(self) -> None:
        """
        THE MUTATION THAT DID NOT BITE. Replacing the household control with
        `change < 0.0` passes every test written against the shipped probes,
        because no probe falls between the household-size change and zero. The
        rule is therefore exercised at the boundary directly, where the two
        candidate rules disagree.
        """
        hh = af.saturation_evidence()["household_size_change"]
        assert hh < 0.0
        midpoint = hh / 2.0                      # a fall, but smaller than the demographic one
        assert midpoint < 0.0, "must be a decline for the test to mean anything"
        assert af.beyond_shrinkage(midpoint, hh) is False, (
            "a decline smaller than household shrinkage carries no automation "
            "signal; a bare sign test would wrongly call it one"
        )
        assert af.beyond_shrinkage(hh * 2.0, hh) is True
        assert af.beyond_shrinkage(0.05, hh) is False

    def test_the_verdict_reports_what_was_measured_not_what_was_hoped(self) -> None:
        """
        Laundry DOES clear the demographic bar, so the verdict must not claim a
        clean null. This test exists because the first draft of the module
        asserted one before the control was run.
        """
        sat = af.saturation_evidence()
        if sat["window_can_see_automation"]:
            assert "may carry an automation signal" in sat["verdict"]
        else:
            assert "predates the window" in sat["verdict"]


class TestTheMeasurementItself:

    def test_the_window_excludes_2020(self) -> None:
        rep = af.report()
        assert 2020 not in range(*rep["window"]) or rep["n_years"] == 22
        assert rep["n_years"] == 22

    def test_trends_use_only_codes_inside_the_component(self) -> None:
        for component in af.UNFLOORED:
            prefixes = COMPONENT_CODES[component]
            for row in af.activity_trends(component):
                assert row["code"][:4] in prefixes

    def test_labels_are_bls_names_carried_in_the_extract(self) -> None:
        labels = atus.tier3_labels()
        assert labels["020102"] == "Laundry"
        assert labels["020201"] == "Food and drink preparation"
        for row in af.activity_trends("nutrition"):
            assert row["label"] == labels[row["code"]]

    def test_every_nutrition_activity_of_any_size_rose(self) -> None:
        """
        The finding: under 22 years of capital deepening, no nutrition activity
        large enough to read declined. Food presentation is ~2 h/yr and is
        dropped by the size filter rather than aggregated into a residual.
        """
        rows = af.activity_trends("nutrition", min_hours=10.0)
        assert rows
        assert all(r["direction"] == "rose" for r in rows)

    def test_small_activities_are_dropped_not_pooled(self) -> None:
        wide = af.activity_trends("shelter", min_hours=0.0)
        narrow = af.activity_trends("shelter", min_hours=50.0)
        assert len(narrow) < len(wide)
        assert all(r["hours_first"] + r["hours_last"] >= 50.0 for r in narrow)


class TestTheTier3ExtractIsATruncationOfTheTier2One:
    """
    The two tables come from the same columns of the same file, so the six-digit
    codes sharing a four-digit prefix must reproduce the tier-2 cell. Assert
    against the CSV rounding bound, NOT equality: both are written at six
    decimals, so a parent with n children can differ from their sum by up to
    (n + 1) x 5e-7 — n child roundings PLUS the parent's own. The first version
    used a flat 1e-6 and reported 435 false mismatches; the second used
    n x 5e-7 and failed on a single-child family, where the parent's own
    rounding is the whole error.
    """

    def test_tier3_rolls_up_to_tier2(self) -> None:
        for year in (2003, 2015, 2025):
            t2 = atus.minutes_per_day(year)
            t3 = atus.tier3_minutes_per_day(year)
            rolled: dict[str, float] = {}
            children: dict[str, int] = {}
            for code, minutes in t3.items():
                rolled[code[:4]] = rolled.get(code[:4], 0.0) + minutes
                children[code[:4]] = children.get(code[:4], 0) + 1
            for code, value in t2.items():
                bound = (children.get(code, 0) + 1) * 5e-7
                assert abs(value - rolled.get(code, 0.0)) <= bound, (
                    f"{year} {code}: tier-3 does not roll up to tier-2"
                )

    def test_the_tolerance_cannot_hide_a_real_discrepancy(self) -> None:
        """A bound wide enough to absorb the finding is worse than none."""
        t3 = atus.tier3_minutes_per_day(2025)
        largest_family = max(
            sum(1 for c in t3 if c[:4] == code[:4]) for code in t3
        )
        assert (largest_family + 1) * 5e-7 < 1e-3, (
            "the rounding bound has grown large enough to hide a real "
            "difference in minutes per day"
        )

    def test_the_day_still_closes_to_1440(self) -> None:
        for year in (2003, 2025):
            assert sum(atus.tier3_minutes_per_day(year).values()) == pytest.approx(
                1440.0, abs=0.05
            )


class TestFloorsChangeNothing:
    """REPORTING ONLY. This fails the moment the module moves a shipped number."""

    def test_the_care_floor_is_untouched(self) -> None:
        assert data.PERSONAL_AUTOMATION_FLOORS["care"] == data.CARE_AUTOMATION_FLOOR

    def test_running_the_report_does_not_mutate_the_table(self) -> None:
        before = dict(data.PERSONAL_AUTOMATION_FLOORS)
        af.report()
        assert dict(data.PERSONAL_AUTOMATION_FLOORS) == before

    def test_no_returned_number_is_nan(self) -> None:
        for component in af.UNFLOORED:
            for row in af.activity_trends(component):
                assert not math.isnan(row["change"])


class TestTheLongSeriesBreaksTheSaturation:
    """
    MTUS 1965-2024 measures the quantity ATUS can only see the tail of. These
    tests pin the confirmation, and the DIRECTION of the bound it yields.
    """

    def test_the_fall_is_real_and_mostly_outside_the_atus_window(self) -> None:
        s = af.long_series("US")
        assert s["change"] < 0.0, "US unpaid domestic time fell across the span"
        assert s["share_of_fall_before_window"] > 0.5

    def test_the_window_sits_in_the_flat_tail(self) -> None:
        c = af.saturation_confirmed("US")
        assert c["confirmed"] is True
        assert c["rate_ratio"] > 1.0, (
            "the pre-window decline must be faster than the in-window one, or "
            "the saturation argument does not hold"
        )

    def test_this_agrees_with_what_atus_alone_suggested(self) -> None:
        """
        The ATUS probes argued saturation from inside the window; the long
        series measures it from outside. If they ever disagree, one of the two
        instruments is wrong and the disagreement is the finding.
        """
        atus_says_flat = not af.saturation_evidence()["probes"]["020203"][
            "beyond_household_shrinkage"
        ]
        assert atus_says_flat
        assert af.saturation_confirmed("US")["confirmed"] is True

    def test_the_bound_is_declared_as_an_UPPER_bound(self) -> None:
        """
        The direction is the whole content. A 1965 baseline already carried
        household automation, so the persisting share overstates the floor.
        Reporting it as a lower bound would invert the finding.
        """
        b = af.aggregate_floor_bound("US")
        assert b["is_upper_bound"] is True
        assert 0.0 < b["persisting_share"] < 1.0
        assert str(b["baseline_year"]) in b["why_upper_bound"]

    def test_the_bound_refuses_to_constrain_one_component(self) -> None:
        b = af.aggregate_floor_bound("US")
        assert b["is_an_aggregate"] is True
        assert b["constrains_a_single_component"] is False

    def test_a_country_with_one_sample_raises_rather_than_guessing(self) -> None:
        singles = [
            c for c in {str(r["country"]) for r in mtus.domestic_by_sample()}
            if len(mtus.domestic_series(c)) < 2
        ]
        for country in singles:
            with pytest.raises(ValueError):
                af.long_series(country)


class TestTheCrossSectionIsNotACapitalGradient:
    """
    The negative result that closes off the cheap route to per-component floors.
    If this ever starts reading as a gradient, the module's method changes.
    """

    def test_it_says_so_explicitly(self) -> None:
        assert af.cross_country()["is_a_capital_gradient"] is False

    def test_at_least_one_country_moved_the_wrong_way(self) -> None:
        assert af.cross_country()["countries_where_it_ROSE"]

    def test_the_lowest_level_is_not_the_richest_country(self) -> None:
        """
        Korea reads lowest of all. Any reading that treats low unpaid domestic
        time as evidence of high capital has to explain that first.
        """
        cc = af.cross_country()
        assert cc["lowest_country"] == "KR"
        assert cc["latest_level"]["KR"] < cc["latest_level"]["US"]


class TestTheMtusExtract:

    def test_the_day_closes_to_1440_in_every_sample(self) -> None:
        """
        The units check. MTUS ships no codebook with this extract, so the
        twelve aggregates summing to a whole day is what establishes that the
        numbers are minutes per day.
        """
        offenders = []
        for row in mtus.domestic_by_sample():
            if float(row["day_minutes"]) != pytest.approx(1440.0, abs=0.01):
                offenders.append(str(row["sample"]))
        assert set(offenders) == set(mtus.NONSTANDARD_DAY_SAMPLES), (
            "a sample whose day does not close must be DECLARED with its reason, "
            "not silently carried or silently dropped"
        )

    def test_the_declared_offender_is_the_one_measured(self) -> None:
        """FR1999 sums to 1680 while its own siblings sum to 1440."""
        rows = {str(r["sample"]): float(r["day_minutes"]) for r in mtus.domestic_by_sample()}
        assert rows["FR1999"] == pytest.approx(1680.0, abs=0.01)
        assert rows["FR1985"] == pytest.approx(1440.0, abs=0.01)
        assert rows["FR2009"] == pytest.approx(1440.0, abs=0.01)
        assert mtus.day_closes("FR1999") is False
        assert mtus.day_closes("US1965") is True

    def test_the_offender_does_not_reach_any_reported_finding(self) -> None:
        """
        FR1999 is neither end of the French span, so nothing this module
        reports depends on it. If that ever changes, the level defect starts
        propagating and this test is where it surfaces.
        """
        span = af.cross_country()["spans"]["FR"]
        assert 1999 not in (span["first_year"], span["last_year"])

    def test_every_sample_carries_a_country_and_a_year(self) -> None:
        for row in mtus.domestic_by_sample():
            assert row["country"]
            assert 1960 <= int(row["year"]) <= 2030
            assert int(row["n_respondents"]) > 0

    def test_the_us_series_spans_the_appliance_transition(self) -> None:
        years = [y for y, _ in mtus.domestic_series("US")]
        assert min(years) <= 1965
        assert max(years) >= 2024


class TestTheWindowYearIsBoundNotRestated:
    """
    The shadow ratchet caught `ATUS_WINDOW_OPENS = 2003` as a domain constant
    declared outside data.py. It was not migrated — it was BOUND, because the
    extract already carries the fact and a second account of one quantity is
    how the two come to differ.
    """

    def test_it_is_derived_from_the_extract(self) -> None:
        years = [r.year for r in atus.survey_years() if r.comparable and r.year != 2020]
        assert af.atus_window_opens() == min(years)

    def test_it_is_not_a_literal_anywhere_in_the_module(self) -> None:
        import inspect
        source = inspect.getsource(af)
        assert "ATUS_WINDOW_OPENS" not in source
        assert "= 2003" not in source


class TestTheSixDigitCodingSeparatesTheComponents:
    """
    The mapping is a declared judgement, but unlike most it is FALSIFIABLE: US
    samples are coded independently by MTUS and ATUS, so the same
    population-year is measured twice.
    """

    def test_each_mapping_reproduces_its_atus_component(self) -> None:
        for component, v in af.validate_code_mapping().items():
            assert v["within_tolerance"], (
                f"{component}: MTUS {v['codes']} reads {v['mean_ratio']:.3f} of "
                f"ATUS {v['atus_target']} — the codes are not that component"
            )
            assert v["residual_is_small"]

    def test_it_holds_across_many_years_not_one(self) -> None:
        """One year agreeing is a coincidence; twenty-one is an identification."""
        for v in af.validate_code_mapping().values():
            assert v["n_years"] >= 15
            assert v["spread"] < 0.15

    def test_the_target_is_the_models_own_component_not_a_hand_pick(self) -> None:
        """
        The first version compared shelter against ATUS 0201 alone and read a
        28% excess. The mapping was right; the target was wrong. Validating
        against COMPONENT_CODES removes the choice.
        """
        from hours_eoh.scenarios.component_shares import COMPONENT_CODES
        for component, v in af.validate_code_mapping().items():
            assert tuple(v["atus_target"]) == tuple(COMPONENT_CODES[component])

    def test_a_wrong_mapping_is_rejected(self) -> None:
        """The check must be able to fail, or it certifies nothing."""
        original = dict(af.COMPONENT_CODES_MTUS)
        try:
            af.COMPONENT_CODES_MTUS["nutrition"] = (2,)      # sleep
            assert not af.validate_code_mapping()["nutrition"]["within_tolerance"]
        finally:
            af.COMPONENT_CODES_MTUS.clear()
            af.COMPONENT_CODES_MTUS.update(original)


class TestThePerComponentBounds:

    def test_nutrition_fell_then_reversed(self) -> None:
        """
        The shape the ATUS window could not see: nutrition fell sharply to a
        minimum in the mid-2000s and has risen since. ATUS opens in 2003, so it
        sees only the recovery — which is why it reported a RISE.
        """
        s = af.component_long_series("nutrition")
        assert s["change_before_window"] < -0.2, "a large fall before the window"
        assert s["change_inside_window"] > 0.0, "a rise inside it"
        assert s["reversed_after_minimum"] is True

    def test_the_bound_is_an_upper_bound_and_says_so(self) -> None:
        for component, b in af.component_floor_bounds().items():
            assert b["is_upper_bound"] is True
            assert 0.0 < b["floor_upper_bound"] < 1.0
            assert b["minimum_year"] >= b["baseline_year"]

    def test_the_bounds_refute_a_zero_floor(self) -> None:
        """
        An absent entry in PERSONAL_AUTOMATION_FLOORS means 0.0 to the model.
        Every component measured here has visited a strictly positive minimum.
        """
        for b in af.component_floor_bounds().values():
            assert b["refutes_a_zero_floor"] is True

    def test_a_bound_still_is_not_a_floor_value(self) -> None:
        """A minimum that was reached and then left is not a level it cannot pass."""
        bounds = af.component_floor_bounds()
        assert any(b["reversed_after_minimum"] for b in bounds.values())
        assert af.report()["produces_a_floor_value"] is False

    def test_the_component_split_is_finer_than_the_aggregate(self) -> None:
        """The whole point: ACT_UNDOM could not separate these."""
        bounds = af.component_floor_bounds()
        assert len(bounds) >= 2
        assert len({round(b["floor_upper_bound"], 3) for b in bounds.values()}) > 1


class TestTheCodeExtract:

    def test_three_samples_are_absent_for_a_stated_reason(self) -> None:
        """SERIAL is empty in these, so the episode join cannot reach them."""
        table = mtus.codes_by_sample()
        for sample in ("AT1992", "FR1985", "FR1999"):
            assert sample not in table
        assert len(table) >= 40

    def test_the_coding_is_finer_than_the_twelve_aggregates(self) -> None:
        for sample, codes in mtus.codes_by_sample().items():
            assert len(codes) > 12, f"{sample} has only {len(codes)} codes"

    def test_every_retained_diary_closed_to_a_full_day(self) -> None:
        """
        The ingest drops any diary not summing to 1440, so each sample's codes
        must sum to a full day. This is the arithmetic gate on a derived
        fixed-width layout that ships no codebook.
        """
        for sample, codes in mtus.codes_by_sample().items():
            assert sum(codes.values()) == pytest.approx(1440.0, abs=0.5), sample

    def test_unknown_sample_raises(self) -> None:
        with pytest.raises(KeyError):
            mtus.code_minutes("XX9999", (18,))
