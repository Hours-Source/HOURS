"""
Thermal Sink EOH — capital as dual-output (§12.2).

The thermal handoff §12.2 makes capital dual-output: the SAME inventory that
eliminates EOH (core.civilization.machine_eoh_from_capital) also dissipates heat.
This module derives that thermal load Φ_auto from the capital stock, so a
collective's thermal ceiling is computed from its OWN capital — the framework's
existing ε sub-model — rather than only top-down from national energy statistics
(the Path C route, research/thermal_path_c.py).

This is the capital adaptation the thermal spec required, and it closes the loop:

    capital stock ──► machine_eoh_from_capital ──► ε          (existing)
                 └──► machine_dissipation_from_capital ──► Φ ──► ψ ──► U  (this)

Both from one inventory — "single data requirements, not several" (§12.2). Service
life feeds both the EOH age model and the embodied-energy amortization here;
condition modulates both the EOH eliminated and the operational dissipation.

Φ has two parts:
    operational:  Σ_type  teh · condition · power_intensity            (running draw)
    embodied:     Σ_type  teh · embodied_energy / (design_life · Δt_s) (amortized)
both × κ̄_grid, the net thermal addition of the physical grid serving the capital.

Honest status: the thermal intensities (CAPITAL_THERMAL_PROFILES) are CHOSEN
placeholders — relative ordering defensible, absolute scale anchored only to
order-of-consistency with Path C's measured ~2200 W·person⁻¹, not fitted. So this
is a Path-B-shaped instrument running on Path-D data: the STRUCTURE (one inventory
→ both outputs) is the deliverable; the magnitudes inherit the placeholder scale.
Advisory only — generates no obligation.

Layer: research/ — reuses core.civilization (DRY, via its by_type output) and the
Path C budget/ceiling machinery; not imported by core/.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.civilization import machine_eoh_from_capital
from hours_eoh.data import (
    CAPITAL_THERMAL_PROFILES,
    SECONDS_PER_YEAR,
    THERMAL_GRID_KAPPA_DEFAULT,
    THERMAL_U_FLOOR,
)
from hours_eoh.research.thermal_path_c import budget_psi_star, utilization_regime, ForcingBasis
from hours_eoh.research.corridor import measured_thermal_ceiling, Ceiling


class CapitalDissipation(TypedDict):
    phi_operational_w: float          # running power draw × κ (W)
    phi_embodied_w: float             # embodied energy amortized over life × κ (W)
    phi_total_w: float                # Φ_auto from this capital stock (W)
    grid_kappa: float
    by_type: dict[str, dict]          # per-type operational/embodied/total (W)


def machine_dissipation_from_capital(
    capital_desc: dict,
    population: float,
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
) -> CapitalDissipation:
    """
    Φ_auto (W) from a capital description — the thermal twin of
    machine_eoh_from_capital(), reusing its resolved per-type stock (DRY).

    Governing equations (per capital type, then summed):
        operational = teh · condition · power_intensity_w_per_teh
        embodied    = teh · embodied_energy_j_per_teh / (design_life · Δt_s)
        Φ_type      = (operational + embodied) · κ̄_grid

    κ̄_grid is the net thermal addition of the physical grid serving the capital
    (§8.1) — a collective property, so a derivation input, not a per-type field.
    Operational dissipation scales with condition (a utilization proxy, parallel
    to the EOH the same capital eliminates); embodied energy is already spent and
    is amortized over design_life regardless of condition.

    Args:
        capital_desc: {type_name: tier-string | spec-dict}, as machine_eoh_from_capital.
        population: total population (scales per-capita tier values).
        grid_kappa: κ̄ of the grid ∈ [0, 1]; 1 = fully stock-liberating.

    Returns:
        CapitalDissipation.

    Raises:
        ValueError: if grid_kappa is outside [0, 1].
    """
    if not 0.0 <= grid_kappa <= 1.0:
        raise ValueError(f"grid_kappa must be in [0, 1], got {grid_kappa}")

    eoh = machine_eoh_from_capital(capital_desc, population)
    op_total = 0.0
    emb_total = 0.0
    by_type: dict[str, dict] = {}
    for type_name, row in eoh["by_type"].items():
        tp = CAPITAL_THERMAL_PROFILES.get(type_name)
        if tp is None:
            continue  # capital type with no thermal profile contributes 0 (flagged by omission)
        teh = row["teh_value"]
        cond = row["condition"]
        dl = max(row["design_life"], 1.0)
        op = teh * cond * tp["power_intensity_w_per_teh"]
        emb = teh * tp["embodied_energy_j_per_teh"] / (dl * SECONDS_PER_YEAR)
        by_type[type_name] = {
            "operational_w": op * grid_kappa,
            "embodied_w": emb * grid_kappa,
            "total_w": (op + emb) * grid_kappa,
        }
        op_total += op
        emb_total += emb

    return CapitalDissipation(
        phi_operational_w=op_total * grid_kappa,
        phi_embodied_w=emb_total * grid_kappa,
        phi_total_w=(op_total + emb_total) * grid_kappa,
        grid_kappa=grid_kappa,
        by_type=by_type,
    )


class CapitalThermalState(TypedDict):
    phi_w: float                  # Φ_auto from capital (W)
    land_m2: float
    psi: float                    # dissipation density Φ/land (W·m⁻²)
    psi_star: float               # allocated budget density (W·m⁻²)
    utilization: float            # U = ψ/ψ*
    regime: str
    in_contact: bool
    phi_per_capita_w: float       # sanity anchor vs Path C ~2200 W·person⁻¹


def collective_thermal_from_capital(
    capital_desc: dict,
    population: float,
    land_m2: float,
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
    u_floor: float = THERMAL_U_FLOOR,
) -> CapitalThermalState:
    """
    A collective's thermal utilization U from its OWN capital stock (bottom-up),
    the framework-native alternative to the Path C national-energy route.

    Φ from machine_dissipation_from_capital → density ψ = Φ/land → U = ψ/ψ*, with
    ψ* the allocated budget (reused from Path C). Feeds measured_thermal_ceiling()
    exactly as the Path C utilization does — so a collective whose capital puts it
    in Contact (U ≥ 1) closes its corridor on measured-structure thermal grounds.

    Reports phi_per_capita_w as the honest sanity anchor against Path C's measured
    ~2200 W·person⁻¹ net-additive dissipation.
    """
    if land_m2 <= 0.0:
        raise ValueError("land_m2 must be positive")
    diss = machine_dissipation_from_capital(capital_desc, population, grid_kappa)
    phi = diss["phi_total_w"]
    psi = phi / land_m2
    psi_star = budget_psi_star(delta_t_lo, basis)
    u, regime = utilization_regime(psi, psi_star, u_floor)
    return CapitalThermalState(
        phi_w=phi,
        land_m2=land_m2,
        psi=psi,
        psi_star=psi_star,
        utilization=u,
        regime=regime,
        in_contact=(regime == "contact"),
        phi_per_capita_w=phi / population if population > 0 else float("inf"),
    )


def capital_thermal_ceiling(
    capital_desc: dict,
    population: float,
    land_m2: float,
    epsilon_current: float,
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
    delta_t_lo: float = 3.0,
    basis: ForcingBasis = "net_erf",
) -> Ceiling:
    """
    The corridor's thermal ceiling computed bottom-up from the collective's
    capital (vs the Path C top-down version). Binds at ε_current when the capital
    stock puts the collective in Contact (U ≥ 1). Thin bridge to the corridor.
    """
    st = collective_thermal_from_capital(
        capital_desc, population, land_m2, grid_kappa, delta_t_lo, basis,
    )
    return measured_thermal_ceiling(st["utilization"], epsilon_current)
