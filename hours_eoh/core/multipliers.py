"""
Multiplier System

Adapted from hours_v6/core/functions_foundation.py with minor modification.
The underlying math is identical; the framing updates. The multiplier now
explicitly measures entropy-reduction leverage: how many EOH does one hour
of this person's labor address across any of the four domains?

Condition II: The population-weighted average multiplier must remain within
the band [1.8, 2.1] with a target of 2.1. Individual multipliers may extend
to M_MAX=6.0 for rare specializations.

Mission Statement: §"Condition II — Multiplier Band", §"Principle 4 — The
multiplier measures entropy-reduction leverage", §"The four-factor assessment
(training, demand, scarcity, impact) measures four aspects of this leverage
across all three layers without structural change."
"""

from __future__ import annotations

from hours_eoh.data import (
    DEFAULT_SEGMENTS, M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET, M_MAX,
)


# ---------------------------------------------------------------------------
# Epoch-alpha model calibration constants
# These control how the four-factor weights shift across the automation arc.
# ---------------------------------------------------------------------------
_ALPHA_TRAINING_BASE:      float = 0.30  # training weight at ε=0
_ALPHA_TRAINING_SLOPE:     float = 0.10  # training weight gain per ε unit
_ALPHA_DEMAND_BASE:        float = 0.25  # demand weight at ε=0.40 (peak)
_ALPHA_DEMAND_PEAK_EPS:    float = 0.40  # ε at which demand weight peaks
_ALPHA_DEMAND_CURVATURE:   float = 0.10  # demand weight curvature parameter
_ALPHA_SCARCITY_BASE:      float = 0.15  # scarcity weight at ε=0
_ALPHA_SCARCITY_GROWTH:    float = 0.20  # scarcity weight growth (multiplied by ε²)
_ALPHA_FACTOR_MIN:         float = 0.05  # minimum floor for any alpha weight


# ---------------------------------------------------------------------------
# Population-Weighted Mean Multiplier
# ---------------------------------------------------------------------------

def population_weighted_mean_multiplier(
    segments: list[dict] | None = None,
) -> float:
    """
    Population-weighted mean multiplier across all workforce tiers.

    Computes the weighted average: Σ(fraction_i × mean_mu_i) / Σ(fraction_i).
    Fractions should sum to 1.0 but the function normalizes if they don't,
    to handle floating-point drift in ε-adjusted segment distributions.

    The default segments are calibrated so the mean = M_BAND_TARGET = 2.10
    at ε=0.

    Args:
        segments: List of dicts, each with keys "name", "fraction", "mean_mu".
                  Defaults to DEFAULT_SEGMENTS from data.py.

    Returns:
        Population-weighted mean multiplier.

    Reference: Mission Statement §"The population-weighted average multiplier
    should be maintained within a defined band — a range of 1.8–2.1 with a
    target of 2.1."
    """
    if segments is None:
        segments = DEFAULT_SEGMENTS

    total_fraction = sum(s["fraction"] for s in segments)
    if total_fraction == 0:
        raise ValueError("Segment fractions sum to zero — cannot compute mean.")

    weighted_sum = sum(s["fraction"] * s["mean_mu"] for s in segments)
    return weighted_sum / total_fraction


# ---------------------------------------------------------------------------
# Multiplier Band Check (Condition II)
# ---------------------------------------------------------------------------

def multiplier_band_check(
    mean_multiplier: float,
    band_low: float = M_BAND_LOW,
    band_high: float = M_BAND_HIGH,
) -> dict:
    """
    Verify that the population-weighted mean multiplier is within the band.

    Condition II structural monitor. Returns a full result dict for dashboard
    integration. A result of "in_band=False" means the governing body must
    adjust tier assignments — either raising low-tier multipliers (BELOW_BAND)
    or tightening high-tier assignments (ABOVE_BAND).

    Args:
        mean_multiplier: Population-weighted mean multiplier.
        band_low: Lower bound. Default: 1.8.
        band_high: Upper bound. Default: 2.1.

    Returns:
        dict: {
          "mean_multiplier": float,
          "band_low": float,
          "band_high": float,
          "target": float,
          "in_band": bool,
          "distance_to_target": float,  # signed: negative = below target
          "status": "OK" | "BELOW_BAND" | "ABOVE_BAND"
        }

    Reference: Mission Statement §"Condition II — Multiplier Band"
    """
    in_band = band_low <= mean_multiplier <= band_high
    if mean_multiplier < band_low:
        status = "BELOW_BAND"
    elif mean_multiplier > band_high:
        status = "ABOVE_BAND"
    else:
        status = "OK"

    return {
        "mean_multiplier":      mean_multiplier,
        "band_low":             band_low,
        "band_high":            band_high,
        "target":               M_BAND_TARGET,
        "in_band":              in_band,
        "distance_to_target":   mean_multiplier - M_BAND_TARGET,
        "status":               status,
    }


# ---------------------------------------------------------------------------
# Tier Multiplier (four-factor assessment)
# ---------------------------------------------------------------------------

def tier_multiplier(
    training: float,
    demand: float,
    scarcity: float,
    impact: float,
    alpha_weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
    m_max: float = M_MAX,
) -> float:
    """
    Compute a tier multiplier from the four-factor entropy-reduction assessment.

    The four factors each measure a dimension of entropy-reduction leverage:
    - Training:  Investment required to develop this entropy-reduction capability
    - Demand:    Intensity of EOH demand for this specific skill
    - Scarcity:  How rare practitioners are relative to EOH demand for their skill
    - Impact:    Measurable EOH reduction per hour of this person's labor

    Each factor ∈ [0, 1]. Multiplier = 1.0 (base) + weighted factor sum scaled
    to (m_max - 1). Clamped to [1.0, m_max].

    The four-factor weights (alpha_weights) shift across economic layers — in the
    care economy, Training and Impact dominate; in production, Demand and Scarcity
    are prominent; in stewardship, all four balance. But the formula is structurally
    unchanged across layers (Mission Statement: Principle 4).

    Args:
        training: Training requirement ∈ [0, 1].
        demand: EOH demand intensity ∈ [0, 1].
        scarcity: Practitioner scarcity ∈ [0, 1].
        impact: Societal EOH impact ∈ [0, 1].
        alpha_weights: Weight of each factor (must sum to 1.0).
        m_max: Maximum allowed multiplier. Default: 6.0.

    Returns:
        Tier multiplier ∈ [1.0, m_max].

    Raises:
        ValueError: If any factor is outside [0, 1].

    Reference: Mission Statement §"Condition II" — four-factor assessment;
    §"Principle 4" — "The multiplier measures entropy-reduction leverage."
    """
    factors = {"training": training, "demand": demand,
               "scarcity": scarcity, "impact": impact}
    for name, val in factors.items():
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"Factor '{name}' must be in [0, 1], got {val}")

    if abs(sum(alpha_weights) - 1.0) > 0.001:
        raise ValueError(f"alpha_weights must sum to 1.0, got {sum(alpha_weights):.4f}")

    factor_values = (training, demand, scarcity, impact)
    weighted_sum = sum(a * f for a, f in zip(alpha_weights, factor_values))
    raw = 1.0 + weighted_sum * (m_max - 1.0)
    return min(max(raw, 1.0), m_max)


# ---------------------------------------------------------------------------
# Epoch-Adaptive Alpha Weights
# ---------------------------------------------------------------------------

def epoch_alpha_weights(
    epsilon: float,
) -> tuple[float, float, float, float]:
    """
    Factor weights (training, demand, scarcity, impact) adapted to automation level.

    The relative weight of each four-factor dimension shifts as the economy
    transitions through care, production, and stewardship layers. No discrete
    switch — continuous blending across the epsilon range.

    At ε=0 (care/subsistence economy):
      Training and Impact dominate — building and deploying human capacity
      to resist entropy is the primary leverage.

    At ε=0.40 (production economy):
      All four factors relatively balanced — standard professional tiers.

    At ε=0.90 (stewardship economy):
      Scarcity becomes critical — rare skills for rare maintenance tasks.
      Training remains high — deep expertise required for complex systems.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Tuple (alpha_training, alpha_demand, alpha_scarcity, alpha_impact)
        summing to 1.0.

    Reference: Mission Statement §"Principle 4" — "the relative weighting of
    factors shifts as the economy evolves."
    """
    # Training: high throughout, rises further at high ε (deep expertise needed)
    alpha_training = _ALPHA_TRAINING_BASE + _ALPHA_TRAINING_SLOPE * epsilon

    # Demand: high at mid-ε (production peak), falls at high ε (less raw demand)
    alpha_demand = _ALPHA_DEMAND_BASE - _ALPHA_DEMAND_CURVATURE * (epsilon - _ALPHA_DEMAND_PEAK_EPS) ** 2

    # Scarcity: low early, rises sharply at high ε (rare skills become critical)
    alpha_scarcity = _ALPHA_SCARCITY_BASE + _ALPHA_SCARCITY_GROWTH * (epsilon ** 2)

    # Impact: high throughout; normalize remainder
    alpha_impact = 1.0 - alpha_training - alpha_demand - alpha_scarcity

    # Clamp and renormalize to handle edge cases
    alphas = [max(_ALPHA_FACTOR_MIN, a) for a in
              (alpha_training, alpha_demand, alpha_scarcity, alpha_impact)]
    total = sum(alphas)
    normalized = tuple(a / total for a in alphas)
    return normalized  # type: ignore[return-value]
