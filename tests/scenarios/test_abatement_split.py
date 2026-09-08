"""
The removal classification, and the result it produces.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import max_abatement
from hours_eoh.data import PERSONAL_EOH_COMPONENTS
from hours_eoh.scenarios.abatement_split import (
    ABATEMENT_KIND, capital_weighting, pace_sensitivity, removal_audit,
    removal_bound, removal_consequence,
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

    def test_the_conversion_moved_no_number(self) -> None:
        """
        THE POINT OF A UNIT CONVERSION. a(K) is invariant under scaling K and
        K_half by the same factor, so redenominating both left every abatement
        figure bit-identical while fixing an incoherence — K in personal-serving
        capital against a K_half denominated in total. Nothing about the PACE is
        asserted by it, which is why it is not a re-choice.
        """
        # EXACT at the reference tier, because the share constant IS the
        # standard tier's. Elsewhere the tier's own personal-serving share
        # differs slightly — 0.1121 basic to 0.1136 minimal — so a single
        # constant introduces a residual. It is bounded at 0.5%, well inside
        # anything a confidence-5 pace constant could support, and it is stated
        # rather than hidden: this is where a "tier-stable" claim stops being
        # "tier-identical".
        for tier in ("standard", "advanced"):
            r = capital_weighting(tier)
            assert r["a_of_personal_serving"] == pytest.approx(
                r["a_of_total"], rel=1e-9), tier
        for tier in ("minimal", "basic"):
            r = capital_weighting(tier)
            assert r["a_of_personal_serving"] == pytest.approx(
                r["a_of_total"], rel=5e-3), tier
            assert r["ratio"] == pytest.approx(1.0, rel=5e-3), tier

    def test_the_pace_constant_is_now_denominated_in_the_same_units_as_k(self) -> None:
        from hours_eoh.data import (
            ABATEMENT_HALF_CAPITAL_TEH, CAPITAL_PERSONAL_SERVING_SHARE,
        )
        assert ABATEMENT_HALF_CAPITAL_TEH == pytest.approx(
            1000.0 * CAPITAL_PERSONAL_SERVING_SHARE, abs=1e-5), (
            "K_half is no longer the redenominated 1,000. If it was RE-CHOSEN "
            "rather than converted, that is a different act and the identity "
            "route overwrites it — see the constant's own resolves_by."
        )

    def test_the_pace_itself_is_still_unsettled(self) -> None:
        """The conversion fixes units, not groundedness. Confidence 5 stands."""
        from utils import provenance as pv
        rec = {r.name: r for r in pv.scan(pv.DATA_PY.read_text(encoding="utf-8")).records}
        k = rec["ABATEMENT_HALF_CAPITAL_TEH"]
        assert k.tag == "placeholder"
        assert k.confidence.startswith("5")

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


class TestThePaceSensitivityIsReported:
    """
    `ABATEMENT_HALF_CAPITAL_TEH`'s tag asks for this in as many words —
    *"Report the sensitivity alongside any abatement figure until it is
    measured"* — and until 2026-09-08 nothing did, so every abatement number in
    this repo was quoted without it.
    """

    def test_the_swing_is_large_enough_to_matter(self) -> None:
        r = pace_sensitivity()
        assert r["swing_share_of_base"] > 0.25, (
            f"the abated base swings {r['swing_share_of_base']:.0%} across the "
            "pace constant's range. If that has fallen below ~25% the constant "
            "has become better grounded and its confidence should say so."
        )

    def test_the_sweep_spans_the_range_confidence_5_licenses(self) -> None:
        """
        Two orders of magnitude. The tag says the 5 is "only that the ORDER of
        magnitude is bounded by the arc having to saturate somewhere inside
        it" — a narrower sweep would claim more grounding than exists.
        """
        lo, hi = r_range = pace_sensitivity()["k_half_range"]
        assert hi / lo >= 100.0, r_range

    def test_more_pace_capital_means_less_abatement(self) -> None:
        """Direction, checked rather than assumed: K_half is a HALF-point, so
        raising it slows abatement and raises the residual obligation."""
        rows = pace_sensitivity()["rows"]
        assert [x["a_of_k"] for x in rows] == sorted(
            (x["a_of_k"] for x in rows), reverse=True)
        assert [x["abated_base"] for x in rows] == sorted(
            x["abated_base"] for x in rows)

    def test_the_shipped_value_sits_inside_the_swept_range(self) -> None:
        r = pace_sensitivity()
        lo, hi = r["base_range"]
        assert lo <= r["base_shipped"] <= hi

    def test_it_is_denominated_in_personal_serving_capital(self) -> None:
        """
        The report and the constant must agree on what K means, or the swing is
        computed at the wrong point on the curve.
        """
        from hours_eoh.data import (
            CAPITAL_PERSONAL_SERVING_SHARE, CAPITAL_STOCK_DEFAULT,
            REFERENCE_FRAME_POPULATION,
        )
        r = pace_sensitivity()
        expected = (CAPITAL_STOCK_DEFAULT / REFERENCE_FRAME_POPULATION
                    * CAPITAL_PERSONAL_SERVING_SHARE)
        assert r["capital_per_capita"] == pytest.approx(expected)


class TestTheRemovalAuditIsHonestAboutWhatItCannotSettle:
    """
    Run against the abatabilities' own definition, with what the repo holds.
    """

    def test_it_does_not_claim_to_validate_the_abatabilities(self) -> None:
        """
        THE LOAD-BEARING ADMISSION. No source here separates an obligation that
        vanished from one a machine met, so the audit reports a relationship
        between two channels and refuses a verdict on the values themselves.
        """
        r = removal_audit()
        assert r["disjointness_established"] is False
        assert "CANNOT be validated" in r["verdict"]

    def test_claimed_removal_exceeds_measured_substitution_at_every_tier(self) -> None:
        for row in removal_audit()["rows"]:
            assert row["ratio"] > 1.0, row["tier"]

    def test_the_two_channels_converge_as_capital_rises(self) -> None:
        """
        The shape that makes overlap plausible rather than merely possible: at
        advanced capital the two are within 1.5x, so whatever separates them
        has to be doing most of its work exactly where capital is thickest.
        """
        ratios = [r["ratio"] for r in removal_audit()["rows"]]
        assert ratios == sorted(ratios, reverse=True)
        assert ratios[-1] < 2.0 < ratios[0]

    def test_substitution_peaks_where_the_removal_examples_live(self) -> None:
        """
        `a(K)`'s worked examples are a tap and sanitation.
        `personal_fulfillment_rate` — the SUBSTITUTION channel — peaks on
        medical and water capital and is near zero on computing. Same assets,
        incompatible semantics.
        """
        from hours_eoh.data import CAPITAL_MACHINE_PROFILES
        rate = {n: p["personal_fulfillment_rate"]
                for n, p in CAPITAL_MACHINE_PROFILES.items()}
        top = sorted(rate, key=rate.get, reverse=True)[:3]
        assert set(top) <= {"medical_systems", "water_treatment",
                            "agricultural_automation", "power_grid"}
        assert rate["computing_ai"] < 0.05
        assert rate["environmental_monitoring"] == 0.0

    def test_the_fiscal_layer_already_subtracts_the_other_channel(self) -> None:
        """
        Where it would bite a person. `sufficiency_guarantee` reimburses
        `max(0, raw − capital_personal_eoh_fulfilled)`. If abatement became the
        generation default, `raw` would already be reduced by a(K) — the same
        tap subtracted twice from what someone is owed.
        """
        import inspect
        from hours_eoh.core import fiscal
        src = inspect.getsource(fiscal.sufficiency_guarantee)
        assert "capital_personal_eoh_fulfilled_per_person" in src
        assert "max(0.0, raw_eoh_per_person - capital_personal_eoh_fulfilled_per_person)" in src
        assert removal_audit()["fiscal_double_subtracts"] is True

    def test_abatement_is_still_not_the_generation_default(self) -> None:
        """The double subtraction is not live, and this is what keeps it so."""
        import inspect
        from hours_eoh.core.eoh_generation import personal_eoh
        assert "abat" not in str(inspect.signature(personal_eoh))
