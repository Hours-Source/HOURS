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

from typing import Any

from hours_eoh.data import (
    REFERENCE_FRAME_POPULATION,
    COMPOUNDING_CRIT,
    COMPOUNDING_WARN,
    MEAN_MULTIPLIER_REFERENCE,
)
from hours_eoh.core.eoh_dynamics import eoh_compounding
from hours_eoh.core.registration import register_shares



def deferred_maintenance_crisis(
    epsilon: float,
    annual_eoh: float,
    fulfillment_fraction: float,
    years: int,
    asset_type: str = "generic_infra",
    population: float | None = None,
    capital_stock_teh: float | None = None,
    degraded_compounding: float = COMPOUNDING_WARN,
    capital_age_ratio: float | None = None,
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
        capital_age_ratio: The frame's stock age (2026-10-04): the starting
            condition (`civilization.condition_from_age_ratio`, reported per
            row as `condition`), the upkeep intensity the rebuild crossover
            reads, and the overbuild reading. None → a new stock, and each
            function's own default age.

    IRREVERSIBILITY IS ONE DERIVED CLOCK (2026-10-04, author). Two hand-set
    thresholds named the same crossover — rebuilding cheaper than catching up —
    and disagreed at every fulfilment: a backlog of 5× a year's demand (it fired
    first, always) and a condition of 0.20. `failure_boundary` is now the first
    year the condition, as a share of the maintained path, falls below
    `capital.rebuild_crossover_ratio` — catching up at the most surplus a year
    can absorb costs more labour than the rebuild (`execute_writedown`'s
    `rebuild_eoh_needed`, over the annual upkeep: the frame's K when it is
    given, else the asset type's upkeep rate at the stock's age). An older,
    more upkeep-intensive stock crosses sooner. Restoration recovers neglect
    damage only — the maintained path is the ceiling — so the starting
    condition is reported, not compared.
        degraded_compounding: The compounding ratio read as DEGRADED
            (default COMPOUNDING_WARN, the dashboard's YELLOW — one value since
            2026-10-03). See its data.py note: below the threshold age the
            ratio stays under ~0.10, so any value in [0.10, 0.50] fires only
            with CRISIS.
        population, capital_stock_teh: The frame (2026-10-03). Given both,
            each year is ALSO read against the overbuild floor
            (`core.autarky.overbuild_check`): the year's compounding joins the
            apparatus's upkeep I(K) and abates nothing — the pipeline books it
            the same way (`infrastructure_compounding_eoh`) — so a backlog can
            turn an apparatus that pays into one that costs its members more
            than autarky. AND THE NEGLECTED STOCK ABATES LESS: its condition
            falls under under-maintenance (`capital.asset_condition`) and
            machine work is TEH × condition (`civilization.machine_eoh_from_capital`),
            so the abating stock is K × `capacity` (the condition ratio) — this fulfilment's
            condition over full fulfilment's, so natural wear cancels and only
            the deferral moves it. Cost side and benefit side are two terms of
            one neglect, not one mechanism counted twice (mode 11). Upkeep
            stays on the full stock. A COMPOSITION OF TWO REPO MECHANISMS
            (2026-10-03), CONFIRMED by the author 2026-10-04 with the
            capacity/efficiency breakdown below. Per year:
            `capacity`, `overbuild_margin` (B₀ − total, h/yr) and
            `overbuild_verdict`; overall `overbuild_year`, the first year it
            reads overbuilt. CAPACITY ALSO READS THE MACHINE SHARE (2026-10-03, author:
            capacity vs efficiency): the overbuild LABOUR test runs at
            ε × capacity — a worn stock does less of the work, as a
            disaster's does in `capital_loss_shock`. Upkeep not performed is
            the EFFICIENCY side (`fulfillment_fraction`); sustained, it
            becomes lost capacity, which only maintenance or a rebuild
            restores. Overbuilt on the obligation test with the labour
            test still passing (at the stated ε) is DEGRADED;
            failing both is CRISIS. Omitted → no overbuild reading and the
            result is unchanged.

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
          "failure_boundary":       int | None,   (year of irreversibility — the derived crossover)
          "rebuild_years":          float,        (rebuild labour over annual upkeep)
          "rebuild_crossover":      float,        (`rebuild_crossover_ratio`)
          "recommendation":         str,
          on a frame, also: "overbuild_margin_before", "overbuild_margin_after",
          "overbuild_year", "overbuild_outcome", and per row
          "capacity", "overbuild_margin", "overbuild_verdict"
        }
    """
    CRIT_RATIO = COMPOUNDING_CRIT
    if not 0.0 < degraded_compounding <= CRIT_RATIO:
        raise ValueError(f"degraded_compounding must be in (0, COMPOUNDING_CRIT], "
                         f"got {degraded_compounding}")
    if (population is None) != (capital_stock_teh is None):
        raise ValueError("population and capital_stock_teh are the frame: give both or neither")
    framed = population is not None
    from hours_eoh.core.capital import (
        asset_condition_trajectory, execute_writedown, rebuild_crossover_ratio,
        writedown_trigger,
    )
    from hours_eoh.core.civilization import condition_from_age_ratio
    from hours_eoh.core.eoh_generation import infrastructure_eoh
    from hours_eoh.data import ASSET_TYPES
    age_kw: dict[str, Any] = ({} if capital_age_ratio is None
                              else {"capital_age_ratio": capital_age_ratio})
    # The starting condition (2026-10-04): reported per row; no age → new.
    c0 = 1.0 if capital_age_ratio is None else condition_from_age_ratio(capital_age_ratio)
    cond = asset_condition_trajectory(1.0, annual_eoh, fulfillment_fraction, years)
    full = asset_condition_trajectory(1.0, annual_eoh, 1.0, years)
    # REBUILD COST IN YEARS OF UPKEEP: the frame's own stock when given, else
    # the asset type's upkeep rate at the stock's age (one unit of capital).
    if framed and annual_eoh > 0.0:
        rebuild_years = float(execute_writedown({
            "asset_id": "stock", "asset_type": asset_type,
            "teh_value": float(capital_stock_teh), "annual_eoh": annual_eoh,  # type: ignore[arg-type]
        })["rebuild_eoh_needed"]) / annual_eoh
    else:
        rebuild_years = 1.0 / infrastructure_eoh(
            1.0, base_maint_rate=ASSET_TYPES[asset_type]["maint_rate"], **age_kw)
    crossover = rebuild_crossover_ratio(rebuild_years)
    if framed:
        from hours_eoh.core.autarky import overbuild_check
    overbuild_year: int | None = None
    worst_overbuild = None
    k_frame = float(capital_stock_teh or 0.0)
    pop_frame = float(population or REFERENCE_FRAME_POPULATION)
    # Passed only when stated, so overbuild_check keeps its own default.
    ob_state: dict[str, Any] = ({} if capital_age_ratio is None
                                else {"capital_age_ratio": capital_age_ratio})
    margin_before = (overbuild_check(k_frame, pop_frame, epsilon=epsilon, **ob_state)
                     ["net_vs_autarky"] if framed else None)

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
        ratio = cond[year - 1]["condition"] / full[year - 1]["condition"]
        if writedown_trigger(ratio, crossover) and failure_year is None:
            failure_year = year

        row: dict[str, Any] = {
            "year":               year,
            "annual_eoh":         annual_eoh,
            "fulfilled":          fulfilled,
            "new_deferred":       new_deferred,
            "cumulative_deferred": deferred,
            "compounding":        compounding,
            "compounding_ratio":  compounding_ratio,
            "total_obligation":   total_obligation,
        }
        if framed:
            ob = overbuild_check(k_frame, pop_frame, epsilon=epsilon * ratio,
                                 added_upkeep_eoh=compounding,
                                 abating_capital_teh=k_frame * ratio, **ob_state)
            row["capacity"] = ratio
            row["condition"] = c0 * ratio
            row["overbuild_margin"] = ob["net_vs_autarky"]
            row["overbuild_verdict"] = ob["verdict"]
            if ob["verdict"] == "overbuilt":
                if overbuild_year is None:
                    overbuild_year = year
                if worst_overbuild is None or not ob["labour_test"]:
                    worst_overbuild = ob
        trajectory.append(row)

    final       = trajectory[-1]
    final_ratio = final["compounding_ratio"]

    # TWO DEFECTS FIXED 2026-08-28, both found by asking why
    # `_IRREVERSIBILITY_MULTIPLE` (the 5× backlog multiple, retired 2026-10-04
    # for the derived crossover) was unpinned.
    #
    # (1) `failure_boundary` is documented as "year of irreversibility" and
    #     RETURNED `crisis_year` — which is already returned under its own key,
    #     so the field duplicated one value while the quantity it names was
    #     computed and discarded. `failure_year` reached the caller only inside
    #     a prose recommendation string.
    #
    # (2) `outcome` was derived from the compounding ratio ALONE, so an asset
    #     past irreversibility read STABLE. At 20 years of zero maintenance the
    #     function returned outcome=STABLE beside a recommendation reading
    #     "Deferred maintenance exceeds 5× annual EOH at year 5. Rebuilding
    #     required." The machine-readable field said the opposite of the
    #     human-readable one, and a caller consuming `outcome` got STABLE for a
    #     collapsed asset.
    #
    # Neither defect failed any test, because nothing asserted a value of
    # either field against a neglected asset.
    if final_ratio >= CRIT_RATIO:
        outcome = "CRISIS"
    elif final_ratio >= degraded_compounding or failure_year is not None:
        outcome = "DEGRADED"
    else:
        outcome = "STABLE"
    overbuild_outcome = None
    if framed:
        overbuild_outcome = ("STABLE" if worst_overbuild is None
                             else "DEGRADED" if worst_overbuild["labour_test"] else "CRISIS")
        severity = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
        outcome = max(outcome, overbuild_outcome, key=severity.__getitem__)

    if crisis_year:
        rec = (
            f"Compounding crisis reached at year {crisis_year} "
            f"({final_ratio:.1%} compounding ratio). "
            f"Intervention required before year {crisis_year}."
        )
    elif failure_year:
        rec = (
            f"From year {failure_year} catching up the neglect costs more labour than "
            f"rebuilding (condition below {crossover:.0%} of the maintained path, the "
            f"derived crossover). "
            f"Rebuilding required. Preventive maintenance cannot restore function."
        )
    else:
        rec = (
            f"Managed deferred maintenance at {fulfillment_fraction:.0%} fulfillment. "
            f"Compounding ratio {final_ratio:.1%} after {years} years — below crisis threshold."
        )

    if framed:
        last = trajectory[-1]
        rec += (f" Overbuild floor: margin {margin_before:,.0f} → "
                f"{last['overbuild_margin']:,.0f} h/yr over {years} years"
                + (f"; the apparatus reads OVERBUILT from year {overbuild_year} — upkeep "
                   "plus compounding exceeds what it saves"
                   + ("; with the worn machines doing less, the labour test fails too"
                      if overbuild_outcome == "CRISIS"
                      else "; the labour test still passes at the worn stock's ε")
                   if overbuild_year else "; the apparatus still pays")
                + f" (capacity {last['capacity']:.1%} of maintained"

                + f"). Outcome: {outcome}.")
    out = {
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
        "failure_boundary":       failure_year,
        "rebuild_years":          rebuild_years,
        "rebuild_crossover":      crossover,
        "recommendation":         rec,
    }
    if framed:
        out.update(overbuild_margin_before=margin_before,
                   overbuild_margin_after=trajectory[-1]["overbuild_margin"],
                   overbuild_year=overbuild_year, overbuild_outcome=overbuild_outcome,
                   capacity_after=trajectory[-1]["capacity"])
    return out


def care_registration_delay(
    epsilon: float,
    delay_epsilon: float = 0.10,
    population: float = REFERENCE_FRAME_POPULATION,
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

    # The delay IS a register held behind the capability (2026-10-01): the
    # register read at its own, lagging ε against the one that tracks.
    expected_care = register_shares(epsilon)["care"]
    actual_care   = register_shares(epsilon, registration_epsilon=delayed_eps)["care"]

    lag_fraction = 1.0 - (actual_care / max(expected_care, 1e-10))

    teh_per_worker_expected = mean_multiplier * expected_care
    teh_per_worker_actual   = mean_multiplier * actual_care
    teh_deficit             = teh_per_worker_expected - teh_per_worker_actual

    # Central difference, clamped to the arc (2026-10-01): at ε=0 this read the
    # register at ε = −0.01, outside every curve's domain — tolerated by the
    # care curve alone, and exposed when the read moved to `register_shares`.
    _lo, _hi = max(0.0, epsilon - 0.01), min(1.0, epsilon + 0.01)
    care_slope_at_eps = (register_shares(_hi)["care"]
                         - register_shares(_lo)["care"]) / (_hi - _lo)
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
