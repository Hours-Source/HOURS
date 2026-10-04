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

RESHAPED TO THE PARTITION (2026-10-04, author: "an overbuilt collective
deferring all eco towards GUF that is then carried by the people"). The 100 B
hours below predates the ecological partition (Phases 4e/4f): it entered the
domain as ONE year's demand — 1,538 h/head, more than the labour supply.
The backlog is now DERIVED: the health deficit (1 − INDUST_ECOSYSTEM_HEALTH)
over the archetype's land, priced by `restoration_cost.deficit_obligation`,
and carried by its PEOPLE as labour with the recurring ecological work (the
GUF's under the partition) — `INDUST_ECOLOGICAL_CARRIED_BY_PEOPLE`. The 100 B
stays as the BASELINE it is compared with. The archetype is also a FRAME
FILE (`indust_frame()`, shipped as `indust_overbuilt`), so the corridor band
and every frame-aware shock run on it as on the US frame.

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
        **INDUST_NO_ECO_PIPELINE_KWARGS,
    )

The derived ecological backlog and its carriage by people are applied by
`scenarios/indust_overshoot`, which owns the scenario.
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
# THE FRAME THE BACKLOG IS STATED AT (2026-10-03). The 100 B hours above is "at
# a 65 M-person scale", and was applied unscaled at every population — at the
# CLI's 1M default, 65× the stated backlog per head; at the US frame, a fifth.
# Mode 6, the frame seam. It now scales with population like the capital
# beside it; at 65M it is bit-identical.
INDUST_REFERENCE_POPULATION: float = 65_000_000

# BASELINE since 2026-10-04: the derived backlog above replaced it. Kept so the
# old reading stays comparable (`indust_baseline_backlog`), never applied.

# The archetype's ε — a declaration, not a reading (ε is never imputed), and
# the ecological work carried by its people rather than the GUF.
INDUST_EPSILON: float = 0.40
INDUST_ECOLOGICAL_CARRIED_BY_PEOPLE: bool = True

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

def indust_baseline_backlog(population: float = INDUST_REFERENCE_POPULATION) -> float:
    """The superseded 100 B-hour backlog at `population` (scaled from its
    65 M frame) — the baseline the derived backlog is compared against."""
    return INDUST_DEFERRED_ECOLOGICAL * population / INDUST_REFERENCE_POPULATION


def indust_frame() -> dict:
    """
    The archetype as a FRAME FILE body — the ONE source of the shipped
    `indust_overbuilt` frame (`utils/frame_inputs.SHIPPED_FRAMES`; a test holds
    the file to this function). Values come from the constants above, so the
    file cannot drift from the scenario.
    """
    from hours_eoh.data import ECOLOGICAL_THRESHOLD, LAND_HECTARES_PER_CAPITA
    pop = INDUST_REFERENCE_POPULATION
    side = "below" if INDUST_ECOSYSTEM_HEALTH < ECOLOGICAL_THRESHOLD else "at or above"
    return {
        "name": "indust_overbuilt",
        "note": ("CONSTRUCTED, not a measurement: an overbuilt industrial collective "
                 f"— {INDUST_CAPITAL_MULTIPLIER:g}x the canonical capital per head, the "
                 f"stock {INDUST_CAPITAL_AGE_RATIO:.0%} through its design life, ecosystem "
                 f"health {INDUST_ECOSYSTEM_HEALTH} ({side} the spike threshold, "
                 f"{ECOLOGICAL_THRESHOLD}), and its "
                 "ecological work carried by its people rather than the GUF. A bound-"
                 "testing frame for how the framework handles collapse, not an everyday "
                 "collective. Its epsilon is declared, not read."),
        "population": pop,
        "epsilon": INDUST_EPSILON,
        "capital_teh": INDUST_CAPITAL_PER_CAPITA * pop,
        "capital_age_ratio": INDUST_CAPITAL_AGE_RATIO,
        "ecosystem_health": INDUST_ECOSYSTEM_HEALTH,
        "land_hectares": pop * LAND_HECTARES_PER_CAPITA,
        "ecological_carried_by_people": INDUST_ECOLOGICAL_CARRIED_BY_PEOPLE,
    }


def make_indust_no_eco_params(
    population: float = INDUST_REFERENCE_POPULATION,
    epsilon:    float = INDUST_EPSILON,
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
