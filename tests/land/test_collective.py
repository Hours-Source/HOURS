"""Tests for hours_eoh/land/collective.py"""

from __future__ import annotations

import math
import pytest

from hours_eoh.land.collective import (
    compute_collective_guf,
    make_urban_collective,
    make_rural_collective,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_residential():
    return [{"area_slu": 3.5, "location_value": 0.72, "use_category": "residential_primary"}]


@pytest.fixture
def small_urban():
    return make_urban_collective(20)


@pytest.fixture
def small_rural():
    return make_rural_collective(10)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_missing_area_slu_raises():
    with pytest.raises(ValueError, match="area_slu"):
        compute_collective_guf(
            [{"location_value": 0.5, "use_category": "residential_primary"}], 0.40
        )


def test_missing_location_value_raises():
    with pytest.raises(ValueError, match="location_value"):
        compute_collective_guf(
            [{"area_slu": 3.5, "use_category": "residential_primary"}], 0.40
        )


def test_missing_use_category_raises():
    with pytest.raises(ValueError, match="use_category"):
        compute_collective_guf([{"area_slu": 3.5, "location_value": 0.5}], 0.40)


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------

def test_returns_expected_keys(small_urban):
    result = compute_collective_guf(small_urban, 0.40)
    for key in (
        "epsilon", "parcel_count", "guf_gross_revenue", "subsidies_absorbed",
        "guf_net_inflow", "guf_by_parcel", "psi", "pop_coverage_frac",
    ):
        assert key in result


def test_parcel_count_matches(small_urban):
    result = compute_collective_guf(small_urban, 0.40)
    assert result["parcel_count"] == len(small_urban)


def test_guf_by_parcel_length(small_urban):
    result = compute_collective_guf(small_urban, 0.40)
    assert len(result["guf_by_parcel"]) == len(small_urban)


def test_guf_by_parcel_keys(small_urban):
    result = compute_collective_guf(small_urban, 0.40)
    row = result["guf_by_parcel"][0]
    for key in ("parcel_id", "guf_applied", "base_fee", "eco_surcharge",
                "infra_premium", "psi", "subsidy_amount", "cap_binds"):
        assert key in row


def test_empty_parcels_returns_zero():
    result = compute_collective_guf([], 0.40)
    assert result["parcel_count"] == 0
    assert result["guf_gross_revenue"] == 0.0
    assert result["guf_net_inflow"] == 0.0
    assert result["guf_by_parcel"] == []


# ---------------------------------------------------------------------------
# Revenue and subsidy logic
# ---------------------------------------------------------------------------

def test_guf_net_inflow_positive_urban(small_urban):
    result = compute_collective_guf(small_urban, 0.40)
    assert result["guf_net_inflow"] > 0.0


def test_gross_equals_net_when_no_subsidies(single_residential):
    result = compute_collective_guf(single_residential, 0.40, median_income=0.0)
    assert result["subsidies_absorbed"] == 0.0
    assert result["guf_gross_revenue"] == pytest.approx(result["guf_net_inflow"])


def test_subsidy_reduces_net_inflow():
    parcels = [{
        "area_slu": 3.5,
        "location_value": 0.72,
        "use_category": "residential_primary",
        "occupant_income": 100.0,  # well below median
    }]
    no_sub  = compute_collective_guf(parcels, 0.40, median_income=0.0)
    with_sub = compute_collective_guf(parcels, 0.40, median_income=1_000.0)

    assert with_sub["subsidies_absorbed"] > 0.0
    assert with_sub["guf_net_inflow"] < no_sub["guf_net_inflow"]


def test_subsidies_absorbed_nonnegative(small_urban):
    result = compute_collective_guf(small_urban, 0.40, median_income=500.0)
    assert result["subsidies_absorbed"] >= 0.0


# ---------------------------------------------------------------------------
# Review cycle cap
# ---------------------------------------------------------------------------

def test_cap_reduces_fee_when_binding():
    parcels = [{
        "area_slu": 3.5,
        "location_value": 0.72,
        "use_category": "residential_primary",
        "guf_previous": 0.001,  # very low previous → cap binds immediately
    }]
    result  = compute_collective_guf(parcels, 0.40)
    row     = result["guf_by_parcel"][0]
    assert row["cap_binds"] is True
    # Applied must equal previous × 1.10
    expected_ceiling = 0.001 * 1.10
    assert row["guf_applied"] == pytest.approx(expected_ceiling, rel=1e-6)


def test_cap_does_not_bind_when_low_increase():
    parcels = [{
        "area_slu": 3.5,
        "location_value": 0.72,
        "use_category": "residential_primary",
        "guf_previous": 1_000_000.0,  # huge previous → cap never binds
    }]
    result = compute_collective_guf(parcels, 0.40)
    assert result["guf_by_parcel"][0]["cap_binds"] is False


# ---------------------------------------------------------------------------
# Archetype factories
# ---------------------------------------------------------------------------

def test_make_urban_collective_count():
    for n in (10, 100, 400):
        assert len(make_urban_collective(n)) == n


def test_make_rural_collective_count():
    for n in (10, 50, 200):
        assert len(make_rural_collective(n)) == n


def test_urban_collective_use_categories():
    parcels = make_urban_collective(100)
    cats = {p["use_category"] for p in parcels}
    assert "residential_primary" in cats
    assert "commercial_retail" in cats


def test_rural_collective_use_categories():
    parcels = make_rural_collective(100)
    cats = {p["use_category"] for p in parcels}
    assert "agricultural_active" in cats
    assert "conservation" in cats


def test_urban_guf_exceeds_rural_same_count():
    urban_result = compute_collective_guf(make_urban_collective(100), 0.40)
    rural_result = compute_collective_guf(make_rural_collective(100), 0.40)
    assert urban_result["guf_gross_revenue"] > rural_result["guf_gross_revenue"]


# ---------------------------------------------------------------------------
# Conservation credit
# ---------------------------------------------------------------------------

def test_conservation_parcel_negative_base_fee():
    parcels = [{"area_slu": 50.0, "location_value": 0.15, "use_category": "conservation"}]
    result  = compute_collective_guf(parcels, 0.40)
    row     = result["guf_by_parcel"][0]
    assert row["base_fee"] < 0.0


def test_guf_applied_nonnegative_for_conservation():
    parcels = [{"area_slu": 50.0, "location_value": 0.15, "use_category": "conservation"}]
    result  = compute_collective_guf(parcels, 0.40)
    assert result["guf_by_parcel"][0]["guf_applied"] >= 0.0


# ---------------------------------------------------------------------------
# Boundary ε values
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", [0.0, 0.99])
def test_all_fees_finite_at_extreme_eps(small_urban, eps):
    result = compute_collective_guf(small_urban, eps)
    for row in result["guf_by_parcel"]:
        assert math.isfinite(row["guf_applied"])
        assert row["guf_applied"] >= 0.0
    assert math.isfinite(result["guf_gross_revenue"])
