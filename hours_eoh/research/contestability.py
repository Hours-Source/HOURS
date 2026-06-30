"""
Contestability instrumentation — reconciliation §8.

EXPERIMENTAL TIER — not stable API. Functional forms are proposed, not
calibrated from empirical data. Regime uncertainty is real (§8.5): the model
cannot know in advance whether automated capital follows the increasing-returns
or replicable trajectory. Default to increasing_returns (adversarial) as the
design-conservative posture (reconciliation §8.5).

The contestability invariant (CI):

    χ(ε) = P(ε) / K_entry(ε) ≥ 1   for all ε ∈ [0, 0.99]

Where:
    P(ε)       — portable per-capita endowment (sufficiency floor + Trust dividend)
    K_entry(ε) — sunk cost of founding a viable alternative collective
    χ ≥ 1      — exit is substantive; any concentration is chosen, not coerced
    χ < 1      — exit is nominal; "HOURS has rebuilt the knife no one is
                  holding inside its own ledger" (reconciliation §8.1)

NOTE: P(ε) is modeled as the population-average portable endowment — the same
universal Trust dividend and guarantee floor for every individual at a given ε,
regardless of tenure in the collective. Individual P with tenure-based vesting
is a known extension (reconciliation §9, open item 7). chi_arc() outputs are
labeled accordingly.

Public functions:
    portable_endowment(epsilon, population, trust_balance) → dict
    entry_cost(epsilon, regime, k0, k_slope) → float
    contestability_margin(epsilon, population, trust_balance, regime, ...) → dict
    commonized_fraction(epsilon) → float
    trust_capital_ratio(trust_balance, capital_stock) → float
    tau_gradient_check(eps_lo, eps_hi, trust_lo, trust_hi, cap_lo, cap_hi) → dict
    min_levy_for_pi(epsilon, trust_balance, capital_stock, g_priv) → dict
    chi_arc(n_points, regime, population, trust_balance, capital_stock) → list[dict]

Mission Statement: §"Contestability — the invariant the arc must preserve."
"""

from __future__ import annotations

from hours_eoh.core.fiscal import sufficiency_guarantee
from hours_eoh.data import (
    AGE_GROUPS, PERSONAL_EOH_BASE, DEP_RATE, DIV_RATE,
    CONTESTABILITY_K0_TEH, CONTESTABILITY_K_SLOPE,
    CONTESTABILITY_K_FLOOR_FRACTION,
    CONTESTABILITY_CHI_WARN, CONTESTABILITY_CHI_CRIT,
    CONTESTABILITY_PHI_FLOOR, CONTESTABILITY_PHI_EXPONENT,
    CONTESTABILITY_G_PRIV, CONTESTABILITY_CAPITAL_YIELD_RATE,
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
)

# Recompute locally — do not import the private constant from fiscal.py.
_AGE_WEIGHTED_EOH_MEAN: float = sum(
    v["fraction"] * v["eoh_weight"] for v in AGE_GROUPS.values()
)  # ≈ 1.475


# ---------------------------------------------------------------------------
# P(ε) — portable per-capita endowment
# ---------------------------------------------------------------------------

def portable_endowment(
    epsilon: float,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
) -> dict:
    """
    Population-average portable per-capita endowment P(ε).

    Governing equation:
        P(ε) = S(ε) + D(ε)

    Where:
        S(ε) = sufficiency_guarantee(ε, capital_fulfilled=ε·ā·EOH_base)["total_per_person"]
               — the per-recipient guarantee floor; eoh_reimbursement declines to zero as
                 machines fulfill personal EOH; meaningful-activity bonus grows quadratically
        D(ε) = trust_balance · DEP_RATE · DIV_RATE / population
               — per-capita Trust dividend (universal, not tenure-dependent)
        ā    = _AGE_WEIGHTED_EOH_MEAN ≈ 1.475
               — population-weighted EOH load per person

    NOTE: P is modeled as population-average. Individual P with tenure-based
    vesting is a known extension (§9 open item 7).

    Worked example (ε=0.40, population=1M, trust_balance=35B TEH):
        capital_fulfilled = 0.40 × 1.475 × 1500 = 885 h/yr
        S ≈ 2332 − 885 + 162 ≈ 1609 TEH/person   (guarantee, ε-scaled)
        D = 35B × 0.045 × 0.40 / 1M = 630 TEH/person
        P ≈ 2239 TEH/person

    ε-behavior:
        ε=0.00: P ≈ 2962 TEH/person (full eoh reimbursement + base meaningful-activity)
        ε=0.99: P ≈ 948  TEH/person (eoh reimbursement ≈ 0; only bonus + dividend)

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population (default: 1M).
        trust_balance: Trust fund balance in TEH (default: TRUST_BASE_TEH).

    Returns:
        dict with keys: p, guarantee_per_person, trust_dividend_per_capita,
        capital_fulfilled_per_person, epsilon.
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if population <= 0:
        raise ValueError(f"population must be positive, got {population}")

    capital_fulfilled = epsilon * _AGE_WEIGHTED_EOH_MEAN * PERSONAL_EOH_BASE
    guarantee = sufficiency_guarantee(
        population=population,
        epsilon=epsilon,
        capital_personal_eoh_fulfilled_per_person=capital_fulfilled,
    )
    trust_dividend = trust_balance * DEP_RATE * DIV_RATE / population
    p = guarantee["total_per_person"] + trust_dividend

    return {
        "p": p,
        "guarantee_per_person": guarantee["total_per_person"],
        "trust_dividend_per_capita": trust_dividend,
        "capital_fulfilled_per_person": capital_fulfilled,
        "epsilon": epsilon,
    }


# ---------------------------------------------------------------------------
# K_entry(ε, regime) — sunk cost of founding an alternative collective
# ---------------------------------------------------------------------------

def entry_cost(
    epsilon: float,
    regime: str = "increasing_returns",
    k0: float = CONTESTABILITY_K0_TEH,
    k_slope: float = CONTESTABILITY_K_SLOPE,
) -> float:
    """
    Sunk cost K_entry(ε) of founding a viable alternative collective.

    Governing equations (proposed functional forms — not calibrated from data):
        increasing_returns: K_entry = K₀ · (1 + k · ε)
        replicable:         K_entry = max(K₀ · (1 − k · ε), f · K₀)

    Where f = CONTESTABILITY_K_FLOOR_FRACTION = 0.10 (minimum founding cost
    as fraction of K₀, preventing collapse to zero in the replicable regime).

    Two empirically uncertain regimes (reconciliation §8.5):
        increasing_returns — automated capital concentrates; K_entry rises with ε
            as reaching viable automation becomes more expensive. Adversarial case.
        replicable — automated capital is cheap/open; K_entry falls with ε
            (fabricator on every desk). Contestability is nearly free.

    Default is increasing_returns (adversarial) as the design-conservative posture.

    Worked example (k₀=1800, k=1.6):
        ε=0.00, increasing_returns: K_entry = 1800 TEH
        ε=0.99, increasing_returns: K_entry = 1800 × 2.584 = 4651 TEH
        ε=0.99, replicable:         K_entry = max(1800 × (−0.584), 180) = 180 TEH

    Args:
        epsilon: Automation level [0.0, 0.99].
        regime: "increasing_returns" or "replicable".
        k0: Base founding cost at ε=0 (TEH/person).
        k_slope: Rate of K_entry change per unit ε.

    Returns:
        K_entry in TEH/person (float > 0).
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    if regime == "increasing_returns":
        return k0 * (1.0 + k_slope * epsilon)
    elif regime == "replicable":
        return max(k0 * (1.0 - k_slope * epsilon), CONTESTABILITY_K_FLOOR_FRACTION * k0)
    else:
        raise ValueError(
            f"regime must be 'increasing_returns' or 'replicable', got {regime!r}"
        )


# ---------------------------------------------------------------------------
# χ(ε) — contestability margin
# ---------------------------------------------------------------------------

def contestability_margin(
    epsilon: float,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    regime: str = "increasing_returns",
    k0: float = CONTESTABILITY_K0_TEH,
    k_slope: float = CONTESTABILITY_K_SLOPE,
) -> dict:
    """
    Contestability margin χ(ε) = P(ε) / K_entry(ε).

    Governing equation (reconciliation §8.1):
        χ(ε) = P(ε) / K_entry(ε)   ≥ 1  required

    Status thresholds:
        χ ≥ CONTESTABILITY_CHI_WARN (1.20) → "OK"
        χ ≥ CONTESTABILITY_CHI_CRIT (1.00) → "WARN"
        χ < CONTESTABILITY_CHI_CRIT (1.00) → "CRIT" (invariant breached)

    Worked example (ε=0, defaults):
        P(0) ≈ 2962 TEH/person, K_entry(0) = 1800 TEH → χ ≈ 1.65  "OK"

    Worked example (ε=0.99, increasing_returns, defaults, no Trust growth):
        P(0.99) ≈ 948 TEH/person, K_entry(0.99) ≈ 4651 TEH → χ ≈ 0.20  "CRIT"
        This is the adversarial finding: without adequate commonization the
        invariant fails as automation matures.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        trust_balance: Trust fund balance in TEH.
        regime: "increasing_returns" (default/adversarial) or "replicable".
        k0: Base founding cost at ε=0.
        k_slope: Rate of K_entry change per unit ε.

    Returns:
        dict with keys: chi, p, k_entry, status, passes, regime, epsilon,
        guarantee_per_person, trust_dividend_per_capita.
    """
    p_result = portable_endowment(epsilon, population, trust_balance)
    p = p_result["p"]
    k = entry_cost(epsilon, regime, k0, k_slope)
    chi = p / k

    if chi >= CONTESTABILITY_CHI_WARN:
        status = "OK"
    elif chi >= CONTESTABILITY_CHI_CRIT:
        status = "WARN"
    else:
        status = "CRIT"

    return {
        "chi": chi,
        "p": p,
        "k_entry": k,
        "status": status,
        "passes": chi >= CONTESTABILITY_CHI_CRIT,
        "regime": regime,
        "epsilon": epsilon,
        "guarantee_per_person": p_result["guarantee_per_person"],
        "trust_dividend_per_capita": p_result["trust_dividend_per_capita"],
    }


# ---------------------------------------------------------------------------
# φ(ε) — commonized fraction of automation value
# ---------------------------------------------------------------------------

def commonized_fraction(epsilon: float) -> float:
    """
    Commonized fraction φ(ε) — share of automation-generated value held in common.

    Governing equation (proposed form — reconciliation §8.2 gives only constraints):
        φ(ε) = φ₀ + (1 − φ₀) · ε^n

    Where:
        φ₀ = CONTESTABILITY_PHI_FLOOR = 0.10  (minimum at ε=0)
        n  = CONTESTABILITY_PHI_EXPONENT = 1.5 (super-linear growth toward 1)

    Constraints from §8.2:
        - φ must be non-decreasing (satisfied by construction)
        - φ → 1 as ε → 1 in the increasing-returns regime (satisfied: φ(0.99) ≈ 0.99)

    Worked example:
        φ(0.00) = 0.100  (minimal commons at subsistence)
        φ(0.40) ≈ 0.328  (care economy: ~1/3 commonized)
        φ(0.99) ≈ 0.986  (near post-scarcity: nearly all automation value in common)

    Args:
        epsilon: Automation level [0.0, 0.99].

    Returns:
        φ(ε) ∈ [PHI_FLOOR, 1.0).
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")
    return CONTESTABILITY_PHI_FLOOR + (1.0 - CONTESTABILITY_PHI_FLOOR) * epsilon ** CONTESTABILITY_PHI_EXPONENT


# ---------------------------------------------------------------------------
# τ(ε) — Trust share of total automated capital
# ---------------------------------------------------------------------------

def trust_capital_ratio(
    trust_balance: float,
    capital_stock: float,
) -> float:
    """
    Trust-capital ratio τ = T / K.

    Governing equation (reconciliation §8.3):
        τ(ε) = T(ε) / K(ε)

    The Piketty-inversion condition requires dτ/dε ≥ 0 across the arc,
    which holds iff g_Trust ≥ g_priv. Use tau_gradient_check() to test this
    across two arc points.

    Args:
        trust_balance: Trust fund balance T (TEH).
        capital_stock: Total automated capital K (TEH).

    Returns:
        τ = T/K (dimensionless share ∈ [0, ∞)).
    """
    if capital_stock <= 0:
        raise ValueError(f"capital_stock must be positive, got {capital_stock}")
    return trust_balance / capital_stock


# ---------------------------------------------------------------------------
# dτ/dε — Piketty-inversion gradient check
# ---------------------------------------------------------------------------

def tau_gradient_check(
    eps_lo: float,
    eps_hi: float,
    trust_lo: float,
    trust_hi: float,
    cap_lo: float,
    cap_hi: float,
) -> dict:
    """
    Finite-difference check of dτ/dε — the Piketty-inversion condition.

    Governing equation (reconciliation §8.3):
        dτ/dε ≈ (τ_hi − τ_lo) / (ε_hi − ε_lo)   ≥ 0  required

    dτ/dε ≥ 0 ⟺ g_Trust ≥ g_priv. This is the design constraint that turns
    Piketty's "r > g" observation (private capital concentration) into a binding
    requirement on the common-fund levy schedule.

    Args:
        eps_lo: Lower ε bound.
        eps_hi: Upper ε bound (must be > eps_lo).
        trust_lo: Trust balance at eps_lo.
        trust_hi: Trust balance at eps_hi.
        cap_lo: Capital stock at eps_lo.
        cap_hi: Capital stock at eps_hi.

    Returns:
        dict with keys: dtau_deps, tau_lo, tau_hi, passes.
    """
    if eps_hi <= eps_lo:
        raise ValueError(f"eps_hi must be > eps_lo, got {eps_lo}, {eps_hi}")
    tau_lo = trust_capital_ratio(trust_lo, cap_lo)
    tau_hi = trust_capital_ratio(trust_hi, cap_hi)
    dtau = (tau_hi - tau_lo) / (eps_hi - eps_lo)
    return {
        "dtau_deps": dtau,
        "tau_lo": tau_lo,
        "tau_hi": tau_hi,
        "passes": dtau >= 0.0,
    }


# ---------------------------------------------------------------------------
# Levy schedule — minimum levy for Piketty inversion
# ---------------------------------------------------------------------------

def min_levy_for_pi(
    epsilon: float,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    g_priv: float = CONTESTABILITY_G_PRIV,
) -> dict:
    """
    Minimum levy revenue required to maintain dτ/dε ≥ 0 (Piketty-inversion condition).

    Governing equations (reconciliation §8.3):
        L_required = T · (g_priv + DEP_RATE · DIV_RATE)
        output_base = ε · K · CAPITAL_YIELD_RATE
        levy_fraction = L_required / output_base

    L_required covers two obligations:
        - T · g_priv: grow the Trust at least as fast as private capital
        - T · DEP_RATE · DIV_RATE: replace the annual dividend outflow

    ADVERSARIAL FINDING: at canonical defaults (Trust=35B, capital=2B, ε=0.40),
    levy_fraction ≈ 21 — far above 1.0, meaning the levy on automated output
    alone cannot satisfy the condition. This is an honest result: the Piketty-
    inversion condition cannot be maintained through levy on automated output
    alone in the adversarial regime; the Trust must itself be much larger than
    private capital stock. levy_as_fraction_of_automated_output > 1 means the
    required levy exceeds the entire automated output — correct behavior, not a bug.

    Args:
        epsilon: Automation level [0.0, 0.99].
        trust_balance: Trust fund balance T (TEH).
        capital_stock: Total automated capital K (TEH).
        g_priv: Assumed private capital growth rate (default: CONTESTABILITY_G_PRIV).

    Returns:
        dict with keys: levy_required_teh, automated_output_teh,
        levy_as_fraction_of_automated_output (None when ε=0),
        feasible, epsilon.
    """
    if not 0.0 <= epsilon <= 0.99:
        raise ValueError(f"epsilon must be in [0.0, 0.99], got {epsilon}")

    levy_required = trust_balance * (g_priv + DEP_RATE * DIV_RATE)

    if epsilon <= 0.0:
        return {
            "levy_required_teh": levy_required,
            "automated_output_teh": 0.0,
            "levy_as_fraction_of_automated_output": None,  # undefined at ε=0
            "feasible": False,
            "epsilon": epsilon,
        }

    automated_output = epsilon * capital_stock * CONTESTABILITY_CAPITAL_YIELD_RATE
    fraction = levy_required / automated_output

    return {
        "levy_required_teh": levy_required,
        "automated_output_teh": automated_output,
        "levy_as_fraction_of_automated_output": fraction,
        "feasible": fraction <= 1.0,
        "epsilon": epsilon,
    }


# ---------------------------------------------------------------------------
# Arc sweep
# ---------------------------------------------------------------------------

def chi_arc(
    n_points: int = 20,
    regime: str = "increasing_returns",
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
) -> list[dict]:
    """
    Arc sweep of the contestability invariant across ε ∈ [0, 0.99].

    Calls contestability_margin(), commonized_fraction(), trust_capital_ratio(),
    and min_levy_for_pi() at each ε point. Returns one row per point.

    Output labels chi as chi_population_avg to make explicit that P is the
    population-average portable endowment, not individually tenure-vested
    (see module docstring and §9 open item 7).

    Args:
        n_points: Number of ε points (default: 20).
        regime: K_entry regime (default: "increasing_returns").
        population: Total population.
        trust_balance: Trust fund balance (TEH).
        capital_stock: Total automated capital (TEH).

    Returns:
        list[dict] — one dict per ε with keys:
            epsilon, p, k_entry, chi_population_avg, phi, tau,
            levy_fraction, levy_feasible, status.
    """
    rows = []
    for i in range(n_points):
        eps = i / (n_points - 1) * 0.99 if n_points > 1 else 0.40
        chi_result = contestability_margin(eps, population, trust_balance, regime)
        phi = commonized_fraction(eps)
        tau = trust_capital_ratio(trust_balance, capital_stock)
        levy = min_levy_for_pi(eps, trust_balance, capital_stock)
        rows.append({
            "epsilon":            eps,
            "p":                  chi_result["p"],
            "k_entry":            chi_result["k_entry"],
            "chi_population_avg": chi_result["chi"],
            "phi":                phi,
            "tau":                tau,
            "levy_fraction":      levy["levy_as_fraction_of_automated_output"],
            "levy_feasible":      levy["feasible"],
            "status":             chi_result["status"],
        })
    return rows
