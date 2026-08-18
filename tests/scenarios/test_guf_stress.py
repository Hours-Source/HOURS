"""
Tests for hours_eoh.scenarios.guf_stress.

Covers: guf_fiscal_integration, guf_writedown_scenario, guf_revenue_sweep,
        automation_levy_guf_stress.
"""

import math
import pytest
from hours_eoh.scenarios.guf_stress import (
    guf_fiscal_integration,
    guf_writedown_scenario,
    guf_revenue_sweep,
    automation_levy_guf_stress,
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


# ===========================================================================
# automation_levy_guf_stress
# ===========================================================================

class TestAutomationLevyGufStress:

    def test_returns_expected_keys(self):
        result = automation_levy_guf_stress(n_periods=5)
        for key in (
            "scenario", "trajectory", "parcel_count", "epsilon_range",
            "levy_peak_period", "guf_peak_period", "crossover_period",
            "first_insolvency", "compensation_adequacy", "outcome", "recommendation",
        ):
            assert key in result

    def test_scenario_name(self):
        result = automation_levy_guf_stress(n_periods=3)
        assert result["scenario"] == "automation_levy_guf_stress"

    def test_trajectory_length(self):
        n = 8
        result = automation_levy_guf_stress(n_periods=n)
        assert len(result["trajectory"]) == n

    def test_trajectory_row_keys(self):
        result = automation_levy_guf_stress(n_periods=3)
        row = result["trajectory"][0]
        for key in ("period", "epsilon", "levy_revenue", "guf_net_inflow",
                    "guf_levy_ratio", "sufficiency_cost", "trust_end", "solvent"):
            assert key in row

    def test_epsilon_monotone_increasing(self):
        result = automation_levy_guf_stress(
            epsilon_start=0.20, epsilon_end=0.70, n_periods=10
        )
        eps = [r["epsilon"] for r in result["trajectory"]]
        for i in range(1, len(eps)):
            assert eps[i] > eps[i - 1]

    def test_all_levy_revenues_finite(self):
        result = automation_levy_guf_stress(n_periods=5)
        for row in result["trajectory"]:
            assert math.isfinite(row["levy_revenue"])
            assert row["levy_revenue"] >= 0.0

    def test_all_guf_net_inflows_finite(self):
        result = automation_levy_guf_stress(n_periods=5)
        for row in result["trajectory"]:
            assert math.isfinite(row["guf_net_inflow"])
            assert row["guf_net_inflow"] >= 0.0

    def test_all_trust_ends_finite(self):
        result = automation_levy_guf_stress(n_periods=5)
        for row in result["trajectory"]:
            assert math.isfinite(row["trust_end"])

    def test_outcome_valid_values(self):
        result = automation_levy_guf_stress(n_periods=5)
        assert result["outcome"] in {"ADEQUATE", "PARTIAL", "CRISIS"}

    def test_guf_peak_period_before_high_epsilon(self):
        # Ψ(ε) bell peaks near ε=0.40; stress from 0.10→0.99 should see GUF peak early
        result = automation_levy_guf_stress(
            epsilon_start=0.10, epsilon_end=0.99, n_periods=20
        )
        guf_peak_row = result["trajectory"][result["guf_peak_period"]]
        # GUF peak must occur at ε < 0.70 (well before the high-ε tail)
        assert guf_peak_row["epsilon"] < 0.70

    def test_first_insolvency_none_when_large_trust(self):
        from hours_eoh.data import TRUST_BASE_TEH
        result = automation_levy_guf_stress(
            trust_balance=TRUST_BASE_TEH * 10,  # very large trust buffer
            n_periods=5,
        )
        assert result["first_insolvency"] is None

    def test_parcel_count_matches_default_inventory(self):
        result = automation_levy_guf_stress(n_periods=3)
        assert result["parcel_count"] == 1_000  # default make_urban_collective(1_000)

    def test_custom_parcel_inventory_respected(self):
        custom = [
            {"area_slu": 5.0, "location_value": 0.80, "use_category": "commercial_retail"},
        ]
        result = automation_levy_guf_stress(parcel_inventory=custom, n_periods=3)
        assert result["parcel_count"] == 1

    def test_compensation_adequacy_positive_with_parcels(self):
        result = automation_levy_guf_stress(n_periods=10)
        assert result["compensation_adequacy"] >= 0.0

    def test_epsilon_range_stored(self):
        result = automation_levy_guf_stress(
            epsilon_start=0.30, epsilon_end=0.75, n_periods=5
        )
        assert result["epsilon_range"] == [0.30, 0.75]


# ===========================================================================
# ε-coherence for the writedown scenario (2026-08-17).
#
# THE GAP THAT HID A LIVE DEFECT. Every existing test of
# guf_writedown_scenario ran at ε=0.40. κ_s(ε) equals κ_ref EXACTLY at 0.40 by
# construction (NLSA Eq. 15), so a β mismatch between two entries describing the
# same service is invisible there — and one was shipped: the default parcel
# carried beta 0.8 on services_reset and beta 0.7 on services_lost for the same
# water-filtration service. CLAUDE.md requires tests at the four key ε values
# precisely so a check cannot land only where the defect cancels.
# ===========================================================================

ARC_EPSILONS = [0.0, 0.40, 0.90, 0.99]


class TestWritedownArcCoherence:

    def test_runs_and_stays_finite_across_the_arc(self):
        for eps in ARC_EPSILONS:
            for pathway in ("restoration", "abandonment"):
                r = guf_writedown_scenario(epsilon=eps, pathway=pathway)
                rb = r["rebuilding_surcharge_total"]
                assert math.isfinite(rb) and rb >= 0.0, (eps, pathway)

    def test_rebuilding_surcharge_falls_with_automation(self):
        """
        κ_s(ε) is monotonically decreasing, so the amortised replacement cost of
        a lost service must fall as ε rises. This is the assertion that would
        have caught the mismatch: it only has content OFF the reference point.
        """
        prev = None
        for eps in ARC_EPSILONS:
            rb = guf_writedown_scenario(
                epsilon=eps, pathway="abandonment"
            )["rebuilding_surcharge_total"]
            if prev is not None:
                assert rb < prev, f"ε={eps} did not fall below the previous point"
            prev = rb

    def test_default_parcel_prices_one_service_on_one_curve(self):
        """
        The regression pin for the fix. Both the reset and the lost entry must
        resolve to water filtration's OWN β — not two different exponents for
        one physical service. Checked away from ε=0.40, where a mismatch cancels.
        """
        from hours_eoh.data import (
            GUF_ECO_BETA_WATER_FILTRATION,
            GUF_ECO_KAPPA_WATER_FILTRATION,
        )
        from hours_eoh.land.guf import ecosystem_service_kappa

        for eps in (0.0, 0.99):
            expected_kappa = ecosystem_service_kappa(
                GUF_ECO_KAPPA_WATER_FILTRATION, GUF_ECO_BETA_WATER_FILTRATION, eps
            )
            # volume_lost 0.4 amortised over the default 50-year horizon
            expected = 0.4 * expected_kappa / 50.0
            got = guf_writedown_scenario(
                epsilon=eps, pathway="abandonment"
            )["rebuilding_surcharge_total"]
            assert got == pytest.approx(expected, rel=1e-12), f"ε={eps}"

    def test_the_mismatch_would_now_be_visible(self):
        """
        Demonstrates that the arc test has teeth: reintroducing the old β on the
        lost side changes the result off the reference point, and does not
        change it at ε=0.40 — which is exactly why it survived.
        """
        old = [{
            "area_slu": 3.5, "location_value": 0.629,
            "use_category": "residential_primary",
            "services_reset": [{"service": "water_filtration", "volume": 0.4,
                                "retained": 0.3}],
            "services_lost": [{"label": "water", "volume_lost": 0.4,
                               "kappa_ref": 1.65, "beta": 0.7}],
        }]
        at_ref = guf_writedown_scenario(epsilon=0.40, pathway="abandonment",
                                        parcels_at_risk=old)
        ref_now = guf_writedown_scenario(epsilon=0.40, pathway="abandonment")
        assert at_ref["rebuilding_surcharge_total"] == pytest.approx(
            ref_now["rebuilding_surcharge_total"], rel=1e-12
        ), "the mismatch must be invisible at ε=0.40 — that is the finding"

        off_ref = guf_writedown_scenario(epsilon=0.99, pathway="abandonment",
                                         parcels_at_risk=old)
        now = guf_writedown_scenario(epsilon=0.99, pathway="abandonment")
        assert off_ref["rebuilding_surcharge_total"] != pytest.approx(
            now["rebuilding_surcharge_total"], rel=1e-6
        ), "and visible off it"
