"""
guf — Ground Use Fee calculations (NLSA TM-0042).

  eoh guf calculate --epsilon ε [options]
  eoh guf trust     --revenues V1,V2,...
"""

from __future__ import annotations
import argparse
import json

from hours_eoh.land.guf import ground_use_fee, guf_trust_inflow

from utils.formatters import bold, fmt_float, fmt_eps, table as fmt_table


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("guf", help="Ground Use Fee calculations")
    sub2 = p.add_subparsers(dest="guf_cmd", required=True)

    calc = sub2.add_parser("calculate", help="Compute GUF for a parcel")
    calc.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    calc.add_argument("--area-slu", type=float, default=1.0, dest="area_slu",
                      help="Area in Standard Land Units (default: 1.0)")
    calc.add_argument("--location-value", type=float, default=1.0,
                      dest="location_value",
                      help="Location value index (default: 1.0)")
    calc.add_argument("--use-category", default="residential_primary",
                      dest="use_category",
                      choices=["residential_primary", "residential_secondary",
                                "agricultural_active", "agricultural_fallow",
                                "commercial_retail", "commercial_office",
                                "industrial_light", "industrial_heavy",
                                "institutional", "conservation"],
                      help="Land use category (default: residential_primary)")
    calc.add_argument("--not-residential", action="store_true", dest="not_residential",
                      help="Mark parcel as non-residential")
    calc.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    calc.set_defaults(func=_calculate)

    trust = sub2.add_parser("trust", help="GUF trust inflow from a set of revenues")
    trust.add_argument("--revenues", required=True, metavar="V1,V2,...",
                       help="Comma-separated GUF revenue values")
    trust.add_argument("--subsidies", type=float, default=0.0,
                       help="Subsidies absorbed (default: 0.0)")
    trust.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    trust.set_defaults(func=_trust)


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
    print(fmt_table(
        ["component", "value"],
        [[str(k), fmt_float(float(v)) if isinstance(v, (int, float)) else str(v)]
         for k, v in result.items()]
    ))


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
    print(fmt_table(
        ["key", "value"],
        [[str(k), fmt_float(float(v)) if isinstance(v, (int, float)) else str(v)]
         for k, v in result.items()]
    ))
