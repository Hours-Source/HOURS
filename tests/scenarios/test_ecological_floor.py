"""
Tests for the ecological domain-balance inversion and the currency-free floor.

The defect under test is the one `data.py` calls THE DOMAIN-BALANCE DEFECT:
`ECOLOGICAL_BASE_RATE` is a RELATIVE anchor summed with absolute counts and then
divided into ε. These tests do not assert that the anchor is right — nothing in
this repo measures stewardship hours. They assert that the machinery which would
SETTLE it behaves correctly, and they pin the size of the gap so it cannot drift
unnoticed the way the domain-share table did.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_generation import ecological_statutory_floor
from hours_eoh.scenarios.ecological_floor import (
    DEFAULT_TARGET_SHARES,
    domain_balance_report,
    floor_from_census,
    implied_stewardship_intensity,
    required_stewardship_intensity,
)

KEY_EPS = [0.0, 0.40, 0.99]


class TestEcologicalStatutoryFloor:
    def test_floor_is_the_sum_of_area_times_hours(self):
        census = [
            {"biome": "cropland", "area_hectares": 1000.0, "hours_per_hectare_year": 12.0},
            {"biome": "forest", "area_hectares": 500.0, "hours_per_hectare_year": 1.5},
        ]
        out = ecological_statutory_floor(census)
        assert out["floor_hours"] == pytest.approx(1000.0 * 12.0 + 500.0 * 1.5)
        assert out["coverage"] == pytest.approx(1.0)
        assert out["mean_hours_per_hectare"] == pytest.approx(12750.0 / 1500.0)

    def test_unpriced_is_EXCLUDED_not_costed_at_zero(self):
        """The load-bearing behaviour, shared with the personal floor.

        A parcel nobody has costed is owed and unquantified. Counting it at zero
        would silently assert that wilderness needs no stewardship, and the floor
        would then be a claim about the world rather than about what is measured.
        """
        census = [
            {"biome": "cropland", "area_hectares": 100.0, "hours_per_hectare_year": 10.0},
            {"biome": "wilderness", "area_hectares": 900.0, "hours_per_hectare_year": None},
        ]
        out = ecological_statutory_floor(census)

        assert out["floor_hours"] == pytest.approx(1000.0)
        # Coverage is by AREA, and it is the number a caller must read first.
        assert out["coverage"] == pytest.approx(0.10)
        assert [u["biome"] for u in out["unpriced"]] == ["wilderness"]
        assert out["unpriced"][0]["area_hectares"] == pytest.approx(900.0)
        # The mean is over PRICED area only — not diluted by the 900 unpriced ha.
        assert out["mean_hours_per_hectare"] == pytest.approx(10.0)

    def test_empty_census_is_zero_coverage_not_a_crash(self):
        out = ecological_statutory_floor([])
        assert out["floor_hours"] == 0.0
        assert out["coverage"] == 0.0
        assert out["mean_hours_per_hectare"] == 0.0

    @pytest.mark.parametrize("bad", [
        {"area_hectares": -1.0, "hours_per_hectare_year": 1.0},
        {"area_hectares": 1.0, "hours_per_hectare_year": -1.0},
        {"hours_per_hectare_year": 1.0},
    ])
    def test_malformed_parcels_raise(self, bad):
        with pytest.raises(ValueError):
            ecological_statutory_floor([bad])


class TestInversion:
    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_arc_coherence(self, eps):
        cur = implied_stewardship_intensity(epsilon=eps)
        assert cur["hours_per_hectare_year"] > 0.0
        assert 0.0 < cur["ecological_share"] < 1.0
        req = required_stewardship_intensity(0.05, epsilon=eps)
        assert req["required_hours_per_hectare_year"] > cur["hours_per_hectare_year"]

    @pytest.mark.parametrize("eps", KEY_EPS)
    def test_inversion_round_trips(self, eps):
        """The required obligation really does produce the requested share.

        share = E / (R + E) with R held fixed, so substituting the answer back in
        must reproduce the target. This is the check that the algebra is right,
        independent of any calibration.
        """
        for share in DEFAULT_TARGET_SHARES:
            req = required_stewardship_intensity(share, epsilon=eps)
            cur = implied_stewardship_intensity(epsilon=eps)
            rest = cur["total_eoh"] - cur["ecological_eoh"]
            new_total = rest + req["required_ecological_eoh"]
            assert req["required_ecological_eoh"] / new_total == pytest.approx(share)

    def test_required_intensity_rises_with_target_share(self):
        reqs = [required_stewardship_intensity(s)["required_hours_per_hectare_year"]
                for s in DEFAULT_TARGET_SHARES]
        assert all(b > a for a, b in zip(reqs, reqs[1:]))

    @pytest.mark.parametrize("bad", [-0.1, 1.0, 1.5])
    def test_share_outside_the_unit_interval_raises(self, bad):
        with pytest.raises(ValueError):
            required_stewardship_intensity(bad)

    def test_intensity_scales_inversely_with_land_per_capita(self):
        """Twice the land per person, half the intensity for the same obligation."""
        a = implied_stewardship_intensity(hectares_per_capita=1.0)
        b = implied_stewardship_intensity(hectares_per_capita=2.0)
        assert b["hours_per_hectare_year"] == pytest.approx(
            a["hours_per_hectare_year"] / 2.0
        )


class TestTheGapItself:
    def test_the_shortfall_is_two_orders_of_magnitude(self):
        """Pins the FINDING, which is the point of the module.

        `data.py` says the ecological base is "either low by 2–3 orders, or
        CDR_LABOR_HOURS_PER_TONNE is, or both; nothing in current data settles
        it." This test converts that from an assertion into a measured bound: at
        the shipped anchor and a planetary-average 1.65 ha/person, reaching a 5%
        share of total EOH requires ~132× the implied stewardship intensity.

        Asserted as a BAND, not a point — the factor moves with every constant
        that changes total EOH, and the claim being made is the order of
        magnitude, not the digits. If this fails, the domain-balance narrative in
        docs/parameter_provenance.md needs re-reading, which is the intent.
        """
        rep = domain_balance_report()
        five = next(r for r in rep["requirements"] if r["target_share"] == 0.05)
        assert 50.0 < five["shortfall_factor"] < 500.0

    def test_the_anchor_implies_under_an_hour_per_hectare_per_year(self):
        """The reading that makes the defect legible without any arithmetic.

        Under one labour-hour per hectare per year, across every biome and
        condition class including cropland. Stated this way the anchor does not
        need refuting — it plainly is not an absolute stewardship figure, which
        is exactly what its own provenance tag says.
        """
        cur = implied_stewardship_intensity()
        assert 0.0 < cur["hours_per_hectare_year"] < 1.0

    def test_ecological_is_under_a_tenth_of_a_percent_of_total_eoh(self):
        cur = implied_stewardship_intensity()
        assert cur["ecological_share"] < 0.001


class TestCensusIntake:
    def test_a_census_can_exceed_the_anchor_and_the_ratio_says_by_how_much(self):
        """The falsification path, exercised end to end.

        A census at intensities that would not be surprising for managed land
        should read far above the anchor — and `ratio_to_anchor` is the number a
        future measurement would report.
        """
        census = [
            {"biome": "cropland", "area_hectares": 5.0e5, "hours_per_hectare_year": 12.0},
            {"biome": "managed_forest", "area_hectares": 4.0e5, "hours_per_hectare_year": 1.5},
            {"biome": "wilderness", "area_hectares": 7.5e5, "hours_per_hectare_year": None},
        ]
        out = floor_from_census(census)

        assert out["ratio_to_anchor"] > 10.0
        assert out["coverage"] < 1.0, "the wilderness parcel must not be priced"
        assert out["floor_h_per_capita"] > out["anchor_h_per_capita"]

    def test_report_is_json_safe(self):
        """The CLI serialises this; a stray non-primitive would only fail there."""
        import json
        rep = domain_balance_report()
        json.dumps(rep)
