"""
Tests for the shipped η table and its loader (reference/data/eta_land.json).

η is an allocation weight, so the properties that matter are conservation (it
redistributes a fixed budget rather than changing it), correct normalisation
footing, and that estimates and failures stay distinguishable from measurements.
"""

from __future__ import annotations

import pytest

from hours_eoh.data import ETA_BASIS
from hours_eoh.research.thermal_path_c import eta_for, load_eta_land


def _resolved(d):
    return {k: v for k, v in d["collectives"].items() if v["eta_clear_sky"] is not None}


# ---------------------------------------------------------------------------
# conservation and normalisation
# ---------------------------------------------------------------------------

def test_eta_is_normalised_to_claimed_land():
    """Mean 1 on the SAME footing as A_LAND_CLAIMED_M2 — the psi* denominator.
    Normalising over all land instead would inflate every collective by ~3%,
    because Antarctica is 8.35% of cos-weighted land at eta ~0.67, and would
    silently change the total allocated."""
    d = load_eta_land()
    res = _resolved(d)
    total_w = sum(v["land_weight"] for v in res.values())
    weighted = sum(v["eta_clear_sky"] * v["land_weight"] for v in res.values())
    assert weighted / total_w == pytest.approx(1.0, abs=0.05)
    assert "Antarctica EXCLUDED" in d["_normalisation"]["basis"]


def test_eta_redistributes_rather_than_creating_budget():
    """sum(eta_i * a_i) == sum(a_i) is what makes eta a redistribution."""
    res = _resolved(load_eta_land())
    a = sum(v["land_weight"] for v in res.values())
    ea = sum(v["eta_clear_sky"] * v["land_weight"] for v in res.values())
    assert ea == pytest.approx(a, rel=0.05)


def test_eta_spread_is_physically_ordered():
    """Warm arid columns shed more; cold ones less. If this inverts, the sign
    convention on ECMWF net radiation has been dropped somewhere."""
    assert eta_for("United Arab Emirates") > eta_for("Germany") > eta_for("Russia")
    assert 0.5 < eta_for("Russia") < eta_for("United Arab Emirates") < 1.5


# ---------------------------------------------------------------------------
# estimates and failures stay visible
# ---------------------------------------------------------------------------

def test_unresolved_collectives_are_null_not_invented():
    """Three mid-Pacific atolls have no land fraction within 5 degrees. A
    fabricated eta for a nation that may not survive the arc is not a rounding
    convenience."""
    d = load_eta_land()
    unresolved = [k for k, v in d["collectives"].items() if v["method"] == "unresolved"]
    assert set(unresolved) == {"Kiribati", "Marshall Islands", "Clipperton Island"}
    for k in unresolved:
        assert d["collectives"][k]["eta_clear_sky"] is None
        assert eta_for(k) is None


def test_unknown_collective_returns_none():
    assert eta_for("Atlantis") is None


def test_inherited_values_carry_their_radius():
    """An estimate must never be mistakable for a measurement."""
    d = load_eta_land()
    inh = [v for v in d["collectives"].values() if v["method"] == "neighbourhood"]
    assert len(inh) == 48
    assert all(v["radius_deg"] is not None for v in inh)
    assert all(v["radius_deg"] <= 5.0 for v in inh)
    direct = [v for v in d["collectives"].values() if v["method"] == "direct"]
    assert all(v["radius_deg"] is None for v in direct)


def test_singapore_is_inherited_not_measured():
    """The framework's headline Contact collective is sub-grid at 0.25 deg — its
    eta is a neighbourhood estimate and must be labelled as one."""
    v = load_eta_land()["collectives"]["Singapore"]
    assert v["method"] == "neighbourhood"
    assert v["eta_clear_sky"] is not None


# ---------------------------------------------------------------------------
# the basis choice
# ---------------------------------------------------------------------------

def test_default_basis_is_clear_sky():
    assert ETA_BASIS == "clear_sky"
    assert eta_for("Brazil") == eta_for("Brazil", "clear_sky")


def test_all_sky_is_retained_as_the_reality_check():
    d = load_eta_land()
    assert all(v["eta_all_sky"] is not None for v in _resolved(d).values())
    assert eta_for("Brazil", "all_sky") != eta_for("Brazil", "clear_sky")


def test_basis_gap_is_largest_where_cloud_is_persistent():
    """The gap is the diagnostic for where the basis choice does real work:
    convective collectives gain under clear-sky, arid ones lose."""
    d = load_eta_land()["collectives"]
    assert d["Singapore"]["gap"] > 0.10          # equatorial convection
    assert d["Brazil"]["gap"] > 0.04
    assert d["United Arab Emirates"]["gap"] < -0.05   # clear skies flatter all-sky
    assert abs(d["Germany"]["gap"]) < 0.02


def test_rejects_unknown_basis():
    with pytest.raises(ValueError):
        eta_for("Brazil", "vibes")


# ---------------------------------------------------------------------------
# provenance travels with the numbers
# ---------------------------------------------------------------------------

def test_limitations_ship_with_the_data():
    d = load_eta_land()
    lim = d["_limitations"]
    assert "seasonal" in lim and "conceptual" in lim
    assert d["world"]["balanced_days"] == 107
    assert "0.5 deg ensemble" in d["_method"]["field"]      # the overwrite trap
    assert 15.0 < d["world"]["longwave_cloud_radiative_effect_w_m2"] < 30.0


# ---------------------------------------------------------------------------
# η wired into F11
# ---------------------------------------------------------------------------

def test_eta_redistributes_utilization_without_rescuing_anyone():
    """η moves U by tens of percent, not orders of magnitude — no collective
    crosses the Contact boundary on η alone."""
    from hours_eoh.research.thermal_path_c import collective_utilization
    sg = collective_utilization("Singapore", 1.4, 7.3e8, 0.98, delta_t_lo=3.0,
                                eta_name="Singapore")
    raw = collective_utilization("Singapore", 1.4, 7.3e8, 0.98, delta_t_lo=3.0, eta=1.0)
    assert sg["eta"] == pytest.approx(1.0635, rel=0.01)
    assert sg["utilization"] < raw["utilization"]        # efficient shedder gains
    assert sg["in_contact"] and raw["in_contact"]        # but stays in Contact


def test_unresolved_eta_falls_back_to_unity_and_says_so():
    """A null η must not silently become zero (infinite ψ) or vanish."""
    from hours_eoh.research.thermal_path_c import collective_utilization
    c = collective_utilization("Kiribati", 0.01, 8.1e8, 0.9, eta_name="Kiribati")
    assert c["eta"] is None
    assert c["eta_applied"] == 1.0


def test_dissipation_density_rejects_nonpositive_eta():
    from hours_eoh.research.thermal_path_c import collective_dissipation_density
    with pytest.raises(ValueError):
        collective_dissipation_density(1.0, 1e10, 0.9, eta=0.0)


def test_marginal_capacity_negative_result_is_recorded():
    """The conceptual objection is unresolved, and the next attempt should start
    from the negative result rather than repeating it."""
    d = load_eta_land()["_marginal_capacity_investigated"]
    assert d["result"].startswith("NEGATIVE")
    assert set(d["estimators"]) and "resolves_by" in d
    assert "DATA requirement" in d["resolves_by"]
