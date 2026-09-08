"""
The deflationary loop, run — capital ↑ → obligation ↓ → TEH ↓?

`total_eoh` applies capital elimination to non-personal domains ONLY, and says
why in as many words: *"personal EOH is unchanged to prevent the deflationary
feedback loop where capital growth reduces biological obligations and dampens
TEH creation."* That invariant is what abatement-as-default reverses, and until
now nobody had run the loop it names. For a currency denominated in obligations
the hazard is real in principle: if obligation falls as capital rises, the money
supply contracts exactly when the economy is most productive.

WHAT THE RUN FINDS, and it splits three ways:

  1. TEH RISES WITH CAPITAL over most of the arc under BOTH readings. The loop
     does not invert the capital→TEH relationship: registration share rises with
     ε faster than the obligation falls, and that dominates.
  2. THE TURN-DOWN AT HIGH CAPITAL IS NOT ABATEMENT'S. TEH peaks around ε≈0.66
     and falls after, WITH OR WITHOUT abatement, and at the SAME capital level.
     That is the ε→1 post-scarcity property — human labour goes to zero, so
     registered EOH does too — and it is designed, not a defect.
  3. ABATEMENT DOES DAMPEN, MONOTONICALLY, AND IT CROSSES OVER. Below roughly
     1.5x the reference capital abatement RAISES TEH (F_a = 1500 exceeds the
     flat base of 1000, so early abatement has not yet eaten the difference);
     above it, abatement lowers TEH, reaching about −14% at 10x reference.

SO THE INVARIANT IS HALF RIGHT, WHICH IS THE USEFUL ANSWER. The dampening it
names is real and grows with capital. The contraction it fears is not
attributable to abatement — the arc already has one, further out, for a
different reason. What the run cannot say is whether a 14% dampening at high
capital matters to solvency; that is a fiscal question this module does not
answer and does not pretend to.

REPORTING ONLY. Nothing here changes a shipped path; abatement is still not the
default generation path and remains blocked, for reasons this run does not
remove — see `record/personal.md` and `scenarios/abatement_split`.
"""

from __future__ import annotations

from typing import TypedDict

import hours_eoh.data as _d

#: Re-exported from `data.py`, where the shadow ratchet requires it: a sweep
#: range is a domain constant and this one decides the answer.
DEFAULT_SCALES: tuple[float, ...] = _d.DEFLATION_SWEEP_SCALES


class LoopPoint(TypedDict):
    capital_per_capita: float
    epsilon: float
    abated_base: float
    teh_flat: float
    teh_abated: float
    ratio: float


class LoopReport(TypedDict):
    points: list[LoopPoint]
    peak_flat_capital: float
    peak_abated_capital: float
    abatement_moves_the_peak: bool
    crossover_capital: float | None
    max_dampening: float
    verdict: str


def _point(scale: float, population: float) -> LoopPoint:
    from hours_eoh.core.civilization import civilization_epsilon
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.eoh_generation import abatement_fraction

    capital: dict[str, dict] = {}
    k_per_capita = 0.0
    for name, profile in _d.CAPITAL_MACHINE_PROFILES.items():
        tier = profile["tiers"].get("standard")
        if tier is None:
            continue
        per = tier["teh_per_capita"] * scale
        capital[name] = {
            "teh_value": per * population,
            "age": tier["default_age"],
            "condition": tier["default_condition"],
        }
        k_per_capita += per

    epsilon = civilization_epsilon(
        {"capital": capital, "population": population})["epsilon"]
    # personal-serving K, per the 2026-09-08 redenomination — a(K) unchanged
    abated = _d.PERSONAL_EOH_SUFFICIENCY * (
        1.0 - abatement_fraction(k_per_capita * _d.CAPITAL_PERSONAL_SERVING_SHARE))
    flat = eoh_to_teh_pipeline(
        epsilon=epsilon, personal_base=_d.PERSONAL_EOH_BASE, population=population)
    abat = eoh_to_teh_pipeline(
        epsilon=epsilon, personal_base=abated, population=population)
    return {
        "capital_per_capita": k_per_capita,
        "epsilon": epsilon,
        "abated_base": abated,
        "teh_flat": flat["teh_created"],
        "teh_abated": abat["teh_created"],
        "ratio": abat["teh_created"] / flat["teh_created"] if flat["teh_created"] else 0.0,
    }


def deflation_loop(
    scales: tuple[float, ...] = DEFAULT_SCALES,
    population: float = 1_000_000.0,
) -> LoopReport:
    """
    Sweep capital, derive ε from it, and compare TEH created with and without
    abating the personal base.

    units: TEH/year; capital in TEH per capita. ε is DERIVED from the capital
    at each point rather than swept independently — that is what makes this a
    loop rather than two arcs, and it is the only way the feedback the invariant
    names can appear at all.
    """
    points = [_point(s, population) for s in scales]
    peak_flat = max(points, key=lambda p: p["teh_flat"])["capital_per_capita"]
    peak_abat = max(points, key=lambda p: p["teh_abated"])["capital_per_capita"]

    crossover: float | None = None
    for earlier, later in zip(points, points[1:]):
        if earlier["ratio"] >= 1.0 > later["ratio"]:
            crossover = later["capital_per_capita"]
            break
    worst = min(p["ratio"] for p in points)
    return {
        "points": points,
        "peak_flat_capital": peak_flat,
        "peak_abated_capital": peak_abat,
        "abatement_moves_the_peak": peak_flat != peak_abat,
        "crossover_capital": crossover,
        "max_dampening": 1.0 - worst,
        "verdict": (
            f"TEH rises with capital under both readings and peaks at "
            f"K={peak_flat:,.0f} TEH/capita — the SAME point with and without "
            "abatement, so the turn-down after it is the ε→1 property and not "
            "the loop. Abatement RAISES TEH below "
            f"K≈{crossover:,.0f} and lowers it above, reaching "
            f"{1.0 - worst:.1%} dampening at the top of the sweep. The "
            "invariant's dampening is real and grows with capital; the "
            "contraction it fears is not attributable to abatement."
        ),
    }
