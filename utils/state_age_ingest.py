"""
State resident population by single year of age → the shipped state age extract.

SPDX-License-Identifier: AGPL-3.0-or-later

Run this ONCE when the source changes; the repo ships only the CSV it writes. The source
lives in gitignored `rawdata/`, as every raw file does:

    rawdata/age/sc-est2025-alldata6.csv   Census Bureau, Population Division,
        Vintage 2025 state characteristics: resident population by state ×
        SEX × ORIGIN × RACE (six groups) × single year of age, July 1 2020–2025
        (www2.census.gov/programs-surveys/popest/datasets/2020-2025/state/asrh/)

    python3 utils/state_age_ingest.py [--raw rawdata] [--out hours_eoh/reference/data]

Output (committed):
    state_age_2025.csv   statefp, age, population — July 1, 2025, both sexes, every
                         origin and race; age 85 means "85 and over"

WHY: the US frame divided into its states (`reference/states.us_state_split`) ran every
state on the NATIONAL age mix, so states differed only in head count. The age mix
reaches the obligation (personal EOH, the guarantee, the care stipend) and the labour
supply (the adult share).

THE UNIVERSE IS RESIDENT, as in the national extract (`nc-est2025-agesex-res`) and in
`state_land_population.csv`'s population. The sibling file `sc-est2025-agesex-civ` is
CIVILIAN (the armed forces are out), and this script does not use it. alldata6 has no
race total: SEX=0 and ORIGIN=0 are totals, and RACE 1–6 partition the population, so the
script sums the six.

INTEGRITY, NOT TOLERANCE: each state's ages must sum to the population that
`state_land_population.csv` ships for it, the same Census vintage from a different
table. A mismatch stops the ingest.

THE TOP-CODE IS 85, where the national extract's is 100. A reader that groups these ages
must refuse a band that starts above 85.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hours_eoh.reference.states import AGE_TOP as TOP_AGE  # noqa: E402

SOURCE = "sc-est2025-alldata6.csv"
YEAR = 2025
#: alldata6's codes: SEX 0 and ORIGIN 0 are totals; RACE has no total.
TOTAL_SEX, TOTAL_ORIGIN, RACES = "0", "0", {"1", "2", "3", "4", "5", "6"}


def read_ages(path: Path) -> dict[str, dict[int, int]]:
    """{statefp: {age: resident population, July 1 YEAR}}."""
    out: dict[str, dict[int, int]] = {}
    races: dict[str, set[str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["SUMLEV"] != "040" or r["SEX"] != TOTAL_SEX or r["ORIGIN"] != TOTAL_ORIGIN:
                continue
            fp, age = r["STATE"], int(r["AGE"])
            if not 0 <= age <= TOP_AGE:
                raise SystemExit(f"{path}: age {age} outside 0–{TOP_AGE}")
            ages = out.setdefault(fp, {})
            ages[age] = ages.get(age, 0) + int(r[f"POPESTIMATE{YEAR}"])
            races.setdefault(fp, set()).add(r["RACE"])
    for fp, ages in out.items():
        if races[fp] != RACES or set(ages) != set(range(TOP_AGE + 1)):
            raise SystemExit(f"{path}: state {fp} lacks a race group or an age")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--raw", default="rawdata")
    ap.add_argument("--out", default="hours_eoh/reference/data")
    a = ap.parse_args(argv)
    ages = read_ages(Path(a.raw) / "age" / SOURCE)
    with (Path(a.out) / "state_land_population.csv").open(newline="") as fh:
        shipped = {r["statefp"]: int(r["population_2025"]) for r in csv.DictReader(fh)}
    if set(ages) != set(shipped):
        raise SystemExit(f"states differ from state_land_population.csv: "
                         f"{sorted(set(ages) ^ set(shipped))}")
    for fp, by_age in ages.items():
        if sum(by_age.values()) != shipped[fp]:
            raise SystemExit(f"state {fp}: ages sum to {sum(by_age.values()):,}, "
                             f"state_land_population.csv ships {shipped[fp]:,}")
    out = Path(a.out) / f"state_age_{YEAR}.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["statefp", "age", "population"])
        for fp in sorted(ages):
            for age in range(TOP_AGE + 1):
                w.writerow([fp, age, ages[fp][age]])
    print(f"wrote {out} ({len(ages)} states × {TOP_AGE + 1} ages; every state's "
          f"ages sum to its shipped population)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
