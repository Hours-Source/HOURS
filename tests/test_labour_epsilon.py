"""
The second instrument on ε — `reference/obligation_work` + `scenarios/labour_epsilon`.

WHAT IS AT STAKE. Until 2026-09-09 the framework had exactly one reading of ε
against a real economy, off the BEA asset inventory, and that reading is the
page's most exposed empirical claim. This is the independent one: ATUS time
diaries instead of asset valuations, and no currency anywhere in the chain.

WHAT THESE TESTS PIN. Not the level. They pin that the comparison **can report
disagreement** — a cross-check that can only conclude "they agree" is not a
cross-check — that the labour route stays currency-free, that the frame is
carried correctly, and that `reconciling_rate` never becomes a recommendation.

THE FRAME TEST EXISTS BECAUSE THE BUG HAPPENED. The first working version passed
the US population into `total_eoh`, which is stated at the 1M reference frame for
its extensive constants, and the fixed point collapsed to exactly zero. The
module's own docstring had claimed the frame was declared at every step.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import REFERENCE_FRAME_POPULATION
from hours_eoh.reference import obligation_work as OW
from hours_eoh.scenarios import labour_epsilon as LE


class TestTheAttributionIsTheOneJudgement:

    @pytest.mark.parametrize("g", OW.OBLIGATION_GROUPS + OW.BROAD_GROUPS, ids=lambda g: g["soc"])
    def test_every_admitted_group_carries_a_basis_and_a_domain(self, g):
        assert len(g["basis"]) > 40, f"SOC {g['soc']} admitted without an argument"
        assert g["domain"], f"SOC {g['soc']} names no domain it discharges"

    @pytest.mark.parametrize("g", OW.EXCLUDED_GROUPS, ids=lambda g: g["soc"])
    def test_every_exclusion_carries_a_reason(self, g):
        assert len(g["reason"]) > 30

    def test_the_groups_partition_without_overlap(self):
        admitted = {g["soc"] for g in OW.OBLIGATION_GROUPS} | {g["soc"] for g in OW.BROAD_GROUPS}
        excluded = {g["soc"] for g in OW.EXCLUDED_GROUPS}
        assert not (admitted & excluded), "a group is both admitted and excluded"

    def test_every_major_group_in_the_registry_is_decided(self):
        """
        No group may be silently absent. An occupation nobody classified counts
        as excluded without anyone having argued for it.
        """
        present = set(OW.employment_by_major_group())
        decided = ({g["soc"] for g in OW.OBLIGATION_GROUPS}
                   | {g["soc"] for g in OW.BROAD_GROUPS}
                   | {g["soc"] for g in OW.EXCLUDED_GROUPS})
        assert present <= decided, f"undecided major groups: {sorted(present - decided)}"

    def test_core_is_narrower_than_broad(self):
        assert OW.obligation_share("core")["share"] < OW.obligation_share("broad")["share"]

    def test_the_employment_total_is_the_us_workforce(self):
        assert OW.obligation_share("core")["total_employment_k"] == pytest.approx(157_800, rel=0.01)

    def test_an_unknown_scope_raises(self):
        with pytest.raises(ValueError, match="scope must be"):
            OW.obligation_share("everything")

    def test_the_hours_assumption_is_declared(self):
        """The share is measured in HEADS and used as HOURS. That has a
        direction and the module has to say which."""
        assert "over-counting" in OW.obligation_share("core")["hours_assumption"]


class TestTheFrameIsCarriedNotAssumed:
    """
    RECURRING FAILURE MODE 6, and it bit this module during construction. ATUS
    measures per person 15+; the package's extensive constants are stated at the
    1M reference population. Two different frames in one calculation.
    """

    def test_the_atus_conversion_is_applied(self):
        m = LE.measured_hours()
        assert 0.7 < m["share_15_plus"] < 0.9
        assert m["unpaid_per_capita"] == pytest.approx(
            m["unpaid_per_15plus"] * m["share_15_plus"], rel=1e-12
        )
        assert m["unpaid_per_capita"] < m["unpaid_per_15plus"], "per capita must be the smaller"

    def test_the_obligation_is_computed_at_the_reference_frame(self):
        """
        THE BUG THIS TEST EXISTS FOR — and its stated CAUSE is retracted.

        It read: "`CAPITAL_STOCK_DEFAULT` is stated at the 1M reference
        population and does not scale, so computing the obligation at the US
        population gives 335M people the capital of 1M and the fixed point
        collapses to zero." That was true when written; the 2026-09-16 capital
        frame repair falsified it — `resolve_capital_stock` now scales the stock
        with the population it is given. MEASURED 2026-09-18: per-capita
        `total_eoh` is frame-invariant to the last bit, ratio 1.0000000000
        between the 1M and 335M frames.

        THE ASSERTION IS UNCHANGED AND STILL EARNS ITS PLACE, because it is
        pinned by the ANSWER rather than by the mechanism: ε collapsing to zero
        is the symptom of ANY frame error here, whatever causes it. Only the
        explanation moved, and the same retraction was made in the source on
        2026-09-18.
        """
        assert LE.labour_epsilon("core")["epsilon"] > 0.05, (
            "ε collapsed — the obligation is being computed at the wrong frame"
        )

    def test_population_is_paired_data_and_not_a_free_knob(self):
        """
        WRITTEN AFTER THE TEST THAT ASSUMED OTHERWISE FAILED. `population` looks
        like a frame parameter and is not: it is the population the survey's own
        15+ count belongs to, and the two travel together. Asserting a smaller
        one asserts more adults than people, and it silently drove ε to zero
        before this guard existed.
        """
        with pytest.raises(ValueError, match="more adults than people"):
            LE.labour_epsilon("core", population=200e6)

    def test_a_larger_population_lowers_the_adult_share_and_raises_epsilon(self):
        """The direction, so the pairing is checked rather than merely guarded."""
        a = LE.labour_epsilon("core", population=335e6)["epsilon"]
        b = LE.labour_epsilon("core", population=400e6)["epsilon"]
        assert b > a, "diluting the adult share must leave less measured human labour"


class TestTheLabourRouteIsCurrencyFree:
    """
    THE ASYMMETRY THAT MAKES THIS WORTH BUILDING. The capital route needs a
    valuation doctrine, a currency conversion and a scope of capital. This needs
    one attribution. That is the census-versus-valuation claim, observed.
    """

    def test_no_currency_is_used(self):
        assert LE.labour_epsilon("core")["currency_used"] is None

    def test_the_module_never_imports_the_conversion(self):
        import ast, inspect, textwrap
        tree = ast.parse(textwrap.dedent(inspect.getsource(LE.labour_epsilon)))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        assert "conversion_band" not in names and "currency_per_teh" not in names

    def test_the_judgement_counts_are_reported(self):
        j = LE.instrument_comparison()["judgements"]
        assert j["labour"] == 1 and j["capital"] == 3


class TestTheComparisonCanDisagree:
    """MODE 9. A cross-check that cannot report disagreement is not one."""

    def test_the_shipped_comparison_is_adjacent(self):
        c = LE.instrument_comparison()
        assert c["verdict"] == "ADJACENT", (
            f"the instruments moved to {c['verdict']} (gap {c['gap']:.4f}) — the "
            "page's corroboration claim has to change with it"
        )
        assert c["gap"] < 0.05

    def test_it_reports_divergent_when_the_instruments_disagree(self):
        """Forced by pushing the capital route somewhere the labour route is not."""
        c = LE.instrument_comparison(capital_rates=(2.0, 3.0))
        assert c["verdict"] == "DIVERGENT" and c["gap"] > 0.05

    def test_it_reports_overlap_when_the_intervals_meet(self):
        c = LE.instrument_comparison(capital_rates=(24.0, 40.0))
        assert c["verdict"] == "OVERLAP" and c["gap"] == 0.0

    def test_all_three_verdicts_are_reachable(self):
        """Stated as one assertion so a future edit cannot quietly lose a branch."""
        got = {LE.instrument_comparison(capital_rates=r)["verdict"]
               for r in ((2.0, 3.0), (24.0, 40.0), (15.94, 23.17))}
        assert got == {"DIVERGENT", "OVERLAP", "ADJACENT"}

    def test_the_shared_denominator_is_declared(self):
        c = LE.instrument_comparison()
        assert "total_eoh" in c["shared_denominator"]


class TestTheReconcilingRateIsADiagnosticNotAValue:

    def test_it_says_it_is_not_a_recommendation(self):
        r = LE.reconciling_rate()
        assert r["is_a_recommendation"] is False
        assert "calibrating" in r["note"]

    def test_it_reports_whether_it_lands_inside_the_band(self):
        r = LE.reconciling_rate()
        assert r["inside_band"] is (r["band_low"] <= r["reconciling_rate"] <= r["band_high"])

    def test_the_rate_it_finds_actually_reconciles(self):
        from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory
        r = LE.reconciling_rate()
        got = epsilon_from_inventory(r["reconciling_rate"], scope="government")["epsilon"]
        assert got == pytest.approx(r["target_epsilon"], abs=5e-3)


class TestLabourEpsilonChangesNothing:

    def test_epsilon_falls_as_more_work_is_attributed(self):
        """More obligation labour means less of it done by machines."""
        assert LE.labour_epsilon("core")["epsilon"] > LE.labour_epsilon("broad")["epsilon"]

    def test_the_verdict_is_computed_from_the_intervals(self):
        r = LE.labour_epsilon_report()
        assert f"{r['comparison']['labour']['high']:.3f}" in r["verdict"]
        assert r["adopted"] is False

    def test_it_states_its_own_gaps(self):
        assert len(OW.what_this_cannot_settle()) >= 4

    def test_nothing_in_core_or_land_imports_it(self):
        import pathlib
        import hours_eoh
        root = pathlib.Path(hours_eoh.__file__).resolve().parent
        for name in ("obligation_work", "labour_epsilon"):
            offenders = [
                p.relative_to(root).as_posix()
                for d in ("core", "land")
                for p in (root / d).rglob("*.py")
                if name in p.read_text(encoding="utf-8", errors="ignore")
            ]
            assert not offenders, f"{offenders} import {name}"

class TestTheLabourArmTakesItsDataToo:
    """
    STEP 2 OF MAKING A CASE STUDY REPRODUCIBLE BY SOMEONE ELSE (2026-09-18).

    Step 1 let the CAPITAL instrument take an inventory. On its own that is
    worse than useless for a foreign user: it lets them compare their capital
    against AMERICA's time use and receive a confident ADJACENT verdict about no
    economy. This class pins the half that closes it, and the gate that makes
    the mixed case inexpressible rather than merely discouraged.

    ALL THREE SCALARS OR NONE. A partial supply would divide one jurisdiction's
    unpaid hours by another's adult count. Refused, because a blend returns a
    number and no error.
    """

    def _shipped_inputs(self):
        m = LE.measured_hours()
        return dict(population_15_plus_supplied=m["population_15_plus"],
                    unpaid_per_15plus=m["unpaid_per_15plus"],
                    paid_per_15plus=m["paid_per_15plus"])

    def test_supplying_the_shipped_values_reproduces_the_shipped_reading(self):
        """The sentinel resolves to exactly what it replaced."""
        a = LE.measured_hours()
        b = LE.measured_hours(**self._shipped_inputs())
        for k in ("unpaid_per_capita", "paid_per_capita", "share_15_plus"):
            assert a[k] == pytest.approx(b[k], rel=1e-12)

    def test_a_partial_supply_is_refused_and_names_what_is_missing(self):
        with pytest.raises(ValueError, match="all three"):
            LE.measured_hours(unpaid_per_15plus=100.0)

    def test_the_adults_guard_fires_on_a_SUPPLIED_count(self):
        """
        THE PIN MOST AT RISK. `population` is paired data, guarded by comparing
        it against the survey's 15+ count. A sentinel that took the supplied
        count and skipped the guard would defeat the check for exactly the
        caller most likely to trip it — someone porting the instrument.
        """
        with pytest.raises(ValueError, match="more adults than people"):
            LE.measured_hours(population=200e6, population_15_plus_supplied=270e6,
                              unpaid_per_15plus=100.0, paid_per_15plus=100.0)

    def test_the_survey_year_does_not_date_someone_elses_hours(self):
        assert LE.measured_hours()["year"] is not None
        assert LE.measured_hours(**self._shipped_inputs())["year"] is None

    def test_the_sources_are_reported_on_a_single_reading(self):
        r = LE.labour_epsilon("core")
        assert r["hours_source"] == "shipped_atus"
        assert r["employment_source"] == "shipped_soc"
        r2 = LE.labour_epsilon("core", **self._shipped_inputs(),
                               employment=OW.employment_by_major_group())
        assert r2["hours_source"] == "supplied"
        assert r2["employment_source"] == "supplied"

    def test_both_arms_or_neither(self):
        """
        THE HALF-PORTED COMPARISON, MADE INEXPRESSIBLE. Supplying one arm and
        letting the other fall back to the shipped US table yields a verdict
        about no economy, so it raises instead.
        """
        from hours_eoh.scenarios.capital_retrodiction import capital_by_profile
        inv = capital_by_profile("government", "current_cost")
        with pytest.raises(ValueError, match="BOTH arms or neither"):
            LE.instrument_comparison(inventory=inv)
        with pytest.raises(ValueError, match="BOTH arms or neither"):
            LE.instrument_comparison(**self._shipped_inputs())

    def test_supplying_both_arms_reproduces_the_shipped_verdict(self):
        """NOT VACUOUS: handed back the shipped values, the ported path agrees."""
        from hours_eoh.scenarios.capital_retrodiction import capital_by_profile
        inv = capital_by_profile("government", "current_cost")
        a = LE.instrument_comparison()
        b = LE.instrument_comparison(inventory=inv, **self._shipped_inputs())
        assert a["verdict"] == b["verdict"]
        assert a["gap"] == pytest.approx(b["gap"], rel=1e-12)
        assert a["sources"] == {"capital": "shipped_bea", "labour": "shipped_atus"}
        assert b["sources"] == {"capital": "supplied", "labour": "supplied"}

    def test_the_reconciling_rate_still_converges_when_ported(self):
        """The bisection assumes ε falls as the rate rises; that holds supplied."""
        from hours_eoh.scenarios.capital_retrodiction import capital_by_profile
        inv = capital_by_profile("government", "current_cost")
        a = LE.reconciling_rate("core")["reconciling_rate"]
        b = LE.reconciling_rate("core", inventory=inv, **self._shipped_inputs())["reconciling_rate"]
        assert a == pytest.approx(b, rel=1e-9)

class TestTheVerdictIsAChoiceAndSaysSo:
    """
    THE PUBLISHED ADJACENT WAS ONE CELL OF A GRID (2026-09-18).

    `instrument_comparison` hard-coded `scope="government"` and inherited
    `doctrine="current_cost"`, so it read ONE corner of the capital grid and
    reported the result as a property of the instruments. The capital route
    returns 18 cells precisely BECAUSE its three judgements are undeclared.

    Measured at the US frame: the corner gives ADJACENT at gap 0.046, while 8 of
    the 18 declared cells fall inside the labour band and the full grid
    (0.200-0.757) OVERLAPS it. The corner stays the headline — government /
    current_cost is the most defensible single reading, and switching the
    headline to the framing that AGREES would be calibrating to the answer, the
    failure `reconciling_rate` names in its own docstring. What changes is that
    the grid verdict is reported beside it and the choice is explicit.
    """

    def test_the_corner_is_still_the_headline(self):
        c = LE.instrument_comparison()
        assert c["verdict"] == "ADJACENT"
        assert c["capital"]["scope"] == "government"
        assert c["capital"]["doctrine"] == "current_cost"

    def test_the_grid_verdict_is_reported_beside_it(self):
        g = LE.instrument_comparison()["grid"]
        assert g["available"] is True
        assert g["verdict"] == "OVERLAP"
        assert g["cells_total"] == 18
        assert 0 < g["cells_inside_labour"] < g["cells_total"], (
            "if NO cell or EVERY cell sits inside the labour band, the grid "
            "verdict has stopped discriminating and this pin should be re-read"
        )

    def test_one_declared_judgement_flips_the_verdict(self):
        """
        THE POINT, AS A TEST RATHER THAN A SENTENCE. Doctrine alone moves it:
        every government/historical_cost cell sits inside the labour band, every
        current_cost one sits above it. A comparison whose answer turns on an
        undeclared default was reporting a choice as a finding.
        """
        cur = LE.instrument_comparison(doctrine="current_cost")
        hist = LE.instrument_comparison(doctrine="historical_cost")
        assert cur["verdict"] == "ADJACENT"
        assert hist["verdict"] == "OVERLAP", (
            f"historical cost read {hist['capital']['low']:.4f}-"
            f"{hist['capital']['high']:.4f} against labour "
            f"{hist['labour']['low']:.4f}-{hist['labour']['high']:.4f}"
        )

    def test_scope_moves_it_too_and_is_not_hard_coded(self):
        """A hard-coded scope would make every scope return the same numbers."""
        got = {sc: LE.instrument_comparison(scope=sc)["capital"]["low"]
               for sc in ("productive", "government", "residential")}
        assert len(set(round(v, 9) for v in got.values())) == 3, got

    def test_a_supplied_inventory_has_no_grid_and_says_so(self):
        """The grid is a property of the SHIPPED table, not of anyone's data."""
        from hours_eoh.scenarios.capital_retrodiction import capital_by_profile
        m = LE.measured_hours()
        c = LE.instrument_comparison(
            inventory=capital_by_profile("government", "current_cost"),
            population_15_plus_supplied=m["population_15_plus"],
            unpaid_per_15plus=m["unpaid_per_15plus"],
            paid_per_15plus=m["paid_per_15plus"])
        assert c["grid"]["available"] is False
        assert "no declared scope/doctrine grid" in c["grid"]["note"]

    def test_the_reader_facing_verdict_names_both(self):
        """
        The institution-facing string is where this matters: it is the starting
        conversation, and it must not present a choice as a property.
        """
        v = LE.labour_epsilon_report()["verdict"]
        assert "government/current_cost" in v
        assert "ADJACENT" in v
        assert "OVERLAP across the declared grid" in v
        assert "depends on the scope and doctrine chosen" in v
