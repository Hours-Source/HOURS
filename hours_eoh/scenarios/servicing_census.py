"""
Phase 2 — the ×100 use-coefficient fit, measured against what it is defined as.

REPORTING ONLY. No constant moves here. This runs the instrument `GUF_USE_*`'s
own `resolves_by` has always named and reports how far the shipped values sit
from it.

THE THING BEING TESTED
----------------------
The ten `GUF_USE_*` coefficients were scaled ×100 from the NLSA template's
abstract values so that aggregate GUF over a 1M-population inventory would land
co-equal with levy revenue at mid-arc. Their own tag block says so, and tags
them `placeholder` on that ground: a value reverse-engineered from a desired
outcome is CHOSEN, whatever the ratios between categories rest on.

Two things follow that the fit cannot distinguish, and this census can:

  LEVEL   — is the ×100 the right magnitude at all?
  RATIOS  — is residential 10.0 against industrial_heavy 37.5 the right SHAPE?

Calibrating one aggregate against another cannot settle either, because a single
scalar k has one degree of freedom and the coefficient table has ten.

WHAT THIS DOES NOT SETTLE
-------------------------
The census is an AGGREGATE: total servicing hours over total serviced area. It
gives a level, and it does NOT give the ten ratios — no measured split of
servicing labour by use category exists in the registry, because occupational
data is not coded by the land use it serves. So this closes the level question
and leaves the shape question open, which is the honest half-answer rather than
a fitted whole one.

Note also that Phase 1b already established the ×100 is NOT wrong because the
ecological term was missing: switching E on moves the calibrated multiplier by
at most 0.017%. Whatever this census finds is therefore about `base_fee`
alone.

Layer: scenarios/ — imports core/, land/ and reference/; imported by neither.
"""

from __future__ import annotations

from hours_eoh.data import GUF_USE_SCALE_FACTOR, SLU_HECTARES
from hours_eoh.land.guf import USE_CATEGORIES
from hours_eoh.reference import servicing
from hours_eoh.scenarios.food_conservation import hours_per_worker_year

#: Re-exported from data.py so callers and tests have one name for it.
SHIPPED_SCALE_FACTOR: float = GUF_USE_SCALE_FACTOR


def census(scope: str = "core") -> dict:
    """
    Measured servicing intensity over serviced land.

    Governing equation:

        h_per_ha = (workers × hours_per_worker_year) / serviced_hectares
        teh_per_slu = h_per_ha × SLU_HECTARES

    units: labour-hours per hectare per year, and TEH per SLU per year — the
    unit `GUF_USE_*` is denominated in.

    Every input is measured or derived; the one judgement is which occupations
    service land and which land classes receive it, isolated in
    reference/servicing.py and reported under two scopes.
    """
    workers = servicing.servicing_workers(scope)
    hectares = servicing.serviced_hectares(scope)
    h_worker = hours_per_worker_year()

    total_hours = workers["total_workers"] * h_worker
    h_per_ha = total_hours / hectares
    return {
        "scope":              scope,
        "workers":            workers["total_workers"],
        "by_function":        workers["by_function"],
        "hours_per_worker_year": h_worker,
        "total_hours":        total_hours,
        "serviced_hectares":  hectares,
        "hours_per_hectare_year": h_per_ha,
        "teh_per_slu_year":   h_per_ha * SLU_HECTARES,
        "missing_from_registry": workers["missing_from_registry"],
    }


def shipped_vs_measured(scope: str = "core") -> dict:
    """
    The shipped `GUF_USE_*` coefficients against the measured servicing rate.

    The census is an aggregate, so it is compared against the
    EMPLOYMENT-WEIGHTED-EQUIVALENT of the table — here the simple mean of the
    positive coefficients, plus the residential value on its own since it is the
    category the overwhelming majority of parcels carry.

    `implied_scale_factor` is the headline: the factor the template's abstract
    values would need, in place of the shipped ×100, for the table's level to
    match the census.
    """
    c = census(scope)
    measured_teh_per_slu = c["teh_per_slu_year"]

    positive = {k: v for k, v in USE_CATEGORIES.items() if v > 0.0}
    mean_coeff = sum(positive.values()) / len(positive)
    residential = USE_CATEGORIES["residential_primary"]

    # The template value each shipped coefficient came from.
    template_mean = mean_coeff / SHIPPED_SCALE_FACTOR
    implied_scale = measured_teh_per_slu / template_mean

    return {
        "scope":                    scope,
        "measured_teh_per_slu":     measured_teh_per_slu,
        "measured_h_per_ha":        c["hours_per_hectare_year"],
        "shipped_mean_coefficient": mean_coeff,
        "shipped_residential":      residential,
        "shipped_over_measured_mean":        mean_coeff / measured_teh_per_slu,
        "shipped_over_measured_residential": residential / measured_teh_per_slu,
        "shipped_scale_factor":     SHIPPED_SCALE_FACTOR,
        "implied_scale_factor":     implied_scale,
        "overshoot_factor":         SHIPPED_SCALE_FACTOR / implied_scale,
    }


def realized_vs_measured(epsilon: float = 0.40) -> dict:
    """
    What the shipped table actually CHARGES per hectare, against what servicing
    that land actually COSTS per hectare.

    This is the like-for-like test, and a sharper one than comparing the raw
    coefficients: the realised rate carries L(p), D(p), Z(p) and Ψ(ε) as well as
    U, so it is the fee a holder really pays.

        realised = compute_collective_guf(archetype, ε) / total hectares
        measured = the census over the land class that archetype occupies

    Urban is compared against `urban_upper` — every core servicing worker
    charged to urban land alone — so the comparison errs AGAINST the finding:
    the true urban servicing rate is lower than 63.7 h/ha·yr, which makes the
    overshoot larger, not smaller.
    """
    from hours_eoh.land.collective import (
        compute_collective_guf,
        make_rural_collective,
        make_urban_collective,
    )

    rows = []
    for name, factory, count, scope in (
        ("urban", make_urban_collective, 10_000, "urban_upper"),
        ("rural", make_rural_collective, 1_000, "core"),
    ):
        parcels = factory(count)
        hectares = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
        guf = compute_collective_guf(parcels, epsilon)["guf_gross_revenue"]
        realised = guf / hectares
        measured = census(scope)["hours_per_hectare_year"]
        rows.append({
            "archetype":        name,
            "hectares":         hectares,
            "guf_teh_per_year": guf,
            "realised_h_per_ha": realised,
            "compared_against": scope,
            "measured_h_per_ha": measured,
            "ratio":            realised / measured,
        })

    by = {r["archetype"]: r for r in rows}
    return {
        "epsilon": epsilon,
        "rows":    rows,
        "verdict": (
            f"THE ×100 IS NOT UNIFORMLY WRONG. The rural archetype realises "
            f"{by['rural']['realised_h_per_ha']:,.1f} h/ha·yr against a measured "
            f"{by['rural']['measured_h_per_ha']:,.1f} — a factor of "
            f"{by['rural']['ratio']:.2f}, essentially on the census. The urban "
            f"archetype realises {by['urban']['realised_h_per_ha']:,.1f} against "
            f"{by['urban']['measured_h_per_ha']:,.1f} — a factor of "
            f"{by['urban']['ratio']:,.1f}×, and that comparison already errs "
            f"against the finding because every servicing worker was charged to "
            f"urban land alone. So the fit did not get the LEVEL wrong so much "
            f"as the DENSITY GRADIENT: the fee is per-SLU, so packing the same "
            f"hectare with more parcels multiplies the charge while the roads, "
            f"pipes and inspections serving that hectare do not multiply with "
            f"it. Retiring the ×100 is therefore not a single rescaling."
        ),
    }


def census_report(scope: str = "core") -> dict:
    """Full Phase 2 report: the census, the comparison, and what it cannot settle."""
    c = census(scope)
    cmp_ = shipped_vs_measured(scope)
    other = "broad" if scope == "core" else "core"
    cmp_other = shipped_vs_measured(other)

    return {
        **c,
        **{k: v for k, v in cmp_.items() if k != "scope"},
        "scope_alternative":            other,
        "alternative_h_per_ha":         cmp_other["measured_h_per_ha"],
        "scope_spread_factor":          max(
            cmp_["measured_h_per_ha"], cmp_other["measured_h_per_ha"]
        ) / min(cmp_["measured_h_per_ha"], cmp_other["measured_h_per_ha"]),
        "verdict": (
            f"scope={scope}: measured servicing intensity is "
            f"{c['hours_per_hectare_year']:,.1f} h/ha·yr "
            f"({cmp_['measured_teh_per_slu']:.4f} TEH/SLU·yr) over "
            f"{c['serviced_hectares'] / 1e6:.1f} Mha, from "
            f"{c['workers'] / 1e3:,.0f}k workers. The shipped table's mean "
            f"positive coefficient is {cmp_['shipped_mean_coefficient']:.2f} "
            f"TEH/SLU·yr — {cmp_['shipped_over_measured_mean']:,.1f}× the "
            f"measured rate — and residential_primary alone is "
            f"{cmp_['shipped_over_measured_residential']:,.1f}×. The ×100 "
            f"therefore OVERSHOOTS by about {cmp_['overshoot_factor']:,.0f}×: "
            f"the census implies ×{cmp_['implied_scale_factor']:,.1f} on the "
            f"template's abstract values, not ×100."
        ),
        "realized": realized_vs_measured(),
        "what_this_does_not_settle": (
            "The RATIOS. This is an aggregate — total servicing hours over total "
            "serviced area — and occupational data is not coded by the land use "
            "it serves, so no measured split across the ten use categories "
            "exists. The level question closes; the shape question "
            "(residential 10.0 against industrial_heavy 37.5) does not, and a "
            "single scalar fitted to an aggregate never could settle it: one "
            "degree of freedom against ten coefficients."
        ),
    }
