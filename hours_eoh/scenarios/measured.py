"""
Measured-multiplier bridge — feeds the real O*NET/BLS registry into the
simulation and dashboard as the employment-weighted replacement for the
synthetic DEFAULT_SEGMENTS.

The registry (`reference.onet_multipliers`) is a frozen ε=0.40 cross-section.
This module reprices it to any ε via `epoch_factor_weights(ε)` — so a simulation
sweeping the automation arc can draw a MEASURED, ε-coherent mean multiplier each
period instead of a hand-set constant. At ε=0.40 the repriced mean equals the
frozen registry mean (≈ 1.9964) by construction.

Layer: scenarios/ imports core/ and reference/ — never the reverse. The measured
data is injected HERE, at the boundary; core/ stays pure (it never imports
reference/). This is the deliberate design: DEFAULT_SEGMENTS remains the core
default, and callers opt into measured data through this bridge.

ε-coherence: `measured_mean_multiplier(ε)` and `measured_segments(ε)` are valid
across ε ∈ [0, 0.99]; the mean stays within the Condition II band on the arc.
"""

from __future__ import annotations

from typing import Any

from hours_eoh.core.multipliers import (
    epoch_factor_weights,
    population_weighted_mean_multiplier,
)
from hours_eoh.core.simulation import run_simulation
from hours_eoh.reference.onet_multipliers import registry_segments
from hours_eoh.scenarios.multiplier_sensitivity import reconstruct


def measured_segments(epsilon: float | None = None) -> list[dict]:
    """
    The measured registry projected onto the `segments` shape consumed by
    `population_weighted_mean_multiplier` and `system_dashboard`.

    Args:
        epsilon: if None, use the frozen reference multipliers (ε=0.40 epoch).
            If given, reprice all 751 occupations under `epoch_factor_weights(ε)`
            before forming segments — the measured, arc-adapted workforce.

    Returns:
        list of {"name": occ6, "fraction": employment share, "mean_mu": multiplier};
        fractions sum to 1.0.
    """
    if epsilon is None:
        return registry_segments()
    run = reconstruct(factor_weights=epoch_factor_weights(epsilon))
    total_emp = sum(run["employment_k"])
    if total_emp <= 0.0:
        raise ValueError("registry has non-positive total employment")
    return [
        {"name": occ, "fraction": emp / total_emp, "mean_mu": m}
        for occ, m, emp in zip(run["occ6"], run["multiplier"], run["employment_k"])
    ]


def measured_mean_multiplier(epsilon: float | None = None) -> float:
    """
    Employment-weighted mean multiplier from the measured registry.

    The measured replacement for the synthetic DEFAULT_SEGMENTS mean (2.10). At
    epsilon=None or 0.40 this is ≈ 1.9964 (the frozen registry mean over 751
    occupations); repricing along the arc keeps it inside the Condition II band.

    Args:
        epsilon: automation level to reprice to; None uses the frozen epoch.

    Returns:
        Employment-weighted mean reference multiplier.
    """
    if epsilon is None:
        return population_weighted_mean_multiplier(registry_segments())
    return reconstruct(factor_weights=epoch_factor_weights(epsilon))["weighted_mean"]


def measured_mean_multiplier_schedule(epsilons: list[float]) -> list[float]:
    """Per-period measured mean multiplier along an ε path — ready to pass as
    `run_simulation(..., mean_multiplier_schedule=...)`."""
    return [measured_mean_multiplier(e) for e in epsilons]


def run_measured_simulation(
    initial_state: dict,
    epsilons: list[float] | None = None,
    n_periods: int = 20,
    **simulate_kwargs: Any,
) -> dict:
    """
    Run `core.simulation.run_simulation` with the mean multiplier sourced from the
    measured O*NET/BLS registry instead of the hand-set default (2.10).

    Args:
        initial_state: starting state from `make_economy_state()`.
        epsilons: optional per-period ε path. When given, each period's mean
            multiplier is the registry repriced to that ε (a measured,
            ε-coherent schedule). When None, a single measured mean (frozen
            epoch) seeds every period.
        n_periods: number of periods.
        **simulate_kwargs: forwarded to `run_simulation` / `simulate_period`.

    Returns:
        The `run_simulation` result dict (see its docstring). The
        `summary.mean_multiplier_trajectory` will carry the measured values.
    """
    if epsilons is not None:
        schedule = measured_mean_multiplier_schedule(epsilons)
        return run_simulation(
            initial_state,
            n_periods=n_periods,
            mean_multiplier_schedule=schedule,
            **simulate_kwargs,
        )
    simulate_kwargs.setdefault("mean_multiplier", measured_mean_multiplier())
    return run_simulation(initial_state, n_periods=n_periods, **simulate_kwargs)
