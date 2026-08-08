"""
Tests for trajectory.py — canonical arc, ε derivation, and physical state.

Covers:
  - canonical_age_distribution(): shape, normalization, monotonic elderly shift
  - canonical_physical_state(): output structure, ε=0 / ε=0.99 extremes,
    monotonicity across the full arc
  - compute_epsilon(): formula, edge cases, clamping
  - effective_capital_from_epsilon(): matches trajectory physical state
  - Physical-state API on EOH generation functions (no epsilon, explicit params)
  - Backward-compat epsilon path still matches canonical-trajectory calls
"""

from __future__ import annotations
import pytest
from hours_eoh.core.trajectory import (
    canonical_age_distribution,
    canonical_physical_state,
    compute_epsilon,
    effective_capital_from_epsilon,
)
from hours_eoh.core.eoh_generation import (
    personal_eoh,
    infrastructure_eoh,
    ecological_eoh,
    knowledge_eoh,
    total_eoh,
    ecological_eoh_breakdown,
)
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    CANONICAL_CAPITAL_GROWTH_SLOPE,
    CANONICAL_MONITORING_CAPABILITY_BASE,
    CANONICAL_MONITORING_CAPABILITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_EXP,
    CANONICAL_ECOSYSTEM_HEALTH_BASE,
    CANONICAL_ECOSYSTEM_HEALTH_DRIFT,
    KNOWLEDGE_EOH_BASE,
    SKILL_TRANSMISSION_RATE,
)


# ---------------------------------------------------------------------------
# canonical_age_distribution
# ---------------------------------------------------------------------------

class TestCanonicalAgeDistribution:
    def test_sums_to_one(self):
        for eps in [0.0, 0.20, 0.50, 0.80, 0.99]:
            dist = canonical_age_distribution(eps)
            assert abs(sum(dist.values()) - 1.0) < 1e-9, (
                f"Distribution sums to {sum(dist.values())} at ε={eps}"
            )

    def test_has_required_groups(self):
        dist = canonical_age_distribution(0.40)
        assert "elderly" in dist
        assert "child" in dist
        assert "working_age" in dist
        assert "infant" in dist

    def test_elderly_grows_with_epsilon(self):
        d0 = canonical_age_distribution(0.0)
        d9 = canonical_age_distribution(0.90)
        assert d9["elderly"] > d0["elderly"], "Elderly fraction should grow with ε"

    def test_child_shrinks_with_epsilon(self):
        d0 = canonical_age_distribution(0.0)
        d9 = canonical_age_distribution(0.90)
        assert d9["child"] < d0["child"], "Child fraction shrinks as elderly grows"

    def test_shift_is_modest(self):
        d0 = canonical_age_distribution(0.0)
        d1 = canonical_age_distribution(0.99)
        shift = d1["elderly"] - d0["elderly"]
        assert shift <= 0.03 * d0["elderly"] + 1e-9

    def test_epsilon_clamped(self):
        canonical_age_distribution(-0.1)
        canonical_age_distribution(1.5)


# ---------------------------------------------------------------------------
# canonical_physical_state
# ---------------------------------------------------------------------------

class TestCanonicalPhysicalState:
    KEYS = {
        "capital_stock_teh", "capital_age_ratio", "ecosystem_health",
        "monitoring_capability", "knowledge_base_size",
        "knowledge_complexity_per_unit", "age_distribution",
    }

    def _state(self, eps: float) -> dict:
        return canonical_physical_state(eps)

    def test_output_keys_complete(self):
        s = self._state(0.40)
        assert s.keys() == self.KEYS

    def test_eps0_capital_is_zero(self):
        """Block III (2026-08-06): subsistence has NO collective apparatus.

        The path was 2.0B × (1 + 2ε), which asserted 2,000 TEH/capita of built
        infrastructure at ε=0 — a collective with an apparatus and no automation
        to justify it. That contradicted ε's own definition (zero machine capital
        ⇒ ε = 0, which civilization_epsilon already honoured) and made the autarky
        comparison report the canonical arc as overbuilt at the origin for a
        reason that was an artifact of this line.
        """
        s = self._state(0.0)
        assert s["capital_stock_teh"] == 0.0

    def test_eps1_endpoint_is_preserved(self):
        """Only the intercept moved: capital at ε=1 is still 3× the base."""
        assert self._state(1.0)["capital_stock_teh"] == pytest.approx(
            3.0 * CAPITAL_STOCK_DEFAULT, rel=1e-9)
        # and the upper arc is materially unchanged (5,940 vs the previous 5,960)
        assert self._state(0.99)["capital_stock_teh"] == pytest.approx(
            2.97 * CAPITAL_STOCK_DEFAULT, rel=1e-9)

    def test_eps1_capital_tripled(self):
        s = self._state(1.0)
        assert s["capital_stock_teh"] == pytest.approx(
            CAPITAL_STOCK_DEFAULT * 3.0, rel=1e-9
        )

    def test_capital_monotone(self):
        states = [self._state(e) for e in [0.0, 0.20, 0.50, 0.80, 0.99]]
        caps = [s["capital_stock_teh"] for s in states]
        assert caps == sorted(caps)

    def test_ecosystem_health_eps0(self):
        s = self._state(0.0)
        assert s["ecosystem_health"] == pytest.approx(CANONICAL_ECOSYSTEM_HEALTH_BASE)

    def test_ecosystem_health_decreases_across_arc(self):
        # drift is negative — development pressure > stewardship gain
        s0 = self._state(0.0)
        s9 = self._state(0.99)
        assert s9["ecosystem_health"] < s0["ecosystem_health"]

    def test_ecosystem_health_positive(self):
        for eps in [0.0, 0.50, 0.99]:
            assert self._state(eps)["ecosystem_health"] > 0.0

    def test_monitoring_capability_monotone(self):
        states = [self._state(e) for e in [0.0, 0.20, 0.50, 0.80, 0.99]]
        caps = [s["monitoring_capability"] for s in states]
        assert caps == sorted(caps)

    def test_monitoring_capability_eps0(self):
        s = self._state(0.0)
        assert s["monitoring_capability"] == pytest.approx(
            CANONICAL_MONITORING_CAPABILITY_BASE
        )

    def test_knowledge_base_size_monotone(self):
        states = [self._state(e) for e in [0.0, 0.20, 0.50, 0.80, 0.99]]
        kbs = [s["knowledge_base_size"] for s in states]
        assert kbs == sorted(kbs)

    def test_knowledge_base_size_eps0(self):
        assert self._state(0.0)["knowledge_base_size"] == pytest.approx(1.0)

    def test_knowledge_complexity_per_unit_eps0(self):
        assert self._state(0.0)["knowledge_complexity_per_unit"] == pytest.approx(1.0)

    def test_knowledge_complexity_per_unit_grows(self):
        s0 = self._state(0.0)
        s9 = self._state(0.99)
        assert s9["knowledge_complexity_per_unit"] > s0["knowledge_complexity_per_unit"]

    def test_age_distribution_sums_to_one(self):
        for eps in [0.0, 0.50, 0.99]:
            dist = self._state(eps)["age_distribution"]
            assert abs(sum(dist.values()) - 1.0) < 1e-9

    def test_capital_age_ratio_grows(self):
        # Older average asset mix as civilization accumulates long-lived infrastructure
        s0 = self._state(0.0)
        s9 = self._state(0.99)
        assert s9["capital_age_ratio"] > s0["capital_age_ratio"]


# ---------------------------------------------------------------------------
# compute_epsilon
# ---------------------------------------------------------------------------

class TestComputeEpsilon:
    def test_zero_denominator_returns_zero(self):
        assert compute_epsilon(1000.0, 0.0) == 0.0

    def test_zero_numerator_returns_zero(self):
        assert compute_epsilon(0.0, 1_000_000.0) == 0.0

    def test_equal_returns_one(self):
        assert compute_epsilon(500.0, 500.0) == pytest.approx(1.0)

    def test_half_fulfillment(self):
        assert compute_epsilon(250.0, 500.0) == pytest.approx(0.5)

    def test_clamp_above_one(self):
        assert compute_epsilon(2000.0, 500.0) == 1.0

    def test_clamp_negative(self):
        assert compute_epsilon(-100.0, 500.0) == 0.0

    def test_monotone_with_fulfillment(self):
        denom = 1_000_000.0
        results = [compute_epsilon(f, denom) for f in [0, 250_000, 500_000, 750_000, 1_000_000]]
        assert results == sorted(results)


# ---------------------------------------------------------------------------
# effective_capital_from_epsilon
# ---------------------------------------------------------------------------

class TestEffectiveCapitalFromEpsilon:
    def test_eps0_returns_baseline(self):
        assert effective_capital_from_epsilon(1_000_000.0, 0.0) == pytest.approx(1_000_000.0)

    def test_deliberately_differs_from_canonical_physical_state(self):
        """The two answer different questions, and since Block III they diverge.

        `canonical_physical_state(ε)` is the ARC's capital AT ε — zero at the
        origin, because subsistence has no apparatus. This function scales a
        CALLER-SUPPLIED ε=0 baseline; the caller is asserting that stock exists,
        so zeroing it would destroy their input rather than model anything.

        Pinned so the divergence stays deliberate rather than looking like drift.
        """
        for eps in [0.0, 0.40, 0.90]:
            state = canonical_physical_state(eps)
            manual = effective_capital_from_epsilon(CAPITAL_STOCK_DEFAULT, eps)
            assert manual > state["capital_stock_teh"]
        # the supplied baseline survives at ε=0; the arc does not have one
        assert effective_capital_from_epsilon(CAPITAL_STOCK_DEFAULT, 0.0) == pytest.approx(
            CAPITAL_STOCK_DEFAULT)
        assert canonical_physical_state(0.0)["capital_stock_teh"] == 0.0

    def test_scales_with_baseline(self):
        # Different baselines scale proportionally
        a = effective_capital_from_epsilon(500_000.0, 0.50)
        b = effective_capital_from_epsilon(1_000_000.0, 0.50)
        assert b == pytest.approx(2 * a)


# ---------------------------------------------------------------------------
# Physical-state API: domain functions with no epsilon
# ---------------------------------------------------------------------------

class TestPhysicalStateAPI:
    """Verify that domain functions work correctly when epsilon is None (new API)."""

    def test_personal_eoh_no_epsilon_uses_default_dist(self):
        # Without epsilon, uses AGE_GROUPS default fractions
        result = personal_eoh(population=1_000_000)
        assert result > 0.0

    def test_personal_eoh_explicit_age_dist(self):
        dist = {"infant": 0.05, "child": 0.15, "working_age": 0.65, "elderly": 0.15}
        result = personal_eoh(population=1_000_000, age_distribution=dist)
        assert result > 0.0

    def test_infrastructure_eoh_no_epsilon(self):
        result = infrastructure_eoh(capital_stock=2_000_000_000.0)
        assert result > 0.0

    def test_ecological_eoh_explicit_monitoring(self):
        # monitoring_capability overrides any epsilon default
        r_low  = ecological_eoh(0.70, monitoring_capability=0.20, deferred=1_000_000.0)
        r_high = ecological_eoh(0.70, monitoring_capability=0.90, deferred=1_000_000.0)
        assert r_high > r_low, "Higher monitoring makes more deferred obligations visible"

    def test_knowledge_eoh_no_epsilon(self):
        # Without epsilon, complexity_per_unit defaults to 1.0
        result = knowledge_eoh(knowledge_base_size=5.0,
                               skill_decay_rate=SKILL_TRANSMISSION_RATE)
        assert result == pytest.approx(KNOWLEDGE_EOH_BASE * 5.0 * 1.0 * SKILL_TRANSMISSION_RATE)

    def test_knowledge_eoh_explicit_complexity(self):
        # Explicit complexity_per_unit used directly
        result = knowledge_eoh(
            knowledge_base_size=5.0,
            skill_decay_rate=SKILL_TRANSMISSION_RATE,
            complexity_per_unit=3.0,
        )
        assert result == pytest.approx(KNOWLEDGE_EOH_BASE * 5.0 * 3.0 * SKILL_TRANSMISSION_RATE)

    def test_total_eoh_no_epsilon(self):
        result = total_eoh(
            population=1_000_000,
            capital_stock=2_000_000_000.0,
            ecosystem_health=0.70,
            knowledge_complexity=1.0,
        )
        assert result["total"] > 0.0
        assert all(v >= 0.0 for k, v in result.items() if k != "competency_gap_factor")


# ---------------------------------------------------------------------------
# Backward compatibility: epsilon path matches canonical-trajectory call
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """
    Old callers pass epsilon explicitly. New callers pass canonical_physical_state.
    The two must produce identical results across the arc.
    """

    EPS_VALUES = [0.0, 0.20, 0.50, 0.80, 0.99]
    POP = 1_000_000.0
    CAPITAL = CAPITAL_STOCK_DEFAULT

    def _canonical_call(self, eps: float) -> dict:
        """New-API call using canonical_physical_state explicitly."""
        state = canonical_physical_state(eps)
        return total_eoh(
            epsilon=None,
            population=self.POP,
            age_distribution=state["age_distribution"],
            capital_stock=state["capital_stock_teh"],
            capital_age_ratio=state["capital_age_ratio"],
            ecosystem_health=state["ecosystem_health"],
            knowledge_complexity=state["knowledge_base_size"],
            monitoring_capability=state["monitoring_capability"],
            knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
        )

    def _legacy_call(self, eps: float) -> dict:
        """Old-API call with epsilon — capital_age_ratio from canonical state, not hardcoded."""
        state = canonical_physical_state(eps)
        return total_eoh(
            epsilon=eps,
            population=self.POP,
            capital_stock=self.CAPITAL,
            capital_age_ratio=state["capital_age_ratio"],
        )

    def test_personal_eoh_compat(self):
        for eps in self.EPS_VALUES:
            state = canonical_physical_state(eps)
            p_new = personal_eoh(self.POP, age_distribution=state["age_distribution"])
            p_old = personal_eoh(self.POP, epsilon=eps)
            assert p_new == pytest.approx(p_old, rel=1e-9), f"ε={eps}"

    def test_infrastructure_eoh_compat(self):
        """The physical-state path and the legacy ε path now DIFFER by the
        intercept, and deliberately so (Block III).

        The legacy path treats `self.CAPITAL` as an ε=0 baseline that exists and
        grows; the arc says the apparatus is built FROM nothing. Both are
        internally consistent — they start from different premises about whether
        the caller already has capital. Only the ratio is asserted, since that is
        the part the two share.
        """
        for eps in self.EPS_VALUES:
            state = canonical_physical_state(eps)
            i_new = infrastructure_eoh(
                state["capital_stock_teh"],
                capital_age_ratio=state["capital_age_ratio"],
            )
            i_old = infrastructure_eoh(
                self.CAPITAL,
                capital_age_ratio=state["capital_age_ratio"],
                epsilon=eps,
            )
            # the legacy path carries the caller's baseline; the arc does not
            assert i_old > i_new or eps == 0.0
            if eps > 0.0:
                ratio = i_new / i_old
                expected = (1.0 + 2.0) * eps / (1.0 + 2.0 * eps)
                assert ratio == pytest.approx(expected, rel=1e-9), f"ε={eps}"
        # at ε=0 the arc has no apparatus at all
        assert infrastructure_eoh(
            canonical_physical_state(0.0)["capital_stock_teh"],
            capital_age_ratio=0.3) == 0.0

    def test_ecological_eoh_compat(self):
        for eps in self.EPS_VALUES:
            state = canonical_physical_state(eps)
            e_new = ecological_eoh(
                state["ecosystem_health"],
                monitoring_capability=state["monitoring_capability"],
                deferred=500_000.0,
            )
            e_old = ecological_eoh(
                state["ecosystem_health"],
                epsilon=eps,
                deferred=500_000.0,
            )
            assert e_new == pytest.approx(e_old, rel=1e-9), f"ε={eps}"

    def test_knowledge_eoh_compat(self):
        for eps in self.EPS_VALUES:
            state = canonical_physical_state(eps)
            k_new = knowledge_eoh(
                state["knowledge_base_size"],
                complexity_per_unit=state["knowledge_complexity_per_unit"],
            )
            k_old = knowledge_eoh(1.0, epsilon=eps)
            assert k_new == pytest.approx(k_old, rel=1e-9), f"ε={eps}"

    def test_ecological_breakdown_compat(self):
        for eps in self.EPS_VALUES:
            state = canonical_physical_state(eps)
            bd_new = ecological_eoh_breakdown(
                state["ecosystem_health"],
                monitoring_capability=state["monitoring_capability"],
                deferred=500_000.0,
            )
            bd_old = ecological_eoh_breakdown(
                state["ecosystem_health"],
                epsilon=eps,
                deferred=500_000.0,
            )
            assert bd_new["total"] == pytest.approx(bd_old["total"], rel=1e-9), f"ε={eps}"
            assert bd_new["monitoring_factor"] == pytest.approx(
                bd_old["monitoring_factor"], rel=1e-9
            ), f"ε={eps}"


# ---------------------------------------------------------------------------
# Monotonicity across the arc
# ---------------------------------------------------------------------------

class TestArcMonotonicity:
    """Core EOH signals must be well-behaved across the full arc ε ∈ [0, 0.99]."""

    EPS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.99]
    POP = 1_000_000.0
    CAPITAL = CAPITAL_STOCK_DEFAULT

    def _canonical_totals(self) -> list[dict]:
        return [
            total_eoh(
                epsilon=eps,
                population=self.POP,
                capital_stock=self.CAPITAL,
            )
            for eps in self.EPS
        ]

    def test_knowledge_eoh_grows_with_epsilon(self):
        totals = self._canonical_totals()
        knowledge = [t["knowledge"] for t in totals]
        # knowledge EOH grows monotonically with ε
        for i in range(len(knowledge) - 1):
            assert knowledge[i + 1] >= knowledge[i], (
                f"Knowledge EOH non-monotone at ε={self.EPS[i+1]}: "
                f"{knowledge[i]} → {knowledge[i+1]}"
            )

    def test_infrastructure_eoh_grows_with_epsilon(self):
        totals = self._canonical_totals()
        infra = [t["infrastructure"] for t in totals]
        for i in range(len(infra) - 1):
            assert infra[i + 1] >= infra[i], (
                f"Infra EOH non-monotone at ε={self.EPS[i+1]}"
            )

    def test_all_domains_positive(self):
        for t in self._canonical_totals():
            for domain in ["personal", "infrastructure", "ecological", "knowledge"]:
                assert t[domain] >= 0.0

    def test_total_equals_sum_of_domains(self):
        for t in self._canonical_totals():
            expected = t["personal"] + t["infrastructure"] + t["ecological"] + t["knowledge"]
            assert t["total"] == pytest.approx(expected, rel=1e-9)
