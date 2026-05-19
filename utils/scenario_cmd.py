"""
scenario — run named scenario functions and display results.

  eoh scenario list
  eoh scenario run <name> [options] [--format table|json|csv]

Available scenarios (use 'eoh scenario list' for full descriptions):

  Original shock / maintenance scenarios:
    sweep               automation_failure  demographic_shock
    ecological_spike    maintenance_crisis  care_delay  recovery

  New shock scenarios:
    labor_income_shock  compound_shock

  Multi-period trajectory scenarios:
    canonical_arc  trust_stress  transition

  Industrial overshoot:
    indust_baseline  indust_recovery

  GUF stress scenarios:
    guf_integration  guf_writedown  guf_sweep

Key options (not all apply to every scenario):
  --epsilon ε                  Automation level (default: 0.40)
  --population N               Population (default: 1 000 000)
  --periods N                  Simulation periods (default: 20)
  --epsilon-start / --end      Arc start/end for trajectory scenarios
  --epsilon-delta RATE         Fixed Δε per period (transition)
  --income-fraction F          Labor income shock fraction (default: 1.0)
  --shock-type TYPE            growth|decline|aging (demographic / compound)
  --shock-magnitude F          Shock magnitude (default: 0.10)
  --ecology-collapse           Enable ecological component in compound_shock
  --ecosystem-health-before F  Pre-shock ecosystem health (default: 0.70)
  --ecosystem-health-after F   Post-shock ecosystem health (default: 0.30)
  --automation-fraction-lost F Automation dropout fraction (default: 0.0)
  --pathway PATH               restoration|abandonment for guf_writedown
  --unfulfilled-eoh F          Unmet ecological EOH for guf_writedown
  --total-eoh-zone F           Zone total EOH for guf_writedown
  --area-slu F                 Parcel area SLU for GUF scenarios (default: 3.5)
  --location-value F           Parcel LVI for GUF scenarios (default: 0.629)
  --use-category CAT           Land use category for GUF scenarios
  --restoration-rate F         Ecological restoration rate (default: 0.05)
"""

from __future__ import annotations
import argparse
import json
import csv
import sys

from utils.formatters import bold, dim, fmt_float, fmt_eps, table as fmt_table

_SCENARIOS: dict[str, str] = {
    # -- original --
    "sweep":               "epsilon_sweep() — arc coherence from ε=0 to ε=0.99",
    "automation_failure":  "automation_failure_shock() — sudden machine EOH dropout",
    "demographic_shock":   "demographic_shock() — population age-structure shift  [--shock-type, --shock-magnitude]",
    "ecological_spike":    "ecological_eoh_spike() — threshold ecosystem EOH surge  [--ecosystem-health-before/after]",
    "maintenance_crisis":  "deferred_maintenance_crisis() — compounding deferred backlog",
    "care_delay":          "care_registration_delay() — lag in care EOH admission",
    "recovery":            "maintenance_recovery_schedule() — backlog paydown arc",
    # -- new shocks --
    "labor_income_shock":  "labor_income_shock() — wage compression / automation displacement  [--income-fraction]",
    "compound_shock":      "compound_shock() — simultaneous multi-axis shock  [--ecology-collapse, --shock-type, --automation-fraction-lost]",
    # -- multi-period trajectories --
    "canonical_arc":       "canonical_arc_trajectory() — full ε arc over N periods  [--epsilon-start, --epsilon-end, --periods]",
    "trust_stress":        "trust_depletion_stress() — multi-stressor Trust depletion  [--epsilon, --periods]",
    "transition":          "automation_transition_trajectory() — fixed Δε convergence  [--epsilon-start, --epsilon-delta, --periods]",
    # -- industrial overshoot --
    "indust_baseline":     "indust_overshoot_baseline() — industrial overshoot fiscal snapshot",
    "indust_recovery":     "indust_recovery_trajectory() — ecosystem recovery from overshoot  [--restoration-rate, --periods]",
    # -- GUF stress --
    "guf_integration":     "guf_fiscal_integration() — GUF revenue vs. levy deficit  [--area-slu, --location-value, --use-category]",
    "guf_writedown":       "guf_writedown_scenario() — ecological write-down pathways  [--pathway, --unfulfilled-eoh, --total-eoh-zone]",
    "guf_sweep":           "guf_revenue_sweep() — GUF across the Ψ(ε) bell curve",
}

_USE_CATEGORIES = [
    "residential_primary", "residential_secondary",
    "agricultural_active", "agricultural_fallow",
    "commercial_retail", "commercial_office",
    "industrial_light", "industrial_heavy",
    "institutional", "conservation",
]


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("scenario", help="Run named scenario functions")
    sub2 = p.add_subparsers(dest="scenario_cmd", required=True)

    sub2.add_parser("list", help="List available scenarios").set_defaults(func=_list)

    run_p = sub2.add_parser("run", help="Run a named scenario",
                             formatter_class=argparse.RawDescriptionHelpFormatter)
    run_p.add_argument("name", choices=list(_SCENARIOS.keys()), metavar="NAME")
    run_p.add_argument("--format", choices=["table", "json", "csv"],
                       default="table", dest="fmt")

    # Universal params
    run_p.add_argument("--epsilon", type=float, default=0.40, metavar="ε",
                       help="Automation level (default: 0.40)")
    run_p.add_argument("--population", type=float, default=1_000_000.0,
                       help="Population (default: 1 000 000)")

    # Trajectory params
    run_p.add_argument("--periods", type=int, default=20,
                       help="Simulation periods (default: 20)")
    run_p.add_argument("--epsilon-start", type=float, default=0.0,
                       dest="epsilon_start", metavar="ε",
                       help="Arc start ε (canonical_arc, transition; default: 0.0)")
    run_p.add_argument("--epsilon-end", type=float, default=0.99,
                       dest="epsilon_end", metavar="ε",
                       help="Arc end ε (canonical_arc; default: 0.99)")
    run_p.add_argument("--epsilon-delta", type=float, default=0.05,
                       dest="epsilon_delta", metavar="RATE",
                       help="Δε per period (transition; default: 0.05)")
    run_p.add_argument("--restoration-rate", type=float, default=0.05,
                       dest="restoration_rate",
                       help="Ecological restoration rate/period (default: 0.05)")

    # Shock params
    run_p.add_argument("--income-fraction", type=float, default=1.0,
                       dest="income_fraction",
                       help="Labor income as fraction of baseline (default: 1.0)")
    run_p.add_argument("--shock-type", choices=["growth", "decline", "aging"],
                       default=None, dest="shock_type",
                       help="Demographic shock type (default: decline)")
    run_p.add_argument("--shock-magnitude", type=float, default=0.10,
                       dest="shock_magnitude",
                       help="Demographic shock magnitude (default: 0.10)")
    run_p.add_argument("--ecology-collapse", action="store_true",
                       dest="ecology_collapse",
                       help="Enable ecological shock component (compound_shock)")
    run_p.add_argument("--ecosystem-health-before", type=float, default=0.70,
                       dest="ecosystem_health_before",
                       help="Ecosystem health before shock (default: 0.70)")
    run_p.add_argument("--ecosystem-health-after", type=float, default=0.30,
                       dest="ecosystem_health_after",
                       help="Ecosystem health after shock (default: 0.30)")
    run_p.add_argument("--automation-fraction-lost", type=float, default=0.0,
                       dest="automation_fraction_lost",
                       help="Fraction of automation lost (compound_shock; default: 0.0)")

    # GUF params
    run_p.add_argument("--pathway", choices=["restoration", "abandonment"],
                       default="restoration",
                       help="Write-down pathway (guf_writedown; default: restoration)")
    run_p.add_argument("--unfulfilled-eoh", type=float, default=400_000.0,
                       dest="unfulfilled_eoh",
                       help="Unmet ecological EOH (guf_writedown; default: 400 000)")
    run_p.add_argument("--total-eoh-zone", type=float, default=1_200_000.0,
                       dest="total_eoh_zone",
                       help="Zone total EOH (guf_writedown; default: 1 200 000)")
    run_p.add_argument("--area-slu", type=float, default=3.5,
                       dest="area_slu",
                       help="Parcel area in SLU (GUF scenarios; default: 3.5)")
    run_p.add_argument("--location-value", type=float, default=0.629,
                       dest="location_value",
                       help="Parcel location value index (GUF scenarios; default: 0.629)")
    run_p.add_argument("--use-category", default="residential_primary",
                       dest="use_category", choices=_USE_CATEGORIES,
                       help="Land use category (GUF scenarios; default: residential_primary)")

    run_p.set_defaults(func=_run)


def _list(args: argparse.Namespace) -> None:
    print(bold("Available scenarios:"))
    for name, desc in _SCENARIOS.items():
        print(f"  {name:<22} {desc}")


def _run(args: argparse.Namespace) -> None:
    result = _dispatch(args)

    if args.fmt == "json":
        # Strip 'raw' — it duplicates the full run_simulation() output and is large
        if isinstance(result, dict):
            result = {k: v for k, v in result.items() if k != "raw"}
        print(json.dumps(result, indent=2, default=str))
        return

    # Trajectory scenarios: show the inner list as the primary table
    display = result
    if isinstance(result, dict):
        if "summary_table" in result:
            display = result["summary_table"]
        elif "trajectory" in result:
            display = result["trajectory"]

    if isinstance(display, list) and display and isinstance(display[0], dict):
        keys = list(display[0].keys())
        if args.fmt == "csv":
            writer = csv.DictWriter(sys.stdout, fieldnames=keys)
            writer.writeheader()
            for row in display:
                writer.writerow({k: str(v) for k, v in row.items()})
            return
        # Print scalar summary above the period table when displaying inner list
        if isinstance(result, dict) and display is not result:
            _print_scalar_summary(result)
        print(fmt_table(keys, [[str(r.get(k, "")) for k in keys] for r in display]))
        return

    if isinstance(display, dict):
        if args.fmt == "csv":
            writer = csv.writer(sys.stdout)
            for k, v in display.items():
                writer.writerow([k, v])
            return
        print(fmt_table(["key", "value"], [[str(k), str(v)] for k, v in display.items()]))
        return

    print(display)


def _print_scalar_summary(result: dict) -> None:
    scalars = {
        k: v for k, v in result.items()
        if isinstance(v, (int, float, str, bool)) and k != "raw"
    }
    if scalars:
        print(fmt_table(["key", "value"], [[str(k), str(v)] for k, v in scalars.items()]))
        print()


def _dispatch(args: argparse.Namespace) -> object:
    name       = args.name
    epsilon    = args.epsilon
    population = args.population

    # -- original scenarios ---------------------------------------------------

    if name == "sweep":
        from hours_eoh.scenarios.sweep import epsilon_sweep
        return epsilon_sweep()

    if name == "automation_failure":
        from hours_eoh.scenarios.shocks import automation_failure_shock
        return automation_failure_shock(epsilon=epsilon, population=population)

    if name == "demographic_shock":
        from hours_eoh.scenarios.shocks import demographic_shock
        return demographic_shock(
            epsilon=epsilon,
            shock_type=args.shock_type or "decline",
            magnitude=args.shock_magnitude,
            population=population,
        )

    if name == "ecological_spike":
        from hours_eoh.scenarios.shocks import ecological_eoh_spike
        return ecological_eoh_spike(
            epsilon=epsilon,
            ecosystem_health_before=args.ecosystem_health_before,
            ecosystem_health_after=args.ecosystem_health_after,
        )

    if name == "maintenance_crisis":
        from hours_eoh.scenarios.maintenance import deferred_maintenance_crisis
        return deferred_maintenance_crisis(epsilon=epsilon)

    if name == "care_delay":
        from hours_eoh.scenarios.maintenance import care_registration_delay
        return care_registration_delay(epsilon=epsilon)

    if name == "recovery":
        from hours_eoh.scenarios.recovery import maintenance_recovery_schedule
        return maintenance_recovery_schedule(epsilon=epsilon)

    # -- new shock scenarios --------------------------------------------------

    if name == "labor_income_shock":
        from hours_eoh.scenarios.shocks import labor_income_shock
        return labor_income_shock(
            epsilon=epsilon,
            income_fraction=args.income_fraction,
            population=population,
        )

    if name == "compound_shock":
        from hours_eoh.scenarios.shocks import compound_shock
        dem_spec = (
            {"shock_type": args.shock_type, "magnitude": args.shock_magnitude}
            if args.shock_type is not None else None
        )
        return compound_shock(
            epsilon=epsilon,
            ecology_collapse=args.ecology_collapse,
            ecosystem_health_before=args.ecosystem_health_before,
            ecosystem_health_after=args.ecosystem_health_after,
            demographic_shock_spec=dem_spec,
            automation_fraction_lost=args.automation_fraction_lost,
            population=population,
        )

    # -- multi-period trajectories --------------------------------------------

    if name == "canonical_arc":
        from hours_eoh.scenarios.long_run import canonical_arc_trajectory
        return canonical_arc_trajectory(
            epsilon_start=args.epsilon_start,
            epsilon_end=args.epsilon_end,
            n_periods=args.periods,
            population=population,
        )

    if name == "trust_stress":
        from hours_eoh.scenarios.long_run import trust_depletion_stress
        return trust_depletion_stress(
            epsilon=epsilon,
            n_periods=args.periods,
            population=population,
        )

    if name == "transition":
        from hours_eoh.scenarios.long_run import automation_transition_trajectory
        return automation_transition_trajectory(
            epsilon_start=args.epsilon_start,
            epsilon_delta=args.epsilon_delta,
            n_periods=args.periods,
            population=population,
        )

    # -- industrial overshoot -------------------------------------------------

    if name == "indust_baseline":
        from hours_eoh.scenarios.indust_overshoot import indust_overshoot_baseline
        return indust_overshoot_baseline(population=population, epsilon=epsilon)

    if name == "indust_recovery":
        from hours_eoh.scenarios.indust_overshoot import indust_recovery_trajectory
        return indust_recovery_trajectory(
            population=population,
            epsilon=epsilon,
            ecological_restoration_rate=args.restoration_rate,
            n_periods=args.periods,
        )

    # -- GUF stress scenarios -------------------------------------------------

    if name == "guf_integration":
        from hours_eoh.scenarios.guf_stress import guf_fiscal_integration
        return guf_fiscal_integration(
            epsilon=epsilon,
            parcel_configs=[{
                "area_slu":       args.area_slu,
                "location_value": args.location_value,
                "use_category":   args.use_category,
            }],
        )

    if name == "guf_writedown":
        from hours_eoh.scenarios.guf_stress import guf_writedown_scenario
        return guf_writedown_scenario(
            epsilon=epsilon,
            unfulfilled_eoh=args.unfulfilled_eoh,
            total_eoh=args.total_eoh_zone,
            pathway=args.pathway,
        )

    if name == "guf_sweep":
        from hours_eoh.scenarios.guf_stress import guf_revenue_sweep
        return guf_revenue_sweep()

    raise ValueError(f"Unknown scenario: {name}")
