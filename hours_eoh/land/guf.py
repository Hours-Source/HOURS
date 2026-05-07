"""
Ground Use Fee (GUF) calculation framework.

Implements NLSA Template

Master equation (NLSA Eq. 1):
  GUF(p) = Ψ(ε) × [A(p)×L(p)×U(p,ε)×D(p)×Z(p) + E(p,ε) + I(p,ε)] × Ω(p)

where:
  Ψ(ε)   = Epsilon Scaling Function — global arc multiplier
  A(p)   = parcel area (Standard Land Units; 1 SLU = 100 m²)
  L(p)   = Location Value Index (dimensionless, 0–1)
  U(p,ε) = Use Category Coefficient (TEH/SLU/yr, ε-scaled)
  D(p)   = Demand Pressure Modifier (dimensionless, 1.0–1.80)
  Z(p)   = Zone Adjustment Factor (dimensionless, 0.80–1.25)
  E(p,ε) = Ecosystem Displacement Surcharge (TEH/yr)
  I(p,ε) = Infrastructure Proximity Premium (TEH/yr)
  Ω(p)   = Occupancy Fraction (default 1.0)

ε arc shape: low at ε=0 (subsistence, minimal institutional capacity),
peak near ε=0.40 (intensive urbanization, high demand, peak displacement),
low at ε=0.99 (labor costs collapsed, stewardship-floor only).

GUF revenue is circulatory TEH flowing to the Trust. At moderate-to-high ε
it may become the Trust's dominant revenue source, replacing the contracting
labor levy base. See guf_trust_inflow() for Trust wiring.

Mission Statement: §"Land is held by the collective … the fee reflects real
costs rather than speculative value." §"Revenue streams pegged to the capital
stock's entropy obligations are foundational" — GUF generalizes this to land.
"""

from __future__ import annotations
import math

from hours_eoh.data import (
    GUF_PSI_A, GUF_PSI_B, GUF_PSI_FLOOR, GUF_PSI_NORM,
    GUF_ALPHA_ZETA, GUF_ALPHA_FLOOR,
    GUF_LVI_W_CENTRALITY, GUF_LVI_W_TRANSIT,
    GUF_LVI_W_SERVICES, GUF_LVI_W_NATURAL_AMENITY,
    GUF_USE_RESIDENTIAL_PRIMARY, GUF_USE_RESIDENTIAL_SECONDARY,
    GUF_USE_AGRICULTURAL_ACTIVE, GUF_USE_AGRICULTURAL_FALLOW,
    GUF_USE_COMMERCIAL_RETAIL, GUF_USE_COMMERCIAL_OFFICE,
    GUF_USE_INDUSTRIAL_LIGHT, GUF_USE_INDUSTRIAL_HEAVY,
    GUF_USE_INSTITUTIONAL, GUF_USE_CONSERVATION_CREDIT,
    GUF_DEMAND_ETA_RESIDENTIAL, GUF_DEMAND_ETA_COMMERCIAL, GUF_DEMAND_D_MAX,
    GUF_ZONE_MIN, GUF_ZONE_MAX,
    GUF_ECO_KAPPA_FLOOR_FRACTION,
    GUF_INFRA_MU_TRANSIT, GUF_INFRA_MU_UTILITIES, GUF_INFRA_MU_PUBLIC_SPACE,
    GUF_CHI_EXTERNAL,
    GUF_REVIEW_CYCLE_CAP,
    GUF_SUBSIDY_LOWER_THRESHOLD, GUF_SUBSIDY_FLOOR_RATE,
    GUF_SOIL_CREDIT_RATE,
)


# ---------------------------------------------------------------------------
# Use category registry
# Calibrated reference rates at ε=0.40 (NLSA Eq. 9 table, midpoints of ranges).
# ---------------------------------------------------------------------------
USE_CATEGORIES: dict[str, float] = {
    "residential_primary":    GUF_USE_RESIDENTIAL_PRIMARY,
    "residential_secondary":  GUF_USE_RESIDENTIAL_SECONDARY,
    "agricultural_active":    GUF_USE_AGRICULTURAL_ACTIVE,
    "agricultural_fallow":    GUF_USE_AGRICULTURAL_FALLOW,
    "commercial_retail":      GUF_USE_COMMERCIAL_RETAIL,
    "commercial_office":      GUF_USE_COMMERCIAL_OFFICE,
    "industrial_light":       GUF_USE_INDUSTRIAL_LIGHT,
    "industrial_heavy":       GUF_USE_INDUSTRIAL_HEAVY,
    "institutional":          GUF_USE_INSTITUTIONAL,
    "conservation":           GUF_USE_CONSERVATION_CREDIT,
}

# Default distance-decay rates by infrastructure type (μ_k, km⁻¹)
_INFRA_MU_BY_TYPE: dict[str, float] = {
    "transit":      GUF_INFRA_MU_TRANSIT,
    "utilities":    GUF_INFRA_MU_UTILITIES,
    "public_space": GUF_INFRA_MU_PUBLIC_SPACE,
}

# Precompute α(0.40) for normalizing labor_content_scaling (NLSA Eq. 20)
_ALPHA_AT_CALIBRATION: float = (1.0 - 0.40) ** GUF_ALPHA_ZETA + GUF_ALPHA_FLOOR


# ===========================================================================
# Section 4 — Epsilon Parameterization
# ===========================================================================

def epsilon_scaling(epsilon: float) -> float:
    """
    Global arc multiplier Ψ(ε) shaping the GUF across the automation arc.
    (NLSA Eq. 18)

    Bell-shaped function: near-floor at ε=0 and ε=0.99, peak near ε=0.40.
    At subsistence (ε=0), institutional capacity is minimal and the formal fee
    approaches a floor. At post-scarcity (ε=0.99), labor costs collapse and
    the fee contracts to a stewardship-only floor. The fee peaks mid-arc when
    urbanization, institutional complexity, and demand pressure are highest.

    Boundary guarantees:
      Ψ(0)    ≈ GUF_PSI_FLOOR  (= 0.02)
      Ψ(0.40) ≈ 1.04           (near-unity; calibration reference point)
      Ψ(0.99) ≈ 0.036          (< 0.05 × Ψ(0.40); post-scarcity floor satisfied)

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Ψ(ε) ≥ GUF_PSI_FLOOR, dimensionless.
    """
    return GUF_PSI_NORM * (epsilon ** GUF_PSI_A) * ((1.0 - epsilon) ** GUF_PSI_B) + GUF_PSI_FLOOR


def labor_content_scaling(epsilon: float) -> float:
    """
    Normalized labor-content scaling α_normalized(ε) for Use Category Coefficients.
    (NLSA Eq. 19-20)

    Equals 1.0 at ε=0.40 (the calibration reference point) by construction.
    Reflects the declining human labor content of land-use administration and
    compliance as automation rises.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        α_normalized(ε) > 0, dimensionless. Exactly 1.0 at ε=0.40.
    """
    alpha = (1.0 - epsilon) ** GUF_ALPHA_ZETA + GUF_ALPHA_FLOOR
    return alpha / _ALPHA_AT_CALIBRATION


# ===========================================================================
# Section 2 — Component Definitions
# ===========================================================================

def location_value_index(
    centrality: float,
    transit: float,
    services: float,
    natural_amenity: float,
    weights: dict[str, float] | None = None,
) -> float:
    """
    Location Value Index L(p) — composite of four normalized sub-indices.
    (NLSA Eq. 3)

    Sub-indices must be pre-normalized to [0, 1] by the caller; spatial analysis
    (gravity models, isochrones, service counts, natural feature proximity) happens
    upstream. This function takes the normalized scores and produces the composite.

    Weights default to national template values but may be overridden for regional
    boards (permitted range ±0.10 per sub-index, must sum to 1.0).

    Args:
        centrality: Normalized Centrality Index Ĉ(p) ∈ [0, 1].
        transit: Normalized Transit Accessibility Index T̂(p) ∈ [0, 1].
        services: Normalized Services Density Index Ŝ(p) ∈ [0, 1].
        natural_amenity: Normalized Natural Amenity Index N̂(p) ∈ [0, 1].
        weights: Optional dict with keys "centrality", "transit", "services",
                 "natural_amenity". Must sum to 1.0. None → template defaults.

    Returns:
        L(p) ∈ [0, 1], dimensionless.
    """
    if weights is None:
        w_c = GUF_LVI_W_CENTRALITY
        w_t = GUF_LVI_W_TRANSIT
        w_s = GUF_LVI_W_SERVICES
        w_n = GUF_LVI_W_NATURAL_AMENITY
    else:
        w_c = weights["centrality"]
        w_t = weights["transit"]
        w_s = weights["services"]
        w_n = weights["natural_amenity"]

    return w_c * centrality + w_t * transit + w_s * services + w_n * natural_amenity


def use_category_coefficient(
    use_category: str,
    epsilon: float,
    custom_u_ref: float | None = None,
) -> float:
    """
    Use Category Coefficient U(p,ε) — base temporal rate per SLU per year.
    (NLSA Eq. 9)

    Reference rates calibrated at ε=0.40; scaled by labor_content_scaling(ε).
    Conservation overlay carries a negative coefficient — a credit that reduces
    the base fee toward the GUF floor (NLSA §2.3, §3).

    For mixed-use parcels, compute the floor-area-weighted blend (NLSA Eq. 10)
    and pass as custom_u_ref.

    Args:
        use_category: Key from USE_CATEGORIES (e.g., "residential_primary").
        epsilon: Automation level [0.0, 0.99].
        custom_u_ref: Override for U_ref (TEH/SLU/yr at ε=0.40). Use for
                      mixed-use blends or collective-specific policy rates.

    Returns:
        U(p,ε) in TEH/SLU/year. Negative for conservation overlay.

    Raises:
        ValueError: If use_category is not in USE_CATEGORIES and custom_u_ref is None.
    """
    if custom_u_ref is not None:
        u_ref = custom_u_ref
    else:
        if use_category not in USE_CATEGORIES:
            raise ValueError(
                f"Unknown use category '{use_category}'. "
                f"Valid options: {list(USE_CATEGORIES)}. "
                "Pass custom_u_ref for non-standard categories."
            )
        u_ref = USE_CATEGORIES[use_category]

    return u_ref * labor_content_scaling(epsilon)


def demand_pressure_modifier(
    demand_supply_ratio: float,
    residential: bool = True,
    eta: float | None = None,
    d_max: float = GUF_DEMAND_D_MAX,
) -> float:
    """
    Demand Pressure Modifier D(p) — bounded logarithmic demand adjustment.
    (NLSA Eq. 11-13)

    Logarithmic form gives diminishing sensitivity to demand spikes, preventing
    runaway escalation. Capped at D_max = 1.80 by constitutional ceiling.
    When supply meets or exceeds demand (ratio ≤ 0), defaults to 1.0.

    Args:
        demand_supply_ratio: Δ(p) = (applicants - available) / available.
                             ≤ 0 → D = 1.0 (no pressure adjustment).
        residential: True → η = 0.15 (residential); False → η = 0.25 (commercial).
        eta: Explicit sensitivity coefficient; overrides the residential flag.
        d_max: Constitutional ceiling. Default: GUF_DEMAND_D_MAX = 1.80.

    Returns:
        D(p) ∈ [1.0, d_max], dimensionless.
    """
    if eta is None:
        eta = GUF_DEMAND_ETA_RESIDENTIAL if residential else GUF_DEMAND_ETA_COMMERCIAL

    if demand_supply_ratio <= 0.0:
        return 1.0

    raw = 1.0 + eta * math.log(1.0 + demand_supply_ratio)
    return min(raw, d_max)


def ecosystem_service_kappa(
    kappa_ref: float,
    beta: float,
    epsilon: float,
    floor_fraction: float = GUF_ECO_KAPPA_FLOOR_FRACTION,
) -> float:
    """
    ε-parameterized ecosystem service replacement cost κ_s(ε).
    (NLSA Eq. 15)

    Derives κ_max from the reference value at ε=0.40, then produces the full
    ε-parameterized form. At ε=0 (subsistence), replacement is maximally
    labor-intensive (κ ≈ κ_max). At ε=0.99, replacement is largely automated
    (κ ≈ κ_floor). Returns exactly kappa_ref at ε=0.40 by construction.

    Derivation of κ_max from reference:
      κ_ref = κ_max × 0.60^β + κ_floor
      κ_max = (κ_ref − κ_floor) / 0.60^β

    Args:
        kappa_ref: Reference replacement cost at ε=0.40, in TEH per physical unit/yr.
        beta: Automation sensitivity exponent β_s ∈ [0.6, 1.2].
        epsilon: Automation level [0.0, 0.99].
        floor_fraction: Irreducible human-judgment floor as fraction of kappa_ref.
                        Default 0.10 (10% of reference; relational/judgment labor).

    Returns:
        κ_s(ε) in same units as kappa_ref. Monotonically decreasing in ε.
        Equals kappa_ref exactly at ε=0.40.
    """
    kappa_floor = kappa_ref * floor_fraction
    kappa_max   = (kappa_ref - kappa_floor) / (0.60 ** beta)
    return kappa_max * ((1.0 - epsilon) ** beta) + kappa_floor


def ecosystem_displacement_surcharge(
    services: list[dict],
    epsilon: float,
) -> dict:
    """
    Ecosystem Displacement Surcharge E(p,ε) — annual cost of lost natural services.
    (NLSA Eq. 14)

    Converts the physical volume of each lost ecosystem service into TEH, using
    the labor-time that would be required to replace those services through
    engineered means. Conservation practices that preserve natural function
    reduce the surcharge proportionally through the retained service fraction.

    Service dict fields:
      "volume":    float — annual service volume in physical units
      "kappa_ref": float — TEH per physical unit per year at ε=0.40
      "beta":      float — automation sensitivity β_s ∈ [0.6, 1.2]
      "retained":  float — fraction of service retained in developed state ρ_s(p) ∈ [0, 1]
      "label":     str   — optional, for reporting

    Args:
        services: List of service dicts (see above).
        epsilon: Automation level [0.0, 0.99].

    Returns:
        dict: {
          "surcharge_total":  float,       (TEH/year)
          "by_service":       list[dict],  (per-service breakdown)
          "epsilon":          float,
        }
    """
    by_service = []
    total      = 0.0

    for svc in services:
        volume       = svc["volume"]
        kappa        = ecosystem_service_kappa(svc["kappa_ref"], svc["beta"], epsilon)
        retained     = max(0.0, min(1.0, svc.get("retained", 0.0)))
        contribution = volume * kappa * (1.0 - retained)

        by_service.append({
            "label":            svc.get("label", "unknown"),
            "volume":           volume,
            "kappa_epsilon":    kappa,
            "retained":         retained,
            "contribution_teh": contribution,
        })
        total += contribution

    return {
        "surcharge_total": total,
        "by_service":      by_service,
        "epsilon":         epsilon,
    }


def infrastructure_proximity_premium(
    assets: list[dict],
    epsilon: float,
) -> dict:
    """
    Infrastructure Proximity Premium I(p,ε) — annualized share of infra cost.
    (NLSA Eq. 16)

    Distributes the annualized construction cost of each infrastructure asset
    across beneficiary parcels, weighted by proximity. The cost is recorded at
    the automation level prevailing at construction (ε_k, baked into cost_teh)
    — a transit station built at ε=0.20 cost more TEH than one built at ε=0.60
    and retains that higher cost for its full design life. As legacy assets reach
    end-of-life and are replaced at higher ε, aggregate I(p) contracts.

    Cross-collective assets are downweighted by chi (GUF_CHI_EXTERNAL = 0.30
    default): the benefiting collective did not bear the maintenance obligation.

    Asset dict fields:
      "cost_teh":          float — TEH invested at construction (H_k at ε_k)
      "design_life":       float — asset life in years (Y_k)
      "beneficiary_count": int   — parcels within influence radius (B_k)
      "distance_km":       float — distance from parcel to asset in km
      "asset_type":        str   — "transit", "utilities", "public_space", or "other"
      "mu":                float — distance-decay km⁻¹ (overrides asset_type default)
      "chi":               float — collective ownership factor (default 1.0 = same collective)

    Args:
        assets: List of infrastructure asset dicts (see above).
        epsilon: Current automation level (for reporting; cost is fixed at ε_k).

    Returns:
        dict: {
          "premium_total":  float,       (TEH/year)
          "by_asset":       list[dict],  (per-asset breakdown)
          "epsilon":        float,
        }
    """
    by_asset = []
    total    = 0.0

    for asset in assets:
        cost_teh     = asset["cost_teh"]
        design_life  = max(1.0, asset["design_life"])
        bene_count   = max(1, asset.get("beneficiary_count", 1))
        dist_km      = max(0.0, asset["distance_km"])
        asset_type   = asset.get("asset_type", "other")
        mu           = asset.get("mu", _INFRA_MU_BY_TYPE.get(asset_type, GUF_INFRA_MU_UTILITIES))
        chi          = asset.get("chi", 1.0)

        annualized_share = cost_teh / (design_life * bene_count)
        proximity_factor = math.exp(-mu * dist_km)
        contribution     = annualized_share * proximity_factor * chi

        by_asset.append({
            "asset_type":        asset_type,
            "cost_teh":          cost_teh,
            "design_life":       design_life,
            "beneficiary_count": bene_count,
            "distance_km":       dist_km,
            "mu":                mu,
            "chi":               chi,
            "annualized_share":  annualized_share,
            "proximity_factor":  proximity_factor,
            "contribution_teh":  contribution,
        })
        total += contribution

    return {
        "premium_total": total,
        "by_asset":      by_asset,
        "epsilon":       epsilon,
    }


def base_fee(
    area_slu: float,
    location_value: float,
    use_coeff: float,
    demand_modifier: float,
    zone_adj: float = 1.0,
) -> float:
    """
    Base fee: A(p) × L(p) × U(p,ε) × D(p) × Z(p). (NLSA Eq. 1, base product)

    Dimensional product: SLU × 1 × (TEH/SLU/yr) × 1 × 1 = TEH/yr.
    Zone adjustment clamped to the permitted range [0.80, 1.25].

    Args:
        area_slu: Parcel ground footprint in SLU (1 SLU = 100 m²).
                  Vertical development does not increase area (NLSA §2.1).
        location_value: L(p) ∈ [0, 1] from location_value_index().
        use_coeff: U(p,ε) from use_category_coefficient(). May be negative
                   for conservation overlay.
        demand_modifier: D(p) ∈ [1.0, 1.80] from demand_pressure_modifier().
        zone_adj: Z(p) zone adjustment. Clamped to [GUF_ZONE_MIN, GUF_ZONE_MAX].

    Returns:
        Base fee in TEH/year. Negative when conservation credit dominates.
    """
    zone_adj = max(GUF_ZONE_MIN, min(GUF_ZONE_MAX, zone_adj))
    return area_slu * location_value * use_coeff * demand_modifier * zone_adj


def ground_use_fee(
    area_slu: float,
    location_value: float,
    use_category: str,
    epsilon: float,
    ecosystem_services: list[dict] | None = None,
    infrastructure_assets: list[dict] | None = None,
    demand_supply_ratio: float = 0.0,
    zone_adj: float = 1.0,
    occupancy_fraction: float = 1.0,
    guf_floor: float = 0.0,
    custom_u_ref: float | None = None,
    residential: bool = True,
) -> dict:
    """
    Master Ground Use Fee calculation for a single parcel. (NLSA Eq. 1-2)

    GUF(p) = max(floor, Ψ(ε) × [base_fee + E(p,ε) + I(p,ε)] × Ω(p))

    All amounts are TEH/year. Conservation credits can drive the base fee
    toward zero, but the total GUF is clamped at guf_floor (default 0.0).
    Any reward for exceptional stewardship beyond zero-fee status is a separate
    Trust disbursement backed by verified stewardship EOH (NLSA §3, §7.2).

    Args:
        area_slu: Parcel ground footprint in SLU (1 SLU = 100 m²).
        location_value: L(p) ∈ [0, 1] from location_value_index() or direct input.
        use_category: Key from USE_CATEGORIES (e.g., "residential_primary").
        epsilon: Current automation level [0.0, 0.99].
        ecosystem_services: List of service dicts for E(p,ε). None → E = 0.
        infrastructure_assets: List of asset dicts for I(p,ε). None → I = 0.
        demand_supply_ratio: Δ(p) for demand modifier. ≤ 0 → D = 1.0.
        zone_adj: Z(p) ∈ [0.80, 1.25].
        occupancy_fraction: Ω(p) ∈ (0, 1]. Default 1.0.
        guf_floor: Non-negative floor in TEH/year. Default 0.0.
        custom_u_ref: Override U_ref for mixed-use blends or policy rates.
        residential: True → residential demand sensitivity for D(p).

    Returns:
        dict: {
          "guf_formula":     float,       (TEH/year before floor)
          "guf_applied":     float,       (= max(guf_formula, guf_floor))
          "base_fee":        float,       (A×L×U×D×Z, TEH/year)
          "eco_surcharge":   float,       (E(p,ε), TEH/year)
          "infra_premium":   float,       (I(p,ε), TEH/year)
          "psi":             float,       (Ψ(ε))
          "occupancy":       float,       (Ω(p))
          "demand_modifier": float,       (D(p))
          "eco_breakdown":   dict | None,
          "infra_breakdown": dict | None,
          "floor_applied":   bool,
          "epsilon":         float,
        }
    """
    psi        = epsilon_scaling(epsilon)
    u_coeff    = use_category_coefficient(use_category, epsilon, custom_u_ref)
    d_modifier = demand_pressure_modifier(demand_supply_ratio, residential)
    bf         = base_fee(area_slu, location_value, u_coeff, d_modifier, zone_adj)

    eco_result = None
    eco_amount = 0.0
    if ecosystem_services:
        eco_result = ecosystem_displacement_surcharge(ecosystem_services, epsilon)
        eco_amount = eco_result["surcharge_total"]

    infra_result = None
    infra_amount = 0.0
    if infrastructure_assets:
        infra_result = infrastructure_proximity_premium(infrastructure_assets, epsilon)
        infra_amount = infra_result["premium_total"]

    occupancy_fraction = max(0.0, min(1.0, occupancy_fraction))
    guf_formula        = psi * (bf + eco_amount + infra_amount) * occupancy_fraction
    guf_applied        = max(guf_floor, guf_formula)

    return {
        "guf_formula":     guf_formula,
        "guf_applied":     guf_applied,
        "base_fee":        bf,
        "eco_surcharge":   eco_amount,
        "infra_premium":   infra_amount,
        "psi":             psi,
        "occupancy":       occupancy_fraction,
        "demand_modifier": d_modifier,
        "eco_breakdown":   eco_result,
        "infra_breakdown": infra_result,
        "floor_applied":   guf_applied > guf_formula + 1e-9,
        "epsilon":         epsilon,
    }


# ===========================================================================
# Section 5 — Rate Change Constraints
# ===========================================================================

def review_cycle_cap(
    guf_formula: float,
    guf_previous: float,
    phi: float = GUF_REVIEW_CYCLE_CAP,
) -> dict:
    """
    Apply the 5-year review cycle rate cap. (NLSA Eq. 21-22)

    Limits GUF increases to φ = 10% per review cycle (default). If the
    formula-derived fee exceeds the cap, the excess is deferred and converges
    in subsequent cycles. Protects established stewards from displacement
    through sudden fee increases (e.g., when a new transit line raises nearby
    location values).

    Args:
        guf_formula: Formula-derived GUF this review cycle (TEH/year).
        guf_previous: GUF applied in the previous review cycle (TEH/year).
        phi: Maximum per-cycle increase rate. Default: GUF_REVIEW_CYCLE_CAP = 0.10.

    Returns:
        dict: {
          "guf_formula":  float,
          "guf_previous": float,
          "cap_ceiling":  float,   (guf_previous × (1 + phi))
          "guf_applied":  float,   (min(formula, ceiling))
          "cap_binds":    bool,
          "deferred":     float,   (formula − applied; 0 if cap doesn't bind)
          "phi":          float,
        }
    """
    cap_ceiling = guf_previous * (1.0 + phi)
    cap_binds   = guf_formula > cap_ceiling + 1e-9
    guf_applied = cap_ceiling if cap_binds else guf_formula
    deferred    = max(0.0, guf_formula - guf_applied)

    return {
        "guf_formula":  guf_formula,
        "guf_previous": guf_previous,
        "cap_ceiling":  cap_ceiling,
        "guf_applied":  guf_applied,
        "cap_binds":    cap_binds,
        "deferred":     deferred,
        "phi":          phi,
    }


def income_linked_subsidy(
    guf_applied: float,
    steward_income: float,
    median_income: float,
) -> dict:
    """
    Income-linked subsidy for primary residential leaseholders. (NLSA Eq. 23-24)

    Reduces the effective GUF for leaseholders below median income. The subsidy
    cost is absorbed by the Trust's land fund (a sub-account of the Trust balance)
    and recorded as a Trust expenditure under the sufficiency obligation — visible
    in the solvency model. Sufficiency Guarantee recipients (zero income) pay
    nothing; the full GUF is absorbed as a Trust sufficiency expenditure (NLSA §9.1).

    Tiers:
      income < 0.40 × median → σ = 0.25 (pays 25% of GUF)
      0.40 × median ≤ income < median → σ linear from 0.25 to 1.0
      income ≥ median → σ = 1.0 (full GUF, no subsidy)

    Args:
        guf_applied: Applied GUF after review cycle cap (TEH/year).
        steward_income: Leaseholder annual post-levy TEH income.
        median_income: Collective median post-levy income (TEH/year).

    Returns:
        dict: {
          "guf_applied":    float,
          "guf_effective":  float,   (what steward actually pays)
          "sigma":          float,   (adjustment factor ∈ [0.25, 1.0])
          "subsidy_amount": float,   (Trust absorbs this amount)
          "steward_income": float,
          "median_income":  float,
          "subsidized":     bool,
        }
    """
    if median_income <= 0.0:
        sigma = 1.0
    else:
        lower = GUF_SUBSIDY_LOWER_THRESHOLD * median_income
        if steward_income < lower:
            sigma = GUF_SUBSIDY_FLOOR_RATE
        elif steward_income < median_income:
            sigma = GUF_SUBSIDY_FLOOR_RATE + (1.0 - GUF_SUBSIDY_FLOOR_RATE) * (
                (steward_income - lower) / (median_income - lower)
            )
        else:
            sigma = 1.0

    guf_effective  = guf_applied * sigma
    subsidy_amount = guf_applied - guf_effective

    return {
        "guf_applied":    guf_applied,
        "guf_effective":  guf_effective,
        "sigma":          sigma,
        "subsidy_amount": subsidy_amount,
        "steward_income": steward_income,
        "median_income":  median_income,
        "subsidized":     sigma < 1.0 - 1e-9,
    }


# ===========================================================================
# Section 9 — Special Provisions
# ===========================================================================

def soil_health_credit(
    area_slu: float,
    delta_shi: float,
    credit_rate: float = GUF_SOIL_CREDIT_RATE,
) -> float:
    """
    Agricultural soil-health credit ΔGUF_soil. (NLSA Eq. 26)

    Credit for leaseholders who demonstrate measurable soil health improvement
    over a review cycle. Applied before the GUF floor — the credit may drive the
    fee toward zero, but the floor prevents it going negative (NLSA §9.2, §3):
    rewards beyond zero are separate Trust disbursements backed by stewardship EOH.

    Args:
        area_slu: Parcel area in SLU.
        delta_shi: Change in Soil Health Index over the review cycle.
                   Only positive (improvement) values generate a credit.
        credit_rate: TEH/SLU per SHI point. Default: GUF_SOIL_CREDIT_RATE = 0.05.

    Returns:
        Credit amount (positive; subtract from GUF formula before applying floor).
        Returns 0.0 if delta_shi ≤ 0.
    """
    if delta_shi <= 0.0:
        return 0.0
    return credit_rate * area_slu * delta_shi


# ===========================================================================
# Section 7 — Trust Integration
# ===========================================================================

def guf_trust_inflow(
    guf_revenues: list[float],
    subsidies_absorbed: float = 0.0,
) -> dict:
    """
    Aggregate GUF payments into a Trust inflow figure. (NLSA §7.1)

    GUF is circulatory TEH: it moves from stewards to the Trust without creating
    or destroying currency. Like levy_collection() in core/fiscal.py, this is pure
    redistribution — the ledger identity holds throughout.

    At moderate-to-high ε, GUF revenue may exceed levy income as the levy base
    (labor income) contracts with automation. Pass the returned "net_inflow" as
    an additional inflow alongside levy_revenue in trust_management().

    Trust integration point: net_inflow feeds into trust_management() as:
      trust_management(
          trust_balance  = ...,
          levy_revenue   = levy_revenue + guf_inflow["net_inflow"],
          ...
      )
    This mirrors how care_stipend_aggregate was wired into fiscal_snapshot().

    Args:
        guf_revenues: GUF payment from each parcel this period (TEH/year).
                      Pass guf_applied for each parcel (after review cap).
        subsidies_absorbed: Total income-linked subsidy cost absorbed by the
                            Trust's land fund this period (TEH/year). This is
                            the sum of subsidy_amount from income_linked_subsidy()
                            across all subsidized leaseholders.

    Returns:
        dict: {
          "gross_revenue":      float,   (sum of all parcel GUF payments)
          "subsidies_absorbed": float,   (Trust pays; reduces net to general fund)
          "net_inflow":         float,   (gross − subsidies; add to trust levy_revenue)
          "parcel_count":       int,
          "circulatory":        bool,    (always True)
        }
    """
    gross_revenue = sum(guf_revenues)
    net_inflow    = max(0.0, gross_revenue - subsidies_absorbed)

    return {
        "gross_revenue":      gross_revenue,
        "subsidies_absorbed": subsidies_absorbed,
        "net_inflow":         net_inflow,
        "parcel_count":       len(guf_revenues),
        "circulatory":        True,
    }
