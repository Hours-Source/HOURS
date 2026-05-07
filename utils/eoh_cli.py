#!/usr/bin/env python3
"""
eoh — HOURS EOH research CLI.

Commands:
  arc          Sweep the epsilon arc
  dashboard    System health snapshot at a given ε
  params       Inspect and modify EohParams
  scenario     Run named scenario functions
  simulate     Multi-period simulation
  sensitivity  Parameter sensitivity analysis
  guf          Ground Use Fee calculations
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Allow running directly from repo root without install
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import formatters

# Sub-command modules (imported lazily inside handlers to keep startup fast)
import utils.arc_cmd as arc_cmd
import utils.dashboard_cmd as dashboard_cmd
import utils.params_cmd as params_cmd
import utils.scenario_cmd as scenario_cmd
import utils.simulate_cmd as simulate_cmd
import utils.sensitivity_cmd as sensitivity_cmd
import utils.guf_cmd as guf_cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eoh",
        description="HOURS EOH research CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI color output")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    arc_cmd.build_parser(sub)
    dashboard_cmd.build_parser(sub)
    params_cmd.build_parser(sub)
    scenario_cmd.build_parser(sub)
    simulate_cmd.build_parser(sub)
    sensitivity_cmd.build_parser(sub)
    guf_cmd.build_parser(sub)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.no_color:
        formatters.set_color(False)

    args.func(args)


if __name__ == "__main__":
    main()
