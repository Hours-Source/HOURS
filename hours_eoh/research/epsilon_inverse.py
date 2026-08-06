"""
The ε inverse — sweep physical state, not ε.

ε is the framework's central invariant and its central embarrassment: CLAUDE.md
states that ε is "a physical observable... not a policy lever; it is a score the
economy produces", and then every sweep in the repo sets it by hand. The two
cannot both be true. This module closes the gap by inverting the derivation
instead of bypassing it.

    capital_for_epsilon(target)  →  the capital stock whose DERIVED ε is target

so a sweep's coordinate becomes "the economy that produces this ε" and ε stays an
output everywhere. `core.civilization.civilization_epsilon` remains the only
thing that says what ε is.

WHY A SOLVER AND NOT A FORMULA. ε = machine_EOH / total_EOH, and capital appears
in both: more capital eliminates more EOH, and also generates more infrastructure
EOH to maintain. There is no closed form, but ε is monotone in the capital scale
and saturates at 1, so bisection is well-posed and cheap.

NON-UNIQUENESS IS THE POINT, NOT A DEFECT. Many capital mixes produce the same ε
with different stock, different maintenance burden, and different dissipation. A
sweep indexed by ε alone hides that; `mix_spread` measures it. It matters most
for the thermal layer, where Φ is a function of the capital, NOT of ε — two
economies at ε = 0.6 with different mixes sit at different thermal utilization.
That is precisely the divergence CLAUDE.md warns ε-as-input conceals.

Layer: research/ — graduates to core/trajectory.py beside the other arc helpers
once the mix parameterisation settles. Until then callers are in experimental
territory, and `canonical_physical_state(ε)` remains the shipped arc reference.
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.core.civilization import civilization_epsilon

#: A balanced reference mix — relative shares of capital TEH by type. Shares are
#: CHOSEN, not measured; they exist so a sweep has a definite economy behind it
#: rather than a bare number. Real deployments pass their own inventory.
REFERENCE_MIX: dict[str, float] = {
    "power_grid": 0.20,
    "water_treatment": 0.10,
    "medical_systems": 0.10,
    "agricultural_automation": 0.10,
    "industrial_automation": 0.20,
    "transportation": 0.15,
    "computing_ai": 0.10,
    "building": 0.05,
}

#: Contrasting mixes, for measuring how much of a result is the mix rather than ε.
COMPUTE_HEAVY_MIX: dict[str, float] = {
    "computing_ai": 0.45, "power_grid": 0.25, "industrial_automation": 0.15,
    "transportation": 0.10, "building": 0.05,
}
INFRASTRUCTURE_HEAVY_MIX: dict[str, float] = {
    "building": 0.30, "transportation": 0.25, "water_treatment": 0.20,
    "power_grid": 0.20, "computing_ai": 0.05,
}

DEFAULT_POPULATION = 1_000_000.0
DEFAULT_AGE = 10.0
DEFAULT_CONDITION = 0.85


class CapitalForEpsilon(TypedDict):
    target_epsilon: float
    epsilon_achieved: float
    reachable: bool
    scale_teh_per_capita: float
    total_capital_teh: float
    capital: dict
    iterations: int


def _build(mix: dict[str, float], scale: float, population: float,
           age: float, condition: float) -> dict:
    return {name: {"teh_value": share * scale * population,
                   "age": age, "condition": condition}
            for name, share in mix.items()}


def epsilon_at_scale(
    scale: float,
    mix: dict[str, float] | None = None,
    population: float = DEFAULT_POPULATION,
    age: float = DEFAULT_AGE,
    condition: float = DEFAULT_CONDITION,
) -> float:
    """
    The DERIVED ε for a capital stock of `scale` TEH per capita in a given mix.

    A thin, honest wrapper: it builds an economy and asks
    `civilization_epsilon` what ε that economy has. Nothing here sets ε.

    units: TEH per capita in, dimensionless ε out. ε(0) = 0 exactly — no capital,
    no machine fulfilment.
    """
    if scale < 0.0:
        raise ValueError(f"scale must be non-negative, got {scale}")
    mix = mix or REFERENCE_MIX
    civ = {"population": population,
           "capital": _build(mix, scale, population, age, condition)}
    return float(civilization_epsilon(civ)["epsilon"])


def capital_for_epsilon(
    target_epsilon: float,
    mix: dict[str, float] | None = None,
    population: float = DEFAULT_POPULATION,
    age: float = DEFAULT_AGE,
    condition: float = DEFAULT_CONDITION,
    tol: float = 1e-4,
    max_iter: int = 200,
) -> CapitalForEpsilon:
    """
    THE INVERSE — the capital stock whose derived ε equals the target.

    Bisects the capital scale over a FIXED mix. ε is monotone in scale (more
    capital eliminates more EOH than it creates) and saturates at 1, so the
    bracket is found by doubling and the root by bisection.

    Use this instead of passing ε as an input: the sweep coordinate becomes an
    economy, and ε is still whatever `civilization_epsilon` derives from it. The
    returned `epsilon_achieved` is the derived value, not the target — check it.

    units: ε dimensionless; scale in TEH per capita.

    ε-behavior: defined on (0, 1). ε = 0 returns an empty stock exactly. Targets
    at or above the saturation point are flagged `reachable=False` with the best
    achievable ε rather than silently returning a huge stock.

    Worked example (reference mix, population 1e6): ε = 0.40 needs roughly
    6,700 TEH per capita, i.e. a total stock near 6.7e9 TEH.

    Raises:
        ValueError: if target_epsilon is outside [0, 1).
    """
    if not 0.0 <= target_epsilon < 1.0:
        raise ValueError(f"target_epsilon must be in [0, 1), got {target_epsilon}")
    mix = mix or REFERENCE_MIX
    if target_epsilon == 0.0:
        return CapitalForEpsilon(
            target_epsilon=0.0, epsilon_achieved=0.0, reachable=True,
            scale_teh_per_capita=0.0, total_capital_teh=0.0, capital={}, iterations=0)

    lo, hi, iters = 0.0, 1.0, 0
    while epsilon_at_scale(hi, mix, population, age, condition) < target_epsilon:
        hi *= 2.0
        iters += 1
        if hi > 1e12:
            achieved = epsilon_at_scale(hi, mix, population, age, condition)
            return CapitalForEpsilon(
                target_epsilon=target_epsilon, epsilon_achieved=achieved, reachable=False,
                scale_teh_per_capita=hi, total_capital_teh=hi * population,
                capital=_build(mix, hi, population, age, condition), iterations=iters)

    for _ in range(max_iter):
        iters += 1
        mid = 0.5 * (lo + hi)
        e = epsilon_at_scale(mid, mix, population, age, condition)
        if abs(e - target_epsilon) <= tol:
            lo = hi = mid
            break
        if e < target_epsilon:
            lo = mid
        else:
            hi = mid
    scale = 0.5 * (lo + hi)
    return CapitalForEpsilon(
        target_epsilon=target_epsilon,
        epsilon_achieved=epsilon_at_scale(scale, mix, population, age, condition),
        reachable=True,
        scale_teh_per_capita=scale,
        total_capital_teh=scale * population,
        capital=_build(mix, scale, population, age, condition),
        iterations=iters,
    )


def mix_spread(
    target_epsilon: float,
    mixes: dict[str, dict[str, float]] | None = None,
    population: float = DEFAULT_POPULATION,
) -> dict:
    """
    How much of a result is the ε, and how much is the economy behind it.

    Solves the inverse for several mixes at ONE ε and reports the spread in
    capital stock and the quantities that follow from it. A sweep indexed by ε
    alone reports the same number for all of these; they are not the same economy.

    This matters most where a downstream quantity depends on capital rather than
    on ε — the thermal layer above all, since Φ is a property of the inventory.
    Two collectives at the same ε with different mixes carry different dissipation
    and therefore different thermal utilization.

    units: TEH; ratios dimensionless.

    Returns:
        dict with per-mix results and `capital_spread` — the max/min ratio of
        total capital across mixes at the same ε.
    """
    mixes = mixes or {"reference": REFERENCE_MIX,
                      "compute_heavy": COMPUTE_HEAVY_MIX,
                      "infrastructure_heavy": INFRASTRUCTURE_HEAVY_MIX}
    rows = {}
    for name, mix in mixes.items():
        r = capital_for_epsilon(target_epsilon, mix, population)
        rows[name] = {
            "scale_teh_per_capita": round(r["scale_teh_per_capita"], 1),
            "total_capital_teh": r["total_capital_teh"],
            "epsilon_achieved": round(r["epsilon_achieved"], 5),
            "reachable": r["reachable"],
        }
    totals = [v["total_capital_teh"] for v in rows.values() if v["reachable"]]
    return {
        "target_epsilon": target_epsilon,
        "mixes": rows,
        "capital_spread": (max(totals) / min(totals)) if totals and min(totals) > 0 else None,
        "note": ("the same ε, different economies. A downstream quantity that depends on "
                 "capital rather than ε — infrastructure EOH, Φ, thermal utilization — "
                 "differs by this factor across mixes at one ε."),
    }
