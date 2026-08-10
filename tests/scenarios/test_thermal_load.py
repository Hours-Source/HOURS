"""
Tests for scenarios/thermal_load.py — the thermal obligation carried in the ledger.

Two findings are pinned here and they point opposite ways:
  1. The obligation is TINY as a share of total EOH (~0.12%), because the
     ecological domain it lands in is itself a rounding error. It read 0.078%
     before PERSONAL_EOH_BASE was repriced 1500 → 1000 — the obligation did not
     grow, the denominator shrank.
  2. It is nonetheless UNAFFORDABLE at low ε, where labour income is thin.

Arc coverage at ε ∈ {0.0, 0.40, 0.99} throughout.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.scenarios.thermal_load import (
    REFERENCE_THERMAL_FLOW_EOH,
    thermal_load_arc,
    thermal_load_verdict,
)

ARC = (0.0, 0.40, 0.99)


# ---------------------------------------------------------------------------
# reachability — the gap this scenario closes
# ---------------------------------------------------------------------------

def test_obligation_actually_reaches_the_ecological_domain():
    rows = thermal_load_arc(arc=ARC)
    for r in rows:
        assert r["ecological_loaded_eoh"] == pytest.approx(
            r["ecological_baseline_eoh"] + REFERENCE_THERMAL_FLOW_EOH
        )


def test_zero_obligation_is_a_clean_no_op():
    loaded = thermal_load_arc(thermal_obligation=0.0, arc=ARC)
    for r in loaded:
        assert r["load_ratio"] == pytest.approx(1.0)
        assert r["thermal_share_of_total"] == 0.0


def test_obligation_flows_into_teh_creation():
    with_ob = thermal_load_arc(arc=(0.40,))[0]
    without = thermal_load_arc(thermal_obligation=0.0, arc=(0.40,))[0]
    assert with_ob["teh_created"] > without["teh_created"]


# ---------------------------------------------------------------------------
# finding 1 — negligible in the ledger
# ---------------------------------------------------------------------------

def test_load_ratio_is_large_on_the_domain():
    """It more than triples the ecological domain."""
    for r in thermal_load_arc(arc=ARC):
        assert r["load_ratio"] > 3.0


def test_share_of_total_is_tiny():
    """…and is ~0.12% of the ledger. Both are true; that is the point."""
    for r in thermal_load_arc(arc=ARC):
        assert r["thermal_share_of_total"] < 0.002


def test_personal_dominates_the_low_arc_even_loaded():
    """
    Block K-IV loosened this from a flat >0.86 to an arc-dependent claim.
    Putting knowledge on its measured footing cut personal's share from
    94% to 51% across the arc, so "personal dominates everywhere" is no longer
    true at high ε. It remains true where the thermal obligation actually bites
    — the low arc, where the coverage gap lives.

    The thermal domain-balance finding is UNAFFECTED and is what this file is
    about: the obligation is still ~0.1% of total EOH and the ecological domain
    is still ~2.5 h/person·yr against personal's 1,400+.
    """
    for r in thermal_load_arc(arc=ARC):
        assert r["ecological_per_capita"] < 5.0
        # > 1,400 until the elderly revalue took w to 1.3016; the claim under
        # test is personal DOMINANCE, which 1,301.6 carries just as well.
        assert r["personal_per_capita"] > 1_250.0
        if r["epsilon"] <= 0.40:
            # > 0.84 until the knowledge re-anchor; 0.819 at ε=0.40 still
            # leaves personal the dominant domain where the obligation bites.
            assert r["personal_share_of_total"] > 0.81

    top = thermal_load_arc(arc=ARC)[-1]
    # 0.511 at the K-IV anchor; 0.562 after the Finding-E re-anchor gave back
    # ~5 points at the top of the arc.
    # 0.562 → 0.530 with the elderly revalue, then → 0.461 with the knowledge
    # re-anchor that followed it. Personal is no longer the largest domain at
    # the top of the arc; knowledge is.
    assert top["personal_share_of_total"] == pytest.approx(0.461, abs=0.01)


def test_verdict_reports_marginal_at_shipped_calibration():
    """0.12% of total EOH — above the 0.1% line, far below materiality.

    Was NEGLIGIBLE (0.078%) at PERSONAL_EOH_BASE = 1500. It crossed the line
    because the reprice shrank the DENOMINATOR, not because the obligation grew
    — which is itself the domain-balance point in miniature.
    """
    v = thermal_load_verdict(arc=ARC)
    assert v["negligible_in_ledger"] is False
    assert v["max_share_of_total"] < 0.002
    assert "MARGINAL" in v["verdict"]
    assert "not because the obligation grew" in v["verdict"]


def test_verdict_flips_to_material_when_the_obligation_is_large():
    """The flag discriminates — it is not hard-coded to the shipped answer."""
    v = thermal_load_verdict(thermal_obligation=5.0e8, arc=ARC)
    assert v["negligible_in_ledger"] is False
    assert "MATERIAL" in v["verdict"]


# ---------------------------------------------------------------------------
# finding 2 — unaffordable at low ε
# ---------------------------------------------------------------------------

def test_coverage_gap_at_low_epsilon():
    v = thermal_load_verdict(arc=(0.0, 0.20, 0.40, 0.99))
    assert 0.0 in v["coverage_below_one_at"]
    assert v["min_coverage_margin"] < 1.0
    assert "COVERAGE GAP" in v["verdict"]


def test_coverage_rises_with_epsilon():
    rows = thermal_load_arc(arc=(0.0, 0.40, 0.99))
    margins = [r["coverage_margin"] for r in rows]
    assert margins == sorted(margins)


def test_carrying_the_obligation_reduces_coverage():
    loaded = thermal_load_arc(arc=(0.99,))[0]["coverage_margin"]
    unloaded = thermal_load_arc(thermal_obligation=0.0, arc=(0.99,))[0]["coverage_margin"]
    assert loaded < unloaded
    # the drop tracks the load ratio — carrying it costs ~3.5× of coverage
    assert unloaded / loaded == pytest.approx(3.5, rel=0.05)


# ---------------------------------------------------------------------------
# ε-coherence and input validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", [0.0, 0.40, 0.99])
def test_arc_coherent_at_key_epsilons(eps):
    r = thermal_load_arc(arc=(eps,))[0]
    for key in ("thermal_eoh", "ecological_loaded_eoh", "total_eoh",
                "teh_created", "load_ratio"):
        assert math.isfinite(r[key]) and r[key] >= 0.0
    assert 0.0 <= r["thermal_share_of_total"] <= 1.0
    assert 0.0 <= r["personal_share_of_total"] <= 1.0


def test_obligation_is_epsilon_invariant():
    """Measured forcing is an observation, not a sensing artifact."""
    rows = thermal_load_arc(arc=(0.0, 0.40, 0.99))
    assert len({r["thermal_eoh"] for r in rows}) == 1
    assert len({round(r["load_ratio"], 9) for r in rows}) == 1


def test_rejects_bad_inputs():
    with pytest.raises(ValueError):
        thermal_load_arc(thermal_obligation=-1.0)
    with pytest.raises(ValueError):
        thermal_load_arc(population=0.0)
