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
    ECOLOGICAL_BASE_RATE,
    ECOLOGICAL_THRESHOLD,
    DEP_RATE,
    DIV_RATE,
    SUFF_LEVY_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    SHOCK_DEGRADED_TRUST_FRACTION,
)
from hours_eoh.core.eoh_generation import (
    ecological_eoh,
    resolve_capital_stock,
    resolve_knowledge_base_size,
)
from hours_eoh.core.fiscal import fiscal_snapshot, resolve_trust_balance
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

# THE LEGACY LABOUR-INCOME PROXY — superseded as the DEFAULT 2026-09-30.
# `2.2e9 × (1 − 0.8ε)`, floored at 3e8, was the levy base in three shocks. It is
# ~81× the mint at ε=0 and ~4.4× at ε=0.40, ignores the population frame, and
# contradicts the wage doctrine (minted TEH IS the wage, 2026-09-15). The
# default is now the pipeline's mint (`_mint_income`); a caller who passes
# `labor_income_base` to `demographic_shock` still gets the proxy formula, so
# pre-2026-09-30 figures reproduce. That is the ONLY reader of these three.
_LABOR_INCOME_BASE:       float = 2_200_000_000.0
_LABOR_INCOME_MIN:        float = 300_000_000.0
_LABOR_INCOME_AUTO_SLOPE: float = 0.80


def _classify(solvent: bool, surplus_deficit: float, trust_balance: float) -> str:
    """
    STABLE / DEGRADED / CRISIS from the Trust's position after a shock — the
    one reader of `SHOCK_DEGRADED_TRUST_FRACTION` (2026-09-30; three copies with
    two values before). DEGRADED: insolvent, but the deficit is at most that
    fraction of the balance, so the Trust carries it for ≥ 1/fraction periods.
    """
    if solvent:
        return "STABLE"
    if -surplus_deficit <= trust_balance * SHOCK_DEGRADED_TRUST_FRACTION:
        return "DEGRADED"
    return "CRISIS"


def _pipeline(
    epsilon: float,
    population: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    ecosystem_health: float = 0.70,
    knowledge_base_size: float | None = None,
    age_distribution: dict[str, float] | None = None,
) -> dict:
    """The shared EOH → TEH path at one state — every shock's EOH and mint."""
    return eoh_to_teh_pipeline(
        epsilon,
        population=population,
        age_distribution=age_distribution,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        knowledge_complexity=resolve_knowledge_base_size(knowledge_base_size, epsilon),
    )


def _mint_income(
    epsilon: float,
    population: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
) -> float:
    """Labour income under the wage doctrine: the period's mint, one frame."""
    return float(_pipeline(epsilon, population, capital_stock_teh,
                           capital_age_ratio)["teh_created"])


def _trust_position(
    epsilon: float,
    population: float,
    trust_balance: float,
    labor_income: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    meaningful_activity_teh: float,
    suff_levy_rate: float,
    dep_rate: float,
    div_rate: float,
    extra_obligation: float = 0.0,
) -> dict:
    """
    The Trust's position from `fiscal_snapshot` — the shared fiscal path — with
    a shock's added obligation charged against it.

    Until 2026-09-30 three shocks rebuilt levy → stewardship → guarantee → trust
    by hand (record/verification.md#parallel-paths (a)); every defect found in
    them on 2026-09-30 sat in that hand-assembled part. The charge is exact,
    not an approximation: the Trust's revenue (levy + GUF + estate + dividend)
    does not depend on what it owes, so adding X to the guarantee lowers
    `surplus_deficit` by exactly X — bound by test.

    NOTE, NOT RESOLVED HERE: the shocks pass their added obligation in EOH
    HOURS and it is charged as TEH one-for-one. That conversion is the shocks'
    pre-existing convention, not a property of `fiscal_snapshot`, which is why
    it stays out of the core signature.
    """
    snap = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=labor_income,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        meaningful_activity_teh=meaningful_activity_teh,
        levy_rates={"sufficiency": suff_levy_rate},
        dep_rate=dep_rate,
        div_rate=div_rate,
    )
    surplus = snap["trust"]["surplus_deficit"] - extra_obligation
    return {
        "solvent":         surplus >= 0.0,
        "surplus_deficit": surplus,
        "guarantee":       snap["guarantee"]["total_cost_teh"],
        "snapshot":        snap,
    }

_SEVERITY:     dict[str, int] = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
_INV_SEVERITY: dict[int, str] = {0: "STABLE", 1: "DEGRADED", 2: "CRISIS"}


# ---------------------------------------------------------------------------
# Automation Failure Shock
# ---------------------------------------------------------------------------

def _failure_pair(
    epsilon: float,
    fraction_lost: float,
    population: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    ecosystem_health: float,
    knowledge_base_size: float | None,
    available_labor_eoh: float,
) -> tuple[dict, dict]:
    """
    The pipeline before and after machines lose `fraction_lost` of their
    capability, at ONE physical state and ONE register.

    The capability falls to ε·(1 − fraction_lost); everything else — the
    obligation's physical state and the register's maturity
    (`registration_epsilon`) — stays at ε. Both runs are capped at the same
    labour supply, so whatever humans cannot take up is DEFERRED by the
    pipeline's own survival-first rationing, not re-derived here.
    """
    from hours_eoh.core.trajectory import canonical_physical_state
    state = canonical_physical_state(epsilon)
    # The frame (population, capital) is passed by keyword at each call so the
    # capital-frame gate can see it; the rest of the shared state is common.
    common = dict(
        age_distribution=state["age_distribution"],
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        knowledge_complexity=resolve_knowledge_base_size(knowledge_base_size, epsilon),
        monitoring_capability=state["monitoring_capability"],
        knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        available_labor_eoh=available_labor_eoh,
        registration_epsilon=epsilon,
    )
    before = eoh_to_teh_pipeline(
        machine_capability=epsilon, population=population,
        capital_stock=capital_stock_teh, **common)
    after = eoh_to_teh_pipeline(
        machine_capability=epsilon * (1.0 - fraction_lost), population=population,
        capital_stock=capital_stock_teh, **common)
    return before, after


def automation_failure_shock(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
    knowledge_base_size: float | None = None,
    workforce_size: float | None = None,
    mean_entropy_reduction_capacity: float | None = None,
    reserve_fraction: float | None = None,
    fraction_lost: float = 1.0,
    labor_supply_per_capita: float | None = None,
    trust_balance: float | None = None,
) -> dict:
    """
    Sudden loss of machine capability: what falls to people, what they can
    take up, and what is deferred (rebuilt 2026-09-30).

    THE CASCADE, every step the shared pipeline's own:

        lost      = observed machine load before − after
                    (total − human EOH: what machines ACTUALLY carried; the
                    labour care's automation floor keeps human was never theirs
                    to drop)
        demand    → humans, capped at the labour supply L
                    (`feasibility.labor_supply_per_capita` × population — the
                    one settled account of L)
        shortfall → DEFERRED, survival-first: personal obligation is served
                    before any other domain, so `deferred_personal > 0` means
                    the survival floor itself is unmet. With no labour at all
                    nothing is served and there is no collective.

    The register stands through the failure (`registration_epsilon`), so the
    surge labour is registered and MINTS — the wage doctrine (2026-09-15),
    bounded by the hours actually served. Nothing is charged to the Trust:
    a Trust balance cannot supply an hour of labour, so a labour shortfall is
    reported as deferral, never priced as a TEH cost. The Trust's position
    after the shock is reported from `fiscal_snapshot` at the new mint.

    WHAT IT DOES NOT MODEL, declared: COMPETENCY. Condition IV exists because
    untrained hours cannot run a water plant, and its threshold is per
    ESSENTIAL domain — which has no mapping onto the four EOH domains, so the
    shock cannot test it. Hours coverage is an UPPER bound on what a collective
    can absorb. Nor the repair obligation the failed machines leave, nor more
    than one period (deferral compounds; see `scenarios/recovery`).

    Args:
        epsilon: Machine capability before the failure [0.0, 0.99].
        population: Total population.
        capital_stock_teh: None → the canonical arc's stock at this ε and
            population; a supplied stock is the ACTUAL stock and held fixed.
        capital_age_ratio: Mean asset age ratio.
        ecosystem_health: Ecological health [0,1].
        knowledge_base_size: None → resolved along the arc.
        workforce_size, mean_entropy_reduction_capacity, reserve_fraction:
            DEPRECATED 2026-09-30, ignored with a warning. The old reading
            covered the machine load with a reserve of 15.5% × 600,000 workers
            × 1,200 h plus everyone at H_MIN — three literals, one copying a
            per-domain constant as a whole-workforce share — and ignored the
            hours the population can actually supply.
        fraction_lost: Share of machine capability lost (0, 1]. Default 1.
        labor_supply_per_capita: L in h/person·yr. None → the measured default.
        trust_balance: None → resolved at `population`.

    Returns:
        dict with "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"}: STABLE when the
        lost load is fully taken up, DEGRADED when some is deferred but the
        survival floor is served, CRISIS when personal obligation is deferred.
    """
    import warnings
    from hours_eoh.scenarios.feasibility import (
        labor_supply_per_capita as _measured_supply)
    from hours_eoh.core.prices import basket_price

    for name, value in (("workforce_size", workforce_size),
                        ("mean_entropy_reduction_capacity", mean_entropy_reduction_capacity),
                        ("reserve_fraction", reserve_fraction)):
        if value is not None:
            warnings.warn(
                f"automation_failure_shock({name}=) is deprecated (2026-09-30) and "
                "ignored: the take-up is bounded by the measured labour supply "
                "(labor_supply_per_capita), not a reserve fraction.",
                DeprecationWarning, stacklevel=2,
            )
    if not 0.0 < fraction_lost <= 1.0:
        raise ValueError(f"fraction_lost must be in (0, 1], got {fraction_lost}")

    supplied_capital = capital_stock_teh
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(supplied_capital, epsilon, population=population)
    trust_balance = resolve_trust_balance(trust_balance, population)
    L_pc = _measured_supply() if labor_supply_per_capita is None else labor_supply_per_capita
    L = L_pc * population

    before, after = _failure_pair(epsilon, fraction_lost, population, capital_stock_teh,
                                  capital_age_ratio, ecosystem_health,
                                  knowledge_base_size, L)
    total = float(before["total_eoh"])

    # Under a labour cap `human_eoh` is the hours SERVED; what humans could not
    # take up is in `deferred_total`. The machine load is what is left of the
    # obligation after both — `total − human_eoh` alone books the deferred
    # hours as if machines still carried them.
    def _machine(p: dict) -> float:
        return total - float(p["human_eoh"]) - float(p["deferred_total"])
    machine_before = _machine(before)
    machine_after = _machine(after)
    lost = machine_before - machine_after
    newly_deferred = float(after["deferred_total"]) - float(before["deferred_total"])
    taken_up = lost - newly_deferred
    coverage = taken_up / lost if lost > 0.0 else 1.0
    deferred_personal = float(after["deferred_personal"])

    if deferred_personal > 0.0:
        outcome = "CRISIS"
    elif newly_deferred > 0.0:
        outcome = "DEGRADED"
    else:
        outcome = "STABLE"

    # The FISCAL reading, at the failure's mint and the pre-failure ε (the
    # register the guarantee reads is the one the pipeline held).
    def _pos(p: dict) -> dict:
        return _trust_position(epsilon, population, trust_balance,
                               float(p["teh_created"]), capital_stock_teh,
                               capital_age_ratio, MEANINGFUL_ACTIVITY_TEH_BASE,
                               SUFF_LEVY_RATE, DEP_RATE, DIV_RATE)
    fiscal_before, fiscal_after = _pos(before), _pos(after)
    floor_before = basket_price(float(before["epsilon_observable"]), MEANINGFUL_ACTIVITY_TEH_BASE)
    floor_after = basket_price(float(after["epsilon_observable"]), MEANINGFUL_ACTIVITY_TEH_BASE)

    # The FAILURE BOUNDARY: the lowest capability on the arc from which this
    # failure can no longer be fully taken up, at this population and supply.
    failure_boundary = None
    if newly_deferred > 0.0:
        failure_boundary = epsilon
    else:
        for i in range(1, 20):
            test_eps = min(0.99, epsilon + i * 0.05)
            b, a = _failure_pair(
                test_eps, fraction_lost, population,
                resolve_capital_stock(supplied_capital, test_eps, population=population),
                capital_age_ratio, ecosystem_health, knowledge_base_size, L)
            if float(a["deferred_total"]) > float(b["deferred_total"]):
                failure_boundary = test_eps
                break
            if test_eps >= 0.99:
                break

    rec = (
        f"Automation failure at ε={epsilon:.2f} (capability lost {fraction_lost:.0%}): "
        f"{lost:,.0f} EOH/yr the machines carried falls to people; "
        f"{taken_up:,.0f} taken up within the labour supply ({coverage:.1%}), "
        f"{newly_deferred:,.0f} deferred"
        + (f", {deferred_personal:,.0f} of it PERSONAL — the survival floor is unmet"
           if deferred_personal > 0.0 else ", none of it personal")
        + f". Outcome: {outcome}. Competency (Condition IV) not tested: hours "
        "coverage is an upper bound."
    )

    return {
        "scenario":                "automation_failure_shock",
        "epsilon":                 epsilon,
        "fraction_lost":           fraction_lost,
        "total_eoh":               total,
        "machine_eoh_before":      machine_before,
        "machine_eoh_lost":        lost,
        "labor_supply_eoh":        L,
        "human_eoh_before":        float(before["human_eoh"]),
        "human_eoh_after":         float(after["human_eoh"]),
        "taken_up_eoh":            taken_up,
        "deferred_eoh":            newly_deferred,
        "deferred_personal_eoh":   deferred_personal,
        "coverage_ratio":          coverage,
        "covered":                 newly_deferred <= 0.0,
        "mint_before":             float(before["teh_created"]),
        "mint_after":              float(after["teh_created"]),
        "floor_price_before":      floor_before,
        "floor_price_after":       floor_after,
        "trust_surplus_before":    fiscal_before["surplus_deficit"],
        "trust_surplus_after":     fiscal_after["surplus_deficit"],
        "trust_solvent_after":     fiscal_after["solvent"],
        "competency_tested":       False,
        "outcome":                 outcome,
        "failure_boundary":        failure_boundary,
        "recommendation":          rec,
    }


# ---------------------------------------------------------------------------
# Demographic Shock
# ---------------------------------------------------------------------------

def demographic_shock(
    epsilon: float,
    shock_type: str,
    magnitude: float,
    trust_balance: float | None = None,
    labor_income_base: float | None = None,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = 0.30,
    population: float = 1_000_000.0,
) -> dict:
    """
    Simulate a sudden demographic change and assess fiscal/EOH impact.

    Shock types:
      "growth":  Sudden population increase (magnitude = fractional growth, e.g. 0.20 = +20%)
      "decline": Sudden population decrease (magnitude = fractional loss)
      "aging":   Shift in age distribution toward elderly (magnitude = fraction of
                 the WHOLE population that moves from working age to elderly)

    Args:
        epsilon: Automation level at time of shock.
        shock_type: One of "growth", "decline", "aging".
        magnitude: Fractional magnitude of the shock [0.0, 1.0].
        trust_balance: Trust balance at time of shock. None → resolved at
            `population`, like every other shock.
        labor_income_base: None (default) → labour income is the MINT at this
            ε for the pre-shock population (wage doctrine). Supplied → the
            legacy proxy `max(3e8, base × (1 − 0.8ε))`, kept so pre-2026-09-30
            figures reproduce.
        meaningful_activity_teh: Sufficiency floor TEH.
        suff_levy_rate: Levy rate.
        dep_rate: Trust depreciation rate.
        div_rate: Trust dividend fraction.
        capital_stock_teh: Capital stock.
        capital_age_ratio: Capital age ratio.
        population: Pre-shock population (2026-09-30). The shock was fixed at
            1M with a 1M-frame Trust default, and `compound_shock` handed it a
            Trust resolved at ITS population — a frame seam.

    Returns:
        dict with "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"} and "recommendation".
    """
    VALID = ("growth", "decline", "aging")
    if shock_type not in VALID:
        raise ValueError(f"shock_type must be one of {VALID}, got '{shock_type}'")
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError(f"magnitude must be in [0, 1], got {magnitude}")
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)

    # FRACTIONS, as `age_distribution` takes — head counts here squared the
    # population in personal EOH until 2026-09-30.
    base_fractions = {g: AGE_GROUPS[g]["fraction"] for g in AGE_GROUPS}
    if shock_type == "growth":
        new_population = population * (1.0 + magnitude)
        new_fractions  = dict(base_fractions)
    elif shock_type == "decline":
        new_population = population * (1.0 - magnitude)
        new_fractions  = dict(base_fractions)
    else:  # aging: `magnitude` of the WHOLE population moves working age → elderly
        # REFUSED beyond the working-age share (2026-09-30): it added elderly
        # without removing workers, growing the population. A share of the
        # population cannot move out of a group smaller than it — no threshold
        # to choose, so no clamp to hide.
        if magnitude > base_fractions["working_age"]:
            raise ValueError(
                f"an aging shock moves people OUT of working age, which is "
                f"{base_fractions['working_age']:.0%} of the population; "
                f"magnitude {magnitude} exceeds it"
            )
        new_population = population
        new_fractions  = dict(base_fractions)
        new_fractions["working_age"] -= magnitude
        new_fractions["elderly"]     += magnitude

    base_eoh = float(_pipeline(epsilon, population, capital_stock_teh, capital_age_ratio,
                               age_distribution=base_fractions)["total_eoh"])
    new_eoh  = float(_pipeline(epsilon, new_population, capital_stock_teh, capital_age_ratio,
                               age_distribution=new_fractions)["total_eoh"])

    if labor_income_base is None:
        labor_income = _mint_income(epsilon, population, capital_stock_teh,
                                    capital_age_ratio)
    else:
        labor_income = max(
            _LABOR_INCOME_MIN,
            labor_income_base * (1.0 - epsilon * _LABOR_INCOME_AUTO_SLOPE),
        )

    # The shock is sudden: income, capital and the Trust are the pre-shock
    # ones; only the population the guarantee is owed to moves.
    def _position(pop: float) -> dict:
        return _trust_position(epsilon, pop, trust_balance, labor_income,
                               capital_stock_teh, capital_age_ratio,
                               meaningful_activity_teh, suff_levy_rate,
                               dep_rate, div_rate)
    before = _position(population)
    after  = _position(new_population)

    eoh_delta = new_eoh - base_eoh

    outcome = _classify(after["solvent"], after["surplus_deficit"], trust_balance)

    rec = (
        f"{shock_type.title()} shock of {magnitude:.0%} at ε={epsilon:.2f}: "
        f"population {population:.0f} → {new_population:.0f}. "
        f"EOH demand {'+' if eoh_delta >= 0 else ''}{eoh_delta:,.0f} h/yr. "
        f"Trust {'solvent' if after['solvent'] else 'INSOLVENT'}. "
        f"Outcome: {outcome}."
    )

    return {
        "scenario":             "demographic_shock",
        "shock_type":           shock_type,
        "magnitude":            magnitude,
        "epsilon":              epsilon,
        # REPORTED 2026-08-28 so the income's own response is observable.
        "labor_income":         labor_income,
        "population_before":    population,
        "population_after":     new_population,
        "eoh_before":           base_eoh,
        "eoh_after":            new_eoh,
        "eoh_delta":            eoh_delta,
        "guarantee_before":     before["guarantee"],
        "guarantee_after":      after["guarantee"],
        "trust_solvent_before": before["solvent"],
        "trust_solvent_after":  after["solvent"],
        "surplus_deficit_after": after["surplus_deficit"],
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
    trust_balance: float | None = None,
    labor_income: float | None = None,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    population: float = 1_000_000.0,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    capital_stock_teh: float | None = None,
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
        labor_income: Annual labour income. None (default) → the MINT at this ε
            and population (wage doctrine, 2026-09-30); it was the 2.2e9
            proxy, unscaled by population.
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
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    if labor_income is None:
        labor_income = _mint_income(epsilon, population, capital_stock_teh, capital_age_ratio)
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

    trust = _trust_position(epsilon, population, trust_balance, labor_income,
                            capital_stock_teh, capital_age_ratio,
                            meaningful_activity_teh, suff_levy_rate,
                            dep_rate, div_rate, extra_obligation=eoh_spike)
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
        "labor_income":          labor_income,   # the levy base used (2026-09-30)
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
    trust_balance: float | None = None,
    population: float = 1_000_000.0,
    capital_stock_teh: float | None = None,
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
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    if not 0.0 <= income_fraction <= 1.0:
        raise ValueError(f"income_fraction must be in [0, 1], got {income_fraction}")

    # THE MINT, UNFLOORED (2026-09-30). Both incomes were floored at the legacy
    # proxy's 3e8 — frameless, so at 100k people the "baseline" was 110× the
    # mint at ε=0, and `income_fraction=0.0` ("total income collapse") never
    # reached zero income. The floor was retired on 2026-09-30
    # (record/fulfilment.md#floor-guard-and-shock-threshold); this copy
    # survived it. The mint is now read at the SAME capital the snapshot sizes.
    baseline_income = _mint_income(epsilon, population, capital_stock_teh, capital_age_ratio)
    shocked_income  = baseline_income * income_fraction

    def _position(income: float) -> dict:
        return _trust_position(epsilon, population, trust_balance, income,
                               capital_stock_teh, capital_age_ratio,
                               meaningful_activity_teh, suff_levy_rate,
                               dep_rate, div_rate)
    snap_before = _position(baseline_income)
    snap_after  = _position(shocked_income)

    surplus_before = snap_before["surplus_deficit"]
    surplus_after  = snap_after["surplus_deficit"]
    delta          = surplus_after - surplus_before

    outcome = _classify(snap_after["solvent"], surplus_after, trust_balance)

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
    trust_balance: float | None = None,
    population: float = 1_000_000.0,
    capital_stock_teh: float | None = None,
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
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    individual_outcomes: dict = {}
    combined_eoh_delta: float = 0.0

    # The MINT (2026-09-30). This was the 2.2e9 proxy at this ε, and it was then
    # passed to `demographic_shock` as `labor_income_base` — an ε=0 base — which
    # applied the (1 − 0.8ε) slope a SECOND time (failure mode 11). Every leg
    # now runs at THIS population (the demographic leg was frameless at 1M
    # until 2026-09-30) and resolves the same mint.
    labor_income = _mint_income(epsilon, population, capital_stock_teh, capital_age_ratio)

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
            meaningful_activity_teh=meaningful_activity_teh,
            suff_levy_rate=suff_levy_rate,
            dep_rate=dep_rate,
            div_rate=div_rate,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            population=population,
        )
        individual_outcomes["demographic_shock"] = dem_result["outcome"]
        combined_eoh_delta += max(0.0, dem_result["eoh_delta"])

    # --- Automation failure shock ----------------------------------------
    automation_deferred: float = 0.0
    if automation_fraction_lost > 0.0:
        auto_result = automation_failure_shock(
            epsilon=epsilon,
            population=population,
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            fraction_lost=automation_fraction_lost,
            trust_balance=trust_balance,
        )
        individual_outcomes["automation_failure_shock"] = auto_result["outcome"]
        # NOT charged to the Trust (2026-09-30). This added the machine load
        # × fraction lost to the guarantee — EOH hours as TEH — so the Trust
        # "paid" for labour nobody was available to do. What the failure leaves
        # is DEFERRED obligation, reported; its severity enters through the
        # leg's outcome. The other two legs keep the charge pending the author.
        automation_deferred = auto_result["deferred_eoh"]

    # --- Combined fiscal check -------------------------------------------
    trust = _trust_position(epsilon, population, trust_balance, labor_income,
                            capital_stock_teh, capital_age_ratio,
                            meaningful_activity_teh, suff_levy_rate,
                            dep_rate, div_rate, extra_obligation=combined_eoh_delta)
    trust_absorbs = trust["solvent"]

    # Combined outcome >= worst individual outcome
    worst_individual = max(
        (_SEVERITY.get(v, 0) for v in individual_outcomes.values()),
        default=0,
    )
    combined_severity = max(
        worst_individual,
        _SEVERITY[_classify(trust_absorbs, trust["surplus_deficit"], trust_balance)],
    )

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
        "automation_deferred_eoh": automation_deferred,
        "trust_absorbs_combined": trust_absorbs,
        "combined_outcome":       combined_outcome,
        "recommendation":         rec,
    }
