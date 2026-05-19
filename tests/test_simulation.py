"""
Tests for hours_eoh.core.simulation

Covers: make_economy_state, simulate_period, run_simulation —
including TEH lifecycle (D1/D2/D3), destruction mechanisms (D4/D5/D6),
derived_epsilon, care_stipend wiring, and per-domain human EOH visibility.
"""

import math
import pytest

from hours_eoh.core.simulation import (
    make_economy_state,
    simulate_period,
    run_simulation,
)
from hours_eoh.core.prices import basket_price
from hours_eoh.data import (
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
    ESTATE_PERSONAL_RESERVE_YEARS,
    ACCUMULATION_CEILING_MULTIPLIER,
    BASE_LIFETIME_EARNINGS_TEH,
)

KEY_EPSILONS = [0.0, 0.40, 0.90, 0.99]


# ---------------------------------------------------------------------------
# State helper
# ---------------------------------------------------------------------------

def _state(eps=0.40, **overrides):
    kwargs = dict(
        epsilon=eps,
        population=1_000_000.0,
        workforce_fraction=0.60,
        trust_balance=TRUST_BASE_TEH,
        labor_income_teh=5_000_000_000.0,
        capital_stock_teh=CAPITAL_STOCK_DEFAULT,
    )
    kwargs.update(overrides)
    return make_economy_state(**kwargs)


def _default_state(**overrides):
    kwargs = dict(
        epsilon=0.40,
        population=1_000_000.0,
        workforce_fraction=0.60,
        trust_balance=TRUST_BASE_TEH,
        labor_income_teh=5_000_000_000.0,
        capital_stock_teh=CAPITAL_STOCK_DEFAULT,
        capital_age_ratio=0.30,
        ecosystem_health=0.70,
    )
    kwargs.update(overrides)
    return make_economy_state(**kwargs)


# ===========================================================================
# make_economy_state
# ===========================================================================

class TestMakeEconomyState:

    def test_required_keys_present(self):
        state = _default_state()
        for key in ("epsilon", "population", "workforce_fraction", "workforce_size",
                    "trust_balance", "labor_income_teh", "capital_stock_teh",
                    "capital_age_ratio", "ecosystem_health", "deferred_ecological",
                    "knowledge_complexity", "teh_created_cumulative",
                    "teh_destroyed_cumulative", "period"):
            assert key in state, f"Missing key: {key}"

    def test_workforce_size_derived(self):
        state = _default_state(population=1_000_000.0, workforce_fraction=0.60)
        assert state["workforce_size"] == pytest.approx(600_000.0)

    def test_capital_embodied_teh_present(self):
        state = _state()
        assert "capital_embodied_teh" in state

    def test_teh_endowment_present(self):
        state = _state()
        assert "teh_endowment" in state

    def test_capital_embodied_defaults_to_capital_stock(self):
        state = _state()
        assert state["capital_embodied_teh"] == pytest.approx(CAPITAL_STOCK_DEFAULT)

    def test_teh_endowment_equals_trust_plus_capital(self):
        state = _state()
        expected = TRUST_BASE_TEH + CAPITAL_STOCK_DEFAULT
        assert state["teh_endowment"] == pytest.approx(expected)

    def test_custom_capital_embodied_accepted(self):
        state = make_economy_state(capital_embodied_teh=1_000_000_000.0)
        assert state["capital_embodied_teh"] == pytest.approx(1_000_000_000.0)

    def test_monitoring_capability_defaults_from_canonical(self):
        state = make_economy_state(epsilon=0.40)
        assert "monitoring_capability" in state
        assert state["monitoring_capability"] > 0.0

    def test_monitoring_capability_explicit(self):
        state = make_economy_state(epsilon=0.40, monitoring_capability=0.75)
        assert state["monitoring_capability"] == pytest.approx(0.75)

    def test_monitoring_increases_with_epsilon(self):
        s0 = make_economy_state(epsilon=0.0)
        s9 = make_economy_state(epsilon=0.90)
        assert s9["monitoring_capability"] > s0["monitoring_capability"]

    def test_deferred_infra_fields_default_zero(self):
        state = make_economy_state()
        assert state["deferred_infrastructure_eoh"] == 0.0
        assert state["infra_deferred_years"] == 0.0

    def test_deferred_infra_explicit(self):
        state = make_economy_state(
            deferred_infrastructure_eoh=500_000.0,
            infra_deferred_years=5.0,
        )
        assert state["deferred_infrastructure_eoh"] == 500_000.0
        assert state["infra_deferred_years"] == 5.0


# ===========================================================================
# simulate_period — core state evolution
# ===========================================================================

class TestSimulatePeriod:

    def test_returns_tuple(self):
        state = _default_state()
        result = simulate_period(state)
        assert isinstance(result, tuple) and len(result) == 2

    def test_period_increments(self):
        state = _default_state()
        new_state, _ = simulate_period(state)
        assert new_state["period"] == 1

    def test_simulate_period_pure_no_mutation(self):
        """simulate_period must not mutate the input state dict."""
        state = _default_state()
        original_pop = state["population"]
        simulate_period(state)
        assert state["population"] == pytest.approx(original_pop)

    def test_population_grows_with_positive_rate(self):
        state = _default_state(population=1_000_000.0)
        new_state, _ = simulate_period(state, population_growth_rate=0.01)
        assert new_state["population"] == pytest.approx(1_010_000.0)

    def test_epsilon_advances_with_delta(self):
        state = _default_state(epsilon=0.40)
        new_state, _ = simulate_period(state, epsilon_delta=0.05)
        assert new_state["epsilon"] == pytest.approx(0.45)

    def test_epsilon_capped_at_099(self):
        state = _default_state(epsilon=0.98)
        new_state, _ = simulate_period(state, epsilon_delta=0.10)
        assert new_state["epsilon"] <= 0.99

    def test_capital_ages_each_period(self):
        state = _default_state(capital_age_ratio=0.30)
        new_state, _ = simulate_period(state, capital_aging_rate=0.015)
        assert new_state["capital_age_ratio"] > 0.30

    def test_capital_age_capped_at_one(self):
        state = _default_state(capital_age_ratio=0.99)
        new_state, _ = simulate_period(state, capital_aging_rate=0.10)
        assert new_state["capital_age_ratio"] <= 1.0

    def test_ecosystem_degrades_no_restoration(self):
        state = _default_state(ecosystem_health=0.70)
        new_state, _ = simulate_period(
            state,
            ecological_degradation_rate=0.01,
            ecological_restoration_rate=0.0,
        )
        assert new_state["ecosystem_health"] < 0.70

    def test_ecosystem_health_stays_positive(self):
        state = _default_state(ecosystem_health=0.01)
        new_state, _ = simulate_period(state, ecological_degradation_rate=0.50)
        assert new_state["ecosystem_health"] > 0.0

    def test_period_result_keys_present(self):
        state = _default_state()
        _, result = simulate_period(state)
        for key in ("period", "epsilon", "teh_created", "teh_destroyed",
                    "teh_net", "trust_start", "trust_end", "solvent",
                    "population", "capital_stock_teh", "ecosystem_health",
                    "fiscal", "total_eoh", "human_eoh", "labor_income"):
            assert key in result, f"Missing key: {key}"

    def test_teh_cumulative_grows_over_periods(self):
        state = _default_state()
        new_state, _ = simulate_period(state)
        assert new_state["teh_created_cumulative"] > 0.0

    def test_solvent_field_is_bool(self):
        state = _default_state()
        _, result = simulate_period(state)
        assert isinstance(result["solvent"], bool)

    def test_all_key_epsilon_initial_states_finite(self):
        """simulate_period must work starting from any key ε value."""
        for eps in KEY_EPSILONS:
            state = _default_state(epsilon=eps)
            new_state, result = simulate_period(state)
            assert math.isfinite(result["teh_created"])
            assert math.isfinite(result["trust_end"])

    def test_teh_endowment_preserved_across_periods(self):
        """teh_endowment must not change between periods."""
        s0 = _state()
        s1, _ = simulate_period(s0)
        s2, _ = simulate_period(s1)
        assert s1["teh_endowment"] == pytest.approx(s0["teh_endowment"])
        assert s2["teh_endowment"] == pytest.approx(s0["teh_endowment"])

    def test_period_result_has_monitoring_capability(self):
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state)
        assert "monitoring_capability" in result
        assert result["monitoring_capability"] > 0.0

    def test_period_result_has_knowledge_complexity_per_unit(self):
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state)
        assert "knowledge_complexity_per_unit" in result
        assert result["knowledge_complexity_per_unit"] > 0.0

    def test_period_result_has_deferred_infra_fields(self):
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state)
        assert "deferred_infrastructure_eoh" in result
        assert "infra_deferred_years" in result
        assert "infra_compounding_eoh" in result

    def test_knowledge_complexity_growth_advances(self):
        state = make_economy_state(epsilon=0.40, knowledge_complexity=2.0)
        new_state, _ = simulate_period(state, knowledge_complexity_growth_rate=0.10)
        assert new_state["knowledge_complexity"] == pytest.approx(2.0 * 1.10)

    def test_knowledge_complexity_static_by_default(self):
        state = make_economy_state(epsilon=0.40, knowledge_complexity=3.0)
        new_state, _ = simulate_period(state, knowledge_complexity_growth_rate=0.0)
        assert new_state["knowledge_complexity"] == pytest.approx(3.0)

    def test_infra_deferred_years_increments_when_backlog_exists(self):
        state = make_economy_state(
            epsilon=0.40,
            deferred_infrastructure_eoh=1_000_000.0,
            infra_deferred_years=3.0,
        )
        new_state, result = simulate_period(state)
        assert new_state["infra_deferred_years"] == pytest.approx(4.0)
        assert result["infra_compounding_eoh"] > 0.0

    def test_infra_deferred_years_unchanged_when_no_backlog(self):
        state = make_economy_state(
            epsilon=0.40,
            deferred_infrastructure_eoh=0.0,
            infra_deferred_years=0.0,
        )
        new_state, result = simulate_period(state)
        assert new_state["infra_deferred_years"] == 0.0
        assert result["infra_compounding_eoh"] == 0.0

    def test_ecological_deferred_paydown_on_restoration(self):
        state = make_economy_state(epsilon=0.40, deferred_ecological=100_000.0)
        new_state, _ = simulate_period(
            state,
            ecological_restoration_rate=0.10,
            ecological_degradation_rate=0.0,
        )
        assert new_state["deferred_ecological"] < state["deferred_ecological"]

    def test_condition_iii_b_backlog_decreases_when_compounding_active(self):
        state = make_economy_state(
            epsilon=0.40,
            deferred_infrastructure_eoh=5_000_000.0,
            infra_deferred_years=10.0,
        )
        new_state, result = simulate_period(state)
        assert result["infra_compounding_eoh"] > 0.0
        assert new_state["deferred_infrastructure_eoh"] < state["deferred_infrastructure_eoh"]

    def test_condition_iii_b_backlog_not_negative(self):
        state = make_economy_state(
            epsilon=0.40,
            deferred_infrastructure_eoh=1.0,
            infra_deferred_years=100.0,
        )
        new_state, _ = simulate_period(state)
        assert new_state["deferred_infrastructure_eoh"] >= 0.0


# ===========================================================================
# run_simulation
# ===========================================================================

class TestRunSimulation:

    def test_returns_expected_keys(self):
        state = _default_state()
        traj = run_simulation(state, n_periods=5)
        for key in ("states", "period_results", "final_state",
                    "solvent_all", "first_insolvency", "summary"):
            assert key in traj, f"Missing key: {key}"

    def test_period_count(self):
        state = _default_state()
        traj = run_simulation(state, n_periods=10)
        assert len(traj["states"]) == 10
        assert len(traj["period_results"]) == 10

    def test_final_state_period_correct(self):
        state = _default_state()
        traj = run_simulation(state, n_periods=5)
        assert traj["final_state"]["period"] == 5

    def test_solvent_all_consistent(self):
        """solvent_all and first_insolvency must be consistent."""
        state = _default_state()
        traj = run_simulation(state, n_periods=10)
        if traj["solvent_all"]:
            assert traj["first_insolvency"] is None
        else:
            assert traj["first_insolvency"] is not None

    def test_summary_finite(self):
        state = _default_state()
        traj = run_simulation(state, n_periods=10)
        summary = traj["summary"]
        for key in ("epsilon_range", "trust_balance_range",
                    "total_teh_created", "total_teh_destroyed"):
            assert key in summary

    def test_20_periods_no_error(self):
        """Standard 20-period run must complete without error."""
        state = _default_state()
        traj = run_simulation(state, n_periods=20, epsilon_delta=0.02,
                              ecological_degradation_rate=0.002)
        assert len(traj["states"]) == 20

    def test_epsilon_arc(self):
        """Epsilon must advance across the full arc when delta is set."""
        state = _default_state(epsilon=0.20)
        traj = run_simulation(state, n_periods=20, epsilon_delta=0.03)
        epsilons = [r["epsilon"] for r in traj["period_results"]]
        assert max(epsilons) > 0.20


# ===========================================================================
# D1+D2 — TEH lifecycle: capital_embodied_teh and endogenous consumption
# ===========================================================================

class TestCapitalEmbodiedTEH:
    """capital_embodied_teh tracks TEH locked in capital, excluded from circulation."""

    def test_period_result_has_lifecycle_keys(self):
        _, result = simulate_period(_state())
        for key in ("teh_total_supply", "teh_in_circulation",
                    "capital_embodied_teh", "investment_teh",
                    "consumption_rate_effective"):
            assert key in result, f"Missing key: {key}"

    def test_teh_in_circulation_finite(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps))
            assert math.isfinite(result["teh_in_circulation"])

    def test_account_identity_holds(self):
        """teh_in_circulation + trust_end + capital_embodied ≈ teh_total_supply."""
        _, result = simulate_period(_state())
        total = result["teh_total_supply"]
        accounted = (
            result["teh_in_circulation"]
            + result["trust_end"]
            + result["capital_embodied_teh"]
        )
        assert accounted == pytest.approx(total, rel=1e-6)

    def test_account_identity_all_epsilons(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps))
            total = result["teh_total_supply"]
            accounted = (
                result["teh_in_circulation"]
                + result["trust_end"]
                + result["capital_embodied_teh"]
            )
            assert accounted == pytest.approx(total, rel=1e-6)

    def test_investment_increases_capital_embodied(self):
        _, r_no_inv   = simulate_period(_state(), capital_investment_rate=0.0)
        _, r_with_inv = simulate_period(_state(), capital_investment_rate=0.05)
        assert r_with_inv["capital_embodied_teh"] > r_no_inv["capital_embodied_teh"]

    def test_writedown_reduces_capital_embodied(self):
        """Write-down destroys capital-embodied TEH each period."""
        s0 = _state()
        s1, _ = simulate_period(s0, capital_investment_rate=0.0)
        assert s1["capital_embodied_teh"] < s0["capital_embodied_teh"]

    def test_multi_period_account_identity(self):
        """Account identity must hold across a 20-period run."""
        traj = run_simulation(_state(), n_periods=20)
        for result in traj["period_results"]:
            total = result["teh_total_supply"]
            accounted = (
                result["teh_in_circulation"]
                + result["trust_end"]
                + result["capital_embodied_teh"]
            )
            assert accounted == pytest.approx(total, rel=1e-5), \
                f"Account identity violated at period {result['period']}"


class TestEndogenousConsumption:
    """D2: income-driven consumption falls with ε as purchasing power rises."""

    def test_consumption_rate_effective_in_result(self):
        _, result = simulate_period(_state())
        assert "consumption_rate_effective" in result

    def test_at_zero_epsilon_rate_near_base(self):
        """At ε=0, pp_ratio=1.0, so effective rate == base_consumption_rate."""
        _, result = simulate_period(_state(eps=0.0))
        assert result["consumption_rate_effective"] == pytest.approx(0.75, rel=1e-4)

    def test_rate_falls_with_epsilon(self):
        """Higher ε → higher PP → more saving → lower consumption rate."""
        rates = []
        for eps in [0.0, 0.20, 0.40, 0.60, 0.80]:
            _, result = simulate_period(_state(eps=eps))
            rates.append(result["consumption_rate_effective"])
        for i in range(len(rates) - 1):
            assert rates[i] >= rates[i + 1] - 1e-6, \
                f"Rate non-monotone at index {i}: {rates[i]:.4f} vs {rates[i+1]:.4f}"

    def test_rate_bounded_above_by_base(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps))
            assert result["consumption_rate_effective"] <= 0.75 + 1e-9

    def test_rate_positive_all_epsilons(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps))
            assert result["consumption_rate_effective"] > 0.0

    def test_teh_destroyed_positive_all_epsilons(self):
        """Destruction = consumption + writedown must be > 0 at all ε."""
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps))
            assert result["teh_destroyed"] > 0.0

    def test_custom_base_rate_applied(self):
        _, r_low  = simulate_period(_state(eps=0.0), base_consumption_rate=0.50)
        _, r_high = simulate_period(_state(eps=0.0), base_consumption_rate=0.90)
        assert r_low["consumption_rate_effective"] < r_high["consumption_rate_effective"]

    def test_higher_labor_income_more_consumption(self):
        _, r_low  = simulate_period(_state(), labor_income_scale=1_000_000_000.0)
        _, r_high = simulate_period(_state(), labor_income_scale=10_000_000_000.0)
        assert r_high["teh_destroyed"] > r_low["teh_destroyed"]

    def test_d1_d2_full_arc_no_error(self):
        traj = run_simulation(_state(), n_periods=20, epsilon_delta=0.02)
        assert len(traj["period_results"]) == 20

    def test_consumption_rate_declines_over_epsilon_arc(self):
        traj = run_simulation(_state(eps=0.10), n_periods=15, epsilon_delta=0.05)
        rates = [r["consumption_rate_effective"] for r in traj["period_results"]]
        assert rates[-1] < rates[0]

    def test_all_lifecycle_values_finite_full_arc(self):
        traj = run_simulation(_state(), n_periods=20, epsilon_delta=0.03)
        for result in traj["period_results"]:
            for key in ("teh_total_supply", "teh_in_circulation",
                        "capital_embodied_teh", "consumption_rate_effective",
                        "teh_destroyed"):
                assert math.isfinite(result[key]), \
                    f"Non-finite {key} at period {result['period']}"


# ===========================================================================
# D3 — Biology-anchored consumption
# ===========================================================================

class TestD3Consumption:
    """D3 destruction driven by personal EOH on-ledger × basket price."""

    def test_d3_result_keys_present(self):
        _, result = simulate_period(_state(), use_d3=True)
        assert "personal_eoh_on_ledger" in result
        assert "baskets_consumed" in result

    def test_d2_mode_unchanged(self):
        """D2 path: consumption_rate_effective is set; D3 fields are None."""
        _, result = simulate_period(_state(), use_d3=False)
        assert result["consumption_rate_effective"] is not None
        assert result["personal_eoh_on_ledger"] is None
        assert result["baskets_consumed"] is None

    def test_d3_destruction_positive_all_epsilons(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps), use_d3=True)
            assert result["teh_destroyed"] > 0.0

    def test_d3_all_values_finite(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps), use_d3=True)
            for key in ("teh_destroyed", "teh_total_supply", "teh_in_circulation",
                        "personal_eoh_on_ledger", "baskets_consumed"):
                assert math.isfinite(result[key]), f"Non-finite {key} at ε={eps}"

    def test_d3_account_identity_holds(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(_state(eps=eps), use_d3=True)
            total = result["teh_total_supply"]
            accounted = (
                result["teh_in_circulation"]
                + result["trust_end"]
                + result["capital_embodied_teh"]
            )
            assert accounted == pytest.approx(total, rel=1e-6), (
                f"Account identity violated at ε={eps}"
            )

    def test_d3_personal_eoh_on_ledger_grows_with_epsilon(self):
        """More automation → more personal EOH on-ledger."""
        ledger_values = []
        for eps in [0.0, 0.40, 0.65, 0.90]:
            _, result = simulate_period(_state(eps=eps), use_d3=True)
            ledger_values.append(result["personal_eoh_on_ledger"])
        for i in range(len(ledger_values) - 1):
            assert ledger_values[i] < ledger_values[i + 1], (
                f"personal_eoh_on_ledger non-increasing at index {i}"
            )

    def test_d3_lower_destruction_than_d2_at_low_epsilon(self):
        """At low ε, most personal EOH is private → D3 destroys less TEH than D2."""
        _, r_d2 = simulate_period(_state(eps=0.0), use_d3=False)
        _, r_d3 = simulate_period(_state(eps=0.0), use_d3=True)
        assert r_d3["teh_destroyed"] < r_d2["teh_destroyed"]

    def test_d3_arc_peaks_then_falls(self):
        """D3 destruction peaks mid-ε then falls as basket prices collapse."""
        low_eps_dest  = simulate_period(_state(eps=0.10), use_d3=True)[1]["teh_destroyed"]
        mid_eps_dest  = simulate_period(_state(eps=0.65), use_d3=True)[1]["teh_destroyed"]
        high_eps_dest = simulate_period(_state(eps=0.99), use_d3=True)[1]["teh_destroyed"]
        assert mid_eps_dest > low_eps_dest
        assert mid_eps_dest > high_eps_dest

    def test_d3_20_period_run_no_error(self):
        traj = run_simulation(_state(), n_periods=20, epsilon_delta=0.02, use_d3=True)
        assert len(traj["period_results"]) == 20

    def test_d3_account_identity_over_arc(self):
        traj = run_simulation(_state(), n_periods=20, epsilon_delta=0.02, use_d3=True)
        for result in traj["period_results"]:
            total = result["teh_total_supply"]
            accounted = (
                result["teh_in_circulation"]
                + result["trust_end"]
                + result["capital_embodied_teh"]
            )
            assert accounted == pytest.approx(total, rel=1e-5), (
                f"Account identity violated at period {result['period']}"
            )

    def test_d3_personal_eoh_on_ledger_rises_over_epsilon_arc(self):
        traj = run_simulation(_state(eps=0.10), n_periods=10, epsilon_delta=0.05, use_d3=True)
        ledger_vals = [r["personal_eoh_on_ledger"] for r in traj["period_results"]]
        assert ledger_vals[-1] > ledger_vals[0]


# ===========================================================================
# D4/D5/D6 destruction mechanisms (phase 15)
# ===========================================================================

class TestSimulatePeriodDestructionMechanisms:

    def _state_with_capital_eoh(self, eps: float = 0.40, cap_pers_fulfil: float = 500.0):
        return make_economy_state(
            epsilon=eps,
            population=1_000_000.0,
            capital_personal_eoh_fulfilled=cap_pers_fulfil,
            teh_endowment=1e10,
        )

    def _state_with_large_holdings(self, eps: float = 0.40):
        reserve = ESTATE_PERSONAL_RESERVE_YEARS * basket_price(eps)
        pop = 1_000_000.0
        per_capita = reserve * 5.0
        return make_economy_state(
            epsilon=eps,
            population=pop,
            teh_endowment=per_capita * pop,
            trust_balance=0.0,
        )

    def test_d4_disabled_produces_zero_cpi_destruction(self):
        state = self._state_with_capital_eoh(cap_pers_fulfil=1000.0)
        _, result = simulate_period(state, use_cpi_destruction=False)
        assert result["d4_cpi"]["teh_destroyed"] == 0.0
        assert result["d4_cpi"]["mechanism"] == "D4_disabled"

    def test_d4_enabled_produces_nonzero_cpi_destruction(self):
        state = self._state_with_capital_eoh(cap_pers_fulfil=1000.0)
        _, result = simulate_period(state, use_cpi_destruction=True)
        assert result["d4_cpi"]["teh_destroyed"] > 0.0
        assert result["d4_cpi"]["mechanism"] == "D4_cpi"

    def test_d4_destruction_scales_with_capital_eoh(self):
        state_lo = self._state_with_capital_eoh(cap_pers_fulfil=100.0)
        state_hi = self._state_with_capital_eoh(cap_pers_fulfil=200.0)
        _, res_lo = simulate_period(state_lo, use_cpi_destruction=True)
        _, res_hi = simulate_period(state_hi, use_cpi_destruction=True)
        assert res_hi["d4_cpi"]["teh_destroyed"] > res_lo["d4_cpi"]["teh_destroyed"]

    def test_d5_disabled_produces_zero_estate_destruction(self):
        state = self._state_with_large_holdings()
        _, result = simulate_period(state, use_estate_dissolution=False)
        assert result["d5_estate"]["teh_destroyed"] == 0.0
        assert result["d5_estate"]["mechanism"] == "D5_disabled"

    def test_d5_enabled_produces_nonzero_destruction_with_large_holdings(self):
        state = self._state_with_large_holdings()
        _, result = simulate_period(state, use_estate_dissolution=True)
        assert result["d5_estate"]["teh_destroyed"] > 0.0
        assert result["d5_estate"]["mechanism"] == "D5_estate"

    def test_d5_levy_increases_trust_balance(self):
        """Estate levy is circulatory — it must increase the Trust balance."""
        state = self._state_with_large_holdings()
        new_state_off, _ = simulate_period(state, use_estate_dissolution=False)
        new_state_on,  _ = simulate_period(state, use_estate_dissolution=True)
        assert new_state_on["trust_balance"] >= new_state_off["trust_balance"]

    def test_d6_disabled_by_default(self):
        """D6 must be off by default."""
        ceiling = ACCUMULATION_CEILING_MULTIPLIER * BASE_LIFETIME_EARNINGS_TEH
        pop = 1_000_000.0
        state = make_economy_state(
            epsilon=0.40,
            population=pop,
            teh_endowment=ceiling * 10.0 * pop,
        )
        _, result = simulate_period(state)
        assert result["d6_ceiling"]["teh_committed_to_capital"] == 0.0
        assert result["d6_ceiling"]["mechanism"] == "D6_disabled"

    def test_d6_enabled_moves_teh_to_capital_pool(self):
        """When D6 enabled with holdings above ceiling, capital_embodied_teh increases."""
        ceiling = ACCUMULATION_CEILING_MULTIPLIER * BASE_LIFETIME_EARNINGS_TEH
        pop = 1_000_000.0
        state = make_economy_state(
            epsilon=0.40,
            population=pop,
            teh_endowment=ceiling * 10.0 * pop,
        )
        new_off, _ = simulate_period(state, use_accumulation_ceiling=False)
        new_on,  _ = simulate_period(state, use_accumulation_ceiling=True)
        assert new_on["capital_embodied_teh"] >= new_off["capital_embodied_teh"]

    def test_d4_d5_combined_reduce_supply_growth(self):
        state = make_economy_state(
            epsilon=0.40,
            population=1_000_000.0,
            capital_personal_eoh_fulfilled=1000.0,
            teh_endowment=5e9,
        )
        _, res_none = simulate_period(state, use_cpi_destruction=False,
                                     use_estate_dissolution=False)
        _, res_both = simulate_period(state, use_cpi_destruction=True,
                                     use_estate_dissolution=True)
        assert res_both["teh_destroyed"] >= res_none["teh_destroyed"]
        assert res_both["teh_net"] <= res_none["teh_net"]

    def test_d4_d5_totals_included_in_teh_destroyed(self):
        state = make_economy_state(
            epsilon=0.40,
            population=1_000_000.0,
            capital_personal_eoh_fulfilled=500.0,
            teh_endowment=5e9,
        )
        _, result = simulate_period(state, use_cpi_destruction=True,
                                    use_estate_dissolution=True)
        d4 = result["d4_cpi"]["teh_destroyed"]
        d5 = result["d5_estate"]["teh_destroyed"]
        assert result["teh_destroyed"] >= d4 + d5 - 1e-6


class TestMultiPeriodDestructionArc:

    def test_net_supply_growth_lower_with_d4_d5_over_10_periods(self):
        """Over 10 periods with capital delivering services, D4+D5 keep supply lower."""
        initial = make_economy_state(
            epsilon=0.40,
            population=1_000_000.0,
            capital_personal_eoh_fulfilled=800.0,
            teh_endowment=2e9,
        )
        kwargs_base = dict(use_cpi_destruction=False, use_estate_dissolution=False,
                           use_accumulation_ceiling=False)
        kwargs_full = dict(use_cpi_destruction=True, use_estate_dissolution=True,
                           use_accumulation_ceiling=False)

        state_base = state_full = initial
        for _ in range(10):
            state_base, _ = simulate_period(state_base, **kwargs_base)
            state_full, _ = simulate_period(state_full, **kwargs_full)

        supply_base = (state_base["teh_endowment"]
                       + state_base["teh_created_cumulative"]
                       - state_base["teh_destroyed_cumulative"])
        supply_full = (state_full["teh_endowment"]
                       + state_full["teh_created_cumulative"]
                       - state_full["teh_destroyed_cumulative"])

        assert supply_full <= supply_base


# ===========================================================================
# derived_epsilon regression (new-8)
# ===========================================================================

class TestDerivedEpsilon:

    def test_derived_epsilon_equals_eps(self):
        """Until machine capacity is modeled endogenously, derived_epsilon == ε."""
        state = make_economy_state(epsilon=0.60)
        _, result = simulate_period(state)
        assert result["derived_epsilon"] == pytest.approx(result["epsilon"])

    def test_derived_epsilon_tracks_epsilon_delta(self):
        for eps_start, delta in [(0.0, 0.10), (0.40, 0.05), (0.90, 0.05)]:
            state = make_economy_state(epsilon=eps_start)
            _, result = simulate_period(state, epsilon_delta=delta)
            expected = min(0.99, eps_start + delta)
            assert result["derived_epsilon"] == pytest.approx(expected)


# ===========================================================================
# human_eoh_by_domain in period_result (phase 8)
# ===========================================================================

class TestHumanEohByDomainInPeriodResult:

    def _s(self, eps=0.40):
        return make_economy_state(
            epsilon=eps,
            population=1_000_000.0,
            workforce_fraction=0.60,
            trust_balance=TRUST_BASE_TEH,
            labor_income_teh=5_000_000_000.0,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT,
        )

    def test_key_present(self):
        _, result = simulate_period(self._s())
        assert "human_eoh_by_domain" in result

    def test_domain_keys_present(self):
        _, result = simulate_period(self._s())
        for domain in ("personal", "infrastructure", "ecological", "knowledge"):
            assert domain in result["human_eoh_by_domain"], f"Missing domain: {domain}"

    def test_human_eoh_leq_gross(self):
        """Human EOH per domain must be <= gross EOH."""
        _, result = simulate_period(self._s(eps=0.40))
        gross = result["eoh_by_domain"]
        human = result["human_eoh_by_domain"]
        for domain in ("personal", "infrastructure", "ecological", "knowledge"):
            assert human[domain] <= gross[domain] + 1e-6

    def test_sum_consistent_with_human_fraction(self):
        """Sum of human domain EOH must equal total_eoh × (1 - ε)."""
        eps = 0.40
        _, result = simulate_period(self._s(eps=eps))
        human_sum = sum(result["human_eoh_by_domain"].values())
        expected  = result["total_eoh"] * (1.0 - eps)
        assert human_sum == pytest.approx(expected, rel=1e-4)

    def test_at_zero_epsilon_human_equals_gross(self):
        """At ε=0, human EOH equals gross EOH (no automation)."""
        _, result = simulate_period(self._s(eps=0.0))
        gross = result["eoh_by_domain"]
        human = result["human_eoh_by_domain"]
        for domain in ("personal", "infrastructure", "ecological", "knowledge"):
            assert human[domain] == pytest.approx(gross[domain], rel=1e-6)

    def test_shrinks_with_higher_epsilon(self):
        _, r_low  = simulate_period(self._s(eps=0.20))
        _, r_high = simulate_period(self._s(eps=0.80))
        for domain in ("personal", "infrastructure"):
            assert r_high["human_eoh_by_domain"][domain] < r_low["human_eoh_by_domain"][domain]

    def test_finite_all_key_epsilons(self):
        for eps in KEY_EPSILONS:
            _, result = simulate_period(self._s(eps=eps))
            for v in result["human_eoh_by_domain"].values():
                assert math.isfinite(v)


# ===========================================================================
# care_stipend wiring (new-15)
# ===========================================================================

class TestSimulatePeriodCareStipend:

    def test_care_stipend_passed_to_fiscal(self):
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state, care_stipend_aggregate=10_000_000.0)
        assert result["fiscal"]["care_stipend"] == pytest.approx(10_000_000.0)

    def test_auto_care_stipend_from_demographics(self):
        """Default (None) → auto-computed from population demographics; should be positive."""
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state)
        assert result["fiscal"]["care_stipend"] > 0.0

    def test_explicit_zero_care_stipend(self):
        """Passing 0.0 explicitly disables the stipend."""
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state, care_stipend_aggregate=0.0)
        assert result["fiscal"]["care_stipend"] == 0.0


# ===========================================================================
# workforce_epsilon_decay (Phase 1A)
# ===========================================================================

class TestWorkforceEpsilonDecay:

    def test_decay_false_leaves_fraction_unchanged(self):
        """Default: workforce_fraction does not change across periods."""
        state = make_economy_state(epsilon=0.40, workforce_fraction=0.60)
        new_state, _ = simulate_period(state, epsilon_delta=0.10,
                                       workforce_epsilon_decay=False)
        assert new_state["workforce_fraction"] == pytest.approx(0.60)

    def test_decay_true_reduces_fraction_with_positive_delta(self):
        """With decay enabled and epsilon advancing, fraction must decrease."""
        state = make_economy_state(epsilon=0.40, workforce_fraction=0.60)
        new_state, _ = simulate_period(state, epsilon_delta=0.10,
                                       workforce_epsilon_decay=True)
        assert new_state["workforce_fraction"] < 0.60

    def test_decay_true_no_change_without_epsilon_delta(self):
        """Decay has no effect when epsilon_delta=0 (ε not advancing)."""
        state = make_economy_state(epsilon=0.40, workforce_fraction=0.60)
        new_state, _ = simulate_period(state, epsilon_delta=0.0,
                                       workforce_epsilon_decay=True)
        assert new_state["workforce_fraction"] == pytest.approx(0.60)

    def test_decay_monotonic_over_arc(self):
        """Over a multi-period arc, workforce_fraction decreases monotonically."""
        state = make_economy_state(epsilon=0.10, workforce_fraction=0.70)
        fracs = [state["workforce_fraction"]]
        for _ in range(8):
            state, _ = simulate_period(state, epsilon_delta=0.08,
                                       workforce_epsilon_decay=True)
            fracs.append(state["workforce_fraction"])
        for i in range(len(fracs) - 1):
            assert fracs[i] >= fracs[i + 1], f"Non-monotonic at step {i}"

    def test_decay_floor_at_005(self):
        """workforce_fraction never drops below 0.05 even at near-full automation."""
        state = make_economy_state(epsilon=0.80, workforce_fraction=0.10)
        for _ in range(10):
            state, _ = simulate_period(state, epsilon_delta=0.02,
                                       workforce_epsilon_decay=True)
        assert state["workforce_fraction"] >= 0.05

    def test_period_result_has_workforce_fraction(self):
        """workforce_fraction is present in period_result."""
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state)
        assert "workforce_fraction" in result
        assert 0.0 < result["workforce_fraction"] <= 1.0


# ===========================================================================
# guf_net_inflow injection (Phase 1B)
# ===========================================================================

class TestGufNetInflowInjection:

    def test_none_inflow_no_change(self):
        """Default None: trust balance identical to baseline with no GUF."""
        state = make_economy_state(epsilon=0.40)
        new_none, _ = simulate_period(state, guf_net_inflow=None)
        new_zero, _ = simulate_period(state, guf_net_inflow=0.0)
        # None and 0.0 should not differ meaningfully
        assert new_none["trust_balance"] == pytest.approx(new_zero["trust_balance"],
                                                          rel=1e-9)

    def test_positive_inflow_increases_trust(self):
        """Positive GUF inflow raises the Trust balance vs. no-GUF baseline."""
        state = make_economy_state(epsilon=0.40)
        new_base, _ = simulate_period(state, guf_net_inflow=None)
        new_guf,  _ = simulate_period(state, guf_net_inflow=1_000_000.0)
        assert new_guf["trust_balance"] > new_base["trust_balance"]

    def test_inflow_amount_added_exactly(self):
        """The trust balance delta equals the injected GUF inflow exactly."""
        state = make_economy_state(epsilon=0.40)
        inflow = 5_000_000.0
        new_base, _ = simulate_period(state, guf_net_inflow=None)
        new_guf,  _ = simulate_period(state, guf_net_inflow=inflow)
        delta = new_guf["trust_balance"] - new_base["trust_balance"]
        assert delta == pytest.approx(inflow, rel=1e-9)

    def test_guf_inflow_in_period_result(self):
        """guf_net_inflow value is present in period_result."""
        state = make_economy_state(epsilon=0.40)
        _, result = simulate_period(state, guf_net_inflow=2_500_000.0)
        assert result["guf_net_inflow"] == pytest.approx(2_500_000.0)

    def test_zero_inflow_no_effect(self):
        """Zero inflow adds nothing to trust balance."""
        state = make_economy_state(epsilon=0.40)
        new_base, _ = simulate_period(state, guf_net_inflow=None)
        new_zero, _ = simulate_period(state, guf_net_inflow=0.0)
        assert new_zero["trust_balance"] == pytest.approx(new_base["trust_balance"],
                                                          rel=1e-9)
