"""
land/collective — Standard collective land-inventory tools.

Provides a batch GUF calculator and two synthetic archetype factories so any
collective can compute aggregate GUF, income-linked subsidies, and soil credits
from a plain list of parcel dicts.

Standard parcel dict schema
───────────────────────────
Required:
  area_slu        float   parcel area in SLU (1 SLU = 100 m²)
  location_value  float   L(p) ∈ [0,1]; pre-computed or via location_value_index()
  use_category    str     key from USE_CATEGORIES

Optional — forwarded to ground_use_fee():
  ecosystem_services    list[dict]
  infrastructure_assets list[dict]
  demand_supply_ratio   float   default 0.0
  zone_adj              float   default 1.0
  occupancy_fraction    float   default 1.0
  custom_u_ref          float   override U_ref for mixed-use blends
  residential           bool    default True

Optional — handled by this module:
  parcel_id        str     label for reporting; default "p{i}"
  occupant_income  float   for income_linked_subsidy() σ-curve; None → no subsidy
  guf_previous     float   for review_cycle_cap(); None → no cap
  delta_shi        float   Soil Health Index improvement for soil_health_credit(); None → 0

This schema maps directly to geo-data pipeline outputs: a GeoJSON or CSV loader
needs only to rename columns to these keys. The field set is a superset of the
minimum required by ground_use_fee() so downstream tools can be built on it.

Mission Statement: §"Land is held by the collective … stewardship leases …
the fee reflects real costs rather than speculative value."
"""

from __future__ import annotations

from hours_eoh.land.guf import (
    ground_use_fee,
    review_cycle_cap,
    income_linked_subsidy,
    soil_health_credit,
    guf_trust_inflow,
    epsilon_scaling,
)

# Keys required in every parcel dict
_REQUIRED_KEYS: frozenset[str] = frozenset({"area_slu", "location_value", "use_category"})

# Keys spread directly into ground_use_fee() as keyword arguments
_GUF_SPREAD_KEYS: frozenset[str] = frozenset({
    "ecosystem_services", "infrastructure_assets", "demand_supply_ratio",
    "zone_adj", "occupancy_fraction", "custom_u_ref", "residential",
})

# Keys consumed by collective processing — not forwarded to ground_use_fee()
_META_KEYS: frozenset[str] = frozenset({
    "parcel_id", "occupant_income", "guf_previous", "delta_shi",
})


def _validate_parcel(parcel: dict, idx: int) -> None:
    missing = _REQUIRED_KEYS - parcel.keys()
    if missing:
        raise ValueError(
            f"Parcel {idx} missing required fields: {sorted(missing)}"
        )


def compute_collective_guf(
    parcels: list[dict],
    epsilon: float,
    median_income: float = 0.0,
    pop_coverage_frac: float = 1.0,
) -> dict:
    """
    Batch GUF calculator for a collective land inventory. (NLSA §7.1)

    Per parcel:
      1. ground_use_fee() — master equation (guf_floor=0; floor handled after credits)
      2. soil_health_credit() subtracted from guf_formula if delta_shi present
      3. review_cycle_cap() applied if guf_previous present
      4. income_linked_subsidy() applied if occupant_income and median_income > 0
    Then aggregates via guf_trust_inflow().

    Args:
        parcels:          List of parcel dicts per standard schema above.
        epsilon:          Automation level [0.0, 0.99].
        median_income:    Collective median post-levy income (TEH/year).
                          Pass 0 to skip subsidy calculation.
        pop_coverage_frac: Fraction of population covered by this inventory.
                           Informational; does not rescale fees.

    Returns:
        dict: {
          "epsilon":            float,
          "parcel_count":       int,
          "guf_gross_revenue":  float,   sum of per-parcel guf_applied pre-subsidy
          "subsidies_absorbed": float,   sum of subsidy_amount across subsidized parcels
          "guf_net_inflow":     float,   gross_revenue − subsidies_absorbed
          "guf_by_parcel":      list[dict],  per-parcel breakdown
          "psi":                float,   Ψ(ε) (same for all parcels)
          "pop_coverage_frac":  float,
        }
    """
    psi = epsilon_scaling(epsilon)

    if not parcels:
        return {
            "epsilon":            epsilon,
            "parcel_count":       0,
            "guf_gross_revenue":  0.0,
            "subsidies_absorbed": 0.0,
            "guf_net_inflow":     0.0,
            "guf_by_parcel":      [],
            "psi":                psi,
            "pop_coverage_frac":  pop_coverage_frac,
        }

    guf_revenues:    list[float] = []
    total_subsidies: float       = 0.0
    by_parcel:       list[dict]  = []

    for i, parcel in enumerate(parcels):
        _validate_parcel(parcel, i)

        pid         = parcel.get("parcel_id", f"p{i}")
        guf_floor_p = max(0.0, float(parcel.get("guf_floor", 0.0)))
        guf_kwargs  = {k: v for k, v in parcel.items() if k in _GUF_SPREAD_KEYS}

        fee_result = ground_use_fee(
            area_slu=parcel["area_slu"],
            location_value=parcel["location_value"],
            use_category=parcel["use_category"],
            epsilon=epsilon,
            guf_floor=0.0,  # floor applied below, after soil credit
            **guf_kwargs,
        )

        guf_formula = fee_result["guf_formula"]

        # Soil health credit (applies before floor; agricultural improvement incentive)
        delta_shi = parcel.get("delta_shi")
        if delta_shi is not None and float(delta_shi) > 0.0:
            guf_formula -= soil_health_credit(parcel["area_slu"], float(delta_shi))

        guf_applied = max(guf_floor_p, guf_formula)
        cap_binds   = False

        # 5-year review cycle cap
        guf_previous = parcel.get("guf_previous")
        if guf_previous is not None:
            cap_result  = review_cycle_cap(guf_applied, float(guf_previous))
            guf_applied = cap_result["guf_applied"]
            cap_binds   = cap_result["cap_binds"]

        # Income-linked subsidy (σ-curve)
        subsidy_amount   = 0.0
        occupant_income  = parcel.get("occupant_income")
        if occupant_income is not None and median_income > 0.0:
            sub_result      = income_linked_subsidy(
                guf_applied, float(occupant_income), median_income
            )
            subsidy_amount   = sub_result["subsidy_amount"]
            total_subsidies += subsidy_amount

        guf_revenues.append(guf_applied)
        by_parcel.append({
            "parcel_id":      pid,
            "guf_applied":    guf_applied,
            "base_fee":       fee_result["base_fee"],
            "eco_surcharge":  fee_result["eco_surcharge"],
            "infra_premium":  fee_result["infra_premium"],
            "psi":            fee_result["psi"],
            "subsidy_amount": subsidy_amount,
            "cap_binds":      cap_binds,
        })

    inflow = guf_trust_inflow(guf_revenues, subsidies_absorbed=total_subsidies)

    return {
        "epsilon":            epsilon,
        "parcel_count":       len(parcels),
        "guf_gross_revenue":  inflow["gross_revenue"],
        "subsidies_absorbed": inflow["subsidies_absorbed"],
        "guf_net_inflow":     inflow["net_inflow"],
        "guf_by_parcel":      by_parcel,
        "psi":                psi,
        "pop_coverage_frac":  pop_coverage_frac,
    }


# ---------------------------------------------------------------------------
# Archetype factories
# ---------------------------------------------------------------------------

def make_urban_collective(parcel_count: int = 10_000) -> list[dict]:
    """
    Synthetic dense urban collective inventory for modeling and calibration.

    Mix: 75% residential_primary · 15% commercial_retail · 5% commercial_office
         · 5% institutional. High location values; moderate demand pressure.

    Args:
        parcel_count: Total parcel count. Fractional split rounded; remainder
                      assigned to institutional.

    Returns:
        list[dict]: Parcel dicts using the standard schema.
    """
    n_res    = round(0.75 * parcel_count)
    n_retail = round(0.15 * parcel_count)
    n_office = round(0.05 * parcel_count)
    n_inst   = parcel_count - n_res - n_retail - n_office

    parcels: list[dict] = []

    for i in range(n_res):
        parcels.append({
            "parcel_id":           f"urban_res_{i}",
            "area_slu":            2.5,
            "location_value":      0.75,
            "use_category":        "residential_primary",
            "demand_supply_ratio": 0.6,
        })
    for i in range(n_retail):
        parcels.append({
            "parcel_id":           f"urban_retail_{i}",
            "area_slu":            4.0,
            "location_value":      0.85,
            "use_category":        "commercial_retail",
            "demand_supply_ratio": 0.4,
            "residential":         False,
        })
    for i in range(n_office):
        parcels.append({
            "parcel_id":           f"urban_office_{i}",
            "area_slu":            3.0,
            "location_value":      0.80,
            "use_category":        "commercial_office",
            "demand_supply_ratio": 0.4,
            "residential":         False,
        })
    for i in range(n_inst):
        parcels.append({
            "parcel_id":      f"urban_inst_{i}",
            "area_slu":       8.0,
            "location_value": 0.65,
            "use_category":   "institutional",
        })

    return parcels


def make_rural_collective(parcel_count: int = 1_000) -> list[dict]:
    """
    Synthetic rural/agricultural collective inventory for modeling and calibration.

    Mix: 50% agricultural_active · 20% agricultural_fallow · 20% residential_primary
         · 10% conservation_credit. Low location values; no demand pressure.

    Args:
        parcel_count: Total parcel count. Remainder assigned to conservation_credit.

    Returns:
        list[dict]: Parcel dicts using the standard schema.
    """
    n_ag_active = round(0.50 * parcel_count)
    n_ag_fallow = round(0.20 * parcel_count)
    n_res       = round(0.20 * parcel_count)
    n_cons      = parcel_count - n_ag_active - n_ag_fallow - n_res

    parcels: list[dict] = []

    for i in range(n_ag_active):
        parcels.append({
            "parcel_id":      f"rural_ag_active_{i}",
            "area_slu":       80.0,
            "location_value": 0.25,
            "use_category":   "agricultural_active",
        })
    for i in range(n_ag_fallow):
        parcels.append({
            "parcel_id":      f"rural_ag_fallow_{i}",
            "area_slu":       40.0,
            "location_value": 0.20,
            "use_category":   "agricultural_fallow",
        })
    for i in range(n_res):
        parcels.append({
            "parcel_id":      f"rural_res_{i}",
            "area_slu":       5.0,
            "location_value": 0.35,
            "use_category":   "residential_primary",
        })
    for i in range(n_cons):
        parcels.append({
            "parcel_id":      f"rural_cons_{i}",
            "area_slu":       120.0,
            "location_value": 0.15,
            "use_category":   "conservation",
        })

    return parcels
