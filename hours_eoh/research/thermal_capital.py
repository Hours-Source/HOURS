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
    INFRA_MAINT_RATE,
    INFRA_AGE_FACTOR_MAX,
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


# ---------------------------------------------------------------------------
# B3 — maintain vs replace, with the embodied-energy pulse
# ---------------------------------------------------------------------------

class MaintainReplace(TypedDict):
    strategy: str
    horizon_years: float
    human_eoh: float              # cumulative human-labour hours over the horizon
    operational_j: float          # integrated running dissipation
    embodied_j: float             # embodied energy actually SPENT in the horizon
    dissipation_j: float
    replacements: int
    mean_age_ratio: float


def _run_strategy(
    teh: float, design_life: float, start_age: float, horizon: float,
    replace_at: float, epsilon: float, base_maint_rate: float,
    age_factor_max: float, power_intensity: float, embodied_per_teh: float,
    grid_kappa: float, dt: float = 0.25,
) -> tuple[float, float, float, int, float]:
    """Step an asset through the horizon, replacing whenever it reaches
    `replace_at` years of age. Returns (human_eoh, operational_j, embodied_j,
    replacements, mean_age_ratio)."""
    age = start_age
    t = 0.0
    human = op = emb = 0.0
    reps = 0
    age_ratio_sum = 0.0
    steps = 0.0
    while t < horizon - 1e-12:
        step = min(dt, horizon - t)
        ratio = min(age / design_life, 1.0)
        age_factor = 1.0 + (age_factor_max - 1.0) * ratio
        # maintenance obligation rises with age; humans carry the (1-eps) share
        human += teh * base_maint_rate * age_factor * (1.0 - epsilon) * step
        # condition proxies utilisation, and declines linearly across design life
        condition = max(0.0, 1.0 - ratio)
        op += teh * condition * power_intensity * grid_kappa * SECONDS_PER_YEAR * step
        age_ratio_sum += ratio * step
        steps += step
        age += step
        t += step
        if age >= replace_at - 1e-12 and t < horizon - 1e-12:
            emb += teh * embodied_per_teh * grid_kappa    # the pulse, spent at replacement
            reps += 1
            age = 0.0
    return human, op, emb, reps, (age_ratio_sum / steps if steps else 0.0)


def maintain_vs_replace(
    capital_type: str,
    teh_value: float,
    current_age: float,
    horizon_years: float = 60.0,
    epsilon: float = 0.40,
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
    base_maint_rate: float = INFRA_MAINT_RATE,
    age_factor_max: float = INFRA_AGE_FACTOR_MAX,
) -> dict:
    """
    B3 — the first decision the thermal layer can actually inform.

    Infrastructure EOH rises with age (`age_factor` climbs toward
    `age_factor_max`), so replacing an asset cuts the maintenance obligation. But
    embodied energy is spent AT CONSTRUCTION, so every replacement is a
    dissipation PULSE. Replace early and you buy fewer labour-hours at the price
    of more pulses per century — F9 ("crash transition programmes are thermally
    worse") at asset scale rather than civilizational scale.

    Two strategies over one horizon:

        maintain  run each asset to its full design life, then replace
        replace   retire at `current_age`, then run on the same full-life cycle

    Both are stepped quarterly through the horizon, accumulating the rising
    maintenance obligation, the running dissipation (which falls as condition
    declines — see the caveat) and an embodied pulse at each replacement.

    THE EXCHANGE RATE is the output that matters: labour-hours saved per joule of
    extra dissipation. It is the first quantity in the framework that prices one
    domain's obligation against another's, and it is what a stewardship decision
    actually turns on.

    CAVEAT, stated rather than buried: the shipped thermal model treats condition
    as a UTILISATION proxy, so an aged asset draws less power because it does less
    work. Real equipment usually draws the same or more for less output — an
    efficiency decay this model does not carry. That biases the comparison AGAINST
    replacement (it under-credits the efficiency a new asset would bring), so the
    replace case here is a conservative floor.

    units: hours, joules, years. ε-behavior: human EOH scales with (1−ε);
    dissipation does not, so the exchange rate steepens as automation rises —
    labour saved becomes cheaper in hours and unchanged in joules.

    Returns:
        dict with both strategies, their difference, and the exchange rate.

    Raises:
        ValueError: for an unknown capital type, or a non-positive horizon.
    """
    if capital_type not in CAPITAL_MACHINE_PROFILES:
        raise ValueError(f"unknown capital type: {capital_type!r}")
    if horizon_years <= 0.0:
        raise ValueError(f"horizon_years must be positive, got {horizon_years}")
    tp = CAPITAL_THERMAL_PROFILES.get(capital_type)
    if tp is None:
        raise ValueError(f"no thermal profile for capital type: {capital_type!r}")

    design_life = float(CAPITAL_MACHINE_PROFILES[capital_type]["design_life"])
    current_age = max(0.0, min(current_age, design_life))
    out: dict[str, MaintainReplace] = {}
    # maintain: carry the existing asset to full design life before replacing
    h, o, e, r, ar = _run_strategy(
        teh_value, design_life, current_age, horizon_years, design_life, epsilon,
        base_maint_rate, age_factor_max, tp["power_intensity_w_per_teh"],
        tp["embodied_energy_j_per_teh"], grid_kappa)
    out["maintain"] = MaintainReplace(
        strategy="maintain", horizon_years=horizon_years, human_eoh=h,
        operational_j=o, embodied_j=e, dissipation_j=o + e, replacements=r,
        mean_age_ratio=ar)
    # replace: retire now, then the same full-life cycle from age zero
    h2, o2, e2, r2, ar2 = _run_strategy(
        teh_value, design_life, 0.0, horizon_years, design_life, epsilon,
        base_maint_rate, age_factor_max, tp["power_intensity_w_per_teh"],
        tp["embodied_energy_j_per_teh"], grid_kappa)
    e2 += teh_value * tp["embodied_energy_j_per_teh"] * grid_kappa   # the pulse spent today
    r2 += 1
    out["replace"] = MaintainReplace(
        strategy="replace", horizon_years=horizon_years, human_eoh=h2,
        operational_j=o2, embodied_j=e2, dissipation_j=o2 + e2, replacements=r2,
        mean_age_ratio=ar2)

    eoh_saved = out["maintain"]["human_eoh"] - out["replace"]["human_eoh"]
    extra_j = out["replace"]["dissipation_j"] - out["maintain"]["dissipation_j"]
    return {
        "capital_type": capital_type,
        "design_life_years": design_life,
        "current_age_years": current_age,
        "epsilon": epsilon,
        "strategies": out,
        "eoh_saved_by_replacing": eoh_saved,
        "extra_dissipation_j": extra_j,
        "exchange_rate_eoh_per_tj": (eoh_saved / (extra_j / 1e12)) if extra_j > 0 else None,
        "replacing_is_thermally_worse": extra_j > 0.0,
        "note": ("condition proxies utilisation in the shipped model, so an aged asset "
                 "draws less rather than costing more per unit output; the replace case "
                 "is therefore a conservative floor"),
    }


def replacement_exchange_curve(
    capital_type: str,
    teh_value: float,
    horizon_years: float = 40.0,
    epsilon: float = 0.40,
    ages: tuple[float, ...] | None = None,
    grid_kappa: float = THERMAL_GRID_KAPPA_DEFAULT,
) -> dict:
    """
    The exchange rate as a function of replacement age — the decision rule.

    Sweeps `maintain_vs_replace` across ages and reports labour-hours saved per
    terajoule of extra dissipation at each. The rate rises monotonically with
    age: replacing a nearly-worn asset buys the same relief for a far smaller
    thermal pulse, because the embodied energy already bought most of its service
    life.

    For a 30-year transportation asset over a 40-year horizon the rate runs from
    ~70 EOH/TJ at age 2 to ~170 at age 29 — **deferring replacement to end of
    life buys about 2.4x more labour relief per joule dissipated.**

    That is F9 at asset scale, and it is a rule a steward can act on: replacing
    early is not merely more expensive in capital, it is thermally worse, and the
    penalty is now priced rather than asserted.

    units: EOH per TJ. Returns the curve, the best age, and the ratio best/worst.
    """
    design_life = float(CAPITAL_MACHINE_PROFILES[capital_type]["design_life"])
    if ages is None:
        ages = tuple(round(design_life * f, 1) for f in (0.05, 0.2, 0.4, 0.6, 0.8, 0.95))
    rows = []
    for a in ages:
        r = maintain_vs_replace(capital_type, teh_value, a, horizon_years, epsilon, grid_kappa)
        rows.append({
            "age_years": a,
            "age_ratio": round(a / design_life, 3),
            "eoh_saved": r["eoh_saved_by_replacing"],
            "extra_dissipation_j": r["extra_dissipation_j"],
            "exchange_rate_eoh_per_tj": r["exchange_rate_eoh_per_tj"],
        })
    rated = [r for r in rows if r["exchange_rate_eoh_per_tj"] is not None]
    best = max(rated, key=lambda r: r["exchange_rate_eoh_per_tj"]) if rated else None
    worst = min(rated, key=lambda r: r["exchange_rate_eoh_per_tj"]) if rated else None
    return {
        "capital_type": capital_type,
        "design_life_years": design_life,
        "horizon_years": horizon_years,
        "curve": rows,
        "best_age_years": best["age_years"] if best else None,
        "best_over_worst": (best["exchange_rate_eoh_per_tj"] / worst["exchange_rate_eoh_per_tj"]
                            if best and worst and worst["exchange_rate_eoh_per_tj"] > 0 else None),
        "rule": ("replace at end of life, not before — the exchange rate rises with age, "
                 "so early replacement pays more joules for the same hours"),
    }
