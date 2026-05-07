"""
params — EohParams inspection and persistent modification.

  eoh params show [--filter KEY]        Print all current values.
  eoh params set KEY VALUE [--reason R] Persist the change; show before/after delta.
  eoh params set KEY VALUE --dry-run    Preview the delta without persisting.
  eoh params diff                       Print overrides relative to defaults.
  eoh params reset                      Reset all params to defaults.

State is persisted to utils/_params_state.json between invocations.
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Any

from hours_eoh.params import EohParams
from hours_eoh.core.eoh_fulfillment import eoh_to_teh_pipeline
from hours_eoh.core.fiscal import fiscal_snapshot
from hours_eoh.data import TRUST_BASE_TEH

from utils.formatters import bold, fmt_float, green, red, dim

_STATE_FILE = Path(__file__).parent / "_params_state.json"


def build_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = sub.add_parser("params", help="Inspect and modify EohParams")
    sub2 = p.add_subparsers(dest="params_cmd", required=True)

    show = sub2.add_parser("show", help="Print current parameter values")
    show.add_argument("--filter", metavar="KEY", dest="filter_key",
                      help="Only show params matching this substring")
    show.set_defaults(func=_show)

    set_ = sub2.add_parser("set", help="Set a parameter value")
    set_.add_argument("key", help="Parameter name")
    set_.add_argument("value", help="New value (parsed as float/int/bool)")
    set_.add_argument("--reason", default="", help="Reason for the change")
    set_.add_argument("--dry-run", action="store_true",
                      help="Preview delta without persisting")
    set_.set_defaults(func=_set)

    diff = sub2.add_parser("diff", help="Show overrides relative to defaults")
    diff.set_defaults(func=_diff)

    reset = sub2.add_parser("reset", help="Reset all params to defaults")
    reset.set_defaults(func=_reset)


# ---------------------------------------------------------------------------
# State persistence helpers
# ---------------------------------------------------------------------------

def _load_overrides() -> dict[str, Any]:
    if _STATE_FILE.exists():
        with open(_STATE_FILE) as f:
            return json.load(f)  # type: ignore[no-any-return]
    return {}


def _save_overrides(overrides: dict[str, Any]) -> None:
    with open(_STATE_FILE, "w") as f:
        json.dump(overrides, f, indent=2)


def _make_params(overrides: dict[str, Any] | None = None) -> EohParams:
    p = EohParams()
    for key, val in (overrides or _load_overrides()).items():
        p.set(key, val, reason="[persisted]")
    return p


def _parse_value(raw: str) -> Any:
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


# ---------------------------------------------------------------------------
# Downstream impact: TEH created + fiscal solvency at three ε checkpoints
# ---------------------------------------------------------------------------

def _impact_row(p: EohParams, eps: float) -> dict[str, Any]:
    data = p.to_dict()
    pipeline = eoh_to_teh_pipeline(
        eps,
        population=float(data["population"]),
        capital_stock=float(data["capital_stock_teh"]),
        capital_age_ratio=float(data["capital_age_ratio"]),
        ecosystem_health=float(data.get("ecosystem_health", 0.70)),
    )
    teh_created  = float(pipeline.get("teh_created", 0.0))
    labor_income = float(pipeline.get("registered_eoh", 0.0)) * 2200.0
    levy_rates = {"sufficiency": float(data.get("suff_levy_rate", 0.0125))}
    snap = fiscal_snapshot(
        epsilon=eps,
        population=float(data["population"]),
        trust_balance=TRUST_BASE_TEH,
        labor_income=labor_income,
        capital_stock_teh=float(data["capital_stock_teh"]),
        capital_age_ratio=float(data["capital_age_ratio"]),
        levy_rates=levy_rates,
        dep_rate=float(data.get("dep_rate", 0.02)),
        div_rate=float(data.get("div_rate", 0.05)),
    )
    return {
        "epsilon":        eps,
        "teh_created":    teh_created,
        "surplus_deficit": snap["trust"]["surplus_deficit"],
        "solvent":        snap.get("solvent", False),
    }


def _cfmt(val: float, width: int = 11) -> str:
    """Format a signed delta with fixed visible width, then colorize."""
    raw = ("+" if val >= 0 else "") + fmt_float(val, decimals=1)
    return (green if val >= 0 else red)(raw.rjust(width))


def _print_impact(p_before: EohParams, p_after: EohParams) -> None:
    checkpoints = [0.0, 0.40, 0.99]
    print(bold("  Downstream impact (TEH created / Trust solvency):"))
    print(f"  {'ε':>6}  {'teh Δ':>11}  {'surplus (after)':>15}  {'surp Δ':>11}  solvent")
    for eps in checkpoints:
        before = _impact_row(p_before, eps)
        after  = _impact_row(p_after,  eps)
        teh_delta  = after["teh_created"]    - before["teh_created"]
        surp_delta = after["surplus_deficit"] - before["surplus_deficit"]
        teh_s   = _cfmt(teh_delta)
        surp_s  = _cfmt(surp_delta)
        after_s = fmt_float(after["surplus_deficit"], decimals=1).rjust(15)
        sol_b = "Y" if before["solvent"] else "N"
        sol_a = "Y" if after["solvent"]  else "N"
        sol_s = sol_a if sol_a == sol_b else f"{sol_b}→{sol_a}"
        if sol_a == "N":
            sol_s = red(sol_s)
        print(f"  {eps:>6.2f}  {teh_s}  {after_s}  {surp_s}  {sol_s}")


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def _show(args: argparse.Namespace) -> None:
    overrides = _load_overrides()
    p = _make_params(overrides)
    items = sorted(p.to_dict().items())
    if args.filter_key:
        items = [(k, v) for k, v in items if args.filter_key.lower() in k.lower()]
    print(bold("EohParams — current values"))
    print(f"  {'key':<40} {'value':>18}  {'status'}")
    print("  " + "-" * 68)
    for k, v in items:
        tag = dim("[overridden]") if k in overrides else ""
        print(f"  {k:<40} {str(v):>18}  {tag}")


def _set(args: argparse.Namespace) -> None:
    new_val = _parse_value(args.value)
    overrides = _load_overrides()

    p_defaults = EohParams()
    valid_keys = set(p_defaults.to_dict().keys())
    if args.key not in valid_keys:
        print(red(f"Unknown parameter: {args.key}"))
        print(dim("  Run 'eoh params show' to see available keys."))
        return

    p_before = _make_params(overrides)
    old_val = p_before.to_dict()[args.key]

    new_overrides = {**overrides, args.key: new_val}
    p_after = _make_params(new_overrides)

    print(bold(f"{'[DRY RUN] ' if args.dry_run else ''}params set {args.key}"))
    print(f"  {args.key}: {old_val}  →  {new_val}")
    print()
    _print_impact(p_before, p_after)

    if not args.dry_run:
        _save_overrides(new_overrides)
        print()
        print(green(f"  Persisted. Run 'eoh params diff' to review all overrides."))


def _diff(args: argparse.Namespace) -> None:
    overrides = _load_overrides()
    if not overrides:
        print(dim("No overrides — all params at defaults."))
        return
    p_default = EohParams()
    defaults = p_default.to_dict()
    print(bold("Active overrides (relative to defaults):"))
    for k, v in overrides.items():
        default = defaults.get(k, "—")
        print(f"  {k}: {default} → {v}")


def _reset(args: argparse.Namespace) -> None:
    if _STATE_FILE.exists():
        os.remove(_STATE_FILE)
    print(green("All params reset to defaults."))
