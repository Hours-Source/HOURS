"""The wiring gate: a parameter that is accepted, changes nothing, and that no test
exercises.

Three defects in one session prompted it, and in each the tests pinned the shape of the
OUTPUT and never the WIRING behind it:

    2026-08-30  arc_stability ran conditions 1 and 3 at `collapsed` and
                condition 2 at `sufficiency`: one verdict, two standards
    2026-08-30  its `capital_stock_teh` default was 2,000 TOTAL over 1e6 people,
                so `delivery_pays` could not bind
    2026-08-30  it passed `personal_base` into `feasibility_check` and read only
                `supply_per_capita`, which ignores it

THIS GATE CATCHES NONE OF THOSE THREE, AND SAYING SO IS THE POINT. With all three
reintroduced the ratchet stays green. A gate that reads as covering more than it does
looks stronger than it is ([record](record/verification.md#the-wiring-gate)).

WHAT IT CATCHES: a parameter that exists, is inert at every configuration tried, and is
never passed by name in the suite. It found `hours_per_worker_year(total_population=)`,
whose value cancelled ([record](record/verification.md#wiring-gate-defect-fixed)).

WHAT IT CANNOT CATCH, stated so nobody relies on it:

  * **a wrong default.** `capital_stock_teh=2000` moves the output: the parameter
    is live and the VALUE is wrong.
  * **a parameter that should exist and does not.** The mixed standards were two
    callees with two defaults and no parameter at all.
  * **a parameter a test names but under-pins.** Stage 2 drops anything the suite
    passes by name, so a test that mentions it silences this gate.
  * **any function with a REQUIRED argument.** Stage 1 skips it, so
    `simulate_period` is invisible here. Its `deferred_eco_growth_rate` was inert
    on every shipped path and survived both blind spots (2026-09-08). A test in
    test_simulation pins it; it is not declared here
    ([record](record/fulfilment.md#five-figures-and-the-instrument)).
  * **its own ratchet being loosened.** The bound here passes if someone raises
    it. Since 2026-10-17 the claims register reads the bound from the assertion
    and fails if it moves (`_wiring_bound_still_12`). Raising both is still
    possible, and is visible in a diff of two files.

The probe is dynamic because static analysis misses even this class: `personal_base` WAS
referenced, forwarded into a call that ignored it. It tries several configurations,
because a no-argument call runs `total_eoh` at ε=0, where `knowledge_exponent` cannot
bite. Stage 2 keeps it usable: "inert at defaults" is not "unpinned", and
`planetary_budget`'s parameters are inert only on its P0 clamp.

IT IS A RATCHET: each pre-existing finding is declared with its reason, the count may
not rise, and masking must be DECLARED, never inferred.
"""

from __future__ import annotations

import importlib
import inspect
import math
import pathlib
import pkgutil
import re

import pytest

import hours_eoh

TESTS = pathlib.Path(__file__).resolve().parent

#: Parameters known to be inert at their defaults AND unexercised, each with the
#: reason it is tolerated. **Four classes**, and only the first is a defect.
_DECLARED: dict[tuple[str, str], str] = {
    # --- A. FIXED 2026-08-31, kept here as the record ---------------------
    # `hours_per_worker_year(total_population=)` was the one real defect this
    # gate found: `hours_per_capita(..., total_population)` divided by it and the
    # return multiplied it back, so the parameter was a round trip and the answer
    # was 1,874.4284 at every population. The parameter is GONE — the function
    # now builds the 15+ aggregate directly — and the value is unchanged,
    # because a cancelling parameter cannot have been affecting it. Removing the
    # declaration is what the ratchet is for: it fired on its own staleness
    # check the moment the parameter stopped existing.
    #
    # --- B. Detectors that CAN fire and that nothing exercises -------------
    ("epsilon_sweep", "jump_threshold"): (
        "the discontinuity detector is live — 0 flags at the default 5.0, 29 at "
        "0.05, 498 at 0.001 — but no test has ever passed it, so nothing checks "
        "that it can fire. The `settlement_report` lesson: a threshold nobody "
        "exercises is a threshold nobody trusts."
    ),
    ("planetary_budget", "a_earth"): (
        "the only one of the five physics parameters `test_thermal` does not "
        "exercise above the P0 clamp. The others are pinned there; this is not."
    ),
    # --- C. Insensitivity: correctly inert, belongs in test_tolerances -----
    ("breaking_labor_intensity", "iterations"): "bisection count; inert IS correct once converged",
    ("delivery_crossover", "tol"): "bisection tolerance; inert IS correct once converged",
    ("thermal_load_verdict", "negligible_threshold"): (
        "reachable, but the measured share (0.129%) sits 29% above the 0.1% "
        "line, so a +7% perturbation cannot cross it. A limit of the probe, not "
        "of the parameter."
    ),
    ("thermal_load_verdict", "material_threshold"): (
        "same: the share is an order of magnitude below the 1% line."
    ),
    # --- D. Inert by ADOPTED POLICY, and that is the point -----------------
    ("total_eoh", "ecological_intensity"): (
        "Phase 4e/4f moved every recurring ecological term to GUF, so the domain "
        "is 0.0 on every shipped path and its intake fields are inert BY "
        "DESIGN. They remain documented intake, which the implementation guide "
        "states at the top of the intake table."
    ),
    ("total_eoh", "ecological_hectares_per_capita"): (
        "same — Phase 4e/4f. It resolves the default ecological AREA from the\n"
        "population, and with the domain empty there is nothing for the area to\n"
        "scale. It stays reachable because supplying a stock makes it live again."
    ),
    # THE ENTRY POINT BECAME PROBEABLE ON 2026-09-01, AND THAT IS THE FINDING.
    # This gate only probes functions callable with no arguments (see the filter
    # below). `eoh_to_teh_pipeline` required `epsilon`, so the ONE function the
    # implementation guide tells an institution to run had never been covered.
    # Giving `epsilon` a default — for the capability/observable rename — closed
    # that hole as a side effect, and the gate immediately found these two.
    # They are the same two fields, inert for the same Phase 4e/4f reason, one
    # layer up. Everything else on the entry point is live or exercised.
    ("eoh_to_teh_pipeline", "ecological_intensity"): (
        "same as total_eoh — Phase 4e/4f emptied the domain. Newly VISIBLE here "
        "rather than newly inert: the pipeline was unprobeable until its required "
        "argument gained a default."
    ),
    ("eoh_to_teh_pipeline", "ecological_hectares_per_capita"): (
        "same as total_eoh — Phase 4e/4f. Newly visible for the same reason as "
        "the line above."
    ),
    ("formation_feedback_simulation", "capacity_floor"): (
        "gates §8.9b charter escalation, which CLAUDE.md records as NEVER firing "
        "at canonical defaults. Inert here is the recorded finding."
    ),
    ("recalibrated_arc", "capacity_floor"): "same — escalation never fires at defaults",
}


# ---------------------------------------------------------------------------
# The probe
# ---------------------------------------------------------------------------

def _modules():
    for m in pkgutil.walk_packages(hours_eoh.__path__, "hours_eoh."):
        if m.name.endswith((".data", ".params")):
            continue
        try:
            yield importlib.import_module(m.name)
        except Exception:                                    # pragma: no cover
            continue


def _perturb(v, mod=None):
    """An alternative value for a parameter. For a string, it tries another member of
    the declared enum that holds the default (a tuple, list or set in the defining
    module). The first version returned None for every string and missed the `standard:
    str` defect.
    """
    if isinstance(v, bool):
        return not v
    if isinstance(v, float):
        return v * 1.07 if v != 0.0 else 0.1
    if isinstance(v, int):
        return v + 1 if v not in (0, 1) else v + 2
    if isinstance(v, str) and mod is not None:
        for name, obj in vars(mod).items():
            if name.startswith("_") or not isinstance(obj, (tuple, list, set, frozenset)):
                continue
            members = [m for m in obj if isinstance(m, str)]
            if v in members and len(members) > 1:
                return next(m for m in members if m != v)
    return None


def _flat(o, out=None, d=0):
    if out is None:
        out = []
    if d > 6:
        return out
    if isinstance(o, dict):
        for k in sorted(o, key=str):
            _flat(o[k], out, d + 1)
    elif isinstance(o, (list, tuple)):
        for x in o:
            _flat(x, out, d + 1)
    elif isinstance(o, bool) or o is None or isinstance(o, str):
        out.append(repr(o))
    elif isinstance(o, (int, float)):
        out.append(float(o))
    else:
        for a in dir(o):
            if a.startswith("_"):
                continue
            try:
                v = getattr(o, a)
            except Exception:
                continue
            if isinstance(v, (int, float, str, bool, type(None))) and not callable(v):
                _flat(v, out, d + 1)
    return out


def _same(a, b) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(x, float) and isinstance(y, float):
            if math.isnan(x) and math.isnan(y):
                continue
            if abs(x - y) > 1e-12 * max(1.0, abs(x), abs(y)):
                return False
        elif x != y:
            return False
    return True


def _inert_parameters() -> list[tuple[str, str]]:
    """Parameters inert at EVERY configuration tried. Stage 1."""
    found: list[tuple[str, str]] = []
    for mod in _modules():
        for name, fn in vars(mod).items():
            if name.startswith("_") or not inspect.isfunction(fn):
                continue
            if fn.__module__ != mod.__name__:
                continue
            try:
                params = list(inspect.signature(fn).parameters.values())
            except Exception:
                continue
            if any(p.default is inspect.Parameter.empty
                   and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                   for p in params):
                continue                       # only no-arg-callable functions

            names = {q.name for q in params}
            configs: list[dict] = [{}]
            if "epsilon" in names:
                configs += [{"epsilon": 0.40}, {"epsilon": 0.99}]
            if "ecosystem_health" in names:
                configs += [{"ecosystem_health": 0.30}]

            bases = []
            for cfg in configs:
                try:
                    bases.append((cfg, _flat(fn(**cfg))))
                except Exception:
                    continue
            if not bases:
                continue

            for p in params:
                if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    continue
                alt = _perturb(p.default, mod)
                if alt is None:
                    continue
                inert, exercised = True, False
                for cfg, base in bases:
                    if p.name in cfg:
                        continue
                    try:
                        got = _flat(fn(**{**cfg, p.name: alt}))
                    except Exception:
                        inert = False           # validated → live
                        break
                    exercised = True
                    if not _same(base, got):
                        inert = False
                        break
                if exercised and inert:
                    found.append((name, p.name))
    return found


def _suite_text() -> str:
    return "\n".join(
        p.read_text(errors="ignore") for p in TESTS.rglob("*.py")
        if p.name != pathlib.Path(__file__).name
    )


def _unexercised(inert: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Stage 2: of those, the ones no test passes by name."""
    blob = _suite_text()
    return [
        (fn, param) for fn, param in inert
        if not re.search(rf"\b{re.escape(param)}\s*=", blob)
    ]


# ---------------------------------------------------------------------------

class TestNoUndeclaredInertParameter:

    def test_the_ratchet(self) -> None:
        """
        THE GATE. A parameter accepted, inert at every configuration tried, and
        never exercised by any test is wiring nobody is holding.
        """
        offenders = sorted(set(_unexercised(_inert_parameters())) - set(_DECLARED))
        assert not offenders, (
            "these parameters change nothing and no test exercises them:\n  "
            + "\n  ".join(f"{fn}({param}=…)" for fn, param in offenders)
            + "\n\nEither wire it, exercise it in a test, or declare it in "
              "_DECLARED with the reason it is inert."
        )

    def test_the_count_does_not_grow(self) -> None:
        """A ratchet, not a blanket rule: lowering the count means wiring or exercising
        a parameter. The bound rose 10 → 12 on 2026-09-01 for COVERAGE, not debt. A
        default on `eoh_to_teh_pipeline`'s `epsilon` let the probe reach the documented
        entry point
        ([record](record/fulfilment.md#epsilon-split-capability-vs-observable)). A rise
        from honesty and a rise from a fresh copy look the same to a counter.
        """
        assert len(_DECLARED) <= 12


class TestTheGateItselfIsHonest:

    def test_every_declaration_carries_a_reason(self) -> None:
        for key, reason in _DECLARED.items():
            assert len(reason) > 30, f"{key} is declared without a reason"

    def test_every_declaration_names_something_still_inert(self) -> None:
        """A declaration for a parameter that is no longer inert is a permission nobody
        uses (the `unused_innocuous_names` failure).
        """
        inert = set(_inert_parameters())
        stale = sorted(k for k in _DECLARED if k not in inert)
        assert not stale, (
            f"these are declared inert but now move the output — remove them "
            f"from _DECLARED: {stale}"
        )

    def test_the_probe_actually_reaches_functions(self) -> None:
        """
        `exercised` asserted alongside `passes`, the provenance flow-trace
        discipline: if the walk stopped finding functions the gate would pass
        while inspecting nothing.
        """
        assert len(_inert_parameters()) >= 20, "the probe has gone blind"

    def test_stage_two_actually_filters(self) -> None:
        """Without the second stage the gate would flag `planetary_budget`'s physics
        parameters, which `test_thermal` exercises above the P0 clamp. A gate that fires
        on well-tested code gets suppressed.
        """
        inert = _inert_parameters()
        assert len(_unexercised(inert)) < len(inert), (
            "stage two filtered nothing; it is not doing its job"
        )

    def test_it_bites_on_a_synthetic_offender(self) -> None:
        """Demonstrated, not asserted."""
        def offender(a: float = 1.0, ignored: float = 2.0) -> float:
            return a * 2.0
        base = _flat(offender())
        assert _same(base, _flat(offender(ignored=99.0))), "probe missed an inert param"
        assert not _same(base, _flat(offender(a=99.0))), "probe flagged a live param"

    def test_string_parameters_are_probed_via_their_enum(self) -> None:
        """
        THE GAP THAT MADE THE FIRST VERSION USELESS ON ITS OWN MOTIVATING CASE.
        `arc_stability.stability_at(standard=)` is a str; returning None for
        strings meant the gate could not see a standard that stopped threading.
        """
        import hours_eoh.scenarios.arc_stability as mod
        assert _perturb("sufficiency", mod) == "survival", (
            "a str default that belongs to a declared enum must yield another "
            "member, or string wiring is unprobed"
        )
        assert _perturb("not-in-any-enum", mod) is None


class TestTheGateStatesItsOwnLimits:
    """The admission carries weight. This gate catches none of the three defects that
    prompted it; without that sentence it reads as coverage it does not give.
    """

    def test_the_docstring_names_what_it_cannot_catch(self) -> None:
        import tests.test_parameter_wiring as mod
        doc = " ".join((mod.__doc__ or "").split())
        assert "CATCHES NONE OF THOSE THREE" in doc
        assert "WHAT IT CANNOT CATCH" in doc
        assert "a wrong default" in doc
        assert "under-pins" in doc

    def test_a_live_parameter_with_a_wrong_default_is_NOT_flagged(self) -> None:
        """
        Demonstrated, not asserted: the limit is real and this is what it looks
        like. A parameter whose value is wrong still moves the output, so no
        inertness probe can see it.
        """
        def wrong_default(scale: float = 2000.0) -> float:
            return scale * 3.0          # live, and 2000.0 is the wrong value
        base = _flat(wrong_default())
        assert not _same(base, _flat(wrong_default(scale=2140.0))), (
            "a wrong-but-live default is invisible to this gate by construction"
        )
