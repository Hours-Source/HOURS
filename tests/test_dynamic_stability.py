"""
research/dynamic_stability — the first instrument for limit cycles
(`record/verification.md § Open`: "nothing tests for limit cycles").

Pins the detector on constructed series where the answer is known, then what
it reads off the repo's own forward models — including that the formation
loop's cobweb is INVISIBLE inside 200 years (failure mode 3, in time).
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.research.dynamic_stability import (
    formation_stability, oscillation, simulation_stability,
)


class TestTheDetectorOnKnownSeries:

    def test_monotone(self):
        assert oscillation([i * 0.1 for i in range(50)])["verdict"] == "MONOTONE"

    def test_one_turn_is_a_turning_point(self):
        assert oscillation([-(i - 25) ** 2 for i in range(50)])["verdict"] == "TURNING"

    def test_a_sine_oscillates_at_its_period(self):
        r = oscillation([math.sin(i / 3) for i in range(200)])
        assert r["verdict"] == "OSCILLATING"
        assert r["period"] == pytest.approx(2 * math.pi * 3, rel=0.1)

    def test_a_cycle_that_settles_is_transient(self):
        xs = [math.sin(i) if i < 20 else 0.5 for i in range(200)]
        assert oscillation(xs)["verdict"] == "TRANSIENT"

    @pytest.mark.parametrize("growth,trend", [(0.99, "DECAYING"), (1.0, "STEADY"),
                                               (1.01, "GROWING")])
    def test_the_swing_trend_is_relative_to_the_level(self, growth, trend):
        xs = [10.0 + (growth ** i) * (1 if i % 2 else -1) for i in range(150)]
        assert oscillation(xs)["swing_trend"] == trend

    def test_a_small_cycle_is_seen_and_the_tolerance_is_the_stated_gap(self):
        xs = [1.0 + 1e-6 * (1 if i % 2 else -1) for i in range(100)]
        assert oscillation(xs)["verdict"] == "OSCILLATING"
        assert oscillation(xs, rel_tol=1e-3)["verdict"] == "MONOTONE"

    def test_too_short_is_refused(self):
        with pytest.raises(ValueError):
            oscillation([1.0, 2.0])


class TestTheFormationLoop:

    @pytest.fixture(scope="class")
    def dividend(self):
        return formation_stability(priority="dividend")

    def test_dividend_priority_is_a_period_two_cobweb(self, dividend):
        eps = dividend["fields"]["eps_actual"]
        assert eps["verdict"] == "OSCILLATING"
        assert eps["period"] == 2.0
        assert 190 <= eps["onset"] <= 230
        assert eps["swing_trend"] == "DECAYING"          # bounded, not diverging
        assert dividend["fields"]["private_funded"]["swing_trend"] == "STEADY"
        assert dividend["final_epsilon"] < 0.95           # the cobweb drags the arc

    def test_the_cobweb_is_invisible_inside_two_hundred_years(self):
        assert formation_stability(n_years=200, priority="dividend")[
            "fields"]["eps_actual"]["verdict"] == "MONOTONE"

    def test_share_priority_settles(self):
        r = formation_stability(priority="share")
        assert r["fields"]["eps_actual"]["verdict"] == "MONOTONE"
        assert r["fields"]["private_funded"]["verdict"] == "TRANSIENT"
        assert r["final_epsilon"] == pytest.approx(0.99)


class TestThePeriodEngine:

    @pytest.mark.parametrize("eps", [0.0, 0.40, 0.90, 0.99])
    def test_no_state_field_cycles_at_a_fixed_epsilon(self, eps):
        assert simulation_stability(epsilon=eps)["oscillating"] == []

    def test_no_state_field_cycles_along_the_arc(self):
        r = simulation_stability(n_periods=330, epsilon=0.0, epsilon_delta=0.003)
        assert r["epsilon_end"] == pytest.approx(0.99)
        assert r["oscillating"] == []
