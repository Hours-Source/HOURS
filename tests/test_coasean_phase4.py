"""
Tests for Coasean Phase 4: two-tier Trust / federation commons (recon. §8.7).

Covers: merge_collectives(), split_collective(), _consolidation_escheat(),
simulate_federation(commons=True) — escheat, tithe, per-collective χ,
conservation, and the Phase 2/3 regression anchors.

Arc tests use KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99] per repo convention.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    COASEAN_INDIVISIBLE_RESERVE_FRACTION,
    CONTESTABILITY_CAPITAL_YIELD_RATE, DEP_RATE, DIV_RATE,
)
from hours_eoh.research.coasean import (
    Collective,
    coasean_collective_count,
    make_federation,
    exchange_rates,
    merge_collectives,
    split_collective,
    _consolidation_escheat,
    simulate_federation,
    n1_regression_anchor,
)
from hours_eoh.research.contestability import (
    commons_seed_required,
    contestability_margin_federated,
    portable_endowment,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]
_POP = 1_000_000.0
_TRUST = TRUST_BASE_TEH
_CAP = CAPITAL_STOCK_DEFAULT
_FRAC = COASEAN_INDIVISIBLE_RESERVE_FRACTION

# Flat-N trajectory: N(ε) = 12 at all three points (verified in a test below).
_FLAT_N_TRAJ = [0.40, 0.405, 0.41]


# ---------------------------------------------------------------------------
# Regression anchors — Phase 4 must not move Phase 1/2/3 behavior
# ---------------------------------------------------------------------------

class TestPhase4RegressionAnchors:

    def test_n1_anchor_still_exact(self):
        """The non-negotiable anchor: N=1 reproduces the single ledger exactly."""
        for eps in (0.0, 0.40, 0.99):
            result = n1_regression_anchor(epsilon=eps)
            assert result["pipeline_match"], f"N=1 anchor broken at ε={eps}"
            assert result["teh_created_delta"] == pytest.approx(0.0, abs=1e-6)
            assert result["solvent_match"]

    def test_defaults_byte_identical_to_phase3(self):
        """Default call vs explicit commons=False: every pre-existing key equal."""
        traj = [0.20, 0.40, 0.60]
        base = simulate_federation(traj, dynamics=True, levy_rate=0.3, g_priv=0.02)
        explicit = simulate_federation(
            traj, dynamics=True, levy_rate=0.3, g_priv=0.02,
            commons=False, commons_tithe=0.0, commons_start=0.0,
        )
        phase3_keys = (
            "period", "epsilon", "n_collectives", "total_teh",
            "mean_teh_per_cap", "all_solvent", "within_inflation",
            "inter_inflation", "system_inflation", "n_exchange_pairs",
            "regime_note", "trust_balance", "capital_stock",
            "tau", "dtau", "piketty_ok",
        )
        for r_base, r_exp in zip(base, explicit):
            for key in phase3_keys:
                assert r_base[key] == r_exp[key], f"{key} moved"

    def test_commons_off_new_keys_neutral(self):
        """commons=False: new keys present with neutral values."""
        records = simulate_federation([0.20, 0.40], dynamics=True, levy_rate=0.3)
        for r in records:
            assert r["commons_balance"] == 0.0
            assert r["commons_tithe_paid"] == 0.0
            assert r["escheat_this_period"] == 0.0
            assert r["commons_floor_coverage"] is None
            assert r["chi_min"] is None
            assert r["chi_marginal_min"] is None
            assert r["chi_worst_collective"] is None
            assert r["chi_status_worst"] is None

    def test_flat_n_trajectory_is_flat(self):
        """Guard the fixture: the anchor trajectory must not cross an N step."""
        counts = {coasean_collective_count(e) for e in _FLAT_N_TRAJ}
        assert len(counts) == 1, f"fixture trajectory crosses N steps: {counts}"

    def test_tithe_zero_no_transition_reproduces_phase3(self):
        """The new anchor: commons=True, tithe=0, flat N == Phase 3 float-exact."""
        kwargs = dict(dynamics=True, levy_rate=0.3, g_priv=0.02)
        base = simulate_federation(_FLAT_N_TRAJ, **kwargs)
        two_tier = simulate_federation(
            _FLAT_N_TRAJ, commons=True, commons_tithe=0.0, **kwargs
        )
        phase3_keys = [k for k in base[0]
                       if not k.startswith(("commons", "chi", "escheat",
                                            "entry_capacity", "exit_financeable"))]
        for r_base, r_two in zip(base, two_tier):
            for key in phase3_keys:
                assert r_base[key] == r_two[key], f"{key} moved"


# ---------------------------------------------------------------------------
# merge_collectives — §8.7 (c)+(d)
# ---------------------------------------------------------------------------

class TestMergeCollectives:

    def _fed(self, epsilon=0.40, n=3, eco=None, caps=None):
        # `caps` supersedes `eco` as the heterogeneity lever: after Phases 4e/4f
        # the ecological domain is health-invariant, so an ecosystem_health
        # schedule makes collectives that are identical in the ledger and every
        # exchange rate comes back exactly 1.0.
        return make_federation(epsilon, n=n, ecosystem_health_schedule=eco,
                               capital_schedule=caps)

    def test_conserves_teh_rate_one(self):
        fed = self._fed()
        result = merge_collectives(fed[0], fed[1], rate=1.0)
        assert result["conserved"], (
            f"TEH not conserved: before={result['teh_before']}, "
            f"after={result['teh_after']}"
        )
        assert result["teh_before"] == pytest.approx(result["teh_after"])

    def test_conserves_teh_rate_not_one(self):
        """Heterogeneous federation: conservation holds in absorber units."""
        fed = self._fed(caps=[1.0e9, 2.0e9, 4.0e9])
        rates = exchange_rates(fed)
        rate = rates[(1, 0)]  # r(absorbed=1 → absorber=0)
        assert rate != 1.0
        result = merge_collectives(fed[0], fed[1], rate=rate)
        assert result["conserved"]

    def test_escheat_equals_indivisible_fraction(self):
        fed = self._fed()
        rate = 1.1
        result = merge_collectives(fed[0], fed[1], rate=rate)
        expected = fed[1].trust_balance * rate * _FRAC
        assert result["escheat_teh"] == pytest.approx(expected)

    def test_population_capital_reserve_additive(self):
        fed = self._fed()
        result = merge_collectives(fed[0], fed[1], rate=1.0)
        m = result["merged"]
        assert m.population == pytest.approx(fed[0].population + fed[1].population)
        assert m.capital_stock == pytest.approx(
            fed[0].capital_stock + fed[1].capital_stock)
        assert m.reserve == pytest.approx(fed[0].reserve + fed[1].reserve)
        assert m.pipeline  # recomputed, valid for further use
        assert m.fiscal

    def test_epsilon_mismatch_raises(self):
        a = make_federation(0.40, n=2)[0]
        b = make_federation(0.60, n=2)[0]
        with pytest.raises(ValueError, match="epsilon mismatch"):
            merge_collectives(a, b)

    def test_nonpositive_rate_raises(self):
        fed = self._fed()
        with pytest.raises(ValueError, match="rate"):
            merge_collectives(fed[0], fed[1], rate=0.0)
        with pytest.raises(ValueError, match="rate"):
            merge_collectives(fed[0], fed[1], rate=-1.0)


# ---------------------------------------------------------------------------
# split_collective — §8.7 (c)+(d)
# ---------------------------------------------------------------------------

class TestSplitCollective:

    def _parent(self, epsilon=0.40):
        return make_federation(epsilon, n=1)[0]

    def test_conserves_teh(self):
        parent = self._parent()
        result = split_collective(parent, [0.5, 0.5])
        total = sum(s.trust_balance for s in result["successors"])
        assert total + result["escheat_teh"] == pytest.approx(parent.trust_balance)
        assert result["conserved"]

    def test_escheat_on_split(self):
        parent = self._parent()
        result = split_collective(parent, [0.3, 0.7])
        assert result["escheat_teh"] == pytest.approx(parent.trust_balance * _FRAC)

    def test_fraction_validation_raises(self):
        parent = self._parent()
        with pytest.raises(ValueError, match="sum to 1"):
            split_collective(parent, [0.5, 0.6])
        with pytest.raises(ValueError, match="> 0"):
            split_collective(parent, [1.5, -0.5])
        with pytest.raises(ValueError, match="at least 2"):
            split_collective(parent, [1.0])

    def test_successors_split_by_fractions(self):
        parent = self._parent()
        result = split_collective(parent, [0.25, 0.75])
        s0, s1 = result["successors"]
        assert s0.population == pytest.approx(parent.population * 0.25)
        assert s1.population == pytest.approx(parent.population * 0.75)
        assert s1.trust_balance == pytest.approx(3.0 * s0.trust_balance)

    def test_split_then_merge_creates_zero_teh(self):
        """Round trip: total trust + total escheats is conserved throughout."""
        parent = self._parent()
        split = split_collective(parent, [0.5, 0.5])
        s0, s1 = split["successors"]
        merge = merge_collectives(s0, s1, rate=1.0)
        final_total = (
            merge["merged"].trust_balance
            + merge["escheat_teh"]
            + split["escheat_teh"]
        )
        assert final_total == pytest.approx(parent.trust_balance)

    def test_sim_escheat_matches_explicit_merges(self):
        """_consolidation_escheat ≡ sequential merge_collectives(rate=1)."""
        n_prev, n_new = 12, 8
        fed = make_federation(0.40, n=n_prev)
        # Merge the last (n_prev - n_new) collectives into survivors, one each.
        explicit_escheat = 0.0
        for i in range(n_prev - n_new):
            result = merge_collectives(fed[i], fed[n_new + i], rate=1.0)
            explicit_escheat += result["escheat_teh"]
        aggregate = _consolidation_escheat(_TRUST, n_prev, n_new)
        assert aggregate == pytest.approx(explicit_escheat)

    def test_consolidation_escheat_no_transition_is_zero(self):
        assert _consolidation_escheat(_TRUST, 12, 12) == 0.0

    def test_consolidation_escheat_capped(self):
        """Fragmentation with d > n_prev cannot escheat more than the total
        indivisible share."""
        escheat = _consolidation_escheat(_TRUST, 1, 20)
        assert escheat <= _TRUST * _FRAC + 1e-6


# ---------------------------------------------------------------------------
# Commons tier dynamics — §8.7 (a)
# ---------------------------------------------------------------------------

class TestCommonsTier:

    def test_tithe_routes_levy(self):
        """Hand-verify one dynamics step: T_{t+1} = T + levy·(1−tithe) − dividend
        (levy − tithe·levy = levy·(1−tithe)); commons_{t+1} = commons + tithe·levy."""
        eps = 0.405  # flat N vs 0.40 — no escheat in the second period
        levy_rate, tithe = 0.3, 0.05
        records = simulate_federation(
            [0.40, eps], dynamics=True, levy_rate=levy_rate,
            commons=True, commons_tithe=tithe,
        )
        automated_output = 0.40 * _CAP * CONTESTABILITY_CAPITAL_YIELD_RATE
        levy_revenue = levy_rate * automated_output
        tithe_paid = tithe * levy_revenue
        dividend = _TRUST * DEP_RATE * DIV_RATE
        assert records[0]["commons_tithe_paid"] == pytest.approx(tithe_paid)
        assert records[1]["trust_balance"] == pytest.approx(
            _TRUST + levy_revenue - tithe_paid - dividend)
        assert records[1]["commons_balance"] == pytest.approx(tithe_paid)

    def test_escheat_on_consolidation(self):
        """N 12 → 8 across ε 0.40 → 0.60: escheat = 4·(T/12)·frac."""
        records = simulate_federation([0.40, 0.60], commons=True)
        assert records[0]["n_collectives"] == 12
        assert records[1]["n_collectives"] == 8
        expected = 4 * (_TRUST / 12) * _FRAC
        assert records[1]["escheat_this_period"] == pytest.approx(expected)
        assert records[1]["commons_balance"] == pytest.approx(expected)
        assert records[1]["trust_balance"] == pytest.approx(_TRUST - expected)

    def test_conservation_static_run(self):
        """dynamics=False across the arc: trust + commons constant at every
        period — escheat is circulatory (§8.7d), not destruction."""
        traj = [0.0, 0.20, 0.40, 0.60, 0.80, 0.99]
        records = simulate_federation(traj, commons=True)
        for r in records:
            assert r["trust_balance"] + r["commons_balance"] == pytest.approx(
                _TRUST), f"conservation broken at period {r['period']}"

    def test_commons_floor_coverage_definition(self):
        """coverage == commons / (S(ε)·population), S via portable_endowment."""
        records = simulate_federation(
            [0.40, 0.60], commons=True, commons_start=1e9)
        r = records[0]
        s = portable_endowment(0.40, _POP, _TRUST)["guarantee_per_person"]
        assert r["commons_floor_coverage"] == pytest.approx(1e9 / (s * _POP))

    def test_tau_includes_commons_escheat_neutral(self):
        """Escheat alone (no dynamics) never moves τ — a pure intra-commons
        transfer (§8.3: τ counts total commonized capital)."""
        traj = [0.40, 0.60, 0.80]
        base = simulate_federation(traj)
        two_tier = simulate_federation(traj, commons=True)
        for r_base, r_two in zip(base, two_tier):
            assert r_two["tau"] == pytest.approx(r_base["tau"])
            if r_two["piketty_ok"] is not None:
                assert r_two["piketty_ok"] == r_base["piketty_ok"]

    def test_commons_start_param(self):
        records = simulate_federation([0.40], commons=True, commons_start=5e9)
        assert records[0]["commons_balance"] == pytest.approx(5e9)


# ---------------------------------------------------------------------------
# Per-collective χ — §8.7 / §8.1 at the collective level
# ---------------------------------------------------------------------------

class TestPerCollectiveChi:

    def test_keys_and_ordering(self):
        records = simulate_federation([0.40], commons=True)
        r = records[0]
        assert r["chi_marginal_min"] <= r["chi_min"]
        assert 0 <= r["chi_worst_collective"] < r["n_collectives"]
        assert r["chi_status_worst"] in ("OK", "WARN", "CRIT")

    def test_matches_direct_computation(self):
        """The worst collective's recorded χ equals a direct margin call."""
        records = simulate_federation([0.40], commons=True)
        r = records[0]
        n = r["n_collectives"]
        direct = contestability_margin_federated(
            0.40,
            collective_trust=_TRUST / n,
            collective_population=_POP / n,
            federation_population=_POP,
        )
        # Symmetric equal split: every collective is the worst collective.
        assert r["chi_min"] == pytest.approx(direct["chi"])
        assert r["chi_marginal_min"] == pytest.approx(direct["chi_marginal"])

    def test_chi_at_key_epsilons(self):
        """Meaningful values and valid statuses across the arc; the honest
        adversarial finding: marginal χ is CRIT at ε=0.99 increasing_returns."""
        for eps in KEY_EPSILONS:
            records = simulate_federation([eps], commons=True)
            r = records[0]
            assert r["chi_min"] > 0.0 and r["chi_min"] < float("inf")
            assert r["chi_marginal_min"] > 0.0
            assert r["chi_status_worst"] in ("OK", "WARN", "CRIT")
        final = simulate_federation([0.99], commons=True)[0]
        assert final["chi_status_worst"] == "CRIT", (
            "expected the adversarial finding at ε=0.99; report, don't tune")

    def test_replicable_regime_improves_chi(self):
        adversarial = simulate_federation([0.90], commons=True)[0]
        replicable = simulate_federation(
            [0.90], commons=True, regime="replicable")[0]
        assert replicable["chi_marginal_min"] > adversarial["chi_marginal_min"]


# ---------------------------------------------------------------------------
# Phase 4b: contestability closure (proposed §8.8) — commons dividend,
# entry underwriting, combined invariant
# ---------------------------------------------------------------------------

class TestPhase4bClosure:

    _ARC = [round(0.05 * i, 2) for i in range(20)] + [0.99]
    _DYN = dict(dynamics=True, g_priv=0.02, levy_rate=0.20, commons=True)

    def test_dividend_off_is_phase4_float_exact(self):
        """commons_dividend=False must not move any Phase 4 value."""
        base = simulate_federation(self._ARC, **self._DYN)
        off = simulate_federation(self._ARC, **self._DYN, commons_dividend=False)
        for rb, ro in zip(base, off):
            for key in ("chi_min", "chi_marginal_min", "commons_balance",
                        "trust_balance", "tau"):
                assert rb[key] == ro[key], f"{key} moved with dividend off"
            assert ro["commons_dividend_paid"] == 0.0

    def test_new_keys_neutral_without_commons(self):
        r = simulate_federation([0.40])[0]
        assert r["commons_dividend_paid"] == 0.0
        assert r["entry_capacity"] is None
        assert r["exit_financeable"] is None

    def test_entry_capacity_reported_with_commons(self):
        """M2 metrics are stock properties: present even without the
        dividend policy."""
        records = simulate_federation(self._ARC, **self._DYN)
        for r in records:
            assert r["entry_capacity"] is not None
            assert r["exit_financeable"] is not None

    def test_dividend_outflow_conserves(self):
        """C_{t+1} = C_t + tithe − dividend (no transition): the commons
        dividend is circulatory, mirroring collective trust dividends."""
        records = simulate_federation(
            _FLAT_N_TRAJ, **self._DYN, commons_dividend=True,
            commons_start=1e9)
        for prev, curr in zip(records, records[1:]):
            expected = (prev["commons_balance"] + prev["commons_tithe_paid"]
                        - prev["commons_dividend_paid"])
            assert curr["commons_balance"] == pytest.approx(expected)

    def test_dividend_raises_marginal_chi(self):
        base = simulate_federation(self._ARC, **self._DYN)
        div = simulate_federation(self._ARC, **self._DYN, commons_dividend=True)
        # After escheat has fed the commons, the universal dividend must
        # strictly improve the worst marginal member's position.
        for rb, rd in zip(base[2:], div[2:]):
            assert rd["chi_marginal_min"] > rb["chi_marginal_min"]

    def test_combined_invariant_holds_with_seed(self):
        """The closure result: seeded commons + dividend policy →
        exit financeable at EVERY period of the canonical adversarial arc."""
        records = simulate_federation(
            self._ARC, **self._DYN, commons_dividend=True,
            commons_start=commons_seed_required())
        assert all(r["exit_financeable"] for r in records), (
            "combined invariant (χ_marginal ≥ 1 OR entry_capacity ≥ 1) "
            "must hold across the arc with the derived seed")

    def test_unseeded_commons_leaves_period_zero_uncovered(self):
        """Honest boundary, and it WORSENED with the 2026-08-06 reprice.

        Before: without the seed, ε=0 relied on χ_marginal alone, and that held
        (χ_marginal ≥ 1). After repricing PERSONAL_EOH_BASE 1500 → 1000 the
        sufficiency floor — which IS the tenure-0 member's whole portable
        endowment — no longer covers K_entry, so χ_marginal is 0.886 and the
        commons arm still starts at capacity 0. Period zero is now uncovered by
        BOTH arms unless the commons is seeded, which sharpens rather than
        softens the case for the §8.8 M2 seed.
        """
        records = simulate_federation(
            self._ARC, **self._DYN, commons_dividend=True)
        assert records[0]["entry_capacity"] == 0.0
        assert records[0]["chi_marginal_min"] < 1.0
        # Both arms fail at period zero without a seed — the gap is now real,
        # where before the reprice χ_marginal covered it on its own.
        assert records[0]["exit_financeable"] is False
        # And the seed closes it, which is the point of the M2 mechanism.
        seeded = simulate_federation(
            self._ARC, **self._DYN, commons_dividend=True,
            commons_start=commons_seed_required())
        assert seeded[0]["exit_financeable"] is True

    def test_key_epsilon_arc_values_meaningful(self):
        for eps in KEY_EPSILONS:
            r = simulate_federation(
                [eps], commons=True, commons_dividend=True,
                commons_start=commons_seed_required())[0]
            assert r["entry_capacity"] is not None and r["entry_capacity"] >= 0.0
            assert r["chi_marginal_min"] > 0.0
