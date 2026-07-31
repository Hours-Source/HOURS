"""
Tests for the measured-data geometric reference multiplier (mult-5.1.0).

Covers core/multipliers.py: composite_from_factors, impact_composite_from_subdomains,
reference_multiplier, epoch_factor_weights — and their agreement with the frozen
O*NET/BLS registry in reference/onet_multipliers.py.

Arc coverage at ε ∈ {0.0, 0.40, 0.99} per the ε-coherence rule.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.core.multipliers import (
    composite_from_factors,
    impact_composite_from_subdomains,
    reference_multiplier,
    epoch_factor_weights,
)
from hours_eoh.data import (
    M_FLOOR, M_GEOMETRIC_R, M_FACTOR_WEIGHTS, M_EPOCH_WEIGHT_ANCHORS,
)
from hours_eoh.reference.onet_multipliers import (
    load_registry, load_reference_bounds, registry_segments,
)
from hours_eoh.core.multipliers import population_weighted_mean_multiplier


ARC = [0.0, 0.40, 0.99]


# ---------------------------------------------------------------------------
# reference_multiplier — geometric map
# ---------------------------------------------------------------------------

def test_reference_multiplier_bounds():
    # z clips to [0,1] -> m in [floor, floor*R]
    assert reference_multiplier(-5.0) == pytest.approx(M_FLOOR)
    assert reference_multiplier(5.0) == pytest.approx(M_FLOOR * M_GEOMETRIC_R)


def test_reference_multiplier_monotonic():
    xs = [i / 20 for i in range(21)]
    ms = [reference_multiplier(x) for x in xs]
    assert all(b >= a for a, b in zip(ms, ms[1:]))


def test_reference_multiplier_chief_executives():
    # composite 0.5789 -> 2.325 (registry)
    assert reference_multiplier(0.5789491557820804) == pytest.approx(2.325, abs=1e-3)


def test_reference_multiplier_rejects_bad_range():
    with pytest.raises(ValueError):
        reference_multiplier(0.5, z_lo=0.7, z_hi=0.7)


# ---------------------------------------------------------------------------
# composite / impact reconstruction
# ---------------------------------------------------------------------------

def test_composite_frozen_weights_reproduce_registry_column():
    for r in load_registry()[:50]:
        fi = impact_composite_from_subdomains(
            r["i_dependency"], r["i_substitutability"], r["i_harm"], r["i_temporal"]
        )
        assert fi == pytest.approx(r["f_impact"], abs=1e-9)
        comp = composite_from_factors(r["f_training"], r["f_demand"], r["f_scarcity"], fi)
        assert comp == pytest.approx(r["composite"], abs=1e-9)


def test_full_registry_reproduces_reference_multiplier():
    max_err = 0.0
    for r in load_registry():
        fi = impact_composite_from_subdomains(
            r["i_dependency"], r["i_substitutability"], r["i_harm"], r["i_temporal"]
        )
        comp = composite_from_factors(r["f_training"], r["f_demand"], r["f_scarcity"], fi)
        max_err = max(max_err, abs(reference_multiplier(comp) - r["reference_multiplier"]))
    # only the registry's 3-decimal storage separates us from exact
    assert max_err < 1e-3


def test_composite_rejects_out_of_range_factor():
    with pytest.raises(ValueError):
        composite_from_factors(1.1, 0.5, 0.5, 0.5)


def test_impact_rejects_bad_bounds():
    with pytest.raises(ValueError):
        impact_composite_from_subdomains(0.5, 0.5, 0.5, 0.5, lo=0.8, hi=0.8)


# ---------------------------------------------------------------------------
# epoch_factor_weights — ε-coherence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", ARC)
def test_epoch_weights_sum_to_one(eps):
    w = epoch_factor_weights(eps)
    assert len(w) == 4
    assert math.isclose(sum(w), 1.0, abs_tol=1e-9)
    assert all(x >= 0.0 for x in w)


@pytest.mark.parametrize("eps", ARC)
def test_epoch_weights_produce_valid_multiplier(eps):
    # a mid-range worker priced under arc weights stays in [floor, floor*R]
    w = epoch_factor_weights(eps)
    comp = composite_from_factors(0.6, 0.5, 0.4, 0.55, weights=w)
    m = reference_multiplier(comp)
    assert M_FLOOR <= m <= M_FLOOR * M_GEOMETRIC_R + 1e-9


def test_epoch_weights_at_040_equal_frozen_weights():
    assert epoch_factor_weights(0.40) == pytest.approx(M_FACTOR_WEIGHTS)


def test_epoch_weights_impact_rises_with_epsilon():
    impact = [epoch_factor_weights(e)[3] for e in [0.0, 0.4, 0.9, 0.99]]
    assert all(b >= a for a, b in zip(impact, impact[1:]))
    # copy/merge limit: impact dominates
    assert epoch_factor_weights(0.99)[3] > 0.5


def test_epoch_weights_clamp_outside_range():
    assert epoch_factor_weights(-0.5) == pytest.approx(M_EPOCH_WEIGHT_ANCHORS[0.0])
    assert epoch_factor_weights(2.0) == pytest.approx(M_EPOCH_WEIGHT_ANCHORS[0.99])


def test_epoch_weights_interpolation_midpoint():
    # ε=0.65 sits between the 0.40 and 0.90 anchors
    w = epoch_factor_weights(0.65)
    lo = M_EPOCH_WEIGHT_ANCHORS[0.40]
    hi = M_EPOCH_WEIGHT_ANCHORS[0.90]
    for i in range(4):
        assert min(lo[i], hi[i]) <= w[i] <= max(lo[i], hi[i])


# ---------------------------------------------------------------------------
# registry loader integration
# ---------------------------------------------------------------------------

def test_registry_loads_751_occupations():
    rows = load_registry()
    assert len(rows) == 751
    assert all(1.0 <= r["reference_multiplier"] <= M_GEOMETRIC_R + 1e-9 for r in rows)


def test_registry_segments_reproduce_weighted_mean():
    m = population_weighted_mean_multiplier(registry_segments())
    # frozen baseline is 1.9993 over 742; the 751-row registry adds 9 Mode-A rows
    assert m == pytest.approx(1.9964, abs=1e-3)


def test_reference_bounds_frozen_values():
    b = load_reference_bounds()
    assert b["R"] == M_GEOMETRIC_R
    assert b["floor"] == M_FLOOR
    assert b["frozen"] is True
