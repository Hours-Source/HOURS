"""
US Census population by single year of age → the shipped age-structure extract.

    python3 utils/census_age_ingest.py [--raw rawdata/age] [--out hours_eoh/reference/data]

Output (committed):
    census_age_2020_2025.csv   year, age, population

Reads `nc-est2025-agesex-res.csv` (Vintage 2025 national estimates, SEX × single
year of age × 2020–2025). Only SEX=0 (both sexes) is kept; AGE=999 is the
published total and is used as an integrity check rather than a row.

WHY THIS EXISTS — it is a denominator, not a headline
------------------------------------------------------
Two things in this repo need a population age structure and neither can get it
from ATUS:

1. **The eldercare module route.** ATUS's eldercare roster gives minutes per
   RECIPIENT, and most recipients are not household members, so they appear on
   no ATUS roster and have no population denominator inside the survey. Without
   an external denominator the module route cannot be compared with the
   household-roster route at all — and reporting that disagreement is the whole
   point of carrying both.
2. **`AGE_GROUPS` fractions.** The shipped 7/16/60/17 split is an OECD-shaped
   default. This file measures it.

WHAT THIS IS NOT: a claim that US age structure is the right structure for any
other collective. It is one jurisdiction at one time, and the age structure of a
modelled collective is an `instance` input its institution supplies. This extract
is the US reference point, used here because the ATUS care measurements it pairs
with are US measurements.

Vintage note: these are post-censal ESTIMATES, revised annually by the Census
Bureau. Re-running against a later vintage will move the numbers slightly.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: SEX=0 is both sexes combined; 1 male, 2 female.
BOTH_SEXES = "0"

#: The published all-ages total, carried as a row in the source file.
TOTAL_AGE = 999

#: Top-coded age in the source. 100 means "100 and over".
MAX_AGE = 100


def ingest(raw_dir: Path, out_dir: Path) -> Path:
    src = raw_dir / "nc-est2025-agesex-res.csv"
    if not src.exists():
        raise FileNotFoundError(f"missing raw census file: {src}")

    with src.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["SEX"] == BOTH_SEXES]

    years = [c for c in rows[0] if c.startswith("POPESTIMATE")]
    by_age = {int(r["AGE"]): r for r in rows}

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "census_age_2020_2025.csv"
    with out_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "age", "population"])
        for column in years:
            year = int(column.removeprefix("POPESTIMATE"))
            total = int(by_age[TOTAL_AGE][column])
            summed = sum(
                int(by_age[a][column]) for a in range(MAX_AGE + 1) if a in by_age
            )
            # Integrity check, not a tolerance: ages 0–100 partition the
            # population exactly because 100 is top-coded "100 and over". If this
            # ever fails the file's structure has changed and the extract is
            # meaningless, so it must stop rather than ship a silent shortfall.
            if summed != total:
                raise ValueError(
                    f"{year}: ages 0–{MAX_AGE} sum to {summed:,} but the "
                    f"published total is {total:,} (diff {total - summed:,})"
                )
            for age in range(MAX_AGE + 1):
                writer.writerow([year, age, int(by_age[age][column])])
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="rawdata/age", type=Path)
    parser.add_argument("--out", default="hours_eoh/reference/data", type=Path)
    args = parser.parse_args(argv)
    print(f"wrote {ingest(args.raw, args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
