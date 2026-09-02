"""
Tests for scenarios/obligation_accounts.py — Phase 0 of the one-obligation
reframe.

Discipline, following the modules this sits beside:
  * the partition must CLOSE exactly — a presentation that loses or invents a
    quantity is not a presentation of anything;
  * findings are asserted as ORDERINGS and SIGNS where the level is calibration
    that has moved before;
  * `TestAccountsChangeNothing` pins that this is reporting only.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import CARE_AUTOMATION_FLOOR, PERSONAL_EOH_COMPONENTS
from hours_eoh.scenarios.obligation_accounts import (
    ACCOUNTS,
    anchor_sensitivity,
    accounts_arc,
    accounts_report,
    automation_uniformity_check,
    delivery_crossover,
    obligation_accounts,
)

ARC = (0.0, 0.40, 0.99)


class TestThePartitionCloses:
    """
    The integrity condition. This module re-presents quantities `total_eoh`
    already computes, so the three accounts must sum to its total EXACTLY. A
    presentation that loses or invents a quantity is not a presentation.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_three_accounts_sum_to_the_gross_total(self, epsilon):
        r = obligation_accounts(epsilon)
        assert r["reconciles"] is True
        assert r["obligation"] + r["delivery"] + r["stock"] == pytest.approx(
            r["gross_total"], rel=1e-12
        )

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_accounts_are_the_domains_regrouped_not_recomputed(self, epsilon):
        """
        Bound to `total_eoh`'s own keys on both sides, so the two cannot drift.
        If the domains are ever recomputed here rather than regrouped, this
        fails — the shadow-constant lesson applied to a derived quantity.
        """
        d = total_eoh(epsilon=epsilon)
        r = obligation_accounts(epsilon)
        assert r["obligation"] == pytest.approx(
            d["personal"] + d["knowledge_civilisational"]
        )
        assert r["delivery"] == pytest.approx(
            d["infrastructure"] + d["knowledge_apparatus"]
        )
        assert r["stock"] == pytest.approx(d["ecological"])

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            obligation_accounts(1.5)
        with pytest.raises(ValueError):
            automation_uniformity_check(-0.1)


class TestTheShapeTheFourWaySumHides:

    def test_the_obligation_is_nearly_flat_and_delivery_is_not(self):
        """
        THE FINDING, as an ordering rather than a level. What must be met barely
        moves across the arc; what meeting it costs grows by more than an order
        of magnitude. Adding the two into one total hides exactly that.
        """
        arc = accounts_arc()
        obligation_growth = arc[-1]["obligation"] / arc[0]["obligation"]
        delivery_growth = arc[-1]["delivery"] / arc[0]["delivery"]
        assert obligation_growth < 1.25, "the obligation should be nearly flat"
        assert delivery_growth > 10.0, "delivery should grow by an order of magnitude"
        assert delivery_growth > 10.0 * obligation_growth

    def test_delivery_over_obligation_rises_monotonically(self):
        ratios = [r["delivery_over_obligation"] for r in accounts_arc()]
        assert ratios == sorted(ratios)

    def test_delivery_approaches_but_no_longer_crosses_the_obligation(self):
        """
        THE CLAIM THAT MOVED WHEN A PLACEHOLDER GOT DATA (2026-09-01), and it is
        the cleanest example in the repo. This asserted a crossover late in the
        arc, and there WAS one at 1.0029. Then AGE_WEIGHT_CHILD took the MTUS
        measurement for ages 6-14 — raising the obligation — and the knowledge
        fixed point re-anchored -9.94% with it, cutting the apparatus term.
        Both push the ratio down and it now peaks at 0.90.

        The SHAPE is what survives and is what is asserted: delivery grows by
        more than an order of magnitude against a nearly flat obligation. The
        crossover was a LEVEL, and levels move.
        """
        c = delivery_crossover()
        assert c["crossover_epsilon"] is None
        assert c["ratio_at_zero"] < 0.10
        assert 0.7 < c["ratio_at_top"] < 1.0

    def test_the_crossover_is_not_reported_as_a_failure(self):
        """
        It is where the apparatus's entropy debt equals the obligation it
        reduces. Whether that is acceptable depends on how much it ABATES, which
        this account does not carry — so the module must say so rather than let
        a reader infer a verdict.
        """
        assert "Not a failure condition" in delivery_crossover()["note"]
        assert "abates" in delivery_crossover()["note"]


class TestTheStockAccountIsSeparateAndBlockIIIPutsItInTheBase:
    """
    THE CORRECTION, and it is why this is not merely a rename of
    `total_eoh(basis="final")`. Legacy damage is not a forward obligation.
    """

    def test_no_stock_ships_by_default(self):
        """Phase 4d/4e/4f: the ecological domain carries stocks and none ships."""
        for r in accounts_arc():
            assert r["stock"] == 0.0
            assert r["base_includes_stock"] is False

    def test_a_supplied_stock_lands_in_the_stock_account(self):
        r = obligation_accounts(0.40, thermal_obligation=1.0e8)
        assert r["stock"] == pytest.approx(1.0e8)
        assert r["reconciles"] is True

    def test_block_iii_base_absorbs_the_stock_and_the_accounts_do_not(self):
        """
        THE DIFFERENCE, measured rather than argued. `total_base` rises by the
        full stock, so a thermal obligation reads as though the system owed more
        going FORWARD. The obligation account does not move.
        """
        plain = obligation_accounts(0.40)
        stocked = obligation_accounts(0.40, thermal_obligation=1.0e8)

        assert stocked["obligation"] == pytest.approx(plain["obligation"]), (
            "a legacy stock must not raise the forward obligation"
        )
        assert stocked["total_base_block_iii"] - plain["total_base_block_iii"] == (
            pytest.approx(1.0e8)
        ), "Block III's base absorbs the whole stock — which is the defect"
        assert stocked["base_includes_stock"] is True
        assert stocked["base_minus_accounts_oblig"] == pytest.approx(1.0e8)


class TestTheCareContradiction:
    """
    Three statements this repo makes about care's automatability. Two agree and
    the third does not, and nothing compared them until now.
    """

    def test_the_two_layers_disagree(self):
        u = automation_uniformity_check(0.99)
        assert u["agrees"] is False
        assert u["implied_human_fraction"] > u["uniform_human_fraction"]

    def test_the_disagreement_is_an_order_of_magnitude(self):
        """
        SIGN and MAGNITUDE-CLASS. The exact factor moves with the care share and
        the floor, both of which are pinned elsewhere; that it is large is the
        claim.
        """
        assert automation_uniformity_check(0.99)["understatement_factor"] > 5.0

    def test_it_is_bound_to_both_sources_and_restates_neither(self):
        """
        The shadow-literal lesson: the check must READ the care share and the
        floor rather than carry its own copies, or it can agree with a source
        that has moved.
        """
        u = automation_uniformity_check(0.99)
        assert u["care_share_of_personal"] == PERSONAL_EOH_COMPONENTS["care"]["share"]
        assert u["care_automation_floor"] == CARE_AUTOMATION_FLOOR

    def test_they_agree_at_zero_automation_which_is_the_control(self):
        """
        At ε=0 nothing is automated, so a floor on automation cannot bite and
        the two accounts MUST coincide. If they disagreed here the check would
        be measuring an arithmetic artefact rather than the contradiction.
        """
        u = automation_uniformity_check(0.0)
        assert u["uniform_human_fraction"] == pytest.approx(1.0)
        assert u["implied_human_fraction"] == pytest.approx(1.0)
        assert u["agrees"] is True

    def test_care_is_the_least_abatable_component(self):
        """
        Block II's independent statement, which is why the floor is not an
        isolated assertion. If care ever stops being least abatable, the
        contradiction's second leg goes with it.
        """
        ab = {k: v["abatability"] for k, v in PERSONAL_EOH_COMPONENTS.items()}
        assert min(ab, key=lambda k: ab[k]) == "care"
        assert PERSONAL_EOH_COMPONENTS["care"]["share"] > 0.5


class TestTheAccountsAreDeclared:

    def test_every_account_says_what_distinguishes_it(self):
        """
        A category nobody has written down is a category nobody has audited —
        the `TERM_BASIS` precedent.
        """
        assert set(ACCOUNTS) == {"obligation", "delivery", "stock"}
        for name, entry in ACCOUNTS.items():
            for field in ("question", "domains", "exists_because", "epsilon_behaviour"):
                assert entry[field].strip(), f"{name}.{field}"

    def test_the_report_runs_and_states_its_status(self):
        rep = accounts_report()
        assert rep["reporting_only"] is True
        assert rep["arc"] and rep["here"]["reconciles"] is True
        assert "delivery cost" in rep["verdict"]


class TestAccountsChangeNothing:
    """
    REPORTING ONLY. This module must not move a single shipped number — it
    exists to make a proposed reframing arguable BEFORE it is adopted, and a
    presentation that changed behaviour would be the adoption.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_total_eoh_is_untouched_by_importing_the_accounts(self, epsilon):
        before = total_eoh(epsilon=epsilon)["total"]
        obligation_accounts(epsilon)
        accounts_report(epsilon)
        assert total_eoh(epsilon=epsilon)["total"] == before

    def test_the_module_declares_itself_reporting_only(self):
        import hours_eoh.scenarios.obligation_accounts as mod
        assert "REPORTING ONLY" in (mod.__doc__ or "")

    def test_it_does_not_take_the_charter_decision(self):
        """
        Whether `total_eoh` should RETURN this shape is a charter question and
        Phase 0 does not answer it. If this module ever starts asserting the
        reframe rather than presenting it, that admission goes first.
        """
        import hours_eoh.scenarios.obligation_accounts as mod
        doc = mod.__doc__ or ""
        assert "WHAT THIS DOES NOT SETTLE" in doc
        assert "charter decision" in doc


class TestTheAnchorMoveIsMeasuredBeforePhase2:
    """
    Phase 2 de-risking. The care contradiction's fix moves the knowledge anchor,
    and this measures how far BEFORE the change is committed to rather than
    after — the anchor has been re-derived six times and every previous move was
    tiny, which is exactly the reason to check whether "tiny" still holds.
    """

    def test_the_uniform_branch_reproduces_the_shipped_constant(self):
        """
        THE CONTROL, and without it the comparison is worthless. This module
        reimplements the fixed point; if the reimplementation did not land
        exactly on `KNOWLEDGE_EOH_BASE`, the non-uniform figure would be
        measuring the reimplementation's drift instead of the change.
        """
        r = anchor_sensitivity()
        assert r["converged"] is True
        # THE CONTROL INVERTED ON ADOPTION (2026-09-01). Before the flip the
        # UNIFORM branch had to reproduce the shipped anchor; now the
        # per-component one does, and the uniform branch must NOT — which is a
        # stronger check than before, because it says the flip actually reached
        # the constant rather than only the code.
        assert r["non_uniform_reproduces_shipped"] is True
        assert r["uniform_reproduces_shipped"] is False
        assert r["base_non_uniform"] == pytest.approx(r["shipped_base"], rel=1e-9)

    def test_the_control_flag_can_report_FALSE(self):
        """
        THE BITE THAT WAS MISSING. Hard-coding `uniform_reproduces_shipped` to
        True passed every test here, because the fact was independently checked
        and the FLAG was not — the reported-vs-applied pattern (`psi` vs
        `psi_applied`). A flag that cannot report False is a flag nobody is
        checking, so the reference is injectable purely to prove it can.
        """
        wrong = anchor_sensitivity(shipped_base=1.0e8)
        assert wrong["uniform_reproduces_shipped"] is False
        assert wrong["base_move"] == pytest.approx(anchor_sensitivity()["base_move"]), (
            "the reference must affect only the control flag, never the measured move"
        )

    def test_the_move_is_large_and_downward(self):
        """
        SIGN and MAGNITUDE-CLASS. Flooring care raises the human labour the model
        requires at every ε above zero, so the implied ε rises and the base falls
        with it. The exact level moves with the care share and the floor; that it
        is an order of magnitude beyond every previous re-anchor is the claim.
        """
        r = anchor_sensitivity()
        assert r["base_move"] < 0.0, "the base must fall"
        assert abs(r["base_move"]) > 0.05, (
            "every previous re-anchor was +0.13% or smaller; if this ever drops "
            "into that range, Phase 2 stops being a calibration change and the "
            "plan should be revisited"
        )
        assert r["epsilon_non_uniform"] > r["epsilon_uniform"]

    def test_the_labour_at_the_top_of_the_arc_differs_by_an_order_of_magnitude(self):
        """
        The substantive consequence, not the calibration one: the difference
        between "labour has effectively ended" and "most of a month of care work
        per person per year still remains".
        """
        top = anchor_sensitivity()["labour_at_top"]
        assert top["non_uniform"] > 4.0 * top["uniform"]

    def test_it_declares_the_move_a_lower_bound(self):
        """
        Only care is floored here. `PERSONAL_EOH_COMPONENTS` gives health an
        abatability of 0.60 and nutrition 0.85, so a fuller treatment floors more
        components and moves the anchor further in the same direction.
        """
        r = anchor_sensitivity()
        assert r["move_is_a_lower_bound"] is True
        assert "LOWER bound" in r["verdict"]

    def test_it_changes_nothing(self):
        from hours_eoh.data import KNOWLEDGE_EOH_BASE
        before = KNOWLEDGE_EOH_BASE
        anchor_sensitivity()
        from hours_eoh.data import KNOWLEDGE_EOH_BASE as after
        assert after == before
