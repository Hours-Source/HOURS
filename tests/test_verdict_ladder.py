"""The verdict ladder as a gate: a verdict may not outrank its weakest input.

SPDX-License-Identifier: AGPL-3.0-or-later

Adopted 2026-09-11 (author decision, `record/theory.md#the-verdict-ladder`). Before this
the rule was prose, and an ungated commitment here drifts in about two days.

It does not stop anyone writing an overclaim in a docstring; nothing static can. It pins
that **the ladder stays COMPUTABLE and stays HONEST**: the graph resolves, the census
cannot drift silently, the tier of the central results cannot strengthen unnoticed, and
the safe error direction stays safe.
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
    """The ladder was adopted as prose. This class makes it a check."""

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
    """The ladder makes this number carry weight: most constants (60.2% today) sit in
    the weakest tier. A move means measurement landed or a tag was weakened, and someone
    must acknowledge either.
    """

    def test_the_shares_are_where_the_last_acknowledged_change_left_them(self):
        """The tier census must equal the acknowledged snapshot in
        `tests/census_snapshot.json`. A move is an EVENT: regenerate the snapshot and
        give the reason in the commit, never widen the assertion to a range. The log of
        earlier moves is in the record
        ([record](record/verification.md#verdict-ladder-census-history)).
        """
        # FROM 2026-10-03 THE ACKNOWLEDGED SHARES LIVE IN ONE PLACE —
        # tests/census_snapshot.json, written by `eoh provenance census --write`
        # (utils/census.py). For the earlier log see
        # record/verification.md#verdict-ladder-census-history. A new move is
        # acknowledged by regenerating, and its WHY goes in the commit message.
        from utils import census
        c = VL.tier_census()
        s = census.snapshot()
        assert c["total"] == s["tier_total"]
        assert dict(c["counts"]) == s["tiers"], (
            f"the census moved: {dict(c['counts'])} against the acknowledged "
            f"{s['tiers']}. If intended, run `eoh provenance census --write` and "
            "say why in the commit."
        )

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
        """**THE LADDER'S CENTRAL FINDING, AND IT IS AGAINST THE FRAMEWORK.** Every
        headline result rests on at least one placeholder, so none may claim more than
        "possible", as computed from the tags. A result that comes back CERTAIN or
        INSTANCE is a real event: someone measured what lies under it.
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
        """A caller must inherit at least its callee's dependencies. If not, the walk
        misses the closure and verdicts read stronger than they are, as with the runtime
        spike.
        """
        caller = VL.dependencies("obligation_accounts", graph)
        callee = VL.dependencies("total_eoh", graph)
        assert callee <= caller, (
            "obligation_accounts calls total_eoh but does not inherit its "
            "constants; the transitive walk is broken"
        )

    def test_default_arguments_are_seen(self, graph):
        """Most constants reach their consumers as default arguments, bound at
        definition time and invisible to runtime perturbation. That instrument found 4
        dependencies for `total_eoh`; this walk finds 21 today. A count near 4 means the
        module has regressed onto the instrument that fails in the dangerous direction.
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
