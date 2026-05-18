"""
research/writedown — Ecological write-down: resolved via GUF layer (eco-collapse-1 closed).

The original placeholder described a TEH-destruction event analogous to the capital
write-down (D1): when ecosystem_health collapses below a threshold, destroy the TEH
that was created for work the ecosystem can no longer provide.

That framing is architecturally incorrect. TEH created for stewardship labor already
performed is legitimate — the labor happened. Ecological collapse does not retroactively
invalidate it. What changes is the collective's *forward obligation*: it must now fund
replacement infrastructure and maintain GUF revenue despite degraded natural baselines.

The correct mechanism lives in the GUF layer (NLSA §9):

  Restoration pathway (ecosystem recoverable):
    V_s baselines are reset to the restoration target, not the degraded state.
    E_reset continues charging parcels as though the ecosystem were functioning at
    the target level, preventing revenue collapse exactly when ecological EOH spikes.
    → ground_use_fee_writedown(..., services_lost=None)

  Abandonment pathway (ecosystem permanently altered):
    V_s baselines reset to the degraded state. A Rebuilding Surcharge R_b(p,ε) is
    added — the annualized labor cost of engineered replacement systems, distributed
    across affected parcels. Trust revenue is maintained for the replacement build.
    → ground_use_fee_writedown(..., services_lost=[...])

  Preventive signal (pre-collapse monitoring):
    When unfulfilled ecological EOH exceeds 30% of total assessed EOH, a formal
    accumulation warning triggers accelerated ρ_s review and ecology fund priority.
    → eoh_accumulation_warning(unfulfilled_eoh, total_eoh)

GUF revenue in all cases flows to the Trust's ecological allocation (circulatory TEH),
funding the response without any TEH destruction event on the ledger.

Reference: NLSA §9, Eq. 27–29; hours_eoh/land/guf.py.
"""

from hours_eoh.land.guf import (
    rebuilding_surcharge,
    ground_use_fee_writedown,
    eoh_accumulation_warning,
)

__all__ = [
    "rebuilding_surcharge",
    "ground_use_fee_writedown",
    "eoh_accumulation_warning",
]
