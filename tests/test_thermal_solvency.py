"""
Tests for the fiscal solvency gate (research/thermal_solvency.py).

The gate decides whether the thermal overage may ever reach the ledger, so these
tests pin the pass conditions themselves as much as the verdict — including the
null-load attribution check, which exists because two earlier drafts reported
failures that had nothing to do with the thermal obligation.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import CDR_LABOR_HOURS_PER_TONNE
from hours_eoh.research.thermal_solvency import (
    ARC_EPSILONS,
    breaking_labor_intensity,
    solvency_at_epsilon,
    solvency_gate,
    thermal_flow_eoh,
)


# ---------------------------------------------------------------------------
# attribution — a gate is only informative if its unloaded baseline passes
# ---------------------------------------------------------------------------

def test_null_load_baseline_passes():
    """Without this, a mis-calibrated reference economy reads as a thermal
    failure. Two earlier drafts did exactly that."""
    g = solvency_gate()
    assert g["baseline_passes"] is True
    assert g["attributable"] is True


def test_reference_matches_the_repo_sweep_calibration():
    """The gate must not invent its own economy — an uncalibrated trust balance
    was the first false failure."""
    from hours_eoh.research import thermal_solvency as ts
    assert ts.REF_TRUST_BALANCE == 3.5e10
    assert ts.REF_CAPITAL_AGE_RATIO == 0.30
    assert ts.REF_CAPITAL_STOCK == 2.0e9


# ---------------------------------------------------------------------------
# the flow
# ---------------------------------------------------------------------------

def test_flow_more_than_triples_the_ecological_domain():
    """At the 40-year horizon — one lifetime of responsibility — the drawdown
    obligation is ~2.5 ecological baselines, so the domain more than triples."""
    flow = thermal_flow_eoh(2.0)
    assert flow == pytest.approx(1_789_175, rel=0.01)
    r = solvency_at_epsilon(0.40)
    assert r["load_ratio"] == pytest.approx(3.5, abs=0.05)


def test_horizon_default_is_a_single_lifetime():
    from hours_eoh.data import THERMAL_PROGRAMME_YEARS
    from hours_eoh.research import thermal_solvency as ts
    assert THERMAL_PROGRAMME_YEARS == 40.0
    assert ts.DEFAULT_PROGRAMME_YEARS == THERMAL_PROGRAMME_YEARS
    # 30 yr is the other end of the range considered, and costs 1.33x annually
    assert thermal_flow_eoh(2.0, programme_years=30.0) == pytest.approx(
        thermal_flow_eoh(2.0, programme_years=40.0) * 40.0 / 30.0)


def test_flow_scales_inversely_with_horizon():
    """F9 again: a crash programme concentrates the same job into fewer years."""
    assert thermal_flow_eoh(2.0, programme_years=25) == pytest.approx(
        thermal_flow_eoh(2.0, programme_years=100) * 4.0)


def test_delta_t_default_comes_from_the_chosen_constant():
    """ΔT_max is CHOSEN and dominates everything — it must not be hardcoded in
    the gate, so that revising it moves every downstream figure at once."""
    from hours_eoh.data import THERMAL_DT_LO
    import inspect
    from hours_eoh.research.thermal_solvency import solvency_at_epsilon as f
    assert inspect.signature(f).parameters["delta_t_max"].default == THERMAL_DT_LO


def test_flow_rejects_bad_horizons():
    with pytest.raises(ValueError):
        thermal_flow_eoh(2.0, programme_years=0.0)
    with pytest.raises(ValueError):
        thermal_flow_eoh(2.0, world_population=0.0)


def test_obligation_partly_funds_itself():
    """Injected through the framework's own hook, the obligation raises registered
    EOH and therefore TEH created. Pricing the cost without that income would be
    pessimistic in a way the ledger identity does not license."""
    r = solvency_at_epsilon(0.40)
    assert r["labor_income_loaded"] > r["labor_income_baseline"]


# ---------------------------------------------------------------------------
# the verdict
# ---------------------------------------------------------------------------

def test_gate_passes_at_the_shipped_estimate():
    g = solvency_gate()
    assert g["passes"] is True
    assert g["failures"] == []
    assert len(g["verdicts"]) == len(ARC_EPSILONS)


def test_gate_passes_at_every_epsilon():
    for r in solvency_gate()["verdicts"]:
        assert r["passes"] is True, r["epsilon"]
        assert r["trust_solvent"] and r["levy_feasible"]
        assert r["coequal"] and r["labor_feasible"]


def test_coequality_holds_under_load():
    """Ecological must not become residual while stewardship stays funded."""
    for r in solvency_gate()["verdicts"]:
        assert r["eco_coverage"] >= r["stew_coverage"] - 0.25


def test_labour_is_nowhere_near_binding():
    """The ecological domain, even doubled, is a fraction of a percent of the
    collective's labour capacity — the constraint that binds is fiscal."""
    for r in solvency_gate()["verdicts"]:
        assert r["labor_fraction"] < 0.01


# ---------------------------------------------------------------------------
# the backward query
# ---------------------------------------------------------------------------

def test_backward_query_finds_a_finite_breaking_point():
    b = breaking_labor_intensity()
    assert b["breaking_value"] == pytest.approx(22.9, rel=0.05)
    assert b["shipped_value"] == CDR_LABOR_HOURS_PER_TONNE
    assert b["margin"] == pytest.approx(38.0, rel=0.05)
    assert b["verdict"] == "robust"


def test_trust_solvency_is_the_binding_condition():
    """It is the Trust that gives way first, not labour and not co-equality —
    so the gate's sensitivity is fiscal, which is what makes the margin the
    right thing to report."""
    g = solvency_gate(labor_hours_per_tonne=100.0)
    assert g["passes"] is False
    assert g["failures"] == ["trust_insolvent"]


def test_monotone_in_labour_intensity():
    """More labour per tonne is strictly harder — the property bisection needs."""
    assert solvency_gate(labor_hours_per_tonne=1.0)["passes"] is True
    assert solvency_gate(labor_hours_per_tonne=1000.0)["passes"] is False


def test_verdict_survives_the_policy_knobs():
    """Horizon and threshold are CHOSEN, so the verdict must not depend on a
    generous setting of either. The worst combination — a 25-year crash
    programme at a 1.5 K threshold — still clears by 16×."""
    worst = breaking_labor_intensity(programme_years=25.0, delta_t_max=1.5)
    assert solvency_gate(programme_years=25.0, delta_t_max=1.5)["passes"] is True
    assert worst["margin"] > 10.0
    assert worst["verdict"] == "robust"


def test_allocation_defaults_to_responsibility_and_admits_the_fallback():
    """The rule is responsibility; the reference collective has no emissions
    history, so it must fall back to population AND say so."""
    from hours_eoh.research.thermal_drawdown import allocation_share
    a = allocation_share(1e6, 8.16e9)
    assert a["requested_basis"] == "responsibility"
    assert a["basis_used"] == "population"
    assert "under-charges" in a["caveat"]

    b = allocation_share(1e6, 8.16e9, cumulative_emissions_t=4.0e11,
                         world_cumulative_emissions_t=1.75e12)
    assert b["basis_used"] == "responsibility"
    assert b["caveat"] is None
    assert b["share"] == pytest.approx(4.0e11 / 1.75e12)
    # responsibility can charge a small collective far more than its headcount
    assert b["share"] > a["share"] * 100


def test_slack_threshold_needs_no_drawdown_and_passes_trivially():
    g = solvency_gate(delta_t_max=3.0)
    assert g["passes"] is True
    assert all(r["thermal_flow_eoh"] == 0.0 for r in g["verdicts"])
