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
        w   Σ(fraction × eoh_weight) over AGE_GROUPS = 1.3528 — the age weighting
            that converts B from per-equivalent to per-capita
        R   infrastructure + ecological + knowledge EOH per capita
        ε   machine-fulfilled share; (1 − ε) is what humans must carry

    feasibility             D(ε) ≤ L
    the implied ceiling     B ≤ (L/(1−ε) − R) / w

The last line is the test. It does not ask whether 1,500 h/yr "feels right"; it
asks what value of B is COMPATIBLE with the labor supply the same model assumes.

WHY THE AGE WEIGHTING MATTERS AND IS EASY TO MISS. `PERSONAL_EOH_BASE` is *not*
per capita — it is per working-age-equivalent, and infants (3.0×) and elderly
(1.48×) are weighted above 1.0. The population-weighted mean w = 1.3528, so a
base of 1,500 asserts **2,029 h/person·yr** of entropy-resistance labor. And
because the extra weight on infants and elderly is CAREGIVER labor, all 2,029
hours must still be supplied by adults — the weighting raises demand without
raising supply. Any feasibility test run against the 1,500 figure understates
the gap by 1.3528×.

WHAT THE TEST FINDS (see `over_determination_report`). Using nothing but the
repo's own constants — H_REF = 2,080 h/yr and workforce_fraction = 0.5, giving
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
from hours_eoh.data import (
    AGE_GROUPS, H_REF, MEASURED_CAPACITY_H_YR, PERSONAL_EOH_BASE,
    PHYSICAL_CAPACITY_CEILING_H_YR, REFERENCE_FRAME_POPULATION,
    CAPACITY_MEASUREMENT_BAND,
)
from hours_eoh.reference import mtus_time_use as mtus

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

    units: dimensionless. Default AGE_GROUPS gives w = 1.3528.

    THESE FIGURES WERE RESTATED IN PROSE AND THAT IS WHY THEY WENT STALE. w was
    written as 1.475 in five places in this module and was 1.3528 live — stale
    since the AGE_WEIGHT_CHILD revalue, not since anything that touched this
    file, so nothing here would ever have caught it.
    `tests/scenarios/test_feasibility.py::TestTheDocumentedFiguresAreLive`
    fails if they diverge again.
    ε-behavior: constant in ε (the age structure drifts with ε only through
    the retired elderly ε-drift, which this reference form always ignored, so
    the ceiling is a clean function of the shipped weights).
    """
    groups = AGE_GROUPS if age_groups is None else age_groups
    return sum(g["fraction"] * g["eoh_weight"] for g in groups.values())


def capacity_weighted_adult_share() -> float:
    """
    a = Σ_g fraction_g · capacity_weight_g — the supply-side mirror of the
    obligation's age weighting.

    WHY THIS IS DERIVED AND NOT READ OFF ONE GROUP. `AGE_GROUPS` weights how
    much obligation each age group GENERATES (infant 3.0, elderly 1.48). Until
    2026-09-04 supply was the bare `working_age` fraction, which asserted that
    the elderly supply exactly zero while generating 1.48x the obligation —
    true of the arithmetic, stated nowhere. It also stood as a literal in THREE
    functions here, so the assertion was made three times and bound nowhere.

    Deriving it changes no number — the shipped capacity weights give 0.60
    exactly — and changes one behaviour: a shift in the age distribution now
    moves supply and demand TOGETHER. `demographic_shock` moved only demand.

    The weights are `placeholder`, `errs: LOW`: child and elderly are zero to
    preserve the shipped arithmetic, not because zero was measured, so this
    share is a LOWER bound on what a population can supply.
    """
    return sum(g["fraction"] * g["capacity_weight"] for g in AGE_GROUPS.values())


def labor_supply_per_capita(
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    adult_share: float | None = None,
) -> float:
    """
    L = c · a — annual human labor available per head of population.

    Args:
        adult_capacity_h_yr: Hours per year one adult can devote to
            entropy-resistance labor. Must be > 0 and at most
            PHYSICAL_CAPACITY_CEILING_H_YR — a person cannot supply more
            labour than time elapses. Defaults to MEASURED_CAPACITY_H_YR, the
            median of 50 measured MTUS frames; supply your own, because the
            measured spread across frames is 1.55x.
        adult_share: Fraction of the population able to supply it. None (default)
            derives it from the per-age `capacity_weight` in AGE_GROUPS via
            `capacity_weighted_adult_share()` — 0.60 on the shipped weights,
            and a LOWER bound, because child and elderly weights are zero by
            admission rather than by measurement.

    Returns:
        L in h/person·yr.

    Raises:
        ValueError: on non-positive capacity or a share outside (0, 1].

    Worked example: the shipped default 2,335.75 h/yr × 0.60 = 1,401.5
    h/person·yr. At the retired H_REF default of 2,080 it was 1,248.0.
    """
    share = capacity_weighted_adult_share() if adult_share is None else adult_share
    if adult_capacity_h_yr <= 0.0:
        raise ValueError(
            f"adult_capacity_h_yr must be > 0, got {adult_capacity_h_yr}"
        )
    if adult_capacity_h_yr > PHYSICAL_CAPACITY_CEILING_H_YR:
        # The calendar bound, not an endurance one. Nothing sustains anywhere
        # near this — the highest measured frame is 3,035 h/adult-yr, 34.6% of
        # it — so an input above this is an arithmetic slip, not an economy.
        raise ValueError(
            f"adult_capacity_h_yr={adult_capacity_h_yr} exceeds the hours that "
            f"elapse in a year ({PHYSICAL_CAPACITY_CEILING_H_YR}); a person "
            "cannot supply more labour than time passes"
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


def demographic_margin(
    epsilon: float = 0.0,
    population: float = REFERENCE_FRAME_POPULATION,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
) -> dict[str, float]:
    """
    How far the population is from the point where it cannot maintain itself.

    WHY A MARGIN AND NOT A FLOOR. The survival floor is a STEP in one ratio,
    not a curve. Personal obligation per capita is near-flat in ε (1,352.8 at
    ε=0 against 1,351.1 at ε=0.9), so ε_suff is 0 while supply covers demand
    and rises only once it does not. Reporting "ε_suff = 0.000, nothing binds"
    is true and says nothing about how close the step is: on the shipped
    demography the answer is **2.13 percentage points of adult share**.

    The critical share is a·crit = P/c — the adult share at which capacity
    exactly meets the personal obligation. Below it the population cannot
    maintain itself unaided and the shortfall must be machine-fulfilled; above
    it, ε_suff = 0 BY CONSTRUCTION, which is the correct answer rather than a
    degenerate one. A population that exists has been meeting its personal
    obligation off-ledger, or there would be no population.

    Returns keys: `adult_share`, `critical_adult_share`, `margin_pp`,
    `supply_per_capita`, `personal_demand_per_capita`, `covers` — and
    `margin_pp` is the one to quote.

    units: shares dimensionless; margin in PERCENTAGE POINTS of adult share;
    per-capita quantities in h/person·yr. ε-behaviour: defined across
    [0, 0.99]; the margin widens with ε as the machine share takes obligation.
    """
    from hours_eoh.core.eoh_generation import total_eoh

    a = capacity_weighted_adult_share()
    supply = labor_supply_per_capita(adult_capacity_h_yr)
    demand = total_eoh(epsilon=epsilon, population=population)["personal"] / population
    a_crit = demand / adult_capacity_h_yr
    return {
        "adult_share": a,
        "critical_adult_share": a_crit,
        "margin_pp": (a - a_crit) * 100.0,
        "supply_per_capita": supply,
        "personal_demand_per_capita": demand,
        "covers": float(supply >= demand),
    }

def capacity_band_alignment(
    epsilon: float = 0.0,
    year: int | None = None,
) -> dict[str, float]:
    """
    REPORTING ONLY — the supply band against the band its capacity was measured on.

    THE MISMATCH. `MEASURED_CAPACITY_H_YR` is hours per adult per year over ages
    **18-69** (paid work, unpaid domestic work and childcare). The adult share it
    is multiplied by selects **18-64**, because `capacity_weight` is 1.0 for
    `working_age` and 0.0 for `elderly`. So c's denominator includes 65-69 and
    a's numerator excludes them: L = c·a understates hours per capita, and the
    arithmetic that would be right is c times the 18-69 share.

    ADOPTED 2026-09-04 (author decision), and this now reports a SATISFIED
    alignment rather than an outstanding one: `AGE_CAPACITY_WEIGHT_ELDERLY` is
    0.3083, so the shipped share carries the 65-69 who sit inside c's window.
    What remains is the residual between the shipped `AGE_GROUP_FRACTIONS` — a
    convention — and the census age structure, which is a smaller and different
    frame question.

    WHY IT DID NOT SHIP AS A FIX FIRST, because the objection stands.
    Correcting the supply band alone made ε=0 feasible — the over-determination
    the repo carried since August closed, frames clearing went 17/50 to 43/50,
    and the retrodiction (1965 clears, 2024 does not) was lost with it. `tests/test_measured_capacity.py`
    warns in as many words that "a fix that made the finding vanish would be the
    more suspicious outcome", and it is right here: `AGE_WEIGHT_ELDERLY` = 1.48
    is documented in its own tag block as a **lower bound**, because the
    institutionalised elderly are outside the ATUS frame entirely. So the
    DEMAND side is understated too, by an unmeasured amount, and closing the
    deficit by correcting only the supply side is the asymmetric fix that
    flatters. Both sides move; only one of them is measurable today.

    Returns the two shares, the census-derived gap, and what the correction
    would do to the feasibility ratio — so the size of the effect is on the
    record without being adopted.

    units: shares dimensionless; ratios dimensionless. ε-behaviour: defined
    across [0, 0.99]; the gap is ε-independent, the ratios are not.
    """
    from hours_eoh.reference.care_demand import population_shares

    lo, hi = CAPACITY_MEASUREMENT_BAND
    wlo, whi = AGE_GROUPS["working_age"]["range"]
    shares = population_shares(
        {"selected": (wlo, whi), "measured": (lo, hi)}, year=year)
    # THE BAND-ALIGNED SHARE IS THE CENSUS SHARE INSIDE THE CAPACITY WINDOW,
    # read directly. The first version of this computed it as
    # `a_used - selected + measured`, which was right only while the elderly
    # capacity weight was 0.0; once the weight was adopted that expression
    # added the same people twice and reported a 0.71 share. A correction is
    # not a delta to be re-applied — it is a target to be compared against.
    a_used = capacity_weighted_adult_share()
    a_band = shares["measured"]
    base = feasibility_check(epsilon=epsilon)
    aligned = feasibility_check(epsilon=epsilon, adult_share=a_band)
    return {
        "share_selected": shares["selected"],
        "share_measured": shares["measured"],
        "gap_pp": (shares["measured"] - shares["selected"]) * 100.0,
        "adult_share_used": a_used,
        "adult_share_band_aligned": a_band,
        "ratio_as_shipped": base["demand_supply_ratio"],
        "ratio_band_aligned": aligned["demand_supply_ratio"],
        "feasible_as_shipped": float(base["feasible"]),
        "feasible_band_aligned": float(aligned["feasible"]),
    }

def feasibility_check(
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
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

    share = capacity_weighted_adult_share() if adult_share is None else adult_share
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
    workforce_fraction: float | None = None,
) -> OverDeterminationReport:
    """
    The full test: is (PERSONAL_EOH_BASE, labor supply) an over-determined pair?

    Two arms, and the first is the one that matters:

    1. **Self-consistency.** The repo's own supply constants — H_REF = 2,080 and
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
        workforce_fraction: RETIRED as the self-consistency basis (2026-09-04).
            None (default) runs the self arm on the MEASURED path —
            `MEASURED_CAPACITY_H_YR` and the capacity-weighted adult share, the
            same L every other feasibility caller uses. Pass a float to
            reproduce the old arm, which was `H_REF` x 0.5 = 1,040 h/person·yr:
            the paid-work calendar year times a participation figure that is the
            same 1e9-for-1M convention the corridor CLI carried, retired there
            on 2026-09-04. That arm is 68% of the measured supply and it is what
            produced the OVER-DETERMINED verdict; the capacity migration of
            2026-09-03 replaced `H_REF` on the feasibility path and missed this
            caller.

    Returns:
        OverDeterminationReport.
    """
    if workforce_fraction is None:
        self_arm = feasibility_check(epsilon=0.0)
    else:
        self_arm = feasibility_check(
            adult_capacity_h_yr=float(H_REF), adult_share=workforce_fraction,
            epsilon=0.0,
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
            f"OVER-DETERMINED. On a supply of "
            f"{self_arm['supply_per_capita']:.0f} h/person·yr, demand at ε=0 is "
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


def measured_capacity_frames(extra: tuple[str, ...] = ()) -> dict:
    """
    The feasibility test run against MEASURED labour capacity, frame by frame.

    THE DEFECT THIS EXISTS FOR. `labor_supply_per_capita` asks for "hours per
    year one adult can devote to entropy-resistance labor" and defaults to
    `H_REF`. But H_REF's own tag block says, in as many words, that read "as a
    measurement of hours actually worked it would be wrong in most
    jurisdictions... which is precisely why it is tagged as the denominator it
    is." It is a paid-work calendar year — 40 x 52 — standing in for all the
    labour a person supplies to every domain, most of which is unpaid. The
    constant warns against exactly this use.

    MTUS supplies the measurement: 50 frames over 1965-2024 and ten countries,
    each the weighted mean of paid work, unpaid domestic work and childcare for
    ages 18-69. **45 of the 50 exceed H_REF**, the five that do not being
    Netherlands 1975-1995.

    AND CORRECTING IT DOES NOT DISSOLVE THE OVER-DETERMINATION, which is why
    this reports rather than repoints. Only 16 of the 50 frames clear at
    epsilon = 0; the ones that do are the historically high-labour frames —
    1960s France and the mid-century US. The model's demand at epsilon = 0 is
    met by societies working roughly 2,400 h/adult-yr and up, and most measured
    societies do not. The default is wrong AND the finding survives its
    correction.

    ADOPTED 2026-09-03 (author decision): the default is now
    `MEASURED_CAPACITY_H_YR`, the all-frame median. This function stays as the
    audit of that choice — it shows the whole distribution the median came from
    and which frames clear.
    """
    frames = mtus.capacity_frames(extra)
    rows = {}
    for sample, capacity in frames.items():
        check = feasibility_check(adult_capacity_h_yr=capacity, epsilon=0.0)
        rows[sample] = {
            "capacity_h_yr": capacity,
            "exceeds_h_ref": capacity > float(H_REF),
            "demand_supply_ratio": check["demand_supply_ratio"],
            "feasible_at_zero": check["feasible"],
        }
    clearing = [s for s, r in rows.items() if r["feasible_at_zero"]]
    above = [s for s, r in rows.items() if r["exceeds_h_ref"]]
    required = feasibility_check(epsilon=0.0)["hours_per_adult_required"]
    return {
        "frames": rows,
        "n_frames": len(rows),
        "n_exceeding_h_ref": len(above),
        "share_exceeding_h_ref": len(above) / len(rows),
        "n_clearing_at_zero": len(clearing),
        "clearing": sorted(clearing),
        "below_h_ref": sorted(s for s, r in rows.items() if not r["exceeds_h_ref"]),
        "h_ref": float(H_REF),
        "hours_per_adult_required": required,
        "default_is_measured_median": True,
        "verdict": (
            f"{len(above)} of {len(rows)} measured frames exceed H_REF="
            f"{float(H_REF):,.0f}, so the default understates capacity almost "
            f"everywhere; but only {len(clearing)} of {len(rows)} clear at "
            f"epsilon=0, because the model's demand needs {required:,.0f} "
            "h/adult-yr. The default is wrong and the over-determination "
            "survives correcting it"
        ),
    }


def feasible_epsilon(
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
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
    time use of 2.8 h/adult·day at the 0.6524 adult share gives H ≈ 667; R ≈ 76.
    Then B = (266 + 667 − 76)/1.3528 ≈ 633 and ε ≈ 0.30. Compare the shipped
    1,500. (Was 544 at w = 1.475 and a = 0.60; both inputs have since moved.)
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
    share = capacity_weighted_adult_share() if adult_share is None else adult_share
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
