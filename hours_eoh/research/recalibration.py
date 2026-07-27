"""
Recalibration prototype — proposed §8.9 (mutually-consistent commons
accounting) and §8.9b (charter-formation doctrine).

EXPERIMENTAL TIER — not stable API. §8.9 adopted-in-principle by the author
2026-07-26; the §8.9b doctrine bundle (charter formation, dilution default,
escalation clause) agreed the same session. Formal reconciliation-doc edit
pending. Functional forms are proposed and flagged, not calibrated.

§8.9 — resolves the three §8.8 "honest remainders" at their causes:

1.  RC4 (flow vs stock).  χ = P/K_entry divided an ANNUAL income flow by a
    ONE-TIME founding stock. A stock target against a flow yields a TIME:
        t_exit(ε) = years to accumulate K_entry from savable flow
    with the invariant  t_exit ≤ RECAL_EXIT_HORIZON_YEARS  (one vesting
    period), plus a genuine accumulating §8.7b capital account
    (capital_account_stock(), Mondragon precedent, zero-interest).

2.  Open item 3 (τ = 17.5 for a share ≤ 1).  K(ε) = K₀ + ν·Y(ε) grows with
    the machine output it must produce; the commons OWNS share φ(ε) of it
    (Meade's social-dividend model), so:
        τ(ε) = φ_actual(ε) ≤ 1        by construction
        dτ/dε ≥ 0                      structural (φ_actual non-decreasing)

3.  Self-financing dropped as the test.  Exit finance has three channels —
    labor (low ε), commons underwriting (mid-arc trough), dividend savings
    (high ε):
        exit_financeable ⇔ t_exit_self ≤ horizon OR entry_capacity ≥ 1

§8.9b — the charter-formation doctrine (phi_policy):

    "target"    §8.9a purchase model: the commons BUYS its rising share out
                of capital income (regression anchor; keeps the published
                §8.9 numbers reproducible).
    "dilution"  DEFAULT DOCTRINE: the commons' share attaches to NEW capital
                at commissioning as a federation charter condition
                (resource-license / Georgist model — automation value
                derives from the common inheritance the four EOH domains
                measure). Nothing is purchased: the commons never spends
                income on acquisition, so the dividend is the full φ·Y.
                Private capital is NEVER sold down — it follows a ratchet
                (can rise, never falls by sale); where keeping φ on target
                would require selling private holdings (s_required > 1,
                from ε ≈ 0.48 at defaults), φ_actual falls below φ_target
                instead. Generational conversion (capital-estate escheat at
                ESTATE_LEVY_FRACTION — the D5 doctrine extended to capital)
                trims the ratchet at mortality speed.
    "escalated" dilution + the charter escalation clause: if the adversarial
                regime is observed AND contestability degrades
                (entry_capacity < RECAL_ESCALATION_CAPACITY_FLOOR, or the
                invariant failing), the charter escalates — the commons
                takes ALL new formation (s = 1) and the capital-estate
                escheat rises to RECAL_ESCALATION_ESTATE_SHARE. No living
                holder is ever divested; convergence toward φ_target happens
                at mortality speed (§8.2's "φ must be ABLE to → 1" becomes
                an asymptotic capability, not a trajectory). At canonical
                defaults the trigger NEVER fires — the brake exists and
                stays off.

Honest §8.9b findings at defaults (reported, not tuned):
    - The no-sale ratchet caps φ_actual at ≈ 0.66 by ε = 0.99 (target 0.99);
      the invariant still holds at every arc point, with a smaller dividend
      (≈ 1,600 vs 1,873 TEH/person·yr at ε = 0.99).
    - The early-arc funding gap of §8.9a DISAPPEARS under the charter
      (nothing is purchased); the compensated-bridge alternative is a
      ≈ 1% levy on labor-era output, sunsetting by ε ≈ 0.2
      (formation_levy_rate()).
    - The charter share is an implicit tax on private capital formation;
      the model does NOT simulate the investment-disincentive feedback on
      K(ε) — open item, flagged.

Public functions:
    capital_stock_epsilon(epsilon, population, capital_output_ratio) → float
    phi_actual(epsilon, phi_policy, ...) → dict
    commons_capital(epsilon, population, ..., phi_policy) → dict
    formation_share_required(epsilon, ...) → dict
    formation_levy_rate(epsilon, ...) → dict
    commons_income_statement(epsilon, ..., phi_policy) → dict
    capital_account_stock(tenure_years, epsilon, ..., phi_policy) → dict
    estate_conversion_flow(epsilon, escheat_share, ...) → dict
    escalation_trigger(epsilon, regime, ...) → dict
    exit_financing(epsilon, ..., phi_policy) → dict
    recalibrated_arc(n_points, regime, ..., phi_policy, estate_escheat_share) → list[dict]

Mission Statement: §"Contestability — the invariant the arc must preserve."
"""

from __future__ import annotations

import math

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    ANNUAL_DEATH_RATE,
    CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_MIN_VIABLE_POPULATION,
    CONTESTABILITY_UNDERWRITE_FRACTION,
    FORMATION_DEPRECIATION_RATE,
    RECAL_ACCOUNT_CREDIT_SHARE,
    RECAL_CAPITAL_OUTPUT_RATIO,
    RECAL_EPSILON_RATE_PER_YEAR,
    RECAL_ESCALATION_CAPACITY_FLOOR,
    RECAL_ESCALATION_ESTATE_SHARE,
    RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    RECAL_EXIT_HORIZON_YEARS,
    RECAL_FOUNDING_LABOR_HOURS,
)
from hours_eoh.research.contestability import (
    commonized_fraction,
    entry_cost,
    machine_output_teh,
)

# Finite-difference step in ε for arc-derivative metrics. Numerical
# parameter, not domain calibration: results are insensitive at this size.
_FD_STEP: float = 0.01

# Grid step for the private-capital ratchet running-max. Numerics only.
_RATCHET_STEP: float = 0.01

# Top of the ε range (CLAUDE.md design invariant: ε ∈ [0, 0.99]).
_EPS_MAX: float = 0.99

_PHI_POLICIES = ("target", "dilution", "escalated")


def capital_stock_epsilon(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
) -> float:
    """
    Physically-consistent capital stock K(ε).

    Governing equation:
        K(ε) = K₀ + ν · Y(ε)
        Y(ε) = machine_output_teh(ε) = ε · total_eoh(ε)    [TEH/yr]

    Where K₀ = CAPITAL_STOCK_DEFAULT is the ε=0-era stock (human-era tools
    and infrastructure, producing no machine-fulfilled EOH) and ν =
    RECAL_CAPITAL_OUTPUT_RATIO converts annual machine output into the
    capital stock required to produce it (Piketty's β ≈ 4–6; ν = 4).

    This closes the §8.8/RC3 inconsistency at its root: the old frame held
    CAPITAL_STOCK_DEFAULT fixed while ε rose, leaving a stock physically
    incapable of fulfilling 99% of EOH. Here the stock grows with the output
    it must produce, by the framework's own measure of that output.

    Worked example (pop = 1M, ν = 4):
        K(0)    = 2.00e9 TEH                      (human-era stock only)
        K(0.40) = 2.00e9 + 4 × 9.41e8 ≈ 5.77e9
        K(0.99) = 2.00e9 + 4 × 2.42e9 ≈ 1.17e10

    ε-behavior: monotone rising, smooth, no discontinuities; K(0) = K₀ > 0
    so downstream ratios are defined across the whole arc.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        capital_output_ratio: ν (> 0).

    Returns:
        Capital stock in TEH (float > 0).
    """
    if not 0.0 <= epsilon <= _EPS_MAX:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if capital_output_ratio <= 0.0:
        raise ValueError(
            f"capital_output_ratio must be > 0, got {capital_output_ratio}"
        )
    return (
        CAPITAL_STOCK_DEFAULT
        + capital_output_ratio * machine_output_teh(epsilon, population)
    )


def _validate_policy(phi_policy: str) -> None:
    if phi_policy not in _PHI_POLICIES:
        raise ValueError(
            f"phi_policy must be one of {_PHI_POLICIES}, got {phi_policy!r}"
        )


def _private_capital_ratchet(
    epsilon: float,
    population: float,
    capital_output_ratio: float,
) -> float:
    """
    Running max over [0, ε] of the target-trajectory private capital
    (1 − φ_target(x))·K(x) — the no-sale ratchet: private capital may rise
    (private investors co-own new formation while s_required < 1) but never
    falls by sale. Grid-evaluated at _RATCHET_STEP; single-peaked at
    defaults (peak ε ≈ 0.48, ≈ 3.93e9 TEH).
    """
    steps = int(epsilon / _RATCHET_STEP)
    xs = [i * _RATCHET_STEP for i in range(steps + 1)]
    xs.append(epsilon)
    return max(
        (1.0 - commonized_fraction(x))
        * capital_stock_epsilon(x, population, capital_output_ratio)
        for x in xs
    )


def phi_actual(
    epsilon: float,
    phi_policy: str = "dilution",
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
) -> dict:
    """
    Policy-resolved commons share φ_actual(ε) — proposed §8.9b.

    Governing equations:
        "target":    φ_actual = φ_target(ε) = commonized_fraction(ε)
                     (§8.9a purchase model — the commons buys the share)
        "dilution":  φ_actual = min(φ_target, 1 − ratchet(ε)/K(ε))
                     ratchet(ε) = max over [0,ε] of (1−φ_target)·K
                     — the commons takes only its charter share of NEW
                     formation; private capital is never sold down, so
                     where holding φ on target would require sales
                     (s_required > 1), φ_actual falls below target instead.
        "escalated": identical to "dilution" at point level. The escalation
                     mechanics (s = 1 on new formation; capital-estate
                     escheat at RECAL_ESCALATION_ESTATE_SHARE) are
                     PATH-DEPENDENT and live in recalibrated_arc(); this
                     point function documents the static approximation.

    Worked example (defaults, dilution):
        ε=0.40: ratchet = (1−0.328)·5.77e9 ≈ 3.88e9 (still rising)
                → cap ≈ 0.328 = φ_target → φ_actual = 0.328, cap not binding
        ε=0.99: ratchet ≈ 3.93e9 (peak, frozen from ε≈0.48)
                → φ_actual = 1 − 3.93e9/1.17e10 ≈ 0.66  (target 0.99):
                cap BINDING — the honest cost of never forcing sales.

    ε-behavior: φ_actual is non-decreasing under every policy (below the
    binding point it follows φ_target; above it, 1 − C/K rises with K),
    so τ = φ_actual keeps dτ/dε ≥ 0 structural.

    Args:
        epsilon: Automation level [0.0, 0.99].
        phi_policy: "target" | "dilution" (default) | "escalated".
        population: Total population.
        capital_output_ratio: ν (> 0).

    Returns:
        dict with keys: phi, phi_target, cap (None under "target"),
        cap_binding, phi_policy, epsilon.
    """
    _validate_policy(phi_policy)
    phi_target = commonized_fraction(epsilon)

    cap: float | None
    if phi_policy == "target":
        phi = phi_target
        cap = None
        cap_binding = False
    else:
        k = capital_stock_epsilon(epsilon, population, capital_output_ratio)
        ratchet = _private_capital_ratchet(
            epsilon, population, capital_output_ratio
        )
        cap = 1.0 - ratchet / k
        phi = min(phi_target, cap)
        cap_binding = phi < phi_target - 1e-12

    return {
        "phi": phi,
        "phi_target": phi_target,
        "cap": cap,
        "cap_binding": cap_binding,
        "phi_policy": phi_policy,
        "epsilon": epsilon,
    }


def commons_capital(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    phi_policy: str = "dilution",
) -> dict:
    """
    Commons capital T_K(ε) under ownership accounting — proposed §8.9/§8.9b.

    Governing equations:
        T_K(ε) = φ_actual(ε, policy) · K(ε)
        τ(ε)   = T_K / K = φ_actual(ε)   ≤ 1 by construction
        dτ/dε  ≥ 0                        structural (φ_actual non-decreasing)

    This replaces the old cash-Trust frame in which τ = TRUST_BASE_TEH /
    CAPITAL_STOCK_DEFAULT ≈ 17.5 — dimensionally incoherent for a share
    (§8.8 open item 3). The Piketty-inversion condition holds identically
    under every policy; what differs is HOW the share is acquired: purchase
    ("target", §8.9a) vs charter attachment to new formation ("dilution" /
    "escalated", §8.9b — see phi_actual()).

    T_K(0) = φ₀·K₀ (= 0.10 × 2e9 = 2e8 TEH at defaults) is an assumed
    INITIAL ENDOWMENT — the generalized form of the §8.8 commons seed.

    Worked example (defaults, dilution):
        ε=0.00: K = 2.00e9 → T_K = 2.0e8,  τ = 0.100
        ε=0.40: K = 5.77e9 → T_K = 1.89e9, τ = 0.328   (= target)
        ε=0.99: K = 1.17e10 → T_K ≈ 7.75e9, τ ≈ 0.66   (cap binding;
                target policy would give τ = 0.987 via forced sales)

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        capital_output_ratio: ν (> 0).
        phi_policy: "target" | "dilution" (default) | "escalated".

    Returns:
        dict with keys: commons_capital, capital_stock, private_capital,
        phi, phi_target, tau, cap_binding, phi_policy, epsilon.
    """
    k = capital_stock_epsilon(epsilon, population, capital_output_ratio)
    resolved = phi_actual(epsilon, phi_policy, population, capital_output_ratio)
    phi = resolved["phi"]
    t_k = phi * k
    return {
        "commons_capital": t_k,
        "capital_stock": k,
        "private_capital": (1.0 - phi) * k,
        "phi": phi,
        "phi_target": resolved["phi_target"],
        "tau": phi,  # τ = φ_actual identically under ownership accounting
        "cap_binding": resolved["cap_binding"],
        "phi_policy": phi_policy,
        "epsilon": epsilon,
    }


def formation_share_required(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
) -> dict:
    """
    Charter share of new capital formation that keeps φ on target — §8.9b.

    Governing equation:
        s(ε) = d(φ_target·K)/dε ÷ dK/dε

    s is the fraction of each newly commissioned unit of capital that must
    attach to the commons for φ_actual to track φ_target WITHOUT any
    purchase or forced sale of existing holdings. Feasible ⇔ s ≤ 1:
    beyond that, target-tracking would require selling private capital —
    exactly what the dilution ratchet refuses, so φ_actual departs from
    target there (see phi_actual()).

    Worked example (defaults):
        ε=0.05: s ≈ 0.17   (early arc: mild charter share)
        ε=0.40: s ≈ 0.83
        ε=0.60: s > 1      (INFEASIBLE from new formation alone — the
                            binding region; at defaults it starts ε ≈ 0.48,
                            where target-trajectory private capital peaks)

    ε-behavior: rises from φ₀ at ε=0 (dφ/dε → 0 there, so s → φ_target),
    crosses 1 near ε ≈ 0.48 at defaults, stays above 1 to the top of the
    arc. This inverts §8.9a's honest window: under the charter doctrine the
    EARLY arc is easy and the LATE arc is where target-tracking fails.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        capital_output_ratio: ν (> 0).

    Returns:
        dict with keys: share_required, feasible (s ≤ 1), d_commons_deps,
        d_capital_deps, epsilon.
    """
    lo = epsilon if epsilon + _FD_STEP <= _EPS_MAX else epsilon - _FD_STEP
    hi = lo + _FD_STEP

    def _target_commons(x: float) -> float:
        return commonized_fraction(x) * capital_stock_epsilon(
            x, population, capital_output_ratio
        )

    d_commons = (_target_commons(hi) - _target_commons(lo)) / _FD_STEP
    d_capital = (
        capital_stock_epsilon(hi, population, capital_output_ratio)
        - capital_stock_epsilon(lo, population, capital_output_ratio)
    ) / _FD_STEP
    share = d_commons / d_capital  # dK/dε > 0 across the arc (K monotone)

    return {
        "share_required": share,
        "feasible": share <= 1.0,
        "d_commons_deps": d_commons,
        "d_capital_deps": d_capital,
        "epsilon": epsilon,
    }


def formation_levy_rate(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
) -> dict:
    """
    Compensated-bridge metric: the labor-era levy that funds the §8.9a
    PURCHASE model's early-arc gap — §8.9b (A2).

    Governing equations:
        gap(ε)  = max(0, reinvest_target(ε) − income_target(ε))
                  (the purchase model's unfunded acquisition need)
        labor(ε) = (1−ε) · total_eoh(ε)      [human-fulfilled output, TEH/yr]
        levy_rate = gap / labor

    Under the charter doctrine ("dilution"/"escalated") nothing is purchased
    and this levy is 0 by construction; the metric quantifies the SOFTER
    variant in which the charter compensates builders for the commons'
    share at cost, funded from the labor-era economy — how every real
    sovereign fund was actually seeded (fiscal surpluses, payroll levies).

    Worked example (defaults):
        ε=0.05: gap ≈ 2.4e7 TEH/yr, labor ≈ 2.2e9 → levy ≈ 1.1%
        ε=0.20: gap = 0 → levy = 0  (SUNSET — the levy self-extinguishes)

    ε-behavior: ≈ 1% at the start of the arc, monotone to 0 by ε ≈ 0.2,
    0 thereafter. Compare SUFF_LEVY_RATE = 1.25%: the bridge is smaller
    than the existing sufficiency levy and temporary.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0).

    Returns:
        dict with keys: levy_rate, funding_gap, labor_output, sunset
        (gap == 0), epsilon.
    """
    inc = commons_income_statement(
        epsilon, population, capital_output_ratio, epsilon_rate_per_year,
        phi_policy="target",
    )
    gap = max(0.0, inc["reinvestment"] - inc["income"])
    labor = (1.0 - epsilon) * total_eoh(
        epsilon=epsilon, population=population
    )["total"]
    return {
        "levy_rate": gap / labor,
        "funding_gap": gap,
        "labor_output": labor,
        "sunset": gap == 0.0,
        "epsilon": epsilon,
    }


def commons_income_statement(
    epsilon: float,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    phi_policy: str = "dilution",
    net_of_replacement: bool = False,
) -> dict:
    """
    Annual commons income statement at ε — proposed §8.9/§8.9b.

    Governing equations:
        income(ε) = φ_actual(ε, policy) · Y(ε)

        "target" (§8.9a purchase model):
            reinvest = d(φ_target·K)/dε · (dε/dt)   (buying the share)
            dividend = max(0, income − reinvest) / population
            acquisition_feasible ⇔ reinvest ≤ income
            (honest window: FALSE for ε ≲ 0.15 — dφ/dε outruns tiny Y)

        "dilution"/"escalated" (§8.9b charter doctrine):
            reinvest = 0            (the share ATTACHES at commissioning;
                                     nothing is ever purchased)
            dividend = income / population       (the full Meade dividend)
            acquisition_feasible ⇔ s_required ≤ 1
            (the window INVERTS: TRUE on the early arc, FALSE from ε ≈ 0.48
             where target-tracking would need forced sales)

    The charter share is an implicit tax on private capital formation
    (builders fund construction, own 1−s); the model does NOT simulate the
    resulting investment-disincentive feedback on K(ε) — open item, flagged.

    Worked example (ε=0.40, defaults, dilution):
        Y = 9.41e8, φ = 0.328 → income ≈ 3.08e8, reinvest = 0
        → D ≈ 308 TEH/person·yr  (§8.9a purchase model: D ≈ 144 —
        the doctrine dividend is strictly larger at every ε)
    ε-behavior of D (dilution): 0 at ε=0, ≈ 308 at 0.40, ≈ 1,606 at 0.99
    (cap binding: the target policy's 1,873 requires forced sales).

    g_priv is ENDOGENOUS: reported both as a rate (g_priv_per_year; None
    where private capital ≈ 0) and — because a rate on a vanishing base is
    theatrical — as the absolute flow private_capital_delta_per_year
    [TEH/yr]. Point-level dilution ignores the (slow) estate-escheat flow;
    recalibrated_arc() is authoritative for the estate path.

    REPLACEMENT (§8.9c correction): the commons must replace its own worn
    machines — replacement_cost = δ·T_K per year (δ =
    FORMATION_DEPRECIATION_RATE), a ≈ (δ·ν) ≈ 20% haircut on the gross
    dividend at defaults. Always reported; subtracted from the dividend only
    when net_of_replacement=True (default False preserves the published
    §8.9/§8.9b gross figures as the regression anchor; formation-feedback
    work uses the net figure).

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population (> 0).
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0).
        phi_policy: "target" | "dilution" (default) | "escalated".

    Returns:
        dict with keys: income, reinvestment, acquisition_feasible,
        dividend_pool, dividend_per_capita, machine_output,
        g_priv_per_year, private_capital_delta_per_year, s_required,
        replacement_cost, net_of_replacement, phi, phi_policy, epsilon.
    """
    if population <= 0.0:
        raise ValueError(f"population must be positive, got {population}")
    if epsilon_rate_per_year < 0.0:
        raise ValueError(
            f"epsilon_rate_per_year must be >= 0, got {epsilon_rate_per_year}"
        )
    _validate_policy(phi_policy)

    y = machine_output_teh(epsilon, population)
    resolved = phi_actual(epsilon, phi_policy, population, capital_output_ratio)
    phi = resolved["phi"]
    income = phi * y
    s_req = formation_share_required(epsilon, population, capital_output_ratio)

    # d(private)/dε by finite difference under the active policy; backward
    # at the top of the arc so the derivative stays inside [0, 0.99].
    lo = epsilon if epsilon + _FD_STEP <= _EPS_MAX else epsilon - _FD_STEP
    hi = lo + _FD_STEP

    def _private(x: float) -> float:
        return commons_capital(
            x, population, capital_output_ratio, phi_policy
        )["private_capital"]

    d_private = (_private(hi) - _private(lo)) / _FD_STEP
    private_delta = d_private * epsilon_rate_per_year

    replacement = FORMATION_DEPRECIATION_RATE * phi * capital_stock_epsilon(
        epsilon, population, capital_output_ratio
    )
    replacement_deducted = replacement if net_of_replacement else 0.0

    if phi_policy == "target":
        def _target_commons(x: float) -> float:
            return commonized_fraction(x) * capital_stock_epsilon(
                x, population, capital_output_ratio
            )
        d_commons = (_target_commons(hi) - _target_commons(lo)) / _FD_STEP
        reinvestment = max(0.0, d_commons) * epsilon_rate_per_year
        dividend_pool = max(0.0, income - reinvestment - replacement_deducted)
        acquisition_feasible = reinvestment <= income
    else:
        reinvestment = 0.0  # charter attachment: nothing is purchased
        dividend_pool = max(0.0, income - replacement_deducted)
        acquisition_feasible = s_req["feasible"]

    private = commons_capital(
        epsilon, population, capital_output_ratio, phi_policy
    )["private_capital"]
    g_priv: float | None
    if private > 0.0:
        g_priv = private_delta / private
    else:
        g_priv = None  # φ → 1: no private capital left to have a growth rate

    return {
        "income": income,
        "reinvestment": reinvestment,
        "acquisition_feasible": acquisition_feasible,
        "dividend_pool": dividend_pool,
        "dividend_per_capita": dividend_pool / population,
        "machine_output": y,
        "g_priv_per_year": g_priv,
        "private_capital_delta_per_year": private_delta,
        "s_required": s_req["share_required"],
        "replacement_cost": replacement,
        "net_of_replacement": net_of_replacement,
        "phi": phi,
        "phi_policy": phi_policy,
        "epsilon": epsilon,
    }


def capital_account_stock(
    tenure_years: float,
    epsilon: float,
    population: float = 1_000_000.0,
    credit_share: float = RECAL_ACCOUNT_CREDIT_SHARE,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    phi_policy: str = "dilution",
) -> dict:
    """
    Individual capital account as a genuine accumulating STOCK — the RC4 fix
    for §8.7b (Mondragon internal-account precedent).

    Governing equation (static-ε approximation, documented limitation):
        account(tenure, ε) = credit_share · D(ε) · tenure_years

    Each membership year credits credit_share of that year's per-capita
    dividend to the member's account; the remainder is paid as cash. The
    account is a SUM OF CREDITS — zero interest, per Condition III: balances
    grow only through income minus expenditure, never through compounding.
    On exit the account crosses the boundary at the prevailing exchange rate
    (§8.7b/d, exit_value()); tenure is federation-wide.

    χ_stock — the dimensionally-clean successor of χ (stock / stock):
        χ_stock = account / (ε · K_entry(ε))
    compares the account against the CAPITAL share of the founding cost
    (the (1−ε) labor share is contributed as the founder's own hours — see
    exit_financing()). None when ε = 0 (no capital share to finance).

    Worked example (tenure=5, ε=0.80, defaults, dilution):
        D(0.80) ≈ 1,134 → account = 0.5 × 1,134 × 5 ≈ 2,834 TEH
        capital share of K_entry = 0.80 × 4,104 ≈ 3,283 → χ_stock ≈ 0.86

    Args:
        tenure_years: Years of federation membership (≥ 0).
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        credit_share: Share of the annual dividend credited to the account
            (∈ [0, 1]).
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0).
        phi_policy: "target" | "dilution" (default) | "escalated".

    Returns:
        dict with keys: account_balance, annual_credit, chi_stock (None at
        ε=0), tenure_years, epsilon.
    """
    if tenure_years < 0.0:
        raise ValueError(f"tenure_years must be >= 0, got {tenure_years}")
    if not 0.0 <= credit_share <= 1.0:
        raise ValueError(f"credit_share must be in [0, 1], got {credit_share}")

    income = commons_income_statement(
        epsilon, population, capital_output_ratio, epsilon_rate_per_year,
        phi_policy,
    )
    annual_credit = credit_share * income["dividend_per_capita"]
    account = annual_credit * tenure_years

    capital_share = epsilon * entry_cost(epsilon)
    chi_stock: float | None = (
        account / capital_share if capital_share > 0.0 else None
    )

    return {
        "account_balance": account,
        "annual_credit": annual_credit,
        "chi_stock": chi_stock,
        "tenure_years": tenure_years,
        "epsilon": epsilon,
    }


def estate_conversion_flow(
    epsilon: float,
    escheat_share: float = RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    death_rate: float = ANNUAL_DEATH_RATE,
) -> dict:
    """
    Generational conversion of private capital to the commons — §8.9b (B4).

    Governing equations:
        flow(ε)   = death_rate · escheat_share · K_priv(ε)     [TEH/yr]
        half_life = ln 2 / (death_rate · escheat_share)        [years]

    On death, escheat_share of a decedent's private CAPITAL escheats to the
    commons — the existing D5 estate treatment (which already levies
    ESTATE_LEVY_FRACTION of TEH estates to the Trust) extended to capital,
    not a new rule. No living holder is ever divested: this is Piketty's
    own instrument (inheritance taxation), and it is the §8.9b escalation
    mechanism — under an active escalation the share rises to
    RECAL_ESCALATION_ESTATE_SHARE (= 1.0), converging φ toward target at
    mortality speed.

    HONEST FINDING: mortality speed is slow. At death_rate = 1%/yr, even
    full escheat (share = 1.0) gives a private-capital half-life of ≈ 69
    years — φ_target ≈ 0.99 is reached asymptotically over generations,
    not within the arc. §8.2's "φ must be ABLE to → 1" survives as an
    asymptotic capability; the exit invariant does not depend on it.

    Worked example (ε=0.60, defaults):
        K_priv ≈ 3.83e9 (dilution) → flow = 0.010 × 0.15 × 3.83e9
        ≈ 5.7e6 TEH/yr; half-life = ln2/(0.010·0.15) ≈ 462 yr.

    Args:
        epsilon: Automation level [0.0, 0.99].
        escheat_share: Capital-estate escheat share (∈ [0, 1]).
        population: Total population.
        capital_output_ratio: ν (> 0).
        death_rate: Annual death rate (≥ 0).

    Returns:
        dict with keys: flow_per_year, private_capital, half_life_years
        (math.inf at share or death_rate 0), escheat_share, epsilon.
    """
    if not 0.0 <= escheat_share <= 1.0:
        raise ValueError(
            f"escheat_share must be in [0, 1], got {escheat_share}"
        )
    if death_rate < 0.0:
        raise ValueError(f"death_rate must be >= 0, got {death_rate}")

    private = commons_capital(
        epsilon, population, capital_output_ratio, phi_policy="dilution"
    )["private_capital"]
    flow = death_rate * escheat_share * private
    decay = death_rate * escheat_share
    half_life = math.log(2.0) / decay if decay > 0.0 else math.inf

    return {
        "flow_per_year": flow,
        "private_capital": private,
        "half_life_years": half_life,
        "escheat_share": escheat_share,
        "epsilon": epsilon,
    }


def escalation_trigger(
    epsilon: float,
    regime: str = "increasing_returns",
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    capacity_floor: float = RECAL_ESCALATION_CAPACITY_FLOOR,
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
) -> dict:
    """
    The §8.9b charter escalation clause — regime-conditioned (B3).

    Governing condition:
        active ⇔ regime == "increasing_returns"
                 AND (entry_capacity < capacity_floor
                      OR NOT exit_financeable)
        (both evaluated under the un-escalated dilution policy)

    §8.5's honest regime uncertainty becomes CONTINGENT policy: private
    capital persists indefinitely unless observed increasing-returns
    concentration measurably threatens the right of exit — the commons must
    always be able to finance well more than one founding (the capacity
    floor), and the combined invariant must hold. When active, the charter
    takes all new formation (s = 1) and the capital-estate escheat rises to
    RECAL_ESCALATION_ESTATE_SHARE — never a forced sale (see
    estate_conversion_flow(); path mechanics in recalibrated_arc(), where
    the trigger LATCHES: charter escalations do not flap).

    HONEST RESULT at canonical defaults: the trigger NEVER fires — capacity
    stays ≈ 145–280 across the arc in both regimes. The brake exists, is
    tested (it fires under forced adversarial parameters, e.g. a founding
    cohort 40× larger), and stays off.

    Args:
        epsilon: Automation level [0.0, 0.99].
        regime: K_entry regime ("increasing_returns" / "replicable").
        population: Total population.
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0).
        capacity_floor: Entry capacity below which the charter escalates.
        min_viable_population: Smallest viable founding cohort (> 0).
        underwrite_fraction: Max deployable commons share (∈ [0, 1]).

    Returns:
        dict with keys: active, reason, entry_capacity, exit_financeable,
        capacity_floor, regime, epsilon.
    """
    fin = exit_financing(
        epsilon,
        population,
        regime,
        capital_output_ratio,
        epsilon_rate_per_year,
        min_viable_population=min_viable_population,
        underwrite_fraction=underwrite_fraction,
        phi_policy="dilution",
    )
    capacity = fin["entry_capacity"]
    adversarial = regime == "increasing_returns"
    low_capacity = capacity < capacity_floor
    active = adversarial and (low_capacity or not fin["exit_financeable"])

    if not adversarial:
        reason = "regime not increasing_returns — escalation never applies"
    elif not active:
        reason = (
            f"contestability healthy (capacity {capacity:.1f} >= "
            f"floor {capacity_floor:g}, invariant holds)"
        )
    elif not fin["exit_financeable"]:
        reason = "exit invariant failing under un-escalated policy"
    else:
        reason = (
            f"entry capacity {capacity:.1f} below floor {capacity_floor:g}"
        )

    return {
        "active": active,
        "reason": reason,
        "entry_capacity": capacity,
        "exit_financeable": fin["exit_financeable"],
        "capacity_floor": capacity_floor,
        "regime": regime,
        "epsilon": epsilon,
    }


def _exit_channels(
    epsilon: float,
    regime: str,
    dividend_per_capita: float,
    commons_capital_teh: float,
    founding_labor_hours: float,
    exit_horizon_years: float,
    min_viable_population: float,
    underwrite_fraction: float,
) -> dict:
    """
    Three-channel exit financing at given dividend and commons capital.
    Shared by exit_financing() (point values) and recalibrated_arc()
    (path-integrated values); governing equations documented on
    exit_financing().
    """
    k_entry = entry_cost(epsilon, regime)
    k_labor = (1.0 - epsilon) * k_entry
    k_capital = epsilon * k_entry

    t_labor = k_labor / founding_labor_hours
    t_capital = k_capital / dividend_per_capita if dividend_per_capita > 0.0 else (
        0.0 if k_capital == 0.0 else math.inf
    )
    t_exit_self = max(t_labor, t_capital)
    self_financeable = t_exit_self <= exit_horizon_years

    if k_capital > 0.0:
        entry_capacity = (
            underwrite_fraction * commons_capital_teh
            / (min_viable_population * k_capital)
        )
    else:
        entry_capacity = math.inf  # no capital share — nothing to underwrite

    exit_financeable = self_financeable or entry_capacity >= 1.0

    if not exit_financeable:
        channel = "none"
    elif self_financeable:
        channel = "labor" if t_labor >= t_capital else "self"
    else:
        channel = "underwritten"

    return {
        "exit_financeable": exit_financeable,
        "channel": channel,
        "t_labor_years": t_labor,
        "t_capital_years": t_capital,
        "t_exit_self_years": t_exit_self,
        "self_financeable": self_financeable,
        "entry_capacity": entry_capacity,
        "k_entry": k_entry,
        "k_labor": k_labor,
        "k_capital": k_capital,
        "dividend_per_capita": dividend_per_capita,
        "regime": regime,
        "epsilon": epsilon,
    }


def exit_financing(
    epsilon: float,
    population: float = 1_000_000.0,
    regime: str = "increasing_returns",
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    founding_labor_hours: float = RECAL_FOUNDING_LABOR_HOURS,
    exit_horizon_years: float = RECAL_EXIT_HORIZON_YEARS,
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
    phi_policy: str = "dilution",
) -> dict:
    """
    Exit financing across the three physical channels — the §8.9 invariant,
    policy-resolved per §8.9b.

    Governing equations. K_entry decomposes by the machine share of work
    (ε is BY DEFINITION the machine-fulfilled fraction of EOH, so the
    fraction of founding work humans can supply themselves is 1−ε):

        K_labor(ε)   = (1−ε) · K_entry(ε)    founders' own building hours
        K_capital(ε) = ε · K_entry(ε)        embodied automated capital

        t_labor   = K_labor / founding_labor_hours          [years]
        t_capital = K_capital / D(ε)                        [years; ∞ if D=0]
        t_exit_self = max(t_labor, t_capital)               (parallel channels)
        self_financeable ⇔ t_exit_self ≤ exit_horizon_years

        entry_capacity = underwrite_fraction · T_K(ε) / (MVP · K_capital)
                         (∞ when K_capital = 0 — nothing to underwrite)

        exit_financeable ⇔ self_financeable OR entry_capacity ≥ 1

    The time formulation is the RC4 fix: a one-time stock against an annual
    flow yields YEARS-TO-FINANCE, bounded by one vesting period — not a
    ratio that demands the stock be covered by a single year's income.

    The three channels at defaults (dilution policy, adversarial regime):
        labor    ε=0:       t_labor = 1.8 yr — at subsistence, exit is
                            financed by hands; the floor feeds the founders.
        commons  ε≈0.05–0.27: the MID-ARC TROUGH — labor displaced, the
                            dividend not yet large. Underwriting carries it
                            (capacity ≈ 145–280; Caja Laboral / Marcora).
                            Under the §8.9b full-φ·Y dividend the trough is
                            NARROWER than §8.9a's (which ran to ε ≈ 0.55).
        dividend ε≥0.30:    self-financeable; t_exit ≈ 2.9 yr at ε=0.99
                            even with the dilution cap (φ ≈ 0.66).

    D and T_K come from commons_income_statement() / commons_capital()
    under the given phi_policy; underwriting deploys the commons' CAPITAL
    (allocating machines to a founding cohort), which stays commonized and
    indivisible in the new collective's trust (§8.7c).

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        regime: K_entry regime ("increasing_returns" default / "replicable").
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0).
        founding_labor_hours: Hours/yr a founder can devote to building (> 0).
        exit_horizon_years: Self-financing horizon (> 0).
        min_viable_population: Smallest viable founding cohort (> 0).
        underwrite_fraction: Max deployable commons share (∈ [0, 1]).
        phi_policy: "target" | "dilution" (default) | "escalated".

    Returns:
        dict with keys: exit_financeable, channel ("labor" | "self" |
        "underwritten" | "none"), t_labor_years, t_capital_years (may be
        math.inf), t_exit_self_years (may be math.inf), self_financeable,
        entry_capacity (may be math.inf), k_entry, k_labor, k_capital,
        dividend_per_capita, regime, epsilon.
    """
    if founding_labor_hours <= 0.0:
        raise ValueError(
            f"founding_labor_hours must be > 0, got {founding_labor_hours}"
        )
    if exit_horizon_years <= 0.0:
        raise ValueError(
            f"exit_horizon_years must be > 0, got {exit_horizon_years}"
        )
    if min_viable_population <= 0.0:
        raise ValueError(
            f"min_viable_population must be > 0, got {min_viable_population}"
        )
    if not 0.0 <= underwrite_fraction <= 1.0:
        raise ValueError(
            f"underwrite_fraction must be in [0, 1], got {underwrite_fraction}"
        )

    income = commons_income_statement(
        epsilon, population, capital_output_ratio, epsilon_rate_per_year,
        phi_policy,
    )
    t_k = commons_capital(
        epsilon, population, capital_output_ratio, phi_policy
    )["commons_capital"]

    return _exit_channels(
        epsilon, regime, income["dividend_per_capita"], t_k,
        founding_labor_hours, exit_horizon_years,
        min_viable_population, underwrite_fraction,
    )


def recalibrated_arc(
    n_points: int = 20,
    regime: str = "increasing_returns",
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    exit_horizon_years: float = RECAL_EXIT_HORIZON_YEARS,
    phi_policy: str = "dilution",
    estate_escheat_share: float = RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
    capacity_floor: float = RECAL_ESCALATION_CAPACITY_FLOOR,
) -> list[dict]:
    """
    Arc sweep of the recalibrated system across ε ∈ [0, 0.99] — §8.9/§8.9b.

    Under "target" each row is the §8.9a purchase model (point functions;
    regression anchor for the published §8.9 numbers). Under
    "dilution"/"escalated" the arc PATH-INTEGRATES the capital split
    (forward Euler, one step per row; each step spans Δt = Δε / (dε/dt)
    years):

        estate_t = death_rate · share_t · K_priv · Δt        (D5 extended)
        take_t   = min(max(0, φ_target·K − (T_K + estate_t)), ΔK)
                   — the charter's share of NEW formation (s ≤ 1; never a
                   forced sale). Under an active escalation take_t = ΔK.
        K_priv  += (ΔK − take_t) − estate_t ;  T_K += take_t + estate_t
        (conservation: T_K + K_priv = K at every row — asserted in tests)

    share_t = estate_escheat_share, rising to RECAL_ESCALATION_ESTATE_SHARE
    while an escalation is active. The escalation trigger (evaluated per
    row under "escalated": adversarial regime AND (capacity < floor OR
    invariant failing)) LATCHES — charter escalations do not flap. At
    canonical defaults it NEVER fires (asserted in tests).

    Expected shape at defaults (dilution, adversarial; asserted in tests):
        - τ = φ_actual non-decreasing (Piketty inversion, structural)
        - private capital NEVER falls by sale — declines only within the
          mortality bound death_rate·share·K_priv·Δt per step
        - exit_financeable at EVERY row; channel arcs labor → underwritten
          → self, with self-financing from ε ≈ 0.30 (§8.9a: 0.59)
        - φ_actual caps at ≈ 0.66 by ε = 0.99 (target 0.99): the honest
          cost of the no-forced-sale doctrine
        - acquisition_feasible (s_required ≤ 1) TRUE early, FALSE from
          ε ≈ 0.48 — §8.9a's honest window, inverted

    Args:
        n_points: Number of ε points (default 20).
        regime: K_entry regime.
        population: Total population.
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Arc speed dε/dt (≥ 0; at 0, no time elapses
            and the estate flow is inactive).
        exit_horizon_years: Self-financing horizon (> 0).
        phi_policy: "target" | "dilution" (default) | "escalated".
        estate_escheat_share: Baseline capital-estate escheat share (∈ [0,1]).
        min_viable_population: Smallest viable founding cohort (> 0).
        underwrite_fraction: Max deployable commons share (∈ [0, 1]).
        capacity_floor: Escalation capacity floor ("escalated" only).

    Returns:
        list[dict] — one row per ε with keys: epsilon, capital_stock,
        machine_output, phi, phi_target, tau, cap_binding, commons_capital,
        private_capital, income, reinvestment, acquisition_feasible,
        dividend_per_capita, g_priv_per_year, private_capital_delta_per_year,
        s_required, escalation_active, phi_policy, k_entry,
        t_exit_self_years, self_financeable, entry_capacity,
        exit_financeable, channel.
    """
    _validate_policy(phi_policy)
    if not 0.0 <= estate_escheat_share <= 1.0:
        raise ValueError(
            f"estate_escheat_share must be in [0, 1], got {estate_escheat_share}"
        )

    rows: list[dict] = []
    eps_prev: float | None = None
    k_prev = 0.0
    k_priv = 0.0
    t_k = 0.0
    escalated = False

    for i in range(n_points):
        eps = i / (n_points - 1) * _EPS_MAX if n_points > 1 else 0.40
        k = capital_stock_epsilon(eps, population, capital_output_ratio)
        y = machine_output_teh(eps, population)
        phi_target = commonized_fraction(eps)
        s_req = formation_share_required(
            eps, population, capital_output_ratio
        )

        if phi_policy == "target":
            income_st = commons_income_statement(
                eps, population, capital_output_ratio, epsilon_rate_per_year,
                phi_policy="target",
            )
            phi = phi_target
            t_k = phi * k
            k_priv = k - t_k
            income = income_st["income"]
            reinvestment = income_st["reinvestment"]
            acquisition_feasible = income_st["acquisition_feasible"]
            dividend = income_st["dividend_per_capita"]
            g_priv = income_st["g_priv_per_year"]
            private_delta = income_st["private_capital_delta_per_year"]
            cap_binding = False
        else:
            if eps_prev is None:
                # Arc start (or single-point fallback): target split.
                k_priv = (1.0 - phi_target) * k
                t_k = k - k_priv
                private_delta = 0.0
            else:
                d_k = k - k_prev
                dt = (
                    (eps - eps_prev) / epsilon_rate_per_year
                    if epsilon_rate_per_year > 0.0 else 0.0
                )
                share = (
                    RECAL_ESCALATION_ESTATE_SHARE if escalated
                    else estate_escheat_share
                )
                estate = min(ANNUAL_DEATH_RATE * share * k_priv * dt, k_priv)
                if escalated:
                    take = d_k  # s = 1: the charter takes all new formation
                else:
                    take = min(
                        max(0.0, phi_target * k - (t_k + estate)), d_k
                    )
                k_priv_new = k_priv + (d_k - take) - estate
                t_k = t_k + take + estate
                private_delta = (
                    (k_priv_new - k_priv) / dt if dt > 0.0 else 0.0
                )
                k_priv = k_priv_new
            phi = t_k / k
            income = phi * y
            reinvestment = 0.0  # charter attachment: nothing is purchased
            acquisition_feasible = s_req["feasible"]
            dividend = income / population
            g_priv = private_delta / k_priv if k_priv > 0.0 else None
            cap_binding = phi < phi_target - 1e-12

        channels = _exit_channels(
            eps, regime, dividend, t_k,
            RECAL_FOUNDING_LABOR_HOURS, exit_horizon_years,
            min_viable_population, underwrite_fraction,
        )

        if phi_policy == "escalated" and not escalated:
            if regime == "increasing_returns" and (
                channels["entry_capacity"] < capacity_floor
                or not channels["exit_financeable"]
            ):
                escalated = True  # latch: escalations do not flap

        rows.append({
            "epsilon":                        eps,
            "capital_stock":                  k,
            "machine_output":                 y,
            "phi":                            phi,
            "phi_target":                     phi_target,
            "tau":                            phi,
            "cap_binding":                    cap_binding,
            "commons_capital":                t_k,
            "private_capital":                k_priv,
            "income":                         income,
            "reinvestment":                   reinvestment,
            "acquisition_feasible":           acquisition_feasible,
            "dividend_per_capita":            dividend,
            "g_priv_per_year":                g_priv,
            "private_capital_delta_per_year": private_delta,
            "s_required":                     s_req["share_required"],
            "escalation_active":              escalated,
            "phi_policy":                     phi_policy,
            "k_entry":                        channels["k_entry"],
            "t_exit_self_years":              channels["t_exit_self_years"],
            "self_financeable":               channels["self_financeable"],
            "entry_capacity":                 channels["entry_capacity"],
            "exit_financeable":               channels["exit_financeable"],
            "channel":                        channels["channel"],
        })
        eps_prev = eps
        k_prev = k
    return rows
