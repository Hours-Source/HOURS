"""
contestability — contestability invariant arc table and stress sweep.

  eoh contestability arc    [--regime increasing_returns|replicable] [--points N]
                            [--population F] [--trust-balance F] [--capital-stock F]
                            [--format table|csv|json]

  eoh contestability stress [--points N] [--population F] [--trust-balance F]
                            [--capital-stock F] [--format table|csv|json]

'arc' prints the full contestability sweep across ε: P (portable endowment),
K_entry (founding cost), χ = P/K_entry, φ (commonized fraction), τ = T/K,
levy_fraction (levy required vs automated output), and PASS/FAIL status.

'stress' forces increasing_returns regime and reports the first ε where χ < 1.

NOTE: levy_fraction > 1 means the required levy exceeds the entire automated
output — an adversarial finding, not a bug (reconciliation §8.3).
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.research.contestability import chi_arc, contestability_margin
from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_CHI_CRIT, CONTESTABILITY_CHI_WARN,
)
from utils.formatters import (
    bold, green, yellow, red, dim, fmt_float, fmt_eps, table as fmt_table,
)


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "contestability",
        help="Contestability invariant arc table and stress sweep (§8)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    sub2 = p.add_subparsers(dest="con_cmd", required=True)

    # ------------------------------------------------------------------ arc
    a = sub2.add_parser(
        "arc",
        help="Arc table: ε, P, K_entry, χ, φ, τ, levy_fraction, PASS/FAIL",
    )
    a.add_argument("--regime",
                   choices=["increasing_returns", "replicable"],
                   default="increasing_returns",
                   help="K_entry regime (default: increasing_returns / adversarial)")
    a.add_argument("--points", type=int, default=20, metavar="N",
                   help="Number of ε points (default: 20)")
    a.add_argument("--population", type=float, default=1_000_000.0)
    a.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH,
                   dest="trust_balance")
    a.add_argument("--capital-stock", type=float, default=CAPITAL_STOCK_DEFAULT,
                   dest="capital_stock")
    a.add_argument("--format", choices=["table", "csv", "json"],
                   default="table", dest="fmt")
    a.set_defaults(func=_arc)

    # ------------------------------------------------------------------ stress
    s = sub2.add_parser(
        "stress",
        help="Increasing-returns stress: find first ε where χ < 1",
    )
    s.add_argument("--points", type=int, default=20, metavar="N",
                   help="Number of ε points (default: 20)")
    s.add_argument("--population", type=float, default=1_000_000.0)
    s.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH,
                   dest="trust_balance")
    s.add_argument("--capital-stock", type=float, default=CAPITAL_STOCK_DEFAULT,
                   dest="capital_stock")
    s.add_argument("--format", choices=["table", "csv", "json"],
                   default="table", dest="fmt")
    s.set_defaults(func=_stress)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def _chi_color(chi: float) -> str:
    if chi >= CONTESTABILITY_CHI_WARN:
        return green(f"{chi:.3f}")
    if chi >= CONTESTABILITY_CHI_CRIT:
        return yellow(f"{chi:.3f}")
    return red(f"{chi:.3f}")


def _status_color(status: str) -> str:
    if status == "OK":
        return green(status)
    if status == "WARN":
        return yellow(status)
    return red(status)


def _levy_cell(fraction: float | None) -> str:
    if fraction is None:
        return dim("N/A")
    if fraction > 1.0:
        return red(f"{fraction:.1f}×")
    return green(f"{fraction:.3f}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _arc(args: argparse.Namespace) -> None:
    rows_data = chi_arc(
        n_points=args.points,
        regime=args.regime,
        population=args.population,
        trust_balance=args.trust_balance,
        capital_stock=args.capital_stock,
    )

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    if args.fmt == "csv":
        if rows_data:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows_data[0].keys()))
            writer.writeheader()
            writer.writerows(rows_data)
        return

    n_pass = sum(1 for r in rows_data if r["status"] != "CRIT")
    n_total = len(rows_data)
    regime_label = green("replicable") if args.regime == "replicable" else yellow("increasing_returns (adversarial)")
    print(bold(f"Contestability arc — {regime_label}  [{args.points} points]"))
    print(dim(
        f"  χ = P / K_entry ≥ {CONTESTABILITY_CHI_CRIT}  required   "
        f"WARN below {CONTESTABILITY_CHI_WARN}   "
        f"levy_fraction > 1 = infeasible (adversarial finding, not a bug)"
    ))
    print()

    table_rows = []
    for r in rows_data:
        table_rows.append([
            fmt_eps(r["epsilon"]),
            fmt_float(r["p"], decimals=0),
            fmt_float(r["k_entry"], decimals=0),
            _chi_color(r["chi_population_avg"]),
            f"{r['phi']:.3f}",
            f"{r['tau']:.4f}",
            _levy_cell(r["levy_fraction"]),
            _status_color(r["status"]),
        ])

    print(fmt_table(
        ["ε", "P (TEH/p)", "K_entry", "χ_avg", "φ", "τ=T/K", "levy_frac", "status"],
        table_rows,
    ))
    print()
    print(dim(f"  {n_pass}/{n_total} points pass χ ≥ {CONTESTABILITY_CHI_CRIT}"))


def _stress(args: argparse.Namespace) -> None:
    rows_data = chi_arc(
        n_points=args.points,
        regime="increasing_returns",
        population=args.population,
        trust_balance=args.trust_balance,
        capital_stock=args.capital_stock,
    )

    # Find breach point
    breach = next((r for r in rows_data if r["chi_population_avg"] < CONTESTABILITY_CHI_CRIT), None)
    min_chi_row = min(rows_data, key=lambda r: r["chi_population_avg"])

    if args.fmt == "json":
        out = {
            "regime": "increasing_returns",
            "breach_epsilon": breach["epsilon"] if breach else None,
            "min_chi": min_chi_row["chi_population_avg"],
            "min_chi_epsilon": min_chi_row["epsilon"],
            "n_points_breach": sum(1 for r in rows_data if r["chi_population_avg"] < CONTESTABILITY_CHI_CRIT),
            "trajectory": rows_data,
        }
        print(json.dumps(out, indent=2))
        return

    if args.fmt == "csv":
        if rows_data:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows_data[0].keys()))
            writer.writeheader()
            writer.writerows(rows_data)
        return

    print(bold("Contestability stress — increasing_returns regime"))
    print(dim("  K_entry rises with ε; P erodes as labor income falls; Trust balance held fixed."))
    print()

    if breach:
        breach_eps = fmt_eps(breach["epsilon"])
        breach_chi = f"{breach['chi_population_avg']:.3f}"
        print(f"  First breach: {red('χ < 1 at ε = ' + breach_eps)}  "
              f"(χ = {red(breach_chi)})")
    else:
        print(f"  {green('No breach')} — χ ≥ 1 across all {args.points} points.")
    min_eps = fmt_eps(min_chi_row["epsilon"])
    print(f"  Minimum χ: {_chi_color(min_chi_row['chi_population_avg'])} at ε = {min_eps}")
    print()

    table_rows = []
    for r in rows_data:
        table_rows.append([
            fmt_eps(r["epsilon"]),
            fmt_float(r["p"], decimals=0),
            fmt_float(r["k_entry"], decimals=0),
            _chi_color(r["chi_population_avg"]),
            _status_color(r["status"]),
        ])

    print(fmt_table(
        ["ε", "P (TEH/p)", "K_entry", "χ_avg", "status"],
        table_rows,
    ))
    print()
    n_breach = sum(1 for r in rows_data if r["chi_population_avg"] < CONTESTABILITY_CHI_CRIT)
    print(dim(f"  {n_breach}/{args.points} points breach χ < {CONTESTABILITY_CHI_CRIT}"))
