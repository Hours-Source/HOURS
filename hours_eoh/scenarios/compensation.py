"""
scenarios/compensation — WHICH MECHANISMS CAN COVER FOR EACH OTHER, AND WHERE.

The second-look review (§15, `notes/critique/2nd_look.txt`) warned that the
framework "could become unfalsifiable through complexity: if one mechanism
causes failure, another mechanism can compensate", and asked for an audit that
"identif[ies] mechanisms that can compensate for each other's failures". This is
that audit, as a knockout study on the shared path.

    For each ε, switch every subset of the named mechanisms ON (the rest OFF)
    and ask the verdict. The MINIMAL SUFFICIENT SETS are the subsets that pass
    with no passing proper subset. They classify the point:

      fails       no subset passes — nothing here stands it still
      unneeded    the empty set passes — the verdict needs none of them
      sole:<m>    one minimal set, one mechanism — a single point of failure
      redundant   several single mechanisms each suffice — they compensate
      joint       only sets of two or more pass — they are needed together
      mixed       anything else (both singletons and larger sets)

The verdict is `stationarity.stationarity_at`'s "stands still", read through its
own arguments, so a mechanism is a pair of keyword overrides — what it is ON and
OFF. `inflow_mechanisms()` ships the two TEH inflows: the levy and the GUF.

WHAT IT FOUND (2026-10-01, at 1M; `tests/scenarios/test_compensation.py`): the
levy and the GUF are REDUNDANT over ε ≈ 0–0.55 — either alone stands the
collective still — so a failure of one is covered there; the LEVY IS THE SOLE
mechanism over ≈ 0.56–0.97; and the top of the arc needs BOTH (JOINT). With
neither, nothing stands still anywhere.

REPORTING ONLY — nothing imports it. 2ⁿ subsets per ε: built for a handful of
mechanisms, not dozens.
"""

from __future__ import annotations

from hours_eoh.data import EPSILON_ARC_MAX

from itertools import combinations
from typing import Any, Callable, Mapping

from hours_eoh.scenarios.stationarity import stationarity_at

#: A mechanism: {"on": kwargs, "off": kwargs} for the verdict function.
Mechanism = Mapping[str, Mapping[str, Any]]


def inflow_mechanisms(guf_parcels: list[dict]) -> dict[str, Mechanism]:
    """The two TEH inflows `stationarity_at` reads: the levy and the GUF."""
    from hours_eoh.data import SUFF_LEVY_RATE
    return {
        "levy": {"on": {"levy_rate": SUFF_LEVY_RATE}, "off": {"levy_rate": 0.0}},
        "guf":  {"on": {"guf_parcels": guf_parcels}, "off": {"guf_parcels": None}},
    }


def _teh_stands_still(epsilon: float, **kw: Any) -> bool:
    return bool(stationarity_at(epsilon, **kw)["stationary"])


def minimal_sufficient_sets(
    epsilon: float,
    mechanisms: Mapping[str, Mechanism],
    verdict: Callable[..., bool] = _teh_stands_still,
    **common: Any,
) -> list[tuple[str, ...]]:
    """The subsets of `mechanisms` that pass at `epsilon` with no passing proper subset."""
    names = sorted(mechanisms)
    passing: list[frozenset[str]] = []
    for k in range(len(names) + 1):
        for subset in combinations(names, k):
            on = frozenset(subset)
            if any(p <= on for p in passing):
                continue                                  # a smaller set already passes
            kw = dict(common)
            for m in names:
                kw.update(mechanisms[m]["on" if m in on else "off"])
            if verdict(epsilon, **kw):
                passing.append(on)
    return [tuple(sorted(p)) for p in passing]


def classify(sets: list[tuple[str, ...]]) -> str:
    """Name the pattern of minimal sufficient sets (see the module docstring)."""
    if not sets:
        return "fails"
    if sets == [()]:
        return "unneeded"
    sizes = {len(s) for s in sets}
    if sizes == {1}:
        return f"sole:{sets[0][0]}" if len(sets) == 1 else "redundant"
    if 1 not in sizes:
        return "joint"
    return "mixed"


def compensation_map(
    mechanisms: Mapping[str, Mechanism],
    step: float = 0.01,
    verdict: Callable[..., bool] = _teh_stands_still,
    **common: Any,
) -> dict:
    """
    Classify every ε on a grid of `step` (a scan resolution, as in
    `stationarity.stationary_bands`) and group contiguous runs.

    Returns {"points": [(ε, class, minimal sets)], "runs": [(class, ε_lo, ε_hi)],
    "step"}. Run edges are accurate to `step`.
    """
    n = max(2, int(round(EPSILON_ARC_MAX / step)))
    points = []
    for i in range(n + 1):
        eps = min(EPSILON_ARC_MAX, i * EPSILON_ARC_MAX / n)
        sets = minimal_sufficient_sets(eps, mechanisms, verdict, **common)
        points.append((eps, classify(sets), sets))
    runs: list[list] = []
    for eps, cls, _ in points:
        if runs and runs[-1][0] == cls:
            runs[-1][2] = eps
        else:
            runs.append([cls, eps, eps])
    return {"points": points, "runs": [tuple(r) for r in runs], "step": step}
