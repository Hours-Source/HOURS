"""
Tests for the drawdown chain (research/thermal_drawdown.py).

Pins each link of ΔF → Δppm → GtCO₂ → joules → EOH separately, so a failure
localizes to one step rather than to "the converter". Also pins the two results
that matter for the gate: the job is essentially ε-invariant, and the programme's
own dissipation is nowhere near self-defeating.
"""

from __future__ import annotations

import math

import pytest

from hours_eoh.data import (
    CDR_ENERGY_GJ_PER_TONNE,
    CDR_GROSS_REMOVAL_FACTOR,
    CDR_LABOR_HOURS_PER_TONNE,
    CO2_CONCENTRATION_PPM,
    CO2_FORCING_COEFFICIENT,
    CO2_PPM_TO_GT,
)
from hours_eoh.research.thermal_drawdown import (
    DRAWDOWN_TIERS,
    drawdown_job,
    drawdown_power,
    forcing_to_ppm_reduction,
    iota_drawdown,
    ppm_to_gross_mass_gt,
)
from hours_eoh.research.thermal_overage import phi_at_epsilon, thermal_overage


# ---------------------------------------------------------------------------
# ι is derived from two plant observables, not assumed
# ---------------------------------------------------------------------------

def test_iota_is_energy_over_labor():
    assert iota_drawdown(4.0, 0.6) == pytest.approx(4.0e9 / 0.6)
    assert iota_drawdown() == pytest.approx(6.67e9, rel=0.01)


def test_iota_is_orders_above_the_infrastructure_floor():
    """Expected direction: drawdown is energy-intensive and labor-thin."""
    from hours_eoh.data import THERMAL_IOTA_FLOOR_INFRASTRUCTURE
    assert iota_drawdown() / THERMAL_IOTA_FLOOR_INFRASTRUCTURE > 1e3


def test_iota_rejects_zero_labor():
    """An infinitely automated drawdown generates no obligation — a claim the
    caller must make explicitly, not reach by dividing by zero."""
    with pytest.raises(ValueError):
        iota_drawdown(4.0, 0.0)


# ---------------------------------------------------------------------------
# ΔF → Δppm
# ---------------------------------------------------------------------------

def test_forcing_to_ppm_reproduces():
    assert forcing_to_ppm_reduction(1.0) == pytest.approx(69.1, abs=0.3)


def test_forcing_to_ppm_inverts_the_forcing_law():
    """Round-trip: applying the log law to the target concentration must return
    the forcing reduction asked for."""
    drop = forcing_to_ppm_reduction(1.0)
    target = CO2_CONCENTRATION_PPM - drop
    recovered = CO2_FORCING_COEFFICIENT * math.log(CO2_CONCENTRATION_PPM / target)
    assert recovered == pytest.approx(1.0, abs=1e-9)


def test_calibrated_coefficient_beats_myhre_by_the_stated_margin():
    """Myhre's 5.35 runs low over the drawdown corridor, so it overstates the
    ppm a given cut requires."""
    calibrated = forcing_to_ppm_reduction(1.0)
    myhre = forcing_to_ppm_reduction(1.0, coefficient=5.35)
    assert myhre > calibrated
    assert myhre / calibrated == pytest.approx(1.05, abs=0.01)


def test_removal_gets_more_forcing_effective_as_it_proceeds():
    """The forcing law is logarithmic in concentration, so a given ppm removed
    at lower concentration buys MORE forcing reduction: the second 0.5 W·m⁻²
    costs fewer ppm than the first (33.0 vs 36.1).

    Note the practical effect runs the opposite way — capture from more dilute
    air costs more energy per tonne — and this chain holds GJ/t constant, so it
    flatters deep cuts. The two are not netted; see CDR_ENERGY_GJ_PER_TONNE."""
    first = forcing_to_ppm_reduction(0.5)
    both = forcing_to_ppm_reduction(1.0)
    second_increment = both - first
    assert second_increment < first
    assert second_increment == pytest.approx(33.0, abs=0.3)


def test_forcing_to_ppm_rejects_bad_inputs():
    with pytest.raises(ValueError):
        forcing_to_ppm_reduction(1.0, coefficient=0.0)
    with pytest.raises(ValueError):
        forcing_to_ppm_reduction(1.0, concentration_ppm=0.0)


# ---------------------------------------------------------------------------
# Δppm → mass
# ---------------------------------------------------------------------------

def test_mass_conversion_and_sink_reversal():
    net, gross = ppm_to_gross_mass_gt(69.1)
    assert net == pytest.approx(69.1 * CO2_PPM_TO_GT)
    assert gross == pytest.approx(net * CDR_GROSS_REMOVAL_FACTOR)
    assert gross > net


def test_omitting_sink_reversal_understates_the_obligation():
    """The link whose omission flatters the result — asserted so it cannot be
    quietly dropped."""
    _, honest = ppm_to_gross_mass_gt(69.1)
    _, naive = ppm_to_gross_mass_gt(69.1, gross_factor=1.0)
    assert honest / naive == pytest.approx(CDR_GROSS_REMOVAL_FACTOR)
    assert honest > naive


# ---------------------------------------------------------------------------
# the whole chain
# ---------------------------------------------------------------------------

def test_chain_is_internally_consistent():
    c = drawdown_job(2.0)
    assert c["energy_j"] == pytest.approx(
        c["gross_mass_gt"] * 1e9 * CDR_ENERGY_GJ_PER_TONNE * 1e9)
    assert c["eoh_global"] == pytest.approx(c["energy_j"] / c["iota_drawdown"])
    assert c["concentration_target"] == pytest.approx(
        CO2_CONCENTRATION_PPM - c["ppm_reduction"])


def test_chain_reproduces_the_2k_job():
    c = drawdown_job(2.0)
    assert c["forcing_reduction"] == pytest.approx(1.0, abs=0.01)
    assert c["gross_mass_gt"] == pytest.approx(973, rel=0.02)
    assert c["eoh_global"] == pytest.approx(5.84e11, rel=0.02)
    assert c["feasible"] is True


def test_energy_is_a_plausible_multiple_of_world_supply():
    """Sanity anchor: the 2 K job is a few years of TOTAL world primary energy —
    order-of-magnitude agreement with published CDR scale-up estimates."""
    world_annual_j = 636e18          # OWID 2024 world primary energy, J/yr
    years = drawdown_job(2.0)["energy_j"] / world_annual_j
    assert 3.0 < years < 12.0


def test_share_scales_linearly_and_is_bounded():
    whole = drawdown_job(2.0)["eoh_global"]
    part = drawdown_job(2.0, population_share=0.25)["eoh_share"]
    assert part == pytest.approx(whole * 0.25)
    with pytest.raises(ValueError):
        drawdown_job(2.0, population_share=1.5)
    with pytest.raises(ValueError):
        drawdown_job(2.0, population_share=-0.1)


def test_slack_threshold_needs_no_drawdown():
    """Above the break-even there is no overage, so no job."""
    c = drawdown_job(3.0)
    assert c["forcing_reduction"] == 0.0
    assert c["eoh_global"] == 0.0


def test_harder_thresholds_cost_more():
    jobs = [drawdown_job(dt)["eoh_global"] for dt in (1.5, 2.0, 2.5)]
    assert all(a > b for a, b in zip(jobs, jobs[1:]))


def test_provenance_ships_with_every_chain():
    c = drawdown_job(2.0)
    assert c["tiers"] == DRAWDOWN_TIERS
    assert "D — placeholder" in c["tiers"]["gross_removal_factor"]
    assert c["tiers"]["iota_drawdown"].startswith("derived")


# ---------------------------------------------------------------------------
# ε-coherence — and the finding that the job barely moves
# ---------------------------------------------------------------------------

def test_job_is_nearly_epsilon_invariant():
    """The drawdown obligation is owed regardless of how far automation has run:
    across the WHOLE arc the job moves under 10%, because Φ is ~1% of the forcing
    reduction. Automation did not create this debt and cannot discharge it."""
    at_zero = drawdown_job(2.0, phi_w=phi_at_epsilon(0.0))["eoh_global"]
    at_full = drawdown_job(2.0, phi_w=phi_at_epsilon(0.99))["eoh_global"]
    assert at_full > at_zero
    assert at_full / at_zero < 1.10


def test_arc_meaningful_at_all_key_epsilons():
    for eps in (0.0, 0.40, 0.90, 0.99):
        c = drawdown_job(2.0, phi_w=phi_at_epsilon(eps))
        assert c["eoh_global"] > 0.0
        assert math.isfinite(c["eoh_global"])


# ---------------------------------------------------------------------------
# does the programme fight itself?
# ---------------------------------------------------------------------------

def test_programme_does_not_self_defeat():
    """Even at κ = 1 — every drawdown watt fully additive — the programme's own
    dissipation is ~0.2% of the overage it clears. The self-defeat concern does
    NOT bind at global scale."""
    p = drawdown_power(drawdown_job(2.0), 100.0)
    assert p["self_defeating_at_kappa_1"] is False
    assert p["ratio_to_overage"] < 0.01


def test_faster_programmes_are_thermally_worse():
    """F9 falling out of the arithmetic: the same job compressed dissipates
    proportionally harder."""
    job = drawdown_job(2.0)
    fast = drawdown_power(job, 25.0)["phi_programme_w"]
    slow = drawdown_power(job, 100.0)["phi_programme_w"]
    assert fast == pytest.approx(slow * 4.0)


def test_drawdown_power_rejects_nonpositive_horizon():
    with pytest.raises(ValueError):
        drawdown_power(drawdown_job(2.0), 0.0)


# ---------------------------------------------------------------------------
# responsibility allocation — the shipped 1750-2024 table
# ---------------------------------------------------------------------------

from hours_eoh.data import CDR_RESPONSIBILITY_BASIS
from hours_eoh.research.thermal_drawdown import (
    allocation_share,
    load_cumulative_emissions,
    responsibility_share,
)


def test_table_covers_the_full_industrial_record():
    """Truncation is the failure mode this table exists to prevent."""
    d = load_cumulative_emissions()
    assert "1750-2024" in d["_tier"]
    assert len(d["collectives"]) > 150
    assert d["world_cumulative_co2_gt"] == pytest.approx(1849, rel=0.01)
    assert d["world_cumulative_co2_incl_luc_gt"] == pytest.approx(2752, rel=0.01)


def test_shares_do_not_sum_to_one_and_the_gap_is_named():
    """2.49% of cumulative fossil CO2 is international shipping and aviation,
    which belong to no territory — so under a responsibility rule nobody owes the
    drawdown for it. Asserted rather than tolerated, because a future refresh
    that quietly closes or widens this gap should fail loudly."""
    d = load_cumulative_emissions()
    c = d["collectives"]
    fossil = sum(r["share_fossil"] for r in c.values() if r["share_fossil"] is not None)
    luc = sum(r["share_incl_luc"] for r in c.values() if r["share_incl_luc"] is not None)
    assert fossil == pytest.approx(0.975, abs=0.005)
    assert luc == pytest.approx(0.998, abs=0.005)
    assert d["_unattributed"]["share_fossil_unattributed"] == pytest.approx(1 - fossil, abs=0.002)
    assert "SIGN-OFF" in " ".join(d["_unattributed"])


def test_land_use_basis_materially_reallocates():
    """Including land-use change is not a rounding adjustment — it roughly
    quintuples Brazil's share and cuts the UK's by a third. Which basis is right
    is an equity question, not a technical one."""
    assert responsibility_share("Brazil", "incl_luc") > 4 * responsibility_share("Brazil", "fossil")
    assert responsibility_share("United Kingdom", "incl_luc") < responsibility_share("United Kingdom", "fossil")


def test_default_basis_is_the_whole_atmospheric_burden():
    assert CDR_RESPONSIBILITY_BASIS == "incl_luc"
    assert responsibility_share("Brazil") == responsibility_share("Brazil", "incl_luc")


def test_unknown_collective_returns_none_not_zero():
    """A zero share would silently excuse a collective from its obligation."""
    assert responsibility_share("Atlantis") is None


def test_rejects_unknown_basis():
    with pytest.raises(ValueError):
        responsibility_share("Brazil", "vibes")


def test_named_collective_resolves_without_carrying_figures():
    a = allocation_share(1e6, 8.16e9, collective="United States")
    assert a["basis_used"] == "responsibility"
    assert a["responsibility_basis"] == "incl_luc"
    assert a["caveat"] is None
    assert a["share"] == pytest.approx(0.2037, rel=0.01)


def test_explicit_figures_override_the_table():
    a = allocation_share(1e6, 8.16e9, cumulative_emissions_t=1.0,
                         world_cumulative_emissions_t=4.0, collective="United States")
    assert a["share"] == pytest.approx(0.25)


def test_unknown_name_falls_back_and_declares_it():
    a = allocation_share(1e6, 8.16e9, collective="Atlantis")
    assert a["basis_used"] == "population"
    assert "under-charges" in a["caveat"]


def test_responsibility_departs_sharply_from_headcount():
    """The rule's whole point: the US owes ~5x its headcount share and
    Bangladesh ~0.06x, a spread of roughly 80x per person."""
    us = responsibility_share("United States")
    bd = responsibility_share("Bangladesh")
    tbl = load_cumulative_emissions()["collectives"]
    us_pc = us / tbl["United States"]["share_population"]
    bd_pc = bd / tbl["Bangladesh"]["share_population"]
    assert us_pc > 4.0
    assert bd_pc < 0.1
    assert us_pc / bd_pc > 50.0
