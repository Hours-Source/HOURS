"""
Measured care demand by recipient age — ATUS 2003–2025, US Census 2020–2025.

The cut `AGE_GROUPS`' epistemic pointer has always named and nothing had made:
who RECEIVES care, at what age, and how much. `reference/atus_time_use.py` cuts
the same survey by ACTIVITY, which answers who provides it.

What it reads (all written by `utils/atus_care_ingest.py` and
`utils/census_age_ingest.py`, all committed, raw files gitignored):

    data/atus_care_by_age_0325.csv     roster route, per person-day by age
    data/atus_care_eldercare_1125.csv  eldercare module route, per recipient-day
    data/atus_care_rivalry_0325.csv    care time by dependant count, fitted ρ
    data/atus_care_coverage_0325.csv   care that could not be attributed, and why
    data/census_age_2020_2025.csv      population by single year of age

Native unit is minutes per person-day. No annualizing convention and no
per-capita bridge is applied here; those are the caller's, as in
`atus_time_use.py`.

TWO THINGS THIS MODULE REPORTS SEPARATELY, AND WHY
---------------------------------------------------
**Individual demand** — what one person of age a receives — is the `dup`
attribution: a care activity credits its full duration to each recipient
present. A bedtime story read to two children is a whole story each.

**The joint saving** — what a collective saves by serving n such people together
— is the rivalry exponent ρ, carried as its own number. Care time scales as
T(n) = T(1)·n^ρ in the dependant count, measured at ρ ≈ 0.27 active and ≈ 0.10
passive against ρ=1 fully rivalrous and ρ=0 fully shared.

Keeping them apart is the point. Folding ρ into the curve would hide the
sub-additivity inside a per-person number, where no caller could see it or vary
it; and a per-person curve that already embedded a household composition could
not be applied to a collective with a different one.

HONEST LIMITS — read before citing any figure from here
--------------------------------------------------------
1. **ONE DIARY PER HOUSEHOLD.** ATUS samples one adult per household, so care
   delivered by a non-diarised co-resident is invisible. Every figure here is
   care from ONE provider, and becoming care RECEIVED needs scaling by the
   number of adult caregivers in the household. That correction is large and is
   deliberately NOT applied — `providers_per_household()` exposes the input so a
   caller applies it knowingly or not at all.
2. **ρ IS NOT IDENTIFIED.** The measured exponent conflates the care technology
   (how rival attention really is) with the behavioural response (whether
   parents add time for a second child). Under full compensation the two cancel
   and per-child care is invariant to family size; under none it falls as 1/n.
   Nothing in this data adjudicates it, which is why the split (ρ=1) and
   duplicate (ρ=0) corners are shipped as their own columns rather than
   interpolated away. ρ is also cross-sectional — across households, not within
   — so household selection is uncontrolled.
3. **THE TWO ELDERLY ROUTES DISAGREE BY AN ORDER OF MAGNITUDE, and the roster
   one is an artefact.** 81.6% of eldercare recipients are not household
   members, so the roster join structurally cannot see them and reads 65+ care
   as barely above working-age. The module route sees them. Both are reported;
   `elderly_route_disagreement()` states the ratio. Do not average them.
4. **ELDERCARE IS DEFINED BY NEED, NOT AGE.** ATUS eldercare recipients appear
   from age 45, and the 45–64 band receives MORE care than 65+. A curve indexed
   on age is therefore indexing a proxy. This is a limit of the framing, not of
   the data.
5. **PASSIVE CARE STOPS AT 12.** Secondary childcare is collected for under-13s
   only, so ages 13–17 have no passive measure. Those cells are EMPTY, never
   zero — a zero would assert that nobody supervises a fifteen-year-old.
   `passive_measured_ages()` gives the range that exists.
6. **US-SPECIFIC, one jurisdiction at one time.** Care arrangements are
   institutions as much as biology. Cross-country panels are what would separate
   a physical requirement from a national arrangement; nothing here can.
7. **OBSERVED HOURS ARE NOT AN OBLIGATION.** The identity
   `observed = obligation − deferred + extraction` applies here exactly as it
   does in `atus_time_use.py`. Care that a household could not deliver leaves no
   diary trace.

Layer rule: `reference/` imports nothing from the package — stdlib only, reading
shipped data files.
"""

from __future__ import annotations

import csv
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_BY_AGE_FILE = _DATA_DIR / "atus_care_by_age_0325.csv"
_ELDER_FILE = _DATA_DIR / "atus_care_eldercare_1125.csv"
_RIVALRY_FILE = _DATA_DIR / "atus_care_rivalry_0325.csv"
_COVERAGE_FILE = _DATA_DIR / "atus_care_coverage_0325.csv"
_CENSUS_FILE = _DATA_DIR / "census_age_2020_2025.csv"
_SELF_FILE = _DATA_DIR / "atus_self_maintenance_0325.csv"

#: ATUS surveys nobody younger, so self-maintenance below this age is UNMEASURED.
SELF_MAINTENANCE_MIN_AGE: int = 15

#: Attribution settings shipped side by side. See the module docstring.
ATTRIBUTIONS: tuple[str, ...] = ("dup", "rho", "split")

#: The attribution that reads as INDIVIDUAL demand, and the curve's default.
DEFAULT_ATTRIBUTION = "dup"

#: Highest age for which ATUS collects secondary (passive) childcare.
PASSIVE_MAX_AGE: int = 12

#: ATUS top-codes both roster age (TEAGE) and eldercare recipient age (TEAGE_EC)
#: at 85, so the 85 cell means "85 AND OVER". Any denominator taken from another
#: source must be folded to match, or the oldest cell divides a top-coded
#: numerator by a single-year population and reports a per-person figure several
#: times the length of a day.
ATUS_TOP_CODED_AGE: int = 85

# MINUTES_PER_HOUR REMOVED 2026-08-28. It was declared here and read by
# NOTHING — a dead duplicate of the live one in reference/atus_time_use.py,
# which does the minute→hour conversion. This module's own header says its
# native unit is minutes per person-day with no annualizing convention, so the
# constant was vestigial. Removing the duplicate is the fix; pinning it would
# have preserved a second definition of an already-defined quantity.
DAYS_PER_YEAR: float = 365.0


@dataclass(frozen=True)
class CareRow:
    """Care received per person-day by one single year of recipient age."""

    year: int
    age: int
    active: dict[str, float]
    #: Empty above ``PASSIVE_MAX_AGE`` — unmeasured, not zero.
    passive: dict[str, float]
    person_days: float
    passive_measured: bool
    comparable: bool


def _f(cell: str) -> float | None:
    return float(cell) if cell not in ("", None) else None


@lru_cache(maxsize=1)
def _by_age() -> tuple[CareRow, ...]:
    with _BY_AGE_FILE.open(newline="") as fh:
        rows = []
        for r in csv.DictReader(fh):
            active = {a: v for a in ATTRIBUTIONS
                      if (v := _f(r[f"active_{a}"])) is not None}
            passive = {a: v for a in ATTRIBUTIONS
                       if (v := _f(r[f"passive_{a}"])) is not None}
            rows.append(CareRow(
                year=int(r["year"]), age=int(r["recipient_age"]),
                active=active, passive=passive,
                person_days=float(r["person_days"]),
                passive_measured=r["passive_measured"] == "true",
                comparable=r["comparable"] == "true",
            ))
    return tuple(rows)


@lru_cache(maxsize=1)
def _rivalry() -> tuple[dict[str, object], ...]:
    with _RIVALRY_FILE.open(newline="") as fh:
        return tuple(dict(r) for r in csv.DictReader(fh))


@lru_cache(maxsize=1)
def _census() -> dict[int, dict[int, float]]:
    out: dict[int, dict[int, float]] = {}
    with _CENSUS_FILE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(int(r["year"]), {})[int(r["age"])] = float(r["population"])
    return out


def survey_years(include_incomparable: bool = False) -> tuple[int, ...]:
    """Years present in the care extract, 2020 excluded unless asked for."""
    years = {r.year for r in _by_age()
             if include_incomparable or r.comparable}
    return tuple(sorted(years))


def latest_year(include_incomparable: bool = False) -> int:
    return survey_years(include_incomparable)[-1]


def rivalry_exponent(kind: str) -> float:
    """ρ for ``"active"`` or ``"passive"``, fitted over dependant counts.

    Not identified — see limit 2. Callers wanting the corners should read the
    ``split`` (ρ=1) and ``dup`` (ρ=0) attributions instead of substituting a
    value here.
    """
    for row in _rivalry():
        if row["kind"] == kind:
            return float(str(row["fitted_rho"]))
    raise KeyError(f"no rivalry exponent for {kind!r}; have active, passive")


def rivalry_table(kind: str) -> dict[int, float]:
    """Mean care minutes per case-day against dependant count — ρ's evidence."""
    return {
        int(str(r["dependants"])): float(str(r["mean_minutes_per_case_day"]))
        for r in _rivalry() if r["kind"] == kind
    }


def joint_cost(n: int, kind: str = "active") -> float:
    """Cost of serving ``n`` equivalent recipients, relative to serving one.

    ``n^ρ``. This is the joint-production saving stated as a multiplier: at
    ρ=0.27, four dependants cost 1.44× one, not 4×. The saving is real and is
    what makes a collective cheaper than n households — but see limit 2 before
    treating ρ as measured rather than bounded.
    """
    if n <= 0:
        return 0.0
    return float(n) ** rivalry_exponent(kind)


def _target_years(year: int | tuple[int, ...] | None) -> frozenset[int]:
    if year is None:
        return frozenset({latest_year()})
    if isinstance(year, int):
        return frozenset({year})
    return frozenset(year)


def care_by_age(
    year: int | tuple[int, ...] | None = None,
    attribution: str = DEFAULT_ATTRIBUTION,
) -> dict[int, dict[str, float | None]]:
    """``age → {"active", "passive", "total"}`` minutes per person-day.

    ``year`` takes one year, or a tuple of years to POOL. Pooling weights each
    year by its person-days, which is what a frozen constant should rest on — a
    single year of one age's cell is thin enough that the curve would carry
    sampling noise as though it were shape.

    ``passive`` and ``total`` are ``None`` above :data:`PASSIVE_MAX_AGE`, where
    no passive measure exists. A caller wanting a number there must decide what
    to do about it; this module will not choose zero on their behalf.
    """
    if attribution not in ATTRIBUTIONS:
        raise ValueError(
            f"unknown attribution {attribution!r}; have {', '.join(ATTRIBUTIONS)}"
        )
    targets = _target_years(year)
    num: dict[int, dict[str, float]] = {}
    den: dict[int, dict[str, float]] = {}
    measured: dict[int, bool] = {}
    for row in _by_age():
        if row.year not in targets:
            continue
        n = num.setdefault(row.age, {"active": 0.0, "passive": 0.0})
        d = den.setdefault(row.age, {"active": 0.0, "passive": 0.0})
        n["active"] += row.active.get(attribution, 0.0) * row.person_days
        d["active"] += row.person_days
        measured[row.age] = measured.get(row.age, False) or row.passive_measured
        if row.passive_measured and attribution in row.passive:
            n["passive"] += row.passive[attribution] * row.person_days
            d["passive"] += row.person_days
    if not num:
        raise KeyError(f"no care data for {sorted(targets)}; have {survey_years()}")
    out: dict[int, dict[str, float | None]] = {}
    for age in sorted(num):
        active = num[age]["active"] / den[age]["active"] if den[age]["active"] else 0.0
        passive = (
            num[age]["passive"] / den[age]["passive"]
            if measured[age] and den[age]["passive"] else None
        )
        out[age] = {
            "active": active,
            "passive": passive,
            "total": None if passive is None else active + passive,
        }
    return out


def elderly_by_age(
    year: int | None = None, household_only: bool | None = None
) -> dict[int, float]:
    """Module route: ``recipient age → eldercare minutes per RECIPIENT-day``.

    Denominator is recipient-days, not population — this is care per person
    receiving it, conditional on receiving any. Use
    :func:`elderly_per_capita` for a population-basis figure comparable with
    :func:`care_by_age`.
    """
    target = latest_year() if year is None else year
    num: dict[int, float] = {}
    den: dict[int, float] = {}
    with _ELDER_FILE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["year"]) != target:
                continue
            if household_only is not None:
                if (r["household_member"] == "1") != household_only:
                    continue
            age, days = int(r["recipient_age"]), float(r["recipient_days"])
            minutes = _f(r["minutes_per_recipient_day"])
            if minutes is None or days <= 0.0:
                continue
            num[age] = num.get(age, 0.0) + minutes * days
            den[age] = den.get(age, 0.0) + days
    return {a: num[a] / den[a] for a in sorted(num) if den[a] > 0.0}


def elderly_per_capita(
    year: int | tuple[int, ...] | None = None,
    household_only: bool | None = None,
) -> dict[int, float]:
    """Module route on a POPULATION basis — minutes per person-day of age a.

    The bridge the two routes need to be comparable at all: ATUS supplies the
    numerator (eldercare minutes delivered nationally, scaled by the survey
    weights) and the Census supplies the denominator (people of that age). ATUS
    cannot supply the denominator itself, because most eldercare recipients are
    not on any sampled household's roster.
    """
    targets = _target_years(year)
    census = _census()
    num: dict[int, float] = {}
    pop_days: dict[int, float] = {}
    with _ELDER_FILE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            row_year = int(r["year"])
            if row_year not in targets:
                continue
            if household_only is not None:
                if (r["household_member"] == "1") != household_only:
                    continue
            minutes = _f(r["minutes_per_recipient_day"])
            if minutes is None:
                continue
            age = int(r["recipient_age"])
            num[age] = num.get(age, 0.0) + minutes * float(r["recipient_days"])
    # One population-year per survey-year, nearest available, so a pooled read
    # divides by the population that was actually there in each of its years.
    for row_year in sorted(targets):
        pop_year = min(census, key=lambda y: abs(y - row_year))
        for age, people in census[pop_year].items():
            # Fold everyone above the ATUS top code into it, so the 85 cell's
            # denominator is the 85-AND-OVER population its numerator describes.
            bucket = min(age, ATUS_TOP_CODED_AGE)
            pop_days[bucket] = pop_days.get(bucket, 0.0) + people * DAYS_PER_YEAR
    out: dict[int, float] = {}
    for age, total in num.items():
        exposure = pop_days.get(min(age, ATUS_TOP_CODED_AGE))
        if exposure:
            out[age] = total / exposure
    return dict(sorted(out.items()))


def elderly_route_disagreement(
    year: int | tuple[int, ...] | None = None, from_age: int = 65
) -> dict[str, float]:
    """The two elderly readings and the ratio between them.

    Reported, never reconciled. The roster route is an artefact of a join that
    cannot see non-household recipients; the module route is the one to use.
    Averaging them would produce a number describing nothing.
    """
    target = latest_year() if year is None else year
    roster = care_by_age(target)
    module = elderly_per_capita(target)
    ages = [a for a in roster if a >= from_age]
    roster_mean = (
        sum(float(roster[a]["active"] or 0.0) for a in ages) / len(ages)
        if ages else 0.0
    )
    module_ages = [a for a in module if a >= from_age]
    module_mean = (
        sum(module[a] for a in module_ages) / len(module_ages)
        if module_ages else 0.0
    )
    return {
        "roster_minutes_per_person_day": roster_mean,
        "module_minutes_per_person_day": module_mean,
        "ratio": module_mean / roster_mean if roster_mean else float("inf"),
        "from_age": float(from_age),
    }


def population_shares(bands: dict[str, tuple[int, int]],
                      year: int | None = None) -> dict[str, float]:
    """Measured population share per age band — the `fraction` half of AGE_GROUPS."""
    census = _census()
    target = max(census) if year is None else year
    if target not in census:
        raise KeyError(f"no census data for {target}; have {sorted(census)}")
    population = census[target]
    total = sum(population.values())
    top = max(population)
    return {
        name: sum(population.get(a, 0.0) for a in range(lo, min(hi, top) + 1)) / total
        for name, (lo, hi) in bands.items()
    }


def providers_per_household(year: int | None = None) -> float:
    """Adults per household — the scaling limit 1 describes, exposed not applied.

    ATUS diarises one adult, so multiplying by this is what turns care from one
    provider into care received. It is NOT applied anywhere in this module,
    because doing it silently would inflate every figure by a factor a reader
    could not see.
    """
    raise NotImplementedError(
        "adults-per-household is not yet extracted — see limit 1. Until it is, "
        "every figure in this module is care from ONE provider, and that is "
        "stated rather than silently corrected."
    )


def self_maintenance_by_age(
    year: int | tuple[int, ...] | None = None
) -> dict[int, float]:
    """``age → own personal-maintenance minutes per day``, 15+ only.

    Personal care excluding SLEEP, plus household activities. Sleep is excluded
    because personal EOH is the labour required to resist entropy for a person,
    not the hours that person exists — at ~8.5 h/day it would swamp every other
    term.

    Ages below :data:`SELF_MAINTENANCE_MIN_AGE` are ABSENT, not zero. ATUS does
    not survey children. Near-zero is plausible for an infant and plainly wrong
    for a twelve-year-old, and nothing here says where in between.
    """
    targets = _target_years(year)
    num: dict[int, float] = {}
    den: dict[int, float] = {}
    with _SELF_FILE.open(newline="") as fh:
        for r in csv.DictReader(fh):
            if int(r["year"]) not in targets:
                continue
            minutes = _f(r["minutes_per_day"])
            days = float(r["person_days"])
            if minutes is None or days <= 0.0:
                continue
            age = int(r["age"])
            num[age] = num.get(age, 0.0) + minutes * days
            den[age] = den.get(age, 0.0) + days
    return {a: num[a] / den[a] for a in sorted(num) if den[a] > 0.0}


def personal_profile(
    year: int | tuple[int, ...] | None = None,
    attribution: str = DEFAULT_ATTRIBUTION,
) -> dict[int, dict[str, float | None]]:
    """``age → {"self", "care", "total"}`` minutes per person-day.

    THE quantity `AGE_GROUPS`' `eoh_weight` is a relative measure of: the whole
    personal obligation attached to a person of that age, however it is served.

        total = self-maintenance + care received from others

    Reading the profile off care alone is the error this function exists to
    prevent. Care received says an infant generates ~25× a working-age adult,
    because it counts everything done FOR the infant and nothing an adult does
    for themselves. Adding self-maintenance brings that to ~3×, which is what
    the shipped weight of 3.0 says.

    ``self`` and ``total`` are ``None`` below
    :data:`SELF_MAINTENANCE_MIN_AGE` — the hole is left open rather than filled
    with a zero that would overstate a child's obligation, or with an assumption
    that would look like a measurement.
    """
    care = care_by_age(year, attribution)
    elder = elderly_per_capita(year, household_only=False)
    own = self_maintenance_by_age(year)
    out: dict[int, dict[str, float | None]] = {}
    for age in sorted(care):
        active = float(care[age]["active"] or 0.0)
        passive = care[age]["passive"]
        received = active + float(passive or 0.0) + elder.get(age, 0.0)
        mine = own.get(age)
        out[age] = {
            "self": mine,
            "care": received,
            "total": None if mine is None else mine + received,
        }
    return out


def band_relative_demand(
    bands: dict[str, tuple[int, int]],
    numeraire: str,
    year: int | tuple[int, ...] | None = None,
    population_year: int | None = None,
) -> dict[str, dict[str, float | None]]:
    """Population-weighted personal obligation per band, relative to ``numeraire``.

    The implied `eoh_weight`, and the reason it is reported rather than adopted:
    every band containing an age below :data:`SELF_MAINTENANCE_MIN_AGE` has an
    unmeasured component, so its ``total`` is a LOWER bound and is flagged
    ``complete=False``. Bands are weighted by census population within the band,
    so a band is not the unweighted mean of its single-year cells.
    """
    profile = personal_profile(year)
    census = _census()
    pop_year = max(census) if population_year is None else population_year
    population = census[pop_year]
    top = max(profile)

    out: dict[str, dict[str, float | None]] = {}
    for name, (lo, hi) in bands.items():
        weight = care_num = self_num = 0.0
        complete = True
        for age in range(lo, hi + 1):
            people = population.get(age, 0.0)
            cell = profile.get(min(age, top))
            if not people or cell is None:
                continue
            weight += people
            care_num += people * float(cell["care"] or 0.0)
            if cell["self"] is None:
                complete = False
            else:
                self_num += people * float(cell["self"])
        out[name] = {
            "care": care_num / weight if weight else None,
            "self": self_num / weight if weight else None,
            "total": (care_num + self_num) / weight if weight else None,
            "complete": complete,
        }
    base = out[numeraire]["total"]
    for cell in out.values():
        total = cell["total"]
        cell["relative"] = (
            float(total) / float(base)
            if base is not None and base and total is not None else None
        )
    return out


def passive_measured_ages() -> tuple[int, int]:
    """Inclusive age range over which a passive measure exists."""
    return (0, PASSIVE_MAX_AGE)


def coverage() -> tuple[dict[str, str], ...]:
    """Care that could not be attributed, with the reason — never costed as zero."""
    with _COVERAGE_FILE.open(newline="") as fh:
        return tuple(dict(r) for r in csv.DictReader(fh))


def curve_knots(
    ages: tuple[int, ...],
    year: int | tuple[int, ...] | None = None,
    attribution: str = DEFAULT_ATTRIBUTION,
) -> dict[str, dict[int, float]]:
    """Care demand in minutes per person-day at the given knot ages.

    NOTHING MIRRORS THIS, and the docstring used to claim `data.py` did (found
    2026-08-17 by a dead-code sweep: this function is referenced nowhere, not
    even by a test, and no constant in `data.py` carries any of the values it
    returns). The claim is removed rather than the function, because the
    function is correct and the measured curve is the thing a future age-weight
    derivation would use — but an unexercised accessor asserting a mirror that
    does not exist is worse than an unexercised accessor.

    Three series, kept SEPARATE because they are
    measured on different bases and one of them stops at 12:

        active        primary care from a co-resident, all ages
        passive       secondary childcare from a co-resident, ages 0–12 only
        elder_nonhh   eldercare delivered to NON-household recipients

    ``elder_nonhh`` excludes household recipients ON PURPOSE. Care for a
    co-resident elderly person is already in ``active`` as a primary care
    activity, so adding the unfiltered module route would count it twice. The
    two streams as shipped are disjoint and additive.

    Absolute minutes rather than a normalised index: the numbers stay directly
    checkable against the extract, and the choice of numeraire is then made once
    in `core/care.py` where it is visible, instead of being baked in here.
    """
    care = care_by_age(year, attribution)
    elder = elderly_per_capita(year, household_only=False)
    top = max(care)

    def active_at(age: int) -> float:
        return float(care.get(min(age, top), {}).get("active") or 0.0)

    def passive_at(age: int) -> float:
        value = care.get(min(age, top), {}).get("passive")
        return float(value) if value is not None else 0.0

    return {
        "active": {a: active_at(a) for a in ages},
        "passive": {a: passive_at(a) for a in ages if a <= PASSIVE_MAX_AGE},
        "elder_nonhh": {
            a: elder.get(min(a, ATUS_TOP_CODED_AGE), 0.0) for a in ages
        },
    }
