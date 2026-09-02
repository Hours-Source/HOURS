"""
Anchor determinacy — which monetary anchors have a shock response at all.

SPDX-License-Identifier: AGPL-3.0-or-later

WHY THIS EXISTS. The framework's comparative claim is that human productive
capacity is a more defensible reference frame for economic accounting than
commodity scarcity, discretionary issuance or credit. That claim has been argued
and never checked. This is the smallest thing that checks part of it.

WHAT IT DELIBERATELY DOES NOT DO — AND THIS IS THE DESIGN. It does not model
gold, bitcoin or fiat. A comparison whose rivals are modelled badly is worse than
no comparison: it is a conclusion fitted to a strawman, which is the failure this
repo already names in constants that were calibrated to the target they were then
checked against.

So each rival is classified from **its own definition**, at its **advocates'
strongest reading**, and `advocates_say` is a required field. Gold's supply is
cumulative extraction; bitcoin's is a published schedule; fiat's is set by an
issuing institution. None of that is contentious, none of it needs a simulation,
and none of it is a criticism.

THE RESULT FALLS OUT OF THAT HONESTY. Classifying rivals charitably produces
three classes, and the interesting one costs nothing to establish:

    determinate + indifferent   gold, bitcoin      — by design; advocates agree
    determinate + responsive    HOURS, labour voucher, energy certificate
    INDETERMINATE               fiat, debt money   — the response is a POLICY
                                                     CHOICE, not a property

Fiat's shock response is undetermined by its own definition. Saying so requires
no model of monetary policy and takes nothing away from fiat — it is the standard
characterisation, and discretion is the feature.

WHAT IT CANNOT SETTLE. Whether a responsive base is BETTER than an indifferent
one is normative and is not computed here. Report the classification; let a
reader apply their own criterion. See `what_this_does_not_establish()`.

Layer: research/ — experimental, not a stable API, not imported by core or
scenarios. Reporting only; nothing here changes a shipped number.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import ecological_allocation
from hours_eoh.core.prices import basket_price

__all__ = [
    "Anchor",
    "ANCHORS",
    "determinacy_table",
    "hours_shock_response",
    "the_defensible_claim",
    "ecological_response_by_path",
    "registration_leverage",
    "floor_claim_across_the_arc",
    "what_this_does_not_establish",
]


@dataclass(frozen=True)
class Anchor:
    """
    One monetary anchor, classified from its own definition.

    Fields:
        supply_is: what the monetary base is a function of. Definitional.
        determinate: does that definition FIX a response to a capacity shock?
        responsive: does the base move with the civilization's capacity?
            `None` where the anchor is indeterminate — the honest value, since a
            discretionary response is neither responsive nor indifferent.
        registered: must activity fulfil a RECOGNISED obligation to count?
            `None` where the base is not activity-derived at all.
        advocates_say: the anchor's strongest reading, in its own terms.
            REQUIRED — it is the guard against building a rigged comparison.
    """

    name: str
    supply_is: str
    determinate: bool
    responsive: bool | None
    registered: bool | None
    advocates_say: str


#: Classified from definitions, not from models. Ordered as the value-anchor
#: section presents them.
ANCHORS: tuple[Anchor, ...] = (
    Anchor(
        name="gold",
        supply_is="cumulative extraction, set by geology and mining effort",
        determinate=True, responsive=False, registered=None,
        advocates_say=(
            "indifference to capacity IS the property being bought: no "
            "institution can expand the base to solve a shortfall, so the unit "
            "cannot be debased by anyone's decision."
        ),
    ),
    Anchor(
        name="bitcoin",
        supply_is="a published issuance schedule fixed in protocol",
        determinate=True, responsive=False, registered=None,
        advocates_say=(
            "the schedule is knowable in advance by anyone, which is a stronger "
            "guarantee than gold's: extraction responds to price, a protocol "
            "does not respond to anything."
        ),
    ),
    Anchor(
        name="fiat",
        supply_is="issuance by an institution exercising discretion",
        determinate=False, responsive=None, registered=None,
        advocates_say=(
            "discretion is the feature. A base that MUST contract when capacity "
            "falls is procyclical; the ability to expand into a shortfall is "
            "what a lender of last resort is for."
        ),
    ),
    Anchor(
        name="debt money",
        supply_is="credit extended against expected future production",
        determinate=False, responsive=None, registered=None,
        advocates_say=(
            "tying issuance to a promise of future production directs capital "
            "toward what someone is willing to underwrite, which no physical "
            "census can assess."
        ),
    ),
    Anchor(
        name="labour voucher",
        supply_is="hours worked",
        determinate=True, responsive=True, registered=False,
        advocates_say=(
            "the unit is denominated in the thing that actually produces, and "
            "it needs no commodity and no central issuer."
        ),
    ),
    Anchor(
        name="energy certificate",
        supply_is="a physical energy budget",
        determinate=True, responsive=True, registered=False,
        advocates_say=(
            "energy is measurable without dispute, conserved, and bounds every "
            "physical process — a harder constraint than labour, which varies "
            "in intensity and skill."
        ),
    ),
    Anchor(
        name="mutual credit",
        supply_is="bilateral obligations recorded within a community",
        determinate=True, responsive=True, registered=True,
        advocates_say=(
            "obligation is registered by both parties at the moment it is "
            "incurred, needs no external anchor, and has run continuously in at "
            "least one economy since 1934."
        ),
    ),
    Anchor(
        name="HOURS",
        supply_is="verified fulfilment of registered obligation",
        determinate=True, responsive=True, registered=True,
        advocates_say=(
            "the unit and the obligation are the same kind of quantity, so a "
            "maintenance requirement can be stated as a census rather than a "
            "valuation, and no accounting doctrine enters."
        ),
    ),
)


def determinacy_table() -> list[dict]:
    """
    The classification, one row per anchor. units: none — this is a taxonomy.

    Worked reading: `fiat` and `debt money` carry `determinate=False` and
    therefore `responsive=None`. That is not a gap in the data; it is the
    finding. An anchor whose issuance is discretionary has no response to a
    capacity shock that follows from what it IS.
    """
    return [
        {
            "anchor":        a.name,
            "supply_is":     a.supply_is,
            "determinate":   a.determinate,
            "responsive":    a.responsive,
            "registered":    a.registered,
            "advocates_say": a.advocates_say,
        }
        for a in ANCHORS
    ]


def hours_shock_response(
    population: float = 1_000_000.0,
    capability: float = 0.40,
    working_age_share: float = 0.63,
    employment_rate: float = 0.70,
    hours_per_worker: float = 2080.0,
) -> dict:
    """
    HOURS' own response, MEASURED — the one row in the table that is computed.

    Governing comparison: hold the frame fixed, halve one physical capacity at a
    time, and report the proportional change in obligation and in minting.
    units: fractions.

    THE FRAME IS AN ARGUMENT, NOT A DEFAULT. Labour supply is
    `population × working_age_share × employment_rate × hours_per_worker`;
    multiplying an hours-per-EMPLOYED-worker figure by working-age population
    would assume full employment and overstate supply.

    Worked example (shipped defaults): halving labour cuts minting by about half
    while the obligation does not move at all, and the unmet part is reported as
    deferred rather than absorbed.

    THE ECOLOGICAL ROW IS WHERE THIS ANCHOR LOSES, and it is reported for that
    reason. Phases 4e/4f relocated the recurring ecological obligation to the
    Ground Use Fee, which is not on this path, so ecosystem condition moves the
    monetary base by nothing at all.
    """
    labour = population * working_age_share * employment_rate * hours_per_worker
    accepted = inspect.signature(eoh_to_teh_pipeline).parameters
    assert "available_labor_eoh" in accepted

    def run(capital_mult: float = 1.0, labour_mult: float = 1.0,
            health: float = 0.70) -> dict:
        return eoh_to_teh_pipeline(
            epsilon=capability, population=population,
            capital_stock=2.0e9 * capital_mult, capital_age_ratio=0.50,
            ecosystem_health=health, monitoring_capability=0.70,
            available_labor_eoh=labour * labour_mult,
        )

    base = run()
    shocks = {
        "labour_halves":     run(labour_mult=0.5),
        "capital_halves":    run(capital_mult=0.5),
        "ecosystem_halves":  run(health=0.35),
    }
    rows = {}
    for label, r in shocks.items():
        rows[label] = {
            "obligation_change": r["total_eoh"] / base["total_eoh"] - 1.0,
            "minting_change":    r["teh_created"] / base["teh_created"] - 1.0,
            "deferred":          r["deferred_total"],
        }
    return {
        "frame": {
            "population": population, "labour_eoh": labour,
            "capability": capability, "hours_per_worker": hours_per_worker,
        },
        "baseline": {"obligation": base["total_eoh"],
                     "minting": base["teh_created"]},
        "shocks": rows,
        "responds_to_labour":    rows["labour_halves"]["minting_change"] < -0.10,
        "responds_to_capital":   rows["capital_halves"]["minting_change"] < -0.10,
        "responds_to_ecosystem": rows["ecosystem_halves"]["minting_change"] < -0.10,
    }


def the_defensible_claim() -> dict:
    """
    The comparative statement the classification supports, and no more.

    It is a claim about the SHAPE of the table — which anchors hold which
    combination of properties — not about which is better. Every term in it is
    checkable from `ANCHORS` and none of it requires a rival to be simulated.
    """
    both = [a.name for a in ANCHORS
            if a.determinate and a.responsive and a.registered]
    indeterminate = [a.name for a in ANCHORS if not a.determinate]
    indifferent = [a.name for a in ANCHORS
                   if a.determinate and a.responsive is False]
    unregistered = [a.name for a in ANCHORS if a.registered is False]
    return {
        "determinate_responsive_registered": both,
        "indeterminate": indeterminate,
        "determinate_but_indifferent": indifferent,
        "responsive_but_unregistered": unregistered,
        "claim": (
            "Of the anchors surveyed, "
            f"{len(indeterminate)} have no capacity response that follows from "
            f"their definition ({', '.join(indeterminate)}); "
            f"{len(indifferent)} are responsive to nothing by design "
            f"({', '.join(indifferent)}); and of those whose base does move "
            f"with physical activity, {', '.join(unregistered)} count activity "
            f"that fulfils no recognised obligation. "
            f"{' and '.join(both)} hold all three properties."
        ),
        "and_this_is_not_a_ranking": (
            "Whether a responsive base is preferable to an indifferent one is a "
            "normative question this module does not answer. Each anchor's own "
            "strongest reading is carried in `advocates_say` precisely so the "
            "reader can apply their own criterion."
        ),
    }


def ecological_response_by_path(
    epsilon: float = 0.40, healthy: float = 0.70, degraded: float = 0.35,
) -> dict:
    """
    The ecological zero, read on both paths — it is one path, not the system.

    Phases 4e/4f moved the recurring ecological obligation out of the domain and
    into the Ground Use Fee. Measuring only the minting pipeline therefore finds
    NO response to ecosystem condition, which is true and badly incomplete: the
    obligation did not vanish, it changed address.

    units: EOH/yr for the relocated obligation, fractions for the ratios.

    Worked example (shipped defaults): halving ecosystem health leaves minting
    exactly unchanged and roughly DOUBLES what the fee is asked to carry.

    The honest statement is therefore not that this framework is blind to
    ecological collapse. It is that **the monetary base is blind to it and the
    land fee is not** — which is a design consequence of the partition, and a
    reader can decide whether an anchor whose supply ignores ecological
    condition is what they want.
    """
    def relocated(health: float) -> float:
        return float(ecological_allocation(
            ecosystem_health=health, epsilon=epsilon, available_teh=1.0e9,
        )["relocated_to_guf"])

    a, b = relocated(healthy), relocated(degraded)
    return {
        "healthy_health": healthy, "degraded_health": degraded,
        "relocated_healthy": a, "relocated_degraded": b,
        "fee_obligation_ratio": (b / a) if a > 0.0 else float("inf"),
        "base_responds": False,
        "fee_responds": b > a,
        "verdict": (
            "the monetary base does not respond to ecosystem condition; the "
            "ground-use fee does, and its obligation rises by a factor of "
            f"{(b / a) if a > 0.0 else float('inf'):.2f} when health halves"
        ),
    }


def registration_leverage(epsilon: float = 0.40) -> dict:
    """
    How much of the money supply registration controls — the defence measured as
    an attack surface.

    Governing comparison: scale the registration share and read the mint.
    units: elasticity, dimensionless.

    THE SAME MECHANISM IS BOTH. Registration is what disqualifies the
    hole-digger, and it is the only lever that moves minting at all — five
    fiscal levers were perturbed in `tests/test_one_mint_path.py` and none of
    them reaches it. So an actor who controls what counts as a registered
    obligation controls the money supply, at UNIT ELASTICITY and with nothing
    else able to offset them.

    That is not a refutation of the anchor; it is the price of the property.
    Every anchor concentrates trust somewhere — gold in geology, protocol money
    in a schedule, fiat in an institution — and this one concentrates it in the
    register. What it means is that the framework's contestability work, which
    is about EXIT, does not address capture of the register, which is about
    VOICE, and nothing here tests it.

    Worked example: doubling the registered share exactly doubles the mint.
    """
    base = eoh_to_teh_pipeline(epsilon=epsilon)
    share, mint = base["registration_share"], base["teh_created"]
    points = {}
    for mult in (0.5, 1.5, 2.0):
        r = eoh_to_teh_pipeline(
            epsilon=epsilon, registration_share=share * mult,
            personal_registration_share=share * mult,
        )
        points[mult] = r["teh_created"] / mint
    elasticities = [points[m] / m for m in points]
    return {
        "baseline_share": share, "baseline_mint": mint,
        "mint_ratio_at_share_multiple": points,
        "elasticity": sum(elasticities) / len(elasticities),
        "is_unit_elastic": all(abs(e - 1.0) < 1e-9 for e in elasticities),
        "is_the_only_lever": True,   # pinned in tests/test_one_mint_path.py
        "verdict": (
            "registration is the sole lever on minting and moves it one for "
            "one; the property that disqualifies unproductive work is the same "
            "property that concentrates capture risk in the register"
        ),
    }


def floor_claim_across_the_arc(
    floor_teh: float = 1500.0,
    points: tuple[float, ...] = (0.0, 0.40, 0.90, 0.99),
) -> dict:
    """
    What a fixed floor entitlement buys, across the arc.

    units: baskets per year at `floor_teh`.

    The stock identity says a unit is a claim; this says what the GUARANTEED
    portion of that claim is worth over time. Measured, it does not merely hold
    — it strengthens, because the basket's price is tied to the human labour
    content of delivering it and that content falls.

    **THIS IS AN INTERNAL RESULT AND MUST BE READ AS ONE.** It follows from the
    framework's own price model, so it is a consistency property, not evidence
    that a unit would command that basket in any actual exchange. Above the
    floor there is no such statement to make: the discovery layer is a stub.

    Worked example: the same floor buys about five and a half times as many
    baskets at the top of the arc as at the bottom.
    """
    rows = {c: floor_teh / basket_price(c) for c in points}
    values = [rows[c] for c in points]
    return {
        "floor_teh": floor_teh,
        "baskets_by_capability": rows,
        "gain": values[-1] / values[0],
        "monotone_non_decreasing": all(
            values[i] <= values[i + 1] + 1e-12 for i in range(len(values) - 1)
        ),
        "is_an_internal_consistency_result": True,
        "verdict": (
            "the guaranteed floor claim strengthens across the arc by a factor "
            f"of {values[-1] / values[0]:.2f}; this follows from the framework's "
            "own price model and is not a claim about market exchange"
        ),
    }


def what_this_does_not_establish() -> tuple[str, ...]:
    """The limits, stated where a reader will meet them."""
    return (
        "That a responsive base is better than an indifferent one. That is "
        "normative and is not computed anywhere in this repository.",
        "That a unit commands anything in EXCHANGE. `floor_claim_across_the_arc` "
        "shows the guaranteed floor claim strengthening, but that follows from "
        "this framework's own price model — an internal consistency result, not "
        "a market one. Above the floor the discovery layer is a stub.",
        "That HOURS responds to capacity in general. Measured, it responds "
        "strongly to LABOUR capacity and weakly to capital. Its MONETARY BASE "
        "does not respond to ecosystem condition at all — though the ground-use "
        "fee does, and roughly doubles; see `ecological_response_by_path`.",
        "That the rivals are well modelled. They are not modelled at all. Each "
        "is classified from its own definition at its advocates' strongest "
        "reading, which is the only version of this comparison worth running.",
        "That registration is capture-resistant. MEASURED, it is the sole lever "
        "on minting and moves it at unit elasticity, so whoever controls what "
        "counts as a registered obligation controls the money supply with "
        "nothing able to offset them — the same failure mode discretionary "
        "issuance is criticised for. The contestability work addresses EXIT, "
        "not capture of the register. See `registration_leverage`.",
    )
