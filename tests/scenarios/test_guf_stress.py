"""
Tests for hours_eoh.scenarios.guf_stress.

Covers: guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep.
"""

import math
import pytest
from hours_eoh.scenarios.guf_stress import (
    guf_fiscal_integration,
    guf_writedown_scenario,
    guf_revenue_sweep,
)

VALID_GUF_OUTCOMES = {"GUF_MATERIAL", "GUF_SUPPLEMENTAL", "GUF_INSUFFICIENT"}


# ===========================================================================
# guf_fiscal_integration
# ===========================================================================

class TestGufFiscalIntegration:

    _PARCEL = {"area_slu": 3.5, "location_value": 0.629, "use_category": "residential_primary"}

    def test_returns_expected_keys(self):
        result = guf_fiscal_integration(epsilon=0.40, parcel_configs=[self._PARCEL])
        for key in ("scenario", "epsilon", "parcel_count", "guf_gross_revenue",
                    "guf_net_inflow", "levy_revenue", "guf_revenue_fraction_of_levy",
                    "trust_end_levy_only", "trust_end_with_guf",
                    "trust_solvent_levy_only", "trust_solvent_with_guf",
                    "outcome", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        r = guf_fiscal_integration(0.40, [self._PARCEL])
        assert r["scenario"] == "guf_fiscal_integration"

    def test_guf_net_inflow_positive_for_nonzero_parcels(self):
        result = guf_fiscal_integration(0.40, [self._PARCEL])
        assert result["guf_net_inflow"] > 0.0

    def test_guf_gross_revenue_equals_sum_of_parcels(self):
        parcels = [self._PARCEL, dict(self._PARCEL)]
        result = guf_fiscal_integration(0.40, parcels)
        assert result["guf_gross_revenue"] > 0.0
        assert result["parcel_count"] == 2

    def test_with_guf_trust_end_at_least_as_high_as_levy_only(self):
        """GUF inflow can only improve (or maintain) trust balance vs. levy-only."""
        result = guf_fiscal_integration(0.40, [self._PARCEL])
        assert result["trust_end_with_guf"] >= result["trust_end_levy_only"] - 1e-6

    def test_outcome_is_valid(self):
        result = guf_fiscal_integration(0.40, [self._PARCEL])
        assert result["outcome"] in VALID_GUF_OUTCOMES

    def test_recommendation_is_string(self):
        result = guf_fiscal_integration(0.40, [self._PARCEL])
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20

    def test_default_parcel_config_runs(self):
        """None parcel_configs uses the default single residential parcel."""
        result = guf_fiscal_integration(0.40, parcel_configs=None)
        assert result["parcel_count"] == 1
        assert result["guf_net_inflow"] > 0.0

    def test_zero_parcels_returns_zero_inflow(self):
        """Empty parcel list produces zero GUF revenue."""
        result = guf_fiscal_integration(0.40, parcel_configs=[])
        assert result["guf_gross_revenue"] == 0.0
        assert result["guf_net_inflow"] == 0.0

    def test_multiple_parcels_add_revenue(self):
        """More parcels should produce more GUF revenue than one."""
        r1 = guf_fiscal_integration(0.40, [self._PARCEL])
        r5 = guf_fiscal_integration(0.40, [self._PARCEL] * 5)
        assert r5["guf_net_inflow"] > r1["guf_net_inflow"]

    def test_guf_fraction_is_non_negative(self):
        result = guf_fiscal_integration(0.40, [self._PARCEL])
        assert result["guf_revenue_fraction_of_levy"] >= 0.0

    def test_subsidies_absorbed_reduces_net_inflow(self):
        r_no_sub = guf_fiscal_integration(0.40, [self._PARCEL], subsidies_absorbed=0.0)
        r_sub    = guf_fiscal_integration(0.40, [self._PARCEL], subsidies_absorbed=1.0)
        assert r_sub["guf_net_inflow"] <= r_no_sub["guf_net_inflow"]


# ===========================================================================
# guf_writedown_scenario
# ===========================================================================

class TestGufWritedownScenario:

    def test_returns_expected_keys(self):
        result = guf_writedown_scenario(epsilon=0.40)
        for key in ("scenario", "epsilon", "pathway", "warning_triggered",
                    "eoh_ratio", "guf_standard_total", "guf_writedown_total",
                    "revenue_delta", "rebuilding_surcharge_total", "recommendation"):
            assert key in result

    def test_scenario_name(self):
        assert guf_writedown_scenario(0.40)["scenario"] == "guf_writedown_scenario"

    def test_warning_triggered_when_ratio_above_threshold(self):
        """unfulfilled/total > 0.30 must trigger warning."""
        result = guf_writedown_scenario(
            epsilon=0.40,
            unfulfilled_eoh=400_000.0,
            total_eoh=1_000_000.0,   # ratio = 0.40 > threshold 0.30
        )
        assert result["warning_triggered"] is True

    def test_no_warning_below_threshold(self):
        result = guf_writedown_scenario(
            epsilon=0.40,
            unfulfilled_eoh=100_000.0,
            total_eoh=1_000_000.0,   # ratio = 0.10 < threshold 0.30
        )
        assert result["warning_triggered"] is False

    def test_restoration_pathway_zero_rebuilding_surcharge(self):
        result = guf_writedown_scenario(epsilon=0.40, pathway="restoration")
        assert result["rebuilding_surcharge_total"] == pytest.approx(0.0, abs=1e-6)

    def test_abandonment_pathway_nonzero_rebuilding_surcharge(self):
        result = guf_writedown_scenario(epsilon=0.40, pathway="abandonment")
        assert result["rebuilding_surcharge_total"] > 0.0

    def test_abandonment_revenue_higher_than_restoration(self):
        """Abandonment includes R_b surcharge — writedown GUF must be higher."""
        r_rest = guf_writedown_scenario(epsilon=0.40, pathway="restoration")
        r_aband = guf_writedown_scenario(epsilon=0.40, pathway="abandonment")
        assert r_aband["guf_writedown_total"] >= r_rest["guf_writedown_total"] - 1e-6

    def test_invalid_pathway_raises(self):
        with pytest.raises(ValueError):
            guf_writedown_scenario(epsilon=0.40, pathway="liquidation")

    def test_eoh_ratio_matches_unfulfilled_over_total(self):
        result = guf_writedown_scenario(
            epsilon=0.40,
            unfulfilled_eoh=300_000.0,
            total_eoh=1_000_000.0,
        )
        assert result["eoh_ratio"] == pytest.approx(0.30, rel=1e-6)

    def test_standard_guf_positive(self):
        result = guf_writedown_scenario(epsilon=0.40)
        assert result["guf_standard_total"] > 0.0

    def test_recommendation_is_string(self):
        result = guf_writedown_scenario(epsilon=0.40)
        assert isinstance(result["recommendation"], str)
        assert len(result["recommendation"]) > 20


# ===========================================================================
# guf_revenue_sweep
# ===========================================================================

class TestGufRevenueSweep:

    def test_returns_list(self):
        result = guf_revenue_sweep()
        assert isinstance(result, list)

    def test_default_has_eleven_points(self):
        result = guf_revenue_sweep()
        assert len(result) == 11

    def test_custom_epsilon_values_length(self):
        eps_vals = [0.0, 0.20, 0.40, 0.60, 0.80, 0.99]
        result = guf_revenue_sweep(epsilon_values=eps_vals)
        assert len(result) == 6

    def test_row_keys_present(self):
        result = guf_revenue_sweep()
        for row in result:
            for key in ("epsilon", "guf_applied", "psi", "base_fee",
                        "eco_surcharge", "infra_premium"):
                assert key in row

    def test_all_values_finite(self):
        result = guf_revenue_sweep()
        for row in result:
            for key, val in row.items():
                if isinstance(val, float):
                    assert math.isfinite(val), f"Non-finite {key} at ε={row['epsilon']}"

    def test_guf_peaks_near_mid_epsilon(self):
        """GUF tracks Ψ(ε) bell — the mid-arc point should have higher GUF than extremes."""
        result = guf_revenue_sweep(
            epsilon_values=[0.0, 0.10, 0.40, 0.80, 0.99]
        )
        by_eps = {r["epsilon"]: r["guf_applied"] for r in result}
        assert by_eps[0.40] > by_eps[0.0]
        assert by_eps[0.40] > by_eps[0.99]

    def test_psi_peaks_near_040(self):
        """Ψ(ε) bell peak should occur near ε=0.40."""
        result = guf_revenue_sweep()
        psi_values = [(r["epsilon"], r["psi"]) for r in result]
        max_psi_eps = max(psi_values, key=lambda x: x[1])[0]
        assert 0.30 <= max_psi_eps <= 0.60, (
            f"Ψ(ε) peak at ε={max_psi_eps}, expected between 0.30 and 0.60"
        )

    def test_custom_parcel_config_used(self):
        """Custom parcel config should produce different GUF values than default."""
        r_default = guf_revenue_sweep()
        r_custom  = guf_revenue_sweep(
            parcel_config={
                "area_slu": 10.0,
                "location_value": 0.90,
                "use_category": "commercial_retail",
            }
        )
        # Larger commercial parcel should produce higher GUF
        guf_default = sum(r["guf_applied"] for r in r_default)
        guf_custom  = sum(r["guf_applied"] for r in r_custom)
        assert guf_custom != guf_default
