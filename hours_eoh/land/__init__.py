"""
Land module — Ground Use Fee and stewardship lease mechanics.

Land cannot be priced under the labor-content identity: it was not made
by human labor. Instead, the GUF measures the annual cost to the collective
of granting exclusive use: opportunity value (location), ecosystem service
displacement, and infrastructure draw. All fees are denominated in TEH and
flow to the Trust as circulatory revenue.

Direct submodule imports are the intended pattern::

    from hours_eoh.land.guf import ground_use_fee, guf_trust_inflow
    from hours_eoh.land.guf import epsilon_scaling, income_linked_subsidy

Mission Statement: §"Land is held by the collective … stewardship leases …
the fee reflects real costs rather than speculative value."
Template: NLSA Technical Manual TM-0042, Seventh Edition.
"""

from hours_eoh.land.collective import (
    compute_collective_guf,
    make_urban_collective,
    make_rural_collective,
)
from hours_eoh.land.calibration import (
    guf_rate_calibration,
    guf_lvi_weight_sensitivity,
)

__all__ = [
    "compute_collective_guf",
    "make_urban_collective",
    "make_rural_collective",
    "guf_rate_calibration",
    "guf_lvi_weight_sensitivity",
]
