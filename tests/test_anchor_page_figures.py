"""
The anchor comparison page and the figures it rests on.

SPDX-License-Identifier: AGPL-3.0-or-later

TWO HALVES. `utils/anchor_page_figures.py` emits every figure the page rests on
from the functions that compute it. The page itself —
`docs/theory/anchor_comparison.md`, published 2026-09-12 — quotes SHAPES where
a figure is calibration, and states a value only where it is structural.

So this file gates both: that the emitter still reaches every quantity and fails
loudly on a renamed key, and that the STRUCTURAL statements on the published
page still agree with the emitter.

WHAT IT CANNOT SEE: a shape claim ("a low single-digit percentage", "roughly two
in five") that has drifted out of its range without any structural statement
moving. The shape words are chosen to be robust to calibration; a change large
enough to break one is a finding, and nothing here detects it automatically.
Before this page moved to `docs/` it lived in gitignored `notes/` and could not
be gated at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from utils import anchor_page_figures as APF

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "theory" / "anchor_comparison.md"


@pytest.fixture(scope="module")
def live():
    return APF.figures()


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


class TestEveryFigureIsReachable:
    """A figure the page rests on and the emitter cannot compute is the drift."""

    def test_every_entry_computes_without_raising(self, live):
        assert len(live) == len(APF.FIGURES)

    @pytest.mark.parametrize("key", sorted(APF.FIGURES))
    def test_each_entry_carries_the_sentence_it_appears_in(self, key):
        """
        Mode 13 says the drift lives in the PROSE, so the prose travels with the
        call. A bare number in this table would be a number with no claim
        attached.
        """
        _, meaning = APF.FIGURES[key]
        assert len(meaning) > 20, f"{key} has no sentence beside it"

    def test_no_figure_is_silently_none(self, live):
        """
        `None` is a legitimate VALUE here — it is how "no crossover" is
        reported — but only for the two crossover entries. Anywhere else it
        means a key was renamed and `.get()` swallowed it.
        """
        allowed_none = {
            "verification_crossover_core",
            "verification_crossover_broad",
        }
        stray = [k for k, v in live.items()
                 if v is None and k not in allowed_none]
        assert not stray, f"{stray} came back None; a renamed key reads as a result"

    def test_no_collection_figure_is_empty(self, live):
        """
        THE DEFECT THIS TEST EXISTS FOR. `anchors_holding_all_three` first asked
        for `registers_obligation`; the field is `registered`. With `.get()` the
        filter emptied and the emitter reported that NO anchor holds all three
        properties — **inverting the page's central result, silently, inside the
        module written to prevent exactly that.**
        """
        empty = [k for k, v in live.items()
                 if isinstance(v, (list, tuple, dict)) and not v]
        assert not empty, (
            f"{empty} came back empty. An empty collection is what a wrong key "
            "looks like, and it reads as a finding."
        )


class TestItAgreesWithTheFunctionsItRePresents:
    """
    The emitter must not become a second account of a quantity. Two accounts of
    one number is the shape that let `psi` diverge from `psi_applied`.
    """

    def test_the_verification_peak_matches_the_crossover_report(self, live):
        from hours_eoh.scenarios.verification_cost import verification_crossover
        for scope, key in (("core", "verification_peak_core"),
                           ("broad", "verification_peak_broad")):
            reported = verification_crossover(
                scope=scope, basis="per_registered"
            )["peak_ratio"]
            assert live[key] == pytest.approx(reported)

    def test_the_not_unique_result_is_what_the_page_claims(self, live):
        """
        The page's central negative result. If this ever returns HOURS alone,
        the page's "not unique" paragraph is false and must be rewritten before
        anything ships.
        """
        assert live["anchors_holding_all_three"] == ["HOURS", "mutual credit"]

    def test_the_corridor_verdict_is_decided_by_the_declaration(self, live):
        """
        THE LIVE FORM OF §7's AUDIT FALSIFIER. The shipped episodic cadence
        closes the corridor; a continuous register leaves it open. A version in
        which both agreed would let the page state a verdict the declaration
        does not support — which is closing by assertion.
        """
        assert live["corridor_verdict_shipped_default"] == "closed_and_usable"
        assert live["corridor_verdict_continuous"] == "open_edges"
        assert 0.0 < live["continuous_human_affordable_from_epsilon"] < 0.99

    def test_the_shape_words_still_describe_the_values(self, live):
        """
        The page quotes shapes, so the shapes are pinned here in the words the
        page uses. When one of these fails, the SENTENCE is wrong — rewrite it,
        do not widen the range.
        """
        # "a low single-digit percentage of the obligation"
        assert 0.01 <= live["verification_peak_core"] < 0.05
        assert 0.01 <= live["verification_peak_broad"] < 0.05
        # "most human EOH mints nothing" at the reference
        assert live["registration_share"] < 0.25
        # "a few percent" on the obligation when capital halves
        assert -0.10 < live["shock_capital_obligation"] < -0.01
        # "well short of 1", "many times the 1% the parameter implies"
        assert live["observable_epsilon_at_top_capability"] < 0.95
        assert live["human_fraction_at_top_capability"] > 0.05
        # the subsistence mix gives the LOWER ceiling
        assert live["ceiling_on_subsistence_mix"] < live["ceiling_on_top_mix"] < 1.0
        # "roughly two constants in five"
        assert 0.30 <= live["measurement_debt_share"] <= 0.50
        # "an order of magnitude to spare" for every episodic regime
        assert live["verification_headroom_share_at_subsistence"] > 0.05


class TestThePublishedPageSaysWhatTheFunctionsSay:
    """
    The page is in `docs/`, so the published sentences can be read here. What is
    checked is every STRUCTURAL statement: the ones the page states flatly
    because they do not move with calibration.
    """

    def test_the_page_is_published_and_in_the_nav(self):
        assert PAGE.exists()
        assert "theory/anchor_comparison.md" in (ROOT / "mkdocs.yml").read_text()

    def test_the_corridor_verdicts_on_the_page_are_the_live_ones(self, live, page):
        assert live["corridor_verdict_shipped_default"] in page
        assert live["corridor_verdict_continuous"] in page

    def test_the_instrument_verdict_on_the_page_is_the_live_one(self, live, page):
        assert live["instrument_verdict"].lower() in page.lower()
        assert "ADJACENT" in page, "the page must use the verdict word"

    def test_the_designed_zeros_are_stated_and_still_zero(self, live, page):
        assert live["shock_capital_minting"] == 0.0
        assert live["shock_ecosystem_minting"] == 0.0
        assert live["shock_labour_minting"] == pytest.approx(-0.5)
        assert "**−50%**" in page and "**0.0%**" in page

    def test_the_unit_elasticity_is_stated_and_still_exact(self, live, page):
        assert live["registration_elasticity"] == pytest.approx(1.0, abs=1e-9)
        assert "1.000" in page

    def test_the_count_of_anchors_is_the_live_count(self, live, page):
        words = {8: "Eight"}
        assert f"{words[live['anchors_classified']]} anchors" in page

    def test_mutual_credit_is_named_as_holding_all_three(self, page):
        assert "Not unique" in page
        assert "Mutual credit holds the same three properties" in page

    def test_the_superseded_ratio_transfer_is_not_quoted_as_live(self, page):
        """
        THE DEFECT THAT BLOCKED PUBLICATION. §5.1 and §7 of the draft still gave
        the 40× registrant ratio transfer as the live answer after it had been
        superseded, while §6 said the corridor was closed. Those figures must not
        come back as current statements.
        """
        for stale in ("46.6%", "117.1%", "0.624", "7.7×"):
            assert stale not in page, f"{stale} is the superseded ratio transfer"

    def test_the_page_quotes_no_constant_count(self, page):
        """Counts move every time a constant lands; the page says shapes."""
        assert not re.search(r"\b\d{3} constants\b", page)
        assert not re.search(r"\bof \d{3}\b", page)


class TestTheMarkdownBlockIsPasteable:
    def test_it_renders_every_figure(self):
        block = APF.as_markdown()
        for key in APF.FIGURES:
            assert f"`{key}" in block

    def test_it_says_it_is_generated(self):
        assert "do not hand-edit" in APF.as_markdown()
