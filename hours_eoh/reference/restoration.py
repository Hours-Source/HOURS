"""
Restoration cost from physics — labour-hours to return a hectare to function.

Phase 3 of notes/guf-restoration-derivation.md. This is the quantity a
reset-cost derivation of GUF's ecological term needs, and it is derived the only
way that has worked in this repo: ASAE field capacity, `width × speed ×
efficiency`, with no price anywhere in the chain.

WHY NOT A PROJECT-COST DATABASE. Four instruments have already failed here, and
each failed differently, which is how the remaining gap became well-posed:

  NRCS EQIP payment schedules   fail on UNITS  — no time unit and no labour line
                                in 2,691 rows; the dollar column mixes
                                implementation cost with foregone income.
  Extension enterprise budgets  fail on SCOPE  — crop PRODUCTION hours.
  Raw agency headcount          fails on ROLE MIX — overstates 4.4×.
  ASAE field capacity           WORKS.

Restoration-project cost databases share EQIP's defect exactly: they report
dollars, and the labour share of a restoration dollar is neither published nor
constant. So they are not used here. The repo's own rule applies — *a
`resolves_by` that names a SOURCE without naming the FIELD in it that carries
the quantity has not been checked.*

WHAT THIS PRICES, AND WHAT IT REFUSES TO
----------------------------------------
A restoration is a SEQUENCE of field operations, and the ASAE table covers the
ones done with agricultural machinery: site preparation, drilling seed, packing,
establishment mowing, spot spraying. Grassland and old-field restoration are
therefore fully derivable.

Three classes are NOT, and they are EXCLUDED rather than costed at zero — the
discipline `reference/personal_basket.py` holds when it prices one basket
component of seven, and `land_stewardship` when it covers 38.1% of area:

  tree planting          hand labour with no implement in the standard
  wetland hydrology      earthworks; excavator productivity is not an ASAE
                         field operation and the standard does not cover it
  monitoring             recurring observation, not a field pass

`UNPRICED_RESTORATION` carries each with its reason and what would settle it.

THE ONE-OFF / RECURRING SPLIT. Establishment is a one-time cost; the
establishment-phase mowing and spraying recur for a stated number of years and
then stop. Both are reported separately, because amortising them together over
a restoration horizon hides which is which.

Layer: reference/ — pure data and derivation; imports nothing from the package
outside this layer.
"""

from __future__ import annotations

from hours_eoh.reference.land_stewardship import ACRE_HECTARES, hours_per_acre

#: Restoration sequences, as passes of named ASAE implements at stated widths.
#:
#: Each entry is (implement, width_ft, passes, phase). `phase` is "establishment"
#: for the one-off conversion or "aftercare" for the repeated passes over the
#: establishment years.
#:
#: WIDTHS ARE SUPPLIED, NOT MEASURED — the same honest shape `hours_per_acre`
#: carries. Hours per hectare fall as the machine widens, so this is a DELIVERY
#: PRODUCTIVITY at a stated equipment scale, not a physical constant. Widths
#: here are mid-range North American equipment, matching
#: PRACTICE_EQUIPMENT_WIDTHS_FT's declared basis.
RESTORATION_SEQUENCES: dict[str, dict] = {
    "grassland_seeding": {
        "label": "Grassland / prairie seeding on retired cropland",
        "aftercare_years": 3,
        "operations": (
            ("disk",                     12.0, 2, "establishment"),
            ("grain_drill",              15.0, 1, "establishment"),
            ("roller_packer",            12.0, 1, "establishment"),
            ("mower_conditioner_rotary", 12.0, 1, "aftercare"),
            ("boom_sprayer",             45.0, 1, "aftercare"),
        ),
        "basis": (
            "Conversion of tilled ground to perennial cover: two disking passes "
            "to break the existing sward and prepare a seedbed, one drilled "
            "seeding, one packing pass for seed-to-soil contact, then one "
            "mowing and one spot-spray pass per aftercare year to suppress "
            "annual weeds while perennials establish. Every operation is an "
            "ASAE field operation at a stated width."
        ),
    },
    "old_field_succession": {
        "label": "Old-field succession management (no seedbed preparation)",
        "aftercare_years": 5,
        "operations": (
            ("boom_sprayer",             45.0, 1, "establishment"),
            ("mower_conditioner_rotary", 12.0, 1, "aftercare"),
        ),
        "basis": (
            "The minimum-intervention path: no tillage and no seeding, one "
            "knock-down pass, then annual mowing to hold succession open while "
            "native cover returns from the seed bank. Included as the LOWER "
            "corner of what restoration can cost, so the range is bounded from "
            "below by something real rather than by zero."
        ),
    },
}

#: Restoration classes the field-capacity route CANNOT price, with the reason
#: and what would settle each. Excluded, never costed at zero.
UNPRICED_RESTORATION: tuple[dict, ...] = (
    {
        "class": "tree_planting",
        "reason": (
            "Hand labour with no implement in the ASAE standard. Field capacity "
            "is defined for machine passes; a planting crew's productivity is a "
            "different quantity with a different form."
        ),
        "resolves_by": (
            "Published planting-crew productivity in SEEDLINGS PER PERSON-DAY "
            "(USDA Forest Service reforestation guidance reports it directly), "
            "combined with a stocking density in seedlings per hectare. Both are "
            "counts, so the chain stays currency-free — the property that makes "
            "field capacity usable."
        ),
    },
    {
        "class": "wetland_hydrology",
        "reason": (
            "Earthworks. Excavator and scraper productivity is volumetric "
            "(m³/hour) and depends on haul distance and material, none of which "
            "is an ASAE field operation. The standard does not cover it and "
            "borrowing a neighbouring implement's efficiency would be the "
            "guessing this module exists to refuse."
        ),
        "resolves_by": (
            "Earthmoving production rates in CUBIC METRES PER MACHINE-HOUR by "
            "material class (the Caterpillar Performance Handbook publishes them "
            "as a field), with a per-hectare earthwork volume from a restoration "
            "design. Same shape as field capacity: a rate and a quantity, no "
            "price in the chain."
        ),
    },
    {
        "class": "monitoring",
        "reason": (
            "Recurring observation rather than a field pass. It has no width and "
            "no speed, so the governing equation does not apply to it at all."
        ),
        "resolves_by": (
            "Survey protocol staffing — plots per person-day and plots per "
            "hectare — from a monitoring design. Note this is the same quantity "
            "`monitoring_capability` scales in the ecological domain, so pricing "
            "it connects two layers that currently do not meet."
        ),
    },
)


def restoration_hours_per_hectare(sequence: str) -> dict:
    """
    One-off and recurring labour to restore a hectare, as a band.

    Governing equation, per operation:

        hours/ha = passes × (1 / EFC) × (1 / ACRE_HECTARES)

    where EFC is the ASAE effective field capacity in acres per hour, evaluated
    at both corners of the standard's speed and efficiency ranges. The LOW
    corner is fast-and-efficient; the HIGH corner is slow-and-inefficient.

    units: labour-hours per hectare. `establishment_*` is one-off;
    `aftercare_*_per_year` recurs for `aftercare_years` and then stops.

    Worked example — grassland_seeding: two disking passes at 12 ft, one 15 ft
    drilled seeding and one packing pass give roughly 1.0–2.6 h/ha of
    establishment, with about 0.4–1.0 h/ha·yr of aftercare for three years.
    Total lifetime cost is therefore a few hours per hectare, NOT the hundreds
    a restoration's DOLLAR cost might suggest — because most of that dollar is
    seed, plant material and design, none of which is labour.

    Raises:
        KeyError: on an unknown sequence.
    """
    if sequence not in RESTORATION_SEQUENCES:
        raise KeyError(
            f"unknown restoration sequence {sequence!r}; have "
            f"{sorted(RESTORATION_SEQUENCES)}"
        )
    spec = RESTORATION_SEQUENCES[sequence]

    totals = {
        "establishment": {"low": 0.0, "high": 0.0},
        "aftercare":     {"low": 0.0, "high": 0.0},
    }
    breakdown = []
    for implement, width_ft, passes, phase in spec["operations"]:
        per_acre = hours_per_acre(implement, width_ft)
        low = passes * per_acre["hours_per_acre_low"] / ACRE_HECTARES
        high = passes * per_acre["hours_per_acre_high"] / ACRE_HECTARES
        totals[phase]["low"] += low
        totals[phase]["high"] += high
        breakdown.append({
            "implement":   implement,
            "label":       per_acre["label"],
            "width_ft":    width_ft,
            "passes":      passes,
            "phase":       phase,
            "h_per_ha_low":  low,
            "h_per_ha_high": high,
        })

    years = spec["aftercare_years"]
    lifetime_low = totals["establishment"]["low"] + totals["aftercare"]["low"] * years
    lifetime_high = totals["establishment"]["high"] + totals["aftercare"]["high"] * years

    return {
        "sequence":        sequence,
        "label":           spec["label"],
        "basis":           spec["basis"],
        "operations":      breakdown,
        "aftercare_years": years,
        "establishment_h_per_ha_low":  totals["establishment"]["low"],
        "establishment_h_per_ha_high": totals["establishment"]["high"],
        "aftercare_h_per_ha_year_low":  totals["aftercare"]["low"],
        "aftercare_h_per_ha_year_high": totals["aftercare"]["high"],
        "lifetime_h_per_ha_low":  lifetime_low,
        "lifetime_h_per_ha_high": lifetime_high,
    }
