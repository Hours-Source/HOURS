"""
Arc sweep example — EOH → TEH pipeline across the automation arc.

Demonstrates:
  1. How total EOH grows with ε even as human labor shrinks (the automation paradox)
  2. How TEH creation peaks near mid-arc and collapses at high ε
  3. Fiscal solvency across the arc at canonical defaults

Corresponding paper section: §"The EOH → TEH pipeline" and §"Condition I — ledger identity".

Run from repo root:
    python3 examples/arc_sweep.py
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.core.prices import basket_price
from hours_eoh.data import TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT

POPULATION = 1_000_000
TRUST = TRUST_BASE_TEH
EPSILON_POINTS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.99]


def fmt(n: float, decimals: int = 1) -> str:
    if n >= 1e9:
        return f"{n/1e9:{'.'+str(decimals)+'f'}}B"
    if n >= 1e6:
        return f"{n/1e6:{'.'+str(decimals)+'f'}}M"
    if n >= 1e3:
        return f"{n/1e3:{'.'+str(decimals)+'f'}}K"
    return f"{n:.{decimals}f}"


def main() -> None:
    col_w = [6, 12, 12, 10, 8, 12, 8]
    headers = ["ε", "total_EOH", "human_EOH", "reg_EOH", "TEH/yr", "basket_price", "solvent"]

    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))
    print("Arc sweep — EOH → TEH pipeline at canonical defaults (population=1M)")
    print()
    print(header_row)
    print("-" * len(header_row))

    for eps in EPSILON_POINTS:
        pipe = eoh_to_teh_pipeline(eps, population=POPULATION)
        labor_income = pipe["teh_created"]

        snap = fiscal_snapshot(
            trust_balance=TRUST,
            labor_income=labor_income,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT * (1.0 + 2.0 * eps),
            capital_age_ratio=0.30 + 0.20 * eps,
            population=POPULATION,
            epsilon=eps,
        )

        bp = basket_price(eps)
        solvent = "YES" if snap["solvent"] else "NO"

        row = [
            f"{eps:.2f}",
            fmt(pipe["total_eoh"]),
            fmt(pipe["human_eoh"]),
            fmt(pipe["registered_eoh"]),
            fmt(pipe["teh_created"]),
            f"{bp:.1f} TEH/yr",
            solvent,
        ]
        print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))

    print()
    print("Key insight: total_EOH rises with ε (growing capital/knowledge complexity)")
    print("             human_EOH = total × (1−ε) falls; TEH peaks near ε=0.40–0.60")
    print("             basket_price falls monotonically → purchasing power rises with ε")
    print(f"             Trust balance held constant at {fmt(TRUST)} TEH throughout")


if __name__ == "__main__":
    main()
