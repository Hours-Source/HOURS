"""
The US parcel census, at county resolution — measured data, no domain imports.

SPDX-License-Identifier: AGPL-3.0-or-later

WHAT THIS IS FOR. `scenarios/use_split` established that the Ground Use Fee has
ONE scaling basis while the measured servicing cost has three — area 41.9%,
parcel 44.5%, throughput 13.6% — and that the 44.5% following PARCEL COUNT is
inexpressible in a per-SLU fee. `guf_magnitude.subdivision_invariance` proves
the point by splitting every parcel in two and getting the same fee back to the
float: parcel count does not enter the fee at all.

Closing that needs a per-parcel TERM, and a term needs a denominator. This is
the denominator: **160,573,137 parcels across 3,230 counties**, which is what
`PARCEL_COUNT_RESOLVES_BY` named — *"assessor parcel rolls, and explicitly NOT a
housing-unit count."*

WHAT IT IS NOT. It supplies the DENOMINATOR, not the numerator. A per-parcel
servicing cost is hours ÷ parcels; the hours come from
`scenarios/servicing_census`. And it carries NO use-category mapping, because
the census's `usedesc` is 41.2% filled and is free text from 3,230 independent
county systems — normalising it is a separate project with a real judgement in
it, and bundling a judgement into a count would make the count unciteable.

THE AREA COLUMN OVER-COUNTS LAND AND THE MODULE SAYS SO IN THREE PLACES. Summed
parcel footprints exceed the land area of six of twelve checked states — Florida
by 31%, Texas by 16% — because footprints overlap in developed areas, while
federal-land-heavy states under-count because that land is thinly parcelised.
`stackid` is populated on 0.2% of Florida rows and cannot explain it, so the
residual cause is unidentified. `land_area_validation()` reports the ratio per
state rather than leaving the limitation in prose only.

Ingest: `utils/parcel_ingest.py` over the 68 GB raw file in `rawdata/parcels/`,
which is gitignored exactly as the 2.9 GB ATUS microdata is.

Layer note: `reference/` imports nothing from the package — pure data.
"""

from __future__ import annotations

import csv
import pathlib

__all__ = [
    "DATA_FILE",
    "NUMUNITS_CAP_SENSITIVITY",
    "NUMUNITS_COLUMN_LEAKS",
    "NUMUNITS_EXCLUDED_COUNTIES",
    "NUMUNITS_NATIONAL_TOTAL",
    "NUMUNITS_RETAINED_TOTAL",
    "US_HOUSING_UNITS_2020",
    "service_point_denominator_verdict",
    "PARCEL_VINTAGE",
    "STATE_LAND_AREA_KM2",
    "load_county_parcels",
    "county_count",
    "national_parcel_count",
    "parcels_by_state",
    "land_area_validation",
]

DATA_FILE = pathlib.Path(__file__).with_name("data") / "parcel_county_counts.csv"

#: The raw file this was derived from. Named so a refreshed vintage is a visible
#: change rather than a silent one.
PARCEL_VINTAGE = "NATIONWIDE_SAMPLE_Q3_R2"

#: Published LAND area by state, km² (US Census gazetteer). Carried ONLY to
#: validate the parcel-footprint sum against something external — this module
#: makes no use of it otherwise, and it is deliberately a partial list: twelve
#: states spanning the developed/federal spectrum is enough to establish the
#: direction and magnitude of the over-count without implying the extract has
#: been validated everywhere.
STATE_LAND_AREA_KM2: dict[str, float] = {
    "02": 1_477_953.0,  # AK — federal-heavy, thinly parcelised
    "06":   403_466.0,  # CA
    "12":   138_887.0,  # FL — worst over-count
    "17":   143_793.0,  # IL
    "30":   376_962.0,  # MT
    "36":   122_057.0,  # NY
    "37":   125_920.0,  # NC
    "39":   105_829.0,  # OH
    "42":   115_883.0,  # PA
    "48":   676_587.0,  # TX
    "49":   212_818.0,  # UT — federal-heavy
    "56":   251_470.0,  # WY — federal-heavy
}

_M2_PER_KM2 = 1.0e6

#: US housing units, 2020 decennial census — carried ONLY as the external
#: yardstick for the measurement below, not used by anything else.
US_HOUSING_UNITS_2020 = 140_498_736

#: WHY `numunits` IS NOT SHIPPED, measured rather than asserted (2026-08-30).
#:
#: `scenarios/use_split` proposed splitting the per-parcel term in two —
#: `P_title` per legal parcel (deed, assessment, boundary) and `P_service` per
#: SERVICE POINT (refuse, metering, inspection), because consolidating a
#: hundred apartments into one parcel removes a hundred deeds but not one
#: refuse collection. `P_title`'s denominator is the parcel count this module
#: ships. `P_service`'s would be a count of units, and `numunits` cannot supply
#: one.
#:
#: Coverage is 47.6%, and that is NOT the binding problem — it is bounded and
#: could be reasoned about. Populated values sum to **52,780,834,579 units**,
#: 364× the US housing stock, and the largest single parcel claims
#: **612,196,539 units** — nearly twice the US population, on one parcel.
#:
#: THE TABLE IS THE FINDING. Each row is (cap, rows above it, units summed
#: below it). Excluding a few hundredths of a percent of rows moves the
#: national total across an order of magnitude — `service_point_denominator_
#: verdict()` computes the exact span rather than restating it here, because a
#: figure written in prose beside a table that produces it is how this repo's
#: stale claims have started:
#:
#:     cap 1,000  →  0.9× the housing stock   ← plausible, and that is the trap
#:     cap 10,000 →  1.9×
#:     no cap     →  364×
#:
#: A cap of 1,000 produces an answer close to the truth. **Choosing it because
#: it produces that answer is fitting to a target**, which is the failure this
#: repo has named in `DEFAULT_SEGMENTS` (means set so the weighted mean hit the
#: band ceiling) and `GUF_USE_SCALE_FACTOR` (scaled so aggregate GUF matched
#: levy revenue). No principled cap exists here, so no cap is adopted and no
#: units column is shipped.
NUMUNITS_CAP_SENSITIVITY: tuple[tuple[int, int, int], ...] = (
    #  cap,     rows above,   units summed below the cap
    (       10,    503_736,      80_643_748),
    (      100,    197_896,      93_540_738),
    (    1_000,     88_052,     128_058_785),
    (   10_000,     37_242,     280_590_381),
    (  100_000,     26_508,     649_540_503),
    (1_000_000,     23_320,   1_719_437_954),
)

#: THE MECHANISM, IDENTIFIED (2026-08-30). The tail is not a heavy tail of a
#: real distribution — it is **other columns**, pasted into `numunits` one
#: county at a time. Each entry is (fips, county, what the column actually
#: holds), and each was established by arithmetic, not inferred from size:
#:
#:   * **Camden NJ** — the single constant 2,040,202 on 22,342 rows, identical
#:     to the digit. That one value is **86.4% of the entire national sum**
#:     (2,040,202 × 22,342 = 45,582,193,084, exact). The county's other 177,200
#:     populated rows say `1` and look perfectly normal.
#:   * **Lee FL** — the parcel's own LAND AREA, at two different scales in the
#:     same county: square feet on 18,532 rows and hundredths of a square foot
#:     on 1,097. The record holder is parcel 14452400000060010, a 140.542-acre
#:     college campus at 8051–8099 College Pkwy, Fort Myers, whose 6,121,965
#:     sq ft becomes `numunits = 612,196,539`. Ratio 100.00 across the top 20,
#:     the scatter explained entirely by `taxacres` rounding to 3 dp.
#:   * **Perry PA** — BUILDING square footage: 1,232 / 1,120 / 1,344 / 1,680,
#:     each repeated hundreds of times. Standard house and double-wide sizes.
#:
#: WHY IT PROPAGATES, and it is the general lesson rather than a fact about
#: these three: the corruption is COUNTY-SCOPED, which is the signature of an
#: aggregation pipeline mapping 3,230 independent county schemas onto one
#: national schema. Every individual value is a plausible integer, so a spot
#: check finds nothing; only the aggregate exposes it, and nobody sums a unit
#: count because Census publishes that. `ownername` is the string
#: `'www.landrecords.us'` on **all 160,573,137 rows**, which says the file has
#: been through at least one commercial repackager — and anything downstream
#: inherits whatever that repackager did or did not check.
NUMUNITS_COLUMN_LEAKS: tuple[tuple[str, str, str], ...] = (
    ("34007", "Camden NJ",  "broadcast fill: 2,040,202 on 22,342 rows"),
    ("12071", "Lee FL",     "land area, in sq ft and in hundredths of a sq ft"),
    ("42099", "Perry PA",   "building square footage"),
)

#: MECHANISM-BASED EXCLUSION, and it is a genuinely different instrument from
#: the cap. A county is excluded where the column can be SHOWN to carry another
#: quantity — a value repeated on ≥1% of rows, or ≥1% of rows matching parcel
#: area or building area to within 2%. **The rule was declared before its
#: outcome was seen**, because choosing exclusions by size is the cap trap at
#: county resolution.
#:
#: It removes **15 counties of 3,230, retaining 98.9% of parcels**, and the
#: national total falls 52,780,834,579 → 227,681,616, a factor of 232. Against
#: the housing stock that is 1.62×, which is the right side of plausible: the
#: field counts commercial suites and retail bays as well as dwellings, so a
#: total above the residential stock is expected.
#:
#: HAND-INSPECTION FOUND THE BIGGEST FOUR; THE RULE FOUND FIFTEEN — including
#: Winchester VA at a 69.5% building-area leak and Milwaukee WI at 16.0% area.
#: **And it is deliberately not exhaustive**: Brevard FL's ~1,400 rows carrying
#: a 9,000-series code sit below the 1% threshold and are RETAINED. A rule
#: loosened until it caught them would be tuned to a target.
NUMUNITS_EXCLUDED_COUNTIES = 15
NUMUNITS_COUNTIES = 3_230
NUMUNITS_RETAINED_PARCELS = 158_833_466
NUMUNITS_RETAINED_TOTAL = 227_681_616
#: The uncleaned sum of every populated `numunits`, over all 3,230 counties.
NUMUNITS_NATIONAL_TOTAL = 52_780_834_579

#: Parcels carrying buildings but NO unit count — genuinely missing data, as
#: distinct from parcels with neither, where zero service points is arguable.
#: 34,428,480 of 108,969,030 built parcels: **31.6% of parcels that have a
#: structure do not say how many units it holds.**
#:
#: THE PAIR BELOW IS THE POINT. Before exclusion 34,428,480/108,969,030 =
#: 31.59%; after excluding all 15 contaminated counties, 33,939,651/107,388,156
#: = **31.61%**. The two defects are ORTHOGONAL — cleaning the tail moves the
#: coverage gap by two hundredths of a percentage point. Whatever the exclusion
#: buys, it does not buy a numerator.
NUMUNITS_MISSING_ON_BUILT_PARCELS = 34_428_480
NUMUNITS_BUILT_PARCELS = 108_969_030
NUMUNITS_MISSING_ON_BUILT_RETAINED = 33_939_651
NUMUNITS_BUILT_PARCELS_RETAINED = 107_388_156

#: AND THE GAP CANNOT BE IMPUTED, which is what stops the cleaned total being a
#: BAND rather than a floor. The missingness is county-clustered — 745 counties
#: populate under 5% of their built parcels, 765 populate over 95% — so the
#: obvious move is to take the rate from the counties that do populate and
#: apply it to those that do not.
#:
#: Measured, that rate is **3.806 units per built parcel** over 42,508,240
#: built parcels in the ≥95%-populated counties. Applied to all 107,388,156
#: retained built parcels it gives ~409 million units, **2.9× the US housing
#: stock** — which no amount of commercial floor space explains. The counties
#: that populate the field are denser than the ones that do not, so the rate is
#: measured exactly where it is least transferable. **A rate measured on a
#: self-selected subsample is not a national rate**, and using it anyway is the
#: coverage-inflation trap `scenarios/land_stewardship` guards against: a class
#: priced on part of its labour reading as fully priced.
#:
#: So the cleaned figure is a LOWER BOUND with an unquantified gap above it,
#: not a band. In this repo's tag vocabulary that fails `bounded`, which
#: requires a MEASURED band — the upper end here is extrapolated under an
#: assumption already known to be false.
NUMUNITS_WELL_POPULATED_BUILT = 42_508_240
NUMUNITS_WELL_POPULATED_UNITS = 161_787_279


def load_county_parcels() -> list[dict[str, float | str]]:
    """
    The shipped extract, one row per county.

    Columns: `statefp`, `countyfp` (strings, FIPS with leading zeros preserved);
    `parcels`, `area_parcels`, `government_parcels`, `ownertype_known` (ints);
    `area_m2` (float, square metres of parcel FOOTPRINT — see the module
    docstring on why that is not land area).
    """
    out: list[dict[str, float | str]] = []
    with DATA_FILE.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({
                "statefp":            r["statefp"],
                "countyfp":           r["countyfp"],
                "parcels":            int(r["parcels"]),
                "area_m2":            float(r["area_m2"]),
                "area_parcels":       int(r["area_parcels"]),
                "government_parcels": int(r["government_parcels"]),
                "ownertype_known":    int(r["ownertype_known"]),
            })
    return out


def county_count() -> int:
    """Counties in the extract. The US has ~3,143 plus territory equivalents."""
    return len(load_county_parcels())


def national_parcel_count() -> int:
    """
    Total parcels — the per-parcel term's denominator.

    Summed from the rows rather than shipped as a constant: a stored total is a
    second copy of a value whose source is elsewhere, which is the pattern this
    repo has found five times.
    """
    return sum(int(r["parcels"]) for r in load_county_parcels())


def parcels_by_state() -> dict[str, int]:
    """Parcel counts keyed by state FIPS."""
    out: dict[str, int] = {}
    for r in load_county_parcels():
        out[str(r["statefp"])] = out.get(str(r["statefp"]), 0) + int(r["parcels"])
    return out


def land_area_validation() -> list[dict[str, float | str]]:
    """
    Summed parcel footprint against published land area, per state.

    Governing comparison:

        ratio(state) = Σ area_m2 / (land_area_km2 × 1e6)

    A ratio above 1 means the footprints sum to MORE than the state contains,
    which is only possible if they overlap. Six of the twelve states carried
    here exceed 1.0.

    THE RESULT IS REPORTED, NOT CORRECTED. The cause is unidentified —
    `stackid`, which marks condominium units sharing a footprint, is populated
    on 0.2% of Florida rows and cannot account for a 31% over-count — so
    "fixing" the number would be fitting rather than measuring. What the module
    can honestly do is make the limitation checkable, which is what this is.
    """
    area: dict[str, float] = {}
    for r in load_county_parcels():
        s = str(r["statefp"])
        area[s] = area.get(s, 0.0) + float(r["area_m2"])

    rows: list[dict[str, float | str]] = []
    for fips, km2 in sorted(STATE_LAND_AREA_KM2.items()):
        summed = area.get(fips, 0.0)
        actual = km2 * _M2_PER_KM2
        rows.append({
            "statefp":        fips,
            "summed_m2":      summed,
            "land_area_m2":   actual,
            "ratio":          summed / actual,
            "exceeds_land":   summed > actual,
        })
    return rows


def service_point_denominator_verdict() -> dict[str, float | str | bool]:
    """
    Whether `P_service` is buildable from this census. It is not.

    Governing comparison — the national units total under each exclusion cap,
    against the 2020 housing stock:

        ratio(cap) = Σ numunits[numunits ≤ cap] / US_HOUSING_UNITS_2020

    Returns the span of that ratio across the caps in
    `NUMUNITS_CAP_SENSITIVITY`. A denominator whose value depends on an
    unprincipled exclusion threshold is not a measurement, and the span is how
    far it can be moved — by excluding between 0.03% and 0.66% of rows. The
    span is COMPUTED and returned, not restated in prose: a figure written
    beside the table that produces it is how a claim goes stale.

    THE PLAUSIBLE ANSWER IS THE TRAP. A cap of 1,000 gives 0.9× the housing
    stock — close enough to look settled. Adopting it on that basis is fitting
    to a target, and this repo has been caught by that twice already.

    What would settle `P_service` is an EXTERNAL service-point count. Census
    housing-unit estimates by county are published, authoritative, and do not
    depend on this file at all — though they cover only the residential share,
    and commercial service points remain a separate gap.
    """
    ratios = [units / US_HOUSING_UNITS_2020 for _, _, units in NUMUNITS_CAP_SENSITIVITY]
    lo, hi = min(ratios), max(ratios)
    imputed = (NUMUNITS_WELL_POPULATED_UNITS / NUMUNITS_WELL_POPULATED_BUILT
               * NUMUNITS_BUILT_PARCELS_RETAINED)
    return {
        "buildable":          False,
        "coverage":           0.476,
        "ratio_span":         hi / lo,
        "ratio_min":          lo,
        "ratio_max":          hi,
        "missing_on_built":   NUMUNITS_MISSING_ON_BUILT_PARCELS / NUMUNITS_BUILT_PARCELS,
        # --- the mechanism-based exclusion, which is NOT the cap -------------
        "excluded_counties":  NUMUNITS_EXCLUDED_COUNTIES,
        "parcels_retained":   NUMUNITS_RETAINED_PARCELS / 160_573_137,
        "cleaned_total":      NUMUNITS_RETAINED_TOTAL,
        "cleaned_ratio":      NUMUNITS_RETAINED_TOTAL / US_HOUSING_UNITS_2020,
        "cleaned_reduction":  NUMUNITS_NATIONAL_TOTAL / NUMUNITS_RETAINED_TOTAL,
        # the gap the exclusion does NOT touch
        "missing_on_built_retained": (NUMUNITS_MISSING_ON_BUILT_RETAINED
                                      / NUMUNITS_BUILT_PARCELS_RETAINED),
        "imputed_ratio":      imputed / US_HOUSING_UNITS_2020,
        "imputable":          False,
        "verdict": (
            f"P_service is NOT buildable from `numunits`. Coverage is 47.6% and "
            f"that is not the binding problem; the field carries OTHER COLUMNS "
            f"— land area, building area, a broadcast constant — pasted in one "
            f"county at a time, summing to 364× the US housing stock "
            f"with one parcel claiming 612 million units. The national total "
            f"moves across a {hi / lo:.0f}× range depending on an exclusion cap "
            f"that nothing justifies, and the cap giving a plausible answer "
            f"(1,000 → 0.9×) would be chosen BECAUSE it is plausible, which is "
            f"fitting. A further "
            f"{NUMUNITS_MISSING_ON_BUILT_PARCELS / NUMUNITS_BUILT_PARCELS:.1%} "
            f"of parcels that HAVE a structure carry no unit count at all. "
            f"P_title is buildable now; P_service needs an external "
            f"service-point count. Excluding the "
            f"{NUMUNITS_EXCLUDED_COUNTIES} counties whose column is SHOWN to "
            f"carry another quantity cleans the tail decisively — "
            f"{NUMUNITS_RETAINED_PARCELS / 160_573_137:.1%} of parcels "
            f"retained, the total down "
            f"{NUMUNITS_NATIONAL_TOTAL / NUMUNITS_RETAINED_TOTAL:.0f}x to "
            f"{NUMUNITS_RETAINED_TOTAL / US_HOUSING_UNITS_2020:.2f}x the "
            f"housing stock — but it does not touch the missing numerator "
            f"({NUMUNITS_MISSING_ON_BUILT_RETAINED / NUMUNITS_BUILT_PARCELS_RETAINED:.1%} "
            f"of built parcels still carry no count, against "
            f"{NUMUNITS_MISSING_ON_BUILT_PARCELS / NUMUNITS_BUILT_PARCELS:.1%} "
            f"before), and the gap cannot be imputed: the populating counties "
            f"give {imputed / US_HOUSING_UNITS_2020:.1f}x the housing stock. "
            f"The cleaned figure is a LOWER BOUND, not a band."
        ),
    }
