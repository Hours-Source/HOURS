"""
scenario — run named scenario functions and display results.

  eoh scenario list
  eoh scenario run <name> [--epsilon ε] [--population N] [--format table|json]

Available scenarios:
  sweep               epsilon_sweep() — arc coherence across ε=0..0.99
  automation_failure  automation_failure_shock()
  demographic_shock   demographic_shock()
  ecological_spike    ecological_eoh_spike()
  maintenance_crisis  deferred_maintenance_crisis()
  care_delay          care_registration_delay()
  recovery            maintenance_recovery_schedule()
"""

from __future__ import annotations
import argparse
import json
import csv
import sys

from utils.formatters import bold, dim, fmt_float, fmt_eps, table as fmt_table

_SCENARIOS: dict[str, str] = {
    "sweep":               "epsilon_sweep() — arc coherence from ε=0 to ε=0.99",
    "automation_failure":  "automation_failure_shock() — sudden machine EOH dropout",
    "demographic_shock":   "demographic_shock() — population age-structure shift",
    "ecological_spike":    "ecological_eoh_spike() — ecosystem EOH surge",
    "maintenance_crisis":  "deferred_maintenance_crisis() — compounding deferred backlog",
    "care_delay":          "care_registration_delay() — lag in care EOH admission",
    "recovery":            "maintenance_recovery_schedule() — backlog paydown arc",
}


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("scenario", help="Run named scenario functions")
    sub2 = p.add_subparsers(dest="scenario_cmd", required=True)

    sub2.add_parser("list", help="List available scenarios").set_defaults(func=_list)

    run_p = sub2.add_parser("run", help="Run a named scenario")
    run_p.add_argument("name", choices=list(_SCENARIOS.keys()), metavar="NAME")
    run_p.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    run_p.add_argument("--population", type=float, default=1_000_000.0)
    run_p.add_argument("--format", choices=["table", "json", "csv"],
                       default="table", dest="fmt")
    run_p.set_defaults(func=_run)


def _list(args: argparse.Namespace) -> None:
    print(bold("Available scenarios:"))
    for name, desc in _SCENARIOS.items():
        print(f"  {name:<22} {desc}")


def _run(args: argparse.Namespace) -> None:
    result = _dispatch(args.name, args.epsilon, args.population)

    if args.fmt == "json":
        print(json.dumps(result, indent=2, default=str))
        return

    # Flatten list-of-dict results into table/csv
    if isinstance(result, list) and result and isinstance(result[0], dict):
        keys = list(result[0].keys())
        if args.fmt == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=keys)
            writer.writeheader()
            for row in result:
                writer.writerow({k: str(v) for k, v in row.items()})
            return
        rows = [[str(r.get(k, "")) for k in keys] for r in result]
        print(fmt_table(keys, rows))
        return

    # Dict result
    if isinstance(result, dict):
        if args.fmt == "csv":
            writer = csv.writer(sys.stdout)
            for k, v in result.items():
                writer.writerow([k, v])
            return
        print(fmt_table(["key", "value"], [[str(k), str(v)] for k, v in result.items()]))
        return

    print(result)


def _dispatch(name: str, epsilon: float, population: float) -> object:
    if name == "sweep":
        from hours_eoh.scenarios.sweep import epsilon_sweep
        return epsilon_sweep()

    if name == "automation_failure":
        from hours_eoh.scenarios.shocks import automation_failure_shock
        return automation_failure_shock(epsilon=epsilon, population=population)

    if name == "demographic_shock":
        from hours_eoh.scenarios.shocks import demographic_shock
        return demographic_shock(epsilon=epsilon, population=population)

    if name == "ecological_spike":
        from hours_eoh.scenarios.shocks import ecological_eoh_spike
        return ecological_eoh_spike(epsilon=epsilon, population=population)

    if name == "maintenance_crisis":
        from hours_eoh.scenarios.maintenance import deferred_maintenance_crisis
        return deferred_maintenance_crisis(epsilon=epsilon)

    if name == "care_delay":
        from hours_eoh.scenarios.maintenance import care_registration_delay
        return care_registration_delay(epsilon=epsilon)

    if name == "recovery":
        from hours_eoh.scenarios.recovery import maintenance_recovery_schedule
        return maintenance_recovery_schedule(epsilon=epsilon)

    raise ValueError(f"Unknown scenario: {name}")
