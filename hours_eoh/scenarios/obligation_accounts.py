"""
The three accounts: what is OWED, what DELIVERING it costs, what is owed FROM
THE PAST.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. No constant moves and no shipped number changes;
`TestAccountsChangeNothing` fails the moment that stops being true. This module
re-presents quantities `total_eoh` already computes — it exists to make a
proposed reframing arguable on evidence before it is adopted, which is the order
that has worked here (Phase 2 measured the ×100 before proposing to move it;
Phase 4f derived the ecological level before defaulting it).

WHY THE FOUR-DOMAIN SUM MAY BE THE WRONG PRESENTATION
------------------------------------------------------
`total_eoh` returns personal + infrastructure + ecological + knowledge as four
co-equal domains. Measured, they are not co-equal and never have been: personal
is 91–97% of the total at every ε. More importantly they are not the same KIND
of quantity, and adding them hides the difference:

    OBLIGATION   what is owed, independent of how it is met. Personal EOH is
                 biologically anchored — food, water, shelter, care, health —
                 and the civilisational knowledge corpus is renewed whatever
                 the capital stock. Neither exists because we built something.

    DELIVERY     what meeting the obligation COSTS. Infrastructure EOH is the
                 entropy debt of the apparatus; apparatus knowledge is the
                 pre-time needed to run it. Both exist ONLY because the
                 apparatus does, and both are incurred to reduce the obligation
                 (`abatement_fraction`, Block II). A delivery cost that exceeds
                 what it abates is an overbuild, not an obligation.

    STOCK        what is owed from the past. Thermal, restoration and visible
                 deferred ecological obligation are accumulated damage, not a
                 recurring requirement. The Phase 4 partition already moved
                 everything recurring in the ecological domain to GUF, so under
                 the shipped defaults the ecological domain IS this account.

THE HEADLINE THE SUM HIDES. Delivery grows against a nearly flat obligation:
at ε=0 it is 5.7% of the obligation and at ε=0.99 it is **100.3%** — the
apparatus costs more entropy than the obligation it serves. That crossover is
invisible in a four-way sum because both sides are added into one total.

WHAT THIS CORRECTS IN THE EXISTING SPLIT. Block III already gives
`total_eoh(basis="gross"|"final")` — base vs overhead — and this is NOT merely
a rename of it. `basis="final"` puts the ecological STOCKS in the base, so a
thermal obligation of 1e8 raises `total_base` by 1e8 and reads as though the
system owed more going forward. Legacy damage is not a forward obligation, and
separating the third account is what fixes that.

WHAT THIS DOES NOT SETTLE. The accounts are a presentation; ε is unchanged and
so is every fiscal result. Whether the reframe should be ADOPTED — whether
`total_eoh` should return this shape, and whether the corridor should bind on
delivery/obligation — is a charter decision and is not taken here.

Layer: scenarios/ — imports core/ and data; imported by neither.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    ARC_REPORTING_POINTS,
    CARE_AUTOMATION_FLOOR,
    PERSONAL_EOH_COMPONENTS,
)

__all__ = [
    "ACCOUNTS",
    "obligation_accounts",
    "accounts_arc",
    "delivery_crossover",
    "automation_uniformity_check",
    "accounts_report",
]

#: The three accounts, and what distinguishes them. Declared rather than
#: inferred, on the `TERM_BASIS` precedent: a category nobody has written down
#: is a category nobody has audited.
ACCOUNTS: dict[str, dict[str, str]] = {
    "obligation": {
        "question": "what is owed, independent of how it is met",
        "domains": "personal + civilisational knowledge",
        "exists_because": "the agent exists",
        "epsilon_behaviour": (
            "nearly flat — it is what must be met, not what meeting it costs"
        ),
    },
    "delivery": {
        "question": "what meeting the obligation costs",
        "domains": "infrastructure + apparatus knowledge",
        "exists_because": "an apparatus was built to reduce the obligation",
        "epsilon_behaviour": (
            "rises with the capital stock; crosses the obligation late in the arc"
        ),
    },
    "stock": {
        "question": "what is owed from the past",
        "domains": "ecological (thermal + restoration + visible deferred)",
        "exists_because": "damage was done and not yet repaid",
        "epsilon_behaviour": (
            "carried, not generated — zero on every shipped path because no "
            "stock ships by default (Phase 4d/4e/4f)"
        ),
    },
}



def obligation_accounts(epsilon: float = 0.40, **state: Any) -> dict:
    """
    The three accounts at one ε, reconciling exactly with `total_eoh`.

    Governing identity — this is a PARTITION of the same quantities, so it must
    close to floating-point equality:

        obligation = personal + knowledge_civilisational
        delivery   = infrastructure + knowledge_apparatus
        stock      = ecological
        obligation + delivery + stock == total_eoh(...)["total"]

    units: EOH (entropy-obligation hours) per year, at the caller's frame.

    ε-behaviour: obligation is nearly flat (it is what must be met); delivery
    rises with the capital stock the arc builds; stock is carried and is 0.0 on
    every shipped path because no stock ships by default.

    Worked example (canonical arc, ε=0.40, default 1M frame):
    obligation 1,365,766,053 = personal 1,301,536,000 + civilisational
    64,230,053; delivery 227,491,276 = infrastructure 135,000,000 + apparatus
    92,491,276; stock 0.0. Ratio delivery/obligation = 0.1666.

    Args:
        epsilon: Automation level [0.0, 0.99].
        **state: Forwarded verbatim to `total_eoh` — population, capital_stock,
            thermal_obligation, and so on. Supplying a stock is how the third
            account becomes non-zero.

    Returns:
        dict with the three account totals, their components, the
        delivery/obligation ratio, and `reconciles` (must be True).

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    d = total_eoh(epsilon=epsilon, **state)

    obligation = d["personal"] + d["knowledge_civilisational"]
    delivery = d["infrastructure"] + d["knowledge_apparatus"]
    stock = d["ecological"]

    return {
        "epsilon":       epsilon,
        "obligation":    obligation,
        "delivery":      delivery,
        "stock":         stock,
        "obligation_components": {
            "personal":                d["personal"],
            "knowledge_civilisational": d["knowledge_civilisational"],
        },
        "delivery_components": {
            "infrastructure":       d["infrastructure"],
            "knowledge_apparatus":  d["knowledge_apparatus"],
        },
        "gross_total":   d["total"],
        "reconciles":    abs(obligation + delivery + stock - d["total"]) < 1e-6,
        "delivery_over_obligation": delivery / obligation if obligation else float("inf"),
        "delivery_share_of_gross":  delivery / d["total"] if d["total"] else 0.0,
        # The existing basis split, carried so the difference is visible rather
        # than argued: `total_base` puts the STOCK in the obligation account.
        "total_base_block_iii":      d["total_base"],
        "base_includes_stock":       stock > 0.0,
        "base_minus_accounts_oblig": d["total_base"] - obligation,
    }


def accounts_arc(
    *,
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **state: Any,
) -> list[dict]:
    """
    The three accounts across the arc — the table the four-domain sum hides.

    units: EOH/year, plus dimensionless ratios.

    Worked example (canonical, default frame): delivery/obligation runs
    0.0570 → 0.0888 → 0.1666 → 0.4486 → 1.0029 across ε ∈ {0, 0.2, 0.4, 0.7,
    0.99}. The obligation itself moves only 1,315.6M → 1,439.9M, i.e. +9.5%
    over the whole arc, so essentially all of the growth in total EOH is
    delivery cost.
    """
    return [obligation_accounts(e, **state) for e in points]


def delivery_crossover(tol: float = 1e-4, **state: Any) -> dict:
    """
    The ε at which the delivery cost first exceeds the obligation it serves.

    Governing condition:

        crossover = min{ ε : delivery(ε) ≥ obligation(ε) }

    units: dimensionless ε.

    Found by bisection on the arc rather than solved analytically, because the
    knowledge apparatus fraction (1 − 1/cpu) and the canonical capital path are
    both non-linear in ε.

    THE CROSSOVER IS NOT A FAILURE, and this function does not call it one. It
    is where the apparatus's own entropy debt equals the obligation it was built
    to reduce — the same question `core/autarky.overbuild_check` asks from the
    labour side, which reports an interior optimum and an overbuild threshold.
    Whether crossing it is acceptable depends on how much obligation the
    apparatus ABATES, which is Block II's `abatement_fraction` and is not in
    this account.

    Returns:
        dict with `crossover_epsilon` (None if it never crosses in [0, 0.99]),
        and the ratio at each end of the arc.
    """
    lo, hi = 0.0, 0.99
    if obligation_accounts(hi, **state)["delivery_over_obligation"] < 1.0:
        crossover = None
    else:
        while hi - lo > tol:
            mid = (lo + hi) / 2.0
            if obligation_accounts(mid, **state)["delivery_over_obligation"] >= 1.0:
                hi = mid
            else:
                lo = mid
        crossover = hi

    return {
        "crossover_epsilon": crossover,
        "ratio_at_zero":     obligation_accounts(0.0, **state)["delivery_over_obligation"],
        "ratio_at_top":      obligation_accounts(0.99, **state)["delivery_over_obligation"],
        "note": (
            "Not a failure condition. It is where the apparatus's entropy debt "
            "equals the obligation it reduces; whether that is acceptable "
            "depends on how much it abates (Block II), which this account does "
            "not carry."
        ),
    }


def automation_uniformity_check(epsilon: float = 0.99) -> dict:
    """
    Three statements this repo makes about whether care can be automated, and
    whether they agree. They do not.

    Governing comparison, at automation level ε:

        uniform(ε)  = 1 − ε                       (human_eoh_per_domain)
        care(ε)     = f + (1 − f)·(1 − ε)         (core/fiscal.care_stipend)
        implied(ε)  = s_care·care(ε) + (1 − s_care)·uniform(ε)

    where f = CARE_AUTOMATION_FLOOR and s_care is care's share of personal EOH
    from `PERSONAL_EOH_COMPONENTS`.

    units: dimensionless human-labour fractions.

    THE CONTRADICTION. `CARE_AUTOMATION_FLOOR`'s own tag block says relational
    care "cannot be automated at any ε — a commitment about what care IS", and
    Block II reaches the same conclusion independently: care is the least
    abatable component and 84.4% of the residual at full abatement. But
    `human_eoh_per_domain` applies the same (1 − ε) to every domain, and care is
    62.1% of personal EOH by the basket's own shares. So the fiscal layer models
    care as un-automatable while the generation layer automates it at the full
    rate — two accounts of one quantity, the `psi` vs `psi_applied` shape.

    Worked example (ε=0.99): uniform gives a human fraction of 0.0100; the
    fiscal floor gives care 0.1585; weighted by care's 62.1% share the implied
    personal human fraction is 0.1022 — **10.2× the uniform figure.**

    REPORTING ONLY. Resolving it means per-component automation rates, which is
    a change to `human_eoh_per_domain` and a theory-flagged decision.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    s_care = PERSONAL_EOH_COMPONENTS["care"]["share"]
    f = CARE_AUTOMATION_FLOOR
    uniform = 1.0 - epsilon
    care = f + (1.0 - f) * (1.0 - epsilon)
    implied = s_care * care + (1.0 - s_care) * uniform

    return {
        "epsilon":                epsilon,
        "care_share_of_personal": s_care,
        "care_automation_floor":  f,
        "uniform_human_fraction": uniform,
        "care_human_fraction":    care,
        "implied_human_fraction": implied,
        "understatement_factor":  implied / uniform if uniform else float("inf"),
        "agrees":                 abs(implied - uniform) < 1e-9,
        "verdict": (
            f"At ε={epsilon:.2f} `human_eoh_per_domain` gives every domain a "
            f"human fraction of {uniform:.4f}, while `care_stipend` floors care "
            f"at {care:.4f}. Care is {s_care:.1%} of personal EOH, so the "
            f"implied personal human fraction is {implied:.4f} — "
            f"{implied / uniform:.1f}× the uniform figure. The fiscal layer and "
            f"Block II agree that care resists automation; the generation layer "
            f"does not know it."
        ),
    }


def accounts_report(epsilon: float = 0.40, **state: Any) -> dict:
    """
    The Phase 0 report: the three accounts, the crossover, and the uniformity
    check, in one call. CLI: `eoh scenario run obligation_accounts`.
    """
    here = obligation_accounts(epsilon, **state)
    cross = delivery_crossover(**state)
    uniformity = automation_uniformity_check(0.99)
    arc = accounts_arc(**state)

    return {
        "epsilon":     epsilon,
        "accounts":    ACCOUNTS,
        "here":        here,
        "arc":         arc,
        "crossover":   cross,
        "uniformity":  uniformity,
        "verdict": (
            f"Obligation moves {arc[0]['obligation'] / 1e6:,.1f}M → "
            f"{arc[-1]['obligation'] / 1e6:,.1f}M EOH across the arc "
            f"({arc[-1]['obligation'] / arc[0]['obligation'] - 1.0:+.1%}), while "
            f"delivery moves {arc[0]['delivery'] / 1e6:,.1f}M → "
            f"{arc[-1]['delivery'] / 1e6:,.1f}M "
            f"({arc[-1]['delivery'] / arc[0]['delivery'] - 1.0:+.0%}). "
            f"Delivery/obligation runs {cross['ratio_at_zero']:.4f} → "
            f"{cross['ratio_at_top']:.4f}"
            + (f", crossing 1.0 at ε≈{cross['crossover_epsilon']:.3f}."
               if cross["crossover_epsilon"] is not None
               else ", never crossing 1.0.")
            + " Essentially all growth in total EOH is delivery cost, which a "
              "four-way sum hides by adding it to the obligation."
        ),
        "reporting_only": True,
    }
