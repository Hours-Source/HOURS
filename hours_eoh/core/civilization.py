"""
Civilization ε derivation from physical capital state.

Provides the endogenous machine-capacity sub-model that compute_epsilon() was
designed to receive. Given a description of a civilization's capital stock
(explicit or shorthand tier), derives machine_eoh_fulfilled and therefore ε
from first principles rather than as an exogenous scenario assumption.

The key formula:
  machine_eoh_fulfilled = Σ teh_value_i × condition_i
                            × (eoh_elimination_rate_i + personal_fulfillment_rate_i)
  ε = machine_eoh_fulfilled / total_eoh_collective_potential

Where total_eoh_collective_potential is the gross physical EOH (no capital
reduction applied — machines cannot reduce the denominator they define).

Usage::

    from hours_eoh.core.civilization import civilization_epsilon

    result = civilization_epsilon({
        "population": 10_000_000,
        "ecosystem_health": 0.65,
        "capital": {
            "power_grid":           "standard",
            "water_treatment":      "standard",
            "medical_systems":      "basic",
            "industrial_automation": {"teh_value": 3e9, "age": 12, "condition": 0.80},
        },
    })
    print(f"ε = {result['epsilon']:.3f}")

Capital can be specified three ways:
  - Tier string:  "power_grid": "standard"
  - Explicit dict: "power_grid": {"teh_value": 2e9, "age": 18, "condition": 0.75}
  - Mixed tier with override: "power_grid": {"tier": "standard", "age": 25}

All tier types are in data.CAPITAL_MACHINE_PROFILES. Tiers are "minimal",
"basic", "standard", "advanced". Tier teh_value is per-capita and is
automatically scaled by population.

Mission Statement: §"ε is a physical observable — the civilization's measured
progress toward post-scarcity, expressed as the fraction of EOH fulfilled by
machines relative to the total EOH demand." This module computes that observable
from physical inputs rather than assuming it.
"""

from __future__ import annotations

from hours_eoh.data import (
    CAPITAL_MACHINE_PROFILES,
    CANONICAL_MONITORING_CAPABILITY_BASE,
    COND_DECAY_SLOPE,
    COND_DECAY_FLOOR,
    ENV_MONITORING_SATURATION_TEH_PER_CAPITA,
    TRUST_BASE_TEH,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _condition_from_age(age: float, design_life: float) -> float:
    """
    Derive condition from age and design life when condition is not specified.

    Linear decay: 1.0 (brand new) → 0.30 (at end of design life).
    Assets past their design life are floor-capped at 0.30 — degraded but
    still operational (full write-down is a separate event via execute_writedown).
    """
    age_fraction = min(1.0, max(0.0, age / max(design_life, 1.0)))
    return max(COND_DECAY_FLOOR, 1.0 - COND_DECAY_SLOPE * age_fraction)


def _resolve_capital_entry(
    type_name: str,
    spec,
    population: float,
) -> dict:
    """
    Resolve one capital entry to {type, teh_value, age, condition, design_life}.

    Accepts three forms for spec:
      - str:  tier name  e.g. "standard"
      - dict: explicit   e.g. {"teh_value": 2e9, "age": 15, "condition": 0.82}
      - dict: tier+override  e.g. {"tier": "standard", "age": 25}

    When a tier is used, teh_value = tier["teh_per_capita"] × population.
    When age is provided without condition, condition is derived from design_life.
    """
    if type_name not in CAPITAL_MACHINE_PROFILES:
        raise ValueError(
            f"Unknown capital type '{type_name}'. "
            f"Known types: {sorted(CAPITAL_MACHINE_PROFILES)}"
        )

    profile     = CAPITAL_MACHINE_PROFILES[type_name]
    design_life = profile["design_life"]
    tiers       = profile.get("tiers", {})

    # --- Identify tier name and explicit overrides ---
    tier_name: str | None = None
    if isinstance(spec, str):
        tier_name = spec
        explicit: dict = {}
    elif isinstance(spec, dict) and "tier" in spec:
        tier_name = spec["tier"]
        explicit  = {k: v for k, v in spec.items() if k != "tier"}
    elif isinstance(spec, dict):
        explicit  = spec
    else:
        raise TypeError(
            f"Capital spec for '{type_name}' must be a str or dict, got {type(spec).__name__}"
        )

    # --- Resolve values ---
    if tier_name is not None:
        if tier_name not in tiers:
            raise ValueError(
                f"Unknown tier '{tier_name}' for '{type_name}'. "
                f"Available: {sorted(tiers)}"
            )
        td        = tiers[tier_name]
        teh_value = float(explicit.get("teh_value", td["teh_per_capita"] * population))
        age       = float(explicit.get("age",       td["default_age"]))
        condition = explicit.get("condition", td["default_condition"])
    else:
        if "teh_value" not in explicit:
            raise ValueError(
                f"Explicit capital spec for '{type_name}' must include 'teh_value'. "
                f"Alternatively, use a tier string: \"standard\", \"advanced\", etc."
            )
        teh_value = float(explicit["teh_value"])
        age       = float(explicit.get("age", 0.0))
        condition = explicit.get("condition")
        if condition is None:
            condition = _condition_from_age(age, design_life)

    return {
        "type":        type_name,
        "teh_value":   float(teh_value),
        "age":         float(age),
        "condition":   float(max(0.0, min(1.0, float(condition)))),
        "design_life": design_life,
    }


# ---------------------------------------------------------------------------
# Public: machine EOH from capital description
# ---------------------------------------------------------------------------

def machine_eoh_from_capital(
    capital_desc: dict,
    population: float,
) -> dict:
    """
    Compute machine EOH capacity from a capital description dict.

    Each key in capital_desc is a type name from CAPITAL_MACHINE_PROFILES;
    each value is a tier string or explicit spec dict (see module docstring).

    The result feeds directly into compute_epsilon() as machine_eoh_fulfilled.

    Args:
        capital_desc: {type_name: spec, ...}
        population: Total population — used to scale per-capita tier values.

    Returns:
        dict: {
          "annual_eoh_eliminated":         float,  system EOH (i/e/k) eliminated
          "annual_personal_eoh_fulfilled":  float,  personal EOH machines handle
          "machine_eoh_total":              float,  = eliminated + personal_fulfilled
          "capital_stock_teh":              float,  Σ teh_value across types
          "capital_age_ratio":              float,  TEH-weighted mean age/design_life
          "by_type": {
              type_name: {
                  "teh_value":           float,
                  "age":                 float,
                  "condition":           float,
                  "design_life":         float,
                  "eoh_eliminated":      float,
                  "personal_fulfilled":  float,
                  "combined_eoh":        float,
              }
          }
        }

    Reference: Mission Statement §"Capital stock eliminates EOH by handling
    obligations that would otherwise require direct human labor."
    """
    total_eliminated  = 0.0
    total_personal    = 0.0
    total_teh         = 0.0
    weighted_age_sum  = 0.0
    by_type: dict     = {}

    for type_name, spec in capital_desc.items():
        resolved = _resolve_capital_entry(type_name, spec, population)
        profile  = CAPITAL_MACHINE_PROFILES[type_name]

        teh  = resolved["teh_value"]
        cond = resolved["condition"]
        dl   = resolved["design_life"]
        age  = resolved["age"]

        eoh_elim   = teh * cond * profile["eoh_elimination_rate"]
        pers_fulfil = teh * cond * profile["personal_fulfillment_rate"]

        total_eliminated  += eoh_elim
        total_personal    += pers_fulfil
        total_teh         += teh
        weighted_age_sum  += teh * (age / max(dl, 1.0))

        by_type[type_name] = {
            "teh_value":          teh,
            "age":                age,
            "condition":          cond,
            "design_life":        dl,
            "eoh_eliminated":     eoh_elim,
            "personal_fulfilled": pers_fulfil,
            "combined_eoh":       eoh_elim + pers_fulfil,
        }

    cap_age_ratio = (weighted_age_sum / total_teh) if total_teh > 0.0 else 0.0

    return {
        "annual_eoh_eliminated":         total_eliminated,
        "annual_personal_eoh_fulfilled":  total_personal,
        "machine_eoh_total":              total_eliminated + total_personal,
        "capital_stock_teh":              total_teh,
        "capital_age_ratio":              min(1.0, cap_age_ratio),
        "by_type":                        by_type,
    }


# ---------------------------------------------------------------------------
# Public: civilization ε derivation
# ---------------------------------------------------------------------------

def civilization_epsilon(civ: dict) -> dict:
    """
    Derive ε and full breakdown from a civilization description dict.

    Takes a physical state description (including capital stock composition),
    derives machine_eoh_fulfilled from the capital, and computes ε as a
    physical observable. Then runs the full EOH → TEH pipeline and fiscal
    snapshot at the derived ε.

    Args:
        civ: Civilization description dict. All keys are optional with defaults.

            population (float):          Total population. Default: 1_000_000.
            workforce_fraction (float):  Active workforce ∈ [0, 1]. Default: 0.60.
            ecosystem_health (float):    Ecosystem state ∈ [0, 1]. Default: 0.70.
            deferred_ecological (float): Accumulated deferred eco EOH. Default: 0.
            knowledge_complexity (float): kbs relative to ε=0 reference. Default: 1.0.
            age_distribution (dict):     age_group → fraction. Default: None (canonical).
            monitoring_capability (float): Overrides auto-derived value. Default: None.
            trust_balance (float):       Trust fund starting balance. Default: TRUST_BASE_TEH.
            mean_multiplier (float):     TEH creation multiplier. Default: 2.10.
            capital (dict):              Capital stock. Keys = CAPITAL_MACHINE_PROFILES
                                         type names; values = tier str or spec dict.
                                         Default: {} → machine_eoh=0 → ε=0.

    Returns:
        dict: {
            "epsilon":         float,   derived ε ∈ [0, 1]
            "physical_state":  dict,    resolved physical parameters
            "eoh_gross":       dict,    total_eoh() without capital reduction
            "machine_eoh": {
                "total":               float,
                "system_eliminated":   float,  (i/e/k domains)
                "personal_fulfilled":  float,
                "by_type":             dict,   per capital type breakdown
            },
            "pipeline":        dict,    eoh_to_teh_pipeline() result at derived ε
            "fiscal":          dict,    fiscal_snapshot() result
            "workforce":       dict,    domain_labor_requirements() result
            "warnings":        list[str],
        }

    Note on double-counting: capital_eoh_eliminated is NOT passed to the TEH
    pipeline because ε already encodes all machine fulfillment (including
    system EOH elimination). Passing both would double-count machine capacity.
    capital_personal_eoh_fulfilled IS passed for fiscal guarantee sizing.

    Mission Statement: §"ε is a physical observable — the civilization's
    measured progress toward post-scarcity, expressed as the fraction of EOH
    fulfilled by machines relative to the total EOH demand that would exist
    if all personal EOH were on the collective ledger."
    """
    from hours_eoh.core.eoh_generation import total_eoh, domain_labor_requirements
    from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
    from hours_eoh.core.fiscal import fiscal_snapshot
    from hours_eoh.core.trajectory import compute_epsilon

    warnings: list[str] = []

    population           = float(civ.get("population",           1_000_000.0))
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")
    workforce_fraction   = float(civ.get("workforce_fraction",   0.60))
    ecosystem_health     = float(civ.get("ecosystem_health",     0.70))
    deferred_ecological  = float(civ.get("deferred_ecological",  0.0))
    knowledge_complexity = float(civ.get("knowledge_complexity", 1.0))
    age_distribution     = civ.get("age_distribution")
    mean_multiplier      = float(civ.get("mean_multiplier",      2.10))
    trust_balance        = float(civ.get("trust_balance",        TRUST_BASE_TEH))

    capital_desc = civ.get("capital", {})
    mach = machine_eoh_from_capital(capital_desc, population)

    capital_stock_teh  = mach["capital_stock_teh"]
    capital_age_ratio  = mach["capital_age_ratio"]
    eoh_eliminated     = mach["annual_eoh_eliminated"]
    personal_fulfilled = mach["annual_personal_eoh_fulfilled"]

    if capital_stock_teh == 0.0:
        warnings.append("No capital specified — machine_eoh=0, ε=0.")

    # Explicit override takes precedence. Otherwise, environmental_monitoring
    # capital raises capability above the canonical base (0.50). Saturates at
    # ENV_MONITORING_SATURATION_TEH_PER_CAPITA → full visibility.
    monitoring_capability = civ.get("monitoring_capability")
    if monitoring_capability is None:
        env_entry = mach["by_type"].get("environmental_monitoring")
        if env_entry is not None:
            env_per_cap = env_entry["teh_value"] / population
            monitoring_capability = min(
                1.0,
                CANONICAL_MONITORING_CAPABILITY_BASE
                + (1.0 - CANONICAL_MONITORING_CAPABILITY_BASE)
                * (env_per_cap / ENV_MONITORING_SATURATION_TEH_PER_CAPITA),
            )
        else:
            monitoring_capability = CANONICAL_MONITORING_CAPABILITY_BASE

    # Gross total EOH — denominator for ε. capital_eoh_eliminated intentionally
    # omitted: ε = machines / gross_total, so the gross must exclude capital reduction.
    eoh_gross = total_eoh(
        population=population,
        age_distribution=age_distribution,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        deferred_ecological=deferred_ecological,
        knowledge_complexity=knowledge_complexity,
        monitoring_capability=monitoring_capability,
    )

    epsilon = compute_epsilon(eoh_eliminated + personal_fulfilled, eoh_gross["total"])

    if epsilon >= 0.98:
        warnings.append(
            f"Derived ε={epsilon:.3f} is near post-scarcity. "
            "Verify capital stock composition is not over-specified."
        )

    # capital_eoh_eliminated=0: ε already encodes all machine fulfillment.
    # capital_personal_eoh_fulfilled passed for fiscal guarantee sizing.
    pipeline = eoh_to_teh_pipeline(
        epsilon=epsilon,
        population=population,
        age_distribution=age_distribution,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        deferred_ecological=deferred_ecological,
        knowledge_complexity=knowledge_complexity,
        capital_eoh_eliminated=0.0,
        capital_personal_eoh_fulfilled=personal_fulfilled,
        mean_multiplier=mean_multiplier,
        monitoring_capability=monitoring_capability,
    )

    workforce_size = population * workforce_fraction
    fiscal = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=pipeline["teh_created"],
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        ecosystem_health=ecosystem_health,
        deferred_ecological=deferred_ecological,
        capital_personal_eoh_fulfilled_per_person=personal_fulfilled / population,
        infra_eoh_override=eoh_gross["infrastructure"],
        eco_eoh_override=eoh_gross["ecological"],
    )

    workforce = domain_labor_requirements(pipeline["eoh_by_domain"], epsilon)

    return {
        "epsilon": epsilon,
        "physical_state": {
            "population":            population,
            "workforce_fraction":    workforce_fraction,
            "workforce_size":        workforce_size,
            "capital_stock_teh":     capital_stock_teh,
            "capital_age_ratio":     capital_age_ratio,
            "ecosystem_health":      ecosystem_health,
            "deferred_ecological":   deferred_ecological,
            "knowledge_complexity":  knowledge_complexity,
            "monitoring_capability": monitoring_capability,
            "age_distribution":      age_distribution,
            "trust_balance":         trust_balance,
        },
        "eoh_gross": eoh_gross,
        "machine_eoh": {
            "total":              eoh_eliminated + personal_fulfilled,
            "system_eliminated":  eoh_eliminated,
            "personal_fulfilled": personal_fulfilled,
            "by_type":            mach["by_type"],
        },
        "pipeline":  pipeline,
        "fiscal":    fiscal,
        "workforce": workforce,
        "warnings":  warnings,
    }
