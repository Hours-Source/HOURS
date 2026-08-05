"""
Infrastructure-EOH statutory floor — the B+D design demonstrated.

This scenario builds the currency-free floor of infrastructure_eoh_breakdown()
from a physical condition census and proves the property that motivated the
redesign: the floor is INVARIANT to the maintenance doctrine, because a doctrine
is a set of accounting/ambition choices and the floor contains none.

The contrast is with the monetized `capital_stock_teh` path
(handoffs/Infrastructure): there, switching doctrine moved infrastructure EOH by
10.26× — and the flip-one-field decomposition showed 100% of that came from
money→hours conversion conventions and 0% from any physical knob. Here, switching
doctrine moves the floor by exactly 1.000×; the only thing that changes is the
explicitly-labelled `discretionary` term, which belongs in the fulfilment/fiscal
layer, not the physical generation floor.

Layer: scenarios/ imports core/ and data.py only. Pure — no I/O. The row-level
NBI ingest and the full doctrine dollar model stay in the handoff / utils.

ε-coherence: the floor is ε-invariant (physical); the breakdown is exercised at
ε ∈ {0, 0.40, 0.99} in the tests via the monitoring/deferred terms.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.eoh_generation import infrastructure_eoh_breakdown
from hours_eoh.data import (
    INFRA_TREATMENT_HOURS_GOOD,
    INFRA_TREATMENT_HOURS_FAIR,
    INFRA_TREATMENT_HOURS_POOR,
)

# Illustrative anchor: FHWA NBI Pennsylvania 2025 condition census (good/fair/poor
# bridge counts). Data only; the full inventory + verification live in the handoff.
PA_2025_BRIDGE_COUNTS: tuple[int, int, int] = (8019, 12482, 2813)


def census_from_condition_counts(
    good: float,
    fair: float,
    poor: float,
    hours_good: float = INFRA_TREATMENT_HOURS_GOOD,
    hours_fair: float = INFRA_TREATMENT_HOURS_FAIR,
    hours_poor: float = INFRA_TREATMENT_HOURS_POOR,
) -> list[dict]:
    """
    Build an asset census (for infrastructure_eoh_breakdown) from good/fair/poor
    counts and task-normative per-condition treatment hours.

    The per-condition hours are currency-free engineering figures (interval ×
    crew-hours); a real deployment replaces the defaults with a state DOT's
    maintenance-activity manual rates.
    """
    return [
        {"count": good, "hours_per_unit_year": hours_good},
        {"count": fair, "hours_per_unit_year": hours_fair},
        {"count": poor, "hours_per_unit_year": hours_poor},
    ]


def condition_census_floor(
    good: float,
    fair: float,
    poor: float,
    discretionary_eoh: float = 0.0,
    deferred_stock: float = 0.0,
    monitoring_capability: float | None = None,
    epsilon: float | None = None,
    assessment_id: str = "statutory",
) -> dict:
    """Breakdown for a good/fair/poor census — a thin, named wrapper over
    infrastructure_eoh_breakdown() with a census built from the counts."""
    census = census_from_condition_counts(good, fair, poor)
    return infrastructure_eoh_breakdown(
        asset_census=census,
        discretionary_eoh=discretionary_eoh,
        deferred_stock=deferred_stock,
        monitoring_capability=monitoring_capability,
        epsilon=epsilon,
        assessment_id=assessment_id,
    )


class DoctrineInvarianceResult(TypedDict):
    counts: tuple[float, float, float]
    floors: dict[str, float]        # statutory_floor per doctrine (all equal)
    totals: dict[str, float]        # total per doctrine (differ only by discretionary)
    floor_spread: float             # max/min statutory_floor — the finding: 1.000
    total_spread: float             # max/min total — moves only via labelled discretionary
    determinacy_restored: bool      # floor_spread == 1.0


def doctrine_floor_invariance(
    counts: tuple[float, float, float] = PA_2025_BRIDGE_COUNTS,
    doctrines: dict[str, float] | None = None,
) -> DoctrineInvarianceResult:
    """
    The gap-closing proof: hold the physical census fixed, vary the maintenance
    doctrine's discretionary ambition, and show the measured floor does not move.

    Args:
        counts: (good, fair, poor) asset counts — the shared physical state.
        doctrines: {label: discretionary_eoh}. Each doctrine differs ONLY in the
            ambition it layers above the floor. Defaults to two doctrines whose
            discretionary spend differs by 10× — the same regime that moved the
            monetized path 10×.

    Returns:
        DoctrineInvarianceResult. `floor_spread` is 1.000 by construction of the
        design: the floor is a physical census × task-normative hours, immune to
        the doctrine. `total_spread` reflects only the explicitly-labelled
        discretionary term, which the fiscal/fulfilment layer can accept or reject.
    """
    good, fair, poor = counts
    if doctrines is None:
        # Two doctrines differing only in discretionary ambition (10× apart).
        doctrines = {"preservation": 2_000_000.0, "worst_first": 200_000.0}

    floors: dict[str, float] = {}
    totals: dict[str, float] = {}
    for label, discretionary in doctrines.items():
        bd = condition_census_floor(
            good, fair, poor, discretionary_eoh=discretionary, assessment_id=label
        )
        floors[label] = bd["statutory_floor"]
        totals[label] = bd["total"]

    floor_vals = list(floors.values())
    total_vals = list(totals.values())
    floor_spread = max(floor_vals) / min(floor_vals) if min(floor_vals) > 0 else float("inf")
    total_spread = max(total_vals) / min(total_vals) if min(total_vals) > 0 else float("inf")

    return DoctrineInvarianceResult(
        counts=counts,
        floors=floors,
        totals=totals,
        floor_spread=floor_spread,
        total_spread=total_spread,
        determinacy_restored=abs(floor_spread - 1.0) < 1e-9,
    )


def epsilon_from_floor(machine_eoh: float, counts: tuple[float, float, float] = PA_2025_BRIDGE_COUNTS) -> float:
    """
    ε with the infrastructure denominator taken as the statutory floor (§5.4b).

    Because the floor is doctrine-invariant, ε is single-valued given an observed
    machine_eoh — the [0.04, 0.40] indeterminacy of the monetized denominator
    (handoffs/Infrastructure §4.3) collapses. This is the ε-observability fix in
    miniature; the full rewire of the fulfilment ε computation is sign-off-gated.
    """
    good, fair, poor = counts
    floor = condition_census_floor(good, fair, poor)["statutory_floor"]
    if floor <= 0.0:
        raise ValueError("statutory floor must be positive to form ε")
    return machine_eoh / floor
