"""
The deflationary loop the non-personal-only elimination invariant names.
"""

from __future__ import annotations

import pytest

from hours_eoh.scenarios.deflation_loop import DEFAULT_SCALES, deflation_loop

REPORT = deflation_loop()


class TestTheLoopDoesNotInvertTheRelationship:

    def test_teh_rises_with_capital_over_most_of_the_sweep(self) -> None:
        """
        The invariant's fear is that capital growth shrinks the money supply.
        It does not, over the range where the arc is not already saturating:
        registration share rises with ε faster than the obligation falls.
        """
        pts = REPORT["points"]
        rising = sum(1 for a, b in zip(pts, pts[1:]) if b["teh_abated"] > a["teh_abated"])
        assert rising > len(pts) / 2, (
            "TEH now falls with capital over most of the sweep — the loop has "
            "inverted the relationship and the invariant was right."
        )

    def test_the_peak_is_not_moved_by_abatement(self) -> None:
        """
        THE SEPARATION THAT MAKES THE ANSWER USABLE. TEH peaks and falls in
        BOTH readings, at the same capital. That turn-down is ε→1 — human
        labour goes to zero, so registered EOH does — and attributing it to
        abatement would be reading a designed property as a defect.
        """
        assert REPORT["abatement_moves_the_peak"] is False
        assert REPORT["peak_flat_capital"] == REPORT["peak_abated_capital"]

    def test_the_peak_sits_where_epsilon_is_high_not_where_capital_is(self) -> None:
        pts = {p["capital_per_capita"]: p for p in REPORT["points"]}
        peak = pts[REPORT["peak_abated_capital"]]
        assert peak["epsilon"] > 0.5, (
            "the peak has moved to a low-ε point, which would mean something "
            "other than post-scarcity saturation is turning TEH down."
        )


class TestTheDampeningIsRealAndCrossesOver:

    def test_abatement_raises_teh_at_low_capital(self) -> None:
        """F_a = 1500 exceeds the flat base of 1000, so early abatement has
        not yet eaten the difference. The loop is not one-signed."""
        first = REPORT["points"][0]
        assert first["ratio"] > 1.0
        assert first["abated_base"] > 1000.0

    def test_abatement_lowers_teh_at_high_capital(self) -> None:
        last = REPORT["points"][-1]
        assert last["ratio"] < 1.0
        assert last["abated_base"] < 1000.0

    def test_the_dampening_is_monotone_in_capital(self) -> None:
        """The invariant's mechanism, checked as a DIRECTION rather than
        asserted: more capital, more dampening, at every step."""
        ratios = [p["ratio"] for p in REPORT["points"]]
        assert ratios == sorted(ratios, reverse=True), ratios

    def test_the_crossover_is_above_the_reference_capital(self) -> None:
        """
        Where it bites. At the reference capital abatement is roughly neutral;
        the dampening needs multiples of it to appear, which is why a sweep
        narrow around the reference would have reported no effect.
        """
        from hours_eoh.data import CAPITAL_STOCK_DEFAULT, REFERENCE_FRAME_POPULATION
        reference = CAPITAL_STOCK_DEFAULT / REFERENCE_FRAME_POPULATION
        assert REPORT["crossover_capital"] is not None
        assert REPORT["crossover_capital"] > reference

    def test_the_dampening_is_bounded_within_the_sweep(self) -> None:
        assert 0.05 < REPORT["max_dampening"] < 0.30, (
            f"max dampening is {REPORT['max_dampening']:.1%}. Outside this "
            "range the 'half right' reading in the module docstring and in "
            "record/personal.md needs re-deriving."
        )


class TestTheRunIsNotVacuous:

    def test_the_sweep_reaches_both_ends_of_the_arc(self) -> None:
        """A sweep that never saturates cannot see the ε→1 turn-down, and one
        that never starts low cannot see the crossover."""
        eps = [p["epsilon"] for p in REPORT["points"]]
        assert min(eps) < 0.10 and max(eps) > 0.90

    def test_epsilon_is_derived_from_the_capital_not_swept(self) -> None:
        """What makes it a loop. If ε were independent there would be no
        feedback to find."""
        pts = REPORT["points"]
        assert all(b["epsilon"] > a["epsilon"] for a, b in zip(pts, pts[1:]))
        assert len(pts) == len(DEFAULT_SCALES)
