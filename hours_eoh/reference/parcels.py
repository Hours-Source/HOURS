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
