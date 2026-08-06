"""
Tests for the thermal overage (research/thermal_overage.py).

Pins the reframing's load-bearing claims: the overage decomposition and the
finding that waste heat is a few percent of it, the zeroing requirement and its
feasibility floor, the carbon-determined automation ceiling, and ε-arc coherence.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    THERMAL_F_NET_ERF,
    THERMAL_F_ANTHRO_ERF,
    THERMAL_LAMBDA_FEEDBACK,
    A_EARTH_M2,
)
from hours_eoh.research.thermal_overage import (
    phi_at_epsilon,
    thermal_overage,
    forcing_required_for_zero,
    post_decarbonization_ceiling,
    overage_arc,
    overage_epsilon_arc,
)
from hours_eoh.research.thermal_path_c import world_dissipation


# ---------------------------------------------------------------------------
# O = Φ + (F − λΔT)·A
# ---------------------------------------------------------------------------

def test_overage_reproduces_at_2k():
    o = thermal_overage(2.0)
    assert o["overage_w"] / 1e12 == pytest.approx(510.5, abs=1.0)
    assert o["is_overage"] is True


def test_decomposition_sums_to_total():
    o = thermal_overage(2.0)
    assert o["forcing_term_w"] + o["heat_term_w"] == pytest.approx(o["overage_w"])


def test_heat_is_a_few_percent_of_the_overage():
    """The headline: eliminating EVERY net-additive watt on Earth closes only a
    few percent of the overage. Zeroing is reachable only through forcing."""
    for dt in (1.5, 2.0, 2.5):
        o = thermal_overage(dt)
        assert o["heat_share"] is not None
        assert 0.02 < o["heat_share"] < 0.09, dt


def test_sign_flips_at_the_budget_opening_threshold():
    """Below F/λ the overage is positive; above it there is slack."""
    opens_at = THERMAL_F_NET_ERF / THERMAL_LAMBDA_FEEDBACK
    assert thermal_overage(opens_at - 0.2)["is_overage"] is True
    assert thermal_overage(opens_at + 0.2)["is_overage"] is False


def test_overage_strictly_decreasing_in_threshold():
    vals = [thermal_overage(dt)["overage_w"] for dt in (1.5, 2.0, 2.5, 3.0)]
    assert all(a > b for a, b in zip(vals, vals[1:]))


def test_slack_reports_no_heat_share():
    o = thermal_overage(3.0)
    assert o["is_overage"] is False
    assert o["heat_share"] is None      # a share of a negative overage is meaningless


def test_uses_total_not_anthropogenic_forcing():
    """C4: the BUDGET side uses total ERF — natural forcing consumes the
    allowance regardless of cause. Only the reachable target is bounded by the
    removable forcing (see the zeroing tests)."""
    total = thermal_overage(2.0)["overage_w"]
    anthro = thermal_overage(2.0, f_total=THERMAL_F_ANTHRO_ERF)["overage_w"]
    assert total > anthro
    assert total - anthro == pytest.approx(
        (THERMAL_F_NET_ERF - THERMAL_F_ANTHRO_ERF) * A_EARTH_M2, rel=1e-9
    )


def test_pipeline_is_reported_with_every_overage():
    """The equilibrium frame must be visible at the point of use (§10.3)."""
    o = thermal_overage(2.0)
    assert o["committed_delta_t"] == pytest.approx(2.805, abs=0.005)
    assert o["pipeline_delta_t"] == pytest.approx(1.575, abs=0.01)
    assert o["pipeline_delta_t"] > 0.0


# ---------------------------------------------------------------------------
# zeroing
# ---------------------------------------------------------------------------

def test_reduction_required_at_2k():
    z = forcing_required_for_zero(2.0)
    assert z["reduction_required"] == pytest.approx(1.0, abs=0.005)
    assert z["share_of_removable"] == pytest.approx(0.322, abs=0.005)
    assert z["feasible"] is True


def test_zeroing_closes_the_overage_exactly():
    """Applying the derived reduction must drive O to zero — the definition."""
    z = forcing_required_for_zero(2.0)
    o = thermal_overage(2.0, f_total=z["forcing_required"])
    assert o["overage_w"] == pytest.approx(0.0, abs=1e6)


def test_feasibility_floor_is_the_carbon_verdict():
    """Even at zero anthropogenic forcing, natural forcing plus present waste
    heat commits only ~0.25 K. Waste heat alone never exhausts the allowance —
    the wall is carbon, and a decarbonization path to zero always exists."""
    z = forcing_required_for_zero(2.0)
    assert z["feasibility_floor_k"] == pytest.approx(0.247, abs=0.005)
    for dt in (1.5, 2.0, 2.5):
        assert forcing_required_for_zero(dt)["feasible"] is True, dt


def test_infeasible_below_the_floor():
    z = forcing_required_for_zero(0.1)
    assert z["feasible"] is False
    assert z["reduction_required"] > z["removable_forcing"]


# ---------------------------------------------------------------------------
# the ceiling is carbon-determined
# ---------------------------------------------------------------------------

def test_ceiling_exists_only_after_drawdown():
    """At a defensible threshold there is NO pre-decarbonization ceiling — the
    budget is zero — while post-drawdown ε_max is ~20×. F4 with a number."""
    c = post_decarbonization_ceiling(2.0)
    assert c["epsilon_max_pre_allocated"] is None
    assert c["carbon_determined"] is True
    assert c["epsilon_max_post_allocated"] == pytest.approx(19.7, abs=0.5)
    assert c["epsilon_max_post_gross"] > c["epsilon_max_post_allocated"]


def test_at_a_lax_threshold_a_pre_decarbonization_ceiling_exists():
    c = post_decarbonization_ceiling(3.0)
    assert c["epsilon_max_pre_allocated"] == pytest.approx(2.16, abs=0.05)
    assert c["carbon_determined"] is False
    assert c["epsilon_max_post_allocated"] > c["epsilon_max_pre_allocated"]


def test_post_decarbonization_ceiling_is_non_binding():
    """Heat becomes binding only at ~20× full automation at present intensity."""
    for dt in (2.0, 2.5, 3.0):
        assert post_decarbonization_ceiling(dt)["epsilon_max_post_allocated"] > 10.0


# ---------------------------------------------------------------------------
# ε-arc coherence
# ---------------------------------------------------------------------------

def test_phi_at_epsilon_reference_point():
    assert phi_at_epsilon(0.40) == pytest.approx(world_dissipation())
    assert phi_at_epsilon(0.0) == 0.0


def test_phi_at_epsilon_rejects_zero_reference():
    with pytest.raises(ValueError):
        phi_at_epsilon(0.5, eps_reference=0.0)


def test_arc_meaningful_at_all_key_epsilons():
    rows = overage_epsilon_arc(2.0, (0.0, 0.40, 0.90, 0.99))
    assert all(r["overage_w"] > 0.0 for r in rows)
    assert rows[0]["heat_term_w"] == 0.0                      # ε=0: no machine dissipation
    heat = [r["heat_term_w"] for r in rows]
    assert all(a <= b for a, b in zip(heat, heat[1:]))        # monotone in ε


def test_automation_is_not_what_breaks_the_budget():
    """Across the WHOLE arc the heat share stays under a tenth: the overage is
    carbon at every ε, not just today's."""
    rows = overage_epsilon_arc(2.0, (0.0, 0.40, 0.90, 0.99))
    assert (rows[-1]["heat_share"] or 0.0) < 0.10
    # and the overage barely moves across the full arc
    assert rows[-1]["overage_w"] / rows[0]["overage_w"] < 1.15


def test_no_discontinuity_approaching_full_automation():
    near = overage_epsilon_arc(2.0, (0.98, 0.99, 1.0))
    diffs = [b["overage_w"] - a["overage_w"] for a, b in zip(near, near[1:])]
    assert all(d > 0.0 for d in diffs)
    assert max(diffs) / min(diffs) < 2.0


# ---------------------------------------------------------------------------
# the arc table
# ---------------------------------------------------------------------------

def test_overage_arc_pairs_debt_with_its_price():
    rows = overage_arc()
    assert len(rows) == 7
    for r in rows:
        assert {"overage_w", "reduction_required", "feasible"} <= set(r)
    # the sweep spans overage into slack
    assert rows[0]["is_overage"] is True
    assert rows[-1]["is_overage"] is False
