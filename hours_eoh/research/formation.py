"""
Formation feedback — proposed §8.9c (who actually builds K(ε)).

EXPERIMENTAL TIER — not stable API. Closes the circularity the §8.9b static
model flagged as open: the charter share s(ε) is an implicit tax on private
capital formation, yet the static model assumed K(ε) = K₀ + ν·Y(ε)
materializes regardless. Here formation is FINANCED or it does not happen,
and ε is DERIVED from the capital the simulation actually forms — inverting
the module's own physics (ε = (K − K₀)/(ν·total_eoh), the aggregate
analogue of core's compute_epsilon; typed-capital integration via
core/civilization.py is the core-grade follow-up).

The three coupled loops, closed:

1.  INCENTIVE. A private builder pays the full construction cost of new
    capital and owns (1−s) of it:
        r_gross  = 1/ν − δ                       (= 0.20 at defaults)
        r_priv(s) = (1−s) · r_gross
    Investment supply (proposed form — heterogeneous hurdle rates, linear):
        f(s) = clamp((r_priv − r_min)/(r_full − r_min), 0, 1)
        s*   = 1 − r_full/r_gross                (incentive-compatible share
                                                  = 0.50 at defaults)
    Condition III is the doctrine's structural ally here: idle TEH earns
    zero interest and leaks via the accumulation ceiling (D6) and estate
    dissolution (D5), so r_min is uniquely low — the charter share is far
    more affordable than it would be in an interest-bearing economy.

2.  FUNDING. Where private supply falls short (s above s*; s = 1 in the
    dilution cap region — the §8.9b funding hole), the commons must pay for
    formation out of its own NET income (gross φ·Y minus replacement of its
    own worn stock, δ·T_K — the §8.9c replacement correction). A priority
    policy decides the split:
        "share"    — formation first, dividend gets the residual
                     (arc pace held; dividend cut)
        "dividend" — dividend first, formation gets only private supply
                     (dividend held; the arc STALLS where f → 0)

3.  ε-ENDOGENEITY. K evolves by funded formation (owners maintain their own
    existing stock — the charter attaches to NET NEW formation, not
    like-for-like replacement, else "never sold down" would break
    silently); ε follows from realized capacity, lagged one period.

Public functions:
    private_return(s, ...) → float
    investment_supply_fraction(s, ...) → float
    incentive_compatible_share(...) → float
    formation_feedback_simulation(n_years, priority, ...) → list[dict]
    formation_verdict(rows, ...) → dict

Mission Statement: §"Contestability — the invariant the arc must preserve."
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.data import (
    ANNUAL_DEATH_RATE,
    CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_MIN_VIABLE_POPULATION,
    CONTESTABILITY_PHI_FLOOR,
    CONTESTABILITY_UNDERWRITE_FRACTION,
    FORMATION_DEPRECIATION_RATE,
    FORMATION_FULL_SUPPLY_RATE,
    FORMATION_HURDLE_RATE_MIN,
    RECAL_CAPITAL_OUTPUT_RATIO,
    RECAL_EPSILON_RATE_PER_YEAR,
    RECAL_ESCALATION_CAPACITY_FLOOR,
    RECAL_ESCALATION_ESTATE_SHARE,
    RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    RECAL_EXIT_HORIZON_YEARS,
    RECAL_FOUNDING_LABOR_HOURS,
)
from hours_eoh.research.contestability import commonized_fraction
from hours_eoh.research.recalibration import (
    _exit_channels,
    capital_stock_epsilon,
)

# Top of the ε range (CLAUDE.md design invariant: ε ∈ [0, 0.99]).
_EPS_MAX: float = 0.99

# Formation-demand tolerance: below this (TEH/yr) demand counts as met, so
# the terminal arc plateau is not misreported as a stall. Numerics only.
_STALL_TOL_TEH: float = 1.0

_PRIORITIES = ("share", "dividend")


def private_return(
    s: float,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    depreciation_rate: float = FORMATION_DEPRECIATION_RATE,
) -> float:
    """
    Net private return on capital formation under charter share s — §8.9c.

    Governing equation:
        r_priv(s) = (1 − s) · (1/ν − δ)

    The builder pays the full construction cost, owns (1−s) of the asset,
    and that ownership yields the gross return 1/ν minus depreciation δ
    (they maintain their own stock).

    Worked example (defaults, ν=4, δ=0.05):
        r_gross = 0.25 − 0.05 = 0.20
        s=0:    r_priv = 0.20      s=0.5: r_priv = 0.10
        s=1:    r_priv = 0.00      (nobody builds for zero ownership)

    Args:
        s: Charter share of new formation (∈ [0, 1]).
        capital_output_ratio: ν (> 0).
        depreciation_rate: δ (∈ [0, 1/ν) for a positive gross return).

    Returns:
        Net annual return on private outlay (float ≥ 0).
    """
    if not 0.0 <= s <= 1.0:
        raise ValueError(f"s must be in [0, 1], got {s}")
    if capital_output_ratio <= 0.0:
        raise ValueError(
            f"capital_output_ratio must be > 0, got {capital_output_ratio}"
        )
    if depreciation_rate < 0.0:
        raise ValueError(
            f"depreciation_rate must be >= 0, got {depreciation_rate}"
        )
    return (1.0 - s) * (1.0 / capital_output_ratio - depreciation_rate)


def investment_supply_fraction(
    s: float,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    depreciation_rate: float = FORMATION_DEPRECIATION_RATE,
    hurdle_rate_min: float = FORMATION_HURDLE_RATE_MIN,
    full_supply_rate: float = FORMATION_FULL_SUPPLY_RATE,
) -> float:
    """
    Fraction of needed formation privately supplied at charter share s.

    Governing equation (proposed form — heterogeneous hurdle rates across
    investors give a linear supply segment; flagged, not calibrated):
        f(s) = clamp((r_priv(s) − r_min) / (r_full − r_min), 0, 1)

    r_min = FORMATION_HURDLE_RATE_MIN is low BECAUSE of Condition III: the
    competing store of value (idle TEH) earns zero interest and leaks via
    the accumulation ceiling and estate dissolution, so only risk
    compensation remains. r_full = FORMATION_FULL_SUPPLY_RATE is the return
    at which formation demand is fully supplied.

    Worked example (defaults): f = 1 for s ≤ 0.5 (the charter is FREE up to
    the incentive-compatible share); f = 0.5 at s = 0.7; f = 0 at s ≥ 0.9.

    Args:
        s: Charter share of new formation (∈ [0, 1]).
        capital_output_ratio: ν (> 0).
        depreciation_rate: δ (≥ 0).
        hurdle_rate_min: r_min (≥ 0).
        full_supply_rate: r_full (> r_min).

    Returns:
        Supply fraction ∈ [0, 1].
    """
    if full_supply_rate <= hurdle_rate_min:
        raise ValueError(
            f"full_supply_rate must exceed hurdle_rate_min, got "
            f"{full_supply_rate} <= {hurdle_rate_min}"
        )
    r = private_return(s, capital_output_ratio, depreciation_rate)
    raw = (r - hurdle_rate_min) / (full_supply_rate - hurdle_rate_min)
    return min(1.0, max(0.0, raw))


def incentive_compatible_share(
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    depreciation_rate: float = FORMATION_DEPRECIATION_RATE,
    full_supply_rate: float = FORMATION_FULL_SUPPLY_RATE,
) -> float:
    """
    s* — the largest charter share at which private investors still supply
    ALL needed formation (§8.9c).

    Governing equation — invert r_priv(s*) = r_full:
        s* = 1 − r_full / (1/ν − δ)

    Worked example (defaults): s* = 1 − 0.10/0.20 = 0.50. Compare
    formation_share_required(ε): s_required crosses s* at ε ≈ 0.33 — below
    that the charter doctrine is genuinely free; above it the commons must
    co-fund formation from its own income.

    Args:
        capital_output_ratio: ν (> 0).
        depreciation_rate: δ (≥ 0).
        full_supply_rate: r_full (> 0; must not exceed the gross return).

    Returns:
        s* ∈ [0, 1).
    """
    r_gross = private_return(0.0, capital_output_ratio, depreciation_rate)
    if full_supply_rate > r_gross:
        raise ValueError(
            f"full_supply_rate {full_supply_rate} exceeds gross return "
            f"{r_gross}: no charter share is incentive-compatible"
        )
    return 1.0 - full_supply_rate / r_gross


def formation_feedback_simulation(
    n_years: int = 100,
    priority: str = "share",
    regime: str = "increasing_returns",
    population: float = 1_000_000.0,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    depreciation_rate: float = FORMATION_DEPRECIATION_RATE,
    hurdle_rate_min: float = FORMATION_HURDLE_RATE_MIN,
    full_supply_rate: float = FORMATION_FULL_SUPPLY_RATE,
    estate_escheat_share: float = RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
    escalation: bool = False,
    charter_share_override: float | None = None,
    exit_horizon_years: float = RECAL_EXIT_HORIZON_YEARS,
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
    capacity_floor: float = RECAL_ESCALATION_CAPACITY_FLOOR,
) -> list[dict]:
    """
    Year-by-year formation-feedback simulation — §8.9c, forward Euler.

    Per year (Δt = 1):
        E        = total_eoh(ε_actual)              (lagged-ε physical state)
        Y        = ε_actual · E                      (realized machine output)
        demand   : dK_needed = max(0, K_req(ε_actual + dε/dt) − K)
                   — capacity is built one arc step ahead of ACTUAL ε (the
                   schedule ε_target is tracked separately as the delay
                   metric, so a stalled arc does not chase a runaway gap)
        charter  : s = clamp((φ_t(ε_next_goal)·K_req − (T_K + estate))
                             / dK_needed, 0, 1)     (escalation forces s=1)
        supply   : private_funded = f(s) · dK_needed
        budget   : B = max(0, φ·Y − δ·T_K)           (net of own replacement)
        priority : "share"    → commons_funded = min(residual, B);
                                dividend = B − commons_funded
                   "dividend" → dividend = B; commons_funded = 0
        ledger   : T_K += s·private_funded + commons_funded + estate
                   K_priv += (1−s)·private_funded − estate
                   (owners maintain their own existing stock; the charter
                   attaches to NET NEW formation only)
        ε_next   = clamp((K − K₀)/(ν·E), 0, 0.99)    (capacity-derived)

    Estate flow: death_rate · share · K_priv (share = estate_escheat_share,
    or RECAL_ESCALATION_ESTATE_SHARE while escalation is latched). The
    §8.9b escalation trigger (escalation=True: adversarial regime AND
    capacity < floor or invariant failing) latches, as in the arc.

    charter_share_override pins s (0.0 = the NULL ANCHOR: no charter, full
    private funding — must reproduce the canonical ~50-year arc pace; the
    baseline every feedback effect is measured against).

    Conservation (T_K + K_priv = K) is exact by construction; asserted in
    tests. Exit channels are evaluated each year at ACTUAL ε and the NET
    dividend — the feedback-consistent invariant check.

    Args:
        n_years: Simulation horizon in years.
        priority: "share" (formation first) or "dividend" (dividend first).
        regime: K_entry regime for the exit evaluation.
        population: Total population.
        capital_output_ratio: ν (> 0).
        epsilon_rate_per_year: Canonical arc speed (≥ 0) — sets both the
            schedule metric and the one-step-ahead capacity goal.
        depreciation_rate: δ (≥ 0).
        hurdle_rate_min / full_supply_rate: investment-supply knobs.
        estate_escheat_share: Baseline capital-estate escheat (∈ [0, 1]).
        escalation: Enable the §8.9b escalation clause (latching).
        charter_share_override: Pin s to a constant (None = endogenous).
        exit_horizon_years / min_viable_population / underwrite_fraction /
            capacity_floor: exit-evaluation and trigger parameters.

    Returns:
        list[dict] — one row per year (year 0 = initial state, no flows)
        with keys: year, eps_actual, eps_target, eps_gap, capital_stock,
        commons_capital, private_capital, tau, s_applied, r_priv,
        supply_fraction, dk_needed, private_funded, commons_funded,
        formation_shortfall, stalled, replacement_commons, income_gross,
        dividend_per_capita, escalation_active, channel, t_exit_self_years,
        entry_capacity, exit_financeable.
    """
    if priority not in _PRIORITIES:
        raise ValueError(
            f"priority must be one of {_PRIORITIES}, got {priority!r}"
        )
    if n_years < 1:
        raise ValueError(f"n_years must be >= 1, got {n_years}")
    if not 0.0 <= estate_escheat_share <= 1.0:
        raise ValueError(
            f"estate_escheat_share must be in [0, 1], got {estate_escheat_share}"
        )
    if charter_share_override is not None and not 0.0 <= charter_share_override <= 1.0:
        raise ValueError(
            f"charter_share_override must be in [0, 1], got {charter_share_override}"
        )

    k0 = CAPITAL_STOCK_DEFAULT
    eps = 0.0
    k = k0
    t_k = CONTESTABILITY_PHI_FLOOR * k0  # the §8.9 initial endowment
    k_priv = k - t_k
    escalated = False

    rows: list[dict] = []

    def _row(year: int, **flows: object) -> dict:
        base: dict = {
            "year": year,
            "eps_actual": eps,
            "eps_target": min(_EPS_MAX, epsilon_rate_per_year * year),
            "eps_gap": min(_EPS_MAX, epsilon_rate_per_year * year) - eps,
            "capital_stock": k,
            "commons_capital": t_k,
            "private_capital": k_priv,
            "tau": t_k / k,
            "escalation_active": escalated,
        }
        base.update(flows)
        return base

    zero_flows = {
        "s_applied": 0.0, "r_priv": private_return(
            0.0, capital_output_ratio, depreciation_rate),
        "supply_fraction": 1.0, "dk_needed": 0.0, "private_funded": 0.0,
        "commons_funded": 0.0, "formation_shortfall": 0.0, "stalled": False,
        "replacement_commons": 0.0, "income_gross": 0.0,
        "dividend_per_capita": 0.0, "channel": "labor",
        "t_exit_self_years": 0.0, "entry_capacity": float("inf"),
        "exit_financeable": True,
    }
    rows.append(_row(0, **zero_flows))

    for year in range(1, n_years + 1):
        e_total = total_eoh(epsilon=eps, population=population)["total"]
        y = eps * e_total
        phi = t_k / k
        income_gross = phi * y
        replacement = depreciation_rate * t_k
        budget = max(0.0, income_gross - replacement)

        # Estate flow (D5 extended to capital; escalation raises the share).
        share_estate = (
            RECAL_ESCALATION_ESTATE_SHARE if escalated else estate_escheat_share
        )
        estate = min(ANNUAL_DEATH_RATE * share_estate * k_priv, k_priv)

        # Formation demand: one arc step ahead of ACTUAL ε.
        eps_goal = min(_EPS_MAX, eps + epsilon_rate_per_year)
        k_req = capital_stock_epsilon(eps_goal, population, capital_output_ratio)
        dk_needed = max(0.0, k_req - k)

        # Charter share of new formation.
        if charter_share_override is not None:
            s = charter_share_override
        elif escalated:
            s = 1.0
        elif dk_needed > 0.0:
            s = min(1.0, max(
                0.0,
                (commonized_fraction(eps_goal) * k_req - (t_k + estate))
                / dk_needed,
            ))
        else:
            s = 0.0

        r_priv = private_return(s, capital_output_ratio, depreciation_rate)
        f = investment_supply_fraction(
            s, capital_output_ratio, depreciation_rate,
            hurdle_rate_min, full_supply_rate,
        )
        private_funded = f * dk_needed
        residual = dk_needed - private_funded

        if priority == "share":
            commons_funded = min(residual, budget)
            dividend_pool = budget - commons_funded
        else:  # dividend-first
            commons_funded = 0.0
            dividend_pool = budget

        dk_actual = private_funded + commons_funded
        shortfall = dk_needed - dk_actual
        stalled = dk_needed > _STALL_TOL_TEH and dk_actual <= _STALL_TOL_TEH

        # Ledger update (conservation: T_K + K_priv = K, exact).
        t_k += s * private_funded + commons_funded + estate
        k_priv += (1.0 - s) * private_funded - estate
        k += dk_actual

        # Capacity-derived ε (lagged E — forward Euler).
        eps = min(_EPS_MAX, max(0.0, (k - k0) / (capital_output_ratio * e_total)))

        dividend_per_capita = dividend_pool / population
        channels = _exit_channels(
            eps, regime, dividend_per_capita, t_k,
            RECAL_FOUNDING_LABOR_HOURS, exit_horizon_years,
            min_viable_population, underwrite_fraction,
        )

        if escalation and not escalated:
            if regime == "increasing_returns" and (
                channels["entry_capacity"] < capacity_floor
                or not channels["exit_financeable"]
            ):
                escalated = True  # latch: escalations do not flap

        rows.append(_row(
            year,
            s_applied=s,
            r_priv=r_priv,
            supply_fraction=f,
            dk_needed=dk_needed,
            private_funded=private_funded,
            commons_funded=commons_funded,
            formation_shortfall=shortfall,
            stalled=stalled,
            replacement_commons=replacement,
            income_gross=income_gross,
            dividend_per_capita=dividend_per_capita,
            channel=channels["channel"],
            t_exit_self_years=channels["t_exit_self_years"],
            entry_capacity=channels["entry_capacity"],
            exit_financeable=channels["exit_financeable"],
        ))
    return rows


def formation_verdict(
    rows: list[dict],
    epsilon_rate_per_year: float = RECAL_EPSILON_RATE_PER_YEAR,
    capital_output_ratio: float = RECAL_CAPITAL_OUTPUT_RATIO,
    depreciation_rate: float = FORMATION_DEPRECIATION_RATE,
    full_supply_rate: float = FORMATION_FULL_SUPPLY_RATE,
) -> dict:
    """
    The §8.9c summary verdict over a formation_feedback_simulation() run.

    Reports the questions the theory needs answered, honestly:
        invariant_holds     — exit_financeable at EVERY simulated year?
        first_failure_year  — first year it fails (None if never)
        years_to_eps_95     — arrival at ε ≥ 0.95 (None = never within run)
        delay_years         — arrival minus the canonical schedule
                              (0.95 / (dε/dt) ≈ 48 yr at defaults)
        stalled / stall_eps — did formation ever fully stop with unmet
                              demand, and at what ε
        terminal_eps        — ε at the end of the run
        s_star              — the incentive-compatible share
        min_dividend_after_takeoff / terminal_dividend — the feedback-
                              consistent dividend path (compare the static
                              §8.9b gross figures)

    Args:
        rows: Output of formation_feedback_simulation().
        epsilon_rate_per_year: The canonical arc speed used for the
            schedule benchmark.
        capital_output_ratio / depreciation_rate / full_supply_rate:
            passed through to incentive_compatible_share().

    Returns:
        dict with the keys above.
    """
    if not rows:
        raise ValueError("rows must be non-empty")

    failures = [r["year"] for r in rows if not r["exit_financeable"]]
    arrival = next((r["year"] for r in rows if r["eps_actual"] >= 0.95), None)
    canonical_years = (
        0.95 / epsilon_rate_per_year if epsilon_rate_per_year > 0.0 else None
    )
    stall_rows = [r for r in rows if r["stalled"]]
    # Dividend after machine output becomes nontrivial (ε ≥ 0.1).
    post_takeoff = [
        r["dividend_per_capita"] for r in rows if r["eps_actual"] >= 0.1
    ]

    return {
        "invariant_holds": not failures,
        "first_failure_year": failures[0] if failures else None,
        "years_to_eps_95": arrival,
        "delay_years": (
            arrival - canonical_years
            if arrival is not None and canonical_years is not None else None
        ),
        "stalled": bool(stall_rows),
        "stall_eps": stall_rows[0]["eps_actual"] if stall_rows else None,
        "terminal_eps": rows[-1]["eps_actual"],
        "s_star": incentive_compatible_share(
            capital_output_ratio, depreciation_rate, full_supply_rate
        ),
        "min_dividend_after_takeoff": min(post_takeoff) if post_takeoff else None,
        "terminal_dividend": rows[-1]["dividend_per_capita"],
        "n_years": rows[-1]["year"],
    }
