"""
scenarios/maintenance — Slow-onset maintenance and care registration scenarios.

Two scenarios that model gradual system degradation when obligations go unmet:

  deferred_maintenance_crisis  — Sustained underinvestment compounds into crisis
  care_registration_delay      — Care admission lags behind ε progression

Both return year-by-year trajectories showing when compounding tips from
manageable to critical ("the slow crisis that looks stable until it isn't").

Mission Statement: §"EOH compounding — threshold spike becomes unrecoverable
if deferred too long"; §"Care registration delay — human capital pipeline
degrades if care admission lags collective demand"
"""

from __future__ import annotations

from hours_eoh.data import (
    COMPOUNDING_CRIT,
    MEAN_MULTIPLIER_REFERENCE,
)
from hours_eoh.core.eoh_dynamics import eoh_compounding
from hours_eoh.core.registration import care_registration_share

_IRREVERSIBILITY_MULTIPLE: float = 5.0  # deferred/annual ratio → rebuilding required


def deferred_maintenance_crisis(
    epsilon: float,
    annual_eoh: float,
    fulfillment_fraction: float,
    years: int,
    asset_type: str = "generic_infra",
) -> dict:
    """
    Simulate sustained underinvestment in infrastructure EOH over multiple years.

    Each year, a fraction of required EOH is unfulfilled. Deferred EOH
    accumulates and begins compounding once it crosses the asset threshold.
    Models "the slow crisis": things look maintainable for years, then
    nonlinear compounding makes the backlog unrecoverable.

    Args:
        epsilon: Automation level (affects compounding softener).
        annual_eoh: Annual EOH demand for the asset/infrastructure.
        fulfillment_fraction: Fraction actually fulfilled each year, ∈ [0,1].
        years: Number of years to simulate.
        asset_type: Asset type controlling compounding profile.

    Returns:
        dict: {
          "scenario":               str,
          "epsilon":                float,
          "annual_eoh":             float,
          "fulfillment_fraction":   float,
          "years":                  int,
          "trajectory":             list[dict],  (year-by-year state)
          "crisis_year":            int | None,   (first year compounding ratio > COMPOUNDING_CRIT)
          "final_deferred":         float,
          "final_compounding_ratio": float,
          "outcome":                str,
          "failure_boundary":       int | None,   (year of irreversibility)
          "recommendation":         str,
        }
    """
    CRIT_RATIO = COMPOUNDING_CRIT

    trajectory   = []
    deferred     = 0.0
    crisis_year  = None
    failure_year = None

    for year in range(1, years + 1):
        fulfilled    = annual_eoh * fulfillment_fraction
        new_deferred = max(0.0, annual_eoh - fulfilled)
        deferred    += new_deferred

        if deferred > 0:
            compounding       = eoh_compounding(deferred, asset_type, float(year), epsilon)
            compounding_ratio = compounding / max(deferred, 1.0)
        else:
            compounding       = 0.0
            compounding_ratio = 0.0

        total_obligation = deferred + compounding

        if compounding_ratio >= CRIT_RATIO and crisis_year is None:
            crisis_year = year
        if total_obligation > annual_eoh * _IRREVERSIBILITY_MULTIPLE and failure_year is None:
            failure_year = year

        trajectory.append({
            "year":               year,
            "annual_eoh":         annual_eoh,
            "fulfilled":          fulfilled,
            "new_deferred":       new_deferred,
            "cumulative_deferred": deferred,
            "compounding":        compounding,
            "compounding_ratio":  compounding_ratio,
            "total_obligation":   total_obligation,
        })

    final       = trajectory[-1]
    final_ratio = final["compounding_ratio"]

    if final_ratio < 0.10:
        outcome = "STABLE"
    elif final_ratio < CRIT_RATIO:
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    if crisis_year:
        rec = (
            f"Compounding crisis reached at year {crisis_year} "
            f"({final_ratio:.1%} compounding ratio). "
            f"Intervention required before year {crisis_year}."
        )
    elif failure_year:
        rec = (
            f"Deferred maintenance exceeds {_IRREVERSIBILITY_MULTIPLE:.0f}× annual EOH at year {failure_year}. "
            f"Rebuilding required. Preventive maintenance cannot restore function."
        )
    else:
        rec = (
            f"Managed deferred maintenance at {fulfillment_fraction:.0%} fulfillment. "
            f"Compounding ratio {final_ratio:.1%} after {years} years — below crisis threshold."
        )

    return {
        "scenario":               "deferred_maintenance_crisis",
        "epsilon":                epsilon,
        "annual_eoh":             annual_eoh,
        "fulfillment_fraction":   fulfillment_fraction,
        "years":                  years,
        "trajectory":             trajectory,
        "crisis_year":            crisis_year,
        "final_deferred":         final["cumulative_deferred"],
        "final_compounding_ratio": final_ratio,
        "outcome":                outcome,
        "failure_boundary":       crisis_year,
        "recommendation":         rec,
    }


def care_registration_delay(
    epsilon: float,
    delay_epsilon: float = 0.10,
    population: float = 1_000_000.0,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
) -> dict:
    """
    Simulate care admission lagging behind ε progression.

    If the collective fails to formalize care work (institutional lag, policy
    failure), the actual care share is behind schedule. The impact: fewer TEH
    created from care labor, and the human capital pipeline builds capacity
    more slowly.

    Args:
        epsilon: Actual automation level.
        delay_epsilon: How many ε-units care admission is lagging.
                       E.g., delay=0.10 means care admission behaves as if
                       ε = actual_ε − delay_epsilon.
        population: Total population.
        mean_multiplier: Multiplier for TEH creation.

    Returns:
        dict: {
          "scenario":                       str,
          "epsilon":                        float,
          "delay_epsilon":                  float,
          "actual_care_share":              float,
          "expected_care_share":            float,
          "lag_fraction":                   float,   (1 - actual/expected)
          "care_teh_per_worker_actual":     float,
          "care_teh_per_worker_expected":   float,
          "teh_deficit_per_worker":         float,
          "pipeline_degradation":           float,
          "outcome":                        str,
          "recommendation":                 str,
        }
    """
    delayed_eps = max(0.0, epsilon - delay_epsilon)

    expected_care = care_registration_share(epsilon)
    actual_care   = care_registration_share(delayed_eps)

    lag_fraction = 1.0 - (actual_care / max(expected_care, 1e-10))

    teh_per_worker_expected = mean_multiplier * expected_care
    teh_per_worker_actual   = mean_multiplier * actual_care
    teh_deficit             = teh_per_worker_expected - teh_per_worker_actual

    care_slope_at_eps = (care_registration_share(epsilon + 0.01)
                         - care_registration_share(epsilon - 0.01)) / 0.02
    pipeline_degradation = lag_fraction * care_slope_at_eps * delay_epsilon

    if lag_fraction < 0.10:
        outcome = "STABLE"
    elif lag_fraction < 0.30:
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    rec = (
        f"Care admission at ε={epsilon:.2f} is lagging by {delay_epsilon:.2f} ε-units. "
        f"Actual share: {actual_care:.3f} vs expected: {expected_care:.3f} "
        f"({lag_fraction:.1%} lag). "
        f"Pipeline degradation: {pipeline_degradation:.3f}. "
        f"Accelerate care formalization to close the gap before ε={epsilon + 0.10:.2f}."
    )

    return {
        "scenario":                     "care_registration_delay",
        "epsilon":                      epsilon,
        "delay_epsilon":                delay_epsilon,
        "actual_care_share":            actual_care,
        "expected_care_share":          expected_care,
        "lag_fraction":                 lag_fraction,
        "care_teh_per_worker_actual":   teh_per_worker_actual,
        "care_teh_per_worker_expected": teh_per_worker_expected,
        "teh_deficit_per_worker":       teh_deficit,
        "pipeline_degradation":         pipeline_degradation,
        "outcome":                      outcome,
        "recommendation":               rec,
    }
