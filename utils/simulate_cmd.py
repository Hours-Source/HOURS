"""
simulate — multi-period simulation runner.

  eoh simulate [--epsilon ε] [--periods N] [--epsilon-delta RATE]
               [--population N] [--format table|csv|json]

Runs run_simulation() and prints period-by-period results.
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.core.simulation import make_economy_state, run_simulation
from hours_eoh.data import TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT

from utils.formatters import bold, fmt_float, fmt_eps, table as fmt_table

# Key columns for the default table view (from period_results)
_TABLE_COLS = [
    "period", "epsilon", "total_eoh", "registered_eoh",
    "teh_created", "teh_destroyed",
]
# Supplemental columns from state dict (merged in)
_STATE_COLS = ["trust_balance", "ecosystem_health", "capital_age_ratio"]


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("simulate", help="Run a multi-period simulation")
    p.add_argument("--epsilon", type=float, default=0.40, metavar="ε",
                   help="Starting ε (default: 0.40)")
    p.add_argument("--periods", type=int, default=20,
                   help="Number of periods to simulate (default: 20)")
    p.add_argument("--epsilon-delta", type=float, default=0.01, metavar="RATE",
                   help="ε increment per period passed to simulate_period (default: 0.01)")
    p.add_argument("--population", type=float, default=1_000_000.0)
    p.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH)
    p.add_argument("--capital-stock", type=float, default=CAPITAL_STOCK_DEFAULT)
    p.add_argument("--format", choices=["table", "csv", "json"],
                   default="table", dest="fmt")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    state = make_economy_state(
        epsilon=args.epsilon,
        population=args.population,
        trust_balance=args.trust_balance,
        capital_stock_teh=args.capital_stock,
    )

    result = run_simulation(
        initial_state=state,
        n_periods=args.periods,
        epsilon_delta=args.epsilon_delta,
    )

    period_results = result.get("period_results", [])
    states = result.get("states", [])

    # Merge state columns into period results for display
    merged = []
    for i, pr in enumerate(period_results):
        row = dict(pr)
        if i < len(states):
            for col in _STATE_COLS:
                row[col] = states[i].get(col, "")
        merged.append(row)

    if args.fmt == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    if args.fmt == "csv":
        if not merged:
            return
        keys = list(merged[0].keys())
        writer = csv.DictWriter(sys.stdout, fieldnames=keys)
        writer.writeheader()
        for row in merged:
            writer.writerow({k: str(v) for k, v in row.items()})
        return

    # table — select key columns
    display_cols = _TABLE_COLS + _STATE_COLS
    available = [c for c in display_cols if c in (merged[0] if merged else {})]
    rows = []
    for r in merged:
        row = []
        for col in available:
            v = r.get(col, "")
            if col == "epsilon":
                row.append(fmt_eps(float(v)))
            elif col in ("total_eoh", "registered_eoh", "teh_created",
                         "teh_destroyed", "trust_balance"):
                row.append(fmt_float(float(v)) if v != "" else "—")
            elif col in ("ecosystem_health", "capital_age_ratio"):
                row.append(f"{float(v):.3f}" if v != "" else "—")
            else:
                row.append(str(v))
        rows.append(row)

    summary = result.get("summary", {})
    solvent = result.get("solvent_all", True)
    print(bold(f"Simulation — {args.periods} periods from ε={fmt_eps(args.epsilon)}  "
               f"solvent={'Y' if solvent else 'N'}"))
    if summary:
        print(f"  TEH created total: {fmt_float(float(summary.get('total_teh_created', 0)))}"
              f"  ε range: {summary.get('epsilon_range', [])}")
    print()
    print(fmt_table(available, rows))
