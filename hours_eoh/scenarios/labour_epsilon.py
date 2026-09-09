"""
ε read off time use — the second instrument, and the one with no currency in it.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. No constant moves and no shipped number changes;
`TestLabourEpsilonChangesNothing` fails the moment that stops being true.

WHY A SECOND INSTRUMENT. `capital_retrodiction` reads ε off the BEA asset
inventory and answers §7's retrodiction falsifier. It was the only reading of ε
against a real economy the framework had, which left its most exposed claim
resting on one measurement. This is the independent one:

    capital route   BEA asset valuations ──► machine EOH ──► ε
    labour route    ATUS time diaries    ──► human EOH   ──► ε

The NUMERATORS are independent — asset valuations and time diaries share no
data, no agency and no method. **The DENOMINATOR is not**: both divide by
`total_eoh`, so an error in the obligation itself passes both instruments
undetected. What is cross-checked here is the machine/human SPLIT, which is
exactly the part that had rested on a single reading.

**AND THE LABOUR ROUTE NEEDS ONE JUDGEMENT WHERE THE CAPITAL ROUTE NEEDS THREE.**
No valuation doctrine, no currency conversion, no scope of capital — only which
paid work discharges an obligation (`reference/obligation_work`). That asymmetry
is the value-anchor section's census-versus-valuation claim, observed on the
framework's own retrodiction rather than argued.

WHAT IT FINDS, and the result is close agreement rather than overlap: at the
narrow attribution the labour route's ε sits just BELOW the capital route's
floor. The two bracket a narrow gap. `reconciling_rate()` reports the conversion
rate at which they would meet, which is the diagnostic that says which side to
doubt.

THE FRAME IS DECLARED AT EVERY STEP. ATUS measures per person aged 15+; the
package's extensives are per capita. `population_15_plus` carries the conversion
and every function here says which frame its answer is in.

Layer: scenarios/ — imports from core/ and reference/, never the reverse.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.data import REFERENCE_FRAME_POPULATION
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.reference.atus_time_use import (
    hours_per_person_15plus, latest_year, population_15_plus,
)
from hours_eoh.reference.capital_inventory import BEA_POPULATION
from hours_eoh.reference.obligation_work import obligation_share, what_this_cannot_settle
from hours_eoh.scenarios.component_shares import observed_shares

__all__ = [
    "measured_hours", "labour_epsilon", "instrument_comparison",
    "reconciling_rate", "labour_epsilon_report",
]

#: ATUS tier-1 prefix for work and work-related activities.
_WORK_PREFIX: str = "05"


def measured_hours(year: int | None = None, population: float = BEA_POPULATION) -> dict:
    """
    Human hours on obligation, per capita per year, from time diaries.

    Governing sums:

        unpaid = Σ personal-component codes           [h/person 15+ · yr]
        paid   = Σ ATUS 05xx                          [h/person 15+ · yr]
        per capita = h/person15+ × population_15_plus / population

    units: hours per capita per year, at the stated `population` frame.

    The unpaid half is `component_shares.observed_shares`, which maps ATUS
    tier-3 codes onto the four personal components and reports what it could not
    map. The paid half is the whole of ATUS work; how much of it discharges an
    obligation is the one judgement, and it lives in `reference/obligation_work`.
    """
    y = latest_year() if year is None else year
    p15 = population_15_plus(y)
    if population < p15:
        raise ValueError(
            f"population {population:,.0f} is below the survey's own 15+ count "
            f"{p15:,.0f}. `population` is not a free frame knob here — it is the "
            "population the ATUS 15+ figure belongs to, and the two travel "
            "together. Supplying a smaller one asserts more adults than people."
        )
    unpaid_15 = observed_shares(y)["mapped_total"]
    # The reference layer already owns this conversion AND the days-per-year it
    # needs; re-declaring either would be a second account of one quantity.
    paid_15 = hours_per_person_15plus(y, (_WORK_PREFIX,))
    share_15 = population_15_plus(y) / population
    return {
        "year":              y,
        "frame":             "per capita, converted from ATUS per person 15+",
        "population":        population,
        "population_15_plus": population_15_plus(y),
        "share_15_plus":     share_15,
        "unpaid_per_15plus": unpaid_15,
        "paid_per_15plus":   paid_15,
        "unpaid_per_capita": unpaid_15 * share_15,
        "paid_per_capita":   paid_15 * share_15,
    }


def labour_epsilon(
    scope: str = "core",
    year: int | None = None,
    population: float = BEA_POPULATION,
    tol: float = 1e-9,
) -> dict:
    """
    ε implied by measured human hours against the obligation they discharge.

    Governing condition, solved by fixed point because the obligation itself
    moves with ε:

        ε = 1 − human_hours / total_eoh(ε)

    units: dimensionless ε ∈ [0, 1).

    The obligation is NOT fixed as automation rises — infrastructure and
    knowledge EOH both grow with the capital that does the automating — so the
    naive one-shot division understates ε. Iterated to a fixed point instead,
    the same reason `feasibility.feasible_epsilon` bisects rather than inverting.

    Args:
        scope: "core" (upper bound on ε) or "broad" (lower bound). See
            `reference/obligation_work.SCOPES`.
        year: ATUS survey year; None → latest.
        population: the frame.

    Raises:
        ValueError: on an unknown scope.
    """
    hours = measured_hours(year, population)
    share = obligation_share(scope)["share"]          # validates scope
    human = hours["unpaid_per_capita"] + hours["paid_per_capita"] * share

    eps = 0.5
    for _ in range(200):
        # THE OBLIGATION IS COMPUTED AT THE REFERENCE FRAME, NOT AT `population`,
        # and this is the frame seam biting twice in one function. Passing the US
        # population collapses the fixed point, because `CAPITAL_STOCK_DEFAULT`
        # is stated "at the 1M reference population" and does NOT scale with the
        # argument — 335M people would hold the capital of 1M, which the
        # constant's own tag block warns about in as many words. Per-capita
        # obligation is what is wanted and it is frame-invariant only where the
        # extensive constants are actually calibrated. `population` remains the
        # frame the MEASURED hours were converted into, which is a different
        # quantity and stays separate.
        domains = total_eoh(epsilon=eps, population=REFERENCE_FRAME_POPULATION)
        total_pc = sum(domains[d] for d in
                       ("personal", "infrastructure", "ecological", "knowledge")
                       ) / REFERENCE_FRAME_POPULATION
        nxt = max(0.0, 1.0 - human / total_pc)
        if abs(nxt - eps) < tol:
            eps = nxt
            break
        eps = nxt

    return {
        "scope":              scope,
        "year":               hours["year"],
        "obligation_share":   share,
        "human_per_capita":   human,
        "unpaid_per_capita":  hours["unpaid_per_capita"],
        "attributed_paid_per_capita": hours["paid_per_capita"] * share,
        "total_obligation_per_capita": total_pc,
        "epsilon":            eps,
        "currency_used":      None,
    }


def instrument_comparison(
    capital_rates: tuple[float, ...] = (15.94, 19.50, 23.17),
    population: float = BEA_POPULATION,
) -> dict:
    """
    The two instruments side by side, with the honest verdict about their gap.

    units: dimensionless ε.

    Reports OVERLAP, ADJACENT or DIVERGENT rather than asserting agreement — a
    comparison that can only conclude "they agree" is not a comparison. The
    labour interval is [broad, core]; the capital interval is the span of the
    supplied rates at government scope, current cost.
    """
    from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory

    lab = {s: labour_epsilon(s, population=population)["epsilon"] for s in ("core", "broad")}
    cap = [epsilon_from_inventory(r, scope="government", population=population)["epsilon"]
           for r in capital_rates]
    lab_lo, lab_hi = lab["broad"], lab["core"]
    cap_lo, cap_hi = min(cap), max(cap)

    if lab_hi >= cap_lo and cap_hi >= lab_lo:
        verdict, gap = "OVERLAP", 0.0
    else:
        gap = cap_lo - lab_hi if cap_lo > lab_hi else lab_lo - cap_hi
        verdict = "ADJACENT" if gap < 0.05 else "DIVERGENT"

    return {
        "labour":   {"low": lab_lo, "high": lab_hi, "by_scope": lab},
        "capital":  {"low": cap_lo, "high": cap_hi, "rates": list(capital_rates)},
        "gap":      gap,
        "verdict":  verdict,
        "shared_denominator": (
            "both divide by total_eoh, so an error in the obligation passes both "
            "instruments; what is cross-checked is the machine/human split"
        ),
        "judgements": {"labour": 1, "capital": 3},
    }


def reconciling_rate(
    scope: str = "core",
    lo: float = 1.0,
    hi: float = 200.0,
    tol: float = 1e-4,
    population: float = BEA_POPULATION,
) -> dict:
    """
    The currency-per-TEH rate at which the capital route would meet the labour route.

    units: units of the inventory's currency per TEH.

    THE DIAGNOSTIC, not a recommendation. If the reconciling rate falls inside
    `capital_retrodiction.conversion_band()` the two instruments are consistent
    under some defensible convention; if it falls outside, at least one of them
    is wrong and the band says which direction to look. It is emphatically NOT a
    value to adopt — solving for the input that makes two estimates agree is
    calibrating to the target, which is the failure this repo names.
    """
    from hours_eoh.scenarios.capital_retrodiction import conversion_band, epsilon_from_inventory

    target = labour_epsilon(scope, population=population)["epsilon"]
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if epsilon_from_inventory(mid, scope="government", population=population)["epsilon"] > target:
            lo = mid            # ε falls as the rate rises
        else:
            hi = mid
    band = conversion_band()
    return {
        "target_epsilon":  target,
        "reconciling_rate": hi,
        "band_low":        band["low"],
        "band_high":       band["high"],
        "inside_band":     band["low"] <= hi <= band["high"],
        "is_a_recommendation": False,
        "note": (
            "solving for the input that makes two estimates agree is calibrating "
            "to the target; this reports where that input would have to sit, so "
            "a reader can judge whether the instruments are consistent"
        ),
    }


def labour_epsilon_report(population: float = BEA_POPULATION) -> dict:
    """Everything, with the verdict computed from the numbers rather than beside them."""
    comp = instrument_comparison(population=population)
    rec = reconciling_rate(population=population)
    return {
        "measured_hours":   measured_hours(population=population),
        "by_scope":         {s: labour_epsilon(s, population=population) for s in ("core", "broad")},
        "comparison":       comp,
        "reconciling":      rec,
        "cannot_settle":    what_this_cannot_settle(),
        "verdict": (
            f"labour route {comp['labour']['low']:.3f}–{comp['labour']['high']:.3f} against "
            f"capital route {comp['capital']['low']:.3f}–{comp['capital']['high']:.3f}: "
            f"{comp['verdict']}"
            + ("" if comp["verdict"] == "OVERLAP" else f", gap {comp['gap']:.3f}")
        ),
        "adopted":          False,
    }
