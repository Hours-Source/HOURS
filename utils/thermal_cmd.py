"""
thermal — planetary radiative capacity: overage, determinacy, ceilings.

  eoh thermal overage     [--points "1.5,2.0,2.5,3.0"] [--lambda F] [--forcing F]
                          [--epsilon ε] [--format table|csv|json]

  eoh thermal arc         --delta-t K [--lambda F] [--forcing F]
                          [--format table|csv|json]

  eoh thermal determinacy [--delta-t K] [--txx] [--lambda F]
                          [--format table|json]

  eoh thermal ceiling     [--points "2.0,2.5,3.0"] [--lambda F] [--reserve F]
                          [--format table|json]

'overage' is the headline table: O(ΔT_max) = Φ + (F_total − λ·ΔT_max)·A_earth,
the power by which civilization exceeds its radiative allowance, decomposed into
its forcing and waste-heat terms, paired with the forcing reduction that would
zero it. At defensible thresholds the heat term is a few percent — eliminating
every net-additive watt on Earth closes only that much, so zeroing is reachable
only through forcing.

'arc' sweeps the same overage across ε at one threshold, showing when (if ever)
waste heat stops being a rounding error.

'determinacy' reports which regime an assessed habitability threshold lands in
once the IGCC forcing uncertainty band is carried through — determinate
unbudgeted, indeterminate, or determinate budgeted. Pass --txx if your threshold
is stated in land extremes rather than GMST (C6, ÷1.48).

'ceiling' contrasts the automation ceiling before and after drawdown to the
natural forcing floor. Where no pre-drawdown ceiling exists the budget is zero,
and the ε ceiling is carbon-determined.

ADVISORY. Every number here is a bound the framework reports; none generates
obligation or mints TEH. ΔT_max is the framework's own judgment and dominates
every result — that is why these are sweeps, not point values. λ is Tier C and
the budget spans ~6.5× across its plausible range; it is printed with the table
for that reason.
"""

from __future__ import annotations
import argparse
import json

from hours_eoh.data import (
    THERMAL_LAMBDA_FEEDBACK,
    THERMAL_COMMONS_RESERVE,
    THERMAL_F_NET_ERF,
    THERMAL_TXX_PER_GMST,
)
from hours_eoh.research.thermal_overage import (
    thermal_overage,
    forcing_required_for_zero,
    post_decarbonization_ceiling,
    overage_arc,
    overage_epsilon_arc,
    phi_at_epsilon,
)
from hours_eoh.research.thermal_path_c import determinacy_zone, world_dissipation
from utils import formatters


_TW = 1e12


def _points(raw: str) -> tuple[float, ...]:
    return tuple(float(x) for x in raw.split(",") if x.strip())


def _frame_note(lam: float, f_total: float) -> str:
    o = thermal_overage(2.0, lam=lam, f_total=f_total)
    return formatters.dim(
        f"λ = {lam} W·m⁻²·K⁻¹ (Tier C) · F_total = {f_total} W·m⁻² (IGCC 2025a) · "
        f"equilibrium frame: {o['committed_delta_t']:.2f} K committed, "
        f"{o['observed_delta_t']:.2f} K delivered, {o['pipeline_delta_t']:.2f} K in pipeline"
    )


# --------------------------------------------------------------------- overage

def _overage(args: argparse.Namespace) -> None:
    phi = phi_at_epsilon(args.epsilon) if args.epsilon is not None else None
    rows = overage_arc(_points(args.points), phi, args.lam, args.forcing)

    if args.fmt == "json":
        print(json.dumps(rows, indent=2))
        return
    if args.fmt == "csv":
        print("delta_t_max,overage_tw,forcing_tw,heat_tw,heat_share,reduction_w_m2,share_of_removable,feasible")
        for r in rows:
            print(f"{r['delta_t_max']},{r['overage_w']/_TW:.2f},{r['forcing_term_w']/_TW:.2f},"
                  f"{r['heat_term_w']/_TW:.2f},{r['heat_share'] or ''},"
                  f"{r['reduction_required']:.4f},{r['share_of_removable']:.4f},{r['feasible']}")
        return

    body = []
    for r in rows:
        over = r["is_overage"]
        verdict = formatters.red("OVERAGE") if over else formatters.green("slack")
        body.append([
            f"{r['delta_t_max']:.2f}",
            f"{r['overage_w']/_TW:,.1f}",
            f"{r['forcing_term_w']/_TW:,.1f}",
            f"{r['heat_term_w']/_TW:,.2f}",
            formatters.fmt_pct(r["heat_share"]) if r["heat_share"] else "—",
            f"{r['reduction_required']:.3f}" if over else "—",
            formatters.fmt_pct(r["share_of_removable"]) if over else "—",
            verdict,
        ])
    print(formatters.bold("\nThermal overage — O(ΔT_max) = Φ + (F_total − λ·ΔT_max)·A_earth\n"))
    print(formatters.table(
        ["ΔT_max K", "O (TW)", "forcing TW", "heat TW", "heat %", "ΔF to zero", "of removable", ""],
        body))
    print("\n" + _frame_note(args.lam, args.forcing))
    print(formatters.dim(
        "  heat % is the share of the overage that eliminating ALL net-additive "
        "dissipation would close."))


# ------------------------------------------------------------------------- arc

def _arc(args: argparse.Namespace) -> None:
    eps = (0.0, 0.20, 0.40, 0.60, 0.90, 0.99)
    rows = overage_epsilon_arc(args.delta_t, eps, args.lam, args.forcing)

    if args.fmt == "json":
        print(json.dumps([{**r, "epsilon": e} for e, r in zip(eps, rows)], indent=2))
        return
    if args.fmt == "csv":
        print("epsilon,heat_tw,forcing_tw,overage_tw,heat_share")
        for e, r in zip(eps, rows):
            print(f"{e},{r['heat_term_w']/_TW:.2f},{r['forcing_term_w']/_TW:.2f},"
                  f"{r['overage_w']/_TW:.2f},{r['heat_share'] or ''}")
        return

    body = [[
        formatters.fmt_eps(e),
        f"{r['heat_term_w']/_TW:,.2f}",
        f"{r['forcing_term_w']/_TW:,.1f}",
        f"{r['overage_w']/_TW:,.1f}",
        formatters.fmt_pct(r["heat_share"]) if r["heat_share"] else "—",
    ] for e, r in zip(eps, rows)]
    print(formatters.bold(f"\nOverage across the automation arc at ΔT_max = {args.delta_t} K\n"))
    print(formatters.table(["ε", "heat TW", "forcing TW", "O (TW)", "heat %"], body))
    print("\n" + formatters.dim(
        "  Φ(ε) is a linear extrapolation holding ι and EOH_total fixed (the Eq. C1 "
        "caveat), and is proportional to the CHOSEN ε_current = 0.40."))


# ----------------------------------------------------------------- determinacy

def _determinacy(args: argparse.Namespace) -> None:
    dt = args.delta_t / THERMAL_TXX_PER_GMST if args.txx else args.delta_t
    z = determinacy_zone(dt, lam=args.lam)

    if args.fmt == "json":
        print(json.dumps({**z, "input_was_txx": args.txx}, indent=2))
        return

    label = {
        "determinate_unbudgeted": formatters.red("DETERMINATE — UNBUDGETED"),
        "indeterminate": formatters.yellow("INDETERMINATE"),
        "determinate_budgeted": formatters.green("DETERMINATE — BUDGETED"),
    }[z["zone"]]
    print(formatters.bold("\nDeterminacy map — robustness across the IGCC forcing p05–p95 band\n"))
    print(formatters.table(
        ["zone", "ΔT_max (GMST)", "ΔT_max (land TXx)"],
        [["unbudgeted below", f"{z['unbudgeted_below_k']:.3f}", f"{z['unbudgeted_below_txx_k']:.3f}"],
         ["budgeted above", f"{z['budgeted_above_k']:.3f}", f"{z['budgeted_above_txx_k']:.3f}"]]))
    src = "land TXx" if args.txx else "GMST"
    print(f"\n  assessed {args.delta_t} K ({src}) → {dt:.3f} K GMST → {label}")
    if not z["robust"]:
        print(formatters.dim(
            "  Forcing uncertainty ALONE spans below-floor to Contact here. The framework "
            "cannot report a sign, and asserting one would exceed the data."))
    print(formatters.dim(
        f"\n  The upper determinate zone needs ~{z['budgeted_above_txx_k']:.1f} K of land extreme "
        "warming — beyond any defensible habitability threshold."))


# --------------------------------------------------------------------- ceiling

def _ceiling(args: argparse.Namespace) -> None:
    rows = [post_decarbonization_ceiling(dt, lam=args.lam, r=args.reserve)
            for dt in _points(args.points)]

    if args.fmt == "json":
        print(json.dumps(rows, indent=2))
        return

    body = []
    for c in rows:
        pre = c["epsilon_max_pre_allocated"]
        body.append([
            f"{c['delta_t_max']:.2f}",
            formatters.red("UNBUDGETED") if pre is None else f"{pre:.2f}",
            f"{c['epsilon_max_post_allocated']:.1f}",
            f"{c['epsilon_max_post_gross']:.1f}",
            formatters.green("yes") if c["carbon_determined"] else "no",
        ])
    print(formatters.bold("\nAutomation ceiling before and after drawdown to the natural forcing floor\n"))
    print(formatters.table(
        ["ΔT_max K", "ε_max now", "ε_max post (alloc)", "ε_max post (gross)", "carbon-determined"],
        body))
    print("\n" + formatters.dim(
        f"  Φ(ε=1) = {phi_at_epsilon(1.0)/_TW:,.1f} TW at present intensity · reserve r = {args.reserve}"))
    print(formatters.dim(
        "  'carbon-determined' means no ceiling exists before drawdown because there is no "
        "budget at all — heat binds only after the forcing is gone."))


# ---------------------------------------------------------------------- parser

def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("thermal", help="Planetary radiative capacity: overage, determinacy, ceilings")
    sub2 = p.add_subparsers(dest="thermal_cmd", required=True)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--lambda", type=float, default=THERMAL_LAMBDA_FEEDBACK,
                        dest="lam", metavar="F",
                        help=f"Climate feedback parameter W·m⁻²·K⁻¹ (default: {THERMAL_LAMBDA_FEEDBACK}, Tier C)")
        sp.add_argument("--forcing", type=float, default=THERMAL_F_NET_ERF, metavar="F",
                        help=f"Total ERF W·m⁻² (default: {THERMAL_F_NET_ERF}, IGCC 2025a)")

    ov = sub2.add_parser("overage", help="Overage table across habitability thresholds")
    ov.add_argument("--points", default="1.5,1.75,2.0,2.17,2.5,2.805,3.0",
                    help="Comma-separated ΔT_max values in K (GMST)")
    ov.add_argument("--epsilon", type=float, default=None, metavar="ε",
                    help="Evaluate Φ at this ε instead of the measured present value")
    ov.add_argument("--format", choices=["table", "csv", "json"], default="table", dest="fmt")
    _common(ov)
    ov.set_defaults(func=_overage)

    ar = sub2.add_parser("arc", help="Overage across the ε arc at one threshold")
    ar.add_argument("--delta-t", type=float, default=2.0, dest="delta_t", metavar="K")
    ar.add_argument("--format", choices=["table", "csv", "json"], default="table", dest="fmt")
    _common(ar)
    ar.set_defaults(func=_arc)

    dz = sub2.add_parser("determinacy", help="Which determinacy zone a threshold lands in")
    dz.add_argument("--delta-t", type=float, default=3.0, dest="delta_t", metavar="K")
    dz.add_argument("--txx", action="store_true",
                    help="Interpret --delta-t as land TXx rather than GMST (C6, ÷1.48)")
    dz.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    _common(dz)
    dz.set_defaults(func=_determinacy)

    cl = sub2.add_parser("ceiling", help="Automation ceiling before and after drawdown")
    cl.add_argument("--points", default="2.0,2.5,3.0",
                    help="Comma-separated ΔT_max values in K (GMST)")
    cl.add_argument("--reserve", type=float, default=THERMAL_COMMONS_RESERVE, metavar="F",
                    help=f"Commons reserve fraction (default: {THERMAL_COMMONS_RESERVE})")
    cl.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    _common(cl)
    cl.set_defaults(func=_ceiling)
