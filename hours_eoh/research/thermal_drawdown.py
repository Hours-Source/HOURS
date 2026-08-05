"""
Thermal Sink EOH — the drawdown chain: from a forcing reduction to the labor
that would deliver it.

The overage (research/thermal_overage.py) says how far over the radiative
allowance civilization sits and what forcing reduction would close it. This
module converts that reduction into EOH — the step that would make the thermal
layer generate obligation rather than merely report a bound.

    ΔF required  →  Δppm  →  net GtCO₂  →  gross GtCO₂  →  joules  →  EOH
       (§10.1)     (Myhre-  (atmospheric  (sink          (plant    (ι_drawdown)
                    form)     mass)        reversal)      energy)

WHY A CHAIN AND NOT A CONSTANT. The handoff's ι ladder would have this be one
lumped J/EOH figure. Five separately-tiered steps are more auditable: the gate's
sensitivity lands on named quantities that can be sourced independently, and a
reader can see which link is load-bearing. Two links carry real provenance
(the forcing coefficient is derived from the shipped IGCC series; the ppm→mass
conversion falls out of atmospheric mass); three are placeholders and say so.

ι IS DERIVED, NOT ASSUMED. Rather than a third free placeholder,

    ι_drawdown = energy per tonne / labor-hours per tonne          [J/EOH]

so the framework's ι is a function of two plant observables — both of which a
real CDR operator publishes. At the shipped defaults ι ≈ 6.7e9 J/EOH, some four
orders above the infrastructure ι floor, which is the expected direction:
drawdown is energy-intensive and labor-thin.

THE HONEST WEAK LINKS, in order of leverage:
  1. ι_drawdown (Tier D via two Tier C/D observables) — sets the answer linearly.
  2. CDR_GROSS_REMOVAL_FACTOR (Tier D) — omitting it would understate the
     obligation ~2× and bias the solvency gate toward PASSING. It is included
     precisely because the error it prevents is the one that flatters us.
  3. CDR_ENERGY_GJ_PER_TONNE (Tier C) — recalled DAC range 2–6, and held
     CONSTANT as concentration falls. Real capture costs more energy per tonne
     from more dilute air, so the chain flatters deep cuts; the forcing law
     works the other way (removal is more forcing-effective at low
     concentration), and the two are not netted here.

SIMPLIFICATION, stated rather than buried: the chain assumes the whole forcing
reduction is delivered by CO₂ drawdown. Non-CO₂ greenhouse reductions would be
cheaper per W·m⁻², while losing fossil aerosol cooling works against you. The
net direction of that pair is not established here, so the chain is neither
conservative nor optimistic by construction — it is CO₂-only, and labelled.

ADVISORY. Producing an EOH figure is not the same as generating obligation.
Nothing here writes to a ledger; wiring the result into ecological EOH is gated
on the fiscal solvency check (research/thermal_solvency.py, next), because the
ecological baseline is ~610K h/yr at population 1M and ecological allocation is
a co-equal Trust obligation.

Layer: research/ — experimental, unstable API, not imported by core/ or
scenarios/.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from hours_eoh.data import (
    CDR_ALLOCATION_BASIS,
    CDR_RESPONSIBILITY_BASIS,
    CDR_UNATTRIBUTED_POLICY,
    CDR_ENERGY_GJ_PER_TONNE,
    CDR_GROSS_REMOVAL_FACTOR,
    CDR_LABOR_HOURS_PER_TONNE,
    CO2_CONCENTRATION_PPM,
    CO2_FORCING_COEFFICIENT,
    CO2_PPM_TO_GT,
    SECONDS_PER_YEAR,
)
from hours_eoh.research.thermal_overage import forcing_required_for_zero

_GJ_TO_J = 1.0e9
_GT_TO_TONNES = 1.0e9

#: Per-step provenance, shipped with every chain so no figure travels without it.
DRAWDOWN_TIERS: dict[str, str] = {
    "co2_forcing_coefficient": "A — OLS on the IGCC 2025a CO₂ ERF series, 350–426 ppm",
    "co2_concentration_ppm": "A — IGCC 2025a annual mean, 2025",
    "ppm_to_gt": "B — atmospheric mass × molar ratio; derivable",
    "gross_removal_factor": "D — placeholder; ESM CDR reversibility would resolve",
    "energy_per_tonne": "C — DAC-order, recalled range 2–6 GJ/t",
    "labor_hours_per_tonne": "D — placeholder; operator staffing disclosures would resolve",
    "iota_drawdown": "derived — energy per tonne ÷ labor-hours per tonne",
}


class DrawdownChain(TypedDict):
    delta_t_max: float
    forcing_reduction: float      # ΔF to be delivered (W·m⁻²)
    ppm_reduction: float          # concentration drop required
    concentration_target: float   # resulting ppm
    net_mass_gt: float            # CO₂ removed from the air
    gross_mass_gt: float          # tonnage actually processed (sink reversal)
    energy_j: float               # programme energy
    iota_drawdown: float          # J per EOH (derived)
    eoh_global: float             # the whole job, hours
    eoh_share: float              # this collective's share, hours
    population_share: float
    feasible: bool                # is the forcing reduction within removable forcing?
    tiers: dict[str, str]


def iota_drawdown(
    energy_gj_per_tonne: float = CDR_ENERGY_GJ_PER_TONNE,
    labor_hours_per_tonne: float = CDR_LABOR_HOURS_PER_TONNE,
) -> float:
    """
    ι_drawdown (J per EOH) — derived, not assumed.

        ι = ( energy per tonne ) / ( labor-hours per tonne )

    Both inputs are things a CDR operator publishes, so the framework's ι becomes
    calibratable from plant data rather than being a third free placeholder. The
    shipped defaults give ≈ 6.7e9 J/EOH.

    units: J·EOH⁻¹. ε-behavior: none — a technology coefficient, not an arc
    quantity.

    Raises:
        ValueError: if labor_hours_per_tonne is not positive (an infinitely
            automated drawdown generates no obligation, which is a claim the
            caller should have to make explicitly rather than reach by dividing
            by zero).
    """
    if labor_hours_per_tonne <= 0.0:
        raise ValueError(
            f"labor_hours_per_tonne must be positive, got {labor_hours_per_tonne}"
        )
    return energy_gj_per_tonne * _GJ_TO_J / labor_hours_per_tonne


def forcing_to_ppm_reduction(
    delta_f: float,
    concentration_ppm: float = CO2_CONCENTRATION_PPM,
    coefficient: float = CO2_FORCING_COEFFICIENT,
) -> float:
    """
    The concentration drop that delivers a forcing reduction (ppm).

        C_target = C_now · exp( −ΔF / k )
        Δppm     = C_now − C_target

    k is DERIVED from the shipped IGCC series over 350–426 ppm rather than taken
    from Myhre's 5.35, which runs 5.2% low across that range. The fit
    self-validates: its intercept implies a pre-industrial 279.8 ppm against the
    accepted 278.

    Logarithmic, so the same ΔF costs progressively FEWER ppm the lower you go:
    the first 0.5 W·m⁻² takes 36.1 ppm, the second only 33.0. Removal is more
    forcing-effective at lower concentration, so in mass terms a drawdown gets
    cheaper per W·m⁻² as it proceeds.

    The practical difficulty runs the other way — capturing from more dilute air
    costs more energy per tonne — and this chain holds energy per tonne CONSTANT,
    so it flatters deep cuts. The two effects are not netted here; the flattering
    one is in `CDR_ENERGY_GJ_PER_TONNE`, and a concentration-dependent capture
    energy is the fix when that constant leaves Tier C.

    units: ppm. Worked example: ΔF = 1.0 W·m⁻² from 425.65 ppm → 356.5 ppm, a
    69.1 ppm reduction (Myhre's coefficient would say 72.6 — a 5% overstatement).

    Raises:
        ValueError: if the coefficient or concentration is not positive.
    """
    if coefficient <= 0.0 or concentration_ppm <= 0.0:
        raise ValueError("coefficient and concentration must be positive")
    return concentration_ppm - concentration_ppm * math.exp(-delta_f / coefficient)


def ppm_to_gross_mass_gt(
    ppm_reduction: float,
    ppm_to_gt: float = CO2_PPM_TO_GT,
    gross_factor: float = CDR_GROSS_REMOVAL_FACTOR,
) -> tuple[float, float]:
    """
    The CO₂ tonnage a concentration drop requires — net and gross (GtCO₂).

        net   = Δppm · GtCO₂-per-ppm
        gross = net · gross_factor

    The gross factor is the link most easily left out and the one whose omission
    flatters the result: pulling CO₂ out of the air lets ocean and land sinks
    OUTGAS back toward equilibrium, so the tonnage processed exceeds the
    concentration drop achieved. Leaving it at 1.0 understates the obligation
    roughly twofold.

    units: GtCO₂. Worked example: 69.1 ppm → 540 Gt net → 973 Gt gross at 1.8.
    """
    net = ppm_reduction * ppm_to_gt
    return net, net * gross_factor


def drawdown_job(
    delta_t_max: float,
    population_share: float = 1.0,
    phi_w: float | None = None,
    energy_gj_per_tonne: float = CDR_ENERGY_GJ_PER_TONNE,
    labor_hours_per_tonne: float = CDR_LABOR_HOURS_PER_TONNE,
    gross_factor: float = CDR_GROSS_REMOVAL_FACTOR,
    concentration_ppm: float = CO2_CONCENTRATION_PPM,
    coefficient: float = CO2_FORCING_COEFFICIENT,
    ppm_to_gt: float = CO2_PPM_TO_GT,
) -> DrawdownChain:
    """
    The full chain: from a habitability threshold to the EOH that closing the
    overage would take.

        ΔF (thermal_overage.forcing_required_for_zero)
          → Δppm  → net Gt → gross Gt → joules → EOH = joules / ι_drawdown

    Returns the global job and a collective's share of it. The share is a
    POPULATION share by default, which is a governance choice wearing physics
    clothing: allocating the drawdown obligation by head is one option, by
    cumulative emissions (responsibility) another, and by present emissions a
    third. They differ by more than an order of magnitude for some collectives.
    The parameter is deliberately a bare fraction so the choice has to be made
    explicitly upstream rather than being smuggled in as a default.

    units: hours (EOH). ε-behavior: enters only through the overage's Φ term,
    which is ~1% of the reduction at defensible thresholds — so the drawdown job
    is essentially ε-invariant, which is itself the finding: this obligation is
    owed regardless of how far automation has run.

    Worked example (ΔT_max = 2.0 K, whole world): ΔF = 1.001 → 69.2 ppm →
    541 Gt net → 974 Gt gross → 3.9e21 J → 5.8e11 EOH.

    Args:
        delta_t_max: assessed habitability threshold (K, GMST).
        population_share: this collective's share of the global job ∈ [0, 1].
        phi_w: net-additive dissipation (W); defaults to the measured world Φ.
            Pass thermal_overage.phi_at_epsilon(ε) to exercise the arc — the job
            barely moves, which is the point.
        energy_gj_per_tonne, labor_hours_per_tonne: the two plant observables
            that derive ι_drawdown.
        gross_factor: sink-reversal multiplier on tonnage.
        concentration_ppm, coefficient, ppm_to_gt: the forcing→mass chain.

    Returns:
        DrawdownChain, with per-step provenance tiers attached.

    Raises:
        ValueError: if population_share is outside [0, 1].
    """
    if not 0.0 <= population_share <= 1.0:
        raise ValueError(f"population_share must be in [0, 1], got {population_share}")

    zero = forcing_required_for_zero(delta_t_max, phi_w)
    delta_f = max(0.0, zero["reduction_required"])
    ppm_drop = forcing_to_ppm_reduction(delta_f, concentration_ppm, coefficient)
    net_gt, gross_gt = ppm_to_gross_mass_gt(ppm_drop, ppm_to_gt, gross_factor)
    energy = gross_gt * _GT_TO_TONNES * energy_gj_per_tonne * _GJ_TO_J
    iota = iota_drawdown(energy_gj_per_tonne, labor_hours_per_tonne)
    eoh_global = energy / iota

    return DrawdownChain(
        delta_t_max=delta_t_max,
        forcing_reduction=delta_f,
        ppm_reduction=ppm_drop,
        concentration_target=concentration_ppm - ppm_drop,
        net_mass_gt=net_gt,
        gross_mass_gt=gross_gt,
        energy_j=energy,
        iota_drawdown=iota,
        eoh_global=eoh_global,
        eoh_share=eoh_global * population_share,
        population_share=population_share,
        feasible=zero["feasible"],
        tiers=dict(DRAWDOWN_TIERS),
    )


def drawdown_power(chain: DrawdownChain, programme_years: float) -> dict:
    """
    The drawdown programme's OWN dissipation, and whether it self-defeats.

        Φ_programme = energy / ( programme_years · Δt_s )

    Powered at κ > 0 the programme adds to Φ while the forcing it removes falls,
    so a fossil- or nuclear-powered drawdown partly fights itself. Reported as a
    ratio to the overage being closed: above 1.0 the programme dissipates more
    than the overage it is clearing, which does not by itself mean failure — the
    energy is transient and the forcing reduction permanent — but it does mean
    the PATH matters and the peak may breach even though the endpoint does not.

    That is F8 ("steerable by τ yet unable to steer — the maneuver breaches the
    wall") in concrete form. Settling it needs the multi-period engine (P5); this
    function reports the ratio, not the verdict.

    units: watts, dimensionless ratios. Faster programmes are thermally worse for
    a fixed job — which is F9 ("crash transition programs are thermally worse")
    falling out of the same arithmetic.

    Raises:
        ValueError: if programme_years is not positive.
    """
    if programme_years <= 0.0:
        raise ValueError(f"programme_years must be positive, got {programme_years}")
    from hours_eoh.research.thermal_overage import thermal_overage

    phi_programme = chain["energy_j"] / (programme_years * SECONDS_PER_YEAR)
    overage = thermal_overage(chain["delta_t_max"])["overage_w"]
    return {
        "programme_years": programme_years,
        "phi_programme_w": phi_programme,
        "overage_w": overage,
        "ratio_to_overage": phi_programme / overage if overage > 0.0 else float("inf"),
        "self_defeating_at_kappa_1": overage > 0.0 and phi_programme > overage,
    }


# ---------------------------------------------------------------------------
# How the global job is split across collectives
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_cumulative_emissions() -> dict:
    """The shipped cumulative-CO2 table (reference/data/cumulative_emissions.json).

    OWID / Global Carbon Budget, 1750–2024, 215 collectives. Read `_basis_choice`
    and `_truncation_warning` before citing any share."""
    path = Path(__file__).resolve().parents[1] / "reference" / "data" / "cumulative_emissions.json"
    with path.open(encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


@lru_cache(maxsize=4)
def _attributed_total(basis: str) -> float:
    key = f"share_{basis}"
    return sum(r[key] for r in load_cumulative_emissions()["collectives"].values()
               if r[key] is not None)


def responsibility_share(
    collective: str,
    basis: str = CDR_RESPONSIBILITY_BASIS,
    unattributed: str = CDR_UNATTRIBUTED_POLICY,
) -> float | None:
    """
    A collective's share of cumulative CO₂ — the responsibility allocation weight.

    `basis` selects "incl_luc" (default: fossil + cement + land-use change, the
    whole atmospheric burden the drawdown must remove) or "fossil" (fossil +
    cement only, lower uncertainty but leaving ~33% of the burden unallocated).

    `unattributed` decides what happens to emissions belonging to no territory —
    international shipping and aviation, 46 GtCO₂ or 2.49% of the cumulative
    fossil total. Under "pro_rata" (default) they are redistributed in proportion
    to existing shares, so shares sum to 1 and every part of the obligation has a
    bearer. Under "unallocated" the raw shares are returned and the commons
    silently absorbs the remainder.

    Returns None for an unknown collective rather than guessing, so a caller
    falls back explicitly instead of silently receiving a zero share.

    units: dimensionless share ∈ [0, 1].

    Raises:
        ValueError: on an unknown basis or unattributed policy.
    """
    if basis not in ("fossil", "incl_luc"):
        raise ValueError(f"unknown responsibility basis: {basis!r}")
    if unattributed not in ("pro_rata", "unallocated"):
        raise ValueError(f"unknown unattributed policy: {unattributed!r}")
    rec = load_cumulative_emissions()["collectives"].get(collective)
    if rec is None:
        return None
    raw = rec[f"share_{basis}"]
    if raw is None:
        return None
    if unattributed == "unallocated":
        return raw
    total = _attributed_total(basis)
    return raw / total if total > 0.0 else raw


def allocation_share(
    population: float,
    world_population: float,
    cumulative_emissions_t: float | None = None,
    world_cumulative_emissions_t: float | None = None,
    basis: str = CDR_ALLOCATION_BASIS,
    collective: str | None = None,
    responsibility_basis: str = CDR_RESPONSIBILITY_BASIS,
    unattributed: str = CDR_UNATTRIBUTED_POLICY,
) -> dict:
    """
    A collective's share of the global drawdown job.

    This is a GOVERNANCE decision wearing physics clothing, and the framework
    takes a position on it (2026-08-05, author's call):

        responsibility — share ∝ cumulative emissions. A collective cannot
                         burden others with the consequences of choices it made.
                         The DEFAULT.
        population     — share ∝ headcount. Simpler, and it silently transfers
                         the cost of one collective's history onto everyone.

    The two differ by more than an order of magnitude for some collectives, so
    the choice is not a detail; it is most of the answer for anyone who is not
    near the world average.

DOCTRINE (2026-08-05). The framework is built to work going forward, not to be a
    complete record of the past. Records are biased toward whoever kept
    documentation, so the more history an allocation demands, the more it
    privileges the well-documented; a line has to be drawn or there is no end to
    how far back one goes. Looking back sets a starting point, not a verdict.
    That is why emissions belonging to no territory are redistributed rather than
    left unowned, and why land converted inside a collective counts as that
    collective's regardless of the demand that motivated it — the world we
    inherited is the world as it is. Both are arguments worth having in a live
    implementation; neither is resolved by the model.

    RESOLVED 2026-08-05. Pass `collective` and the share is looked up in the shipped
    1750–2024 table (reference/data/cumulative_emissions.json, OWID / Global
    Carbon Budget). Explicit emissions figures still override it. Without either,
    this falls back to population and SAYS SO in `basis_used` and `caveat` — it
    does not quietly substitute one rule for the other.

    Truncation is not a small error: measured against a 1965+ fossil-energy proxy,
    the UK is under-charged 1.70× and Germany 1.31×, while Singapore is
    over-charged 4.1×. A cumulative basis that does not reach 1750 mis-ranks
    exactly the collectives the rule exists to charge.

    units: dimensionless share ∈ [0, 1].

    Returns:
        dict with `share`, `basis_used`, `requested_basis`, and `caveat`.

    Raises:
        ValueError: on a non-positive world population, or an unknown basis.
    """
    if world_population <= 0.0:
        raise ValueError(f"world_population must be positive, got {world_population}")
    if basis not in ("responsibility", "population"):
        raise ValueError(f"unknown allocation basis: {basis!r}")

    pop_share = min(1.0, population / world_population)

    # A named collective resolves against the shipped 1750–2024 table, so callers
    # need not carry emissions figures around.
    if basis == "responsibility" and collective is not None and cumulative_emissions_t is None:
        share = responsibility_share(collective, responsibility_basis, unattributed)
        if share is not None:
            return {"share": share, "basis_used": "responsibility",
                    "requested_basis": basis, "caveat": None,
                    "responsibility_basis": responsibility_basis}

    if basis == "population":
        return {"share": pop_share, "basis_used": "population",
                "requested_basis": basis, "caveat": None,
                "responsibility_basis": None}

    if (cumulative_emissions_t is None
            or world_cumulative_emissions_t is None
            or world_cumulative_emissions_t <= 0.0):
        return {
            "share": pop_share,
            "basis_used": "population",
            "requested_basis": "responsibility",
            "caveat": ("responsibility weighting requested but cumulative emissions "
                       "were not supplied — fell back to population share, which "
                       "under-charges high-emitting collectives"),
            "responsibility_basis": None,
        }
    return {
        "share": min(1.0, cumulative_emissions_t / world_cumulative_emissions_t),
        "basis_used": "responsibility",
        "requested_basis": basis,
        "caveat": None,
        "responsibility_basis": responsibility_basis,
    }
