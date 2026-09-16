"""
Tests for `scenarios/stationarity.py` — both sides of standing still, under the
doctrine that minted TEH is the wage.
"""
from __future__ import annotations

import math

import pytest

import hours_eoh.scenarios.stationarity as mod
from hours_eoh.land.collective import make_rural_collective, make_urban_collective
from hours_eoh.scenarios.stationarity import (
    d3_consumption,
    drawdown,
    stationarity_at,
    stationarity_report,
    stationary_bands,
)

ARC = (0.0, 0.40, 0.90, 0.99)
URBAN = make_urban_collective(10_000)
RURAL = make_rural_collective(1_000)


class TestItChangesNothingAndSaysWhatItIs:

    def test_reporting_only_and_the_doctrine_are_declared(self):
        doc = mod.__doc__ or ""
        assert "REPORTING ONLY" in doc
        assert "MINTED TEH IS THE WAGE" in doc
        assert "WHAT THIS DOES NOT DO" in doc

    @pytest.mark.parametrize("eps", ARC)
    def test_every_value_is_finite_across_the_arc(self, eps):
        r = stationarity_at(eps, guf_parcels=URBAN)
        for side in ("labour", "teh"):
            for k, v in r[side].items():
                if isinstance(v, float):
                    assert math.isfinite(v), (side, k, v)

    def test_bad_inputs_are_refused(self):
        with pytest.raises(ValueError):
            stationarity_at(1.2)
        with pytest.raises(ValueError):
            stationarity_at(0.4, standard="collapsed")
        with pytest.raises(ValueError):
            stationarity_at(0.4, guarantee="v3")
        with pytest.raises(ValueError):
            stationarity_at(0.4, guf_cap="half")
        with pytest.raises(ValueError):
            stationarity_at(0.4, need_fraction=1.5)


class TestTheLabourSideReadsThePipelineSplit:

    @pytest.mark.parametrize("eps", ARC)
    def test_human_hours_are_the_pipelines(self, eps):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.eoh_generation import resolve_capital_stock
        r = stationarity_at(eps, standard="sufficiency")
        p = eoh_to_teh_pipeline(epsilon=eps, population=1e6,
                                capital_stock=resolve_capital_stock(None, eps),
                                personal_standard="sufficiency")
        assert r["labour"]["human_hours_per_capita"] == pytest.approx(p["human_eoh"] / 1e6, rel=1e-12)

    @pytest.mark.parametrize("eps", ARC)
    def test_it_agrees_with_arc_stability_now_both_use_the_adopted_split(self, eps):
        """Until 2026-09-15 arc_stability read a uniform 1 − ε and understated
        human hours 21 against 458 per capita at 0.99. The agreement is checked
        at the top, where the two splits differ most, not only near 0."""
        r = stationarity_at(eps, standard="sufficiency")["labour"]
        assert r["arc_stability_human_per_capita"] == pytest.approx(
            r["human_hours_per_capita"], rel=1e-9)

    def test_the_default_is_the_shipped_base_and_withholds_the_comparison(self):
        """Author decision 2026-09-15: keep the shipped base of 1,000 h."""
        from hours_eoh.data import PERSONAL_EOH_BASE
        r = stationarity_at(0.40)
        assert r["personal_base"] == PERSONAL_EOH_BASE
        assert r["teh"]["guarantee_base"] == PERSONAL_EOH_BASE
        assert r["labour"]["arc_stability_stationary"] is None
        assert (r["labour"]["human_hours_per_capita"]
                < stationarity_at(0.40, standard="sufficiency")["labour"]["human_hours_per_capita"])

    def test_a_custom_base_is_wired_and_withholds_the_comparison(self):
        at_std = stationarity_at(0.40, standard="sufficiency")
        higher = stationarity_at(0.40, standard="sufficiency", personal_base=2000.0)
        same = stationarity_at(0.40, standard="sufficiency", personal_base=1500.0)
        assert higher["labour"]["human_hours_per_capita"] > at_std["labour"]["human_hours_per_capita"]
        assert higher["teh"]["guarantee_owed"] > at_std["teh"]["guarantee_owed"]
        assert higher["labour"]["arc_stability_stationary"] is None
        assert same["labour"]["arc_stability_human_per_capita"] == pytest.approx(
            at_std["labour"]["arc_stability_human_per_capita"], rel=1e-12)
        with pytest.raises(ValueError):
            stationarity_at(0.40, personal_base=0.0)

    def test_the_labour_side_can_fail_and_can_hold(self):
        assert stationarity_at(0.0, standard="sufficiency")["labour"]["stationary"] is False
        assert stationarity_at(0.0, standard="survival")["labour"]["stationary"] is True
        short = stationarity_at(0.0, standard="sufficiency")["labour"]
        assert short["shortfall_per_capita"] == pytest.approx(
            short["human_hours_per_capita"] - short["supply_per_capita"], rel=1e-12)


class TestTheTrustOwesOnlyTheGuarantee:

    @pytest.mark.parametrize("eps", ARC)
    def test_owed_is_the_guarantee_and_the_booking_is_reported_separately(self, eps):
        from hours_eoh.core.fiscal import sufficiency_guarantee, aggregate_care_stipend_from_demographics
        # `guarantee="shipped"` is explicit since V1 became the default here
        # (2026-09-16): this test is the SHIPPED identity, against core.
        r = stationarity_at(eps, standard="sufficiency", guarantee="shipped")["teh"]
        g = sufficiency_guarantee(1e6, eps, personal_eoh_base=1500.0)
        assert r["guarantee_owed"] == pytest.approx(g["total_cost_teh"], rel=1e-12)
        assert r["paid_by_mint"] >= aggregate_care_stipend_from_demographics(1e6, eps)
        assert r["stationary"] == (r["inflow"] >= r["guarantee_owed"])

    def test_v1_and_v2_scale_with_registration(self):
        eps = 0.40
        v1 = stationarity_at(eps, guarantee="v1", need_fraction=0.05)["teh"]
        v2 = stationarity_at(eps, guarantee="v2")["teh"]
        assert v1["guarantee_owed"] == pytest.approx(0.05 * v2["guarantee_owed"], rel=1e-12)

    def test_the_teh_side_can_fail_and_can_hold(self):
        """Both directions, so the verdict is not a threshold that cannot fire."""
        assert stationarity_at(0.99, guarantee="v2")["teh"]["stationary"] is False
        assert stationarity_at(0.0, guarantee="v1", need_fraction=0.05,
                               guf_parcels=URBAN, guf_cap="payable")["teh"]["stationary"] is True

    def test_the_inheritance_changes_how_long_not_whether(self):
        a = stationarity_at(0.99, guarantee="v2")["teh"]
        b = stationarity_at(0.99, guarantee="v2", trust_start=1.0e9)["teh"]
        assert a["stationary"] == b["stationary"] is False
        assert a["years_covered"] == 0.0
        assert b["years_covered"] == pytest.approx(1.0e9 / b["shortfall"], rel=1e-12)


class TestTheLandFeeFrameAndCap:

    def test_no_parcels_means_no_fee_and_says_so(self):
        assert stationarity_at(0.0)["teh"]["guf"] == 0.0

    def test_the_fee_scales_with_the_declared_parcel_count(self):
        a = stationarity_at(0.40, guf_parcels=RURAL, guf_parcel_count=1.0e5)["teh"]["guf"]
        b = stationarity_at(0.40, guf_parcels=RURAL, guf_parcel_count=2.0e5)["teh"]["guf"]
        assert b == pytest.approx(2.0 * a, rel=1e-12)

    def test_a_share_cap_bites_and_payable_is_bounded_by_what_holders_have(self):
        r = stationarity_at(0.0, guf_parcels=URBAN, guf_cap=0.01)["teh"]
        assert r["guf"] == pytest.approx(0.01 * r["mint"], rel=1e-12)
        assert r["guf"] < r["guf_uncapped"]
        p = stationarity_at(0.0, guf_parcels=URBAN, guf_cap="payable")["teh"]
        assert p["guf"] <= p["mint"] - p["levy"] - p["d3_consumption"] + 1e-6
        assert p["guf"] < p["guf_uncapped"]


class TestD3IsTheSimulationsQuantity:

    @pytest.mark.parametrize("eps", ARC)
    def test_d3_consumption_matches_simulate_period(self, eps):
        from hours_eoh.core.simulation import make_economy_state, simulate_period
        from hours_eoh.data import CAPITAL_FAILURE_RATE, CAPITAL_WRITEDOWN_MONITORING_SLOPE
        new_state, r = simulate_period(make_economy_state(epsilon=eps, population=1e6),
                                       use_d3=True, use_cpi_destruction=False,
                                       use_estate_dissolution=False)
        writedown = (new_state["capital_stock_teh"] * CAPITAL_FAILURE_RATE
                     * (1.0 - CAPITAL_WRITEDOWN_MONITORING_SLOPE * eps))
        gross = r["eoh_by_domain"]["personal"]
        mine = d3_consumption(gross, r["personal_eoh_on_ledger"] / gross,
                              r["human_eoh_by_domain"]["personal"])
        assert mine == pytest.approx(r["teh_destroyed"] - writedown, rel=1e-9)


class TestWhatTheLevyHasToBeAndWhereTheArcIsExpensive:
    """The author's question, 2026-09-16: is standing still at every ε a design
    success or an oversized levy, and is there a threshold below which it fails
    that reads as the friction of first organising resources?"""

    def _teh(self, eps, **kw):
        return stationarity_at(eps, need_fraction=0.05, **kw)["teh"]

    def test_v1_is_the_reporting_default(self):
        assert self._teh(0.40)["guarantee_design"] == "v1"

    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.99))
    def test_the_required_levy_is_the_closed_form_and_the_verdict_agrees(self, eps):
        """r*(ε) = max(0, (owed − GUF) / mint), and the verdict turns there.
        The fee is uncapped here, so it does not move with the levy and the
        form is exact rather than a fixed point."""
        r = self._teh(eps, guf_parcels=URBAN)
        r_star = max(0.0, (r["guarantee_owed"] - r["guf"]) / r["mint"])
        assert self._teh(eps, guf_parcels=URBAN,
                         levy_rate=r_star + 1e-6)["stationary"] is True
        if r_star > 1e-3:
            assert self._teh(eps, guf_parcels=URBAN,
                             levy_rate=r_star - 1e-3)["stationary"] is False

    def test_the_bottom_of_the_arc_costs_more_than_the_middle_but_the_top_binds(self):
        """THE FRICTION, MEASURED — and its mechanism DECOMPOSED rather than
        asserted (corrected 2026-09-16; the first version said "registration is
        near zero so the mint is small", which cannot be the cause because
        under V1 registration scales the guarantee AND the mint).

            r*_nofee = r_personal × need × per_person ÷ mint_per_capita

        ε=0 → 0.19: registration ×3.69, guarantee per person ×0.87, mint per
        capita ×4.23 — the mint OUTRUNS registration, so the ratio falls.
        0.19 → 0.99: registration ×23.8 against mint per capita ×4.63 while the
        guarantee per person only halves — registration SATURATES (0.87 of
        people on ledger) and the mint plateaus, so the ratio rises. The bump
        is real and it is not what binds: the ε=0.99 corner needs 2.4× the
        bottom, which is what the shipped 4.5% is sized to."""
        def r_nofee(e):
            r = self._teh(e)
            return r["guarantee_owed"] / r["mint"]
        bottom, middle, top = r_nofee(0.0), r_nofee(0.19), r_nofee(0.99)
        assert bottom > middle, "the bottom is dearer than the cheapest point"
        assert top > bottom, "and the top is dearer still — the corner binds"
        assert bottom / middle == pytest.approx(1.327, rel=0.02)
        assert top / bottom == pytest.approx(1.806, rel=0.02)

    def test_the_uncapped_fee_exceeds_the_whole_mint_at_subsistence(self):
        """Why "the fee covers the bottom" is a SYMPTOM. record/guf.md already
        records the fee's level as structurally mis-set; this is that defect
        seen from the fiscal side, and the payable cap is the honest figure."""
        r = self._teh(0.0, guf_parcels=URBAN)
        assert r["guf_uncapped"] / r["mint"] > 1.0
        capped = self._teh(0.0, guf_parcels=URBAN, guf_cap="payable")
        assert capped["guf"] / capped["mint"] < 0.5


class TestBandsAndDrawdown:

    def test_bands_report_all_three_and_the_sides_end_differently(self):
        """The TEH side loses its inflow near the top while labour holds there —
        an ordering the scan can get wrong, unlike `both ⊆ labour`."""
        # Bound to the sufficiency standard and the 1.25% levy it was written
        # at: at the 4.5% default the TEH side also reaches 0.99 (next test).
        b = stationary_bands(step=0.11, standard="sufficiency", guarantee="v1",
                             need_fraction=0.05, guf_parcels=URBAN, levy_rate=0.0125)
        assert set(b) >= {"labour", "teh", "both"}
        assert b["teh"]["upper"] < b["labour"]["upper"]

    def test_the_adopted_levy_and_base_reach_the_end_of_the_arc_under_v1(self):
        """THE DECISION'S PIN (2026-09-15): levy 4.5%, base 1,000 h, V1 at 5%
        need, urban fee, no inheritance — both sides stand still on [0, 0.99].
        4.4% stops the TEH side short of 0.99, so this can fail. The shipped
        guarantee design does not stand still at any ε under the same inputs."""
        adopted = stationary_bands(guarantee="v1", need_fraction=0.05, guf_parcels=URBAN)
        assert (adopted["both"]["lower"], adopted["both"]["upper"]) == (0.0, 0.99)
        short = stationary_bands(guarantee="v1", need_fraction=0.05, guf_parcels=URBAN,
                                 levy_rate=0.044)
        assert short["teh"]["upper"] < 0.99
        assert stationary_bands(guf_parcels=URBAN, guarantee="shipped")["teh"]["upper"] is None

    def test_drawdown_fails_where_the_teh_side_is_short_and_holds_where_it_is_not(self):
        # Inside the band V1 at 5% need stands still on with the land fee — a
        # point where something is owed, so holding is not by construction.
        held = drawdown(50, 0.40, 0.40, guarantee="v1", need_fraction=0.05, guf_parcels=URBAN)
        assert held["fails_in_year"] is None and held["trust_end"] > 0.0
        fails = drawdown(50, 0.99, 0.99, guarantee="v2")
        assert fails["fails_in_year"] == 0 and fails["trust_end"] < 0.0

    def test_drawdown_refuses_a_zero_length_arc(self):
        with pytest.raises(ValueError):
            drawdown(0)

    def test_the_report_states_the_doctrine_in_its_verdict(self):
        rep = stationarity_report(0.40)
        assert rep["reporting_only"] is True
        assert "minted TEH is the wage" in rep["verdict"]
