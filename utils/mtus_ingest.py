"""
MTUS episode file → the shipped per-age self-maintenance extract.

SPDX-License-Identifier: AGPL-3.0-or-later

Run this ONCE when the raw MTUS files change; the repo ships only the small
derived CSV. The raw files (`mtus.dat` 3.3 GB, `mtus_esp.csv` 150 MB) live in
`rawdata/`, which is gitignored — exactly as the 68 GB parcel census and the
2.9 GB ATUS microdata are.

    python3 utils/mtus_ingest.py

Output (committed):
    mtus_self_maintenance_by_age.csv   age, minutes_per_day, diaries, samples

WHY THIS EXTRACT EXISTS
------------------------
`AGE_WEIGHT_INFANT` and `AGE_WEIGHT_CHILD` are one-sided bands because ATUS
surveys nobody under 15, so self-maintenance for the whole infant band and for
ages 6–14 is ABSENT — and `care_curve` necessarily records absent as 0.0. The
constants' own `resolves_by` names the fix: "a time-use survey covering
children would close the band from below." MTUS is that survey.

THE LAYOUT IS DERIVED, NOT ASSUMED — no codebook ships with the file:

    [85:89] start   [89:93] end   [93:97] duration   [97:100] activity code

`duration` was located by the only constraint that identifies it — the window
whose values sum to exactly 1440 in every diary — and confirmed by
`start + duration == next start`.

THE ACTIVITY AGGREGATION IS DERIVED THE SAME WAY, by joining episodes to the
`mtus_esp.csv` aggregates and solving for the code set:

    ACT_PCARE  = {2, 4, 5, 6}          exact on AM2008 and KR2004
    ACT_CHCARE = {28, 29, 30, 31}      exact on both
    ACT_UNDOM  = {18..25, 27}          exact on AM2008, 93% on KR2004

Sleep is code 2 — stable at 453–568 min/day and ~2.1 episodes/day in every
sample checked, and always the largest single code.

THE JOIN KEY IS (SAMPLE, SERIAL) AND THAT COST A WRONG ANSWER. `SERIAL` alone is
NOT unique: SERIAL 46950 exists as both `IT2002` and `KR1999`, because the file
stacks extracts and the counter restarts per sample. Joining on SERIAL merged
Italian and Korean episodes into single diaries and produced a confident, wrong
result. It surfaced only on checking a second country.

WHAT THIS EXTRACT DOES NOT SETTLE
----------------------------------
MTUS puts MEALS inside its personal-care block and the repo's definition
(ATUS tier-1 01 less sleep, plus 02) excludes them — ATUS counts eating under
tier-1 11. Removing meals would need the sub-codes of {4, 5, 6}, and those are
NOT comparable across samples: code 6 runs 137 min/day in AM2008 and 59 in
KR2004, while code 4 runs 29 and 83. So the extract carries the sleep-removed
figure and the eating term stays in, which biases the ratio TOWARD 1 — the safe
direction for a floor, and stated rather than corrected.
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import sys

SLEEP = frozenset({2})
PCARE_NON_SLEEP = frozenset({4, 5, 6})
UNDOM = frozenset({18, 19, 20, 21, 22, 23, 24, 25, 27})

DEFAULT_DAT = "rawdata/mtus.dat"
DEFAULT_ESP = "rawdata/mtus_esp.csv"
DEFAULT_OUT = "hours_eoh/reference/data"
OUT_NAME = "mtus_self_maintenance_by_age.csv"

#: A diary that does not close to a full day is dropped, not repaired. 15,441
#: rows in `mtus_esp.csv` close to 1,680 minutes (28 hours) rather than 1,440.
MINUTES_PER_DAY = 1440


def ingest(dat: pathlib.Path, esp: pathlib.Path, out_dir: pathlib.Path) -> pathlib.Path:
    meta: dict[tuple[str, int], tuple[int, float, str]] = {}
    with esp.open(newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            serial = (row.get("SERIAL") or "").strip()
            if not serial.isdigit():
                continue
            try:
                age = int(row["AGE"])
                weight = float(row["PROPWT"] or 0.0)
            except (ValueError, TypeError):
                continue
            if age < 0 or weight <= 0.0:
                continue
            meta[(row["SAMPLE"], int(serial))] = (age, weight, row["SAMPLE"])
    print(f"{esp.name}: {len(meta):,} diaries with age and weight")

    acc: dict[tuple[str, int], list[float]] = collections.defaultdict(
        lambda: [0.0, 0.0]
    )
    with dat.open() as fh:
        for line in fh:
            if line[0] != "3":
                continue
            serial = line[1:8].strip()
            if not serial.isdigit():
                continue
            key = (line[8:14], int(serial))
            if key not in meta:
                continue
            minutes = int(line[93:97])
            code = int(line[97:100])
            cell = acc[key]
            cell[0] += minutes
            if code in PCARE_NON_SLEEP or code in UNDOM:
                cell[1] += minutes

    by_age: dict[int, list[float]] = collections.defaultdict(lambda: [0.0, 0.0, 0])
    samples: dict[int, set[str]] = collections.defaultdict(set)
    for key, (total, self_min) in acc.items():
        if total != MINUTES_PER_DAY:
            continue
        age, weight, sample = meta[key]
        cell = by_age[age]
        cell[0] += weight
        cell[1] += weight * self_min
        cell[2] += 1
        samples[age].add(sample)

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / OUT_NAME
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["age", "minutes_per_day", "diaries", "samples"])
        for age in sorted(by_age):
            weight, weighted, n = by_age[age]
            writer.writerow([age, f"{weighted / weight:.4f}", n, len(samples[age])])

    print(f"{out}: {len(by_age)} ages, {sum(c[2] for c in by_age.values()):,} diaries")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dat", default=DEFAULT_DAT, type=pathlib.Path)
    parser.add_argument("--esp", default=DEFAULT_ESP, type=pathlib.Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=pathlib.Path)
    args = parser.parse_args(argv)
    for path in (args.dat, args.esp):
        if not path.exists():
            sys.exit(f"raw MTUS file not found: {path} (gitignored by design)")
    ingest(args.dat, args.esp, args.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
