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
              contestability (exit financeable, §8.9), thermal (advisory today),
              and any other ceiling that plugs in (fiscal solvency, ecological).
              The UPPER bound.

Most of this is already computed — the dashboard checks Conditions I–IV, χ, and
solvency. This module UNIFIES those into an explicit band and adds the missing
lower bound (ε_suff) plus a stability-over-horizon test.

Readiness is honest: ε_suff and the contestability ceiling are computable now;
the thermal ceiling is INCONCLUSIVE at P0 (research/thermal.py) and enters as a
non-binding, advisory ceiling until measured ι (handoff §13.1 path C) lands.

CONTESTABILITY AXIS MIGRATION (2026-08-05). This module previously took its
contestability ceiling from the bare margin χ = P/K_entry, which §8.9 had
already superseded — so the recorded "corridor CLOSED at defaults" finding was
produced by a retired invariant. `contestability_ceiling()` now runs the adopted
three-channel financeability test; the bare-χ form survives, explicitly labelled,
as `contestability_ceiling_bare_chi()`. At defaults the two DISAGREE (bare-χ
binds at ε ≈ 0.24, the adopted test does not bind at all), and
`contestability_axes()` exists to report that disagreement rather than bury it.
The closed-corridor result stands only as a statement about the stricter test.

Layer: research/ — composes research/thermal + research/contestability + core
inventory; experimental until the API stabilizes (same discipline as those two).
ε-coherence: the corridor scans ε across the arc; every reported edge lies in
[0, 0.99].
"""

from __future__ import annotations

from typing import Callable, TypedDict

from hours_eoh.data import CONTESTABILITY_CHI_CRIT, THERMAL_U_FLOOR
from hours_eoh.research.contestability import contestability_margin
from hours_eoh.research.recalibration import exit_financing
from hours_eoh.research.thermal import provable_ceiling_bound

# Survival-critical EOH domains for ε_suff. Personal EOH is the biological
# survival floor (the sufficiency guarantee's basis); callers may widen this.
DEFAULT_SURVIVAL_DOMAINS: tuple[str, ...] = ("personal",)
_ARC = tuple(i / 100 for i in range(100))  # 0.00 … 0.99


# ---------------------------------------------------------------------------
# Lower bound — survival floor ε_suff (E22)
# ---------------------------------------------------------------------------

def survival_inventory(
    population: float = 1_000_000.0,
    **kwargs: float,
) -> dict[str, float]:
    """
    An EOH inventory taken at the SURVIVAL standard — the correct input to
    `survival_floor_epsilon`.

    Why this exists (2026-08-06). ε_suff was being computed from an inventory at
    the *operating* personal standard, which is a sufficiency-shaped number. That
    is a category error: it asks "how much automation is needed before nobody
    goes without a decent life", and then reports the answer as a survival floor.
    Run at the survival standard (S_a = 600 per working-age-equivalent) the floor
    is ε_suff = 0 — subsistence survives with no automation, which is what the
    historical record shows.

    The corrected reading of the two numbers together: **subsistence can survive
    but cannot reach sufficiency without automation.** The gap between them is
    what a collective exists to close, not evidence that the model is broken.

    units: hours/year per domain.
    ε-behavior: pass `epsilon=` through kwargs for the canonical inventory at
    that ε; the survival standard itself is ε-invariant.

    Args:
        population: Total population.
        **kwargs: Forwarded to `core.eoh_generation.total_eoh` (epsilon,
            capital_stock, ecosystem_health, …). `personal_standard` is set here
            and must not be passed.

    Returns:
        The `total_eoh` dict with personal taken at the survival standard.

    Raises:
        TypeError: if `personal_standard` is supplied by the caller.
    """
    if "personal_standard" in kwargs:
        raise TypeError(
            "survival_inventory sets personal_standard='survival'; do not pass it"
        )
    from hours_eoh.core.eoh_generation import total_eoh
    return total_eoh(population=population, personal_standard="survival", **kwargs)  # type: ignore[arg-type]


def survival_floor_epsilon(
    eoh_by_domain: dict[str, float],
    available_labor_eoh: float,
    survival_domains: tuple[str, ...] = DEFAULT_SURVIVAL_DOMAINS,
) -> float:
    """
    E22 — the survival floor ε_suff: the minimum machine-fulfillment share needed
    to cover survival EOH beyond what available human labor can do.

    IMPORTANT — which inventory you pass decides what this measures. Build it
    with `survival_inventory()` so the personal domain is taken at the SURVIVAL
    standard. Passing an inventory at the operating (abatement-collapsed) or
    sufficiency standard makes this report a SUFFICIENCY floor under a survival
    name, which is the category error this signature note exists to prevent:

        survival standard   S_a = 600   →  ε_suff = 0.00   (subsistence survives)
        operating           1000        →  ε_suff = 0.31
        sufficiency         F_a = 1500  →  ε_suff = 0.53

    All three are meaningful; only the first is a survival floor.

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
    regime: str = "increasing_returns",
    phi_policy: str = "dilution",
    arc: tuple[float, ...] = _ARC,
) -> Ceiling:
    """
    The contestability ceiling on the ADOPTED §8.9 invariant: the lowest ε at
    which exit stops being financeable through any of the three channels.

    Governing condition (research/recalibration.exit_financing):

        exit_financeable(ε) ⇔ t_exit_self(ε) ≤ horizon  OR  entry_capacity(ε) ≥ 1

    where t_exit_self = max(t_labor, t_capital) is time-to-finance-exit and
    entry_capacity is the commons' underwriting capacity for a founding cohort.
    The ceiling is the first ε on the arc at which neither channel carries; if
    every ε is financeable the ceiling is non-binding.

    This REPLACES the bare-χ axis for corridor use. χ = P/K_entry demanded that
    one year of income cover the whole founding stock — a flow/stock mismatch
    (RC4) superseded by §8.9. The retired test is retained as
    `contestability_ceiling_bare_chi()`, which is strictly stricter; where the
    two disagree, that disagreement is a reportable fact and not a bug (see
    `contestability_axes()`).

    Note the signature difference from the bare-χ form, and it is substantive:
    there is no `trust_balance` argument. Under §8.9 the commons' capital stock
    is DERIVED from φ(ε)·K(ε) under the charter policy rather than supplied as a
    free parameter, so a thin-trust input can no longer be posed independently
    of the charter that would have produced it.

    units: dimensionless ε. ε-behavior: scans the whole arc [0, 0.99]; at
    defaults the channel arcs labor → underwritten → self and nothing binds.

    Args:
        population: Total population.
        regime: K_entry regime ("increasing_returns" adversarial default).
        phi_policy: Charter policy — "dilution" (default) | "target" | "escalated".
        arc: ε values to scan.

    Returns:
        Ceiling named "contestability".

    Worked example (defaults, adversarial regime): ε=0 finances by labor
    (t=1.8 yr), ε≈0.1–0.2 by commons underwriting, ε≥0.4 self-finances
    (t≈2.9 yr at ε=0.99) → non-binding across the arc.

    Reference: notes/contestability-closure-proposal.md §8.9, §8.9b.
    """
    for eps in arc:
        fin = exit_financing(eps, population=population, regime=regime,
                             phi_policy=phi_policy)
        if not fin["exit_financeable"]:
            return Ceiling(
                name="contestability", epsilon_ceiling=eps, binding=True,
                status=f"exit not financeable at ε ≥ {eps:.2f} "
                       f"(neither self-financing nor commons underwriting carries)",
            )
    return Ceiling(name="contestability", epsilon_ceiling=None, binding=False,
                   status="exit financeable across the arc (§8.9 three-channel test)")


def contestability_ceiling_bare_chi(
    population: float,
    trust_balance: float,
    regime: str = "increasing_returns",
    arc: tuple[float, ...] = _ARC,
) -> Ceiling:
    """
    SUPERSEDED (§8.9, 2026-07-26) — the bare-χ contestability ceiling, retained
    as the STRICTER adversarial test and as a regression anchor.

        χ(ε) = P(ε) / K_entry(ε) ,   ceiling = first ε with χ < CHI_CRIT

    Why it was retired: χ compares a per-year FLOW (the portable endowment P) to
    a one-time STOCK (the founding cost K_entry), so it demands that a single
    year's income cover an entire collective's founding capital. That is the RC4
    flow/stock defect; §8.9 replaced it with time-to-finance-exit plus an
    accumulating capital account.

    Why it is kept: it is a genuine upper-bound stress — a collective that
    passes bare-χ needs no underwriting and no vesting period at all. Read it as
    "exit is financeable from one year of income alone", not as the invariant.

    Do NOT use this as the corridor's contestability axis; use
    `contestability_ceiling()`. Callers wanting the comparison should use
    `contestability_axes()`, which reports both and flags disagreement.

    Args:
        population: Total population.
        trust_balance: Trust corpus (TEH) — a free parameter here, which is
            itself part of why the test was retired (§8.9 derives it from φ·K).
        regime: K_entry regime.
        arc: ε values to scan.

    Returns:
        Ceiling named "contestability_bare_chi".
    """
    ceiling: float | None = None
    for eps in arc:
        chi = contestability_margin(eps, population, trust_balance, regime=regime)["chi"]
        if chi < CONTESTABILITY_CHI_CRIT:
            ceiling = eps
            break
    if ceiling is None:
        return Ceiling(name="contestability_bare_chi", epsilon_ceiling=None, binding=False,
                       status=f"[SUPERSEDED axis] χ ≥ {CONTESTABILITY_CHI_CRIT:g} across the arc")
    return Ceiling(name="contestability_bare_chi", epsilon_ceiling=ceiling, binding=True,
                   status=f"[SUPERSEDED axis] χ < {CONTESTABILITY_CHI_CRIT:g} at ε ≥ {ceiling:.2f}")


class AxesComparison(TypedDict):
    adopted: Ceiling            # §8.9 three-channel financeability
    bare_chi: Ceiling           # retired flow/stock χ
    agree: bool                 # do both axes give the same binding verdict?
    note: str


def contestability_axes(
    population: float,
    trust_balance: float,
    regime: str = "increasing_returns",
    phi_policy: str = "dilution",
    arc: tuple[float, ...] = _ARC,
) -> AxesComparison:
    """
    Report BOTH contestability axes side by side and flag disagreement.

    This exists because the disagreement is itself the finding. Before this was
    wired, the corridor ran on the retired bare-χ axis and reported a closed
    corridor at defaults; on the adopted §8.9 axis nothing binds. Publishing one
    number without the other hides which invariant produced the verdict.

    Args:
        population: Total population.
        trust_balance: Trust corpus for the bare-χ arm only.
        regime: K_entry regime.
        phi_policy: Charter policy for the adopted arm.
        arc: ε values to scan.

    Returns:
        AxesComparison. `agree` is False whenever the two axes differ on whether
        contestability binds at all — the case that must be reported, not
        averaged.
    """
    adopted = contestability_ceiling(population, regime=regime,
                                     phi_policy=phi_policy, arc=arc)
    bare = contestability_ceiling_bare_chi(population, trust_balance,
                                           regime=regime, arc=arc)
    agree = adopted["binding"] == bare["binding"]
    if agree:
        note = "both axes agree on whether contestability binds"
    elif bare["binding"]:
        note = (f"AXES DISAGREE: the retired bare-χ test binds at "
                f"ε ≥ {bare['epsilon_ceiling']:.2f} while the adopted §8.9 "
                f"three-channel test does not bind. The adopted axis governs; "
                f"the bare-χ figure is the one-year-of-income stress, not the invariant.")
    else:
        note = ("AXES DISAGREE: the adopted §8.9 test binds where bare-χ does not — "
                "investigate, this direction is not expected (bare-χ is stricter).")
    return AxesComparison(adopted=adopted, bare_chi=bare, agree=agree, note=note)


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
    u_floor: float = THERMAL_U_FLOOR,
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

class Floor(TypedDict):
    name: str
    epsilon_floor: float    # ε at/below which this bound is violated
    binding: bool           # does it constrain within [0, 0.99]?
    status: str


def overbuild_floor(
    capital_stock_teh: float,
    population: float = 1_000_000.0,
    **kwargs: float,
) -> Floor:
    """
    The overbuild floor — the lowest ε at which the collective is worth being in.

    Below it the apparatus demands more hours of its members than autarky would
    (`(1−ε)·total(K) ≥ B₀`), and the collective should dissolve rather than
    operate. That makes it a genuine LOWER bound on the corridor, alongside the
    survival floor, and a second way a corridor can close: not "we cannot
    survive", but "we would be better off apart".

    Non-binding (floor 0.0) whenever the OBLIGATION test already passes — an
    apparatus that removes more obligation than it creates is worth being in at
    every ε, with nothing for automation to rescue.

    units: dimensionless ε.
    ε-behavior: the floor is a property of the apparatus, not of the operating ε;
    it is the ε that apparatus *requires*.

    Args:
        capital_stock_teh: Apparatus capital (TEH).
        population: Total population.
        **kwargs: Forwarded to core.autarky.overbuild_check.

    Returns:
        Floor named "overbuild".

    Reference: core/autarky.py; docs/parameter_provenance.md §"Abatement".
    """
    from hours_eoh.core.autarky import break_even_epsilon, overbuild_check
    e = break_even_epsilon(capital_stock_teh, population, **kwargs)
    check = overbuild_check(capital_stock_teh, population, epsilon=0.0, **kwargs)  # type: ignore[arg-type]
    if e <= 0.0:
        return Floor(name="overbuild", epsilon_floor=0.0, binding=False,
                     status=f"apparatus pays at any ε ({check['verdict']})")
    return Floor(name="overbuild", epsilon_floor=e, binding=True,
                 status=f"worth being in only at ε ≥ {e:.2f} — below it the "
                        f"apparatus costs members more hours than autarky")


def survival_floor(
    eoh_by_domain: dict[str, float],
    available_labor_eoh: float,
    survival_domains: tuple[str, ...] = DEFAULT_SURVIVAL_DOMAINS,
) -> Floor:
    """`survival_floor_epsilon` in Floor form, for composing with other bounds."""
    e = survival_floor_epsilon(eoh_by_domain, available_labor_eoh, survival_domains)
    if e <= 0.0:
        return Floor(name="survival", epsilon_floor=0.0, binding=False,
                     status="human labour covers survival at ε = 0")
    return Floor(name="survival", epsilon_floor=e, binding=True,
                 status=f"survival requires ε ≥ {e:.2f}")


class CorridorReport(TypedDict):
    epsilon_suff: float               # lower bound (the binding floor)
    binding_floor: str | None         # which floor sets it; None = nothing binds
    floors: list[Floor]
    epsilon_max: float                # upper bound (tightest binding ceiling, or 1.0 aspirational)
    width: float                      # ε_max − ε_suff
    feasible: bool                    # width ≥ 0
    binding_ceiling: str | None       # which ceiling sets ε_max; None = no binding ceiling (aspirational)
    sufficiency_met: bool             # is ε_suff itself reachable (< 1)?
    success: bool                     # feasible AND sufficiency met — the reframed success flag
    ceilings: list[Ceiling]
    note: str


def corridor(
    epsilon_suff: float | list[Floor],
    ceilings: list[Ceiling],
) -> CorridorReport:
    """
    Compose the lower bounds and the invariant ceilings into a feasible band.

    ε_max is the tightest binding ceiling; if none binds within the arc, ε_max is
    1.0 and the band is open to the aspirational target (with thermal noted as
    advisory, not proven-open). The corridor is feasible when width ≥ 0.

    SUCCESS is defined here without reference to ε = 1: a corridor is a success
    when it is feasible (positive width) and the sufficiency floor is reachable
    (ε_suff < 1). Reaching ε = 1 is aspirational, not the success criterion.

    TWO LOWER BOUNDS (Block III, 2026-08-06). The band's floor used to be the
    survival floor alone. It is now the MAX over every supplied floor, because a
    collective can be infeasible for two independent reasons:

        survival    ε_suff      below it the population cannot meet its
                                obligation at all
        overbuild   ε_breakeven below it the apparatus costs members more hours
                                than autarky would — they should disperse, not
                                because they would die but because the collective
                                is not worth being in

    Args:
        epsilon_suff: EITHER a bare float (the survival floor, backward
            compatible) OR a list of Floor. When a list, the binding floor is
            the largest and is named in the report.
        ceilings: the upper-bound invariants (contestability, thermal, …).

    Returns:
        CorridorReport.
    """
    if isinstance(epsilon_suff, (int, float)):
        floors: list[Floor] = [Floor(name="survival", epsilon_floor=float(epsilon_suff),
                                     binding=float(epsilon_suff) > 0.0,
                                     status="supplied as a scalar")]
    else:
        floors = list(epsilon_suff)
    binding_floors = [f for f in floors if f["binding"]]
    if binding_floors:
        tightest_floor = max(binding_floors, key=lambda f: f["epsilon_floor"])
        eps_floor = tightest_floor["epsilon_floor"]
        floor_name: str | None = tightest_floor["name"]
    else:
        eps_floor = 0.0
        floor_name = None
    epsilon_suff = eps_floor

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
        note = (f"corridor closed: the {floor_name or 'survival'} floor exceeds the "
                f"tightest ceiling — no ε satisfies both")
    elif binding_name is None:
        note = ("open corridor: no invariant binds within the arc; ε_max is "
                "aspirational (thermal advisory — not proven open, needs measured ι)")
    else:
        note = f"corridor [{epsilon_suff:.2f}, {eps_max:.2f}] bounded above by {binding_name}"

    return CorridorReport(
        epsilon_suff=epsilon_suff,
        binding_floor=floor_name,
        floors=floors,
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
