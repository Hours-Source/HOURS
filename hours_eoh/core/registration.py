"""
Registration Boundary Functions

Model the progressive admission of labor categories to the collective ledger.
The collective decides which entropy obligations it recognizes; recognition
is what makes labor economic. Only registered EOH fulfillment creates TEH.

Three labor categories, each with different registration trajectories:
  - Production: admitted early, near-complete by ε=0.20
  - Stewardship: rises through mid-automation as monitoring capacity develops
  - Care: follows a sigmoid driven by collective demand for human capital quality

**ε=0 calibration (open design question — see min3 in design_gaps_review.md)**:
ε=0 is subsistence per the mission statement — "the formal monetary economy is
small," "personal EOH on-ledger is near-zero," "TEH barely circulates." The
current non-personal baselines (production ~70%, stewardship ~20%) imply a
significant degree of collective labor organization at subsistence, which requires
physical justification. Either lower these baselines toward 10–15% to reflect a
truly minimal collective economy, or document the physical argument for why ~70%
of production labor is collectively organized in a near-zero-automation civilization
(e.g., trade guilds, organized agriculture). This is a design decision, not
merely a terminology choice.

Mission Statement: §"The registration boundary", §"Collective demand drives
care registration", §"Two attractors" (ε=0 = subsistence, ε=1 = post-scarcity)
"""

from __future__ import annotations
import math


# ---------------------------------------------------------------------------
# Registration sigmoid calibration constants
# ---------------------------------------------------------------------------
_PROD_REG_BASE:         float = 0.15   # production floor: ~25% at ε=0 with sigmoid contribution.
# Physical justification (min3 resolved): At ε=0 (subsistence), the collective
# ledger is minimal. The mission statement is explicit — "the formal monetary
# economy is small," "TEH barely circulates." Organized trade, fishing guilds,
# and grain accounting exist in pre-industrial societies, but these represent
# a minority of total production labor: most food production, foraging, and
# shelter construction is household-scale and off-ledger. With the sigmoid
# contribution at ε=0 (~0.10×0.84 ≈ 8%), total production registration at
# ε=0 ≈ 25% — enough to represent organized market towns and common-pool
# resource accounting without claiming that 70% of subsistence production is
# formally tracked. Production is still the first domain admitted and reaches
# near-full registration by ε=0.25–0.30 (early automation). The old 70% base
# conflated any collective coordination with formal ledger registration.
_PROD_REG_GROWTH:       float = 0.84   # additional share to gain (total → 0.99)
_PROD_REG_SIGMOID_RATE: float = 20.0   # fast: near-complete by ε=0.25
_PROD_REG_INFLECTION:   float = 0.10   # ε at which production registration rises fastest

_STEW_REG_BASE:         float = 0.05   # stewardship floor: ~7% at ε=0 with sigmoid contribution.
# Physical justification: at ε=0, built infrastructure is minimal and communal
# maintenance (shared wells, paths) accounts for only a small fraction of labor.
# Rate raised from 6.0 to 10.0 so sigmoid(0) ≈ 0.018 — keeping the ε=0 value
# near the floor rather than contributing a spurious 8% baseline.
_STEW_REG_GROWTH:       float = 0.90   # additional share to gain (total → 0.95)
_STEW_REG_SIGMOID_RATE: float = 10.0   # steeper than production; sigmoid(0) ≈ 0.018
_STEW_REG_INFLECTION:   float = 0.40   # ε at which stewardship registration rises fastest

# Personal EOH registration constants (R1)
# At ε=0: near-zero (all personal needs met privately). At ε=1: near full
# (collective capital systems handle essentially all personal EOH).
# Inflection at 0.65 because capital systems must be sufficiently mature
# (mid-to-late automation) before they can reliably fulfill personal EOH at scale.
_PERS_REG_START:        float = 0.0    # no collective personal EOH fulfillment at ε=0
_PERS_REG_SATURATION:   float = 0.95   # some personal EOH always remains private (grief, intimacy)
_PERS_REG_RATE:         float = 7.0    # moderate steepness — slower than care, faster than stewardship
_PERS_REG_INFLECTION:   float = 0.65   # ε at which personal registration rises fastest

# Knowledge EOH registration constants (M3)
# Knowledge outputs lack physical indicators — harder to verify than infrastructure
# (you can inspect a bridge; you cannot easily inspect a research insight).
# Inflection at ε=0.70: formal verification infrastructure (peer review, credentialing,
# automated audit) requires mature automation before it can operate at scale.
# Saturation at 0.80: some knowledge work (tacit skill, judgment, creative insight)
# is never fully admissible to the collective ledger regardless of automation level.
_KNOW_REG_BASE:        float = 0.0    # no formal knowledge verification at subsistence
_KNOW_REG_SATURATION:  float = 0.80   # never fully verified — intangible outputs
_KNOW_REG_RATE:        float = 5.0    # slower than care — harder to verify than care labor
_KNOW_REG_INFLECTION:  float = 0.70   # requires mature automation for verification infrastructure

# Labor category weight model constants
_LABOR_PROD_BASE:    float = 0.45   # production share at ε=0
_LABOR_PROD_SLOPE:   float = 0.45   # production share decline rate with ε
_LABOR_CARE_BASE:    float = 0.30   # care share at ε=0
_LABOR_CARE_GROWTH:  float = 0.60   # care share growth amplitude
_LABOR_CARE_EXPONENT: float = 1.5   # care growth shape: concave-up (slow then fast)
_LABOR_CARE_MAX:     float = 0.85   # care share ceiling
_LABOR_MIN_FLOOR:    float = 0.05   # minimum share for any labor category


# ---------------------------------------------------------------------------
# Care Registration (sigmoid)
# ---------------------------------------------------------------------------

def care_registration_share(
    epsilon: float,
    start_share: float = 0.05,
    inflection: float = 0.45,
    rate: float = 8.0,
    saturation: float = 0.95,
) -> float:
    """
    Fraction of care EOH admitted to the collective ledger at automation level ε.

    Care labor (raising children, tending elders, healing, mentoring) was always
    happening but was unregistered — a private zero event. As automation increases
    systemic complexity, the collective's stake in human capital quality rises,
    driving progressive admission along a sigmoid.

    Sigmoid shape (from Mission Statement):
    - Slow onset at low ε: subsistence communities need hands, not credentials
    - Rapid mid-range acceleration: complex systems demand quality human capital
    - Saturation well before ε=1.0: full registration required before post-scarcity

    At ε=0.40 (current equilibrium): admission is rising but not yet rapid.
    At ε=0.90 (near-post-scarcity): care broadly registered and compensated.

    Args:
        epsilon: Automation level [0.0, 0.99].
        start_share: Minimum registration even at ε=0 (formal education,
                     public health are admitted early). Default: 0.05.
        inflection: ε at which the sigmoid is steepest (fastest admission).
                    Default: 0.45.
        rate: Steepness of the sigmoid. Higher → faster transition. Default: 8.0.
        saturation: Maximum registration asymptote. Default: 0.95.

    Returns:
        Care registration share ∈ [start_share, saturation]. Monotonically
        increasing with ε.

    Reference: Mission Statement §"The precise start, inflection, and saturation
    points of this sigmoid require further modeling, but the shape is clear."
    """
    # Logistic sigmoid centered at inflection point
    sigmoid = 1.0 / (1.0 + math.exp(-rate * (epsilon - inflection)))
    # Scale from start_share to saturation
    return start_share + (saturation - start_share) * sigmoid


# ---------------------------------------------------------------------------
# Production Registration
# ---------------------------------------------------------------------------

def production_registration_share(epsilon: float) -> float:
    """
    Fraction of production EOH registered in the collective ledger.

    Production labor (making goods, building infrastructure) is the most
    legible form of entropy resistance and the first admitted to the ledger.
    Most collective economies start here. Near-full registration by ε=0.20.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Production registration share ∈ [0.15, 0.99]. Monotonically increasing.
        Floor ≈ 0.25 at ε=0 (subsistence); near-complete by ε=0.20.

    Reference: Mission Statement §"The production economy was the first layer
    admitted to the ledger because production labor is the easiest to verify."
    """
    sigmoid = 1.0 / (1.0 + math.exp(-_PROD_REG_SIGMOID_RATE * (epsilon - _PROD_REG_INFLECTION)))
    return _PROD_REG_BASE + _PROD_REG_GROWTH * sigmoid


# ---------------------------------------------------------------------------
# Stewardship Registration
# ---------------------------------------------------------------------------

def stewardship_registration_share(epsilon: float) -> float:
    """
    Fraction of stewardship EOH registered in the collective ledger.

    Stewardship labor (maintaining machines, infrastructure, ecological systems)
    becomes countable as monitoring and assessment systems develop. The
    difficulty is verification — unlike goods produced, maintenance outcomes
    require specialized inspection. Registration rises through mid-automation.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Stewardship registration share ∈ [0.05, 0.95]. Monotonically increasing.
        Floor ≈ 0.07 at ε=0; rises through mid-automation to near-saturation by ε=0.90.

    Reference: Mission Statement §"Stewardship labor becomes countable as
    monitoring and assessment systems develop."
    """
    sigmoid = 1.0 / (1.0 + math.exp(-_STEW_REG_SIGMOID_RATE * (epsilon - _STEW_REG_INFLECTION)))
    return _STEW_REG_BASE + _STEW_REG_GROWTH * sigmoid


# ---------------------------------------------------------------------------
# Personal EOH Registration (R1)
# ---------------------------------------------------------------------------

def personal_eoh_registration_share(
    epsilon: float,
    start_share: float = _PERS_REG_START,
    inflection: float = _PERS_REG_INFLECTION,
    rate: float = _PERS_REG_RATE,
    saturation: float = _PERS_REG_SATURATION,
) -> float:
    """
    Fraction of personal EOH demand currently on the collective ledger.

    This is a DEMAND registration boundary, distinct from the labor
    registration functions (care, production, stewardship), which describe
    what fraction of fulfillment labor is admitted. This function answers:
    "what fraction of the population's personal biological obligations is
    the collective formally accountable for?"

    At ε=0: essentially zero. Personal needs (food, shelter, healthcare)
    are met privately or through informal community — the collective ledger
    does not see them. Only on-ledger personal EOH drives terminal TEH
    destruction (D3); off-ledger fulfillment terminates outside the system.

    At ε→1: near full. Automated capital systems (food production, housing,
    medical) handle personal EOH at scale. The collective recognizes and
    finances these obligations through the fiscal system.

    Inflection at ε=0.65: capital systems must be sufficiently mature and
    deployed before they can reliably fulfill personal EOH. This occurs
    after the mid-automation transition, when stewardship infrastructure
    is well-established.

    Args:
        epsilon: Automation level [0.0, 0.99].
        start_share: Registration floor at ε=0. Default: 0.0 (fully private).
        inflection: ε at which the sigmoid is steepest. Default: 0.65.
        rate: Sigmoid steepness. Higher → faster transition. Default: 7.0.
        saturation: Maximum registration asymptote. Default: 0.95.
                    Some personal EOH (grief, intimacy, autonomous care)
                    remains private regardless of automation level.

    Returns:
        Personal EOH demand registration share ∈ [start_share, saturation].
        Monotonically non-decreasing with ε.

    Reference: Design review §"R1 — Personal EOH Registration Boundary";
    Mission Statement §"at ε=0, all personal EOH is off-ledger; at ε=1,
    all personal EOH is on-ledger."
    """
    sigmoid = 1.0 / (1.0 + math.exp(-rate * (epsilon - inflection)))
    return start_share + (saturation - start_share) * sigmoid


# ---------------------------------------------------------------------------
# Knowledge EOH Registration (M3)
# ---------------------------------------------------------------------------

def knowledge_eoh_registration_share(epsilon: float) -> float:
    """
    Fraction of knowledge EOH admitted to the collective ledger at automation level ε.

    Knowledge labor differs from care and stewardship in a fundamental way:
    outputs are intangible and verification is hard. A bridge inspection can
    confirm whether maintenance labor was effective; a research contribution,
    a curriculum, or a diagnostic judgment cannot be as easily audited. This
    makes collective admission slower and less complete than care.

    Inflection at ε=0.70: formal verification infrastructure (automated peer
    review, credentialing systems, AI-assisted audit) must be mature before
    the collective can reliably recognize knowledge labor at scale. This occurs
    late in the automation arc — after stewardship (0.40) and personal EOH (0.65)
    registration transitions.

    Saturation at 0.80 (vs. care's 0.95): some knowledge work — tacit skill,
    judgment under uncertainty, creative insight — is never fully admissible.
    The collective can recognize knowledge products but cannot always verify
    the labor behind them.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Knowledge EOH demand registration share ∈ [0.0, 0.80].
        Monotonically non-decreasing with ε.

    Reference: Design review §"M3 — Knowledge EOH registration not modeled";
    Mission Statement §"at ε=0.99, knowledge labor is the dominant remaining
    human domain."
    """
    epsilon = max(0.0, min(1.0, epsilon))
    sigmoid = 1.0 / (1.0 + math.exp(-_KNOW_REG_RATE * (epsilon - _KNOW_REG_INFLECTION)))
    return _KNOW_REG_BASE + (_KNOW_REG_SATURATION - _KNOW_REG_BASE) * sigmoid


# ---------------------------------------------------------------------------
# Total Registration Share (labor categories)
# ---------------------------------------------------------------------------

def total_registration_share(
    epsilon: float,
    care_weight: float | None = None,
    production_weight: float | None = None,
    stewardship_weight: float | None = None,
    care_params: dict | None = None,
    knowledge_weight: float | None = None,
) -> float:
    """
    Weighted composite registration share across all labor categories.

    Combines care, production, and stewardship shares, weighted by their
    fraction of total human EOH fulfillment at this automation level.

    By default, weights are computed dynamically from labor_category_weights(ε)
    so they correctly reflect the shifting labor composition: production shrinks
    toward zero at high ε, care grows to dominate, stewardship peaks mid-arc.
    Using fixed ε=0.40 weights at high ε would bias registration toward
    production even after it has mostly vanished, undercounting TEH creation.

    Pass explicit care_weight/production_weight/stewardship_weight to override
    (must sum to 1.0). Useful for sensitivity analysis or fixed-composition
    calibration scenarios.

    Args:
        epsilon: Automation level [0.0, 0.99].
        care_weight: Fraction of human EOH that is care labor. Default: dynamic.
        production_weight: Fraction of human EOH that is production labor.
        stewardship_weight: Fraction of human EOH that is stewardship labor.
        care_params: Optional dict of care sigmoid parameters to override defaults.
        knowledge_weight: Fraction of human EOH that is knowledge labor. When
            provided, all four weights are used; they are re-normalized so the
            composite always sums correctly. Default: None (knowledge excluded,
            preserving the 3-category backward-compatible behavior).

    Returns:
        Composite registration share ∈ [0.0, 1.0].

    Raises:
        ValueError: If explicit weights are provided but do not sum to 1.0.

    Reference: Mission Statement §"The Three Economies" — care, production,
    stewardship layers shift in relative proportion as automation progresses.
    """
    # Use ε-dependent weights unless all three are explicitly overridden
    if care_weight is None or production_weight is None or stewardship_weight is None:
        weights = labor_category_weights(epsilon)
        care_weight        = weights["care"]
        production_weight  = weights["production"]
        stewardship_weight = weights["stewardship"]
    else:
        total_weight = care_weight + production_weight + stewardship_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(
                f"Labor category weights must sum to 1.0, got {total_weight:.4f}"
            )

    c_params = care_params or {}
    c_share = care_registration_share(epsilon, **c_params)
    p_share = production_registration_share(epsilon)
    s_share = stewardship_registration_share(epsilon)

    if knowledge_weight is not None:
        k_share = knowledge_eoh_registration_share(epsilon)
        total_w = care_weight + production_weight + stewardship_weight + knowledge_weight
        return (care_weight * c_share + production_weight * p_share
                + stewardship_weight * s_share + knowledge_weight * k_share) / total_w

    return (care_weight * c_share
            + production_weight * p_share
            + stewardship_weight * s_share)


# ---------------------------------------------------------------------------
# Labor Category Weights (ε-dependent)
# ---------------------------------------------------------------------------

def labor_category_weights(epsilon: float) -> dict[str, float]:
    """
    Approximate fraction of human EOH in each labor category at automation level ε.

    As automation rises:
    - Production labor shrinks (machines handle more production)
    - Stewardship labor grows (more capital to maintain)
    - Care labor grows (higher demand for human capital quality)

    These weights shift continuously — no discrete switch between economic layers.
    At ε=0.99, care is dominant; production is near-zero (all automated).

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        dict with keys: care, production, stewardship (summing to 1.0).

    Reference: Mission Statement §"Principle 7 — Every mechanism must have a
    graceful degradation path" — "no mechanism should require a discrete switch."
    """
    # Production shrinks with automation
    prod = max(_LABOR_MIN_FLOOR, _LABOR_PROD_BASE - _LABOR_PROD_SLOPE * epsilon)

    # Care grows — but slowly at first (concave-up power function)
    care_raw = _LABOR_CARE_BASE + _LABOR_CARE_GROWTH * (epsilon ** _LABOR_CARE_EXPONENT)
    care = min(care_raw, _LABOR_CARE_MAX)

    # Stewardship fills the remainder, peaking in mid-automation
    stew = max(_LABOR_MIN_FLOOR, 1.0 - prod - care)

    # Normalize to sum to exactly 1.0
    total = prod + care + stew
    return {
        "production":   prod / total,
        "care":         care / total,
        "stewardship":  stew / total,
    }


# ---------------------------------------------------------------------------
# Registration trajectory bounds validator
# ---------------------------------------------------------------------------

def validate_registration_trajectory(
    epsilon_sequence: list[float],
    care_params: dict | None = None,
    tolerance: float = 1e-6,
) -> dict:
    """
    Validate that a registration trajectory is monotone and physically achievable.

    Checks three invariants along the given ε path:
    1. Care registration is monotonically non-decreasing (sigmoid guarantee).
    2. Production registration is monotonically non-decreasing.
    3. Composite total_registration_share is monotonically non-decreasing.

    Any violation means the trajectory implies an impossible reversal of
    collective admission — the ledger cannot un-admit labor once recognized.

    Args:
        epsilon_sequence: Ordered list of ε values representing the path.
                          Need not be evenly spaced; any order is accepted
                          (violations flagged regardless of ordering).
        care_params: Optional care sigmoid parameter overrides.
        tolerance: Allowed backward step before flagging a violation (floating-point).

    Returns:
        dict: {
          "valid":           bool,    (True iff no violations found)
          "violations":      list[dict],  (each: {epsilon_from, epsilon_to, metric, value_from, value_to})
          "care_range":      [float, float],   (min, max care share across path)
          "production_range": [float, float],
          "total_range":     [float, float],
          "n_checked":       int,
        }

    Reference: Mission Statement §"The collective decides which obligations it
    recognizes — once recognized, that recognition cannot be revoked without
    a formal collective decision (not modeled here)."
    """
    c_params = care_params or {}
    violations: list[dict] = []

    prev: dict[str, float] = {}
    all_care, all_prod, all_total = [], [], []

    for eps in epsilon_sequence:
        care  = care_registration_share(eps, **c_params)
        prod  = production_registration_share(eps)
        total = total_registration_share(eps, care_params=care_params)

        all_care.append(care)
        all_prod.append(prod)
        all_total.append(total)

        if prev:
            for name, val, prev_val in (
                ("care",       care,  prev["care"]),
                ("production", prod,  prev["production"]),
                ("total",      total, prev["total"]),
            ):
                if val < prev_val - tolerance:
                    violations.append({
                        "epsilon_from": prev["eps"],
                        "epsilon_to":   eps,
                        "metric":       name,
                        "value_from":   prev_val,
                        "value_to":     val,
                        "decline":      prev_val - val,
                    })

        prev = {"eps": eps, "care": care, "production": prod, "total": total}

    return {
        "valid":            len(violations) == 0,
        "violations":       violations,
        "care_range":       [min(all_care),  max(all_care)]  if all_care  else [0.0, 0.0],
        "production_range": [min(all_prod),  max(all_prod)]  if all_prod  else [0.0, 0.0],
        "total_range":      [min(all_total), max(all_total)] if all_total else [0.0, 0.0],
        "n_checked":        len(epsilon_sequence),
    }
