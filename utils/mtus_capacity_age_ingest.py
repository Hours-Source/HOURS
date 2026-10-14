"""
MTUS → measured entropy-resistance labour BY SINGLE YEAR OF AGE, every sample.

    python3 utils/mtus_capacity_age_ingest.py [--esp rawdata/mtus_esp_lite.csv] [--out hours_eoh/reference/data]

Output (committed):
    mtus_capacity_by_age.csv   sample, country, year, age, diaries, weight,
                               work / undom / chcare minutes per day

WHY THIS EXISTS. `AGE_CAPACITY_WEIGHT_*`'s `resolves_by` asks for "paid work
plus unpaid domestic work plus childcare, the same three fields
`measured_capacity` counts, tabulated for under-18 and over-64 rather than
pooled over 18-69". `mtus_domestic_ingest.py` pools exactly those three columns
over 18-69 per sample; this is the SAME file, the SAME three columns and the
SAME weight, cut by age instead of pooled — so a band built from it reproduces
`measured_capacity` (US2024, 18-69: 381.2 min/day) and is the same instrument,
not a neighbouring one.

Every age a sample covers is kept; coverage differs by sample (BG1965 starts at
18, US1965 stops at 69, AT1992 includes 9-year-olds), which is why `diaries`
and `weight` ship per row: a band mean is the weight-weighted mean of its ages,
and an age a sample did not survey is ABSENT, never zero.

Decisions shared with `mtus_domestic_ingest.py`: weighted by `PROPWT`, rows
with a non-positive weight dropped, no deduplication (SERIAL is empty in three
samples; each row is one diary day).
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib

OUT_NAME = "mtus_capacity_by_age.csv"

#: The three columns `reference.mtus_time_use.LABOUR_AGGREGATES` counts.
FIELDS: tuple[str, ...] = ("ACT_WORK", "ACT_UNDOM", "ACT_CHCARE")


def _num(value: str | None) -> float:
    try:
        return float(value or 0.0)
    except ValueError:
        return 0.0


def ingest(esp: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    if not esp.exists():
        raise FileNotFoundError(f"missing MTUS file: {esp}")
    acc: dict[tuple[str, int], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0, 0.0, 0.0, 0.0])          # weight, work, undom, chcare, diaries
    country: dict[str, str] = {}
    year: dict[str, int] = {}
    with esp.open(newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                age = int(float(row["AGE"]))
            except (ValueError, KeyError):
                continue
            w = _num(row.get("PROPWT"))
            if age < 0 or w <= 0.0:
                continue
            sample = row["SAMPLE"]
            cell = acc[(sample, age)]
            cell[0] += w
            for i, field in enumerate(FIELDS, start=1):
                cell[i] += w * _num(row.get(field))
            cell[4] += 1
            country.setdefault(sample, row.get("COUNTRY", ""))
            if sample not in year:
                try:
                    year[sample] = int(float(row["YEAR"]))
                except (ValueError, KeyError):
                    year[sample] = int(sample[-4:])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / OUT_NAME
    with out.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sample", "country", "year", "age", "diaries", "weight",
                         "work_minutes_per_day", "undom_minutes_per_day",
                         "chcare_minutes_per_day"])
        for (sample, age) in sorted(acc):
            w, work, undom, chcare, n = acc[(sample, age)]
            writer.writerow([sample, country[sample], year[sample], age, int(n),
                             f"{w:.4f}", f"{work / w:.4f}", f"{undom / w:.4f}",
                             f"{chcare / w:.4f}"])
    print(f"{out}: {len({s for s, _ in acc})} samples, {len(acc)} sample-ages")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--esp", default=pathlib.Path("rawdata/mtus_esp_lite.csv"), type=pathlib.Path)
    parser.add_argument("--out", default=pathlib.Path("hours_eoh/reference/data"), type=pathlib.Path)
    args = parser.parse_args(argv)
    ingest(args.esp, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
