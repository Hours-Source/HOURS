"""
EOH Fulfillment and TEH Creation, TEH Destruction

Model the full pipeline:
  EOH demand (total_eoh)
  → human-labor share (human_eoh_share)
  → registered fraction (registered_eoh)
  → TEH creation through labor (teh_created)
  → TEH destruction through consumption and write-down
  → net TEH supply (teh_supply) — must satisfy Condition I

The critical distinction from the old model: EOH is the *input*.
Labor supply is the *response* to EOH demand, not the starting point.

CAPABILITY vs OBSERVED — TWO QUANTITIES, ONE NAME UNTIL 2026-09-01
------------------------------------------------------------------
`epsilon` has been doing two jobs. As an INPUT it says what machines are capable
of taking; as an OBSERVABLE it is defined as the machine share of obligation,
`machine_eoh / total_eoh`. Under `automation_response="uniform"` these are
identical by construction — the split is exactly (1-ε) on every domain, so the
share recovered from the split is the number fed in, and the distinction cannot
be seen.

**Phase 2 separated them.** Because the personal domain now retains a floored
human share, the observed machine share is strictly BELOW the supplied index
everywhere except zero:

    capability   0.00    0.40    0.90    0.99    →1
    observed     0.00    0.365   0.825   0.909   0.917

So the input is a **machine-capability index** and ε proper is the **observed
share**. Both are reported; `observable_epsilon()` derives the second from the
first, and `observable_epsilon_ceiling()` gives the limit — which is why the arc
stops short of 1 as a consequence of the declared floors rather than as a
convention.

`epsilon=` remains accepted everywhere as the historical name for the capability
index, and nothing that passed it before behaves differently. What changed is
that the derived quantity is now reported beside it instead of being assumed
equal to it.

Mission Statement: §"EOH as demand signal", §"The dual ledger",
§"Condition I — Ledger Identity", §"Guardrail II — Capital write-down"
"""

from __future__ import annotations

from hours_eoh.data import (
    PERSONAL_AUTOMATION_FLOORS,
    PERSONAL_EOH_COMPONENTS,
    CAPITAL_FAILURE_RATE,
    CAPITAL_STOCK_DEFAULT,
    CAPITAL_WRITEDOWN_MONITORING_SLOPE,
    ECOLOGICAL_INTENSITY_BASE,
    INFRA_MAINT_RATE,
    LAND_HECTARES_PER_CAPITA,
    KNOWLEDGE_EOH_BASE,
    PERSONAL_EOH_BASE,
    SKILL_TRANSMISSION_RATE,
    MEAN_MULTIPLIER_REFERENCE,
)


# ---------------------------------------------------------------------------
# Human EOH Share
# ---------------------------------------------------------------------------

def human_eoh_share(
    total_eoh: float,
    epsilon: float = 0.40,
) -> float:
    """
    The portion of total EOH that requires human labor at this automation level.

    At ε=0: all EOH fulfillment is human labor → human_eoh = total_eoh.
    At ε=0.99: only 1% requires human labor; machines handle the rest.

    The relationship is linear: human_fraction = (1 - ε). This captures the
    clean substitution of automation for human labor across all EOH domains.
    The total entropy obligation (total_eoh) does not change — only who
    (or what) fulfills it changes.

    Args:
        total_eoh: Total EOH (hours/year) across all four domains.
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Human-labor EOH (hours/year) — the portion requiring human workers.

    Reference: Mission Statement §"EOH and automation" — "At ε=0, all EOH
    fulfillment is human labor ... At ε=0.99, only 1% of registered EOH
    fulfillment requires human labor."
    """
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError(f"epsilon must be in [0.0, 1.0], got {epsilon}")
    human_fraction = 1.0 - epsilon
    return total_eoh * human_fraction


# ---------------------------------------------------------------------------
# Registered EOH
# ---------------------------------------------------------------------------

def registered_eoh(
    human_eoh: float,
    registration_share: float,
) -> float:
    """
    The portion of human-fulfilled EOH registered in the collective ledger.

    Only registered EOH generates TEH. Self-care (cooking own dinner) and
    household EOH (family vehicle maintenance) are zero events — real entropy
    resistance happens, but no monetary event occurs because the EOH is not
    in the collective ledger. The registration boundary is what defines
    economic activity.

    Args:
        human_eoh: Human-labor EOH (hours/year) — from human_eoh_share().
        registration_share: Fraction of human EOH registered in collective ledger,
                            ∈ [0.0, 1.0]. Comes from total_registration_share()
                            in registration.py.

    Returns:
        Registered EOH (hours/year) — the portion that will generate TEH.

    Special case: self-care and household EOH have registration_share=0.0,
    producing zero registered EOH and therefore zero TEH — correct by design.

    Reference: Mission Statement §"The registration boundary" — "Self-care is
    a zero event ... The collective decides which obligations it recognizes."
    """
    if not 0.0 <= registration_share <= 1.0:
        raise ValueError(
            f"registration_share must be in [0.0, 1.0], got {registration_share}"
        )
    return human_eoh * registration_share


# ---------------------------------------------------------------------------
# TEH Creation
# ---------------------------------------------------------------------------

def teh_created(
    registered_eoh_hours: float,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
) -> float:
    """
    TEH created when workers fulfill registered EOH at their multiplied tier rates.

    Governing equation:
        TEH = EOH_registered × m̄

    where m̄ = population_weighted_mean_multiplier() across all workers fulfilling
    registered EOH in this period.

    Worked example: 1,000 registered EOH fulfilled by a workforce with mean
    multiplier m̄ = 2.10 → 2,100 TEH created this period.
    At m̄ = 1.0 (all base tier): 1,000 EOH → 1,000 TEH.
    At m̄ = 3.0 (advanced workforce): 1,000 EOH → 3,000 TEH.

    The mean_multiplier must satisfy Condition II (band [1.8, 2.1]). Caller is
    responsible for verifying this via multiplier_band_check() before passing
    mean_multiplier here. This function does not gate on the band.

    Args:
        registered_eoh_hours: Registered EOH fulfilled this period (hours).
        mean_multiplier: Population-weighted mean multiplier (must be ≥ 1.0).

    Returns:
        TEH created (currency units — 1 TEH = 1 verified hour of entropy resistance).

    Reference: Mission Statement §"EOH as demand signal" — "100 EOH ...
    at a 3.0 multiplier creates 300 TEH. The multiplier system applies to all
    entropy-reduction labor uniformly."
    """
    if mean_multiplier < 1.0:
        raise ValueError(f"mean_multiplier must be ≥ 1.0, got {mean_multiplier}")
    return registered_eoh_hours * mean_multiplier


# ---------------------------------------------------------------------------
# D0: Capital Write-Down
# ---------------------------------------------------------------------------

def capital_writedown(
    capital_stock_teh: float,
    failure_rate: float = CAPITAL_FAILURE_RATE,
    epsilon: float = 0.40,
) -> float:
    """
    TEH destroyed when assets degrade beyond recoverability (capital write-down).

    When capital degrades beyond the recoverability threshold, the associated
    EOH is formally written off and the TEH embodied in that capital is
    destroyed. For human capital: death is a write-down — the person's personal
    EOH vanishes and their entropy-reduction capacity must be redistributed.

    Higher ε enables better monitoring and predictive maintenance, slightly
    reducing the fraction of capital that fails catastrophically (versus being
    maintained in time).

    Args:
        capital_stock_teh: Current capital stock value in TEH.
        failure_rate: Annual fraction of capital that fails beyond recovery.
        epsilon: Automation level. Better monitoring → slightly lower failure rate.

    Returns:
        TEH destroyed through capital write-down this period.

    Reference: Mission Statement §"Guardrail II — Capital write-down" — "When
    capital degrades beyond the point where maintenance labor can restore
    function, the associated EOH must be formally written off."
    """
    # Better monitoring at higher ε catches failures earlier, reducing total
    # catastrophic write-downs (CAPITAL_WRITEDOWN_MONITORING_SLOPE reduction at ε=1.0).
    monitoring_factor = 1.0 - CAPITAL_WRITEDOWN_MONITORING_SLOPE * epsilon
    adjusted_rate = failure_rate * monitoring_factor
    return capital_stock_teh * adjusted_rate


# ---------------------------------------------------------------------------
# TEH Supply (Condition I)
# ---------------------------------------------------------------------------

def teh_supply(
    teh_created_total: float,
    teh_destroyed_total: float,
) -> float:
    """
    Net TEH in existence for an UNENDOWED economy: cumulative creation minus
    cumulative destruction.

    This is the operational definition of Condition I (Ledger Identity) for a
    collective that began at zero.

    SCOPE — READ THIS BEFORE USING IT (2026-09-01). **This function has no
    callers, and it raises on the shipped model's canonical trajectory.** The
    simulated economy starts with a founding endowment — a Trust balance plus
    embodied capital that no registered fulfilment created — so `simulate_period`
    computes `teh_endowment + created - destroyed` instead, and destruction
    legitimately exceeds creation for a long initial stretch while that founding
    stock is retired. Handed those cumulative flows, the guard below fires.

    The doctrine quoted under Reference is NOT amended here: for a collective
    founded at zero this function is exactly right, and the identity it states is
    the bound the framework's value-anchor argument wants. What is recorded is
    that the shipped model is not that collective, and that the two accounts have
    to be told apart. `tests/test_stock_is_bounded.py` pins both — the endowed
    identity that holds every period, and this function's refusal of the endowed
    trajectory — and fails if this acquires a caller, since that would be either
    a bug or a decision to model an endowment-free economy.

    Spending and levies are circulatory — they move TEH between accounts but
    do not appear here. Only terminal consumption and capital write-down remove
    TEH from existence.

    Args:
        teh_created_total: Cumulative TEH created through verified labor (hours).
        teh_destroyed_total: Cumulative TEH destroyed (consumption + write-downs).

    Returns:
        Net TEH supply (hours). Non-negative by construction.

    Raises:
        ValueError: If destroyed > created (a ledger violation — impossible in
                    a correctly operating system).

    Reference: Mission Statement §"Condition I — Ledger Identity" — "The total
    supply must always equal cumulative creation minus cumulative destruction,
    with no exceptions." Quoted as written; see SCOPE above for how a founding
    endowment sits against it.
    """
    tol = max(teh_created_total * 1e-9, 1e-6)  # floating-point tolerance
    if teh_destroyed_total > teh_created_total + tol:
        raise ValueError(
            f"Ledger violation: destroyed ({teh_destroyed_total:.4f}) > "
            f"created ({teh_created_total:.4f}) — impossible in a correct system."
        )
    return teh_created_total - teh_destroyed_total


# ---------------------------------------------------------------------------
# Per-domain human EOH breakdown
# ---------------------------------------------------------------------------

#: How the machine/human split is applied across the personal obligation.
#: `uniform` is the shipped behaviour and reproduces every pre-Phase-2 number
#: exactly; `per_component` applies the floors in PERSONAL_AUTOMATION_FLOORS.
AUTOMATION_RESPONSES: tuple[str, ...] = ("uniform", "per_component")

#: ADOPTED 2026-09-01 (author sign-off, notes/phase-2-per-component-automation.md).
#: `per_component` is now the DEFAULT. `uniform` stays reachable and is what
#: every figure published before this date was computed at — the Phase 4d/4e/4f
#: pattern, where the superseded policy survives under its own name so a stale
#: figure can be reproduced rather than merely disbelieved.


def personal_human_fraction(
    epsilon: float,
    automation_response: str = "per_component",
) -> float:
    """
    The share of personal EOH that stays human-carried at automation level ε.

    Governing equations:

        uniform(ε)        = 1 − ε
        per_component(ε)  = Σ_c share_c · [ f_c + (1 − f_c)·(1 − ε) ]

    where share_c comes from `PERSONAL_EOH_COMPONENTS` and f_c from
    `PERSONAL_AUTOMATION_FLOORS` (0.0 for a component with no declared floor,
    which reduces that term to 1 − ε).

    units: dimensionless fraction in [0, 1].

    ε-behaviour: both forms equal 1.0 at ε=0 — with nothing automated a floor ON
    automation cannot bite, and that coincidence is the control. They diverge as
    ε rises; at ε=0.99 uniform gives 0.0100 and per_component 0.1022, a factor
    of 10.2.

    WHY THIS EXISTS. `CARE_AUTOMATION_FLOOR`'s own tag block says relational care
    "cannot be automated at any ε — a commitment about what care IS", and Block
    II independently finds care the least abatable component at 84.4% of the
    residual. But the shipped split applies one (1 − ε) to every domain, and care
    is 62.1% of personal EOH. **The fiscal layer has modelled care as
    un-automatable while the generation layer automated it at the full rate**,
    and nothing compared them until `scenarios/obligation_accounts`.

    AN AUTOMATION FLOOR IS NOT AN ABATABILITY. `abatability` in
    `PERSONAL_EOH_COMPONENTS` is the most infrastructure can REMOVE — a(K),
    ε-free by construction. This is who does what REMAINS. They compose.

    Worked example (ε=0.99, per_component): care is 62.1% of personal and floors
    at 0.15 + 0.85·0.01 = 0.1585; the other 37.9% carry no floor and give 0.0100;
    the weighted fraction is 0.1022.

    Args:
        epsilon: Automation level [0.0, 1.0].
        automation_response: One of AUTOMATION_RESPONSES. Default `uniform`
            reproduces the pre-2026-08-30 split exactly.

    Raises:
        ValueError: if epsilon is outside [0.0, 1.0] or the response is unknown.
    """
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError(f"epsilon must be in [0.0, 1.0], got {epsilon}")
    if automation_response not in AUTOMATION_RESPONSES:
        raise ValueError(
            f"automation_response must be one of {AUTOMATION_RESPONSES}, "
            f"got {automation_response!r}"
        )

    uniform = 1.0 - epsilon
    if automation_response == "uniform":
        return uniform

    total = 0.0
    for name, spec in PERSONAL_EOH_COMPONENTS.items():
        floor = PERSONAL_AUTOMATION_FLOORS.get(name, 0.0)
        total += float(spec["share"]) * (floor + (1.0 - floor) * uniform)
    return total


def _resolve_capability(epsilon: float | None, machine_capability: float | None,
                        default: float | None = None) -> float:
    """
    Accept either name for the machine-capability index; refuse both.

    `epsilon=` is the historical name and still works. `machine_capability=` is
    the name the quantity earns after 2026-09-01 (see the CAPABILITY vs OBSERVED
    block above). Supplying both with different values RAISES rather than
    silently preferring one — the `total_eoh` base-vs-area precedent. Supplying
    both with the SAME value is permitted, since a caller migrating names should
    not be punished for being explicit.
    """
    if epsilon is not None and machine_capability is not None:
        if epsilon != machine_capability:
            raise ValueError(
                f"epsilon={epsilon} and machine_capability={machine_capability} "
                f"are two names for one quantity and disagree; supply one"
            )
        return float(epsilon)
    value = machine_capability if machine_capability is not None else epsilon
    if value is None:
        if default is None:
            raise ValueError("supply epsilon= or machine_capability=")
        return float(default)
    return float(value)


def observable_epsilon(
    total_eoh_dict: dict,
    machine_capability: float,
    automation_response: str = "per_component",
) -> float:
    """
    The OBSERVED machine share of gross obligation — ε as the theory defines it.

    Governing equation:

        ε_obs = (total_eoh - human_eoh) / total_eoh

    where `human_eoh` is what `human_eoh_per_domain` actually allocates to
    people at the given capability. units: dimensionless, [0, 1).

    WHY THIS IS NOT THE INPUT. Under `uniform` the split is exactly (1-c) on
    every domain, so ε_obs == c identically and the distinction is invisible.
    Under `per_component` the personal domain keeps a floored human share, so
    **ε_obs < c everywhere except c = 0**. Feeding c = 0.99 through the canonical
    state returns ε_obs ≈ 0.9085 — a gap of 0.081. The parameter is a statement
    about machines; this is the statement about the ledger.

    Worked example: at the canonical arc points the gap runs +0.000 (c=0),
    +0.035 (c=0.40), +0.081 (c=0.99).

    RELATION TO `trajectory.compute_epsilon`. That function normalises by the
    fully-recognised collective potential, so it additionally carries the
    registration boundary. This one is the machine share of GROSS obligation and
    is what the fulfilment split can answer on its own. They coincide when
    registration is complete; neither supersedes the other.

    Raises:
        ValueError: if the supplied obligation totals to zero, where the share
            is undefined rather than zero.
    """
    domains = ("personal", "infrastructure", "ecological", "knowledge")
    total = sum(total_eoh_dict.get(d, 0.0) for d in domains)
    if total <= 0.0:
        raise ValueError("observable epsilon is undefined at zero obligation")
    human = human_eoh_per_domain(
        total_eoh_dict, machine_capability,
        automation_response=automation_response,
    )["total"]
    return (total - human) / total


def observable_epsilon_ceiling(
    total_eoh_dict: dict,
    automation_response: str = "per_component",
) -> float:
    """
    The highest observed machine share the declared floors permit.

    Governing equation: `observable_epsilon(eoh, 1.0, response)` — the limit as
    machine capability goes to its maximum. units: dimensionless.

    THIS IS WHY ε DOES NOT REACH 1. Under `uniform` the ceiling is exactly 1.0:
    nothing stops automation. Under `per_component` the personal domain retains
    `Σ share_c · floor_c` of its obligation for people whatever the machines can
    do, so the ceiling is `1 - personal_share · Σ share_c · floor_c` and sits
    strictly below 1. The arc's endpoint is therefore a CONSEQUENCE of the
    declared floors rather than a convention.

    Worked example: on the canonical ε=0.99 state the ceiling is ≈0.917.

    IT IS A LOWER BOUND ON THE RESIDUAL, and therefore an UPPER bound on itself.
    Only care carries a measured floor; nutrition, shelter and health carry none,
    which is an admission and not a zero. Every floor added lowers this ceiling.
    """
    return observable_epsilon(total_eoh_dict, 1.0, automation_response)


def human_eoh_per_domain(
    total_eoh_dict: dict,
    epsilon: float | None = None,
    automation_response: str = "per_component",
    machine_capability: float | None = None,
) -> dict:
    """
    Per-domain human-labor EOH from a total_eoh() result dict.

    total_eoh() returns gross domain totals (full physical obligation) but not
    the human-labor portions. This helper splits each domain, making
    domain-specific human workforce demand explicit for stewardship planning,
    fiscal allocation, and scarcity detection.

    Args:
        total_eoh_dict: Return dict from total_eoh(). Must contain keys:
                        "personal", "infrastructure", "ecological", "knowledge".
        epsilon: Historical name for `machine_capability`; still accepted.
        machine_capability: Machine capability index [0.0, 0.99] — what machines
                        CAN take, not what they are observed to have taken.
        automation_response: "per_component" (default) or "uniform".

    Returns:
        dict: {
          "personal":       float,
          "infrastructure": float,
          "ecological":     float,
          "knowledge":      float,
          "total":          float,
          "human_fraction": float,   (human EOH / gross EOH — the real share)
          "uniform_split_factor": float,  (= 1 - c; applied to the non-personal
                          domains. Equal to "human_fraction" only under
                          `uniform`, which is why one name served both before.)
          "personal_human_fraction": float,
          "human_fraction_observed": float,  (= total / gross — the real share)
          "machine_capability":      float,  (the input, honestly named)
          "epsilon_observable":      float,  (the DERIVED machine share)
          "epsilon":        float,   (deprecated alias for machine_capability)
        }

    THE TWO ε KEYS ARE NOT THE SAME QUANTITY, and after Phase 2 they differ.
    `epsilon`/`machine_capability` is what was supplied; `epsilon_observable` is
    what the resulting split implies. Reporting only the first is how a parameter
    comes to be quoted as an outcome. See `observable_epsilon`.

    Reference: Mission Statement §"EOH and automation".

    PHASE 2 (adopted 2026-09-01): `automation_response="per_component"` is the
    DEFAULT and gives the PERSONAL domain its own human fraction from
    `personal_human_fraction`, honouring the declared automation floors. The
    other three domains keep the uniform split — nothing in this repo measures a
    floor for them, and inventing one would be the guessing this module refuses.
    `"uniform"` remains reachable and reproduces every pre-flip number exactly.
    """
    capability = _resolve_capability(epsilon, machine_capability, default=0.40)
    human_fraction = 1.0 - capability
    personal_fraction = personal_human_fraction(capability, automation_response)
    domains = ("personal", "infrastructure", "ecological", "knowledge")
    per_domain = {
        d: total_eoh_dict.get(d, 0.0) * (
            personal_fraction if d == "personal" else human_fraction
        )
        for d in domains
    }
    human_total = sum(per_domain.values())
    gross = sum(total_eoh_dict.get(d, 0.0) for d in domains)
    observed = (gross - human_total) / gross if gross > 0.0 else 0.0
    return {
        **per_domain,
        "total":          human_total,
        # `human_fraction` MEANS the share of obligation people carry. Before
        # Phase 2 that was (1 - c) on every domain and the two readings coincided;
        # now the personal domain has its own floor, so (1 - c) is the split
        # factor applied to the OTHER three and is no longer the human fraction
        # of anything. It is reported under a name that says what it is.
        "human_fraction": (human_total / gross) if gross > 0.0 else 0.0,
        "uniform_split_factor": human_fraction,
        "personal_human_fraction": personal_fraction,
        "human_fraction_observed": (human_total / gross) if gross > 0.0 else 0.0,
        "automation_response":     automation_response,
        "machine_capability":      capability,
        "epsilon_observable":      observed,
        "epsilon":        capability,
    }


# ---------------------------------------------------------------------------
# Labor-constrained fulfillment — the personal-EOH deficit
# ---------------------------------------------------------------------------

_DOMAINS: tuple[str, ...] = ("personal", "infrastructure", "ecological", "knowledge")
_NON_PERSONAL: tuple[str, ...] = ("infrastructure", "ecological", "knowledge")


def labor_constrained_fulfillment(
    human_by_domain: dict[str, float],
    available_labor_eoh: float,
    rationing: str = "survival_first",
) -> dict:
    """
    Split human-carried EOH demand into what labor can SERVE and what is DEFERRED.

    The pipeline's default assumption is that every hour of human-carried EOH gets
    worked: human_eoh = (1−ε)·total, full stop. That is a demand figure being
    reported as a fulfillment figure, and it hides the one thing an obligation
    ledger exists to show — obligation that goes unmet. Ecological EOH has carried
    a `deferred` term since the beginning; personal EOH, which is the survival
    floor, carried none.

    Governing relations:

        demand   H_d = Σ_domain human_by_domain[d]
        supply   L   = available_labor_eoh
        served   S   = min(H_d, L)
        deferred D   = max(0, H_d − L)

    and D is allocated across domains by the rationing doctrine:

        "survival_first" (default)  personal EOH is served to the extent labor
            allows, and the shortfall falls on the non-personal domains pro-rata.
            Only once personal alone exceeds L does `deferred_personal` become
            non-zero. This is the physically realistic order — a population short
            of labor feeds itself before it maintains bridges — and it means a
            non-zero personal deficit is a severe reading, not a routine one.

        "pro_rata"  the shortfall is spread across all four domains in proportion
            to demand. Use when modelling a collective that cannot or does not
            triage, or as the pessimistic comparison.

    WHAT THIS DOES NOT CLAIM. Deferred personal EOH is unmet biological
    obligation — nutrition, shelter, hygiene, care. Its consequences are real, but
    this function reports HOURS, not outcomes. Mortality in this model is
    exogenous (`ANNUAL_DEATH_RATE`, `death_rate_elderly`) and nothing here feeds
    it; treating a deficit as a death rate would require a dose-response
    relationship the framework does not have and this function does not supply.
    What it supplies is the quantity such a relationship would take as input.

    units: all EOH in hours/year; `coverage` dimensionless.
    ε-behavior: the caller supplies human-carried demand, which already has (1−ε)
    applied, so the deficit falls as ε rises — machines relieve labor. At high ε
    the deficit goes to zero and this function is a no-op, which is correct.

    Args:
        human_by_domain: Human-carried EOH per domain (from human_eoh_per_domain).
        available_labor_eoh: L, human labor capacity in EOH-hours/year (≥ 0),
            e.g. workforce_size × reference work-year hours.
        rationing: "survival_first" (default) | "pro_rata".

    Returns:
        dict: {
          "demand_by_domain":   dict,   (echo of input, the four domains)
          "served_by_domain":   dict,
          "deferred_by_domain": dict,
          "demand_total":       float,
          "served_total":       float,
          "deferred_total":     float,
          "deferred_personal":  float,  (the survival-floor shortfall)
          "available_labor":    float,
          "labor_constrained":  bool,   (demand exceeds supply)
          "coverage":           float,  (served / demand ∈ [0, 1])
          "rationing":          str,
        }

    Raises:
        ValueError: on negative labor, negative demand, or an unknown doctrine.

    Worked example (1M people, ε=0, shipped constants, L = 1e9 h/yr):
        personal demand    2,213M h/yr      served 1,000M    deferred 1,213M
        non-personal          76M h/yr      served     0M    deferred    76M
        coverage 0.437 — the population can cover 44% of its obligation, and
        under survival_first every hour of labor goes to personal EOH with
        nothing left for infrastructure, ecology or knowledge.
    """
    if available_labor_eoh < 0.0:
        raise ValueError(
            f"available_labor_eoh must be ≥ 0, got {available_labor_eoh}"
        )
    if rationing not in ("survival_first", "pro_rata"):
        raise ValueError(
            f"rationing must be 'survival_first' or 'pro_rata', got {rationing!r}"
        )

    demand = {d: float(human_by_domain.get(d, 0.0)) for d in _DOMAINS}
    for d, v in demand.items():
        if v < 0.0:
            raise ValueError(f"human EOH for {d} must be ≥ 0, got {v}")

    demand_total = sum(demand.values())
    served_total = min(demand_total, available_labor_eoh)

    if demand_total <= available_labor_eoh or demand_total == 0.0:
        served = dict(demand)
    elif rationing == "pro_rata":
        f = served_total / demand_total
        served = {d: v * f for d, v in demand.items()}
    else:  # survival_first
        p_served = min(demand["personal"], available_labor_eoh)
        remaining = available_labor_eoh - p_served
        np_demand = sum(demand[d] for d in _NON_PERSONAL)
        f = (remaining / np_demand) if np_demand > 0.0 else 0.0
        f = min(1.0, f)
        served = {"personal": p_served,
                  **{d: demand[d] * f for d in _NON_PERSONAL}}

    deferred = {d: max(0.0, demand[d] - served[d]) for d in _DOMAINS}

    return {
        "demand_by_domain":   demand,
        "served_by_domain":   served,
        "deferred_by_domain": deferred,
        "demand_total":       demand_total,
        "served_total":       sum(served.values()),
        "deferred_total":     sum(deferred.values()),
        "deferred_personal":  deferred["personal"],
        "available_labor":    available_labor_eoh,
        "labor_constrained":  demand_total > available_labor_eoh,
        "coverage":           (sum(served.values()) / demand_total
                               if demand_total > 0.0 else 1.0),
        "rationing":          rationing,
    }


# ---------------------------------------------------------------------------
# End-to-end EOH → TEH pipeline orchestrator
# ---------------------------------------------------------------------------

def eoh_to_teh_pipeline(
    epsilon: float | None = None,
    population: float = 1_000_000.0,
    age_distribution: dict | None = None,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
    deferred_ecological: float = 0.0,
    knowledge_complexity: float = 1.0,
    # BOUND 2026-08-15 (author sign-off), was a bare `0.10` literal.
    # `knowledge_eoh` migrated to SKILL_TRANSMISSION_RATE (0.025) in Block K-III,
    # but this literal did not follow it and was passed straight into total_eoh(),
    # OVERRIDING that default. The same repricing hazard as the `= 1500.0`
    # defaults: a constant that does not propagate is not a single source of
    # truth. Two paths therefore computed knowledge EOH 4× apart, and the `arc`
    # table printed its knowledge/total columns from one and teh_created from the
    # other. Binding it moves pipeline total 2.38× and teh_created 2.16× at
    # ε=0.99 — see notes/placeholder-inversion-audit.md.
    skill_decay_rate: float = SKILL_TRANSMISSION_RATE,
    capital_eoh_eliminated: float = 0.0,
    capital_personal_eoh_fulfilled: float = 0.0,
    infrastructure_compounding_eoh: float = 0.0,
    competency_gap_factor: float = 0.0,
    registration_share: float | None = None,
    personal_registration_share: float | None = None,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    monitoring_capability: float | None = None,
    knowledge_complexity_per_unit: float | None = None,
    thermal_obligation: float = 0.0,
    # See the note on total_eoh: stranded at ecological_eoh until 2026-08-30
    # while its sibling thermal_obligation reached here.
    restoration_obligation: float = 0.0,
    available_labor_eoh: float | None = None,
    rationing: str = "survival_first",
    # Per-domain scale overrides. These reached `total_eoh` but stopped here, so
    # the documented intake path (docs/guides/implementation_guide.md tells an
    # institution to run this function) could not express the four domain bases an
    # institution actually recalibrates — nor the AREA the ecological obligation
    # was keyed to on 2026-08-16, which left that fix stranded one layer below the
    # entry point. All default to None → total_eoh's own defaults, so no existing
    # caller moves.
    personal_base: float = PERSONAL_EOH_BASE,
    # THE STANDARDS SELECTOR (Block I). It reached `total_eoh` and stopped at
    # this wall — the same wall the four domain bases stopped at on 2026-08-17,
    # and it is the LARGER lever: survival → sufficiency moves total EOH 2.09x,
    # more than any base. docs/guides/implementation_guide.md tells an
    # institution to pass it while also telling them to run this function, so
    # the guide's two instructions could not both be followed.
    personal_standard: str | None = None,
    infra_maint_rate: float = INFRA_MAINT_RATE,
    ecological_base: float | None = None,
    ecological_area_hectares: float | None = None,
    ecological_intensity: float = ECOLOGICAL_INTENSITY_BASE,
    ecological_hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
    # The Phase-4e partition switch: "domain" books the health response as the
    # standing obligation (default, pre-4e behaviour), "guf" relocates it to the
    # reset cost. Stranded at this wall until 2026-08-17 — a switch that cannot
    # be reached from the documented entry point is a switch nobody exercises.
    ecological_health_response: str = "guf",
    ecological_standing_response: str = "guf",
    automation_response: str = "per_component",
    knowledge_base: float = KNOWLEDGE_EOH_BASE,
    # THE MACHINE-CAPABILITY INDEX under its own name (2026-09-01). `epsilon=`
    # still works and is unchanged; this is the same quantity said honestly, and
    # supplying both with different values raises. See the CAPABILITY vs OBSERVED
    # block at the top of this module.
    machine_capability: float | None = None,
) -> dict:
    """
    End-to-end EOH → human share → registered → TEH creation in one call.

    Chains the four-step pipeline with a single epsilon, preventing the
    common error of calling total_eoh() at one ε and human_eoh_share() at
    another. Returns all intermediate values for auditability (Guardrail I).

    Pipeline:
      1. total_eoh(epsilon, ...)                  → domain breakdown + total
      2. human_eoh_share(domain, epsilon)         → human labor portion per domain
      3. registered_eoh(human, share_by_domain)   → per-domain registration
      4. teh_created(registered_total, mult)      → TEH generated this period

    Registration is applied per-domain — a critical distinction:
      - Personal EOH uses personal_eoh_registration_share(ε): demand registration,
        tracking what fraction of biological obligation is collectively recognized.
        Near-zero at ε=0; rises to ~0.95 by ε=0.99. Inflection at ε=0.65.
      - Infrastructure/ecological/knowledge EOH use total_registration_share(ε):
        labor registration, tracking what fraction of fulfillment labor is on
        the collective ledger.

    If registration_share is provided (non-None), it overrides BOTH personal
    and non-personal registration uniformly — useful for scenario testing.
    If personal_registration_share is provided separately, it overrides only
    the personal domain while non-personal uses the dynamic (or registration_share)
    value.

    Args:
        epsilon: Automation level [0.0, 0.99]. Applied consistently to all steps.
        population: Total population.
        age_distribution: Optional dict mapping age group → fraction.
        capital_stock: Baseline capital stock in TEH (at ε=0).
        capital_age_ratio: Mean asset age relative to design life.
        ecosystem_health: Ecosystem state ∈ [0, 1].
        deferred_ecological: Accumulated deferred ecological EOH (hours).
        knowledge_complexity: Relative knowledge base size.
        skill_decay_rate: Annual skill renewal fraction.
        capital_eoh_eliminated: EOH eliminated by capital stock.
        capital_personal_eoh_fulfilled: Personal EOH fulfilled by capital.
        infrastructure_compounding_eoh: Deferred-maintenance compounding spike.
        competency_gap_factor: Knowledge EOH amplifier from competency gaps.
        registration_share: Uniform override for ALL domains. None → per-domain
            dynamic computation. When set, also overrides personal_registration_share.
        personal_registration_share: Override for the personal domain only.
            None → use personal_eoh_registration_share(epsilon) dynamically.
            Ignored if registration_share is set.
        mean_multiplier: Population-weighted mean multiplier for step 4.
        available_labor_eoh: OPTIONAL labor-supply constraint, EOH-hours/year.
            None (default) → the historical behavior: every hour of human-carried
            EOH is assumed worked, and `deferred_*` are 0. When supplied,
            registration operates on SERVED rather than DEMANDED EOH — labor that
            does not exist cannot mint TEH — and the shortfall is reported.
        rationing: How a shortfall is allocated across domains,
            "survival_first" (default) | "pro_rata". See
            labor_constrained_fulfillment(). Ignored when available_labor_eoh
            is None.

    Returns:
        dict: {
          "epsilon":                  float,
          "total_eoh":                float,
          "eoh_by_domain":            dict,   (personal/infrastructure/ecological/knowledge)
          "human_eoh":                float,  (total across all domains)
          "human_fraction":           float,  (human EOH / gross EOH)
          "uniform_split_factor":     float,  (= 1 - c)
          "registration_share":       float,  (effective composite: registered/human)
          "registration_by_domain":   dict,   (personal: float, non_personal: float)
          "registered_eoh":           float,  (total)
          "registered_eoh_by_domain": dict,   (personal: float, non_personal: float)
          "mean_multiplier":          float,
          "teh_created":              float,
          "capital_eoh_eliminated":        float,
          "capital_personal_eoh_fulfilled": float,
          "deficit":              dict | None,  (full labor_constrained_fulfillment result)
          "deferred_personal":    float,  (0.0 when unconstrained)
          "deferred_total":       float,
          "labor_constrained":    bool,
          "fulfillment_coverage": float,  (1.0 when unconstrained)
        }

    Governing equation (compound over four domains):

        TEH = [Σ_domain  EOH_domain × (1−ε) × reg_share_domain(ε)] × m̄

    where reg_share_domain differs by domain (personal uses demand registration;
    infrastructure/ecological/knowledge use the labor composite).

    As ε rises from 0 to 1, total_eoh grows (more complex civilization) but
    human_eoh = total_eoh × (1−ε) falls; registered EOH first rises then falls
    as registration rates saturate; TEH_created peaks near mid-arc and collapses
    as ε → 1 (machines handle almost everything).

    Worked example at ε=0.40 (canonical defaults, population=1M, m̄=2.10):
        total_eoh   = 2,353M h/yr
        human_eoh   = 2,353M × 0.60         = 1,412M h/yr  (1−ε share)
        personal reg = 313M × 0.141         =    44M h/yr  (demand sigmoid pers_reg(0.40)=0.141)
        non-pers reg = 1,098M × 0.592       =   191M h/yr  (labor sigmoid np_reg(0.40)=0.592)
        registered  =   44M + 191M          =   235M h/yr
        TEH_created = 235M × 2.10           =   494M TEH/yr

    For comparison:
        ε=0.00: total=2,288M, human=2,288M, reg=33M, TEH=70M  (near-zero personal reg)
        ε=0.90: total=2,432M, human=243M,   reg=199M, TEH=419M (high reg, low human supply)

    Reference: Mission Statement §"EOH as demand signal" — the pipeline from
    physical obligation to currency creation must be transparent and auditable.
    """
    from hours_eoh.core.eoh_generation import total_eoh as _total_eoh
    from hours_eoh.core.registration import (
        total_registration_share,
        personal_eoh_registration_share as _personal_reg_share,
    )

    # Resolve the two names for the capability index back into one local, so the
    # body below is unchanged and there is exactly one place the precedence lives.
    epsilon = _resolve_capability(epsilon, machine_capability)

    eoh_dict = _total_eoh(
        epsilon=epsilon,
        population=population,
        age_distribution=age_distribution,
        capital_stock=capital_stock,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        deferred_ecological=deferred_ecological,
        knowledge_complexity=knowledge_complexity,
        skill_decay_rate=skill_decay_rate,
        capital_eoh_eliminated=capital_eoh_eliminated,
        capital_personal_eoh_fulfilled=capital_personal_eoh_fulfilled,
        infrastructure_compounding_eoh=infrastructure_compounding_eoh,
        competency_gap_factor=competency_gap_factor,
        monitoring_capability=monitoring_capability,
        knowledge_complexity_per_unit=knowledge_complexity_per_unit,
        thermal_obligation=thermal_obligation,
        personal_base=personal_base,
        personal_standard=personal_standard,
        infra_maint_rate=infra_maint_rate,
        # Both stay None-able and are forwarded as-is: total_eoh refuses the
        # both-supplied combination and resolves neither-supplied to the shipped
        # anchor exactly. Resolving either of them here would put that precedence
        # in two places.
        ecological_base=ecological_base,
        ecological_area_hectares=ecological_area_hectares,
        ecological_intensity=ecological_intensity,
        ecological_hectares_per_capita=ecological_hectares_per_capita,
        restoration_obligation=restoration_obligation,
        ecological_health_response=ecological_health_response,
        ecological_standing_response=ecological_standing_response,
        knowledge_base=knowledge_base,
    )

    # Per-domain human EOH via the existing helper
    hd                 = human_eoh_per_domain(
        eoh_dict, epsilon, automation_response=automation_response
    )
    personal_eoh_val   = eoh_dict["personal"]

    # THE OBSERVED MACHINE SHARE, CAPTURED BEFORE THE LABOUR CONSTRAINT.
    # A labour shortfall is DEFERRED, not machine-fulfilled, so computing the
    # share after rationing would credit machines with obligation that simply
    # went unserved. What machines take does not depend on whether the people
    # exist to do the rest.
    epsilon_observed   = hd["epsilon_observable"]

    # Labor constraint (opt-in). Without it the pipeline assumes every hour of
    # human-carried EOH gets worked — a demand figure reported as fulfillment.
    # With it, registration operates on SERVED EOH, so labor that does not exist
    # cannot mint TEH, and the shortfall is reported rather than absorbed.
    deficit: dict | None = None
    if available_labor_eoh is not None:
        deficit = labor_constrained_fulfillment(hd, available_labor_eoh, rationing)
        served = deficit["served_by_domain"]
        hd = {**hd, **served, "total": deficit["served_total"]}

    human_personal     = hd["personal"]
    human_non_personal = hd["infrastructure"] + hd["ecological"] + hd["knowledge"]
    human_total        = hd["total"]

    # Per-domain registration (M5):
    # - Personal: demand registration (what fraction of biological obligation
    #   is collectively recognised). Near-zero at ε=0; ~0.95 by ε=0.99.
    # - Infrastructure + Ecological: labor registration composite
    #   (care/production/stewardship), physical outputs are directly inspectable.
    # - Knowledge: separate verification-difficulty sigmoid — knowledge outputs
    #   lack physical indicators; inflection at ε=0.70, saturation at 0.80.
    # When registration_share is provided, it overrides ALL domains uniformly.
    from hours_eoh.core.registration import knowledge_eoh_registration_share as _know_reg_share
    if registration_share is not None:
        pers_share   = registration_share
        infra_share  = registration_share
        eco_share    = registration_share
        know_share   = registration_share
    else:
        pers_share  = (personal_registration_share
                       if personal_registration_share is not None
                       else _personal_reg_share(epsilon))
        infra_share = eco_share = total_registration_share(epsilon)
        know_share  = _know_reg_share(epsilon)

    human_infra    = hd["infrastructure"]
    human_eco      = hd["ecological"]
    human_know     = hd["knowledge"]

    reg_personal = registered_eoh(human_personal, pers_share)
    reg_infra    = registered_eoh(human_infra,    infra_share)
    reg_eco      = registered_eoh(human_eco,      eco_share)
    reg_know     = registered_eoh(human_know,     know_share)
    reg_total    = reg_personal + reg_infra + reg_eco + reg_know

    # Backward-compatible aggregates for callers that use the personal/non_personal split
    reg_non_personal = reg_infra + reg_eco + reg_know
    # Composite non-personal share (weighted by human EOH volume)
    non_pers_share   = reg_non_personal / max(human_non_personal, 1.0)

    # Effective composite registration share for backward-compatible reporting
    effective_share  = reg_total / max(human_total, 1.0)

    teh = teh_created(reg_total, mean_multiplier)

    return {
        "epsilon":           epsilon,
        # The same value as "epsilon", said honestly: this is what machines CAN
        # take. "epsilon_observable" is what the split implies they DID take, and
        # after Phase 2 the two differ. Quoting the first as an outcome is the
        # defect this pair exists to prevent.
        "machine_capability":  epsilon,
        "epsilon_observable":  epsilon_observed,
        "total_eoh":         eoh_dict["total"],
        "eoh_by_domain": {
            "personal":       personal_eoh_val,
            "infrastructure": eoh_dict["infrastructure"],
            "ecological":     eoh_dict["ecological"],
            "knowledge":      eoh_dict["knowledge"],
        },
        "human_eoh":          human_total,
        # See the split helper: this is the share people CARRY, not the
        # split factor. They differ once any domain has an automation floor,
        # and reporting the factor under this name understated human labour
        # by 5.8x at the top of the arc.
        "human_fraction":     (human_total / eoh_dict["total"]
                               if eoh_dict["total"] > 0.0 else 0.0),
        "uniform_split_factor": 1.0 - epsilon,
        "registration_share": effective_share,
        "registration_by_domain": {
            "personal":       pers_share,
            "infrastructure": infra_share,
            "ecological":     eco_share,
            "knowledge":      know_share,
            "non_personal":   non_pers_share,   # backward compat
        },
        "registered_eoh":     reg_total,
        "registered_eoh_by_domain": {
            "personal":       reg_personal,
            "infrastructure": reg_infra,
            "ecological":     reg_eco,
            "knowledge":      reg_know,
            "non_personal":   reg_non_personal,  # backward compat
        },
        "mean_multiplier":    mean_multiplier,
        "teh_created":        teh,
        "capital_eoh_eliminated":         capital_eoh_eliminated,
        "capital_personal_eoh_fulfilled":  capital_personal_eoh_fulfilled,
        # Labor constraint. None when available_labor_eoh was not supplied —
        # the pipeline then assumes full fulfillment, as it always has.
        "deficit":            deficit,
        "deferred_personal":  (deficit["deferred_personal"] if deficit else 0.0),
        "deferred_total":     (deficit["deferred_total"] if deficit else 0.0),
        "labor_constrained":  bool(deficit["labor_constrained"]) if deficit else False,
        "fulfillment_coverage": (deficit["coverage"] if deficit else 1.0),
    }
