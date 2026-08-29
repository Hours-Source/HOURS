"""
The stewardship-hours census — the ecological anchor's `resolves_by`, run.

`scenarios/ecological_floor.py` inverted the question and asked what stewardship
intensity a given EOH share would demand. It could not answer the forward
question because nothing in the repo measured stewardship hours. This module
answers it, for one jurisdiction, from measured inputs the repo already holds.

    intensity(class) = employment(class) × hours_per_worker_year / area(class)

    census = [{biome, area_hectares, hours_per_hectare_year}, ...]

and the census goes through `core.eoh_generation.ecological_statutory_floor`,
whose comparison against `ECOLOGICAL_BASE_RATE` is the falsification.

units: labour-hours per hectare per year throughout.
ε-behavior: none. Stewardship burden is a property of the land and its
condition; ε enters fulfilment, not this generation floor. The census is
therefore identical at ε ∈ {0, 0.40, 0.99} — asserted in the tests, because a
floor that moved with ε would mean an automation term had leaked into a
generation quantity.

THE RESULT DEPENDS ON A SCOPE CHOICE, AND THE MODULE REFUSES TO MAKE IT
-----------------------------------------------------------------------
Two readings, from the same measured inputs:

  ecosystem-only   0.18 h/ha·yr over forest-use land and federal parks.
  with amenity     7.3 h/ha·yr over those plus urban groundskeeping.

CORRECTED 2026-08-28. These lines used to read "BELOW the anchor's implied 0.37
h/ha·yr — the anchor is not too low here, it is too HIGH." That comparison was
against the PRE-Phase-4b implied intensity, which divided the whole contiguous
US obligation by a million-person population. Against a frame-consistent anchor
the ecosystem scope reads ~222× ABOVE, so the claim was inverted, and the
hypothesis it appeared to refute was in fact supported on every class. The
reversal was recorded in CLAUDE.md on 2026-08-17 and this module was not
updated — the verdict string shipped the retracted reading for eleven days.
The ratio is now computed live rather than restated in prose.

A factor of 50 separates the two area-weighted means, and 510 separates the two
land classes themselves. The only thing that moves between them is whether 1.33M
landscaping, tree-care and vegetation workers count as ecological stewardship.
See `reference.land_stewardship` for the argument both ways. Reporting one number
would conceal that the scope question, not the measurement, is what is
unresolved.

WHAT THIS DOES NOT SETTLE
--------------------------
Coverage is 30.3% of US land area by the amenity reading and 27.3% without it.
The largest unpriced class — 107.6 Mha of rural parks and wildlife areas — is
precisely the land most likely to carry real stewardship labour, and it is
excluded rather than costed at zero. So the priced mean is NOT an estimate of
the US stewardship intensity; it is a lower bound over the part that has a
costed path, and `coverage` must be read before it is compared to anything.

This is the same discipline `personal_floor` applies at 6.9% basket coverage,
and for the same reason: at low coverage the residual is dominated by the
repo's own incompleteness, so a number fitted to it would be a fitted residual
wearing a measurement's clothes.

THE ANCHOR IS KEYED TO NOTHING — WHICH IS THE DEFECT, STATED EXACTLY
---------------------------------------------------------------------
`ecological_eoh(ecosystem_health, ...)` takes no area and no population. It
returns `base_rate / health` (+ spike, deferred, thermal) — 609,756 h/yr at
canonical health, for a collective of one million or of three hundred and
thirty-five million, on one hectare or on a billion.

That makes ecological the ONLY domain with no extensive quantity behind it:

    personal_eoh(population, ...)          extensive in population
    infrastructure_eoh(capital_stock, ...) extensive in capital
    knowledge_eoh(...)                     extensive in the corpus
    ecological_eoh(ecosystem_health, ...)  extensive in NOTHING

which is why its share collapses as the system grows — everything else scales
and it does not. The repo records the defect as "a relative anchor summed with
absolute counts"; the sharper statement is that stewardship demand is a property
of AREA and the anchor has no area term at all.

`implied_stewardship_intensity` manufactures one, dividing by
`population × hectares_per_capita`. So the "0.37 h/ha·yr" the anchor implies is
a synthesised per-hectare figure, not a measured one, and it moves with
population for a quantity that should not depend on population.

CONSEQUENCE FOR THE COMPARISON. `floor_from_census(census, population=...)`
divides that fixed anchor by whatever denominator it is handed:
`population=US_REFERENCE_POPULATION` would deflate it 335× and report a ratio of ~8,600×
that means nothing.

The comparable quantity is INTENSITY (h/ha·yr), which is population-free. This
module therefore calls `floor_from_census` at `REFERENCE_POPULATION` — where the
anchor is defined — and reports US per-capita figures from its own arithmetic,
clearly separated. Anyone reusing `floor_from_census` on a census at a different
scale needs to know this.

Population is not irrelevant to the obligation, but it does not belong in the
rate. Load per hectare does drive stewardship demand — more people on the same
ground degrade it faster than it recovers — and the model already has the place
for that: `ecosystem_health` falls under load, and `ecological_eoh` divides by
it. So the physically-shaped form is `area × intensity(health)` with health
responding to density, NOT a population term in the rate itself. That is the
shape `ecological_statutory_floor` computes, which makes this census a
falsification of the anchor's FORM as much as of its level.

Reference: `data.ECOLOGICAL_BASE_RATE` resolves_by; `scenarios/ecological_floor.py`
(the inversion this answers); reconciliation §9 (domain balance).
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import ecological_statutory_floor
from hours_eoh.data import (
    AGENCY_STEWARDSHIP_ROLE_MIX,
    AMENITY_STEWARDSHIP_WEIGHT,
    LAND_HECTARES_PER_CAPITA,
    PRACTICE_EQUIPMENT_WIDTHS_FT,
    US_MAINLAND_HECTARES,
    US_REFERENCE_POPULATION,
)
from hours_eoh.reference.land_stewardship import (
    ACRE_HECTARES,
    AGENCY_LAND_STEWARDS,
    AGENCY_ROLE_MIX_RESOLVES_BY,
    ALLOCATION_POLICIES,
    COMPLETE_ATTRIBUTIONS,
    CROPLAND_ADOPTION_RESOLVES_BY,
    HELD_OUT_OCCUPATIONS,
    JURISDICTION,
    PARKS_CLASS,
    PARKS_FEDERAL,
    PARKS_OTHER,
    PRACTICE_OPERATIONS,
    STEWARDSHIP_ATTRIBUTIONS,
    UNPRICED_REASONS,
    agency_role_mix,
    derive_allocations,
    hours_per_acre,
    load_land_use,
    load_stewardship_employment,
    parks_split,
    total_land_hectares,
)
from hours_eoh.reference.onet_multipliers import load_registry
from hours_eoh.scenarios.ecological_floor import (
    REFERENCE_POPULATION,
    floor_from_census,
    implied_stewardship_intensity,
    required_stewardship_intensity,
)
from hours_eoh.scenarios.food_conservation import hours_per_worker_year

#: Scope readings the census is reported under. `ecosystem` excludes land classes
#: flagged `amenity` (w=0); `with_amenity` includes them whole (w=1); `declared`
#: is the ADOPTED position at `AMENITY_STEWARDSHIP_WEIGHT`. The two corners are
#: kept because `scope_comparison` needs them to show the 50× spread the decision
#: was made against — a decision whose alternatives have been deleted is not
#: reviewable.
SCOPES: tuple[str, ...] = ("ecosystem", "declared", "with_amenity")

#: The adopted default. `census_report()` and `stewardship_census()` read this
#: unless told otherwise.
ADOPTED_SCOPE: str = "declared"


def _resolve_amenity_weight(scope: str, amenity_weight: float | None) -> float:
    """The single place scope becomes a weight — duplicating it desynced the
    reported weight from the one actually applied."""
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}, got {scope!r}")
    if amenity_weight is None:
        amenity_weight = {
            "ecosystem": 0.0,
            "declared": AMENITY_STEWARDSHIP_WEIGHT,
            "with_amenity": 1.0,
        }[scope]
    if not 0.0 <= amenity_weight <= 1.0:
        raise ValueError(f"amenity_weight must be in [0, 1], got {amenity_weight}")
    return amenity_weight


def stewardship_intensities(
    scope: str = ADOPTED_SCOPE,
    allocation: str = "held_out",
    amenity_weight: float | None = None,
) -> list[dict]:
    """
    Measured stewardship intensity per land-use class, hours per hectare per year.

    Governing equation, per attributed class:

        h_per_ha = Σ_occ employment_k(occ) · 1000 · h_worker_year / area_hectares

    where employment is BLS EP (frozen epoch 2026-07-29), `h_worker_year` is the
    repo's derived ≈1,874 h (ATUS ÷ registry employment, NOT a chosen 2,080), and
    area is USDA ERS Major Land Uses 2022. Classes with no attributed occupation
    return `hours_per_hectare_year=None` and carry their reason.

    units: labour-hours per hectare per year.

    Worked example (forest-use land): (10.3 + 14.0) thousand workers × 1,874 h
    ÷ 250,078,730 ha = 0.182 h/ha·yr — about eleven minutes per hectare per year.

    Args:
        scope: "with_amenity" (default) counts urban groundskeeping as
            stewardship; "ecosystem" excludes every class flagged `amenity`.
        allocation: how much of the held-out occupations to bring in —
            "held_out" (default, errs LOW), "derived" (the supervisory chain,
            genuinely derivable), or "area" (plus advisory occupations spread
            by land area — the upper corner). See `ALLOCATION_POLICIES`.
        amenity_weight: fraction of amenity-class labour counted as ecological
            stewardship, ∈ [0, 1]. `None` (default) takes it from `scope`:
            1.0 for "with_amenity", 0.0 for "ecosystem". Supplying a value
            OVERRIDES the scope, which is how the continuous curve between the
            two corners is swept.

    Raises:
        ValueError: on an unknown scope or policy, an amenity weight outside
            [0, 1], or if an attributed occupation has vanished from the registry.
    """
    amenity_weight = _resolve_amenity_weight(scope, amenity_weight)

    registry = load_registry()
    employment = load_stewardship_employment(registry)
    extra = derive_allocations(registry, allocation)
    h_worker = hours_per_worker_year()

    attributed = {a["land_use"]: a for a in STEWARDSHIP_ATTRIBUTIONS}

    # The parks class is SPLIT: the federally-staffed two-thirds is priceable
    # from the agency workforce, the state-and-other third is not, and merging
    # them would let the unmeasured part inherit the measured part's intensity.
    land_rows: list[dict] = []
    for land in load_land_use():
        if land["land_use"] == PARKS_CLASS:
            land_rows.extend(parks_split())
        else:
            land_rows.append(land)

    mix = agency_role_mix()
    agency_area = sum(a["hectares"] for a in AGENCY_LAND_STEWARDS)
    agency_workers = mix["combined"]["total"] * AGENCY_STEWARDSHIP_ROLE_MIX

    rows: list[dict] = []
    for land in land_rows:
        name = land["land_use"]

        if name == PARKS_FEDERAL:
            rows.append({
                "land_use": name,
                "area_hectares": land["area_hectares"],
                "workers": agency_workers,
                "allocated_workers": 0.0,
                "hours_per_hectare_year": (
                    agency_workers * h_worker / land["area_hectares"]
                    if land["area_hectares"] > 0.0 else None
                ),
                "amenity": False,
                "complete": True,
                "reason": (
                    "OPM Federal Workforce Data 2025-09: 27,104 NPS+FWS staff x "
                    f"role mix {AGENCY_STEWARDSHIP_ROLE_MIX:.4f} (band "
                    "[0.2263, 0.4073]) over the agencies' own reported acreage. "
                    "Headcount exact; acreage is an agency round number and is "
                    "the weaker half of the ratio."
                ),
                "excluded_partial_hours": 0.0,
            })
            continue
        area = land["area_hectares"]
        attr = attributed.get(name)
        allocated = sum(extra.get(name, {}).values())

        # A class whose attribution is INCOMPLETE may not be priced by an
        # allocation alone: the floor's priced/unpriced split is binary, so
        # doing so would mark the whole class priced at a fraction of its true
        # labour. Report the hours, exclude them. See COMPLETE_ATTRIBUTIONS.
        if attr is None:
            rows.append({
                "land_use": name,
                "area_hectares": area,
                "workers": None,
                "allocated_workers": allocated,
                "hours_per_hectare_year": None,
                "amenity": False,
                "complete": False,
                "reason": UNPRICED_REASONS[name],
                "excluded_partial_hours": allocated * h_worker,
            })
            continue

        weight = amenity_weight if attr["amenity"] else 1.0
        workers = (
            sum(employment[occ]["employment_k"] * 1000.0 for occ in attr["occupations"])
            + allocated
        ) * weight
        priced = weight > 0.0

        rows.append({
            "land_use": name,
            "area_hectares": area,
            "workers": workers if priced else None,
            "allocated_workers": allocated * weight,
            "hours_per_hectare_year": (
                (workers * h_worker / area) if priced and area > 0.0 else None
            ),
            "amenity": bool(attr["amenity"]),
            "complete": name in COMPLETE_ATTRIBUTIONS,
            "reason": (
                attr["basis"] if priced
                else "amenity_weight=0 — excluded as amenity, not ecosystem function"
            ),
            "excluded_partial_hours": 0.0,
        })

    return rows


def stewardship_census(
    scope: str = ADOPTED_SCOPE,
    allocation: str = "held_out",
    amenity_weight: float | None = None,
) -> list[dict]:
    """
    The land census in `ecological_statutory_floor` intake shape.

    Returns `[{"biome", "area_hectares", "hours_per_hectare_year"}, ...]` over
    ALL nine US land-use classes — priced classes carry a float, unpriced carry
    `None` so the floor EXCLUDES them rather than costing them at zero.

    units: hectares and hours per hectare per year.

    Worked example: nine rows, two priced under the default scope, covering
    276.9 Mha of the 915.1 Mha US total → coverage 0.303.
    """
    return [
        {
            "biome": r["land_use"],
            "area_hectares": r["area_hectares"],
            "hours_per_hectare_year": r["hours_per_hectare_year"],
        }
        for r in stewardship_intensities(scope, allocation, amenity_weight)
    ]


def census_report(
    scope: str = ADOPTED_SCOPE,
    allocation: str = "held_out",
    amenity_weight: float | None = None,
) -> dict:
    """
    Run the census through the floor and compare it to the anchor.

    The falsification. Returns the per-class intensities, the floor result, the
    anchor comparison at REFERENCE scale (see the module docstring on why the
    comparison is on intensity and not per capita), and the target-share
    requirement the measured intensity happens to land against.

    Reports; changes nothing. No constant moves on this.
    """
    rows = stewardship_intensities(scope, allocation, amenity_weight)
    census = stewardship_census(scope, allocation, amenity_weight)
    floor = ecological_statutory_floor(census)

    # REFERENCE_POPULATION, deliberately: the anchor is an absolute total defined
    # at that scale, so only intensity is comparable. See the module docstring.
    compared = floor_from_census(census, population=REFERENCE_POPULATION)
    anchor = implied_stewardship_intensity(population=REFERENCE_POPULATION)
    one_pc = required_stewardship_intensity(0.01, population=REFERENCE_POPULATION)

    total_ha = total_land_hectares()
    measured = floor["mean_hours_per_hectare"]
    anchor_intensity = anchor["hours_per_hectare_year"]

    return {
        "scope": scope,
        "allocation": allocation,
        "amenity_weight": _resolve_amenity_weight(scope, amenity_weight),
        "jurisdiction": JURISDICTION,
        "hours_per_worker_year": hours_per_worker_year(),
        "by_class": rows,
        "excluded_partial_hours": sum(r["excluded_partial_hours"] for r in rows),
        "floor_hours": floor["floor_hours"],
        "area_total_hectares": total_ha,
        "area_priced_hectares": floor["area_priced"],
        "coverage": floor["coverage"],
        "measured_hours_per_hectare": measured,
        "anchor_hours_per_hectare": anchor_intensity,
        "ratio_to_anchor": compared["ratio_to_anchor"],
        "required_h_per_ha_at_1pc_share": one_pc["required_hours_per_hectare_year"],
        "us_hectares_per_capita": total_ha / US_REFERENCE_POPULATION,
        "us_floor_h_per_capita": floor["floor_hours"] / US_REFERENCE_POPULATION,
        "unpriced": floor["unpriced"],
        "held_out_occupations": list(HELD_OUT_OCCUPATIONS),
        "verdict": _verdict(scope, floor, measured, anchor_intensity, one_pc),
    }


def _verdict(
    scope: str,
    floor: dict,
    measured: float,
    anchor_intensity: float,
    one_pc: dict,
) -> str:
    ratio = measured / anchor_intensity if anchor_intensity > 0.0 else 0.0
    direction = "ABOVE" if ratio >= 1.0 else "BELOW"
    return (
        f"scope={scope}: measured stewardship intensity is {measured:.3f} h/ha·yr "
        f"over the {floor['coverage'] * 100:.1f}% of US land area that has a "
        f"costed path, against the anchor's implied {anchor_intensity:.3f} — "
        f"a factor of {ratio:.2f}× {direction}. Reaching a 1% ecological share "
        f"needs {one_pc['required_hours_per_hectare_year']:.1f} h/ha·yr. "
        f"{len(floor['unpriced'])} land classes covering "
        f"{sum(u['area_hectares'] for u in floor['unpriced']) / 1e6:.1f} Mha are "
        f"EXCLUDED, not costed at zero, so this is a LOWER BOUND — read coverage "
        f"before comparing it to anything, and read both scopes before quoting "
        f"either."
    )


def agency_report() -> dict:
    """
    The parks-and-wildlife class: measured workforce, measured role mix, priced.

    Governing equation:

        workers   = Σ_agency headcount × AGENCY_STEWARDSHIP_ROLE_MIX
        intensity = workers × hours_per_worker_year / Σ_agency hectares

    units: labour-hours per hectare per year.

    WHAT CHANGED, AND WHY IT MATTERS. The first pass at this class had agency
    HEADCOUNT but not the ROLE MIX, and reported a RAW 1.090 h/ha·yr for NPS —
    six times the forest intensity — with the directional note that pricing the
    class would likely RAISE the census. **That was wrong, by the size of the
    role mix.** NPS is 10.12% resource-management staff; its largest series are
    park ranger (20.7%) and maintenance mechanic (13.9%). Corrected, federal
    parks come in at 0.161 h/ha·yr — comparable to forest's 0.182 and BELOW the
    declared census mean — so pricing it LOWERS the mean (0.585 → 0.498) while
    raising coverage (0.303 → 0.381).

    The class was not priced on the raw figure, and this is why. A directional
    claim that does not survive its own measurement is the cheapest kind of
    error to make and the easiest to propagate.

    Worked example: 27,104 NPS+FWS staff × 0.2263 = 6,133 stewardship workers ×
    1,874.4 h ÷ 71,629,358 ha = 0.161 h/ha·yr.

    Reports; changes nothing.
    """
    mix = agency_role_mix()
    h = hours_per_worker_year()
    area = sum(a["hectares"] for a in AGENCY_LAND_STEWARDS)

    per_agency = []
    for a in AGENCY_LAND_STEWARDS:
        m = mix[a["agency"]]
        per_agency.append({
            "agency": a["name"],
            "headcount": m["total"],
            "stewardship_workers": m["total"] * AGENCY_STEWARDSHIP_ROLE_MIX,
            "role_mix_low": m["low"],
            "role_mix_high": m["high"],
            "hectares": a["hectares"],
            "raw_hours_per_hectare_year": m["total"] * h / a["hectares"],
            "stewardship_hours_per_hectare_year": (
                m["total"] * m["low"] * h / a["hectares"]
            ),
            "area_source": a["area_source"],
            "note": a["note"],
        })

    workers = mix["combined"]["total"] * AGENCY_STEWARDSHIP_ROLE_MIX
    intensity = workers * h / area
    raw = mix["combined"]["total"] * h / area
    census = census_report()
    forest = next(
        r for r in census["by_class"] if r["land_use"] == "Forest-use land (all)"
    )

    return {
        "agencies": per_agency,
        "role_mix_band": (mix["combined"]["low"], mix["combined"]["high"]),
        "role_mix_adopted": AGENCY_STEWARDSHIP_ROLE_MIX,
        "federal_area_hectares": area,
        "stewardship_hours_per_hectare_year": intensity,
        "raw_hours_per_hectare_year": raw,
        "raw_overstates_by": raw / intensity if intensity > 0.0 else 0.0,
        "vs_forest": intensity / forest["hours_per_hectare_year"],
        "vs_census_mean": intensity / census["measured_hours_per_hectare"],
        "priced": True,
        "resolves_by": AGENCY_ROLE_MIX_RESOLVES_BY,
        "verdict": (
            f"federal parks and refuges are tended at {intensity:.3f} h/ha·yr — "
            f"{intensity / forest['hours_per_hectare_year']:.2f}× the forest "
            f"intensity and {intensity / census['measured_hours_per_hectare']:.2f}× "
            f"the census mean, so pricing this class LOWERS the mean and raises "
            f"coverage. The RAW figure ignoring role mix is {raw:.3f}, "
            f"{raw / intensity:.1f}× higher, and the earlier directional reading "
            f"taken from it — that parks would raise the census — did not "
            f"survive measurement. NPS reads {mix['NPS']['low']:.1%} "
            f"resource-management staff against FWS's {mix['FWS']['low']:.1%}: "
            f"one is a visitor-services organisation standing on land, the other "
            f"is a land-management organisation."
        ),
    }



def practice_hours_per_hectare(practice: str) -> dict:
    """
    Stewardship hours per hectare per year for one conservation practice.

    Governing equation:

        h/ha·yr = Σ_operations (1 / EFC(operation)) / 0.40468564224

    summed over the practice's operation list, at the shipped equipment widths,
    and reported as a band from the ASAE efficiency and speed ranges.

    units: labour-hours per hectare per year, on land that RECEIVES the practice.

    THE UNIT MATTERS AND IS EASY TO MISREAD. This is hours per hectare *of
    treated land*, not per hectare of cropland. Multiplying it by the census's
    152.7 Mha would assert that every acre of US cropland is cover-cropped.

    Worked example: 340 Cover Crop is one drilled seeding pass plus one
    termination pass — 0.123–0.342 h/acre, i.e. **0.303–0.845 h/ha·yr** on
    cover-cropped ground. For scale, the census reads 0.182 h/ha·yr on forest
    and 0.161 on federal parks, so a cover-cropped acre is tended comparably or
    somewhat harder than working forest.

    Raises:
        KeyError: on an unknown practice.
    """
    if practice not in PRACTICE_OPERATIONS:
        raise KeyError(
            f"unknown practice {practice!r}; have {sorted(PRACTICE_OPERATIONS)}"
        )
    spec = PRACTICE_OPERATIONS[practice]
    ops = []
    low = high = 0.0
    for op in spec["operations"]:
        d = hours_per_acre(op, PRACTICE_EQUIPMENT_WIDTHS_FT[op])
        ops.append(d)
        low += d["hours_per_acre_low"]
        high += d["hours_per_acre_high"]

    return {
        "practice": practice,
        "practice_code": spec["practice_code"],
        "label": spec["label"],
        "basis": spec["basis"],
        "operations": ops,
        "hours_per_acre_low": low,
        "hours_per_acre_high": high,
        "hours_per_hectare_low": low / ACRE_HECTARES,
        "hours_per_hectare_high": high / ACRE_HECTARES,
    }


def field_capacity_report() -> dict:
    """
    What the field-capacity route delivers, and the gap it does not close.

    IT WORKED, ON ITS OWN TERMS. Hours per acre for a conservation practice are
    now computable from physics alone — width x speed x efficiency, no price
    anywhere in the chain. That is the fifth instrument tried and the first that
    yields the right quantity in the right units.

    IT STILL CANNOT PRICE CROPLAND, and the reason is a NEW gap rather than
    another failure of the same one. Hours per hectare of TREATED land is not
    hours per hectare of cropland. Converting between them needs the adoption
    fraction — what share of the 152.7 Mha actually receives each practice —
    and nothing in this repo carries it.

    So the route has moved the problem from "we have no hours" to "we have hours
    and no adoption". That is a smaller and much better-posed question: the USDA
    Census of Agriculture reports cover-crop acres directly, on a five-year
    cycle, and it is the instrument named in `CROPLAND_ADOPTION_RESOLVES_BY`.

    AND THE UNKNOWN IS NOW BOUNDED ABOVE, which is the strongest form of not
    knowing. Adoption cannot exceed 1, so the class's contribution cannot exceed
    the practice rate times the whole 152.7 Mha: **0.27–0.74× the entire current
    census**. Universal cover-cropping of every acre of US cropland would not
    even double the measured floor. At realistic adoption — the Census of
    Agriculture's cover-crop share has run 5–7% — it is 1–5%. So the missing
    input moves the answer within a known range rather than transforming it,
    and cropland is NOT where the domain-balance gap is hiding.

    Reports; changes nothing. Cropland stays unpriced.
    """
    practices = [practice_hours_per_hectare(p) for p in sorted(PRACTICE_OPERATIONS)]
    census = census_report()
    forest = next(
        r for r in census["by_class"] if r["land_use"] == "Forest-use land (all)"
    )
    cover = practice_hours_per_hectare("340_cover_crop")
    cropland_ha = next(
        c["area_hectares"] for c in load_land_use()
        if c["land_use"] == "Total cropland"
    )
    ceiling = (
        cover["hours_per_hectare_low"] * cropland_ha / census["floor_hours"],
        cover["hours_per_hectare_high"] * cropland_ha / census["floor_hours"],
    )

    return {
        "practices": practices,
        "adoption_ceiling_ratio": ceiling,
        "cropland_hectares": cropland_ha,
        "widths_ft": dict(PRACTICE_EQUIPMENT_WIDTHS_FT),
        "cover_crop_h_per_ha_band": (
            cover["hours_per_hectare_low"], cover["hours_per_hectare_high"]
        ),
        "forest_h_per_ha": forest["hours_per_hectare_year"],
        "cropland_priced": False,
        "missing_input": "practice adoption fraction per hectare of cropland",
        "resolves_by": CROPLAND_ADOPTION_RESOLVES_BY,
        "verdict": (
            f"cover-cropped ground takes {cover['hours_per_hectare_low']:.3f}–"
            f"{cover['hours_per_hectare_high']:.3f} h/ha·yr at the shipped "
            f"equipment widths, against {forest['hours_per_hectare_year']:.3f} "
            f"on working forest — so a treated acre is tended comparably or "
            f"somewhat harder. The route yields the RIGHT QUANTITY in the RIGHT "
            f"UNITS from physics alone, which four earlier instruments did not. "
            f"It still cannot price the 152.7 Mha, because hours per hectare of "
            f"TREATED land is not hours per hectare of cropland and the adoption "
            f"fraction is unknown — but that unknown is now BOUNDED: adoption "
            f"cannot exceed 1, so the class contributes at most "
            f"{ceiling[0]:.2f}–{ceiling[1]:.2f}× the whole current census. "
            f"Cover-cropping every acre of US cropland would not double the "
            f"measured floor, so cropland is NOT where the domain-balance gap "
            f"is hiding."
        ),
    }


def frame_report() -> dict:
    """
    Is the US reference frame over- or under-landed for the people in it?

    Governing comparison:

        ha_per_capita(US)  = US_MAINLAND_HECTARES / US_REFERENCE_POPULATION
        burden(h/person·yr) = ha_per_capita × measured intensity

    against the shipped `LAND_HECTARES_PER_CAPITA`, a planetary average whose own
    tag warns it is the wrong number for any actual collective.

    WHY THIS MATTERS FOR THE OBLIGATION. Stewardship demand scales with AREA and
    stewardship labour scales with POPULATION, so land per capita is the ratio
    that decides whether a collective can discharge its own ecological
    obligation. A land-rich, people-poor collective owes more hours per person
    than a dense one on identical ground — which is the sense in which a
    territory can be "over-sized" for its population.

    units: hectares per person; labour-hours per person per year.

    Worked example: 765,495,267 ha ÷ 335M = 2.285 ha/person, against the global
    default 1.65 — the contiguous US carries **38.5% more land per person** than
    the planetary average. At the declared amenity weight the measured intensity
    is 0.585 h/ha·yr, so the burden is ~1.34 h/person·yr over priced land.

    Reports; changes nothing.
    """
    us_ha_pc = US_MAINLAND_HECTARES / US_REFERENCE_POPULATION
    ratio = us_ha_pc / LAND_HECTARES_PER_CAPITA
    rep = census_report()
    intensity = rep["measured_hours_per_hectare"]

    return {
        "us_mainland_hectares": US_MAINLAND_HECTARES,
        "us_population": US_REFERENCE_POPULATION,
        "us_hectares_per_capita": us_ha_pc,
        "shipped_hectares_per_capita": LAND_HECTARES_PER_CAPITA,
        "ratio_to_shipped": ratio,
        "over_landed": ratio > 1.0,
        "measured_intensity_h_per_ha": intensity,
        "burden_h_per_capita_priced": us_ha_pc * intensity * rep["coverage"],
        "burden_h_per_capita_if_all_land_priced": us_ha_pc * intensity,
        "verdict": (
            f"the contiguous US carries {us_ha_pc:.3f} ha/person against the "
            f"shipped planetary default {LAND_HECTARES_PER_CAPITA:.2f} — "
            f"{'OVER' if ratio > 1.0 else 'UNDER'}-landed by {abs(ratio - 1) * 100:.1f}%. "
            f"Stewardship demand scales with area and stewardship labour with "
            f"population, so a land-rich frame owes MORE hours per person on "
            f"identical ground. At the declared amenity weight that is "
            f"{us_ha_pc * intensity:.2f} h/person·yr if every hectare were "
            f"priced, against {us_ha_pc * intensity * rep['coverage']:.2f} over "
            f"the {rep['coverage'] * 100:.1f}% that is. Both are far below the "
            f"personal domain's ~1,475 h/person·yr, which is the domain-balance "
            f"defect restated in per-capita terms."
        ),
    }


def allocation_band(scope: str = "ecosystem") -> dict:
    """
    The three allocation policies side by side — the corners, not a fitted point.

    Same discipline as `reference.care_demand.rivalry_exponent`, whose ρ is not
    identified and whose callers are told to read the corners rather than
    substitute a middle value. How much of an advisory occupation's year lands
    on any given land class is not measured by anything, so this reports the
    range the answer sits in and refuses to pick inside it.

    units: labour-hours per hectare per year.

    Worked example (`ecosystem` scope): 0.182 held_out → 0.188 derived → 0.271
    area. The supervisory chain moves forest intensity 3.2%; the advisory
    area-split moves it 49%; and the whole band stays BELOW the anchor's 0.370.
    """
    out = {}
    for policy in ALLOCATION_POLICIES:
        rep = census_report(scope=scope, allocation=policy)
        out[policy] = {
            "measured_hours_per_hectare": rep["measured_hours_per_hectare"],
            "coverage": rep["coverage"],
            "ratio_to_anchor": rep["ratio_to_anchor"],
            "excluded_partial_hours": rep["excluded_partial_hours"],
        }

    lo = out["held_out"]["measured_hours_per_hectare"]
    hi = out["area"]["measured_hours_per_hectare"]
    ratios = [v["ratio_to_anchor"] for v in out.values()]

    return {
        "scope": scope,
        "policies": out,
        "band": (lo, hi),
        "band_factor": (hi / lo) if lo > 0.0 else 0.0,
        "crosses_anchor": min(ratios) < 1.0 < max(ratios),
        "verdict": (
            f"scope={scope}: allocating the held-out occupations moves the "
            f"measured intensity from {lo:.3f} to {hi:.3f} h/ha·yr "
            f"({hi / lo:.2f}× across the band). The band does "
            f"{'CROSS' if min(ratios) < 1.0 < max(ratios) else 'NOT cross'} the "
            f"anchor, so the anchor comparison is "
            f"{'sensitive to' if min(ratios) < 1.0 < max(ratios) else 'robust against'} "
            f"the allocation choice. Only the supervisory chain is derived; the "
            f"advisory split is area-proportional, which is neutral, not measured."
        ),
    }


def anchor_crossing_weight(allocation: str = "held_out") -> float:
    """
    The amenity weight at which the census exactly equals the anchor — solved,
    not read off a grid.

    Governing equation. Above w=0 the priced area is fixed (forest + urban), so
    the intensity is linear in w:

        (fixed_hours + w · amenity_hours) / priced_area = anchor
        w* = (anchor · priced_area − fixed_hours) / amenity_hours

    where `fixed` is every priced non-amenity class. Derived from the census
    rather than from named classes: it was written against forest and urban
    alone and silently stopped being right the moment parks became priceable.

    units: dimensionless weight.

    Worked example: with forest, federal parks and urban priced, w* = 0.0364.
    Grid-reading this was wrong by a whole grid cell, which is why it is solved:
    a crossing point that moves with the sample grid is not a property of the
    model. It also moves whenever a class becomes priceable, which is why it is
    computed and never stored.
    """
    rows = stewardship_intensities("with_amenity", allocation=allocation)

    fixed_hours = fixed_area = amenity_hours = amenity_area = 0.0
    for r in rows:
        if r["hours_per_hectare_year"] is None:
            continue
        hours = r["hours_per_hectare_year"] * r["area_hectares"]
        if r["amenity"]:
            amenity_hours += hours
            amenity_area += r["area_hectares"]
        else:
            fixed_hours += hours
            fixed_area += r["area_hectares"]

    anchor = implied_stewardship_intensity(population=REFERENCE_POPULATION)[
        "hours_per_hectare_year"
    ]
    if amenity_hours <= 0.0:
        return float("nan")
    return (anchor * (fixed_area + amenity_area) - fixed_hours) / amenity_hours


def amenity_curve(
    weights: tuple[float, ...] = (
        0.0, 0.0228, AMENITY_STEWARDSHIP_WEIGHT, 0.0699, 0.25, 0.5, 1.0,
    ),
    allocation: str = "held_out",
) -> dict:
    """
    Intensity as a continuous function of the amenity weight.

    `scope_comparison` reports the two corners. This sweeps between them,
    because the honest position is not "one of these two" but "somewhere on this
    curve, and nothing here locates you on it."

    units: labour-hours per hectare per year against a dimensionless weight.

    Worked example: at w=0 the census reads 0.182 h/ha·yr (forest only); at
    w=0.5, 4.66; at w=1.0, 9.15. The anchor (0.3695) is crossed at **w* =
    0.0228** — solving `(forest_h + w·urban_h) / priced_area = anchor`. So
    admitting even 2.3% of groundskeeping labour puts the census above the
    anchor, and that is itself the finding: the result is not sensitive to WHERE
    on the curve you sit, only to whether you are at the origin.

    Note the discontinuity at w=0: coverage steps 0.273 → 0.303 the moment any
    amenity labour is admitted, because the urban class becomes priced. The
    intensity is linear in w above that step, not through it.
    """
    rows = []
    for w in weights:
        rep = census_report(
            scope="with_amenity", allocation=allocation, amenity_weight=w
        )
        rows.append({
            "amenity_weight": w,
            "measured_hours_per_hectare": rep["measured_hours_per_hectare"],
            "coverage": rep["coverage"],
            "ratio_to_anchor": rep["ratio_to_anchor"],
        })

    crossing = next(
        (r["amenity_weight"] for r in rows if r["ratio_to_anchor"] >= 1.0), None
    )
    return {
        "allocation": allocation,
        "curve": rows,
        "anchor_crossing_weight": anchor_crossing_weight(allocation),
        "first_weight_at_or_above_anchor": crossing,
        "verdict": (
            "the anchor is cleared at an amenity weight of "
            f"{crossing if crossing is not None else 'never'} on this grid — "
            "the census sits above the anchor for all but a near-zero admission "
            "of amenity labour, and below it only if amenity groundskeeping is "
            "excluded almost entirely."
        ),
    }


def scope_comparison() -> dict:
    """
    Both readings side by side — the scope question made visible.

    The single most important output of this module. `ecosystem` and
    `with_amenity` differ by roughly five hundred fold on identical measured
    inputs, and which one is right is a definitional question the data cannot
    settle.
    """
    reports = {s: census_report(s) for s in SCOPES}
    eco = reports["ecosystem"]["measured_hours_per_hectare"]
    amen = reports["with_amenity"]["measured_hours_per_hectare"]

    return {
        "readings": {
            s: {
                "measured_hours_per_hectare": r["measured_hours_per_hectare"],
                "coverage": r["coverage"],
                "ratio_to_anchor": r["ratio_to_anchor"],
                "floor_hours": r["floor_hours"],
            }
            for s, r in reports.items()
        },
        "spread_factor": (amen / eco) if eco > 0.0 else 0.0,
        "verdict": (
            f"the two scopes differ by {amen / eco:.0f}× on identical measured "
            f"inputs ({eco:.3f} vs {amen:.3f} h/ha·yr). Ecosystem-only lands ~"
            f"{reports['ecosystem']['ratio_to_anchor']:.0f}× ABOVE the anchor; "
            f"with amenity groundskeeping ~"
            f"{reports['with_amenity']['ratio_to_anchor']:.0f}× above it. The "
            f"measurement is not what is unresolved — the definition is. Do not "
            f"quote a single stewardship intensity for the US. "
            f"AND UNDER PHASE 4f (ADOPTED 2026-08-28) NEITHER FIGURE BELONGS "
            f"IN THE ECOLOGICAL DOMAIN: these hours are GUF's recurring charge. "
            f"The anchor comparison above is retained because it is what this "
            f"census was built to make, but it now answers a question the "
            f"partition has closed — read it as evidence about GUF's target, "
            f"not about ECOLOGICAL_BASE_RATE."
        ),
    }
