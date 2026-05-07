"""
Distributed Competency (Condition IV) and Workforce Dynamics

Models the competency reserve across seven essential domains, the minimum
labor obligation that sustains it, and the automation failure scenario.

Condition IV (Distributed Competency) requires that at least 15.5% of
the workforce remain certified in each of seven essential domains regardless
of automation level. This is not a market outcome — it is a structural
requirement. As automation rises, maintaining the reserve requires explicit
policy (the minimum hours obligation and competency rotation).

Key functions:
  - competency_reserve(): Track certified workers across essential domains
  - competency_check(): Does the reserve meet Condition IV?
  - minimum_hours_allocation(): The 260-hour/year obligation split 40/30/30
  - automation_failure_scenario(): What if automation suddenly fails?

Mission Statement: §"Condition IV — Distributed Competency"; §"minimum
labor obligation … 260 hours per year, split 40/30/30 across competency
rotation, stewardship service, and regular employment"; §"Automation failure
… the reserve must be sufficient to cover critical infrastructure EOH."
"""

from __future__ import annotations

from hours_eoh.data import (
    ESSENTIAL_DOMAINS,
    COMPETENCY_THRESHOLD,
    H_MIN,
    H_MIN_ALLOCATION,
)


# ---------------------------------------------------------------------------
# Competency Reserve
# ---------------------------------------------------------------------------

def competency_reserve(
    certified_by_domain: dict[str, float],
    workforce_size: float,
    domain_requirements: dict[str, float] | None = None,
) -> dict:
    """
    Compute the competency reserve across the seven essential domains.

    The reserve tracks certified workers per domain relative to the total
    workforce. A domain is "at risk" when its certified fraction falls below
    the required threshold. Condition IV requires ALL seven domains to meet
    the threshold simultaneously.

    Args:
        certified_by_domain: Dict mapping domain name → certified worker count.
                             Missing domains are treated as 0 certified.
                             Domain names must be in ESSENTIAL_DOMAINS.
        workforce_size: Total active workforce (denominator for fractions).
        domain_requirements: Optional per-domain threshold override.
                             Default: COMPETENCY_THRESHOLD (0.155) for all domains.

    Returns:
        dict: {
          "per_domain": {domain: {"certified_count", "required_count",
                                  "reserve_fraction", "required_fraction",
                                  "meets_threshold", "gap"}},
          "domains_at_risk":      list[str],   (domains below threshold)
          "workforce_size":       float,
          "overall_meets_threshold": bool,
          "n_domains_at_risk":    int,
          "status":               "OK" or "COMPETENCY_GAP",
        }

    Raises:
        ValueError: If workforce_size ≤ 0, or if an unrecognized domain name
                    is in certified_by_domain.

    Reference: Mission Statement §"Condition IV — Distributed Competency:
    ≥15.5% of the workforce must remain certified in each of seven essential
    domains at every ε level."
    """
    if workforce_size <= 0:
        raise ValueError(f"workforce_size must be positive, got {workforce_size}")

    for domain in certified_by_domain:
        if domain not in ESSENTIAL_DOMAINS:
            raise ValueError(
                f"Unrecognized domain: '{domain}'. "
                f"Valid domains: {ESSENTIAL_DOMAINS}"
            )

    if domain_requirements is None:
        domain_requirements = {}

    per_domain: dict[str, dict] = {}
    domains_at_risk: list[str] = []

    for domain in ESSENTIAL_DOMAINS:
        count = float(certified_by_domain.get(domain, 0.0))
        required_fraction = float(domain_requirements.get(domain, COMPETENCY_THRESHOLD))
        required_count    = workforce_size * required_fraction
        reserve_fraction  = count / workforce_size
        meets_threshold   = reserve_fraction >= required_fraction - 1e-9
        gap               = max(0.0, required_count - count)

        per_domain[domain] = {
            "certified_count":  count,
            "required_count":   required_count,
            "reserve_fraction": reserve_fraction,
            "required_fraction": required_fraction,
            "meets_threshold":  meets_threshold,
            "gap":              gap,
        }

        if not meets_threshold:
            domains_at_risk.append(domain)

    overall_ok = len(domains_at_risk) == 0

    return {
        "per_domain":             per_domain,
        "domains_at_risk":        domains_at_risk,
        "workforce_size":         workforce_size,
        "overall_meets_threshold": overall_ok,
        "n_domains_at_risk":      len(domains_at_risk),
        "status":                 "OK" if overall_ok else "COMPETENCY_GAP",
    }


# ---------------------------------------------------------------------------
# Competency Check
# ---------------------------------------------------------------------------

def competency_check(
    reserve: dict,
    minimum_threshold: float = COMPETENCY_THRESHOLD,
) -> dict:
    """
    Structured Condition IV pass/fail check from a competency_reserve() result.

    Aligned with condition_iv_check() in conditions.py but operates on the
    full per-domain breakdown. Flags critical infrastructure domains (water,
    energy, healthcare) separately from non-critical gaps.

    Args:
        reserve: Output dict from competency_reserve().
        minimum_threshold: Minimum acceptable fraction per domain. Default: 0.155.

    Returns:
        dict: {
          "passes":           bool,
          "status":           "OK" or "CONDITION_IV_VIOLATION",
          "threshold":        float,
          "domains_at_risk":  list[str],
          "critical_domains": list[str],   (water/energy/healthcare gaps)
          "per_domain":       {domain: {"fraction", "required", "gap_workers", "status"}},
          "recommendation":   str,
        }

    Reference: Mission Statement §"Condition IV — Model it, flag it, reject
    any modification that would allow the reserve to fall below threshold."
    """
    domains_at_risk = reserve.get("domains_at_risk", [])
    overall_ok      = reserve.get("overall_meets_threshold", False)

    # Critical infrastructure domains: failure here directly threatens
    # personal EOH obligations (no fallback if water/energy/healthcare fails)
    CRITICAL = {"healthcare", "water", "energy"}
    critical_gaps = [d for d in domains_at_risk if d in CRITICAL]

    per_domain_status: dict[str, dict] = {}
    for domain, data in reserve["per_domain"].items():
        per_domain_status[domain] = {
            "fraction":    data["reserve_fraction"],
            "required":    data["required_fraction"],
            "gap_workers": data["gap"],
            "status":      "OK" if data["meets_threshold"] else "BELOW_THRESHOLD",
        }

    if overall_ok:
        recommendation = (
            "Competency reserve meets Condition IV across all seven essential domains."
        )
    elif critical_gaps:
        recommendation = (
            f"CRITICAL gaps in: {', '.join(critical_gaps)}. "
            f"These domains have no fallback — EOH coverage will fail immediately. "
            f"Emergency training or workforce reallocation required."
        )
    else:
        recommendation = (
            f"Non-critical gaps in: {', '.join(domains_at_risk)}. "
            f"Increase competency rotation hours or reduce automation displacement "
            f"in these domains before ε advances further."
        )

    return {
        "passes":           overall_ok,
        "status":           "OK" if overall_ok else "CONDITION_IV_VIOLATION",
        "threshold":        minimum_threshold,
        "domains_at_risk":  domains_at_risk,
        "critical_domains": critical_gaps,
        "per_domain":       per_domain_status,
        "recommendation":   recommendation,
    }


# ---------------------------------------------------------------------------
# Minimum Hours Allocation
# ---------------------------------------------------------------------------

def minimum_hours_allocation(
    h_min: float = H_MIN,
    rotation_share: float = H_MIN_ALLOCATION["competency_rotation"],
    stewardship_share: float = H_MIN_ALLOCATION["stewardship_service"],
    employment_share: float = H_MIN_ALLOCATION["regular_employment"],
    workforce_size: float = 1.0,
    epsilon: float = 0.40,
) -> dict:
    """
    Allocate the minimum annual labor obligation across three functions.

    Every working-age collective member contributes a minimum of H_min hours
    per year (default 260), split across:
    - Competency rotation (40%): practice in an essential domain to maintain
      Condition IV. At high ε, this is the primary mechanism for reserve upkeep.
    - Stewardship service (30%): direct entropy resistance work on infrastructure.
    - Regular employment (30%): market or assigned labor.

    The total labor available from this obligation is h_min × workforce_size.
    At high ε, the rotation component is especially critical because fewer
    workers are engaged in full-time essential-domain work.

    Args:
        h_min: Minimum annual hours per worker. Default: 260.
        rotation_share: Fraction for competency rotation. Default: 0.40.
        stewardship_share: Fraction for stewardship. Default: 0.30.
        employment_share: Fraction for regular employment. Default: 0.30.
        workforce_size: Number of workers subject to h_min. Default: 1.0.
        epsilon: Automation level (for context; does not change allocation math).

    Returns:
        dict: {
          "h_min":                 float,
          "rotation_hours":        float,   (h_min × rotation_share)
          "stewardship_hours":     float,
          "employment_hours":      float,
          "total_hours":           float,   (= h_min)
          "workforce_size":        float,
          "total_rotation_eoh":    float,   (rotation_hours × workforce_size)
          "total_stewardship_eoh": float,
          "total_employment_eoh":  float,
          "total_labor_eoh":       float,   (h_min × workforce_size)
          "epsilon":               float,
        }

    Raises:
        ValueError: If shares do not sum to 1.0, or if h_min ≤ 0.

    Reference: Mission Statement §"Minimum labor obligation — 260 hours per
    year, split 40/30/30 across competency rotation, stewardship service,
    and regular employment."
    """
    if h_min <= 0:
        raise ValueError(f"h_min must be positive, got {h_min}")

    total_share = rotation_share + stewardship_share + employment_share
    if abs(total_share - 1.0) > 0.001:
        raise ValueError(
            f"rotation_share + stewardship_share + employment_share must equal 1.0, "
            f"got {total_share:.4f}"
        )

    rotation_hours    = h_min * rotation_share
    stewardship_hours = h_min * stewardship_share
    employment_hours  = h_min * employment_share

    return {
        "h_min":                 h_min,
        "rotation_hours":        rotation_hours,
        "stewardship_hours":     stewardship_hours,
        "employment_hours":      employment_hours,
        "total_hours":           rotation_hours + stewardship_hours + employment_hours,
        "workforce_size":        workforce_size,
        "total_rotation_eoh":    rotation_hours    * workforce_size,
        "total_stewardship_eoh": stewardship_hours * workforce_size,
        "total_employment_eoh":  employment_hours  * workforce_size,
        "total_labor_eoh":       h_min             * workforce_size,
        "epsilon":               epsilon,
    }


# ---------------------------------------------------------------------------
# Automation Failure Scenario
# ---------------------------------------------------------------------------

def automation_failure_scenario(
    epsilon: float,
    critical_eoh: float,
    reserve_capacity_eoh: float,
    h_min_labor_eoh: float,
    workforce_size: float = 1.0,
) -> dict:
    """
    Simulate sudden loss of automation and assess human workforce coverage.

    When automation fails at ε level, the EOH that was being handled
    by automation suddenly requires human labor. The workforce can respond
    with two sources:
    1. Competency reserve capacity: entropy-reduction capacity of the
       certified workers held in reserve across essential domains.
    2. Minimum hours labor: emergency mobilization of all workers at h_min.
       Every worker fulfills their minimum obligation on critical tasks.

    The coverage ratio determines severity:
    - ≥ 1.0: covered — workforce can absorb the automation failure
    - 0.75–1.0: MODERATE — close to adequate, short-term shortfall manageable
    - 0.50–0.75: SEVERE — significant gap; infrastructure will degrade quickly
    - < 0.50: CRITICAL — catastrophic gap; immediate structural failure

    Args:
        epsilon: Automation level at which failure occurs [0.0, 0.99].
        critical_eoh: EOH per year that automation was fulfilling and
                      now must be covered by human labor.
        reserve_capacity_eoh: Total entropy-reduction capacity of the
                              competency reserve workforce (EOH/year).
        h_min_labor_eoh: Total emergency labor available = h_min × workforce_size.
                         From minimum_hours_allocation()["total_labor_eoh"].
        workforce_size: Total workforce size (for informational output).

    Returns:
        dict: {
          "epsilon":                float,
          "critical_eoh":          float,
          "reserve_capacity_eoh":  float,
          "h_min_labor_eoh":       float,
          "human_coverage_total":  float,   (reserve + h_min)
          "coverage_ratio":        float,   (coverage / critical_eoh)
          "gap_eoh":               float,   (uncovered EOH; 0 if covered)
          "covered":               bool,
          "severity":              str,     ("NONE", "MODERATE", "SEVERE", "CRITICAL")
          "workforce_size":        float,
          "automation_eoh_fraction": float, (epsilon — how much was automated)
          "recommendation":        str,
        }

    Reference: Mission Statement §"Automation failure — the reserve must be
    sufficient to cover critical infrastructure EOH for at least one maintenance
    cycle without automation support."
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if critical_eoh < 0:
        raise ValueError(f"critical_eoh must be non-negative, got {critical_eoh}")
    if reserve_capacity_eoh < 0:
        raise ValueError(f"reserve_capacity_eoh must be non-negative, got {reserve_capacity_eoh}")
    if h_min_labor_eoh < 0:
        raise ValueError(f"h_min_labor_eoh must be non-negative, got {h_min_labor_eoh}")

    human_coverage = reserve_capacity_eoh + h_min_labor_eoh
    if critical_eoh <= 0.0:
        coverage_ratio = 1.0
        gap_eoh        = 0.0
        covered        = True
    else:
        coverage_ratio = human_coverage / critical_eoh
        gap_eoh        = max(0.0, critical_eoh - human_coverage)
        covered        = coverage_ratio >= 1.0 - 1e-9

    if covered:
        severity = "NONE"
        recommendation = (
            f"Workforce can absorb automation failure at ε={epsilon:.2f}. "
            f"Reserve ({reserve_capacity_eoh:,.0f} EOH/yr) + emergency h_min labor "
            f"({h_min_labor_eoh:,.0f} EOH/yr) covers critical demand "
            f"({critical_eoh:,.0f} EOH/yr). Coverage ratio: {coverage_ratio:.2f}."
        )
    elif coverage_ratio >= 0.75:
        severity = "MODERATE"
        recommendation = (
            f"Moderate gap at ε={epsilon:.2f}. Short-term shortfall manageable through "
            f"prioritization. Gap: {gap_eoh:,.0f} EOH/yr. "
            f"Increase h_min or reserve capacity before automation advances further."
        )
    elif coverage_ratio >= 0.50:
        severity = "SEVERE"
        recommendation = (
            f"Severe workforce gap at ε={epsilon:.2f}. Infrastructure degradation likely. "
            f"Gap: {gap_eoh:,.0f} EOH/yr ({100*(1-coverage_ratio):.0f}% uncovered). "
            f"Emergency competency training and reserve expansion required."
        )
    else:
        severity = "CRITICAL"
        recommendation = (
            f"CRITICAL failure at ε={epsilon:.2f}. Automation dependency too high. "
            f"Gap: {gap_eoh:,.0f} EOH/yr ({100*(1-coverage_ratio):.0f}% uncovered). "
            f"Immediate rollback of automation required; catastrophic infrastructure "
            f"failure probable without intervention."
        )

    return {
        "epsilon":                 epsilon,
        "critical_eoh":           critical_eoh,
        "reserve_capacity_eoh":   reserve_capacity_eoh,
        "h_min_labor_eoh":        h_min_labor_eoh,
        "human_coverage_total":   human_coverage,
        "coverage_ratio":         coverage_ratio,
        "gap_eoh":                gap_eoh,
        "covered":                covered,
        "severity":               severity,
        "workforce_size":         workforce_size,
        "automation_eoh_fraction": epsilon,
        "recommendation":         recommendation,
    }


def competency_to_knowledge_eoh_delta(
    reserve_result: dict,
    knowledge_eoh_base: float,
    gap_amplification: float = 2.0,
) -> dict:
    """
    Compute additional knowledge EOH demand from competency reserve gaps.

    When certified worker counts fall below the Condition IV threshold in
    essential domains, the knowledge maintenance burden increases: underskilled
    domains see faster skill atrophy and require more structured recovery
    training, both of which generate additional knowledge EOH.

    The result's "competency_gap_factor" is the fractional amplifier to pass
    into total_eoh(competency_gap_factor=...) — it scales the knowledge_eoh()
    result upward in proportion to the combined gap across all at-risk domains.

    Args:
        reserve_result: Return dict from competency_reserve().
        knowledge_eoh_base: The base knowledge EOH (hours/year) — used to
                            compute per-domain deltas. Pass knowledge_base
                            from total_eoh() calibration (default 100_000).
        gap_amplification: How steeply each unit of competency gap amplifies
                           knowledge EOH. Default 2.0 (2× per full-domain gap).

    Returns:
        dict: {
          "competency_gap_factor": float,   (pass to total_eoh())
          "knowledge_eoh_delta":   float,   (absolute EOH increase at knowledge_eoh_base)
          "domain_deltas":         dict,    (per-domain breakdown)
          "n_domains_at_risk":     int,
          "total_gap_fraction":    float,
        }

    Reference: Mission Statement §"Condition IV — Distributed Competency";
    §"Knowledge EOH — skills atrophy when the certified reserve shrinks."
    """
    per_domain = reserve_result.get("per_domain", {})
    total_gap_fraction = 0.0
    domain_deltas: dict[str, float] = {}

    for domain, info in per_domain.items():
        if not info.get("meets_threshold", True):
            gap_workers    = float(info.get("gap", 0.0))
            required_count = float(info.get("required_count", 1.0))
            gap_frac       = gap_workers / max(required_count, 1.0)
            domain_deltas[domain] = knowledge_eoh_base * gap_frac * gap_amplification
            total_gap_fraction   += gap_frac

    competency_gap_factor = total_gap_fraction * gap_amplification
    knowledge_eoh_delta   = knowledge_eoh_base * competency_gap_factor

    return {
        "competency_gap_factor": competency_gap_factor,
        "knowledge_eoh_delta":   knowledge_eoh_delta,
        "domain_deltas":         domain_deltas,
        "n_domains_at_risk":     reserve_result.get("n_domains_at_risk", 0),
        "total_gap_fraction":    total_gap_fraction,
    }


def apply_death_redistribution(
    death_result: dict,
    current_eoh_burden: float,
) -> dict:
    """
    Apply the EOH redistribution from a human capital write-down (death).

    execute_writedown() / death_event() return the redistribution obligation
    in their result dict but do not apply it — the caller must commit the
    redistribution by calling this function. Without this step, the deceased
    worker's EOH capacity is removed from the labor supply but their
    fulfillment obligation is silently orphaned.

    Semantics: the dead worker's entropy_reduction_capacity was covering a
    share of the collective EOH burden. That share now falls to the remaining
    workforce. current_eoh_burden is the total EOH the workforce was
    collectively responsible for; adding redistributed_eoh brings that burden
    to the correct post-death level.

    Args:
        death_result: Return dict from death_event() or execute_writedown()
                      for a human capital asset. Must contain
                      "eoh_to_redistribute" and "new_workforce".
        current_eoh_burden: Total EOH the workforce was responsible for
                            fulfilling before this death (hours/year).

    Returns:
        dict: {
          "redistributed_eoh":    float,  (= death_result["eoh_to_redistribute"])
          "new_workforce":        float,  (= death_result["new_workforce"])
          "additional_per_worker": float,  (redistributed / new_workforce)
          "new_total_eoh_burden": float,  (current + redistributed)
          "absorbed":             bool,   (True if any EOH was redistributed)
        }

    Reference: Mission Statement §"Humans as capital stock" — write-down of
    a human asset must zero their EOH contribution and redistribute the
    unmet obligation to remaining workers.
    """
    redistributed    = float(death_result.get("eoh_to_redistribute", 0.0))
    new_workforce    = float(death_result.get("new_workforce", 0.0))
    per_worker_extra = redistributed / max(new_workforce, 1.0)
    new_burden       = current_eoh_burden + redistributed

    return {
        "redistributed_eoh":     redistributed,
        "new_workforce":         new_workforce,
        "additional_per_worker": per_worker_extra,
        "new_total_eoh_burden":  new_burden,
        "absorbed":              redistributed > 0.0,
    }
