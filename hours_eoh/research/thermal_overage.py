"""
Thermal Sink EOH — the OVERAGE: the power by which civilization exceeds its
radiative allowance, and what it would take to zero it.

This module reframes the thermal layer from headroom to debt, and the reframing
is what makes it useful. The budget formulation (research/thermal.py,
research/thermal_path_c.py) asks "how much dissipation does the allowance
permit?" — a permission. Permissions do not fit in an EOH generation function,
which is why the thermal layer has stayed advisory. The overage asks "by how
much are we over?" — an obligation, positive exactly when the framework has
something to say and zero when it does not.

    O(ΔT_max) = Φ + ( F_total − λ·ΔT_max ) · A_earth              [W]

Signed and unclipped: positive is overage, negative is slack. No max(0, …) is
needed, and the two terms are the two things civilization actually does — burn
(Φ) and force (F). What falls out is the measured claim the budget framing
could not state:

    at ΔT_max = 2.0 K the overage is ~510 TW, of which waste heat is 3.4%.
    Eliminating EVERY net-additive watt on Earth closes 3.4% of it.

Zeroing is reachable only through forcing. That is F3, restated as a debt
rather than a windfall, and unlike the F3 "gain" it does not degenerate: below
the budget-opening threshold — which is exactly the determinate zone the
framework calls honest (handoff 2.0 §4.2) — the gain saturates at (1−r)·λ·ΔT·A
and the forcing drops out of it entirely, so it reports the chosen threshold
rather than the carbon. The overage stays a function of F everywhere.

WHY EQUILIBRIUM (handoff 2.0 §10.3). λ·ΔT is the forcing that yields ΔT *at
steady state*, and present forcing has already committed 2.805 K against 1.23 K
delivered. Keeping the equilibrium frame is what makes the overage a STOCK to be
drawn down rather than a FLOW to be slowed: it counts warming already bought and
not yet delivered. A transient framing would hide ~964 TW of it. This is the same
logic that makes carbon budgets cumulative, and it is a deliberate choice, not
an artifact — see `pipeline_delta_t` on every report.

BASIS (handoff 2.0 §10.1). The overage uses TOTAL ERF per C4 — natural forcing
consumes habitability regardless of cause. The REACHABLE target is bounded by
anthropogenic ERF, because 0.262 W·m⁻² of natural forcing is a floor labor
cannot go below. The two bases do different jobs here rather than competing,
which is the argument for splitting them.

ADVISORY ONLY. Nothing here generates EOH or mints TEH. Converting O to
obligation needs ι_drawdown (J per EOH of removal labor) and must clear the
fiscal solvency gate first — the overage could swamp the ecological domain,
whose baseline is ~610K h/yr at population 1M, and ecological allocation is a
co-equal Trust obligation. Gate before wiring.

OPEN — the κ feedback, and it is F8. Drawdown powered at κ > 0 adds to Φ while
the forcing falls. Rough arithmetic puts the removal energy for the 2 K case at
the same order as the overage it closes, so a fossil- or nuclear-powered
drawdown may not converge. Because the energy is transient and the forcing
reduction permanent this is not a fixed point but a PATH question: does the
program's own thermal load breach the threshold during the program? That is F8
("steerable by τ yet unable to steer — the maneuver breaches the wall"), made
concrete. Needs the multi-period engine (P5); not modelled here.

Layer: research/ — experimental, unstable API, not imported by core/ or
scenarios/. Reuses the measured Φ from research/thermal_path_c.py.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.data import (
    A_EARTH_M2,
    THERMAL_LAMBDA_FEEDBACK,
    THERMAL_COMMONS_RESERVE,
    THERMAL_F_NET_ERF,
    THERMAL_F_ANTHRO_ERF,
    THERMAL_F_NATURAL_ERF,
    THERMAL_GMST_OBSERVED,
    THERMAL_EPS_CURRENT,
)
from hours_eoh.research.thermal_path_c import world_dissipation


class ThermalOverage(TypedDict):
    delta_t_max: float          # assessed habitability threshold (K, GMST)
    overage_w: float            # O — signed; positive is overage, negative slack
    forcing_term_w: float       # (F_total − λ·ΔT_max) · A_earth
    heat_term_w: float          # Φ — net-additive dissipation
    heat_share: float | None    # heat_term / overage; None when there is no overage
    is_overage: bool
    committed_delta_t: float    # F_total / λ — warming already bought
    observed_delta_t: float     # measured GMST anomaly
    pipeline_delta_t: float     # committed − observed: bought, not yet delivered


class ZeroingRequirement(TypedDict):
    delta_t_max: float
    forcing_required: float          # F at which O = 0 (W·m⁻²)
    reduction_required: float        # F_total − F_required (W·m⁻²)
    removable_forcing: float         # anthropogenic ERF — the ceiling on reduction
    share_of_removable: float        # reduction / removable
    feasible: bool                   # is the reduction within the removable forcing?
    feasibility_floor_k: float       # lowest ΔT_max reachable even at zero anthro forcing


def phi_at_epsilon(
    epsilon: float,
    phi_reference: float | None = None,
    eps_reference: float = THERMAL_EPS_CURRENT,
) -> float:
    """
    Φ(ε) — net-additive dissipation at automation level ε (W).

        Φ(ε) = Φ_measured · ( ε / ε_reference )

    A LINEAR EXTRAPOLATION holding ι and EOH_total fixed — the same caveat that
    governs Eq. C1. Falling ι makes this an over-estimate; rising EOH_total makes
    it an under-estimate. It is not a prediction; it is the ε-axis the overage
    needs in order to be arc-testable.

    Inherits the §10.2 problem: `eps_reference` is a CHOSEN Tier D constant
    (0.40 = arc midpoint), so Φ(ε) is proportional to a number nobody measured.
    Where a result can be stated as a ratio, prefer the ratio.

    units: watts. ε-behavior: Φ(0) = 0 (no automation, no machine dissipation);
    rises linearly; finite and well-defined at ε → 1.

    Worked example: ε = 0.40, Φ_measured = 17.71 TW → Φ = 17.71 TW (the
    reference point). ε = 0.99 → 43.8 TW.

    Args:
        epsilon: automation level ∈ [0, 1].
        phi_reference: measured Φ (W); defaults to the shipped world mix.
        eps_reference: the ε at which phi_reference was measured.

    Returns:
        Φ(ε) in watts.

    Raises:
        ValueError: if eps_reference is not positive.
    """
    if eps_reference <= 0.0:
        raise ValueError(f"eps_reference must be positive, got {eps_reference}")
    phi = world_dissipation() if phi_reference is None else phi_reference
    return phi * (epsilon / eps_reference)


def thermal_overage(
    delta_t_max: float,
    phi_w: float | None = None,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_total: float = THERMAL_F_NET_ERF,
    a_earth: float = A_EARTH_M2,
    observed_delta_t: float = THERMAL_GMST_OBSERVED,
) -> ThermalOverage:
    """
    O — the power by which civilization exceeds its radiative allowance (W).

        O(ΔT_max) = Φ + ( F_total − λ·ΔT_max ) · A_earth

    Positive is overage, negative is slack. The decomposition is the point: the
    forcing term and the heat term are separately reported because they are
    closed by different labor (drawdown vs efficiency) and because their ratio
    is the finding — at defensible thresholds the heat term is 2–4%.

    Every report carries the pipeline (committed − observed) so the equilibrium
    frame is visible at the point of use: the overage includes warming already
    bought and not yet delivered, which is precisely what a transient framing
    would let you spend.

    units: watts (ΔT in K, F in W·m⁻², λ in W·m⁻²·K⁻¹).
    ε-behavior: enters only through Φ; use phi_at_epsilon(ε). At ε = 0 the
    overage is pure forcing. No discontinuity anywhere on the arc — there is no
    clipping and no division by a quantity that vanishes.

    Worked example (ΔT_max = 2.0 K, Φ = 17.47 TW, λ = 1.2, F = 3.366):
        forcing term = (3.366 − 2.400) · 5.101e14 = 493 TW
        heat term    = 17.47 TW
        O            = 510 TW, of which heat is 3.4%
    Eliminating all net-additive dissipation closes 3.4% of the overage.

    Args:
        delta_t_max: assessed habitability threshold (K, GMST basis — convert
            from land TXx by dividing by THERMAL_TXX_PER_GMST, per C6).
        phi_w: net-additive dissipation (W); defaults to the measured world Φ.
        lam: climate feedback parameter (W·m⁻²·K⁻¹). Tier C — the budget spans
            6.5× across its plausible range (§10.4); pair it with the frame.
        f_total: total ERF (W·m⁻²) — total, not anthropogenic, per C4.
        a_earth: Earth surface area (m²).
        observed_delta_t: measured GMST anomaly (K), for the pipeline term.

    Returns:
        ThermalOverage.
    """
    phi = world_dissipation() if phi_w is None else phi_w
    forcing_term = (f_total - lam * delta_t_max) * a_earth
    overage = phi + forcing_term
    committed = f_total / lam if lam > 0.0 else float("inf")
    return ThermalOverage(
        delta_t_max=delta_t_max,
        overage_w=overage,
        forcing_term_w=forcing_term,
        heat_term_w=phi,
        heat_share=(phi / overage if overage > 0.0 else None),
        is_overage=overage > 0.0,
        committed_delta_t=committed,
        observed_delta_t=observed_delta_t,
        pipeline_delta_t=committed - observed_delta_t,
    )


def forcing_required_for_zero(
    delta_t_max: float,
    phi_w: float | None = None,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_total: float = THERMAL_F_NET_ERF,
    f_removable: float = THERMAL_F_ANTHRO_ERF,
    f_natural: float = THERMAL_F_NATURAL_ERF,
    a_earth: float = A_EARTH_M2,
) -> ZeroingRequirement:
    """
    What forcing must fall to for the overage to close, and whether labor can
    get there.

        F_required = λ·ΔT_max − Φ/A_earth
        R          = F_total − F_required = ( F_total − λ·ΔT_max ) + Φ/A_earth

    R is the reduction the framework is asking for, in the units climate policy
    already uses. Feasibility is the check the gain formulation never had:
    natural forcing is a floor labor cannot go below, so

        feasible  ⟺  R ≤ F_removable  ⟺  ΔT_max ≥ ( F_natural + Φ/A_earth ) / λ

    and that floor is 0.247 K. Waste heat alone never exhausts the allowance at
    any defensible threshold — **the wall is carbon, not heat**, and there is
    always a decarbonization path to thermal zero.

    units: W·m⁻² for forcings, K for the floor. ε-behavior: through Φ only; the
    Φ/A_earth term is 0.034 W·m⁻² at present dissipation, so ε moves the answer
    by ~1% of the reduction at defensible thresholds.

    Worked example (ΔT_max = 2.0 K): F_required = 2.400 − 0.034 = 2.366, so
    R = 1.000 W·m⁻² — 32.2% of the removable 3.104. Feasible with margin.

    Args:
        delta_t_max: assessed habitability threshold (K, GMST).
        phi_w: net-additive dissipation (W); defaults to measured world Φ.
        lam: climate feedback parameter (W·m⁻²·K⁻¹).
        f_total: total ERF (W·m⁻²) — what must come down.
        f_removable: anthropogenic ERF (W·m⁻²) — the ceiling on reduction.
        f_natural: natural ERF (W·m⁻²) — the floor labor cannot cross.
        a_earth: Earth surface area (m²).

    Returns:
        ZeroingRequirement.
    """
    phi = world_dissipation() if phi_w is None else phi_w
    psi = phi / a_earth
    f_required = lam * delta_t_max - psi
    reduction = f_total - f_required
    floor_k = (f_natural + psi) / lam if lam > 0.0 else float("inf")
    return ZeroingRequirement(
        delta_t_max=delta_t_max,
        forcing_required=f_required,
        reduction_required=reduction,
        removable_forcing=f_removable,
        share_of_removable=reduction / f_removable if f_removable > 0.0 else float("inf"),
        feasible=reduction <= f_removable,
        feasibility_floor_k=floor_k,
    )


def post_decarbonization_ceiling(
    delta_t_max: float,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_natural: float = THERMAL_F_NATURAL_ERF,
    f_total: float = THERMAL_F_NET_ERF,
    r: float = THERMAL_COMMONS_RESERVE,
    a_earth: float = A_EARTH_M2,
    phi_reference: float | None = None,
    eps_reference: float = THERMAL_EPS_CURRENT,
) -> dict:
    """
    The automation ceiling once forcing has been drawn down to its natural floor
    — the sharpest available statement that the ε ceiling is carbon-determined.

        ε_max^post = (1 − r) · ( λ·ΔT_max − F_natural ) · A_earth / Φ(ε=1)

    compared against the pre-decarbonization ceiling at the same threshold. At
    ΔT_max = 2.0 K the pre-decarbonization budget is UNBUDGETED (no ceiling
    exists because there is no budget), while post-decarbonization ε_max ≈ 20
    allocated (≈25 gross). Heat becomes binding only at roughly 20–25× full
    automation at present intensity.

    This is F4 ("fusion relieves carbon not heat") with a number on "later", and
    the sequencing claim it licenses: carbon now, heat at ~20×.

    Both the allocated (reserve applied) and gross (r = 0) figures are returned,
    because the commons reserve is a governance holdback rather than physics and
    the two answer different questions.

    units: dimensionless ε. ε-behavior: Φ(ε=1) is the denominator, so the result
    is a multiple of full automation at present intensity — the C1 caveat
    (ι, EOH_total held fixed) applies in full.

    Args:
        delta_t_max: assessed habitability threshold (K, GMST).
        lam: climate feedback parameter (W·m⁻²·K⁻¹).
        f_natural: irreducible natural forcing (W·m⁻²).
        f_total: present total ERF (W·m⁻²), for the pre-decarbonization compare.
        r: commons reserve fraction.
        a_earth: Earth surface area (m²).
        phi_reference, eps_reference: the measured Φ and the ε it was measured at.

    Returns:
        dict with `epsilon_max_post_allocated`, `epsilon_max_post_gross`,
        `epsilon_max_pre_allocated` (None when unbudgeted), `budget_post_w`,
        `phi_at_epsilon_1_w`, and `carbon_determined` (True when the ceiling
        exists only after drawdown).
    """
    phi_e1 = phi_at_epsilon(1.0, phi_reference, eps_reference)
    budget_post = max(0.0, lam * delta_t_max - f_natural) * a_earth
    budget_pre = max(0.0, lam * delta_t_max - f_total) * a_earth
    pre = ((1.0 - r) * budget_pre / phi_e1) if budget_pre > 0.0 else None
    return {
        "delta_t_max": delta_t_max,
        "epsilon_max_post_allocated": (1.0 - r) * budget_post / phi_e1,
        "epsilon_max_post_gross": budget_post / phi_e1,
        "epsilon_max_pre_allocated": pre,
        "budget_post_w": budget_post,
        "phi_at_epsilon_1_w": phi_e1,
        "carbon_determined": budget_pre <= 0.0 < budget_post,
    }


def overage_arc(
    delta_t_values: tuple[float, ...] = (1.5, 1.75, 2.0, 2.17, 2.5, 2.805, 3.0),
    phi_w: float | None = None,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_total: float = THERMAL_F_NET_ERF,
) -> list[dict]:
    """
    The overage and its zeroing requirement swept across habitability thresholds
    — the table that replaces the F3 gain as the headline.

    ΔT_max dominates every thermal result and is the framework's own judgment
    (handoff 2.0 §9), so the sweep IS the report; a point value would hide the
    only input that matters. Rows pair O(ΔT) with the reduction needed to zero
    it, so the reader sees the debt and the price of clearing it together.

    units: watts and W·m⁻². Returns rows ordered as given.
    """
    rows: list[dict] = []
    for dt in delta_t_values:
        o = thermal_overage(dt, phi_w, lam, f_total)
        z = forcing_required_for_zero(dt, phi_w, lam, f_total)
        rows.append({**o, **{k: v for k, v in z.items() if k != "delta_t_max"}})
    return rows


def overage_epsilon_arc(
    delta_t_max: float,
    epsilons: tuple[float, ...] = (0.0, 0.40, 0.90, 0.99),
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_total: float = THERMAL_F_NET_ERF,
    phi_reference: float | None = None,
    eps_reference: float = THERMAL_EPS_CURRENT,
) -> list[ThermalOverage]:
    """
    The overage across the automation arc at a fixed habitability threshold.

    The heat term scales with ε while the forcing term does not, so this is the
    sweep that shows WHEN heat stops being a rounding error. At present
    intensity it never does before ε = 1: at ΔT_max = 2.0 K the heat share rises
    only from 0% (ε = 0) to ~8% (ε = 0.99). Automation is not what breaks the
    budget; carbon is.

    ε-behavior: the required arc coverage — meaningful and finite at ε ∈
    {0, 0.40, 0.90, 0.99} with no discontinuity.
    """
    return [
        thermal_overage(
            delta_t_max,
            phi_at_epsilon(e, phi_reference, eps_reference),
            lam,
            f_total,
        )
        for e in epsilons
    ]
