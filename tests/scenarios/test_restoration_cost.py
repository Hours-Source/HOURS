"""
Tests for the restoration-cost derivation (Phase 3).

The derivation is physics — ASAE field capacity, no price in the chain. The
service side it is compared against is NOT, and `TestConditionalOnPlaceholderVs`
keeps that distinction visible.
"""

import math

import pytest

from hours_eoh.data import GUF_ECO_KAPPA_CARBON, GUF_SERVICE_PROFILE_DECLARED
from hours_eoh.reference.land_stewardship import ACRE_HECTARES, hours_per_acre
from hours_eoh.reference.restoration import (
    RESTORATION_SEQUENCES,
    UNPRICED_RESTORATION,
    restoration_hours_per_hectare,
)
from hours_eoh.scenarios.restoration_cost import (
    BOUNDING_ASSUMPTION_H_PER_HA,
    implied_kappa,
    legacy_stock,
    restoration_band,
    restoration_report,
)


class TestDerivationIsPhysics:
    """Every operation must resolve through the ASAE table — no free numbers."""

    def test_every_operation_names_a_real_implement(self):
        for name, spec in RESTORATION_SEQUENCES.items():
            for implement, width_ft, passes, phase in spec["operations"]:
                # Raises KeyError on an unknown implement, which is the point:
                # guessing a neighbour's efficiency is how a plausible wrong
                # number gets in.
                r = hours_per_acre(implement, width_ft)
                assert r["hours_per_acre_low"] > 0.0
                assert passes >= 1
                assert phase in ("establishment", "aftercare")

    def test_hours_reproduce_the_governing_equation(self):
        """hours/ha = passes × (1/EFC) × (1/ACRE_HECTARES), summed per phase."""
        r = restoration_hours_per_hectare("grassland_seeding")
        expected_low = 0.0
        for implement, width_ft, passes, phase in \
                RESTORATION_SEQUENCES["grassland_seeding"]["operations"]:
            if phase != "establishment":
                continue
            per_acre = hours_per_acre(implement, width_ft)
            expected_low += passes * per_acre["hours_per_acre_low"] / ACRE_HECTARES
        assert r["establishment_h_per_ha_low"] == pytest.approx(expected_low, rel=1e-12)

    def test_lifetime_is_establishment_plus_aftercare_years(self):
        for name in RESTORATION_SEQUENCES:
            r = restoration_hours_per_hectare(name)
            expected = (
                r["establishment_h_per_ha_low"]
                + r["aftercare_h_per_ha_year_low"] * r["aftercare_years"]
            )
            assert r["lifetime_h_per_ha_low"] == pytest.approx(expected, rel=1e-12)

    def test_band_corners_are_ordered(self):
        for name in RESTORATION_SEQUENCES:
            r = restoration_hours_per_hectare(name)
            assert r["lifetime_h_per_ha_low"] < r["lifetime_h_per_ha_high"]

    def test_wider_equipment_costs_fewer_hours(self):
        """
        The substitution the width parameter encodes: capital for labour. Not
        noise in the estimate — the same substitution ε measures elsewhere.
        """
        narrow = hours_per_acre("grain_drill", 10.0)["hours_per_acre_low"]
        wide = hours_per_acre("grain_drill", 20.0)["hours_per_acre_low"]
        assert wide < narrow

    def test_unknown_sequence_raises(self):
        with pytest.raises(KeyError, match="unknown restoration sequence"):
            restoration_hours_per_hectare("terraforming")


class TestUnpricedIsExcludedNotZeroed:

    def test_three_classes_are_excluded_with_reasons(self):
        assert len(UNPRICED_RESTORATION) == 3
        classes = {u["class"] for u in UNPRICED_RESTORATION}
        assert classes == {"tree_planting", "wetland_hydrology", "monitoring"}
        for u in UNPRICED_RESTORATION:
            assert u["reason"].strip()
            assert u["resolves_by"].strip()

    def test_each_pointer_names_the_FIELD_not_just_a_source(self):
        """
        The repo's own rule: a resolves_by that names a SOURCE without naming
        the FIELD in it that carries the quantity has not been checked. Each
        pointer here names a unit-bearing field.
        """
        expected_fields = {
            "tree_planting":     "SEEDLINGS PER PERSON-DAY",
            "wetland_hydrology": "CUBIC METRES PER MACHINE-HOUR",
            "monitoring":        "plots per person-day",
        }
        by_class = {u["class"]: u["resolves_by"] for u in UNPRICED_RESTORATION}
        for cls, field in expected_fields.items():
            assert field in by_class[cls], cls

    def test_report_states_coverage(self):
        rep = restoration_report()
        assert rep["band"]["priced_count"] == len(RESTORATION_SEQUENCES)
        assert rep["band"]["unpriced_count"] == 3
        assert "EXCLUDED rather than costed at zero" in rep["coverage_note"]


class TestTheCorrection:
    """
    Phase 0's bounding used 100 h/ha as "a plausible restoration figure". The
    derivation says otherwise, and the correction strengthens the conclusion.
    """

    def test_the_guess_was_far_too_high(self):
        s = legacy_stock()
        assert BOUNDING_ASSUMPTION_H_PER_HA == 100.0
        assert s["guess_overstated_by_low"] > 10.0
        assert s["guess_overstated_by_high"] > s["guess_overstated_by_low"]

    def test_derived_cost_is_single_digit_hours_per_hectare(self):
        band = restoration_band()
        assert 0.1 < band["lifetime_low"] < 10.0
        assert 0.1 < band["lifetime_high"] < 10.0

    def test_legacy_stock_is_negligible_per_capita(self):
        """
        The conclusion, pinned. Against a personal obligation of ~1,301
        h/person·yr, the whole restoration backlog is hundredths of an hour.
        """
        s = legacy_stock()
        assert s["h_per_capita_high"] < 0.1
        assert s["h_per_capita_low"] > 0.0

    def test_stock_scales_with_area_and_inversely_with_horizon(self):
        base = legacy_stock(100e6, 50.0)["annual_hours_low"]
        twice_area = legacy_stock(200e6, 50.0)["annual_hours_low"]
        half_horizon = legacy_stock(100e6, 25.0)["annual_hours_low"]
        assert twice_area == pytest.approx(2.0 * base, rel=1e-12)
        assert half_horizon == pytest.approx(2.0 * base, rel=1e-12)


class TestImpliedKappa:

    def test_biological_replacement_is_far_cheaper_than_engineered(self):
        """
        The comparison Phase 3 exists for. GUF_ECO_KAPPA_CARBON is an ENGINEERED
        cost (CDR operator staffing); restoration is a BIOLOGICAL replacement of
        the same service. The gap is the measurement, not a discrepancy.
        Asserted as a SIGN and an order, never a level.
        """
        k = implied_kappa()
        assert k["implied_kappa_high"] < GUF_ECO_KAPPA_CARBON
        assert k["shipped_over_implied_low"] > 5.0

    def test_kappa_scales_inversely_with_horizon(self):
        short = implied_kappa(25.0)["implied_kappa_low"]
        long = implied_kappa(50.0)["implied_kappa_low"]
        assert short == pytest.approx(2.0 * long, rel=1e-12)


class TestConditionalOnPlaceholderVs:
    """
    The restoration side is physics; the service side is not. Any κ computed
    here is a sensitivity with a sound method, never a result.
    """

    def test_kappa_depends_on_the_declared_service_profile(self):
        k = implied_kappa()
        assert k["carbon_volume_per_ha_year"] == GUF_SERVICE_PROFILE_DECLARED["carbon"]

    def test_the_verdict_says_so(self):
        rep = restoration_report()
        assert "CONDITIONAL" in rep["kappa_verdict"]
        assert "placeholder" in rep["kappa_verdict"]


class TestReportChangesNothing:
    """REPORTING ONLY."""

    def test_shipped_kappa_is_untouched(self):
        assert GUF_ECO_KAPPA_CARBON == 0.6

    def test_report_resolves_and_stays_finite(self):
        rep = restoration_report()
        for corner in ("low", "high"):
            assert math.isfinite(rep["stock"][f"h_per_capita_{corner}"])
            assert math.isfinite(rep["kappa"][f"implied_kappa_{corner}"])
