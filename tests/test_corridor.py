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
    survival_inventory,
    survival_floor,
    overbuild_floor,
    Floor,
    contestability_ceiling,
    contestability_ceiling_bare_chi,
    contestability_axes,
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


# ---------------------------------------------------------------------------
# The survival-floor correction (Block I, 2026-08-06)
#
# ε_suff was being computed from an inventory at the OPERATING personal standard
# — a sufficiency-shaped number — and reported as a survival floor. At the
# survival standard the floor is 0: subsistence survives without automation.
# ---------------------------------------------------------------------------

def test_survival_floor_is_zero_at_the_survival_standard():
    """The correction. Subsistence survives with no automation, as it did."""
    assert survival_floor_epsilon(survival_inventory(epsilon=0.0), L_AVAIL) == 0.0


def test_the_three_standards_give_three_different_floors():
    """All three are meaningful; only the first is a survival floor."""
    from hours_eoh.core.eoh_generation import total_eoh as _t
    surv = survival_floor_epsilon(survival_inventory(epsilon=0.0), L_AVAIL)
    oper = survival_floor_epsilon(_t(epsilon=0.0), L_AVAIL)
    suff = survival_floor_epsilon(
        _t(epsilon=0.0, personal_standard="sufficiency"), L_AVAIL)
    assert surv == 0.0
    assert oper == pytest.approx(0.306, abs=0.005)
    assert suff == pytest.approx(0.530, abs=0.005)
    assert surv < oper < suff


@pytest.mark.parametrize("eps", ARC)
def test_survival_floor_stays_zero_across_the_arc(eps):
    """Automation only ever relieves the survival floor; it never creates one."""
    assert survival_floor_epsilon(survival_inventory(epsilon=eps), L_AVAIL) == 0.0


def test_survival_inventory_rejects_a_conflicting_standard():
    with pytest.raises(TypeError):
        survival_inventory(personal_standard="sufficiency")


def test_corridor_opens_fully_on_the_survival_floor():
    """With ε_suff = 0 and nothing binding above, the band is the whole arc."""
    es = survival_floor_epsilon(survival_inventory(epsilon=0.40), L_AVAIL)
    rep = corridor(es, [contestability_ceiling(POP),
                        thermal_ceiling(1.86e10, 2.5e9, epsilon=0.40)])
    assert rep["epsilon_suff"] == 0.0
    assert rep["width"] == pytest.approx(1.0)
    assert rep["success"] is True


# ---------------------------------------------------------------------------
# Block III — two lower bounds, not one
#
# A collective can be infeasible for two independent reasons: it cannot survive,
# or it is not worth being in. The band's floor is the max over both.
# ---------------------------------------------------------------------------

class TestTwoFloors:

    def test_scalar_floor_is_backward_compatible(self):
        rep = corridor(0.3, [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == pytest.approx(0.3)
        assert rep["binding_floor"] == "survival"

    def test_no_binding_floor_reports_none(self):
        rep = corridor([survival_floor(survival_inventory(epsilon=0.40), L_AVAIL)],
                       [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == 0.0
        assert rep["binding_floor"] is None

    def test_modest_apparatus_does_not_bind(self):
        f = overbuild_floor(1.9e9, POP)
        assert f["binding"] is False
        assert f["epsilon_floor"] == 0.0
        assert "pays at any" in f["status"]

    def test_huge_apparatus_binds_the_floor(self):
        f = overbuild_floor(1.0e11, POP)
        assert f["binding"] is True
        assert 0.0 < f["epsilon_floor"] < 1.0
        assert "worth being in only at" in f["status"]

    def test_binding_floor_is_the_max(self):
        surv = Floor(name="survival", epsilon_floor=0.20, binding=True, status="x")
        over = Floor(name="overbuild", epsilon_floor=0.55, binding=True, status="y")
        rep = corridor([surv, over], [_ceiling("thermal", None, False)])
        assert rep["epsilon_suff"] == pytest.approx(0.55)
        assert rep["binding_floor"] == "overbuild"

    def test_overbuild_can_close_a_corridor_survival_would_not(self):
        """The new failure mode: not 'we would die' but 'we are better off apart'."""
        surv = Floor(name="survival", epsilon_floor=0.0, binding=False, status="x")
        over = overbuild_floor(1.0e11, POP)
        rep = corridor([surv, over], [_ceiling("contestability", 0.30, True)])
        assert rep["feasible"] is False
        assert rep["binding_floor"] == "overbuild"
        assert "overbuild floor exceeds" in rep["note"]

    def test_floors_are_echoed_for_audit(self):
        floors = [survival_floor(survival_inventory(epsilon=0.40), L_AVAIL),
                  overbuild_floor(1.9e9, POP)]
        rep = corridor(floors, [_ceiling("thermal", None, False)])
        assert [f["name"] for f in rep["floors"]] == ["survival", "overbuild"]

    @pytest.mark.parametrize("eps", ARC)
    def test_arc_coherent_with_both_floors(self, eps):
        floors = [survival_floor(survival_inventory(epsilon=eps), L_AVAIL),
                  overbuild_floor(1.9e9, POP)]
        rep = corridor(floors, [contestability_ceiling(POP)])
        assert 0.0 <= rep["epsilon_suff"] <= 1.0
        assert rep["success"] is True
