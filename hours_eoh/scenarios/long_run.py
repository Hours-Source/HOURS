"""
scenarios/long_run — Multi-period trajectory scenarios.

Three scenarios that exercise run_simulation() over extended arcs:

  canonical_arc_trajectory   — Full ε arc from start to end over N periods
  trust_depletion_stress     — Multi-stressor run; when does the Trust break?
  automation_transition_trajectory — Fixed epsilon_delta; track purchasing
                                     power and fiscal convergence

Each returns a structured result with "outcome" and a per-period summary
alongside the raw run_simulation() trajectory.

Mission Statement: §"The system must remain coherent across the full
automation arc"; §"Stress tests — identify failure boundaries."
"""

from __future__ import annotations
import math
from typing import Any

from hours_eoh.data import (
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
    ECOLOGICAL_THRESHOLD,
)
from hours_eoh.core.simulation import make_economy_state, run_simulation
from hours_eoh.core.prices import basket_price, floor_purchasing_power

_VALID_OUTCOMES = {"STABLE", "DEGRADED", "CRISIS"}


# ---------------------------------------------------------------------------
# Canonical Arc Trajectory
# ---------------------------------------------------------------------------

def canonical_arc_trajectory(
    epsilon_start: float = 0.0,
    epsilon_end: float = 0.99,
    n_periods: int = 20,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    **sim_kwargs: Any,
) -> dict:
    """
    Run the economy from epsilon_start to epsilon_end over n_periods.

    Computes epsilon_delta = (epsilon_end - epsilon_start) / n_periods and
    calls run_simulation(). Returns the raw trajectory plus a compact
    summary_table and a list of inflection_points (significant state transitions).

    Args:
        epsilon_start: Starting automation level [0.0, 0.99].
        epsilon_end:   Target automation level at end of run.
        n_periods:     Number of simulation periods.
        population:    Initial population.
        trust_balance: Initial Trust fund balance (TEH).
        capital_stock_teh: Initial capital stock (TEH).
        **sim_kwargs:  Additional kwargs forwarded to run_simulation() /
                       simulate_period() (e.g., ecological_degradation_rate).

    Returns:
        dict: {
          "scenario":           str,
          "epsilon_start":      float,
          "epsilon_end":        float,
          "n_periods":          int,
          "solvent_all":        bool,
          "first_insolvency":   int | None,
          "summary_table":      list[dict],   one row per period
          "inflection_points":  list[dict],   notable state transitions
          "raw":                dict,          full run_simulation() result
        }
    """
    epsilon_delta = (epsilon_end - epsilon_start) / max(n_periods, 1)
    initial_state = make_economy_state(
        epsilon=epsilon_start,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
    )

    raw = run_simulation(
        initial_state,
        n_periods=n_periods,
        epsilon_delta=epsilon_delta,
        **sim_kwargs,
    )

    summary_table = []
    for i, result in enumerate(raw["period_results"]):
        bp = basket_price(result["epsilon"])
        summary_table.append({
            "period":           result["period"],
            "epsilon":          result["epsilon"],
            "teh_created":      result["teh_created"],
            "trust_end":        result["trust_end"],
            "solvent":          result["solvent"],
            "ecosystem_health": result["ecosystem_health"],
            "basket_price":     bp,
        })

    inflection_points = _find_inflection_points(raw["period_results"])

    return {
        "scenario":          "canonical_arc_trajectory",
        "epsilon_start":     epsilon_start,
        "epsilon_end":       epsilon_end,
        "n_periods":         n_periods,
        "solvent_all":       raw["solvent_all"],
        "first_insolvency":  raw["first_insolvency"],
        "summary_table":     summary_table,
        "inflection_points": inflection_points,
        "raw":               raw,
    }


def _find_inflection_points(period_results: list[dict]) -> list[dict]:
    """Return periods where solvency changes, ecosystem crosses threshold, or trust sign changes."""
    points = []
    prev: dict | None = None
    for r in period_results:
        if prev is None:
            prev = r
            continue
        if r["solvent"] != prev["solvent"]:
            points.append({
                "period": r["period"],
                "type":   "solvency_change",
                "from":   prev["solvent"],
                "to":     r["solvent"],
            })
        eco_now  = r.get("ecosystem_health", 1.0)
        eco_prev = prev.get("ecosystem_health", 1.0)
        if (eco_prev > ECOLOGICAL_THRESHOLD >= eco_now
                or eco_now > ECOLOGICAL_THRESHOLD >= eco_prev):
            points.append({
                "period": r["period"],
                "type":   "ecosystem_threshold_cross",
                "from":   eco_prev,
                "to":     eco_now,
            })
        if prev["trust_end"] >= 0.0 > r["trust_end"] or prev["trust_end"] < 0.0 <= r["trust_end"]:
            points.append({
                "period": r["period"],
                "type":   "trust_sign_change",
                "from":   prev["trust_end"],
                "to":     r["trust_end"],
            })
        prev = r
    return points


# ---------------------------------------------------------------------------
# Trust Depletion Stress
# ---------------------------------------------------------------------------

def trust_depletion_stress(
    epsilon: float = 0.40,
    n_periods: int = 30,
    stressor_profile: dict | None = None,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
) -> dict:
    """
    Run a multi-stressor simulation and report when/whether the Trust breaks.

    stressor_profile keys (all optional, override simulate_period() defaults):
      ecological_degradation_rate    — ecosystem_health decline per period
      deferred_eco_growth_rate       — deferred EOH growth rate when stressed
      capital_aging_rate             — age_ratio increase per period
      capital_investment_rate        — fraction of labor_income reinvested

    Outcome classification:
      STABLE   — solvent every period
      DEGRADED — first insolvency after 50% of periods
      CRISIS   — first insolvency within the first third of periods

    Args:
        epsilon:          Starting automation level [0.0, 0.99].
        n_periods:        Number of periods to simulate.
        stressor_profile: Dict of simulate_period() overrides. None → defaults.
        population:       Initial population.
        trust_balance:    Initial Trust balance (TEH).
        capital_stock_teh: Initial capital stock.

    Returns:
        dict: {
          "scenario":              str,
          "epsilon":               float,
          "n_periods":             int,
          "stressor_profile":      dict,
          "first_insolvency":      int | None,
          "trust_floor":           float,   (minimum trust balance seen)
          "depletion_rate_per_period": float,
          "outcome":               str,
          "recommendation":        str,
          "raw":                   dict,    (full run_simulation() result)
        }
    """
    profile = stressor_profile or {}
    initial_state = make_economy_state(
        epsilon=epsilon,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
    )

    raw = run_simulation(initial_state, n_periods=n_periods, **profile)

    trust_values = [r["trust_end"] for r in raw["period_results"]]
    trust_floor  = min(trust_values) if trust_values else trust_balance
    first_ins    = raw["first_insolvency"]

    if trust_values:
        depletion_rate = (trust_balance - trust_values[-1]) / max(n_periods, 1)
    else:
        depletion_rate = 0.0

    if first_ins is None:
        outcome = "STABLE"
    elif first_ins > n_periods * 2 // 3:
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    if outcome == "STABLE":
        rec = (
            f"Trust remained solvent for all {n_periods} periods at ε={epsilon:.2f} "
            f"with stressor profile {profile}. "
            f"Minimum trust balance: {trust_floor:,.0f} TEH."
        )
    elif outcome == "DEGRADED":
        rec = (
            f"First insolvency at period {first_ins} (> {n_periods*2//3} periods). "
            f"System degrades under sustained stress but holds for majority of arc. "
            f"Monitor ecological and capital health."
        )
    else:
        rec = (
            f"CRISIS: First insolvency at period {first_ins} (within first third). "
            f"Stressor profile {profile} overwhelms the Trust rapidly. "
            f"Immediate intervention required."
        )

    return {
        "scenario":                  "trust_depletion_stress",
        "epsilon":                   epsilon,
        "n_periods":                 n_periods,
        "stressor_profile":          profile,
        "first_insolvency":          first_ins,
        "trust_floor":               trust_floor,
        "depletion_rate_per_period": depletion_rate,
        "outcome":                   outcome,
        "recommendation":            rec,
        "raw":                       raw,
    }


# ---------------------------------------------------------------------------
# Automation Transition Trajectory
# ---------------------------------------------------------------------------

def automation_transition_trajectory(
    epsilon_start: float = 0.10,
    epsilon_delta: float = 0.05,
    n_periods: int = 15,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
) -> dict:
    """
    Simulate a fixed-rate automation transition and track key economic indicators.

    At each period, ε advances by epsilon_delta. Returns a per-period trajectory
    tracking purchasing power, labor income, and trust solvency — the three key
    signals of a healthy automation transition (Principle 5).

    Also computes convergence_period: the first period where trust surplus
    stabilises within 5% of the previous period.

    Args:
        epsilon_start: Starting automation level.
        epsilon_delta: Automation advance per period.
        n_periods:     Number of periods.
        population:    Initial population.
        trust_balance: Initial Trust balance (TEH).
        capital_stock_teh: Initial capital stock.

    Returns:
        dict: {
          "scenario":             str,
          "epsilon_start":        float,
          "epsilon_delta":        float,
          "n_periods":            int,
          "trajectory":           list[dict],   per-period metrics
          "convergence_period":   int | None,
          "raw":                  dict,
        }
    """
    initial_state = make_economy_state(
        epsilon=epsilon_start,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
    )

    raw = run_simulation(
        initial_state,
        n_periods=n_periods,
        epsilon_delta=epsilon_delta,
    )

    trajectory = []
    convergence_period = None
    prev_surplus = None

    for result in raw["period_results"]:
        eps = result["epsilon"]
        floor_teh = result["fiscal"]["guarantee"]["total_cost_teh"]
        pp = floor_purchasing_power(floor_teh, eps, floor_teh)
        surplus = result["fiscal"]["trust"]["surplus_deficit"]

        trajectory.append({
            "period":              result["period"],
            "epsilon":             eps,
            "teh_in_circulation":  result["teh_in_circulation"],
            "floor_pp_index":      pp["pp_index"],
            "labor_income":        result["labor_income"],
            "trust_surplus_deficit": surplus,
            "solvent":             result["solvent"],
            "basket_price":        basket_price(eps),
        })

        if (prev_surplus is not None and abs(prev_surplus) > 1e-6
                and abs(surplus - prev_surplus) / abs(prev_surplus) < 0.05
                and convergence_period is None):
            convergence_period = result["period"]

        prev_surplus = surplus

    return {
        "scenario":           "automation_transition_trajectory",
        "epsilon_start":      epsilon_start,
        "epsilon_delta":      epsilon_delta,
        "n_periods":          n_periods,
        "trajectory":         trajectory,
        "convergence_period": convergence_period,
        "raw":                raw,
    }
