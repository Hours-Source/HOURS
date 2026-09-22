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

from collections.abc import Mapping
from typing import Any

import inspect

from hours_eoh.data import (
    LOW_EPSILON_CAPITAL_PROBE_TEH_PER_CAPITA,
    REFERENCE_FRAME_POPULATION,
)
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
    "OBLIGATION_STATE_OWNED", "obligation_state_keys",
    "low_epsilon_obligation_sensitivity",
]

#: The three `total_eoh` parameters the fixed point sets for itself. `epsilon`
#: is the variable being solved for, `population` is pinned to the reference
#: frame, and `basis` is a contract of the whole module. A caller supplying any
#: of them is not adjusting their state, they are breaking the solve — so these
#: are refused by name rather than silently overridden.
OBLIGATION_STATE_OWNED: frozenset[str] = frozenset({"epsilon", "population", "basis"})


def obligation_state_keys() -> frozenset[str]:
    """
    The physical-state parameters `obligation_state` may carry.

    Derived from `total_eoh`'s own signature rather than restated here, so a
    parameter added there becomes supplyable without editing this list — the
    copy-of-a-value failure this repo has found six times.
    """
    return frozenset(inspect.signature(total_eoh).parameters) - OBLIGATION_STATE_OWNED


def _checked_obligation_state(
    state: "Mapping[str, Any] | None",
) -> dict[str, Any]:
    """Validate a supplied obligation state, naming what is wrong with it."""
    if state is None:
        return {}
    allowed = obligation_state_keys()
    owned = sorted(k for k in state if k in OBLIGATION_STATE_OWNED)
    if owned:
        raise ValueError(
            f"obligation_state may not set {owned}: the fixed point owns them "
            "(epsilon is what it solves for, population is pinned to the "
            "reference frame, basis is a module contract)"
        )
    unknown = sorted(k for k in state if k not in allowed)
    if unknown:
        raise ValueError(
            f"obligation_state has no such total_eoh parameter: {unknown}. "
            f"Supplyable keys: {sorted(allowed)}"
        )
    return dict(state)

#: ATUS tier-1 prefix for work and work-related activities.
_WORK_PREFIX: str = "05"


def measured_hours(
    year: int | None = None,
    population: float = BEA_POPULATION,
    *,
    population_15_plus_supplied: float | None = None,
    unpaid_per_15plus: float | None = None,
    paid_per_15plus: float | None = None,
) -> dict:
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
    # ALL THREE OR NONE (2026-09-18). A partial supply would divide one
    # jurisdiction's unpaid hours by another's adult count, or set a foreign
    # unpaid figure beside America's paid one — the half-ported instrument this
    # parameterisation exists to prevent, at a finer grain. Refused rather than
    # blended, because a blend produces a number and no error.
    _supplied = (population_15_plus_supplied, unpaid_per_15plus, paid_per_15plus)
    if any(v is not None for v in _supplied) and not all(v is not None for v in _supplied):
        missing = [n for n, v in zip(
            ("population_15_plus_supplied", "unpaid_per_15plus", "paid_per_15plus"),
            _supplied) if v is None]
        raise ValueError(
            f"supply all three measured-hours inputs or none; missing {missing}. "
            "A partial supply mixes two jurisdictions' time use into one reading."
        )
    # NARROWED STRUCTURALLY, NOT ASSERTED. `_own` is a runtime fact mypy cannot
    # follow into the float() calls below, and a `type: ignore` there would hide
    # a real None leak from a caller who supplied two of three. Binding the three
    # inside the `is not None` test makes the narrowing something the checker can
    # see, which is the same remedy used for the frozen-frame resolve.
    if (population_15_plus_supplied is not None
            and unpaid_per_15plus is not None
            and paid_per_15plus is not None):
        _own = True
        _p15_own, _unpaid_own, _paid_own = (float(population_15_plus_supplied),
                                            float(unpaid_per_15plus),
                                            float(paid_per_15plus))
    else:
        _own = False
        _p15_own = _unpaid_own = _paid_own = 0.0

    y = latest_year() if year is None else year
    p15 = _p15_own if _own else population_15_plus(y)
    if population < p15:
        raise ValueError(
            f"population {population:,.0f} is below the survey's own 15+ count "
            f"{p15:,.0f}. `population` is not a free frame knob here — it is the "
            "population the ATUS 15+ figure belongs to, and the two travel "
            "together. Supplying a smaller one asserts more adults than people."
        )
    unpaid_15 = _unpaid_own if _own else observed_shares(y)["mapped_total"]
    # The reference layer already owns this conversion AND the days-per-year it
    # needs; re-declaring either would be a second account of one quantity.
    paid_15 = _paid_own if _own else hours_per_person_15plus(y, (_WORK_PREFIX,))
    share_15 = p15 / population
    return {
        # The ATUS survey year belongs to the SHIPPED series. Supplied hours have
        # their own vintage this module does not know, so it is not asserted.
        "year":              None if _own else y,
        "hours_source":      "supplied" if _own else "shipped_atus",
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
    *,
    population_15_plus_supplied: float | None = None,
    unpaid_per_15plus: float | None = None,
    paid_per_15plus: float | None = None,
    employment: "Mapping[str, float] | None" = None,
    obligation_state: "Mapping[str, Any] | None" = None,
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
        obligation_state: the jurisdiction's OWN physical state, forwarded to
            `total_eoh`. None (default) uses the canonical arc's state at each
            iterate, which is what every reading before 2026-09-21 did.
            **`capital_stock` is ABSOLUTE TEH at the reference frame, not per
            capita** — multiply a per-capita figure by REFERENCE_FRAME_POPULATION
            before passing it, or the frame seam closed for the Trust reopens
            here. Keys are checked against `total_eoh`'s signature; `epsilon`,
            `population` and `basis` are owned by this fixed point and refused.

    Returns, beyond ε: `epsilon_raw` and `clamped`. ε is floored at 0.0, and the
    floor is load-bearing — on the 65-sample MTUS panel it binds for 2 samples
    at `core` and 9 at `broad`, almost all of them 1965-66. A clamped reading
    reports 0.0000 whether the overshoot is 0.01 or 0.33, so `epsilon_raw`
    carries the unclamped value and `clamped` says which you are looking at.

    Raises:
        ValueError: on an unknown scope, or an unusable `obligation_state` key.
    """
    hours = measured_hours(
        year, population,
        population_15_plus_supplied=population_15_plus_supplied,
        unpaid_per_15plus=unpaid_per_15plus,
        paid_per_15plus=paid_per_15plus,
    )
    # `employment` was ALREADY pluggable here before this work — one third of the
    # labour side needed no change. It still validates scope.
    share = obligation_share(scope, employment=employment)["share"]
    human = hours["unpaid_per_capita"] + hours["paid_per_capita"] * share

    state = _checked_obligation_state(obligation_state)

    eps = 0.5
    total_pc = 0.0
    for _ in range(200):
        # THE OBLIGATION IS COMPUTED AT THE REFERENCE FRAME, NOT AT `population`,
        # AND — UNLESS `obligation_state` SAYS OTHERWISE — AT THE CANONICAL
        # ARC'S PHYSICAL STATE RATHER THAN THE CALLER'S.
        #
        # THE PIN WAS DESCRIBED AS INERT ON 2026-09-18 AND THAT WAS TRUE OF ONE
        # VARIABLE ONLY. The measurement behind it stands: per-capita `total_eoh`
        # is frame-INVARIANT in POPULATION to the last bit — 1,360.74 / 1,531.93
        # / 2,154.34 at ε = 0 / 0.40 / 0.90, ratio 1.0000000000 between the 1M
        # and 335M frames. What that reasoning did not reach is that the
        # obligation is NOT invariant in STATE, and a foreign caller's state is
        # not the canonical arc's.
        #
        # MEASURED 2026-09-21, and it is why `obligation_state` now exists: the
        # canonical arc holds capital_stock_teh = 0 at ε = 0, so infrastructure
        # and ecological EOH are both 0.00 and the obligation collapses to
        # personal-only. Against measured hours from a labour-intensive economy
        # the fixed point then floors at ε = 0 — 9 of 65 MTUS samples at `broad`,
        # RS1965 overshooting by 0.3267. Supplying that jurisdiction's own
        # capital lifts it: US1965 unclamps near 4,000 TEH/capita, CZ1965 near
        # 8,301, RS1965 near 16,000.
        #
        # `population` remains the frame the MEASURED hours were converted into,
        # which is a different quantity and stays separate. That separation is
        # what a foreign caller most needs to see: the hours are theirs, and the
        # obligation they are divided by is this package's unless they supply
        # their own state.
        domains = total_eoh(epsilon=eps, population=REFERENCE_FRAME_POPULATION,
                            **state)
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
        # THE FLOOR, REPORTED RATHER THAN HIDDEN. `epsilon` is max(0, ·) and a
        # clamped reading says 0.0000 whether the overshoot is 0.0001 or 0.33.
        # `epsilon_raw` is that same quantity unclamped at the converged
        # iterate, so "human hours exceed the modelled obligation" is a number
        # instead of a silence. A negative value is a finding about the
        # OBLIGATION or the ATTRIBUTION, not about the economy.
        "epsilon_raw":        1.0 - human / total_pc,
        "clamped":            (1.0 - human / total_pc) < 0.0,
        "currency_used":      None,
        # WHOSE TIME USE, AND WHOSE OCCUPATIONAL STRUCTURE. Carried out so a
        # reader of a single result can tell a US reading from a ported one
        # without inspecting the call.
        "hours_source":       hours["hours_source"],
        "employment_source":  "shipped_soc" if employment is None else "supplied",
    }


def low_epsilon_obligation_sensitivity(
    human_per_capita: float,
    capital_grid: tuple[float, ...] = LOW_EPSILON_CAPITAL_PROBE_TEH_PER_CAPITA,
) -> dict:
    """
    What the ε floor does as a jurisdiction's own capital replaces the arc's.

    REPORTING ONLY, and deliberately NOT a change to `canonical_physical_state`.

    THE CLAIM THIS EXPOSES AND DOES NOT TOUCH. The canonical arc holds
    `capital_stock_teh = 0` at ε = 0. Infrastructure and ecological EOH are then
    both 0.00 and the obligation is personal-only — 1,352.80 of 1,360.74 per
    capita, 99.4%. Measured against a labour-intensive economy's hours the fixed
    point floors at zero: on the 65-sample MTUS panel, 2 samples clamp at `core`
    and 9 at `broad`, all but one of them 1965-66. Whether a subsistence economy
    genuinely owes no infrastructure obligation is a THEORY question for the
    author (CLAUDE.md §3), so this function measures the consequence and leaves
    the arc alone.

    MEASURED 2026-09-21, broad-scope hours: US1965 unclamps near 4,000
    TEH/capita, CZ1965 near 8,301, RS1965 near 16,000. The US BEA reading of
    8,301 sits inside the grid so a real economy is locatable in the sweep.

    units: `capital_per_capita` in TEH/capita; `epsilon` dimensionless.

    Args:
        human_per_capita: the measured human obligation hours per capita —
            `labour_epsilon(...)["human_per_capita"]`.
        capital_grid: TEH per capita to sweep. Defaults to the declared probe
            grid in `data.py`; nothing in it is anybody's measured stock.

    Returns:
        `rows`, one per grid point, each with the obligation it produces, the
        clamped ε and the raw ε; plus `unclamps_at`, the first grid point where
        the floor stops binding, or None if it binds throughout.
    """
    rows = []
    unclamps_at: float | None = None
    for cap in capital_grid:
        eps = 0.5
        total_pc = 0.0
        for _ in range(200):
            domains = total_eoh(
                epsilon=eps, population=REFERENCE_FRAME_POPULATION,
                capital_stock=cap * REFERENCE_FRAME_POPULATION,
            )
            total_pc = sum(domains[d] for d in
                           ("personal", "infrastructure", "ecological", "knowledge")
                           ) / REFERENCE_FRAME_POPULATION
            nxt = max(0.0, 1.0 - human_per_capita / total_pc)
            if abs(nxt - eps) < 1e-9:
                eps = nxt
                break
            eps = nxt
        raw = 1.0 - human_per_capita / total_pc
        if raw >= 0.0 and unclamps_at is None:
            unclamps_at = cap
        rows.append({
            "capital_per_capita": cap,
            "total_obligation_per_capita": total_pc,
            "epsilon": eps,
            "epsilon_raw": raw,
            "clamped": raw < 0.0,
        })
    return {
        "human_per_capita": human_per_capita,
        "rows": rows,
        "unclamps_at": unclamps_at,
        "reporting_only": True,
        "does_not_change": "canonical_physical_state — see CLAUDE.md §3",
    }


def instrument_comparison(
    capital_rates: tuple[float, ...] = (15.94, 19.50, 23.17),
    population: float = BEA_POPULATION,
    *,
    scope: str = "government",
    doctrine: str = "current_cost",
    inventory: "Mapping[str, float] | None" = None,
    population_15_plus_supplied: float | None = None,
    unpaid_per_15plus: float | None = None,
    paid_per_15plus: float | None = None,
    employment: "Mapping[str, float] | None" = None,
) -> dict:
    """
    The two instruments side by side, with the honest verdict about their gap.

    units: dimensionless ε.

    Reports OVERLAP, ADJACENT or DIVERGENT rather than asserting agreement — a
    comparison that can only conclude "they agree" is not a comparison. The
    labour interval is [broad, core]; the capital interval is the span of the
    supplied rates AT ONE CELL of the capital grid.

    THE VERDICT DEPENDS ON A CHOICE, AND THAT CHOICE IS NOW STATED (2026-09-18).
    `scope` and `doctrine` were a hard-coded "government" and an inherited
    `current_cost` default, so this function silently read ONE CORNER of a grid
    the capital route insists must stay a grid — its three judgements being
    undeclared is the whole reason it returns 18 cells. Measured at the US
    frame: the corner gives ADJACENT with a gap of 0.046, while **8 of the 18
    declared cells fall inside the labour band** and the full grid (0.2003 –
    0.7571) OVERLAPS it.

    The corner remains the headline because government/current_cost is the most
    defensible single reading — switching the headline to the framing that
    produces agreement would be calibrating to the answer, which is the failure
    `reconciling_rate` warns about in its own docstring. The grid verdict is
    reported BESIDE it under `grid`, so a reader sees that the answer is a
    function of a declared choice rather than a property of the instruments.

    A SUPPLIED inventory has no declared scope/doctrine grid to sweep, so
    `grid["available"]` is False for a ported capital arm.
    """
    from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory

    # BOTH ARMS OR NEITHER, AND THE REPORT SAYS WHICH. Threading only the
    # capital inventory would compare a supplied capital reading against the
    # SHIPPED US labour reading and return a confident verdict that means
    # nothing — the half-ported instrument this parameterisation exists to make
    # inexpressible rather than merely discouraged.
    _lab_own = any(v is not None for v in
                   (population_15_plus_supplied, unpaid_per_15plus,
                    paid_per_15plus, employment))
    _cap_own = inventory is not None
    if _lab_own != _cap_own:
        raise ValueError(
            "supply BOTH arms or neither: "
            f"capital={'supplied' if _cap_own else 'shipped'}, "
            f"labour={'supplied' if _lab_own else 'shipped'}. Comparing one "
            "jurisdiction's capital against another's time use produces a "
            "verdict about no economy."
        )
    lab = {s: labour_epsilon(
               s, population=population,
               population_15_plus_supplied=population_15_plus_supplied,
               unpaid_per_15plus=unpaid_per_15plus,
               paid_per_15plus=paid_per_15plus,
               employment=employment)["epsilon"]
           for s in ("core", "broad")}
    cap = [epsilon_from_inventory(r, scope=scope, doctrine=doctrine,
                                  population=population, inventory=inventory)["epsilon"]
           for r in capital_rates]
    lab_lo, lab_hi = lab["broad"], lab["core"]
    cap_lo, cap_hi = min(cap), max(cap)

    if lab_hi >= cap_lo and cap_hi >= lab_lo:
        verdict, gap = "OVERLAP", 0.0
    else:
        gap = cap_lo - lab_hi if cap_lo > lab_hi else lab_lo - cap_hi
        verdict = "ADJACENT" if gap < 0.05 else "DIVERGENT"

    # THE GRID BESIDE THE CORNER. Same rates, so the two sweeps cannot differ by
    # a rate set: `capital_rates` defaults to a 19.50 mid where the band's own
    # derived mid is 19.5586, and passing it through keeps them one comparison.
    if inventory is None:
        from hours_eoh.scenarios.capital_retrodiction import retrodiction_grid
        _rows = retrodiction_grid(rates=capital_rates, population=population)
        _geps = [row["epsilon"] for row in _rows]
        _glo, _ghi = min(_geps), max(_geps)
        _inside = [row for row in _rows if lab_lo <= row["epsilon"] <= lab_hi]
        if lab_hi >= _glo and _ghi >= lab_lo:
            _gverdict, _ggap = "OVERLAP", 0.0
        else:
            _ggap = _glo - lab_hi if _glo > lab_hi else lab_lo - _ghi
            _gverdict = "ADJACENT" if _ggap < 0.05 else "DIVERGENT"
        grid_info: dict = {
            "available":           True,
            "low":                 _glo,
            "high":                _ghi,
            "verdict":             _gverdict,
            "gap":                 _ggap,
            "cells_inside_labour": len(_inside),
            "cells_total":         len(_rows),
            "note": (
                "the capital route's three judgements are undeclared, which is why "
                "it returns a grid; reading one cell of it is a choice and this "
                "reports what the whole grid says"
            ),
        }
    else:
        grid_info = {
            "available": False,
            "note": ("a supplied inventory has no declared scope/doctrine grid to "
                     "sweep — the grid is a property of the shipped table"),
        }

    return {
        "labour":   {"low": lab_lo, "high": lab_hi, "by_scope": lab},
        "capital":  {"low": cap_lo, "high": cap_hi, "rates": list(capital_rates),
                     "scope": scope, "doctrine": doctrine},
        "gap":      gap,
        "verdict":  verdict,
        "grid":     grid_info,
        "shared_denominator": (
            "both divide by total_eoh, so an error in the obligation passes both "
            "instruments; what is cross-checked is the machine/human split"
        ),
        "judgements": {"labour": 1, "capital": 3},
        "sources": {"capital": "supplied" if _cap_own else "shipped_bea",
                    "labour":  "supplied" if _lab_own else "shipped_atus"},
    }


def reconciling_rate(
    scope: str = "core",
    lo: float = 1.0,
    hi: float = 200.0,
    tol: float = 1e-4,
    population: float = BEA_POPULATION,
    *,
    inventory: "Mapping[str, float] | None" = None,
    population_15_plus_supplied: float | None = None,
    unpaid_per_15plus: float | None = None,
    paid_per_15plus: float | None = None,
    employment: "Mapping[str, float] | None" = None,
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

    # The bisection assumes ε falls as the rate rises. VERIFIED 2026-09-18 for a
    # SUPPLIED inventory too — strictly falling across rates 2 → 160 — so the
    # bracket stays valid when the capital arm is ported.
    target = labour_epsilon(
        scope, population=population,
        population_15_plus_supplied=population_15_plus_supplied,
        unpaid_per_15plus=unpaid_per_15plus,
        paid_per_15plus=paid_per_15plus,
        employment=employment)["epsilon"]
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if epsilon_from_inventory(mid, scope="government", population=population,
                                  inventory=inventory)["epsilon"] > target:
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
            f"capital route {comp['capital']['low']:.3f}–{comp['capital']['high']:.3f} "
            f"at {comp['capital']['scope']}/{comp['capital']['doctrine']}: "
            f"{comp['verdict']}"
            + ("" if comp["verdict"] == "OVERLAP" else f", gap {comp['gap']:.3f}")
            + (
                ""
                if not comp["grid"]["available"]
                else (
                    f" — but {comp['grid']['verdict']} across the declared grid "
                    f"({comp['grid']['cells_inside_labour']} of "
                    f"{comp['grid']['cells_total']} cells inside the labour band, "
                    f"{comp['grid']['low']:.3f}–{comp['grid']['high']:.3f}), so the "
                    f"verdict depends on the scope and doctrine chosen"
                )
            )
        ),
        "adopted":          False,
    }
