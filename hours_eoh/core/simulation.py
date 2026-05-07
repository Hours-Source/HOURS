"""
Multi-Period Simulation Engine

Provides the state-loop infrastructure that wires per-event functions into a
coherent multi-year simulation. Without this, the package is a collection of
stateless functions that can compute any individual period correctly but cannot
answer questions like "what does the economy look like in 20 years at ε=0.60?"

The simulation is deliberately *aggregate*: it tracks population-level
quantities (total population, workforce size, trust balance, ecological health,
capital age) rather than individual asset or person lifecycles. For finer
granularity, call the individual functions (aging, birth_event, death_event,
execute_writedown) directly.

Key design principles:
- State is a plain dict (no class) for easy inspection and serialization.
- simulate_period() is a pure function: same state + same inputs → same output.
  It does not mutate state; it returns a new state dict.
- All intermediate values are returned in period_result for auditability.
- Epsilon is part of state so trajectories can model automation progression.

Mission Statement: §"Stress tests — identify failure boundaries"; §"The system
must remain coherent across the full automation arc"; §"Automation failure —
the reserve must cover critical infrastructure EOH."
"""

from __future__ import annotations
import math

from hours_eoh.data import (
    DEP_RATE, DIV_RATE, SUFF_LEVY_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE, MEANINGFUL_ACTIVITY_TEH_SCALE,
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT, BASKET_EOH_CONTENT,
    LABOR_INCOME_MIN_TEH,
    CAPITAL_FAILURE_RATE, CAPITAL_WRITEDOWN_MONITORING_SLOPE,
    ESTATE_INHERITANCE_FRACTION, ESTATE_LEVY_FRACTION, ESTATE_PERSONAL_RESERVE_YEARS,
    ACCUMULATION_CEILING_MULTIPLIER,
)


# ---------------------------------------------------------------------------
# Economy State
# ---------------------------------------------------------------------------

def make_economy_state(
    epsilon: float = 0.40,
    population: float = 1_000_000.0,
    workforce_fraction: float = 0.60,
    trust_balance: float = TRUST_BASE_TEH,
    labor_income_teh: float = 5_000_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
    deferred_ecological: float = 0.0,
    knowledge_complexity: float = 1.0,
    teh_created_cumulative: float = 0.0,
    teh_destroyed_cumulative: float = 0.0,
    capital_eoh_eliminated: float = 0.0,
    capital_personal_eoh_fulfilled: float = 0.0,
    capital_embodied_teh: float | None = None,
    teh_endowment: float | None = None,
    period: int = 0,
    monitoring_capability: float | None = None,
    deferred_infrastructure_eoh: float = 0.0,
    infra_deferred_years: float = 0.0,
) -> dict:
    """
    Construct a well-formed economy state dict for simulate_period().

    The state captures all quantities that persist between periods. Per-period
    inputs (levy rates, mean multiplier, registration share overrides) are
    passed directly to simulate_period() rather than stored in state.

    Args:
        epsilon: Current automation level [0.0, 0.99].
        population: Total population (all ages).
        workforce_fraction: Fraction of population in active workforce [0, 1].
        trust_balance: Trust fund balance at start of this period (TEH).
        labor_income_teh: Recorded labor income from the last completed period (TEH).
                          Written for observability; simulate_period() derives income
                          from the EOH pipeline (teh_created), not from this field.
        capital_stock_teh: Aggregate capital stock value (TEH at ε=0 baseline).
        capital_age_ratio: Mean(age / design_life) across all capital assets ∈ [0, 1].
        ecosystem_health: Aggregate ecosystem state ∈ [0, 1].
        deferred_ecological: Accumulated deferred ecological EOH (hours).
        knowledge_complexity: Relative knowledge base size (1.0 = reference).
        teh_created_cumulative: Cumulative TEH created since simulation start.
        teh_destroyed_cumulative: Cumulative TEH destroyed since start.
        capital_eoh_eliminated: Aggregate annual EOH eliminated by capital stock.
        capital_personal_eoh_fulfilled: Aggregate annual personal EOH fulfilled
                                        by capital stock.
        capital_embodied_teh: TEH locked in the capital stock (not in free
            circulation). Represents the social wealth embodied in built assets.
            Grows via investment, shrinks via write-down. Defaults to
            capital_stock_teh when None (at simulation start, all capital value
            is embodied in assets).
        teh_endowment: Pre-simulation TEH wealth (Trust seed + initial capital).
            Used as the baseline for computing true circulating TEH each period.
            Preserved unchanged across periods once set. Defaults to
            trust_balance + capital_embodied_teh when None.
        period: Current period number (auto-incremented by simulate_period).
        monitoring_capability: Current monitoring capability ∈ [0, 1].
            Governs how much deferred ecological EOH is visible and how
            quickly infrastructure deterioration is caught. Defaults to the
            canonical trajectory value at epsilon when None.
        deferred_infrastructure_eoh: Accumulated deferred infrastructure EOH
            (hours). Grows if infrastructure maintenance is underfunded;
            drives compounding via eoh_compounding(). Default: 0.0.
        infra_deferred_years: Years the infrastructure EOH backlog has been
            accumulating. Drives the threshold-spike shape in eoh_compounding().
            Default: 0.0.

    Returns:
        State dict with all the above keys plus derived "workforce_size".
    """
    from hours_eoh.core.trajectory import canonical_physical_state as _cps
    _cap_embodied = capital_stock_teh if capital_embodied_teh is None else capital_embodied_teh
    _endowment    = (trust_balance + _cap_embodied) if teh_endowment is None else teh_endowment
    _monitoring   = _cps(epsilon)["monitoring_capability"] if monitoring_capability is None else monitoring_capability
    return {
        "epsilon":                       epsilon,
        "population":                    population,
        "workforce_fraction":            workforce_fraction,
        "workforce_size":                population * workforce_fraction,
        "trust_balance":                 trust_balance,
        "labor_income_teh":              labor_income_teh,
        "capital_stock_teh":             capital_stock_teh,
        "capital_age_ratio":             capital_age_ratio,
        "ecosystem_health":              ecosystem_health,
        "deferred_ecological":           deferred_ecological,
        "knowledge_complexity":          knowledge_complexity,
        "teh_created_cumulative":        teh_created_cumulative,
        "teh_destroyed_cumulative":      teh_destroyed_cumulative,
        "capital_eoh_eliminated":        capital_eoh_eliminated,
        "capital_personal_eoh_fulfilled": capital_personal_eoh_fulfilled,
        "capital_embodied_teh":          _cap_embodied,
        "teh_endowment":                 _endowment,
        "period":                        period,
        "monitoring_capability":         _monitoring,
        "deferred_infrastructure_eoh":   deferred_infrastructure_eoh,
        "infra_deferred_years":          infra_deferred_years,
    }


# ---------------------------------------------------------------------------
# Single-period simulation
# ---------------------------------------------------------------------------

def simulate_period(
    state: dict,
    *,
    # Demographic rates (applied to population each period)
    population_growth_rate: float = 0.005,    # net natural increase (births - deaths)
    # Capital dynamics
    capital_aging_rate: float = 0.015,        # age_ratio increase per period
    capital_investment_rate: float = 0.0,     # fraction of labor_income reinvested
    # Ecological dynamics
    ecological_degradation_rate: float = 0.002,   # ecosystem_health decline/period
    ecological_restoration_rate: float = 0.0,     # ecosystem_health restoration/period
    deferred_eco_growth_rate: float = 0.05,        # deferred EOH growth if ecosystem degraded
    # EOH / fiscal parameters
    levy_rates: dict[str, float] | None = None,
    mean_multiplier: float = 2.10,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    floor_fraction: float = 0.15,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    meaningful_activity_scale: float = MEANINGFUL_ACTIVITY_TEH_SCALE,
    # Labor income model: income scales with workforce and (1-ε)
    labor_income_scale: float | None = None,  # override auto-computation
    # Epsilon progression
    epsilon_delta: float = 0.0,               # automation advancement per period
    # TEH destruction calibration
    base_consumption_rate: float = 0.75,      # D2: fraction of period income consumed at ε=0
    # D3: biology-anchored terminal consumption (replaces D2 when use_d3=True)
    use_d3: bool = False,                     # True → biology-grounded destruction; False → D2 income model
    basket_eoh_content: float = BASKET_EOH_CONTENT,  # D3: personal EOH hours satisfied per basket
    # Knowledge complexity evolution
    knowledge_complexity_growth_rate: float = 0.0,   # fractional growth of knowledge_complexity per period
    # Care economy wiring (new-15)
    care_stipend_aggregate: float | None = None,  # None → auto-computed from demographics each period
                                                  # 0.0 → explicitly disable; >0 → caller override
    # D4 — CPI transaction-level destruction (Option 2)
    use_cpi_destruction: bool = True,     # TEH destroyed when capital delivers personal-EOH services
    # D5 — Estate dissolution on death (Option 1)
    use_estate_dissolution: bool = True,  # TEH written down on death above personal reserve
    estate_inheritance_fraction: float = ESTATE_INHERITANCE_FRACTION,
    estate_levy_fraction: float = ESTATE_LEVY_FRACTION,
    estate_reserve_years: float = ESTATE_PERSONAL_RESERVE_YEARS,
    # D6 — Accumulation ceiling (Option 3, disabled by default)
    use_accumulation_ceiling: bool = False,
    accumulation_ceiling_multiplier: float = ACCUMULATION_CEILING_MULTIPLIER,
) -> tuple[dict, dict]:
    """
    Advance the economy by one period and return (new_state, period_result).

    Applies events in causal order:
      1. Population: grow/shrink by population_growth_rate
      2. Capital: age by capital_aging_rate; grow via investment
      3. Ecology: degrade/restore ecosystem; accumulate deferred EOH
      4. EOH pipeline: total_eoh → human_share → registration → TEH creation
      5. Fiscal: levies → stewardship → guarantee → trust balance update
      6. TEH destruction: terminal consumption + capital write-down proxy
      7. State update: epsilon advances, cumulative TEH updated

    All intermediate values are captured in period_result for auditability.
    simulate_period() does NOT mutate state — it returns a fresh dict.

    Args:
        state: Current economy state dict (from make_economy_state() or prior
               simulate_period() call).
        population_growth_rate: Net population change per period (births - deaths).
                                Default 0.005 (0.5%/period growth).
        capital_aging_rate: Increase in capital_age_ratio per period.
                            At 0.015/period, stock reaches age_ratio=1.0 in ~47 periods.
        capital_investment_rate: Fraction of labor_income reinvested in capital
                                 stock. 0 = no new investment.
        ecological_degradation_rate: Ecosystem health decline per period if no
                                     restoration effort.
        ecological_restoration_rate: Ecosystem health improvement per period
                                     (e.g., from regenerative labor investment).
        deferred_eco_growth_rate: Rate at which deferred ecological EOH grows
                                  when ecosystem_health is below 0.5.
        levy_rates: Override default levy rates.
        mean_multiplier: Population-weighted mean multiplier.
        dep_rate: Trust depreciation rate.
        div_rate: Trust dividend fraction.
        floor_fraction: Fraction of population receiving guarantee.
        meaningful_activity_teh: Discretionary bonus at ε=0.
        meaningful_activity_scale: Quadratic ε-growth factor for bonus.
        labor_income_scale: If provided, override auto-computed labor income.
        epsilon_delta: Automation advancement this period. Apply before EOH.

    Returns:
        (new_state, period_result) where:
          - new_state: updated economy state dict for the next period
          - period_result: full intermediate breakdown (EOH, fiscal, TEH, etc.)

    Reference: Mission Statement §"The system must remain coherent across the
    full automation arc"; §"Automation failure"; §"The care economy transition."
    """
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline, human_eoh_per_domain
    from hours_eoh.core.fiscal import fiscal_snapshot
    from hours_eoh.core.trajectory import canonical_physical_state as _cps

    # ---- 1. Extract current state ------------------------------------------
    eps              = min(0.99, state["epsilon"] + epsilon_delta)
    population       = state["population"]
    workforce_frac   = state["workforce_fraction"]
    trust_bal        = state["trust_balance"]
    cap_stock        = state["capital_stock_teh"]
    cap_age          = state["capital_age_ratio"]
    eco_health       = state["ecosystem_health"]
    deferred_eco     = state["deferred_ecological"]
    know_complexity  = state["knowledge_complexity"]
    cap_eoh_elim     = state["capital_eoh_eliminated"]
    cap_pers_fulfil  = state["capital_personal_eoh_fulfilled"]
    teh_created_cum  = state["teh_created_cumulative"]
    teh_destr_cum    = state["teh_destroyed_cumulative"]
    cap_embodied     = state["capital_embodied_teh"]
    teh_endowment    = state["teh_endowment"]
    deferred_infra   = state.get("deferred_infrastructure_eoh", 0.0)
    infra_def_years  = state.get("infra_deferred_years", 0.0)

    # Physical state at current ε — used for monitoring_capability and
    # knowledge_complexity_per_unit (both are derived from the canonical arc
    # until a separate evolution sub-model is added).
    _canon = _cps(eps)
    new_monitoring_cap         = _canon["monitoring_capability"]
    knowledge_complexity_per_unit = _canon["knowledge_complexity_per_unit"]

    # ---- 2. Population update ----------------------------------------------
    new_population      = population * (1.0 + population_growth_rate)
    new_workforce_size  = new_population * workforce_frac

    # Auto-compute care stipend from demographics when caller does not supply one.
    if care_stipend_aggregate is None:
        from hours_eoh.core.fiscal import aggregate_care_stipend_from_demographics as _agg_care
        care_stipend_aggregate = _agg_care(new_population, eps)

    # ---- 3. Capital dynamics -----------------------------------------------
    new_cap_age    = min(1.0, cap_age + capital_aging_rate)
    new_cap_stock  = cap_stock * (1.0 + capital_investment_rate)

    # ---- 4. Ecological dynamics --------------------------------------------
    net_eco_change = ecological_restoration_rate - ecological_degradation_rate
    new_eco_health = max(0.01, min(1.0, eco_health + net_eco_change))

    # Deferred EOH grows when ecosystem is stressed (below 0.5)
    eco_stress    = max(0.0, 0.5 - new_eco_health)  # 0 above threshold, >0 below
    new_deferred  = deferred_eco * (1.0 + deferred_eco_growth_rate * eco_stress * 2.0)

    # new-11: When restoration effort is active, reduce the deferred ecological
    # backlog proportionally. Restoration rate represents fractional paydown of
    # accumulated obligations — regenerative labor directly reduces the backlog.
    if ecological_restoration_rate > 0.0 and new_deferred > 0.0:
        from hours_eoh.core.eoh_dynamics import update_deferred_from_fulfillment as _udf
        eco_fulfilled = new_deferred * ecological_restoration_rate
        new_deferred  = _udf(new_deferred, eco_fulfilled)["new_deferred"]

    # ---- 5. EOH → TEH pipeline ---------------------------------------------
    # new-5: Compute infrastructure compounding EOH from the deferred backlog.
    # This makes deferred-maintenance compounding live demand in the EOH ledger
    # (not just a dashboard warning).
    if deferred_infra > 0.0 and infra_def_years > 0.0:
        from hours_eoh.core.eoh_dynamics import eoh_compounding as _eoh_comp
        infra_compounding_eoh = _eoh_comp(deferred_infra, "generic_infra", infra_def_years, eps)
    else:
        infra_compounding_eoh = 0.0

    pipeline = eoh_to_teh_pipeline(
        epsilon=eps,
        population=new_population,
        capital_stock=new_cap_stock,
        capital_age_ratio=new_cap_age,
        ecosystem_health=new_eco_health,
        deferred_ecological=new_deferred,
        knowledge_complexity=know_complexity,
        capital_eoh_eliminated=cap_eoh_elim,
        capital_personal_eoh_fulfilled=cap_pers_fulfil,
        infrastructure_compounding_eoh=infra_compounding_eoh,
        monitoring_capability=new_monitoring_cap,
        knowledge_complexity_per_unit=knowledge_complexity_per_unit,
        mean_multiplier=mean_multiplier,
    )

    # Condition III-B: credit compounding fulfillment against the deferred backlog.
    # The pipeline created TEH for the human-fulfilled portion of infra_compounding_eoh.
    # The physical obligation must decrease by the same amount — otherwise the backlog
    # persists at full size while generating income each period, which is economically
    # equivalent to interest on an idle balance (violating the spirit of Condition III).
    new_deferred_infra = deferred_infra
    if infra_compounding_eoh > 0.0 and new_deferred_infra > 0.0:
        from hours_eoh.core.registration import total_registration_share as _infra_reg
        _infra_reg_share = _infra_reg(eps)
        human_compounding_fulfilled = infra_compounding_eoh * (1.0 - eps) * _infra_reg_share
        new_deferred_infra = max(0.0, new_deferred_infra - human_compounding_fulfilled)

    # new-5: Advance infrastructure deferred state.
    # Deferred years reset to zero when the backlog is fully cleared; otherwise increment.
    new_infra_def_years = 0.0 if new_deferred_infra == 0.0 else infra_def_years + 1.0
    teh_this_period = pipeline["teh_created"]

    # Labor income = TEH created this period (what registered human workers earned).
    # At ε=0: full teh_created; at ε=0.99: teh_created approaches zero as human_eoh_share
    # collapses. This is physics-derived, not a geometric decay formula.
    # labor_income_scale overrides for scenario testing (e.g., income-shock stress tests).
    labor_income = labor_income_scale if labor_income_scale is not None else teh_this_period
    labor_income = max(LABOR_INCOME_MIN_TEH, labor_income)

    # Per-person personal EOH fulfilled (for guarantee reduction)
    cap_per_person = cap_pers_fulfil / max(new_population, 1.0)

    # ---- 6. Fiscal pipeline ------------------------------------------------
    fiscal = fiscal_snapshot(
        trust_balance=trust_bal,
        labor_income=labor_income,
        capital_stock_teh=new_cap_stock,
        capital_age_ratio=new_cap_age,
        population=new_population,
        epsilon=eps,
        levy_rates=levy_rates,
        mean_multiplier=mean_multiplier,
        dep_rate=dep_rate,
        div_rate=div_rate,
        floor_fraction=floor_fraction,
        meaningful_activity_teh=meaningful_activity_teh,
        meaningful_activity_scale=meaningful_activity_scale,
        capital_personal_eoh_fulfilled_per_person=cap_per_person,
        capital_eoh_eliminated=cap_eoh_elim,
        ecosystem_health=new_eco_health,
        deferred_ecological=new_deferred,
        eco_eoh_override=pipeline["eoh_by_domain"]["ecological"],
        care_stipend_aggregate=care_stipend_aggregate,
    )
    new_trust_bal = fiscal["trust"]["trust_end"]

    # ---- 7. TEH destruction — D1 capital accounting + D2/D3 consumption
    #         + D4 CPI delivery + D5 estate dissolution + D6 ceiling (opt-in)
    from hours_eoh.core.prices import basket_price as _basket_price, cpi_goods_destruction as _cpi_dest
    from hours_eoh.core.capital import estate_dissolution as _estate_diss
    from hours_eoh.core.fiscal import accumulation_ceiling_commitment as _acc_ceil

    # D1: Capital investment locks TEH into capital-embodied pool (not destroyed).
    #     Write-down destroys capital-embodied TEH when assets fail beyond recovery.
    investment_teh   = cap_stock * capital_investment_rate
    writedown_teh    = new_cap_stock * CAPITAL_FAILURE_RATE * (1.0 - CAPITAL_WRITEDOWN_MONITORING_SLOPE * eps)
    new_cap_embodied = max(0.0, cap_embodied + investment_teh - writedown_teh)

    # Terminal consumption — D2 (income-driven) or D3 (biology-anchored).
    if use_d3:
        from hours_eoh.core.registration import personal_eoh_registration_share as _pers_reg
        personal_eoh_total     = pipeline["eoh_by_domain"].get("personal", 0.0)
        pers_reg_share         = _pers_reg(eps)
        personal_eoh_on_ledger = personal_eoh_total * pers_reg_share
        baskets_consumed       = personal_eoh_on_ledger / max(basket_eoh_content, 1.0)
        consumption            = baskets_consumed * _basket_price(eps)
        consumption_rate_eff   = None
    else:
        period_income          = fiscal["levies"]["worker_net"] + fiscal["trust"]["dividend"]
        pp_ratio               = _basket_price(0.0) / max(_basket_price(eps), 1e-6)
        consumption_rate_eff   = base_consumption_rate / max(1.0, pp_ratio)
        consumption            = period_income * consumption_rate_eff
        personal_eoh_on_ledger = None
        baskets_consumed       = None

    # D4: CPI transaction-level destruction — TEH destroyed when capital
    #     delivers personal-EOH services at embedded labor price.
    if use_cpi_destruction:
        cap_personal_total = cap_pers_fulfil * population
        d4 = _cpi_dest(cap_personal_total, eps, basket_eoh_content)
    else:
        d4 = {"teh_destroyed": 0.0, "baskets_delivered": 0.0,
              "basket_price": _basket_price(eps), "mechanism": "D4_disabled"}

    # D5: Estate dissolution — TEH written down on death above personal reserve.
    #     Also levies a fraction to Trust (circulatory).
    #     Uses start-of-period circulating TEH as the estate proxy.
    current_total_supply = teh_endowment + teh_created_cum - teh_destr_cum
    current_circ_approx  = max(0.0, current_total_supply - state["trust_balance"] - cap_embodied)
    if use_estate_dissolution:
        d5 = _estate_diss(
            current_circ_approx, population, eps,
            inheritance_fraction=estate_inheritance_fraction,
            estate_levy_fraction=estate_levy_fraction,
            personal_reserve_years=estate_reserve_years,
        )
        new_trust_bal = new_trust_bal + d5["teh_levied_to_trust"]
    else:
        d5 = {"teh_destroyed": 0.0, "teh_levied_to_trust": 0.0,
              "teh_inherited": 0.0, "mechanism": "D5_disabled"}

    # D6: Accumulation ceiling (disabled by default) — excess above ceiling
    #     committed to capital formation (moves to capital_embodied, not destroyed yet).
    if use_accumulation_ceiling:
        d6 = _acc_ceil(current_circ_approx, population,
                       ceiling_multiplier=accumulation_ceiling_multiplier)
        new_cap_embodied = new_cap_embodied + d6["teh_committed_to_capital"]
    else:
        d6 = {"teh_committed_to_capital": 0.0, "mechanism": "D6_disabled"}

    teh_dest_this = consumption + writedown_teh + d4["teh_destroyed"] + d5["teh_destroyed"]
    new_teh_created_cum = teh_created_cum + teh_this_period
    new_teh_destr_cum   = teh_destr_cum   + teh_dest_this

    # D1: True circulating TEH = total supply minus institutional reserves.
    # teh_endowment is the pre-simulation wealth (Trust seed + initial capital);
    # it anchors the ledger so the Trust and capital are excluded from circulation.
    # Negative values are valid: institutional reserves exceed simulation-era supply
    # (i.e., the Trust holds more pre-simulation wealth than new TEH has been created
    # and not yet destroyed). This is the correct state in early high-ε runs.
    total_supply = teh_endowment + new_teh_created_cum - new_teh_destr_cum
    teh_in_circ  = total_supply - new_trust_bal - new_cap_embodied

    # new-10: Evolve knowledge complexity (knowledge base size) each period.
    new_know_complexity = know_complexity * (1.0 + knowledge_complexity_growth_rate)

    # ---- 8. Build new state ------------------------------------------------
    new_state = make_economy_state(
        epsilon=eps,
        population=new_population,
        workforce_fraction=workforce_frac,
        trust_balance=new_trust_bal,
        labor_income_teh=labor_income,
        capital_stock_teh=new_cap_stock,
        capital_age_ratio=new_cap_age,
        ecosystem_health=new_eco_health,
        deferred_ecological=new_deferred,
        knowledge_complexity=new_know_complexity,
        teh_created_cumulative=new_teh_created_cum,
        teh_destroyed_cumulative=new_teh_destr_cum,
        capital_eoh_eliminated=cap_eoh_elim,
        capital_personal_eoh_fulfilled=cap_pers_fulfil,
        capital_embodied_teh=new_cap_embodied,
        teh_endowment=teh_endowment,   # preserved: endowment is fixed at simulation start
        period=state["period"] + 1,
        monitoring_capability=new_monitoring_cap,
        deferred_infrastructure_eoh=new_deferred_infra,
        infra_deferred_years=new_infra_def_years,
    )

    # derived_epsilon: architecture hook for when machine capacity is modeled endogenously.
    # compute_epsilon(machine_eoh, total_eoh) will produce a non-trivial value once a
    # machine_capacity sub-model tracks actual automated fulfillment. Until then the
    # result is always eps (machine_eoh = total × eps → derived = eps), so skip the call.
    derived_epsilon = eps

    period_result = {
        "period":            state["period"],
        "epsilon":           eps,
        "derived_epsilon":   derived_epsilon,   # ε as physical progress score (currently = eps)
        # EOH
        "total_eoh":         pipeline["total_eoh"],
        "human_eoh":         pipeline["human_eoh"],
        "registered_eoh":    pipeline["registered_eoh"],
        "registration_share": pipeline["registration_share"],
        "eoh_by_domain":     pipeline["eoh_by_domain"],
        "human_eoh_by_domain": {
            k: v for k, v in
            human_eoh_per_domain(pipeline["eoh_by_domain"], eps).items()
            if k not in ("total", "human_fraction", "epsilon")
        },
        # TEH
        "teh_created":       teh_this_period,
        "teh_destroyed":     teh_dest_this,
        "teh_net":           teh_this_period - teh_dest_this,
        "labor_income":      labor_income,
        # TEH lifecycle (D1 + D2/D3 + D4 + D5 + D6)
        "teh_total_supply":           total_supply,           # gross: endowment + created - destroyed
        "teh_in_circulation":         teh_in_circ,            # net: excludes Trust + capital-embodied
        "capital_embodied_teh":       new_cap_embodied,       # TEH locked in capital assets
        "investment_teh":             investment_teh,          # TEH moved into capital this period
        "consumption_rate_effective": consumption_rate_eff,    # D2 endogenous rate (None when D3 active)
        # D3 biology-anchored consumption fields (None when D2 active)
        "personal_eoh_on_ledger":     personal_eoh_on_ledger, # D3: personal EOH demand on collective ledger
        "baskets_consumed":           baskets_consumed,        # D3: sufficiency baskets consumed this period
        # D4: CPI transaction-level destruction
        "d4_cpi":                     d4,
        # D5: Estate dissolution on death
        "d5_estate":                  d5,
        # D6: Accumulation ceiling capital commitment
        "d6_ceiling":                 d6,
        # Fiscal
        "fiscal":            fiscal,
        "trust_start":       trust_bal,
        "trust_end":         new_trust_bal,
        "solvent":           fiscal["solvent"],
        # Population / capital
        "population":        new_population,
        "capital_stock_teh": new_cap_stock,
        "capital_age_ratio": new_cap_age,
        "ecosystem_health":  new_eco_health,
        "deferred_ecological": new_deferred,
        # new-2/new-5: physical state tracking
        "monitoring_capability":         new_monitoring_cap,
        "knowledge_complexity_per_unit": knowledge_complexity_per_unit,
        "deferred_infrastructure_eoh":   new_deferred_infra,
        "infra_deferred_years":          new_infra_def_years,
        "infra_compounding_eoh":         infra_compounding_eoh,
    }

    return new_state, period_result


# ---------------------------------------------------------------------------
# Multi-period run helper
# ---------------------------------------------------------------------------

def run_simulation(
    initial_state: dict,
    n_periods: int = 20,
    **simulate_kwargs,
) -> dict:
    """
    Run simulate_period() for n_periods and return the full trajectory.

    Args:
        initial_state: Starting state from make_economy_state().
        n_periods: Number of periods to simulate.
        **simulate_kwargs: Keyword arguments forwarded to simulate_period()
                           (e.g., population_growth_rate, epsilon_delta, etc.)

    Returns:
        dict: {
          "states":          list[dict],   (state after each period)
          "period_results":  list[dict],   (full period_result for each period)
          "final_state":     dict,
          "solvent_all":     bool,         (True if solvent every period)
          "first_insolvency": int | None,  (first period number with insolvency)
          "summary": {
            "epsilon_range":       [float, float],
            "trust_balance_range": [float, float],
            "total_teh_created":   float,
            "total_teh_destroyed": float,
          },
        }
    """
    state    = initial_state
    states: list[dict]         = []
    results: list[dict]        = []
    first_insolvency: int | None = None

    for _ in range(n_periods):
        new_state, period_result = simulate_period(state, **simulate_kwargs)
        states.append(new_state)
        results.append(period_result)

        if not period_result["solvent"] and first_insolvency is None:
            first_insolvency = period_result["period"]

        state = new_state

    final = states[-1] if states else initial_state
    eps_values    = [r["epsilon"] for r in results]
    trust_values  = [r["trust_end"] for r in results]

    return {
        "states":           states,
        "period_results":   results,
        "final_state":      final,
        "solvent_all":      first_insolvency is None,
        "first_insolvency": first_insolvency,
        "summary": {
            "epsilon_range":       [min(eps_values), max(eps_values)],
            "trust_balance_range": [min(trust_values), max(trust_values)],
            "total_teh_created":   final["teh_created_cumulative"],
            "total_teh_destroyed": final["teh_destroyed_cumulative"],
        },
    }
