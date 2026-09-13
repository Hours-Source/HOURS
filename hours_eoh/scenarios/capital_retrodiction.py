"""
Reading ε off a real economy — and what that reading actually depends on.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. No constant moves and no shipped number changes;
`TestRetrodictionChangesNothing` fails the moment that stops being true.

WHAT THIS SETTLES. `docs/theory/anchor_comparison.md` ("What would change our
mind") carries a falsification
condition — *if a retrodiction produces an implausible ε, the endogenous-supply
property is not reading the world it says it reads* — and it HAD FIRED: the one
run against a real economy gave ε = 0.777–1.000, saturated, for a US where 158M
people work. `record/thermal.md` concluded the machine profiles were
"miscalibrated by ~3×".

**They are not.** The saturated reading is one corner of a grid spanned by three
judgements nobody had declared, and the BEA stock tables confirm the input the
estimate used was already right:

    doctrine     1.79x   current-cost vs historical-cost, ONE physical stock
    convention   1.45x   wages/compensation x 2,080/derived hours
    scope        ~2.5x   productive capital vs every fixed asset

Any two compound past 3×. Across the defensible interior the US reads ε ≈ 0.4–0.6.

**THE CONVERSION RATE IS AN INTAKE FIELD WITH NO DEFAULT, AND THAT IS THE
DESIGN.** `currency_per_teh` is required everywhere in this module. It is
specific to a currency, a year, a wage series and an hours convention, so a
shipped value would be a fifth undeclared judgement — and worse, it would bury
the one this framework most needs visible. Converting a currency-denominated
stock into TEH IS the valuation step: §2 argues a census needs no convention
while a valuation transmits doctrine undamped, and requiring the rate at the API
boundary is that argument enforced rather than restated. `conversion_band()`
gives a feasibility range for sanity-checking a supplied rate. It is not a
default and nothing here falls back to it.

Layer: scenarios/ — imports from core/, reference/ and research/, never the reverse.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from hours_eoh.reference.capital_inventory import (
    BEA_POPULATION, BEA_YEAR, DOCTRINE_RATIOS, MEASURED_AGES, SCOPES,
    UNALLOCATED, UNALLOCATED_USD_B,
    capital_by_profile, scope_total, what_this_cannot_settle,
)
from hours_eoh.research.thermal_capital import epsilon_current_from_inventory
from hours_eoh.scenarios.food_conservation import hours_per_worker_year

__all__ = [
    "conversion_band", "epsilon_from_inventory", "retrodiction_grid",
    "doctrine_spread", "unallocated_sensitivity", "retrodiction_report",
]

_REGISTRY = Path(__file__).resolve().parents[1] / "reference" / "data" / "multiplier_registry_v5.csv"

#: Age used when the inventory carries no measured age for a profile. The
#: measured class ages in `MEASURED_AGES` cover equipment, structures and IPP;
#: profiles mix classes, so a profile-level age is a weighted question the
#: inventory does not answer. Structures dominate every scope by value, so the
#: structures age is the honest fallback and is stated rather than assumed.
_FALLBACK_AGE_KEY: str = "private_structures"


def conversion_band() -> dict:
    """
    What a currency-per-TEH rate could defensibly be, derived from repo data.

    Governing equation, per convention:

        rate = mean_wage / (hours_per_year × mean_multiplier)

    units: units of the inventory's currency per TEH.

    **THIS IS A SANITY BAND, NOT A DEFAULT.** Nothing in this module falls back
    to it. The four rows are four CONVENTIONS, not an error bar: wages against
    total compensation, and the 2,080-hour convention against the derived
    work-year. A supplied rate outside the band implies something unusual about
    the collective's wage structure and is worth questioning; a rate inside it
    is not thereby correct.

    The compensation multiple is NOT in this repo — it is a published BLS ratio —
    and its absence is the argument: the rate cannot be derived here, only
    bounded.
    """
    with _REGISTRY.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r.get("ep_employment_k") and r.get("oews_median_wage")
                and r.get("reference_multiplier")]
    emp = [float(r["ep_employment_k"]) for r in rows]
    total = sum(emp)
    wage = sum(float(r["oews_median_wage"]) * e for r, e in zip(rows, emp)) / total
    mult = sum(float(r["reference_multiplier"]) * e for r, e in zip(rows, emp)) / total
    derived_h = hours_per_worker_year()

    conventions = {
        "wages_2080h":            wage / (2080.0 * mult),
        "wages_derived_hours":    wage / (derived_h * mult),
        "compensation_2080h":     wage * 1.31 / (2080.0 * mult),
        "compensation_derived_h": wage * 1.31 / (derived_h * mult),
    }
    lo, hi = min(conventions.values()), max(conventions.values())
    return {
        "occupations":        len(rows),
        "mean_wage":          wage,
        "mean_multiplier":    mult,
        "hours_convention":   2080.0,
        "hours_derived":      derived_h,
        "compensation_multiple": 1.31,
        "compensation_multiple_source": (
            "BLS total compensation to wages. NOT IN THIS REPO — which is why "
            "the rate is bounded here and never derived."
        ),
        "by_convention":      conventions,
        "low":                lo,
        "high":               hi,
        "spread":             hi / lo,
        "is_a_default":       False,
    }


def epsilon_from_inventory(
    currency_per_teh: float,
    scope: str = "government",
    doctrine: str = "current_cost",
    population: float = BEA_POPULATION,
) -> dict:
    """
    ε derived from the BEA inventory at a SUPPLIED conversion rate.

    Governing chain:

        BEA $B ──(÷ currency_per_teh)──► TEH ──► civilization_epsilon ──► ε

    units: dimensionless ε ∈ [0, 1].

    Args:
        currency_per_teh: REQUIRED. Units of the inventory's currency per TEH.
            There is no default and there will not be one: see the module
            docstring. `conversion_band()` says what is plausible.
        scope: one of `SCOPES` — the second judgement.
        doctrine: "current_cost" or "historical_cost" — the third.
        population: the frame the inventory is counted over.

    Raises:
        ValueError: on a non-positive rate, an unknown scope or doctrine.
    """
    if currency_per_teh <= 0.0:
        raise ValueError(
            f"currency_per_teh must be positive, got {currency_per_teh}. There is "
            "no default: the rate is specific to a currency, a year and an hours "
            "convention, and supplying it is the institution's declaration of "
            "which valuation doctrine it is using."
        )
    by_profile = capital_by_profile(scope, doctrine)   # validates scope/doctrine
    age = MEASURED_AGES[_FALLBACK_AGE_KEY]
    desc = {
        name: {"teh_value": usd_b * 1e9 / currency_per_teh, "age": age, "condition": 0.85}
        for name, usd_b in by_profile.items() if usd_b > 0.0
    }
    total_teh = sum(d["teh_value"] for d in desc.values())
    return {
        "year":             BEA_YEAR,
        "scope":            scope,
        "doctrine":         doctrine,
        "currency_per_teh": currency_per_teh,
        "population":       population,
        "capital_usd_b":    sum(by_profile.values()),
        "capital_teh":      total_teh,
        "teh_per_capita":   total_teh / population,
        "age_years":        age,
        "epsilon":          epsilon_current_from_inventory(desc, population),
    }


def retrodiction_grid(
    rates: tuple[float, ...] | None = None,
    population: float = BEA_POPULATION,
) -> list[dict]:
    """
    ε across every combination of the three judgements. units: dimensionless.

    A single ε for a real economy would be a number with three undeclared
    choices inside it. This returns the grid instead, which is the honest object.
    """
    if rates is None:
        band = conversion_band()
        rates = (band["low"], (band["low"] + band["high"]) / 2.0, band["high"])
    return [
        epsilon_from_inventory(r, scope=s, doctrine=d, population=population)
        for s in SCOPES for d in ("current_cost", "historical_cost") for r in rates
    ]


def doctrine_spread() -> dict:
    """
    The framework's own thesis, measured on BEA's two valuations of one stock.

    §2 argues that a census needs no convention while a valuation transmits
    doctrine undamped. BEA publishes current-cost and historical-cost net stock
    for the identical physical inventory. units: dimensionless ratio.

    This is EVIDENCE FOR §2 rather than a limitation of the retrodiction: the
    spread is the prediction, observed.
    """
    return {
        "ratios":         dict(DOCTRINE_RATIOS),
        "aggregate":      DOCTRINE_RATIOS["private_fixed_assets"],
        "widest_class":   max(DOCTRINE_RATIOS.items(), key=lambda kv: kv[1]),
        "narrowest_class": min(DOCTRINE_RATIOS.items(), key=lambda kv: kv[1]),
        "reading": (
            "Two published valuations of one unchanging physical stock differ by "
            f"{DOCTRINE_RATIOS['private_fixed_assets']:.2f}x in aggregate. The "
            "census route cannot move at all, because it never receives the "
            "valuation. That is the §2 claim, measured."
        ),
    }


def unallocated_sensitivity(currency_per_teh: float, scope: str = "government") -> dict:
    """
    What the one placed-not-measured line is worth. units: dimensionless ε.

    Government equipment carries no by-type breakdown outside defence in any BEA
    Fixed Assets table, so it is assigned to a single profile. This moves the
    whole amount to each profile in turn and reports the span — bounding the gap
    rather than closing it, because the bound is the result.
    """
    base = capital_by_profile(scope)
    amount = UNALLOCATED_USD_B
    placed = "computing_ai"
    age = MEASURED_AGES[_FALLBACK_AGE_KEY]
    out: dict[str, float] = {}
    for target in base:
        moved = dict(base)
        moved[placed] = moved.get(placed, 0.0) - amount
        moved[target] = moved.get(target, 0.0) + amount
        desc = {n: {"teh_value": v * 1e9 / currency_per_teh, "age": age, "condition": 0.85}
                for n, v in moved.items() if v > 0.0}
        out[target] = epsilon_current_from_inventory(desc, BEA_POPULATION)
    lo, hi = min(out.values()), max(out.values())
    return {
        "usd_b":           amount,
        "share_of_scope":  amount / sum(base.values()),
        "epsilon_by_target": out,
        "span":            hi - lo,
        "verdict": (
            f"reassigning the whole ${amount:,.1f}B moves ε by {hi - lo:.4f} — "
            "bounded far below the doctrine and conversion spreads, so the "
            "missing breakdown does not change a conclusion"
        ),
    }


def retrodiction_report(currency_per_teh: float | None = None) -> dict:
    """
    The whole grid with its caveats attached, and a verdict computed from it.

    `currency_per_teh` is optional HERE and only here: passing None reports
    across the band rather than at a point, which is the honest default for a
    report. It is still never defaulted to a value.
    """
    band = conversion_band()
    grid = retrodiction_grid()
    eps = [row["epsilon"] for row in grid]
    interior = [row for row in grid
                if row["scope"] == "government" and row["doctrine"] == "current_cost"]
    saturated = [row for row in grid if row["epsilon"] >= 0.99]

    verdict = (
        f"across the declared grid the US reads ε = {min(eps):.3f}–{max(eps):.3f}; "
        f"{len(saturated)} of {len(grid)} cells saturate"
    )
    return {
        "year":              BEA_YEAR,
        "conversion_band":   band,
        "doctrine":          doctrine_spread(),
        "scopes":            {k: v["reading"] for k, v in SCOPES.items()},
        "grid":              grid,
        "epsilon_min":       min(eps),
        "epsilon_max":       max(eps),
        "saturated_cells":   len(saturated),
        "interior_epsilon":  [row["epsilon"] for row in interior],
        "unallocated":       unallocated_sensitivity(band["low"]),
        "cannot_settle":     what_this_cannot_settle(),
        "point_estimate":    None,
        "verdict":           verdict,
        "adopted":           False,
    }
