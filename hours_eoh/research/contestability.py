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

Two views of P(ε):
    Population-average — the same universal Trust dividend and guarantee floor
    for every individual at a given ε (portable_endowment()).
    Individual/marginal — tenure-vested dividend via
    portable_endowment_individual(); chi_marginal is χ for the tenure-0,
    savings-0 member, the person the invariant actually protects
    (reconciliation §9, open item 7).

Public functions:
    portable_endowment(epsilon, population, trust_balance) → dict
    portable_endowment_individual(epsilon, tenure_years, ...) → dict
    portable_endowment_federated(epsilon, collective_trust, ...) → dict
    exit_value(guarantee_per_person, dividend_vested, savings, rate) → dict
    entry_cost(epsilon, regime, k0, k_slope) → float
    entry_underwriting(epsilon, commons_balance, regime, ...) → dict
    commons_seed_required(min_viable_population, ...) → float
    machine_output_teh(epsilon, population) → float
    contestability_margin(epsilon, population, trust_balance, regime, ...) → dict
    contestability_margin_federated(epsilon, collective_trust, ...) → dict
    commonized_fraction(epsilon) → float
    trust_capital_ratio(trust_balance, capital_stock) → float
    tau_gradient_check(eps_lo, eps_hi, trust_lo, trust_hi, cap_lo, cap_hi) → dict
    min_levy_for_pi(epsilon, trust_balance, capital_stock, g_priv) → dict
    trust_required_for_chi(epsilon, chi_target, ...) → dict
    levy_schedule_for_chi(n_points, regime, ...) → list[dict]
    chi_arc(n_points, regime, population, trust_balance, capital_stock) → list[dict]

Mission Statement: §"Contestability — the invariant the arc must preserve."
"""

from __future__ import annotations

from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.fiscal import sufficiency_guarantee
from hours_eoh.data import (
    AGE_GROUPS, PERSONAL_EOH_BASE, DEP_RATE, DIV_RATE,
    CONTESTABILITY_K0_TEH, CONTESTABILITY_K_SLOPE,
    CONTESTABILITY_K_FLOOR_FRACTION,
    CONTESTABILITY_CHI_WARN, CONTESTABILITY_CHI_CRIT,
    CONTESTABILITY_PHI_FLOOR, CONTESTABILITY_PHI_EXPONENT,
    CONTESTABILITY_G_PRIV, CONTESTABILITY_CAPITAL_YIELD_RATE,
    CONTESTABILITY_VESTING_YEARS,
    CONTESTABILITY_MIN_VIABLE_POPULATION,
    CONTESTABILITY_UNDERWRITE_FRACTION,
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


def portable_endowment_individual(
    epsilon: float,
    tenure_years: float,
    vesting_years: float = CONTESTABILITY_VESTING_YEARS,
    savings: float = 0.0,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
) -> dict:
    """
    Individual portable endowment P_ind(ε) with tenure-based dividend vesting.

    Governing equation:
        P_ind(ε) = S(ε) + v(tenure) · D(ε) + savings
        v(tenure) = min(1, tenure_years / vesting_years)   (linear vesting)

    Where:
        S(ε) — sufficiency guarantee per person. UNCONDITIONAL: the floor is
               membership-independent (reconciliation §8.1), so it never vests.
        D(ε) — per-capita Trust dividend. Vests linearly over vesting_years;
               a new member (tenure=0) commands none of it on exit.
        savings — portable personal savings; add to P but are not guaranteed
               (reconciliation §8.1).

    This closes §9 open item 7 at the mechanism level: the population-average
    χ in portable_endowment() overstates exit viability for recent members.
    The marginal member (tenure=0, savings=0) has P_ind = S(ε) only — the
    honest lower bound the invariant must protect.

    Worked example (ε=0.40, defaults, trust=35B, pop=1M):
        S ≈ 1476 TEH/person, D = 630 TEH/person
        tenure=0:   P_ind ≈ 1476  (floor only)
        tenure=2.5: P_ind ≈ 1476 + 0.5·630 = 1791
        tenure≥5:   P_ind ≈ 2106  (equals population-average P)

    ε-behavior: S falls as machines fulfill personal EOH (see
    portable_endowment()); the vested dividend share is ε-invariant in this
    static model, so the marginal member's P declines fastest across the arc.

    Args:
        epsilon: Automation level [0.0, 0.99].
        tenure_years: Years of FEDERATION tenure (≥ 0). Tenure accrues to the
                      person federation-wide (reconciliation §8.7b): moving
                      between collectives never resets the clock or forfeits
                      vested balance.
        vesting_years: Years for the dividend to fully vest (> 0).
                       Default: CONTESTABILITY_VESTING_YEARS = 5.0.
        savings: Portable personal savings in TEH (≥ 0). Default 0.0.
        population: Total population (default: 1M).
        trust_balance: Trust fund balance in TEH (default: TRUST_BASE_TEH).

    Returns:
        dict with keys: p_individual, vested_fraction, guarantee_per_person,
        trust_dividend_vested, trust_dividend_full, savings, tenure_years,
        epsilon.
    """
    if tenure_years < 0.0:
        raise ValueError(f"tenure_years must be >= 0, got {tenure_years}")
    if vesting_years <= 0.0:
        raise ValueError(f"vesting_years must be > 0, got {vesting_years}")
    if savings < 0.0:
        raise ValueError(f"savings must be >= 0, got {savings}")

    avg = portable_endowment(epsilon, population, trust_balance)
    vested_fraction = min(1.0, tenure_years / vesting_years)
    dividend_vested = avg["trust_dividend_per_capita"] * vested_fraction
    p_individual = avg["guarantee_per_person"] + dividend_vested + savings

    return {
        "p_individual":          p_individual,
        "vested_fraction":       vested_fraction,
        "guarantee_per_person":  avg["guarantee_per_person"],
        "trust_dividend_vested": dividend_vested,
        "trust_dividend_full":   avg["trust_dividend_per_capita"],
        "savings":               savings,
        "tenure_years":          tenure_years,
        "epsilon":               epsilon,
    }


def portable_endowment_federated(
    epsilon: float,
    collective_trust: float,
    collective_population: float,
    federation_population: float | None = None,
    tenure_years: float = 0.0,
    vesting_years: float = CONTESTABILITY_VESTING_YEARS,
    savings: float = 0.0,
    commons_balance: float = 0.0,
) -> dict:
    """
    Two-tier portable endowment P_fed(ε) — reconciliation §8.7 (a)+(b),
    extended with the commons dividend (proposed §8.8, mechanism M1).

    Governing equation:
        P_fed(ε) = S(ε) + D_fed + v(tenure) · D_coll(ε) + savings
        D_coll   = collective_trust · DEP_RATE · DIV_RATE / collective_population
        D_fed    = commons_balance · DEP_RATE · DIV_RATE / federation_population
        v        = min(1, tenure_years / vesting_years)   (linear vesting)

    D_fed is the UNIVERSAL commons dividend: the federation commons pays its
    yield per capita to every member with NO vesting (Alaska Permanent Fund
    precedent — residency-based, not tenure-vested). This is what turns the
    §8.7c escheat from an adversarial finding into a stabilizer: consolidation
    moves capital from tenure-gated collective dividends into the universal
    tier, so the marginal member's P *rises* with concentration instead of
    being drained by it. The commons corpus stays indivisible (§8.7c); only
    yield distributes — exactly as collective trusts already pay dividends.
    Default commons_balance = 0.0 reproduces §8.7 behavior unchanged.

    Two-tier semantics (§8.7a): the sufficiency floor S is FEDERATION-guaranteed
    and membership-independent — it never vests and does not depend on which
    collective the member belongs to. The dividend claim D_coll is held against
    the member's own collective's trust through their capital account (§8.7b).
    tenure_years is FEDERATION tenure: moving between collectives never resets
    the clock or forfeits vested balance.

    S per person is population-invariant (sufficiency_guarantee's
    total_per_person depends only on ε), so the federation-level guarantee
    equals the per-collective number; federation_population is carried for
    context and future federation-level cost accounting.

    Identity (testable): with federation_population == collective_population,
    P_fed equals portable_endowment_individual(...)["p_individual"] exactly —
    both funnel through portable_endowment().

    Worked example (ε=0.40, collective_trust=35B/12, collective_pop=1M/12):
        S ≈ 1476 TEH/person (federation floor, ε-scaled)
        D_coll = (35B/12) × 0.045 × 0.40 / (1M/12) = 630 TEH/person
                 (equal split leaves the per-capita dividend unchanged)
        tenure=0:  P_fed ≈ 1476   (floor only — the marginal member)
        tenure≥5:  P_fed ≈ 2106
        with commons_balance=4.5B, fed_pop=1M: D_fed = 4.5B×0.018/1M = 81
        added at EVERY tenure, including tenure=0.

    ε-behavior: S falls as machines fulfill personal EOH (see
    portable_endowment()); D_coll is ε-invariant in this static view, so the
    marginal member's P declines fastest across the arc — unless the commons
    grows with ε (escheat + tithe), in which case D_fed partially offsets the
    decline. Meaningful across ε ∈ [0, 0.99]; no discontinuities as ε → 1.

    Args:
        epsilon: Automation level [0.0, 0.99].
        collective_trust: The member's collective's trust balance in TEH.
        collective_population: The collective's population (> 0).
        federation_population: Total federation population (None → treat the
            collective as the whole federation, the single-ledger limit).
        tenure_years: FEDERATION tenure in years (≥ 0). Default 0.0 — the
            marginal member the invariant protects.
        vesting_years: Years for the dividend to fully vest (> 0).
        savings: Portable personal savings in TEH (≥ 0).
        commons_balance: Federation commons balance in TEH (≥ 0). Its yield
            pays the universal unvested dividend D_fed. Default 0.0 — §8.7
            behavior, no commons dividend.

    Returns:
        dict with keys: p_federated, p_marginal, guarantee_per_person,
        dividend_full, dividend_vested, dividend_commons, vested_fraction,
        savings, tenure_years, epsilon, collective_trust,
        collective_population, federation_population.
    """
    if tenure_years < 0.0:
        raise ValueError(f"tenure_years must be >= 0, got {tenure_years}")
    if vesting_years <= 0.0:
        raise ValueError(f"vesting_years must be > 0, got {vesting_years}")
    if savings < 0.0:
        raise ValueError(f"savings must be >= 0, got {savings}")
    if federation_population is not None and federation_population <= 0:
        raise ValueError(
            f"federation_population must be positive, got {federation_population}"
        )
    if commons_balance < 0.0:
        raise ValueError(f"commons_balance must be >= 0, got {commons_balance}")

    fed_pop = collective_population if federation_population is None else federation_population
    # S is per-person and population-invariant; D_coll needs the collective's
    # own trust and population — portable_endowment() supplies both components.
    coll = portable_endowment(epsilon, collective_population, collective_trust)
    vested_fraction = min(1.0, tenure_years / vesting_years)
    dividend_vested = coll["trust_dividend_per_capita"] * vested_fraction
    # M1: universal commons dividend — unvested, so it reaches tenure-0.
    dividend_commons = commons_balance * DEP_RATE * DIV_RATE / fed_pop
    p_marginal = coll["guarantee_per_person"] + dividend_commons
    p_federated = p_marginal + dividend_vested + savings

    return {
        "p_federated":           p_federated,
        "p_marginal":            p_marginal,
        "guarantee_per_person":  coll["guarantee_per_person"],
        "dividend_full":         coll["trust_dividend_per_capita"],
        "dividend_vested":       dividend_vested,
        "dividend_commons":      dividend_commons,
        "vested_fraction":       vested_fraction,
        "savings":               savings,
        "tenure_years":          tenure_years,
        "epsilon":               epsilon,
        "collective_trust":      collective_trust,
        "collective_population": collective_population,
        "federation_population": fed_pop,
    }


def exit_value(
    guarantee_per_person: float,
    dividend_vested: float,
    savings: float = 0.0,
    rate: float = 1.0,
) -> dict:
    """
    Value a member commands on exit across a collective boundary — §8.7 (b)+(d).

    Governing equation:
        p_exit = S + (D_vested + savings) · r

    Where r is the inter-collective exchange rate r(home → destination) from
    research/coasean.exchange_rates(). The FLOOR IS NOT CONVERTED: S is
    federation-denominated and guaranteed everywhere (§8.7a), so it crosses
    the boundary at par. Only the home-collective-denominated capital account
    (vested dividend + savings) converts at the prevailing rate (§8.7b:
    accounts convert 1:1 at the exchange rate — a unit conversion, not a
    valuation; zero TEH is created or destroyed, §8.7d).

    Takes plain floats rather than an endowment result dict to avoid coupling
    to the differing key schemas of portable_endowment_individual()
    (trust_dividend_vested) and portable_endowment_federated()
    (dividend_vested).

    Worked example (S=1476, D_vested=630, savings=0, r=0.9):
        p_exit = 1476 + 630 × 0.9 = 2043 TEH — the member arrives in a
        lower-productivity collective with the floor intact and the account
        marked down by the rate.

    Args:
        guarantee_per_person: Federation floor S in TEH (≥ 0).
        dividend_vested: Vested capital-account dividend in home TEH (≥ 0).
        savings: Portable savings in home TEH (≥ 0).
        rate: Exchange rate r(home → destination) (> 0). 1.0 = symmetric
              collectives (the single-ledger limit).

    Returns:
        dict with keys: p_exit, floor_component, account_component_home,
        account_component_converted, rate.
    """
    if rate <= 0.0:
        raise ValueError(f"rate must be > 0, got {rate}")
    if guarantee_per_person < 0.0:
        raise ValueError(
            f"guarantee_per_person must be >= 0, got {guarantee_per_person}"
        )
    if dividend_vested < 0.0:
        raise ValueError(f"dividend_vested must be >= 0, got {dividend_vested}")
    if savings < 0.0:
        raise ValueError(f"savings must be >= 0, got {savings}")

    account_home = dividend_vested + savings
    account_converted = account_home * rate
    return {
        "p_exit":                      guarantee_per_person + account_converted,
        "floor_component":             guarantee_per_person,
        "account_component_home":      account_home,
        "account_component_converted": account_converted,
        "rate":                        rate,
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
# Entry underwriting — the commons as entry-financier (proposed §8.8, M2)
# ---------------------------------------------------------------------------

def entry_underwriting(
    epsilon: float,
    commons_balance: float,
    regime: str = "increasing_returns",
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
    k0: float = CONTESTABILITY_K0_TEH,
    k_slope: float = CONTESTABILITY_K_SLOPE,
) -> dict:
    """
    Commons-financed entry capacity — the Baumol threat made credible.

    Governing equations:
        deployable      = underwrite_fraction · commons_balance
        founding_need   = min_viable_population · K_entry(ε, regime)
        entry_capacity  = deployable / founding_need     ≥ 1  required

    Contestability (Baumol–Panzar–Willig 1982) disciplines an incumbent
    through the credible THREAT of entry — which requires entry finance, not
    that every individual carry K_entry in cash. χ(ε) = P/K_entry compares an
    individual's annual endowment flow to a one-time founding stock and is
    therefore nearly unclosable in the adversarial regime (trust required
    ≈ 6.9× base at ε=0.99; see trust_required_for_chi()). This function
    closes the stock side directly: the federation commons underwrites the
    founding capital of new collectives. Underwritten capital moves
    commons → new collective's trust — it stays commonized and indivisible
    (§8.7c), never becoming a personal claim, so the escheat rule is
    respected, and the §8.7c escheat itself becomes the feedback that makes
    concentration self-limiting: every consolidation feeds the fund that
    finances alternatives.

    The combined invariant (proposed §8.8):
        exit is financeable at ε  ⇔  χ_marginal(ε) ≥ 1  OR  entry_capacity(ε) ≥ 1
        (self-financed exit at low ε; commons-financed entry at high ε)

    Worked example (ε=0.99, increasing_returns, commons=1.57e10):
        K_entry ≈ 4651; founding_need = 5000 × 4651 ≈ 2.33e7
        deployable = 0.5 × 1.57e10 ≈ 7.8e9 → entry_capacity ≈ 337  "OK"
    At ε=0 the commons is typically empty (capacity 0) but χ_marginal ≈ 1.3
    carries the invariant; the crossover is covered by seeding the commons —
    see commons_seed_required().

    ε-behavior: founding_need rises with K_entry in the adversarial regime,
    but a tithe+escheat-fed commons grows faster along canonical trajectories,
    so capacity rises toward ε→1 — concentration finances its own
    contestability. Meaningful across ε ∈ [0, 0.99].

    Args:
        epsilon: Automation level [0.0, 0.99].
        commons_balance: Federation commons balance in TEH (≥ 0).
        regime: "increasing_returns" (default/adversarial) or "replicable".
        min_viable_population: Smallest population able to staff a viable
            alternative collective (uncalibrated placeholder — see data.py).
        underwrite_fraction: Max deployable share of the commons per period;
            the rest stays as the floor backstop (§8.7a).
        k0: Base founding cost at ε=0.
        k_slope: Rate of K_entry change per unit ε.

    Returns:
        dict with keys: entry_capacity, passes (capacity ≥ 1), deployable,
        founding_need, underwrite_per_founder (per-capita grant available,
        capped at K_entry), k_entry, min_viable_population,
        underwrite_fraction, regime, epsilon.
    """
    if commons_balance < 0.0:
        raise ValueError(f"commons_balance must be >= 0, got {commons_balance}")
    if min_viable_population <= 0.0:
        raise ValueError(
            f"min_viable_population must be > 0, got {min_viable_population}"
        )
    if not 0.0 <= underwrite_fraction <= 1.0:
        raise ValueError(
            f"underwrite_fraction must be in [0, 1], got {underwrite_fraction}"
        )

    k = entry_cost(epsilon, regime, k0, k_slope)
    deployable = underwrite_fraction * commons_balance
    founding_need = min_viable_population * k
    entry_capacity = deployable / founding_need
    underwrite_per_founder = min(k, deployable / min_viable_population)

    return {
        "entry_capacity":         entry_capacity,
        "passes":                 entry_capacity >= 1.0,
        "deployable":             deployable,
        "founding_need":          founding_need,
        "underwrite_per_founder": underwrite_per_founder,
        "k_entry":                k,
        "min_viable_population":  min_viable_population,
        "underwrite_fraction":    underwrite_fraction,
        "regime":                 regime,
        "epsilon":                epsilon,
    }


def commons_seed_required(
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
    k0: float = CONTESTABILITY_K0_TEH,
) -> float:
    """
    Commons seed capital for entry_capacity ≥ 1 at ε=0 (proposed §8.8, M2).

    Governing equation — invert entry_capacity(0) ≥ 1 for commons_balance:
        seed = min_viable_population · K_entry(0) / underwrite_fraction
             = min_viable_population · k0 / underwrite_fraction
        (K_entry(0) = k0 in both regimes)

    At ε=0 the commons has collected no tithe and no escheat, so without a
    seed the entry-underwriting arm of the combined invariant starts at
    capacity 0. χ_marginal ≈ 1.3 at ε=0 carries the invariant on its own
    there, but the seed removes the early-arc window where both arms could
    sag before escheat inflows begin.

    Worked example (defaults): 5000 × 1800 / 0.5 = 1.8e7 TEH — about 0.05%
    of TRUST_BASE_TEH. The early-arc gap closes for ~1/2000th of the Trust.

    Args:
        min_viable_population: Smallest viable founding cohort (> 0).
        underwrite_fraction: Max deployable commons share (∈ (0, 1]).
        k0: Base founding cost at ε=0.

    Returns:
        Seed balance in TEH (float > 0).
    """
    if min_viable_population <= 0.0:
        raise ValueError(
            f"min_viable_population must be > 0, got {min_viable_population}"
        )
    if not 0.0 < underwrite_fraction <= 1.0:
        raise ValueError(
            f"underwrite_fraction must be in (0, 1], got {underwrite_fraction}"
        )
    return min_viable_population * k0 / underwrite_fraction


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

    Marginal χ:
        chi_marginal = P_ind(tenure=0, savings=0) / K_entry — χ for the newest
        member, whose Trust dividend has not vested. Always ≤ chi. This is the
        honest lower bound: the invariant protects the person for whom exit is
        hardest (§9 open item 7). status/passes remain keyed to the
        population-average chi for backward compatibility; status_marginal
        reports the marginal member's position.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.
        trust_balance: Trust fund balance in TEH.
        regime: "increasing_returns" (default/adversarial) or "replicable".
        k0: Base founding cost at ε=0.
        k_slope: Rate of K_entry change per unit ε.

    Returns:
        dict with keys: chi, chi_marginal, p, p_marginal, k_entry, status,
        status_marginal, passes, regime, epsilon, guarantee_per_person,
        trust_dividend_per_capita.
    """
    p_result = portable_endowment(epsilon, population, trust_balance)
    p = p_result["p"]
    p_marginal = p_result["guarantee_per_person"]  # tenure=0: unvested dividend
    k = entry_cost(epsilon, regime, k0, k_slope)
    chi = p / k
    chi_marginal = p_marginal / k

    def _status(value: float) -> str:
        if value >= CONTESTABILITY_CHI_WARN:
            return "OK"
        if value >= CONTESTABILITY_CHI_CRIT:
            return "WARN"
        return "CRIT"

    return {
        "chi": chi,
        "chi_marginal": chi_marginal,
        "p": p,
        "p_marginal": p_marginal,
        "k_entry": k,
        "status": _status(chi),
        "status_marginal": _status(chi_marginal),
        "passes": chi >= CONTESTABILITY_CHI_CRIT,
        "regime": regime,
        "epsilon": epsilon,
        "guarantee_per_person": p_result["guarantee_per_person"],
        "trust_dividend_per_capita": p_result["trust_dividend_per_capita"],
    }


def contestability_margin_federated(
    epsilon: float,
    collective_trust: float,
    collective_population: float,
    federation_population: float | None = None,
    regime: str = "increasing_returns",
    k0: float = CONTESTABILITY_K0_TEH,
    k_slope: float = CONTESTABILITY_K_SLOPE,
    commons_balance: float = 0.0,
    min_viable_population: float = CONTESTABILITY_MIN_VIABLE_POPULATION,
    underwrite_fraction: float = CONTESTABILITY_UNDERWRITE_FRACTION,
) -> dict:
    """
    Per-collective contestability margin under the two-tier Trust — §8.7,
    extended with the commons closure mechanisms (proposed §8.8).

    Governing equation (reconciliation §8.1, re-based on the two-tier P):
        χ(ε)          = P_fed(fully vested) / K_entry(ε)
        χ_marginal(ε) = (S(ε) + D_fed(ε)) / K_entry(ε)   (tenure-0 member)
        D_fed         = commons_balance · DEP_RATE · DIV_RATE / fed_pop
        exit_financeable ⇔ χ_marginal ≥ 1  OR  entry_capacity ≥ 1

    The marginal member — federation tenure 0, savings 0 — commands the
    federation floor S plus the universal (unvested) commons dividend D_fed;
    they are the person the invariant actually protects (§9 open item 7).
    With commons_balance = 0 (default), D_fed = 0 and entry_capacity = 0:
    every value reproduces §8.7 behavior exactly, and exit_financeable
    reduces to χ_marginal ≥ 1. Status thresholds and key shape mirror
    contestability_margin(); identity (testable): with
    federation_population == collective_population and commons_balance = 0
    this equals contestability_margin(epsilon, collective_population,
    collective_trust, ...) key-for-key on chi, chi_marginal, p, p_marginal,
    k_entry.

    Worked example (ε=0.40, 12-collective equal split of 35B/1M, no commons):
        S ≈ 1476, D_coll = 630, K_entry = 1800·(1+1.6·0.40) = 2952
        χ = (1476+630)/2952 ≈ 0.71 "CRIT"; χ_marginal = 1476/2952 ≈ 0.50
        The equal split preserves per-capita values, so the federation
        inherits the single-ledger adversarial finding unchanged.
    Same point with commons_balance = 4.5e9 (canonical escheat by ε=0.40):
        D_fed = 81 → χ_marginal ≈ 0.53 — still CRIT on its own, but
        entry_capacity = 0.5·4.5e9/(5000·2952) ≈ 152 → exit_financeable.

    Args:
        epsilon: Automation level [0.0, 0.99].
        collective_trust: The collective's trust balance in TEH.
        collective_population: The collective's population (> 0).
        federation_population: Total federation population (None → collective
            is the whole federation).
        regime: "increasing_returns" (default/adversarial) or "replicable".
        k0: Base founding cost at ε=0.
        k_slope: Rate of K_entry change per unit ε.
        commons_balance: Federation commons balance in TEH (≥ 0). Feeds both
            the universal dividend (M1) and entry underwriting (M2).
        min_viable_population: Smallest viable founding cohort (> 0).
        underwrite_fraction: Max deployable commons share (∈ [0, 1]).

    Returns:
        dict with keys: chi, chi_marginal, p, p_marginal, k_entry, status,
        status_marginal, passes, regime, epsilon, guarantee_per_person,
        dividend_per_capita, dividend_commons, entry_capacity,
        exit_financeable, collective_trust, collective_population.
    """
    vested = portable_endowment_federated(
        epsilon,
        collective_trust=collective_trust,
        collective_population=collective_population,
        federation_population=federation_population,
        tenure_years=CONTESTABILITY_VESTING_YEARS,  # fully vested
        commons_balance=commons_balance,
    )
    p = vested["p_federated"]
    p_marginal = vested["p_marginal"]  # tenure=0: floor + commons dividend
    k = entry_cost(epsilon, regime, k0, k_slope)
    chi = p / k
    chi_marginal = p_marginal / k
    underwriting = entry_underwriting(
        epsilon, commons_balance, regime,
        min_viable_population, underwrite_fraction, k0, k_slope,
    )
    exit_financeable = (
        chi_marginal >= CONTESTABILITY_CHI_CRIT or underwriting["passes"]
    )

    def _status(value: float) -> str:
        if value >= CONTESTABILITY_CHI_WARN:
            return "OK"
        if value >= CONTESTABILITY_CHI_CRIT:
            return "WARN"
        return "CRIT"

    return {
        "chi": chi,
        "chi_marginal": chi_marginal,
        "p": p,
        "p_marginal": p_marginal,
        "k_entry": k,
        "status": _status(chi),
        "status_marginal": _status(chi_marginal),
        "passes": chi >= CONTESTABILITY_CHI_CRIT,
        "regime": regime,
        "epsilon": epsilon,
        "guarantee_per_person": vested["guarantee_per_person"],
        "dividend_per_capita": vested["dividend_full"],
        "dividend_commons": vested["dividend_commons"],
        "entry_capacity": underwriting["entry_capacity"],
        "exit_financeable": exit_financeable,
        "collective_trust": collective_trust,
        "collective_population": collective_population,
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

    CALIBRATION NOTE: τ = T/K ≈ 17.5 at canonical defaults is intentional
    (see docs/parameter_provenance.md: TRUST_BASE_TEH is sized at 35,000
    TEH/person to fund the guarantee; CAPITAL_STOCK_DEFAULT at 2,000
    TEH/person). The Trust dwarfing private capital makes the g_Trust ≥ g_priv
    rate condition expensive in absolute TEH — a large T growing at 3% needs a
    large levy. But the binding constraint for exit is not τ's level; it is the
    per-capita dividend (T·DEP_RATE·DIV_RATE/pop ≈ 630 TEH) versus K_entry
    (up to ≈4,651 TEH at ε=0.99). dτ/dε ≥ 0 governs the *trend* — the commons
    must not erode relative to private capital — while χ ≥ 1 requires the
    dividend to *grow* toward K_entry. See trust_required_for_chi() for the
    Trust balance that closes the χ gap.

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
# Derived levy schedule — the Trust path that holds χ ≥ target (§8.2)
# ---------------------------------------------------------------------------

def trust_required_for_chi(
    epsilon: float,
    chi_target: float = CONTESTABILITY_CHI_CRIT,
    population: float = 1_000_000.0,
    regime: str = "increasing_returns",
    k0: float = CONTESTABILITY_K0_TEH,
    k_slope: float = CONTESTABILITY_K_SLOPE,
) -> dict:
    """
    Trust balance required to hold the contestability invariant at a given ε.

    SUPERSEDED (proposed §8.9, 2026-07-26): the bare-χ target this inverts
    divides an annual income flow by a one-time founding stock (§8.8 RC4),
    which is why T_required balloons to 6.9× base — the demand that one
    year of dividend cover the whole founding cost. The dimensionally-clean
    successors are the time-to-finance-exit invariant and stock-based
    capital accounts in research/recalibration.py. Retained unchanged as
    the documented negative result: the trust-growth path cannot close
    bare χ, which is why entry underwriting (M2) exists.

    Governing equation — invert χ(ε) ≥ χ_target for T:
        P(ε) = S(ε) + T·DEP_RATE·DIV_RATE / pop  ≥  χ_target · K_entry(ε)
        T_required = max(0, χ_target·K_entry(ε) − S(ε)) · pop / (DEP_RATE·DIV_RATE)

    Where S(ε) is the per-person sufficiency guarantee (unconditional,
    membership-independent) and the dividend rate DEP_RATE·DIV_RATE converts a
    Trust stock into an annual per-capita flow. This is the §8.2 requirement
    made concrete: as K_entry rises and S falls across the arc, the only
    component of P that can rise to meet it is the commonized dividend, so the
    Trust must grow. This function says by how much.

    Worked example (ε=0.99, increasing_returns, pop=1M, χ_target=1):
        K_entry ≈ 4651 TEH, S ≈ 318 TEH
        T_required = (4651 − 318) × 1M / (0.045 × 0.40) ≈ 2.41e11 TEH
        — roughly 6.9× the canonical TRUST_BASE_TEH of 3.5e10. The invariant
        is closable, but only with a Trust that grows ~7× across the arc.

    ε-behavior: in the increasing_returns regime T_required rises
    monotonically (K_entry rises, S falls). In the replicable regime it
    typically falls to 0 at high ε (K_entry collapses below S).

    Args:
        epsilon: Automation level [0.0, 0.99].
        chi_target: Required contestability margin. Default: 1.0 (the invariant).
        population: Total population.
        regime: "increasing_returns" (default/adversarial) or "replicable".
        k0: Base founding cost at ε=0.
        k_slope: Rate of K_entry change per unit ε.

    Returns:
        dict with keys: trust_required, gap_vs_base (T_required −
        TRUST_BASE_TEH; negative = current base suffices), dividend_required
        (per-capita annual dividend needed), guarantee_per_person, k_entry,
        chi_target, epsilon.
    """
    if chi_target <= 0.0:
        raise ValueError(f"chi_target must be > 0, got {chi_target}")

    p_result = portable_endowment(epsilon, population, TRUST_BASE_TEH)
    s = p_result["guarantee_per_person"]
    k = entry_cost(epsilon, regime, k0, k_slope)

    dividend_required = max(0.0, chi_target * k - s)
    trust_required = dividend_required * population / (DEP_RATE * DIV_RATE)

    return {
        "trust_required":       trust_required,
        "gap_vs_base":          trust_required - TRUST_BASE_TEH,
        "dividend_required":    dividend_required,
        "guarantee_per_person": s,
        "k_entry":              k,
        "chi_target":           chi_target,
        "epsilon":              epsilon,
    }


def machine_output_teh(epsilon: float, population: float = 1_000_000.0) -> float:
    """
    Machine-fulfilled EOH per year — the physically-consistent levy base.

    Governing equation:
        machine_output(ε) = ε · total_eoh(ε)     [TEH/yr, population-level]

    ε is BY DEFINITION the fraction of total EOH fulfilled by machines
    (CLAUDE.md: compute_epsilon(machine_eoh, total_eoh)), so the value of
    automated production per year is ε times the total entropy obligation —
    measured by the pipeline's own generation functions, not assumed. The
    static base ε·K·CONTESTABILITY_CAPITAL_YIELD_RATE understates this ~12×
    at high ε (198 vs 2,421 TEH/person·yr at ε=0.99 at canonical defaults)
    because CAPITAL_STOCK_DEFAULT is an ε=0-era calibration held fixed while
    ε rises — a capital stock physically incapable of fulfilling 99% of EOH.
    Using the pipeline's own measure removes that inconsistency from the
    levy-feasibility question (proposed §8.8, mechanism M3).

    ε-behavior: rises smoothly from 0 at ε=0 to ≈ total EOH at ε→1; no
    discontinuities. Uses canonical physical state via total_eoh(epsilon=...)
    backward-compat pathway.

    Args:
        epsilon: Automation level [0.0, 0.99].
        population: Total population.

    Returns:
        Machine-fulfilled TEH per year, population-level (float ≥ 0).
    """
    return epsilon * total_eoh(epsilon=epsilon, population=population)["total"]


def levy_schedule_for_chi(
    n_points: int = 20,
    regime: str = "increasing_returns",
    population: float = 1_000_000.0,
    capital_stock: float = CAPITAL_STOCK_DEFAULT,
    chi_target: float = CONTESTABILITY_CHI_CRIT,
    trust_start: float = TRUST_BASE_TEH,
    levy_base: str = "capital_yield",
) -> list[dict]:
    """
    Common-fund levy schedule that holds χ ≥ χ_target across the arc (§8.2).

    SUPERSEDED (proposed §8.9, 2026-07-26): the trust targets this schedule
    chases inherit the §8.8 RC4 flow-vs-stock artifact (see
    trust_required_for_chi()), so its growth-step infeasibility is a
    property of the retired invariant, not of the system. Retained
    unchanged as the documented negative result. The recalibrated frame
    (research/recalibration.py) replaces the levy-rate race entirely:
    the commons owns share φ(ε) of an ε-consistent capital stock, so
    dτ/dε ≥ 0 is structural and the dividend is funded by measured
    machine output.

    The missing Workstream B deliverable: derive, per ε-step, the levy revenue
    the Trust must collect so that the contestability invariant holds at every
    point on the arc. Treats each arc step as one accounting period.

    Governing equations, per step i:
        T_target(ε_i)   = max(trust_start, trust_required_for_chi(ε_i))
                          — the Trust never needs to shrink below its start
        ΔT_i            = T_target(ε_i) − T_target(ε_{i−1})     (0 at i=0)
        dividend_out_i  = T_target(ε_i) · DEP_RATE · DIV_RATE
                          — the outflow that must be replenished to hold T
        levy_required_i = max(0, ΔT_i) + dividend_out_i
        output_i        = ε_i · K · CONTESTABILITY_CAPITAL_YIELD_RATE   (capital_yield)
                        = machine_output_teh(ε_i, pop)                  (machine_output)
        levy_fraction_i = levy_required_i / output_i    (None at ε=0)
        feasible_i      = levy_fraction_i ≤ 1

    HONEST RESULT, NOT TUNED: with the default capital_yield base at
    canonical defaults in the adversarial regime the schedule is infeasible
    at every ε — but ~12× of that gap is a calibration artifact:
    CAPITAL_STOCK_DEFAULT (2,000 TEH/person) is an ε=0-era stock that cannot
    physically fulfill 99% of EOH, yet the base holds it fixed while ε rises.
    levy_base="machine_output" uses the pipeline's own measure of automated
    production (ε·total_eoh — see machine_output_teh()); under it the
    SUSTAINING levy (dividend outflow at a held T_target) becomes feasible
    across most of the arc, while the GROWTH steps (ΔT to reach the 6.9×
    trust target) remain infeasible in mid-arc. Even the corrected base
    cannot make χ_marginal ≥ 1 self-financing — that is what the
    entry-underwriting mechanism (entry_underwriting()) is for. Reporting
    the remaining infeasibility is the point (reconciliation §8.5;
    CLAUDE.md §5: if a result is ugly, report it).

    Args:
        n_points: Number of ε points across [0, 0.99]. Default: 20.
        regime: K_entry regime. Default: "increasing_returns" (adversarial).
        population: Total population.
        capital_stock: Total automated capital K (TEH), held fixed across the
            arc (static model; K(ε) dynamics are research/coasean.py Phase 3).
            Used only when levy_base="capital_yield".
        chi_target: Required contestability margin. Default: 1.0.
        trust_start: Trust balance at ε=0. Default: TRUST_BASE_TEH.
        levy_base: "capital_yield" (default, §8.7-era static base) or
            "machine_output" (physically-consistent base, proposed §8.8 M3).

    Returns:
        list[dict] — one row per ε with keys:
            epsilon, k_entry, guarantee_per_person, trust_target, delta_trust,
            dividend_outflow, levy_required, automated_output,
            levy_fraction (None at ε=0), feasible, chi_check, levy_base.
        chi_check is contestability_margin() recomputed at trust_target — it
        must satisfy chi ≥ chi_target at every row (asserted in tests).
    """
    if levy_base not in ("capital_yield", "machine_output"):
        raise ValueError(
            f"levy_base must be 'capital_yield' or 'machine_output', got {levy_base!r}"
        )
    rows: list[dict] = []
    prev_target = None
    for i in range(n_points):
        eps = i / (n_points - 1) * 0.99 if n_points > 1 else 0.40
        req = trust_required_for_chi(eps, chi_target, population, regime)
        trust_target = max(trust_start, req["trust_required"])
        delta_trust = 0.0 if prev_target is None else trust_target - prev_target
        dividend_outflow = trust_target * DEP_RATE * DIV_RATE
        levy_required = max(0.0, delta_trust) + dividend_outflow

        if levy_base == "machine_output":
            automated_output = machine_output_teh(eps, population)
        else:
            automated_output = eps * capital_stock * CONTESTABILITY_CAPITAL_YIELD_RATE
        levy_fraction: float | None
        if automated_output > 0.0:
            levy_fraction = levy_required / automated_output
            feasible = levy_fraction <= 1.0
        else:
            levy_fraction = None  # undefined at ε=0
            feasible = False

        chi_check = contestability_margin(
            eps, population, trust_target, regime,
        )["chi"]

        rows.append({
            "epsilon":              eps,
            "k_entry":              req["k_entry"],
            "guarantee_per_person": req["guarantee_per_person"],
            "trust_target":         trust_target,
            "delta_trust":          delta_trust,
            "dividend_outflow":     dividend_outflow,
            "levy_required":        levy_required,
            "automated_output":     automated_output,
            "levy_fraction":        levy_fraction,
            "feasible":             feasible,
            "chi_check":            chi_check,
            "levy_base":            levy_base,
        })
        prev_target = trust_target
    return rows


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
    population-average portable endowment. chi_marginal is the tenure-0,
    savings-0 member's margin (unvested dividend — the honest lower bound;
    see portable_endowment_individual() and §9 open item 7).

    Args:
        n_points: Number of ε points (default: 20).
        regime: K_entry regime (default: "increasing_returns").
        population: Total population.
        trust_balance: Trust fund balance (TEH).
        capital_stock: Total automated capital (TEH).

    Returns:
        list[dict] — one dict per ε with keys:
            epsilon, p, k_entry, chi_population_avg, chi_marginal, phi, tau,
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
            "chi_marginal":       chi_result["chi_marginal"],
            "phi":                phi,
            "tau":                tau,
            "levy_fraction":      levy["levy_as_fraction_of_automated_output"],
            "levy_feasible":      levy["feasible"],
            "status":             chi_result["status"],
        })
    return rows
