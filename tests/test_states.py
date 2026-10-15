"""
`reference/states.py` — the US by state, and the frame it divides.

The state table is the SAME measurement as the frame's land
(`US_MAINLAND_HECTARES` is ERS's "48 States" line), so the 49 units must sum to
it within ERS's own rounding, and the frame must read the mainland's mix.
"""

from __future__ import annotations

import math

from hours_eoh.data import US_MAINLAND_HECTARES
from hours_eoh.reference.parcels import (
    contiguous_48_private_parcels, private_parcels_by_state)
from hours_eoh.reference.states import (
    ACRES_PER_KACRE, contiguous_48_land_hectares_by_class, load_states)
from hours_eoh.reference.land_stewardship import ACRE_HECTARES

#: ERS publishes whole thousands of acres: a bound of 5 per class over nine
#: classes. The observed gap is 3 thousand acres (`utils/state_ingest.py`).
_ERS_ROUNDING_HA = 9 * 5 * ACRES_PER_KACRE * ACRE_HECTARES


class TestTheStatesAreTheFramesLand:

    def test_the_49_units_sum_to_the_frame(self):
        """Land to ERS rounding against the data.py constant; parcels' ends
        exactly against the frame's count (the central splits unknowns per
        state, so it is not additive and is not asserted)."""
        mainland = [s for s in load_states() if s["in_48_states"]]
        assert len(mainland) == 49
        land = sum(sum(s["land_hectares"].values()) for s in mainland)
        assert abs(land - US_MAINLAND_HECTARES) < _ERS_ROUNDING_HA
        by_state = private_parcels_by_state()
        frame = contiguous_48_private_parcels()
        for end in ("low", "high"):
            assert sum(by_state[s["statefp"]][end] for s in mainland) == frame[end]

    def test_the_us_frame_reads_the_mainlands_own_mix(self):
        """The frame's shares are the 48 + DC's, not the 50 states' (which put
        Alaska's parks and miscellaneous land on the mainland)."""
        from tests.test_frame_inputs import _labels
        got = _labels("--frame", "us")["land_use_fractions"]["value"]
        by_class = contiguous_48_land_hectares_by_class()
        total = sum(by_class.values())
        for k, ha in by_class.items():
            assert math.isclose(got[k], ha / total, rel_tol=1e-12), k
