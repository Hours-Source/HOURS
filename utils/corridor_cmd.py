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

#: The reference ε the rest of the CLI defaults to, used only when no measured
#: reading exists for the frame — and then printed as a default.
_EPSILON_REFERENCE = 0.40

#: `--frame` names → the declared jurisdiction (data.JURISDICTION_FRAMES) and
#: the Path C collective whose measured utilization belongs to it.
_FRAMES: dict[str, dict[str, str]] = {
    "us": {"jurisdiction": "us_mainland", "path_c": "United States"},
}


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
    # REAL-DATA INPUTS (2026-10-03). The band could only read the shipped
    # demography, a canonical capital stock and the P0 thermal bound; the repo
    # already held the US readings for all three. --frame us fills them.
    band.add_argument("--frame", choices=sorted(_FRAMES), default=None,
                      help="A declared jurisdiction: sets population, land and "
                           "ages from it, and the Path C utilization if it has "
                           "one. 'us' = contiguous-48 US, Census ages, Path C "
                           "'United States'. Explicit flags override it")
    band.add_argument("--ages", choices=["shipped", "census"], default=None,
                      help="Age mix for the obligation, the labour supply and the "
                           "margin: 'shipped' = AGE_GROUP_FRACTIONS, 'census' = "
                           "US Census single-year ages (latest year) grouped to "
                           "AGE_GROUP_RANGES (default: census with --frame us, "
                           "else shipped)")
    band.add_argument("--bea-usd-per-teh", type=float, default=None,
                      dest="bea_usd_per_teh", metavar="RATE",
                      help="Read capital from the BEA US inventory "
                           "(capital_retrodiction.epsilon_from_inventory) at this "
                           "currency-per-TEH rate. US frame only — the inventory "
                           "is the whole US. No default: the rate is a judgement "
                           "(conversion_band() bounds it)")
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


def _resolve_inputs(args: argparse.Namespace) -> dict:
    """Population, land, ages, capital and utilization, with where each came from."""
    frame = _FRAMES[args.frame] if args.frame else None
    jur = JURISDICTION_FRAMES[frame["jurisdiction"]] if frame else None
    population = (args.population if args.population is not None
                  else jur["population"] if jur else REFERENCE_FRAME_POPULATION)

    ages_choice = args.ages or ("census" if frame else "shipped")
    if ages_choice == "census":
        from hours_eoh.reference.care_demand import population_shares
        ages: dict[str, float] | None = population_shares(AGE_GROUP_RANGES)
    else:
        ages = None

    if args.bea_usd_per_teh is not None:
        if args.frame != "us" or population != jur["population"]:  # type: ignore[index]
            raise SystemExit("--bea-usd-per-teh reads the whole-US inventory; it "
                             "needs --frame us at the US population")
        if args.capital_stock is not None:
            raise SystemExit("--bea-usd-per-teh and --capital-stock both set capital")
        from hours_eoh.scenarios.capital_retrodiction import epsilon_from_inventory
        capital = float(epsilon_from_inventory(args.bea_usd_per_teh)["capital_teh"])
        capital_src = f"BEA US inventory at {args.bea_usd_per_teh} $/TEH"
    else:
        capital = resolve_capital_stock(args.capital_stock, args.epsilon,
                                        population=population)
        capital_src = "supplied" if args.capital_stock is not None else "canonical arc"

    share = population / WORLD_POPULATION
    if args.land_m2 is not None:
        land_m2, land_src = args.land_m2, "supplied"
    elif jur:
        land_m2, land_src = jur["land_hectares"] * M2_PER_HECTARE, frame["jurisdiction"]  # type: ignore[index]
    else:
        land_m2, land_src = A_LAND_CLAIMED_M2 * share, "population share of A_LAND_CLAIMED_M2"
    phi_other = (THERMAL_ANTHROPOGENIC_DISSIPATION_W * share
                 if args.phi_other is None else args.phi_other)

    utilization, u_src = args.utilization, "supplied"
    if utilization is None and frame and frame.get("path_c"):
        from hours_eoh.research.thermal_path_c import all_collectives_utilization
        rows = {c["name"]: c for c in all_collectives_utilization(delta_t_lo=args.delta_t_lo)}
        utilization, u_src = float(rows[frame["path_c"]]["utilization"]), f"Path C '{frame['path_c']}'"
    from hours_eoh.research.thermal_path_c import determinacy_zone
    return {
        "delta_t_lo": args.delta_t_lo,
        "thermal_zone": determinacy_zone(args.delta_t_lo)["zone"],
        "frame": args.frame, "population": population,
        "ages": ages_choice, "age_fractions": ages,
        "capital_teh": capital, "capital_source": capital_src,
        "land_m2": land_m2, "land_source": land_src, "phi_other_w": phi_other,
        "utilization": utilization, "utilization_source": u_src if utilization is not None else None,
    }


def _resolve_epsilon(args: argparse.Namespace) -> dict:
    """
    The ε the inventory is taken at, and where it came from (2026-10-03).

    Supplied → used as given. Unsupplied on a frame with measured readings →
    the repo's two instruments (`labour_epsilon.instrument_comparison`: time
    use and the BEA capital route, at --bea-usd-per-teh if given, else across
    `conversion_band()`), reported as the midpoint of their joint span ± half
    its width, with their own agreement verdict. Otherwise the 0.40 reference,
    LABELLED a default — `--frame us` used to run at it silently.
    """
    if args.epsilon is not None:
        return {"value": args.epsilon, "margin": 0.0, "low": args.epsilon,
                "high": args.epsilon, "source": "supplied"}
    if args.frame == "us":
        from hours_eoh.scenarios.labour_epsilon import instrument_comparison
        rates = (args.bea_usd_per_teh,) if args.bea_usd_per_teh is not None else None
        c = instrument_comparison(capital_rates=rates)
        lo = min(c["labour"]["low"], c["capital"]["low"])
        hi = max(c["labour"]["high"], c["capital"]["high"])
        # DIVERGENT: neither instrument's interval meets the other's, so the
        # span is their DISAGREEMENT, not a measurement error around a value,
        # and the midpoint is a reading neither instrument gives (2026-10-03).
        divergent = c["verdict"] == "DIVERGENT"
        return {"value": 0.5 * (lo + hi), "margin": 0.5 * (hi - lo), "low": lo, "high": hi,
                "margin_kind": "disagreement" if divergent else "span",
                "source": (f"US instruments — labour {_span(c['labour'])}, "
                           f"capital {_span(c['capital'])} ({c['verdict']}); "
                           + ("instruments disagree — span shown, midpoint is not a reading"
                              if divergent else "midpoint ± half-span")),
                "instruments": {"labour": [c["labour"]["low"], c["labour"]["high"]],
                                "capital": [c["capital"]["low"], c["capital"]["high"]],
                                "verdict": c["verdict"]}}
    return {"value": _EPSILON_REFERENCE, "margin": None, "low": _EPSILON_REFERENCE,
            "high": _EPSILON_REFERENCE,
            "source": "default — no measured reading for this frame"}


def _span(r: dict) -> str:
    return (f"{r['low']:.3f}" if r["low"] == r["high"]
            else f"{r['low']:.3f}–{r['high']:.3f}")


def _verdict(rep: dict) -> tuple:
    return (rep["feasible"], rep["binding_floor"], rep["binding_ceiling"],
            round(rep["epsilon_suff"], 3))


def _band(args: argparse.Namespace) -> None:
    eps = _resolve_epsilon(args)
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
    inp = _resolve_inputs(args)
    pop, ages = inp["population"], inp["age_fractions"]
    if args.standard == "survival":
        eoh = survival_inventory(population=pop, epsilon=args.epsilon,
                                 age_distribution=ages)
    else:
        from hours_eoh.core.eoh_generation import total_eoh
        eoh = total_eoh(epsilon=args.epsilon, population=pop,
                        personal_standard=args.standard, age_distribution=ages)
    # ONE ACCOUNT OF L. `scenarios/feasibility.labor_supply_per_capita` is the
    # framed one — c·a, adult capacity times the capacity-weighted adult share —
    # and `arc_stability` already used it. This CLI carried a bare 1e9 instead:
    # 71% of the framed value, implying an adult share of 42.8% that no country
    # has. Two accounts of one quantity (corpus F-008). Bound here rather than in
    # `research/corridor.py`, which must not import `scenarios/` — utils may.
    from hours_eoh.scenarios.feasibility import (
        capacity_weighted_adult_share, demographic_margin, labor_supply_per_capita)
    available_labor = (
        labor_supply_per_capita(adult_share=capacity_weighted_adult_share(ages)) * pop
        if args.available_labor is None else args.available_labor)
    floors = [
        survival_floor(eoh, available_labor),
        overbuild_floor(inp["capital_teh"], pop),
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
                                                     age_distribution=ages),
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
    k_limit = overbuild_capital_limit(inp["capital_teh"], pop) if inp["capital_teh"] > 0 else None
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
    rep["inputs"] = {k: v for k, v in inp.items() if k != "age_fractions"}  # type: ignore[typeddict-unknown-key]
    rep["inputs"]["age_fractions"] = ages  # type: ignore[typeddict-item]
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

    print(bold("Inputs"))
    er = rep["epsilon_reading"]
    if er["margin"]:
        holds = er.get("verdict_holds_across_range")
        if er.get("margin_kind") == "disagreement":
            print(f"  ε: span [{er['low']:.3f}, {er['high']:.3f}] — inventory taken at "
                  f"{er['value']:.3f}, NOT a reading  ({er['source']})")
        else:
            print(f"  ε: {er['value']:.3f} ± {er['margin']:.3f}  [{er['low']:.3f}, {er['high']:.3f}]"
                  f"  ({er['source']})")
        print(f"     verdict at both ends of the range: "
              + (green("same") if holds else red("DIFFERS — read the band at each end")))
    else:
        print(f"  ε: {er['value']:.3f}  ({er['source']})")
    print(f"  frame: {inp['frame'] or '—'}   population: {pop:,.0f}   ages: {inp['ages']}")
    print(f"  capital: {fmt_float(inp['capital_teh'])} TEH "
          f"({inp['capital_teh'] / pop:,.0f}/person; {inp['capital_source']})")
    print(f"  land: {inp['land_m2']:.3e} m² ({inp['land_source']})")
    if inp["utilization"] is not None:
        print(f"  thermal utilization U: {inp['utilization']:.3f} ({inp['utilization_source']}) "
              f"at ΔT_lo {inp['delta_t_lo']:.2f} K — zone: {inp['thermal_zone']}")
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
    marg = demographic_margin(epsilon=args.epsilon, population=pop, age_fractions=ages)
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
