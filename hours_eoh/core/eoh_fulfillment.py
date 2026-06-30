"""
EOH Fulfillment and TEH Creation, TEH Destruction

Model the full pipeline:
  EOH demand (total_eoh)
  → human-labor share (human_eoh_share)
  → registered fraction (registered_eoh)
  → TEH creation through labor (teh_created)
  → TEH destruction through consumption and write-down
  → net TEH supply (teh_supply) — must satisfy Condition I

The critical distinction from the old model: EOH is the *input*.
Labor supply is the *response* to EOH demand, not the starting point.

Mission Statement: §"EOH as demand signal", §"The dual ledger",
§"Condition I — Ledger Identity", §"Guardrail II — Capital write-down"
"""

from __future__ import annotations

from hours_eoh.data import (
    CAPITAL_WRITEDOWN_MONITORING_SLOPE,
)


# ---------------------------------------------------------------------------
# Human EOH Share
# ---------------------------------------------------------------------------

def human_eoh_share(
    total_eoh: float,
    epsilon: float = 0.40,
) -> float:
    """
    The portion of total EOH that requires human labor at this automation level.

    At ε=0: all EOH fulfillment is human labor → human_eoh = total_eoh.
    At ε=0.99: only 1% requires human labor; machines handle the rest.

    The relationship is linear: human_fraction = (1 - ε). This captures the
    clean substitution of automation for human labor across all EOH domains.
    The total entropy obligation (total_eoh) does not change — only who
    (or what) fulfills it changes.

    Args:
        total_eoh: Total EOH (hours/year) across all four domains.
        epsilon: Automation level [0.0, 0.99].

    Returns:
        Human-labor EOH (hours/year) — the portion requiring human workers.

    Reference: Mission Statement §"EOH and automation" — "At ε=0, all EOH
    fulfillment is human labor ... At ε=0.99, only 1% of registered EOH
    fulfillment requires human labor."
    """
    if not 0.0 <= epsilon <= 1.0:
        raise ValueError(f"epsilon must be in [0.0, 1.0], got {epsilon}")
    human_fraction = 1.0 - epsilon
    return total_eoh * human_fraction


# ---------------------------------------------------------------------------
# Registered EOH
# ---------------------------------------------------------------------------

def registered_eoh(
    human_eoh: float,
    registration_share: float,
) -> float:
    """
    The portion of human-fulfilled EOH registered in the collective ledger.

    Only registered EOH generates TEH. Self-care (cooking own dinner) and
    household EOH (family vehicle maintenance) are zero events — real entropy
    resistance happens, but no monetary event occurs because the EOH is not
    in the collective ledger. The registration boundary is what defines
    economic activity.

    Args:
        human_eoh: Human-labor EOH (hours/year) — from human_eoh_share().
        registration_share: Fraction of human EOH registered in collective ledger,
                            ∈ [0.0, 1.0]. Comes from total_registration_share()
                            in registration.py.

    Returns:
        Registered EOH (hours/year) — the portion that will generate TEH.

    Special case: self-care and household EOH have registration_share=0.0,
    producing zero registered EOH and therefore zero TEH — correct by design.

    Reference: Mission Statement §"The registration boundary" — "Self-care is
    a zero event ... The collective decides which obligations it recognizes."
    """
    if not 0.0 <= registration_share <= 1.0:
        raise ValueError(
            f"registration_share must be in [0.0, 1.0], got {registration_share}"
        )
    return human_eoh * registration_share


# ---------------------------------------------------------------------------
# TEH Creation
# ---------------------------------------------------------------------------

def teh_created(
    registered_eoh_hours: float,
    mean_multiplier: float = 2.10,
) -> float:
    """
    TEH created when workers fulfill registered EOH at their multiplied tier rates.

    Governing equation:
        TEH = EOH_registered × m̄

    where m̄ = population_weighted_mean_multiplier() across all workers fulfilling
    registered EOH in this period.

    Worked example: 1,000 registered EOH fulfilled by a workforce with mean
    multiplier m̄ = 2.10 → 2,100 TEH created this period.
    At m̄ = 1.0 (all base tier): 1,000 EOH → 1,000 TEH.
    At m̄ = 3.0 (advanced workforce): 1,000 EOH → 3,000 TEH.

    The mean_multiplier must satisfy Condition II (band [1.8, 2.1]). Caller is
    responsible for verifying this via multiplier_band_check() before passing
    mean_multiplier here. This function does not gate on the band.

    Args:
        registered_eoh_hours: Registered EOH fulfilled this period (hours).
        mean_multiplier: Population-weighted mean multiplier (must be ≥ 1.0).

    Returns:
        TEH created (currency units — 1 TEH = 1 verified hour of entropy resistance).

    Reference: Mission Statement §"EOH as demand signal" — "100 EOH ...
    at a 3.0 multiplier creates 300 TEH. The multiplier system applies to all
    entropy-reduction labor uniformly."
    """
    if mean_multiplier < 1.0:
        raise ValueError(f"mean_multiplier must be ≥ 1.0, got {mean_multiplier}")
    return registered_eoh_hours * mean_multiplier


# ---------------------------------------------------------------------------
# D0: Capital Write-Down
# ---------------------------------------------------------------------------

def capital_writedown(
    capital_stock_teh: float,
    failure_rate: float = 0.005,
    epsilon: float = 0.40,
) -> float:
    """
    TEH destroyed when assets degrade beyond recoverability (capital write-down).

    When capital degrades beyond the recoverability threshold, the associated
    EOH is formally written off and the TEH embodied in that capital is
    destroyed. For human capital: death is a write-down — the person's personal
    EOH vanishes and their entropy-reduction capacity must be redistributed.

    Higher ε enables better monitoring and predictive maintenance, slightly
    reducing the fraction of capital that fails catastrophically (versus being
    maintained in time).

    Args:
        capital_stock_teh: Current capital stock value in TEH.
        failure_rate: Annual fraction of capital that fails beyond recovery.
        epsilon: Automation level. Better monitoring → slightly lower failure rate.

    Returns:
        TEH destroyed through capital write-down this period.

    Reference: Mission Statement §"Guardrail II — Capital write-down" — "When
    capital degrades beyond the point where maintenance labor can restore
    function, the associated EOH must be formally written off."
    """
    # Better monitoring at higher ε catches failures earlier, reducing total
    # catastrophic write-downs (CAPITAL_WRITEDOWN_MONITORING_SLOPE reduction at ε=1.0).
    monitoring_factor = 1.0 - CAPITAL_WRITEDOWN_MONITORING_SLOPE * epsilon
    adjusted_rate = failure_rate * monitoring_factor
    return capital_stock_teh * adjusted_rate


# ---------------------------------------------------------------------------
# TEH Supply (Condition I)
# ---------------------------------------------------------------------------

def teh_supply(
    teh_created_total: float,
    teh_destroyed_total: float,
) -> float:
    """
    Net TEH in existence: cumulative creation minus cumulative destruction.

    This is the operational definition of Condition I (Ledger Identity).
    The total supply must always equal cumulative creation minus cumulative
    destruction, with no exceptions.

    Spending and levies are circulatory — they move TEH between accounts but
    do not appear here. Only terminal consumption and capital write-down remove
    TEH from existence.

    Args:
        teh_created_total: Cumulative TEH created through verified labor (hours).
        teh_destroyed_total: Cumulative TEH destroyed (consumption + write-downs).

    Returns:
        Net TEH supply (hours). Non-negative by construction.

    Raises:
        ValueError: If destroyed > created (a ledger violation — impossible in
                    a correctly operating system).

    Reference: Mission Statement §"Condition I — Ledger Identity" — "The total
    supply must always equal cumulative creation minus cumulative destruction,
    with no exceptions."
    """
    tol = max(teh_created_total * 1e-9, 1e-6)  # floating-point tolerance
    if teh_destroyed_total > teh_created_total + tol:
        raise ValueError(
            f"Ledger violation: destroyed ({teh_destroyed_total:.4f}) > "
            f"created ({teh_created_total:.4f}) — impossible in a correct system."
        )
    return teh_created_total - teh_destroyed_total


# ---------------------------------------------------------------------------
# Per-domain human EOH breakdown
# ---------------------------------------------------------------------------

def human_eoh_per_domain(
    total_eoh_dict: dict,
    epsilon: float = 0.40,
) -> dict:
    """
    Per-domain human-labor EOH from a total_eoh() result dict.

    total_eoh() returns gross domain totals (full physical obligation) but not
    the human-labor portions. This helper applies (1-ε) to each domain, making
    domain-specific human workforce demand explicit for stewardship planning,
    fiscal allocation, and scarcity detection.

    Args:
        total_eoh_dict: Return dict from total_eoh(). Must contain keys:
                        "personal", "infrastructure", "ecological", "knowledge".
        epsilon: Automation level [0.0, 0.99].

    Returns:
        dict: {
          "personal":       float,
          "infrastructure": float,
          "ecological":     float,
          "knowledge":      float,
          "total":          float,
          "human_fraction": float,   (= 1 - ε)
          "epsilon":        float,
        }

    Reference: Mission Statement §"EOH and automation" — human_fraction = (1-ε)
    applies uniformly across all four entropy domains.
    """
    human_fraction = 1.0 - epsilon
    domains = ("personal", "infrastructure", "ecological", "knowledge")
    per_domain = {d: total_eoh_dict.get(d, 0.0) * human_fraction for d in domains}
    return {
        **per_domain,
        "total":          sum(per_domain.values()),
        "human_fraction": human_fraction,
        "epsilon":        epsilon,
    }


# ---------------------------------------------------------------------------
# End-to-end EOH → TEH pipeline orchestrator
# ---------------------------------------------------------------------------

def eoh_to_teh_pipeline(
    epsilon: float,
    population: float = 1_000_000.0,
    age_distribution: dict | None = None,
    capital_stock: float = 2_000_000_000.0,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
    deferred_ecological: float = 0.0,
    knowledge_complexity: float = 1.0,
    skill_decay_rate: float = 0.10,
    capital_eoh_eliminated: float = 0.0,
    capital_personal_eoh_fulfilled: float = 0.0,
    infrastructure_compounding_eoh: float = 0.0,
    competency_gap_factor: float = 0.0,
    registration_share: float | None = None,
    personal_registration_share: float | None = None,
    mean_multiplier: float = 2.10,
    monitoring_capability: float | None = None,
    knowledge_complexity_per_unit: float | None = None,
) -> dict:
    """
    End-to-end EOH → human share → registered → TEH creation in one call.

    Chains the four-step pipeline with a single epsilon, preventing the
    common error of calling total_eoh() at one ε and human_eoh_share() at
    another. Returns all intermediate values for auditability (Guardrail I).

    Pipeline:
      1. total_eoh(epsilon, ...)                  → domain breakdown + total
      2. human_eoh_share(domain, epsilon)         → human labor portion per domain
      3. registered_eoh(human, share_by_domain)   → per-domain registration
      4. teh_created(registered_total, mult)      → TEH generated this period

    Registration is applied per-domain — a critical distinction:
      - Personal EOH uses personal_eoh_registration_share(ε): demand registration,
        tracking what fraction of biological obligation is collectively recognized.
        Near-zero at ε=0; rises to ~0.95 by ε=0.99. Inflection at ε=0.65.
      - Infrastructure/ecological/knowledge EOH use total_registration_share(ε):
        labor registration, tracking what fraction of fulfillment labor is on
        the collective ledger.

    If registration_share is provided (non-None), it overrides BOTH personal
    and non-personal registration uniformly — useful for scenario testing.
    If personal_registration_share is provided separately, it overrides only
    the personal domain while non-personal uses the dynamic (or registration_share)
    value.

    Args:
        epsilon: Automation level [0.0, 0.99]. Applied consistently to all steps.
        population: Total population.
        age_distribution: Optional dict mapping age group → fraction.
        capital_stock: Baseline capital stock in TEH (at ε=0).
        capital_age_ratio: Mean asset age relative to design life.
        ecosystem_health: Ecosystem state ∈ [0, 1].
        deferred_ecological: Accumulated deferred ecological EOH (hours).
        knowledge_complexity: Relative knowledge base size.
        skill_decay_rate: Annual skill renewal fraction.
        capital_eoh_eliminated: EOH eliminated by capital stock.
        capital_personal_eoh_fulfilled: Personal EOH fulfilled by capital.
        infrastructure_compounding_eoh: Deferred-maintenance compounding spike.
        competency_gap_factor: Knowledge EOH amplifier from competency gaps.
        registration_share: Uniform override for ALL domains. None → per-domain
            dynamic computation. When set, also overrides personal_registration_share.
        personal_registration_share: Override for the personal domain only.
            None → use personal_eoh_registration_share(epsilon) dynamically.
            Ignored if registration_share is set.
        mean_multiplier: Population-weighted mean multiplier for step 4.

    Returns:
        dict: {
          "epsilon":                  float,
          "total_eoh":                float,
          "eoh_by_domain":            dict,   (personal/infrastructure/ecological/knowledge)
          "human_eoh":                float,  (total across all domains)
          "human_fraction":           float,  (= 1 - ε)
          "registration_share":       float,  (effective composite: registered/human)
          "registration_by_domain":   dict,   (personal: float, non_personal: float)
          "registered_eoh":           float,  (total)
          "registered_eoh_by_domain": dict,   (personal: float, non_personal: float)
          "mean_multiplier":          float,
          "teh_created":              float,
          "capital_eoh_eliminated":        float,
          "capital_personal_eoh_fulfilled": float,
        }

    Governing equation (compound over four domains):

        TEH = [Σ_domain  EOH_domain × (1−ε) × reg_share_domain(ε)] × m̄

    where reg_share_domain differs by domain (personal uses demand registration;
    infrastructure/ecological/knowledge use the labor composite).

    As ε rises from 0 to 1, total_eoh grows (more complex civilization) but
    human_eoh = total_eoh × (1−ε) falls; registered EOH first rises then falls
    as registration rates saturate; TEH_created peaks near mid-arc and collapses
    as ε → 1 (machines handle almost everything).

    Worked example at ε=0.40 (canonical defaults, population=1M, m̄=2.10):
        total_eoh   = 2,353M h/yr
        human_eoh   = 2,353M × 0.60         = 1,412M h/yr  (1−ε share)
        personal reg = 313M × 0.141         =    44M h/yr  (demand sigmoid pers_reg(0.40)=0.141)
        non-pers reg = 1,098M × 0.592       =   191M h/yr  (labor sigmoid np_reg(0.40)=0.592)
        registered  =   44M + 191M          =   235M h/yr
        TEH_created = 235M × 2.10           =   494M TEH/yr

    For comparison:
        ε=0.00: total=2,288M, human=2,288M, reg=33M, TEH=70M  (near-zero personal reg)
        ε=0.90: total=2,432M, human=243M,   reg=199M, TEH=419M (high reg, low human supply)

    Reference: Mission Statement §"EOH as demand signal" — the pipeline from
    physical obligation to currency creation must be transparent and auditable.
    """
    from hours_eoh.core.eoh_generation import total_eoh as _total_eoh
    from hours_eoh.core.registration import (
        total_registration_share,
        personal_eoh_registration_share as _personal_reg_share,
    )

    eoh_dict = _total_eoh(
        epsilon=epsilon,
        population=population,
        age_distribution=age_distribution,
        capital_stock=capital_stock,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
        deferred_ecological=deferred_ecological,
        knowledge_complexity=knowledge_complexity,
        skill_decay_rate=skill_decay_rate,
        capital_eoh_eliminated=capital_eoh_eliminated,
        capital_personal_eoh_fulfilled=capital_personal_eoh_fulfilled,
        infrastructure_compounding_eoh=infrastructure_compounding_eoh,
        competency_gap_factor=competency_gap_factor,
        monitoring_capability=monitoring_capability,
        knowledge_complexity_per_unit=knowledge_complexity_per_unit,
    )

    # Per-domain human EOH via the existing helper (uniform (1-ε) per domain)
    hd                 = human_eoh_per_domain(eoh_dict, epsilon)
    personal_eoh_val   = eoh_dict["personal"]
    human_personal     = hd["personal"]
    human_non_personal = hd["infrastructure"] + hd["ecological"] + hd["knowledge"]
    human_total        = hd["total"]

    # Per-domain registration (M5):
    # - Personal: demand registration (what fraction of biological obligation
    #   is collectively recognised). Near-zero at ε=0; ~0.95 by ε=0.99.
    # - Infrastructure + Ecological: labor registration composite
    #   (care/production/stewardship), physical outputs are directly inspectable.
    # - Knowledge: separate verification-difficulty sigmoid — knowledge outputs
    #   lack physical indicators; inflection at ε=0.70, saturation at 0.80.
    # When registration_share is provided, it overrides ALL domains uniformly.
    from hours_eoh.core.registration import knowledge_eoh_registration_share as _know_reg_share
    if registration_share is not None:
        pers_share   = registration_share
        infra_share  = registration_share
        eco_share    = registration_share
        know_share   = registration_share
    else:
        pers_share  = (personal_registration_share
                       if personal_registration_share is not None
                       else _personal_reg_share(epsilon))
        infra_share = eco_share = total_registration_share(epsilon)
        know_share  = _know_reg_share(epsilon)

    human_infra    = hd["infrastructure"]
    human_eco      = hd["ecological"]
    human_know     = hd["knowledge"]

    reg_personal = registered_eoh(human_personal, pers_share)
    reg_infra    = registered_eoh(human_infra,    infra_share)
    reg_eco      = registered_eoh(human_eco,      eco_share)
    reg_know     = registered_eoh(human_know,     know_share)
    reg_total    = reg_personal + reg_infra + reg_eco + reg_know

    # Backward-compatible aggregates for callers that use the personal/non_personal split
    reg_non_personal = reg_infra + reg_eco + reg_know
    # Composite non-personal share (weighted by human EOH volume)
    non_pers_share   = reg_non_personal / max(human_non_personal, 1.0)

    # Effective composite registration share for backward-compatible reporting
    effective_share  = reg_total / max(human_total, 1.0)

    teh = teh_created(reg_total, mean_multiplier)

    return {
        "epsilon":           epsilon,
        "total_eoh":         eoh_dict["total"],
        "eoh_by_domain": {
            "personal":       personal_eoh_val,
            "infrastructure": eoh_dict["infrastructure"],
            "ecological":     eoh_dict["ecological"],
            "knowledge":      eoh_dict["knowledge"],
        },
        "human_eoh":          human_total,
        "human_fraction":     1.0 - epsilon,
        "registration_share": effective_share,
        "registration_by_domain": {
            "personal":       pers_share,
            "infrastructure": infra_share,
            "ecological":     eco_share,
            "knowledge":      know_share,
            "non_personal":   non_pers_share,   # backward compat
        },
        "registered_eoh":     reg_total,
        "registered_eoh_by_domain": {
            "personal":       reg_personal,
            "infrastructure": reg_infra,
            "ecological":     reg_eco,
            "knowledge":      reg_know,
            "non_personal":   reg_non_personal,  # backward compat
        },
        "mean_multiplier":    mean_multiplier,
        "teh_created":        teh,
        "capital_eoh_eliminated":         capital_eoh_eliminated,
        "capital_personal_eoh_fulfilled":  capital_personal_eoh_fulfilled,
    }
