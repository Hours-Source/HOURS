"""
Tests for Path C — the measured top-down thermal residual (research/thermal_path_c.py).

Reproduces the handoff's key figures (Φ, ψ*, collective U, decarbonization, ε_max),
asserts the provenance tiers ship intact, and checks the measured thermal ceiling
flows into the corridor (F11 → a real collective-level bound).
"""

from __future__ import annotations

import pytest

from hours_eoh.research.thermal_path_c import (
    load_path_c_inputs,
    dissipation_flux,
    world_dissipation,
    measured_epsilon_max,
    budget_psi_star,
    budget_opens_at,
    collective_dissipation_density,
    utilization_regime,
    collective_utilization,
    all_collectives_utilization,
    decarbonization_headroom,
    global_ceiling,
)
from hours_eoh.research.thermal_path_c import determinacy_zone
from hours_eoh.research.corridor import measured_thermal_ceiling, corridor, Ceiling
from hours_eoh.data import THERMAL_EPS_CURRENT


# ---------------------------------------------------------------------------
# E1 dissipation
# ---------------------------------------------------------------------------

def test_world_dissipation_reproduces_handoff():
    assert world_dissipation() / 1e12 == pytest.approx(17.71, abs=0.02)


def test_dissipation_kappa_weighting():
    # fossil at κ=1 fully counts; flux-redirecting at κ=0 drops out
    phi = dissipation_flux({"coal": 100.0, "hydro": 100.0}, {"coal": 1.0, "hydro": 0.0})
    coal_only = dissipation_flux({"coal": 100.0}, {"coal": 1.0})
    assert phi == pytest.approx(coal_only)


def test_dissipation_missing_kappa_defaults_conservative():
    # missing κ → 1.0 (conservative), not 0
    assert dissipation_flux({"x": 100.0}, {}) > 0.0


# ---------------------------------------------------------------------------
# budget + Eq. C1
# ---------------------------------------------------------------------------

def test_psi_star_reproduces():
    # post-C5 (total ERF 3.366): the 3.5 K case is the handoff 2.0 §4.3 headline
    assert budget_psi_star(3.5, "net_erf") == pytest.approx(2.521, abs=0.005)
    assert budget_psi_star(3.0, "net_erf") == pytest.approx(0.707, abs=0.005)


def test_psi_star_zero_below_threshold():
    # post-C5 the net-ERF budget opens at 2.805 K → 2.5 K is now CLOSED, where
    # the superseded 2.72 forcing gave a positive 0.846. The correction moved
    # the whole 2.5–2.8 K band from budgeted to unbudgeted.
    assert budget_psi_star(2.5, "net_erf") == 0.0
    assert budget_psi_star(2.0, "net_erf") == 0.0


def test_budget_opens_at():
    assert budget_opens_at("net_erf") == pytest.approx(2.805, abs=0.01)
    assert budget_opens_at("wmghg") == pytest.approx(2.988, abs=0.01)
    assert budget_opens_at("anthro") == pytest.approx(2.587, abs=0.01)


def test_measured_epsilon_max_c1():
    # ε_max = ε_current · alloc / Φ ; post-C5 the 3.0 K net case = 2.16
    g = global_ceiling(3.0, "net_erf")
    assert g["epsilon_max"] == pytest.approx(2.16, abs=0.03)
    assert g["binds_below_1"] is False


def test_binding_multiple_equals_epsilon_max():
    """The Eq. C1 identity that the withdrawn '10–50×' claim contradicted:
    binding needs Φ ≥ ε_current·budget, so the binding multiple IS ε_max."""
    g = global_ceiling(3.0, "net_erf")
    eps_max = g["epsilon_max"]
    assert eps_max is not None
    phi_at_binding = THERMAL_EPS_CURRENT * g["allocated_budget_w"]
    assert phi_at_binding / g["phi_w"] == pytest.approx(eps_max, rel=1e-9)


def test_epsilon_max_scales_with_chosen_eps_current():
    """ε_max is directly proportional to a CHOSEN tier-D constant — halving
    ε_current halves the ceiling and brings it to the edge of binding."""
    g = global_ceiling(3.0, "net_erf", eps_current=0.20)
    assert g["epsilon_max"] == pytest.approx(1.08, abs=0.03)


def test_measured_epsilon_max_unbudgeted_returns_none():
    assert measured_epsilon_max(0.0, 1e13) is None


def test_global_ceiling_nonbinding_note_is_conditional():
    g = global_ceiling(3.0, "net_erf")
    assert "conditional" in g["note"]
    # the superseded multiple must not reappear
    assert "10–50" not in g["note"]


# ---------------------------------------------------------------------------
# F11 collective utilization
# ---------------------------------------------------------------------------

def test_singapore_in_contact():
    # post-C5 U roughly quadruples at 3.0 K (22.4 → 84.2): same regime, far worse margin.
    # Since P2, η is applied BY DEFAULT when the name resolves in the shipped table, so
    # the operative figure is 79.2 — Singapore sheds slightly better than the claimed-land
    # mean (η = 1.063). The un-weighted value stays recoverable with eta=1.0, and the two
    # are pinned together so the wiring cannot drift unnoticed.
    c = collective_utilization("Singapore", 1.4, 7.3e8, 0.98, delta_t_lo=3.0)
    raw = collective_utilization("Singapore", 1.4, 7.3e8, 0.98, delta_t_lo=3.0, eta=1.0)
    assert raw["utilization"] == pytest.approx(84.2, abs=0.5)
    assert c["utilization"] == pytest.approx(79.2, abs=0.5)
    assert c["utilization"] == pytest.approx(raw["utilization"] / c["eta_applied"], rel=1e-9)
    assert c["in_contact"] is True
    assert c["regime"] == "contact"


def test_world_below_floor():
    c = collective_utilization("World", 600.0, 1.35e14, 0.931, delta_t_lo=3.0)
    assert c["utilization"] == pytest.approx(0.19, abs=0.01)
    assert c["regime"] == "below_floor"


def test_germany_uk_cross_into_contact_post_c5():
    """§4.3: at 3.0 K the correction pushes Germany and the UK over U = 1 —
    marginal collectives must be re-read post-C5, not carried over."""
    for name, ej, land, share in [("Germany", 11.5, 3.57e11, 0.80),
                                  ("United Kingdom", 7.0, 2.43e11, 0.83)]:
        c = collective_utilization(name, ej, land, share, delta_t_lo=3.0)
        assert c["in_contact"] is True, name


def test_utilization_regime_boundaries():
    assert utilization_regime(2.0, 1.0)[1] == "contact"
    assert utilization_regime(0.6, 1.0)[1] == "standing_exposure"
    assert utilization_regime(0.1, 1.0)[1] == "below_floor"
    assert utilization_regime(1.0, 0.0)[1] == "unbudgeted"


def test_density_rejects_zero_land():
    with pytest.raises(ValueError):
        collective_dissipation_density(1.0, 0.0, 0.9)


def test_all_collectives_covers_dataset():
    rows = all_collectives_utilization(3.0)
    names = {r["name"] for r in rows}
    assert {"Singapore", "World", "United States"} <= names


# ---------------------------------------------------------------------------
# F3 decarbonization headroom
# ---------------------------------------------------------------------------

def test_decarbonization_headroom_reproduces():
    h = decarbonization_headroom(3.0, "net_erf")
    assert h["gain_w"] / 1e12 == pytest.approx(1374, abs=5)
    # ~78× current world dissipation — the load-bearing signal, grown by C5
    assert h["gain_over_current_dissipation"] == pytest.approx(77.6, abs=0.5)


def test_decarbonization_gain_is_linear_in_removable_forcing():
    """The basis IS the answer: gain = (1−r)·F·A_earth, so the three bases give
    three different headlines. Open sign-off item — see the F3 basis caveat."""
    total = decarbonization_headroom(3.0, "net_erf")["gain_w"] / 1e12
    anthro = decarbonization_headroom(3.0, "anthro")["gain_w"] / 1e12
    wmghg = decarbonization_headroom(3.0, "wmghg")["gain_w"] / 1e12
    assert total == pytest.approx(1374, abs=5)
    assert anthro == pytest.approx(1267, abs=5)
    assert wmghg == pytest.approx(1463, abs=5)
    assert anthro < total < wmghg


def test_decarbonization_gain_saturates_above_the_opening_threshold():
    """gain = (1−r)·min(F, λ·ΔT_lo)·A_earth. ABOVE the opening threshold the ΔT
    term drops out and the gain is the full removable forcing; BELOW it the gain
    is capped by the whole temperature allowance and still rises with ΔT. F3
    survives either way — there is headroom to recover even where there is no
    budget today (`binds_now` False, `gain_w` large)."""
    at_2k = decarbonization_headroom(2.0, "net_erf")   # below threshold: capped
    at_3k = decarbonization_headroom(3.0, "net_erf")   # above: saturated
    at_4k = decarbonization_headroom(4.0, "net_erf")
    assert at_2k["allocated_now_w"] == 0.0
    assert at_2k["gain_w"] / 1e12 == pytest.approx(979, abs=5)
    assert at_2k["gain_w"] < at_3k["gain_w"]
    assert at_3k["gain_w"] == pytest.approx(at_4k["gain_w"], rel=1e-9)


# ---------------------------------------------------------------------------
# provenance ships intact
# ---------------------------------------------------------------------------

def test_provenance_tiers_present():
    d = load_path_c_inputs()
    assert set(d["provenance_tiers"]) == {"A", "B", "C", "D"}
    # the load-bearing caveats survive into the shipped dataset
    assert "WARNING" in d["national_data"]["_WARNING"] or d["national_data"]["_tier"] == "C"
    assert d["climate_parameters"]["delta_T_lo_cases"]["tier"] == "D"


# ---------------------------------------------------------------------------
# measured thermal ceiling → corridor
# ---------------------------------------------------------------------------

def test_measured_thermal_ceiling_binds_in_contact():
    c = measured_thermal_ceiling(22.4, epsilon_current=0.40)
    assert c["binding"] is True
    assert c["epsilon_ceiling"] == pytest.approx(0.40)
    assert "CONTACT" in c["status"]


def test_measured_thermal_ceiling_nonbinding_below_floor():
    c = measured_thermal_ceiling(0.05, epsilon_current=0.40)
    assert c["binding"] is False


def test_measured_thermal_closes_corridor_for_dense_collective():
    # Singapore: U=22.4 → thermal binds at ε_current=0.40, below a 0.52 survival floor
    sg = collective_utilization("Singapore", 1.4, 7.3e8, 0.98, delta_t_lo=3.0)
    tc = measured_thermal_ceiling(sg["utilization"], epsilon_current=0.40)
    rep = corridor(0.52, [tc])
    assert rep["feasible"] is False
    assert rep["binding_ceiling"] == "thermal_measured"


def test_measured_thermal_leaves_corridor_open_below_floor():
    us = collective_utilization("United States", 95.0, 9.15e12, 0.90, delta_t_lo=3.0)
    tc = measured_thermal_ceiling(us["utilization"], epsilon_current=0.40)
    rep = corridor(0.40, [tc])
    assert rep["feasible"] is True
    assert rep["success"] is True


# ---------------------------------------------------------------------------
# determinacy map (§4.2) — the result C5 made computable
# ---------------------------------------------------------------------------

def test_determinacy_zones():
    # below p05/λ: no budget on ANY forcing in the band
    assert determinacy_zone(2.0)["zone"] == "determinate_unbudgeted"
    # between the two: forcing uncertainty alone spans both regimes
    assert determinacy_zone(3.0)["zone"] == "indeterminate"
    assert determinacy_zone(3.0)["robust"] is False
    # above p95/λ: a budget exists even on the least favourable forcing
    assert determinacy_zone(3.5)["zone"] == "determinate_budgeted"


def test_determinacy_thresholds_and_txx_conversion():
    z = determinacy_zone(3.0)
    assert z["unbudgeted_below_k"] == pytest.approx(2.168, abs=0.01)
    assert z["budgeted_above_k"] == pytest.approx(3.418, abs=0.01)
    # C6: assess in land extremes, ÷1.48 to convert back
    assert z["unbudgeted_below_txx_k"] == pytest.approx(3.209, abs=0.01)
    assert z["budgeted_above_txx_k"] == pytest.approx(5.059, abs=0.01)


def test_upper_determinate_zone_is_probably_unreachable():
    """The §4.2 conclusion: reporting determinate HEADROOM needs ~5.1 K of land
    extreme warming. The determinate answer available is the lower one."""
    assert determinacy_zone(3.0)["budgeted_above_txx_k"] > 5.0


# ---------------------------------------------------------------------------
# H — the measured headroom multiple (the ε_current fix)
# ---------------------------------------------------------------------------

def test_headroom_multiple_is_the_measured_content():
    """H = budget/Φ contains no chosen constant; ε_max = H·ε_current does."""
    from hours_eoh.research.thermal_path_c import headroom_multiple
    g = global_ceiling(3.0)
    assert g["headroom_multiple"] == pytest.approx(5.39, rel=0.01)
    assert g["epsilon_max"] == pytest.approx(
        g["headroom_multiple"] * g["eps_current"], rel=1e-9)


def test_H_is_invariant_to_the_chosen_epsilon():
    """The whole point: changing ε_current moves ε_max and leaves H alone."""
    a = global_ceiling(3.0, eps_current=0.40)
    b = global_ceiling(3.0, eps_current=0.20)
    assert a["headroom_multiple"] == pytest.approx(b["headroom_multiple"])
    assert b["epsilon_max"] == pytest.approx(a["epsilon_max"] / 2.0)


def test_headroom_none_when_unbudgeted():
    from hours_eoh.research.thermal_path_c import headroom_multiple
    assert headroom_multiple(0.0, 1e13) is None
    with pytest.raises(ValueError):
        headroom_multiple(1e14, 0.0)


def test_note_leads_with_the_measured_quantity():
    note = global_ceiling(3.0)["note"]
    assert "MEASURED" in note and "H =" in note
    assert "CHOSEN" in note


# ---------------------------------------------------------------------------
# the ε_current sensitivity band — the chosen constant travels with the figure
# ---------------------------------------------------------------------------

def test_epsilon_max_band_brackets_the_point_estimate():
    g = global_ceiling(3.0, eps_current=0.40, eps_current_band=(0.20, 0.60))
    lo, hi = g["epsilon_max_band"]
    assert lo < g["epsilon_max"] < hi
    # ε_max is linear in ε_current, so the band edges are exactly H × edges
    assert lo == pytest.approx(g["headroom_multiple"] * 0.20)
    assert hi == pytest.approx(g["headroom_multiple"] * 0.60)


def test_band_reports_binding_at_the_low_edge():
    """At ΔT_lo = 3.0 K the ceiling is non-binding at 0.40 but binds by ε≈0.185.

    This is the sensitivity §10.2 says exceeds the ΔT_lo sensitivity: the
    headline "non-binding" is a statement about the chosen constant.
    """
    g = global_ceiling(3.0, eps_current=0.40, eps_current_band=(0.10, 0.60))
    assert g["binds_below_1"] is False
    assert g["binds_within_band"] is True
    assert "BINDING at the low edge" in g["note"]


def test_band_not_binding_when_whole_band_clears():
    g = global_ceiling(3.0, eps_current=0.40, eps_current_band=(0.50, 0.60))
    assert g["binds_within_band"] is False
    assert "BINDING at the low edge" not in g["note"]


def test_band_rejects_malformed_range():
    for bad in [(0.0, 0.5), (0.6, 0.2), (0.2, 1.0)]:
        with pytest.raises(ValueError):
            global_ceiling(3.0, eps_current_band=bad)
