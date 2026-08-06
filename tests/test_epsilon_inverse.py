"""
Tests for the ε inverse (research/epsilon_inverse.py).

The property that matters: ε is never set, only derived. These pin the
round-trip, the arc coverage a sweep needs, and the non-uniqueness that an
ε-indexed sweep would otherwise hide.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.core.civilization import civilization_epsilon
from hours_eoh.research.epsilon_inverse import (
    COMPUTE_HEAVY_MIX,
    INFRASTRUCTURE_HEAVY_MIX,
    REFERENCE_MIX,
    capital_for_epsilon,
    epsilon_at_scale,
    mix_spread,
)


# ---------------------------------------------------------------------------
# the inverse round-trips through the DERIVATION, not around it
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", [0.20, 0.40, 0.60, 0.90, 0.99])
def test_round_trip_through_civilization_epsilon(target):
    """The returned capital, fed back to core.civilization, must derive the ε
    that was asked for. Nothing anywhere sets ε."""
    r = capital_for_epsilon(target)
    assert r["epsilon_achieved"] == pytest.approx(target, abs=1e-3)
    civ = {"population": 1_000_000.0, "capital": r["capital"]}
    assert civilization_epsilon(civ)["epsilon"] == pytest.approx(target, abs=1e-3)


def test_arc_endpoints():
    """ε = 0 is an empty stock exactly — no capital, no machine fulfilment."""
    r = capital_for_epsilon(0.0)
    assert r["capital"] == {} and r["total_capital_teh"] == 0.0
    assert epsilon_at_scale(0.0) == 0.0


def test_covers_the_whole_arc_a_sweep_needs():
    """CLAUDE.md requires meaningful output across ε ∈ [0, 0.99]."""
    for e in (0.0, 0.40, 0.90, 0.99):
        r = capital_for_epsilon(e)
        assert r["reachable"]
        assert math.isfinite(r["total_capital_teh"])


def test_capital_increases_monotonically_with_epsilon():
    scales = [capital_for_epsilon(e)["scale_teh_per_capita"]
              for e in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert all(a < b for a, b in zip(scales, scales[1:]))


def test_epsilon_is_monotone_in_capital():
    """The property bisection needs. Not obvious a priori: capital appears in
    BOTH terms of ε = machine_EOH / total_EOH, since more capital also generates
    more infrastructure EOH to maintain."""
    eps = [epsilon_at_scale(s) for s in (100, 500, 2000, 8000, 16000)]
    assert all(a < b for a, b in zip(eps, eps[1:]))


def test_rejects_targets_outside_the_arc():
    for bad in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError):
            capital_for_epsilon(bad)
    with pytest.raises(ValueError):
        epsilon_at_scale(-1.0)


# ---------------------------------------------------------------------------
# non-uniqueness — the thing an ε-indexed sweep hides
# ---------------------------------------------------------------------------

def test_same_epsilon_is_not_the_same_economy():
    """Three mixes at ε = 0.40 need materially different capital stocks. A sweep
    indexed by ε alone reports one number for all three."""
    s = mix_spread(0.40)
    assert s["capital_spread"] > 1.2
    totals = {k: v["total_capital_teh"] for k, v in s["mixes"].items()}
    assert len(set(totals.values())) == len(totals)
    for v in s["mixes"].values():
        assert v["epsilon_achieved"] == pytest.approx(0.40, abs=1e-3)


def test_infrastructure_heavy_mix_needs_the_most_capital():
    """It generates the most maintenance obligation per unit of EOH eliminated,
    so it must buy more capital to reach the same ε — the feedback that makes the
    inverse a solver rather than a formula."""
    ref = capital_for_epsilon(0.40, REFERENCE_MIX)["total_capital_teh"]
    infra = capital_for_epsilon(0.40, INFRASTRUCTURE_HEAVY_MIX)["total_capital_teh"]
    compute = capital_for_epsilon(0.40, COMPUTE_HEAVY_MIX)["total_capital_teh"]
    assert infra > ref > compute


def test_spread_carries_its_interpretation():
    s = mix_spread(0.40)
    assert "thermal" in s["note"] or "Φ" in s["note"]
