"""
The land census and the stewardship workforce that tends it — US, measured.

`ECOLOGICAL_BASE_RATE` is a RELATIVE anchor that `total_eoh()` sums with absolute
counts. Its `resolves_by` names the instrument that would settle it:

    "a stewardship-hours census on an absolute footing — **agency FTEs per
     hectare**, or the GUF parcel inventory × measured crew-hours"

The first of those is reachable from data this repo already ships. This module
assembles it: measured land area by use class, measured employment by stewardship
occupation, and the repo's own derived work-year. Read with
`scenarios.land_stewardship`, which builds the census and runs it through
`core.eoh_generation.ecological_statutory_floor`.

WHAT IS MEASURED, AND WHAT IS ASSUMED
--------------------------------------
Three measured inputs, one assumed mapping. The distinction is the whole point,
because the assumption is the weak link and it must not be able to hide inside a
number that looks measured:

  MEASURED  land area by use class — USDA ERS Major Land Uses, U.S. total, 2022
            (released 2026-08-14). Nine classes that partition total land exactly.
  MEASURED  employment by occupation — BLS Employment Projections, via this
            repo's own `multiplier_registry_v5.csv`, frozen epoch 2026-07-29.
  DERIVED   hours per worker-year — `scenarios.food_conservation
            .hours_per_worker_year()`, ≈1,874 h, itself ATUS ÷ registry
            employment. Not a chosen 2,080.
  ASSUMED   which occupations steward which land class. THIS IS NOT MEASURED.
            OEWS/EP classify by what a worker does, not by the land they stand
            on, and no public crosswalk assigns an occupation to a land-use
            class. Every attribution below is a stated judgement, carries a
            `basis`, and is the first thing to attack.

THE HELD-OUT OCCUPATIONS, AND WHY THE ERROR RUNS LOW
-----------------------------------------------------
Three sizeable occupations that plainly do stewardship work are attributed to NO
land class and contribute nothing: Conservation Scientists (29.5k), First-Line
Supervisors of Farming/Fishing/Forestry (67.0k), and Soil and Plant Scientists
(21.8k). Each spans several land classes, or spans land and water, and splitting
them would mean inventing the split. Holding them out understates the floor.

That is the safe direction here and it is worth being explicit about why. The
open question is whether the anchor is low by two to three orders of magnitude.
A floor that errs LOW makes the gap look SMALLER than it is, so it cannot
manufacture the finding it is being used to test. An attribution that erred high
could.

THE SCOPE QUESTION THAT DECIDES THE ANSWER
-------------------------------------------
Landscaping and Groundskeeping Workers is 1,235k people — fifty times the entire
forest and conservation workforce — on 2.9% of the land. Whether that labour is
"ecological stewardship" is a genuine and unresolved question:

  FOR    the framework defines ecological EOH as the labour land demands to hold
         condition, and urban vegetation demands exactly that; it is also the
         land class where the demand is least deferrable.
  AGAINST the condition being held is amenity, not ecosystem function. Mowing a
         corporate lawn on a fortnightly cycle maintains an appearance standard.
         Counting it makes the ecological domain largely a grounds-maintenance
         account.

This module does not adjudicate. `STEWARDSHIP_ATTRIBUTIONS` marks the class
`amenity=True` and the scenario layer reports the census BOTH ways. The choice
is worth 510× per hectare (92.9 h/ha·yr on urban land against 0.18 on forest)
and 50× on the area-weighted mean over priced land. A single number would
conceal a definitional disagreement of that size.

JURISDICTION
------------
US only, and not incidentally. Land-use composition, mechanisation, and public
land-management staffing all differ enough between jurisdictions that these
intensities do not transfer. Stated as `JURISDICTION` for the same reason
`personal_basket.LSMS_AGRO_ECOLOGY` states its agro-ecology: the number's scope
is a property of the number, not a caveat that can be separated from it.

Layer rule: `reference/` imports nothing from the package — these are data, and
any layer may read them.

Source (reproduce the extract):
    https://www.ers.usda.gov/data-products/major-land-uses
    → "All data in CSV" → filter Regions_and_States == "U.S. total", YEAR == 2022,
      keep the nine partition classes below, acres × 0.40468564224 → hectares.

Reference: `data.ECOLOGICAL_BASE_RATE` resolves_by; reconciliation §9 (domain
balance); the infrastructure floor's determinacy result.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

#: Where these numbers apply. Not a caveat — a bound on the quantity.
JURISDICTION: str = (
    "United States, all 50 states, land-use composition as of 2022 and "
    "workforce as of the BLS EP epoch 2026-07-29"
)

#: International acre → hectare, exact.
ACRE_HECTARES: float = 0.40468564224

_DATA = Path(__file__).parent / "data" / "mlu_land_use_2022.csv"

#: The MLU class that is the total, not a partition member.
_TOTAL_CLASS = "Total land"


def load_land_use() -> list[dict]:
    """
    US land area by major use class, in hectares.

    units: hectares. The nine returned classes PARTITION total land exactly —
    verified in `tests`, because MLU also publishes aggregates ("All special
    uses") and cropland subdivisions that would double-count if mixed in.

    Worked example: forest-use land is 617,958 thousand acres → 250,078,730 ha,
    27.3% of the 915,052,512 ha US total.
    """
    with _DATA.open() as fh:
        rows = [
            {
                "land_use": r["land_use"],
                "area_hectares": float(r["area_hectares"]),
                "area_kacres": float(r["area_kacres"]),
                "year": int(r["year"]),
                "source": r["source"],
            }
            for r in csv.DictReader(fh)
        ]
    return [r for r in rows if r["land_use"] != _TOTAL_CLASS]


def total_land_hectares() -> float:
    """Total US land area, hectares. The census denominator."""
    with _DATA.open() as fh:
        for r in csv.DictReader(fh):
            if r["land_use"] == _TOTAL_CLASS:
                return float(r["area_hectares"])
    raise ValueError(f"{_DATA} has no '{_TOTAL_CLASS}' row")


# ---------------------------------------------------------------------------
# The attribution — ASSUMED, not measured. Attack this first.
# ---------------------------------------------------------------------------

#: SOC codes as they appear in `multiplier_registry_v5.csv` (unhyphenated).
#: Employment is read from the registry at run time rather than copied here, so
#: the two cannot drift — the `personal_basket` mirroring lesson.
STEWARDSHIP_ATTRIBUTIONS: tuple[dict, ...] = (
    {
        "land_use": "Forest-use land (all)",
        "occupations": ("454011", "191032"),
        "amenity": False,
        "basis": (
            "Forest and Conservation Workers (454011) and Foresters (191032) are "
            "defined by SOC as working forest and conservation land. Logging "
            "occupations (454021/22/23) are DELIBERATELY EXCLUDED: extraction is "
            "production, not the labour the land demands to hold condition."
        ),
    },
    {
        "land_use": "Land in urban areas",
        "occupations": ("373011", "373013", "373012"),
        "amenity": True,
        "basis": (
            "Landscaping and Groundskeeping (373011), Tree Trimmers and Pruners "
            "(373013) and Vegetation Pesticide Handlers (373012) work managed "
            "vegetation, which is overwhelmingly urban and suburban. SCOPE-"
            "CONTESTED: the condition being held is largely amenity rather than "
            "ecosystem function. Reported separately, never silently merged."
        ),
    },
)

#: Land classes whose attribution is COMPLETE — the occupations named are, as far
#: as the occupational data resolves, the whole stewardship workforce for that
#: class. Only a complete class may be priced.
#:
#: THE COVERAGE-INFLATION TRAP. `ecological_statutory_floor`'s priced/unpriced
#: split is BINARY: a class priced with a fraction of its true labour reads as
#: fully priced and inflates `coverage`. Allocating advisory hours onto cropland
#: would mark 152.7 Mha priced at 0.083 h/ha·yr — coverage 0.303 → 0.470 while
#: the mean FALLS, because the real quantity there is the EQIP practice hours
#: nobody has measured. Partial contributions to an incomplete class are
#: therefore reported and EXCLUDED, never merged into the floor.
COMPLETE_ATTRIBUTIONS: frozenset[str] = frozenset({
    "Forest-use land (all)",
    "Land in urban areas",
})

#: Occupations that do stewardship work and are attributed to NO land class by
#: default, with the reason. Their omission is what makes the floor err LOW.
#: `ALLOCATION_POLICIES` can bring them in — see `derive_allocations`.
HELD_OUT_OCCUPATIONS: tuple[dict, ...] = (
    {
        "occ6": "191031",
        "title": "Conservation Scientists",
        "reason": (
            "advisory work spanning cropland, rangeland and forest; no public "
            "basis for splitting them, and inventing one would put an assumed "
            "number where a measured one appears to be"
        ),
    },
    {
        "occ6": "451011",
        "title": "First-Line Supervisors of Farming, Fishing, and Forestry",
        "reason": "spans land and water; the fishing share is not land stewardship at all",
    },
    {
        "occ6": "191013",
        "title": "Soil and Plant Scientists",
        "reason": "research and laboratory work, not field stewardship of a specific parcel",
    },
)

#: What would narrow `AGENCY_STEWARDSHIP_ROLE_MIX`'s band. The band exists
#: because two large series are genuinely split; closing it is a measurement,
#: not an argument.
AGENCY_ROLE_MIX_RESOLVES_BY: str = (
    "a task decomposition inside series 0025 (park ranger, 3,991 NPS staff) and "
    "0456 (wildland fire) — the share of hours spent on resource condition "
    "rather than visitors and emergency response. NPS budget justifications "
    "report FTE by activity (Resource Stewardship vs Visitor Services vs "
    "Facility Operations) and are the direct instrument. NOTE the ROLE MIX "
    "ITSELF IS NOW MEASURED: the earlier blocker was the OPM Federal Workforce "
    "Data endpoint, and the failure was a wrong call shape — data.opm.gov/api/"
    "v1/files needs the dataset segment (/employment) plus year/month/version, "
    "not the bare path. The bare path 404s and that was read as an inaccessible "
    "API."
)

#: The parks-and-wildlife MLU class, split by whether a workforce exists for it.
#: Federal NPS+FWS land is now priceable; state parks and the remainder are not,
#: because state-agency staffing is outside the federal workforce data. Splitting
#: is what lets the measured two-thirds be priced without the unmeasured third
#: inheriting its intensity.
PARKS_CLASS: str = "Land in rural parks and wildlife areas"
PARKS_FEDERAL: str = "Rural parks and wildlife — federal (NPS + FWS)"
PARKS_OTHER: str = "Rural parks and wildlife — state and other"


#: Land classes with no costed stewardship path, and why. These are returned to
#: the floor with `hours_per_hectare_year=None` so they are EXCLUDED rather than
#: costed at zero — the load-bearing behaviour `ecological_statutory_floor` and
#: `personal_statutory_floor` share.
UNPRICED_REASONS: dict[str, str] = {
    "Total cropland": (
        "unmeasured — no OEWS/EP occupation separates conservation-practice "
        "labour from crop production labour, and the instrument this reason "
        "USED to name does not work: NRCS EQIP payment schedules carry no time "
        "unit and no labour line, and their dollar column mixes implementation "
        "cost with foregone income (EQIP_HAS_NO_LABOUR_LINE, checked against PA "
        "FY2026). Resolves via CROPLAND_HOURS_RESOLVES_BY — extension "
        "enterprise budgets, which record hours because a farm planner needs "
        "hours."
    ),
    "Grassland pasture and range": (
        "unmeasured — as cropland: rangeland stewardship is not separable from "
        "livestock husbandry in the occupational data, and the EQIP schedule "
        "prices grazing practices in dollars per acre with labour bundled in "
        "(practice 528 Grazing Management, 9 base scenarios, all $/Ac). "
        "Resolves via CROPLAND_HOURS_RESOLVES_BY."
    ),
    PARKS_OTHER: (
        "unmeasured — state parks and other non-federal holdings, 35.98 Mha. "
        "State-agency staffing is outside the OPM federal workforce data, so "
        "there is no headcount to apply. The federal two-thirds of this class "
        "IS priced (see PARKS_FEDERAL); splitting is what stops this third "
        "inheriting the measured part's intensity. Resolves via NASPD's annual "
        "state-park operating statistics, which report staffing by state."
    ),
    "Land in rural transportation facilities": (
        "unmeasured — roadside vegetation management is real stewardship labour "
        "but sits inside state DOT maintenance budgets, the same instrument the "
        "infrastructure floor's `resolves_by` already names."
    ),
    "Land in defense and industrial areas": (
        "unmeasured — DoD natural-resource management staffing is published per "
        "installation but not aggregated."
    ),
    "Farmsteads, roads, and miscellaneous farmland": (
        "unmeasured — no instrument isolates it from farm operations generally."
    ),
    "Miscellaneous other land": (
        "no costed path — desert, tundra, barren rock and unmanaged wetland. "
        "Some of this land genuinely demands no stewardship labour and some is "
        "wilderness under active management; the census cannot tell them apart, "
        "so it declines to price either. NOT zero: 90.6 Mha are owed and "
        "unquantified."
    ),
}


# ---------------------------------------------------------------------------
# Allocation — bringing the held-out occupations in at a WEIGHT, not a flag
# ---------------------------------------------------------------------------

#: How much of each held-out occupation lands on stewarded ground. Named
#: policies rather than a fitted weight, for the reason `reference.care_demand`
#: gives for the rivalry exponent ρ: the quantity is NOT IDENTIFIED, so callers
#: should read the CORNERS rather than substitute a value in the middle.
#:
#:   held_out  the three contribute nothing (the shipped default, errs LOW)
#:   derived   only what can actually be derived: the supervisory chain below
#:   area      derived, plus advisory occupations spread by land area (the
#:             upper corner — area is a neutral allocator, not a measured one)
ALLOCATION_POLICIES: tuple[str, ...] = ("held_out", "derived", "area")

#: Supervisees of `451011`, by sub-domain. Supervisors are allocated in
#: proportion to the headcount they supervise — a DERIVED split, not a guess,
#: because the registry carries every supervisee occupation.
SUPERVISEE_GROUPS: dict[str, tuple[str, ...]] = {
    "farming": ("452011", "452021", "452041", "452091", "452092", "452093"),
    "fishing": ("453031",),
    "forestry": ("454011", "454021", "454022", "454023"),
}

#: Within forestry, the occupations that are STEWARDSHIP rather than extraction.
#: The same exclusion `STEWARDSHIP_ATTRIBUTIONS` applies to the workers is
#: applied to the share of supervisors attributed to them.
FORESTRY_STEWARDSHIP_OCCUPATIONS: tuple[str, ...] = ("454011",)

#: Land classes an advisory occupation could plausibly serve, for the `area`
#: policy. Area-proportional is a NEUTRAL allocator, not a measured one: advisory
#: intensity per hectare is certainly higher on cropland than on wilderness, and
#: nothing here measures that. It is the upper corner, and it is labelled as one.
ADVISORY_LAND_CLASSES: tuple[str, ...] = (
    "Total cropland",
    "Grassland pasture and range",
    "Forest-use land (all)",
)

#: Occupations allocated by the `area` policy only.
ADVISORY_OCCUPATIONS: tuple[str, ...] = ("191031",)


def derive_allocations(
    registry_rows: Sequence[Mapping[str, Any]],
    policy: str = "held_out",
) -> dict[str, dict[str, float]]:
    """
    Extra workers per land class from the held-out occupations, by policy.

    Governing derivations:

        supervisors(forestry) = E(451011) · [Σ forestry supervisees / Σ all
                                supervisees] · [E(454011) / Σ forestry]

        advisory(class)       = E(191031) · area(class) / Σ area(advisory classes)

    The first is DERIVED — every term is registry employment. The second is a
    neutral area split and is the upper corner, not a measurement.

    units: workers (headcount, not thousands).

    Worked example (`derived`): 67,000 supervisors × 5.6% forestry × 20.4%
    stewardship-within-forestry = **764 workers**, against the 67,000 that
    including them naively would have added. Holding them out was very nearly
    right, and now that is shown rather than assumed.

    Returns:
        {land_use: {occ6: workers}}. Empty under the `held_out` policy.

    Raises:
        ValueError: on an unknown policy.
    """
    if policy not in ALLOCATION_POLICIES:
        raise ValueError(f"policy must be one of {ALLOCATION_POLICIES}, got {policy!r}")
    if policy == "held_out":
        return {}

    emp = {str(r["occ6"]): float(r["employment_k"]) for r in registry_rows}
    out: dict[str, dict[str, float]] = {}

    # Supervisory chain — derivable in full.
    group_totals = {
        g: sum(emp[o] for o in occs if o in emp)
        for g, occs in SUPERVISEE_GROUPS.items()
    }
    all_supervisees = sum(group_totals.values())
    forestry_total = group_totals["forestry"]
    if all_supervisees > 0.0 and forestry_total > 0.0:
        stewardship_within = (
            sum(emp[o] for o in FORESTRY_STEWARDSHIP_OCCUPATIONS if o in emp)
            / forestry_total
        )
        workers = (
            emp.get("451011", 0.0)
            * (forestry_total / all_supervisees)
            * stewardship_within
            * 1000.0
        )
        out.setdefault("Forest-use land (all)", {})["451011"] = workers

    if policy == "area":
        # Advisory occupations, spread by area. Contributions landing on an
        # INCOMPLETE class are still emitted — the scenario layer reports them
        # and refuses to let them price the class. See COMPLETE_ATTRIBUTIONS.
        areas = {c["land_use"]: c["area_hectares"] for c in load_land_use()}
        total = sum(areas[c] for c in ADVISORY_LAND_CLASSES)
        for occ in ADVISORY_OCCUPATIONS:
            for cls in ADVISORY_LAND_CLASSES:
                out.setdefault(cls, {})[occ] = (
                    emp.get(occ, 0.0) * 1000.0 * areas[cls] / total
                )

    return out


# ---------------------------------------------------------------------------
# Agency land stewards — the parks-and-wildlife intake, NOT yet priceable
# ---------------------------------------------------------------------------

#: Occupational series whose work IS maintaining the condition of land or
#: ecosystem. The same rule as the amenity split, applied to federal series.
AGENCY_STEWARDSHIP_SERIES: frozenset[str] = frozenset({
    "0401",  # general natural resources management and biological sciences
    "0403", "0404", "0405",  # biological science / technician
    "0408",  # ecology
    "0430",  # botany
    "0454",  # rangeland management
    "0457",  # soil conservation
    "0460", "0462",  # forestry, forestry technician
    "0470", "0471",  # soil science, agronomy
    "0482",  # fish biology
    "0485",  # wildlife refuge management
    "0486", "0487",  # wildlife biology, animal science
    "0499",  # biological science student trainee
    "1315",  # hydrology
})

#: Series that are genuinely split between stewardship and something else. They
#: are the DIFFERENCE between the two ends of `AGENCY_STEWARDSHIP_ROLE_MIX`'s
#: band, and naming them is what makes the band reviewable.
AGENCY_AMBIGUOUS_SERIES: frozenset[str] = frozenset({
    "0456",  # wildland fire — fuels treatment and prescribed burn vs response
    "0025",  # park ranger — resource protection vs interpretation
})

#: Federal land-managing agencies whose staff tend the parks-and-wildlife class.
#: Headcounts are EXACT, from record-level OPM Federal Workforce Data; areas are
#: agency round numbers and remain the weaker half of each ratio.
AGENCY_LAND_STEWARDS: tuple[dict, ...] = (
    {
        "agency": "NPS",
        "name": "National Park Service",
        "hectares": 85_000_000.0 * ACRE_HECTARES,
        "hectares_are_rounded": True,
        "area_source": (
            "nps.gov/aboutus/faqs.htm — '433 areas covering more than 85 million "
            "acres'. Retrieved 2026-08-16."
        ),
        "note": (
            "Acreage spans all 50 states plus DC and the territories while the "
            "MLU census covers the 50 states, a small over-count. The larger "
            "distortion is Alaska, which holds a majority of NPS acreage and a "
            "small minority of its staff, so one national intensity averages two "
            "very different regimes."
        ),
    },
    {
        "agency": "FWS",
        "name": "Fish and Wildlife Service — National Wildlife Refuge System",
        "hectares": 92_000_000.0 * ACRE_HECTARES,
        "hectares_are_rounded": True,
        "area_source": (
            "fws.gov/program/national-wildlife-refuge-system — 'more than 92 "
            "million acres, or over 95% of National Wildlife Refuge System "
            "lands'. Retrieved 2026-08-16."
        ),
        "note": (
            "Refuge acreage is majority-Alaska (Arctic, Yukon Delta, Alaska "
            "Maritime), so the same regime-averaging caveat applies, more "
            "strongly. Refuge area also includes water."
        ),
    },
)

_FEDSCOPE = Path(__file__).parent / "data" / "fedscope_land_agency_2025.csv"


def load_agency_workforce() -> list[dict]:
    """
    Federal land-agency headcount by occupational series — record-level, exact.

    units: workers (headcount at the 2025-09 snapshot).

    Source: OPM Federal Workforce Data, employment 2025-09 v3, pulled from
    `data.opm.gov/api/v1/files/employment/2025/09/3/download`. 337 series across
    NPS (19,315) and FWS (7,789). The FAQ figure this replaces was
    "approximately 20,000" for NPS alone; this is the exact count, by series,
    which is what makes the role mix computable at all.
    """
    with _FEDSCOPE.open() as fh:
        return [
            {
                "agency": r["agency"],
                "series_code": r["series_code"],
                "series_name": r["series_name"],
                "headcount": int(r["headcount"]),
            }
            for r in csv.DictReader(fh)
        ]


def agency_role_mix() -> dict:
    """
    The share of each agency's staff whose work maintains land condition.

    Governing equation, per agency:

        low  = Σ headcount(series ∈ STEWARDSHIP) / Σ headcount
        high = Σ headcount(series ∈ STEWARDSHIP ∪ AMBIGUOUS) / Σ headcount

    units: dimensionless fraction.

    Worked example: NPS 1,955 / 19,315 = 0.1012 low, 6,338 / 19,315 = 0.3281
    high — the gap is almost entirely series 0025, 3,991 park rangers who do
    resource protection and interpretation both. FWS reads 0.5364 / 0.6037.

    Returns:
        {agency: {"low", "high", "total", "stewardship", "ambiguous"}} plus a
        "combined" entry over both agencies.
    """
    rows = load_agency_workforce()
    out: dict[str, dict] = {}
    for agency in {r["agency"] for r in rows}:
        rs = [r for r in rows if r["agency"] == agency]
        total = sum(r["headcount"] for r in rs)
        core = sum(
            r["headcount"] for r in rs
            if r["series_code"] in AGENCY_STEWARDSHIP_SERIES
        )
        amb = sum(
            r["headcount"] for r in rs
            if r["series_code"] in AGENCY_AMBIGUOUS_SERIES
        )
        out[agency] = {
            "total": total,
            "stewardship": core,
            "ambiguous": amb,
            "low": core / total if total else 0.0,
            "high": (core + amb) / total if total else 0.0,
        }

    total = sum(v["total"] for v in out.values())
    core = sum(v["stewardship"] for v in out.values())
    amb = sum(v["ambiguous"] for v in out.values())
    out["combined"] = {
        "total": total,
        "stewardship": core,
        "ambiguous": amb,
        "low": core / total if total else 0.0,
        "high": (core + amb) / total if total else 0.0,
    }
    return out




def parks_split() -> list[dict]:
    """
    Split the parks class into the federally-staffed part and the rest.

    units: hectares.

    Worked example: NPS 34.40 Mha + FWS 37.23 Mha = 71.63 Mha of the class's
    107.60 Mha — 66.6%. The remaining 35.98 Mha is state parks and other
    holdings whose workforce is not in the federal data, and it stays unpriced.

    Raises:
        ValueError: if the agencies' claimed area exceeds the census class,
            which would mean the acreages and the MLU class have drifted apart.
    """
    total = next(
        c["area_hectares"] for c in load_land_use() if c["land_use"] == PARKS_CLASS
    )
    federal = sum(a["hectares"] for a in AGENCY_LAND_STEWARDS)
    if federal > total:
        raise ValueError(
            f"federal land-agency area {federal:,.0f} ha exceeds the MLU parks "
            f"class {total:,.0f} ha — the acreages and the census have drifted"
        )
    return [
        {"land_use": PARKS_FEDERAL, "area_hectares": federal},
        {"land_use": PARKS_OTHER, "area_hectares": total - federal},
    ]


# ---------------------------------------------------------------------------
# NRCS EQIP — THE INSTRUMENT THE resolves_by NAMED, AND WHY IT DOES NOT WORK
# ---------------------------------------------------------------------------

#: THE EQIP PAYMENT SCHEDULE DOES NOT ITEMISE LABOUR. This is a negative result
#: and it corrects a claim made in two places: the eco_eoh handoff (§2, "per-acre
#: cost by practice, labour broken out, republished annually by state") and this
#: module's own earlier `UNPRICED_REASONS` entry for cropland, which promised
#: EQIP schedules "itemise labour per acre per practice".
#:
#: Checked against Pennsylvania EQIP-1 FY2026, 2,691 rows, 210 practices:
#:
#:   * 31 distinct units, and NOT ONE is a unit of time. `Gal/Hr`, `Bu/Hr` and
#:     `kBTU/Hr` are flow and energy rates, not labour hours.
#:   * ZERO components that are a labour line item. "High Labor", "Low Labor"
#:     and "Hand Labor" are SCENARIO NAMES — which variant of the practice is
#:     being paid for — not a decomposition of one.
#:   * `Component` enumerates practice VARIANTS (fence type, cover-crop species
#:     count, grazing regime), not a bill of materials. Each row is a whole-
#:     practice payment rate in dollars per physical unit, with labour bundled
#:     in and unseparable.
#:
#: A payment rate is also the wrong KIND of figure even before the labour
#: problem. 60 rows across 9 practices name "Foregone Income" outright, mixed
#: into the same column as implementation cost with no field distinguishing
#: them. Income foregone is an opportunity cost — price formation — which the
#: handoff's own method rule (§3: replacement cost yes, everything else no)
#: excludes. Converting these to TEH by dividing by a wage would import exactly
#: what Guardrail I forbids, and would do it on a bundle that is part materials,
#: part equipment, part contractor margin and part foregone rent.
#:
#: THIS IS THE THIRD WRONG-INSTRUMENT POINTER the repo has found (after
#: SKILL_WORKING_LIFE_YEARS → BLS Employee Tenure). The pattern is now clear
#: enough to state as a rule: a `resolves_by` that names a SOURCE without naming
#: the FIELD in it that carries the quantity has not been checked.
EQIP_HAS_NO_LABOUR_LINE: bool = True

#: What a naive read of the file gets wrong, recorded as prose because nothing
#: computes with it: 1,041 of 2,691 rows (38.7%) are `HU-` duplicates —
#: Historically Underserved, a flat policy uplift at a median 1.200x the base
#: rate (8.3% of pairs deviate; range 1.008–1.333). They are the SAME practice
#: at a different payment rate, so any sum or mean over the raw file
#: double-counts them. It was briefly a module constant; nothing read it, and a
#: constant no code consumes is a docstring with a type annotation. The figure
#: also is NOT re-derivable here — it comes from the source schedule's COST
#: column and the shipped extract drops that column deliberately.

_EQIP_PA = Path(__file__).parent / "data" / "nrcs_eqip_pa_2026_practices.csv"


def load_eqip_practices() -> list[dict]:
    """
    The EQIP practice inventory — what IS usable from the payment schedule.

    units: none; this is a catalogue. `scenarios` counts base (non-HU) variants.

    The schedule cannot price stewardship in hours (`EQIP_HAS_NO_LABOUR_LINE`),
    but it does establish the PHYSICAL BASIS of a cropland stewardship census:
    which practices exist, and at what physical granularity each is measured —
    210 practices, most in acres, feet or each. That is the shape a labour
    census would have to fill, and it is worth keeping even though the cost
    column is unusable.

    Worked example: practice 340 Cover Crop has 5 base scenarios priced in Ac
    and kSqFt; a stewardship census needs hours per acre for each, which this
    file does not carry and an enterprise budget does.
    """
    with _EQIP_PA.open() as fh:
        return [
            {
                "practice_code": r["practice_code"],
                "practice_name": r["practice_name"],
                "scenarios": int(r["scenarios"]),
                "units": tuple(r["units"].split("|")),
                "names_foregone_income": r["names_foregone_income"] == "True",
            }
            for r in csv.DictReader(fh)
        ]


#: The instrument that WOULD price cropland stewardship in hours, now that EQIP
#: has been checked and excluded. Land-grant extension ENTERPRISE BUDGETS
#: (Penn State, Iowa State, Kansas State and their peers) itemise machine hours
#: and labour hours per acre per field operation, in HOURS, because they are
#: built for farm planning rather than for payment. They are the agricultural
#: analogue of the state-DOT maintenance-activity manuals the infrastructure
#: floor's `resolves_by` already names, and they share the property that makes
#: those usable: the quantity is recorded in time because time is what the
#: planner needs, not converted into time from money.
CROPLAND_HOURS_RESOLVES_BY: str = (
    "land-grant extension enterprise budgets, which itemise labour hours and "
    "machine hours per acre per field operation — Penn State Extension crop "
    "budgets for the PA jurisdiction already used elsewhere in this repo, and "
    "their peers by state. NOT the NRCS EQIP payment schedule: checked FY2026 "
    "Pennsylvania, 2,691 rows, no time unit and no labour line item, and its "
    "dollar column mixes implementation cost with foregone income. See "
    "EQIP_HAS_NO_LABOUR_LINE."
)


#: PENN STATE EXTENSION — HOURS EXIST, BUT NOT OF THE QUANTITY THIS SOCKET NEEDS.
#: The instrument `CROPLAND_HOURS_RESOLVES_BY` named, checked 2026-08-16.
#:
#: The Agricultural Alternatives series DOES carry per-acre labour in HOURS,
#: currency-free, in an "Initial Resource Requirements" block — exactly the
#: property that made it the right pointer after EQIP failed. 30 guides fetched,
#: 17 carry the block, 5 give both a 1-acre basis and a labour figure.
#:
#: IT STILL DOES NOT PRICE CROPLAND STEWARDSHIP, for three reasons, and the
#: first is the same error this module rejects everywhere else:
#:
#:   1. WRONG QUANTITY. These are CROP PRODUCTION hours — growing a saleable
#:      crop — not the labour the land demands to hold its condition. Counting
#:      them as ecological EOH is the same move as counting logging as forest
#:      stewardship, which `STEWARDSHIP_ATTRIBUTIONS` deliberately excludes.
#:   2. WRONG CROPS. Asparagus, tomato, pepper, onion and cantaloupe are
#:      horticultural crops on a sliver of US cropland. The 152.7 Mha in the
#:      census is overwhelmingly corn, soybeans, wheat and hay, whose per-acre
#:      labour is far lower. `growing-corn-and-corn-silage-on-a-budget` carries
#:      no hours figure at all.
#:   3. PARTIAL EVEN AS PRODUCTION. The block separates labour from
#:      "Harvest/grading/packaging", and the harvest term is an order of
#:      magnitude larger (asparagus 5–20 against 25–300 h/acre).
#:
#: FOURTH INSTRUMENT CHECKED, FOURTH NOT USABLE — and the reason has shifted,
#: which is progress. EQIP failed on UNITS (no hours anywhere). This one has the
#: units and fails on SCOPE. That narrows what is missing to a single question:
#: hours per acre for a CONSERVATION PRACTICE, not for a crop.
EXTENSION_MEASURES_PRODUCTION_NOT_STEWARDSHIP: bool = True

_PSU_HOURS = Path(__file__).parent / "data" / "psu_extension_labour_hours.csv"


def load_extension_labour_hours() -> list[dict]:
    """
    Per-acre labour hours from Penn State Extension — production, not stewardship.

    units: labour-hours per acre per year, as a low–high range.

    KEPT DESPITE BEING UNUSABLE FOR THE SOCKET, because it establishes that the
    extension-publication route yields hours at all, and because the next worker
    should be able to see what was checked rather than re-check it. Every row
    carries `measures`, which says what the number is NOT.

    Worked example: tomato 19 h/acre of production labour. Applying that to the
    census's 152.7 Mha of cropland would give 1.15e9 h/yr of "stewardship" from
    a figure that contains no stewardship at all.
    """
    with _PSU_HOURS.open() as fh:
        return [
            {
                "crop": r["crop"],
                "labour_low": float(r["labor_hours_per_acre_low"]),
                "labour_high": float(r["labor_hours_per_acre_high"]),
                "harvest_low": (
                    float(r["harvest_hours_per_acre_low"])
                    if r["harvest_hours_per_acre_low"] else None
                ),
                "measures": r["measures"],
            }
            for r in csv.DictReader(fh)
        ]


#: The narrowed question, after four instruments. Field-operation hours for a
#: conservation practice are a PHYSICS quantity, not a cost one: field capacity
#: in acres per hour is implement width x travel speed x field efficiency, so
#: hours per acre falls straight out of the machine and the operation list. That
#: is currency-free by construction, the same property that makes the
#: infrastructure floor better-determined than the monetized path.
CROPLAND_HOURS_RESOLVES_BY_V2: str = (
    "machinery field-capacity tables (ASABE D497 and the extension "
    "machinery-cost publications that republish them) applied to the operation "
    "list of a conservation practice: acres/hour = width x speed x field "
    "efficiency, so hours/acre is derived from the machine, not from a price. "
    "The practice inventory in nrcs_eqip_pa_2026_practices.csv supplies the "
    "operation lists. RULED OUT ALREADY: NRCS EQIP payment schedules (no time "
    "unit, no labour line, dollar column mixes cost with foregone income) and "
    "Penn State Extension Agricultural Alternatives (hours yes, but crop "
    "PRODUCTION hours for horticultural crops, not stewardship)."
)


# ---------------------------------------------------------------------------
# FIELD CAPACITY — hours per acre from the machine, with no money in the chain
# ---------------------------------------------------------------------------

#: The conversion constant in the effective-field-capacity identity. Exact:
#: 43,560 sq ft per acre / 5,280 ft per mile = 8.25. Not a calibration.
FIELD_CAPACITY_CONSTANT: float = 8.25

_ASAE = Path(__file__).parent / "data" / "asae_field_capacity.csv"


def load_field_capacity_table() -> dict[str, dict]:
    """
    ASAE field efficiency and suggested speed by implement.

    units: field efficiency dimensionless ∈ (0,1]; speed miles per hour.

    Source: ASAE Standards 2005 Table 5, as republished in Schuler,
    "Estimating Agricultural Field Machinery Costs", UW-Extension. 17 implements,
    each with an efficiency RANGE and a speed RANGE — the ranges are the
    standard's own, not a band this repo invented.

    NOTE WHAT IS ABSENT: implement WIDTH. The standard gives efficiency and
    speed because those are properties of the operation; width is a machine-size
    CHOICE, and it is the input that makes hours-per-acre a delivery
    productivity rather than a physical constant. See `hours_per_acre`.
    """
    with _ASAE.open() as fh:
        return {
            r["implement"]: {
                "label": r["implement_label"],
                "efficiency_low": float(r["field_efficiency_low"]),
                "efficiency_high": float(r["field_efficiency_high"]),
                "speed_low": float(r["speed_mph_low"]),
                "speed_high": float(r["speed_mph_high"]),
            }
            for r in csv.DictReader(fh)
        }


def effective_field_capacity(
    width_ft: float, speed_mph: float, field_efficiency: float
) -> float:
    """
    Acres covered per hour by one machine and one operator.

    Governing equation (ASAE/ASABE EP496, D497):

        EFC (ac/h) = width_ft × speed_mph × field_efficiency / 8.25

    units: acres per hour.

    THIS IS THE WHOLE POINT OF THE ROUTE. Every term is a physical property of
    the machine and the pass — width, speed, and the fraction of theoretical
    capacity actually achieved once turns, overlap and refills are counted.
    There is no price anywhere in the chain, so the resulting labour figure
    cannot import price formation the way a payment schedule or a wage-divided
    cost would. Same determinacy property as the infrastructure floor.

    Worked example, checked against the publication's own: a 12 ft rotary
    mower-conditioner at 6 mph and 0.75 efficiency gives
    6 × 12 × 0.75 / 8.25 = **6.545 ac/h** (the worksheet rounds to 6.55).

    Raises:
        ValueError: on a non-positive width, speed or efficiency, or an
            efficiency above 1.0 — a machine cannot exceed its theoretical
            capacity, and a silent pass here would understate hours.
    """
    if width_ft <= 0.0 or speed_mph <= 0.0:
        raise ValueError(
            f"width and speed must be positive, got {width_ft}, {speed_mph}"
        )
    if not 0.0 < field_efficiency <= 1.0:
        raise ValueError(
            f"field efficiency must be in (0, 1], got {field_efficiency}"
        )
    return width_ft * speed_mph * field_efficiency / FIELD_CAPACITY_CONSTANT


def hours_per_acre(implement: str, width_ft: float) -> dict:
    """
    Labour-hours to make one pass over one acre, as a band.

    Governing equation:

        hours/acre = 1 / EFC

    evaluated at both corners of the standard's efficiency and speed ranges.
    SLOW is low speed with low efficiency; FAST is high with high.

    units: labour-hours per acre per pass.

    WIDTH IS SUPPLIED, NOT MEASURED, and that is the honest shape of this
    quantity. Hours per acre falls as the machine gets wider, so this is a
    DELIVERY PRODUCTIVITY at a stated equipment scale — exactly what
    `reference.personal_basket` does when it prices nutrition at the LSMS
    *unassisted* stratum rather than pretending one number covers every
    technology. Doubling the drill halves the hours, and that is not noise in
    the estimate, it is capital substituting for labour: the same substitution ε
    measures elsewhere in the framework.

    Worked example: a 15 ft grain drill runs 0.55–0.80 efficiency at 4–7 mph, so
    EFC spans 4.00–10.18 ac/h and one seeding pass costs **0.098–0.250 h/acre**.

    Raises:
        KeyError: on an unknown implement — guessing a neighbour's efficiency
            is how a plausible wrong number gets in.
    """
    table = load_field_capacity_table()
    if implement not in table:
        raise KeyError(
            f"unknown implement {implement!r}; have {sorted(table)}"
        )
    m = table[implement]
    slow = effective_field_capacity(width_ft, m["speed_low"], m["efficiency_low"])
    fast = effective_field_capacity(width_ft, m["speed_high"], m["efficiency_high"])
    return {
        "implement": implement,
        "label": m["label"],
        "width_ft": width_ft,
        "capacity_slow_ac_per_hr": slow,
        "capacity_fast_ac_per_hr": fast,
        "hours_per_acre_high": 1.0 / slow,
        "hours_per_acre_low": 1.0 / fast,
    }



#: The input the field-capacity route needs and does not have. Hours per hectare
#: of TREATED land is not hours per hectare of cropland; the bridge is the share
#: of cropland receiving each practice, and nothing here carries it.
CROPLAND_ADOPTION_RESOLVES_BY: str = (
    "USDA Census of Agriculture, which reports cover-crop acreage directly "
    "(Table 47 in the 2022 cycle) alongside no-till, reduced-till and "
    "conservation-easement acres, by state and county, on a five-year cycle. "
    "That converts hours per treated hectare into hours per hectare of "
    "cropland. It is the LAST missing input for this land class: the hours "
    "themselves are now derivable from field capacity, which is physics."
)

#: Operations a conservation practice requires, per acre per year. ASSUMED —
#: this is the weak link in the route, exactly as the occupation→land-class
#: mapping is the weak link in the census. The NRCS conservation practice
#: standards specify what each practice involves in prose; turning that into an
#: implement list is a reading, and a different reading gives different hours.
#: Only practices whose operations are unambiguous are listed.
PRACTICE_OPERATIONS: dict[str, dict] = {
    "340_cover_crop": {
        "practice_code": "340",
        "label": "Cover Crop",
        "operations": ("grain_drill", "boom_sprayer"),
        "basis": (
            "one drilled seeding pass in autumn and one termination pass in "
            "spring. Chemical termination is assumed; mechanical termination "
            "(roller_packer) is the EQIP schedule's separate scenario and costs "
            "a comparable single pass."
        ),
    },
    "340_cover_crop_mechanical": {
        "practice_code": "340",
        "label": "Cover Crop, Mechanical Termination",
        "operations": ("grain_drill", "roller_packer"),
        "basis": (
            "the EQIP schedule's Mechanical Termination scenario — drill in, "
            "roller-crimp out, no herbicide pass."
        ),
    },
    "329_residue_tillage_no_till": {
        "practice_code": "329",
        "label": "Residue and Tillage Management, No Till",
        "operations": (),
        "basis": (
            "no till is the ABSENCE of an operation. Its stewardship hours are "
            "ZERO by construction, and the practice's benefit is the tillage "
            "passes it removes — which is why a labour census alone cannot rank "
            "conservation practices by value. Included precisely because it is "
            "the case that breaks a naive hours-are-good reading."
        ),
    },
}


def load_stewardship_employment(
    registry_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict]:
    """
    Employment in thousands for each attributed occupation, keyed by SOC code.

    Takes the registry rows as an ARGUMENT rather than importing the loader,
    because `reference/` imports nothing from the package. The caller
    (`scenarios.land_stewardship`) supplies `reference.onet_multipliers
    .load_registry()`.

    units: thousands of workers (the registry's own unit, preserved).

    Raises:
        ValueError: if an attributed occupation is absent from the registry —
            silently dropping one would understate the floor without saying so.
    """
    wanted = {occ for a in STEWARDSHIP_ATTRIBUTIONS for occ in a["occupations"]}
    found = {
        str(r["occ6"]): {
            "employment_k": float(r["employment_k"]),
            "title": str(r["title"]),
        }
        for r in registry_rows
        if r["occ6"] in wanted
    }
    missing = wanted - set(found)
    if missing:
        raise ValueError(
            f"attributed occupations absent from the registry: {sorted(missing)}. "
            "The registry epoch has moved; re-check the attribution rather than "
            "dropping them."
        )
    return found
