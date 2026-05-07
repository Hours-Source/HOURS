"""
Industrialized / Ecologically-Neglected Scenario Parameters
(indust_no_eco)

Physical premise
----------------
A civilization that has built dense industrial capital (10× the canonical
per-capita capital base) under the assumption that infrastructure expansion is
neutral with respect to other entropy domains.  The result:

  - Infrastructure EOH is 10× the canonical burden and ages faster
    (capital_age_ratio = 0.75 vs. canonical 0.35 at ε=0.40)
  - Capital provides NO EOH offset in other domains and NO personal EOH
    fulfillment: it consumes entropy obligations, it does not reduce them
  - Decades of industrial externalities have pushed ecosystem health below
    the spike threshold (0.38 < 0.40) and accumulated a 100 B-hour
    deferred ecological backlog
  - No investment has been made in ecological monitoring or restoration

This is the archetype of industrial overshoot: large capital stock,
maximum maintenance burden, zero ecological credit, large deferred backlog.

Compare with the canonical baseline (ε=0.40, ecosystem_health=0.82,
capital offsets zero EOH) to observe fiscal and domain divergence.

Usage
-----
    from hours_eoh.indust_no_eco_params import make_indust_no_eco_params, INDUST_NO_ECO_PIPELINE_KWARGS

    p    = make_indust_no_eco_params(population=65_000_000)
    pipe = eoh_to_teh_pipeline(
        epsilon          = 0.40,
        population       = p["population"],
        capital_stock    = p["capital_stock_teh"],
        capital_age_ratio= p["capital_age_ratio"],
        ecosystem_health = p["ecosystem_health"],
        deferred_ecological = p["deferred_ecological"],
        **INDUST_NO_ECO_PIPELINE_KWARGS,
    )
"""

from __future__ import annotations

from hours_eoh.params import EohParams
from hours_eoh.data import CAPITAL_STOCK_DEFAULT

# ---------------------------------------------------------------------------
# Scenario constants
# ---------------------------------------------------------------------------

INDUST_CAPITAL_MULTIPLIER:   float = 10.0
# Capital per capita = canonical 2 000 TEH × 10 — dense built infrastructure.
INDUST_CAPITAL_PER_CAPITA:   float = (CAPITAL_STOCK_DEFAULT / 1_000_000) * INDUST_CAPITAL_MULTIPLIER

# Aging industrial stock: 3/4 through design life (deferred renewal typical
# of heavy-industry economies that prioritise expansion over maintenance).
INDUST_CAPITAL_AGE_RATIO:    float = 0.75

# Ecosystem health below spike threshold (0.40): active threshold-failure
# regime — the nonlinear penalty in ecological_eoh() is now live.
INDUST_ECOSYSTEM_HEALTH:     float = 0.38

# 100 B hours of accumulated deferred ecological obligation — roughly
# four-to-five decades of industrial-era neglect at a 65 M-person scale.
# At ε=0.40 monitoring capability = 0.70, so 70 B hours are visible to
# the ledger (nearly half of personal EOH for a 65 M population).
INDUST_DEFERRED_ECOLOGICAL:  float = 100_000_000_000.0

# Capital provides no EOH reduction in any domain — it consumes only.
# Setting both to zero explicitly: the industrial capital stock generates
# infrastructure EOH (maintenance burden) but does NOT offset personal,
# ecological, or knowledge EOH.
INDUST_CAPITAL_EOH_ELIMINATED:         float = 0.0
INDUST_CAPITAL_PERSONAL_EOH_FULFILLED: float = 0.0

# ---------------------------------------------------------------------------
# EohParams overrides (keys present in EOH_DEFAULTS)
# ---------------------------------------------------------------------------
INDUST_NO_ECO_OVERRIDES: dict = {
    "capital_age_ratio":   INDUST_CAPITAL_AGE_RATIO,
    "ecosystem_health":    INDUST_ECOSYSTEM_HEALTH,
    "deferred_ecological": INDUST_DEFERRED_ECOLOGICAL,
}

# ---------------------------------------------------------------------------
# Pipeline kwargs passed directly to eoh_to_teh_pipeline() / total_eoh()
# (not stored in EohParams — no defaults exist for these in EOH_DEFAULTS)
# ---------------------------------------------------------------------------
INDUST_NO_ECO_PIPELINE_KWARGS: dict = {
    "capital_eoh_eliminated":          INDUST_CAPITAL_EOH_ELIMINATED,
    "capital_personal_eoh_fulfilled":  INDUST_CAPITAL_PERSONAL_EOH_FULFILLED,
}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_indust_no_eco_params(
    population: float = 65_000_000,
    epsilon:    float = 0.40,
) -> EohParams:
    """
    Construct an EohParams instance calibrated to the industrial/no-ecology scenario.

    Capital stock is scaled proportionally to population at
    INDUST_CAPITAL_MULTIPLIER × the canonical per-capita baseline. All other
    scenario constants are fixed above and documented in this module.

    Note: INDUST_NO_ECO_PIPELINE_KWARGS must be passed separately when calling
    eoh_to_teh_pipeline() or total_eoh() — those parameters are not stored in
    EohParams because they have no entry in EOH_DEFAULTS.

    Args:
        population: Civilization population. Default: 65M (medium country).
        epsilon:    Automation level for context label. Does not alter physical-
                    state parameters (those are set explicitly above).

    Returns:
        EohParams with industrial-overshoot calibration applied.
    """
    p = EohParams()
    p.set("population",
          population,
          phase=0, reason="indust_no_eco scenario")
    p.set("capital_stock_teh",
          INDUST_CAPITAL_PER_CAPITA * population,
          phase=0, reason=f"10× industrial capital base ({INDUST_CAPITAL_MULTIPLIER}× canonical)")
    for key, val in INDUST_NO_ECO_OVERRIDES.items():
        p.set(key, val, phase=0, reason="indust_no_eco scenario")
    return p
