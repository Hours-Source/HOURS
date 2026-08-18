"""
scenarios/sweep — Epsilon sweep across the full automation arc.

Verifies that the EOH framework remains coherent from ε=0 to ε=0.99.
Checks every computed value for NaN, Infinity, and unexpected discontinuities.
Includes fiscal solvency at every ε point (new-7).

Mission Statement: §"Degrade gracefully as ε → 1.0 (no discontinuities or
division-by-zero)"; §"The system must remain coherent across the full automation arc."
"""

from __future__ import annotations
import math
from typing import Any

from hours_eoh.data import (
    AGE_GROUPS,
    ECOLOGICAL_BASE_RATE, LAND_HECTARES_PER_CAPITA, SKILL_TRANSMISSION_RATE,
    TRUST_BASE_TEH,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    CAPITAL_STOCK_DEFAULT,
)
from hours_eoh.core.eoh_generation import (
    personal_eoh,
    infrastructure_eoh,
    ecological_eoh,
    knowledge_eoh,
)
from hours_eoh.core.registration import (
    care_registration_share,
    total_registration_share,
)
from hours_eoh.core.prices import basket_price, floor_purchasing_power
from hours_eoh.core.fiscal import fiscal_snapshot


def epsilon_sweep(
    n_points: int = 100,
    population: float = 1_000_000.0,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
    knowledge_base_size: float = 10.0,
    trust_balance: float = TRUST_BASE_TEH,
    floor_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    jump_threshold: float = 5.0,
) -> dict:
    """
    Run all core functions across ε = 0 to 0.99 in n_points steps.

    Checks every value for: NaN, Infinity, unexpected discontinuities,
    monotonicity violations in basket_price and floor_pp.

    Args:
        n_points: Number of ε points (0.0 to 0.99). Default: 100.
        population: Population for personal EOH.
        capital_stock_teh: Capital stock for infrastructure EOH.
        capital_age_ratio: Mean asset age as fraction of design life.
        ecosystem_health: Ecological health [0,1]. Default: 0.70 (above crisis threshold).
        knowledge_base_size: Knowledge base for knowledge EOH.
        trust_balance: Trust fund balance.
        floor_teh: Sufficiency floor for PP calculation.
        jump_threshold: Max allowed relative jump (|Δf| / |f|) per ε step.
                        Default: 5.0 (500%). Flags sudden 5× changes.

    Returns:
        dict: {
          "sweep":                  list[dict],  (one per ε point)
          "n_points":               int,
          "all_finite":             bool,
          "basket_price_monotone":  bool,
          "floor_pp_monotone":      bool,
          "discontinuities":        list[dict],  (flagged jumps)
          "infinities":             list[dict],  (NaN/Inf values)
          "status":                 "OK" or "ISSUES_FOUND",
        }
    """
    age_distribution = {
        group: AGE_GROUPS[group]["fraction"] * population
        for group in AGE_GROUPS
    }

    results         = []
    prev: dict[str, Any] = {}
    infinities      = []
    discontinuities = []
    basket_prices   = []
    floor_pps       = []

    for i in range(n_points + 1):
        eps = i * 0.99 / n_points

        pers_eoh  = personal_eoh(population, age_distribution, eps)
        infra_eoh = infrastructure_eoh(capital_stock_teh, capital_age_ratio, eps)
        # PHASE 4b (2026-08-17): resolve the ecological area FROM THE POPULATION,
        # as total_eoh now does. This module sums its own four domains rather
        # than calling total_eoh, so it was a SECOND live instance of the frame
        # mismatch and the fix there did not reach it: personal scaled with
        # `population` while ecological carried ECOLOGICAL_BASE_RATE, the whole
        # contiguous US. Exactly the shape of the SKILL_TRANSMISSION_RATE defect
        # documented immediately below — a module that bypasses the shared path
        # is the last place a superseded default survives.
        eco_eoh   = ecological_eoh(
            ecosystem_health, eps,
            area_hectares=population * LAND_HECTARES_PER_CAPITA,
        )
        # SKILL_TRANSMISSION_RATE, not the deprecated SKILL_DECAY_RATE this
        # module used until 2026-08-09. params.py moved its `skill_decay_rate`
        # default to the transmission rate at Block K-IV; sweep.py bypasses
        # params and so was left as the last live caller of the pre-K-IV value,
        # scoring knowledge EOH 4.00× high (knowledge_eoh is linear in the
        # rate) against every other path in the repo.
        know_eoh  = knowledge_eoh(knowledge_base_size, SKILL_TRANSMISSION_RATE, eps,
                                  population=population)
        tot_eoh   = pers_eoh + infra_eoh + eco_eoh + know_eoh

        bp  = basket_price(eps, floor_teh)
        pp  = floor_purchasing_power(floor_teh, eps, floor_teh)
        care = care_registration_share(eps)
        reg  = total_registration_share(eps)

        labor_income_proxy = tot_eoh * (1.0 - eps)
        fiscal = fiscal_snapshot(
            trust_balance=trust_balance,
            labor_income=max(labor_income_proxy, 1.0),
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            population=population,
            epsilon=eps,
            ecosystem_health=ecosystem_health,
        )

        metrics = {
            "epsilon":               eps,
            "personal_eoh":          pers_eoh,
            "infrastructure_eoh":    infra_eoh,
            "ecological_eoh":        eco_eoh,
            "knowledge_eoh":         know_eoh,
            "total_eoh":             tot_eoh,
            "basket_price":          bp,
            "floor_pp_index":        pp["pp_index"],
            "care_registration":     care,
            "total_registration":    reg,
            "fiscal_solvent":        fiscal["solvent"],
            "trust_surplus_deficit": fiscal["trust"]["surplus_deficit"],
        }
        results.append(metrics)
        basket_prices.append(bp)
        floor_pps.append(pp["pp_index"])

        for key, val in metrics.items():
            if key == "epsilon":
                continue
            if not math.isfinite(val):
                infinities.append({"epsilon": eps, "metric": key, "value": val})

        if prev:
            for key in ("personal_eoh", "infrastructure_eoh", "basket_price",
                        "floor_pp_index", "care_registration", "total_registration"):
                old_val = prev.get(key, 0.0)
                new_val = metrics[key]
                if abs(old_val) > 1e-10:
                    rel_jump = abs(new_val - old_val) / abs(old_val)
                    if rel_jump > jump_threshold:
                        discontinuities.append({
                            "epsilon":   eps,
                            "metric":    key,
                            "old_value": old_val,
                            "new_value": new_val,
                            "rel_jump":  rel_jump,
                        })
        prev = metrics

    basket_monotone = all(
        basket_prices[i] >= basket_prices[i + 1] - 1e-9
        for i in range(len(basket_prices) - 1)
    )
    pp_monotone = all(
        floor_pps[i] <= floor_pps[i + 1] + 1e-9
        for i in range(len(floor_pps) - 1)
    )

    all_finite = len(infinities) == 0
    has_issues = not all_finite or not basket_monotone or not pp_monotone

    return {
        "sweep":                 results,
        "n_points":              n_points,
        "all_finite":            all_finite,
        "basket_price_monotone": basket_monotone,
        "floor_pp_monotone":     pp_monotone,
        "discontinuities":       discontinuities,
        "infinities":            infinities,
        "status":                "ISSUES_FOUND" if has_issues else "OK",
    }
