"""
The frailty care socket — an intake contract, not a model.

WHY A SOCKET AND NOT A CONSTANT. Care load tracks FRAILTY-YEARS, not
elder-years: most years after 65 are cheap and the cost concentrates in a short
terminal window. Counting people over 65 therefore says almost nothing about
staffing, and whether that window stretches (morbidity expansion) or arrives
later at the same length (compression) is unresolved, differs by country and by
condition, and is the pivotal variable. The retired elderly ε-drift asserted an
answer to it as a placeholder scalar and went on 2026-09-04 (its own tag block
in `data.py` carries the reason; it is not named here, because a retired
constant named under `scenarios/` reads as a live consumer to the provenance
gate). This is the shape that replaces it — somewhere for a measurement to arrive, not a better
guess.

THE TWO FIELDS, and their product is the only thing the model consumes:

    frailty_years_per_capita        Σ_x prevalence(x)·pop(x) / pop
    care_hours_per_frailty_year     intensity while in the state
                            product = frailty care hours per capita

That decomposition is chosen so compression and expansion are EXPRESSIBLE:
compression holds frailty-years flat or falling as longevity rises, expansion
raises them, and a single "care hours per elderly person" states neither. Both
fields are what actuarial sources carry — disability/ADL prevalence by age
(Sullivan-method HLE tables) and continuance plus staffing intensity from
long-term-care pricing. Those sources also cover the INSTITUTIONAL population,
which ATUS excludes by construction and which is exactly where the terminal
window sits.

NO DEFAULT, DELIBERATELY. Every entry point here requires the intake. The repo
has been bitten by a default that became load-bearing (`GUF_USE_SCALE_FACTOR`
was a fitted scalar that ended up quoted), and a care number is worse: shipping
one is writing a rationing rule that the framework has no standing to write and
no accountability for. `pristine_gap_obligation` set the precedent — no default
inventory, and a test pins that.

WHAT THIS DOES NOT DO, and the scope is measured rather than assumed:

  * IT SETTLES ABOUT AN EIGHTH OF CARE. Weighted by population share, frailty
    care is 7.5-11.6% of measured care and dependant care is 83-86%. Childcare
    tracks fertility and household composition; no actuarial table speaks to it.
  * IT DOES NOT DECIDE HOW TO RATION. Explicit rationing is a rule that can be
    argued with; implicit rationing stops tracking need and starts tracking
    advocacy. This computes whether a shortfall EXISTS — the prior question —
    and reports the reserve against it. A reserve is not an answer to who pays.
  * THE RESERVE IS REPORTED PER CAPITA AND THAT IS ITS WEAKNESS. Unpaid care is
    concentrated; a per-capita mean says nothing about whether the spare hours
    sit with the people doing the caring. `concentration` is required for that
    reason and the report refuses to omit it.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.data import AGE_GROUPS


class FrailtyIntake(TypedDict):
    """What a collective must supply. No field has a default."""

    frailty_years_per_capita: float      #: Σ prevalence(x)·pop(x) / pop
    care_hours_per_frailty_year: float   #: intensity while in the state
    source: str                          #: the table, its vintage and its population
    covers_institutional: bool           #: ATUS-style household frames do not


class FrailtyLoad(TypedDict):
    hours_per_capita: float
    frailty_years_per_capita: float
    care_hours_per_frailty_year: float
    share_of_care: float
    source: str
    covers_institutional: bool


def frailty_care_load(intake: FrailtyIntake) -> FrailtyLoad:
    """
    Frailty care hours per capita from a supplied intake.

    units: hours per head of population per year. ε-behaviour: none — frailty
    is a property of the population, not of the automation level. That is the
    substantive difference from what it replaces, which drifted with ε.

    Raises:
        ValueError: on a missing field, a non-positive quantity, or a `source`
            that does not name something. The last is not decoration: an intake
            whose provenance is unstated is a guess wearing a measurement's
            clothes, and this is the field that stops it.
    """
    required = ("frailty_years_per_capita", "care_hours_per_frailty_year",
                "source", "covers_institutional")
    missing = [k for k in required if k not in intake]
    if missing:
        raise ValueError(
            f"frailty intake is missing {missing}. There is no default: a "
            "shipped care number is a rationing rule this framework has no "
            "standing to write. Supply disability/ADL prevalence by age and a "
            "continuance-based intensity, and say where they came from."
        )
    fy = float(intake["frailty_years_per_capita"])
    hr = float(intake["care_hours_per_frailty_year"])
    if fy <= 0.0 or hr <= 0.0:
        raise ValueError(
            f"frailty_years_per_capita={fy} and care_hours_per_frailty_year={hr} "
            "must both be positive. Zero frailty-years is not a low-care "
            "population, it is an unmeasured one — excluded is not zero."
        )
    if not str(intake["source"]).strip():
        raise ValueError("`source` must name the table, its vintage and its population")

    care_weight = sum(g["fraction"] * g["care_weight"] for g in AGE_GROUPS.values())
    frailty_weight = sum(
        g["fraction"] * g["care_weight"]
        for g in AGE_GROUPS.values() if g["care_key"] == "frailty"
    )
    return {
        "hours_per_capita": fy * hr,
        "frailty_years_per_capita": fy,
        "care_hours_per_frailty_year": hr,
        # what fraction of the model's own care obligation this intake speaks to
        "share_of_care": frailty_weight / care_weight if care_weight else 0.0,
        "source": str(intake["source"]),
        "covers_institutional": bool(intake["covers_institutional"]),
    }


def morbidity_direction(early: FrailtyIntake, later: FrailtyIntake) -> dict:
    """
    COMPRESSION or EXPANSION, from two intakes at different dates.

    The question the retired elderly ε-drift asserted an answer to, made
    answerable instead. Compression: frailty-years per capita flat or falling
    while the population ages. Expansion: rising. The verdict is the SIGN of the
    change, never a rate — two points do not give a rate, and the repo's own
    history is full of figures that became rates by restatement.

    units: dimensionless ratio plus a label.
    """
    a = frailty_care_load(early)
    b = frailty_care_load(later)
    ratio = b["frailty_years_per_capita"] / a["frailty_years_per_capita"]
    if ratio > 1.0:
        label = "expansion"
    elif ratio < 1.0:
        label = "compression"
    else:
        label = "stationary"
    return {
        "ratio": ratio,
        "direction": label,
        "hours_ratio": b["hours_per_capita"] / a["hours_per_capita"],
        "both_cover_institutional": a["covers_institutional"] and b["covers_institutional"],
        "note": (
            "SIGN ONLY. Two points give a direction, not a rate, and an "
            "intensity change can move the hours ratio in the opposite "
            "direction to the frailty-years ratio — read both."
        ),
    }
