"""
The US by state — land use (ERS 2022) and resident population (Census 2025).

SPDX-License-Identifier: AGPL-3.0-or-later

Measured data, keyed by the state FIPS the parcel extract uses. Ingest:
`utils/state_ingest.py` over ERS Major Land Uses summary tables 1 and 5 and the
Census SCPRC-EST2025 state estimates, all in `rawdata/` (gitignored).

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

WHAT IT IS NOT. No state age mix, labour capacity, capital stock or ε: none
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


def us_state_split() -> dict[str, Any]:
    """
    The US frame divided into its 49 units — the 48 and DC — as a split file
    (`utils/frame_inputs.load_split`): each unit's measured population, land
    and private parcels. A split states how a frame DIVIDES; the frame states
    how much there is, so each unit runs on its SHARE of the frame's totals.
    """
    parcels = private_parcels_by_state()
    units = [{"id": s["statefp"], "label": s["state"],
              "population": s["population"],
              "land_hectares": round(sum(s["land_hectares"].values()), 1),
              "parcel_count": round(parcels[s["statefp"]]["central"], 1)}
             for s in load_states() if s["in_48_states"]]
    return {
        "name": "us_states",
        "frame": "us",
        "note": ("The contiguous 48 and DC, by state. population: " + POPULATION_SOURCE
                 + ". land_hectares: " + LAND_SOURCE + ", total land. parcel_count: "
                 "the county parcel census's PRIVATE parcels, unknown owner types "
                 "split like each state's known ones. Each is a WEIGHT: a unit runs "
                 "on its share of the frame's population, land and parcels, and on "
                 "its population share of the frame's capital and Trust. Age mix, "
                 "labour capacity, stock age, ecosystem health and epsilon are the "
                 "frame's: none ships by state."),
        "collectives": units,
    }
