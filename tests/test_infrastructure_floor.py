"""
Tests for the B+D infrastructure-EOH design: the measured statutory floor and the
convention/measurement split.

core/eoh_generation.py: infrastructure_statutory_floor, infrastructure_eoh_breakdown
scenarios/infrastructure_floor.py: doctrine invariance (the gap-closing proof)

Arc coverage at ε ∈ {0.0, 0.40, 0.99}.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import (
    infrastructure_eoh,
    infrastructure_statutory_floor,
    infrastructure_eoh_breakdown,
)
from hours_eoh.scenarios.infrastructure_floor import (
    census_from_condition_counts,
    condition_census_floor,
    doctrine_floor_invariance,
    epsilon_from_floor,
    PA_2025_BRIDGE_COUNTS,
)

ARC = [0.0, 0.40, 0.99]
CENSUS = [
    {"count": 8019, "hours_per_unit_year": 8.0},
    {"count": 12482, "hours_per_unit_year": 20.0},
    {"count": 2813, "hours_per_unit_year": 48.0},
]


# ---------------------------------------------------------------------------
# statutory floor
# ---------------------------------------------------------------------------

def test_statutory_floor_worked_example():
    assert infrastructure_statutory_floor(CENSUS) == pytest.approx(448816.0)


def test_statutory_floor_empty_is_zero():
    assert infrastructure_statutory_floor([]) == 0.0


def test_statutory_floor_rejects_negative():
    with pytest.raises(ValueError):
        infrastructure_statutory_floor([{"count": -1.0, "hours_per_unit_year": 8.0}])


def test_statutory_floor_rejects_missing_key():
    with pytest.raises(ValueError):
        infrastructure_statutory_floor([{"count": 10.0}])


# ---------------------------------------------------------------------------
# breakdown — backward compatibility (the regression anchor)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", [None, *ARC])
def test_scalar_fallback_total_equals_infrastructure_eoh(eps):
    stock = 2_000_000_000.0
    base = infrastructure_eoh(stock, 0.5, eps)
    bd = infrastructure_eoh_breakdown(capital_stock=stock, capital_age_ratio=0.5, epsilon=eps)
    assert bd["total"] == pytest.approx(base)
    assert bd["audited"] is False


def test_breakdown_requires_census_or_stock():
    with pytest.raises(ValueError):
        infrastructure_eoh_breakdown()


# ---------------------------------------------------------------------------
# breakdown — census path
# ---------------------------------------------------------------------------

def test_census_path_is_audited():
    bd = infrastructure_eoh_breakdown(asset_census=CENSUS)
    assert bd["audited"] is True
    assert bd["statutory_floor"] == pytest.approx(448816.0)


@pytest.mark.parametrize("eps", ARC)
def test_census_floor_is_epsilon_invariant(eps):
    # the physical floor does not depend on automation level
    bd = infrastructure_eoh_breakdown(asset_census=CENSUS, epsilon=eps)
    assert bd["statutory_floor"] == pytest.approx(448816.0)


def test_breakdown_terms_sum_to_total():
    bd = infrastructure_eoh_breakdown(
        asset_census=CENSUS, discretionary_eoh=100_000.0,
        deferred_stock=50_000.0, monitoring_capability=0.7,
    )
    assert bd["visible_deferred"] == pytest.approx(35_000.0)
    assert bd["total"] == pytest.approx(
        bd["statutory_floor"] + bd["discretionary"] + bd["visible_deferred"]
    )


def test_assessment_id_recorded():
    bd = infrastructure_eoh_breakdown(asset_census=CENSUS, assessment_id="preservation")
    assert bd["assessment_id"] == "preservation"


# ---------------------------------------------------------------------------
# scenario — the doctrine-invariance proof
# ---------------------------------------------------------------------------

def test_census_builder_shape():
    census = census_from_condition_counts(1.0, 2.0, 3.0)
    assert [b["count"] for b in census] == [1.0, 2.0, 3.0]


def test_doctrine_floor_invariance_restores_determinacy():
    r = doctrine_floor_invariance()
    # the finding: the measured floor does not move with the doctrine (was 10.26x)
    assert r["floor_spread"] == pytest.approx(1.0)
    assert r["determinacy_restored"] is True
    # all doctrine floors are identical
    assert len(set(round(v, 6) for v in r["floors"].values())) == 1


def test_doctrine_total_moves_only_via_discretionary():
    r = doctrine_floor_invariance()
    # totals differ (convention still has an effect) but ONLY through the
    # explicitly-labelled discretionary term, not the physical floor
    assert r["total_spread"] > 1.0


@pytest.mark.parametrize("eps", ARC)
def test_condition_census_floor_valid_across_arc(eps):
    bd = condition_census_floor(*PA_2025_BRIDGE_COUNTS, epsilon=eps)
    assert bd["statutory_floor"] == pytest.approx(448816.0)
    assert bd["total"] >= bd["statutory_floor"]


def test_epsilon_from_floor_single_valued():
    # numerator sized to read 0.40 against the floor; single-valued (no [0.04,0.40] band)
    floor = condition_census_floor(*PA_2025_BRIDGE_COUNTS)["statutory_floor"]
    eps = epsilon_from_floor(0.40 * floor)
    assert eps == pytest.approx(0.40)


def test_epsilon_from_floor_rejects_zero_floor():
    with pytest.raises(ValueError):
        epsilon_from_floor(1000.0, counts=(0.0, 0.0, 0.0))
