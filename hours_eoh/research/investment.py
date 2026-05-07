"""
research/investment — Investment ranking and allocation tools (research-only).

Re-exports rank_investment_candidates() and optimal_investment() from
hours_eoh.core.eoh_dynamics at the canonical research import path.

These functions are NOT wired into dashboard or simulation. They are
research tools for evaluating infrastructure investment alternatives.
Implementations live in core/eoh_dynamics.py alongside eoh_reduction_ratio()
to avoid a circular import.

Canonical import::

    from hours_eoh.research.investment import rank_investment_candidates, optimal_investment

Mission Statement: §"The production economy — build what maximizes net EOH
reduction per unit of maintenance obligation."
"""

from hours_eoh.core.eoh_dynamics import (  # noqa: F401
    rank_investment_candidates,
    optimal_investment,
    eoh_reduction_ratio,
)
