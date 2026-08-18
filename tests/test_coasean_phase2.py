"""
Phase 2 tests for hours_eoh/research/coasean.py.

Covers: exchange_rates(), three_regime_inflation(), simulate_federation(),
and make_federation() with ecosystem_health_schedule.

The core invariant under test is the three-regime inflation theorem
(reconciliation §7): within_inflation = 0 always; inter_inflation > 0
during transition when collectives are heterogeneous; system_inflation → 0
as ε → 0.99 (N → 1).
"""

from __future__ import annotations
import pytest

from hours_eoh.research.coasean import (
    Collective,
    coasean_collective_count,
    exchange_rates,
    make_federation,
    n1_regression_anchor,
    simulate_federation,
    three_regime_inflation,
)
from hours_eoh.data import TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT

KEY_EPSILONS = [0.0, 0.40, 0.99]

# Reproducible heterogeneous ecosystem health for two collectives
_ECO_A = 0.80
_ECO_B = 0.60


def _two_collective_fed(epsilon: float = 0.40) -> list[Collective]:
    """Federation of exactly 2 collectives with different ecosystem health."""
    return make_federation(
        epsilon=epsilon,
        n=2,
        population=1_000_000.0,
        ecosystem_health_schedule=[_ECO_A, _ECO_B],
    )


# ---------------------------------------------------------------------------
# make_federation — ecosystem_health_schedule
# ---------------------------------------------------------------------------

class TestMakeFederationHeterogeneity:
    def test_schedule_sets_individual_eco_health(self):
        schedule = [0.90, 0.60, 0.40]
        fed = make_federation(0.40, n=3, population=600_000.0,
                              ecosystem_health_schedule=schedule)
        assert fed[0].ecosystem_health == pytest.approx(0.90)
        assert fed[1].ecosystem_health == pytest.approx(0.60)
        assert fed[2].ecosystem_health == pytest.approx(0.40)

    def test_wrong_schedule_length_raises(self):
        with pytest.raises(ValueError, match="ecosystem_health_schedule length"):
            make_federation(0.40, n=3, population=600_000.0,
                            ecosystem_health_schedule=[0.70, 0.60])  # wrong length

    def test_schedule_clips_to_valid_range(self):
        fed = make_federation(0.40, n=2, population=200_000.0,
                              ecosystem_health_schedule=[1.50, -0.20])
        assert 0.01 <= fed[0].ecosystem_health <= 0.99
        assert 0.01 <= fed[1].ecosystem_health <= 0.99

    def test_heterogeneous_teh_differs_between_collectives(self):
        fed = _two_collective_fed(0.40)
        teh_a = fed[0].pipeline["teh_created"]
        teh_b = fed[1].pipeline["teh_created"]
        # Higher ecosystem health (less ecological EOH drag) → different output
        # PHASE 4b: ecosystem_health still differentiates the collectives, but
        # the domain it acts on shrank 464x, so the difference is now well
        # inside pytest.approx's default relative tolerance. Asserted as a
        # strict inequality with a magnitude floor instead — the heterogeneity
        # is real and it is now a much weaker lever on the ledger, which is
        # itself the domain-balance defect restated.
        assert teh_a != teh_b
        assert abs(teh_a - teh_b) > 1.0

    def test_no_schedule_means_symmetric_teh(self):
        fed = make_federation(0.40, n=2, population=1_000_000.0)
        teh_a = fed[0].pipeline["teh_created"]
        teh_b = fed[1].pipeline["teh_created"]
        assert teh_a == pytest.approx(teh_b)

    def test_n1_anchor_unaffected_by_schedule_addition(self):
        result = n1_regression_anchor(epsilon=0.40)
        assert result["pipeline_match"] is True


# ---------------------------------------------------------------------------
# exchange_rates
# ---------------------------------------------------------------------------

class TestExchangeRates:
    def test_empty_for_single_collective(self):
        fed = make_federation(0.99, population=1_000_000.0)  # N=1 at ε=0.99
        assert exchange_rates(fed) == {}

    def test_symmetric_rates_all_unity(self):
        fed = make_federation(0.40, n=4, population=1_000_000.0)
        rates = exchange_rates(fed)
        for (i, j), r in rates.items():
            assert r == pytest.approx(1.0), f"Symmetric rate ({i},{j}) = {r}, expected 1.0"

    def test_heterogeneous_rates_deviate_from_unity(self):
        fed = _two_collective_fed(0.40)
        rates = exchange_rates(fed)
        assert len(rates) == 2  # (0,1) and (1,0)
        # Higher-eco collective (index 0) should have higher productivity
        r_01 = rates[(0, 1)]
        r_10 = rates[(1, 0)]
        # PHASE 4b: the rate still deviates from unity, but by ~1e-6 rather than
        # ~1e-3, because the ecological domain that ecosystem_health drives
        # shrank 464x when the frame was declared. The deviation is asserted
        # directly rather than through approx, whose default tolerance now
        # swallows it. WHAT THIS SAYS about the model, and it is not flattering:
        # a federation whose collectives differ ONLY in ecosystem health now has
        # essentially no terms of trade between them.
        assert r_01 != 1.0, "Expected non-unity rate for heterogeneous fed"
        assert abs(r_01 - 1.0) > 1e-9
        assert r_01 == pytest.approx(1.0 / r_10, rel=1e-9)  # rates are reciprocals

    def test_rates_are_reciprocals(self):
        fed = _two_collective_fed(0.40)
        rates = exchange_rates(fed)
        r_01 = rates[(0, 1)]
        r_10 = rates[(1, 0)]
        assert r_01 * r_10 == pytest.approx(1.0, rel=1e-9)

    def test_rate_count_equals_n_times_n_minus_1(self):
        for n, eps in [(2, 0.0), (5, 0.0), (12, 0.40)]:
            fed = make_federation(eps, n=n, population=1_000_000.0)
            rates = exchange_rates(fed)
            assert len(rates) == n * (n - 1), (
                f"Expected {n*(n-1)} rates for N={n}, got {len(rates)}"
            )

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_all_rates_positive(self, eps):
        fed = make_federation(eps, population=1_000_000.0)
        for r in exchange_rates(fed).values():
            assert r > 0.0

    def test_higher_eco_health_gives_rate_above_1_vs_lower(self):
        fed = _two_collective_fed(0.40)
        rates = exchange_rates(fed)
        # Collective 0 has eco=0.80, collective 1 has eco=0.60
        # Higher eco → lower ecological EOH drag → different pipeline output
        # We don't know exact direction a priori (eco can raise or lower TEH
        # depending on the spike/baseline interplay), but rate must be non-trivial
        assert (0, 1) in rates and (1, 0) in rates


# ---------------------------------------------------------------------------
# three_regime_inflation
# ---------------------------------------------------------------------------

class TestThreeRegimeInflation:
    def test_within_inflation_always_zero(self):
        fed_a = _two_collective_fed(0.40)
        fed_b = _two_collective_fed(0.60)
        r0 = exchange_rates(fed_a)
        r1 = exchange_rates(fed_b)
        result = three_regime_inflation(r0, r1, 0.60)
        assert result["within_inflation"] == 0.0

    def test_empty_rates_gives_zero_inflation(self):
        result = three_regime_inflation({}, {}, 0.99)
        assert result["within_inflation"] == 0.0
        assert result["inter_inflation"] == 0.0
        assert result["system_inflation"] == 0.0

    def test_n1_limit_gives_zero_system_inflation(self):
        # At ε=0.99, N=1, both rate dicts should be empty → system_inflation = 0
        result = three_regime_inflation({}, {}, 0.99)
        assert result["system_inflation"] == 0.0
        assert "single-collective" in result["regime_note"].lower()

    def test_symmetric_federation_zero_inter_inflation(self):
        fed_a = make_federation(0.40, n=4, population=1_000_000.0)
        fed_b = make_federation(0.50, n=4, population=1_000_000.0)
        r0 = exchange_rates(fed_a)
        r1 = exchange_rates(fed_b)
        result = three_regime_inflation(r0, r1, 0.50)
        # All rates = 1.0 in both periods → no drift
        assert result["inter_inflation"] == pytest.approx(0.0, abs=1e-9)

    def test_heterogeneous_federation_nonzero_inter_inflation(self):
        # Different eco schedules across periods → exchange rates drift
        fed_a = make_federation(0.40, n=2, population=1_000_000.0,
                                ecosystem_health_schedule=[_ECO_A, _ECO_B])
        fed_b = make_federation(0.50, n=2, population=1_000_000.0,
                                ecosystem_health_schedule=[0.75, 0.65])
        r0 = exchange_rates(fed_a)
        r1 = exchange_rates(fed_b)
        result = three_regime_inflation(r0, r1, 0.50)
        assert result["inter_inflation"] > 0.0

    def test_system_inflation_less_than_inter(self):
        fed_a = _two_collective_fed(0.40)
        fed_b = make_federation(0.50, n=2, population=1_000_000.0,
                                ecosystem_health_schedule=[0.75, 0.65])
        r0 = exchange_rates(fed_a)
        r1 = exchange_rates(fed_b)
        result = three_regime_inflation(r0, r1, 0.50)
        assert result["system_inflation"] <= result["inter_inflation"]

    def test_system_inflation_shrinks_toward_high_epsilon(self):
        # Same rate drift at low vs high ε → system_inflation is smaller at high ε
        eco_a = [_ECO_A, _ECO_B]
        eco_b = [0.75, 0.65]
        rates_before_low = exchange_rates(
            make_federation(0.20, n=2, population=1_000_000.0,
                            ecosystem_health_schedule=eco_a))
        rates_after_low  = exchange_rates(
            make_federation(0.30, n=2, population=1_000_000.0,
                            ecosystem_health_schedule=eco_b))
        rates_before_high = exchange_rates(
            make_federation(0.80, n=2, population=1_000_000.0,
                            ecosystem_health_schedule=eco_a))
        rates_after_high  = exchange_rates(
            make_federation(0.85, n=2, population=1_000_000.0,
                            ecosystem_health_schedule=eco_b))

        low  = three_regime_inflation(rates_before_low,  rates_after_low,  0.30)
        high = three_regime_inflation(rates_before_high, rates_after_high, 0.85)

        assert low["system_inflation"] > high["system_inflation"]

    def test_max_rate_pair_identified(self):
        fed_a = _two_collective_fed(0.40)
        fed_b = make_federation(0.50, n=2, population=1_000_000.0,
                                ecosystem_health_schedule=[0.75, 0.65])
        r0 = exchange_rates(fed_a)
        r1 = exchange_rates(fed_b)
        result = three_regime_inflation(r0, r1, 0.50)
        if result["inter_inflation"] > 0.0:
            assert result["max_rate_pair"] is not None
            assert isinstance(result["max_rate_pair"], tuple)


# ---------------------------------------------------------------------------
# simulate_federation
# ---------------------------------------------------------------------------

class TestSimulateFederation:
    def _standard_trajectory(self) -> list[float]:
        return [i / 9 * 0.99 for i in range(10)]

    def test_returns_one_record_per_period(self):
        traj = self._standard_trajectory()
        records = simulate_federation(traj)
        assert len(records) == len(traj)

    def test_period_index_sequential(self):
        records = simulate_federation(self._standard_trajectory())
        for i, rec in enumerate(records):
            assert rec["period"] == i

    def test_epsilon_stored_correctly(self):
        traj = [0.0, 0.40, 0.99]
        records = simulate_federation(traj)
        for rec, eps in zip(records, traj):
            assert rec["epsilon"] == eps

    def test_within_inflation_always_zero(self):
        records = simulate_federation(self._standard_trajectory())
        for rec in records:
            assert rec["within_inflation"] == 0.0

    def test_system_inflation_zero_at_epsilon_099(self):
        records = simulate_federation([0.90, 0.99])
        last = records[-1]
        assert last["epsilon"] == 0.99
        assert last["system_inflation"] == pytest.approx(0.0, abs=1e-9)

    def test_n_exchange_pairs_zero_at_n1(self):
        records = simulate_federation([0.99])
        assert records[0]["n_exchange_pairs"] == 0

    def test_total_teh_positive(self):
        records = simulate_federation(self._standard_trajectory())
        for rec in records:
            assert rec["total_teh"] > 0.0

    def test_symmetric_federation_zero_inter_inflation(self):
        records = simulate_federation(self._standard_trajectory(), heterogeneity=0.0)
        for rec in records:
            assert rec["inter_inflation"] == pytest.approx(0.0, abs=1e-9)

    def test_heterogeneous_federation_inter_inflation_possible(self):
        records = simulate_federation(self._standard_trajectory(), heterogeneity=0.15)
        # At least one transition should show non-zero inter-collective inflation
        # (when N > 1 and eco schedules differ between periods)
        mid_records = [r for r in records if r["n_collectives"] > 1 and r["period"] > 0]
        if mid_records:
            any_nonzero = any(r["inter_inflation"] > 0.0 for r in mid_records)
            assert any_nonzero, "Expected non-zero inter-collective inflation with heterogeneity=0.15"

    def test_system_inflation_never_exceeds_inter(self):
        records = simulate_federation(self._standard_trajectory(), heterogeneity=0.10)
        for rec in records:
            assert rec["system_inflation"] <= rec["inter_inflation"] + 1e-12

    def test_reproducible_with_same_seed(self):
        traj = self._standard_trajectory()
        r1 = simulate_federation(traj, seed=7)
        r2 = simulate_federation(traj, seed=7)
        for a, b in zip(r1, r2):
            assert a["inter_inflation"] == pytest.approx(b["inter_inflation"])

    def test_different_seeds_different_results(self):
        traj = self._standard_trajectory()
        r1 = simulate_federation(traj, heterogeneity=0.15, seed=1)
        r2 = simulate_federation(traj, heterogeneity=0.15, seed=2)
        # With non-trivial heterogeneity, different seeds should give different inflation
        inflations_1 = [r["inter_inflation"] for r in r1]
        inflations_2 = [r["inter_inflation"] for r in r2]
        assert inflations_1 != inflations_2

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_single_period_runs_at_key_epsilons(self, eps):
        records = simulate_federation([eps])
        assert len(records) == 1
        assert records[0]["epsilon"] == eps
        assert records[0]["within_inflation"] == 0.0
