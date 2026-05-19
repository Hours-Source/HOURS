"""
scenarios/shocks — Sudden-onset shock scenarios.

Three scenarios that model abrupt state changes and assess whether the
EOH/fiscal system can absorb them:

  automation_failure_shock  — Sudden loss of automation at a given ε
  demographic_shock         — Sudden population change (growth, decline, aging)
  ecological_eoh_spike      — Threshold ecological failure (EOH spike)

Each returns a structured dict with "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"}
and a human-readable "recommendation".

Mission Statement: §"Automation failure — the reserve must cover critical
infrastructure EOH"; §"Demographic shock"; §"Ecological EOH spike"
"""

from __future__ import annotations

from hours_eoh.data import (
    AGE_GROUPS,
    PERSONAL_EOH_BASE,
    ESSENTIAL_DOMAINS,
    H_MIN,
    ECOLOGICAL_BASE_RATE,
    ECOLOGICAL_THRESHOLD,
    TRUST_BASE_TEH,
    DEP_RATE,
    DIV_RATE,
    SUFF_LEVY_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    CAPITAL_STOCK_DEFAULT,
)
from hours_eoh.core.eoh_generation import (
    personal_eoh,
    infrastructure_eoh,
    ecological_eoh,
    knowledge_eoh,
    total_eoh as compute_total_eoh,
)
from hours_eoh.core.fiscal import (
    levy_collection,
    stewardship_allocation,
    sufficiency_guarantee,
    trust_management,
)
from hours_eoh.core.workforce import automation_failure_scenario, minimum_hours_allocation

_LABOR_INCOME_BASE:       float = 2_200_000_000.0
_LABOR_INCOME_MIN:        float = 300_000_000.0
_LABOR_INCOME_AUTO_SLOPE: float = 0.80


# ---------------------------------------------------------------------------
# Automation Failure Shock
# ---------------------------------------------------------------------------

def automation_failure_shock(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
    knowledge_base_size: float = 10.0,
    workforce_size: float = 600_000.0,
    mean_entropy_reduction_capacity: float = 1200.0,
    reserve_fraction: float = 0.155,
) -> dict:
    """
    Simulate sudden loss of automation at a given ε level.

    At epsilon ε, automation was handling ε×total_eoh of demand. If automation
    fails suddenly, the workforce (calibrated for the ε economy) must cover this.

    Args:
        epsilon: Automation level at failure [0.0, 0.99].
        population: Total population.
        capital_stock_teh: Capital stock value.
        capital_age_ratio: Mean asset age ratio.
        ecosystem_health: Ecological health [0,1].
        knowledge_base_size: Knowledge base size.
        workforce_size: Working-age population.
        mean_entropy_reduction_capacity: EOH/yr per working-age worker.
        reserve_fraction: Fraction of workforce in the competency reserve.

    Returns:
        dict: {
          "scenario":             str,
          "epsilon":              float,
          "total_eoh":            float,
          "automation_eoh":       float,
          "human_baseline_eoh":   float,
          "reserve_capacity_eoh": float,
          "h_min_labor_eoh":      float,
          "coverage_ratio":       float,
          "covered":              bool,
          "severity":             str,
          "outcome":              str,
          "failure_boundary":     float | None,
          "recommendation":       str,
        }
    """
    from hours_eoh.core.trajectory import canonical_physical_state as _cps
    _state = _cps(epsilon)

    pers_eoh  = personal_eoh(population, age_distribution=_state["age_distribution"])
    infra_eoh = infrastructure_eoh(
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
    )
    eco_eoh   = ecological_eoh(
        ecosystem_health,
        monitoring_capability=_state["monitoring_capability"],
        base_rate=ECOLOGICAL_BASE_RATE,
    )
    know_eoh  = knowledge_eoh(
        knowledge_base_size,
        complexity_per_unit=_state["knowledge_complexity_per_unit"],
    )
    tot_eoh = pers_eoh + infra_eoh + eco_eoh + know_eoh

    automation_eoh = tot_eoh * epsilon
    human_baseline = tot_eoh * (1.0 - epsilon)

    reserve_eoh = workforce_size * reserve_fraction * mean_entropy_reduction_capacity
    h_min_alloc = minimum_hours_allocation(
        h_min=H_MIN, workforce_size=workforce_size, epsilon=epsilon
    )
    h_min_eoh = h_min_alloc["total_labor_eoh"]

    result = automation_failure_scenario(
        epsilon=epsilon,
        critical_eoh=automation_eoh,
        reserve_capacity_eoh=reserve_eoh,
        h_min_labor_eoh=h_min_eoh,
        workforce_size=workforce_size,
    )

    failure_boundary = None
    if not result["covered"]:
        failure_boundary = epsilon
    else:
        for i in range(1, 20):
            test_eps = min(0.99, epsilon + i * 0.05)
            _test_state = _cps(test_eps)
            test_automation = compute_total_eoh(
                population=population,
                age_distribution=_test_state["age_distribution"],
                capital_stock=capital_stock_teh * (1.0 + (test_eps - epsilon)),
                capital_age_ratio=capital_age_ratio,
                ecosystem_health=ecosystem_health,
                monitoring_capability=_test_state["monitoring_capability"],
            )["total"] * test_eps
            test_result = automation_failure_scenario(
                epsilon=test_eps,
                critical_eoh=test_automation,
                reserve_capacity_eoh=reserve_eoh,
                h_min_labor_eoh=h_min_eoh,
            )
            if not test_result["covered"]:
                failure_boundary = test_eps
                break

    severity = result["severity"]
    if severity == "NONE":
        outcome = "STABLE"
    elif severity in ("MODERATE", "SEVERE"):
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    return {
        "scenario":             "automation_failure_shock",
        "epsilon":              epsilon,
        "total_eoh":            tot_eoh,
        "automation_eoh":       automation_eoh,
        "human_baseline_eoh":   human_baseline,
        "reserve_capacity_eoh": reserve_eoh,
        "h_min_labor_eoh":      h_min_eoh,
        "coverage_ratio":       result["coverage_ratio"],
        "gap_eoh":              result["gap_eoh"],
        "covered":              result["covered"],
        "severity":             severity,
        "outcome":              outcome,
        "failure_boundary":     failure_boundary,
        "recommendation":       result["recommendation"],
    }


# ---------------------------------------------------------------------------
# Demographic Shock
# ---------------------------------------------------------------------------

def demographic_shock(
    epsilon: float,
    shock_type: str,
    magnitude: float,
    trust_balance: float = TRUST_BASE_TEH,
    labor_income_base: float = _LABOR_INCOME_BASE,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
) -> dict:
    """
    Simulate a sudden demographic change and assess fiscal/EOH impact.

    Shock types:
      "growth":  Sudden population increase (magnitude = fractional growth, e.g. 0.20 = +20%)
      "decline": Sudden population decrease (magnitude = fractional loss)
      "aging":   Shift in age distribution toward elderly (magnitude = fraction of
                 working-age that shifts to elderly)

    Args:
        epsilon: Automation level at time of shock.
        shock_type: One of "growth", "decline", "aging".
        magnitude: Fractional magnitude of the shock [0.0, 1.0].
        trust_balance: Trust fund balance at time of shock.
        labor_income_base: Labor income at ε=0.
        meaningful_activity_teh: Sufficiency floor TEH.
        suff_levy_rate: Levy rate.
        dep_rate: Trust depreciation rate.
        div_rate: Trust dividend fraction.
        capital_stock_teh: Capital stock.
        capital_age_ratio: Capital age ratio.

    Returns:
        dict with "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"} and "recommendation".
    """
    VALID = ("growth", "decline", "aging")
    if shock_type not in VALID:
        raise ValueError(f"shock_type must be one of {VALID}, got '{shock_type}'")
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError(f"magnitude must be in [0, 1], got {magnitude}")

    BASE_POPULATION = 1_000_000.0
    base_dist = {g: AGE_GROUPS[g]["fraction"] * BASE_POPULATION for g in AGE_GROUPS}

    base_eoh_data = compute_total_eoh(
        epsilon,
        population=BASE_POPULATION,
        age_distribution=base_dist,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
    )
    base_eoh = base_eoh_data["total"]

    labor_income = max(
        _LABOR_INCOME_MIN,
        labor_income_base * (1.0 - epsilon * _LABOR_INCOME_AUTO_SLOPE),
    )
    levies = levy_collection(labor_income, {"sufficiency": suff_levy_rate})
    stew   = stewardship_allocation(capital_stock_teh, capital_age_ratio,
                                    epsilon, trust_balance)
    guar_before = sufficiency_guarantee(
        BASE_POPULATION, epsilon, meaningful_activity_teh=meaningful_activity_teh
    )
    trust_before = trust_management(
        trust_balance, levies["total_levied"],
        stew["teh_allocated"], guar_before["total_cost_teh"],
        dep_rate, div_rate, epsilon,
    )

    if shock_type == "growth":
        new_population = BASE_POPULATION * (1.0 + magnitude)
        new_dist = {g: AGE_GROUPS[g]["fraction"] * new_population for g in AGE_GROUPS}
    elif shock_type == "decline":
        new_population = BASE_POPULATION * (1.0 - magnitude)
        new_dist = {g: AGE_GROUPS[g]["fraction"] * new_population for g in AGE_GROUPS}
    else:  # aging
        shift = BASE_POPULATION * magnitude
        new_dist = dict(base_dist)
        new_dist["working_age"] = max(0.0, base_dist["working_age"] - shift)
        new_dist["elderly"]    = base_dist["elderly"] + shift
        new_population = sum(new_dist.values())

    new_eoh_data = compute_total_eoh(
        epsilon,
        population=new_population,
        age_distribution=new_dist,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
    )
    new_eoh = new_eoh_data["total"]

    guar_after  = sufficiency_guarantee(
        new_population, epsilon, meaningful_activity_teh=meaningful_activity_teh
    )
    trust_after = trust_management(
        trust_balance, levies["total_levied"],
        stew["teh_allocated"], guar_after["total_cost_teh"],
        dep_rate, div_rate, epsilon,
    )

    eoh_delta = new_eoh - base_eoh

    if trust_after["solvent"]:
        outcome = "STABLE"
    elif trust_after["surplus_deficit"] > -trust_balance * 0.05:
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    rec = (
        f"{shock_type.title()} shock of {magnitude:.0%} at ε={epsilon:.2f}: "
        f"population {BASE_POPULATION:.0f} → {new_population:.0f}. "
        f"EOH demand {'+' if eoh_delta >= 0 else ''}{eoh_delta:,.0f} h/yr. "
        f"Trust {'solvent' if trust_after['solvent'] else 'INSOLVENT'}. "
        f"Outcome: {outcome}."
    )

    return {
        "scenario":             "demographic_shock",
        "shock_type":           shock_type,
        "magnitude":            magnitude,
        "epsilon":              epsilon,
        "population_before":    BASE_POPULATION,
        "population_after":     new_population,
        "eoh_before":           base_eoh,
        "eoh_after":            new_eoh,
        "eoh_delta":            eoh_delta,
        "guarantee_before":     guar_before["total_cost_teh"],
        "guarantee_after":      guar_after["total_cost_teh"],
        "trust_solvent_before": trust_before["solvent"],
        "trust_solvent_after":  trust_after["solvent"],
        "surplus_deficit_after": trust_after["surplus_deficit"],
        "outcome":              outcome,
        "recommendation":       rec,
    }


# ---------------------------------------------------------------------------
# Ecological EOH Spike
# ---------------------------------------------------------------------------

def ecological_eoh_spike(
    epsilon: float,
    ecosystem_health_before: float,
    ecosystem_health_after: float,
    deferred_ecological_eoh: float = 0.0,
    base_rate: float = ECOLOGICAL_BASE_RATE,
    trust_balance: float = TRUST_BASE_TEH,
    labor_income: float = _LABOR_INCOME_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    population: float = 1_000_000.0,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
) -> dict:
    """
    Simulate threshold ecological failure and assess whether the system absorbs it.

    A sudden drop in ecosystem_health below the 0.40 threshold triggers a nonlinear
    EOH spike. Checks whether the Trust can absorb the added cost.

    Args:
        epsilon: Automation level at time of failure.
        ecosystem_health_before: Ecosystem health before collapse [0, 1].
        ecosystem_health_after: Ecosystem health after collapse [0, 1].
        deferred_ecological_eoh: Pre-existing deferred ecological EOH.
        base_rate: Ecological EOH base rate.
        trust_balance: Trust fund balance.
        labor_income: Annual labor income.
        suff_levy_rate: Levy rate.
        dep_rate: Trust depreciation rate.
        div_rate: Trust dividend fraction.
        population: Population.
        meaningful_activity_teh: Sufficiency floor TEH.
        capital_stock_teh: Capital stock.
        capital_age_ratio: Capital age ratio.

    Returns:
        dict with "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"} and "recommendation".
    """
    eoh_before = ecological_eoh(ecosystem_health_before, epsilon,
                                base_rate=base_rate,
                                deferred=deferred_ecological_eoh)
    eoh_after  = ecological_eoh(ecosystem_health_after,  epsilon,
                                base_rate=base_rate,
                                deferred=deferred_ecological_eoh)

    eoh_spike   = max(0.0, eoh_after - eoh_before)
    spike_ratio = eoh_spike / max(eoh_before, 1.0)
    crossed_thresh = (ecosystem_health_before > ECOLOGICAL_THRESHOLD
                      >= ecosystem_health_after)

    levies = levy_collection(labor_income, {"sufficiency": suff_levy_rate})
    stew   = stewardship_allocation(capital_stock_teh, capital_age_ratio,
                                    epsilon, trust_balance)
    guar   = sufficiency_guarantee(
        population, epsilon, meaningful_activity_teh=meaningful_activity_teh
    )
    trust  = trust_management(
        trust_balance, levies["total_levied"],
        stew["teh_allocated"],
        guar["total_cost_teh"] + eoh_spike,
        dep_rate, div_rate, epsilon,
    )

    trust_absorbs = trust["solvent"]

    if not crossed_thresh:
        outcome = "STABLE" if trust_absorbs else "DEGRADED"
        rec = (
            f"Health dropped {ecosystem_health_before:.2f} → {ecosystem_health_after:.2f} "
            f"but threshold ({ECOLOGICAL_THRESHOLD:.2f}) was not crossed. "
            f"EOH spike: {eoh_spike:,.0f} h/yr ({spike_ratio:.1%} increase). "
            f"Trust {'absorbs' if trust_absorbs else 'CANNOT absorb'} spike."
        )
    elif trust_absorbs:
        outcome = "DEGRADED"
        rec = (
            f"Threshold crossed ({ecosystem_health_before:.2f} → {ecosystem_health_after:.2f}). "
            f"EOH spike: {eoh_spike:,.0f} h/yr ({spike_ratio:.1%} above baseline). "
            f"Trust absorbs spike this period. "
            f"Ecosystem restoration EOH must be registered to prevent compounding."
        )
    else:
        outcome = "CRISIS"
        rec = (
            f"CRISIS: Threshold crossed ({ecosystem_health_before:.2f} → {ecosystem_health_after:.2f}). "
            f"EOH spike: {eoh_spike:,.0f} h/yr ({spike_ratio:.1%} above baseline). "
            f"Trust CANNOT absorb spike (surplus_deficit={trust['surplus_deficit']:,.0f}). "
            f"Emergency ecological EOH registration and trust disbursement required."
        )

    return {
        "scenario":              "ecological_eoh_spike",
        "epsilon":               epsilon,
        "health_before":         ecosystem_health_before,
        "health_after":          ecosystem_health_after,
        "eoh_before":            eoh_before,
        "eoh_after":             eoh_after,
        "eoh_spike":             eoh_spike,
        "spike_ratio":           spike_ratio,
        "threshold_crossed":     crossed_thresh,
        "trust_surplus_deficit": trust["surplus_deficit"],
        "trust_absorbs":         trust_absorbs,
        "absorbed":              trust_absorbs,
        "outcome":               outcome,
        "recommendation":        rec,
    }


# ---------------------------------------------------------------------------
# Labor Income Shock
# ---------------------------------------------------------------------------

def labor_income_shock(
    epsilon: float,
    income_fraction: float,
    trust_balance: float = TRUST_BASE_TEH,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
) -> dict:
    """
    Simulate a sudden collapse in labor income (TEH creation).

    income_fraction controls how much of baseline labor income remains after
    the shock (e.g., 0.50 = 50% of normal income). Baseline income is derived
    from the EOH pipeline at the given ε. Runs fiscal_snapshot() at both
    baseline and shocked income levels to measure the fiscal impact.

    Args:
        epsilon:         Automation level [0.0, 0.99].
        income_fraction: Fraction of baseline income remaining [0.0, 1.0].
                         1.0 = no shock; 0.0 = total income collapse.
        trust_balance:   Trust fund balance at time of shock.
        population:      Population.
        capital_stock_teh: Capital stock.
        capital_age_ratio: Capital age ratio.
        meaningful_activity_teh: Sufficiency floor TEH.
        suff_levy_rate:  Levy rate.
        dep_rate:        Trust depreciation rate.
        div_rate:        Trust dividend fraction.

    Returns:
        dict: {
          "scenario":               str,
          "epsilon":                float,
          "income_fraction":        float,
          "baseline_income":        float,
          "shocked_income":         float,
          "trust_solvent_before":   bool,
          "trust_solvent_after":    bool,
          "surplus_deficit_before": float,
          "surplus_deficit_after":  float,
          "surplus_deficit_delta":  float,
          "outcome":                str,   STABLE / DEGRADED / CRISIS
          "recommendation":         str,
        }
    """
    if not 0.0 <= income_fraction <= 1.0:
        raise ValueError(f"income_fraction must be in [0, 1], got {income_fraction}")

    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.fiscal import fiscal_snapshot

    pipeline = eoh_to_teh_pipeline(epsilon=epsilon, population=population)
    baseline_income = max(pipeline["teh_created"], _LABOR_INCOME_MIN)
    shocked_income  = max(baseline_income * income_fraction, _LABOR_INCOME_MIN)

    snap_before = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=baseline_income,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        meaningful_activity_teh=meaningful_activity_teh,
        levy_rates={"sufficiency": suff_levy_rate},
        dep_rate=dep_rate,
        div_rate=div_rate,
    )
    snap_after = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=shocked_income,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        meaningful_activity_teh=meaningful_activity_teh,
        levy_rates={"sufficiency": suff_levy_rate},
        dep_rate=dep_rate,
        div_rate=div_rate,
    )

    surplus_before = snap_before["trust"]["surplus_deficit"]
    surplus_after  = snap_after["trust"]["surplus_deficit"]
    delta          = surplus_after - surplus_before

    if snap_after["solvent"]:
        outcome = "STABLE"
    elif abs(surplus_after) < trust_balance * 0.10:
        outcome = "DEGRADED"
    else:
        outcome = "CRISIS"

    rec = (
        f"Labor income shock at ε={epsilon:.2f}: income reduced to "
        f"{income_fraction:.0%} of baseline "
        f"({baseline_income:,.0f} → {shocked_income:,.0f} TEH/yr). "
        f"Trust {'SOLVENT' if snap_after['solvent'] else 'INSOLVENT'} after shock. "
        f"Surplus/deficit delta: {delta:+,.0f} TEH. Outcome: {outcome}."
    )

    return {
        "scenario":               "labor_income_shock",
        "epsilon":                epsilon,
        "income_fraction":        income_fraction,
        "baseline_income":        baseline_income,
        "shocked_income":         shocked_income,
        "trust_solvent_before":   snap_before["solvent"],
        "trust_solvent_after":    snap_after["solvent"],
        "surplus_deficit_before": surplus_before,
        "surplus_deficit_after":  surplus_after,
        "surplus_deficit_delta":  delta,
        "outcome":                outcome,
        "recommendation":         rec,
    }


# ---------------------------------------------------------------------------
# Compound Shock
# ---------------------------------------------------------------------------

def compound_shock(
    epsilon: float,
    ecology_collapse: bool = False,
    ecosystem_health_before: float = 0.70,
    ecosystem_health_after: float = 0.30,
    demographic_shock_spec: dict | None = None,
    automation_fraction_lost: float = 0.0,
    trust_balance: float = TRUST_BASE_TEH,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
) -> dict:
    """
    Simulate multiple simultaneous shocks and assess combined Trust absorption.

    Runs each enabled shock component independently, then combines their EOH
    deltas and checks whether the Trust can absorb the aggregate obligation.
    The combined outcome is always at least as severe as the worst individual
    outcome.

    Shock components (each optional):
      ecology_collapse:        Ecological EOH spike (uses ecological_eoh_spike()).
      demographic_shock_spec:  Dict with "shock_type" and "magnitude" keys,
                               passed to demographic_shock(). None = disabled.
      automation_fraction_lost: Fraction of automation capacity that fails [0,1],
                                passed to automation_failure_shock(). 0 = disabled.

    Args:
        epsilon:                 Automation level [0.0, 0.99].
        ecology_collapse:        Enable ecological shock component.
        ecosystem_health_before: Ecosystem health before ecological collapse.
        ecosystem_health_after:  Ecosystem health after ecological collapse.
        demographic_shock_spec:  Dict with keys "shock_type" str and "magnitude" float.
        automation_fraction_lost: Fraction of automation that fails [0.0, 1.0].
        trust_balance:           Trust fund balance.
        population:              Population.
        capital_stock_teh:       Capital stock.
        capital_age_ratio:       Capital age ratio.
        meaningful_activity_teh: Sufficiency floor TEH.
        suff_levy_rate:          Levy rate.
        dep_rate:                Trust depreciation rate.
        div_rate:                Trust dividend fraction.

    Returns:
        dict: {
          "scenario":             str,
          "epsilon":              float,
          "individual_outcomes":  dict,   keyed by shock name
          "combined_eoh_delta":   float,  sum of all EOH deltas
          "trust_absorbs_combined": bool,
          "combined_outcome":     str,    STABLE / DEGRADED / CRISIS
          "recommendation":       str,
        }
    """
    _SEVERITY = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
    _INV_SEVERITY = {0: "STABLE", 1: "DEGRADED", 2: "CRISIS"}

    individual_outcomes: dict = {}
    combined_eoh_delta: float = 0.0

    labor_income = max(
        _LABOR_INCOME_MIN,
        _LABOR_INCOME_BASE * (1.0 - epsilon * _LABOR_INCOME_AUTO_SLOPE),
    )

    # --- Ecological shock -----------------------------------------------
    if ecology_collapse:
        eco_result = ecological_eoh_spike(
            epsilon=epsilon,
            ecosystem_health_before=ecosystem_health_before,
            ecosystem_health_after=ecosystem_health_after,
            trust_balance=trust_balance,
            labor_income=labor_income,
            suff_levy_rate=suff_levy_rate,
            dep_rate=dep_rate,
            div_rate=div_rate,
            population=population,
            meaningful_activity_teh=meaningful_activity_teh,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
        )
        individual_outcomes["ecological_eoh_spike"] = eco_result["outcome"]
        combined_eoh_delta += eco_result["eoh_spike"]

    # --- Demographic shock -----------------------------------------------
    if demographic_shock_spec is not None:
        dem_result = demographic_shock(
            epsilon=epsilon,
            shock_type=demographic_shock_spec["shock_type"],
            magnitude=demographic_shock_spec["magnitude"],
            trust_balance=trust_balance,
            labor_income_base=labor_income,
            meaningful_activity_teh=meaningful_activity_teh,
            suff_levy_rate=suff_levy_rate,
            dep_rate=dep_rate,
            div_rate=div_rate,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
        )
        individual_outcomes["demographic_shock"] = dem_result["outcome"]
        combined_eoh_delta += max(0.0, dem_result["eoh_delta"])

    # --- Automation failure shock ----------------------------------------
    if automation_fraction_lost > 0.0:
        auto_result = automation_failure_shock(
            epsilon=epsilon,
            population=population,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
        )
        individual_outcomes["automation_failure_shock"] = auto_result["outcome"]
        # automation_eoh scaled by fraction_lost
        combined_eoh_delta += auto_result["automation_eoh"] * automation_fraction_lost

    # --- Combined fiscal check -------------------------------------------
    levies = levy_collection(labor_income, {"sufficiency": suff_levy_rate})
    stew   = stewardship_allocation(capital_stock_teh, capital_age_ratio,
                                    epsilon, trust_balance)
    guar   = sufficiency_guarantee(population, epsilon,
                                   meaningful_activity_teh=meaningful_activity_teh)
    trust  = trust_management(
        trust_balance, levies["total_levied"],
        stew["teh_allocated"],
        guar["total_cost_teh"] + combined_eoh_delta,
        dep_rate, div_rate, epsilon,
    )
    trust_absorbs = trust["solvent"]

    # Combined outcome >= worst individual outcome
    worst_individual = max(
        (_SEVERITY.get(v, 0) for v in individual_outcomes.values()),
        default=0,
    )
    if trust_absorbs:
        combined_severity = max(worst_individual, _SEVERITY["STABLE"])
    else:
        combined_deficit = abs(trust["surplus_deficit"])
        if combined_deficit < trust_balance * 0.10:
            combined_severity = max(worst_individual, _SEVERITY["DEGRADED"])
        else:
            combined_severity = max(worst_individual, _SEVERITY["CRISIS"])

    combined_outcome = _INV_SEVERITY[combined_severity]

    if not individual_outcomes:
        combined_outcome = "STABLE"

    rec = (
        f"Compound shock at ε={epsilon:.2f}: "
        f"combined EOH delta {combined_eoh_delta:,.0f} h/yr across "
        f"{len(individual_outcomes)} component(s). "
        f"Trust {'absorbs' if trust_absorbs else 'CANNOT absorb'} combined obligation. "
        f"Individual outcomes: {individual_outcomes}. "
        f"Combined outcome: {combined_outcome}."
    )

    return {
        "scenario":               "compound_shock",
        "epsilon":                epsilon,
        "individual_outcomes":    individual_outcomes,
        "combined_eoh_delta":     combined_eoh_delta,
        "trust_absorbs_combined": trust_absorbs,
        "combined_outcome":       combined_outcome,
        "recommendation":         rec,
    }
