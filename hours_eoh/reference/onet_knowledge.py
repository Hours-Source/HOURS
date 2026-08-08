"""
Measured occupational training hours — recovered from the O*NET 30.3 / BLS spine.

This module answers one question from data already shipped in this repo: **how
many hours of training does the workforce embody?** That quantity is the input
`KNOWLEDGE_EOH_BASE`'s epistemic pointer has always named ("occupational CPD
hours"), and it turns out the multiplier registry already carries it.

The recovery (why this is measurement, not invention)
-----------------------------------------------------
`data/multiplier_provenance_v5.csv` tags `f_training` as::

    f_training,log-minmax of measured hours,derived,economy-wide normalization

So `f_training` is a normalized *measurement*, and the normalization is exactly
invertible against the frozen bounds in `multiplier_reference_bounds.json`::

    hours(c) = exp( lo + f_training(c) · (hi − lo) )      lo, hi = train_log bounds

Nothing is fitted, assumed or back-solved here. The registry stores a monotone
transform of measured hours; this module applies its inverse.

What the numbers look like at the frozen epoch
-----------------------------------------------
    range                     771 h  →  37,220 h   (short OJT → physician)
    employment-weighted mean  11,001 h/worker  ≈  5.3 FTE-years at 2,080 h/yr
    covered employment        157.79 M over 751 occupations

The mean is face-plausible for a modern workforce: roughly thirteen years of
schooling plus occupational training. That is a sanity check, not a validation —
see the limits below.

HONEST LIMITS — read before citing any figure from here
--------------------------------------------------------
1. **STOCK, NOT FLOW.** These are cumulative hours to reach occupational
   competency. They are NOT annual continuing-professional-development hours.
   Converting stock to an annual obligation requires a renewal rate, which is a
   separate quantity this module does not and cannot supply. O*NET measures the
   hours to *reach* competency, never the hours to *hold* it. The CPD term is
   resolved by Eurostat CVTS (paid training hours per employee), which is not
   ingested anywhere in this repo.
2. **The tails are winsorized and therefore not recoverable.** The registry was
   built with 1/99 percentile winsorization, so occupations at `f_training` 0.0
   or 1.0 are clipped: their true hours lie beyond the returned bound. That is
   exactly 8 occupations at each tail of 751. `occupation_training_hours()`
   flags them; treat clipped rows as bounds, not values.
3. **No external corroboration exists.** The whole chain rests on the O*NET
   education/training category → hours mapping performed upstream in
   `handoffs/multipliers-v5/`. Nothing in this repo checks it against an
   independent source. NCES/OECD attainment-and-instructional-hours would.
4. **US-specific and epoch-frozen** (reference epoch 2026-07-29, methodology
   mult-5.1.0). Employment weights are BLS EP 2024–2034.
5. **This module deliberately does not convert to per-capita.** Doing so needs an
   employment-to-population ratio and a registry-coverage gross-up, neither of
   which is derivable from the shipped data files. Those are the caller's
   inputs; see `hours_eoh/scenarios/knowledge_base.py`, which documents both.

Layer rule: `reference/` imports nothing from hours_eoh core/land/scenarios/data —
this module reads only shipped data files via the standard library.

Reference: notes/knowledge-eoh-closure.md §1 (the derivation route); Block K-II.
"""

from __future__ import annotations

import csv
import math
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

_DATA_DIR = Path(__file__).resolve().parent / "data"
_REGISTRY_CSV = _DATA_DIR / "multiplier_registry_v5.csv"
_BOUNDS_JSON = _DATA_DIR / "multiplier_reference_bounds.json"

# The registry stores employment in thousands (`ep_employment_k`).
_EMPLOYMENT_UNITS = 1_000.0


class OccupationTraining(TypedDict):
    """One occupation's recovered training stock."""
    occ6: str
    title: str
    employment: float          # persons
    f_training: float          # normalized [0, 1] as stored in the registry
    training_hours: float      # RECOVERED cumulative hours to competency
    winsorized: bool           # True → clipped tail; treat hours as a BOUND


@lru_cache(maxsize=1)
def train_log_bounds() -> tuple[float, float]:
    """
    The frozen (lo, hi) log-hour bounds `f_training` was normalized against.

    These are `bounds.train_log` in `multiplier_reference_bounds.json`, which
    carries `"frozen": true` and an explicit warning against re-deriving per
    vintage — re-derivation restores the circularity the freeze exists to break.

    Returns:
        (lo, hi) in natural-log hours. exp() of each gives 771 h and 37,220 h.
    """
    import json
    with _BOUNDS_JSON.open() as fh:
        bounds = json.load(fh)["bounds"]["train_log"]
    return float(bounds[0]), float(bounds[1])


def training_hours(f_training: float) -> float:
    """
    Invert the log-minmax normalization: normalized factor → measured hours.

        hours = exp( lo + f · (hi − lo) )

    units: hours (cumulative, to occupational competency — NOT per year).
    ε-behavior: none. This is a property of an occupation, not of the arc.

    Args:
        f_training: Normalized training factor as stored in the registry, [0, 1].

    Returns:
        Cumulative training hours. At f=0 → 770.5; at f=1 → 37,220.4.

    Raises:
        ValueError: if f_training is outside [0, 1].

    Worked example: f_training = 0.5 → exp(6.647 + 0.5 × 3.878) = 5,357 h,
    about 2.6 FTE-years — a mid-skill occupation.
    """
    if not 0.0 <= f_training <= 1.0:
        raise ValueError(f"f_training must be in [0, 1], got {f_training}")
    lo, hi = train_log_bounds()
    return math.exp(lo + f_training * (hi - lo))


@lru_cache(maxsize=1)
def _load_training_rows() -> tuple[OccupationTraining, ...]:
    rows: list[OccupationTraining] = []
    with _REGISTRY_CSV.open(newline="") as fh:
        for r in csv.DictReader(fh):
            f = float(r["f_training"])
            rows.append(OccupationTraining(
                occ6=r["occ6"],
                title=r["title"],
                employment=float(r["ep_employment_k"]) * _EMPLOYMENT_UNITS,
                f_training=f,
                training_hours=training_hours(f),
                # Clipped at either winsor tail — the true value lies beyond.
                winsorized=(f <= 0.0 or f >= 1.0),
            ))
    return tuple(rows)


def occupation_training_hours() -> list[OccupationTraining]:
    """
    Per-occupation recovered training stock, one row per registry occupation.

    Rows with `winsorized=True` sit at a clipped 1/99 percentile tail: their
    `training_hours` is a BOUND, not a value. There are 8 at each tail of 751,
    which is exactly what 1% per side predicts — this is the registry's designed
    baseline, not a defect.

    Returns:
        A fresh list of 751 OccupationTraining dicts (safe to mutate).
    """
    return [dict(r) for r in _load_training_rows()]  # type: ignore[misc]


def workforce_training_stock() -> dict:
    """
    Employment-weighted training stock embodied in the covered workforce.

        S_covered = Σ_c  employment(c) · training_hours(c)        [hours]
        mean      = S_covered / Σ_c employment(c)                 [hours/worker]

    This is the measured quantity Block K-II exists to produce. It is a STOCK.
    Turning it into the annual knowledge obligation needs (a) a renewal rate and
    (b) a population denominator, neither of which lives here — see the module
    docstring, limits 1 and 5.

    units: hours; employment in persons.
    ε-behavior: none — this describes one observed workforce at the frozen epoch,
    which is precisely why `scenarios/knowledge_base.py` must anchor it to an
    ε_ref rather than treating it as an ε=0 baseline.

    Returns:
        dict:
          "covered_employment"    float — persons in the 751 covered occupations
          "total_stock_hours"     float — Σ employment × training hours
          "mean_hours_per_worker" float — the headline: 11,001 h ≈ 5.3 FTE-years
          "median_hours"          float — unweighted median across occupations
          "min_hours"             float — 770.5 (a clipped bound)
          "max_hours"             float — 37,220.4 (a clipped bound)
          "n_occupations"         int
          "n_winsorized_low"      int   — 8 expected
          "n_winsorized_high"     int   — 8 expected
          "winsorized_employment_share" float — how much employment sits on a bound

    Worked example (frozen epoch): covered_employment 157,786,000;
    total_stock_hours 1.7359e12; mean_hours_per_worker 11,001.
    """
    rows = _load_training_rows()
    employment = sum(r["employment"] for r in rows)
    stock = sum(r["employment"] * r["training_hours"] for r in rows)
    hours_sorted = sorted(r["training_hours"] for r in rows)
    n = len(rows)
    mid = n // 2
    median = (hours_sorted[mid] if n % 2
              else 0.5 * (hours_sorted[mid - 1] + hours_sorted[mid]))
    clipped = [r for r in rows if r["winsorized"]]
    return {
        "covered_employment":    employment,
        "total_stock_hours":     stock,
        "mean_hours_per_worker": stock / employment if employment > 0 else 0.0,
        "median_hours":          median,
        "min_hours":             hours_sorted[0],
        "max_hours":             hours_sorted[-1],
        "n_occupations":         n,
        "n_winsorized_low":      sum(1 for r in rows if r["f_training"] <= 0.0),
        "n_winsorized_high":     sum(1 for r in rows if r["f_training"] >= 1.0),
        "winsorized_employment_share": (
            sum(r["employment"] for r in clipped) / employment
            if employment > 0 else 0.0
        ),
    }
