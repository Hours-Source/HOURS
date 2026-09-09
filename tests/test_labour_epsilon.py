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
        THE BUG THIS TEST EXISTS FOR. `CAPITAL_STOCK_DEFAULT` is stated at the 1M
        reference population and does not scale, so computing the obligation at
        the US population gives 335M people the capital of 1M and the fixed point
        collapses to zero. Pinned by the ANSWER, not by reading the source.
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
