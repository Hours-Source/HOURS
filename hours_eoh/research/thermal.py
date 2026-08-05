"""
Thermal Sink EOH — P0: the decarbonization-headroom finding (F3), with the
provable ceiling bound (E29 / F1–F2) demoted to conditional.

The uncounted vector (handoffs/Thermal_Sink_EOH_Implementation_Handoff_1_0.md):
all degraded energy must exit through radiation to space; that capacity is fixed
and cannot be enlarged by labor. Machine fulfillment of entropy obligations costs
joules, so automation ε has a thermodynamic ceiling ε_max that may sit below 1.

P0 REORDER (2026-08-01, per the Path C first-pass, handoffs/path c §7 rec 2 & 5):
the measured run showed the thermodynamic-floor ceiling bound is NON-BINDING at
current dissipation, so F1/F2 are demoted to CONDITIONAL — true as specified, but
not a constraint today. The load-bearing P0 finding is instead:

    F3 — decarbonization headroom. Greenhouse forcing and waste heat draw on ONE
    unified budget (E6), so cutting forcing frees thermal budget for dissipation.
    Measured, this is ~1,374 TW ≈ 78× current world dissipation on the total-ERF
    basis (~1,267 TW ≈ 72× on the removable anthropogenic forcing — see
    research/thermal_path_c.decarbonization_headroom for why the basis is an open
    question). This is where the measured signal is, and it is computable from
    constants alone — so it is the primary P0 deliverable
    (`decarbonization_headroom`).

C5 (2026-08-03): forcing corrected from the AR6-2019 vintage 2.72 to IGCC-2025a
total 3.366 [2.602–4.102]. F1's old "binds at ~10–50× present dissipation" was
computed on the superseded constant and is withdrawn: post-correction the global
ceiling binds at 2.2× present dissipation at ΔT_lo = 3.0 K, rising to 13.4× at
4.0 K. The correction tightened every ceiling and enlarged F3.

Everything here is **advisory**: it computes bounds and reports them; it generates
NO obligation and mints NO TEH (the ledger identity is untouched). Obligation
generation (E13–E18) is a later phase, gated on the §10.2 robustness test.

The floor bound is retained (conditional). Its epistemics (handoff §13.1 path D):
it uses thermodynamic FLOORS ι_floor ≤ real ι, and larger ι gives a smaller ε_max,
so the floor-based value OVERSTATES ε_max. Therefore a floor bound < 1 would be
conclusive; at current dissipation it comes back ≥ 1 (INCONCLUSIVE), which the
measured Path C run confirms globally. The measured, binding thermal instrument is
collective utilization U (research/thermal_path_c.py, F11), not this global bound.

Layer: research/ — experimental, unstable API, not imported by core/ (the same
discipline as research/contestability.py). Graduates to core/thermal.py when the
API stabilizes and the ε-vector Mission Statement amendment (§12.1) is signed off.
ε-coherence: the bound is a LEVEL quantity (no growth rate); it is well-defined
and its degradation sentinels are exercised across ε ∈ {0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    A_EARTH_M2,
    SECONDS_PER_YEAR,
    THERMAL_LAMBDA_FEEDBACK,
    THERMAL_F_GHG,
    THERMAL_F_ALB,
    THERMAL_DT_LO,
    THERMAL_COMMONS_RESERVE,
    THERMAL_ANTHROPOGENIC_DISSIPATION_W,
    THERMAL_IOTA_FLOOR_PERSONAL,
    THERMAL_IOTA_FLOOR_INFRASTRUCTURE,
    THERMAL_IOTA_FLOOR_ECOLOGICAL,
    THERMAL_IOTA_FLOOR_KNOWLEDGE,
)

# Per-domain thermodynamic floors (J/EOH), keyed to total_eoh() domains.
IOTA_FLOOR_BY_DOMAIN: dict[str, float] = {
    "personal":       THERMAL_IOTA_FLOOR_PERSONAL,
    "infrastructure": THERMAL_IOTA_FLOOR_INFRASTRUCTURE,
    "ecological":     THERMAL_IOTA_FLOOR_ECOLOGICAL,
    "knowledge":      THERMAL_IOTA_FLOOR_KNOWLEDGE,
}
_EOH_DOMAINS = tuple(IOTA_FLOOR_BY_DOMAIN)

BoundVerdict = Literal["CONCLUSIVE_BELOW_1", "INCONCLUSIVE_ABOVE_1", "UNBUDGETED"]


# ---------------------------------------------------------------------------
# Budget chain — E6, E7, E8, E9
# ---------------------------------------------------------------------------

def residual_thermal_forcing(
    delta_t_lo: float = THERMAL_DT_LO,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
) -> float:
    """
    E6 — residual thermal forcing available for direct waste heat (W·m⁻²).

        F*_th = λ · ΔT_lo − F_GHG − F_alb

    The temperature allowance λ·ΔT_lo is shared by greenhouse, albedo, and direct
    thermal forcing (one budget, not two — handoff §2). What greenhouse and albedo
    already claim is subtracted; the residual is the direct-thermal headroom. May
    be negative (budget already exhausted by other forcing) — the caller floors it.

    This is the coupling behind F3: cutting F_GHG raises F*_th, so decarbonization
    RAISES the automation ceiling — restoration and liberation are one project.

    Args:
        delta_t_lo: assessed habitability threshold (K), low end of the range.
        lam: climate feedback parameter (W·m⁻²·K⁻¹).
        f_ghg, f_alb: greenhouse and albedo forcing already committed (W·m⁻²).

    Returns:
        Residual thermal forcing (W·m⁻²); may be negative.
    """
    return lam * delta_t_lo - f_ghg - f_alb


def planetary_budget(
    delta_t_lo: float = THERMAL_DT_LO,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
    a_earth: float = A_EARTH_M2,
) -> float:
    """
    E7 — planetary thermal budget (W), floored at 0.

        Φ*_planet = max(0, F*_th) · A_earth

    Zero means the temperature allowance is fully consumed by greenhouse/albedo
    forcing before any direct waste heat — the unbudgeted regime.
    """
    return max(0.0, residual_thermal_forcing(delta_t_lo, lam, f_ghg, f_alb)) * a_earth


def allocated_density(
    a_eff_total: float,
    r: float = THERMAL_COMMONS_RESERVE,
    delta_t_lo: float = THERMAL_DT_LO,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
    a_earth: float = A_EARTH_M2,
) -> float:
    """
    E8 — allocated dissipation density ψ* (W·m⁻²).

        ψ* = (1 − r) · Φ*_planet / A_eff,total

    r is the commons reserve held back from allocation. Zero when the budget is
    exhausted (Φ*_planet = 0). a_eff_total must be positive.
    """
    if a_eff_total <= 0.0:
        raise ValueError(f"a_eff_total must be positive, got {a_eff_total}")
    budget = planetary_budget(delta_t_lo, lam, f_ghg, f_alb, a_earth)
    return (1.0 - r) * budget / a_eff_total


# ---------------------------------------------------------------------------
# F3 — decarbonization headroom (the PRIMARY P0 finding)
# ---------------------------------------------------------------------------

class DecarbonizationHeadroom(TypedDict):
    delta_t_lo: float
    allocated_now_w: float           # thermal budget allocated at current forcing (W)
    allocated_zero_forcing_w: float  # budget at zero anthropogenic forcing (W)
    gain_w: float                    # budget decarbonization would return (W)
    binds_now: bool                  # is there any thermal budget at all today?


def decarbonization_headroom(
    delta_t_lo: float = THERMAL_DT_LO,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    r: float = THERMAL_COMMONS_RESERVE,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
    a_earth: float = A_EARTH_M2,
) -> DecarbonizationHeadroom:
    """
    F3 — the thermal budget decarbonization would return. THE primary P0 finding
    (reordered ahead of the floor bound per the Path C run — it is where the
    measured signal is, and it is computable from constants alone).

    The unified-budget structure (E6) puts greenhouse forcing and direct waste
    heat on ONE temperature allowance, so cutting forcing frees budget:

        gain = allocated(ΔT_lo, F=0) − allocated(ΔT_lo, F=f_ghg+f_alb)

    where allocated(F) = (1 − r) · max(0, λ·ΔT_lo − F) · A_earth. This makes
    ecological restoration (cutting F) and technological liberation (raising the
    automation ceiling) THE SAME PROJECT rather than rivals. Measured (Path C,
    net-ERF post-C5, ΔT_lo = 3.0 K): gain ≈ 1,374 TW ≈ 78× current world
    dissipation. The gain is (1 − r)·min(F, λ·ΔT_lo)·A_earth — LINEAR in the
    forcing assumed removable, which is why that basis is a live question (F3
    caveat in research/thermal_path_c.decarbonization_headroom), and saturating
    at F once ΔT_lo clears the budget-opening threshold.

    Note the finding survives even where there is no budget today: at a tight
    ΔT_lo the current allocation is 0 (GHG forcing has consumed the allowance),
    yet zero-forcing opens a large budget — `binds_now` is False but `gain_w` is
    large. That is the F3 point in its sharpest form.

    Advisory only. units: watts.

    Args:
        delta_t_lo: assessed habitability threshold (K).
        lam: climate feedback parameter (W·m⁻²·K⁻¹).
        r: commons reserve fraction.
        f_ghg, f_alb: current greenhouse and albedo forcing (W·m⁻²).
        a_earth: Earth surface area (m²).

    Returns:
        DecarbonizationHeadroom.

    Reference: handoffs §12.2/F3; handoffs/path c §4 (measured ~1000–1100 TW).
    """
    def alloc(forcing: float) -> float:
        f_th = lam * delta_t_lo - forcing
        return (1.0 - r) * max(0.0, f_th) * a_earth

    now = alloc(f_ghg + f_alb)
    zero = alloc(0.0)
    return DecarbonizationHeadroom(
        delta_t_lo=delta_t_lo,
        allocated_now_w=now,
        allocated_zero_forcing_w=zero,
        gain_w=zero - now,
        binds_now=now > 0.0,
    )


# ---------------------------------------------------------------------------
# Thermodynamic floor — E27
# ---------------------------------------------------------------------------

def iota_floor(domain: str) -> float:
    """
    E27 — thermodynamic floor ι_floor,d on the thermal intensity of automation
    (J per EOH fulfilled) for a domain.

    The minimum joules to fulfill one EOH by machine: Landauer for knowledge,
    Carnot/enthalpy minima for infrastructure, caloric + heat-rejection COP for
    personal. These are the gating uncertainty (CHOSEN placeholders) — the budget
    chain above is real physics, but the J/EOH mapping is not yet measured.

    Raises:
        KeyError: if domain is not one of the four EOH domains.
    """
    return IOTA_FLOOR_BY_DOMAIN[domain]


def eoh_weighted_iota_floor(eoh_by_domain: dict[str, float]) -> float:
    """
    ῑ_floor — the EOH-weighted aggregate thermodynamic floor (J/EOH).

        ῑ_floor = Σ_d ι_floor,d · EOH_d / Σ_d EOH_d

    Uses only the four generating domains (personal, infrastructure, ecological,
    knowledge); the 'total' and bookkeeping keys in a total_eoh() dict are ignored.
    """
    num = 0.0
    den = 0.0
    for d in _EOH_DOMAINS:
        eoh_d = eoh_by_domain.get(d, 0.0)
        num += iota_floor(d) * eoh_d
        den += eoh_d
    if den <= 0.0:
        raise ValueError("total generating EOH must be positive to weight ι_floor")
    return num / den


# ---------------------------------------------------------------------------
# The provable ceiling bound — E29 / F2
# ---------------------------------------------------------------------------

class BoundReport(TypedDict):
    epsilon_max_bound: float | None    # floor-based UPPER bound on ε_max; None if unbudgeted
    verdict: BoundVerdict
    conclusive: bool                   # True iff the floor bound proves ε_max < 1
    binds_below_1: bool                # epsilon_max_bound < 1
    psi_star: float                    # allocated density (W·m⁻²)
    phi_star_collective: float         # ψ*·A_eff(c) — collective allocation (W)
    phi_other: float                   # residual dissipation charged (W)
    iota_floor_weighted: float         # ῑ_floor (J/EOH)
    eoh_total: float                   # EOH_total(c) (hours/year)
    headroom_w: float                  # ψ*·A_eff − Φ_other (W); the numerator
    advisory_only: bool                # always True at P0 — generates no obligation


def provable_ceiling_bound(
    a_eff_collective: float,
    phi_other: float = THERMAL_ANTHROPOGENIC_DISSIPATION_W,
    a_eff_total: float = A_EARTH_M2,
    epsilon: float | None = 0.40,
    eoh_by_domain: dict[str, float] | None = None,
    dt_s: float = SECONDS_PER_YEAR,
    r: float = THERMAL_COMMONS_RESERVE,
    delta_t_lo: float = THERMAL_DT_LO,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
) -> BoundReport:
    """
    E29 — the provable automation-ceiling bound, findings F1/F2. CONDITIONAL
    (demoted from the P0 headline; see the module docstring and F3
    `decarbonization_headroom`, the primary finding).

        ε_max(c) ≤ [ ψ*·A_eff(c) − Φ_other(c) ] · Δt_s / ( ῑ_floor · EOH_total(c) )

    Computed entirely from physical constants and existing EOH inventory — no new
    measurement. Because ι_floor ≤ real ι and ε_max decreases in ι, the returned
    value OVERSTATES the true ε_max (handoff §13.1 path D). Hence a bound < 1 would
    be conclusive (the thermal budget forbids full automation). At current
    dissipation the bound comes back ≥ 1 (INCONCLUSIVE) — and the measured Path C
    run confirms F1/F2 do NOT bind globally today; post-C5 they begin to bind at
    2.2× present dissipation (ΔT_lo = 3.0 K). The measured binding instrument is
    collective utilization U (research/thermal_path_c.py, F11), not this bound.

    Advisory only: returns a report; generates no obligation, mints no TEH.

    Degradation (handoff §9):
      - ψ* = 0 (budget exhausted by GHG/albedo) → verdict UNBUDGETED, bound None.
      - numerator ≤ 0 (Φ_other already exceeds the collective allocation) → the
        collective is over budget on residual dissipation alone; bound floored at
        0.0 and reported CONCLUSIVE_BELOW_1.

    Args:
        a_eff_collective: η-weighted effective area of the collective (m²). For P0
            a plain area may be passed (η defaults to 1; handoff §9 missing-η rule).
        phi_other: residual (non-automation) dissipation charged to the collective (W).
        a_eff_total: total effective area the budget divides over (m²); Earth default.
        epsilon: automation level for the EOH inventory when eoh_by_domain is None.
        eoh_by_domain: explicit per-domain EOH (hours/year); when None, derived via
            total_eoh(epsilon=...). Must carry the four generating domains.
        dt_s: period length in seconds (Δt_s); one year default.
        r, delta_t_lo, lam, f_ghg, f_alb: budget-chain parameters (see E6–E8).

    Returns:
        BoundReport.

    Raises:
        ValueError: if a_eff_collective ≤ 0.
    """
    if a_eff_collective <= 0.0:
        raise ValueError(f"a_eff_collective must be positive, got {a_eff_collective}")

    if eoh_by_domain is None:
        eoh_by_domain = total_eoh(epsilon=epsilon)
    eoh_total = sum(eoh_by_domain.get(d, 0.0) for d in _EOH_DOMAINS)
    iota_bar = eoh_weighted_iota_floor(eoh_by_domain)

    psi_star = allocated_density(a_eff_total, r, delta_t_lo, lam, f_ghg, f_alb)
    phi_star_collective = psi_star * a_eff_collective
    headroom_w = phi_star_collective - phi_other

    # ψ* == 0: unbudgeted regime (E8 / §9). No finite bound.
    if psi_star <= 0.0:
        return BoundReport(
            epsilon_max_bound=None,
            verdict="UNBUDGETED",
            conclusive=True,   # unbudgeted is itself a conclusive (worst-case) finding
            binds_below_1=True,
            psi_star=psi_star,
            phi_star_collective=phi_star_collective,
            phi_other=phi_other,
            iota_floor_weighted=iota_bar,
            eoh_total=eoh_total,
            headroom_w=headroom_w,
            advisory_only=True,
        )

    # Numerator ≤ 0: over budget on residual dissipation alone.
    if headroom_w <= 0.0:
        return BoundReport(
            epsilon_max_bound=0.0,
            verdict="CONCLUSIVE_BELOW_1",
            conclusive=True,
            binds_below_1=True,
            psi_star=psi_star,
            phi_star_collective=phi_star_collective,
            phi_other=phi_other,
            iota_floor_weighted=iota_bar,
            eoh_total=eoh_total,
            headroom_w=headroom_w,
            advisory_only=True,
        )

    # EOH·s⁻¹ conversion: EOH_total is hours/year; the flux form (E2) divides by
    # Δt_s, so the bound multiplies the watt headroom by Δt_s over (ῑ_floor·EOH).
    bound = headroom_w * dt_s / (iota_bar * eoh_total)
    binds = bound < 1.0
    return BoundReport(
        epsilon_max_bound=bound,
        verdict="CONCLUSIVE_BELOW_1" if binds else "INCONCLUSIVE_ABOVE_1",
        conclusive=binds,
        binds_below_1=binds,
        psi_star=psi_star,
        phi_star_collective=phi_star_collective,
        phi_other=phi_other,
        iota_floor_weighted=iota_bar,
        eoh_total=eoh_total,
        headroom_w=headroom_w,
        advisory_only=True,
    )


# ---------------------------------------------------------------------------
# Sensitivity — the §10.2 robustness deliverable
# ---------------------------------------------------------------------------

class SensitivityCell(TypedDict):
    lam: float
    delta_t_lo: float
    residual_forcing: float
    psi_star: float
    epsilon_max_bound: float | None
    verdict: BoundVerdict


class SensitivityReport(TypedDict):
    cells: list[SensitivityCell]
    any_conclusive_below_1: bool     # did any assessed corner prove ε_max < 1 (excl. unbudgeted)?
    any_unbudgeted: bool             # did any corner exhaust the budget on GHG/albedo alone?
    all_inconclusive_when_budgeted: bool  # when budgeted, was the floor bound ALWAYS ≥ 1?
    note: str


def ceiling_bound_sensitivity(
    a_eff_collective: float,
    phi_other: float = THERMAL_ANTHROPOGENIC_DISSIPATION_W,
    epsilon: float | None = 0.40,
    lam_values: tuple[float, ...] = (1.2, 2.0, 3.2),
    delta_t_lo_values: tuple[float, ...] = (1.5, 2.0, 3.0, 4.0),
    r: float = THERMAL_COMMONS_RESERVE,
    f_ghg: float = THERMAL_F_GHG,
    f_alb: float = THERMAL_F_ALB,
) -> SensitivityReport:
    """
    §10.2 robustness — sweep the assessed climate space and report whether the
    corridor SIGN (does ε_max bind below 1?) is robust. This, not the point bound,
    is what §10.2 gates obligation on: if the sign is not robust, the extension is
    advisory-only.

    The floor-based bound (path D) can only prove ε_max < 1; a bound ≥ 1 is
    inconclusive (needs measured ι). So `all_inconclusive_when_budgeted = True`
    is the expected honest result — it says the thermodynamic floor is too low to
    bind automation, and the binding question needs the measured-ι ladder. The
    measured Path C run confirmed exactly this globally, which is why F1/F2 are
    demoted to conditional and F3 (`decarbonization_headroom`) is the P0 headline.
    """
    cells: list[SensitivityCell] = []
    any_below = False
    any_unbudgeted = False
    all_inconclusive = True
    for lam in lam_values:
        for dt in delta_t_lo_values:
            rep = provable_ceiling_bound(
                a_eff_collective, phi_other=phi_other, epsilon=epsilon,
                delta_t_lo=dt, lam=lam, r=r, f_ghg=f_ghg, f_alb=f_alb,
            )
            cells.append(SensitivityCell(
                lam=lam,
                delta_t_lo=dt,
                residual_forcing=residual_thermal_forcing(delta_t_lo=dt, lam=lam),
                psi_star=rep["psi_star"],
                epsilon_max_bound=rep["epsilon_max_bound"],
                verdict=rep["verdict"],
            ))
            if rep["verdict"] == "UNBUDGETED":
                any_unbudgeted = True
            elif rep["verdict"] == "CONCLUSIVE_BELOW_1":
                any_below = True
                all_inconclusive = False
            else:  # INCONCLUSIVE_ABOVE_1 — budgeted but floor did not bind
                pass
    note = (
        "Floor-based bound (path D) is an OVERSTATE of ε_max: a bound < 1 is "
        "conclusive, a bound ≥ 1 is inconclusive and needs measured ι (path C/B)."
    )
    return SensitivityReport(
        cells=cells,
        any_conclusive_below_1=any_below,
        any_unbudgeted=any_unbudgeted,
        all_inconclusive_when_budgeted=all_inconclusive,
        note=note,
    )
