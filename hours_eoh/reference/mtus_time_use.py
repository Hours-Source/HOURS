"""
MTUS self-maintenance by single year of age — the ages ATUS cannot see.

SPDX-License-Identifier: AGPL-3.0-or-later

WHAT THIS IS FOR. `AGE_WEIGHT_INFANT` and `AGE_WEIGHT_CHILD` are one-sided
bands because ATUS surveys nobody under 15. `reference/care_demand` records
that honestly — *"Ages below SELF_MAINTENANCE_MIN_AGE are ABSENT, not zero.
Near-zero is plausible for an infant and plainly wrong for a twelve-year-old"* —
but the arithmetic still has to put a number in, and the number it puts in is
0.0. The constants' own `resolves_by` names the fix: *"a time-use survey
covering children would close the band from below."*

This is that survey: **977,809 diaries, 21 countries, 89 country-years**, with
children surveyed from age 3.

WHAT IT MEASURES. Non-sleep personal care plus unpaid domestic work, which is
the MTUS analogue of the repo's self-maintenance definition (ATUS tier-1 01
less sleep, plus 02). Sleep is separable and was removed; see
`utils/mtus_ingest.py` for how the layout and the activity aggregation were
derived from the raw file, which ships no codebook.

TWO LIMITS, BOTH LOAD-BEARING, AND NEITHER IS CORRECTED HERE:

  1. **MEALS ARE STILL IN.** MTUS puts eating inside its personal-care block;
     ATUS counts it under tier-1 11 and the repo's definition excludes it.
     Removing it needs the sub-codes of {4, 5, 6}, and those are NOT comparable
     across samples — code 6 runs 137 min/day in AM2008 and 59 in KR2004, code 4
     runs 29 and 83. So a level from this file sits ABOVE the repo's definition:
     working-age reads 263.7 here against 153.2 in `care_curve`.

     **The bias direction is known and it is the safe one.** Eating is roughly
     age-invariant, so it enters numerator and denominator alike and pulls any
     ratio TOWARD 1. For a band whose value is below 1 — children — the measured
     ratio therefore OVERSTATES, and `AGE_WEIGHT_*` errs HIGH by design.

  2. **AGES 0–2 ARE 260 DIARIES FROM ONE SAMPLE.** They are reported and must
     not be leaned on. More importantly an infant's maintenance IS the
     caregiver's work, which `care_curve` already counts on the care-received
     side — so an extrapolated self-maintenance term for 0–2 would DOUBLE COUNT,
     and this module does not extrapolate one.

Layer: `reference/` imports nothing from the package — pure data.
"""

from __future__ import annotations

import csv
import pathlib

__all__ = [
    "DATA_FILE",
    "MTUS_DIARIES",
    "MTUS_COUNTRIES",
    "WORKING_AGE_MINUTES",
    "CARE_CURVE_WORKING_AGE_MINUTES",
    "load_by_age",
    "band_minutes",
    "band_ratio",
]

DATA_FILE = pathlib.Path(__file__).with_name("data") / "mtus_self_maintenance_by_age.csv"

#: Diaries behind the extract, after dropping days that do not close to 1440.
MTUS_DIARIES = 977_809

#: Distinct countries in `mtus_esp.csv`.
MTUS_COUNTRIES = 21

#: Working-age self-maintenance in THIS module's definition (meals included).
#: Carried so a caller can see the gap rather than discover it.
WORKING_AGE_MINUTES = 263.7

#: The same quantity in the repo's definition, from `scenarios/care_curve`.
#: The gap is meals — see limit 1 in the module docstring.
CARE_CURVE_WORKING_AGE_MINUTES = 153.196359550956


def load_by_age() -> list[dict[str, float]]:
    """
    The shipped extract, one row per single year of age.

    Columns: `age`, `minutes_per_day` (weighted mean non-sleep self-maintenance),
    `diaries` (unweighted count), `samples` (distinct country-years contributing).

    `samples` is shipped alongside the count because a mean over many diaries
    from ONE country-year is a different thing from the same count spread over
    fifty — and ages 0–2 are the case where that distinction bites.
    """
    rows: list[dict[str, float]] = []
    with DATA_FILE.open(encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            rows.append({
                "age":             float(record["age"]),
                "minutes_per_day": float(record["minutes_per_day"]),
                "diaries":         float(record["diaries"]),
                "samples":         float(record["samples"]),
            })
    return rows


def band_minutes(lo: int, hi: int) -> dict[str, float]:
    """
    Diary-weighted mean self-maintenance over an inclusive age band.

    Governing sum:

        minutes(band) = Σ_a diaries(a)·minutes(a) / Σ_a diaries(a)

    units: minutes per day.

    Worked example: the child band (6, 17) reads 170.9 min/day over 88,763
    diaries — against the 24.5 `care_curve` reports, which is an ATUS figure
    observed only on ages 15–17 and diluted across the whole band by counting
    6–14 as zero.

    Raises:
        ValueError: if the band is empty or reversed.
    """
    if lo > hi:
        raise ValueError(f"band ({lo}, {hi}) is reversed")
    rows = [r for r in load_by_age() if lo <= r["age"] <= hi]
    if not rows:
        raise ValueError(f"no ages in band ({lo}, {hi})")
    diaries = sum(r["diaries"] for r in rows)
    return {
        "lo": float(lo),
        "hi": float(hi),
        "minutes_per_day": sum(r["minutes_per_day"] * r["diaries"] for r in rows) / diaries,
        "diaries": diaries,
        "min_samples": min(r["samples"] for r in rows),
    }


def band_ratio(lo: int, hi: int, working_age: tuple[int, int] = (18, 64)) -> float:
    """
    Self-maintenance in a band relative to working age, in MTUS's own units.

    The RATIO is what transfers to the repo's frame; the LEVEL does not, because
    meals are in this definition and not in the repo's. Transferring a ratio
    across two definitions is an assumption, and the module docstring states
    which way it errs.

    units: dimensionless.

    Worked example: child (6, 17) → 0.648.
    """
    return band_minutes(lo, hi)["minutes_per_day"] / band_minutes(*working_age)["minutes_per_day"]
