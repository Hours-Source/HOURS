"""
Thermal Sink EOH — Path C: the measured top-down thermal residual.

Path C is the measurement the corridor's thermal ceiling was waiting on: the
dissipation Φ and the budget ψ* from published energy statistics + measured
forcing, rather than thermodynamic floors (P0, research/thermal.py). It resolves
the P0 finding "INCONCLUSIVE from floors" into a concrete, measured answer.

The operative formula (the handoff's algebraic shortcut, Eq. C1):

    ε_max = ε_current · (allocated budget) / Φ_auto            ι and EOH_total CANCEL

so Path C needs NO EOH register — only energy statistics and the framework's
existing ε ≈ 0.40. This is what moved the method from "near-term" to "runnable
today." Caveat: C1 holds ι and EOH_total fixed as ε scales, so the figure is a
LOWER bound on ε_max (falling ι raises it; rising EOH_total lowers it).

Three findings this reproduces (see handoffs/path c - thermal sink/):
  F1  the thermal ceiling does NOT bind globally at current dissipation — but by
      much less margin than the pre-C5 run reported. CONDITIONAL: binding needs
      Φ > ε_current·budget, and by Eq. C1 that multiple IS ε_max, so at ΔT_lo =
      3.0 K the ceiling binds at 2.2× present dissipation, not the ~10–50×
      claimed before the forcing correction. Range 2.2× (3.0 K) to 13.4× (4.0 K).
  F3  carbon has consumed essentially the whole thermal budget: decarbonization
      is worth ~1,374 TW ≈ 78× current dissipation on the total-ERF basis, or
      ~1,267 TW ≈ 72× on the anthropogenic (removable-forcing) basis. THE
      load-bearing thermal claim — the measured signal is here, not in F1.
  F11 dense collectives are in Contact NOW (at ΔT_lo = 3.0 K post-C5: Singapore
      U ≈ 84, S. Korea 5.2, Netherlands 3.9, and Germany/UK newly over 1). The
      constraint binds LOCALLY while the global aggregate sits at U = 0.18 — so
      the corridor's thermal ceiling is a COLLECTIVE-level instrument; run
      globally it is uninformative by more than an order of magnitude.

C5 (2026-08-03): forcing moved from AR6-2019 2.72 to IGCC-2025a total 3.366
[2.602–4.102]. Every figure above is post-correction. The budget is smaller, so
every ceiling tightened and every utilization rose; F3 grew because the gain is
linear in the forcing removed.

Provenance is uneven and the weakest data drives the strongest finding — the
shipped dataset (reference/data/thermal_path_c.json) carries per-input tiers
(A retrieved / B constant / C training-data-unverified / D framework placeholder).
ΔT_lo (Tier D) dominates everything; national energy (Tier C) is unverified —
Singapore is robust, Netherlands/S. Korea are marginal (30% error flips regime).
Do NOT generate obligation from this; it is Path C (5–10× uncertainty), adequate
for regime SIGN per §10.2, not for obligation (that is Path B).

Layer: research/ — reuses the budget chain from research/thermal.py; reads the
shipped dataset via reference/. Not imported by core/.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from hours_eoh.data import (
    SECONDS_PER_YEAR,
    A_LAND_CLAIMED_M2,
    THERMAL_LAMBDA_FEEDBACK,
    THERMAL_COMMONS_RESERVE,
    THERMAL_F_NET_ERF,
    THERMAL_F_NET_ERF_P05,
    THERMAL_F_NET_ERF_P95,
    THERMAL_F_ANTHRO_ERF,
    THERMAL_F_WMGHG_ERF,
    THERMAL_TXX_PER_GMST,
    THERMAL_U_FLOOR,
    THERMAL_EPS_CURRENT,
    ETA_BASIS,
)
from hours_eoh.research.thermal import (
    allocated_density,
    decarbonization_headroom as _p0_decarbonization_headroom,
)

_DATA = Path(__file__).resolve().parents[1] / "reference" / "data" / "thermal_path_c.json"
_EJ_TO_J = 1.0e18

Regime = Literal["contact", "standing_exposure", "below_floor", "unbudgeted"]
ForcingBasis = Literal["net_erf", "wmghg", "anthro"]
DeterminacyZone = Literal["determinate_unbudgeted", "indeterminate", "determinate_budgeted"]


@lru_cache(maxsize=1)
def load_path_c_inputs() -> dict:
    """The shipped Path C dataset (energy mix, κ, forcing, national records), with
    provenance tiers intact. Read the `_tier`/`_caveat`/`_WARNING` fields before
    citing any figure — provenance is uneven by design."""
    with _DATA.open(encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


# ---------------------------------------------------------------------------
# E1 — measured dissipation
# ---------------------------------------------------------------------------

def dissipation_flux(
    energy_by_source_ej: dict[str, float],
    kappa: dict[str, float],
) -> float:
    """
    E1 — κ-weighted net-additive dissipation Φ (W) from an annual energy mix.

        Φ = Σ_s ( EJ_s · κ_s ) · 10¹⁸ / Δt_s

    κ is the net thermal addition coefficient: stock-liberating sources (fossil,
    nuclear, fusion, geothermal) = 1.0; flux-redirecting (wind, hydro, solar) ≈ 0.
    Only sources present in BOTH dicts contribute; a missing κ defaults conservative
    (1.0) per the handoff's missing-κ rule.

    Worked example (2025 world mix): 558.8 EJ net-additive → Φ = 17.71 TW.

    Args:
        energy_by_source_ej: annual energy supply by source (EJ/yr).
        kappa: net thermal addition coefficient per source (dimensionless).

    Returns:
        Net-additive dissipation Φ (W).
    """
    phi_ej = 0.0
    for source, ej in energy_by_source_ej.items():
        k = kappa.get(source, 1.0)  # missing κ → conservative 1.0
        phi_ej += ej * k
    return phi_ej * _EJ_TO_J / SECONDS_PER_YEAR


def world_dissipation() -> float:
    """Φ for the shipped 2025 world energy mix (17.71 TW)."""
    d = load_path_c_inputs()
    return dissipation_flux(d["world_energy_2025"]["by_source_EJ"], d["kappa_coefficients"])


# ---------------------------------------------------------------------------
# Eq. C1 — measured global ε_max (no EOH register)
# ---------------------------------------------------------------------------

def measured_epsilon_max(
    allocated_budget_w: float,
    phi_auto_w: float,
    eps_current: float = THERMAL_EPS_CURRENT,
) -> float | None:
    """
    Eq. C1 — the measured automation ceiling, without an EOH register.

        ε_max = ε_current · allocated_budget / Φ_auto

    ι and EOH_total cancel out of E21/ε_current, leaving only measured energy
    quantities. A LOWER bound (holds ι, EOH_total fixed as ε scales). Returns None
    when the budget is zero (unbudgeted — GHG forcing has consumed the allowance).

    Args:
        allocated_budget_w: the collective/global thermal allocation (W); for the
            global figure, ψ*·A_claimed = (1−r)·Φ*_planet.
        phi_auto_w: current automation dissipation (W); Path C uses Φ ≈ Φ_auto.
        eps_current: the framework's current-equilibrium ε.

    Returns:
        ε_max (dimensionless), or None if unbudgeted.
    """
    if allocated_budget_w <= 0.0:
        return None
    if phi_auto_w <= 0.0:
        raise ValueError("phi_auto_w must be positive")
    return eps_current * allocated_budget_w / phi_auto_w


# ---------------------------------------------------------------------------
# E6–E8 budget wrapper (measured forcing basis)
# ---------------------------------------------------------------------------

_FORCING_BY_BASIS: dict[str, float] = {
    "net_erf": THERMAL_F_NET_ERF,      # C4: total ERF — the BUDGET basis
    "wmghg": THERMAL_F_WMGHG_ERF,      # GHG alone — forward-looking as aerosol cooling declines
    "anthro": THERMAL_F_ANTHRO_ERF,    # anthropogenic alone — the REMOVABLE forcing (F3 basis)
}


def _forcing_value(basis: ForcingBasis) -> float:
    return _FORCING_BY_BASIS[basis]


def budget_psi_star(
    delta_t_lo: float,
    basis: ForcingBasis = "net_erf",
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    r: float = THERMAL_COMMONS_RESERVE,
    a_eff_total: float = A_LAND_CLAIMED_M2,
) -> float:
    """ψ* (W·m⁻² of claimed land) at a habitability threshold and forcing basis.
    Thin wrapper over research.thermal.allocated_density with the measured forcing.
    Zero below the budget-opening threshold. Post-C5: ψ*(3.0 K, net) = 0.707,
    ψ*(3.5 K, net) = 2.521 (was 2.660 at 3.0 K on the superseded 2.72 forcing —
    the corrected budget is roughly a quarter of what the old constant implied)."""
    return allocated_density(
        a_eff_total, r=r, delta_t_lo=delta_t_lo, lam=lam,
        f_ghg=_forcing_value(basis), f_alb=0.0,
    )


def budget_opens_at(basis: ForcingBasis = "net_erf",
                    lam: float = THERMAL_LAMBDA_FEEDBACK) -> float:
    """ΔT_lo (K, GMST) at which the budget opens: F/λ. Post-C5: 2.805 K on total
    ERF, 2.988 K GHG-only, 2.587 K anthropogenic-only (was 2.27/3.20)."""
    return _forcing_value(basis) / lam


def determinacy_zone(
    delta_t_lo: float,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    f_p05: float = THERMAL_F_NET_ERF_P05,
    f_p95: float = THERMAL_F_NET_ERF_P95,
) -> dict:
    """
    The SINGLE-AXIS determinacy map (handoff 2.0 §4.2) — the central Path C
    result, and the one thing C5 made computable: with a forcing UNCERTAINTY BAND
    rather than a point value, some habitability thresholds give a robust answer
    and some do not.

    **SUPERSEDED 2026-08-05 by research.thermal_lambda.determinacy_map.** This
    function holds λ FIXED at an unassessed value, so it reports a determinate
    zone about three times wider than the evidence supports. Carrying λ as well —
    which the two-axis map does — moves the determinately-unbudgeted boundary from
    2.168 K to 1.324 K GMST, or 3.21 K to 1.96 K in land extremes, and widens the
    indeterminate band 3.12×. Determinacy requires the WHOLE parameter box to
    agree, so an extra uncertain axis can only ever make agreement harder.

    Retained because the §4.2 numbers were published against it and the delta must
    stay auditable. Do NOT lead with it: `thermal_lambda.thermal_verdict` is the
    headline entry point.

        budget opens at  ΔT = F/λ

    so sweeping F across its p05–p95 band gives two thresholds and three zones:

        ΔT ≤ F_p05/λ   determinate — UNBUDGETED. Even the most favourable
                       forcing leaves no allowance; all net-additive dissipation
                       is overshoot. Robust across the whole forcing band.
        ΔT ≥ F_p95/λ   determinate — BUDGETED. A budget exists even on the least
                       favourable forcing.
        between        INDETERMINATE. Forcing uncertainty ALONE spans
                       below-floor to Contact; the framework cannot report a
                       sign, and saying which side it falls on would be a claim
                       the data does not support.

    Post-C5 (λ = 1.2, IGCC 2025a band): 2.168 K and 3.418 K GMST — equivalently
    3.209 K and 5.059 K in land TXx via C6 (×1.48). The upper determinate zone
    therefore requires ~5.1 K of land extreme warming, which is beyond any
    defensible habitability threshold. The determinate answer actually available
    to an honest assessment is the LOWER one.

    Args:
        delta_t_lo: assessed habitability threshold (K, GMST basis).
        lam: climate feedback parameter (W·m⁻²·K⁻¹).
        f_p05, f_p95: forcing uncertainty band (W·m⁻²).

    Returns:
        dict with `zone`, the two thresholds in GMST and in land TXx, and
        `robust` (True outside the indeterminate band).
    """
    lo, hi = f_p05 / lam, f_p95 / lam
    if delta_t_lo <= lo:
        zone: DeterminacyZone = "determinate_unbudgeted"
    elif delta_t_lo >= hi:
        zone = "determinate_budgeted"
    else:
        zone = "indeterminate"
    return {
        "delta_t_lo": delta_t_lo,
        "zone": zone,
        "robust": zone != "indeterminate",
        "unbudgeted_below_k": lo,
        "budgeted_above_k": hi,
        "unbudgeted_below_txx_k": lo * THERMAL_TXX_PER_GMST,
        "budgeted_above_txx_k": hi * THERMAL_TXX_PER_GMST,
    }


# ---------------------------------------------------------------------------
# F11 — collective utilization and regime (the measured binding instrument)
# ---------------------------------------------------------------------------

class CollectiveUtilization(TypedDict):
    name: str
    psi: float                # W·m⁻² dissipation density on EFFECTIVE land (η·a)
    psi_star: float           # W·m⁻² allocated density
    utilization: float        # U = ψ/ψ*
    regime: Regime
    in_contact: bool
    eta: float | None         # η looked up; None = unresolved or unknown collective
    eta_applied: float        # what was actually used — 1.0 when η is None


def collective_dissipation_density(
    energy_ej: float,
    land_m2: float,
    fossil_nuclear_share: float,
    eta: float = 1.0,
) -> float:
    """
    ψ (W·m⁻²) — a collective's net-additive dissipation per unit EFFECTIVE land.

        A_eff = η · land_m²
        ψ     = ( energy_EJ · 10¹⁸ / Δt_s ) · κ̄ / A_eff

    κ̄ is approximated by the fossil+nuclear share (those sources have κ = 1; the
    remainder ≈ 0).

    η (P2, reference/data/eta_land.json) weights land by how effectively its
    column sheds heat to space, normalised so the mean over claimed land is 1 —
    so η REDISTRIBUTES a fixed planetary budget rather than changing it. Default
    1.0 leaves every existing caller unmoved.

    Effect at ΔT_lo = 3.0 K: no collective crosses the Contact boundary. η moves
    utilization by −9% to +18% — Singapore 84.2 → 79.2, Canada 0.05 → 0.06,
    Germany and the UK deeper into Contact. Real, second-order, and not a rescue.

    Raises:
        ValueError: if land_m2 or eta is not positive.
    """
    if land_m2 <= 0.0:
        raise ValueError("land_m2 must be positive")
    if eta <= 0.0:
        raise ValueError(f"eta must be positive, got {eta}")
    phi = energy_ej * _EJ_TO_J / SECONDS_PER_YEAR * fossil_nuclear_share
    return phi / (eta * land_m2)


def utilization_regime(
    psi: float,
    psi_star: float,
    u_floor: float = THERMAL_U_FLOOR,
) -> tuple[float, Regime]:
    """U = ψ/ψ* and its regime. U ≥ 1 → Contact (over budget); U ≥ u_floor →
    Standing exposure; below → below_floor. ψ* = 0 → unbudgeted."""
    if psi_star <= 0.0:
        return float("inf"), "unbudgeted"
    u = psi / psi_star
    if u >= 1.0:
        return u, "contact"
    if u >= u_floor:
        return u, "standing_exposure"
    return u, "below_floor"


def collective_utilization(
    name: str,
    energy_ej: float,
    land_m2: float,
    fossil_nuclear_share: float,
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
    u_floor: float = THERMAL_U_FLOOR,
    eta: float | None = None,
    eta_name: str | None = None,
) -> CollectiveUtilization:
    """Full per-collective utilization (F11). Post-C5 at ΔT_lo=3.0 K, net-ERF,
    Singapore reads U ≈ 84 (Contact); the World aggregate reads U ≈ 0.18 (below
    floor) — which is why the thermal instrument is collective-level, not
    planetary. The C5 correction quadrupled every U at this threshold; the
    regime SIGN is unchanged for the extremes but Germany and the UK crossed
    into Contact, so marginal collectives must be re-read, not carried over."""
    if eta is None:
        eta = eta_for(eta_name if eta_name is not None else name)
    eta_applied = 1.0 if eta is None else eta
    psi = collective_dissipation_density(energy_ej, land_m2, fossil_nuclear_share, eta_applied)
    psi_star = budget_psi_star(delta_t_lo, basis)
    u, regime = utilization_regime(psi, psi_star, u_floor)
    return CollectiveUtilization(
        name=name, psi=psi, psi_star=psi_star,
        utilization=u, regime=regime, in_contact=(regime == "contact"),
        eta=eta, eta_applied=eta_applied,
    )


def all_collectives_utilization(
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
) -> list[CollectiveUtilization]:
    """Utilization for every national record in the shipped dataset."""
    d = load_path_c_inputs()
    out: list[CollectiveUtilization] = []
    for rec in d["national_data"]["records"]:
        out.append(collective_utilization(
            rec["name"], rec["energy_EJ"], rec["land_m2"],
            rec["fossil_nuclear_share"], delta_t_lo, basis,
        ))
    return out


# ---------------------------------------------------------------------------
# F3 — decarbonization headroom (the load-bearing measured claim)
# ---------------------------------------------------------------------------

def decarbonization_headroom(
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    r: float = THERMAL_COMMONS_RESERVE,
    a_earth: float = 5.101e14,
) -> dict:
    """
    F3 — the MEASURED decarbonization headroom: the P0 structural finding
    (research.thermal.decarbonization_headroom) evaluated at measured forcing, plus
    the ratio to measured current world dissipation.

        gain = allocated(ΔT_lo, F=0) − allocated(ΔT_lo, F=measured)
             = (1 − r) · min(F, λ·ΔT_lo) · A_earth

    Above the budget-opening threshold the ΔT term drops out and the gain is just
    the removable forcing; below it the gain is capped by the entire temperature
    allowance and still rises with ΔT_lo (at 2.5 K it is 1,224 TW, not 1,374).

    Post-C5 the gain is 1,374 TW ≈ 78× current world dissipation on the default
    `net_erf` basis — the strongest measured thermal signal, and why the P0
    headline was reordered to this from the (non-binding) floor bound.

    BASIS CAVEAT — open, author's call. The gain is linear in the forcing
    removed, so the basis is the whole answer:

        net_erf  F = 3.366 → 1,374 TW (78×). Consistent with the BUDGET (C4),
                 but credits decarbonization with removing solar and volcanic
                 forcing (+0.262), which labor cannot remove.
        anthro   F = 3.104 → 1,267 TW (72×). The REMOVABLE forcing: what human
                 action put there is what human action can take back. Aerosol
                 unmasking is already netted in, so this is the honest ceiling
                 on what decarbonization can actually return.
        wmghg    F = 3.585 → 1,463 TW (83×). GHG alone, ignoring the aerosol
                 cooling that would be lost alongside — an OVER-estimate.

    The default is unchanged (`net_erf`) so this correction did not silently move
    the theory; `anthro` is the defensible F3 basis and switching it is a
    sign-off item. See handoff 2.0 §10.1.

    Returns:
        dict: the P0 DecarbonizationHeadroom fields plus `basis` and
        `gain_over_current_dissipation`.
    """
    base = _p0_decarbonization_headroom(
        delta_t_lo=delta_t_lo, lam=lam, r=r,
        f_ghg=_forcing_value(basis), f_alb=0.0, a_earth=a_earth,
    )
    phi = world_dissipation()
    return {
        **base,
        "basis": basis,
        "gain_over_current_dissipation": base["gain_w"] / phi if phi > 0 else float("inf"),
    }


# ---------------------------------------------------------------------------
# Orchestration — the global ε_max report (F1, conditional)
# ---------------------------------------------------------------------------

class GlobalCeilingReport(TypedDict):
    delta_t_lo: float
    basis: ForcingBasis
    phi_w: float
    allocated_budget_w: float
    headroom_multiple: float | None   # H = budget/Φ_auto — MEASURED, no chosen input
    utilization: float | None
    epsilon_max: float | None         # = H · ε_current, so it inherits a CHOSEN constant
    eps_current: float
    binds_below_1: bool
    note: str


def headroom_multiple(
    allocated_budget_w: float,
    phi_auto_w: float,
) -> float | None:
    """
    H — the thermal headroom multiple: how many times present automation
    dissipation the budget supports.

        H = allocated_budget / Φ_auto

    THE MEASURED CONTENT OF F1. Eq. C1 gives ε_max = ε_current · H, so ε_max is
    proportional to ε_current — a CHOSEN Tier D constant (0.40, "the arc
    midpoint"). H is the same statement with that constant divided out: a pure
    ratio of two energy quantities, both measured. "The thermal budget supports
    5.4× current automation dissipation" is a claim the ledger can back; "ε_max =
    2.16" is that claim multiplied by a number nobody measured.

    Report H as the headline and ε_max as a labelled conversion. This also sits
    better with the framework's own invariant that ε is an observable rather than
    an input — a ceiling expressed as a multiple of measured dissipation needs no
    view about where ε currently sits.

    units: dimensionless. Returns None when the budget is zero (unbudgeted).

    Raises:
        ValueError: if phi_auto_w is not positive.
    """
    if allocated_budget_w <= 0.0:
        return None
    if phi_auto_w <= 0.0:
        raise ValueError("phi_auto_w must be positive")
    return allocated_budget_w / phi_auto_w


def global_ceiling(
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
    eps_current: float = THERMAL_EPS_CURRENT,
    r: float = THERMAL_COMMONS_RESERVE,
    lam: float = THERMAL_LAMBDA_FEEDBACK,
    a_earth: float = 5.101e14,
) -> GlobalCeilingReport:
    """
    The measured global ε_max via Eq. C1 (F1). Comes back NON-BINDING at current
    dissipation, but the margin is thin post-C5: binding requires Φ ≥ ε_current ·
    budget, and dividing through, that multiple IS ε_max. So ε_max = 2.19 at
    ΔT_lo = 3.0 K means the global ceiling binds at 2.19× present dissipation —
    not the ~10–50× reported before the forcing correction. At ~2%/yr growth in
    net-additive supply that is roughly 40 years, so "non-binding" here means
    "not yet", not "far away".

    ε_max is also directly proportional to `eps_current`, a CHOSEN Tier D
    constant (0.40 = arc midpoint). At eps_current = 0.20 the same budget gives
    ε_max = 1.09 — essentially binding now. Report the sensitivity with the
    value; it is larger than the ΔT_lo sensitivity the handoff foregrounds.

    Reported as conditional, not a current constraint. For the binding instrument
    use collective_utilization() (F11); the global aggregate is uninformative.
    """
    phi = world_dissipation()
    f_th = lam * delta_t_lo - _forcing_value(basis)
    allocated = (1.0 - r) * max(0.0, f_th) * a_earth
    h = headroom_multiple(allocated, phi)
    eps_max = measured_epsilon_max(allocated, phi, eps_current)
    u = phi / allocated if allocated > 0.0 else None
    binds = eps_max is not None and eps_max < 1.0
    if allocated <= 0.0:
        note = "unbudgeted at this ΔT_lo/basis — GHG forcing has consumed the allowance (F3)"
    elif binds:
        note = "thermal ceiling binds globally at current dissipation"
    else:
        note = (f"non-binding globally (F1 conditional). MEASURED: the budget supports "
                f"H = {h:.3g}× present automation dissipation. Derived: ε_max = H·ε_current "
                f"= {eps_max:.3g} at the CHOSEN ε_current = {eps_current}, so the ceiling "
                f"binds at {eps_max:.2g}× present Φ — quote H, not ε_max, where the chosen "
                f"constant would travel with the claim")
    return GlobalCeilingReport(
        delta_t_lo=delta_t_lo, basis=basis, phi_w=phi,
        allocated_budget_w=allocated, headroom_multiple=h, utilization=u,
        epsilon_max=eps_max, eps_current=eps_current, binds_below_1=binds, note=note,
    )


# ---------------------------------------------------------------------------
# η — radiative-efficiency weighting on claimed land (P2)
# ---------------------------------------------------------------------------

_ETA_DATA = Path(__file__).resolve().parents[1] / "reference" / "data" / "eta_land.json"


@lru_cache(maxsize=1)
def load_eta_land() -> dict:
    """The shipped η table (reference/data/eta_land.json).

    ERA5 1940–2025, clear-sky and all-sky, normalised to CLAIMED land so its mean
    is 1 on the same footing as A_LAND_CLAIMED_M2. Read `_limitations` before
    citing: this is a sampled climatology (6 months, the 1st of each, 107 balanced
    days), not an annual mean."""
    with _ETA_DATA.open(encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


def eta_for(collective: str, basis: str = ETA_BASIS) -> float | None:
    """
    η for a collective — the weight on its claimed land area.

        A_eff(c) = η(c) · a(c)

    η redistributes a fixed budget rather than changing it: Σ η_i·a_i = Σ a_i over
    claimed land. A collective whose column sheds heat efficiently gets a larger
    allocation from the same planetary total.

    Returns None for a collective below ERA5's resolution with no land neighbour
    (three mid-Pacific atolls) and for unknown names — never a fabricated value,
    because a made-up η for a nation that may not survive the arc is not a
    rounding convenience. Callers must decide explicitly what to do with None.

    `basis` defaults to data.ETA_BASIS ("clear_sky"); "all_sky" is retained as the
    physical reality check. Where the two diverge the basis choice is doing real
    work — Singapore +0.12, Brazil +0.06, the Gulf −0.05 to −0.08.

    units: dimensionless, mean 1 over claimed land.

    Raises:
        ValueError: on an unknown basis.
    """
    if basis not in ("clear_sky", "all_sky"):
        raise ValueError(f"unknown eta basis: {basis!r}")
    rec = load_eta_land()["collectives"].get(collective)
    if rec is None:
        return None
    return rec[f"eta_{basis}"]
