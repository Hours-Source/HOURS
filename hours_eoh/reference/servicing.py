"""
The servicing-cost census — what holding land under human use costs in labour.

This is the instrument `GUF_USE_*`'s own `resolves_by` has always named:

    "a stewardship-cost census — collective labour-hours per year actually
     attributable to servicing each use category (roads, utilities, inspection,
     dispute resolution), divided by land area. That measures the quantity the
     fee is DEFINED as, so it settles the levels and the ratios in one
     instrument rather than calibrating one against the other."

It is a DIFFERENT quantity from `reference/land_stewardship.py`, and the two
must not be merged. Stewardship asks what the LAND demands to hold its
condition; servicing asks what the BUILT ENVIRONMENT ON it demands to be
habitable — roads resurfaced, water delivered, sewage carried, buildings
inspected, boundaries adjudicated. The occupational sets are disjoint by
construction (see `DISJOINT_FROM_STEWARDSHIP`).

WHAT IT IS FOR. The ten `GUF_USE_*` coefficients were scaled ×100 from the NLSA
template's abstract values so that aggregate GUF over a 1M-population inventory
would land co-equal with levy revenue at mid-arc. That is a value
reverse-engineered from a desired outcome, and it is tagged `placeholder` on
exactly that ground. This module measures the quantity instead.

STRUCTURE, following the stewardship census's discipline:
  MEASURED   employment by occupation — BLS Employment Projections, via
             reference/data/multiplier_registry_v5.csv (the `ep_employment_k`
             field, 751 occupations, the same file the multiplier uses).
  MEASURED   land area by use class — USDA ERS Major Land Uses 2022, via
             reference/data/mlu_land_use_2022.csv.
  DERIVED    hours per worker-year — scenarios/food_conservation, from ATUS ÷
             registry employment. Not a chosen 2,080.
  ASSUMED    WHICH OCCUPATIONS SERVICE LAND, and WHICH LAND CLASSES ARE
             SERVICED. This is the one judgement, it is isolated in
             `SERVICING_ATTRIBUTIONS` and `SERVICED_LAND_CLASSES`, and it is
             reported under two scopes that are never silently merged.

THE ROLE-MIX TRAP, which this census inherits from the parks finding. Raw
occupational headcount overstated federal stewardship by 4.4× because a park
ranger is largely a visitor-services role. The same hazard is worse here: a
keyword search for "inspector" returns `519061 Inspectors, Testers, Sorters,
Samplers and Weighers` (598.1k), which is manufacturing quality control and has
nothing to do with land. It is EXCLUDED by name, not filtered by a rule, and the
exclusions carry their reasons in `EXCLUDED_OCCUPATIONS`.

Layer: reference/ — pure data, imports nothing from the package.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Mapping, Sequence

from hours_eoh.reference.land_stewardship import land_hectares_by_class

_DATA = Path(__file__).parent / "data"

#: Occupations whose work is UNAMBIGUOUSLY the servicing of land under human
#: use. Each names the function from the `resolves_by` it answers to.
#:
#: The test of membership is definitional, not statistical: would this
#: occupation exist if the land were not held for human use? A highway
#: maintenance worker would not. A lawyer would.
SERVICING_ATTRIBUTIONS: tuple[dict, ...] = (
    {
        "occ6": "474051", "function": "roads",
        "title": "Highway Maintenance Workers",
        "basis": "Defined by SOC as maintaining highways and rights-of-way.",
    },
    {
        "occ6": "472071", "function": "roads",
        "title": "Paving, Surfacing, and Tamping Equipment Operators",
        "basis": "Surfacing is the recurring cost of a road, not its construction.",
    },
    {
        "occ6": "537081", "function": "roads",
        "title": "Refuse and Recyclable Material Collectors",
        "basis": (
            "Collection is a per-parcel municipal service delivered over the "
            "road network; it exists because the land is occupied."
        ),
    },
    {
        "occ6": "518031", "function": "utilities",
        "title": "Water and Wastewater Treatment Plant and System Operators",
        "basis": "Delivery and carriage for occupied parcels.",
    },
    {
        "occ6": "499051", "function": "utilities",
        "title": "Electrical Power-Line Installers and Repairers",
        "basis": "The distribution network exists to reach occupied parcels.",
    },
    {
        "occ6": "474071", "function": "utilities",
        "title": "Septic Tank Servicers and Sewer Pipe Cleaners",
        "basis": "Sewerage service, the non-reticulated and reticulated halves.",
    },
    {
        "occ6": "472151", "function": "utilities",
        "title": "Pipelayers",
        "basis": "Water, sewer and gas reticulation to parcels.",
    },
    {
        "occ6": "435041", "function": "utilities",
        "title": "Meter Readers, Utilities",
        "basis": "Per-parcel measurement; the occupation is defined by the visit.",
    },
    {
        "occ6": "474011", "function": "inspection",
        "title": "Construction and Building Inspectors",
        "basis": (
            "The inspection function named in the resolves_by. Distinct from "
            "519061, which is manufacturing QC — see EXCLUDED_OCCUPATIONS."
        ),
    },
    {
        "occ6": "232093", "function": "dispute_resolution",
        "title": "Title Examiners, Abstractors, and Searchers",
        "basis": (
            "Definitionally land: the occupation exists to establish who holds "
            "which parcel. The narrowest defensible reading of 'dispute "
            "resolution' — it is the only legal occupation whose entire subject "
            "matter is land tenure."
        ),
    },
)

#: Occupations a keyword search surfaces and this census REFUSES, with the
#: reason. Named rather than filtered, because the parks finding showed that a
#: rule which looks right removes the wrong people.
EXCLUDED_OCCUPATIONS: tuple[dict, ...] = (
    {
        "occ6": "519061", "employment_k_approx": 598.1,
        "title": "Inspectors, Testers, Sorters, Samplers, and Weighers",
        "reason": (
            "MANUFACTURING QUALITY CONTROL, not building inspection. Matches any "
            "regex for 'inspect' and would nearly quadruple the inspection "
            "function on its own. The single largest false positive available."
        ),
    },
    {
        "occ6": "231011", "employment_k_approx": 900.7,
        "title": "Lawyers",
        "reason": (
            "Only a fraction of legal work concerns land, and this census has no "
            "role-mix fraction to apply. Including the whole occupation repeats "
            "the raw-agency-headcount error that overstated federal stewardship "
            "4.4×. Available under the `broad` scope at a DECLARED weight."
        ),
    },
    {
        "occ6": "131041", "employment_k_approx": 430.3,
        "title": "Compliance Officers",
        "reason": (
            "Spans environmental, financial, safety and trade compliance. No "
            "land-specific split is derivable from the registry."
        ),
    },
    {
        "occ6": "472073", "employment_k_approx": 507.1,
        "title": "Operating Engineers and Other Construction Equipment Operators",
        "reason": (
            "General construction plant. Construction is the creation of the "
            "built environment, not the recurring cost of holding it — the same "
            "production-versus-condition line that excludes logging from the "
            "forest stewardship attribution."
        ),
    },
)

#: Occupations admitted only under the `broad` scope, each at a DECLARED weight.
#: The precedent is AMENITY_STEWARDSHIP_WEIGHT: where a scope choice is worth a
#: large factor, the weight is named and both corners survive.
BROAD_SCOPE_WEIGHTS: dict[str, float] = {
    "231011": 0.05,   # Lawyers — real-property practice as a share of the bar
    "131041": 0.10,   # Compliance Officers — the building/zoning share
    "499052": 1.00,   # Telecommunications Line Installers — network to parcels
    "492022": 0.50,   # Telecom Equipment Installers — premises half
}

#: Land classes that RECEIVE the servicing this census measures. Under the
#: `core` scope only land whose defining feature is human occupation or the
#: transport network serving it.
SERVICED_LAND_CLASSES: dict[str, tuple[str, ...]] = {
    "core": (
        "Land in urban areas",
        "Land in rural transportation facilities",
    ),
    "broad": (
        "Land in urban areas",
        "Land in rural transportation facilities",
        "Land in defense and industrial areas",
        "Farmsteads, roads, and miscellaneous farmland",
    ),
    # ALL core servicing workers over URBAN LAND ALONE. Deliberately an UPPER
    # BOUND on urban intensity, not an estimate of it: some of these workers
    # serve the rural transport network, and none of them is subtracted here.
    # It exists so the urban archetype can be compared like-for-like — a fee
    # rate realised on urban parcels against a servicing rate measured over
    # urban land — rather than against an average that includes 10.3 Mha of
    # sparsely-serviced highway corridor.
    "urban_upper": (
        "Land in urban areas",
    ),
}

#: The two censuses must not double-count. Asserted in tests rather than
#: assumed: no occupation may appear in both attributions.
DISJOINT_FROM_STEWARDSHIP: str = (
    "Stewardship measures what the LAND demands to hold condition; servicing "
    "measures what the BUILT ENVIRONMENT demands to stay habitable. Groundskeeping "
    "(373011) is stewardship under the amenity scope; highway maintenance (474051) "
    "is servicing. No occupation belongs to both, and a test enforces it."
)


def load_registry_employment() -> dict[str, float]:
    """
    Employment by SOC code, thousands. MEASURED — BLS Employment Projections.

    Reads the same file the multiplier registry uses, so the two cannot drift.
    """
    path = _DATA / "multiplier_registry_v5.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return {
            str(row["occ6"]): float(row["ep_employment_k"])
            for row in csv.DictReader(fh)
            if row.get("ep_employment_k")
        }


def load_land_use() -> dict[str, float]:
    """
    Land area in hectares by ERS use class. MEASURED — USDA ERS MLU 2022.

    Delegates to `land_stewardship.land_hectares_by_class`, which is the single
    loader over this CSV. This module briefly carried its own, and the two
    disagreed on whether the aggregate "Total land" row belongs in a mapping —
    it does not, because summing such a mapping then doubles the area.
    """
    return land_hectares_by_class()


def servicing_workers(
    scope: str = "core",
    employment: Mapping[str, float] | None = None,
) -> dict:
    """
    Workers servicing land, by function.

    Governing sum:

        core  : Σ over SERVICING_ATTRIBUTIONS of employment[occ]
        broad : core + Σ over BROAD_SCOPE_WEIGHTS of weight × employment[occ]

    units: workers (headcount, not thousands).

    Returns a per-function breakdown plus the total, and the list of any
    attributed occupation the registry does not carry — reported, never
    silently dropped.
    """
    if scope not in ("core", "broad", "urban_upper"):
        raise ValueError(
            f"scope must be 'core', 'broad' or 'urban_upper', got {scope!r}"
        )

    emp = load_registry_employment() if employment is None else dict(employment)

    by_function: dict[str, float] = {}
    missing: list[str] = []
    for att in SERVICING_ATTRIBUTIONS:
        occ = att["occ6"]
        if occ not in emp:
            missing.append(occ)
            continue
        by_function[att["function"]] = (
            by_function.get(att["function"], 0.0) + emp[occ] * 1_000.0
        )

    weighted: dict[str, float] = {}
    if scope == "broad":
        for occ, w in BROAD_SCOPE_WEIGHTS.items():
            if occ not in emp:
                missing.append(occ)
                continue
            weighted[occ] = emp[occ] * 1_000.0 * w

    total = sum(by_function.values()) + sum(weighted.values())
    return {
        "scope":            scope,
        "by_function":      by_function,
        "broad_weighted":   weighted,
        "total_workers":    total,
        "missing_from_registry": missing,
    }


def serviced_hectares(scope: str = "core", land_use: Mapping[str, float] | None = None) -> float:
    """Total area receiving the servicing, for the given scope. MEASURED."""
    if scope not in SERVICED_LAND_CLASSES:
        raise ValueError(f"scope must be one of {sorted(SERVICED_LAND_CLASSES)}, got {scope!r}")
    lu = load_land_use() if land_use is None else dict(land_use)
    return sum(lu[name] for name in SERVICED_LAND_CLASSES[scope])
