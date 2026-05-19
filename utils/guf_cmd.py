"""
guf — Ground Use Fee calculations (NLSA TM-0042).

  eoh guf calculate            --epsilon ε [options]
  eoh guf trust                --revenues V1,V2,...
  eoh guf writedown            --epsilon ε [--pathway restoration|abandonment] [options]
  eoh guf rebuilding-surcharge --epsilon ε --services-json '[...]'
  eoh guf accumulation-warning --unfulfilled F --total F
  eoh guf inventory calculate  --parcels FILE [--epsilon ε] [--median-income TEH]
  eoh guf inventory sweep      --parcels FILE [--epsilon-start ε] [--epsilon-end ε] [--steps N]
  eoh guf inventory stress     --parcels FILE [--epsilon-start ε] [--epsilon-end ε] [--periods N]

Inventory JSON parcel file format (list of parcel dicts):
  [
    {"area_slu": 3.5, "location_value": 0.72, "use_category": "residential_primary"},
    {"area_slu": 5.0, "location_value": 0.85, "use_category": "commercial_retail",
     "ecosystem_services": [{"label":"water","volume":0.4,"kappa_ref":1.65,"beta":0.8,"retained":0.3}]}
  ]

Services JSON format (for writedown and rebuilding-surcharge):
  Reset services  (--services-reset-json / --services-json for rebuilding-surcharge):
    [{"label":"water","volume":0.4,"kappa_ref":1.65,"beta":0.8,"retained":0.3}, ...]
  Lost services   (--services-lost-json / --services-json for rebuilding-surcharge):
    [{"label":"biodiversity","volume_lost":5.0,"kappa_ref":0.35,"beta":0.7}, ...]
"""

from __future__ import annotations
import argparse
import json
import sys

from hours_eoh.land.guf import (
    ground_use_fee,
    guf_trust_inflow,
    rebuilding_surcharge,
    ground_use_fee_writedown,
    eoh_accumulation_warning,
)
from hours_eoh.land.collective import compute_collective_guf
from hours_eoh.scenarios.guf_stress import automation_levy_guf_stress
from hours_eoh.data import (
    GUF_WRITEDOWN_AMORTIZATION_YEARS,
    GUF_EOH_ACCUMULATION_THRESHOLD,
    TRUST_BASE_TEH,
    CAPITAL_STOCK_DEFAULT,
)

from utils.formatters import bold, green, yellow, red, fmt_float, fmt_eps, fmt_pct, table as fmt_table

_USE_CATEGORIES = [
    "residential_primary", "residential_secondary",
    "agricultural_active", "agricultural_fallow",
    "commercial_retail", "commercial_office",
    "industrial_light", "industrial_heavy",
    "institutional", "conservation",
]


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("guf", help="Ground Use Fee calculations")
    sub2 = p.add_subparsers(dest="guf_cmd", required=True)

    # ------------------------------------------------------------------ calculate
    calc = sub2.add_parser("calculate", help="Compute GUF for a parcel")
    calc.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    calc.add_argument("--area-slu", type=float, default=1.0, dest="area_slu",
                      help="Area in Standard Land Units (default: 1.0)")
    calc.add_argument("--location-value", type=float, default=1.0,
                      dest="location_value",
                      help="Location value index (default: 1.0)")
    calc.add_argument("--use-category", default="residential_primary",
                      dest="use_category", choices=_USE_CATEGORIES,
                      help="Land use category (default: residential_primary)")
    calc.add_argument("--not-residential", action="store_true", dest="not_residential",
                      help="Mark parcel as non-residential")
    calc.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    calc.set_defaults(func=_calculate)

    # ------------------------------------------------------------------ trust
    trust = sub2.add_parser("trust", help="GUF trust inflow from a set of revenues")
    trust.add_argument("--revenues", required=True, metavar="V1,V2,...",
                       help="Comma-separated GUF revenue values")
    trust.add_argument("--subsidies", type=float, default=0.0,
                       help="Subsidies absorbed (default: 0.0)")
    trust.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    trust.set_defaults(func=_trust)

    # ------------------------------------------------------------------ writedown
    wd = sub2.add_parser(
        "writedown",
        help="Modified GUF during an ecological write-down event (NLSA Eq. 29)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Compute GUF_wd under the restoration or abandonment pathway.\n\n"
            "Restoration (default): V_s baselines reset to recovery target; R_b = 0.\n"
            "  Pass reset service volumes via --services-reset-json.\n\n"
            "Abandonment: degraded V_s baseline plus rebuilding surcharge R_b.\n"
            "  Pass --pathway abandonment and supply both --services-reset-json\n"
            "  (degraded state) and --services-lost-json (lost volumes for R_b)."
        ),
    )
    wd.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    wd.add_argument("--area-slu", type=float, default=1.0, dest="area_slu",
                    help="Parcel area in SLU (default: 1.0)")
    wd.add_argument("--location-value", type=float, default=1.0, dest="location_value",
                    help="Location Value Index L(p) (default: 1.0)")
    wd.add_argument("--use-category", default="residential_primary",
                    dest="use_category", choices=_USE_CATEGORIES)
    wd.add_argument("--pathway", choices=["restoration", "abandonment"],
                    default="restoration",
                    help="Write-down pathway (default: restoration)")
    wd.add_argument("--services-reset-json", dest="services_reset_json",
                    default=None, metavar="JSON",
                    help="JSON list of reset-baseline service dicts for E_reset")
    wd.add_argument("--services-lost-json", dest="services_lost_json",
                    default=None, metavar="JSON",
                    help="JSON list of lost-service dicts for R_b (abandonment only)")
    wd.add_argument("--amortization-years", type=float,
                    default=GUF_WRITEDOWN_AMORTIZATION_YEARS, dest="amortization_years",
                    help=f"R_b amortization period in years (default: {GUF_WRITEDOWN_AMORTIZATION_YEARS:.0f})")
    wd.add_argument("--not-residential", action="store_true", dest="not_residential")
    wd.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    wd.set_defaults(func=_writedown)

    # ------------------------------------------------------------------ rebuilding-surcharge
    rb = sub2.add_parser(
        "rebuilding-surcharge",
        help="Rebuilding surcharge R_b(p,ε) for lost ecosystem services (NLSA Eq. 28)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Compute the annualized replacement cost of lost ecosystem services.\n\n"
            "Services JSON: list of dicts with fields:\n"
            "  volume_lost  float  annual service volume lost per parcel\n"
            "  kappa_ref    float  TEH/unit/yr at ε=0.40\n"
            "  beta         float  automation sensitivity (0.6–1.2)\n"
            "  label        str    optional label\n\n"
            "Example:\n"
            '  --services-json \'[{"label":"biodiversity","volume_lost":5.0,'
            '"kappa_ref":0.35,"beta":0.7}]\''
        ),
    )
    rb.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    rb.add_argument("--services-json", required=True, dest="services_json", metavar="JSON",
                    help="JSON list of lost-service dicts")
    rb.add_argument("--amortization-years", type=float,
                    default=GUF_WRITEDOWN_AMORTIZATION_YEARS, dest="amortization_years",
                    help=f"Amortization period in years (default: {GUF_WRITEDOWN_AMORTIZATION_YEARS:.0f})")
    rb.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    rb.set_defaults(func=_rebuilding_surcharge)

    # ------------------------------------------------------------------ accumulation-warning
    aw = sub2.add_parser(
        "accumulation-warning",
        help="EOH accumulation warning — pre-collapse preventive signal (NLSA §9.8)",
    )
    aw.add_argument("--unfulfilled", type=float, required=True,
                    help="Unmet ecological EOH in the monitored zone")
    aw.add_argument("--total", type=float, required=True,
                    help="Total assessed ecological EOH for the zone")
    aw.add_argument("--threshold", type=float, default=GUF_EOH_ACCUMULATION_THRESHOLD,
                    help=f"Warning trigger ratio (default: {GUF_EOH_ACCUMULATION_THRESHOLD})")
    aw.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    aw.set_defaults(func=_accumulation_warning)

    # ------------------------------------------------------------------ inventory
    inv = sub2.add_parser(
        "inventory",
        help="Batch GUF analysis for a collective land inventory (JSON parcel file)",
    )
    inv_sub = inv.add_subparsers(dest="inv_cmd", required=True)

    # inventory calculate
    inv_calc = inv_sub.add_parser(
        "calculate",
        help="Compute aggregate GUF for all parcels in the inventory at a given ε",
    )
    inv_calc.add_argument("--parcels", required=True, metavar="FILE",
                          help="Path to JSON file (list of parcel dicts)")
    inv_calc.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    inv_calc.add_argument("--median-income", type=float, default=0.0,
                          dest="median_income",
                          help="Collective median income for subsidy calculation (TEH/yr)")
    inv_calc.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    inv_calc.set_defaults(func=_inv_calculate)

    # inventory sweep
    inv_sweep = inv_sub.add_parser(
        "sweep",
        help="Compute aggregate GUF across a range of ε values",
    )
    inv_sweep.add_argument("--parcels", required=True, metavar="FILE",
                           help="Path to JSON file (list of parcel dicts)")
    inv_sweep.add_argument("--epsilon-start", type=float, default=0.0,
                           dest="epsilon_start", metavar="ε")
    inv_sweep.add_argument("--epsilon-end", type=float, default=0.99,
                           dest="epsilon_end", metavar="ε")
    inv_sweep.add_argument("--steps", type=int, default=11,
                           help="Number of ε points (default: 11)")
    inv_sweep.add_argument("--median-income", type=float, default=0.0,
                           dest="median_income")
    inv_sweep.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    inv_sweep.set_defaults(func=_inv_sweep)

    # inventory stress
    inv_stress = inv_sub.add_parser(
        "stress",
        help="Multi-period stress: automation rises, levy falls — does GUF compensate?",
    )
    inv_stress.add_argument("--parcels", default=None, metavar="FILE",
                            help="JSON parcel file (omit to use 1 000-parcel urban default)")
    inv_stress.add_argument("--epsilon-start", type=float, default=0.20,
                            dest="epsilon_start", metavar="ε")
    inv_stress.add_argument("--epsilon-end", type=float, default=0.80,
                            dest="epsilon_end", metavar="ε")
    inv_stress.add_argument("--periods", type=int, default=20)
    inv_stress.add_argument("--population", type=float, default=1_000_000.0)
    inv_stress.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH,
                            dest="trust_balance")
    inv_stress.add_argument("--median-income", type=float, default=0.0,
                            dest="median_income")
    inv_stress.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    inv_stress.set_defaults(func=_inv_stress)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_services_json(raw: str, flag: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: {flag} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(parsed, list):
        print(f"error: {flag} must be a JSON array", file=sys.stderr)
        sys.exit(1)
    return parsed


def _scalar_rows(result: dict) -> list[list[str]]:
    """Extract scalar key/value pairs from a result dict for table display."""
    rows = []
    for k, v in result.items():
        if isinstance(v, (int, float)):
            rows.append([str(k), fmt_float(float(v))])
        elif isinstance(v, bool):
            rows.append([str(k), str(v)])
        elif isinstance(v, str):
            rows.append([str(k), v])
    return rows


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _calculate(args: argparse.Namespace) -> None:
    result = ground_use_fee(
        area_slu=args.area_slu,
        location_value=args.location_value,
        use_category=args.use_category,
        epsilon=args.epsilon,
        residential=not args.not_residential,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold(f"GUF — ε={fmt_eps(args.epsilon)}  area={args.area_slu} SLU  "
               f"use={args.use_category}"))
    print(fmt_table(["component", "value"], _scalar_rows(result)))


def _trust(args: argparse.Namespace) -> None:
    revenues = [float(v.strip()) for v in args.revenues.split(",")]
    result = guf_trust_inflow(
        guf_revenues=revenues,
        subsidies_absorbed=args.subsidies,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold("GUF trust inflow"))
    print(fmt_table(["key", "value"], _scalar_rows(result)))


def _writedown(args: argparse.Namespace) -> None:
    services_reset = (
        _parse_services_json(args.services_reset_json, "--services-reset-json")
        if args.services_reset_json else None
    )
    services_lost = None
    if args.pathway == "abandonment":
        if args.services_lost_json is None:
            print("error: --pathway abandonment requires --services-lost-json", file=sys.stderr)
            sys.exit(1)
        services_lost = _parse_services_json(args.services_lost_json, "--services-lost-json")

    result = ground_use_fee_writedown(
        area_slu=args.area_slu,
        location_value=args.location_value,
        use_category=args.use_category,
        epsilon=args.epsilon,
        services_reset=services_reset,
        services_lost=services_lost,
        amortization_years=args.amortization_years,
        residential=not args.not_residential,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    pathway_label = (
        green("restoration") if result["writedown_pathway"] == "restoration"
        else yellow("abandonment")
    )
    print(bold(f"GUF write-down — ε={fmt_eps(args.epsilon)}  pathway={pathway_label}  "
               f"area={args.area_slu} SLU  use={args.use_category}"))
    print(fmt_table(["component", "TEH/yr"], [
        ["base_fee",             fmt_float(result["base_fee"])],
        ["eco_surcharge (reset)",fmt_float(result["eco_surcharge"])],
        ["infra_premium",        fmt_float(result["infra_premium"])],
        ["rebuilding_surcharge", fmt_float(result["rebuilding_surcharge"])],
        ["─" * 20,               "─" * 10],
        ["guf_formula",          fmt_float(result["guf_formula"])],
        ["guf_applied",          fmt_float(result["guf_applied"])],
    ]))
    if result["floor_applied"]:
        print(yellow("  floor applied"))


def _rebuilding_surcharge(args: argparse.Namespace) -> None:
    services = _parse_services_json(args.services_json, "--services-json")
    result = rebuilding_surcharge(
        services_lost=services,
        epsilon=args.epsilon,
        amortization_years=args.amortization_years,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    print(bold(f"Rebuilding surcharge R_b — ε={fmt_eps(args.epsilon)}  "
               f"amortization={args.amortization_years:.0f} yr"))
    rows = [
        [s["label"], fmt_float(s["volume_lost"]), fmt_float(s["kappa_epsilon"]),
         fmt_float(s["contribution_teh"])]
        for s in result["by_service"]
    ]
    rows.append(["─" * 12, "─" * 10, "─" * 10, "─" * 12])
    rows.append(["total", "", "", fmt_float(result["surcharge_total"])])
    print(fmt_table(["service", "vol_lost", "κ(ε)", "TEH/yr"], rows))


def _accumulation_warning(args: argparse.Namespace) -> None:
    result = eoh_accumulation_warning(
        unfulfilled_eoh=args.unfulfilled,
        total_eoh=args.total,
        threshold=args.threshold,
    )

    if args.fmt == "json":
        print(json.dumps(result, indent=2))
        return

    status = red("WARNING") if result["warning"] else green("OK")
    print(bold(f"EOH accumulation — {status}"))
    print(fmt_table(["metric", "value"], [
        ["unfulfilled_eoh",  fmt_float(result["unfulfilled_eoh"])],
        ["total_eoh",        fmt_float(result["total_eoh"])],
        ["ratio",            fmt_pct(result["ratio"])],
        ["threshold",        fmt_pct(result["threshold"])],
        ["warning",          str(result["warning"])],
        ["accelerated_rho_review", str(result["accelerated_rho_review"])],
        ["ecology_fund_priority",  str(result["ecology_fund_priority"])],
    ]))


def _load_parcels(path: str) -> list[dict]:
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: cannot read parcel file {path!r}: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, list):
        print("error: parcel file must be a JSON array of parcel objects", file=sys.stderr)
        sys.exit(1)
    return data


def _inv_calculate(args: argparse.Namespace) -> None:
    parcels = _load_parcels(args.parcels)
    result  = compute_collective_guf(parcels, args.epsilon, args.median_income)

    if args.fmt == "json":
        out = {k: v for k, v in result.items() if k != "guf_by_parcel"}
        print(json.dumps(out, indent=2))
        return

    print(bold(f"Inventory GUF — {result['parcel_count']} parcels  ε={fmt_eps(args.epsilon)}"))
    print(fmt_table(["metric", "TEH/yr"], [
        ["guf_gross_revenue",  fmt_float(result["guf_gross_revenue"])],
        ["subsidies_absorbed", fmt_float(result["subsidies_absorbed"])],
        ["guf_net_inflow",     fmt_float(result["guf_net_inflow"])],
        ["psi (Ψ)",            f"{result['psi']:.4f}"],
    ]))


def _inv_sweep(args: argparse.Namespace) -> None:
    parcels    = _load_parcels(args.parcels)
    eps_values = [
        args.epsilon_start + i * (args.epsilon_end - args.epsilon_start) / max(args.steps - 1, 1)
        for i in range(args.steps)
    ]

    rows_data = []
    for eps in eps_values:
        r = compute_collective_guf(parcels, eps, args.median_income)
        rows_data.append({
            "epsilon":          eps,
            "psi":              r["psi"],
            "guf_gross_revenue": r["guf_gross_revenue"],
            "guf_net_inflow":   r["guf_net_inflow"],
        })

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    print(bold(f"Inventory GUF sweep — {len(parcels)} parcels  "
               f"ε={fmt_eps(args.epsilon_start)}→{fmt_eps(args.epsilon_end)}"))
    rows = [
        [fmt_eps(r["epsilon"]), f"{r['psi']:.3f}",
         fmt_float(r["guf_gross_revenue"]), fmt_float(r["guf_net_inflow"])]
        for r in rows_data
    ]
    print(fmt_table(["epsilon", "psi", "gross_revenue", "net_inflow"], rows))


def _inv_stress(args: argparse.Namespace) -> None:
    parcels = _load_parcels(args.parcels) if args.parcels else None
    result  = automation_levy_guf_stress(
        parcel_inventory=parcels,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        n_periods=args.periods,
        population=args.population,
        trust_balance=args.trust_balance,
        median_income=args.median_income,
    )

    if args.fmt == "json":
        out = {k: v for k, v in result.items() if k != "trajectory"}
        out["trajectory"] = result["trajectory"]
        print(json.dumps(out, indent=2))
        return

    traj = result["trajectory"]
    outcome_fn = green if result["outcome"] == "ADEQUATE" else (
        yellow if result["outcome"] == "PARTIAL" else red
    )
    print(bold(
        f"Automation→Levy→GUF stress — {result['parcel_count']} parcels  "
        f"ε={fmt_eps(args.epsilon_start)}→{fmt_eps(args.epsilon_end)}  "
        f"{args.periods} periods  outcome={outcome_fn(result['outcome'])}"
    ))
    print(f"  GUF peak: period {result['guf_peak_period']}  "
          f"levy peak: period {result['levy_peak_period']}  "
          f"crossover: {result['crossover_period']}  "
          f"first insolvency: {result['first_insolvency']}")
    print(f"  compensation adequacy: {result['compensation_adequacy']:.1%}")
    print()
    rows = [
        [str(r["period"]), fmt_eps(r["epsilon"]),
         fmt_float(r["levy_revenue"]), fmt_float(r["guf_net_inflow"]),
         f"{r['guf_levy_ratio']:.2f}",
         fmt_float(r["trust_end"]),
         green("Y") if r["solvent"] else red("N")]
        for r in traj
    ]
    print(fmt_table(
        ["period", "epsilon", "levy_rev", "guf_net", "guf/levy", "trust_end", "solv"],
        rows,
    ))
