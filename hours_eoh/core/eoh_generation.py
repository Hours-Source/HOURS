"""
EOH Generation Functions

Model the four entropy domains. These functions return the total EOH generated
by each domain — the labor demand that physical reality creates. EOH generation
is independent of who fulfills it (human or machine). The human share is
handled separately by human_eoh_share() in eoh_fulfillment.py.

**Physical state design**: EOH generation functions take physical state parameters
(capital_stock, ecosystem_health, monitoring_capability, knowledge_base_size,
age_distribution). They do NOT use ε as a proxy for unspecified physical state.
For cross-sectional analysis at a given ε, use trajectory.canonical_physical_state(ε)
to obtain the canonical physical state and pass it explicitly.

Each function retains an optional `epsilon` keyword for backward compatibility.
When provided, it fills in canonical-trajectory defaults for any physical state
not otherwise specified. New code should pass physical state directly.

Mission Statement: §"The four entropy domains" (personal, infrastructure,
ecological, knowledge); §"What an economy is" — civilization's organized
resistance to entropy; §"Guardrail I — Physical grounding" — EOH rates derived
from measurable physical indicators, not from policy or fiscal convenience.
"""

from __future__ import annotations
import math
from typing import TypedDict

from hours_eoh.data import (
    INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT,
    INFRA_MAINT_RATE,
    INFRA_AGE_FACTOR_MAX,
    ECOLOGICAL_THRESHOLD,
    AGE_GROUPS, ESSENTIAL_DOMAINS,
    PERSONAL_EOH_BASE, PERSONAL_EOH_SURVIVAL, PERSONAL_EOH_SUFFICIENCY,
    CAPITAL_STOCK_DEFAULT, ECOLOGICAL_BASE_RATE, ECOLOGICAL_INTENSITY_BASE,
    ECOLOGICAL_THRESHOLD, LAND_HECTARES_PER_CAPITA, US_MAINLAND_HECTARES,
    ECOLOGICAL_SPIKE_INTENSITY,
    INFRA_MAINT_RATE, KNOWLEDGE_EOH_BASE,
    KNOWLEDGE_EPS_EXPONENT, KNOWLEDGE_REFERENCE_POPULATION, SKILL_DECAY_RATE,
    SKILL_TRANSMISSION_RATE, SKILL_CPD_RATE,
    PERSONAL_EOH_COMPONENTS, ABATEMENT_HALF_CAPITAL_TEH,
    CANONICAL_CAPITAL_GROWTH_SLOPE,
    CANONICAL_MONITORING_CAPABILITY_BASE,
    CANONICAL_MONITORING_CAPABILITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_EXP,
    MEAN_MULTIPLIER_REFERENCE,
)


# ---------------------------------------------------------------------------
# EOH generation calibration constants (physics, not trajectory)
# ---------------------------------------------------------------------------
# ECOLOGICAL_SPIKE_INTENSITY migrated to data.py 2026-08-28 as
# ECOLOGICAL_SPIKE_INTENSITY. It was named as calibrated-to-target on
# 2026-08-09 and stayed a shadow constant for the whole period since.
# Trajectory-scaling constants (CANONICAL_*) are in data.py and used only
# when epsilon is provided as a backward-compat canonical-trajectory lookup.


def _resolve_monitoring_capability(
    monitoring_capability: float | None,
    epsilon: float | None,
) -> float:
    """
    Resolve the effective monitoring capability from optional explicit and epsilon inputs.

    Priority: explicit value > epsilon-derived canonical > canonical base (ε=0 default).
    Shared by ecological_eoh() and ecological_eoh_breakdown() to keep the resolution
    logic in one place.
    """
    if monitoring_capability is not None:
        return max(0.0, min(1.0, monitoring_capability))
    if epsilon is not None:
        return CANONICAL_MONITORING_CAPABILITY_BASE + CANONICAL_MONITORING_CAPABILITY_SLOPE * epsilon
    return CANONICAL_MONITORING_CAPABILITY_BASE


# ---------------------------------------------------------------------------
# Personal EOH — the standards selector
# ---------------------------------------------------------------------------

#: The three values `PERSONAL_EOH_BASE` was doing the work of. See the STANDARDS
#: SPLIT block in data.py for why they are distinct.
PERSONAL_STANDARDS: dict[str, float] = {
    "survival":    PERSONAL_EOH_SURVIVAL,     # S_a — autarky-referenced, hard-bounded
    "sufficiency": PERSONAL_EOH_SUFFICIENCY,  # F_a — autarky-referenced, may exceed supply
    "collapsed":   PERSONAL_EOH_BASE,         # F_a × (1 − a(K)) placeholder; the default
}


def personal_base_for(standard: str) -> float:
    """
    The per-working-age-equivalent obligation for a named standard.

    Governing distinction (data.py §"THE STANDARDS SPLIT"):

        "survival"     S_a  what must be met or people die. AUTARKY-referenced
                            and HARD-bounded: S_a ≤ (L − R)/w, because a survival
                            standard exceeding labour supply means extinction.
        "sufficiency"  F_a  what a decent life costs, AUTARKY-referenced. Allowed
                            to exceed labour supply — that gap is why collectives
                            form, not a defect.
        "collapsed"    the abatement-collapsed operating value used by the
                            generation default until Block II builds a(K).

    Why "collapsed" is the default and not "sufficiency": the operating value is
    F_a × (1 − a(K)), and a(K) does not exist yet. Defaulting to F_a would assert
    zero abatement — that infrastructure never reduces the obligation, only who
    serves it — which is precisely the simplification the abatement work exists
    to remove.

    units: hours/year per working-age-equivalent.
    ε-behavior: none — these are standards, not trajectories. The ε-dependence
    arrives with abatement.

    Args:
        standard: "survival" | "sufficiency" | "collapsed".

    Returns:
        The base rate in h/yr per working-age-equivalent.

    Raises:
        ValueError: on an unknown standard.

    Worked example: `personal_base_for("survival")` = 600, which at the shipped
    age weighting w = 1.475 is 885 h/person·yr — inside the 924 h/person·yr
    autarky supply, so ε_suff = 0 and subsistence survives without automation.
    """
    if standard not in PERSONAL_STANDARDS:
        raise ValueError(
            f"standard must be one of {sorted(PERSONAL_STANDARDS)}, got {standard!r}"
        )
    return PERSONAL_STANDARDS[standard]


def max_abatement() -> float:
    """
    a_max — the ceiling on how much of the personal obligation infrastructure can
    ever remove. DERIVED, not chosen:

        a_max = Σ_component  share · abatability

    over `PERSONAL_EOH_COMPONENTS`. At shipped values a_max = 0.4483, and the
    55.2% that survives is **84.4% care** — the anti-correlation the block
    predicts, falling out of the weights rather than being asserted.

    units: dimensionless ∈ [0, 1].
    """
    return sum(c["share"] * c["abatability"] for c in PERSONAL_EOH_COMPONENTS.values())


def abatement_fraction(
    capital_per_capita_teh: float,
    half_capital: float = ABATEMENT_HALF_CAPITAL_TEH,
    a_max: float | None = None,
) -> float:
    """
    a(K) — the fraction of the personal obligation that infrastructure REMOVES.

    Governing equation (hyperbolic saturation):

        a(K) = a_max · K / (K + K_half)

        a(0)   = 0        no apparatus, no abatement — autarky by definition
        a(K_half) = a_max/2
        a(∞)   = a_max    bounded by what is physically abatable, not by capital

    This is the mechanism the model was missing. Before it, personal EOH was flat
    across the entire arc and infrastructure only changed WHO served the
    obligation. Physically, a tap replaces water hauling and sanitation cuts the
    disease burden that drives care hours — the obligation itself falls.

    Saturating rather than linear because the components run out: once the water
    is piped there is no more hauling to remove, and the residual is care, which
    barely abates at all.

    units: dimensionless ∈ [0, a_max]. K in TEH per capita.
    ε-behavior: no ε appears. Abatement is a function of the CAPITAL STOCK, not
    of the automation score — which is what lets it be composed with ε rather
    than double-counting against it. ε says who serves the remaining obligation;
    a(K) says how much obligation remains.

    Args:
        capital_per_capita_teh: K, capital stock per capita (≥ 0).
        half_capital: K_half (> 0). The CHOSEN pace constant — see data.py.
        a_max: Ceiling override. None (default) derives it from the components.

    Returns:
        a(K) ∈ [0, a_max].

    Raises:
        ValueError: on negative capital, non-positive half_capital, or an a_max
            outside [0, 1].

    Worked example: at the standard-tier inventory (~1,900 TEH/capita) and
    K_half = 1,000, a = 0.4483 × 0.655 = 0.294 — so sufficiency-under-collective
    is 1,500 × (1 − 0.294) = 1,059 h/yr per working-age-equivalent against the
    autarky 1,500.
    """
    if capital_per_capita_teh < 0.0:
        raise ValueError(
            f"capital_per_capita_teh must be ≥ 0, got {capital_per_capita_teh}"
        )
    if half_capital <= 0.0:
        raise ValueError(f"half_capital must be > 0, got {half_capital}")
    cap = max_abatement() if a_max is None else a_max
    if not 0.0 <= cap <= 1.0:
        raise ValueError(f"a_max must be in [0, 1], got {cap}")
    k = capital_per_capita_teh
    return cap * k / (k + half_capital)


def abated_personal_base(
    capital_per_capita_teh: float,
    standard: str = "sufficiency",
    half_capital: float = ABATEMENT_HALF_CAPITAL_TEH,
) -> float:
    """
    B(K) = X_a × (1 − a(K)) — the autarky-referenced standard, abated by capital.

    This is the quantity `PERSONAL_EOH_BASE` stands in for. Once abatement is
    adopted as the default generation path, the collapsed placeholder retires and
    the operating value is computed here instead of asserted.

    units: hours/year per working-age-equivalent.
    ε-behavior: none directly — see `abatement_fraction` on why abatement is
    capital-driven rather than ε-driven.

    Args:
        capital_per_capita_teh: K, capital stock per capita.
        standard: Which autarky-referenced standard to abate — "sufficiency"
            (default, F_a) or "survival" (S_a). "collapsed" is rejected: it is
            already an abated value, so abating it again double-counts.
        half_capital: K_half.

    Returns:
        The abated base in h/yr per working-age-equivalent.

    Raises:
        ValueError: if standard is "collapsed" or unknown.

    Worked example: F_a = 1,500 at K = 1,900 TEH/capita → 1,059. Compare the
    shipped collapsed placeholder of 1,000, which the mechanism now replaces
    with something that has an economy behind it.
    """
    if standard == "collapsed":
        raise ValueError(
            "'collapsed' is already an abated value — abating it double-counts. "
            "Use 'sufficiency' (F_a) or 'survival' (S_a)."
        )
    base = personal_base_for(standard)
    return base * (1.0 - abatement_fraction(capital_per_capita_teh, half_capital))


def personal_eoh(
    population: float,
    age_distribution: dict[str, float] | None = None,
    epsilon: float | None = None,
    base_rate: float = PERSONAL_EOH_BASE,
    standard: str | None = None,
) -> float:
    """
    Total personal EOH generated by the population.

    Personal EOH is pure biology — the entropy obligations that human bodies
    generate simply by existing. Biology does not change with automation; what
    changes is the human vs. machine share of fulfillment (handled by
    human_eoh_share() in eoh_fulfillment.py).

    **Physical state input**: age_distribution is the explicit physical parameter.
    If None and epsilon is provided, the canonical age distribution for that ε
    is used (trajectory.canonical_age_distribution(ε)). If both are None, the
    AGE_GROUPS default fractions are used.

    Args:
        population: Total population count.
        age_distribution: Dict mapping group name → fraction of population.
                          Keys must match AGE_GROUPS. Defaults to AGE_GROUPS
                          fractions (or canonical arc if epsilon is provided).
        epsilon: Optional automation level [0.0, 0.99]. When provided and
                 age_distribution is None, fills in the canonical age distribution
                 for that ε. Does not otherwise affect the physics.
        base_rate: Personal EOH per working-age-equivalent person per year (hours).
                   Default: PERSONAL_EOH_BASE (1000 h/yr) — the abatement-collapsed
                   operating value. Ignored when `standard` is given.
        standard: OPTIONAL named standard — "survival" | "sufficiency" |
                  "collapsed" — which overrides `base_rate` via
                  `personal_base_for()`. None (default) uses `base_rate` as
                  passed, so every existing caller is unaffected.

                  The two are mutually exclusive by intent: `base_rate` is for a
                  caller that has its own number, `standard` for one that wants
                  the framework's. Passing both is not an error; `standard` wins,
                  and that is stated rather than silently resolved.

    Returns:
        Total personal EOH (hours/year) — the demand signal, not the supply.

    Worked example (1M people, shipped age weighting w = 1.475):
        standard="survival"     →   885M h/yr   (885 h/person·yr)
        standard="collapsed"    → 1,475M h/yr   (1,475)
        standard="sufficiency"  → 2,213M h/yr   (2,213)
    The survival figure fits inside an autarky labour supply of ~924 h/person·yr;
    the sufficiency figure does not, and is not meant to.

    Reference: Mission Statement §"Personal EOH — the entropy of human bodies";
    §"Biology does not change with automation." Standards split: data.py
    §"THE STANDARDS SPLIT".
    """
    if standard is not None:
        base_rate = personal_base_for(standard)
    if age_distribution is None:
        if epsilon is not None:
            from hours_eoh.core.trajectory import canonical_age_distribution
            age_distribution = canonical_age_distribution(epsilon)
        else:
            age_distribution = {k: v["fraction"] for k, v in AGE_GROUPS.items()}

    weighted_pop = 0.0
    for group, fraction in age_distribution.items():
        weight = AGE_GROUPS[group]["eoh_weight"] if group in AGE_GROUPS else 1.0
        weighted_pop += population * fraction * weight

    return weighted_pop * base_rate


# ---------------------------------------------------------------------------
# Infrastructure EOH
# ---------------------------------------------------------------------------

def infrastructure_eoh(
    capital_stock: float,
    capital_age_ratio: float = 0.50,
    epsilon: float | None = None,
    base_maint_rate: float = INFRA_MAINT_RATE,
    age_factor_max: float = INFRA_AGE_FACTOR_MAX,
) -> float:
    """
    Total infrastructure EOH generated by the built capital stock.

    Infrastructure maintenance burden scales with (a) the size of the capital
    stock and (b) how old/degraded the assets are. EOH generation is a property
    of what has been built, not of the automation level per se.

    **Physical state input**: capital_stock is the ACTUAL current stock in TEH
    (not an ε=0 baseline). The simulation tracks actual capital stock as it grows
    through investment; that value is passed directly here. The stewardship
    economy's core dynamic — growing capital stock generating growing entropy
    obligations — is expressed by passing the actual stock, which grows as
    simulate_period() invests each period.

    **Backward compatibility**: If epsilon is provided, capital_stock is treated
    as the ε=0 baseline and the canonical capital growth factor is applied:
    effective_capital = capital_stock × (1 + CANONICAL_CAPITAL_GROWTH_SLOPE × ε).
    This preserves existing test and cross-sectional analysis behaviour.
    New simulation code should track actual capital stock and omit epsilon.

    Args:
        capital_stock: Actual current capital stock in TEH. When epsilon is
                       provided (legacy), treated as ε=0 baseline and scaled.
        capital_age_ratio: Mean(current_age / design_life) across assets, ∈ [0, 1].
                           0 = all brand-new; 1 = all at end of design life.
        epsilon: Optional. When provided, applies canonical capital growth scaling
                 for backward compatibility. New code should omit this and pass
                 actual capital stock directly.
        base_maint_rate: EOH per TEH of capital at age_ratio=0 (fraction/year).
        age_factor_max: Maximum maintenance multiplier at capital_age_ratio=1.

    Returns:
        Total infrastructure EOH (hours/year).

    Reference: Mission Statement §"Infrastructure EOH — the entropy of built systems";
    §"The stewardship economy — growing capital stock generates growing entropy
    obligations, shifting the economy toward maintenance."
    """
    age_factor = 1.0 + (age_factor_max - 1.0) * capital_age_ratio
    if epsilon is not None:
        # Legacy: capital_stock is ε=0 baseline; apply canonical growth
        effective_capital = capital_stock * (1.0 + CANONICAL_CAPITAL_GROWTH_SLOPE * epsilon)
    else:
        effective_capital = capital_stock
    return effective_capital * base_maint_rate * age_factor


def statutory_hours_per_unit_year(
    crew_hours_per_visit: float,
    interval_months: float = INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT,
) -> float:
    """
    Annual inspection labour per asset, from the statutory interval.

    Governing equation:

        hours_per_unit_year = (12 / interval_months) · crew_hours_per_visit

    units: labour-hours per asset per year.

    THIS FORMULA WAS ALREADY THE DOCUMENTED DERIVATION and nothing implemented
    it. `infrastructure_statutory_floor` names it in its own docstring as how a
    caller obtains `hours_per_unit_year`, while
    `INFRA_STATUTORY_INTERVAL_MONTHS_DEFAULT` — the 24-month routine interval
    adopted from **23 CFR 650**, a US federal regulation — sat in `data.py`
    tagged, provenance-audited and read by NOTHING. A statute-backed convention
    that no code path can reach is a convention nobody is actually following.

    NO MONEY ENTERS. An interval is a count of months and a crew-visit is a
    count of hours, so the whole chain stays currency-free — the property that
    made the statutory floor doctrine-invariant (spread 1.000 against the
    monetized path's 10.26×) and the reason it is the auditable stream.

    Worked example: the 23 CFR 650 routine interval of 24 months at 16
    crew-hours per visit gives (12/24) × 16 = **8.0 h/asset·yr** — the "good"
    bucket in `infrastructure_statutory_floor`'s own worked example.

    Args:
        crew_hours_per_visit: Labour-hours one inspection visit costs.
        interval_months: Months between routine inspections. Defaults to the
            US statutory routine interval; supply your jurisdiction's own.

    Raises:
        ValueError: on a non-positive interval or negative crew hours.
    """
    if interval_months <= 0.0:
        raise ValueError(f"interval_months must be > 0, got {interval_months}")
    if crew_hours_per_visit < 0.0:
        raise ValueError(
            f"crew_hours_per_visit must be >= 0, got {crew_hours_per_visit}"
        )
    return (12.0 / interval_months) * crew_hours_per_visit


def infrastructure_statutory_floor(asset_census: list[dict]) -> float:
    """
    Task-normative infrastructure EOH floor from a physical condition census —
    currency-free.

    Governing equation:
        floor = Σ_bucket  count · hours_per_unit_year

    Each census bucket is a physical count of assets in a given condition and the
    task-normative labour-hours per unit per year to inspect/maintain them (e.g.
    (12 / inspection_interval_months) · crew_hours_per_visit). No money→hours
    conversion enters — this is the auditable, measured stream. Motivated by the
    NBI calibration (the infrastructure-floor handoff): flipping any physical knob moves
    this floor; flipping an accounting convention does not, because there is none.

    units: hours/year. ε-behavior: none — maintenance burden is a property of what
    is built and its condition, not of the automation level (ε enters fulfilment,
    not this generation floor).

    Worked example: 8,019 good @ 8 h + 12,482 fair @ 20 h + 2,813 poor @ 48 h
        = 64,152 + 249,640 + 135,024 = 448,816 h/yr.

    Args:
        asset_census: list of buckets, each a dict with keys
            "count" (float ≥ 0) and "hours_per_unit_year" (float ≥ 0).

            OPTIONAL thermal keys are read by the census's other consumer and
            IGNORED here: "type" (a CAPITAL_THERMAL_PROFILES key), "teh_per_unit",
            "condition", "design_life_years". The same physical inventory yields
            both the labour floor (hours, this function) and the dissipation floor
            (watts, research/thermal_capital.infrastructure_thermal_floor) — the
            §12.2 dual-output property at census granularity. Specifying them
            together costs nothing; retrofitting means re-surveying.

    Returns:
        Total statutory-floor EOH (hours/year).

    Raises:
        ValueError: if any count or hours_per_unit_year is negative or a bucket
            is missing a required key.

    Reference: the infrastructure-floor handoff §4.4 (statutory floor survives); Mission
    Statement Guardrail I (physical grounding).
    """
    total = 0.0
    for i, bucket in enumerate(asset_census):
        try:
            count = float(bucket["count"])
            hpu = float(bucket["hours_per_unit_year"])
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"census bucket {i} needs 'count' and 'hours_per_unit_year': {bucket!r}"
            ) from exc
        if count < 0.0 or hpu < 0.0:
            raise ValueError(f"census bucket {i} has negative count/hours: {bucket!r}")
        total += count * hpu
    return total


#: Why a basket component contributes nothing to the floor. These are different
#: facts about the world and the distinction is the floor's load-bearing one, so
#: the vocabulary is importable rather than re-typed at each call site.
REASON_UNMEASURED: str = "unmeasured"            # a path may exist; nobody costed it
REASON_BELOW_MIN_EPSILON: str = "below_min_epsilon"  # no path at this automation level


def ecological_statutory_floor(land_census: list[dict]) -> dict:
    """
    Task-normative ecological EOH floor from a physical land census — currency-free.

    Governing equation:

        floor = Σ_parcel  area_hectares · hours_per_hectare_year

    The third and last of the currency-free floors, after
    `infrastructure_statutory_floor` (condition census × treatment hours) and
    `personal_statutory_floor` (physical basket × delivery productivity). Same
    determinacy property: flipping a physical knob moves this floor, flipping an
    accounting convention does not, because there is none.

    WHY THIS EXISTS — THE DOMAIN-BALANCE DEFECT
    -------------------------------------------
    `ECOLOGICAL_BASE_RATE` is documented as a RELATIVE anchor — it "does not
    represent an absolute ecosystem-specific count" — but `total_eoh()` sums it
    with absolute counts and then divides the result into ε. At defaults the
    ecological domain lands at **0.6 h/person·yr, under 0.1% of total EOH**, so
    it cannot move ε and the thermal obligation it carries books at roughly one
    part in a thousand of the ledger.

    This function is the absolute footing that constant's `resolves_by` names. It
    does NOT set the number: no stewardship-hours census exists in this repo, and
    inventing one would be the fitted-residual error the personal floor was built
    to avoid. What it does is make the domain **measurable**, so that a census —
    agency FTEs per hectare, or the GUF parcel inventory × measured crew-hours —
    can retire the anchor when one arrives.

    UNPRICED IS EXCLUDED, NOT ZERO. A parcel whose `hours_per_hectare_year` is
    None has no costed stewardship path; it is owed and unquantified. Such
    parcels are returned in `unpriced` WITH their area, and excluded from
    `floor_hours` rather than contributing zero — the same load-bearing behaviour
    as the personal floor, for the same reason. `coverage` is the fraction of
    censused AREA that is priced, and a caller adding `floor_hours` to anything
    must read it first.

    units: hours/year (absolute, not per capita — divide by population yourself).
    ε-behavior: none. Stewardship burden is a property of the land and its
    condition, not of the automation level; ε enters fulfilment, not this
    generation floor.

    Worked example (a 1M-person collective, 1.86 ha/person of land):
        [{"biome": "cropland",  "area_hectares": 5.0e5, "hours_per_hectare_year": 12.0},
         {"biome": "managed_forest", "area_hectares": 4.0e5, "hours_per_hectare_year": 1.5},
         {"biome": "wilderness", "area_hectares": 9.6e5, "hours_per_hectare_year": None}]
        floor_hours = 5.0e5·12.0 + 4.0e5·1.5 = 6.6e6 h/yr
        coverage    = 9.0e5 / 1.86e6 = 0.484
        → 6.6 h/person·yr over the priced 48.4% of area, against the relative
          anchor's 0.6 h/person·yr over ALL of it. The gap is the finding.

    Args:
        land_census: list of parcels, each a dict with keys
            "area_hectares" (float ≥ 0) and "hours_per_hectare_year"
            (float ≥ 0, or None for "no costed stewardship path").
            OPTIONAL: "biome" (str) — carried through to the returned records
            so an unpriced parcel can be named in a report.

    Returns:
        dict with keys:
            "floor_hours"   float  — Σ over PRICED parcels only (hours/year)
            "area_total"    float  — all censused area (hectares)
            "area_priced"   float  — area with a costed path (hectares)
            "coverage"      float  — area_priced / area_total, 0.0 if no area
            "unpriced"      list   — [{"biome", "area_hectares"}, ...]
            "mean_hours_per_hectare" float — floor_hours / area_priced, 0.0 if none

    Raises:
        ValueError: if a parcel is missing "area_hectares", or any area or
            hours value is negative.

    Reference: reconciliation §9 (domain balance); the infrastructure floor's
    determinacy result (scenarios/infrastructure_floor.py, doctrine spread 1.000).
    """
    floor_hours = 0.0
    area_total = 0.0
    area_priced = 0.0
    unpriced: list[dict] = []

    for i, parcel in enumerate(land_census):
        try:
            area = float(parcel["area_hectares"])
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"land census parcel {i} needs 'area_hectares': {parcel!r}"
            ) from exc
        if area < 0.0:
            raise ValueError(f"land census parcel {i} has negative area: {parcel!r}")

        area_total += area
        hph = parcel.get("hours_per_hectare_year")

        if hph is None:
            unpriced.append({
                "biome": parcel.get("biome", f"parcel_{i}"),
                "area_hectares": area,
            })
            continue

        hph = float(hph)
        if hph < 0.0:
            raise ValueError(f"land census parcel {i} has negative hours: {parcel!r}")

        floor_hours += area * hph
        area_priced += area

    return {
        "floor_hours": floor_hours,
        "area_total": area_total,
        "area_priced": area_priced,
        "coverage": (area_priced / area_total) if area_total > 0.0 else 0.0,
        "unpriced": unpriced,
        "mean_hours_per_hectare": (
            floor_hours / area_priced if area_priced > 0.0 else 0.0
        ),
    }


class PersonalFloor(TypedDict):
    """The return of personal_statutory_floor(). `coverage` governs the rest."""

    floor_hours: float
    by_component: dict[str, float]
    unreachable: list[dict]
    coverage: float
    epsilon: float


def _basket_coverage(basket: list[dict], priced: dict[str, float]) -> float:
    """
    How much of the basket the floor actually covers, by declared share where
    every component states one and by count otherwise.

    Derived after pricing rather than accumulated during it, so the pricing loop
    carries no bookkeeping that an early `continue` could skip.
    """
    if not basket:
        return 0.0
    shares = [component.get("share") for component in basket]
    if any(share is None for share in shares):
        return len(priced) / len(basket)
    total = sum(float(share) for share in shares if share is not None)
    if total <= 0.0:
        return len(priced) / len(basket)
    return sum(
        float(component["share"]) for component in basket
        if component["component"] in priced
    ) / total


def personal_statutory_floor(
    basket: list[dict],
    epsilon: float = 0.0,
) -> PersonalFloor:
    """
    Task-normative personal EOH floor from a physical needs basket — currency-free,
    and the twin of infrastructure_statutory_floor().

    Governing equation (per component, then summed):

        floor = Σ_component  quantity_per_person_year · hours_per_unit

    where `quantity` is a physical requirement (kcal, litres, m², degree-days,
    interventions) and `hours_per_unit` is its inverse delivery productivity —
    labour-hours per physical unit at a stated delivery path. No money→hours
    conversion enters, and no observed spending enters. This is the personal
    domain's answer to the same determinacy problem the infrastructure floor
    solved: flipping a physical knob moves the floor, flipping an accounting
    convention does not, because there is none.

    WHY A NORMATIVE FLOOR AND NOT OBSERVED HOURS. Time use measures what a
    population spends, which is the obligation plus institutionally-induced
    hours minus obligation gone unserved:

        observed = obligation − deferred + extraction

    One observable, three unknowns. A floor computed from physical quantities at
    a stated delivery productivity is `obligation` by construction — extraction
    cannot enter it, because nothing here is derived from what anyone was
    observed to do or paid.

    UNREACHABLE IS NOT ZERO — the load-bearing behaviour. A component whose
    `hours_per_unit` is None, or whose `min_epsilon` exceeds the ε asked for, has
    NO delivery path at that automation level: the quantity is owed and cannot be
    delivered at any price in unassisted human labour. Q/P is undefined, not
    large. Such components are returned in `unreachable` — each WITH ITS REASON,
    because "nobody has measured this yet" and "no human labour can deliver this"
    are different facts about the world — and are EXCLUDED from `floor_hours`
    rather than silently contributing zero. A caller that adds `floor_hours` to
    anything must read `coverage` first.

    units: hours per person per year. ε-behavior: the floor is a STEP function of
    ε — physical requirements do not depend on the automation level, but which of
    them have a delivery path does. Components without `min_epsilon` are
    reachable at every ε including 0.

    Args:
        basket: list of components, each a dict with keys
            "component" (str), "quantity_per_person_year" (float ≥ 0),
            "hours_per_unit" (float ≥ 0, or None for "no delivery path").
            OPTIONAL: "min_epsilon" (float, default 0.0) — the automation level
            below which this component has no delivery path, the step-in term for
            entitlements with no unassisted route; "share" (float) — the
            component's intended share of the whole basket, used to weight
            `coverage`; "unit" (str) — documentation only.
        epsilon: automation level the floor is asked for, ∈ [0, 1].

    Returns:
        dict: {
          "floor_hours":   float,  Σ over components WITH a delivery path
          "by_component":  {name: hours},
          "unreachable":   [{"component": name, "reason": str}, ...],
                                   owed, no delivery path at this ε. reason is
                                   REASON_UNMEASURED (hours_per_unit is None —
                                   the path may exist, nobody has costed it) or
                                   REASON_BELOW_MIN_EPSILON (the path does not
                                   exist at this automation level)
          "coverage":      float,  share of the basket priced, by "share" if every
                                   component carries one, else by count
          "epsilon":       float,
        }

    Worked example: nutrition alone — 767,025 kcal/person·yr at 2,317.8 kcal per
    labour-hour (LSMS-ISA unassisted stratum) → 767,025 × 4.3153e-4 = 331.0 h/yr,
    with health unreachable at ε = 0 and `coverage` reporting how much of the
    basket that 331.0 actually covers.

    Raises:
        ValueError: if a component is missing a required key, or carries a
            negative quantity or hours_per_unit.

    Reference: the personal-obligation handoff §0.1 (the basket must be pinned to physical
    quantities or the parameter is unfalsifiable), §0.3 (survival core vs
    entitlement augmentation — health has no ε=0 delivery path); Mission
    Statement Guardrail I (physical grounding).
    """
    total = 0.0
    by_component: dict[str, float] = {}
    unreachable: list[dict] = []

    for i, component in enumerate(basket):
        try:
            name = str(component["component"])
            quantity = float(component["quantity_per_person_year"])
            raw_hours = component["hours_per_unit"]
            hours_per_unit = None if raw_hours is None else float(raw_hours)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"basket component {i} needs 'component', 'quantity_per_person_year' "
                f"and 'hours_per_unit' (None means no delivery path): {component!r}"
            ) from exc
        if quantity < 0.0 or (hours_per_unit is not None and hours_per_unit < 0.0):
            raise ValueError(
                f"basket component {i} has negative quantity/hours_per_unit: {component!r}"
            )

        # Order matters: a component below its step-in threshold has no delivery
        # path at all, which is a stronger statement than "not yet costed".
        if epsilon < float(component.get("min_epsilon", 0.0)):
            unreachable.append({"component": name, "reason": REASON_BELOW_MIN_EPSILON})
            continue
        if hours_per_unit is None:
            unreachable.append({"component": name, "reason": REASON_UNMEASURED})
            continue

        by_component[name] = quantity * hours_per_unit
        total += by_component[name]

    return PersonalFloor(
        floor_hours=total,
        by_component=by_component,
        unreachable=unreachable,
        coverage=_basket_coverage(basket, by_component),
        epsilon=epsilon,
    )


def infrastructure_eoh_breakdown(
    capital_stock: float | None = None,
    capital_age_ratio: float = 0.50,
    asset_census: list[dict] | None = None,
    discretionary_eoh: float = 0.0,
    deferred_stock: float = 0.0,
    monitoring_capability: float | None = None,
    epsilon: float | None = None,
    base_maint_rate: float = INFRA_MAINT_RATE,
    age_factor_max: float = INFRA_AGE_FACTOR_MAX,
    assessment_id: str = "none",
) -> dict:
    """
    Infrastructure EOH split into a measured floor and a convention-laden remainder.

    The B+D design (author-selected 2026-07-31). infrastructure_eoh() returns a
    single float that conceals two halves of very different epistemic status. This
    companion separates them, mirroring ecological_eoh_breakdown():

        statutory_floor  — task-normative, currency-free, AUDITED when an
                           asset_census is supplied; the measured stream.
        discretionary    — maintenance ambition ABOVE the floor. Doctrine/
                           convention-dependent → a policy choice that belongs in
                           the fulfilment/fiscal layer, quarantined here as an input.
        visible_deferred — accrued-but-unfulfilled obligation made visible by
                           monitoring (deferred_stock · monitoring_factor).
        total = statutory_floor + discretionary + visible_deferred

    This is the same "floor = measurement, above the floor = discovery/politics"
    move as the price-as-floor reconciliation (§3) and the measured multiplier —
    infrastructure as the third domain under one epistemics.

    Two input paths:
      - asset_census (PRIMARY, physical): the floor is
        infrastructure_statutory_floor(asset_census); audited=True. Currency never
        enters, so ε's infrastructure denominator can honestly be this floor
        (the infrastructure-floor handoff §5.4b) — the [0.04, 0.40] ε-indeterminacy of the
        monetized path collapses to a physical count.
      - capital_stock (FALLBACK, monetized): the floor is infrastructure_eoh(...);
        audited=False. With discretionary=0 and deferred=0 the total EQUALS
        infrastructure_eoh() with the same args — full backward compatibility.

    ε-behavior: the census floor is ε-invariant (physical). The scalar-fallback
    floor applies the legacy canonical growth when epsilon is given (unchanged).
    Degrades gracefully across ε ∈ [0, 0.99]; monitoring_factor is clamped.

    Args:
        capital_stock: monetized stock (TEH) for the fallback path. Required when
            asset_census is None.
        capital_age_ratio: mean age/design-life ∈ [0, 1] (fallback path only).
        asset_census: physical condition census (see infrastructure_statutory_floor).
            When provided, takes precedence over capital_stock for the floor.
        discretionary_eoh: policy ambition above the floor (hours/year); default 0.
        deferred_stock: accrued unfulfilled obligation (hours); default 0.
        monitoring_capability: fraction of deferred visible ∈ [0, 1]; resolved from
            epsilon when None (shared with the ecological path).
        epsilon: automation level; fallback-path canonical growth + monitoring default.
        base_maint_rate, age_factor_max: fallback-path rate model parameters.
        assessment_id: label naming the doctrine/source behind discretionary_eoh.

    Returns:
        dict: {
          "statutory_floor":  float,   (measured/auditable floor)
          "discretionary":    float,   (convention-dependent ambition)
          "visible_deferred": float,   (deferred_stock · monitoring_factor)
          "total":            float,   (= floor + discretionary + visible_deferred)
          "audited":          bool,    (True iff a physical census produced the floor)
          "monitoring_factor": float,
          "assessment_id":    str,
          "epsilon":          float | None,
        }

    Raises:
        ValueError: if neither asset_census nor capital_stock is provided.

    Reference: the infrastructure-floor handoff §5.1–5.4; reconciliation §3 (floor semantics);
    Mission Statement Guardrail I.
    """
    if asset_census is not None:
        floor = infrastructure_statutory_floor(asset_census)
        audited = True
    elif capital_stock is not None:
        floor = infrastructure_eoh(
            capital_stock, capital_age_ratio, epsilon, base_maint_rate, age_factor_max
        )
        audited = False
    else:
        raise ValueError("infrastructure_eoh_breakdown needs asset_census or capital_stock")

    mon = _resolve_monitoring_capability(monitoring_capability, epsilon)
    visible_deferred = max(0.0, deferred_stock) * mon

    return {
        "statutory_floor":  floor,
        "discretionary":    discretionary_eoh,
        "visible_deferred": visible_deferred,
        "total":            floor + discretionary_eoh + visible_deferred,
        "audited":          audited,
        "monitoring_factor": mon,
        "assessment_id":    assessment_id,
        "epsilon":          epsilon,
    }


# ---------------------------------------------------------------------------
# Ecological EOH
# ---------------------------------------------------------------------------

def ecological_eoh(
    ecosystem_health: float,
    epsilon: float | None = None,
    base_rate: float | None = None,
    threshold: float = ECOLOGICAL_THRESHOLD,
    deferred: float = 0.0,
    monitoring_capability: float | None = None,
    thermal_obligation: float = 0.0,
    area_hectares: float | None = None,
    intensity: float = ECOLOGICAL_INTENSITY_BASE,
    restoration_obligation: float = 0.0,
    health_response: str = "guf",
    standing_response: str = "guf",
) -> float:
    """
    Total ecological EOH generated by natural systems civilization depends on.

    Four-component formula:

        baseline        = base_rate / ecosystem_health                      [h/yr]
        spike           = base_rate × 5 × ((threshold − health) / threshold)²
                          (only when ecosystem_health < threshold; else 0)  [h/yr]
        visible_deferred = deferred × monitoring_capability                 [h/yr]
        thermal          = the planetary radiative-capacity obligation       [h/yr]

        total = baseline + spike + visible_deferred + thermal

    THE PRISTINE-VS-CURRENT PARTITION (2026-08-17, author sign-off)
    ---------------------------------------------------------------
    Two standards were being conflated in one obligation, and the split assigns
    each to the layer that can carry it:

        GUF E(p,ε)      FLOW  · attributable to the holder of exclusive use
                              · standard: MAINTAIN CURRENT CONDITION
                              · "do not degrade it further while you hold it"

        ecological_eoh  STOCK · attributable to NO ONE
                              · standard: THE PRISTINE GAP
                              · what is already lost, before or outside any
                                current holding

    The rule that generates it: *obligations human use creates and can reset go
    to GUF; obligations nature cannot self-restore, or that no present holder
    caused, stay in the domain.* Thermal falls out of that rather than being
    wedged into it — its own note below calls it "the one ecological service
    labor cannot restore", and it is unattributable to any parcel. So the domain
    carries exactly two terms, `thermal` and `restoration`, and both are stocks.

    WHY THE DOMAIN IS SMALL AND SHOULD BE. Under this partition the recurring
    cost of land is a GUF matter, and what remains here is a backlog. Measured:
    the servicing flow is 45.92 h/ha·yr while the restoration stock amortises to
    0.017–0.096 h/ha·yr, so PER HECTARE the stock is at most 0.21% of the flow.
    A small ecological domain is the partition working, not the partition
    failing.

    (CORRECTED 2026-08-28. This read "the stock is 0.56% of the flow" beside
    those two per-hectare figures. 0.56% is a US-SCALE ratio over DIFFERENT
    areas — 100 Mha of restorable land against 37.1 Mha of serviced land — and
    pairing it with a per-hectare pair is the mixing that
    `scenarios/ecological_floor` carries an explicit warning against. The
    warning was written; this docstring was not updated to match it.)

    WHAT IS NOT SUPPLIED. `restoration_obligation` defaults to 0.0 because the
    quantity behind it — how much land sits how far below reference condition —
    is not measured anywhere in this package. Phase 3 gives the cost PER HECTARE
    RESTORED; this needs the HECTARES NEEDING RESTORATION, and inventing that
    inventory would put a fitted number where a measurement belongs. See
    `scenarios/restoration_cost.pristine_gap_obligation`, which computes the term
    from a caller-supplied condition inventory and states what would settle it.

    The thermal term (added 2026-08-05, author sign-off) is the first obligation
    the framework books against planetary radiative capacity — the one ecological
    service labor cannot restore. It arrives as an annual FLOW, the drawdown job
    discharged over a programme horizon, and it is NOT scaled by monitoring
    capability: measured forcing is a direct observation, so unlike historical
    neglect this obligation is fully visible at every ε. Sized by
    research/thermal_drawdown and research/thermal_solvency; zero by default, so
    it is opt-in and every prior caller is unaffected.

    Ecological systems do not degrade smoothly — long periods of slow
    accumulation are punctuated by sharp threshold failures (fishery collapse,
    soil depletion, aquifer loss, climate tipping points). The spike captures
    this: below health=0.40, EOH surges nonlinearly.

    As ε rises from 0 to 1, baseline EOH stays flat (ecosystem health degrades
    slightly on canonical arc, keeping baseline roughly constant), but
    visible_deferred grows with monitoring capability — better sensing makes
    historical neglect legible.

    Worked example (above threshold, ε=0.40, no deferred):
        health=0.82, monitoring=0.70 (canonical at ε=0.40)
        baseline = 500,000 / 0.82 = 610K h/yr
        spike    = 0 (health above threshold)
        total    = 610K h/yr

    Worked example (below threshold, ε=0.40):
        health=0.30, threshold=0.40, monitoring=0.70
        baseline = 500,000 / 0.30 = 1,667K h/yr
        spike    = 500,000 × 5 × ((0.40−0.30)/0.40)² = 156K h/yr
        total    = 1,823K h/yr  (+3× compared to healthy ecosystem)

    **Physical state input**: monitoring_capability is the explicit physical
    parameter, ∈ [0.0, 1.0]. When provided, takes precedence over the
    epsilon-derived canonical value (0.50 + 0.50ε).

    Args:
        ecosystem_health: Current ecosystem state, ∈ [0.0, 1.0].
                          1.0 = pristine; 0.0 = effectively collapsed.
        epsilon: Optional. When provided and monitoring_capability is None,
                 supplies the canonical monitoring capability for that ε.
        base_rate: Baseline ecological EOH at ecosystem_health=1.0 (hours/year).
        threshold: Below this health level, the nonlinear spike activates.
        deferred: Accumulated deferred EOH from historical neglect (hours).
        monitoring_capability: Fraction of deferred EOH visible to the ledger,
                               ∈ [0.0, 1.0]. When provided, takes precedence
                               over the epsilon-derived canonical value.

    Returns:
        Total ecological EOH (hours/year) including baseline, spike, and
        monitoring-visible deferred obligations.

    Reference: Mission Statement §"Ecological EOH — the entropy of natural systems";
    §"EOH and compounding" — threshold-based, not exponential; §"Guardrail I —
    EOH rates derived from measurable physical indicators."
    """
    return ecological_eoh_breakdown(
        ecosystem_health, epsilon, base_rate, threshold, deferred,
        monitoring_capability, thermal_obligation, area_hectares, intensity,
        restoration_obligation, health_response, standing_response,
    )["total"]


# ---------------------------------------------------------------------------
# Knowledge EOH
# ---------------------------------------------------------------------------

def skill_renewal_rate(
    transmission: float = SKILL_TRANSMISSION_RATE,
    cpd: float = SKILL_CPD_RATE,
) -> dict[str, float]:
    """
    The annual knowledge-renewal rate, split into its two physical components.

    Governing decomposition (Block K-III):

        d = r_transmission + r_CPD                              [1/year]

        r_transmission = 1 / working_life   — the stock is re-created as cohorts
                         retire. Knowledge dies with people; that is the entropy.
        r_CPD          = recurring renewal by a WORKING practitioner staying
                         current in an occupation they already hold.

    WHY THE SPLIT EXISTS. `SKILL_DECAY_RATE` = 0.10 was doing both jobs, exactly
    as `PERSONAL_EOH_BASE` did three before Block I. The two are orthogonal:
    transmission is set by demography and is derivable; CPD is set by how fast a
    field moves and is NOT in O*NET, which measures the hours to REACH
    competency, never the hours to HOLD it.

    WHAT THE SPLIT REVEALS. The components sum to 0.0277, against the shipped
    0.10. Against the measured 11,001 h/worker stock (reference/onet_knowledge)
    that is 305 h/worker·yr versus 1,100 — 14.7% of the H_REF 2,080 h work-year
    versus **55.0%**. The shipped rate asserts that every worker spends more than
    half of every working year, forever, re-acquiring knowledge they already
    have. This function reports the discrepancy rather than reconciling it away.

    NOTHING DEFAULTS TO THIS YET. `knowledge_eoh` still defaults to
    `SKILL_DECAY_RATE`, so the arc is unchanged; adoption is Block K-IV.

    units: 1/year. ε-behavior: none — neither component is ε-driven. Ageing and
    field churn do not wait for automation. (Whether CPD should rise with ε — a
    faster-moving apparatus needs more re-learning — is a real question and is
    NOT asserted here; `knowledge_eoh`'s cpu term already carries the apparatus's
    growing complexity, and putting it in both places would double-count.)

    Args:
        transmission: Cohort-turnover renewal rate, ≥ 0.
        cpd: Continuing-practice renewal rate, ≥ 0.

    Returns:
        dict: {"transmission", "cpd", "total", "shipped", "ratio_to_shipped",
               "transmission_share"}.

    Raises:
        ValueError: if either component is negative.

    Worked example (defaults): transmission 0.0250 + cpd 0.0027 = 0.0277, which
    is 0.277× the shipped 0.10; transmission is 90.3% of the total, so the term
    that CAN be measured dominates the one that cannot.
    """
    if transmission < 0.0:
        raise ValueError(f"transmission must be non-negative, got {transmission}")
    if cpd < 0.0:
        raise ValueError(f"cpd must be non-negative, got {cpd}")
    total = transmission + cpd
    return {
        "transmission":       transmission,
        "cpd":                cpd,
        "total":              total,
        "shipped":            SKILL_DECAY_RATE,
        "ratio_to_shipped":   total / SKILL_DECAY_RATE if SKILL_DECAY_RATE else float("inf"),
        "transmission_share": transmission / total if total > 0.0 else 0.0,
    }


def knowledge_eoh(
    knowledge_base_size: float,
    skill_decay_rate: float = SKILL_TRANSMISSION_RATE,
    epsilon: float | None = None,
    base_rate: float = KNOWLEDGE_EOH_BASE,
    epsilon_exponent: float = KNOWLEDGE_EPS_EXPONENT,
    complexity_per_unit: float | None = None,
    population: float = KNOWLEDGE_REFERENCE_POPULATION,
) -> float:
    """
    Total knowledge EOH generated by the information entropy of civilization.

    At high automation, almost all remaining human contribution is knowledge
    maintenance, transmission, and judgment. Skills atrophy. Institutional
    memory fades. Software rots. Standards drift. This domain becomes dominant
    as ε → 1.0 — and is the hardest to verify, requiring careful consideration
    of registration standards (Mission Statement: §"Admitting knowledge EOH
    to the collective ledger will require careful consideration").

    Governing equation (units corrected 2026-08-08, Block K-I):

        K(ε) = S · (population / P_ref) · kbs(ε) · cpu(ε) · d        [hours/year]

    where S = `base_rate` is a STOCK of embodied knowledge hours, d =
    `skill_decay_rate` is the annual renewal fraction, and P_ref =
    KNOWLEDGE_REFERENCE_POPULATION is the population S is quoted at.

    STOCK, NOT FLOW — read this before calibrating. `base_rate` was previously
    documented as "baseline knowledge EOH at ε=0 (hours/year)", but it is not:
    at the ε=0 reference this returns base × 1 × 1 × 0.10 = one TENTH of
    base_rate. The constant has always operated as a stock that `skill_decay_rate`
    converts to an annual obligation. The label was wrong, not the arithmetic.
    This matters because it is what makes the domain measurable: the O*NET/BLS
    spine supplies exactly a training STOCK (hours to reach competency) and a
    renewal RATE, which is the same shape. See the knowledge-base closure note.

    POPULATION SCALING (new in K-I). Knowledge EOH was population-invariant —
    the identical absolute figure at 1M and at 300M — so the domain's share of
    total EOH silently fell as 1/population while personal, infrastructure and
    ecological all scaled. It now scales linearly. At the default population
    this is a no-op and reproduces every prior result exactly.

    Both effective_kbs and complexity_per_unit are O(1) — knowledge EOH is O(kbs),
    not O(kbs²). Automated systems are more complex (larger kbs AND harder per-unit
    maintenance), which is why knowledge EOH grows sharply with ε.

    HONEST SCALE CAVEAT: at shipped calibration this domain is ~0.005% of total
    EOH (docs/parameter_provenance.md §"Domain balance"), which is not credible
    for a function whose own reference says human labor at ε→1 is "almost
    entirely care, judgment, and knowledge maintenance". Block K-I fixes the
    STRUCTURE and deliberately moves no numbers; the re-base is Block K-IV.

    **Physical state input**: knowledge_base_size is the ACTUAL current knowledge
    base size relative to the ε=0 reference (1.0 = reference). complexity_per_unit
    is the per-unit maintenance difficulty factor (1.0 = reference, grows with
    system complexity at high automation). Pass both from simulation state or from
    trajectory.canonical_physical_state(ε).

    **Backward compatibility**: If epsilon is provided, knowledge_base_size is treated
    as the ε=0 baseline (typically 1.0) and the canonical growth factor is applied:
    effective_kbs = kbs × (1 + CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE × ε).
    complexity_per_unit is derived from the canonical trajectory if not explicitly
    provided. Old callers passing knowledge_base_size=1.0 and epsilon=ε get the
    same result as before.

    Args:
        knowledge_base_size: Actual knowledge base size relative to ε=0 reference.
                             When epsilon is provided (legacy), treated as ε=0
                             baseline and scaled by canonical growth factor.
        skill_decay_rate: Annual renewal fraction applied to the stock. NOTE this
                 currently conflates transmission (cohort turnover) with CPD
                 (staying current); Block K-III splits them. See SKILL_DECAY_RATE.
        epsilon: Optional automation level [0.0, 0.99]. When provided, fills in
                 canonical-trajectory defaults and scales knowledge_base_size as
                 the ε=0 baseline. New code should omit this.
        base_rate: STOCK of embodied knowledge hours at the ε=0 reference, quoted
                 at `KNOWLEDGE_REFERENCE_POPULATION`. NOT an annual figure — see
                 the stock/flow note above.
        epsilon_exponent: Per-unit complexity growth exponent (canonical trajectory).
        complexity_per_unit: Per-unit maintenance difficulty, ∈ [1.0, ∞). When
                             provided, takes precedence over epsilon-derived value.
        population: Population the obligation is generated for. Scales the stock
                 linearly off `KNOWLEDGE_REFERENCE_POPULATION`. Must be ≥ 0.

    Returns:
        Total knowledge EOH (hours/year).

    Raises:
        ValueError: if population is negative.

    Worked example (canonical arc, ε = 0.40, kbs = 4.6, cpu = 2.44, d = 0.10):
        1e5 × (1e6/1e6) × 4.6 × 2.44 × 0.10 = 112,240 h/yr at 1M population;
        the same call at 2M population now returns 224,480, where before K-I it
        returned 112,240 regardless of how many people were in the collective.

    Reference: Mission Statement §"Knowledge EOH — the entropy of information
    systems"; §"At ε=0.99, remaining human labor is almost entirely care,
    judgment, and knowledge maintenance."
    """
    if population < 0.0:
        raise ValueError(f"population must be non-negative, got {population}")

    if epsilon is not None:
        # Legacy: kbs is ε=0 baseline; apply canonical knowledge growth
        effective_kbs = knowledge_base_size * (1.0 + CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE * epsilon)
        cpu = (
            complexity_per_unit if complexity_per_unit is not None
            else 1.0 + (epsilon ** epsilon_exponent) * CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE
        )
    else:
        effective_kbs = knowledge_base_size
        # cpu=1.0 is the ε=0 reference floor — physical-state callers are expected
        # to pass a measured complexity_per_unit; this is the no-automation baseline.
        cpu = complexity_per_unit if complexity_per_unit is not None else 1.0

    # Stock → annual obligation, scaled to the served population. The population
    # ratio is 1.0 at the default, so this reproduces pre-K-I output exactly.
    population_scale = population / KNOWLEDGE_REFERENCE_POPULATION
    return base_rate * population_scale * effective_kbs * cpu * skill_decay_rate


def knowledge_eoh_breakdown(
    knowledge_base_size: float,
    skill_decay_rate: float = SKILL_TRANSMISSION_RATE,
    epsilon: float | None = None,
    base_rate: float = KNOWLEDGE_EOH_BASE,
    epsilon_exponent: float = KNOWLEDGE_EPS_EXPONENT,
    complexity_per_unit: float | None = None,
    apparatus_fraction: float | None = None,
    population: float = KNOWLEDGE_REFERENCE_POPULATION,
) -> dict:
    """
    Split knowledge EOH into CIVILISATIONAL and APPARATUS components.

    Governing decomposition:

        K_total          = base · kbs · cpu · decay
        K_civilisational = base · kbs · cpu(0) · decay      [cpu(0) ≡ 1.0]
        K_apparatus      = K_total − K_civilisational
        apparatus_fraction = 1 − cpu(0)/cpu = 1 − 1/cpu

    NO NEW CONSTANT IS INTRODUCED, and that is the point. The split falls out of
    the existing functional form and its existing rationale: `knowledge_base_size`
    is the corpus a civilisation must renew whatever its capital — language,
    medicine, law, craft — while `complexity_per_unit` is documented as
    automation-driven ("each increment of automation creates more complex
    knowledge infrastructure to maintain"). So the ε-invariant floor is
    civilisational and everything the complexity term adds is apparatus: the cost
    of knowing how to run the machines.

    Across the canonical arc the apparatus share runs 0% at ε=0 to 89.8% at
    ε=0.99, which is the physically expected direction.

    Why this matters beyond bookkeeping: the apparatus component belongs in the
    collective's OVERHEAD (with infrastructure) for the overbuild test, while the
    civilisational component is a standing obligation like personal or ecological
    EOH. Charging the whole domain to either side misstates the overhead ratio.

    HONEST SCALE CAVEAT: at shipped calibration knowledge EOH is ~0.005% of total
    EOH (docs/parameter_provenance.md §"Domain balance"), so this split is
    structurally right and numerically inconsequential until the domain bases are
    put on a commensurable footing. Do not quote the apparatus share as if it
    moved anything today.

    units: hours/year; `apparatus_fraction` dimensionless ∈ [0, 1].
    ε-behavior: apparatus_fraction rises monotonically with ε and is 0 at ε=0.

    Args:
        knowledge_base_size: Corpus size relative to the ε=0 reference.
        skill_decay_rate: Annual renewal fraction.
        epsilon: Optional backward-compat canonical lookup.
        base_rate: Knowledge EOH at the reference state.
        epsilon_exponent: Complexity growth exponent.
        complexity_per_unit: Measured complexity; overrides the ε-derived value.
        apparatus_fraction: OPTIONAL explicit override of the derived split, for
            a caller who rejects the cpu-is-apparatus reading. None (default)
            derives it.
        population: Population the obligation is generated for; forwarded to
            `knowledge_eoh`. The split itself is population-invariant (it is a
            ratio), so this scales both components equally.

    Returns:
        dict: {"civilisational", "apparatus", "total", "apparatus_fraction"}.

    Raises:
        ValueError: if apparatus_fraction is given and outside [0, 1].

    Worked example (canonical arc at ε = 0.40, kbs = 4.6, cpu = 2.44):
        total 112,240 h/yr → civilisational 46,000, apparatus 66,240, share 59.0%.
    """
    if apparatus_fraction is not None and not 0.0 <= apparatus_fraction <= 1.0:
        raise ValueError(
            f"apparatus_fraction must be in [0, 1], got {apparatus_fraction}"
        )
    total = knowledge_eoh(knowledge_base_size, skill_decay_rate, epsilon,
                          base_rate, epsilon_exponent, complexity_per_unit,
                          population)
    if apparatus_fraction is None:
        # cpu as actually used by knowledge_eoh, so the split cannot drift from it
        if epsilon is not None:
            cpu = (complexity_per_unit if complexity_per_unit is not None
                   else 1.0 + (epsilon ** epsilon_exponent)
                   * CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE)
        else:
            cpu = complexity_per_unit if complexity_per_unit is not None else 1.0
        apparatus_fraction = 0.0 if cpu <= 0.0 else max(0.0, 1.0 - 1.0 / cpu)
    apparatus = total * apparatus_fraction
    return {
        "civilisational":     total - apparatus,
        "apparatus":          apparatus,
        "total":              total,
        "apparatus_fraction": apparatus_fraction,
    }


# ---------------------------------------------------------------------------
# Total EOH Aggregate
# ---------------------------------------------------------------------------

def effective_capital_from_stock(capital_stock: float, epsilon: float) -> float:
    """
    ε-adjusted effective capital stock.

    **Deprecated**: Use ``trajectory.effective_capital_from_epsilon()`` instead.
    That function is the canonical reference and is imported by fiscal/stewardship
    code. This function is retained only for backward compatibility.

    Args:
        capital_stock: Baseline capital stock in TEH (at ε=0).
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Effective capital stock in TEH at this automation level.
    """
    from hours_eoh.core.trajectory import effective_capital_from_epsilon
    return effective_capital_from_epsilon(capital_stock, epsilon)


def ecological_scale(
    base_rate: float | None = None,
    area_hectares: float | None = None,
    intensity: float = ECOLOGICAL_INTENSITY_BASE,
) -> dict:
    """
    Resolve the ecological obligation's SCALE — the extensive quantity it rests on.

    Governing equation:

        scale = area_hectares · intensity          [hours/year at health = 1.0]

    THE DEFECT THIS CLOSES. Until 2026-08-16 `ecological_eoh` took no area and no
    population: it returned `base_rate / health`, and nothing scaled it. That made
    ecological the only domain with no extensive quantity behind it —

        personal_eoh(population, ...)           extensive in population
        infrastructure_eoh(capital_stock, ...)  extensive in capital
        knowledge_eoh(...)                      extensive in the corpus
        ecological_eoh(ecosystem_health, ...)   extensive in NOTHING

    — which is why its share collapses as the system grows: everything else
    scales and it did not. Stewardship demand is a property of AREA, so area is
    what it is now keyed to.

    POPULATION DOES NOT BELONG IN THE RATE, and this is deliberate. Load per
    hectare genuinely drives demand — more people on the same ground degrade it
    faster than it recovers — but the model already has the place for that:
    `ecosystem_health` falls under load and the obligation divides by it. Putting
    population in the rate as well would double-count the same mechanism.

    units: hours/year (the scale at pristine health, before the health divisor).

    Precedence, in order:
      1. `base_rate` if given — the pre-2026-08-16 absolute path, honoured so
         every existing caller is unaffected.
      2. `area_hectares × intensity` if an area is given.
      3. `US_MAINLAND_HECTARES × intensity` — the reference frame, which equals
         `ECOLOGICAL_BASE_RATE` by construction, so the default is unchanged.

    Worked example: the shipped anchor over the land it is nominally the
    obligation for is 765,495,267 ha × 6.5317e-4 = 500,000 h/yr — i.e. **2.35
    seconds per hectare per year**. That is the domain-balance defect stated in
    units that make it obvious.

    Returns:
        dict with "scale", "area_hectares", "intensity", and "path"
        ("base_rate" | "area" | "reference_frame").
    """
    if base_rate is not None:
        return {
            "scale": base_rate,
            "area_hectares": None,
            "intensity": None,
            "path": "base_rate",
        }
    if area_hectares is not None:
        if area_hectares < 0.0:
            raise ValueError(f"area_hectares must be >= 0, got {area_hectares}")
        return {
            "scale": area_hectares * intensity,
            "area_hectares": area_hectares,
            "intensity": intensity,
            "path": "area",
        }
    return {
        "scale": US_MAINLAND_HECTARES * intensity,
        "area_hectares": US_MAINLAND_HECTARES,
        "intensity": intensity,
        "path": "reference_frame",
    }


def ecological_eoh_breakdown(
    ecosystem_health: float,
    epsilon: float | None = None,
    base_rate: float | None = None,
    threshold: float = ECOLOGICAL_THRESHOLD,
    deferred: float = 0.0,
    monitoring_capability: float | None = None,
    thermal_obligation: float = 0.0,
    area_hectares: float | None = None,
    intensity: float = ECOLOGICAL_INTENSITY_BASE,
    restoration_obligation: float = 0.0,
    health_response: str = "guf",
    standing_response: str = "guf",
) -> dict:
    """
    Full component breakdown of ecological EOH: baseline + spike + visible
    deferred + thermal obligation.

    ecological_eoh() returns the total only. This companion function exposes the
    three constituent terms for transparency (Guardrail I) and monitoring dashboards.
    The values here sum to ecological_eoh() with the same arguments.

    **Physical state input**: monitoring_capability is the explicit physical
    parameter (same as ecological_eoh()). When provided, takes precedence over
    the epsilon-derived canonical value.

    Args:
        ecosystem_health: Current ecosystem state ∈ [0.0, 1.0].
        epsilon: Optional. When provided and monitoring_capability is None,
                 supplies the canonical monitoring capability for that ε.
        base_rate: Baseline ecological EOH at ecosystem_health=1.0 (hours/year).
        threshold: Below this health level, the nonlinear spike activates.
        deferred: Accumulated deferred EOH from historical neglect (hours).
        monitoring_capability: Fraction of deferred EOH visible to the ledger,
                               ∈ [0.0, 1.0]. When provided, takes precedence.
        thermal_obligation: Annual EOH owed against the planetary radiative
                            budget (h/yr). Default 0.0 — supplying it is opt-in,
                            so every existing caller is unaffected.
        restoration_obligation: THE PRISTINE-GAP STOCK (h/yr), amortised. The
                            legacy restoration backlog: what it costs to bring
                            land back UP to reference condition, as distinct
                            from holding it where it is. Default 0.0 and opt-in,
                            same treatment as thermal. See the partition note in
                            this function's docstring — the two are the whole of
                            what the ecological DOMAIN carries under the
                            2026-08-17 split, and everything else is GUF.

    Returns:
        dict: {
          "baseline":         float,   (routine stewardship at current health)
          "spike":            float,   (nonlinear threshold spike; 0 if above threshold)
          "visible_deferred": float,   (deferred obligation visible at this ε)
          "thermal":          float,   (planetary radiative-capacity obligation)
          "total":            float,   (= baseline + spike + visible_deferred + thermal)
          "monitoring_factor": float,  (fraction of deferred that is visible)
          "in_threshold_spike": bool,
          "ecosystem_health": float,
          "deferred":         float,
          "epsilon":          float | None,
        }

    Reference: Mission Statement §"Ecological EOH — threshold-based, not exponential."
    """
    scale = ecological_scale(base_rate, area_hectares, intensity)
    rate = scale["scale"]

    if health_response not in ("domain", "guf"):
        raise ValueError(
            f"health_response must be 'domain' or 'guf', got {health_response!r}"
        )

    health = max(ecosystem_health, 0.001)
    baseline = rate / health

    spike = 0.0
    if health < threshold:
        deficit = (threshold - health) / threshold
        spike = rate * ECOLOGICAL_SPIKE_INTENSITY * (deficit ** 2)

    # PHASE 4e (2026-08-17, author sign-off) — DECOMPOSE THE HEALTH RESPONSE.
    #
    #     baseline = rate / health  =  rate  +  rate·(1 − health)/health
    #                                   ↑              ↑
    #                             standing        degradation_response
    #
    # An exact algebraic split, so it moves no number by itself. What it makes
    # assignable is the partition: `standing` is what land in reference
    # condition asks whatever anyone does to it — the domain's own obligation —
    # while `degradation_response` and `spike` are the ledger's reaction to land
    # being BELOW reference, which is disturbance, which under the 2026-08-17
    # partition is a reset cost and therefore GUF's.
    #
    # The decomposition carries the partition's signature: at health = 1.0 the
    # degradation response is EXACTLY ZERO and the domain carries only
    # `standing`. Land in balance asks nothing beyond its own maintenance, and
    # that now falls out of the algebra rather than being asserted.
    standing = rate
    degradation_response = baseline - rate

    mon = _resolve_monitoring_capability(monitoring_capability, epsilon)
    visible_deferred = deferred * mon

    # `health_response` decides which side of the partition the reaction is
    # BOOKED on. Default "domain" reproduces every pre-4e number exactly; "guf"
    # relocates it, and the relocated amount is reported either way so it is
    # never merely missing. Opt-in is the same treatment `thermal_obligation`
    # received at its own sign-off.
    # PHASE 4f (2026-08-28) — THE STANDING TERM IS GUF'S TOO, AND THAT CLOSES
    # THE ECOLOGICAL LEVEL.
    #
    # `standing` is a RECURRING per-year obligation, and Phase 4d's partition
    # says "everything recurring is GUF". The question the repo has carried for
    # months — what should ECOLOGICAL_BASE_RATE be? — was posed as a
    # MEASUREMENT question, and its own `resolves_by` names
    # `scenarios/land_stewardship.census_report()`. That pointer was written
    # 2026-08-16, the day BEFORE the partition was signed off, and the partition
    # invalidates it: the census is already spent.
    #
    # CHECKED, NOT ASSUMED. `scenarios/guf_magnitude.recurring_target_by_class`
    # charges the measured stewardship intensity of every class the census can
    # price — forest 0.182, federal parks 0.161, urban 4.349 h/ha·yr — as part
    # of GUF's recurring target. Raising this anchor toward the census would
    # therefore bill the SAME measured hours twice: once to the holder through
    # GUF, once to the domain. That is the double-application failure the Ψ
    # audit found (two terms, one mechanism), reached from the other direction.
    #
    # And there is no unassigned residue for the domain to keep. Phase 4c
    # established that land held by no member is held by the FEDERATION and owes
    # what any holder owes, with `uncollected_hours` structurally 0.0 — so every
    # hectare has a holder and every holder pays maintain-current through GUF.
    #
    # THE CONCLUSION, which reverses the long-standing framing: the anchor is
    # not "low by 2-3 orders and awaiting a census". Its correct value under the
    # adopted partition is ZERO, and the 7.97e-4 h/ha·yr it currently carries is
    # a small positive residue of the pre-partition model. The domain's real
    # content is the two STOCK terms — thermal and restoration — which are
    # already separate parameters with their own measured basis.
    #
    # THE PARTITION, STATED ONCE. Both switches ADOPTED and defaulting to "guf"
    # (4e and 4f, author sign-off 2026-08-28/29), so the shipped domain is the
    # three STOCK terms and nothing else.
    #
    # Written as "what the domain KEEPS" rather than as a baseline with
    # subtractions. The earlier form computed `baseline − (standing −
    # standing_kept)` inside one branch of a two-branch `if`, which was correct
    # and unreadable: `baseline` silently contains `standing`, so the reader had
    # to hold that identity in mind to see what the expression meant. Four
    # policy combinations over two independent switches do not need four
    # branches — each switch decides whether its own term is kept.
    #
    #   standing            recurring, land at reference condition   → 4f
    #   degradation + spike recurring, the response to DISTURBANCE   → 4e
    #   visible_deferred    a STOCK: the accumulated backlog         → stays
    #   thermal             a STOCK: non-restorable                  → stays
    #   restoration         a STOCK: the pristine gap                → stays
    relocatable = degradation_response + spike
    kept_standing = 0.0 if standing_response == "guf" else standing
    kept_disturbance = 0.0 if health_response == "guf" else relocatable
    total = (kept_standing + kept_disturbance + visible_deferred
             + thermal_obligation + restoration_obligation)

    return {
        "baseline":          baseline,
        "standing":          standing,
        "degradation_response": degradation_response,
        "spike":             spike,
        "health_response":   health_response,
        "relocatable_to_guf": relocatable,
        "standing_response": standing_response,
        "standing_relocated": standing - kept_standing,
        "visible_deferred":  visible_deferred,
        "thermal":           thermal_obligation,
        "restoration":       restoration_obligation,
        "total":             total,
        "monitoring_factor": mon,
        "in_threshold_spike": ecosystem_health < threshold,
        "ecosystem_health":  ecosystem_health,
        "deferred":          deferred,
        "epsilon":           epsilon,
        "scale":             rate,
        "area_hectares":     scale["area_hectares"],
        "intensity":         scale["intensity"],
        "scale_path":        scale["path"],
    }


def total_eoh(
    epsilon: float | None = None,
    population: float = 1_000_000.0,
    age_distribution: dict[str, float] | None = None,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
    deferred_ecological: float = 0.0,
    knowledge_complexity: float = 1.0,
    skill_decay_rate: float = SKILL_TRANSMISSION_RATE,
    # Per-domain base rates — allow override for calibration sweeps
    personal_base: float = PERSONAL_EOH_BASE,
    personal_standard: str | None = None,
    infra_maint_rate: float = INFRA_MAINT_RATE,
    ecological_base: float | None = None,
    ecological_threshold: float = ECOLOGICAL_THRESHOLD,
    ecological_area_hectares: float | None = None,
    ecological_intensity: float = ECOLOGICAL_INTENSITY_BASE,
    ecological_hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
    ecological_health_response: str = "guf",
    ecological_standing_response: str = "guf",
    knowledge_base: float = KNOWLEDGE_EOH_BASE,
    knowledge_exponent: float = KNOWLEDGE_EPS_EXPONENT,
    capital_eoh_eliminated: float = 0.0,
    capital_personal_eoh_fulfilled: float = 0.0,
    infrastructure_compounding_eoh: float = 0.0,
    competency_gap_factor: float = 0.0,
    # Physical state parameters (new API — override canonical defaults when provided)
    monitoring_capability: float | None = None,
    knowledge_complexity_per_unit: float | None = None,
    thermal_obligation: float = 0.0,
    # STRANDED UNTIL 2026-08-30, and the omission mattered more after the
    # partition than before it. `thermal_obligation` — the same class of term,
    # added by the same phase — reached `total_eoh` and the pipeline; this one
    # stopped at `ecological_eoh`. After Phases 4e/4f the ecological domain
    # carries ONLY stocks, so this is one of three, and it was the one an
    # institution following the documented intake path could not supply.
    restoration_obligation: float = 0.0,
    basis: str = "gross",
) -> dict[str, float]:
    """
    Aggregate EOH across all four domains.

    Returns a breakdown by domain plus the total, making the demand signal
    transparent and auditable (Guardrail I: physical grounding). This is the
    total entropy obligation of the civilization — what physics demands,
    independent of who (human or machine) fulfills it.

    **Physical state design**: When epsilon is None, each domain function uses
    only the explicit physical parameters passed here. When epsilon is provided,
    domain functions use canonical-trajectory defaults for any physical state
    not explicitly overridden. monitoring_capability and knowledge_complexity_per_unit
    always take precedence over the epsilon-derived canonical values when provided.

    Args:
        epsilon: Optional automation level [0.0, 0.99]. When provided, fills in
                 canonical-trajectory defaults for domain functions (backward compat).
                 New simulation code passes physical state directly and omits this.
        population: Total population.
        age_distribution: Optional dict mapping age group → fraction.
        capital_stock: Actual current capital stock in TEH. When epsilon is
                       provided (legacy), treated as ε=0 baseline and scaled.
        capital_age_ratio: Mean asset age relative to design life, ∈ [0, 1].
        ecosystem_health: Ecosystem state, ∈ [0, 1].
        deferred_ecological: Accumulated deferred ecological EOH (hours).
        knowledge_complexity: Knowledge base size relative to ε=0 reference.
                              When epsilon is provided, treated as ε=0 baseline
                              and scaled by canonical growth factor.
        skill_decay_rate: Annual fraction of skills requiring renewal.
        (+ per-domain base rates for calibration)
        capital_eoh_eliminated: Aggregate system EOH eliminated by the capital
            stock (sum of annual_eoh_eliminated across all assets). Applied
            proportionally to infrastructure/ecological/knowledge only — NOT
            personal EOH. Personal entropy (biological needs) is unaffected by
            capital stock size; only the human-labor burden decreases via (1-ε).
        capital_personal_eoh_fulfilled: Aggregate personal EOH fulfilled by the
            capital stock per year (sum of annual_personal_eoh_fulfilled across
            all assets). Passed through to the return dict so fiscal.py can
            compute per-capita fulfillment and reduce the guarantee's EOH
            reimbursement accordingly. Does NOT alter total personal EOH demand
            — the biological obligation still exists, but capital handles it.
        infrastructure_compounding_eoh: Deferred-maintenance compounding spike
            (pre-computed via eoh_compounding()) added to baseline infrastructure
            EOH. Converts deferred maintenance from an informational health warning
            into actual demand in the EOH ledger. Applied before capital_eoh_eliminated
            reduction so eliminated obligations are still removed from the compounded
            total.
        competency_gap_factor: Additional fractional amplification of knowledge EOH
            from competency gaps. When certified worker counts fall below the Condition
            IV threshold in essential domains, skill decay accelerates and recovery
            training increases knowledge EOH demand. Compute via
            competency_to_knowledge_eoh_delta() in workforce.py. Default 0.0 (no gap).
        monitoring_capability: Fraction of deferred ecological EOH visible to the
            ledger, ∈ [0.0, 1.0]. When provided, takes precedence over the
            epsilon-derived canonical value.
        knowledge_complexity_per_unit: Per-unit maintenance difficulty for knowledge
            EOH, ∈ [1.0, ∞). When provided, takes precedence over the epsilon-derived
            canonical value.

    Governing equation (additive across four physical domains):

        EOH_total = EOH_personal + EOH_infrastructure + EOH_ecological + EOH_knowledge

    Key non-obvious behavior: total EOH *rises* with ε on the canonical arc.
    Personal EOH is roughly flat (biological needs are constant), but infrastructure
    grows with capital stock, ecological EOH is held roughly flat at healthy values,
    and knowledge EOH grows steeply as ε² × knowledge_base_size. The automation
    paradox: more machines → more complex civilization → more entropy to maintain.

    Worked example at ε=0.40 (canonical defaults, population=1M):
        Personal:        2,217M h/yr  (1M people × ~2,217 h/yr avg weighted EOH)
        Infrastructure:    135M h/yr  (3.6B TEH capital × 0.025/yr × 1.5 age factor)
        Ecological:        714K h/yr  (healthy ecosystem, no deferred, 70% monitoring)
        Knowledge:         112K h/yr  (knowledge_base=4.6 × 0.10 decay × 100K base × 2.44/unit)
        Total:           2,353M h/yr

    Compare at ε=0.0 (subsistence): total = 2,288M h/yr
    Compare at ε=0.90 (high automation): total = 2,432M h/yr

    Returns:
        dict with keys: personal, infrastructure, ecological, knowledge, total,
        capital_eoh_eliminated, capital_personal_eoh_fulfilled,
        infrastructure_compounding_eoh, competency_gap_factor.
        All values in hours/year.

    Reference: Mission Statement §"Entropy Obligation Hours — Accounting Framework"
    """
    p = personal_eoh(population, age_distribution, epsilon, personal_base,
                     standard=personal_standard)
    i = infrastructure_eoh(capital_stock, capital_age_ratio, epsilon,
                           infra_maint_rate, 2.0) + infrastructure_compounding_eoh
    # Ecological scale: an AREA or an absolute base, never both. `ecological_scale`
    # silently prefers base_rate when given both (it honours pre-2026-08-16 callers);
    # here there is no legacy combination to honour, so the ambiguity is refused
    # rather than resolved — a supplied area that the caller believes is in force,
    # and is not, is the silently-ignored-parameter failure this repo keeps finding.
    if ecological_base is not None and ecological_area_hectares is not None:
        raise ValueError(
            "pass ecological_base OR ecological_area_hectares, not both: "
            f"got base={ecological_base}, area={ecological_area_hectares} ha. "
            "The area would be silently ignored under ecological_scale() precedence."
        )
    # Neither given → RESOLVE THE AREA FROM THE POPULATION (2026-08-17, Phase 4b).
    #
    # THE DEFECT THIS CLOSES. The default used to be ECOLOGICAL_BASE_RATE, which
    # is the obligation for the WHOLE CONTIGUOUS US — 765,495,267 ha — while the
    # default population is 1,000,000. Nothing connected them, so the shipped
    # default had a million people stewarding the entire United States, and the
    # reported ecological SHARE was flattered by the ratio between the two.
    #
    # WHY THE FIX IS HERE AND NOT IN THE CONSTANT. ECOLOGICAL_BASE_RATE is not
    # wrong: it correctly states the US-scale obligation, and
    # ECOLOGICAL_INTENSITY_BASE is DERIVED from it as base / US_MAINLAND_HECTARES.
    # Rewriting the constant to a 1M-consistent value would break that identity —
    # an identity the repo pins deliberately — so the pins would be firing against
    # the fix rather than against a defect. What was wrong is the RESOLUTION: a
    # population was being paired with an area nobody chose.
    #
    # This also closes a disagreement the repo had already recorded. Because the
    # anchor was keyed to US area while `scenarios/ecological_floor` computed its
    # implied intensity over population × LAND_HECTARES_PER_CAPITA, the two paths
    # reported intensities 464× apart from the same constant. Resolving the
    # default the same way `ecological_floor` always has makes them agree.
    if ecological_base is None and ecological_area_hectares is None:
        ecological_area_hectares = population * ecological_hectares_per_capita
    e = ecological_eoh(ecosystem_health, epsilon, ecological_base,
                       ecological_threshold, deferred_ecological,
                       monitoring_capability, thermal_obligation,
                       ecological_area_hectares, ecological_intensity,
                       restoration_obligation=restoration_obligation,
                       health_response=ecological_health_response,
                       standing_response=ecological_standing_response)
    k = knowledge_eoh(knowledge_complexity, skill_decay_rate, epsilon,
                      knowledge_base, knowledge_exponent, knowledge_complexity_per_unit,
                      population)

    # Competency gap feedback: undercertified domains accelerate skill decay,
    # increasing knowledge EOH demand. Applied before elimination so the extra
    # demand can still be offset by capital investments.
    if competency_gap_factor > 0.0:
        k *= (1.0 + competency_gap_factor)

    # Apply capital-stock EOH elimination to non-personal domains only.
    # Proportional reduction preserves relative domain shares; personal EOH is
    # unchanged to prevent the deflationary feedback loop where capital growth
    # reduces biological obligations and dampens TEH creation.
    if capital_eoh_eliminated > 0.0:
        non_personal = i + e + k
        if non_personal > 0.0:
            reduction_factor = 1.0 - capital_eoh_eliminated / non_personal
            i = max(0.0, i * reduction_factor)
            e = max(0.0, e * reduction_factor)
            k = max(0.0, k * reduction_factor)

    if basis not in ("gross", "final"):
        raise ValueError(f"basis must be 'gross' or 'final', got {basis!r}")

    # BASIS (Block III). Infrastructure and the APPARATUS share of knowledge are
    # INTERMEDIATE — the cost of the service apparatus, not obligations a
    # civilisation owes. Counting them in the total is the same error as adding
    # intermediate consumption to GDP. `final` reports what is actually owed;
    # `gross` (default, unchanged) reports owed + the apparatus that serves it.
    k_split = knowledge_eoh_breakdown(
        knowledge_base_size=knowledge_complexity if knowledge_complexity_per_unit is None
        else knowledge_complexity,
        complexity_per_unit=knowledge_complexity_per_unit,
        epsilon=epsilon if knowledge_complexity_per_unit is None else None,
    )
    app_share = k_split["apparatus_fraction"]
    k_apparatus = k * app_share
    k_civil = k - k_apparatus
    base_eoh = p + e + k_civil
    overhead_eoh = i + k_apparatus

    return {
        "personal":               p,
        "infrastructure":         i,
        "ecological":             e,
        "knowledge":              k,
        "total":                  (base_eoh + overhead_eoh) if basis == "gross" else base_eoh,
        "total_gross":            p + i + e + k,
        "total_base":             base_eoh,
        "total_overhead":         overhead_eoh,
        "knowledge_apparatus":    k_apparatus,
        "knowledge_civilisational": k_civil,
        "capital_eoh_eliminated":         capital_eoh_eliminated,
        "capital_personal_eoh_fulfilled":  capital_personal_eoh_fulfilled,
        "infrastructure_compounding_eoh":  infrastructure_compounding_eoh,
        "competency_gap_factor":           competency_gap_factor,
    }


# ---------------------------------------------------------------------------
# Domain labor requirements
# ---------------------------------------------------------------------------

def domain_labor_requirements(
    eoh_by_domain: dict,
    epsilon: float,
    hours_per_worker: float = 2000.0,
) -> dict:
    """
    Workers required in each EOH domain given current automation level.

    Translates the domain EOH breakdown (from total_eoh()) into headcount
    requirements by dividing the human-labor share by annual hours per worker.
    This makes the demand signal concrete for workforce planning: how many
    healthcare workers, infrastructure stewards, ecological monitors, etc.
    are needed to fulfill the human portion of each domain's EOH?

    The human fraction = (1 − ε) applies uniformly — automation handles
    (ε × domain_eoh) and the remaining (1−ε) requires human workers.

    Args:
        eoh_by_domain: Dict with keys "personal", "infrastructure",
                       "ecological", "knowledge" — typically from
                       total_eoh()[domain] or eoh_to_teh_pipeline()["eoh_by_domain"].
        epsilon: Automation level [0.0, 0.99]. Applied to all domains.
        hours_per_worker: Annual productive hours per worker. Default 2000
                          (H_REF from data.py — one full working year).

    Returns:
        dict: {
          "epsilon":        float,
          "human_fraction": float,      (= 1 − ε)
          "hours_per_worker": float,
          "domains": {
            <domain>: {
              "total_eoh":      float,  (gross physical obligation)
              "human_eoh":      float,  (portion requiring human labor)
              "workers_needed": float,  (human_eoh / hours_per_worker)
            },
            ...
          },
          "total_workers_needed": float,   (sum across all domains)
        }

    Reference: Mission Statement §"The workforce must be sized to its EOH
    obligation, not the other way around — scarcity of workers in any domain
    is a structural risk, not a labor-market outcome."
    """
    human_fraction = max(0.0, 1.0 - epsilon)
    h = max(hours_per_worker, 1.0)

    domains: dict = {}
    for name, total in eoh_by_domain.items():
        human = total * human_fraction
        domains[name] = {
            "total_eoh":      total,
            "human_eoh":      human,
            "workers_needed": human / h,
        }

    total_workers = sum(d["workers_needed"] for d in domains.values())

    return {
        "epsilon":              epsilon,
        "human_fraction":       human_fraction,
        "hours_per_worker":     hours_per_worker,
        "domains":              domains,
        "total_workers_needed": total_workers,
    }


# ---------------------------------------------------------------------------
# EOH to essential workforce domains
# ---------------------------------------------------------------------------

# Default weight matrix: rows = essential workforce domains, cols = EOH domains.
# Each column sums to 1.0 — every unit of aggregate EOH is attributed to
# exactly one essential domain. Agriculture leads on ecological EOH (farming
# is the primary ecosystem steward); healthcare on personal EOH (biological
# care); construction/energy/water/manufacturing/logistics divide infrastructure;
# knowledge EOH is distributed across all seven domains.
_EOH_TO_ESSENTIAL_WEIGHTS: dict[str, dict[str, float]] = {
    #                        personal  infrastructure  ecological  knowledge
    "agriculture":    {"personal": 0.00, "infrastructure": 0.05, "ecological": 0.50, "knowledge": 0.10},
    "construction":   {"personal": 0.00, "infrastructure": 0.25, "ecological": 0.00, "knowledge": 0.10},
    "energy":         {"personal": 0.00, "infrastructure": 0.20, "ecological": 0.10, "knowledge": 0.10},
    "water":          {"personal": 0.00, "infrastructure": 0.15, "ecological": 0.30, "knowledge": 0.10},
    "healthcare":     {"personal": 0.80, "infrastructure": 0.05, "ecological": 0.00, "knowledge": 0.30},
    "manufacturing":  {"personal": 0.00, "infrastructure": 0.20, "ecological": 0.05, "knowledge": 0.15},
    "logistics":      {"personal": 0.20, "infrastructure": 0.10, "ecological": 0.05, "knowledge": 0.15},
}
assert set(_EOH_TO_ESSENTIAL_WEIGHTS) == set(ESSENTIAL_DOMAINS), (
    "Weight matrix keys must match ESSENTIAL_DOMAINS — update _EOH_TO_ESSENTIAL_WEIGHTS "
    f"to cover: {set(ESSENTIAL_DOMAINS) - set(_EOH_TO_ESSENTIAL_WEIGHTS)}"
)


def eoh_to_essential_domains(
    eoh_by_domain: dict,
    weights: dict[str, dict[str, float]] | None = None,
) -> dict:
    """
    Distribute aggregate EOH across the seven essential workforce domains.

    The four EOH domains (personal, infrastructure, ecological, knowledge) are
    physical-obligation categories. The seven essential workforce domains
    (agriculture, construction, energy, water, healthcare, manufacturing,
    logistics) are certification categories for Condition IV. This function
    bridges them so that domain_eoh_coverage() can be called from aggregate
    simulation data.

    Each EOH domain is distributed proportionally across the seven essential
    domains using a weight matrix. The default weights are calibrated so each
    EOH domain column sums to 1.0 (every unit is fully attributed). Callers
    can override with a custom weight matrix for sector-specific models.

    Args:
        eoh_by_domain: Dict with any subset of "personal", "infrastructure",
                       "ecological", "knowledge" — from total_eoh() or
                       eoh_to_teh_pipeline()["eoh_by_domain"].
        weights: Optional weight matrix overriding _EOH_TO_ESSENTIAL_WEIGHTS.
                 Format: {essential_domain: {eoh_domain: fraction}}.
                 Default None → use _EOH_TO_ESSENTIAL_WEIGHTS.

    Returns:
        dict: {essential_domain: eoh_hours} for the seven essential domains.
              Values are in the same units as the input eoh_by_domain values.

    Reference: Mission Statement §"Condition IV — Distributed Competency" —
    certified capacity must cover EOH demand domain by domain, not just in aggregate.
    """
    w = weights if weights is not None else _EOH_TO_ESSENTIAL_WEIGHTS
    return {
        ess_domain: sum(
            eoh_by_domain.get(eoh_dom, 0.0) * frac
            for eoh_dom, frac in eoh_weights.items()
        )
        for ess_domain, eoh_weights in w.items()
    }


# ---------------------------------------------------------------------------
# Epsilon-delta sensitivity
# ---------------------------------------------------------------------------

def epsilon_delta_sensitivity(
    base_epsilon: float,
    delta_epsilon: float,
    population: float = 1_000_000.0,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
    knowledge_complexity: float = 1.0,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
) -> dict:
    """
    How do key EOH/TEH metrics change for a given Δε automation advance?

    Answers the question: "if automation advances by Δε, what moves and by
    how much?" Returns base values, new values, absolute deltas, and
    percentage changes for the metrics most sensitive to automation progression.
    Useful for stress-test interpretation and tactical epsilon-progression
    planning.

    Metrics tracked:
    - total_eoh: gross physical entropy obligation
    - human_eoh: human-labor share (shrinks with ε)
    - teh_created: TEH generated this period
    - registration_share: composite registration fraction (rises with ε)
    - knowledge_eoh: knowledge domain (grows sharply at high ε)
    - workers_needed: total headcount implied by domain labor requirements

    Args:
        base_epsilon: Starting automation level [0.0, 0.99].
        delta_epsilon: Automation advancement. Can be negative for retreat.
                       Clamped so new_epsilon ∈ [0.0, 0.99].
        population: Population size (held fixed — this is a sensitivity, not simulation).
        capital_stock: Capital stock TEH.
        capital_age_ratio: Asset age.
        ecosystem_health: Ecosystem state.
        knowledge_complexity: Knowledge base size.
        mean_multiplier: TEH creation multiplier.

    Returns:
        dict: {
          "base_epsilon":  float,
          "new_epsilon":   float,
          "delta_epsilon": float,   (actual applied delta; may differ if clamped)
          "metrics": {
            <name>: {
              "base":     float,
              "new":      float,
              "delta":    float,    (new − base)
              "pct_change": float,  (delta / base × 100; None if base == 0)
            },
            ...
          },
        }

    Reference: Mission Statement §"Stress tests — identify failure boundaries";
    §"The system must remain coherent across the full automation arc."
    """
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

    new_eps = max(0.0, min(0.99, base_epsilon + delta_epsilon))
    actual_delta = new_eps - base_epsilon

    def _snapshot(eps: float) -> dict:
        pipe = eoh_to_teh_pipeline(
            epsilon=eps,
            population=population,
            capital_stock=capital_stock,
            capital_age_ratio=capital_age_ratio,
            ecosystem_health=ecosystem_health,
            knowledge_complexity=knowledge_complexity,
            mean_multiplier=mean_multiplier,
        )
        req = domain_labor_requirements(pipe["eoh_by_domain"], eps)
        return {
            "total_eoh":        pipe["total_eoh"],
            "human_eoh":        pipe["human_eoh"],
            "teh_created":      pipe["teh_created"],
            "registration_share": pipe["registration_share"],
            "knowledge_eoh":    pipe["eoh_by_domain"].get("knowledge", 0.0),
            "workers_needed":   req["total_workers_needed"],
        }

    base = _snapshot(base_epsilon)
    new  = _snapshot(new_eps)

    def _pct(b: float, delta: float) -> float | None:
        return (delta / b * 100.0) if b != 0.0 else None

    metrics: dict = {}
    for name in base:
        b = base[name]
        n = new[name]
        d = n - b
        metrics[name] = {"base": b, "new": n, "delta": d, "pct_change": _pct(b, d)}

    return {
        "base_epsilon":  base_epsilon,
        "new_epsilon":   new_eps,
        "delta_epsilon": actual_delta,
        "metrics":       metrics,
    }
