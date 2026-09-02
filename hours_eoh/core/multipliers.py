"""
Multiplier System

Adapted from hours_v6/core/functions_foundation.py with minor modification.
The underlying math is identical; the framing updates. The multiplier now
explicitly measures entropy-reduction leverage: how many EOH does one hour
of this person's labor address across any of the four domains?

THE MULTIPLIER SETS THE FLOOR WAGE RATE, NOT THE UNIVERSAL PRICE
----------------------------------------------------------------
This is the price-as-floor reframing (reconciliation §3, workstream C, author
sign-off 2026-08-15) and it changes what this module is answerable for.

The multiplier prices the base rate at which the collective guarantees to pay
for fulfilling a registered entropy obligation. It does NOT set the economy-wide
price of that labor; discovery does, above the floor, via the `market_premium`
seam in core/prices.floor_price().

Why this matters more than a docstring usually does: the skill differential is
the wound that killed Owen's National Equitable Labour Exchange in 1834, and the
limit time banking survives by refusing to touch (docs/theory/prior_art.md).
Owen's promoters had to set THE price of a skilled hour against an unskilled one
and could not. This module does not carry that burden. A floor need only be
FAIR ENOUGH — wrong by a little means someone is briefly underpaid at the floor
and takes the premium instead, not that the economy misprices the trade. Much of
the measurement burden the working paper's §4.2 assumed dissolves with it.

Condition II: The population-weighted average multiplier must remain within
the band [1.8, 2.1] with a target of 2.1. Individual multipliers may extend
to M_MAX=6.0 for rare specializations.

That band is a CONSTITUTIONAL commitment, not a measurement — `M_BAND_LOW`,
`M_BAND_HIGH`, `M_BAND_TARGET` and `M_MAX` are all tagged `normative` in data.py,
with `decided_by` naming a charter rather than a `resolves_by` naming evidence.
They previously claimed `Physics`, justified by an argument about fairness
between labor tiers, which is an argument about legitimacy and not about entropy.
The strongest reason to hold the band is that it was decided; there is no reason
to call it physics.

Mission Statement: §"Condition II — Multiplier Band", §"Principle 4 — The
multiplier measures entropy-reduction leverage", §"The four-factor assessment
(training, demand, scarcity, impact) measures four aspects of this leverage
across all three layers without structural change."
"""

from __future__ import annotations

from hours_eoh.reference.onet_multipliers import registry_segments

# THE DEFAULT WORKFORCE IS MEASURED, NOT CALIBRATED (2026-08-16). This was
# data.DEFAULT_SEGMENTS — four synthetic tiers whose means were set so the
# weighted mean landed on 2.10, the TOP of the constitutional band. A default
# reverse-engineered from the target it is checked against cannot test anything,
# and any caller omitting `segments` was scored against it.
#
# registry_segments() is the O*NET 30.3/BLS registry: 751 occupations, 94.2% of
# US employment, one segment per occupation weighted by employment. It gives
# 1.9964 — inside [1.8, 2.1] on its own evidence rather than pinned to the
# ceiling by construction.
#
# LAYER NOTE: core/ imports reference/ here, which is permitted ("reference/
# imports nothing from the package — pure data; any layer may import from it")
# and is the first time core/ exercises it. reference/ holds no domain logic and
# cannot import back, so the dependency stays acyclic.

from typing import TypedDict

from hours_eoh.data import (
    DEFAULT_SEGMENTS, M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET, M_MAX,
    SCARCITY_ROLLING_WINDOW, SCARCITY_SUPPLY_LAG_YEARS, SCARCITY_SEVERE_THRESHOLD,
    TRAINING_VALIDATION_TOLERANCE,
    ARTIFICIAL_SCARCITY_PASS_RATE_FLOOR, ARTIFICIAL_SCARCITY_QUALITY_THRESHOLD,
    TIER_ASSESSMENT_INTERVAL_YEARS,
    ALPHA_SCALE,
    ALPHA_IMPACT_EOH_REDUCTION_WEIGHT, ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT,
    ALPHA_IMPACT_RESILIENCE_WEIGHT,
    GOVERNANCE_MIN_ASSESSORS, GOVERNANCE_IRR_WARN_THRESHOLD, GOVERNANCE_IRR_CRIT_THRESHOLD,
    M_FLOOR, M_GEOMETRIC_R, M_COMPOSITE_Z_LO, M_COMPOSITE_Z_HI,
    M_FACTOR_WEIGHTS, M_IMPACT_SUBDOMAIN_WEIGHTS,
    M_IMPACT_COMPOSITE_LO, M_IMPACT_COMPOSITE_HI, M_EPOCH_WEIGHT_ANCHORS,
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
        segments = registry_segments()

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
# Reclassification Impact (Condition II governance query)
# ---------------------------------------------------------------------------

def reclassification_impact(
    segments: list[dict],
    changes: list[dict],
) -> dict:
    """
    Compute the M band impact of proposed tier reclassifications.

    Answers the governance question: "if we reclassify occupation X from
    mean multiplier A to mean multiplier B (affecting fraction F of the
    workforce), does M stay within the [1.8, 2.1] band?"

    Does not change tier fractions — only mean_mu per segment. Structural
    changes to workforce composition (fraction rebalancing) are outside
    the scope of a reclassification query.

    Args:
        segments: Current workforce distribution. Each dict must have keys
                  "name" (str), "fraction" (float), and "mean_mu" (float).
                  Same format as population_weighted_mean_multiplier().
        changes: Proposed reclassifications. Each dict must have keys
                 "name" (str, must match a segment) and "new_mean_mu" (float).
                 Multiple segments may be updated in a single call.

    Returns:
        dict with keys:
          "segments_before"     list[dict]   original segments (not mutated)
          "segments_after"      list[dict]   modified copy with changes applied
          "m_before"            float        population_weighted_mean_multiplier(segments)
          "m_after"             float        population_weighted_mean_multiplier(segments_after)
          "m_delta"             float        m_after − m_before
          "band_before"         dict         full multiplier_band_check(m_before) result
          "band_after"          dict         full multiplier_band_check(m_after) result
          "passes"              bool         band_after["in_band"]
          "changes_applied"     list[dict]   the changes list as provided
          "absorption_remaining" dict:
              "to_ceiling"           float   M_BAND_HIGH − m_after  (>0 = room to rise)
              "to_floor"             float   m_after − M_BAND_LOW   (>0 = room to fall)
              "further_drift_budget" float   budget in direction of this change

    Raises:
        ValueError: If any change names a segment not present in segments.

    Reference: Mission Statement §"Condition II — Multiplier Band"; §"Anti-gaming
    safeguard 3 — sunset mechanism"; Roadmap §2.3 (inverse query system).
    """
    segment_names = {s["name"] for s in segments}
    change_map: dict[str, float] = {}
    for change in changes:
        if change["name"] not in segment_names:
            raise ValueError(
                f"Change targets segment '{change['name']}' which is not in segments. "
                f"Available: {sorted(segment_names)}"
            )
        change_map[change["name"]] = change["new_mean_mu"]

    segments_after = [{**s, "mean_mu": change_map.get(s["name"], s["mean_mu"])} for s in segments]

    m_before = population_weighted_mean_multiplier(segments)
    m_after  = population_weighted_mean_multiplier(segments_after)
    m_delta  = m_after - m_before

    band_before = multiplier_band_check(m_before)
    band_after  = multiplier_band_check(m_after)

    to_ceiling = M_BAND_HIGH - m_after
    to_floor   = m_after - M_BAND_LOW

    further_drift_budget = (
        to_ceiling if m_delta > 0.0 else (to_floor if m_delta < 0.0 else min(to_ceiling, to_floor))
    )

    return {
        "segments_before":  [{**s} for s in segments],
        "segments_after":   segments_after,
        "m_before":         m_before,
        "m_after":          m_after,
        "m_delta":          m_delta,
        "band_before":      band_before,
        "band_after":       band_after,
        "passes":           band_after["in_band"],
        "changes_applied":  list(changes),
        "absorption_remaining": {
            "to_ceiling":           to_ceiling,
            "to_floor":             to_floor,
            "further_drift_budget": further_drift_budget,
        },
    }


# ---------------------------------------------------------------------------
# Reference multiplier — measured-data geometric map (mult-5.1.0, FROZEN)
#
# This is the ADOPTED reference multiplier form (author sign-off 2026-07-30),
# replacing the additive tier_multiplier() below for the minted floor. It is
# calibrated on measured O*NET/BLS factor levels (hours_eoh.reference.
# onet_multipliers) rather than on hand-assigned factor scores.
#
#     composite = Σ w_i · f_i                          (composite_from_factors)
#     z = clip((composite − Z_LO)/(Z_HI − Z_LO), 0, 1)
#     m = FLOOR · R ** z                               (reference_multiplier)
#
# The map has no free parameters: FLOOR is constitutional, R and the z-range are
# DERIVED-THEN-FROZEN at the reference epoch, curvature is deleted. See
# the multiplier falsifiability pass — the rank ordering and pairwise
# ratios are the measurements; the absolute range/spread/band pass are
# construction artifacts of the normalization choice.
# ---------------------------------------------------------------------------

def composite_from_factors(
    training: float,
    demand: float,
    scarcity: float,
    impact: float,
    weights: tuple[float, float, float, float] = M_FACTOR_WEIGHTS,
) -> float:
    """
    Weighted composite of the four measured assessment factors.

    Governing equation:
        composite = w_T·T + w_D·D + w_S·S + w_I·I

    Each factor is an economy-wide normalized measurement ∈ [0, 1]
    (`hours_eoh.reference.onet_multipliers`). At the frozen weights
    M_FACTOR_WEIGHTS = (0.30, 0.25, 0.20, 0.25) this reproduces the registry's
    `composite` column exactly. `weights` is exposed so the sensitivity harness
    can perturb the (CHOSEN) split; pass `epoch_factor_weights(ε)` for
    arc-adapted weighting.

    ε-behavior: this function is ε-agnostic; ε enters only through `weights`.
    At ε=0.40 the epoch weights equal the frozen weights by construction.

    Worked example (Chief Executives, occ 11-1011):
        T=1.000, D=0.30698, S=0.22586, I=0.62812, frozen weights →
        composite = 0.30 + 0.076746 + 0.045172 + 0.157031 ≈ 0.5789

    Args:
        training, demand, scarcity, impact: measured factors ∈ [0, 1].
        weights: (w_T, w_D, w_S, w_I); need not sum to 1 but conventionally does.

    Returns:
        composite score (same scale as the factors when weights sum to 1).

    Raises:
        ValueError: if any factor is outside [0, 1].

    Reference: the multiplier methodology parameters §multiplier_map;
    reconciliation §3 (floor semantics).
    """
    factors = {"training": training, "demand": demand,
               "scarcity": scarcity, "impact": impact}
    for name, val in factors.items():
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"Factor '{name}' must be in [0, 1], got {val}")
    w_t, w_d, w_s, w_i = weights
    return w_t * training + w_d * demand + w_s * scarcity + w_i * impact


def impact_composite_from_subdomains(
    dependency: float,
    substitutability: float,
    harm: float,
    temporal: float,
    weights: tuple[float, float, float, float] = M_IMPACT_SUBDOMAIN_WEIGHTS,
    lo: float = M_IMPACT_COMPOSITE_LO,
    hi: float = M_IMPACT_COMPOSITE_HI,
) -> float:
    """
    Reconstruct the measured impact factor f_impact from its four sub-components.

    Governing equations:
        raw = w_dep·dependency + w_sub·substitutability + w_harm·harm + w_temp·temporal
        f_impact = clip((raw − lo)/(hi − lo), 0, 1)          (affine outer-normalization)

    The outer-normalization is an affine rescale (rank- and spacing-preserving)
    that makes the stated sub-domain weights operative — without it a composite
    of near-orthogonal parts concentrates toward the middle and the stated
    weights become fiction (see `reference/data/multiplier_reference_bounds.json`
    → outer_normalization).
    `lo`/`hi` are FROZEN; `weights` is exposed for the sensitivity harness (the
    impact sub-domain split is CHOSEN, uncalibrated).

    Worked example (Chief Executives): dep=0.99341, sub=0.07222, harm=0.58403,
        temp=0.66804, frozen weights → raw ≈ 0.59569 →
        f_impact = (0.59569 − 0.33175)/(0.75196 − 0.33175) ≈ 0.6281

    Args:
        dependency, substitutability, harm, temporal: measured sub-components ∈ [0, 1].
        weights: (w_dep, w_sub, w_harm, w_temp).
        lo, hi: frozen impact-composite normalization bounds; hi must exceed lo.

    Returns:
        f_impact ∈ [0, 1], the impact argument to composite_from_factors().

    Raises:
        ValueError: if any sub-component is outside [0, 1] or hi ≤ lo.

    Reference: the multiplier methodology parameters §factors.impact.
    """
    subs = {"dependency": dependency, "substitutability": substitutability,
            "harm": harm, "temporal": temporal}
    for name, val in subs.items():
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"Impact sub-component '{name}' must be in [0, 1], got {val}")
    if hi <= lo:
        raise ValueError(f"impact-composite bounds require hi > lo, got lo={lo}, hi={hi}")
    w_dep, w_sub, w_harm, w_temp = weights
    raw = w_dep * dependency + w_sub * substitutability + w_harm * harm + w_temp * temporal
    f = (raw - lo) / (hi - lo)
    return min(1.0, max(0.0, f))


def reference_multiplier(
    composite: float,
    floor: float = M_FLOOR,
    R: float = M_GEOMETRIC_R,
    z_lo: float = M_COMPOSITE_Z_LO,
    z_hi: float = M_COMPOSITE_Z_HI,
) -> float:
    """
    Minted-floor multiplier from a factor composite via the frozen geometric map.

    Governing equations:
        z = clip((composite − z_lo)/(z_hi − z_lo), 0, 1)
        m = floor · R ** z

    This is the ADOPTED reference form (author sign-off 2026-07-30). It prices
    ONE HOUR of labour and sets the FLOOR at which TEH is minted — not realized
    earnings; a discovered market premium sits on top (reconciliation §3,
    market_premium hook). The map has no free parameters: `floor` is
    constitutional, `R` and the z-range are DERIVED-THEN-FROZEN at the reference
    epoch. Output is bounded to [floor, floor·R] = [1.0, 3.2] at defaults, well
    under the aspirational M_MAX = 6.0 cap (which has never bound).

    ε-behavior: the map itself is ε-invariant (a frozen cross-section). ε enters
    upstream through the composite's factor weights — pass a composite built with
    `epoch_factor_weights(ε)` for arc behavior. Degrades gracefully at every ε:
    z is clipped, so no discontinuity or division issue across [0, 0.99].

    Worked example (Chief Executives, composite 0.5789):
        z = (0.5789 − 0.15307)/(0.74020 − 0.15307) = 0.7253
        m = 1.0 · 3.2 ** 0.7253 ≈ 2.325   (matches the registry)

    Args:
        composite: weighted factor composite (from composite_from_factors()).
        floor: constitutional floor multiplier (default M_FLOOR = 1.0).
        R: frozen spread ratio (default M_GEOMETRIC_R = 3.2).
        z_lo, z_hi: frozen composite normalization range; z_hi must exceed z_lo.

    Returns:
        Minted-floor multiplier ∈ [floor, floor·R].

    Raises:
        ValueError: if z_hi ≤ z_lo.

    Reference: `reference/data/multiplier_reference_bounds.json` (shipped mirror of
    the multiplier handoff's bounds file, which is local-only); README semantics;
    reconciliation §3.
    """
    if z_hi <= z_lo:
        raise ValueError(f"composite z-range requires z_hi > z_lo, got z_lo={z_lo}, z_hi={z_hi}")
    z = (composite - z_lo) / (z_hi - z_lo)
    z = min(1.0, max(0.0, z))
    return floor * (R ** z)


def epoch_factor_weights(
    epsilon: float,
) -> tuple[float, float, float, float]:
    """
    Factor weights (training, demand, scarcity, impact) adapted to automation level.

    Piecewise-linear interpolation over the CHOSEN anchors M_EPOCH_WEIGHT_ANCHORS.
    This is the measured-data-aligned replacement for the additive form's
    epoch_alpha_weights(): it returns NORMALIZED weights summing to 1.0 (fractions
    of the composite), not absolute TEH/hr α coefficients. Feed the result to
    composite_from_factors() and then reference_multiplier().

    Governing behavior (anchors, each summing to 1.0):
        ε=0.00 → (0.35, 0.30, 0.20, 0.15)   care/subsistence: training+demand lead
        ε=0.40 → (0.30, 0.25, 0.20, 0.25)   production: balanced (= frozen weights)
        ε=0.90 → (0.20, 0.20, 0.20, 0.40)   stewardship: impact rising
        ε=0.99 → (0.15, 0.15, 0.15, 0.55)   copy/merge limit: impact dominates
    Values between anchors are linearly interpolated; outside [0, 0.99] the
    nearest anchor is held (clamped). The convex interpolation preserves sum = 1.

    Epistemic status: CHOSEN. The ε-dependence encodes a governance judgement
    (which leverage matters as machines take over), not a measurement. The
    ε=0.99 shape is the theoretical limit where training/scarcity/demand
    degenerate under copy/merge and only impact survives (handoffs KNOWN_ISSUES §5).

    Args:
        epsilon: automation level; clamped to the anchor range [0.0, 0.99].

    Returns:
        (w_training, w_demand, w_scarcity, w_impact) summing to 1.0.

    Reference: the multiplier methodology parameters §factors.weights_by_epsilon.
    """
    anchors = sorted(M_EPOCH_WEIGHT_ANCHORS.items())
    lo_eps, lo_w = anchors[0]
    hi_eps, hi_w = anchors[-1]
    if epsilon <= lo_eps:
        weights = lo_w
    elif epsilon >= hi_eps:
        weights = hi_w
    else:
        # find the bracketing anchor pair
        left_eps, left_w = lo_eps, lo_w
        right_eps, right_w = hi_eps, hi_w
        for a_eps, a_w in anchors:
            if a_eps <= epsilon:
                left_eps, left_w = a_eps, a_w
            if a_eps >= epsilon:
                right_eps, right_w = a_eps, a_w
                break
        span = right_eps - left_eps
        t = 0.0 if span == 0.0 else (epsilon - left_eps) / span
        weights = tuple(l + t * (r - l) for l, r in zip(left_w, right_w))  # type: ignore[assignment]
    total = sum(weights)
    return tuple(w / total for w in weights)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Tier Multiplier (four-factor assessment) — DEPRECATED additive form
#
# Retained for backward compatibility. SUPERSEDED for the reference multiplier
# by the geometric map above (reference_multiplier / composite_from_factors),
# author sign-off 2026-07-30. The additive floor term "1.0 +" mechanically
# compresses the ladder (the multiplier registry's known issues §3); the measured
# pass adopts the geometric map instead. New code should prefer
# reference_multiplier(); this function and epoch_alpha_weights() are kept so
# existing callers and the alpha-coefficient interpretation remain available.
# ---------------------------------------------------------------------------

def tier_multiplier(
    training: float,
    demand: float,
    scarcity: float,
    impact: float,
    alpha_coefficients: tuple[float, float, float, float] = (1.25, 1.25, 1.25, 1.25),
    m_max: float = M_MAX,
) -> float:
    """
    Compute a tier multiplier from the four-factor entropy-reduction assessment.

    Paper §4.2 additive form:
        m(c) = 1 + α₁·T(c) + α₂·D(c) + α₃·S(c) + α₄·I(c)

    NOTE: this multiplier sets the floor wage rate, not the economy-wide price.
    See reconciliation §3 and §5. Awaiting author sign-off before propagating to README/docs/.

    The four factors each measure a dimension of entropy-reduction leverage:
    - Training (T):  Investment required to develop this entropy-reduction capability
    - Demand (D):    Intensity of EOH demand for this specific skill
    - Scarcity (S):  How rare practitioners are relative to EOH demand for their skill
    - Impact (I):    Measurable EOH reduction per hour of this person's labor (use
                     compute_impact_score() to derive from observable sub-questions)

    Each factor ∈ [0, 1]. Each αᵢ is an absolute coefficient in TEH/hr per unit
    factor score. The default (1.25, 1.25, 1.25, 1.25) sums to ALPHA_SCALE = 5.0,
    so m reaches M_MAX = 6.0 when all factors are 1.0.

    For arc-correct behavior across the automation arc, pass
    alpha_coefficients = epoch_alpha_weights(epsilon). At ε=0.40 the returned
    coefficients are approximately (1.70, 1.25, 0.91, 1.14).

    ε-behavior of coefficients (from epoch_alpha_weights):
    - α₁ (training): high throughout; rises further as ε→1 (deep expertise)
    - α₂ (demand): peaks near ε=0.40 (production economy), falls at high ε
    - α₃ (scarcity): rises sharply at high ε (rare skills become critical)
    - α₄ (impact): holds residual; high at low ε, compressed at high ε

    Worked example at ε=0.40 (α ≈ 1.70, 1.25, 0.91, 1.14):
        T=0.65, D=0.55, S=0.30, I=0.45
        m = 1 + 1.70×0.65 + 1.25×0.55 + 0.91×0.30 + 1.14×0.45 ≈ 3.58

    Args:
        training: Training requirement ∈ [0, 1].
        demand: EOH demand intensity ∈ [0, 1].
        scarcity: Practitioner scarcity ∈ [0, 1]. Use scarcity_score() to derive.
        impact: Societal EOH impact ∈ [0, 1]. Use compute_impact_score() to derive.
        alpha_coefficients: Absolute TEH/hr coefficients for each factor. Expected
            to sum to ALPHA_SCALE (= M_MAX - 1 = 5.0). Default: balanced equal weights.
        m_max: Maximum allowed multiplier. Default: M_MAX = 6.0.

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

    a1, a2, a3, a4 = alpha_coefficients
    raw = 1.0 + a1 * training + a2 * demand + a3 * scarcity + a4 * impact
    return min(max(raw, 1.0), m_max)


# ---------------------------------------------------------------------------
# Epoch-Adaptive Alpha Weights
# ---------------------------------------------------------------------------

def epoch_alpha_weights(
    epsilon: float,
) -> tuple[float, float, float, float]:
    """
    Absolute alpha coefficients (training, demand, scarcity, impact) for the
    tier_multiplier() additive formula, adapted to automation level.

    DEPRECATED (2026-07-30): the additive reference form is superseded by the
    geometric map. For the measured-data reference multiplier use
    epoch_factor_weights() → composite_from_factors() → reference_multiplier().
    Retained for backward compatibility and the α-coefficient interpretation.

    Governing equations:
        α₁(ε) = BASE_train + SLOPE_train × ε
        α₂(ε) = BASE_demand − CURV_demand × (ε − ε_peak)²
        α₃(ε) = BASE_scarcity + GROWTH_scarcity × ε²
        α₄(ε) = residual (floor-clamped, renormalized)

    All four are then normalized to relative fractions, then scaled by ALPHA_SCALE
    so they sum to ALPHA_SCALE = M_MAX − 1 = 5.0.  The shape (which factor
    dominates at each ε) is unchanged from the normalized form; only the scale
    changes. To recover normalized fractions: divide each coefficient by ALPHA_SCALE.

    At ε=0 (care/subsistence economy):
      Training and Impact dominate — building and deploying human capacity
      to resist entropy is the primary leverage.

    At ε=0.40 (production economy):
      All four factors relatively balanced — standard professional tiers.

    At ε≈0.99 (stewardship economy):
      Scarcity becomes critical — rare skills for rare maintenance tasks.
      Training remains high — deep expertise required for complex systems.

    Example coefficient values:
        ε=0.00: α ≈ (1.50, 1.17, 0.75, 1.58)  sum = 5.0
        ε=0.40: α ≈ (1.70, 1.25, 0.91, 1.14)  sum = 5.0
        ε=0.99: α ≈ (1.98, 1.06, 1.71, 0.25)  sum = 5.0

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Tuple (alpha_training, alpha_demand, alpha_scarcity, alpha_impact) of
        absolute TEH/hr coefficients summing to ALPHA_SCALE ≈ 5.0.

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

    # Clamp to minimum floor and renormalize to relative fractions, then scale
    # to absolute coefficients summing to ALPHA_SCALE
    alphas = [max(_ALPHA_FACTOR_MIN, a) for a in
              (alpha_training, alpha_demand, alpha_scarcity, alpha_impact)]
    total = sum(alphas)
    absolute = tuple(a / total * ALPHA_SCALE for a in alphas)
    return absolute  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Scarcity Score (B3) — rolling average with supply-response discount
# ---------------------------------------------------------------------------

def scarcity_score(
    history: list[tuple[float, float]],
    supply_elasticity: float = 0.0,
    supply_lag_years: float = SCARCITY_SUPPLY_LAG_YEARS,
    window: int = SCARCITY_ROLLING_WINDOW,
) -> dict:
    """
    Compute a dampened scarcity factor from practitioner/demand history.

    Produces the `scarcity` argument for `tier_multiplier()`. Using a rolling
    average over multiple periods prevents annual oscillation; the supply-response
    discount prevents over-rewarding roles where raising the multiplier will itself
    resolve the scarcity within a few years.

    Args:
        history: List of (practitioner_count, demand_eoh) pairs, most-recent last.
                 At least one entry required. demand_eoh must be > 0.
        supply_elasticity: Expected fractional annual growth in practitioners if
                 the multiplier is raised (e.g. 0.10 = 10%/year). Default 0 = no
                 discount applied.
        supply_lag_years: Years before the supply response materializes. Controls
                 the discount horizon.
        window: Number of recent periods to include in the rolling average.

    Returns:
        dict with keys:
          "scarcity"                float  final score ∈ [0,1] — use as tier_multiplier() scarcity arg
          "raw_current"             float  point-in-time scarcity from the latest entry
          "rolling_mean"            float  rolling window average before supply discount
          "supply_adjusted"         float  after supply-response discount (= rolling_mean if no elasticity)
          "window_size"             int    periods actually used
          "supply_discount_applied" bool
          "status"                  str    "OK" | "SEVERE_SCARCITY"

    Raises:
        ValueError: If history is empty or any demand_eoh ≤ 0.

    Reference: Mission Statement §"Scarcity — rolling average and supply-response
    discount"; Roadmap Track B3.
    """
    if not history:
        raise ValueError("history must contain at least one (practitioners, demand_eoh) entry")
    for i, (p, d) in enumerate(history):
        if d <= 0.0:
            raise ValueError(f"demand_eoh must be > 0; entry {i} has demand_eoh={d}")
        if p < 0.0:
            raise ValueError(f"practitioner_count must be >= 0; entry {i} has {p}")

    window_entries = history[-window:]
    window_size = len(window_entries)

    raw_values = [max(0.0, min(1.0, 1.0 - p / d)) for p, d in window_entries]
    rolling_mean = sum(raw_values) / window_size

    # Latest entry for supply-response calculation
    practitioners_now, demand_now = history[-1]
    raw_current = raw_values[-1]

    discount_applied = False
    if supply_elasticity > 0.0 and raw_current > 0.0:
        future_practitioners = practitioners_now * (1.0 + supply_elasticity * supply_lag_years)
        future_raw = max(0.0, min(1.0, 1.0 - future_practitioners / demand_now))
        supply_adjusted = min(1.0, rolling_mean * (future_raw / raw_current))
        discount_applied = True
    else:
        supply_adjusted = rolling_mean

    scarcity = supply_adjusted
    status = "SEVERE_SCARCITY" if scarcity > SCARCITY_SEVERE_THRESHOLD else "OK"

    return {
        "scarcity":                scarcity,
        "raw_current":             raw_current,
        "rolling_mean":            rolling_mean,
        "supply_adjusted":         supply_adjusted,
        "window_size":             window_size,
        "supply_discount_applied": discount_applied,
        "status":                  status,
    }


# ---------------------------------------------------------------------------
# Anti-Gaming Safeguards (B5)
# ---------------------------------------------------------------------------

def validate_training_duration(
    mandated_years: float,
    median_competency_years: float,
    tolerance_factor: float = TRAINING_VALIDATION_TOLERANCE,
) -> dict:
    """
    Check whether mandated training duration is empirically justified.

    Flags roles where the officially required training time substantially
    exceeds the median time for practitioners to demonstrate competency.
    Excess mandated duration without competency justification is a signal of
    credential inflation or manufactured barriers to entry.

    Args:
        mandated_years: Officially required training duration in years.
        median_competency_years: Observed median time-to-competency from
                 practitioner cohort data.
        tolerance_factor: Ratio ceiling above which the gap is flagged.
                 Default 1.5 (mandated may be up to 50% longer than median).

    Returns:
        dict with keys:
          "mandated_years"          float
          "median_competency_years" float
          "ratio"                   float  mandated / median
          "tolerance_factor"        float
          "passes"                  bool
          "status"                  str    "OK" | "TRAINING_INFLATION"

    Raises:
        ValueError: If either duration is not positive.

    Reference: Mission Statement §"Anti-gaming safeguard 1 — empirical training
    validation"; Roadmap Track B5.
    """
    if mandated_years < 0.0:
        raise ValueError(f"mandated_years must be >= 0, got {mandated_years}")
    if median_competency_years <= 0.0:
        raise ValueError(f"median_competency_years must be > 0, got {median_competency_years}")

    ratio = mandated_years / median_competency_years
    passes = ratio <= tolerance_factor
    status = "OK" if passes else "TRAINING_INFLATION"

    return {
        "mandated_years":          mandated_years,
        "median_competency_years": median_competency_years,
        "ratio":                   ratio,
        "tolerance_factor":        tolerance_factor,
        "passes":                  passes,
        "status":                  status,
    }


def detect_artificial_scarcity(
    pass_rate: float,
    floor: float = ARTIFICIAL_SCARCITY_PASS_RATE_FLOOR,
    quality_differential: float | None = None,
    quality_threshold: float = ARTIFICIAL_SCARCITY_QUALITY_THRESHOLD,
) -> dict:
    """
    Detect manufactured scarcity through entry barrier analysis.

    Two independent triggers:
    1. Pass rate below floor — no legitimately demanding field sustains this
       without manufactured barriers.
    2. Low quality differential — if measured outcome quality between passers
       and near-misses is negligible, the barrier is not sorting on competency.

    Trigger 1 takes precedence; trigger 2 applies only when trigger 1 is absent.

    Args:
        pass_rate: Fraction of candidates passing certification/entry ∈ [0, 1].
        floor: Pass rate below which artificial scarcity is declared regardless
               of other evidence. Default: 0.30.
        quality_differential: Measured outcome quality difference between passers
               and near-misses, normalized ∈ [0, 1]. None = not available.
        quality_threshold: Minimum quality_differential to justify a low (but
               above-floor) pass rate. Default: 0.20.

    Returns:
        dict with keys:
          "pass_rate"             float
          "floor"                 float
          "quality_differential"  float | None
          "quality_threshold"     float
          "passes"                bool   True = no artificial scarcity detected
          "status"                str    "OK" | "ARTIFICIAL_SCARCITY" | "ARTIFICIAL_SCARCITY_RISK"
          "trigger"               str | None  which check fired; None if OK

    Raises:
        ValueError: If pass_rate or quality_differential is outside [0, 1].

    Reference: Mission Statement §"Anti-gaming safeguard 2 — artificial scarcity
    detection"; Roadmap Track B5.
    """
    if not 0.0 <= pass_rate <= 1.0:
        raise ValueError(f"pass_rate must be in [0, 1], got {pass_rate}")
    if quality_differential is not None and not 0.0 <= quality_differential <= 1.0:
        raise ValueError(f"quality_differential must be in [0, 1], got {quality_differential}")

    if pass_rate < floor:
        status = "ARTIFICIAL_SCARCITY"
        trigger = "pass_rate_below_floor"
    elif quality_differential is not None and quality_differential < quality_threshold:
        status = "ARTIFICIAL_SCARCITY_RISK"
        trigger = "low_quality_differential"
    else:
        status = "OK"
        trigger = None

    return {
        "pass_rate":            pass_rate,
        "floor":                floor,
        "quality_differential": quality_differential,
        "quality_threshold":    quality_threshold,
        "passes":               status == "OK",
        "status":               status,
        "trigger":              trigger,
    }


def tier_expiry_check(
    assigned_epoch: int,
    current_epoch: int,
    interval_years: int = TIER_ASSESSMENT_INTERVAL_YEARS,
) -> dict:
    """
    Enforce sunset reassessment scheduling for tier assignments.

    Every tier assignment has a finite validity window. This function checks
    whether a role's assessment is current or overdue, and returns the
    remaining time or overdue amount.

    Args:
        assigned_epoch: Year (or period) the tier was last assessed.
        current_epoch: Current year (or period).
        interval_years: Maximum years between reassessments. Default: 5.

    Returns:
        dict with keys:
          "assigned_epoch"  int
          "current_epoch"   int
          "interval_years"  int
          "elapsed"         int   years since last assessment
          "remaining"       int   years until due (negative if overdue)
          "expired"         bool
          "status"          str   "CURRENT" | "OVERDUE"

    Raises:
        ValueError: If current_epoch < assigned_epoch.

    Reference: Mission Statement §"Anti-gaming safeguard 3 — sunset mechanism";
    Roadmap Track B5.
    """
    if current_epoch < assigned_epoch:
        raise ValueError(
            f"current_epoch ({current_epoch}) must be >= assigned_epoch ({assigned_epoch})"
        )

    elapsed = current_epoch - assigned_epoch
    remaining = interval_years - elapsed
    expired = elapsed >= interval_years
    status = "OVERDUE" if expired else "CURRENT"

    return {
        "assigned_epoch": assigned_epoch,
        "current_epoch":  current_epoch,
        "interval_years": interval_years,
        "elapsed":        elapsed,
        "remaining":      remaining,
        "expired":        expired,
        "status":         status,
    }


# ---------------------------------------------------------------------------
# Impact Score Decomposition
# ---------------------------------------------------------------------------

def compute_impact_score(
    eoh_reduction_fraction: float,
    domain_coverage: float,
    resilience_contribution: float,
    w_eoh: float = ALPHA_IMPACT_EOH_REDUCTION_WEIGHT,
    w_cov: float = ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT,
    w_res: float = ALPHA_IMPACT_RESILIENCE_WEIGHT,
) -> float:
    """
    Decompose the impact factor I(c) ∈ [0,1] from observable sub-questions.

    Governing equation:
        I(c) = w_eoh · eoh_reduction_fraction
             + w_cov · domain_coverage
             + w_res · resilience_contribution

    Sub-questions:
        eoh_reduction_fraction: fraction of domain EOH one practitioner eliminates
            per hour of labor (e.g. a surgeon addressing 40% of demand = 0.40) ∈ [0,1]
        domain_coverage: fraction of domain EOH breadth this role contributes to
            (e.g. a generalist covering 60% of domain needs = 0.60) ∈ [0,1]
        resilience_contribution: emergency reserve capacity
            (0 = no reserve role, 1 = critical-path emergency responder) ∈ [0,1]

    The result feeds directly into tier_multiplier() as the `impact` argument.
    The default weights sum to 1.0; if custom weights are supplied they must also
    sum to 1.0 (validated here).

    Args:
        eoh_reduction_fraction: Fraction of EOH demand addressed per practitioner-hour ∈ [0,1].
        domain_coverage: Breadth of EOH domain served by this role ∈ [0,1].
        resilience_contribution: Emergency reserve capacity ∈ [0,1].
        w_eoh: Weight for EOH reduction. Default: ALPHA_IMPACT_EOH_REDUCTION_WEIGHT.
        w_cov: Weight for domain coverage. Default: ALPHA_IMPACT_DOMAIN_COVERAGE_WEIGHT.
        w_res: Weight for resilience. Default: ALPHA_IMPACT_RESILIENCE_WEIGHT.

    Returns:
        Impact score I(c) ∈ [0,1].

    Raises:
        ValueError: If any input is outside [0,1] or weights do not sum to 1.0.

    Reference: Mission Statement §"Principle 4" — decomposed impact sub-questions.
    """
    for name, val in [("eoh_reduction_fraction", eoh_reduction_fraction),
                      ("domain_coverage", domain_coverage),
                      ("resilience_contribution", resilience_contribution)]:
        if not 0.0 <= val <= 1.0:
            raise ValueError(f"'{name}' must be in [0, 1], got {val}")

    if abs(w_eoh + w_cov + w_res - 1.0) > 0.001:
        raise ValueError(
            f"Weights must sum to 1.0, got {w_eoh + w_cov + w_res:.4f}"
        )

    return w_eoh * eoh_reduction_fraction + w_cov * domain_coverage + w_res * resilience_contribution


# ---------------------------------------------------------------------------
# Governance Assessment
# ---------------------------------------------------------------------------

class GovernanceInputs(TypedDict, total=False):
    """Governance metadata for a tier assessment. All fields optional."""
    sortition_flag:     bool       # assessors randomly selected from eligible pool
    assessor_count:     int        # number of independent assessors
    irr_score:          float      # inter-rater reliability ∈ [0,1]
    adversarial_review: bool       # external challenge mechanism applied
    review_epoch:       int | None # epoch of last assessment (for sunset clock)
    current_epoch:      int | None # current epoch (for sunset clock)


def assess_tier(
    training: float,
    demand: float,
    scarcity: float,
    impact: float,
    epsilon: float,
    governance: GovernanceInputs | None = None,
) -> dict:
    """
    Full tier assessment: arc-correct multiplier computation + governance validation.

    Combines epoch_alpha_weights(epsilon) → tier_multiplier() with structured
    governance checks against thresholds from data.py. Reuses tier_expiry_check()
    when both review_epoch and current_epoch are provided. Returns a status dict
    following the codebase's "status/warnings/passes" pattern.

    Governance checks performed (when governance inputs are supplied):
    - assessor_count < GOVERNANCE_MIN_ASSESSORS → WARN
    - irr_score < GOVERNANCE_IRR_CRIT_THRESHOLD → CRIT
    - irr_score < GOVERNANCE_IRR_WARN_THRESHOLD → WARN
    - not sortition_flag → WARN
    - sum(alpha_coefficients) > ALPHA_SCALE × 1.10 → WARN (coefficient overshoot)
    - review_epoch provided and tier is OVERDUE (via tier_expiry_check) → WARN

    The overall governance_status is the worst level across all triggered checks.

    Args:
        training: Training requirement ∈ [0, 1].
        demand: EOH demand intensity ∈ [0, 1].
        scarcity: Practitioner scarcity ∈ [0, 1].
        impact: Societal EOH impact ∈ [0, 1].
        epsilon: Automation level [0.0, 0.99] — used to derive alpha_coefficients.
        governance: Optional governance metadata dict (see GovernanceInputs).

    Returns:
        dict with keys:
          "multiplier":         float       — the computed m(c)
          "alpha_coefficients": tuple       — from epoch_alpha_weights(epsilon)
          "governance_status":  str         — "OK" | "WARN" | "CRIT"
          "warnings":           list[str]   — human-readable governance issues
          "passes_governance":  bool        — True iff status != "CRIT"
          "sunset_check":       dict|None   — tier_expiry_check() result if epochs provided
          "inputs":             dict        — echo of all inputs for audit trail

    Reference: Mission Statement §"Governance safeguards" — sortition, IRR, sunset.
    """
    alpha_coefficients = epoch_alpha_weights(epsilon)
    multiplier = tier_multiplier(training, demand, scarcity, impact, alpha_coefficients)

    warnings: list[str] = []
    severity_levels = {"OK": 0, "WARN": 1, "CRIT": 2}
    worst = "OK"
    sunset_check = None

    def _escalate(level: str, message: str) -> None:
        warnings.append(message)
        nonlocal worst
        if severity_levels[level] > severity_levels[worst]:
            worst = level

    if sum(alpha_coefficients) > ALPHA_SCALE * 1.10:
        _escalate("WARN",
            f"alpha_coefficients sum to {sum(alpha_coefficients):.3f}, "
            f"exceeding ALPHA_SCALE × 1.10 = {ALPHA_SCALE * 1.10:.3f}; "
            "cap will clamp but coefficients may be miscalibrated")

    if governance:
        assessor_count = governance.get("assessor_count", GOVERNANCE_MIN_ASSESSORS)
        if assessor_count < GOVERNANCE_MIN_ASSESSORS:
            _escalate("WARN",
                f"assessor_count={assessor_count} < GOVERNANCE_MIN_ASSESSORS="
                f"{GOVERNANCE_MIN_ASSESSORS}")

        irr_score = governance.get("irr_score", 1.0)
        if irr_score < GOVERNANCE_IRR_CRIT_THRESHOLD:
            _escalate("CRIT",
                f"irr_score={irr_score:.2f} < GOVERNANCE_IRR_CRIT_THRESHOLD="
                f"{GOVERNANCE_IRR_CRIT_THRESHOLD}")
        elif irr_score < GOVERNANCE_IRR_WARN_THRESHOLD:
            _escalate("WARN",
                f"irr_score={irr_score:.2f} < GOVERNANCE_IRR_WARN_THRESHOLD="
                f"{GOVERNANCE_IRR_WARN_THRESHOLD}")

        if not governance.get("sortition_flag", True):
            _escalate("WARN", "sortition_flag=False: assessors were not randomly selected")

        review_epoch = governance.get("review_epoch")
        current_epoch = governance.get("current_epoch")
        if review_epoch is not None and current_epoch is not None:
            sunset_check = tier_expiry_check(review_epoch, current_epoch)
            if sunset_check["expired"]:
                _escalate("WARN",
                    f"Tier assessment expired: {sunset_check['elapsed']} years elapsed, "
                    f"interval={sunset_check['interval_years']}")

    return {
        "multiplier":         multiplier,
        "alpha_coefficients": alpha_coefficients,
        "governance_status":  worst,
        "warnings":           warnings,
        "passes_governance":  worst != "CRIT",
        "sunset_check":       sunset_check,
        "inputs": {
            "training":   training,
            "demand":     demand,
            "scarcity":   scarcity,
            "impact":     impact,
            "epsilon":    epsilon,
            "governance": dict(governance) if governance else None,
        },
    }
