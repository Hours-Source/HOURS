"""
The compass: can the system STOP here? Stability at a point on the arc, rather
than arrival at its end.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. Composes checks that already exist and adds no mechanism;
`TestStabilityChangesNothing` fails the moment that stops being true.

WHAT THIS ASKS THAT NOTHING ELSE DID
-------------------------------------
The repo has three neighbouring questions and none of them is this one.
`scenarios/long_run.canonical_arc_trajectory` asks how long the JOURNEY takes.
`research/corridor.corridor` asks which band of ε is survivable, binding floors
against ceilings. `core/autarky.overbuild_check` asks whether one collective at
one capital stock is worth being in.

The compass is different and simpler: **at this ε, with no further automation
ever arriving, can the system stay here indefinitely?** A currency that must
keep growing to avoid collapse has a ceiling that eventually fails it. One that
is stationary at every point on its arc does not — and whether post-scarcity is
reachable becomes a question about ambition rather than about survival.

THE THREE CONDITIONS, and they are not the same question asked three ways:

    1. OBLIGATION MET     human labour supply >= the human share of what is
                          OWED. Can the agents here survive?

    2. DELIVERY PAYS      the apparatus abates more obligation than it costs.
                          Is the machinery earning its keep, or is it overhead
                          that the automation is merely masking?

    3. STOCK STATIONARY   surplus labour, after the obligation AND the delivery
                          cost, is non-negative — so a carried stock can be
                          serviced rather than compounding. **You can meet your
                          obligation while your bridges rot**, which is why this
                          is separate from (1).

Conditions 1 and 3 are ordered by construction: 3 implies 1. They are reported
separately anyway, because WHICH one fails says what to do about it.

EVERY VERDICT STATES ITS STANDARD, and that is not decoration. This module
shipped for one commit evaluating conditions 1 and 3 at `collapsed` and
condition 2 at `sufficiency` — one verdict, two standards, undeclared — and
every test in its own file passed. It was caught by checking whether the
neighbouring `corridor` entry point was reachable. `collapsed` is now refused
outright: it is F_a·(1 − a), already abated, and `core/autarky` will not accept
an abated value as the autarky reference because a standard with the apparatus
baked into it cannot be the counterfactual FOR the apparatus.

HOW THIS RELATES TO `corridor`, stated so the two do not read as contradicting.
Corridor asks which ε are SURVIVABLE; this asks where the system could STAND
STILL, which additionally requires the delivery cost to be covered. Stability is
therefore strictly stronger, and the bands show it at the same standard:

    standard      corridor floor    stationary band
    survival           0.000        [0.000, 0.990]
    sufficiency        0.424        [0.487, 0.990]

WHAT THIS DOES NOT DO. It takes no charter decision and moves no number. It does
not assert that the stationary band is where the system SHOULD sit — a society
may rationally accept a non-stationary point while it builds through one. It
reports where standing still is possible.

Layer: scenarios/ — imports core/ and scenarios/; imported by neither.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from hours_eoh.core.autarky import overbuild_check
from hours_eoh.core.eoh_generation import personal_base_for
from hours_eoh.data import MEASURED_CAPACITY_H_YR, ARC_REPORTING_POINTS, CAPITAL_STOCK_DEFAULT
from hours_eoh.scenarios.feasibility import labor_supply_per_capita
from hours_eoh.scenarios.obligation_accounts import obligation_accounts

__all__ = [
    "CONDITIONS",
    "STANDARDS",
    "band_by_standard",
    "stability_at",
    "stability_arc",
    "stationary_band",
    "band_from_flags",
    "stability_report",
]

#: The three conditions, declared rather than inferred — the `TERM_BASIS` and
#: `ACCOUNTS` precedent.
#: The standards a stability verdict may be evaluated at, and the vocabulary is
#: Block I's own. A verdict MUST state which — the category error CLAUDE.md
#: records is a SURVIVAL feasibility test applied to a SUFFICIENCY number, and
#: `corridor band --standard` exists for exactly this reason.
#:
#: `collapsed` (PERSONAL_EOH_BASE = 1000, the shipped operating value) is
#: DELIBERATELY EXCLUDED, and the reason is structural rather than a preference.
#: `core/autarky.autarky_reference` refuses it in as many words — *"an abated
#: value cannot be the autarky reference; use 'sufficiency' (F_a) or 'survival'
#: (S_a)"* — because `collapsed` is already F_a·(1 − a), and the overbuild test
#: asks what the obligation would cost with NO apparatus at all. A standard that
#: has the apparatus baked into it cannot be the counterfactual for the
#: apparatus.
#:
#: THIS MODULE SHIPPED FOR ONE COMMIT WITH THE DEFECT IT NOW GUARDS: conditions
#: 1 and 3 ran at `collapsed` (feasibility's own default) while condition 2 ran
#: at `sufficiency` (overbuild's own default) — one verdict, two standards,
#: undeclared. Found by checking whether `corridor` was reachable, which is why
#: that check was worth running.
STANDARDS: tuple[str, ...] = ("survival", "sufficiency")

CONDITIONS: dict[str, dict[str, str]] = {
    "obligation_met": {
        "asks": "can the agents here survive?",
        "test": "human labour supply >= human share of the obligation account",
        "source": "scenarios/feasibility.labor_supply_per_capita",
        "failure_means": "the obligation cannot be served at all at this epsilon",
    },
    "delivery_pays": {
        "asks": "is the apparatus earning its keep?",
        "test": "the apparatus abates more obligation than it costs to hold",
        "source": "core/autarky.overbuild_check (obligation test)",
        "failure_means": (
            "overhead the automation is masking — members would be better off "
            "dispersing, not because they would die but because the collective "
            "is not worth being in"
        ),
    },
    "stock_stationary": {
        "asks": "can a carried stock be serviced rather than compounding?",
        "test": "surplus after obligation AND delivery cost is non-negative",
        "source": "this module, from the accounts and the labour supply",
        "failure_means": (
            "the obligation is met while the stock grows — you can feed everyone "
            "and still lose the bridges"
        ),
    },
}


def _as_dict(x: Any) -> dict:
    return asdict(x) if is_dataclass(x) and not isinstance(x, type) else dict(x)


def stability_at(
    epsilon: float = 0.40,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    population: float = 1.0e6,
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    standard: str = "sufficiency",
) -> dict:
    """
    The three conditions at one ε. Can the system stop here?

    Governing tests, all per capita per year:

        supply     = labour_supply_per_capita(adult_capacity)
        obligation = (1 - ε) · obligation_account / population
        delivery   = (1 - ε) · delivery_account / population

        1. obligation_met    supply >= obligation
        2. delivery_pays     overbuild_check(...).obligation_test
        3. stock_stationary  supply - obligation - delivery >= 0

    units: labour-hours per capita per year; the verdicts are boolean.

    ε-behaviour: obligation falls with ε (fewer human hours to serve a nearly
    flat obligation) while delivery rises with the capital stock the arc builds,
    so the two conditions bind at opposite ends. That is the point of reporting
    them separately.

    Worked example (canonical, ε=0.40, sufficiency, 2e9 TEH over 1e6 people):
    supply 1,200.0 h/person·yr against an obligation and a delivery cost that
    the arc table reports; the three flags are returned separately so which one
    fails is legible.

    Args:
        epsilon: Automation level [0.0, 0.99].
        capital_stock_teh: TOTAL apparatus capital in TEH, not per capita —
            `overbuild_check` divides by population itself. Defaults to
            `CAPITAL_STOCK_DEFAULT` (2e9, i.e. 2,000/capita at the 1M reference
            frame). **This module shipped for one commit with a default of
            2,000 TOTAL — 0.002 per capita — which made condition 2 unable to
            bind at all: it was not that the apparatus always paid, it was that
            there was no apparatus.**
        population: Frame population.
        adult_capacity_h_yr: Hours an adult can supply in a year.

    Raises:
        ValueError: if epsilon is outside [0.0, 0.99].
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if standard not in STANDARDS:
        raise ValueError(f"standard must be one of {STANDARDS}, got {standard!r}")

    base = personal_base_for(standard)
    acct = obligation_accounts(
        epsilon, population=population, personal_standard=standard
    )
    # `labor_supply_per_capita` directly, NOT `feasibility_check`: the only
    # quantity needed here is the supply, which does not depend on
    # `personal_base` at all. Passing a standard into a call whose output
    # ignores it is the silently-ignored-parameter failure, and it was in this
    # module for one commit.
    supply = labor_supply_per_capita(adult_capacity_h_yr=adult_capacity_h_yr)
    over = _as_dict(overbuild_check(
        capital_stock_teh=capital_stock_teh,
        population=population,
        epsilon=epsilon,
        standard=standard,
    ))

    human = 1.0 - epsilon
    obligation = human * acct["obligation"] / population
    delivery = human * acct["delivery"] / population
    surplus = supply - obligation - delivery

    obligation_met = supply >= obligation
    delivery_pays = bool(over["obligation_test"])
    stock_stationary = surplus >= 0.0

    failing = [
        name for name, ok in (
            ("obligation_met", obligation_met),
            ("delivery_pays", delivery_pays),
            ("stock_stationary", stock_stationary),
        ) if not ok
    ]

    return {
        "epsilon":            epsilon,
        "standard":           standard,
        "personal_base":      base,
        "supply_per_capita":  supply,
        "obligation_per_capita": obligation,
        "delivery_per_capita":   delivery,
        "surplus_per_capita":    surplus,
        "obligation_met":     obligation_met,
        "delivery_pays":      delivery_pays,
        "stock_stationary":   stock_stationary,
        "stationary":         not failing,
        "failing":            failing,
        "overbuild_verdict":  over["verdict"],
        # Carried so the standard's reach into condition 2 is OBSERVABLE. It is
        # the only field of the overbuild test that moves with the standard, and
        # without it a standard that never arrived would look identical.
        "autarky_reference":  over["autarky_reference"],
        "net_vs_autarky":     over["net_vs_autarky"],
        "capital_stock_teh":  capital_stock_teh,
        "note": (
            "Conditions 1 and 3 are ordered by construction — 3 implies 1 — and "
            "are reported separately because WHICH fails says what to do. All "
            f"three are evaluated at the {standard!r} standard "
            f"({base:,.0f} h/person·yr); a verdict mixing standards is the "
            "category error this repo has already made once."
        ),
    }


def stability_arc(
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **kw: Any,
) -> list[dict]:
    """
    The three conditions across the arc — where the system could stand still.

    units: as `stability_at`.

    Worked example (canonical, 2,000 TEH/capita): stationary at every reported
    ε, with the surplus rising to mid-arc and falling back as the delivery cost
    overtakes the obligation late.
    """
    return [stability_at(e, **kw) for e in points]


def stationary_band(
    tol: float = 1e-3,
    **kw: Any,
) -> dict:
    """
    The contiguous ε range over which all three conditions hold.

    Governing search: scan ε on a fine grid and return the first and last point
    at which `stationary` is True, plus whether the band is contiguous.

    units: dimensionless ε.

    A CONTIGUOUS BAND IS NOT ASSUMED. If the conditions fail in the middle and
    hold at both ends the band is reported as non-contiguous rather than
    silently spanned — the same discipline `guf_over_levy` needed when a ratio
    assumed monotone turned out to be U-shaped.

    THE BAND IS NOT A TARGET. A society may rationally sit outside it while
    building through; this reports where standing still is possible, not where
    anyone should stand.
    """
    n = max(2, int(round(0.99 / tol)))
    grid = [i * 0.99 / n for i in range(n + 1)]
    flags = [(e, stability_at(e, **kw)["stationary"]) for e in grid]
    return band_from_flags(flags)


def band_from_flags(flags: list[tuple[float, bool]]) -> dict:
    """
    The band logic, extracted from `stationary_band` so the NON-CONTIGUOUS path
    is reachable in a test.

    On the shipped calibration the band happens to be contiguous, so a test
    driving only the model cannot tell "contiguous because it was checked" from
    "contiguous because it was hard-coded" — a threshold that cannot fire, which
    this repo has been caught by before (`settlement_report`'s unconditional
    breach). Splitting the pure logic out makes the other branch testable on a
    synthetic input.

    Args:
        flags: (epsilon, stationary) pairs in ascending epsilon.

    Returns:
        dict with `lower`, `upper`, `contiguous`, `width`, `any_stationary`,
        `gaps` (the failing points INSIDE the band) and a `note`.
    """
    ok = [e for e, s in flags if s]
    if not ok:
        return {
            "lower": None, "upper": None, "contiguous": False,
            "width": 0.0, "any_stationary": False, "gaps": [],
            "note": "no ε on the grid satisfies all three conditions",
        }

    lower, upper = min(ok), max(ok)
    gaps = [round(e, 4) for e, s in flags if lower <= e <= upper and not s]
    return {
        "lower":          lower,
        "upper":          upper,
        "contiguous":     not gaps,
        "width":          upper - lower,
        "any_stationary": True,
        "gaps":           gaps[:20],
        "note": (
            "A band is reported as non-contiguous rather than silently spanned "
            "if the conditions fail inside it."
        ),
    }


def band_by_standard(**kw: Any) -> dict:
    """
    The stationary band at every admissible standard — both corners reported
    rather than one picked, the `land_stewardship.SCOPES` precedent.

    units: dimensionless ε.

    Directly comparable to `eoh corridor band --standard <s>`, which reports the
    binding survival floor at the same standards. The two answer different
    questions — corridor asks which band is SURVIVABLE, this asks where the
    system could STAND STILL — so they are not expected to agree, and stating
    the standard is what makes the difference legible instead of looking like a
    contradiction.
    """
    return {s: stationary_band(standard=s, **kw) for s in STANDARDS}


def stability_report(epsilon: float = 0.40, **kw: Any) -> dict:
    """
    The Phase 1 report. CLI: `eoh scenario run arc_stability`.
    """
    here = stability_at(epsilon, **kw)
    arc = stability_arc(**kw)
    band = stationary_band(**kw)
    by_standard = band_by_standard(**{k: v for k, v in kw.items() if k != "standard"})

    stationary_points = [r["epsilon"] for r in arc if r["stationary"]]
    return {
        "epsilon":     epsilon,
        "conditions":  CONDITIONS,
        "here":        here,
        "arc":         arc,
        "band":        band,
        "band_by_standard": by_standard,
        "standard":    here["standard"],
        "verdict": (
            f"At ε={epsilon:.2f}, standard={here['standard']!r}, the system is "
            f"{'STATIONARY' if here['stationary'] else 'NOT stationary'}"
            + ("" if here["stationary"] else f" (failing: {', '.join(here['failing'])})")
            + f". Across the reported arc {len(stationary_points)} of {len(arc)} "
            f"points are stationary"
            + (f", and the band is ε ∈ [{band['lower']:.3f}, {band['upper']:.3f}]"
               f"{'' if band['contiguous'] else ' — NOT contiguous'}."
               if band["any_stationary"] else ", and no point is.")
            + " The compass asks whether the system can STOP here, not whether "
              "it can reach the end of the arc."
        ),
        "reporting_only": True,
    }
