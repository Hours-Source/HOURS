"""
contestability — contestability invariant arc table and stress sweep.

  eoh contestability arc    [--regime increasing_returns|replicable] [--points N]
                            [--population F] [--trust-balance F] [--capital-stock F]
                            [--format table|csv|json]

  eoh contestability stress [--points N] [--population F] [--trust-balance F]
                            [--capital-stock F] [--format table|csv|json]

  eoh contestability levy   [--regime increasing_returns|replicable] [--points N]
                            [--population F] [--capital-stock F] [--chi-target F]
                            [--format table|csv|json]

  eoh contestability recal  [--regime increasing_returns|replicable] [--points N]
                            [--phi-policy target|dilution|escalated]
                            [--estate-escheat F] [--population F]
                            [--capital-output-ratio F] [--epsilon-rate F]
                            [--exit-horizon F] [--min-viable-population F]
                            [--format table|csv|json]

  eoh contestability formation [--priority share|dividend] [--years N]
                            [--regime ...] [--hurdle F] [--full-supply F]
                            [--escalation] [--charter-share F]
                            [--min-viable-population F] [--format table|csv|json]

  eoh contestability audit  [--terms-json PATH|-] [--vesting-years F]
                            [--admission-cost F] [--exit-notice-years F]
                            [--minimum-hours F] [--dividend-fraction F]
                            [--epsilon F] [--collective-trust F]
                            [--collective-population F] [--federation-population F]
                            [--commons-balance F]
                            [--regime increasing_returns|replicable]
                            [--format table|json]

'arc' prints the full contestability sweep across ε: P (portable endowment),
K_entry (founding cost), χ = P/K_entry, φ (commonized fraction), τ = T/K,
levy_fraction (levy required vs automated output), and PASS/FAIL status.

'stress' forces increasing_returns regime and reports the first ε where χ < 1.

'levy' prints the derived common-fund levy schedule (§8.2): the Trust balance
required at each ε to hold χ ≥ target, the per-step levy needed to fund it,
and whether the levy is feasible from automated output.

'recal' prints the §8.9/§8.9b recalibrated arc: the commons owns share φ(ε)
of an ε-consistent capital stock K(ε) = K₀ + ν·Y(ε), so τ = φ ≤ 1 with
dτ/dε ≥ 0 structural; exit is financed by labor (low ε), commons
underwriting (mid ε), or dividend savings (high ε) — t_exit ≤ horizon
replaces the flow/stock χ (§8.8 RC4). --phi-policy selects the doctrine:
'dilution' (default, §8.9b charter formation — the commons' share attaches
to NEW capital at commissioning; private capital is never sold down, so φ
caps at ≈0.66 by ε=0.99), 'target' (§8.9a purchase model, regression
anchor), or 'escalated' (dilution + the charter escalation clause: full
generational conversion if observed concentration threatens exit; never
fires at canonical defaults).

'formation' runs the §8.9c formation-feedback simulation: capital formation
is FINANCED or it does not happen (private supply falls as the charter share
rises; the commons co-funds from net income per --priority), and ε is
DERIVED from the capital actually formed. Reports the year-by-year path and
the verdict: pace vs the canonical 50-yr arc, stall/crawl, the
feedback-consistent dividend, and whether exit stays financeable.
--charter-share 0 is the null anchor (no charter — must reproduce canonical
pace). Raising --hurdle/--full-supply toward fiat-like returns quantifies
the Condition III finding: zero interest is what makes the charter share
affordable.

'audit' checks proposed membership terms (§8.7e) against the invariant:
admission cost adds to K_entry; exit notice, minimum hours, vesting length,
and dividend retention are checked against the MEMBERSHIP_* thresholds.
The code audits the contract; it does not legislate it.

NOTE: levy_fraction > 1 means the required levy exceeds the entire automated
output — an adversarial finding, not a bug (reconciliation §8.3).
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.research.contestability import (
    chi_arc, contestability_margin, levy_schedule_for_chi,
)
from hours_eoh.research.formation import (
    formation_feedback_simulation, formation_verdict,
)
from hours_eoh.research.recalibration import recalibrated_arc
from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    CONTESTABILITY_CHI_CRIT, CONTESTABILITY_CHI_WARN,
    CONTESTABILITY_MIN_VIABLE_POPULATION,
    FORMATION_FULL_SUPPLY_RATE, FORMATION_HURDLE_RATE_MIN,
    RECAL_CAPITAL_OUTPUT_RATIO, RECAL_EPSILON_RATE_PER_YEAR,
    RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE, RECAL_EXIT_HORIZON_YEARS,
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

    # ------------------------------------------------------------------ levy
    lv = sub2.add_parser(
        "levy",
        help="Derived levy schedule that holds χ ≥ target across the arc (§8.2)",
    )
    lv.add_argument("--regime",
                    choices=["increasing_returns", "replicable"],
                    default="increasing_returns",
                    help="K_entry regime (default: increasing_returns / adversarial)")
    lv.add_argument("--points", type=int, default=20, metavar="N",
                    help="Number of ε points (default: 20)")
    lv.add_argument("--population", type=float, default=1_000_000.0)
    lv.add_argument("--capital-stock", type=float, default=CAPITAL_STOCK_DEFAULT,
                    dest="capital_stock")
    lv.add_argument("--chi-target", type=float, default=CONTESTABILITY_CHI_CRIT,
                    dest="chi_target",
                    help="Required contestability margin (default: 1.0)")
    lv.add_argument("--levy-base", choices=["capital_yield", "machine_output"],
                    default="capital_yield", dest="levy_base",
                    help="Levy base: static ε·K·yield (default) or the "
                         "physically-consistent ε·total_EOH (§8.8 M3)")
    lv.add_argument("--format", choices=["table", "csv", "json"],
                    default="table", dest="fmt")
    lv.set_defaults(func=_levy)

    # ------------------------------------------------------------------ recal
    rc = sub2.add_parser(
        "recal",
        help="§8.9 recalibrated arc: τ=φ ownership accounting, endogenous "
             "dividend, three-channel exit financing",
    )
    rc.add_argument("--regime",
                    choices=["increasing_returns", "replicable"],
                    default="increasing_returns",
                    help="K_entry regime (default: increasing_returns / adversarial)")
    rc.add_argument("--points", type=int, default=20, metavar="N",
                    help="Number of ε points (default: 20)")
    rc.add_argument("--phi-policy",
                    choices=["target", "dilution", "escalated"],
                    default="dilution", dest="phi_policy",
                    help="Commons-share doctrine (default: dilution — §8.9b "
                         "charter formation, no forced sales)")
    rc.add_argument("--estate-escheat", type=float,
                    default=RECAL_ESTATE_CAPITAL_ESCHEAT_SHARE,
                    dest="estate_escheat",
                    help="Capital-estate escheat share (default: 0.15 = "
                         "ESTATE_LEVY_FRACTION, the D5 doctrine extended)")
    rc.add_argument("--min-viable-population", type=float,
                    default=CONTESTABILITY_MIN_VIABLE_POPULATION,
                    dest="min_viable_population",
                    help="Founding cohort size (raise to stress the "
                         "escalation trigger)")
    rc.add_argument("--population", type=float, default=1_000_000.0)
    rc.add_argument("--capital-output-ratio", type=float,
                    default=RECAL_CAPITAL_OUTPUT_RATIO, dest="capital_output_ratio",
                    help="ν: capital stock per unit annual machine output "
                         "(default: 4.0, Piketty's β)")
    rc.add_argument("--epsilon-rate", type=float,
                    default=RECAL_EPSILON_RATE_PER_YEAR, dest="epsilon_rate",
                    help="Arc speed dε/dt per year (default: 0.02 — 50-year arc)")
    rc.add_argument("--exit-horizon", type=float,
                    default=RECAL_EXIT_HORIZON_YEARS, dest="exit_horizon",
                    help="Self-financing horizon in years (default: 5.0)")
    rc.add_argument("--format", choices=["table", "csv", "json"],
                    default="table", dest="fmt")
    rc.set_defaults(func=_recal)

    # ------------------------------------------------------------------ formation
    fm = sub2.add_parser(
        "formation",
        help="§8.9c formation-feedback simulation: who builds K(ε), and "
             "what the charter share costs",
    )
    fm.add_argument("--priority", choices=["share", "dividend"],
                    default="share",
                    help="Commons budget priority: fund formation first "
                         "(default) or pay the dividend first")
    fm.add_argument("--years", type=int, default=100, metavar="N",
                    help="Simulation horizon in years (default: 100)")
    fm.add_argument("--regime",
                    choices=["increasing_returns", "replicable"],
                    default="increasing_returns")
    fm.add_argument("--hurdle", type=float,
                    default=FORMATION_HURDLE_RATE_MIN,
                    help="Minimum private return for any formation "
                         "(default: 0.02 — low because of Condition III)")
    fm.add_argument("--full-supply", type=float,
                    default=FORMATION_FULL_SUPPLY_RATE, dest="full_supply",
                    help="Return at which formation is fully supplied "
                         "(default: 0.10; try 0.18 for a fiat-like world)")
    fm.add_argument("--escalation", action="store_true",
                    help="Enable the §8.9b escalation clause (latching)")
    fm.add_argument("--charter-share", type=float, default=None,
                    dest="charter_share",
                    help="Pin the charter share (0 = null anchor: no "
                         "charter, canonical pace)")
    fm.add_argument("--min-viable-population", type=float,
                    default=CONTESTABILITY_MIN_VIABLE_POPULATION,
                    dest="min_viable_population")
    fm.add_argument("--format", choices=["table", "csv", "json"],
                    default="table", dest="fmt")
    fm.set_defaults(func=_formation)

    # ------------------------------------------------------------------ audit
    au = sub2.add_parser(
        "audit",
        help="Audit proposed membership terms against the χ invariant (§8.7e)",
    )
    au.add_argument("--terms-json", type=str, default=None, dest="terms_json",
                    metavar="PATH",
                    help="MembershipTerms as a JSON file ('-' for stdin); "
                         "inline flags below override its keys")
    au.add_argument("--vesting-years", type=float, default=None, dest="vesting_years")
    au.add_argument("--admission-cost", type=float, default=None, dest="admission_cost",
                    help="Sunk buy-in to join, in TEH (adds to K_entry)")
    au.add_argument("--exit-notice-years", type=float, default=None,
                    dest="exit_notice_years")
    au.add_argument("--minimum-hours", type=float, default=None, dest="minimum_hours",
                    help="Annual labor obligation (hours/year)")
    au.add_argument("--dividend-fraction", type=float, default=None,
                    dest="dividend_fraction",
                    help="Share of the pro-rata dividend actually distributed")
    au.add_argument("--epsilon", type=float, default=0.40)
    au.add_argument("--collective-trust", type=float, default=TRUST_BASE_TEH,
                    dest="collective_trust")
    au.add_argument("--collective-population", type=float, default=1_000_000.0,
                    dest="collective_population")
    au.add_argument("--federation-population", type=float, default=None,
                    dest="federation_population")
    au.add_argument("--commons-balance", type=float, default=0.0,
                    dest="commons_balance")
    au.add_argument("--regime",
                    choices=["increasing_returns", "replicable"],
                    default="increasing_returns")
    au.add_argument("--commons-dividend", action="store_true",
                    dest="commons_dividend",
                    help="§8.8 M1: include the universal commons dividend in P")
    au.add_argument("--underwriting-policy", action="store_true",
                    dest="underwriting_policy",
                    help="§8.8 M2: commons-financed entry may waive the "
                         "χ_marginal CRIT to WARN")
    au.add_argument("--format", choices=["table", "json"],
                    default="table", dest="fmt")
    au.set_defaults(func=_audit)


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


def _levy(args: argparse.Namespace) -> None:
    rows_data = levy_schedule_for_chi(
        n_points=args.points,
        regime=args.regime,
        population=args.population,
        capital_stock=args.capital_stock,
        chi_target=args.chi_target,
        levy_base=args.levy_base,
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

    n_feasible = sum(1 for r in rows_data if r["feasible"])
    n_total = len(rows_data)
    regime_label = green("replicable") if args.regime == "replicable" else yellow("increasing_returns (adversarial)")
    print(bold(f"Derived levy schedule — {regime_label}  "
               f"[χ ≥ {args.chi_target}, {args.points} points]"))
    print(dim(
        "  trust_target = Trust balance required to hold χ ≥ target (§8.2)   "
        "levy = ΔT + dividend outflow   levy_frac > 1 = infeasible from automated output"
    ))
    print()

    table_rows = []
    for r in rows_data:
        table_rows.append([
            fmt_eps(r["epsilon"]),
            fmt_float(r["k_entry"], decimals=0),
            f"{r['trust_target']:.2e}",
            f"{r['levy_required']:.2e}",
            _levy_cell(r["levy_fraction"]),
            green("YES") if r["feasible"] else red("NO"),
            _chi_color(r["chi_check"]),
        ])

    print(fmt_table(
        ["ε", "K_entry", "trust_target", "levy_req", "levy_frac", "feasible", "χ_check"],
        table_rows,
    ))
    print()
    print(dim(f"  {n_feasible}/{n_total} points feasible from automated output alone"))
    if n_feasible < n_total:
        print(dim(
            "  Infeasible points need additional levy bases (accumulation-ceiling "
            "redirection, estate dissolution) or a growing capital base — "
            "honest adversarial finding, not a bug (§8.5)."
        ))


def _recal(args: argparse.Namespace) -> None:
    rows_data = recalibrated_arc(
        n_points=args.points,
        regime=args.regime,
        population=args.population,
        capital_output_ratio=args.capital_output_ratio,
        epsilon_rate_per_year=args.epsilon_rate,
        exit_horizon_years=args.exit_horizon,
        phi_policy=args.phi_policy,
        estate_escheat_share=args.estate_escheat,
        min_viable_population=args.min_viable_population,
    )

    if args.fmt in ("json", "csv"):
        # inf is not valid JSON and reads poorly in CSV — serialize as None.
        clean = [
            {k: (None if isinstance(v, float) and not _finite(v) else v)
             for k, v in r.items()}
            for r in rows_data
        ]
        if args.fmt == "json":
            print(json.dumps(clean, indent=2))
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(clean[0].keys()))
            writer.writeheader()
            writer.writerows(clean)
        return

    n_fin = sum(1 for r in rows_data if r["exit_financeable"])
    n_acq = sum(1 for r in rows_data if r["acquisition_feasible"])
    n_esc = sum(1 for r in rows_data if r["escalation_active"])
    n_total = len(rows_data)
    regime_label = (green("replicable") if args.regime == "replicable"
                    else yellow("increasing_returns (adversarial)"))
    print(bold(f"Recalibrated arc (proposed §8.9/§8.9b) — {regime_label}  "
               f"policy: {args.phi_policy}  [{args.points} points]"))
    print(dim(
        "  τ = φ ≤ 1 by ownership accounting (dτ/dε ≥ 0 structural)   "
        f"exit: t_self ≤ {args.exit_horizon:g}y OR capacity ≥ 1   "
        "channel: labor → underwritten → self"
    ))
    if args.phi_policy != "target":
        print(dim(
            "  charter doctrine: the commons' share attaches to NEW capital "
            "at commissioning; private capital is never sold down "
            "(* = φ capped below target — the honest cost of no forced sales)"
        ))
    print()

    table_rows = []
    for r in rows_data:
        t_self = (f"{r['t_exit_self_years']:.1f}"
                  if _finite(r["t_exit_self_years"]) else "∞")
        cap = (f"{r['entry_capacity']:.1f}"
               if _finite(r["entry_capacity"]) else "∞")
        s_req = (f"{r['s_required']:.2f}" if r["s_required"] <= 1.0
                 else red(f"{r['s_required']:.2f}"))
        dk = r["private_capital_delta_per_year"]
        dk_cell = f"{dk:+.2e}" if dk != 0.0 else dim("0")
        channel = {
            "labor": green("labor"),
            "self": green("self"),
            "underwritten": yellow("underwritten"),
            "none": red("none"),
        }[r["channel"]]
        tau_cell = (f"{r['tau']:.3f}*" if r["cap_binding"]
                    else f"{r['tau']:.3f}")
        if r["escalation_active"]:
            tau_cell = red(tau_cell + "!")
        table_rows.append([
            fmt_eps(r["epsilon"]),
            tau_cell,
            fmt_float(r["dividend_per_capita"], decimals=0),
            s_req,
            green("Y") if r["acquisition_feasible"] else red("N"),
            dk_cell,
            t_self,
            cap,
            channel,
            green("YES") if r["exit_financeable"] else red("NO"),
        ])

    print(fmt_table(
        ["ε", "τ=φ", "D (TEH/p·y)", "s_req", "acq", "ΔKpriv/y",
         "t_self (y)", "capacity", "channel", "financeable"],
        table_rows,
    ))
    print()
    summary = (f"  {n_fin}/{n_total} points exit-financeable   "
               f"{n_acq}/{n_total} points acquisition-feasible")
    if args.phi_policy == "escalated":
        summary += (f"   escalation: {red(f'{n_esc} rows ACTIVE') if n_esc else green('never fired')}")
    print(dim(summary))
    if args.phi_policy == "target" and n_acq < n_total:
        print(dim(
            "  Early-arc acquisition infeasibility is carried by the initial "
            "endowment φ₀·K₀ and human-era fiscal levies — honest window, "
            "reported not tuned (§8.9). The charter doctrine "
            "(--phi-policy dilution) removes the purchase entirely."
        ))
    elif args.phi_policy != "target" and n_acq < n_total:
        print(dim(
            "  s_req > 1 rows: keeping φ on target would require forced "
            "sales — the charter refuses; φ caps instead (§8.9b honest "
            "window, inverted from §8.9a)."
        ))


def _finite(x: float) -> bool:
    return x == x and abs(x) != float("inf")


def _formation(args: argparse.Namespace) -> None:
    rows_data = formation_feedback_simulation(
        n_years=args.years,
        priority=args.priority,
        regime=args.regime,
        hurdle_rate_min=args.hurdle,
        full_supply_rate=args.full_supply,
        escalation=args.escalation,
        charter_share_override=args.charter_share,
        min_viable_population=args.min_viable_population,
    )
    verdict = formation_verdict(
        rows_data, full_supply_rate=args.full_supply,
    )

    if args.fmt in ("json", "csv"):
        clean = [
            {k: (None if isinstance(v, float) and not _finite(v) else v)
             for k, v in r.items()}
            for r in rows_data
        ]
        if args.fmt == "json":
            print(json.dumps({"verdict": verdict, "rows": clean}, indent=2))
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(clean[0].keys()))
            writer.writeheader()
            writer.writerows(clean)
        return

    regime_label = (green("replicable") if args.regime == "replicable"
                    else yellow("increasing_returns (adversarial)"))
    print(bold(f"Formation feedback (proposed §8.9c) — {regime_label}  "
               f"priority: {args.priority}  [{args.years} years]"))
    print(dim(
        "  formation is financed or it does not happen; ε derives from the "
        "capital actually formed   s* = "
        f"{verdict['s_star']:.2f} (charter free below it)"
    ))
    print()

    step = max(1, args.years // 20)
    table_rows = []
    for r in rows_data[::step]:
        t_self = (f"{r['t_exit_self_years']:.1f}"
                  if _finite(r["t_exit_self_years"]) else "∞")
        channel = {
            "labor": green("labor"),
            "self": green("self"),
            "underwritten": yellow("underwritten"),
            "none": red("none"),
        }[r["channel"]]
        eps_cell = f"{r['eps_actual']:.3f}"
        if r["eps_gap"] > 0.01:
            eps_cell = yellow(eps_cell + f" ({r['eps_gap']:+.2f})")
        table_rows.append([
            str(r["year"]),
            eps_cell,
            f"{r['s_applied']:.2f}",
            f"{r['supply_fraction']:.2f}",
            fmt_float(r["commons_funded"], decimals=0),
            fmt_float(r["dividend_per_capita"], decimals=0),
            f"{r['tau']:.3f}",
            t_self,
            channel,
            green("YES") if r["exit_financeable"] else red("NO"),
        ])

    print(fmt_table(
        ["yr", "ε (lag)", "s", "f", "commons→K", "D (TEH/p·y)", "τ",
         "t_self", "channel", "financeable"],
        table_rows,
    ))
    print()

    inv = (green("HOLDS every year") if verdict["invariant_holds"]
           else red(f"FAILS at year {verdict['first_failure_year']}"))
    if verdict["years_to_eps_95"] is not None:
        pace = (f"ε ≥ 0.95 at year {verdict['years_to_eps_95']} "
                f"(delay {verdict['delay_years']:+.1f} yr vs canonical)")
        pace = green(pace) if abs(verdict["delay_years"]) < 2 else yellow(pace)
    else:
        pace = red(
            f"never reaches ε = 0.95 — terminal ε = "
            f"{verdict['terminal_eps']:.3f} "
            + ("(STALLED)" if verdict["stalled"] else "(crawling)")
        )
    print(f"  Exit invariant: {inv}")
    print(f"  Arc pace:       {pace}")
    print(dim(
        f"  min dividend after takeoff: "
        f"{verdict['min_dividend_after_takeoff']:.0f} TEH/p·yr   "
        f"terminal: {verdict['terminal_dividend']:.0f}"
    ))


def _audit(args: argparse.Namespace) -> None:
    from hours_eoh.research.membership import contestability_audit

    # Terms: JSON file/stdin first, then inline flags overlay explicitly
    # provided keys only — absent keys keep the framework's canonical defaults.
    terms: dict = {}
    if args.terms_json is not None:
        if args.terms_json == "-":
            terms = json.load(sys.stdin)
        else:
            with open(args.terms_json) as fh:
                terms = json.load(fh)
    inline = {
        "vesting_years":            args.vesting_years,
        "admission_cost_teh":       args.admission_cost,
        "exit_notice_years":        args.exit_notice_years,
        "minimum_hours_annual":     args.minimum_hours,
        "dividend_policy_fraction": args.dividend_fraction,
    }
    terms.update({k: v for k, v in inline.items() if v is not None})

    result = contestability_audit(
        terms,  # type: ignore[arg-type]
        epsilon=args.epsilon,
        collective_trust=args.collective_trust,
        collective_population=args.collective_population,
        commons_balance=args.commons_balance,
        federation_population=args.federation_population,
        regime=args.regime,
        commons_dividend=args.commons_dividend,
        underwriting_policy=args.underwriting_policy,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold("Membership-terms contestability audit (§8.7e)"))
    print(dim("  the code audits the contract; it does not legislate it\n"))
    print(f"  ε = {fmt_eps(args.epsilon)}   regime = {args.regime}")
    t = result["terms"]
    print(
        f"  terms: vesting={t['vesting_years']}y  "
        f"admission={fmt_float(t['admission_cost_teh'], decimals=0)} TEH  "
        f"notice={t['exit_notice_years']}y  "
        f"min_hours={fmt_float(t['minimum_hours_annual'], decimals=0)}/y  "
        f"dividend_out={t['dividend_policy_fraction']:.2f}"
    )
    print()
    rows = [
        ["χ_marginal (tenure-0)", _chi_color(result["chi_marginal"]),
         _status_color(result["status_marginal"])],
        ["χ_vested (full tenure)", _chi_color(result["chi_vested"]), ""],
        ["K_entry effective", fmt_float(result["k_entry_effective"], decimals=0), ""],
        ["P marginal (floor + D_fed)", fmt_float(result["p_marginal"], decimals=0), ""],
        ["P vested", fmt_float(result["p_vested"], decimals=0), ""],
        ["entry capacity (§8.8 M2)", f"{result['entry_capacity']:.1f}",
         green("financeable") if result["exit_financeable"] else red("not financeable")],
        ["commons floor coverage",
         f"{result['commons_floor_coverage']:.4f} yr", ""],
    ]
    print(fmt_table(["metric", "value", "status"], rows, indent=2))
    print()
    print(f"  Audit: {_status_color(result['audit_status'])}   "
          f"passes: {'yes' if result['passes'] else 'no'}")
    for w in result["warnings"]:
        print(f"    - {w}")
