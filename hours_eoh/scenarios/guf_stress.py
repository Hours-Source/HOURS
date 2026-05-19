"""
scenarios/guf_stress — Ground Use Fee fiscal integration and ecological write-down.

Four scenarios that exercise the GUF layer against the Trust and fiscal system:

  guf_fiscal_integration      — Does GUF revenue close a levy deficit? How material is it?
  guf_writedown_scenario      — Full ecological collapse → warning → write-down pathways
  guf_revenue_sweep           — How does GUF track the Ψ(ε) bell curve across the arc?
  automation_levy_guf_stress  — Multi-period: automation rises → levy falls → does GUF compensate?

Mission Statement: §"Ground Use Fee — land rents fund the ecological and
stewardship obligations co-equally with levy revenue."
"""

from __future__ import annotations

from hours_eoh.data import (
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
    DEP_RATE,
    DIV_RATE,
    SUFF_LEVY_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    GUF_EOH_ACCUMULATION_THRESHOLD,
    GUF_WRITEDOWN_AMORTIZATION_YEARS,
)
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import (
    levy_collection,
    stewardship_allocation,
    sufficiency_guarantee,
    trust_management,
)
from hours_eoh.land.guf import (
    ground_use_fee,
    guf_trust_inflow,
    ground_use_fee_writedown,
    eoh_accumulation_warning,
)
from hours_eoh.land.collective import compute_collective_guf, make_urban_collective

_DEFAULT_PARCEL = {
    "area_slu":       3.5,
    "location_value": 0.629,
    "use_category":   "residential_primary",
}

# Positional kwargs consumed by ground_use_fee(); remaining keys are passed as extras.
_GUF_POSITIONAL_KEYS = frozenset({"area_slu", "location_value", "use_category"})


# ---------------------------------------------------------------------------
# GUF Fiscal Integration
# ---------------------------------------------------------------------------

def guf_fiscal_integration(
    epsilon: float,
    parcel_configs: list[dict] | None = None,
    trust_balance: float = TRUST_BASE_TEH,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    levy_rates: dict | None = None,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    subsidies_absorbed: float = 0.0,
) -> dict:
    """
    Compare Trust solvency with and without GUF revenue at a given ε.

    Computes aggregate GUF payments for each parcel in parcel_configs via
    ground_use_fee(), aggregates via guf_trust_inflow(), then runs
    trust_management() twice — levy-only baseline vs. levy + GUF net_inflow —
    to measure how material the GUF revenue stream is.

    Args:
        epsilon:           Automation level [0.0, 0.99].
        parcel_configs:    List of dicts with ground_use_fee() kwargs. Each must
                           have at least {area_slu, location_value, use_category}.
                           None → one default residential parcel.
        trust_balance:     Trust fund balance at start of period.
        population:        Total population.
        capital_stock_teh: Capital stock (TEH).
        capital_age_ratio: Mean asset age ratio.
        levy_rates:        Override default levy rates.
        dep_rate:          Trust depreciation rate.
        div_rate:          Trust dividend fraction.
        subsidies_absorbed: Total income-linked subsidy cost absorbed by Trust.

    Returns:
        dict: {
          "scenario":                  str,
          "epsilon":                   float,
          "parcel_count":              int,
          "guf_gross_revenue":         float,
          "guf_net_inflow":            float,
          "levy_revenue":              float,
          "guf_revenue_fraction_of_levy": float,  (0 if levy = 0)
          "trust_end_levy_only":       float,
          "trust_end_with_guf":        float,
          "trust_solvent_levy_only":   bool,
          "trust_solvent_with_guf":    bool,
          "outcome":                   str,   GUF_MATERIAL / GUF_SUPPLEMENTAL / GUF_INSUFFICIENT
          "recommendation":            str,
        }
    """
    configs = [_DEFAULT_PARCEL] if parcel_configs is None else parcel_configs

    parcel_results = [
        ground_use_fee(
            area_slu=c["area_slu"],
            location_value=c["location_value"],
            use_category=c["use_category"],
            epsilon=epsilon,
            **{k: v for k, v in c.items() if k not in _GUF_POSITIONAL_KEYS},
        )
        for c in configs
    ]

    guf_revenues = [r["guf_applied"] for r in parcel_results]
    inflow = guf_trust_inflow(guf_revenues, subsidies_absorbed=subsidies_absorbed)

    labor_income = eoh_to_teh_pipeline(epsilon=epsilon, population=population)["teh_created"]
    levies = levy_collection(labor_income, levy_rates or {"sufficiency": SUFF_LEVY_RATE})
    stew   = stewardship_allocation(capital_stock_teh, capital_age_ratio,
                                    epsilon, trust_balance)
    guar   = sufficiency_guarantee(population, epsilon,
                                   meaningful_activity_teh=MEANINGFUL_ACTIVITY_TEH_BASE)

    # Baseline: levy only
    trust_base = trust_management(
        trust_balance,
        levies["total_levied"],
        stew["teh_allocated"],
        guar["total_cost_teh"],
        dep_rate, div_rate, epsilon,
    )

    # With GUF: levy + net_inflow
    trust_guf = trust_management(
        trust_balance,
        levies["total_levied"] + inflow["net_inflow"],
        stew["teh_allocated"],
        guar["total_cost_teh"],
        dep_rate, div_rate, epsilon,
    )

    guf_fraction = (inflow["net_inflow"] / max(levies["total_levied"], 1.0))

    if not trust_base["solvent"] and trust_guf["solvent"]:
        outcome = "GUF_MATERIAL"
    elif trust_base["solvent"] and trust_guf["solvent"]:
        outcome = "GUF_SUPPLEMENTAL"
    else:
        outcome = "GUF_INSUFFICIENT"

    rec = (
        f"GUF fiscal integration at ε={epsilon:.2f} ({len(configs)} parcels): "
        f"GUF net_inflow {inflow['net_inflow']:,.0f} TEH/yr "
        f"= {guf_fraction:.1%} of levy revenue. "
        f"Trust solvent levy-only: {trust_base['solvent']}; "
        f"with GUF: {trust_guf['solvent']}. Outcome: {outcome}."
    )

    return {
        "scenario":                     "guf_fiscal_integration",
        "epsilon":                      epsilon,
        "parcel_count":                 len(configs),
        "guf_gross_revenue":            inflow["gross_revenue"],
        "guf_net_inflow":               inflow["net_inflow"],
        "levy_revenue":                 levies["total_levied"],
        "guf_revenue_fraction_of_levy": guf_fraction,
        "trust_end_levy_only":          trust_base["trust_end"],
        "trust_end_with_guf":           trust_guf["trust_end"],
        "trust_solvent_levy_only":      trust_base["solvent"],
        "trust_solvent_with_guf":       trust_guf["solvent"],
        "outcome":                      outcome,
        "recommendation":               rec,
    }


# ---------------------------------------------------------------------------
# GUF Ecological Write-Down Scenario
# ---------------------------------------------------------------------------

def guf_writedown_scenario(
    epsilon: float,
    parcels_at_risk: list[dict] | None = None,
    unfulfilled_eoh: float = 400_000.0,
    total_eoh: float = 1_200_000.0,
    pathway: str = "restoration",
    amortization_years: float = GUF_WRITEDOWN_AMORTIZATION_YEARS,
) -> dict:
    """
    Simulate an ecological write-down event from warning through GUF impact.

    Steps:
      1. Check eoh_accumulation_warning() — does the zone trigger a warning?
      2. For each parcel, compute standard GUF via ground_use_fee().
      3. Compute GUF under write-down via ground_use_fee_writedown() for `pathway`.
      4. Report revenue delta and total rebuilding surcharge.

    pathway options:
      "restoration" — services_lost=None, R_b=0, E uses recovery-target baselines
      "abandonment" — services_lost provided, R_b added over amortization_years

    Args:
        epsilon:           Automation level [0.0, 0.99].
        parcels_at_risk:   List of dicts for each at-risk parcel. Each must have
                           {area_slu, location_value, use_category}. Optional keys:
                           services_reset (list[dict]) and services_lost (list[dict]).
                           None → one default parcel with a modest ecosystem service.
        unfulfilled_eoh:   Unmet ecological EOH in the zone (for warning check).
        total_eoh:         Total assessed ecological EOH for the zone.
        pathway:           "restoration" or "abandonment".
        amortization_years: Years to amortize rebuilding surcharge (abandonment only).

    Returns:
        dict: {
          "scenario":               str,
          "epsilon":                float,
          "pathway":                str,
          "warning_triggered":      bool,
          "eoh_ratio":              float,
          "guf_standard_total":     float,   (sum of guf_applied before write-down)
          "guf_writedown_total":    float,   (sum after write-down)
          "revenue_delta":          float,   (writedown − standard)
          "rebuilding_surcharge_total": float,
          "recommendation":         str,
        }
    """
    if pathway not in ("restoration", "abandonment"):
        raise ValueError(f"pathway must be 'restoration' or 'abandonment', got '{pathway}'")

    # Default parcel: simple residential with one ecosystem service
    default_parcels = [{
        "area_slu":         3.5,
        "location_value":   0.629,
        "use_category":     "residential_primary",
        "services_reset":   [{"label": "water", "volume": 0.4, "kappa_ref": 1.65,
                               "beta": 0.8, "retained": 0.3}],
        "services_lost":    [{"label": "water", "volume_lost": 0.4,
                               "kappa_ref": 1.65, "beta": 0.7}],
    }]
    configs = parcels_at_risk or default_parcels

    # 1. Warning check
    warning_result = eoh_accumulation_warning(unfulfilled_eoh, total_eoh)

    # 2. Standard GUF per parcel
    standard_gufs = [
        ground_use_fee(
            area_slu=c["area_slu"],
            location_value=c["location_value"],
            use_category=c["use_category"],
            epsilon=epsilon,
        )
        for c in configs
    ]

    # 3. Write-down GUF per parcel
    writedown_gufs = []
    total_rb = 0.0
    for c in configs:
        services_reset = c.get("services_reset", None)
        services_lost  = c.get("services_lost", None) if pathway == "abandonment" else None

        wd = ground_use_fee_writedown(
            area_slu=c["area_slu"],
            location_value=c["location_value"],
            use_category=c["use_category"],
            epsilon=epsilon,
            services_reset=services_reset,
            services_lost=services_lost,
            amortization_years=amortization_years,
        )
        writedown_gufs.append(wd)
        total_rb += wd.get("rebuilding_surcharge", 0.0)

    guf_standard_total  = sum(r["guf_applied"] for r in standard_gufs)
    guf_writedown_total = sum(r["guf_applied"] for r in writedown_gufs)
    revenue_delta       = guf_writedown_total - guf_standard_total

    rec = (
        f"Write-down scenario at ε={epsilon:.2f}, pathway={pathway}: "
        f"EOH accumulation ratio {warning_result['ratio']:.2%} "
        f"({'WARNING ACTIVE' if warning_result['warning'] else 'below threshold'}). "
        f"Standard GUF: {guf_standard_total:,.2f} TEH/yr → "
        f"Write-down GUF: {guf_writedown_total:,.2f} TEH/yr "
        f"(delta: {revenue_delta:+,.2f}). "
        f"Total rebuilding surcharge: {total_rb:,.2f} TEH/yr "
        f"({'none' if pathway == 'restoration' else f'{amortization_years:.0f}-yr amortization'})."
    )

    return {
        "scenario":               "guf_writedown_scenario",
        "epsilon":                epsilon,
        "pathway":                pathway,
        "warning_triggered":      warning_result["warning"],
        "eoh_ratio":              warning_result["ratio"],
        "guf_standard_total":     guf_standard_total,
        "guf_writedown_total":    guf_writedown_total,
        "revenue_delta":          revenue_delta,
        "rebuilding_surcharge_total": total_rb,
        "recommendation":         rec,
    }


# ---------------------------------------------------------------------------
# GUF Revenue Sweep
# ---------------------------------------------------------------------------

def guf_revenue_sweep(
    epsilon_values: list[float] | None = None,
    parcel_config: dict | None = None,
) -> list[dict]:
    """
    Compute GUF at each ε in epsilon_values for a single parcel configuration.

    Useful for verifying that GUF revenue tracks the Ψ(ε) bell curve:
    near-zero at ε=0, peaking ~ε=0.40, declining to near-zero at ε=0.99.

    Args:
        epsilon_values: List of ε points to evaluate. None → 11-point canonical arc.
        parcel_config:  Dict with at least {area_slu, location_value, use_category}.
                        None → default residential parcel.

    Returns:
        list[dict]: One dict per ε with keys:
          {epsilon, guf_applied, psi, base_fee, eco_surcharge, infra_premium}
    """
    if epsilon_values is None:
        epsilon_values = [round(i * 0.099, 3) for i in range(11)]

    config = parcel_config or _DEFAULT_PARCEL

    results = []
    for eps in epsilon_values:
        r = ground_use_fee(
            area_slu=config["area_slu"],
            location_value=config["location_value"],
            use_category=config["use_category"],
            epsilon=eps,
            **{k: v for k, v in config.items()
               if k not in ("area_slu", "location_value", "use_category")},
        )
        results.append({
            "epsilon":      eps,
            "guf_applied":  r["guf_applied"],
            "psi":          r["psi"],
            "base_fee":     r["base_fee"],
            "eco_surcharge": r["eco_surcharge"],
            "infra_premium": r["infra_premium"],
        })

    return results


# ---------------------------------------------------------------------------
# Automation → Levy → GUF Compensation Stress
# ---------------------------------------------------------------------------

def automation_levy_guf_stress(
    parcel_inventory: list[dict] | None = None,
    epsilon_start: float = 0.20,
    epsilon_end: float = 0.80,
    n_periods: int = 20,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    levy_rates: dict | None = None,
    median_income: float = 0.0,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
) -> dict:
    """
    Multi-period stress: automation rises → levy falls → does GUF compensate?

    Models the core fiscal loop as ε increases over n_periods:
      - Labor income (EOH pipeline) falls → levy revenue falls
      - GUF revenue tracks the Ψ(ε) bell curve: peaks near ε=0.40, then declines
      - Sufficiency guarantee cost changes with ε (rising per-person, fewer recipients)
      - Trust balance evolves period-by-period

    Per period:
      1. ε = epsilon_start + i × (epsilon_end − epsilon_start) / n_periods
      2. levy_revenue  = eoh_to_teh_pipeline(ε)["teh_created"] × levy_rate
      3. guf_net_inflow = compute_collective_guf(parcel_inventory, ε)["guf_net_inflow"]
      4. stew_cost     = stewardship_allocation(capital_stock_teh, ..., ε, trust_balance)
      5. guar_cost     = sufficiency_guarantee(population, ε)["total_cost_teh"]
      6. trust_result  = trust_management(trust_balance, levy + guf, stew, guar, ...)
      7. trust_balance = trust_result["trust_end"]   (carries forward to next period)

    Args:
        parcel_inventory:  Standard parcel dicts (see land/collective.py schema).
                           None → 1 000-parcel synthetic urban inventory.
        epsilon_start:     Starting ε [0.0, 0.99].
        epsilon_end:       Ending ε [epsilon_start, 0.99].
        n_periods:         Number of periods to simulate.
        population:        Total population.
        trust_balance:     Initial Trust balance.
        capital_stock_teh: Capital stock (TEH).
        capital_age_ratio: Mean asset age ratio.
        levy_rates:        Override default levy rates.
        median_income:     Collective median income for GUF subsidy calculation.
        dep_rate:          Trust depreciation rate.
        div_rate:          Trust dividend fraction.

    Returns:
        dict: {
          "scenario":             "automation_levy_guf_stress",
          "trajectory":           list[dict],  one row per period
          "parcel_count":         int,
          "epsilon_range":        [float, float],
          "levy_peak_period":     int,   period with highest levy_revenue
          "guf_peak_period":      int,   period with highest guf_net_inflow
          "crossover_period":     int|None,  first period where guf > levy
          "first_insolvency":     int|None,  first period solvent=False
          "compensation_adequacy": float,  mean(guf / levy_shortfall) when levy < baseline
          "outcome":              str,   ADEQUATE / PARTIAL / CRISIS
          "recommendation":       str,
        }

    Each trajectory row:
        {period, epsilon, levy_revenue, guf_net_inflow, guf_levy_ratio,
         sufficiency_cost, trust_end, solvent}
    """
    inventory = parcel_inventory if parcel_inventory is not None else make_urban_collective(1_000)
    rates      = levy_rates or {"sufficiency": SUFF_LEVY_RATE}
    eps_delta  = (epsilon_end - epsilon_start) / max(n_periods, 1)

    trajectory: list[dict] = []
    bal = trust_balance

    for i in range(n_periods):
        eps = epsilon_start + i * eps_delta

        labor_income = eoh_to_teh_pipeline(epsilon=eps, population=population)["teh_created"]
        levy_rev     = levy_collection(labor_income, rates)["total_levied"]

        guf_result   = compute_collective_guf(inventory, eps, median_income=median_income)
        guf_net      = guf_result["guf_net_inflow"]

        stew_cost    = stewardship_allocation(
            capital_stock_teh, capital_age_ratio, eps, bal
        )["teh_allocated"]
        guar_cost    = sufficiency_guarantee(
            population, eps,
            meaningful_activity_teh=MEANINGFUL_ACTIVITY_TEH_BASE,
        )["total_cost_teh"]

        trust_result = trust_management(
            bal,
            levy_rev + guf_net,
            stew_cost,
            guar_cost,
            dep_rate, div_rate, eps,
        )
        bal = trust_result["trust_end"]

        trajectory.append({
            "period":          i,
            "epsilon":         eps,
            "levy_revenue":    levy_rev,
            "guf_net_inflow":  guf_net,
            "guf_levy_ratio":  guf_net / max(levy_rev, 1.0),
            "sufficiency_cost": guar_cost,
            "trust_end":       bal,
            "solvent":         trust_result["solvent"],
        })

    if not trajectory:
        return {
            "scenario": "automation_levy_guf_stress",
            "trajectory": [],
            "parcel_count": len(inventory),
            "epsilon_range": [epsilon_start, epsilon_end],
            "levy_peak_period": 0,
            "guf_peak_period": 0,
            "crossover_period": None,
            "first_insolvency": None,
            "compensation_adequacy": 0.0,
            "outcome": "ADEQUATE",
            "recommendation": "No periods simulated.",
        }

    levy_peak = max(range(n_periods), key=lambda j: trajectory[j]["levy_revenue"])
    guf_peak  = max(range(n_periods), key=lambda j: trajectory[j]["guf_net_inflow"])

    baseline_levy   = trajectory[0]["levy_revenue"]
    crossover_period: int | None = None
    first_insolvency: int | None = None

    shortfall_periods: list[float] = []
    adequacy_ratios:   list[float] = []

    for j, row in enumerate(trajectory):
        if first_insolvency is None and not row["solvent"]:
            first_insolvency = j
        if crossover_period is None and row["guf_net_inflow"] > row["levy_revenue"]:
            crossover_period = j
        if row["levy_revenue"] < baseline_levy:
            shortfall = baseline_levy - row["levy_revenue"]
            shortfall_periods.append(shortfall)
            adequacy_ratios.append(row["guf_net_inflow"] / max(shortfall, 1.0))

    compensation_adequacy = (
        sum(adequacy_ratios) / len(adequacy_ratios) if adequacy_ratios else 0.0
    )

    insolvent_count = sum(1 for r in trajectory if not r["solvent"])
    first_third     = n_periods // 3

    if first_insolvency is None:
        outcome = "ADEQUATE"
    elif first_insolvency <= first_third:
        outcome = "CRISIS"
    elif insolvent_count >= n_periods // 2:
        outcome = "PARTIAL"
    else:
        outcome = "ADEQUATE"

    guf_peak_eps = trajectory[guf_peak]["epsilon"]
    rec = (
        f"Automation stress ε={epsilon_start:.2f}→{epsilon_end:.2f} over {n_periods} periods "
        f"({len(inventory)} parcels): levy peaks at period {levy_peak} "
        f"(ε={trajectory[levy_peak]['epsilon']:.2f}), GUF peaks at period {guf_peak} "
        f"(ε={guf_peak_eps:.2f}, Ψ-driven). "
        f"Crossover (GUF>levy) at period "
        f"{'none' if crossover_period is None else crossover_period}. "
        f"Compensation adequacy: {compensation_adequacy:.1%}. "
        f"First insolvency: {'none' if first_insolvency is None else f'period {first_insolvency}'}. "
        f"Outcome: {outcome}."
    )

    return {
        "scenario":              "automation_levy_guf_stress",
        "trajectory":            trajectory,
        "parcel_count":          len(inventory),
        "epsilon_range":         [epsilon_start, epsilon_end],
        "levy_peak_period":      levy_peak,
        "guf_peak_period":       guf_peak,
        "crossover_period":      crossover_period,
        "first_insolvency":      first_insolvency,
        "compensation_adequacy": compensation_adequacy,
        "outcome":               outcome,
        "recommendation":        rec,
    }
