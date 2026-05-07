"""
research/writedown — Ecological write-down modeling (future work).

Tracks the eco-collapse-1 open gap: when ecosystem_health collapses below
a critical threshold, accumulated ecological EOH obligations should be
written down (similar to capital write-down), destroying the TEH that was
created for work the ecosystem can no longer provide.

This module is a placeholder. The write-down mechanism requires:
  1. A per-unit ecological TEH ledger (analogous to capital_embodied_teh)
  2. A trigger condition: ecosystem_health < ECOLOGICAL_WRITEDOWN_THRESHOLD
  3. A partial write-down formula: fraction of ecological TEH destroyed per
     threshold-crossing event
  4. Integration with fiscal_snapshot() to report write-down as TEH destruction

Reference: Mission Statement §"Ecological entropy — threshold events";
eco-collapse-1 open gap in design_gaps_review.md.
"""

# Implementation pending (eco-collapse-1).
# See: hours_eoh.core.eoh_dynamics for capital write-down patterns to follow.
