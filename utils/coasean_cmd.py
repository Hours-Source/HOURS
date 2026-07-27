"""
coasean — Coasean collective federation CLI command (research-tier, §§6–7).

Sub-commands:
  n1-check     Verify N=1 regression anchor at ε ∈ {0, 0.40, 0.99}
  count        Print emergent collective count across the ε arc
  federation   Show per-collective pipeline + fiscal summary at a given ε

All output is clearly marked EXPERIMENTAL — research API, not stable.
"""

from __future__ import annotations
import argparse
import json

from utils.formatters import table, fmt_float, fmt_eps, green, yellow, red


def build_parser(sub: argparse.Action) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "coasean",
        help="[EXPERIMENTAL] Coasean collective federation mechanics (§§6–7)",
    )
    p.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    csub = p.add_subparsers(dest="coasean_cmd", metavar="SUBCOMMAND")
    csub.required = True

    # n1-check
    n1 = csub.add_parser("n1-check", help="Verify N=1 regression anchor")
    n1.add_argument("--population", type=float, default=1_000_000.0)
    n1.set_defaults(func=run_n1_check)

    # count
    cnt = csub.add_parser("count", help="Emergent collective count across the ε arc")
    cnt.add_argument("--points", type=int, default=20)
    cnt.set_defaults(func=run_count)

    # federation
    fed = csub.add_parser("federation", help="Per-collective snapshot at a given ε")
    fed.add_argument("--epsilon", type=float, default=0.40)
    fed.add_argument("--population", type=float, default=1_000_000.0)
    fed.add_argument("--n", type=int, default=None,
                     help="Override collective count (default: emergent N(ε))")
    fed.set_defaults(func=run_federation)

    # simulate
    sim = csub.add_parser("simulate",
                          help="Multi-period federation arc with three-regime inflation")
    sim.add_argument("--periods", type=int, default=10,
                     help="Number of periods (default: 10)")
    sim.add_argument("--epsilon-start", type=float, default=0.10, dest="eps_start")
    sim.add_argument("--epsilon-end",   type=float, default=0.99, dest="eps_end")
    sim.add_argument("--population",    type=float, default=1_000_000.0)
    sim.add_argument("--heterogeneity", type=float, default=0.10,
                     help="Std dev of ecosystem health variation (default: 0.10)")
    sim.add_argument("--seed",          type=int,   default=42)
    sim.add_argument("--dynamics", action="store_true",
                     help="Enable Phase 3 Trust/capital evolution")
    sim.add_argument("--g-priv",    type=float, default=0.0, dest="g_priv",
                     help="Private capital growth rate per period (with --dynamics)")
    sim.add_argument("--levy-rate", type=float, default=0.0, dest="levy_rate",
                     help="Common-fund levy on automated output (with --dynamics)")
    sim.add_argument("--commons", action="store_true",
                     help="Enable Phase 4 two-tier commons (escheat, tithe, per-collective χ)")
    sim.add_argument("--commons-tithe", type=float, default=None, dest="commons_tithe",
                     help="Levy fraction routed to the federation commons "
                          "(default: COASEAN_COMMONS_TITHE = 0.03)")
    sim.add_argument("--regime", choices=["increasing_returns", "replicable"],
                     default="increasing_returns",
                     help="K_entry regime for per-collective χ (with --commons)")
    sim.add_argument("--commons-dividend", action="store_true", dest="commons_dividend",
                     help="Phase 4b closure (§8.8 M1): commons pays a universal "
                          "unvested dividend that feeds χ")
    sim.add_argument("--commons-start", type=float, default=0.0, dest="commons_start",
                     help="Initial commons balance in TEH (seed; see "
                          "commons_seed_required() — ~1.8e7 at defaults)")
    sim.set_defaults(func=run_simulate)

    p.set_defaults(func=lambda args: p.print_help())


def run_n1_check(args: argparse.Namespace) -> None:
    from hours_eoh.research.coasean import n1_regression_anchor

    print("EXPERIMENTAL — research/coasean.py (Workstream D Phase 1)\n")

    eps_list = [0.0, 0.40, 0.99]
    rows_data = []
    for eps in eps_list:
        res = n1_regression_anchor(
            epsilon=eps,
            population=args.population,
        )
        rows_data.append({
            "epsilon":           eps,
            "ref_teh":           res["ref_teh_created"],
            "fed_teh":           res["fed_teh_created"],
            "teh_delta":         res["teh_created_delta"],
            "pipeline_match":    res["pipeline_match"],
            "solvent_match":     res["solvent_match"],
        })

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    headers = ["ε", "ref_teh", "fed_teh", "teh_delta", "pipeline_match", "solvent_match"]
    rows = []
    for r in rows_data:
        ok_p = "PASS" if r["pipeline_match"] else "FAIL"
        ok_s = "PASS" if r["solvent_match"] else "FAIL"
        rows.append([
            fmt_eps(r["epsilon"]),
            fmt_float(r["ref_teh"]),
            fmt_float(r["fed_teh"]),
            f"{r['teh_delta']:.2e}",
            ok_p,
            ok_s,
        ])
    print(table(headers, rows))
    all_ok = all(r["pipeline_match"] and r["solvent_match"] for r in rows_data)
    status = "ALL PASS — N=1 regression anchor holds" if all_ok else "FAILURES DETECTED"
    print(f"\n{status}")


def run_count(args: argparse.Namespace) -> None:
    from hours_eoh.research.coasean import coasean_collective_count

    print("EXPERIMENTAL — research/coasean.py\n")

    n_points = args.points
    rows_data = []
    for i in range(n_points):
        eps = i / (n_points - 1) * 0.99 if n_points > 1 else 0.40
        n = coasean_collective_count(eps)
        rows_data.append({"epsilon": eps, "n_collectives": n})

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    headers = ["ε", "N(ε)"]
    rows = [[fmt_eps(r["epsilon"]), str(r["n_collectives"])] for r in rows_data]
    print(table(headers, rows))


def run_simulate(args: argparse.Namespace) -> None:
    from hours_eoh.research.coasean import simulate_federation
    from hours_eoh.data import COASEAN_COMMONS_TITHE, CONTESTABILITY_CHI_CRIT, CONTESTABILITY_CHI_WARN

    print("EXPERIMENTAL — research/coasean.py (three-regime inflation, §7; commons, §8.7)\n")
    tithe = COASEAN_COMMONS_TITHE if args.commons_tithe is None else args.commons_tithe
    extras = ""
    if args.dynamics:
        extras += f"  dynamics: levy={args.levy_rate:.2f} g_priv={args.g_priv:.3f}"
    if args.commons:
        extras += f"  commons: tithe={tithe:.3f} regime={args.regime}"
    print(
        f"Simulating {args.periods} periods  "
        f"ε: {args.eps_start:.3f} → {args.eps_end:.3f}  "
        f"heterogeneity={args.heterogeneity:.2f}  seed={args.seed}{extras}\n"
    )

    trajectory = [
        args.eps_start + (args.eps_end - args.eps_start) * i / max(args.periods - 1, 1)
        for i in range(args.periods)
    ]

    records = simulate_federation(
        epsilon_trajectory=trajectory,
        population=args.population,
        heterogeneity=args.heterogeneity,
        seed=args.seed,
        dynamics=args.dynamics,
        g_priv=args.g_priv,
        levy_rate=args.levy_rate,
        commons=args.commons,
        commons_tithe=tithe,
        regime=args.regime,
        commons_dividend=args.commons_dividend,
        commons_start=args.commons_start,
    )

    if args.fmt == "json":
        print(json.dumps(records, indent=2))
        return

    headers = ["t", "ε", "N", "total_teh", "within_infl", "inter_infl", "sys_infl", "solvent"]
    if args.dynamics:
        headers += ["T", "τ", "piketty"]
    if args.commons:
        headers += ["commons", "escheat", "χ_marg_min", "χ_status",
                    "entry_cap", "exit_fin"]
    rows = []
    for r in records:
        row = [
            str(r["period"]),
            f"{r['epsilon']:.3f}",
            str(r["n_collectives"]),
            fmt_float(r["total_teh"]),
            f"{r['within_inflation']:.4f}",
            f"{r['inter_inflation']:.4f}",
            f"{r['system_inflation']:.4f}",
            "Y" if r["all_solvent"] else "N",
        ]
        if args.dynamics:
            piketty = r["piketty_ok"]
            row += [
                fmt_float(r["trust_balance"]),
                f"{r['tau']:.4f}",
                "-" if piketty is None else ("Y" if piketty else "N"),
            ]
        if args.commons:
            chi_m = r["chi_marginal_min"]
            chi_cell = f"{chi_m:.3f}"
            if chi_m < CONTESTABILITY_CHI_CRIT:
                chi_cell = red(chi_cell)
            elif chi_m < CONTESTABILITY_CHI_WARN:
                chi_cell = yellow(chi_cell)
            else:
                chi_cell = green(chi_cell)
            fin = r["exit_financeable"]
            fin_cell = "-" if fin is None else (green("Y") if fin else red("N"))
            row += [
                fmt_float(r["commons_balance"]),
                fmt_float(r["escheat_this_period"]),
                chi_cell,
                r["chi_status_worst"],
                "-" if r["entry_capacity"] is None else f"{r['entry_capacity']:.1f}",
                fin_cell,
            ]
        rows.append(row)
    print(table(headers, rows))
    print(
        "\nwithin_infl = 0 always (floor-impossibility, structural)"
        "\ninter_infl  = exchange-rate drift between collectives"
        "\nsys_infl    = inter × (1−ε) → 0 as ε → 1 (§7 asymptote)"
    )
    if args.commons:
        print(
            "χ_marg_min  = worst collective's tenure-0 member (§8.7) — "
            "the invariant requires ≥ 1"
            "\nentry_cap   = viable foundings the commons can underwrite (§8.8 M2)"
            "\nexit_fin    = χ_marg_min ≥ 1 OR entry_cap ≥ 1 (proposed §8.8 "
            "combined invariant)"
        )


def run_federation(args: argparse.Namespace) -> None:
    from hours_eoh.research.coasean import make_federation, coasean_collective_count
    from hours_eoh.data import TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT

    print("EXPERIMENTAL — research/coasean.py\n")

    eps = args.epsilon
    n = args.n
    if n is None:
        n = coasean_collective_count(eps)

    print(f"ε = {eps:.3f}  |  N = {n} collectives  |  population = {args.population:,.0f}\n")

    fed = make_federation(
        epsilon=eps,
        n=n,
        population=args.population,
        trust_balance=TRUST_BASE_TEH,
        capital_stock_teh=CAPITAL_STOCK_DEFAULT,
    )

    rows_data = []
    for c in fed:
        rows_data.append({
            "id":       c.collective_id,
            "pop":      c.population,
            "teh":      c.pipeline.get("teh_created", 0.0),
            "reserve":  c.reserve,
            "solvent":  c.fiscal.get("solvent", False),
            "surplus":  c.fiscal.get("trust", {}).get("surplus_deficit", 0.0),
        })

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    headers = ["id", "population", "teh_created", "reserve", "solvent", "surplus"]
    rows = []
    for r in rows_data:
        rows.append([
            str(r["id"]),
            fmt_float(r["pop"]),
            fmt_float(r["teh"]),
            fmt_float(r["reserve"]),
            "Y" if r["solvent"] else "N",
            fmt_float(r["surplus"]),
        ])
    print(table(headers, rows))
