"""
land/calibration — GUF rate and weight calibration tools.

Two functions for collectives that want to fit their GUF revenue to a fiscal
target or understand how sensitive their aggregate fee is to location-value
index weight choices.

  guf_rate_calibration      — find the use-coefficient multiplier k that
                               achieves a target GUF / levy revenue ratio
  guf_lvi_weight_sensitivity — sweep LVI weight variants to quantify sensitivity
                               of aggregate GUF to location sub-index weights

Mission Statement: §"Land is held by the collective … stewardship leases …
the fee reflects real costs rather than speculative value."
"""

from __future__ import annotations

from hours_eoh.data import SUFF_LEVY_RATE
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import levy_collection
from hours_eoh.land.guf import (
    USE_CATEGORIES,
    location_value_index,
    epsilon_scaling,
)
from hours_eoh.land.collective import compute_collective_guf

# Default LVI weight variants: canonical + four alternatives that shift emphasis
_DEFAULT_LVI_VARIANTS: list[dict] = [
    {"centrality": 0.35, "transit": 0.30, "services": 0.20, "natural_amenity": 0.15},  # canonical
    {"centrality": 0.45, "transit": 0.30, "services": 0.15, "natural_amenity": 0.10},  # urban core
    {"centrality": 0.25, "transit": 0.40, "services": 0.20, "natural_amenity": 0.15},  # transit-led
    {"centrality": 0.25, "transit": 0.20, "services": 0.30, "natural_amenity": 0.25},  # services/amenity
    {"centrality": 0.25, "transit": 0.25, "services": 0.25, "natural_amenity": 0.25},  # equal weights
]

# LVI sub-index keys that trigger recomputation in sensitivity analysis
_LVI_SUB_KEYS: frozenset[str] = frozenset(
    {"centrality", "transit", "services", "natural_amenity"}
)


def guf_rate_calibration(
    parcel_inventory: list[dict],
    target_guf_levy_ratio: float,
    population: float = 1_000_000.0,
    epsilon: float = 0.40,
    levy_rates: dict | None = None,
    tolerance: float = 0.01,
    psi_policy: str = "retired",
) -> dict:
    """
    Find the use-coefficient multiplier k that achieves target_guf_levy_ratio.

    Solves for k such that aggregate GUF(k) ≈ target_guf_levy_ratio × levy_revenue.

    GUF components split into:
      scalable: Ψ_base × k × base_fee × Ω   (use-coefficient-driven; linear in k)
      fixed:    (Ψ_E·E + Ψ_I·I) × Ω          (ecosystem/infra surcharges; invariant)

    The three Ψ factors come from psi_application(ε, psi_policy) and are the ones
    ACTUALLY applied. Under the default `retired` they are all 1.0.

    k = (target_guf − fixed) / scalable    (closed-form, exact when no floors bind)

    After solving, the function verifies by re-running compute_collective_guf
    with a small representative sample (up to 500 parcels) and reports the
    achieved ratio vs. the target.

    Args:
        parcel_inventory:      Standard parcel dicts (see collective.py schema).
        target_guf_levy_ratio: e.g. 1.0 → GUF ≈ levy revenue; 0.5 → GUF = half levy.
        population:            For levy revenue calculation.
        epsilon:               Automation level [0.0, 0.99].
        levy_rates:            Override default levy rates.
        tolerance:             Acceptable |achieved_ratio − target| for converged=True.
        psi_policy:            One of land.guf.PSI_POLICIES; default `retired`.

    Returns:
        dict: {
          "calibrated_multiplier": float,   k to apply to all use coefficients
          "achieved_ratio":        float,   actual GUF/levy at k (from sample)
          "levy_revenue":          float,
          "guf_at_calibrated_k":   float,   estimated aggregate GUF at k
          "target_guf_levy_ratio": float,
          "converged":             bool,
        }
    """
    rates = levy_rates or {"sufficiency": SUFF_LEVY_RATE}

    labor_income = eoh_to_teh_pipeline(epsilon=epsilon, population=population)["teh_created"]
    levy_revenue = levy_collection(labor_income, rates)["total_levied"]

    target_guf = target_guf_levy_ratio * levy_revenue

    # Base GUF at k=1 using full inventory
    base_result = compute_collective_guf(parcel_inventory, epsilon, psi_policy=psi_policy)
    by_parcel   = base_result["guf_by_parcel"]
    # The three factors ACTUALLY applied, not Ψ(ε): under `retired` they are all
    # 1.0, and under `flow_only` the E+I leg is unscaled while base_fee is not.
    # Decomposing with a single Ψ would solve for a k the fee never uses.
    psi_b, psi_e, psi_i = base_result["psi_applied"]

    # Decompose into scalable (base_fee driven) and fixed (E+I driven)
    scalable_sum = 0.0
    fixed_sum    = 0.0
    for parcel, row in zip(parcel_inventory, by_parcel):
        omega        = max(0.0, min(1.0, float(parcel.get("occupancy_fraction", 1.0))))
        scalable_sum += psi_b * row["base_fee"] * omega
        fixed_sum    += (
            psi_e * row["eco_surcharge"] + psi_i * row["infra_premium"]
        ) * omega

    converged = True
    if scalable_sum < 1e-9:
        # No scalable component — cannot calibrate (pure E+I inventory)
        k          = 1.0
        converged  = False
        estimated  = base_result["guf_gross_revenue"]
    else:
        k         = (target_guf - fixed_sum) / scalable_sum
        k         = max(0.01, min(1_000.0, k))
        estimated = k * scalable_sum + fixed_sum

    # Verify with a sample to account for floor clamping
    sample     = parcel_inventory[:500]
    scale_frac = len(parcel_inventory) / max(len(sample), 1)
    sample_mod = []
    for p in sample:
        p2             = dict(p)
        u_base         = USE_CATEGORIES.get(p["use_category"], 1.0)
        p2["custom_u_ref"] = k * u_base
        sample_mod.append(p2)

    sample_result  = compute_collective_guf(sample_mod, epsilon, psi_policy=psi_policy)
    achieved_guf   = sample_result["guf_gross_revenue"] * scale_frac
    achieved_ratio = achieved_guf / max(levy_revenue, 1.0)

    if abs(achieved_ratio - target_guf_levy_ratio) > tolerance:
        converged = False

    return {
        "calibrated_multiplier":  k,
        "achieved_ratio":         achieved_ratio,
        "levy_revenue":           levy_revenue,
        "guf_at_calibrated_k":    achieved_guf,
        "target_guf_levy_ratio":  target_guf_levy_ratio,
        "converged":              converged,
    }


def guf_lvi_weight_sensitivity(
    parcel_inventory: list[dict],
    epsilon: float = 0.40,
    weight_variants: list[dict] | None = None,
) -> dict:
    """
    Quantify sensitivity of aggregate GUF to location_value_index weight choices.

    For each weight variant, recomputes location_value via location_value_index()
    using each parcel's LVI sub-indices (centrality, transit, services,
    natural_amenity). If a parcel only has a pre-computed location_value (no
    sub-indices), that value is used unchanged for all variants.

    Args:
        parcel_inventory: Parcel dicts. Parcels with LVI sub-index fields
                          (centrality, transit, services, natural_amenity)
                          have location_value recomputed per variant. Parcels
                          with only location_value use that value for all variants.
        epsilon:          Automation level [0.0, 0.99].
        weight_variants:  List of weight dicts, each with keys "centrality",
                          "transit", "services", "natural_amenity" summing to 1.0.
                          None → 5 canonical variants (canonical + 4 alternatives).

    Returns:
        dict: {
          "epsilon":              float,
          "parcel_count":         int,
          "variants":             list[dict],  one per weight variant
          "sensitivity_range":    (float, float),  (min, max) aggregate GUF
          "relative_sensitivity": float,  (max−min) / mean aggregate GUF
        }

    Each variant dict:
        {
          "weights":               dict,
          "guf_aggregate":         float,
          "guf_net_inflow":        float,
          "guf_by_parcel_mean":    float,
          "guf_by_parcel_std":     float,
          "psi":                   float,
        }
    """
    variants = weight_variants if weight_variants is not None else _DEFAULT_LVI_VARIANTS

    variant_results = []
    for wt in variants:
        # Build modified parcels with recomputed location_value
        modified: list[dict] = []
        for p in parcel_inventory:
            p2 = dict(p)
            has_sub = _LVI_SUB_KEYS.issubset(p.keys())
            if has_sub:
                p2["location_value"] = location_value_index(
                    centrality=float(p["centrality"]),
                    transit=float(p["transit"]),
                    services=float(p["services"]),
                    natural_amenity=float(p["natural_amenity"]),
                    weights=wt,
                )
            modified.append(p2)

        result = compute_collective_guf(modified, epsilon)
        fees   = [row["guf_applied"] for row in result["guf_by_parcel"]]
        n      = max(len(fees), 1)
        mean   = sum(fees) / n
        std    = (sum((f - mean) ** 2 for f in fees) / n) ** 0.5 if n > 1 else 0.0

        variant_results.append({
            "weights":            dict(wt),
            "guf_aggregate":      result["guf_gross_revenue"],
            "guf_net_inflow":     result["guf_net_inflow"],
            "guf_by_parcel_mean": mean,
            "guf_by_parcel_std":  std,
            "psi":                result["psi"],
        })

    aggregates = [v["guf_aggregate"] for v in variant_results]
    agg_min    = min(aggregates) if aggregates else 0.0
    agg_max    = max(aggregates) if aggregates else 0.0
    agg_mean   = sum(aggregates) / max(len(aggregates), 1)
    rel_sens   = (agg_max - agg_min) / agg_mean if agg_mean > 1e-9 else 0.0

    return {
        "epsilon":              epsilon,
        "parcel_count":         len(parcel_inventory),
        "variants":             variant_results,
        "sensitivity_range":    (agg_min, agg_max),
        "relative_sensitivity": rel_sens,
    }
