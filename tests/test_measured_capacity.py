"""Measured labour capacity, and the default that stands in for it.

`feasibility.labor_supply_per_capita` asks for the hours one adult can give to
entropy-resistance labour. Its default was `H_REF`, a paid-work calendar year whose own
tag block warns against reading it as hours worked; most of the labour a person supplies
is unpaid.

These tests pin the measurement, the direction of the error, and what closed the
over-determination ([record](record/personal.md#measured-capacity-test-history)).
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
        """Travel and education are SHIPPED but not summed. Adding either would raise
        every figure by a judgement nobody has made.
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
        """Observed hours are a FLOOR on capacity, because people could work more than
        they did. Using them understates capacity, so clearing gets harder, not easier.
        """
        frames = mtus.capacity_frames()
        assert sum(v > float(H_REF) for v in frames.values()) > len(frames) / 2


class TestTheFindingDidNotSurviveTheBandCorrection:
    """The over-determination is gone; these tests pin the new state and what removed
    it. Two one-sided loosenings removed it: the band alignment (2026-09-04) raised
    supply, and the capital path (2026-09-09) lowered demand. Neither measured the
    demand side, and `AGE_WEIGHT_ELDERLY` stays a documented LOWER bound, so the surplus
    pinned here is an UPPER bound
    ([record](record/personal.md#measured-capacity-test-history)).
    """

    #: 39/50 under the pre-adoption share of 0.60, since the 2026-09-09
    #: capital-path decision; 17/50 before it. Pinned so each flip is a visible
    #: number rather than a remembered one — and the docstring above says which
    #: change produced which, because two now have.
    N_CLEARING_BEFORE_BAND_ALIGNMENT = 39
    #: what the same count read before the capital path moved, kept as the
    #: attribution rather than as a reproducible state: it is NOT recoverable
    #: from a parameter in this file.
    N_CLEARING_BEFORE_CAPITAL_PATH = 17

    def test_most_frames_now_clear_at_zero(self) -> None:
        r = measured_capacity_frames()
        assert r["n_clearing_at_zero"] > r["n_frames"] / 2, (
            "fewer than half the frames clear again. If the demand side was "
            "raised, this is the over-determination returning and the history "
            "entry should say so; if the supply share was reverted, say that."
        )

    def test_the_flip_is_the_band_alignment_and_nothing_else(self) -> None:
        """
        Re-runs the pre-adoption share directly. It DID stop reproducing 17,
        on 2026-09-09, and the guard worked exactly as written: something other
        than the band alignment had moved the frame counts. That something is
        the capital-path decision, named in the class docstring. If this stops
        reproducing 39, a THIRD change has moved them and the attribution is
        wrong again.
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
        """The retrodiction was 1965 clears and 2024 does not. Since the capital path
        both clear under either share, so the test pins the ORDERING that remains: 1965
        sits further below the line than 2024.
        """
        c65 = mtus.measured_capacity("US1965")
        c24 = mtus.measured_capacity("US2024")
        before65 = feasibility_check(adult_capacity_h_yr=c65, adult_share=0.60)
        before24 = feasibility_check(adult_capacity_h_yr=c24, adult_share=0.60)
        # BOTH HALVES NOW CLEAR UNDER THE PRE-ADOPTION SHARE TOO (2026-09-09).
        # This asserted `before24["feasible"] is False` — the surviving half of
        # the retrodiction — and the capital-path decision removed it: US2024
        # reads 0.9774, just under. The ORDERING is what remains, and it is
        # asserted because it is the part that has not moved: 1965 still sits
        # further below the line than 2024.
        assert before65["feasible"] is True and before24["feasible"] is True
        assert before65["demand_supply_ratio"] < before24["demand_supply_ratio"] < 1.0

        after65 = feasibility_check(adult_capacity_h_yr=c65)
        after24 = feasibility_check(adult_capacity_h_yr=c24)
        assert after65["feasible"] is True and after24["feasible"] is True

    def test_the_verdict_follows_the_counts(self, monkeypatch) -> None:
        """The verdict's conclusion turns with the counts; it is not fixed text.
        Frames below the demand must read as an over-determination that survives."""
        import hours_eoh.scenarios.feasibility as fz
        assert "meets that demand" in measured_capacity_frames()["verdict"]
        low = {f"XX{i}": 1500.0 for i in range(5)}
        monkeypatch.setattr(fz.mtus, "capacity_frames", lambda extra=(): low)
        r = fz.measured_capacity_frames()
        assert r["n_clearing_at_zero"] == 0
        assert "survives" in r["verdict"] and "does not understate" in r["verdict"]
        assert r["default_is_measured_median"] is False


class TestTheDefaultIsTheMeasuredMedian:
    """ADOPTED 2026-09-03 (author decision). The default is the median of 50 measured
    frames, not H_REF.
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
        """The shipped ε=0 ratio sits below 1, and below the ratio at H_REF. Capacity
        alone, on the pre-adoption share, also clears now, so "only the band fix closed
        it" is history, not a state this test reproduces
        ([record](record/personal.md#measured-capacity-test-history)).
        """
        check = feasibility_check(epsilon=0.0)
        assert check["feasible"] is True
        # 0.942 at the band alignment; 0.893 since the capital-path decision
        # (2026-09-09) took the ε=0 infrastructure term out of the demand.
        assert 0.85 < check["demand_supply_ratio"] < 1.0
        at_h_ref = feasibility_check(epsilon=0.0, adult_capacity_h_yr=float(H_REF))
        assert check["demand_supply_ratio"] < at_h_ref["demand_supply_ratio"]
        # the capacity fix ALONE, on the pre-adoption share: narrowed, not closed
        # AND THE CAPACITY-ONLY CASE NOW CLEARS TOO (2026-09-09). It read
        # 1.026 — narrowed but not closed, which is what this test was written
        # to say — and the capital-path decision took it to 0.9774. So the
        # "only the second correction closed it" account above is now the
        # history of how it was closed, not a state this file can reproduce;
        # the capacity fix alone no longer leaves a deficit to point at.
        capacity_only = feasibility_check(epsilon=0.0, adult_share=0.60)
        assert 0.95 < capacity_only["demand_supply_ratio"] < 1.0
        assert capacity_only["feasible"] is True

    def test_the_stationary_band_is_pinned_at_its_level(self) -> None:
        """The sufficiency band's floor is pinned at its level, because the
        arc_stability tests assert only its shape. Each move of the level shows here
        first; the comments list the moves.
        """
        from hours_eoh.scenarios.arc_stability import stationary_band
        # 0.491 → 0.382 → 0.374 → 0.309 → 0.290 (2026-09-09, capital path)
        # → 0.382 (2026-09-15, arc_stability moved from a uniform 1 − ε to the
        # adopted per-component split; the ONE test in the suite that moved).
        # Sixth move, fifth time the level pin made one visible.
        # → 0.384 (2026-10-04, the default stock age measured: 0.50 → 0.591).
        # → 0.383 (2026-10-15, KNOWLEDGE_EOH_BASE re-derived net -1.96% with the
        # national population at the 2024 Census).
        assert stationary_band(standard="sufficiency")["lower"] == pytest.approx(
            0.383, abs=5e-4
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
    """Capacity is measured over ages 18-69, and the working-age band is 18-64. The
    65-69 share was 5.83 points of adult share on US 2025 ages. Since 2026-09-04 the
    elderly capacity weight carries it, and these tests pin the gap and that the shipped
    path takes it ([record](record/personal.md#band-alignment-adopted)).
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
        """ADOPTED 2026-09-04: the shipped path now takes the correction, so the
        residual gap must be under one point. A report that still showed the full gap
        would be a second account of one quantity.
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
