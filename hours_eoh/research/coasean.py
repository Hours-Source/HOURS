"""
Coasean collective federation — experimental scaffold (reconciliation §§6–7).

A "Coasean collective" is an island of internal planning whose boundary sits
where internal coordination cost equals inter-collective transaction cost
(Coase 1937). Inside it, the EOH→TEH pipeline runs without a price mechanism.
Between collectives, exchange rates are discovered — not declared.

This module is EXPERIMENTAL (research-tier). API is unstable.
Do not import from core/, land/, or scenarios/.

Key concepts
------------
N(ε) — emergent collective count
    As ε rises, machine coordination costs fall and internal-planning islands
    can grow larger, so the total count consolidates:
        N(ε) = max(1, round(N_max × (1−ε)^exponent))
    At ε→1, N→1: the whole economy becomes one planning collective, recovering
    the single-ledger baseline as the limit case.

Collective
    A single planning island. Each runs the full EOH→TEH pipeline and fiscal
    snapshot internally. Population, Trust balance, capital stock, and ecosystem
    health may differ across collectives (heterogeneous federation).

N=1 regression anchor
    make_federation(n=1) must reproduce eoh_to_teh_pipeline() +
    fiscal_snapshot() to floating-point precision (n1_regression_anchor()).

Three-regime inflation theorem (reconciliation §7)
    Within-collective: floor-impossibility at all ε. TEH requires verified work;
        the floor price cannot inflate. within_inflation = 0 structurally.
    Inter-collective: relative inflation appears as exchange-rate movement in
        transition. An over-issuing collective sees its unit depreciate against
        its neighbors. exchange_rates() + three_regime_inflation() model this.
    System-wide: inflation-impossibility re-emerges as ε→1 asymptote. As N→1,
        no exchange rates remain to move; system_inflation → 0.
    Formal identity: system_inflation(ε) = inter_inflation × max(0, 1−ε).

Phase 1 (delivered)
    Collective dataclass, run_collective_period(), coasean_collective_count(),
    make_federation(), n1_regression_anchor().

Phase 2 (delivered)
    exchange_rates(), three_regime_inflation(), simulate_federation().
    make_federation() extended with ecosystem_health_schedule for heterogeneity.

Phase 3 (this file adds)
    Trust/capital dynamics in simulate_federation() (dynamics=True): the Trust
    grows by a common-fund levy on automated output and pays out its dividend;
    private capital grows at g_priv. τ = T/K is tracked per period with the
    Piketty-inversion check dτ ≥ 0 ⟺ g_Trust ≥ g_priv (reconciliation §8.3),
    reusing tau_gradient_check() from research/contestability.py.
    Settlement mechanics: bilateral_imbalances() + settlement_check() implement
    the paper's bilateral-imbalance-ceiling sketch (reconciliation §9-item-4);
    an over-issuing collective's unsettled deficit depreciates its unit —
    transition inflation carried honestly as an exchange-rate movement (§7).
    Discovery seam: exchange_rates(discovery_premium=...) layers discovered
    deviations over the productivity-parity baseline, mirroring the
    floor-price + market_premium seam in core/prices.py (reconciliation §3).

Phase 4 (this file adds) — reconciliation §8.7 two-tier Trust
    Boundary events: merge_collectives() and split_collective() with the
    indivisible-reserve escheat (§8.7c) and TEH-conservation postconditions
    (§8.7d — boundary events create and destroy zero TEH; exchange rates are
    unit conversions, not valuations).
    Federation commons: simulate_federation(commons=True) tracks a commons
    balance above the collective trusts — funded by a levy tithe
    (COASEAN_COMMONS_TITHE, Italian Law 59/1992 precedent) plus consolidation
    escheats — and reports per-collective χ each period via
    contestability_margin_federated() from research/contestability.py. The
    commons backs the sufficiency floor as reinsurance, not as payer.
"""

from __future__ import annotations

import random as _random
from dataclasses import dataclass, field
from typing import Any

from hours_eoh.data import (
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
    COASEAN_N_MAX,
    COASEAN_BOUNDARY_EXPONENT,
    COASEAN_RESERVE_FRACTION,
    COASEAN_IMBALANCE_CEILING,
    COASEAN_DEPRECIATION_SLOPE,
    COASEAN_COMMONS_TITHE,
    COASEAN_INDIVISIBLE_RESERVE_FRACTION,
    CONTESTABILITY_CAPITAL_YIELD_RATE,
    DEP_RATE,
    DIV_RATE,
)
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.research.contestability import (
    contestability_margin_federated,
    entry_underwriting,
    tau_gradient_check,
)


# ---------------------------------------------------------------------------
# Collective dataclass
# ---------------------------------------------------------------------------

@dataclass
class Collective:
    """
    A single Coasean planning island.

    Stores the outputs of one period's EOH→TEH pipeline and fiscal snapshot
    for a slice of the population with its own Trust sub-balance, capital
    sub-stock, and ecosystem health.

    Fields
    ------
    collective_id    : int   — index within the federation (0-based)
    epsilon          : float — shared automation level (same for all collectives)
    population       : float — this collective's population slice
    trust_balance    : float — this collective's Trust sub-balance (TEH)
    capital_stock    : float — this collective's capital stock (TEH)
    ecosystem_health : float — this collective's ecosystem health [0, 1]
    pipeline         : dict  — output of eoh_to_teh_pipeline() for this slice
    fiscal           : dict  — output of fiscal_snapshot() for this slice
    reserve          : float — inter-collective reserve held (COASEAN_RESERVE_FRACTION
                               of teh_created, earmarked for inter-collective exchange)

    Note: at N=1, pipeline and fiscal exactly reproduce the single-ledger
    reference calls — this is the regression anchor (n1_regression_anchor()).
    """

    collective_id:    int
    epsilon:          float
    population:       float
    trust_balance:    float
    capital_stock:    float
    ecosystem_health: float = 0.70
    pipeline:         dict = field(default_factory=dict)
    fiscal:           dict = field(default_factory=dict)
    reserve:          float = 0.0


# ---------------------------------------------------------------------------
# Phase 1: collective count, single-period run, federation factory, anchor
# ---------------------------------------------------------------------------

def coasean_collective_count(epsilon: float) -> int:
    """
    Emergent number of Coasean collectives at automation level ε.

    Governing equation:
        N(ε) = max(1, round(N_max × (1−ε)^exponent))

    where N_max = COASEAN_N_MAX and exponent = COASEAN_BOUNDARY_EXPONENT.

    ε-behavior
    ----------
    ε=0.00 → N = N_max (maximally fragmented; planning islands are small)
    ε=0.40 → N ≈ 12    (mid-arc consolidation)
    ε=0.90 → N ≈ 2     (near-post-scarcity; two large planning blocs)
    ε=0.99 → N = 1     (single collective; recovers single-ledger baseline)

    The formula is a working hypothesis from reconciliation §6. Real-world
    collective boundaries depend on governance, geography, and transaction
    cost structure — none of which is modeled here. Use N_max and exponent as
    calibration knobs, not physics parameters.

    Args:
        epsilon: Automation level ∈ [0, 0.99].

    Returns:
        Integer ≥ 1.
    """
    raw = COASEAN_N_MAX * (1.0 - epsilon) ** COASEAN_BOUNDARY_EXPONENT
    return max(1, round(raw))


def run_collective_period(
    epsilon: float,
    population: float,
    trust_balance: float,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run one period of the EOH→TEH pipeline and fiscal snapshot for a single collective.

    This is a thin wrapper that chains eoh_to_teh_pipeline() → fiscal_snapshot()
    with consistent parameters, so the N=1 collective is byte-for-byte identical
    to the single-ledger reference calls.

    Labor income passed to fiscal_snapshot is teh_created — the gross TEH earned
    by workers this period, per fiscal_snapshot docstring (§ "Worked example").

    Args:
        epsilon:           Automation level ∈ [0, 0.99].
        population:        Collective population.
        trust_balance:     Collective Trust sub-balance (TEH).
        capital_stock_teh: Collective capital stock (TEH).
        capital_age_ratio: Mean asset age ratio [0, 1].
        ecosystem_health:  Ecosystem health score [0, 1].

    Returns:
        (pipeline_dict, fiscal_dict) — raw outputs of the underlying core calls.
    """
    pipeline = eoh_to_teh_pipeline(
        epsilon,
        population=population,
        capital_stock=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
    )
    labor_income = pipeline["teh_created"]
    fiscal = fiscal_snapshot(
        trust_balance=trust_balance,
        labor_income=labor_income,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        population=population,
        epsilon=epsilon,
        ecosystem_health=ecosystem_health,
    )
    return pipeline, fiscal


def make_federation(
    epsilon: float,
    n: int | None = None,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
    ecosystem_health_schedule: list[float] | None = None,
) -> list[Collective]:
    """
    Create a federation of N Coasean collectives at automation level ε.

    Population, Trust balance, and capital stock are divided equally. Ecosystem
    health is shared (symmetric baseline) unless ecosystem_health_schedule is
    provided, in which case each collective gets its own health value — enabling
    the heterogeneous federations needed for meaningful exchange rates.

    N(ε) derivation
    ---------------
    If n is None, uses coasean_collective_count(epsilon). At ε=0.99, N=1 — the
    single-collective limit case that anchors the regression test.

    ε-behavior
    ----------
    ε=0.00 → 20 collectives (default N_max), each managing ~50K people
    ε=0.40 → 12 collectives
    ε=0.99 →  1 collective  — identical to single-ledger baseline

    Args:
        epsilon:                   Automation level ∈ [0, 0.99].
        n:                         Override collective count (None → use N(ε)).
        population:                Total population across all collectives.
        trust_balance:             Total Trust balance to split equally.
        capital_stock_teh:         Total capital stock to split equally.
        capital_age_ratio:         Mean asset age ratio (shared by all).
        ecosystem_health:          Ecosystem health shared by all (if no schedule).
        ecosystem_health_schedule: Per-collective ecosystem health list, length n.
                                   If provided, overrides ecosystem_health.
                                   Values are clipped to [0.01, 0.99].

    Returns:
        List of Collective objects, one per collective.
    """
    if n is None:
        n = coasean_collective_count(epsilon)

    if ecosystem_health_schedule is not None and len(ecosystem_health_schedule) != n:
        raise ValueError(
            f"ecosystem_health_schedule length {len(ecosystem_health_schedule)} != n={n}"
        )

    pop_per     = population / n
    trust_per   = trust_balance / n
    capital_per = capital_stock_teh / n

    collectives = []
    for i in range(n):
        if ecosystem_health_schedule is not None:
            eco = max(0.01, min(0.99, ecosystem_health_schedule[i]))
        else:
            eco = ecosystem_health

        pipeline, fiscal = run_collective_period(
            epsilon=epsilon,
            population=pop_per,
            trust_balance=trust_per,
            capital_stock_teh=capital_per,
            capital_age_ratio=capital_age_ratio,
            ecosystem_health=eco,
        )
        reserve = pipeline["teh_created"] * COASEAN_RESERVE_FRACTION
        collectives.append(Collective(
            collective_id=i,
            epsilon=epsilon,
            population=pop_per,
            trust_balance=trust_per,
            capital_stock=capital_per,
            ecosystem_health=eco,
            pipeline=pipeline,
            fiscal=fiscal,
            reserve=reserve,
        ))
    return collectives


def n1_regression_anchor(
    epsilon: float = 0.40,
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    ecosystem_health: float = 0.70,
) -> dict[str, Any]:
    """
    Verify that a single-collective federation exactly reproduces the reference pipeline.

    The N=1 case is the regression anchor for all federation mechanics: if the
    wrapper around eoh_to_teh_pipeline() + fiscal_snapshot() changes behavior
    for N=1, something has drifted from the reference.

    Governing identity (must hold to floating-point precision):
        make_federation(ε, n=1)[0].pipeline  ≡  eoh_to_teh_pipeline(ε, ...)
        make_federation(ε, n=1)[0].fiscal    ≡  fiscal_snapshot(ε, ...)

    ε-behavior
    ----------
    Tested at ε ∈ {0, 0.40, 0.99}. All deltas should be 0.0 (exact equality).

    Args:
        epsilon, population, trust_balance, capital_stock_teh,
        capital_age_ratio, ecosystem_health: passed identically to both the
        reference calls and make_federation(n=1).

    Returns:
        dict with keys:
          "teh_created_delta"  — |federation − reference| for teh_created
          "solvent_match"      — bool: both agree on fiscal solvency
          "surplus_delta"      — |federation − reference| for surplus_deficit
          "pipeline_match"     — bool: teh_created_delta < 1e-6
          "federation_n"       — n used (always 1)
          "ref_teh_created"    — reference teh_created value
          "fed_teh_created"    — federation teh_created value
          "ref_solvent"        — reference solvent bool
          "fed_solvent"        — federation solvent bool
    """
    ref_pipeline, ref_fiscal = run_collective_period(
        epsilon,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
    )

    fed = make_federation(
        epsilon=epsilon,
        n=1,
        population=population,
        trust_balance=trust_balance,
        capital_stock_teh=capital_stock_teh,
        capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health,
    )
    coll = fed[0]

    ref_teh    = ref_pipeline["teh_created"]
    fed_teh    = coll.pipeline["teh_created"]
    teh_delta  = abs(fed_teh - ref_teh)

    ref_surplus    = ref_fiscal["trust"]["surplus_deficit"]
    fed_surplus    = coll.fiscal["trust"]["surplus_deficit"]
    surplus_delta  = abs(fed_surplus - ref_surplus)

    return {
        "teh_created_delta": teh_delta,
        "surplus_delta":     surplus_delta,
        "solvent_match":     coll.fiscal["solvent"] == ref_fiscal["solvent"],
        "pipeline_match":    teh_delta < 1e-6,
        "federation_n":      1,
        "ref_teh_created":   ref_teh,
        "fed_teh_created":   fed_teh,
        "ref_solvent":       ref_fiscal["solvent"],
        "fed_solvent":       coll.fiscal["solvent"],
    }


# ---------------------------------------------------------------------------
# Phase 2: exchange rates, three-regime inflation, multi-period simulation
# ---------------------------------------------------------------------------

def exchange_rates(
    collectives: list[Collective],
    discovery_premium: dict[tuple[int, int], float] | None = None,
) -> dict[tuple[int, int], float]:
    """
    Pairwise exchange rates between all collectives in a federation.

    Governing equation — fundamental-parity baseline plus discovered deviation:

        r(i, j) = parity(i, j) × (1 + discovery_premium.get((i, j), 0))
        parity(i, j) = productivity(i) / productivity(j)
        productivity(c) = teh_created(c) / population(c)     [TEH per person]

    The productivity ratio is the *baseline*, not the discovered rate — the
    exchange-rate analog of the floor price (reconciliation §3): a computed
    reference the ledger can back, with discovery layered above it. The
    discovery_premium seam mirrors floor_price(market_premium=...) in
    core/prices.py. Actual discovery (preference, reserves, balance of trade)
    is not modeled here; callers supply observed or simulated deviations.

    Interpretation:
      r(i, j) > 1 → one unit of i's TEH buys more than one unit of j's
      r(i, j) = 1 → parity; no exchange advantage
      r(i, j) < 1 → j's currency is harder money

    For a symmetric federation (identical ε and ecosystem health) with no
    premiums, all rates are 1.0. Rates deviate when collectives differ in
    per-capita productivity — typically from ecosystem_health_schedule — or
    when discovery premiums are supplied.

    ε-behavior
    ----------
    ε=0.00 → N=20 collectives; many pairs; rates cluster near 1.0 in symmetric case.
    ε=0.40 → N=12; mid-arc; heterogeneous rates reflect ecosystem health spread.
    ε=0.99 → N=1; empty dict (no pairs; single-collective limit).

    Args:
        collectives: List of Collective objects from make_federation().
        discovery_premium: Optional per-pair fractional deviation from parity,
            keyed (i, j). Each value must be > −1 (a rate cannot go
            non-positive). None (default) → pure parity baseline; behavior
            identical to Phase 2.

    Returns:
        dict mapping (collective_id_i, collective_id_j) → float, for all i ≠ j.
        Empty dict if len(collectives) ≤ 1.

    Raises:
        ValueError: If any discovery premium is ≤ −1.
    """
    if len(collectives) <= 1:
        return {}

    if discovery_premium:
        for pair, prem in discovery_premium.items():
            if prem <= -1.0:
                raise ValueError(
                    f"discovery_premium for pair {pair} must be > -1, got {prem}"
                )

    per_capita: dict[int, float] = {
        c.collective_id: c.pipeline["teh_created"] / c.population
        for c in collectives
    }

    premiums = discovery_premium or {}
    rates: dict[tuple[int, int], float] = {
        (id_i, id_j): (pi / max(pj, 1e-6)) * (1.0 + premiums.get((id_i, id_j), 0.0))
        for id_i, pi in per_capita.items()
        for id_j, pj in per_capita.items()
        if id_i != id_j
    }

    return rates


def bilateral_imbalances(
    trade_flows: dict[tuple[int, int], float],
) -> dict[tuple[int, int], float]:
    """
    Net bilateral trade imbalances from gross pairwise flows.

    Governing equation, for each unordered pair {i, j} with i < j:

        B(i, j) = flow(i → j) − flow(j → i)

    Where flow(i → j) is the TEH value of goods/services collective i delivered
    to collective j this period. B(i, j) > 0 means i is the net exporter and j
    the net debtor; B < 0 the reverse; B = 0 balanced trade.

    This is the accounting layer beneath the paper's bilateral-imbalance-ceiling
    sketch (reconciliation §9-item-4): settlement discipline operates on the
    *net* position, not gross volume, so balanced high-volume trade never
    triggers settlement.

    ε-behavior: none directly — imbalances are per-period observables. The
    number of possible pairs falls with ε as N(ε) consolidates; at ε=0.99
    (N=1) there are no pairs and the dict is empty.

    Args:
        trade_flows: Gross flows keyed (exporter_id, importer_id) → TEH ≥ 0.
            Missing pairs are treated as zero flow.

    Returns:
        dict keyed (i, j) with i < j → net flow from i to j (TEH, signed).
        Pairs with zero net flow in both directions are omitted.

    Raises:
        ValueError: If any flow is negative.
    """
    for pair, flow in trade_flows.items():
        if flow < 0.0:
            raise ValueError(f"trade flow for pair {pair} must be >= 0, got {flow}")

    net: dict[tuple[int, int], float] = {}
    for (i, j), flow in trade_flows.items():
        lo, hi = (i, j) if i < j else (j, i)
        signed = flow if i < j else -flow
        net[(lo, hi)] = net.get((lo, hi), 0.0) + signed
    return {pair: b for pair, b in net.items() if b != 0.0}


def settlement_check(
    imbalance: float,
    debtor_reserve: float,
    ceiling_fraction: float = COASEAN_IMBALANCE_CEILING,
    depreciation_slope: float = COASEAN_DEPRECIATION_SLOPE,
) -> dict:
    """
    Bilateral-imbalance-ceiling settlement check for one debtor position.

    Governing equations (paper's sketch, reconciliation §9-item-4):

        ceiling            = ceiling_fraction × debtor_reserve
        within ceiling     → trade continues on credit;  status "OK"
        beyond ceiling     → status "SETTLEMENT_REQUIRED":
            settled_from_reserve = min(imbalance, debtor_reserve)
            unsettled            = imbalance − settled_from_reserve
            excess_ratio         = unsettled / max(ceiling, 1e-9)
            depreciation_factor  = 1 / (1 + depreciation_slope × excess_ratio)

    The depreciation factor (∈ (0, 1]) multiplies the debtor collective's
    exchange rate: a deficit its reserve cannot settle depreciates its unit.
    This is the mechanism that stops a collective from over-issuing and
    exporting depreciation invisibly — the deficit becomes a visible, honest
    exchange-rate movement (reconciliation §7, transition-inflation regime).
    The functional form is proposed, not calibrated (§8.5 analog).

    Worked example (reserve=1000, ceiling_fraction=0.5, slope=0.2):
        imbalance=400  → ceiling=500, within → "OK", factor=1.0
        imbalance=800  → beyond; settle 800 from reserve; unsettled=0 → factor=1.0
        imbalance=1500 → settle 1000; unsettled=500; excess=1.0 → factor≈0.833

    Args:
        imbalance: Net TEH the debtor owes on this bilateral position (≥ 0).
        debtor_reserve: The debtor collective's inter-collective reserve (≥ 0).
        ceiling_fraction: Credit ceiling as a fraction of the debtor's reserve.
            Default: COASEAN_IMBALANCE_CEILING = 0.50.
        depreciation_slope: Rate depreciation per unit of unsettled excess.
            Default: COASEAN_DEPRECIATION_SLOPE = 0.20.

    Returns:
        dict with keys: imbalance, ceiling, debtor_reserve, status
        ("OK" | "SETTLEMENT_REQUIRED"), settled_from_reserve, unsettled,
        depreciation_factor.

    Raises:
        ValueError: If imbalance or debtor_reserve is negative.
    """
    if imbalance < 0.0:
        raise ValueError(f"imbalance must be >= 0, got {imbalance}")
    if debtor_reserve < 0.0:
        raise ValueError(f"debtor_reserve must be >= 0, got {debtor_reserve}")

    ceiling = ceiling_fraction * debtor_reserve

    if imbalance <= ceiling:
        return {
            "imbalance":            imbalance,
            "ceiling":              ceiling,
            "debtor_reserve":       debtor_reserve,
            "status":               "OK",
            "settled_from_reserve": 0.0,
            "unsettled":            0.0,
            "depreciation_factor":  1.0,
        }

    settled = min(imbalance, debtor_reserve)
    unsettled = imbalance - settled
    excess_ratio = unsettled / max(ceiling, 1e-9)
    depreciation_factor = 1.0 / (1.0 + depreciation_slope * excess_ratio)

    return {
        "imbalance":            imbalance,
        "ceiling":              ceiling,
        "debtor_reserve":       debtor_reserve,
        "status":               "SETTLEMENT_REQUIRED",
        "settled_from_reserve": settled,
        "unsettled":            unsettled,
        "depreciation_factor":  depreciation_factor,
    }


def three_regime_inflation(
    rates_t0: dict[tuple[int, int], float],
    rates_t1: dict[tuple[int, int], float],
    epsilon: float,
) -> dict[str, Any]:
    """
    Three-regime inflation metrics for one period transition (reconciliation §7).

    The three regimes of the inflation theorem:

    1. Within-collective (all ε): floor-impossibility — structural.
       TEH requires verified work; the floor price basket_price(ε) is determined
       by physics. within_inflation = 0.0 by construction.

    2. Inter-collective (transition): exchange-rate movement.
       An over-issuing collective sees its unit depreciate against its neighbors.
       Measured as the maximum relative change in any pairwise exchange rate
       between two consecutive periods:
           inter_inflation = max_{(i,j)} |r_t1(i,j) − r_t0(i,j)| / r_t0(i,j)

    3. System-wide (ε→1 asymptote): recovers impossibility.
       As N(ε)→1, inter-collective exchange disappears. The system-wide metric
       weights inter-collective spread by the remaining fragmentation:
           system_inflation = inter_inflation × max(0, 1 − ε)
       At ε=0.99, N=1 and system_inflation = 0 — inflation-impossibility holds
       system-wide as the limiting case.

    Regime uncertainty note (per reconciliation §8.5 analog):
    The mapping from per-capita TEH to exchange rates is a working hypothesis.
    Real collective exchange rates depend on preference, governance, reserve
    holdings, and external balances — none fully modeled here.

    Args:
        rates_t0: Exchange rates at period start, from exchange_rates().
        rates_t1: Exchange rates at period end, from exchange_rates().
        epsilon:  Automation level at period end ∈ [0, 0.99].

    Returns:
        dict with keys:
          "within_inflation"  float — always 0.0 (structural guarantee)
          "inter_inflation"   float — max relative rate change across pairs
          "system_inflation"  float — inter × max(0, 1−ε)
          "mean_rate_change"  float — mean absolute relative rate change
          "max_rate_pair"     tuple | None — (i, j) pair with max rate change
          "regime_note"       str   — qualitative regime description
    """
    within_inflation: float = 0.0

    # N=1 (or first period): no inter-collective exchange
    if not rates_t0 or not rates_t1:
        return {
            "within_inflation": within_inflation,
            "inter_inflation":  0.0,
            "system_inflation": 0.0,
            "mean_rate_change": 0.0,
            "max_rate_pair":    None,
            "regime_note":      (
                "N=1 (single-collective limit): within-floor impossibility holds "
                "system-wide (no inter-collective exchange)"
            ),
        }

    common_pairs = set(rates_t0) & set(rates_t1)
    if not common_pairs:
        return {
            "within_inflation": within_inflation,
            "inter_inflation":  0.0,
            "system_inflation": 0.0,
            "mean_rate_change": 0.0,
            "max_rate_pair":    None,
            "regime_note":      "Federation structure changed; no comparable rate pairs",
        }

    rel_changes: dict[tuple[int, int], float] = {}
    for pair in common_pairs:
        r0 = rates_t0[pair]
        r1 = rates_t1[pair]
        rel_changes[pair] = abs(r1 - r0) / max(abs(r0), 1e-12)

    inter_inflation  = max(rel_changes.values())
    mean_rate_change = sum(rel_changes.values()) / len(rel_changes)
    max_pair         = max(rel_changes, key=lambda p: rel_changes[p])
    system_inflation = inter_inflation * max(0.0, 1.0 - epsilon)

    if epsilon >= 0.95:
        note = (
            f"Near post-scarcity (ε={epsilon:.2f}): N→1; "
            f"system_inflation={system_inflation:.4f} → 0"
        )
    elif inter_inflation < 1e-9:
        note = "Symmetric federation: exchange rates static; inter-collective inflation = 0"
    elif inter_inflation < 0.01:
        note = (
            f"Low inter-collective drift ({inter_inflation:.4f}): "
            f"exchange rates near-stable at ε={epsilon:.2f}"
        )
    else:
        note = (
            f"Inter-collective exchange-rate movement: "
            f"max drift {inter_inflation:.2%} at pair {max_pair} (ε={epsilon:.2f})"
        )

    return {
        "within_inflation": within_inflation,
        "inter_inflation":  inter_inflation,
        "system_inflation": system_inflation,
        "mean_rate_change": mean_rate_change,
        "max_rate_pair":    max_pair,
        "regime_note":      note,
    }


# ---------------------------------------------------------------------------
# Phase 4: boundary events + federation commons (reconciliation §8.7)
# ---------------------------------------------------------------------------

def merge_collectives(
    absorber: Collective,
    absorbed: Collective,
    rate: float = 1.0,
    indivisible_fraction: float = COASEAN_INDIVISIBLE_RESERVE_FRACTION,
) -> dict[str, Any]:
    """
    Merge two collectives: the absorbed dissolves into the absorber — §8.7 (c)+(d).

    Governing equations (all in absorber units; rate = r(absorbed → absorber)
    from exchange_rates(), a unit conversion, not a valuation):
        escheat      = T_b · r · f                    (indivisible reserve → commons, §8.7c)
        T_merged     = T_a + T_b · r · (1 − f)        (allocated accounts carry over, §8.7b)
        K_merged     = K_a + K_b · r ;  R_merged = R_a + R_b · r
        pop_merged   = pop_a + pop_b ;  eco = population-weighted mean

    Conservation (§8.7d — boundary events create and destroy zero TEH):
        teh_before = T_a + T_b · r  ==  T_merged + escheat  = teh_after
        exact in absorber units for ANY rate; asserted in the returned
        `conserved` flag with tolerance 1e-9 · max(1, teh_before).

    The escheat is not lost: it is circulatory, moving from the collective
    tier to the federation commons (the caller banks it — simulate_federation
    adds it to commons_t; standalone callers must route it themselves).

    The merged collective's pipeline/fiscal are recomputed via
    run_collective_period() at the merged parameters (capital_age_ratio at
    the module default 0.50 — Collective does not carry it), so the returned
    Collective is valid for further federation use.

    Worked example (T_a = T_b = 2.9B, r = 1, f = 0.30):
        escheat = 0.875B ;  T_merged = 2.917B + 2.042B = 4.958B
        teh_before = 5.833B = teh_after ✓

    Args:
        absorber: Surviving collective.
        absorbed: Dissolving collective (same ε as absorber).
        rate: Exchange rate r(absorbed → absorber) (> 0). 1.0 = symmetric.
        indivisible_fraction: Unallocated share of the absorbed trust that
            escheats (∈ [0, 1]). Default COASEAN_INDIVISIBLE_RESERVE_FRACTION.

    Returns:
        dict with keys: merged (Collective), escheat_teh, teh_before,
        teh_after, conserved (bool), rate.
    """
    if rate <= 0.0:
        raise ValueError(f"rate must be > 0, got {rate}")
    if absorber.epsilon != absorbed.epsilon:
        raise ValueError(
            f"epsilon mismatch: absorber={absorber.epsilon}, absorbed={absorbed.epsilon}"
        )
    if not 0.0 <= indivisible_fraction <= 1.0:
        raise ValueError(
            f"indivisible_fraction must be in [0, 1], got {indivisible_fraction}"
        )

    trust_b_converted = absorbed.trust_balance * rate
    escheat = trust_b_converted * indivisible_fraction
    merged_trust = absorber.trust_balance + trust_b_converted * (1.0 - indivisible_fraction)
    merged_pop = absorber.population + absorbed.population
    merged_capital = absorber.capital_stock + absorbed.capital_stock * rate
    merged_reserve = absorber.reserve + absorbed.reserve * rate
    merged_eco = (
        absorber.ecosystem_health * absorber.population
        + absorbed.ecosystem_health * absorbed.population
    ) / merged_pop

    pipeline, fiscal = run_collective_period(
        epsilon=absorber.epsilon,
        population=merged_pop,
        trust_balance=merged_trust,
        capital_stock_teh=merged_capital,
        ecosystem_health=merged_eco,
    )
    merged = Collective(
        collective_id=absorber.collective_id,
        epsilon=absorber.epsilon,
        population=merged_pop,
        trust_balance=merged_trust,
        capital_stock=merged_capital,
        ecosystem_health=merged_eco,
        pipeline=pipeline,
        fiscal=fiscal,
        reserve=merged_reserve,
    )

    teh_before = absorber.trust_balance + trust_b_converted
    teh_after = merged_trust + escheat
    conserved = abs(teh_before - teh_after) <= 1e-9 * max(1.0, teh_before)

    return {
        "merged":      merged,
        "escheat_teh": escheat,
        "teh_before":  teh_before,
        "teh_after":   teh_after,
        "conserved":   conserved,
        "rate":        rate,
    }


def split_collective(
    parent: Collective,
    fractions: list[float],
    indivisible_fraction: float = COASEAN_INDIVISIBLE_RESERVE_FRACTION,
    new_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Split a collective into successors: the parent dissolves — §8.7 (c)+(d).

    Governing equations:
        escheat     = T_parent · f                     (parent dissolves → §8.7c escheat)
        T_i         = T_parent · (1 − f) · fractions[i]
        pop_i, K_i, R_i = parent value · fractions[i]

    §8.7(d)'s "indivisible reserve dividing by the escheat rule": a split
    dissolves the parent, so its indivisible portion escheats to the commons —
    it is NOT negotiated among successors. Successors receive only the
    allocated share, pro-rata by population fractions: members carry their
    capital accounts to whichever successor they join, and `fractions` is the
    aggregate representation of that sorting (the model tracks no individual
    accounts). No exchange rate applies: all successors start in the parent's
    unit.

    Conservation (§8.7d): Σ T_i + escheat == T_parent, exact; `conserved` flag
    with tolerance 1e-9 · max(1, T_parent).

    Worked example (T = 35B, f = 0.30, fractions = [0.5, 0.5]):
        escheat = 10.5B ;  T_0 = T_1 = 12.25B ;  12.25·2 + 10.5 = 35 ✓

    Args:
        parent: Dissolving collective.
        fractions: Population shares of the successors (≥ 2 entries, each > 0,
            summing to 1 within 1e-9).
        indivisible_fraction: Escheating unallocated share (∈ [0, 1]).
        new_ids: Successor collective_ids (None → parent.collective_id, then
            sequential from it).

    Returns:
        dict with keys: successors (list[Collective]), escheat_teh,
        teh_before, teh_after, conserved (bool).
    """
    if len(fractions) < 2:
        raise ValueError(f"need at least 2 successor fractions, got {len(fractions)}")
    if any(f <= 0.0 for f in fractions):
        raise ValueError(f"all fractions must be > 0, got {fractions}")
    if abs(sum(fractions) - 1.0) > 1e-9:
        raise ValueError(f"fractions must sum to 1, got sum={sum(fractions)}")
    if not 0.0 <= indivisible_fraction <= 1.0:
        raise ValueError(
            f"indivisible_fraction must be in [0, 1], got {indivisible_fraction}"
        )
    if new_ids is not None and len(new_ids) != len(fractions):
        raise ValueError(
            f"new_ids length {len(new_ids)} != fractions length {len(fractions)}"
        )

    escheat = parent.trust_balance * indivisible_fraction
    allocated = parent.trust_balance * (1.0 - indivisible_fraction)
    ids = new_ids if new_ids is not None else [
        parent.collective_id + i for i in range(len(fractions))
    ]

    successors = []
    for i, frac in enumerate(fractions):
        pop_i = parent.population * frac
        trust_i = allocated * frac
        capital_i = parent.capital_stock * frac
        pipeline, fiscal = run_collective_period(
            epsilon=parent.epsilon,
            population=pop_i,
            trust_balance=trust_i,
            capital_stock_teh=capital_i,
            ecosystem_health=parent.ecosystem_health,
        )
        successors.append(Collective(
            collective_id=ids[i],
            epsilon=parent.epsilon,
            population=pop_i,
            trust_balance=trust_i,
            capital_stock=capital_i,
            ecosystem_health=parent.ecosystem_health,
            pipeline=pipeline,
            fiscal=fiscal,
            reserve=parent.reserve * frac,
        ))

    teh_after = sum(s.trust_balance for s in successors) + escheat
    conserved = abs(parent.trust_balance - teh_after) <= 1e-9 * max(1.0, parent.trust_balance)

    return {
        "successors":  successors,
        "escheat_teh": escheat,
        "teh_before":  parent.trust_balance,
        "teh_after":   teh_after,
        "conserved":   conserved,
    }


def _consolidation_escheat(
    trust_total: float,
    n_prev: int,
    n_new: int,
    indivisible_fraction: float = COASEAN_INDIVISIBLE_RESERVE_FRACTION,
) -> float:
    """
    Aggregate escheat when the federation's N(ε) changes between periods.

    Governing equation (first-order rule):
        escheat = |n_prev − n_new| · (trust_total / n_prev) · f

    On consolidation (n_new < n_prev) this is provably identical to
    d = n_prev − n_new sequential merge_collectives(rate=1) calls on the
    equal-split federation: each dissolving collective holds trust_total/n_prev
    and escheats f of it (asserted in tests). On fragmentation (n_new > n_prev,
    ε decreasing) the symmetric rule treats each net-new collective as one
    parent split, escheating f of one equal share per split — first-order only:
    it undercounts compounded splits when d > n_prev. Canonical trajectories
    are monotone-increasing in ε, so fragmentation is a corner case.

    Capped at trust_total · f (cannot escheat more than the total indivisible
    share).

    Args:
        trust_total: Sum of all collective trusts before the transition (≥ 0).
        n_prev: Collective count last period (≥ 1).
        n_new: Collective count this period (≥ 1).
        indivisible_fraction: Escheating unallocated share (∈ [0, 1]).

    Returns:
        Escheat in TEH (≥ 0); 0.0 when n_new == n_prev.
    """
    d = abs(n_prev - n_new)
    if d == 0:
        return 0.0
    raw = d * (trust_total / n_prev) * indivisible_fraction
    return min(raw, trust_total * indivisible_fraction)


def simulate_federation(
    epsilon_trajectory: list[float],
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    heterogeneity: float = 0.10,
    baseline_ecosystem_health: float = 0.70,
    seed: int = 42,
    dynamics: bool = False,
    g_priv: float = 0.0,
    levy_rate: float = 0.0,
    commons: bool = False,
    commons_tithe: float = COASEAN_COMMONS_TITHE,
    commons_start: float = 0.0,
    regime: str = "increasing_returns",
    commons_dividend: bool = False,
) -> list[dict[str, Any]]:
    """
    Multi-period Coasean federation simulation across an ε trajectory.

    At each period, constructs a federation at the given ε with N(ε) collectives.
    When heterogeneity > 0, each collective receives a distinct ecosystem health
    drawn from Normal(0.70, heterogeneity²), creating productivity variation and
    thus non-trivial exchange rates.

    Three-regime inflation theorem verification
    -------------------------------------------
    The simulation directly tests reconciliation §7 across the arc:
    - within_inflation = 0 at every period (structural)
    - inter_inflation > 0 during transition (when N > 1 and heterogeneity > 0)
    - system_inflation → 0 as ε → 0.99 (N → 1)

    Phase 3: Trust/capital dynamics (dynamics=True)
    -----------------------------------------------
    With dynamics enabled, the Trust and private capital evolve per period:

        automated_output_t = ε_t · K_t · CONTESTABILITY_CAPITAL_YIELD_RATE
        levy_revenue_t     = levy_rate · automated_output_t
        dividend_outflow_t = T_t · DEP_RATE · DIV_RATE
        T_{t+1}            = T_t + levy_revenue_t − dividend_outflow_t
        K_{t+1}            = K_t · (1 + g_priv)

    τ_t = T_t / K_t is tracked per period and the Piketty-inversion condition
    (reconciliation §8.3) is checked: dτ ≥ 0 ⟺ g_Trust ≥ g_priv. Between
    periods with rising ε the check reuses tau_gradient_check() from
    research/contestability.py; for flat/repeated ε it falls back to the raw
    per-period τ difference (the condition is the same; only the denominator
    differs). This makes the central §8.3 growth condition *testable*: a levy
    too small to outpace g_priv and the dividend outflow shows piketty_ok
    flipping False.

    With dynamics=False (default), Trust and capital are held constant and
    every record matches the Phase 2 output exactly — the regression anchor
    for existing callers.

    Phase 4: two-tier Trust / federation commons (commons=True) — recon. §8.7
    -------------------------------------------------------------------------
    With the commons tier enabled, three mechanisms activate:

    1. Escheat on N-transition (§8.7c): when N(ε) changes between periods,
       the indivisible share of each net-dissolving collective's trust
       escheats to the federation commons via _consolidation_escheat():
           escheat = |Δn| · (T / n_prev) · COASEAN_INDIVISIBLE_RESERVE_FRACTION
       Escheat is circulatory — trust_balance + commons_balance is conserved
       by the transition (no TEH created or destroyed, §8.7d).
    2. Levy tithe (§8.7a; requires dynamics=True): a fraction commons_tithe
       of each period's levy revenue routes to the commons instead of the
       collective trusts (Italian Law 59/1992 3% precedent):
           tithe_paid = commons_tithe · levy_revenue
           T_{t+1}    = T_t + levy_revenue − tithe_paid − dividend_outflow
           C_{t+1}    = C_t + tithe_paid + escheat_{t+1}
    3. Per-collective χ (§8.1 at the collective level): each period computes
       contestability_margin_federated() per collective and records the
       federation's worst case — chi_min (population-average) and
       chi_marginal_min (tenure-0 member, the person the invariant protects).

    The commons is a BACKSTOP for the sufficiency floor, not the payer — each
    collective's fiscal snapshot already charges the guarantee, so an explicit
    commons payout would double-count the floor. commons_floor_coverage
    reports the reinsurance ratio C / (S(ε) · population): years of
    federation-wide floor the commons could carry. HONEST FINDINGS to expect
    at defaults: coverage is tiny at a 3% tithe, and consolidation escheat
    migrates trust from collective dividends to the commons across the arc,
    so chi_marginal_min worsens while total τ holds. Report, don't tune
    (CLAUDE.md §5).

    Phase 4b: contestability closure (commons_dividend=True) — proposed §8.8
    -------------------------------------------------------------------------
    Answers the Phase 4 adversarial findings with two mechanisms:

    M1 — universal commons dividend: the commons pays its yield per capita to
    every member, UNVESTED (Alaska Permanent Fund precedent):
        D_fed_t = C_t · DEP_RATE · DIV_RATE / population   (per person)
        C_{t+1} = C_t + tithe + escheat − C_t·DEP_RATE·DIV_RATE
    Per-collective χ is computed with commons_balance=C_t, so escheat now
    RAISES the marginal member's endowment instead of draining it — the
    §8.7c escheat becomes a stabilizer: consolidation moves capital from
    tenure-gated collective dividends into the universal tier.

    M2 — entry-underwriting capacity (always reported when commons=True,
    since it is a property of the commons stock, not of dividend policy):
        entry_capacity_t = UNDERWRITE_FRACTION · C_t
                           / (MIN_VIABLE_POPULATION · K_entry(ε_t))
        exit_financeable_t ⇔ chi_marginal_min ≥ 1 OR entry_capacity ≥ 1
    The Baumol threat made credible: the commons can capitalize new
    collectives' trusts (capital stays commonized — §8.7c is respected).
    Seed the commons via commons_start ≥ commons_seed_required() (≈1.8e7 TEH
    at defaults, ~0.05% of TRUST_BASE_TEH) to close the ε≈0 window before
    escheat inflows begin.

    With commons_dividend=False every χ value and balance is float-exact
    identical to Phase 4 (commons_balance=0 is passed to the χ computation
    and no dividend outflow occurs); the M2 metrics are additional keys only.

    τ under the commons: tau = (T + C) / K — §8.3's Piketty condition
    concerns TOTAL commonized capital vs private; excluding the commons would
    make escheat (a pure intra-commons transfer) spuriously flip piketty_ok.
    With commons=False, C ≡ 0.0 and every value is float-exact identical to
    the Phase 3 output.

    N=1 asymptote (regression check)
    ---------------------------------
    At ε = 0.99, N = 1 → exchange_rates() returns {} → three_regime_inflation()
    returns system_inflation = 0 and regime_note indicates single-collective limit.

    Args:
        epsilon_trajectory: ε value for each period. Typically increasing.
        population:         Total population (fixed across all periods).
        trust_balance:      Trust balance at period 0 (constant when
                            dynamics=False; evolves per the equations above
                            when dynamics=True).
        capital_stock_teh:  Capital stock at period 0 (constant or evolving,
                            same rule).
        capital_age_ratio:  Mean asset age ratio (fixed).
        heterogeneity:      Std dev of Normal distribution for ecosystem health
                            variation across collectives. 0 = fully symmetric
                            (all exchange rates = 1.0).
        seed:               Random seed for reproducible heterogeneity schedules.
        dynamics:           Enable Trust/capital evolution. Default False
                            (Phase 2 behavior, byte-identical).
        g_priv:             Per-period private capital growth rate. Used only
                            when dynamics=True.
        levy_rate:          Common-fund levy as a fraction of automated output,
                            feeding the Trust. Used only when dynamics=True.
        commons:            Enable the Phase 4 two-tier commons machinery
                            (escheat, tithe, per-collective χ). Default False
                            (Phase 3 behavior, float-exact identical).
        commons_tithe:      Fraction of levy revenue routed to the commons.
                            Default COASEAN_COMMONS_TITHE (0.03). Used only
                            when commons=True and dynamics=True.
        commons_start:      Initial commons balance in TEH. Default 0.0.
        regime:             K_entry regime for per-collective χ:
                            "increasing_returns" (default/adversarial) or
                            "replicable". Used only when commons=True.
        commons_dividend:   Enable the Phase 4b closure (M1 universal commons
                            dividend feeding χ; dividend outflow from C under
                            dynamics). Default False (Phase 4 float-exact).

    Returns:
        List of period dicts, one per element of epsilon_trajectory. Each dict:
          "period"            int   — 0-indexed period number
          "epsilon"           float — automation level this period
          "n_collectives"     int   — N(ε)
          "total_teh"         float — sum of teh_created across all collectives
          "mean_teh_per_cap"  float — total_teh / population
          "all_solvent"       bool  — True if every collective is fiscally solvent
          "within_inflation"  float — always 0.0 (structural)
          "inter_inflation"   float — max relative exchange-rate drift this period
          "system_inflation"  float — inter × max(0, 1−ε)
          "n_exchange_pairs"  int   — number of pairwise rates (N×(N−1))
          "regime_note"       str   — qualitative regime description
          "trust_balance"     float — Trust at this period (constant unless dynamics)
          "capital_stock"     float — capital at this period (constant unless dynamics)
          "tau"               float — (T + commons)/K this period
          "dtau"              float | None — τ change vs previous period (None at period 0)
          "piketty_ok"        bool | None — dτ ≥ 0 (None at period 0)
        Phase 4 keys (always present; neutral when commons=False):
          "commons_balance"        float — commons at period start, post-escheat
          "commons_tithe_paid"     float — tithe routed this period (0.0 unless
                                           commons and dynamics)
          "escheat_this_period"    float — indivisible-reserve escheat at this
                                           period's N-transition (0.0 if none)
          "commons_floor_coverage" float | None — commons / (S(ε)·population),
                                           years of floor the commons could carry
          "chi_min"                float | None — min over collectives of the
                                           two-tier population-average χ
          "chi_marginal_min"       float | None — min over collectives of the
                                           tenure-0 χ (the invariant's honest bound)
          "chi_worst_collective"   int | None — collective_id at chi_marginal_min
          "chi_status_worst"       str | None — "OK"/"WARN"/"CRIT" at chi_marginal_min
        Phase 4b keys (always present; neutral when commons=False):
          "commons_dividend_paid"  float — universal dividend outflow this
                                           period (0.0 unless commons_dividend
                                           and dynamics)
          "entry_capacity"         float | None — commons entry-underwriting
                                           capacity (viable foundings financeable)
          "exit_financeable"       bool | None — chi_marginal_min ≥ 1 OR
                                           entry_capacity ≥ 1 (proposed §8.8
                                           combined invariant)
    """
    rng = _random.Random(seed)
    records: list[dict[str, Any]] = []
    prev_rates: dict[tuple[int, int], float] = {}

    trust_t = trust_balance
    capital_t = capital_stock_teh
    commons_t = commons_start if commons else 0.0
    prev_tau: float | None = None
    prev_eps: float | None = None
    prev_n: int | None = None

    for period, epsilon in enumerate(epsilon_trajectory):
        n = coasean_collective_count(epsilon)

        # §8.7c: N-transition escheat — the net-dissolving collectives'
        # indivisible reserves move to the commons before the re-pool.
        escheat = 0.0
        if commons and prev_n is not None and n != prev_n:
            escheat = _consolidation_escheat(trust_t, prev_n, n)
            trust_t -= escheat
            commons_t += escheat

        # Per-collective ecosystem health: Normal(baseline, heterogeneity²), clipped
        eco_schedule: list[float] | None = None
        if heterogeneity > 0.0:
            eco_schedule = [
                max(0.01, min(0.99, baseline_ecosystem_health + rng.gauss(0.0, heterogeneity)))
                for _ in range(n)
            ]

        collectives = make_federation(
            epsilon=epsilon,
            n=n,
            population=population,
            trust_balance=trust_t,
            capital_stock_teh=capital_t,
            capital_age_ratio=capital_age_ratio,
            ecosystem_health=baseline_ecosystem_health,
            ecosystem_health_schedule=eco_schedule,
        )

        curr_rates = exchange_rates(collectives)
        inflation  = three_regime_inflation(prev_rates, curr_rates, epsilon)
        total_teh, all_solvent = 0.0, True
        for c in collectives:
            total_teh  += c.pipeline["teh_created"]
            all_solvent = all_solvent and c.fiscal["solvent"]

        # §8.7: per-collective χ under the two-tier P — worst case is the
        # federation's contestability position (the invariant is only as
        # strong as its weakest collective's marginal member).
        chi_min: float | None = None
        chi_marginal_min: float | None = None
        chi_worst_collective: int | None = None
        chi_status_worst: str | None = None
        commons_floor_coverage: float | None = None
        entry_capacity: float | None = None
        exit_financeable: bool | None = None
        if commons:
            # Phase 4b (M1): χ sees the commons only under the dividend
            # policy — commons_balance=0.0 keeps Phase 4 float-exact.
            chi_commons = commons_t if commons_dividend else 0.0
            margins = [
                contestability_margin_federated(
                    epsilon,
                    collective_trust=c.trust_balance,
                    collective_population=c.population,
                    federation_population=population,
                    regime=regime,
                    commons_balance=chi_commons,
                )
                for c in collectives
            ]
            chi_min = min(m["chi"] for m in margins)
            worst_idx = min(range(len(margins)), key=lambda i: margins[i]["chi_marginal"])
            chi_marginal_min = margins[worst_idx]["chi_marginal"]
            chi_worst_collective = collectives[worst_idx].collective_id
            chi_status_worst = margins[worst_idx]["status_marginal"]
            # Reinsurance ratio: years of federation-wide floor the commons
            # could carry. S is ε-only, identical across collectives.
            floor_liability = margins[0]["guarantee_per_person"] * population
            commons_floor_coverage = commons_t / max(floor_liability, 1e-9)
            # Phase 4b (M2): entry capacity is a property of the commons
            # stock itself, reported regardless of dividend policy.
            underwriting = entry_underwriting(epsilon, commons_t, regime)
            entry_capacity = underwriting["entry_capacity"]
            exit_financeable = chi_marginal_min >= 1.0 or underwriting["passes"]

        # Piketty-inversion tracking (§8.3): dτ ≥ 0 ⟺ g_Trust ≥ g_priv.
        # τ counts TOTAL commonized capital — both tiers (see docstring);
        # commons_t ≡ 0.0 when commons=False keeps Phase 3 float-exact.
        tau = (trust_t + commons_t) / max(capital_t, 1e-9)
        dtau: float | None = None
        piketty_ok: bool | None = None
        if prev_tau is not None and prev_eps is not None:
            if epsilon > prev_eps:
                # tau_gradient_check computes τ = trust/cap internally; passing
                # the τ values with cap=1 reuses its dτ/dε logic directly.
                grad = tau_gradient_check(
                    prev_eps, epsilon,
                    trust_lo=prev_tau, trust_hi=tau,
                    cap_lo=1.0, cap_hi=1.0,
                )
                dtau = grad["dtau_deps"]
                piketty_ok = grad["passes"]
            else:
                dtau = tau - prev_tau  # flat ε: raw per-period τ difference
                piketty_ok = dtau >= -1e-12

        # Dynamics arithmetic hoisted above the append so the tithe is
        # reportable in the same period's record. Expressions preserved
        # verbatim from Phase 3; tithe_paid ≡ 0.0 when commons=False, and
        # (T + levy) − 0.0 − dividend is IEEE-identical to (T + levy) − dividend.
        tithe_paid = 0.0
        commons_dividend_paid = 0.0
        if dynamics:
            automated_output = (
                epsilon * capital_t * CONTESTABILITY_CAPITAL_YIELD_RATE
            )
            levy_revenue = levy_rate * automated_output
            if commons:
                tithe_paid = commons_tithe * levy_revenue
                if commons_dividend:
                    # M1: the commons pays its yield universally, same
                    # outflow rule as collective trust dividends.
                    commons_dividend_paid = commons_t * DEP_RATE * DIV_RATE
            dividend_outflow = trust_t * DEP_RATE * DIV_RATE

        records.append({
            "period":           period,
            "epsilon":          epsilon,
            "n_collectives":    n,
            "total_teh":        total_teh,
            "mean_teh_per_cap": total_teh / max(population, 1.0),
            "all_solvent":      all_solvent,
            "within_inflation": inflation["within_inflation"],
            "inter_inflation":  inflation["inter_inflation"],
            "system_inflation": inflation["system_inflation"],
            "n_exchange_pairs": len(curr_rates),
            "regime_note":      inflation["regime_note"],
            "trust_balance":    trust_t,
            "capital_stock":    capital_t,
            "tau":              tau,
            "dtau":             dtau,
            "piketty_ok":       piketty_ok,
            "commons_balance":        commons_t,
            "commons_tithe_paid":     tithe_paid,
            "escheat_this_period":    escheat,
            "commons_floor_coverage": commons_floor_coverage,
            "chi_min":                chi_min,
            "chi_marginal_min":       chi_marginal_min,
            "chi_worst_collective":   chi_worst_collective,
            "chi_status_worst":       chi_status_worst,
            "commons_dividend_paid":  commons_dividend_paid,
            "entry_capacity":         entry_capacity,
            "exit_financeable":       exit_financeable,
        })

        prev_rates = curr_rates
        prev_tau = tau
        prev_eps = epsilon
        prev_n = n

        if dynamics:
            trust_t = max(0.0, trust_t + levy_revenue - tithe_paid - dividend_outflow)
            commons_t = max(0.0, commons_t + tithe_paid - commons_dividend_paid)
            capital_t = capital_t * (1.0 + g_priv)

    return records
