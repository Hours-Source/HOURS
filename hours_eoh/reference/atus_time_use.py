"""
Measured US time use — the American Time Use Survey, 2003–2025.

The repo's most-named unclaimed measurement. Three separate findings pointed at
ATUS before anything read it: `PERSONAL_EOH_BASE`'s epistemic pointer, the
`AGE_GROUPS` weights, and the labour-supply side of ε_ref. This module is the
measurement layer for all three — it reports hours, and nothing else.

What it reads
-------------
`data/atus_annual_0325.csv` and `data/atus_years_0325.csv`, written by
`utils/atus_ingest.py` from the BLS multi-year microdata (258,954 respondents,
2003–2025). The raw files are ~2.9 GB and are not shipped; these extracts are,
on the same pattern as the O*NET multiplier registry.

Native unit is mean minutes per day per person aged 15+. Two conversions are the
CALLER's, and both are exposed rather than baked in:

    hours per person 15+ per year  =  minutes/day × 365 / 60
    hours per capita (all ages)    =  the above × population_15_plus / total_pop

HONEST LIMITS — read before citing any figure from here
--------------------------------------------------------
1. **15 AND OVER ONLY.** ATUS does not survey children, so household and care
   work performed by under-15s is absent. In the US that is small; in a
   subsistence collective it is not, which is exactly why this module refuses to
   emit a per-capita figure without being told the population it is dividing by.
2. **2020 IS NOT COMPARABLE** and is excluded from `series()` by default.
   Collection was suspended mid-March to mid-May 2020, so the estimates cover
   roughly May–December and use a different weight (`TU20FWGT`). It is present in
   the data and reachable with `include_incomparable=True`; it is never pooled
   silently.
3. **PRIMARY ACTIVITIES ONLY.** A diary records one activity at a time, so
   simultaneous work is undercounted — supervising a child while cooking books as
   cooking. Secondary childcare is a separate ATUS field THIS extract does not
   carry, and it is large: measured against the same file it runs about 4× the
   primary care time. Every care figure here is therefore a LOWER BOUND.
   `reference/care_demand.py` carries it, cut by recipient age, along with the
   eldercare module — use that module for anything about care, and this one for
   anything about activities.
4. **OBSERVED HOURS ARE NOT AN OBLIGATION.** This is the load-bearing limit.
   What a population spends is what it spends; the entropy obligation is a
   different quantity, related by

       observed = obligation − deferred + extraction

   where `deferred` is obligation gone unserved (visible physiologically, not in
   a diary) and `extraction` is institutionally-induced hours that resist no
   entropy. Neither is identified by time use alone. Read
   `hours_eoh/scenarios/personal_floor.py` before treating any number here as a
   calibration target.
5. **US-specific, and the US is one point.** These are the institutions of one
   country. Cross-country panels (HETUS/MTUS) are what would separate a physical
   requirement from a national arrangement; nothing here can.
6. **Diary recall, single day.** Standard ATUS caveats apply: one 24-hour recall
   per respondent, day-of-week weighted, no within-person time series.

Layer rule: `reference/` imports nothing from hours_eoh core/land/scenarios/data —
this module reads only shipped data files via the standard library.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

_DATA_DIR = Path(__file__).resolve().parent / "data"
_ANNUAL_FILE = _DATA_DIR / "atus_annual_0325.csv"
_YEARS_FILE = _DATA_DIR / "atus_years_0325.csv"

#: ATUS annualizing convention: diary minutes/day → hours/year. Named for the
#: survey, not generically, because `personal_basket.DIET_DAYS_PER_YEAR` is a
#: different convention (365.25) living one module away.
ATUS_DAYS_PER_YEAR: float = 365.0
MINUTES_PER_HOUR: float = 60.0


class YearRow(NamedTuple):
    """One survey year's frame. `comparable` is False where collection was partial."""

    year: int
    n_respondents: int
    population_15_plus: float
    mean_household_size: float
    mean_age: float
    weight_variable: str
    comparable: bool


@lru_cache(maxsize=1)
def _years() -> tuple[YearRow, ...]:
    with _YEARS_FILE.open(newline="") as fh:
        return tuple(
            YearRow(
                year=int(r["year"]),
                n_respondents=int(r["n_respondents"]),
                population_15_plus=float(r["population_15_plus"]),
                mean_household_size=float(r["mean_household_size"]),
                mean_age=float(r["mean_age"]),
                weight_variable=r["weight_variable"],
                comparable=r["comparable"].strip().lower() == "true",
            )
            for r in csv.DictReader(fh)
        )


@lru_cache(maxsize=1)
def _minutes() -> dict[int, dict[str, float]]:
    table: dict[int, dict[str, float]] = {}
    with _ANNUAL_FILE.open(newline="") as fh:
        for row in csv.DictReader(fh):
            table.setdefault(int(row["year"]), {})[row["tier2"]] = float(
                row["mean_minutes_per_day"]
            )
    return table


def survey_years(include_incomparable: bool = False) -> tuple[YearRow, ...]:
    """
    The survey frame for every year in the extract, oldest first.

    2020 is omitted unless `include_incomparable` — see limit 2. Its row carries
    `comparable=False` and `weight_variable='TU20FWGT'` so the reason travels
    with the data rather than living in a comment.
    """
    rows = _years()
    return rows if include_incomparable else tuple(r for r in rows if r.comparable)


def latest_year(include_incomparable: bool = False) -> int:
    """The most recent survey year available."""
    return survey_years(include_incomparable)[-1].year


def minutes_per_day(year: int) -> dict[str, float]:
    """
    Mean minutes per day per person 15+, by tier-2 activity code, for one year.

    The ATUS native unit. Summing every code returns 1440 by construction — a
    diary accounts for the whole day — which is the arithmetic check on this
    whole chain (`test_day_sums_to_1440`).

    Raises:
        KeyError: if the year is not in the extract.
    """
    table = _minutes()
    if year not in table:
        raise KeyError(f"year {year} not in the ATUS extract; have {sorted(table)}")
    return dict(table[year])


def hours_per_person_15plus(year: int, codes: tuple[str, ...]) -> float:
    """
    Hours per person aged 15+ per year, over a set of tier-1 or tier-2 codes.

    Governing equation:

        h = Σ_code  minutes_per_day(code) × 365 / 60

    A code is matched by prefix, so "02" takes the whole tier-1 category and
    "0202" takes food preparation alone.

    units: hours per person aged 15+ per year.

    Worked example: `hours_per_person_15plus(2025, ("0202",))` = 259.8 — food
    preparation, presentation and cleanup, up from 194.3 in 2003.
    """
    total = sum(
        minutes for code, minutes in minutes_per_day(year).items()
        if any(code.startswith(prefix) for prefix in codes)
    )
    return total * ATUS_DAYS_PER_YEAR / MINUTES_PER_HOUR


def tier1_hours(year: int) -> dict[str, float]:
    """Hours per person 15+ per year for every tier-1 category, for one year."""
    per_day = minutes_per_day(year)
    totals: dict[str, float] = {}
    for code, minutes in per_day.items():
        totals[code[:2]] = totals.get(code[:2], 0.0) + minutes
    return {
        tier1: value * ATUS_DAYS_PER_YEAR / MINUTES_PER_HOUR
        for tier1, value in sorted(totals.items())
    }


def series(
    codes: tuple[str, ...],
    include_incomparable: bool = False,
) -> dict[int, float]:
    """
    The 2003–2025 series for a set of activity codes, in hours per person 15+.

    ε-behavior: none — this is a measurement over calendar time, not over the
    automation arc. Reading it AS an ε arc requires a capital series to index it
    by, which this module does not have and does not invent.

    units: {year: hours per person aged 15+ per year}.

    Worked example: `series(("0202",))` runs 194.3 (2003) → 259.8 (2025). Over
    the same period grocery shopping ("0701") falls 146.4 → 108.9. Provisioning
    automated; preparation did not.
    """
    return {
        row.year: hours_per_person_15plus(row.year, codes)
        for row in survey_years(include_incomparable)
    }


def per_capita_scale(year: int, total_population: float) -> float:
    """
    The 15+ → all-ages bridge: multiply a per-person-15+ figure by this.

    Deliberately explicit. ATUS covers ages 15 and over; every EOH quantity in
    this repo is per capita over the whole population, and silently equating the
    two would overstate per-capita hours by ~20% in the US and by far more in a
    young population.

    Governing equation:  scale = population_15_plus(year) / total_population

    units: dimensionless.

    Worked example: 2025, against a 335e6 total population → 0.8298.

    SERIES TRAP. Holding one `total_population` fixed across survey years is
    WRONG: population_15_plus runs 225.3M (2003) → 278.0M (2025), so a constant
    denominator manufactures a spurious +23% trend. It turned a measured −26%
    into −8% once already. Per-capita conversion is valid at a single year; a
    historical per-capita series needs a matching total-population series, which
    this extract does not carry. Report `series()` in its native per-person-15+
    unit instead.

    Raises:
        ValueError: if total_population is not positive.
        KeyError: if the year is not in the extract.
    """
    if total_population <= 0.0:
        raise ValueError(f"total_population must be positive, got {total_population}")
    for row in _years():
        if row.year == year:
            return row.population_15_plus / total_population
    raise KeyError(f"year {year} not in the ATUS extract")


def hours_per_capita(
    year: int,
    codes: tuple[str, ...],
    total_population: float,
) -> float:
    """
    Hours per capita (ALL ages) per year — the unit every EOH quantity uses.

    Governing equation:

        h_capita = hours_per_person_15plus × population_15_plus / total_population

    units: hours per capita per year.

    Worked example: 2025, unpaid household and care work ("02", "03", "04"),
    335e6 population → 763.8 h/person·yr. This is the figure comparable to
    `PERSONAL_EOH_BASE`, and limit 4 in the module docstring governs how.
    """
    return hours_per_person_15plus(year, codes) * per_capita_scale(year, total_population)
