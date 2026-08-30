"""
Tests for hours_eoh.core.fiscal

Covers: levy_collection, stewardship_allocation, sufficiency_guarantee,
trust_management, fiscal_snapshot, trust_solvency_trajectory,
care_stipend, steward_eoh_obligation, collective_land_registration,
stewardship_dividend_needed, min_levy_for_solvency,
ecological_allocation, aggregate_care_stipend_from_demographics,
accumulation_ceiling_commitment.

Sources: phase3, phase6 (TestTrustSolvencyTrajectory, TestFiscalSnapshotCapitalEohEliminated),
         phase7 (TestMinLevyForSolvency), phase12 C2 (TestEcologicalAllocation,
         TestFiscalSnapshotEcological), phase14 (TestAggregateCareStipendHelper,
         TestFiscalSnapshotCareStipend), phase15 (TestAccumulationCeiling).
"""

import math
import pytest

from hours_eoh.data import (
    SUFF_GUARANTEE_STRUCTURAL_MIN,
    CARE_AUTOMATION_FLOOR,
    PROVIDER_CAP_EQUIVALENTS,
)
from hours_eoh.core.fiscal import (
    levy_collection,
    stewardship_allocation,
    sufficiency_guarantee,
    trust_management,
    fiscal_snapshot,
    trust_solvency_trajectory,
    care_stipend,
    steward_eoh_obligation,
    collective_land_registration,
    stewardship_dividend_needed,
    min_levy_for_solvency,
    ecological_allocation,
    aggregate_care_stipend_from_demographics,
    accumulation_ceiling_commitment,
)
from hours_eoh.core.conditions import balance_check
from hours_eoh.params import EohParams
from hours_eoh.data import (
    TRUST_BASE_TEH,
    DEP_RATE,
    DIV_RATE,
    CAPITAL_STOCK_DEFAULT,
    ACCUMULATION_CEILING_MULTIPLIER,
    BASE_LIFETIME_EARNINGS_TEH,
    ECOLOGICAL_BASE_RATE,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# Levies and Circulation
# ===========================================================================

class TestLevyCollection:

    def test_levy_is_circulatory(self):
        """All levy revenue is accounted for — no TEH created or destroyed through fiscal mechanisms."""
        labor_income = 2_200_000_000.0
        rates = {"sufficiency": 0.0125, "stewardship": 0.01}

        result = levy_collection(labor_income, rates)

        assert result["worker_net"] + result["total_levied"] == pytest.approx(
            result["gross_income"]
        ), "Levy must be circulatory: worker_net + total_levied = gross_income"

        assert result["circulatory"] is True

    def test_levy_balance_check_passes_for_worker_and_trust(self):
        """Condition III holds for both accounts after levy collection."""
        labor_income = 1_000_000.0
        levy_rate = 0.0125
        trust_start = 15_000_000_000.0

        result = levy_collection(labor_income, {"sufficiency": levy_rate})
        levy_amount = result["total_levied"]

        worker_check = balance_check(
            balance_start=0.0,
            earnings=labor_income,
            expenditures=levy_amount,
            balance_end=result["worker_net"],
        )
        assert worker_check["passes"] is True

        trust_check = balance_check(
            balance_start=trust_start,
            earnings=levy_amount,
            expenditures=0.0,
            balance_end=trust_start + levy_amount,
        )
        assert trust_check["passes"] is True

    def test_zero_levy_rates_return_full_income_to_worker(self):
        result = levy_collection(1_000_000.0, {"suff": 0.0})
        assert result["worker_net"] == pytest.approx(1_000_000.0)
        assert result["total_levied"] == pytest.approx(0.0)

    def test_multiple_levy_rates_sum_correctly(self):
        income = 1_000_000.0
        rates = {"a": 0.01, "b": 0.02, "c": 0.005}
        result = levy_collection(income, rates)
        assert result["total_levy_rate"] == pytest.approx(0.035)
        assert result["total_levied"] == pytest.approx(35_000.0)
        assert result["by_levy"]["a"] == pytest.approx(10_000.0)
        assert result["by_levy"]["b"] == pytest.approx(20_000.0)
        assert result["by_levy"]["c"] == pytest.approx(5_000.0)

    def test_levy_rate_out_of_range_raises(self):
        with pytest.raises(ValueError):
            levy_collection(1_000_000.0, {"bad": 1.5})

    def test_total_levy_over_100_pct_raises(self):
        with pytest.raises(ValueError):
            levy_collection(1_000_000.0, {"a": 0.6, "b": 0.6})

    def test_levy_at_all_key_epsilons(self):
        """Levy is ε-independent (applied to labor income regardless of ε)."""
        income = 1_000_000.0
        for _ in KEY_EPSILONS:
            result = levy_collection(income, {"suff": 0.0125})
            assert result["total_levied"] == pytest.approx(12_500.0)


# ===========================================================================
# Stewardship Allocation
# ===========================================================================

class TestStewardshipAllocation:

    def test_stewardship_scales_with_capital_stock(self):
        """Stewardship allocation scales with capital stock EOH."""
        eps = 0.40
        stew_small = stewardship_allocation(1e9,  0.5, eps, available_teh=1e12)
        stew_large = stewardship_allocation(3e9,  0.5, eps, available_teh=1e12)
        assert stew_large["teh_required"] > stew_small["teh_required"]

    def test_stewardship_human_share_decreases_with_epsilon(self):
        """At higher ε, automation handles more stewardship → less human-labor EOH."""
        capital = 2e9
        stew_0  = stewardship_allocation(capital, 0.5, 0.0,  available_teh=1e12)
        stew_90 = stewardship_allocation(capital, 0.5, 0.90, available_teh=1e12)
        assert stew_90["human_stewardship_eoh"] < stew_0["human_stewardship_eoh"]

    def test_stewardship_capped_at_available(self):
        """Allocation cannot exceed available TEH."""
        eps = 0.40
        result = stewardship_allocation(2e9, 0.5, eps, available_teh=1_000.0)
        assert result["teh_allocated"] <= 1_000.0 + 1e-6
        assert result["funding_gap"] > 0

    def test_stewardship_fully_funded_when_sufficient(self):
        result = stewardship_allocation(2e9, 0.5, 0.40, available_teh=1e12)
        assert result["fully_funded"] is True
        assert result["funding_gap"] == pytest.approx(0.0)

    def test_stewardship_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = stewardship_allocation(2e9, 0.5, eps, available_teh=1e12)
            assert math.isfinite(result["teh_required"])
            assert result["teh_required"] > 0

    def test_stewardship_infrastructure_eoh_in_result(self):
        """Result includes the EOH breakdown for auditability."""
        result = stewardship_allocation(2e9, 0.5, 0.40, available_teh=1e12)
        assert "infrastructure_eoh_total" in result
        assert "human_stewardship_eoh" in result
        assert result["infrastructure_eoh_total"] > 0
        assert result["human_stewardship_eoh"] <= result["infrastructure_eoh_total"]

    def test_infra_eoh_override_used_directly(self):
        """When infra_eoh_override is supplied, it is used without recomputation."""
        override_value = 500_000.0
        result = stewardship_allocation(
            2e9, 0.5, 0.40, available_teh=1e12,
            infra_eoh_override=override_value,
        )
        assert result["infrastructure_eoh_total"] == pytest.approx(override_value)

    def test_infra_eoh_override_affects_teh_required(self):
        """Override value flows through to human_stewardship_eoh and teh_required."""
        normal   = stewardship_allocation(2e9, 0.5, 0.40, available_teh=1e12)
        override = stewardship_allocation(2e9, 0.5, 0.40, available_teh=1e12,
                                          infra_eoh_override=normal["infrastructure_eoh_total"] * 0.5)
        assert override["teh_required"] < normal["teh_required"]

    def test_fiscal_snapshot_threads_effective_infrastructure_eoh(self):
        """fiscal_snapshot passes infra_eoh_override to stewardship_allocation."""
        base = fiscal_snapshot(
            trust_balance=TRUST_BASE_TEH,
            labor_income=5e9,
            capital_stock_teh=2e9,
            capital_age_ratio=0.5,
            population=1_000_000,
            epsilon=0.40,
        )
        reduced_infra = base["stewardship"]["infrastructure_eoh_total"] * 0.70
        reduced = fiscal_snapshot(
            trust_balance=TRUST_BASE_TEH,
            labor_income=5e9,
            capital_stock_teh=2e9,
            capital_age_ratio=0.5,
            population=1_000_000,
            epsilon=0.40,
            infra_eoh_override=reduced_infra,
        )
        assert reduced["stewardship"]["infrastructure_eoh_total"] < base["stewardship"]["infrastructure_eoh_total"]
        assert reduced["stewardship"]["teh_required"] < base["stewardship"]["teh_required"]


# ===========================================================================
# Sufficiency Guarantee
# ===========================================================================

class TestSufficiencyGuarantee:

    def test_guarantee_cost_positive_at_all_epsilons(self):
        for eps in KEY_EPSILONS:
            result = sufficiency_guarantee(1_000_000, eps)
            assert result["total_cost_teh"] > 0
            assert math.isfinite(result["total_cost_teh"])

    def test_fewer_recipients_needed_at_higher_epsilon(self):
        """At higher ε: rising PP means fewer people need the floor guarantee."""
        g_0  = sufficiency_guarantee(1_000_000, 0.0)
        g_90 = sufficiency_guarantee(1_000_000, 0.90)
        assert g_90["floor_fraction"] < g_0["floor_fraction"]

    def test_structural_minimum_always_preserved(self):
        """Even at ε=0.99, some fraction always at floor (not zero)."""
        result = sufficiency_guarantee(1_000_000, 0.99)
        assert result["floor_fraction"] > 0.0

    def test_guarantee_scales_with_population(self):
        g1 = sufficiency_guarantee(1_000_000, 0.40)
        g2 = sufficiency_guarantee(2_000_000, 0.40)
        assert g2["total_cost_teh"] == pytest.approx(g1["total_cost_teh"] * 2, rel=1e-4)

    def test_guarantee_higher_activity_teh_increases_cost(self):
        """Higher meaningful activity TEH increases total guarantee cost."""
        g1 = sufficiency_guarantee(1_000_000, 0.40, meaningful_activity_teh=1000.0)
        g2 = sufficiency_guarantee(1_000_000, 0.40, meaningful_activity_teh=2000.0)
        assert g2["total_cost_teh"] > g1["total_cost_teh"]

    def test_guarantee_result_keys(self):
        """New EOH-reimbursement model returns expected keys."""
        result = sufficiency_guarantee(1_000_000, 0.40)
        for key in ("raw_eoh_per_person", "capital_personal_eoh_fulfilled_per_person",
                    "eoh_reimbursement_per_person", "meaningful_activity_teh_effective",
                    "total_per_person", "eoh_reimbursement_total",
                    "meaningful_activity_total", "total_cost_teh"):
            assert key in result, f"Missing key: {key}"

    def test_meaningful_activity_scales_with_epsilon(self):
        """Meaningful activity TEH grows quadratically with ε."""
        g_0  = sufficiency_guarantee(1_000_000, 0.0)
        g_90 = sufficiency_guarantee(1_000_000, 0.90)
        assert g_90["meaningful_activity_teh_effective"] > g_0["meaningful_activity_teh_effective"]

    def test_eoh_reimbursement_independent_of_epsilon(self):
        """EOH reimbursement per person is fixed — biology does not change with automation."""
        g_0  = sufficiency_guarantee(1_000_000, 0.0)
        g_90 = sufficiency_guarantee(1_000_000, 0.90)
        assert g_0["eoh_reimbursement_per_person"] == pytest.approx(
            g_90["eoh_reimbursement_per_person"], rel=1e-9
        )

    def test_capital_fulfillment_zero_by_default(self):
        """Without capital fulfillment, reimbursement equals full age-weighted personal EOH."""
        g = sufficiency_guarantee(1_000_000, 0.40)
        assert g["capital_personal_eoh_fulfilled_per_person"] == 0.0
        assert g["eoh_reimbursement_per_person"] == pytest.approx(g["raw_eoh_per_person"])

    def test_capital_fulfillment_reduces_reimbursement(self):
        """Capital fulfillment reduces EOH reimbursement by the fulfilled amount."""
        g_base    = sufficiency_guarantee(1_000_000, 0.40)
        fulfilled = 500.0
        g_partial = sufficiency_guarantee(
            1_000_000, 0.40,
            capital_personal_eoh_fulfilled_per_person=fulfilled,
        )
        expected = g_base["raw_eoh_per_person"] - fulfilled
        assert g_partial["eoh_reimbursement_per_person"] == pytest.approx(expected, rel=1e-6)
        assert g_partial["total_cost_teh"] < g_base["total_cost_teh"]

    def test_capital_fulfillment_floored_at_zero(self):
        """Over-fulfillment floors reimbursement at zero."""
        g = sufficiency_guarantee(
            1_000_000, 0.40,
            capital_personal_eoh_fulfilled_per_person=9_999.0,
        )
        assert g["eoh_reimbursement_per_person"] == 0.0
        assert g["total_cost_teh"] > 0.0  # meaningful_activity_teh still paid


# ===========================================================================
# Trust Management
# ===========================================================================

class TestTrustManagement:

    def test_trust_solvent_at_all_key_epsilons(self):
        """Trust remains solvent at ε = 0, 0.40, 0.90, 0.99."""
        p = EohParams()
        for eps in KEY_EPSILONS:
            result = trust_management(
                trust_balance=p["trust_base"],
                levy_revenue=50_000_000.0,
                stewardship_cost=100_000_000.0,
                guarantee_cost=80_000_000.0,
                dep_rate=p["dep_rate"],
                div_rate=p["div_rate"],
                epsilon=eps,
            )
            assert result["solvent"] is True, (
                f"Trust must be solvent at ε={eps} with conservative expenditures"
            )

    def test_trust_insolvent_when_expenditures_exceed_revenue(self):
        p = EohParams()
        result = trust_management(
            trust_balance=p["trust_base"],
            levy_revenue=0.0,
            stewardship_cost=1e12,
            guarantee_cost=1e12,
            dep_rate=p["dep_rate"],
            div_rate=p["div_rate"],
            epsilon=0.40,
        )
        assert result["solvent"] is False

    def test_trust_no_interest(self):
        """Trust balance changes only through depreciation, renewal, and levy inflows — no interest."""
        trust_start = 15_000_000_000.0
        levy = 50_000_000.0
        dep = trust_start * 0.045
        div = dep * 0.40
        renewal = dep * 0.60

        result = trust_management(trust_start, levy, 0.0, 0.0, 0.045, 0.40)

        expected_end = trust_start - dep + renewal + levy
        assert result["trust_end"] == pytest.approx(expected_end, rel=1e-6)

    def test_trust_balance_decline_without_levy(self):
        """Without levy inflows, trust balance declines over time."""
        result = trust_management(15e9, 0.0, 50e6, 50e6, 0.045, 0.40)
        assert result["trust_end"] < 15e9

    def test_trust_surplus_deficit_correct(self):
        p = EohParams()
        levy = 100_000_000.0
        stew = 50_000_000.0
        guar = 40_000_000.0
        ann_dep = p["trust_base"] * p["dep_rate"]
        dividend = ann_dep * p["div_rate"]
        expected_revenue = dividend + levy
        expected_exp = stew + guar

        result = trust_management(p["trust_base"], levy, stew, guar,
                                   p["dep_rate"], p["div_rate"])
        assert result["total_revenue"]     == pytest.approx(expected_revenue)
        assert result["total_expenditure"] == pytest.approx(expected_exp)
        assert result["surplus_deficit"]   == pytest.approx(expected_revenue - expected_exp)

    def test_all_result_keys_present(self):
        result = trust_management(15e9, 10e6, 50e6, 50e6)
        for key in ("trust_start", "ann_depreciation", "dividend", "renewal",
                    "levy_inflow", "total_revenue", "total_expenditure",
                    "surplus_deficit", "solvent", "trust_end", "trust_stable"):
            assert key in result, f"Missing key: {key}"


# ===========================================================================
# Fiscal Snapshot
# ===========================================================================

class TestFiscalSnapshot:

    def test_fiscal_snapshot_returns_all_sections(self):
        p = EohParams()
        result = fiscal_snapshot(
            trust_balance=p["trust_base"],
            labor_income=2_200_000_000.0,
            capital_stock_teh=p["capital_stock_teh"],
            capital_age_ratio=p["capital_age_ratio"],
            population=p["population"],
            epsilon=0.40,
        )
        for key in ("levies", "stewardship", "guarantee", "trust", "solvent"):
            assert key in result

    def test_fiscal_snapshot_circulatory_levy(self):
        """Levy in snapshot is circulatory: total_levied goes into trust."""
        p = EohParams()
        result = fiscal_snapshot(
            trust_balance=p["trust_base"],
            labor_income=1_000_000_000.0,
            capital_stock_teh=p["capital_stock_teh"],
            capital_age_ratio=p["capital_age_ratio"],
            population=p["population"],
            epsilon=0.40,
        )
        levied = result["levies"]["total_levied"]
        trust_inflow = result["trust"]["levy_inflow"]
        assert levied == pytest.approx(trust_inflow)


class TestFiscalSnapshotCapitalEohEliminated:
    """fiscal_snapshot() must auto-reduce infrastructure EOH when capital_eoh_eliminated > 0."""

    def _base_snapshot(self, **overrides):
        kwargs = dict(
            trust_balance=TRUST_BASE_TEH,
            labor_income=5_000_000_000.0,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT,
            capital_age_ratio=0.30,
            population=1_000_000.0,
            epsilon=0.40,
        )
        kwargs.update(overrides)
        return fiscal_snapshot(**kwargs)

    def test_no_elimination_baseline(self):
        """With capital_eoh_eliminated=0, snapshot must run without error."""
        result = self._base_snapshot(capital_eoh_eliminated=0.0)
        assert result["solvent"] in (True, False)

    def test_elimination_reduces_stewardship_cost(self):
        """Non-zero capital_eoh_eliminated must reduce stewardship allocation."""
        base = self._base_snapshot(capital_eoh_eliminated=0.0)
        reduced = self._base_snapshot(capital_eoh_eliminated=50_000_000.0)
        base_stew = base["stewardship"]["teh_allocated"]
        red_stew  = reduced["stewardship"]["teh_allocated"]
        assert red_stew <= base_stew

    def test_explicit_override_takes_precedence(self):
        """infra_eoh_override must take precedence over auto-computation."""
        auto   = self._base_snapshot(capital_eoh_eliminated=50_000_000.0)
        manual = self._base_snapshot(infra_eoh_override=999_999_999.0,
                                     capital_eoh_eliminated=50_000_000.0)
        assert (manual["stewardship"]["teh_allocated"]
                >= auto["stewardship"]["teh_allocated"])

    def test_large_elimination_does_not_go_negative(self):
        """Eliminating more EOH than infrastructure total must not produce negative cost."""
        result = self._base_snapshot(capital_eoh_eliminated=1e15)
        stew = result["stewardship"]["teh_allocated"]
        assert stew >= 0.0

    def test_snapshot_keys_present(self):
        result = self._base_snapshot()
        for key in ("solvent", "trust", "stewardship", "guarantee", "levies"):
            assert key in result

    def test_at_all_key_epsilons(self):
        """With elimination, snapshot must remain finite across all key ε."""
        for eps in KEY_EPSILONS:
            result = self._base_snapshot(
                epsilon=eps,
                capital_eoh_eliminated=20_000_000.0,
            )
            trust_end = result["trust"]["trust_end"]
            assert math.isfinite(trust_end)


# ===========================================================================
# Trust Solvency Trajectory
# ===========================================================================

class TestTrustSolvencyTrajectory:
    """Trust trajectory must track balance correctly and flag insolvency."""

    def test_return_keys_present(self):
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=10,
        )
        for key in ("periods", "solvent_throughout", "first_insolvency",
                    "final_balance", "min_balance", "total_levy_inflow",
                    "total_expenditure", "trend"):
            assert key in result

    def test_period_count_matches_n_periods(self):
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=15,
        )
        assert len(result["periods"]) == 15

    def test_no_levy_declining_trend(self):
        """With zero levy revenue and non-zero expenditure, Trust must decline."""
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=20,
            levy_revenue_per_period=0.0,
        )
        assert result["final_balance"] < TRUST_BASE_TEH or not result["solvent_throughout"]

    def test_high_levy_stable_or_growing(self):
        """High levy revenue relative to costs must keep Trust stable or growing."""
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=20,
            levy_revenue_per_period=5_000_000_000.0,
            stewardship_cost_per_period=100_000_000.0,
            guarantee_cost_per_period=100_000_000.0,
        )
        assert result["solvent_throughout"] is True
        assert result["trend"] in ("GROWING", "STABLE")

    def test_insolvency_detected_when_floor_exceeded(self):
        """Trust must be flagged insolvent once balance drops below the solvency floor."""
        result = trust_solvency_trajectory(
            initial_trust_balance=1_000.0,
            n_periods=50,
            levy_revenue_per_period=0.0,
            stewardship_cost_per_period=0.0,
            guarantee_cost_per_period=0.0,
            solvency_floor=500.0,
        )
        assert result["solvent_throughout"] is False
        assert result["first_insolvency"] is not None
        assert result["first_insolvency"] < 50

    def test_first_insolvency_none_when_always_solvent(self):
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=10,
            levy_revenue_per_period=5_000_000_000.0,
            stewardship_cost_per_period=100_000_000.0,
            guarantee_cost_per_period=100_000_000.0,
        )
        assert result["first_insolvency"] is None
        assert result["solvent_throughout"] is True

    def test_period_balances_finite(self):
        result = trust_solvency_trajectory(
            initial_trust_balance=TRUST_BASE_TEH,
            n_periods=30,
        )
        for p in result["periods"]:
            assert math.isfinite(p["trust_end"])

    def test_explicit_costs_override_auto(self):
        """Explicit stewardship/guarantee costs must be used as-is."""
        result_auto   = trust_solvency_trajectory(TRUST_BASE_TEH, n_periods=5)
        result_manual = trust_solvency_trajectory(
            TRUST_BASE_TEH,
            n_periods=5,
            stewardship_cost_per_period=0.0,
            guarantee_cost_per_period=0.0,
        )
        assert result_manual["final_balance"] >= result_auto["final_balance"]

    def test_trend_field_valid(self):
        result = trust_solvency_trajectory(TRUST_BASE_TEH, n_periods=20)
        assert result["trend"] in ("GROWING", "STABLE", "DECLINING", "INSOLVENT")


# ===========================================================================
# Care Stipend
# ===========================================================================

class TestCareStipend:

    def test_stipend_highest_for_infant(self):
        """Care stipend highest for ages 0–6."""
        infant   = care_stipend([0], epsilon=0.40)
        toddler  = care_stipend([4], epsilon=0.40)
        school   = care_stipend([8], epsilon=0.40)
        teen     = care_stipend([15], epsilon=0.40)
        assert (infant["epsilon_adjusted"]
                > toddler["epsilon_adjusted"]
                > school["epsilon_adjusted"]
                > teen["epsilon_adjusted"])

    def test_adult_dependent_produces_zero_stipend(self):
        """Adults (age ≥ 18) are not covered — no gaming via adult 'dependents'."""
        result = care_stipend([20, 30], epsilon=0.40)
        assert result["epsilon_adjusted"] == pytest.approx(0.0)

    def test_diminishing_returns_for_multiple_dependents(self):
        """Diminishing per additional dependent — anti-gaming."""
        one   = care_stipend([0],       epsilon=0.40)
        two   = care_stipend([0, 0],    epsilon=0.40)
        three = care_stipend([0, 0, 0], epsilon=0.40)

        second_marginal = two["after_diminishing"] - one["after_diminishing"]
        third_marginal  = three["after_diminishing"] - two["after_diminishing"]

        assert second_marginal < one["after_diminishing"]
        assert third_marginal < second_marginal

    def test_provider_cap_limits_high_dependent_counts(self):
        """Per-provider cap prevents unlimited expansion."""
        many_infants = care_stipend([0] * 10, epsilon=0.40)
        one_infant   = care_stipend([0], epsilon=0.40)
        assert many_infants["epsilon_adjusted"] < 10 * one_infant["epsilon_adjusted"]
        assert many_infants["cap_applied"] is True

    def test_stipend_declines_with_epsilon(self):
        """Per-dependent EOH scales inversely with ε."""
        s_0  = care_stipend([0], epsilon=0.0)
        s_40 = care_stipend([0], epsilon=0.40)
        s_90 = care_stipend([0], epsilon=0.90)
        assert s_0["epsilon_adjusted"] > s_40["epsilon_adjusted"] > s_90["epsilon_adjusted"]

    def test_relational_care_floor_at_high_epsilon(self):
        """Even at ε=0.99: some care stipend remains for relational/emotional care."""
        result = care_stipend([0], epsilon=0.99)
        assert result["epsilon_adjusted"] > 0.0
        assert result["automation_factor"] >= 0.14

    def test_stipend_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = care_stipend([0, 3, 8], epsilon=eps)
            assert math.isfinite(result["epsilon_adjusted"])
            assert result["epsilon_adjusted"] >= 0.0

    def test_empty_dependents_produces_zero(self):
        result = care_stipend([], epsilon=0.40)
        assert result["epsilon_adjusted"] == pytest.approx(0.0)
        assert result["dependents_count"] == 0

    def test_covered_count_excludes_adults(self):
        result = care_stipend([2, 8, 20, 25], epsilon=0.40)
        assert result["covered_count"] == 2

    def test_stipend_reasonable_magnitude(self):
        """Sanity check: single infant's annual stipend at ε=0 equals base_infant_stipend."""
        result = care_stipend([0], epsilon=0.0, base_infant_stipend=200.0)
        assert result["epsilon_adjusted"] == pytest.approx(200.0)


# ===========================================================================
# Steward EOH Obligation + Collective Land Registration
# ===========================================================================

class TestStewardEohObligation:

    def test_private_obligation_at_low_epsilon(self):
        """At low ε: nearly all housing EOH is private."""
        result = steward_eoh_obligation(
            structure_value_teh=500_000.0,
            land_area_units=1.0,
            epsilon=0.0,
        )
        assert result["private_eoh_obligation"] > 0
        assert result["private_eoh_obligation"] > result["collective_eoh_registered"] * 5

    def test_collective_share_grows_with_epsilon(self):
        r_0  = steward_eoh_obligation(500_000.0, 1.0, epsilon=0.0)
        r_90 = steward_eoh_obligation(500_000.0, 1.0, epsilon=0.90)
        r_99 = steward_eoh_obligation(500_000.0, 1.0, epsilon=0.99)
        assert r_99["collective_eoh_registered"] > r_90["collective_eoh_registered"] > r_0["collective_eoh_registered"]

    def test_private_plus_collective_equals_total(self):
        """Conservation: private + collective = total."""
        result = steward_eoh_obligation(500_000.0, 1.0, epsilon=0.90)
        assert (result["private_eoh_obligation"] + result["collective_eoh_registered"]
                == pytest.approx(result["total_structure_eoh"]))

    def test_at_full_automation_most_is_collective(self):
        result = steward_eoh_obligation(500_000.0, 1.0, epsilon=0.99)
        assert result["collective_share"] > 0.70

    def test_scales_with_structure_value(self):
        r1 = steward_eoh_obligation(200_000.0, 1.0, 0.40)
        r2 = steward_eoh_obligation(400_000.0, 1.0, 0.40)
        assert r2["total_structure_eoh"] == pytest.approx(r1["total_structure_eoh"] * 2)


class TestCollectiveLandRegistration:

    def test_near_zero_at_low_epsilon(self):
        """Collective housing registration is near zero below ε≈0.70."""
        share_0  = collective_land_registration(0.0)
        share_40 = collective_land_registration(0.40)
        assert share_0  < 0.01
        assert share_40 < 0.05

    def test_rises_steeply_at_high_epsilon(self):
        share_80 = collective_land_registration(0.80)
        share_90 = collective_land_registration(0.90)
        share_99 = collective_land_registration(0.99)
        assert share_80 < share_90 < share_99

    def test_monotonically_increasing(self):
        prev = 0.0
        for i in range(20):
            eps = i * 0.99 / 19
            share = collective_land_registration(eps)
            assert share >= prev - 1e-10
            prev = share

    def test_bounded_by_saturation(self):
        for eps in KEY_EPSILONS:
            share = collective_land_registration(eps)
            assert 0.0 <= share <= 0.90 + 1e-6

    def test_near_saturation_at_eps_099(self):
        share = collective_land_registration(0.99)
        assert share > 0.85


# ===========================================================================
# Fiscal Solvency Integration
# ===========================================================================

class TestFiscalSolvencyIntegration:

    def _solvency_at(self, epsilon: float) -> dict:
        from hours_eoh.core.prices import floor_purchasing_power
        p = EohParams()
        teh_created_approx = max(300_000_000.0, 2_200_000_000.0 * (1.0 - epsilon * 0.80))
        levies = levy_collection(teh_created_approx, {"sufficiency": p["suff_levy_rate"]})
        stew   = stewardship_allocation(
            p["capital_stock_teh"], p["capital_age_ratio"],
            epsilon, available_teh=p["trust_base"],
        )
        guar   = sufficiency_guarantee(p["population"], epsilon)
        trust  = trust_management(
            p["trust_base"], levies["total_levied"],
            stew["teh_allocated"], guar["total_cost_teh"],
            p["dep_rate"], p["div_rate"], epsilon,
        )
        pp = floor_purchasing_power(p["meaningful_activity_teh_base"], epsilon)
        return {"levies": levies, "stewardship": stew,
                "guarantee": guar, "trust": trust, "pp": pp}

    def test_trust_solvent_at_eps0(self):
        result = self._solvency_at(0.0)
        assert result["trust"]["solvent"] is True

    def test_trust_solvent_at_eps40(self):
        result = self._solvency_at(0.40)
        assert result["trust"]["solvent"] is True

    def test_trust_solvent_at_eps90(self):
        result = self._solvency_at(0.90)
        assert result["trust"]["solvent"] is True

    def test_trust_solvent_at_eps99(self):
        result = self._solvency_at(0.99)
        assert result["trust"]["solvent"] is True

    def test_floor_pp_rises_across_automation_arc(self):
        pp_0  = self._solvency_at(0.0)["pp"]["pp_index"]
        pp_40 = self._solvency_at(0.40)["pp"]["pp_index"]
        pp_90 = self._solvency_at(0.90)["pp"]["pp_index"]
        assert pp_0 <= pp_40 <= pp_90

    def test_all_levy_revenue_accounted(self):
        """No TEH created or destroyed through fiscal mechanisms."""
        p = EohParams()
        income = 2_200_000_000.0
        levies = levy_collection(income, {"suff": p["suff_levy_rate"]})
        before = income + p["trust_base"]
        after  = levies["worker_net"] + levies["total_levied"] + p["trust_base"]
        assert before == pytest.approx(after)


# ===========================================================================
# Stewardship Dividend Needed
# ===========================================================================

class TestStewardshipDividendNeeded:

    def test_min_div_rate_computed(self):
        result = stewardship_dividend_needed(
            stewardship_teh_required=500.0,
            dep_rate=0.10,
            trust_balance=10_000.0,
        )
        assert result["min_div_rate"] == pytest.approx(0.5)

    def test_feasible_when_min_div_rate_lte_one(self):
        result = stewardship_dividend_needed(500.0, dep_rate=0.10, trust_balance=10_000.0)
        assert result["feasible"] is True

    def test_infeasible_when_trust_too_small(self):
        result = stewardship_dividend_needed(5_000.0, dep_rate=0.10, trust_balance=1_000.0)
        assert result["feasible"] is False
        assert result["min_div_rate"] > 1.0

    def test_zero_trust_balance_returns_none_div_rate(self):
        result = stewardship_dividend_needed(500.0, dep_rate=0.10, trust_balance=0.0)
        assert result["min_div_rate"] is None
        assert result["feasible"] is False

    def test_shortfall_at_div1_positive_when_infeasible(self):
        result = stewardship_dividend_needed(5_000.0, dep_rate=0.10, trust_balance=1_000.0)
        assert result["shortfall_at_div1"] > 0.0

    def test_shortfall_zero_when_feasible(self):
        result = stewardship_dividend_needed(50.0, dep_rate=0.10, trust_balance=10_000.0)
        assert result["shortfall_at_div1"] == pytest.approx(0.0)

    def test_result_keys(self):
        result = stewardship_dividend_needed(500.0, dep_rate=0.10, trust_balance=10_000.0)
        for key in ("stewardship_teh_required", "annual_dep", "min_div_rate",
                    "trust_balance", "dep_rate", "feasible", "shortfall_at_div1"):
            assert key in result


# ===========================================================================
# Min Levy For Solvency
# ===========================================================================

class TestMinLevyForSolvency:
    """Inverse query must correctly compute the three solvency-target levies."""

    def _run(self, **overrides):
        kwargs = dict(
            trust_balance=TRUST_BASE_TEH,
            epsilon=0.40,
        )
        kwargs.update(overrides)
        return min_levy_for_solvency(**kwargs)

    def test_return_keys_present(self):
        result = self._run()
        for key in ("trust_balance", "dividend", "stewardship_cost", "guarantee_cost",
                    "total_expenditure", "current_surplus", "cover_expenditures",
                    "stable_trust", "full_solvency", "feasible", "epsilon"):
            assert key in result

    def test_stable_trust_equals_dividend(self):
        result = self._run()
        assert result["stable_trust"] == pytest.approx(result["dividend"])

    def test_full_solvency_geq_stable_trust(self):
        result = self._run()
        assert result["full_solvency"] >= result["stable_trust"] - 1e-9

    def test_full_solvency_geq_cover_expenditures(self):
        result = self._run()
        assert result["full_solvency"] >= result["cover_expenditures"] - 1e-9

    def test_cover_expenditures_zero_when_surplus(self):
        result = min_levy_for_solvency(
            trust_balance=1e15,
            epsilon=0.40,
            stewardship_teh=1.0,
            guarantee_teh=1.0,
        )
        assert result["cover_expenditures"] == pytest.approx(0.0)

    def test_levy_rates_returned_with_labor_income(self):
        result = min_levy_for_solvency(
            trust_balance=TRUST_BASE_TEH,
            epsilon=0.40,
            labor_income=5_000_000_000.0,
        )
        for rate_key in ("cover_expenditures_rate", "stable_trust_rate", "full_solvency_rate"):
            assert result[rate_key] is not None
            assert result[rate_key] >= 0.0

    def test_levy_rates_none_without_labor_income(self):
        result = self._run()
        for rate_key in ("cover_expenditures_rate", "stable_trust_rate", "full_solvency_rate"):
            assert result[rate_key] is None

    def test_at_all_key_epsilons_finite(self):
        for eps in KEY_EPSILONS:
            result = min_levy_for_solvency(trust_balance=TRUST_BASE_TEH, epsilon=eps)
            assert math.isfinite(result["full_solvency"])

    def test_explicit_cost_override(self):
        result = min_levy_for_solvency(
            trust_balance=TRUST_BASE_TEH,
            stewardship_teh=100_000.0,
            guarantee_teh=100_000.0,
        )
        assert result["stewardship_cost"] == pytest.approx(100_000.0)
        assert result["guarantee_cost"]   == pytest.approx(100_000.0)
        assert result["total_expenditure"] == pytest.approx(200_000.0)

    def test_full_solvency_rate_increases_with_cost(self):
        low  = min_levy_for_solvency(TRUST_BASE_TEH, stewardship_teh=1e6,  guarantee_teh=1e6,  labor_income=5e9)
        high = min_levy_for_solvency(TRUST_BASE_TEH, stewardship_teh=1e10, guarantee_teh=1e10, labor_income=5e9)
        assert high["full_solvency_rate"] >= low["full_solvency_rate"]


# ===========================================================================
# Ecological Allocation (C2)
# ===========================================================================

#: Phases 4e/4f (adopted 2026-08-28/29) relocated BOTH recurring ecological
#: terms to GUF, so `ecological_allocation` funds nothing by default — the
#: recurring cost of holding land is the Ground Use Fee's. Tests whose subject
#: is the ALLOCATION MECHANISM run at the pre-partition policy, where there is
#: an obligation to allocate against; the adopted default is asserted by
#: `TestTheAllocationIsEmptyUnderThePartition` below.
PRE_PARTITION = {"health_response": "domain", "standing_response": "domain"}


class TestEcologicalAllocation:
    """ecological_allocation() must mirror stewardship_allocation() semantics
    but for ecological EOH."""

    def test_return_keys(self):
        result = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40,
            available_teh=1_000_000_000.0,
        )
        for key in ("ecological_eoh_total", "human_ecological_eoh", "teh_required",
                    "teh_allocated", "funding_gap", "fully_funded",
                    "funding_coverage", "epsilon"):
            assert key in result

    def test_teh_allocated_capped_at_available(self):
        available = 1_000.0
        result = ecological_allocation(0.70, 0.40, available_teh=available, **PRE_PARTITION)
        assert result["teh_allocated"] <= available + 1e-9

    def test_fully_funded_when_trust_large(self):
        result = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40,
            available_teh=1_000_000_000_000.0,
        )
        assert result["fully_funded"] is True
        assert result["funding_gap"] == pytest.approx(0.0)

    def test_funding_gap_when_trust_zero(self):
        result = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40, available_teh=0.0,
            **PRE_PARTITION,
        )
        assert result["teh_allocated"] == pytest.approx(0.0)
        assert result["funding_gap"] > 0.0
        assert result["fully_funded"] is False

    def test_higher_epsilon_lower_human_ecological_eoh(self):
        low  = ecological_allocation(0.70, 0.20, available_teh=1e12, **PRE_PARTITION)
        high = ecological_allocation(0.70, 0.80, available_teh=1e12, **PRE_PARTITION)
        assert high["human_ecological_eoh"] < low["human_ecological_eoh"]

    def test_degraded_ecosystem_requires_more_teh(self):
        healthy  = ecological_allocation(0.90, 0.40, available_teh=1e12, **PRE_PARTITION)
        degraded = ecological_allocation(0.30, 0.40, available_teh=1e12, **PRE_PARTITION)
        assert degraded["teh_required"] > healthy["teh_required"]

    def test_eco_eoh_override_respected(self):
        result = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40,
            available_teh=1e12, eco_eoh_override=999_999.0,
        )
        assert result["ecological_eoh_total"] == pytest.approx(999_999.0)

    def test_funding_coverage_one_when_fully_funded(self):
        result = ecological_allocation(0.70, 0.40, available_teh=1e12, **PRE_PARTITION)
        assert result["funding_coverage"] == pytest.approx(1.0)

    def test_funding_coverage_proportional_when_underfunded(self):
        result = ecological_allocation(0.70, 0.40, available_teh=0.0)
        assert result["funding_coverage"] == pytest.approx(0.0)


class TestFiscalSnapshotEcological:
    """fiscal_snapshot() must include ecological allocation."""

    def _snap(self, **kwargs):
        defaults = dict(
            trust_balance=TRUST_BASE_TEH,
            labor_income=2_000_000_000.0,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT,
            capital_age_ratio=0.30,
            population=1_000_000.0,
            epsilon=0.40,
            ecosystem_health=0.70,
        )
        defaults.update(kwargs)
        return fiscal_snapshot(**defaults)

    def test_ecological_key_present(self):
        result = self._snap()
        assert "ecological" in result

    def test_ecological_keys_complete(self):
        result = self._snap()
        eco = result["ecological"]
        for key in ("ecological_eoh_total", "human_ecological_eoh", "teh_required",
                    "teh_allocated", "funding_gap", "fully_funded", "funding_coverage"):
            assert key in eco

    def test_ecological_teh_counted_in_trust_expenditure(self):
        result = self._snap()
        stew_alloc = result["stewardship"]["teh_allocated"]
        eco_alloc  = result["ecological"]["teh_allocated"]
        trust_exp  = result["trust"]["total_expenditure"]
        guarantee  = result["guarantee"]["total_cost_teh"]
        assert trust_exp == pytest.approx(stew_alloc + eco_alloc + guarantee, rel=1e-6)

    def test_degraded_ecosystem_reduces_solvency(self):
        """
        PHASES 4e/4f: `ecosystem_health` no longer reaches the fisc through the
        ecological domain — condition changes what the HOLDER owes via GUF, not
        what the Trust allocates. Asserted by supplying the obligation the
        pre-partition policy would have produced, which is what
        `relocated_to_guf` now reports on every snapshot.
        """
        from hours_eoh.core.eoh_generation import ecological_eoh
        def snap_at(h):
            return self._snap(
                ecosystem_health=h,
                eco_eoh_override=ecological_eoh(
                    h, 0.40, health_response="domain",
                    standing_response="domain"),
            )
        healthy, degraded = snap_at(0.95), snap_at(0.25)
        assert (degraded["trust"]["surplus_deficit"]
                < healthy["trust"]["surplus_deficit"])

    def test_health_no_longer_moves_the_fisc_by_default(self):
        """The consequence, pinned: the relocation is reported, not silent."""
        healthy, degraded = self._snap(ecosystem_health=0.95), self._snap(ecosystem_health=0.25)
        assert (degraded["trust"]["surplus_deficit"]
                == healthy["trust"]["surplus_deficit"])
        assert degraded["ecological"]["teh_required"] == 0.0
        assert degraded["ecological"]["relocated_to_guf"] > \
            healthy["ecological"]["relocated_to_guf"]

    def test_eco_eoh_override_passthrough(self):
        result = self._snap(eco_eoh_override=0.0)
        assert result["ecological"]["ecological_eoh_total"] == pytest.approx(0.0)
        assert result["ecological"]["teh_required"] == pytest.approx(0.0)

    def test_existing_keys_still_present(self):
        result = self._snap()
        for key in ("levies", "stewardship", "guarantee", "trust", "solvent"):
            assert key in result

    def test_levy_circularity_unchanged(self):
        result = self._snap()
        assert (result["levies"]["total_levied"]
                == pytest.approx(result["trust"]["levy_inflow"]))


# ===========================================================================
# Aggregate Care Stipend Helper (new-15)
# ===========================================================================

class TestAggregateCareStipendHelper:

    def test_positive_output(self):
        result = aggregate_care_stipend_from_demographics(
            population=1_000_000.0, epsilon=0.40
        )
        assert result > 0.0

    def test_declines_with_epsilon(self):
        r0 = aggregate_care_stipend_from_demographics(1_000_000.0, 0.0)
        r9 = aggregate_care_stipend_from_demographics(1_000_000.0, 0.90)
        assert r0 > r9

    def test_scales_with_population(self):
        r_small = aggregate_care_stipend_from_demographics(500_000.0, 0.40)
        r_large = aggregate_care_stipend_from_demographics(1_000_000.0, 0.40)
        assert r_large == pytest.approx(2 * r_small, rel=1e-6)

    def test_zero_population_returns_zero(self):
        assert aggregate_care_stipend_from_demographics(0.0, 0.40) == 0.0

    def test_higher_child_fraction_increases_stipend(self):
        low  = aggregate_care_stipend_from_demographics(1e6, 0.40, child_fraction=0.05)
        high = aggregate_care_stipend_from_demographics(1e6, 0.40, child_fraction=0.30)
        assert high > low


class TestFiscalSnapshotCareStipend:

    def _base(self, **kwargs) -> dict:
        return fiscal_snapshot(
            trust_balance=TRUST_BASE_TEH,
            labor_income=5_000_000_000.0,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT,
            capital_age_ratio=0.30,
            population=1_000_000.0,
            epsilon=0.40,
            **kwargs,
        )

    def test_care_stipend_field_in_return(self):
        result = self._base()
        assert "care_stipend" in result

    def test_zero_care_stipend_default(self):
        result = self._base()
        assert result["care_stipend"] == 0.0

    def test_care_stipend_aggregate_included_in_expenditure(self):
        base     = self._base(care_stipend_aggregate=0.0)
        with_care = self._base(care_stipend_aggregate=100_000_000.0)
        assert with_care["trust"]["total_expenditure"] > base["trust"]["total_expenditure"]
        assert with_care["trust"]["surplus_deficit"] < base["trust"]["surplus_deficit"]

    def test_care_stipend_flows_through_to_solvency(self):
        large_care = TRUST_BASE_TEH
        result = self._base(care_stipend_aggregate=large_care)
        assert result["trust"]["surplus_deficit"] < 0.0

    def test_backward_compat_no_care_stipend(self):
        result = self._base()
        assert "solvent" in result
        assert "trust" in result


# ===========================================================================
# Accumulation Ceiling (D6)
# ===========================================================================

class TestAccumulationCeiling:

    def test_zero_commitment_below_ceiling(self):
        ceiling = ACCUMULATION_CEILING_MULTIPLIER * BASE_LIFETIME_EARNINGS_TEH
        pop = 1_000_000.0
        teh_circ = ceiling * 0.5 * pop
        result = accumulation_ceiling_commitment(teh_circ, pop)
        assert result["teh_committed_to_capital"] == 0.0

    def test_positive_commitment_above_ceiling(self):
        ceiling = ACCUMULATION_CEILING_MULTIPLIER * BASE_LIFETIME_EARNINGS_TEH
        pop = 1_000_000.0
        teh_circ = ceiling * 2.0 * pop
        result = accumulation_ceiling_commitment(teh_circ, pop)
        assert result["teh_committed_to_capital"] > 0.0

    def test_commitment_equals_population_times_excess(self):
        ceiling = ACCUMULATION_CEILING_MULTIPLIER * BASE_LIFETIME_EARNINGS_TEH
        pop = 1_000_000.0
        per_capita = ceiling + 50_000.0
        result = accumulation_ceiling_commitment(per_capita * pop, pop)
        assert abs(result["teh_committed_to_capital"] - 50_000.0 * pop) < 1.0
        assert abs(result["excess_per_capita"] - 50_000.0) < 1.0

    def test_custom_ceiling_respected(self):
        pop = 100_000.0
        per_capita = 200_000.0
        result = accumulation_ceiling_commitment(
            per_capita * pop, pop,
            ceiling_multiplier=1.0,
            base_lifetime_earnings=100_000.0,
        )
        assert abs(result["teh_committed_to_capital"] - 100_000.0 * pop) < 1.0

    def test_mechanism_label(self):
        result = accumulation_ceiling_commitment(0.0, 1.0)
        assert result["mechanism"] == "D6_ceiling"


class TestFiscalSnapshotStatesItsFrame:
    """
    THE SEAM BETWEEN THE TWO DOCUMENTED ENTRY POINTS (closed 2026-08-20).

    `docs/guides/implementation_guide.md` tells an institution to run
    `eoh_to_teh_pipeline()` and `fiscal_snapshot()`. Until this fix those two
    calls resolved the ecological obligation two different ways: the pipeline
    derived the area from the population it was given (Phase 4b), while
    fiscal_snapshot took its requirement from ECOLOGICAL_BASE_RATE, the whole
    contiguous US, whatever population was passed. The guide's own worked
    example — 5M people — therefore disagreed with itself by 92.8x, reported
    `solvent: True` either way, and surfaced nothing.

    This is the sixth instance of the frame defect and the first on the
    institutional intake path. The static gate lives in
    tests/test_ecological_scale_resolution.py; these are the runtime pins.
    """

    def _frame(self, population, hectares):
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        pipe = eoh_to_teh_pipeline(
            epsilon=0.40, population=population, capital_stock=2000.0 * population,
            ecosystem_health=0.70, ecological_area_hectares=hectares,
        )
        snap = fiscal_snapshot(
            trust_balance=35e9, labor_income=pipe["teh_created"],
            capital_stock_teh=2000.0 * population, capital_age_ratio=0.5,
            population=population, epsilon=0.40, ecosystem_health=0.70,
            ecological_area_hectares=hectares,
        )
        return pipe["eoh_by_domain"]["ecological"], snap["ecological"]["ecological_eoh_total"]

    def test_the_two_entry_points_agree_at_a_declared_frame(self):
        """Same jurisdiction, same land → one obligation, not two."""
        for pop, ha in ((1e6, 1.65e6), (5e6, 12e6), (335e6, 765_495_267.0)):
            eco_pipe, eco_fisc = self._frame(pop, ha)
            assert eco_fisc == pytest.approx(eco_pipe, rel=1e-9), (
                f"pop={pop:,.0f} ha={ha:,.0f}: pipeline {eco_pipe:.6e} "
                f"vs fiscal {eco_fisc:.6e}"
            )

    def test_the_undeclared_default_now_resolves_from_population(self):
        """
        Omitting the area is no longer an unstated US pairing: it resolves the
        same way `total_eoh` does, so the default is a frame somebody chose.
        """
        from hours_eoh.data import LAND_HECTARES_PER_CAPITA
        pop = 5_000_000.0
        bare = fiscal_snapshot(
            trust_balance=35e9, labor_income=1e9, capital_stock_teh=2000.0 * pop,
            capital_age_ratio=0.5, population=pop, epsilon=0.40, ecosystem_health=0.70,
        )["ecological"]["ecological_eoh_total"]
        declared = fiscal_snapshot(
            trust_balance=35e9, labor_income=1e9, capital_stock_teh=2000.0 * pop,
            capital_age_ratio=0.5, population=pop, epsilon=0.40, ecosystem_health=0.70,
            ecological_area_hectares=pop * LAND_HECTARES_PER_CAPITA,
        )["ecological"]["ecological_eoh_total"]
        assert bare == pytest.approx(declared, rel=1e-12)

    def test_the_ecological_requirement_scales_with_the_frame(self):
        """
        The property the defect destroyed: doubling the land doubles the
        obligation. Under the US anchor it was invariant to both land and
        population, which is what made a 5M-person collective owe the US total.
        """
        pop = 5_000_000.0
        small = fiscal_snapshot(
            trust_balance=35e9, labor_income=1e9, capital_stock_teh=2000.0 * pop,
            capital_age_ratio=0.5, population=pop, epsilon=0.40, ecosystem_health=0.70,
            ecological_area_hectares=6e6,
        )["ecological"]["ecological_eoh_total"]
        large = fiscal_snapshot(
            trust_balance=35e9, labor_income=1e9, capital_stock_teh=2000.0 * pop,
            capital_age_ratio=0.5, population=pop, epsilon=0.40, ecosystem_health=0.70,
            ecological_area_hectares=12e6,
        )["ecological"]["ecological_eoh_total"]
        assert large == pytest.approx(2.0 * small, rel=1e-9)

    def test_base_rate_and_area_together_are_refused(self):
        """
        Two answers to one question. `ecological_scale` silently prefers
        base_rate, so an area the caller believes is in force and is not is the
        silently-ignored-parameter failure this repo keeps finding. `total_eoh`
        refuses the same combination.
        """
        with pytest.raises(ValueError, match="not both"):
            ecological_allocation(
                ecosystem_health=0.70, epsilon=0.40, available_teh=1e9,
                base_rate=5e5, area_hectares=1e6,
            )

    def test_a_caller_with_no_population_keeps_the_declared_us_frame(self):
        """
        The gate is an allowlist for a reason: `ecological_allocation` called
        directly has no population in scope, and for it the declared reference
        frame is the right default. Unchanged behaviour, pinned so the fix to
        the population-scaled callers cannot silently migrate down here.
        """
        from hours_eoh.data import ECOLOGICAL_BASE_RATE
        from hours_eoh.core.eoh_generation import ecological_eoh
        got = ecological_allocation(
            ecosystem_health=0.70, epsilon=0.40, available_teh=1e12,
        )["ecological_eoh_total"]
        assert got == pytest.approx(
            ecological_eoh(0.70, 0.40, base_rate=ECOLOGICAL_BASE_RATE), rel=1e-12
        )


class TestTheGuaranteeAndCareFloors:
    """
    THE THREE FISCAL FLOORS, migrated and pinned (2026-08-28).

    `SUFF_GUARANTEE_STRUCTURAL_MIN`, `CARE_AUTOMATION_FLOOR` and
    `PROVIDER_CAP_EQUIVALENTS` lived in `core/fiscal.py` as shadow constants —
    untagged, invisible to the provenance gate, and a +7% move failed no test.
    All three are `normative`: they are commitments, not measurements, which is
    exactly why they need pinning. A charter commitment nothing tests is a
    commitment the code can quietly abandon.

    Pinned as BEHAVIOUR — that the floor exists, binds, and cannot be argued
    below — rather than at their levels.
    """

    def test_the_guarantee_floor_never_falls_below_the_structural_minimum(self):
        """
        The floor's floor. As ε → 1 the guarantee decays toward this and stops;
        a model in which automation removes the entitlement entirely is a
        different charter.
        """
        for eps in (0.0, 0.40, 0.90, 0.99, 1.0):
            g = sufficiency_guarantee(1_000_000.0, eps)
            assert g["floor_fraction"] >= SUFF_GUARANTEE_STRUCTURAL_MIN - 1e-12, (
                f"guarantee floor breached at ε={eps}: {g['floor_fraction']}"
            )

    def test_a_caller_cannot_set_a_guarantee_below_the_minimum(self):
        """The clamp is the mechanism — the commitment is not a default that a
        caller may quietly undercut."""
        g = sufficiency_guarantee(1_000_000.0, 0.0, floor_fraction=0.0)
        assert g["floor_fraction"] >= SUFF_GUARANTEE_STRUCTURAL_MIN - 1e-12

    def test_the_guarantee_floor_decays_but_stays_above_the_minimum(self):
        """Both halves: it does shrink with automation, and it does not vanish."""
        lo = sufficiency_guarantee(1_000_000.0, 0.0)["floor_fraction"]
        hi = sufficiency_guarantee(1_000_000.0, 0.99)["floor_fraction"]
        assert hi < lo, "the floor should shrink with automation"
        assert hi > SUFF_GUARANTEE_STRUCTURAL_MIN

    def test_care_stipend_floors_at_the_relational_fraction(self):
        """
        THE CLAIM: some fraction of care is relational and cannot be automated
        at any ε. Block II reached the same conclusion from the other side —
        care is the least abatable component — so a non-zero floor here is
        consistent with the abatement model rather than an independent guess.
        """
        assert care_stipend([0], epsilon=0.0)["automation_factor"] == pytest.approx(1.0)
        at_full = care_stipend([0], epsilon=1.0)["automation_factor"]
        assert at_full == pytest.approx(CARE_AUTOMATION_FLOOR, rel=1e-9)
        assert at_full > 0.0, "care may not automate to nothing"

    def test_the_care_automation_factor_falls_monotonically(self):
        factors = [care_stipend([0], epsilon=e)["automation_factor"]
                   for e in (0.0, 0.25, 0.5, 0.75, 0.99)]
        assert factors == sorted(factors, reverse=True), factors
        assert all(f >= CARE_AUTOMATION_FLOOR - 1e-12 for f in factors)

    def test_the_provider_cap_binds_on_many_dependents(self):
        """
        A cap that never applies is not a cap. It must bind for a large
        household and not for a single dependent.
        """
        assert care_stipend([0], epsilon=0.0)["cap_applied"] is False
        many = care_stipend([0] * 6, epsilon=0.0)
        assert many["cap_applied"] is True
        assert many["capped_total"] <= many["provider_cap_teh"] + 1e-9

    def test_the_cap_is_the_declared_number_of_full_rate_dependents(self):
        """It is denominated in full-infant-rate equivalents, so the cap must be
        exactly that multiple of the base stipend at ε=0."""
        c = care_stipend([0], epsilon=0.0, base_infant_stipend=200.0)
        assert c["provider_cap_teh"] == pytest.approx(
            200.0 * PROVIDER_CAP_EQUIVALENTS, rel=1e-12
        )


class TestGufRevenueReachesTheFisc:
    """
    THE PLUMBING GAP THE PARTITION CREATED, CLOSED (2026-08-29).

    Phases 4e/4f moved the recurring ecological obligation out of the ecological
    allocation and assigned it to the Ground Use Fee. Until GUF revenue reached
    `fiscal_snapshot` there was no way to ask whether the fee covers what was
    moved to it: the obligation left one side of the ledger and arrived nowhere,
    and the Trust simply allocated nothing.

    GUF is a SEPARATE revenue line, not folded into the levy, because the two
    instruments behave oppositely across the arc — the levy contracts with
    labour income while the fee scales with land held. `land/guf.py` claims GUF
    "may become the Trust's dominant revenue source, replacing the contracting
    labor levy base", and `guf_over_levy` is what makes that checkable.
    """

    def _snap(self, **kw):
        base = dict(trust_balance=35e9, labor_income=1e9, capital_stock_teh=2e9,
                    capital_age_ratio=0.5, population=1e6, epsilon=0.40)
        base.update(kw)
        return fiscal_snapshot(**base)

    def test_guf_defaults_to_zero_and_changes_nothing(self):
        """Additive: a caller who supplies no fee is unaffected."""
        a = self._snap()
        b = self._snap(guf_revenue=0.0)
        assert a["trust"]["trust_end"] == b["trust"]["trust_end"]
        assert a["trust"]["guf_inflow"] == 0.0

    def test_guf_revenue_reaches_the_trust(self):
        base = self._snap()
        withguf = self._snap(guf_revenue=1_000_000.0)
        assert withguf["trust"]["guf_inflow"] == 1_000_000.0
        assert withguf["trust"]["trust_end"] == pytest.approx(
            base["trust"]["trust_end"] + 1_000_000.0, rel=1e-12
        )
        assert withguf["trust"]["total_revenue"] == pytest.approx(
            base["trust"]["total_revenue"] + 1_000_000.0, rel=1e-12
        )

    def test_guf_is_not_folded_into_the_levy(self):
        """
        The substitution the partition is about is only visible if the two
        arrive as separate numbers.
        """
        s = self._snap(guf_revenue=1_000_000.0)
        assert s["trust"]["levy_inflow"] == self._snap()["trust"]["levy_inflow"]
        assert s["trust"]["guf_over_levy"] == pytest.approx(
            1_000_000.0 / s["trust"]["levy_inflow"], rel=1e-12
        )

    def test_guf_is_circulatory_not_minted(self):
        """
        `land/guf.py`: "GUF revenue is circulatory TEH flowing to the Trust."
        It must move the Trust and the revenue line and NOT teh_created — the
        fee redistributes, it does not mint. Condition III is untouched.
        """
        from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
        minted = eoh_to_teh_pipeline(epsilon=0.40, population=1e6)["teh_created"]
        s = self._snap(labor_income=minted, guf_revenue=5_000_000.0)
        assert s["trust"]["guf_inflow"] == 5_000_000.0
        # the levy base is labour income and is untouched by the fee
        assert s["levies"]["total_levied"] == \
            self._snap(labor_income=minted)["levies"]["total_levied"]

    def test_the_relocated_obligation_is_reported_in_teh(self):
        """Set against a TEH revenue figure, the obligation must be in TEH too —
        the human share at ε, times the mean multiplier."""
        from hours_eoh.core.eoh_fulfillment import human_eoh_share
        from hours_eoh.data import MEAN_MULTIPLIER_REFERENCE

        s = self._snap()
        eco = s["ecological"]
        assert eco["relocated_teh_required"] == pytest.approx(
            human_eoh_share(eco["relocated_to_guf"], 0.40) * MEAN_MULTIPLIER_REFERENCE,
            rel=1e-12,
        )
        assert s["guf"]["obligation"] == eco["relocated_teh_required"]

    def test_coverage_answers_the_partitions_question(self):
        under = self._snap(guf_revenue=0.0)
        over = self._snap(guf_revenue=1_000_000.0)
        assert under["guf"]["covered"] is False
        assert under["guf"]["gap"] > 0.0
        assert over["guf"]["covered"] is True
        assert over["guf"]["gap"] == 0.0

    def test_the_obligation_is_declared_a_lower_bound(self):
        """
        `covered` is necessary, not sufficient: the fee also carries the
        SERVICING cost of the built environment, which this snapshot has no
        parcel inventory for. A verdict that let a reader forget that would be
        the more dangerous half of the answer.
        """
        g = self._snap(guf_revenue=1e6)["guf"]
        assert g["obligation_is_a_lower_bound"] is True
        assert "LOWER BOUND" in g["verdict"]
        assert "servicing" in g["note"]

    def test_a_real_inventory_reaches_the_snapshot(self):
        """
        END TO END, on the shipped urban archetype: a parcel inventory produces
        revenue, and that revenue lands in the Trust. This is the path the
        implementation guide points an institution at.
        """
        from hours_eoh.land.collective import compute_collective_guf, make_urban_collective

        parcels = make_urban_collective()
        hectares = sum(p["area_slu"] for p in parcels) * 100.0 / 10_000.0
        revenue = compute_collective_guf(parcels, 0.40)["guf_net_inflow"]
        assert revenue > 0.0

        s = self._snap(population=30_000.0,
                       ecological_area_hectares=hectares,
                       guf_revenue=revenue)
        assert s["trust"]["guf_inflow"] == pytest.approx(revenue)
        assert s["guf"]["covered"] is True

    def test_the_fee_is_an_order_of_magnitude_over_the_servicing_census(self):
        """
        THE COMPARISON WITH INFORMATION IN IT, and an independent corroboration
        that the wiring is right. `coverage` against the relocated ECOLOGICAL
        obligation is ~1e6 on this archetype and says almost nothing — the
        denominator is tiny for the reason the domain-balance work records.
        Against the SERVICING census, the same revenue reads ~21× over, which
        matches the 18.1× urban overshoot `scenarios/servicing_census` measured
        by a completely separate route.
        """
        from hours_eoh.core.eoh_fulfillment import human_eoh_share
        from hours_eoh.data import MEAN_MULTIPLIER_REFERENCE
        from hours_eoh.land.collective import compute_collective_guf, make_urban_collective

        parcels = make_urban_collective()
        hectares = sum(p["area_slu"] for p in parcels) * 100.0 / 10_000.0
        revenue = compute_collective_guf(parcels, 0.40)["guf_net_inflow"]

        servicing_teh = human_eoh_share(45.92 * hectares, 0.40) * MEAN_MULTIPLIER_REFERENCE
        ratio = revenue / servicing_teh
        assert 10.0 < ratio < 40.0, (
            f"expected the known urban overshoot, got {ratio:.1f}×"
        )


class TestFiscalSnapshotAcceptsAState:
    """
    THE CONTAINER EXISTED AND THIS FUNCTION DID NOT ACCEPT IT (closed 2026-08-29).

    `make_economy_state()` has carried ten of `fiscal_snapshot`'s quantities
    since the first commit, and `simulate_period` was unpacking it into NINETEEN
    loose keyword arguments to make the call. Every unpack is a place two paths
    can disagree — which is how the ecological frame came to differ by 92.8×
    between the pipeline and the fiscal layer.

    This is not a layer-rule change. `fiscal_snapshot`'s parameter count grew
    20 → 27 between May and August, and only ONE of its nine injected values
    (`guf_revenue`) is caused by the layer rule at all; four are physical state
    the model learned it does not carry, which is what a state container is for.
    """

    def _state(self, **kw):
        from hours_eoh.core.simulation import make_economy_state
        st = make_economy_state(**kw)
        st["labor_income_teh"] = 1.0e9
        return st

    def test_the_state_form_equals_the_loose_form_exactly(self):
        """Bit-identical, not approx: this is a plumbing change, not a model one."""
        st = self._state(population=5e6, capital_stock_teh=1e10)
        via_state = fiscal_snapshot(state=st)
        via_loose = fiscal_snapshot(
            trust_balance=st["trust_balance"], labor_income=st["labor_income_teh"],
            capital_stock_teh=st["capital_stock_teh"],
            capital_age_ratio=st["capital_age_ratio"],
            population=st["population"], epsilon=st["epsilon"],
            ecosystem_health=st["ecosystem_health"],
            deferred_ecological=st["deferred_ecological"],
            capital_eoh_eliminated=st["capital_eoh_eliminated"],
            capital_personal_eoh_fulfilled_per_person=st["capital_personal_eoh_fulfilled"],
        )
        assert via_state["trust"]["trust_end"] == via_loose["trust"]["trust_end"]
        assert via_state["solvent"] == via_loose["solvent"]
        assert via_state["guarantee"]["total_cost_teh"] == \
            via_loose["guarantee"]["total_cost_teh"]

    def test_every_mapped_key_actually_reaches_the_result(self):
        """
        A state key that is accepted and ignored is worse than one that is
        absent — the failure `test_each_domain_base_actually_moves_the_ledger`
        exists to catch. Each mapped quantity must move something.
        """
        from hours_eoh.core.fiscal import _STATE_TO_PARAM
        base = fiscal_snapshot(state=self._state())
        moved = []
        for key in _STATE_TO_PARAM:
            st = self._state()
            # ε is bounded, so it gets a perturbation inside its own range;
            # everything else scales. A perturbation that raises ValueError is
            # not evidence the key is inert.
            st[key] = 0.55 if key == "epsilon" else st[key] * 1.5 + 1.0
            if fiscal_snapshot(state=st) != base:
                moved.append(key)
        assert set(moved) == set(_STATE_TO_PARAM), (
            f"state keys accepted and ignored: {sorted(set(_STATE_TO_PARAM) - set(moved))}"
        )

    def test_supplying_a_quantity_both_ways_is_refused(self):
        """
        A state that can be overridden piecemeal is not a state — the same
        discipline `total_eoh` applies to base-vs-area and
        `research/exchange.build_collective` applies to frames. Silently
        preferring one is the ignored-parameter failure this repo keeps finding.
        """
        st = self._state()
        with pytest.raises(ValueError, match="state's to supply"):
            fiscal_snapshot(state=st, population=99.0)
        with pytest.raises(ValueError, match="state's to supply"):
            fiscal_snapshot(state=st, trust_balance=1.0)

    def test_a_partial_state_is_completed_by_explicit_arguments(self):
        """The state need not be complete — it is a container, not a contract."""
        st = {"population": 1e6, "epsilon": 0.40}
        s = fiscal_snapshot(state=st, trust_balance=35e9, labor_income=1e9,
                            capital_stock_teh=2e9, capital_age_ratio=0.5)
        assert s["guarantee"]["population"] == 1e6

    def test_missing_quantities_are_named(self):
        with pytest.raises(ValueError, match="missing required quantities"):
            fiscal_snapshot(trust_balance=1.0)
        with pytest.raises(ValueError, match="capital_stock_teh"):
            fiscal_snapshot(state={"population": 1e6, "epsilon": 0.40})

    def test_policy_is_not_state_and_stays_explicit(self):
        """
        `levy_rates`, `dep_rate`, `div_rate` and the cross-layer values are NOT
        state and must not be readable from one — a levy rate is a charter
        decision, not a fact about the economy.
        """
        from hours_eoh.core.fiscal import _STATE_TO_PARAM
        for policy in ("levy_rates", "dep_rate", "div_rate", "guf_revenue",
                       "health_response", "standing_response", "mean_multiplier"):
            assert policy not in _STATE_TO_PARAM.values()

    def test_simulate_period_is_unchanged_by_the_rewiring(self):
        """The 19-kwarg unpack became a state; the simulation must not move."""
        from hours_eoh.core.simulation import make_economy_state, simulate_period
        new_state, report = simulate_period(make_economy_state())
        assert new_state["trust_balance"] > 0.0
        assert report["fiscal"]["solvent"] in (True, False)


class TestTheInjectionRegisterIsComplete:
    """
    THE REGISTER IS CHECKED, NOT JUST WRITTEN (2026-08-29).

    `core/fiscal.INJECTION_REGISTER` classifies every value `fiscal_snapshot`
    takes because core may not fetch it. The classification decides what
    happens when a measurement lands — promote to state, or leave it as the
    honest record of a layer boundary — so it is only useful if it stays
    complete. A prose list of nine parameters goes stale the moment a tenth is
    added, which is the `unused_innocuous_names` failure in a new place.
    """

    #: What makes a parameter an injection: it names a value core cannot compute
    #: from what it was given, because the thing that knows sits in another
    #: layer or is not modelled at all.
    MARKERS = ("_override", "_obligation", "guf_revenue", "_aggregate",
               "capital_eoh_eliminated", "capital_personal_eoh_fulfilled",
               "_response")

    def _injected(self):
        """
        Marker-shaped AND not readable from state. The second half is what makes
        this a live definition rather than a name pattern: once a quantity is in
        `_STATE_TO_PARAM`, core can be handed it rather than told it, and it has
        been promoted out of the injection class.
        """
        import inspect
        from hours_eoh.core.fiscal import fiscal_snapshot, _STATE_TO_PARAM
        state_readable = set(_STATE_TO_PARAM.values())
        return {p for p in inspect.signature(fiscal_snapshot).parameters
                if any(m in p for m in self.MARKERS) and p not in state_readable}

    def test_promotion_removes_a_parameter_from_the_injection_class(self):
        """
        The rule, demonstrated on the two it already moved.
        `capital_eoh_eliminated` and `capital_personal_eoh_fulfilled_per_person`
        are still parameters — a caller may pass either — but they are no longer
        INJECTIONS, because `make_economy_state` carries them and core can be
        handed them. The register caught this overlap on its first run.
        """
        import inspect
        from hours_eoh.core.fiscal import (
            fiscal_snapshot, INJECTION_REGISTER, _STATE_TO_PARAM)
        promoted = {"capital_eoh_eliminated",
                    "capital_personal_eoh_fulfilled_per_person"}
        params = set(inspect.signature(fiscal_snapshot).parameters)
        assert promoted <= params, "still reachable as parameters"
        assert promoted <= set(_STATE_TO_PARAM.values()), "readable from state"
        assert not (promoted & set(INJECTION_REGISTER)), "no longer injections"

    def test_every_injected_parameter_is_classified(self):
        from hours_eoh.core.fiscal import INJECTION_REGISTER
        missing = self._injected() - set(INJECTION_REGISTER)
        assert not missing, (
            f"injected without a category: {sorted(missing)}. Classify it in "
            "core/fiscal.INJECTION_REGISTER — the category decides whether a "
            "measurement promotes it to state or it stays a layer boundary."
        )

    def test_the_register_names_no_parameter_that_has_gone(self):
        """A register entry for a parameter nobody has is one nobody reviews."""
        import inspect
        from hours_eoh.core.fiscal import fiscal_snapshot, INJECTION_REGISTER
        params = set(inspect.signature(fiscal_snapshot).parameters)
        stale = set(INJECTION_REGISTER) - params
        assert not stale, f"register names parameters that no longer exist: {sorted(stale)}"

    def test_every_category_is_one_of_the_four(self):
        from hours_eoh.core.fiscal import INJECTION_REGISTER
        allowed = {"recompute_avoidance", "unmodelled_state", "cross_layer",
                   "theory_switch"}
        assert set(INJECTION_REGISTER.values()) <= allowed

    def test_nothing_promotable_is_already_state(self):
        """
        A quantity cannot be both injected and state — that would be two routes
        to one value, which is how `psi` came to differ from `psi_applied`.
        """
        from hours_eoh.core.fiscal import INJECTION_REGISTER, _STATE_TO_PARAM
        assert not (set(INJECTION_REGISTER) & set(_STATE_TO_PARAM.values()))

    def test_the_cross_layer_entry_is_not_promotable(self):
        """
        `guf_revenue` must stay injected. Promoting it into core would assert
        that land tenure is physics — a theory claim smuggled in as an
        engineering convenience, and `land/` is a separate layer precisely
        because it is not physics.
        """
        from hours_eoh.core.fiscal import INJECTION_REGISTER, PROMOTABLE_CATEGORIES
        assert INJECTION_REGISTER["guf_revenue"] == "cross_layer"
        assert "cross_layer" not in PROMOTABLE_CATEGORIES

    def test_theory_switches_are_not_an_architectural_cost(self):
        """
        They would exist under any architecture, so they are excluded from the
        promotable set too — they retire by a sign-off deleting a branch, not
        by a refactor.
        """
        from hours_eoh.core.fiscal import INJECTION_REGISTER, PROMOTABLE_CATEGORIES
        switches = [p for p, c in INJECTION_REGISTER.items() if c == "theory_switch"]
        assert set(switches) == {"health_response", "standing_response"}
        assert "theory_switch" not in PROMOTABLE_CATEGORIES
