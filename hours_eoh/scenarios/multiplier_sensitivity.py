"""
Multiplier sensitivity harness — robustness of the measured reference multiplier
to its CHOSEN constants.

Why this exists
---------------
The v5.1 reference multiplier is measured (O*NET/BLS), but a handful of its
constants remain CHOSEN — the four factor weights, the impact sub-domain weights,
and the ε-weighting. the multiplier falsifiability pass establishes the
correct question to ask of them: NOT "does the band still pass" (the absolute
scale is a construction artifact — a band pass carries almost no empirical
content), but "does the RANK ORDERING and do the PAIRWISE RATIOS survive?" —
those are the measurements. This harness perturbs the CHOSEN constants over the
sweep ranges from `PROVENANCE_TABLE.csv` and reports both, honestly labelled.

What it sweeps (reconstructable from the shipped registry)
----------------------------------------------------------
- factor weights (training, demand, scarcity, impact) — ±delta, renormalized
- impact sub-domain weights (dependency, substitutability, harm, temporal)
- ε via epoch_factor_weights (the ε-arc IS a factor-weight sweep)
- Dirichlet Monte-Carlo over the factor-weight simplex (mirrors v5's 300-draw study)

What it CANNOT sweep from the registry alone (flagged, not silently skipped)
----------------------------------------------------------------------------
- scarcity leg split (O/G) — needs the raw legs, not the frozen f_scarcity column
- demand sub-domain weights — the registry carries only aggregated f_demand
- normalization method (min-max / winsor / rank) — needs a pipeline re-run;
  FALSIFIABILITY.md already quantifies this as the dominant ±2.8× spread swing
These require `economy_wide_final.csv` + a stage_b re-run; out of scope here.

Reporting convention (from FALSIFIABILITY.md)
---------------------------------------------
- PRIMARY (falsifiable): Spearman rank correlation vs the frozen ordering;
  pairwise-ratio drift on anchor pairs.
- SECONDARY (convention): employment-weighted mean / band verdict, spread ratio,
  clip rate. Reported, but labelled a construction artifact.

Layer: scenarios/ — imports core/ and reference/ (never the reverse).
ε-coherence: `epsilon_arc()` sweeps ε ∈ {0.0, 0.40, 0.99} (and any arc passed).
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np

from hours_eoh.core.multipliers import (
    composite_from_factors,
    impact_composite_from_subdomains,
    reference_multiplier,
    epoch_factor_weights,
)
from hours_eoh.data import (
    M_FACTOR_WEIGHTS, M_IMPACT_SUBDOMAIN_WEIGHTS,
    M_BAND_LOW, M_BAND_HIGH, M_COMPOSITE_Z_LO, M_COMPOSITE_Z_HI,
)
from hours_eoh.reference.onet_multipliers import (
    OccupationMultiplier, load_registry, anchor_pairs,
)

_FACTOR_NAMES = ("training", "demand", "scarcity", "impact")


# ---------------------------------------------------------------------------
# Core reconstruction
# ---------------------------------------------------------------------------

class MultiplierRun(TypedDict):
    occ6: list[str]                     # occupation codes, registry order
    multiplier: list[float]             # reconstructed reference multiplier per occ
    employment_k: list[float]           # BLS EP employment weight (thousands)
    weighted_mean: float                # employment-weighted mean multiplier
    spread_ratio: float                 # max/min multiplier
    clip_fraction: float                # fraction of occs with z clipped to 0 or 1
    factor_weights: tuple[float, float, float, float]
    impact_weights: tuple[float, float, float, float]


def _normalize(weights: tuple[float, ...]) -> tuple[float, float, float, float]:
    total = sum(weights)
    if total <= 0.0:
        raise ValueError(f"weights must have positive sum, got {weights}")
    return tuple(w / total for w in weights)  # type: ignore[return-value]


def reconstruct(
    rows: list[OccupationMultiplier] | None = None,
    factor_weights: tuple[float, float, float, float] = M_FACTOR_WEIGHTS,
    impact_weights: tuple[float, float, float, float] = M_IMPACT_SUBDOMAIN_WEIGHTS,
) -> MultiplierRun:
    """
    Recompute every occupation's reference multiplier under a given weighting.

    Rebuilds f_impact from the measured i_* sub-components under `impact_weights`,
    forms the composite under `factor_weights`, and applies the frozen geometric
    map. At the default (frozen) weights this reproduces the registry's
    `reference_multiplier` column to storage precision.

    Args:
        rows: registry rows; defaults to the full shipped registry.
        factor_weights: (training, demand, scarcity, impact); used as-is (not
            renormalized here — callers perturbing weights should renormalize
            first if they want a pure emphasis shift).
        impact_weights: (dependency, substitutability, harm, temporal).

    Returns:
        MultiplierRun with per-occupation multipliers and summary metrics.
    """
    if rows is None:
        rows = load_registry()
    z_span = M_COMPOSITE_Z_HI - M_COMPOSITE_Z_LO

    occ6: list[str] = []
    mult: list[float] = []
    emp: list[float] = []
    clipped = 0
    for r in rows:
        fi = impact_composite_from_subdomains(
            r["i_dependency"], r["i_substitutability"], r["i_harm"], r["i_temporal"],
            weights=impact_weights,
        )
        comp = composite_from_factors(
            r["f_training"], r["f_demand"], r["f_scarcity"], fi, weights=factor_weights,
        )
        z_raw = (comp - M_COMPOSITE_Z_LO) / z_span
        if z_raw <= 0.0 or z_raw >= 1.0:
            clipped += 1
        occ6.append(r["occ6"])
        mult.append(reference_multiplier(comp))
        emp.append(r["employment_k"])

    m_arr = np.asarray(mult)
    e_arr = np.asarray(emp)
    wmean = float(np.average(m_arr, weights=e_arr))
    return MultiplierRun(
        occ6=occ6,
        multiplier=mult,
        employment_k=emp,
        weighted_mean=wmean,
        spread_ratio=float(m_arr.max() / m_arr.min()),
        clip_fraction=clipped / len(rows),
        factor_weights=factor_weights,
        impact_weights=impact_weights,
    )


# ---------------------------------------------------------------------------
# Robustness metrics
# ---------------------------------------------------------------------------

def spearman(a: list[float], b: list[float]) -> float:
    """Spearman rank correlation (Pearson on ranks). No SciPy dependency."""
    x = np.asarray(a)
    y = np.asarray(b)
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    if rx.std() == 0.0 or ry.std() == 0.0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def pairwise_ratios(
    run: MultiplierRun,
    pairs: dict[str, tuple[str, str]] | None = None,
) -> dict[str, float]:
    """Multiplier ratio num/den for each named anchor pair (the robust,
    falsifiable claim). Silently skips pairs whose codes are absent."""
    if pairs is None:
        pairs = anchor_pairs()
    by_occ = dict(zip(run["occ6"], run["multiplier"]))
    out: dict[str, float] = {}
    for label, (num, den) in pairs.items():
        if num in by_occ and den in by_occ and by_occ[den] != 0.0:
            out[label] = by_occ[num] / by_occ[den]
    return out


def _band_verdict(weighted_mean: float) -> str:
    return "IN" if M_BAND_LOW <= weighted_mean <= M_BAND_HIGH else "BREACH"


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------

class PerturbationResult(TypedDict):
    label: str
    spearman_vs_baseline: float          # PRIMARY — falsifiable
    min_pairwise_ratio_drift: float      # PRIMARY — max |Δ ratio / ratio| over pairs
    weighted_mean: float                 # SECONDARY — convention
    band_verdict: str                    # SECONDARY — convention
    spread_ratio: float                  # SECONDARY — convention
    clip_fraction: float                 # SECONDARY — convention


def _perturbation(label: str, base: MultiplierRun, run: MultiplierRun) -> PerturbationResult:
    base_ratios = pairwise_ratios(base)
    new_ratios = pairwise_ratios(run)
    drift = 0.0
    for k, bv in base_ratios.items():
        if k in new_ratios and bv != 0.0:
            drift = max(drift, abs(new_ratios[k] - bv) / bv)
    return PerturbationResult(
        label=label,
        spearman_vs_baseline=spearman(base["multiplier"], run["multiplier"]),
        min_pairwise_ratio_drift=drift,
        weighted_mean=run["weighted_mean"],
        band_verdict=_band_verdict(run["weighted_mean"]),
        spread_ratio=run["spread_ratio"],
        clip_fraction=run["clip_fraction"],
    )


def sweep_factor_weights(
    rows: list[OccupationMultiplier] | None = None,
    delta: float = 0.10,
) -> list[PerturbationResult]:
    """Perturb each factor weight by ±delta (renormalized) and report robustness."""
    if rows is None:
        rows = load_registry()
    base = reconstruct(rows)
    results: list[PerturbationResult] = []
    for i, name in enumerate(_FACTOR_NAMES):
        for sign in (+1.0, -1.0):
            w = list(M_FACTOR_WEIGHTS)
            w[i] = max(0.0, w[i] + sign * delta)
            run = reconstruct(rows, factor_weights=_normalize(tuple(w)))
            tag = f"{name}{'+' if sign > 0 else '-'}{delta:g}"
            results.append(_perturbation(tag, base, run))
    return results


def sweep_impact_subdomain_weights(
    rows: list[OccupationMultiplier] | None = None,
    delta: float = 0.10,
) -> list[PerturbationResult]:
    """Perturb each impact sub-domain weight by ±delta (renormalized)."""
    if rows is None:
        rows = load_registry()
    base = reconstruct(rows)
    names = ("dependency", "substitutability", "harm", "temporal")
    results: list[PerturbationResult] = []
    for i, name in enumerate(names):
        for sign in (+1.0, -1.0):
            w = list(M_IMPACT_SUBDOMAIN_WEIGHTS)
            w[i] = max(0.0, w[i] + sign * delta)
            run = reconstruct(rows, impact_weights=_normalize(tuple(w)))
            tag = f"impact.{name}{'+' if sign > 0 else '-'}{delta:g}"
            results.append(_perturbation(tag, base, run))
    return results


def epsilon_arc(
    rows: list[OccupationMultiplier] | None = None,
    arc: tuple[float, ...] = (0.0, 0.40, 0.99),
) -> list[PerturbationResult]:
    """Reprice the whole economy under epoch_factor_weights(ε) across the arc.

    ε-coherence check: every ε in [0, 0.99] yields a valid economy-wide multiplier
    distribution. The ε=0.40 point equals the frozen baseline by construction.
    """
    if rows is None:
        rows = load_registry()
    base = reconstruct(rows)
    results: list[PerturbationResult] = []
    for eps in arc:
        run = reconstruct(rows, factor_weights=epoch_factor_weights(eps))
        results.append(_perturbation(f"epsilon={eps:g}", base, run))
    return results


class MonteCarloResult(TypedDict):
    n_draws: int
    concentration: float
    spearman_p5: float
    spearman_median: float
    spearman_min: float
    band_pass_fraction: float
    ratio_drift_p95: float


def monte_carlo_factor_weights(
    rows: list[OccupationMultiplier] | None = None,
    n_draws: int = 300,
    concentration: float = 50.0,
    seed: int = 0,
) -> MonteCarloResult:
    """Dirichlet Monte-Carlo over the factor-weight simplex (v5's 300-draw study).

    Draws weights ~ Dirichlet(concentration · M_FACTOR_WEIGHTS): higher
    concentration = tighter around the frozen split. Reports the distribution of
    the PRIMARY metric (Spearman vs frozen ordering) plus the fraction of draws
    whose employment-weighted mean stays in band (SECONDARY, convention).

    Deterministic given `seed`.
    """
    if rows is None:
        rows = load_registry()
    base = reconstruct(rows)
    rng = np.random.default_rng(seed)
    alpha = concentration * np.asarray(M_FACTOR_WEIGHTS)
    spearmans: list[float] = []
    drifts: list[float] = []
    in_band = 0
    base_ratios = pairwise_ratios(base)
    for _ in range(n_draws):
        w = _normalize(tuple(float(x) for x in rng.dirichlet(alpha)))
        run = reconstruct(rows, factor_weights=w)
        spearmans.append(spearman(base["multiplier"], run["multiplier"]))
        nr = pairwise_ratios(run)
        d = 0.0
        for k, bv in base_ratios.items():
            if k in nr and bv != 0.0:
                d = max(d, abs(nr[k] - bv) / bv)
        drifts.append(d)
        if _band_verdict(run["weighted_mean"]) == "IN":
            in_band += 1
    s = np.asarray(spearmans)
    return MonteCarloResult(
        n_draws=n_draws,
        concentration=concentration,
        spearman_p5=float(np.percentile(s, 5)),
        spearman_median=float(np.median(s)),
        spearman_min=float(s.min()),
        band_pass_fraction=in_band / n_draws,
        ratio_drift_p95=float(np.percentile(drifts, 95)),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

class SensitivityReport(TypedDict):
    baseline_weighted_mean: float
    baseline_spread_ratio: float
    factor_weight_sweep: list[PerturbationResult]
    impact_subdomain_sweep: list[PerturbationResult]
    epsilon_arc: list[PerturbationResult]
    monte_carlo: MonteCarloResult
    not_swept: list[str]


def sensitivity_report(
    rows: list[OccupationMultiplier] | None = None,
    delta: float = 0.10,
    n_draws: int = 300,
    seed: int = 0,
) -> SensitivityReport:
    """Full sensitivity report over the reconstructable CHOSEN constants.

    Rank ordering and pairwise ratios are the falsifiable claims; band/spread are
    reported as convention. See module docstring.
    """
    if rows is None:
        rows = load_registry()
    base = reconstruct(rows)
    return SensitivityReport(
        baseline_weighted_mean=base["weighted_mean"],
        baseline_spread_ratio=base["spread_ratio"],
        factor_weight_sweep=sweep_factor_weights(rows, delta=delta),
        impact_subdomain_sweep=sweep_impact_subdomain_weights(rows, delta=delta),
        epsilon_arc=epsilon_arc(rows),
        monte_carlo=monte_carlo_factor_weights(rows, n_draws=n_draws, seed=seed),
        not_swept=[
            "scarcity_leg_split (needs raw O/G legs)",
            "demand_subdomain_weights (registry carries only aggregated f_demand)",
            "normalization_method (needs stage_b re-run; ±2.8x per FALSIFIABILITY.md)",
        ],
    )
