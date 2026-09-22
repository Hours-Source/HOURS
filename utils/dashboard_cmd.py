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
from hours_eoh.core.simulation import make_economy_state, simulate_period
from hours_eoh.data import (
    CAPITAL_STOCK_DEFAULT,
    ESSENTIAL_DOMAINS,
    MEANINGFUL_ACTIVITY_TEH_BASE,
    CONTESTABILITY_CHI_CRIT,
)
from hours_eoh.params import EohParams
from hours_eoh.research.contestability import contestability_margin
from hours_eoh.research.recalibration import exit_financing

from utils.formatters import bold, green, red, status_color, fmt_float, fmt_eps
from hours_eoh.core.eoh_generation import resolve_capital_stock
from hours_eoh.core.fiscal import resolve_trust_balance


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("dashboard", help="System health snapshot at a given ε")
    p.add_argument("--epsilon", type=float, default=0.40, metavar="ε")
    p.add_argument("--population", type=float, default=1_000_000.0)
    # DEFAULT None since 2026-09-17 (Trust-frame decision): an unsupplied
    # balance resolves against --population, so the inheritance travels with
    # the frame. Supplying the flag states YOUR balance and it is used as given.
    p.add_argument("--trust-balance", type=float, default=None)
    # DEFAULT None since 2026-09-09 (capital-path decision): an unsupplied
    # stock resolves along the canonical arc at --epsilon, so the dashboard
    # reads the arc rather than a fixed 2e9 at every ε. Supplying the flag
    # states YOUR stock and it is used as given.
    p.add_argument("--capital-stock", type=float, default=None)
    p.add_argument("--ecosystem-health", type=float, default=0.70)
    p.add_argument("--measured", action="store_true",
                   help="Source Condition II from the measured O*NET/BLS registry "
                        "(751 occupations, repriced to ε) instead of DEFAULT_SEGMENTS")
    p.add_argument("--thermal-obligation", type=float, default=0.0, metavar="EOH",
                   help="Annual planetary radiative-capacity obligation (h/yr) to "
                        "carry as the fourth ecological term. Default 0.0 (off). "
                        "~1.79e6 for 1M people at ε=0.40 per research/thermal_solvency")
    p.add_argument("--certified-fraction", type=float,
                   default=DECLARED_CERTIFIED_FRACTION, metavar="SHARE",
                   help="Share of the workforce with certified competency in each "
                        "essential domain. DECLARED: nothing in the package tracks "
                        f"it. Default {DECLARED_CERTIFIED_FRACTION}")
    p.add_argument("--format", choices=["table", "json"], default="table", dest="fmt")
    p.set_defaults(func=run)


#: The one account this command cannot compute. Nothing in the package tracks
#: certified competency by domain, so Condition IV reads a DECLARED share of the
#: workforce, printed as declared and overridable with --certified-fraction. It
#: sits above the Condition IV threshold, so on its default the condition can
#: only pass — which is why it is shown rather than folded into the verdict.
DECLARED_CERTIFIED_FRACTION = 0.18


def _build_kwargs(eps: float, population: float, trust_balance: float | None,
                  capital_stock: float, ecosystem_health: float,
                  thermal_obligation: float = 0.0,
                  certified_fraction: float = DECLARED_CERTIFIED_FRACTION) -> dict:
    """
    The dashboard's accounts, computed rather than invented (2026-09-12).

    Until then the ledger, the Trust and the EOH totals were stand-ins built from
    literals (destroyed = 0.85 × created, expenditure = 0.90 × earnings, total
    EOH = population × base × 1.5), so Conditions I and III passed by
    construction and the EOH indicators read a total up to 1.6× off the model's.
    Now: the EOH side comes from the pipeline on the stated frame, and the ledger
    and Trust from ONE simulated period on the same frame — the only engine in
    the package that tracks both. Only certified competency is declared.
    """
    trust_balance = resolve_trust_balance(trust_balance, population)
    p = EohParams()
    workforce_fraction = float(p["workforce_fraction"])
    capital_age_ratio = float(p["capital_age_ratio"])
    workforce = population * workforce_fraction

    pipeline = eoh_to_teh_pipeline(eps, population=population,
                                   capital_stock=capital_stock,
                                   capital_age_ratio=capital_age_ratio,
                                   ecosystem_health=ecosystem_health,
                                   thermal_obligation=thermal_obligation)
    teh_created = float(pipeline["teh_created"])
    # The pipeline's total already carries the thermal obligation as its fourth
    # ecological term. With no labour supply nothing is deferred, so fulfilled
    # equals the total — stated, not assumed away.
    total_eoh_val = float(pipeline["total_eoh"])
    fulfilled = total_eoh_val - float(pipeline["deferred_total"])

    # Condition I and III accounts from one simulated period on the same frame.
    state = make_economy_state(
        epsilon=eps, population=population, trust_balance=trust_balance,
        capital_stock_teh=capital_stock, capital_age_ratio=capital_age_ratio,
        ecosystem_health=ecosystem_health, workforce_fraction=workforce_fraction,
    )
    after, period = simulate_period(state)
    trust = period["fiscal"]["trust"]

    certified_by_domain = {d: workforce * certified_fraction for d in ESSENTIAL_DOMAINS}

    return dict(
        epsilon=eps,
        teh_created=float(after["teh_created_cumulative"]),
        teh_destroyed=float(after["teh_destroyed_cumulative"]),
        teh_observed=float(period["teh_total_supply"]) - float(after["teh_endowment"]),
        # The Trust balance's own identity (2026-09-15): what the Trust OWES
        # leaves the balance, and levy and GUF inflows enter it
        # (`fiscal.trust_management`). Stewardship, ecological and care labour
        # are paid at the mint and never appear here; unspent dividend is
        # retained, so the dividend is capacity and not an outflow. Read
        # `total_expenditure` rather than the guarantee directly, so this stays
        # bound to whatever core charges the Trust.
        balance_start=float(trust["trust_start"]),
        earnings=float(trust["levy_inflow"]) + float(trust["guf_inflow"]),
        expenditures=float(trust["total_expenditure"]),
        balance_end=float(trust["trust_end"]),
        certified_by_domain=certified_by_domain,
        workforce_size=workforce,
        total_eoh=total_eoh_val,
        fulfilled_eoh=fulfilled,
        deferred_eoh=0.0,
        time_deferred=0.0,
        trust_balance=trust_balance,
        labor_income=teh_created,
        capital_stock_teh=capital_stock,
        capital_age_ratio=capital_age_ratio,
        population=population,
        floor_teh=MEANINGFUL_ACTIVITY_TEH_BASE,
        # THE PIPELINE'S OWN ECOLOGICAL FIGURE, forwarded (2026-08-17).
        #
        # `fiscal.ecological_allocation` falls back to `base_rate =
        # ECOLOGICAL_BASE_RATE` — the obligation for the WHOLE contiguous US —
        # when no override is supplied. This command already computes the
        # pipeline, so it HAD the frame-resolved value in hand and discarded it
        # one line from where it was needed, reporting an ecological cost
        # inflated ~812x. `simulation.py` and `civilization.py` both forward it
        # and were always correct; only the user-facing dashboard was not.
        #
        # Third instance of the bypass pattern, after `scenarios/sweep.py` and
        # the `skill_decay_rate` literal: a caller that reaches around the
        # shared path is where a superseded default survives.
        eco_eoh_override=float(pipeline["eoh_by_domain"]["ecological"]),
    )


def run(args: argparse.Namespace) -> None:
    # Resolve ONCE, so every panel below reads the same capital at this ε —
    # `psi` diverging from `psi_applied` is what two resolution points look like.
    _capital = resolve_capital_stock(args.capital_stock, args.epsilon)
    kwargs = _build_kwargs(
        args.epsilon, args.population, args.trust_balance,
        _capital, args.ecosystem_health,
        getattr(args, "thermal_obligation", 0.0),
        getattr(args, "certified_fraction", DECLARED_CERTIFIED_FRACTION),
    )
    # Contestability: computed here (research/ layer) and passed into core
    # system_dashboard() so overall_status reflects it. The ADOPTED §8.9
    # three-channel invariant governs; χ rides along as the superseded stricter
    # stress (see core.dashboard.system_dashboard for why both are passed).
    _chi = contestability_margin(
        args.epsilon, args.population, args.trust_balance,
    )
    _fin = exit_financing(args.epsilon, population=args.population)
    # --measured: replace synthetic DEFAULT_SEGMENTS with the O*NET/BLS registry
    # repriced to this ε (boundary injection; core stays pure).
    if getattr(args, "measured", False):
        from hours_eoh.scenarios.measured import measured_segments
        kwargs["segments"] = measured_segments(args.epsilon)
    snap = system_dashboard(**kwargs, chi=_chi["chi"],
                            exit_financeable=bool(_fin["exit_financeable"]))

    if args.fmt == "json":
        print(json.dumps(snap, indent=2, default=str))
        return

    overall = snap.get("overall_status", "UNKNOWN")
    print(bold(f"System Dashboard — ε = {fmt_eps(args.epsilon)}  "
               f"[{status_color(overall)}]"))
    if getattr(args, "measured", False):
        c2 = snap.get("condition_ii", {})
        m_meas = c2.get("mean_multiplier") if isinstance(c2, dict) else None
        note = "Condition II from measured O*NET/BLS registry (751 occs, repriced to ε)"
        if isinstance(m_meas, (int, float)):
            note += f" — mean m̄ = {m_meas:.4f}"
        print(green("  ● " + note))
    _cf = getattr(args, "certified_fraction", DECLARED_CERTIFIED_FRACTION)
    print(f"  Accounts: EOH from the pipeline; ledger and Trust from one simulated "
          f"period.\n  DECLARED, not tracked: certified competency = {_cf:.2f} of "
          f"the workforce per domain (--certified-fraction).")
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
    # The ADOPTED invariant first (§8.9 three-channel financeability). The bare-χ
    # figures below it are the retired flow/stock test, kept as a stricter stress
    # — reporting only χ is what let a superseded verdict stand as the result.
    _fin_label = (
        green(f"exit FINANCEABLE via {_fin['channel']} channel")
        if _fin["exit_financeable"]
        else red("exit NOT FINANCEABLE — no channel carries")
    )
    print(f"  §8.9 invariant (adopted): {_fin_label}")
    _t = _fin["t_exit_self_years"]
    print(f"    t_exit_self = {_t:.2f} yr" if _t != float("inf") else
          "    t_exit_self = ∞ (dividend cannot fund the capital share)", end="")
    print(f"   entry_capacity = {_fin['entry_capacity']:.3g}")

    _cv = _chi["chi"]
    _cm = _chi["chi_marginal"]
    _chi_label = (
        green(f"χ = {_cv:.3f} ≥ 1") if _cv >= CONTESTABILITY_CHI_CRIT
        else red(f"χ = {_cv:.3f} < 1")
    )
    _marg_label = (
        green(f"χ_marginal = {_cm:.3f} ≥ 1") if _cm >= CONTESTABILITY_CHI_CRIT
        else red(f"χ_marginal = {_cm:.3f} < 1")
    )
    print(f"  [SUPERSEDED stress] P/K_entry: {_chi_label}")
    print(f"  [SUPERSEDED stress] tenure-0 member: {_marg_label}")
    print(f"    P = {fmt_float(_chi['p'], decimals=0)} TEH/person   "
          f"K_entry = {fmt_float(_chi['k_entry'], decimals=0)} TEH/person")
    if _fin["exit_financeable"] and _cv < CONTESTABILITY_CHI_CRIT:
        print("    (χ < 1 with exit still financeable is EXPECTED: χ demands one "
              "year's income cover\n     the whole founding stock — the RC4 "
              "flow/stock mismatch §8.9 retired.)")

    print()
    print(bold("Autarky comparison (Block II)"))
    from hours_eoh.core.autarky import overbuild_check as _ob, break_even_epsilon as _be
    _o = _ob(_capital, args.population, epsilon=args.epsilon)
    _vcol = green if _o["verdict"] == "pays" else red
    print(f"  verdict: {_vcol(_o['verdict'].upper())}  — {_o['note']}")
    print(f"  B₀ (autarky) {_o['autarky_reference'] / args.population:8.1f}   "
          f"B(K) {_o['obligation_with_apparatus'] / args.population:8.1f}   "
          f"overhead {_o['overhead'] / args.population:7.1f}   h/person·yr")
    print(f"  abatement a(K) = {_o['abatement']:.4f}   "
          f"break-even ε = {_be(_capital, args.population):.4f}")

    # `suppressed_flags` is printed HERE and not only in --format json (2026-09-17).
    # core.system_dashboard declared the masking on 2026-09-16 — "MASKING MUST BE
    # DECLARED, NEVER INFERRED" — but the table path, which is the default and what
    # a person actually reads, printed only the two flag lists. So at ε=0 the reader
    # saw `Personal registration: RED` above an EMPTY red-flag list and an
    # overall_status that did not reflect it, with nothing saying the exclusion was
    # deliberate: the declaration existed in the library and was invisible at the
    # documented entry point. Same shape as the ten --trust-balance defaults.
    for flag_key, flag_label in [
        ("red_flags", "Red flags"),
        ("yellow_flags", "Warnings"),
        ("suppressed_flags", "Suppressed — declared, and NOT counted in overall status"),
    ]:
        flags = snap.get(flag_key, [])
        if flags:
            print()
            print(bold(f"{flag_label}:"))
            for flag in flags:
                print(f"  • {flag}")
