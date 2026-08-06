"""
Tests for B3 — maintain vs replace with the embodied-energy pulse
(research/thermal_capital.py).

The first decision the thermal layer can inform, so what matters is that the
trade-off has the right shape and the right sign, not that any figure is precise:
the thermal intensities are still CHOSEN placeholders.
"""

from __future__ import annotations

import pytest

from hours_eoh.research.thermal_capital import (
    maintain_vs_replace,
    replacement_exchange_curve,
)


def test_replacing_always_costs_extra_dissipation():
    """Embodied energy is spent at construction, so every replacement is a pulse.
    Replacing earlier than necessary can only add dissipation."""
    for age in (2.0, 10.0, 25.0):
        r = maintain_vs_replace("transportation", 1e8, age, horizon_years=40.0)
        assert r["replacing_is_thermally_worse"] is True
        assert r["extra_dissipation_j"] > 0.0


def test_replacing_saves_labour():
    """The other side of the trade: age_factor climbs, so a fresh asset carries a
    smaller maintenance obligation."""
    r = maintain_vs_replace("transportation", 1e8, 20.0, horizon_years=40.0)
    assert r["eoh_saved_by_replacing"] > 0.0
    assert r["strategies"]["replace"]["human_eoh"] < r["strategies"]["maintain"]["human_eoh"]


def test_exchange_rate_improves_with_age():
    """THE DECISION RULE. Replacing a nearly-worn asset buys the same relief for a
    smaller pulse, because the embodied energy already bought most of its service
    life. F9 at asset scale."""
    c = replacement_exchange_curve("transportation", 1e8, horizon_years=40.0)
    rates = [r["exchange_rate_eoh_per_tj"] for r in c["curve"]]
    assert all(r is not None for r in rates)
    assert rates[0] < rates[-1]
    assert c["best_over_worst"] > 2.0
    assert "end of life" in c["rule"]


def test_a_long_horizon_makes_the_strategies_converge():
    """Over a horizon that is a whole number of design lives, both strategies do
    the same total aging and the same number of replacements — the difference is
    timing, not quantity. A useful null: the model is not inventing a gap."""
    r = maintain_vs_replace("transportation", 1e8, 20.0, horizon_years=60.0)
    assert r["eoh_saved_by_replacing"] == pytest.approx(0.0, abs=1.0)
    assert r["extra_dissipation_j"] == pytest.approx(0.0, abs=1e9)


def test_human_share_scales_with_epsilon():
    """Labour saved falls with automation; dissipation does not — so the exchange
    rate steepens as ε rises."""
    lo = maintain_vs_replace("transportation", 1e8, 10.0, horizon_years=40.0, epsilon=0.20)
    hi = maintain_vs_replace("transportation", 1e8, 10.0, horizon_years=40.0, epsilon=0.80)
    assert hi["eoh_saved_by_replacing"] < lo["eoh_saved_by_replacing"]
    assert hi["extra_dissipation_j"] == pytest.approx(lo["extra_dissipation_j"], rel=1e-9)


def test_arc_coherent():
    for eps in (0.0, 0.40, 0.90, 0.99):
        r = maintain_vs_replace("transportation", 1e8, 10.0, horizon_years=40.0, epsilon=eps)
        assert r["eoh_saved_by_replacing"] >= 0.0
        assert r["extra_dissipation_j"] > 0.0


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        maintain_vs_replace("not_a_type", 1e8, 10.0)
    with pytest.raises(ValueError):
        maintain_vs_replace("transportation", 1e8, 10.0, horizon_years=0.0)


def test_caveat_travels_with_the_result():
    """Condition proxies utilisation, so an aged asset draws less rather than
    costing more per unit output — the replace case is a conservative floor."""
    r = maintain_vs_replace("transportation", 1e8, 10.0)
    assert "conservative floor" in r["note"]
