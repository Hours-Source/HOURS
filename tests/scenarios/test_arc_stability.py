"""
Tests for scenarios/arc_stability.py — Phase 1, the compass made checkable.

Discipline:
  * conditions asserted as ORDERINGS and SIGNS, never as levels — every level
    here moves with the capital path and the knowledge anchor, and the anchor
    has been re-derived six times;
  * the structural implication (3 ⇒ 1) is pinned as algebra, not observed;
  * `TestStabilityChangesNothing` pins that this is reporting only.
"""

from __future__ import annotations

import pytest

from hours_eoh.scenarios.arc_stability import (
    CONDITIONS,
    band_from_flags,
    stability_arc,
    stability_at,
    stability_report,
    stationary_band,
)

ARC = (0.0, 0.40, 0.99)


class TestTheConditionsAreDeclared:

    def test_all_three_are_named_with_what_failure_means(self):
        """
        A condition nobody has written down is a condition nobody has audited —
        the `TERM_BASIS` and `ACCOUNTS` precedent. `failure_means` is the field
        that makes a failing check actionable rather than merely red.
        """
        assert set(CONDITIONS) == {
            "obligation_met", "delivery_pays", "stock_stationary",
        }
        for name, c in CONDITIONS.items():
            for field in ("asks", "test", "source", "failure_means"):
                assert c[field].strip(), f"{name}.{field}"

    def test_every_condition_appears_in_the_result(self):
        r = stability_at(0.40)
        for name in CONDITIONS:
            assert name in r, name

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            stability_at(1.5)
        with pytest.raises(ValueError):
            stability_at(-0.1)


class TestTheStructuralImplication:
    """
    Condition 3 implies condition 1 by construction:
        surplus = supply − obligation − delivery ≥ 0
        and delivery ≥ 0
        ⇒ supply ≥ obligation.
    Pinned as algebra rather than observed on a grid, because an implication
    that only holds where it was sampled is not an implication.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_stock_stationary_implies_obligation_met(self, epsilon):
        r = stability_at(epsilon)
        assert r["delivery_per_capita"] >= 0.0
        if r["stock_stationary"]:
            assert r["obligation_met"], "3 must imply 1"

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_surplus_is_the_stated_residual(self, epsilon):
        r = stability_at(epsilon)
        assert r["surplus_per_capita"] == pytest.approx(
            r["supply_per_capita"] - r["obligation_per_capita"]
            - r["delivery_per_capita"]
        )

    @pytest.mark.parametrize("epsilon", ARC)
    def test_stationary_means_all_three_and_failing_names_them(self, epsilon):
        r = stability_at(epsilon)
        flags = [r["obligation_met"], r["delivery_pays"], r["stock_stationary"]]
        assert r["stationary"] is all(flags)
        assert bool(r["failing"]) is not all(flags)


class TestWhatTheArcActuallyShows:

    def test_subsistence_is_not_stationary_and_fails_on_the_OBLIGATION(self):
        """
        THE LOW-END FINDING, and which condition fails is the whole content. At
        ε=0 the obligation exceeds the labour that exists to serve it; the
        apparatus is not the problem. That is the repo's own recorded position
        — subsistence can survive but cannot reach sufficiency without
        automation — arriving from the stability side.
        """
        r = stability_at(0.0)
        assert r["stationary"] is False
        assert r["obligation_met"] is False
        assert "obligation_met" in r["failing"]
        assert r["delivery_pays"] is True, (
            "the apparatus is not what fails at subsistence — if this ever "
            "flips, the low-end diagnosis changes and so does the remedy"
        )

    def test_the_upper_arc_is_stationary(self):
        assert stability_at(0.99)["stationary"] is True

    def test_the_surplus_rises_across_the_arc(self):
        """ORDERING, not level. More automation frees more labour."""
        s = [r["surplus_per_capita"] for r in stability_arc()]
        assert s == sorted(s)

    def test_the_human_delivery_cost_peaks_in_the_INTERIOR(self):
        """
        A shape I did not predict and the run produced. The human share of the
        delivery cost is (1 − ε)·delivery: delivery grows with the capital stock
        while (1 − ε) collapses faster, so the product peaks mid-arc rather than
        rising monotonically. Pinned because an arc test assuming monotonicity
        here would fail on a correct implementation — the Ψ-bell trap in a new
        place.
        """
        d = [r["delivery_per_capita"] for r in stability_arc()]
        assert d.index(max(d)) not in (0, len(d) - 1), (
            "the human delivery cost should peak strictly inside the arc"
        )
        assert d[-1] < d[0] or d[-1] < max(d)

    def test_the_obligation_per_capita_falls_across_the_arc(self):
        o = [r["obligation_per_capita"] for r in stability_arc()]
        assert o == sorted(o, reverse=True)


class TestTheStationaryBand:

    def test_the_band_exists_and_excludes_subsistence(self):
        b = stationary_band()
        assert b["any_stationary"] is True
        assert b["lower"] > 0.0, "ε=0 must not be inside the band"
        assert b["upper"] > b["lower"]

    def test_contiguity_is_measured_not_assumed(self):
        """
        A band reported as contiguous must have no failing point inside it.
        """
        b = stationary_band()
        assert b["contiguous"] is (b["gaps"] == [])

    def test_the_non_contiguous_branch_is_REACHABLE(self):
        """
        THE BITE THAT WAS MISSING. On the shipped calibration the band is
        contiguous, so a test driving only the model cannot tell "contiguous
        because it was checked" from "contiguous because it was hard-coded" —
        hard-coding `contiguous = True` passed every test in this file. The pure
        logic is now separable and both branches are exercised.
        """
        good = band_from_flags([(0.0, False), (0.1, True), (0.2, True)])
        assert good["contiguous"] is True and good["gaps"] == []

        broken = band_from_flags([(0.0, True), (0.1, False), (0.2, True)])
        assert broken["contiguous"] is False, "a hole inside the band must show"
        assert broken["gaps"] == [0.1], "and must name where it breaks"
        assert broken["lower"] == 0.0 and broken["upper"] == 0.2

    def test_an_empty_band_is_reported_not_spanned(self):
        empty = band_from_flags([(0.0, False), (0.5, False)])
        assert empty["any_stationary"] is False
        assert empty["lower"] is None and empty["upper"] is None

    def test_the_band_is_not_presented_as_a_target(self):
        b = stationary_band()
        assert "not" in b["note"].lower() or "rather than" in b["note"].lower()
        import hours_eoh.scenarios.arc_stability as mod
        assert "not a target" in (mod.stationary_band.__doc__ or "").lower()


class TestTheReport:

    def test_it_runs_and_states_the_question_it_asks(self):
        rep = stability_report()
        assert rep["reporting_only"] is True
        assert rep["arc"] and rep["band"]
        assert "STOP here" in rep["verdict"]

    def test_the_report_distinguishes_stopping_from_arriving(self):
        """
        The compass. If this module ever starts measuring progress along the arc
        it has become `long_run.canonical_arc_trajectory` and the distinction
        that justifies it is gone.
        """
        import hours_eoh.scenarios.arc_stability as mod
        doc = " ".join((mod.__doc__ or "").split())   # the phrase wraps a line
        assert "rather than arrival at its end" in doc
        assert "canonical_arc_trajectory" in doc


class TestStabilityChangesNothing:
    """REPORTING ONLY — composes existing checks and adds no mechanism."""

    def test_the_module_declares_itself_reporting_only(self):
        import hours_eoh.scenarios.arc_stability as mod
        assert "REPORTING ONLY" in (mod.__doc__ or "")

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_underlying_checks_are_untouched(self, epsilon):
        from hours_eoh.scenarios.feasibility import feasibility_check
        before = feasibility_check(epsilon=epsilon)["demand_supply_ratio"]
        stability_at(epsilon)
        stability_report(epsilon)
        assert feasibility_check(epsilon=epsilon)["demand_supply_ratio"] == before

    def test_it_takes_no_charter_decision(self):
        import hours_eoh.scenarios.arc_stability as mod
        assert "WHAT THIS DOES NOT DO" in (mod.__doc__ or "")
