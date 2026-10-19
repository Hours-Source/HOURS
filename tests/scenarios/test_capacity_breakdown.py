"""
Tests for scenarios/capacity_breakdown.py — where the work goes, as hours of
capacity. Shapes and identities, never levels: the personal split is a
placeholder and every level moves with it.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.eoh_fulfillment import personal_human_fraction
from hours_eoh.scenarios.arc_stability import stability_at
from hours_eoh.scenarios.capacity_breakdown import (
    SHARE_SOURCES, breakdown_at, capacity_report,
)

ARC = [0.0, 0.40, 0.90, 0.99]


class TestItIsTheCompassSplitByComponent:

    @pytest.mark.parametrize("eps", ARC)
    @pytest.mark.parametrize("standard", ["survival", "sufficiency"])
    def test_desk_rows_close_to_the_compass_and_the_personal_split(self, eps, standard):
        """The rows partition obligation + delivery exactly, and the personal
        rows partition `personal_human_fraction · personal` — so the per-row
        formula cannot drift from the pipeline's split."""
        b = breakdown_at(eps, standard=standard, capital_stock_teh=3.0e9)
        a = stability_at(eps, standard=standard, capital_stock_teh=3.0e9)
        assert b["total_hours_per_capita_yr"] == pytest.approx(
            a["obligation_per_capita"] + a["delivery_per_capita"], rel=1e-12)
        assert b["capacity_per_capita_yr"] == a["supply_per_capita"]
        personal = sum(r["hours_per_capita_yr"] for r in b["rows"] if r["account"] == "personal")
        gross = a["obligation_per_capita"] - next(
            r["hours_per_capita_yr"] for r in b["rows"]
            if r["component"] == "knowledge (civilisational)")
        assert personal == pytest.approx(gross, rel=1e-12)
        assert b["personal_human_fraction"] == personal_human_fraction(eps)


class TestTheStandardMovesOnlyThePersonalRows:

    @pytest.mark.parametrize("eps", ARC)
    @pytest.mark.parametrize("shares", SHARE_SOURCES)
    def test_sufficiency_adds_personal_work_and_nothing_collective(self, eps, shares):
        lo = breakdown_at(eps, standard="survival", shares=shares)
        hi = breakdown_at(eps, standard="sufficiency", shares=shares)
        for a, b in zip(lo["rows"], hi["rows"]):
            if a["account"] == "personal":
                assert b["hours_per_capita_yr"] > a["hours_per_capita_yr"]
            else:
                assert b["hours_per_capita_yr"] == a["hours_per_capita_yr"]


class TestEachInputMovesItsRows:
    """The point of the report is that moving an input moves the breakdown —
    and moves only what it should."""

    def test_capital_moves_upkeep_capacity_moves_shares_not_hours(self):
        base = breakdown_at(0.40, capital_stock_teh=2.0e9)
        more = breakdown_at(0.40, capital_stock_teh=4.0e9)
        up = {r["component"]: r["hours_per_capita_yr"] for r in base["rows"]}
        up2 = {r["component"]: r["hours_per_capita_yr"] for r in more["rows"]}
        assert up2["infrastructure upkeep"] > up["infrastructure upkeep"]
        wider = breakdown_at(0.40, capital_stock_teh=2.0e9, adult_share=0.75)
        assert wider["total_hours_per_capita_yr"] == base["total_hours_per_capita_yr"]
        assert wider["total_share_of_capacity"] < base["total_share_of_capacity"]
        older = breakdown_at(0.40, capital_stock_teh=2.0e9, capital_age_ratio=0.9)
        assert older["total_hours_per_capita_yr"] > base["total_hours_per_capita_yr"]

    def test_the_split_moves_the_personal_rows_and_unsupplied_is_declared(self):
        d = capacity_report(0.40)["runs"]
        desk, obs = d[("sufficiency", "desk")], d[("sufficiency", "observed")]
        care = [r for r in (desk, obs) for r in r["rows"] if r["component"] == "care"]
        assert care[0]["hours_per_capita_yr"] > care[1]["hours_per_capita_yr"]
        for key in ("capital_source", "capital_age_source", "adult_share_source"):
            assert "NOT SUPPLIED" in desk[key]
