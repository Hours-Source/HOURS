"""
Ground Use Fee (GUF) calculation framework.

Implements NLSA Template

Master equation (NLSA Eq. 1, as applied since 2026-08-20):
  GUF(p) = [Ψ_b·A(p)×L(p)×U(p,ε)×D(p)×Z(p) + Ψ_e·E(p,ε) + Ψ_i·I(p,ε)] × Ω(p)

where (Ψ_b, Ψ_e, Ψ_i) = psi_application(ε, psi_policy). THE DEFAULT IS
`retired`, i.e. all three are 1.0, and the equation reduces to

  GUF(p) = [A(p)×L(p)×U(p,ε)×D(p)×Z(p) + E(p,ε) + I(p,ε)] × Ω(p)

Pass psi_policy="bell" to recover NLSA Eq. 1 verbatim, Ψ(ε) multiplying the
whole bracket. See `psi_application` for why the bell was retired.

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

ε arc shape, under the default `retired` policy: MONOTONE FALLING, carried by
α(ε) = labor_content_scaling inside U(p,ε). Unautomated land administration
takes more human hours, so the fee is highest at subsistence and declines as
automation takes over the work. The bell shape it replaced — low at both ends,
peak at ε=0.40 — was an artifact of two far-end assumptions that did not
survive audit (`psi_application`, handoffs/guf_redefinition.md §17).

GUF revenue is circulatory TEH flowing to the Trust. At moderate-to-high ε
it may become the Trust's dominant revenue source, replacing the contracting
labor levy base. See guf_trust_inflow() for Trust wiring. NOTE this claim was
FALSE under the bell — GUF/levy ran 7.54× at ε=0.20 down to 0.10× at ε=0.99,
so GUF handed over TO the levy rather than replacing it. Under `retired` it
holds: GUF/levy stays ≥ 0.90× across the whole arc and reaches 2.77× at
ε=0.99. Retiring Ψ was decided on other grounds; that it repairs this claim is
corroboration, not the argument.

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
    GUF_ECOSYSTEM_SERVICES,
    GUF_INFRA_MU_TRANSIT, GUF_INFRA_MU_UTILITIES, GUF_INFRA_MU_PUBLIC_SPACE,
    GUF_CHI_EXTERNAL,
    GUF_REVIEW_CYCLE_CAP,
    GUF_SUBSIDY_LOWER_THRESHOLD, GUF_SUBSIDY_FLOOR_RATE, GUF_AFFORDABILITY_THRESHOLD,
    GUF_SOIL_CREDIT_RATE,
    GUF_WRITEDOWN_AMORTIZATION_YEARS,
    GUF_EOH_ACCUMULATION_THRESHOLD,
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

# ---------------------------------------------------------------------------
# Term basis registry — what each term of the master equation IS
# handoffs/guf_redefinition.md §10 step 1 ("adopt E as a step")
# ---------------------------------------------------------------------------

#: The closed vocabulary of definitional bases a fee term may rest on. These are
#: not interchangeable: two terms on different bases answer different questions
#: and must not be netted, calibrated against one another, or resolved by one
#: instrument.
FEE_BASES: tuple[str, ...] = (
    "extent",       # the physical quantity the fee is assessed over
    "cost_flow",    # recurring labour the holding costs, per period
    "cost_stock",   # one-off labour amortised over an asset's life
    "rent",         # unearned locational surplus (market-derived)
    "congestion",   # scarcity/occupancy pressure
    "damage",       # value destroyed by the use (Pigouvian)
    "policy",       # a declared charter choice, not a measurement
    "utilisation",  # the fraction of the assessed quantity actually in use
    "unresolved",   # no basis survives scrutiny — see the entry
)

#: WHAT EACH TERM OF NLSA Eq. 1 IS, declared rather than inferred.
#:
#: `spec_direction` is scored against the inverted-Goldilocks spec
#: (handoffs/guf_redefinition.md §1): cheap remote, expensive in serviced
#: sprawl, cheap dense. "aligned" moves the fee the way the spec wants as
#: density rises; "inverted" moves it the wrong way; "neutral" is
#: density-independent.
#:
#: `epsilon_response` records whether the term carries its OWN automation
#: adjustment. It is here because the double-application it exposes is
#: invisible in any single function: U carries α(ε) internally AND Ψ(ε)
#: multiplies the bracket that contains it, so the flow leg is discounted
#: twice for the same stated reason. See `psi_application`.
TERM_BASIS: dict[str, dict[str, str]] = {
    "A": {
        "basis": "extent",
        "quantity": "parcel ground footprint in Standard Land Units",
        "spec_direction": "neutral",
        "epsilon_response": "none",
        "why": (
            "The base the fee is assessed over. SLUs are an AREA unit, which is "
            "why parcel count does not enter the fee at all — see "
            "scenarios/guf_magnitude.subdivision_invariance."
        ),
    },
    "L": {
        "basis": "rent",
        "quantity": "hedonic regression on parcel transaction values",
        "spec_direction": "inverted",
        "epsilon_response": "none",
        "why": (
            "Its own provenance entry defines it as the output of a hedonic "
            "regression — 'the standard land-valuation method'. That is "
            "speculative value, which the Mission Statement disclaims for this "
            "fee, and it peaks in the dense core where the spec wants the fee "
            "cheapest. Slated for redefinition as relative servicing intensity "
            "or deletion; §15 of the memo names the instrument that decides."
        ),
    },
    "U": {
        "basis": "cost_flow",
        "quantity": "recurring servicing labour per SLU per year",
        "spec_direction": "aligned",
        "epsilon_response": "alpha",
        "why": (
            "The one term whose resolves_by names the quantity the fee is "
            "DEFINED as. Carries labor_content_scaling(ε) internally."
        ),
    },
    "D": {
        "basis": "congestion",
        "quantity": "occupancy pressure against a constitutional ceiling",
        "spec_direction": "inverted",
        "epsilon_response": "none",
        "why": (
            "Congestion is not a cost, and it is a density proxy — so it lifts "
            "the fee exactly where the spec wants it lowest. Slated to be "
            "dropped."
        ),
    },
    "Z": {
        "basis": "policy",
        "quantity": "local zone adjustment within a permitted band",
        "spec_direction": "neutral",
        "epsilon_response": "none",
        "why": (
            "Declared governance discretion, and the honest home for any "
            "wanted location premium: currency-free, market-free, and openly a "
            "charter decision rather than a measurement."
        ),
    },
    "E": {
        "basis": "damage",
        "quantity": "ecosystem service volume displaced by the use",
        "spec_direction": "aligned",
        "epsilon_response": "kappa",
        "why": (
            "Correct basis for the land-take leg, and numerically inert: "
            "Phase 1b measured its effect on the calibration at ≤0.017%, and it "
            "would need ~938× the declared profile to rival base_fee."
        ),
    },
    "I": {
        "basis": "cost_stock",
        "quantity": "construction labour, annuitised over design life and shared across beneficiary parcels",
        "spec_direction": "aligned",
        "epsilon_response": "construction_epoch",
        "why": (
            "NOT benefit-received, which is how it reads and how the redefinition "
            "memo first scored it. cost_teh/(design_life × beneficiary_count) is "
            "an amortised capital cost. It is therefore the STOCK leg to U's "
            "FLOW leg — the Phase 4 partition, already implemented here and "
            "unrecognised — and it is disjoint from the servicing census by "
            "construction, because that census excludes construction "
            "occupations by name. Sign-aligned and structurally so: the "
            "proximity factor is bounded in (0,1] while 1/beneficiary_count is "
            "unbounded, so sharing dominates and dense parcels pay less."
        ),
    },
    "Psi": {
        "basis": "unresolved",
        "quantity": "—",
        "spec_direction": "inverted",
        "epsilon_response": "psi",
        "why": (
            "Its two ends carry two different claims and neither survives. The "
            "ε→0.99 end ('labor costs collapse') is the SAME claim α(ε) already "
            "implements inside U, applied a second time — together they discount "
            "the flow leg 271× from its ε=0.40 reference. The ε=0 end "
            "('institutional capacity is minimal') is a claim about COLLECTION "
            "CAPABILITY, not cost, and it runs OPPOSITE to α, which correctly "
            "rises at subsistence. Multiplying them conflates what a holding "
            "costs with whether an institution can levy it. See `psi_application`."
        ),
    },
    "Omega": {
        "basis": "utilisation",
        "quantity": "occupancy fraction of the parcel",
        "spec_direction": "neutral",
        "epsilon_response": "none",
        "why": (
            "A fraction of the parcel, not a headcount — which is why it cannot "
            "carry the throughput-scaling share of servicing cost."
        ),
    },
}


# ---------------------------------------------------------------------------
# Ψ application policy
# ---------------------------------------------------------------------------

#: How Ψ(ε) is applied to the three components of the master equation.
#: `retired` is the DEFAULT since 2026-08-20 (author decision). `bell` is the
#: pre-flip behaviour and remains fully reachable and tested — retiring a curve
#: is not the same as removing the ability to reproduce it, and every NLSA §4.4
#: boundary condition is still pinned against it.
PSI_POLICIES: tuple[str, ...] = ("bell", "flow_only", "retired")


def psi_application(epsilon: float, policy: str = "retired") -> tuple[float, float, float]:
    """
    The multiplier Ψ contributes to each component: (base_fee, E, I).

    Governing forms:

        bell       (Ψ, Ψ, Ψ)      shipped — Ψ multiplies the whole bracket
        flow_only  (Ψ, 1, 1)      Ψ multiplies only the flow leg
        retired    (1, 1, 1)      Ψ ≡ 1; the ε response lives where it is earned

    units: dimensionless, one factor per component.

    WHAT THE POLICIES ARE CLAIMING, in order of how much they concede:

    `bell` asserts that a single global automation curve scales recurring
    servicing cost, ecosystem damage and amortised construction debt by the same
    factor. It was the shipped default until 2026-08-20 and reproduces every
    pre-flip figure exactly.

    `flow_only` fixes one structural defect without touching the flow leg: Ψ
    currently multiplies I, and I's own docstring says cost_teh "retains that
    higher cost for its full design life", with aggregate I contracting only as
    legacy assets are REPLACED at higher ε. Multiplying an epoch-fixed annuity by
    current automation discounts it a second time and short-circuits the asset
    turnover that was supposed to carry the response. The same argument applies
    to E, whose κ already carries its own β(ε).

    `retired` additionally drops the flow-leg duplication: U already carries
    α(ε) = labor_content_scaling, whose stated rationale ("the declining human
    labor content of land-use administration") is Ψ's own high-end rationale
    verbatim. At ε=0.99 α = 0.1051 and Ψ = 0.0349, so the pair discounts the flow
    leg to 0.0037 of its ε=0.40 value — 271×, for one stated reason applied
    twice. At ε=0 they run in OPPOSITE directions (α = 1.4695, Ψ = 0.0200),
    because Ψ's low end is about institutional capacity rather than cost.

    ε-behaviour: at `retired` the fee's automation response is α(ε) on the flow
    leg and asset turnover on the stock leg — both mechanisms that name what they
    measure. Nothing becomes ε-invariant.

    Worked example (ε=0.99): bell → (0.0349, 0.0349, 0.0349); flow_only →
    (0.0349, 1.0, 1.0); retired → (1.0, 1.0, 1.0).

    Raises:
        ValueError: if policy is not in PSI_POLICIES.
    """
    if policy not in PSI_POLICIES:
        raise ValueError(f"psi_policy must be one of {PSI_POLICIES}, got {policy!r}")
    if policy == "retired":
        return (1.0, 1.0, 1.0)
    psi = epsilon_scaling(epsilon)
    if policy == "flow_only":
        return (psi, 1.0, 1.0)
    return (psi, psi, psi)


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

    RETIRED FROM THE DEFAULT FEE PATH 2026-08-20 (author decision). This
    function still computes the curve and `psi_policy="bell"` still applies it,
    but `psi_application` defaults to `retired` and the shipped fee no longer
    uses it. The two justifications below are recorded as the claims that were
    audited and did not survive; do not restore them without reading
    handoffs/guf_redefinition.md §17.

      ~~At subsistence (ε=0), institutional capacity is minimal and the formal
      fee approaches a floor.~~ A claim about whether a fee can be COLLECTED,
      not about what a holding COSTS — and it points opposite to α(ε), which
      correctly RISES at subsistence (1.4695 against this floor's 0.0200).

      ~~At post-scarcity (ε=0.99), labor costs collapse and the fee contracts
      to a stewardship-only floor.~~ The same claim α(ε) already makes inside
      U ("the declining human labor content of land-use administration"). The
      pair discounts the flow leg to 0.0037 of its ε=0.40 reference — 273× for
      one mechanism counted twice.

    Bell-shaped function: near-floor at ε=0 and ε=0.99, peak near ε=0.40.

    Boundary guarantees:
      Ψ(0)    ≈ GUF_PSI_FLOOR  (= 0.02)
      Ψ(0.40) =  1.00          (the peak, exactly; ε* = a/(a+b) = 0.40)
      Ψ(0.99) ≈ 0.035          (< 0.05 × Ψ(0.40); post-scarcity floor satisfied)

    The peak was 1.061 until 2026-08-15: GUF_PSI_NORM was PINNED at 4.0 while
    claiming to normalize the curve to 1.0. It is now derived from a, b and the
    floor, so it tracks them. The fee curve fell ≈5.7% across the productive arc
    and no test noticed — tests/land/test_calibration.py::TestPsiNormalization
    is the pin that was missing.

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


def service_from_registry(
    service: str,
    volume: float,
    retained: float = 0.0,
    kappa_ref: float | None = None,
    beta: float | None = None,
) -> dict:
    """
    Build one E(p,ε) service dict from the named-service registry.

    Governing intent: κ and β are PER-SERVICE PARTNERS. Eq. 15 derives κ_max
    from κ_ref *through* β, so a caller who pairs carbon's κ with pollination's
    β gets a replacement-cost curve belonging to neither, and nothing downstream
    can detect it. Naming the service binds them together.

    Until 2026-08-17 the seven GUF_ECO_KAPPA_* constants were read by no code
    path at all — E defaulted to zero and every caller passed bare literals — so
    the named constants documented values the package never used.

    Args:
        service:   Key of GUF_ECOSYSTEM_SERVICES.
        volume:    Annual service volume, in that service's declared unit.
        retained:  ρ_s(p) ∈ [0, 1] — fraction still delivered in the developed
                   state. 0.0 means the service is wholly displaced.
        kappa_ref: Optional jurisdiction override. κ is genuinely local (a
                   wetland's filtration value is not a global constant), so an
                   override is legitimate — it REPLACES the registry value and
                   is reported as such, never silently merged.
        beta:      Optional override, same treatment.

    Returns:
        A service dict for `ecosystem_displacement_surcharge`, carrying
        "service", "unit" and "kappa_source" ("registry" | "override") so the
        provenance of every term survives into the breakdown.
    """
    if service not in GUF_ECOSYSTEM_SERVICES:
        raise KeyError(
            f"unknown ecosystem service {service!r}; registered services are "
            f"{sorted(GUF_ECOSYSTEM_SERVICES)}"
        )
    spec = GUF_ECOSYSTEM_SERVICES[service]
    k = float(spec["kappa_ref"]) if kappa_ref is None else kappa_ref  # type: ignore[arg-type]
    b = float(spec["beta"]) if beta is None else beta                 # type: ignore[arg-type]
    return {
        "label":        service,
        "service":      service,
        "volume":       volume,
        "kappa_ref":    k,
        "beta":         b,
        "retained":     retained,
        "unit":         str(spec["unit"]),
        "kappa_source": "registry" if kappa_ref is None else "override",
        "beta_source":  "registry" if beta is None else "override",
    }


def _resolve_kappa_beta(svc: dict) -> tuple[float, float]:
    """
    Resolve one service dict's (κ_ref, β) pair.

    Shared by `ecosystem_displacement_surcharge` (E) and `rebuilding_surcharge`
    (the §9 restoration/abandonment pathway) so the two cannot drift — they
    consume the same table and previously each read the caller's literals
    independently.

    Precedence: explicit κ_ref AND β win outright (the pre-2026-08-17 form every
    existing caller uses); otherwise a "service" key inherits both from the
    registry, with either individually overridable. A dict carrying neither
    raises, naming the registered services.
    """
    if "kappa_ref" in svc and "beta" in svc:
        return float(svc["kappa_ref"]), float(svc["beta"])
    if "service" in svc:
        resolved = service_from_registry(
            service=svc["service"],
            volume=0.0,
            kappa_ref=svc.get("kappa_ref"),
            beta=svc.get("beta"),
        )
        return float(resolved["kappa_ref"]), float(resolved["beta"])
    raise KeyError(
        "each service needs either explicit 'kappa_ref' and 'beta', or a "
        f"'service' key naming one of {sorted(GUF_ECOSYSTEM_SERVICES)}; "
        f"got keys {sorted(svc)}"
    )


def ecosystem_services_for_area(
    area_hectares: float,
    per_hectare_volumes: dict[str, float],
    retained: float | dict[str, float] = 0.0,
) -> list[dict]:
    """
    Scale per-hectare ecosystem service volumes to a land area.

    Governing equation:

        V_s = area_hectares × per_hectare_volume[s]        [service units/yr]

    THE V_s INTAKE. E(p,ε) was reachable only by hand-building one parcel's
    service list, which is why it has never been run at land-class scale. This
    turns a per-hectare service profile — the form ecological survey data
    actually arrives in — into the list E consumes.

    WHAT THIS DOES NOT DO: it supplies no volumes. `per_hectare_volumes` is the
    caller's measurement, and the package ships none — there is no measured
    figure here for how much filtration a hectare of forest delivers. Inventing
    one would enter with the same standing as a measured value and afterwards
    nothing could tell them apart, which is the discipline
    reference/personal_basket.py holds for the same reason.

    Args:
        area_hectares:       Land area the profile applies to.
        per_hectare_volumes: {service name: volume per hectare per year}, keys
                             from GUF_ECOSYSTEM_SERVICES.
        retained:            ρ_s — a scalar applied to every service, or a dict
                             keyed by service name (missing keys → 0.0).

    Returns:
        List of service dicts, ready for `ecosystem_displacement_surcharge`.
    """
    if area_hectares < 0.0:
        raise ValueError(f"area_hectares must be >= 0, got {area_hectares}")

    out: list[dict] = []
    for name, per_ha in per_hectare_volumes.items():
        rho = retained.get(name, 0.0) if isinstance(retained, dict) else retained
        out.append(
            service_from_registry(
                service=name,
                volume=area_hectares * per_ha,
                retained=rho,
            )
        )
    return out


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
        volume = svc["volume"]

        kappa_ref, beta = _resolve_kappa_beta(svc)
        kappa        = ecosystem_service_kappa(kappa_ref, beta, epsilon)
        retained     = max(0.0, min(1.0, svc.get("retained", 0.0)))
        contribution = volume * kappa * (1.0 - retained)

        by_service.append({
            "label":            svc.get("label", svc.get("service", "unknown")),
            "volume":           volume,
            "kappa_ref":        kappa_ref,
            "beta":             beta,
            "kappa_epsilon":    kappa,
            "retained":         retained,
            "contribution_teh": contribution,
            "unit":             svc.get("unit"),
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
    psi_policy: str = "retired",
) -> dict:
    """
    Master Ground Use Fee calculation for a single parcel. (NLSA Eq. 1-2)

    GUF(p) = max(floor, [Ψ_b·base_fee + Ψ_e·E(p,ε) + Ψ_i·I(p,ε)] × Ω(p))

    where (Ψ_b, Ψ_e, Ψ_i) = psi_application(ε, psi_policy). At the default
    `bell` all three are Ψ(ε) and this is exactly NLSA Eq. 1 as shipped:

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
        psi_policy: One of PSI_POLICIES. `retired` (default) sets Ψ ≡ 1 and
            leaves the ε response to α(ε) and asset turnover. `flow_only` keeps
            Ψ on the flow leg only; `bell` reproduces the pre-2026-08-20 fee
            exactly. See `psi_application` for what each one claims.

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
    psi_b, psi_e, psi_i = psi_application(epsilon, psi_policy)
    guf_formula        = (
        psi_b * bf + psi_e * eco_amount + psi_i * infra_amount
    ) * occupancy_fraction
    guf_applied        = max(guf_floor, guf_formula)

    return {
        "guf_formula":     guf_formula,
        "guf_applied":     guf_applied,
        "base_fee":        bf,
        "eco_surcharge":   eco_amount,
        "infra_premium":   infra_amount,
        # The factor actually applied to base_fee. NOT necessarily Ψ(ε): under
        # `retired` it is 1.0. Reported this way so a caller that multiplies
        # base_fee by it reconstructs the fee under every policy — a reported
        # multiplier that is not the applied one is the silently-ignored-
        # parameter failure this repo keeps finding.
        "psi":             psi_b,
        "psi_raw":         psi,
        "occupancy":       occupancy_fraction,
        "demand_modifier": d_modifier,
        "eco_breakdown":   eco_result,
        "infra_breakdown": infra_result,
        "floor_applied":   guf_applied > guf_formula + 1e-9,
        "epsilon":         epsilon,
        "psi_policy":      psi_policy,
        "psi_applied":     (psi_b, psi_e, psi_i),
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


def min_income_for_access(
    guf_applied: float,
    median_income: float,
    affordability_threshold: float = GUF_AFFORDABILITY_THRESHOLD,
    guarantee_income: float | None = None,
) -> dict:
    """
    Minimum income at which a primary residential parcel is affordable.

    Inverse query of ground_use_fee() + income_linked_subsidy(): given a parcel's
    annual GUF and a collective's median income, find the income floor at which
    housing is accessible — with and without the income-linked subsidy.

    The subsidy tiers (NLSA Eq. 23-24) mean the effective GUF is income-dependent:
    at the lowest incomes the subsidy reduces GUF to GUF_SUBSIDY_FLOOR_RATE of
    the assessed amount. Two analytical minima follow directly:

      min_income_no_subsidy   = guf_applied / affordability_threshold
      min_income_full_subsidy = GUF_SUBSIDY_FLOOR_RATE × guf_applied / affordability_threshold

    Status classification (all boundaries scale with affordability_threshold):
      ACCESSIBLE            guf_applied ≤ threshold × median_income
                            (affordable at median without subsidy)
      SUBSIDISED_ACCESSIBLE threshold × median < guf_applied ≤ median_income
                            (subsidy makes it accessible below median)
      INACCESSIBLE          guf_applied > median_income
                            (min_income_full_subsidy > median; only above-median
                            earners could afford it, who don't receive the subsidy)

    Args:
        guf_applied: Annual GUF in TEH/year — use ground_use_fee()["guf_applied"]
                     (or after review_cycle_cap() if applicable).
        median_income: Collective median post-levy income (TEH/year).
        affordability_threshold: GUF as fraction of income that defines accessible
                     housing. Default: GUF_AFFORDABILITY_THRESHOLD (0.25).
        guarantee_income: Annual TEH from the sufficiency guarantee (from
                     sufficiency_guarantee()["total_per_person"]). When provided,
                     accessible_at_guarantee is computed. None → field is None.

    Returns:
        dict with keys:
          "guf_applied"                  float
          "median_income"                float
          "affordability_threshold"      float
          "min_income_no_subsidy"        float  guf_applied / threshold
          "min_income_full_subsidy"      float  GUF_SUBSIDY_FLOOR_RATE × guf_applied / threshold
          "affordability_ratio_at_median" float  guf_applied / median_income
          "accessible_at_median"         bool   ratio_at_median ≤ threshold
          "accessible_at_guarantee"      bool | None  None if guarantee_income not provided
          "status"                       str    "ACCESSIBLE" | "SUBSIDISED_ACCESSIBLE" | "INACCESSIBLE"
          "subsidy_absorption"           float  Trust-absorbed fraction at full subsidy (= 1 − FLOOR_RATE)

    Raises:
        ValueError: If guf_applied < 0, median_income ≤ 0, or threshold ≤ 0.

    Reference: Mission Statement §"Land stewardship and housing access";
    NLSA §6 (income-linked subsidy); Roadmap §2.3 (inverse query system).
    """
    if guf_applied < 0.0:
        raise ValueError(f"guf_applied must be ≥ 0, got {guf_applied}")
    if median_income <= 0.0:
        raise ValueError(f"median_income must be > 0, got {median_income}")
    if affordability_threshold <= 0.0:
        raise ValueError(f"affordability_threshold must be > 0, got {affordability_threshold}")

    min_income_no_subsidy   = guf_applied / affordability_threshold
    min_income_full_subsidy = GUF_SUBSIDY_FLOOR_RATE * guf_applied / affordability_threshold
    ratio_at_median         = guf_applied / median_income
    accessible_at_median    = ratio_at_median <= affordability_threshold

    # Status: boundaries scale cleanly with threshold
    if accessible_at_median:
        status = "ACCESSIBLE"
    elif guf_applied <= median_income:
        status = "SUBSIDISED_ACCESSIBLE"
    else:
        status = "INACCESSIBLE"

    accessible_at_guarantee: bool | None = None
    if guarantee_income is not None and guarantee_income > 0.0:
        guf_at_guarantee = income_linked_subsidy(
            guf_applied, steward_income=guarantee_income, median_income=median_income
        )["guf_effective"]
        accessible_at_guarantee = (guf_at_guarantee / guarantee_income) <= affordability_threshold
    elif guarantee_income is not None:
        accessible_at_guarantee = False

    return {
        "guf_applied":                  guf_applied,
        "median_income":                median_income,
        "affordability_threshold":      affordability_threshold,
        "min_income_no_subsidy":        min_income_no_subsidy,
        "min_income_full_subsidy":      min_income_full_subsidy,
        "affordability_ratio_at_median": ratio_at_median,
        "accessible_at_median":         accessible_at_median,
        "accessible_at_guarantee":      accessible_at_guarantee,
        "status":                       status,
        "subsidy_absorption":           1.0 - GUF_SUBSIDY_FLOOR_RATE,
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


# ===========================================================================
# Section 9 — Ecological Write-Down Events
# ===========================================================================

def rebuilding_surcharge(
    services_lost: list[dict],
    epsilon: float,
    amortization_years: float = GUF_WRITEDOWN_AMORTIZATION_YEARS,
) -> dict:
    """
    Rebuilding Surcharge R_b(p,ε) — annualized replacement cost of lost ecosystem services.
    (NLSA Eq. 28)

    Used under the abandonment pathway after an ecological write-down declaration.
    Distributes the labor cost of engineered replacement systems across affected parcels
    via their per-parcel lost service volumes. Like the Infrastructure Proximity Premium,
    this is an annualized share of collectively funded capital — the difference is that
    the capital replaces destroyed natural function rather than built infrastructure.

    The surcharge is ε-parameterized through κ_s(ε): at high ε automated replacement
    is cheaper, so R_b contracts along the arc. Amortized over Y_r years (default 50,
    matching standard infrastructure design life).

    Service dict fields:
      "volume_lost": float — annual service volume lost per parcel (pre-collapse minus
                              post-collapse), in the same physical units as kappa_ref
      "kappa_ref":   float — TEH per physical unit per year at ε=0.40 (same table as
                              ecosystem_displacement_surcharge)
      "beta":        float — automation sensitivity β_s ∈ [0.6, 1.2]
      "label":       str   — optional, for reporting

    Args:
        services_lost: Per-parcel lost service volumes (see above).
        epsilon: Current automation level [0.0, 0.99].
        amortization_years: Y_r — design life of replacement infrastructure in years.

    Returns:
        dict: {
          "surcharge_total":  float,       (TEH/year per parcel)
          "by_service":       list[dict],  (per-service breakdown)
          "epsilon":          float,
          "amortization_years": float,
        }
    """
    amortization_years = max(1.0, amortization_years)
    by_service = []
    total      = 0.0

    for svc in services_lost:
        volume_lost = max(0.0, svc["volume_lost"])
        # Same registry resolution as E(p,ε). This is the §9 restoration and
        # abandonment pathway, so it is the path a restoration-cost derivation
        # runs through — it must consume the same κ table, not a caller's
        # literals, or the two halves of the reset cost can disagree silently.
        kappa_ref, beta = _resolve_kappa_beta(svc)
        kappa        = ecosystem_service_kappa(kappa_ref, beta, epsilon)
        contribution = volume_lost * kappa / amortization_years

        by_service.append({
            "label":            svc.get("label", svc.get("service", "unknown")),
            "volume_lost":      volume_lost,
            "kappa_epsilon":    kappa,
            "amortization_years": amortization_years,
            "contribution_teh": contribution,
        })
        total += contribution

    return {
        "surcharge_total":    total,
        "by_service":         by_service,
        "epsilon":            epsilon,
        "amortization_years": amortization_years,
    }


def ground_use_fee_writedown(
    area_slu: float,
    location_value: float,
    use_category: str,
    epsilon: float,
    services_reset: list[dict] | None = None,
    services_lost: list[dict] | None = None,
    infrastructure_assets: list[dict] | None = None,
    demand_supply_ratio: float = 0.0,
    zone_adj: float = 1.0,
    occupancy_fraction: float = 1.0,
    guf_floor: float = 0.0,
    amortization_years: float = GUF_WRITEDOWN_AMORTIZATION_YEARS,
    custom_u_ref: float | None = None,
    residential: bool = True,
) -> dict:
    """
    Modified Ground Use Fee during an active ecological write-down event. (NLSA Eq. 29)

    GUF_wd(p) = Ψ(ε) × [A(p)×L(p)×U(p,ε)×D(p)×Z(p) + E_reset(p,ε) + I(p,ε) + R_b(p,ε)] × Ω(p)

    Differs from ground_use_fee() in two ways:
      1. E_reset uses reset V_s baselines (services_reset), not the current degraded state.
         Under the restoration pathway, baselines are set to the restoration target so the
         surcharge is maintained at the target level despite collapse. Pass the reset service
         list here instead of the pre-collapse originals.
      2. R_b is added under the abandonment pathway (services_lost is not None).
         Under the restoration pathway, pass services_lost=None → R_b = 0.

    The rate-change cap (review_cycle_cap) still applies to the result; call it separately
    after this function, as with standard ground_use_fee().

    Args:
        area_slu: Parcel ground footprint in SLU.
        location_value: L(p) ∈ [0, 1].
        use_category: Key from USE_CATEGORIES.
        epsilon: Current automation level [0.0, 0.99].
        services_reset: Service dicts with reset V_s baselines for E_reset(p,ε).
                        None → E_reset = 0.
        services_lost: Per-parcel lost service dicts for R_b(p,ε) (abandonment pathway).
                       None → restoration pathway, R_b = 0.
        infrastructure_assets: Asset dicts for I(p,ε). None → I = 0.
        demand_supply_ratio: Δ(p) for demand modifier. ≤ 0 → D = 1.0.
        zone_adj: Z(p) ∈ [0.80, 1.25].
        occupancy_fraction: Ω(p) ∈ (0, 1].
        guf_floor: Non-negative floor in TEH/year.
        amortization_years: Y_r for R_b calculation.
        custom_u_ref: Override U_ref for mixed-use blends.
        residential: True → residential demand sensitivity for D(p).

    Returns:
        dict extending ground_use_fee() output with:
          "rebuilding_surcharge": float,       (R_b(p,ε), TEH/year; 0 under restoration)
          "writedown_pathway":    str,          ("restoration" or "abandonment")
          "rb_breakdown":         dict | None,  (from rebuilding_surcharge())
    """
    psi        = epsilon_scaling(epsilon)
    u_coeff    = use_category_coefficient(use_category, epsilon, custom_u_ref)
    d_modifier = demand_pressure_modifier(demand_supply_ratio, residential)
    bf         = base_fee(area_slu, location_value, u_coeff, d_modifier, zone_adj)

    eco_result = None
    eco_amount = 0.0
    if services_reset:
        eco_result = ecosystem_displacement_surcharge(services_reset, epsilon)
        eco_amount = eco_result["surcharge_total"]

    infra_result = None
    infra_amount = 0.0
    if infrastructure_assets:
        infra_result = infrastructure_proximity_premium(infrastructure_assets, epsilon)
        infra_amount = infra_result["premium_total"]

    rb_result  = None
    rb_amount  = 0.0
    pathway    = "restoration"
    if services_lost is not None:
        rb_result = rebuilding_surcharge(services_lost, epsilon, amortization_years)
        rb_amount = rb_result["surcharge_total"]
        pathway   = "abandonment"

    occupancy_fraction = max(0.0, min(1.0, occupancy_fraction))
    guf_formula        = psi * (bf + eco_amount + infra_amount + rb_amount) * occupancy_fraction
    guf_applied        = max(guf_floor, guf_formula)

    return {
        "guf_formula":          guf_formula,
        "guf_applied":          guf_applied,
        "base_fee":             bf,
        "eco_surcharge":        eco_amount,
        "infra_premium":        infra_amount,
        "rebuilding_surcharge": rb_amount,
        "psi":                  psi,
        "occupancy":            occupancy_fraction,
        "demand_modifier":      d_modifier,
        "eco_breakdown":        eco_result,
        "infra_breakdown":      infra_result,
        "rb_breakdown":         rb_result,
        "writedown_pathway":    pathway,
        "floor_applied":        guf_applied > guf_formula + 1e-9,
        "epsilon":              epsilon,
    }


def eoh_accumulation_warning(
    unfulfilled_eoh: float,
    total_eoh: float,
    threshold: float = GUF_EOH_ACCUMULATION_THRESHOLD,
) -> dict:
    """
    EOH Accumulation Warning — preventive signal before ecological collapse. (NLSA §9.8)

    Monitors the ratio of unfulfilled ecological EOH to total assessed ecological EOH
    for a defined zone. When the ratio exceeds the threshold (default 0.30), a formal
    warning is issued, triggering two responses:

      1. Accelerated ρ_s review: all parcels in the zone undergo extraordinary review of
         retained service fractions outside the normal 5-year cycle.
      2. Ecology fund priority: the zone receives priority allocation from the Trust's
         ecological fund for directed stewardship labor.

    This warning is not a write-down declaration. It signals that the system is
    approaching a threshold and that preventive labor is less costly than post-collapse
    restoration. The GUF's role is to ensure the warning translates into fiscal action.

    Args:
        unfulfilled_eoh: Unmet ecological EOH in the monitored zone (EOH/period).
        total_eoh: Total assessed ecological EOH for the zone (EOH/period).
        threshold: Accumulation ratio above which the warning triggers.
                   Default: GUF_EOH_ACCUMULATION_THRESHOLD = 0.30.

    Returns:
        dict: {
          "ratio":                  float,  (unfulfilled / total; 0.0 if total ≤ 0)
          "threshold":              float,
          "warning":                bool,   (True when ratio > threshold)
          "unfulfilled_eoh":        float,
          "total_eoh":              float,
          "accelerated_rho_review": bool,   (triggered alongside warning)
          "ecology_fund_priority":  bool,   (triggered alongside warning)
        }
    """
    if total_eoh <= 0.0:
        ratio = 0.0
    else:
        ratio = max(0.0, unfulfilled_eoh) / total_eoh

    warning = ratio > threshold

    return {
        "ratio":                  ratio,
        "threshold":              threshold,
        "warning":                warning,
        "unfulfilled_eoh":        unfulfilled_eoh,
        "total_eoh":              total_eoh,
        "accelerated_rho_review": warning,
        "ecology_fund_priority":  warning,
    }
