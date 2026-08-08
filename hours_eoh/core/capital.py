"""
Capital Write-Down Mechanics

Models the full lifecycle of capital assets (including human capital): condition
tracking based on maintenance history, write-down trigger detection, and write-down
execution with TEH and EOH ledger updates.

Key principle: when an asset is written down, the event is:
1. EOH obligation zeroed (the asset no longer generates entropy demand)
2. TEH destroyed equal to the asset's remaining capital value
3. For human capital: personal EOH and entropy-reduction capacity both removed;
   unfulfilled EOH redistributed to remaining workforce without creating orphans.

Guardrail II from the Mission Statement applies: irrecoverable capital cannot
carry an indefinite maintenance obligation. The write-down acknowledges a
permanent loss of physical capacity — not a monetary event, but an accounting
of reality.

Mission Statement: §"Guardrail II — Capital write-down", §"Humans as capital
stock", §"The dual ledger", §"Condition I — Ledger Identity"
"""

from __future__ import annotations
from typing import TypedDict

from hours_eoh.data import (
    AGE_GROUPS, HUMAN_CAPITAL_NATURAL_DECAY, PERSONAL_EOH_BASE,
    INFANT_EOH_EPSILON_FACTOR, MATURATION_AUTO_LEVERAGE,
    ANNUAL_DEATH_RATE, ESTATE_INHERITANCE_FRACTION,
    ESTATE_LEVY_FRACTION, ESTATE_PERSONAL_RESERVE_YEARS,
)


# ---------------------------------------------------------------------------
# Asset condition calibration constants
# ---------------------------------------------------------------------------
_ASSET_FULL_NEGLECT_DECAY:     float = 0.20  # condition drop per period at zero maintenance
_ASSET_OVER_MAINT_RESTORE_RATE: float = 0.05  # condition restore per unit surplus maintenance

# Maturation model calibration (birth event uses INFANT_EOH_EPSILON_FACTOR from data.py)
_MATURATION_BASE_GROWTH_RATE: float = 50.0  # EOH/yr capacity from natural aging (per year)
_MATURATION_EDU_COEFFICIENT:  float = 5.0   # sqrt-scaling coefficient for education investment
_MATURATION_EDU_EXPONENT:     float = 0.5   # diminishing-returns exponent for education


# ---------------------------------------------------------------------------
# Asset Data Structure
# ---------------------------------------------------------------------------

class Asset(TypedDict, total=False):
    """
    Typed dict for a capital asset (including human capital).

    Required keys:
        asset_id:      Unique identifier.
        asset_type:    Key into ASSET_TYPES (from data.py).
        teh_value:     TEH embodied in this asset (destroyed if written down).
        annual_eoh:    Current annual EOH this asset generates (hours/year).
        design_life:   Expected useful life (years).
        age:           Current age (years).
        condition:     Current condition score ∈ [0.0, 1.0].

    Optional keys (human capital):
        is_human_capital:            True for persons.
        entropy_reduction_capacity:  EOH per year this person can fulfill.
        personal_eoh_per_year:       EOH this person generates by existing.
    """
    asset_id:                   str
    asset_type:                 str
    teh_value:                  float
    annual_eoh:                 float
    annual_eoh_eliminated:             float   # non-human assets: system EOH (i/e/k) reduced per year — not personal
    annual_personal_eoh_fulfilled:     float   # personal EOH this asset fulfills per year (water, energy, healthcare)
    design_life:                       float
    age:                               float
    condition:                         float
    is_human_capital:                  bool
    entropy_reduction_capacity:        float   # human capital only
    personal_eoh_per_year:             float   # human capital only


def make_asset(
    asset_id: str,
    asset_type: str,
    teh_value: float,
    annual_eoh: float,
    design_life: float,
    annual_eoh_eliminated: float = 0.0,
    annual_personal_eoh_fulfilled: float = 0.0,
    age: float = 0.0,
    condition: float = 1.0,
    is_human_capital: bool = False,
    entropy_reduction_capacity: float = 0.0,
    personal_eoh_per_year: float = 0.0,
) -> Asset:
    """
    Construct a well-formed Asset dict.

    Args:
        asset_id: Unique identifier.
        asset_type: Key into ASSET_TYPES.
        teh_value: TEH embodied in the asset (initial construction cost).
        annual_eoh: Annual maintenance EOH demand (hours/year).
        design_life: Design life (years).
        annual_eoh_eliminated: System EOH (infrastructure/ecological/knowledge)
                               this asset reduces per year. Does NOT reduce
                               personal EOH — biological needs are unaffected.
        annual_personal_eoh_fulfilled: Personal EOH this asset fulfills per year
                               on behalf of the population (water treatment →
                               sanitation EOH, hospitals → healthcare EOH, energy
                               grids → heating/cooking EOH). Distinct from
                               annual_eoh_eliminated: the biological demand still
                               exists; the capital handles fulfillment. Non-zero
                               only for infrastructure assets with direct personal
                               EOH coverage.
        age: Current asset age (years). Default: 0.
        condition: Initial condition ∈ [0, 1]. Default: 1.0 (brand new).
        is_human_capital: True for persons.
        entropy_reduction_capacity: For persons: EOH/year they can fulfill.
        personal_eoh_per_year: For persons: EOH they generate by existing.

    Returns:
        Asset dict.

    Reference: Mission Statement §"Humans as capital stock" — persons are
    modeled with the same write-down logic as infrastructure assets.
    """
    return Asset(
        asset_id=asset_id,
        asset_type=asset_type,
        teh_value=teh_value,
        annual_eoh=annual_eoh,
        annual_eoh_eliminated=annual_eoh_eliminated,
        annual_personal_eoh_fulfilled=annual_personal_eoh_fulfilled,
        design_life=design_life,
        age=age,
        condition=condition,
        is_human_capital=is_human_capital,
        entropy_reduction_capacity=entropy_reduction_capacity,
        personal_eoh_per_year=personal_eoh_per_year,
    )


def aggregate_personal_eoh_fulfilled(
    assets: list[Asset],
    population: float,
) -> dict:
    """
    Aggregate annual_personal_eoh_fulfilled across a capital fleet and derive
    the per-capita value needed by sufficiency_guarantee().

    Each asset in the fleet that directly fulfills personal biological EOH
    (water treatment, hospitals, energy grids) contributes its
    annual_personal_eoh_fulfilled to the collective total. Dividing by
    population gives the per-capita coverage that reduces the guarantee's
    EOH reimbursement component.

    Args:
        assets: List of Asset dicts. Assets without annual_personal_eoh_fulfilled
                (or with value 0.0) are silently skipped.
        population: Total population served by the asset fleet.

    Returns:
        dict: {
          "total_annual_personal_eoh_fulfilled": float,  (sum across fleet)
          "per_capita_fulfilled":               float,  (total / population)
          "asset_count":                        int,
          "population":                         float,
        }

    Usage: pass result["per_capita_fulfilled"] to sufficiency_guarantee() as
    capital_personal_eoh_fulfilled_per_person.

    Reference: Mission Statement §"Capital stock fulfills personal EOH on behalf
    of the population — water treatment, healthcare infrastructure, energy grids."
    """
    total = sum(a.get("annual_personal_eoh_fulfilled", 0.0) for a in assets)
    per_capita = total / max(population, 1.0)
    return {
        "total_annual_personal_eoh_fulfilled": total,
        "per_capita_fulfilled":                per_capita,
        "asset_count":                         len(assets),
        "population":                          population,
    }


# ---------------------------------------------------------------------------
# Asset Condition Tracking
# ---------------------------------------------------------------------------

def asset_condition(
    initial_condition: float,
    maintenance_history: list[dict],
    natural_decay_rate: float = HUMAN_CAPITAL_NATURAL_DECAY,
) -> float:
    """
    Compute current asset condition from its maintenance history.

    Each period, the asset's condition evolves based on:
    1. Maintenance quality: fulfilled / demanded (< 1.0 → condition declines)
    2. Natural aging: small constant decline representing unavoidable wear
    3. Surplus maintenance: over-maintenance slightly restores condition

    Condition ∈ [0.0, 1.0]:
    - 1.0: fully maintained, like-new
    - 0.5: significant deterioration
    - 0.2: approaching recoverability threshold (write-down territory)
    - 0.0: collapsed / irrecoverable

    Args:
        initial_condition: Condition at the start of the maintenance history.
                           Typically 1.0 for a new asset.
        maintenance_history: List of period dicts:
                             [{"eoh_demanded": float, "eoh_fulfilled": float}, ...]
                             Periods are applied in order (chronological).
        natural_decay_rate: Annual condition loss from unavoidable wear.
                            Default: 0.005 (0.5%/year). Higher for software, lower
                            for stone structures.

    Returns:
        Current condition ∈ [0.0, 1.0].

    Reference: Mission Statement §"Guardrail II — Capital write-down":
    "asset state based on EOH fulfillment history"
    """
    condition = float(initial_condition)
    condition = max(0.0, min(1.0, condition))

    for period in maintenance_history:
        demanded  = float(period.get("eoh_demanded", 0.0))
        fulfilled = float(period.get("eoh_fulfilled", 0.0))

        # Maintenance quality this period
        if demanded > 0:
            quality = min(fulfilled / demanded, 2.0)  # cap surplus at 2×
        else:
            quality = 1.0  # no demand → perfect quality

        # Deficit effect: unmet maintenance degrades condition
        # Full neglect (quality=0): condition drops _ASSET_FULL_NEGLECT_DECAY this period
        deficit_fraction = max(0.0, 1.0 - quality)
        condition *= (1.0 - deficit_fraction * _ASSET_FULL_NEGLECT_DECAY)

        # Natural aging: unavoidable
        condition *= (1.0 - natural_decay_rate)

        # Surplus maintenance slightly restores condition (bounded by initial)
        if quality > 1.0:
            surplus = quality - 1.0
            # Diminishing returns on over-maintenance
            restoration = surplus * _ASSET_OVER_MAINT_RESTORE_RATE * condition
            condition = min(initial_condition, condition + restoration)

        condition = max(0.0, min(1.0, condition))

    return condition


def asset_condition_trajectory(
    initial_condition: float,
    annual_eoh: float,
    fulfillment_fraction: float,
    years: int,
    natural_decay_rate: float = 0.005,
) -> list[dict]:
    """
    Simulate asset condition over time at a constant maintenance level.

    Useful for modeling scenarios: what happens if we fully maintain an asset
    vs. let it degrade to 70% of required maintenance?

    Args:
        initial_condition: Starting condition ∈ [0, 1].
        annual_eoh: Annual EOH demand (hours).
        fulfillment_fraction: Fraction of demand fulfilled each year, ∈ [0, 2].
        years: Number of years to simulate.
        natural_decay_rate: Annual wear rate.

    Returns:
        List of dicts: [{"year": int, "condition": float,
                         "eoh_demanded": float, "eoh_fulfilled": float}, ...]
    """
    condition = initial_condition
    history   = []

    for year in range(1, years + 1):
        demanded  = annual_eoh
        fulfilled = demanded * fulfillment_fraction
        period    = {"eoh_demanded": demanded, "eoh_fulfilled": fulfilled}

        # Apply one period of condition evolution
        condition = asset_condition(condition, [period], natural_decay_rate)
        history.append({
            "year":          year,
            "condition":     condition,
            "eoh_demanded":  demanded,
            "eoh_fulfilled": fulfilled,
        })

    return history


# ---------------------------------------------------------------------------
# Write-Down Trigger
# ---------------------------------------------------------------------------

def writedown_trigger(
    condition: float,
    recoverability_threshold: float = 0.20,
) -> bool:
    """
    Determine whether an asset has degraded beyond the recovery point.

    Below the recoverability threshold, the maintenance labor required to
    restore function exceeds the labor required to rebuild from scratch.
    The asset must be written down — its EOH obligation zeroed and its
    TEH value destroyed.

    Args:
        condition: Current asset condition ∈ [0, 1].
        recoverability_threshold: Condition below which recovery is not viable.
                                  Default: 0.20 (20% of original condition).

    Returns:
        True if write-down should be triggered; False if asset is recoverable.

    Reference: Mission Statement §"Guardrail II — Capital write-down" —
    "When capital degrades beyond the point where maintenance labor can restore
    function, the associated EOH must be formally written off."
    """
    return condition < recoverability_threshold


# ---------------------------------------------------------------------------
# Execute Write-Down
# ---------------------------------------------------------------------------

def execute_writedown(
    asset: Asset,
    workforce_size: float = 0.0,
    other_assets_eoh: float = 0.0,
) -> dict:
    """
    Execute a capital write-down and return the ledger updates to apply.

    This function does NOT mutate any ledger state — it returns what SHOULD
    happen. The caller applies these changes to the TEH and EOH ledgers.

    Write-down effects:
    1. TEH destroyed: asset's teh_value is removed from circulation (Condition I).
       This is the second destruction mechanism alongside terminal consumption.
    2. EOH zeroed: the asset's annual_eoh is removed from the collective ledger.
       If the asset was generating EOH it can no longer fulfill, that obligation
       was deferred — the write-down acknowledges we cannot recover it.
    3. For human capital (death): additional redistribution required.
       - Personal EOH (entropy obligations of this person) is removed.
       - Entropy-reduction capacity is removed from workforce.
       - Any EOH this person was fulfilling must be redistributed.

    Guardrail II: irrecoverable capital cannot carry an indefinite obligation.
    The write-down is not a monetary event — it is an acknowledgment that the
    asset no longer exists in maintainable form.

    Args:
        asset: The asset to write down (must satisfy writedown_trigger).
        workforce_size: Total employed workforce (used for human capital redistribution).
        other_assets_eoh: Total EOH generated by remaining capital (for redistribution).

    Returns:
        dict: {
          "asset_id": str,
          "teh_destroyed": float,              (add to cumulative_destroyed)
          "eoh_removed_from_ledger": float,    (annual EOH zeroed)
          "is_human_capital": bool,
          "human_capacity_lost": float,        (entropy-reduction capacity removed)
          "eoh_to_redistribute": float,        (EOH this person was fulfilling)
          "eoh_per_remaining_worker": float,   (redistributed burden, if human)
          "rebuild_eoh_needed": float,         (EOH to rebuild equivalent asset)
          "notes": str,
        }

    Reference: Mission Statement §"Guardrail II — Capital write-down";
    §"For human capital, death is a write-down. The person's personal EOH
    vanishes, but their entropy-reduction capacity also vanishes — every EOH
    they were fulfilling must be redistributed."
    """
    is_human = asset.get("is_human_capital", False)
    teh_destroyed = asset["teh_value"]
    eoh_removed   = asset["annual_eoh"]

    # For human capital: the EOH they were fulfilling must be redistributed
    eoh_to_redistribute = 0.0
    eoh_per_remaining   = 0.0
    human_capacity_lost = 0.0

    if is_human:
        human_capacity_lost = asset.get("entropy_reduction_capacity", 0.0)
        # The person was fulfilling some portion of registered EOH.
        # Redistribute that obligation to remaining workforce.
        eoh_to_redistribute = human_capacity_lost
        remaining_workforce = max(workforce_size - 1, 1.0)
        eoh_per_remaining = eoh_to_redistribute / remaining_workforce

        notes = (
            f"Human capital write-down (death). "
            f"Personal EOH of {asset.get('personal_eoh_per_year', 0):.0f} h/yr removed. "
            f"Entropy-reduction capacity of {human_capacity_lost:.0f} h/yr redistributed "
            f"across {remaining_workforce:.0f} remaining workers "
            f"({eoh_per_remaining:.2f} h/worker/yr additional burden)."
        )
    else:
        # Infrastructure/ecological write-down
        # EOH the asset was generating is zeroed (no one needs to fulfill it anymore)
        # EOH this asset was ELIMINATING is now returned to the burden stack
        eoh_returned_to_burden = asset.get("annual_eoh_eliminated", 0.0)

        # Rebuild EOH: starting over requires re-expending the original construction cost
        # plus first-year maintenance. Rough proxy: teh_value as EOH.
        rebuild_eoh = teh_destroyed

        notes = (
            f"Infrastructure write-down. "
            f"{eoh_removed:.0f} EOH/yr maintenance obligation zeroed. "
            f"Asset was eliminating {eoh_returned_to_burden:.0f} personal EOH/yr — "
            f"that burden returns to population. "
            f"Rebuild would require ~{rebuild_eoh:.0f} EOH."
        )
        eoh_to_redistribute = eoh_returned_to_burden

    return {
        "asset_id":               asset["asset_id"],
        "teh_destroyed":          teh_destroyed,
        "eoh_removed_from_ledger": eoh_removed,
        "is_human_capital":       is_human,
        "human_capacity_lost":    human_capacity_lost,
        "eoh_to_redistribute":    eoh_to_redistribute,
        "eoh_per_remaining_worker": eoh_per_remaining,
        "rebuild_eoh_needed":     teh_destroyed,
        "notes":                  notes,
    }


# ---------------------------------------------------------------------------
# Human Capital Lifecycle Events
# ---------------------------------------------------------------------------

def birth_event(
    population: float,
    eoh_ledger_total: float,
    epsilon: float = 0.40,
    personal_eoh_base: float = PERSONAL_EOH_BASE,
) -> dict:
    """
    Register a new member in the collective. Maximum personal EOH; zero capacity.

    A newborn is the highest-EOH-density event in the system: maximum personal
    entropy obligation, zero entropy-reduction capacity. The return on investment
    (care labor during childhood) is the eventual capacity of a trained adult.

    Args:
        population: Current population (before this birth).
        eoh_ledger_total: Current total EOH in the collective ledger.
        epsilon: Automation level (affects per-capita EOH).
        personal_eoh_base: EOH per working-age person per year.

    Returns:
        dict: {
          "new_population": float,
          "added_eoh_per_year": float,         (new personal EOH demand added)
          "entropy_reduction_capacity": float,  (= 0: newborns contribute nothing yet)
          "net_eoh_change_per_year": float,    (always positive: more demand, no capacity)
          "care_eoh_required_total": float,    (estimated care investment over 18 years)
          "notes": str,
        }

    Reference: Mission Statement §"A newborn is the highest-EOH-density event
    in the system: maximum personal entropy obligation, zero entropy-reduction
    capacity, requiring years of intensive labor investment before contributing."
    """
    infant_eoh_weight = AGE_GROUPS["infant"]["eoh_weight"]
    child_eoh_weight  = AGE_GROUPS["child"]["eoh_weight"]
    new_personal_eoh = personal_eoh_base * infant_eoh_weight * (1.0 - INFANT_EOH_EPSILON_FACTOR * epsilon)

    # Care investment over 18 years until productive adulthood
    # Intensive in first 6 years (infant weight), moderate 6-18 (child weight)
    care_years_intensive = AGE_GROUPS["infant"]["range"][1] + 1   # 0–5 → 6 years
    care_years_moderate  = AGE_GROUPS["child"]["range"][1] - AGE_GROUPS["child"]["range"][0] + 1  # 6–17 → 12 years
    care_investment = (personal_eoh_base * infant_eoh_weight * care_years_intensive
                       + personal_eoh_base * child_eoh_weight * care_years_moderate)

    return {
        "new_population":             population + 1,
        "added_eoh_per_year":         new_personal_eoh,
        "entropy_reduction_capacity": 0.0,   # newborns contribute nothing yet
        "net_eoh_change_per_year":    new_personal_eoh,  # all cost, no capacity
        "care_eoh_required_total":    care_investment,
        "notes": (
            f"New collective member registered. Personal EOH: {new_personal_eoh:.0f} h/yr. "
            f"Estimated care investment through adulthood: {care_investment:.0f} EOH. "
            f"Capacity: 0 h/yr until educated/trained."
        ),
    }


def death_event(
    asset: Asset,
    workforce_size: float,
    epsilon: float = 0.40,
) -> dict:
    """
    Process a human capital write-down (death). Delegates to execute_writedown.

    Death is a capital write-down: the person's personal EOH vanishes (no one
    needs to maintain them), but so does their entropy-reduction capacity. The
    EOH they were fulfilling must be redistributed — NOT abandoned, as that
    would create orphaned obligations.

    Args:
        asset: Human capital asset (is_human_capital must be True).
        workforce_size: Total workforce before this death.
        epsilon: Automation level (for context).

    Returns:
        Same as execute_writedown() plus epsilon context.

    Raises:
        ValueError: If asset is not human capital.

    Reference: Mission Statement §"For human capital, death is a write-down.
    The person's personal EOH vanishes, but their entropy-reduction capacity
    also vanishes — every EOH they were fulfilling must be redistributed to
    other workers or to automation."
    """
    if not asset.get("is_human_capital", False):
        raise ValueError(
            f"death_event() requires human capital asset; "
            f"asset {asset['asset_id']} has is_human_capital=False"
        )

    result = execute_writedown(asset, workforce_size=workforce_size)
    result["epsilon"] = epsilon
    result["new_workforce"] = max(workforce_size - 1, 0.0)
    return result


def maturation_update(
    asset: Asset,
    years_elapsed: float,
    education_eoh: float = 0.0,
    training_eoh: float = 0.0,
    epsilon: float = 0.0,
) -> dict:
    """
    Update a human capital asset's entropy-reduction capacity as it matures.

    Care economy investment (years of education, training, mentoring) converts
    the initial zero-capacity of a newborn into the productive capacity of an
    adult. Capacity grows roughly logarithmically with education investment.

    At higher ε, automation tools (simulators, personalized tutoring AI,
    precision diagnostics) amplify the return on each EOH of education.
    The leverage factor is 1 + MATURATION_AUTO_LEVERAGE × ε, applied to
    the education component only (base natural growth is biology-determined).

    Args:
        asset: Human capital asset to update.
        years_elapsed: Years since last update.
        education_eoh: EOH invested in formal education/training this period.
        training_eoh: EOH invested in skill training this period.
        epsilon: Automation level [0.0, 0.99].

    Returns:
        dict: {
          "asset_id": str,
          "capacity_delta": float,           (increase in entropy-reduction capacity)
          "new_capacity": float,
          "education_eoh_invested": float,
          "return_on_investment_ratio": float,  (lifetime capacity gain per EOH invested)
          "notes": str,
        }

    Reference: Mission Statement §"Care is capital formation — Raising children,
    educating, training, healing, and mentoring ... build the entropy-reduction
    workforce the system depends on."
    """
    total_investment = education_eoh + training_eoh

    # Capacity grows with investment but with diminishing returns
    # Each EOH invested in education yields progressively less marginal capacity
    current_cap = asset.get("entropy_reduction_capacity", 0.0)

    # Logarithmic growth model: sqrt of investment adds to capacity
    # Base growth: natural maturation with age (even without formal education)
    base_growth = _MATURATION_BASE_GROWTH_RATE * years_elapsed
    # Education multiplier: sqrt scaling for diminishing returns.
    # Automation leverage amplifies returns: precision tutoring, simulators, etc.
    automation_leverage = 1.0 + MATURATION_AUTO_LEVERAGE * epsilon
    edu_growth = (
        _MATURATION_EDU_COEFFICIENT * (total_investment ** _MATURATION_EDU_EXPONENT) * automation_leverage
        if total_investment > 0 else 0.0
    )

    capacity_delta = base_growth + edu_growth
    new_capacity = current_cap + capacity_delta

    # Design life analog: assume 40-year productive career
    career_years = 40.0
    lifetime_capacity = new_capacity * career_years
    roi = lifetime_capacity / max(total_investment, 1.0)

    return {
        "asset_id":                 asset["asset_id"],
        "capacity_delta":           capacity_delta,
        "new_capacity":             new_capacity,
        "education_eoh_invested":   total_investment,
        "return_on_investment_ratio": roi,
        "notes": (
            f"Maturation: capacity +{capacity_delta:.0f} h/yr "
            f"(base: {base_growth:.0f}, education: {edu_growth:.0f}). "
            f"New capacity: {new_capacity:.0f} h/yr. "
            f"Lifetime ROI: {roi:.1f}× investment."
        ),
    }


# ---------------------------------------------------------------------------
# D5: Estate dissolution on death
# ---------------------------------------------------------------------------

def estate_dissolution(
    teh_in_circulation: float,
    population: float,
    epsilon: float,
    annual_death_rate: float = ANNUAL_DEATH_RATE,
    inheritance_fraction: float = ESTATE_INHERITANCE_FRACTION,
    estate_levy_fraction: float = ESTATE_LEVY_FRACTION,
    personal_reserve_years: float = ESTATE_PERSONAL_RESERVE_YEARS,
) -> dict:
    """
    Aggregate TEH destroyed through estate dissolution on death.

    D5: on death, accumulated savings above a personal reserve are split into
    three streams — inherited (circulatory, passes to heirs), levied to Trust
    (circulatory, funds collective obligations), and written down (destroyed).

    The personal reserve = personal_reserve_years × basket_price(ε). It is
    passed to heirs unconditionally. As ε rises and basket prices fall, the
    reserve shrinks in TEH terms: at high automation a given TEH amount covers
    more years, so less reserve is needed and more of the estate enters
    dissolution. This is coherent — high-ε savings are worth more in real terms.

    The aggregate model uses per-capita circulating TEH as the estate proxy,
    since the simulation does not track individual holdings. This understates
    dissolution for the wealthiest decedents and overstates it for the poorest;
    the aggregate effect is unbiased at the mean.

    Ledger effects:
      - teh_destroyed:       removed from existence (write-down)
      - teh_levied_to_trust: moves from circulation to Trust (add to trust balance)
      - teh_inherited:       stays in circulation (passes to heirs, no net change)

    Args:
        teh_in_circulation: TEH in free circulation (total_supply − Trust − capital).
        population: Total population.
        epsilon: ε ∈ [0, 0.99].
        annual_death_rate: Fraction of population dying per year. Default: 0.010.
        inheritance_fraction: Fraction of excess above reserve passed to heirs.
        estate_levy_fraction: Fraction of excess levied to Trust.
        personal_reserve_years: Years of basket costs preserved unconditionally.

    Returns:
        dict: {
            "teh_destroyed":        float,   written down
            "teh_levied_to_trust":  float,   circulatory → Trust
            "teh_inherited":        float,   circulatory → heirs
            "deaths_this_period":   float,
            "per_capita_teh":       float,
            "personal_reserve":     float,   TEH per person preserved unconditionally
            "excess_per_estate":    float,   TEH above reserve per deceased
            "mechanism":            "D5_estate",
        }

    Reference: Mission Statement §"Guardrail II — Capital write-down";
    human capital write-down (death) extended to accumulated savings above
    what a member of the collective could reasonably consume in remaining life.
    """
    from hours_eoh.core.prices import basket_price as _basket_price

    per_capita_teh   = teh_in_circulation / max(population, 1.0)
    personal_reserve = personal_reserve_years * _basket_price(epsilon)
    excess_per_estate = max(0.0, per_capita_teh - personal_reserve)

    deaths        = population * annual_death_rate
    total_excess  = deaths * excess_per_estate

    writedown_fraction = max(0.0, 1.0 - inheritance_fraction - estate_levy_fraction)

    teh_destroyed  = total_excess * writedown_fraction
    teh_levied     = total_excess * estate_levy_fraction
    # Reserve passes to heirs in full; excess inheritance share also passes to heirs
    teh_inherited  = deaths * personal_reserve + total_excess * inheritance_fraction

    return {
        "teh_destroyed":       teh_destroyed,
        "teh_levied_to_trust": teh_levied,
        "teh_inherited":       teh_inherited,
        "deaths_this_period":  deaths,
        "per_capita_teh":      per_capita_teh,
        "personal_reserve":    personal_reserve,
        "excess_per_estate":   excess_per_estate,
        "mechanism":           "D5_estate",
    }


# ---------------------------------------------------------------------------
# Aggregate EOH eliminated across a capital fleet
# ---------------------------------------------------------------------------

def aggregate_eoh_eliminated(
    assets: list[Asset],
) -> dict:
    """
    Sum annual_eoh_eliminated across a fleet of capital assets.

    Mirrors aggregate_personal_eoh_fulfilled(). The total feeds into
    total_eoh(capital_eoh_eliminated=...) to proportionally reduce
    infrastructure, ecological, and knowledge EOH obligations.

    Each asset's annual_eoh_eliminated is set by make_asset() and updated
    after execute_writedown() zeroes it. Zero-value assets (no EOH
    elimination capacity) contribute nothing.

    Args:
        assets: List of Asset dicts. Missing annual_eoh_eliminated treated as 0.

    Returns:
        dict: {
          "total_eoh_eliminated": float,
          "asset_count":          int,
        }

    Reference: Mission Statement §"Infrastructure EOH — capital stock eliminates
    EOH by handling obligations that would otherwise require direct human labor."
    """
    total = sum(a.get("annual_eoh_eliminated", 0.0) for a in assets)
    return {
        "total_eoh_eliminated": total,
        "asset_count":          len(assets),
    }


# ---------------------------------------------------------------------------
# Apply birth EOH to the collective ledger
# ---------------------------------------------------------------------------

def apply_birth_eoh(
    birth_result: dict,
    current_total_personal_eoh: float,
) -> dict:
    """
    Apply the EOH impact of a birth event to the collective ledger.

    Symmetric to apply_death_redistribution() in workforce.py: a birth adds
    personal EOH demand without adding any fulfillment capacity. This function
    makes the birth event's ledger commitment explicit — the caller updates
    their running personal EOH total from the return value.

    Without this step, birth_event()'s added_eoh_per_year is informational
    only. Calling apply_birth_eoh() closes the loop by committing the new
    obligation to the tracked total, ensuring the EOH ledger stays accurate
    as population changes.

    Args:
        birth_result: Return dict from birth_event(). Must contain
                      "added_eoh_per_year" and "new_population".
        current_total_personal_eoh: Running total personal EOH before this birth.

    Returns:
        dict: {
          "added_eoh_per_year":       float,  (= birth_result["added_eoh_per_year"])
          "new_total_personal_eoh":   float,  (current + added)
          "new_population":           float,  (= birth_result["new_population"])
          "capacity_added":           float,  (always 0 — newborns add no capacity)
          "net_burden_increase":      float,  (= added_eoh_per_year; always positive)
        }

    Reference: Mission Statement §"A newborn is the highest-EOH-density event
    in the system: maximum personal entropy obligation, zero entropy-reduction
    capacity."
    """
    added_eoh   = float(birth_result.get("added_eoh_per_year", 0.0))
    new_pop     = float(birth_result.get("new_population", 0.0))
    new_total   = current_total_personal_eoh + added_eoh

    return {
        "added_eoh_per_year":     added_eoh,
        "new_total_personal_eoh": new_total,
        "new_population":         new_pop,
        "capacity_added":         0.0,
        "net_burden_increase":    added_eoh,
    }
