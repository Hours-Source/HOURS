"""
The removal classification, and the result it produces.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import max_abatement
from hours_eoh.data import PERSONAL_EOH_COMPONENTS
from hours_eoh.scenarios.abatement_split import (
    ABATEMENT_KIND, capital_weighting, removal_bound, removal_consequence,
)

KINDS = {"relocation", "substitution", "removal"}


class TestTheClassificationIsCompleteAndStated:

    def test_every_component_is_classified(self) -> None:
        assert set(ABATEMENT_KIND) == set(PERSONAL_EOH_COMPONENTS), (
            "a component with an abatability and no kind is an unexamined "
            "claim that capital removes its obligation."
        )

    def test_every_kind_is_from_the_closed_set(self) -> None:
        for name, entry in ABATEMENT_KIND.items():
            assert entry["kinds"], name
            assert set(entry["kinds"]) <= KINDS, name

    def test_every_classification_states_its_reading(self) -> None:
        """It is a JUDGEMENT, so it has to be arguable. A kind with no reason
        is a fitted constant with a label on it."""
        for name, entry in ABATEMENT_KIND.items():
            assert len(entry["why"]) > 120, f"{name} does not say why"

    def test_removal_is_certain_for_exactly_the_prevention_case(self) -> None:
        certain = {n for n, e in ABATEMENT_KIND.items() if e["removal_is_certain"]}
        assert certain == {"health"}, (
            f"removal_is_certain is now {certain}. Widening it directly widens "
            "the lower bound and weakens the finding — it needs the physical "
            "argument that the entropy is NOT GENERATED, not that capital helps."
        )


class TestTheBoundIsABandNotAPoint:

    def test_the_upper_bound_is_the_shipped_a_max(self) -> None:
        """The finding: a(K) already takes the most generous reading."""
        r = removal_bound()
        assert r["removal_upper"] == pytest.approx(max_abatement())
        assert r["shipped_a_max"] == pytest.approx(0.448276, abs=1e-5)

    def test_the_lower_bound_counts_only_unambiguous_removal(self) -> None:
        r = removal_bound()
        h = PERSONAL_EOH_COMPONENTS["health"]
        assert r["removal_lower"] == pytest.approx(h["share"] * h["abatability"])
        assert r["removal_lower"] < r["removal_upper"]

    def test_the_spread_is_large_enough_to_matter(self) -> None:
        r = removal_bound()
        assert r["shipped_over_lower"] > 4.0, (
            f"the spread is {r['shipped_over_lower']:.1f}x. If it has narrowed "
            "below ~4 the deflation concern may be tolerable and record/"
            "personal.md's blocking of abatement should be re-read."
        )

    def test_it_refuses_to_report_a_point(self) -> None:
        r = removal_bound()
        assert "removal_point" not in r and "removal_share" not in r
        assert r["removal_lower"] != r["removal_upper"]


class TestTheConsequenceIsTheResult:

    def test_the_two_readings_straddle_the_labour_supply(self) -> None:
        """
        THE FINDING. Feasible under the shipped a_max, infeasible under removal
        only — so the abatement path's feasibility rests on counting
        substitution and relocation as removal.
        """
        r = removal_consequence()
        assert r["covered_shipped"] is True
        assert r["covered_removal_only"] is False
        assert r["per_capita_removal_only"] > r["supply_per_capita"] > r["per_capita_shipped"]

    def test_the_removal_only_base_is_higher(self) -> None:
        """Less abatement means more obligation — the direction, checked."""
        r = removal_consequence()
        assert r["base_removal_only"] > r["base_shipped"]
        assert r["a_max_removal_only"] < r["a_max_shipped"]

    def test_more_capital_abates_more_under_both_readings(self) -> None:
        lo = removal_consequence(500.0)
        hi = removal_consequence(20000.0)
        assert hi["base_shipped"] < lo["base_shipped"]
        assert hi["base_removal_only"] < lo["base_removal_only"]

    def test_the_verdict_names_the_dependence(self) -> None:
        v = removal_consequence()["verdict"]
        assert "CLEARS" in v and "DOES NOT" in v
        assert "held to its own definition" in v


class TestKIsWeightedByWhatServesThePersonalObligation:
    """
    `a(K)` reduces the PERSONAL obligation and took TOTAL capital, so a data
    centre abated water-hauling. The typing was never missing —
    `CAPITAL_MACHINE_PROFILES` has carried `personal_fulfillment_rate` all
    along — it was unused.
    """

    def test_only_about_an_eighth_of_capital_serves_the_personal_obligation(self) -> None:
        for tier in ("minimal", "basic", "standard", "advanced"):
            r = capital_weighting(tier)
            assert 0.10 < r["personal_serving_share"] < 0.13, (
                f"{tier}: personal-serving share is "
                f"{r['personal_serving_share']:.1%}. The 11.3% figure is quoted "
                "in record/personal.md and in the blocked abatement item."
            )

    def test_the_share_is_stable_across_tiers(self) -> None:
        """It does not drift with capital level, so the correction is a clean
        rescaling rather than a tier-dependent one."""
        shares = [capital_weighting(t)["personal_serving_share"]
                  for t in ("minimal", "basic", "standard", "advanced")]
        assert max(shares) - min(shares) < 0.005, shares

    def test_the_correct_k_lowers_abatement_at_every_tier(self) -> None:
        for tier in ("minimal", "basic", "standard", "advanced"):
            r = capital_weighting(tier)
            assert r["a_of_personal_serving"] < r["a_of_total"], tier
            assert r["ratio"] > 2.0, tier

    def test_the_preserving_k_half_reproduces_the_old_curve_exactly(self) -> None:
        """
        The identity that makes `k_half_preserving` meaningful: a(K) is
        invariant under scaling K and K_half together, so preserving the curve
        means scaling K_half by the same share — which is precisely why
        adopting it would be fitting the pace constant to the answer the wrong
        K produced.
        """
        from hours_eoh.core.eoh_generation import abatement_fraction
        r = capital_weighting()
        preserved = abatement_fraction(
            r["capital_personal_serving"], half_capital=r["k_half_preserving"])
        assert preserved == pytest.approx(r["a_of_total"], rel=1e-12)

    def test_neither_correction_is_adopted(self) -> None:
        """`ABATEMENT_HALF_CAPITAL_TEH` is untouched: the weighting is a
        correction, the pace constant is a re-choice, and this module reports
        rather than decides."""
        from hours_eoh.data import ABATEMENT_HALF_CAPITAL_TEH
        r = capital_weighting()
        assert ABATEMENT_HALF_CAPITAL_TEH == 1000.0
        assert r["k_half_shipped"] == 1000.0
        assert r["k_half_preserving"] < 200.0

    def test_the_weighting_is_stock_semantics_not_condition_weighted(self) -> None:
        """
        `machine_eoh_from_capital` multiplies by condition because it computes
        EOH currently fulfilled; a(K) takes a STOCK. Condition-weighting would
        give a smaller number again, and mixing the two would be the frame
        error this repo has found seven times.
        """
        from hours_eoh.data import CAPITAL_MACHINE_PROFILES
        from hours_eoh.scenarios.abatement_split import personal_serving_capital
        pop = 1_000_000.0
        cap = {n: "standard" for n, p in CAPITAL_MACHINE_PROFILES.items()
               if "standard" in p["tiers"]}
        expected = sum(
            p["tiers"]["standard"]["teh_per_capita"] * p["personal_fulfillment_rate"]
            for p in CAPITAL_MACHINE_PROFILES.values() if "standard" in p["tiers"]
        )
        assert personal_serving_capital(cap, pop) == pytest.approx(expected)
