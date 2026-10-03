"""
scenarios/shocks — Sudden-onset shock scenarios.

  automation_failure_shock  — machines lose capability; the register stands
  demographic_shock         — population growth, decline or aging
  ecological_eoh_spike      — ecosystem collapse and the restoration it leaves
  labor_income_shock        — the mint falls
  compound_shock            — any of the first three, applied to ONE state

Each returns "outcome" ∈ {"STABLE", "DEGRADED", "CRISIS"} and a
"recommendation".

ONE STATE, ONE CASCADE (2026-10-01, author: "if the machines are no longer
doing the work then it falls back to human labor, if there is not enough human
labor it falls to deferred"). A shock is a change to one state — machine
capability, population and age mix, ecosystem health and the restoration it
leaves — and its consequence is read from the shared pipeline run before and
after, capped at the labour supply the population can actually give
(`feasibility.labor_supply_per_capita`, moving with the age mix):

    added human demand → taken up within the labour supply
                       → the rest DEFERRED, survival-first: personal
                         obligation is served before any other domain, so
                         `deferred_personal_eoh > 0` is the survival floor
                         itself unmet. No labour, no collective.

NOTHING IS CHARGED TO THE TRUST. A balance cannot supply an hour of labour, so
a labour shortfall is deferral, never a TEH cost; the work that IS done
registers and mints (the wage doctrine). The Trust's real obligation — the
sufficiency guarantee — is read from `fiscal_snapshot` at the after-state, with
the register held at its pre-shock level (`registration_epsilon`: the register
is what the collective carries, the capability how much human labour carries
it — author, 2026-10-01).

THE OUTCOME is the worse of the labour reading (STABLE: all taken up;
DEGRADED: some deferred; CRISIS: personal deferred) and the fiscal reading
(`_classify` on the Trust after the shock).

Mission Statement: §"Automation failure — the reserve must cover critical
infrastructure EOH"; §"Demographic shock"; §"Ecological EOH spike"
"""

from __future__ import annotations

import warnings
from typing import Any, TypedDict

from hours_eoh.data import (
    EPSILON_ARC_MAX,
    CANONICAL_CAPITAL_AGE_BASE,
    REFERENCE_FRAME_POPULATION,
    ECOSYSTEM_HEALTH_DEFAULT,
    AGE_GROUPS,
    ECOLOGICAL_THRESHOLD,
    COMPETENCY_THRESHOLD,
    DEP_RATE,
    DIV_RATE,
    ESSENTIAL_DOMAINS,
    LAND_HECTARES_PER_CAPITA,
    SUFF_LEVY_RATE,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    SHOCK_DEGRADED_TRUST_FRACTION,
)
from hours_eoh.core.eoh_generation import (
    resolve_capital_stock,
    resolve_knowledge_base_size,
)
from hours_eoh.core.conditions import condition_iv_coverage
from hours_eoh.core.fiscal import fiscal_snapshot, resolve_trust_balance
from hours_eoh.core.workforce import competency_reserve
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.prices import basket_price
from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.scenarios.feasibility import (
    capacity_weighted_adult_share,
    labor_supply_per_capita as _measured_supply,
)
from hours_eoh.scenarios.restoration_cost import (
    DEFAULT_AMORTIZATION_YEARS,
    pristine_gap_obligation,
)

# THE LEGACY LABOUR-INCOME PROXY — superseded as the DEFAULT 2026-09-30.
# `2.2e9 × (1 − 0.8ε)`, floored at 3e8. The ONLY reader is `demographic_shock`
# when a caller passes `labor_income_base`, so pre-2026-09-30 figures reproduce.
_LABOR_INCOME_BASE:       float = 2_200_000_000.0
_LABOR_INCOME_MIN:        float = 300_000_000.0
_LABOR_INCOME_AUTO_SLOPE: float = 0.80

_SEVERITY:     dict[str, int] = {"STABLE": 0, "DEGRADED": 1, "CRISIS": 2}
_INV_SEVERITY: dict[int, str] = {0: "STABLE", 1: "DEGRADED", 2: "CRISIS"}


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


def _worse(*outcomes: str) -> str:
    return _INV_SEVERITY[max(_SEVERITY[o] for o in outcomes)]


def _pipeline(
    epsilon: float,
    population: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    ecosystem_health: float = ECOSYSTEM_HEALTH_DEFAULT,
    knowledge_base_size: float | None = None,
    age_distribution: dict[str, float] | None = None,
) -> dict:
    """The shared EOH → TEH path at one unshocked state."""
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
    registration_epsilon: float | None = None,
    ecosystem_health: float = ECOSYSTEM_HEALTH_DEFAULT,
) -> dict:
    """
    The Trust's position from `fiscal_snapshot`, the shared fiscal path.

    Until 2026-09-30 three shocks rebuilt levy → stewardship → guarantee →
    trust by hand; until 2026-10-01 they then charged their added EOH against
    the result as TEH. Neither remains: nothing is charged, and the guarantee
    reads the register at `registration_epsilon` while the capability is
    `epsilon`.
    """
    snap = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=labor_income,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        ecosystem_health=ecosystem_health,
        meaningful_activity_teh=meaningful_activity_teh,
        levy_rates={"sufficiency": suff_levy_rate},
        dep_rate=dep_rate,
        div_rate=div_rate,
        registration_epsilon=registration_epsilon,
    )
    surplus = snap["trust"]["surplus_deficit"]
    return {
        "solvent":         snap["trust"]["solvent"],
        "surplus_deficit": surplus,
        "guarantee":       snap["guarantee"]["total_cost_teh"],
        "snapshot":        snap,
    }


# ---------------------------------------------------------------------------
# The state, the run, the cascade
# ---------------------------------------------------------------------------

class _State(TypedDict):
    capability: float                 # machine capability ε (what machines CAN take)
    population: float
    age_fractions: dict[str, float]
    ecosystem_health: float
    restoration_eoh: float            # annual restoration obligation, h/yr
    labor_supply_per_capita: float    # L, h/person·yr — moves with the age mix


def _base_fractions() -> dict[str, float]:
    return {g: AGE_GROUPS[g]["fraction"] for g in AGE_GROUPS}


def _base_state(
    epsilon: float,
    population: float,
    ecosystem_health: float,
    labor_supply_per_capita: float | None,
) -> _State:
    fractions = _base_fractions()
    supply = (_measured_supply(adult_share=capacity_weighted_adult_share(fractions))
              if labor_supply_per_capita is None else labor_supply_per_capita)
    return _State(capability=epsilon, population=population, age_fractions=fractions,
                  ecosystem_health=ecosystem_health, restoration_eoh=0.0,
                  labor_supply_per_capita=supply)


def _with_age_mix(state: _State, population: float, fractions: dict[str, float]) -> _State:
    """A new population and age mix; supply per head follows the adult share."""
    ratio = (capacity_weighted_adult_share(fractions)
             / capacity_weighted_adult_share(state["age_fractions"]))
    return _State(**{**state, "population": population, "age_fractions": fractions,
                     "labor_supply_per_capita": state["labor_supply_per_capita"] * ratio})


def _demographic_change(state: _State, shock_type: str, magnitude: float) -> _State:
    valid = ("growth", "decline", "aging")
    if shock_type not in valid:
        raise ValueError(f"shock_type must be one of {valid}, got '{shock_type}'")
    if not 0.0 <= magnitude <= 1.0:
        raise ValueError(f"magnitude must be in [0, 1], got {magnitude}")
    fractions = dict(state["age_fractions"])
    population = state["population"]
    if shock_type == "growth":
        population *= 1.0 + magnitude
    elif shock_type == "decline":
        population *= 1.0 - magnitude
    else:
        # `magnitude` of the WHOLE population moves working age → elderly.
        # REFUSED beyond the working-age share (2026-09-30): it added elderly
        # without removing workers. No threshold to choose, so no clamp.
        if magnitude > fractions["working_age"]:
            raise ValueError(
                f"an aging shock moves people OUT of working age, which is "
                f"{fractions['working_age']:.0%} of the population; "
                f"magnitude {magnitude} exceeds it"
            )
        fractions["working_age"] -= magnitude
        fractions["elderly"] += magnitude
    return _with_age_mix(state, population, fractions)


def _restoration(
    population: float,
    health_before: float,
    health_after: float,
    amortization_years: float,
    corner: str,
) -> float:
    """
    The annual restoration obligation a collapse leaves, h/yr —
    `restoration_cost.pristine_gap_obligation` on the frame's land.

    DECLARED BINDING: the deficit is the health LOST, `h_before − h_after`,
    uniformly over `population × LAND_HECTARES_PER_CAPITA`. Health and deficit
    share one scale (1 = reference condition, per both docstrings); the
    function refuses an invented deficit, and this one is the scenario's own
    input. Priced by the repo's measured field-operation sequences, which are
    machinery: what they do NOT price is biological recovery TIME.
    """
    deficit = max(0.0, health_before - health_after)
    if deficit == 0.0:
        return 0.0
    return float(pristine_gap_obligation(
        [{"class": "shock", "hectares": population * LAND_HECTARES_PER_CAPITA,
          "deficit": deficit}],
        amortization_years=amortization_years, corner=corner,
    )["annual_hours"])


def _run(
    state: _State,
    epsilon: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    knowledge_base_size: float | None,
    deferred_ecological: float = 0.0,
) -> dict:
    """
    The pipeline at `state`, the physical state and the REGISTER held at the
    pre-shock `epsilon`, capped at the state's labour supply.
    """
    phys = canonical_physical_state(epsilon)
    return eoh_to_teh_pipeline(
        machine_capability=state["capability"],
        registration_epsilon=epsilon,
        population=state["population"],
        capital_stock=capital_stock_teh,
        age_distribution=state["age_fractions"],
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=state["ecosystem_health"],
        knowledge_complexity=resolve_knowledge_base_size(knowledge_base_size, epsilon),
        monitoring_capability=phys["monitoring_capability"],
        knowledge_complexity_per_unit=phys["knowledge_complexity_per_unit"],
        restoration_obligation=state["restoration_eoh"],
        deferred_ecological=deferred_ecological,
        available_labor_eoh=state["labor_supply_per_capita"] * state["population"],
    )


def _cascade(before: dict, after: dict) -> dict:
    """
    What the shock asks of people, and what they can give.

    Under a labour cap `human_eoh` is the hours SERVED and `deferred_total` the
    rest, so human DEMAND is their sum and the machine load is what is left of
    the obligation — `total − human_eoh` alone books deferred hours as if
    machines still carried them.
    """
    def demand(p: dict) -> float:
        return float(p["human_eoh"]) + float(p["deferred_total"])

    added = demand(after) - demand(before)
    newly_deferred = float(after["deferred_total"]) - float(before["deferred_total"])
    deferred_personal = float(after["deferred_personal"])
    if deferred_personal > 0.0:
        labour = "CRISIS"
    elif newly_deferred > 0.0:
        labour = "DEGRADED"
    else:
        labour = "STABLE"
    return {
        "machine_eoh_before":    float(before["total_eoh"]) - demand(before),
        "machine_eoh_after":     float(after["total_eoh"]) - demand(after),
        "added_human_eoh":       added,
        "taken_up_eoh":          added - newly_deferred,
        "deferred_eoh":          newly_deferred,
        "deferred_personal_eoh": deferred_personal,
        "coverage_ratio":        (added - newly_deferred) / added if added > 0.0 else 1.0,
        "labour_outcome":        labour,
    }


def _threshold_reserve(state: _State) -> dict:
    """Certification at EXACTLY the Condition IV minimum — `COMPETENCY_THRESHOLD`
    of the state's working-age headcount: the conservative case."""
    workforce = state["population"] * state["age_fractions"]["working_age"]
    return competency_reserve(
        {d: workforce * COMPETENCY_THRESHOLD for d in ESSENTIAL_DOMAINS}, workforce)


def _competency(s0: _State, before: dict, s1: _State, after: dict) -> dict:
    """
    Condition IV in hours (`conditions.condition_iv_coverage`) before and after
    the shock, each state certified at the minimum of its OWN headcount — so an
    aging shock shrinks the certified pool as it shrinks supply. Two tiers
    (author, 2026-10-01: "the people (agent needs) should be what needs to be
    covered, the rest can build back over time as the arc climbs again"):

        PERSONAL tier — registered personal hours: a shortfall the shock
                        CREATES here is CRISIS, the survival floor without
                        competent hands;
        REGISTERED    — all registered hours: a created shortfall elsewhere is
                        DEGRADED, rebuildable.

    A shock is charged only with the shortfalls it CREATES: a domain already
    short before it (healthcare, over a band of the upper arc at the Condition
    IV minimum) is reported, not blamed on it.
    """
    def created(reading: str) -> tuple[list[str], list[str], dict]:
        c0 = condition_iv_coverage(_threshold_reserve(s0), before, reading)
        c1 = condition_iv_coverage(_threshold_reserve(s1), after, reading)
        return (c0["domains_short"],
                [d for d in c1["domains_short"] if d not in c0["domains_short"]], c1)

    short_before, made, c1 = created("registered")
    personal_before, personal_made, _ = created("personal")
    if personal_made:
        outcome = "CRISIS"
    elif made:
        outcome = "DEGRADED"
    else:
        outcome = "STABLE"
    return {
        "competency_tested":                True,
        "competency_short_before":          short_before,
        "competency_short_after":           c1["domains_short"],
        "competency_short_created":         made,
        "competency_personal_short_before": personal_before,
        "competency_personal_short_created": personal_made,
        "competency_coverage_after":        {d: v["coverage_ratio"] for d, v in c1["per_domain"].items()},
        "competency_unattributed_eoh":      c1["unattributed_eoh"],
        "competency_outcome":               outcome,
    }


def _fiscal(
    state: _State,
    epsilon: float,
    pipe: dict,
    trust_balance: float,
    capital_stock_teh: float,
    capital_age_ratio: float,
    labor_income: float | None = None,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
) -> dict:
    """The Trust at `state`: the state's mint (or a supplied income), the
    capability read as the state's, the register held at `epsilon`."""
    return _trust_position(
        state["capability"], state["population"], trust_balance,
        float(pipe["teh_created"]) if labor_income is None else labor_income,
        capital_stock_teh, capital_age_ratio, meaningful_activity_teh,
        suff_levy_rate, dep_rate, div_rate,
        registration_epsilon=epsilon, ecosystem_health=state["ecosystem_health"],
    )


def _deprecated(fn: str, **supplied: object) -> None:
    for name, value in supplied.items():
        if value is not None:
            warnings.warn(
                f"{fn}({name}=) is deprecated and ignored (see the docstring).",
                DeprecationWarning, stacklevel=3,
            )


# ---------------------------------------------------------------------------
# Automation Failure Shock
# ---------------------------------------------------------------------------

def automation_failure_shock(
    epsilon: float,
    population: float = REFERENCE_FRAME_POPULATION,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
    ecosystem_health: float = ECOSYSTEM_HEALTH_DEFAULT,
    knowledge_base_size: float | None = None,
    workforce_size: float | None = None,
    mean_entropy_reduction_capacity: float | None = None,
    reserve_fraction: float | None = None,
    fraction_lost: float = 1.0,
    labor_supply_per_capita: float | None = None,
    trust_balance: float | None = None,
) -> dict:
    """
    Machines lose `fraction_lost` of their capability; the register stands.

    The capability falls ε → ε·(1 − fraction_lost); the OBSERVED machine load
    lost falls to people (the labour care's automation floor keeps human was
    never the machines' to drop), is taken up within the labour supply, and the
    rest is deferred survival-first. See the module docstring for the cascade
    and the outcome rule.

    COMPETENCY (Condition IV) IS TESTED (2026-10-01): untrained hours cannot
    run a water plant, so the work taken up is also set against the people
    certified to do it, per essential domain (`conditions.condition_iv_coverage`
    at the Condition IV minimum, through the untagged essential-domain bridge).
    A shortfall the failure creates makes it DEGRADED. Not modelled: the
    repair the failed machines leave, or more than one period
    (`scenarios/recovery`).

    Args:
        epsilon: Machine capability before the failure [0.0, 0.99].
        population: Total population.
        capital_stock_teh: None → the canonical arc's stock at this ε and
            population; a supplied stock is the ACTUAL stock and held fixed.
        capital_age_ratio, ecosystem_health: Physical state.
        knowledge_base_size: None → resolved along the arc.
        workforce_size, mean_entropy_reduction_capacity, reserve_fraction:
            DEPRECATED 2026-09-30, ignored with a warning — three literals, one
            copying a per-domain constant as a whole-workforce share.
        fraction_lost: Share of machine capability lost (0, 1]. Default 1.
        labor_supply_per_capita: L in h/person·yr. None → the measured default.
        trust_balance: None → resolved at `population`.
    """
    _deprecated("automation_failure_shock", workforce_size=workforce_size,
                mean_entropy_reduction_capacity=mean_entropy_reduction_capacity,
                reserve_fraction=reserve_fraction)
    if not 0.0 < fraction_lost <= 1.0:
        raise ValueError(f"fraction_lost must be in (0, 1], got {fraction_lost}")
    supplied_capital = capital_stock_teh
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(supplied_capital, epsilon, population=population)
    trust_balance = resolve_trust_balance(trust_balance, population)

    def pair(eps: float, capital: float) -> tuple[_State, _State, dict, dict]:
        s0 = _base_state(eps, population, ecosystem_health, labor_supply_per_capita)
        s1 = _State(**{**s0, "capability": eps * (1.0 - fraction_lost)})
        return (s0, s1,
                _run(s0, eps, capital, capital_age_ratio, knowledge_base_size),
                _run(s1, eps, capital, capital_age_ratio, knowledge_base_size))

    s0, s1, before, after = pair(epsilon, capital_stock_teh)
    c = _cascade(before, after)
    f0 = _fiscal(s0, epsilon, before, trust_balance, capital_stock_teh, capital_age_ratio)
    f1 = _fiscal(s1, epsilon, after, trust_balance, capital_stock_teh, capital_age_ratio)
    comp = _competency(s0, before, s1, after)
    outcome = _worse(c["labour_outcome"], comp["competency_outcome"],
                     _classify(f1["solvent"], f1["surplus_deficit"], trust_balance))

    # The lowest capability on the arc from which this failure can no longer
    # be fully taken up, at this population and supply.
    failure_boundary = None
    if c["deferred_eoh"] > 0.0:
        failure_boundary = epsilon
    else:
        for i in range(1, 20):
            test_eps = min(EPSILON_ARC_MAX, epsilon + i * 0.05)
            _, _, b, a = pair(test_eps, resolve_capital_stock(
                supplied_capital, test_eps, population=population))
            if float(a["deferred_total"]) > float(b["deferred_total"]):
                failure_boundary = test_eps
                break
            if test_eps >= EPSILON_ARC_MAX:
                break

    lost = c["machine_eoh_before"] - c["machine_eoh_after"]
    rec = (
        f"Automation failure at ε={epsilon:.2f} (capability lost {fraction_lost:.0%}): "
        f"{lost:,.0f} EOH/yr the machines carried falls to people; "
        f"{c['taken_up_eoh']:,.0f} taken up within the labour supply "
        f"({c['coverage_ratio']:.1%}), {c['deferred_eoh']:,.0f} deferred"
        + (f", {c['deferred_personal_eoh']:,.0f} of it PERSONAL — the survival "
           "floor is unmet" if c["deferred_personal_eoh"] > 0.0 else ", none of it personal")
        + f". Trust {'solvent' if f1['solvent'] else 'INSOLVENT'} at the new mint. "
        + (f"Certified capacity falls short in {comp['competency_short_created']}. "
           if comp["competency_short_created"] else "")
        + f"Outcome: {outcome}."
    )
    return {
        "scenario":                "automation_failure_shock",
        "epsilon":                 epsilon,
        "fraction_lost":           fraction_lost,
        "total_eoh":               float(before["total_eoh"]),
        "machine_eoh_before":      c["machine_eoh_before"],
        "machine_eoh_lost":        lost,
        "labor_supply_eoh":        s0["labor_supply_per_capita"] * population,
        "human_eoh_before":        float(before["human_eoh"]),
        "human_eoh_after":         float(after["human_eoh"]),
        "taken_up_eoh":            c["taken_up_eoh"],
        "deferred_eoh":            c["deferred_eoh"],
        "deferred_personal_eoh":   c["deferred_personal_eoh"],
        "coverage_ratio":          c["coverage_ratio"],
        "covered":                 c["deferred_eoh"] <= 0.0,
        "mint_before":             float(before["teh_created"]),
        "mint_after":              float(after["teh_created"]),
        "floor_price_before":      basket_price(float(before["epsilon_observable"]),
                                                MEANINGFUL_ACTIVITY_TEH_BASE),
        "floor_price_after":       basket_price(float(after["epsilon_observable"]),
                                                MEANINGFUL_ACTIVITY_TEH_BASE),
        "trust_surplus_before":    f0["surplus_deficit"],
        "trust_surplus_after":     f1["surplus_deficit"],
        "trust_solvent_after":     f1["solvent"],
        **comp,
        "labour_outcome":          c["labour_outcome"],
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
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
    population: float = REFERENCE_FRAME_POPULATION,
    labor_supply_per_capita: float | None = None,
) -> dict:
    """
    A sudden change to the population: "growth" / "decline" (population ×
    (1 ± magnitude)) or "aging" (`magnitude` of the WHOLE population moves from
    working age to elderly; refused beyond the working-age share).

    SUPPLY MOVES WITH THE AGE MIX (2026-10-01). The labour supply per head
    follows `capacity_weighted_adult_share` of the new mix — an aging shock
    that raised demand and left supply untouched is what
    `capacity_weighted_adult_share`'s own docstring recorded. The after-state's
    mint is what the new population's work registers; the Trust owes the
    guarantee at the new population.

    Args:
        epsilon: Machine capability at the time of the shock.
        shock_type: "growth", "decline" or "aging".
        magnitude: Fractional magnitude [0, 1].
        trust_balance: None → resolved at `population`.
        labor_income_base: None (default) → the mint. Supplied → the legacy
            proxy `max(3e8, base × (1 − 0.8ε))` for BOTH fiscal readings, so
            pre-2026-09-30 figures reproduce.
        meaningful_activity_teh, suff_levy_rate, dep_rate, div_rate: Fiscal.
        capital_stock_teh, capital_age_ratio: Physical state.
        population: Pre-shock population.
        labor_supply_per_capita: Pre-shock L. None → the measured default.
    """
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    s0 = _base_state(epsilon, population, 0.70, labor_supply_per_capita)
    s1 = _demographic_change(s0, shock_type, magnitude)
    before = _run(s0, epsilon, capital_stock_teh, capital_age_ratio, None)
    after = _run(s1, epsilon, capital_stock_teh, capital_age_ratio, None)
    c = _cascade(before, after)

    proxy = (None if labor_income_base is None else max(
        _LABOR_INCOME_MIN, labor_income_base * (1.0 - epsilon * _LABOR_INCOME_AUTO_SLOPE)))
    kw = dict(meaningful_activity_teh=meaningful_activity_teh,
              suff_levy_rate=suff_levy_rate, dep_rate=dep_rate, div_rate=div_rate)
    f0 = _fiscal(s0, epsilon, before, trust_balance, capital_stock_teh,
                 capital_age_ratio, labor_income=proxy, **kw)
    f1 = _fiscal(s1, epsilon, after, trust_balance, capital_stock_teh,
                 capital_age_ratio, labor_income=proxy, **kw)
    comp = _competency(s0, before, s1, after)
    outcome = _worse(c["labour_outcome"], comp["competency_outcome"],
                     _classify(f1["solvent"], f1["surplus_deficit"], trust_balance))
    eoh_delta = float(after["total_eoh"]) - float(before["total_eoh"])
    rec = (
        f"{shock_type.title()} shock of {magnitude:.0%} at ε={epsilon:.2f}: "
        f"population {population:.0f} → {s1['population']:.0f}. "
        f"EOH demand {'+' if eoh_delta >= 0 else ''}{eoh_delta:,.0f} h/yr; "
        f"labour supply {s0['labor_supply_per_capita'] * population:,.0f} → "
        f"{s1['labor_supply_per_capita'] * s1['population']:,.0f} h/yr; "
        f"{c['deferred_eoh']:,.0f} deferred. "
        f"Trust {'solvent' if f1['solvent'] else 'INSOLVENT'}. Outcome: {outcome}."
    )
    return {
        "scenario":              "demographic_shock",
        "shock_type":            shock_type,
        "magnitude":             magnitude,
        "epsilon":               epsilon,
        # REPORTED 2026-08-28 so the income's own response is observable.
        "labor_income":          proxy if proxy is not None else float(before["teh_created"]),
        "labor_income_after":    proxy if proxy is not None else float(after["teh_created"]),
        "population_before":     population,
        "population_after":      s1["population"],
        "labor_supply_before":   s0["labor_supply_per_capita"] * population,
        "labor_supply_after":    s1["labor_supply_per_capita"] * s1["population"],
        "eoh_before":            float(before["total_eoh"]),
        "eoh_after":             float(after["total_eoh"]),
        "eoh_delta":             eoh_delta,
        "taken_up_eoh":          c["taken_up_eoh"],
        "deferred_eoh":          c["deferred_eoh"],
        "deferred_personal_eoh": c["deferred_personal_eoh"],
        "guarantee_before":      f0["guarantee"],
        "guarantee_after":       f1["guarantee"],
        "trust_solvent_before":  f0["solvent"],
        "trust_solvent_after":   f1["solvent"],
        "surplus_deficit_after": f1["surplus_deficit"],
        **comp,
        "labour_outcome":        c["labour_outcome"],
        "outcome":               outcome,
        "recommendation":        rec,
    }


# ---------------------------------------------------------------------------
# Ecological EOH Spike
# ---------------------------------------------------------------------------

def ecological_eoh_spike(
    epsilon: float,
    ecosystem_health_before: float,
    ecosystem_health_after: float,
    deferred_ecological_eoh: float = 0.0,
    base_rate: float | None = None,
    trust_balance: float | None = None,
    labor_income: float | None = None,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    population: float = REFERENCE_FRAME_POPULATION,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
    restoration_years: float = DEFAULT_AMORTIZATION_YEARS,
    restoration_corner: str = "high",
    labor_supply_per_capita: float | None = None,
) -> dict:
    """
    An ecosystem collapse: what it leaves to be done, and who can do it.

    THE SPIKE IS THE RESTORATION (2026-10-01). Under the adopted Phase 4e/4f
    partition the ecological domain is health-invariant — the recurring
    degradation response is the land holder's, through the GUF — so this
    shock, which read the domain, reported a spike of exactly 0 at every
    population and decided its verdict from the threshold flag alone. What a
    collapse leaves in the domain is a RESTORATION STOCK: the health lost,
    over the frame's land, priced by `pristine_gap_obligation` and amortised
    over `restoration_years`. It enters the pipeline as `restoration_obligation`
    and runs the cascade. The holder's added GUF flow is reported beside it in
    hours (`guf_flow_added_eoh`, from `fiscal_snapshot`) and is not cascaded —
    it is the GUF's to fund.

    WHAT IT DOES NOT MODEL: biological recovery TIME. The priced sequences are
    field operations; the record's own 12–69× biological-vs-engineered gap
    (`restoration_cost.implied_kappa`) bounds how far they understate.
    `threshold_crossed` is reported; it no longer sets the outcome on its own.

    Args:
        epsilon: Machine capability at the time of failure.
        ecosystem_health_before, ecosystem_health_after: Health ∈ [0, 1].
        deferred_ecological_eoh: A pre-existing deferred stock (intake).
        base_rate: DEPRECATED 2026-10-01, ignored — it set the whole-US anchor
            for a domain the partition has emptied.
        trust_balance: None → resolved at `population`.
        labor_income: None → the state's mint. Supplied → used for both
            fiscal readings.
        suff_levy_rate, dep_rate, div_rate, meaningful_activity_teh: Fiscal.
        population: Population; the land is population × LAND_HECTARES_PER_CAPITA.
        capital_stock_teh, capital_age_ratio: Physical state.
        restoration_years: Horizon the restoration stock is discharged over.
        restoration_corner: "high" (default, conservative) or "low" band corner;
            both are reported.
        labor_supply_per_capita: L. None → the measured default.
    """
    _deprecated("ecological_eoh_spike", base_rate=base_rate)
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    restoration = {corner: _restoration(population, ecosystem_health_before,
                                        ecosystem_health_after, restoration_years, corner)
                   for corner in ("low", "high")}
    s0 = _base_state(epsilon, population, ecosystem_health_before, labor_supply_per_capita)
    s1 = _State(**{**s0, "ecosystem_health": ecosystem_health_after,
                   "restoration_eoh": restoration[restoration_corner]})
    before = _run(s0, epsilon, capital_stock_teh, capital_age_ratio, None,
                  deferred_ecological=deferred_ecological_eoh)
    after = _run(s1, epsilon, capital_stock_teh, capital_age_ratio, None,
                 deferred_ecological=deferred_ecological_eoh)
    c = _cascade(before, after)
    f0 = _fiscal(s0, epsilon, before, trust_balance, capital_stock_teh, capital_age_ratio,
                 labor_income, meaningful_activity_teh, suff_levy_rate, dep_rate, div_rate)
    f1 = _fiscal(s1, epsilon, after, trust_balance, capital_stock_teh, capital_age_ratio,
                 labor_income, meaningful_activity_teh, suff_levy_rate, dep_rate, div_rate)
    guf_flow = (float(f1["snapshot"]["ecological"]["relocated_to_guf"])
                - float(f0["snapshot"]["ecological"]["relocated_to_guf"]))
    eoh_before = float(before["eoh_by_domain"]["ecological"])
    eoh_after = float(after["eoh_by_domain"]["ecological"])
    spike = max(0.0, eoh_after - eoh_before)
    crossed = ecosystem_health_before > ECOLOGICAL_THRESHOLD >= ecosystem_health_after
    comp = _competency(s0, before, s1, after)
    outcome = _worse(c["labour_outcome"], comp["competency_outcome"],
                     _classify(f1["solvent"], f1["surplus_deficit"], trust_balance))
    rec = (
        f"Health {ecosystem_health_before:.2f} → {ecosystem_health_after:.2f} "
        f"(threshold {ECOLOGICAL_THRESHOLD:.2f} {'crossed' if crossed else 'not crossed'}): "
        f"restoration {restoration['low']:,.0f}–{restoration['high']:,.0f} h/yr over "
        f"{restoration_years:.0f} years, of which people carry "
        f"{c['added_human_eoh']:,.0f} (machines the rest): {c['taken_up_eoh']:,.0f} "
        f"taken up, {c['deferred_eoh']:,.0f} deferred. The holder's GUF flow rises "
        f"{guf_flow:,.0f} h/yr. Outcome: {outcome}. Not modelled: biological "
        "recovery time."
    )
    return {
        "scenario":              "ecological_eoh_spike",
        "epsilon":               epsilon,
        "health_before":         ecosystem_health_before,
        "health_after":          ecosystem_health_after,
        "eoh_before":            eoh_before,
        "eoh_after":             eoh_after,
        "eoh_spike":             spike,
        # Share of the whole obligation (the domain is empty before a collapse
        # under the partition, so a ratio to it is undefined).
        "spike_ratio":           spike / float(before["total_eoh"]),
        "restoration_eoh_low":   restoration["low"],
        "restoration_eoh_high":  restoration["high"],
        "guf_flow_added_eoh":    guf_flow,
        "threshold_crossed":     crossed,
        "added_human_eoh":       c["added_human_eoh"],
        "taken_up_eoh":          c["taken_up_eoh"],
        "deferred_eoh":          c["deferred_eoh"],
        "deferred_personal_eoh": c["deferred_personal_eoh"],
        "labor_income":          labor_income if labor_income is not None
                                 else float(after["teh_created"]),
        "trust_surplus_deficit": f1["surplus_deficit"],
        "trust_absorbs":         f1["solvent"],
        "absorbed":              f1["solvent"],
        **comp,
        "labour_outcome":        c["labour_outcome"],
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
    population: float = REFERENCE_FRAME_POPULATION,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
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
    ecosystem_health_before: float = ECOSYSTEM_HEALTH_DEFAULT,
    ecosystem_health_after: float = 0.30,
    demographic_shock_spec: dict | None = None,
    automation_fraction_lost: float = 0.0,
    trust_balance: float | None = None,
    population: float = REFERENCE_FRAME_POPULATION,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = CANONICAL_CAPITAL_AGE_BASE,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    suff_levy_rate: float = SUFF_LEVY_RATE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    labor_supply_per_capita: float | None = None,
) -> dict:
    """
    Several shocks at once — applied to ONE state and run through ONE cascade.

    Until 2026-10-01 each component was run separately and their EOH deltas
    summed and charged to the Trust as TEH. The shocks share one labour pool,
    so the honest composition is to apply every change to the same state —
    capability lost, the collapse's restoration, the new population and age
    mix — and read the cascade once. Each component is also run alone and
    reported in `individual_outcomes`; the combined outcome is never better
    than the worst of them.
    """
    trust_balance = resolve_trust_balance(trust_balance, population)
    # (e) 2026-09-09: unspecified capital resolves along the arc; a supplied
    # stock is the ACTUAL stock and is never rescaled.
    capital_stock_teh = resolve_capital_stock(capital_stock_teh, epsilon, population=population)
    common: dict[str, Any] = dict(trust_balance=trust_balance, population=population,
                  capital_stock_teh=capital_stock_teh, capital_age_ratio=capital_age_ratio)
    health0 = ecosystem_health_before if ecology_collapse else 0.70
    s0 = _base_state(epsilon, population, health0, labor_supply_per_capita)
    s1 = _State(**s0)
    individual: dict[str, str] = {}
    automation_deferred = 0.0

    if ecology_collapse:
        eco = ecological_eoh_spike(
            epsilon, ecosystem_health_before, ecosystem_health_after,
            suff_levy_rate=suff_levy_rate, dep_rate=dep_rate, div_rate=div_rate,
            meaningful_activity_teh=meaningful_activity_teh,
            labor_supply_per_capita=labor_supply_per_capita, **common)
        individual["ecological_eoh_spike"] = eco["outcome"]
        s1 = _State(**{**s1, "ecosystem_health": ecosystem_health_after,
                       "restoration_eoh": eco["restoration_eoh_high"]})
    if demographic_shock_spec is not None:
        dem = demographic_shock(
            epsilon, demographic_shock_spec["shock_type"], demographic_shock_spec["magnitude"],
            meaningful_activity_teh=meaningful_activity_teh, suff_levy_rate=suff_levy_rate,
            dep_rate=dep_rate, div_rate=div_rate,
            labor_supply_per_capita=labor_supply_per_capita, **common)
        individual["demographic_shock"] = dem["outcome"]
        changed = _demographic_change(s0, demographic_shock_spec["shock_type"],
                                      demographic_shock_spec["magnitude"])
        s1 = _with_age_mix(s1, changed["population"], changed["age_fractions"])
    if automation_fraction_lost > 0.0:
        auto = automation_failure_shock(
            epsilon, fraction_lost=automation_fraction_lost,
            labor_supply_per_capita=labor_supply_per_capita, **common)
        individual["automation_failure_shock"] = auto["outcome"]
        automation_deferred = auto["deferred_eoh"]
        s1 = _State(**{**s1, "capability": epsilon * (1.0 - automation_fraction_lost)})

    if not individual:
        # NOTHING WAS TESTED, SO NOTHING IS CLAIMED (2026-10-03). This returned
        # "STABLE" and trust_absorbs_combined=True — a verdict and an answer
        # from a run that applied no shock and never asked the Trust, which a
        # test pinned as intended (mode 9: it could not fail).
        return {
            "scenario": "compound_shock", "epsilon": epsilon,
            "individual_outcomes": {}, "combined_eoh_delta": 0.0,
            "combined_deferred_eoh": 0.0, "combined_deferred_personal_eoh": 0.0,
            "automation_deferred_eoh": 0.0, "trust_absorbs_combined": None,
            "combined_outcome": "NO_SHOCK",
            "recommendation": (f"Compound shock at ε={epsilon:.2f}: no components "
                               "enabled — nothing was tested."),
        }

    before = _run(s0, epsilon, capital_stock_teh, capital_age_ratio, None)
    after = _run(s1, epsilon, capital_stock_teh, capital_age_ratio, None)
    c = _cascade(before, after)
    f1 = _fiscal(s1, epsilon, after, trust_balance, capital_stock_teh, capital_age_ratio,
                 None, meaningful_activity_teh, suff_levy_rate, dep_rate, div_rate)
    comp = _competency(s0, before, s1, after)
    combined = _worse(c["labour_outcome"], comp["competency_outcome"],
                      _classify(f1["solvent"], f1["surplus_deficit"], trust_balance),
                      *individual.values())
    rec = (
        f"Compound shock at ε={epsilon:.2f} ({len(individual)} component(s), one "
        f"state): {c['added_human_eoh']:,.0f} h/yr more asked of people, "
        f"{c['taken_up_eoh']:,.0f} taken up, {c['deferred_eoh']:,.0f} deferred"
        + (f" ({c['deferred_personal_eoh']:,.0f} personal)"
           if c["deferred_personal_eoh"] > 0.0 else "")
        + f". Trust {'solvent' if f1['solvent'] else 'INSOLVENT'}. "
        f"Individual outcomes: {individual}. Combined outcome: {combined}."
    )
    return {
        "scenario":                       "compound_shock",
        "epsilon":                        epsilon,
        "individual_outcomes":            individual,
        "combined_eoh_delta":             c["added_human_eoh"],
        "combined_deferred_eoh":          c["deferred_eoh"],
        "combined_deferred_personal_eoh": c["deferred_personal_eoh"],
        "automation_deferred_eoh":        automation_deferred,
        "trust_absorbs_combined":         f1["solvent"],
        **comp,
        "combined_outcome":               combined,
        "recommendation":                 rec,
    }
