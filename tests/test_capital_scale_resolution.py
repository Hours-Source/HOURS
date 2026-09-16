"""
The capital scale-resolution gate.

WHY THIS EXISTS. `CAPITAL_STOCK_DEFAULT` is declared "at the 1M reference
population" and `resolve_capital_stock` had no way to hear about any other one:
it returned the same ABSOLUTE stock whatever population the caller was
modelling. 25 of the 32 functions that call it have a `population` in scope, and
exactly one of them scaled — `land/calibration.py`, fixed by hand a day earlier,
whose own comment says "THE SEAM ITSELF IS UPSTREAM AND IS NOT FIXED HERE".

WHAT IT COST, measured at the documented entry point (`eoh_to_teh_pipeline`,
ε=0.40, no capital supplied) before the 2026-09-16 repair:

    population    per-capita TEH    infrastructure EOH per capita
      1e5              913.65                 900.00
      1e6              339.64                  90.00
      1e7              282.23                   9.00

A 3.24x spread for identical capital INTENSITY, and infrastructure EOH per
capita exactly inverse-proportional to population — the fixed reference stock
divided among whoever was named. A collective of 100,000 was told it owed ten
times the stewardship labour per person that the reference frame did. At
`min_levy_for_solvency` the same defect read 1,078.07 / 107.81 / 10.78 TEH per
capita while the guarantee per capita stayed flat at 139.85: one domain
travelling with the frame and the other not, summed as though they agreed.

THIS IS FAILURE MODE 6, and the ecological chain's gate is the precedent — same
defect, one domain over, found four times by hand there before a gate caught it.
The repair is the same shape too: resolve at ε FIRST, then scale by the frame,
because a supplied stock is never rescaled by the callee.

WHAT THE GATE CHECKS. Any function with a `population` in scope that calls into
the capital chain must SAY which frame it means: pass `population`, or supply a
`capital_stock`. Calling with neither is the defect.

**THE GATE STATES ITS OWN GAP** (the F-013 rule). Crediting a supplied stock is
STATIC: this scan sees that a capital argument was passed, never whether it is
`None` at runtime. A caller that passes `capital_stock=None` alongside a
population defeats it, and only a runtime probe would see that. The gap is
narrow because the value of naming the argument is that the caller has decided
the stock is theirs to supply — but it is a gap, not a guarantee.

THE WRAPPER LESSON, inherited rather than re-learned: the ecological gate was
keyed to the names at the BOTTOM of its chain and did not see callers entering
one wrapper up, so `fiscal_snapshot` reached the US anchor while the gate looked
straight past. `_CHAIN_CALLS` therefore names the wrappers too — `total_eoh` and
`eoh_to_teh_pipeline`, both of which take a `population` that defaults to the
reference frame, which is the same seam one level up.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.eoh_generation import resolve_capital_stock
from hours_eoh.core.fiscal import min_levy_for_solvency

PKG = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh"

#: Functions in the capital-scale chain. A call to any of these resolves or
#: consumes a capital stock and must state its frame.
_CHAIN_CALLS = {
    "resolve_capital_stock",
    "infrastructure_eoh",
    "total_eoh",
    "eoh_to_teh_pipeline",
}

#: Keyword arguments that STATE the frame. Any one of them discharges the rule:
#: `population` scales the resolved stock, and supplying a stock means the
#: caller is naming the actual one, which is never rescaled.
_FRAME_KWARGS = {"population", "capital_stock", "capital_stock_teh"}

#: Parameter names that mean "this function has a population in scope".
_POPULATION_PARAMS = {"population", "pop"}

#: Positional forms that state the frame, by callee. Positions are 0-indexed
#: counts of positional arguments needed before the frame is stated:
#:   resolve_capital_stock(capital_stock, epsilon, population)  -> 3
#:   infrastructure_eoh(capital_stock, ...)                     -> 1
#:   total_eoh(epsilon, population, ...)                        -> 2
#:   eoh_to_teh_pipeline(epsilon, population, ...)              -> 2
#:
#: `resolve_capital_stock` deliberately needs THREE and is not discharged by its
#: first positional: a stock passed there is routinely `None` — that is the
#: whole point of a resolver — so crediting it would exempt exactly the calls
#: the 2026-09-16 repair had to fix.
_POSITIONAL_FRAME_AT = {
    "resolve_capital_stock": 3,
    "infrastructure_eoh": 1,
    "total_eoh": 2,
    "eoh_to_teh_pipeline": 2,
}

#: Callers exempt from the rule, each with the reason it does not apply. EVERY
#: entry must name a function that exists — an exemption for a function nobody
#: has is an exemption nobody reviews.
#:
#: EMPTY ON THE DAY THE GATE LANDED, and that is the state to preserve: after
#: the repair every caller with a population in scope states its frame. An entry
#: here is a deliberate act in a diff, which is the point.
_DECLARED_EXEMPT: dict[str, str] = {}


def _iter_functions():
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield path, node


def _has_population_param(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    a = fn.args
    names = {x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    return bool(names & _POPULATION_PARAMS)


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _unframed_chain_calls(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Calls into the capital chain that state no frame."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name not in _CHAIN_CALLS:
            continue
        if {k.arg for k in node.keywords if k.arg} & _FRAME_KWARGS:
            continue
        if len(node.args) >= _POSITIONAL_FRAME_AT[name]:
            continue
        out.append(f"{name} (line {node.lineno})")
    return out


class TestEveryPopulationScaledCallerStatesItsFrame:

    def test_no_unframed_capital_call_alongside_a_population(self) -> None:
        """
        THE GATE. A function that scales with population and resolves a capital
        stock without saying which frame it means is the defect the 2026-09-16
        repair closed at 24 call sites.
        """
        offenders = []
        for path, fn in _iter_functions():
            if fn.name in _DECLARED_EXEMPT:
                continue
            if not _has_population_param(fn):
                continue
            unframed = _unframed_chain_calls(fn)
            if unframed:
                rel = path.relative_to(PKG.parent)
                offenders.append(f"{rel}:{fn.lineno} {fn.name}() -> {', '.join(unframed)}")

        assert not offenders, (
            "these functions scale with population but resolve a capital stock "
            "without stating a frame:\n  "
            + "\n  ".join(offenders)
            + "\n\nPass `population=population`, or supply an explicit "
              "`capital_stock`, or declare an exemption with its reason."
        )


class TestTheGateItselfIsHonest:
    """A gate that cannot bite, or that exempts nothing real, is not a gate."""

    def test_every_exemption_names_a_function_that_exists(self) -> None:
        defined = {fn.name for _, fn in _iter_functions()}
        stale = sorted(set(_DECLARED_EXEMPT) - defined)
        assert not stale, f"exemptions for functions that do not exist: {stale}"

    def test_every_exemption_carries_a_reason(self) -> None:
        for name, reason in _DECLARED_EXEMPT.items():
            assert reason.strip(), f"{name} is exempt with no reason given"

    def test_the_scan_actually_reaches_the_call_sites(self) -> None:
        """
        Guards the scan itself: if `_CHAIN_CALLS` stopped matching anything — a
        rename, a moved module — the gate would pass while inspecting nothing.
        `exercised` asserted alongside `passes`.
        """
        seen = 0
        for _, fn in _iter_functions():
            for node in ast.walk(fn):
                if isinstance(node, ast.Call) and _call_name(node) in _CHAIN_CALLS:
                    seen += 1
        assert seen >= 30, f"the scan reached only {seen} chain calls; it should see dozens"

    def test_a_population_scaled_caller_is_actually_being_examined(self) -> None:
        """The other half: the scan must find functions to APPLY the rule to."""
        examined = [
            fn.name for _, fn in _iter_functions()
            if _has_population_param(fn) and any(
                _call_name(n) in _CHAIN_CALLS
                for n in ast.walk(fn) if isinstance(n, ast.Call)
            )
        ]
        assert len(examined) >= 20, (
            f"only {len(examined)} population-scaled chain callers examined: {examined}"
        )


class TestTheFrameHoldsAtRuntime:
    """
    The structural gate says every caller STATES a frame; these say the frame
    actually TRAVELS. Both are needed — a caller can pass `population` into a
    resolver that ignores it, which is the shape of failure mode 10.
    """

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_per_capita_output_is_frame_invariant(self, eps) -> None:
        """
        Across the arc, not at 0.40 alone — a ratio checked at one point is the
        trap failure mode 3 names, and this one is a ratio.

        Before the repair, ε=0.40 read 913.65 / 339.64 / 282.23 TEH per capita
        at populations 1e5 / 1e6 / 1e7.
        """
        per_capita = [
            eoh_to_teh_pipeline(epsilon=eps, population=pop)["teh_created"] / pop
            for pop in (1e5, 1e6, 1e7)
        ]
        assert per_capita[0] == pytest.approx(per_capita[1], rel=1e-12)
        assert per_capita[1] == pytest.approx(per_capita[2], rel=1e-12)

    def test_the_infrastructure_domain_is_what_used_to_break_it(self) -> None:
        """Named explicitly, because the personal domain was always frame-correct
        and summing the two hid which one was wrong."""
        pc = [
            eoh_to_teh_pipeline(epsilon=0.40, population=pop)["eoh_by_domain"]["infrastructure"] / pop
            for pop in (1e5, 1e6, 1e7)
        ]
        assert pc[0] == pytest.approx(90.0, rel=1e-9)   # was 900.00
        assert pc[1] == pytest.approx(90.0, rel=1e-9)
        assert pc[2] == pytest.approx(90.0, rel=1e-9)   # was 9.00

    def test_a_supplied_stock_is_never_rescaled(self) -> None:
        """The doctrine the repair must not break: a caller who names a stock is
        naming the ACTUAL stock, and scaling it would destroy their input."""
        assert resolve_capital_stock(2.4e9, 0.40, 1e5) == 2.4e9
        assert resolve_capital_stock(2.4e9, 0.40, 1e7) == 2.4e9
        a = eoh_to_teh_pipeline(epsilon=0.40, population=1e5, capital_stock=2.4e9)
        b = eoh_to_teh_pipeline(epsilon=0.40, population=1e7, capital_stock=2.4e9)
        assert (a["eoh_by_domain"]["infrastructure"]
                == pytest.approx(b["eoh_by_domain"]["infrastructure"], rel=1e-12))

    def test_omitting_population_keeps_the_reference_frame(self) -> None:
        """The repair is ADDITIVE: an unwired caller reads what it always read."""
        assert resolve_capital_stock(None, 0.40) == resolve_capital_stock(
            None, 0.40, 1_000_000.0)

    def test_the_fiscal_entry_point_travels_too(self) -> None:
        """`min_levy_for_solvency` read 1,078.07 / 107.81 / 10.78 TEH of
        stewardship per capita at 1e5 / 1e6 / 1e7 while the guarantee per capita
        stayed flat at 139.85 — one domain travelling with the frame, one not."""
        rows = [
            min_levy_for_solvency(trust_balance=3.5e10, population=pop,
                                  epsilon=0.40, labor_income=1e9)
            for pop in (1e5, 1e6, 1e7)
        ]
        stewardship_pc = [r["stewardship_cost"] / pop
                          for r, pop in zip(rows, (1e5, 1e6, 1e7))]
        guarantee_pc = [r["guarantee_cost"] / pop
                        for r, pop in zip(rows, (1e5, 1e6, 1e7))]
        assert stewardship_pc[0] == pytest.approx(stewardship_pc[1], rel=1e-12)
        assert stewardship_pc[1] == pytest.approx(stewardship_pc[2], rel=1e-12)
        # And the two domains now agree about what frame they are in.
        assert guarantee_pc[0] == pytest.approx(guarantee_pc[2], rel=1e-12)
