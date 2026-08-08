"""
The labor-feasibility ceiling — is PERSONAL_EOH_BASE over-determined?

An EOH demand is a claim about hours that must be worked. At ε = 0 no machine
carries any of it, so every one of those hours must come out of a living human's
year. That gives a hard upper bound the demand side cannot exceed, and it is
computable from constants the repo already ships.

    GOVERNING RELATIONS

    supply per capita       L = c · a
        c   adult annual labor capacity (h/yr·adult)
        a   adult share of population (dimensionless)

    demand per capita       D(ε) = (1 − ε) · [ w · B  +  R ]
        B   PERSONAL_EOH_BASE, h/yr per working-age-EQUIVALENT
        w   Σ(fraction × eoh_weight) over AGE_GROUPS = 1.475 — the age weighting
            that converts B from per-equivalent to per-capita
        R   infrastructure + ecological + knowledge EOH per capita
        ε   machine-fulfilled share; (1 − ε) is what humans must carry

    feasibility             D(ε) ≤ L
    the implied ceiling     B ≤ (L/(1−ε) − R) / w

The last line is the test. It does not ask whether 1,500 h/yr "feels right"; it
asks what value of B is COMPATIBLE with the labor supply the same model assumes.

WHY THE AGE WEIGHTING MATTERS AND IS EASY TO MISS. `PERSONAL_EOH_BASE` is *not*
per capita — it is per working-age-equivalent, and infants (3.0×) and elderly
(2.5×) are weighted above 1.0. The population-weighted mean w = 1.475, so a base
of 1,500 asserts **2,213 h/person·yr** of entropy-resistance labor. And because
the extra weight on infants and elderly is CAREGIVER labor, all 2,213 hours must
still be supplied by adults — the weighting raises demand without raising supply.
Any feasibility test run against the 1,500 figure understates the gap by 1.475×.

WHAT THE TEST FINDS (see `over_determination_report`). Using nothing but the
repo's own constants — H_REF = 2,000 h/yr and workforce_fraction = 0.5, giving
L = 1,000 h/person·yr — demand at ε = 0 exceeds supply by **2.29×**. Under
subsistence-population parameters (adult share 0.55–0.60, ethnographic adult
labor budgets below the modern 2,080-hour reference) the ratio runs 1.5–3.5×.
There is no parameter choice in the plausible range that closes it.

WHAT IS AND IS NOT SHOWN. This does not falsify 1,500 in isolation — feasibility
is a joint property. The finding is that the PAIR

    (PERSONAL_EOH_BASE = 1500,  H_REF × workforce_fraction = 1000)

cannot both hold. Closing the gap by raising supply instead requires adults to
work ≈ 3,850 h/yr — 10.5 h/day, every day, with no rest days — which is not a
labor budget any observed subsistence population sustains. So the resolution has
to come mostly from the demand side, and `implied_base_ceiling` says where.

RELATION TO THE SURVIVAL FLOOR. `research/corridor.survival_floor_epsilon` has
been computing this shortfall all along and reporting ε_suff ≈ 0.53 at shipped
defaults — i.e. the framework's own instrument says "subsistence" needs 53%
automation to survive. This module makes that reading explicit and inverts it
onto the constant responsible.

Layer: scenarios/ — imports core/ and data.py only. Pure, no I/O.
ε-coherence: the ceiling is evaluated across the arc; it binds hardest at ε = 0
(humans carry everything) and relaxes as machines take share, which is exactly
the direction that makes ε = 0 the diagnostic point.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import AGE_GROUPS, H_REF, PERSONAL_EOH_BASE

# Ethnographic / subsistence-demography reference band, used for the sweep.
# Adult share: high-fertility age structures run a smaller working-age share than
# the OECD-shaped 0.60 default in AGE_GROUPS.
SUBSISTENCE_ADULT_SHARE_BAND: tuple[float, float] = (0.55, 0.60)
# Adult annual labor capacity: total work (subsistence + domestic + manufacture),
# bracketing well below and modestly above the modern 2,080-hour reference so the
# test cannot be accused of assuming its conclusion.
SUBSISTENCE_CAPACITY_BAND: tuple[float, ...] = (1200.0, 1500.0, 1800.0, 2080.0, 2600.0)


def age_weight_mean(age_groups: dict[str, dict] | None = None) -> float:
    """
    w = Σ(fraction × eoh_weight) — converts PERSONAL_EOH_BASE from per
    working-age-equivalent to per capita.

    units: dimensionless. Default AGE_GROUPS gives w = 1.475.
    ε-behavior: constant in ε (the age structure drifts with ε only through
    ELDERLY_EOH_EPSILON_FACTOR, which this reference form deliberately ignores so
    the ceiling is a clean function of the shipped weights).
    """
    groups = AGE_GROUPS if age_groups is None else age_groups
    return sum(g["fraction"] * g["eoh_weight"] for g in groups.values())


def labor_supply_per_capita(
    adult_capacity_h_yr: float = float(H_REF),
    adult_share: float | None = None,
) -> float:
    """
    L = c · a — annual human labor available per head of population.

    Args:
        adult_capacity_h_yr: Hours per year one adult can devote to
            entropy-resistance labor (> 0).
        adult_share: Fraction of the population able to supply it. None (default)
            reads the working-age fraction from AGE_GROUPS (0.60).

    Returns:
        L in h/person·yr.

    Raises:
        ValueError: on non-positive capacity or a share outside (0, 1].

    Worked example: 2,000 h/yr × 0.60 = 1,200 h/person·yr. The repo's own
    workforce_fraction of 0.50 gives 1,000.
    """
    share = AGE_GROUPS["working_age"]["fraction"] if adult_share is None else adult_share
    if adult_capacity_h_yr <= 0.0:
        raise ValueError(
            f"adult_capacity_h_yr must be > 0, got {adult_capacity_h_yr}"
        )
    if not 0.0 < share <= 1.0:
        raise ValueError(f"adult_share must be in (0, 1], got {share}")
    return adult_capacity_h_yr * share


class FeasibilityCheck(TypedDict):
    epsilon: float
    supply_per_capita: float          # L
    personal_demand_per_capita: float # w·B·(1−ε)
    residual_per_capita: float        # R·(1−ε), the non-personal domains
    total_demand_per_capita: float    # D(ε)
    demand_supply_ratio: float        # D/L — > 1 means infeasible
    feasible: bool
    implied_base_ceiling: float       # the largest B compatible with L at this ε
    shipped_base: float
    base_overshoot: float             # shipped_base / implied_base_ceiling
    hours_per_adult_required: float   # what closing the gap on the SUPPLY side costs
    deficit_share: float              # what closing NEITHER side implies: unmet obligation


def feasibility_check(
    adult_capacity_h_yr: float = float(H_REF),
    adult_share: float | None = None,
    epsilon: float = 0.0,
    population: float = 1_000_000.0,
    personal_base: float = PERSONAL_EOH_BASE,
) -> FeasibilityCheck:
    """
    Test D(ε) ≤ L and invert it onto PERSONAL_EOH_BASE.

    THREE resolutions exist and the report prices all of them, because choosing
    between them is a theory decision and not an arithmetic one:

    1. **Lower demand** — `implied_base_ceiling` is the largest base compatible
       with the stated supply, `base_overshoot` how far the shipped constant
       exceeds it.
    2. **Raise supply** — `hours_per_adult_required` is what the same population
       would have to work. At shipped constants this is 10.5–12.5 h/day with no
       rest days, which no observed subsistence population sustains.
    3. **Accept the gap as real** — `deficit_share` is the fraction of the
       obligation left UNMET. This is the resolution that defends the shipped
       constant, and it is not absurd: EOH is what entropy *demands*, not what
       got done, and a population that fails to meet it does not violate
       arithmetic — it experiences the shortfall as morbidity and mortality. On
       that reading ε = 0 is genuinely infeasible *as a fully-served state*, and
       the defect is in the documentation ("ε = 0 is subsistence") rather than in
       the constant.

    Resolution 3 is a substantive empirical claim — at shipped constants it
    asserts that 41–62% of the personal entropy obligation goes permanently
    unserved even in a capital-rich society. That may be partly true. It should
    be *stated* and defended, not carried silently inside a constant, which is
    the only thing this module insists on.

    units: all per-capita quantities in h/person·yr; ratios dimensionless.
    ε-behavior: human-carried demand scales with (1 − ε) while supply does not,
    so the ratio falls monotonically across the arc and the test is hardest at
    ε = 0. At ε → 1 any base is feasible, which is why ε = 0 is the diagnostic.

    Args:
        adult_capacity_h_yr: Adult annual labor capacity (> 0).
        adult_share: Adult share of population. None → AGE_GROUPS working_age.
        epsilon: Automation level ∈ [0, 1).
        population: Population used to take the per-capita EOH inventory.
        personal_base: The base under test. Defaults to the shipped constant.

    Returns:
        FeasibilityCheck.

    Raises:
        ValueError: if epsilon is outside [0, 1) or population is non-positive.

    Worked example (shipped defaults, adult_capacity = 2,000, share = 0.60,
    ε = 0): supply 1,200; personal demand 2,213; ratio 1.91; implied base
    ceiling 762; overshoot 1.97×; closing it on the supply side would need
    3,814 h/yr per adult.
    """
    if not 0.0 <= epsilon < 1.0:
        raise ValueError(f"epsilon must be in [0, 1), got {epsilon}")
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")

    share = AGE_GROUPS["working_age"]["fraction"] if adult_share is None else adult_share
    supply = labor_supply_per_capita(adult_capacity_h_yr, share)
    w = age_weight_mean()

    inv = total_eoh(epsilon=epsilon, population=population,
                    personal_base=personal_base)
    human = 1.0 - epsilon
    personal_pc = inv["personal"] / population * human
    residual_pc = ((inv["infrastructure"] + inv["ecological"] + inv["knowledge"])
                   / population * human)
    demand_pc = personal_pc + residual_pc

    # B ≤ (L/(1−ε) − R) / w, floored at 0 — a negative ceiling means the
    # non-personal domains alone already exhaust the labor supply.
    ceiling = max(0.0, (supply / human - residual_pc / human) / w)

    return FeasibilityCheck(
        epsilon=epsilon,
        supply_per_capita=supply,
        personal_demand_per_capita=personal_pc,
        residual_per_capita=residual_pc,
        total_demand_per_capita=demand_pc,
        demand_supply_ratio=demand_pc / supply if supply > 0 else float("inf"),
        feasible=demand_pc <= supply,
        implied_base_ceiling=ceiling,
        shipped_base=personal_base,
        base_overshoot=(personal_base / ceiling if ceiling > 0 else float("inf")),
        hours_per_adult_required=demand_pc / share if share > 0 else float("inf"),
        deficit_share=(max(0.0, demand_pc - supply) / demand_pc
                       if demand_pc > 0 else 0.0),
    )


class OverDeterminationReport(TypedDict):
    self_consistency: FeasibilityCheck      # the repo against its OWN supply constants
    subsistence_cases: list[FeasibilityCheck]
    worst_ratio: float
    best_ratio: float
    ceiling_band: tuple[float, float]       # implied base ceiling across the sweep
    feasible_anywhere: bool
    over_determined: bool
    verdict: str


def over_determination_report(
    capacities: tuple[float, ...] = SUBSISTENCE_CAPACITY_BAND,
    shares: tuple[float, float] = SUBSISTENCE_ADULT_SHARE_BAND,
    workforce_fraction: float = 0.5,
) -> OverDeterminationReport:
    """
    The full test: is (PERSONAL_EOH_BASE, labor supply) an over-determined pair?

    Two arms, and the first is the one that matters:

    1. **Self-consistency.** The repo's own supply constants — H_REF = 2,000 and
       `workforce_fraction` = 0.5, the same 1e9-for-1M figure the corridor tests
       use as `available_labor_eoh` — against its own demand constants. No
       external data, no ethnography, no judgement call. If this arm fails, the
       model contradicts itself and nothing about the outside world is at issue.
    2. **Subsistence sweep.** The plausible range for a pre-automation
       population: adult shares 0.55–0.60 and adult capacities from 1,200 to
       2,600 h/yr. Deliberately generous at the top end — 2,600 h/yr exceeds the
       modern full-time reference — so the conclusion cannot rest on a stingy
       assumption.

    `over_determined` is True when the self-consistency arm fails, because that
    is the claim that stands without appeal to any outside source.

    Args:
        capacities: Adult annual labor capacities to sweep.
        shares: (low, high) adult population shares.
        workforce_fraction: The repo's own labor-participation parameter, used
            for the self-consistency arm.

    Returns:
        OverDeterminationReport.
    """
    self_arm = feasibility_check(
        adult_capacity_h_yr=float(H_REF), adult_share=workforce_fraction, epsilon=0.0,
    )
    cases = [
        feasibility_check(adult_capacity_h_yr=c, adult_share=s, epsilon=0.0)
        for c in capacities for s in shares
    ]
    ratios = [c["demand_supply_ratio"] for c in cases]
    ceilings = [c["implied_base_ceiling"] for c in cases]
    feasible_anywhere = any(c["feasible"] for c in cases)
    over = not self_arm["feasible"]

    if over:
        verdict = (
            f"OVER-DETERMINED. On the repo's own constants (H_REF={H_REF:g} × "
            f"workforce_fraction={workforce_fraction:g} = "
            f"{self_arm['supply_per_capita']:.0f} h/person·yr), demand at ε=0 is "
            f"{self_arm['total_demand_per_capita']:.0f} — a factor of "
            f"{self_arm['demand_supply_ratio']:.2f}. PERSONAL_EOH_BASE would have "
            f"to be ≤ {self_arm['implied_base_ceiling']:.0f} to be compatible "
            f"(shipped {self_arm['shipped_base']:.0f}, overshoot "
            f"{self_arm['base_overshoot']:.2f}×), or adults would have to work "
            f"{self_arm['hours_per_adult_required']:.0f} h/yr "
            f"({self_arm['hours_per_adult_required'] / 365:.1f} h/day, every day), "
            f"or {self_arm['deficit_share']:.0%} of the obligation must be accepted "
            f"as permanently UNMET. "
            f"Across the subsistence sweep the ratio runs "
            f"{min(ratios):.2f}–{max(ratios):.2f}× and the implied ceiling "
            f"{min(ceilings):.0f}–{max(ceilings):.0f} h/yr. The pair cannot both "
            f"hold; ε = 0 is not a feasible state of this model."
        )
    else:
        verdict = (
            f"CONSISTENT on the repo's own constants (ratio "
            f"{self_arm['demand_supply_ratio']:.2f}). Subsistence sweep ratio "
            f"{min(ratios):.2f}–{max(ratios):.2f}×."
        )

    return OverDeterminationReport(
        self_consistency=self_arm,
        subsistence_cases=cases,
        worst_ratio=max(ratios),
        best_ratio=min(ratios),
        ceiling_band=(min(ceilings), max(ceilings)),
        feasible_anywhere=feasible_anywhere,
        over_determined=over,
        verdict=verdict,
    )


def feasible_epsilon(
    adult_capacity_h_yr: float = float(H_REF),
    adult_share: float | None = None,
    personal_base: float = PERSONAL_EOH_BASE,
    population: float = 1_000_000.0,
    tol: float = 1e-6,
) -> float:
    """
    The lowest ε at which the demand becomes carryable — the feasibility floor.

    Solved by bisection on D(ε) ≤ L rather than in closed form, and the reason is
    itself a finding: the naive inversion

        ε_feas ≈ 1 − L / D(0)              [WRONG — understates it]

    assumes the EOH inventory is fixed and automation merely takes share of it.
    It is not fixed. Infrastructure EOH RISES with ε (75 → 224 h/person·yr from
    ε = 0 to 0.99) because automation is capital, and capital has to be
    maintained; knowledge EOH rises too. So automation both relieves demand and
    creates it, and the true crossover sits above the linear estimate. On shipped
    constants the closed form gives 0.563 and the actual crossover is ≈ 0.58 —
    small here only because the domains that grow are the small ones.

    Cross-check: `research/corridor.survival_floor_epsilon` reports the same
    shortfall scoped to the personal domain alone, and lands just below this. A
    non-zero value either way is the model stating that its own ε = 0 endpoint —
    documented as "subsistence" — requires automation to reach.

    units: dimensionless ε ∈ [0, 1). Returns 0.0 when ε = 0 is already feasible,
    and 1.0 − tol when no ε on the arc carries the demand.

    Args:
        adult_capacity_h_yr: Adult annual labor capacity (> 0).
        adult_share: Adult share of population. None → AGE_GROUPS working_age.
        personal_base: The base under test.
        population: Population for the per-capita inventory.
        tol: Bisection tolerance on ε.

    Returns:
        The feasibility floor ε_feas.
    """
    def ok(eps: float) -> bool:
        return feasibility_check(adult_capacity_h_yr, adult_share, eps,
                                 population, personal_base)["feasible"]

    if ok(0.0):
        return 0.0
    hi = 1.0 - tol
    if not ok(hi):
        return hi
    lo = 0.0
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if ok(mid):
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------------------
# Identification — breaking the circularity
# ---------------------------------------------------------------------------

class BaseIdentification(TypedDict):
    machine_eoh_per_capita: float     # M — from capital, B-free
    human_eoh_per_capita: float       # H — from time use, measured
    residual_per_capita: float        # R — non-personal domains, B-free
    implied_base: float               # B = (M + H − R) / w
    implied_epsilon: float            # ε = M / (M + H), the by-product
    assumes_zero_deficit: bool        # always True — see the docstring
    note: str


def identify_base(
    machine_eoh_per_capita: float,
    observed_human_hours_per_capita: float,
    residual_per_capita: float | None = None,
    population: float = 1_000_000.0,
) -> BaseIdentification:
    """
    Identify PERSONAL_EOH_BASE from the accounting identity, without circularity.

        D = M + H            total obligation = machine-served + human-served
        D = w·B + R          the model's own decomposition
        ⇒ B = (M + H − R) / w
        ⇒ ε = M / (M + H)    falls out as a BY-PRODUCT, not an input

    WHY THIS IS NOT CIRCULAR. The trap is calibrating B from observed hours
    alone: that sets D := L, which forces demand/supply ≡ 1 and ε_personal ≡ 0 by
    construction, and makes `feasibility_check` vacuous. The identity avoids it
    because M comes from a *different* measurement — a capital inventory scored
    against CAPITAL_MACHINE_PROFILES elimination rates — and M does not depend on
    B at any point. Two independent instruments, one unknown.

    THE ONE ASSUMPTION, AND IT IS THE WHOLE RESIDUAL RISK: `D = M + H` says every
    hour of obligation is served by a machine or a human. If a society leaves
    part of it unserved, the true D is M + H + deficit, so this returns a LOWER
    BOUND on B. That has a counter-intuitive consequence for where to calibrate:

      - The ε ≈ 0 anchor society FIXES THE ENDPOINT cleanly (zero machine capital
        ⇒ ε = 0 whatever B is — verified, the endpoint is B-free). But it is the
        WORST place to measure B, because its unserved deficit is largest and
        least observable: it is paid in infant mortality and shortened life, not
        recorded in a time-use diary.
      - A capital-rich society is the BEST place to measure B, because its
        deficit is smallest — the opposite of the intuition that says to
        calibrate a subsistence constant on subsistence data.

    Pair this lower bound with `feasibility_check`'s `implied_base_ceiling`
    (an upper bound from the supply side) and B is bracketed from both directions
    by independent routes.

    units: all inputs and outputs h/person·yr except the dimensionless ε.

    Args:
        machine_eoh_per_capita: M, e.g. from
            core.civilization.machine_eoh_from_capital(...)["machine_eoh_total"]
            divided by population. B-free by construction.
        observed_human_hours_per_capita: H, from time-use measurement, summed
            over all four domains and expressed per head of POPULATION (not per
            adult — multiply per-adult hours by the adult share first).
        residual_per_capita: R, the non-personal domains. None → read from
            total_eoh() at the shipped constants (they do not depend on B).
        population: Population for the residual inventory.

    Returns:
        BaseIdentification.

    Raises:
        ValueError: on negative inputs or a non-positive population.

    Worked example: a standard-tier capital inventory gives M ≈ 266 h/person·yr;
    time use of 2.8 h/adult·day at a 0.60 adult share gives H ≈ 613; R ≈ 76. Then
    B = (266 + 613 − 76)/1.475 ≈ 544 and ε ≈ 0.30. Compare the shipped 1,500.
    """
    if machine_eoh_per_capita < 0.0 or observed_human_hours_per_capita < 0.0:
        raise ValueError("M and H must be ≥ 0")
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")

    if residual_per_capita is None:
        inv = total_eoh(epsilon=0.0, population=population)
        residual_per_capita = ((inv["infrastructure"] + inv["ecological"]
                                + inv["knowledge"]) / population)

    w = age_weight_mean()
    d = machine_eoh_per_capita + observed_human_hours_per_capita
    implied = max(0.0, (d - residual_per_capita) / w)
    eps = machine_eoh_per_capita / d if d > 0 else 0.0

    return BaseIdentification(
        machine_eoh_per_capita=machine_eoh_per_capita,
        human_eoh_per_capita=observed_human_hours_per_capita,
        residual_per_capita=residual_per_capita,
        implied_base=implied,
        implied_epsilon=eps,
        assumes_zero_deficit=True,
        note=(f"B ≥ {implied:.0f} h/yr (LOWER bound — any unserved obligation "
              f"raises it). ε = {eps:.3f} falls out as a by-product. Pair with "
              f"feasibility_check().implied_base_ceiling for the upper bound."),
    )


def implied_human_hours(
    machine_eoh_per_capita: float,
    personal_base: float = PERSONAL_EOH_BASE,
    adult_share: float | None = None,
    population: float = 1_000_000.0,
) -> dict:
    """
    The overidentifying test: fix B, and the human-hours residual becomes a
    FALSIFIABLE PREDICTION at every capital stock.

        H(K) = w·B + R − M(K)

    This is what the framework currently lacks — a claim time-use data can
    refute. A fixed B implies a whole trajectory of hours-per-adult-per-day
    across development levels, and cross-cultural time allocation data measures
    exactly that. At B = 1,500 the prediction is 7.1 h/day of entropy-resistance
    labour per adult in an advanced-capital society and 10.0 h/day in a
    basic-capital one; no time-use survey reports figures near the former.

    A second, sharper use: run it PER DOMAIN. The model asserts the machine share
    (1 − ε) applies uniformly across all four domains
    (`core.eoh_fulfillment.human_eoh_per_domain`). If per-domain time-use data
    implies different ε by domain, that uniformity is falsified — which is
    exactly the ε-as-a-vector question (§12.1), currently sign-off-gated and
    argued on theory grounds alone. This turns it into a measurement.

    units: h/person·yr and h/adult·day.

    Args:
        machine_eoh_per_capita: M at the capital stock being predicted for.
        personal_base: The B whose prediction is being tested.
        adult_share: For the per-adult-per-day conversion. None → AGE_GROUPS.
        population: Population for the residual inventory.

    Returns:
        dict with human_per_capita, human_per_adult_year, human_per_adult_day,
        personal_base, machine_eoh_per_capita.
    """
    share = AGE_GROUPS["working_age"]["fraction"] if adult_share is None else adult_share
    inv = total_eoh(epsilon=0.0, population=population, personal_base=personal_base)
    residual = ((inv["infrastructure"] + inv["ecological"] + inv["knowledge"])
                / population)
    demand = age_weight_mean() * personal_base + residual
    h_pc = max(0.0, demand - machine_eoh_per_capita)
    per_adult_yr = h_pc / share if share > 0 else float("inf")
    return {
        "human_per_capita": h_pc,
        "human_per_adult_year": per_adult_yr,
        "human_per_adult_day": per_adult_yr / 365.0,
        "personal_base": personal_base,
        "machine_eoh_per_capita": machine_eoh_per_capita,
    }
