"""
Contestability chart example — χ(ε) = P/K_entry across the automation arc.

Demonstrates:
  1. The contestability margin χ(ε) under two K_entry regimes:
     - replicable (K_entry falls with ε) → χ holds above 1 across the arc
     - increasing_returns (K_entry rises with ε) → χ breaches 1 at high ε
  2. The commonized fraction φ(ε): automation value held in common
  3. The adversarial finding: levy required for Piketty-inversion >> automated output

Corresponding paper section: hours-reconciliation.md §8 (contestability invariant),
§8.3 (the adversarial finding), §8.5 (regime uncertainty).

Run from repo root:
    python3 examples/contestability_chart.py
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hours_eoh.research.contestability import chi_arc
from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_CHI_CRIT,
)

POPULATION = 1_000_000
TRUST = TRUST_BASE_TEH
CAPITAL = CAPITAL_STOCK_DEFAULT
N_POINTS = 11


def fmt_chi(chi: float) -> str:
    flag = "" if chi >= CONTESTABILITY_CHI_CRIT else " ← BREACH"
    return f"{chi:.3f}{flag}"


def fmt_levy(fraction: float | None) -> str:
    if fraction is None:
        return "N/A (ε=0)"
    if fraction > 1.0:
        return f"{fraction:.1f}× (infeasible)"
    return f"{fraction:.3f}"


def main() -> None:
    print("Contestability chart — χ(ε) = P / K_entry across the automation arc")
    print()
    print(f"Population: {POPULATION:,}  |  Trust: {TRUST/1e9:.0f}B TEH  |  Capital: {CAPITAL/1e9:.0f}B TEH")
    print(f"Invariant: χ ≥ {CONTESTABILITY_CHI_CRIT} required at all ε")
    print()

    for regime in ["replicable", "increasing_returns"]:
        rows = chi_arc(n_points=N_POINTS, regime=regime, population=POPULATION,
                       trust_balance=TRUST, capital_stock=CAPITAL)

        regime_label = ("replicable (K_entry falls with ε — optimistic)"
                        if regime == "replicable"
                        else "increasing_returns (K_entry rises with ε — adversarial)")
        print(f"Regime: {regime_label}")
        print()

        col_w = [6, 10, 10, 10, 8, 20]
        headers = ["ε", "P (TEH)", "K_entry", "χ_avg", "φ", "levy_fraction"]
        header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))
        print(header_row)
        print("-" * len(header_row))

        for row in rows:
            r = [
                f"{row['epsilon']:.2f}",
                f"{row['p']:.0f}",
                f"{row['k_entry']:.0f}",
                fmt_chi(row["chi_population_avg"]),
                f"{row['phi']:.3f}",
                fmt_levy(row["levy_fraction"]),
            ]
            print("  ".join(v.ljust(w) for v, w in zip(r, col_w)))

        n_breach = sum(1 for r in rows if r["chi_population_avg"] < CONTESTABILITY_CHI_CRIT)
        print()
        if n_breach == 0:
            print(f"  Result: χ ≥ {CONTESTABILITY_CHI_CRIT} at all {N_POINTS} points — invariant holds.")
        else:
            breach = next(r for r in rows if r["chi_population_avg"] < CONTESTABILITY_CHI_CRIT)
            print(f"  Result: {n_breach}/{N_POINTS} points breach χ < {CONTESTABILITY_CHI_CRIT}. "
                  f"First breach at ε={breach['epsilon']:.2f} (χ={breach['chi_population_avg']:.3f})")
        print()

    print("─" * 72)
    print()
    print("The adversarial finding (levy_fraction >> 1):")
    print()
    print("  The Piketty-inversion condition (Trust must grow faster than private capital)")
    print("  cannot be met by a levy on automated output alone at canonical defaults.")
    print("  At ε=0.40, levy_fraction ≈ 21× — the required levy exceeds the entire")
    print("  automated output. This means commonization of automation value must happen")
    print("  through structural ownership (φ → 1 via collective charter), not only")
    print("  through after-the-fact taxation. This is not a model error; it is the")
    print("  core finding that motivated reconciliation §8.3.")
    print()
    print("Run `eoh contestability arc` and `eoh contestability stress` for CLI access.")
    print("Run `eoh dashboard` to see χ status in the system health snapshot.")


if __name__ == "__main__":
    main()
