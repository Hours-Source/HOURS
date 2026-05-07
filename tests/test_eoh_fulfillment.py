"""
Tests for hours_eoh.core.eoh_fulfillment

Covers: human_eoh_share, registered_eoh, teh_created, teh_supply,
capital_writedown, human_eoh_per_domain, eoh_to_teh_pipeline.
"""

import math
import pytest

from hours_eoh.core.eoh_fulfillment import (
    human_eoh_share,
    registered_eoh,
    teh_created,
    capital_writedown,
    teh_supply,
    human_eoh_per_domain,
    eoh_to_teh_pipeline,
)
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.registration import (
    personal_eoh_registration_share,
    knowledge_eoh_registration_share,
    total_registration_share,
)
from hours_eoh.data import CAPITAL_STOCK_DEFAULT

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ===========================================================================
# human_eoh_share
# ===========================================================================

class TestHumanEohShare:

    def test_full_at_zero_epsilon(self):
        """At ε=0: all EOH requires human labor."""
        total = 1_000_000.0
        human = human_eoh_share(total, epsilon=0.0)
        assert human == pytest.approx(total)

    def test_decreases_with_epsilon(self):
        """Human-labor EOH decreases with ε."""
        total = 1_000_000.0
        h0   = human_eoh_share(total, epsilon=0.0)
        h40  = human_eoh_share(total, epsilon=0.40)
        h90  = human_eoh_share(total, epsilon=0.90)
        h99  = human_eoh_share(total, epsilon=0.99)
        assert h0 > h40 > h90 > h99, (
            "Human EOH share must decrease strictly with ε"
        )

    def test_at_099(self):
        """At ε=0.99: only 1% of total EOH requires human labor."""
        total = 1_000_000.0
        human = human_eoh_share(total, epsilon=0.99)
        assert human == pytest.approx(total * 0.01)

    def test_rejects_invalid_epsilon(self):
        with pytest.raises(ValueError):
            human_eoh_share(1000.0, epsilon=1.5)


# ===========================================================================
# registered_eoh
# ===========================================================================

class TestRegisteredEoh:

    def test_zero_for_household(self):
        """Self-care and household EOH produce zero TEH.

        Household EOH has registration_share=0.0 → registered_eoh=0 → teh_created=0.
        """
        household_human_eoh = 500_000.0
        reg_eoh = registered_eoh(household_human_eoh, registration_share=0.0)
        assert reg_eoh == 0.0
        teh = teh_created(reg_eoh, mean_multiplier=2.10)
        assert teh == 0.0

    def test_scales_with_registration_share(self):
        human = 1_000_000.0
        half_registered  = registered_eoh(human, registration_share=0.50)
        full_registered  = registered_eoh(human, registration_share=1.00)
        assert half_registered == pytest.approx(500_000.0)
        assert full_registered == pytest.approx(1_000_000.0)

    def test_rejects_invalid_share(self):
        with pytest.raises(ValueError):
            registered_eoh(1000.0, registration_share=1.5)


# ===========================================================================
# teh_created
# ===========================================================================

class TestTehCreated:

    def test_equals_eoh_times_multiplier(self):
        """TEH creation = registered EOH × multiplier rates."""
        reg_eoh = 100.0
        multiplier = 3.0
        teh = teh_created(reg_eoh, multiplier)
        assert teh == pytest.approx(300.0), (
            "100 EOH at 3.0× multiplier should create 300 TEH"
        )

    def test_mission_statement_example(self):
        """Mission Statement example: '100 EOH ... at a 3.0 multiplier creates 300 TEH'."""
        assert teh_created(100.0, 3.0) == pytest.approx(300.0)

    def test_rejects_submultiplier(self):
        with pytest.raises(ValueError):
            teh_created(100.0, mean_multiplier=0.5)


# ===========================================================================
# teh_supply and capital_writedown
# ===========================================================================

class TestTehSupply:

    def test_equals_created_minus_destroyed(self):
        """TEH supply = cumulative creation - cumulative destruction."""
        created   = 10_000_000.0
        destroyed =  4_000_000.0
        supply = teh_supply(created, destroyed)
        assert supply == pytest.approx(6_000_000.0)

    def test_zero_when_all_destroyed(self):
        assert teh_supply(1_000.0, 1_000.0) == pytest.approx(0.0)

    def test_raises_on_ledger_violation(self):
        """Destroyed > Created is impossible — must raise ValueError."""
        with pytest.raises(ValueError, match="Ledger violation"):
            teh_supply(1_000.0, 1_001.0)


class TestCapitalWritedown:

    def test_positive_at_all_epsilons(self):
        capital = 2_000_000_000.0
        for eps in KEY_EPSILONS:
            result = capital_writedown(capital, epsilon=eps)
            assert result > 0
            assert math.isfinite(result)

    def test_decreases_with_epsilon(self):
        """Better monitoring at higher ε → fewer catastrophic write-downs."""
        capital = 2_000_000_000.0
        wd_0  = capital_writedown(capital, failure_rate=0.005, epsilon=0.0)
        wd_90 = capital_writedown(capital, failure_rate=0.005, epsilon=0.90)
        assert wd_0 > wd_90


# ===========================================================================
# human_eoh_per_domain
# ===========================================================================

class TestHumanEohPerDomain:

    def test_human_fraction_applied_to_each_domain(self):
        eoh = total_eoh(0.40)
        result = human_eoh_per_domain(eoh, epsilon=0.40)
        for domain in ("personal", "infrastructure", "ecological", "knowledge"):
            assert result[domain] == pytest.approx(eoh[domain] * 0.60, rel=1e-9)

    def test_total_equals_sum_of_domains(self):
        eoh = total_eoh(0.40)
        result = human_eoh_per_domain(eoh, epsilon=0.40)
        domains = ("personal", "infrastructure", "ecological", "knowledge")
        assert result["total"] == pytest.approx(sum(result[d] for d in domains))

    def test_zero_epsilon_returns_full_eoh(self):
        eoh = total_eoh(0.0)
        result = human_eoh_per_domain(eoh, epsilon=0.0)
        assert result["personal"] == pytest.approx(eoh["personal"])

    def test_high_epsilon_reduces_all_domains(self):
        eoh = total_eoh(0.90)
        result = human_eoh_per_domain(eoh, epsilon=0.90)
        for domain in ("personal", "infrastructure", "ecological", "knowledge"):
            assert result[domain] < eoh[domain]

    def test_result_keys(self):
        eoh = total_eoh(0.40)
        result = human_eoh_per_domain(eoh, epsilon=0.40)
        for key in ("personal", "infrastructure", "ecological", "knowledge",
                    "total", "human_fraction", "epsilon"):
            assert key in result


# ===========================================================================
# eoh_to_teh_pipeline — Phase 12 C1 (per-domain registration)
# ===========================================================================

class TestEohToTehPipeline:
    """End-to-end pipeline must chain total_eoh → human_share → registration → TEH."""

    def test_output_keys_present(self):
        result = eoh_to_teh_pipeline(epsilon=0.40)
        for key in ("epsilon", "total_eoh", "eoh_by_domain", "human_eoh",
                    "human_fraction", "registration_share", "registered_eoh",
                    "mean_multiplier", "teh_created"):
            assert key in result, f"Missing key: {key}"

    def test_human_fraction_equals_one_minus_epsilon(self):
        for eps in KEY_EPSILONS:
            result = eoh_to_teh_pipeline(epsilon=eps)
            assert result["human_fraction"] == pytest.approx(1.0 - eps)

    def test_human_eoh_consistent(self):
        """human_eoh must equal total_eoh × (1 - ε)."""
        result = eoh_to_teh_pipeline(epsilon=0.40)
        assert result["human_eoh"] == pytest.approx(
            result["total_eoh"] * (1.0 - 0.40), rel=1e-6
        )

    def test_teh_created_consistent(self):
        """teh_created must equal registered_eoh × mean_multiplier."""
        result = eoh_to_teh_pipeline(epsilon=0.40, mean_multiplier=2.10)
        assert result["teh_created"] == pytest.approx(
            result["registered_eoh"] * 2.10, rel=1e-6
        )

    def test_domain_breakdown_sums_to_total(self):
        result = eoh_to_teh_pipeline(epsilon=0.40)
        domain_sum = sum(result["eoh_by_domain"].values())
        assert domain_sum == pytest.approx(result["total_eoh"], rel=1e-6)

    def test_teh_positive_for_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = eoh_to_teh_pipeline(epsilon=eps)
            assert result["teh_created"] > 0.0

    def test_registration_share_override(self):
        """Explicit registration_share must be used instead of dynamic computation."""
        result = eoh_to_teh_pipeline(epsilon=0.40, registration_share=0.50)
        expected_teh = result["human_eoh"] * 0.50 * result["mean_multiplier"]
        assert result["teh_created"] == pytest.approx(expected_teh, rel=1e-6)

    def test_capital_eoh_eliminated_passthrough(self):
        """capital_eoh_eliminated must appear in the returned dict."""
        result = eoh_to_teh_pipeline(epsilon=0.40, capital_eoh_eliminated=1_000_000.0)
        assert result["capital_eoh_eliminated"] == pytest.approx(1_000_000.0)

    def test_higher_epsilon_lower_human_eoh(self):
        """Greater automation → less human EOH (holding population fixed)."""
        low  = eoh_to_teh_pipeline(epsilon=0.20, population=1_000_000.0)
        high = eoh_to_teh_pipeline(epsilon=0.80, population=1_000_000.0)
        assert high["human_eoh"] < low["human_eoh"]

    # --- Phase 12 C1: per-domain registration ---

    def test_registration_by_domain_keys_present(self):
        result = eoh_to_teh_pipeline(epsilon=0.40)
        assert "registration_by_domain" in result
        assert "registered_eoh_by_domain" in result
        assert "personal" in result["registration_by_domain"]
        assert "non_personal" in result["registration_by_domain"]

    def test_personal_registration_near_zero_at_eps0(self):
        """At ε=0, personal EOH registration is near-zero (off-ledger subsistence)."""
        result = eoh_to_teh_pipeline(epsilon=0.0)
        pers_share = result["registration_by_domain"]["personal"]
        assert pers_share < 0.05, (
            f"Personal registration at ε=0 should be near-zero, got {pers_share:.4f}"
        )

    def test_personal_registration_high_at_eps99(self):
        """At ε=0.99, personal EOH registration approaches saturation (~0.95)."""
        result = eoh_to_teh_pipeline(epsilon=0.99)
        pers_share = result["registration_by_domain"]["personal"]
        assert pers_share > 0.85, (
            f"Personal registration at ε=0.99 should be high, got {pers_share:.4f}"
        )

    def test_personal_non_personal_share_differ_at_low_epsilon(self):
        """At low ε, personal and non-personal registration shares must differ materially."""
        result = eoh_to_teh_pipeline(epsilon=0.10)
        pers   = result["registration_by_domain"]["personal"]
        non_p  = result["registration_by_domain"]["non_personal"]
        assert non_p > pers + 0.20, (
            f"Non-personal ({non_p:.3f}) should be much higher than personal "
            f"({pers:.3f}) at ε=0.10"
        )

    def test_personal_registration_matches_standalone_function(self):
        """Pipeline personal share must exactly match personal_eoh_registration_share()."""
        for eps in [0.0, 0.40, 0.70, 0.99]:
            result   = eoh_to_teh_pipeline(epsilon=eps)
            expected = personal_eoh_registration_share(eps)
            actual   = result["registration_by_domain"]["personal"]
            assert actual == pytest.approx(expected, rel=1e-9), (
                f"ε={eps}: pipeline personal share {actual} ≠ standalone {expected}"
            )

    def test_registered_eoh_by_domain_sums_to_total(self):
        KEY_EPS_C1 = [0.0, 0.20, 0.40, 0.70, 0.90, 0.99]
        for eps in KEY_EPS_C1:
            result    = eoh_to_teh_pipeline(epsilon=eps)
            domain_sum = (result["registered_eoh_by_domain"]["personal"]
                          + result["registered_eoh_by_domain"]["non_personal"])
            assert domain_sum == pytest.approx(result["registered_eoh"], rel=1e-9), (
                f"ε={eps}: domain sum {domain_sum} ≠ registered_eoh {result['registered_eoh']}"
            )

    def test_teh_created_consistent_with_per_domain_registered(self):
        """teh_created must equal total registered_eoh × multiplier."""
        KEY_EPS_C1 = [0.0, 0.20, 0.40, 0.70, 0.90, 0.99]
        for eps in KEY_EPS_C1:
            result = eoh_to_teh_pipeline(epsilon=eps, mean_multiplier=2.10)
            assert result["teh_created"] == pytest.approx(
                result["registered_eoh"] * 2.10, rel=1e-6
            )

    def test_uniform_override_applies_to_both_domains(self):
        """When registration_share is set, both personal and non_personal use it."""
        result = eoh_to_teh_pipeline(epsilon=0.40, registration_share=0.60)
        assert result["registration_by_domain"]["personal"]     == pytest.approx(0.60)
        assert result["registration_by_domain"]["non_personal"] == pytest.approx(0.60)

    def test_uniform_override_backward_compat(self):
        """Uniform override must produce teh = human_eoh × share × multiplier."""
        result = eoh_to_teh_pipeline(epsilon=0.40, registration_share=0.50)
        expected = result["human_eoh"] * 0.50 * result["mean_multiplier"]
        assert result["teh_created"] == pytest.approx(expected, rel=1e-6)

    def test_personal_registration_override(self):
        """personal_registration_share override applies to personal domain only."""
        default = eoh_to_teh_pipeline(epsilon=0.40)
        override = eoh_to_teh_pipeline(epsilon=0.40, personal_registration_share=0.80)
        # Non-personal should be the same
        assert (override["registration_by_domain"]["non_personal"]
                == pytest.approx(default["registration_by_domain"]["non_personal"]))
        # Personal should use the override
        assert override["registration_by_domain"]["personal"] == pytest.approx(0.80)

    def test_teh_lower_at_eps0_due_to_personal_near_zero(self):
        """At ε=0, TEH is lower with per-domain registration than with uniform composite."""
        per_domain = eoh_to_teh_pipeline(epsilon=0.0)
        uniform    = eoh_to_teh_pipeline(epsilon=0.0, registration_share=0.42)
        assert per_domain["teh_created"] < uniform["teh_created"]

    def test_monotone_personal_registration_across_arc(self):
        """Personal domain registration share must be monotonically non-decreasing."""
        KEY_EPS_C1 = [0.0, 0.20, 0.40, 0.70, 0.90, 0.99]
        shares = [
            eoh_to_teh_pipeline(epsilon=eps)["registration_by_domain"]["personal"]
            for eps in KEY_EPS_C1
        ]
        for i in range(len(shares) - 1):
            assert shares[i] <= shares[i + 1] + 1e-9, (
                f"Personal share not monotone: {shares[i]:.4f} > {shares[i+1]:.4f} "
                f"at ε={KEY_EPS_C1[i]}→{KEY_EPS_C1[i+1]}"
            )

    # --- Phase 14 M5: four-domain registration keys ---

    def test_registration_by_domain_has_four_keys(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.40, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
        )
        rd = result["registration_by_domain"]
        for key in ("personal", "infrastructure", "ecological", "knowledge"):
            assert key in rd, f"Missing key: {key}"

    def test_registered_eoh_by_domain_has_four_keys(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.40, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
        )
        rd = result["registered_eoh_by_domain"]
        for key in ("personal", "infrastructure", "ecological", "knowledge"):
            assert key in rd, f"Missing key: {key}"

    def test_knowledge_registration_lower_than_infra_at_eps040(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.40, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
        )
        rd = result["registration_by_domain"]
        assert rd["knowledge"] < rd["infrastructure"], (
            f"knowledge ({rd['knowledge']:.3f}) should be below infra "
            f"({rd['infrastructure']:.3f}) at ε=0.40"
        )

    def test_knowledge_registration_matches_standalone_function(self):
        for eps in [0.0, 0.40, 0.70, 0.99]:
            result = eoh_to_teh_pipeline(
                epsilon=eps, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
            )
            expected = knowledge_eoh_registration_share(eps)
            assert result["registration_by_domain"]["knowledge"] == pytest.approx(
                expected, rel=1e-9
            ), f"Mismatch at ε={eps}"

    def test_infra_registration_matches_total_registration_share(self):
        for eps in [0.0, 0.40, 0.99]:
            result = eoh_to_teh_pipeline(
                epsilon=eps, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
            )
            expected = total_registration_share(eps)
            assert result["registration_by_domain"]["infrastructure"] == pytest.approx(
                expected, rel=1e-9
            ), f"Infra registration mismatch at ε={eps}"

    def test_non_personal_backward_compat_key_present(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.40, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
        )
        assert "non_personal" in result["registration_by_domain"]
        assert "non_personal" in result["registered_eoh_by_domain"]

    def test_non_personal_equals_sum_of_three_domains(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.50, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
        )
        rd = result["registered_eoh_by_domain"]
        expected_sum = rd["infrastructure"] + rd["ecological"] + rd["knowledge"]
        assert rd["non_personal"] == pytest.approx(expected_sum, rel=1e-9)

    def test_uniform_override_applies_to_knowledge(self):
        result = eoh_to_teh_pipeline(
            epsilon=0.40, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
            registration_share=0.50,
        )
        assert result["registration_by_domain"]["knowledge"] == pytest.approx(0.50)

    def test_all_registration_shares_in_range(self):
        for eps in [0.0, 0.40, 0.70, 0.99]:
            result = eoh_to_teh_pipeline(
                epsilon=eps, population=1_000_000.0, capital_stock=CAPITAL_STOCK_DEFAULT,
            )
            for domain, share in result["registration_by_domain"].items():
                assert 0.0 <= share <= 1.0, (
                    f"Out-of-range registration share for {domain} at ε={eps}: {share}"
                )

    def test_knowledge_registration_grows_with_eps(self):
        shares = [
            eoh_to_teh_pipeline(epsilon=e, population=1e6,
                                 capital_stock=CAPITAL_STOCK_DEFAULT
                                 )["registration_by_domain"]["knowledge"]
            for e in [0.0, 0.30, 0.60, 0.90, 0.99]
        ]
        for i in range(len(shares) - 1):
            assert shares[i + 1] >= shares[i]
