"""
DOES CAPTURE IN ONE COLLECTIVE BECOME ISSUANCE IN ALL? — reporting only.

Item 8 of the register-governance outline, and the one part of that front the
existing code can actually answer rather than merely argue. `scenarios/register_capture.py`
prices a capture inside one ledger; this asks what the federation does about it.

THE ANSWER IS NOT THE ONE THE ARCHITECTURE ADVERTISES
------------------------------------------------------
`coasean.three_regime_inflation` states the hope in its own docstring: *"An
over-issuing collective sees its unit depreciate against its neighbors"* —
transition inflation carried honestly as an exchange-rate movement, which is what
makes inter-collective exchange a pressure valve rather than a leak.

Measured, that is true of ONE of the two mechanisms and false of the other, and
the prose does not distinguish them:

1. **PARITY REWARDS CAPTURE.** `exchange_rates` is built on
   `productivity(c) = teh_created(c) / population(c)`. Capture raises
   `teh_created` and leaves the obligation untouched, so the capturing
   collective's measured productivity RISES and its unit APPRECIATES. **Parity
   has no real-output term to divide by, so within it over-issuance and
   productivity are the same observation.**

2. **SETTLEMENT DISCIPLINES CAPTURE — but only through trade.**
   `coasean.settlement_check` depreciates a debtor whose bilateral deficit
   exceeds its credit ceiling and exhausts its reserve. That is a genuine
   corrective, and it is the mechanism the depreciation claim actually rests on.

The consequence is the finding: **the discipline is real but it is not automatic,
because it engages through a channel domestic capture does not use.** A register
captured to admit more of its own population's obligation mints TEH that is
earned and spent at home. It need not run any bilateral deficit at all, and while
it does not, parity is paying it a premium.

WHAT THIS IS NOT
----------------
Not a claim that any federation has done this: no actor, incentive or defection
is modelled, here or in `register_capture`. Not a defect in `settlement_check`,
whose functional form is explicitly proposed rather than calibrated. And not an
argument against federation — the no-recognition regime is still the one where
capture is *visible in principle*, which is more than mutual recognition offers.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.registration import personal_eoh_registration_share
from hours_eoh.research.coasean import settlement_check
from hours_eoh.research.exchange import CollectiveFrame, build_collective, parity_rate

#: The reference pairing used throughout, so both collectives differ in exactly
#: one thing — the registration decision. Population, land and capital travel
#: together as one frame, per the frame-seam discipline.
_REFERENCE_FRAME: dict[str, float] = {
    "population": 1_000_000.0,
    "land_hectares": 1_650_000.0,
    "capital_stock_teh": 2_400_000_000.0,
}


def _frame(collective_id: int) -> CollectiveFrame:
    return CollectiveFrame(collective_id=collective_id, **_REFERENCE_FRAME)  # type: ignore[arg-type]


def parity_response(
    share_delta: float = 0.05,
    epsilon: float = 0.40,
) -> dict[str, Any]:
    """
    What the parity baseline does when one collective captures its register.

    Two collectives identical in every respect — same frame, same ε, same
    physical state — except that one admits `share_delta` more of its personal
    obligation. The obligation itself is untouched, and that is asserted rather
    than assumed.

    Returns the parity rate of the capturing collective against the honest one.
    **Above 1.0 means capture was rewarded.**
    """
    honest = build_collective(_frame(0), epsilon)
    captured = build_collective(
        _frame(1),
        epsilon,
        personal_registration_share=personal_eoh_registration_share(epsilon) + share_delta,
    )
    h, c = honest.pipeline, captured.pipeline
    rate = parity_rate(captured, honest)
    return {
        "epsilon": epsilon,
        "share_delta": share_delta,
        "honest_share": float(h["registration_share"]),
        "captured_share": float(c["registration_share"]),
        "honest_mint": float(h["teh_created"]),
        "captured_mint": float(c["teh_created"]),
        "obligation_identical": float(h["total_eoh"]) == float(c["total_eoh"]),
        "parity_captured_over_honest": rate,
        "capture_was_rewarded": rate > 1.0,
        "why": (
            "parity is teh_created/population; capture raises teh_created and "
            "leaves the obligation alone, so it reads as productivity"
        ),
        "reporting_only": True,
    }


def settlement_offset(
    share_delta: float = 0.05,
    epsilon: float = 0.40,
    debtor_reserve: float = 1.0e9,
    imbalance_multiples: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0),
) -> dict[str, Any]:
    """
    How much trade deficit it takes for settlement to cancel the parity gain.

    `settlement_check` depreciates a debtor whose bilateral deficit exceeds its
    credit ceiling and exhausts its reserve. Applied against the parity gain from
    `parity_response`, the net rate is `parity × depreciation_factor`, and the
    question is where that crosses back to 1.0.

    Below the crossing the capturing collective is net AHEAD despite the
    settlement mechanism running. Reported as a curve rather than a single
    number because the crossing depends on the reserve, the ceiling fraction and
    the slope — the last of which `settlement_check` states is proposed rather
    than calibrated.
    """
    gain = parity_response(share_delta, epsilon)["parity_captured_over_honest"]
    rows = []
    for mult in imbalance_multiples:
        r = settlement_check(imbalance=debtor_reserve * mult, debtor_reserve=debtor_reserve)
        factor = float(r["depreciation_factor"])
        rows.append(
            {
                "imbalance_over_reserve": mult,
                "status": r["status"],
                "depreciation_factor": factor,
                "net_rate": gain * factor,
                "capture_still_ahead": gain * factor > 1.0,
            }
        )
    crossing = next((r["imbalance_over_reserve"] for r in rows if not r["capture_still_ahead"]), None)
    return {
        "epsilon": epsilon,
        "parity_gain": gain,
        "rows": rows,
        "crossing_imbalance_over_reserve": crossing,
        "note": (
            "below the crossing the capturing collective is net ahead WITH the "
            "settlement mechanism running; the discipline is real but not automatic"
        ),
        "reporting_only": True,
    }


def recognition_regimes(
    share_delta: float = 0.05,
    epsilon: float = 0.40,
) -> dict[str, Any]:
    """
    Outline item 8, both regimes, with what each costs.

    **Mutual recognition** — the federation accepts every register's issuance at
    par. There is one unit, so there is no pairwise rate to move and the exchange
    layer reports nothing whatever happens in any register. The captured issuance
    dilutes every holder, and the instrument that would have shown it does not
    exist in this regime. Capture in one IS issuance in all, exactly.

    **No recognition** — units are separate and parity is computed. Capture is
    visible in principle, but see `parity_response`: what parity shows is a
    capturing collective looking MORE productive, not less. Visibility is not
    the same as discipline, and the discipline lives in the settlement path.

    Neither regime is recommended here. What is reported is what each does.
    """
    p = parity_response(share_delta, epsilon)
    return {
        "epsilon": epsilon,
        "mutual_recognition": {
            "rate_signal_exists": False,
            "capture_dilutes": "every holder in the federation",
            "detectable_by_exchange_layer": False,
            "why": "one unit means no pairwise rate; there is nothing for a rate to say",
        },
        "no_recognition": {
            "rate_signal_exists": True,
            "capture_dilutes": "the capturing collective's own holders",
            "detectable_by_exchange_layer": True,
            "but": (
                f"parity moves the WRONG WAY — the capturing collective's unit "
                f"appreciates {p['parity_captured_over_honest']:.4f}x, because "
                f"parity reads minted TEH as output"
            ),
        },
        "the_discipline_is_in_settlement_not_parity": True,
        "and_settlement_needs_trade": (
            "a register captured to admit more of its OWN population's obligation "
            "mints TEH earned and spent at home, so it need run no bilateral "
            "deficit at all — and while it does not, parity pays it a premium"
        ),
        "reporting_only": True,
    }


def federation_report(share_delta: float = 0.05, epsilon: float = 0.40) -> dict[str, Any]:
    """The federation half of the governance failure model, as one call."""
    return {
        "epsilon": epsilon,
        "parity": parity_response(share_delta, epsilon),
        "settlement": settlement_offset(share_delta, epsilon),
        "regimes": recognition_regimes(share_delta, epsilon),
        "what_this_does_not_establish": [
            "that any federation has captured a register. No actor, incentive or "
            "defection is modelled.",
            "that settlement_check is miscalibrated. Its functional form is "
            "explicitly proposed rather than calibrated, and the crossing point "
            "moves with the slope.",
            "that federation is a mistake. No-recognition is still the regime "
            "where capture is visible IN PRINCIPLE, which mutual recognition is not.",
        ],
        "reporting_only": True,
    }
