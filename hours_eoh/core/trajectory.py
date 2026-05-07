"""
Canonical Trajectory and ε Derivation

Two purposes:

1. **Canonical physical state** — the expected physical state of a civilization
   on the ideal arc at a given automation level ε. Functions that need to test
   behaviour across the full arc call canonical_physical_state(ε) to get
   physically-grounded default inputs rather than passing ε as a God-parameter
   that encodes hidden physical assumptions inside EOH generation functions.

   EOH generation functions take physical state (capital_stock, ecosystem_health,
   knowledge_base_size, monitoring_capability, age_distribution). The canonical
   trajectory provides those values for arc testing and cross-sectional analysis.
   Real simulations diverge from the canonical arc — that divergence is the point
   of modeling diverse trajectories.

2. **compute_epsilon()** — the formal definition of ε as a derived metric:
   ε = machine EOH fulfilled / total EOH collective potential.
   Where total EOH collective potential = total EOH computed with all personal
   EOH on the collective ledger (the fully-recognized reference state). This makes
   ε a true progress score: it reaches 1.0 only when machines handle everything
   AND the collective fully recognizes personal EOH obligations.

   In the current simulation, ε is still an exogenous scenario input (epsilon_delta
   advances it each period). compute_epsilon() reports the derived value for
   transparency and sets up the hook for when machine capacity is modeled
   endogenously.

Mission Statement: §"ε ... the measured degree to which physical entropy
obligations are fulfilled by machines rather than human bodies"; §"Principle 9 —
Every mechanism must express the arc, not just a point on it."
"""

from __future__ import annotations

from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    AGE_GROUPS,
    ELDERLY_EOH_EPSILON_FACTOR,
    CANONICAL_CAPITAL_GROWTH_SLOPE,
    CANONICAL_MONITORING_CAPABILITY_BASE,
    CANONICAL_MONITORING_CAPABILITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE,
    CANONICAL_KNOWLEDGE_COMPLEXITY_EXP,
    CANONICAL_CAPITAL_AGE_DRIFT,
    CANONICAL_ECOSYSTEM_HEALTH_BASE,
    CANONICAL_ECOSYSTEM_HEALTH_DRIFT,
)


# ---------------------------------------------------------------------------
# Canonical age distribution
# ---------------------------------------------------------------------------

def canonical_age_distribution(epsilon: float) -> dict[str, float]:
    """
    Age distribution on the canonical arc at automation level ε.

    Better medicine at higher automation → longer lives → growing elderly fraction.
    The shift is modest (≤5% of the child fraction) and secondary to the dominant
    ε-effect, which is in the human_eoh_share() fulfillment split.

    This function was formerly an anonymous inline calculation inside personal_eoh().
    Now it is explicit so that callers who want ε-adjusted age composition can
    request it, while callers with measured actual demographics pass their own dict.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Dict mapping age group name → fraction of population. Sums to 1.0.

    Reference: Mission Statement §"Personal EOH — the entropy of human bodies";
    §"Humans as capital stock" — aging as capital depreciation.
    """
    dist = {k: v["fraction"] for k, v in AGE_GROUPS.items()}
    elderly_boost = ELDERLY_EOH_EPSILON_FACTOR * epsilon
    if "elderly" in dist and "child" in dist:
        shift = min(elderly_boost * dist["child"], 0.03 * dist["elderly"])
        dist["elderly"] = dist["elderly"] + shift
        dist["child"]   = dist["child"]   - shift
    return dist


# ---------------------------------------------------------------------------
# Canonical physical state
# ---------------------------------------------------------------------------

def canonical_physical_state(epsilon: float) -> dict:
    """
    Physical state of a civilization on the ideal trajectory at automation level ε.

    Returns the expected capital stock, ecosystem health, monitoring capability,
    knowledge base complexity, and age distribution at each point on the arc.
    Used for:
      - Arc testing: test functions at specific ε values without running full simulation
      - Cross-sectional analysis: "what does the fiscal system look like at ε=0.40?"
      - Baseline comparison: measure how far a simulated trajectory has diverged

    These are NOT constraints on what the model can represent. A real simulation
    diverges freely — fast automation with low capital investment, or slow
    automation with rich ecological infrastructure are valid trajectories. The
    canonical arc is the reference against which those trajectories are measured.

    The constants defining this arc are in data.py under the CANONICAL_* prefix.
    To recalibrate the arc, change those constants — not this function.

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        dict: {
          "capital_stock_teh":      float,  — actual current capital stock
          "capital_age_ratio":      float,  — mean asset age across arc
          "ecosystem_health":       float,  — ecosystem state on ideal arc
          "monitoring_capability":  float,  — ecological monitoring capacity
          "knowledge_base_size":    float,  — knowledge complexity (relative, 1.0 = ε=0 reference)
          "knowledge_complexity_per_unit": float, — per-unit maintenance cost factor
          "age_distribution":       dict,   — population age fractions
        }

    Reference: Mission Statement §"Two attractors: ε=0 (subsistence) and ε=1
    (post-scarcity)" — canonical_physical_state anchors each function to the
    physical reality at both extremes.
    """
    eps = max(0.0, min(1.0, epsilon))
    return {
        "capital_stock_teh":     CAPITAL_STOCK_DEFAULT * (1.0 + CANONICAL_CAPITAL_GROWTH_SLOPE * eps),
        "capital_age_ratio":     0.30 + CANONICAL_CAPITAL_AGE_DRIFT * eps,
        "ecosystem_health":      max(0.01, CANONICAL_ECOSYSTEM_HEALTH_BASE + CANONICAL_ECOSYSTEM_HEALTH_DRIFT * eps),
        "monitoring_capability": CANONICAL_MONITORING_CAPABILITY_BASE + CANONICAL_MONITORING_CAPABILITY_SLOPE * eps,
        "knowledge_base_size":   1.0 + CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE * eps,
        "knowledge_complexity_per_unit": 1.0 + (eps ** CANONICAL_KNOWLEDGE_COMPLEXITY_EXP) * CANONICAL_KNOWLEDGE_COMPLEXITY_SLOPE,
        "age_distribution":      canonical_age_distribution(eps),
    }


# ---------------------------------------------------------------------------
# ε derivation
# ---------------------------------------------------------------------------

def compute_epsilon(
    machine_eoh_fulfilled: float,
    total_eoh_collective_potential: float,
) -> float:
    """
    Derive ε from the physical state of EOH fulfillment.

    ε = machine_eoh_fulfilled / total_eoh_collective_potential

    Where total_eoh_collective_potential is the total EOH demand that would exist
    if all personal EOH were on the collective ledger — the fully-recognized
    reference state. This normalization makes ε a true progress score:
      - Numerator: what machines actually handled this period
      - Denominator: what the full collective obligation would be at peak recognition

    ε reaches 1.0 only when machines handle everything AND the collective fully
    recognizes personal EOH obligations. A civilization that has high automation
    but has not registered personal EOH still has ε < 1.0 — it has not completed
    the transition.

    In the current simulation, ε is an exogenous scenario parameter (epsilon_delta
    advances it each period) and machine_eoh_fulfilled is derived from it:
    machine_eoh = total_eoh × ε. So compute_epsilon() returns the input ε — it is
    currently circular. Its value is as the explicit formula and architecture hook
    for when machine capacity is modeled endogenously: once a machine_capacity
    sub-model tracks actual automated fulfillment, this function produces a
    non-trivial ε that emerges from the physical state rather than being assumed.

    Args:
        machine_eoh_fulfilled: EOH handled by machines this period (hours/year).
        total_eoh_collective_potential: Total EOH demand with all personal EOH
            on the collective ledger. Typically = total_eoh()["total"] since
            total_eoh() returns raw physical demand independent of registration.

    Returns:
        Derived ε ∈ [0.0, 1.0].

    Reference: Mission Statement §"ε ... the measured degree to which physical
    entropy obligations are fulfilled by machines rather than human bodies";
    §"the civilization's measured progress score toward post-scarcity."
    """
    if total_eoh_collective_potential <= 0.0:
        return 0.0
    return min(1.0, max(0.0, machine_eoh_fulfilled / total_eoh_collective_potential))


# ---------------------------------------------------------------------------
# Canonical capital stock helper (formerly effective_capital_from_stock)
# ---------------------------------------------------------------------------

def effective_capital_from_epsilon(capital_stock_at_eps0: float, epsilon: float) -> float:
    """
    Canonical capital stock at automation level ε from the ε=0 baseline.

    Equivalent to canonical_physical_state(ε)["capital_stock_teh"] scaled to
    a custom ε=0 baseline rather than CAPITAL_STOCK_DEFAULT.

    Use this when calling infrastructure_eoh() in a cross-sectional context
    where you have a baseline capital stock and want the canonical-trajectory
    value at a given ε — rather than the simulation-tracked actual capital stock.

    Args:
        capital_stock_at_eps0: Capital stock at ε=0 (TEH).
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Canonical capital stock in TEH at this automation level.

    Reference: Mission Statement §"Infrastructure EOH — growing capital stock
    as ε rises."
    """
    return capital_stock_at_eps0 * (1.0 + CANONICAL_CAPITAL_GROWTH_SLOPE * epsilon)
