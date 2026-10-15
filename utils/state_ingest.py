"""
State land use and population → the shipped state extract.

SPDX-License-Identifier: AGPL-3.0-or-later

Run this ONCE when a source changes; the repo ships only the CSV it writes. The
sources are small and live in `rawdata/` (gitignored), as every raw file does:

    rawdata/ers_mlu/summary_table_1_2022.xlsx   ERS Major Land Uses, Summary
        table 1 — major uses of land by state, 2022 (1,000 acres)
    rawdata/ers_mlu/summary_table_5_2022.xlsx   Summary table 5 — special uses
        by state, 2022: the four classes table 1 folds into "Special-use areas"
    rawdata/age/SCPRC-EST2025-18+POP.csv        Census resident population by
        state, July 1, 2025

    python3 utils/state_ingest.py [--raw rawdata] [--out hours_eoh/reference/data]

Output (committed):
    state_land_population.csv   statefp, state, in_48_states, population_2025,
                                then one column per ERS class (1,000 acres),
                                named as `mlu_land_use_2022.csv` names them

WHY: a federation of the US frame's states needs each state's people, land and
parcels; the repo held parcels by state and nothing else. The same table gives
the contiguous 48's OWN land-use mix, where the frame had applied the 50-state
shares (Alaska's forest and miscellaneous land in them).

`in_48_states` is ERS's own scope — the rows its "48 States" line sums, DC
included — not a list kept here. The checks below print each ERS sub-total
against the sum of its rows: ERS says its distributions "may not add to totals
due to rounding", so a gap of a few thousand acres is the source's, reported.
Census's 18+ column is NOT shipped: it is a different definition of "adult"
from `capacity_weighted_adult_share`, which the framework reads.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

#: Census state FIPS for the 50 states and DC — the key the parcel extract uses.
STATE_FIPS: dict[str, str] = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05",
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10",
    "District of Columbia": "11", "Florida": "12", "Georgia": "13", "Hawaii": "15",
    "Idaho": "16", "Illinois": "17", "Indiana": "18", "Iowa": "19", "Kansas": "20",
    "Kentucky": "21", "Louisiana": "22", "Maine": "23", "Maryland": "24",
    "Massachusetts": "25", "Michigan": "26", "Minnesota": "27", "Mississippi": "28",
    "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32",
    "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36",
    "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40",
    "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44",
    "South Carolina": "45", "South Dakota": "46", "Tennessee": "47", "Texas": "48",
    "Utah": "49", "Vermont": "50", "Virginia": "51", "Washington": "53",
    "West Virginia": "54", "Wisconsin": "55", "Wyoming": "56",
}

#: ERS column → the class name `mlu_land_use_2022.csv` uses. Table 1's
#: "Special-use areas" is not shipped: table 5 partitions it.
TABLE1 = {"Cropland": "Total cropland",
          "Grassland pasture and range": "Grassland pasture and range",
          "Forest-use land": "Forest-use land (all)",
          "Urban areas": "Land in urban areas",
          "Miscellaneous other land": "Miscellaneous other land"}
TABLE5 = {"Rural transportation": "Land in rural transportation facilities",
          "Rural parks and wildlife": "Land in rural parks and wildlife areas",
          "Defense and industrial": "Land in defense and industrial areas",
          "Farmsteads and farm roads": "Farmsteads, roads, and miscellaneous farmland"}
CLASSES = list(TABLE1.values())[:3] + list(TABLE5.values()) + list(TABLE1.values())[3:]

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_xlsx(path: Path) -> list[list[str]]:
    """The first sheet's rows as strings — stdlib only (no openpyxl here)."""
    z = zipfile.ZipFile(path)
    shared = [] if "xl/sharedStrings.xml" not in z.namelist() else [
        "".join(t.text or "" for t in si.iter(_NS + "t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(_NS + "si")]
    sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    rows = []
    for row in ET.fromstring(z.read(sheet)).iter(_NS + "row"):
        cells = []
        for c in row.findall(_NS + "c"):
            v = c.find(_NS + "v")
            val = "" if v is None else (v.text or "")
            if c.get("t") == "s":
                val = shared[int(val)]
            cells.append(re.sub(r"\s+", " ", val).strip())
        rows.append(cells)
    return rows


def read_table(path: Path, columns: dict[str, str]) -> tuple[dict[str, dict], dict[str, dict]]:
    """(states, totals): {name: {class: kacres}} for the 50 states + DC, and the
    same for the '48 States' and 'U.S. total' lines. `in_48` marks the rows
    above ERS's '48 States' line."""
    rows = [r for r in read_xlsx(path) if any(r)]
    header = next(r for r in rows if r and r[0] == "Regions and States")
    idx = {columns[h]: i for i, h in enumerate(header) if h in columns}
    if len(idx) != len(columns):
        raise SystemExit(f"{path}: expected columns {sorted(columns)}, header {header}")
    states: dict[str, dict] = {}
    totals: dict[str, dict] = {}
    in_48 = True
    for r in rows[rows.index(header) + 1:]:
        name = r[0]
        if name in ("48 States", "U.S. total"):
            totals[name] = {k: float(r[i]) for k, i in idx.items()}
            in_48 = in_48 and name != "48 States"
        elif name in STATE_FIPS:
            states[name] = {k: float(r[i]) for k, i in idx.items()} | {"in_48": in_48}
    missing = set(STATE_FIPS) - set(states)
    if missing:
        raise SystemExit(f"{path}: no row for {sorted(missing)}")
    return states, totals


def read_population(path: Path) -> dict[str, int]:
    """{state: resident population} — Census marks state rows with a leading '.'."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    out = {r[0][1:]: int(r[1].replace(",", "")) for r in rows
           if r and r[0].startswith(".") and r[0][1:] in STATE_FIPS}
    missing = set(STATE_FIPS) - set(out)
    if missing:
        raise SystemExit(f"{path}: no row for {sorted(missing)}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--raw", default="rawdata")
    ap.add_argument("--out", default="hours_eoh/reference/data")
    a = ap.parse_args(argv)
    raw = Path(a.raw)
    t1, tot1 = read_table(raw / "ers_mlu" / "summary_table_1_2022.xlsx", TABLE1)
    t5, tot5 = read_table(raw / "ers_mlu" / "summary_table_5_2022.xlsx", TABLE5)
    pop = read_population(raw / "age" / "SCPRC-EST2025-18+POP.csv")
    if any(t1[s]["in_48"] != t5[s]["in_48"] for s in STATE_FIPS):
        raise SystemExit("tables 1 and 5 disagree on the 48-States scope")

    # Each ERS sub-total against its rows, reported (ERS: rounding).
    for scope, keep in (("48 States", True), ("U.S. total", None)):
        for cls_tab, tot in ((t1, tot1), (t5, tot5)):
            for cls, published in tot[scope].items():
                summed = sum(v[cls] for v in cls_tab.values() if keep is None or v["in_48"])
                print(f"{scope:<10} {cls:<46} rows {summed:>10,.0f}  "
                      f"published {published:>10,.0f}  gap {summed - published:+,.0f}",
                      file=sys.stderr)

    out = Path(a.out) / "state_land_population.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["statefp", "state", "in_48_states", "population_2025"] + CLASSES)
        for name in sorted(STATE_FIPS, key=STATE_FIPS.__getitem__):
            land = t1[name] | t5[name]
            w.writerow([STATE_FIPS[name], name, int(land["in_48"]), pop[name]]
                       + [f"{land[c]:.0f}" for c in CLASSES])
    print(f"wrote {out} ({len(STATE_FIPS)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
