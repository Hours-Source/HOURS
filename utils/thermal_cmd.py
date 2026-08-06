"""
thermal — planetary radiative capacity: overage, determinacy, ceilings.

  eoh thermal overage     [--points "1.5,2.0,2.5,3.0"] [--lambda F] [--forcing F]
                          [--epsilon ε] [--format table|csv|json]

  eoh thermal arc         --delta-t K [--lambda F] [--forcing F]
                          [--format table|csv|json]

  eoh thermal determinacy [--delta-t K] [--txx] [--single-axis]
                          [--lambda-lo F] [--lambda-hi F] [--format table|json]

  eoh thermal ceiling     [--points "2.0,2.5,3.0"] [--lambda F] [--reserve F]
                          [--format table|json]

  eoh thermal drawdown    [--delta-t K] [--hours-per-tonne F] [--years N]
                          [--format table|json]

  eoh thermal gate        [--delta-t K] [--hours-per-tonne F] [--years N]
                          [--format table|json]

  eoh thermal lambda      [--delta-t K] [--format table|json]

'overage' is the headline table: O(ΔT_max) = Φ + (F_total − λ·ΔT_max)·A_earth,
the power by which civilization exceeds its radiative allowance, decomposed into
its forcing and waste-heat terms, paired with the forcing reduction that would
zero it. At defensible thresholds the heat term is a few percent — eliminating
every net-additive watt on Earth closes only that much, so zeroing is reachable
only through forcing.

'arc' sweeps the same overage across ε at one threshold, showing when (if ever)
waste heat stops being a rounding error.

'determinacy' is the HEADLINE, and it leads: it reports what the framework can
determinately say at a threshold before it reports any number. Both the forcing
band AND λ are carried, because determinacy requires the whole parameter box to
agree and holding λ fixed at an unassessed value overstates the determinate zone
roughly threefold. Where the answer is indeterminate the budget is WITHHELD, not
estimated — a number there would be a point estimate from inside a band that
contains both 'no budget' and 'ample budget'. --single-axis reproduces the older
forcing-only map for comparison. Pass --txx if your threshold is stated in land
extremes rather than GMST (C6, ÷1.48).

'ceiling' contrasts the automation ceiling before and after drawdown to the
natural forcing floor. Where no pre-drawdown ceiling exists the budget is zero,
and the ε ceiling is carbon-determined.

'drawdown' shows the conversion chain from the required forcing reduction to the
labour that would deliver it, with each link's provenance tier. Note the energy
term cancels out of the EOH — the obligation is gross tonnage × labour-hours per
tonne — so energy per tonne affects only the programme's own dissipation.

'gate' runs the fiscal solvency gate under the FLOW convention: the drawdown
obligation annualized over the programme horizon, injected through the
framework's own deferred-ecological hook so it flows through the whole pipeline
and partly funds itself. All five pass conditions at every ε, plus the backward
query — what labour intensity would break the Trust, and how far the shipped
estimate sits from it. The null-load baseline is re-run every time, so a failure
can never be misattributed to the thermal load.

'lambda' reports the derived feedback parameter with its frame and the budget
sensitivity across the plausible range. λ is the second-largest lever after
ΔT_max and the budget spans ZERO to ~11x across AR6's own likely ECS range, so
the band is printed as a first-class output rather than a footnote.

ΔT_max (default 2.0 K) and the programme horizon (default 40 yr — one lifetime
of responsibility) are both CHOSEN. ΔT_max dominates every result and may be
judged too high later; every downward revision enlarges the obligation. The
horizon is an ethical choice about who does the work, and the obligation scales
as 1/horizon. Allocation across collectives defaults to RESPONSIBILITY
(cumulative emissions), falling back to population — with the fallback declared —
when emissions history is not supplied.

The thermal obligation is now WIRED into ecological EOH as a fourth term
(core.eoh_generation.ecological_eoh, `thermal_obligation`, default 0.0). The
bounds below remain advisory; ΔT_max is the framework's own judgment and dominates
every result — that is why these are sweeps, not point values. λ is Tier C and
the budget spans ~6.5× across its plausible range; it is printed with the table
for that reason.
"""

from __future__ import annotations
import argparse
import json

from hours_eoh.data import (
    CDR_LABOR_HOURS_PER_TONNE,
    THERMAL_DT_LO,
    THERMAL_PROGRAMME_YEARS,
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
    from hours_eoh.research.thermal_lambda import (
        determinacy_gain_from_tightening, determinacy_map, thermal_verdict)
    dt = args.delta_t / THERMAL_TXX_PER_GMST if args.txx else args.delta_t

    if args.single_axis:
        z = determinacy_zone(dt)
        if args.fmt == "json":
            print(json.dumps({**z, "SUPERSEDED": "holds λ fixed; see the two-axis map"}, indent=2))
            return
        print(formatters.bold("\nSingle-axis determinacy (forcing only) — SUPERSEDED\n"))
        print(formatters.table(["boundary", "GMST", "land TXx"],
              [["unbudgeted below", f"{z['unbudgeted_below_k']:.3f}", f"{z['unbudgeted_below_txx_k']:.3f}"],
               ["budgeted above", f"{z['budgeted_above_k']:.3f}", f"{z['budgeted_above_txx_k']:.3f}"]]))
        print(formatters.yellow(
            "\n  Holds λ fixed at an unassessed value and overstates the determinate zone "
            "~3x.\n  Use the default (two-axis) map."))
        return

    band = (args.lambda_lo, args.lambda_hi) if args.lambda_lo and args.lambda_hi else None
    m = determinacy_map(dt, lam_band=band)
    v = thermal_verdict(dt, lam_band=band)
    if args.fmt == "json":
        print(json.dumps({"verdict": v, "map": m}, indent=2)); return

    label = {"determinate_unbudgeted": formatters.red("DETERMINATE — UNBUDGETED"),
             "indeterminate": formatters.yellow("INDETERMINATE"),
             "determinate_budgeted": formatters.green("DETERMINATE — BUDGETED")}[v["zone"]]
    src = "land TXx" if args.txx else "GMST"
    print(formatters.bold(f"\nThermal verdict at {args.delta_t} K ({src})\n"))
    print(f"  {label}\n")
    for line in _wrap(v["claim"], 76):
        print(f"  {line}")
    if v["budget_tw"] is not None:
        print(f"\n  budget: {v['budget_tw']:,.1f} TW")
    if v["overage_tw"] is not None:
        over = f"{v['overage_tw']:,.1f} TW"
        print(f"  overage: {formatters.red(over)}")
    if v["what_would_resolve"]:
        print()
        for line in _wrap("What would resolve it: " + v["what_would_resolve"], 76):
            print(formatters.dim(f"  {line}"))
    vs, a = m["vs_single_axis"], m["attribution"]
    print(formatters.bold("\nthe map\n"))
    print(formatters.table(
        ["map", "unbudgeted below", "budgeted above", "indeterminate width"],
        [["single axis (λ fixed)", f"{vs['single_unbudgeted_below_k']:.3f} K",
          f"{vs['single_budgeted_above_k']:.3f} K", f"{vs['single_width_k']:.3f} K"],
         ["two axis (default)", f"{m['unbudgeted_below_k']:.3f} K",
          f"{m['budgeted_above_k']:.3f} K",
          formatters.yellow(f"{m['indeterminate_width_k']:.3f} K")]]))
    print(formatters.dim(
        f"  land extremes: unbudgeted below {m['unbudgeted_below_txx_k']:.2f} K TXx "
        f"(observed TXx is already ~1.8 K)"))
    print(formatters.dim(
        f"  carrying λ widens the band {vs['widening_factor']:.2f}x — an extra uncertain axis "
        "never buys agreement"))
    tight = determinacy_gain_from_tightening((1.10, 1.45))
    print(formatters.dim(
        f"  λ is worth {a['lambda_over_forcing']:.1f}x the forcing band; a tight assessed "
        f"λ would recover {tight['width_reduction_k']:.2f} K"))


def _wrap(text: str, width: int) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width)


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


# -------------------------------------------------------------------- drawdown

def _drawdown(args: argparse.Namespace) -> None:
    from hours_eoh.research.thermal_drawdown import drawdown_job, drawdown_power
    c = drawdown_job(args.delta_t, labor_hours_per_tonne=args.hours_per_tonne)
    if args.fmt == "json":
        print(json.dumps({**c, "power": drawdown_power(c, args.years)}, indent=2))
        return
    rows = [
        ["ΔF required", f"{c['forcing_reduction']:.3f} W·m⁻²", "derived from the overage"],
        ["→ concentration", f"{c['ppm_reduction']:.1f} ppm → {c['concentration_target']:.1f}",
         c["tiers"]["co2_forcing_coefficient"]],
        ["→ net mass", f"{c['net_mass_gt']:,.0f} GtCO₂", c["tiers"]["ppm_to_gt"]],
        ["→ gross mass", f"{c['gross_mass_gt']:,.0f} GtCO₂", c["tiers"]["gross_removal_factor"]],
        ["→ energy", f"{c['energy_j']:.3g} J", c["tiers"]["energy_per_tonne"]],
        ["→ EOH", f"{c['eoh_global']:.4g} hours", c["tiers"]["labor_hours_per_tonne"]],
    ]
    print(formatters.bold(f"\nDrawdown chain at ΔT_max = {args.delta_t} K\n"))
    print(formatters.table(["step", "value", "provenance"], rows))
    pw = drawdown_power(c, args.years)
    print("\n" + formatters.dim(
        f"  programme over {args.years:.0f} yr draws {pw['phi_programme_w']/_TW:.2f} TW — "
        f"{100*pw['ratio_to_overage']:.2f}% of the overage it clears; "
        f"self-defeating at κ=1: {pw['self_defeating_at_kappa_1']}"))
    print(formatters.dim(
        "  the energy term CANCELS out of the EOH: obligation = gross tonnes × labour-hours/tonne."))


# ------------------------------------------------------------------------ gate

def _gate(args: argparse.Namespace) -> None:
    from hours_eoh.research.thermal_solvency import solvency_gate, breaking_labor_intensity
    g = solvency_gate(delta_t_max=args.delta_t, labor_hours_per_tonne=args.hours_per_tonne,
                      programme_years=args.years)
    b = breaking_labor_intensity(delta_t_max=args.delta_t, programme_years=args.years)
    if args.fmt == "json":
        print(json.dumps({**g, "backward_query": b}, indent=2))
        return

    body = [[
        formatters.fmt_eps(r["epsilon"]),
        f"{r['eco_baseline_eoh']:,.0f}",
        f"{r['eco_loaded_eoh']:,.0f}",
        f"{r['load_ratio']:.2f}×",
        f"{r['labor_income_loaded']:,.0f}",
        formatters.fmt_pct(r["eco_coverage"]),
        formatters.fmt_pct(r["labor_fraction"]),
        formatters.green("PASS") if r["passes"] else formatters.red("FAIL " + ",".join(r["failures"])),
    ] for r in g["verdicts"]]
    print(formatters.bold(
        f"\nFiscal solvency gate — ΔT_max {args.delta_t} K, {args.hours_per_tonne} h/t, "
        f"{args.years:.0f} yr, FLOW convention\n"))
    print(formatters.table(
        ["ε", "eco base h/yr", "eco loaded", "load", "labour income", "eco cov", "labour", ""], body))
    verdict = formatters.green("PASS") if g["passes"] else formatters.red("FAIL")
    print(f"\n  overall: {verdict}    null-load baseline passes: {g['baseline_passes']} "
          f"(failures attributable: {g['attributable']})")
    if b["breaking_value"]:
        print(f"  backward query: the Trust gives way at {b['breaking_value']:.1f} h/t — "
              f"{b['margin']:.0f}× the shipped {b['shipped_value']} h/t ({b['verdict']})")
    else:
        print(f"  backward query: {b['verdict']}")
    print(formatters.dim(
        "\n  The obligation is WIRED into ecological EOH as a fourth term (2026-08-05).\n"
        "  Sizing inputs remain Tier C/D — see `thermal drawdown` for per-link provenance."))



# ---------------------------------------------------------------------- lambda

def _lambda(args: argparse.Namespace) -> None:
    from hours_eoh.research.thermal_lambda import (
        lambda_for_frame, lambda_sensitivity, load_climate_feedback)
    d = load_climate_feedback()
    rows = lambda_sensitivity(args.delta_t)
    if args.fmt == "json":
        print(json.dumps({"frames": {f: lambda_for_frame(f) for f in ("equilibrium", "historical")},
                          "sensitivity": rows, "pattern_effect": d["pattern_effect"]}, indent=2))
        return
    print(formatters.bold("\nClimate feedback λ — derived from IGCC 2025a\n"))
    eq, hi = lambda_for_frame("equilibrium"), lambda_for_frame("historical")
    print(formatters.table(
        ["frame", "λ", "band", "pairs with"],
        [["equilibrium", f"{eq['value']:.3f}", f"{eq['band'][0]:.2f}–{eq['band'][1]:.2f}",
          "the equilibrium budget (commitment accounting)"],
         ["historical", f"{hi['value']:.3f}", f"{hi['band'][0]:.2f}–{hi['band'][1]:.2f}",
          formatters.yellow("a transient reading — REJECTED by this framework")]]))
    print(formatters.dim(f"\n  λ_hist = (F − N)/ΔT over four windows, spread "
                         f"{d['historical']['window_spread']}"))
    print(formatters.dim(f"  pattern effect {d['pattern_effect']['value']:+.3f} — positive as "
                         "expected, an independent check on the derivation"))
    body = []
    for r in rows:
        flag = formatters.red("UNBUDGETED") if r["unbudgeted"] else f"{r['budget_tw']:,.1f}"
        note = formatters.yellow("frame mismatch") if r["note"] else ""
        body.append([r["label"], f"{r['lambda']:.3f}", r["frame"], flag,
                     "—" if r["vs_shipped"] is None else f"{r['vs_shipped']}x", note])
    print(formatters.bold(f"\nBudget sensitivity at ΔT_max = {args.delta_t} K\n"))
    print(formatters.table(["λ candidate", "λ", "frame", "budget TW", "vs shipped", ""], body))
    print("\n" + formatters.dim(
        "  Across AR6's own likely ECS range the budget runs from ZERO to ~11x the shipped\n"
        "  case. λ uncertainty ALONE can close the budget — separately from the forcing band."))


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
    dz.add_argument("--single-axis", action="store_true", dest="single_axis",
                    help="SUPERSEDED forcing-only map, for comparison")
    dz.add_argument("--lambda-lo", type=float, default=None, dest="lambda_lo", metavar="F")
    dz.add_argument("--lambda-hi", type=float, default=None, dest="lambda_hi", metavar="F")
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

    dd = sub2.add_parser("drawdown", help="The forcing→labour conversion chain")
    dd.add_argument("--delta-t", type=float, default=THERMAL_DT_LO, dest="delta_t", metavar="K")
    dd.add_argument("--hours-per-tonne", type=float, default=CDR_LABOR_HOURS_PER_TONNE,
                    dest="hours_per_tonne", metavar="F")
    dd.add_argument("--years", type=float, default=THERMAL_PROGRAMME_YEARS, metavar="N",
                    help=f"Programme horizon (default: {THERMAL_PROGRAMME_YEARS:.0f}, CHOSEN)")
    dd.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    dd.set_defaults(func=_drawdown)

    gt = sub2.add_parser("gate", help="Fiscal solvency gate + backward query")
    gt.add_argument("--delta-t", type=float, default=THERMAL_DT_LO, dest="delta_t", metavar="K")
    gt.add_argument("--hours-per-tonne", type=float, default=CDR_LABOR_HOURS_PER_TONNE,
                    dest="hours_per_tonne", metavar="F")
    gt.add_argument("--years", type=float, default=THERMAL_PROGRAMME_YEARS, metavar="N")
    gt.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    gt.set_defaults(func=_gate)

    lm = sub2.add_parser("lambda", help="Derived climate feedback λ + budget sensitivity")
    lm.add_argument("--delta-t", type=float, default=3.0, dest="delta_t", metavar="K")
    lm.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    lm.set_defaults(func=_lambda)

