"""
Tests for hours_eoh.land.guf — Ground Use Fee calculation framework.

Covers all functions across the automation arc (ε=0, 0.40, 0.90, 0.99).
The worked example from NLSA §10 is used as a regression anchor.
"""

import math
import pytest

from hours_eoh.land.guf import (
    epsilon_scaling,
    labor_content_scaling,
    location_value_index,
    use_category_coefficient,
    demand_pressure_modifier,
    ecosystem_service_kappa,
    ecosystem_displacement_surcharge,
    infrastructure_proximity_premium,
    base_fee,
    ground_use_fee,
    review_cycle_cap,
    income_linked_subsidy,
    min_income_for_access,
    soil_health_credit,
    guf_trust_inflow,
    rebuilding_surcharge,
    ground_use_fee_writedown,
    eoh_accumulation_warning,
    USE_CATEGORIES,
)
from hours_eoh.data import (
    GUF_PSI_FLOOR, GUF_DEMAND_D_MAX,
    GUF_WRITEDOWN_AMORTIZATION_YEARS, GUF_EOH_ACCUMULATION_THRESHOLD,
    GUF_AFFORDABILITY_THRESHOLD, GUF_SUBSIDY_FLOOR_RATE,
)


# ===========================================================================
# epsilon_scaling (Ψ)
# ===========================================================================

class TestEpsilonScaling:
    def test_floor_at_zero(self):
        # Ψ(0) = GUF_PSI_NORM × 0 × 1 + GUF_PSI_FLOOR = GUF_PSI_FLOOR
        assert epsilon_scaling(0.0) == pytest.approx(GUF_PSI_FLOOR)

    def test_near_one_at_calibration(self):
        # Ψ(0.40) ≈ 1.04; the calibration reference point
        psi = epsilon_scaling(0.40)
        assert 1.0 <= psi <= 1.10

    def test_low_at_post_scarcity(self):
        # Boundary: Ψ(0.99) < 0.05 × Ψ(0.40)
        psi_mid  = epsilon_scaling(0.40)
        psi_high = epsilon_scaling(0.99)
        assert psi_high < 0.05 * psi_mid

    def test_low_at_subsistence(self):
        # Boundary: Ψ(0) < 0.05 × Ψ(0.40)
        psi_mid = epsilon_scaling(0.40)
        psi_low = epsilon_scaling(0.0)
        assert psi_low < 0.05 * psi_mid

    def test_bell_shape_peak_in_mid_range(self):
        # Peak should occur between ε=0.20 and ε=0.60
        candidates = [epsilon_scaling(e / 100) for e in range(1, 99)]
        peak_idx   = candidates.index(max(candidates))
        peak_eps   = (peak_idx + 1) / 100
        assert 0.20 <= peak_eps <= 0.60

    def test_non_negative_everywhere(self):
        for eps in [0.0, 0.10, 0.40, 0.70, 0.99]:
            assert epsilon_scaling(eps) >= 0.0


# ===========================================================================
# labor_content_scaling (α)
# ===========================================================================

class TestLaborContentScaling:
    def test_unity_at_calibration(self):
        assert labor_content_scaling(0.40) == pytest.approx(1.0, rel=1e-9)

    def test_above_one_at_subsistence(self):
        # At ε=0 labor content is higher than at ε=0.40
        assert labor_content_scaling(0.0) > 1.0

    def test_below_one_at_high_epsilon(self):
        assert labor_content_scaling(0.90) < 1.0

    def test_monotone_decreasing(self):
        epsilons = [0.0, 0.10, 0.40, 0.60, 0.90, 0.99]
        values   = [labor_content_scaling(e) for e in epsilons]
        assert all(values[i] >= values[i + 1] for i in range(len(values) - 1))

    def test_floor_prevents_zero(self):
        # At ε=0.99, still positive (irreducible human judgment)
        assert labor_content_scaling(0.99) > 0.0


# ===========================================================================
# location_value_index
# ===========================================================================

class TestLocationValueIndex:
    def test_default_weights_sum_to_one(self):
        from hours_eoh.data import (
            GUF_LVI_W_CENTRALITY, GUF_LVI_W_TRANSIT,
            GUF_LVI_W_SERVICES, GUF_LVI_W_NATURAL_AMENITY,
        )
        total = GUF_LVI_W_CENTRALITY + GUF_LVI_W_TRANSIT + GUF_LVI_W_SERVICES + GUF_LVI_W_NATURAL_AMENITY
        assert total == pytest.approx(1.0)

    def test_uniform_sub_indices(self):
        # All sub-indices = 0.5 → L = 0.5 regardless of weights
        result = location_value_index(0.5, 0.5, 0.5, 0.5)
        assert result == pytest.approx(0.5)

    def test_worked_example(self):
        # NLSA §10: L = 0.35×0.55 + 0.30×0.71 + 0.20×0.68 + 0.15×0.58 = 0.629
        result = location_value_index(0.55, 0.71, 0.68, 0.58)
        assert result == pytest.approx(0.629, abs=0.001)

    def test_custom_weights(self):
        weights = {"centrality": 0.25, "transit": 0.25, "services": 0.25, "natural_amenity": 0.25}
        result  = location_value_index(1.0, 0.0, 0.0, 0.0, weights=weights)
        assert result == pytest.approx(0.25)

    def test_zero_inputs(self):
        assert location_value_index(0.0, 0.0, 0.0, 0.0) == pytest.approx(0.0)

    def test_full_inputs(self):
        assert location_value_index(1.0, 1.0, 1.0, 1.0) == pytest.approx(1.0)


# ===========================================================================
# use_category_coefficient
# ===========================================================================

class TestUseCategoryCoefficient:
    def test_reference_at_calibration(self):
        # At ε=0.40, α=1.0, so U = U_ref exactly
        from hours_eoh.data import GUF_USE_RESIDENTIAL_PRIMARY
        result = use_category_coefficient("residential_primary", 0.40)
        assert result == pytest.approx(GUF_USE_RESIDENTIAL_PRIMARY, rel=1e-9)

    def test_lower_at_high_epsilon(self):
        # Labor content drops → U drops
        u_mid  = use_category_coefficient("residential_primary", 0.40)
        u_high = use_category_coefficient("residential_primary", 0.90)
        assert u_high < u_mid

    def test_negative_conservation(self):
        # Conservation overlay is a credit (negative coefficient)
        u = use_category_coefficient("conservation", 0.40)
        assert u < 0.0

    def test_custom_u_ref(self):
        # Mixed-use blend: caller passes pre-computed U_ref
        result = use_category_coefficient("residential_primary", 0.40, custom_u_ref=0.15)
        assert result == pytest.approx(0.15, rel=1e-9)

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown use category"):
            use_category_coefficient("something_invalid", 0.40)

    def test_all_known_categories_valid(self):
        for cat in USE_CATEGORIES:
            result = use_category_coefficient(cat, 0.40)
            assert isinstance(result, float)


# ===========================================================================
# demand_pressure_modifier
# ===========================================================================

class TestDemandPressureModifier:
    def test_zero_ratio_returns_one(self):
        assert demand_pressure_modifier(0.0) == pytest.approx(1.0)

    def test_negative_ratio_returns_one(self):
        assert demand_pressure_modifier(-0.5) == pytest.approx(1.0)

    def test_positive_ratio_above_one(self):
        result = demand_pressure_modifier(0.15)
        assert result > 1.0

    def test_worked_example(self):
        # NLSA §10: D = 1 + 0.15 × ln(1 + 0.15) ≈ 1.021
        result = demand_pressure_modifier(0.15, residential=True)
        assert result == pytest.approx(1.021, abs=0.001)

    def test_constitutional_ceiling(self):
        # Very high demand ratio must be capped at 1.80
        result = demand_pressure_modifier(1000.0, residential=True)
        assert result == pytest.approx(GUF_DEMAND_D_MAX)

    def test_commercial_higher_sensitivity(self):
        # Commercial η=0.25 > residential η=0.15 → higher D for same Δ
        d_res  = demand_pressure_modifier(0.50, residential=True)
        d_comm = demand_pressure_modifier(0.50, residential=False)
        assert d_comm > d_res

    def test_custom_eta(self):
        result = demand_pressure_modifier(0.15, eta=0.20)
        expected = 1.0 + 0.20 * math.log(1.15)
        assert result == pytest.approx(expected)


# ===========================================================================
# ecosystem_service_kappa
# ===========================================================================

class TestEcosystemServiceKappa:
    def test_reference_point_exact(self):
        # At ε=0.40, κ(ε) must equal kappa_ref exactly
        kappa_ref = 1.65  # water filtration reference
        beta      = 0.8
        result    = ecosystem_service_kappa(kappa_ref, beta, 0.40)
        assert result == pytest.approx(kappa_ref, rel=1e-9)

    def test_monotone_decreasing(self):
        # κ decreases as ε increases (more automation → cheaper replacement)
        kappa_ref = 2.75
        beta      = 0.9
        epsilons  = [0.0, 0.20, 0.40, 0.60, 0.90, 0.99]
        values    = [ecosystem_service_kappa(kappa_ref, beta, e) for e in epsilons]
        assert all(values[i] >= values[i + 1] for i in range(len(values) - 1))

    def test_floor_at_high_epsilon(self):
        # At ε=0.99, κ ≈ kappa_floor = 0.10 × kappa_ref (not zero)
        kappa_ref    = 1.0
        beta         = 0.8
        floor_frac   = 0.10
        result       = ecosystem_service_kappa(kappa_ref, beta, 0.99, floor_frac)
        kappa_floor  = kappa_ref * floor_frac
        assert result >= kappa_floor * 0.95  # near floor

    def test_higher_beta_faster_decline(self):
        # Higher β → κ declines faster with ε
        kappa_ref  = 1.0
        val_lo_b   = ecosystem_service_kappa(kappa_ref, beta=0.6, epsilon=0.80)
        val_hi_b   = ecosystem_service_kappa(kappa_ref, beta=1.2, epsilon=0.80)
        assert val_hi_b < val_lo_b


# ===========================================================================
# ecosystem_displacement_surcharge
# ===========================================================================

class TestEcosystemDisplacementSurcharge:
    def _sample_services(self):
        return [
            {"label": "water",   "volume": 0.4,  "kappa_ref": 1.2,  "beta": 0.8, "retained": 0.30},
            {"label": "carbon",  "volume": 0.15, "kappa_ref": 2.5,  "beta": 0.9, "retained": 0.25},
            {"label": "thermal", "volume": 12.0, "kappa_ref": 0.03, "beta": 0.8, "retained": 0.20},
        ]

    def test_worked_example_at_calibration(self):
        # NLSA §10: E = 0.336 + 0.281 + 0.288 = 0.905 TEH/year at ε=0.40
        # Note: at ε=0.40 κ = kappa_ref exactly
        result = ecosystem_displacement_surcharge(self._sample_services(), 0.40)
        assert result["surcharge_total"] == pytest.approx(0.905, abs=0.005)

    def test_fully_retained_zero_contribution(self):
        services = [{"label": "water", "volume": 10.0, "kappa_ref": 2.0, "beta": 0.8, "retained": 1.0}]
        result   = ecosystem_displacement_surcharge(services, 0.40)
        assert result["surcharge_total"] == pytest.approx(0.0)

    def test_fully_displaced_full_contribution(self):
        services = [{"label": "water", "volume": 1.0, "kappa_ref": 2.0, "beta": 0.8, "retained": 0.0}]
        result   = ecosystem_displacement_surcharge(services, 0.40)
        assert result["surcharge_total"] == pytest.approx(2.0, rel=1e-6)  # V × κ_ref × 1

    def test_surcharge_lower_at_high_epsilon(self):
        # At high ε, κ is lower → surcharge lower
        services = self._sample_services()
        e_mid    = ecosystem_displacement_surcharge(services, 0.40)["surcharge_total"]
        e_high   = ecosystem_displacement_surcharge(services, 0.90)["surcharge_total"]
        assert e_high < e_mid

    def test_empty_services_zero(self):
        result = ecosystem_displacement_surcharge([], 0.40)
        assert result["surcharge_total"] == pytest.approx(0.0)

    def test_by_service_breakdown(self):
        services = self._sample_services()
        result   = ecosystem_displacement_surcharge(services, 0.40)
        assert len(result["by_service"]) == 3
        total_check = sum(s["contribution_teh"] for s in result["by_service"])
        assert total_check == pytest.approx(result["surcharge_total"])


# ===========================================================================
# infrastructure_proximity_premium
# ===========================================================================

class TestInfrastructureProximityPremium:
    def _sample_assets(self):
        return [
            {
                "cost_teh": 45_000, "design_life": 50, "beneficiary_count": 1800,
                "distance_km": 0.8, "asset_type": "transit", "chi": 1.0,
            },
            {
                "cost_teh": 8_000, "design_life": 75, "beneficiary_count": 500,
                "distance_km": 0.4, "asset_type": "public_space", "chi": 1.0,
            },
        ]

    def test_worked_example(self):
        # NLSA §10: I = 0.335 + 0.155 = 0.490 TEH/year
        result = infrastructure_proximity_premium(self._sample_assets(), 0.40)
        assert result["premium_total"] == pytest.approx(0.490, abs=0.005)

    def test_distance_decay(self):
        # Doubling distance reduces the premium
        near  = [{"cost_teh": 10000, "design_life": 50, "beneficiary_count": 100,
                   "distance_km": 0.5, "asset_type": "transit", "chi": 1.0}]
        far   = [{"cost_teh": 10000, "design_life": 50, "beneficiary_count": 100,
                   "distance_km": 1.0, "asset_type": "transit", "chi": 1.0}]
        p_near = infrastructure_proximity_premium(near, 0.40)["premium_total"]
        p_far  = infrastructure_proximity_premium(far,  0.40)["premium_total"]
        assert p_far < p_near

    def test_external_collective_discount(self):
        # chi < 1 reduces the premium proportionally
        full = [{"cost_teh": 10000, "design_life": 50, "beneficiary_count": 100,
                  "distance_km": 0.5, "asset_type": "transit", "chi": 1.0}]
        ext  = [{"cost_teh": 10000, "design_life": 50, "beneficiary_count": 100,
                  "distance_km": 0.5, "asset_type": "transit", "chi": 0.3}]
        p_full = infrastructure_proximity_premium(full, 0.40)["premium_total"]
        p_ext  = infrastructure_proximity_premium(ext,  0.40)["premium_total"]
        assert p_ext == pytest.approx(p_full * 0.3, rel=1e-6)

    def test_empty_assets_zero(self):
        result = infrastructure_proximity_premium([], 0.40)
        assert result["premium_total"] == pytest.approx(0.0)

    def test_premium_not_epsilon_dependent_for_legacy_assets(self):
        # Cost_teh is fixed at construction ε_k; current ε doesn't change it
        assets = self._sample_assets()
        p_low  = infrastructure_proximity_premium(assets, 0.10)["premium_total"]
        p_high = infrastructure_proximity_premium(assets, 0.80)["premium_total"]
        assert p_low == pytest.approx(p_high)


# ===========================================================================
# ground_use_fee (master equation)
# ===========================================================================

class TestGroundUseFee:
    def _nlsa_example(self, epsilon=0.40, psi_policy="retired"):
        """NLSA §10 residential example (partial — no previous cycle cap).

        NOTE this is the one fixture in the suite where E and I are BOTH
        non-zero, so it is also the only place the three Ψ policies can be told
        apart from one another rather than just from `bell`.
        """
        eco_services = [
            {"label": "water",   "volume": 0.4,  "kappa_ref": 1.2,  "beta": 0.8, "retained": 0.30},
            {"label": "carbon",  "volume": 0.15, "kappa_ref": 2.5,  "beta": 0.9, "retained": 0.25},
            {"label": "thermal", "volume": 12.0, "kappa_ref": 0.03, "beta": 0.8, "retained": 0.20},
        ]
        infra_assets = [
            {"cost_teh": 45_000, "design_life": 50, "beneficiary_count": 1800,
             "distance_km": 0.8, "asset_type": "transit", "chi": 1.0},
            {"cost_teh":  8_000, "design_life": 75, "beneficiary_count":  500,
             "distance_km": 0.4, "asset_type": "public_space", "chi": 1.0},
        ]
        return ground_use_fee(
            psi_policy            = psi_policy,
            area_slu              = 3.5,
            location_value        = 0.629,
            use_category          = "residential_primary",
            epsilon               = epsilon,
            ecosystem_services    = eco_services,
            infrastructure_assets = infra_assets,
            demand_supply_ratio   = 0.15,
            zone_adj              = 1.0,
            occupancy_fraction    = 1.0,
        )

    def test_worked_example_formula(self):
        # NLSA §10 components: base_fee scales with GUF_USE_RESIDENTIAL_PRIMARY (10.0 TEH/SLU/yr);
        # base = 3.5 × 0.629 × 10.0 × D ≈ 22.5. Eco and infra use caller-supplied kappa_ref
        # values so are unchanged: eco=0.905, infra=0.490.
        # Ψ(0.40) ≈ 1.062 → GUF ≈ 1.062 × (22.5 + 0.905 + 0.490) ≈ 25.4.
        result = self._nlsa_example(0.40)
        assert result["base_fee"]      == pytest.approx(22.5, abs=0.05)
        assert result["eco_surcharge"] == pytest.approx(0.905, abs=0.005)
        assert result["infra_premium"] == pytest.approx(0.490, abs=0.005)
        # Verify master equation assembly
        expected = result["psi"] * (result["base_fee"] + 0.905 + 0.490)
        assert result["guf_formula"] == pytest.approx(expected, rel=1e-4)

    def test_components_sum_correctly(self):
        result = self._nlsa_example(0.40)
        psi    = result["psi"]
        reconstructed = psi * (result["base_fee"] + result["eco_surcharge"] + result["infra_premium"])
        assert result["guf_formula"] == pytest.approx(reconstructed, rel=1e-9)

    def test_floor_applied_when_below_zero(self):
        # Conservation parcel with high overlay credit could go negative
        result = ground_use_fee(
            area_slu       = 10.0,
            location_value = 0.1,
            use_category   = "conservation",
            epsilon        = 0.40,
            guf_floor      = 0.0,
        )
        assert result["guf_applied"] >= 0.0
        assert result["floor_applied"] == (result["guf_formula"] < 0.0)

    def test_guf_lower_at_high_epsilon(self):
        mid  = self._nlsa_example(0.40)["guf_formula"]
        high = self._nlsa_example(0.90)["guf_formula"]
        assert high < mid

    def test_guf_lower_at_zero_epsilon_under_the_bell_policy(self):
        """
        The bell's low-ε behaviour, still pinned — but now explicitly AS the
        `bell` policy rather than as the fee's only shape. Ψ(0) = 0.02.
        """
        zero = self._nlsa_example(0.0, psi_policy="bell")["guf_formula"]
        mid  = self._nlsa_example(0.40, psi_policy="bell")["guf_formula"]
        assert zero < mid * 0.10

    def test_guf_is_HIGHER_at_zero_epsilon_under_the_default(self):
        """
        THE FLIP, 2026-08-20. Under `retired` the fee's only automation response
        is α(ε) = labor_content_scaling, which RISES at subsistence (1.4695)
        because unautomated land administration takes more human hours. The old
        assertion was pinning Ψ's ε=0 floor, and that floor was a claim about
        institutional COLLECTION CAPACITY wearing a cost multiplier — see
        handoffs/guf_redefinition.md §17.
        """
        zero = self._nlsa_example(0.0)["guf_formula"]
        mid  = self._nlsa_example(0.40)["guf_formula"]
        assert zero > mid

    def test_occupancy_fraction_scales(self):
        full = ground_use_fee(3.5, 0.629, "residential_primary", 0.40,
                              occupancy_fraction=1.0)["guf_formula"]
        half = ground_use_fee(3.5, 0.629, "residential_primary", 0.40,
                              occupancy_fraction=0.5)["guf_formula"]
        assert half == pytest.approx(full * 0.5, rel=1e-6)

    def test_boundary_verification_subsistence_under_the_bell_policy(self):
        # NLSA §4.4: GUF(ε=0) < 0.05 × GUF(ε=0.40) for all parcels.
        # RETAINED AS A PROPERTY OF `bell`, which is what §4.4 was describing.
        g0   = self._nlsa_example(0.00, psi_policy="bell")["guf_formula"]
        g040 = self._nlsa_example(0.40, psi_policy="bell")["guf_formula"]
        assert g0 < 0.05 * g040

    def test_boundary_verification_post_scarcity_under_the_bell_policy(self):
        # NLSA §4.4: GUF(ε=0.99) < 0.05 × GUF(ε=0.40) for all parcels.
        g099 = self._nlsa_example(0.99, psi_policy="bell")["guf_formula"]
        g040 = self._nlsa_example(0.40, psi_policy="bell")["guf_formula"]
        assert g099 < 0.05 * g040

    def test_the_nlsa_4_4_boundaries_DO_NOT_hold_under_the_default(self):
        """
        Recorded as a consequence, not smuggled. NLSA §4.4's two boundary
        conditions were properties of Ψ's bell, and retiring it retires them.
        At ε=0.99 the fee is ~12% of its ε=0.40 value, not under 5% — which is
        α(0.99) = 0.1051 doing the work alone, once the duplicate discount is
        removed.
        """
        g040 = self._nlsa_example(0.40)["guf_formula"]
        g099 = self._nlsa_example(0.99)["guf_formula"]
        assert g099 > 0.05 * g040
        assert g099 < 0.25 * g040

    def test_all_three_policies_agree_at_the_calibration_reference(self):
        """Ψ(0.40) = 1 exactly, so the reference point is policy-invariant."""
        vals = [
            self._nlsa_example(0.40, psi_policy=p)["guf_formula"]
            for p in ("bell", "flow_only", "retired")
        ]
        assert vals[0] == pytest.approx(vals[1])
        assert vals[1] == pytest.approx(vals[2])

    def test_flow_only_differs_from_bell_where_E_and_I_are_non_zero(self):
        """
        The one fixture that can show it. Elsewhere in the suite E = I = 0 and
        `flow_only` is indistinguishable from `bell`.
        """
        bell = self._nlsa_example(0.80, psi_policy="bell")["guf_formula"]
        flow = self._nlsa_example(0.80, psi_policy="flow_only")["guf_formula"]
        assert flow > bell


# ===========================================================================
# review_cycle_cap
# ===========================================================================

class TestReviewCycleCap:
    def test_cap_does_not_bind_when_below_ceiling(self):
        result = review_cycle_cap(guf_formula=1.5, guf_previous=1.5)
        assert result["cap_binds"] is False
        assert result["guf_applied"] == pytest.approx(1.5)
        assert result["deferred"] == pytest.approx(0.0)

    def test_cap_binds_when_above_ceiling(self):
        # Previous=1.52, cap=1.672; formula=1.685 > 1.672 → binds
        result = review_cycle_cap(guf_formula=1.685, guf_previous=1.52)
        assert result["cap_binds"] is True
        assert result["guf_applied"] == pytest.approx(1.52 * 1.10, rel=1e-6)
        assert result["deferred"] == pytest.approx(1.685 - result["guf_applied"], abs=1e-6)

    def test_worked_example(self):
        # NLSA §10: previous=1.52, formula=1.685, cap=1.672, applied=1.672
        result = review_cycle_cap(guf_formula=1.685, guf_previous=1.52)
        assert result["guf_applied"] == pytest.approx(1.672, abs=0.001)

    def test_custom_phi(self):
        result = review_cycle_cap(guf_formula=2.0, guf_previous=1.0, phi=0.05)
        assert result["cap_ceiling"] == pytest.approx(1.05)
        assert result["cap_binds"] is True

    def test_decrease_never_blocked(self):
        # Cap only blocks increases; decreases go through
        result = review_cycle_cap(guf_formula=1.0, guf_previous=2.0)
        assert result["cap_binds"] is False
        assert result["guf_applied"] == pytest.approx(1.0)


# ===========================================================================
# income_linked_subsidy
# ===========================================================================

class TestIncomeLinkedSubsidy:
    def test_above_median_full_rate(self):
        result = income_linked_subsidy(2.0, steward_income=4000, median_income=3500)
        assert result["sigma"] == pytest.approx(1.0)
        assert result["subsidized"] is False
        assert result["subsidy_amount"] == pytest.approx(0.0)

    def test_below_lower_threshold_floor_rate(self):
        # Income < 40% × median → sigma = 0.25
        result = income_linked_subsidy(2.0, steward_income=1000, median_income=3500)
        assert result["sigma"] == pytest.approx(0.25)
        assert result["guf_effective"] == pytest.approx(0.50)
        assert result["subsidized"] is True

    def test_worked_example(self):
        # NLSA §10: Y=3200, Ŷ=3500, 0.4Ŷ=1400
        # σ = 0.25 + 0.75 × [(3200-1400)/(3500-1400)] = 0.25 + 0.75×0.857 = 0.893
        # GUF_effective = 1.672 × 0.893 = 1.493
        result = income_linked_subsidy(1.672, steward_income=3200, median_income=3500)
        assert result["sigma"] == pytest.approx(0.893, abs=0.002)
        assert result["guf_effective"] == pytest.approx(1.493, abs=0.005)

    def test_linear_interpolation_midpoint(self):
        # At the exact midpoint between lower threshold and median
        # lower = 0.40 × 1000 = 400; midpoint = (400+1000)/2 = 700
        result = income_linked_subsidy(1.0, steward_income=700, median_income=1000)
        # σ = 0.25 + 0.75 × [(700-400)/600] = 0.25 + 0.75×0.5 = 0.625
        assert result["sigma"] == pytest.approx(0.625, rel=1e-6)

    def test_zero_median_income_no_subsidy(self):
        # Edge case: no median defined → no subsidy
        result = income_linked_subsidy(1.0, steward_income=0, median_income=0)
        assert result["sigma"] == pytest.approx(1.0)

    def test_subsidy_amount_identity(self):
        result = income_linked_subsidy(2.0, steward_income=1000, median_income=3500)
        assert result["guf_applied"] == pytest.approx(
            result["guf_effective"] + result["subsidy_amount"], rel=1e-9
        )


# ===========================================================================
# min_income_for_access
# ===========================================================================

class TestGufAccessibility:

    EXPECTED_KEYS = {
        "guf_applied", "median_income", "affordability_threshold",
        "min_income_no_subsidy", "min_income_full_subsidy",
        "affordability_ratio_at_median", "accessible_at_median",
        "accessible_at_guarantee", "status", "subsidy_absorption",
    }

    def test_result_keys_present(self):
        result = min_income_for_access(200.0, 1000.0)
        assert self.EXPECTED_KEYS == set(result.keys())

    def test_status_accessible(self):
        # guf=200, median=1000, threshold=0.25 → ratio=0.20 ≤ 0.25 → ACCESSIBLE
        result = min_income_for_access(200.0, 1000.0)
        assert result["status"] == "ACCESSIBLE"
        assert result["accessible_at_median"] is True

    def test_status_subsidised_accessible(self):
        # guf=400, median=1000, threshold=0.25 → ratio=0.40 > 0.25, but 400 ≤ 1000 → SUBSIDISED
        result = min_income_for_access(400.0, 1000.0)
        assert result["status"] == "SUBSIDISED_ACCESSIBLE"
        assert result["accessible_at_median"] is False

    def test_status_inaccessible(self):
        # guf=1200, median=1000 → 1200 > median → INACCESSIBLE
        result = min_income_for_access(1200.0, 1000.0)
        assert result["status"] == "INACCESSIBLE"

    def test_min_income_no_subsidy_formula(self):
        guf, t = 300.0, 0.25
        result = min_income_for_access(guf, 1000.0, affordability_threshold=t)
        assert result["min_income_no_subsidy"] == pytest.approx(guf / t)

    def test_min_income_full_subsidy_formula(self):
        guf, t = 300.0, 0.25
        result = min_income_for_access(guf, 1000.0, affordability_threshold=t)
        assert result["min_income_full_subsidy"] == pytest.approx(
            GUF_SUBSIDY_FLOOR_RATE * guf / t
        )

    def test_affordability_ratio_at_median(self):
        result = min_income_for_access(250.0, 1000.0)
        assert result["affordability_ratio_at_median"] == pytest.approx(250.0 / 1000.0)

    def test_accessible_at_guarantee_true(self):
        # guf=200, full subsidy = 50 TEH, guarantee=400 → ratio=50/400=0.125 ≤ 0.25
        result = min_income_for_access(200.0, 1000.0, guarantee_income=400.0)
        assert result["accessible_at_guarantee"] is True

    def test_accessible_at_guarantee_false(self):
        # guf=1000, full subsidy=250, guarantee=400 → ratio=250/400=0.625 > 0.25
        result = min_income_for_access(1000.0, 2000.0, guarantee_income=400.0)
        assert result["accessible_at_guarantee"] is False

    def test_accessible_at_guarantee_none_when_not_provided(self):
        result = min_income_for_access(200.0, 1000.0)
        assert result["accessible_at_guarantee"] is None

    def test_subsidy_absorption_constant(self):
        # Trust always absorbs (1 − FLOOR_RATE) of GUF at minimum income
        result = min_income_for_access(200.0, 1000.0)
        assert result["subsidy_absorption"] == pytest.approx(1.0 - GUF_SUBSIDY_FLOOR_RATE)

    def test_boundary_exactly_at_threshold(self):
        # guf=250, median=1000, threshold=0.25 → ratio exactly 0.25 → ACCESSIBLE
        result = min_income_for_access(250.0, 1000.0)
        assert result["status"] == "ACCESSIBLE"
        assert result["accessible_at_median"] is True

    def test_zero_guf_always_accessible(self):
        result = min_income_for_access(0.0, 1000.0)
        assert result["status"] == "ACCESSIBLE"
        assert result["min_income_no_subsidy"] == pytest.approx(0.0)

    def test_invalid_guf_raises(self):
        with pytest.raises(ValueError):
            min_income_for_access(-10.0, 1000.0)

    def test_invalid_median_raises(self):
        with pytest.raises(ValueError):
            min_income_for_access(200.0, 0.0)

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            min_income_for_access(200.0, 1000.0, affordability_threshold=0.0)


# ===========================================================================
# soil_health_credit
# ===========================================================================

class TestSoilHealthCredit:
    def test_positive_delta_generates_credit(self):
        credit = soil_health_credit(area_slu=5.0, delta_shi=0.1)
        assert credit > 0.0

    def test_zero_delta_no_credit(self):
        assert soil_health_credit(5.0, 0.0) == pytest.approx(0.0)

    def test_negative_delta_no_credit(self):
        assert soil_health_credit(5.0, -0.1) == pytest.approx(0.0)

    def test_linear_in_area_and_shi(self):
        c1 = soil_health_credit(5.0, 0.1)
        c2 = soil_health_credit(10.0, 0.1)
        c3 = soil_health_credit(5.0, 0.2)
        assert c2 == pytest.approx(2.0 * c1, rel=1e-9)
        assert c3 == pytest.approx(2.0 * c1, rel=1e-9)

    def test_default_rate(self):
        # 0.05 TEH/SLU per SHI point
        assert soil_health_credit(4.0, 0.5) == pytest.approx(0.05 * 4.0 * 0.5)


# ===========================================================================
# guf_trust_inflow
# ===========================================================================

class TestGufTrustInflow:
    def test_no_subsidies(self):
        revenues = [1.5, 2.0, 0.8]
        result   = guf_trust_inflow(revenues)
        assert result["gross_revenue"] == pytest.approx(4.3)
        assert result["net_inflow"]    == pytest.approx(4.3)
        assert result["subsidies_absorbed"] == pytest.approx(0.0)
        assert result["circulatory"] is True

    def test_subsidies_reduce_net_inflow(self):
        revenues = [2.0, 2.0, 2.0]  # gross = 6.0
        result   = guf_trust_inflow(revenues, subsidies_absorbed=1.5)
        assert result["gross_revenue"] == pytest.approx(6.0)
        assert result["net_inflow"]    == pytest.approx(4.5)

    def test_parcel_count(self):
        revenues = [1.0, 1.0, 1.0, 1.0]
        result   = guf_trust_inflow(revenues)
        assert result["parcel_count"] == 4

    def test_empty_revenue_list(self):
        result = guf_trust_inflow([])
        assert result["gross_revenue"] == pytest.approx(0.0)
        assert result["net_inflow"]    == pytest.approx(0.0)
        assert result["parcel_count"]  == 0

    def test_subsidies_cannot_create_negative_inflow(self):
        # If subsidies > gross, net_inflow is floored at 0
        result = guf_trust_inflow([0.5], subsidies_absorbed=2.0)
        assert result["net_inflow"] >= 0.0

    def test_always_circulatory(self):
        result = guf_trust_inflow([1.0, 2.0])
        assert result["circulatory"] is True


# ===========================================================================
# rebuilding_surcharge (Eq. 28)
# ===========================================================================

class TestRebuildingSurcharge:
    def _lost_services(self):
        return [
            {"label": "biodiversity", "volume_lost": 5.0,  "kappa_ref": 0.350, "beta": 0.7},
            {"label": "water",        "volume_lost": 0.2,  "kappa_ref": 1.650, "beta": 0.8},
        ]

    def test_basic_calculation(self):
        # R_b = Σ[V_lost × κ(ε)] / Y_r
        result = rebuilding_surcharge(self._lost_services(), epsilon=0.40)
        expected_bio   = 5.0  * 0.350 / GUF_WRITEDOWN_AMORTIZATION_YEARS
        expected_water = 0.2  * 1.650 / GUF_WRITEDOWN_AMORTIZATION_YEARS
        assert result["surcharge_total"] == pytest.approx(expected_bio + expected_water, rel=1e-6)

    def test_kappa_at_calibration_equals_kappa_ref(self):
        # At ε=0.40, κ = kappa_ref → surcharge uses reference values directly
        services = [{"label": "water", "volume_lost": 1.0, "kappa_ref": 2.0, "beta": 0.8}]
        result   = rebuilding_surcharge(services, epsilon=0.40)
        assert result["surcharge_total"] == pytest.approx(2.0 / GUF_WRITEDOWN_AMORTIZATION_YEARS, rel=1e-9)

    def test_decreasing_with_epsilon(self):
        # Higher automation → cheaper replacement → lower surcharge
        svcs = self._lost_services()
        r_lo = rebuilding_surcharge(svcs, epsilon=0.0)["surcharge_total"]
        r_md = rebuilding_surcharge(svcs, epsilon=0.40)["surcharge_total"]
        r_hi = rebuilding_surcharge(svcs, epsilon=0.90)["surcharge_total"]
        assert r_lo > r_md > r_hi

    def test_longer_amortization_lowers_annual_cost(self):
        svcs  = self._lost_services()
        r_50  = rebuilding_surcharge(svcs, epsilon=0.40, amortization_years=50)["surcharge_total"]
        r_100 = rebuilding_surcharge(svcs, epsilon=0.40, amortization_years=100)["surcharge_total"]
        assert r_100 == pytest.approx(r_50 / 2.0, rel=1e-6)

    def test_zero_volume_lost_zero_surcharge(self):
        services = [{"label": "water", "volume_lost": 0.0, "kappa_ref": 2.0, "beta": 0.8}]
        result   = rebuilding_surcharge(services, epsilon=0.40)
        assert result["surcharge_total"] == pytest.approx(0.0)

    def test_empty_services_zero(self):
        result = rebuilding_surcharge([], epsilon=0.40)
        assert result["surcharge_total"] == pytest.approx(0.0)

    def test_by_service_breakdown_sums_to_total(self):
        result    = rebuilding_surcharge(self._lost_services(), epsilon=0.40)
        check_sum = sum(s["contribution_teh"] for s in result["by_service"])
        assert check_sum == pytest.approx(result["surcharge_total"])

    def test_result_fields_present(self):
        result = rebuilding_surcharge(self._lost_services(), epsilon=0.40)
        assert "surcharge_total" in result
        assert "by_service"      in result
        assert "epsilon"         in result
        assert "amortization_years" in result


# ===========================================================================
# ground_use_fee_writedown (Eq. 29)
# ===========================================================================

class TestGroundUseFeeWritedown:
    def _base_kwargs(self):
        return dict(
            area_slu=3.5, location_value=0.629,
            use_category="residential_primary", epsilon=0.40,
        )

    def _reset_services(self):
        # Reset to restoration-target V_s baselines
        return [
            {"label": "water",   "volume": 0.4,  "kappa_ref": 1.2,  "beta": 0.8, "retained": 0.30},
            {"label": "carbon",  "volume": 0.15, "kappa_ref": 2.5,  "beta": 0.9, "retained": 0.25},
        ]

    def _lost_services(self):
        return [
            {"label": "biodiversity", "volume_lost": 5.0, "kappa_ref": 0.350, "beta": 0.7},
        ]

    def test_restoration_pathway_rb_is_zero(self):
        # services_lost=None → restoration pathway, R_b = 0
        result = ground_use_fee_writedown(
            **self._base_kwargs(),
            services_reset=self._reset_services(),
            services_lost=None,
        )
        assert result["rebuilding_surcharge"] == pytest.approx(0.0)
        assert result["writedown_pathway"] == "restoration"
        assert result["rb_breakdown"] is None

    def test_abandonment_pathway_rb_positive(self):
        result = ground_use_fee_writedown(
            **self._base_kwargs(),
            services_reset=self._reset_services(),
            services_lost=self._lost_services(),
        )
        assert result["rebuilding_surcharge"] > 0.0
        assert result["writedown_pathway"] == "abandonment"
        assert result["rb_breakdown"] is not None

    def test_master_equation_assembly(self):
        # GUF_wd = Ψ × [base + E_reset + I + R_b] × Ω
        result = ground_use_fee_writedown(
            **self._base_kwargs(),
            services_reset=self._reset_services(),
            services_lost=self._lost_services(),
        )
        psi  = result["psi"]
        expected = psi * (
            result["base_fee"] + result["eco_surcharge"] +
            result["infra_premium"] + result["rebuilding_surcharge"]
        )
        assert result["guf_formula"] == pytest.approx(expected, rel=1e-9)

    def test_abandonment_higher_than_restoration(self):
        # Abandonment adds R_b, so GUF_wd > pure restoration GUF_wd
        restoration = ground_use_fee_writedown(
            **self._base_kwargs(), services_reset=self._reset_services(), services_lost=None,
        )["guf_formula"]
        abandonment = ground_use_fee_writedown(
            **self._base_kwargs(), services_reset=self._reset_services(),
            services_lost=self._lost_services(),
        )["guf_formula"]
        assert abandonment > restoration

    def test_no_services_equals_base_only(self):
        # No E_reset, no R_b, no infra → GUF_wd = Ψ × base × Ω
        result = ground_use_fee_writedown(**self._base_kwargs())
        expected = result["psi"] * result["base_fee"]
        assert result["guf_formula"] == pytest.approx(expected, rel=1e-9)

    def test_floor_applied(self):
        # Conservation parcel: base fee negative, floor clamps to 0
        result = ground_use_fee_writedown(
            area_slu=10.0, location_value=0.1,
            use_category="conservation", epsilon=0.40, guf_floor=0.0,
        )
        assert result["guf_applied"] >= 0.0

    def test_output_keys_present(self):
        result = ground_use_fee_writedown(**self._base_kwargs())
        for key in ("guf_formula", "guf_applied", "base_fee", "eco_surcharge",
                    "infra_premium", "rebuilding_surcharge", "psi",
                    "writedown_pathway", "rb_breakdown", "floor_applied", "epsilon"):
            assert key in result

    def test_arc_boundaries(self):
        # GUF_wd obeys same arc shape: low at extremes
        r000 = ground_use_fee_writedown(
            **{**self._base_kwargs(), "epsilon": 0.00},
            services_reset=self._reset_services(), services_lost=self._lost_services(),
        )["guf_formula"]
        r040 = ground_use_fee_writedown(
            **{**self._base_kwargs(), "epsilon": 0.40},
            services_reset=self._reset_services(), services_lost=self._lost_services(),
        )["guf_formula"]
        r099 = ground_use_fee_writedown(
            **{**self._base_kwargs(), "epsilon": 0.99},
            services_reset=self._reset_services(), services_lost=self._lost_services(),
        )["guf_formula"]
        assert r000 < r040
        assert r099 < r040


# ===========================================================================
# eoh_accumulation_warning (§9.8)
# ===========================================================================

class TestEohAccumulationWarning:
    def test_no_warning_below_threshold(self):
        result = eoh_accumulation_warning(unfulfilled_eoh=20.0, total_eoh=100.0)
        assert result["ratio"] == pytest.approx(0.20)
        assert result["warning"] is False
        assert result["accelerated_rho_review"] is False
        assert result["ecology_fund_priority"]  is False

    def test_warning_above_threshold(self):
        result = eoh_accumulation_warning(unfulfilled_eoh=35.0, total_eoh=100.0)
        assert result["ratio"] == pytest.approx(0.35)
        assert result["warning"] is True
        assert result["accelerated_rho_review"] is True
        assert result["ecology_fund_priority"]  is True

    def test_exactly_at_threshold_no_warning(self):
        # Strictly greater than threshold triggers warning
        result = eoh_accumulation_warning(
            unfulfilled_eoh=GUF_EOH_ACCUMULATION_THRESHOLD * 100.0,
            total_eoh=100.0,
        )
        assert result["warning"] is False

    def test_default_threshold(self):
        result = eoh_accumulation_warning(unfulfilled_eoh=30.0, total_eoh=100.0)
        assert result["threshold"] == pytest.approx(GUF_EOH_ACCUMULATION_THRESHOLD)

    def test_custom_threshold(self):
        result = eoh_accumulation_warning(20.0, 100.0, threshold=0.15)
        assert result["warning"] is True

    def test_zero_total_eoh_no_warning(self):
        # Degenerate zone: ratio defined as 0 to avoid division
        result = eoh_accumulation_warning(unfulfilled_eoh=10.0, total_eoh=0.0)
        assert result["ratio"] == pytest.approx(0.0)
        assert result["warning"] is False

    def test_fully_fulfilled_no_warning(self):
        result = eoh_accumulation_warning(unfulfilled_eoh=0.0, total_eoh=100.0)
        assert result["ratio"] == pytest.approx(0.0)
        assert result["warning"] is False

    def test_result_fields_present(self):
        result = eoh_accumulation_warning(25.0, 100.0)
        for key in ("ratio", "threshold", "warning", "unfulfilled_eoh",
                    "total_eoh", "accelerated_rho_review", "ecology_fund_priority"):
            assert key in result


# ---------------------------------------------------------------------------
# Cross-layer reconciliation: the carbon replacement cost
#
# GUF_ECO_KAPPA_CARBON (land layer) and CDR_LABOR_HOURS_PER_TONNE (thermal layer)
# are the SAME physical quantity — labour-hours to remove one tonne of CO₂ — and
# they disagreed 4.58× (2.750 vs 0.6) until 2026-08-09, when the author adopted the
# thermal figure as the better-sourced of the two.
#
# They cannot be bound by expression: CDR_LABOR_HOURS_PER_TONNE is defined far below
# the GUF block in data.py, so a reference would be forward. This test IS the
# binding, and it is stronger than an assignment would be because it fails whichever
# side moves alone.
# ---------------------------------------------------------------------------

class TestCarbonKappaReconciliation:

    def test_carbon_kappa_equals_the_thermal_labor_intensity(self):
        from hours_eoh.data import CDR_LABOR_HOURS_PER_TONNE, GUF_ECO_KAPPA_CARBON
        assert GUF_ECO_KAPPA_CARBON == pytest.approx(CDR_LABOR_HOURS_PER_TONNE), (
            "GUF_ECO_KAPPA_CARBON and CDR_LABOR_HOURS_PER_TONNE are the same "
            "quantity (labour-hours per tonne CO₂). They were reconciled on "
            "2026-08-09 by adopting the thermal figure. If a staffing refresh moves "
            "one, move both — or record why the land layer's replacement cost should "
            "differ from the removal cost."
        )

    def test_units_are_commensurate_on_a_flow(self):
        """κ is per tonne per YEAR; the CDR figure is per tonne. The bridge is that
        replacing a displaced sink means removing its annual uptake every year, so
        the per-tonne labour cost carries straight over to the flow."""
        from hours_eoh.data import GUF_ECO_KAPPA_CARBON
        annual_uptake_tonnes = 12.0
        # One year of replacement labour for a parcel's displaced sequestration.
        assert (annual_uptake_tonnes * GUF_ECO_KAPPA_CARBON
                == pytest.approx(7.2))

    def test_sink_reversal_is_not_applied_and_that_is_recorded(self):
        """CDR_GROSS_REMOVAL_FACTOR is deliberately NOT in this path.

        Sink reversal applies when drawing atmospheric concentration DOWN; replacing
        a displaced sink offsets a FLOW, which may not incur it. Applying it would
        give 1.08. The question is open, and omitting it understates the obligation
        if it does apply — the wrong direction of error — so the omission is pinned
        here rather than left as an unexamined default.
        """
        from hours_eoh.data import (CDR_GROSS_REMOVAL_FACTOR,
                                    CDR_LABOR_HOURS_PER_TONNE,
                                    GUF_ECO_KAPPA_CARBON)
        assert GUF_ECO_KAPPA_CARBON != pytest.approx(
            CDR_LABOR_HOURS_PER_TONNE * CDR_GROSS_REMOVAL_FACTOR
        ), "sink reversal now applied — update the open question in data.py"

    def test_the_reconciliation_moved_the_land_figure_down(self):
        """Direction matters: the land layer previously charged 4.58× too much."""
        from hours_eoh.data import GUF_ECO_KAPPA_CARBON
        previous = 2.750
        assert GUF_ECO_KAPPA_CARBON < previous
        assert previous / GUF_ECO_KAPPA_CARBON == pytest.approx(4.5833, rel=1e-3)


# ===========================================================================
# Phase 1 (2026-08-17): the E term woken up.
#
# The seven GUF_ECO_KAPPA_* constants were read by NO code path. E(p,ε)
# defaulted to zero, no scenario supplied `ecosystem_services`, and every
# caller that did passed bare literals. See notes/guf-restoration-derivation.md.
# ===========================================================================

from hours_eoh.data import (
    GUF_ECO_BETA_CARBON,
    GUF_ECO_KAPPA_CARBON as _K_CARBON,
    GUF_ECO_BETA_POLLINATION,
    GUF_ECO_KAPPA_AIR_QUALITY,
    GUF_ECO_KAPPA_POLLINATION,
    GUF_ECO_KAPPA_WATER_FILTRATION,
    GUF_ECOSYSTEM_SERVICES,
)
from hours_eoh.land.guf import (
    ecosystem_services_for_area,
    service_from_registry,
)

ARC = [0.0, 0.40, 0.99]


class TestRegistryIsBoundNotRestated:
    """Every registry value must come FROM the constant that carries it."""

    def test_kappa_values_are_the_data_constants(self):
        assert GUF_ECOSYSTEM_SERVICES["carbon"]["kappa_ref"] is _K_CARBON
        assert GUF_ECOSYSTEM_SERVICES["water_filtration"]["kappa_ref"] is GUF_ECO_KAPPA_WATER_FILTRATION
        assert GUF_ECOSYSTEM_SERVICES["air_quality"]["kappa_ref"] is GUF_ECO_KAPPA_AIR_QUALITY

    def test_every_service_carries_kappa_beta_and_a_unit(self):
        # κ is meaningless without its unit: 0.6 TEH/tonne and 0.006 TEH/m³ are
        # not comparable magnitudes.
        assert len(GUF_ECOSYSTEM_SERVICES) == 7
        for name, spec in GUF_ECOSYSTEM_SERVICES.items():
            assert set(spec) == {"kappa_ref", "beta", "unit"}, name
            assert float(spec["kappa_ref"]) > 0.0
            assert 0.6 <= float(spec["beta"]) <= 1.2
            assert isinstance(spec["unit"], str) and spec["unit"]


class TestKappaAndBetaArePaired:
    """
    The sharper defect the registry closes. Eq. 15 derives κ_max from κ_ref
    THROUGH β, so mismatched partners produce a curve belonging to neither and
    nothing downstream can detect it.
    """

    def test_naming_a_service_binds_both(self):
        s = service_from_registry("pollination", volume=1.0)
        assert s["kappa_ref"] == GUF_ECO_KAPPA_POLLINATION
        assert s["beta"] == GUF_ECO_BETA_POLLINATION
        assert s["kappa_source"] == "registry"
        assert s["beta_source"] == "registry"

    def test_a_mismatched_pair_produces_a_different_curve(self):
        # Demonstrates what the pairing prevents, rather than asserting it is
        # impossible: carbon's κ under pollination's β is a real, silent error.
        right = ecosystem_service_kappa(_K_CARBON, GUF_ECO_BETA_CARBON, 0.0)
        wrong = ecosystem_service_kappa(_K_CARBON, GUF_ECO_BETA_POLLINATION, 0.0)
        assert right != pytest.approx(wrong, rel=1e-6)

    def test_kappa_equals_reference_at_the_calibration_epsilon(self):
        # Eq. 15's defining property, checked for every registered service.
        for name, spec in GUF_ECOSYSTEM_SERVICES.items():
            k = ecosystem_service_kappa(
                float(spec["kappa_ref"]), float(spec["beta"]), 0.40
            )
            assert k == pytest.approx(float(spec["kappa_ref"]), rel=1e-12), name


class TestOverridesReplaceAndAreReported:
    """κ is genuinely local, so an override is legitimate — but never silent."""

    def test_override_wins_and_is_labelled(self):
        s = service_from_registry("carbon", volume=1.0, kappa_ref=2.75)
        assert s["kappa_ref"] == 2.75
        assert s["kappa_source"] == "override"
        assert s["beta_source"] == "registry"

    def test_unknown_service_raises_with_the_registered_names(self):
        with pytest.raises(KeyError, match="unknown ecosystem service"):
            service_from_registry("unobtanium", volume=1.0)


class TestVolumeIntakeAtLandClassScale:

    def test_volumes_scale_linearly_with_area(self):
        profile = {"carbon": 2.5, "water_filtration": 0.01}
        one = ecosystem_services_for_area(1.0e6, profile)
        five = ecosystem_services_for_area(5.0e6, profile)
        for a, b in zip(one, five):
            assert b["volume"] == pytest.approx(5.0 * a["volume"], rel=1e-12)

    def test_retained_accepts_scalar_or_per_service(self):
        profile = {"carbon": 1.0, "pollination": 1.0}
        flat = ecosystem_services_for_area(100.0, profile, retained=0.5)
        assert all(s["retained"] == 0.5 for s in flat)
        keyed = ecosystem_services_for_area(100.0, profile, retained={"carbon": 0.8})
        by = {s["service"]: s["retained"] for s in keyed}
        assert by["carbon"] == 0.8
        assert by["pollination"] == 0.0  # missing key → 0.0, not an error

    def test_zero_area_gives_zero_surcharge(self):
        svcs = ecosystem_services_for_area(0.0, {"carbon": 2.5})
        for eps in ARC:
            assert ecosystem_displacement_surcharge(svcs, eps)["surcharge_total"] == 0.0

    def test_negative_area_rejected(self):
        with pytest.raises(ValueError, match="area_hectares"):
            ecosystem_services_for_area(-1.0, {"carbon": 1.0})

    def test_supplies_no_volumes_of_its_own(self):
        """
        THE DISCIPLINE. The package ships no measured per-hectare service
        volumes — there is no figure here for how much filtration a hectare of
        forest delivers. An invented one would enter with the same standing as a
        measured value and afterwards nothing could tell them apart.
        """
        with pytest.raises(TypeError):
            ecosystem_services_for_area(1.0e6)  # type: ignore[call-arg]
        assert ecosystem_services_for_area(1.0e6, {}) == []


class TestSurchargeResolvesNamedServices:

    def test_named_service_needs_no_literals(self):
        r = ecosystem_displacement_surcharge([{"service": "carbon", "volume": 1000.0}], 0.40)
        assert r["surcharge_total"] == pytest.approx(1000.0 * _K_CARBON, rel=1e-12)
        b = r["by_service"][0]
        assert b["label"] == "carbon"
        assert b["kappa_ref"] == _K_CARBON
        assert b["beta"] == GUF_ECO_BETA_CARBON

    def test_explicit_literal_form_is_unchanged(self):
        """Backward compatibility: the pre-2026-08-17 caller shape still works."""
        old = [{"label": "water", "volume": 0.4, "kappa_ref": 1.65,
                "beta": 0.8, "retained": 0.3}]
        r = ecosystem_displacement_surcharge(old, 0.40)
        assert r["surcharge_total"] == pytest.approx(0.4 * 1.65 * 0.7, rel=1e-12)

    def test_a_service_with_neither_form_raises(self):
        with pytest.raises(KeyError, match="either explicit"):
            ecosystem_displacement_surcharge([{"volume": 1.0}], 0.40)

    def test_arc_coherence_for_every_registered_service(self):
        for name in GUF_ECOSYSTEM_SERVICES:
            prev = None
            for eps in ARC:
                r = ecosystem_displacement_surcharge(
                    [{"service": name, "volume": 100.0}], eps
                )
                t = r["surcharge_total"]
                assert math.isfinite(t) and t > 0.0, name
                if prev is not None:
                    assert t < prev, f"{name} κ must fall with ε"
                prev = t


class TestEStillDefaultsToZero:
    """
    Phase 1 makes the term REACHABLE, not active. Waking it for existing
    callers would be a calibration change; the note reserves that for sign-off.
    """

    def test_ground_use_fee_without_services_has_no_eco_surcharge(self):
        for eps in ARC:
            r = ground_use_fee(
                area_slu=10.0, location_value=0.5,
                use_category="residential_primary", epsilon=eps,
            )
            assert r["eco_surcharge"] == 0.0
            assert r["eco_breakdown"] is None


class TestRestorationPathwayUsesTheSameTable:
    """
    rebuilding_surcharge is the §9 restoration/abandonment pathway — the path a
    restoration-cost derivation runs through. It read the caller's literals
    independently of E, so the two halves of the reset cost could disagree
    silently. Both now resolve through _resolve_kappa_beta.
    """

    def test_named_service_resolves_in_rebuilding_surcharge(self):
        r = rebuilding_surcharge(
            [{"service": "biodiversity", "volume_lost": 5.0}], epsilon=0.40
        )
        b = r["by_service"][0]
        assert b["label"] == "biodiversity"
        # κ = κ_ref at ε=0.40, amortised over the writedown horizon
        assert b["kappa_epsilon"] == pytest.approx(
            float(GUF_ECOSYSTEM_SERVICES["biodiversity"]["kappa_ref"]), rel=1e-12
        )

    def test_literal_form_still_works(self):
        old = rebuilding_surcharge(
            [{"label": "biodiversity", "volume_lost": 5.0,
              "kappa_ref": 0.35, "beta": 0.7}], epsilon=0.40
        )
        named = rebuilding_surcharge(
            [{"service": "biodiversity", "volume_lost": 5.0}], epsilon=0.40
        )
        # The literals in the shipped CLI example ARE the registry values, which
        # is the hazard: they agree until one side moves.
        assert old["surcharge_total"] == pytest.approx(
            named["surcharge_total"], rel=1e-12
        )

    def test_missing_both_forms_raises(self):
        with pytest.raises(KeyError, match="either explicit"):
            rebuilding_surcharge([{"volume_lost": 1.0}], epsilon=0.40)

    def test_both_paths_agree_on_kappa_for_every_service(self):
        """The drift this guards: E and the restoration path must read one table."""
        for name in GUF_ECOSYSTEM_SERVICES:
            for eps in ARC:
                e = ecosystem_displacement_surcharge(
                    [{"service": name, "volume": 1.0}], eps
                )["by_service"][0]["kappa_epsilon"]
                rb = rebuilding_surcharge(
                    [{"service": name, "volume_lost": 1.0}], eps
                )["by_service"][0]["kappa_epsilon"]
                assert e == pytest.approx(rb, rel=1e-12), f"{name} at ε={eps}"


class TestTheRemoteEndIsZeroByABSENCE:
    """
    OPEN ITEM CLOSED, AND IT WAS MIS-SCOPED (2026-08-29).

    CLAUDE.md carried this as open since 2026-08-20:

        "STILL OPEN: `retired` gives ε=0 the HIGHEST fee (1,692 h/ha·yr) …
         it collides with the spec's '≈0 at the remote end' until one
         remembers that zero comes from ASSET ABSENCE, not from a multiplier.
         … Needs the asset intake to test, which is the critical path."

    THE HYPOTHESIS IN THAT NOTE IS RIGHT AND ITS SCOPING IS WRONG. No asset
    intake is needed: `location_value` already carries absence, and it zeroes
    `base_fee` outright. NLSA §4.4's "≈0 at the remote end" is satisfied
    exactly, at every ε, and the apparent contradiction was never in the
    formula — it was in holding a SERVICED URBAN inventory fixed while
    sweeping ε, which asserts a serviced parcel at subsistence.

    The general lesson, and the reason this sat open for nine days: an item
    recorded as "needs data" is worth re-deriving before it is worked. This one
    needed a test, and the note said so in its own first clause.
    """

    def test_a_parcel_with_no_location_value_pays_nothing_at_any_epsilon(self):
        """The remote end, and it is EXACT rather than approximate."""
        for eps in (0.0, 0.40, 0.99):
            r = ground_use_fee(area_slu=1.0, location_value=0.0,
                               use_category="residential_primary", epsilon=eps)
            assert r["guf_applied"] == 0.0, f"remote land owes nothing at ε={eps}"

    def test_the_zero_is_ABSENCE_and_not_the_floor(self):
        """
        The distinction the whole item turns on. A fee clamped to zero by
        `guf_floor` would mean the formula wanted to charge and was stopped —
        which is what happens to the conservation CREDIT. Here `base_fee` is
        zero on its own, so nothing is being suppressed.
        """
        r = ground_use_fee(area_slu=1.0, location_value=0.0,
                           use_category="residential_primary", epsilon=0.0)
        assert r["base_fee"] == 0.0
        assert r["floor_applied"] is False
        assert r["guf_formula"] == 0.0

    def test_location_value_is_what_carries_absence(self):
        """Monotone in L, and zero only at zero — so 'remote' is expressible
        without an asset inventory."""
        fees = [
            ground_use_fee(area_slu=1.0, location_value=L,
                           use_category="residential_primary", epsilon=0.0)["guf_applied"]
            for L in (0.0, 0.1, 0.4, 0.75, 1.0)
        ]
        assert fees[0] == 0.0
        assert all(b > a for a, b in zip(fees, fees[1:])), fees

    def test_the_high_epsilon_zero_reading_needs_a_CONTRADICTORY_inventory(self):
        """
        THE CONTRADICTION, DEMONSTRATED. Holding a serviced urban parcel fixed
        across the arc makes ε=0 the most expensive point — α's honest reading,
        since unautomated land administration costs the most human hours. That
        is not a defect; it is a parcel declared `residential_primary` at
        L=0.75 while ε=0 asserts subsistence, and no such parcel exists.

        Both readings are pinned together so neither can be quoted alone.
        """
        serviced = [
            ground_use_fee(area_slu=1.0, location_value=0.75,
                           use_category="residential_primary", epsilon=e)["guf_applied"]
            for e in (0.0, 0.40, 0.99)
        ]
        assert serviced == sorted(serviced, reverse=True), (
            "for a FIXED inventory the fee falls monotonically with ε — α alone"
        )
        assert serviced[0] > serviced[-1] * 10.0

        remote = [
            ground_use_fee(area_slu=1.0, location_value=0.0,
                           use_category="residential_primary", epsilon=e)["guf_applied"]
            for e in (0.0, 0.40, 0.99)
        ]
        assert remote == [0.0, 0.0, 0.0], (
            "and the same sweep on land that is actually remote is flat at zero, "
            "so the spec's boundary condition holds and the inventory was the "
            "thing asserting otherwise"
        )

    def test_the_conservation_credit_is_still_clipped_and_that_is_separate(self):
        """
        NOT the same issue, pinned here so the two are not conflated. A
        conservation parcel on VALUABLE ground is owed a credit by the formula
        and receives nothing, because `guf_floor` clamps at zero. That is a
        charter question — should a credit pay out? — and it is untouched by
        this item, which is about absence rather than suppression.
        """
        r = ground_use_fee(area_slu=1.0, location_value=0.75,
                           use_category="conservation", epsilon=0.0)
        assert r["guf_formula"] < 0.0, "the formula wants to pay a credit"
        assert r["guf_applied"] == 0.0, "and the floor stops it"
        assert r["floor_applied"] is True


class TestTheConservationCreditClampIsADecision:
    """
    CHARTER DECISION, 2026-08-30 (author sign-off): a credit may reduce a fee to
    zero; it may NOT pay out.

    The clamp existed before the decision as an accident of `guf_floor`. What
    changed is that it is now DECIDED, with the four measurements that decided
    it pinned here so the decision cannot be reversed by someone who only sees
    the floor and reads it as an oversight. That is the failure this file has
    hit before: `guf_magnitude` recorded the credit as "notional −90 h/ha·yr,
    never paid" as though it were a defect awaiting repair.
    """

    HA = 100.0  # 1 ha = 100 SLU

    def _fee(self, cat, L, eps=0.40, **kw):
        return ground_use_fee(area_slu=self.HA, location_value=L,
                              use_category=cat, epsilon=eps, **kw)

    def test_a_credit_reduces_to_zero_and_no_further(self):
        """The decision, stated as behaviour."""
        for L in (0.25, 0.50, 0.75, 1.0):
            r = self._fee("conservation", L)
            assert r["guf_formula"] < 0.0, "the formula wants to pay"
            assert r["guf_applied"] == 0.0, "and it is bounded at zero"
            assert r["floor_applied"] is True

    def test_the_payout_would_dwarf_the_work_it_rewards(self):
        """
        MEASUREMENT (1): ~2,064× the measured stewardship cost. Asserted as an
        order of magnitude — the levels move with every constant in the chain,
        and pinning them is what let the stale 3.5 survive its own correction.
        """
        from hours_eoh.core.eoh_fulfillment import human_eoh_share
        from hours_eoh.data import MEAN_MULTIPLIER_REFERENCE

        payout = -self._fee("conservation", 0.75)["guf_formula"]
        measured_cost = human_eoh_share(0.182, 0.40) * MEAN_MULTIPLIER_REFERENCE
        assert payout / measured_cost > 500.0, (
            f"payout {payout:,.1f} vs measured stewardship {measured_cost:.4f} "
            f"TEH/ha·yr — if this ratio ever approaches 1 the decision is worth "
            f"revisiting, because the payout would then price the actual work"
        )

    def test_the_payout_tracks_location_value_not_ecological_service(self):
        """
        MEASUREMENT (2), and the one that decides the KIND of instrument this
        is. The same ecosystem earns an order of magnitude more on valuable
        ground, so it compensates foregone development rather than paying for
        ecology.
        """
        cheap = -self._fee("conservation", 0.05)["guf_formula"]
        dear = -self._fee("conservation", 0.95)["guf_formula"]
        assert dear > 10.0 * cheap, (
            f"identical ecosystem: {cheap:,.1f} vs {dear:,.1f} TEH/ha·yr"
        )

    def test_the_reward_for_conserving_already_exists_and_is_larger(self):
        """
        MEASUREMENT (4). The avoided fee is the incentive, and it already
        exceeds what a payout would add.
        """
        avoided = {
            cat: self._fee(cat, 0.75)["guf_applied"]
            for cat in ("residential_primary", "commercial_retail", "industrial_heavy")
        }
        payout = -self._fee("conservation", 0.75)["guf_formula"]
        assert min(avoided.values()) > payout, (
            f"avoided fees {avoided} must exceed the {payout:,.1f} a payout adds"
        )

    def test_the_coefficient_still_does_work_and_must_not_be_retired(self):
        """
        THE NUANCE THE DECISION TURNS ON. The clamp bounds the credit BELOW; it
        is live above that bound. On a parcel carrying an infrastructure
        premium the credit reduces a real, positive fee — so setting the
        coefficient to 0.0 would RAISE fees, and "the credit never pays" is not
        an argument for deleting it.
        """
        assets = [{"cost_teh": 5.0e5, "design_life": 50.0,
                   "beneficiary_count": 40.0, "distance_km": 0.2}]
        for L in (0.10, 0.25):
            with_credit = self._fee("conservation", L, infrastructure_assets=assets)
            assert with_credit["guf_applied"] > 0.0, "a real fee remains"
            assert with_credit["guf_applied"] < with_credit["infra_premium"], (
                "and the credit has reduced it below the premium alone — "
                "the coefficient is load-bearing here"
            )
            assert with_credit["floor_applied"] is False

    def test_restoration_labour_is_not_what_the_clamp_blocks(self):
        """
        WHAT THE DECISION COSTS: nothing, for the case a reward is actually
        wanted. Restoration is labour; it registers and mints TEH through the
        ordinary pipeline. The clamp forbids paying a holder for a DESIGNATION,
        not paying a restorer for HOURS.
        """
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline

        idle = eoh_to_teh_pipeline(epsilon=0.40, population=1e6)
        restoring = eoh_to_teh_pipeline(epsilon=0.40, population=1e6,
                                        restoration_obligation=1.0e6)
        assert restoring["teh_created"] > idle["teh_created"], (
            "restoration work must reach the ledger as labour — the parameter "
            "was stranded at ecological_eoh until 2026-08-30, which made this "
            "argument false at the documented entry point"
        )
