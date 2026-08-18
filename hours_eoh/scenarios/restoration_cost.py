"""
Phase 3 — what resetting a hectare actually costs in labour, and what it implies.

REPORTING ONLY. No constant moves. `notes/guf-restoration-derivation.md` §Phase 3.

THE RESULT, AND IT CORRECTS AN EARLIER ESTIMATE IN THIS FILE'S OWN LINEAGE
--------------------------------------------------------------------------
The Phase-0 bounding exercise asked what a legacy restoration backlog would
contribute to the ecological domain and used **100 h/ha** as "a plausible
restoration figure (prairie seeding/planting)". Derived from ASAE field capacity
instead of guessed, grassland seeding costs **1.8–4.8 h/ha over its whole
lifetime**, establishment and three years of aftercare included, and
minimum-intervention old-field succession costs **0.9–2.6 h/ha**.

**Across both sequences the guess was 21–115× too high.** The conclusion it
supported — that no basis rebalances the domains — therefore holds *a fortiori*:
the legacy-restoration route is not merely small, it is roughly two orders of
magnitude smaller than a figure that was already too small to matter.

WHY THE GUESS WAS SO FAR OUT, which is the transferable part: **most of a
restoration's DOLLAR cost is not labour.** It is seed, plant material, design,
survey and land acquisition. Reasoning from a remembered cost-per-acre and
converting at some wage silently prices all of that as labour. This is the same
defect that made NRCS EQIP payment schedules unusable — the dollar column mixes
implementation cost with foregone income — and it is why the currency-free route
is the only one that has worked here.

Layer: scenarios/ — imports reference/, core/ and land/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.data import (
    GUF_ECO_KAPPA_CARBON,
    RESTORATION_AMORTIZATION_YEARS,
    RESTORATION_BOUNDING_ASSUMPTION_H_PER_HA,
    GUF_SERVICE_PROFILE_DECLARED,
    US_MAINLAND_HECTARES,
    US_REFERENCE_POPULATION,
)
from hours_eoh.reference.restoration import (
    RESTORATION_SEQUENCES,
    UNPRICED_RESTORATION,
    restoration_hours_per_hectare,
)

#: Re-exported from data.py so callers and tests have one name for each.
BOUNDING_ASSUMPTION_H_PER_HA: float = RESTORATION_BOUNDING_ASSUMPTION_H_PER_HA
DEFAULT_AMORTIZATION_YEARS: float = RESTORATION_AMORTIZATION_YEARS


def restoration_band() -> dict:
    """Every priced sequence, plus the classes the instrument cannot reach."""
    rows = [restoration_hours_per_hectare(s) for s in RESTORATION_SEQUENCES]
    return {
        "sequences": rows,
        "lifetime_low":  min(r["lifetime_h_per_ha_low"] for r in rows),
        "lifetime_high": max(r["lifetime_h_per_ha_high"] for r in rows),
        "unpriced": [
            {"class": u["class"], "reason": u["reason"], "resolves_by": u["resolves_by"]}
            for u in UNPRICED_RESTORATION
        ],
        "priced_count":   len(rows),
        "unpriced_count": len(UNPRICED_RESTORATION),
    }


def legacy_stock(
    restorable_hectares: float = 100e6,
    amortization_years: float = DEFAULT_AMORTIZATION_YEARS,
) -> dict:
    """
    The legacy restoration backlog as an annual obligation, at US scale.

    Governing equation:

        annual_hours = restorable_hectares × lifetime_h_per_ha / horizon

    The area is the CALLER'S, and 100 Mha is the same figure the Phase-0
    bounding used so the two are comparable — roughly the scale of US cropland
    plus degraded rangeland. It is not a measurement of what needs restoring;
    that inventory does not exist here.
    """
    band = restoration_band()
    pop = US_REFERENCE_POPULATION
    out = {
        "restorable_hectares": restorable_hectares,
        "amortization_years":  amortization_years,
        "share_of_us_land":    restorable_hectares / US_MAINLAND_HECTARES,
    }
    for corner in ("low", "high"):
        h_per_ha = band[f"lifetime_{corner}"]
        annual = restorable_hectares * h_per_ha / amortization_years
        out[f"h_per_ha_{corner}"] = h_per_ha
        out[f"annual_hours_{corner}"] = annual
        out[f"h_per_capita_{corner}"] = annual / pop

    assumed = restorable_hectares * BOUNDING_ASSUMPTION_H_PER_HA / amortization_years
    out["bounding_assumption_h_per_ha"] = BOUNDING_ASSUMPTION_H_PER_HA
    out["bounding_h_per_capita"] = assumed / pop
    out["guess_overstated_by_low"] = BOUNDING_ASSUMPTION_H_PER_HA / band["lifetime_high"]
    out["guess_overstated_by_high"] = BOUNDING_ASSUMPTION_H_PER_HA / band["lifetime_low"]
    return out


def implied_kappa(amortization_years: float = DEFAULT_AMORTIZATION_YEARS) -> dict:
    """
    κ implied by restoration cost, against the shipped engineered κ.

    Governing equation:

        κ_implied = (lifetime_h_per_ha / horizon) / V_s_per_hectare_year

    units: labour-hours per unit of service per year — the unit κ is in.

    THE COMPARISON THIS EXISTS FOR. `GUF_ECO_KAPPA_CARBON` = 0.6 h/tonne is an
    ENGINEERED replacement cost, adopted from `CDR_LABOR_HOURS_PER_TONNE`
    (direct-air-capture operator staffing). Restoration is a BIOLOGICAL
    replacement of the same service. If the biological route is far cheaper in
    labour, that is not a discrepancy to reconcile — it is the measurement of
    how much cheaper it is to let a system do the work than to build a machine
    that does it, which is the quantity the whole reframing turns on.

    CONDITIONAL ON V_s, WHICH IS A PLACEHOLDER. The service volumes come from
    `GUF_SERVICE_PROFILE_DECLARED`, order-of-magnitude values that are not a
    measurement of anywhere. The restoration side is physics; the service side
    is not. Read this as a SENSITIVITY with a sound method, never as a result.
    """
    band = restoration_band()
    carbon_per_ha_yr = GUF_SERVICE_PROFILE_DECLARED["carbon"]

    out: dict = {
        "amortization_years": amortization_years,
        "carbon_volume_per_ha_year": carbon_per_ha_yr,
        "shipped_kappa_carbon": GUF_ECO_KAPPA_CARBON,
        "shipped_kappa_basis": (
            "engineered removal — CDR operator staffing, adopted 2026-08-09"
        ),
    }
    for corner in ("low", "high"):
        annualised = band[f"lifetime_{corner}"] / amortization_years
        k = annualised / carbon_per_ha_yr
        out[f"restoration_h_per_ha_year_{corner}"] = annualised
        out[f"implied_kappa_{corner}"] = k
        out[f"shipped_over_implied_{corner}"] = GUF_ECO_KAPPA_CARBON / k
    return out


def restoration_report(
    restorable_hectares: float = 100e6,
    amortization_years: float = DEFAULT_AMORTIZATION_YEARS,
) -> dict:
    """Full Phase 3 report."""
    band = restoration_band()
    stock = legacy_stock(restorable_hectares, amortization_years)
    kappa = implied_kappa(amortization_years)

    return {
        "band":   band,
        "stock":  stock,
        "kappa":  kappa,
        "verdict": (
            f"Restoration costs {band['lifetime_low']:.2f}–"
            f"{band['lifetime_high']:.2f} labour-hours per hectare over its whole "
            f"lifetime, derived from ASAE field capacity with no price in the "
            f"chain. The Phase-0 bounding assumed "
            f"{BOUNDING_ASSUMPTION_H_PER_HA:,.0f} h/ha — the guess was "
            f"{stock['guess_overstated_by_low']:,.0f}–"
            f"{stock['guess_overstated_by_high']:,.0f}× TOO HIGH, and the "
            f"conclusion it supported holds a fortiori. At "
            f"{restorable_hectares / 1e6:,.0f} Mha over "
            f"{amortization_years:,.0f} years the legacy backlog is "
            f"{stock['h_per_capita_low']:.4f}–{stock['h_per_capita_high']:.4f} "
            f"h/person·yr, against a personal obligation of ~1,301. "
            f"Restoration is not where the ecological domain is hiding."
        ),
        "kappa_verdict": (
            f"Restoration implies κ_carbon of "
            f"{kappa['implied_kappa_low']:.4f}–{kappa['implied_kappa_high']:.4f} "
            f"h/tonne against the shipped {GUF_ECO_KAPPA_CARBON} — the "
            f"engineered figure is {kappa['shipped_over_implied_high']:,.0f}–"
            f"{kappa['shipped_over_implied_low']:,.0f}× higher. That gap is not "
            f"an inconsistency to reconcile: it is how much cheaper in LABOUR it "
            f"is to let a biological system deliver the service than to build "
            f"and staff a machine that does. CONDITIONAL on a placeholder V_s — "
            f"the restoration side is physics, the service side is not."
        ),
        "coverage_note": (
            f"{band['priced_count']} sequences priced, {band['unpriced_count']} "
            f"classes EXCLUDED rather than costed at zero: "
            f"{', '.join(u['class'] for u in band['unpriced'])}. Each names what "
            f"would settle it, and each pointer names the FIELD carrying the "
            f"quantity — seedlings per person-day, cubic metres per machine-hour, "
            f"plots per person-day — not merely a source."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 4d — the pristine gap as an annual domain obligation
# ---------------------------------------------------------------------------

def pristine_gap_obligation(
    condition_inventory: list[dict],
    amortization_years: float = DEFAULT_AMORTIZATION_YEARS,
    sequence: str = "grassland_seeding",
    corner: str = "high",
) -> dict:
    """
    The legacy restoration backlog as an annual EOH flow, for the domain.

    Governing equation:

        annual = Σ_c  area_c × deficit_c × lifetime_h_per_ha / horizon

    where `deficit_c` ∈ [0, 1] is how far class c sits below reference
    condition — 0 is at reference and owes nothing, 1 is fully degraded and owes
    a whole restoration.

    units: labour-hours per year. Feeds `ecological_eoh(restoration_obligation=)`,
    which is the STOCK half of the 2026-08-17 partition; the FLOW half is GUF's
    E(p,ε) and is not computed here.

    THE INVENTORY IS THE CALLER'S, AND IT IS THE MISSING QUANTITY. This package
    ships none. Phase 3 measured the cost PER HECTARE RESTORED from ASAE field
    capacity; what this needs is the HECTARES NEEDING RESTORATION AND BY HOW
    MUCH, which is a land-condition survey, not a machinery calculation. Passing
    an invented deficit produces a number with the same standing as a measured
    one and afterwards nothing can tell them apart — so the argument is required
    and there is no default.

    resolves_by: USDA National Resources Inventory. FIELD: the NRI land
    cover/use transition matrices report area moving between condition classes
    on a 5-year cycle, and the Phase-3 sequences are keyed to exactly those
    transitions (cropland → perennial cover, old-field succession). One survey
    supplies both the area and the class, which is what makes it the right
    instrument rather than a source that merely mentions restoration.

    Args:
        condition_inventory: [{"class": str, "hectares": float,
                               "deficit": float ∈ [0,1]}, ...]
        amortization_years:  Horizon over which the backlog is discharged.
        sequence:            Which restoration sequence prices the gap.
        corner:              "low" or "high" band corner of the derived cost.

    Returns:
        dict with the annual obligation, the per-class breakdown, and the
        per-hectare cost it was priced at.
    """
    if corner not in ("low", "high"):
        raise ValueError(f"corner must be 'low' or 'high', got {corner!r}")
    if amortization_years <= 0.0:
        raise ValueError(
            f"amortization_years must be > 0, got {amortization_years}"
        )

    cost = restoration_hours_per_hectare(sequence)[f"lifetime_h_per_ha_{corner}"]

    rows = []
    total = 0.0
    for entry in condition_inventory:
        deficit = entry["deficit"]
        if not 0.0 <= deficit <= 1.0:
            raise ValueError(
                f"deficit must be in [0, 1], got {deficit} for "
                f"{entry.get('class', '?')!r}"
            )
        hectares = entry["hectares"]
        if hectares < 0.0:
            raise ValueError(f"hectares must be >= 0, got {hectares}")
        annual = hectares * deficit * cost / amortization_years
        rows.append({
            "class":            entry.get("class", "unnamed"),
            "hectares":         hectares,
            "deficit":          deficit,
            "annual_hours":     annual,
        })
        total += annual

    return {
        "annual_hours":            total,
        "by_class":                rows,
        "lifetime_h_per_ha":       cost,
        "sequence":                sequence,
        "corner":                  corner,
        "amortization_years":      amortization_years,
        "inventory_is_supplied":   True,
        "note": (
            "STOCK half of the pristine/current partition. The FLOW half — "
            "holding land at its current condition — is GUF's E(p,ε) and is not "
            "computed here. The condition inventory is the caller's; this "
            "package ships none, and the deficit is the quantity a land-condition "
            "survey settles."
        ),
    }
