"""
sensitivity — parameter sensitivity analysis.

  eoh sensitivity fiscal --parameter levy_rate --values 0.1,0.15,0.2 [--epsilon ε]
  eoh sensitivity arc    [--start ε] [--end ε] [--points N] [--delta D]
  eoh sensitivity delta  --epsilon ε --delta D
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.scenarios.sensitivity import (
    fiscal_parameter_sweep,
    eoh_arc_sensitivity,
    epsilon_delta_sensitivity,
)
from hours_eoh.data import TRUST_BASE_TEH

from utils.formatters import bold, fmt_float, fmt_eps, table as fmt_table


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("sensitivity", help="Parameter sensitivity analysis")
    sub2 = p.add_subparsers(dest="sens_cmd", required=True)

    # -- fiscal
    fp = sub2.add_parser("fiscal", help="Sweep a fiscal parameter at a given ε")
    fp.add_argument("--parameter", required=True, metavar="PARAM",
                    help="Parameter to sweep (levy_rate, dep_rate, div_rate, "
                         "floor_fraction, capital_age_ratio)")
    fp.add_argument("--values", required=True, metavar="V1,V2,...",
                    help="Comma-separated list of values to sweep")
    fp.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    fp.add_argument("--population", type=float, default=1_000_000.0)
    fp.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH)
    fp.add_argument("--format", choices=["table", "csv", "json"],
                    default="table", dest="fmt")
    fp.set_defaults(func=_fiscal)

    # -- arc
    ap = sub2.add_parser("arc", help="Cross-sectional metrics across the ε arc")
    ap.add_argument("--start", type=float, default=0.0, metavar="ε")
    ap.add_argument("--end", type=float, default=0.99, metavar="ε")
    ap.add_argument("--points", type=int, default=10)
    ap.add_argument("--delta", type=float, default=0.05,
                    help="ε increment used for each delta calculation (default: 0.05)")
    ap.add_argument("--format", choices=["table", "csv", "json"],
                    default="table", dest="fmt")
    ap.set_defaults(func=_arc)

    # -- delta
    dp = sub2.add_parser("delta", help="Cross-sectional ε-delta sensitivity at a point")
    dp.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    dp.add_argument("--delta", type=float, default=0.05,
                    help="ε increment (default: 0.05)")
    dp.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    dp.set_defaults(func=_delta)


# ---------------------------------------------------------------------------

def _fiscal(args: argparse.Namespace) -> None:
    values = [float(v.strip()) for v in args.values.split(",")]
    result = fiscal_parameter_sweep(
        parameter=args.parameter,
        values=values,
        epsilon=args.epsilon,
        population=args.population,
        trust_balance=args.trust_balance,
    )

    rows_data = result.get("results", [])
    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold(f"Fiscal sensitivity — {args.parameter} at ε={fmt_eps(args.epsilon)}"))
    print(f"  Solvent across sweep: {result.get('solvent_range', '—')}")
    if rows_data:
        keys = list(rows_data[0].keys())
        if args.fmt == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows_data)
            return
        rows = [[str(r.get(k, "")) for k in keys] for r in rows_data]
        print(fmt_table(keys, rows))


def _arc(args: argparse.Namespace) -> None:
    rows_data = eoh_arc_sensitivity(
        epsilon_start=args.start,
        epsilon_end=args.end,
        n_points=args.points,
        delta_epsilon=args.delta,
    )

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    if args.fmt == "csv":
        if rows_data:
            # Flatten metrics dict into top-level keys
            flat = [_flatten_arc_row(r) for r in rows_data]
            writer = csv.DictWriter(sys.stdout, fieldnames=list(flat[0].keys()))
            writer.writeheader()
            writer.writerows(flat)
        return

    print(bold(f"Arc sensitivity — ε [{args.start}, {args.end}]  Δε={args.delta}"))
    flat = [_flatten_arc_row(r) for r in rows_data]
    if flat:
        keys = list(flat[0].keys())
        rows = [[str(r.get(k, "")) for k in keys] for r in flat]
        print(fmt_table(keys, rows))


def _flatten_arc_row(r: dict) -> dict:
    out: dict = {
        "base_ε": fmt_eps(r.get("base_epsilon", 0.0)),
        "new_ε":  fmt_eps(r.get("new_epsilon", 0.0)),
        "Δε":     fmt_eps(r.get("delta_epsilon", 0.0)),
    }
    metrics = r.get("metrics", {})
    if isinstance(metrics, dict):
        for k, m in metrics.items():
            if isinstance(m, dict):
                out[f"{k}_Δ"] = fmt_float(float(m.get("delta", 0)))
                out[f"{k}_%"] = f"{m.get('pct_change', 0):.1f}%"
            else:
                out[k] = fmt_float(float(m)) if isinstance(m, (int, float)) else str(m)
    return out


def _delta(args: argparse.Namespace) -> None:
    result = epsilon_delta_sensitivity(
        base_epsilon=args.epsilon,
        delta_epsilon=args.delta,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold(f"ε-delta sensitivity: ε={fmt_eps(args.epsilon)} → "
               f"{fmt_eps(result.get('new_epsilon', args.epsilon + args.delta))}  "
               f"Δε={args.delta}"))
    metrics = result.get("metrics", {})
    if isinstance(metrics, dict):
        rows = []
        for name, m in metrics.items():
            if isinstance(m, dict):
                rows.append([
                    name,
                    fmt_float(float(m.get("base", 0))),
                    fmt_float(float(m.get("new", 0))),
                    fmt_float(float(m.get("delta", 0))),
                    f"{m.get('pct_change', 0):.2f}%",
                ])
        print(fmt_table(["metric", "base", "new", "Δ", "pct_change"], rows))
    else:
        print(fmt_table(
            ["key", "value"],
            [[str(k), str(v)] for k, v in result.items()]
        ))
