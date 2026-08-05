"""
Tests for capital as dual-output (research/thermal_capital.py, §12.2).

The same capital inventory yields both ε (machine_eoh_from_capital) and Φ
(machine_dissipation_from_capital). Covers the derivation, the aggregate sanity
anchor vs Path C, and the bottom-up capital thermal ceiling flowing into the corridor.
"""

from __future__ import annotations

import pytest

from hours_eoh.core.civilization import machine_eoh_from_capital
from hours_eoh.data import CAPITAL_MACHINE_PROFILES
from hours_eoh.research.thermal_capital import (
    machine_dissipation_from_capital,
    collective_thermal_from_capital,
    capital_thermal_ceiling,
)
from hours_eoh.research.corridor import corridor

ALL_STANDARD = {t: "standard" for t in CAPITAL_MACHINE_PROFILES}
POP = 1_000_000.0


# ---------------------------------------------------------------------------
# capital → Φ derivation
# ---------------------------------------------------------------------------

def test_dual_output_same_inventory():
    # one inventory produces both EOH and Φ
    eoh = machine_eoh_from_capital(ALL_STANDARD, POP)
    diss = machine_dissipation_from_capital(ALL_STANDARD, POP)
    assert eoh["machine_eoh_total"] > 0.0
    assert diss["phi_total_w"] > 0.0
    # Φ = operational + embodied
    assert diss["phi_total_w"] == pytest.approx(
        diss["phi_operational_w"] + diss["phi_embodied_w"]
    )


def test_operational_dominates_embodied():
    diss = machine_dissipation_from_capital(ALL_STANDARD, POP)
    assert diss["phi_operational_w"] > diss["phi_embodied_w"]


def test_grid_kappa_scales_linearly():
    full = machine_dissipation_from_capital(ALL_STANDARD, POP, grid_kappa=1.0)
    half = machine_dissipation_from_capital(ALL_STANDARD, POP, grid_kappa=0.5)
    assert half["phi_total_w"] == pytest.approx(0.5 * full["phi_total_w"])


def test_grid_kappa_zero_is_thermally_neutral():
    # a fully flux-redirecting grid adds no net heat
    diss = machine_dissipation_from_capital(ALL_STANDARD, POP, grid_kappa=0.0)
    assert diss["phi_total_w"] == 0.0


def test_grid_kappa_out_of_range_rejected():
    with pytest.raises(ValueError):
        machine_dissipation_from_capital(ALL_STANDARD, POP, grid_kappa=1.5)


def test_more_capital_more_dissipation():
    minimal = machine_dissipation_from_capital({t: "minimal" for t in CAPITAL_MACHINE_PROFILES}, POP)
    advanced = machine_dissipation_from_capital({t: "advanced" for t in CAPITAL_MACHINE_PROFILES}, POP)
    assert advanced["phi_total_w"] > minimal["phi_total_w"]


def test_aggregate_order_consistent_with_path_c():
    # honest sanity anchor: Φ/capita within a factor of ~3 of Path C's measured
    # ~2200 W·person⁻¹ net-additive (NOT fitted — placeholder scale)
    diss = machine_dissipation_from_capital(ALL_STANDARD, POP)
    per_cap = diss["phi_total_w"] / POP
    assert 700.0 < per_cap < 7000.0


def test_heavy_types_dominate():
    diss = machine_dissipation_from_capital(ALL_STANDARD, POP)
    ranked = sorted(diss["by_type"].items(), key=lambda kv: -kv[1]["total_w"])
    top = {name for name, _ in ranked[:4]}
    # compute/industry/power are the physically expected heavy dissipators
    assert "computing_ai" in top
    assert "industrial_automation" in top


# ---------------------------------------------------------------------------
# collective utilization from capital
# ---------------------------------------------------------------------------

def test_dense_collective_in_contact():
    st = collective_thermal_from_capital(ALL_STANDARD, POP, land_m2=7.3e8, delta_t_lo=3.0)
    assert st["in_contact"] is True
    assert st["utilization"] >= 1.0


def test_large_collective_below_floor():
    st = collective_thermal_from_capital(ALL_STANDARD, POP, land_m2=9.15e12, delta_t_lo=3.0)
    assert st["regime"] == "below_floor"


def test_collective_rejects_zero_land():
    with pytest.raises(ValueError):
        collective_thermal_from_capital(ALL_STANDARD, POP, land_m2=0.0)


def test_phi_per_capita_reported():
    st = collective_thermal_from_capital(ALL_STANDARD, POP, land_m2=1e11)
    assert st["phi_per_capita_w"] > 0.0


# ---------------------------------------------------------------------------
# corridor integration (bottom-up thermal ceiling)
# ---------------------------------------------------------------------------

def test_capital_thermal_ceiling_binds_when_dense():
    c = capital_thermal_ceiling(ALL_STANDARD, POP, land_m2=7.3e8, epsilon_current=0.40)
    assert c["binding"] is True
    assert c["epsilon_ceiling"] == pytest.approx(0.40)


def test_capital_thermal_ceiling_closes_corridor():
    c = capital_thermal_ceiling(ALL_STANDARD, POP, land_m2=7.3e8, epsilon_current=0.40)
    rep = corridor(0.52, [c])  # survival floor above the thermal ceiling
    assert rep["feasible"] is False
    assert rep["binding_ceiling"] == "thermal_measured"


def test_capital_thermal_ceiling_open_when_large():
    c = capital_thermal_ceiling(ALL_STANDARD, POP, land_m2=9.15e12, epsilon_current=0.40)
    rep = corridor(0.40, [c])
    assert rep["feasible"] is True
    assert rep["success"] is True
