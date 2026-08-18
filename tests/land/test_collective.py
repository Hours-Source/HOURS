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


# ===========================================================================
# attach_ecosystem_services — the E term reaches an inventory (2026-08-17).
#
# E(p,ε) was ZERO in every scenario the package ships: neither archetype set
# `ecosystem_services`, and no calibration or stress path supplied it. See
# notes/guf-restoration-derivation.md.
# ===========================================================================

from hours_eoh.data import (
    GUF_SERVICE_PROFILE_DECLARED,
    GUF_SERVICE_RETENTION_BY_USE,
    SLU_HECTARES,
)
from hours_eoh.land.collective import attach_ecosystem_services
from hours_eoh.land.guf import USE_CATEGORIES, ecosystem_displacement_surcharge

ARC = [0.0, 0.40, 0.99]


class TestArchetypesShipWithoutServices:
    """E stays 0 by default. Turning it on is a calibration change, not plumbing."""

    def test_neither_factory_sets_ecosystem_services(self):
        for factory in (make_urban_collective, make_rural_collective):
            parcels = factory(50)
            assert not any(p.get("ecosystem_services") for p in parcels)

    def test_attaching_does_not_mutate_the_input(self):
        base = make_urban_collective(20)
        enriched = attach_ecosystem_services(base)
        assert all("ecosystem_services" not in p for p in base)
        assert all(p["ecosystem_services"] for p in enriched)


class TestAreaConversionAndScaling:

    def test_volume_uses_the_slu_to_hectare_conversion(self):
        parcel = [{"area_slu": 100.0, "location_value": 0.5,
                   "use_category": "residential_primary"}]
        out = attach_ecosystem_services(parcel, retained=0.0)
        carbon = next(s for s in out[0]["ecosystem_services"] if s["service"] == "carbon")
        expected = 100.0 * SLU_HECTARES * GUF_SERVICE_PROFILE_DECLARED["carbon"]
        assert carbon["volume"] == pytest.approx(expected, rel=1e-12)

    def test_e_scales_with_parcel_area(self):
        small = attach_ecosystem_services(
            [{"area_slu": 1.0, "location_value": 0.5, "use_category": "residential_primary"}],
            retained=0.0)
        big = attach_ecosystem_services(
            [{"area_slu": 10.0, "location_value": 0.5, "use_category": "residential_primary"}],
            retained=0.0)
        for a, b in zip(small[0]["ecosystem_services"], big[0]["ecosystem_services"]):
            assert b["volume"] == pytest.approx(10.0 * a["volume"], rel=1e-12)


class TestRetentionFollowsUseCategory:
    """
    ρ = 1 gives E = 0 CORRECTLY: land that keeps delivering its services owes no
    displacement surcharge. That is the reframing sitting in the equation — E is
    structurally a disturbance measure.
    """

    def test_default_takes_rho_from_the_parcel_use_category(self):
        parcels = [
            {"area_slu": 1.0, "location_value": 0.5, "use_category": "conservation"},
            {"area_slu": 1.0, "location_value": 0.5, "use_category": "industrial_heavy"},
        ]
        out = attach_ecosystem_services(parcels)  # retained=None → by use
        assert out[0]["ecosystem_services"][0]["retained"] == \
            GUF_SERVICE_RETENTION_BY_USE["conservation"]
        assert out[1]["ecosystem_services"][0]["retained"] == \
            GUF_SERVICE_RETENTION_BY_USE["industrial_heavy"]

    def test_conservation_owes_less_than_industry_on_identical_land(self):
        """The ORDERING is the claim; the magnitudes are placeholders."""
        def e_for(use):
            p = [{"area_slu": 5.0, "location_value": 0.5, "use_category": use}]
            base = compute_collective_guf(p, 0.40)["guf_gross_revenue"]
            enr = compute_collective_guf(attach_ecosystem_services(p), 0.40)["guf_gross_revenue"]
            return enr - base
        assert e_for("conservation") < e_for("agricultural_active") < e_for("industrial_heavy")

    def test_retention_table_covers_every_use_category(self):
        assert set(GUF_SERVICE_RETENTION_BY_USE) == set(USE_CATEGORIES)

    def test_retention_values_are_fractions_and_ordered_as_claimed(self):
        for use, rho in GUF_SERVICE_RETENTION_BY_USE.items():
            assert 0.0 <= rho <= 1.0, use
        assert GUF_SERVICE_RETENTION_BY_USE["conservation"] > \
               GUF_SERVICE_RETENTION_BY_USE["agricultural_active"] > \
               GUF_SERVICE_RETENTION_BY_USE["commercial_retail"] > \
               GUF_SERVICE_RETENTION_BY_USE["industrial_heavy"]

    def test_explicit_scalar_overrides_the_table(self):
        parcels = [{"area_slu": 1.0, "location_value": 0.5, "use_category": "conservation"}]
        out = attach_ecosystem_services(parcels, retained=0.0)
        assert out[0]["ecosystem_services"][0]["retained"] == 0.0

    def test_rho_zero_is_the_upper_bound_on_e(self):
        base = make_rural_collective(100)
        b = compute_collective_guf(base, 0.40)["guf_gross_revenue"]
        upper = compute_collective_guf(
            attach_ecosystem_services(base, retained=0.0), 0.40)["guf_gross_revenue"]
        by_use = compute_collective_guf(
            attach_ecosystem_services(base), 0.40)["guf_gross_revenue"]
        assert upper - b > by_use - b > 0.0


class TestArcCoherence:

    def test_raw_surcharge_falls_with_automation(self):
        """
        E itself is κ-driven and monotonically decreasing. Tested on the RAW
        surcharge, not on the difference in total GUF — see the test below for
        why that distinction matters.
        """
        enriched = attach_ecosystem_services(make_rural_collective(50))
        services = [s for p in enriched for s in p["ecosystem_services"]]
        prev = None
        for eps in ARC:
            e = ecosystem_displacement_surcharge(services, eps)["surcharge_total"]
            assert math.isfinite(e) and e > 0.0
            if prev is not None:
                assert e < prev, f"κ must fall with ε (ε={eps})"
            prev = e

    def test_the_fee_contribution_is_NOT_monotonic_because_of_psi(self):
        """
        A trap worth pinning. E falls monotonically in ε, but what a parcel
        actually pays is Ψ(ε)·E, and Ψ is a bell curve (0.02 → 1.00 → 0.035).
        So the ecological CONTRIBUTION to GUF rises to mid-arc and then falls.
        An arc test asserting monotonicity on the fee would fail for a correct
        implementation — as this one first did.
        """
        base = make_rural_collective(50)
        enriched = attach_ecosystem_services(base)

        def contribution(eps: float) -> float:
            b = compute_collective_guf(base, eps)["guf_gross_revenue"]
            e = compute_collective_guf(enriched, eps)["guf_gross_revenue"]
            return e - b

        low, mid, high = contribution(0.0), contribution(0.40), contribution(0.99)
        assert mid > low and mid > high
        for v in (low, mid, high):
            assert math.isfinite(v) and v > 0.0
