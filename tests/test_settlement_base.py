"""
`research/settlement_base.py` — which quantity backs a TEH at the boundary.

CLAUDE.md §5 (2026-09-12): settle on the BASE, never on a discovered rate. The
rule names the property and not the equation, so these tests pin what each
candidate DOES — capture direction, boundedness across ε, the frame — and the
two candidates whose passes are identities are pinned AS identities, so a pass
there is never quoted as evidence.

Shapes, not levels: levels are calibration and will move.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.data import ARC_REPORTING_POINTS
from hours_eoh.research.exchange import build_collective, parity_rate
from hours_eoh.research.settlement_base import (
    BASES,
    BY_CONSTRUCTION,
    SEARCH_POINTS,
    _reference_frame,
    acquisition,
    arc_pairing,
    base_report,
    capture_response,
    frame_check,
    multiplier_response,
    settlement_rate,
    spread_decomposition,
)

KEY = [0.0, 0.40, 0.90, 0.99]
PER_TEH = ("obligation", "human")


@pytest.fixture(scope="module")
def arc() -> dict:
    return arc_pairing(pairing="arc")


@pytest.fixture(scope="module")
def fixed() -> dict:
    return arc_pairing(pairing="fixed")


class TestTheBaselineIsTheCurrentForm:

    @pytest.mark.parametrize("eps", KEY)
    def test_parity_candidate_is_exchange_parity_rate(self, eps: float) -> None:
        """If these drift apart, the table is comparing against a baseline that
        is not the code the federation actually runs."""
        a = build_collective(_reference_frame(1, capital_per_capita=9600.0), eps)
        b = build_collective(_reference_frame(0), eps)
        assert settlement_rate(a, b, "parity") == parity_rate(a, b)

    @pytest.mark.parametrize("base", sorted(BASES))
    @pytest.mark.parametrize("eps", KEY)
    def test_every_base_is_reciprocal_finite_and_positive(self, base: str, eps: float) -> None:
        a = build_collective(_reference_frame(1, capital_per_capita=9600.0), eps)
        b = build_collective(_reference_frame(0), 0.40)
        r = settlement_rate(a, b, base)
        assert math.isfinite(r) and r > 0.0
        assert r * settlement_rate(b, a, base) == pytest.approx(1.0, rel=1e-12)
        assert settlement_rate(a, a, base) == 1.0

    def test_unknown_base_raises(self) -> None:
        c = build_collective(_reference_frame(0), 0.40)
        with pytest.raises(ValueError):
            settlement_rate(c, c, "discovered")


class TestCapture:
    """The failure `register_federation` measured: parity rewards it."""

    @pytest.mark.parametrize("eps", ARC_REPORTING_POINTS)
    def test_the_comparison_holds_the_obligation_fixed(self, eps: float) -> None:
        c = capture_response(epsilon=eps)
        assert c["obligation_identical"]
        assert c["mint_ratio"] > 1.0

    @pytest.mark.parametrize("eps", ARC_REPORTING_POINTS)
    def test_parity_rewards_and_per_teh_bases_discipline(self, eps: float) -> None:
        v = capture_response(epsilon=eps)["verdict"]
        assert v["parity"] == "rewarded"
        for b in PER_TEH:
            assert v[b] == "disciplined", f"{b} at ε={eps}"

    @pytest.mark.parametrize("eps", ARC_REPORTING_POINTS)
    def test_per_teh_discipline_is_exactly_the_over_issuance(self, eps: float) -> None:
        """Obligation identical, so the capturer depreciates by exactly the mint
        ratio — the discipline is proportional, not a penalty on top."""
        c = capture_response(epsilon=eps)
        assert c["rates"]["obligation"] == pytest.approx(1.0 / c["mint_ratio"], rel=1e-12)

    @pytest.mark.parametrize("eps", ARC_REPORTING_POINTS)
    def test_neutral_bases_are_neutral(self, eps: float) -> None:
        v = capture_response(epsilon=eps)["verdict"]
        for b in ("registered", "floor", "obligation_parity"):
            assert v[b] == "neutral", f"{b} at ε={eps}"

    def test_the_identity_passes_are_declared(self) -> None:
        """Mode 2: a candidate that passes because of its definition must say
        so in the output, or the report reads as three independent passes."""
        c = capture_response()
        assert set(c["by_construction"]) >= {"registered", "floor"}
        assert "registration" in BY_CONSTRUCTION["obligation_parity"]


class TestTheFork:
    """Does machine-fulfilled obligation back a TEH? `obligation` says yes,
    `human` says no — and at high ε they put a high-capital collective on
    OPPOSITE sides of par. That is the author's question, pinned so the two
    candidates cannot silently become the same one."""

    @pytest.mark.parametrize("eps", [0.90, 0.99])
    def test_obligation_and_human_disagree_on_the_side_of_par(self, eps: float) -> None:
        rich = build_collective(_reference_frame(1, capital_per_capita=9600.0), eps)
        ref = build_collective(_reference_frame(0), eps)
        assert settlement_rate(rich, ref, "obligation") > 1.0
        assert settlement_rate(rich, ref, "human") < 1.0


class TestRateCapture:
    """A multiplier above band — capture of the RATE rather than the register."""

    def test_registered_says_something_only_here(self) -> None:
        m = multiplier_response(multiplier_ratio=1.10)
        assert m["rates"]["registered"] == pytest.approx(1.0 / 1.10, rel=1e-12)

    def test_parity_rewards_rate_capture_too(self) -> None:
        assert multiplier_response()["rates"]["parity"] > 1.0

    def test_obligation_parity_is_blind_to_it(self) -> None:
        """THE PRICE OF obligation_parity's BOUNDEDNESS. It cannot see issuance
        at all, so a collective minting above band settles at par. If this
        stops being 1.0 the trade-off in `base_report` is stale."""
        assert multiplier_response()["rates"]["obligation_parity"] == 1.0


class TestBoundedness:
    """§5's failure: a base EOH here is your entire collective there."""

    @pytest.mark.parametrize("pairing", ["arc", "fixed"])
    def test_parity_is_unbounded_across_the_arc(self, pairing: str, arc: dict, fixed: dict) -> None:
        r = (arc if pairing == "arc" else fixed)["bases"]["parity"]
        assert r["max_rate"] > 10.0

    @pytest.mark.parametrize("pairing", ["arc", "fixed"])
    def test_per_teh_bases_do_not_bound_it_either(self, pairing: str, arc: dict, fixed: dict) -> None:
        """The finding. Settling per TEH disciplines capture and does NOT bound
        the cross-rate — it reverses parity's direction (the subsistence
        collective's unit is now the hard one) without shrinking it an order."""
        res = (arc if pairing == "arc" else fixed)["bases"]
        for b in PER_TEH:
            assert res[b]["max_rate"] > 10.0, b
        # and the direction is REVERSED: parity's strong side is high ε,
        # obligation's is low ε
        assert res["parity"]["max_at"][0] > res["parity"]["max_at"][1]
        assert res["obligation"]["max_at"][0] < res["obligation"]["max_at"][1]

    @pytest.mark.parametrize("pairing", ["arc", "fixed"])
    def test_obligation_parity_stays_within_a_factor_of_two(self, pairing: str, arc: dict, fixed: dict) -> None:
        r = (arc if pairing == "arc" else fixed)["bases"]["obligation_parity"]
        assert 1.0 < r["max_rate"] < 2.0

    def test_floor_is_bounded_by_its_price_floors(self, fixed: dict) -> None:
        assert 1.0 < fixed["bases"]["floor"]["max_rate"] < 10.0

    def test_registered_is_one_everywhere_at_the_shipped_multiplier(self, fixed: dict) -> None:
        r = fixed["bases"]["registered"]
        assert r["max_rate"] == pytest.approx(1.0, rel=1e-12)
        assert r["min_rate"] == pytest.approx(1.0, rel=1e-12)

    def test_min_is_the_reciprocal_of_max(self, fixed: dict) -> None:
        for b, r in fixed["bases"].items():
            assert r["min_rate"] == pytest.approx(1.0 / r["max_rate"], rel=1e-12), b

    def test_the_obligation_extremum_is_between_reporting_points(self, fixed: dict) -> None:
        """Mode 3. The strong side of the obligation base sits mid-arc, where
        the reporting points cannot see it; read off them it is understated."""
        at = max(fixed["bases"]["obligation"]["max_at"])
        assert 0.40 < at < 0.90
        assert at not in ARC_REPORTING_POINTS
        on_points = arc_pairing(points=ARC_REPORTING_POINTS, pairing="fixed")
        assert on_points["bases"]["obligation"]["max_rate"] < fixed["bases"]["obligation"]["max_rate"]

    def test_the_arc_pairing_excludes_subsistence_and_says_so(self, arc: dict) -> None:
        assert arc["excluded_epsilons"] == [0.0]
        assert arc["points"] == len(SEARCH_POINTS)


class TestTheBecauseEvaluated:
    """§5: the obligation is population-bounded, SO the cross-rate is bounded.
    The first half holds; the SO fails at the TEH↔EOH conversion."""

    @pytest.mark.parametrize("pairing", ["arc", "fixed"])
    def test_the_obligation_is_population_bounded(self, pairing: str) -> None:
        assert spread_decomposition(pairing=pairing)["obligation_per_capita_spread"] < 2.0

    @pytest.mark.parametrize("pairing", ["arc", "fixed"])
    def test_the_conversion_is_not(self, pairing: str) -> None:
        d = spread_decomposition(pairing=pairing)
        assert d["mint_per_eoh_spread"] > 10.0
        assert d["registration_share_spread"] > d["mint_per_eoh_spread"], (
            "the register drives the conversion spread; the human fraction "
            "partly offsets it"
        )


class TestAcquisition:

    def test_years_scale_inversely_with_the_rate(self) -> None:
        a = build_collective(_reference_frame(1), 0.90)
        b = build_collective(_reference_frame(0), 0.0)
        p = acquisition(a, b, "parity")
        o = acquisition(a, b, "obligation")
        ratio = p["years_of_mint_for_whole_capital"] / o["years_of_mint_for_whole_capital"]
        assert ratio == pytest.approx(o["rate"] / p["rate"], rel=1e-12)

    def test_no_discount_column_restates_the_rate(self) -> None:
        """The dropped normalisation was identically r. Keep it dropped."""
        a = build_collective(_reference_frame(1), 0.90)
        b = build_collective(_reference_frame(0), 0.0)
        assert "discount" not in acquisition(a, b, "parity")


class TestFrame:

    def test_scaling_the_population_moves_no_base(self) -> None:
        for b, r in frame_check()["scaled_population"].items():
            assert r == pytest.approx(1.0, rel=1e-12), b

    def test_land_is_inert_on_the_shipped_path(self) -> None:
        """A property of the CURRENT calibration — ecological EOH is 0.0 on
        every shipped path (record/ecological.md), so a land difference cannot
        move any base and this probe cannot tell a seam from physics. Should
        FAIL if the ecological level is ever resolved; then read it again."""
        for b, r in frame_check()["more_land_per_capita"].items():
            assert r == 1.0, b


class TestTheReport:

    def test_it_names_what_the_author_decides_and_does_not_decide_for_them(self) -> None:
        r = base_report()
        text = " ".join(r["author_decides"]).lower()
        assert "machine-fulfilled" in text
        assert "blind to issuance" in text
        assert r["reporting_only"] is True
        limits = " ".join(r["what_this_does_not_establish"]).lower()
        assert "goods layer" in limits and "threshold" in limits
