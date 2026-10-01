"""
THE REGISTER IS READ IN ONE PLACE — `core/registration.register_shares`.

Author, 2026-10-01: "registration is separate from machine capability — one is
what the collective carries, the other how much human labour carries it." Until
that date 21 calls in 9 modules across core/, scenarios/, research/ and utils/ called
the registration curves with the CAPABILITY ε, so nothing could hold the
register while machines changed. Every reading now goes through
`register_shares(epsilon, registration_epsilon=None)`.

This gate refuses an import of any individual curve outside
`core/registration.py`, by AST (aliases and multi-line imports included — a
text search sees neither), the shape of `test_one_mint_path.py`.

STATES ITS OWN GAP: it sees imports, not a re-implemented sigmoid. A module that
copied a curve's formula inline would pass.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from hours_eoh.core import registration as R

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCANNED = ("hours_eoh", "utils")

#: The curves. Read off the module, not typed here, so a new curve is covered
#: the day it is added.
CURVES = frozenset(
    name for name, obj in vars(R).items()
    if callable(obj) and getattr(obj, "__module__", "") == R.__name__
    and name not in {"register_shares", "resolve_registration_epsilon",
                     "validate_registration_trajectory"}
)

#: Imports allowed outside registration.py, each with its reason.
ALLOWED = {
    ("hours_eoh/core/fiscal.py", "collective_land_registration"):
        "re-export only: the curve moved from fiscal to registration on "
        "2026-10-01 and its public name is kept (deprecate, don't delete)",
}


def _offenders() -> list[str]:
    out = []
    for d in SCANNED:
        for f in sorted((ROOT / d).rglob("*.py")):
            rel = f.relative_to(ROOT).as_posix()
            if rel == "hours_eoh/core/registration.py":
                continue
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "hours_eoh.core.registration":
                    for a in node.names:
                        if a.name in CURVES and (rel, a.name) not in ALLOWED:
                            out.append(f"{rel}:{node.lineno} imports {a.name}")
                if (isinstance(node, ast.Attribute) and node.attr in CURVES
                        and isinstance(node.value, ast.Name)
                        and node.value.id in {"registration", "R", "_reg"}):
                    out.append(f"{rel}:{node.lineno} reads registration.{node.attr}")
    return out


def test_the_curves_are_found():
    # A scan over zero curves passes and guards nothing.
    assert {"personal_eoh_registration_share", "total_registration_share",
            "knowledge_eoh_registration_share", "care_registration_share",
            "collective_land_registration"} <= CURVES


def test_no_curve_is_read_outside_the_register():
    bad = _offenders()
    assert not bad, (
        "Read the register through `register_shares(epsilon, "
        "registration_epsilon)`, not a curve directly:\n  " + "\n  ".join(bad))


def test_every_allowance_is_still_needed():
    for (rel, name), _reason in ALLOWED.items():
        assert name in (ROOT / rel).read_text(encoding="utf-8"), (rel, name)


@pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
def test_unset_register_tracks_the_capability(eps):
    assert R.register_shares(eps) == R.register_shares(eps, registration_epsilon=eps)
    assert R.register_shares(eps)["personal"] == R.personal_eoh_registration_share(eps)
    assert set(R.register_shares(eps)) == set(R.REGISTER_KEYS)


def test_a_held_register_ignores_the_capability():
    held = [R.register_shares(e, registration_epsilon=0.40) for e in (0.0, 0.40, 0.90, 0.99)]
    assert all(h == held[0] for h in held)


def test_out_of_range_register_refused():
    with pytest.raises(ValueError):
        R.register_shares(0.40, registration_epsilon=1.5)


@pytest.mark.parametrize("eps", [0.40, 0.90])
def test_the_simulation_carries_a_held_register(eps):
    """The register is STATE: set once, carried forward, read by the
    pipeline, the guarantee and both in-period reads."""
    from hours_eoh.core.simulation import make_economy_state, simulate_period
    held = make_economy_state(epsilon=eps, registration_epsilon=0.20)
    free = make_economy_state(epsilon=eps)
    (s_held, p_held), (s_free, p_free) = simulate_period(held), simulate_period(free)
    assert s_held["registration_epsilon"] == 0.20
    assert s_free["registration_epsilon"] is None
    # Carried, not re-read: a second period keeps it.
    assert simulate_period(s_held)[0]["registration_epsilon"] == 0.20
    # A register held below the capability admits less to the ledger.
    assert p_held["teh_created"] < p_free["teh_created"]


def test_a_lagging_register_trips_the_care_indicator():
    """The dashboard's care status could only read its own curve back; a
    register held behind the capability is the lag its comment describes. The
    GREEN line is 20% of saturation, so a register lagging only to ε=0.30 still
    reads GREEN — it trips near the bottom of the arc."""
    from hours_eoh.core.dashboard import eoh_health_indicators
    status = {r: eoh_health_indicators(1e9, 8e8, epsilon=0.90, registration_epsilon=r)[
        "care_admission_status"] for r in (None, 0.30, 0.20, 0.0)}
    assert status == {None: "GREEN", 0.30: "GREEN", 0.20: "YELLOW", 0.0: "RED"}
