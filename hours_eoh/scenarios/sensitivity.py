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
    TRUST_BASE_TEH,
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


def fiscal_parameter_sweep(
    parameter: str,
    values: list[float],
    epsilon: float = 0.40,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    labor_income: float = 2_200_000_000.0,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
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

    Args:
        parameter: Name of the parameter to sweep (see above).
        values: List of parameter values to test.
        epsilon: Automation level [0.0, 0.99]. Default: 0.40.
        population: Population.
        trust_balance: Trust fund balance.
        labor_income: Annual labor income (TEH/year).
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
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    # `need_fraction` added 2026-09-16 with the V1 adoption. `floor_fraction`
    # survives but is swept against `design="shipped"`, because that is the only
    # design that reads it: under V1 it moved nothing, and a swept parameter
    # that changes no output is failure mode 5 wearing a sweep's clothes.
    SUPPORTED = {"levy_rate", "dep_rate", "div_rate", "floor_fraction",
                 "need_fraction", "capital_age_ratio"}
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
    epsilon_end: float = 0.99,
    n_points: int = 20,
    delta_epsilon: float = 0.05,
) -> list[dict]:
    """
    Report epsilon_delta_sensitivity() across the arc from epsilon_start to epsilon_end.

    Useful for identifying which ε windows produce the largest changes in
    EOH demand, labor income, and registration per unit of automation advance.

    Args:
        epsilon_start: Starting ε value.
        epsilon_end: Ending ε value.
        n_points: Number of evaluation points.
        delta_epsilon: Δε used at each evaluation point.

    Returns:
        List of epsilon_delta_sensitivity() result dicts, one per ε point.
    """
    from hours_eoh.core.eoh_generation import epsilon_delta_sensitivity

    step = (epsilon_end - epsilon_start) / max(n_points - 1, 1)
    return [
        epsilon_delta_sensitivity(epsilon_start + i * step, delta_epsilon)
        for i in range(n_points)
    ]
