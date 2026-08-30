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

  Measured inputs (the measurement spine):
    measured_sim  multiplier_sensitivity  infra_floor  knowledge_base
    personal_floor  food_conservation  ecological_floor  land_stewardship

  Thermal obligation carried in the ledger:
    thermal_load

  Autarky reference / overbuild:
    overbuild

  Feasibility ceiling:
    feasibility

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
  --thermal-obligation EOH     Planetary radiative obligation (thermal_load)
  --capital-stock TEH          Apparatus capital (overbuild)
  --adult-capacity H           Adult annual labour capacity (feasibility)
  --adult-share F              Adult share of population (feasibility)
  --epsilon-ref ε              Anchoring ε for the measured O*NET workforce
                               (knowledge_base; default: 0.40)
"""

from __future__ import annotations
import argparse
import json
import csv
import sys

from hours_eoh.data import H_REF
from hours_eoh.reference.land_stewardship import (
    ALLOCATION_POLICIES as _LAND_ALLOCATIONS,
)
from hours_eoh.scenarios.land_stewardship import (
    ADOPTED_SCOPE as _LAND_ADOPTED_SCOPE,
)
from hours_eoh.scenarios.land_stewardship import SCOPES as _LAND_SCOPES
from hours_eoh.scenarios.personal_floor import OBSERVED_CONVENTIONS
from hours_eoh.scenarios.thermal_load import REFERENCE_THERMAL_FLOW_EOH
from hours_eoh.data import LAND_HECTARES_PER_CAPITA
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
    "guf_sweep":           "guf_revenue_sweep() — GUF across the arc; monotone falling under the default psi_policy=retired",
    # -- measured inputs (the measurement spine) --
    "measured_sim":        "run_measured_simulation() — simulation with Condition II from the O*NET/BLS registry  [--periods]",
    "multiplier_sensitivity": "sensitivity_report() — multiplier robustness under weight perturbation + Monte Carlo",
    "infra_floor":         "doctrine_floor_invariance() — currency-free statutory floor vs the monetized path",
    "collective":          "collective_snapshot() — ONE collective end to end: pipeline + GUF + fisc on one stated frame. The documented institutional entry point  [--epsilon, --population]",
    "frame":               "frame_report() — jurisdiction frames: the population/land/capital pairing, and the 424x the undeclared shipped default flatters the ecological share; REPORTING ONLY  [--epsilon]",
    "ecological_floor":    "domain_balance_report() — the ecological anchor inverted: what stewardship intensity a given EOH share demands  [--epsilon, --hectares-per-capita]",
    "land_tenure":         "tenure_allocation() — unowned land is FEDERATION: the reset obligation split by tenure, with nothing uncollected; REPORTING ONLY",
    "restoration_cost":    "restoration_report() — labour-hours to reset a hectare, from ASAE field capacity; the legacy-stock and implied-κ readings; REPORTING ONLY  [--restorable-hectares, --amortization-years]",
    "servicing_census":    "census_report() + realized_vs_measured() — the SERVICING-cost census (BLS employment x ERS land use) against the GUF_USE_* x100 fit; REPORTING ONLY  [--scope]",
    "use_split":           "split_report() — the ten GUF_USE_* ratios decomposed into servicing + stewardship + policy; rho is indexed by USE CATEGORY, which is the bridge the land-class censuses could not provide; REPORTING ONLY",
    "guf_magnitude":       "magnitude_report() — GUF's magnitude: the DERIVED revenue target (servicing + stewardship, per the Phase 4 partition) and the two-part tariff the measured cost implies; REPORTING ONLY  [--epsilon, --scope]",
    "land_stewardship":    "census_report() + scope_comparison() — the US stewardship-hours census (ERS land use × BLS employment) against the anchor; REPORTING ONLY  [--scope]",
    "knowledge_base":      "knowledge_base_band() + epsilon_ref_fixed_point() — KNOWLEDGE_EOH_BASE from the measured O*NET training stock  [--epsilon-ref, --observed-hours]",
    "personal_floor":      "identity_report() — task-normative personal floor vs measured ATUS hours; REPORTING ONLY  [--epsilon, --convention, --atus-year]",
    "food_conservation":   "conservation_test() — did automation eliminate food labour, or relocate it? stage by stage  [--atus-year]",
    "care_curve":          "implied_weights() — measured personal obligation by age (self-maintenance + care received) vs the shipped AGE_GROUPS weights; REPORTING ONLY",
    # -- thermal obligation carried in the ledger --
    "thermal_load":        "thermal_load_verdict() — carry the planetary radiative obligation and report what it moves  [--thermal-obligation]",
    # -- autarky / overbuild --
    "overbuild":           "overbuild_check() — is the collective carrying its own weight, or is it overhead?  [--capital-stock, --epsilon]",
    # -- feasibility --
    "feasibility":         "over_determination_report() — is PERSONAL_EOH_BASE compatible with the labor supply?  [--adult-capacity, --adult-share]",
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
    run_p.add_argument("--hectares-per-capita", type=float,
                       default=LAND_HECTARES_PER_CAPITA, metavar="HA",
                       help=(f"Stewarded land per person, ha (ecological_floor; "
                             f"default: {LAND_HECTARES_PER_CAPITA} — a PLANETARY "
                             f"average, wrong for any actual collective; supply "
                             f"your own)"))

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

    # Autarky / overbuild
    run_p.add_argument("--capital-stock", type=float, default=1.9e9,
                       dest="capital_stock", metavar="TEH",
                       help="Apparatus capital stock in TEH (overbuild; default: 1.9e9 "
                            "= 1,900 TEH/capita at 1M population)")

    # Feasibility ceiling
    run_p.add_argument("--adult-capacity", type=float, default=None,
                       dest="adult_capacity", metavar="H",
                       help=f"Adult annual labor capacity, h/yr (feasibility; "
                            f"default: sweep the subsistence band, or {H_REF} for a "
                            f"single case)")
    run_p.add_argument("--adult-share", type=float, default=None,
                       dest="adult_share", metavar="F",
                       help="Adult share of population (feasibility; default: the "
                            "AGE_GROUPS working_age fraction, 0.60)")

    # Thermal obligation
    run_p.add_argument("--thermal-obligation", type=float,
                       default=REFERENCE_THERMAL_FLOW_EOH,
                       dest="thermal_obligation", metavar="EOH",
                       help=f"Annual planetary radiative obligation in EOH-hours "
                            f"(thermal_load; default: {REFERENCE_THERMAL_FLOW_EOH:,.0f} "
                            f"— the ε=0.40 reference for 1M people)")

    run_p.add_argument("--epsilon-ref", type=float, default=0.40,
                       dest="epsilon_ref", metavar="EPS",
                       help="Reference automation level the measured O*NET "
                            "workforce is anchored at (knowledge_base; default: "
                            "0.40). THE DOMINANT UNCERTAINTY — 7.13x across "
                            "[0.2, 0.6]; the band is reported regardless")

    run_p.add_argument("--observed-hours", type=float, default=937.3,
                       dest="observed_hours", metavar="H",
                       help="Measured human labour per capita per year, for the "
                            "ε_ref fixed point (knowledge_base; default: 937.3 — "
                            "US 2025 PAID labour. The full-labour reading, 1701.1, "
                            "has no solution: Finding B)")
    run_p.add_argument("--convention", default="unpaid_core",
                       choices=sorted(OBSERVED_CONVENTIONS),
                       help="Which measured hours count as personal-domain labour "
                            "(personal_floor; default: unpaid_core). A CONVENTION, "
                            "not a measurement — every option is reported anyway")
    run_p.add_argument("--atus-year", type=int, default=None, metavar="YYYY",
                       dest="atus_year",
                       help="ATUS survey year (personal_floor; default: the latest "
                            "comparable year. 2020 is excluded — partial collection)")
    run_p.add_argument("--scope", default=_LAND_ADOPTED_SCOPE,
                       choices=list(_LAND_SCOPES),
                       help="How much urban amenity groundskeeping counts as "
                            "ecological stewardship (land_stewardship; default: "
                            "declared, the signed-off weight). 'ecosystem' and "
                            "'with_amenity' are the corners, 50× apart — both "
                            "are printed regardless")
    run_p.add_argument("--allocation", default="held_out",
                       choices=list(_LAND_ALLOCATIONS),
                       help="How much of the held-out occupations to bring in "
                            "(land_stewardship; default: held_out, which errs "
                            "LOW). 'derived' adds the supervisory chain; 'area' "
                            "also spreads advisory occupations by land area — "
                            "the upper corner, neutral but not measured")
    run_p.add_argument("--amenity-weight", type=float, default=None,
                       dest="amenity_weight", metavar="W",
                       help="Fraction of amenity labour counted as stewardship, "
                            "∈[0,1] (land_stewardship). OVERRIDES --scope; the "
                            "anchor is crossed at w*=0.0228")

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
        # `population` is not a parameter of demographic_shock — the shock is
        # expressed as a magnitude against the shipped fiscal baseline, not
        # against a supplied headcount. Passing it raised TypeError on every
        # invocation (2026-08-17 audit).
        return demographic_shock(
            epsilon=epsilon,
            shock_type=args.shock_type or "decline",
            magnitude=args.shock_magnitude,
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
        # annual_eoh / fulfillment_fraction / years are REQUIRED and were never
        # passed. Defaults here are the CLI's, not the function's: the
        # infrastructure domain at the reference frame, chronic under-service,
        # and a decade — enough to show the compounding the scenario is about.
        from hours_eoh.core.eoh_generation import total_eoh
        return deferred_maintenance_crisis(
            epsilon=epsilon,
            annual_eoh=total_eoh(epsilon=epsilon, population=population)["infrastructure"],
            fulfillment_fraction=0.85,
            years=10,
        )

    if name == "care_delay":
        from hours_eoh.scenarios.maintenance import care_registration_delay
        return care_registration_delay(epsilon=epsilon)

    if name == "recovery":
        from hours_eoh.core.eoh_generation import total_eoh
        from hours_eoh.scenarios.maintenance import deferred_maintenance_crisis
        from hours_eoh.scenarios.recovery import maintenance_recovery_schedule
        # current_deferred / annual_eoh are REQUIRED and were never passed. The
        # backlog is taken from the crisis scenario above so the two agree
        # rather than each inventing a starting point.
        _annual = total_eoh(epsilon=epsilon, population=population)["infrastructure"]
        _crisis = deferred_maintenance_crisis(
            epsilon=epsilon, annual_eoh=_annual,
            fulfillment_fraction=0.85, years=10,
        )
        return maintenance_recovery_schedule(
            epsilon=epsilon,
            current_deferred=_crisis["final_deferred"],
            annual_eoh=_annual,
        )

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

    # -- measured inputs ------------------------------------------------------

    if name == "measured_sim":
        from hours_eoh.core.simulation import make_economy_state
        from hours_eoh.scenarios.measured import run_measured_simulation
        state = make_economy_state(epsilon=epsilon, population=population)
        return run_measured_simulation(state, n_periods=args.periods)

    if name == "multiplier_sensitivity":
        from hours_eoh.scenarios.multiplier_sensitivity import sensitivity_report
        return sensitivity_report()

    if name == "infra_floor":
        from hours_eoh.scenarios.infrastructure_floor import doctrine_floor_invariance
        return doctrine_floor_invariance()

    if name == "land_tenure":
        from hours_eoh.scenarios.land_tenure import tenure_allocation
        from hours_eoh.scenarios.servicing_census import census as _sv_census
        intensity = _sv_census("core")["hours_per_hectare_year"]
        # Declared tenure fractions are the CALLER'S; these illustrate the rule
        # at a stated, non-measured split and the report says so.
        rep = tenure_allocation(intensity, {
            "Land in rural parks and wildlife areas": 0.67,
            "Miscellaneous other land": 1.0,
        })
        lt_out: dict = {
            "intensity_h_per_ha_yr": rep["intensity_h_per_ha_year"],
            "federation_hours": rep["federation_hours"],
            "member_hours": rep["member_hours"],
            "total_hours": rep["total_hours"],
            "federation_share": rep["federation_share"],
            "uncollected_hours": rep["uncollected_hours"],
            "classes_without_declared_tenure": ", ".join(
                rep["classes_without_declared_tenure"]
            ),
            "note": rep["note"],
        }
        return lt_out

    if name == "restoration_cost":
        from hours_eoh.scenarios.restoration_cost import restoration_report
        rep = restoration_report(
            restorable_hectares=getattr(args, "restorable_hectares", None) or 100e6,
            amortization_years=getattr(args, "amortization_years", None) or 50.0,
        )
        rc_out: dict = {}
        for seq in rep["band"]["sequences"]:
            rc_out[f"{seq['sequence']} | establishment h/ha"] = (
                f"{seq['establishment_h_per_ha_low']:.3f}-{seq['establishment_h_per_ha_high']:.3f}"
            )
            rc_out[f"{seq['sequence']} | lifetime h/ha"] = (
                f"{seq['lifetime_h_per_ha_low']:.3f}-{seq['lifetime_h_per_ha_high']:.3f}"
            )
        s_ = rep["stock"]
        rc_out["restorable_hectares"] = s_["restorable_hectares"]
        rc_out["amortization_years"] = s_["amortization_years"]
        rc_out["legacy h/person.yr"] = (
            f"{s_['h_per_capita_low']:.5f}-{s_['h_per_capita_high']:.5f}"
        )
        rc_out["phase0 guess h/ha"] = s_["bounding_assumption_h_per_ha"]
        rc_out["guess overstated by"] = (
            f"{s_['guess_overstated_by_low']:.0f}x-{s_['guess_overstated_by_high']:.0f}x"
        )
        k_ = rep["kappa"]
        rc_out["implied kappa_carbon h/tonne"] = (
            f"{k_['implied_kappa_low']:.5f}-{k_['implied_kappa_high']:.5f}"
        )
        rc_out["shipped kappa_carbon (engineered)"] = k_["shipped_kappa_carbon"]
        rc_out["engineered over biological"] = (
            f"{k_['shipped_over_implied_high']:.0f}x-{k_['shipped_over_implied_low']:.0f}x"
        )
        rc_out["unpriced"] = ", ".join(u["class"] for u in rep["band"]["unpriced"])
        rc_out["verdict"] = rep["verdict"]
        rc_out["kappa_verdict"] = rep["kappa_verdict"]
        rc_out["coverage_note"] = rep["coverage_note"]
        return rc_out

    if name == "servicing_census":
        from hours_eoh.scenarios.servicing_census import census_report
        scope = getattr(args, "scope", None) or "core"
        if scope not in ("core", "broad", "urban_upper"):
            scope = "core"
        rep = census_report(scope)
        sv_out: dict = {
            "scope": rep["scope"],
            "workers": rep["workers"],
            "hours_per_worker_year": rep["hours_per_worker_year"],
            "serviced_hectares": rep["serviced_hectares"],
            "measured_h_per_ha_yr": rep["hours_per_hectare_year"],
            "measured_teh_per_slu_yr": rep["measured_teh_per_slu"],
            "shipped_mean_coefficient": rep["shipped_mean_coefficient"],
            "shipped_over_measured_mean": rep["shipped_over_measured_mean"],
            "shipped_over_measured_residential": rep["shipped_over_measured_residential"],
            "implied_scale_factor": rep["implied_scale_factor"],
            "shipped_scale_factor": rep["shipped_scale_factor"],
            "overshoot_factor": rep["overshoot_factor"],
            "scope_spread_factor": rep["scope_spread_factor"],
        }
        for fn, w in rep["by_function"].items():
            sv_out[f"workers | {fn}"] = w
        for row in rep["realized"]["rows"]:
            sv_out[f"{row['archetype']} | realised_h_per_ha"] = row["realised_h_per_ha"]
            sv_out[f"{row['archetype']} | vs {row['compared_against']}"] = row["ratio"]
        sv_out["realized_verdict"] = rep["realized"]["verdict"]
        sv_out["verdict"] = rep["verdict"]
        sv_out["what_this_does_not_settle"] = rep["what_this_does_not_settle"]
        return sv_out

    if name == "guf_magnitude":
        from hours_eoh.scenarios.guf_magnitude import magnitude_report
        gm_scope = getattr(args, "scope", None) or "core"
        if gm_scope not in ("core", "broad"):
            gm_scope = "core"
        rep = magnitude_report(epsilon=args.epsilon, servicing_scope=gm_scope)
        gm_out: dict = {
            "epsilon": rep["epsilon"],
            "servicing_scope": rep["servicing_scope"],
            "stewardship_scope": rep["stewardship_scope"],
        }
        # Option 1 — the derived target
        tvr = rep["target_vs_realised"]
        for row in tvr["rows"]:
            tag = row["archetype"]
            gm_out[f"{tag} | realised_h_per_ha"] = row["realised_h_per_ha"]
            gm_out[f"{tag} | target_h_per_ha"] = row["target_h_per_ha"]
            gm_out[f"{tag} | ratio"] = row["ratio"]
            gm_out[f"{tag} | like_for_like"] = row["like_for_like"]
        gm_out["target_verdict"] = tvr["verdict"]
        amen = rep["amenity_sensitivity"]
        gm_out["amenity | ratio_span"] = amen["ratio_span"]
        gm_out["amenity | spread_factor"] = amen["spread_factor"]
        gm_out["amenity | sign_robust"] = amen["sign_robust"]
        # Option 2 — the two-part tariff
        basis = rep["scaling_basis"]
        for b, share in basis["shares"].items():
            gm_out[f"cost scales with | {b}"] = share
        two = rep["two_part_rates"]
        gm_out["u_area_h_per_ha_yr"] = two["u_area_h_per_ha_yr"]
        gm_out["u_area_teh_per_slu_yr"] = two["u_area_teh_per_slu_yr"]
        gm_out["implied_scale_factor_area_only"] = two["implied_scale_factor_area_only"]
        gm_out["u_parcel_h_per_parcel_yr"] = two["u_parcel_h_per_parcel_yr"]
        gm_out["u_parcel_hours_total"] = two["u_parcel_hours_total"]
        gm_out["u_parcel_resolves_by"] = two["u_parcel_resolves_by"]
        gm_out["tariff_verdict"] = two["verdict"]
        sub = rep["subdivision"]
        gm_out["subdivision | invariant"] = sub["invariant"]
        gm_out["subdivision | verdict"] = sub["verdict"]
        gm_out["conservation_credit_verdict"] = rep["conservation_credit"]["verdict"]
        # The term-basis audit (memo step 1)
        tb = rep["term_basis"]
        for term, entry in tb["terms"].items():
            gm_out[f"basis | {term}"] = (
                f"{entry['basis']} · {entry['spec_direction']} · ε:{entry['epsilon_response']}"
            )
        gm_out["basis | verdict"] = tb["verdict"]
        pd = rep["psi_double"]
        gm_out["psi | alpha at 0.99"] = pd["alpha"]
        gm_out["psi | psi at 0.99"] = pd["psi"]
        gm_out["psi | combined at 0.99"] = pd["combined"]
        gm_out["psi | opposite signs at 0"] = pd["opposite_signs_at_zero"]
        gm_out["psi | double_application_verdict"] = pd["verdict"]
        pp = rep["psi_policies"]
        for row in pp["rows"]:
            gm_out[f"psi_policy | {row['psi_policy']}"] = " ".join(
                f"{e:g}:{v:,.0f}" for e, v in row["realised_h_per_ha"].items()
            )
        gm_out["psi_policy | flow_only == bell"] = pp["flow_only_equals_bell"]
        gm_out["psi_policy | verdict"] = pp["verdict"]
        gm_out["what_this_does_not_settle"] = rep["what_this_does_not_settle"]
        return gm_out

    if name == "use_split":
        from hours_eoh.scenarios.use_split import split_report
        rep = split_report()
        out: dict = {
            "spearman_fee_vs_disturbance": rep["ranks"]["spearman"],
            "categories":                  rep["ranks"]["n"],
            "disagreements":               len(rep["ranks"]["disagreements"]),
        }
        for row in rep["ranks"]["rows"]:
            out[f"{row['use_category']} | U"] = row["shipped_u"]
            out[f"{row['use_category']} | disturbance"] = row["disturbance"]
            out[f"{row['use_category']} | rank gap"] = row["rank_gap"]
        b = rep["basis"]
        out["basis_area_share"] = b["shares"]["area"]
        out["basis_parcel_share"] = b["shares"]["parcel"]
        out["basis_throughput_share"] = b["shares"]["throughput"]
        out["expressible_by_a_per_SLU_fee"] = b["expressible_now"]
        out["basis_verdict"] = b["verdict"]
        for k, v in rep["terms"].items():
            out[f"term | {k}"] = v
        out["verdict"] = rep["verdict"]
        return out

    if name == "collective":
        from hours_eoh.core.simulation import make_economy_state
        from hours_eoh.data import CAPITAL_STOCK_DEFAULT, TRUST_BASE_TEH
        from hours_eoh.land.collective import make_urban_collective
        from hours_eoh.scenarios.collective import collective_snapshot

        # The urban archetype is 302.5 ha, so the CLI default population is
        # scaled to it rather than left at the package 1e6 — pairing a million
        # people with 302 hectares is the undeclared-frame defect this scenario
        # exists to make impossible. Capital and Trust scale with it, because
        # both are declared "at the 1M reference population" in their tag blocks.
        pop = float(args.population) if args.population != 1_000_000.0 else 30_000.0
        state = make_economy_state(
            population=pop,
            capital_stock_teh=CAPITAL_STOCK_DEFAULT * pop / 1_000_000.0,
            trust_balance=TRUST_BASE_TEH * pop / 1_000_000.0,
            epsilon=args.epsilon,
        )
        rep = collective_snapshot(state, parcels=make_urban_collective())
        fr, gf, fi = rep["frame"], rep["guf"], rep["fiscal"]
        return {
            "epsilon":                 fr["epsilon"],
            "population":              fr["population"],
            "land_hectares":           fr["land_hectares"],
            "hectares_per_capita":     fr["hectares_per_capita"],
            "parcel_count":            fr["parcel_count"],
            "teh_created":             rep["pipeline"]["teh_created"],
            "ecological_eoh":          rep["pipeline"]["eoh_by_domain"]["ecological"],
            "guf_revenue":             gf["revenue"],
            "guf_relocated_obligation": gf["obligation"],
            "guf_over_levy":           fi["trust"]["guf_over_levy"],
            "levy_total":              fi["levies"]["total_levied"],
            "trust_end":               fi["trust"]["trust_end"],
            "solvent":                 fi["solvent"],
            "guf_verdict":             gf["verdict"],
            "verdict":                 rep["verdict"],
        }

    if name == "frame":
        from hours_eoh.scenarios.frame import frame_report
        rep = frame_report(epsilon=args.epsilon)
        frame_out: dict = {"epsilon": rep["epsilon"]}
        for row in rep["rows"]:
            tag = row["frame"]
            frame_out[f"{tag} | population"] = row["population"]
            frame_out[f"{tag} | ha_per_capita"] = row["hectares_per_capita"]
            frame_out[f"{tag} | ecological_share"] = row["ecological_share"]
            frame_out[f"{tag} | ecological_h_per_capita"] = row["ecological_h_per_cap"]
        frame_out["share_spread_factor"] = rep["share_spread"]
        frame_out["mismatch_verdict"] = rep["mismatch"]["verdict"]
        frame_out["verdict"] = rep["verdict"]
        return frame_out

    if name == "ecological_floor":
        from hours_eoh.scenarios.ecological_floor import domain_balance_report
        rep = domain_balance_report(
            epsilon=args.epsilon,
            hectares_per_capita=args.hectares_per_capita,
        )
        cur = rep["current"]
        eco_out: dict = {
            "epsilon": rep["epsilon"],
            "hectares_per_capita": rep["hectares_per_capita"],
            "ecological_share": cur["ecological_share"],
            "ecological_h_per_capita": cur["ecological_h_per_capita"],
            "implied_hours_per_hectare_year": cur["hours_per_hectare_year"],
        }
        for row in rep["requirements"]:
            key = f"required_h_per_ha_at_{row['target_share'] * 100:.0f}pc_share"
            eco_out[key] = row["required_hours_per_hectare_year"]
            eco_out[f"shortfall_factor_at_{row['target_share'] * 100:.0f}pc"] = (
                row["shortfall_factor"]
            )
        eco_out["verdict"] = rep["verdict"]
        return eco_out

    if name == "land_stewardship":
        from hours_eoh.scenarios.land_stewardship import (
            agency_report,
            allocation_band,
            field_capacity_report,
            amenity_curve,
            census_report,
            frame_report,
            scope_comparison,
        )
        rep = census_report(
            scope=args.scope,
            allocation=args.allocation,
            amenity_weight=args.amenity_weight,
        )
        cmp = scope_comparison()
        frame = frame_report()
        agency = agency_report()
        fieldcap = field_capacity_report()
        band = allocation_band(scope=args.scope)
        curve = amenity_curve(allocation=args.allocation)

        return {
            "scope": rep["scope"],
            "allocation": rep["allocation"],
            "amenity_weight": rep["amenity_weight"],
            "allocation_band": f"{band['band'][0]:.3f}–{band['band'][1]:.3f} h/ha·yr",
            "allocation_band_factor": band["band_factor"],
            "allocation_crosses_anchor": band["crosses_anchor"],
            "excluded_partial_hours": rep["excluded_partial_hours"],
            "amenity_weight_at_anchor": curve["anchor_crossing_weight"],
            "us_hectares_per_capita_frame": frame["us_hectares_per_capita"],
            "over_landed_vs_global_default": frame["ratio_to_shipped"],
            "frame_verdict": frame["verdict"],
            "agency_role_mix_adopted": agency["role_mix_adopted"],
            "agency_stewardship_h_per_ha": agency["stewardship_hours_per_hectare_year"],
            "agency_raw_h_per_ha": agency["raw_hours_per_hectare_year"],
            "agency_raw_overstates_by": agency["raw_overstates_by"],
            "agency_vs_forest": agency["vs_forest"],
            "cover_crop_h_per_ha_band": fieldcap["cover_crop_h_per_ha_band"],
            "cropland_adoption_ceiling_ratio": fieldcap["adoption_ceiling_ratio"],
            "cropland_priced": fieldcap["cropland_priced"],
            "agency_verdict": agency["verdict"],
            "field_capacity_verdict": fieldcap["verdict"],
            "jurisdiction": rep["jurisdiction"],
            "hours_per_worker_year": rep["hours_per_worker_year"],
            "floor_hours": rep["floor_hours"],
            "coverage": rep["coverage"],
            "measured_hours_per_hectare": rep["measured_hours_per_hectare"],
            "anchor_hours_per_hectare": rep["anchor_hours_per_hectare"],
            "ratio_to_anchor": rep["ratio_to_anchor"],
            "required_h_per_ha_at_1pc_share": rep["required_h_per_ha_at_1pc_share"],
            "us_hectares_per_capita": rep["us_hectares_per_capita"],
            "ecosystem_h_per_ha": (
                cmp["readings"]["ecosystem"]["measured_hours_per_hectare"]
            ),
            "with_amenity_h_per_ha": (
                cmp["readings"]["with_amenity"]["measured_hours_per_hectare"]
            ),
            "scope_spread_factor": cmp["spread_factor"],
            "held_out_occupations": ", ".join(
                f"{h['occ6']} {h['title']}" for h in rep["held_out_occupations"]
            ),
            "verdict": rep["verdict"],
            "scope_verdict": cmp["verdict"],
            "allocation_verdict": band["verdict"],
            "summary_table": [
                {
                    "land_use": r["land_use"],
                    "Mha": round(r["area_hectares"] / 1e6, 1),
                    "workers_k": (
                        "—" if r["workers"] is None else round(r["workers"] / 1e3, 1)
                    ),
                    "h_per_ha_yr": (
                        "— excluded, not zero"
                        if r["hours_per_hectare_year"] is None
                        else round(r["hours_per_hectare_year"], 3)
                    ),
                }
                for r in rep["by_class"]
            ],
        }

    if name == "knowledge_base":
        from hours_eoh.scenarios.knowledge_base import (
            domain_share_projection, epsilon_ref_fixed_point, knowledge_base_band,
            renewal_doctrine_comparison, workforce_training_stock,
        )
        band = knowledge_base_band()
        stock = workforce_training_stock()
        proj = domain_share_projection(epsilon_ref=args.epsilon_ref)
        doc = renewal_doctrine_comparison(epsilon_ref=args.epsilon_ref)
        kb_out: dict = {
            "measured_mean_hours_per_worker": stock["mean_hours_per_worker"],
            "covered_employment":             stock["covered_employment"],
            "winsorized_per_tail":            stock["n_winsorized_low"],
            "embodied_stock_per_capita":      doc["embodied_stock_per_capita"],
            "shipped_base_rate":              band["shipped_base_rate"],
            "base_rate_low":                  band["base_rate_low"],
            "base_rate_high":                 band["base_rate_high"],
            "epsilon_ref_spread":             band["epsilon_ref_spread"],
            "route_spread":                   band["route_spread"],
            "dominant_uncertainty":           band["dominant_uncertainty"],
            "note":                           band["note"],
        }
        for row in band["rows"]:
            key = f"base@eps_ref={row['epsilon_ref']:.2f}_{row['route']}"
            kb_out[key] = row["base_rate"]
        for dname, dd in doc["doctrines"].items():
            kb_out[f"renewal_rate_{dname}"] = dd["renewal_rate"]
            kb_out[f"h_per_worker_yr_{dname}"] = dd["hours_per_worker_year"]
            kb_out[f"work_year_share_{dname}"] = dd["work_year_share"]
            kb_out[f"credible_{dname}"] = dd["credible"]
        kb_out["renewal_verdict"] = doc["verdict"]
        kb_out["projection_decay"] = proj["decay"]
        for row in proj["rows"]:
            kb_out[f"projected_knowledge_h_pc@eps={row['epsilon']:.2f}"] = \
                row["knowledge_h_per_capita"]
            kb_out[f"projected_personal_share@eps={row['epsilon']:.2f}"] = \
                row["personal_share"]
            kb_out[f"projected_knowledge_share@eps={row['epsilon']:.2f}"] = \
                row["knowledge_share"]
        kb_out["projection_note"] = proj["note"]
        # Finding E: the anchor and the base solved together, not one then the other.
        fp = epsilon_ref_fixed_point(args.observed_hours)
        kb_out["fixed_point_observed_h"] = args.observed_hours
        kb_out["fixed_point_epsilon_ref"] = fp["epsilon_fixed_point"]
        kb_out["fixed_point_base_rate"] = fp["base_rate"]
        kb_out["fixed_point_converged"] = fp["converged"]
        kb_out["fixed_point_note"] = fp["note"]
        return kb_out

    if name == "care_curve":
        from hours_eoh.scenarios.care_curve import (
            elderly_routes, implied_weights, measured_population_shares, rivalry,
        )
        weights = implied_weights()
        routes = elderly_routes()
        riv = rivalry()
        shares = measured_population_shares()
        cc_out: dict = {
            "years_pooled":  ", ".join(str(y) for y in weights["years"]),
            "numeraire":     weights["numeraire"],
            "rho_active":    riv["active"]["rho"],
            "rho_passive":   riv["passive"]["rho"],
            "cost_of_four_active": riv["active"]["cost_of_four"],
        }
        for row in weights["rows"]:
            band = row["band"]
            cc_out[f"{band}_self_min_day"] = row["self_minutes_per_day"]
            cc_out[f"{band}_care_min_day"] = row["care_minutes_per_day"]
            cc_out[f"{band}_implied"] = row["implied_weight"]
            cc_out[f"{band}_shipped"] = row["shipped_weight"]
            cc_out[f"{band}_bound"] = row["bound"]
            cc_out[f"{band}_share_measured"] = shares[band]
        cc_out["implied_w"] = weights["implied_w"]
        cc_out["shipped_w"] = weights["shipped_w"]
        cc_out["elderly_roster_min_day"] = routes["roster_minutes_per_person_day"]
        cc_out["elderly_module_min_day"] = routes["module_minutes_per_person_day"]
        cc_out["elderly_route_ratio"] = routes["ratio"]
        cc_out["note"] = (
            "REPORTING ONLY. Infant and child totals are LOWER bounds — ATUS "
            "surveys nobody under 15, so their self-maintenance is unmeasured. "
            "The elderly band is complete and reads ~41% under the shipped 2.5, "
            "but ATUS covers the household population only and excludes the "
            "institutionalised elderly, who need the most care."
        )
        return cc_out

    if name == "personal_floor":
        from hours_eoh.scenarios.personal_floor import (
            climate_conditioning, floor_arc, floor_vs_constants, identity_report,
            observed_hours,
        )
        report = identity_report(year=args.atus_year, epsilon=epsilon,
                                 convention=args.convention)
        constants = floor_vs_constants(epsilon=epsilon)
        pf_out: dict = {
            "year":              report["year"],
            "convention":        report["convention"],
            "observed_h_per_capita": report["observed_hours"],
            "floor_priced":      report["floor_priced"],
            "basket_coverage":   report["coverage"],
            "residual":          report["residual"],
            "residual_terms":    " + ".join(report["residual_terms"]),
            "identified":        report["identified"],
        }
        for row in floor_arc():
            pf_out[f"floor@eps={row['epsilon']:.2f}"] = row["floor_hours"]
            pf_out[f"unreachable@eps={row['epsilon']:.2f}"] = len(row["unreachable"])
        for other in OBSERVED_CONVENTIONS:
            # report["year"] is the resolved year, so the selected convention's
            # figure here is the same one the identity above was computed from.
            pf_out[f"observed_{other}"] = observed_hours(report["year"], other)
        for cname, value in constants["constants_per_capita"].items():
            pf_out[f"{cname}_per_capita"] = value
            pf_out[f"floor_share_of_{cname}"] = constants["floor_share_of"][cname]
        # The climate caveat travels WITH the number, not in a docstring: the one
        # priced component is a rainfed tropical smallholder measurement.
        climate = climate_conditioning()
        pf_out["priced_and_climate_conditioned"] = ", ".join(
            climate["priced_and_climate_conditioned"]) or "none"
        pf_out["agro_ecology_of_measurement"] = climate["agro_ecology_of_measurement"]
        pf_out["transfer_bias_sign"] = (
            "undetermined" if climate["transfer_bias_sign"] is None else
            climate["transfer_bias_sign"])
        pf_out["climate_verdict"] = climate["verdict"]
        pf_out["verdict"] = constants["verdict"]
        pf_out["note"] = report["note"]
        return pf_out

    if name == "food_conservation":
        from hours_eoh.scenarios.food_conservation import (
            conservation_test, uncounted_headroom, unpaid_food_series,
        )
        r = conservation_test(year=args.atus_year)
        fc_out: dict = {
            "year": r["year"],
            "hours_per_worker_year_derived": r["hours_per_worker_year"],
        }
        for stage in r["stages"]:
            key = stage["stage"]
            fc_out[f"{key}_lsms"] = (
                stage["lsms_hours"] if stage["lsms_hours"] is not None else "UNMEASURED")
            fc_out[f"{key}_us_paid"] = stage["us_paid_hours"]
            fc_out[f"{key}_us_unpaid"] = stage["us_unpaid_hours"]
            fc_out[f"{key}_us_total"] = stage["us_total_hours"]
        fc_out["us_total"] = r["us_total"]
        fc_out["us_total_is_lower_bound"] = r["us_total_is_lower_bound"]
        fc_out["lsms_total_measured"] = r["lsms_total_measured"]
        fc_out["production_ratio"] = r["production_ratio"]
        series = unpaid_food_series()
        fc_out["unpaid_preparation_change_2003_2025"] = series["preparation_change"]
        fc_out["unpaid_provisioning_change_2003_2025"] = series["provisioning_change"]
        fc_out["headroom_per_1pct_employment"] = \
            uncounted_headroom(0.01)["hours_per_capita"]
        fc_out["verdict"] = r["verdict"]
        fc_out["caveat"] = r["caveat"]
        return fc_out

    # -- thermal obligation ---------------------------------------------------

    if name == "overbuild":
        from hours_eoh.core.autarky import (
            autarky_reference, break_even_epsilon, overbuild_check, payback,
        )
        k = args.capital_stock
        c = overbuild_check(k, population, epsilon=epsilon)
        pb = payback(k, population, epsilon=epsilon)
        out: dict = {kk: v for kk, v in c.items()}
        out["break_even_epsilon"] = break_even_epsilon(k, population)
        out["payback_years"] = pb["payback_years"]
        out["payback_verdict"] = pb["verdict"]
        # a sweep so the interior optimum is visible, not just the point verdict
        rows = []
        for kpc in (0.0, 250.0, 1_000.0, 4_145.0, 20_000.0, 100_000.0):
            cc = overbuild_check(kpc * population, population, epsilon=epsilon)
            rows.append({
                "K_per_capita": kpc,
                "abatement": round(cc["abatement"], 4),
                "obligation_pc": round(cc["obligation_with_apparatus"] / population, 1),
                "overhead_pc": round(cc["overhead"] / population, 1),
                "total_pc": round(cc["total"] / population, 1),
                "net_vs_autarky_pc": round(cc["net_vs_autarky"] / population, 1),
                "verdict": cc["verdict"],
            })
        out["summary_table"] = rows
        return out

    if name == "feasibility":
        from hours_eoh.scenarios.feasibility import (
            feasibility_check, over_determination_report,
        )
        r = over_determination_report()
        out: dict = {k: v for k, v in r.items()
                     if k not in ("subsistence_cases", "self_consistency")}
        out["ceiling_band"] = str(tuple(round(x) for x in r["ceiling_band"]))
        # self-consistency arm first — it needs no external data
        for k, v in r["self_consistency"].items():
            out[f"self_{k}"] = v
        if args.adult_capacity is not None or args.adult_share is not None:
            c = feasibility_check(
                adult_capacity_h_yr=args.adult_capacity or float(H_REF),
                adult_share=args.adult_share,
                epsilon=epsilon,
            )
            out["summary_table"] = [dict(c)]
        else:
            out["summary_table"] = [dict(c) for c in r["subsistence_cases"]]
        return out

    if name == "thermal_load":
        from hours_eoh.scenarios.thermal_load import thermal_load_verdict
        v = thermal_load_verdict(
            thermal_obligation=args.thermal_obligation,
            population=population,
        )
        # Reshape at the CLI boundary: the display layer renders "summary_table"
        # as the period table with the scalars printed above it.
        out = {k: val for k, val in v.items() if k != "rows"}
        out["coverage_below_one_at"] = str(v["coverage_below_one_at"])
        out["summary_table"] = v["rows"]
        return out

    raise ValueError(f"Unknown scenario: {name}")
