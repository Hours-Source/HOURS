"""
MTUS six-digit episode file → per-sample, per-activity-code minutes.

SPDX-License-Identifier: AGPL-3.0-or-later

    python3 utils/mtus_code_ingest.py

Output (committed):  mtus_codes_by_sample.csv   sample, code, minutes_per_day

WHY. `scenarios/automation_floors` could bound the AGGREGATE floor from
`ACT_UNDOM` but not any single component, because that aggregate is nutrition
and shelter together. The episode file carries a finer coding — 56 to 67
distinct codes per sample — which separates them. This extract makes that
coding available without the 3.1 GB raw file.

THE LAYOUT IS DERIVED, NOT ASSUMED, and it is the one `utils/mtus_ingest.py`
established (no codebook ships with the file):

    line[0] == "3"   episode record
    [1:8] serial   [8:14] sample   [93:97] duration   [97:100] activity code

`duration` was located by the only constraint that identifies it — the window
summing to exactly 1440 in every diary — and confirmed by
`start + duration == next start`.

WHAT THIS EXTRACT DELIBERATELY DOES NOT DO. It ships every code it finds and
maps nothing. The code→component mapping is a declared judgement and lives in
`scenarios/automation_floors`, where it can be stated and tested; an extract cut
to fit one hypothesis is the calibrated-to-target failure in data form. 3,600-odd
rows is a small price for an extract that outlives the question it was built for.

THE JOIN KEY. (SAMPLE, SERIAL). `SERIAL` alone is NOT unique — the file stacks
extracts and the counter restarts per sample. It is also EMPTY in AT1992, FR1985
and FR1999, where `HLDID` carries the identifier instead; those three samples
therefore contribute nothing here, which is recorded rather than hidden.
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib

#: Ages every one of the harmonised samples covers, matching the domestic extract.
AGE_LO, AGE_HI = 18, 69

#: A diary that does not close to a full day is dropped, not repaired.
MINUTES_PER_DAY = 1440

OUT_NAME = "mtus_codes_by_sample.csv"


def ingest(dat: pathlib.Path, esp: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    weights: dict[tuple[str, int], float] = {}
    with esp.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            serial = (row.get("SERIAL") or "").strip()
            if not serial.isdigit():
                continue                      # AT1992 / FR1985 / FR1999 land here
            try:
                age = int(float(row["AGE"]))
                weight = float(row["PROPWT"] or 0.0)
            except (ValueError, TypeError, KeyError):
                continue
            if weight <= 0.0 or not (AGE_LO <= age <= AGE_HI):
                continue
            weights[(row["SAMPLE"], int(serial))] = weight

    minutes: dict[str, dict[int, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float)
    )
    day: dict[tuple[str, int], float] = collections.defaultdict(float)
    per_diary: dict[tuple[str, int], dict[int, float]] = collections.defaultdict(
        lambda: collections.defaultdict(float)
    )
    with dat.open() as fh:
        for line in fh:
            if line[0] != "3":
                continue
            serial = line[1:8].strip()
            if not serial.isdigit():
                continue
            key = (line[8:14], int(serial))
            if key not in weights:
                continue
            dur = int(line[93:97])
            per_diary[key][int(line[97:100])] += dur
            day[key] += dur

    weight_sum: dict[str, float] = collections.defaultdict(float)
    for key, codes in per_diary.items():
        if day[key] != MINUTES_PER_DAY:       # the arithmetic gate on the layout
            continue
        sample, _ = key
        w = weights[key]
        weight_sum[sample] += w
        bucket = minutes[sample]
        for code, dur in codes.items():
            bucket[code] += w * dur

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / OUT_NAME
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sample", "code", "minutes_per_day"])
        for sample in sorted(minutes):
            total = weight_sum[sample]
            for code in sorted(minutes[sample]):
                writer.writerow([sample, code, f"{minutes[sample][code] / total:.4f}"])
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dat", default=pathlib.Path("rawdata/mtus.dat"), type=pathlib.Path)
    parser.add_argument("--esp", default=pathlib.Path("rawdata/mtus_esp_lite.csv"), type=pathlib.Path)
    parser.add_argument("--out", default=pathlib.Path("hours_eoh/reference/data"), type=pathlib.Path)
    args = parser.parse_args(argv)
    for path in (args.dat, args.esp):
        if not path.exists():
            raise SystemExit(f"missing raw MTUS file: {path}")
    print(f"wrote {ingest(args.dat, args.esp, args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
