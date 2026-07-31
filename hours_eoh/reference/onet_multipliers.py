"""
Measured reference multiplier data — O*NET 30.3 + BLS EP/OEWS.

This module loads the frozen v5.1 reference multiplier registry: 751 occupations
covering 94.2% of US employment, with each of the four assessment factors
(training, demand, scarcity, impact) MEASURED from public survey data rather than
assigned by hand. It is the first real-world dataset the HOURS multiplier chews on.

Provenance and honest limits live in two shipped files next to this module:
    data/multiplier_registry_v5.csv        the 751-occupation registry (production output)
    data/multiplier_reference_bounds.json  the frozen normalization/geometric-map reference
    data/multiplier_provenance_v5.csv      every constant tagged physics/derived/measured/CHOSEN

Read `docs/parameter_provenance.md` §Multiplier and the handoff's `FALSIFIABILITY.md`
before citing any absolute figure: the RANK ORDERING and PAIRWISE RATIOS are
measurements (falsifiable against source data); the absolute range, global spread
ratio and band pass are construction artifacts of the normalization choice
(±2.8× swing across normalizations) with no empirical content.

Sources: O*NET 30.3 (May 2026), BLS Employment Projections 2024–2034,
BLS OEWS May 2025. Frozen reference epoch 2026-07-29, methodology mult-5.1.0.

Layer rule: `reference/` imports nothing from hours_eoh core/land/scenarios —
this module reads only shipped data files via the standard library.
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

_DATA_DIR = Path(__file__).resolve().parent / "data"
_REGISTRY_CSV = _DATA_DIR / "multiplier_registry_v5.csv"
_REFERENCE_BOUNDS_JSON = _DATA_DIR / "multiplier_reference_bounds.json"


class OccupationMultiplier(TypedDict):
    """One measured occupation row from the frozen v5.1 registry.

    Factor columns (`f_*`) are economy-wide normalized to [0, 1]; the impact
    sub-components (`i_*`) are the measured inputs behind `f_impact`. `composite`
    is Σ(factor_weight × f_factor) at the frozen weights; `reference_multiplier`
    is the geometric map floor·R^z of that composite. See
    `hours_eoh.core.multipliers.reference_multiplier`.
    """

    occ6: str                    # 6-digit SOC code
    title: str
    employment_k: float          # BLS EP employment, thousands of workers
    median_wage: float           # BLS OEWS median annual wage (USD), context only
    f_training: float            # measured — O*NET education + training/experience
    f_demand: float              # measured — O*NET abilities/skills/work-context burden
    f_scarcity: float            # measured — BLS EP openings + growth
    i_dependency: float          # impact sub — 1 − HHI industry dispersion
    i_substitutability: float    # impact sub — 1 − norm(log route pool)
    i_harm: float                # impact sub — work-context harm-of-absence
    i_temporal: float            # impact sub — persisting − transient activities (residualized)
    f_impact: float              # measured (3 of 4 sub anchored) — outer-normalized impact composite
    composite: float             # Σ w_i·f_i at frozen weights ∈ ~[0.15, 0.74]
    reference_multiplier: float  # floor·R^z geometric map of composite ∈ [1.0, R]


@lru_cache(maxsize=1)
def load_reference_bounds() -> dict:
    """Return the frozen v5.1 reference bounds (geometric map, normalization,
    factor weights, baseline metrics).

    These values are FROZEN at the 2026-07-29 reference epoch. Re-deriving any of
    them per data vintage re-introduces the circularity the freeze exists to break
    (see the file's own `warning` field). Callers should read, never recompute.
    """
    with _REFERENCE_BOUNDS_JSON.open(encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return data


@lru_cache(maxsize=1)
def _load_rows() -> tuple[OccupationMultiplier, ...]:
    rows: list[OccupationMultiplier] = []
    with _REGISTRY_CSV.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                OccupationMultiplier(
                    occ6=r["occ6"],
                    title=r["title"],
                    employment_k=float(r["ep_employment_k"]),
                    # wage is context-only; a handful of Mode-A-recovered rows lack it
                    median_wage=float(r["oews_median_wage"]) if r["oews_median_wage"].strip() else float("nan"),
                    f_training=float(r["f_training"]),
                    f_demand=float(r["f_demand"]),
                    f_scarcity=float(r["f_scarcity"]),
                    i_dependency=float(r["i_dependency"]),
                    i_substitutability=float(r["i_substitutability"]),
                    i_harm=float(r["i_harm"]),
                    i_temporal=float(r["i_temporal"]),
                    f_impact=float(r["f_impact"]),
                    composite=float(r["composite"]),
                    reference_multiplier=float(r["reference_multiplier"]),
                )
            )
    return tuple(rows)


def load_registry() -> list[OccupationMultiplier]:
    """Return all 751 measured occupation rows from the frozen v5.1 registry.

    A fresh list (safe to mutate) of shared, immutable row dicts. Employment
    weights are in thousands of workers (`employment_k`).
    """
    return list(_load_rows())


def registry_segments() -> list[dict]:
    """Project the registry onto the `segments` shape consumed by
    `hours_eoh.core.multipliers.population_weighted_mean_multiplier`.

    Each occupation becomes one segment: `fraction` = its employment share of the
    registry, `mean_mu` = its measured `reference_multiplier`. Feeding the result
    to `population_weighted_mean_multiplier` reproduces the frozen employment-
    weighted mean (≈ 1.9993) — the measured-data replacement for the synthetic
    `DEFAULT_SEGMENTS`.

    Returns:
        list of {"name": occ6, "fraction": emp_share, "mean_mu": reference_multiplier}.
        Fractions sum to 1.0 (up to float error).
    """
    rows = _load_rows()
    total_emp = sum(r["employment_k"] for r in rows)
    if total_emp <= 0.0:
        raise ValueError("registry has non-positive total employment")
    return [
        {
            "name": r["occ6"],
            "fraction": r["employment_k"] / total_emp,
            "mean_mu": r["reference_multiplier"],
        }
        for r in rows
    ]


def anchor_pairs() -> dict[str, tuple[str, str]]:
    """A small set of interior occupation pairs whose ratio is the robust,
    falsifiable claim (see `FALSIFIABILITY.md`: pairwise ratios vary only
    1.06–1.24× across radically different normalizations, unlike the global
    spread). Used by the sensitivity harness to report ratio stability.

    Values are (numerator occ6, denominator occ6).
    """
    return {
        # anesthesiologist / orderly-equivalent (nursing assistant)
        "anesthesiologist_over_nursing_assistant": ("291211", "311131"),
        # registered nurse / nursing assistant
        "rn_over_nursing_assistant": ("291141", "311131"),
        # general/operations manager / office clerk
        "manager_over_office_clerk": ("111021", "439061"),
    }
