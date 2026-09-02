"""
The anchor comparison, and the guards that stop it being rigged.

WHY THESE TESTS ARE SHAPED THIS WAY. A comparison against rivals you model
yourself is the easiest thing in this repository to fake: pick a weak version of
each alternative and the conclusion writes itself. That is the calibrated-to-
target failure at the scale of a module, and it would be undetectable from the
output.

So the tests are mostly about METHOD rather than result — that no rival is
simulated, that each carries its own strongest reading, that an indeterminate
anchor is recorded as indeterminate rather than as unresponsive, and that the
headline claim is COMPUTED from the classification rather than restated beside
it.

THE RESULT ITSELF IS PINNED AS NOT-UNIQUE, deliberately. Mutual credit holds the
same three properties HOURS does. A later edit that quietly makes HOURS the sole
holder is exactly the drift this file exists to catch.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from hours_eoh.research.anchor_determinacy import (
    ANCHORS,
    determinacy_table,
    hours_shock_response,
    the_defensible_claim,
    what_this_does_not_establish,
)

MODULE = (pathlib.Path(__file__).resolve().parent.parent
          / "hours_eoh" / "research" / "anchor_determinacy.py")


class TestNoRivalIsSimulated:
    """
    The central design guard. The moment this module grows a model of gold or
    fiat, the comparison stops being a classification and starts being a
    conclusion fitted to whatever that model does.
    """

    def test_it_measures_only_this_framework(self):
        """
        The guard is "no RIVAL is modelled", not "one import". Reading HOURS'
        own machinery is the point; anything outside `core/` would mean a rival
        had acquired a model.
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = sorted({
            node.module or "" for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("hours_eoh")
        })
        assert all(m.startswith("hours_eoh.core.") for m in imported), (
            f"this module classifies rivals from their definitions and measures "
            f"only HOURS: {imported}"
        )

    def test_no_rival_carries_a_numeric_parameter(self):
        """
        A mining rate or an issuance schedule appearing here means a rival is
        being modelled. The classification needs no number from any of them.
        """
        for a in ANCHORS:
            assert not any(ch.isdigit() for ch in a.supply_is), (
                f"{a.name}: `supply_is` carries a number, which means this has "
                f"stopped being a definitional classification"
            )


class TestEveryRivalGetsItsStrongestReading:
    """The anti-strawman guard, enforced rather than intended."""

    def test_every_anchor_states_what_its_advocates_say(self):
        for a in ANCHORS:
            assert len(a.advocates_say.strip()) > 60, (
                f"{a.name}: a rival entered without its best case is a strawman"
            )

    def test_the_indifferent_anchors_are_given_their_actual_argument(self):
        """
        Gold and bitcoin are not accidentally unresponsive — indifference is the
        property being bought. If their entries ever read as a deficiency, the
        comparison has been tilted.
        """
        for name in ("gold", "bitcoin"):
            a = next(x for x in ANCHORS if x.name == name)
            assert "IS the property" in a.advocates_say or "guarantee" in a.advocates_say

    def test_fiat_discretion_is_stated_as_a_feature(self):
        a = next(x for x in ANCHORS if x.name == "fiat")
        assert "feature" in a.advocates_say.lower()


class TestIndeterminateIsNotUnresponsive:
    """
    The distinction that lets this run without modelling monetary policy. An
    anchor whose issuance is discretionary has no response that follows from
    what it IS — recording that as `responsive=False` would be a claim about
    policy that nobody here is entitled to make.
    """

    @pytest.mark.parametrize("name", ("fiat", "debt money"))
    def test_indeterminate_anchors_carry_none_not_false(self, name):
        a = next(x for x in ANCHORS if x.name == name)
        assert a.determinate is False
        assert a.responsive is None, (
            "None is the honest value: a discretionary response is neither "
            "responsive nor indifferent"
        )

    def test_determinate_anchors_all_state_a_direction(self):
        for a in ANCHORS:
            if a.determinate:
                assert a.responsive is not None


class TestTheClaimIsComputedNotRestated:

    def test_the_claim_names_the_anchors_the_classification_selects(self):
        c = the_defensible_claim()
        for name in c["determinate_responsive_registered"]:
            assert name in c["claim"]
        for name in c["indeterminate"]:
            assert name in c["claim"]

    def test_moving_an_anchor_moves_the_claim(self):
        """
        The restated-figure guard: if the prose were written beside the table
        rather than from it, this would pass while the two disagreed.
        """
        import hours_eoh.research.anchor_determinacy as m
        before = the_defensible_claim()["determinate_responsive_registered"]
        original = m.ANCHORS
        try:
            m.ANCHORS = tuple(x for x in original if x.name != "mutual credit")
            after = the_defensible_claim()["determinate_responsive_registered"]
        finally:
            m.ANCHORS = original
        assert "mutual credit" in before and "mutual credit" not in after


class TestHoursIsNotAlone:
    """
    PINNED AS NOT-UNIQUE. Mutual credit registers obligation bilaterally at the
    moment it is incurred, and its base moves with activity — the same three
    properties. The honest differentiator is SCALE, which is stated in its own
    row, not structure.

    A future edit that makes HOURS the sole holder of all three is the drift
    this test exists to catch.
    """

    def test_two_anchors_hold_all_three_properties(self):
        holders = the_defensible_claim()["determinate_responsive_registered"]
        assert set(holders) == {"mutual credit", "HOURS"}

    def test_the_module_says_so_rather_than_implying_uniqueness(self):
        c = the_defensible_claim()
        assert "mutual credit and HOURS" in c["claim"]

    def test_the_differentiator_against_mutual_credit_is_stated(self):
        a = next(x for x in ANCHORS if x.name == "mutual credit")
        row = next(r for r in determinacy_table() if r["anchor"] == "mutual credit")
        assert "bilateral" in a.supply_is
        assert row["registered"] is True


class TestTheMeasuredRowIsMeasured:

    def test_hours_responds_to_labour_capacity(self):
        r = hours_shock_response()
        assert r["responds_to_labour"] is True
        assert r["shocks"]["labour_halves"]["minting_change"] < -0.3

    def test_the_unmet_obligation_is_reported_not_absorbed(self):
        r = hours_shock_response()
        assert r["shocks"]["labour_halves"]["deferred"] > 0.0

    def test_the_ecological_zero_is_reported_because_it_is_where_this_loses(self):
        """
        Phases 4e/4f put the recurring ecological obligation in the Ground Use
        Fee, off this path. A comparison that omitted its own worst axis would
        be the rigged version of itself.
        """
        r = hours_shock_response()
        eco = r["shocks"]["ecosystem_halves"]
        assert eco["minting_change"] == pytest.approx(0.0, abs=1e-12)
        assert r["responds_to_ecosystem"] is False

    def test_the_frame_uses_employment_not_working_age(self):
        """
        Labour supply must not be working-age population times an
        hours-per-EMPLOYED-worker figure; that assumes full employment.
        """
        default = hours_shock_response()
        full = hours_shock_response(employment_rate=1.0)
        assert full["frame"]["labour_eoh"] > default["frame"]["labour_eoh"]


class TestTheThreeLimitsThatWereNarrowed:
    """
    Three of the five stated limits turned out to be cheap to narrow. None is
    closed — each is now a SCOPED statement with its caveat attached, which is
    the difference between a limit and an excuse.
    """

    def test_the_ecological_zero_is_one_path_not_the_system(self):
        from hours_eoh.research.anchor_determinacy import ecological_response_by_path
        r = ecological_response_by_path()
        assert r["base_responds"] is False, "the pipeline finding stands"
        assert r["fee_responds"] is True, "and the obligation did not vanish"
        assert r["fee_obligation_ratio"] > 1.5, (
            "halving ecosystem health should materially raise what the fee "
            "carries; if it stops doing so the partition has quietly emptied"
        )

    def test_registration_is_unit_elastic_on_the_money_supply(self):
        from hours_eoh.research.anchor_determinacy import registration_leverage
        r = registration_leverage()
        assert r["is_unit_elastic"] is True
        assert r["elasticity"] == pytest.approx(1.0, rel=1e-9)

    def test_the_capture_reading_is_stated_beside_the_defence(self):
        """
        The two readings are one mechanism and must travel together: a module
        that reported only the hole-digger defence would be advocacy.
        """
        from hours_eoh.research.anchor_determinacy import registration_leverage
        doc = (registration_leverage.__doc__ or "")
        assert "hole-digger" in doc and "controls the money supply" in doc

    def test_the_floor_claim_strengthens_and_says_it_is_internal(self):
        from hours_eoh.research.anchor_determinacy import floor_claim_across_the_arc
        r = floor_claim_across_the_arc()
        assert r["monotone_non_decreasing"] is True
        assert r["gain"] > 2.0
        assert r["is_an_internal_consistency_result"] is True
        assert "not a claim about market exchange" in r["verdict"]


class TestTheLimitsAreStated:

    def test_it_refuses_to_rank(self):
        c = the_defensible_claim()
        assert "normative" in c["and_this_is_not_a_ranking"].lower()

    def test_the_named_gaps_include_the_ones_that_hurt(self):
        limits = " ".join(what_this_does_not_establish()).lower()
        for gap in ("exchange", "ecosystem", "capture", "not modelled at all"):
            assert gap in limits, f"missing stated limit: {gap}"

    def test_registration_capture_is_named_as_untested(self):
        limits = " ".join(what_this_does_not_establish())
        assert "controls the money supply" in limits
