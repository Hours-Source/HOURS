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

from hours_eoh.data import (
    ARC_REPORTING_POINTS,
    REFERENCE_FRAME_POPULATION,
    US_REFERENCE_POPULATION,
)
from hours_eoh.reference.verification import (
    direction_of_error,
    verification_workers,
    what_this_cannot_settle,
)
from hours_eoh.data import MEASURED_CAPACITY_H_YR
from hours_eoh.scenarios.feasibility import feasibility_check
from hours_eoh.scenarios.food_conservation import hours_per_worker_year
from hours_eoh.scenarios.obligation_accounts import obligation_accounts

#: Grid the PEAK is searched on, distinct from the four arc reporting points.
#: Numerics only — it selects no result and carries no theory. It exists because
#: the `per_registered` ratio turns between two reporting points, so the four
#: points cannot see its maximum. `test_tolerances`' rule applies: refining this
#: grid must not move a reported result beyond the grid spacing.
#: Spans the same arc as `ARC_REPORTING_POINTS` and is bound to its ceiling, so
#: the two cannot drift apart — the shadow-constant rule.
PEAK_SEARCH_POINTS: tuple[float, ...] = tuple(
    max(ARC_REPORTING_POINTS) * i / 200 for i in range(201)
)

__all__ = [
    "verification_hours_us",
    "verification_hours_per_capita",
    "verification_account",
    "verification_arc",
    "verification_crossover",
    "net_fraction_falsifier",
    "registrant_scope_sensitivity",
    "verification_feasibility_corridor",
    "which_binds_across_the_arc",
    "corridor_is_usable",
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

    Returns `crossover_epsilon` (None if it never crosses in [0, 0.99]),
    `returns_below_at` (where it comes back under, for a crossing that does not
    persist to the top of the arc), the ratio at each end, and the peak with the
    ε it sits at — so a search that finds nothing still reports something, and
    a MID-ARC excursion is reported as one rather than missed.
    """
    def ratio(e: float) -> float:
        return verification_account(e, scope=scope, population=population,
                                    basis=basis, **state
                                    )["verification_over_obligation"]

    # THE SEARCH IS SEEDED FROM THE GRID, NOT FROM THE ENDPOINTS. Testing
    # `ratio(0) < 1 and ratio(0.99) < 1` and concluding "no crossover" is only
    # valid for a MONOTONE ratio. `per_registered` is not monotone — it turns
    # where registered EOH peaks, at ε≈0.77 — so there is a band of rates whose
    # cost exceeds the obligation across the middle of the arc and is back below
    # it at both ends. Measured on the shipped configuration: at 110x the rate
    # the ratio peaks at 1.25 and the endpoint test returned None. That made
    # §7's falsifier unfalsifiable in exactly the region where the extremum
    # hides — `LEVY_SUFFICIENCY_WARN`'s defect applied to the anchor's audit
    # claim, which this module's own docstring says it exists to avoid.
    grid = sorted(set(PEAK_SEARCH_POINTS) | {0.0, 0.99})
    ratios = [ratio(e) for e in grid]
    first = next((i for i, r in enumerate(ratios) if r >= 1.0), None)

    if first is None:
        crossover = None
        exits = None
    elif first == 0:
        crossover = grid[0]
        exits = next((grid[i] for i in range(1, len(grid)) if ratios[i] < 1.0),
                     None)
    else:
        lo, hi = grid[first - 1], grid[first]
        while hi - lo > tol:
            mid = (lo + hi) / 2.0
            if ratio(mid) >= 1.0:
                hi = mid
            else:
                lo = mid
        crossover = hi
        exits = next(
            (grid[i] for i in range(first + 1, len(grid)) if ratios[i] < 1.0),
            None,
        )

    return {
        "scope":             scope,
        "basis":             basis,
        "crossover_epsilon": crossover,
        "returns_below_at":  exits,
        "ratio_at_zero":     ratio(0.0),
        "ratio_at_top":      ratio(0.99),
        "peak_ratio":        max(ratios),
        "peak_epsilon":      grid[ratios.index(max(ratios))],
        "note": (
            "Not a failure condition by itself — the same caveat "
            "delivery_crossover carries. It is where the apparatus that makes "
            "the obligation legible costs as much as the obligation. Whether "
            "that is acceptable depends on what legibility buys, which this "
            "account does not carry."
        ),
    }


def net_fraction_falsifier(
    floor: float,
    scope: str = "core",
    basis: str = "per_registered",
    population: float = REFERENCE_FRAME_POPULATION,
    **state: Any,
) -> dict:
    """
    The ε at which the NET fraction of the obligation falls below a declared floor.

    Governing quantity:

        net(ε) = 1 − verification(ε) / obligation(ε)

    units: dimensionless ε; `floor` is a dimensionless fraction in (0, 1).

    **WHY THIS EXISTS AND `verification_crossover` IS NOT ENOUGH.** §7's falsifier
    is a crossover test at ratio 1.0, and the net-energy literature's result is
    that a crossover set at 1 fires far too late. What matters is the fraction of
    gross obligation left for actual entropy reduction, and it degrades
    non-linearly: EROI's net fraction (EROI−1)/EROI is insensitive above roughly
    10–15:1 and collapses below it. **A register consuming 20% of the obligation
    it verifies has not crossed over and has also lost the comparative audit
    claim outright.** So the crossover answers a question nobody should have
    asked, and this answers the one they should.

    **THE FLOOR IS REQUIRED AND HAS NO DEFAULT, DELIBERATELY.** A threshold
    shipped with this function would be calibrated against the configuration it
    is then checked on, which is the `LEVY_SUFFICIENCY_WARN` defect applied to
    the anchor's audit claim. The bound must be declared in advance by whoever
    is making the comparative argument, and different declarations are different
    arguments.

    Returns the ε where the net fraction first drops below `floor` (None if it
    never does), the minimum net fraction on the arc and where it sits.

    Raises:
        ValueError: if `floor` is not in (0.0, 1.0).
    """
    if not 0.0 < floor < 1.0:
        raise ValueError(
            f"floor must be a fraction in (0.0, 1.0), got {floor}. It has no "
            "default on purpose: a threshold this module chose would be "
            "calibrated to the configuration it is checked against."
        )

    grid = sorted(set(PEAK_SEARCH_POINTS) | {0.0, 0.99})
    nets = [
        1.0 - verification_account(e, scope=scope, population=population,
                                   basis=basis, **state
                                   )["verification_over_obligation"]
        for e in grid
    ]
    breach = next((grid[i] for i, n in enumerate(nets) if n < floor), None)
    worst = min(nets)

    return {
        "scope":            scope,
        "basis":            basis,
        "floor":            floor,
        "breach_epsilon":   breach,
        "min_net_fraction": worst,
        "min_at_epsilon":   grid[nets.index(worst)],
        "floor_is_declared_not_shipped": True,
        "note": (
            "The floor is the caller's argument, not this module's. A crossover "
            "at ratio 1.0 is the special case floor=0.0, which the net-energy "
            "literature says fires far too late to be the interesting test."
        ),
    }


def registrant_scope_sensitivity(
    registrant_multiple: float,
    scope: str = "core",
    basis: str = "per_registered",
    population: float = REFERENCE_FRAME_POPULATION,
    **state: Any,
) -> dict:
    """
    What the measured apparatus cost becomes if the registrant side is added.

    units: dimensionless ratio of the obligation; `registrant_multiple` is
    dimensionless (registrant-side hours per unit of apparatus-side hours).

    **THIS IS NOT AN ESTIMATE AND MUST NEVER BE PRESENTED AS ONE.** The census
    behind `verification_account` is APPARATUS-side: it counts people whose job
    is to verify. The hour a registrant spends documenting their own fulfilment
    is nobody's occupation and no occupational census reaches it. This function
    does not measure that hour. It answers one conditional question: **if the
    registrant side ran at `registrant_multiple` times the apparatus, would §7's
    falsifier still not fire?**

    **`registrant_multiple` IS REQUIRED AND HAS NO DEFAULT**, on the
    `currency_per_teh` precedent. A shipped multiple would turn a transferred
    judgement into a constant, and this one does not transfer cleanly:

      - The only measured case is US federal tax compliance. Registrant-side
        hours there run **~40× the administering agency's workforce** — the one
        comparison in matching units (workers against workers). The widely
        quoted 23–26× compares hours to a money budget and does not.
      - That case is **adversarial and money-denominated**; a register verifying
        physical fulfilment against a stated obligation is neither.
      - **Its own error bar is 7.7×.** The IRS revised the same quantity from
        363 million to 2.8 billion hours as a methodology change. A figure built
        on it inherits an order of magnitude of revision risk.

    So the honest output is a sensitivity with the judgement named in the return
    value, and `is_measured` is False and stays False.

    Raises:
        ValueError: if `registrant_multiple` is not positive.
    """
    if registrant_multiple <= 0.0:
        raise ValueError(
            f"registrant_multiple must be > 0, got {registrant_multiple}. "
            "There is no default: the multiple is a transferred judgement from "
            "one adversarial, money-denominated case, not a measurement."
        )

    grid = sorted(set(PEAK_SEARCH_POINTS) | {0.0, 0.99})
    apparatus = [
        verification_account(e, scope=scope, population=population,
                             basis=basis, **state
                             )["verification_over_obligation"]
        for e in grid
    ]
    # The registrant side is ADDITIONAL to the apparatus, not a replacement for
    # it — the two are disjoint by construction (one is an occupation, the other
    # is definitionally not).
    combined = [a * (1.0 + registrant_multiple) for a in apparatus]
    peak = max(combined)
    crossing = next((grid[i] for i, c in enumerate(combined) if c >= 1.0), None)

    return {
        "scope":               scope,
        "basis":               basis,
        "registrant_multiple": registrant_multiple,
        "apparatus_peak":      max(apparatus),
        "combined_peak":       peak,
        "crossover_epsilon":   crossing,
        "crosses":             crossing is not None,
        "is_measured":         False,
        "judgement": (
            "The multiple is transferred from US federal tax compliance, the "
            "only case where the registrant side has been measured. That case "
            "is adversarial and money-denominated; a HOURS register is neither. "
            "The comparison in matching units (workers against workers) is ~40x; "
            "the quoted 23-26x compares hours to a money budget and does not "
            "transfer. The source figure carries a 7.7x methodology revision in "
            "its own history, so this output spans an order of magnitude before "
            "any question about transferability is asked."
        ),
    }


def verification_feasibility_corridor(
    registrant_multiple: float,
    epsilon: float = 0.40,
    scope: str = "core",
    basis: str = "per_registered",
    adult_capacity_h_yr: float = MEASURED_CAPACITY_H_YR,
    population: float = REFERENCE_FRAME_POPULATION,
    **state: Any,
) -> dict:
    """
    The three bounds on verification cost, in one unit, with which one binds.

    units: each bound is a dimensionless REGISTRANT MULTIPLE — registrant-side
    hours per unit of apparatus-side hours — so the three are comparable and
    the smallest is the binding constraint.

    **WHY A CORRIDOR AND NOT A POINT.** The registrant multiple cannot be known
    in advance: it depends on the evidence standard, the recording cadence and
    the re-review frequency, which are a register's design rather than a fact
    about the world. Shipping a point estimate of an unknowable parameter is the
    failure this repo names as calibrating to the target you then check against.
    So this does not estimate the multiple. **It reports how large the multiple
    would have to be before each constraint binds**, which is a statement about
    the framework rather than about an institution nobody has built yet.

    That is threshold analysis, standard in health-technology assessment, and it
    is the same instrument as `crossing_registrant_multiple` one level up. What
    this adds is that **the §7 falsifier is not the binding constraint
    everywhere**, and nothing previously checked which was:

      - `ratio_bound`      verification equals the obligation it verifies.
                           §7's falsifier. Institutional — it compares two
                           quantities the framework itself defines.
      - `clearing_bound`   obligation + verification exceeds the labour a
                           population can supply, so the system stops clearing.
                           **A registrant's documenting hour is an hour not
                           spent fulfilling**, so this is an addition to demand
                           and not a separate account.
      - `physical_bound`   verification alone exceeds total labour supply. The
                           only bound with NO institution in it, and therefore
                           the only one that cannot be argued away.

    **THE CORRIDOR HAS EDGES AND NO CENTRE.** A reader who wants a single number
    from it is asking for the estimate this function refuses to produce — the
    IPCC's downstream failure, where a published range is collapsed to its
    midpoint by everyone who quotes it. The edges come from three named
    instruments; nothing here places a point between them.

    Args:
        registrant_multiple: REQUIRED, no default. What the caller asserts the
            registrant side costs relative to the apparatus. Reported back
            against the three bounds; it does not affect them.
        epsilon: where on the arc to evaluate. The binding bound CHANGES along
            the arc, which is the finding.

    Raises:
        ValueError: if `registrant_multiple` is not positive.
    """
    if registrant_multiple <= 0.0:
        raise ValueError(
            f"registrant_multiple must be > 0, got {registrant_multiple}"
        )

    acct = verification_account(epsilon, scope=scope, population=population,
                                basis=basis, **state)
    v_per_capita = acct["verification"] / population
    obligation_per_capita = acct["obligation"] / population

    # The clearing bound runs through `feasibility_check`'s OWN verification
    # parameter rather than being recomputed here. Two accounts of one quantity
    # is the shape that let `psi` diverge from `psi_applied`, and this module
    # named that wiring gap before closing it.
    base = feasibility_check(
        adult_capacity_h_yr=adult_capacity_h_yr, epsilon=epsilon
    )
    supply = base["supply_per_capita"]
    demand = base["total_demand_per_capita"]

    def _bound(headroom: float) -> float | None:
        # combined = v x (1 + m); the bound binds when combined >= headroom.
        if v_per_capita <= 0.0:
            return None
        m = headroom / v_per_capita - 1.0
        return m if m > 0.0 else 0.0

    bounds = {
        "ratio_bound":    _bound(obligation_per_capita),
        "clearing_bound": _bound(max(0.0, supply - demand)),
        "physical_bound": _bound(supply),
    }
    live = {k: v for k, v in bounds.items() if v is not None}
    binding = min(live, key=lambda k: live[k]) if live else None

    # THE WIRED PATH IS THE CHECK ON THE ARITHMETIC ABOVE. Running
    # `feasibility_check` with the combined verification load must stop
    # clearing exactly where `clearing_bound` says it does — if the two
    # disagree, one of them is wrong and the bound is the one nobody would
    # notice.
    clearing = bounds["clearing_bound"]
    if clearing is not None:
        at_bound = feasibility_check(
            adult_capacity_h_yr=adult_capacity_h_yr, epsilon=epsilon,
            verification_h_per_capita=v_per_capita * (1.0 + clearing),
        )
        clearing_verified = abs(at_bound["demand_supply_ratio"] - 1.0) < 1e-6
    else:
        clearing_verified = None

    return {
        "epsilon":             epsilon,
        "scope":               scope,
        "basis":               basis,
        "registrant_multiple": registrant_multiple,
        "clearing_bound_verified_through_feasibility": clearing_verified,
        "verification_h_per_capita": v_per_capita,
        "labour_supply_per_capita": supply,
        "demand_per_capita":   demand,
        **bounds,
        "binding_bound":       binding,
        "binding_multiple":    live.get(binding) if binding else None,
        "within_corridor": (
            registrant_multiple < live[binding] if binding else None
        ),
        "is_measured":         False,
        "note": (
            "Bounds are thresholds computed from the framework; the multiple is "
            "the caller's declared judgement and moves none of them. The "
            "corridor has edges and no centre - a midpoint between these is an "
            "estimate this function declines to make."
        ),
    }


def which_binds_across_the_arc(
    scope: str = "core",
    basis: str = "per_registered",
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **state: Any,
) -> list[dict]:
    """
    Which of the three bounds is tightest at each ε. units: as the corridor.

    **THE POINT OF THE FUNCTION IS THAT THE ANSWER CHANGES.** At low ε the
    population is close to its labour ceiling — the shipped configuration runs
    demand/supply near 0.9 at ε=0 — so the clearing bound binds hard. At high ε
    the obligation is met with little human labour, headroom is large, and §7's
    ratio bound binds instead. **A falsifier that tests only the ratio is
    therefore testing the non-binding constraint over most of the low arc**, and
    nothing checked that before this function existed.

    The multiple is not needed here: thresholds do not depend on it.
    """
    return [
        {
            k: v for k, v in verification_feasibility_corridor(
                1.0, epsilon=e, scope=scope, basis=basis, **state
            ).items()
            if k not in ("registrant_multiple", "within_corridor")
        }
        for e in points
    ]


def corridor_is_usable(
    registrant_multiple: float | None = None,
    multiple_error_factor: float | None = None,
    scope: str = "core",
    basis: str = "per_registered",
    points: tuple[float, ...] = ARC_REPORTING_POINTS,
    **state: Any,
) -> dict:
    """
    Is the corridor CLOSED as a usable band, or still a set of open edges?

    units: none — this returns three met/unmet conditions and a verdict.

    **WHY THIS IS A FUNCTION AND NOT A PARAGRAPH.** "Usable" is the kind of word
    that gets asserted beside evidence rather than computed from it. Three
    conditions have to hold, each of which the code can check:

      1. **MEASURED, not transferred.** `registrant_multiple` has a value
         measured for a HOURS-like register — the Standard Cost Model's `time`
         term, hours per fulfilment record — rather than one carried across from
         an adversarial money-denominated case. Nothing here measures it, so
         this is supplied or it is unmet.
      2. **BOUNDED BY INDEPENDENT INSTRUMENTS.** The band's edges come from at
         least two instruments that do not share a mechanism. Three do:
         ratio-to-obligation (institutional), clearing (labour supply), and the
         physical labour ceiling. This one is MET and is the reason the corridor
         exists at all.
      3. **THE DECLARED VALUE SITS INSIDE WITH MARGIN.** The multiple, widened
         by its own error factor, is still below the binding bound at every ε
         reported. A value inside the band but with an error bar wider than its
         margin has not been shown to be inside it.

    All three must hold. **Today condition 1 is unmet, so 3 is undeterminable
    and the verdict is `open_edges` — which is the honest state, computed.**

    This is also where the verdict ladder bites: the corridor's edges are
    arithmetic on measured censuses, so they are statable; the multiple is
    unmeasured, so anything resting on it is `possible` and no better.

    Args:
        registrant_multiple: a MEASURED multiple, if one exists. None means
            condition 1 is unmet, which is the shipped state.
        multiple_error_factor: the multiplicative error bar on it (e.g. 7.7 for
            the tax-compliance figure). Required for condition 3.
    """
    rows = which_binds_across_the_arc(scope=scope, basis=basis,
                                      points=points, **state)
    tightest = min(rows, key=lambda r: r["binding_multiple"])

    instruments = ("ratio_bound", "clearing_bound", "physical_bound")
    independent = sum(1 for b in instruments if tightest[b] is not None)

    measured = registrant_multiple is not None
    bounded = independent >= 2

    inside: bool | None
    if registrant_multiple is None or multiple_error_factor is None:
        inside = None
    else:
        # WIDEN BEFORE COMPARING. A value inside the band whose error bar is
        # wider than its margin has not been shown to be inside it.
        widened = registrant_multiple * multiple_error_factor
        inside = widened < tightest["binding_multiple"]

    conditions = {
        "1_multiple_is_measured": measured,
        "2_bounded_by_independent_instruments": bounded,
        "3_declared_value_sits_inside_with_margin": inside,
    }
    closed = all(v is True for v in conditions.values())

    return {
        "scope":            scope,
        "basis":            basis,
        "conditions":       conditions,
        "independent_instruments": independent,
        "tightest_bound":   tightest["binding_multiple"],
        "tightest_at_epsilon": tightest["epsilon"],
        "binding_bound":    tightest["binding_bound"],
        "verdict":          "closed_and_usable" if closed else "open_edges",
        "what_would_close_it": (
            "A measured registrant multiple — the Standard Cost Model's `time` "
            "term, hours per fulfilment record, from any institution running a "
            "fulfilment register at scale. Condition 2 is already met (three "
            "independent instruments bound the band); 3 cannot be evaluated "
            "until 1 is."
            if not measured else
            "Nothing — all three conditions hold."
            if closed else
            "The declared multiple, widened by its own error bar, exceeds the "
            "binding bound. Either the error bar must narrow or the "
            "configuration must change."
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

    # THE PEAK IS SEARCHED ON ITS OWN GRID, NOT READ OFF THE REPORTING POINTS.
    # `per_registered` turns where registered EOH peaks, and that turning point
    # (ε≈0.76 on the shipped configuration) falls BETWEEN the 0.40 and 0.90
    # reporting points. Taking `max` over the four-point arc understated the
    # peak by ~18% and published it as "the peak" — this module's own
    # `verification_arc` docstring names that trap and this function walked
    # into it. `PEAK_SEARCH_POINTS` is a numerics-only grid: making it finer
    # must not move a reported result by more than the grid spacing.
    peak_state = {k: v for k, v in state.items() if k != "points"}
    peak_rows = [
        row
        for b in ("per_capita", "per_registered")
        for row in verification_arc(scope=scope, basis=b,
                                    points=PEAK_SEARCH_POINTS, **peak_state)
    ]
    worst_row = max(peak_rows,
                    key=lambda r: r["verification_over_obligation"],
                    default=None)
    worst = worst_row["verification_over_obligation"] if worst_row else 0.0
    worst_epsilon = worst_row["epsilon"] if worst_row else None
    worst_basis = worst_row["basis"] if worst_row else None

    # The multiple at which the APPARATUS figure, scaled for a registrant side,
    # would cross. Solved from the peak rather than restated: combined =
    # peak x (1 + m) >= 1, so m >= 1/peak - 1. Reported so the verdict below
    # cannot be read as a statement about verification cost when it is a
    # statement about the apparatus.
    crossing_multiple = (1.0 / worst - 1.0) if worst > 0.0 else None

    if reachable:
        verdict = (
            "the audit advantage does not hold across the whole arc under "
            + " and ".join(reachable)
            + "; see §7 of the anchor comparison"
        )
    else:
        verdict = (
            "THE APPARATUS stays below the obligation it verifies everywhere "
            "on the arc under both bases, peaking at "
            f"{worst:.2%} of it at ε={worst_epsilon:.3f} on the "
            f"{worst_basis} basis — a point the four reporting points do not "
            "contain"
        )

    return {
        "scope":             scope,
        "rate_per_capita":   verification_hours_per_capita(scope),
        "us_census":         verification_hours_us(scope),
        "arc":               arcs,
        "crossover":         crossings,
        "peak_share_of_obligation": worst,
        "peak_epsilon":      worst_epsilon,
        "peak_basis":        worst_basis,
        "reporting_point_max": max(
            (row["verification_over_obligation"]
             for rows in arcs.values() for row in rows),
            default=0.0,
        ),
        "basis_unsettled":   which_basis_is_unsettled(),
        "scope_is_apparatus_only": (
            "core and broad both count people whose JOB is to verify. The "
            "registrant's own documentation hour is nobody's occupation and no "
            "occupational census reaches it. Call "
            "`registrant_scope_sensitivity(multiple)` to ask what the answer "
            "becomes if it is added - it takes the multiple as a required "
            "argument because there is no measurement of it here."
        ),
        "direction_of_error": direction_of_error(),
        "cannot_settle":     what_this_cannot_settle(),
        "apparatus_verdict": verdict,
        "verdict":           verdict,  # deprecated alias; prefer the scoped key
        "crossing_registrant_multiple": crossing_multiple,
        "scope_verdict": (
            "AND THIS DOES NOT ANSWER §7. The registrant's own documentation "
            "hour is nobody's occupation and no occupational census reaches "
            "it. At any registrant multiple of "
            f"{crossing_multiple:.1f}x or more this scope crosses — and the "
            "only measured registrant multiple, from an adversarial "
            "money-denominated case carrying its own 7.7x revision, is ~40x. "
            "Call `registrant_scope_sensitivity(multiple)`; it takes the "
            "multiple as required input because nothing here measures it."
        ) if crossing_multiple is not None else None,
        "adopted":           False,
    }
