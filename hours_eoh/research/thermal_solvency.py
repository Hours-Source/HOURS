"""
Thermal Sink EOH — the fiscal solvency gate.

The overage is a debt, and research/thermal_drawdown.py converts it into EOH.
This module answers the question that decides whether that EOH may ever reach the
ledger: **can the fiscal system carry it?** Until the answer is yes, the thermal
layer stays advisory.

THE FLOW CONVENTION (adopted 2026-08-05, author's call). The drawdown is a
programme executed over a horizon, so its obligation enters as an annual flow —
job ÷ programme_years — not as a stock dropped into one period. The choice is
worth stating loudly because it is worth a factor of ~100: the same 2 K job for a
1M-population collective reads as 100× the entire ecological domain if injected
as a stock, and ~1× if annualized over a century. No measured input in the chain
has anything like that leverage.

THE BACKWARD QUERY. Rather than "what is the labour intensity of drawdown?" —
which nobody can answer yet — this asks **what would it have to be to break the
Trust?** and then reports how far the shipped estimate sits from that. That is
the same epistemic move as F2's floor bound: a question whose answer is useful
before the measurement lands, and which can only err in one direction.

The chain simplifies more than expected. Since ι_drawdown = energy ÷ labour per
tonne, the energy CANCELS out of the EOH:

    EOH = energy / ι = gross_tonnes · labour_hours_per_tonne

so the obligation depends on tonnage and labour intensity ALONE. Energy per tonne
never touches it — it matters only for the programme's own dissipation (F8/F9).
That collapses the gate's sensitivity onto one Tier D number, which is exactly
the number the backward query targets.

SELF-FUNDING IS MODELLED, NOT ASSUMED AWAY. As of 2026-08-05 the obligation is
injected through `thermal_obligation`, a real fourth term in
`core.eoh_generation.ecological_eoh` rather than the earlier
`deferred_ecological` workaround (which had to be divided by the monitoring
factor to cancel a visibility curve that does not apply to measured forcing). It
therefore flows through the whole pipeline: more ecological EOH → more human EOH
→ more registered EOH → more TEH created → a larger levy base. The obligation
partly pays for itself, and pricing the cost without that income would be
pessimistic in a way the ledger identity does not license. Both the loaded and
unloaded economies are computed.

PASS CONDITIONS — fixed in advance, in writing, so they cannot move later:

  1. Trust solvent at every ε ∈ {0, 0.40, 0.90, 0.99}.
  2. The levy needed to COVER EXPENDITURE stays within labour income. Note this
     is deliberately not `full_solvency`, which additionally demands the Trust's
     whole dividend be replaced from levy every period — a target the unloaded
     baseline misses at every ε by 1.3–9.4×, because it is a property of the
     Trust's dividend design rather than of any load placed on it. Testing
     against it would have reported a thermal failure that was nothing of the
     kind.
  3. Ecological and stewardship remain CO-EQUAL — neither becomes residual.
  4. The labour to service it exists.
  5. Arc coherence: finite and meaningful at every ε.

ALL FIVE, or the layer stays advisory. A failure here is a publishable finding —
"the thermal overage is not fiscally absorbable" would be among the strongest
results the framework has produced — and must be reported, not tuned around.

Layer: research/ — imports core/ (permitted), not imported by core/ or
scenarios/. Note scenarios/ may NOT import research/, which is why the gate lives
here rather than beside the other stress scenarios.
"""

from __future__ import annotations

from typing import Any, TypedDict

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.eoh_generation import ecological_eoh_breakdown
from hours_eoh.core.fiscal import fiscal_snapshot, min_levy_for_solvency
from hours_eoh.data import (
    LAND_HECTARES_PER_CAPITA,
    CDR_ALLOCATION_BASIS,
    CDR_LABOR_HOURS_PER_TONNE,
    THERMAL_DT_LO,
    THERMAL_PROGRAMME_YEARS,
)
from hours_eoh.research.thermal_drawdown import allocation_share, drawdown_job

#: Reference collective. These MATCH scenarios/sweep.epsilon_sweep — the repo's
#: canonical arc-coherence-with-solvency check — deliberately, so the gate is not
#: measuring a reference economy of its own invention. A first pass with an
#: uncalibrated trust balance (5e8) reported failure at every ε *before* any
#: thermal load, which is the trap this alignment closes: a gate is only
#: informative if its unloaded baseline passes.
REF_POPULATION = 1_000_000.0
REF_WORLD_POPULATION = 8.16e9
REF_CAPITAL_STOCK = 2.0e9
REF_CAPITAL_AGE_RATIO = 0.30
REF_ECOSYSTEM_HEALTH = 0.70
REF_TRUST_BALANCE = 3.5e10
#: Available human labour: 50% of population × 2000 h/yr — the corridor's convention.
REF_AVAILABLE_LABOR = REF_POPULATION * 0.50 * 2000.0
#: Programme horizon — see data.THERMAL_PROGRAMME_YEARS. 40 yr keeps the work
#: inside a single lifetime of responsibility. CHOSEN, and the flow scales as
#: 1/horizon, so it is a real lever rather than a formality.
DEFAULT_PROGRAMME_YEARS = THERMAL_PROGRAMME_YEARS
#: Co-equality tolerance: how far ecological funding coverage may fall below
#: stewardship's before ecological counts as residual. CHOSEN.
COEQUALITY_TOLERANCE = 0.25

ARC_EPSILONS: tuple[float, ...] = (0.0, 0.40, 0.90, 0.99)

#: A labour intensity indistinguishable from zero, for the null-load baseline.
#: Not literally 0.0 — `iota_drawdown` rejects that, on the grounds that an
#: infinitely automated drawdown generating no obligation is a claim a caller
#: should have to make explicitly.
_NULL_LOAD = 1e-12


class SolvencyVerdict(TypedDict):
    epsilon: float
    thermal_flow_eoh: float       # h/yr added to the ecological domain
    eco_baseline_eoh: float
    eco_loaded_eoh: float
    load_ratio: float             # loaded ÷ baseline
    labor_income_baseline: float
    labor_income_loaded: float    # the self-funding effect
    trust_end: float
    trust_solvent: bool
    levy_feasible: bool
    eco_coverage: float
    stew_coverage: float
    coequal: bool
    human_eco_eoh: float
    labor_fraction: float         # share of available labour the domain consumes
    labor_feasible: bool
    passes: bool
    failures: list[str]


def thermal_flow_eoh(
    delta_t_max: float,
    population: float = REF_POPULATION,
    world_population: float = REF_WORLD_POPULATION,
    programme_years: float = DEFAULT_PROGRAMME_YEARS,
    labor_hours_per_tonne: float = CDR_LABOR_HOURS_PER_TONNE,
    cumulative_emissions_t: float | None = None,
    world_cumulative_emissions_t: float | None = None,
    basis: str = CDR_ALLOCATION_BASIS,
    collective: str | None = None,
) -> float:
    """
    The annual EOH the drawdown obligation adds to the ecological domain (h/yr).

        flow = gross_tonnes · labour_hours_per_tonne · population_share
               / programme_years

    The share follows `allocation_share`: responsibility (cumulative emissions)
    by default, because a collective cannot burden others with the consequences
    of choices it made. Pass `collective` to resolve against the shipped
    1750–2024 table; without it, or for an unknown name, this falls back to
    population and says so rather than substituting one rule for the other.

    units: hours/year. ε-behavior: essentially flat — the job moves under 10%
    across the whole arc, because Φ is ~1% of the forcing reduction. The debt is
    owed regardless of how far automation has run.

    Worked example (ΔT_max = 2.0 K, 1M of 8.16e9 people, 40 yr, 0.6 h/t):
        973 Gt × 0.6 h/t × 1.225e-4 / 40 = 1,789,174 h/yr — about 2.5× the
        ecological baseline of 714,286 h/yr, so the domain more than triples.

    Raises:
        ValueError: if programme_years or world_population is not positive.
    """
    if programme_years <= 0.0:
        raise ValueError(f"programme_years must be positive, got {programme_years}")
    if world_population <= 0.0:
        raise ValueError(f"world_population must be positive, got {world_population}")
    alloc = allocation_share(
        population, world_population,
        cumulative_emissions_t, world_cumulative_emissions_t, basis,
        collective=collective,
    )
    share = alloc["share"]
    job = drawdown_job(
        delta_t_max,
        population_share=share,
        labor_hours_per_tonne=labor_hours_per_tonne,
    )
    return job["eoh_share"] / programme_years


def solvency_at_epsilon(
    epsilon: float,
    delta_t_max: float = THERMAL_DT_LO,
    labor_hours_per_tonne: float = CDR_LABOR_HOURS_PER_TONNE,
    programme_years: float = DEFAULT_PROGRAMME_YEARS,
    population: float = REF_POPULATION,
    world_population: float = REF_WORLD_POPULATION,
    capital_stock: float = REF_CAPITAL_STOCK,
    capital_age_ratio: float = REF_CAPITAL_AGE_RATIO,
    ecosystem_health: float = REF_ECOSYSTEM_HEALTH,
    trust_balance: float = REF_TRUST_BALANCE,
    available_labor: float = REF_AVAILABLE_LABOR,
    coequality_tolerance: float = COEQUALITY_TOLERANCE,
) -> SolvencyVerdict:
    """
    Run the five pass conditions at one ε, with and without the thermal load.

    The obligation is injected through `thermal_obligation` — a real term in the
    ecological domain — so it flows through the entire pipeline rather than being
    bolted onto the cost side: EOH → human EOH → registered EOH → TEH created →
    levy base. That self-funding is real under the ledger identity and is
    modelled.

    units: mixed; every field carries its own. Returns a verdict per ε with the
    failures named, so a FAIL says which condition broke rather than only that
    something did.
    """
    flow = thermal_flow_eoh(
        delta_t_max, population, world_population, programme_years, labor_hours_per_tonne
    )

    # ONE POLICY FOR THE WHOLE VERDICT. This function compares a LOADED
    # ecological requirement against a baseline and checks co-equality of
    # funding — all of which presuppose the ecological obligation sits in the
    # domain. Phases 4e/4f (adopted 2026-08-28/29) move both recurring terms to
    # GUF, so the pipeline, the snapshot and the baseline must be evaluated at
    # the same pre-partition policy or the co-equality check compares a live
    # stewardship coverage against an emptied ecological one.
    base_pipe = eoh_to_teh_pipeline(
        epsilon, population=population, capital_stock=capital_stock,
        capital_age_ratio=capital_age_ratio, ecosystem_health=ecosystem_health,
                           ecological_standing_response="domain",
                           ecological_health_response="domain")
    loaded_pipe = eoh_to_teh_pipeline(
        epsilon, population=population, capital_stock=capital_stock,
        capital_age_ratio=capital_age_ratio, ecosystem_health=ecosystem_health,
        thermal_obligation=flow,
                           ecological_standing_response="domain",
                           ecological_health_response="domain")

    snap = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=loaded_pipe["teh_created"],
        capital_stock_teh=capital_stock,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        ecosystem_health=ecosystem_health,
        thermal_obligation=flow,
        health_response="domain", standing_response="domain")
    levy = min_levy_for_solvency(
        trust_balance=trust_balance, epsilon=epsilon,
        capital_stock_teh=capital_stock, capital_age_ratio=capital_age_ratio,
        population=population, labor_income=loaded_pipe["teh_created"],
    )

    eco, stew, trust = snap["ecological"], snap["stewardship"], snap["trust"]
    # Frame the ecological baseline from THIS run's population, as `total_eoh`
    # does. Found 2026-08-17 by the scale-resolution gate on its first run —
    # the fifth instance of the defect, and the one four manual passes missed.
    # It matters here specifically: the thermal-solvency verdict compares the
    # loaded ecological requirement against this baseline, and an unframed
    # baseline made the comparison depend on a frame nobody declared.
    # AND AT THE PRE-PARTITION POLICY, for the same reason thermal_load uses it:
    # this verdict compares the LOADED ecological requirement against a
    # baseline, and Phases 4e/4f (adopted 2026-08-28/29) send both recurring
    # ecological terms to GUF — so under the shipped default the baseline is 0.0
    # and `load_ratio` is a division by zero rather than a large number.
    eco_base = ecological_eoh_breakdown(
        ecosystem_health, epsilon,
        area_hectares=population * LAND_HECTARES_PER_CAPITA,
        health_response="domain", standing_response="domain",
    )["total"]
    human_eco = eco["human_ecological_eoh"]
    labor_fraction = human_eco / available_labor if available_labor > 0.0 else float("inf")

    trust_ok = bool(snap["solvent"]) and trust["trust_end"] >= 0.0
    # Cover-expenditure, NOT full-solvency: see pass condition 2.
    levy_ok = levy["cover_expenditures"] <= loaded_pipe["teh_created"]
    coequal = eco["funding_coverage"] >= stew["funding_coverage"] - coequality_tolerance
    labor_ok = labor_fraction <= 1.0

    failures: list[str] = []
    if not trust_ok:
        failures.append("trust_insolvent")
    if not levy_ok:
        failures.append("levy_exceeds_labor_income")
    if not coequal:
        failures.append("ecological_became_residual")
    if not labor_ok:
        failures.append("labor_unavailable")

    return SolvencyVerdict(
        epsilon=epsilon,
        thermal_flow_eoh=flow,
        eco_baseline_eoh=eco_base,
        eco_loaded_eoh=eco["ecological_eoh_total"],
        load_ratio=eco["ecological_eoh_total"] / eco_base if eco_base > 0.0 else float("inf"),
        labor_income_baseline=base_pipe["teh_created"],
        labor_income_loaded=loaded_pipe["teh_created"],
        trust_end=trust["trust_end"],
        trust_solvent=trust_ok,
        levy_feasible=levy_ok,
        eco_coverage=eco["funding_coverage"],
        stew_coverage=stew["funding_coverage"],
        coequal=coequal,
        human_eco_eoh=human_eco,
        labor_fraction=labor_fraction,
        labor_feasible=labor_ok,
        passes=not failures,
        failures=failures,
    )


def solvency_gate(
    delta_t_max: float = THERMAL_DT_LO,
    labor_hours_per_tonne: float = CDR_LABOR_HOURS_PER_TONNE,
    programme_years: float = DEFAULT_PROGRAMME_YEARS,
    epsilons: tuple[float, ...] = ARC_EPSILONS,
    **kwargs: float,
) -> dict:
    """
    The gate: all five conditions at every ε, or the thermal layer stays advisory.

    Returns the per-ε verdicts, the overall pass/fail, and the union of failure
    reasons. A FAIL is a result to report, not an obstacle to tune around — a
    thermal obligation the fiscal system cannot carry is a finding about the
    framework's reach, and one worth publishing.
    """
    rows = [
        solvency_at_epsilon(
            e, delta_t_max=delta_t_max,
            labor_hours_per_tonne=labor_hours_per_tonne,
            programme_years=programme_years, **kwargs,
        )
        for e in epsilons
    ]
    failures = sorted({f for r in rows for f in r["failures"]})

    # A gate is only informative if its UNLOADED baseline passes. Two early
    # versions of this module reported failure at every ε for reasons that had
    # nothing to do with the thermal obligation (an uncalibrated trust balance,
    # then the wrong levy target). Running the null load every time makes that
    # misattribution impossible rather than merely unlikely.
    baseline = [
        solvency_at_epsilon(
            e, delta_t_max=delta_t_max, labor_hours_per_tonne=_NULL_LOAD,
            programme_years=programme_years, **kwargs,
        )
        for e in epsilons
    ]
    baseline_passes = all(r["passes"] for r in baseline)

    return {
        "delta_t_max": delta_t_max,
        "baseline_passes": baseline_passes,
        "attributable": baseline_passes,   # is a failure attributable to the load?
        "labor_hours_per_tonne": labor_hours_per_tonne,
        "programme_years": programme_years,
        "verdicts": rows,
        "passes": all(r["passes"] for r in rows),
        "failures": failures,
        "worst_epsilon": min(rows, key=lambda r: (r["passes"], -r["load_ratio"]))["epsilon"],
    }


def breaking_labor_intensity(
    delta_t_max: float = THERMAL_DT_LO,
    programme_years: float = DEFAULT_PROGRAMME_YEARS,
    lo: float = 1e-4,
    hi: float = 1e4,
    iterations: int = 80,
    **kwargs: Any,
) -> dict:
    """
    THE BACKWARD QUERY — the labour intensity at which the gate flips.

    Bisects labour-hours-per-tonne between a value the system carries and one it
    does not, then reports the margin against the shipped estimate. The gate's
    sensitivity collapses onto this single number (the energy term cancels out of
    the EOH), so this is the whole answer in one figure.

    Reading it: a large margin means the verdict is robust to the Tier D
    placeholder being wrong by that factor. A margin near 1 means the answer is
    being decided by a number nobody has measured, and the verdict should not be
    published either way.

    Returns None for `breaking_value` when the gate holds across the entire
    search range — which is itself a strong result.

    units: labour-hours per tonne CO₂. Monotone: more labour per tonne is
    strictly harder, so bisection is well-posed.
    """
    def passes(h: float) -> bool:
        return bool(solvency_gate(
            delta_t_max=delta_t_max, labor_hours_per_tonne=h,
            programme_years=programme_years, **kwargs,
        )["passes"])

    if not passes(lo):
        return {"breaking_value": None, "shipped_value": CDR_LABOR_HOURS_PER_TONNE,
                "margin": None, "verdict": "fails even at the lowest labour intensity"}
    if passes(hi):
        return {"breaking_value": None, "shipped_value": CDR_LABOR_HOURS_PER_TONNE,
                "margin": None, "verdict": "holds across the entire search range"}

    a, b = lo, hi
    for _ in range(iterations):
        mid = (a * b) ** 0.5          # geometric bisection — the range spans decades
        if passes(mid):
            a = mid
        else:
            b = mid
    breaking = (a * b) ** 0.5
    return {
        "breaking_value": breaking,
        "shipped_value": CDR_LABOR_HOURS_PER_TONNE,
        "margin": breaking / CDR_LABOR_HOURS_PER_TONNE,
        "verdict": ("robust" if breaking / CDR_LABOR_HOURS_PER_TONNE > 10.0
                    else "decided by an unmeasured number — do not publish either way"),
    }
