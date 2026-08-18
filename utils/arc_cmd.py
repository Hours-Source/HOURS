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
from hours_eoh.core.registration import total_registration_share
from hours_eoh.core.prices import basket_price, floor_price, floor_purchasing_power
from hours_eoh.data import MEANINGFUL_ACTIVITY_TEH_BASE
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.data import TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT

from utils.formatters import table, fmt_float, fmt_pct, fmt_eps, bold


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("arc", help="Sweep the epsilon arc and display system metrics")
    p.add_argument("--points", type=int, default=20, metavar="N",
                   help="Number of ε points (default: 20)")
    p.add_argument("--domain", choices=["personal", "infra", "eco", "knowledge", "all"],
                   default="all", help="Domain to highlight (default: all)")
    p.add_argument("--format", choices=["table", "csv", "json"], default="table",
                   dest="fmt", help="Output format (default: table)")
    p.add_argument("--population", type=float, default=1_000_000.0)
    p.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH)
    p.add_argument("--domain-shares", action="store_true",
                   help="Show each domain as a SHARE of total EOH instead of "
                        "absolute hours (the denominator check — see "
                        "docs/parameter_provenance.md 'Domain balance')")
    p.add_argument("--thermal-obligation", type=float, default=0.0, metavar="EOH",
                   help="Annual planetary radiative-capacity obligation (h/yr) to "
                        "carry as the fourth ecological term. Default 0.0 (off). "
                        "~1.79e6 for 1M people at ε=0.40 per research/thermal_solvency")
    p.add_argument("--knowledge-epsilon-ref", type=float, default=None,
                   dest="knowledge_epsilon_ref", metavar="EPS",
                   help="Re-derive KNOWLEDGE_EOH_BASE at this reference "
                        "automation level instead of the frozen ε_ref = 0.40, "
                        "and run the arc with it. THE DOMINANT UNCERTAINTY in "
                        "the knowledge domain: 7.13x across [0.2, 0.6]. "
                        "See notes/knowledge-eoh-closure.md §4")
    p.set_defaults(func=run)


def _sweep(n_points: int, population: float, trust_balance: float,
           thermal_obligation: float = 0.0,
           knowledge_base: float | None = None) -> list[dict]:
    results = []
    for i in range(n_points):
        eps = i / (n_points - 1) * 0.99 if n_points > 1 else 0.40
        state = canonical_physical_state(eps)
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
        reg = total_registration_share(eps)
        price = floor_price(eps)
        floor_pp_result = floor_purchasing_power(MEANINGFUL_ACTIVITY_TEH_BASE, eps)
        floor_pp = float(floor_pp_result.get("pp_index", 0.0))

        labor_income = pipeline.get("registered_eoh", 0.0) * 2200.0
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

    The denominator check. ε = machine_EOH / total_EOH, so whichever domain
    dominates total_EOH effectively sets ε.

    Block K-IV (2026-08-08) moved this materially: personal ran 87–96% across
    the whole arc before knowledge was put on its measured O*NET footing. After
    K-IV, the ε_ref fixed-point re-anchor and the 2026-08-10 AGE_GROUPS elderly
    revalue, it runs 98.9% → 46.1% (re-measured 2026-08-10). The defect is
    PARTLY closed — personal still dominates the low arc, where there is no
    apparatus for knowledge to attach to, and the ecological domain is
    untouched at <0.1%.
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
    print("personal EOH runs ~99% at ε=0 falling to ~46% at ε=0.99. Block K-IV "
          "put knowledge on\nits measured O*NET/BLS footing, which closed one of "
          "the two small domains — knowledge is\nnow CO-EQUAL with personal at "
          "the top of the arc (~46% each).\n\n"
          "The ECOLOGICAL domain is 464x SMALLER than this table used to show, and "
          "the correction\nis the finding. Until 2026-08-17 the default paired "
          "ECOLOGICAL_BASE_RATE — the obligation\nfor the WHOLE contiguous US — "
          "with a population of 1,000,000, so the column was\nflattered by the "
          "ratio between them. The area is now resolved FROM the population, and "
          "the\ndomain reads ~0.001 h/person·yr. The defect did not shrink when "
          "the frame was declared:\nit was being MASKED by the frame, and it is "
          "the last of the four domains still open.\n"
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
        print(f"KNOWLEDGE_EOH_BASE re-derived at ε_ref = {eps_ref:.2f}: "
              f"{knowledge_base:.4e} (frozen default is ε_ref = 0.40). "
              f"This is the arc's dominant knowledge-domain lever — 7.13× "
              f"across ε_ref ∈ [0.2, 0.6].")
    if getattr(args, "thermal_obligation", 0.0) > 0.0:
        print()
        print(f"Carrying a thermal obligation of "
              f"{args.thermal_obligation:,.0f} h/yr as the fourth ecological term "
              f"({args.thermal_obligation / args.population:.2f} h/person·yr).")
