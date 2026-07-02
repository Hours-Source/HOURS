"""
Tests for Coasean Phase 3: Trust/capital dynamics, settlement rules,
discovery seam, and the desire-economy stub.

Covers: simulate_federation(dynamics=True), bilateral_imbalances(),
settlement_check(), exchange_rates(discovery_premium=...),
research/desire.py stub.

Arc tests use KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99] per repo convention.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    COASEAN_IMBALANCE_CEILING, COASEAN_DEPRECIATION_SLOPE,
    CONTESTABILITY_CAPITAL_YIELD_RATE, DEP_RATE, DIV_RATE,
)
from hours_eoh.research.coasean import (
    make_federation,
    exchange_rates,
    bilateral_imbalances,
    settlement_check,
    simulate_federation,
    n1_regression_anchor,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# Regression anchors — Phase 3 must not move Phase 1/2 behavior
# ---------------------------------------------------------------------------

class TestPhase3RegressionAnchors:

    def test_n1_anchor_still_exact(self):
        """The non-negotiable anchor: N=1 reproduces the single ledger exactly."""
        for eps in (0.0, 0.40, 0.99):
            result = n1_regression_anchor(epsilon=eps)
            assert result["pipeline_match"], f"N=1 anchor broken at ε={eps}"
            assert result["teh_created_delta"] == pytest.approx(0.0, abs=1e-6)
            assert result["solvent_match"]

    def test_default_args_reproduce_phase2_records(self):
        """dynamics=False (default): every Phase 2 field is unchanged."""
        traj = [0.20, 0.40, 0.60]
        base = simulate_federation(traj)
        explicit = simulate_federation(traj, dynamics=False, g_priv=0.0, levy_rate=0.0)
        phase2_keys = (
            "period", "epsilon", "n_collectives", "total_teh",
            "mean_teh_per_cap", "all_solvent", "within_inflation",
            "inter_inflation", "system_inflation", "n_exchange_pairs",
        )
        for r_base, r_exp in zip(base, explicit):
            for key in phase2_keys:
                assert r_base[key] == r_exp[key]

    def test_static_run_holds_trust_and_capital_constant(self):
        records = simulate_federation([0.20, 0.40, 0.60])
        for r in records:
            assert r["trust_balance"] == pytest.approx(TRUST_BASE_TEH)
            assert r["capital_stock"] == pytest.approx(CAPITAL_STOCK_DEFAULT)

    def test_exchange_rates_no_premium_identity(self):
        """discovery_premium=None reproduces the parity baseline exactly."""
        fed = make_federation(0.40, n=3, ecosystem_health_schedule=[0.5, 0.7, 0.9])
        assert exchange_rates(fed) == exchange_rates(fed, discovery_premium=None)


# ---------------------------------------------------------------------------
# Trust/capital dynamics (§8.3 Piketty inversion, now testable)
# ---------------------------------------------------------------------------

class TestTrustCapitalDynamics:

    def test_tau_fields_present_in_all_records(self):
        records = simulate_federation([0.20, 0.40], dynamics=True)
        for r in records:
            for key in ("trust_balance", "capital_stock", "tau", "dtau", "piketty_ok"):
                assert key in r

    def test_first_period_has_no_gradient(self):
        records = simulate_federation([0.20, 0.40], dynamics=True)
        assert records[0]["dtau"] is None
        assert records[0]["piketty_ok"] is None
        assert records[1]["dtau"] is not None
        assert records[1]["piketty_ok"] is not None

    def test_zero_levy_with_private_growth_fails_piketty(self):
        """No levy + growing private capital + dividend outflow ⇒ τ falls."""
        records = simulate_federation(
            [0.30, 0.40, 0.50, 0.60], dynamics=True, g_priv=0.05, levy_rate=0.0,
        )
        assert all(r["piketty_ok"] is False for r in records[1:])
        taus = [r["tau"] for r in records]
        assert taus[-1] < taus[0]

    def test_large_levy_passes_piketty(self):
        """A levy big enough to outpace g_priv and the dividend ⇒ dτ ≥ 0.

        At canonical defaults the dividend outflow alone is ~18× automated
        output, so only an unrealistically large levy_rate closes it — set
        capital high enough that output can carry the Trust (K = 10×T)."""
        records = simulate_federation(
            [0.30, 0.40, 0.50, 0.60], dynamics=True, g_priv=0.01, levy_rate=0.9,
            trust_balance=1e9, capital_stock_teh=1e10,
        )
        assert all(r["piketty_ok"] for r in records[1:])

    def test_trust_evolution_equation(self):
        """T_{t+1} = T_t + levy·output − dividend, K_{t+1} = K·(1+g)."""
        traj = [0.40, 0.60]
        g, levy = 0.05, 0.30
        records = simulate_federation(
            traj, dynamics=True, g_priv=g, levy_rate=levy,
        )
        t0, k0 = records[0]["trust_balance"], records[0]["capital_stock"]
        output = traj[0] * k0 * CONTESTABILITY_CAPITAL_YIELD_RATE
        expected_t1 = max(0.0, t0 + levy * output - t0 * DEP_RATE * DIV_RATE)
        assert records[1]["trust_balance"] == pytest.approx(expected_t1)
        assert records[1]["capital_stock"] == pytest.approx(k0 * (1 + g))

    def test_trust_never_goes_negative(self):
        records = simulate_federation(
            [0.10] * 30, dynamics=True, g_priv=0.10, levy_rate=0.0,
            trust_balance=1000.0,
        )
        for r in records:
            assert r["trust_balance"] >= 0.0

    def test_dynamics_at_key_epsilons(self):
        """Arc coverage: dynamics run produces finite records at all key ε."""
        records = simulate_federation(
            KEY_EPSILONS, dynamics=True, g_priv=0.03, levy_rate=0.10,
        )
        assert len(records) == len(KEY_EPSILONS)
        for r in records:
            assert r["tau"] > 0.0
            assert r["total_teh"] >= 0.0


# ---------------------------------------------------------------------------
# Settlement and reserve rules (reconciliation §9-item-4)
# ---------------------------------------------------------------------------

class TestBilateralImbalances:

    def test_balanced_trade_nets_to_empty(self):
        flows = {(0, 1): 500.0, (1, 0): 500.0}
        assert bilateral_imbalances(flows) == {}

    def test_net_exporter_sign_convention(self):
        flows = {(0, 1): 800.0, (1, 0): 300.0}
        net = bilateral_imbalances(flows)
        assert net[(0, 1)] == pytest.approx(500.0)  # 0 is net exporter

    def test_reverse_deficit_is_negative(self):
        flows = {(0, 1): 200.0, (1, 0): 700.0}
        net = bilateral_imbalances(flows)
        assert net[(0, 1)] == pytest.approx(-500.0)

    def test_one_way_flow(self):
        net = bilateral_imbalances({(2, 5): 100.0})
        assert net[(2, 5)] == pytest.approx(100.0)

    def test_multiple_pairs_independent(self):
        flows = {(0, 1): 100.0, (1, 2): 250.0, (2, 1): 50.0}
        net = bilateral_imbalances(flows)
        assert net[(0, 1)] == pytest.approx(100.0)
        assert net[(1, 2)] == pytest.approx(200.0)

    def test_negative_flow_raises(self):
        with pytest.raises(ValueError):
            bilateral_imbalances({(0, 1): -10.0})


class TestSettlementCheck:

    def test_within_ceiling_is_ok(self):
        r = settlement_check(imbalance=400.0, debtor_reserve=1000.0)
        assert r["status"] == "OK"
        assert r["settled_from_reserve"] == 0.0
        assert r["depreciation_factor"] == 1.0

    def test_beyond_ceiling_settles_from_reserve(self):
        r = settlement_check(imbalance=800.0, debtor_reserve=1000.0)
        assert r["status"] == "SETTLEMENT_REQUIRED"
        assert r["settled_from_reserve"] == pytest.approx(800.0)
        assert r["unsettled"] == 0.0
        assert r["depreciation_factor"] == 1.0

    def test_unsettled_excess_depreciates(self):
        """Worked example from the docstring: reserve=1000, imbalance=1500."""
        r = settlement_check(imbalance=1500.0, debtor_reserve=1000.0)
        assert r["settled_from_reserve"] == pytest.approx(1000.0)
        assert r["unsettled"] == pytest.approx(500.0)
        expected = 1.0 / (1.0 + COASEAN_DEPRECIATION_SLOPE * (500.0 / 500.0))
        assert r["depreciation_factor"] == pytest.approx(expected)
        assert r["depreciation_factor"] < 1.0

    def test_depreciation_monotone_in_imbalance(self):
        factors = [
            settlement_check(imb, 1000.0)["depreciation_factor"]
            for imb in (1200.0, 1500.0, 2000.0, 5000.0)
        ]
        for hi, lo in zip(factors, factors[1:]):
            assert lo <= hi

    def test_depreciation_factor_bounded(self):
        r = settlement_check(imbalance=1e9, debtor_reserve=10.0)
        assert 0.0 < r["depreciation_factor"] <= 1.0

    def test_zero_reserve_all_unsettled(self):
        r = settlement_check(imbalance=100.0, debtor_reserve=0.0)
        assert r["status"] == "SETTLEMENT_REQUIRED"
        assert r["settled_from_reserve"] == 0.0
        assert r["unsettled"] == pytest.approx(100.0)
        assert r["depreciation_factor"] < 1.0

    def test_ceiling_uses_constant(self):
        r = settlement_check(imbalance=0.0, debtor_reserve=1000.0)
        assert r["ceiling"] == pytest.approx(COASEAN_IMBALANCE_CEILING * 1000.0)

    def test_negative_inputs_raise(self):
        with pytest.raises(ValueError):
            settlement_check(-1.0, 100.0)
        with pytest.raises(ValueError):
            settlement_check(1.0, -100.0)


# ---------------------------------------------------------------------------
# Discovery seam (reconciliation §3 analog for exchange rates)
# ---------------------------------------------------------------------------

class TestDiscoveryPremium:

    def _fed(self):
        return make_federation(0.40, n=2, ecosystem_health_schedule=[0.6, 0.8])

    def test_premium_scales_parity(self):
        fed = self._fed()
        base = exchange_rates(fed)
        with_prem = exchange_rates(fed, discovery_premium={(0, 1): 0.10})
        assert with_prem[(0, 1)] == pytest.approx(base[(0, 1)] * 1.10)
        assert with_prem[(1, 0)] == pytest.approx(base[(1, 0)])  # untouched pair

    def test_negative_premium_allowed_above_minus_one(self):
        fed = self._fed()
        base = exchange_rates(fed)
        discounted = exchange_rates(fed, discovery_premium={(0, 1): -0.50})
        assert discounted[(0, 1)] == pytest.approx(base[(0, 1)] * 0.50)

    def test_premium_at_or_below_minus_one_raises(self):
        fed = self._fed()
        with pytest.raises(ValueError):
            exchange_rates(fed, discovery_premium={(0, 1): -1.0})

    def test_empty_premium_dict_is_identity(self):
        fed = self._fed()
        assert exchange_rates(fed, discovery_premium={}) == exchange_rates(fed)

    def test_single_collective_still_empty(self):
        fed = make_federation(0.99, n=1)
        assert exchange_rates(fed, discovery_premium={(0, 1): 0.5}) == {}


# ---------------------------------------------------------------------------
# Desire economy stub (reconciliation §9-item-6)
# ---------------------------------------------------------------------------

class TestDesireStub:

    def test_module_imports(self):
        import hours_eoh.research.desire as desire
        assert desire.__doc__ is not None
        assert "§9-item-6" in desire.__doc__

    def test_all_interface_functions_raise_not_implemented(self):
        from hours_eoh.research.desire import (
            want_economy_share, want_price_discovery, want_contestability,
        )
        with pytest.raises(NotImplementedError):
            want_economy_share(0.40)
        with pytest.raises(NotImplementedError):
            want_price_discovery("sculpture-7", [1.0, 2.0], 0.40)
        with pytest.raises(NotImplementedError):
            want_contestability(0.40)

    def test_not_imported_by_other_research_modules(self):
        """Layer hygiene: nothing depends on the stub."""
        import hours_eoh.research.coasean as coasean
        import hours_eoh.research.contestability as contestability
        import inspect
        for mod in (coasean, contestability):
            assert "desire" not in inspect.getsource(mod)
