"""
Tests for hours_eoh/research/contestability.py.

Arc tests use KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99] following the
codebase-wide convention for four-point automation-arc coverage.
"""

from __future__ import annotations

import pytest

from hours_eoh.research.contestability import (
    portable_endowment,
    entry_cost,
    contestability_margin,
    commonized_fraction,
    trust_capital_ratio,
    tau_gradient_check,
    min_levy_for_pi,
    chi_arc,
)
from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_K0_TEH, CONTESTABILITY_K_SLOPE,
    CONTESTABILITY_K_FLOOR_FRACTION,
    CONTESTABILITY_CHI_CRIT, CONTESTABILITY_CHI_WARN,
    CONTESTABILITY_PHI_FLOOR, CONTESTABILITY_PHI_EXPONENT,
    CONTESTABILITY_G_PRIV,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]
_POP = 1_000_000.0
_TRUST = TRUST_BASE_TEH
_CAP = CAPITAL_STOCK_DEFAULT


# ---------------------------------------------------------------------------
# TestPortableEndowment
# ---------------------------------------------------------------------------

class TestPortableEndowment:

    def test_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = portable_endowment(eps, _POP, _TRUST)
            assert result["p"] > 0, f"P must be positive at ε={eps}, got {result['p']}"

    def test_required_keys_present(self):
        result = portable_endowment(0.40, _POP, _TRUST)
        assert set(result.keys()) == {
            "p", "guarantee_per_person", "trust_dividend_per_capita",
            "capital_fulfilled_per_person", "epsilon",
        }

    def test_p_higher_at_epsilon_zero_than_epsilon_99(self):
        p0 = portable_endowment(0.0, _POP, _TRUST)["p"]
        p99 = portable_endowment(0.99, _POP, _TRUST)["p"]
        assert p0 > p99, (
            f"P should be higher at ε=0 (full eoh reimbursement) than ε=0.99 "
            f"(machines fill personal EOH). P(0)={p0:.0f}, P(0.99)={p99:.0f}"
        )

    def test_trust_dividend_component_is_positive(self):
        result = portable_endowment(0.40, _POP, _TRUST)
        assert result["trust_dividend_per_capita"] > 0

    def test_capital_fulfilled_zero_at_epsilon_zero(self):
        result = portable_endowment(0.0, _POP, _TRUST)
        assert result["capital_fulfilled_per_person"] == pytest.approx(0.0)

    def test_capital_fulfilled_grows_with_epsilon(self):
        c_lo = portable_endowment(0.40, _POP, _TRUST)["capital_fulfilled_per_person"]
        c_hi = portable_endowment(0.90, _POP, _TRUST)["capital_fulfilled_per_person"]
        assert c_hi > c_lo

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            portable_endowment(1.5, _POP, _TRUST)

    def test_invalid_population_raises(self):
        with pytest.raises(ValueError):
            portable_endowment(0.40, 0.0, _TRUST)


# ---------------------------------------------------------------------------
# TestEntryCost
# ---------------------------------------------------------------------------

class TestEntryCost:

    def test_positive_at_all_key_epsilons_both_regimes(self):
        for eps in KEY_EPSILONS:
            for regime in ["increasing_returns", "replicable"]:
                k = entry_cost(eps, regime)
                assert k > 0, f"K_entry > 0 required at ε={eps} regime={regime}, got {k}"

    def test_increasing_returns_monotone_increasing(self):
        vals = [entry_cost(eps, "increasing_returns") for eps in KEY_EPSILONS]
        for lo, hi in zip(vals, vals[1:]):
            assert hi > lo, f"increasing_returns K_entry must rise: {lo} → {hi}"

    def test_replicable_monotone_decreasing(self):
        vals = [entry_cost(eps, "replicable") for eps in KEY_EPSILONS]
        for lo, hi in zip(vals, vals[1:]):
            assert hi <= lo, f"replicable K_entry must fall: {lo} → {hi}"

    def test_replicable_floor_applied_at_high_epsilon(self):
        k = entry_cost(0.99, "replicable")
        floor = CONTESTABILITY_K0_TEH * CONTESTABILITY_K_FLOOR_FRACTION
        assert k >= floor, f"Replicable floor {floor} not applied at ε=0.99, got {k}"

    def test_both_regimes_equal_at_epsilon_zero(self):
        k_ir = entry_cost(0.0, "increasing_returns")
        k_re = entry_cost(0.0, "replicable")
        assert k_ir == pytest.approx(k_re, rel=1e-9)

    def test_invalid_regime_raises(self):
        with pytest.raises(ValueError, match="regime"):
            entry_cost(0.40, "bad_regime")

    def test_increasing_returns_exceeds_replicable_at_high_epsilon(self):
        assert entry_cost(0.99, "increasing_returns") > entry_cost(0.99, "replicable")


# ---------------------------------------------------------------------------
# TestContestabilityMargin
# ---------------------------------------------------------------------------

class TestContestabilityMargin:

    def test_required_keys_present(self):
        result = contestability_margin(0.40, _POP, _TRUST)
        assert set(result.keys()) == {
            "chi", "p", "k_entry", "status", "passes", "regime",
            "epsilon", "guarantee_per_person", "trust_dividend_per_capita",
        }

    def test_replicable_passes_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = contestability_margin(eps, _POP, _TRUST, regime="replicable")
            assert result["passes"], (
                f"replicable regime must satisfy χ ≥ 1 at ε={eps}, "
                f"got χ={result['chi']:.3f}"
            )

    def test_increasing_returns_passes_at_epsilon_zero(self):
        result = contestability_margin(0.0, _POP, _TRUST, regime="increasing_returns")
        assert result["passes"], (
            f"χ must be ≥ 1 at ε=0 in increasing_returns, got χ={result['chi']:.3f}"
        )

    def test_increasing_returns_breaches_at_epsilon_99(self):
        result = contestability_margin(0.99, _POP, _TRUST, regime="increasing_returns")
        assert not result["passes"], (
            f"χ must be < 1 at ε=0.99 in increasing_returns (adversarial finding), "
            f"got χ={result['chi']:.3f}"
        )
        assert result["status"] == "CRIT"

    def test_chi_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            for regime in ["increasing_returns", "replicable"]:
                chi = contestability_margin(eps, _POP, _TRUST, regime=regime)["chi"]
                assert chi > 0, f"χ must be positive at ε={eps} regime={regime}"

    def test_status_strings_valid(self):
        valid = {"OK", "WARN", "CRIT"}
        for eps in KEY_EPSILONS:
            status = contestability_margin(eps, _POP, _TRUST)["status"]
            assert status in valid, f"Status {status!r} not in {valid}"

    def test_passes_consistent_with_chi_crit(self):
        for eps in KEY_EPSILONS:
            result = contestability_margin(eps, _POP, _TRUST)
            assert result["passes"] == (result["chi"] >= CONTESTABILITY_CHI_CRIT)

    def test_chi_equals_p_over_k(self):
        result = contestability_margin(0.40, _POP, _TRUST)
        assert result["chi"] == pytest.approx(result["p"] / result["k_entry"], rel=1e-9)


# ---------------------------------------------------------------------------
# TestCommonizedFraction
# ---------------------------------------------------------------------------

class TestCommonizedFraction:

    def test_at_epsilon_zero_equals_phi_floor(self):
        phi = commonized_fraction(0.0)
        assert phi == pytest.approx(CONTESTABILITY_PHI_FLOOR, abs=1e-9)

    def test_at_epsilon_99_approaches_one(self):
        phi = commonized_fraction(0.99)
        assert phi > 0.95, f"φ(0.99) must be > 0.95, got {phi:.4f}"

    def test_monotone_increasing(self):
        vals = [commonized_fraction(eps) for eps in KEY_EPSILONS]
        for lo, hi in zip(vals, vals[1:]):
            assert hi > lo, f"φ must be monotone increasing: {lo} → {hi}"

    def test_in_range_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            phi = commonized_fraction(eps)
            assert CONTESTABILITY_PHI_FLOOR <= phi <= 1.0, (
                f"φ must be in [PHI_FLOOR, 1.0] at ε={eps}, got {phi}"
            )

    def test_invalid_epsilon_raises(self):
        with pytest.raises(ValueError):
            commonized_fraction(1.5)


# ---------------------------------------------------------------------------
# TestTauAndGradient
# ---------------------------------------------------------------------------

class TestTauAndGradient:

    def test_tau_is_ratio(self):
        tau = trust_capital_ratio(100.0, 400.0)
        assert tau == pytest.approx(0.25, abs=1e-12)

    def test_tau_zero_trust_gives_zero(self):
        assert trust_capital_ratio(0.0, 100.0) == pytest.approx(0.0)

    def test_tau_invalid_capital_raises(self):
        with pytest.raises(ValueError):
            trust_capital_ratio(100.0, 0.0)

    def test_gradient_positive_when_trust_grows_faster(self):
        result = tau_gradient_check(
            eps_lo=0.0, eps_hi=0.5,
            trust_lo=100.0, trust_hi=200.0,  # Trust doubles
            cap_lo=100.0, cap_hi=150.0,       # Capital grows slower
        )
        assert result["passes"], f"dτ/dε should be positive, got {result['dtau_deps']:.4f}"
        assert result["dtau_deps"] > 0

    def test_gradient_negative_when_capital_grows_faster(self):
        result = tau_gradient_check(
            eps_lo=0.0, eps_hi=0.5,
            trust_lo=100.0, trust_hi=110.0,   # Trust barely grows
            cap_lo=100.0, cap_hi=500.0,        # Capital booms
        )
        assert not result["passes"], "dτ/dε should be negative (Piketty failure)"
        assert result["dtau_deps"] < 0

    def test_required_keys_present(self):
        result = tau_gradient_check(0.0, 0.5, 100.0, 110.0, 100.0, 200.0)
        assert set(result.keys()) == {"dtau_deps", "tau_lo", "tau_hi", "passes"}

    def test_invalid_eps_order_raises(self):
        with pytest.raises(ValueError):
            tau_gradient_check(0.5, 0.1, 100.0, 110.0, 100.0, 200.0)


# ---------------------------------------------------------------------------
# TestMinLevyForPi
# ---------------------------------------------------------------------------

class TestMinLevyForPi:

    def test_required_keys_present(self):
        result = min_levy_for_pi(0.40, _TRUST, _CAP)
        assert set(result.keys()) == {
            "levy_required_teh", "automated_output_teh",
            "levy_as_fraction_of_automated_output", "feasible", "epsilon",
        }

    def test_levy_required_positive(self):
        for eps in [0.40, 0.90, 0.99]:
            result = min_levy_for_pi(eps, _TRUST, _CAP)
            assert result["levy_required_teh"] > 0

    def test_infeasible_at_epsilon_zero(self):
        result = min_levy_for_pi(0.0, _TRUST, _CAP)
        assert result["feasible"] is False
        assert result["levy_as_fraction_of_automated_output"] is None
        assert result["automated_output_teh"] == pytest.approx(0.0)

    def test_adversarial_finding_infeasible_at_mid_arc(self):
        """At canonical defaults the levy required >> automated output (adversarial finding)."""
        result = min_levy_for_pi(0.40, _TRUST, _CAP)
        assert result["feasible"] is False, (
            "With default Trust=35B and capital=2B the Piketty-inversion condition "
            "cannot be met by levy alone — this is the adversarial finding."
        )
        assert result["levy_as_fraction_of_automated_output"] > 1.0

    def test_feasible_when_capital_very_large(self):
        """With a very large capital stock the levy fraction drops below 1."""
        large_cap = _TRUST * 100  # Capital much larger than Trust
        result = min_levy_for_pi(0.99, _TRUST, large_cap)
        assert result["feasible"] is True

    def test_levy_fraction_declines_with_larger_capital(self):
        r1 = min_levy_for_pi(0.40, _TRUST, _CAP)
        r2 = min_levy_for_pi(0.40, _TRUST, _CAP * 10)
        assert r2["levy_as_fraction_of_automated_output"] < r1["levy_as_fraction_of_automated_output"]


# ---------------------------------------------------------------------------
# TestChiArc
# ---------------------------------------------------------------------------

class TestChiArc:

    def test_row_count_matches_n_points(self):
        for n in [5, 10, 20]:
            rows = chi_arc(n_points=n)
            assert len(rows) == n

    def test_required_keys_per_row(self):
        rows = chi_arc(n_points=5)
        expected = {
            "epsilon", "p", "k_entry", "chi_population_avg",
            "phi", "tau", "levy_fraction", "levy_feasible", "status",
        }
        for row in rows:
            assert set(row.keys()) == expected

    def test_replicable_arc_all_pass(self):
        rows = chi_arc(n_points=10, regime="replicable")
        for row in rows:
            assert row["chi_population_avg"] >= CONTESTABILITY_CHI_CRIT, (
                f"replicable regime must keep χ ≥ 1 at ε={row['epsilon']:.3f}, "
                f"got χ={row['chi_population_avg']:.3f}"
            )

    def test_increasing_returns_breaches_at_high_epsilon(self):
        rows = chi_arc(n_points=20, regime="increasing_returns")
        last = rows[-1]
        assert last["chi_population_avg"] < CONTESTABILITY_CHI_CRIT, (
            f"increasing_returns must breach χ < 1 at ε=0.99, "
            f"got χ={last['chi_population_avg']:.3f}"
        )

    def test_epsilon_range_covers_zero_to_99(self):
        rows = chi_arc(n_points=10)
        assert rows[0]["epsilon"] == pytest.approx(0.0, abs=1e-9)
        assert rows[-1]["epsilon"] == pytest.approx(0.99, abs=1e-6)

    def test_phi_monotone_across_arc(self):
        rows = chi_arc(n_points=10)
        phis = [r["phi"] for r in rows]
        for lo, hi in zip(phis, phis[1:]):
            assert hi >= lo, f"φ must be non-decreasing across arc: {lo} → {hi}"

    def test_tau_constant_when_trust_and_capital_fixed(self):
        """τ=T/K is constant across ε when trust and capital are fixed inputs."""
        rows = chi_arc(n_points=5, trust_balance=1000.0, capital_stock=400.0)
        for row in rows:
            assert row["tau"] == pytest.approx(2.5, abs=1e-9)
