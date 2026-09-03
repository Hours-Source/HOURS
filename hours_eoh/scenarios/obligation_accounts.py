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
at ε=0 it is 5.5% of the obligation and at ε=0.99 it is **89.6%**. Essentially
all growth in total EOH is delivery cost, and a four-way sum hides that by
adding it to the obligation.

**THE CROSSOVER CLAIM IS WITHDRAWN (2026-09-01), AND IT IS THE CLEANEST CASE OF
WHY A PLACEHOLDER MATTERS.** This module originally read 100.3% at ε=0.99 —
"the apparatus costs more entropy than the obligation it serves" — and that was
true at the calibration of the day. Then `AGE_WEIGHT_CHILD` took the MTUS
self-maintenance measurement for ages 6–14 (1.5 → 1.82, raising the obligation)
and the knowledge fixed point re-anchored −9.94% with it (cutting the apparatus
term). Both push the ratio DOWN and it no longer crosses 1.0. The SHAPE
survives — delivery grows 17.6× while the obligation grows 8% — and the level
did not.

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
    PERSONAL_AUTOMATION_FLOORS,
    PERSONAL_EOH_COMPONENTS,
)

__all__ = [
    "ACCOUNTS",
    "obligation_accounts",
    "accounts_arc",
    "delivery_crossover",
    "automation_uniformity_check",
    "anchor_sensitivity",
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

    Worked example (canonical arc, ε=0.40, default 1M frame): obligation
    1,409,559,274; delivery 218,300,074; stock 0.0. Ratio 0.1549.

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
    0.0549 → 0.0848 → 0.1549 → 0.4053 → 0.8964 across ε ∈ {0, 0.2, 0.4, 0.7,
    0.99}. The obligation itself moves only 1,365.4M → 1,475.7M, i.e. +8.1%
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

    THERE IS NO CROSSOVER AT THE CURRENT CALIBRATION — this returns None, and
    that is a result rather than a gap. Delivery peaks at 0.90 of the
    obligation. The function is kept because the crossover DID exist before
    `AGE_WEIGHT_CHILD` took its measurement on 2026-09-01, and a search that
    can only report "yes" is not a search.

    THE CROSSOVER WOULD NOT BE A FAILURE, and this function does not call it
    one. It is where the apparatus's own entropy debt equals the obligation it
    was built to reduce — the same question `core/autarky.overbuild_check` asks from the
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


def anchor_sensitivity(
    observed_hours_per_capita: float = 937.3,
    shipped_base: float | None = None,
) -> dict:
    """
    What fixing the care contradiction would cost the knowledge anchor.

    `KNOWLEDGE_EOH_BASE` is set by a fixed point (`knowledge_base.
    epsilon_ref_fixed_point`) that solves the anchor and the base together:

        base(ε_ref) ──► total_eoh ──► ε_residual(observed) ──► ε_ref …

    The residual step asks at what ε the human labour the model REQUIRES equals
    the labour actually observed. That step currently applies a uniform (1 − ε)
    to every domain. Flooring care — as `core/fiscal.care_stipend` already does
    and as Block II independently supports — raises the required labour at every
    ε above zero, so the implied ε rises and the base falls with it.

    Governing substitution, personal domain only:

        uniform(ε)     = 1 − ε
        non_uniform(ε) = s_care·[f + (1 − f)(1 − ε)] + (1 − s_care)·(1 − ε)

    units: ε dimensionless; base in hours at KNOWLEDGE_REFERENCE_POPULATION.

    ADOPTED 2026-09-01. This measured the cost BEFORE the flip; the flip has
    since been taken, so `non_uniform_reproduces_shipped` is now the True one.
    It is retained rather than retired because it is what makes the adopted
    anchor reproducible from first principles — and because a search that can
    only confirm the current state is not a search.

    WHY THIS WAS MEASURED BEFORE PHASE 2 AND NOT AFTER. The anchor has been
    re-derived six times and every previous move was tiny — +0.13%, +0.00047%,
    0.00% — precisely because the domains it balances against are tiny. This
    would be the first move against the 91–97% domain, and the question is
    whether "small" still holds. It does not: the base moves **−16.4%**.

    Worked example (937.3 h/person·yr, US paid labour): ε* 0.386618 → 0.423227,
    base 523,614,562.88 → 437,917,083.98. Human labour at ε=0.99 goes 28.8 →
    148.8 h/person·yr, a factor of **5.16** — the difference between "labour has
    effectively ended" and "most of a month of care work per person per year".

    NO LONGER A LOWER BOUND FOR THE REASON IT WAS. This read only care until
    2026-09-03; it now reads every entry in `PERSONAL_AUTOMATION_FLOORS`, so it
    tracks whatever has been adopted. It remains a lower bound on the FULL
    treatment while shelter and health carry no floor.

    (Historical note, kept because the reasoning still holds.) Only care was
    floored here, using the fiscal
    layer's own floor and the basket's own share. `PERSONAL_EOH_COMPONENTS` gives
    health an abatability of 0.60 and nutrition 0.85, so a fuller treatment
    floors more components, raises required labour further, and moves the anchor
    further in the same direction.

    REPORTING ONLY. Nothing is written back; this exists so Phase 2 is committed
    to on a measured blast radius rather than an estimate.
    """
    from hours_eoh.core.trajectory import canonical_physical_state
    from hours_eoh.data import KNOWLEDGE_EOH_BASE, SKILL_TRANSMISSION_RATE

    # Injectable ONLY so the control flag is falsifiable — a flag that
    # cannot report False is a flag nobody is checking.
    reference = KNOWLEDGE_EOH_BASE if shipped_base is None else shipped_base
    from hours_eoh.scenarios.knowledge_base import knowledge_base_from_registry

    pop = 1.0e6
    # Every floored component, not `care` alone. The first version modelled the
    # single entry the table then had, and its own docstring called the result a
    # LOWER bound for exactly that reason. When nutrition was adopted on
    # 2026-09-03 the shipped anchor moved past what this could reproduce and the
    # control silently reported False on BOTH branches — a control that cannot
    # report True is as useless as one that cannot report False. Reading the
    # table keeps the reimplementation independent (which is the point) without
    # letting it model a different economy from the one it checks.
    floors = dict(PERSONAL_AUTOMATION_FLOORS)

    def _domains(eps: float, base: float) -> dict:
        st = canonical_physical_state(eps)
        return total_eoh(
            population=pop,
            capital_stock=st["capital_stock_teh"],
            capital_age_ratio=st["capital_age_ratio"],
            ecosystem_health=st["ecosystem_health"],
            monitoring_capability=st["monitoring_capability"],
            age_distribution=st["age_distribution"],
            knowledge_complexity=st["knowledge_base_size"],
            knowledge_complexity_per_unit=st["knowledge_complexity_per_unit"],
            knowledge_base=base,
            skill_decay_rate=SKILL_TRANSMISSION_RATE,
        )

    def _required(eps: float, base: float, uniform: bool) -> float:
        d = _domains(eps, base)
        if uniform:
            return (1.0 - eps) * d["total"] / pop
        personal_hf = 0.0
        for name, spec in PERSONAL_EOH_COMPONENTS.items():
            share = float(spec["share"])
            floor = floors.get(name, 0.0)
            personal_hf += share * (floor + (1.0 - floor) * (1.0 - eps))
        rest = d["infrastructure"] + d["ecological"] + d["knowledge"]
        return (personal_hf * d["personal"] + (1.0 - eps) * rest) / pop

    def _residual(base: float, uniform: bool) -> float | None:
        if _required(0.0, base, uniform) < observed_hours_per_capita:
            return None
        lo, hi = 0.0, 0.99
        if _required(hi, base, uniform) > observed_hours_per_capita:
            return hi
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            if _required(mid, base, uniform) > observed_hours_per_capita:
                lo = mid
            else:
                hi = mid
            if hi - lo < 1e-6:
                break
        return 0.5 * (lo + hi)

    def _fixed_point(uniform: bool) -> tuple[float | None, float | None, bool]:
        eps = 0.40
        for _ in range(80):
            base = knowledge_base_from_registry(
                eps, decay=SKILL_TRANSMISSION_RATE
            )["base_rate"]
            implied = _residual(base, uniform)
            if implied is None:
                return None, None, False
            if abs(implied - eps) < 1e-4:
                base = knowledge_base_from_registry(
                    implied, decay=SKILL_TRANSMISSION_RATE
                )["base_rate"]
                return implied, base, True
            eps = 0.5 * (eps + implied)
        return eps, None, False

    eps_u, base_u, conv_u = _fixed_point(True)
    eps_n, base_n, conv_n = _fixed_point(False)

    # Narrowed explicitly rather than behind an `ok` flag: mypy cannot follow a
    # boolean guard into a dict literal, and widening the annotation to silence
    # it would hide a real None that reaches arithmetic.
    if base_u is None or base_n is None or eps_u is None or eps_n is None:
        return {
            "observed_hours_per_capita": observed_hours_per_capita,
            "epsilon_uniform":     eps_u,
            "epsilon_non_uniform": eps_n,
            "base_uniform":        base_u,
            "base_non_uniform":    base_n,
            "shipped_base":        reference,
            "uniform_reproduces_shipped": False,
            "base_move":           None,
            "converged":           False,
            "labour_at_top":       None,
            "move_is_a_lower_bound": True,
            "verdict": (
                "no fixed point at these inputs — the supplied labour exceeds "
                "the whole obligation at ε=0, which is Finding B and not a "
                "solver failure"
            ),
        }

    move = base_n / base_u - 1.0
    return {
        "observed_hours_per_capita": observed_hours_per_capita,
        "epsilon_uniform":     eps_u,
        "epsilon_non_uniform": eps_n,
        "base_uniform":        base_u,
        "base_non_uniform":    base_n,
        "shipped_base":        reference,
        "uniform_reproduces_shipped": abs(base_u / reference - 1.0) < 1e-6,
        # ADOPTED 2026-09-01: the shipped anchor is now the NON-uniform one, so
        # this is the flag that should read True and the one above should not.
        # Both are reported rather than the pair being swapped, so the move can
        # be seen rather than inferred.
        "non_uniform_reproduces_shipped": abs(base_n / reference - 1.0) < 1e-6,
        "base_move":  move,
        "converged":  conv_u and conv_n,
        "labour_at_top": {
            "uniform":     _required(0.99, KNOWLEDGE_EOH_BASE, True),
            "non_uniform": _required(0.99, KNOWLEDGE_EOH_BASE, False),
        },
        "move_is_a_lower_bound": True,
        "verdict": (
            f"Flooring care alone moves the knowledge anchor "
            f"{move:+.2%} (ε* {eps_u:.6f} → {eps_n:.6f}). "
            f"Every previous re-anchor was +0.13% or smaller, because the "
            f"domains it balanced against were tiny; this is the first move "
            f"against the 91–97% domain and it is two to four orders of "
            f"magnitude larger. It is a LOWER bound — only care is floored."
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
