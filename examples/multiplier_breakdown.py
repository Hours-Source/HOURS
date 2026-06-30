"""
Multiplier breakdown example — four-factor assessment across the automation arc.

Demonstrates:
  1. How epoch-adaptive alpha coefficients shift from skill-scarcity (early arc)
     to impact-dominance (late arc) as labor becomes rare
  2. The four-factor contribution to a tier multiplier at contrasting ε values
  3. The constitutional band check (mean ≈ [1.8, 2.1], hard cap 6.0)

Corresponding paper section: §"Condition II — Multiplier Band" and
§"The multiplier assessment function m(c) = 1 + α₁T + α₂D + α₃S + α₄I".

Run from repo root:
    python3 examples/multiplier_breakdown.py
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hours_eoh.core.multipliers import (
    epoch_alpha_weights,
    tier_multiplier,
    multiplier_band_check,
    assess_tier,
)


EPSILON_POINTS = [0.0, 0.40, 0.90, 0.99]

# A "mid-tier" worker profile: moderate across all four factors
EXAMPLE_TIER = {
    "training": 0.50,   # T(c): above-average training cost; 0=low-skill, 1=high-skill
    "demand":   0.60,   # D(c): above-average demand for this skill
    "scarcity": 0.40,   # S(c): moderate scarcity; endogenous, use lagged measure
    "impact":   0.55,   # I(c): above-average societal impact
}


def fmt_alpha(coeffs: tuple) -> str:
    labels = ["T", "D", "S", "I"]
    return "  ".join(f"α{l}={v:.3f}" for l, v in zip(labels, coeffs))


def main() -> None:
    print("Multiplier breakdown — four-factor assessment at canonical alpha weights")
    print()
    print("Worker profile (held constant across ε):")
    print(f"  T(training)={EXAMPLE_TIER['training']:.2f}  "
          f"D(demand)={EXAMPLE_TIER['demand']:.2f}  "
          f"S(scarcity)={EXAMPLE_TIER['scarcity']:.2f}  "
          f"I(impact)={EXAMPLE_TIER['impact']:.2f}")
    print()
    print("Formula: m(c) = 1 + α_T·T + α_D·D + α_S·S + α_I·I")
    print("         Σαᵢ = 5.0 (ALPHA_SCALE); weights epoch-adaptive to shift")
    print("         emphasis from training/scarcity early to impact late.")
    print()

    col_w = [6, 40, 8, 8]
    headers = ["ε", "alpha coefficients", "m(c)", "band?"]
    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))
    print(header_row)
    print("-" * len(header_row))

    for eps in EPSILON_POINTS:
        alphas = epoch_alpha_weights(eps)
        m = tier_multiplier(
            training=EXAMPLE_TIER["training"],
            demand=EXAMPLE_TIER["demand"],
            scarcity=EXAMPLE_TIER["scarcity"],
            impact=EXAMPLE_TIER["impact"],
            alpha_coefficients=alphas,
        )
        band = multiplier_band_check(m)
        band_label = band.get("status", "OK")

        row = [
            f"{eps:.2f}",
            fmt_alpha(alphas),
            f"{m:.3f}",
            band_label,
        ]
        print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))

    print()
    print("Key insight: alpha weights shift over the arc — at ε=0.99, impact (I)")
    print("             dominates because scarcity and training lose meaning when")
    print("             almost all labor is performed by machines.")
    print()

    # Full four-factor contribution breakdown at ε=0.40
    eps_ref = 0.40
    alphas = epoch_alpha_weights(eps_ref)  # returns (α_T, α_D, α_S, α_I)
    print(f"Four-factor contribution breakdown at ε={eps_ref}:")
    print()
    factors = ["training", "demand", "scarcity", "impact"]
    descriptions = [
        "training/skill-acquisition cost",
        "demand for this skill",
        "supply scarcity (lagged, endogenous)",
        "societal impact (EOH reduction + coverage + resilience)",
    ]
    labels = ["α_T × T", "α_D × D", "α_S × S", "α_I × I"]
    total_contrib = 0.0
    for alpha, factor, formula_label, description in zip(alphas, factors, labels, descriptions):
        score = EXAMPLE_TIER[factor]
        contrib = alpha * score
        total_contrib += contrib
        print(f"  {formula_label}: {alpha:.3f} × {score:.2f} = +{contrib:.4f}  [{description}]")
    print(f"  base:                                    1.0000")
    print(f"  ──────────────────────────────────────────────")
    m_total = 1.0 + total_contrib
    print(f"  m(c) = 1 + {total_contrib:.4f} = {m_total:.4f}")
    print()
    print("Run `eoh multiplier assess` for CLI access to the same calculation.")


if __name__ == "__main__":
    main()
