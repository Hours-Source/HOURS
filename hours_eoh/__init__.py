"""
HOURS EOH — Entropy Obligation Hours framework.

Causal model: entropy generates EOH → workers fulfill registered EOH → TEH created.
Old model started from labor supply; this model starts from entropy demand.

Mission Statement: docs/mission_statement.md
"""

__version__ = "0.1.0"

# Public API — canonical entry points
from hours_eoh.params import EohParams, EOH_DEFAULTS
from hours_eoh import data

__all__ = [
    "EohParams",
    "EOH_DEFAULTS",
    "data",
]
