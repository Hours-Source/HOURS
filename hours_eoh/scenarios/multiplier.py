"""
scenarios/multiplier — Multiplier band drift scenarios.

Three scenarios that model mean multiplier (M) moving outside the [1.8, 2.1]
band and probe whether the fiscal system can absorb the drift before governance
corrects it:

  m_below_band_drift   M falls through the 1.8 floor (automation displaces
                       base-tier jobs; governance cycle lags behind)
  m_above_band_drift   M rises above the 2.1 ceiling (credential inflation;
                       reclassification drift without anti-gaming enforcement)
  m_band_sweep         Static M sensitivity sweep — lowest M for solvency,
                       highest M before instability

These build on the `mean_multiplier_schedule` parameter added to
run_simulation(), which lets M vary per period without changing the
simulate_period() interface.

Mission Statement: §"Condition II — Multiplier Band"; §"Anti-gaming
safeguards"; §"The population-weighted average must remain within [1.8, 2.1]."
"""

from __future__ import annotations
from typing import Any

from hours_eoh.data import (
    M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET, M_MAX,
    TIER_ASSESSMENT_INTERVAL_YEARS,
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
)
from hours_eoh.core.multipliers import multiplier_band_check
from hours_eoh.core.simulation import make_economy_state, run_simulation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_drift_schedule(
    n_periods: int,
    m_start: float,
    m_drift_rate: float,
    band_limit: float,
    breach_above: bool,          # True = breach when m_t > band_limit; False = when < band_limit
    governance_lag: int,
    correction_magnitude: float | None,
) -> tuple[list[float], int | None, int | None]:
    """
    Build a per-period M schedule with optional governance correction.

    Returns (schedule, breach_period, correction_period).
    breach_period and correction_period are None if no breach occurs.

    When correction_magnitude is not None, the correction advances incrementally
    from the M value at correction onset — not from the continuing drift baseline.
    This ensures the governance response is anchored to the actual state when the
    council acts, not to an extrapolated drift position.
    """
    schedule: list[float] = []
    breach_period: int | None = None
    correction_period: int | None = None
    m_onset: float | None = None   # M value frozen at first correction period

    for t in range(n_periods):
        raw_m = m_start + t * m_drift_rate

        if correction_period is not None and t >= correction_period:
            if t == correction_period:
                m_onset = raw_m   # freeze drift value at correction onset
            if correction_magnitude is None:
                raw_m = M_BAND_TARGET
            else:
                assert m_onset is not None
                gap = M_BAND_TARGET - m_onset
                sign = 1.0 if gap >= 0.0 else -1.0
                move = sign * min(abs(gap), correction_magnitude * (t - correction_period))
                raw_m = m_onset + move

        m_t = min(max(raw_m, 1.0), M_MAX)
        schedule.append(m_t)

        if breach_period is None:
            if (breach_above and m_t > band_limit) or (not breach_above and m_t < band_limit):
                breach_period = t
                correction_period = t + governance_lag

    return schedule, breach_period, correction_period


def _outcome_from_run(
    raw: dict,
    breach_period: int | None,
    governance_lag: int,
    m_trajectory: list[float],
    band_low: float = M_BAND_LOW,
    band_high: float = M_BAND_HIGH,
) -> str:
    """Classify outcome as STABLE / DEGRADED / CRISIS."""
    if not raw["solvent_all"]:
        return "CRISIS"
    if breach_period is None:
        return "STABLE"
    periods_out = sum(
        1 for m in m_trajectory
        if m < band_low or m > band_high
    )
    if periods_out >= governance_lag:
        return "DEGRADED"
    return "STABLE"


def _fiscal_impact(raw: dict, baseline_teh: float) -> dict:
    trust_values = [r["trust_end"] for r in raw["period_results"]]
    return {
        "teh_creation_delta": raw["final_state"]["teh_created_cumulative"] - baseline_teh,
        "min_trust_balance":  min(trust_values),
        "solvent_throughout": raw["solvent_all"],
    }


_BELOW_BAND_RECOMMENDATIONS: dict[str, str] = {
    "CRISIS": (
        "Trust insolvency during drift period. Governance lag exceeds the "
        "system's fiscal resilience. Reduce governance_lag or strengthen "
        "the Trust accumulation target."
    ),
    "DEGRADED": (
        "M was below band for {periods_out} periods before correction. "
        "Trust balance dipped but recovered. Consider a faster governance "
        "response cycle or a pre-emptive M floor trigger."
    ),
    "STABLE": "System absorbed the drift within the governance correction window.",
}

_ABOVE_BAND_RECOMMENDATIONS: dict[str, str] = {
    "CRISIS": (
        "Trust insolvency despite above-band M. Investigate whether the "
        "guarantee cost escalation from high-M TEH pricing is outpacing levy revenue."
    ),
    "DEGRADED": (
        "M was above band for {periods_out} periods. Trust remained solvent "
        "but purchasing-power equity was compromised during the drift window. "
        "Enforce anti-gaming safeguards to prevent reclassification drift."
    ),
    "STABLE": (
        "Above-band drift was brief and corrected within the governance window. "
        "Trust solvency was not threatened."
    ),
}


def _run_drift_scenario(
    band_limit: float,
    breach_above: bool,
    status_label: str,
    recommendations: dict[str, str],
    epsilon: float,
    n_periods: int,
    m_start: float,
    m_drift_rate: float,
    governance_lag: int,
    correction_magnitude: float | None,
    population: float,
    trust_balance: float,
    capital_stock_teh: float,
    **sim_kwargs: Any,
) -> dict:
    schedule, breach_period, correction_period = _build_drift_schedule(
        n_periods=n_periods,
        m_start=m_start,
        m_drift_rate=m_drift_rate,
        band_limit=band_limit,
        breach_above=breach_above,
        governance_lag=governance_lag,
        correction_magnitude=correction_magnitude,
    )

    state = make_economy_state(
        epsilon=epsilon,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
    )

    baseline = run_simulation(
        make_economy_state(epsilon=epsilon, population=population,
                           trust_balance=trust_balance, capital_stock_teh=capital_stock_teh),
        n_periods=n_periods,
        mean_multiplier=m_start,
        **sim_kwargs,
    )
    baseline_teh = baseline["final_state"]["teh_created_cumulative"]

    raw = run_simulation(
        state,
        n_periods=n_periods,
        mean_multiplier_schedule=schedule,
        **sim_kwargs,
    )

    m_traj = raw["summary"]["mean_multiplier_trajectory"]
    band_status = [multiplier_band_check(m)["status"] for m in m_traj]
    periods_out = sum(1 for s in band_status if s == status_label)
    outcome = _outcome_from_run(raw, breach_period, governance_lag, m_traj)

    rec_template = recommendations.get(outcome, "")
    rec = rec_template.format(periods_out=periods_out)

    return {
        "outcome":             outcome,
        "breach_period":       breach_period,
        "correction_period":   correction_period,
        "periods_out_of_band": periods_out,
        "m_trajectory":        m_traj,
        "band_status":         band_status,
        "fiscal_impact":       _fiscal_impact(raw, baseline_teh),
        "recommendation":      rec,
        "raw":                 raw,
    }


# ---------------------------------------------------------------------------
# M Below-Band Drift
# ---------------------------------------------------------------------------

def m_below_band_drift(
    epsilon: float = 0.40,
    n_periods: int = 20,
    m_start: float = 2.10,
    m_drift_rate: float = -0.05,
    governance_lag: int = TIER_ASSESSMENT_INTERVAL_YEARS,
    correction_magnitude: float | None = None,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    **sim_kwargs: Any,
) -> dict:
    """
    Model M falling through the 1.8 floor faster than governance can respond.

    Represents workforce composition shifts where automation eliminates
    base-tier jobs faster than the Standards of Contribution Council's
    assessment cycle can reclassify or introduce compensating roles.

    The schedule drifts M at m_drift_rate per period. When M first crosses
    below M_BAND_LOW, a breach is recorded and a correction is scheduled
    after governance_lag periods. Correction either snaps M fully to
    M_BAND_TARGET (correction_magnitude=None) or advances incrementally
    from the M value frozen at correction onset.

    Args:
        epsilon: Starting automation level [0.0, 0.99].
        n_periods: Simulation length in periods.
        m_start: Initial M value. Default: M_BAND_TARGET (2.10).
        m_drift_rate: M change per period (negative = falling). Default: -0.05.
        governance_lag: Periods from breach detection to correction.
                        Default: TIER_ASSESSMENT_INTERVAL_YEARS (5).
        correction_magnitude: If None, corrects fully to M_BAND_TARGET at
                        correction_period. If a float, corrects by that
                        amount per period from the onset value.
        population: Initial population.
        trust_balance: Initial Trust balance (TEH).
        capital_stock_teh: Initial capital stock (TEH).
        **sim_kwargs: Forwarded to run_simulation() and simulate_period().

    Returns:
        dict with keys:
          "outcome"           str          "STABLE" | "DEGRADED" | "CRISIS"
          "breach_period"     int | None   first period M < M_BAND_LOW
          "correction_period" int | None   first period correction is applied
          "periods_out_of_band" int        total periods with M < M_BAND_LOW
          "m_trajectory"      list[float]  M used each period
          "band_status"       list[str]    multiplier_band_check status per period
          "fiscal_impact"     dict         teh_creation_delta, min_trust_balance, solvent_throughout
          "recommendation"    str
          "raw"               dict         full run_simulation() result

    Reference: Mission Statement §"Condition II — Multiplier Band"; Roadmap §2.3.
    """
    return _run_drift_scenario(
        band_limit=M_BAND_LOW,
        breach_above=False,
        status_label="BELOW_BAND",
        recommendations=_BELOW_BAND_RECOMMENDATIONS,
        epsilon=epsilon,
        n_periods=n_periods,
        m_start=m_start,
        m_drift_rate=m_drift_rate,
        governance_lag=governance_lag,
        correction_magnitude=correction_magnitude,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
        **sim_kwargs,
    )


# ---------------------------------------------------------------------------
# M Above-Band Drift
# ---------------------------------------------------------------------------

def m_above_band_drift(
    epsilon: float = 0.40,
    n_periods: int = 20,
    m_start: float = 2.10,
    m_drift_rate: float = 0.04,
    governance_lag: int = TIER_ASSESSMENT_INTERVAL_YEARS,
    correction_magnitude: float | None = None,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    **sim_kwargs: Any,
) -> dict:
    """
    Model M rising above the 2.1 ceiling from credential inflation.

    Represents systematic tier reclassification without anti-gaming enforcement:
    Skilled roles drift into Advanced, Advanced into Elite, without corresponding
    competency evidence or scarcity justification. M rises until governance
    corrects it after governance_lag periods.

    Above-band M increases TEH creation per registered EOH-hour — the Trust
    typically gains revenue — but it distorts the purchasing-power equity
    the sufficiency guarantee is designed to maintain. The outcome classification
    reflects the combination of fiscal health and band integrity.

    Args:
        epsilon: Starting automation level [0.0, 0.99].
        n_periods: Simulation length in periods.
        m_start: Initial M value. Default: M_BAND_TARGET (2.10).
        m_drift_rate: M change per period (positive = rising). Default: +0.04.
        governance_lag: Periods from breach detection to correction.
        correction_magnitude: Correction per period from onset; None = full snap.
        population: Initial population.
        trust_balance: Initial Trust balance (TEH).
        capital_stock_teh: Initial capital stock (TEH).
        **sim_kwargs: Forwarded to run_simulation().

    Returns:
        Same structure as m_below_band_drift(), with band_status values
        of "ABOVE_BAND" rather than "BELOW_BAND" during the breach window.

    Reference: Mission Statement §"Condition II"; §"Anti-gaming safeguard 2 —
    artificial scarcity detection"; Roadmap §2.3.
    """
    return _run_drift_scenario(
        band_limit=M_BAND_HIGH,
        breach_above=True,
        status_label="ABOVE_BAND",
        recommendations=_ABOVE_BAND_RECOMMENDATIONS,
        epsilon=epsilon,
        n_periods=n_periods,
        m_start=m_start,
        m_drift_rate=m_drift_rate,
        governance_lag=governance_lag,
        correction_magnitude=correction_magnitude,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
        **sim_kwargs,
    )


# ---------------------------------------------------------------------------
# M Band Sweep
# ---------------------------------------------------------------------------

def m_band_sweep(
    epsilon: float = 0.40,
    m_values: list[float] | None = None,
    n_periods: int = 10,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    **sim_kwargs: Any,
) -> dict:
    """
    Sweep static M values and report fiscal health at each level.

    Runs one fixed-M simulation per value in m_values. Identifies the
    lowest M that keeps the Trust solvent and the highest M before the
    system becomes structurally unstable. Useful for sensitivity analysis
    and for answering "what multiplier distribution keeps M within target
    given this workforce composition?"

    Args:
        epsilon: Automation level for all runs [0.0, 0.99].
        m_values: List of M values to test. Default: 11 values from 1.5
                  to 2.5 in steps of 0.10.
        n_periods: Simulation length per run.
        population: Initial population.
        trust_balance: Initial Trust balance (TEH).
        capital_stock_teh: Initial capital stock (TEH).
        **sim_kwargs: Forwarded to run_simulation() for each run.

    Returns:
        dict with keys:
          "m_values"              list[float]  tested M values
          "outcomes"              list[str]    STABLE / DEGRADED / CRISIS per run
          "teh_created"           list[float]  cumulative TEH over n_periods per run
          "final_trust_balance"   list[float]  Trust balance at end of run
          "solvent_all"           list[bool]   solvent every period
          "band_status"           list[str]    multiplier_band_check status at each M
          "summary": {
            "m_floor_for_solvency"  float | None  lowest M keeping Trust solvent
            "m_ceiling_stable"      float | None  highest M with solvent_all=True
          }

    Reference: Mission Statement §"Condition II"; Roadmap §2.3 (inverse query).
    """
    if m_values is None:
        m_values = [round(1.5 + 0.10 * i, 2) for i in range(11)]

    outcomes:            list[str]   = []
    teh_created_list:    list[float] = []
    final_trust_list:    list[float] = []
    solvent_all_list:    list[bool]  = []
    band_status_list:    list[str]   = []

    for m in m_values:
        state = make_economy_state(
            epsilon=epsilon,
            population=population,
            trust_balance=trust_balance,
            capital_stock_teh=capital_stock_teh,
        )
        raw = run_simulation(
            state,
            n_periods=n_periods,
            mean_multiplier=m,
            **sim_kwargs,
        )

        solvent = raw["solvent_all"]
        final_trust = raw["final_state"]["trust_balance"]
        teh = raw["final_state"]["teh_created_cumulative"]
        band = multiplier_band_check(m)["status"]

        if not solvent:
            outcome = "CRISIS"
        elif band != "OK":
            outcome = "DEGRADED"
        else:
            outcome = "STABLE"

        outcomes.append(outcome)
        teh_created_list.append(teh)
        final_trust_list.append(final_trust)
        solvent_all_list.append(solvent)
        band_status_list.append(band)

    solvent_m = [m for m, s in zip(m_values, solvent_all_list) if s]
    m_floor   = min(solvent_m) if solvent_m else None
    m_ceiling = max(solvent_m) if solvent_m else None

    return {
        "m_values":            m_values,
        "outcomes":            outcomes,
        "teh_created":         teh_created_list,
        "final_trust_balance": final_trust_list,
        "solvent_all":         solvent_all_list,
        "band_status":         band_status_list,
        "summary": {
            "m_floor_for_solvency": m_floor,
            "m_ceiling_stable":     m_ceiling,
        },
    }
