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
from functools import lru_cache
import pathlib

__all__ = [
    "DATA_FILE",
    "DOMESTIC_FILE",
    "domestic_by_sample",
    "domestic_series",
    "LABOUR_AGGREGATES",
    "measured_capacity",
    "capacity_frames",
    "NONSTANDARD_DAY_SAMPLES",
    "day_closes",
    "CODES_FILE",
    "codes_by_sample",
    "code_minutes",
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


DOMESTIC_FILE = pathlib.Path(__file__).with_name("data") / "mtus_domestic_by_sample.csv"

#: Samples whose twelve ACT_* aggregates do NOT sum to a 1440-minute day.
#: DECLARED, not dropped: an extract that silently omits a sample is one whose
#: coverage cannot be audited. Every row of FR1999 sums to exactly 1680 minutes
#: — a 28-hour day, uniform across all 15,441 diaries — while its own siblings
#: FR1985 and FR2009 are exactly 1440. A uniform factor of 7/6 on every row is a
#: scaling or units defect in the harmonisation, not over-reporting by
#: respondents, so the COMPOSITION is probably intact and the LEVEL is not. No
#: correction is applied here: rescaling would assume the composition is right,
#: which is the assumption most likely to be wrong if the defect is something
#: else. Use the sample for shares if you must; do not use it for levels.
NONSTANDARD_DAY_SAMPLES: dict[str, str] = {
    "FR1999": "every row sums to 1680 minutes (28 h), a uniform 7/6 of a day",
}


def day_closes(sample: str) -> bool:
    """Whether a sample's aggregates sum to a 1440-minute day."""
    return sample not in NONSTANDARD_DAY_SAMPLES


@lru_cache(maxsize=1)
def domestic_by_sample() -> list[dict[str, float | str | int]]:
    """
    Unpaid domestic work and childcare, minutes per day, one row per MTUS sample.

    Ages 18-69 (the band every one of the 50 samples covers) weighted by
    `PROPWT`. `day_minutes` is the twelve ACT_* aggregates summed and is 1440.0
    by construction — the arithmetic check that the units are minutes per day,
    which matters because MTUS ships no codebook with this extract.

    Derived by `utils/mtus_domestic_ingest.py`; the raw file is gitignored.
    """
    rows: list[dict[str, float | str | int]] = []
    with DOMESTIC_FILE.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append({
                "sample": row["sample"],
                "country": row["country"],
                "year": int(row["year"]),
                "n_respondents": int(row["n_respondents"]),
                "undom_minutes_per_day": float(row["undom_minutes_per_day"]),
                "chcare_minutes_per_day": float(row["chcare_minutes_per_day"]),
                "work_minutes_per_day": float(row["work_minutes_per_day"]),
                "travel_minutes_per_day": float(row["travel_minutes_per_day"]),
                "educa_minutes_per_day": float(row["educa_minutes_per_day"]),
                "day_minutes": float(row["day_minutes"]),
            })
    return rows


CODES_FILE = pathlib.Path(__file__).with_name("data") / "mtus_codes_by_sample.csv"


@lru_cache(maxsize=1)
def codes_by_sample() -> dict[str, dict[int, float]]:
    """
    Minutes per day by MTUS activity code, per sample, ages 18-69.

    The six-digit episode file carries 56-67 distinct codes per sample against
    the twelve `ACT_*` aggregates, which is what separates nutrition from
    shelter. NO MAPPING IS APPLIED HERE — the codes ship raw and the
    code→component judgement lives in `scenarios/automation_floors`, declared
    and validated there.

    AT1992, FR1985 and FR1999 are ABSENT: `SERIAL` is empty in those three
    samples so the episode join cannot reach them. Recorded rather than hidden.

    Derived by `utils/mtus_code_ingest.py`; the 3.1 GB raw file is gitignored.
    """
    out: dict[str, dict[int, float]] = {}
    with CODES_FILE.open(newline="") as fh:
        for row in csv.DictReader(fh):
            out.setdefault(row["sample"], {})[int(row["code"])] = float(
                row["minutes_per_day"]
            )
    return out


def code_minutes(sample: str, codes: tuple[int, ...]) -> float:
    """Minutes per day for a set of activity codes in one sample."""
    table = codes_by_sample()
    if sample not in table:
        raise KeyError(f"{sample} not in the code extract; have {len(table)} samples")
    return sum(table[sample].get(code, 0.0) for code in codes)


#: MINUTES PER DAY -> HOURS PER YEAR. MTUS diaries are a 24-hour day, so the
#: conversion is the calendar and carries no work-year convention in it — which
#: is the whole point of using it in place of one.
_MIN_PER_DAY_TO_H_PER_YEAR: float = 365.25 / 60.0

#: The aggregates summed into measured entropy-resistance labour. Paid work,
#: unpaid domestic work and childcare — the three that are unambiguously labour
#: someone performs against an obligation. `ACT_TRAVEL` and `ACT_EDUCA` are
#: SHIPPED but NOT summed: commuting is arguable and education is investment in
#: the knowledge domain rather than service of it, and folding either in would
#: raise every figure by a judgement nobody has made. Vary it by passing
#: `extra=` rather than by editing this.
LABOUR_AGGREGATES: tuple[str, ...] = (
    "work_minutes_per_day", "undom_minutes_per_day", "chcare_minutes_per_day",
)


def measured_capacity(sample: str, extra: tuple[str, ...] = ()) -> float:
    """
    Measured entropy-resistance labour, hours per adult per year, ages 18-69.

    This is the quantity `feasibility.labor_supply_per_capita` asks for — "hours
    per year one adult can devote to entropy-resistance labor" — measured
    rather than taken from a work-year convention. It counts paid work, unpaid
    domestic work and childcare; pass `extra` to add `travel_minutes_per_day`
    or `educa_minutes_per_day`.

    IT IS A FLOOR ON CAPACITY, NOT CAPACITY. These are hours people DID work,
    and capacity is what they COULD. Using observed as capacity therefore
    understates it, which is the conservative direction for a feasibility test:
    it makes clearing harder, not easier.

    Worked example: US1965 reads 263.0 + 170.7 + 28.8 = 462.5 min/day, which is
    2,815 h/yr. US2024 reads 231.5 + 121.0 + 28.7 = 381.2, or 2,321 h/yr.
    """
    rows = {str(r["sample"]): r for r in domestic_by_sample()}
    if sample not in rows:
        raise KeyError(f"{sample} not in the MTUS extract; have {len(rows)} samples")
    row = rows[sample]
    minutes = sum(float(row[k]) for k in LABOUR_AGGREGATES + extra)
    return minutes * _MIN_PER_DAY_TO_H_PER_YEAR


def capacity_frames(extra: tuple[str, ...] = ()) -> dict[str, float]:
    """
    Measured capacity for every MTUS sample: 50 frames over 1965-2024 and ten
    countries, each a year-and-place a feasibility run can be compared against.
    """
    return {
        str(r["sample"]): measured_capacity(str(r["sample"]), extra)
        for r in domestic_by_sample()
    }


def domestic_series(country: str) -> list[tuple[int, float]]:
    """(year, unpaid domestic minutes/day) for one country, oldest first."""
    return sorted(
        (int(r["year"]), float(r["undom_minutes_per_day"]))
        for r in domestic_by_sample()
        if r["country"] == country
    )


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
