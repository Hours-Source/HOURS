"""
Membership-terms audit — reconciliation §8.7 (e).

EXPERIMENTAL TIER — not stable API.

The math/contract line (§8.7e): code owns everything that must hold no
matter what the agreements say — χ ≥ 1 for the marginal member, dτ/dε ≥ 0,
conservation across boundary events, exchange-rate conversion, and the
vesting arithmetic given a schedule. Collectives own the terms: vesting
length, admission rules, dividend policy, exit notice, minimum-hours
obligations. Terms enter the code as data structures with validators —

    the code is the constitutional court, not the legislature: the
    contract space is free, and the invariant is its boundary.

This is the operational form of §9-item-7's warning that membership rules
must not be drawn so tight that they themselves destroy χ ≥ 1. The audit
does not simulate the terms; it checks any proposed MembershipTerms against
the contestability invariant and reports OK/WARN/CRIT with reasons,
following the GovernanceInputs + assess_tier() validator pattern from
core/multipliers.py.

Public API:
    MembershipTerms — TypedDict of the term families collectives may set
    contestability_audit(terms, epsilon, ...) → dict

Mission Statement: reconciliation §8.7e (math/contract line); §9-item-7
(membership rules vs χ).
"""

from __future__ import annotations

from typing import TypedDict

from hours_eoh.data import (
    PERSONAL_EOH_BASE,
    TRUST_BASE_TEH,
    CONTESTABILITY_CHI_WARN,
    CONTESTABILITY_CHI_CRIT,
    CONTESTABILITY_VESTING_YEARS,
    MEMBERSHIP_VESTING_WARN_YEARS,
    MEMBERSHIP_EXIT_NOTICE_WARN_YEARS,
    MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS,
    MEMBERSHIP_MIN_HOURS_WARN_FRACTION,
    MEMBERSHIP_MIN_HOURS_CRIT_FRACTION,
    MEMBERSHIP_DIVIDEND_POLICY_WARN,
)
from hours_eoh.research.contestability import (
    entry_cost,
    entry_underwriting,
    portable_endowment_federated,
)


class MembershipTerms(TypedDict, total=False):
    """
    A collective's proposed membership contract. All fields optional —
    absent fields default to the framework's canonical values in the audit.

    These are exactly the term families §8.7(e) assigns to collectives
    (vesting, admission, dividend policy) plus the exit-friction term that
    §9-item-7 makes load-bearing. Split negotiations are boundary events
    (research/coasean.split_collective), not terms. Admission cost is
    treated as SUNK (non-refundable); a refundable buy-in would be part of
    the member's capital account and belongs in P — the schema deliberately
    cannot express it (see contestability_audit()).
    """
    vesting_years:            float  # dividend vesting schedule length (years)
    admission_cost_teh:       float  # sunk buy-in to join (TEH)
    exit_notice_years:        float  # notice before exit takes effect (years)
    minimum_hours_annual:     float  # labor obligation (hours/year, §9-item-7)
    dividend_policy_fraction: float  # share of pro-rata dividend distributed ∈ [0, 1]


def contestability_audit(
    terms: MembershipTerms,
    epsilon: float,
    collective_trust: float = TRUST_BASE_TEH,
    collective_population: float = 1_000_000.0,
    commons_balance: float = 0.0,
    federation_population: float | None = None,
    regime: str = "increasing_returns",
    commons_dividend: bool = False,
    underwriting_policy: bool = False,
) -> dict:
    """
    Audit proposed membership terms against the contestability invariant — §8.7e.

    Governing equations:
        k_eff        = K_entry(ε, regime) + admission_cost_teh
        p_marginal   = S(ε) + D_fed                             (tenure-0 member)
        p_vested     = p_marginal
                       + D_coll · dividend_policy_fraction      (fully vested)
        D_fed        = commons_balance · DEP_RATE · DIV_RATE / fed_pop
                       when commons_dividend=True, else 0       (§8.8 M1)
        χ_marginal   = p_marginal / k_eff   — CRIT below CONTESTABILITY_CHI_CRIT,
                                              WARN below CONTESTABILITY_CHI_WARN
        entry_capacity = UNDERWRITE_FRACTION · commons_balance
                         / (MIN_VIABLE_POPULATION · k_eff)      (§8.8 M2)
        exit_financeable ⇔ χ_marginal ≥ CHI_CRIT OR entry_capacity ≥ 1

    Underwriting capacity uses k_eff, not bare K_entry: if every collective
    charged the proposed admission cost, a commons-financed exit cohort
    would face it too — terms that inflate admission shrink the number of
    foundings the commons can finance, and the audit must see that.
    With underwriting_policy=True the χ_marginal CRIT escalation is waived
    when the commons can finance the founding instead (exit_financeable via
    M2) — it downgrades to WARN, because the marginal member's own endowment
    still cannot fund exit and the guarantee now depends on federation
    policy, not arithmetic in the member's hands. With the default False,
    entry_capacity and exit_financeable are reported informationally and
    the §8.7e escalation rules are unchanged.

    Admission cost enters K_entry, not P: the audit asks "if every collective
    adopted these terms, does exit stay substantive?" — the exiting marginal
    member must fund the founding cost OR a destination's admission charge,
    and both are sunk from their side of the boundary. The vesting schedule
    cannot rescue χ_marginal (tenure-0 has nothing vested); it is checked
    separately as friction.

    Checks (thresholds are named constants in data.py):
        1. χ_marginal < CHI_CRIT → CRIT; < CHI_WARN → WARN   (the core §9-item-7 check)
        2. vesting_years > MEMBERSHIP_VESTING_WARN_YEARS → WARN
        3. exit_notice_years > CRIT_YEARS → CRIT; > WARN_YEARS → WARN
           (exit deferred three years is nominal, not substantive — §8.1)
        4. minimum_hours_annual ≥ MIN_HOURS_CRIT_FRACTION × PERSONAL_EOH_BASE → CRIT
           (obligation equal to the whole personal entropy load is compulsion
           by definition); > WARN_FRACTION × base → WARN
        5. dividend_policy_fraction < MEMBERSHIP_DIVIDEND_POLICY_WARN → WARN
           (retention rebuilds the honeypot the escheat rule exists to defuse)
        6. commons_balance ≤ 0 → WARN (the floor component of P is unbacked).
           Coverage ADEQUACY is a scenario judgment, not a terms property —
           commons_floor_coverage is reported without escalation.

    Worked example (ε=0.40, defaults, admission=500 TEH):
        K_entry = 1800·(1+1.6·0.40) = 2952 ;  k_eff = 3452
        S ≈ 1476 → χ_marginal ≈ 0.43 "CRIT" — the terms fail the audit even
        though the same collective with zero admission is only at the
        framework's baseline breach (χ_marginal ≈ 0.50).

    ε-behavior: S falls and K_entry rises (increasing_returns) across the
    arc, so identical terms audit worse at higher ε — terms acceptable at
    subsistence can breach the invariant near post-scarcity. Meaningful
    across ε ∈ [0, 0.99].

    Args:
        terms: Proposed MembershipTerms (absent fields → canonical defaults:
            vesting CONTESTABILITY_VESTING_YEARS, admission 0, notice 0,
            minimum hours 0, dividend fraction 1.0).
        epsilon: Automation level [0.0, 0.99].
        collective_trust: The collective's trust balance (TEH).
        collective_population: The collective's population (> 0).
        commons_balance: Federation commons balance (TEH) backing the floor
            and, under §8.8, feeding the universal dividend and entry
            underwriting.
        federation_population: Total federation population (None → collective
            is the whole federation).
        regime: "increasing_returns" (default/adversarial) or "replicable".
        commons_dividend: Include the universal commons dividend in P
            (§8.8 M1). Default False — §8.7 behavior unchanged.
        underwriting_policy: Let commons-financed entry (§8.8 M2) waive the
            χ_marginal CRIT to WARN. Default False — §8.7e escalations
            unchanged; capacity is still reported.

    Returns:
        dict with keys: audit_status ("OK"|"WARN"|"CRIT"), warnings,
        passes (worst != "CRIT"), chi_marginal, chi_vested, status_marginal,
        k_entry_effective, p_marginal, p_vested, guarantee_per_person,
        dividend_per_capita, dividend_commons, entry_capacity,
        exit_financeable, commons_floor_coverage, epsilon, regime,
        terms (echo).
    """
    vesting_years = terms.get("vesting_years", CONTESTABILITY_VESTING_YEARS)
    admission_cost = terms.get("admission_cost_teh", 0.0)
    exit_notice = terms.get("exit_notice_years", 0.0)
    minimum_hours = terms.get("minimum_hours_annual", 0.0)
    dividend_fraction = terms.get("dividend_policy_fraction", 1.0)

    if vesting_years <= 0.0:
        raise ValueError(f"vesting_years must be > 0, got {vesting_years}")
    if admission_cost < 0.0:
        raise ValueError(f"admission_cost_teh must be >= 0, got {admission_cost}")
    if exit_notice < 0.0:
        raise ValueError(f"exit_notice_years must be >= 0, got {exit_notice}")
    if minimum_hours < 0.0:
        raise ValueError(f"minimum_hours_annual must be >= 0, got {minimum_hours}")
    if not 0.0 <= dividend_fraction <= 1.0:
        raise ValueError(
            f"dividend_policy_fraction must be in [0, 1], got {dividend_fraction}"
        )

    # Two-tier P under the proposed terms (ε validation happens here too).
    endowment = portable_endowment_federated(
        epsilon,
        collective_trust=collective_trust,
        collective_population=collective_population,
        federation_population=federation_population,
        tenure_years=vesting_years,   # fully vested member
        vesting_years=vesting_years,
        commons_balance=commons_balance if commons_dividend else 0.0,
    )
    s = endowment["guarantee_per_person"]
    dividend_full = endowment["dividend_full"]
    dividend_commons = endowment["dividend_commons"]

    k_entry_base = entry_cost(epsilon, regime)
    k_eff = k_entry_base + admission_cost
    p_marginal = s + dividend_commons
    p_vested = p_marginal + dividend_full * dividend_fraction
    chi_marginal = p_marginal / k_eff
    chi_vested = p_vested / k_eff

    # §8.8 M2 — commons-financed entry against the EFFECTIVE founding cost:
    # admission charges raise what an exit cohort must fund, so they shrink
    # the commons' capacity too. entry_underwriting() supplies the policy
    # constants; its k_entry is replaced by k_eff via the capacity identity
    # capacity = deployable / (min_viable · k).
    uw = entry_underwriting(epsilon, commons_balance, regime)
    entry_capacity = uw["deployable"] / (uw["min_viable_population"] * k_eff)
    exit_financeable = (
        chi_marginal >= CONTESTABILITY_CHI_CRIT or entry_capacity >= 1.0
    )

    warnings: list[str] = []
    severity_levels = {"OK": 0, "WARN": 1, "CRIT": 2}
    worst = "OK"

    def _escalate(level: str, message: str) -> None:
        warnings.append(message)
        nonlocal worst
        if severity_levels[level] > severity_levels[worst]:
            worst = level

    # 1. The core check: the marginal member's exit under these terms.
    #    A commons that can finance the founding (§8.8 M2) downgrades the
    #    breach to WARN: exit stays financeable, but by federation policy
    #    rather than arithmetic in the member's own hands.
    if chi_marginal < CONTESTABILITY_CHI_CRIT:
        if underwriting_policy and entry_capacity >= 1.0:
            _escalate("WARN",
                f"chi_marginal={chi_marginal:.3f} < {CONTESTABILITY_CHI_CRIT} "
                f"but entry_capacity={entry_capacity:.1f} ≥ 1: exit is "
                "commons-financed, not self-financed — substantive only "
                "while the underwriting policy holds (§8.8)")
        else:
            _escalate("CRIT",
                f"chi_marginal={chi_marginal:.3f} < {CONTESTABILITY_CHI_CRIT} "
                f"and entry_capacity={entry_capacity:.3f} < 1: under these "
                "terms the tenure-0 member cannot fund exit and the commons "
                "cannot finance it — the invariant is breached (§9-item-7)")
    elif chi_marginal < CONTESTABILITY_CHI_WARN:
        _escalate("WARN",
            f"chi_marginal={chi_marginal:.3f} < {CONTESTABILITY_CHI_WARN}: "
            "marginal member's exit margin is thinning")

    # 2. Vesting friction.
    if vesting_years > MEMBERSHIP_VESTING_WARN_YEARS:
        _escalate("WARN",
            f"vesting_years={vesting_years} > MEMBERSHIP_VESTING_WARN_YEARS="
            f"{MEMBERSHIP_VESTING_WARN_YEARS}: dividend held hostage that long "
            "thins exit for most members")

    # 3. Exit notice.
    if exit_notice > MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS:
        _escalate("CRIT",
            f"exit_notice_years={exit_notice} > "
            f"{MEMBERSHIP_EXIT_NOTICE_CRIT_YEARS}: exit deferred that long is "
            "nominal, not substantive (§8.1)")
    elif exit_notice > MEMBERSHIP_EXIT_NOTICE_WARN_YEARS:
        _escalate("WARN",
            f"exit_notice_years={exit_notice} > "
            f"{MEMBERSHIP_EXIT_NOTICE_WARN_YEARS}: exit friction accumulating")

    # 4. Minimum-hours obligation vs the personal entropy load.
    min_hours_crit = MEMBERSHIP_MIN_HOURS_CRIT_FRACTION * PERSONAL_EOH_BASE
    min_hours_warn = MEMBERSHIP_MIN_HOURS_WARN_FRACTION * PERSONAL_EOH_BASE
    if minimum_hours >= min_hours_crit:
        _escalate("CRIT",
            f"minimum_hours_annual={minimum_hours} >= {min_hours_crit}: "
            "obligation equals the full personal EOH load — membership is "
            "compulsion by definition")
    elif minimum_hours > min_hours_warn:
        _escalate("WARN",
            f"minimum_hours_annual={minimum_hours} > {min_hours_warn}: "
            "obligation above half the personal entropy load (§9-item-7)")

    # 5. Dividend retention.
    if dividend_fraction < MEMBERSHIP_DIVIDEND_POLICY_WARN:
        _escalate("WARN",
            f"dividend_policy_fraction={dividend_fraction} < "
            f"{MEMBERSHIP_DIVIDEND_POLICY_WARN}: retention rebuilds the "
            "honeypot inside the collective")

    # 6. Commons backing (structural emptiness only; adequacy is a scenario
    #    judgment reported via commons_floor_coverage without escalation).
    fed_pop = (
        collective_population if federation_population is None
        else federation_population
    )
    floor_liability = s * fed_pop
    commons_floor_coverage = commons_balance / max(floor_liability, 1e-9)
    if commons_balance <= 0.0:
        _escalate("WARN",
            "commons_balance <= 0: the federation commons is empty — the "
            "floor component of P is unbacked (§8.7a)")

    return {
        "audit_status":           worst,
        "warnings":               warnings,
        "passes":                 worst != "CRIT",
        "chi_marginal":           chi_marginal,
        "chi_vested":             chi_vested,
        "status_marginal":        (
            "OK" if chi_marginal >= CONTESTABILITY_CHI_WARN
            else "WARN" if chi_marginal >= CONTESTABILITY_CHI_CRIT
            else "CRIT"
        ),
        "k_entry_effective":      k_eff,
        "p_marginal":             p_marginal,
        "p_vested":               p_vested,
        "guarantee_per_person":   s,
        "dividend_per_capita":    dividend_full,
        "dividend_commons":       dividend_commons,
        "entry_capacity":         entry_capacity,
        "exit_financeable":       exit_financeable,
        "commons_floor_coverage": commons_floor_coverage,
        "epsilon":                epsilon,
        "regime":                 regime,
        "terms": {
            "vesting_years":            vesting_years,
            "admission_cost_teh":       admission_cost,
            "exit_notice_years":        exit_notice,
            "minimum_hours_annual":     minimum_hours,
            "dividend_policy_fraction": dividend_fraction,
        },
    }
