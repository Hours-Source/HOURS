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

from hours_eoh.data import MEANINGFUL_ACTIVITY_TEH_BASE
from hours_eoh.core.eoh_generation import (
    resolve_capital_stock,
    resolve_knowledge_base_size,
)
from hours_eoh.core.registration import (
    care_registration_share,
    total_registration_share,
)
from hours_eoh.core.prices import basket_price, floor_purchasing_power
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.core.fiscal import resolve_trust_balance


def epsilon_sweep(
    n_points: int = 100,
    population: float = 1_000_000.0,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float = 0.30,
    ecosystem_health: float = 0.70,
    knowledge_base_size: float | None = None,
    trust_balance: float | None = None,
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
    trust_balance = resolve_trust_balance(trust_balance, population)

    results         = []
    prev: dict[str, Any] = {}
    infinities      = []
    discontinuities = []
    basket_prices   = []
    floor_pps       = []

    for i in range(n_points + 1):
        eps = i * 0.99 / n_points

        # (e) 2026-09-09: an unspecified stock resolves along the arc at EACH ε,
        # so the sweep still sweeps capital (and knowledge). Resolved once per
        # point and used by both the pipeline and the fiscal snapshot, so the
        # two cannot read different capital for the same ε.
        cap_at_eps = resolve_capital_stock(capital_stock_teh, eps, population=population)
        kbs_at_eps = resolve_knowledge_base_size(knowledge_base_size, eps)

        # ONE PIPELINE CALL (2026-09-30): the domains, the observed ε and the
        # mint all come from the shared path. This module summed its own four
        # domains beside that call, and THREE defects survived in the
        # hand-summed copy because the shared path's tests could not see it —
        # ecological at the whole-US area (Phase 4b), knowledge at the
        # pre-K-IV decay rate (4.00×), and head counts passed as age fractions
        # (personal EOH population² × weight, 2026-09-30).
        pipe = eoh_to_teh_pipeline(
            eps, population=population, capital_stock=cap_at_eps,
            capital_age_ratio=capital_age_ratio, ecosystem_health=ecosystem_health,
            knowledge_complexity=kbs_at_eps,
        )
        domains   = pipe["eoh_by_domain"]
        pers_eoh  = float(domains["personal"])
        infra_eoh = float(domains["infrastructure"])
        eco_eoh   = float(domains["ecological"])
        know_eoh  = float(domains["knowledge"])
        tot_eoh   = float(pipe["total_eoh"])

        # THE FLOOR IS READ AT THE OBSERVED ε (author decision, 2026-09-30): the
        # machine share of THIS point's obligation, not the capability index.
        eps_floor = float(pipe["epsilon_observable"])
        bp  = basket_price(eps_floor, floor_teh)
        pp  = floor_purchasing_power(floor_teh, eps_floor, floor_teh)
        care = care_registration_share(eps)
        reg  = total_registration_share(eps)

        # THE MINT IS THE LABOUR INCOME (2026-09-30) — the same call's.
        mint = float(pipe["teh_created"])
        fiscal = fiscal_snapshot(
            trust_balance=trust_balance,
            labor_income=mint,
            capital_stock_teh=cap_at_eps,
            capital_age_ratio=capital_age_ratio,
            population=population,
            epsilon=eps,
            ecosystem_health=ecosystem_health,
        )

        metrics = {
            "epsilon":               eps,
            "epsilon_observable":    eps_floor,
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
