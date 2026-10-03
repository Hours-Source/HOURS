"""
scenarios/sensitivity — Parameter sensitivity analysis tools.

Tools for understanding how the EOH/fiscal system responds to changes in
key parameters across the ε arc. Answers questions like: "how much does
Trust solvency change if the levy rate drops by 10%?"

Canonical cross-sectional sensitivity (Δmetric per Δε) is in
hours_eoh.core.eoh_generation.epsilon_delta_sensitivity().
This module provides aggregate fiscal and scenario-level sweeps.

Mission Statement: §"The system must remain coherent across the full
automation arc."
"""

from __future__ import annotations
from typing import Callable

from hours_eoh.data import (
    EPSILON_ARC_MAX,
    CANONICAL_CAPITAL_AGE_BASE,
    REFERENCE_FRAME_POPULATION,
    ECOSYSTEM_HEALTH_DEFAULT,
    SUFF_LEVY_RATE,
    DEP_RATE,
    DIV_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    CAPITAL_STOCK_DEFAULT,
)
from hours_eoh.core.fiscal import fiscal_snapshot

# Re-export the core cross-sectional sensitivity function at the canonical
# scenarios layer so callers can import from one place.
from hours_eoh.core.eoh_generation import (  # noqa: F401
    epsilon_delta_sensitivity, resolve_capital_stock,
)
from hours_eoh.core.fiscal import resolve_trust_balance


def fiscal_parameter_sweep(
    parameter: str,
    values: list[float],
    epsilon: float = 0.40,
    population: float = REFERENCE_FRAME_POPULATION,
    trust_balance: float | None = None,
    labor_income: float | None = None,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
    ecosystem_health: float = ECOSYSTEM_HEALTH_DEFAULT,
) -> dict:
    """
    Sweep a single fiscal parameter across a list of values at a given ε.

    Runs fiscal_snapshot() for each value in `values`, varying only the
    named parameter. All other inputs remain at their defaults. Records
    surplus_deficit, solvency, and the total Trust expenditure at each value.

    Supported parameters:
      "levy_rate"        — overall levy rate (applied to both levy buckets)
      "dep_rate"         — Trust depreciation rate
      "div_rate"         — Trust dividend fraction
      "floor_fraction"   — fraction of population receiving guarantee. Swept
                           against `design="shipped"`, the only design that
                           reads it; under V1 it moves nothing.
      "need_fraction"    — V1: share of ON-LEDGER people the guarantee reaches
      "capital_age_ratio" — mean asset age ratio (affects stewardship cost)
  "trust_per_capita" — PRIOR WORK brought per person, in TEH/person; applied
                       as trust_balance = value x population. 0.0 is a
                       subsistence founding. NOTE the guarantee is Trust-
                       INDEPENDENT under V1, so `guarantee_cost` is flat across
                       this sweep by construction and `surplus_deficit` is
                       what moves, through the dividend.

    Args:
        parameter: Name of the parameter to sweep (see above).
        values: List of parameter values to test.
        epsilon: Automation level [0.0, 0.99]. Default: 0.40.
        population: Population.
        trust_balance: Trust fund balance.
        labor_income: Annual labour income (TEH/year). None (default) → the
            MINT at this ε and population (wage doctrine). It defaulted to
            2.2e9 — ~4.4× the mint at ε=0.40 and unscaled by population —
            until 2026-09-30.
        capital_stock_teh: Capital stock in TEH.
        capital_age_ratio: Mean asset age as fraction of design life.
        ecosystem_health: Ecological health [0,1].

    Returns:
        dict: {
          "parameter":   str,
          "epsilon":     float,
          "results":     list[dict],   (one per value; includes parameter_value + key metrics)
          "solvent_range": tuple[float | None, float | None],  (min, max solvent value)
        }

    Raises:
        ValueError: If parameter is not one of the supported names.
    """
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    if labor_income is None:
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        labor_income = float(eoh_to_teh_pipeline(
            epsilon, population=population, capital_stock=capital_stock_teh,
        )["teh_created"])
    # `need_fraction` added 2026-09-16 with the V1 adoption. `floor_fraction`
    # survives but is swept against `design="shipped"`, because that is the only
    # design that reads it: under V1 it moved nothing, and a swept parameter
    # that changes no output is failure mode 5 wearing a sweep's clothes.
    SUPPORTED = {"levy_rate", "dep_rate", "div_rate", "floor_fraction",
                 "need_fraction", "capital_age_ratio", "trust_per_capita"}
    if parameter not in SUPPORTED:
        raise ValueError(f"parameter must be one of {SUPPORTED}, got '{parameter}'")

    results = []
    solvent_values = []

    for val in values:
        kwargs: dict = dict(
            trust_balance=trust_balance,
            labor_income=labor_income,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            population=population,
            epsilon=epsilon,
            ecosystem_health=ecosystem_health,
        )

        if parameter == "levy_rate":
            kwargs["levy_rates"] = {"sufficiency": val}
        elif parameter == "dep_rate":
            kwargs["dep_rate"] = val
        elif parameter == "div_rate":
            kwargs["div_rate"] = val
        elif parameter == "floor_fraction":
            kwargs["floor_fraction"] = val
            kwargs["design"] = "shipped"
        elif parameter == "need_fraction":
            kwargs["need_fraction"] = val
        elif parameter == "capital_age_ratio":
            kwargs["capital_age_ratio"] = val
        elif parameter == "trust_per_capita":
            # PRIOR WORK BROUGHT, per person (2026-09-17). Swept per-capita and
            # multiplied up, because the frame holds INTENSITY fixed, not the
            # aggregate — sweeping a raw balance at a fixed population would
            # confound the level with the frame. 0.0 is a subsistence founding
            # and is a valid point, not an edge case.
            kwargs["trust_balance"] = val * population

        snap = fiscal_snapshot(**kwargs)
        results.append({
            "parameter_value":    val,
            "solvent":            snap["solvent"],
            "surplus_deficit":    snap["trust"]["surplus_deficit"],
            "total_expenditure":  snap["trust"]["total_expenditure"],
            "levy_collected":     snap["levies"]["total_levied"],
            "guarantee_cost":     snap["guarantee"]["total_cost_teh"],
        })
        if snap["solvent"]:
            solvent_values.append(val)

    solvent_range = (
        (min(solvent_values), max(solvent_values)) if solvent_values else (None, None)
    )

    return {
        "parameter":     parameter,
        "epsilon":       epsilon,
        "results":       results,
        "solvent_range": solvent_range,
    }


def eoh_arc_sensitivity(
    epsilon_start: float = 0.0,
    epsilon_end: float = EPSILON_ARC_MAX,
    n_points: int = 20,
    delta_epsilon: float = 0.05,
) -> list[dict]:
    """
    Report epsilon_delta_sensitivity() across the arc from epsilon_start to epsilon_end.

    Useful for identifying which ε windows produce the largest changes in
    EOH demand, labor income, and registration per unit of automation advance.

    Every row is a full Δε step INSIDE [epsilon_start, epsilon_end]: the base
    points span [start, end − Δε] for an advance (and [start − Δε, end] for a
    retreat), so the last step lands on the end. Until 2026-10-03 the bases
    spanned [start, end] and the last row stepped 0.99 → 0.99 — a clamped,
    empty step reported as "0.0%" on the steepest window of the arc.

    Args:
        epsilon_start: Starting ε value.
        epsilon_end: Ending ε value.
        n_points: Number of evaluation points.
        delta_epsilon: Δε used at each evaluation point.

    Returns:
        List of epsilon_delta_sensitivity() result dicts, one per ε point.

    Raises:
        ValueError: if |Δε| exceeds the range, so no full step fits.
    """
    from hours_eoh.core.eoh_generation import epsilon_delta_sensitivity

    lo = epsilon_start - min(delta_epsilon, 0.0)
    hi = epsilon_end - max(delta_epsilon, 0.0)
    if hi < lo:
        raise ValueError(
            f"|delta_epsilon| = {abs(delta_epsilon)} does not fit in "
            f"[{epsilon_start}, {epsilon_end}]")
    step = (hi - lo) / max(n_points - 1, 1)
    return [
        epsilon_delta_sensitivity(lo + i * step, delta_epsilon)
        for i in range(n_points)
    ]
