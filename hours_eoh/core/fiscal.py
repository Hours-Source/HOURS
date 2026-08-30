"""
Levies and Circulation, Care Labor Compensation, Land and Stewardship EOH

All levy and fiscal mechanisms are CIRCULATORY: they move TEH between
accounts but never create or destroy it. Only terminal consumption and
capital write-down destroy TEH (Condition I). The fiscal system's job is
to redirect TEH from where labor earns it to where entropy obligations require
it — the stewardship allocation and sufficiency guarantee.

The Trust is the fiscal backbone. Its balance represents accumulated social
wealth that funds the stewardship economy as production output declines with
automation. Unlike a sovereign wealth fund, it does not earn interest
(Condition III) — it pays out via dividend and is replenished by levies.

Mission Statement: §"Fiscal architecture", §"The Trust and the Stewardship
Allocation", §"Principle 2 — The system must never depend on production for
survival", §"The registration boundary" (care), §"Land is held by the collective"
"""

from __future__ import annotations
import math

from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    SUFF_LEVY_RATE, DEP_RATE, DIV_RATE,
    PERSONAL_EOH_BASE, AGE_GROUPS,
    MEANINGFUL_ACTIVITY_TEH_BASE, MEANINGFUL_ACTIVITY_TEH_SCALE,
    SUFF_GUARANTEE_EPS_DECAY,
    INFRA_MAINT_RATE, ECOLOGICAL_BASE_RATE, ECOLOGICAL_INTENSITY_BASE,
    ACCUMULATION_CEILING_MULTIPLIER, BASE_LIFETIME_EARNINGS_TEH,
    MEAN_MULTIPLIER_REFERENCE, LAND_HECTARES_PER_CAPITA,
    CARE_AUTOMATION_FLOOR, SUFF_GUARANTEE_STRUCTURAL_MIN,
    PROVIDER_CAP_EQUIVALENTS,
)
from hours_eoh.core.eoh_generation import infrastructure_eoh, ecological_eoh
from hours_eoh.core.eoh_fulfillment import human_eoh_share


# ---------------------------------------------------------------------------
# Fiscal calibration constants
# ---------------------------------------------------------------------------
# CARE_AUTOMATION_FLOOR and SUFF_GUARANTEE_STRUCTURAL_MIN MIGRATED TO data.py
# 2026-08-28 as CARE_AUTOMATION_FLOOR and SUFF_GUARANTEE_STRUCTURAL_MIN. Both
# were shadow constants: untagged, and a +7% move failed no test.
# SUFF_GUARANTEE_EPS_DECAY imported from data.py
# Population-weighted mean EOH weight from default AGE_GROUPS fractions (constant):
# 0.07×3.0 + 0.16×1.5 + 0.60×1.0 + 0.17×2.5 = 1.475
_AGE_WEIGHTED_EOH_MEAN: float = sum(
    v["fraction"] * v["eoh_weight"] for v in AGE_GROUPS.values()
)


# ===========================================================================
# Levies and Circulation
# ===========================================================================

def levy_collection(
    labor_income: float,
    levy_rates: dict[str, float],
) -> dict:
    """
    Collect TEH levies from labor income. All levies are circulatory.

    Levies redirect TEH from workers to the Trust (and other collective funds).
    No TEH is created or destroyed: worker_net + total_levied = labor_income.
    This is verifiable using balance_check() from conditions.py.

    Multiple levy rates may apply simultaneously (sufficiency levy, stewardship
    levy, care allocation levy). Each is expressed as a fraction of gross
    labor income.

    Args:
        labor_income: Gross TEH earned by workers this period (= teh_created).
        levy_rates: Dict mapping levy name → rate ∈ [0, 1].
                    Common keys: "sufficiency", "stewardship", "care_allocation".

    Returns:
        dict: {
          "gross_income": float,
          "total_levy_rate": float,
          "total_levied": float,
          "worker_net": float,
          "by_levy": dict[str, float],   (TEH collected per levy)
          "circulatory": bool,           (always True — sanity check)
        }

    Raises:
        ValueError: If any rate is outside [0, 1] or total rate exceeds 1.0.

    Reference: Mission Statement §"Condition I — Levies and fiscal mechanisms
    that collect TEH are circulatory — they redirect TEH into capital investment,
    stewardship allocation, and social programs, but do not destroy it."
    """
    for name, rate in levy_rates.items():
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"Levy rate '{name}' must be in [0, 1], got {rate}")

    total_rate = sum(levy_rates.values())
    if total_rate > 1.0 + 1e-9:
        raise ValueError(
            f"Total levy rate {total_rate:.4f} exceeds 1.0 — workers cannot owe more than they earn."
        )

    by_levy = {name: labor_income * rate for name, rate in levy_rates.items()}
    total_levied = sum(by_levy.values())
    worker_net   = labor_income - total_levied

    return {
        "gross_income":    labor_income,
        "total_levy_rate": total_rate,
        "total_levied":    total_levied,
        "worker_net":      worker_net,
        "by_levy":         by_levy,
        "circulatory":     True,
    }


def _allocation_metrics(
    total_eoh: float,
    epsilon: float,
    available_teh: float,
    mean_multiplier: float,
) -> tuple[float, float, float, float, bool, float]:
    """Shared computation for stewardship_allocation() and ecological_allocation()."""
    human_eoh     = human_eoh_share(total_eoh, epsilon)
    teh_required  = human_eoh * mean_multiplier
    teh_allocated = min(teh_required, available_teh)
    funding_gap   = max(0.0, teh_required - available_teh)
    fully_funded  = funding_gap < 1.0
    coverage      = teh_allocated / max(teh_required, 1.0)
    return human_eoh, teh_required, teh_allocated, funding_gap, fully_funded, coverage


def stewardship_allocation(
    capital_stock_teh: float,
    capital_age_ratio: float,
    epsilon: float,
    available_teh: float,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    infra_maint_rate: float = INFRA_MAINT_RATE,
    infra_eoh_override: float | None = None,
) -> dict:
    """
    Direct TEH toward fulfilling EOH generated by the capital stock.

    The stewardship allocation is sized by the capital stock's entropy
    obligations — the infrastructure EOH that requires human labor. It is NOT
    sized by political budgeting. When the capital stock grows (as automation
    enables more investment), the stewardship allocation must grow with it.
    This is the mechanism by which the Trust's expenditure scales with the
    stewardship economy's growing needs.

    The allocation is capped at available_teh — the Trust cannot pay out more
    than it has. Any gap between required and available indicates a funding
    shortfall that must be flagged.

    Args:
        capital_stock_teh: Total capital stock value in TEH (baseline at ε=0).
        capital_age_ratio: Mean asset age relative to design life, ∈ [0, 1].
        epsilon: Automation level. Affects both capital size and human share.
        available_teh: TEH available in the Trust for stewardship allocation.
        mean_multiplier: Mean multiplier for stewardship workers.
        infra_maint_rate: Fraction of capital stock = annual EOH demand.
        infra_eoh_override: If provided, use this value as the total infrastructure
            EOH instead of recomputing via infrastructure_eoh(). Pass
            total_eoh(...)["infrastructure"] here when capital_eoh_eliminated has
            already been applied — this keeps stewardship sizing consistent with
            the EOH ledger and avoids double-counting eliminated obligations.

    Returns:
        dict: {
          "infrastructure_eoh_total": float,
          "human_stewardship_eoh":    float,   (= human_eoh_share of infra EOH)
          "teh_required":             float,   (human_eoh × multiplier)
          "teh_allocated":            float,   (min(required, available))
          "funding_gap":              float,   (0 if fully funded)
          "fully_funded":             bool,
          "funding_coverage":         float,   (allocated / required)
          "epsilon":                  float,
        }

    Reference: Mission Statement §"The stewardship economy — the Trust and
    the Stewardship Allocation become the economy's fiscal center of gravity";
    §"Principle 2 — Revenue streams pegged to the capital stock's entropy
    obligations are foundational."
    """
    if infra_eoh_override is not None:
        total_infra_eoh = infra_eoh_override
    else:
        total_infra_eoh = infrastructure_eoh(
            capital_stock=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            epsilon=epsilon,
            base_maint_rate=infra_maint_rate,
        )

    human_eoh, teh_required, teh_allocated, funding_gap, fully_funded, coverage = (
        _allocation_metrics(total_infra_eoh, epsilon, available_teh, mean_multiplier)
    )

    return {
        "infrastructure_eoh_total": total_infra_eoh,
        "human_stewardship_eoh":    human_eoh,
        "teh_required":             teh_required,
        "teh_allocated":            teh_allocated,
        "funding_gap":              funding_gap,
        "fully_funded":             fully_funded,
        "funding_coverage":         coverage,
        "epsilon":                  epsilon,
    }


def ecological_allocation(
    ecosystem_health: float,
    epsilon: float,
    available_teh: float,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    base_rate: float | None = None,
    deferred: float = 0.0,
    eco_eoh_override: float | None = None,
    thermal_obligation: float = 0.0,
    area_hectares: float | None = None,
    intensity: float = ECOLOGICAL_INTENSITY_BASE,
    health_response: str = "guf",
    standing_response: str = "guf",
) -> dict:
    """
    Direct TEH toward fulfilling EOH generated by natural systems.

    Ecological stewardship is the second pillar of the stewardship economy,
    alongside infrastructure maintenance. As automation rises, ecological
    EOH grows (more monitoring makes more deferred obligations visible) while
    the human labor share falls (automation handles more routine monitoring).
    At high ε, the remaining human ecological labor is judgment-intensive:
    triage, intervention, and ecosystem design that automation cannot substitute.

    Like stewardship_allocation(), the allocation is sized by physical obligation
    (ecological_eoh()), not by budget. The Trust is the funding source. Any gap
    between required and available is flagged as a shortfall.

    Args:
        ecosystem_health: Current ecosystem state ∈ [0, 1]. Lower → more EOH.
        epsilon: Automation level. Affects both ecological EOH visibility and
                 the human labor share required to fulfill it.
        available_teh: TEH available in the Trust for ecological allocation.
        mean_multiplier: Mean multiplier for ecological stewardship workers.
        base_rate: Baseline ecological EOH at health=1.0 (hours/year). An
            ABSOLUTE obligation for a declared reference frame. None (default)
            and no `area_hectares` → ECOLOGICAL_BASE_RATE, the whole-contiguous-US
            anchor, which is the right default ONLY for a caller with no
            population in scope. See `area_hectares`.
        deferred: Accumulated deferred ecological EOH from historical neglect.
        eco_eoh_override: If provided, use this value as the total ecological
            EOH instead of recomputing via ecological_eoh(). Pass
            total_eoh(...)["ecological"] here when available.
        area_hectares: The land this allocation is the obligation FOR. Supply it
            and the scale resolves as `area × intensity` instead of resting on
            the US anchor. A caller that scales anything else with population
            MUST state its frame this way — pairing one jurisdiction's
            population with another's land silently rescales the domain (the
            defect Phase 4b closed in `total_eoh`, found four more times since).
        intensity: Ecological EOH per hectare per year at health = 1.0. Used
            only when resolving from `area_hectares`.

    Raises:
        ValueError: If both `base_rate` and `area_hectares` are given. They are
            two answers to one question and `ecological_scale` silently prefers
            base_rate, so an area the caller believes is in force and is not is
            exactly the silently-ignored-parameter failure this repo keeps
            finding. `total_eoh` refuses the same combination for the same reason.

    Returns:
        dict: {
          "ecological_eoh_total": float,
          "human_ecological_eoh": float,   (= human_eoh_share of ecological EOH)
          "teh_required":         float,   (human_eoh × multiplier)
          "teh_allocated":        float,   (min(required, available))
          "funding_gap":          float,   (0 if fully funded)
          "fully_funded":         bool,
          "funding_coverage":     float,   (allocated / required)
          "epsilon":              float,
        }

    Reference: Mission Statement §"The stewardship economy — humans maintain
    the machines, the infrastructure, the ecological systems, and the knowledge
    base"; §"Ecological EOH makes the obligation visible: ignoring it does not
    eliminate the obligation but defers it with compounding consequences."
    """
    if base_rate is not None and area_hectares is not None:
        raise ValueError(
            "pass base_rate OR area_hectares, not both: "
            f"got base_rate={base_rate}, area={area_hectares} ha. "
            "The area would be silently ignored under ecological_scale() precedence."
        )
    # Neither given → the declared US reference frame. Correct for a caller with
    # no population in scope; a caller that HAS one must pass `area_hectares`.
    if base_rate is None and area_hectares is None:
        base_rate = ECOLOGICAL_BASE_RATE

    # WHY THIS CAN BE ZERO, REPORTED RATHER THAN LEFT SILENT. After Phases 4e
    # and 4f (adopted 2026-08-28/29) the ecological DOMAIN carries stocks only,
    # and none ships by default — so `ecological_eoh` returns 0.0 and the Trust
    # allocates nothing here. That is the partition working, not an omission:
    # the recurring cost of holding land is the Ground Use Fee's.
    #
    # BUT `fiscal_snapshot` HAS NO GUF REVENUE LINE, so the obligation leaves
    # this allocation and is not picked up anywhere else in the fiscal snapshot.
    # `relocated_to_guf` reports what the pre-partition policy would have
    # charged here, so a reader sees the size of what moved instead of a bare
    # zero. Connecting GUF revenue to the fisc is open work.
    # THE RELOCATED FIGURE IS COMPUTED WHETHER OR NOT AN OVERRIDE IS SUPPLIED
    # (corrected 2026-08-29). This read `_relocated = 0.0` in the override
    # branch, on the reasoning that a caller supplying the total must know what
    # was relocated. That was wrong twice over: an override states the DOMAIN
    # total and says nothing about what left it, and both principal paths —
    # `simulate_period` and `scenarios/collective.collective_snapshot` — pass an
    # override. So the two calls that matter reported no relocated obligation,
    # which made `snap["guf"]["coverage"]` vacuous exactly where it was meant to
    # be read. Found by running the new assembly scenario, three commits after
    # the field was added: the reported value was not the computed one, which is
    # the `psi` vs `psi_applied` failure in code written to close that class.
    #
    # It is derivable from the same arguments the override was derived from, so
    # it is derived. The caveat is that this assumes the override was computed
    # at THIS frame — which `collective_snapshot` guarantees by construction,
    # since it passes the area and the override from one resolution.
    _relocated = ecological_eoh(
        ecosystem_health=ecosystem_health,
        epsilon=epsilon,
        base_rate=base_rate,
        deferred=deferred,
        thermal_obligation=thermal_obligation,
        area_hectares=area_hectares,
        intensity=intensity,
        health_response="domain",
        standing_response="domain",
    )
    if eco_eoh_override is not None:
        total_eco_eoh = eco_eoh_override
    else:
        total_eco_eoh = ecological_eoh(
            ecosystem_health=ecosystem_health,
            epsilon=epsilon,
            base_rate=base_rate,
            deferred=deferred,
            thermal_obligation=thermal_obligation,
            area_hectares=area_hectares,
            intensity=intensity,
            health_response=health_response,
            standing_response=standing_response,
        )

    human_eoh, teh_required, teh_allocated, funding_gap, fully_funded, coverage = (
        _allocation_metrics(total_eco_eoh, epsilon, available_teh, mean_multiplier)
    )

    return {
        "ecological_eoh_total": total_eco_eoh,
        "human_ecological_eoh": human_eoh,
        "teh_required":         teh_required,
        "teh_allocated":        teh_allocated,
        "funding_gap":          funding_gap,
        "fully_funded":         fully_funded,
        "funding_coverage":     coverage,
        "epsilon":              epsilon,
        # What the pre-partition policy would have charged here. Zero above with
        # a positive figure here means the obligation MOVED to GUF, not that it
        # vanished — see the note at the top of this function.
        "relocated_to_guf":     _relocated,
        # ...and the same quantity in TEH, so it can be set against GUF revenue
        # without the reader doing the human-share and multiplier conversion by
        # hand. This is the obligation the partition assigns to the Ground Use
        # Fee; `fiscal_snapshot` compares it against what GUF actually collects.
        "relocated_teh_required": (
            human_eoh_share(_relocated, epsilon) * mean_multiplier
        ),
    }


def sufficiency_guarantee(
    population: float,
    epsilon: float,
    personal_eoh_base: float = PERSONAL_EOH_BASE,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    meaningful_activity_scale: float = MEANINGFUL_ACTIVITY_TEH_SCALE,
    floor_fraction: float = 0.15,
    capital_personal_eoh_fulfilled_per_person: float = 0.0,
) -> dict:
    """
    Compute the cost of the sufficiency guarantee at a given automation level.

    The guarantee has two components per recipient:
    1. EOH reimbursement: 1 TEH per EOH of personal biological entropy burden.
       Covers the metabolic/care obligation that exists regardless of labor
       participation. Uses the population-weighted average age EOH weight so
       the payment reflects the actual biological mix (infants, elderly, etc.).
    2. Meaningful activity TEH: discretionary spending bonus beyond biological
       subsistence. Scales quadratically with ε so non-participants have real
       purchasing power as the labor pool shrinks at high automation — without
       eliminating the incentive to join the labor pool (which earns a multiplier
       premium on top of this baseline).

    The fraction receiving the guarantee declines slightly with ε (rising
    purchasing power means fewer people fall below subsistence), but a
    structural minimum remains for those between labor engagements or unable
    to work.

    Principle 5: the guarantee's purchasing power rises with automation because
    the meaningful activity component grows with ε while the basket price falls.

    Args:
        population: Total population.
        epsilon: Automation level [0.0, 0.99].
        personal_eoh_base: Personal EOH base rate (h/yr per working-age-equivalent).
        meaningful_activity_teh: Discretionary spending bonus at ε=0 (TEH/yr).
        meaningful_activity_scale: Quadratic growth factor: bonus = base×(1+scale×ε²).
        floor_fraction: Fraction of population receiving the guarantee.
        capital_personal_eoh_fulfilled_per_person: Personal EOH already fulfilled
            by the capital stock per person per year (= total capital fulfillment /
            population). Reduces the EOH reimbursement component: the guarantee
            only reimburses UNFULFILLED personal EOH. The biological demand still
            exists — capital handles fulfillment, reducing what individuals need
            TEH to address. Floored at zero so over-fulfillment doesn't go negative.

    Governing equations (two-component guarantee per recipient):

        raw_eoh = ā × personal_eoh_base          (ā = 1.475, age-weighted EOH mean)
        eoh_reimb = max(0, raw_eoh − capital_fulfilled_per_person)  [TEH/yr]
        meaningful_activity = base × (1 + scale × ε²)              [TEH/yr]
        total_per_person = eoh_reimb + meaningful_activity
        total_cost = recipients × total_per_person

    As ε rises from 0 to 1, total_cost_teh *falls* (fewer recipients × smaller
    reimbursement as capital handles more personal EOH) even as per-person
    purchasing power rises (meaningful_activity grows with ε²).

    Worked examples (population=1M, capital_fulfilled=0, canonical defaults):

        ε     recipients  eoh_reimb/person  ma_teh/person  total/person  total_cost
        0.00    150,000       2,213 TEH        120 TEH      2,333 TEH      350M TEH
        0.40    130,000       2,213 TEH        149 TEH      2,361 TEH      307M TEH
        0.70    115,000       2,213 TEH        208 TEH      2,421 TEH      278M TEH

    Returns:
        dict: {
          "population":                              float,
          "floor_fraction":                          float,
          "recipients":                              float,
          "raw_eoh_per_person":                      float,  TEH/yr — age-weighted, pre-fulfillment
          "capital_personal_eoh_fulfilled_per_person": float,
          "eoh_reimbursement_per_person":            float,  TEH/yr — max(0, raw − capital_fulfilled)
          "meaningful_activity_teh_effective":       float,  TEH/yr — ε-scaled discretionary bonus
          "total_per_person":                        float,  TEH/yr
          "eoh_reimbursement_total":                 float,  TEH/yr — aggregate
          "meaningful_activity_total":               float,  TEH/yr
          "total_cost_teh":                          float,  TEH/yr — total guarantee cost
          "epsilon":                                 float,
        }

    Reference: Mission Statement §"Principle 5 — The floor rises with automation;
    it never falls." §"The sufficiency guarantee: purchasing power never declines."
    """
    # Clamp floor_fraction to the structural minimum so the formula can't
    # produce an effective_fraction below SUFF_GUARANTEE_STRUCTURAL_MIN
    # when a caller passes a floor_fraction smaller than the minimum.
    floor_fraction = max(floor_fraction, SUFF_GUARANTEE_STRUCTURAL_MIN)

    raw_eoh_per_person = _AGE_WEIGHTED_EOH_MEAN * personal_eoh_base
    eoh_reimbursement_per_person = max(0.0, raw_eoh_per_person - capital_personal_eoh_fulfilled_per_person)

    # Meaningful activity TEH grows quadratically with ε: as the labor pool shrinks,
    # non-participants need more purchasing power; quadratic prevents premature
    # inflation at low-ε where labor participation is easy.
    meaningful_activity_teh_effective = (
        meaningful_activity_teh * (1.0 + meaningful_activity_scale * epsilon ** 2)
    )

    total_per_person = eoh_reimbursement_per_person + meaningful_activity_teh_effective

    # At higher ε, fewer people need the guarantee (rising PP means less hardship),
    # but a structural minimum remains (training periods, illness, care commitments).
    effective_fraction = (
        SUFF_GUARANTEE_STRUCTURAL_MIN
        + (floor_fraction - SUFF_GUARANTEE_STRUCTURAL_MIN) * (1.0 - SUFF_GUARANTEE_EPS_DECAY * epsilon)
    )

    recipients = population * effective_fraction
    eoh_reimbursement_total = recipients * eoh_reimbursement_per_person
    meaningful_activity_total = recipients * meaningful_activity_teh_effective
    total_cost_teh = eoh_reimbursement_total + meaningful_activity_total

    return {
        "population":                                population,
        "floor_fraction":                            effective_fraction,
        "recipients":                                recipients,
        "raw_eoh_per_person":                        raw_eoh_per_person,
        "capital_personal_eoh_fulfilled_per_person": capital_personal_eoh_fulfilled_per_person,
        "eoh_reimbursement_per_person":              eoh_reimbursement_per_person,
        "meaningful_activity_teh_effective":         meaningful_activity_teh_effective,
        "total_per_person":                          total_per_person,
        "eoh_reimbursement_total":                   eoh_reimbursement_total,
        "meaningful_activity_total":                 meaningful_activity_total,
        "total_cost_teh":                            total_cost_teh,
        "epsilon":                                   epsilon,
    }


# ===========================================================================
# Trust Management
# ===========================================================================

def trust_management(
    trust_balance: float,
    levy_revenue: float,
    stewardship_cost: float,
    guarantee_cost: float,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    epsilon: float = 0.40,
    guf_revenue: float = 0.0,
) -> dict:
    """
    Fiscal balance of the Trust for one period.

    The Trust is the structural backbone of the fiscal system. As production
    output shrinks with automation, the Trust's stewardship dividend becomes
    the dominant revenue stream. Its balance represents accumulated social
    wealth — the collective's "savings" — that enables the stewardship economy
    to function without depending on production labor income.

    The Trust does NOT earn interest (Condition III). Its balance changes only
    through levy inflows and dividend payouts. Over time, if levy inflows
    are insufficient to offset payouts, the Trust balance shrinks — making
    long-run solvency a structural design concern, not an afterthought.

    Trust flows this period:
    1. Annual depreciation: annDep = trust × dep_rate
       (The "spending capacity" the Trust can mobilize)
    2. Dividend (paid out): annDep × div_rate → funds stewardship + guarantee
    3. Renewal (stays in Trust): annDep × (1 - div_rate) → reinvested
    4. Levy inflows: replenish trust from labor income
    5. End balance: trust - annDep + renewal + levy_revenue
       = trust × (1 - dep_rate × div_rate) + levy_revenue

    Args:
        trust_balance: Trust balance at start of period (TEH).
        levy_revenue: Total levy revenue collected this period (TEH).
        stewardship_cost: TEH required for stewardship allocation.
        guarantee_cost: TEH required for sufficiency guarantee.
        dep_rate: Annual depreciation rate of trust balance.
        div_rate: Fraction of depreciation paid as dividend.
        epsilon: Automation level (for context/reporting).

    Returns:
        dict: {
          "trust_start":       float,
          "ann_depreciation":  float,
          "dividend":          float,    (= annDep × div_rate; available for spending)
          "renewal":           float,    (= annDep × (1 - div_rate); stays in trust)
          "levy_inflow":       float,
          "total_revenue":     float,    (dividend + levy)
          "total_expenditure": float,    (stewardship + guarantee)
          "surplus_deficit":   float,    (positive = surplus)
          "solvent":           bool,
          "trust_end":         float,    (projected end-of-period balance)
          "trust_stable":      bool,     (end balance ≥ start balance)
          "epsilon":           float,
        }

    Reference: Mission Statement §"Principle 2 — The fiscal architecture must
    remain solvent under any automation level"; §"Revenue streams pegged to the
    capital stock's entropy obligations are foundational."
    """
    ann_dep    = trust_balance * dep_rate
    dividend   = ann_dep * div_rate
    renewal    = ann_dep * (1.0 - div_rate)

    # GUF IS ITS OWN REVENUE LINE, NOT FOLDED INTO THE LEVY (2026-08-29).
    # A ground-use fee and a labour levy are different instruments: the levy
    # scales with labour income and therefore CONTRACTS as ε rises, while GUF
    # scales with land held and does not. Adding GUF into `levy_inflow` would
    # hide exactly the substitution the Phase 4 partition is about — and
    # `land/guf.py` claims GUF "may become the Trust's dominant revenue source,
    # replacing the contracting labor levy base", which is a claim you cannot
    # check if the two arrive as one number.
    #
    # It is CIRCULATORY, like the levy: collected from holders and spent, never
    # minted. `land/guf.py` says so in its own header ("GUF revenue is
    # circulatory TEH flowing to the Trust"), so no TEH is created here and
    # Condition III is untouched.
    total_revenue     = dividend + levy_revenue + guf_revenue
    total_expenditure = stewardship_cost + guarantee_cost
    surplus_deficit   = total_revenue - total_expenditure

    # Trust balance evolves: loses depreciation, gains renewal and both inflows
    # (dividend goes out; renewal stays; levy and GUF come in)
    trust_end = trust_balance - ann_dep + renewal + levy_revenue + guf_revenue
    # Equivalently: trust_end = trust_balance - div_rate*annDep + levy_revenue
    # = trust_balance - dividend + levy_revenue

    return {
        "trust_start":       trust_balance,
        "ann_depreciation":  ann_dep,
        "dividend":          dividend,
        "renewal":           renewal,
        "levy_inflow":       levy_revenue,
        "guf_inflow":        guf_revenue,
        # The claim land/guf.py makes, made checkable: GUF over levy. > 1 means
        # the fee has overtaken the contracting labour base.
        "guf_over_levy":     (guf_revenue / levy_revenue
                              if levy_revenue > 0.0 else float("inf")
                              if guf_revenue > 0.0 else 0.0),
        "total_revenue":     total_revenue,
        "total_expenditure": total_expenditure,
        "surplus_deficit":   surplus_deficit,
        "solvent":           surplus_deficit >= 0.0,
        "trust_end":         trust_end,
        "trust_stable":      trust_end >= trust_balance,
        "epsilon":           epsilon,
    }


# ---------------------------------------------------------------------------
# THE INJECTION REGISTER, AND THE RULE FOR RETIRING AN ENTRY
# ---------------------------------------------------------------------------
#
# `core/` may not import outward, so anything it needs from a layer above or
# beside it arrives as a parameter. Those parameters accumulate, and by
# 2026-08-29 `fiscal_snapshot` carried nine — up from five at the first commit,
# with six of the seven added in the final three weeks of measurement work.
#
# THE GROWTH IS MOSTLY NOT THE LAYER RULE, and treating it as though it were
# leads to the wrong repair. Categorised, the nine are four different things,
# and only ONE is caused by the layer rule at all:
#
#   1 RECOMPUTE-AVOIDANCE — infra_eoh_override, eco_eoh_override
#     Not a defect: these are the FIX for two paths computing one obligation
#     and disagreeing, which they did by 92.8x before 2026-08-20. They retire
#     when the caller passes a state that already carries the resolved value.
#
#   2 UNMODELLED PHYSICAL STATE — thermal_obligation, care_stipend_aggregate
#     (was four; `capital_eoh_eliminated` and
#     `capital_personal_eoh_fulfilled_per_person` were PROMOTED to state on
#     2026-08-29 when this function learned to read the container)
#     Each is core ADMITTING it does not model something physical. This is the
#     category that grows when measurement lands, and that is healthy: the
#     parameter is a declared hypothesis, not debt. PROMOTE to `_STATE_TO_PARAM`
#     when the quantity is measured well enough to be state a civilisation has.
#     `thermal_obligation` is the live candidate — it stays a parameter only
#     while λ is bounded rather than measured.
#
#   3 CROSS-LAYER VALUE — guf_revenue
#     The only true cost of the layer rule. `land/` imports `core/`, so `core/`
#     cannot ask for a fee it is owed. DO NOT PROMOTE THIS ONE: moving it into
#     core asserts that land tenure is physics, which is a theory claim, and
#     `land/` is a separate layer precisely because it is not. It is assembled
#     one layer up instead.
#
#   4 THEORY SWITCH — health_response, standing_response
#     Partition decisions that happen to be parameters. They would exist under
#     any architecture and are not an architectural cost at all. They retire
#     when a decision is settled and the superseded branch is deleted, which is
#     a sign-off, not a refactor.
#
# THE TEST FOR PROMOTING AN ENTRY: does the measurement say core should MODEL
# this, or that another layer OWNS it? Model → promote to state. Owns → it
# stays a parameter, and the parameter is the honest record of the boundary.
# Read this list as what the model does not yet know, the same way `resolves_by`
# is read in data.py.

#: The register above, as data, so it can be CHECKED rather than merely
#: written. A prose list naming nine parameters goes stale the moment a tenth
#: is added, and this repo has found that failure often enough to know better —
#: `_DECLARED_EXEMPT` and `_INNOCUOUS_NAMES` are both checked for exactly this.
#: `tests/test_fiscal.py::TestTheInjectionRegisterIsComplete` fails if a
#: parameter is injected without being classified, so adding one is a visible
#: act in a diff rather than a silent accumulation.
INJECTION_REGISTER: dict[str, str] = {
    "infra_eoh_override":                        "recompute_avoidance",
    "eco_eoh_override":                          "recompute_avoidance",
    "thermal_obligation":                        "unmodelled_state",
    "care_stipend_aggregate":                    "unmodelled_state",
    # PROMOTED 2026-08-29, and the register caught it on its first run:
    # `capital_eoh_eliminated` and `capital_personal_eoh_fulfilled_per_person`
    # were classified here AND appear in `_STATE_TO_PARAM`, because
    # `make_economy_state` already carries both. Core no longer has to be told
    # them, so they are state, not injections. That is the promotion rule
    # executing — and it is why a quantity may not sit in both registers: two
    # routes to one value is how `psi` came to differ from `psi_applied`.
    "guf_revenue":                               "cross_layer",
    "health_response":                           "theory_switch",
    "standing_response":                         "theory_switch",
}

#: Which categories may be promoted into `_STATE_TO_PARAM` when a measurement
#: lands, and which may not. `cross_layer` is excluded on purpose: promoting
#: `guf_revenue` would assert that land tenure is physics.
PROMOTABLE_CATEGORIES: frozenset[str] = frozenset(
    {"unmodelled_state", "recompute_avoidance"}
)

#: The economy-state keys `fiscal_snapshot` can read, mapped to its own
#: parameter names. `make_economy_state()` in core/simulation.py already carries
#: every one of them — the container existed before this function accepted it.
#: Only two names differ, and both differences are historical rather than
#: meaningful.
_STATE_TO_PARAM: dict[str, str] = {
    "trust_balance":                  "trust_balance",
    "labor_income_teh":               "labor_income",
    "capital_stock_teh":              "capital_stock_teh",
    "capital_age_ratio":              "capital_age_ratio",
    "population":                     "population",
    "epsilon":                        "epsilon",
    "ecosystem_health":               "ecosystem_health",
    "deferred_ecological":            "deferred_ecological",
    "capital_eoh_eliminated":         "capital_eoh_eliminated",
    "capital_personal_eoh_fulfilled": "capital_personal_eoh_fulfilled_per_person",
}


def fiscal_snapshot(
    trust_balance: float | None = None,
    labor_income: float | None = None,
    capital_stock_teh: float | None = None,
    capital_age_ratio: float | None = None,
    population: float | None = None,
    epsilon: float | None = None,
    levy_rates: dict[str, float] | None = None,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    floor_fraction: float = 0.15,
    meaningful_activity_teh: float = MEANINGFUL_ACTIVITY_TEH_BASE,
    meaningful_activity_scale: float = MEANINGFUL_ACTIVITY_TEH_SCALE,
    capital_personal_eoh_fulfilled_per_person: float = 0.0,
    capital_eoh_eliminated: float = 0.0,
    infra_eoh_override: float | None = None,
    ecosystem_health: float = 0.70,
    deferred_ecological: float = 0.0,
    eco_eoh_override: float | None = None,
    care_stipend_aggregate: float = 0.0,
    thermal_obligation: float = 0.0,
    ecological_area_hectares: float | None = None,
    ecological_hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
    ecological_intensity: float = ECOLOGICAL_INTENSITY_BASE,
    health_response: str = "guf",
    standing_response: str = "guf",
    guf_revenue: float = 0.0,
    state: dict | None = None,
) -> dict:
    """
    Compute full fiscal balance for one period from first principles.

    Assembles levy_collection → stewardship_allocation → sufficiency_guarantee
    → trust_management into a single coherent snapshot. This is the fiscal
    analog of conditions.dashboard_snapshot() — it answers: is the Trust
    solvent and are all obligations funded?

    Args:
        trust_balance: Trust balance at period start.
        labor_income: Total TEH earned by workers this period.
        capital_stock_teh: Capital stock in TEH (for stewardship sizing).
        capital_age_ratio: Mean asset age ratio.
        population: Total population.
        epsilon: Automation level.
        levy_rates: Dict of levy rates. Defaults to {"sufficiency": 0.0125}.
        mean_multiplier: Mean workforce multiplier.
        dep_rate: Trust depreciation rate.
        div_rate: Trust dividend fraction.
        floor_fraction: Fraction of population receiving the guarantee.
        meaningful_activity_teh: Discretionary spending bonus at ε=0.
        meaningful_activity_scale: Quadratic ε-growth factor for the bonus.
        capital_personal_eoh_fulfilled_per_person: Per-person personal EOH
            already fulfilled by the capital stock. Passed through to
            sufficiency_guarantee() to reduce the reimbursement component.
        capital_eoh_eliminated: Aggregate EOH eliminated by the capital stock
            (sum of annual_eoh_eliminated across all assets). When provided,
            the Trust is automatically sized against the reduced infrastructure
            EOH — keeping fiscal sizing consistent with the EOH ledger. For
            full accuracy across all domains, pass infra_eoh_override directly
            from total_eoh(..., capital_eoh_eliminated=X)["infrastructure"].
        infra_eoh_override: Pre-computed infrastructure EOH with elimination
            already applied. Takes precedence over capital_eoh_eliminated when
            both are provided. Use when the caller has already run total_eoh().
        ecosystem_health: Ecosystem state ∈ [0, 1] for ecological allocation.
            Default 0.70 (above crisis threshold, moderate degradation).
        deferred_ecological: Accumulated deferred ecological EOH (hours).
            Passed through to ecological_eoh() if eco_eoh_override is None.
        eco_eoh_override: Pre-computed ecological EOH from total_eoh()["ecological"].
            Pass this whenever the caller has already run total_eoh() — otherwise
            ecological_eoh() is recomputed internally. Same pattern as infra_eoh_override.

    Solvency identity (Trust is solvent when):

        levy_inflow + Trust_dividend ≥ stewardship + ecological + guarantee + care_stipend

    Trust dynamics each period:
        Trust_end = Trust_start − depreciation(dep_rate) − dividend(div_rate) + levy_inflow

    As ε rises from 0 to 1, labor_income falls (machines do more), levy_inflow
    falls with it, but guarantee_cost also falls (capital fulfills personal EOH),
    creating a long-run fiscal equilibrium — provided Trust grew large enough
    during mid-arc to fund obligations through dividend alone.

    Worked example at ε=0.40 (population=1M, Trust=35B TEH, labor_income=494M TEH):
        levy_inflow     =   6.2M TEH  (494M × 1.25% suff_levy)
        stewardship     = 282M TEH    (capital stock infrastructure obligation)
        ecological      =   0.9M TEH  (healthy ecosystem)
        guarantee       = 307M TEH    (130K recipients × 2,361 TEH/person)
        trust_dividend  = 630M TEH    (35B × 4.5% dep × 40% div)
        surplus_deficit =  46.6M TEH  → solvent=True; trust_stable=False (Trust eroding)

    Returns:
        dict with "levies", "stewardship", "ecological", "guarantee", "trust",
        and "solvent" (bool) at top level.

    Reference: Mission Statement §"Principle 8 — Every claim should be
    verifiable by running a function."
    """
    # ---- state resolution -------------------------------------------------
    #
    # `core/` HAS CARRIED A STATE CONTAINER SINCE THE FIRST COMMIT AND THIS
    # FUNCTION DID NOT ACCEPT IT. `make_economy_state()` holds ten of the
    # quantities below, and `simulate_period` was unpacking it into nineteen
    # loose keyword arguments to make this call. Every unpack is a place two
    # paths can disagree, which is exactly how the ecological frame came to
    # differ by 92.8x between the pipeline and this function.
    #
    # SUPPLYING BOTH A STATE AND THE SAME QUANTITY LOOSE IS REFUSED, not
    # silently resolved. `total_eoh` refuses `ecological_base` alongside
    # `area_hectares` for the same reason, and `research/exchange.build_
    # collective` refuses kwargs that restate a frame: a state that can be
    # overridden piecemeal is not a state, and a caller who believes an
    # argument is in force when it is not is the silently-ignored-parameter
    # failure this repo keeps finding.
    #
    # A state is a snapshot of ONE economy at ONE moment. `simulate_period`
    # evolves its state and passes the evolved one, which is why this reads
    # whatever it is given rather than any notion of "the" state.
    if state is not None:
        _given = {
            "trust_balance": trust_balance, "labor_income": labor_income,
            "capital_stock_teh": capital_stock_teh,
            "capital_age_ratio": capital_age_ratio,
            "population": population, "epsilon": epsilon,
            "ecosystem_health": ecosystem_health if ecosystem_health != 0.70 else None,
            "deferred_ecological": deferred_ecological or None,
            "capital_eoh_eliminated": capital_eoh_eliminated or None,
            "capital_personal_eoh_fulfilled_per_person":
                capital_personal_eoh_fulfilled_per_person or None,
        }
        _clash = sorted(
            param for key, param in _STATE_TO_PARAM.items()
            if key in state and _given.get(param) is not None
        )
        if _clash:
            raise ValueError(
                f"these are the state's to supply, not the caller's: {_clash}. "
                "Build a different state instead of overriding one — a state "
                "that can be overridden piecemeal is not a state."
            )
        _resolved = {param: state[key] for key, param in _STATE_TO_PARAM.items()
                     if key in state}
        trust_balance = _resolved.get("trust_balance", trust_balance)
        labor_income = _resolved.get("labor_income", labor_income)
        capital_stock_teh = _resolved.get("capital_stock_teh", capital_stock_teh)
        capital_age_ratio = _resolved.get("capital_age_ratio", capital_age_ratio)
        population = _resolved.get("population", population)
        epsilon = _resolved.get("epsilon", epsilon)
        ecosystem_health = _resolved.get("ecosystem_health", ecosystem_health)
        deferred_ecological = _resolved.get("deferred_ecological", deferred_ecological)
        capital_eoh_eliminated = _resolved.get(
            "capital_eoh_eliminated", capital_eoh_eliminated)
        capital_personal_eoh_fulfilled_per_person = _resolved.get(
            "capital_personal_eoh_fulfilled_per_person",
            capital_personal_eoh_fulfilled_per_person)

    # Written as an explicit disjunction rather than a computed list so the
    # type narrows past it: after this, the six are floats whatever route
    # supplied them, and the rest of the body is identical to what it was
    # before `state=` existed.
    if (trust_balance is None or labor_income is None
            or capital_stock_teh is None or capital_age_ratio is None
            or population is None or epsilon is None):
        _missing = sorted(n for n, v in (
            ("trust_balance", trust_balance), ("labor_income", labor_income),
            ("capital_stock_teh", capital_stock_teh),
            ("capital_age_ratio", capital_age_ratio),
            ("population", population), ("epsilon", epsilon),
        ) if v is None)
        raise ValueError(
            f"missing required quantities: {_missing}. Supply them directly or "
            "pass a `state=` carrying them (see make_economy_state)."
        )

    if levy_rates is None:
        levy_rates = {"sufficiency": SUFF_LEVY_RATE}

    # Auto-compute infra_eoh_override when capital_eoh_eliminated is set and
    # no explicit override was provided. Applies elimination proportionally
    # using infrastructure as the non-personal base (conservative approximation;
    # for exact multi-domain proportional reduction pass infra_eoh_override
    # from total_eoh(..., capital_eoh_eliminated=...)["infrastructure"]).
    if capital_eoh_eliminated > 0.0 and infra_eoh_override is None:
        raw_infra = infrastructure_eoh(
            capital_stock=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            epsilon=epsilon,
        )
        reduction_factor  = max(0.0, 1.0 - capital_eoh_eliminated / max(raw_infra, 1.0))
        infra_eoh_override = raw_infra * reduction_factor

    levies    = levy_collection(labor_income, levy_rates)
    stew      = stewardship_allocation(capital_stock_teh, capital_age_ratio,
                                       epsilon, trust_balance, mean_multiplier,
                                       infra_eoh_override=infra_eoh_override)
    # Both stewardship and ecological draw from the full Trust balance independently.
    # They are co-equal stewardship obligations — neither has priority over the other.
    # trust_management() sees their combined expenditure and determines solvency.
    # THE FRAME. fiscal_snapshot scales the guarantee, the levy base and the
    # stewardship obligation with `population`, so its ecological term must rest
    # on the SAME jurisdiction. Until 2026-08-20 it did not: it called
    # ecological_allocation() with no frame at all, so the ecological
    # requirement silently resolved to ECOLOGICAL_BASE_RATE — the obligation for
    # the whole contiguous US — whatever population was passed. This is the
    # fifth instance of the defect Phase 4b closed in `total_eoh`, and the first
    # one sitting on the documented institutional intake path: the
    # implementation guide's own worked example calls this function, and running
    # it verbatim disagreed with its own pipeline call by 92.8×.
    #
    # Resolution is the same as `total_eoh`'s and deliberately so — two entry
    # points into one obligation must not resolve it two ways.
    eco_area = ecological_area_hectares
    if eco_eoh_override is None and eco_area is None:
        eco_area = population * ecological_hectares_per_capita
    eco       = ecological_allocation(
        ecosystem_health=ecosystem_health,
        epsilon=epsilon,
        available_teh=trust_balance,
        mean_multiplier=mean_multiplier,
        deferred=deferred_ecological,
        eco_eoh_override=eco_eoh_override,
        thermal_obligation=thermal_obligation,
        area_hectares=eco_area,
        intensity=ecological_intensity,
        health_response=health_response,
        standing_response=standing_response,
    )
    guarantee = sufficiency_guarantee(
        population, epsilon,
        meaningful_activity_teh=meaningful_activity_teh,
        meaningful_activity_scale=meaningful_activity_scale,
        floor_fraction=floor_fraction,
        capital_personal_eoh_fulfilled_per_person=capital_personal_eoh_fulfilled_per_person,
    )
    # new-15: care stipend is care-labor compensation from the Trust — co-equal
    # with stewardship and ecological as a structural obligation, distinct from
    # the sufficiency guarantee (which is a floor, not labor compensation).
    trust     = trust_management(
        trust_balance, levies["total_levied"],
        stew["teh_allocated"] + eco["teh_allocated"] + care_stipend_aggregate,
        guarantee["total_cost_teh"],
        dep_rate, div_rate, epsilon,
        guf_revenue=guf_revenue,
    )

    # THE PARTITION'S OWN QUESTION, NOW ANSWERABLE (2026-08-29).
    #
    # Phases 4e/4f moved the recurring ecological obligation out of this
    # snapshot's ecological allocation and assigned it to the Ground Use Fee.
    # Until GUF revenue reached this function there was no way to ask whether
    # the fee actually covers what was moved to it — the obligation left one
    # side of the ledger and arrived nowhere. That gap is what this block
    # closes.
    #
    # `obligation` is the relocated ecological requirement in TEH. It is a LOWER
    # BOUND on what GUF must fund, not the whole of it: the fee also carries the
    # SERVICING cost of the built environment (scenarios/servicing_census
    # measures 45.92 h/ha·yr over 37.1 Mha), which this snapshot has no inventory
    # for. So `covered` being True means "GUF covers the part that left the
    # ecological domain", never "GUF is adequately sized".
    _guf_obligation = float(eco.get("relocated_teh_required", 0.0))
    _guf_gap = max(0.0, _guf_obligation - guf_revenue)
    guf = {
        "revenue":           guf_revenue,
        "obligation":        _guf_obligation,
        "coverage":          (guf_revenue / _guf_obligation
                              if _guf_obligation > 0.0 else None),
        "gap":               _guf_gap,
        "covered":           _guf_gap <= 0.0,
        "obligation_is_a_lower_bound": True,
        "note": (
            "obligation = the recurring ecological requirement relocated out of "
            "the domain by Phases 4e/4f. It EXCLUDES the servicing cost of the "
            "built environment, which GUF also carries and which this snapshot "
            "has no parcel inventory for — so `covered` is necessary, not "
            "sufficient. Supply guf_revenue from land/collective.compute_"
            "collective_guf()['guf_net_inflow']."
        ),
        # DO NOT READ A LARGE `coverage` AS "GUF IS WELL SIZED". The denominator
        # is the relocated ECOLOGICAL obligation alone, which the domain-balance
        # work has repeatedly found to be tiny — on the shipped urban archetype
        # it is ~0.34 TEH/yr against ~348,000 TEH/yr of fee, a ratio of ~1e6
        # that says almost nothing about the fee and almost everything about the
        # obligation. Set against the SERVICING census instead (the other half
        # of what GUF carries, and the larger one), the same archetype reads
        # ~21x over — consistent with the 18.1x urban overshoot
        # scenarios/servicing_census measured independently. That is the
        # comparison with information in it, and this snapshot cannot make it
        # without a parcel inventory.
        "verdict": (
            f"GUF revenue {guf_revenue:,.0f} TEH/yr against a relocated "
            f"ecological obligation of {_guf_obligation:,.2f} TEH/yr. The "
            f"obligation is a LOWER BOUND — it excludes the servicing cost of "
            f"the built environment — and it is small for the reason the "
            f"domain-balance work records, so a large coverage figure here is "
            f"evidence about the obligation, not about the fee. Run "
            f"`eoh scenario run servicing_census` for the comparison that "
            f"constrains the fee's magnitude."
            if _guf_obligation > 0.0 else
            "no relocated ecological obligation at this configuration — either "
            "the pre-partition policy is in force (nothing was relocated) or "
            "the collective stewards no land."
        ),
    }

    return {
        "guf":              guf,
        "levies":           levies,
        "stewardship":      stew,
        "ecological":       eco,
        "guarantee":        guarantee,
        "care_stipend":     care_stipend_aggregate,
        "trust":            trust,
        "solvent":          trust["solvent"],
        "epsilon":          epsilon,
    }


# ===========================================================================
# Care Labor Compensation
# ===========================================================================

# Age bracket weights for care stipend (normalized to infant = 1.0)
CARE_AGE_BRACKETS: list[dict] = [
    {"min_age": 0,  "max_age": 2,  "weight": 1.00, "label": "infant"},
    {"min_age": 3,  "max_age": 5,  "weight": 0.90, "label": "toddler"},
    {"min_age": 6,  "max_age": 11, "weight": 0.60, "label": "school-age"},
    {"min_age": 12, "max_age": 17, "weight": 0.30, "label": "adolescent"},
    {"min_age": 18, "max_age": 999,"weight": 0.00, "label": "adult (not covered)"},
]

# Diminishing scale factors for multiple dependents (per-dependent multiplier)
# 1st dependent: full rate. Each additional dependent: lower marginal rate.
DEPENDENT_SCALE: list[float] = [1.00, 0.80, 0.65, 0.50]   # index = 0-based position

# Per-provider cap: PROVIDER_CAP_EQUIVALENTS migrated to data.py 2026-08-28.


def _age_weight(age: int) -> float:
    """Return the EOH weight for a dependent of a given age."""
    for bracket in CARE_AGE_BRACKETS:
        if bracket["min_age"] <= age <= bracket["max_age"]:
            return bracket["weight"]
    return 0.0


def care_stipend(
    dependents: list[int],
    epsilon: float = 0.40,
    base_infant_stipend: float = 200.0,
    policy_params: dict | None = None,
) -> dict:
    """
    Compute TEH compensation for registered care labor.

    Care labor (raising children, tending dependents) is registered in the
    collective ledger and compensated through a stipend. The EOH registered
    per dependent is a function of automation: at ε=0, all care is manual
    and per-child EOH is highest; as automation rises, physical care EOH
    declines while relational/emotional care EOH persists.

    Anti-gaming structure:
    1. Fixed per-age-bracket rates (not based on claimed hours — prevents inflation)
    2. Diminishing returns for multiple dependents (prevents unlimited expansion)
    3. Per-provider cap (prevents one provider claiming unlimited children)
    4. Age limits (adults are not covered; they have their own EOH and capacity)
    5. ε floor: even at full automation, 15% base rate covers relational care
       that machines cannot replace (Mission Statement: care is the system's
       "deepest and most permanent function")

    Args:
        dependents: List of dependent ages (integers). Each entry is one dependent.
                    Ages outside covered brackets (≥18) contribute zero stipend.
        epsilon: Automation level. Per-dependent stipend scales down with ε.
        base_infant_stipend: Annual TEH for a registered infant at ε=0. Default: 200.
        policy_params: Optional dict to override defaults:
                       {"provider_cap_equivalents": float,
                        "dependent_scale": list[float],
                        "automation_floor": float}

    Returns:
        dict: {
          "dependents_count":   int,
          "covered_count":      int,    (age < 18)
          "per_dependent":      list[dict],   (age, weight, raw_stipend, scaled_stipend)
          "raw_total":          float,  (before diminishing returns + cap)
          "after_diminishing":  float,  (after per-dependent scale factors)
          "capped_total":       float,  (after per-provider cap)
          "epsilon_adjusted":   float,  (final annual stipend in TEH)
          "automation_factor":  float,  (fraction of base rate at this ε)
          "provider_cap_teh":   float,
          "cap_applied":        bool,
        }

    Reference: Mission Statement §"Care labor policy requires further modeling.
    Diminishing stipend per dependent child up to a defined maximum per care
    provider ... The registered EOH per dependent is itself a function of
    automation."
    """
    params = policy_params or {}
    cap_equiv  = params.get("provider_cap_equivalents", PROVIDER_CAP_EQUIVALENTS)
    dep_scale  = params.get("dependent_scale", DEPENDENT_SCALE)
    auto_floor = params.get("automation_floor", CARE_AUTOMATION_FLOOR)

    # ε scaling: physical care declines with automation; relational care floors
    # At ε=0: full rate. At ε=1: auto_floor (15% for relational/emotional care).
    automation_factor = auto_floor + (1.0 - auto_floor) * (1.0 - epsilon)

    # Provider cap in TEH
    provider_cap_teh = base_infant_stipend * cap_equiv * automation_factor

    # Per-dependent computation
    per_dependent_details = []
    covered = [age for age in dependents if age < 18]

    for i, age in enumerate(dependents):
        weight      = _age_weight(age)
        scale_factor = dep_scale[i] if i < len(dep_scale) else dep_scale[-1]
        raw_stipend  = base_infant_stipend * weight           # before any scaling
        scaled_stipend = raw_stipend * scale_factor          # after diminishing returns

        per_dependent_details.append({
            "age":           age,
            "weight":        weight,
            "position":      i + 1,
            "scale_factor":  scale_factor,
            "raw_stipend":   raw_stipend,
            "scaled_stipend": scaled_stipend,
            "covered":       weight > 0,
        })

    raw_total         = sum(d["raw_stipend"] for d in per_dependent_details)
    after_diminishing = sum(d["scaled_stipend"] for d in per_dependent_details)

    # Apply per-provider cap (before ε adjustment, since cap is in base units)
    cap_in_base       = provider_cap_teh / automation_factor if automation_factor > 0 else provider_cap_teh
    after_cap         = min(after_diminishing, cap_in_base)
    cap_applied       = after_diminishing > cap_in_base

    # Apply ε adjustment (automation reduces human-labor component of care EOH)
    epsilon_adjusted  = after_cap * automation_factor

    return {
        "dependents_count":   len(dependents),
        "covered_count":      len(covered),
        "per_dependent":      per_dependent_details,
        "raw_total":          raw_total,
        "after_diminishing":  after_diminishing,
        "capped_total":       after_cap,
        "epsilon_adjusted":   epsilon_adjusted,
        "automation_factor":  automation_factor,
        "provider_cap_teh":   provider_cap_teh,
        "cap_applied":        cap_applied,
    }


def aggregate_care_stipend_from_demographics(
    population: float,
    epsilon: float,
    infant_fraction: float = 0.05,
    child_fraction: float = 0.15,
    avg_dependents_per_carer: float = 1.5,
    base_infant_stipend: float = 200.0,
) -> float:
    """
    Approximate aggregate care stipend from population-level demographics.

    Bridges the gap between care_stipend() (per-household) and the aggregate
    simulation (population-level). Uses the population's infant and child
    fractions to estimate the number of active care providers, then scales a
    representative household stipend to the full population.

    Representative household: mix of infants (age 1) and school-age children
    (age 8) in proportion to avg_dependents_per_carer. This approximates the
    true age distribution within covered households.

    Args:
        population: Total population.
        epsilon: Automation level. Passed to care_stipend() for ε-adjustment.
        infant_fraction: Fraction of population in infant age group (0–2 yrs).
            Default: 0.05 (canonical arc ε=0.40 value).
        child_fraction: Fraction of population in child age group (3–17 yrs).
            Default: 0.15.
        avg_dependents_per_carer: Average number of dependents per registered
            care provider. Drives the diminishing-returns computation.
            Default: 1.5 (one primary + partial-time second dependent).
        base_infant_stipend: Per-year TEH for a registered infant at ε=0.

    Returns:
        Total aggregate care stipend (TEH/year) across all care providers.

    Reference: Mission Statement §"Care labor policy requires further modeling"
    — aggregate wiring uses a representative-household approximation until
    full demographic simulation is implemented.
    """
    child_count  = population * (infant_fraction + child_fraction)
    carer_count  = child_count / max(avg_dependents_per_carer, 1.0)
    n_deps       = max(1, round(avg_dependents_per_carer))
    # Representative dependent ages: infants dominate at low n, mix at higher n
    n_infants    = (n_deps + 1) // 2
    n_school_age = n_deps - n_infants
    rep_deps     = [1] * n_infants + [8] * n_school_age
    rep_stipend  = care_stipend(rep_deps, epsilon, base_infant_stipend)["epsilon_adjusted"]
    return carer_count * rep_stipend


# ===========================================================================
# Land and Stewardship EOH
# ===========================================================================

def steward_eoh_obligation(
    structure_value_teh: float,
    land_area_units: float,
    epsilon: float = 0.40,
    structure_maint_rate: float = 0.020,
    collective_registration_share: float | None = None,
) -> dict:
    """
    Compute private EOH borne by a land steward for the structures they use.

    Land belongs to the collective (assigned via leasehold deeds). Structures
    built on that land generate infrastructure EOH that falls to the assigned
    steward to manage, maintaining a home is a private stewardship obligation.
    This EOH is NOT in the collective ledger; it does not generate TEH for the
    steward. It is a private zero event (like household maintenance).

    In the final stages of automation, as the collective approaches full EOH
    coverage, housing and land-based EOH may be registered to the collective
    ledger, zeroing out remaining private obligations. This transition is
    modeled by collective_land_registration().

    Args:
        structure_value_teh: TEH value of structures on the parcel.
        land_area_units: Size of land parcel (in any consistent unit).
        epsilon: Automation level. At very high ε, more transitions collective.
        structure_maint_rate: Annual maintenance EOH as fraction of structure value.
        collective_registration_share: Fraction of structure EOH transferred to
                                       collective ledger. If None, computed via
                                       collective_land_registration(epsilon).

    Returns:
        dict: {
          "total_structure_eoh":       float,    (annual EOH from structure)
          "collective_share":          float,    (fraction now collective)
          "private_eoh_obligation":    float,    (steward bears this privately)
          "collective_eoh_registered": float,    (entered the collective ledger)
          "is_fully_private":          bool,     (collective_share = 0)
          "is_fully_collective":       bool,     (collective_share = 1)
          "epsilon":                   float,
        }

    Reference: Mission Statement §"Land is held by the collective ... maintaining
    a home is a private stewardship obligation. In the final stages of automation,
    as the system approaches full EOH coverage, housing and land-based EOH may
    be registered to the collective ledger."
    """
    if collective_registration_share is None:
        collective_registration_share = collective_land_registration(epsilon)

    total_eoh   = structure_value_teh * structure_maint_rate
    coll_eoh    = total_eoh * collective_registration_share
    private_eoh = total_eoh * (1.0 - collective_registration_share)

    return {
        "total_structure_eoh":       total_eoh,
        "collective_share":          collective_registration_share,
        "private_eoh_obligation":    private_eoh,
        "collective_eoh_registered": coll_eoh,
        "is_fully_private":          collective_registration_share < 0.001,
        "is_fully_collective":       collective_registration_share > 0.999,
        "land_area_units":           land_area_units,
        "epsilon":                   epsilon,
    }


def collective_land_registration(
    epsilon: float,
    inflection: float = 0.85,
    rate: float = 22.0,
    saturation: float = 0.90,
) -> float:
    """
    Fraction of housing/land EOH registered to the collective ledger.

    The transition of land/housing EOH from private to collective begins very
    late in the automation arc. Below the inflection point, nearly all housing
    EOH remains a private stewardship obligation. As the collective approaches
    full EOH coverage, it absorbs remaining private obligations, zeroing out
    stewards' private maintenance burden and bringing all entropy resistance
    under the ledger.

    This is a late-stage sigmoid, distinct from the care admission curve:
    - Care registration: inflection at ε=0.45 (mid-automation)
    - Land registration: inflection at ε=0.85 (near post-scarcity)

    Args:
        epsilon: Automation level [0.0, 0.99].
        inflection: ε at which transition is fastest. Default: 0.85.
        rate: Steepness of sigmoid. Default: 22.0 (sharp transition).
        saturation: Maximum collective share. Default: 0.90.

    Returns:
        Collective land registration share ∈ [0.0, saturation].
        Monotonically increasing.

    Reference: Mission Statement §"In the final stages of automation ... housing
    and land-based EOH may be registered to the collective ledger, zeroing out
    all remaining private EOH obligations."
    """
    sigmoid = 1.0 / (1.0 + math.exp(-rate * (epsilon - inflection)))
    return saturation * sigmoid


# ---------------------------------------------------------------------------
# Stewardship dividend adequacy check
# ---------------------------------------------------------------------------

def stewardship_dividend_needed(
    stewardship_teh_required: float,
    dep_rate: float,
    trust_balance: float,
) -> dict:
    """
    Minimum div_rate needed for the Trust dividend to cover stewardship cost.

    The Trust dividend = trust_balance × dep_rate × div_rate. If the current
    dividend is less than stewardship_teh_required, the Trust will draw down
    over time (levy revenue covers the rest, but at the expense of the guarantee
    or solvency). This function computes the minimum div_rate for self-sufficiency.

    A min_div_rate > 1.0 is infeasible (cannot distribute more than 100% of
    depreciation) — this signals the Trust balance itself must grow (higher
    levy inflows or lower stewardship cost).

    Args:
        stewardship_teh_required: Annual stewardship TEH needed (from stewardship_allocation()).
        dep_rate: Trust's annual depreciation rate (from trust_management() dep_rate).
        trust_balance: Current Trust balance in TEH.

    Returns:
        dict: {
          "stewardship_teh_required": float,
          "annual_dep":               float,   (= trust_balance × dep_rate)
          "min_div_rate":             float | None,   (None if Trust is empty)
          "trust_balance":            float,
          "dep_rate":                 float,
          "feasible":                 bool,    (min_div_rate ≤ 1.0)
          "shortfall_at_div1":        float,   (gap if div_rate were set to 1.0)
        }

    Reference: Mission Statement §"Principle 2 — The fiscal architecture must
    remain solvent under any automation level"; §"Revenue streams pegged to the
    capital stock's entropy obligations are foundational."
    """
    ann_dep = trust_balance * dep_rate

    if ann_dep <= 0.0:
        return {
            "stewardship_teh_required": stewardship_teh_required,
            "annual_dep":               ann_dep,
            "min_div_rate":             None,
            "trust_balance":            trust_balance,
            "dep_rate":                 dep_rate,
            "feasible":                 False,
            "shortfall_at_div1":        stewardship_teh_required,
        }

    min_div_rate   = stewardship_teh_required / ann_dep
    feasible       = min_div_rate <= 1.0
    shortfall_div1 = max(0.0, stewardship_teh_required - ann_dep)

    return {
        "stewardship_teh_required": stewardship_teh_required,
        "annual_dep":               ann_dep,
        "min_div_rate":             min_div_rate,
        "trust_balance":            trust_balance,
        "dep_rate":                 dep_rate,
        "feasible":                 feasible,
        "shortfall_at_div1":        shortfall_div1,
    }

# ---------------------------------------------------------------------------
# Multi-period Trust solvency trajectory
# ---------------------------------------------------------------------------

def trust_solvency_trajectory(
    initial_trust_balance: float,
    n_periods: int = 50,
    levy_revenue_per_period: float = 0.0,
    stewardship_cost_per_period: float | None = None,
    guarantee_cost_per_period: float | None = None,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    epsilon: float = 0.40,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    population: float = 1_000_000.0,
    solvency_floor: float | None = None,
) -> dict:
    """
    Simulate Trust balance across N periods and assess long-run solvency.

    trust_management() is correct for one period but gives no signal about
    trajectory. A Trust earning less from levies than it pays in dividends
    burns down slowly — imperceptible period-to-period but a structural failure
    over decades. This function makes that trajectory explicit.

    If stewardship_cost_per_period or guarantee_cost_per_period are None,
    they are computed once from stewardship_allocation() and
    sufficiency_guarantee() at the given epsilon (treated as constant
    across all periods — for varying costs, pass explicit values).

    Args:
        initial_trust_balance: Trust balance at period 0.
        n_periods: Number of periods to simulate.
        levy_revenue_per_period: Total levy revenue each period (TEH).
        stewardship_cost_per_period: Fixed stewardship cost each period.
                                     None → auto-compute from capital/epsilon.
        guarantee_cost_per_period: Fixed guarantee cost each period.
                                   None → auto-compute from population/epsilon.
        dep_rate: Trust depreciation rate (same each period).
        div_rate: Trust dividend fraction (same each period).
        epsilon: Automation level (used for auto-cost computation).
        capital_stock_teh: Capital stock for stewardship auto-computation.
        capital_age_ratio: Asset age for stewardship auto-computation.
        population: Population for guarantee auto-computation.
        solvency_floor: Minimum acceptable Trust balance (TEH). If None,
                        defaults to one period's dividend (can't pay out less
                        than one dividend cycle).

    Returns:
        dict: {
          "periods":              list[dict],   (per-period balance + surplus/deficit)
          "solvent_throughout":   bool,
          "first_insolvency":     int | None,   (period number; None if always solvent)
          "final_balance":        float,
          "min_balance":          float,
          "total_levy_inflow":    float,
          "total_expenditure":    float,
          "trend":                str,   ("GROWING", "STABLE", "DECLINING", "INSOLVENT")
          "years_to_insolvency":  float | None,  (extrapolated; None if solvent)
          "solvency_floor":       float,
        }

    Reference: Mission Statement §"Principle 2 — The fiscal architecture must
    remain solvent under any automation level"; §"The Trust must be maintained
    across the full automation arc."
    """
    # Auto-compute period costs if not provided
    if stewardship_cost_per_period is None:
        stew_result = stewardship_allocation(
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            epsilon=epsilon,
            available_teh=initial_trust_balance,
        )
        stewardship_cost_per_period = stew_result["teh_allocated"]

    if guarantee_cost_per_period is None:
        guar_result = sufficiency_guarantee(population=population, epsilon=epsilon)
        guarantee_cost_per_period = guar_result["total_cost_teh"]

    # Default solvency floor: one period's dividend
    initial_ann_dep = initial_trust_balance * dep_rate
    if solvency_floor is None:
        solvency_floor = initial_ann_dep * div_rate

    balance           = initial_trust_balance
    periods           = []
    first_insolvency  = None
    total_levy_inflow = 0.0
    total_expenditure = 0.0

    for period in range(n_periods):
        result = trust_management(
            trust_balance=balance,
            levy_revenue=levy_revenue_per_period,
            stewardship_cost=stewardship_cost_per_period,
            guarantee_cost=guarantee_cost_per_period,
            dep_rate=dep_rate,
            div_rate=div_rate,
            epsilon=epsilon,
        )

        balance = result["trust_end"]
        solvent_this_period = balance >= solvency_floor

        if not solvent_this_period and first_insolvency is None:
            first_insolvency = period

        periods.append({
            "period":         period,
            "trust_start":    result["trust_start"],
            "trust_end":      balance,
            "dividend":       result["dividend"],
            "levy_inflow":    levy_revenue_per_period,
            "surplus_deficit": result["surplus_deficit"],
            "solvent":        solvent_this_period,
        })

        total_levy_inflow += levy_revenue_per_period
        total_expenditure += result["total_expenditure"]

    solvent_throughout = first_insolvency is None
    final_balance      = periods[-1]["trust_end"] if periods else initial_trust_balance
    min_balance        = min(p["trust_end"] for p in periods) if periods else initial_trust_balance

    # Trend: compare first-half average surplus to second-half
    if len(periods) >= 4:
        mid = len(periods) // 2
        early_surplus = sum(p["surplus_deficit"] for p in periods[:mid]) / mid
        late_surplus  = sum(p["surplus_deficit"] for p in periods[mid:]) / (len(periods) - mid)
        if first_insolvency is not None:
            trend = "INSOLVENT"
        elif early_surplus > 0 and late_surplus > 0:
            trend = "GROWING"
        elif abs(early_surplus) < initial_trust_balance * 0.001:
            trend = "STABLE"
        else:
            trend = "DECLINING"
    else:
        trend = "INSOLVENT" if first_insolvency is not None else "STABLE"

    # Extrapolate years-to-insolvency from trajectory slope
    years_to_insolvency: float | None = None
    if not solvent_throughout and first_insolvency is not None:
        years_to_insolvency = float(first_insolvency)
    elif final_balance < initial_trust_balance:
        # Linearly extrapolate from current decline rate
        decline_per_period = (initial_trust_balance - final_balance) / max(n_periods, 1)
        if decline_per_period > 0.0:
            years_to_insolvency = (final_balance - solvency_floor) / decline_per_period

    return {
        "periods":             periods,
        "solvent_throughout":  solvent_throughout,
        "first_insolvency":    first_insolvency,
        "final_balance":       final_balance,
        "min_balance":         min_balance,
        "total_levy_inflow":   total_levy_inflow,
        "total_expenditure":   total_expenditure,
        "trend":               trend,
        "years_to_insolvency": years_to_insolvency,
        "solvency_floor":      solvency_floor,
    }


# ---------------------------------------------------------------------------
# Inverse solvency query
# ---------------------------------------------------------------------------

def min_levy_for_solvency(
    trust_balance: float,
    epsilon: float = 0.40,
    dep_rate: float = DEP_RATE,
    div_rate: float = DIV_RATE,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    population: float = 1_000_000.0,
    stewardship_teh: float | None = None,
    guarantee_teh: float | None = None,
    labor_income: float | None = None,
) -> dict:
    """
    Minimum levy revenue needed to keep the Trust solvent and stable.

    This is the backward query that trust_solvency_trajectory() cannot answer:
    given a Trust balance and cost structure, what levy inflow is required to
    (a) cover expenditures from the dividend, and (b) keep the trust balance
    non-declining?

    Three solvency targets are returned:

    cover_expenditures:
        levy ≥ max(0, expenditure − dividend).
        The dividend funds as much of stewardship + guarantee as it can;
        the levy covers the remainder. Trust balance still declines.

    stable_trust:
        levy ≥ dividend.
        The levy replaces the dividend paid out so the trust balance holds flat.
        Does not require covering all expenditures from levy alone.

    full_solvency:
        levy ≥ max(dividend, expenditure − dividend).
        The union: trust stays flat AND all expenditures are covered.

    If labor_income is provided, each levy target is also expressed as a rate
    (fraction of labor income). Rates > 1.0 indicate infeasible targets.

    Args:
        trust_balance: Current Trust balance (TEH).
        epsilon: Automation level — used for auto-computing costs.
        dep_rate: Trust depreciation rate.
        div_rate: Dividend fraction of depreciation.
        capital_stock_teh: Capital stock for stewardship auto-computation.
        capital_age_ratio: Asset age for stewardship auto-computation.
        population: Population for guarantee auto-computation.
        stewardship_teh: Override for stewardship cost. None → auto-compute.
        guarantee_teh: Override for guarantee cost. None → auto-compute.
        labor_income: Total labor income this period — used to compute levy rates.
                      None → rates not included in result.

    Returns:
        dict: {
          "trust_balance":          float,
          "dividend":               float,   (= trust × dep_rate × div_rate)
          "stewardship_cost":       float,
          "guarantee_cost":         float,
          "total_expenditure":      float,
          "current_surplus":        float,   (dividend − expenditure; negative = gap)
          "cover_expenditures":     float,   (min levy to cover costs from dividend)
          "stable_trust":           float,   (min levy to prevent trust drawdown)
          "full_solvency":          float,   (min levy for both)
          "cover_expenditures_rate": float | None,
          "stable_trust_rate":       float | None,
          "full_solvency_rate":      float | None,
          "feasible":               bool,    (full_solvency achievable ≤ 100% labor income)
          "epsilon":                float,
        }

    Reference: Mission Statement §"Principle 2 — The fiscal architecture must
    remain solvent under any automation level"; §"Policy calibration requires
    knowing not just outcomes but what inputs are required for a target outcome."
    """
    ann_dep  = trust_balance * dep_rate
    dividend = ann_dep * div_rate

    if stewardship_teh is None:
        stew = stewardship_allocation(
            capital_stock_teh=capital_stock_teh,
            capital_age_ratio=capital_age_ratio,
            epsilon=epsilon,
            available_teh=trust_balance,
        )
        stewardship_teh = stew["teh_allocated"]

    if guarantee_teh is None:
        guar = sufficiency_guarantee(population=population, epsilon=epsilon)
        guarantee_teh = guar["total_cost_teh"]

    total_expenditure = stewardship_teh + guarantee_teh
    current_surplus   = dividend - total_expenditure

    # Three levy targets
    cover_exp    = max(0.0, total_expenditure - dividend)
    stable_trust = dividend
    full_solv    = max(cover_exp, stable_trust)

    def rate(levy: float) -> float | None:
        if labor_income is None:
            return None
        return levy / max(labor_income, 1.0)

    return {
        "trust_balance":           trust_balance,
        "dividend":                dividend,
        "stewardship_cost":        stewardship_teh,
        "guarantee_cost":          guarantee_teh,
        "total_expenditure":       total_expenditure,
        "current_surplus":         current_surplus,
        "cover_expenditures":      cover_exp,
        "stable_trust":            stable_trust,
        "full_solvency":           full_solv,
        "cover_expenditures_rate": rate(cover_exp),
        "stable_trust_rate":       rate(stable_trust),
        "full_solvency_rate":      rate(full_solv),
        "feasible":                None if labor_income is None else (full_solv <= labor_income),
        "epsilon":                 epsilon,
    }


# ---------------------------------------------------------------------------
# D6: Accumulation ceiling capital commitment (disabled by default)
# ---------------------------------------------------------------------------

def accumulation_ceiling_commitment(
    teh_in_circulation: float,
    population: float,
    ceiling_multiplier: float = ACCUMULATION_CEILING_MULTIPLIER,
    base_lifetime_earnings: float = BASE_LIFETIME_EARNINGS_TEH,
) -> dict:
    """
    Route TEH above the accumulation ceiling into capital formation.

    D6 (opt-in): when per-capita circulating TEH exceeds the ceiling, the
    aggregate excess is committed to capital investment. TEH moves from free
    circulation into the capital_embodied_teh pool, where it is eventually
    destroyed through write-downs. This is not immediate destruction — it is
    routing deferred consumption into the physical economy.

    The ceiling is set as a multiple of base lifetime earnings (2080 TEH/yr
    × 42-yr career at 1× multiplier = 87,360 TEH). At 3.5× that is ~305,760
    TEH per capita. Workers who accumulate beyond this ceiling have their
    excess committed to infrastructure rather than held indefinitely as savings.

    Disabled by default — the framework does not mandate capital commitment
    and the behavioral parameter is empirically uncertain. Enable only for
    scenario testing.

    Ledger effect:
      - teh_committed_to_capital: subtract from teh_in_circulation,
        add to capital_embodied_teh. Not destroyed yet — destruction comes
        from future capital write-downs.

    Args:
        teh_in_circulation: TEH in free circulation.
        population: Total population.
        ceiling_multiplier: Max per-capita accumulation as × base lifetime earnings.
        base_lifetime_earnings: TEH from a full 42-year career at 1× multiplier.

    Returns:
        dict: {
            "teh_committed_to_capital": float,   moves from circulation → capital pool
            "ceiling_teh":              float,   absolute per-capita ceiling
            "per_capita_teh":           float,
            "excess_per_capita":        float,
            "mechanism":                "D6_ceiling",
        }

    Reference: §8.5 Lifetime Accumulation Boundary (reference framework);
    excess above ceiling committed to capital rather than levied, to preserve
    the "labor is honored" principle while preventing permanent savings stranding.
    """
    ceiling_teh      = ceiling_multiplier * base_lifetime_earnings
    per_capita_teh   = teh_in_circulation / max(population, 1.0)
    excess_per_capita = max(0.0, per_capita_teh - ceiling_teh)
    total_committed  = excess_per_capita * population

    return {
        "teh_committed_to_capital": total_committed,
        "ceiling_teh":              ceiling_teh,
        "per_capita_teh":           per_capita_teh,
        "excess_per_capita":        excess_per_capita,
        "mechanism":                "D6_ceiling",
    }
