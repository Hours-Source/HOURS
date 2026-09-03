"""
Unpaid domestic work by MTUS sample — the long series ATUS cannot reach.

WHY THIS EXISTS. `scenarios/automation_floors` measured the ATUS window
(2003-2025) against the personal automation floors and found it saturated: the
household automation that mattered predates the sample, so the series cannot
see what is left for machines to take. MTUS spans 1965-2024 across ten
countries, which is the capital variation that window lacks.

WHAT IS EXTRACTED. One row per sample: the weighted mean minutes per day of
`ACT_UNDOM` (unpaid domestic work), `ACT_CHCARE` (childcare), `ACT_WORK` (paid
work), plus `ACT_TRAVEL` and `ACT_EDUCA` — the two whose membership in
"entropy-resistance labour" is arguable — and the respondent count. The three
core columns are shipped as SEPARATE columns rather than pre-summed, so a
caller varies the definition instead of inheriting one. That is an AGGREGATE — nutrition and shelter together — so it
cannot give per-component floors. It answers the prior question: does household
labour respond to capital at all, and where did the response happen.

THREE DECISIONS THE EXTRACT MAKES, EACH FORCED BY THE DATA.

1. AGES 18-69 ONLY. Age coverage differs by sample — BG1965 starts at 18,
   US1965 stops at 69, AT1992 includes 9-year-olds. Comparing raw means across
   samples with different age floors measures the floor, not the behaviour.
   18-69 is the band every one of the 50 samples covers.

2. WEIGHTED BY `PROPWT`, and rows with a non-positive weight are dropped.

3. NO DEDUPLICATION, and the reason is a trap worth recording. `SERIAL` is
   EMPTY in AT1992, FR1985 and FR1999 while `HLDID` is populated, so a key
   built on SERIAL collapses ~100% of those three samples into apparent
   duplicates. They are not duplicates; the identifier is simply absent. No US
   sample is affected. Each row is one diary day and the weighted mean is taken
   over rows, so no key is needed — but anyone adding one must use HLDID.

The arithmetic check: the twelve ACT_* columns sum to exactly 1440 minutes per
diary, which is what makes the units trustworthy without a codebook.
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib

#: Every sample covers this band; see decision 1 above.
AGE_LO, AGE_HI = 18, 69

#: The twelve harmonised activity aggregates. They partition the day.
ACT_COLUMNS: tuple[str, ...] = (
    "ACT_CHCARE", "ACT_CIVIC", "ACT_EDUCA", "ACT_INHOME", "ACT_MEDIA",
    "ACT_NOREC", "ACT_OUTHOME", "ACT_PCARE", "ACT_PHYSICAL", "ACT_TRAVEL",
    "ACT_UNDOM", "ACT_WORK",
)

OUT_NAME = "mtus_domestic_by_sample.csv"


def _num(value: str | None) -> float:
    try:
        return float(value or 0.0)
    except ValueError:
        return 0.0


def ingest(esp: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    """Read the harmonised episode file and write one row per sample."""
    if not esp.exists():
        raise FileNotFoundError(f"missing MTUS file: {esp}")

    undom: dict[str, float] = collections.defaultdict(float)
    chcare: dict[str, float] = collections.defaultdict(float)
    work: dict[str, float] = collections.defaultdict(float)
    travel: dict[str, float] = collections.defaultdict(float)
    educa: dict[str, float] = collections.defaultdict(float)
    day: dict[str, float] = collections.defaultdict(float)
    weight: dict[str, float] = collections.defaultdict(float)
    count: collections.Counter[str] = collections.Counter()
    country: dict[str, str] = {}
    year: dict[str, int] = {}

    with esp.open(newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                age = int(float(row["AGE"]))
            except (ValueError, KeyError):
                continue
            if not (AGE_LO <= age <= AGE_HI):
                continue
            w = _num(row.get("PROPWT"))
            if w <= 0.0:
                continue
            sample = row["SAMPLE"]
            undom[sample] += w * _num(row.get("ACT_UNDOM"))
            chcare[sample] += w * _num(row.get("ACT_CHCARE"))
            work[sample] += w * _num(row.get("ACT_WORK"))
            travel[sample] += w * _num(row.get("ACT_TRAVEL"))
            educa[sample] += w * _num(row.get("ACT_EDUCA"))
            day[sample] += w * sum(_num(row.get(c)) for c in ACT_COLUMNS)
            weight[sample] += w
            count[sample] += 1
            country.setdefault(sample, row.get("COUNTRY", ""))
            if sample not in year:
                try:
                    year[sample] = int(float(row["YEAR"]))
                except (ValueError, KeyError):
                    year[sample] = int(sample[-4:])

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / OUT_NAME
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "sample", "country", "year", "n_respondents",
            "undom_minutes_per_day", "chcare_minutes_per_day",
            "work_minutes_per_day", "travel_minutes_per_day",
            "educa_minutes_per_day", "day_minutes",
        ])
        for sample in sorted(undom):
            w = weight[sample]
            writer.writerow([
                sample, country[sample], year[sample], count[sample],
                f"{undom[sample] / w:.4f}",
                f"{chcare[sample] / w:.4f}",
                f"{work[sample] / w:.4f}",
                f"{travel[sample] / w:.4f}",
                f"{educa[sample] / w:.4f}",
                f"{day[sample] / w:.4f}",
            ])
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esp", default=pathlib.Path("rawdata/mtus_esp_lite.csv"),
                        type=pathlib.Path)
    parser.add_argument("--out", default=pathlib.Path("hours_eoh/reference/data"),
                        type=pathlib.Path)
    args = parser.parse_args(argv)
    print(f"wrote {ingest(args.esp, args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
