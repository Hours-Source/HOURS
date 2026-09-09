"""
Outline item 8 — does capture in one collective become issuance in all?

Named for the module rather than mirroring `tests/research/` because there is no
such directory; `research/` tests live at the top level here.

These pin a finding that runs AGAINST the architecture's own advertised
behaviour, so they are written so that the advertised behaviour would fail them:
if parity ever starts disciplining capture, `test_parity_rewards_capture` breaks
and the finding is retired rather than quietly outliving its truth.
"""

from __future__ import annotations

import pytest

from hours_eoh.research.register_federation import (
    federation_report,
    parity_response,
    recognition_regimes,
    settlement_offset,
)

ARC = [0.0, 0.40, 0.90]


class TestParityRewardsCapture:
    """
    The finding, and it contradicts `three_regime_inflation`'s prose — *"an
    over-issuing collective sees its unit depreciate against its neighbors"*.
    True via settlement, false via parity, and the prose does not separate them.
    """

    def test_the_two_collectives_differ_only_in_the_registration_decision(self) -> None:
        p = parity_response()
        assert p["obligation_identical"], (
            "the comparison is only meaningful if the physical obligation is "
            "identical; otherwise the rate move could be real productivity"
        )
        assert p["captured_share"] > p["honest_share"]
        assert p["captured_mint"] > p["honest_mint"]

    @pytest.mark.parametrize("eps", ARC)
    def test_capture_appreciates_the_capturing_unit(self, eps: float) -> None:
        """THE ONE THAT MUST BE ABLE TO FAIL. If parity ever divides by a real
        output term rather than by minted TEH, this breaks — and that is the
        signal to retire the finding, not to update the number."""
        p = parity_response(epsilon=eps)
        assert p["capture_was_rewarded"] is True
        assert p["parity_captured_over_honest"] > 1.0, (
            f"at ε={eps} parity no longer rewards capture "
            f"({p['parity_captured_over_honest']:.6f}); the finding may be stale"
        )

    def test_a_larger_capture_is_rewarded_more(self) -> None:
        """Monotonicity — the direction, not the level. A parity that rewarded
        capture but did not scale with it would mean something else is moving."""
        small = parity_response(share_delta=0.02)["parity_captured_over_honest"]
        large = parity_response(share_delta=0.08)["parity_captured_over_honest"]
        assert 1.0 < small < large

    def test_the_refusal_direction_is_punished_symmetrically(self) -> None:
        """A register that admits LESS looks less productive and its unit weakens
        — so parity penalises a collective for under-registering exactly as it
        rewards one for over-registering. Both are the same defect."""
        r = parity_response(share_delta=-0.02)
        assert r["parity_captured_over_honest"] < 1.0


class TestTheDisciplineIsInSettlementNotParity:

    def test_settlement_can_offset_the_gain_but_needs_a_large_deficit(self) -> None:
        s = settlement_offset()
        assert s["parity_gain"] > 1.0
        assert s["crossing_imbalance_over_reserve"] is not None, (
            "settlement never offsets the parity gain at any tested imbalance — "
            "if that is now true the discipline claim has no support at all"
        )
        # and below the crossing the capturing collective is still ahead
        below = [r for r in s["rows"] if r["imbalance_over_reserve"] < s["crossing_imbalance_over_reserve"]]
        assert below and all(r["capture_still_ahead"] for r in below)

    def test_a_deficit_inside_the_credit_ceiling_does_nothing_at_all(self) -> None:
        """The channel domestic capture does not use. Within the ceiling the
        status is OK and the depreciation factor is exactly 1.0, so a register
        captured to admit its own population's obligation — TEH earned and spent
        at home — meets no resistance whatever."""
        s = settlement_offset()
        inside = next(r for r in s["rows"] if r["imbalance_over_reserve"] == 0.5)
        assert inside["status"] == "OK"
        assert inside["depreciation_factor"] == 1.0
        assert inside["capture_still_ahead"] is True

    def test_the_crossing_moves_with_the_reserve(self) -> None:
        """The crossing is not a constant of the framework — it depends on the
        reserve, the ceiling fraction and a slope `settlement_check` states is
        proposed rather than calibrated. Quoting one number as the threshold
        would be quoting a point on a surface."""
        a = settlement_offset(debtor_reserve=1.0e9)
        b = settlement_offset(debtor_reserve=1.0e9, imbalance_multiples=(1.6, 1.7, 1.8))
        assert a["crossing_imbalance_over_reserve"] != b["crossing_imbalance_over_reserve"]


class TestTheTwoRegimes:

    def test_mutual_recognition_has_no_signal_at_all(self) -> None:
        r = recognition_regimes()["mutual_recognition"]
        assert r["rate_signal_exists"] is False
        assert r["detectable_by_exchange_layer"] is False
        assert "every holder" in r["capture_dilutes"]

    def test_no_recognition_is_detectable_but_points_the_wrong_way(self) -> None:
        r = recognition_regimes()["no_recognition"]
        assert r["detectable_by_exchange_layer"] is True
        assert "appreciates" in r["but"], (
            "the regime comparison must carry the direction, or 'detectable' "
            "reads as 'disciplined'"
        )

    def test_the_report_declares_what_it_does_not_establish(self) -> None:
        limits = " ".join(federation_report()["what_this_does_not_establish"]).lower()
        assert "no actor" in limits
        assert "calibrated" in limits, (
            "the report must say settlement_check's form is proposed rather than "
            "calibrated — otherwise the crossing reads as a measured constant"
        )
        assert "mistake" in limits or "visible" in limits, (
            "it must not read as an argument against federation"
        )
