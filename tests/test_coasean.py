"""
Tests for hours_eoh/research/coasean.py — Coasean collective federation (Phase 1).

Coverage:
  - coasean_collective_count(): arc behavior, monotonicity, floor
  - Collective dataclass: field population, N=1 field identity
  - run_collective_period(): output shape, solvency at arc points
  - make_federation(): N=1 population identity, N>1 population sum, arc coverage
  - n1_regression_anchor(): exact match at ε ∈ {0, 0.40, 0.99}
"""

from __future__ import annotations
import pytest

from hours_eoh.research.coasean import (
    Collective,
    coasean_collective_count,
    make_federation,
    n1_regression_anchor,
    run_collective_period,
)
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    COASEAN_N_MAX,
    TRUST_BASE_TEH,
)

KEY_EPSILONS = [0.0, 0.40, 0.99]


# ---------------------------------------------------------------------------
# coasean_collective_count
# ---------------------------------------------------------------------------

class TestCoaseanCollectiveCount:
    def test_count_at_epsilon_zero_equals_n_max(self):
        assert coasean_collective_count(0.0) == COASEAN_N_MAX

    def test_count_at_epsilon_099_is_1(self):
        assert coasean_collective_count(0.99) == 1

    def test_count_never_below_1(self):
        for eps in KEY_EPSILONS + [0.10, 0.50, 0.90]:
            assert coasean_collective_count(eps) >= 1

    def test_count_monotonically_nonincreasing(self):
        epsilons = [i / 20 * 0.99 for i in range(21)]
        counts = [coasean_collective_count(e) for e in epsilons]
        for i in range(1, len(counts)):
            assert counts[i] <= counts[i - 1], (
                f"Count rose from ε={epsilons[i-1]:.3f} (N={counts[i-1]}) "
                f"to ε={epsilons[i]:.3f} (N={counts[i]})"
            )

    def test_count_returns_integer(self):
        for eps in KEY_EPSILONS:
            assert isinstance(coasean_collective_count(eps), int)

    def test_count_midpoint_between_1_and_n_max(self):
        n_mid = coasean_collective_count(0.50)
        assert 1 <= n_mid <= COASEAN_N_MAX


# ---------------------------------------------------------------------------
# run_collective_period
# ---------------------------------------------------------------------------

class TestRunCollectivePeriod:
    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_returns_two_dicts(self, eps):
        result = run_collective_period(eps, population=1_000_000.0,
                                       trust_balance=TRUST_BASE_TEH)
        assert isinstance(result, tuple) and len(result) == 2
        pipeline, fiscal = result
        assert isinstance(pipeline, dict)
        assert isinstance(fiscal, dict)

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_pipeline_has_teh_created(self, eps):
        pipeline, _ = run_collective_period(eps, population=1_000_000.0,
                                             trust_balance=TRUST_BASE_TEH)
        assert "teh_created" in pipeline
        assert pipeline["teh_created"] >= 0.0

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_fiscal_has_solvent(self, eps):
        _, fiscal = run_collective_period(eps, population=1_000_000.0,
                                           trust_balance=TRUST_BASE_TEH)
        assert "solvent" in fiscal
        assert isinstance(fiscal["solvent"], bool)
        # nested trust sub-dict must also be present
        assert "trust" in fiscal
        assert "surplus_deficit" in fiscal["trust"]

    def test_smaller_population_gives_smaller_teh(self):
        p1, _ = run_collective_period(0.40, population=1_000_000.0,
                                       trust_balance=TRUST_BASE_TEH)
        p2, _ = run_collective_period(0.40, population=500_000.0,
                                       trust_balance=TRUST_BASE_TEH)
        assert p2["teh_created"] < p1["teh_created"]


# ---------------------------------------------------------------------------
# make_federation
# ---------------------------------------------------------------------------

class TestMakeFederation:
    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_n1_returns_single_collective(self, eps):
        fed = make_federation(eps, n=1, population=1_000_000.0)
        assert len(fed) == 1
        assert isinstance(fed[0], Collective)

    def test_n1_population_equals_total(self):
        fed = make_federation(0.40, n=1, population=1_000_000.0)
        assert fed[0].population == pytest.approx(1_000_000.0)

    def test_population_sums_to_total(self):
        total_pop = 1_000_000.0
        for n in [1, 3, 5, 10]:
            fed = make_federation(0.40, n=n, population=total_pop)
            assert sum(c.population for c in fed) == pytest.approx(total_pop, rel=1e-9)

    def test_trust_sums_to_total(self):
        trust = TRUST_BASE_TEH
        for n in [1, 4, 8]:
            fed = make_federation(0.40, n=n, trust_balance=trust)
            assert sum(c.trust_balance for c in fed) == pytest.approx(trust, rel=1e-9)

    def test_default_n_matches_collective_count(self):
        for eps in KEY_EPSILONS:
            fed = make_federation(eps, population=1_000_000.0)
            expected_n = coasean_collective_count(eps)
            assert len(fed) == expected_n

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_all_collectives_have_pipeline_and_fiscal(self, eps):
        fed = make_federation(eps, population=1_000_000.0)
        for c in fed:
            assert c.pipeline, f"Collective {c.collective_id} has empty pipeline"
            assert c.fiscal, f"Collective {c.collective_id} has empty fiscal"

    def test_collective_ids_are_sequential(self):
        fed = make_federation(0.40, n=5, population=1_000_000.0)
        assert [c.collective_id for c in fed] == list(range(5))

    def test_reserve_nonnegative(self):
        fed = make_federation(0.40, n=3, population=1_000_000.0)
        for c in fed:
            assert c.reserve >= 0.0

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_epsilon_stored_on_collective(self, eps):
        fed = make_federation(eps, n=1, population=1_000_000.0)
        assert fed[0].epsilon == eps


# ---------------------------------------------------------------------------
# N=1 regression anchor — the core invariant
# ---------------------------------------------------------------------------

class TestN1RegressionAnchor:
    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_teh_created_exact_match(self, eps):
        result = n1_regression_anchor(epsilon=eps)
        assert result["teh_created_delta"] == pytest.approx(0.0, abs=1e-6), (
            f"ε={eps}: teh_created delta = {result['teh_created_delta']:.6e} "
            f"(ref={result['ref_teh_created']:.4f}, fed={result['fed_teh_created']:.4f})"
        )

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_pipeline_match_flag_true(self, eps):
        result = n1_regression_anchor(epsilon=eps)
        assert result["pipeline_match"] is True

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_solvent_match(self, eps):
        result = n1_regression_anchor(epsilon=eps)
        assert result["solvent_match"] is True, (
            f"ε={eps}: ref_solvent={result['ref_solvent']}, "
            f"fed_solvent={result['fed_solvent']}"
        )

    @pytest.mark.parametrize("eps", KEY_EPSILONS)
    def test_surplus_exact_match(self, eps):
        result = n1_regression_anchor(epsilon=eps)
        assert result["surplus_delta"] == pytest.approx(0.0, abs=1e-4)

    def test_federation_n_is_1(self):
        result = n1_regression_anchor()
        assert result["federation_n"] == 1
