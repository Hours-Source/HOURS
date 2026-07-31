"""
Tests for scenarios/multiplier_sensitivity.py — the map-agnostic robustness harness.

Verifies: baseline reconstruction matches the registry, rank ordering is robust
under the CHOSEN-constant sweeps (the falsifiable claim), ε-coherence across the
arc, and Monte-Carlo determinism.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.scenarios.multiplier_sensitivity import (
    reconstruct,
    spearman,
    pairwise_ratios,
    sweep_factor_weights,
    sweep_impact_subdomain_weights,
    epsilon_arc,
    monte_carlo_factor_weights,
    sensitivity_report,
)
from hours_eoh.reference.onet_multipliers import load_registry


def test_baseline_reconstructs_registry():
    rows = load_registry()
    run = reconstruct(rows)
    max_err = max(abs(m - r["reference_multiplier"]) for m, r in zip(run["multiplier"], rows))
    assert max_err < 1e-3
    assert run["weighted_mean"] == pytest.approx(1.9964, abs=1e-3)


def test_spearman_identity_and_reverse():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert spearman(xs, xs) == pytest.approx(1.0)
    assert spearman(xs, xs[::-1]) == pytest.approx(-1.0)


def test_pairwise_ratios_present():
    run = reconstruct()
    ratios = pairwise_ratios(run)
    # anesthesiologist mints above a nursing assistant
    assert ratios["anesthesiologist_over_nursing_assistant"] > 1.0


def test_factor_weight_sweep_rank_robust():
    results = sweep_factor_weights(delta=0.10)
    assert len(results) == 8  # 4 factors x ±
    # rank ordering survives every ±0.10 perturbation (the falsifiable claim)
    assert all(p["spearman_vs_baseline"] > 0.90 for p in results)
    # pairwise ratios drift only modestly
    assert all(p["min_pairwise_ratio_drift"] < 0.30 for p in results)


def test_impact_subdomain_sweep_runs():
    results = sweep_impact_subdomain_weights(delta=0.10)
    assert len(results) == 8
    assert all(p["spearman_vs_baseline"] > 0.85 for p in results)


@pytest.mark.parametrize("eps", [0.0, 0.40, 0.99])
def test_epsilon_arc_valid_at_each_point(eps):
    results = epsilon_arc(arc=(eps,))
    assert len(results) == 1
    p = results[0]
    assert 1.0 <= p["weighted_mean"] <= 3.2
    assert math.isfinite(p["spearman_vs_baseline"])


def test_epsilon_040_reproduces_baseline():
    (p,) = epsilon_arc(arc=(0.40,))
    assert p["spearman_vs_baseline"] == pytest.approx(1.0, abs=1e-9)


def test_epsilon_099_reorders_toward_impact():
    (p0,) = epsilon_arc(arc=(0.0,))
    (p99,) = epsilon_arc(arc=(0.99,))
    # the high-ε repricing departs further from the ε=0.40 baseline than ε=0 does
    assert p99["spearman_vs_baseline"] < p0["spearman_vs_baseline"]


def test_monte_carlo_deterministic():
    a = monte_carlo_factor_weights(n_draws=100, seed=42)
    b = monte_carlo_factor_weights(n_draws=100, seed=42)
    assert a == b
    # rank ordering is robust across the simplex (v5 reported p5 ~0.82)
    assert a["spearman_p5"] > 0.80
    assert 0.0 <= a["band_pass_fraction"] <= 1.0


def test_sensitivity_report_structure():
    r = sensitivity_report(n_draws=50, seed=0)
    assert r["baseline_weighted_mean"] == pytest.approx(1.9964, abs=1e-3)
    assert len(r["factor_weight_sweep"]) == 8
    assert len(r["impact_subdomain_sweep"]) == 8
    assert len(r["epsilon_arc"]) == 3
    # honest about what it cannot sweep from the registry
    assert any("normalization" in s for s in r["not_swept"])
