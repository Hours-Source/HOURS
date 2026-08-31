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
    STANDARDS,
    band_by_standard,
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


class TestTheStandardIsDeclaredAndSingular:
    """
    THE DEFECT THIS MODULE SHIPPED WITH FOR ONE COMMIT, and the tests that would
    have caught it.

    Conditions 1 and 3 ran at `collapsed` (feasibility's own default) while
    condition 2 ran at `sufficiency` (overbuild's own default) — one verdict, two
    standards, undeclared. Every test in this file passed. It was found by
    checking whether the neighbouring `corridor` entry point was reachable, not
    by the suite.
    """

    def test_the_result_states_which_standard_it_is_at(self):
        r = stability_at(0.40)
        assert r["standard"] in STANDARDS
        assert r["personal_base"] > 0.0

    def test_all_three_conditions_move_together_with_the_standard(self):
        """
        THE BITE, and the first version of it did NOT bite. It asserted the
        band moves with the standard — but the band is driven by conditions 1
        and 3, so condition 2 could stay stuck on its own default undetected.
        Condition 2 is now pinned through `autarky_reference`, the one field of
        the overbuild test that moves with the standard.
        """
        from hours_eoh.core.eoh_generation import personal_base_for
        lo = stability_at(0.40, standard="survival")
        hi = stability_at(0.40, standard="sufficiency")

        assert hi["personal_base"] > lo["personal_base"]
        assert hi["personal_base"] == personal_base_for("sufficiency")
        assert lo["personal_base"] == personal_base_for("survival")
        # conditions 1 & 3
        assert hi["obligation_per_capita"] > lo["obligation_per_capita"]
        assert hi["surplus_per_capita"] < lo["surplus_per_capita"]
        # condition 2 — the one the band cannot see
        assert hi["autarky_reference"] > lo["autarky_reference"], (
            "the standard did not reach overbuild_check; condition 2 is stuck "
            "on its own default, which is the mixed-standard defect"
        )

    def test_the_reported_standard_is_the_requested_one(self):
        """
        Hard-coding the reported field passed every earlier test — the
        reported-vs-applied shape again. Pinned against the request.
        """
        for st in STANDARDS:
            assert stability_at(0.40, standard=st)["standard"] == st

    def test_the_supply_does_not_depend_on_the_standard_and_says_so(self):
        """
        The labour SUPPLY is a capacity, not an obligation, so it must NOT move
        with the standard. This module briefly passed `personal_base` into
        `feasibility_check` and read only `supply_per_capita`, which ignores it —
        a silently-ignored parameter. It now calls `labor_supply_per_capita`
        directly, which is honest about what it needs.
        """
        lo = stability_at(0.40, standard="survival")
        hi = stability_at(0.40, standard="sufficiency")
        assert lo["supply_per_capita"] == hi["supply_per_capita"]
        # The CALL, not the word — the module still discusses the defect in
        # prose, and a substring check would fire on its own documentation (the
        # claims-register lesson).
        import ast
        import hours_eoh.scenarios.arc_stability as mod
        tree = ast.parse(open(mod.__file__).read())
        called = {
            n.func.id for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "feasibility_check" not in called, (
            "reading only `supply_per_capita` from feasibility_check invites "
            "passing it a standard it ignores"
        )
        assert "labor_supply_per_capita" in called

    def test_every_condition_source_names_something_that_exists(self):
        """
        A `source:` pointer that outlives the call it names is this repo's most
        repeated failure. Line 117 named `feasibility_check` for one commit
        after the module stopped calling it.
        """
        import importlib
        import re
        checked = 0
        for name, c in CONDITIONS.items():
            src = re.sub(r"\s*\(.*\)$", "", c["source"]).strip()
            if "/" not in src:                      # "this module, ..." — no target
                continue
            mod_path, _, fn = src.rpartition(".")
            mod = importlib.import_module("hours_eoh." + mod_path.replace("/", "."))
            assert hasattr(mod, fn), f"{name}: {src} does not exist"
            checked += 1
        assert checked >= 2, (
            "the scan matched nothing and would pass vacuously — the "
            "`exercised alongside passes` discipline"
        )


class TestConditionTwoIsReachableInBothDirections:
    """
    A condition that cannot fail is not a condition. `delivery_pays` was True
    everywhere for one commit — not because the apparatus always paid, but
    because the default `capital_stock_teh` was 2,000 TOTAL over 1e6 people,
    i.e. 0.002 per capita. There was no apparatus to fail to pay for, and every
    test in this file passed.
    """

    def test_capital_stock_teh_is_TOTAL_not_per_capita(self):
        """
        The units error, pinned. `overbuild_check` divides by population itself,
        and its own docstring says "Total apparatus capital".
        """
        from hours_eoh.data import CAPITAL_STOCK_DEFAULT
        r = stability_at(0.40)
        assert r["capital_stock_teh"] == CAPITAL_STOCK_DEFAULT
        assert r["capital_stock_teh"] > 1.0e8, (
            "a default small enough to be a per-capita figure means the "
            "apparatus is effectively absent and condition 2 cannot bind"
        )

    def test_delivery_pays_holds_at_the_reference_capital(self):
        assert stability_at(0.40)["delivery_pays"] is True

    def test_delivery_pays_FAILS_when_the_apparatus_is_overbuilt(self):
        """
        The other direction. At ~25,000 TEH/capita the apparatus costs more than
        it abates — the recorded overbuild threshold — and the condition must
        say so.
        """
        r = stability_at(0.40, capital_stock_teh=2.5e10)
        assert r["delivery_pays"] is False
        assert r["overbuild_verdict"] == "overbuilt"
        assert "delivery_pays" in r["failing"]
        assert r["stationary"] is False

    def test_the_abated_standard_is_refused_with_its_reason(self):
        """
        `collapsed` is F_a·(1 − a) — already abated — and `core/autarky` refuses
        it as an autarky reference in as many words. A standard with the
        apparatus baked into it cannot be the counterfactual FOR the apparatus.
        """
        assert "collapsed" not in STANDARDS
        with pytest.raises(ValueError):
            stability_at(0.40, standard="collapsed")
        with pytest.raises(ValueError):
            stability_at(0.40, standard="nonsense")

    def test_the_exclusion_is_explained_where_a_reader_will_look(self):
        import hours_eoh.scenarios.arc_stability as mod
        doc = " ".join((mod.__doc__ or "").split())
        src = " ".join(open(mod.__file__).read().split())
        assert "autarky reference" in src
        assert "collapsed" in src


class TestItIsComparableToTheNeighbouringQuestions:
    """
    The module docstring names `corridor` and `canonical_arc_trajectory` as the
    neighbouring questions. A pointer a reader cannot follow is worse than none —
    the `resolves_by`-naming-a-source-not-a-field lesson — so both are exercised.
    """

    def test_both_neighbours_are_importable_and_runnable(self):
        from hours_eoh.research.corridor import survival_floor_epsilon  # noqa: F401
        from hours_eoh.scenarios.long_run import canonical_arc_trajectory
        r = canonical_arc_trajectory(n_periods=3)
        assert r["n_periods"] == 3

    def test_stability_is_strictly_stronger_than_survivability(self):
        """
        THE RELATIONSHIP, and it is the reason the two bands may differ without
        contradicting. Corridor asks which ε are SURVIVABLE; this asks where the
        system could STAND STILL, which additionally requires the delivery cost
        to be covered. So the stationary band must start at or above corridor's
        floor at the same standard — and stating the standard is what makes that
        legible instead of looking like a disagreement.
        """
        from hours_eoh.core.eoh_generation import total_eoh
        from hours_eoh.research.corridor import survival_floor
        for standard in STANDARDS:
            # The same path `utils/corridor_cmd._band` takes.
            eoh = total_eoh(epsilon=0.40, population=1.0e6,
                            personal_standard=standard)
            floor = survival_floor(eoh, 1.0e9)["epsilon_floor"]
            band = stationary_band(standard=standard)
            assert band["lower"] >= floor - 1e-9, (
                f"at {standard!r} the stationary band starts BELOW the survival "
                f"floor ({band['lower']} < {floor}), which would mean the system "
                f"can stand still where it cannot survive"
            )

    def test_the_band_is_reported_at_every_admissible_standard(self):
        """Both corners survive rather than one being picked — SCOPES precedent."""
        by = band_by_standard()
        assert set(by) == set(STANDARDS)
