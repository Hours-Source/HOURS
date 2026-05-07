"""
scenarios/recovery — Recovery trajectory analysis after a shock or crisis.

Given a deferred EOH backlog, models how long it takes to recover under
different fulfillment strategies. Answers the question: "how fast does the
system recover from a shock, and what fulfillment rate is required?"

Recovery is defined as the backlog dropping to ≤ annual_eoh (one year of
demand — the manageable steady-state level). Any fulfillment_fraction > 1.0
directs surplus capacity to backlog paydown.

Mission Statement: §"EOH compounding — threshold spike becomes unrecoverable
if deferred too long"; §"Regenerative offset reduces compounded backlog."
"""

from __future__ import annotations

from hours_eoh.core.eoh_dynamics import eoh_compounding


def maintenance_recovery_schedule(
    epsilon: float,
    current_deferred: float,
    annual_eoh: float,
    fulfillment_fraction: float = 1.5,
    asset_type: str = "generic_infra",
    max_years: int = 50,
) -> dict:
    """
    Estimate how many years to recover from a deferred maintenance backlog.

    Each year, `fulfillment_fraction × annual_eoh` is paid toward obligations.
    The first `annual_eoh` covers current demand; any surplus reduces the backlog.
    Recovery is declared when the backlog drops to ≤ annual_eoh (one year's demand).

    A fulfillment_fraction of exactly 1.0 covers only current demand — the backlog
    never shrinks. Fractional values > 1.0 are required for active recovery.

    Args:
        epsilon: Automation level (affects compounding softener).
        current_deferred: Current accumulated deferred EOH backlog.
        annual_eoh: Annual EOH demand for the asset.
        fulfillment_fraction: Total capacity as a fraction of annual_eoh.
                              Must be > 1.0 for any backlog reduction.
                              Default: 1.5 (50% extra capacity toward backlog).
        asset_type: Asset type controlling compounding profile.
        max_years: Maximum years to simulate before declaring unrecoverable.

    Returns:
        dict: {
          "epsilon":              float,
          "current_deferred":     float,
          "annual_eoh":           float,
          "fulfillment_fraction": float,
          "recovery_year":        int | None,   (year backlog ≤ annual_eoh, or None)
          "recoverable":          bool,
          "trajectory":           list[dict],
          "final_deferred":       float,
          "recommendation":       str,
        }
    """
    deferred      = current_deferred
    trajectory    = []
    recovery_year = None
    annual_surplus = annual_eoh * max(0.0, fulfillment_fraction - 1.0)

    for year in range(1, max_years + 1):
        if deferred > 0:
            compounding       = eoh_compounding(deferred, asset_type, float(year), epsilon)
            compounding_ratio = compounding / max(deferred, 1.0)
        else:
            compounding       = 0.0
            compounding_ratio = 0.0

        # Reduce backlog by surplus capacity (anything above annual demand)
        deferred = max(0.0, deferred - annual_surplus)

        trajectory.append({
            "year":              year,
            "deferred":          deferred,
            "compounding":       compounding,
            "compounding_ratio": compounding_ratio,
        })

        # Recovered when backlog ≤ one year of demand (manageable steady state)
        if deferred <= annual_eoh and recovery_year is None:
            recovery_year = year
            break

    final_deferred = trajectory[-1]["deferred"]
    recoverable    = recovery_year is not None

    if recoverable:
        rec = (
            f"Backlog of {current_deferred:,.0f} EOH recoverable in {recovery_year} year(s) "
            f"at {fulfillment_fraction:.0%} fulfillment "
            f"({annual_surplus:,.0f} EOH/yr directed to backlog paydown)."
        )
    else:
        rec = (
            f"Backlog of {current_deferred:,.0f} EOH NOT recoverable within {max_years} years "
            f"at {fulfillment_fraction:.0%} fulfillment ({annual_surplus:,.0f} EOH/yr surplus). "
            f"Remaining after {max_years} years: {final_deferred:,.0f} EOH. "
            f"Increase fulfillment rate or accept asset rebuilding."
        )

    return {
        "epsilon":              epsilon,
        "current_deferred":     current_deferred,
        "annual_eoh":           annual_eoh,
        "fulfillment_fraction": fulfillment_fraction,
        "recovery_year":        recovery_year,
        "recoverable":          recoverable,
        "trajectory":           trajectory,
        "final_deferred":       final_deferred,
        "recommendation":       rec,
    }


def minimum_fulfillment_for_recovery(
    epsilon: float,
    current_deferred: float,
    annual_eoh: float,
    asset_type: str = "generic_infra",
    max_years: int = 50,
    resolution: float = 0.05,
) -> dict:
    """
    Find the minimum fulfillment fraction that allows recovery within max_years.

    Sweeps fulfillment_fraction from 1.0 upward in steps of resolution,
    calling maintenance_recovery_schedule() at each level until recovery is found.

    Args:
        epsilon: Automation level.
        current_deferred: Current accumulated deferred EOH backlog.
        annual_eoh: Annual EOH demand.
        asset_type: Asset type.
        max_years: Maximum years allowed for recovery.
        resolution: Step size for sweeping fulfillment_fraction. Default: 0.05.

    Returns:
        dict: {
          "min_fulfillment":  float | None,   (minimum fraction to recover, or None)
          "recovery_year":    int | None,
          "sweep":            list[dict],      (results at each tested fraction)
        }
    """
    sweep = []
    for i in range(1, 41):
        frac = 1.0 + i * resolution
        result = maintenance_recovery_schedule(
            epsilon=epsilon,
            current_deferred=current_deferred,
            annual_eoh=annual_eoh,
            fulfillment_fraction=frac,
            asset_type=asset_type,
            max_years=max_years,
        )
        sweep.append({"fulfillment_fraction": frac, **result})
        if result["recoverable"]:
            return {
                "min_fulfillment": frac,
                "recovery_year":   result["recovery_year"],
                "sweep":           sweep,
            }

    return {"min_fulfillment": None, "recovery_year": None, "sweep": sweep}
