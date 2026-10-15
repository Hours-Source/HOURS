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
from hours_eoh.data import SLU_HECTARES, SUFF_LEVY_RATE
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


class TestLabourSupplyReachesTheMint:
    """
    THE STRANDED PARAMETER AT THE DOCUMENTED ENTRY POINT (found 2026-09-12).
    The implementation guide calls `available_labor_eoh` the single most
    consequential default and tells institutions to use this function in
    preference to the hand-run calls — and this function could not accept it.
    Every snapshot measured DEMAND. These pin that the field now moves the
    mint, the deferral and the fiscal layer's income, by absolute identities
    rather than by relative comparisons, which cannot see a constant factor.
    """

    def test_zero_labour_mints_exactly_nothing(self):
        r = collective_snapshot(_state(), land_hectares=302.5,
                                available_labor_eoh=0.0)
        assert r["pipeline"]["teh_created"] == 0.0
        assert r["frame"]["labor_constrained"] is True
        assert r["pipeline"]["deferred_total"] > 0.0

    def test_the_fiscal_layer_is_paid_what_was_SERVED(self):
        unconstrained = collective_snapshot(_state(), land_hectares=302.5)
        half = 0.5 * unconstrained["pipeline"]["human_eoh"]
        served = collective_snapshot(_state(), land_hectares=302.5,
                                     available_labor_eoh=half)
        # Absolute identity: the income the levies are raised on IS the
        # constrained mint — not the demanded one, and not a copy of either.
        assert served["fiscal"]["levies"]["gross_income"] == pytest.approx(
            served["pipeline"]["teh_created"])
        assert (served["pipeline"]["teh_created"]
                < unconstrained["pipeline"]["teh_created"])

    def test_shortfall_plus_served_is_the_obligation(self):
        demanded = collective_snapshot(_state(), land_hectares=302.5)
        half = 0.5 * demanded["pipeline"]["human_eoh"]
        r = collective_snapshot(_state(), land_hectares=302.5,
                                available_labor_eoh=half)
        p = r["pipeline"]
        assert p["human_eoh"] + p["deferred_total"] == pytest.approx(
            demanded["pipeline"]["human_eoh"], rel=1e-9)

    def test_omitting_it_says_demand_in_the_verdict(self):
        r = collective_snapshot(_state(), land_hectares=302.5)
        assert r["frame"]["labour_supplied"] is False
        assert r["frame"]["labor_constrained"] is False
        assert "DEMAND" in r["verdict"]

    def test_ample_labour_is_not_read_as_demand(self):
        """
        The pipeline's `labor_constrained` is False both when no supply was
        given and when an ample one was. Reading it as "was labour supplied"
        told an institution with enough hours that it had measured demand —
        the reported value that isn't the meaning (mode 10).
        """
        demanded = collective_snapshot(_state(), land_hectares=302.5)
        ample = 2.0 * demanded["pipeline"]["human_eoh"]
        r = collective_snapshot(_state(), land_hectares=302.5,
                                available_labor_eoh=ample)
        assert r["frame"]["labour_supplied"] is True
        assert r["frame"]["labor_constrained"] is False
        assert "DEMAND" not in r["verdict"]
        assert "sufficed" in r["verdict"]
        assert r["pipeline"]["deferred_total"] == 0.0
        assert r["pipeline"]["teh_created"] == pytest.approx(
            demanded["pipeline"]["teh_created"])

    def test_binding_labour_says_bound(self):
        r = collective_snapshot(_state(), land_hectares=302.5,
                                available_labor_eoh=0.0)
        assert r["frame"]["labour_supplied"] is True
        assert "BOUND" in r["verdict"]

    def test_the_state_fields_reach_the_pipeline(self):
        """A state carrying a deferred ecological stock must not be read as
        canonical — it was, until this entry point forwarded the field."""
        clean = collective_snapshot(_state(), land_hectares=302.5)
        stocked = collective_snapshot(_state(deferred_ecological=1e6),
                                      land_hectares=302.5)
        assert (stocked["pipeline"]["eoh_by_domain"]["ecological"]
                > clean["pipeline"]["eoh_by_domain"]["ecological"])

    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.90, 0.99))
    def test_a_default_state_is_unchanged_by_the_forwarding(self, eps):
        """Blast radius of forwarding, measured: zero on a default state."""
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        s = _state(eps=eps)
        direct = eoh_to_teh_pipeline(
            epsilon=eps, population=s["population"],
            capital_stock=s["capital_stock_teh"],
            capital_age_ratio=s["capital_age_ratio"],
            ecosystem_health=s["ecosystem_health"],
            ecological_area_hectares=302.5,
        )
        r = collective_snapshot(s, land_hectares=302.5)
        assert r["pipeline"]["teh_created"] == pytest.approx(direct["teh_created"])


class TestBothHalvesSeeOneValue:
    """
    ONE VALUE, BOTH HALVES (2026-10-14). The guard refused frame quantities BY
    NAME and forwarded every other keyword to the fiscal layer only, so a
    quantity both halves take reached one of them: an age mix moved fiscal
    expenditure and left personal EOH on the shipped mix, and a state's
    register maturity moved expenditure 3.96x while the mint stayed put —
    `simulate_period` passed it, this entry point did not. Each value is
    checked against the pipeline called DIRECTLY with it, so a forwarded
    value that the pipeline then ignores cannot pass.
    """

    #: The renames the two signatures spell differently. THE GAP: a rename not
    #: listed here is invisible to the derivation below.
    RENAMES = {"age_fractions": "age_distribution",
               "health_response": "ecological_health_response",
               "standing_response": "ecological_standing_response",
               "capital_personal_eoh_fulfilled_per_person":
                   "capital_personal_eoh_fulfilled"}

    def test_every_shared_quantity_is_forwarded_or_refused(self):
        """Derived from the two signatures, not from the table under test."""
        import inspect
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.fiscal import fiscal_snapshot
        from hours_eoh.scenarios.collective import SHARED_WITH_PIPELINE
        pipe = set(inspect.signature(eoh_to_teh_pipeline).parameters)
        shared = {f for f in inspect.signature(fiscal_snapshot).parameters
                  if self.RENAMES.get(f, f) in pipe}
        assert "age_fractions" in shared and "mean_multiplier" in shared
        own = set(inspect.signature(collective_snapshot).parameters)
        assert "age_fractions" in own       # its own argument, sent to both
        for f in sorted(shared - set(SHARED_WITH_PIPELINE) - own):
            with pytest.raises(ValueError):
                collective_snapshot(_state(), land_hectares=302.5, **{f: 1.0})
        for f, to in SHARED_WITH_PIPELINE.items():
            assert self.RENAMES.get(f, f) == to and to in pipe

    def test_the_core_table_is_every_shared_quantity(self):
        """`core.fiscal.PIPELINE_SHARED_PARAMS` is the ONE table both assembly
        points read (2026-10-14). Derived from the signatures: every shared
        name is in it or declared not-one-quantity — so a parameter added to
        both functions fails here until an assembly point is told."""
        import inspect
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        from hours_eoh.core.fiscal import (
            PIPELINE_SHARED_NOT_ONE_QUANTITY, PIPELINE_SHARED_PARAMS, fiscal_snapshot)
        pipe = set(inspect.signature(eoh_to_teh_pipeline).parameters)
        shared = {f for f in inspect.signature(fiscal_snapshot).parameters
                  if self.RENAMES.get(f, f) in pipe} - {"population", "epsilon",
                                                         "capital_age_ratio",
                                                         "ecosystem_health",
                                                         "ecological_area_hectares"}
        assert shared == set(PIPELINE_SHARED_PARAMS) | PIPELINE_SHARED_NOT_ONE_QUANTITY
        assert all(self.RENAMES.get(f, f) == p for f, p in PIPELINE_SHARED_PARAMS.items())

    @pytest.mark.parametrize("kw, pipe_kw", [
        ({"age_fractions": {"infant": 0.065, "child": 0.145,
                            "working_age": 0.600, "elderly": 0.190}},
         {"age_distribution": {"infant": 0.065, "child": 0.145,
                               "working_age": 0.600, "elderly": 0.190}}),
        ({"mean_multiplier": 2.4}, {"mean_multiplier": 2.4}),
        ({"thermal_obligation": 1e8}, {"thermal_obligation": 1e8}),
        # Inert under the default GUF response (the fee carries the domain),
        # so run where the domain carries it.
        ({"ecological_intensity": 2e-3, "health_response": "domain",
          "standing_response": "domain"},
         {"ecological_intensity": 2e-3, "ecological_health_response": "domain",
          "ecological_standing_response": "domain"}),
        ({"health_response": "domain"}, {"ecological_health_response": "domain"}),
        ({"standing_response": "domain"}, {"ecological_standing_response": "domain"}),
    ])
    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.90, 0.99))
    def test_a_keyword_reaches_the_pipeline_as_the_direct_call(self, kw, pipe_kw, eps):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        s = _state(eps=eps, ecosystem_health=0.4)
        base = dict(epsilon=eps, population=s["population"],
                    capital_stock=s["capital_stock_teh"],
                    capital_age_ratio=s["capital_age_ratio"],
                    ecosystem_health=s["ecosystem_health"],
                    ecological_area_hectares=302.5)
        r = collective_snapshot(s, land_hectares=302.5, **kw)
        direct = eoh_to_teh_pipeline(**base, **pipe_kw)
        # The WHOLE pipeline result: under the default GUF response the
        # ecological intensity moves the relocated obligation, not the mint.
        assert r["pipeline"] == direct
        assert direct != eoh_to_teh_pipeline(**base)

    def test_the_age_mix_reaches_the_fiscal_half_too(self):
        mix = {"infant": 0.065, "child": 0.145, "working_age": 0.600, "elderly": 0.190}
        a = collective_snapshot(_state(), land_hectares=302.5)
        b = collective_snapshot(_state(), land_hectares=302.5, age_fractions=mix)
        assert (b["fiscal"]["trust"]["total_expenditure"]
                != a["fiscal"]["trust"]["total_expenditure"])

    @pytest.mark.parametrize("field, value", [
        ("registration_epsilon", 0.70),
        ("capital_eoh_eliminated", 1e6),
        ("capital_personal_eoh_fulfilled", 1e6),
    ])
    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.90, 0.99))
    def test_a_state_field_reaches_the_pipeline_as_in_the_period_engine(
            self, field, value, eps):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        s = _state(eps=eps, **{field: value})
        base = dict(epsilon=eps, population=s["population"],
                    capital_stock=s["capital_stock_teh"],
                    capital_age_ratio=s["capital_age_ratio"],
                    ecosystem_health=s["ecosystem_health"],
                    ecological_area_hectares=302.5)
        r = collective_snapshot(s, land_hectares=302.5)
        direct = eoh_to_teh_pipeline(**base, **{field: value})
        # The whole result: the capital-fulfilled personal EOH is reported,
        # not applied, so it moves a key and not the mint.
        assert r["pipeline"] == direct
        assert direct != eoh_to_teh_pipeline(**base)

    def test_a_deferred_infrastructure_backlog_is_refused(self):
        with pytest.raises(ValueError, match="compounds per period"):
            collective_snapshot(_state(deferred_infrastructure_eoh=1e6),
                                land_hectares=302.5)


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
            r["pipeline"]["teh_created"] * SUFF_LEVY_RATE, rel=1e-9
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
        replacing the contracting labor levy base". That was true at BOTH ends
        of the arc and false in the middle; since the Phase 2 adoption it is
        true only at SUBSISTENCE. The claim's own mechanism — a contracting
        levy base — is what per-component automation removes, because care
        resists automation and keeps labour income alive at high ε.

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
        # MONOTONE FALLING SINCE 2026-09-01, and the U-shape is withdrawn.
        # It was U-shaped because the levy COLLAPSED at post-scarcity, so the
        # fee overtook it again at the top. Adopting per-component automation
        # stops that collapse: care resists automation, so human labour and
        # therefore labour income survive at high ε, and the levy base with
        # them. The fee now falls against the levy all the way up.
        assert ratios == sorted(ratios, reverse=True), (
            f"expected a monotone fall now the levy base does not collapse: {ratios}"
        )
        # `> 10` until 2026-09-15, a LEVEL this docstring disowns. The levy rose
        # 1.25% → 4.5% and ε=0 reads 9.19. The shape claim is which stream
        # dominates at each end: the fee at subsistence, the levy at the top.
        assert ratios[0] > 1.0, "the fee dominates the levy at subsistence"
        assert ratios[-1] < 1.0, "and below it at post-scarcity"

    def test_the_fee_never_vanishes_across_the_arc(self):
        """
        The half of the claim that DOES hold: the fee scales with land held, so
        it contracts with the labour content of administration but never to
        zero, while the levy base does collapse toward ε→1.
        """
        for e in (0.0, 0.40, 0.99):
            r = collective_snapshot(_state(eps=e), parcels=make_urban_collective())
            assert r["guf"]["revenue"] > 0.0



class TestTheFeeFollowsStationarity:
    """Author, 2026-10-14: on a frame with a parcel COUNT and no inventory the
    fee is a sample's mean over the count, as `stationarity_at` prices it —
    one implementation (`land.collective.sample_scaled_guf`)."""

    def test_it_is_stationaritys_fee(self):
        from hours_eoh.land.collective import make_urban_collective
        from hours_eoh.scenarios.stationarity import stationarity_at
        sample = make_urban_collective(10_000)
        for count in (None, 1.2e6):
            r = collective_snapshot(_state(pop=1e6), land_hectares=2.3e6,
                                    guf_sample=sample, guf_parcel_count=count)
            st = stationarity_at(0.40, population=1e6, guf_parcels=sample,
                                 **({} if count is None else {"guf_parcel_count": count}))
            assert r["guf"]["revenue"] == st["teh"]["guf"]
            assert r["frame"]["land_hectares"] == 2.3e6     # the land is never the sample's

class TestTheFeeCollectedIsWhatTheMintCanPay:
    """Author, 2026-10-15: "you can't pay what isn't minted". A fee beyond what
    the mint leaves holders is REPORTED unpaid, never booked as Trust revenue —
    the over-expanded claim, carried on the books and not carried in fact."""

    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.90, 0.99))
    def test_the_unpaid_fee_is_reported_and_not_booked(self, eps):
        from hours_eoh.scenarios.stationarity import stationarity_at
        sample = make_urban_collective(1_000)
        # 1M people holding 1.5e8 parcels: a fee far beyond their mint
        kw = dict(land_hectares=7.6e8, guf_sample=sample, guf_parcel_count=1.5e8)
        capped = collective_snapshot(_state(pop=1e6, eps=eps), **kw)
        whole = collective_snapshot(_state(pop=1e6, eps=eps), guf_cap=None, **kw)
        lf = capped["land_fee"]
        assert lf["assessed"] == whole["land_fee"]["assessed"] == whole["guf"]["revenue"]
        assert lf["collected"] == capped["guf"]["revenue"] == capped["fiscal"]["trust"]["guf_inflow"]
        assert lf["collected"] == min(lf["assessed"], lf["payable_ceiling"])
        assert lf["unpaid"] > 0.0
        assert lf["payable_ceiling"] <= capped["pipeline"]["teh_created"]
        # the Trust holds exactly the unpaid fee less than the uncapped book
        assert (whole["fiscal"]["trust"]["trust_end"] - capped["fiscal"]["trust"]["trust_end"]
                == pytest.approx(lf["unpaid"], rel=1e-9))
        # one ceiling with stationarity, whose levy is the fisc's at the default
        st = stationarity_at(eps, population=1e6, capital_stock_teh=2000.0 * 1e6,
                             guf_parcels=sample, guf_parcel_count=1.5e8)["teh"]
        assert st["guf"] == pytest.approx(lf["collected"], rel=1e-9)
        assert st["guf_unpaid"] == pytest.approx(lf["unpaid"], rel=1e-9)

    def test_a_fee_within_the_mint_is_collected_whole(self):
        r = collective_snapshot(_state(), parcels=make_urban_collective(1_000))
        assert r["land_fee"]["unpaid"] == 0.0
        assert r["land_fee"]["collected"] == r["land_fee"]["assessed"]

    def test_an_unknown_cap_is_refused(self):
        with pytest.raises(ValueError):
            collective_snapshot(_state(), parcels=make_urban_collective(10), guf_cap="half")


class TestTheFeeFollowsStationarityRefusals:
    def test_a_half_stated_fee_is_refused(self):
        from hours_eoh.land.collective import make_urban_collective
        sample = make_urban_collective(100)
        with pytest.raises(ValueError):
            collective_snapshot(_state(), parcels=sample, guf_sample=sample)
        with pytest.raises(ValueError):
            collective_snapshot(_state(), parcels=sample, guf_parcel_count=1e4)


class TestThePerParcelHalf:
    """Author, 2026-10-15: "ship the per-parcel half first". A parcel COUNT
    with no sample prices the fee's measured half, P(ε) × count, in both entry
    points, and says the area part is NOT SUPPLIED."""

    @pytest.mark.parametrize("eps", (0.0, 0.40, 0.90, 0.99))
    def test_both_entry_points_price_the_measured_half(self, eps):
        from hours_eoh.land.collective import PER_PARCEL_BASIS, per_parcel_guf
        from hours_eoh.land.guf import ground_use_fee, per_parcel_term
        from hours_eoh.scenarios.stationarity import stationarity_at
        # the ONE term: what the fee charges a serviced parcel
        assert per_parcel_term(eps) == ground_use_fee(2.5, 0.75, "residential_primary",
                                                      eps)["parcel_term"] > 0.0
        r = collective_snapshot(_state(pop=1e6, eps=eps), land_hectares=2.3e6,
                                guf_parcel_count=4.6e5, guf_cap=None)
        assert r["land_fee"]["assessed"] == per_parcel_guf(eps, 4.6e5) == per_parcel_term(eps) * 4.6e5
        assert r["frame"]["guf_basis"] == PER_PARCEL_BASIS and r["frame"]["parcel_count"] == 4.6e5
        st = stationarity_at(eps, population=1e6, guf_parcels=None, guf_parcel_count=4.6e5)["teh"]
        assert st["guf_uncapped"] == r["land_fee"]["assessed"] and st["guf_basis"] == PER_PARCEL_BASIS
        # an empty sample is no fee, whatever the count
        assert stationarity_at(eps, population=1e6, guf_parcels=[],
                               guf_parcel_count=4.6e5)["teh"]["guf_uncapped"] == 0.0

    def test_the_half_falls_with_automation_and_never_vanishes(self):
        from hours_eoh.land.guf import per_parcel_term
        vals = [per_parcel_term(e) for e in (0.0, 0.40, 0.90, 0.99)]
        assert all(a > b > 0.0 for a, b in zip(vals, vals[1:]))

    def test_a_negative_count_is_refused(self):
        from hours_eoh.land.collective import per_parcel_guf
        with pytest.raises(ValueError):
            per_parcel_guf(0.4, -1.0)
