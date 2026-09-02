"""
ATUS 2003–2025 ingest — raw microdata → the shipped annual extract.

Run this ONCE when the raw BLS files change; the repo ships only the small
derived CSVs it writes. The raw multi-year files are ~2.9 GB and live in
`rawdata/atus/` which is gitignored, exactly as the O*NET build lives in
the multiplier handoff while the repo ships `multiplier_registry_v5.csv`.

    python3 utils/atus_ingest.py [--raw rawdata/atus] [--out hours_eoh/reference/data]

Outputs (both committed):
    atus_annual_0325.csv   year, tier2 activity code, mean minutes/day
    atus_years_0325.csv    year, n, population 15+, mean household size, mean age,
                           the weight variable used, and a comparability flag

WEIGHTS — the trap this script exists to handle
------------------------------------------------
`TUFNWGTP` is the multi-year final weight and it is **zero for 2020**. A naive
pool over the multi-year file silently drops 2020, or divides by ~0 and emits
garbage. BLS supplies `TU20FWGT` for the 2019–2020 period instead, and this
script uses it for 2020 alone.

2020 IS NOT COMPARABLE and is flagged as such in the years file. ATUS collection
was suspended mid-March to mid-May 2020, so the 2020 estimates cover roughly
May–December. Any series that pools it with full-year estimates is comparing
eight months against twelve. Downstream code must read `comparable` and decide;
this script neither drops the year nor hides it.

Units: minutes per day per person aged 15+, the ATUS native unit. The ACTIVITY
extract carries no annualizing convention and no 15+→all-ages bridge — those are
the caller's decisions, documented in `hours_eoh/reference/atus_time_use.py`. The
years extract does divide the weight sum by `ATUS_DAYS_PER_YEAR` to state the
frame's population, because a sum of person-DAYS is not a population.
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

# Allow running directly from repo root without install (as utils/eoh_cli.py does)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hours_eoh.reference.atus_time_use import ATUS_DAYS_PER_YEAR  # noqa: E402

#: 2020 has no valid TUFNWGTP; BLS ships TU20FWGT for the 2019–20 period.
SPECIAL_WEIGHT_YEARS: dict[int, str] = {2020: "TU20FWGT"}

#: Years whose estimates do not cover a full calendar year of collection.
NON_COMPARABLE_YEARS: frozenset[int] = frozenset({2020})

DEFAULT_WEIGHT = "TUFNWGTP"


def _household_sizes(resp_path: Path) -> dict[str, int]:
    """TUCASEID → TRNUMHOU from the respondent file (the summary file lacks it)."""
    sizes: dict[str, int] = {}
    with resp_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        i_id, i_n = header.index("TUCASEID"), header.index("TRNUMHOU")
        for row in reader:
            try:
                sizes[row[i_id]] = int(row[i_n])
            except (ValueError, IndexError):
                continue
    return sizes


def ingest(raw_dir: Path, out_dir: Path) -> tuple[Path, Path]:
    """Read the raw summary + respondent files and write the two extracts."""
    sum_path = raw_dir / "sum" / "atussum_0325.dat"
    resp_path = raw_dir / "resp" / "atusresp_0325.dat"
    for path in (sum_path, resp_path):
        if not path.exists():
            raise FileNotFoundError(f"missing raw ATUS file: {path}")

    sizes = _household_sizes(resp_path)

    with sum_path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        # Activity columns are t + 6 digits; tier 2 is the first four of those.
        activities = [
            (i, name[1:5])
            for name, i in idx.items()
            if name.startswith("t") and name[1:].isdigit() and len(name) == 7
        ]
        i_year, i_age, i_case = idx["TUYEAR"], idx["TEAGE"], idx["TUCASEID"]
        weight_cols = {
            name: idx[name]
            for name in {DEFAULT_WEIGHT, *SPECIAL_WEIGHT_YEARS.values()}
        }

        weight_sum: dict[int, float] = collections.defaultdict(float)
        minutes: dict[int, dict[str, float]] = collections.defaultdict(
            lambda: collections.defaultdict(float)
        )
        n_rows: collections.Counter[int] = collections.Counter()
        age_sum: dict[int, float] = collections.defaultdict(float)
        hh_sum: dict[int, float] = collections.defaultdict(float)
        hh_weight: dict[int, float] = collections.defaultdict(float)

        for row in reader:
            year = int(row[i_year])
            weight = float(row[weight_cols[SPECIAL_WEIGHT_YEARS.get(year, DEFAULT_WEIGHT)]])
            if weight <= 0.0:
                continue
            n_rows[year] += 1
            weight_sum[year] += weight
            age_sum[year] += weight * float(row[i_age])
            size = sizes.get(row[i_case])
            if size is not None:
                hh_sum[year] += weight * size
                hh_weight[year] += weight
            bucket = minutes[year]
            for i, tier2 in activities:
                # Short-circuit on the string: most of the 431 activity columns
                # are "0" for any given respondent, and this skips 111M float()
                # calls over the file.
                cell = row[i]
                if cell != "0":
                    bucket[tier2] += weight * float(cell)

    out_dir.mkdir(parents=True, exist_ok=True)
    annual_path = out_dir / "atus_annual_0325.csv"
    years_path = out_dir / "atus_years_0325.csv"

    with annual_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["year", "tier2", "mean_minutes_per_day"])
        for year in sorted(minutes):
            total = weight_sum[year]
            for tier2 in sorted(minutes[year]):
                writer.writerow([year, tier2, f"{minutes[year][tier2] / total:.6f}"])

    with years_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "year", "n_respondents", "population_15_plus", "mean_household_size",
            "mean_age", "weight_variable", "comparable",
        ])
        for year in sorted(weight_sum):
            mean_hh = hh_sum[year] / hh_weight[year] if hh_weight[year] else None
            writer.writerow([
                year,
                n_rows[year],
                f"{weight_sum[year] / ATUS_DAYS_PER_YEAR:.1f}",
                f"{mean_hh:.4f}" if mean_hh is not None else "",
                f"{age_sum[year] / weight_sum[year]:.3f}",
                SPECIAL_WEIGHT_YEARS.get(year, DEFAULT_WEIGHT),
                "false" if year in NON_COMPARABLE_YEARS else "true",
            ])

    return annual_path, years_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="rawdata/atus", type=Path)
    parser.add_argument("--out", default="hours_eoh/reference/data", type=Path)
    args = parser.parse_args(argv)

    annual, years = ingest(args.raw, args.out)
    print(f"wrote {annual}")
    print(f"wrote {years}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
