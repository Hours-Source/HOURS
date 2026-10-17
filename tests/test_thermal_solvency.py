"""Tests for the fiscal solvency gate (research/thermal_solvency.py).

The gate decides whether the thermal overage may ever reach the ledger. So these tests
pin the pass conditions as well as the verdict, including the null-load attribution
check: two earlier drafts reported failures that had nothing to do with the thermal
obligation.
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
    from hours_eoh.data import TRUST_BASE_TEH
    assert ts.REF_TRUST_BALANCE == TRUST_BASE_TEH
    assert ts.REF_CAPITAL_AGE_RATIO == 0.30
    assert ts.REF_CAPITAL_STOCK == 2.0e9


# ---------------------------------------------------------------------------
# the flow
# ---------------------------------------------------------------------------

def test_flow_more_than_triples_the_ecological_domain():
    """The drawdown obligation is about three orders of magnitude larger than the
    ecological domain, at the PRE-PARTITION policy. The test asserts an order of
    magnitude, not a level. An earlier reading of 3.5 ("more than triples") divided by a
    baseline inflated 464× by the frame mismatch
    ([record](record/thermal.md#thermal-solvency-test-history)).
    """
    flow = thermal_flow_eoh(2.0)
    assert flow == pytest.approx(1_789_175, rel=0.01)
    r = solvency_at_epsilon(0.40)
    assert 1_000.0 < r["load_ratio"] < 3_000.0


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
    """ΔT_max is CHOSEN and dominates everything. The gate must read the constant, not a
    hard-coded copy, so that revising it moves every downstream figure at once.
    """
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
        assert r["labor_feasible"]


def test_the_coequality_condition_is_retired_and_stays_retired():
    """The co-equality condition stays retired (2026-09-16, author decision). It
    compared two Trust FUNDING coverages against a balance that, since the wage
    doctrine, funds neither, so it could not fail. The DOCTRINE is untouched: both
    allocations remain co-equal requirements, paid at the mint. A reader who searches
    for the old keys finds the reason here
    ([record](record/thermal.md#thermal-solvency-test-history)).
    """
    for r in solvency_gate()["verdicts"]:
        for gone in ("coequal", "eco_coverage", "stew_coverage"):
            assert gone not in r, (
                f"{gone} is back in the solvency verdict. It reports a Trust "
                "funding ratio for labour the Trust does not fund; if it is "
                "needed again, the question it answers has changed and the "
                "module docstring should say how."
            )
        assert "ecological_became_residual" not in r["failures"]


def test_labour_is_nowhere_near_binding():
    """The ecological domain, even doubled, is a fraction of a percent of the
    collective's labour capacity at the shipped intensity. (Until 2026-09-15
    this said the binding constraint is fiscal; when the gate breaks it now
    breaks on labour — see test_labour_is_now_the_binding_condition.)"""
    for r in solvency_gate()["verdicts"]:
        assert r["labor_fraction"] < 0.01


# ---------------------------------------------------------------------------
# the backward query
# ---------------------------------------------------------------------------

def test_backward_query_finds_a_finite_breaking_point():
    b = breaking_labor_intensity()
    # 22.9 before the PERSONAL_EOH_BASE reprice; 40.5 after — a smaller
    # ecological/personal ratio means labour intensity has further to travel
    # before it breaks the gate, so the verdict got MORE robust, not less.
    # 40.5 → 44.7: the ecological obligation is unchanged but the total EOH it
    # is measured against shrank, so it takes a larger shock to break solvency.
    # 44.7 → 48.2 (2026-08-16): the mean multiplier moved 2.10 → 1.9964 when the
    # eleven hard-coded `mean_multiplier = 2.10` defaults were bound to the
    # MEASURED registry mean. A smaller multiplier mints less TEH per registered
    # hour, so the fisc is tighter and the shock needed to break it is LARGER —
    # the margin widening here is arithmetic, not an improvement in solvency.
    #
    # NOTE what this test is really pinning: it is the ONLY assertion in the
    # suite that moved when the multiplier that mints all TEH fell 4.9%. The
    # verdict stays "robust" throughout, and it stays robust because the
    # ecological obligation is negligible in the ledger — the domain-balance
    # defect — not because the fisc is strong. That caveat predates this change
    # and is unaffected by it.
    #
    # 48.2 → 335.3 (2026-09-15): minted TEH is the wage, so the Trust no longer
    # pays for ecological and stewardship labour the mint already paid. The
    # loaded ecological requirement stopped reaching Trust solvency at all, and
    # the gate now breaks on LABOUR (see the next test). This is not a stronger
    # fisc: the fiscal conditions went near-vacuous for this question.
    assert b["breaking_value"] == pytest.approx(335.3, rel=0.05)
    assert b["shipped_value"] == CDR_LABOR_HOURS_PER_TONNE
    # 67.6 → 74.5 → 80.3 → 558.9, the last by the same doctrine change.
    assert b["margin"] == pytest.approx(558.9, rel=0.05)
    assert b["verdict"] == "robust"


def test_labour_is_now_the_binding_condition():
    """Labour, not the Trust, now breaks the gate. Under the wage doctrine (2026-09-15)
    the Trust owes only the guarantee, so a thermal overage carried as ecological labour
    cannot make it insolvent. 100 h/t passes and 400 fails, on labour alone.
    """
    assert solvency_gate(labor_hours_per_tonne=100.0)["passes"] is True
    g = solvency_gate(labor_hours_per_tonne=400.0)
    assert g["passes"] is False
    assert g["failures"] == ["labor_unavailable"]


def test_monotone_in_labour_intensity():
    """More labour per tonne is strictly harder — the property bisection needs."""
    assert solvency_gate(labor_hours_per_tonne=1.0)["passes"] is True
    assert solvency_gate(labor_hours_per_tonne=1000.0)["passes"] is False


def test_verdict_survives_the_policy_knobs():
    """Horizon and threshold are CHOSEN, so the verdict must not depend on a generous
    setting of either. The worst combination, a 25-year crash programme at a 1.5 K
    threshold, still clears with a margin above 10×.
    """
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
