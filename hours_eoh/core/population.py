"""
Human Capital Lifecycle: Aging

Models age-based changes to personal EOH and entropy-reduction capacity.
The other lifecycle events (birth, maturation, death) are in capital.py
and are fully tested in Phase 2. This module adds:

  - age_group_for_age(): classify a person's age into the four EOH groups
  - aging(): advance age, update personal EOH, decay entropy-reduction capacity
  - population_eoh_curve(): EOH demand by age cohort across a full population
  - population_lifecycle_snapshot(): aggregate snapshot of population EOH burden

Design principles:
- Personal EOH rises sharply at birth (3.0×) and again in elderly years (2.5×)
- Entropy-reduction capacity peaks in mid-career, declines with age
- Automation (ε) slightly modulates elderly EOH and covered burden
- No TEH created or destroyed — aging is an EOH accounting event only

Mission Statement: §"Humans as capital stock"; §"A newborn is the highest-EOH-
density event in the system"; §"Personal entropy — the human body requires
continuous entropy resistance to sustain biological organization"
"""

from __future__ import annotations
import math

from hours_eoh.data import (
    AGE_GROUPS,
    PERSONAL_EOH_BASE,
    ELDERLY_EOH_EPSILON_FACTOR,
    HUMAN_CAPITAL_NATURAL_DECAY,
    HUMAN_CAPITAL_ELDERLY_DECAY,
    CAPACITY_DECLINE_ONSET_AGE,
    CAPACITY_DECLINE_MID_AGE,
    CAPACITY_DECLINE_LATE_AGE,
    CAPACITY_DECLINE_EARLY_RATE,
    CAPACITY_DECLINE_MID_RATE,
    CAPACITY_DECLINE_LATE_RATE,
)


# ---------------------------------------------------------------------------
# Capacity decline model constants
# MIGRATED TO data.py 2026-08-27. They were shadow constants — untagged,
# invisible to the provenance gate, and a +7% perturbation of any of them moved
# no test at all. Onset age differs from the AGE_GROUPS elderly boundary
# because the claim is biological capacity, not labour-force status.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Age classification
# ---------------------------------------------------------------------------

def age_group_for_age(age: float) -> str:
    """
    Return the AGE_GROUPS key for a given age in years.

    Boundaries (from data.py):
      infant      0–5
      child       6–17
      working_age 18–64
      elderly     65+

    Args:
        age: Age in years. Must be ≥ 0.

    Returns:
        One of: "infant", "child", "working_age", "elderly".

    Reference: Mission Statement §"Humans as capital stock" — the EOH weight
    system distinguishes biological life stages, not economic productivity.
    """
    if age < 0:
        raise ValueError(f"Age must be non-negative, got {age}")
    if age < 6:
        return "infant"
    elif age < 18:
        return "child"
    elif age < 65:
        return "working_age"
    else:
        return "elderly"


def _capacity_decline_rate(age: float) -> float:
    """
    Annual fractional decline in entropy-reduction capacity due to aging.

    Returns 0 through peak working years. Rises in later working life.
    Steeper in elderly phases — matching the biological reality that
    physical and cognitive capacity decreases with age.

    Designed to produce:
    - Ages 18–49: no age-related decline (prime working capacity)
    - Ages 50–64: 1.5%/year (gradual late-career erosion)
    - Ages 65–79: 4.0%/year (early elderly phase)
    - Ages 80+:   7.0%/year (late elderly phase)
    """
    if age < CAPACITY_DECLINE_ONSET_AGE:
        return 0.0
    elif age < CAPACITY_DECLINE_MID_AGE:
        return CAPACITY_DECLINE_EARLY_RATE
    elif age < CAPACITY_DECLINE_LATE_AGE:
        return CAPACITY_DECLINE_MID_RATE
    else:
        return CAPACITY_DECLINE_LATE_RATE


# ---------------------------------------------------------------------------
# Aging
# ---------------------------------------------------------------------------

def aging(
    asset: dict,
    years_elapsed: float = 1.0,
    epsilon: float = 0.40,
    personal_eoh_base: float = PERSONAL_EOH_BASE,
) -> dict:
    """
    Advance a human capital asset's age and update EOH/capacity accordingly.

    Aging modifies three quantities:
    1. Personal EOH (entropy obligation): changes when crossing age-group boundaries.
       Elderly personal EOH is slightly higher at higher ε because automation
       defers some human-provided care into the formal EOH ledger.
    2. Entropy-reduction capacity: peak in mid-career, declining thereafter.
       Decline rate depends on age (see _capacity_decline_rate).
    3. Condition: natural biological aging degrades condition slowly; faster
       in elderly years.

    This function does NOT mutate the input asset — it returns a result dict
    containing the updated values and an `updated_asset` dict.

    Args:
        asset: A human capital Asset (is_human_capital must be True).
        years_elapsed: Years to advance age. Default: 1.0.
        epsilon: Automation level (affects elderly personal EOH).
        personal_eoh_base: Base EOH for a working-age person. Default: 1500.

    Returns:
        dict: {
          "asset_id":                str,
          "old_age":                 float,
          "new_age":                 float,
          "old_age_group":           str,
          "new_age_group":           str,
          "age_group_changed":       bool,
          "old_personal_eoh_per_year": float,
          "new_personal_eoh_per_year": float,
          "personal_eoh_delta":      float,
          "old_capacity":            float,
          "new_capacity":            float,
          "capacity_delta":          float,
          "old_condition":           float,
          "new_condition":           float,
          "updated_asset":           dict,   (use this to persist the state)
          "epsilon":                 float,
        }

    Raises:
        ValueError: If asset is not human capital.

    Reference: Mission Statement §"Humans as capital stock" — aging is
    modeled as gradual write-down of capacity, mirrored by rising personal EOH.
    """
    if not asset.get("is_human_capital", False):
        raise ValueError(
            f"aging() requires a human capital asset; "
            f"asset {asset.get('asset_id', '?')} has is_human_capital=False"
        )
    if years_elapsed < 0:
        raise ValueError(f"years_elapsed must be non-negative, got {years_elapsed}")

    old_age = float(asset.get("age", 0.0))
    new_age = old_age + years_elapsed

    old_group = age_group_for_age(old_age)
    new_group = age_group_for_age(new_age)

    # Personal EOH is determined by age-group weight
    eoh_weight = AGE_GROUPS[new_group]["eoh_weight"]
    new_personal_eoh = personal_eoh_base * eoh_weight
    # Automation slightly elevates elderly EOH: deferred personal care becomes
    # a registered EOH obligation at higher ε
    if new_group == "elderly":
        new_personal_eoh *= (1.0 + ELDERLY_EOH_EPSILON_FACTOR * epsilon)

    old_personal_eoh = float(asset.get("personal_eoh_per_year", 0.0))

    # Capacity decline: use mid-period age for the annual rate (continuous approx.)
    old_capacity = float(asset.get("entropy_reduction_capacity", 0.0))
    mid_age = old_age + years_elapsed / 2.0
    decline_rate = _capacity_decline_rate(mid_age)
    new_capacity = old_capacity * ((1.0 - decline_rate) ** years_elapsed)
    new_capacity = max(0.0, new_capacity)

    # Natural condition decay — biological aging
    old_condition = float(asset.get("condition", 1.0))
    natural_decay = HUMAN_CAPITAL_NATURAL_DECAY if new_group != "elderly" else HUMAN_CAPITAL_ELDERLY_DECAY
    new_condition = old_condition * ((1.0 - natural_decay) ** years_elapsed)
    new_condition = max(0.0, min(1.0, new_condition))

    # Build updated asset dict (shallow copy + overrides)
    updated_asset = dict(asset)
    updated_asset["age"]                      = new_age
    updated_asset["personal_eoh_per_year"]    = new_personal_eoh
    updated_asset["entropy_reduction_capacity"] = new_capacity
    updated_asset["condition"]                = new_condition

    return {
        "asset_id":                 asset.get("asset_id", ""),
        "old_age":                  old_age,
        "new_age":                  new_age,
        "old_age_group":            old_group,
        "new_age_group":            new_group,
        "age_group_changed":        old_group != new_group,
        "old_personal_eoh_per_year": old_personal_eoh,
        "new_personal_eoh_per_year": new_personal_eoh,
        "personal_eoh_delta":       new_personal_eoh - old_personal_eoh,
        "old_capacity":             old_capacity,
        "new_capacity":             new_capacity,
        "capacity_delta":           new_capacity - old_capacity,
        "old_condition":            old_condition,
        "new_condition":            new_condition,
        "updated_asset":            updated_asset,
        "epsilon":                  epsilon,
    }


# ---------------------------------------------------------------------------
# Population EOH Curve
# ---------------------------------------------------------------------------

def population_eoh_curve(
    age_distribution: dict[str, float],
    epsilon: float = 0.40,
    base_rate: float = PERSONAL_EOH_BASE,
) -> list[dict]:
    """
    Compute total personal EOH demand by age cohort across a population.

    Each age group has a different EOH weight reflecting biological needs:
    - Infants (0–5):   3.0× → intensive personal entropy resistance
    - Children (6–17): 1.5× → still high care needs
    - Working-age (18–64): 1.0× → baseline
    - Elderly (65+):   2.5× → rising biological entropy resistance

    At higher ε, elderly EOH is slightly elevated (automation shifts some
    elder care from informal → registered collective obligation).

    Args:
        age_distribution: Dict mapping age group name → count.
                          Keys must be in {"infant", "child", "working_age", "elderly"}.
        epsilon: Automation level [0.0, 0.99].
        base_rate: EOH per year per working-age-equivalent. Default: 1500.

    Returns:
        List of dicts per age group, sorted by eoh_per_capita (descending):
        [{"age_group", "age_range", "population", "eoh_per_capita",
          "total_eoh", "eoh_weight", "epsilon"}, ...]

    Reference: Mission Statement §"Personal entropy — the human body requires
    continuous entropy resistance at every stage of life, with infants and
    elderly requiring the highest density of care labor."
    """
    for group_name in age_distribution:
        if group_name not in AGE_GROUPS:
            raise ValueError(
                f"Unknown age group: '{group_name}'. "
                f"Valid groups: {list(AGE_GROUPS.keys())}"
            )

    result = []
    for group_name, count in age_distribution.items():
        group = AGE_GROUPS[group_name]
        eoh_weight = group["eoh_weight"]

        eoh_per_capita = base_rate * eoh_weight
        if group_name == "elderly":
            eoh_per_capita *= (1.0 + ELDERLY_EOH_EPSILON_FACTOR * epsilon)

        total_eoh = eoh_per_capita * float(count)

        result.append({
            "age_group":      group_name,
            "age_range":      group["range"],
            "population":     float(count),
            "eoh_per_capita": eoh_per_capita,
            "total_eoh":      total_eoh,
            "eoh_weight":     eoh_weight,
            "epsilon":        epsilon,
        })

    return sorted(result, key=lambda x: x["eoh_per_capita"], reverse=True)


# ---------------------------------------------------------------------------
# Population Lifecycle Snapshot
# ---------------------------------------------------------------------------

def population_lifecycle_snapshot(
    age_distribution: dict[str, float],
    epsilon: float = 0.40,
    base_rate: float = PERSONAL_EOH_BASE,
    mean_entropy_reduction_capacity: float = 1200.0,
) -> dict:
    """
    Full snapshot of a population's EOH demand and workforce capacity.

    Aggregates the EOH curve into summary statistics useful for fiscal
    planning: total obligation, care pipeline cost, dependency ratio,
    and how much of the burden automation covers at this ε level.

    Args:
        age_distribution: Dict mapping age group → count.
        epsilon: Automation level.
        base_rate: Personal EOH base rate.
        mean_entropy_reduction_capacity: Human-only EOH/yr a working-age person
                                         can fulfill through their own labor (not
                                         automation-assisted throughput). This is
                                         intentionally ε-independent: it represents
                                         the biological ceiling on human work capacity,
                                         which does not change with automation level.
                                         At higher ε, automation_covered_eoh absorbs
                                         more of the burden; this parameter stays fixed.
                                         Default: 1200 (roughly 60% of full-year).

    Returns:
        dict: {
          "total_population": float,
          "total_personal_eoh": float,          (total EOH demand per year)
          "working_age_count": float,
          "dependent_count": float,
          "dependency_ratio": float,            (dependents per worker)
          "care_pipeline_eoh": float,           (EOH needed for infants + children)
          "workforce_capacity_eoh": float,      (working-age entropy-reduction capacity)
          "automation_covered_eoh": float,      (EOH handled by automation)
          "human_eoh_burden": float,            (EOH requiring human labor)
          "net_capacity_gap": float,            (human burden minus workforce capacity; <0 = surplus)
          "eoh_curve": list[dict],
          "epsilon": float,
        }

    Reference: Mission Statement §"Care is capital formation" — the care
    pipeline shows the investment required to grow future workforce capacity.
    """
    curve = population_eoh_curve(age_distribution, epsilon, base_rate)

    total_population = sum(float(v) for v in age_distribution.values())
    total_personal_eoh = sum(c["total_eoh"] for c in curve)

    working_age_count = float(age_distribution.get("working_age", 0.0))
    infant_count = float(age_distribution.get("infant", 0.0))
    child_count  = float(age_distribution.get("child", 0.0))

    dependent_count  = total_population - working_age_count
    dependency_ratio = dependent_count / max(working_age_count, 1.0)

    # Care pipeline: EOH needed to care for those not yet at working capacity
    care_pipeline_eoh = (
        infant_count * base_rate * AGE_GROUPS["infant"]["eoh_weight"]
        + child_count * base_rate * AGE_GROUPS["child"]["eoh_weight"]
    )

    # Workforce capacity (working-age only)
    workforce_capacity_eoh = working_age_count * mean_entropy_reduction_capacity

    # Automation covers its share; humans cover the rest
    automation_covered_eoh = total_personal_eoh * epsilon
    human_eoh_burden       = total_personal_eoh * (1.0 - epsilon)

    net_capacity_gap = human_eoh_burden - workforce_capacity_eoh

    return {
        "total_population":        total_population,
        "total_personal_eoh":      total_personal_eoh,
        "working_age_count":       working_age_count,
        "dependent_count":         dependent_count,
        "dependency_ratio":        dependency_ratio,
        "care_pipeline_eoh":       care_pipeline_eoh,
        "workforce_capacity_eoh":  workforce_capacity_eoh,
        "automation_covered_eoh":  automation_covered_eoh,
        "human_eoh_burden":        human_eoh_burden,
        "net_capacity_gap":        net_capacity_gap,
        "eoh_curve":               curve,
        "epsilon":                 epsilon,
    }


# ---------------------------------------------------------------------------
# Cohort aging trajectory
# ---------------------------------------------------------------------------

def cohort_aging_trajectory(
    initial_distribution: dict[str, float],
    n_years: int = 20,
    birth_rate: float = 0.012,
    death_rate_elderly: float = 0.04,
    epsilon: float = 0.40,
    capital_personal_eoh_per_person: float = 0.0,
) -> dict:
    """
    Simulate year-by-year cohort flow and track how the age distribution shifts.

    Models the four-cohort population as a flow system: each year, a fraction
    of each cohort ages into the next group, births replenish infants, and
    elderly deaths remove population. This makes demographic dynamics concrete
    for fiscal planning: a bulge in the infant cohort becomes a care-demand
    surge 65 years later; a shrinking working-age cohort raises the dependency
    ratio immediately.

    Cohort transition rules (simplified from AGE_GROUPS ranges):
      - infant  (0–5,   6 years): 1/6 graduate to child each year
      - child   (6–17, 12 years): 1/12 graduate to working_age each year
      - working_age (18–64, 47 years): 1/47 graduate to elderly each year
      - elderly (65+):  fraction die each year (death_rate_elderly)
    Births add to infant cohort at birth_rate × total_population each year.
    Working-age deaths are assumed negligible (absorbed into birth/death rates).

    Args:
        initial_distribution: Starting counts per age group
                              (keys: "infant", "child", "working_age", "elderly").
        n_years: Number of years to simulate.
        birth_rate: Annual births as fraction of total population.
        death_rate_elderly: Annual deaths as fraction of elderly cohort.
        epsilon: Automation level (held fixed — use run_simulation for ε arcs).
        capital_personal_eoh_per_person: Annual personal EOH fulfilled per person
                                         by the capital stock (water, energy, healthcare
                                         infrastructure). Reduces the effective personal
                                         EOH base rate used in each year's snapshot,
                                         lowering the human_eoh_burden. Default: 0.0
                                         (no capital-stock reduction).

    Returns:
        dict: {
          "years":             list[int],                 (0..n_years)
          "distributions":     list[dict[str, float]],   (one per year)
          "total_populations": list[float],
          "dependency_ratios": list[float],               (dependents/working_age)
          "human_eoh_burdens": list[float],               (total human EOH each year)
          "peak_dependency_year": int,                    (year with highest ratio)
          "final_distribution": dict[str, float],
        }

    Reference: Mission Statement §"Care pipeline" — the infant cohort is a
    forward-dated liability; tracking it reveals care-demand surges before
    they arrive and allows fiscal preparation.
    """
    def _span(group: str) -> int:
        lo, hi = AGE_GROUPS[group]["range"]
        return hi - lo + 1

    _INFANT_YEARS      = _span("infant")       # 6
    _CHILD_YEARS       = _span("child")        # 12
    _WORKING_AGE_YEARS = _span("working_age")  # 47

    dist = {k: float(v) for k, v in initial_distribution.items()}
    for key in ("infant", "child", "working_age", "elderly"):
        dist.setdefault(key, 0.0)

    years, distributions, totals, dep_ratios, burdens = [], [], [], [], []

    effective_base = max(0.0, PERSONAL_EOH_BASE - capital_personal_eoh_per_person)

    for year in range(n_years + 1):
        total_pop = sum(dist.values())
        working   = dist["working_age"]
        dep_ratio = (total_pop - working) / max(working, 1.0)

        snapshot = population_lifecycle_snapshot(dist, epsilon=epsilon,
                                                 base_rate=effective_base)

        years.append(year)
        distributions.append(dict(dist))
        totals.append(total_pop)
        dep_ratios.append(dep_ratio)
        burdens.append(snapshot["human_eoh_burden"])

        if year < n_years:
            grad_infant    = dist["infant"]      / _INFANT_YEARS
            grad_child     = dist["child"]       / _CHILD_YEARS
            grad_working   = dist["working_age"] / _WORKING_AGE_YEARS
            elderly_deaths = dist["elderly"]     * death_rate_elderly
            births         = total_pop           * birth_rate

            dist = {
                "infant":      max(0.0, dist["infant"]      - grad_infant  + births),
                "child":       max(0.0, dist["child"]       - grad_child   + grad_infant),
                "working_age": max(0.0, dist["working_age"] - grad_working + grad_child),
                "elderly":     max(0.0, dist["elderly"]     - elderly_deaths + grad_working),
            }

    peak_year = dep_ratios.index(max(dep_ratios))

    return {
        "years":               years,
        "distributions":       distributions,
        "total_populations":   totals,
        "dependency_ratios":   dep_ratios,
        "human_eoh_burdens":   burdens,
        "peak_dependency_year": peak_year,
        "final_distribution":  distributions[-1],
    }
