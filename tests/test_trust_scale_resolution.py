"""
THE INHERITANCE TRAVELS WITH THE FRAME — the Trust chain's scale gate.

Sibling of `test_capital_scale_resolution.py`. That gate closed the capital
seam; this one closes the Trust seam, which is the same defect
(CLAUDE.md § Recurring failure modes, mode 6) in the other constant named
there: `TRUST_BASE_TEH`, declared "at the 1M reference population" and
consumed by callers that moved the population without moving it.

WHY THIS GATE IS KEYED ON THE QUANTITY, NOT THE NAME
----------------------------------------------------
The session that built it began by scanning for the parameter *name*
`trust_balance` and found 22 sites. Keying the same scan on the QUANTITY —
"what defaults to TRUST_BASE_TEH" — found four more that the name filter could
not see:

  * `levy_schedule_for_chi(trust_start=...)`      — same quantity, other name
  * `contestability_audit(collective_trust=...)`  — same quantity, third name
  * `CollectiveFrame.trust_balance`               — a dataclass FIELD, not a
                                                    parameter
  * `civilization_epsilon`                        — `civ.get("trust_balance",
                                                    TRUST_BASE_TEH)`, a
                                                    dict-get default

That is failure mode 8 in miniature — "the label names the department, the
field names the quantity" — so the scan below walks parameter defaults, class
field defaults, `.get()` defaults and argparse defaults alike.

WHAT IT CANNOT SEE (a checker must state its own gaps, corpus F-013)
--------------------------------------------------------------------
Static and shallow by construction. It sees a default POSITION holding the
constant; it cannot see a caller that computes `TRUST_BASE_TEH * k` inline with
some other k, nor one that hard-codes 35_000_000_000.0 as a literal.

It also cannot see a dict VALUE. `params.py`'s `EOH_DEFAULTS` holds
`"trust_base": TRUST_BASE_TEH`, which is not a default position at all, so no
scan below reaches it. Checked by hand 2026-09-17: every reader of
`p["trust_base"]` is a test, and no operative caller passes it as a balance
beside a population — but the shape is invisible here by construction, not
because it is absent.

The runtime pins below cover the flow the package's own entry points drive, and
nothing else.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from hours_eoh.data import REFERENCE_FRAME_POPULATION, TRUST_BASE_TEH
from hours_eoh.core.fiscal import resolve_trust_balance
from hours_eoh.core.simulation import make_economy_state
from hours_eoh.research.exchange import CollectiveFrame
from hours_eoh.scenarios.long_run import trust_depletion_stress

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCANNED = ("hours_eoh", "utils")

# The ONLY sites allowed to hold TRUST_BASE_TEH in a default position, each
# because it has NO population in scope to resolve against — there is no frame,
# so a sentinel would resolve against nothing. Each must DECLARE that in its
# docstring; the declaration is checked, not assumed (mode 7).
FRAMELESS = {
    ("hours_eoh/research/contestability.py", "min_levy_for_pi"):
        "takes epsilon/trust/capital/g_priv — no population of any name",
    ("hours_eoh/scenarios/shocks.py", "demographic_shock"):
        "the shock arrives as a fractional magnitude, not a population",
}


def _py_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for d in SCANNED:
        out.extend(sorted((ROOT / d).rglob("*.py")))
    return out


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _holds_constant(node: ast.AST | None) -> bool:
    return node is not None and "TRUST_BASE_TEH" in ast.dump(node)


class TestNoDefaultCarriesTheReferenceFrame:
    """A default may not hold the 1M-frame constant where a frame exists."""

    def test_no_function_parameter_default_holds_the_constant(self) -> None:
        offenders: list[str] = []
        for f in _py_files():
            src = f.read_text(encoding="utf-8")
            if "TRUST_BASE_TEH" not in src:
                continue
            for n in ast.walk(ast.parse(src)):
                if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                a = n.args
                pos = [*a.posonlyargs, *a.args]
                names = [x.arg for x in (*pos, *a.kwonlyargs)]
                off = len(pos) - len(a.defaults)
                pairs = [(pos[off + i].arg, d) for i, d in enumerate(a.defaults)]
                pairs += [
                    (a.kwonlyargs[i].arg, d)
                    for i, d in enumerate(a.kw_defaults)
                    if d is not None
                ]
                for pname, default in pairs:
                    if not _holds_constant(default):
                        continue
                    if (_rel(f), n.name) in FRAMELESS:
                        continue
                    has_pop = any("population" in x for x in names)
                    offenders.append(
                        f"{_rel(f)}::{n.name}({pname}=TRUST_BASE_TEH) "
                        f"population_in_scope={has_pop}"
                    )
        assert not offenders, (
            "A parameter defaults to the 1M-reference Trust while a population "
            "is in scope — the inheritance does not travel with the frame:\n  "
            + "\n  ".join(offenders)
        )

    def test_no_class_field_default_holds_the_constant(self) -> None:
        offenders: list[str] = []
        for f in _py_files():
            src = f.read_text(encoding="utf-8")
            if "TRUST_BASE_TEH" not in src:
                continue
            tree = ast.parse(src)
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                for n in cls.body:
                    if isinstance(n, ast.AnnAssign) and _holds_constant(n.value):
                        target = getattr(n.target, "id", "?")
                        offenders.append(f"{_rel(f)}::{cls.name}.{target}")
        assert not offenders, (
            "A class field defaults to the 1M-reference Trust. A frozen frame "
            "resolves in __post_init__ instead (see CollectiveFrame):\n  "
            + "\n  ".join(offenders)
        )

    def test_no_dict_get_default_holds_the_constant(self) -> None:
        offenders: list[str] = []
        for f in _py_files():
            src = f.read_text(encoding="utf-8")
            if "TRUST_BASE_TEH" not in src:
                continue
            for n in ast.walk(ast.parse(src)):
                if (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "get"
                    and len(n.args) == 2
                    and _holds_constant(n.args[1])
                ):
                    offenders.append(f"{_rel(f)}:{n.lineno}")
        assert not offenders, (
            "A .get() default holds the 1M-reference Trust — the shape no "
            "parameter-level scan can see:\n  " + "\n  ".join(offenders)
        )

    def test_no_cli_flag_defaults_to_the_constant(self) -> None:
        """
        The documented entry point is where the seam matters most.

        Ten argparse definitions defaulted --trust-balance (and
        --collective-trust) to TRUST_BASE_TEH while --population sat beside them
        freely settable, so `--population 335000000` ran 335M people on a
        1M-person Trust. Every fix above the CLI is invisible here.
        """
        offenders: list[str] = []
        for f in sorted((ROOT / "utils").rglob("*.py")):
            src = f.read_text(encoding="utf-8")
            if "TRUST_BASE_TEH" not in src:
                continue
            for n in ast.walk(ast.parse(src)):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    continue
                if n.func.attr != "add_argument":
                    continue
                for kw in n.keywords:
                    if kw.arg == "default" and _holds_constant(kw.value):
                        offenders.append(f"{_rel(f)}:{n.lineno}")
        assert not offenders, (
            "A CLI flag defaults to the 1M-reference Trust:\n  "
            + "\n  ".join(offenders)
        )


class TestTheFramelessExemptionsAreDeclared:
    """An exemption that stops saying why it exists is an undeclared default."""

    @pytest.mark.parametrize("rel,func", sorted(FRAMELESS))
    def test_the_exemption_declares_its_frame(self, rel: str, func: str) -> None:
        src = (ROOT / rel).read_text(encoding="utf-8")
        node = next(
            n for n in ast.walk(ast.parse(src))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func
        )
        doc = ast.get_docstring(node) or ""
        assert "FRAME" in doc, (
            f"{rel}::{func} keeps an explicit TRUST_BASE_TEH default but no "
            "longer DECLARES that it has no population to resolve against."
        )
        assert "population" in doc.lower()

    @pytest.mark.parametrize("rel,func", sorted(FRAMELESS))
    def test_the_exemption_really_has_no_population(self, rel: str, func: str) -> None:
        """The reason must stay TRUE, not merely stated."""
        src = (ROOT / rel).read_text(encoding="utf-8")
        node = next(
            n for n in ast.walk(ast.parse(src))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func
        )
        a = node.args
        names = [x.arg for x in (*a.posonlyargs, *a.args, *a.kwonlyargs)]
        assert not any("population" in x for x in names), (
            f"{rel}::{func} now takes a population, so it can resolve against a "
            "frame and must lose its exemption."
        )


class TestTheResolverHoldsPerCapitaFixed:
    """What the frame holds fixed is Trust INTENSITY, not the absolute balance."""

    def test_the_reference_frame_is_bit_identical(self) -> None:
        assert resolve_trust_balance(None, REFERENCE_FRAME_POPULATION) == TRUST_BASE_TEH

    @pytest.mark.parametrize("pop", [1.0, 1e3, 1e6, 3.35e8, 8e9])
    def test_per_capita_is_invariant_across_populations(self, pop: float) -> None:
        got = resolve_trust_balance(None, pop) / pop
        assert got == pytest.approx(TRUST_BASE_TEH / REFERENCE_FRAME_POPULATION)

    @pytest.mark.parametrize("supplied", [0.0, 1.0, 7.0e9, 35.0e9, 4.2e12])
    def test_a_supplied_balance_is_never_rescaled(self, supplied: float) -> None:
        """A supplied value is the ACTUAL value — the frame doctrine."""
        for pop in (1.0, 1e6, 3.35e8):
            assert resolve_trust_balance(supplied, pop) == supplied

    def test_no_inheritance_stays_sayable(self) -> None:
        """
        A civilisation starting from subsistence brings 0.0, and 0.0 must not be
        read as "unsupplied" and silently replaced by the shipped inheritance.
        """
        assert resolve_trust_balance(0.0, 3.35e8) == 0.0


class TestTheFrameCarriesTheInheritance:
    """The frozen frame resolves its own inheritance from its own population."""

    def test_an_unsupplied_balance_scales_with_the_frame(self) -> None:
        small = CollectiveFrame(0, 1e6, 1.65e6, 2e9)
        big = CollectiveFrame(1, 1e7, 1.65e7, 2e10)
        assert small.trust_balance == TRUST_BASE_TEH
        assert big.trust_balance == TRUST_BASE_TEH * 10.0
        assert (big.trust_balance / big.population) == pytest.approx(
            small.trust_balance / small.population
        )

    def test_a_supplied_balance_is_used_as_given(self) -> None:
        f = CollectiveFrame(0, 1e7, 1.65e7, 2e10, trust_balance=7.0e9)
        assert f.trust_balance == 7.0e9

    def test_a_frame_with_no_inheritance_keeps_none(self) -> None:
        f = CollectiveFrame(0, 1e7, 1.65e7, 2e10, trust_balance=0.0)
        assert f.trust_balance == 0.0

    def test_a_negative_balance_is_still_refused(self) -> None:
        with pytest.raises(ValueError, match="trust_balance"):
            CollectiveFrame(0, 1e6, 1.65e6, 2e9, trust_balance=-1.0)


class TestTheStateBuilderCarriesTheInheritance:
    """The one place every scenario's Trust enters the ledger."""

    def test_per_capita_is_invariant_through_the_state_builder(self) -> None:
        a = make_economy_state(epsilon=0.40, population=1e6)
        b = make_economy_state(epsilon=0.40, population=3.35e8)
        assert (b["trust_balance"] / 3.35e8) == pytest.approx(
            a["trust_balance"] / 1e6
        )

    def test_a_supplied_balance_reaches_the_state_untouched(self) -> None:
        s = make_economy_state(epsilon=0.40, population=3.35e8, trust_balance=1.0e9)
        assert s["trust_balance"] == 1.0e9


class TestAScenarioDrivenOffTheReferenceFrame:
    """
    The pin the rest of the suite did not have.

    Every existing Trust test ran at the 1M reference population, where the
    resolver's ratio is exactly 1.0 and the repair is bit-identical — so the
    whole suite stayed green through this change and proved nothing about it
    (mode 1: "no tests failed" usually means "nothing tested it"). These drive a
    scenario at 1x, 10x and 335x the reference and check the INTENSITY, which is
    what the frame holds fixed.
    """

    @pytest.mark.parametrize("pop", [1e6, 1e7, 3.35e8])
    def test_the_trust_floor_per_capita_is_frame_invariant(self, pop: float) -> None:
        r = trust_depletion_stress(population=pop)
        ref = trust_depletion_stress(population=REFERENCE_FRAME_POPULATION)
        assert (r["trust_floor"] / pop) == pytest.approx(
            ref["trust_floor"] / REFERENCE_FRAME_POPULATION, rel=1e-9
        )

    @pytest.mark.parametrize("pop", [1e6, 1e7, 3.35e8])
    def test_the_verdict_does_not_depend_on_the_frame(self, pop: float) -> None:
        """Solvency is an intensity question; moving the frame may not move it."""
        r = trust_depletion_stress(population=pop)
        assert r["outcome"] == "STABLE"
        assert r["first_insolvency"] is None

    def test_a_supplied_balance_is_not_rescaled_by_the_scenario(self) -> None:
        """
        A collective at 335M that states a 1e9 Trust has a 1e9 Trust — not the
        11.7e12 the frame would have resolved for it.
        """
        resolved = trust_depletion_stress(population=3.35e8)
        supplied = trust_depletion_stress(population=3.35e8, trust_balance=1.0e9)
        assert resolved["trust_floor"] > 1.0e12
        assert supplied["trust_floor"] < 1.0e10
