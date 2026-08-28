"""
Price Dynamics — Floor Prices

In the EOH framework, the TEH ledger sets the **floor price** of a good or
service: the minimum price implied by its human labor content. Market discovery
can produce prices above this floor (via `floor_price(..., market_premium=X>`),
but the floor itself is determined by the Comprehensive Price Identity, not by
supply and demand.

The floor price of a good equals its human labor content × mean multiplier.
As automation rises, the human labor content falls, so floor prices fall
automatically. This is a floor guarantee, not a claim that all prices converge
to it — see reconciliation §3 (price-as-floor reframing) and §9-item-3.

This creates Principle 5 (floor purchasing power rises with automation) as a
mathematical consequence: if the sufficiency floor is constant in nominal TEH
and floor prices fall, the floor purchases more. No policy intervention required.

The price basket contains goods AND services. Goods floor prices fall steeply
with automation (production is the first thing automated). Service floor prices
fall more slowly (care, knowledge, judgment resist full automation longer).

**Theory flag (reconciliation §3)**: the functions in this module compute
*floor prices*, not universal prices. The term "price" in existing docstrings
and the arc CLI refers to the floor. A `market_premium` seam is exposed via
`floor_price()` for discovered premiums above the floor. The reframing of
basket_price() as floor_price() is pending author sign-off (Workstream C PR).

Mission Statement: §"Principle 5 — The floor rises with automation; it never
falls"; §"TEH-denominated prices fall as automation handles more EOH, so the
same nominal TEH buys more"; §"teh_price" in Phase 3.2 requirements.
"""

from __future__ import annotations
import math

from hours_eoh.data import (
    MEANINGFUL_ACTIVITY_TEH_BASE, BASKET_EOH_CONTENT, MEAN_MULTIPLIER_REFERENCE,
    BASKET_GOODS_WEIGHT, BASKET_SERVICES_WEIGHT,
    GOODS_PRICE_FLOOR, SERVICES_PRICE_FLOOR, SERVICES_PRICE_DECLINE_EXPONENT,
)


# ---------------------------------------------------------------------------
# Basket composition: what the sufficiency basket contains
# ---------------------------------------------------------------------------

# Fraction of the sufficiency basket that is goods vs. services
# All five basket/price constants MIGRATED TO data.py 2026-08-28. They were
# shadow constants — untagged, invisible to the provenance gate, and a +7% move
# of any of them failed no test. Goods: food, clothing, shelter materials,
# manufactured items. Services: healthcare, care, education, local skilled
# services.


# ---------------------------------------------------------------------------
# Good Price (single item)
# ---------------------------------------------------------------------------

def domain_scarcity_multiplier(
    eoh_demand: float,
    fulfillment_capacity: float,
    max_scarcity: float = 2.0,
) -> float:
    """
    Price scarcity multiplier when EOH demand outpaces fulfillment capacity.

    In the EOH framework, floor prices reflect labor content; market discovery
    sets premiums above the floor (reconciliation §3). When a domain's EOH
    demand chronically exceeds the workforce's ability to fulfill it, a
    scarcity signal is appropriate — prices rise to ration consumption
    and redirect labor toward the shortfall.

    At balance (demand ≤ capacity): multiplier = 1.0 (no scarcity signal).
    At 2× overdemand (demand = 2× capacity): multiplier = max_scarcity.
    Scales linearly between these extremes.

    Args:
        eoh_demand: Total EOH demanded in this domain (hours/year).
        fulfillment_capacity: Total fulfillment capacity available (hours/year).
        max_scarcity: Maximum multiplier at 2× overdemand. Default: 2.0.

    Returns:
        Scarcity multiplier ≥ 1.0. Pass as scarcity_factor to teh_price().

    Reference: Mission Statement §"Prices tell you how much human life went
    into making something" — under scarcity, the signal must be amplified to
    direct labor toward unfulfilled obligations.
    """
    if fulfillment_capacity <= 0.0 or eoh_demand <= 0.0:
        return 1.0
    ratio = eoh_demand / fulfillment_capacity
    if ratio <= 1.0:
        return 1.0
    # Linear from 1.0 at ratio=1 to max_scarcity at ratio=2; capped above 2
    return 1.0 + (max_scarcity - 1.0) * min(ratio - 1.0, 1.0)


def teh_price(
    human_labor_hours_at_eps0: float,
    epsilon: float = 0.40,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    goods_price_floor: float = GOODS_PRICE_FLOOR,
    scarcity_factor: float = 1.0,
) -> float:
    """
    Price of a good in TEH at a given automation level.

    Price = human_labor_content × mean_multiplier

    Where human_labor_content = labor hours needed to produce the good,
    which falls with automation. At ε=0: all labor is human. At ε=0.90:
    90% is automated, so 10% of original hours remain human-labor.

    The price floor prevents prices from reaching exactly zero even at full
    automation — some irreducible human contribution (logistics, quality
    assurance, final-mile delivery) persists.

    Args:
        human_labor_hours_at_eps0: Human labor hours needed to produce this
                                   good at ε=0 (no automation).
        epsilon: Automation level. Scales down human labor content.
        mean_multiplier: Mean multiplier for the workers who produce this good.
        goods_price_floor: Minimum fraction of base price (irreducible labor).
        scarcity_factor: Optional multiplier from domain_scarcity_multiplier().
                         Default 1.0 (no scarcity signal). Values > 1.0 indicate
                         EOH demand exceeds fulfillment capacity in this domain.

    Returns:
        TEH price of the good at this automation level.

    This computes the **floor price** — the minimum price guaranteed by the
    TEH ledger. Market discovery above this floor is not modeled here.

    Example: A loaf of bread requires 0.1 hours of human labor at ε=0 with
    mean_multiplier=2.0 → floor price = 0.2 TEH. At ε=0.80: floor price = 0.2 × 0.20
    = 0.04 TEH (clipped to floor if needed).

    Reference: Mission Statement §"Prices tell you how much human life went
    into making something"; §"Phase 3.2 — teh_price(good, human_labor_content, ε)";
    reconciliation §3 (price-as-floor reframing).
    """
    # Human labor content at this ε
    human_fraction = max(1.0 - epsilon, goods_price_floor)
    human_hours    = human_labor_hours_at_eps0 * human_fraction
    return human_hours * mean_multiplier * scarcity_factor


def teh_price_trajectory(
    human_labor_hours_at_eps0: float,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    n_points: int = 20,
) -> list[dict]:
    """
    Price trajectory for a good across the full automation range.

    Args:
        human_labor_hours_at_eps0: Base labor content.
        mean_multiplier: Mean worker multiplier.
        n_points: Number of ε points (0.0 to 0.99).

    Returns:
        List of {"epsilon": float, "price_teh": float, "relative_to_eps0": float}.
    """
    base_price = teh_price(human_labor_hours_at_eps0, 0.0, mean_multiplier)
    result = []
    for i in range(n_points + 1):
        eps = i * 0.99 / n_points
        price = teh_price(human_labor_hours_at_eps0, eps, mean_multiplier)
        result.append({
            "epsilon":         eps,
            "price_teh":       price,
            "relative_to_eps0": price / max(base_price, 1e-10),
        })
    return result


# ---------------------------------------------------------------------------
# Basket Price
# ---------------------------------------------------------------------------

def basket_price(
    epsilon: float,
    baseline_cost_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    goods_weight: float = BASKET_GOODS_WEIGHT,
    services_weight: float = BASKET_SERVICES_WEIGHT,
    goods_price_floor: float = GOODS_PRICE_FLOOR,
    services_price_floor: float = SERVICES_PRICE_FLOOR,
) -> float:
    """
    TEH cost of the sufficiency basket at automation level ε.

    The basket contains both goods (60%) and services (40%). Goods prices fall
    steeply with automation (production is automated first). Services prices fall
    more slowly because care, knowledge, and judgment resist full automation.

    Governing equations:

        goods_ratio     = max(1 − ε × (1 − goods_floor), goods_floor)     [0.05, 1.0]
        services_ratio  = services_floor + (1 − services_floor) × (1−ε)^0.35  [0.2, 1.0]
        basket_price    = baseline × (goods_weight × goods_ratio
                                    + services_weight × services_ratio)

    Five governing parameters (from prices.py constants):
        baseline_cost_teh   = 120.0 TEH  (basket cost at ε=0 = MEANINGFUL_ACTIVITY_TEH_BASE)
        goods_weight        = 0.60
        services_weight     = 0.40
        goods_price_floor   = 0.05  (goods cannot fall below 5% of ε=0 price)
        services_price_floor= 0.20  (services floor at 20% — labor-intensive minimum)

    As ε rises from 0 to 1, basket_price falls monotonically — the mathematical
    basis for Principle 5 (sufficiency purchasing power rises with automation).

    Worked trajectory:
        ε=0.00: basket_price = 120.0 TEH/yr  (full human-labor cost)
        ε=0.40: basket_price =  86.4 TEH/yr  (−28% from automation gains)
        ε=0.90: basket_price =  37.2 TEH/yr  (−69% as services also fall)

    Args:
        epsilon: Automation level [0.0, 0.99].
        baseline_cost_teh: Basket cost at ε=0 (TEH/year). Default: 120.0.
        goods_weight: Fraction of basket that is goods. Default: 0.60.
        services_weight: Fraction of basket that is services. Default: 0.40.
        goods_price_floor: Minimum goods price ratio (floor). Default: 0.05.
        services_price_floor: Minimum services price ratio. Default: 0.20.

    Returns:
        TEH cost of the sufficiency basket (TEH/yr). Always positive; bounded
        in (baseline_cost_teh × weighted_floor, baseline_cost_teh].

    This function computes the **floor price** of the basket — the minimum
    guaranteed by the TEH ledger. Use `floor_price()` to add a market_premium
    above the floor. See reconciliation §3 (price-as-floor reframing).

    Reference: Mission Statement §"As automation reduces the human labor
    content of the Sufficiency basket, the Guarantee's purchasing power
    increases automatically."
    """
    if abs(goods_weight + services_weight - 1.0) > 0.001:
        raise ValueError(
            f"goods_weight + services_weight must equal 1.0, "
            f"got {goods_weight + services_weight:.4f}"
        )

    # Goods: price declines nearly linearly, floored at goods_price_floor
    goods_price_ratio = max(1.0 - epsilon * (1.0 - goods_price_floor), goods_price_floor)

    # Services: price declines slower (power < 1 → concave decline)
    # At ε=0: 1.0. At ε=0.99: services_price_floor.
    services_price_ratio = services_price_floor + (1.0 - services_price_floor) * ((1.0 - epsilon) ** SERVICES_PRICE_DECLINE_EXPONENT)

    basket_ratio = goods_weight * goods_price_ratio + services_weight * services_price_ratio
    return baseline_cost_teh * basket_ratio


def floor_price(
    epsilon: float,
    market_premium: float = 0.0,
    baseline_cost_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    goods_weight: float = BASKET_GOODS_WEIGHT,
    services_weight: float = BASKET_SERVICES_WEIGHT,
    goods_price_floor: float = GOODS_PRICE_FLOOR,
    services_price_floor: float = SERVICES_PRICE_FLOOR,
) -> float:
    """
    Floor price of the sufficiency basket with an optional market_premium above it.

    Governing equation:
        floor_price(ε) = basket_price(ε) + market_premium

    This is the primary entry point for the price-as-floor reframing
    (reconciliation §3). The TEH ledger guarantees basket_price(ε) as the
    floor — the price that labor content alone justifies. Any market discovery
    above the floor is expressed as market_premium (TEH/yr, absolute).

    At market_premium=0.0 (default), this is identical to basket_price().
    Behavior is therefore unchanged from the pre-refactor code at the default,
    satisfying the Workstream C acceptance criterion.

    As ε rises from 0 to 1, the floor falls monotonically (Principle 5) while
    market_premium is a caller-supplied observable — it may rise, fall, or vary
    independently of the automation level.

    Args:
        epsilon: Automation level [0.0, 0.99].
        market_premium: Discovered price above the floor (TEH/yr). Default 0.0.
                        Positive values represent premiums from scarcity, quality,
                        or collective-level price discovery. The floor guarantee
                        is unaffected by this parameter.
        baseline_cost_teh: Basket floor cost at ε=0 (TEH/year). Default: 120.0.
        goods_weight: Fraction of basket that is goods. Default: 0.60.
        services_weight: Fraction of basket that is services. Default: 0.40.
        goods_price_floor: Minimum goods floor ratio. Default: 0.05.
        services_price_floor: Minimum services floor ratio. Default: 0.20.

    Returns:
        Total basket price (TEH/yr) = floor + premium. Equal to basket_price()
        when market_premium=0.0.

    Reference: reconciliation §3 (price-as-floor reframing) and §9-item-3.
    Author sign-off required before merging this reframing — see Workstream C PR.
    """
    if market_premium < 0.0:
        raise ValueError(f"market_premium must be ≥ 0.0, got {market_premium}")
    return basket_price(
        epsilon=epsilon,
        baseline_cost_teh=baseline_cost_teh,
        goods_weight=goods_weight,
        services_weight=services_weight,
        goods_price_floor=goods_price_floor,
        services_price_floor=services_price_floor,
    ) + market_premium


# ---------------------------------------------------------------------------
# Purchasing Power
# ---------------------------------------------------------------------------

def purchasing_power(
    teh_amount: float,
    epsilon: float = 0.40,
    baseline_basket_cost: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    goods_weight: float = BASKET_GOODS_WEIGHT,
    services_weight: float = BASKET_SERVICES_WEIGHT,
) -> dict:
    """
    What a given amount of TEH can buy at automation level ε.

    Purchasing power is measured in "basket equivalents" — how many
    sufficiency baskets the given TEH amount can purchase. As ε rises,
    basket prices fall, so the same nominal TEH buys more baskets.

    Args:
        teh_amount: Amount of TEH to evaluate.
        epsilon: Automation level.
        baseline_basket_cost: Cost of one basket at ε=0.
        goods_weight: Fraction of basket that is goods.
        services_weight: Fraction of basket that is services.

    Returns:
        dict: {
          "teh_amount":      float,
          "basket_price":    float,   (cost of one basket at this ε)
          "baskets_afforded": float,  (purchasing power in basket units)
          "pp_index":        float,   (relative to ε=0; 1.0 at ε=0, >1 thereafter)
          "epsilon":         float,
        }

    Reference: Mission Statement §"TEH-denominated prices fall as automation
    handles more EOH, so the same nominal TEH buys more."
    """
    bp_at_eps  = basket_price(epsilon, baseline_basket_cost, goods_weight, services_weight)
    bp_at_eps0 = basket_price(0.0,    baseline_basket_cost, goods_weight, services_weight)

    baskets_afforded = teh_amount / max(bp_at_eps, 1e-10)
    pp_index         = bp_at_eps0 / max(bp_at_eps, 1e-10)  # >1 means more purchasing power

    return {
        "teh_amount":       teh_amount,
        "basket_price":     bp_at_eps,
        "baskets_afforded": baskets_afforded,
        "pp_index":         pp_index,
        "epsilon":          epsilon,
    }


def floor_purchasing_power(
    floor_teh: float,
    epsilon: float = 0.40,
    baseline_basket_cost: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    goods_weight: float = BASKET_GOODS_WEIGHT,
    services_weight: float = BASKET_SERVICES_WEIGHT,
) -> dict:
    """
    Purchasing power of the sufficiency floor at automation level ε.

    The floor's purchasing power must never decline with automation (Principle 5).
    If the basket_price is monotonically decreasing and floor_teh is constant,
    then floor purchasing power is monotonically increasing — proven by construction.

    This function quantifies the rise: at ε=0.40, the floor should buy
    materially more than at ε=0. At ε=0.90, it should buy substantially more.

    Args:
        floor_teh: Nominal sufficiency floor in TEH/year (constant in nominal terms).
        epsilon: Automation level.
        baseline_basket_cost: Basket cost at ε=0.
        goods_weight: Fraction of basket that is goods.
        services_weight: Fraction of basket that is services.

    Returns:
        dict: {
          "floor_teh":         float,   (nominal, unchanged)
          "basket_price":      float,   (falling with ε)
          "baskets_afforded":  float,   (rising with ε — Principle 5)
          "pp_index":          float,   (relative to ε=0; must be ≥ 1.0)
          "pp_gain_pct":       float,   (percentage gain over ε=0 baseline)
          "epsilon":           float,
        }

    Reference: Mission Statement §"Principle 5 — The floor rises with
    automation; it never falls ... Any proposed modification that would allow
    the floor to decline in real terms ... violates the system's core commitment.
    Model it, flag it, reject it."
    """
    pp = purchasing_power(floor_teh, epsilon, baseline_basket_cost,
                          goods_weight, services_weight)
    pp_gain = (pp["pp_index"] - 1.0) * 100.0

    return {
        "floor_teh":        floor_teh,
        "basket_price":     pp["basket_price"],
        "baskets_afforded": pp["baskets_afforded"],
        "pp_index":         pp["pp_index"],
        "pp_gain_pct":      pp_gain,
        "epsilon":          epsilon,
    }


def floor_monotonicity_guard(
    floor_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    baseline_basket_cost: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    n_points: int = 100,
    tolerance: float = 1e-6,
) -> dict:
    """
    Verify that floor purchasing power is non-decreasing across the full ε range.

    This is the Principle 5 structural integrity check. Any modification to the
    pricing model that causes the floor PP to decline at any ε level must be
    flagged as a violation. This function sweeps ε from 0 to 0.99 and checks
    monotonicity at every step.

    Args:
        floor_teh: Nominal sufficiency floor.
        baseline_basket_cost: Basket cost at ε=0.
        n_points: Number of ε points to check.
        tolerance: Allowed backward step in pp_index (floating-point tolerance).

    Returns:
        dict: {
          "passes": bool,
          "violations": list[dict],  (empty if passes)
          "pp_at_eps0": float,
          "pp_at_eps90": float,
          "pp_at_eps99": float,
          "status": "OK" or "PRINCIPLE_5_VIOLATION",
        }

    Reference: Mission Statement §"Principle 5 — Model it, flag it, reject it."
    """
    violations = []
    prev_pp = None

    pp_at = {}
    for i in range(n_points + 1):
        eps = i * 0.99 / n_points
        result = floor_purchasing_power(floor_teh, eps, baseline_basket_cost)
        pp = result["pp_index"]

        if prev_pp is not None and pp < prev_pp - tolerance:
            violations.append({
                "epsilon":        eps,
                "pp_index":       pp,
                "prev_pp_index":  prev_pp,
                "decline":        prev_pp - pp,
            })

        for target in (0.0, 0.40, 0.90, 0.99):
            if abs(eps - target) < 0.99 / (2 * n_points):
                pp_at[target] = pp

        prev_pp = pp

    passes = len(violations) == 0
    return {
        "passes":      passes,
        "violations":  violations,
        "pp_at_eps0":  pp_at.get(0.0,  1.0),
        "pp_at_eps40": pp_at.get(0.40, None),
        "pp_at_eps90": pp_at.get(0.90, None),
        "pp_at_eps99": pp_at.get(0.99, None),
        "status":      "OK" if passes else "PRINCIPLE_5_VIOLATION",
    }


# ---------------------------------------------------------------------------
# Purchasing power sweep (for analysis and dashboard)
# ---------------------------------------------------------------------------

def purchasing_power_sweep(
    teh_amount: float,
    baseline_basket_cost: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    n_points: int = 20,
) -> list[dict]:
    """
    Compute purchasing power at each ε level across the automation arc.

    Args:
        teh_amount: TEH amount to evaluate (e.g., sufficiency floor).
        baseline_basket_cost: Basket cost at ε=0.
        n_points: Number of ε points.

    Returns:
        List of purchasing_power() results at each ε level.
    """
    result = []
    for i in range(n_points + 1):
        eps = i * 0.99 / n_points
        result.append(purchasing_power(teh_amount, eps, baseline_basket_cost))
    return result


# ---------------------------------------------------------------------------
# Comprehensive price monotonicity audit (all components, not just floor)
# ---------------------------------------------------------------------------

def full_price_monotonicity_audit(
    baseline_cost_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    human_labor_hours_at_eps0: float = 1.0,
    floor_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    n_points: int = 100,
    tolerance: float = 1e-6,
) -> dict:
    """
    Verify Principle 5 for all price components simultaneously.

    basket_price() and teh_price() must be monotonically non-increasing with ε.
    floor purchasing power must be monotonically non-decreasing. Scarcity
    multipliers can legally break monotonicity (they're demand-dependent) and
    are not checked here.

    This extends floor_monotonicity_guard() to cover basket price and goods
    price in addition to the floor PP. Any component violation means a
    modification to the pricing model has broken the fundamental Principle 5
    guarantee.

    Args:
        baseline_cost_teh: Basket cost at ε=0.
        human_labor_hours_at_eps0: Labor content of a reference good at ε=0.
        floor_teh: Nominal sufficiency floor.
        n_points: Number of ε points to check.
        tolerance: Allowed backward step (floating-point noise).

    Returns:
        dict: {
          "passes":              bool,   (True iff all components pass)
          "basket_price":        {"passes": bool, "violations": list, "range": [min, max]},
          "goods_price":         {"passes": bool, "violations": list, "range": [min, max]},
          "floor_pp":            {"passes": bool, "violations": list, "range": [min, max]},
          "status":              "OK" | "PRINCIPLE_5_VIOLATION",
          "violation_summary":   list[str],   (one-line descriptions of failing components)
        }

    Reference: Mission Statement §"Principle 5 — The floor rises with automation;
    it never falls"; §"Phase 3.2 — Model it, flag it, reject it."
    """
    basket_violations: list[dict] = []
    goods_violations:  list[dict] = []
    fp_violations:     list[dict] = []

    prev_basket = prev_goods = prev_fp = None
    basket_vals, goods_vals, fp_vals = [], [], []

    for i in range(n_points + 1):
        eps = i * 0.99 / n_points

        b_price = basket_price(eps, baseline_cost_teh)
        g_price = teh_price(human_labor_hours_at_eps0, eps)
        fp      = floor_purchasing_power(floor_teh, eps, baseline_cost_teh)["pp_index"]

        basket_vals.append(b_price)
        goods_vals.append(g_price)
        fp_vals.append(fp)

        if prev_basket is not None and prev_goods is not None and prev_fp is not None:
            if b_price > prev_basket + tolerance:
                basket_violations.append({
                    "epsilon": eps, "value": b_price,
                    "prev_value": prev_basket, "increase": b_price - prev_basket,
                })
            if g_price > prev_goods + tolerance:
                goods_violations.append({
                    "epsilon": eps, "value": g_price,
                    "prev_value": prev_goods, "increase": g_price - prev_goods,
                })
            if fp < prev_fp - tolerance:
                fp_violations.append({
                    "epsilon": eps, "value": fp,
                    "prev_value": prev_fp, "decline": prev_fp - fp,
                })

        prev_basket, prev_goods, prev_fp = b_price, g_price, fp

    components = {
        "basket_price": {
            "passes":     len(basket_violations) == 0,
            "violations": basket_violations,
            "range":      [min(basket_vals), max(basket_vals)],
        },
        "goods_price": {
            "passes":     len(goods_violations) == 0,
            "violations": goods_violations,
            "range":      [min(goods_vals), max(goods_vals)],
        },
        "floor_pp": {
            "passes":     len(fp_violations) == 0,
            "violations": fp_violations,
            "range":      [min(fp_vals), max(fp_vals)],
        },
    }

    all_pass = all(c["passes"] for c in components.values())
    violation_summary = [
        name for name, c in components.items() if not c["passes"]
    ]

    return {
        "passes":           all_pass,
        **components,
        "status":           "OK" if all_pass else "PRINCIPLE_5_VIOLATION",
        "violation_summary": violation_summary,
    }


# ---------------------------------------------------------------------------
# D4: CPI transaction-level destruction
# ---------------------------------------------------------------------------

def cpi_goods_destruction(
    capital_personal_eoh_fulfilled_total: float,
    epsilon: float,
    basket_eoh_content: float = BASKET_EOH_CONTENT,
) -> dict:
    """
    TEH destroyed when capital infrastructure delivers personal-EOH services.

    D4: the CPI transaction-level destruction mechanism. When capital assets
    (water treatment, hospitals, energy grids) fulfill personal EOH obligations,
    those services are consumed at their embedded labor price. TEH is destroyed
    at the point of delivery — the exchange of service for TEH is the destruction
    event, not deferred to a later behavioral consumption decision.

    Destruction = (capital_personal_eoh_fulfilled / basket_eoh_content) × basket_price(ε)

    As ε rises, basket_price falls, so D4 destruction per unit of fulfilled EOH
    also falls — consistent with automation making those services cheaper to provide.
    At ε=0, infrastructure services are expensive (high labor content); at ε→1,
    they approach free.

    Distinct from D2/D3 (income-driven individual consumption): D4 captures
    destruction at the infrastructure-to-recipient boundary, independent of
    whether individuals spend personal income. It closes the circuit for services
    that are never paid for directly by individuals (guarantee-funded or
    collectively provisioned goods).

    Args:
        capital_personal_eoh_fulfilled_total: Total personal EOH fulfilled by
            capital infrastructure across the entire population (EOH/year).
            Equals capital_personal_eoh_fulfilled_per_capita × population.
        epsilon: Automation level ε ∈ [0, 0.99].
        basket_eoh_content: Personal EOH hours per sufficiency basket. Default: 1500.

    Returns:
        dict: {
            "teh_destroyed":                    float,
            "baskets_delivered":                float,
            "basket_price":                     float,
            "capital_personal_eoh_fulfilled":   float,
            "mechanism":                        "D4_cpi",
        }

    Reference: Comprehensive Price Identity — goods' floor prices are set by
    embedded labor content (reconciliation §3); consumption at that price is
    the destruction event.
    """
    baskets = capital_personal_eoh_fulfilled_total / max(basket_eoh_content, 1.0)
    bp      = basket_price(epsilon)
    return {
        "teh_destroyed":                  baskets * bp,
        "baskets_delivered":              baskets,
        "basket_price":                   bp,
        "capital_personal_eoh_fulfilled": capital_personal_eoh_fulfilled_total,
        "mechanism":                      "D4_cpi",
    }
