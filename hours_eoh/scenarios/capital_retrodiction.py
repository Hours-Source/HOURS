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
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from hours_eoh.reference.capital_inventory import (
    AGE_ROWS, BEA_POPULATION, BEA_YEAR, DOCTRINE_RATIOS, SCOPES,
    PROFILE_MAP, UNALLOCATED, UNALLOCATED_USD_B,
    capital_by_profile, scope_total, what_this_cannot_settle,
)
from hours_eoh.data import (
    AGE_EFFICIENCY_BETA_EQUIPMENT, AGE_EFFICIENCY_BETA_STRUCTURES,
    CAPITAL_AGE_RATIO_DEFAULT, CAPITAL_MACHINE_PROFILES, EPSILON_ARC_MAX,
)
from hours_eoh.core.civilization import age_efficiency, condition_from_age_ratio
from hours_eoh.research.thermal_capital import epsilon_current_from_inventory
from hours_eoh.scenarios.food_conservation import hours_per_worker_year

__all__ = [
    "conversion_band", "epsilon_from_inventory", "retrodiction_grid",
    "doctrine_spread", "unallocated_sensitivity", "retrodiction_report",
    "stock_age_ratio",
]

_REGISTRY = Path(__file__).resolve().parents[1] / "reference" / "data" / "multiplier_registry_v5.csv"

#: THE AGES THE INVENTORY IS READ AT (2026-10-04). Each profile's age over its
#: life comes from its own BEA rows (`AGE_ROWS`: average age over BEA service
#: life, current cost — the physical reading whatever doctrine values the
#: stock), replacing one class age (private structures, 28.6 yr) applied to
#: every profile. `civilization` divides age by the PROFILE's design life, so
#: the age passed is ratio × that life: the ratio arrives intact and the
#: placeholder lives cancel. A supplied inventory is someone else's stock, so
#: it is read at `CAPITAL_AGE_RATIO_DEFAULT` and says so.

#: ε at or above which a reading counts as SATURATED — the §7 retrodiction
#: falsifier's own threshold. 0.99 and not 1.0 because the arc's declared
#: endpoint is 0.99: a reading that reaches it has run out of room, and whether
#: it lands on 0.995 or exactly 1.0 is a detail of the capital curve rather than
#: a difference in what it tells you. Defined once and read by BOTH
#: `epsilon_from_inventory` (per call) and `retrodiction_report` (per grid), so
#: the two accounts of "saturated" cannot drift apart.
_SATURATION_EPSILON: float = EPSILON_ARC_MAX


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
    *,
    inventory: Mapping[str, float] | None = None,
    age_ratios: Mapping[str, float] | None = None,
    conditions: Mapping[str, float] | None = None,
) -> dict:
    """
    ε derived from a capital inventory at a SUPPLIED conversion rate.

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
        inventory: YOUR OWN inventory, keyed by machine profile, in the same
            currency the rate converts from. `None` (default) reads the shipped
            BEA table, so the US path is unchanged. Supplying one is what lets a
            non-US institution run this instrument.

            IT ARRIVES UNDECLARED, AND THE RESULT SAYS SO. The shipped table is
            37 rows each carrying a `basis`, plus 3 exclusions each carrying a
            `reason`, and `TestTheJudgementsStayDeclared` checks them. A supplied
            mapping has none of that — the mapping from your national accounts
            onto the machine profiles is YOUR judgement, and the framework cannot
            see it. `inventory_source` in the returned dict reports which table
            produced the figure so the two can never be confused.
        age_ratios: YOUR stock's age over its life, by machine profile
            (2026-10-04). Unstated, the shipped table reads its BEA ages and a
            supplied inventory `CAPITAL_AGE_RATIO_DEFAULT`; `age_source` says
            which.
        conditions: YOUR stock's productive condition, by profile, in [0, 1].
            Unstated, the shipped table reads BLS age-efficiency on its BEA
            rows, and a supplied inventory derives it from its age on the same
            curve (`civilization.condition_from_age_ratio`).

    Raises:
        ValueError: on a non-positive rate, an unknown scope or doctrine, an
            inventory key that is not a machine profile, or a negative value.
    """
    if currency_per_teh <= 0.0:
        raise ValueError(
            f"currency_per_teh must be positive, got {currency_per_teh}. There is "
            "no default: the rate is specific to a currency, a year and an hours "
            "convention, and supplying it is the institution's declaration of "
            "which valuation doctrine it is using."
        )
    # CALLED UNCONDITIONALLY: this is where scope and doctrine are validated, so
    # skipping it when an inventory is supplied would drop the check for exactly
    # the caller most likely to get them wrong — someone porting this instrument
    # to another jurisdiction.
    shipped = capital_by_profile(scope, doctrine)
    if inventory is None:
        by_profile, source = shipped, "shipped_bea"
    else:
        unknown = sorted(set(inventory) - set(CAPITAL_MACHINE_PROFILES))
        if unknown:
            raise ValueError(
                f"inventory keys must be machine profiles, got {unknown}. "
                f"Known profiles: {sorted(CAPITAL_MACHINE_PROFILES)}. Mapping your "
                "national accounts onto these is the judgement this instrument "
                "cannot make for you."
            )
        negative = sorted(k for k, v in inventory.items() if float(v) < 0.0)
        if negative:
            raise ValueError(f"inventory values must be >= 0, negative at {negative}")
        by_profile, source = {k: float(v) for k, v in inventory.items()}, "supplied"
    ratios, derived, age_source = _ages(scope, inventory is not None, age_ratios)
    if conditions is not None:
        unknown = sorted(set(conditions) - set(CAPITAL_MACHINE_PROFILES))
        bad = sorted(k for k, v in conditions.items() if not 0.0 <= float(v) <= 1.0)
        if unknown or bad:
            raise ValueError(f"conditions: unknown profiles {unknown}, outside [0, 1] at {bad}")
        derived = {**(derived or {}), **{k: float(v) for k, v in conditions.items()}}
    desc = _describe(by_profile, currency_per_teh, ratios, derived)
    total_teh = sum(d["teh_value"] for d in desc.values())
    eps = epsilon_current_from_inventory(desc, population)
    return {
        # BEA_YEAR belongs to the SHIPPED table. A supplied inventory has its own
        # vintage that this module does not know, and reporting BEA's would date
        # someone else's data with someone else's year.
        "year":             BEA_YEAR if inventory is None else None,
        "inventory_source": source,
        "scope":            scope,
        "doctrine":         doctrine,
        "currency_per_teh": currency_per_teh,
        "population":       population,
        "capital_usd_b":    sum(by_profile.values()),
        "capital_teh":      total_teh,
        "teh_per_capita":   total_teh / population,
        "age_ratio":        sum(d["teh_value"] * ratios[n] for n, d in desc.items()) / total_teh,
        "age_ratio_by_profile": {n: ratios[n] for n in desc},
        "condition_by_profile": {n: _condition_of(d, n) for n, d in desc.items()},
        "age_source":       age_source,
        "epsilon":          eps,
        # REPORTED PER CALL, not only per grid. The shipped grid is guarded by
        # `test_no_cell_of_the_declared_grid_saturates` AND by a can-fire test; a
        # SUPPLIED inventory had neither, so a foreign caller could read a
        # boundary artefact (ε pinned at the arc's endpoint because the rate is
        # too low for their inventory) as a finding about their economy.
        "saturated":        eps >= _SATURATION_EPSILON,
    }


def _row_efficiency(row: Mapping[str, Any]) -> float:
    """One BEA row's productive condition: BLS age-efficiency at its mean age
    over its mid service life, β by BEA class (IPP takes equipment's)."""
    beta = (AGE_EFFICIENCY_BETA_STRUCTURES if row["class"] == "structures"
            else AGE_EFFICIENCY_BETA_EQUIPMENT)
    return age_efficiency(row["age"] / (0.5 * sum(row["life"])), beta)


def _ages(scope: str, supplied: bool,
          stated: Mapping[str, float] | None = None
          ) -> tuple[dict[str, float], dict[str, float] | None, str]:
    """Each machine profile's age over its life, and its condition: as stated
    (a profile left out takes `CAPITAL_AGE_RATIO_DEFAULT`); else from its BEA
    rows on the shipped inventory (a profile with no row carrying a life takes
    the scope's), `CAPITAL_AGE_RATIO_DEFAULT` for a supplied one. Conditions
    are None where only a ratio is known: `civilization` then derives them
    from the age it is passed, on the same curve."""
    if stated is not None:
        unknown = sorted(set(stated) - set(CAPITAL_MACHINE_PROFILES))
        bad = sorted(k for k, v in stated.items() if not 0.0 <= float(v))
        if unknown or bad:
            raise ValueError(f"age_ratios: unknown profiles {unknown}, negative at {bad}")
        return ({n: float(stated.get(n, CAPITAL_AGE_RATIO_DEFAULT)) for n in CAPITAL_MACHINE_PROFILES},
                None, "supplied: age_ratios")
    if supplied:
        return ({n: CAPITAL_AGE_RATIO_DEFAULT for n in CAPITAL_MACHINE_PROFILES}, None,
                "default: CAPITAL_AGE_RATIO_DEFAULT — a supplied inventory's ages are not known")
    whole = stock_age_ratio(scope)
    profile_of = {r["line"]: r["profile"] for r in PROFILE_MAP
                  if r["scope"] in SCOPES[scope]["includes"]}
    age_sum: dict[str, float] = {}
    cond_sum: dict[str, float] = {}
    weight: dict[str, float] = {}
    for row in AGE_ROWS:
        name = profile_of.get(row["line"])
        if name is None or row["life"] is None or row["age"] is None:
            continue
        w = row["usd_b"]
        age_sum[name] = age_sum.get(name, 0.0) + w * row["age"] / (0.5 * sum(row["life"]))
        cond_sum[name] = cond_sum.get(name, 0.0) + w * _row_efficiency(row)
        weight[name] = weight.get(name, 0.0) + w
    return ({n: age_sum[n] / weight[n] if weight.get(n) else whole["ratio"]
             for n in CAPITAL_MACHINE_PROFILES},
            {n: cond_sum[n] / weight[n] if weight.get(n) else whole["condition"]
             for n in CAPITAL_MACHINE_PROFILES},
            f"measured: BEA {BEA_YEAR} average age over BEA service life, by profile; "
            "condition on BLS's age-efficiency curve")


def _describe(by_profile: Mapping[str, float], currency_per_teh: float,
              ratios: Mapping[str, float], conditions: Mapping[str, float] | None) -> dict:
    """The inventory as `civilization` reads it — each profile at its age
    (ratio × the profile's design life, so the placeholder lives cancel) and,
    where measured, its condition."""
    out = {}
    for n, usd_b in by_profile.items():
        if usd_b <= 0.0:
            continue
        d: dict[str, float] = {"teh_value": usd_b * 1e9 / currency_per_teh,
                               "age": ratios[n] * CAPITAL_MACHINE_PROFILES[n]["design_life"]}
        if conditions is not None and n in conditions:
            d["condition"] = conditions[n]
        out[n] = d
    return out

def _condition_of(d: Mapping[str, float], name: str) -> float:
    """The condition `civilization` reads for one entry: stated, or derived
    from its age on the same curve."""
    if "condition" in d:
        return float(d["condition"])
    return condition_from_age_ratio(d["age"] / max(CAPITAL_MACHINE_PROFILES[name]["design_life"], 1.0))


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
    ratios, conditions, _ = _ages(scope, False)
    out: dict[str, float] = {}
    for target in base:
        moved = dict(base)
        moved[placed] = moved.get(placed, 0.0) - amount
        moved[target] = moved.get(target, 0.0) + amount
        desc = _describe(moved, currency_per_teh, ratios, conditions)
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
    saturated = [row for row in grid if row["epsilon"] >= _SATURATION_EPSILON]

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


def stock_age_ratio(scope: str = "government", doctrine: str = "current_cost") -> dict:
    """
    THE STOCK'S AGE AS A FRACTION OF ITS LIFE — `capital_age_ratio`, measured
    (2026-10-04). Until now every reading of it was a default: a bare 0.50 in
    core, frozen from the first commit, or the canonical arc's 0.30.

    Value-weighted mean of BEA average age over BEA service life, row by row
    (`AGE_ROWS`) — the same weighting `civilization.machine_eoh_from_capital`
    uses (TEH-weighted age / design life). A RATIO, so no currency enters: the
    rate that would turn dollars into TEH cancels.

    THE DIRECTION OF ITS ERROR: BEA's ages are weighted by NET (depreciated)
    stock, so an old asset counts for less than in a physical count — the
    ratio errs LOW. Current cost is the doctrine that matches a physical age
    (each vintage at its real quantity, today's prices); historical cost weights
    by nominal outlay, which inflation tilts younger. Both are returned.

    Args:
        scope: one of `SCOPES` — what counts as capital.
        doctrine: "current_cost" (Tables 2.9 / 7.7) or "historical_cost"
            (2.10; PRIVATE ONLY — BEA publishes no historical-cost government
            age, so the government lines are reported as not covered).

    Returns: ratio (at each row's mid life), low / high (each row at its
        longest / shortest BEA life), mean_age_years, share_past_life (stock
        older than its mid life), coverage (share of the scope's stock with both
        an age and a life — WITHIN PRIVATE assets when `private_only`, the
        government rows then listed in `excluded` at their current-cost size),
        and the excluded rows with BEA's reason.
    """
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {sorted(SCOPES)}, got {scope!r}")
    if doctrine not in ("current_cost", "historical_cost"):
        raise ValueError(
            f"doctrine must be 'current_cost' or 'historical_cost', got {doctrine!r}")
    admitted = {r["line"] for r in PROFILE_MAP if r["scope"] in SCOPES[scope]["includes"]}
    hist = doctrine == "historical_cost"
    used, excluded, total = [], [], 0.0
    classes: list[str] = []
    conds: list[float] = []
    for row in AGE_ROWS:
        if row["line"] not in admitted:
            continue
        weight = row.get("usd_b_hist") if hist else row["usd_b"]
        age = row.get("age_hist") if hist else row["age"]
        if weight is None:
            excluded.append({"bea": row["bea"], "type": row["type"],
                             "usd_b_current_cost": row["usd_b"],
                             "reason": "no historical-cost table for government assets"})
            continue
        total += weight
        if age is None or row["life"] is None:
            excluded.append({"bea": row["bea"], "type": row["type"], "usd_b": weight,
                             "reason": row["life_basis"]})
            continue
        used.append((weight, age, row["life"]))
        classes.append(row["class"])
        conds.append(_row_efficiency({**row, "age": age}))
    covered = sum(w for w, _, _ in used)
    if covered <= 0.0:
        raise ValueError(f"no row in scope {scope!r} carries both an age and a life")

    def mean(f: Callable[[float, tuple[int, int]], float]) -> float:
        return sum(w * f(a, life) for w, a, life in used) / covered

    mid = lambda life: 0.5 * (life[0] + life[1])  # noqa: E731
    return {
        "scope": scope, "doctrine": doctrine, "year": BEA_YEAR,
        "private_only": hist,
        "ratio": mean(lambda a, life: a / mid(life)),
        "low": mean(lambda a, life: a / life[1]),
        "high": mean(lambda a, life: a / life[0]),
        "mean_age_years": mean(lambda a, life: a),
        # Productive condition on BLS's age-efficiency curve, and the
        # structures share that blends the two curves (2026-10-04).
        "condition": sum(w * c for (w, _, _), c in zip(used, conds)) / covered,
        "structures_share": sum(w for (w, _, _), k in zip(used, classes)
                                if k == "structures") / covered,
        "share_past_life": sum(w for w, a, life in used if a > mid(life)) / covered,
        "coverage": covered / total,
        "excluded": excluded,
    }
