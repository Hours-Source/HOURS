"""
hours_eoh.reference — Calibrated example data for the HOURS framework.

Importable by tests and by package users. The package began as example
data: input shapes for the key arc cases (normal, severe scarcity,
recovering, oversupply, below/above multiplier band). It now also holds the
measured datasets and their derivations, 17 modules in all; CLAUDE.md's
module layout lists every one. It imports nothing from the domain layers.

The first six modules
---------------------
practitioners    Example practitioner/demand histories for scarcity_score()
workforce        Workforce composition snapshots for population_weighted_mean_multiplier()
onet_multipliers Measured O*NET/BLS reference multiplier registry (751 occupations)
onet_knowledge   Measured occupational training hours recovered from that registry
atus_time_use    Measured US time use 2003–2025 (BLS ATUS)
personal_basket  The personal obligation pinned to physical quantities

Callers import the last three, and every later module, by module name
(`from hours_eoh.reference import atus_time_use`). This package does not
re-export them, so an import of it stays cheap.

Layer rule: this package imports nothing from hours_eoh core, land, scenarios,
data or params — enforced by tests/test_reference_data.py::TestLayerIsolation.
"""

from hours_eoh.reference.practitioners import (
    PRACTITIONER_HISTORIES,
    SEVERE_SCARCITY_EXAMPLE,
    RECOVERING_EXAMPLE,
    STABLE_EXAMPLE,
)
from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS
from hours_eoh.reference.onet_multipliers import (
    OccupationMultiplier,
    load_registry,
    load_reference_bounds,
    registry_segments,
    anchor_pairs,
)

__all__ = [
    "PRACTITIONER_HISTORIES",
    "SEVERE_SCARCITY_EXAMPLE",
    "RECOVERING_EXAMPLE",
    "STABLE_EXAMPLE",
    "WORKFORCE_SNAPSHOTS",
    "OccupationMultiplier",
    "load_registry",
    "load_reference_bounds",
    "registry_segments",
    "anchor_pairs",
]
