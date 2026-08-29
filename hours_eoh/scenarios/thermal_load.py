"""
Thermal obligation carried through the ledger — reachability, and its scale.

The planetary radiative-capacity obligation is a real fourth term in ecological
EOH (`core.eoh_generation.ecological_eoh(..., thermal_obligation=)`), flowing on
into the TEH pipeline and the fiscal snapshot. But it defaults to 0.0 everywhere,
and before this scenario existed the only caller that ever set it non-zero was
`research/thermal_solvency`. So the framework's headline thermal result — that
civilization is ~510 TW over its radiative allowance and the ledger now carries
that debt — was not reachable from any default path: not `arc`, not `dashboard`,
not `simulate`, not any scenario.

This scenario carries it, and reports what carrying it does. The honest answer,
at shipped calibration, is: almost nothing.

    thermal flow at ε = 0.40, 1M people   ≈ 1.79e6 h/yr  =  1.8 h/person·yr
    ecological EOH, loaded                ≈ 2.5 h/person·yr
    personal EOH                          ≈ 1,478 h/person·yr

The obligation enters at roughly one part in a thousand of what the model already
says people owe to entropy. That is not a bug in the thermal layer — it is the
domain-balance defect (docs/parameter_provenance.md §"Domain balance"): the
ecological base rate is a documented RELATIVE anchor summed with absolute counts,
so the domain the obligation lands in is 0.03% of total EOH to begin with.

The consequence to keep in view: `research/thermal_solvency`'s verdict that the
fiscal system carries the obligation with a large margin passes because the
obligation is negligible, not because the fisc is strong. This scenario reports
the coverage ratio next to the load ratio so the two cannot be read apart.

Layer: scenarios/ imports core/ and data.py only. The obligation VALUE is a
research-tier quantity (research/thermal_drawdown → thermal_solvency), so it
enters here as a parameter rather than an import; `REFERENCE_THERMAL_FLOW_EOH`
records the reference figure and where it came from.

ε-coherence: exercised across ε ∈ [0, 0.99]; the obligation is ε-invariant by
construction (measured forcing is a direct observation, not a sensing artifact),
while the domains it is compared against move with ε.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.data import CAPITAL_STOCK_DEFAULT, TRUST_BASE_TEH

# Reference annual thermal obligation for a 1M-person collective at ε = 0.40,
# from research/thermal_solvency.solvency_at_epsilon(0.40)["thermal_flow_eoh"] —
# the drawdown-chain labour requirement at a 2.0 K threshold, allocated by
# responsibility. Tier D at root (CDR_LABOR_HOURS_PER_TONNE = 0.6); recorded here
# so the scenario is runnable without reaching into research/.
REFERENCE_THERMAL_FLOW_EOH: float = 1_789_175.0
REFERENCE_POPULATION: float = 1_000_000.0


class ThermalLoadRow(TypedDict):
    epsilon: float
    thermal_eoh: float               # the obligation carried (h/yr)
    ecological_baseline_eoh: float   # ecological EOH without it
    ecological_loaded_eoh: float     # ecological EOH with it
    # None once the partition empties the baseline — see the note at the
    # computation. A ratio with no denominator is not infinite, it is undefined.
    load_ratio: float | None         # loaded / baseline — how much it moves the DOMAIN
    total_eoh: float
    thermal_share_of_total: float    # how much it moves the LEDGER
    personal_share_of_total: float
    thermal_per_capita: float        # h/person·yr
    ecological_per_capita: float
    personal_per_capita: float
    teh_created: float
    solvent: bool
    coverage_margin: float | None    # levy capacity ÷ obligation cost


def thermal_load_arc(
    thermal_obligation: float = REFERENCE_THERMAL_FLOW_EOH,
    population: float = REFERENCE_POPULATION,
    arc: tuple[float, ...] = (0.0, 0.20, 0.40, 0.60, 0.80, 0.99),
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    ecosystem_health: float = 0.70,
) -> list[ThermalLoadRow]:
    """
    Carry a thermal obligation across the ε arc and report what it moves.

    Governing relations (all already in core/; this composes them):

        ecological_loaded = ecological_baseline + thermal_obligation
        load_ratio        = ecological_loaded / ecological_baseline
        thermal_share     = thermal_obligation / total_EOH

    The two ratios are the point. `load_ratio` is large (≈ 3.5× at defaults) —
    the obligation more than triples the ecological domain. `thermal_share` is
    tiny (< 0.1%) — because that domain is a rounding error in the total. A
    reader shown only the first would conclude the thermal layer had transformed
    the ledger; a reader shown only the second would conclude it was pointless.
    Both are true and they belong in the same table.

    units: EOH in hours/year; ratios dimensionless; per-capita in h/person·yr.
    ε-behavior: the obligation is ε-invariant by construction (measured forcing
    is an observation, not a sensing artifact), and with `ecosystem_health` held
    fixed the ecological baseline is too — so `load_ratio` is flat across the arc
    at 3.50×. `thermal_share_of_total` drifts down only because total EOH grows
    with ε (infrastructure and knowledge rise). Vary `ecosystem_health` to move
    the baseline; the obligation will not move with it.

    Args:
        thermal_obligation: Annual obligation in EOH-hours (≥ 0).
        population: Total population (> 0).
        arc: ε values to report.
        trust_balance: Trust corpus for the fiscal arm.
        capital_stock: Capital stock (TEH).
        ecosystem_health: Ecosystem state ∈ [0, 1].

    Returns:
        list[ThermalLoadRow], one per ε in `arc`.

    Raises:
        ValueError: if thermal_obligation < 0 or population <= 0.

    Worked example (defaults, ε = 0.40, 1M people):
        thermal_eoh          1,789,175 h/yr   →  1.79 h/person·yr
        ecological baseline    714,286 h/yr   →  0.71 h/person·yr
        load_ratio                 3.51       (the domain more than triples)
        thermal_share_of_total     0.0011     (the ledger barely notices)
        personal_share_of_total    0.91
    """
    if thermal_obligation < 0.0:
        raise ValueError(
            f"thermal_obligation must be ≥ 0, got {thermal_obligation}"
        )
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")

    rows: list[ThermalLoadRow] = []
    for eps in arc:
        # COMPUTED AT THE PRE-PARTITION POLICY, and the reason is the module's
        # question. `load_ratio` asks how much the thermal obligation moves the
        # ECOLOGICAL DOMAIN — which presupposes a domain to move. Phases 4e/4f
        # (adopted 2026-08-28/29) send both recurring ecological terms to GUF,
        # so under the shipped default the baseline is 0.0 and the comparison
        # is 0/0. Evaluating here where the baseline is live keeps the question
        # answerable; `thermal_share_of_total`, which measures the effect on the
        # LEDGER rather than on the domain, is unaffected either way.
        base = total_eoh(epsilon=eps, population=population,
                         capital_stock=capital_stock,
                         ecosystem_health=ecosystem_health,
                           ecological_standing_response="domain",
                           ecological_health_response="domain")
        loaded = total_eoh(epsilon=eps, population=population,
                           capital_stock=capital_stock,
                           ecosystem_health=ecosystem_health,
                           thermal_obligation=thermal_obligation,
                           ecological_standing_response="domain",
                           ecological_health_response="domain")
        pipeline = eoh_to_teh_pipeline(eps, population=population,
                                       capital_stock=capital_stock,
                                       ecosystem_health=ecosystem_health,
                                       thermal_obligation=thermal_obligation,
                                       ecological_standing_response="domain",
                         ecological_health_response="domain")
        teh_created = float(pipeline.get("teh_created", 0.0))
        snap = fiscal_snapshot(
            epsilon=eps,
            population=population,
            trust_balance=trust_balance,
            labor_income=teh_created,
            capital_stock_teh=capital_stock,
            capital_age_ratio=0.5,
            ecosystem_health=ecosystem_health,
            thermal_obligation=thermal_obligation,
            eco_eoh_override=loaded["ecological"],
        )
        eco_base = base["ecological"]
        eco_loaded = loaded["ecological"]
        # Coverage: what the ecological obligation costs in TEH, against the levy
        # take available to fund it. funding_coverage is the direct ratio.
        eco_required = float(snap.get("ecological", {}).get("teh_required", 0.0))
        levy = float(snap.get("levies", {}).get("total_levied", 0.0))
        rows.append(ThermalLoadRow(
            epsilon=eps,
            thermal_eoh=thermal_obligation,
            ecological_baseline_eoh=eco_base,
            ecological_loaded_eoh=eco_loaded,
            # THE DENOMINATOR IS GONE, AND None IS THE HONEST ANSWER.
            # This read `float("inf")` when the baseline was zero, which was a
            # correct guard while a zero baseline was an edge case. After Phase
            # 4e/4f (adopted 2026-08-28/29) it is the SHIPPED DEFAULT: the
            # ecological domain carries stocks only, none of which is supplied
            # by default, so `eco_base` is 0.0 on every ordinary run and `inf`
            # would be this module's headline figure.
            #
            # It is also the wrong QUESTION now. `load_ratio` asked "how much
            # does the thermal obligation move the ecological domain?" — but
            # under the partition the thermal obligation IS one of that domain's
            # stocks. It is not moving a baseline; it is the content. So the
            # ratio is undefined rather than enormous, and `None` says that
            # where `inf` implied a magnitude. `thermal_share_of_total` is
            # unaffected and carries the effect on the ledger.
            load_ratio=(eco_loaded / eco_base) if eco_base > 0 else None,
            total_eoh=loaded["total"],
            thermal_share_of_total=(thermal_obligation / loaded["total"]
                                    if loaded["total"] > 0 else 0.0),
            personal_share_of_total=(loaded["personal"] / loaded["total"]
                                     if loaded["total"] > 0 else 0.0),
            thermal_per_capita=thermal_obligation / population,
            ecological_per_capita=eco_loaded / population,
            personal_per_capita=loaded["personal"] / population,
            teh_created=teh_created,
            solvent=bool(snap.get("solvent", False)),
            # As for `load_ratio`: undefined, not infinite. Under the adopted
            # partition the Trust's ecological requirement is 0.0 by default —
            # the recurring obligation is GUF's — so there is nothing for the
            # levy to cover and the margin has no denominator.
            coverage_margin=(levy / eco_required) if eco_required > 0 else None,
        ))
    return rows


class ThermalLoadVerdict(TypedDict):
    thermal_obligation: float
    # None when no row had a non-zero baseline — the partition's default state.
    max_load_ratio: float | None     # largest effect on the ecological DOMAIN
    max_share_of_total: float        # largest effect on the LEDGER
    solvent_throughout: bool
    min_coverage_margin: float | None
    coverage_below_one_at: list[float]  # ε values where the levy cannot fund it
    negligible_in_ledger: bool       # share < 0.1% everywhere on the arc
    verdict: str
    rows: list[ThermalLoadRow]


def thermal_load_verdict(
    thermal_obligation: float = REFERENCE_THERMAL_FLOW_EOH,
    population: float = REFERENCE_POPULATION,
    negligible_threshold: float = 0.001,
    material_threshold: float = 0.01,
    **kwargs: float,
) -> ThermalLoadVerdict:
    """
    Roll `thermal_load_arc` into a single reportable verdict.

    `negligible_in_ledger` is the flag that matters and it is deliberately harsh:
    it is True when the obligation never reaches `negligible_threshold` (0.1% by
    default) of total EOH anywhere on the arc. At shipped calibration it is True,
    and a solvency verdict computed against a negligible obligation should be
    read as "the obligation is small", not "the fisc is strong".

    `coverage_below_one_at` is the second finding and it cuts the other way. The
    levy take covers the loaded ecological requirement 0.17× at ε=0 and 0.66× at
    ε=0.20 — the obligation is negligible in the ledger and STILL unaffordable at
    low automation, because labour income is what funds it and there is little of
    it. Coverage crosses 1 between ε=0.20 and 0.40 and reaches ≈10.7× at ε=0.99.
    The unloaded arc runs ≈3.5× higher at every point (0.59 → 37.5), which is the
    right comparison for any previously-quoted margin: those figures were taken
    without the obligation being carried.

    Args:
        thermal_obligation: Annual obligation in EOH-hours.
        population: Total population.
        negligible_threshold: Share of total EOH below which the obligation is
            reported as negligible in the ledger.
        **kwargs: Forwarded to thermal_load_arc (arc, trust_balance, …).

    Returns:
        ThermalLoadVerdict.
    """
    rows = thermal_load_arc(thermal_obligation, population, **kwargs)  # type: ignore[arg-type]
    _ratios = [r["load_ratio"] for r in rows if r["load_ratio"] is not None]
    max_load = max(_ratios) if _ratios else None
    max_share = max(r["thermal_share_of_total"] for r in rows)
    solvent = all(r["solvent"] for r in rows)
    _covs = [r["coverage_margin"] for r in rows if r["coverage_margin"] is not None]
    min_cov = min(_covs) if _covs else None
    under = [r["epsilon"] for r in rows
             if r["coverage_margin"] is not None and r["coverage_margin"] < 1.0]
    negligible = max_share < negligible_threshold

    # THE LOAD RATIO MAY HAVE NO DENOMINATOR. After Phases 4e/4f the ecological
    # domain carries stocks only and none ships by default, so `max_load` is
    # None on every ordinary run. Rendered as a phrase rather than a number so
    # the verdict stays readable and never claims a magnitude it does not have.
    _load = (f"multiplies the ecological domain by {max_load:.2f}×"
             if max_load is not None else
             "lands in an ecological domain that is EMPTY by default — the "
             "recurring obligation is GUF's under the adopted partition, so "
             "there is no baseline to multiply")

    if not negligible and max_share < material_threshold:
        # MARGINAL: above the negligible line but nowhere near material. Added
        # 2026-08-06 because a binary line reads badly at 0.12% — the obligation
        # did not grow, the DENOMINATOR shrank (PERSONAL_EOH_BASE 1500 → 1000),
        # and calling that "material" would overstate it as badly as calling it
        # negligible would understate it.
        verdict = (
            f"MARGINAL: the obligation {_load}; it reaches "
            f"{max_share:.3%} of total EOH — above "
            f"the {negligible_threshold:.1%} negligible line but far below "
            f"materiality. Note it crossed that line because the personal "
            f"domain was repriced, not because the obligation grew."
        )
    elif negligible:
        verdict = (
            f"CARRIED BUT NEGLIGIBLE IN THE LEDGER: the obligation {_load}; "
            f"it never exceeds "
            f"{max_share:.4%} of total EOH. The domain it lands in is a rounding "
            f"error, so a passing solvency verdict here is evidence that the "
            f"obligation is small, not that the fisc is strong. See "
            f"docs/parameter_provenance.md §'Domain balance'."
        )
    else:
        verdict = (
            f"MATERIAL: the obligation reaches {max_share:.2%} of total EOH "
            f"({_load})."
        )

    if under:
        verdict += (
            f" COVERAGE GAP: the levy take falls short of the loaded ecological "
            f"requirement at ε ∈ {[round(e, 2) for e in under]} "
            f"(minimum {min_cov:.2f}×) — at low automation the obligation is "
            f"small in the ledger and still unaffordable, because labour income "
            f"is what funds it and there is little of it."
        )
    else:
        verdict += f" Minimum coverage margin {min_cov:.1f}×."

    return ThermalLoadVerdict(
        thermal_obligation=thermal_obligation,
        max_load_ratio=max_load,
        max_share_of_total=max_share,
        solvent_throughout=solvent,
        min_coverage_margin=min_cov,
        coverage_below_one_at=under,
        negligible_in_ledger=negligible,
        verdict=verdict,
        rows=rows,
    )
