"""
The anchor page's figure emitter — the half of the regeneration path that can
exist while the page is still gitignored.

SPDX-License-Identifier: AGPL-3.0-or-later

WHAT THIS GATES, AND WHAT IT CANNOT. `notes/anchor_comparison_draft.md` is
gitignored, so no test here can read it: the page's figures cannot be checked
against the page. What CAN be gated is that the emitter still reaches every
quantity the page quotes, still fails loudly when a key is renamed, and still
agrees with the functions it claims to be re-presenting.

That distinction is the point rather than an apology for it. A checker that did
not state its own gap would read as a gate on the page, which it is not.
"""

from __future__ import annotations

import pytest

from utils import anchor_page_figures as APF


class TestEveryFigureIsReachable:
    """A figure the page quotes and the emitter cannot compute is the drift."""

    def test_every_entry_computes_without_raising(self):
        live = APF.figures()
        assert len(live) == len(APF.FIGURES)

    @pytest.mark.parametrize("key", sorted(APF.FIGURES))
    def test_each_entry_carries_the_sentence_it_appears_in(self, key):
        """
        Mode 13 says the drift lives in the PROSE, so the prose travels with the
        call. A bare number in this table would be a number with no claim
        attached, which is what the page already has.
        """
        _, meaning = APF.FIGURES[key]
        assert len(meaning) > 20, f"{key} has no sentence beside it"

    def test_no_figure_is_silently_none(self):
        """
        `None` is a legitimate VALUE here — it is how "no crossover" is
        reported — but only for the two crossover entries. Anywhere else it
        means a key was renamed and `.get()` swallowed it.
        """
        allowed_none = {
            "verification_crossover_core",
            "verification_crossover_broad",
        }
        live = APF.figures()
        stray = [k for k, v in live.items()
                 if v is None and k not in allowed_none]
        assert not stray, f"{stray} came back None; a renamed key reads as a result"

    def test_no_collection_figure_is_empty(self):
        """
        THE DEFECT THIS TEST EXISTS FOR. `anchors_holding_all_three` first asked
        for `registers_obligation`; the field is `registered`. With `.get()` the
        filter emptied and the emitter reported that NO anchor holds all three
        properties — **inverting the page's central result, silently, inside the
        module written to prevent exactly that.**
        """
        live = APF.figures()
        empty = [k for k, v in live.items()
                 if isinstance(v, (list, tuple, dict)) and not v]
        assert not empty, (
            f"{empty} came back empty. An empty collection is what a wrong key "
            "looks like, and it reads as a finding."
        )


class TestItAgreesWithTheFunctionsItRePresents:
    """
    The emitter must not become a second account of a quantity. Where it
    re-presents something a scenario already computes, the two must match —
    two accounts of one number is the shape that let `psi` diverge from
    `psi_applied`.
    """

    def test_the_verification_peak_matches_the_crossover_report(self):
        from hours_eoh.scenarios.verification_cost import verification_crossover
        live = APF.figures()
        for scope, key in (("core", "verification_peak_core"),
                           ("broad", "verification_peak_broad")):
            reported = verification_crossover(
                scope=scope, basis="per_registered"
            )["peak_ratio"]
            assert live[key] == pytest.approx(reported)

    def test_the_not_unique_result_is_what_the_page_claims(self):
        """
        The page's central negative result. If this ever returns HOURS alone,
        the page's "not unique" paragraph is false and must be rewritten before
        anything ships.
        """
        holders = APF.figures()["anchors_holding_all_three"]
        assert holders == ["HOURS", "mutual credit"], (
            f"the set holding all three properties is now {holders}. The page "
            "says HOURS is not unique and shares them with mutual credit; that "
            "sentence is now wrong in one direction or the other."
        )

    def test_the_scope_sensitivity_keeps_both_verdicts_live(self):
        """
        Narrow does not cross, broad does. A version where both agree would let
        the page state a verdict the measurement does not support.
        """
        live = APF.figures()
        assert live["scope_sensitivity_core_crosses"] is False
        assert live["scope_sensitivity_broad_crossover"] is not None
        assert live["scope_sensitivity_core_peak"] < 1.0
        assert live["scope_sensitivity_broad_peak"] > 1.0


class TestTheMarkdownBlockIsPasteable:
    def test_it_renders_every_figure(self):
        block = APF.as_markdown()
        for key in APF.FIGURES:
            assert f"`{key}" in block

    def test_it_says_it_is_generated(self):
        assert "do not hand-edit" in APF.as_markdown()
