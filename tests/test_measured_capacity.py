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


class TestTheFindingSurvivesTheCorrection:
    """
    The load-bearing test. If correcting the default made ε=0 feasible
    everywhere, the correction would be doing suspicious work.
    """

    def test_most_frames_still_do_not_clear_at_zero(self) -> None:
        r = measured_capacity_frames()
        assert r["n_clearing_at_zero"] < r["n_frames"] / 2

    def test_the_frames_that_clear_are_the_high_labour_ones(self) -> None:
        r = measured_capacity_frames()
        clearing = r["clearing"]
        assert "US1965" in clearing
        assert "FR1966" in clearing
        assert "US2024" not in clearing

    def test_clearing_is_exactly_capacity_above_the_requirement(self) -> None:
        """No separate criterion: a frame clears iff it supplies the hours."""
        r = measured_capacity_frames()
        need = r["hours_per_adult_required"]
        for sample, row in r["frames"].items():
            assert row["feasible_at_zero"] is (row["capacity_h_yr"] >= need), sample

    def test_1965_us_clears_and_2024_us_does_not(self) -> None:
        """
        The retrodiction, pinned. A society working 1965 hours meets the
        model's obligation with no automation; one working 2024 hours does not.
        """
        us65 = feasibility_check(adult_capacity_h_yr=mtus.measured_capacity("US1965"))
        us24 = feasibility_check(adult_capacity_h_yr=mtus.measured_capacity("US2024"))
        assert us65["feasible"] is True
        assert us24["feasible"] is False
        assert us65["demand_supply_ratio"] < 1.0 < us24["demand_supply_ratio"]


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

    def test_the_verdict_is_unchanged_and_the_deficit_narrowed(self) -> None:
        """
        The finding SURVIVES its own fix, which is why the fix was worth
        making. Under H_REF the ratio was 1.1525; measured it is ~1.026. It
        narrowed and it did not close.
        """
        check = feasibility_check(epsilon=0.0)
        assert check["feasible"] is False
        assert 1.0 < check["demand_supply_ratio"] < 1.10
        at_h_ref = feasibility_check(epsilon=0.0, adult_capacity_h_yr=float(H_REF))
        assert check["demand_supply_ratio"] < at_h_ref["demand_supply_ratio"]

    def test_the_stationary_band_is_pinned_at_its_level(self) -> None:
        """
        PINNED BECAUSE IT MOVED. The sufficiency band's floor was 0.491 under
        the stale 2000.0 literal and is 0.382 under the measured median — a
        shift of about a fifth of the band's width that NO test would have
        caught, because the arc_stability tests assert shape (`lower > 0`) and
        never level. Pinning the level is what makes the next move visible.
        """
        from hours_eoh.scenarios.arc_stability import stationary_band
        assert stationary_band(standard="sufficiency")["lower"] == pytest.approx(
            0.374, abs=5e-4
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
