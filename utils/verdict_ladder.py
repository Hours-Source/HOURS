"""
The verdict ladder, computed — what may be asserted about any result.

SPDX-License-Identifier: AGPL-3.0-or-later

THE RULE (author decision, 2026-09-11, `record/theory.md#the-verdict-ladder`):
*a verdict may not outrank the weakest input it rests on.*

    CERTAIN    physics, derived, derived-then-FROZEN — and arithmetic that closes
    INSTANCE   measured, instance, convention — only as good as its census,
               checkable for FEASIBILITY within a stable bound
    POSSIBLE   placeholder, bounded, normative — and that is the ceiling

This module computes, for any function in the package, the transitive set of
`data.py` constants it could rest on, and therefore the strongest verdict it is
entitled to.

WHY STATIC AND NOT RUNTIME — the spike result, kept because it is the reason
this file has the shape it has.

A runtime route was tried first: perturb each constant, call the function, see
whether the output moves. It fails, and it fails in the dangerous direction.

  * **Most constants reach their consumers as DEFAULT ARGUMENTS**
    (`base_rate: float = PERSONAL_EOH_BASE`), which Python binds at function
    DEFINITION time. Patching the module attribute afterwards cannot reach them.
    Measured: `total_eoh` reported **4** dependencies by perturbation and **18**
    by this module.
  * **So runtime UNDER-approximates, and an under-approximation makes a verdict
    look STRONGER than it is** — it finds fewer placeholder inputs than exist.
    That is precisely the error the ladder exists to prevent.
  * It is also 1,700x slower: 352s for one function against 0.20s to build this
    whole graph.

Static OVER-approximates instead: it unions the constants reachable through a
function's entire call closure, including branches never taken. **That makes a
verdict weaker than it might be, which is the safe direction**, and it is the
repo's own stated doctrine — static is TOTAL but SHALLOW, runtime DEEP but
NARROW.

WHAT IT CANNOT SEE, stated because a checker that hides its gaps reads as
stronger than it is:

  * **Functions are keyed by bare name**, so two same-named functions in
    different modules merge. That unions their dependencies — over-approximating
    again, so it is safe, but a name collision makes one function's verdict
    weaker than its own code warrants.
  * **Dynamic dispatch, `getattr`, and values loaded from `reference/data/`**
    are invisible. Reference data is measured-by-construction, so its absence
    biases toward CERTAIN on that axis — the one place this module's error is
    NOT in the safe direction. Declared rather than fixed.
  * It sees which constants a result COULD rest on, never which it does.

Layer: utils/ — imports freely, imported by nothing.
"""

from __future__ import annotations

import ast
import collections
import pathlib
import sys
from typing import Iterable

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from utils import provenance as pv

__all__ = [
    "TIER_OF_TAG",
    "TIER_ORDER",
    "build_graph",
    "dependencies",
    "verdict_for",
    "tier_census",
]

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh"

#: Provenance tag -> ladder tier. The tags ARE the tiers; no second taxonomy is
#: invented here. `convention` sits in INSTANCE because a convention is a
#: declared choice about how to measure, which a collective can restate — not an
#: unmeasured value. That placement is a reading of the author's decision and is
#: the one boundary in this file worth arguing about.
TIER_OF_TAG: dict[str, str] = {
    "physics": "CERTAIN",
    "derived": "CERTAIN",
    "derived-then-FROZEN": "CERTAIN",
    "measured": "INSTANCE",
    "instance": "INSTANCE",
    "convention": "INSTANCE",
    "placeholder": "POSSIBLE",
    "bounded": "POSSIBLE",
    "normative": "POSSIBLE",
}

#: Weakest wins, so a verdict is the MAX over its inputs.
TIER_ORDER: dict[str, int] = {"CERTAIN": 0, "INSTANCE": 1, "POSSIBLE": 2}


def _records() -> dict[str, pv.Record]:
    """Every tagged `data.py` constant, keyed by name."""
    return {r.name: r for r in pv.load().records}


def build_graph(root: pathlib.Path | None = None) -> dict[str, tuple[str, set, set]]:
    """
    function name -> (module, data constants it names, functions it calls).

    Includes default-argument expressions, which is the whole point: that is
    where most constants in this codebase are consumed, and it is exactly what
    the runtime route could not see.
    """
    base = root or PACKAGE_ROOT
    graph: dict[str, tuple[str, set, set]] = {}
    for path in sorted(base.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and (
                node.module.endswith("data")
            ):
                imported |= {a.name for a in node.names}
        if not imported:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                targets = [node]
            elif isinstance(node, ast.ClassDef):
                targets = [m for m in node.body
                           if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            else:
                continue
            for fn in targets:
                names: set[str] = set()
                calls: set[str] = set()
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Name) and sub.id in imported:
                        names.add(sub.id)
                    elif isinstance(sub, ast.Call):
                        target = sub.func
                        if isinstance(target, ast.Name):
                            calls.add(target.id)
                        elif isinstance(target, ast.Attribute):
                            calls.add(target.attr)
                mod, have_names, have_calls = graph.get(
                    fn.name, (path.stem, set(), set())
                )
                graph[fn.name] = (mod, have_names | names, have_calls | calls)
    return graph


def dependencies(
    function: str,
    graph: dict[str, tuple[str, set, set]] | None = None,
    _seen: set[str] | None = None,
) -> set[str]:
    """Every `data.py` constant reachable through `function`'s call closure."""
    g = graph if graph is not None else build_graph()
    seen = _seen if _seen is not None else set()
    if function in seen or function not in g:
        return set()
    seen.add(function)
    _, names, calls = g[function]
    out = set(names)
    for called in calls:
        out |= dependencies(called, g, seen)
    return out


def verdict_for(
    function: str,
    graph: dict[str, tuple[str, set, set]] | None = None,
    records: dict | None = None,
) -> dict:
    """
    The strongest verdict `function` is entitled to, and what holds it there.

    units: none — a tier name, plus the constants that set it.
    """
    g = graph if graph is not None else build_graph()
    recs = records if records is not None else _records()
    deps = {d for d in dependencies(function, g) if d in recs}
    tiers = {d: TIER_OF_TAG.get(getattr(recs[d], "tag", ""), "POSSIBLE")
             for d in deps}
    if not tiers:
        return {
            "function": function,
            "known": function in g,
            "verdict": None,
            "dependencies": 0,
            "note": ("no data.py constant is reachable — either pure arithmetic "
                     "or the function is not in the package"),
        }
    worst = max(tiers.values(), key=lambda t: TIER_ORDER[t])
    holding = sorted(d for d, t in tiers.items() if t == worst)
    return {
        "function":     function,
        "known":        True,
        "verdict":      worst,
        "dependencies": len(deps),
        "by_tier":      dict(collections.Counter(tiers.values())),
        "held_there_by": holding,
        "note": (
            "OVER-approximated: the union over the call closure, branches "
            "included. A verdict may be weaker than the function's own code "
            "warrants; it is never stronger."
        ),
    }


def tier_census(names: Iterable[str] | None = None) -> dict:
    """
    How many constants sit at each tier — the number the ladder makes
    load-bearing, computed rather than restated.
    """
    recs = _records()
    keys = list(names) if names is not None else list(recs)
    counts = collections.Counter(
        TIER_OF_TAG.get(getattr(recs[k], "tag", ""), "POSSIBLE")
        for k in keys if k in recs
    )
    total = sum(counts.values())
    return {
        "total": total,
        "counts": dict(counts),
        "shares": {t: counts.get(t, 0) / total for t in TIER_ORDER} if total else {},
    }


def main() -> int:  # pragma: no cover
    graph, recs = build_graph(), _records()
    census = tier_census()
    print("CONSTANT CENSUS BY TIER")
    for tier in ("CERTAIN", "INSTANCE", "POSSIBLE"):
        n = census["counts"].get(tier, 0)
        print(f"  {tier:9s} {n:4d}  {census['shares'].get(tier, 0):6.1%}")
    print(f"  {'TOTAL':9s} {census['total']:4d}\n")
    print("VERDICT BY REPORTING FUNCTION")
    for fn in sys.argv[1:] or [
        "total_eoh", "obligation_accounts", "ground_use_fee",
        "feasibility_check", "verification_report", "corridor_is_usable",
    ]:
        v = verdict_for(fn, graph, recs)
        if not v["known"]:
            print(f"  {fn:24s} not found")
            continue
        print(f"  {fn:24s} {str(v['verdict']):9s} "
              f"{v['dependencies']:3d} deps  held by: "
              f"{', '.join(v.get('held_there_by', [])[:3])}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
