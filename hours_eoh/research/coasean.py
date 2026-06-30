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

Phase 2 (this file adds)
    exchange_rates(), three_regime_inflation(), simulate_federation().
    make_federation() extended with ecosystem_health_schedule for heterogeneity.
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
)
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot


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

def exchange_rates(collectives: list[Collective]) -> dict[tuple[int, int], float]:
    """
    Pairwise exchange rates between all collectives in a federation.

    Exchange rate r(i, j) — the number of units of collective j's TEH that one
    unit of collective i's TEH buys when the two collectives trade:

        r(i, j) = productivity(i) / productivity(j)
        productivity(c) = teh_created(c) / population(c)     [TEH per person]

    Interpretation:
      r(i, j) > 1 → collective i is more productive; i's currency is harder money
      r(i, j) = 1 → symmetric collectives; no exchange advantage
      r(i, j) < 1 → collective j is more productive; j's currency is harder money

    For a symmetric federation (identical ε and ecosystem health), all rates are 1.0.
    Rates deviate from 1.0 only when collectives differ in per-capita productivity —
    typically from different ecosystem health values passed via ecosystem_health_schedule.

    This formula models "backing" — how much verified TEH underpins each population
    member — rather than preference. It is a working hypothesis; real inter-collective
    rates would also depend on reserves, governance, and balance of trade.

    ε-behavior
    ----------
    ε=0.00 → N=20 collectives; many pairs; rates cluster near 1.0 in symmetric case.
    ε=0.40 → N=12; mid-arc; heterogeneous rates reflect ecosystem health spread.
    ε=0.99 → N=1; empty dict (no pairs; single-collective limit).

    Args:
        collectives: List of Collective objects from make_federation().

    Returns:
        dict mapping (collective_id_i, collective_id_j) → float, for all i ≠ j.
        Empty dict if len(collectives) ≤ 1.
    """
    if len(collectives) <= 1:
        return {}

    per_capita: dict[int, float] = {
        c.collective_id: c.pipeline["teh_created"] / c.population
        for c in collectives
    }

    rates: dict[tuple[int, int], float] = {
        (id_i, id_j): pi / max(pj, 1e-6)
        for id_i, pi in per_capita.items()
        for id_j, pj in per_capita.items()
        if id_i != id_j
    }

    return rates


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


def simulate_federation(
    epsilon_trajectory: list[float],
    population: float = 1_000_000.0,
    trust_balance: float = TRUST_BASE_TEH,
    capital_stock_teh: float = CAPITAL_STOCK_DEFAULT,
    capital_age_ratio: float = 0.50,
    heterogeneity: float = 0.10,
    baseline_ecosystem_health: float = 0.70,
    seed: int = 42,
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

    N=1 asymptote (regression check)
    ---------------------------------
    At ε = 0.99, N = 1 → exchange_rates() returns {} → three_regime_inflation()
    returns system_inflation = 0 and regime_note indicates single-collective limit.

    Args:
        epsilon_trajectory: ε value for each period. Typically increasing.
        population:         Total population (fixed across all periods).
        trust_balance:      Trust balance per period (held constant; period-to-period
                            Trust dynamics are a Phase 3 concern).
        capital_stock_teh:  Total capital stock (fixed).
        capital_age_ratio:  Mean asset age ratio (fixed).
        heterogeneity:      Std dev of Normal distribution for ecosystem health
                            variation across collectives. 0 = fully symmetric
                            (all exchange rates = 1.0).
        seed:               Random seed for reproducible heterogeneity schedules.

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
    """
    rng = _random.Random(seed)
    records: list[dict[str, Any]] = []
    prev_rates: dict[tuple[int, int], float] = {}

    for period, epsilon in enumerate(epsilon_trajectory):
        n = coasean_collective_count(epsilon)

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
            trust_balance=trust_balance,
            capital_stock_teh=capital_stock_teh,
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
        })

        prev_rates = curr_rates

    return records
