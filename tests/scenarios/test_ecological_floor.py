"""Tests for the ecological domain-balance inversion and the currency-free floor.

The defect under test is what `data.py` calls THE DOMAIN-BALANCE DEFECT:
`ECOLOGICAL_BASE_RATE` is a RELATIVE anchor, summed with absolute counts and then
divided into ε. These tests do not assert that the anchor is right; nothing in this repo
measures stewardship hours. They assert that the machinery which would SETTLE it works,
and they pin the size of the gap so it cannot drift unnoticed.
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
        """An unpriced parcel is EXCLUDED, not costed at zero, as in the personal floor.
        A parcel nobody has costed is owed and unquantified. A zero would assert that
        wilderness needs no stewardship, which is a claim about the world, not about
        what is measured.
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
    def test_the_shortfall_exceeds_four_orders_of_magnitude(self):
        """Pins the FINDING as a measured bound. At the shipped anchor and 1.65
        ha/person, a 5% share of total EOH needs a stewardship intensity many orders
        above the implied one. The test asserts a BAND, because the factor moves with
        every constant in total EOH. The old "low by 2–3 orders" framing it was built to
        quantify has since been reversed
        ([record](record/ecological.md#phase-4f-ecological-level-closed)).
        """
        rep = domain_balance_report()
        five = next(r for r in rep["requirements"] if r["target_share"] == 0.05)
        # PHASE 4b (2026-08-17): 133x -> 61,712x. The gap did not get better
        # when the frame was declared — it got 464x WORSE, because the mismatch
        # had been INFLATING the anchor and thereby masking the very defect this
        # number measures. Still asserted as a BAND and an order of magnitude.
        assert 10_000.0 < five["shortfall_factor"] < 500_000.0

    def test_the_anchor_implies_under_an_hour_per_hectare_per_year(self):
        """The anchor implies under one labour-hour per hectare per year, across every
        biome and condition class, cropland included. So it plainly is not an absolute
        stewardship figure, which is what its own provenance tag says.
        """
        cur = implied_stewardship_intensity()
        assert 0.0 < cur["hours_per_hectare_year"] < 1.0

    def test_ecological_is_under_a_tenth_of_a_percent_of_total_eoh(self):
        cur = implied_stewardship_intensity()
        assert cur["ecological_share"] < 0.001


class TestCensusIntake:
    def test_a_census_can_exceed_the_anchor_and_the_ratio_says_by_how_much(self):
        """The falsification path, end to end. A census at intensities usual for managed
        land reads far above the anchor, and `ratio_to_anchor` is the number a future
        measurement would report.
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


class TestTheVerdictsQuotedFiguresAreStillTrue:
    """The verdict quotes figures from OTHER scenarios, and computes them since
    2026-10-18. These tests pin the sources, so a moved figure fails here. The
    per-hectare 0.21%, not the US-scale 0.56%, belongs beside a per-hectare table
    ([record](record/ecological.md)).
    """

    def test_servicing_flow_figure(self):
        from hours_eoh.scenarios.servicing_census import census
        assert census("core")["hours_per_hectare_year"] == pytest.approx(45.92, abs=0.01)

    def test_restoration_stock_band(self):
        from hours_eoh.scenarios.restoration_cost import (
            DEFAULT_AMORTIZATION_YEARS,
            restoration_band,
        )
        band = restoration_band()
        lo = band["lifetime_low"] / DEFAULT_AMORTIZATION_YEARS
        hi = band["lifetime_high"] / DEFAULT_AMORTIZATION_YEARS
        assert lo == pytest.approx(0.017, abs=0.001)
        assert hi == pytest.approx(0.096, abs=0.001)

    def test_the_per_hectare_ratio_is_the_one_quoted(self):
        from hours_eoh.scenarios.restoration_cost import (
            DEFAULT_AMORTIZATION_YEARS,
            restoration_band,
        )
        from hours_eoh.scenarios.servicing_census import census
        flow = census("core")["hours_per_hectare_year"]
        stock = restoration_band()["lifetime_high"] / DEFAULT_AMORTIZATION_YEARS
        assert stock / flow * 100.0 == pytest.approx(0.21, abs=0.02)

    def test_the_verdict_carries_the_caveat(self):
        from hours_eoh.scenarios.ecological_floor import domain_balance_report
        v = domain_balance_report()["verdict"]
        assert "REFERENCE POINTS, NOT TARGETS" in v
        assert "INVERSION, not a measurement" in v
        assert "464" in v          # the factor moved without new evidence
        assert "0.21%" in v and "0.56%" in v   # both stated, and distinguished

    def test_the_verdict_no_longer_claims_nothing_measures_stewardship(self):
        """`scenarios/land_stewardship` exists; the old verdict said it did not."""
        from hours_eoh.scenarios.ecological_floor import domain_balance_report
        v = domain_balance_report()["verdict"]
        assert "Nothing in this repo measures stewardship hours" not in v
        assert "land_stewardship" in v
