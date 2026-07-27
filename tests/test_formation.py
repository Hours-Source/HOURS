"""
Tests for research/formation.py — §8.9c formation feedback: the investment
supply curve, the incentive-compatible share, the funding waterfall, the
capacity-derived ε, the null anchor, both priority policies, the escalation
latch, and the Condition III (zero-interest advantage) finding.
"""

import math

import pytest

from hours_eoh.data import (
    FORMATION_DEPRECIATION_RATE,
    FORMATION_FULL_SUPPLY_RATE,
    FORMATION_HURDLE_RATE_MIN,
    RECAL_CAPITAL_OUTPUT_RATIO,
)
from hours_eoh.research.formation import (
    formation_feedback_simulation,
    formation_verdict,
    incentive_compatible_share,
    investment_supply_fraction,
    private_return,
)

# Fiat-like counterfactual knobs (interest-bearing outside option raises the
# returns investors demand): used by the Condition III tests.
FIAT_FULL_SUPPLY = 0.18
FIAT_HURDLE = 0.06


# ---------------------------------------------------------------------------
# Supply analytics
# ---------------------------------------------------------------------------

class TestSupplyAnalytics:
    def test_gross_return(self):
        # r_gross = 1/ν − δ = 0.25 − 0.05 = 0.20 at defaults.
        assert private_return(0.0) == pytest.approx(
            1.0 / RECAL_CAPITAL_OUTPUT_RATIO - FORMATION_DEPRECIATION_RATE
        )

    def test_return_linear_in_share(self):
        assert private_return(0.5) == pytest.approx(0.5 * private_return(0.0))
        assert private_return(1.0) == 0.0

    def test_full_supply_at_zero_share(self):
        assert investment_supply_fraction(0.0) == 1.0

    def test_full_supply_up_to_s_star(self):
        s_star = incentive_compatible_share()
        assert investment_supply_fraction(s_star) == pytest.approx(1.0)

    def test_zero_supply_at_high_share(self):
        # f = 0 once r_priv ≤ r_min: s ≥ 1 − r_min/r_gross = 0.9 at defaults.
        assert investment_supply_fraction(0.9) == pytest.approx(0.0)
        assert investment_supply_fraction(1.0) == 0.0

    def test_supply_midpoint(self):
        # Linear between the rates: s = 0.7 → r_priv = 0.06 → f = 0.5.
        assert investment_supply_fraction(0.7) == pytest.approx(0.5)

    def test_s_star_analytic(self):
        # s* = 1 − r_full/r_gross = 1 − 0.10/0.20 = 0.50 at defaults.
        assert incentive_compatible_share() == pytest.approx(0.5)

    def test_s_star_fiat_counterfactual(self):
        # THE CONDITION III FINDING (analytic half): with a fiat-like
        # required return the charter is free only up to s* ≈ 0.10 —
        # zero interest quintuples the affordable charter share.
        assert incentive_compatible_share(
            full_supply_rate=FIAT_FULL_SUPPLY
        ) == pytest.approx(0.1)

    def test_rejects_bad_share(self):
        with pytest.raises(ValueError):
            private_return(1.5)

    def test_rejects_inverted_supply_rates(self):
        with pytest.raises(ValueError):
            investment_supply_fraction(0.5, hurdle_rate_min=0.2,
                                       full_supply_rate=0.1)

    def test_rejects_infeasible_full_supply_rate(self):
        with pytest.raises(ValueError):
            incentive_compatible_share(full_supply_rate=0.5)  # > r_gross


# ---------------------------------------------------------------------------
# Null anchor — the baseline every feedback effect is measured against
# ---------------------------------------------------------------------------

class TestNullAnchor:
    def test_reproduces_canonical_pace(self):
        # s pinned to 0 (no charter): full private funding, and the sim must
        # reproduce the canonical ~50-year arc (0.95/0.02 = 47.5 yr).
        v = formation_verdict(formation_feedback_simulation(
            n_years=60, charter_share_override=0.0))
        assert v["years_to_eps_95"] == 47
        assert abs(v["delay_years"]) < 1.0
        assert not v["stalled"]
        assert v["invariant_holds"]

    def test_full_private_supply_throughout(self):
        rows = formation_feedback_simulation(
            n_years=60, charter_share_override=0.0)
        assert all(r["supply_fraction"] == 1.0 for r in rows)
        assert all(r["commons_funded"] == 0.0 for r in rows[1:])


# ---------------------------------------------------------------------------
# Simulation mechanics
# ---------------------------------------------------------------------------

class TestSimulationMechanics:
    @pytest.mark.parametrize("priority", ["share", "dividend"])
    def test_conservation_every_year(self, priority):
        for r in formation_feedback_simulation(n_years=80, priority=priority):
            assert r["commons_capital"] + r["private_capital"] == pytest.approx(
                r["capital_stock"]
            )

    @pytest.mark.parametrize("priority", ["share", "dividend"])
    def test_tau_is_a_share_and_non_decreasing(self, priority):
        rows = formation_feedback_simulation(n_years=80, priority=priority)
        taus = [r["tau"] for r in rows]
        assert all(0.0 < t <= 1.0 for t in taus)
        assert all(b >= a - 1e-9 for a, b in zip(taus, taus[1:]))

    @pytest.mark.parametrize("priority", ["share", "dividend"])
    def test_eps_monotone_non_decreasing(self, priority):
        rows = formation_feedback_simulation(n_years=80, priority=priority)
        eps = [r["eps_actual"] for r in rows]
        assert all(b >= a - 1e-9 for a, b in zip(eps, eps[1:]))

    def test_charter_never_exceeds_full_take(self):
        for r in formation_feedback_simulation(n_years=80)[1:]:
            assert 0.0 <= r["s_applied"] <= 1.0

    def test_private_ownership_split(self):
        # Private capital gains (1−s)·private_funded each year (minus the
        # slow estate flow): with estates off, growth matches exactly.
        rows = formation_feedback_simulation(
            n_years=40, estate_escheat_share=0.0)
        for prev, cur in zip(rows, rows[1:]):
            gain = (1.0 - cur["s_applied"]) * cur["private_funded"]
            assert cur["private_capital"] - prev["private_capital"] == (
                pytest.approx(gain, abs=1.0)
            )

    def test_rejects_bad_priority(self):
        with pytest.raises(ValueError):
            formation_feedback_simulation(priority="growth")

    def test_rejects_bad_override(self):
        with pytest.raises(ValueError):
            formation_feedback_simulation(charter_share_override=1.5)

    def test_verdict_rejects_empty(self):
        with pytest.raises(ValueError):
            formation_verdict([])


# ---------------------------------------------------------------------------
# Priority policies — the §8.9c verdicts
# ---------------------------------------------------------------------------

class TestSharePriority:
    def test_holds_canonical_pace(self):
        # THE HEADLINE: with formation funded first, the feedback costs the
        # arc NOTHING in time — the commons budget always covers the
        # residual the charter share scares off.
        v = formation_verdict(formation_feedback_simulation(
            n_years=60, priority="share"))
        assert v["years_to_eps_95"] == 47
        assert v["invariant_holds"]
        assert not v["stalled"]

    def test_dividend_pays_the_price_mid_arc(self):
        # Feedback-consistent D ≈ 113 at ε ≈ 0.41 (static §8.9b gross: 302).
        rows = formation_feedback_simulation(n_years=60, priority="share")
        r20 = rows[20]
        assert r20["eps_actual"] == pytest.approx(0.406, abs=0.01)
        assert r20["dividend_per_capita"] == pytest.approx(113.0, abs=15.0)

    def test_cap_region_funding_hole_is_commons_funded(self):
        # Where s = 1 private supply is zero and the commons pays for all
        # formation — the §8.9b funding hole, closed and visible.
        rows = formation_feedback_simulation(n_years=60, priority="share")
        cap_rows = [r for r in rows[1:] if r["s_applied"] == 1.0
                    and r["dk_needed"] > 1.0]
        assert cap_rows
        for r in cap_rows:
            assert r["supply_fraction"] == 0.0
            assert r["commons_funded"] > 0.0

    def test_underwriting_carries_the_arc(self):
        # Under the feedback-consistent dividend, self-financing arrives
        # only at ε ≈ 0.86 (static §8.9b claimed 0.30): the underwritten
        # channel dominates the transition.
        rows = formation_feedback_simulation(n_years=60, priority="share")
        mid = [r for r in rows if 0.1 <= r["eps_actual"] <= 0.85]
        assert all(r["channel"] == "underwritten" for r in mid)
        first_self = next(r for r in rows if r["channel"] == "self"
                          and r["eps_actual"] > 0.0)
        assert first_self["eps_actual"] == pytest.approx(0.86, abs=0.03)
        assert rows[-1]["channel"] == "self"

    def test_estate_conversion_visible_post_arc(self):
        # After ε plateaus, τ keeps rising via the D5-extension escheat —
        # generational conversion at work.
        rows = formation_feedback_simulation(n_years=120, priority="share")
        assert rows[-1]["tau"] > rows[60]["tau"]


class TestDividendPriority:
    def test_arc_crawls_never_completes(self):
        # Dividend-first does not hard-stall — it CRAWLS: partial private
        # supply keeps some formation going, but ε reaches only ≈ 0.60
        # after 120 years and never hits 0.95.
        v = formation_verdict(formation_feedback_simulation(
            n_years=120, priority="dividend"))
        assert v["years_to_eps_95"] is None
        assert v["terminal_eps"] == pytest.approx(0.601, abs=0.02)
        assert not v["stalled"]  # crawl, not stall — worth distinguishing

    def test_commons_never_funds_formation(self):
        rows = formation_feedback_simulation(n_years=60, priority="dividend")
        assert all(r["commons_funded"] == 0.0 for r in rows)

    def test_invariant_still_holds_on_the_crawl(self):
        # Honest nuance: even the crawling arc never breaks exit — capacity
        # does not depend on the dividend.
        v = formation_verdict(formation_feedback_simulation(
            n_years=120, priority="dividend"))
        assert v["invariant_holds"]


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------

class TestEscalation:
    def test_never_fires_at_canonical_defaults(self):
        rows = formation_feedback_simulation(
            n_years=80, priority="share", escalation=True)
        assert not any(r["escalation_active"] for r in rows)

    def test_forced_escalation_fires_and_latches(self):
        rows = formation_feedback_simulation(
            n_years=80, priority="share", escalation=True,
            min_viable_population=200_000.0,
        )
        active = [r["escalation_active"] for r in rows]
        assert any(active)
        first = active.index(True)
        assert all(active[first:])  # latched


# ---------------------------------------------------------------------------
# The Condition III finding — zero interest is the doctrine's ally
# ---------------------------------------------------------------------------

class TestConditionIIIFinding:
    def test_fiat_world_drives_dividend_to_zero_mid_arc(self):
        # With fiat-like required returns the commons must cannibalize the
        # dividend ENTIRELY for a stretch of the arc to hold pace; in the
        # zero-interest world it never does.
        fiat = formation_verdict(formation_feedback_simulation(
            n_years=60, priority="share",
            full_supply_rate=FIAT_FULL_SUPPLY, hurdle_rate_min=FIAT_HURDLE,
        ))
        zero = formation_verdict(formation_feedback_simulation(
            n_years=60, priority="share"))
        assert fiat["min_dividend_after_takeoff"] == 0.0
        assert zero["min_dividend_after_takeoff"] > 0.0

    def test_fiat_world_worsens_the_crawl(self):
        fiat = formation_verdict(formation_feedback_simulation(
            n_years=120, priority="dividend",
            full_supply_rate=FIAT_FULL_SUPPLY, hurdle_rate_min=FIAT_HURDLE,
        ))
        zero = formation_verdict(formation_feedback_simulation(
            n_years=120, priority="dividend"))
        assert fiat["terminal_eps"] < zero["terminal_eps"]

    def test_invariant_survives_even_the_fiat_counterfactual(self):
        # Underwriting capacity carries exit even where the dividend dies.
        v = formation_verdict(formation_feedback_simulation(
            n_years=60, priority="share",
            full_supply_rate=FIAT_FULL_SUPPLY, hurdle_rate_min=FIAT_HURDLE,
        ))
        assert v["invariant_holds"]


# ---------------------------------------------------------------------------
# Verdict shape
# ---------------------------------------------------------------------------

class TestVerdict:
    def test_keys(self):
        v = formation_verdict(formation_feedback_simulation(n_years=10))
        assert set(v.keys()) == {
            "invariant_holds", "first_failure_year", "years_to_eps_95",
            "delay_years", "stalled", "stall_eps", "terminal_eps", "s_star",
            "min_dividend_after_takeoff", "terminal_dividend", "n_years",
        }

    def test_s_star_reported(self):
        v = formation_verdict(formation_feedback_simulation(n_years=10))
        assert v["s_star"] == pytest.approx(0.5)
