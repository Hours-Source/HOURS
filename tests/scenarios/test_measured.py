"""
Tests for scenarios/measured.py — the measured-registry bridge into simulation
and dashboard.

Verifies the registry reprices coherently across the ε arc, feeds
population_weighted_mean_multiplier and system_dashboard as a drop-in for
DEFAULT_SEGMENTS, and seeds run_simulation with a measured mean multiplier.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.multipliers import population_weighted_mean_multiplier
from hours_eoh.core.dashboard import system_dashboard
from hours_eoh.core.simulation import make_economy_state
from hours_eoh.data import M_BAND_LOW, M_BAND_HIGH, M_GEOMETRIC_R
from hours_eoh.scenarios.measured import (
    measured_segments,
    measured_mean_multiplier,
    measured_mean_multiplier_schedule,
    run_measured_simulation,
)

ARC = [0.0, 0.40, 0.99]


def test_measured_segments_default_fractions_sum_to_one():
    segs = measured_segments()
    assert len(segs) == 751
    assert sum(s["fraction"] for s in segs) == pytest.approx(1.0, abs=1e-9)
    assert all(1.0 <= s["mean_mu"] <= M_GEOMETRIC_R + 1e-9 for s in segs)


def test_measured_mean_default_matches_frozen_registry():
    assert measured_mean_multiplier() == pytest.approx(1.9964, abs=1e-3)
    # segments feed the core function to the same value
    m = population_weighted_mean_multiplier(measured_segments())
    assert m == pytest.approx(1.9964, abs=1e-3)


def test_measured_mean_epsilon_040_equals_default():
    # default path reads the stored 3-decimal reference_multiplier column;
    # the ε=0.40 path recomputes from f_ columns at full precision — they agree
    # to storage precision (the epoch weights equal the frozen weights at ε=0.40).
    assert measured_mean_multiplier(0.40) == pytest.approx(measured_mean_multiplier(), abs=1e-3)


@pytest.mark.parametrize("eps", ARC)
def test_measured_mean_in_band_across_arc(eps):
    m = measured_mean_multiplier(eps)
    assert M_BAND_LOW <= m <= M_BAND_HIGH


@pytest.mark.parametrize("eps", ARC)
def test_measured_segments_repriced_valid(eps):
    segs = measured_segments(eps)
    assert len(segs) == 751
    assert sum(s["fraction"] for s in segs) == pytest.approx(1.0, abs=1e-9)
    assert all(1.0 <= s["mean_mu"] <= M_GEOMETRIC_R + 1e-9 for s in segs)


def test_measured_segments_drive_dashboard_condition_ii():
    # measured registry is a drop-in for DEFAULT_SEGMENTS in system_dashboard
    snap = system_dashboard(
        epsilon=0.40,
        teh_created=1_000_000.0, teh_destroyed=850_000.0, teh_observed=150_000.0,
        balance_start=1_000_000.0, earnings=100_000.0, expenditures=90_000.0,
        balance_end=1_010_000.0,
        certified_by_domain={}, workforce_size=600_000.0,
        total_eoh=1_000_000.0, fulfilled_eoh=800_000.0,
        deferred_eoh=0.0, time_deferred=0.0,
        trust_balance=1_000_000.0, labor_income=1_000_000.0,
        capital_stock_teh=2_000_000_000.0, capital_age_ratio=0.5,
        population=1_000_000.0, floor_teh=1000.0,
        segments=measured_segments(0.40),
    )
    assert snap["condition_ii"]["mean_multiplier"] == pytest.approx(1.9964, abs=1e-3)


def test_schedule_length_and_values():
    sched = measured_mean_multiplier_schedule(ARC)
    assert len(sched) == 3
    assert sched[1] == pytest.approx(1.9964, abs=1e-3)


def test_run_measured_simulation_uses_measured_mean():
    state = make_economy_state()
    res = run_measured_simulation(state, epsilons=[0.2, 0.4, 0.6], n_periods=3)
    traj = res["summary"]["mean_multiplier_trajectory"]
    assert len(traj) == 3
    # every period drew a measured (in-band) multiplier, not the 2.10 default
    assert all(M_BAND_LOW <= m <= M_BAND_HIGH for m in traj)
    assert traj[1] == pytest.approx(1.9964, abs=1e-3)


def test_run_measured_simulation_static_seed():
    state = make_economy_state()
    res = run_measured_simulation(state, n_periods=2)
    traj = res["summary"]["mean_multiplier_trajectory"]
    assert all(m == pytest.approx(1.9964, abs=1e-3) for m in traj)
