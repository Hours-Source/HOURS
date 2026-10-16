"""
The US by state — land use (ERS 2022) and resident population (Census 2025).

SPDX-License-Identifier: AGPL-3.0-or-later

Measured data, keyed by the state FIPS the parcel extract uses. Ingest:
`utils/state_ingest.py` over ERS Major Land Uses summary tables 1 and 5 and the
Census SCPRC-EST2025 state estimates; `utils/state_age_ingest.py` over the
Census SC-EST2025-ALLDATA6 single-year ages. All in `rawdata/` (gitignored).

WHAT IT IS FOR. The US frame divided into its states (`us_state_split`): a
federation needs each member's people, land and parcels, and the repo held
parcels by state and nothing else. The same table gives the contiguous 48's
OWN land-use mix (`contiguous_48_land_hectares_by_class`), where the frame had
applied the 50-state shares with Alaska's forest and miscellaneous land in them.

SCOPE IS THE SOURCE'S. `in_48_states` marks the rows ERS's own "48 States"
line sums — the 48 and DC — which is `US_MAINLAND_HECTARES`' source line, so the
frame's land and its states' land are one measurement. ERS publishes whole
thousands of acres and says its distributions "may not add to totals due to
rounding"; the ingest prints each gap (at most 4 thousand acres a class).

EACH STATE'S AGE MIX IS ITS OWN (2026-10-15): `state_population_shares` groups
the state's resident ages, as `care_demand.population_shares` groups the
nation's. The state file top-codes at 85, the national at 100, so a band
starting above 85 is refused rather than read as empty.

WHAT IT IS NOT. No state labour capacity, capital stock, stock age or ε: none
ships by state, so a state split carries the frame's (`us_state_split` says
which in its note). BEA publishes no state capital stock at all.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from hours_eoh.reference.land_stewardship import ACRE_HECTARES, land_hectares_by_class
from hours_eoh.reference.parcels import private_parcels_by_state

DATA_FILE = Path(__file__).parent / "data" / "state_land_population.csv"
AGE_FILE = Path(__file__).parent / "data" / "state_age_2025.csv"
#: The state age file's top-coded age: 85 means "85 and over".
AGE_TOP = 85

AGE_SOURCE = ("Census Bureau, Population Division, SC-EST2025-ALLDATA6: resident "
              "population by single year of age, July 1, 2025")
POPULATION_SOURCE = ("Census Bureau, Population Division, SCPRC-EST2025-18+POP: "
                     "resident population, July 1, 2025")
LAND_SOURCE = "USDA ERS Major Land Uses 2022, summary tables 1 and 5 (by state)"

#: ERS publishes thousands of acres.
ACRES_PER_KACRE = 1_000.0

_FIXED = ("statefp", "state", "in_48_states", "population_2025")


def load_states() -> list[dict[str, Any]]:
    """
    The 50 states and DC: `statefp`, `state`, `in_48_states` (bool),
    `population` (persons, 2025) and `land_hectares` ({ERS class: ha}, the nine
    classes `land_stewardship.land_hectares_by_class` names).
    """
    classes = set(land_hectares_by_class())
    with DATA_FILE.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows and set(rows[0]) - set(_FIXED) != classes:
        raise ValueError(f"{DATA_FILE}: land columns must be exactly {sorted(classes)}")
    return [{"statefp": r["statefp"], "state": r["state"],
             "in_48_states": r["in_48_states"] == "1",
             "population": int(r["population_2025"]),
             "land_hectares": {c: float(r[c]) * ACRES_PER_KACRE * ACRE_HECTARES for c in classes}}
            for r in rows]


def contiguous_48_land_hectares_by_class() -> dict[str, float]:
    """{ERS class: ha} summed over the 48 and DC — the US frame's own land mix."""
    out = dict.fromkeys(land_hectares_by_class(), 0.0)
    for s in load_states():
        if s["in_48_states"]:
            for c, ha in s["land_hectares"].items():
                out[c] += ha
    return out


def _state_ages() -> dict[str, dict[int, int]]:
    out: dict[str, dict[int, int]] = {}
    with AGE_FILE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["statefp"], {})[int(r["age"])] = int(r["population"])
    return out


def _shares(ages: dict[int, int], bands: dict[str, tuple[int, int]]) -> dict[str, float]:
    total = sum(ages.values())
    return {name: sum(ages.get(a, 0) for a in range(lo, min(hi, AGE_TOP) + 1)) / total
            for name, (lo, hi) in bands.items()}


def _refuse_above_top(bands: dict[str, tuple[int, int]]) -> None:
    above = sorted(n for n, (lo, _) in bands.items() if lo > AGE_TOP)
    if above:
        raise ValueError(f"{AGE_FILE.name} top-codes at {AGE_TOP}; bands {above} start above it")


def state_population_shares(bands: dict[str, tuple[int, int]]) -> dict[str, dict[str, float]]:
    """{statefp: {band: share of the state's residents}} — each state's own
    age mix, 2025, grouped to `bands` (the caller's, e.g. AGE_GROUP_RANGES)."""
    _refuse_above_top(bands)
    return {fp: _shares(ages, bands) for fp, ages in _state_ages().items()}


def contiguous_48_population_shares(bands: dict[str, tuple[int, int]]) -> dict[str, float]:
    """The 48 and DC's age mix — the US frame's people, where the frame reads
    the NATIONAL mix (50 states and DC). Reported beside it, not applied."""
    _refuse_above_top(bands)
    ages = _state_ages()
    pooled: dict[int, int] = {}
    for s in load_states():
        if s["in_48_states"]:
            for a, n in ages[s["statefp"]].items():
                pooled[a] = pooled.get(a, 0) + n
    return _shares(pooled, bands)


def us_state_split(age_bands: dict[str, tuple[int, int]]) -> dict[str, Any]:
    """
    The US frame divided into its 49 units — the 48 and DC — as a split file
    (`utils/frame_inputs.load_split`): each unit's measured population, land
    and private parcels, and its own age mix grouped to `age_bands`. A split
    states how a frame DIVIDES; the frame states how much there is, so each
    unit runs on its SHARE of the frame's totals — except the age mix, which
    is a composition, not a quantity, and replaces the frame's.
    """
    parcels = private_parcels_by_state()
    ages = state_population_shares(age_bands)
    units = [{"id": s["statefp"], "label": s["state"],
              "population": s["population"],
              "land_hectares": round(sum(s["land_hectares"].values()), 1),
              "parcel_count": round(parcels[s["statefp"]]["central"], 1),
              "age_fractions": ages[s["statefp"]]}
             for s in load_states() if s["in_48_states"]]
    return {
        "name": "us_states",
        "frame": "us",
        "note": ("The contiguous 48 and DC, by state. population: " + POPULATION_SOURCE
                 + ". land_hectares: " + LAND_SOURCE + ", total land. parcel_count: "
                 "the county parcel census's PRIVATE parcels, unknown owner types "
                 "split like each state's known ones. Each is a WEIGHT: a unit runs "
                 "on its share of the frame's population, land and parcels, and on "
                 "its population share of the frame's capital and Trust. "
                 "age_fractions: " + AGE_SOURCE + ", the unit's own mix, in place "
                 "of the frame's. Labour capacity, stock age, ecosystem health and "
                 "epsilon are the frame's: none ships by state."),
        "collectives": units,
    }
