"""
coasean — Coasean collective federation CLI command (research-tier, §§6–7).

Sub-commands:
  n1-check     Verify N=1 regression anchor at ε ∈ {0, 0.40, 0.99}
  count        Print emergent collective count across the ε arc
  federation   Show per-collective pipeline + fiscal summary at a given ε

All output is clearly marked EXPERIMENTAL — research API, not stable.
"""

from __future__ import annotations

from hours_eoh.data import REFERENCE_FRAME_POPULATION, EPSILON_ARC_MAX
import argparse
import json

import sys

from utils.formatters import table, fmt_float, fmt_eps, green, yellow, red
from utils.frame_inputs import add_frame_arguments, frame_flags_given


def _banner(args: argparse.Namespace, text: str) -> None:
    """A header line: to stderr under --format json, so stdout stays one JSON
    document (2026-10-14 — all four subcommands printed it into the JSON)."""
    print(text, file=sys.stderr if getattr(args, "fmt", None) == "json" else sys.stdout)
from hours_eoh.research.coasean import RATE_BASES


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
    n1.add_argument("--population", type=float, default=REFERENCE_FRAME_POPULATION)
    n1.set_defaults(func=run_n1_check)

    # count
    cnt = csub.add_parser("count", help="Emergent collective count across the ε arc")
    cnt.add_argument("--points", type=int, default=20)
    cnt.set_defaults(func=run_count)

    # federation
    fed = csub.add_parser(
        "federation", help="Per-collective snapshot at a given ε",
        description="Without a frame: N equal collectives of the reference economy "
                    "(make_federation), no land fee charged. On --frame/--frame-file: "
                    "the frame divided by --split (or N(ε) equal shares), each "
                    "collective run as `scenario run collective` runs the frame — "
                    "its land, labour supply and the per-parcel land fee, capped at "
                    "what its mint can pay")
    fed.add_argument("--epsilon", type=float, default=None,
                     help="Default: the frame's reading on a frame, else 0.40")
    fed.add_argument("--population", type=float, default=None,
                     help="Default: the frame's, else REFERENCE_FRAME_POPULATION. On a "
                          "frame it moves every collective's people, not its land")
    fed.add_argument("--n", type=int, default=None,
                     help="Override collective count (default: emergent N(ε)); "
                          "refused with --split, which states its own")
    fed.add_argument("--split", default=None, metavar="NAME|PATH",
                     help="How the frame divides: a split file, or a shipped one by name "
                          "(us_states = the contiguous 48 and DC). Needs a frame")
    add_frame_arguments(fed)
    fed.set_defaults(func=run_federation)

    # simulate
    sim = csub.add_parser("simulate",
                          help="Multi-period federation arc with three-regime inflation")
    sim.add_argument("--periods", type=int, default=10,
                     help="Number of periods (default: 10)")
    sim.add_argument("--epsilon-start", type=float, default=0.10, dest="eps_start")
    sim.add_argument("--epsilon-end",   type=float, default=EPSILON_ARC_MAX, dest="eps_end")
    sim.add_argument("--population",    type=float, default=REFERENCE_FRAME_POPULATION)
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
    sim.add_argument("--rate-basis", choices=list(RATE_BASES), default="registered",
                     dest="rate_basis",
                     help="exchange-rate basis the inflation metrics read: "
                          "'registered' is the adopted settlement (2026-09-30); "
                          "'parity' reproduces pre-adoption output")
    sim.set_defaults(func=run_simulate)

    p.set_defaults(func=lambda args: p.print_help())


def run_n1_check(args: argparse.Namespace) -> None:
    from hours_eoh.research.coasean import n1_regression_anchor

    _banner(args, "EXPERIMENTAL — research/coasean.py (Workstream D Phase 1)\n")

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

    _banner(args, "EXPERIMENTAL — research/coasean.py\n")

    n_points = args.points
    rows_data = []
    for i in range(n_points):
        eps = i / (n_points - 1) * EPSILON_ARC_MAX if n_points > 1 else 0.40
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

    _banner(args, "EXPERIMENTAL — research/coasean.py (three-regime inflation, §7; commons, §8.7)\n")
    tithe = COASEAN_COMMONS_TITHE if args.commons_tithe is None else args.commons_tithe
    extras = ""
    if args.dynamics:
        extras += f"  dynamics: levy={args.levy_rate:.2f} g_priv={args.g_priv:.3f}"
    if args.commons:
        extras += f"  commons: tithe={tithe:.3f} regime={args.regime}"
    _banner(
        args,
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
        rate_basis=args.rate_basis,
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
    from hours_eoh.data import CAPITAL_STOCK_DEFAULT

    if args.frame is not None or args.frame_file is not None:
        return _run_federation_on_frame(args)
    if args.split is not None or frame_flags_given(args):
        raise SystemExit("--split and the frame flags need --frame or --frame-file: "
                         "a split divides a frame")
    args.epsilon = 0.40 if args.epsilon is None else args.epsilon
    args.population = (REFERENCE_FRAME_POPULATION if args.population is None
                       else args.population)

    _banner(args, "EXPERIMENTAL — research/coasean.py\n")
    _banner(args, "No land fee is charged on this path (make_federation); "
                  "--frame runs each collective with it.\n")

    eps = args.epsilon
    n = args.n
    if n is None:
        n = coasean_collective_count(eps)

    _banner(args, f"ε = {eps:.3f}  |  N = {n} collectives  |  population = {args.population:,.0f}\n")

    fed = make_federation(
        epsilon=eps,
        n=n,
        population=args.population,
        # THE 1M STOCK, SCALED TO --population (2026-10-14): passed unscaled,
        # per-capita mint read 332.2 at 1e6 and 281.5 at 1e7 for one economy.
        capital_stock_teh=CAPITAL_STOCK_DEFAULT * (args.population / REFERENCE_FRAME_POPULATION),
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


def _run_federation_on_frame(args: argparse.Namespace) -> None:
    """
    THE FRAME, DIVIDED (2026-10-15). Each collective is the frame's values at
    its share (`frame_inputs.split_frame`) run through `collective_on_frame` —
    the path `scenario run collective` takes for the whole frame, so the land
    fee, its payable cap and the labour supply are the same mechanisms. The
    whole frame is run once more beside them: what is created, owed and
    assessed adds up across the split; what is COLLECTED need not, because the
    cap binds per collective (a min does not add), and the difference is
    reported, not reconciled.
    """
    from hours_eoh.data import M2_PER_HECTARE
    from hours_eoh.research.coasean import coasean_collective_count
    from hours_eoh.research.exchange import Collective, CollectiveFrame
    from utils.frame_inputs import (even_split, labelled_inputs, load_split,
                                    resolve_epsilon, resolve_inputs, split_frame)
    from utils.scenario_cmd import collective_on_frame

    if args.n is not None and args.n < 1:
        raise SystemExit("--n must be at least 1")
    if args.split is not None and args.n is not None:
        raise SystemExit("--n and --split both set the collective count; a split "
                         "states its own")
    eps = resolve_epsilon(args)
    e = eps["value"]
    v, lab = resolve_inputs(args, e)
    if lab["land_m2"]["kind"] not in ("supplied", "measured"):
        raise SystemExit("a federation on a frame needs the frame's LAND: state "
                         "land_hectares in the frame file")
    split = (load_split(args.split) if args.split is not None
             else even_split(args.n or coasean_collective_count(e)))
    if split.get("frame") and split["frame"] != args.frame:
        raise SystemExit(f"split {split.get('name')!r} divides --frame {split['frame']}; "
                         f"this run is on {args.frame or 'a frame file'}")

    def row(u: dict, rep: dict) -> dict:
        c = Collective(
            frame=CollectiveFrame(
                collective_id=len(rows), population=u["population"],
                land_hectares=u["land_m2"] / M2_PER_HECTARE,
                capital_stock_teh=float(rep["frame"]["capital_stock_teh"]),
                trust_balance=float(rep["fiscal"]["trust"]["trust_start"]),
                capital_age_ratio=u["capital_age_ratio"],
                ecosystem_health=u["ecosystem_health"], label=u.get("label", "")),
            epsilon=e, pipeline=rep["pipeline"], fiscal=rep["fiscal"])
        fee = rep["land_fee"]
        return {"id": u.get("id", "frame"), "label": u.get("label", "the whole frame"),
                "population": u["population"],
                "hectares_per_capita": rep["frame"]["hectares_per_capita"],
                "parcel_count": rep["frame"]["parcel_count"],
                "teh_created": c.teh_created, "reserve": c.reserve,
                "guf_assessed": fee["assessed"], "guf_collected": fee["collected"],
                "guf_unpaid": fee["unpaid"],
                # What the unit's LAND moves: the ecological work relocated to
                # the fee. The fee's area part is NOT SUPPLIED, so land reaches
                # no fee, mint or surplus figure yet.
                "guf_relocated_obligation": rep["guf"]["obligation"],
                "solvent": bool(rep["fiscal"]["solvent"]),
                "surplus": rep["fiscal"]["trust"]["surplus_deficit"]}

    rows: list[dict] = []

    def run(fv: dict, at: float) -> tuple[list[dict], dict]:
        rows.clear()
        for u in split_frame(fv, split):
            rows.append(row(u, collective_on_frame(u, at, u["land_m2"] / M2_PER_HECTARE)))
        return list(rows), row(fv, collective_on_frame(fv, at, fv["land_m2"] / M2_PER_HECTARE))

    def outcome(at: float, fv: dict) -> dict:
        units, one = run(fv, at)
        return {"solvent": sum(r["solvent"] for r in units),
                "collectives_unpaid": sum(r["guf_unpaid"] > 0.0 for r in units),
                "guf_collected": sum(r["guf_collected"] for r in units),
                "frame_as_one_guf_collected": one["guf_collected"]}

    # BOTH ENDS, AS `scenario run` DOES: the frame's ε reading and a derived
    # capital rate are ranges, and the labels say their ends are re-run.
    across_eps = ({f"{x:.3f}": outcome(x, v) for x in (eps["low"], eps["high"])}
                  if eps["high"] > eps["low"] else None)
    band = v.get("capital_rate_band")
    across_cap = ({f"{r:.2f}": outcome(e, resolve_inputs(
        argparse.Namespace(**{**vars(args), "_capital_rate": r}), e)[0])
        for r in (band[0], band[2])} if band else None)
    rows, whole = run(v, e)
    summed = ("population", "parcel_count", "teh_created", "reserve", "guf_assessed",
              "guf_collected", "guf_unpaid", "guf_relocated_obligation", "surplus")
    total = {"id": "total", "label": f"{len(rows)} collectives",
             **{k: sum(r[k] for r in rows) for k in summed},
             "solvent": sum(r["solvent"] for r in rows)}
    shared = {k: labelled_inputs(v, lab, eps)[k] for k in
              ("age_fractions", "adult_capacity_h_yr", "capital_age_ratio",
               "ecosystem_health", "capital_teh", "trust_balance") if k in lab}
    out = {"epsilon": eps, "split": split.get("name"), "note": split.get("note"),
           "collectives": rows, "total": total, "frame_as_one": whole,
           "outcomes_across_epsilon": across_eps, "outcomes_across_capital": across_cap,
           "frame_inputs": shared}
    if args.fmt == "json":
        print(json.dumps(out, indent=2, default=str))
        return

    _banner(args, "EXPERIMENTAL — research/coasean.py, each collective through "
                  "collective_snapshot\n")
    _banner(args, f"ε = {e:.3f} ({eps['kind']}: {eps['source']})")
    _banner(args, f"split: {split.get('name')} — {len(rows)} collectives; population, land "
                  "and parcels are each collective's share of the frame's, capital and "
                  "Trust its population share; the rest is the frame's. Settlement "
                  "rates are all 1.0: every collective mints at one multiplier\n")
    headers = ["id", "label", "population", "ha/head", "parcels", "teh_created",
               "fee assessed", "fee collected", "unpaid", "solvent", "surplus"]
    body = [[str(r["id"]), str(r["label"]), fmt_float(r["population"]),
             "" if "hectares_per_capita" not in r else f"{r['hectares_per_capita']:.2f}",
             fmt_float(r["parcel_count"]), fmt_float(r["teh_created"]),
             fmt_float(r["guf_assessed"]), fmt_float(r["guf_collected"]),
             fmt_float(r["guf_unpaid"]),
             ("Y" if r["solvent"] else "N") if isinstance(r["solvent"], bool)
             else f"{r['solvent']}/{len(rows)}",
             fmt_float(r["surplus"])] for r in (*rows, total, whole)]
    print(table(headers, body))
    for name, ends in (("ε", across_eps), ("capital rate", across_cap)):
        if ends:
            print(f"\nat the {name} ends: " + "; ".join(
                f"{k}: {o['solvent']}/{len(rows)} solvent, {o['collectives_unpaid']} with "
                f"an unpaid fee, collected {fmt_float(o['guf_collected'])}"
                for k, o in ends.items()))
