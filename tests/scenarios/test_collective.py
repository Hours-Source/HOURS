"""
Tests for hours_eoh.scenarios.collective — the single assembly point.

The frame is stated ONCE and the three calls cannot disagree. What these pin is
not arithmetic (core and land own that) but the RECONCILIATION: that the
pipeline's ecological obligation is what the fiscal layer sizes against, that
the parcel inventory supplies both the fee and the area, and that a caller
cannot half-state a frame.
"""

import pytest

from hours_eoh.core.simulation import make_economy_state
from hours_eoh.data import SLU_HECTARES
from hours_eoh.land.collective import make_urban_collective, make_rural_collective
from hours_eoh.scenarios.collective import collective_snapshot, land_hectares_of

ARC = (0.0, 0.40, 0.99)


def _state(pop=30_000.0, eps=0.40, **kw):
    return make_economy_state(
        population=pop, epsilon=eps,
        capital_stock_teh=2000.0 * pop,
        trust_balance=35_000.0 * pop,
        **kw,
    )


class TestTheFrameIsStatedOnce:

    def test_the_pipeline_and_the_fisc_see_ONE_ecological_obligation(self):
        """
        THE DEFECT THIS FUNCTION EXISTS TO MAKE IMPOSSIBLE. Run by hand, the
        guide's own worked example had the pipeline resolve the ecological area
        from population while the fiscal layer took the whole contiguous US —
        a disagreement of 92.8×, reported `solvent: True` either way.
        """
        r = collective_snapshot(_state(), parcels=make_urban_collective())
        assert r["pipeline"]["eoh_by_domain"]["ecological"] == \
            r["fiscal"]["ecological"]["ecological_eoh_total"]

    def test_it_is_the_SHARED_AREA_that_makes_them_agree(self):
        """
        WHICH GUARANTEE IS LOAD-BEARING, established by breaking the other one.
        A mutation sweep of this module showed that deleting the
        `eco_eoh_override=` line changes nothing: given the same area, the
        fiscal layer recomputes the same obligation anyway. So the AREA is what
        closes the 92.8× gap and the override is a second guard.
        
        Demonstrated here rather than asserted: the same population WITHOUT a
        stated area resolves from LAND_HECTARES_PER_CAPITA and lands somewhere
        else entirely, which is the defect in miniature.
        """
        from hours_eoh.core.fiscal import fiscal_snapshot
        st = _state()
        r = collective_snapshot(st, parcels=make_urban_collective())
        framed = r["fiscal"]["ecological"]["relocated_to_guf"]

        unframed = fiscal_snapshot(
            state={**st, "labor_income_teh": r["pipeline"]["teh_created"]},
        )["ecological"]["relocated_to_guf"]
        assert unframed != pytest.approx(framed, rel=0.10), (
            "an unstated area must NOT coincide with the parcels' own area, or "
            "this test proves nothing"
        )

    def test_labour_income_is_what_the_pipeline_says_was_earned(self):
        """Not an assumed income: the levy base is the minted TEH."""
        r = collective_snapshot(_state(), parcels=make_urban_collective())
        levied = r["fiscal"]["levies"]["total_levied"]
        assert levied == pytest.approx(
            r["pipeline"]["teh_created"] * 0.0125, rel=1e-9
        )

    def test_the_parcels_supply_both_the_fee_and_the_area(self):
        """One inventory, one jurisdiction — the two cannot describe different
        places because there is only one of them."""
        parcels = make_urban_collective()
        r = collective_snapshot(_state(), parcels=parcels)
        assert r["frame"]["land_hectares"] == pytest.approx(land_hectares_of(parcels))
        assert r["guf"]["revenue"] > 0.0

    @pytest.mark.parametrize("factory", [make_urban_collective, make_rural_collective])
    def test_land_area_uses_the_declared_conversion(self, factory):
        """
        `1 SLU = 100 m²` lived in three docstrings and no value until
        2026-08-28. It is bound here, not restated.

        BOTH archetypes, because the first version tested only urban — whose
        area is 302.5 ha — so hard-coding `hectares = 302.5` in the assembly
        passed every test. Measured at the one point where the defect is
        invisible, which is the ε=0.40 trap in a new place. Rural is 610.0 ha
        and catches it.
        """
        parcels = factory()
        expected = sum(p["area_slu"] for p in parcels) * SLU_HECTARES
        assert land_hectares_of(parcels) == pytest.approx(expected)
        assert land_hectares_of([]) == 0.0

    @pytest.mark.parametrize("factory", [make_urban_collective, make_rural_collective])
    def test_the_frame_area_is_the_parcels_area(self, factory):
        parcels = factory()
        r = collective_snapshot(_state(), parcels=parcels)
        assert r["frame"]["land_hectares"] == pytest.approx(land_hectares_of(parcels))


class TestAHalfStatedFrameIsRefused:

    def test_both_land_and_parcels_is_refused(self):
        with pytest.raises(ValueError, match="not both"):
            collective_snapshot(_state(), land_hectares=500.0,
                                parcels=make_urban_collective())

    def test_neither_is_refused(self):
        with pytest.raises(ValueError, match="supply land_hectares or parcels"):
            collective_snapshot(_state())

    @pytest.mark.parametrize("kw", ["population", "epsilon", "capital_stock_teh",
                                    "ecological_area_hectares", "eco_eoh_override",
                                    "guf_revenue"])
    def test_restating_a_frame_quantity_is_refused(self, kw):
        """
        A frame that can be overridden piecemeal is not a frame — the same
        discipline `fiscal_snapshot` applies to state-vs-loose.
        """
        with pytest.raises(ValueError, match="frame's to state"):
            collective_snapshot(_state(), land_hectares=302.5, **{kw: 1.0})

    def test_policy_still_passes_through(self):
        """Levy rates and the dividend split are policy, not frame."""
        r = collective_snapshot(_state(), land_hectares=302.5,
                                levy_rates={"sufficiency": 0.05})
        assert r["fiscal"]["levies"]["total_levied"] == pytest.approx(
            r["pipeline"]["teh_created"] * 0.05, rel=1e-9
        )


class TestWithoutParcels:

    def test_no_inventory_means_no_fee_and_the_verdict_says_so(self):
        """
        A collective with no assessed land raises no fee — and the recurring
        obligation the partition moved to GUF is then funded by nothing. That
        must read as a missing inventory, never as "the collective owes
        nothing", which is the misreading the Phase 4 caveat warns against.
        """
        r = collective_snapshot(_state(), land_hectares=302.5)
        assert r["guf"]["revenue"] == 0.0
        assert r["frame"]["parcel_count"] == 0
        assert "no assessed land" in r["verdict"]
        assert r["fiscal"]["ecological"]["relocated_to_guf"] > 0.0

    def test_land_area_still_frames_the_domain(self):
        small = collective_snapshot(_state(), land_hectares=100.0)
        large = collective_snapshot(_state(), land_hectares=200.0)
        assert large["fiscal"]["ecological"]["relocated_to_guf"] == pytest.approx(
            2.0 * small["fiscal"]["ecological"]["relocated_to_guf"], rel=1e-9
        )


class TestTheRelocatedObligationSurvivesTheOverride:
    """
    A DEFECT THIS SCENARIO FOUND IN ITS OWN DEPENDENCY (2026-08-29).

    `ecological_allocation` set `relocated_to_guf = 0.0` whenever an
    `eco_eoh_override` was supplied — and BOTH principal paths supply one, so
    the two calls that matter reported no relocated obligation and
    `guf["coverage"]` was vacuous exactly where it was meant to be read. An
    override states the DOMAIN total; it says nothing about what left the
    domain, and the relocated figure is derivable from the same arguments.
    """

    def test_the_override_path_still_reports_what_was_relocated(self):
        r = collective_snapshot(_state(), parcels=make_urban_collective())
        assert r["fiscal"]["ecological"]["relocated_to_guf"] > 0.0
        assert r["guf"]["obligation"] > 0.0
        assert r["guf"]["coverage"] is not None

    def test_it_agrees_with_the_no_override_path(self):
        """Same frame, same relocated figure, whichever route computed it."""
        from hours_eoh.core.fiscal import ecological_allocation
        direct = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40, available_teh=1e12,
            area_hectares=302.5,
        )["relocated_to_guf"]
        via = collective_snapshot(
            _state(), land_hectares=302.5
        )["fiscal"]["ecological"]["relocated_to_guf"]
        assert via == pytest.approx(direct, rel=1e-12)


class TestArcCoherence:

    @pytest.mark.parametrize("eps", ARC)
    def test_the_assembly_resolves_across_the_arc(self, eps):
        r = collective_snapshot(_state(eps=eps), parcels=make_urban_collective())
        assert r["pipeline"]["teh_created"] > 0.0
        assert r["guf"]["revenue"] > 0.0
        assert r["frame"]["epsilon"] == eps

    @pytest.mark.parametrize("eps", ARC)
    def test_both_archetypes_resolve(self, eps):
        for parcels in (make_urban_collective(), make_rural_collective()):
            r = collective_snapshot(_state(eps=eps), parcels=parcels)
            assert r["fiscal"]["solvent"] in (True, False)

    def test_the_fee_over_levy_ratio_is_U_SHAPED_not_monotone(self):
        """
        A SHAPE I ASSUMED AND THE TEST REFUTED (2026-08-29).

        I wrote this expecting the ratio to rise monotonically: the levy
        contracts with labour income while the fee scales with land held, so
        the fee should overtake it. Measured on the urban archetype at a
        30,000-person frame:

            ε      0.00    0.20    0.40    0.70    0.90    0.99
            ratio  29.61    7.81    2.82    0.87    0.74    2.23

        It FALLS then rises. The reason is that BOTH streams contract with ε and
        the levy peaks mid-arc: `teh_created` rises to a maximum around ε≈0.4–0.7
        and collapses after, while the fee declines monotonically with the labour
        content of land administration (α(ε), under the `retired` Ψ policy). The
        ratio is therefore high at BOTH ends — at subsistence because there is
        little registered labour to levy, and at post-scarcity because labour
        income has collapsed — and lowest where the labour economy is largest.

        `land/guf.py` says GUF "may become the Trust's dominant revenue source,
        replacing the contracting labor levy base". That is true at the ends and
        FALSE in the 0.7–0.9 band on this frame, where the fee is subordinate.
        The LEVEL is frame-dependent — it moves with the population paired
        against the parcels, which is precisely the pairing this module makes
        explicit — so the shape is pinned here and the level is not.
        """
        arc = (0.0, 0.20, 0.40, 0.70, 0.90, 0.99)
        ratios = [
            collective_snapshot(_state(eps=e), parcels=make_urban_collective())
            ["fiscal"]["trust"]["guf_over_levy"]
            for e in arc
        ]
        assert ratios != sorted(ratios), "the ratio is not monotone rising"
        trough = ratios.index(min(ratios))
        assert 0 < trough < len(arc) - 1, f"the minimum must be interior: {ratios}"
        assert ratios[0] > ratios[trough], "high at subsistence"
        assert ratios[-1] > ratios[trough], "and rising again at post-scarcity"

    def test_the_fee_never_vanishes_across_the_arc(self):
        """
        The half of the claim that DOES hold: the fee scales with land held, so
        it contracts with the labour content of administration but never to
        zero, while the levy base does collapse toward ε→1.
        """
        for e in (0.0, 0.40, 0.99):
            r = collective_snapshot(_state(eps=e), parcels=make_urban_collective())
            assert r["guf"]["revenue"] > 0.0
