"""
research/dynamic_stability — DOES ANY LOOP OSCILLATE?

`record/verification.md § Open` carried "Dynamic stability / oscillation is
unbuilt … nothing tests for limit cycles." `arc_stability` answers whether the
system can STAND STILL at a point; this answers whether the coupled loops,
run forward, settle, drift or cycle. It runs the repo's own forward models and
reads their trajectories — nothing is re-implemented.

    oscillation(series)       the detector: direction changes, onset, dominant
                              period, the swing's trend (growing / decaying)
    formation_stability(...)  the capital → automation → income → formation
                              loop (`research/formation`, §8.9c)
    simulation_stability(...) the period engine (`core/simulation`), at a fixed
                              ε or along a rising arc

WHAT IT FOUND (2026-10-01, called, not recalled):
  * The period engine does not oscillate — no state field changes direction
    more than twice in 200–330 periods at fixed ε or on a rising arc.
  * The formation loop under `priority="share"` is monotone in ε to 0.99;
    private formation and the dividend wobble over years 11–24 and settle
    (TRANSIENT) as private funding ends.
  * Under `priority="dividend"` it is a PERIOD-2 COBWEB from year ≈206: private
    formation switches on and off every other year across the supply curve's
    clamp at f = 0 (`investment_supply_fraction`, charter share alternating
    ≈0.877 / ≈0.928 against the 0.9 at which supply hits zero), and ε steps
    up, then down; private formation runs a STEADY full on/off. ε and the
    dividend are BOUNDED AND DECAYING relative to their level, so a cobweb, not
    a divergence — and the arc it drags reaches only ε ≈ 0.91 in 1,000 years. Onset at year ≈206 is invisible
    to any horizon of 200 years or less (failure mode 3 in time).

THE DETECTOR STATES ITS GAPS: it reads one series at a time, so a cycle that
exists only in a combination of fields is invisible to it; and its tolerance
treats changes below `rel_tol` of the series' scale as flat, so a sub-tolerance
cycle reads MONOTONE.

RESEARCH / REPORTING ONLY — not imported by core/, land/ or scenarios/.
"""

from __future__ import annotations

import statistics
from typing import Any, Sequence

#: Steps smaller than this fraction of the series' scale count as flat.
DEFAULT_REL_TOL: float = 1e-9
#: More direction changes than this is a cycle, not a turning point.
TURNING_POINTS_MAX: int = 2


def oscillation(series: Sequence[float], rel_tol: float = DEFAULT_REL_TOL) -> dict:
    """
    Read one trajectory for oscillation.

    Returns {verdict, direction_changes, onset (index of the first turn, or
    None), period (median steps between turns, ×2 — a full cycle), max_rise,
    max_fall, swing_trend, n}.

    verdict: "MONOTONE" (no turn), "TURNING" (≤ TURNING_POINTS_MAX), "TRANSIENT"
    (more, but none in the last third of the series — it settled),
    "OSCILLATING" (more, and still turning in the last third).
    swing_trend (OSCILLATING only): the largest fall RELATIVE TO THE LEVEL in
    the last third of the oscillating stretch against the first — "GROWING" /
    "DECAYING" / "STEADY". Relative, because a swing that keeps pace with a
    rising level is not growing.
    """
    xs = [float(x) for x in series]
    if len(xs) < 3:
        raise ValueError("need at least 3 points")
    scale = max(abs(x) for x in xs) or 1.0
    steps = [b - a for a, b in zip(xs, xs[1:])]
    live = [(i, d) for i, d in enumerate(steps) if abs(d) > rel_tol * scale]
    turns = [i for (j, a), (i, b) in zip(live, live[1:]) if (a > 0) != (b > 0)]
    n_turns = len(turns)
    sustained = bool(turns) and turns[-1] >= 2 * len(steps) // 3
    verdict = ("MONOTONE" if n_turns == 0
               else "TURNING" if n_turns <= TURNING_POINTS_MAX
               else "OSCILLATING" if sustained else "TRANSIENT")
    period = (2.0 * statistics.median(b - a for a, b in zip(turns, turns[1:]))
              if n_turns >= 2 else None)
    swing_trend = None
    if verdict == "OSCILLATING":
        rel = [d / abs(xs[i]) if xs[i] != 0.0 else 0.0
               for i, d in enumerate(steps)][turns[0]:]
        third = max(1, len(rel) // 3)
        first = max([-d for d in rel[:third] if d < 0.0], default=0.0)
        last = max([-d for d in rel[-third:] if d < 0.0], default=0.0)
        ratio = last / first if first > 0.0 else float("inf")
        swing_trend = ("GROWING" if ratio > 1.0 + rel_tol
                       else "DECAYING" if ratio < 1.0 - rel_tol else "STEADY")
    return {
        "verdict": verdict, "direction_changes": n_turns,
        "onset": turns[0] if turns else None, "period": period,
        "max_rise": max(steps), "max_fall": min(steps),
        "swing_trend": swing_trend, "n": len(xs),
    }


def _numeric_fields(rows: list[dict]) -> list[str]:
    return [k for k, v in rows[0].items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)]


def formation_stability(
    n_years: int = 1000,
    fields: Sequence[str] = ("eps_actual", "private_funded", "dividend_per_capita"),
    rel_tol: float = DEFAULT_REL_TOL,
    **formation_kw: Any,
) -> dict:
    """
    Run `research.formation.formation_feedback_simulation` and read each field.

    The horizon defaults to 1,000 years because the dividend-priority cobweb
    begins at year ≈206: a 100- or 200-year run reports MONOTONE.
    """
    from hours_eoh.research.formation import formation_feedback_simulation
    rows = formation_feedback_simulation(n_years=n_years, **formation_kw)
    return {
        "n_years": n_years,
        "kwargs": dict(formation_kw),
        "fields": {f: oscillation([r[f] for r in rows], rel_tol) for f in fields},
        "final_epsilon": rows[-1]["eps_actual"],
    }


def simulation_stability(
    n_periods: int = 200,
    epsilon: float = 0.40,
    rel_tol: float = DEFAULT_REL_TOL,
    **period_kw: Any,
) -> dict:
    """
    Run `core.simulation.simulate_period` forward from `make_economy_state(ε)`
    and read every numeric state field. `period_kw` reaches `simulate_period`
    (e.g. `epsilon_delta` for a rising arc, `workforce_epsilon_decay`).
    """
    from hours_eoh.core.simulation import make_economy_state, simulate_period
    state = make_economy_state(epsilon=epsilon)
    rows: list[dict] = []
    for _ in range(n_periods):
        state, _period = simulate_period(state, **period_kw)
        rows.append(dict(state))
    readings = {f: oscillation([r[f] for r in rows], rel_tol)
                for f in _numeric_fields(rows)}
    return {
        "n_periods": n_periods, "epsilon_start": epsilon,
        "epsilon_end": rows[-1]["epsilon"], "kwargs": dict(period_kw),
        "oscillating": sorted(f for f, r in readings.items() if r["verdict"] == "OSCILLATING"),
        "fields": readings,
    }
