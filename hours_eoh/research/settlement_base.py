"""
WHICH QUANTITY BACKS A TEH AT THE COLLECTIVE BOUNDARY? — reporting only.

SPDX-License-Identifier: AGPL-3.0-or-later

THE RULE THIS MEASURES AGAINST
------------------------------
CLAUDE.md §5 (author decision, 2026-09-12): *"Do not settle at a DISCOVERED rate
at the federation level. Settle on the BASE."* Cross-collective exchange must
clear against the obligation-anchored floor, and the failure it forbids is named:
**"a base EOH here is your entire collective there"** — a collective whose unit
has appreciated acquiring another's whole productive base for a marginal quantity
of its own.

`research/exchange.parity_rate` is mint-per-capita over mint-per-capita with no
real-output term. `research/register_federation` measured the consequence: a
captured register APPRECIATES 1.2724× at ε=0.40. So the rule constrains work that
already exists, and the open question is not WHETHER to settle on the base but
**WHICH QUANTITY THE BASE IS**. The rule names the property — obligation-anchored,
population-bounded — and not the equation. Choosing the equation was a theory
commitment (§3 author sign-off), so this module did not choose: it evaluates the
candidates side by side and reports what each does. **DECIDED 2026-09-30
(author): REGISTERED settles (`exchange.registered_rate`), the FLOOR is reported
beside it as purchasing power.** This module is the comparison behind that
decision and stays reporting-only.

THE CANDIDATES — what one TEH of collective c is taken to be worth
------------------------------------------------------------------
Each candidate is a per-collective BACKING, b(c), in some physical unit per TEH;
the settlement rate is b(a)/b(b), in TEH_b per TEH_a.

    parity      b = teh_created / population      — the CURRENT form; the
                                                    baseline, not a candidate
    obligation  b = total_eoh / teh_created       — gross obligation per TEH
    human       b = human_eoh / teh_created       — human-served obligation per TEH
    registered  b = registered_eoh / teh_created  — = 1/mean_multiplier
    floor       b = 1 / floor_price(ε)            — sufficiency baskets per TEH,
                                                    at the SUPPLIED capability ε
    floor_observed
                b = 1 / floor_price(ε_obs)        — the same at the OBSERVED ε,
                                                    machine_eoh / total_eoh
    obligation_parity
                b = total_eoh / population        — obligation per PERSON; parity
                                                    with the mint replaced by the
                                                    obligation. NOT a per-TEH backing

`parity`'s backing is not per-TEH at all, which is the defect in one line: it
prices a unit by how MANY units were minted per person.

TWO CANDIDATES PASS THE CAPTURE TEST BY CONSTRUCTION, AND THAT IS REPORTED
--------------------------------------------------------------------------
`registered` is 1/m: every collective built at the shipped multiplier settles at
exactly 1.0 whatever else differs, so capture-neutrality there is an identity
(CLAUDE.md failure mode 2). It becomes informative only when the collectives'
multipliers DIFFER, and that case is run. `floor` reads ε and nothing else about
the collective — no mint, no population, no capital — so it cannot respond to
capture or to capital by construction; its only information is the automation
level. Both are carried because the author may want exactly that property; they
are flagged `by_construction` so a pass is not read as evidence.

THE FORK THE AUTHOR HAS TO SETTLE
---------------------------------
`obligation` and `human` differ on ONE question: **does machine-fulfilled
obligation back a TEH?** At high ε, a collective with 4× the capital settles
above par under `obligation` and below it under `human` (pinned in
`tests/test_settlement_base.py::TestTheFork`). That is not a calibration difference and it is not reported as one.

WHAT THIS DOES NOT ESTABLISH
----------------------------
No actor, incentive or trade is modelled. There is no goods layer, so what a
settled TEH buys on the far side is not represented (record/theory.md,
capture-aggregate-bounded). Canonical-arc collectives take capital, age and
health from `canonical_physical_state`; knowledge and monitoring state are left
at the pipeline's own defaults.

STATUS: experimental, reporting only. Nothing imports this. The base has been
chosen (2026-09-30); `parity_rate` is kept unchanged as the superseded form, so
`tests/test_register_federation.py`'s capture tests remain true statements about
`parity_rate` and are no longer statements about how the federation settles.

Layer note: imports from `core/`, `data.py` and `research/exchange.py` only.
"""

from __future__ import annotations

import math
from itertools import permutations
from typing import Any, Callable

from hours_eoh.data import (
    ARC_REPORTING_POINTS,
    COASEAN_IMBALANCE_CEILING,
    LAND_HECTARES_PER_CAPITA,
    M_BAND_HIGH,
    M_BAND_LOW,
    REFERENCE_FRAME_POPULATION,
)
from hours_eoh.core.conditions import condition_ii_check
from hours_eoh.core.multipliers import population_weighted_mean_multiplier
from hours_eoh.core.prices import floor_price
from hours_eoh.core.registration import personal_eoh_registration_share
from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.reference.workforce import WORKFORCE_SNAPSHOTS
from hours_eoh.research.exchange import (
    Collective,
    CollectiveFrame,
    FederationBook,
    build_collective,
)

__all__ = [
    "BAND_RATE_BOUNDS",
    "registered_settlement",
    "composition_pairing",
    "floor_epsilon_seam",
    "purchasing_gain",
    "settled_rate_matrix",
    "book_exercise",
    "focus_report",
    "BASES",
    "BY_CONSTRUCTION",
    "SEARCH_POINTS",
    "backing",
    "settlement_rate",
    "capture_response",
    "multiplier_response",
    "acquisition",
    "arc_pairing",
    "spread_decomposition",
    "frame_check",
    "base_report",
]

#: Grid for extrema over ε-pairs, distinct from the reporting points (failure
#: mode 3: an extremum needs its own grid). Numerics only; bound to the arc
#: ceiling of `ARC_REPORTING_POINTS` so the two cannot drift apart. Same
#: construction as `scenarios/verification_cost.PEAK_SEARCH_POINTS`, not
#: imported because `research/` does not import `scenarios/`.
SEARCH_POINTS: tuple[float, ...] = tuple(
    max(ARC_REPORTING_POINTS) * i / 100 for i in range(101)
)


#: Float noise, not a tolerance on any quantity: `registered` is
#: registered_eoh/teh_created, which equals 1/m only to rounding, so an exact
#: `== 1.0` would call the identity "rewarded" by one ulp. Numerics only; it
#: selects no result above rounding.
_NEUTRAL_ULPS: int = 4


def _verdict(r: float) -> str:
    if abs(r - 1.0) <= _NEUTRAL_ULPS * math.ulp(1.0):
        return "neutral"
    return "rewarded" if r > 1.0 else "disciplined"


def _parity(c: Collective) -> float:
    return c.teh_per_capita


def _obligation(c: Collective) -> float:
    return float(c.pipeline["total_eoh"]) / c.teh_created


def _human(c: Collective) -> float:
    return float(c.pipeline["human_eoh"]) / c.teh_created


def _registered(c: Collective) -> float:
    return float(c.pipeline["registered_eoh"]) / c.teh_created


def _floor(c: Collective) -> float:
    return 1.0 / floor_price(c.epsilon)


def _floor_observed(c: Collective) -> float:
    return 1.0 / floor_price(float(c.pipeline["epsilon_observable"]))


def _obligation_parity(c: Collective) -> float:
    return float(c.pipeline["total_eoh"]) / c.frame.population


#: name → (backing function, what one TEH is taken to be worth).
BASES: dict[str, tuple[Callable[[Collective], float], str]] = {
    "parity":     (_parity,     "TEH minted per person — the CURRENT form, not a base"),
    "obligation": (_obligation, "EOH of gross obligation per TEH"),
    "human":      (_human,      "EOH of human-served obligation per TEH"),
    "registered": (_registered, "EOH admitted to the register per TEH (= 1/m)"),
    "floor":      (_floor,      "sufficiency baskets per TEH at the floor price"),
    "floor_observed": (
        _floor_observed,
        "sufficiency baskets per TEH at the floor price of the OBSERVED ε",
    ),
    "obligation_parity": (
        _obligation_parity,
        "EOH of obligation per PERSON — §5 read literally; not a per-TEH backing",
    ),
}

#: Candidates whose response to some input is fixed by their definition rather
#: than measured, with what they cannot see. A pass on one of these is not
#: evidence (failure mode 2).
BY_CONSTRUCTION: dict[str, str] = {
    "registered": "equals m_b/m_a; 1.0 for any two collectives at the same multiplier",
    "floor": "reads the SUPPLIED ε only; blind to mint, population, capital and land",
    "floor_observed": (
        "reads the observed machine share only; capture-neutral STRUCTURALLY, "
        "since registration moves neither machine nor total EOH"
    ),
    "obligation_parity": (
        "capture-neutral STRUCTURALLY, not by blindness: total_eoh accepts no "
        "registration parameter (tests/test_registration_containment.py), so no "
        "register decision can reach it — but it does see capital and age"
    ),
}


def backing(c: Collective, base: str) -> float:
    """What one TEH of `c` is worth under `base` (units per `BASES[base][1]`)."""
    if base not in BASES:
        raise ValueError(f"unknown base {base!r}; expected one of {sorted(BASES)}")
    return BASES[base][0](c)


def settlement_rate(a: Collective, b: Collective, base: str) -> float:
    """
    TEH_b per TEH_a when one TEH of each is taken to be worth its backing.

        r(a, b) = backing(a) / backing(b)

    Reciprocal by construction (r(a,b)·r(b,a) = 1) and 1.0 for a collective
    against itself. Under `parity` this is exactly `exchange.parity_rate(a, b)`.
    """
    return backing(a, base) / backing(b, base)


def _reference_frame(collective_id: int, population: float = REFERENCE_FRAME_POPULATION,
                     hectares_per_capita: float = LAND_HECTARES_PER_CAPITA,
                     capital_per_capita: float | None = None) -> CollectiveFrame:
    """The 1M reference frame with the ε=0.40 canonical capital intensity."""
    if capital_per_capita is None:
        capital_per_capita = (
            canonical_physical_state(0.40)["capital_stock_teh"] / REFERENCE_FRAME_POPULATION
        )
    return CollectiveFrame(
        collective_id=collective_id,
        population=population,
        land_hectares=population * hectares_per_capita,
        capital_stock_teh=population * capital_per_capita,
    )


# ---------------------------------------------------------------------------
# Capture — the failure `register_federation` measured on parity
# ---------------------------------------------------------------------------

def capture_response(share_delta: float = 0.05, epsilon: float = 0.40) -> dict[str, Any]:
    """
    Each base's rate for a capturing collective against an identical honest one.

    The two differ ONLY in the personal registration share (asserted: the
    obligation is identical). Above 1.0 the capture is REWARDED, below 1.0 it
    is DISCIPLINED, exactly 1.0 it is NEUTRAL.

    ε-behaviour: parity's reward is largest at subsistence, where the register
    is nearly empty and a 5pp admission multiplies the mint; the per-TEH bases
    mirror it, depreciating the capturer by exactly the mint ratio.
    """
    honest = build_collective(_reference_frame(0), epsilon)
    captured = build_collective(
        _reference_frame(1),
        epsilon,
        personal_registration_share=personal_eoh_registration_share(epsilon) + share_delta,
    )
    rates = {b: settlement_rate(captured, honest, b) for b in BASES}
    return {
        "epsilon": epsilon,
        "share_delta": share_delta,
        "obligation_identical": (
            float(honest.pipeline["total_eoh"]) == float(captured.pipeline["total_eoh"])
        ),
        "mint_ratio": captured.teh_created / honest.teh_created,
        "rates": rates,
        "verdict": {b: _verdict(r) for b, r in rates.items()},
        "by_construction": dict(BY_CONSTRUCTION),
        "reporting_only": True,
    }


def multiplier_response(
    multiplier_ratio: float = 1.10,
    epsilon: float = 0.40,
) -> dict[str, Any]:
    """
    Two collectives identical except that one mints at a higher multiplier.

    The only configuration in which `registered` says anything: it settles at
    exactly 1/multiplier_ratio. Every other per-TEH base depreciates the
    high-multiplier unit by the same factor; `parity` appreciates it. A
    multiplier set above the shipped one is capture of the RATE rather than
    the register — the same defect one parameter over.
    """
    base = build_collective(_reference_frame(0), epsilon)
    m = float(base.pipeline["mean_multiplier"])
    high = build_collective(_reference_frame(1), epsilon, mean_multiplier=m * multiplier_ratio)
    return {
        "epsilon": epsilon,
        "multiplier_ratio": multiplier_ratio,
        "rates": {b: settlement_rate(high, base, b) for b in BASES},
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# The failure the rule names — a base EOH here is your entire collective there
# ---------------------------------------------------------------------------

def acquisition(a: Collective, b: Collective, base: str) -> dict[str, float]:
    """
    What it costs `a` to acquire all of `b`, settled on `base`.

        cost_a = K_b / r(a, b)                 [TEH_a]
        years  = cost_a / teh_created(a)       [years of a's own mint]

    and the same for b's whole annual mint. `years` is the quantity the §5
    failure is stated in — "a MARGINAL quantity of its own" is a small `years`.

    NOTE, found while building this: the obvious normalisation — `a`'s cost at
    r = 1 over its cost at r — is IDENTICALLY r, because K_b and teh_created(a)
    cancel. It was dropped rather than reported, since a "discount" column
    equal to the rate column reads as a second, independent test and is not
    one (CLAUDE.md failure mode 2).
    """
    r = settlement_rate(a, b, base)
    k_b = b.frame.capital_stock_teh
    return {
        "rate": r,
        "years_of_mint_for_whole_capital": k_b / r / a.teh_created,
        "years_of_mint_for_annual_mint": b.teh_created / r / a.teh_created,
    }


def _arc_collective(collective_id: int, epsilon: float) -> Collective | None:
    """A canonical-arc collective, or None where the arc holds no capital (ε=0)."""
    s = canonical_physical_state(epsilon)
    k = float(s["capital_stock_teh"])
    if k <= 0.0:
        return None
    frame = CollectiveFrame(
        collective_id=collective_id,
        population=REFERENCE_FRAME_POPULATION,
        land_hectares=REFERENCE_FRAME_POPULATION * LAND_HECTARES_PER_CAPITA,
        capital_stock_teh=k,
        capital_age_ratio=float(s["capital_age_ratio"]),
        ecosystem_health=float(s["ecosystem_health"]),
    )
    return build_collective(frame, epsilon)


def arc_pairing(
    points: tuple[float, ...] = SEARCH_POINTS,
    pairing: str = "arc",
) -> dict[str, Any]:
    """
    Every ordered pair of collectives at different ε, per base: the rate
    extrema and the cheapest whole-base acquisition.

    `pairing="arc"` builds each collective on the canonical arc (capital, age
    and health from `canonical_physical_state`). The arc holds no capital at
    ε=0, and a frame with no capital is refused, so those points are EXCLUDED
    and listed — the subsistence end is then covered only by `"fixed"`.

    `pairing="fixed"` holds the frame at the ε=0.40 reference intensity and
    varies only ε — isolating the automation level from the capital that
    usually accompanies it, and reaching ε=0.

    Reports, per base: min/max rate over all pairs with the ε-pair where each
    sits (min = 1/max, since every base is reciprocal — so `max_rate` alone is
    the spread's square root, and no separate spread is reported), and the cheapest whole-capital acquisition in years of the
    acquirer's own mint. Extrema sit BETWEEN the reporting points for several
    bases (ε≈0.72–0.77), which is why the search grid is not
    `ARC_REPORTING_POINTS`.
    """
    if pairing not in ("arc", "fixed"):
        raise ValueError(f"pairing must be 'arc' or 'fixed', got {pairing!r}")
    built: list[Collective] = []
    excluded: list[float] = []
    for i, e in enumerate(points):
        c = (_arc_collective(i, e) if pairing == "arc"
             else build_collective(_reference_frame(i), e))
        if c is None:
            excluded.append(e)
        else:
            built.append(c)

    out: dict[str, Any] = {}
    for base in BASES:
        lo = hi = None
        cheapest: tuple[float, float, float] | None = None
        for a, b in permutations(built, 2):
            r = settlement_rate(a, b, base)
            if lo is None or r < lo[0]:
                lo = (r, a.epsilon, b.epsilon)
            if hi is None or r > hi[0]:
                hi = (r, a.epsilon, b.epsilon)
            y = acquisition(a, b, base)["years_of_mint_for_whole_capital"]
            if cheapest is None or y < cheapest[0]:
                cheapest = (y, a.epsilon, b.epsilon)
        assert lo is not None and hi is not None and cheapest is not None
        out[base] = {
            "min_rate": lo[0], "min_at": (lo[1], lo[2]),
            "max_rate": hi[0], "max_at": (hi[1], hi[2]),
            "cheapest_whole_capital_years": cheapest[0],
            "cheapest_at": (cheapest[1], cheapest[2]),
            "by_construction": BY_CONSTRUCTION.get(base),
        }
    return {
        "pairing": pairing,
        "points": len(points),
        "excluded_epsilons": excluded,
        "bases": out,
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# Why the per-TEH bases are not bounded — §5's "because", evaluated
# ---------------------------------------------------------------------------

def spread_decomposition(
    points: tuple[float, ...] = SEARCH_POINTS,
    pairing: str = "arc",
) -> dict[str, Any]:
    """
    §5 argues: the floor is bounded by the obligation, the obligation is bounded
    by population, SO settling on the base keeps the cross-rate inside a ratio of
    two physically-bounded quantities. This evaluates each step.

        obligation-base rate = (E_a/T_a)/(E_b/T_b)
                             = [(E_a/P_a)/(E_b/P_b)] · [(T_b/P_b)/(T_a/P_a)]

    so its spread is the spread of per-capita OBLIGATION (the population-bounded
    quantity) times the spread of per-capita MINT — and the mint passes through
    the register. Reported: max/min over the grid of each factor, and of the
    registration share and human fraction that drive the mint.
    """
    if pairing not in ("arc", "fixed"):
        raise ValueError(f"pairing must be 'arc' or 'fixed', got {pairing!r}")
    cs: list[Collective] = []
    for i, e in enumerate(points):
        c = (_arc_collective(i, e) if pairing == "arc"
             else build_collective(_reference_frame(i), e))
        if c is not None:
            cs.append(c)

    def spread(xs: list[float]) -> float:
        return max(xs) / min(xs)

    obligation_pc = [float(c.pipeline["total_eoh"]) / c.frame.population for c in cs]
    mint_per_eoh = [c.teh_created / float(c.pipeline["total_eoh"]) for c in cs]
    share = [float(c.pipeline["registration_share"]) for c in cs]
    human = [float(c.pipeline["human_eoh"]) / float(c.pipeline["total_eoh"]) for c in cs]
    return {
        "pairing": pairing,
        "obligation_per_capita_spread": spread(obligation_pc),
        "mint_per_eoh_spread": spread(mint_per_eoh),
        "registration_share_spread": spread(share),
        "human_fraction_spread": spread(human),
        "reading": (
            "the obligation IS population-bounded — its per-capita spread across "
            "the whole arc is small — so §5's 'because' holds for any base that "
            "reads the obligation or floor directly. It fails for a per-TEH base, "
            "which converts through TEH-per-EOH, and that runs through the "
            "registration share."
        ),
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# The frame seam (failure mode 6)
# ---------------------------------------------------------------------------

def frame_check(epsilon: float = 0.40) -> dict[str, Any]:
    """
    Each base against a frame change that should NOT move it, and one that may.

    `scaled`: 10× the population, same per-capita capital and land. Any base
    that moves here is reading an extensive quantity through a seam.
    `land`: same population and capital, 3× the land per person — a REAL
    ecological difference, which may move a base, and which is reported so a
    seam is distinguishable from a physical effect.
    """
    ref = build_collective(_reference_frame(0), epsilon)
    scaled = build_collective(
        _reference_frame(1, population=10.0 * REFERENCE_FRAME_POPULATION), epsilon
    )
    land = build_collective(
        _reference_frame(2, hectares_per_capita=3.0 * LAND_HECTARES_PER_CAPITA), epsilon
    )
    return {
        "epsilon": epsilon,
        "scaled_population": {b: settlement_rate(scaled, ref, b) for b in BASES},
        "more_land_per_capita": {b: settlement_rate(land, ref, b) for b in BASES},
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# One call
# ---------------------------------------------------------------------------

def base_report() -> dict[str, Any]:
    """Everything above, and what only the author can decide."""
    return {
        "capture": {e: capture_response(epsilon=e) for e in ARC_REPORTING_POINTS},
        "multiplier": multiplier_response(),
        "arc": arc_pairing(pairing="arc"),
        "fixed": arc_pairing(pairing="fixed"),
        "decomposition": spread_decomposition(),
        "frame": frame_check(),
        "author_decides": [
            "THE TRADE-OFF THE TABLE SHOWS: every base that disciplines issuance "
            "reads TEH-per-EOH, which legitimately runs ~20x along the arc, so it "
            "inherits that spread; the only bounded base that sees the collective "
            "(obligation_parity) is blind to issuance — including a multiplier "
            "set above the shipped one. A base measured against the published registration "
            "schedule at the collective's own ε would separate the two, but it "
            "settles against a policy curve rather than physics; not built.",
            "DECIDED 2026-09-30: registered settles, floor is read beside it. The "
            "items below were the open questions at the comparison and are kept "
            "as what the decision set aside.",
            "SET ASIDE — WHETHER MACHINE-FULFILLED OBLIGATION BACKS A TEH: "
            "'obligation' says yes, 'human' says no, and they put a high-capital "
            "collective on opposite sides of par at high ε. Neither settles.",
            "SET ASIDE — WHETHER A BASE BLIND TO THE COLLECTIVE ('floor') IS "
            "ACCEPTABLE AS SETTLEMENT: it is read beside settlement, not applied.",
        ],
        "what_this_does_not_establish": [
            "that any base clears a real trade — there is no goods layer, so what "
            "a settled TEH buys on the far side is not represented.",
            "anything about actors or incentives — no defection is modelled.",
            "a verdict on 'bounded': the report gives the rate spread and the "
            "cheapest acquisition in years of mint; the threshold at which that "
            "becomes 'your entire collective' is the author's reading of §5, "
            "not a constant this module chose.",
        ],
        "reporting_only": True,
    }


# ---------------------------------------------------------------------------
# REGISTERED AND FLOOR — the two carried forward (author, 2026-09-30)
# ---------------------------------------------------------------------------
#
# ADOPTED the same day: registered settles (`exchange.registered_rate`), the
# floor is read beside it (`exchange.settlement_terms`). What follows asks of the
# two what the table above could not: where each one's bound COMES from,
# whether it holds, and what each does when money moves through the book.

#: The cross-rate range `registered` is confined to IF both collectives honour
#: Condition II. Derived, not chosen: it is the band's own edges, divided.
BAND_RATE_BOUNDS: tuple[float, float] = (M_BAND_LOW / M_BAND_HIGH, M_BAND_HIGH / M_BAND_LOW)


def registered_settlement(a: Collective, b: Collective) -> dict[str, Any]:
    """
    Hour-for-hour settlement, with the condition that makes it bounded checked.

        r(a, b) = m_b / m_a        [TEH_b per TEH_a]

    One TEH of `a` certifies 1/m_a hours of registered obligation SERVED; it
    settles for the TEH_b that certify the same hours. This is §5's "a base EOH
    here is a base EOH there" read literally.

    THE BOUND IS CONDITIONAL. r lies inside `BAND_RATE_BOUNDS` only when both
    multipliers lie inside the Condition II band — and nothing in
    `build_collective` enforces the band; a caller can mint at any multiplier.
    So the check runs on both sides and travels with the rate: a breach is
    reported, never clamped, because clamping would hide the state Condition II
    exists to surface.
    """
    m_a = float(a.pipeline["mean_multiplier"])
    m_b = float(b.pipeline["mean_multiplier"])
    r = settlement_rate(a, b, "registered")
    ca, cb = condition_ii_check(m_a), condition_ii_check(m_b)
    lo, hi = BAND_RATE_BOUNDS
    return {
        "rate": r,
        "m_a": m_a,
        "m_b": m_b,
        "status_a": ca["status"],
        "status_b": cb["status"],
        "both_in_band": bool(ca["in_band"] and cb["in_band"]),
        "within_band_bounds": lo <= r <= hi,
        "band_rate_bounds": BAND_RATE_BOUNDS,
    }


def composition_pairing(
    epsilon: float = 0.40,
    snapshots: tuple[str, ...] = tuple(WORKFORCE_SNAPSHOTS),
) -> dict[str, Any]:
    """
    `registered` between collectives whose multipliers DIFFER — the only case
    in which it says anything.

    At the shipped multiplier every `registered` rate is exactly 1.0: one unit
    and no pairwise rate, which is the MUTUAL RECOGNITION regime
    `register_federation.recognition_regimes` already priced ("the exchange
    layer reports nothing whatever happens in any register"). Whether
    `registered` is more than that depends on multipliers actually differing
    between collectives.

    The multipliers here come from `reference/workforce.WORKFORCE_SNAPSHOTS`.
    READ WHAT THEY ARE (failure mode 8): five ILLUSTRATIVE compositions written
    to sit at chosen band positions, not measurements of any economy. THREE sit
    out of band: `below_band` and `above_band` by design, and `high_epsilon` —
    the composition written to represent the NATURAL high-ε workforce, base
    tier automated away — at ≈2.22, with nobody gaming anything. If
    `registered` settles, a federation's high-ε members are flagged by their
    skill mix, and the band bound fails where the arc is heading.

    In-band pairs staying inside `BAND_RATE_BOUNDS` is ALGEBRA, not a result
    (both m in [LOW, HIGH] ⇒ m_b/m_a in [LOW/HIGH, HIGH/LOW]); the informative
    counts are the breach pairs that leave it. They show what the rate does across
    compositions; they do not show that real collectives differ this much.
    Every collective is built at the same ε and frame, so the multiplier is the
    only thing that differs.
    """
    ms = {k: population_weighted_mean_multiplier(WORKFORCE_SNAPSHOTS[k]) for k in snapshots}
    cs = {
        k: build_collective(_reference_frame(i), epsilon, mean_multiplier=m)
        for i, (k, m) in enumerate(ms.items())
    }
    pairs = {
        (x, y): registered_settlement(cs[x], cs[y])
        for x, y in permutations(cs, 2)
    }
    in_band_pairs = [v for v in pairs.values() if v["both_in_band"]]
    breach_pairs = [v for v in pairs.values() if not v["both_in_band"]]
    return {
        "epsilon": epsilon,
        "multipliers": ms,
        "pairs": pairs,
        "in_band_pairs_within_bounds": all(v["within_band_bounds"] for v in in_band_pairs),
        "breach_pairs_outside_bounds": sum(not v["within_band_bounds"] for v in breach_pairs),
        "breach_pairs": len(breach_pairs),
        "provenance": "illustrative compositions (reference/workforce.py), not measured",
        "reporting_only": True,
    }


def floor_epsilon_seam(points: tuple[float, ...] = ARC_REPORTING_POINTS) -> dict[str, Any]:
    """
    WHICH ε THE FLOOR IS A FUNCTION OF — a seam, reported and not resolved.

    `floor_price(ε)` is called with the SUPPLIED capability index at every call
    site in `core/` and `scenarios/`. The physical machine share is the
    OBSERVED ε, `machine_eoh / total_eoh`, and under `per_component` it sits
    strictly below the capability away from zero, because care resists
    automation (record/fulfilment.md). A settlement leg on the supplied ε settles
    against a number the collective STATES; on the observed ε, against one it
    MEASURES. Switching would change what the floor price is a function of
    repo-wide — a theory choice, left to the author.

    Reports, at each point on the fixed reference frame: both ε, both floors,
    and the settlement rate against the ε=0 collective under each.
    """
    ref = build_collective(_reference_frame(0), 0.0)
    rows = []
    for i, e in enumerate(points):
        c = build_collective(_reference_frame(i + 1), e)
        obs = float(c.pipeline["epsilon_observable"])
        rows.append({
            "epsilon_supplied": e,
            "epsilon_observed": obs,
            "floor_supplied": floor_price(e),
            "floor_observed": floor_price(obs),
            "rate_vs_subsistence_supplied": settlement_rate(c, ref, "floor"),
            "rate_vs_subsistence_observed": settlement_rate(c, ref, "floor_observed"),
        })
    return {
        "rows": rows,
        "max_rate_supplied": max(r["rate_vs_subsistence_supplied"] for r in rows),
        "max_rate_observed": max(r["rate_vs_subsistence_observed"] for r in rows),
        "author_decides": (
            "whether the floor price is a function of the capability a collective "
            "states or the machine share it measures"
        ),
        "reporting_only": True,
    }


def purchasing_gain(a: Collective, b: Collective, floor_base: str = "floor") -> dict[str, float]:
    """
    What an hour settled hour-for-hour buys on the far side, in baskets.

        gain = r_floor(a, b) / r_registered(a, b)

    Settle on `registered` (hours for hours), then spend at b's floor: `gain`
    baskets in b per basket the same hours bought at home. Above 1.0 the hour
    buys more abroad. This is the ratio of the two carried-forward bases, NOT
    their product — the product has units (TEH_b/TEH_a)² and means nothing.

    Composition is clean here only because `floor_price` does not read the
    multiplier (checked: its signature and body carry no m), so the two legs
    are independent and neither applies the other's mechanism (failure mode 11).
    Bounded by the band ratio times the floor's own spread, when both
    collectives are in band.
    """
    if floor_base not in ("floor", "floor_observed"):
        raise ValueError(f"floor_base must be 'floor' or 'floor_observed', got {floor_base!r}")
    rf = settlement_rate(a, b, floor_base)
    rr = settlement_rate(a, b, "registered")
    return {"floor_rate": rf, "registered_rate": rr, "gain": rf / rr}


def settled_rate_matrix(collectives: list[Collective], base: str) -> dict[tuple[int, int], float]:
    """`exchange.rate_matrix` with the rate taken from `base` instead of parity."""
    return {
        (a.collective_id, b.collective_id): settlement_rate(a, b, base)
        for a, b in permutations(collectives, 2)
    }


#: Fraction of the smaller ceiling a book-exercise transfer sends. Numerics
#: only: AT the ceiling, whether `breached` fires is decided by float rounding
#: of `reserve − earmarked`; half keeps a neutral-rate transfer clear of that
#: edge, so a breach it reports is the RATE's doing.
_INSIDE_CEILING: float = 0.5


def book_exercise(
    share_delta: float = 0.05,
    epsilon: float = 0.40,
    bases: tuple[str, ...] = ("parity", "registered", "floor", "floor_observed"),
) -> dict[str, Any]:
    """
    The capture scenario run THROUGH the double-entry book, per base.

    `register_federation` measured parity's reward as a rate. This moves money:
    the capturing collective sends half the SMALLER of the two settlement ceilings
    (`COASEAN_IMBALANCE_CEILING` × reserve) to the honest one at each base's
    rate, via `FederationBook.transfer`. The smaller, because each ceiling is a
    fraction of its OWN reserve and capture enlarges the capturer's: sending
    the capturer's own ceiling breaches the honest receiver even at rate 1, so
    a breach there would say nothing about the rate. Reported: what arrived, the federation's change
    in resident holdings (the revaluation), whether both books balance, and
    whether either side breached.

    Under parity the honest collective receives MORE than was sent, in a unit
    the capture made look productive, and federation holdings grow by the
    revaluation. Under a neutral base it receives exactly what was sent and
    federation holdings are conserved — which, before `transfer`'s sender leg
    was corrected on 2026-09-30, no base could show.
    """
    honest = build_collective(_reference_frame(0), epsilon)
    captured = build_collective(
        _reference_frame(1),
        epsilon,
        personal_registration_share=personal_eoh_registration_share(epsilon) + share_delta,
    )
    amount = COASEAN_IMBALANCE_CEILING * min(honest.reserve, captured.reserve) * _INSIDE_CEILING
    out: dict[str, Any] = {}
    for base in bases:
        book = FederationBook.from_collectives([honest, captured])
        before = sum(book.ledger(i).holdings() for i in (0, 1))
        r = settled_rate_matrix([honest, captured], base)[(1, 0)]
        t = book.transfer(1, 0, amount=amount, rate=r, memo=f"capture @ {base}")
        rep = book.settlement_report()
        out[base] = {
            "rate": r,
            "sent": t["sent"],
            "received": t["received"],
            "federation_holdings_change": sum(book.ledger(i).holdings() for i in (0, 1)) - before,
            "books_balance": book.all_balance(),
            "receiver_breached": bool(rep[0]["breached"]),
            "sender_breached": bool(rep[1]["breached"]),
        }
    return {
        "epsilon": epsilon,
        "share_delta": share_delta,
        "amount_sent": amount,
        "bases": out,
        "reporting_only": True,
    }


def focus_report() -> dict[str, Any]:
    """The registered/floor section as one call."""
    return {
        "band_rate_bounds": BAND_RATE_BOUNDS,
        "composition": composition_pairing(),
        "floor_seam": floor_epsilon_seam(),
        "book": {e: book_exercise(epsilon=e) for e in ARC_REPORTING_POINTS},
        "author_decides": [
            "DECIDED 2026-09-30: registered settles; floor is the purchasing-power "
            "reading beside it (`purchasing_gain`). Still open:",
            "for floor: the SUPPLIED or the OBSERVED ε (`floor_epsilon_seam`).",
            "what disciplines a deficit beyond reserve under base settlement — "
            "`settlement_check`'s depreciation would be a non-base rate (§5).",
            "for registered: whether mutual recognition at a common multiplier is "
            "acceptable, since that is what it reduces to unless multipliers "
            "differ — and whether a band breach suspends settlement or only "
            "reports, given that the illustrative NATURAL high-ε composition "
            "breaches the band on its own.",
        ],
        "reporting_only": True,
    }
