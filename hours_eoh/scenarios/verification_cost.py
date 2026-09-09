"""
What running the register costs, against the obligation it serves.

SPDX-License-Identifier: AGPL-3.0-or-later

REPORTING ONLY. No constant moves and no shipped number changes;
`TestVerificationChangesNothing` fails the moment that stops being true. This is
Phase 2 of the verification-cost work: Phase 1 (`reference/verification.py`)
counted the workers, this converts them to hours at a declared frame and puts
them beside the obligation. Phase 3 — whether the term enters `total_eoh` —
moves every ratio computed against the obligation and needs the author.

WHAT THIS ANSWERS. `anchor_comparison_draft.md` §7 states a falsification
condition: *if verification cost, once costed, exceeds the obligation it
verifies at any point on the arc, the anchor is not cheaper to audit than the
incumbents.* That was unanswerable while the term did not exist. It is
answerable now, and `verification_crossover()` answers it.

THE FRAME IS DECLARED, BECAUSE THIS IS EXACTLY WHERE THE SEAM OPENS. The census
is US-scale — BLS employment against `US_REFERENCE_POPULATION`. The package's
extensive constants are stated at `REFERENCE_FRAME_POPULATION`. A per-capita
rate is the only quantity that survives the move between them, so the conversion
runs through one, and every function here that takes a population says which
frame its answer is in.

**AND THE PER-CAPITA BASIS IS A FRAME CONVERSION, NOT A SCALING CLAIM.**
`reference/verification.SCALING_BASIS` says this cost follows the REGISTER's
throughput — admissions plus sunset-clock re-reviews — and not population. The
two readings disagree about the one thing the falsifier turns on, the
ε-behaviour:

    per_capita   the US apparatus costs a fixed rate per person. The obligation
                 GROWS along the arc, so the ratio FALLS. This is what the data
                 supports and it ignores the declared scaling basis.
    per_registered  the cost follows registered EOH, which rises steeply with ε.
                 This is what the module says is right and it has no measured
                 anchor, because the US registers nothing comparable.

Both are reported. Neither is adopted, and `which_basis_is_unsettled()` says so
in its own return value rather than in a comment.

Layer: scenarios/ — imports from core/ and reference/, never the reverse.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.data import REFERENCE_FRAME_POPULATION, US_REFERENCE_POPULATION
from hours_eoh.reference.verification import (
    direction_of_error,
    verification_workers,
    what_this_cannot_settle,
)
from hours_eoh.scenarios.food_conservation import hours_per_worker_year
from hours_eoh.scenarios.obligation_accounts import obligation_accounts

__all__ = [
    "verification_hours_us",
    "verification_hours_per_capita",
    "verification_account",
    "verification_arc",
    "verification_crossover",
    "which_basis_is_unsettled",
    "verification_report",
]


def verification_hours_us(scope: str = "core") -> dict:
    """
    Annual verification labour in the UNITED STATES, in hours.

    Governing equation:

        hours = workers(scope) × hours_per_worker_year()

    units: hours per year, at the US frame (`US_REFERENCE_POPULATION`).

    `hours_per_worker_year` is DERIVED from measured paid hours over measured
    employment, not a chosen 2,080 — the same conversion `servicing_census` uses,
    so the two censuses cannot drift on the one number they share.
    """
    workers = verification_workers(scope)
    h_worker = hours_per_worker_year()
    return {
        "scope":                 scope,
        "frame":                 "US",
        "frame_population":      US_REFERENCE_POPULATION,
        "workers":               workers["total_workers"],
        "by_function":           workers["by_function"],
        "hours_per_worker_year": h_worker,
        "total_hours":           workers["total_workers"] * h_worker,
    }


def verification_hours_per_capita(scope: str = "core") -> float:
    """
    Verification labour per person per year, at US institutional density.

    Governing equation: `verification_hours_us(scope) / US_REFERENCE_POPULATION`.
    units: hours per person per year.

    THE ONE QUANTITY THAT SURVIVES THE FRAME MOVE. Everything else in the census
    is extensive and means nothing away from the US population it was counted
    over.
    """
    return verification_hours_us(scope)["total_hours"] / US_REFERENCE_POPULATION


def verification_account(
    epsilon: float,
    scope: str = "core",
    population: float = REFERENCE_FRAME_POPULATION,
    basis: str = "per_capita",
    **state: Any,
) -> dict:
    """
    The verification term beside the obligation it serves, at one ε.

    Governing equations:

        per_capita      V = rate(scope) × population
        per_registered  V = rate(scope) × population × registered(ε)/registered(ε_ref)

    units: EOH-equivalent hours per year, at the caller's `population` frame.

    The second basis honours `SCALING_BASIS` — the cost follows the register's
    throughput — by scaling the measured US rate with registered EOH relative to
    a reference point on the arc. It has no measured anchor of its own; what it
    has is the right SHAPE, and the reference point is stated rather than fitted.

    Args:
        epsilon: machine-capability index ∈ [0, 0.99].
        scope: "core" (lower bound) or "broad" (upper bound).
        population: the frame. Defaults to the package reference frame.
        basis: "per_capita" or "per_registered" — see the module docstring.
        **state: forwarded to `obligation_accounts`.

    Returns the term, the three existing accounts, and the ratios that matter:
    verification over the OBLIGATION (what §7's falsifier is about) and over
    DELIVERY (which is the account it would join).

    Raises:
        ValueError: on an unknown basis, rather than silently using per_capita.
    """
    if basis not in ("per_capita", "per_registered"):
        raise ValueError(
            f"basis must be 'per_capita' or 'per_registered', got {basis!r}"
        )

    rate = verification_hours_per_capita(scope)
    verification = rate * population

    if basis == "per_registered":
        # The register's throughput, indexed to the arc point where the measured
        # rate was taken. ε_ref is DECLARED, not fitted: 0.40 is the package's
        # reference point and the one the US apparatus is least unlike.
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

        here = eoh_to_teh_pipeline(epsilon=epsilon, population=population)
        ref = eoh_to_teh_pipeline(epsilon=0.40, population=population)
        ratio = (here["registered_eoh"] / ref["registered_eoh"]
                 if ref["registered_eoh"] > 0.0 else 1.0)
        verification *= ratio

    acc = obligation_accounts(epsilon, population=population, **state)
    obligation = acc["obligation"]
    delivery = acc["delivery"]

    return {
        "epsilon":            epsilon,
        "scope":              scope,
        "basis":              basis,
        "frame_population":   population,
        "rate_per_capita":    rate,
        "verification":       verification,
        "obligation":         obligation,
        "delivery":           delivery,
        "stock":              acc["stock"],
        "verification_over_obligation": (verification / obligation
                                         if obligation > 0.0 else float("inf")),
        "verification_over_delivery":   (verification / delivery
                                         if delivery > 0.0 else float("inf")),
        # The account it would JOIN if Phase 3 adopts it, reported so the size of
        # that change is visible before anyone decides to make it.
        "delivery_with_verification":   delivery + verification,
        "adopted":            False,
    }


def verification_arc(
    scope: str = "core",
    basis: str = "per_capita",
    population: float = REFERENCE_FRAME_POPULATION,
    points: tuple[float, ...] = (0.0, 0.40, 0.90, 0.99),
    **state: Any,
) -> list[dict]:
    """
    The account at each arc point. units: as `verification_account`.

    `points` is a parameter and not a module constant so a caller can sweep its
    own: a ratio read at 0.40 alone is the trap this repo names as measuring
    where the defect is invisible, and the default is the four points every
    other arc report here uses.
    """
    return [
        verification_account(e, scope=scope, population=population,
                             basis=basis, **state)
        for e in points
    ]


def verification_crossover(
    scope: str = "core",
    basis: str = "per_capita",
    tol: float = 1e-4,
    population: float = REFERENCE_FRAME_POPULATION,
    **state: Any,
) -> dict:
    """
    The ε at which verification cost first exceeds the obligation it verifies.

    Governing condition:

        crossover = min{ ε : verification(ε) ≥ obligation(ε) }

    units: dimensionless ε.

    **THIS IS THE ANSWER TO §7 OF THE ANCHOR COMPARISON**, which says that if
    this crossing exists on the arc, the anchor is not cheaper to audit than the
    incumbents. Bisection on the arc, the same shape as
    `obligation_accounts.delivery_crossover`, because the obligation is
    non-linear in ε and the registered share more so.

    A crossover WOULD NOT BE A FAILURE ON ITS OWN, and this function does not
    call it one — the same caveat `delivery_crossover` carries. What it would
    mean is that the apparatus making the obligation legible costs more than the
    obligation, which is a real argument against the anchor and is exactly what
    §7 says it would take to change our mind.

    Returns `crossover_epsilon` (None if it never crosses in [0, 0.99]) and the
    ratio at each end, so a search that finds nothing still reports something.
    """
    def ratio(e: float) -> float:
        return verification_account(e, scope=scope, population=population,
                                    basis=basis, **state
                                    )["verification_over_obligation"]

    lo, hi = 0.0, 0.99
    if ratio(hi) < 1.0 and ratio(lo) < 1.0:
        crossover = None
    else:
        while hi - lo > tol:
            mid = (lo + hi) / 2.0
            if ratio(mid) >= 1.0:
                hi = mid
            else:
                lo = mid
        crossover = hi

    return {
        "scope":             scope,
        "basis":             basis,
        "crossover_epsilon": crossover,
        "ratio_at_zero":     ratio(0.0),
        "ratio_at_top":      ratio(0.99),
        "note": (
            "Not a failure condition by itself — the same caveat "
            "delivery_crossover carries. It is where the apparatus that makes "
            "the obligation legible costs as much as the obligation. Whether "
            "that is acceptable depends on what legibility buys, which this "
            "account does not carry."
        ),
    }


def which_basis_is_unsettled() -> dict:
    """
    The choice this module refuses to make, stated in its own return value.

    The per-capita and per-registered readings disagree about the ε-behaviour,
    which is the only thing the §7 falsifier turns on. Reporting one of them as
    THE answer would settle by presentation a question no measurement here
    settles.
    """
    return {
        "per_capita": (
            "What the data supports. The US apparatus is counted against the US "
            "population, so a per-person rate is the one quantity that survives "
            "the frame move. It ignores `SCALING_BASIS`, which says this cost "
            "follows the register and not the population."
        ),
        "per_registered": (
            "What the module says is right. Verification follows admissions and "
            "re-reviews, and the registered share rises steeply along the arc. "
            "It has no measured anchor: the US registers nothing comparable, so "
            "the level is carried over from the per-capita measurement at a "
            "DECLARED reference point rather than measured at each ε."
        ),
        "why_it_matters": (
            "They disagree about the DIRECTION of the ratio across the arc, and "
            "the direction is what §7's falsifier turns on. Under per_capita the "
            "obligation grows and the ratio falls; under per_registered the cost "
            "chases the ledger."
        ),
        "settles_by": (
            "hours per registration decision, from any institution that runs an "
            "eligibility or claims register at scale and publishes both its "
            "caseload and its staffing. That is one measurement and it would "
            "settle the basis for both readings."
        ),
        "adopted": None,
    }


def verification_report(scope: str = "core", **state: Any) -> dict:
    """
    Everything at once, with the caveats attached rather than alongside.

    REPORTING ONLY. The `verdict` is a sentence about the ratios, computed from
    them rather than restated beside them — the drift this repo has caught more
    often than any other.
    """
    arcs = {b: verification_arc(scope=scope, basis=b, **state)
            for b in ("per_capita", "per_registered")}
    crossings = {b: verification_crossover(scope=scope, basis=b, **state)
                 for b in ("per_capita", "per_registered")}

    reachable = [b for b, c in crossings.items()
                 if c["crossover_epsilon"] is not None]
    worst = max(
        (row["verification_over_obligation"]
         for rows in arcs.values() for row in rows),
        default=0.0,
    )

    if reachable:
        verdict = (
            "the audit advantage does not hold across the whole arc under "
            + " and ".join(reachable)
            + "; see §7 of the anchor comparison"
        )
    else:
        verdict = (
            "verification cost stays below the obligation it verifies at every "
            f"arc point under both bases, peaking at {worst:.2%} of it"
        )

    return {
        "scope":             scope,
        "rate_per_capita":   verification_hours_per_capita(scope),
        "us_census":         verification_hours_us(scope),
        "arc":               arcs,
        "crossover":         crossings,
        "peak_share_of_obligation": worst,
        "basis_unsettled":   which_basis_is_unsettled(),
        "direction_of_error": direction_of_error(),
        "cannot_settle":     what_this_cannot_settle(),
        "verdict":           verdict,
        "adopted":           False,
    }
