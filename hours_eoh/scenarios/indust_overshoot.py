"""
scenarios/indust_overshoot — Industrial overshoot archetype scenario.

Uses indust_no_eco_params to construct the industrial-overshoot physical state:
  - 10× canonical capital stock per capita
  - Capital age ratio 0.75 (aging industrial fleet)
  - Ecosystem health 0.38 (below spike threshold)
  - 100 B-hour deferred ecological backlog
  - Capital provides zero EOH offset (consumes, never reduces obligations)

Two scenarios:

  indust_overshoot_baseline    — Single-period EOH/fiscal snapshot vs. canonical
  indust_recovery_trajectory   — Multi-period run: can restoration pull the
                                  economy out of the overshoot regime?

Mission Statement: §"Industrial overshoot — dense capital stock, maximum
maintenance burden, zero ecological credit, threshold-failure regime active."
"""

from __future__ import annotations

from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    TRUST_BASE_TEH,
)
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.core.simulation import make_economy_state, run_simulation
from hours_eoh.core.trajectory import canonical_physical_state as _canonical_state
from hours_eoh.indust_no_eco_params import (
    make_indust_no_eco_params,
    INDUST_NO_ECO_PIPELINE_KWARGS,
    INDUST_CAPITAL_AGE_RATIO,
    INDUST_ECOSYSTEM_HEALTH,
    INDUST_DEFERRED_ECOLOGICAL,
)


# ---------------------------------------------------------------------------
# Indust Overshoot Baseline
# ---------------------------------------------------------------------------

def indust_overshoot_baseline(
    population: float = 65_000_000,
    epsilon: float = 0.40,
) -> dict:
    """
    Single-period EOH/fiscal snapshot under industrial-overshoot physical state.

    Builds scenario parameters via make_indust_no_eco_params() and runs
    eoh_to_teh_pipeline() + fiscal_snapshot(). Compares the result against
    the canonical baseline at the same ε to quantify the overshoot burden.

    Args:
        population: Civilization population. Default: 65 M.
        epsilon:    Automation level [0.0, 0.99]. Default: 0.40.

    Returns:
        dict: {
          "scenario":              str,
          "population":            float,
          "epsilon":               float,
          "eoh_by_domain":         dict,    (indust scenario)
          "teh_created":           float,
          "fiscal":                dict,    (fiscal_snapshot result)
          "canonical_total_eoh":   float,   (baseline at same ε)
          "eoh_vs_canonical_ratio": float,  (indust / canonical)
          "outcome":               str,     MANAGEABLE / STRESSED / CRITICAL
          "recommendation":        str,
        }
    """
    p = make_indust_no_eco_params(population=population, epsilon=epsilon)

    pipeline = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=population,
        capital_stock=p["capital_stock_teh"],
        capital_age_ratio=p["capital_age_ratio"],
        ecosystem_health=p["ecosystem_health"],
        deferred_ecological=p["deferred_ecological"],
        **INDUST_NO_ECO_PIPELINE_KWARGS,
    )

    labor_income = max(pipeline["teh_created"], 1.0)
    fiscal = fiscal_snapshot(
        trust_balance=TRUST_BASE_TEH * (population / 1_000_000),
        labor_income=labor_income,
        capital_stock_teh=p["capital_stock_teh"],
        capital_age_ratio=p["capital_age_ratio"],
        population=population,
        epsilon=epsilon,
        ecosystem_health=p["ecosystem_health"],
        deferred_ecological=p["deferred_ecological"],
    )

    # Canonical baseline for comparison
    canon_state = _canonical_state(epsilon)
    from hours_eoh.core.eoh_generation import total_eoh as _total_eoh
    canon_eoh = _total_eoh(
        epsilon=epsilon,
        population=population,
        age_distribution=canon_state["age_distribution"],
        capital_stock=CAPITAL_STOCK_DEFAULT * (population / 1_000_000),
        capital_age_ratio=canon_state["capital_age_ratio"],
        ecosystem_health=canon_state["ecosystem_health"],
        monitoring_capability=canon_state["monitoring_capability"],
    )["total"]

    indust_total = pipeline["total_eoh"]
    ratio = indust_total / max(canon_eoh, 1.0)

    if fiscal["solvent"] and ratio < 2.0:
        outcome = "MANAGEABLE"
    elif fiscal["solvent"] or ratio < 3.0:
        outcome = "STRESSED"
    else:
        outcome = "CRITICAL"

    rec = (
        f"Industrial overshoot at ε={epsilon:.2f} ({population/1e6:.0f}M pop): "
        f"EOH is {ratio:.1f}× canonical. "
        f"Infrastructure EOH: {pipeline['eoh_by_domain'].get('infrastructure', 0):,.0f} h/yr. "
        f"Ecosystem health: {p['ecosystem_health']:.2f} (threshold regime: {'YES' if p['ecosystem_health'] < 0.40 else 'NO'}). "
        f"Fiscal: {'SOLVENT' if fiscal['solvent'] else 'INSOLVENT'}. Outcome: {outcome}."
    )

    return {
        "scenario":               "indust_overshoot_baseline",
        "population":             population,
        "epsilon":                epsilon,
        "eoh_by_domain":          pipeline["eoh_by_domain"],
        "total_eoh":              indust_total,
        "teh_created":            pipeline["teh_created"],
        "fiscal":                 fiscal,
        "canonical_total_eoh":    canon_eoh,
        "eoh_vs_canonical_ratio": ratio,
        "outcome":                outcome,
        "recommendation":         rec,
    }


# ---------------------------------------------------------------------------
# Indust Recovery Trajectory
# ---------------------------------------------------------------------------

def indust_recovery_trajectory(
    population: float = 65_000_000,
    epsilon: float = 0.40,
    ecological_restoration_rate: float = 0.02,
    n_periods: int = 30,
) -> dict:
    """
    Multi-period recovery run starting from industrial-overshoot initial state.

    Seeds make_economy_state() with indust_no_eco_params values and runs
    run_simulation() with ecological_restoration_rate and capital_investment_rate=0
    (no new capital — the industrial fleet is maintained but not expanded).

    Recovery milestones:
      - ecosystem_recovered:           ecosystem_health > 0.40 (above spike threshold)
      - fiscal_recovered:              Trust solvent every period after first half
      - years_to_ecosystem_recovery:   first period where health > 0.40 (or None)

    Args:
        population:                  Civilization population.
        epsilon:                     Automation level [0.0, 0.99].
        ecological_restoration_rate: ecosystem_health improvement per period.
                                     0.0 = no restoration effort.
        n_periods:                   Number of simulation periods.

    Returns:
        dict: {
          "scenario":                    str,
          "population":                  float,
          "epsilon":                     float,
          "ecological_restoration_rate": float,
          "n_periods":                   int,
          "ecosystem_recovered":         bool,
          "fiscal_recovered":            bool,
          "years_to_ecosystem_recovery": int | None,
          "trajectory":                  list[dict],  per-period summary
          "raw":                         dict,
        }
    """
    p = make_indust_no_eco_params(population=population, epsilon=epsilon)
    scaled_trust = TRUST_BASE_TEH * (population / 1_000_000)

    initial_state = make_economy_state(
        epsilon=epsilon,
        population=population,
        trust_balance=scaled_trust,
        capital_stock_teh=p["capital_stock_teh"],
        capital_age_ratio=INDUST_CAPITAL_AGE_RATIO,
        ecosystem_health=INDUST_ECOSYSTEM_HEALTH,
        deferred_ecological=INDUST_DEFERRED_ECOLOGICAL,
    )

    raw = run_simulation(
        initial_state,
        n_periods=n_periods,
        ecological_restoration_rate=ecological_restoration_rate,
        capital_investment_rate=0.0,
    )

    trajectory = []
    ecosystem_recovered = False
    years_to_recovery = None

    for result in raw["period_results"]:
        eco = result["ecosystem_health"]
        if eco > 0.40 and not ecosystem_recovered:
            ecosystem_recovered = True
            years_to_recovery = result["period"] + 1  # 1-indexed

        trajectory.append({
            "period":            result["period"],
            "ecosystem_health":  eco,
            "deferred_ecological": result.get("deferred_ecological", 0.0),
            "trust_end":         result["trust_end"],
            "solvent":           result["solvent"],
            "teh_created":       result["teh_created"],
        })

    # fiscal_recovered: solvent in every period after the midpoint
    mid = n_periods // 2
    fiscal_recovered = all(
        r["solvent"] for r in raw["period_results"][mid:]
    ) if raw["period_results"] else False

    return {
        "scenario":                    "indust_recovery_trajectory",
        "population":                  population,
        "epsilon":                     epsilon,
        "ecological_restoration_rate": ecological_restoration_rate,
        "n_periods":                   n_periods,
        "ecosystem_recovered":         ecosystem_recovered,
        "fiscal_recovered":            fiscal_recovered,
        "years_to_ecosystem_recovery": years_to_recovery,
        "trajectory":                  trajectory,
        "raw":                         raw,
    }
