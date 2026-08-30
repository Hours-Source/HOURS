"""
Tests for scenarios/guf_magnitude.py — GUF's derived revenue target (Option 1)
and the two-part tariff the measured cost implies (Option 2).

Discipline, following the two censuses this module sits on top of:
  * the ASSUMED input (what each occupation's cost scales with) is tested for
    completeness and for naming only occupations that exist — the
    `unused_innocuous_names` lesson;
  * findings are asserted as ORDERINGS and SIGNS wherever the level is
    calibration that will move;
  * the falsification is RUN, not asserted in prose;
  * `TestMagnitudeChangesNothing` pins that this is reporting only.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import GUF_USE_SCALE_FACTOR, SLU_HECTARES
from hours_eoh.land.collective import compute_collective_guf, make_urban_collective
from hours_eoh.land.guf import (
    FEE_BASES,
    PSI_POLICIES,
    TERM_BASIS,
    USE_CATEGORIES,
    epsilon_scaling,
    ground_use_fee,
    psi_application,
)
from hours_eoh.reference import servicing
from hours_eoh.scenarios.guf_magnitude import (
    PARCEL_COUNT_RESOLVES_BY,
    amenity_sensitivity,
    basis_table,
    conservation_credit_check,
    magnitude_report,
    psi_double_application,
    psi_policy_comparison,
    recurring_target_by_class,
    scaling_basis_shares,
    subdivision_invariance,
    target_vs_realised,
    two_part_rates,
)
from hours_eoh.scenarios.servicing_census import census

ARC = (0.0, 0.40, 0.99)


# ---------------------------------------------------------------------------
# The assumed input: the scaling basis
# ---------------------------------------------------------------------------

class TestScalingBasisIsDeclaredAndComplete:

    def test_every_attributed_occupation_has_a_basis(self):
        """No servicing worker may fall outside the cut."""
        for att in servicing.SERVICING_ATTRIBUTIONS:
            assert att["occ6"] in servicing.SCALING_BASIS, att["title"]
        for occ in servicing.BROAD_SCOPE_WEIGHTS:
            assert occ in servicing.SCALING_BASIS, occ

    def test_no_basis_entry_names_an_occupation_that_is_not_in_the_census(self):
        """
        A declared classification nobody exercises is a classification nobody
        reviews. Every key must belong to an occupation this census actually
        counts, under core or broad.
        """
        known = {a["occ6"] for a in servicing.SERVICING_ATTRIBUTIONS}
        known |= set(servicing.BROAD_SCOPE_WEIGHTS)
        assert set(servicing.SCALING_BASIS) == known

    def test_every_basis_is_one_of_the_declared_three(self):
        for occ, entry in servicing.SCALING_BASIS.items():
            assert entry["basis"] in servicing.SCALING_BASES, occ
            assert entry["why"].strip(), occ

    @pytest.mark.parametrize("scope", ["core", "broad"])
    def test_the_basis_cut_reconciles_with_the_census_total(self, scope):
        """
        The second cut is the SAME workers, so the totals must agree exactly —
        otherwise one of the two is dropping people silently.
        """
        cut = servicing.workers_by_scaling_basis(scope)
        assert cut["missing_basis"] == []
        assert cut["total_workers"] == pytest.approx(
            servicing.servicing_workers(scope)["total_workers"]
        )

    def test_unknown_scope_raises(self):
        with pytest.raises(ValueError):
            servicing.workers_by_scaling_basis("nonsense")


# ---------------------------------------------------------------------------
# Option 2 — the two-part tariff
# ---------------------------------------------------------------------------

class TestScalingBasisShares:

    def test_shares_sum_to_one(self):
        s = scaling_basis_shares("core")
        assert sum(s["shares"].values()) == pytest.approx(1.0)

    def test_the_fee_tracks_a_minority_of_the_cost_structure(self):
        """
        THE OPTION 2 FINDING, as a sign rather than a level: the Ground Use Fee
        scales with area alone, and area-scaling work is less than half the
        measured cost. Levels are calibration; the inequality is the claim.
        """
        s = scaling_basis_shares("core")
        assert s["area_share"] < 0.5
        assert s["shares"]["parcel"] > 0.0
        assert s["shares"]["throughput"] > 0.0
        lo, hi = s["parcel_share_range"]
        assert lo < hi                      # throughput brackets, never folded
        assert lo + s["area_share"] < 1.0

    def test_the_split_is_robust_to_the_scope_judgement(self):
        """
        Like the census's own 1.05× scope robustness: the broad scope adds
        weighted workers on both sides and the area share barely moves.
        """
        core = scaling_basis_shares("core")["area_share"]
        broad = scaling_basis_shares("broad")["area_share"]
        assert abs(core - broad) < 0.05

    def test_hours_reconcile_with_the_census(self):
        s = scaling_basis_shares("core")
        assert s["total_hours"] == pytest.approx(census("core")["total_hours"])


class TestTwoPartRates:

    def test_the_parcel_rate_is_measured_now_that_the_divisor_exists(self):
        """
        THE EXCLUSION IS RETIRED (2026-08-30). It read "no national parcel count
        is carried in this repo"; `reference/parcels` carries one. An exclusion
        whose stated blocker has been removed and is left standing is the
        status-note-outliving-its-decision failure this repo has caught eight
        times, so the retirement is pinned rather than merely performed.
        """
        r = two_part_rates("core")
        assert r["u_area_h_per_ha_yr"] > 0.0
        assert r["u_parcel_h_per_parcel_yr"] is not None
        assert r["u_parcel_h_per_parcel_yr"] == pytest.approx(
            r["u_parcel_hours_total"] / r["u_parcel_parcels"]
        )
        assert "u_parcel_excluded_reason" not in r, (
            "the exclusion key must go, not merely be contradicted by a "
            "neighbouring value — two accounts of one status is how `psi` came "
            "to differ from `psi_applied`"
        )

    def test_the_parcel_rate_is_declared_a_lower_bound_and_says_why(self):
        """
        THE HALF THAT DID NOT CLOSE, and it must not be quoted as a point. The
        numerator is restricted to SERVICED_LAND_CLASSES; the denominator is
        every parcel in the country. Restricting the denominator can only remove
        parcels, so it can only RAISE the rate — hence errs LOW.

        The gap is deliberately not quantified. Parcels concentrate in developed
        land so the bound is probably close, but "probably close" is not a
        measurement, and guessing it would be the fitting this module exists to
        refuse.
        """
        r = two_part_rates("core")
        assert r["u_parcel_is_lower_bound"] is True
        assert r["u_parcel_errs"] == "LOW"
        assert "restrict" in r["u_parcel_bound_reason"].lower()
        assert "FIELD:" in r["u_parcel_resolves_by"]
        assert r["u_parcel_resolves_by"] == PARCEL_COUNT_RESOLVES_BY

    def test_the_resolves_by_still_names_the_unclosed_half(self):
        """
        The pointer stays live because it is only HALF satisfied: the count
        exists, the land-class restriction does not. A `resolves_by` retired on
        partial satisfaction is how a bound silently becomes a point.
        """
        assert "restricted to the land classes" in PARCEL_COUNT_RESOLVES_BY

    def test_the_parcel_rate_is_not_the_area_rate_in_disguise(self):
        """
        The two rates have different denominators and different units. If they
        ever coincided it would mean one divisor had leaked into the other.
        """
        r = two_part_rates("core")
        assert r["u_parcel_parcels"] != pytest.approx(r["serviced_hectares"])
        assert r["u_parcel_h_per_parcel_yr"] != pytest.approx(
            r["u_area_h_per_ha_yr"]
        )

    def test_the_area_rate_is_the_area_share_of_the_census_rate(self):
        """The governing equation, checked against its own inputs."""
        r = two_part_rates("core")
        s = scaling_basis_shares("core")
        assert r["u_area_h_per_ha_yr"] == pytest.approx(
            census("core")["hours_per_hectare_year"] * s["area_share"]
        )

    def test_slu_conversion_uses_the_constant(self):
        r = two_part_rates("core")
        assert r["u_area_teh_per_slu_yr"] == pytest.approx(
            r["u_area_h_per_ha_yr"] * SLU_HECTARES
        )

    def test_area_only_scale_factor_is_below_the_aggregate_and_far_below_shipped(self):
        """
        ORDERING, not level: dividing only the area-scaling hours by area must
        give a smaller factor than dividing all of them, and both must sit far
        below the shipped ×100.
        """
        r = two_part_rates("core")
        from hours_eoh.scenarios.servicing_census import shipped_vs_measured

        aggregate = shipped_vs_measured("core")["implied_scale_factor"]
        assert r["implied_scale_factor_area_only"] < aggregate
        assert aggregate < GUF_USE_SCALE_FACTOR


class TestSubdivisionInvariance:
    """
    THE FALSIFICATION, run rather than asserted. Phase 2 recorded the urban
    overshoot's mechanism as parcel density; it is not.
    """

    @pytest.mark.parametrize("epsilon", ARC)
    def test_doubling_the_parcel_count_does_not_move_the_fee(self, epsilon):
        r = subdivision_invariance(epsilon)
        assert r["parcels_after"] == 2 * r["parcels_before"]
        assert r["invariant"] is True
        assert r["h_per_ha_after"] == r["h_per_ha_before"]
        assert r["ratio"] == pytest.approx(1.0)

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            subdivision_invariance(1.5)


# ---------------------------------------------------------------------------
# Option 1 — the derived revenue target
# ---------------------------------------------------------------------------

class TestRecurringTarget:

    def test_the_target_is_the_sum_of_two_disjoint_censuses(self):
        rows = {r["land_use"]: r for r in recurring_target_by_class()}
        urban = rows["Land in urban areas"]
        assert urban["complete"] is True
        assert urban["target_h_per_ha"] == pytest.approx(
            urban["servicing_h_per_ha"] + urban["stewardship_h_per_ha"]
        )

    def test_adding_stewardship_raises_the_target_above_servicing_alone(self):
        """The Option 1 correction, in one inequality."""
        rows = {r["land_use"]: r for r in recurring_target_by_class()}
        urban = rows["Land in urban areas"]
        assert urban["target_h_per_ha"] > urban["servicing_h_per_ha"]

    def test_incomplete_classes_are_marked_and_not_silently_totalled(self):
        """
        A class missing either half must SAY which half. Seven of nine are
        incomplete on the stewardship side, and that is the honest state.
        """
        rows = recurring_target_by_class()
        incomplete = [r for r in rows if not r["complete"]]
        assert incomplete, "expected unpriced classes to survive as unpriced"
        for r in incomplete:
            assert r["missing"], r["land_use"]
            for half in r["missing"]:
                assert half in ("servicing", "stewardship")

    def test_unserviced_classes_carry_no_servicing_rate(self):
        """Forest is in no serviced land class; it must not inherit the rate."""
        rows = {r["land_use"]: r for r in recurring_target_by_class()}
        assert rows["Forest-use land (all)"]["servicing_h_per_ha"] is None

    def test_unknown_scope_raises(self):
        with pytest.raises(ValueError):
            recurring_target_by_class(servicing_scope="nonsense")


class TestTargetVsRealised:

    @pytest.mark.parametrize("epsilon", ARC)
    def test_runs_across_the_arc(self, epsilon):
        r = target_vs_realised(epsilon)
        rows = {x["archetype"]: x for x in r["rows"]}
        assert rows["urban"]["target_h_per_ha"] > 0.0
        assert rows["urban"]["ratio"] > 0.0

    def test_the_urban_fee_over_collects_at_mid_arc(self):
        """SIGN, not level. The level is calibration and has moved before."""
        assert target_vs_realised(0.40)["urban_ratio"] > 1.0

    def test_the_rural_comparison_is_withdrawn_not_repeated(self):
        """
        The rural archetype is 70% agricultural, and agricultural land is in no
        serviced class and unpriced by the stewardship census. Both halves of
        its target are missing, so no ratio may be reported — Phase 2's figure
        survives only under its own name, flagged.
        """
        rows = {x["archetype"]: x for x in target_vs_realised(0.40)["rows"]}
        rural = rows["rural"]
        assert rural["like_for_like"] is False
        assert rural["target_h_per_ha"] is None
        assert rural["ratio"] is None
        assert rural["phase_2_comparison"] > 0.0

    def test_urban_is_compared_against_the_urban_scope(self):
        """Errs AGAINST the finding, as Phase 2 established."""
        r = target_vs_realised(0.40)
        rows = {x["archetype"]: x for x in r["rows"]}
        assert rows["urban"]["servicing_h_per_ha"] == pytest.approx(
            census("urban_upper")["hours_per_hectare_year"]
        )

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            target_vs_realised(-0.1)


class TestAmenitySensitivity:

    def test_the_sign_is_robust_and_the_magnitude_is_not(self):
        """
        The amenity weight is worth 41× in the stewardship census. Here it is
        worth about 2.5× — enough that a single quoted figure would overstate
        how well determined this is, and not enough to reverse the finding.
        """
        r = amenity_sensitivity(0.40)
        assert r["sign_robust"] is True
        assert len(r["rows"]) == 3
        assert r["spread_factor"] > 1.0
        lo, hi = r["ratio_span"]
        assert lo > 1.0 and hi > lo

    def test_servicing_does_not_move_with_the_stewardship_scope(self):
        r = amenity_sensitivity(0.40)
        assert r["servicing_h_per_ha"] == pytest.approx(
            census("urban_upper")["hours_per_hectare_year"]
        )


class TestConservationCredit:

    def test_the_credit_and_the_owed_flow_have_opposite_signs(self):
        r = conservation_credit_check()
        assert r["is_credit"] is True
        assert r["conservation_coefficient"] < 0.0
        assert r["classes_owing_stewardship"]
        for c in r["classes_owing_stewardship"]:
            assert c["owed_h_per_ha"] > 0.0
        lo, hi = r["owed_h_per_ha_range"]
        assert 0.0 < lo <= hi

    @pytest.mark.parametrize("epsilon", ARC)
    def test_the_credit_is_clipped_by_the_fee_floor_and_never_pays_out(self, epsilon):
        """
        THE FINDING, and it is the fee floor rather than the coefficient: the
        credit is notionally large and negative, and `ground_use_fee` clamps at
        `guf_floor`, so conservation land realises exactly zero. Neither side of
        the notional exchange happens.
        """
        r = conservation_credit_check(epsilon)
        assert r["notional_h_per_ha"] < 0.0
        assert r["realised_h_per_ha"] == pytest.approx(0.0)
        assert r["credit_is_clipped"] is True

    def test_conservation_land_pays_less_than_it_owes(self):
        r = conservation_credit_check()
        assert r["realised_h_per_ha"] < min(r["owed_h_per_ha_range"])

    def test_it_is_reported_as_a_decision_not_a_defect(self):
        assert "charter decision" in conservation_credit_check()["verdict"]

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            conservation_credit_check(1.5)


# ---------------------------------------------------------------------------
# The report, and the guardrail
# ---------------------------------------------------------------------------

class TestMagnitudeReport:

    @pytest.mark.parametrize("epsilon", ARC)
    def test_report_runs_across_the_arc(self, epsilon):
        rep = magnitude_report(epsilon)
        assert rep["epsilon"] == epsilon
        assert rep["by_class"]
        assert rep["two_part_rates"]["u_area_h_per_ha_yr"] > 0.0
        assert rep["subdivision"]["invariant"] is True

    def test_report_states_what_it_cannot_settle(self):
        assert "RATIOS" in magnitude_report()["what_this_does_not_settle"]


# ---------------------------------------------------------------------------
# The term-basis audit (memo §10 step 1)
# ---------------------------------------------------------------------------

class TestTermBasisRegistry:

    def test_every_term_of_the_master_equation_is_declared(self):
        """A term with no declared basis is a term nobody has audited."""
        assert set(TERM_BASIS) == {"A", "L", "U", "D", "Z", "E", "I", "Psi", "Omega"}

    def test_every_basis_is_in_the_closed_vocabulary(self):
        for term, entry in TERM_BASIS.items():
            assert entry["basis"] in FEE_BASES, term
            assert entry["spec_direction"] in (
                "aligned", "inverted", "neutral",
            ), term
            assert entry["why"].strip(), term
            assert entry["quantity"].strip(), term

    def test_no_vocabulary_entry_goes_unused(self):
        """
        A permission nobody exercises is a permission nobody reviews. `benefit`
        is deliberately absent from FEE_BASES: it was the expected label for I
        and the audit refuted it (§12 of the memo).
        """
        assert basis_table()["bases_unused"] == []
        assert "benefit" not in FEE_BASES

    def test_I_is_stock_not_benefit_and_is_sign_aligned(self):
        """
        THE AUDIT'S OWN FINDING, pinned. Scoring the terms is what forced
        cost_teh/(design_life × beneficiary_count) to be read as an annuity.
        """
        assert TERM_BASIS["I"]["basis"] == "cost_stock"
        assert TERM_BASIS["I"]["spec_direction"] == "aligned"

    def test_U_and_I_are_the_flow_and_stock_of_one_partition(self):
        assert TERM_BASIS["U"]["basis"] == "cost_flow"
        assert TERM_BASIS["I"]["basis"] == "cost_stock"

    def test_psi_has_no_surviving_basis(self):
        assert TERM_BASIS["Psi"]["basis"] == "unresolved"

    def test_four_terms_carry_their_own_epsilon_response(self):
        """The double application, as a property of the declaration."""
        assert set(basis_table()["carries_own_epsilon_response"]) == {
            "U", "E", "I", "Psi"
        }


class TestPsiDoubleApplication:

    def test_alpha_and_psi_give_the_same_reason_and_compound(self):
        r = psi_double_application(0.99)
        assert r["alpha"] < 1.0 and r["psi"] < 1.0
        assert r["combined"] == pytest.approx(r["alpha"] * r["psi"])
        assert r["combined"] < 0.01          # two multipliers, one mechanism

    def test_they_point_opposite_ways_at_subsistence(self):
        """
        THE CATEGORY ERROR: α rises at ε=0 (unautomated administration costs
        more human hours) while Ψ collapses (institutional capacity is minimal).
        A cost and a collection capability, silently multiplied.
        """
        r = psi_double_application()
        assert r["alpha_at_zero"] > 1.0
        assert r["psi_at_zero"] < 1.0
        assert r["opposite_signs_at_zero"] is True

    def test_both_are_unity_at_the_calibration_reference(self):
        r = psi_double_application(0.40)
        assert r["alpha"] == pytest.approx(1.0)
        assert r["psi"] == pytest.approx(1.0)

    def test_out_of_range_epsilon_raises(self):
        with pytest.raises(ValueError):
            psi_double_application(1.5)


class TestPsiPolicies:

    def test_retired_is_the_default(self):
        """
        FLIPPED 2026-08-20 (author decision). Ψ ≡ 1 is now the shipped
        behaviour; `bell` remains reachable and tested, because retiring a
        curve is not the same as deleting the ability to reproduce it.
        """
        parcels = make_urban_collective(500)
        for e in ARC:
            assert (
                compute_collective_guf(parcels, e, psi_policy="retired")["guf_gross_revenue"]
                == compute_collective_guf(parcels, e)["guf_gross_revenue"]
            )

    def test_bell_remains_reachable_and_differs_away_from_the_reference(self):
        parcels = make_urban_collective(500)
        bell = compute_collective_guf(parcels, 0.99, psi_policy="bell")["guf_gross_revenue"]
        default = compute_collective_guf(parcels, 0.99)["guf_gross_revenue"]
        assert bell < default
        assert bell == pytest.approx(default * epsilon_scaling(0.99))

    @pytest.mark.parametrize("epsilon", ARC)
    def test_bell_applies_psi_to_all_three_components(self, epsilon):
        psi = epsilon_scaling(epsilon)
        assert psi_application(epsilon, "bell") == (psi, psi, psi)

    @pytest.mark.parametrize("epsilon", ARC)
    def test_flow_only_spares_the_stock_and_damage_legs(self, epsilon):
        b, e_, i = psi_application(epsilon, "flow_only")
        assert b == epsilon_scaling(epsilon)
        assert (e_, i) == (1.0, 1.0)

    @pytest.mark.parametrize("epsilon", ARC)
    def test_retired_is_unity_everywhere(self, epsilon):
        assert psi_application(epsilon, "retired") == (1.0, 1.0, 1.0)

    def test_unknown_policy_raises(self):
        with pytest.raises(ValueError):
            psi_application(0.40, "nonsense")
        with pytest.raises(ValueError):
            ground_use_fee(
                area_slu=1.0, location_value=0.5,
                use_category="residential_primary", epsilon=0.40,
                psi_policy="nonsense",
            )

    def test_all_policies_agree_at_the_calibration_reference(self):
        """Ψ(0.40) = 1 exactly, so bell and retired coincide there by construction."""
        parcels = make_urban_collective(500)
        vals = {
            p: compute_collective_guf(parcels, 0.40, psi_policy=p)["guf_gross_revenue"]
            for p in PSI_POLICIES
        }
        assert vals["bell"] == pytest.approx(vals["retired"])

    def test_retiring_the_bell_gives_a_monotone_falling_fee(self):
        """
        The SHAPE claim, not a level: α(ε) alone is monotone, so a fee whose
        only automation response is labour content must fall monotonically.
        The bell does not, which is the artifact.
        """
        rows = {r["psi_policy"]: r for r in psi_policy_comparison()["rows"]}
        assert rows["retired"]["monotone_falling"] is True
        assert rows["bell"]["monotone_falling"] is False

    def test_flow_only_equals_bell_because_the_stock_leg_is_inert(self):
        """
        HONEST STATE, pinned so it fails loudly when the asset inventory lands:
        no shipped path supplies ecosystem_services or infrastructure_assets, so
        E = I = 0 and sparing them changes nothing. When that stops being true
        this test should fail and be replaced, not deleted.
        """
        assert psi_policy_comparison()["flow_only_equals_bell"] is True
        fee = ground_use_fee(
            area_slu=1.0, location_value=0.5,
            use_category="residential_primary", epsilon=0.40,
        )
        assert fee["eco_surcharge"] == 0.0
        assert fee["infra_premium"] == 0.0

    def test_the_policy_travels_in_the_result(self):
        fee = ground_use_fee(
            area_slu=1.0, location_value=0.5,
            use_category="residential_primary", epsilon=0.80,
            psi_policy="retired",
        )
        assert fee["psi_policy"] == "retired"
        assert fee["psi_applied"] == (1.0, 1.0, 1.0)


class TestMagnitudeChangesNothing:
    """REPORTING ONLY. This module measures the ×100; it does not retire it."""

    def test_scale_factor_is_untouched(self):
        assert GUF_USE_SCALE_FACTOR == 100.0

    def test_use_categories_are_untouched(self):
        assert USE_CATEGORIES["residential_primary"] == 10.0
        assert USE_CATEGORIES["industrial_heavy"] == 37.5
        assert USE_CATEGORIES["conservation"] == -6.0

    def test_the_phase_2_census_is_unmoved(self):
        """
        Option 1 adds a second half to the TARGET; it must not disturb the
        servicing census itself, which several other findings rest on.
        """
        c = census("core")
        assert c["workers"] == pytest.approx(909_600.0)
        assert c["hours_per_hectare_year"] == pytest.approx(45.9178, rel=1e-4)
