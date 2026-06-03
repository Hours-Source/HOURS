"""
hours_eoh.reference — Calibrated example data for the HOURS framework.

Importable by tests and by package users. Contains no domain logic —
pure data that demonstrates expected input shapes and covers the key
arc cases (normal, severe scarcity, recovering, oversupply, below/above
multiplier band).

Modules
-------
practitioners  Example practitioner/demand histories for scarcity_score()
workforce      Workforce composition snapshots for population_weighted_mean_multiplier()

Layer rule: this package imports nothing from hours_eoh core, land, or scenarios.
"""

from hours_eoh.reference.practitioners import (
    PRACTITIONER_HISTORIES,
    SEVERE_SCARCITY_EXAMPLE,
    RECOVERING_EXAMPLE,
    STABLE_EXAMPLE,
)
from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS

__all__ = [
    "PRACTITIONER_HISTORIES",
    "SEVERE_SCARCITY_EXAMPLE",
    "RECOVERING_EXAMPLE",
    "STABLE_EXAMPLE",
    "WORKFORCE_SNAPSHOTS",
]
