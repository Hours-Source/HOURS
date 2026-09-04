"""
Measured labour capacity, and the default that stands in for it.

WHY THIS EXISTS. `feasibility.labor_supply_per_capita` asks for "hours per year
one adult can devote to entropy-resistance labor" and defaults to `H_REF` —
whose own tag block says that read "as a measurement of hours actually worked it
would be wrong in most jurisdictions... which is precisely why it is tagged as
the denominator it is." A paid-work calendar year is standing in for all the
labour a person supplies, most of which is unpaid.

These tests pin the measurement, the direction of the error, and — the part
that matters most — that correcting it does NOT dissolve the over-determination
the repo has carried since August. A fix that made the finding vanish would be
the more suspicious outcome.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    H_REF, MEASURED_CAPACITY_H_YR, PHYSICAL_CAPACITY_CEILING_H_YR,
)
from hours_eoh.reference import mtus_time_use as mtus
from hours_eoh.scenarios.feasibility import (
    feasibility_check, measured_capacity_frames,
)


class TestTheMeasurement:

    def test_every_sample_has_a_capacity(self) -> None:
        frames = mtus.capacity_frames()
        assert len(frames) >= 45
        assert all(1000.0 < v < 5000.0 for v in frames.values())

    def test_it_is_the_three_core_aggregates_and_no_others(self) -> None:
        """
        Travel and education are SHIPPED but not summed. Folding either in
        would raise every figure by a judgement nobody has made.
        """
        assert mtus.LABOUR_AGGREGATES == (
            "work_minutes_per_day", "undom_minutes_per_day", "chcare_minutes_per_day",
        )
        row = {str(r["sample"]): r for r in mtus.domestic_by_sample()}["US2024"]
        expected = sum(float(row[k]) for k in mtus.LABOUR_AGGREGATES) * 365.25 / 60.0
        assert mtus.measured_capacity("US2024") == pytest.approx(expected, rel=1e-12)

    def test_extra_aggregates_raise_it_and_are_opt_in(self) -> None:
        base = mtus.measured_capacity("US2024")
        with_travel = mtus.measured_capacity("US2024", ("travel_minutes_per_day",))
        assert with_travel > base

    def test_the_conversion_carries_no_work_year_convention(self) -> None:
        """
        A diary is a 24-hour day, so minutes/day to hours/year is the calendar.
        That is the point of using it instead of a work-year constant.
        """
        row = {str(r["sample"]): r for r in mtus.domestic_by_sample()}["US1965"]
        minutes = sum(float(row[k]) for k in mtus.LABOUR_AGGREGATES)
        assert mtus.measured_capacity("US1965") == pytest.approx(
            minutes * 365.25 / 60.0, rel=1e-12
        )

    def test_unknown_sample_raises(self) -> None:
        with pytest.raises(KeyError):
            mtus.measured_capacity("XX9999")


class TestTheDefaultUnderstatesCapacity:

    def test_most_measured_frames_exceed_h_ref(self) -> None:
        r = measured_capacity_frames()
        assert r["share_exceeding_h_ref"] > 0.8
        assert r["n_exceeding_h_ref"] >= 40

    def test_the_exceptions_are_named_not_hidden(self) -> None:
        """The five below H_REF are all Netherlands, a short-hours jurisdiction."""
        below = measured_capacity_frames()["below_h_ref"]
        assert below
        assert all(s.startswith("NL") for s in below)

    def test_the_error_runs_one_way(self) -> None:
        """
        Observed hours are a FLOOR on capacity — people could work more than
        they did — so using them understates capacity, which makes clearing
        harder rather than easier.
        """
        frames = mtus.capacity_frames()
        assert sum(v > float(H_REF) for v in frames.values()) > len(frames) / 2


class TestTheFindingDidNotSurviveTheBandCorrection:
    """
    THE OVER-DETERMINATION IS GONE, AND WHAT REMOVED IT IS RECORDED HERE.

    This class was `TestTheFindingSurvivesTheCorrection` and it asserted the
    opposite: fewer than half the frames clearing at ε=0, and US2024 among
    those that do not. Aligning the supply band to the band its capacity is
    measured on (`AGE_CAPACITY_WEIGHT_ELDERLY` 0.0 → 0.3083, adopted
    2026-09-04, author decision) moved the count **17/50 → 43/50** and flipped
    **US2024 from not-clearing to clearing**.

    WHAT THAT COST, STATED PLAINLY. The retrodiction went with it. The model
    used to say a society working 1965 hours meets its personal obligation
    unaided and one working 2024 hours does not; it no longer says that. That
    was the framework's sharpest empirical claim about modern time use.

    AND THE OBJECTION IS NOT WITHDRAWN. This file's own docstring warned that
    "a fix that made the finding vanish would be the more suspicious outcome",
    and the correction is ONE-SIDED: supply rose by a measured 5.83pp of adult
    share while `AGE_WEIGHT_ELDERLY` = 1.48 remains a documented LOWER bound,
    because the institutionalised elderly are outside the ATUS frame. So the
    surplus these tests now pin is an UPPER bound on the true one, and a
    symmetric correction — measuring the elderly obligation against the
    institutional population — could restore some or all of the finding.
    Nobody knows, because only one side has been measured.

    These tests therefore pin the NEW state and the REASON, so that the day the
    demand side is measured, the comparison is available rather than lost.
    """

    #: 17/50 under the pre-adoption share of 0.60. Pinned so the flip is a
    #: visible number rather than a remembered one.
    N_CLEARING_BEFORE_BAND_ALIGNMENT = 17

    def test_most_frames_now_clear_at_zero(self) -> None:
        r = measured_capacity_frames()
        assert r["n_clearing_at_zero"] > r["n_frames"] / 2, (
            "fewer than half the frames clear again. If the demand side was "
            "raised, this is the over-determination returning and the history "
            "entry should say so; if the supply share was reverted, say that."
        )

    def test_the_flip_is_the_band_alignment_and_nothing_else(self) -> None:
        """
        Re-runs the pre-adoption share directly. If this stops reproducing 17,
        something OTHER than the band alignment has moved the frame counts and
        the attribution in the history entry is wrong.
        """
        frames = mtus.capacity_frames()
        before = sum(
            1 for c in frames.values()
            if feasibility_check(adult_capacity_h_yr=c, adult_share=0.60)["feasible"]
        )
        assert before == self.N_CLEARING_BEFORE_BAND_ALIGNMENT

    def test_the_frames_that_clear_are_the_high_labour_ones(self) -> None:
        r = measured_capacity_frames()
        clearing = r["clearing"]
        assert "US1965" in clearing
        assert "FR1966" in clearing
        assert "US2024" in clearing, (
            "US2024 no longer clears. That would restore the retrodiction — "
            "check whether the demand side was measured, which is the "
            "symmetric correction record/personal.md § Open asks for."
        )

    def test_clearing_is_exactly_capacity_above_the_requirement(self) -> None:
        """No separate criterion: a frame clears iff it supplies the hours."""
        r = measured_capacity_frames()
        need = r["hours_per_adult_required"]
        for sample, row in r["frames"].items():
            assert row["feasible_at_zero"] is (row["capacity_h_yr"] >= need), sample

    def test_the_retrodiction_held_only_under_the_unaligned_band(self) -> None:
        """
        THE CLAIM THAT WAS LOST, KEPT RUNNABLE. Under the pre-adoption share
        both halves held: 1965 clears, 2024 does not. Under the adopted share
        both clear. Asserting BOTH states is the only way a reader can see what
        the adoption changed without re-deriving it, and it is the comparison
        the symmetric correction will need.
        """
        c65 = mtus.measured_capacity("US1965")
        c24 = mtus.measured_capacity("US2024")
        before65 = feasibility_check(adult_capacity_h_yr=c65, adult_share=0.60)
        before24 = feasibility_check(adult_capacity_h_yr=c24, adult_share=0.60)
        assert before65["feasible"] is True and before24["feasible"] is False
        assert before65["demand_supply_ratio"] < 1.0 < before24["demand_supply_ratio"]

        after65 = feasibility_check(adult_capacity_h_yr=c65)
        after24 = feasibility_check(adult_capacity_h_yr=c24)
        assert after65["feasible"] is True and after24["feasible"] is True


class TestTheDefaultIsTheMeasuredMedian:
    """
    ADOPTED 2026-09-03 (author decision). The default was H_REF — a paid-work
    calendar year whose own tag block warns against being read as hours
    actually worked. It is now the median of 50 measured frames.
    """

    def test_every_capacity_default_is_the_measured_median(self) -> None:
        import inspect
        from hours_eoh.scenarios import feasibility as f
        from hours_eoh.scenarios import arc_stability as a
        for mod, name in (
            (f, "labor_supply_per_capita"), (f, "feasibility_check"),
            (f, "feasible_epsilon"), (a, "stability_at"),
        ):
            default = inspect.signature(getattr(mod, name)).parameters[
                "adult_capacity_h_yr"
            ].default
            assert default == MEASURED_CAPACITY_H_YR, f"{name} default drifted"

    def test_no_capacity_default_is_a_bare_literal(self) -> None:
        """
        `arc_stability.stability_at` carried a hardcoded 2000.0 that did not
        follow H_REF when it moved to 2080 — a third work-year convention, and
        the `= 1500.0` pattern. Nothing may restate a capacity again.
        """
        import inspect
        from hours_eoh.scenarios import arc_stability as a, feasibility as f
        for mod in (a, f):
            source = inspect.getsource(mod)
            assert "adult_capacity_h_yr: float = 2000.0" not in source
            assert "adult_capacity_h_yr: float = 2080" not in source

    def test_the_capacity_fix_narrowed_the_deficit_and_the_band_fix_closed_it(self) -> None:
        """
        TWO CORRECTIONS, AND ONLY THE SECOND CLOSED IT — which is the honest
        account of a result that used to read as one number.

        Under H_REF the ε=0 ratio was 1.1525. Measuring capacity (2026-09-03)
        took it to ~1.026: narrowed, not closed, and this file was written to
        say so. Aligning the supply band to the capacity band (2026-09-04) took
        it to ~0.942: closed. The capacity fix is symmetric — it corrects a
        quantity measured on its own terms. The band fix is NOT: supply moved
        by a measured 5.83pp while demand stays a documented lower bound.
        """
        check = feasibility_check(epsilon=0.0)
        assert check["feasible"] is True
        assert 0.90 < check["demand_supply_ratio"] < 1.0
        at_h_ref = feasibility_check(epsilon=0.0, adult_capacity_h_yr=float(H_REF))
        assert check["demand_supply_ratio"] < at_h_ref["demand_supply_ratio"]
        # the capacity fix ALONE, on the pre-adoption share: narrowed, not closed
        capacity_only = feasibility_check(epsilon=0.0, adult_share=0.60)
        assert 1.0 < capacity_only["demand_supply_ratio"] < 1.10
        assert capacity_only["feasible"] is False

    def test_the_stationary_band_is_pinned_at_its_level(self) -> None:
        """
        PINNED BECAUSE IT MOVED, AND IT HAS MOVED AGAIN. The sufficiency band's
        floor was 0.491 under the stale 2000.0 literal, 0.382 under the measured
        median, 0.374 after the per-component automation default, and is 0.309
        with the supply band aligned (2026-09-04). Each move was invisible to
        the arc_stability tests, which assert shape (`lower > 0`) and never
        level — pinning the level is what makes the next one visible, and this
        is the third time that has paid.
        """
        from hours_eoh.scenarios.arc_stability import stationary_band
        assert stationary_band(standard="sufficiency")["lower"] == pytest.approx(
            0.309, abs=5e-4
        )
        assert stationary_band(standard="survival")["lower"] == pytest.approx(
            0.0, abs=5e-4
        )


class TestCapacityHasAPhysicalCeiling:
    """
    A person cannot supply more labour than time elapses. That is the calendar,
    not endurance — the sustainable limit is far lower and is empirical.
    """

    def test_the_ceiling_is_the_hours_in_a_year(self) -> None:
        from hours_eoh.data import SECONDS_PER_YEAR
        assert PHYSICAL_CAPACITY_CEILING_H_YR == pytest.approx(
            SECONDS_PER_YEAR / 3600.0, rel=1e-12
        )
        assert PHYSICAL_CAPACITY_CEILING_H_YR == pytest.approx(24 * 365.25, rel=1e-12)

    def test_an_impossible_capacity_is_refused(self) -> None:
        from hours_eoh.scenarios.feasibility import labor_supply_per_capita
        with pytest.raises(ValueError, match="more labour than time"):
            labor_supply_per_capita(
                adult_capacity_h_yr=PHYSICAL_CAPACITY_CEILING_H_YR + 1.0
            )

    def test_the_ceiling_itself_is_accepted(self) -> None:
        """The bound is inclusive: it is impossible to EXCEED, not to reach."""
        from hours_eoh.scenarios.feasibility import labor_supply_per_capita
        assert labor_supply_per_capita(
            adult_capacity_h_yr=PHYSICAL_CAPACITY_CEILING_H_YR
        ) > 0.0

    def test_nothing_measured_comes_close_to_it(self) -> None:
        """
        The binding limit in practice is endurance, not the calendar. The
        highest measured frame is about a third of the ceiling; if a measured
        frame ever approached it, the measurement would be wrong.
        """
        worst = max(mtus.capacity_frames().values())
        assert worst / PHYSICAL_CAPACITY_CEILING_H_YR < 0.5

    def test_the_default_sits_inside_the_measured_range(self) -> None:
        frames = mtus.capacity_frames().values()
        assert min(frames) < MEASURED_CAPACITY_H_YR < max(frames)


class TestTheCapacityBandIsNotTheSupplyBand:
    """
    c is measured over 18-69; a selects 18-64. Reported, not corrected.

    THE DEFECT IS ARITHMETIC, NOT EPISTEMIC. `MEASURED_CAPACITY_H_YR` is hours
    per adult per year over ages 18-69 — 65-69 are in its denominator. The adult
    share it is multiplied by gives `elderly` a capacity weight of 0.0, so the
    same people are outside a's numerator. L = c·a therefore understates hours
    per capita by the 65-69 share, which is 5.83 percentage points on US 2025
    single-year ages.

    AND IT IS DELIBERATELY NOT FIXED. Correcting supply alone takes the ε=0
    feasibility ratio from 1.0245 to 0.9338 — the over-determination this file's
    own docstring says must not vanish. It would vanish for a one-sided reason:
    `AGE_WEIGHT_ELDERLY` = 1.48 is documented as a LOWER bound, because the
    institutionalised elderly are outside the ATUS frame, so demand is
    understated too by an amount nobody has measured. These tests pin the gap,
    its direction, and the fact that the shipped path does NOT take it.
    """

    def test_the_two_bands_disagree(self) -> None:
        from hours_eoh.data import AGE_GROUP_RANGES, CAPACITY_MEASUREMENT_BAND
        assert CAPACITY_MEASUREMENT_BAND != AGE_GROUP_RANGES["working_age"], (
            "the bands now agree — if the capacity extract was re-cut to 18-64, "
            "or the working-age range widened, this report is obsolete and the "
            "elderly capacity weight should be revisited with it."
        )

    def test_the_gap_is_the_65_to_69_share_and_is_positive(self) -> None:
        from hours_eoh.scenarios.feasibility import capacity_band_alignment
        r = capacity_band_alignment()
        assert r["gap_pp"] > 0.0, (
            "the measured band must be WIDER than the selected one; a negative "
            "gap means c is measured on fewer people than a selects, which "
            "would overstate supply rather than understate it."
        )
        assert r["share_measured"] > r["share_selected"]

    def test_the_bands_now_agree_and_the_report_measures_nothing(self) -> None:
        """
        ADOPTED 2026-09-04. The report was written to hold a correction the
        shipped path did not take; the path now takes it, so the gap it
        measures must be zero. A reporting function whose finding has been
        adopted and which still reports a gap is two accounts of one quantity.
        """
        from hours_eoh.scenarios.feasibility import capacity_band_alignment
        r = capacity_band_alignment()
        gap_pp = (r["adult_share_band_aligned"] - r["adult_share_used"]) * 100.0
        assert 0.0 <= gap_pp < 1.0, (
            f"the band gap is {gap_pp:.2f}pp, was 5.83 before adoption and "
            "0.61 after. A gap near 5.8 means AGE_CAPACITY_WEIGHT_ELDERLY was "
            "reverted; a gap above 1 means AGE_GROUP_FRACTIONS drifted from the "
            "census structure the weight was derived on."
        )
        assert r["feasible_as_shipped"] == r["feasible_band_aligned"], (
            "the residual gap now flips ε=0 feasibility — it is no longer a "
            "rounding difference between a convention and a census."
        )

    def test_the_shipped_share_carries_the_elderly_inside_the_capacity_band(self) -> None:
        from hours_eoh.data import AGE_CAPACITY_WEIGHT_ELDERLY, AGE_GROUPS
        from hours_eoh.scenarios.feasibility import capacity_weighted_adult_share
        assert AGE_CAPACITY_WEIGHT_ELDERLY == 0.3083
        expected = 0.60 + AGE_GROUPS["elderly"]["fraction"] * AGE_CAPACITY_WEIGHT_ELDERLY
        assert capacity_weighted_adult_share() == pytest.approx(expected)
