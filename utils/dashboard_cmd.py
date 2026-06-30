"""
dashboard — system snapshot with color-coded condition status.

Runs system_dashboard() at a given ε and prints all four structural
conditions (I–IV) plus EOH and fiscal health indicators.
"""

from __future__ import annotations
import argparse
import json

from hours_eoh.core.dashboard import system_dashboard
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.data import (
    TRUST_BASE_TEH, CAPITAL_STOCK_DEFAULT,
    PERSONAL_EOH_BASE, ESSENTIAL_DOMAINS,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    CONTESTABILITY_CHI_CRIT,
)
from hours_eoh.params import EohParams
from hours_eoh.research.contestability import contestability_margin

from utils.formatters import bold, green, red, status_color, fmt_float, fmt_eps


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("dashboard", help="System health snapshot at a given ε")
    p.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    p.add_argument("--population", type=float, default=1_000_000.0)
    p.add_argument("--trust-balance", type=float, default=TRUST_BASE_TEH)
    p.add_argument("--capital-stock", type=float, default=CAPITAL_STOCK_DEFAULT)
    p.add_argument("--ecosystem-health", type=float, default=0.70)
    p.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    p.set_defaults(func=run)


def _build_kwargs(eps: float, population: float, trust_balance: float,
                  capital_stock: float, ecosystem_health: float) -> dict:
    p = EohParams()
    workforce = population * float(p["workforce_fraction"])

    pipeline = eoh_to_teh_pipeline(eps, population=population,
                                   capital_stock=capital_stock,
                                   ecosystem_health=ecosystem_health)
    teh_created   = float(pipeline.get("teh_created", 0.0))
    teh_destroyed = teh_created * 0.85
    teh_observed  = teh_created - teh_destroyed

    levy_rate = float(p["suff_levy_rate"])
    earnings     = teh_created * levy_rate
    expenditures = earnings * 0.90
    balance_end  = trust_balance + earnings - expenditures

    total_eoh_val = population * PERSONAL_EOH_BASE * 1.5
    fulfilled     = total_eoh_val * (1.0 - eps * 0.5)

    certified_by_domain = {d: workforce * 0.18 for d in ESSENTIAL_DOMAINS}

    return dict(
        epsilon=eps,
        teh_created=teh_created,
        teh_destroyed=teh_destroyed,
        teh_observed=teh_observed,
        balance_start=trust_balance,
        earnings=earnings,
        expenditures=expenditures,
        balance_end=balance_end,
        certified_by_domain=certified_by_domain,
        workforce_size=workforce,
        total_eoh=total_eoh_val,
        fulfilled_eoh=fulfilled,
        deferred_eoh=0.0,
        time_deferred=0.0,
        trust_balance=trust_balance,
        labor_income=teh_created,
        capital_stock_teh=capital_stock,
        capital_age_ratio=float(p["capital_age_ratio"]),
        population=population,
        floor_teh=MEANINGFUL_ACTIVITY_TEH_BASE,
    )


def run(args: argparse.Namespace) -> None:
    kwargs = _build_kwargs(
        args.epsilon, args.population, args.trust_balance,
        args.capital_stock, args.ecosystem_health,
    )
    snap = system_dashboard(**kwargs)

    if args.fmt == "json":
        print(json.dumps(snap, indent=2, default=str))
        return

    overall = snap.get("overall_status", "UNKNOWN")
    print(bold(f"System Dashboard — ε = {fmt_eps(args.epsilon)}  "
               f"[{status_color(overall)}]"))
    print()

    print(bold("Structural Conditions"))
    for key, label in [
        ("condition_i",   "I   — Ledger Identity"),
        ("condition_ii",  "II  — Multiplier Band"),
        ("condition_iii", "III — Zero Interest"),
        ("condition_iv",  "IV  — Distributed Competency"),
    ]:
        entry = snap.get(key, {})
        status = entry.get("status", "UNKNOWN") if isinstance(entry, dict) else "UNKNOWN"
        print(f"  {label}: {status_color(status)}")

    print()
    print(bold("EOH Health"))
    eoh = snap.get("eoh_health", {})
    def _eoh_row(label: str, val_key: str, status_key: str) -> None:
        v = eoh.get(val_key, "—")
        s = eoh.get(status_key, "")
        print(f"  {label}: {status_color(s)}  {fmt_float(float(v)) if isinstance(v, (int, float)) else v}")
    _eoh_row("Deferred ratio",        "deferred_maintenance_ratio", "deferred_ratio_status")
    _eoh_row("Compounding ratio",     "eoh_compounding_ratio",      "compounding_status")
    _eoh_row("Registration coverage", "registration_coverage",      "registration_status")
    _eoh_row("Personal registration", "personal_registration_share","personal_registration_status")

    print()
    print(bold("Fiscal Health"))
    fh = snap.get("fiscal_health", {})
    def _fh_row(label: str, val_key: str, status_key: str) -> None:
        v = fh.get(val_key, "—")
        s = fh.get(status_key, "")
        print(f"  {label}: {status_color(s)}  {fmt_float(float(v)) if isinstance(v, (int, float)) else v}")
    _fh_row("Trust solvency",        "trust_surplus_deficit", "trust_status")
    _fh_row("PP index",              "pp_index",              "pp_status")
    _fh_row("Levy/guarantee ratio",  "levy_to_guarantee_ratio","levy_status")
    _fh_row("Ecological cost",       "ecological_cost",       "ecological_status")

    print()
    print(bold("Contestability (§8)"))
    _chi = contestability_margin(
        args.epsilon, args.population, args.trust_balance,
    )
    _cv = _chi["chi"]
    _chi_label = (
        green(f"χ = {_cv:.3f} ≥ 1") if _cv >= CONTESTABILITY_CHI_CRIT
        else red(f"χ = {_cv:.3f} < 1 — EXIT IS NOMINAL")
    )
    print(f"  P/K_entry (increasing_returns): {_chi_label}")
    print(f"  P = {fmt_float(_chi['p'], decimals=0)} TEH/person   "
          f"K_entry = {fmt_float(_chi['k_entry'], decimals=0)} TEH/person")

    for flag_key, flag_label in [("red_flags", "Red flags"), ("yellow_flags", "Warnings")]:
        flags = snap.get(flag_key, [])
        if flags:
            print()
            print(bold(f"{flag_label}:"))
            for flag in flags:
                print(f"  • {flag}")
