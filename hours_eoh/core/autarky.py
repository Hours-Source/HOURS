"""
The autarky reference, the overbuild test, and the payback horizon.

A collective is a service apparatus. It exists to discharge an obligation its
members would otherwise discharge alone, and it is worth having only while it
costs less than doing so. This module makes that comparison a computable verdict
rather than an assumption.

    THE THREE QUANTITIES

    B₀    autarky reference — the obligation with NO apparatus, discharged alone.
          Personal at the autarky-referenced standard, plus ecological. Fixed:
          population × per-person obligation, exactly what an obligation is.
    B(K)  the obligation WITH an apparatus of size K. Lower than B₀, because
          infrastructure abates (a tap replaces hauling) — see
          eoh_generation.abatement_fraction.
    I(K)  the overhead the apparatus costs: infrastructure EOH plus the
          apparatus share of knowledge EOH.

    total(K) = B(K) + I(K)

    THE TWO TESTS, and they answer different questions

    obligation test   total(K) < B₀
        "all needs met effectively" — the apparatus removes more obligation than
        it creates. This is the demanding one and the goal.

    labour test       (1−ε)·total(K) < B₀
        "is the collective worth being in" — the apparatus plus its automation
        costs members fewer HOURS than autarky would. Weaker, because machines
        carry part of what remains.

    Equivalently the labour test is  I/B < ε/(1−ε): overhead may grow only as
    fast as automation earns the right to it.

WHY BOTH. A collective can pass the labour test and fail the obligation test —
it is worth being in, but only because automation is masking an apparatus that
is not carrying its own weight. Reporting one without the other hides that.

BOUNDARY CASE: with no apparatus at all (I = 0, a = 0) the collective is exactly
EQUIVALENT to autarky, not worse. The verdict is `neutral`, not `overbuilt`;
strict inequality matters at the origin.

TEMPORARY OVERBUILD IS REAL. Capital is built before it pays. `payback()`
integrates over an asset's design life instead of judging a single period, so
"overbuilt now, worth it over the life" is a decidable claim rather than an
excuse. A collective that never pays back is overbuilt in the sense that matters.

Layer: core/ — imports only data.py and other core/ modules. Pure, no I/O.
ε-coherence: the obligation test is ε-free by construction (it compares
obligations, not labour); the labour test is evaluated across the full arc and
relaxes monotonically as ε rises.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.eoh_generation import (
    abated_personal_base,
    abatement_fraction,
    ecological_eoh,
    infrastructure_eoh,
    knowledge_eoh_breakdown,
    personal_base_for,
    personal_eoh,
)
from hours_eoh.data import ABATEMENT_HALF_CAPITAL_TEH


class AutarkyReference(TypedDict):
    personal: float          # at the autarky-referenced standard, unabated
    ecological: float
    total: float             # B₀
    per_capita: float
    standard: str


def autarky_reference(
    population: float = 1_000_000.0,
    standard: str = "sufficiency",
    ecosystem_health: float = 0.70,
    age_distribution: dict[str, float] | None = None,
) -> AutarkyReference:
    """
    B₀ — the obligation with no apparatus, discharged alone.

    Personal EOH at the autarky-referenced standard (unabated, because there is
    no infrastructure to abate it) plus ecological EOH, which is owed to the land
    whatever the organisation and so is not reducible by forming a collective.

    Infrastructure and knowledge are deliberately ABSENT: with no apparatus there
    is nothing to maintain and no operating skill to renew. That is what makes
    this a reference rather than just another inventory.

    units: hours/year (and h/person·yr in `per_capita`).
    ε-behavior: none. B₀ is the fixed comparator every other quantity moves
    against — "population × per-person obligation", which is what an obligation
    is.

    Args:
        population: Total population (> 0).
        standard: "sufficiency" (default, F_a) or "survival" (S_a). "collapsed"
            is rejected — it is an already-abated value and cannot serve as the
            unabated reference.
        ecosystem_health: Ecosystem state ∈ [0, 1].
        age_distribution: Optional explicit age structure.

    Returns:
        AutarkyReference.

    Raises:
        ValueError: on non-positive population or standard="collapsed".

    Worked example (1M people, sufficiency, health 0.70):
        personal 2,213M + ecological 0.71M → B₀ ≈ 2,213 h/person·yr.
    """
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")
    if standard == "collapsed":
        raise ValueError(
            "'collapsed' is an abated value and cannot be the autarky reference; "
            "use 'sufficiency' (F_a) or 'survival' (S_a)"
        )
    p = personal_eoh(population, age_distribution, standard=standard)
    e = ecological_eoh(ecosystem_health)
    return AutarkyReference(
        personal=p, ecological=e, total=p + e,
        per_capita=(p + e) / population, standard=standard,
    )


class OverbuildCheck(TypedDict):
    epsilon: float
    autarky_reference: float          # B₀
    abatement: float                  # a(K)
    obligation_with_apparatus: float  # B(K)
    overhead: float                   # I(K)
    total: float                      # B(K) + I(K)
    net_vs_autarky: float             # B₀ − total  (> 0 = the goal)
    overhead_ratio: float             # I/B
    labour_threshold: float           # ε/(1−ε)
    labour_collective: float          # (1−ε)·total
    labour_autarky: float             # B₀
    labour_saved: float
    obligation_test: bool             # total < B₀ — all needs met effectively
    labour_test: bool                 # worth being in
    verdict: str                      # "pays" | "neutral" | "overbuilt"
    note: str


def overbuild_check(
    capital_stock_teh: float,
    population: float = 1_000_000.0,
    epsilon: float = 0.40,
    standard: str = "sufficiency",
    ecosystem_health: float = 0.70,
    capital_age_ratio: float = 0.50,
    knowledge_base_size: float = 1.0,
    knowledge_complexity_per_unit: float = 1.0,
    half_capital: float = ABATEMENT_HALF_CAPITAL_TEH,
) -> OverbuildCheck:
    """
    Is this collective carrying its own weight, or is it overhead?

    Governing comparisons (module docstring for why there are two):

        obligation test   B(K) + I(K)  <  B₀
        labour test       (1−ε)·(B(K) + I(K))  <  B₀   ⟺   I/B < ε/(1−ε)

    The verdict is on the OBLIGATION test, because that is the one that says the
    apparatus removes more than it creates. The labour test rides alongside and
    is reported separately: passing it while failing the obligation test means
    the collective is worth being in only because automation is masking an
    apparatus that does not pay for itself.

    units: hours/year throughout; ratios dimensionless.
    ε-behavior: `obligation_test` is ε-free; `labour_test` relaxes monotonically
    with ε, so a young collective can fail it and grow into passing.

    Args:
        capital_stock_teh: Total apparatus capital (TEH, ≥ 0).
        population: Total population (> 0).
        epsilon: Automation level ∈ [0, 1).
        standard: Autarky-referenced standard to compare against.
        ecosystem_health: Ecosystem state.
        capital_age_ratio: Mean asset age / design life.
        knowledge_base_size: Corpus size relative to the ε=0 reference.
        knowledge_complexity_per_unit: Measured complexity; drives the apparatus
            share of knowledge EOH.
        half_capital: K_half for the abatement curve.

    Returns:
        OverbuildCheck.

    Raises:
        ValueError: on negative capital, non-positive population, or ε outside
            [0, 1).

    Worked example (1M people, K = 1.9B TEH, ε = 0.40): a = 0.294, so the
    obligation falls from 2,213 to 1,563 h/person·yr while overhead adds 47.5 —
    total 1,610 against B₀ 2,213, so the apparatus removes far more than it
    costs and the verdict is `pays`.
    """
    if capital_stock_teh < 0.0:
        raise ValueError(f"capital_stock_teh must be ≥ 0, got {capital_stock_teh}")
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")
    if not 0.0 <= epsilon < 1.0:
        raise ValueError(f"epsilon must be in [0, 1), got {epsilon}")

    ref = autarky_reference(population, standard, ecosystem_health)
    b0 = ref["total"]

    k_pc = capital_stock_teh / population
    a = abatement_fraction(k_pc, half_capital)

    # B(K): the abated personal obligation, plus the unabatable ecological one.
    abated_base = abated_personal_base(k_pc, standard, half_capital)
    b_k = personal_eoh(population, base_rate=abated_base) + ref["ecological"]

    # I(K): infrastructure, plus the APPARATUS share of knowledge (the
    # civilisational share is a standing obligation and belongs in B, not I).
    infra = infrastructure_eoh(capital_stock_teh, capital_age_ratio)
    know = knowledge_eoh_breakdown(
        knowledge_base_size, complexity_per_unit=knowledge_complexity_per_unit)
    i_k = infra + know["apparatus"]

    total = b_k + i_k
    threshold = epsilon / (1.0 - epsilon)
    ratio = i_k / b_k if b_k > 0.0 else float("inf")
    labour_collective = (1.0 - epsilon) * total

    obligation_ok = total < b0
    # Strict, so the no-apparatus origin reads as equivalence rather than failure.
    labour_ok = labour_collective < b0

    if total < b0:
        verdict = "pays"
        note = (f"apparatus removes {(b0 - total) / population:.1f} h/person·yr more "
                f"than it costs — all needs met effectively")
    elif total == b0:
        verdict = "neutral"
        note = "apparatus exactly offsets itself — equivalent to autarky"
    else:
        verdict = "overbuilt"
        note = (f"apparatus costs {(total - b0) / population:.1f} h/person·yr MORE "
                f"than autarky: the overhead of the collective exceeds not having "
                f"one. Labour test "
                f"{'still passes on automation' if labour_ok else 'fails too'}.")

    return OverbuildCheck(
        epsilon=epsilon,
        autarky_reference=b0,
        abatement=a,
        obligation_with_apparatus=b_k,
        overhead=i_k,
        total=total,
        net_vs_autarky=b0 - total,
        overhead_ratio=ratio,
        labour_threshold=threshold,
        labour_collective=labour_collective,
        labour_autarky=b0,
        labour_saved=b0 - labour_collective,
        obligation_test=obligation_ok,
        labour_test=labour_ok,
        verdict=verdict,
        note=note,
    )


def break_even_epsilon(
    capital_stock_teh: float,
    population: float = 1_000_000.0,
    tol: float = 1e-6,
    **kwargs: float,
) -> float:
    """
    The lowest ε at which this apparatus is worth being in — the LABOUR test's
    crossing.

        (1−ε)·total(K) < B₀      ⟹      ε > 1 − B₀ / total(K)

    NOTE the comparator is B₀, the AUTARKY reference, not B(K). Those diverge
    once abatement exists — B(K) < B₀ is the whole point of the mechanism — and
    deriving against B(K) understates the collective's advantage and reports a
    break-even that is too high. (It did, until a test caught it.)

    Below it the collective demands more hours of its members than autarky would,
    and should dissolve rather than operate. That makes it a genuine LOWER bound
    on the corridor, alongside the survival floor — and a second reason a
    corridor can close.

    Returns 0.0 whenever the OBLIGATION test already passes: an apparatus that
    removes more than it costs is worth being in at every ε, including the
    no-apparatus origin, which is neutral rather than failing.

    units: dimensionless ε.

    Args:
        capital_stock_teh: Apparatus capital.
        population: Total population.
        tol: Bisection tolerance.
        **kwargs: Forwarded to overbuild_check (standard, ecosystem_health, …).

    Returns:
        ε_breakeven ∈ [0, 1).

    Worked example: at K = 1.9B TEH for 1M people the overhead ratio is 0.030,
    so ε_breakeven ≈ 0.030 — trivially cleared anywhere on the arc.
    """
    c = overbuild_check(capital_stock_teh, population, epsilon=0.0, **kwargs)  # type: ignore[arg-type]
    b0, total = c["autarky_reference"], c["total"]
    if total <= 0.0 or total <= b0:
        return 0.0
    return min(1.0 - tol, 1.0 - b0 / total)


class Payback(TypedDict):
    capital_teh: float
    annual_labour_saved: float
    design_life_years: float
    payback_years: float          # may be inf
    lifetime_saved: float
    lifetime_return: float        # lifetime_saved − capital
    pays_back_within_life: bool
    verdict: str


def payback(
    capital_stock_teh: float,
    population: float = 1_000_000.0,
    epsilon: float = 0.40,
    design_life_years: float = 40.0,
    **kwargs: float,
) -> Payback:
    """
    Does the apparatus pay back inside its design life? — the temporal test.

    Governing relations:

        annual_saved   = B₀ − (1−ε)·total(K)        [labour hours/year]
        payback_years  = K / annual_saved           [∞ if annual_saved ≤ 0]
        lifetime_saved = annual_saved · design_life
        lifetime_return = lifetime_saved − K

    Capital is built before it pays, so a point-in-time verdict of "overbuilt"
    may be correct today and wrong over the asset's life. This turns "the
    overbuild is temporary" from an excuse into a decidable claim: an apparatus
    that never pays back is overbuilt in the sense that matters, whatever a
    single period says.

    Both sides are in TEH-hours, which is what makes the ratio meaningful — the
    capital stock is denominated in verified labour-hours, so `payback_years` is
    "years of saved labour needed to repay the labour embodied in the apparatus".

    units: hours and years; `lifetime_return` in hours.
    ε-behavior: annual saving rises with ε (machines carry more of what remains),
    so payback shortens monotonically along the arc.

    Args:
        capital_stock_teh: Apparatus capital (TEH).
        population: Total population.
        epsilon: Automation level.
        design_life_years: Horizon over which the apparatus must repay (> 0).
        **kwargs: Forwarded to overbuild_check.

    Returns:
        Payback.

    Raises:
        ValueError: on non-positive design life.
    """
    if design_life_years <= 0.0:
        raise ValueError(
            f"design_life_years must be > 0, got {design_life_years}"
        )
    c = overbuild_check(capital_stock_teh, population, epsilon, **kwargs)  # type: ignore[arg-type]
    saved = c["labour_saved"]
    if saved <= 0.0:
        years = float("inf")
    else:
        years = capital_stock_teh / saved
    lifetime = saved * design_life_years
    within = years <= design_life_years

    if saved <= 0.0:
        verdict = ("NEVER PAYS BACK: the apparatus costs more labour than autarky "
                   "at this ε, so no horizon repays it")
    elif within:
        verdict = (f"pays back in {years:.1f} yr of a {design_life_years:.0f}-yr "
                   f"life; lifetime return {lifetime - capital_stock_teh:,.0f} TEH")
    else:
        verdict = (f"does NOT pay back within its {design_life_years:.0f}-yr life "
                   f"({years:.1f} yr needed) — temporary overbuild is only a "
                   f"defence when the horizon actually closes")

    return Payback(
        capital_teh=capital_stock_teh,
        annual_labour_saved=saved,
        design_life_years=design_life_years,
        payback_years=years,
        lifetime_saved=lifetime,
        lifetime_return=lifetime - capital_stock_teh,
        pays_back_within_life=within,
        verdict=verdict,
    )
