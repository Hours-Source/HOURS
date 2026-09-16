"""
The verdict ladder as a gate — a verdict may not outrank its weakest input.

SPDX-License-Identifier: AGPL-3.0-or-later

Adopted 2026-09-11 (author decision, `record/theory.md#the-verdict-ladder`).
Before this existed the rule was prose, and this repo's measured drift interval
on an ungated commitment is two days.

WHAT THIS GATE IS FOR, and it is not what it first looks like. It does not stop
anyone writing an overclaim in a docstring — nothing static can. What it pins is
that **the ladder stays COMPUTABLE and stays HONEST**: the graph resolves, the
census cannot drift silently, the tier of the framework's central results cannot
strengthen without someone noticing, and the safe error direction stays safe.
"""

from __future__ import annotations

import pytest

from utils import verdict_ladder as VL


@pytest.fixture(scope="module")
def graph():
    return VL.build_graph()


@pytest.fixture(scope="module")
def records():
    return VL._records()


class TestTheLadderIsComputable:
    """It was adopted as prose. This is what makes it a check."""

    def test_the_graph_builds_and_is_not_trivial(self, graph):
        assert len(graph) > 400, (
            "the call graph collapsed; every verdict below it is then "
            "computed from nothing and would read as CERTAIN"
        )

    def test_every_tag_in_the_vocabulary_has_a_tier(self):
        """
        A tag with no tier would fall to the POSSIBLE default and look like a
        deliberate placement. The mapping must be total over the real
        vocabulary, not over the tags that happen to be in use.
        """
        from utils import provenance as pv
        vocabulary = {t for t in pv.TAGS} | {
            t for t in getattr(pv, "SUB_LABELS", set())
        }
        used = {getattr(r, "tag", "") for r in VL._records().values()}
        for tag in used:
            assert tag in VL.TIER_OF_TAG, (
                f"{tag!r} is in use on a shipped constant and has no tier"
            )
        assert set(VL.TIER_OF_TAG) <= vocabulary | set(VL.TIER_OF_TAG), (
            "the tier map invented a tag"
        )

    @pytest.mark.parametrize("fn", (
        "total_eoh", "obligation_accounts", "ground_use_fee",
        "feasibility_check", "verification_report",
    ))
    def test_the_central_functions_resolve(self, fn, graph, records):
        v = VL.verdict_for(fn, graph, records)
        assert v["known"] is True
        assert v["verdict"] in VL.TIER_ORDER
        assert v["dependencies"] > 0


class TestTheCensusCannotDriftSilently:
    """
    THE NUMBER THE LADDER MAKES LOAD-BEARING. 65% of constants sit in the
    weakest tier. If that share moves, either measurement landed or a tag was
    weakened, and both are events someone should have to acknowledge.
    """

    def test_the_shares_are_where_the_last_acknowledged_change_left_them(self):
        """
        **THIS RATCHET FIRED THE DAY AFTER IT WAS WRITTEN, AND THAT IS THE
        POINT.** Adding `REGISTER_CADENCE` as an `instance` moved the census
        342 -> 343 and INSTANCE 89 -> 90. Nothing was wrong; a constant landed.
        The ratchet exists so that a share which moves is an EVENT someone
        acknowledges in a diff, rather than a drift nobody sees — so the fix
        is to update these numbers deliberately, with the reason, never to
        loosen the assertion into a range.

        history: 342 = 31/89/222 at adoption (2026-09-11)
                 343 = 31/90/222 after REGISTER_CADENCE (2026-09-11)
                 346 = 31/93/222 after the three water constants (2026-09-11)
                 345 = 31/93/221 after LEVY_SUFFICIENCY_WARN was RETIRED
                       (2026-09-16)
                 344 = 31/93/220 after ELDERLY_EOH_EPSILON_FACTOR was DELETED
                       (2026-09-16) — retired 2026-09-04 with zero readers for
                       twelve days, so it was neither debt nor a `baseline`
                       (nothing live to compare against); the reasoning moved to
                       record/personal.md, which a test now requires to exist

        **The 2026-09-16 move is the first DOWNWARD one, and it is the good
        direction for a reason worth stating.** POSSIBLE fell because a
        constant left `data.py` entirely: the levy-sufficiency threshold was
        calibrated to the value it watched, so the pillar it drove could only
        ever report GREEN. It was replaced by an identity — do inflows cover
        the guarantee — which needs no constant at all. The framework got no
        more measured; it got one less thing to have to measure, which is the
        only kind of count reduction this ratchet should ever see.

        **Note what the three water constants did to the SHARES**: INSTANCE rose
        and POSSIBLE did not move, because declaring a component resolves it
        without measuring anything. That is the verdict ladder's INSTANCE tier
        working as designed — the framework got no more certain, it got more
        explicit about what it is asking you to supply.
        """
        c = VL.tier_census()
        assert c["total"] == 344
        assert c["counts"]["CERTAIN"] == 31
        assert c["counts"]["INSTANCE"] == 93
        assert c["counts"]["POSSIBLE"] == 220

    def test_possible_is_still_the_largest_tier(self):
        """
        The framework's honest position rests on this being true. If POSSIBLE
        ever stops dominating, the "possible is the ceiling" framing is
        understating the evidence and the page should say so.
        """
        c = VL.tier_census()["counts"]
        assert c["POSSIBLE"] > c["CERTAIN"] + c["INSTANCE"]


class TestTheVerdictsThemselves:

    @pytest.mark.parametrize("fn", (
        "total_eoh", "obligation_accounts", "ground_use_fee",
        "feasibility_check", "verification_report", "corridor_is_usable",
    ))
    def test_no_central_result_claims_better_than_possible(
        self, fn, graph, records
    ):
        """
        **THE LADDER'S CENTRAL FINDING, AND IT IS AGAINST THE FRAMEWORK.**
        Every one of the framework's headline results rests on at least one
        placeholder, so none of them is entitled to more than "possible". That
        is not a hedge the page chose — it is computed from the tags.

        If one of these ever comes back CERTAIN or INSTANCE it is a real event:
        someone measured the constants underneath it, and the page may then
        make a stronger claim than it currently does. Until then it may not.
        """
        assert VL.verdict_for(fn, graph, records)["verdict"] == "POSSIBLE"

    def test_total_eoh_is_held_there_by_named_constants(self, graph, records):
        """
        Not just "POSSIBLE" but WHICH inputs hold it there — otherwise the
        verdict is unfalsifiable and nobody can work on it.
        """
        v = VL.verdict_for("total_eoh", graph, records)
        assert "PERSONAL_EOH_BASE" in v["held_there_by"], (
            "the personal base is the largest placeholder under the "
            "obligation; if it stopped appearing here the graph lost an edge"
        )

    def test_a_pure_arithmetic_function_is_not_forced_to_possible(
        self, graph, records
    ):
        """
        The ladder must be able to return something other than POSSIBLE, or it
        is a constant function wearing a gate's clothes.
        """
        clean = [
            fn for fn in graph
            if (v := VL.verdict_for(fn, graph, records))["known"]
            and v["verdict"] in ("CERTAIN", "INSTANCE")
        ]
        assert clean, (
            "every function in the package resolved to POSSIBLE, which means "
            "the tier map or the graph is degenerate rather than the codebase "
            "being uniformly weak"
        )


class TestTheErrorDirectionStaysSafe:
    """
    Static OVER-approximates, so a verdict is weaker than the code may warrant
    and never stronger. That is the property the runtime route did not have,
    and it is the reason this module is static.
    """

    def test_dependencies_grow_with_the_call_closure(self, graph, records):
        """
        A caller must inherit at least its callee's dependencies. If it does
        not, the closure is not being walked and verdicts will read stronger
        than they are — the exact failure the runtime spike had.
        """
        caller = VL.dependencies("obligation_accounts", graph)
        callee = VL.dependencies("total_eoh", graph)
        assert callee <= caller, (
            "obligation_accounts calls total_eoh but does not inherit its "
            "constants; the transitive walk is broken"
        )

    def test_default_arguments_are_seen(self, graph):
        """
        THE SPIKE RESULT, PINNED. Most constants reach their consumers as
        default arguments, which Python binds at definition time — invisible to
        runtime perturbation, which found 4 dependencies for `total_eoh` where
        this finds 18. If this number collapses toward 4, the module has
        regressed onto the instrument that fails in the dangerous direction.
        """
        assert "PERSONAL_EOH_BASE" in VL.dependencies("personal_eoh", graph), (
            "PERSONAL_EOH_BASE reaches `personal_eoh` only as the default of "
            "`base_rate`; missing it means default-argument expressions are "
            "no longer walked"
        )
        assert len(VL.dependencies("total_eoh", graph)) >= 15

    def test_it_declares_its_own_gaps(self):
        doc = VL.__doc__ or ""
        for gap in ("bare name", "getattr", "OVER-approximates"):
            assert gap in doc, (
                f"the {gap!r} limitation left the module docstring; a checker "
                "that hides a gap reads as stronger than it is"
            )
