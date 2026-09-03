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

    def test_unfloored_is_derived_from_the_table_not_restated(self) -> None:
        """
        A hardcoded list went stale the moment nutrition was adopted. Deriving
        it means the two cannot disagree — the `= 1500.0` lesson.
        """
        for component in af.UNFLOORED:
            assert component not in data.PERSONAL_AUTOMATION_FLOORS
        assert set(af.UNFLOORED) == (
            set(data.PERSONAL_EOH_COMPONENTS) - set(data.PERSONAL_AUTOMATION_FLOORS)
        )

    def test_nutrition_stays_measurable_after_adoption(self) -> None:
        """
        The series is what the floor was derived FROM, so dropping it once the
        value shipped would remove the evidence for the value.
        """
        assert "nutrition" in af.MEASURABLE
        assert "nutrition" not in af.UNFLOORED
        assert af.activity_trends("nutrition")


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
        for component in af.MEASURABLE:
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
        for component in af.MEASURABLE:
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


class TestTheReplication:
    """
    Seven within-country series are seven tests, not one. The cross-SECTION was
    shown not to be a capital gradient; a within-country span does not have
    that problem, because the institutions are roughly held and capital moves.
    """

    def test_nutrition_replicates_across_countries(self) -> None:
        r = af.replication("nutrition")
        assert r["replicates"] is True
        assert r["n_countries"] >= 6
        assert "US" in r["fell"]

    def test_shelter_replicates_too(self) -> None:
        assert af.replication("shelter")["replicates"] is True

    def test_the_declared_break_stays_in_the_denominator(self) -> None:
        """
        A replication rate computed after dropping the disagreements is not a
        replication rate. Bulgaria rose; it is flagged and COUNTED.
        """
        r = af.replication("nutrition")
        assert "BG" in r["countries"]
        assert r["countries"]["BG"]["institutional_break"]
        assert r["n_countries"] == len(r["fell"]) + len(r["rose"])
        assert r["replication_rate"] == len(r["fell"]) / r["n_countries"]

    def test_a_rise_without_an_explanation_is_reported_as_such(self) -> None:
        """
        South Africa rose and carries no declared break. That is not tidied
        away — if every exception had a story, the stories would be doing the
        work rather than the data.
        """
        r = af.replication("nutrition")
        assert "ZA" in r["rose_without_a_declared_break"]

    def test_the_break_is_declared_ahead_of_the_result_not_fitted_to_it(self) -> None:
        """
        Only countries in INSTITUTIONAL_BREAK may be discounted, and the list
        is short and specific. If it ever grows to cover every disagreement,
        the mechanism has become unfalsifiable.
        """
        assert len(af.INSTITUTIONAL_BREAK) <= 2
        for reason in af.INSTITUTIONAL_BREAK.values():
            assert len(reason) > 40, "a break must say what changed"

    def test_dropping_the_break_would_inflate_the_rate(self) -> None:
        """The bite: the honest denominator gives a lower number, and does so."""
        r = af.replication("nutrition")
        honest = r["replication_rate"]
        inflated = len(r["fell"]) / (r["n_countries"] - len(af.INSTITUTIONAL_BREAK))
        assert inflated > honest


class TestTheConvergence:
    """
    A single series' minimum is not a floor — nutrition reached it and left.
    Independent economies settling at a similar LEVEL is the better signature.
    """

    def test_nutrition_converges_more_tightly_than_shelter(self) -> None:
        """
        The asymmetry is the finding: nutrition lands in a narrow band across
        five economies with different cuisines and histories; shelter does not.
        Only one of them looks like a floor.
        """
        nut = af.developed_convergence("nutrition")
        shel = af.developed_convergence("shelter")
        assert nut["band_ratio"] < shel["band_ratio"]
        assert nut["band_ratio"] < 1.6

    def test_it_refuses_to_call_itself_a_floor_value(self) -> None:
        for component in af.COMPONENT_CODES_MTUS:
            d = af.developed_convergence(component)
            assert d["is_a_floor_value"] is False
            assert "UNPAID" in d["why_not"]

    def test_the_selection_circularity_is_declared(self) -> None:
        """
        Membership is "the countries whose series fell", which is close to
        "the countries that showed the effect". Stated, not hidden.
        """
        d = af.developed_convergence("nutrition")
        assert d["selection_is_circular"] is True
        assert set(d["members"]) == set(af.replication("nutrition")["fell"])

    def test_the_band_is_computed_from_the_members_only(self) -> None:
        d = af.developed_convergence("nutrition")
        assert d["low"] == min(d["levels"].values())
        assert d["high"] == max(d["levels"].values())
        assert "BG" not in d["levels"]

    def test_it_still_produces_no_floor_value(self) -> None:
        assert af.report()["produces_a_floor_value"] is False


class TestChildcareIsIdentifiedExactly:
    """
    The strongest identification in this work, and for a different reason from
    the others: it recovers MTUS's OWN definition rather than approximating an
    outside survey's, so it can be exact — and is.
    """

    def test_it_reproduces_the_files_own_aggregate_on_every_sample(self) -> None:
        r = af.childcare_identification()
        assert r["exact_everywhere"] is True
        assert r["min_ratio"] == pytest.approx(1.0, abs=0.005)
        assert r["max_ratio"] == pytest.approx(1.0, abs=0.005)
        assert r["n_samples"] >= 40

    def test_a_wrong_code_set_is_rejected(self) -> None:
        original = af.CHILDCARE_CODES_MTUS
        try:
            af.CHILDCARE_CODES_MTUS = (28, 29)          # type: ignore[misc]
            assert af.childcare_identification()["exact_everywhere"] is False
        finally:
            af.CHILDCARE_CODES_MTUS = original          # type: ignore[misc]


class TestChildcareIsNotTheCareComponent:
    """
    The scope limit is measured and travels with the series. Care is 62.1% of
    the personal component, so overstating what is measured here would be the
    most consequential overclaim available in this module.
    """

    def test_it_does_not_clear_the_mapping_bar(self) -> None:
        s = af.childcare_is_not_the_care_component()
        assert s["clears_the_mapping_bar"] is False
        assert 0.7 < s["share_of_atus_care"] < 0.95

    def test_it_is_not_admitted_as_a_component(self) -> None:
        """Structural, not a comment: it is kept out of the validated map."""
        assert "childcare" not in af.COMPONENT_CODES_MTUS
        assert "childcare" in af._EXTRA_CODE_SETS
        assert af.childcare_is_not_the_care_component()["admitted_as_a_component"] is False

    def test_what_is_missing_is_named(self) -> None:
        what = af.childcare_is_not_the_care_component()["what_is_missing"]
        assert "adult" in what and "non-household" in what

    def test_the_validated_map_still_covers_only_the_two_that_qualify(self) -> None:
        assert set(af.COMPONENT_CODES_MTUS) == {"nutrition", "shelter"}
        for v in af.validate_code_mapping().values():
            assert v["within_tolerance"]


class TestTheCareFloorCorroboration:
    """
    `CARE_AUTOMATION_FLOOR` is normative — a charter commitment with no dataset
    behind it. This does not measure it, and says so; it asks whether the
    series behaves as a high floor would predict.
    """

    def test_childcare_is_far_flatter_than_nutrition(self) -> None:
        c = af.care_floor_corroboration()
        assert c["childcare_is_flatter"] is True
        assert abs(c["us_childcare_change"]) < 0.05
        assert c["us_nutrition_change"] < -0.2

    def test_the_contrast_is_magnitude_not_a_majority_vote(self) -> None:
        """
        With seven countries a majority test turns 4-3 into a replication and
        3-4 into nothing, which is a coin toss dressed as a finding.
        """
        c = af.care_floor_corroboration()
        assert c["childcare_median_abs_change"] < c["nutrition_median_abs_change"] / 2.0
        assert c["consistent_with_a_high_floor"] is True

    def test_it_refuses_to_call_itself_a_measurement(self) -> None:
        assert af.care_floor_corroboration()["is_a_measurement_of_the_floor"] is False

    def test_the_confound_runs_the_helpful_way_and_is_stated(self) -> None:
        """
        Paid daycare moves care OUT of unpaid time, so observed childcare should
        fall even with no automation. It does not — which makes flatness harder
        to explain away, not easier. The docstring must keep saying so.
        """
        import re
        doc = re.sub(r"\s+", " ", af.care_floor_corroboration.__doc__ or "")
        assert "daycare" in doc
        assert "It does not fall" in doc

    def test_the_normative_floor_is_untouched(self) -> None:
        from hours_eoh import data
        assert data.CARE_AUTOMATION_FLOOR == data.PERSONAL_AUTOMATION_FLOORS["care"]
        assert af.report()["produces_a_floor_value"] is False


class TestTheMarketSubstitutionCheck:
    """
    The convergence's stated limit, partly addressed. If the rise in home
    preparation were the market unwinding into the observation, buying prepared
    food would move WITH it. It moves against.
    """

    def test_preparation_and_bought_food_move_opposite_ways(self) -> None:
        r = af.market_substitution_check()
        assert r["preparation_rose"] is True
        assert r["bought_food_fell"] is True
        assert r["moves_against_each_other"] is True
        assert r["rise_is_marketisation"] is False

    def test_groceries_move_with_preparation_not_against_it(self) -> None:
        """Cooking at home needs ingredients; the two should rise together."""
        s = af.market_substitution_check()["series"]
        assert s["groceries"]["change"] > 0.0
        assert s["preparation"]["change"] > 0.0

    def test_eating_is_the_control_and_is_flat(self) -> None:
        """
        Substitution changes where food is PREPARED, not how much is eaten. If
        total eating moved sharply, something other than substitution is going
        on and neither reading would be safe.
        """
        r = af.market_substitution_check()
        assert r["eating_is_roughly_flat"] is True

    def test_eating_is_excluded_from_the_away_composite(self) -> None:
        """
        Eating happens wherever the food came from, so it says nothing about
        who prepared it. Including it would make the composite move with meals
        rather than with the market.
        """
        assert "110101" not in af.FOOD_AWAY_CODES
        assert set(af.FOOD_AWAY_CODES) & set(af.GROCERY_CODES) == set()

    def test_it_states_the_two_things_it_does_not_cover(self) -> None:
        """
        The window opens in 2003, so the 1965-2005 FALL — where the converged
        level came from — is outside it; and it is one country while the
        convergence is a cross-country claim.
        """
        r = af.market_substitution_check()
        assert r["covers_the_fall"] is False
        assert r["is_cross_country"] is False
        assert r["window"][0] >= 2003

    def test_the_convergence_records_it_as_partial(self) -> None:
        d = af.developed_convergence("nutrition")
        assert d["substitution_tested_for_us"] is True
        assert d["substitution_tested_cross_country"] is False
        assert d["is_a_floor_value"] is False, (
            "a partial answer to one of two limits does not make this a value"
        )


class TestTheNutritionFloorEstimate:
    """
    The one construction here that marketisation cannot move, because it counts
    PAID AND UNPAID human labour. A restaurant cook is human labour.
    """

    def test_service_is_excluded_and_the_estimate_is_the_lower_reading(self) -> None:
        r = af.nutrition_floor_estimate()
        assert r["service_excluded"] is True
        assert r["estimate"] == r["estimate_excluding_service"]
        assert r["estimate"] < r["superseded_reading_including_service"]

    def test_the_superseded_reading_survives(self) -> None:
        """
        The 14-point difference the decision resolves stays visible, on the
        pattern the Psi policies and `uniform` set: a decided-against reading
        is kept reachable so the decision can be re-examined, not erased.
        """
        r = af.nutrition_floor_estimate()
        assert r["decision_cost"] == pytest.approx(
            r["superseded_reading_including_service"] - r["estimate"], rel=1e-12
        )
        assert r["decision_cost"] > 0.10

    def test_the_reason_is_that_service_is_unbounded(self) -> None:
        """
        Structural, not a preference: a floor is a LOWER bound and elaboration
        has no upper one, so service is a market price above the floor rather
        than part of it.
        """
        import re
        r = af.nutrition_floor_estimate()
        assert r["service_is_unbounded"] is True
        doc = re.sub(r"\s+", " ", af.nutrition_floor_estimate.__doc__ or "")
        assert "no upper one" in doc or "no cap" in doc
        assert "market_premium" in doc

    def test_service_is_what_splits_it(self) -> None:
        """
        The unassisted benchmark has ZERO service — a subsistence economy has no
        restaurants — so service hours are an activity that did not previously
        exist, not labour that survived automation. Both readings are defensible
        and they differ, which is why no point estimate is given.
        """
        r = af.nutrition_floor_estimate()
        assert r["unassisted_service_is_zero"] is True
        assert r["decision_cost"] > 0.10

    def test_production_is_the_measured_part(self) -> None:
        """Automation took essentially all of production; that half is measured."""
        r = af.nutrition_floor_estimate()
        assert r["production_retained"] < 0.05
        assert r["unassisted_production_benchmark"] > 0.0

    def test_the_assumed_term_is_flagged_as_assumed(self) -> None:
        assert af.nutrition_floor_estimate()["unassisted_processing_is_assumed"] is True

    def test_marketisation_cannot_move_it(self) -> None:
        """
        The reason this construction exists. Paid and unpaid are both counted,
        so shifting cooking between home and restaurant moves hours between
        buckets and leaves the total alone.
        """
        r = af.nutrition_floor_estimate()
        assert r["marketisation_cannot_move_it"] is True
        assert 0.0 < r["paid_share"] < 1.0, "both buckets must be non-empty"

    def test_it_is_adopted_but_still_not_a_measurement(self) -> None:
        """
        ADOPTED 2026-09-03. It remains an ESTIMATE — a ceiling on an assumed
        term — and is tagged `placeholder` with a confidence rather than
        promoted to `normative`, because a value that moves when the data
        arrives is not a commitment.
        """
        from utils import provenance as pv
        r = af.nutrition_floor_estimate()
        assert r["is_a_measurement"] is False
        assert r["is_adopted"] is True
        assert af.PERSONAL_AUTOMATION_FLOORS["nutrition"] == pytest.approx(
            data.NUTRITION_AUTOMATION_FLOOR, rel=1e-12
        )
        record = next(
            x for x in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records
            if x.name == "NUTRITION_AUTOMATION_FLOOR"
        )
        assert record.tag == "placeholder", "an estimate is not a commitment"
        assert record.confidence, "an adopted placeholder must state its confidence"
        assert record.resolves_by, "and what would settle it"

    def test_it_refuses_to_run_without_the_measured_benchmark(self) -> None:
        """Inventing a denominator is the failure this module exists to avoid."""
        import hours_eoh.scenarios.food_conservation as fcmod
        original = fcmod.conservation_test

        def blank(*a, **k):
            out = original(*a, **k)
            out["stages"] = [
                {**s, "lsms_hours": None} if s["stage"] == "production" else s
                for s in out["stages"]
            ]
            return out

        fcmod.conservation_test = blank        # type: ignore[assignment]
        try:
            with pytest.raises(ValueError, match="no denominator|benchmark"):
                af.nutrition_floor_estimate()
        finally:
            fcmod.conservation_test = original  # type: ignore[assignment]

    def test_the_band_brackets_the_independent_mtus_bound(self) -> None:
        """
        REPORTED, NOT ASSERTED AS CORROBORATION. The MTUS route gives an upper
        bound of ~0.511 on a different quantity — unpaid preparation against its
        own 1965 level, not total labour against an unassisted benchmark. That
        it lands inside this band is worth noticing and is NOT evidence the two
        agree, because they do not measure the same thing.
        """
        r = af.nutrition_floor_estimate()
        low = r["estimate"]
        high = r["superseded_reading_including_service"]
        mtus_bound = af.component_floor_bounds()["nutrition"]["floor_upper_bound"]
        assert low < mtus_bound < high


class TestTheEstimateErrsHigh:
    """
    The one assumption in the estimate is that unassisted processing equals
    current US processing. `reference/personal_basket` says processing plausibly
    EXCEEDS production in hand-powered systems, so the assumption is low and the
    estimate is a ceiling. That direction is the finding, not a caveat.
    """

    def test_the_shipped_assumption_is_the_most_generous_one(self) -> None:
        s = af.processing_sensitivity()
        assert s["shipped_is_the_highest"] is True
        assert s["errs"] == "HIGH"

    def test_a_plausible_processing_term_pushes_it_well_down(self) -> None:
        s = af.processing_sensitivity()["floors"]
        assert s["equal_to_production"] < s["assumed_equal_to_current_us"]
        assert s["twice_production"] < 0.30

    def test_the_estimate_carries_its_direction(self) -> None:
        assert af.nutrition_floor_estimate()["errs"] == "HIGH"

    def test_the_resolving_field_is_named_not_just_the_source(self) -> None:
        """
        F-001: a pointer that names a SOURCE without naming the FIELD in it has
        not been checked. This names the variable, the stratum and the scope.
        """
        field = af.PROCESSING_TERM_FIELD
        assert "hours per person" in field
        assert "at low capital" in field
        for activity in ("threshing", "milling", "fuel collection", "cooking"):
            assert activity in field
        assert af.nutrition_floor_estimate()["resolves_by"] == field
        assert "time-use" in field.lower(), (
            "the field must name the instrument that CAN reach it, not only "
            "the one that cannot"
        )

    def test_the_direction_agrees_with_the_reference_module(self) -> None:
        """
        The claim that processing exceeds production is not this module's; it is
        `personal_basket`'s, and this test fails if that statement is removed
        rather than letting the direction float free of its source.
        """
        import re
        from hours_eoh.reference import personal_basket
        doc = re.sub(r"\s+", " ", personal_basket.__doc__ or "")
        assert "processing plausibly exceeds production labour" in doc


class TestTheProcessingTermIsAnchoredNotAssumed:
    """
    The correction that came from checking a claim instead of asserting it. The
    resolving field was described as "a single variable in LSMS"; the handoff
    says ATUS "measures the processing/preparation term directly, WHICH LSMS
    CANNOT". MTUS supplies a measured anchor instead.
    """

    def test_the_anchors_all_exceed_the_assumed_term(self) -> None:
        """
        Low-capital food preparation runs 396-473 h/person-yr against the US
        220.5 the estimate assumes. Every anchor makes the denominator bigger
        and the floor smaller.
        """
        r = af.anchored_processing_estimate()
        for sample, row in r["anchors"].items():
            assert row["processing_h_yr"] > 300.0, sample
            assert row["floor"] < r["assumed_estimate"], sample

    def test_every_anchor_yields_an_upper_bound(self) -> None:
        """
        None of these frames is unassisted — South Africa 2010 has mills,
        electricity and shops — so true unassisted processing exceeds all of
        them and the true floor is below all of these.
        """
        r = af.anchored_processing_estimate()
        assert r["every_anchor_is_a_lower_bound"] is True
        assert r["so_every_floor_is_an_upper_bound"] is True

    def test_the_tightest_bound_comes_from_the_largest_anchor(self) -> None:
        """
        The opposite of the usual intuition: more unassisted processing means a
        bigger denominator and a smaller floor.
        """
        r = af.anchored_processing_estimate()
        largest = max(r["anchors"], key=lambda k: r["anchors"][k]["processing_h_yr"])
        assert r["tightest_anchor"] == largest
        assert r["tightest_bound"] == min(
            v["floor"] for v in r["anchors"].values()
        )

    def test_the_field_no_longer_claims_lsms_can_supply_it(self) -> None:
        """
        The correction, pinned. Saying LSMS could supply this made the gap look
        cheap, and it was wrong in exactly that direction.
        """
        field = af.PROCESSING_TERM_FIELD
        assert "NOT obtainable from LSMS" in field
        assert "harvest and not the meal" in field
        assert "2 of the 9" in field, "the partial WASH route must stay bounded"

    def test_the_handoff_still_says_lsms_cannot(self) -> None:
        """
        The claim is the handoff's, not this module's. If that sentence is ever
        removed, this correction has lost its source and must be re-checked.
        """
        import pathlib, re
        doc = pathlib.Path(
            "handoffs/personal_eoh/HANDOFF_personal_eoh_base.md"
        )
        if not doc.exists():          # handoffs/ is gitignored
            pytest.skip("handoff not present in this checkout")
        text = re.sub(r"\s+", " ", doc.read_text(encoding="utf-8", errors="replace"))
        assert "which LSMS cannot" in text
