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
    def _nlsa_example(self, epsilon=0.40):
        """NLSA §10 residential example (partial — no previous cycle cap)."""
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

    def test_guf_lower_at_zero_epsilon(self):
        zero = self._nlsa_example(0.0)["guf_formula"]
        mid  = self._nlsa_example(0.40)["guf_formula"]
        # ε=0 has near-zero Ψ; GUF substantially lower
        assert zero < mid * 0.10

    def test_occupancy_fraction_scales(self):
        full = ground_use_fee(3.5, 0.629, "residential_primary", 0.40,
                              occupancy_fraction=1.0)["guf_formula"]
        half = ground_use_fee(3.5, 0.629, "residential_primary", 0.40,
                              occupancy_fraction=0.5)["guf_formula"]
        assert half == pytest.approx(full * 0.5, rel=1e-6)

    def test_boundary_verification_subsistence(self):
        # NLSA §4.4: GUF(ε=0) < 0.05 × GUF(ε=0.40) for all parcels
        g0   = self._nlsa_example(0.00)["guf_formula"]
        g040 = self._nlsa_example(0.40)["guf_formula"]
        assert g0 < 0.05 * g040

    def test_boundary_verification_post_scarcity(self):
        # NLSA §4.4: GUF(ε=0.99) < 0.05 × GUF(ε=0.40) for all parcels
        g099 = self._nlsa_example(0.99)["guf_formula"]
        g040 = self._nlsa_example(0.40)["guf_formula"]
        assert g099 < 0.05 * g040


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
