"""
arc — epsilon arc sweep command.

Sweeps ε from 0 to 0.99 and prints EOH by domain, registration share,
TEH created, basket price, and fiscal solvency at each point.
"""

from __future__ import annotations
import argparse
import csv
import json
import sys

from hours_eoh.core.trajectory import canonical_physical_state
from hours_eoh.core.eoh_generation import total_eoh
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.registration import register_shares
from hours_eoh.core.prices import basket_price, floor_price, floor_purchasing_power
from hours_eoh.data import MEANINGFUL_ACTIVITY_TEH_BASE, REFERENCE_FRAME_POPULATION, EPSILON_ARC_MAX
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.data import CAPITAL_STOCK_DEFAULT

from utils.formatters import table, fmt_float, fmt_pct, fmt_eps, bold
from hours_eoh.core.fiscal import resolve_trust_balance


def knowledge_ref_figures() -> tuple[float, float, float, float]:
    """The frozen base's ε_ref (the fixed point) and the ε_ref band's spread, live."""
    from hours_eoh.scenarios.knowledge_base import (
        DEFAULT_EPSILON_REF_BAND, epsilon_ref_fixed_point, knowledge_base_band)
    from hours_eoh.scenarios.personal_floor import paid_labour_anchor
    star = epsilon_ref_fixed_point(paid_labour_anchor())["epsilon_fixed_point"]
    spread = knowledge_base_band()["epsilon_ref_spread"]
    return star, spread, DEFAULT_EPSILON_REF_BAND[0], DEFAULT_EPSILON_REF_BAND[-1]


def knowledge_ref_help() -> tuple[str, str]:
    """The same figures as help text. A missing data file degrades the help, not the parser."""
    try:
        star, spread, lo, hi = knowledge_ref_figures()
    except (OSError, KeyError, ValueError):
        return ("ε_ref (see epsilon_ref_fixed_point)",
                "the spread knowledge_base_band() reports")
    return f"ε_ref = {star:.3f}", f"{spread:.2f}x across [{lo}, {hi}]"


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    from hours_eoh.scenarios.thermal_load import REFERENCE_THERMAL_FLOW_EOH
    star_text, spread_text = knowledge_ref_help()
    p = sub.add_parser("arc", help="Sweep the epsilon arc and display system metrics")
    p.add_argument("--points", type=int, default=20, metavar="N",
                   help="Number of ε points (default: 20)")
    p.add_argument("--domain", choices=["personal", "infra", "eco", "knowledge", "all"],
                   default="all", help="Domain to highlight (default: all)")
    p.add_argument("--format", choices=["table", "csv", "json"], default="table",
                   dest="fmt", help="Output format (default: table)")
    p.add_argument("--population", type=float, default=REFERENCE_FRAME_POPULATION)
    # DEFAULT None since 2026-09-17 (Trust-frame decision): an unsupplied
    # balance resolves against --population, so the inheritance travels with
    # the frame. Supplying the flag states YOUR balance and it is used as given.
    p.add_argument("--trust-balance", type=float, default=None)
    p.add_argument("--domain-shares", action="store_true",
                   help="Show each domain as a SHARE of total EOH instead of "
                        "absolute hours (the denominator check — see "
                        "docs/parameter_provenance.md 'Domain balance')")
    p.add_argument("--thermal-obligation", type=float, default=0.0, metavar="EOH",
                   help="Annual planetary radiative-capacity obligation (h/yr) to "
                        "carry as the fourth ecological term. Default 0.0 (off). "
                        f"~{REFERENCE_THERMAL_FLOW_EOH:.3g} for 1M people at ε=0.40 "
                        "per research/thermal_solvency")
    p.add_argument("--knowledge-epsilon-ref", type=float, default=None,
                   dest="knowledge_epsilon_ref", metavar="EPS",
                   help="Re-derive KNOWLEDGE_EOH_BASE at this reference "
                        "automation level instead of the frozen base's fixed "
                        f"point {star_text}, and run the arc with it. THE "
                        f"DOMINANT UNCERTAINTY in the knowledge domain: {spread_text}. "
                        "See the knowledge-base closure note §4")
    p.set_defaults(func=run)


def _sweep(n_points: int, population: float, trust_balance: float | None,
           thermal_obligation: float = 0.0,
           knowledge_base: float | None = None) -> list[dict]:
    trust_balance = resolve_trust_balance(trust_balance, population)
    results = []
    for i in range(n_points):
        eps = i / (n_points - 1) * EPSILON_ARC_MAX if n_points > 1 else 0.40
        state = canonical_physical_state(eps, population=population)
        eoh = total_eoh(
            capital_stock=state["capital_stock_teh"],
            capital_age_ratio=state["capital_age_ratio"],
            ecosystem_health=state["ecosystem_health"],
            monitoring_capability=state["monitoring_capability"],
            age_distribution=state["age_distribution"],
            # BUG FIX (Block K-IV, 2026-08-08): this was
            #     knowledge_base=state["knowledge_base_size"]
            # which put the corpus SIZE (kbs, 1.0 → 9.91) into the base-RATE
            # slot while `knowledge_complexity` — the actual kbs argument —
            # stayed at its 1.0 default. The arc's knowledge column was
            # therefore under-reported by a factor of KNOWLEDGE_EOH_BASE for
            # the whole life of the command, and the column never responded to
            # the constant at all. Two same-prefixed parameter names, one
            # keyword apart.
            knowledge_complexity=state["knowledge_base_size"],
            knowledge_complexity_per_unit=state["knowledge_complexity_per_unit"],
            **({"knowledge_base": knowledge_base}
               if knowledge_base is not None else {}),
            population=population,
            thermal_obligation=thermal_obligation,
        )
        pipeline = eoh_to_teh_pipeline(eps, population=population,
                                       thermal_obligation=thermal_obligation)
        reg = register_shares(eps)["labour"]
        # The floor is read at the OBSERVED ε (author decision, 2026-09-30).
        eps_floor = float(pipeline["epsilon_observable"])
        price = floor_price(eps_floor)
        floor_pp_result = floor_purchasing_power(MEANINGFUL_ACTIVITY_TEH_BASE, eps_floor)
        floor_pp = float(floor_pp_result.get("pp_index", 0.0))

        # THE MINT IS THE LABOUR INCOME (2026-09-30). This was
        # `registered_eoh × 2200.0` from the initial commit — a bare literal,
        # ~1,100× the mint (`registered_eoh × mean_multiplier`, m ≈ 2), so the
        # Trust's surplus read ~100× high and the `solvent` column could not
        # show insolvency for any Trust: with `--trust-balance 0` ε=0.99 is
        # insolvent on the real mint and was reported solvent. Every other
        # path passes `teh_created` (`build_collective`, `run_collective_period`).
        labor_income = pipeline.get("teh_created", 0.0)
        snap = fiscal_snapshot(
            epsilon=eps,
            population=population,
            trust_balance=trust_balance,
            labor_income=labor_income,
            capital_stock_teh=state["capital_stock_teh"],
            capital_age_ratio=state["capital_age_ratio"],
            ecosystem_health=state["ecosystem_health"],
            thermal_obligation=thermal_obligation,
        )

        results.append({
            "epsilon": eps,
            "personal_eoh": eoh.get("personal", 0.0),
            "infra_eoh": eoh.get("infrastructure", 0.0),
            "eco_eoh": eoh.get("ecological", 0.0),
            "knowledge_eoh": eoh.get("knowledge", 0.0),
            "total_eoh": eoh.get("total", 0.0),
            "registration": reg,
            "teh_created": pipeline.get("teh_created", 0.0),
            "floor_price": price,
            "floor_pp": floor_pp,
            "solvent": snap.get("solvent", False),
        })
    return results


def _domain_share_rows(rows_data: list[dict], population: float) -> None:
    """Each domain as a share of total EOH, plus per-capita hours.

    The denominator check: ε = machine_EOH / total_EOH, so whichever domain dominates
    total EOH effectively sets ε. Before Block K-IV (2026-08-08) personal ran 87–96%
    across the whole arc. Since K-IV it falls across the arc (the footer prints the
    shares at both ends), so the defect is PARTLY closed. Personal still dominates the
    low arc, where knowledge has no apparatus to attach to, and the ecological domain is
    empty under the Phase 4e/4f partition.
    """
    headers = ["ε", "personal%", "infra%", "eco%", "know%",
               "eco h/p·yr", "know h/p·yr", "personal h/p·yr"]
    rows = []
    for r in rows_data:
        tot = r["total_eoh"] or 1.0
        rows.append([
            fmt_eps(r["epsilon"]),
            fmt_pct(r["personal_eoh"] / tot),
            fmt_pct(r["infra_eoh"] / tot),
            fmt_pct(r["eco_eoh"] / tot),
            fmt_pct(r["knowledge_eoh"] / tot),
            fmt_float(r["eco_eoh"] / population),
            fmt_float(r["knowledge_eoh"] / population),
            fmt_float(r["personal_eoh"] / population),
        ])
    print(table(headers, rows))
    print()
    print(bold("Domain balance: "), end="")
    lo, hi = rows_data[0], rows_data[-1]

    def share(r: dict, key: str) -> float:
        return r[key] / (r["total_eoh"] or 1.0)

    eco_max = max(r["eco_eoh"] for r in rows_data) / population
    print(f"personal EOH runs {share(lo, 'personal_eoh'):.1%} of the total at "
          f"ε={lo['epsilon']:.2f} and {share(hi, 'personal_eoh'):.1%} at "
          f"ε={hi['epsilon']:.2f}; knowledge rises from {share(lo, 'knowledge_eoh'):.1%} "
          f"to {share(hi, 'knowledge_eoh'):.1%}.\n"
          f"The ecological domain reads at most {eco_max:.3g} h/person·yr on this arc: "
          "Phases 4e/4f moved both\nrecurring terms to GUF, and the domain carries "
          "supplied stocks only.\n"
          "See docs/parameter_provenance.md §'Domain balance — the denominator problem'.")


def run(args: argparse.Namespace) -> None:
    eps_ref = getattr(args, "knowledge_epsilon_ref", None)
    knowledge_base = None
    if eps_ref is not None:
        from hours_eoh.scenarios.knowledge_base import knowledge_base_from_registry
        knowledge_base = knowledge_base_from_registry(eps_ref)["base_rate"]

    rows_data = _sweep(args.points, args.population, args.trust_balance,
                       getattr(args, "thermal_obligation", 0.0),
                       knowledge_base)

    if args.fmt == "json":
        print(json.dumps(rows_data, indent=2))
        return

    if args.fmt == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows_data[0].keys()))
        writer.writeheader()
        writer.writerows(rows_data)
        return

    if getattr(args, "domain_shares", False):
        _domain_share_rows(rows_data, args.population)
        return

    # table
    headers = ["ε", "personal", "infra", "eco", "knowledge", "total_eoh",
               "reg%", "teh_created", "floor_price", "floor_pp", "solvent"]
    rows = []
    for r in rows_data:
        rows.append([
            fmt_eps(r["epsilon"]),
            fmt_float(r["personal_eoh"]),
            fmt_float(r["infra_eoh"]),
            fmt_float(r["eco_eoh"]),
            fmt_float(r["knowledge_eoh"]),
            fmt_float(r["total_eoh"]),
            fmt_pct(r["registration"]),
            fmt_float(r["teh_created"]),
            fmt_float(r["floor_price"]),
            fmt_float(r["floor_pp"]),
            "Y" if r["solvent"] else "N",
        ])
    print(table(headers, rows))
    if eps_ref is not None and knowledge_base is not None:
        print()
        star, spread, band_lo, band_hi = knowledge_ref_figures()
        print(f"KNOWLEDGE_EOH_BASE re-derived at ε_ref = {eps_ref:.2f}: "
              f"{knowledge_base:.4e} (the frozen base sits at its fixed point, "
              f"ε_ref = {star:.3f}). This is the arc's dominant knowledge-domain "
              f"lever — {spread:.2f}× across ε_ref ∈ [{band_lo}, {band_hi}].")
    if getattr(args, "thermal_obligation", 0.0) > 0.0:
        print()
        print(f"Carrying a thermal obligation of "
              f"{args.thermal_obligation:,.0f} h/yr as the fourth ecological term "
              f"({args.thermal_obligation / args.population:.2f} h/person·yr).")
