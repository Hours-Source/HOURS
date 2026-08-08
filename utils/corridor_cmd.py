"""
corridor — the stability corridor [ε_suff, ε_max] and its binding invariants.

Success in this framework is a stable feasible band, not ε → 1 (author sign-off
2026-08-01). This command composes the survival floor with the invariant ceilings
and reports the band, which ceiling binds it, and whether it is open at all.

Two subcommands:

  band   the corridor at a given physical state, with every ceiling listed
  axes   both contestability axes side by side — the adopted §8.9 three-channel
         financeability test and the SUPERSEDED bare-χ test — and whether they
         agree. This exists because they disagree at defaults, and the corridor
         previously ran on the retired one.
"""

from __future__ import annotations

import argparse
import json

from hours_eoh.data import TRUST_BASE_TEH
from hours_eoh.research.corridor import (
    contestability_axes,
    contestability_ceiling,
    contestability_ceiling_bare_chi,
    corridor,
    overbuild_floor,
    survival_floor,
    survival_floor_epsilon,
    survival_inventory,
    thermal_ceiling,
)

from utils.formatters import bold, dim, green, red, table, fmt_eps, fmt_float


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "corridor",
        help="[EXPERIMENTAL] Stability corridor [ε_suff, ε_max] and its ceilings",
    )
    sub2 = p.add_subparsers(dest="corridor_cmd", required=True)

    band = sub2.add_parser("band", help="The corridor and its binding ceiling")
    band.add_argument("--epsilon", type=float, default=0.40, metavar="ε",
                      help="ε at which the EOH inventory is taken (default: 0.40)")
    band.add_argument("--population", type=float, default=1_000_000.0)
    band.add_argument("--available-labor", type=float, default=1.0e9,
                      dest="available_labor", metavar="EOH",
                      help="Human labor capacity, EOH-hours/yr (default: 1e9)")
    band.add_argument("--standard", choices=["survival", "collapsed", "sufficiency"],
                      default="survival",
                      help="Personal-EOH standard for the LOWER bound (default: "
                           "survival — the floor is a survival floor). 'sufficiency' "
                           "reports the automation needed for a decent life, which is "
                           "a different and larger number")
    band.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH,
                      dest="trust_balance",
                      help="Trust corpus — used by the superseded χ arm only")
    band.add_argument("--regime", choices=["increasing_returns", "replicable"],
                      default="increasing_returns",
                      help="K_entry regime (default: increasing_returns, adversarial)")
    band.add_argument("--phi-policy", choices=["dilution", "target", "escalated"],
                      default="dilution", dest="phi_policy",
                      help="Charter policy for the adopted axis (default: dilution)")
    band.add_argument("--bare-chi", action="store_true", dest="bare_chi",
                      help="Use the SUPERSEDED bare-χ contestability axis instead "
                           "of the adopted §8.9 test (reproduces the pre-migration "
                           "closed-corridor result)")
    band.add_argument("--capital-stock", type=float, default=1.9e9,
                      dest="capital_stock", metavar="TEH",
                      help="Apparatus capital for the OVERBUILD floor (default: 1.9e9). "
                           "Below its break-even ε the collective costs members more "
                           "hours than autarky and should dissolve")
    band.add_argument("--land-m2", type=float, default=1.86e10, dest="land_m2",
                      help="Claimed land area for the thermal ceiling (default: 1.86e10)")
    band.add_argument("--phi-other", type=float, default=2.5e9, dest="phi_other",
                      help="Non-automation dissipation, W (default: 2.5e9)")
    band.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    band.set_defaults(func=_band)

    axes = sub2.add_parser(
        "axes", help="Both contestability axes side by side, and their disagreement")
    axes.add_argument("--population", type=float, default=1_000_000.0)
    axes.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH,
                      dest="trust_balance")
    axes.add_argument("--regime", choices=["increasing_returns", "replicable"],
                      default="increasing_returns")
    axes.add_argument("--phi-policy", choices=["dilution", "target", "escalated"],
                      default="dilution", dest="phi_policy")
    axes.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    axes.set_defaults(func=_axes)


def _band(args: argparse.Namespace) -> None:
    if args.standard == "survival":
        eoh = survival_inventory(population=args.population, epsilon=args.epsilon)
    else:
        from hours_eoh.core.eoh_generation import total_eoh
        eoh = total_eoh(epsilon=args.epsilon, population=args.population,
                        personal_standard=args.standard)
    floors = [
        survival_floor(eoh, args.available_labor),
        overbuild_floor(args.capital_stock, args.population),
    ]

    if args.bare_chi:
        contest = contestability_ceiling_bare_chi(
            args.population, args.trust_balance, regime=args.regime)
    else:
        contest = contestability_ceiling(
            args.population, regime=args.regime, phi_policy=args.phi_policy)

    therm = thermal_ceiling(args.land_m2, args.phi_other, epsilon=args.epsilon)
    rep = corridor(floors, [contest, therm])

    if args.fmt == "json":
        print(json.dumps(rep, indent=2, default=str))
        return

    verdict = green("OPEN") if rep["feasible"] else red("CLOSED")
    print(bold(f"Stability corridor — inventory at ε = {fmt_eps(args.epsilon)}  [{verdict}]"))
    if args.bare_chi:
        print(red("  ● using the SUPERSEDED bare-χ contestability axis "
                  "(--bare-chi); the adopted §8.9 axis is the default"))
    print()

    print(bold("Band"))
    print(f"  ε_suff (binding floor): {fmt_eps(rep['epsilon_suff'])}"
          + (f"  ← {rep['binding_floor']}" if rep["binding_floor"] else "  (nothing binds)"))
    print(f"  ε_max  (tightest ceiling): {fmt_eps(rep['epsilon_max'])}"
          + ("" if rep["binding_ceiling"] else "  (aspirational — nothing binds)"))
    print(f"  width: {rep['width']:+.3f}")
    print(f"  success (feasible AND sufficiency reachable): "
          f"{green('yes') if rep['success'] else red('no')}")
    print()

    print(bold("Floors"))
    frows = [[f["name"], "yes" if f["binding"] else "no",
              fmt_eps(f["epsilon_floor"]), f["status"]] for f in rep["floors"]]
    print(table(["bound", "binds", "ε_floor", "status"], frows))
    print()

    print(bold("Ceilings"))
    rows = [[c["name"],
             "yes" if c["binding"] else "no",
             fmt_eps(c["epsilon_ceiling"]) if c["epsilon_ceiling"] is not None else "—",
             c["status"]]
            for c in rep["ceilings"]]
    print(table(["invariant", "binds", "ε_ceiling", "status"], rows))
    print()
    print(dim(f"  {rep['note']}"))


def _axes(args: argparse.Namespace) -> None:
    cmp = contestability_axes(
        args.population, args.trust_balance,
        regime=args.regime, phi_policy=args.phi_policy,
    )

    if args.fmt == "json":
        print(json.dumps(cmp, indent=2, default=str))
        return

    print(bold("Contestability axes"))
    print()
    rows = []
    for label, c in (("adopted (§8.9 three-channel)", cmp["adopted"]),
                     ("SUPERSEDED (bare χ = P/K_entry)", cmp["bare_chi"])):
        rows.append([
            label,
            "yes" if c["binding"] else "no",
            fmt_eps(c["epsilon_ceiling"]) if c["epsilon_ceiling"] is not None else "—",
            c["status"],
        ])
    print(table(["axis", "binds", "ε_ceiling", "status"], rows))
    print()
    if cmp["agree"]:
        print(green("  ● " + cmp["note"]))
    else:
        print(red("  ● " + cmp["note"]))
