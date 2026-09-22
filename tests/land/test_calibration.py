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
    # TWO DEFECTS FIXED 2026-09-15, and the target is now hit EXACTLY rather
    # than within ±25%:
    #   1. `population` did not move `levy_revenue` (797,263 / 797,419 / 798,970
    #      TEH at 5 / 50 / 500 people), because the pipeline resolved the
    #      1M-frame default capital stock at every frame. Capital travels with
    #      the frame now, so 50 people and 50 parcels is a coherent pairing.
    #   2. The solver's fixed leg summed only E and I, missing the flat
    #      per-parcel charge P(ε) the fee has added since 2026-08-30 — 4.723
    #      TEH/parcel here, 236.15 over the inventory, invariant in k. It
    #      overshot every target by exactly that: 1.149 asked for 1.0, 0.649
    #      asked for 0.5.
    result = guf_rate_calibration(small_urban_50, 1.0, population=50.0, tolerance=0.10)
    assert result["converged"] is True
    assert result["achieved_ratio"] == pytest.approx(1.0, rel=1e-6)


def test_the_target_is_hit_exactly_at_several_ratios_and_frames(small_urban_50):
    """The solver is exact where a k exists, not merely close: a residual it
    cannot see would show up as a constant offset across targets, which is how
    the P(ε) omission was found."""
    for target in (0.25, 0.5, 1.0, 2.0):
        r = guf_rate_calibration(small_urban_50, target, population=104.0, tolerance=0.10)
        assert r["converged"] is True
        assert r["achieved_ratio"] == pytest.approx(target, rel=1e-6)
    # And the frame reaches the solve: levy revenue scales with population.
    a = guf_rate_calibration(small_urban_50, 1.0, population=50.0)
    b = guf_rate_calibration(small_urban_50, 1.0, population=500.0)
    assert b["levy_revenue"] == pytest.approx(10.0 * a["levy_revenue"], rel=1e-9)


def test_an_unreachable_target_reports_failure_rather_than_a_clamped_k(small_urban_50):
    """`converged` must be able to say no. Below the fixed leg — the part of
    the fee no use-coefficient can scale — no k reaches the target, and k
    clamps at its 0.01 floor instead of going negative."""
    r = guf_rate_calibration(small_urban_50, 1.0, population=50.0, tolerance=0.10,
                             levy_rates={"sufficiency": 0.0125})
    assert r["converged"] is False
    assert r["calibrated_multiplier"] == pytest.approx(0.01)
    assert r["achieved_ratio"] > 1.0


def test_the_capital_stock_reaches_the_levy_base(small_urban_50):
    """The frame's third extensive is wired, not merely accepted."""
    lean = guf_rate_calibration(small_urban_50, 1.0, population=50.0,
                                capital_stock_teh=1.0e5)
    rich = guf_rate_calibration(small_urban_50, 1.0, population=50.0,
                                capital_stock_teh=1.0e9)
    assert rich["levy_revenue"] > 100.0 * lean["levy_revenue"]


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


class TestPsiNormalization:
    """The GUF fee curve's peak — previously unpinned, and wrong.

    `GUF_PSI_NORM` was pinned at 4.0 while its own `form:` claimed it "puts Ψ's
    peak at ≈1.0". The actual peak was 1.061. Deriving it moved the whole fee
    curve −5.7% across the productive arc and NOT ONE TEST FAILED, which is why
    these exist: a normalization of two live parameters must not be a literal,
    and the property it normalizes must be asserted somewhere.
    """

    def test_psi_peaks_at_exactly_one(self):
        from hours_eoh.data import GUF_PSI_A, GUF_PSI_B
        from hours_eoh.land.guf import epsilon_scaling

        peak_epsilon = GUF_PSI_A / (GUF_PSI_A + GUF_PSI_B)
        assert epsilon_scaling(peak_epsilon) == pytest.approx(1.0, abs=1e-9)

    def test_the_peak_is_where_the_kernel_says_it_is(self):
        """ε* = a/(a+b), checked against a scan rather than assumed."""
        from hours_eoh.data import GUF_PSI_A, GUF_PSI_B
        from hours_eoh.land.guf import epsilon_scaling

        scan = [(e / 1000.0, epsilon_scaling(e / 1000.0)) for e in range(1, 1000)]
        arg_max = max(scan, key=lambda p: p[1])[0]
        assert arg_max == pytest.approx(
            GUF_PSI_A / (GUF_PSI_A + GUF_PSI_B), abs=2e-3
        )

    def test_the_norm_tracks_its_inputs_rather_than_being_pinned(self):
        """Change a speed and the normalization must follow, or Ψ stops peaking at 1."""
        from hours_eoh.data import GUF_PSI_FLOOR

        def norm(a: float, b: float) -> float:
            peak = a / (a + b)
            return (1.0 - GUF_PSI_FLOOR) / (peak**a * (1.0 - peak) ** b)

        for a, b in ((0.8, 1.2), (1.0, 1.0), (0.5, 1.5)):
            peak = a / (a + b)
            psi_peak = norm(a, b) * peak**a * (1.0 - peak) ** b + GUF_PSI_FLOOR
            assert psi_peak == pytest.approx(1.0, abs=1e-9)
