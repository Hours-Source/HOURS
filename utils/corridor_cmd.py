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

from hours_eoh.core.eoh_generation import resolve_capital_stock
from hours_eoh.data import (
    A_LAND_CLAIMED_M2,
    AGE_GROUP_RANGES,
    JURISDICTION_FRAMES,
    M2_PER_HECTARE,
    REFERENCE_FRAME_POPULATION,
    THERMAL_ANTHROPOGENIC_DISSIPATION_W,
    THERMAL_DT_LO,
    THERMAL_U_FLOOR,
    WORLD_POPULATION,
)

import argparse
import json

from hours_eoh.research.corridor import (
    contestability_axes,
    contestability_ceiling,
    contestability_ceiling_bare_chi,
    DEFAULT_SURVIVAL_DOMAINS,
    corridor,
    measured_thermal_ceiling,
    overbuild_capital_limit,
    overbuild_floor,
    survival_floor,
    survival_floor_epsilon,
    survival_inventory,
    thermal_ceiling,
)

from utils.formatters import bold, dim, green, red, table, fmt_eps, fmt_float
from utils.frame_inputs import (
    add_frame_arguments, labelled_inputs, print_inputs, resolve_epsilon, resolve_inputs,
)



def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser(
        "corridor",
        help="[EXPERIMENTAL] Stability corridor [ε_suff, ε_max] and its ceilings",
    )
    sub2 = p.add_subparsers(dest="corridor_cmd", required=True)

    band = sub2.add_parser("band", help="The corridor and its binding ceiling")
    band.add_argument("--epsilon", type=float, default=None, metavar="ε",
                      help="ε at which the EOH inventory is taken. Default: the "
                           "--frame's MEASURED reading (both instruments, as a "
                           "point ± margin), else the 0.40 reference, labelled")
    band.add_argument("--population", type=float, default=None,
                      help="Population (default: the --frame's, else "
                           "REFERENCE_FRAME_POPULATION)")
    # REAL-DATA INPUTS (2026-10-03): --frame, --frame-file, --ages,
    # --adult-capacity and --bea-usd-per-teh, shared with `scenario run`
    # (utils/frame_inputs.py) so one frame resolves one way everywhere.
    add_frame_arguments(band)
    band.add_argument("--delta-t-lo", type=float, default=THERMAL_DT_LO,
                      dest="delta_t_lo", metavar="K",
                      help="Habitability threshold for BOTH thermal ceilings — "
                           "the P0 bound and the Path C utilization (default: "
                           "THERMAL_DT_LO, the adopted value). Its determinacy "
                           "zone is printed beside U")
    band.add_argument("--utilization", type=float, default=None, metavar="U",
                      help="Measured thermal utilization (Path C). Adds the "
                           "MEASURED thermal ceiling beside the P0 bound "
                           "(default: the --frame's Path C reading, if any)")
    band.add_argument("--available-labor", type=float, default=None,
                      dest="available_labor", metavar="EOH",
                      help="Human labor capacity, EOH-hours/yr. Default: DERIVED "
                           "as labor_supply_per_capita() x population — one "
                           "account of L, shared with the feasibility path. The "
                           "retired literal 1e9 implied a 42.8%% adult share, "
                           "which no population has.")
    band.add_argument("--standard", choices=["survival", "collapsed", "sufficiency"],
                      default="survival",
                      help="Personal-EOH standard for the LOWER bound (default: "
                           "survival — the floor is a survival floor). 'sufficiency' "
                           "reports the automation needed for a decent life, which is "
                           "a different and larger number")
    # DEFAULT None since 2026-09-17 (Trust-frame decision): an unsupplied
    # balance resolves against --population, so the inheritance travels with
    # the frame. Supplying the flag states YOUR balance and it is used as given.
    band.add_argument("--trust-balance", type=float, default=None,
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
    # FRAME (2026-10-03): these three defaulted to fixed totals for a 1M
    # collective (1.9e9 TEH, 1.86e10 m², 2.5e9 W) beside a settable
    # --population, so `--population 1e4` bound the overbuild floor at ε 0.754
    # on 100x the capital intensity (mode 6). Unsupplied, each now resolves
    # against the population: capital along the canonical arc, land and
    # residual dissipation as the per-capita share of the global quantities.
    band.add_argument("--capital-stock", type=float, default=None,
                      dest="capital_stock", metavar="TEH",
                      help="Apparatus capital for the OVERBUILD floor (default: the "
                           "canonical arc's stock at --epsilon and --population). "
                           "Below its break-even ε the collective costs members more "
                           "hours than autarky and should dissolve")
    band.add_argument("--land-m2", type=float, default=None, dest="land_m2",
                      help="Claimed land area for the thermal ceiling (default: "
                           "--population's share of A_LAND_CLAIMED_M2)")
    band.add_argument("--phi-other", type=float, default=None, dest="phi_other",
                      help="Non-automation dissipation, W (default: --population's "
                           "share of THERMAL_ANTHROPOGENIC_DISSIPATION_W)")
    band.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    band.set_defaults(func=_band)

    axes = sub2.add_parser(
        "axes", help="Both contestability axes side by side, and their disagreement")
    axes.add_argument("--population", type=float, default=REFERENCE_FRAME_POPULATION)
    axes.add_argument("--trust-balance", type=float, default=None,
                      dest="trust_balance")
    axes.add_argument("--regime", choices=["increasing_returns", "replicable"],
                      default="increasing_returns")
    axes.add_argument("--phi-policy", choices=["dilution", "target", "escalated"],
                      default="dilution", dest="phi_policy")
    axes.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    axes.set_defaults(func=_axes)


def _verdict(rep: dict) -> tuple:
    return (rep["feasible"], rep["binding_floor"], rep["binding_ceiling"],
            round(rep["epsilon_suff"], 3))


def _band(args: argparse.Namespace) -> None:
    # The band computes no guarantee, so the retirement register reaches
    # nothing here: refused rather than accepted and ignored (mode 5).
    unread = [f for f, a in (("--retirement-age", "retirement_age"),
                             ("--years-in-collective", "years_in_collective"))
              if getattr(args, a, None) is not None]
    if unread:
        raise SystemExit(f"corridor band does not read the retirement register "
                         f"({', '.join(unread)}); run the shocks with it")
    eps = resolve_epsilon(args)
    args = argparse.Namespace(**{**vars(args), "epsilon": eps["value"]})
    rep = _compute(args)
    if eps["high"] > eps["low"]:
        ends = {e: _compute(argparse.Namespace(**{**vars(args), "epsilon": e}))
                for e in (eps["low"], eps["high"])}
        eps["verdict_holds_across_range"] = all(
            _verdict(r) == _verdict(rep) for r in ends.values())
    rep["epsilon_reading"] = eps
    # THE ECHO (2026-10-03): a ceiling that binds AT the current ε (thermal
    # contact) reports the --epsilon it was given, not a limit it located.
    # Set before output so json carries it too.
    rep["epsilon_max_is_current"] = (
        rep["binding_ceiling"] is not None and rep["epsilon_max"] == args.epsilon
        and any(c["binding"] and c["epsilon_ceiling"] == args.epsilon for c in rep["ceilings"]))
    _show(args, rep)


def _compute(args: argparse.Namespace) -> dict:
    inp, labels = resolve_inputs(args, args.epsilon)
    pop, ages = inp["population"], inp["age_fractions"]
    # THE FRAME'S ECOLOGY (2026-10-04): a frame that declares its people carry
    # its ecological work brings its restoration and the recurring flow into
    # the obligation the band reads; off, both are the shipped defaults.
    eco = dict(restoration_obligation=inp["restoration_eoh"],
               ecological_health_response=inp["ecological_response"],
               ecological_standing_response=inp["ecological_response"],
               ecosystem_health=inp["ecosystem_health"])
    if args.standard == "survival":
        eoh = survival_inventory(population=pop, epsilon=args.epsilon,
                                 age_distribution=ages)
    else:
        from hours_eoh.core.eoh_generation import total_eoh
        eoh = total_eoh(epsilon=args.epsilon, population=pop,
                        personal_standard=args.standard, age_distribution=ages, **eco)
    # ONE ACCOUNT OF L. `scenarios/feasibility.labor_supply_per_capita` is the
    # framed one — c·a, adult capacity times the capacity-weighted adult share —
    # and `arc_stability` already used it. This CLI carried a bare 1e9 instead:
    # 71% of the framed value, implying an adult share of 42.8% that no country
    # has. Two accounts of one quantity (corpus F-008). Bound here rather than in
    # `research/corridor.py`, which must not import `scenarios/` — utils may.
    available_labor = (inp["labor_supply_per_capita"] * pop
                       if args.available_labor is None else args.available_labor)
    floors = [
        survival_floor(eoh, available_labor),
        # The frame's age and health ALWAYS — stated, or the labelled default
        # (CAPITAL_AGE_RATIO_DEFAULT; the US frame's is measured off BEA).
        overbuild_floor(inp["capital_teh"], pop, capital_age_ratio=inp["capital_age_ratio"],
                        ecosystem_health=inp["ecosystem_health"]),
    ]

    if args.bare_chi:
        contest = contestability_ceiling_bare_chi(
            pop, args.trust_balance, regime=args.regime)
    else:
        contest = contestability_ceiling(
            pop, regime=args.regime, phi_policy=args.phi_policy)

    # The bound divides by the collective's EOH, so the inventory travels with
    # the frame too; left to itself it reads total_eoh at the 1M default.
    from hours_eoh.core.eoh_generation import total_eoh as _total_eoh
    therm = thermal_ceiling(inp["land_m2"], inp["phi_other_w"], epsilon=args.epsilon,
                            eoh_by_domain=_total_eoh(epsilon=args.epsilon, population=pop,
                                                     age_distribution=ages, **eco),
                            delta_t_lo=args.delta_t_lo)
    ceilings = [contest, therm]
    if inp["utilization"] is not None:
        ceilings.append(measured_thermal_ceiling(inp["utilization"],
                                                 epsilon_current=args.epsilon,
                                                 delta_t_lo=args.delta_t_lo))
    rep = corridor(floors, ceilings)
    # HEADROOM (2026-10-03): "no / —" said a bound does not bind and nothing
    # about how far it is from binding — the gap the demographic margin closed
    # for one bound, closed here for the rest that have a distance.
    eoh_surv = sum(eoh.get(d, 0.0) for d in DEFAULT_SURVIVAL_DOMAINS)
    ob_state = {k: inp[k] for k in ("capital_age_ratio", "ecosystem_health")}
    k_limit = (overbuild_capital_limit(inp["capital_teh"], pop, **ob_state)
               if inp["capital_teh"] > 0 else None)
    u = inp["utilization"]
    headroom: dict = {
        "survival": {"labour_cover": available_labor / eoh_surv if eoh_surv > 0 else None},
        "overbuild": {"capital_limit_teh": k_limit,
                      "capital_limit_per_capita": k_limit / pop if k_limit else None,
                      "multiple": k_limit / inp["capital_teh"] if k_limit else None},
    }
    if u is not None:
        # Contact is U = 1 by definition (ψ = ψ*); the regime itself comes from
        # the ceiling function rather than being re-tested here.
        tm = next(c for c in ceilings if c["name"] == "thermal_measured")
        regime = ("contact" if tm["binding"]
                  else "unbudgeted" if tm["status"].startswith("UNBUDGETED")
                  else "exposure" if tm["status"].startswith("standing exposure")
                  else "below")
        headroom["thermal_measured"] = {
            "utilization": u, "regime": regime, "exposure_at": THERMAL_U_FLOOR,
            "to_exposure": THERMAL_U_FLOOR / u if u > 0 else None,
            "to_contact": 1.0 / u if u > 0 else None}
    rep["headroom"] = headroom  # type: ignore[typeddict-unknown-key]
    rep["inputs"] = dict(inp)  # type: ignore[typeddict-unknown-key]
    rep["input_labels"] = labels  # type: ignore[typeddict-unknown-key]
    return rep  # type: ignore[return-value]


def _show(args: argparse.Namespace, rep: dict) -> None:
    from hours_eoh.scenarios.feasibility import demographic_margin
    inp, headroom = rep["inputs"], rep["headroom"]
    pop, ages = inp["population"], inp["age_fractions"]
    if args.fmt == "json":
        print(json.dumps(rep, indent=2, default=str))
        return

    verdict = green("OPEN") if rep["feasible"] else red("CLOSED")
    print(bold(f"Stability corridor — inventory at ε = {fmt_eps(args.epsilon)}  [{verdict}]"))
    if args.bare_chi:
        print(red("  ● using the SUPERSEDED bare-χ contestability axis "
                  "(--bare-chi); the adopted §8.9 axis is the default"))
    print()

    er = rep["epsilon_reading"]
    holds = er.get("verdict_holds_across_range")
    print_inputs(labelled_inputs(inp, rep["input_labels"], er), er,
                 ends=None if holds is None else (
                     green("same verdict") if holds else red("verdict DIFFERS — read the band at each end")),
                 frame=inp["frame"])
    if inp["utilization"] is not None:
        print(f"  {'thermal zone':24s} {inp['thermal_zone']} at ΔT_lo {inp['delta_t_lo']:.2f} K")
    print()

    print(bold("Band"))
    print(f"  ε_suff (binding floor): {fmt_eps(rep['epsilon_suff'])}"
          + (f"  ← {rep['binding_floor']}" if rep["binding_floor"] else "  (nothing binds)"))
    echo = rep["epsilon_max_is_current"]
    print(f"  ε_max  (tightest ceiling): {fmt_eps(rep['epsilon_max'])}"
          + ("" if rep["binding_ceiling"] else "  (aspirational — nothing binds)")
          + (f"  = current ε — no budgeted headroom ({rep['binding_ceiling']}); "
             "set by --epsilon, not located" if echo else ""))
    print(f"  width: {rep['width']:+.3f}" + ("  (to the current ε)" if echo else ""))
    print(f"  success (feasible AND sufficiency reachable): "
          f"{green('yes') if rep['success'] else red('no')}")
    print()

    # A FLOOR OF 0.000 SAYS "NOTHING BINDS" AND HIDES HOW CLOSE THE STEP IS.
    # ε_suff is a STEP in one ratio, not a curve: personal obligation per capita
    # is near-flat in ε, so the floor is 0 while capacity covers the obligation
    # and rises only once it does not. The distance to that step is the quantity
    # a reader needs; `demographic_margin` returns it (the 2.13 pp once quoted
    # here predated the 2026-09-04 capacity alignment, mode 7).
    marg = demographic_margin(epsilon=args.epsilon, population=pop, age_fractions=ages,
                              adult_capacity_h_yr=inp["adult_capacity_h_yr"])
    print(bold("Demographic margin"))
    print(f"  adult share (capacity-weighted): {marg['adult_share']:.4f}")
    print(f"  critical share  P/c            : {marg['critical_adult_share']:.4f}")
    covers = marg["covers"] >= 1.0
    print(f"  margin: {marg['margin_pp']:+.2f} pp of adult share  "
          + (green("capacity covers the obligation")
             if covers else red("capacity does NOT cover the obligation")))
    print(f"  L = {marg['supply_per_capita']:,.1f} h/person·yr"
          f"   vs personal obligation {marg['personal_demand_per_capita']:,.1f}"
          f"   (L {'derived' if args.available_labor is None else 'OVERRIDDEN'})")
    print()

    print(bold("Floors"))
    frows = [[f["name"], "yes" if f["binding"] else "no",
              fmt_eps(f["epsilon_floor"]), _headroom(f["name"], headroom), f["status"]]
             for f in rep["floors"]]
    print(table(["bound", "binds", "ε_floor", "headroom", "status"], frows))
    print()

    print(bold("Ceilings"))
    rows = [[c["name"],
             "yes" if c["binding"] else "no",
             fmt_eps(c["epsilon_ceiling"]) if c["epsilon_ceiling"] is not None else "—",
             _headroom(c["name"], headroom),
             c["status"]]
            for c in rep["ceilings"]]
    print(table(["invariant", "binds", "ε_ceiling", "headroom", "status"], rows))
    print()
    print(dim(f"  {rep['note']}"))


def _headroom(name: str, h: dict) -> str:
    """One line of distance-to-binding for a bound, or "—" where none is defined."""
    if name == "survival" and h["survival"]["labour_cover"] is not None:
        return f"labour {h['survival']['labour_cover']:.2f}× survival need"
    if name == "overbuild":
        o = h["overbuild"]
        return (f"pays to {o['capital_limit_per_capita']:,.0f} TEH/person ({o['multiple']:.2f}×)"
                if o["multiple"] else "—")
    if name == "thermal_measured" and "thermal_measured" in h:
        t = h["thermal_measured"]
        # The REGIME is read from measured_thermal_ceiling, which owns the
        # exposure and contact lines; only the distances are computed here.
        if t["regime"] == "unbudgeted":
            return "no budget"
        if t["regime"] == "contact" or t["to_contact"] is None:
            return "—"
        contact = f"contact {t['to_contact']:.2f}×"
        return f"exposure {t['to_exposure']:.2f}×, {contact}" if t["regime"] == "below" else contact
    return "—"


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
