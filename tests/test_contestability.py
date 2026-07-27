"""
Tests for hours_eoh/research/contestability.py.

Arc tests use KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99] following the
codebase-wide convention for four-point automation-arc coverage.
"""

from __future__ import annotations

import pytest

from hours_eoh.research.contestability import (
    portable_endowment,
    portable_endowment_individual,
    portable_endowment_federated,
    exit_value,
    contestability_margin_federated,
    trust_required_for_chi,
    levy_schedule_for_chi,
    entry_cost,
    entry_underwriting,
    commons_seed_required,
    machine_output_teh,
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
    CONTESTABILITY_MIN_VIABLE_POPULATION,
    CONTESTABILITY_UNDERWRITE_FRACTION,
    DEP_RATE, DIV_RATE,
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
            "chi", "chi_marginal", "p", "p_marginal", "k_entry",
            "status", "status_marginal", "passes", "regime",
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
            "epsilon", "p", "k_entry", "chi_population_avg", "chi_marginal",
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


# ---------------------------------------------------------------------------
# TestPortableEndowmentIndividual — tenure-vested P (§9 open item 7)
# ---------------------------------------------------------------------------

class TestPortableEndowmentIndividual:

    def test_tenure_zero_is_floor_only(self):
        """A new member commands only the unconditional guarantee on exit."""
        for eps in KEY_EPSILONS:
            ind = portable_endowment_individual(eps, tenure_years=0.0,
                                                population=_POP, trust_balance=_TRUST)
            avg = portable_endowment(eps, _POP, _TRUST)
            assert ind["p_individual"] == pytest.approx(avg["guarantee_per_person"])
            assert ind["vested_fraction"] == 0.0

    def test_full_tenure_equals_population_average(self):
        """At tenure ≥ vesting_years, P_ind equals the population-average P."""
        for eps in KEY_EPSILONS:
            ind = portable_endowment_individual(eps, tenure_years=50.0,
                                                population=_POP, trust_balance=_TRUST)
            avg = portable_endowment(eps, _POP, _TRUST)
            assert ind["p_individual"] == pytest.approx(avg["p"])
            assert ind["vested_fraction"] == 1.0

    def test_vesting_is_monotone_in_tenure(self):
        tenures = [0.0, 1.0, 2.5, 5.0, 10.0]
        values = [portable_endowment_individual(0.40, t)["p_individual"]
                  for t in tenures]
        for lo, hi in zip(values, values[1:]):
            assert hi >= lo

    def test_savings_are_additive(self):
        base = portable_endowment_individual(0.40, 2.0)["p_individual"]
        with_savings = portable_endowment_individual(0.40, 2.0, savings=500.0)["p_individual"]
        assert with_savings == pytest.approx(base + 500.0)

    def test_positive_at_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            result = portable_endowment_individual(eps, tenure_years=0.0)
            assert result["p_individual"] > 0

    def test_negative_tenure_raises(self):
        with pytest.raises(ValueError):
            portable_endowment_individual(0.40, tenure_years=-1.0)

    def test_zero_vesting_years_raises(self):
        with pytest.raises(ValueError):
            portable_endowment_individual(0.40, 1.0, vesting_years=0.0)

    def test_negative_savings_raises(self):
        with pytest.raises(ValueError):
            portable_endowment_individual(0.40, 1.0, savings=-10.0)


# ---------------------------------------------------------------------------
# TestChiMarginal — marginal member's contestability margin
# ---------------------------------------------------------------------------

class TestChiMarginal:

    def test_chi_marginal_never_exceeds_population_chi(self):
        for eps in KEY_EPSILONS:
            r = contestability_margin(eps, _POP, _TRUST)
            assert r["chi_marginal"] <= r["chi"] + 1e-12

    def test_chi_marginal_keys_present(self):
        r = contestability_margin(0.40, _POP, _TRUST)
        for key in ("chi_marginal", "p_marginal", "status_marginal"):
            assert key in r

    def test_status_marginal_valid(self):
        for eps in KEY_EPSILONS:
            r = contestability_margin(eps, _POP, _TRUST)
            assert r["status_marginal"] in ("OK", "WARN", "CRIT")

    def test_p_marginal_equals_guarantee(self):
        r = contestability_margin(0.40, _POP, _TRUST)
        assert r["p_marginal"] == pytest.approx(r["guarantee_per_person"])

    def test_chi_arc_includes_chi_marginal(self):
        rows = chi_arc(n_points=5)
        for row in rows:
            assert "chi_marginal" in row
            assert row["chi_marginal"] <= row["chi_population_avg"] + 1e-12


# ---------------------------------------------------------------------------
# TestTrustRequiredForChi — §8.2 inversion
# ---------------------------------------------------------------------------

class TestTrustRequiredForChi:

    def test_closure_at_all_key_epsilons(self):
        """Feeding T_required back into contestability_margin yields χ ≥ target."""
        for eps in KEY_EPSILONS:
            req = trust_required_for_chi(eps, chi_target=1.0, population=_POP)
            trust = max(req["trust_required"], 1.0)  # trust_capital guard
            chi = contestability_margin(eps, _POP, trust)["chi"]
            assert chi >= 1.0 - 1e-9, (
                f"closure failed at ε={eps}: T_req={req['trust_required']:.3e} "
                f"gives χ={chi:.4f}"
            )

    def test_monotone_increasing_in_adversarial_regime(self):
        values = [trust_required_for_chi(eps, regime="increasing_returns")["trust_required"]
                  for eps in [0.0, 0.25, 0.50, 0.75, 0.99]]
        for lo, hi in zip(values, values[1:]):
            assert hi >= lo, f"T_required must rise with ε in increasing_returns: {lo:.3e} → {hi:.3e}"

    def test_zero_when_guarantee_covers_entry(self):
        """Replicable regime at high ε: K_entry collapses below S → no Trust needed."""
        req = trust_required_for_chi(0.99, regime="replicable")
        assert req["trust_required"] == pytest.approx(0.0), (
            f"K_entry={req['k_entry']:.0f} < S={req['guarantee_per_person']:.0f} "
            f"should need no Trust, got {req['trust_required']:.3e}"
        )

    def test_gap_vs_base_sign(self):
        req = trust_required_for_chi(0.99, regime="increasing_returns")
        assert req["gap_vs_base"] == pytest.approx(
            req["trust_required"] - TRUST_BASE_TEH)

    def test_invalid_chi_target_raises(self):
        with pytest.raises(ValueError):
            trust_required_for_chi(0.40, chi_target=0.0)

    def test_higher_target_needs_more_trust(self):
        lo = trust_required_for_chi(0.99, chi_target=1.0)["trust_required"]
        hi = trust_required_for_chi(0.99, chi_target=1.5)["trust_required"]
        assert hi > lo


# ---------------------------------------------------------------------------
# TestLevyScheduleForChi — the derived §8.2 schedule
# ---------------------------------------------------------------------------

class TestLevyScheduleForChi:

    def test_chi_check_holds_at_every_row(self):
        """The schedule's whole point: the invariant holds at every arc point."""
        for regime in ("increasing_returns", "replicable"):
            rows = levy_schedule_for_chi(n_points=10, regime=regime)
            for row in rows:
                assert row["chi_check"] >= 1.0 - 1e-9, (
                    f"{regime}: χ_check={row['chi_check']:.4f} < 1 "
                    f"at ε={row['epsilon']:.3f}"
                )

    def test_trust_target_monotone_in_adversarial_regime(self):
        rows = levy_schedule_for_chi(n_points=10, regime="increasing_returns")
        targets = [r["trust_target"] for r in rows]
        for lo, hi in zip(targets, targets[1:]):
            assert hi >= lo

    def test_trust_target_never_below_start(self):
        rows = levy_schedule_for_chi(n_points=10, trust_start=TRUST_BASE_TEH)
        for row in rows:
            assert row["trust_target"] >= TRUST_BASE_TEH

    def test_adversarial_infeasible_at_defaults(self):
        """Honest adversarial finding: automated output alone cannot fund the
        schedule at canonical defaults. If this ever passes, the calibration
        changed — re-examine, do not silently accept."""
        rows = levy_schedule_for_chi(n_points=10, regime="increasing_returns")
        assert not all(r["feasible"] for r in rows)

    def test_levy_fraction_none_at_epsilon_zero(self):
        rows = levy_schedule_for_chi(n_points=10)
        assert rows[0]["epsilon"] == pytest.approx(0.0, abs=1e-9)
        assert rows[0]["levy_fraction"] is None
        assert rows[0]["feasible"] is False

    def test_required_keys_present(self):
        rows = levy_schedule_for_chi(n_points=3)
        expected = {
            "epsilon", "k_entry", "guarantee_per_person", "trust_target",
            "delta_trust", "dividend_outflow", "levy_required",
            "automated_output", "levy_fraction", "feasible", "chi_check",
            "levy_base",
        }
        for row in rows:
            assert set(row.keys()) == expected

    def test_replicable_cheaper_than_adversarial(self):
        adv = levy_schedule_for_chi(n_points=10, regime="increasing_returns")
        rep = levy_schedule_for_chi(n_points=10, regime="replicable")
        assert sum(r["levy_required"] for r in rep) <= sum(r["levy_required"] for r in adv)

    def test_arc_coverage(self):
        rows = levy_schedule_for_chi(n_points=10)
        assert rows[0]["epsilon"] == pytest.approx(0.0, abs=1e-9)
        assert rows[-1]["epsilon"] == pytest.approx(0.99, abs=1e-6)


# ---------------------------------------------------------------------------
# TestPortableEndowmentFederated — §8.7 two-tier P
# ---------------------------------------------------------------------------

class TestPortableEndowmentFederated:

    def test_identity_with_individual_when_single_ledger(self):
        """federation == collective: P_fed equals P_ind exactly."""
        for eps in KEY_EPSILONS:
            for tenure in (0.0, 2.5, 5.0, 10.0):
                fed = portable_endowment_federated(
                    eps, collective_trust=_TRUST,
                    collective_population=_POP, tenure_years=tenure)
                ind = portable_endowment_individual(eps, tenure_years=tenure)
                assert fed["p_federated"] == pytest.approx(
                    ind["p_individual"]), f"identity broken at ε={eps}"

    def test_marginal_member_floor_only(self):
        """tenure=0: P_fed == S — the person the invariant protects."""
        fed = portable_endowment_federated(
            0.40, collective_trust=_TRUST, collective_population=_POP)
        assert fed["p_federated"] == pytest.approx(fed["guarantee_per_person"])
        assert fed["dividend_vested"] == 0.0

    def test_vesting_monotone_in_tenure(self):
        values = [
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                tenure_years=t)["p_federated"]
            for t in (0.0, 1.0, 2.5, 5.0, 8.0)
        ]
        assert values == sorted(values)
        # Vesting saturates at vesting_years.
        assert values[-1] == pytest.approx(values[-2])

    def test_equal_split_preserves_per_capita_dividend(self):
        """An equal N-way split leaves D_coll unchanged — the federation
        inherits the single-ledger per-capita picture."""
        whole = portable_endowment_federated(
            0.40, collective_trust=_TRUST, collective_population=_POP,
            tenure_years=5.0)
        slice_ = portable_endowment_federated(
            0.40, collective_trust=_TRUST / 12,
            collective_population=_POP / 12,
            federation_population=_POP, tenure_years=5.0)
        assert slice_["dividend_full"] == pytest.approx(whole["dividend_full"])
        assert slice_["p_federated"] == pytest.approx(whole["p_federated"])

    def test_arc_key_epsilons(self):
        """Meaningful, finite output across the arc; S declines with ε."""
        floors = []
        for eps in KEY_EPSILONS:
            fed = portable_endowment_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            assert 0.0 < fed["p_federated"] < float("inf")
            floors.append(fed["guarantee_per_person"])
        assert floors[0] > floors[-1], "S should decline across the arc"

    def test_validation_raises(self):
        with pytest.raises(ValueError, match="tenure_years"):
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                tenure_years=-1.0)
        with pytest.raises(ValueError, match="vesting_years"):
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                vesting_years=0.0)
        with pytest.raises(ValueError, match="savings"):
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                savings=-5.0)
        with pytest.raises(ValueError, match="federation_population"):
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                federation_population=0.0)
        with pytest.raises(ValueError, match="epsilon"):
            portable_endowment_federated(
                1.5, collective_trust=_TRUST, collective_population=_POP)


# ---------------------------------------------------------------------------
# TestExitValue — §8.7 (b)+(d): the boundary crossing
# ---------------------------------------------------------------------------

class TestExitValue:

    def test_rate_one_identity(self):
        """Symmetric collectives: p_exit == S + D_vested + savings."""
        result = exit_value(1476.0, 630.0, savings=100.0, rate=1.0)
        assert result["p_exit"] == pytest.approx(1476.0 + 630.0 + 100.0)

    def test_floor_not_converted(self):
        """Only the account crosses the exchange boundary: p_exit − S scales
        linearly with rate while the floor component is rate-invariant."""
        for rate in (0.5, 0.9, 1.0, 1.3):
            result = exit_value(1476.0, 630.0, rate=rate)
            assert result["floor_component"] == pytest.approx(1476.0)
            assert result["p_exit"] - 1476.0 == pytest.approx(630.0 * rate)

    def test_bad_inputs_raise(self):
        with pytest.raises(ValueError, match="rate"):
            exit_value(1476.0, 630.0, rate=0.0)
        with pytest.raises(ValueError, match="guarantee_per_person"):
            exit_value(-1.0, 630.0)
        with pytest.raises(ValueError, match="dividend_vested"):
            exit_value(1476.0, -1.0)
        with pytest.raises(ValueError, match="savings"):
            exit_value(1476.0, 630.0, savings=-1.0)


# ---------------------------------------------------------------------------
# TestContestabilityMarginFederated — §8.7 per-collective χ
# ---------------------------------------------------------------------------

class TestContestabilityMarginFederated:

    def test_matches_single_ledger_margin(self):
        """federation == collective: key-for-key identity with
        contestability_margin on chi, chi_marginal, p, p_marginal, k_entry."""
        for eps in KEY_EPSILONS:
            fed = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            single = contestability_margin(eps, _POP, _TRUST)
            for key in ("chi", "chi_marginal", "p", "p_marginal", "k_entry"):
                assert fed[key] == pytest.approx(single[key]), (
                    f"{key} diverged at ε={eps}")

    def test_marginal_leq_average(self):
        for eps in KEY_EPSILONS:
            fed = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            assert fed["chi_marginal"] <= fed["chi"]

    def test_statuses_at_key_epsilons(self):
        """Valid statuses across the arc; the adversarial finding survives
        the two-tier reframing: CRIT at ε=0.99 increasing_returns."""
        for eps in KEY_EPSILONS:
            fed = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            assert fed["status"] in ("OK", "WARN", "CRIT")
            assert fed["status_marginal"] in ("OK", "WARN", "CRIT")
        final = contestability_margin_federated(
            0.99, collective_trust=_TRUST, collective_population=_POP)
        assert final["status"] == "CRIT"

    def test_replicable_regime(self):
        adv = contestability_margin_federated(
            0.90, collective_trust=_TRUST, collective_population=_POP)
        rep = contestability_margin_federated(
            0.90, collective_trust=_TRUST, collective_population=_POP,
            regime="replicable")
        assert rep["chi"] > adv["chi"]


# ---------------------------------------------------------------------------
# TestEntryUnderwriting — §8.8 M2 (commons as entry-financier)
# ---------------------------------------------------------------------------

class TestEntryUnderwriting:

    def test_required_keys_present(self):
        result = entry_underwriting(0.40, 1e9)
        assert set(result.keys()) == {
            "entry_capacity", "passes", "deployable", "founding_need",
            "underwrite_per_founder", "k_entry", "min_viable_population",
            "underwrite_fraction", "regime", "epsilon",
        }

    def test_capacity_identity(self):
        """capacity = fraction·C / (min_viable·K_entry) at all key ε."""
        commons = 5e9
        for eps in KEY_EPSILONS:
            result = entry_underwriting(eps, commons)
            expected = (
                CONTESTABILITY_UNDERWRITE_FRACTION * commons
                / (CONTESTABILITY_MIN_VIABLE_POPULATION * entry_cost(eps))
            )
            assert result["entry_capacity"] == pytest.approx(expected)

    def test_empty_commons_cannot_finance(self):
        for eps in KEY_EPSILONS:
            result = entry_underwriting(eps, 0.0)
            assert result["entry_capacity"] == 0.0
            assert result["passes"] is False

    def test_worked_example_high_eps(self):
        """Docstring worked example: ε=0.99, C=1.57e10 → capacity ≈ 337."""
        result = entry_underwriting(0.99, 1.57e10)
        assert result["entry_capacity"] == pytest.approx(337.5, rel=0.01)
        assert result["passes"] is True

    def test_replicable_cheaper_than_adversarial(self):
        commons = 1e9
        adv = entry_underwriting(0.90, commons)
        rep = entry_underwriting(0.90, commons, regime="replicable")
        assert rep["entry_capacity"] > adv["entry_capacity"]

    def test_underwrite_per_founder_capped_at_k_entry(self):
        result = entry_underwriting(0.40, 1e12)  # abundant commons
        assert result["underwrite_per_founder"] == pytest.approx(result["k_entry"])

    def test_validation(self):
        with pytest.raises(ValueError):
            entry_underwriting(0.40, -1.0)
        with pytest.raises(ValueError):
            entry_underwriting(0.40, 1e9, min_viable_population=0.0)
        with pytest.raises(ValueError):
            entry_underwriting(0.40, 1e9, underwrite_fraction=1.5)


# ---------------------------------------------------------------------------
# TestCommonsSeedRequired — §8.8 M2 (ε=0 window)
# ---------------------------------------------------------------------------

class TestCommonsSeedRequired:

    def test_default_value(self):
        """seed = min_viable · k0 / fraction = 5000·1800/0.5 = 1.8e7."""
        assert commons_seed_required() == pytest.approx(
            CONTESTABILITY_MIN_VIABLE_POPULATION * CONTESTABILITY_K0_TEH
            / CONTESTABILITY_UNDERWRITE_FRACTION
        )

    def test_seed_yields_capacity_one_at_eps_zero(self):
        seed = commons_seed_required()
        result = entry_underwriting(0.0, seed)
        assert result["entry_capacity"] == pytest.approx(1.0)
        assert result["passes"] is True

    def test_seed_is_small_vs_trust_base(self):
        """The early-arc gap closes for well under 0.1% of the Trust."""
        assert commons_seed_required() < 0.001 * TRUST_BASE_TEH

    def test_validation(self):
        with pytest.raises(ValueError):
            commons_seed_required(min_viable_population=0.0)
        with pytest.raises(ValueError):
            commons_seed_required(underwrite_fraction=0.0)


# ---------------------------------------------------------------------------
# TestCommonsDividendEndowment — §8.8 M1 (universal unvested dividend)
# ---------------------------------------------------------------------------

class TestCommonsDividendEndowment:

    def test_zero_commons_identity(self):
        """commons_balance=0 reproduces §8.7 values exactly."""
        for eps in KEY_EPSILONS:
            base = portable_endowment_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            with_zero = portable_endowment_federated(
                eps, collective_trust=_TRUST, collective_population=_POP,
                commons_balance=0.0)
            assert base["p_federated"] == with_zero["p_federated"]
            assert with_zero["dividend_commons"] == 0.0
            assert with_zero["p_marginal"] == with_zero["guarantee_per_person"]

    def test_dividend_reaches_tenure_zero(self):
        """The commons dividend is unvested: tenure-0 P rises by D_fed."""
        commons = 5e9
        for eps in KEY_EPSILONS:
            result = portable_endowment_federated(
                eps, collective_trust=_TRUST, collective_population=_POP,
                tenure_years=0.0, commons_balance=commons)
            d_fed = commons * DEP_RATE * DIV_RATE / _POP
            assert result["dividend_commons"] == pytest.approx(d_fed)
            assert result["p_marginal"] == pytest.approx(
                result["guarantee_per_person"] + d_fed)

    def test_negative_commons_raises(self):
        with pytest.raises(ValueError):
            portable_endowment_federated(
                0.40, collective_trust=_TRUST, collective_population=_POP,
                commons_balance=-1.0)

    def test_margin_federated_zero_commons_identity(self):
        for eps in KEY_EPSILONS:
            base = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            zero = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP,
                commons_balance=0.0)
            assert base["chi"] == zero["chi"]
            assert base["chi_marginal"] == zero["chi_marginal"]
            assert zero["entry_capacity"] == 0.0

    def test_margin_federated_commons_raises_marginal_chi(self):
        for eps in KEY_EPSILONS:
            base = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP)
            rich = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP,
                commons_balance=1e10)
            assert rich["chi_marginal"] > base["chi_marginal"]

    def test_exit_financeable_combined_invariant(self):
        """Generous commons: financeable everywhere even where χ_marginal
        is CRIT — the §8.8 combined invariant."""
        for eps in KEY_EPSILONS:
            result = contestability_margin_federated(
                eps, collective_trust=_TRUST, collective_population=_POP,
                commons_balance=1e10)
            assert result["exit_financeable"] is True
        # And with no commons the high-ε points are NOT financeable.
        bare = contestability_margin_federated(
            0.99, collective_trust=_TRUST, collective_population=_POP)
        assert bare["exit_financeable"] is False


# ---------------------------------------------------------------------------
# TestMachineOutputLevyBase — §8.8 M3 (physically-consistent levy base)
# ---------------------------------------------------------------------------

class TestMachineOutputLevyBase:

    def test_zero_at_eps_zero(self):
        assert machine_output_teh(0.0, _POP) == 0.0

    def test_monotone_rising_in_eps(self):
        values = [machine_output_teh(eps, _POP) for eps in KEY_EPSILONS]
        assert values == sorted(values)

    def test_exceeds_static_base_at_high_eps(self):
        """The calibration-artifact finding: the physical base is an order
        of magnitude above the static ε·K·yield base at high ε."""
        eps = 0.99
        static = eps * _CAP * 0.10  # CONTESTABILITY_CAPITAL_YIELD_RATE
        physical = machine_output_teh(eps, _POP)
        assert physical > 10.0 * static

    def test_levy_schedule_invalid_base_raises(self):
        with pytest.raises(ValueError):
            levy_schedule_for_chi(n_points=3, levy_base="bogus")

    def test_levy_schedule_base_echoed(self):
        rows = levy_schedule_for_chi(n_points=3, levy_base="machine_output")
        assert all(r["levy_base"] == "machine_output" for r in rows)

    def test_machine_base_no_worse_than_capital_yield(self):
        """Same levy_required, larger base → fractions weakly smaller and
        feasibility weakly better at every ε > 0."""
        cap = levy_schedule_for_chi(n_points=10)
        mach = levy_schedule_for_chi(n_points=10, levy_base="machine_output")
        for rc, rm in zip(cap, mach):
            assert rm["levy_required"] == pytest.approx(rc["levy_required"])
            if rc["levy_fraction"] is not None and rm["levy_fraction"] is not None:
                assert rm["levy_fraction"] <= rc["levy_fraction"]

    def test_chi_check_holds_under_machine_base(self):
        rows = levy_schedule_for_chi(n_points=10, levy_base="machine_output")
        for r in rows:
            assert r["chi_check"] >= 1.0 - 1e-9
