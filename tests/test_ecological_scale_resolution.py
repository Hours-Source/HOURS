"""
The ecological scale-resolution gate.

WHY THIS EXISTS. The same defect has now been found FOUR times, by four
different routes, and never by a gate:

    2026-08-17  `total_eoh` / `eoh_to_teh_pipeline`  — found by a readiness audit
    2026-08-17  `scenarios/sweep.py`                 — found while fixing the above
    2026-08-17  the dashboard's fiscal path          — found by re-auditing
    2026-08-17  `core/autarky.autarky_reference`     — found by a codebase sweep

Every instance is the same shape. A function scales one domain with
`population` and then calls `ecological_eoh(...)` with **no area**, so the
ecological term silently resolves to a fixed reference frame — historically the
whole contiguous US — and the two are summed as though they were on the same
footing. Nothing about it looks wrong at the call site, which is why reading the
code never caught it.

WHAT THE GATE CHECKS. Any function that has a `population` in scope and calls
into the ecological scale must SAY which frame it means: pass `area_hectares`,
pass an explicit `base_rate`, or take a `hectares_per_capita`-style parameter
and resolve from population. Calling with neither is the defect.

WHY IT IS AN ALLOWLIST AND NOT A BLANKET RULE. Some callers genuinely have no
population — `ecological_eoh_breakdown` itself, the shock scenarios that vary
health at a fixed frame — and for those the declared reference frame is the
right default. Those are named, with the reason, so that adding to the list is a
visible act in a diff rather than an emergent property of how a function
happened to be written. The `_INNOCUOUS_NAMES` precedent: masking must be
DECLARED, never inferred.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

PKG = pathlib.Path(__file__).resolve().parent.parent / "hours_eoh"

#: Functions in the ecological-scale chain. A call to any of these is a scale
#: resolution and must state its frame.
_SCALE_CALLS = {"ecological_eoh", "ecological_eoh_breakdown", "ecological_scale"}

#: Keyword arguments that STATE the frame. Any one of them discharges the rule.
_FRAME_KWARGS = {
    "area_hectares",
    "ecological_area_hectares",
    "base_rate",
    "ecological_base",
}

#: Parameter names that mean "this function has a population in scope", i.e. it
#: is scaling something extensive and the ecological term must scale with it.
_POPULATION_PARAMS = {"population", "pop"}

#: Callers exempt from the rule, each with the reason it does not apply.
#: EVERY entry must name a function that exists — an exemption for a function
#: nobody has is an exemption nobody reviews (`unused_innocuous_names` lesson).
_DECLARED_EXEMPT: dict[str, str] = {
    "ecological_eoh": (
        "the resolution point itself — it is what `ecological_scale` resolves "
        "FOR, and it takes no population by design"
    ),
    "ecological_eoh_breakdown": (
        "same: the decomposition of the resolution point, no population in scope"
    ),
    "total_eoh": (
        "resolves the area from its own population when neither base nor area "
        "is supplied — it is the fix, not an instance of the defect"
    ),
}


def _iter_functions():
    for path in sorted(PKG.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield path, node


def _has_population_param(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    args = fn.args
    names = {a.arg for a in (*args.args, *args.kwonlyargs, *args.posonlyargs)}
    return bool(names & _POPULATION_PARAMS)


def _unframed_scale_calls(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Calls into the ecological scale that state no frame."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        name = (
            node.func.id if isinstance(node.func, ast.Name)
            else node.func.attr if isinstance(node.func, ast.Attribute)
            else None
        )
        if name not in _SCALE_CALLS:
            continue
        kwargs = {k.arg for k in node.keywords if k.arg}
        if kwargs & _FRAME_KWARGS:
            continue
        # `ecological_eoh(health, eps, base_rate, ...)` — base_rate is 3rd
        # positional; `ecological_scale(base_rate, area, ...)` — 1st.
        positional_frame = (
            (name == "ecological_eoh" and len(node.args) >= 3)
            or (name == "ecological_eoh_breakdown" and len(node.args) >= 3)
            or (name == "ecological_scale" and len(node.args) >= 1)
        )
        if positional_frame:
            continue
        out.append(f"{name} (line {node.lineno})")
    return out


class TestEveryPopulationScaledCallerStatesItsFrame:

    def test_no_unframed_ecological_call_alongside_a_population(self) -> None:
        """
        THE GATE. A function that scales with population and resolves the
        ecological scale without saying which frame it means is the defect that
        has been found four times by hand.
        """
        offenders = []
        for path, fn in _iter_functions():
            if fn.name in _DECLARED_EXEMPT:
                continue
            if not _has_population_param(fn):
                continue
            unframed = _unframed_scale_calls(fn)
            if unframed:
                rel = path.relative_to(PKG.parent)
                offenders.append(f"{rel}:{fn.lineno} {fn.name}() -> {', '.join(unframed)}")

        assert not offenders, (
            "these functions scale with population but resolve the ecological "
            "scale without stating a frame:\n  "
            + "\n  ".join(offenders)
            + "\n\nPass `area_hectares=population * LAND_HECTARES_PER_CAPITA`, or "
              "an explicit `base_rate`, or declare an exemption with its reason."
        )


class TestTheGateItselfIsHonest:
    """A gate that cannot bite, or that exempts nothing real, is not a gate."""

    def test_every_exemption_names_a_function_that_exists(self) -> None:
        """
        An exemption for a function nobody has is an exemption nobody reviews —
        the failure the `unused_innocuous_names` check was built for after the
        registration migration made two allowlist entries stale within an hour.
        """
        defined = {fn.name for _, fn in _iter_functions()}
        stale = sorted(set(_DECLARED_EXEMPT) - defined)
        assert not stale, f"exemptions for functions that do not exist: {stale}"

    def test_every_exemption_carries_a_reason(self) -> None:
        for name, reason in _DECLARED_EXEMPT.items():
            assert reason.strip(), f"{name} is exempt with no reason given"

    def test_the_scan_actually_reaches_the_call_sites(self) -> None:
        """
        Guards the scan itself: if `_SCALE_CALLS` stopped matching anything —
        a rename, a moved module — the gate would pass while inspecting
        nothing. `exercised` asserted alongside `passes`, the provenance
        flow-trace discipline.
        """
        seen = 0
        for _, fn in _iter_functions():
            for node in ast.walk(fn):
                if isinstance(node, ast.Call):
                    name = (
                        node.func.id if isinstance(node.func, ast.Name)
                        else node.func.attr if isinstance(node.func, ast.Attribute)
                        else None
                    )
                    if name in _SCALE_CALLS:
                        seen += 1
        assert seen >= 8, f"only {seen} ecological-scale calls found; the scan has gone blind"

    def test_the_gate_bites_on_a_synthetic_offender(self) -> None:
        """Demonstrated, not asserted: a known-bad function must be caught."""
        bad = ast.parse(
            "def f(population, ecosystem_health):\n"
            "    return ecological_eoh(ecosystem_health)\n"
        ).body[0]
        assert _has_population_param(bad)
        assert _unframed_scale_calls(bad), "the gate failed to catch a known offender"

    def test_the_gate_accepts_a_correctly_framed_caller(self) -> None:
        good = ast.parse(
            "def f(population, ecosystem_health):\n"
            "    return ecological_eoh(ecosystem_health, area_hectares=population * 1.65)\n"
        ).body[0]
        assert not _unframed_scale_calls(good), "the gate flagged a correct caller"


class TestTheFourKnownInstancesAreCovered:
    """
    Named so the regression is legible in the diff. Each was found by a
    different route and none by a gate.
    """

    @pytest.mark.parametrize(
        "module,function",
        [
            ("core/eoh_generation.py", "total_eoh"),
            ("core/autarky.py", "autarky_reference"),
            ("scenarios/sweep.py", "epsilon_sweep"),
        ],
    )
    def test_known_site_states_its_frame(self, module: str, function: str) -> None:
        path = PKG / module
        tree = ast.parse(path.read_text())
        fn = next(
            n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == function
        )
        if function in _DECLARED_EXEMPT:
            pytest.skip(f"{function} is the resolution point, declared exempt")
        assert not _unframed_scale_calls(fn), (
            f"{module}:{function} has regressed to an unframed ecological call"
        )
