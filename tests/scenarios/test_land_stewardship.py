"""
S1 — the stewardship-hours census, the ecological anchor's `resolves_by` run.

Covers `reference/land_stewardship.py` (measured land area + the ASSUMED
occupation→land-class attribution) and `scenarios/land_stewardship.py` (the
census, the floor, the falsification).

REPORTING ONLY. No constant moves on this — `TestChangesNothing` fails the
moment that stops being true.

The tests that matter most here are not the arithmetic ones. They are the
discipline guards: that unpriced land is EXCLUDED rather than costed at zero,
that the amenity scope stays separable, that the held-out occupations stay held
out, and that the census carries no ε — each of which is a way the census could
silently become something other than a measurement.
"""

import pytest

from hours_eoh.core.eoh_generation import ecological_statutory_floor
from hours_eoh.data import (
    AGENCY_STEWARDSHIP_ROLE_MIX,
    PRACTICE_EQUIPMENT_WIDTHS_FT,
)
from hours_eoh.reference.land_stewardship import (
    ACRE_HECTARES,
    AGENCY_AMBIGUOUS_SERIES,
    PARKS_CLASS,
    PARKS_FEDERAL,
    PARKS_OTHER,
    agency_role_mix,
    CROPLAND_ADOPTION_RESOLVES_BY,
    CROPLAND_HOURS_RESOLVES_BY,
    CROPLAND_HOURS_RESOLVES_BY_V2,
    FIELD_CAPACITY_CONSTANT,
    PRACTICE_OPERATIONS,
    effective_field_capacity,
    hours_per_acre,
    load_field_capacity_table,
    EQIP_HAS_NO_LABOUR_LINE,
    EXTENSION_MEASURES_PRODUCTION_NOT_STEWARDSHIP,
    load_agency_workforce,
    load_eqip_practices,
    load_extension_labour_hours,
    parks_split,
    HELD_OUT_OCCUPATIONS,
    STEWARDSHIP_ATTRIBUTIONS,
    UNPRICED_REASONS,
    derive_allocations,
    load_land_use,
    load_stewardship_employment,
    total_land_hectares,
)
from hours_eoh.reference.onet_multipliers import load_registry
from hours_eoh.scenarios.ecological_floor import implied_stewardship_intensity
from hours_eoh.data import AMENITY_STEWARDSHIP_WEIGHT
from hours_eoh.scenarios.land_stewardship import (
    ADOPTED_SCOPE,
    SCOPES,
    agency_report,
    allocation_band,
    amenity_curve,
    anchor_crossing_weight,
    frame_report,
    census_report,
    field_capacity_report,
    practice_hours_per_hectare,
    scope_comparison,
    stewardship_census,
    stewardship_intensities,
)

ARC = (0.0, 0.40, 0.99)


def load_load_use_classes():
    """MLU class names as the census sees them, before the parks split."""
    return [c["land_use"] for c in load_land_use()]


class TestLandUseExtract:
    """USDA ERS MLU 2022 — the measured denominator."""

    def test_the_nine_classes_partition_total_land_exactly(self):
        """MLU also publishes aggregates; mixing them in would double-count."""
        classes = load_land_use()
        assert len(classes) == 9
        assert sum(c["area_hectares"] for c in classes) == pytest.approx(
            total_land_hectares(), rel=1e-9
        )

    def test_total_is_the_us_land_area(self):
        # 2,261,144 thousand acres. Sanity against an independent recollection
        # of US land area (~915 Mha) — a unit slip would show here.
        assert total_land_hectares() == pytest.approx(9.1505e8, rel=1e-3)

    def test_acre_conversion_is_the_international_acre(self):
        assert ACRE_HECTARES == pytest.approx(0.40468564224, abs=1e-12)
        for c in load_land_use():
            assert c["area_hectares"] == pytest.approx(
                c["area_kacres"] * 1000.0 * ACRE_HECTARES, rel=1e-6
            )

    def test_every_class_is_either_attributed_or_has_a_stated_reason(self):
        """No land class may be silently dropped."""
        attributed = {a["land_use"] for a in STEWARDSHIP_ATTRIBUTIONS}
        # PARKS_CLASS is split into a federal (priced from agency data) and a
        # state-and-other (unpriced) row, so it is covered by the split, not by
        # an attribution or an unpriced reason under its own name.
        named = attributed | set(UNPRICED_REASONS) | {PARKS_CLASS}
        for c in load_load_use_classes():
            assert c in named, (
                f"{c!r} is neither attributed nor given a reason for being unpriced"
            )


class TestAttributionDiscipline:
    """The assumed mapping — the weak link, kept visible."""

    def test_every_attributed_occupation_exists_in_the_registry(self):
        emp = load_stewardship_employment(load_registry())
        wanted = {o for a in STEWARDSHIP_ATTRIBUTIONS for o in a["occupations"]}
        assert set(emp) == wanted

    def test_a_vanished_occupation_raises_rather_than_understating(self):
        """Dropping one silently would lower the floor with no signal."""
        rows = [r for r in load_registry() if r["occ6"] != "454011"]
        with pytest.raises(ValueError, match="absent from the registry"):
            load_stewardship_employment(rows)

    def test_held_out_occupations_are_not_attributed_anywhere(self):
        """They err the floor LOW, which is the safe direction — keep it so."""
        attributed = {o for a in STEWARDSHIP_ATTRIBUTIONS for o in a["occupations"]}
        for held in HELD_OUT_OCCUPATIONS:
            assert held["occ6"] not in attributed
            assert held["reason"].strip(), "a held-out occupation must say why"

    def test_logging_is_excluded_from_forest_stewardship(self):
        """Extraction is production, not the labour the land demands."""
        attributed = {o for a in STEWARDSHIP_ATTRIBUTIONS for o in a["occupations"]}
        for logging in ("454021", "454022", "454023"):
            assert logging not in attributed

    def test_every_attribution_states_its_basis(self):
        for a in STEWARDSHIP_ATTRIBUTIONS:
            assert len(a["basis"]) > 80, (
                "an attribution is an assumption; it must argue for itself"
            )


class TestUnpricedIsExcludedNotZero:
    """The load-bearing behaviour, shared with the personal floor."""

    def test_unpriced_classes_carry_none_not_zero(self):
        census = stewardship_census("with_amenity")
        unpriced = [c for c in census if c["hours_per_hectare_year"] is None]
        assert unpriced, "the census must have unpriced land — coverage is 30%"
        for c in unpriced:
            assert c["hours_per_hectare_year"] is None
            assert c["area_hectares"] > 0.0, "an unpriced class keeps its area"

    def test_coverage_is_well_below_one_and_says_so(self):
        # 0.303 -> 0.381 when federal parks became priceable (agency role mix).
        rep = census_report("with_amenity")
        assert 0.33 < rep["coverage"] < 0.45
        assert "LOWER BOUND" in rep["verdict"]

    def test_excluded_area_is_reported_not_discarded(self):
        rep = census_report("with_amenity")
        excluded = sum(u["area_hectares"] for u in rep["unpriced"])
        assert excluded + rep["area_priced_hectares"] == pytest.approx(
            rep["area_total_hectares"], rel=1e-9
        )

    def test_costing_the_unpriced_at_zero_would_change_the_answer(self):
        """The behaviour is load-bearing, so demonstrate the difference."""
        census = stewardship_census("with_amenity")
        zeroed = [
            {**c, "hours_per_hectare_year": c["hours_per_hectare_year"] or 0.0}
            for c in census
        ]
        real = ecological_statutory_floor(census)
        fake = ecological_statutory_floor(zeroed)
        assert real["floor_hours"] == pytest.approx(fake["floor_hours"])
        # Same total hours, but the intensity is diluted 3.3x by land nobody costed.
        # 3.3x before federal parks were priced; 2.6x after, because the priced
        # area grew while the unpriced area shrank.
        assert real["mean_hours_per_hectare"] > 2.0 * fake["mean_hours_per_hectare"]
        assert fake["coverage"] == pytest.approx(1.0)


class TestTheScopeQuestion:
    """Amenity groundskeeping decides the answer; both readings stay visible."""

    def test_ecosystem_scope_lands_ABOVE_the_anchor(self):
        """
        REVERSED BY PHASE 4b (2026-08-17), and this is the largest single finding
        of that change. Until the frame was declared, the anchor was compared at
        an intensity inflated 464x by pairing the WHOLE contiguous US with a
        million people — so forest read 0.49x the anchor and this test asserted
        `< 1.0`, recorded as "forest falsifies 'the anchor is 2-3 orders low' in
        the OPPOSITE direction".

        Against a frame-consistent anchor the ecosystem scope reads 222x ABOVE
        it. The earlier falsification was an artefact of the frame mismatch: the
        mismatch was INFLATING the anchor and thereby MASKING the domain-balance
        defect it was being used to test. The hypothesis it appeared to refute
        is now supported on every class, forest included.
        """
        rep = census_report("ecosystem")
        assert rep["ratio_to_anchor"] > 100.0
        assert rep["measured_hours_per_hectare"] == pytest.approx(0.1773, abs=0.01)

    def _superseded_test_ecosystem_scope_lands_below_the_anchor(self):
        rep = census_report("ecosystem")
        assert rep["ratio_to_anchor"] < 1.0
        assert rep["measured_hours_per_hectare"] == pytest.approx(0.182, abs=0.01)

    def test_amenity_scope_lands_well_above_the_anchor(self):
        # 9.15 -> 7.31: federal parks added 71.6 Mha at 0.161 h/ha, diluting the
        # amenity-scope mean without changing the urban intensity.
        rep = census_report("with_amenity")
        assert rep["ratio_to_anchor"] > 15.0
        assert rep["measured_hours_per_hectare"] == pytest.approx(7.31, abs=0.1)

    def test_the_two_scopes_disagree_by_more_than_an_order_of_magnitude(self):
        """THE finding. If this collapses, the scope question has been resolved
        somewhere without being argued — which is what the test exists to catch."""
        cmp = scope_comparison()
        assert cmp["spread_factor"] > 10.0
        assert "the definition is" in cmp["verdict"]

    def test_amenity_land_is_excluded_under_ecosystem_scope(self):
        eco = {r["land_use"]: r for r in stewardship_intensities("ecosystem")}
        assert eco["Land in urban areas"]["hours_per_hectare_year"] is None
        assert "amenity" in eco["Land in urban areas"]["reason"]

    def test_unknown_scope_raises(self):
        with pytest.raises(ValueError, match="scope must be one of"):
            stewardship_intensities("whatever")


class TestEpsilonInvariance:
    """A generation floor must carry no automation term."""

    @pytest.mark.parametrize("scope", SCOPES)
    def test_census_is_identical_across_the_arc(self, scope):
        """ε enters fulfilment, never this. Built once, compared at three ε."""
        base = stewardship_census(scope)
        for _eps in ARC:
            assert stewardship_census(scope) == base

    @pytest.mark.parametrize("scope", SCOPES)
    def test_intensities_are_finite_and_non_negative(self, scope):
        for r in stewardship_intensities(scope):
            h = r["hours_per_hectare_year"]
            if h is not None:
                assert h >= 0.0
                assert h == h  # not NaN


class TestTheFalsification:
    """What the census actually says about the anchor."""

    def test_forest_intensity_matches_the_worked_example(self):
        rows = {r["land_use"]: r for r in stewardship_intensities("ecosystem")}
        forest = rows["Forest-use land (all)"]
        assert forest["workers"] == pytest.approx((10.3 + 14.0) * 1000.0)
        assert forest["hours_per_hectare_year"] == pytest.approx(0.182, abs=0.005)

    def test_the_one_percent_coincidence_did_not_survive_pricing_parks(self):
        """It WAS within 3% (9.154 vs 9.433) and is now 22.5% away (7.306 vs
        9.433), because federal parks added 71.6 Mha of low-intensity land. It
        was recorded as a coincidence, not a result, and this is what that
        caution was for."""
        rep = census_report("with_amenity")
        assert rep["measured_hours_per_hectare"] == pytest.approx(7.31, abs=0.1)
        assert rep["measured_hours_per_hectare"] < rep["required_h_per_ha_at_1pc_share"]

    def test_the_implied_intensity_is_now_POPULATION_INVARIANT(self):
        """
        THE TRAP THIS TEST GUARDED IS GONE — and it was the frame mismatch.

        It used to assert that `ecological_eoh` is population-INVARIANT (an
        absolute US total) while the implied INTENSITY deflates 335x with
        population, so only intensity was comparable and only at the reference
        scale. Both halves were consequences of a single defect: an obligation
        keyed to the whole contiguous US being divided by whatever population
        the caller happened to pass.

        After Phase 4b the obligation scales with population and the INTENSITY
        does not — which is the right way round, and it is what makes the census
        comparison meaningful at any scale rather than at one privileged one.
        """
        ref = implied_stewardship_intensity(population=1e6)
        us = implied_stewardship_intensity(population=335e6)
        # the obligation now scales
        assert us["ecological_eoh"] == pytest.approx(335.0 * ref["ecological_eoh"], rel=1e-9)
        # and the intensity is invariant, to float precision
        assert us["hours_per_hectare_year"] == pytest.approx(
            ref["hours_per_hectare_year"], rel=1e-12
        )

        rep = census_report("with_amenity")
        assert rep["anchor_hours_per_hectare"] == pytest.approx(
            ref["hours_per_hectare_year"]
        )

    def test_report_carries_its_jurisdiction(self):
        rep = census_report("with_amenity")
        assert "United States" in rep["jurisdiction"]

    def test_work_year_is_the_derived_figure_not_a_convention(self):
        rep = census_report("with_amenity")
        assert 1700.0 < rep["hours_per_worker_year"] < 2000.0
        assert rep["hours_per_worker_year"] != 2080.0
        assert rep["hours_per_worker_year"] != 1800.0


class TestAllocationIsWeightedNotBinary:
    """The held-out occupations brought in at a weight — corners, not a fit."""

    def test_supervisor_allocation_is_derived_from_supervisee_headcount(self):
        """67,000 supervisors contribute 764 workers, not 67,000 and not zero."""
        alloc = derive_allocations(load_registry(), "derived")
        workers = alloc["Forest-use land (all)"]["451011"]
        assert workers == pytest.approx(764.0, abs=15.0)
        assert workers < 0.02 * 67_000.0, "the chain must discount heavily"

    def test_held_out_policy_allocates_nothing(self):
        assert derive_allocations(load_registry(), "held_out") == {}

    def test_unknown_policy_raises(self):
        with pytest.raises(ValueError, match="policy must be one of"):
            derive_allocations(load_registry(), "vibes")

    def test_the_band_does_not_cross_the_anchor_in_either_scope(self):
        """THE result: the allocation choice barely matters, the scope decides."""
        for scope in SCOPES:
            band = allocation_band(scope)
            assert not band["crosses_anchor"], (
                f"{scope}: the anchor comparison has become sensitive to the "
                "allocation policy — re-read the band before quoting a ratio"
            )

    def test_allocation_moves_far_less_than_scope(self):
        eco = allocation_band("ecosystem")
        scope_spread = scope_comparison()["spread_factor"]
        assert eco["band_factor"] < 2.0
        assert scope_spread > 10.0 * eco["band_factor"]

    def test_area_policy_moves_forest_but_stays_below_the_anchor(self):
        band = allocation_band("ecosystem")
        # Phase 4b: was < 1.0 against the 464x-inflated anchor; now 309x above.
        # The ORDERING this test exists for is unaffected — see below.
        assert band["policies"]["area"]["ratio_to_anchor"] > 100.0
        assert (
            band["policies"]["area"]["measured_hours_per_hectare"]
            > band["policies"]["held_out"]["measured_hours_per_hectare"]
        )


class TestCoverageInflationGuard:
    """A partial allocation may not price an incomplete class."""

    def test_advisory_hours_on_cropland_are_excluded_not_merged(self):
        rows = {
            r["land_use"]: r
            for r in stewardship_intensities("ecosystem", allocation="area")
        }
        crop = rows["Total cropland"]
        assert crop["allocated_workers"] > 0.0, "the area policy does allocate here"
        assert crop["hours_per_hectare_year"] is None, "but it must NOT price the class"
        assert crop["excluded_partial_hours"] > 0.0, "and the hours must be reported"

    def test_coverage_does_not_move_with_the_allocation_policy(self):
        """The trap: pricing cropland on advisory labour alone would take
        coverage 0.303 -> 0.470 while dragging the mean down."""
        band = allocation_band("with_amenity")
        covs = {v["coverage"] for v in band["policies"].values()}
        assert len(covs) == 1, f"coverage moved with allocation: {covs}"

    def test_only_complete_attributions_are_priced(self):
        for scope in SCOPES:
            for r in stewardship_intensities(scope, allocation="area"):
                if r["hours_per_hectare_year"] is not None:
                    assert r["complete"], (
                        f"{r['land_use']} priced without a complete attribution"
                    )

    def test_excluded_partial_hours_are_totalled_in_the_report(self):
        rep = census_report("ecosystem", allocation="area")
        assert rep["excluded_partial_hours"] > 1e7


class TestAmenityWeightIsContinuous:
    """Between the two corners, and the anchor crossing sits near the origin."""

    def test_weight_overrides_scope(self):
        a = census_report("with_amenity", amenity_weight=0.0)
        b = census_report("ecosystem")
        assert a["measured_hours_per_hectare"] == pytest.approx(
            b["measured_hours_per_hectare"]
        )

    def test_intensity_is_monotone_in_the_weight(self):
        curve = amenity_curve()["curve"]
        vals = [r["measured_hours_per_hectare"] for r in curve]
        assert vals == sorted(vals)

    def test_the_anchor_is_now_CROSSED_AT_EVERY_POSITIVE_WEIGHT(self):
        """
        PHASE 4b REVERSED THE AMENITY-WEIGHT QUESTION, and this is the second
        large consequence of declaring the frame.

        The weight mattered because the census crossed the anchor at
        w* = 0.0288, just above zero: at any smaller weight the census read
        BELOW the anchor and at any larger one above it, so the weight set the
        SIGN of the comparison and had to be argued and declared
        (AMENITY_STEWARDSHIP_WEIGHT = 0.0468, band [0.0468, 0.0699]).

        Against a frame-consistent anchor the solved crossing weight is
        NEGATIVE — the census exceeds the anchor even with the entire amenity
        class excluded. So the weight no longer sets the sign at all; it sets
        only the magnitude, and the scope question that needed a charter
        decision to settle the direction no longer needs one for that purpose.
        The declared weight stays, because it still governs the magnitude and
        both corners are still reported.
        """
        w = anchor_crossing_weight()
        assert w < 0.0, "a positive crossing weight would restore the old regime"

        # the census is above the anchor at w = 0 — i.e. with NO amenity labour
        rep_zero = census_report("with_amenity", amenity_weight=0.0)
        assert rep_zero["ratio_to_anchor"] > 1.0

    def test_the_declared_weight_sits_above_the_crossing(self):
        """The adopted position is above w*, so the census clears the anchor on
        the charter weight — the sign does not depend on the weight, only the
        magnitude does."""
        assert AMENITY_STEWARDSHIP_WEIGHT > anchor_crossing_weight()
        assert census_report("declared")["ratio_to_anchor"] > 1.0

    def test_coverage_steps_once_then_holds(self):
        """Discontinuous at w=0 (urban becomes priced), flat above it."""
        curve = amenity_curve()["curve"]
        assert curve[0]["coverage"] == pytest.approx(0.3516, abs=0.005)
        assert {round(r["coverage"], 6) for r in curve[1:]} == {
            round(curve[-1]["coverage"], 6)
        }

    def test_weight_outside_the_unit_interval_raises(self):
        for bad in (-0.1, 1.1):
            with pytest.raises(ValueError, match="amenity_weight must be in"):
                stewardship_intensities("with_amenity", amenity_weight=bad)


class TestTheAnchorIsKeyedToNothing:
    """
    The defect stated exactly, AND ITS CLOSURE: ecological used to be the only
    domain with no extensive quantity behind it.

    THIS CLASS WENT STALE AND ITS TEST BECAME UNFALSIFIABLE (found 2026-08-27).
    `ecological_eoh` gained `area_hectares` on 2026-08-16, but this test still
    read:

        # No area or population parameter exists to pass.
        assert ecological_eoh(0.82) == ecological_eoh(0.82)

    Three separate faults in four lines. The comment was FALSE — the parameter
    exists, and another test in this same file passes it. The assertion was a
    pure TAUTOLOGY: `f(x) == f(x)` cannot fail for any deterministic f, so it
    pinned nothing while reading as coverage. And the expected value restated
    `ECOLOGICAL_BASE_RATE` as the bare literal `500_000.0` — the shadow-literal
    pattern this repo hunts, in the file documenting an anchor defect.

    It now asserts the two things that are actually true and load-bearing: the
    no-area path resolves to the DECLARED reference frame, and the with-area
    path is linear in area — the extensive behaviour whose absence was the
    original defect.
    """

    def test_without_an_area_it_resolves_to_the_declared_reference_frame(self):
        """
        Bound to the constant, not to a literal. If ECOLOGICAL_BASE_RATE moves,
        this must move with it or say why. Pinned at the pre-Phase-4f policy
        because the frame question and the partition question are separate.
        """
        from hours_eoh.core.eoh_generation import ecological_eoh
        from hours_eoh.data import ECOLOGICAL_BASE_RATE

        assert ecological_eoh(0.82, standing_response="domain") == pytest.approx(
            ECOLOGICAL_BASE_RATE / 0.82, rel=1e-9
        )

    def test_with_an_area_it_is_linear_in_area(self):
        """
        THE PROPERTY WHOSE ABSENCE WAS THE DEFECT. Ecological demand is a
        property of ground, so doubling the ground doubles the obligation.
        """
        from hours_eoh.core.eoh_generation import ecological_eoh

        one = ecological_eoh(0.82, area_hectares=1.0e6)
        two = ecological_eoh(0.82, area_hectares=2.0e6)
        assert two == pytest.approx(2.0 * one, rel=1e-9)
        assert one > 0.0

    def test_the_other_domains_do_scale(self):
        from hours_eoh.core.eoh_generation import personal_eoh

        small = personal_eoh(1_000_000.0)
        large = personal_eoh(2_000_000.0)
        assert large == pytest.approx(2.0 * small, rel=1e-6)


class TestTheAmenitySignOff:
    """Author decision 2026-08-16: include at a declared weight."""

    def test_the_adopted_scope_is_the_declared_weight_not_a_corner(self):
        assert ADOPTED_SCOPE == "declared"
        assert census_report()["amenity_weight"] == AMENITY_STEWARDSHIP_WEIGHT

    def test_the_reported_weight_is_the_weight_actually_applied(self):
        """These were computed in two places and desynced — one source now."""
        for scope, expected in (
            ("ecosystem", 0.0),
            ("declared", AMENITY_STEWARDSHIP_WEIGHT),
            ("with_amenity", 1.0),
        ):
            rep = census_report(scope)
            assert rep["amenity_weight"] == expected
            direct = census_report("with_amenity", amenity_weight=expected)
            assert rep["measured_hours_per_hectare"] == pytest.approx(
                direct["measured_hours_per_hectare"]
            )

    def test_the_declared_weight_sits_inside_its_stated_band(self):
        """band: [0.0468, 0.0699] from the amenity class's own composition."""
        assert 0.0468 <= AMENITY_STEWARDSHIP_WEIGHT <= 0.0699

    def test_the_band_is_the_occupational_composition(self):
        """The band must remain DERIVABLE from the registry, not a memory."""
        emp = {r["occ6"]: r["employment_k"] for r in load_registry()}
        total = emp["373011"] + emp["373013"] + emp["373012"]
        assert emp["373013"] / total == pytest.approx(0.0468, abs=0.0005)
        assert (emp["373013"] + emp["373012"]) / total == pytest.approx(
            0.0699, abs=0.0005
        )

    def test_the_corners_survive_the_decision(self):
        """A decision whose alternatives have been deleted is not reviewable."""
        assert {"ecosystem", "with_amenity"} <= set(SCOPES)
        assert scope_comparison()["spread_factor"] > 10.0


class TestEcologicalIsNowExtensiveInArea:
    """The form fix. Level held; only the shape changed."""

    def test_the_default_reproduces_the_old_absolute_exactly(self):
        """Form fix, not level fix — a level change here would be a separate
        decision and would have moved the whole suite."""
        from hours_eoh.core.eoh_generation import ecological_eoh
        from hours_eoh.data import ECOLOGICAL_BASE_RATE

        # `standing_response="domain"` is the pre-Phase-4f policy this test was
        # written against; 4f moved the default on 2026-08-28 and is a partition
        # decision, not an area one. Pinning it keeps this test about the FORM.
        assert ecological_eoh(1.0, standing_response="domain") == pytest.approx(
            ECOLOGICAL_BASE_RATE, rel=1e-12
        )
        assert ecological_eoh(0.82, standing_response="domain") == pytest.approx(
            ECOLOGICAL_BASE_RATE / 0.82, rel=1e-12
        )

    def test_intensity_times_reference_area_is_the_anchor(self):
        from hours_eoh.data import (
            ECOLOGICAL_BASE_RATE,
            ECOLOGICAL_INTENSITY_BASE,
            US_MAINLAND_HECTARES,
        )

        assert US_MAINLAND_HECTARES * ECOLOGICAL_INTENSITY_BASE == pytest.approx(
            ECOLOGICAL_BASE_RATE, rel=1e-9
        )

    def test_the_obligation_now_scales_with_area(self):
        """THE defect closed: it used to be identical for any area."""
        from hours_eoh.core.eoh_generation import ecological_eoh

        one = ecological_eoh(1.0, area_hectares=1.0e6)
        two = ecological_eoh(1.0, area_hectares=2.0e6)
        assert two == pytest.approx(2.0 * one, rel=1e-12)
        assert ecological_eoh(1.0, area_hectares=0.0) == pytest.approx(0.0)

    def test_the_spike_scales_with_area_too(self):
        """The threshold spike is a multiple of the same scale; leaving it
        absolute would have made collapse area-independent."""
        from hours_eoh.core.eoh_generation import ecological_eoh_breakdown

        a = ecological_eoh_breakdown(0.30, area_hectares=1.0e6)
        b = ecological_eoh_breakdown(0.30, area_hectares=2.0e6)
        assert a["spike"] > 0.0
        assert b["spike"] == pytest.approx(2.0 * a["spike"], rel=1e-12)

    def test_legacy_base_rate_callers_are_unaffected(self):
        from hours_eoh.core.eoh_generation import ecological_eoh

        assert ecological_eoh(1.0, base_rate=123_456.0,
                              standing_response="domain") == pytest.approx(123_456.0)
        # under the adopted 4f default a supplied base still scales the domain,
        # but pristine land owes it nothing — the standing term is GUF's.
        assert ecological_eoh(1.0, base_rate=123_456.0) == 0.0

    def test_the_scale_path_is_reported(self):
        from hours_eoh.core.eoh_generation import ecological_eoh_breakdown

        assert ecological_eoh_breakdown(1.0)["scale_path"] == "reference_frame"
        assert (
            ecological_eoh_breakdown(1.0, area_hectares=1e6)["scale_path"] == "area"
        )
        assert (
            ecological_eoh_breakdown(1.0, base_rate=1.0)["scale_path"] == "base_rate"
        )

    def test_negative_area_raises(self):
        from hours_eoh.core.eoh_generation import ecological_eoh

        with pytest.raises(ValueError, match="area_hectares must be"):
            ecological_eoh(1.0, area_hectares=-1.0)

    @pytest.mark.parametrize("eps", ARC)
    def test_arc_coherence_at_every_epsilon(self, eps):
        from hours_eoh.core.eoh_generation import ecological_eoh

        v = ecological_eoh(0.82, epsilon=eps, area_hectares=1.0e8)
        assert v > 0.0
        assert v == v  # not NaN


class TestTheFrameIsUsSized:
    """US population against US mainland area — the testing frame."""

    def test_the_us_is_over_landed_relative_to_the_global_default(self):
        f = frame_report()
        assert f["over_landed"] is True
        assert f["us_hectares_per_capita"] == pytest.approx(2.285, abs=0.01)
        assert f["ratio_to_shipped"] == pytest.approx(1.385, abs=0.01)

    def test_the_frame_uses_mainland_not_the_us_total(self):
        """Alaska's 150 Mha is unmanaged and would dilute every intensity 16%."""
        from hours_eoh.data import US_MAINLAND_HECTARES

        assert US_MAINLAND_HECTARES < total_land_hectares()
        assert US_MAINLAND_HECTARES == pytest.approx(7.655e8, rel=1e-3)

    def test_the_per_capita_burden_is_dwarfed_by_the_personal_domain(self):
        """Domain balance restated per capita — still the open defect."""
        f = frame_report()
        assert f["burden_h_per_capita_if_all_land_priced"] < 10.0


class TestAgencyRoleMixIsMeasured:
    """OPM Federal Workforce Data closes the role mix, and the class is priced."""

    def test_headcounts_are_exact_not_the_rounded_faq_figure(self):
        mix = agency_role_mix()
        assert mix["NPS"]["total"] == 19_315
        assert mix["FWS"]["total"] == 7_789
        assert mix["combined"]["total"] == 27_104

    def test_the_band_is_derivable_from_the_shipped_extract(self):
        """band [0.2263, 0.4073] must stay computable, not remembered."""
        mix = agency_role_mix()["combined"]
        assert mix["low"] == pytest.approx(0.2263, abs=0.0005)
        assert mix["high"] == pytest.approx(0.4073, abs=0.0005)
        assert AGENCY_STEWARDSHIP_ROLE_MIX == pytest.approx(mix["low"], abs=0.0005)

    def test_the_two_agencies_disagree_by_about_five(self):
        """NPS is visitor services on land; FWS refuges are land management."""
        mix = agency_role_mix()
        assert mix["FWS"]["low"] / mix["NPS"]["low"] == pytest.approx(5.3, abs=0.5)

    def test_the_ambiguous_series_are_the_band(self):
        """0025 and 0456 ARE the gap between low and high — name them or the
        band is unreviewable."""
        rows = load_agency_workforce()
        gap = sum(
            r["headcount"] for r in rows
            if r["series_code"] in AGENCY_AMBIGUOUS_SERIES
        )
        mix = agency_role_mix()["combined"]
        assert gap == mix["ambiguous"]
        assert (mix["high"] - mix["low"]) == pytest.approx(
            gap / mix["total"], abs=1e-9
        )

    def test_the_raw_figure_overstates_by_the_role_mix(self):
        """The correction that overturned the earlier directional claim."""
        rep = agency_report()
        assert rep["raw_overstates_by"] == pytest.approx(4.4, abs=0.2)
        assert rep["raw_hours_per_hectare_year"] > 0.7
        assert rep["stewardship_hours_per_hectare_year"] < 0.2

    def test_parks_now_lands_below_forest_not_six_times_above(self):
        """Directional reversal, pinned so it cannot silently flip back."""
        rep = agency_report()
        assert rep["vs_forest"] < 1.0
        assert rep["vs_census_mean"] < 1.0

    def test_pricing_parks_lowers_the_mean_and_raises_coverage(self):
        rep = census_report()
        assert rep["coverage"] == pytest.approx(0.3808, abs=0.002)
        assert rep["measured_hours_per_hectare"] == pytest.approx(0.498, abs=0.01)
        assert rep["ratio_to_anchor"] > 1.0

    def test_the_class_is_split_and_area_is_conserved(self):
        total = next(
            c["area_hectares"] for c in load_land_use() if c["land_use"] == PARKS_CLASS
        )
        parts = parks_split()
        assert sum(p["area_hectares"] for p in parts) == pytest.approx(total, rel=1e-9)
        assert len(parts) == 2

    def test_the_state_share_stays_unpriced(self):
        """State-agency staffing is outside the federal data; it must not
        inherit the federal intensity."""
        rows = {r["land_use"]: r for r in stewardship_intensities()}
        assert rows[PARKS_FEDERAL]["hours_per_hectare_year"] is not None
        assert rows[PARKS_OTHER]["hours_per_hectare_year"] is None
        assert rows[PARKS_OTHER]["area_hectares"] > 3.0e7

    def test_the_wrong_call_shape_is_recorded_not_the_wrong_conclusion(self):
        r = agency_report()["resolves_by"]
        assert "wrong call shape" in r or "dataset segment" in r


class TestEqipCannotPriceStewardship:
    """A checked negative result — and a correction to two written claims."""

    def test_the_practice_inventory_loads(self):
        practices = load_eqip_practices()
        assert len(practices) == 210
        assert all(p["scenarios"] > 0 for p in practices)

    def test_no_practice_claims_a_labour_line_or_a_time_unit(self):
        """31 units in the source file, not one of them time. Gal/Hr, Bu/Hr and
        kBTU/Hr are flow and energy rates, not labour hours."""
        assert EQIP_HAS_NO_LABOUR_LINE is True
        for p in load_eqip_practices():
            for u in p["units"]:
                assert not u.lower().startswith(("hr", "hour", "day", "min")), (
                    f"{p['practice_code']} claims a time unit {u!r} — if the "
                    "schedule has gained one, EQIP_HAS_NO_LABOUR_LINE is stale"
                )

    def test_foregone_income_practices_are_flagged(self):
        """Income foregone is price formation and inadmissible under the
        method rule; it must be visible, not buried in a dollar column."""
        flagged = [p for p in load_eqip_practices() if p["names_foregone_income"]]
        assert len(flagged) == 9

    def test_the_cropland_reason_no_longer_points_at_eqip_as_the_answer(self):
        """The reason previously promised EQIP 'itemise labour per acre per
        practice'. It does not. A wrong pointer must be corrected where it was
        written, not just noted elsewhere."""
        reason = UNPRICED_REASONS["Total cropland"]
        assert "does not work" in reason or "EQIP_HAS_NO_LABOUR_LINE" in reason
        assert "CROPLAND_HOURS_RESOLVES_BY" in reason

    def test_the_replacement_instrument_records_what_was_ruled_out(self):
        assert "enterprise budget" in CROPLAND_HOURS_RESOLVES_BY
        assert "NOT the NRCS EQIP" in CROPLAND_HOURS_RESOLVES_BY

    def test_cropland_and_rangeland_remain_unpriced(self):
        rows = {r["land_use"]: r for r in stewardship_intensities()}
        for cls in ("Total cropland", "Grassland pasture and range"):
            assert rows[cls]["hours_per_hectare_year"] is None


class TestExtensionHoursAreProductionNotStewardship:
    """Fourth instrument checked. Right units, wrong quantity."""

    def test_the_extract_loads_and_is_in_hours(self):
        rows = load_extension_labour_hours()
        assert len(rows) == 5
        for r in rows:
            assert r["labour_high"] >= r["labour_low"] > 0.0

    def test_every_row_says_what_it_is_not(self):
        """The label is load-bearing: these hours are one careless join away
        from becoming a stewardship figure."""
        assert EXTENSION_MEASURES_PRODUCTION_NOT_STEWARDSHIP is True
        for r in load_extension_labour_hours():
            assert "NOT land stewardship" in r["measures"]

    def test_harvest_dwarfs_the_labour_line_where_both_are_given(self):
        """Even as a production figure it is partial — asparagus 5-20 against
        25-300 h/acre of harvest."""
        rows = [r for r in load_extension_labour_hours() if r["harvest_low"]]
        assert rows
        assert any(r["harvest_low"] > r["labour_high"] for r in rows)

    def test_cropland_is_still_not_priced_by_it(self):
        rows = {r["land_use"]: r for r in stewardship_intensities()}
        assert rows["Total cropland"]["hours_per_hectare_year"] is None

    def test_the_next_instrument_is_currency_free_by_construction(self):
        assert "field-capacity" in CROPLAND_HOURS_RESOLVES_BY_V2
        assert "RULED OUT ALREADY" in CROPLAND_HOURS_RESOLVES_BY_V2


class TestFieldCapacityIsPhysics:
    """Fifth instrument. Right quantity, right units, no price in the chain."""

    def test_the_identity_reproduces_the_publications_worked_example(self):
        """6 mph x 12 ft x 0.75 / 8.25 = 6.545; the worksheet rounds to 6.55."""
        assert effective_field_capacity(12.0, 6.0, 0.75) == pytest.approx(6.545, abs=0.01)

    def test_the_constant_is_exact_not_calibrated(self):
        assert FIELD_CAPACITY_CONSTANT == pytest.approx(43_560.0 / 5_280.0, abs=1e-12)

    def test_capacity_is_linear_in_every_term(self):
        base = effective_field_capacity(15.0, 5.0, 0.7)
        assert effective_field_capacity(30.0, 5.0, 0.7) == pytest.approx(2 * base)
        assert effective_field_capacity(15.0, 10.0, 0.7) == pytest.approx(2 * base)
        assert effective_field_capacity(15.0, 5.0, 0.35) == pytest.approx(base / 2)

    def test_impossible_inputs_raise_rather_than_understating_hours(self):
        for w, sp, e in ((0.0, 5.0, 0.7), (-1.0, 5.0, 0.7), (15.0, 0.0, 0.7)):
            with pytest.raises(ValueError, match="must be positive"):
                effective_field_capacity(w, sp, e)
        for e in (0.0, 1.5, -0.1):
            with pytest.raises(ValueError, match="field efficiency"):
                effective_field_capacity(15.0, 5.0, e)

    def test_the_table_carries_ranges_not_point_values(self):
        table = load_field_capacity_table()
        assert len(table) == 17
        for name, m in table.items():
            assert 0.0 < m["efficiency_low"] <= m["efficiency_high"] <= 1.0, name
            assert 0.0 < m["speed_low"] <= m["speed_high"], name

    def test_unknown_implement_raises_rather_than_borrowing_a_neighbour(self):
        with pytest.raises(KeyError, match="unknown implement"):
            hours_per_acre("hovercraft", 15.0)

    def test_wider_machines_mean_fewer_hours_per_acre(self):
        """Not noise in the estimate — capital substituting for labour, which is
        why this is a delivery productivity and not a physical constant."""
        narrow = hours_per_acre("grain_drill", 15.0)
        wide = hours_per_acre("grain_drill", 30.0)
        assert wide["hours_per_acre_low"] == pytest.approx(
            narrow["hours_per_acre_low"] / 2.0
        )


class TestPracticeHoursDoNotPriceCropland:
    """The route delivers hours. It still cannot price the class."""

    def test_cover_crop_lands_in_a_plausible_band(self):
        d = practice_hours_per_hectare("340_cover_crop")
        assert d["hours_per_hectare_low"] == pytest.approx(0.303, abs=0.01)
        assert d["hours_per_hectare_high"] == pytest.approx(0.844, abs=0.01)

    def test_mechanical_termination_costs_more_than_spraying(self):
        chem = practice_hours_per_hectare("340_cover_crop")
        mech = practice_hours_per_hectare("340_cover_crop_mechanical")
        assert mech["hours_per_hectare_low"] > chem["hours_per_hectare_low"]

    def test_no_till_is_zero_hours_and_that_is_the_point(self):
        """The case that breaks a naive hours-are-good reading: the practice's
        benefit is the passes it REMOVES, so a labour census alone cannot rank
        conservation practices by value."""
        d = practice_hours_per_hectare("329_residue_tillage_no_till")
        assert d["hours_per_hectare_low"] == 0.0
        assert d["hours_per_hectare_high"] == 0.0
        assert d["operations"] == []

    def test_unknown_practice_raises(self):
        with pytest.raises(KeyError, match="unknown practice"):
            practice_hours_per_hectare("340_cover_crop_by_hand")

    def test_the_report_refuses_to_price_cropland(self):
        rep = field_capacity_report()
        assert rep["cropland_priced"] is False
        assert "adoption" in rep["missing_input"]
        rows = {r["land_use"]: r for r in stewardship_intensities()}
        assert rows["Total cropland"]["hours_per_hectare_year"] is None

    def test_the_missing_input_is_named_and_is_a_new_gap(self):
        assert "Census of Agriculture" in CROPLAND_ADOPTION_RESOLVES_BY
        assert "LAST missing input" in CROPLAND_ADOPTION_RESOLVES_BY

    def test_the_adoption_unknown_is_BOUNDED_above(self):
        """The strongest form of not-knowing. Even 100% cover-crop adoption on
        every acre of US cropland adds 0.27-0.74x the current census — so the
        missing adoption fraction cannot transform the picture, only move it
        within a known range. At realistic adoption (5-7%) it is 1-5%."""
        cover = practice_hours_per_hectare("340_cover_crop")
        cropland_ha = next(
            c["area_hectares"] for c in load_land_use()
            if c["land_use"] == "Total cropland"
        )
        census = census_report()["floor_hours"]
        ceiling_low = cover["hours_per_hectare_low"] * cropland_ha
        ceiling_high = cover["hours_per_hectare_high"] * cropland_ha
        assert ceiling_low / census == pytest.approx(0.27, abs=0.03)
        assert ceiling_high / census == pytest.approx(0.74, abs=0.05)
        assert ceiling_high < census, (
            "even universal adoption stays below the measured census; if this "
            "flips, the bound in the verdict is stale"
        )

    def test_the_report_states_the_ceiling(self):
        rep = field_capacity_report()
        lo, hi = rep["adoption_ceiling_ratio"]
        assert 0.0 < lo < hi < 1.0

class TestEquipmentWidthsArePinned:
    """These sit OUTSIDE the shadow-constant ratchet (`OPERATIVE_LAYERS` omits
    `reference/`) and they scale the output linearly, so they are pinned here
    instead. This test is standing in for a gate that does not reach them."""

    def test_every_operation_used_has_a_width(self):
        needed = {
            op for spec in PRACTICE_OPERATIONS.values() for op in spec["operations"]
        }
        assert needed <= set(PRACTICE_EQUIPMENT_WIDTHS_FT), (
            f"missing widths for {needed - set(PRACTICE_EQUIPMENT_WIDTHS_FT)}"
        )

    def test_every_width_names_a_real_implement(self):
        table = load_field_capacity_table()
        for op in PRACTICE_EQUIPMENT_WIDTHS_FT:
            assert op in table, f"{op} has a width but no ASAE entry"

    def test_the_shipped_widths_are_what_the_figures_were_computed_at(self):
        assert PRACTICE_EQUIPMENT_WIDTHS_FT == {
            "grain_drill": 15.0,
            "boom_sprayer": 60.0,
            "roller_packer": 20.0,
            "field_cultivator": 25.0,
            "row_cultivator": 20.0,
            "disk": 25.0,
            "mower_conditioner_rotary": 12.0,
        }

    def test_halving_a_width_doubles_the_practice_hours(self):
        """The blast radius, demonstrated rather than asserted in prose — so
        anyone changing a width sees what it costs.

        Mutates the dict IN PLACE rather than rebinding, because the scenario
        layer imported the same object and a rebind would not reach it — which
        is itself worth knowing about every dict constant in `data.py`."""
        before = practice_hours_per_hectare("340_cover_crop")["hours_per_hectare_low"]
        original = dict(PRACTICE_EQUIPMENT_WIDTHS_FT)
        try:
            PRACTICE_EQUIPMENT_WIDTHS_FT["grain_drill"] = 7.5
            PRACTICE_EQUIPMENT_WIDTHS_FT["boom_sprayer"] = 30.0
            after = practice_hours_per_hectare("340_cover_crop")[
                "hours_per_hectare_low"
            ]
        finally:
            PRACTICE_EQUIPMENT_WIDTHS_FT.clear()
            PRACTICE_EQUIPMENT_WIDTHS_FT.update(original)
        assert after == pytest.approx(2.0 * before, rel=1e-9)
        assert PRACTICE_EQUIPMENT_WIDTHS_FT["grain_drill"] == 15.0


class TestTheCliDispatchStaysWiredUp:
    """A renamed key in `agency_report` broke `eoh scenario run land_stewardship`
    and every unit test still passed, because nothing exercised the dispatch.
    This is the smoke test that would have caught it."""

    def _run(self, *cli_args):
        """Drive the REAL parser, so argument wiring is covered too — a
        hand-built Namespace would silently supply defaults the CLI does not."""
        import argparse

        from utils.scenario_cmd import _dispatch, build_parser

        parser = argparse.ArgumentParser()
        build_parser(parser.add_subparsers(dest="cmd"))
        args = parser.parse_args(
            ["scenario", "run", "land_stewardship", *cli_args]
        )
        return _dispatch(args)

    def test_dispatch_runs_and_every_key_resolves(self):
        out = self._run()
        assert isinstance(out, dict)
        assert out["scope"] == ADOPTED_SCOPE
        assert out["summary_table"]

    def test_dispatch_surfaces_each_sub_report(self):
        """One key per report, so a rename in any of them fails here."""
        out = self._run()
        for key in (
            "coverage",
            "ratio_to_anchor",
            "allocation_band",
            "amenity_weight_at_anchor",
            "us_hectares_per_capita_frame",
            "agency_stewardship_h_per_ha",
            "agency_raw_overstates_by",
            "cover_crop_h_per_ha_band",
            "cropland_adoption_ceiling_ratio",
            "cropland_priced",
        ):
            assert key in out, f"CLI lost {key!r}"

    def test_the_output_is_json_serialisable(self):
        import json

        json.dumps(self._run())

    @pytest.mark.parametrize("scope", SCOPES)
    def test_every_scope_dispatches(self, scope):
        assert self._run("--scope", scope)["scope"] == scope

    @pytest.mark.parametrize("allocation", ("held_out", "derived", "area"))
    def test_every_allocation_dispatches(self, allocation):
        assert self._run("--allocation", allocation)["allocation"] == allocation

    def test_the_amenity_weight_flag_reaches_the_report(self):
        out = self._run("--amenity-weight", "0.5")
        assert out["amenity_weight"] == pytest.approx(0.5)


class TestChangesNothing:
    """S1 is reporting only."""

    def test_ecological_base_rate_is_untouched(self):
        from hours_eoh.data import ECOLOGICAL_BASE_RATE

        assert ECOLOGICAL_BASE_RATE == 500_000.0

    def test_the_census_does_not_write_to_any_constant(self):
        from hours_eoh import data

        before = data.ECOLOGICAL_BASE_RATE
        census_report("with_amenity")
        scope_comparison()
        assert data.ECOLOGICAL_BASE_RATE == before
