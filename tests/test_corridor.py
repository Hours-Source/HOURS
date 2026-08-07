"""
Tests for the stability corridor (research/corridor.py).

The reframed success criterion: a stable feasible band [ε_suff, ε_max], NOT ε → 1.
Covers the survival floor (E22), the invariant ceilings, corridor composition,
and stability over a horizon.

Arc coverage at ε ∈ {0.0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.research.corridor import (
    survival_floor_epsilon,
    contestability_ceiling,
    thermal_ceiling,
    corridor,
    corridor_stability,
    Ceiling,
    CorridorReport,
)

ARC = [0.0, 0.40, 0.90, 0.99]
POP = 1_000_000.0
L_AVAIL = 1.0e9  # ~50% workforce × 2000 h/yr


# ---------------------------------------------------------------------------
# survival floor — E22
# ---------------------------------------------------------------------------

def test_survival_floor_zero_when_labor_covers():
    eoh = {"personal": 500.0, "infrastructure": 100.0, "ecological": 10.0, "knowledge": 1.0}
    # abundant labor covers survival → ε_suff = 0
    assert survival_floor_epsilon(eoh, available_labor_eoh=1e6) == 0.0


def test_survival_floor_positive_when_labor_short():
    eoh = {"personal": 1000.0, "infrastructure": 0.0, "ecological": 0.0, "knowledge": 0.0}
    # survival 1000, labor 400, total 1000 → (1000-400)/1000 = 0.6
    assert survival_floor_epsilon(eoh, available_labor_eoh=400.0) == pytest.approx(0.6)


@pytest.mark.parametrize("eps", ARC)
def test_survival_floor_in_unit_interval_across_arc(eps):
    es = survival_floor_epsilon(total_eoh(epsilon=eps), L_AVAIL)
    assert 0.0 <= es <= 1.0


def test_survival_floor_rejects_bad_inputs():
    with pytest.raises(ValueError):
        survival_floor_epsilon({"personal": 0.0}, available_labor_eoh=1.0)
    with pytest.raises(ValueError):
        survival_floor_epsilon({"personal": 10.0}, available_labor_eoh=-1.0)


def test_survival_floor_widening_domains_raises_it():
    eoh = {"personal": 500.0, "infrastructure": 500.0, "ecological": 0.0, "knowledge": 0.0}
    narrow = survival_floor_epsilon(eoh, 100.0, survival_domains=("personal",))
    wide = survival_floor_epsilon(eoh, 100.0, survival_domains=("personal", "infrastructure"))
    assert wide > narrow


# ---------------------------------------------------------------------------
# ceilings
# ---------------------------------------------------------------------------

def test_adopted_contestability_ceiling_nonbinding_at_defaults():
    # §8.9 three-channel test: exit is financeable at every ε in the adversarial
    # regime, so contestability does not bound the corridor at defaults.
    c = contestability_ceiling(POP, regime="increasing_returns")
    assert c["name"] == "contestability"
    assert c["binding"] is False
    assert c["epsilon_ceiling"] is None


@pytest.mark.parametrize("policy", ["dilution", "target"])
def test_adopted_contestability_ceiling_across_charter_policies(policy):
    c = contestability_ceiling(POP, regime="increasing_returns", phi_policy=policy)
    assert c["binding"] is False


def test_bare_chi_ceiling_nonbinding_when_well_capitalized():
    c = contestability_ceiling_bare_chi(POP, 5.0e11, regime="increasing_returns")
    assert c["binding"] is False
    assert c["epsilon_ceiling"] is None
    assert "SUPERSEDED" in c["status"]


def test_bare_chi_ceiling_binds_when_thin_trust():
    c = contestability_ceiling_bare_chi(POP, 5.0e10, regime="increasing_returns")
    assert c["name"] == "contestability_bare_chi"
    assert c["binding"] is True
    assert c["epsilon_ceiling"] is not None
    assert 0.0 <= c["epsilon_ceiling"] <= 0.99


def test_axes_disagree_at_thin_trust_and_the_adopted_axis_governs():
    """The migration finding, pinned.

    The retired bare-χ axis binds at thin trust; the adopted §8.9 axis does not
    bind at all. The recorded "corridor CLOSED at defaults" result came from the
    former. If this test ever starts passing with agree=True, the disagreement
    has been resolved and the corridor docs need re-reading.
    """
    cmp = contestability_axes(POP, 5.0e10, regime="increasing_returns")
    assert cmp["bare_chi"]["binding"] is True
    assert cmp["adopted"]["binding"] is False
    assert cmp["agree"] is False
    assert "AXES DISAGREE" in cmp["note"]


def test_axes_agree_when_well_capitalized():
    cmp = contestability_axes(POP, 5.0e11, regime="increasing_returns")
    assert cmp["agree"] is True
    assert cmp["adopted"]["binding"] is False
    assert cmp["bare_chi"]["binding"] is False


def test_thermal_ceiling_advisory_at_p0():
    # P0 thermal is INCONCLUSIVE or UNBUDGETED → non-binding advisory
    c = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    assert c["binding"] is False
    assert c["name"] == "thermal"


# ---------------------------------------------------------------------------
# corridor composition
# ---------------------------------------------------------------------------

def _ceiling(name: str, eps: float | None, binding: bool) -> Ceiling:
    return Ceiling(name=name, epsilon_ceiling=eps, binding=binding, status="test")


def test_corridor_open_when_no_binding_ceiling():
    rep = corridor(0.3, [_ceiling("thermal", None, False)])
    assert rep["epsilon_max"] == 1.0
    assert rep["binding_ceiling"] is None
    assert rep["feasible"] is True
    assert rep["success"] is True  # success without reaching ε=1


def test_corridor_bounded_by_tightest_ceiling():
    rep = corridor(0.3, [_ceiling("contestability", 0.7, True),
                         _ceiling("ecological", 0.55, True)])
    assert rep["epsilon_max"] == pytest.approx(0.55)
    assert rep["binding_ceiling"] == "ecological"
    assert rep["width"] == pytest.approx(0.25)
    assert rep["success"] is True


def test_corridor_closed_when_floor_exceeds_ceiling():
    # A closed corridor is a reportable result, not a bug: the survival floor sits
    # above the tightest ceiling, so no ε satisfies both. Composition-level test —
    # the ceiling is supplied, not derived, precisely because which contestability
    # axis produced it is the caller's decision (see the axes tests above).
    rep = corridor(0.52, [_ceiling("contestability", 0.29, True)])
    assert rep["feasible"] is False
    assert rep["success"] is False
    assert rep["width"] < 0.0
    assert "closed" in rep["note"]


def test_corridor_success_does_not_require_epsilon_1():
    # a feasible band topping out well below 1 is still a success
    rep = corridor(0.2, [_ceiling("thermal", 0.6, True)])
    assert rep["epsilon_max"] == pytest.approx(0.6)
    assert rep["success"] is True


def test_corridor_end_to_end_on_the_adopted_axis():
    """End-to-end on the axis that governs: the corridor is OPEN at defaults."""
    es = survival_floor_epsilon(total_eoh(epsilon=0.40), L_AVAIL)
    t = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    rep = corridor(es, [contestability_ceiling(POP), t])
    assert rep["feasible"] is True
    assert rep["success"] is True
    assert rep["binding_ceiling"] is None


def test_corridor_end_to_end_on_the_superseded_axis_still_closes():
    """The retired axis, run deliberately: thin trust still closes the corridor.

    Kept as the regression anchor for the pre-migration result so the earlier
    finding stays reproducible and attributable to the test that produced it.
    """
    es = survival_floor_epsilon(total_eoh(epsilon=0.40), L_AVAIL)
    t = thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)
    adv = corridor(es, [contestability_ceiling_bare_chi(POP, 5.0e10), t])
    assert adv["feasible"] is False
    good = corridor(es, [contestability_ceiling_bare_chi(POP, 5.0e11), t])
    assert good["success"] is True


# ---------------------------------------------------------------------------
# stability over horizon
# ---------------------------------------------------------------------------

def _report(width: float) -> CorridorReport:
    es = 0.3
    return corridor(es, [_ceiling("x", es + width, True)])


def test_stability_stable():
    s = corridor_stability([_report(0.3), _report(0.31), _report(0.29), _report(0.3)])
    assert s["verdict"] == "STABLE"
    assert s["all_feasible"] is True


def test_stability_breached():
    s = corridor_stability([_report(0.3), _report(-0.1)])
    assert s["verdict"] == "BREACHED"
    assert s["all_feasible"] is False


def test_stability_narrowing():
    s = corridor_stability([_report(0.4), _report(0.3), _report(0.15)])
    assert s["verdict"] == "NARROWING"


def test_stability_rejects_empty():
    with pytest.raises(ValueError):
        corridor_stability([])
