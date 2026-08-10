"""
scenarios/care_curve — measured personal obligation by age vs the shipped weights.

REPORTING ONLY. Nothing here feeds `total_eoh`, `AGE_GROUPS`, or any fiscal
path; `TestCareCurveChangesNothing` fails the moment that stops being true.
Adopting these weights would move `w = Σ(fraction × eoh_weight)`, which
multiplies `PERSONAL_EOH_BASE` through the whole model — the same blast radius
as the 1,500 → 1,000 reprice, and the same requirement of an author decision.

WHAT IT MEASURES
----------------
`AGE_GROUPS`' `eoh_weight` is the personal EOH a person of that age GENERATES,
relative to a working-age adult. Two components, and taking either alone gets
the answer badly wrong:

    total(age) = self-maintenance(age) + care received from others(age)

Care received alone says an infant generates ~25× a working-age adult, because
it counts everything done FOR the infant and nothing an adult does for
themselves. Self-maintenance alone says an infant generates nothing. Together
they give ~2.6×, against a shipped 3.0.

Sleep is excluded from self-maintenance: personal EOH is the labour required to
resist entropy for a person, not the hours that person exists.

WHAT IT CANNOT SETTLE
---------------------
Two of the four bands are LOWER BOUNDS. ATUS surveys nobody under 15, so
self-maintenance is unmeasured for infants and for most of the child band; those
totals carry `complete=False` and can only rise.

The elderly band is complete and reads 41% below the shipped 2.5 — but ATUS
covers the HOUSEHOLD population only, and the institutionalised elderly are both
excluded and the highest-care group there is. The gap is a finding about
household-resident elderly, not about the elderly.

Mission Statement: §"Humans as capital stock" — the EOH weight system
distinguishes biological life stages, not economic productivity.
"""

from __future__ import annotations

from hours_eoh.data import AGE_GROUPS
from hours_eoh.reference import care_demand as cd

#: Survey years pooled for a stable read. A single year's single-year-of-age
#: cell is thin enough to carry sampling noise as though it were shape.
POOLED_YEARS_FROM: int = 2021

#: The band whose obligation is 1.0 by definition, matching AGE_GROUPS.
NUMERAIRE_BAND: str = "working_age"


def pooled_years() -> tuple[int, ...]:
    """Comparable survey years at or after :data:`POOLED_YEARS_FROM`."""
    return tuple(y for y in cd.survey_years() if y >= POOLED_YEARS_FROM)


def bands() -> dict[str, tuple[int, int]]:
    return {name: group["range"] for name, group in AGE_GROUPS.items()}


def implied_weights() -> dict:
    """Measured band weights against the shipped ones.

    Returns each band's self / care / total minutes per person-day, the implied
    weight relative to the numeraire band, the shipped `eoh_weight`, and whether
    the band's measurement is complete.
    """
    measured = cd.band_relative_demand(bands(), NUMERAIRE_BAND, pooled_years())
    rows = []
    for name, group in AGE_GROUPS.items():
        cell = measured[name]
        implied = cell["relative"]
        shipped = float(group["eoh_weight"])
        rows.append({
            "band": name,
            "range": group["range"],
            "self_minutes_per_day": cell["self"],
            "care_minutes_per_day": cell["care"],
            "total_minutes_per_day": cell["total"],
            "implied_weight": implied,
            "shipped_weight": shipped,
            "ratio": (implied / shipped) if implied and shipped else None,
            "complete": cell["complete"],
            "bound": "measured" if cell["complete"] else "lower",
        })
    return {
        "rows": rows,
        "years": pooled_years(),
        "numeraire": NUMERAIRE_BAND,
        "implied_w": implied_w(rows),
        "shipped_w": sum(
            g["fraction"] * g["eoh_weight"] for g in AGE_GROUPS.values()
        ),
    }


def implied_w(rows: list[dict]) -> float | None:
    """Σ(fraction × implied weight) — what `w` would become, at shipped fractions.

    Held at the SHIPPED population fractions on purpose. Changing the weights and
    the fractions together would make the movement in `w` impossible to attribute
    to either, and the fractions are an `instance` input a deploying institution
    supplies anyway.
    """
    total = 0.0
    for row in rows:
        implied = row["implied_weight"]
        if implied is None:
            return None
        total += float(AGE_GROUPS[row["band"]]["fraction"]) * float(implied)
    return total


def measured_population_shares() -> dict[str, float]:
    """The `fraction` half of AGE_GROUPS, from the census extract."""
    return cd.population_shares(bands())


def elderly_routes() -> dict:
    """The two elderly readings and their disagreement — reported, not reconciled."""
    out: dict[str, object] = dict(cd.elderly_route_disagreement(pooled_years()))
    out["note"] = (
        "the roster route is an ARTEFACT: 81.6% of eldercare recipients are not "
        "household members, so a household-roster join cannot see them. Do not "
        "average the two."
    )
    return out


def rivalry() -> dict:
    """The joint-production exponents and what they cost at scale."""
    return {
        kind: {
            "rho": cd.rivalry_exponent(kind),
            "table": cd.rivalry_table(kind),
            "cost_of_four": cd.joint_cost(4, kind),
        }
        for kind in ("active", "passive")
    }


def report() -> dict:
    """Everything the scenario reports, in one call."""
    weights = implied_weights()
    return {
        "weights": weights,
        "population_shares": measured_population_shares(),
        "elderly_routes": elderly_routes(),
        "rivalry": rivalry(),
        "coverage": cd.coverage(),
        "limits": {
            "self_maintenance_min_age": cd.SELF_MAINTENANCE_MIN_AGE,
            "passive_max_age": cd.PASSIVE_MAX_AGE,
            "top_coded_age": cd.ATUS_TOP_CODED_AGE,
            "one_diary_per_household": True,
        },
    }
