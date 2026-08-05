"""
The stability corridor — success as a stable feasible band, not ε → 1.

Framework decision (2026-08-01, author sign-off): ε = 1 (full automation) is
demoted from *the* target to ASPIRATIONAL — the target to reach. Success is a
STABLE MEASURABLE CORRIDOR: a band of ε over which every invariant holds, with
positive width sustained over the horizon and the sufficiency floor met. A
collective stable at ε = 0.6 with a positive corridor is a success by this
framework's standard, not a failed run at ε = 1.

The corridor is the region where the framework's invariants hold simultaneously:

    corridor(c) = [ ε_suff , ε_max ]          feasible iff width ≥ 0
      ε_suff  survival floor (E22): the minimum automation needed to meet
              survival EOH given available human labor — the LOWER bound.
      ε_max   the tightest binding ceiling among the framework's invariants —
              contestability (χ ≥ 1), thermal (advisory today), and any other
              ceiling that plugs in (fiscal solvency, ecological). The UPPER bound.

Most of this is already computed — the dashboard checks Conditions I–IV, χ, and
solvency. This module UNIFIES those into an explicit band and adds the missing
lower bound (ε_suff) plus a stability-over-horizon test.

Readiness is honest: ε_suff and the contestability ceiling are computable now;
the thermal ceiling is INCONCLUSIVE at P0 (research/thermal.py) and enters as a
non-binding, advisory ceiling until measured ι (handoff §13.1 path C) lands.

Layer: research/ — composes research/thermal + research/contestability + core
inventory; experimental until the API stabilizes (same discipline as those two).
ε-coherence: the corridor scans ε across the arc; every reported edge lies in
[0, 0.99].
"""

from __future__ import annotations

from typing import Callable, TypedDict

from hours_eoh.data import CONTESTABILITY_CHI_CRIT
from hours_eoh.research.contestability import contestability_margin
from hours_eoh.research.thermal import provable_ceiling_bound

# Survival-critical EOH domains for ε_suff. Personal EOH is the biological
# survival floor (the sufficiency guarantee's basis); callers may widen this.
DEFAULT_SURVIVAL_DOMAINS: tuple[str, ...] = ("personal",)
_ARC = tuple(i / 100 for i in range(100))  # 0.00 … 0.99


# ---------------------------------------------------------------------------
# Lower bound — survival floor ε_suff (E22)
# ---------------------------------------------------------------------------

def survival_floor_epsilon(
    eoh_by_domain: dict[str, float],
    available_labor_eoh: float,
    survival_domains: tuple[str, ...] = DEFAULT_SURVIVAL_DOMAINS,
) -> float:
    """
    E22 — the survival floor ε_suff: the minimum machine-fulfillment share needed
    to cover survival EOH beyond what available human labor can do.

    Governing equation:
        ε_suff = max(0, [ EOH_surv − L_avail ] / EOH_total)

    EOH_surv is the survival-critical EOH (the `survival_domains` subset of the
    breakdown — personal EOH by default, the biological necessity floor). If human
    labor alone covers survival (L_avail ≥ EOH_surv), ε_suff = 0: no automation is
    required to survive. When survival demand outruns human labor, the shortfall
    must be machine-fulfilled, and ε_suff is that shortfall as a fraction of total
    EOH — the LOWER edge of the corridor.

    units: dimensionless ∈ [0, 1]. ε-behavior: ε_suff is a level quantity computed
    from an EOH inventory; it does not itself depend on the operating ε.

    Args:
        eoh_by_domain: per-domain EOH (hours/year), e.g. from total_eoh().
        available_labor_eoh: human labor capacity in EOH-hours/year (L_avail),
            e.g. workforce_size × reference work-year hours.
        survival_domains: which domains count as survival-critical.

    Returns:
        ε_suff ∈ [0, 1].

    Raises:
        ValueError: if total EOH is non-positive or available_labor_eoh < 0.

    Reference: handoffs/Thermal_Sink_EOH_Implementation_Handoff §5.5 E22.
    """
    if available_labor_eoh < 0.0:
        raise ValueError(f"available_labor_eoh must be ≥ 0, got {available_labor_eoh}")
    eoh_total = sum(v for k, v in eoh_by_domain.items()
                    if k in ("personal", "infrastructure", "ecological", "knowledge"))
    if eoh_total <= 0.0:
        raise ValueError("total generating EOH must be positive")
    eoh_surv = sum(eoh_by_domain.get(d, 0.0) for d in survival_domains)
    shortfall = eoh_surv - available_labor_eoh
    return min(1.0, max(0.0, shortfall / eoh_total))


# ---------------------------------------------------------------------------
# Ceilings — upper-bound invariants
# ---------------------------------------------------------------------------

class Ceiling(TypedDict):
    name: str
    epsilon_ceiling: float | None   # ε at/above which the invariant breaks; None = non-binding on the arc
    binding: bool                   # does it constrain within [0, 0.99]?
    status: str                     # human-readable ("holds to ε=0.99", "χ<1 at ε≥0.72", "INCONCLUSIVE")


def contestability_ceiling(
    population: float,
    trust_balance: float,
    regime: str = "increasing_returns",
    arc: tuple[float, ...] = _ARC,
) -> Ceiling:
    """
    The contestability ceiling: the lowest ε at which χ falls below the critical
    margin (exit stops being substantive). χ is monotone-decreasing in ε, so the
    first crossing is the ceiling. Non-binding when χ stays ≥ 1 across the arc.
    """
    ceiling: float | None = None
    for eps in arc:
        chi = contestability_margin(eps, population, trust_balance, regime=regime)["chi"]
        if chi < CONTESTABILITY_CHI_CRIT:
            ceiling = eps
            break
    if ceiling is None:
        return Ceiling(name="contestability", epsilon_ceiling=None, binding=False,
                       status=f"χ ≥ {CONTESTABILITY_CHI_CRIT:g} across the arc")
    return Ceiling(name="contestability", epsilon_ceiling=ceiling, binding=True,
                   status=f"χ < {CONTESTABILITY_CHI_CRIT:g} at ε ≥ {ceiling:.2f}")


def thermal_ceiling(
    a_eff_collective: float,
    phi_other: float,
    epsilon: float = 0.40,
    **bound_kwargs: float,
) -> Ceiling:
    """
    The P0 thermal ceiling (research/thermal.py, thermodynamic-floor bound). At P0
    the floor-based bound is INCONCLUSIVE (ε_max ≫ 1) or UNBUDGETED — advisory,
    non-binding. SUPERSEDED for real use by measured_thermal_ceiling() (Path C):
    the measured signal is at the collective level (utilization U), not the global
    floor bound. Retained for the P0 story and as a regression anchor.
    """
    rep = provable_ceiling_bound(a_eff_collective, phi_other=phi_other,
                                 epsilon=epsilon, **bound_kwargs)  # type: ignore[arg-type]
    bound = rep["epsilon_max_bound"]
    if rep["verdict"] == "UNBUDGETED":
        return Ceiling(name="thermal", epsilon_ceiling=None, binding=False,
                       status="UNBUDGETED (advisory; GHG-forcing driven, not automation)")
    if rep["conclusive"] and bound is not None and bound < 1.0:
        return Ceiling(name="thermal", epsilon_ceiling=bound, binding=True,
                       status=f"thermodynamic ceiling ε_max ≤ {bound:.3f}")
    return Ceiling(name="thermal", epsilon_ceiling=None, binding=False,
                   status="INCONCLUSIVE from floors (needs measured ι, path C)")


def measured_thermal_ceiling(
    utilization: float,
    epsilon_current: float = 0.40,
    u_floor: float = 0.50,
) -> Ceiling:
    """
    The MEASURED thermal ceiling (Path C, finding F11). The binding thermal signal
    is a collective's utilization U = ψ/ψ* — its measured dissipation density
    against the allocated budget — not the (non-binding) global ε_max.

    A collective already in Contact (U ≥ 1) is over the thermal budget at its
    CURRENT automation, so there is no thermal headroom above ε_current: the
    ceiling binds at ε_current itself. Standing exposure (U ≥ u_floor) is flagged
    advisory (the budget is being approached but not breached). Below the floor,
    non-binding.

    Feed `utilization` from research.thermal_path_c.collective_utilization(...)
    ["utilization"]. This is the measured instrument the corridor was waiting on —
    it makes "Singapore is in Contact now" a real corridor bound, and it is
    collective-level by construction (the global aggregate sits at U ≈ 0.05 and is
    uninformative).

    Args:
        utilization: U = ψ/ψ* for the collective (Path C).
        epsilon_current: the collective's current automation level.
        u_floor: Standing-exposure boundary.

    Returns:
        Ceiling. Binding (at ε_current) iff U ≥ 1.
    """
    if utilization >= 1.0:
        return Ceiling(
            name="thermal_measured", epsilon_ceiling=epsilon_current, binding=True,
            status=f"CONTACT now: U={utilization:.2f} ≥ 1 — over budget at current ε "
                   f"(no thermal headroom to automate further)",
        )
    if utilization >= u_floor:
        return Ceiling(
            name="thermal_measured", epsilon_ceiling=None, binding=False,
            status=f"standing exposure: U={utilization:.2f} (advisory; budget approached)",
        )
    return Ceiling(
        name="thermal_measured", epsilon_ceiling=None, binding=False,
        status=f"below U_floor: U={utilization:.2f} (thermal non-binding)",
    )


# ---------------------------------------------------------------------------
# The corridor
# ---------------------------------------------------------------------------

class CorridorReport(TypedDict):
    epsilon_suff: float               # lower bound (survival floor)
    epsilon_max: float                # upper bound (tightest binding ceiling, or 1.0 aspirational)
    width: float                      # ε_max − ε_suff
    feasible: bool                    # width ≥ 0
    binding_ceiling: str | None       # which ceiling sets ε_max; None = no binding ceiling (aspirational)
    sufficiency_met: bool             # is ε_suff itself reachable (< 1)?
    success: bool                     # feasible AND sufficiency met — the reframed success flag
    ceilings: list[Ceiling]
    note: str


def corridor(
    epsilon_suff: float,
    ceilings: list[Ceiling],
) -> CorridorReport:
    """
    Compose the survival floor and the invariant ceilings into a feasible band.

    ε_max is the tightest binding ceiling; if none binds within the arc, ε_max is
    1.0 and the band is open to the aspirational target (with thermal noted as
    advisory, not proven-open). The corridor is feasible when width ≥ 0.

    SUCCESS is defined here without reference to ε = 1: a corridor is a success
    when it is feasible (positive width) and the sufficiency floor is reachable
    (ε_suff < 1). Reaching ε = 1 is aspirational, not the success criterion.

    Args:
        epsilon_suff: the survival floor (from survival_floor_epsilon()).
        ceilings: the upper-bound invariants (contestability, thermal, …).

    Returns:
        CorridorReport.
    """
    binding = [c for c in ceilings if c["binding"] and c["epsilon_ceiling"] is not None]
    if binding:
        tightest = min(binding, key=lambda c: c["epsilon_ceiling"])  # type: ignore[arg-type,return-value]
        eps_max = float(tightest["epsilon_ceiling"])  # type: ignore[arg-type]
        binding_name: str | None = tightest["name"]
    else:
        eps_max = 1.0
        binding_name = None

    width = eps_max - epsilon_suff
    feasible = width >= 0.0
    sufficiency_met = epsilon_suff < 1.0
    success = feasible and sufficiency_met

    if not feasible:
        note = ("corridor closed: the survival floor exceeds the tightest ceiling — "
                "no ε meets survival without breaching an invariant")
    elif binding_name is None:
        note = ("open corridor: no invariant binds within the arc; ε_max is "
                "aspirational (thermal advisory — not proven open, needs measured ι)")
    else:
        note = f"corridor [{epsilon_suff:.2f}, {eps_max:.2f}] bounded above by {binding_name}"

    return CorridorReport(
        epsilon_suff=epsilon_suff,
        epsilon_max=eps_max,
        width=width,
        feasible=feasible,
        binding_ceiling=binding_name,
        sufficiency_met=sufficiency_met,
        success=success,
        ceilings=ceilings,
        note=note,
    )


# ---------------------------------------------------------------------------
# Stability over the horizon
# ---------------------------------------------------------------------------

class StabilityReport(TypedDict):
    n_periods: int
    min_width: float
    all_feasible: bool
    all_success: bool
    verdict: str          # "STABLE" | "NARROWING" | "BREACHED"
    width_series: list[float]


def corridor_stability(series: list[CorridorReport]) -> StabilityReport:
    """
    Assess whether a corridor is STABLE over a horizon — the operational meaning
    of "a stable corridor is its own success."

    - BREACHED: any period is infeasible (width < 0) — an invariant was violated.
    - NARROWING: feasible throughout but the band is shrinking toward closure
      (last-period width below half the first-period width, and strictly falling).
    - STABLE: feasible throughout and not narrowing to closure.

    Args:
        series: per-period CorridorReports (e.g. from a multi-period simulation).

    Returns:
        StabilityReport.

    Raises:
        ValueError: if series is empty.
    """
    if not series:
        raise ValueError("corridor_stability needs at least one period")
    widths = [c["width"] for c in series]
    all_feasible = all(c["feasible"] for c in series)
    all_success = all(c["success"] for c in series)
    min_width = min(widths)

    if not all_feasible:
        verdict = "BREACHED"
    elif len(widths) >= 2 and widths[-1] < 0.5 * widths[0] and widths[-1] < widths[0]:
        verdict = "NARROWING"
    else:
        verdict = "STABLE"

    return StabilityReport(
        n_periods=len(series),
        min_width=min_width,
        all_feasible=all_feasible,
        all_success=all_success,
        verdict=verdict,
        width_series=widths,
    )
