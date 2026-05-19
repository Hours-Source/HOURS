"""Tests for hours_eoh/land/calibration.py"""

from __future__ import annotations

import math
import pytest

from hours_eoh.land.calibration import guf_rate_calibration, guf_lvi_weight_sensitivity
from hours_eoh.land.collective import make_urban_collective, make_rural_collective


# ---------------------------------------------------------------------------
# guf_rate_calibration
# ---------------------------------------------------------------------------

@pytest.fixture
def small_urban_50():
    return make_urban_collective(50)


@pytest.fixture
def small_rural_50():
    return make_rural_collective(50)


def test_rate_calibration_returns_expected_keys(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 1.0)
    for key in (
        "calibrated_multiplier", "achieved_ratio", "levy_revenue",
        "guf_at_calibrated_k", "target_guf_levy_ratio", "converged",
    ):
        assert key in result


def test_rate_calibration_converges_at_unity(small_urban_50):
    # Use population=50 so that 50 parcels can plausibly produce levy-equivalent GUF
    result = guf_rate_calibration(small_urban_50, 1.0, population=50.0, tolerance=0.10)
    assert result["converged"] is True
    assert abs(result["achieved_ratio"] - 1.0) <= 0.25  # sample approximation ±25%


def test_rate_calibration_multiplier_positive(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 0.5, population=50.0)
    assert result["calibrated_multiplier"] > 0.0


def test_rate_calibration_multiplier_direction_high_target(small_urban_50):
    # Scale population to 50 so both targets are achievable without hitting k-ceiling
    low  = guf_rate_calibration(small_urban_50, 0.5, population=50.0)
    high = guf_rate_calibration(small_urban_50, 2.0, population=50.0)
    assert high["calibrated_multiplier"] > low["calibrated_multiplier"]


def test_rate_calibration_levy_revenue_positive(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 1.0)
    assert result["levy_revenue"] > 0.0


def test_rate_calibration_guf_at_k_positive(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 1.0)
    assert result["guf_at_calibrated_k"] > 0.0


def test_rate_calibration_achieved_ratio_finite(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 1.0)
    assert math.isfinite(result["achieved_ratio"])
    assert result["achieved_ratio"] > 0.0


def test_rate_calibration_target_stored(small_urban_50):
    result = guf_rate_calibration(small_urban_50, 1.5)
    assert result["target_guf_levy_ratio"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# guf_lvi_weight_sensitivity
# ---------------------------------------------------------------------------

@pytest.fixture
def lvi_parcels():
    # Parcels with LVI sub-index fields for recomputation
    return [
        {
            "area_slu": 3.5, "location_value": 0.72,
            "use_category": "residential_primary",
            "centrality": 0.80, "transit": 0.70, "services": 0.65, "natural_amenity": 0.40,
        },
        {
            "area_slu": 4.0, "location_value": 0.85,
            "use_category": "commercial_retail",
            "centrality": 0.90, "transit": 0.80, "services": 0.75, "natural_amenity": 0.30,
            "residential": False,
        },
    ]


def test_lvi_sensitivity_returns_expected_keys(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    for key in ("epsilon", "parcel_count", "variants", "sensitivity_range", "relative_sensitivity"):
        assert key in result


def test_lvi_sensitivity_default_five_variants(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    assert len(result["variants"]) == 5


def test_lvi_sensitivity_custom_variants(lvi_parcels):
    custom = [
        {"centrality": 0.40, "transit": 0.30, "services": 0.20, "natural_amenity": 0.10},
        {"centrality": 0.20, "transit": 0.20, "services": 0.30, "natural_amenity": 0.30},
    ]
    result = guf_lvi_weight_sensitivity(lvi_parcels, weight_variants=custom)
    assert len(result["variants"]) == 2


def test_lvi_sensitivity_all_aggregates_finite(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    for v in result["variants"]:
        assert math.isfinite(v["guf_aggregate"])
        assert v["guf_aggregate"] > 0.0


def test_lvi_sensitivity_range_ordered(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    lo, hi = result["sensitivity_range"]
    assert lo <= hi


def test_lvi_sensitivity_range_matches_variants(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    aggregates = [v["guf_aggregate"] for v in result["variants"]]
    lo, hi = result["sensitivity_range"]
    assert lo == pytest.approx(min(aggregates))
    assert hi == pytest.approx(max(aggregates))


def test_lvi_sensitivity_relative_sensitivity_nonnegative(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    assert result["relative_sensitivity"] >= 0.0


def test_lvi_sensitivity_parcel_count(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    assert result["parcel_count"] == len(lvi_parcels)


def test_lvi_sensitivity_precomputed_location_value_unchanged():
    # Parcels without sub-indices: location_value used as-is for all variants
    parcels = [
        {"area_slu": 3.5, "location_value": 0.72, "use_category": "residential_primary"},
        {"area_slu": 3.5, "location_value": 0.50, "use_category": "residential_primary"},
    ]
    result = guf_lvi_weight_sensitivity(parcels)
    # Without sub-indices, all variants should produce identical results
    aggs = [v["guf_aggregate"] for v in result["variants"]]
    assert max(aggs) == pytest.approx(min(aggs))


def test_lvi_sensitivity_variant_keys(lvi_parcels):
    result = guf_lvi_weight_sensitivity(lvi_parcels)
    v = result["variants"][0]
    for key in ("weights", "guf_aggregate", "guf_net_inflow", "guf_by_parcel_mean",
                "guf_by_parcel_std", "psi"):
        assert key in v
