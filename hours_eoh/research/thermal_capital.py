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
    CAPITAL_MACHINE_PROFILES,
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


# ---------------------------------------------------------------------------
# The census twin — one physical survey, two floors
# ---------------------------------------------------------------------------

class ThermalFloor(TypedDict):
    phi_operational_w: float      # running power draw × κ (W)
    phi_embodied_w: float         # embodied energy amortized over life × κ (W)
    phi_total_w: float            # the dissipation floor (W)
    grid_kappa: float
    coverage: float               # share of counted assets carrying thermal fields
    unpriced_buckets: list[int]   # indices contributing 0 for want of thermal data
    by_bucket: list[dict]


def infrastructure_thermal_floor(
    asset_census: list[dict],
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
) -> ThermalFloor:
    """
    The dissipation floor Φ (W) from the SAME physical condition census that
    yields the labour floor — core.eoh_generation.infrastructure_statutory_floor.

    Governing equation (per bucket, then summed):

        Φ_bucket = count · teh_per_unit
                   · [ condition · power_intensity
                       + embodied_energy / (design_life · Δt_s) ] · κ̄_grid

    This is `machine_dissipation_from_capital`'s per-type equation evaluated at
    census granularity: `count · teh_per_unit` supplies the TEH that the per-type
    route reads from the tier tables. Deliberately symmetric with the hours floor
    — same argument, same shape, watts instead of hours — so the pair reviews as
    one idea rather than two.

    Why it matters: the census is the item with an external deadline. A survey
    specified without `type`/`teh_per_unit`/`condition` can still produce the
    labour floor but can never produce this one without re-surveying, and it is
    the census — not national energy statistics — that makes F11's per-collective
    utilization defensible from a collective's own inventory.

    COVERAGE, NOT SILENT ZEROS. A bucket without usable thermal fields
    contributes nothing and is listed in `unpriced_buckets`; `coverage` is the
    share of counted assets that were actually priced. A thermal floor at 40%
    coverage is a different claim from one at 100%, and the caller is told which
    it holds. Reading a low-coverage total as a real floor understates Φ.

    Defaults are conservative where the census is silent: missing `condition`
    reads as 1.0 (full utilization → maximum operational draw), and missing
    `design_life_years` falls back to the type's CAPITAL_MACHINE_PROFILES life.

    units: watts. ε-behavior: none — like its hours twin this is a property of
    what is built and its condition, not of the automation level. ε enters when
    Φ is compared against an allocation (collective_thermal_from_capital), not
    here.

    Worked example (2,813 poor bridges, 40,000 TEH each, condition 0.35,
    transportation profile at 3.0 W/TEH and 90 MJ/TEH over 40 y, κ = 0.93):
        operational = 2813 · 40000 · 0.35 · 3.0          = 118.1 MW
        embodied    = 2813 · 40000 · 9.0e7 / (40 · Δt_s) =   8.0 MW
        Φ           = (118.1 + 8.0) · 0.93               = 117.3 MW

    Args:
        asset_census: buckets as documented on infrastructure_statutory_floor.
            Thermally priced iff `type` is a CAPITAL_THERMAL_PROFILES key and
            `teh_per_unit` is positive.
        grid_kappa: κ̄ of the grid serving the assets ∈ [0, 1]; 1 = fully
            stock-liberating. A collective property, not a per-asset one.

    Returns:
        ThermalFloor.

    Raises:
        ValueError: if grid_kappa is outside [0, 1], or a bucket has a negative
            count or negative thermal quantity.
    """
    if not 0.0 <= grid_kappa <= 1.0:
        raise ValueError(f"grid_kappa must be in [0, 1], got {grid_kappa}")

    op_total = 0.0
    emb_total = 0.0
    counted = 0.0
    priced = 0.0
    unpriced: list[int] = []
    by_bucket: list[dict] = []

    for i, bucket in enumerate(asset_census):
        count = float(bucket.get("count", 0.0))
        if count < 0.0:
            raise ValueError(f"census bucket {i} has negative count: {bucket!r}")
        counted += count

        raw_type = bucket.get("type")
        type_name = str(raw_type) if raw_type is not None else ""
        teh_per_unit = float(bucket.get("teh_per_unit", 0.0) or 0.0)
        profile = CAPITAL_THERMAL_PROFILES.get(type_name) if type_name else None
        if profile is None or teh_per_unit <= 0.0:
            unpriced.append(i)
            by_bucket.append({"index": i, "priced": False, "phi_w": 0.0})
            continue
        if teh_per_unit < 0.0:
            raise ValueError(f"census bucket {i} has negative teh_per_unit: {bucket!r}")

        condition = float(bucket.get("condition", 1.0))
        design_life = float(
            bucket.get("design_life_years")
            or CAPITAL_MACHINE_PROFILES.get(type_name, {}).get("design_life", 1.0)
        )
        if condition < 0.0 or design_life <= 0.0:
            raise ValueError(
                f"census bucket {i} needs condition ≥ 0 and design_life > 0: {bucket!r}"
            )

        teh = count * teh_per_unit
        op = teh * condition * profile["power_intensity_w_per_teh"]
        emb = teh * profile["embodied_energy_j_per_teh"] / (design_life * SECONDS_PER_YEAR)
        op_total += op
        emb_total += emb
        priced += count
        by_bucket.append({
            "index": i,
            "priced": True,
            "type": type_name,
            "operational_w": op * grid_kappa,
            "embodied_w": emb * grid_kappa,
            "phi_w": (op + emb) * grid_kappa,
        })

    return ThermalFloor(
        phi_operational_w=op_total * grid_kappa,
        phi_embodied_w=emb_total * grid_kappa,
        phi_total_w=(op_total + emb_total) * grid_kappa,
        grid_kappa=grid_kappa,
        coverage=(priced / counted if counted > 0.0 else 0.0),
        unpriced_buckets=unpriced,
        by_bucket=by_bucket,
    )
