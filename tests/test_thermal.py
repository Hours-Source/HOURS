"""
Tests for the Thermal Sink EOH P0 bound (research/thermal.py, E29 / finding F2).

Covers the budget chain (E6–E8), the EOH-weighted thermodynamic floor (E27), the
provable ceiling bound (E29) and its degradation sentinels, and the §10.2
sensitivity artifact. Advisory-only: asserts no obligation/TEH is produced.

Arc coverage at ε ∈ {0.0, 0.40, 0.90, 0.99}.
"""

from __future__ import annotations

import pytest

from hours_eoh.research.thermal import (
    residual_thermal_forcing,
    planetary_budget,
    allocated_density,
    decarbonization_headroom,
    iota_floor,
    eoh_weighted_iota_floor,
    provable_ceiling_bound,
    ceiling_bound_sensitivity,
    IOTA_FLOOR_BY_DOMAIN,
)
from hours_eoh.data import A_EARTH_M2

ARC = [0.0, 0.40, 0.90, 0.99]
# Reference 1M-person collective (see the finding writeup).
A_COLL = 1.86e10
PHI_OTHER = 2.5e9


# ---------------------------------------------------------------------------
# budget chain
# ---------------------------------------------------------------------------

def test_residual_forcing_formula():
    # λ·ΔT_lo − F_GHG − F_alb = 3.2·3.0 − 3.0 − 0 = 6.6
    assert residual_thermal_forcing(delta_t_lo=3.0, lam=3.2, f_ghg=3.0, f_alb=0.0) == pytest.approx(6.6)


def test_residual_forcing_can_go_negative():
    # default λ=1.2, ΔT_lo=2.0, F_GHG=3.0 → 2.4 − 3.0 = −0.6 (budget exhausted by GHG)
    assert residual_thermal_forcing(delta_t_lo=2.0, lam=1.2, f_ghg=3.0) < 0.0


def test_planetary_budget_floored_at_zero():
    assert planetary_budget(delta_t_lo=2.0, lam=1.2, f_ghg=3.0) == 0.0
    assert planetary_budget(delta_t_lo=3.0, lam=2.0, f_ghg=3.0) > 0.0


def test_decarbonization_raises_budget_F3():
    # lowering F_GHG strictly raises the budget (restoration and liberation couple)
    hi_ghg = planetary_budget(delta_t_lo=3.0, lam=2.0, f_ghg=3.0)
    lo_ghg = planetary_budget(delta_t_lo=3.0, lam=2.0, f_ghg=1.0)
    assert lo_ghg > hi_ghg


def test_allocated_density_reserve_and_positivity():
    psi = allocated_density(A_EARTH_M2, r=0.20, delta_t_lo=3.0, lam=2.0, f_ghg=3.0)
    psi_no_reserve = allocated_density(A_EARTH_M2, r=0.0, delta_t_lo=3.0, lam=2.0, f_ghg=3.0)
    assert psi == pytest.approx(0.8 * psi_no_reserve)


def test_allocated_density_rejects_nonpositive_area():
    with pytest.raises(ValueError):
        allocated_density(0.0)


# ---------------------------------------------------------------------------
# F3 — decarbonization headroom (the reordered P0 headline)
# ---------------------------------------------------------------------------

def test_decarbonization_headroom_reproduces_measured():
    # net-ERF forcing 2.72 at ΔT_lo=3.0 K → ~1110 TW freed (Path C)
    h = decarbonization_headroom(delta_t_lo=3.0, f_ghg=2.72)
    assert h["gain_w"] / 1e12 == pytest.approx(1110, abs=5)
    assert h["binds_now"] is True


def test_decarbonization_headroom_sharp_form_no_budget_now():
    # at ΔT_lo=2.0 K the current budget is 0 (GHG has consumed it) yet the gain
    # is large — F3 in its sharpest form
    h = decarbonization_headroom(delta_t_lo=2.0, f_ghg=2.72)
    assert h["allocated_now_w"] == 0.0
    assert h["binds_now"] is False
    assert h["gain_w"] / 1e12 == pytest.approx(979, abs=5)


def test_decarbonization_gain_nonnegative():
    # cutting forcing never reduces the budget
    for dt in (1.5, 2.0, 3.0, 4.0):
        assert decarbonization_headroom(delta_t_lo=dt)["gain_w"] >= 0.0


# ---------------------------------------------------------------------------
# thermodynamic floor
# ---------------------------------------------------------------------------

def test_iota_floor_ordering_knowledge_lowest():
    # F6: knowledge (Landauer) is orders below the caloric/enthalpy floors
    assert iota_floor("knowledge") < iota_floor("ecological")
    assert iota_floor("ecological") < iota_floor("personal")


def test_iota_floor_unknown_domain():
    with pytest.raises(KeyError):
        iota_floor("nonexistent")


def test_eoh_weighted_floor_between_min_and_max():
    eoh = {"personal": 1e9, "infrastructure": 1e8, "ecological": 1e6, "knowledge": 1e5}
    w = eoh_weighted_iota_floor(eoh)
    assert min(IOTA_FLOOR_BY_DOMAIN.values()) <= w <= max(IOTA_FLOOR_BY_DOMAIN.values())


def test_eoh_weighted_floor_rejects_empty():
    with pytest.raises(ValueError):
        eoh_weighted_iota_floor({"personal": 0.0})


# ---------------------------------------------------------------------------
# the bound — E29
# ---------------------------------------------------------------------------

def test_bound_advisory_only_across_arc():
    # every arc point: advisory only, no obligation/TEH surface
    for eps in ARC:
        rep = provable_ceiling_bound(A_COLL, phi_other=PHI_OTHER, epsilon=eps)
        assert rep["advisory_only"] is True


def test_bound_unbudgeted_at_default_constants():
    # default λ=1.2, ΔT_lo=2.0 → ψ*=0 → UNBUDGETED (worst case, conclusive)
    rep = provable_ceiling_bound(A_COLL, phi_other=PHI_OTHER, epsilon=0.40)
    assert rep["verdict"] == "UNBUDGETED"
    assert rep["epsilon_max_bound"] is None
    assert rep["psi_star"] == 0.0


def test_bound_inconclusive_when_budgeted_floor_too_low():
    # open the budget (λ=3.2, ΔT_lo=3.0): floor bound is >> 1 → INCONCLUSIVE.
    # This is the honest P0 result: the thermodynamic floor does not bind ε.
    rep = provable_ceiling_bound(A_COLL, phi_other=PHI_OTHER, epsilon=0.40,
                                 lam=3.2, delta_t_lo=3.0)
    assert rep["verdict"] == "INCONCLUSIVE_ABOVE_1"
    assert rep["epsilon_max_bound"] is not None and rep["epsilon_max_bound"] > 1.0
    assert rep["conclusive"] is False


def test_bound_conclusive_when_headroom_negative():
    # if Φ_other already exceeds the collective allocation, bound floors at 0 < 1
    rep = provable_ceiling_bound(A_COLL, phi_other=1e18, epsilon=0.40,
                                 lam=3.2, delta_t_lo=3.0)
    assert rep["verdict"] == "CONCLUSIVE_BELOW_1"
    assert rep["epsilon_max_bound"] == 0.0
    assert rep["conclusive"] is True


def test_bound_rejects_nonpositive_area():
    with pytest.raises(ValueError):
        provable_ceiling_bound(0.0)


def test_bound_larger_iota_gives_tighter_bound():
    # monotonicity: a heavier EOH mix (more personal) lowers the bound
    light = provable_ceiling_bound(A_COLL, phi_other=PHI_OTHER, lam=3.2, delta_t_lo=3.0,
                                   eoh_by_domain={"knowledge": 1e9, "personal": 1.0,
                                                  "infrastructure": 1.0, "ecological": 1.0})
    heavy = provable_ceiling_bound(A_COLL, phi_other=PHI_OTHER, lam=3.2, delta_t_lo=3.0,
                                   eoh_by_domain={"knowledge": 1.0, "personal": 1e9,
                                                  "infrastructure": 1.0, "ecological": 1.0})
    assert heavy["epsilon_max_bound"] < light["epsilon_max_bound"]


# ---------------------------------------------------------------------------
# sensitivity — §10.2
# ---------------------------------------------------------------------------

def test_sensitivity_reports_both_regimes():
    rep = ceiling_bound_sensitivity(A_COLL, phi_other=PHI_OTHER)
    # default grid spans unbudgeted corners and budgeted-but-inconclusive corners
    assert rep["any_unbudgeted"] is True
    # honest P0 finding: when budgeted, the floor bound never binds below 1
    assert rep["all_inconclusive_when_budgeted"] is True
    assert rep["any_conclusive_below_1"] is False


def test_sensitivity_cells_cover_grid():
    rep = ceiling_bound_sensitivity(A_COLL, phi_other=PHI_OTHER,
                                    lam_values=(1.2, 3.2), delta_t_lo_values=(2.0, 3.0))
    assert len(rep["cells"]) == 4
