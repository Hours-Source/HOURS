"""
Structural Condition Verification

Monitors for all three foundational conditions plus Condition IV (recommended).

Condition I:   Ledger Identity — TEH supply = cumulative creation - destruction
Condition II:  Multiplier Band — mean multiplier ∈ [M_BAND_LOW, M_BAND_HIGH]
Condition III: Zero Interest — balances change only through earnings/expenditures
Condition IV:  Distributed Competency — ≥15.5% of workforce certified in essential domains

The dashboard is not a summary — it is a structural integrity check.
If all conditions show green, the system is coherent.
If any shows red, the papers have a problem, not the code.

Mission Statement: §"Structural Conditions", §"Principle 8 — The code is
the constitution's test bench"
"""

from __future__ import annotations

import warnings

from hours_eoh.data import (
    M_BAND_LOW, M_BAND_HIGH, M_BAND_TARGET, COMPETENCY_THRESHOLD,
    MEAN_MULTIPLIER_REFERENCE, MEASURED_CAPACITY_H_YR,
)
from hours_eoh.core.multipliers import multiplier_band_check


# ---------------------------------------------------------------------------
# Condition I Monitor — Ledger Identity
# ---------------------------------------------------------------------------

def condition_i_check(
    teh_created: float,
    teh_destroyed: float,
    teh_observed: float,
    tolerance: float = 1e-6,
) -> dict:
    """
    Condition I: Ledger Identity.

    Verify that TEH in circulation equals cumulative creation minus cumulative
    destruction. Any discrepancy is a ledger violation — either TEH is being
    created outside the EOH fulfillment pipeline (a structural error) or being
    destroyed through a mechanism other than terminal consumption or capital
    write-down (also a structural error).

    Note: spending and levies are circulatory — they do NOT appear in creation
    or destruction totals. A levy that moves TEH from workers to the Trust does
    not change the total supply and should produce a discrepancy of zero.

    Args:
        teh_created: Cumulative TEH created through verified EOH fulfillment.
        teh_destroyed: Cumulative TEH destroyed (terminal consumption + write-downs).
        teh_observed: Actual TEH observed in circulation (sum of all account balances).
        tolerance: Fractional tolerance for floating-point comparison. Default: 1e-6.

    Returns:
        dict with "expected", "observed", "discrepancy", "relative_discrepancy",
        "passes" (bool), "status" ("OK" or "LEDGER_VIOLATION").

    Reference: Mission Statement §"Condition I — Ledger Identity"
    """
    expected = teh_created - teh_destroyed
    discrepancy = abs(teh_observed - expected)
    relative_disc = discrepancy / max(abs(expected), 1.0)
    passes = relative_disc <= tolerance

    return {
        "expected":              expected,
        "observed":              teh_observed,
        "discrepancy":           discrepancy,
        "relative_discrepancy":  relative_disc,
        "passes":                passes,
        "status":                "OK" if passes else "LEDGER_VIOLATION",
    }


# ---------------------------------------------------------------------------
# Condition II Monitor — Multiplier Band (delegates to multipliers.py)
# ---------------------------------------------------------------------------

def condition_ii_check(
    mean_multiplier: float,
    band_low: float = M_BAND_LOW,
    band_high: float = M_BAND_HIGH,
) -> dict:
    """
    Condition II: Multiplier Band.

    Verify that the population-weighted mean multiplier is within [band_low, band_high].
    Delegates to multipliers.multiplier_band_check() for the full result dict.

    Reference: Mission Statement §"Condition II — Multiplier Band"
    """
    return multiplier_band_check(mean_multiplier, band_low, band_high)


# ---------------------------------------------------------------------------
# Condition III Monitor — Zero Interest
# ---------------------------------------------------------------------------

def balance_check(
    balance_start: float,
    earnings: float,
    expenditures: float,
    balance_end: float,
    tolerance: float = 1e-6,
) -> dict:
    """
    Condition III: Zero Interest.

    Verify: B(t+Δt) = B(t) + E(t,Δt) - X(t,Δt). No third term.

    Account balances must change ONLY through earnings (labor income, transfers
    received) and expenditures (payments, transfers sent). Any growth without
    corresponding labor is an interest violation — it would create currency
    measuring entropy resistance that was never performed.

    This function checks a single account over a single period. To verify the
    whole system, call it for every account in the ledger.

    Note: Levies that move TEH from worker to Trust are an expenditure for the
    worker and an earning for the Trust — they satisfy this condition.

    Args:
        balance_start: Account balance at start of period (TEH).
        earnings: Total TEH received during period (labor income + transfers in).
        expenditures: Total TEH paid out during period (purchases + transfers out).
        balance_end: Account balance at end of period (TEH).
        tolerance: Fractional tolerance. Default: 1e-6.

    Returns:
        dict with "expected_end", "observed_end", "discrepancy",
        "relative_discrepancy", "passes" (bool), "status".

    Reference: Mission Statement §"Condition III — Zero Interest" —
    "Account balances change only through earnings and expenditures."
    """
    expected_end = balance_start + earnings - expenditures
    discrepancy = abs(balance_end - expected_end)
    relative_disc = discrepancy / max(abs(expected_end), 1.0)
    passes = relative_disc <= tolerance

    return {
        "balance_start":         balance_start,
        "earnings":              earnings,
        "expenditures":          expenditures,
        "expected_end":          expected_end,
        "observed_end":          balance_end,
        "discrepancy":           discrepancy,
        "relative_discrepancy":  relative_disc,
        "passes":                passes,
        "status":                "OK" if passes else "INTEREST_VIOLATION",
    }


def condition_iii_balance_growth_check(
    prev_balance: float,
    new_balance: float,
    labor_income: float,
    expenditure: float,
    tolerance: float = 1e-6,
) -> dict:
    """
    Assert that a balance delta is entirely labor-derived (Condition III).

    Enforces the zero-interest invariant for a single period: the only valid
    source of balance growth is labor income minus expenditure. Any other growth
    (compounding, fractional reserve, residual rounding that accumulates) is an
    interest violation.

    This is a named wrapper around balance_check() that makes the Condition III
    assertion explicit — the balance delta must equal labor_income - expenditure.
    Use this when you have period-over-period balances and want to assert that
    no third-party mechanism (market interest, platform fees, etc.) inflated them.

    Args:
        prev_balance: Account balance at start of period (TEH).
        new_balance:  Account balance at end of period (TEH).
        labor_income: TEH earned through labor this period (inflow).
        expenditure:  TEH paid out this period (outflow).
        tolerance:    Fractional tolerance for floating-point comparisons.

    Returns:
        Same dict as balance_check(): "passes", "status", "discrepancy", etc.
        "status" is "OK" when the invariant holds, "INTEREST_VIOLATION" when not.

    Reference: Mission Statement §"Condition III — Zero Interest" — balances
    change only through labor income and expenditure; no compounding or interest.
    """
    return balance_check(prev_balance, labor_income, expenditure, new_balance, tolerance)


# ---------------------------------------------------------------------------
# Condition IV Monitor — Distributed Competency (recommended)
# ---------------------------------------------------------------------------

def condition_iv_check(
    workforce: float,
    competent_workers: float,
    threshold: float = COMPETENCY_THRESHOLD,
    domain_coverage: dict[str, float] | None = None,
) -> dict:
    """
    Condition IV: Distributed Competency (recommended).

    Verify that a minimum share of the workforce maintains certified competency
    across essential infrastructure domains. Recommended threshold: 15.5%.

    Without this, the system is monetarily sound but vulnerable to catastrophic
    failure when automation fails. The Sufficiency Guarantee promises real
    purchasing power — but purchasing power requires goods and services to exist,
    which requires human capacity to produce them when automation fails.

    Condition IV is what makes the floor credible under stress.

    Args:
        workforce: Total employed workforce.
        competent_workers: Workers with current certifications in essential domains.
        threshold: Minimum required fraction. Default: 0.155 (15.5%).
        domain_coverage: Optional dict mapping domain name → fraction of minimum
                         requirement met (1.0 = fully met, <1.0 = deficit).

    Returns:
        dict with "reserve_fraction", "threshold", "passes" (bool), "status",
        and per-domain breakdown if domain_coverage is provided.

    Reference: Mission Statement §"Condition IV — Distributed Competency" —
    "an economy that cannot fall back on distributed human competency across
    essential domains is one cascading failure away from collapse."
    """
    reserve_fraction = competent_workers / max(workforce, 1.0)
    passes = reserve_fraction >= threshold

    result: dict = {
        "competent_workers": competent_workers,
        "workforce":         workforce,
        "reserve_fraction":  reserve_fraction,
        "threshold":         threshold,
        "passes":            passes,
        "status":            "OK" if passes else "COMPETENCY_DEFICIT",
    }

    if domain_coverage is not None:
        domains_ok = {d: (v >= 1.0) for d, v in domain_coverage.items()}
        result["domain_coverage"] = domain_coverage
        result["domains_ok"] = domains_ok
        result["all_domains_ok"] = all(domains_ok.values())
        # Upgrade status if domain-level gaps exist even if aggregate passes
        if passes and not result["all_domains_ok"]:
            result["status"] = "DOMAIN_GAP"

    return result


# ---------------------------------------------------------------------------
# Composite Dashboard Snapshot
# ---------------------------------------------------------------------------

def dashboard_snapshot(
    *,
    teh_created: float,
    teh_destroyed: float,
    teh_observed: float,
    mean_multiplier: float,
    balance_start: float,
    earnings: float,
    expenditures: float,
    balance_end: float,
    workforce: float,
    competent_workers: float,
    epsilon: float = 0.40,
    band_low: float = M_BAND_LOW,
    band_high: float = M_BAND_HIGH,
    competency_threshold: float = COMPETENCY_THRESHOLD,
) -> dict:
    """
    Composite structural integrity snapshot across all four conditions.

    The dashboard is not a summary — it is a structural integrity check.
    If all_pass=True, the system is self-consistent at this epsilon.
    If all_pass=False, the failing condition identifies the specific mechanism
    that is broken (Principle 8: the code is the constitution's test bench).

    All arguments are keyword-only to prevent accidental positional errors
    in this high-stakes function.

    Args:
        teh_created: Cumulative TEH created.
        teh_destroyed: Cumulative TEH destroyed.
        teh_observed: TEH currently in circulation.
        mean_multiplier: Population-weighted mean multiplier.
        balance_start: Account balance at period start.
        earnings: Total earnings this period.
        expenditures: Total expenditures this period.
        balance_end: Account balance at period end.
        workforce: Total employed workforce.
        competent_workers: Workers certified in essential domains.
        epsilon: Automation level (for context/reporting only).
        band_low: Multiplier band lower bound.
        band_high: Multiplier band upper bound.
        competency_threshold: Condition IV threshold.

    Returns:
        dict with "epsilon", per-condition results, "all_pass" (bool),
        "overall_status" ("GREEN" or "RED").

    Reference: Mission Statement §"Principle 8 — The code is the constitution's
    test bench. If the dashboard shows green, the system works. If it shows
    red, the papers have a problem, not the code."
    Adopted reading (transparency pass, 2026-08-15; docs Design Principle 8):
    "GREEN" means every condition checked passes on the inputs given, not that
    the system works.
    """
    c1 = condition_i_check(teh_created, teh_destroyed, teh_observed)
    c2 = condition_ii_check(mean_multiplier, band_low, band_high)
    c3 = balance_check(balance_start, earnings, expenditures, balance_end)
    c4 = condition_iv_check(workforce, competent_workers, competency_threshold)

    all_pass = c1["passes"] and c2["in_band"] and c3["passes"] and c4["passes"]

    return {
        "epsilon":         epsilon,
        "condition_i":     c1,
        "condition_ii":    c2,
        "condition_iii":   c3,
        "condition_iv":    c4,
        "all_pass":        all_pass,
        "overall_status":  "GREEN" if all_pass else "RED",
    }


# ---------------------------------------------------------------------------
# Domain-level EOH coverage check
# ---------------------------------------------------------------------------

def domain_eoh_coverage(
    reserve_result: dict,
    domain_eoh_demands: dict[str, float],
    epsilon: float = 0.40,
    mean_multiplier: float = MEAN_MULTIPLIER_REFERENCE,
    coverage_warning_threshold: float = 0.80,
) -> dict:
    """
    DEPRECATED 2026-10-01 — use `condition_iv_coverage`. Output unchanged, so
    every earlier figure reproduces; it warns.

    WHY. Capacity per certified worker here is `H_MIN × mean_multiplier ×
    (1 − ε)`: the multiplier converts hours to TEH, not to EOH, and (1 − ε)
    shrinks a WORKER's hours as machines take share, where the human share
    belongs on DEMAND. At threshold certification on the arc it reported
    Condition IV failing at every ε and worse as automation rose (coverage
    → 0 at ε = 0.99) — the opposite of the physics.

    Check whether certified workforce capacity can actually cover per-domain EOH.

    Condition IV verifies certified fractions but not whether those workers can
    fulfill the domain's full EOH demand. If a domain's EOH has grown faster
    than certified capacity (e.g., infrastructure aged while reserve stayed flat),
    the Condition IV check passes but the domain is in real shortfall.

    Capacity per certified worker = h_min × mean_multiplier × (1-ε).
    (At high ε, each worker's human-labor share shrinks — more workers are
    needed to cover the same human EOH demand.)

    Args:
        reserve_result: Return dict from competency_reserve().
        domain_eoh_demands: {domain_name: annual_eoh_hours} for domains to check.
        epsilon: Automation level. Scales certified capacity by (1-ε).
        mean_multiplier: Worker EOH throughput per hour (default: 2.10).
        coverage_warning_threshold: Flag domains below this coverage ratio.
                                    Default: 0.80 (80% of demand covered).

    Returns:
        dict: {
          "per_domain": {domain: {
            "eoh_demand":     float,
            "certified_count": float,
            "capacity_eoh":   float,
            "coverage_ratio": float,
            "meets_coverage": bool,
          }},
          "domains_at_risk":            list[str],
          "all_covered":                bool,
          "status":                     "OK" or "COVERAGE_GAP",
          "epsilon":                    float,
          "coverage_warning_threshold": float,
        }

    Reference: Mission Statement §"Condition IV — Distributed Competency" —
    reserve size is necessary but not sufficient; coverage requires capacity
    to match demand, not just a fraction to exceed a threshold.
    """
    from hours_eoh.data import H_MIN

    warnings.warn(
        "domain_eoh_coverage is deprecated (2026-10-01): it sizes a certified "
        "worker as H_MIN × the TEH multiplier × (1 − ε). Use condition_iv_coverage.",
        DeprecationWarning, stacklevel=2,
    )
    per_domain_reserve = reserve_result.get("per_domain", {})
    human_fraction     = 1.0 - epsilon
    domain_coverage: dict[str, dict] = {}
    domains_at_risk: list[str] = []

    for domain, eoh_demand in domain_eoh_demands.items():
        certified = float(
            per_domain_reserve.get(domain, {}).get("certified_count", 0.0)
        )
        # Each certified worker contributes H_MIN hours × multiplier × human_fraction
        capacity_eoh = certified * H_MIN * mean_multiplier * human_fraction

        if eoh_demand <= 0.0:
            coverage_ratio = 1.0
        else:
            coverage_ratio = capacity_eoh / eoh_demand

        meets_coverage = coverage_ratio >= coverage_warning_threshold
        domain_coverage[domain] = {
            "eoh_demand":     eoh_demand,
            "certified_count": certified,
            "capacity_eoh":   capacity_eoh,
            "coverage_ratio": coverage_ratio,
            "meets_coverage": meets_coverage,
        }

        if not meets_coverage:
            domains_at_risk.append(domain)

    all_covered = len(domains_at_risk) == 0

    return {
        "per_domain":                 domain_coverage,
        "domains_at_risk":            domains_at_risk,
        "all_covered":                all_covered,
        "status":                     "OK" if all_covered else "COVERAGE_GAP",
        "epsilon":                    epsilon,
        "coverage_warning_threshold": coverage_warning_threshold,
    }


def condition_iv_coverage(
    reserve_result: dict,
    pipeline: dict,
    demand: str = "registered",
    hours_per_certified_worker: float = MEASURED_CAPACITY_H_YR,
    weights: dict[str, dict[str, float]] | None = None,
) -> dict:
    """
    Can the people certified in each essential domain carry its work?
    Condition IV in hours (2026-10-01).

    Governing relation, per essential domain d:

        capacity_d = certified_d × hours_per_certified_worker         [h/yr]
        demand_d   = Σ_k  w(d, k) × D_k                               [h/yr]
        covered_d  ⇔  capacity_d ≥ demand_d

    where D_k is the demand in EOH domain k read off `pipeline` (an
    `eoh_to_teh_pipeline` result) and w the essential-domain bridge
    (`eoh_generation.eoh_to_essential_domains`). No threshold is chosen: a
    domain is covered or it is not.

    THREE DECLARED CHOICES — what the verdict rests on:

    1. CAPACITY is a certified adult's measured annual capacity
       (`MEASURED_CAPACITY_H_YR`, the one settled account of adult supply),
       independent of ε — a worker's hours do not shrink as machines take
       share. `H_MIN`, which the deprecated check used, is the MINIMUM a
       member owes, not what one can give.
    2. DEMAND defaults to the REGISTERED hours: the register is what the
       collective carries (author, 2026-10-01), and certified workers are the
       collective's competency — household self-maintenance off the ledger is
       not theirs to cover. `demand="personal"` reads only the registered
       PERSONAL hours: the survivability tier (author, 2026-10-01: "the people
       (agent needs) should be what needs to be covered, the rest can build back
       over time"), the same priority `labor_constrained_fulfillment` serves
       first. `demand="human"` reads all human-carried hours.
       Any shortfall sits in a band of the upper arc, which the four
       reporting points can miss (mode 3) — call the function on a fine grid.
       `dashboard.system_dashboard` and the shocks read both "personal"
       (a shortfall fails Condition IV) and "registered" (a warning).
    3. THE BRIDGE. Its personal column is DERIVED from the obligation's
       components (`data.ESSENTIAL_BRIDGE_PERSONAL`, 2026-10-01); the other
       three columns are the original judgement. Care has its own essential
       domain since 2026-10-01 and is most of the personal obligation, so it is
       the domain that binds. Hours no domain is certified for are reported as
       `unattributed_eoh`, never counted as a shortfall. Pass `weights=` to
       test another bridge.

    ε-behaviour: capacity is ε-invariant; demand follows the pipeline, so
    coverage moves only through what people are asked to carry.

    Args:
        reserve_result: `workforce.competency_reserve(...)` — certified counts.
        pipeline: An `eoh_to_teh_pipeline(...)` result at the state in question.
        demand: "registered" (default), "personal" or "human".
        hours_per_certified_worker: h/yr one certified adult can supply.
        weights: Bridge override, {essential_domain: {eoh_domain: share}}.

    Returns:
        dict with `per_domain` {d: {demand_eoh, certified_count, capacity_eoh,
        coverage_ratio, covered}}, `domains_short`, `all_covered`, `status`
        ("OK" / "COVERAGE_GAP"), `demand_reading`, `hours_per_certified_worker`.
    """
    from hours_eoh.core.eoh_generation import UNATTRIBUTED_ESSENTIAL, eoh_to_essential_domains

    readings = {"registered": "registered_eoh_by_domain", "personal": "registered_eoh_by_domain",
                "human": "human_eoh_by_domain"}
    if demand not in readings:
        raise ValueError(f"demand must be one of {sorted(readings)}, got {demand!r}")
    if hours_per_certified_worker <= 0.0:
        raise ValueError(
            f"hours_per_certified_worker must be > 0, got {hours_per_certified_worker}")
    source = pipeline[readings[demand]]
    by_eoh = {k: float(source[k]) for k in
              ("personal", "infrastructure", "ecological", "knowledge")}
    if demand == "personal":
        by_eoh = {k: (v if k == "personal" else 0.0) for k, v in by_eoh.items()}
    by_essential = eoh_to_essential_domains(by_eoh, weights)
    unattributed = float(by_essential.pop(UNATTRIBUTED_ESSENTIAL, 0.0))

    reserve = reserve_result.get("per_domain", {})
    per_domain: dict[str, dict] = {}
    short: list[str] = []
    for d, demand_eoh in by_essential.items():
        certified = float(reserve.get(d, {}).get("certified_count", 0.0))
        capacity = certified * hours_per_certified_worker
        ratio = capacity / demand_eoh if demand_eoh > 0.0 else float("inf")
        covered = capacity >= demand_eoh
        per_domain[d] = {
            "demand_eoh":      demand_eoh,
            "certified_count": certified,
            "capacity_eoh":    capacity,
            "coverage_ratio":  ratio,
            "covered":         covered,
        }
        if not covered:
            short.append(d)
    return {
        "per_domain":                 per_domain,
        "domains_short":              short,
        "all_covered":                not short,
        "status":                     "OK" if not short else "COVERAGE_GAP",
        "demand_reading":             demand,
        "unattributed_eoh":           unattributed,
        "hours_per_certified_worker": hours_per_certified_worker,
    }
